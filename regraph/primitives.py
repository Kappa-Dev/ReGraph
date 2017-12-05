"""Graph transformation primitives.

This package contains a collection of utils for various transformations on
`networkx.(Di)Graph` objects. Attributes: `regraph.attribute_sets`
"""

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
                           keys_by_value,
                           json_dict_to_attrs)
from regraph.exceptions import (ReGraphError,
                                GraphError,
                                GraphAttrsWarning)
from regraph.attribute_sets import FiniteSet


def add_node(graph, node_id, attrs=None):
    """Add a node to a graph.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_id : hashable
        Prefix that is prepended to the new unique name.
    attrs : dict, optional
        Node attributes.

    Raises
    -------
    regraph.exceptions.GraphError
        Raises an error if node already exists in the graph.
    """
    new_attrs = deepcopy(attrs)
    if new_attrs is None:
        new_attrs = dict()
    if node_id not in graph.nodes():
        graph.add_node(node_id)
        normalize_attrs(new_attrs)
        graph.node[node_id] = new_attrs
    else:
        raise GraphError("Node '%s' already exists!" % node_id)


def add_nodes_from(graph, node_list):
    """Add nodes from a node list.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_list : iterable
        Iterable containing a collection of nodes, optionally,
        with their attributes


    Examples
    --------
    >>> import networkx as nx
    >>> from regraph.primitives import add_nodes_from
    >>> G = nx.Graph()
    >>> add_nodes_from(G, [1, (2, {"a": 1}), 3])
    """
    for n in node_list:
        try:
            node_id, node_attrs = n
            add_node(graph, node_id, node_attrs)
        except (TypeError, ValueError) as e:
            add_node(graph, n)


def add_node_attrs(graph, node, attrs):
    """Add new attributes to a node.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node : hashable
        Id of a node to add attributes to.
    attrs : dict
        Attributes to add.

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.
    """
    if node not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node))
    normalize_attrs(attrs)
    node_attrs = graph.node[node]
    if node_attrs is None:
        graph.node[node] = copy.deepcopy(attrs)
    else:
        for key in attrs:
            if key in node_attrs:
                # node_attrs[key] = hyb_union(node_attrs[key], attrs_dict[key])
                node_attrs[key] = node_attrs[key].union(attrs[key])
            else:
                node_attrs[key] = attrs[key]


def add_edge(graph, s, t, attrs=None, **attr):
    """Add an edge to a graph.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dict
        Edge attributes.

    Raises
    ------
    ReGraphError
        If `attrs` is not a dictionary
    GraphError
        If either one of the nodes does not exist in the graph or
        an edge between `s` and `t` already
        exists.
    """
    # Set up attribute dict (from Networkx to preserve the signature).
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
        if (s, t) in graph.edges():
            raise GraphError(
                "Edge '%s'->'%s' already exists!" %
                (s, t)
            )
        graph.add_edge(s, t, new_attrs)
    else:
        if (s, t) in graph.edges() or (t, s) in graph.edges():
            raise GraphError(
                "Edge '%s'->'%s' already exists!" %
                (s, t)
            )
        graph.add_edge(s, t)
        graph.edge[s][t] = new_attrs
        graph.edge[t][s] = new_attrs


def remove_edge(graph, s, t):
    """Remove edge from a graph.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.

    Raises
    ------
    GraphError
        If edge between `s` and `t` does not exist.

    """
    if graph.is_directed():
        if (s, t) not in graph.edges():
            raise GraphError(
                "Edge '%s->%s' does not exist!" % (str(s), str(t)))
    graph.remove_edge(s, t)


def add_edges_from(graph, edge_list):
    """Add edges from an edge list.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    edge_list : iterable
        Iterable containing a collection of edges, optionally,
        with their attributes

    Raises
    ------
    ReGraphError
        If an element of the collection is neither a tuple of size 2
        (containing a source and a target of an edge), not a tuple
        of size 3 (containing a source, a target and attributes of an edge).

    Examples
    --------
    >>> import networkx as nx
    >>> from regraph.primitives import add_nodes_from, add_edges_from
    >>> G = nx.Graph()
    >>> add_nodes_from(G, [1, 2, 3])
    >>> add_edges_from(G, [(1, 2), (2, 3, {"a": 1})])

    """
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


def copy_node(graph, node_id):
    """Copy node.

    Create a copy of a node in a graph. A new id for the copy is
    generated by regraph.primitives.unique_node_id.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_id : hashable, node to copy.

    Returns
    -------
    new_name
        Id of the copy node.

    """
    new_name = unique_node_id(graph, node_id)
    add_node(graph, new_name, graph.node[node_id])
    return new_name


def add_node_new_id(graph, node_id, attrs=None):
    """Create a new node id if node_id already exists."""
    new_id = unique_node_id(graph, node_id)
    add_node(graph, new_id, attrs)
    return new_id


def remove_node(graph, node_id):
    """Remove node.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_id : hashable, node to remove.

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.

    """
    if node_id in graph.nodes():
        neighbors = set(graph.__getitem__(node_id).keys())
        neighbors -= {node_id}
        graph.remove_node(node_id)
    else:
        raise GraphError("Node %s does not exist!" % str(node_id))
    return


def update_node_attrs(graph, node_id, attrs):
    """Update attributes of a node.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_id : hashable, node to update.
    attrs : dict
        New attributes to assign to the node

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.

    """
    new_attrs = deepcopy(attrs)
    if node_id not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node_id))
    elif new_attrs is None:
        warnings.warn(
            "You want to update '%s' attrs with an empty attrs_dict!" % node_id,
            GraphAttrsWarning
        )
    else:
        normalize_attrs(new_attrs)
        graph.node[node_id] = new_attrs


def remove_node_attrs(graph, node_id, attrs):
    """Remove attrs of a node specified by attrs_dict.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_id : hashable
        Node whose attributes to remove.
    attrs : dict
        Dictionary with attributes to remove.

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.
    """
    if node_id not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node_id))
    elif attrs is None:
        warnings.warn(
            "You want to remove attrs from '%s' with an empty attrs_dict!" %
            node_id,
            GraphAttrsWarning
        )
    elif graph.node[node_id] is None:
        warnings.warn(
            "Node '%s' does not have any attribute!" %
            node_id, GraphAttrsWarning
        )
    else:
        normalize_attrs(attrs)
        old_attrs = graph.node[node_id]
        for key, value in attrs.items():
            if key in old_attrs:
                new_set = old_attrs[key].difference(value)
                if not new_set:
                    del old_attrs[key]
                else:
                    old_attrs[key] = new_set


def add_edge_attrs(graph, s, t, attrs):
    """Add attributes of an edge in a graph.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dict
        Dictionary with attributes to remove.

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    new_attrs = deepcopy(attrs)
    if not graph.has_edge(s, t):
        raise(
            GraphError("Edge '%s->%s' does not exist" %
                       (str(s), str(t)))
        )
    elif new_attrs is None:
        pass
    else:
        normalize_attrs(new_attrs)
        edge_attrs = get_edge(graph, s, t)
        for key, value in new_attrs.items():
            if key in edge_attrs:
                edge_attrs[key] = edge_attrs[key].union(value)
            else:
                edge_attrs[key] = value
        set_edge(graph, s, t, edge_attrs)


def update_edge_attrs(graph, s, t, attrs):
    """Update attributes of an edge.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dict
        New attributes to assign to the edge

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    if not graph.has_edge(s, t):
        raise GraphError("Edge '%s->%s' does not exist!" %
                         (str(s), str(t)))
    elif attrs is None:
        warnings.warn(
            "You want to update '%s->%s' attrs with an empty attrs_dict" %
            (str(s), str(t)), GraphAttrsWarning
        )
    else:
        new_attrs = deepcopy(attrs)
        normalize_attrs(new_attrs)
        graph.edge[s][t] = new_attrs
        if not graph.is_directed():
            graph.edge[t][s] = new_attrs


def remove_edge_attrs(graph, s, t, attrs):
    """Remove attrs of an edge specified by attrs.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dict
        Dictionary with attributes to remove.

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    if not graph.has_edge(s, t):
        raise GraphError("Edge %s-%s does not exist"
                         % (str(s), str(t)))
    else:
        normalize_attrs(attrs)
        old_attrs = get_edge(graph, s, t)
        for key, value in attrs.items():
            if key in old_attrs:
                new_set = old_attrs[key].difference(value)
                if new_set:
                    old_attrs[key] = new_set
                else:
                    del old_attrs[key]
        set_edge(graph, s, t, old_attrs)


def get_edge(graph, s, t):
    """Get edge attributes.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.
    """
    if graph.is_directed():
        return graph.edge[s][t]
    else:
        return merge_attributes(graph.edge[s][t], graph.edge[s][t])


def exists_edge(graph, s, t):
    """Check if an edge exists.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.
    """
    if graph.is_directed():
        return(s in graph.edge and t in graph.edge[s])
    else:
        s_t = s in graph.edge and t in graph.edge[s]
        t_s = t in graph.edge and s in graph.edge[t]
        return(s_t and t_s)


def filter_edges_by_attributes(graph, attr_key, attr_cond):
    """Filter graph edges by attributes.

    Removes all the edges of the graph (inplace) that do not
    satisfy `attr_cond`.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    attrs_key : attribute key
    attrs_cond : callable
        Condition for an attribute to satisfy: callable that returns
        `True` if condition is satisfied, `False` otherwise.

    """
    for (s, t) in graph.edges():
        if (attr_key not in graph.edge[s][t].keys() or
                not attr_cond(graph.edge[s][t][attr_key])):
            graph.remove_edge(s, t)


def set_edge(graph, s, t, attrs):
    """Set edge attrs.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dictionary
        Dictionary with attributes to set.

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    new_attrs = deepcopy(attrs)
    if not graph.has_edge(s, t):
        raise GraphError(
            "Edge %s->%s does not exist" % (str(s), str(t)))

    normalize_attrs(new_attrs)
    graph.edge[s][t] = new_attrs
    if not graph.is_directed():
        graph.edge[t][s] = new_attrs


def clone_node(graph, node_id, name=None):
    """Clone node.

    Create a new node, a copy of a node with `node_id`, and reconnect it
    with all the adjacent nodes of `node_id`.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_id : id of a node to clone.
    name : id for the clone, optional
        If is not specified, new id will be generated.

    Returns
    -------
    new_node : hashable, clone's id

    Raises
    ------
    GraphError
        If node wiht `node_id` does not exists or a node with
        `name` (clone's name) already exists.

    Examples
    --------
    >>> g = nx.DiGraph()
    >>> add_nodes_from(g, [1, 2, 3])
    >>> add_edges_from(g, [(1, 2), (3, 2)])
    >>> clone_node(g, 2, "2_clone")
    >>> g.nodes()
    [1, 2, "2_clone", 3]
    >>> g.edges()
    [(1, 2), (1, "2_clone"), (3, 2), (3, "2_clone")]

    """
    if node_id not in graph.nodes():
        raise GraphError("Node '%s' does not exist!" % str(node_id))

    # generate new name for a clone
    if name is None:
        i = 1
        new_node = str(node_id) + str(i)
        while new_node in graph.nodes():
            i += 1
            new_node = str(node_id) + str(i)
    else:
        if name in graph.nodes():
            raise GraphError("Node '%s' already exists!" % str(name))
        else:
            new_node = name

    graph.add_node(new_node, deepcopy(graph.node[node_id]))

    # Connect all the edges
    if graph.is_directed():
        add_edges_from(
            graph,
            [(n, new_node) for n, _ in graph.in_edges(node_id)])
        add_edges_from(
            graph,
            [(new_node, n) for _, n in graph.out_edges(node_id)])

        # Copy the attributes of the edges
        for s, t in graph.in_edges(node_id):
            graph.edge[s][new_node] = deepcopy(graph.edge[s][t])
        for s, t in graph.out_edges(node_id):
            graph.edge[new_node][t] = deepcopy(graph.edge[s][t])
    else:
        add_edges_from(
            graph,
            [(n, new_node) for n in graph.neighbors(node_id)]
        )

        # Copy the attributes of the edges
        for n in graph.neighbors(node_id):
            graph.edge[new_node][n] = deepcopy(graph.edge[n][node_id])
            graph.edge[n][new_node] = graph.edge[new_node][n]

    return new_node


def relabel_node(graph, node_id, new_id):
    """Relabel a node in the graph.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    node_id : id of a node to relabel.
    new_id : hashable, new label of a node.
    """
    clone_node(graph, node_id, new_id)
    graph.remove_node(node_id)


def relabel_nodes(graph, mapping):
    """Relabel graph nodes inplace given a mapping.

    Similar to networkx.relabel.relabel_nodes:
    https://networkx.github.io/documentation/development/_modules/networkx/relabel.html

    Parameters
    ----------
    graph : networkx.(Di)Graph
    mapping: dict
        A dictionary with keys being old node ids and their values
        being new id's of the respective nodes.

    Raises
    ------
    ReGraphError
        If new id's do not define a set of distinct node id's.

    """
    unique_names = set(mapping.values())
    if len(unique_names) != len(graph.nodes()):
        raise ReGraphError(
            "Attempt to relabel nodes failed: the IDs are not unique!")

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

    Parameters
    ----------
    graph : networkx.(Di)Graph
    mapping: dict
        A dictionary with keys being old node ids and their values
        being new id's of the respective nodes.

    Returns
    -------
    g : networkx.(Di)Graph
        New graph object isomorphic to the `graph` with the relabled nodes.

    Raises
    ------
    ReGraphError
        If new id's do not define a set of distinct node id's.


    See also
    --------
    regraph.primitives.relabel_nodes
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
        if g.is_directed():
            set_edge(g, s, t, attributes[(s, t)])
        else:
            if (s, t) in attributes.keys():
                set_edge(g, s, t, attributes[(s, t)])
            else:
                set_edge(g, s, t, attributes[(t, s)])
    return g


def merge_nodes(graph, nodes, node_id=None, method="union", edge_method="union"):
    """Merge a list of nodes.

    Parameters
    ----------

    graph : nx.(Di)Graph
    nodes : iterable
        Collection of node id's to merge.
    node_id : hashable, optional
        Id of a new node corresponding to the result of merge.
    method : optional
        Method of node attributes merge: if `"union"` the resulting node
        will contain the union of all attributes of the merged nodes,
        if `"intersection"`, the resulting node will contain their
        intersection. Default value is `"union"`.
    edge_method : optional
        Method of edge attributes merge: if `"union"` the edges that were
        merged will contain the union of all attributes,
        if `"intersection"` -- their ntersection. Default value is `"union"`.

    Returns
    -------
    node_id : hashable
        Id of a new node corresponding to the result of merge.

    Raises
    ------
    ReGraphError
        If unknown merging method is provided
    GraphError
        If some nodes from `nodes` do not exist in the graph.

    Examples
    --------

    >>> g = nx.DiGraph()
    >>> add_nodes_from(g, [(1, {"a": 1, "b": 1}), 2, (3, {"a": 3, "c": 3})])
    >>> add_edges_from(g, [(1, 3), (1, 2), (2, 3)])
    >>> merge_nodes(g, [1, 3], "merged_node")
    >>> g.nodes()
    ["merged_node", 2]
    >>> g.edges()
    [("merged_node", "merged_node"), ("merged_node", 2), (2, "merged_node")]
    >>> g.node["merged_node"]
    {"a": {1, 3}, "b": {1}, "c": {3}}

    """
    if len(nodes) == 1:
        if node_id is not None:
            relabel_node(graph, nodes[0], node_id)

    elif len(nodes) > 1:

        if method is None:
            method = "union"

        if edge_method is None:
            method = "union"

        # Generate name for new node
        if node_id is None:
            node_id = "_".join([str(n) for n in nodes])
        elif node_id in graph.nodes() and (node_id not in nodes):
            raise GraphError(
                "New name for merged node is not valid: "
                "node with name '%s' already exists!" % node_id
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
                    [n if n not in nodes else node_id
                     for n, _ in in_edges])
                target_nodes.update(
                    [n if n not in nodes else node_id
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

        add_node(graph, node_id, attr_accumulator)
        all_neighbors.add(node_id)

        if graph.is_directed():
            if self_loop:
                add_edges_from(graph, [(node_id, node_id)])
                graph.edge[node_id][node_id] = self_loop_attrs
            for n in source_nodes:
                if not exists_edge(graph, n, node_id):
                    add_edge(graph, n, node_id)
            for n in target_nodes:
                if not exists_edge(graph, node_id, n):
                    add_edge(graph, node_id, n)

            # Attach accumulated attributes to edges
            for node, attrs in source_dict.items():
                if node not in nodes:
                    graph.edge[node][node_id] = attrs
            for node, attrs in target_dict.items():
                if node not in nodes:
                    graph.edge[node_id][node] = attrs
        else:
            if self_loop:
                add_edges_from(graph, [(node_id, node_id)])
                graph.edge[node_id][node_id] = self_loop_attrs

            add_edges_from(graph, [(n, node_id) for n in neighbors])

            # Attach accumulated attributes to edges
            for node, attrs in neighbors_dict.items():
                if node not in nodes:
                    graph.edge[node][node_id] = attrs
                    graph.edge[node_id][node] = attrs

        return node_id


def subtract(a, b, ba_mapping):
    """Subtract graphs provided node mapping.

    Subtract graph B from A having mapping of nodes from B to
    nodes from A specified.

    Parameters
    ----------
    a : networkx.(Di)Graph
    b : networkx.(Di)Graph
    ba_mapping : dict

    Returns
    -------
    Graph representing the difference a - b.

    Examples
    --------
    >>> a = nx.DiGraph()
    >>> add_nodes_from(a, [1, 2, 3])
    >>> add_edges_from(a, [(1, 2), (2, 2), (2, 3)])
    >>> b = nx.DiGraph()
    >>> add_nodes_from(b, ['x', 'y'])
    >>> ba_mapping = {'x': 1, 'y': 3}
    >>> diff = subtract(a, b, ba_mapping)
    >>> diff.nodes()
    [2]
    >>> diff.edges()
    [(2, 2)]
    """
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
                attrs = json_dict_to_attrs(node["attrs"])
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
                attrs = json_dict_to_attrs(edge["attrs"])
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
    """Load a graph from a JSON file.

    Create a `networkx.(Di)Graph` object from
    a JSON representation stored in a file.

    Parameters
    ----------
    filename : str
        Name of the file to load the json serialization of the graph
    directed : bool, optional
        `True` if the graph to load is directed, `False` otherwise.
        Default value `True`.

    Returns
    -------
    nx.(Di)Graph object

    Raises
    ------
    ReGraphError
        If was not able to load the file

    """
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
    """Create a JSON representation of a graph."""
    j_data = {"edges": [], "nodes": []}
    # dump nodes
    for node in graph.nodes():
        node_data = {}
        node_data["id"] = node
        if graph.node[node] is not None:
            attrs = {}
            for key, value in graph.node[node].items():
                attrs[key] = value.to_json()
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
                attrs[key] = value.to_json()
            edge_data["attrs"] = attrs
        j_data["edges"].append(edge_data)
    return j_data


def export_graph(graph, filename):
    """Export graph to JSON file.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    filename : str
        Name of the file to save the json serialization of the graph


    """
    with open(filename, 'w') as f:
        j_data = graph_to_json(graph)
        json.dump(j_data, f)
    return


def find_matching(graph, pattern):
    """Find matching of a pattern in a graph.

    This function takes as an input a graph and a pattern graph, it
    searches for a matching of the pattern inside of the graph
    (corresponds to subgraph matching problem). The matching is defined by
    a map from the nodes of the pattern to the nodes of the graph such that:

    * edges are preserved, i.e. if there is an edge between nodes `n1` and `n2`
      in the pattern, there is an edge between the nodes of the graph that
      correspond to the image of `n1` and `n2`, moreover, the attribute
      dictionary of the edge between `n1` and `n2` is the subdictiotary of
      the edge it corresponds to in the graph;
    * the attribute dictionary of a pattern node is a subdictionary of
      its image in the graph;

    Uses `networkx.isomorphism.(Di)GraphMatcher` class, which implements
    subgraph matching algorithm.

    Parameters
    ----------
    graph : nx.(Di)Graph
    pattern : nx.(Di)Graph
        Pattern graph to search for

    Returns
    -------
    instances : list of dict's
        List of instances of matching found in the graph, every instance
        is represented with a dictionary where keys are nodes of the
        pattern, and values are corresponding nodes of the graph.

    Examples
    --------
    Suppose you are given the following graph:

    >>> g = networkx.DiGraph()
    >>> add_nodes_from(g, [(1, {"color": {"red"}}), 2, (3, {"color": {"blue"}})])
    >>> add_edges_from(g, [(1, 1), (1, 2), (3, 3), (3, 2)])

    And you would like to match the following pattern:

    >>> pattern = networkx.DiGraph()
    >>> add_nodes_from(pattern, [("x", {"color": "blue"}), "y"])
    >>> add_edges_from(pattern, [("x", "x"), ("x", "y")])

    Matching instances can be found as follows:

    >>> instances = find_matching(g, pattern)
    >>> instances
    [{"x": 3, "y": 2}]

    """
    labels_mapping = dict([(n, i + 1) for i, n in enumerate(graph.nodes())])
    g = get_relabeled_graph(graph, labels_mapping)
    matching_nodes = set()

    # find all the nodes matching the nodes in pattern
    for pattern_node in pattern.nodes():
        for node in g.nodes():
            if valid_attributes(pattern.node[pattern_node], g.node[node]):
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
                matching_obj = isomorphism.DiGraphMatcher(
                    pattern, edge_induced_graph)
                for isom in matching_obj.isomorphisms_iter():
                    isomorphic_subgraphs.append((subg, isom))
            else:
                edge_induced_graph = nx.Graph(edgeset)
                edge_induced_graph.add_nodes_from(
                    [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                matching_obj = isomorphism.GraphMatcher(
                    pattern, edge_induced_graph)
                for isom in matching_obj.isomorphisms_iter():
                    isomorphic_subgraphs.append((subg, isom))

    for subgraph, mapping in isomorphic_subgraphs:
        # check node matches
        # exclude subgraphs which nodes information does not
        # correspond to pattern
        for (pattern_node, node) in mapping.items():
            if not valid_attributes(pattern.node[pattern_node], subgraph.node[node]):
                break
        else:
            # check edge attribute matched
            for edge in pattern.edges():
                pattern_attrs = get_edge(pattern, edge[0], edge[1])
                target_attrs = get_edge(
                    subgraph, mapping[edge[0]], mapping[edge[1]])
                if not valid_attributes(pattern_attrs, target_attrs):
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


def print_graph(graph):
    """Util for pretty graph printing."""
    print("\nNodes:\n")
    for n in graph.nodes():
        print(n, " : ", graph.node[n])
    print("\nEdges:\n")
    for (n1, n2) in graph.edges():
        print(n1, '->', n2, ' : ', graph.edge[n1][n2])
    return


def equal(graph1, graph2):
    """Eqaulity of two graphs.

    Parameters
    ----------
    graph1 : nx.(Di)Graph
    graph2 : nx.(Di)Graph


    Returns
    -------
    bool
        True if two graphs are equal, False otherwise.
    """
    if set(graph1.nodes()) != set(graph2.nodes()):
        return False
    if set(graph1.edges()) != set(graph2.edges()):
        return False
    for node in graph1.nodes():
        # normalize_attrs(graph1.node[node])
        # normalize_attrs(graph2.node[node])
        if graph1.node[node] != graph2.node[node]:
            return False
    for s, t in graph1.edges():
        if get_edge(graph1, s, t) != get_edge(graph2, s, t):
            return False
    return True


def find_matching_with_types(graph, pattern, graph_typings,
                             pattern_typings, typing_graphs,
                             decr_types=False):
    """Find matching of a typed pattern in a typed graph.

    Parameters
    ----------
    graph : networkx.(Di)Graph
    pattern : networkx.(Di)Graph
    graph_typings : dict
        Dictionnary of typings of the graph
    pattern_typings : dict
        Dictionnary of typings of the pattern
    typing_graph : dict
        Dictionnary of the graphs typing the pattern

    networkX can only look at nodes attributes to compare them
    so we put the typings inside the nodes' attrs during matching
    we assume that no key is named:
    regraph_tmp_typings_key_that_you_should_not_use
    """
    typing_key = "regraph_tmp_typings_key_that_you_should_not_use"

    def _allowed_edge(source, target, typings):
        for (typ_id, typ_map) in typings.items():
            if typ_id not in typing_graphs.keys():
                raise ValueError(
                    "typing graph or pattern not in typing_graphs")
            typ_gr = typing_graphs[typ_id]
            if (source in typ_map.keys() and
                    target in typ_map.keys() and
                    typ_map[target] not in typ_gr.successors(typ_map[source])):
                return False
        return True

    may_edges = [edge for edge in itertools.product(pattern.nodes(),
                                                    pattern.nodes())
                 if (_allowed_edge(*edge, typings=pattern_typings) and
                     edge not in pattern.edges())]
    may_edges_subsets = itertools.chain.from_iterable(
        itertools.combinations(may_edges, r) for r in range(len(may_edges) + 1))

    def _put_typings_in_attrs(gr, typings):
        for (node, (typ_id, typ_map)) in\
                itertools.product(gr.nodes(), typings.items()):
            if node in typ_map.keys():
                add_node_attrs(
                    gr, node, {typing_key: FiniteSet([(typ_id, typ_map[node])])})

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
    return matchings


def unique_node_id(graph, prefix):
    """Generate a unique id starting by a prefix.

    Parameters
    ----------
    graph : networkx.Graph
    prefix : str
        Prefix that is prepended to the new unique name.


    Returns
    -------
    str
        New unique node id starting with a prefix.
    """
    if prefix not in graph.nodes():
        return prefix
    idx = 0
    new_id = "{}_{}".format(prefix, idx)
    while new_id in graph.nodes():
        idx += 1
        new_id = "{}_{}".format(prefix, idx)
    return new_id
