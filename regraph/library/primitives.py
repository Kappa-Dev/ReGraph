"""Defines primitives for graph transformation."""
import warnings
from copy import deepcopy


def cast_node(graph, node, new_type):
    """Change the node type in the TypedGraph."""
    graph.node[node].type_ = new_type


def merge_attributes(attr1, attr2, method="union"):
    """Merge two dictionaries of attributes."""
    result = {}
    if method == "union":
        for key1 in attr1.keys():
            if key1 in attr2.keys():
                if attr1[key1] == attr2[key1]:
                    result.update(
                        {key1: attr1[key1]})
                else:
                    attr_set = set()
                    if type(attr1[key1]) == set:
                        attr_set.update(attr1[key1])
                    else:
                        attr_set.add(attr1[key1])
                    if type(attr2[key1]) == set:
                        attr_set.update(attr2[key1])
                    else:
                        attr_set.add(attr2[key1])
                    result.update(
                        {key1: attr_set})
            else:
                result.update({key1: attr1[key1]})

        for key2 in attr2.keys():
            if key2 not in result:
                result.update({key2: attr2[key2]})
    elif method == "intersection":
        for key1 in attr1.keys():
            if key1 in attr2.keys():
                if attr1[key1] == attr2[key1]:
                    result.update(
                        {key1: attr1[key1]})
                else:
                    attr_set1 = set()
                    attr_set2 = set()
                    if type(attr1[key1]) == set:
                        attr_set1.update(attr1[key1])
                    else:
                        attr_set1.add(attr1[key1])
                    if type(attr2[key1]) == set:
                        attr_set2.update(attr2[key1])
                    else:
                        attr_set2.add(attr2[key1])
                    intersect = set.intersection(attr_set1, attr_set2)
                    if len(intersect) == 1:
                        result.update({key1: list(intersect)[0]})
                    elif len(intersect) > 1:
                        result.update({key1: intersect})
    else:
        raise ValueError("Merging method %s is not defined!" % method)
    return result


def merge_nodes(graph, nodes, method="union",
                node_name=None, edge_method="union"):
    """Merge list of nodes."""
    # Type checking
    node_type = graph.node[nodes[0]].type_
    for node in nodes:
        if graph.node[node].type_ != node_type:
            raise ValueError(
                "Merge error: Non consistent node types ('%s', '%s')!" %
                (str(graph.node[node].type_), str(node_type)))

    if method is None:
        method = "union"

    if edge_method is None:
        method = "union"

    # Generate name for new node
    if node_name is None:
        node_name = "_".join([str(n) for n in nodes])
    elif node_name in graph.nodes():
        raise ValueError(
            "The node with name '%s' already exists!" % str(node_name))

    # Merge data attached to node according to the method specified
    # restore proper connectivity
    if method == "union":
        attr_accumulator = {}
    elif method == "intersection":
        attr_accumulator = deepcopy(graph.node[nodes[0]].attrs_)
    else:
        raise ValueError("Merging method %s is not defined!" % method)

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

    for node in nodes:

        attr_accumulator = merge_attributes(
            attr_accumulator, graph.node[node].attrs_, method)

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

    graph.add_node(node_name, node_type, attr_accumulator)

    if graph.is_directed():
        if self_loop:
            graph.add_edges_from([(node_name, node_name)])
            graph.edge[node_name][node_name] = self_loop_attrs

        graph.add_edges_from([(n, node_name) for n in source_nodes])
        graph.add_edges_from([(node_name, n) for n in target_nodes])

        # Attach accumulated attributes to edges
        for node, attrs in source_dict.items():
            if node not in nodes:
                graph.edge[node][node_name] = attrs
        for node, attrs in target_dict.items():
            if node not in nodes:
                graph.edge[node_name][node] = attrs
    else:
        if self_loop:
            graph.add_edges_from([(node_name, node_name)])
            graph.set_edge(node_name, node_name, self_loop_attrs)

        graph.add_edges_from([(n, node_name) for n in neighbors])

        # Attach accumulated attributes to edges
        for node, attrs in neighbors_dict.items():
            if node not in nodes:
                graph.set_edge(node, node_name, attrs)

    return node_name


def clone_node(graph, node, name=None):
    """Clone existing node and all its edges."""
    if node not in graph.nodes():
        raise ValueError("Node %s does not exist" % str(node))

    if name is None:
        new_node = "%s_copy" % str(node)
        while new_node in graph.nodes():
            new_node = "%s_copy" % new_node
    else:
        if name in graph.nodes():
            raise ValueError("Node %s already exist!" % str(name))
        else:
            new_node = name

    graph.add_node(new_node, graph.node[node].type_,
                   deepcopy(graph.node[node].attrs_))

    # Connect all the edges
    if graph.is_directed():
        graph.add_edges_from(
            [(n, new_node) for n, _ in graph.in_edges(node)])
        graph.add_edges_from(
            [(new_node, n) for _, n in graph.out_edges(node)])

        # Copy the attributes of the edges
        for s, t in graph.in_edges(node):
            graph.edge[s][new_node] = deepcopy(graph.edge[s][t])
        for s, t in graph.out_edges(node):
            graph.edge[new_node][t] = deepcopy(graph.edge[s][t])
    else:
        graph.add_edges_from(
            [(n, new_node) for n in graph.neighbors(node)])

        # Copy the attributes of the edges
        for n in graph.neighbors(node):
            graph.set_edge(new_node, n, deepcopy(graph.edge[n][node]))

    return new_node


def add_node(graph, node_type, name=None, attrs={}):
    """Add new node to the graph."""
    if name is not None:
        new_name = name
    else:
        i = 0
        new_name = "new_node_%d" % i
        while new_name in graph.nodes():
            i += 1
            new_name = "new_node_%d" % i
    if new_name not in graph.nodes():
        graph.add_node(new_name, node_type, attrs)
    else:
        raise ValueError("Node %s already exists!" % str(new_name))
    return new_name


def remove_node(graph, node):
    """Remove node from the graph."""
    if node in graph.nodes():
        graph.remove_node(node)
    else:
        raise ValueError("Node %s does not exist!" % str(node))
    return


def add_edge(graph, source, target, attrs={}):
    """Add edge to the graph."""
    if graph.is_directed(): 
        if not (source, target) in graph.edges():
            if source not in graph.nodes():
                raise ValueError("Node %s does not exist" % str(source))
            if target not in graph.nodes():
                raise ValueError("Node %s does not exist" % str(target))
            graph.add_edge(source, target)
            graph.edge[source][target] = attrs
        else:
            raise ValueError(
                "Edge %s-%s already exists" % (str(source), str(target)))
    else:
        if (source, target) not in graph.edges() and (target, source) not in graph.edges():
            if source not in graph.nodes():
                raise ValueError("Node %s does not exist" % str(source))
            if target not in graph.nodes():
                raise ValueError("Node %s does not exist" % str(target))
            graph.add_edge(source, target)
            graph.edge[source][target] = attrs
            graph.edge[target][source] = attrs
        else:
            raise ValueError(
                "Edge %s-%s already exists" % (str(source), str(target)))
        return


def remove_edge(graph, source, target):
    """Remove edge from the graph."""
    if graph.is_directed():
        if (source, target) in graph.edges():
            graph.remove_edge(source, target)
        else:
            raise ValueError(
                "Edge %s->%s does not exist!" % (str(source), str(target)))
    else:
        if (source, target) in graph.edges() or (target, source) in graph.edges():
            graph.remove_edge(source, target)
        else:
            raise ValueError(
                "Edge %s->%s does not exist!" % (str(source), str(target))) 
    return


def add_node_attrs(graph, node, attrs_dict):
    if node not in graph.nodes():
        raise ValueError("Node %s does not exist" % str(node))
    else:
        for key, value in attrs_dict.items():
            if key not in graph.node[node].attrs_.keys():
                graph.node[node].attrs_.update({key: value})
            else:
                if type(value) != set:
                    value = set([value])
                if type(graph.node[node].attrs_[key]) != set:
                    graph.node[node].attrs_[key] =\
                        set([graph.node[node].attrs_[key]])
                graph.node[node].attrs_[key].update(value)


def remove_node_attrs(graph, node, attrs_dict):
    if node not in graph.nodes():
        raise ValueError("Node %s does not exist" % str(node))
    else:
        for key, value in attrs_dict.items():
            if key not in graph.node[node].attrs_.keys():
                warnings.warn(
                    "Node %s does not have attribute '%s'" % (str(node), str(key)), RuntimeWarning)
            else:
                if type(value) != set:
                    value = set([value])
                if type(graph.node[node].attrs_[key]) != set:
                    graph.node[node].attrs_[key] =\
                        set([graph.node[node].attrs_[key]])
                for el in value:
                    if el in graph.node[node].attrs_[key]:
                        graph.node[node].attrs_[key].remove(el)
                    else:
                        warnings.warn(
                            "Node %s does not have attribute '%s' with value '%s'" %
                            (str(node), str(key), str(el)), RuntimeWarning)


def add_edge_attrs(graph, node_1, node_2, attrs_dict):
    if graph.is_directed():
        if (node_1, node_2) not in graph.edges():
            raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
        else:
            for key, value in attrs_dict.items():
                if key not in graph.edge[node_1][node_2].keys():
                    graph.edge[node_1][node_2].update({key: value})
                else:
                    if type(value) != set:
                        value = set([value])
                    if type(graph.edge[node_1][node_2][key]) != set:
                        graph.edge[node_1][node_2][key] =\
                            set([graph.edge[node_1][node_2][key]])
                    graph.edge[node_1][node_2][key].update(value)
    else:
        if (node_1, node_2) not in graph.edges() and (node_2, node_1) not in graph.edges():
            raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
        else:
            for key, value in attrs_dict.items():
                if key not in graph.edge[node_1][node_2].keys():
                    graph.edge[node_1][node_2].update({key: value})
                    graph.edge[node_2][node_1].update({key: value})
                else:
                    print(graph.edge[node_1][node_2][key])
                    if type(value) != set:
                        value = set([value])
                    if type(graph.edge[node_1][node_2][key]) != set:
                        graph.edge[node_1][node_2][key] =\
                            set([graph.edge[node_1][node_2][key]])
                        graph.edge[node_2][node_1][key] =\
                            set([graph.edge[node_2][node_1][key]])
                    graph.edge[node_1][node_2][key].update(value)
                    graph.edge[node_2][node_1][key].update(value)
                    print(graph.edge[node_1][node_2][key])


def remove_edge_attrs(graph, node_1, node_2, attrs_dict):
    if (node_1, node_2) not in graph.edges() and (node_2, node_1) not in graph.edges():
        raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
    else:
        for key, value in attrs_dict.items():
            if key not in graph.edge[node_1][node_2].keys():
                warnings.warn(
                    "Edge %s-%s does not have attribute '%s'" %
                    (str(node_1), str(node_2), str(key)), RuntimeWarning)
            else:
                if type(value) != set:
                    value = set([value])
                if type(graph.edge[node_1][node_2][key]) != set:
                    graph.edge[node_1][node_2][key] =\
                        set([graph.edge[node_1][node_2][key]])
                    if not graph.is_directed():
                        graph.edge[node_2][node_1][key] =\
                            set([graph.edge[node_2][node_1][key]])
                for el in value:
                    if el in graph.edge[node_1][node_2][key]:
                        graph.edge[node_1][node_2][key].remove(el)
                    else:
                        warnings.warn(
                            "Edge %s-%s does not have attribute '%s' with value '%s'" %
                            (str(node_1), str(node_2), str(key), str(el)), RuntimeWarning)


def update_node_attrs(graph, node, new_attrs):
    if node not in graph.nodes():
        raise ValueError("Node %s does not exist" % str(node))
    else:
        for key, value in new_attrs.items():
            graph.node[node].attrs_[key] = value


def update_edge_attrs(graph, node_1, node_2, new_attrs):
    if (node_1, node_2) not in graph.edges() and (node_2, node_1) not in graph.edges():
        raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
    else:
        for key, value in new_attrs.items():
            graph.edge[node_1][node_2][key] = value
            if not graph.is_directed():
                graph.edge[node_2][node_1][key] = value
