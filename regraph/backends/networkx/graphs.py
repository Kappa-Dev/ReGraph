"""NetworkX-based in-memory graph objects.

This module implements data structures wrapping the `networkx.DiGraph` class.
"""
import itertools
import networkx as nx
from networkx.algorithms import isomorphism

import warnings

from regraph.exceptions import (ReGraphError,
                                GraphError,
                                GraphAttrsWarning,
                                )
from regraph.graphs import Graph
from regraph.backends.networkx.plotting import plot_graph

from regraph.utils import (normalize_attrs,
                           safe_deepcopy_dict,
                           valid_attributes,
                           normalize_relation,
                           )


class NXGraph(Graph):
    """Wrapper for NetworkX directed graphs."""

    node_dict_factory = dict
    adj_dict_factory = dict

    def __init__(self, incoming_graph_data=None, **attr):
        """Initialize NetworkX graph."""
        super().__init__()
        self._graph = nx.DiGraph()

    def nodes(self, data=False):
        """Return the list of nodes."""
        if data:
            return [(n, self.get_node(n)) for n in self._graph.nodes()]
        else:
            return self._graph.nodes()

    def edges(self, data=False):
        """Return the list of edges."""
        if data:
            return [(s, t, self.get_edge(s, t)) for s, t in self.edges()]
        return self._graph.edges()

    def get_node(self, n):
        """Get node attributes.

        Parameters
        ----------
        n : hashable
            Node id.
        """
        return self._graph.nodes[n]

    def get_edge(self, s, t):
        """Get edge attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        return self._graph.adj[s][t]

    def add_node(self, node_id, attrs=None):
        """Abstract method for adding a node.

        Parameters
        ----------
        node_id : hashable
            Prefix that is prepended to the new unique name.
        attrs : dict, optional
            Node attributes.
        """
        if attrs is None:
            new_attrs = dict()
        else:
            new_attrs = safe_deepcopy_dict(attrs)
            normalize_attrs(new_attrs)
        if node_id not in self.nodes():
            self._graph.add_node(node_id, **new_attrs)
            return node_id
        else:
            raise GraphError("Node '{}' already exists!".format(node_id))

    def remove_node(self, node_id):
        """Remove node.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node_id : hashable, node to remove.
        """
        if node_id in self.nodes():
            self._graph.remove_node(node_id)
        else:
            raise GraphError("Node '{}' does not exist!".format(node_id))
        return

    def add_edge(self, s, t, attrs=None, **attr):
        """Add an edge to a graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dict
            Edge attributes.
        """
        if attrs is None:
            attrs = attr
        else:
            try:
                attrs.update(attr)
            except AttributeError:
                raise ReGraphError(
                    "The attr_dict argument must be a dictionary."
                )

        new_attrs = safe_deepcopy_dict(attrs)
        if s not in self.nodes():
            raise GraphError("Node '{}' does not exist!".format(s))
        if t not in self.nodes():
            raise GraphError("Node '{}' does not exist!".format(t))
        normalize_attrs(new_attrs)

        if (s, t) in self.edges():
            raise GraphError(
                "Edge '{}'->'{}' already exists!".format(s, t))
        self._graph.add_edge(s, t, **new_attrs)

    def remove_edge(self, s, t):
        """Remove edge from the graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        if (s, t) not in self.edges():
            raise GraphError(
                "Edge '{}->{}' does not exist!".format(s, t))
        self._graph.remove_edge(s, t)

    def update_node_attrs(self, node_id, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        node_id : hashable, node to update.
        attrs : dict
            New attributes to assign to the node

        """
        new_attrs = safe_deepcopy_dict(attrs)
        if node_id not in self.nodes():
            raise GraphError(
                "Node '{}' does not exist!".format(node_id))
        elif new_attrs is None:
            warnings.warn(
                "You want to update '{}' attrs with an empty attrs_dict!".format(
                    node_id),
                GraphAttrsWarning
            )
        else:
            if normalize is True:
                normalize_attrs(new_attrs)
            attrs_to_remove = set()
            for k in self._graph.nodes[node_id].keys():
                if k not in new_attrs.keys():
                    attrs_to_remove.add(k)
            self._graph.add_node(node_id, **new_attrs)
            for k in attrs_to_remove:
                del self._graph.nodes[node_id][k]

    def update_edge_attrs(self, s, t, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        s : hashable, source node of the edge to update.
        t : hashable, target node of the edge to update.
        attrs : dict
            New attributes to assign to the node

        """
        if not self._graph.has_edge(s, t):
            raise GraphError("Edge '{}->{}' does not exist!".format(
                             s, t))
        if attrs is None:
            warnings.warn(
                "You want to update '{}->{}' attrs with an empty attrs_dict".format(
                    s, t), GraphAttrsWarning
            )

        if normalize is True:
            normalize_attrs(attrs)
        attrs_to_remove = set()
        for k in self._graph.adj[s][t].keys():
            if k not in attrs.keys():
                attrs_to_remove.add(k)
        self._graph.add_edge(s, t, **attrs)
        for k in attrs_to_remove:
            del self._graph.adj[s][t][k]

    def successors(self, node_id):
        """Return the set of successors."""
        return self._graph.successors(node_id)

    def predecessors(self, node_id):
        """Return the set of predecessors."""
        if node_id not in self.nodes():
            raise GraphError(
                "Node '{}' does not exist in the graph".format(
                    node_id))

        return self._graph.predecessors(node_id)

    def get_relabeled_graph(self, mapping):
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
                pass
            try:
                g.add_node(
                    new_node,
                    **self.get_node(old_node))
            except KeyError:
                raise GraphError("Node '%s' does not exist!" % old_node)

        new_edges = list()
        attributes = dict()
        for s, t in self.edges():
            new_s = None
            new_t = None
            try:
                new_s = mapping[s]
            except KeyError:
                pass
            try:
                new_t = mapping[t]
            except KeyError:
                pass
            if new_s and new_t:
                new_edges.append((new_s, new_t))
                attributes[(new_s, new_t)] = self.get_edge(s, t)

        g.add_edges_from(new_edges)
        for s, t in g.edges():
            for k, v in attributes[(s, t)].items():
                g.adj[s][t][k] = v
        return g

    def subgraph(self, nodes):
        """Get a subgraph induced by the collection of nodes."""
        g = NXGraph()
        g.add_nodes_from([
            (n, attrs) for n, attrs in self.nodes(data=True)
            if n in nodes])
        for s, t, attrs in self.edges(data=True):
            if s in g.nodes() and t in g.nodes():
                g.add_edge(s, t, attrs)
        return g

    def advanced_find_matching(self, pattern_dict,
                               nodes=None, graph_typing=None,
                               pattern_typing=None):
        """Find matching of a pattern in a graph in an advanced way."""
        patterns = []

        edge_combinations = [
            [(u_var, v_var, attrs), (v_var, u_var, attrs)]
            for (u_var, v_var, attrs) in pattern_dict["undirected_edges"]
        ]

        for new_edges in itertools.product(*edge_combinations):
            pattern = NXGraph()
            pattern.add_nodes_from(pattern_dict["nodes"])
            pattern.add_edges_from(pattern_dict["directed_edges"])
            pattern.add_edges_from(list(new_edges))
            patterns.append(pattern)
            plot_graph(pattern)

        instances = []
        for pattern in patterns:
            instances += self.find_matching(
                pattern, nodes, graph_typing, pattern_typing)
        return instances

    def find_matching(self, pattern, nodes=None,
                      graph_typing=None, pattern_typing=None):
        """Find matching of a pattern in a graph.

        This function takes as an input a graph and a pattern, optionally,
        it also takes a collection of nodes specifying the subgraph of the
        original graph, where the matching should be searched in, then it
        searches for a matching of the pattern inside of the graph (or induced
        subragh), which corresponds to solving subgraph matching problem.
        The matching is defined by a map from the nodes of the pattern
        to the nodes of the graph such that:

        * edges are preserved, i.e. if there is an edge between nodes `n1`
          and `n2` in the pattern, there is an edge between the nodes of
          the graph that correspond to the image of `n1` and `n2`,
          moreover, the attribute dictionary of the edge between `n1`
          and `n2` is the subdictiotary of the edge it corresponds to
          in the graph;
        * the attribute dictionary of a pattern node is a subdictionary of
          its image in the graph;

        Uses `networkx.isomorphism.(Di)GraphMatcher` class, which implements
        subgraph matching algorithm.

        In addition, two parameters `graph_typing` and `pattern_typing`
        can be specified. They restrict the space of admisible solutions
        by checking if an isomorphic subgraph found in the input graph respects
        the provided pattern typings according to the specified graph typings.

        Parameters
        ----------
        graph : nx.(Di)Graph
        pattern : nx.(Di)Graph
            Pattern graph to search for
        nodes : iterable, optional
            Subset of nodes to search for matching
        graph_typing : dict of dict, optional
            Dictionary defining typing of graph nodes
        pattern_typing : dict of dict, optional
            Dictionary definiting typing of pattern nodes

        Returns
        -------
        instances : list of dict's
            List of instances of matching found in the graph, every instance
            is represented with a dictionary where keys are nodes of the
            pattern, and values are corresponding nodes of the graph.

        """
        new_pattern_typing = dict()
        if pattern_typing:
            for graph, pattern_mapping in pattern_typing.items():
                new_pattern_typing[graph] = normalize_relation(
                    pattern_mapping)

        if graph_typing is None:
            graph_typing = {}

        # check graph/pattern typing is consistent
        for g, mapping in new_pattern_typing.items():
            if g not in graph_typing:
                raise ReGraphError(
                    "Graph is not typed by '{}' from the specified ".format(
                        g) +
                    "pattern typing")

        if nodes is not None:
            g = self._graph.subgraph(nodes)
        else:
            g = self._graph

        labels_mapping = dict([(n, i + 1) for i, n in enumerate(g.nodes())])
        g = self.get_relabeled_graph(labels_mapping)
        inverse_mapping = dict(
            [(value, key) for key, value in labels_mapping.items()]
        )

        matching_nodes = set()

        # find all the nodes matching the nodes in pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if new_pattern_typing:
                    # check types match
                    match = False
                    for graph, pattern_mapping in new_pattern_typing.items():
                        if node in graph_typing[graph].keys() and\
                           pattern_node in pattern_mapping.keys():
                            if graph_typing[graph][node] in pattern_mapping[
                                    pattern_node]:
                                if valid_attributes(
                                        pattern.get_node(pattern_node),
                                        g.nodes[node]):
                                    match = True
                        else:
                            if valid_attributes(
                                    pattern.get_node(pattern_node),
                                    g.nodes[node]):
                                match = True
                    if match:
                        matching_nodes.add(node)
                else:
                    if valid_attributes(
                            pattern.get_node(pattern_node),
                            g.nodes[node]):
                        matching_nodes.add(node)

        # find all the isomorphic subgraphs
        reduced_graph = g.subgraph(matching_nodes)
        instances = []
        isomorphic_subgraphs = []
        for sub_nodes in itertools.combinations(reduced_graph.nodes(),
                                                len(pattern.nodes())):
            subg = reduced_graph.subgraph(sub_nodes)
            for edgeset in itertools.combinations(subg.edges(),
                                                  len(pattern.edges())):
                edge_induced_graph = nx.DiGraph(list(edgeset))
                edge_induced_graph.add_nodes_from(
                    [n for n in subg.nodes()
                     if n not in edge_induced_graph.nodes()])
                if isinstance(pattern, Graph):
                    matching_obj = isomorphism.DiGraphMatcher(
                        pattern._graph, edge_induced_graph)
                else:
                    matching_obj = isomorphism.DiGraphMatcher(
                        pattern, edge_induced_graph)
                for isom in matching_obj.isomorphisms_iter():
                    isomorphic_subgraphs.append((subg, isom))

        for subgraph, mapping in isomorphic_subgraphs:
            # print(subgraph.nodes(), mapping)
            # check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if new_pattern_typing:
                    for g, pattern_mapping in new_pattern_typing.items():
                        if inverse_mapping[node] in graph_typing[g].keys() and\
                           pattern_node in pattern_mapping.keys():
                            if graph_typing[g][
                                inverse_mapping[node]] not in pattern_mapping[
                                    pattern_node]:
                                break
                        if not valid_attributes(
                                pattern.get_node(pattern_node),
                                subgraph.nodes[node]):
                            break
                    else:
                        continue
                    break
                else:
                    if not valid_attributes(
                            pattern.get_node(pattern_node),
                            subgraph.nodes[node]):
                        break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.get_edge(edge[0], edge[1])
                    target_attrs = subgraph.adj[
                        mapping[edge[0]]][mapping[edge[1]]]
                    if not valid_attributes(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # bring back original labeling
        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]

        return instances

    @classmethod
    def copy(cls, graph):
        """Copy the input graph object."""
        new_graph = cls()
        new_graph.add_nodes_from(graph.nodes(data=True))
        new_graph.add_edges_from(graph.edges(data=True))
        return new_graph

    def nodes_disconnected_from(self, node_id):
        """Find nodes disconnected from the input node."""
        components = nx.weakly_connected_components(
            self._graph)

        disconnected_components = []
        for comp in components:
            if node_id not in comp:
                disconnected_components.append(comp)
        return set([
            n
            for n in comp
            for comp in disconnected_components
        ])
