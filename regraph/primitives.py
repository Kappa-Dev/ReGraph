import warnings
import os
import json
import itertools
import copy
import networkx as nx

from copy import deepcopy
from networkx.algorithms import isomorphism

from regraph.utils import (merge_attributes,
                           normalize_attrs,
                           valid_attributes,
                           to_set,
                           keys_by_value,
                           is_subdict,
                           dict_sub)
from regraph.exceptions import (ReGraphError,
                                GraphError,
                                GraphAttrsWarning)


def unique_node_id(graph, prefix):
    """get a unique id starting by prefix"""
    if prefix not in graph.nodes():
        return prefix
    idx = 0
    new_id = "{}_{}".format(prefix, idx)
    while new_id in graph.nodes():
        idx += 1
        new_id = "{}_{}".format(prefix, idx)
    return new_id


def copy_node(graph, node_id):
    new_name = unique_node_id(graph, node_id)
    add_node(graph, new_name, graph.node[node_id])
    return new_name


def add_node(graph, node_id, attrs=None):
    """Add node to a nx.(Di)Graph."""
    new_attrs = deepcopy(attrs)
    if new_attrs is None:
        new_attrs = dict()
    if node_id not in graph.nodes():
        graph.add_node(node_id)
        normalize_attrs(new_attrs)
        graph.node[node_id] = new_attrs
        # self.unckecked_nodes.add(node_id)
    else:
        raise GraphError("Node '%s' already exists!" % node_id)


def remove_node(graph, node):
    """Remove node from the self."""
    if node in graph.nodes():
        neighbors = set(graph.__getitem__(node).keys())
        neighbors -= {node}
        graph.remove_node(node)
        # self.unckecked_nodes |= neighbors
    else:
        raise GraphError("Node %s does not exist!" % str(node))
    return


def add_nodes_from(graph, node_list):
    """Add nodes from a list."""
    for n in node_list:
        if type(n) == int:
            add_node(graph, n)
        elif len(n) == 2:
            node_id, node_attrs = n
            add_node(graph, node_id, node_attrs)
        else:
            raise ReGraphError(
                "Each element of the node list should be either " +
                "'node_id' or ('node_id', 'node_attrs')!"
            )


def add_node_attrs(graph, node, attrs_dict):
    """Add new attributes to the node."""
    new_attrs = deepcopy(attrs_dict)
    if node not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node))
    elif new_attrs is None:
        pass
    else:
        # if not self.valid_attributes(node, attrs_dict):
        #     raise ValueError("The attributes are not valid!")
        if graph.node[node] is None:
            graph.node[node] = deepcopy(new_attrs)
            normalize_attrs(graph.node[node])
        else:
            normalize_attrs(graph.node[node])
            for key, value in new_attrs.items():
                if key not in graph.node[node].keys():
                    graph.node[node].update({key: to_set(value)})
                else:
                    graph.node[node][key] =\
                        graph.node[node][key].union(to_set(value))


def update_node_attrs(graph, node, attrs):
    """Update attributes of a node."""
    new_attrs = deepcopy(attrs)
    if node not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node))
    elif new_attrs is None:
        warnings.warn(
            "You want to update '%s' attrs with an empty attrs_dict!" % node,
            GraphAttrsWarning
        )
    else:
        # if not self.valid_attributes(node, new_attrs):
        #     raise ValueError("The attributes are not valid")
        normalize_attrs(new_attrs)
        # if self.node[node].attrs_ is None:
        graph.node[node] = new_attrs


def remove_node_attrs(graph, node, attrs_dict):
    """Remove attrs of a node specified by attrs_dict."""
    if node not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node))
    elif attrs_dict is None:
        pass
        warnings.warn(
            "You want to remove attrs from '%s' with an empty attrs_dict!" % node, 
            GraphAttrsWarning
        )
    elif graph.node[node] is None:
        warnings.warn(
            "Node '%s' does not have any attribute!" % node, GraphAttrsWarning
        )
    else:
        normalize_attrs(graph.node[node])
        for key, value in attrs_dict.items():
            if key not in graph.node[node].keys():
                warnings.warn(
                    "Node '%s' does not have attribute '%s'!" %
                    (node, key), GraphAttrsWarning
                )
            else:
                elements_to_remove = []
                for el in to_set(value):
                    if el in graph.node[node][key]:
                        elements_to_remove.append(el)
                    else:
                        warnings.warn(
                            "Node '%s' does not have attribute '%s' with value '%s'!" %
                            (node, key, el),
                            GraphAttrsWarning
                        )
                for el in elements_to_remove:
                    graph.node[node][key].remove(el)
    return


def add_edge(graph, s, t, attrs=None, **attr):
    """Add edge."""
    # set up attribute dict (from Networkx to preserve the signature).
    if attrs is None:
        attrs = attr
    else:
        try:
            attrs.update(attr)
        except AttributeError:
            raise ReGraphError(
                "The attr_dict argument must be a dictionary."
            )
    new_attrs = deepcopy(attrs)
    if s not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % s)
    if t not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % t)
    normalize_attrs(new_attrs)

    if graph.is_directed():
        graph.add_edge(s, t, new_attrs)
    else:
        graph.add_edge(s, t)
        graph.edge[s][t] = new_attrs
        graph.edge[t][s] = new_attrs
    # self.unckecked_nodes |= {s, t}


def add_edges_from(graph, edge_list):
    """Add edges from an edge list."""
    for e in edge_list:
        if len(e) == 2:
            add_edge(graph, e[0], e[1])
        elif len(e) == 3:
            add_edge(graph, e[0], e[1], e[2])
        else:
            raise ReGraphError(
                "Was expecting 2 or 3 elements per tuple, got %s." %
                str(len(e))
            )


def remove_edge(graph, source, target):
    """Remove edge from a graph."""
    if graph.is_directed():
        if (source, target) not in graph.edges():
            raise GraphError(
                "Edge '%s->%s' does not exist!" % (str(source), str(target)))
    graph.remove_edge(source, target)


def add_edge_attrs(graph, node_1, node_2, attrs_dict):
    """Add attributes of an edge in a graph."""
    new_attrs = deepcopy(attrs_dict)
    if (node_1, node_2) not in graph.edges():
        raise(
            GraphError("Edge '%s->%s' does not exist" %
                       (str(node_1), str(node_2)))
        )
    elif new_attrs is None:
        pass
    else:
        for key, value in new_attrs.items():
            if key not in graph.edge[node_1][node_2].keys():
                graph.edge[node_1][node_2].update({key: to_set(value)})
            else:
                graph.edge[node_1][node_2][key].update(to_set(value))
            if not graph.is_directed():
                if key not in graph.edge[node_2][node_1].keys():
                    graph.edge[node_2][node_1].update({key: to_set(value)})
                else:
                    graph.edge[node_2][node_1][key].update(to_set(value))
    return


def update_edge_attrs(graph, node_1, node_2, attrs):
    """Update attributes of an edge in a graph."""
    if (node_1, node_2) not in graph.edges():
        raise GraphError("Edge '%s->%s' does not exist!" % (str(node_1), str(node_2)))
    elif attrs is None:
        warnings.warn(
            "You want to update '%s->%s' attrs with an empty attrs_dict" %
            (str(node_1), str(node_2)), GraphAttrsWarning
        )
    else:
        new_attrs = deepcopy(attrs)
        normalize_attrs(new_attrs)
        graph.edge[node_1][node_2] = new_attrs
        if not graph.is_directed():
            graph.edge[node_2][node_1] = new_attrs


def remove_edge_attrs(graph, node_1, node_2, attrs_dict):
    """Remove attributes of an edge in a graph."""
    if (node_1, node_2) not in graph.edges():
        raise GraphError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
    elif attrs_dict is None:
        warnings.warn(
            "You want to remove attrs from %s-%s attrs with an empty attrs_dict" %\
            (str(node_1), str(node_2)), GraphAttrsWarning
        )
    else:

        new_attrs = get_edge(graph, node_1, node_2)
        normalize_attrs(new_attrs)

        for key, value in attrs_dict.items():
            if key not in new_attrs.keys():
                warnings.warn(
                    "Edge %s-%s does not have attribute '%s'" %
                    (str(node_1), str(node_2), str(key)), GraphAttrsWarning)
            else:
                elements_to_remove = []
                for el in to_set(value):
                    if el in new_attrs[key]:
                        elements_to_remove.append(el)
                    else:
                        warnings.warn(
                            "Edge %s-%s does not have attribute '%s' with value '%s'" %
                            (str(node_1), str(node_2), str(key), str(el)), GraphAttrsWarning)
                for el in elements_to_remove:
                    new_attrs[key].remove(el)

                if not graph.is_directed():
                    elements_to_remove = []
                    for el in to_set(value):
                        if el in new_attrs[key]:
                            elements_to_remove.append(el)
                        else:
                            warnings.warn(
                                "Edge %s-%s does not have attribute '%s' with value '%s'" %
                                (str(node_1), str(node_2), str(key), str(el)), GraphAttrsWarning)
                    for el in elements_to_remove:
                        new_attrs[key].remove(el)
        set_edge(graph, node_1, node_2, new_attrs)
    return


def get_edge(graph, u, v):
    """Get edge attrs."""
    if graph.is_directed():
        return graph.edge[u][v]
    else:
        return merge_attributes(graph.edge[u][v], graph.edge[v][u])


def exists_edge(graph, source, target):
    """Check edge exists."""
    if graph.is_directed():
        return(source in graph.edge and target in graph.edge[source])
    else:
        s_t = source in graph.edge and target in graph.edge[source]
        t_s = target in graph.edge and source in graph.edge[target]
        return(s_t and t_s)

    def filter_edges_by_attributes(self, attr_key, attr_cond):
        for (n1, n2) in self.edges():
            if (attr_key not in self.edge[n1][n2].keys() or
               not attr_cond(self.edge[n1][n2][attr_key])):
                print("key:")
                print("attr_key")
                print("attribute:")
                print(self.edge[n1][n2][attr_key])

                self.remove_edge(n1, n2)
        return self


def set_edge(graph, source, target, attrs):
    """Set edge attrs."""
    new_attrs = deepcopy(attrs)
    if not (source, target) in graph.edges():
        raise GraphError(
            "Edge %s->%s does not exist" % (str(source), str(target)))

    normalize_attrs(new_attrs)
    graph.edge[source][target] = new_attrs
    if not graph.is_directed():
        graph.edge[target][source] = new_attrs


def clone_node(graph, node, name=None):
    """Clone existing node and all its edges."""
    if node not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node))

    # generate new name for a clone
    if name is None:
        i = 1
        new_node = str(node) + str(i)
        while new_node in graph.nodes():
            i += 1
            new_node = str(node) + str(i)
    else:
        if name in graph.nodes():
            raise GraphError("Node '%s' already exists!" % str(name))
        else:
            new_node = name

    # part with constraints (?)
    # graph.unckecked_nodes |= set(graph.__getitem__(node).keys())
    graph.add_node(new_node, deepcopy(graph.node[node]))
    # graph.unckecked_nodes |= {new_node}
    # if node in graph.input_constraints.keys():
    #     graph.input_constraints[new_node] = graph.input_constraints[node].deepcopy()

    # Connect all the edges
    if graph.is_directed():
        add_edges_from(
            graph,
            [(n, new_node) for n, _ in graph.in_edges(node)])
        add_edges_from(
            graph,
            [(new_node, n) for _, n in graph.out_edges(node)])

        # Copy the attributes of the edges
        for s, t in graph.in_edges(node):
            graph.edge[s][new_node] = deepcopy(graph.edge[s][t])
        for s, t in graph.out_edges(node):
            graph.edge[new_node][t] = deepcopy(graph.edge[s][t])
    else:
        add_edges_from(
            graph,
            [(n, new_node) for n in graph.neighbors(node)]
        )

        # Copy the attributes of the edges
        for n in graph.neighbors(node):
            graph.edge[new_node][n] = deepcopy(graph.edge[n][node])
            graph.edge[n][new_node] = graph.edge[new_node][n]

    return new_node


def relabel_node(graph, n, new_name):
    """Relabel a node in the graph."""
    clone_node(graph, n, new_name)
    graph.remove_node(n)


def relabel_nodes(graph, mapping):
    """Relabel graph nodes in place.

    Similar to networkx.relabel.relabel_nodes:
    https://networkx.github.io/documentation/development/_modules/networkx/relabel.html
    """
    unique_names = set(mapping.values())
    if len(unique_names) != len(graph.nodes()):
        raise ReGraphError("Attempt to relabel nodes failed: the IDs are not unique!") 

    temp_names = {}
    # Relabeling of the nodes: if at some point new ID conflicts
    # with already existing ID - assign temp ID
    for key, value in mapping.items():
        if key != value:
            if value not in graph.nodes():
                clone_node(graph, key, value)
                remove_node(graph, key)
            else:
                new_name = clone_node(graph, key)
                temp_names[new_name] = value
    # Relabeling the nodes with the temp ID to their new IDs
    for key, value in temp_names:
        if key != value:
            clone_node(graph, key, value)
            remove_node(graph, key)
    return


def get_relabeled_graph(graph, mapping):
    """Return a graph with node labeling specified in the mapping.

    Similar to networkx.relabel.relabel_nodes:
    https://networkx.github.io/documentation/development/_modules/networkx/relabel.html
    """
    g = type(graph)()

    old_nodes = set(mapping.keys())

    for old_node in old_nodes:
        try:
            new_node = mapping[old_node]
        except KeyError:
            continue
        try:
            g.add_node(
                new_node,
                graph.node[old_node])
        except KeyError:
            raise GraphError("Node '%s' does not exist!" % old_node)

    new_edges = list()
    attributes = dict()
    for s, t in graph.edges():
        new_edges.append((
            mapping[s],
            mapping[t]))
        attributes[(mapping[s], mapping[t])] =\
            graph.edge[s][t]

    add_edges_from(g, new_edges)
    for s, t in g.edges():
        # print_graph(g)
        # print(s, t)
        # print(attributes)
        if g.is_directed():
            set_edge(g, s, t, attributes[(s, t)])
        else:
            if (s, t) in attributes.keys():
                set_edge(g, s, t, attributes[(s, t)])
            else:
                set_edge(g, s, t, attributes[(t, s)])
    return g


def merge_nodes(graph, nodes, node_name=None, method="union", edge_method="union"):
    """Merge list of nodes."""
    if len(nodes) == 1:
        if node_name is not None:
            relabel_node(graph, nodes[0], node_name)

    elif len(nodes) > 1:

        if method is None:
            method = "union"

        if edge_method is None:
            method = "union"

        # Generate name for new node
        if node_name is None:
            node_name = "_".join([str(n) for n in nodes])
        elif node_name in graph.nodes() and (node_name not in nodes):
            raise ReGraphError(
                "New name for merged node is not valid: "
                "node with name '%s' already exists!" % node_name
            )

        # Merge data attached to node according to the method specified
        # restore proper connectivity
        if method == "union":
            attr_accumulator = {}
        elif method == "intersection":
            attr_accumulator = deepcopy(graph.node[nodes[0]])
        else:
            raise ReGraphError("Merging method '%s' is not defined!" % method)

        self_loop = False
        self_loop_attrs = {}

        if graph.is_directed():
            source_nodes = set()
            target_nodes = set()

            source_dict = {}
            target_dict = {}
        else:
            neighbors = set()
            neighbors_dict = {}
        all_neighbors = set()

        for node in nodes:
            all_neighbors |= set(graph.__getitem__(node).keys())
            attr_accumulator = merge_attributes(
                attr_accumulator, graph.node[node], method)

            if graph.is_directed():
                in_edges = graph.in_edges(node)
                out_edges = graph.out_edges(node)

                # manage self loops
                for s, t in in_edges:
                    if s in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = graph.edge[s][t]
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                graph.edge[s][t],
                                edge_method)

                for s, t in out_edges:
                    if t in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = graph.edge[s][t]
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                graph.edge[s][t],
                                edge_method)

                source_nodes.update(
                    [n if n not in nodes else node_name
                     for n, _ in in_edges])
                target_nodes.update(
                    [n if n not in nodes else node_name
                     for _, n in out_edges])

                for edge in in_edges:
                    if not edge[0] in source_dict.keys():
                        attrs = graph.edge[edge[0]][edge[1]]
                        source_dict.update({edge[0]: attrs})
                    else:
                        attrs = merge_attributes(
                            source_dict[edge[0]],
                            graph.edge[edge[0]][edge[1]],
                            edge_method)
                        source_dict.update({edge[0]: attrs})

                for edge in out_edges:
                    if not edge[1] in target_dict.keys():
                        attrs = graph.edge[edge[0]][edge[1]]
                        target_dict.update({edge[1]: attrs})
                    else:
                        attrs = merge_attributes(
                            target_dict[edge[1]],
                            graph.edge[edge[0]][edge[1]],
                            edge_method)
                        target_dict.update({edge[1]: attrs})
            else:
                for n in graph.neighbors(node):
                    if n in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = graph.edge[n][node]
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                graph.edge[n][node],
                                edge_method)

                neighbors.update(
                    [n for n in graph.neighbors(node) if n not in nodes])
                for n in graph.neighbors(node):
                    if n not in nodes:
                        if n not in neighbors_dict.keys():
                            attrs = graph.edge[n][node]
                            neighbors_dict.update({n: attrs})
                        else:
                            attrs = merge_attributes(
                                neighbors_dict[n],
                                graph.edge[n][node],
                                edge_method)
                            neighbors_dict.update({n: attrs})

            graph.remove_node(node)
            all_neighbors -= {node}

        add_node(graph, node_name, attr_accumulator)
        all_neighbors.add(node_name)

        # (???)
        # graph.unckecked_nodes |= all_neighbors

        if graph.is_directed():
            if self_loop:
                add_edges_from(graph, [(node_name, node_name)])
                graph.edge[node_name][node_name] = self_loop_attrs

            add_edges_from(graph, [(n, node_name) for n in source_nodes])
            add_edges_from(graph, [(node_name, n) for n in target_nodes])

            # Attach accumulated attributes to edges
            for node, attrs in source_dict.items():
                if node not in nodes:
                    graph.edge[node][node_name] = attrs
            for node, attrs in target_dict.items():
                if node not in nodes:
                    graph.edge[node_name][node] = attrs
        else:
            if self_loop:
                add_edges_from(graph, [(node_name, node_name)])
                graph.edge[node_name][node_name] = self_loop_attrs

            add_edges_from(graph, [(n, node_name) for n in neighbors])

            # Attach accumulated attributes to edges
            for node, attrs in neighbors_dict.items():
                if node not in nodes:
                    graph.edge[node][node_name] = attrs
                    graph.edge[node_name][node] = attrs

        return node_name


def subtract(a, b, ba_mapping):
    """Return a graph difference between A and B having B-> A mapping."""
    res = type(a)()
    f = ba_mapping

    for n in a.nodes():
        if n not in f.values():
            add_node(res,
                     n,
                     a.node[n])
    for (n1, n2) in a.edges():
        if n1 in res.nodes() and n2 in res.nodes():
            b_keys_1 = keys_by_value(f, n1)
            b_keys_2 = keys_by_value(f, n2)
            if len(b_keys_1) == 0 or len(b_keys_2) == 0:
                add_edge(res, n1, n2, get_edge(a, n1, n2))
            else:
                for k1 in b_keys_1:
                    for k2 in b_keys_2:
                        if (k1, k2) not in b.edges():
                            add_edge(res,
                                     n1,
                                     n2,
                                     get_edge(a, n1, n2))
    return res


def append_to_node_names(graph, token):
    """Append a token to the node names."""
    relabel_nodes(
        graph,
        {n: (str(n) + "_" + str(token)) for n in graph.nodes()}
    )


def graph_from_json(j_data, directed=True):
    """Create a graph from a python dictionary."""
    loaded_nodes = []
    if "nodes" in j_data.keys():
        j_nodes = j_data["nodes"]
        for node in j_nodes:
            if "id" in node.keys():
                node_id = node["id"]
            else:
                raise ReGraphError(
                    "Error loading graph: node id is not specified!")
            attrs = None
            if "attrs" in node.keys():
                attrs = node["attrs"]
            loaded_nodes.append((node_id, attrs))
    else:
        raise ReGraphError(
            "Error loading graph: no nodes specified!")
    loaded_edges = []
    if "edges" in j_data.keys():
        j_edges = j_data["edges"]
        for edge in j_edges:
            if "from" in edge.keys():
                s_node = edge["from"]
            else:
                raise ReGraphError(
                    "Error loading graph: edge source is not specified!")
            if "to" in edge.keys():
                t_node = edge["to"]
            else:
                raise ReGraphError(
                    "Error loading graph: edge target is not specified!")
            if "attrs" in edge.keys():
                attrs = edge["attrs"]
                if type(attrs) == list:
                    attrs = set(attrs)
                loaded_edges.append((s_node, t_node, attrs))
            else:
                loaded_edges.append((s_node, t_node))
    if directed:
        graph = nx.DiGraph()
    else:
        graph = nx.Graph()
    add_nodes_from(graph, loaded_nodes)
    add_edges_from(graph, loaded_edges)
    return graph


def load_graph(filename, directed=True):
    """Create graph from JSON or XML file."""
    if os.path.isfile(filename):
        with open(filename, "r+") as f:
            j_data = json.loads(f.read())
            return graph_from_json(j_data, directed)
    else:
        raise ReGraphError(
            "Error loading graph: file '%s' does not exist!" %
            filename
        )


def graph_to_json(graph):
    """Create Python dict from a graph."""
    j_data = {"edges": [], "nodes": []}
    # dump nodes
    for node in graph.nodes():
        node_data = {}
        node_data["id"] = node
        # node_data["input_constraints"] =\
        #     [viewable_cond for (_, (_, viewable_cond)) in self.input_constraints.get(node,[])]
        # node_data["output_constraints"] =\
        #     [viewable_cond for (_, (_, viewable_cond)) in self.output_constraints.get(node,[])]
        if graph.node[node] is not None:
            attrs = {}
            for key, value in graph.node[node].items():
                if type(value) == set:
                    attrs[key] = list(value)
                else:
                    attrs[key] = value
            node_data["attrs"] = attrs
        j_data["nodes"].append(node_data)
    # dump edges
    for s, t in graph.edges():
        edge_data = {}
        edge_data["from"] = s
        edge_data["to"] = t
        if graph.edge[s][t] is not None:
            attrs = {}
            for key, value in graph.edge[s][t].items():
                if type(value) == set:
                    attrs[key] = list(value)
                else:
                    attrs[key] = value
            edge_data["attrs"] = attrs
        j_data["edges"].append(edge_data)
    return j_data


def export_graph(graph, filename):
    """Export graph to JSON or XML file."""
    with open(filename, 'w') as f:
        j_data = graph_to_json(graph)
        json.dump(j_data, f)
    return


def find_matching(graph, pattern, ignore_attrs=False):
    """Find matching of a pattern in a graph."""
    labels_mapping = dict([(n, i + 1) for i, n in enumerate(graph.nodes())])
    g = get_relabeled_graph(graph, labels_mapping)
    matching_nodes = set()

    # find all the nodes matching the nodes in pattern
    for pattern_node in pattern.nodes():
        for node in g.nodes():
            if ignore_attrs or is_subdict(pattern.node[pattern_node], g.node[node]):
                matching_nodes.add(node)
    reduced_graph = g.subgraph(matching_nodes)
    instances = []
    isomorphic_subgraphs = []
    for sub_nodes in itertools.combinations(reduced_graph.nodes(),
                                            len(pattern.nodes())):
        subg = reduced_graph.subgraph(sub_nodes)
        for edgeset in itertools.combinations(subg.edges(),
                                              len(pattern.edges())):
            if g.is_directed():
                edge_induced_graph = nx.DiGraph(list(edgeset))
                edge_induced_graph.add_nodes_from(
                    [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                matching_obj = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
                for isom in matching_obj.isomorphisms_iter():
                    isomorphic_subgraphs.append((subg, isom))
            else:
                edge_induced_graph = nx.Graph(edgeset)
                edge_induced_graph.add_nodes_from(
                    [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                matching_obj = isomorphism.GraphMatcher(pattern, edge_induced_graph)
                for isom in matching_obj.isomorphisms_iter():
                    isomorphic_subgraphs.append((subg, isom))

    for subgraph, mapping in isomorphic_subgraphs:
        # check node matches
        # exclude subgraphs which nodes information does not
        # correspond to pattern
        for (pattern_node, node) in mapping.items():
            if not ignore_attrs and\
               not is_subdict(pattern.node[pattern_node], subgraph.node[node]):
                break
        else:
            # check edge attribute matched
            for edge in pattern.edges():
                pattern_attrs = get_edge(pattern, edge[0], edge[1])
                target_attrs = get_edge(subgraph, mapping[edge[0]], mapping[edge[1]])
                if not ignore_attrs and not is_subdict(pattern_attrs, target_attrs):
                    break
            else:
                instances.append(mapping)

    # bring back original labeling
    inverse_mapping = dict(
        [(value, key) for key, value in labels_mapping.items()]
    )
    for instance in instances:
        for key, value in instance.items():
            instance[key] = inverse_mapping[value]
    return instances


def rewrite(graph, instance, rule, inplace=True):
    """Rewrite an instance of a rule in a graph."""
    p_g_m = {}

    if not inplace:
        g = deepcopy(graph)
    else:
        g = graph

    # Remove/clone nodes
    for n in rule.lhs.nodes():
        p_keys = keys_by_value(rule.p_lhs, n)
        # Remove nodes
        if len(p_keys) == 0:
            remove_node(g, instance[n])
        # Keep nodes
        elif len(p_keys) == 1:
            p_g_m[p_keys[0]] = instance[n]
        # Clone nodes
        else:
            i = 1
            for k in p_keys:
                if i == 1:
                    p_g_m[k] = instance[n]
                else:
                    new_name = clone_node(g, instance[n])
                    p_g_m[k] = new_name
                i += 1

    # Remove edges
    for (n1, n2) in rule.lhs.edges():
        p_keys_1 = keys_by_value(rule.p_lhs, n1)
        p_keys_2 = keys_by_value(rule.p_lhs, n2)
        if len(p_keys_1) > 0 and len(p_keys_2) > 0:
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    if g.is_directed():
                        if (k1, k2) not in rule.p.edges():
                            if (p_g_m[k1], p_g_m[k2]) in g.edges():
                                remove_edge(g, p_g_m[k1], p_g_m[k2])
                    else:
                        if (k1, k2) not in rule.p.edges() and (k2, k1) not in rule.p.edges():
                            if (p_g_m[k1], p_g_m[k2]) in g.edges() or\
                               (p_g_m[k2], p_g_m[k1]) in g.edges():
                                remove_edge(g, p_g_m[k1], p_g_m[k2])
    # Remove node attrs
    for n in rule.p.nodes():
        attrs_to_remove = dict_sub(
            rule.lhs.node[rule.p_lhs[n]],
            rule.p.node[n]
        )
        remove_node_attrs(g, p_g_m[n], attrs_to_remove)

    # Remove edge attrs
    for (n1, n2) in rule.p.edges():
        attrs_to_remove = dict_sub(
            get_edge(rule.lhs, rule.p_lhs[n1], rule.p_lhs[n2]),
            get_edge(rule.p, n1, n2)
        )
        remove_edge_attrs(g, p_g_m[n1], p_g_m[n2], attrs_to_remove)

    # Add/merge nodes
    rhs_g_prime = {}
    for n in rule.rhs.nodes():
        p_keys = keys_by_value(rule.p_rhs, n)
        # Add nodes
        if len(p_keys) == 0:
            add_node(
                g,
                n,
                rule.rhs.node[n])
            rhs_g_prime[n] = n
        # Keep nodes
        elif len(p_keys) == 1:
            rhs_g_prime[rule.p_rhs[p_keys[0]]] = p_g_m[p_keys[0]]
        # Merge nodes
        else:
            nodes_to_merge = []
            for k in p_keys:
                nodes_to_merge.append(p_g_m[k])
            new_name = merge_nodes(g, nodes_to_merge)
            rhs_g_prime[n] = new_name

    # Add edges
    for (n1, n2) in rule.rhs.edges():
        if g.is_directed():
            if (rhs_g_prime[n1], rhs_g_prime[n2]) not in g.edges():
                add_edge(
                    g,
                    rhs_g_prime[n1],
                    rhs_g_prime[n2],
                    get_edge(rule.rhs, n1, n2))
        else:
            if (rhs_g_prime[n1], rhs_g_prime[n2]) not in g.edges() and\
               (rhs_g_prime[n2], rhs_g_prime[n1]) not in g.edges():
                add_edge(
                    g,
                    rhs_g_prime[n1],
                    rhs_g_prime[n2],
                    get_edge(rule.rhs, n1, n2)
                )

    # Add node attrs
    for n in rule.rhs.nodes():
        p_keys = keys_by_value(rule.p_rhs, n)
        # Add attributes to the nodes which stayed invariant
        if len(p_keys) == 1:
            attrs_to_add = dict_sub(
                rule.rhs.node[n],
                rule.p.node[p_keys[0]]
            )
            add_node_attrs(g, rhs_g_prime[n], attrs_to_add)
        # Add attributes to the nodes which were merged
        elif len(p_keys) > 1:
            merged_attrs = {}
            for k in p_keys:
                merged_attrs = merge_attributes(
                    merged_attrs,
                    rule.p.node[k]
                )
            attrs_to_add = dict_sub(rule.rhs.node[n], merged_attrs)
            add_node_attrs(g, rhs_g_prime[n], attrs_to_add)

    # Add edge attrs
    for (n1, n2) in rule.rhs.edges():
        p_keys_1 = keys_by_value(rule.p_rhs, n1)
        p_keys_2 = keys_by_value(rule.p_rhs, n2)
        for k1 in p_keys_1:
            for k2 in p_keys_2:
                if g.is_directed():
                    if (k1, k2) in rule.p.edges():
                        attrs_to_add = dict_sub(
                            get_edge(rule.rhs, n1, n2),
                            get_edge(rule.p, k1, k2)
                        )
                        add_edge_attrs(
                            g,
                            rhs_g_prime[n1],
                            rhs_g_prime[n2],
                            attrs_to_add
                        )
                else:
                    if (k1, k2) in rule.p.edges() or (k2, k1) in rule.p.edges():
                        attrs_to_add = dict_sub(
                            get_edge(rule.rhs, n1, n2),
                            get_edge(rule.p, k1, k2)
                        )
                        add_edge_attrs(
                            g,
                            rhs_g_prime[n1],
                            rhs_g_prime[n2],
                            attrs_to_add
                        )
    if inplace:
        return rhs_g_prime
    else:
        return (g, rhs_g_prime)


def print_graph(graph):
    """Util for nx graphs printing."""
    print("\nNodes:\n")
    for n in graph.nodes():
        print(n, " : ", graph.node[n])
    print("\nEdges:\n")
    for (n1, n2) in graph.edges():
        print(n1, '->', n2, ' : ', graph.edge[n1][n2])
    return


def equal(graph1, graph2):
    """Eqaulity of two graphs."""
    if set(graph1.nodes()) != set(graph2.nodes()):
        return False
    if set(graph1.edges()) != set(graph2.edges()):
        return False
    for node in graph1.nodes():
        normalize_attrs(graph1.node[node])
        normalize_attrs(graph2.node[node])
        if graph1.node[node] != graph2.node[node]:
            return False
    for s, t in graph1.edges():
        normalize_attrs(get_edge(graph1, s, t))
        normalize_attrs(get_edge(graph2, s, t))
        if get_edge(graph1, s, t) != get_edge(graph2, s, t):
            return False
    return True


def find_match(graph, pattern, graph_typings, pattern_typings, typing_graphs,
               decr_types=False):
    """
    graph_typings = dictionnary of typings of the graph
    pattern_typings = dictionnary of typings of the pattern
    typing_graph = dictionnary of the graphs typing the pattern

    networkX can only look at nodes attributes to compare them
    so we put the typings inside during matching
    we assume that no key is named:
    regraph_tmp_typings_key_that_you_should_not_use
    """
    typing_key = "regraph_tmp_typings_key_that_you_should_not_use"

    def _allowed_edge(source, target, typings):
        for (typ_id, typ_map) in typings.items():
            if typ_id not in typing_graphs.keys():
                raise ValueError("typing graph or pattern not in typing_graphs")
            typ_gr = typing_graphs[typ_id]
            if (source in typ_map.keys() and
                    target in typ_map.keys() and
                    typ_map[target] not in typ_gr.successors(typ_map[source])):
                return False
        return True

    may_edges = [edge for edge in itertools.product(pattern.nodes(),
                                                    pattern.nodes())
                 if (_allowed_edge(*edge, pattern_typings) and
                     edge not in pattern.edges())]
    may_edges_subsets = itertools.chain.from_iterable(
        itertools.combinations(may_edges, r) for r in range(len(may_edges)+1))

    def _put_typings_in_attrs(gr, typings):
        for (node, (typ_id, typ_map)) in\
                itertools.product(gr.nodes(), typings.items()):
            if node in typ_map.keys():
                add_node_attrs(
                    gr, node, {typing_key: (typ_id, typ_map[node])})

    _put_typings_in_attrs(pattern, pattern_typings)
    _put_typings_in_attrs(graph, graph_typings)

    if decr_types:
        def _compare_dicts(d1, d2):
            types1 = d1[typing_key]
            types2 = d2[typing_key]
            d1_without_types = copy.copy(d1)
            d2_without_types = copy.copy(d1)
            del d1_without_types[typing_key]
            del d2_without_types[typing_key]
            return (valid_attributes(types2, types1) and
                    valid_attributes(d1_without_types, d2_without_types))

    else:
        def _compare_dicts(d1, d2):
            return valid_attributes(d2, d1)

    matchings = []
    for added_edges in may_edges_subsets:
        pat = copy.deepcopy(pattern)
        pat.add_edges_from(added_edges)
        if graph.is_directed():
            matcher = isomorphism.DiGraphMatcher(graph, pat, _compare_dicts,
                                                 _compare_dicts)
        else:
            matcher = isomorphism.GraphMatcher(graph, pat, _compare_dicts,
                                               _compare_dicts)
        for sub in matcher.subgraph_isomorphisms_iter():
            matchings.append({v: k for (k, v) in sub.items()})

    def _remove_typings_in_attrs(gr):
        for node in gr.nodes():
            if typing_key in gr.node[node].keys():
                del gr.node[node][typing_key]

    _remove_typings_in_attrs(graph)
    _remove_typings_in_attrs(pattern)
    print(matchings)
    return matchings


def maximal_machings(gr):
    """ not the same matchings (couplage in french)"""
    return set(map(frozenset, _naive_maximal_machings(gr)))


def _naive_maximal_machings(gr):
    matchings = []
    for (source, target) in gr.edges():
        gr_copy = copy.copy(gr)
        remove_node(gr_copy, source)
        remove_node(gr_copy, target)
        submatchings = _naive_maximal_machings(gr_copy)
        matchings += [subm.add((source, target)) for subm in submatchings]
    return matchings

