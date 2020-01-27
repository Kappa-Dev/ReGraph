"""In-memory graph hierarchy related data structures.

This module contains a data structure implementing
graph hierarchy based on NetworkX graphs.

* `NXHierarchy` -- class for in-memort graph hierarchies.
"""
import copy
import networkx as nx
import warnings

from regraph.exceptions import (HierarchyError,
                                ReGraphError,
                                InvalidHomomorphism,
                                RewritingError,
                                ReGraphWarning)
from regraph.hierarchies import Hierarchy
from regraph.backends.networkx.graphs import NXGraph
from regraph.category_utils import (compose,
                                    pushout,
                                    get_unique_map_to_pullback,
                                    check_homomorphism,
                                    right_relation_dict,
                                    pullback_complement)
from regraph.utils import (normalize_attrs,
                           normalize_relation,
                           keys_by_value,)


class NXHierarchy(Hierarchy, NXGraph):
    """Class for in-memory hierarchies.

    Attributes
    ----------

    """

    rel_dict_factory = dict

    # Implementation of abstract methods

    def graphs(self, data=False):
        """Return a list of graphs in the hierarchy."""
        if data:
            return [
                (n, n_data["attrs"])
                for n, n_data in self.nodes(True)
                if "graph" in n_data]
        else:
            return [n for n, n_data in self.nodes(True) if "graph" in n_data]

    def typings(self, data=False):
        """Return a list of graph typing edges in the hierarchy."""
        if data:
            return [
                (s, t, e_data["attrs"])
                for s, t, e_data in self.edges(True)
                if "mapping" in e_data]
        else:
            return [
                (s, t)
                for s, t, e_data in self.edges(True)
                if "mapping" in e_data]

    def relations(self, data=False):
        """Return a list of relations."""
        if data:
            return [
                (l, r, attrs)
                for (l, r), attrs in self.relation_edges.items()
            ]
        else:
            return list(set(self.relation_edges.keys()))

    def successors(self, node_id):
        """Return the set of successors."""
        return self._graph.successors(node_id)

    def predecessors(self, node_id):
        """Return the set of predecessors."""
        return self._graph.predecessors(node_id)

    def get_graph(self, graph_id):
        """Get a graph object associated to the node 'graph_id'."""
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Hierarchy node '{}' does not exist!".format(graph_id))
        if not self.is_graph(graph_id):
            raise HierarchyError(
                "Hierarchy node '{}' is a rule!".format(graph_id))
        return self.node[graph_id]["graph"]

    def get_typing(self, source, target):
        """Get a typing dict associated to the edge 'source->target'."""
        if (source, target) in self.edges():
            if self.is_graph(source):
                return self.get_edge(source, target)["mapping"]
            else:
                edge = self.get_edge(source, target)
                return (edge["lhs_mapping"], edge["rhs_mapping"])
        else:
            try:
                path = nx.shortest_path(self._graph, source, target)
            except:
                raise HierarchyError(
                    "No path from '{}' to '{}' in the hierarchy".format(
                        source, target))
            return self.compose_path_typing(path)

    def get_relation(self, left, right):
        """Get a relation dict associated to the rel 'left-right'."""
        return self.relation_edges[(left, right)]["rel"]

    def get_graph_attrs(self, graph_id):
        """Get attributes of a graph in the hierarchy.

        graph_id : hashable
            Id of the graph
        """
        return self.get_node(graph_id)["attrs"]

    def set_graph_attrs(self, node_id, attrs):
        """Set attributes of a graph in the hierarchy.

        graph_id : hashable
            Id of the graph
        """
        return self.set_node_attrs(node_id, {"attrs": attrs})

    def get_typing_attrs(self, source, target):
        """Get attributes of a typing in the hierarchy.

        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        return self.get_edge(source, target)["attrs"]

    def set_typing_attrs(self, source, target, attrs):
        """Set attributes of a typing in the hierarchy.

        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        return self.set_edge_attrs(source, target, {"attrs": attrs})

    def get_relation_attrs(self, left, right):
        """Get attributes of a reltion in the hierarchy.

        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
        """
        return self.relation_edges[(left, right)]["attrs"]

    def set_relation_attrs(self, left, right, attrs):
        """Set attributes of a relation in the hierarchy.

        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
        """
        normalize_attrs(attrs)
        for k, v in attrs.items():
            self.relation_edges[(left, right)]["attrs"][k] = v
            self.relation_edges[(right, left)]["attrs"][k] = v

    def set_node_relation(self, left_graph, right_graph,
                          left_node, right_node):
        """Set relation to a particular node."""
        if left_node in self.relation_edges[
                left_graph, right_graph]["rel"].keys():
            self.relation_edges[left_graph, right_graph]["rel"][left_node].add(
                right_node)
        else:
            self.relation_edges[left_graph, right_graph]["rel"][left_node] = {
                right_node}

        if right_node in self.relation_edges[
                right_graph, left_graph]["rel"].keys():
            self.relation_edges[
                right_graph, left_graph]["rel"][right_node].add(left_node)
        else:
            self.relation_edges[right_graph, left_graph]["rel"][right_node] = {
                left_node}

    def add_graph(self, graph_id, graph, graph_attrs=None):
        """Add a new graph to the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        graph : regraph.Graph
            Graph object corresponding to the new node of
            the hierarchy
        graph_attrs : dict, optional
            Dictionary containing attributes of the new node
        """
        if graph_id in self.nodes():
            raise HierarchyError(
                "Node '{}' already exists in the hierarchy!".format(graph_id))

        self.add_node(graph_id)
        if graph_attrs is not None:
            normalize_attrs(graph_attrs)
        else:
            graph_attrs = dict()
        self.update_node_attrs(
            graph_id, {
                "graph": graph,
                "attrs": graph_attrs
            }, normalize=False)
        return

    def add_empty_graph(self, graph_id, attrs=None):
        """"Add a new empty graph to the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        graph_attrs : dict, optional
            Dictionary containing attributes of the new node
        """
        g = NXGraph()
        self.add_graph(graph_id, g, attrs)

    def add_graph_from_data(self, graph_id, node_list, edge_list, attrs=None):
        """Add a new graph to the hierarchy from the input node/edge lists.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        node_list : iterable
            List of nodes (with attributes)
        edge_list : iterable
            List of edges (with attributes)
        graph_attrs : dict, optional
            Dictionary containing attributes of the new node
        """
        self.add_empty_graph(graph_id, attrs)
        g = self.get_graph(graph_id)
        if node_list is not None:
            g.add_nodes_from(node_list)
        if edge_list is not None:
            g.add_edges_from(edge_list)

    def add_typing(self, source, target, mapping=None, attrs=None):
        """Add homomorphism to the hierarchy.

        Parameters
        ----------
        source : hashable
            Id of the source graph node of typing
        target : hashable
            Id of the target graph node of typing
        mapping : dict
            Dictionary representing a mapping of nodes
            from the source graph to target's nodes
        attrs : dict, optional
            Dictionary containing attributes of the new
            typing edge. Empty by default

        Raises
        ------
        HierarchyError
            This error is raised in the following cases:

                * source or target ids are not found in the hierarchy
                * a typing edge between source and target already exists
                * addition of an edge between source and target creates
                a cycle or produces paths that do not commute with
                some already existing paths

        InvalidHomomorphism
            If a homomorphisms from a graph at the source to a graph at
            the target given by `mapping` is not a valid homomorphism.

        """
        if source not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(source))
        if target not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(target))

        if mapping is None:
            mapping = dict()

        if (source, target) in self.edges():
            raise HierarchyError(
                "Edge '{}->{}' already exists in the hierarchy: "
                "no muliple edges allowed!".format(source, target)
            )
        if not self.is_graph(source):
            raise HierarchyError(
                "Source of a typing should be a graph,"
                " '{}' is provided!".format(
                    type(self.node[source]))
            )

        if not self.is_graph(target):
            raise HierarchyError(
                "Target of a typing should be a graph, "
                "'{}' is provided!".format(
                    type(self.node[target]))
            )

        # check no cycles are produced
        self.add_edge(source, target)
        if not nx.is_directed_acyclic_graph(self._graph):
            self.remove_edge(source, target)
            raise HierarchyError(
                "Edge '{}->{}' creates a cycle in the hierarchy!".format(
                    source, target)
            )
        self.remove_edge(source, target)

        # check if the homomorphism is valid
        check_homomorphism(
            self.get_graph(source),
            self.get_graph(target),
            mapping,
        )

        # check if newly created path commutes with existing shortest paths
        self._check_consistency(source, target, mapping)

        self.add_edge(source, target)
        if attrs is not None:
            normalize_attrs(attrs)
        else:
            attrs = dict()
        self.set_edge(
            source, target, {
                "mapping": mapping,
                "attrs": attrs
            }, normalize=False)
        return

    def add_relation(self, left, right, relation, attrs=None):
        """Add relation to the hierarchy.

        This method adds a relation between two graphs in
        the hierarchy corresponding to the nodes with ids
        `left` and `right`, the relation itself is defined
        by a dictionary `relation`, where a key is a node in
        the `left` graph and its corresponding value is a set
        of nodes from the `right` graph to which the node is
        related. Relations in the hierarchy are symmetric
        (see example below).

        Parameters
        ----------
        left
            Id of the hierarchy's node represening the `left` graph
        right
            Id of the hierarchy's node represening the `right` graph
        relation : dict
            Dictionary representing a relation of nodes from `left`
            to the nodes from `right`, a key of the dictionary is
            assumed to be a node from `left` and its value a set
            of ids of related nodes from `right`
        attrs : dict
            Dictionary containing attributes of the new relation

        Raises
        ------
        HierarchyError
            This error is raised in the following cases:

                * node with id `left`/`right` is not defined in the hierarchy;
                * node with id `left`/`right` is not a graph;
                * a relation between `left` and `right` already exists;
                * some node ids specified in `relation` are not found in the
                `left`/`right` graph.
        """
        if left not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(left))
        if right not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(right))

        if not self.is_graph(left):
            raise HierarchyError(
                "Relation can be defined only on graph objects"
            )
        if not self.is_graph(right):
            raise HierarchyError(
                "Relation can be defined only on graph objects"
            )

        if (left, right) in self.relations():
            raise HierarchyError(
                "Relation '{}-{}' already exists in the hierarchy "
                "multiple edges are not allowed!".format(
                    left, right)
            )

        # normalize relation dict
        relation = normalize_relation(relation)

        # check relation is well-defined on left and right side
        for key, values in relation.items():
            if key not in self.get_graph(left).nodes():
                raise HierarchyError(
                    "Relation is not valid: node '{}' does not "
                    "exist in a graph '{}'".format(key, left)
                )
            for v in values:
                if v not in self.get_graph(right).nodes():
                    raise HierarchyError(
                        "Relation is not valid: node '{}' does not "
                        "exist in a graph '{}'".format(v, right)
                    )

        if attrs is not None:
            normalize_attrs(attrs)
        else:
            attrs = dict()
        pairs = set()
        for k, values in relation.items():
            for v in values:
                pairs.add((k, v))
        right_relation = right_relation_dict(pairs)
        rel_ab_dict = {
            "rel": relation,
            "attrs": attrs
        }
        rel_ba_dict = {
            "rel": right_relation,
            "attrs": attrs
        }
        self.relation_edges.update({(left, right): rel_ab_dict})
        self.relation_edges.update({(right, left): rel_ba_dict})
        return

    def remove_graph(self, graph_id, reconnect=False):
        """Remove graph from the hierarchy.

        Removes a graph from the hierarchy, if the `reconnect`
        parameter is set to True, adds typing from the
        predecessors of the removed node to all its successors,
        by composing the homomorphisms (for every predecessor `p`
        and for every successor 's' composes two homomorphisms
        `p`->`node_id` and `node_id`->`s`, then removes `node_id` and
        all its incident edges, by which makes node's
        removal a procedure of 'forgetting' one level
        of 'abstraction').

        Parameters
        ----------
        graph_id
            Id of a graph to remove
        reconnect : bool
            Reconnect the descendants of the removed node to
            its predecessors

        Raises
        ------
        HierarchyError
            If graph with `node_id` is not defined in the hierarchy
        """
        if not self.is_graph(graph_id):
            raise HierarchyError(
                "Hierarchy node '{}' is a rule! ".format(graph_id) +
                "Use, 'remove_rule' method instead")
        self.remove_node(graph_id, reconnect)

    def remove_typing(self, s, t):
        """Remove a typing from the hierarchy."""
        self.remove_edge(s, t)

    def remove_relation(self, left, right):
        """Remove a relation from the hierarchy."""
        if (left, right) not in self.relations() and\
           (right, left) not in self.relations():
            raise HierarchyError(
                "Relation '{}-{}' is not defined in the hierarchy".format(
                    left, right)
            )
        del self.relation_edges[left, right]
        del self.relation_edges[right, left]

    def bfs_tree(self, graph, reverse=False):
        """BFS tree from the graph to all other reachable graphs."""
        return list(nx.bfs_tree(self._graph, graph, reverse=reverse))[1:]

    def shortest_path(self, source, target):
        """Shortest path from 'source' to 'target'."""
        return nx.shortest_path(self._graph, source, target)

    def copy_graph(self, graph_id, new_graph_id, attach_graphs=None):
        """Create a copy of a graph in a hierarchy."""
        if attach_graphs is None:
            attach_graphs = []
        if new_graph_id in self.graphs():
            raise HierarchyError(
                "Graph with id '{}' already exists in the hierarchy".format(
                    new_graph_id))
        graph_copy = NXGraph.copy(self.get_graph(graph_id))
        self.add_graph(
            new_graph_id, graph_copy,
            self.get_graph_attrs(graph_id))

        # copy all typings to/from attach_graphs
        for g in attach_graphs:
            if g in self.successors(graph_id):
                self.add_typing(new_graph_id, g, self.get_typing(graph_id, g))
            if g in self.predecessors(graph_id):
                self.add_typing(g, new_graph_id, self.get_typing(g, graph_id))
            if g in self.adjacent_relations(graph_id):
                self.add_relation(g, new_graph_id, self.get_relation(
                    g, graph_id))

    def relabel_graph_node(self, graph_id, node, new_name):
        """Rename a node in a graph of the hierarchy."""
        if new_name in self.get_graph(graph_id).nodes():
            raise ReGraphError(
                "Node '{}' already exists in the graph '{}'".format(
                    new_name, graph_id)
            )
        if node not in self.get_graph(graph_id).nodes():
            raise ReGraphError(
                "Node '{}' does not exist in the graph '{}".format(
                    node, graph_id)
            )
        self.get_graph(graph_id).relabel_node(node, new_name)
        for pred in self.predecessors(graph_id):
            mapping = self.get_typing(pred, graph_id)
            new_mapping = dict()
            for k, v in mapping.items():
                if v == node:
                    new_mapping[k] = new_name
                else:
                    new_mapping[k] = v
            self._update_mapping(pred, graph_id, new_mapping)
        for suc in self.successors(graph_id):
            mapping = self.get_typing(graph_id, suc)
            new_mapping = dict()
            for k, v in mapping.items():
                if k == node:
                    new_mapping[new_name] = v
                else:
                    new_mapping[k] = v
            self._update_mapping(graph_id, suc, new_mapping)

    def relabel_graph(self, graph_id, new_graph_id):
        """Relabel a graph in the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph to relabel
        new_graph_id : hashable
            New graph id to assign to this graph
        """
        self.relabel_node(graph_id, new_graph_id)

    def relabel_graphs(self, mapping):
        """Relabel graphs in the hierarchy.

        Parameters
        ----------
        mapping: dict
            A dictionary with keys being old graph ids and their values
            being new id's of the respective graphs.

        Raises
        ------
        ReGraphError
            If new id's do not define a set of distinct graph id's.
        """
        unique_names = set(mapping.values())
        if len(unique_names) != len(self.nodes()):
            raise ReGraphError(
                "Attempt to relabel nodes failed: the IDs are not unique!")

        temp_names = {}
        # Relabeling of the nodes: if at some point new ID conflicts
        # with already existing ID - assign temp ID
        for key, value in mapping.items():
            if key != value:
                if value not in self.nodes():
                    new_name = value
                else:
                    new_name = self.generate_new_node_id(value)
                    temp_names[new_name] = value
                self.relabel_node(key, new_name)
        # Relabeling the nodes with the temp ID to their new IDs
        for key, value in temp_names.items():
            if key != value:
                self.relabel_node(key, value)
        return

    def _check_consistency(self, source, target, mapping=None):
        all_paths = dict(nx.all_pairs_shortest_path(self._graph))

        paths_to_source = {}
        paths_from_target = {}
        for s in self.nodes():
            if source in all_paths[s].keys():
                paths_to_source[s] = all_paths[s][source]
            if s == target:
                for key in all_paths[target].keys():
                    paths_from_target[key] = all_paths[target][key]

        for s in paths_to_source.keys():
            if self.is_rule(paths_to_source[s][0]):
                for t in paths_from_target.keys():
                    # find homomorphism from s to t via new path
                    if s == source:
                        raise HierarchyError(
                            "Found a rule typing some node in the self!"
                        )
                    new_lhs_h, new_rhs_h = self.compose_path_typing(
                        paths_to_source[s])
                    new_lhs_h = compose(new_lhs_h, mapping)
                    new_rhs_h = compose(new_rhs_h, mapping)

                    if t != target:
                        new_lhs_h = compose(
                            new_lhs_h,
                            self.compose_path_typing(paths_from_target[t])
                        )
                        new_rhs_h = compose(
                            new_rhs_h,
                            self.compose_path_typing(paths_from_target[t]),
                        )
                    try:
                        # find homomorphisms from s to t via other paths
                        s_t_paths = nx.all_shortest_paths(self._graph, s, t)
                        for path in s_t_paths:
                            lhs_h, rhs_h = self.compose_path_typing(path)
                            if lhs_h != new_lhs_h:
                                raise HierarchyError(
                                    "Invalid lhs typing: homomorphism does "
                                    "not commute with an existing " +
                                    "path from '{}' to '{}'!".format(s, t)
                                )
                            if rhs_h != new_rhs_h:
                                raise HierarchyError(
                                    "Invalid rhs typing: homomorphism does "
                                    "not commute with an existing " +
                                    "path from '{}' to '{}'!".format(s, t)
                                )
                    except(nx.NetworkXNoPath):
                        pass
            else:
                for t in paths_from_target.keys():
                    # find homomorphism from s to t via new path
                    if s != source:
                        new_homomorphism = self.compose_path_typing(
                            paths_to_source[s])
                    else:
                        new_homomorphism = dict([(key, key)
                                                 for key, _ in mapping.items()])
                    new_homomorphism = compose(
                        new_homomorphism, mapping)
                    if t != target:
                        new_homomorphism = compose(
                            new_homomorphism,
                            self.compose_path_typing(paths_from_target[t])
                        )

                    # find homomorphisms from s to t via other paths
                    s_t_paths = nx.all_shortest_paths(self._graph, s, t)
                    try:
                        # check only the first path
                        for path in s_t_paths:
                            path_homomorphism = self.compose_path_typing(path)
                            if path_homomorphism != new_homomorphism:
                                raise HierarchyError(
                                    "Homomorphism does not commute with an " +
                                    "existing path from '{}' to '{}'!".format(
                                        s, t)
                                )
                    except(nx.NetworkXNoPath):
                            pass

    def _propagate_clone(self, origin_id, node_id, p_origin_m,
                         origin_m_origin, p_typing,
                         g_m_g, g_m_origin_m):
        """Propagate clones from 'origin_id' to 'graph_id'.

        Perform a controlled propagation of clones to 'graph'

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        p_origin_m : dict
            Instance of rule's interface inside the updated origin
        origin_m_origin : dict
            Map from the updated origin to the initial origin
        p_typing : dict
            Controlling relation from the nodes of 'graph_id' to
            the nodes of the interfaces

        Returns
        -------
        g_m_g : dict
            Map from the updated 'graph_id' to the 'graph_id'
        """
        if self.is_graph(node_id):
            g_m_g, g_m_origin_m = super()._propagate_clone(
                origin_id, node_id, p_origin_m,
                origin_m_origin, p_typing,
                g_m_g, g_m_origin_m)
        else:
            cloned_origin_nodes = {}
            for n in set(origin_m_origin.values()):
                clones = keys_by_value(origin_m_origin, n)
                if len(clones) > 1:
                    cloned_origin_nodes[n] = clones

            rule = self.get_rule(node_id)
            origin_typing = self.get_typing(node_id, origin_id)

            lhs_m_lhs = g_m_g[0]
            p_m_p = g_m_g[1]
            rhs_m_rhs = g_m_g[2]
            lhs_m_origin_m = g_m_origin_m[0]
            rhs_m_origin_m = g_m_origin_m[1]

            if p_typing:
                warnings.warn(
                    "Non-empty typing of the rule '{}' by ".format(
                        node_id),
                    "the interface: non-canonical propagation to rules is not "
                    "implemented, typing is ignored",
                    ReGraphWarning)

            p_origin_typing = {
                n: origin_typing[0][rule.p_lhs[n]]
                for n in rule.p.nodes()
            }
            cloned_lhs_nodes = self._produce_clones(
                cloned_origin_nodes, p_origin_m, rule.lhs, origin_typing[0],
                {}, lhs_m_lhs, lhs_m_origin_m)

            cloned_p_nodes = self._produce_clones(
                cloned_origin_nodes, p_origin_m, rule.p,
                p_origin_typing,
                {}, p_m_p, {
                    n: lhs_m_origin_m[rule.p_lhs[n]]
                    for n in rule.p.nodes()
                })

            cloned_rhs_nodes = self._produce_clones(
                cloned_origin_nodes, p_origin_m, rule.rhs,
                origin_typing[1], {},
                rhs_m_rhs, rhs_m_origin_m)

            # restore rule homomorphisms
            for n, p_node in cloned_p_nodes.items():
                original_p_node = p_m_p[n]
                original_lhs_node = rule.p_lhs[original_p_node]
                original_rhs_node = rule.p_rhs[original_p_node]
                lhs_clones = keys_by_value(cloned_lhs_nodes, p_node)
                rhs_clones = keys_by_value(cloned_rhs_nodes, p_node)
                for lhs_clone in lhs_clones:
                    if lhs_m_lhs[lhs_clone] == original_lhs_node:
                        rule.p_lhs[n] = lhs_clone
                        break
                for rhs_clone in rhs_clones:
                    if rhs_m_rhs[rhs_clone] == original_rhs_node:
                        rule.p_rhs[n] = rhs_clone
                        break

        self._restrictive_update_incident_homs(node_id, g_m_g)
        self._restrictive_update_incident_rels(node_id, g_m_g)

        return g_m_g, g_m_origin_m

    def _propagate_node_removal(self, origin_id, node_id, rule, instance,
                                g_m_g, g_m_origin_m):
        """Propagate node removal from 'origin_id' to 'graph_id'.

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        origin_m_origin : dict
            Map from the updated origin to the initial origin

        Returns
        -------
        g_m_g : dict
            Map from the updated 'graph_id' to the 'graph_id'
        """
        if self.is_graph(node_id):
            g_m_g, g_m_origin_m = super()._propagate_node_removal(
                origin_id, node_id, rule, instance,
                g_m_g, g_m_origin_m)
        else:
            object_rule = self.get_rule(node_id)
            origin_typing = self.get_typing(node_id, origin_id)
            for lhs_node in rule.removed_nodes():
                origin_n = instance[lhs_node]
                lhs_nodes = keys_by_value(origin_typing[0], origin_n)
                p_nodes = [
                    n for n in object_rule.p.nodes()
                    if object_rule.p_lhs[n] in lhs_nodes]
                rhs_nodes = keys_by_value(origin_typing[1], origin_n)
                lhs_m_lhs = g_m_g[0]
                p_m_p = g_m_g[1]
                rhs_m_rhs = g_m_g[1]
                lhs_m_origin_m = g_m_origin_m[0]
                p_m_origin_m = g_m_origin_m[1]
                rhs_m_origin_m = g_m_origin_m[1]
                for node in lhs_nodes:
                    object_rule.lhs.remove_node(node)
                    del lhs_m_lhs[node]
                    del lhs_m_origin_m[node]
                for node in p_nodes:
                    object_rule.p.remove_node(node)
                    del p_m_p[node]
                    del p_m_origin_m[node]
                for node in rhs_nodes:
                    object_rule.rhs.remove_node(node)
                    del rhs_m_rhs[node]
                    del rhs_m_origin_m[node]

        self._restrictive_update_incident_homs(node_id, g_m_g)
        self._restrictive_update_incident_rels(node_id, g_m_g)

        return g_m_g, g_m_origin_m

    def _propagate_node_attrs_removal(self, origin_id, node_id, rule,
                                      p_origin_m, g_m_origin_m):
        """Propagate node attrs removal from 'origin_id' to 'graph_id'.

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        rule : regraph.Rule
            Original rewriting rule
        instance : dict
            Original instance
        """
        if self.is_graph(node_id):
            super()._propagate_node_attrs_removal(
                origin_id, node_id, rule,
                p_origin_m, g_m_origin_m)
        else:
            pass
            # object_rule = self.get_rule(node_id)
            # origin_typing = self.get_typing(node_id, origin_id)

            # for lhs_node, attrs in rule.removed_node_attrs().items():
            #     lhs_nodes_to_remove_attrs = keys_by_value(
            #         origin_typing[0], instance[lhs_node])
            #     for node in lhs_nodes_to_remove_attrs:
            #         object_rule.lhs.remove_node_attrs(node, attrs)
            #     p_nodes_to_remove_attrs = [
            #         n for n in object_rule.p.nodes()
            #         if object_rule.p_lhs[n] in lhs_nodes_to_remove_attrs]
            #     for node in p_nodes_to_remove_attrs:
            #         object_rule.p.remove_node_attrs(node, attrs)
            #     rhs_nodes_to_remove_attrs = keys_by_value(
            #         origin_typing[1], instance[lhs_node])
            #     for node in rhs_nodes_to_remove_attrs:
            #         object_rule.rhs.remove_node_attrs(node, attrs)

    def _propagate_edge_removal(self, origin_id, node_id, g_m_origin_m):
        """Propagate edge removal from 'origin_id' to 'graph_id'.

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        node_id : hashable
            ID of the node where propagation is performed
        p_origin_m : dict
            Instance of rule's interface inside the updated origin
        origin_m_origin : dict
            Map from the updated origin to the initial origin
        """
        if self.is_graph(node_id):
            super()._propagate_edge_removal(origin_id, node_id, g_m_origin_m)
        else:
            rule = self.get_rule(node_id)
            origin_graph = self.get_graph(origin_id)
            for s, t in rule.lhs.edges():
                origin_s = g_m_origin_m[0][s]
                origin_t = g_m_origin_m[0][t]
                if (origin_s, origin_t) not in origin_graph.edges():
                    rule.lhs.remove_edge(s, t)
            for s, t in rule.p.edges():
                origin_s = g_m_origin_m[0][rule.p_lhs[s]]
                origin_t = g_m_origin_m[0][rule.p_lhs[t]]
                if (origin_s, origin_t) not in origin_graph.edges():
                    rule.p.remove_edge(s, t)
            for s, t in rule.rhs.edges():
                origin_s = g_m_origin_m[1][s]
                origin_t = g_m_origin_m[1][t]
                if (origin_s, origin_t) not in origin_graph.edges():
                    rule.rhs.remove_edge(s, t)

    def _propagate_edge_attrs_removal(self, origin_id, node_id, rule, p_origin_m):
        """Propagate edge attrs removal from 'origin_id' to 'graph_id'.

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        rule : regraph.Rule
            Original rewriting rule
        p_origin_m : dict
            Instance of rule's interface inside the updated origin
        """
        if self.is_graph(node_id):
            super()._propagate_edge_attrs_removal(
                origin_id, node_id, rule, p_origin_m)
        else:
            object_rule = self.get_rule(node_id)
            origin_typing = self.get_typing(node_id, origin_id)

            for (p_u, p_v), attrs in rule.removed_edge_attrs().items():
                lhs_us = keys_by_value(origin_typing[0], p_origin_m[p_u])
                lhs_vs = keys_by_value(origin_typing[0], p_origin_m[p_v])
                for u in lhs_us:
                    for v in lhs_vs:
                        if (u, v) in object_rule.lhs.edges():
                            object_rule.lhs.removed_edge_attrs(u, v, attrs)
                p_us = [
                    n
                    for n in object_rule.p.nodes
                    if object_rule.p_lhs[n] in lhs_us]
                p_vs = [
                    n
                    for n in object_rule.p.nodes
                    if object_rule.p_lhs[n] in lhs_vs]
                for u in p_us:
                    for v in p_vs:
                        if (u, v) in object_rule.p.edges():
                            object_rule.p.removed_edge_attrs(u, v, attrs)
                rhs_us = keys_by_value(origin_typing[1], p_origin_m[p_u])
                rhs_vs = keys_by_value(origin_typing[1], p_origin_m[p_v])
                for u in rhs_us:
                    for v in rhs_vs:
                        if (u, v) in object_rule.rhs.edges():
                            object_rule.rhs.removed_edge_attrs(u, v, attrs)

    def _get_rule_liftings(self, graph_id, rule, instance, p_typing):
        pass

    def _get_rule_projections(self, graph_id, rule, instance, rhs_typing):
        pass

    # Implementation of the NXHierarchy-specific methods

    def __init__(self, attrs=None):
        """Initialize in-memory hierarchy."""
        NXGraph.__init__(self)
        if attrs is None:
            attrs = dict()
        self.attrs = attrs

        self.rel_dict_factory = reldf = self.rel_dict_factory
        self.relation_edges = reldf()

    def rules(self, data=True):
        """Return a list of rules in the hierarchy."""
        if data:
            return [
                (n, n_data["attrs"])
                for n, n_data in self.nodes(True).items()
                if "rule" in n_data]
        else:
            return [n for n, n_data in self.nodes(True) if "rule" in n_data]

    def rule_typings(self, data=True):
        """Return a list of rule typing edges in the hierarchy."""
        if data:
            return [
                (s, t, e_data["attrs"])
                for s, t, e_data in self.edges(True).items()
                if "lhs_mapping" in e_data]
        else:
            return [
                (s, t)
                for s, t, e_data in self.edges(True).items()
                if "lhs_mapping" in e_data]

    def get_node_attrs(self, node_id):
        """Get attributes of a node in the hierarchy.

        node_id : hashable
            Id of the node
        """
        return self.get_node(node_id)["attrs"]

    def get_rule(self, rule_id):
        """Get a rule object associated to the node 'graph_id'."""
        if rule_id not in self.nodes():
            pass
        if not self.is_rule(rule_id):
            pass
        return self.node[rule_id]["rule"]

    def add_rule(self, rule_id, rule, attrs=None):
        """Add rule to the hierarchy.

        Parameters
        ----------
        rule_id : hashable
            Id of a new node in the hierarchy
        rule : regraph.rules.Rule
            Rule object corresponding to the new node of
            the hierarchy
        attrs : dict
            Dictionary containing attributes of the new node

        Raises
        ------
        HierarchyError
            If the rule object is defined for directed/undirected
            graphs while the hierarchy's parameter `directed` is
            False/True (the hierarchy accommodates undirected/directed
            graphs) or if node with provided id already exists
            in the hierarchy

        """
        if rule_id in self.nodes():
            raise HierarchyError(
                "Node '{}' already exists in the hierarchy!".format(
                    rule_id)
            )
        self.add_node(rule_id)
        if attrs is not None:
            normalize_attrs(attrs)
        else:
            attrs = dict()
        self.update_node_attrs(
            rule_id,
            {
                "rule": rule,
                "attrs": attrs
            },
            normalize=False)
        return

    def add_rule_typing(self, rule_id, graph_id, lhs_mapping,
                        rhs_mapping=None,
                        lhs_total=False, rhs_total=False,
                        attrs=None):
        """Add typing of a rule.

        source
            Id of a rule node to type
        target
            Id of a target graph node of typing
        lhs_mapping : dict
            Dictionary representing a mapping of nodes
            from the left-hand side of the rule to target's nodes
        rhs_mapping : dict
            Dictionary representing a mapping of nodes
            from the right-hand side of the rule to target's nodes
        lhs_total : bool
            True if left-hand side typing is total, False otherwise
        rhs_total : bool
            True if right-hand side typing is total, False otherwise
        attrs : dict
            Dictionary containing attributes of the new
            typing edge

        Raises
        ------
        HierarchyError
            This error is raised in the following cases:

                * source or target ids are not found in the hierarchy
                * a typing edge between source and target already exists
                * a source node is not a rule
                * a target node is not a graph
                * addition of an edge produces paths that do not commute with
                some already existing paths

        InvalidHomomorphism
            If a homomorphisms from the left(right)-hand side to a graph at
            the target given by `lhs(rhs)_mapping` is not a valid homomorphism.

        """
        if rule_id not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(rule_id))
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(graph_id))

        if not self.is_rule(rule_id):
            raise HierarchyError(
                "Source of a rule typing should be a rule, "
                "`{}` is provided!".format(
                    type(self.node[rule_id]))
            )
        if not self.is_graph(graph_id):
            raise HierarchyError(
                "Target of a rule typing should be a graph, "
                "'{}' is provided!".format(
                    type(self.node[graph_id])))

        # check if an lhs typing is valid
        check_homomorphism(
            self.node[rule_id]["rule"].lhs,
            self.node[graph_id]["graph"],
            lhs_mapping,
            total=lhs_total
        )

        new_rhs_mapping = rhs_mapping
        if new_rhs_mapping is None:
            new_rhs_mapping = dict()
        rule = self.node[rule_id]["rule"]
        for node in rule.rhs.nodes():
            p_keys = keys_by_value(rule.p_rhs, node)
            if len(p_keys) == 1:
                l = rule.p_lhs[p_keys[0]]
                if l in lhs_mapping.keys():
                    new_rhs_mapping[node] = lhs_mapping[l]
            if len(p_keys) > 1:
                type_set = set()
                for p in p_keys:
                    l = rule.p_lhs[p]
                    if l in lhs_mapping.keys():
                        type_set.add(lhs_mapping[l])
                if len(type_set) > 1:
                    raise HierarchyError(
                        "Invalid rule typing: rule merges nodes of different "
                        "types (types that being merged: {})!".format(type_set)
                    )
                elif len(type_set) == 1:
                    new_rhs_mapping[node] = list(type_set)[0]

        # check if an rhs typing is valid
        check_homomorphism(
            self.node[rule_id]["rule"].rhs,
            self.node[graph_id]["graph"],
            new_rhs_mapping,
            total=rhs_total
        )

        # check if newly created path commutes with existing shortest paths
        self._check_rule_typing(rule_id, graph_id, lhs_mapping, new_rhs_mapping)

        self.add_edge(rule_id, graph_id)
        if attrs is not None:
            normalize_attrs(attrs)
        else:
            attrs = dict()
        self.set_edge(
            rule_id, graph_id,
            {
                "lhs_mapping": lhs_mapping,
                "rhs_mapping": new_rhs_mapping,
                "lhs_total": lhs_total,
                "rhs_total": rhs_total,
                "attrs": attrs
            },
            normalize=False)
        return

    def get_rule_typing(self, rule_id, graph_id):
        """Get typing dict of `source` by `target` (`source` is rule)."""
        if not self.is_rule(rule_id):
            raise HierarchyError("Hierarchy node '{}' is not a rule".format(
                rule_id))
        if graph_id not in self.successors(rule_id):
            raise HierarchyError(
                "Rule '{}' is not typed by the graph '{}'".format(
                    rule_id, graph_id))
        rule = self.get_node(rule_id)["rule"]
        lhs_typing = self.get_edge(rule_id, graph_id)["lhs_mapping"]
        rhs_typing = self.get_edge(rule_id, graph_id)["rhs_mapping"]
        p_typing = {n: rhs_typing[rule.p_rhs[n]] for n in rule.p.nodes()}
        return (lhs_typing, p_typing, rhs_typing)

    def is_graph(self, node_id):
        """Test if a hierarchy node is a graph."""
        return "graph" in self.get_node(node_id)

    def is_rule(self, node_id):
        """Test if a hierarchy node is a rule."""
        return "rule" in self.get_node(node_id)

    def is_typing(self, s, t):
        """Test if a hierarchy edge is a typing."""
        return "mapping" in self.get_edge(s, t)

    def is_rule_typing(self, s, t):
        """Test if a hierarchy edge is a rule typing."""
        return "lhs_mapping" in self.get_edge(s, t)

    def remove_node(self, node_id, reconnect=False):
        """Remove node from the hierarchy.

        Removes a node from the hierarchy, if the `reconnect`
        parameter is set to True, adds typing from the
        predecessors of the removed node to all its successors,
        by composing the homomorphisms (for every predecessor `p`
        and for every successor 's' composes two homomorphisms
        `p`->`node_id` and `node_id`->`s`, then removes `node_id` and
        all its incident edges, by which makes node's
        removal a procedure of 'forgetting' one level
        of 'abstraction').

        Parameters
        ----------
        node_id
            Id of a node to remove
        reconnect : bool
            Reconnect the descendants of the removed node to
            its predecessors

        Raises
        ------
        HierarchyError
            If node with `node_id` is not defined in the hierarchy
        """
        if node_id not in self.nodes():
            raise HierarchyError(
                "Node '{}'' is not defined in the hierarchy!".format(node_id))

        if reconnect:
            out_graphs = self.successors(node_id)
            in_graphs = self.predecessors(node_id)

            for source in in_graphs:
                for target in out_graphs:
                    if self.is_rule_typing(source, node_id):
                        lhs_map, rhs_map = self.get_rule_typing(
                            source, node_id)
                        new_lhs_map = compose(
                            lhs_map,
                            self.get_typing(node_id, target)
                        )
                        new_rhs_map = compose(
                            rhs_map,
                            self.get_typing(node_id, target)
                        )
                        if (source, target) not in self.edges():
                            self.add_rule_typing(
                                source,
                                target,
                                new_lhs_map,
                                new_rhs_map
                            )
                    elif self.is_typing(source, node_id):
                        # compose two homomorphisms
                        mapping = compose(
                            self.get_typing(source, node_id),
                            self.get_typing(node_id, target)
                        )

                        if (source, target) not in self.edges():
                            self.add_typing(
                                source, target, mapping)

        nx.DiGraph.remove_node(self._graph, node_id)

        # Update dicts representing relations
        for u, v in self.relation_edges.keys():
            if u == node_id or v == node_id:
                del self.relation_edges[u, v]

        return

    def remove_rule(self, rule_id, reconnect=False):
        """Remove graph from the hierarchy.

        Removes a rule from the hierarchy, if the `reconnect`
        parameter is set to True, adds typing from the
        predecessors of the removed node to all its successors,
        by composing the homomorphisms (for every predecessor `p`
        and for every successor 's' composes two homomorphisms
        `p`->`node_id` and `node_id`->`s`, then removes `node_id` and
        all its incident edges, by which makes node's
        removal a procedure of 'forgetting' one level
        of 'abstraction').

        Parameters
        ----------
        rule_id
            Id of a rule to remove
        reconnect : bool
            Reconnect the descendants of the removed node to
            its predecessors

        Raises
        ------
        HierarchyError
            If graph with `node_id` is not defined in the hierarchy
        """
        if not self.is_rule(rule_id):
            raise HierarchyError(
                "Hierarchy node '{}' is a graph! ".format(rule_id) +
                "Use, 'remove_graph' method instead")
        self.remove_node(rule_id, reconnect)

    def compose_path_typing(self, path):
        """Compose homomorphisms along the path.

        Parameters
        ----------
        path : list
            List of nodes of the hierarchy forming a path

        Returns
        -------
        If source node of the path is a graph

        homomorphism : dict
            Dictionary containg the typing of the nodes
            from the source graph of the path by the nodes
            of the target graph

        if source node of the path is a rule

        lhs_homomorphism : dict
            Dictionary containg the typing of the nodes
            from the left-hand side of the source rule
            of the path by the nodes of the target graph
        rhs_homomorphism : dict
            Dictionary containg the typing of the nodes
            from the right-hand side of the source rule
            of the path by the nodes of the target graph
        """
        s = path[0]
        t = path[1]
        if self.is_graph(s):
            homomorphism = self.get_typing(s, t)
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                homomorphism = compose(
                    homomorphism,
                    self.get_typing(s, t)
                )
            return homomorphism
        else:
            lhs_typing, p_typing, rhs_typing = self.get_rule_typing(s, t)
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                lhs_typing = compose(
                    lhs_typing,
                    self.get_typing(s, t)
                )
                p_typing = compose(
                    p_typing,
                    self.get_typing(s, t)
                )
                rhs_typing = compose(
                    rhs_typing,
                    self.get_typing(s, t)
                )

            return (lhs_typing, p_typing, rhs_typing)

    @classmethod
    def copy(cls, hierarchy):
        """Copy the hierarchy object."""
        return copy.deepcopy(hierarchy)

    def find_rule_matching(self, graph_id, rule_id):
        """Find matching of a rule `rule_id` form the hierarchy."""
        if self.is_rule(graph_id):
            raise ReGraphError(
                "Pattern matching in a rule is not implemented!")

        if not self.is_rule(rule_id):
            raise HierarchyError("Invalid rule '{}' to match!".format(rule_id))

        rule = self.node[rule_id]["rule"]

        lhs_typing = dict()
        rhs_typing = dict()

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] = self.adj[rule_id][suc]["lhs_mapping"]
            rhs_typing[suc] = self.adj[rule_id][suc]["rhs_mapping"]

        instances = self.find_matching(
            graph_id,
            rule.lhs,
            lhs_typing
        )
        return instances

    def _update_graph(self, graph_id, graph_obj):
        """Update the graph object stored at the node of with id 'graph_id'."""
        self.set_node_attrs(
            graph_id, {
                "graph": graph_obj,
                "attrs": self.node[graph_id]["attrs"]
            },
            normalize=False
        )

    def _update_mapping(self, source, target, mapping):
        """Update the mapping dictionary from source to target."""
        if self.is_graph(source):
            self.update_edge_attrs(
                source, target,
                {
                    "mapping": mapping,
                    "attrs": self.get_typing_attrs(source, target)
                },
                normalize=False
            )
        else:
            lhs, rhs = mapping
            self._update_rule_homomorphism(
                source, target, lhs, rhs)

    def _update_relation(self, left, right, relation):
        """Update the relation dictionaries (left and right)."""
        old_attrs = copy.deepcopy(self.relation_edges[left, right]["attrs"])
        self.remove_relation(left, right)
        self.add_relation(left, right, relation, old_attrs)

    def _update_rule(self, rule_id, rule_obj):
        """Update the rule object stored at the node of with id 'rule_id'."""
        self.update_node_attrs(
            rule_id,
            {
                "rule": rule_obj,
                "attrs": self.node[rule_id]["attrs"]
            },
            normalize=False
        )

    def _update_rule_homomorphism(self, source, target, lhs_h, rhs_h):
        self.update_edge_attrs(
            source, target,
            {
                "lhs_mapping": lhs_h,
                "rhs_mapping": rhs_h,
                "attrs": self.get_typing_attrs(source, target)
            },
            normalize=False
        )

    def _update(self, graphs=None, homomorphisms=None, relations=None,
                rules=None, rule_homomorphisms=None):
        """Update parts of hierarchy with new objects."""
        if graphs is None:
            graphs = dict()
        if homomorphisms is None:
            homomorphisms = dict()
        if relations is None:
            relations = dict()
        if rules is None:
            rules = dict()
        if rule_homomorphisms is None:
            rule_homomorphisms = dict()

        for graph, graph_obj in graphs.items():
            self._update_graph(graph, graph_obj)

        for (s, t), mapping in homomorphisms.items():
            self._update_mapping(s, t, mapping)

        for (l, r), relation in relations.items():
            self._update_relation(l, r, relation)

        for rule, rule_obj in rules.items():
            self._update_rule(rule, rule_obj)

        for (s, t), (lhs_h, rhs_h) in rule_homomorphisms.items():
            self._update_rule_homomorphism(s, t, lhs_h, rhs_h)

    def _restrictive_update_incident_homs(self, node_id, g_m_g):
        """Update incident homomorphisms after a restrictive change."""
        for suc in self.successors(node_id):
            typing = self.get_typing(node_id, suc)
            if self.is_graph(node_id):
                self._update_mapping(node_id, suc, compose(g_m_g, typing))
            else:
                self._update_rule_homomorphism(
                    node_id, suc,
                    compose(g_m_g[0], typing[0]),
                    compose(g_m_g[2], typing[1]))

    def _restrictive_update_incident_rels(self, graph_id, g_m_g):
        """Update incident relations after a restrictive change."""
        if self.is_graph(graph_id):
            for related_g in self.adjacent_relations(graph_id):
                rel = self.get_relation(graph_id, related_g)
                new_rel = dict()

                for node in self.get_graph(graph_id).nodes():
                    old_node = g_m_g[node]
                    if old_node in rel.keys():
                        new_rel[node] = rel[old_node]

                self._update_relation(graph_id, related_g, new_rel)

    def _expansive_update_incident_homs(self, graph_id, g_m_g_prime,
                                        pred_typings):
        """Update incident homomorphisms after an expansive change."""
        for pred, typing in pred_typings.items():
            if self.is_graph(pred):
                self._update_mapping(
                    pred, graph_id, compose(typing, g_m_g_prime))
            else:
                self._update_rule_homomorphism(
                    pred, graph_id,
                    compose(typing[0], g_m_g_prime),
                    compose(typing[1], g_m_g_prime))

    def _expansive_update_incident_rels(self, graph_id, g_m_g_prime,
                                        adj_relations):
        """Update incident relations after an expansive change."""
        for related_g, rel in self.adjacent_relations(graph_id):
            if self.is_graph(related_g):
                super()._expansive_update_incident_rels(
                    graph_id, g_m_g_prime, adj_relations)
            else:
                pass

    def apply_rule(self, graph_id, rule_id, instance):
        """Apply rule from the hierarchy."""
        if self.is_rule(graph_id):
            raise ReGraphError("Rewriting of a rule is not implemented!")

        if not self.is_rule(rule_id):
            raise RewritingError(
                "Invalid rewriting rule '{}'!".format(rule_id))

        rule = self.get_rule(rule_id)

        lhs_typing = dict()
        rhs_typing = dict()

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] =\
                self.adj[rule_id][suc]["lhs_mapping"]
            rhs_typing[suc] =\
                self.adj[rule_id][suc]["rhs_mapping"]

        return self.rewrite(
            graph_id,
            rule,
            instance,
            rhs_typing=rhs_typing)

    def to_json(self, rename_nodes=None):
        """Convert hierarchy to its json representation."""
        return super().to_json(rename_nodes)

    def _check_rule_typing(self, rule_id, graph_id, lhs_mapping, rhs_mapping):
        all_paths = dict(nx.all_pairs_shortest_path(self._graph))

        paths_from_target = {}
        for s in self.nodes():
            if s == graph_id:
                for key in all_paths[graph_id].keys():
                    paths_from_target[key] = all_paths[graph_id][key]

        for t in paths_from_target.keys():
            if t != graph_id:
                new_lhs_h = compose(
                    lhs_mapping,
                    self.compose_path_typing(paths_from_target[t]))
                new_rhs_h = compose(
                    rhs_mapping,
                    self.compose_path_typing(paths_from_target[t]))
                try:
                    # find homomorphisms from s to t via other paths
                    s_t_paths = nx.all_shortest_paths(self._graph, rule_id, t)
                    for path in s_t_paths:
                        lhs_h, _, rhs_h = self.compose_path_typing(path)
                        if lhs_h != new_lhs_h:
                            raise HierarchyError(
                                "Invalid lhs typing: homomorphism does not "
                                "commute with an existing "
                                "path from '{}' to '{}'!".format(s, t)
                            )
                        if rhs_h != new_rhs_h:
                            raise HierarchyError(
                                "Invalid rhs typing: homomorphism does not "
                                "commute with an existing " +
                                "path from '{}' to '{}'!".format(s, t)
                            )
                except(nx.NetworkXNoPath):
                    pass
        return

    def _get_identity_map(self, node_id):
        if self.is_graph(node_id):
            return {
                n: n for n in self.get_graph(node_id).nodes()
            }
        else:
            lhs_map = {
                n: n for n in self.get_rule(node_id).lhs.nodes()
            }
            p_map = {
                n: n for n in self.get_rule(node_id).p.nodes()
            }
            rhs_map = {
                n: n for n in self.get_rule(node_id).rhs.nodes()
            }
            return (lhs_map, p_map, rhs_map)

    def _restore_by_backward_composability(self, target_id, g_m_g, g_m_origin_ms):
        if self.is_graph(target_id):
            graph_nodes = self.get_graph(target_id).nodes()
            for pred in self.predecessors(target_id):
                pred_typing = self.get_typing(pred, target_id)
                if self.is_graph(pred):
                    pred_graph = get_unique_map_to_pullback(
                        graph_nodes,
                        g_m_g,
                        g_m_origin_ms[target_id],
                        pred_typing,
                        g_m_origin_ms[pred])
                    self.remove_typing(pred, target_id)
                    self.add_typing(pred, target_id, pred_graph)
                else:
                    lhs_typing, rhs_typing = pred_typing
                    lhs_pred_graph = get_unique_map_to_pullback(
                        graph_nodes,
                        g_m_g,
                        g_m_origin_ms[target_id],
                        lhs_typing,
                        g_m_origin_ms[pred][0])
                    rhs_pred_graph = get_unique_map_to_pullback(
                        graph_nodes,
                        g_m_g,
                        g_m_origin_ms[target_id],
                        rhs_typing,
                        g_m_origin_ms[pred][1])
                    self.remove_typing(pred, target_id)
                    self.add_rule_typing(
                        pred, target_id, lhs_pred_graph, rhs_pred_graph)

    def relabel_nodes(self, graph, mapping):
        """Relabel nodes of a graph in the hierarchy."""
        graph_obj = self.get_graph(graph)
        graph_obj.relabel_nodes(mapping)

        # update homomorphisms
        for predecessor in self.predecessors(graph):
            old_typing = self.get_typing(predecessor, graph)
            self._update_mapping(
                predecessor, graph, compose(old_typing, mapping))
        for successor in self.successors(graph):
            old_typing = self.get_typing(graph, successor)
            self._update_mapping(
                graph, successor,
                {
                    mapping[k]: v
                    for k, v in old_typing.items()
                }
            )
        # update relations
        for adj in self.adjacent_relations(graph):
            old_rel = self.get_relation(graph, adj)
            self._update_relation(
                graph, adj,
                {
                    mapping[k]: v
                    for k, v in old_rel.items()
                }
            )

    # def _compose_backward(self, pred_id, graph_id, g_m_g, graph_m_origin_m,
    #                       pred_m_origin_m, pred_typing):
    #     graph_nodes = self.get_graph(graph_id).nodes()
    #     return get_unique_map_to_pullback(
    #         graph_nodes,
    #         g_m_g,
    #         graph_m_origin_m,
    #         pred_typing,
    #         pred_m_origin_m)

    def _compose_backward(self, pred_id, graph_id, g_m_g, graph_m_origin_m,
                          pred_m_origin_m, pred_typing):
        if self.is_graph(pred_id):
            return super()._compose_backward(
                pred_id, graph_id, g_m_g, graph_m_origin_m,
                pred_m_origin_m, pred_typing)
        else:
            # rule = self.get_rule(graph_id)
            # lhs_nodes = rule.lhs.nodes()
            # rhs_nodes = rule.rhs.nodes()
            graph_nodes = self.get_graph(graph_id).nodes()

            lhs_typing, rhs_typing = pred_typing
            pred_m_origin_m_lhs, _, pred_m_origin_m_rhs = pred_m_origin_m

            lhs_hom = get_unique_map_to_pullback(
                graph_nodes,
                g_m_g,
                graph_m_origin_m,
                lhs_typing,
                pred_m_origin_m_lhs)

            rhs_hom = get_unique_map_to_pullback(
                graph_nodes,
                g_m_g,
                graph_m_origin_m,
                rhs_typing,
                pred_m_origin_m_lhs)
            return (lhs_hom, rhs_hom)
