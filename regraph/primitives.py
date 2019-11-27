"""Graph transformation primitives.

This package contains a collection of utils for various transformations on
`regraph.Graph` objects. Attributes: `regraph.attribute_sets`
"""
import copy
import itertools
import json
import networkx as nx
import numpy as np
import os
import warnings

from networkx.algorithms import isomorphism

from regraph.graphs import NXGraph
from regraph.utils import (merge_attributes,
                           normalize_attrs,
                           valid_attributes,
                           keys_by_value,
                           json_dict_to_attrs,
                           load_nodes_from_json,
                           load_edges_from_json,
                           attrs_to_json,
                           attrs_from_json,
                           generate_new_id,
                           safe_deepcopy_dict)
from regraph.exceptions import (ReGraphError,
                                GraphError,
                                GraphAttrsWarning)
from regraph.attribute_sets import (FiniteSet)


def generate_new_node_id(graph, basename):
    return graph.generate_new_node_id(basename)


def add_node(graph, node_id, attrs=dict()):
    """Add a node to a graph.

    Parameters
    ----------
    graph : regraph.Graph
    node_id : hashable
        Prefix that is prepended to the new unique name.
    attrs : dict, optional
        Node attributes.

    Raises
    -------
    regraph.exceptions.GraphError
        Raises an error if node already exists in the graph.
    """
    graph.add_node(node_id, attrs)


def add_nodes_from(graph, node_list):
    """Add nodes from a node list.

    Parameters
    ----------
    graph : regraph.Graph
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
    graph.add_nodes_from(node_list)


def add_node_attrs(graph, node, attrs):
    """Add new attributes to a node.

    Parameters
    ----------
    graph : regraph.Graph
    node : hashable
        Id of a node to add attributes to.
    attrs : dict
        Attributes to add.

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.
    """
    graph.add_node_attrs(node, attrs)


def add_edge(graph, s, t, attrs=None, **attr):
    """Add an edge to a graph.

    Parameters
    ----------
    graph : regraph.Graph
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
    graph.add_edge(s, t, attrs)


def remove_edge(graph, s, t):
    """Remove edge from a graph.

    Parameters
    ----------
    graph : regraph.Graph
    s : hashable, source node id.
    t : hashable, target node id.

    Raises
    ------
    GraphError
        If edge between `s` and `t` does not exist.

    """
    graph.remove_edge(s, t)


def get_relabeled_graph(graph, mapping):
        """Return a graph with node labeling specified in the mapping.

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
        g = nx.DiGraph()
        old_nodes = set(mapping.keys())

        for old_node in old_nodes:
            try:
                new_node = mapping[old_node]
            except KeyError:
                continue
            try:
                g.add_node(
                    new_node,
                    **graph.get_node(old_node))
            except KeyError:
                raise GraphError("Node '%s' does not exist!" % old_node)

        new_edges = list()
        attributes = dict()
        for s, t in graph.edges():
            new_edges.append((
                mapping[s],
                mapping[t]))
            attributes[(mapping[s], mapping[t])] =\
                graph.get_edge(s, t)

        g.add_edges_from(new_edges)
        for s, t in g.edges():
            g.adj[s][t] = attributes[(s, t)]
        return g


def add_edges_from(graph, edge_list):
    """Add edges from an edge list.

    Parameters
    ----------
    graph : regraph.Graph
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
    graph.add_edges_from(edge_list)


def copy_node(graph, node_id):
    """Copy node.

    Create a copy of a node in a graph. A new id for the copy is
    generated by regraph.primitives.unique_node_id.

    Parameters
    ----------
    graph : regraph.Graph
    node_id : hashable, node to copy.

    Returns
    -------
    new_name
        Id of the copy node.

    """
    return graph.copy_node(node_id)


def add_node_new_id(graph, node_id, attrs=None):
    """Create a new node id if node_id already exists."""
    new_id = unique_node_id(graph, node_id)
    add_node(graph, new_id, attrs)
    return new_id


def remove_node(graph, node_id):
    """Remove node.

    Parameters
    ----------
    graph : regraph.Graph
    node_id : hashable, node to remove.

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.

    """
    graph.remove_node(node_id)


def set_node_attrs(graph, node_id, attrs, normalize=True, update=True):
    graph.set_node_attrs(node_id, attrs, normalize=normalize, update=update)


def update_node_attrs(graph, node_id, attrs, normalize=True):
    """Update attributes of a node.

    Parameters
    ----------
    graph : regraph.Graph
    node_id : hashable, node to update.
    attrs : dict
        New attributes to assign to the node

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.

    """
    graph.update(node_id, attrs, normalize=normalize)


def remove_node_attrs(graph, node_id, attrs):
    """Remove attrs of a node specified by attrs_dict.

    Parameters
    ----------
    graph : regraph.Graph
    node_id : hashable
        Node whose attributes to remove.
    attrs : dict
        Dictionary with attributes to remove.

    Raises
    ------
    GraphError
        If a node with the specified id does not exist.
    """
    graph.remove_node_attrs(node_id, attrs)


def add_edge_attrs(graph, s, t, attrs):
    """Add attributes of an edge in a graph.

    Parameters
    ----------
    graph : regraph.Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dict
        Dictionary with attributes to remove.

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    graph.add_edge_attrs(s, t, attrs)


def update_edge_attrs(graph, s, t, attrs, normalize=True):
    """Update attributes of an edge.

    Parameters
    ----------
    graph : regraph.Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dict
        New attributes to assign to the edge

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    graph.update_edge_attrs(s, t, attrs, normalize=normalize)


def remove_edge_attrs(graph, s, t, attrs):
    """Remove attrs of an edge specified by attrs.

    Parameters
    ----------
    graph : regraph.Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dict
        Dictionary with attributes to remove.

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    graph.remove_edge_attrs(s, t, attrs)


def get_node(graph, n):
    """Get node attributes.

    Parameters
    ----------
    graph : regraph.Graph or regraph.neo4j.Neo4jGraph
    s : hashable, source node id.
    t : hashable, target node id.
    """
    return graph.get_node_attrs(n)


def get_edge(graph, s, t):
    """Get edge attributes.

    Parameters
    ----------
    graph : regraph.Graph
    s : hashable, source node id.
    t : hashable, target node id.
    """
    return graph.get_edge_attrs(s, t)


def exists_edge(graph, s, t):
    """Check if an edge exists.

    Parameters
    ----------
    graph : regraph.Graph
    s : hashable, source node id.
    t : hashable, target node id.
    """
    return graph.exists_edge(s, t)


def filter_edges_by_attributes(graph, attr_key, attr_cond):
    """Filter graph edges by attributes.

    Removes all the edges of the graph (inplace) that do not
    satisfy `attr_cond`.

    Parameters
    ----------
    graph : regraph.Graph
    attrs_key : attribute key
    attrs_cond : callable
        Condition for an attribute to satisfy: callable that returns
        `True` if condition is satisfied, `False` otherwise.

    """
    graph.filter_edges_by_attributes(attr_key, attr_cond)


def set_edge(graph, s, t, attrs, normalize=True):
    """Set edge attrs.

    Parameters
    ----------
    graph : regraph.Graph
    s : hashable, source node id.
    t : hashable, target node id.
    attrs : dictionary
        Dictionary with attributes to set.

    Raises
    ------
    GraphError
        If an edge between `s` and `t` does not exist.
    """
    graph.set_edge(s, t, attrs, normalize=normalize)


def clone_node(graph, node_id, name=None):
    """Clone node.

    Create a new node, a copy of a node with `node_id`, and reconnect it
    with all the adjacent nodes of `node_id`.

    Parameters
    ----------
    graph : regraph.Graph
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
    new_node = graph.clone_node(node_id, name=name)
    return new_node


def relabel_node(graph, node_id, new_id):
    """Relabel a node in the graph.

    Parameters
    ----------
    graph : regraph.Graph
    node_id : id of a node to relabel.
    new_id : hashable, new label of a node.
    """
    graph.relabel_node(node_id, new_id)


def relabel_nodes(graph, mapping):
    """Relabel graph nodes inplace given a mapping.

    Similar to networkx.relabel.relabel_nodes:
    https://networkx.github.io/documentation/development/_modules/networkx/relabel.html

    Parameters
    ----------
    graph : regraph.Graph
    mapping: dict
        A dictionary with keys being old node ids and their values
        being new id's of the respective nodes.

    Raises
    ------
    ReGraphError
        If new id's do not define a set of distinct node id's.

    """
    graph.relabel_nodes(mapping)
    return


def merge_nodes(graph, nodes, node_id=None, method="union", edge_method="union"):
    """Merge a list of nodes.

    Parameters
    ----------

    graph : regraph.Graph
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
    new_id = graph.merge_nodes(nodes, node_id)
    return new_id


def subtract(a, b, ba_mapping):
    """Subtract graphs provided node mapping.

    Subtract graph B from A having mapping of nodes from B to
    nodes from A specified.

    Parameters
    ----------
    a : regraph.Graph
    b : regraph.Graph
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
                     get_node(a, n))
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
    graph.relabel_nodes(
        {n: (str(n) + "_" + str(token)) for n in graph.nodes()}
    )


def networkx_from_json(j_data):
    """Create a NetworkX graph from a json-like dictionary."""
    graph = NXGraph()
    graph.from_json(j_data)
    return graph


def load_networkx_graph(filename, directed=True):
    """Load a NetworkX graph from a JSON file.

    Create a `regraph.Graph` object from
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
    regraph.Graph object

    Raises
    ------
    ReGraphError
        If was not able to load the file

    """
    if os.path.isfile(filename):
        with open(filename, "r+") as f:
            j_data = json.loads(f.read())
            return networkx_from_json(j_data, directed)
    else:
        raise ReGraphError(
            "Error loading graph: file '%s' does not exist!" %
            filename
        )


def graph_to_json(graph):
    """Create a JSON representation of a graph."""
    j_data = graph.to_json()
    return j_data


def graph_to_d3_json(graph,
                     attrs=True,
                     node_attrs_to_attach=None,
                     edge_attrs_to_attach=None,
                     nodes=None):
    """Create a JSON representation of a graph."""
    # if isinstance(graph, nx.DiGraph):
    j_data = graph.to_d3_json()
    return j_data


def export_graph(graph, filename):
    """Export graph to JSON file.

    Parameters
    ----------
    graph : regraph.Graph
    filename : str
        Name of the file to save the json serialization of the graph


    """
    graph.export(filename)
    return


def find_matching(graph, pattern, nodes=None):
    """Find matching of a pattern in a graph.

    Parameters
    ----------
    graph : regraph.Graph
    pattern : regraph.Graph
        Pattern graph to search for
    nodes : iterable, optional
        Subset of nodes to search for matching

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
    instances = graph.find_matching(pattern, nodes)
    return instances


def print_graph(graph):
    """Util for pretty graph printing."""
    graph.print_graph()


def equal(graph1, graph2):
    """Eqaulity of two graphs.

    Parameters
    ----------
    graph1 : regraph.Graph
    graph2 : regraph.Graph


    Returns
    -------
    bool
        True if two graphs are equal, False otherwise.
    """
    return graph1 == graph2


def find_matching_with_types(graph, pattern, graph_typings,
                             pattern_typings, typing_graphs,
                             decr_types=False):
    """Find matching of a typed pattern in a typed graph.

    Parameters
    ----------
    graph : regraph.Graph
    pattern : regraph.Graph
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
            d1_without_types = safe_deepcopy_dict(d1)
            d2_without_types = safe_deepcopy_dict(d1)
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
            if typing_key in get_node(gr, node).keys():
                del get_node(gr, node)[typing_key]

    _remove_typings_in_attrs(graph)
    _remove_typings_in_attrs(pattern)
    return matchings
