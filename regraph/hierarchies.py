"""Graph hierarchy related abstract data structures.

This module contains abstact data structures for
graph hierarchies. A graph hierarchy is a DAG, whose nodes
are graphs and whose directed edges represent
homomorphisms between graphs. In addition, hierarchies are
equipped with relations on graphs (which can be thought of as
undirected edges or, alternatively, spans).
"""

from abc import ABC, abstractmethod
import copy
import json

import os

from regraph.exceptions import (HierarchyError,
                                ReGraphError,
                                InvalidHomomorphism,
                                RewritingError)

from regraph.category_utils import (compose,
                                    check_homomorphism,
                                    relation_to_span,
                                    pushout,
                                    get_unique_map_to_pullback,
                                    get_unique_map_from_pushout,
                                    is_monic,
                                    pullback,
                                    image_factorization,
                                    get_unique_map_to_pullback_complement)
from regraph.rules import Rule
from regraph.utils import (attrs_from_json,
                           attrs_to_json,
                           keys_by_value,
                           normalize_typing_relation,
                           test_strictness)


class Hierarchy(ABC):
    """Abstract class for graph hierarchy objects in ReGraph.

    A graph hierarchy is a DAG, where nodes are graphs with attributes and
    edges are homomorphisms representing graph typing in the system.
    """

    @abstractmethod
    def graphs(self, data=False):
        """Return a list of graphs in the hierarchy."""
        pass

    @abstractmethod
    def typings(self, data=False):
        """Return a list of graph typing edges in the hierarchy."""
        pass

    @abstractmethod
    def relations(self, data=False):
        """Return a list of relations."""
        pass

    @abstractmethod
    def successors(self, node_id):
        """Return the set of successors."""
        pass

    @abstractmethod
    def predecessors(self, node_id):
        """Return the set of predecessors."""
        pass

    @abstractmethod
    def get_graph(self, graph_id):
        """Get a graph object associated to the node 'graph_id'."""
        pass

    @abstractmethod
    def get_typing(self, source_id, target_id):
        """Get a typing dict associated to the edge 'source_id->target_id'."""
        pass

    @abstractmethod
    def get_relation(self, left_id, right_id):
        """Get a relation dict associated to the rel 'left_id->target_id'."""
        pass

    @abstractmethod
    def get_graph_attrs(self, graph_id):
        """Get attributes of a graph in the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph
        """
        pass

    @abstractmethod
    def set_graph_attrs(self, node_id, attrs):
        """Set attributes of a graph in the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph
        """
        pass

    @abstractmethod
    def get_typing_attrs(self, source, target):
        """Get attributes of a typing in the hierarchy.

        Parameters
        ----------
        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        pass

    @abstractmethod
    def set_typing_attrs(self, source, target, attrs):
        """Set attributes of a typing in the hierarchy.

        Parameters
        ----------
        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        pass

    @abstractmethod
    def get_relation_attrs(self, left, right):
        """Get attributes of a reltion in the hierarchy.

        Parameters
        ----------
        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
        """
        pass

    @abstractmethod
    def set_relation_attrs(self, left, right, attrs):
        """Set attributes of a relation in the hierarchy.

        Parameters
        ----------
        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
        """
        pass

    @abstractmethod
    def set_node_relation(self, left_graph, right_graph, left_node,
                          right_node):
        """Set relation for a particular node.

        Parameters
        ----------
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def add_empty_graph(self, graph_id, attrs=None):
        """"Add a new empty graph to the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        graph_attrs : dict, optional
            Dictionary containing attributes of the new node
        """
        pass

    @abstractmethod
    def add_typing(self, source, target, mapping, attrs=None):
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
        attrs : dict
            Dictionary containing attributes of the new
            typing edge

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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        node_id
            Id of a graph to remove
        reconnect : bool
            Reconnect the descendants of the removed node to
            its predecessors

        Raises
        ------
        HierarchyError
            If graph with `node_id` is not defined in the hierarchy
        """
        pass

    @abstractmethod
    def remove_typing(self, s, t):
        """Remove a typing from the hierarchy."""
        pass

    @abstractmethod
    def remove_relation(self, left, right):
        """Remove a relation from the hierarchy."""
        pass

    @abstractmethod
    def bfs_tree(self, graph, reverse=False):
        """BFS tree from the graph to all other reachable graphs."""
        pass

    @abstractmethod
    def shortest_path(self, source, target):
        """Shortest path from 'source' to 'target'."""
        pass

    @abstractmethod
    def copy_graph(self, graph_id, new_graph_id, attach_graphs=[]):
        """Create a copy of a graph in a hierarchy."""
        pass

    @abstractmethod
    def relabel_graph_node(self, graph_id, node, new_name):
        """Rename a node in a graph of the hierarchy."""
        pass

    @abstractmethod
    def relabel_graph(self, graph_id, new_graph_id):
        """Relabel a graph in the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph to relabel
        new_graph_id : hashable
            New graph id to assign to this graph
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def _update_mapping(self, source, target, mapping):
        """Update the mapping dictionary from source to target."""
        pass

    @abstractmethod
    def _update_relation(self, left, right, relation):
        """Update the relation dictionaries (left and right)."""
        pass

    # Implemented methods

    def __str__(self):
        """String representation of the hierarchy."""
        res = ""
        res += "\nGraphs:\n"
        for n, attrs in self.graphs(True):
            res += "\n{} {}\n".format(n, attrs)
        res += "\nTyping homomorphisms: \n"
        for n1, n2, attrs in self.typings(True):
            res += "{} -> {}: {}\n".format(
                n1, n2, attrs)
        res += "\nRelations:\n"
        for n1, n2, attrs in self.relations(True):
            res += "{}-{}: {}\n".format(
                n1, n2, attrs)

        return res

    def __eq__(self, hierarchy):
        """Hierarchy equality test."""
        for node, attrs in self.graphs(True):
            if node not in hierarchy.graphs():
                return False
            if attrs != hierarchy.get_graph_attrs(node):
                return False

        for s, t, attrs in self.typings(True):
            if (s, t) not in hierarchy.edges():
                return False
            if attrs != hierarchy.get_typing_attrs(s, t):
                return False

        for n1, n2, attrs in self.relations(True):
            if (n1, n2) not in hierarchy.relations() and\
               (n2, n1) not in hierarchy.relations():
                return False
            if attrs != hierarchy.get_relation_attrs(n1, n2):
                return False

        return True

    def __ne__(self, hierarchy):
        """Non-equality operator."""
        return not (self == hierarchy)

    def add_graph_from_json(self, graph_id, json_data, attrs=None):
        """Add a new graph to the hirarchy from its JSON-reprsentation.

        Parameters
        ----------
        graph_id : hashable
            Id of the new graph
        json_data : dict
            JSON-like dictionary containing the representation of the graph
        attrs : dict
            Attributes to attach to the new graph
        """
        node_list = []
        edge_list = []
        for n in json_data["nodes"]:
            node_list.append((n["id"], attrs_from_json(n["attrs"])))
        for e in json_data["edges"]:
            edge_list.append((e["from"], e["to"], attrs_from_json(e["attrs"])))
        self.add_graph_from_data(graph_id, node_list, edge_list, attrs)

    def to_json(self, rename_nodes=None):
        """Return json representation of the hierarchy.

        Parameters
        ----------
        rename_nodes : dict, optional
            Dictionary specifying mapping of node ids
            from the original graph to its JSON-representation
        """
        json_data = {
            "graphs": [],
            "typing": [],
            "relations": []
        }
        for node, attrs in self.graphs(True):
            if rename_nodes and node in rename_nodes.keys():
                node_id = rename_nodes[node]
            else:
                node_id = node

            json_data["graphs"].append({
                "id": node_id,
                "graph": self.get_graph(node).to_json(),
                "attrs": attrs_to_json(attrs)
            })

        for s, t, attrs in self.typings(True):
            if rename_nodes and s in rename_nodes.keys():
                s_id = rename_nodes[s]
            else:
                s_id = s
            if rename_nodes and t in rename_nodes.keys():
                t_id = rename_nodes[t]
            else:
                t_id = t
            json_data["typing"].append({
                "from": s_id,
                "to": t_id,
                "mapping": self.get_typing(s, t),
                "attrs": attrs_to_json(attrs)
            })

        visited = set()
        for u, v, attrs in self.relations(True):
            if rename_nodes and u in rename_nodes.keys():
                u_id = rename_nodes[u]
            else:
                u_id = u
            if rename_nodes and v in rename_nodes.keys():
                v_id = rename_nodes[v]
            else:
                v_id = v
            if not (u, v) in visited and not (v, u) in visited:
                visited.add((u, v))
                json_data["relations"].append({
                    "from": u_id,
                    "to": v_id,
                    "rel": {
                        a: list(b) for a, b in self.get_relation(u, v).items()
                    },
                    "attrs": attrs_to_json(attrs)
                })

        return json_data

    @classmethod
    def from_json(cls, json_data, ignore=None):
        """Create a hierarchy object from JSON-representation.

        Parameters
        ----------
        json_data : dict
            JSON-like dict containing representation of a hierarchy
        ignore : dict, optional
            Dictionary containing components to ignore in the process
            of converting from JSON, dictionary should respect the
            following format:
            {
                "graphs": <collection of ids of graphs to ignore>,
                "rules": <collection of ids of rules to ignore>,
                "typing": <collection of tuples containing typing
                    edges to ignore>,
                "rule_typing": <collection of tuples containing rule
                    typing edges to ignore>>,
                "relations": <collection of tuples containing
                    relations to ignore>,
            }

        Returns
        -------
        hierarchy : regraph.hierarchies.Hierarchy
        """
        hierarchy = cls()

        # add graphs
        for graph_data in json_data["graphs"]:
            if ignore is not None and\
               "graphs" in ignore.keys() and\
               graph_data["id"] in ignore["graphs"]:
                pass
            else:
                if "attrs" not in graph_data.keys():
                    attrs = dict()
                else:
                    attrs = attrs_from_json(graph_data["attrs"])
                hierarchy.add_graph_from_json(
                    graph_data["id"], graph_data["graph"], attrs)

        # add typing
        for typing_data in json_data["typing"]:
            if ignore is not None and\
               "typing" in ignore.keys() and\
               (typing_data["from"], typing_data["to"]) in ignore["typing"]:
                pass
            else:
                if "attrs" not in typing_data.keys():
                    attrs = dict()
                else:
                    attrs = attrs_from_json(typing_data["attrs"])
                hierarchy.add_typing(
                    typing_data["from"],
                    typing_data["to"],
                    typing_data["mapping"],
                    attrs)

        # add relations
        for relation_data in json_data["relations"]:
            from_g = relation_data["from"]
            to_g = relation_data["to"]
            if ignore is not None and\
               "relations" in ignore.keys() and\
               ((from_g, to_g) in ignore["relations"] or
                    (to_g, from_g) in ignore["relations"]):
                pass
            else:
                if "attrs" not in relation_data.keys():
                    attrs = dict()
                else:
                    attrs = attrs_from_json(relation_data["attrs"])
                if (from_g, to_g) not in hierarchy.relations():
                    hierarchy.add_relation(
                        relation_data["from"],
                        relation_data["to"],
                        {a: set(b) for a, b in relation_data["rel"].items()},
                        attrs
                    )
        return hierarchy

    @classmethod
    def load(cls, filename, ignore=None):
        """Load the hierarchy from a file.

        Parameters
        ----------
        filename : str
            Path to the file containing JSON-representation of the hierarchy
        ignore : dict
            Dictionary with graph elemenets to ignore when loading
        Returns
        -------
        hierarchy : regraph.hierarchies.Hierarchy
        """
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                json_data = json.loads(f.read())
                hierarchy = cls.from_json(json_data, ignore)
            return hierarchy
        else:
            raise ReGraphError("File '{}' does not exist!".format(filename))

    def export(self, filename):
        """Export the hierarchy to a file."""
        with open(filename, 'w') as f:
            j_data = self.to_json()
            json.dump(j_data, f)

    def adjacent_relations(self, g):
        """Return a list of related graphs."""
        if g not in self.graphs():
            raise HierarchyError(
                "Graph node '{}' does not exist in the hierarchy!".format(g))
        return [
            r
            for l, r in self.relations()
            if l == g
        ]

    def node_type(self, graph_id, node_id):
        """Get a list of the immediate types of a node."""
        if graph_id not in self.graphs():
            raise HierarchyError(
                "Graph '{}' is not defined in the hierarchy!".format(graph_id)
            )
        if node_id not in self.get_graph(graph_id).nodes():
            raise HierarchyError(
                "Graph '{}'' does not have a node with id '{}'!".format(
                    graph_id, node_id)
            )
        types = dict()
        for successor in self.successors(graph_id):
            mapping = self.get_typing(graph_id, successor)
            if node_id in mapping.keys():
                types[successor] = mapping[node_id]
        return types

    def get_ancestors(self, graph_id):
        """Return ancestors of a graph with the typing morphisms."""
        ancestors = dict()
        for pred in self.predecessors(graph_id):
            typing = self.get_typing(pred, graph_id)
            pred_ancestors = self.get_ancestors(pred)
            if pred in ancestors.keys():
                ancestors.update(pred_ancestors)
            else:
                ancestors[pred] = typing
            for anc, anc_typing in pred_ancestors.items():
                if anc in ancestors.keys():
                    ancestors[anc].update(compose(anc_typing, typing))
                else:
                    ancestors[anc] = compose(anc_typing, typing)
        return ancestors

    def get_descendants(self, graph_id, maybe=None):
        """Return descendants of a graph with the typing morphisms."""
        descendants = dict()
        for successor in self.successors(graph_id):
            mapping = self.get_typing(graph_id, successor)
            typing_descendants = self.get_descendants(successor, maybe)
            if successor in descendants.keys():
                descendants[successor].update(mapping)
            else:
                descendants[successor] = mapping
            for anc, typ in typing_descendants.items():
                if anc in descendants.keys():
                    descendants[anc].update(compose(mapping, typ))
                else:
                    descendants[anc] = compose(mapping, typ)
        return descendants

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
        homomorphism = self.get_typing(s, t)
        for i in range(2, len(path)):
            s = path[i - 1]
            t = path[i]
            homomorphism = compose(
                homomorphism,
                self.get_typing(s, t)
            )
        return homomorphism

    def get_rule_hierarchy(self, origin_id, rule, instance=None,
                           p_typing=None, rhs_typing=None):
        """Find rule hierarchy corresponding to the input rewriting.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph to rewrite
        rule : regraph.Rule
            Rewriting rule
        instance : dict, optional
            Instance of the rule in the graph. If not specified,
            the identity of the left-hand side is used
        p_typing : dict
            Relations controlling backward propagation. The keys are
            ancestors of the rewritten graph, values are dictionaries
            containing individual relations between the nodes of a given
            ancestor and the preserved part of the rule
        rhs_typing : dict
            Relation controlling forward propagation. The keys are
            descendants of the rewritten graph, values are dictionaries
            containing individual relations between the right-hand
            side of the rule and the nodes of a given
            descendant
        Returns
        -------
        rule_hierarchy : dictionary
            Dictionary contains two keys: (1) `rules` whose value is
            a dictionary with id's of the graphs in the hierarchy and
            the computed propagation rules; (2) `rule_homomorphisms` whose
            value is a dictionary with pairs of graphs in the hierarchy and
            the computed homomorphisms between rules.
        """
        instance, p_typing, rhs_typing = self._check_rule_instance_typing(
            origin_id, rule, instance, p_typing, rhs_typing, False)

        instances = {origin_id: instance}
        rule_hierarchy = {
            "rules": {origin_id: rule},
            "rule_homomorphisms": {}
        }

        # Compute rules and their map to the original rule
        l_g_ls = {}  # LHS's of rule liftings to LHS of the original rule
        p_g_ps = {}  # interfaces of rule liftings to LHS of the original rule

        ancestors = self.get_ancestors(origin_id)
        descendants = self.get_descendants(origin_id)

        # Compute rule liftings
        for ancestor, origin_typing in ancestors.items():
            # Compute L_G
            l_g, l_g_g, l_g_l = pullback(
                self.get_graph(ancestor),
                rule.lhs,
                self.get_graph(origin_id),
                origin_typing,
                instance)

            # Compute canonical P_G
            canonical_p_g, p_g_l_g, p_g_p = pullback(
                l_g, rule.p, rule.lhs, l_g_l, rule.p_lhs)

            # Remove controlled things from P_G
            if ancestor in p_typing.keys():
                l_g_factorization = {
                    keys_by_value(l_g_g, k)[0]: v
                    for k, v in p_typing[ancestor].items()
                }
                p_g_nodes_to_remove = set()
                for n in canonical_p_g.nodes():
                    l_g_node = p_g_l_g[n]
                    # If corresponding L_G node is specified in
                    # the controlling relation, remove all
                    # the instances of P nodes not mentioned
                    # in this relations
                    if l_g_node in l_g_factorization.keys():
                        p_nodes = l_g_factorization[l_g_node]
                        if p_g_p[n] not in p_nodes:
                            del p_g_p[n]
                            del p_g_l_g[n]
                            p_g_nodes_to_remove.add(n)

                for n in p_g_nodes_to_remove:
                    canonical_p_g.remove_node(n)
            rule_hierarchy["rules"][ancestor] =\
                Rule(p=canonical_p_g, lhs=l_g, p_lhs=p_g_l_g)

            instances[ancestor] = l_g_g
            l_g_ls[ancestor] = l_g_l
            p_g_ps[ancestor] = p_g_p

        l_l_ts = {}  # Original rule LHS to the LHS of rule projections
        p_p_ts = {}  # Original rule interface to the inter. of rule projections
        r_r_ts = {}  # Original rule RHS to the RHS of rule projections

        # Compute rule projections
        for descendant, origin_typing in descendants.items():
            # Compute canonical P_T
            l_t, l_l_t, l_t_t = image_factorization(
                rule.lhs, self.get_graph(descendant),
                compose(instance, origin_typing))

            # Compute canonical R_T
            r_t, l_t_r_t, r_r_t = pushout(
                rule.p, l_t, rule.rhs,
                compose(rule.p_lhs, l_l_t),
                rule.p_rhs)

            # Modify P_T and R_T according to the controlling
            # relation rhs_typing
            if descendant in rhs_typing.keys():
                r_t_factorization = {
                    r_r_t[k]: v
                    for k, v in rhs_typing[descendant].items()
                }
                added_t_nodes = set()
                for n in r_t.nodes():
                    if n in r_t_factorization.keys():
                        # If corresponding R_T node is specified in
                        # the controlling relation add nodes of T
                        # that type it to P
                        t_nodes = r_t_factorization[n]
                        for t_node in t_nodes:
                            if t_node not in l_t_t.values() and\
                               t_node not in added_t_nodes:
                                new_p_node = l_t.generate_new_node_id(
                                    t_node)
                                l_t.add_node(new_p_node)
                                added_t_nodes.add(t_node)
                                l_t_r_t[new_p_node] = n
                                l_t_t[new_p_node] = t_node
                            else:
                                l_t_r_t[keys_by_value(l_t_t, t_node)[0]] = n

            rule_hierarchy["rules"][descendant] =\
                Rule(lhs=l_t, p=l_t, rhs=r_t, p_rhs=l_t_r_t)

            instances[descendant] = l_t_t
            l_l_ts[descendant] = l_l_t
            p_p_ts[descendant] = {k: l_l_t[v] for k, v in rule.p_lhs.items()}
            r_r_ts[descendant] = r_r_t

        # Compute homomorphisms between rules
        for graph_id, graph_rule in rule_hierarchy["rules"].items():
            if graph_id in ancestors:
                for successor in self.successors(graph_id):
                    old_typing = self.get_typing(graph_id, successor)
                    if successor == origin_id:
                        graph_lhs_successor_lhs = l_g_ls[graph_id]
                        graph_p_successor_p = p_g_ps[graph_id]
                        rule_hierarchy["rule_homomorphisms"][
                            (graph_id, successor)] = (
                                graph_lhs_successor_lhs,
                                graph_p_successor_p,
                                compose(
                                    graph_p_successor_p,
                                    rule_hierarchy["rules"][successor].p_rhs)
                        )
                    else:
                        l_graph_successor = compose(
                            instances[graph_id],
                            old_typing)
                        # already lifted to the successor
                        if successor in ancestors:
                            graph_rule = rule_hierarchy["rules"][graph_id]
                            suc_rule = rule_hierarchy["rules"][successor]
                            graph_lhs_successor_lhs = get_unique_map_to_pullback(
                                suc_rule.lhs.nodes(),
                                instances[successor],
                                l_g_ls[successor],
                                compose(
                                    instances[graph_id],
                                    old_typing),
                                l_g_ls[graph_id])
                            graph_p_successor_p = get_unique_map_to_pullback(
                                suc_rule.p.nodes(),
                                suc_rule.p_lhs,
                                p_g_ps[successor],
                                compose(
                                    graph_rule.p_lhs,
                                    graph_lhs_successor_lhs),
                                p_g_ps[graph_id])

                            rule_hierarchy["rule_homomorphisms"][
                                (graph_id, successor)] = (
                                    graph_lhs_successor_lhs,
                                    graph_p_successor_p,
                                    graph_p_successor_p
                            )
                        elif successor in descendants:
                            rule_hierarchy["rule_homomorphisms"][(graph_id, successor)] = (
                                compose(l_g_ls[graph_id],
                                        l_l_ts[successor]),
                                compose(p_g_ps[graph_id],
                                        p_p_ts[successor]),
                                compose(
                                    compose(p_g_ps[graph_id],
                                            rule.p_rhs),
                                    r_r_ts[successor])
                            )
                        # didn't touch the successor or projected to it
                        else:
                            pass

            if graph_id in descendants:
                for predecessor in self.predecessors(graph_id):
                    old_typing = self.get_typing(predecessor, graph_id)
                    if predecessor == origin_id:
                        predecessor_l_graph_l = l_l_ts[graph_id]
                        predecessor_p_graph_p = p_p_ts[graph_id]
                        predecessor_rhs_graph_rhs = r_r_ts[graph_id]
                        rule_hierarchy["rule_homomorphisms"][
                            (predecessor, graph_id)] = (
                                predecessor_l_graph_l,
                                predecessor_p_graph_p,
                                predecessor_rhs_graph_rhs
                        )
                    else:
                        # already projected to the predecessor
                        if predecessor in descendants:

                            l_pred_graph = compose(
                                instances[predecessor],
                                old_typing)
                            predecessor_l_graph_l = {}
                            for k, v in instances[
                                    predecessor].items():
                                predecessor_l_graph_l[k] = keys_by_value(
                                    instances[graph_id],
                                    l_pred_graph[k])[0]

                            predecessor_rhs_graph_rhs = get_unique_map_from_pushout(
                                rule_hierarchy["rules"][predecessor].rhs.nodes(),
                                rule_hierarchy["rules"][predecessor].p_rhs,
                                r_r_ts[predecessor],
                                compose(
                                    predecessor_l_graph_l,
                                    rule_hierarchy["rules"][graph_id].p_rhs),
                                r_r_ts[graph_id])

                            rule_hierarchy["rule_homomorphisms"][
                                (predecessor, graph_id)] = (
                                    predecessor_l_graph_l,
                                    predecessor_l_graph_l,
                                    predecessor_rhs_graph_rhs
                            )
                        # didn't touch the predecessor or lifter to it
                        else:
                            pass

        return rule_hierarchy, instances

    def refine_rule_hierarchy(self, rule_hierarchy, instances):
        """Refine the input rule hierarchy to its reversible version.

        Parameters
        ----------
        rule_hierarchy : dict
            Rule hierarchy to refine
        instances : dict of dict
            Dictionary containing ids of the graphs in the hierarchy as keys
            and dictionaries represening instances of the corresponding rules

        Returns
        -------
        new_instances : dict of dict
            Dictionary containing ids of the graphs in the hierarchy as keys
            and dictionaries represening new instances of the corresponding
            refined rules

        """
        new_lhs_instances = {}

        new_rules = {}
        new_rule_homomorphisms = {}

        # Refine individual rules
        for graph, rule in rule_hierarchy["rules"].items():
            # refine rule
            new_lhs_instance = rule.refine(
                self.get_graph(graph), instances[graph])
            new_lhs_instances[graph] = new_lhs_instance

        # Update rule homomorphisms
        for (source, target), (lhs_h, p_h, rhs_h) in rule_hierarchy[
                "rule_homomorphisms"].items():
            typing = self.get_typing(source, target)
            source_rule = rule_hierarchy["rules"][source]
            target_rule = rule_hierarchy["rules"][target]
            for node in source_rule.lhs.nodes():
                if node not in lhs_h.keys():
                    source_node = new_lhs_instances[source][node]
                    target_node = typing[source_node]
                    target_lhs_node = keys_by_value(
                        new_lhs_instances[target], target_node)[0]
                    lhs_h[node] = target_lhs_node

                    if node in source_rule.p_lhs.values():
                        source_p_node = keys_by_value(
                            source_rule.p_lhs, node)[0]
                        target_p_node = keys_by_value(
                            target_rule.p_lhs, target_lhs_node)[0]
                        p_h[source_p_node] = target_p_node

                        source_rhs_node = source_rule.p_rhs[source_p_node]
                        target_rhs_node = target_rule.p_rhs[target_p_node]
                        rhs_h[source_rhs_node] = target_rhs_node
            # Add necessary node attrs
            for node in source_rule.lhs.nodes():
                t_node = lhs_h[node]
                target_rule._add_node_attrs_lhs(t_node, source_rule.lhs.get_node(node))
            # Add necessary node edges
            for s_lhs_s, s_lhs_t in source_rule.lhs.edges():
                t_lhs_s = lhs_h[s_lhs_s]
                t_lhs_t = lhs_h[s_lhs_t]
                if not target_rule.lhs.exists_edge(t_lhs_s, t_lhs_t):
                    target_rule._add_edge_lhs(
                        t_lhs_s,
                        t_lhs_t,
                        source_rule.lhs.get_edge(s_lhs_s, s_lhs_t))
                else:
                    target_rule._add_edge_attrs_lhs(
                        t_lhs_s,
                        t_lhs_t,
                        source_rule.lhs.get_edge(s_lhs_s, s_lhs_t))

        # If merge is performed, add all the instances of the merged nodes
        for (source, target), (lhs_h, p_h, rhs_h) in rule_hierarchy[
                "rule_homomorphisms"].items():
            source_rule = rule_hierarchy["rules"][source]
            target_rule = rule_hierarchy["rules"][target]
            typing = self.get_typing(source, target)
            if len(target_rule.merged_nodes()) > 0:
                for rhs_node, p_nodes in target_rule.merged_nodes().items():
                    # rhs_node_instances = keys_by_value(typing, rhs_node)
                    for p_node in p_nodes:
                        lhs_node_instance = new_lhs_instances[target][
                            target_rule.p_lhs[p_node]]
                        source_nodes = [
                            n
                            for n in keys_by_value(typing, lhs_node_instance)
                        ]
                        source_nodes_to_add = [
                            s
                            for s in source_nodes
                            if s not in new_lhs_instances[source].values()
                        ]

                        for n in source_nodes_to_add:
                            lhs_s_node = source_rule.lhs.generate_new_node_id(n)
                            p_s_node, rhs_s_node = source_rule._add_node_lhs(
                                lhs_s_node)
                            # Add the instances of the new lhs node
                            new_lhs_instances[source][lhs_s_node] = n
                            # Add maps to the target for the new lhs node
                            lhs_h[lhs_s_node] = target_rule.p_lhs[p_node]
                            p_h[p_s_node] = p_node
                            rhs_h[rhs_s_node] = rhs_node

        # Add identity rules where needed
        if len(rule_hierarchy["rules"]) == 0:
            # if the are no rules in the rule hierarchy,
            # create the identity rule for every graph
            for graph in self.graphs():
                rule_hierarchy["rules"][graph] = Rule.identity_rule()
                new_lhs_instances[graph] = dict()
            for (s, t) in self.typings():
                rule_hierarchy["rule_homomorphisms"][(s, t)] = (
                    dict(), dict(), dict())
        else:
            # add identity rules where needed
            # to preserve the info on p/rhs_typing
            # add ancestors that are not included in rule hierarchy
            for graph, rule in rule_hierarchy["rules"].items():
                for ancestor, typing in self.get_ancestors(graph).items():
                    if ancestor not in rule_hierarchy["rules"] and\
                       ancestor not in new_rules:
                        # Find a typing of ancestor by the graph
                        l_pred, l_pred_pred, l_pred_l_graph = pullback(
                            self.get_graph(ancestor), rule.lhs,
                            self.get_graph(graph), typing,
                            new_lhs_instances[graph])
                        new_rules[ancestor] = Rule(p=l_pred, lhs=l_pred)
                        new_lhs_instances[ancestor] = l_pred_pred
                        r_pred_r_graph = {
                            v: rule.p_rhs[k]
                            for k, v in l_pred_l_graph.items()
                        }
                        for successor in self.successors(ancestor):
                            if successor in rule_hierarchy["rules"]:
                                if successor == graph:
                                    new_rule_homomorphisms[
                                        (ancestor, graph)] = (
                                            l_pred_l_graph, l_pred_l_graph,
                                            r_pred_r_graph
                                    )
                                else:
                                    path = self.shortest_path(graph, successor)
                                    lhs_h, p_h, rhs_h = rule_hierarchy[
                                        "rule_homomorphisms"][
                                            (path[0], path[1])]
                                    for i in range(2, len(path)):
                                        new_lhs_h, new_p_h, new_rhs_h =\
                                            rule_hierarchy[
                                                "rule_homomorphisms"][
                                                    (path[i - 1], path[i])]
                                        lhs_h = compose(lhs_h, new_lhs_h)
                                        p_h = compose(p_h, new_p_h)
                                        rhs_h = compose(rhs_h, new_rhs_h)

                                    new_rule_homomorphisms[
                                        (ancestor, successor)] = (
                                            compose(l_pred_l_graph, lhs_h),
                                            compose(l_pred_l_graph, p_h),
                                            compose(r_pred_r_graph, rhs_h)
                                    )
                            if successor in new_rules:
                                lhs_h = {
                                    k: keys_by_value(
                                        new_lhs_instances[successor],
                                        self.get_typing(
                                            ancestor, successor)[v])[0]
                                    for k, v in new_lhs_instances[
                                        ancestor].items()
                                }
                                new_rule_homomorphisms[
                                    (ancestor, successor)] = (
                                        lhs_h, lhs_h, lhs_h
                                )
                        for predecessor in self.predecessors(ancestor):
                            if predecessor in rule_hierarchy["rules"] or\
                               predecessor in new_rules:
                                lhs_h = {
                                    k: keys_by_value(
                                        new_lhs_instances[ancestor],
                                        self.get_typing(
                                            predecessor, ancestor)[v])[0]
                                    for k, v in new_lhs_instances[
                                        predecessor].items()
                                }
                                new_rule_homomorphisms[
                                    (predecessor, ancestor)] = (
                                        lhs_h, lhs_h, lhs_h
                                )

                for descendant, typing in self.get_descendants(graph).items():
                    if descendant not in rule_hierarchy["rules"] and\
                       descendant not in new_rules:
                        l_suc, l_graph_l_suc, l_suc_suc = image_factorization(
                            rule.lhs, self.get_graph(descendant),
                            compose(
                                new_lhs_instances[graph],
                                typing))
                        new_rules[descendant] = Rule(p=l_suc, lhs=l_suc)
                        new_lhs_instances[descendant] = l_suc_suc
                        p_graph_p_suc = {
                            k: l_graph_l_suc[v]
                            for k, v in rule.p_lhs.items()
                        }
                        for predecessor in self.predecessors(descendant):
                            if predecessor in rule_hierarchy["rules"]:
                                if predecessor == graph:
                                    new_rule_homomorphisms[
                                        (predecessor, descendant)] = (
                                            l_graph_l_suc,
                                            p_graph_p_suc,
                                            p_graph_p_suc
                                    )
                                else:
                                    path = self.shortest_path(
                                        predecessor, graph)
                                    lhs_h, p_h, rhs_h = rule_hierarchy[
                                        "rule_homomorphisms"][
                                            (path[0], path[1])]
                                    for i in range(2, len(path)):
                                        new_lhs_h, new_p_h, new_rhs_h =\
                                            rule_hierarchy[
                                                "rule_homomorphisms"][
                                                    (path[i - 1], path[i])]
                                        lhs_h = compose(lhs_h, new_lhs_h)
                                        p_h = compose(p_h, new_p_h)
                                        rhs_h = compose(rhs_h, new_rhs_h)
                                    new_rule_homomorphisms[
                                        (predecessor, descendant)] = (
                                            compose(lhs_h, l_graph_l_suc),
                                            compose(p_h, p_graph_p_suc),
                                            compose(rhs_h, p_graph_p_suc)
                                    )
                            if predecessor in new_rules:
                                lhs_h = {
                                    k: keys_by_value(
                                        new_lhs_instances[descendant],
                                        self.get_typing(
                                            predecessor, descendant)[v])[0]
                                    for k, v in new_lhs_instances[
                                        predecessor].items()
                                }
                                new_rule_homomorphisms[
                                    (predecessor, descendant)] = (
                                    lhs_h, lhs_h, lhs_h
                                )

                        for successor in self.successors(descendant):
                            if successor in rule_hierarchy["rules"] or\
                               successor in new_rules:
                                lhs_h = {
                                    k: keys_by_value(
                                        new_lhs_instances[successor],
                                        self.get_typing(
                                            descendant, successor)[v])[0]
                                    for k, v in new_lhs_instances[
                                        descendant].items()
                                }
                                new_rule_homomorphisms[
                                    (descendant, successor)] = (
                                        lhs_h, lhs_h, lhs_h
                                )

        rule_hierarchy["rules"].update(new_rules)
        rule_hierarchy["rule_homomorphisms"].update(
            new_rule_homomorphisms)

        return new_lhs_instances

    def unique_graph_id(self, prefix):
        """Generate a new graph id starting with a prefix."""
        if prefix not in self.graphs():
            return prefix
        i = 0
        while "{}_{}".format(prefix, i) in self.graphs():
            i += 1
        return "{}_{}".format(prefix, i)

    def duplicate_subgraph(self, graph_dict, attach_graphs=[]):
        """Duplicate a subgraph induced by the set of nodes.

        Parameters
        ----------
        graph_dict : dict
            Dictionary contaning names of graphs to duplicate as keys
            and their new IDs in the hierarchy as values
        attach_graphs : list, optional
            List of not duplicated graph IDs that should be reattached to
            the duplicated graphs, if empty, duplicated subgraph
            is disconnected from the rest of the hierarchy
        """
        old_graphs = self.graphs()
        for original, new in graph_dict.items():
            if new in old_graphs:
                raise HierarchyError(
                    "Cannot duplicate the graph '{}' as '{}': ".format(
                        original, new) +
                    "the graph '{}' ".format(new) +
                    "already exists in the hierarchy!")

        # copy graphs
        for original, new in graph_dict.items():
            self.copy_graph(original, new, attach_graphs)

        # copy typing between duplicated graphs
        visited = set()
        for g in graph_dict.keys():
            preds = [
                p for p in self.predecessors(g)
                if p in graph_dict.keys() and (p, g) not in visited]
            sucs = [
                p for p in self.successors(g)
                if p in graph_dict.keys() and (g, p) not in visited]
            for s in sucs:
                self.add_typing(
                    graph_dict[g], graph_dict[s],
                    self.get_typing(g, s))
                visited.add((g, s))
            for p in preds:
                self.add_typing(
                    graph_dict[p], graph_dict[g],
                    self.get_typing(p, g))
                visited.add((p, g))

    def relation_to_span(self, left, right, edges=False, attrs=False):
        """Convert relation to a span.

        This method computes the span of the form
        `left` <- `common` -> `right` from a binary
        symmetric relation between two graphs in
        the hierarchy.

        Parameters
        ----------
        left
            Id of the hierarchy's node represening the `left` graph
        right
            Id of the hierarchy's node represening the `right` graph
        edges : bool, optional
            If True, maximal set of edges is added to the common
            part graph
        attrs : bool, optional
            If True, maximal dict of attrs is added to the nodes of
            the common part graph

        Returns
        -------
        common : nx.(Di)Graph
            Graph representing the common part graph induced
            by the relation
        left_h : dict
            Homomorphism from the common part graph to the left
            graph of the relation
        right_h : dict
            Homomorphism from the common part graph to the right
            graph of the relation

        Raises
        ------
        HierarchyError
            If nodes corresponding to either `left` or `right` ids
            do not exist in the hierarchy, or there is no relation
            between them.
        """
        if left not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(left))
        if right not in self.nodes():
            raise HierarchyError(
                "Node '{}' is not defined in the hierarchy!".format(right))

        if (left, right) not in self.relations() and\
           (right, left) not in self.relations():
            raise HierarchyError(
                "Relation between graphs '{}' and '{}' is not defined".format(
                    left, right)
            )
        common, left_h, right_h = relation_to_span(
            self.get_graph(left),
            self.get_graph(right),
            self.get_relation(left, right),
            edges,
            attrs)
        return common, left_h, right_h

    def find_matching(self, graph_id, pattern,
                      pattern_typing=None, nodes=None):
        """Find an instance of a pattern in a specified graph.

        Parameters
        ----------
        graph_id : hashable
            Id of a graph in the hierarchy to search for matches
        pattern : Graph object
            A pattern to match
        pattern_typing : dict
            A dictionary that specifies a typing of a pattern,
            keys of the dictionary -- graph id that types a pattern, this graph
            should be among parents of the `graph_id` graph;
            values are mappings of nodes from pattern to the typing graph;
        nodes : iterable
            Subset of nodes where matching should be performed

        Returns
        -------
        instances : list of dict
            List of matched instances
        """
        if pattern_typing is None:
            pattern_typing = dict()

        # Check that 'typing_graph' and 'pattern_typing' are correctly
        # specified
        descendants = self.get_descendants(graph_id)
        if pattern_typing is not None:
            for typing_graph, _ in pattern_typing.items():
                if typing_graph not in descendants.keys():
                    raise HierarchyError(
                        "Pattern typing graph '{}' is not in "
                        "the (transitive) typing graphs of '{}'!".format(
                            typing_graph, graph_id)
                    )

            # Check pattern typing is a valid homomorphism
            for typing_graph, mapping in pattern_typing.items():
                try:
                    check_homomorphism(
                        pattern,
                        self.get_graph(typing_graph),
                        mapping
                    )
                except InvalidHomomorphism as e:
                    raise ReGraphError(
                        "Specified pattern is not valid in the "
                        "hierarchy (it produces the following error: "
                        "{}) ".format(e)
                    )

        graph_typing = {
            typing_graph: self.get_typing(graph_id, typing_graph)
            for typing_graph in pattern_typing.keys()
        }
        instances = self.get_graph(graph_id).find_matching(
            pattern, nodes, graph_typing, pattern_typing)
        return instances

    def rewrite(self, graph_id, rule, instance,
                p_typing=None, rhs_typing=None, strict=False):
        """Rewrite and propagate the changes backward & forward.

        Rewriting in the hierarchy cosists of an application of the
        SqPO-rewriting rule (given by the 'rule' parameter) to a
        graph in the hierarchy. Such rewriting often triggers a set of
        changes that are applied to other graphs and homomorphisms in the
        hierarchy, which are necessary to ensure that the hierarchy stays
        consistent. If the rule is restrictive (deletes nodes/edges/attrs
        or clones nodes), in general, the respective changes to all the graphs
        (transitively) typed by the graph subject to rewriting are made.
        On the other hand, if the rule is relaxing (adds nodes/edges/attrs
        or merges nodes), in general, the respective changes to all the graphs
        that (tansitively) type the graph subject to rewriting are made.


        Parameters
        ----------
        graph_id
            Id of the graph in the hierarchy to rewrite
        rule : regraph.rule.Rule
            Rule object to apply
        instance : dict, optional
            Dictionary containing an instance of the lhs of the rule in
            the graph subject to rewriting, by default, tries to construct
            identity morphism of the nodes of the pattern
        p_typing : dict, optional
            Dictionary containing typing of graphs in the hierarchy by the
            interface of the rule, keys are ids of hierarchy graphs,
            values are dictionaries containing the mapping of nodes from
            the hierarchy graphs to the inteface nodes (note that a node
            from a graph can be typed by a set of nodes in
            the interface of the rule, e.g. if we want to perform
            cloning of some types, etc).
        rhs_typing : dict, optional
            Dictionary containing typing of the rhs by graphs of the hierarchy,
            keys are ids of hierarchy graphs, values are dictionaries
            containing the mapping of nodes from the rhs to the nodes of
            the typing graph given by the respective key of the value
            (note that a node from the rhs can be typed by a set of nodes of
            some graph, e.g. if we want to perform merging of some types, etc).
        strict : bool, optional
            Rewriting is strict when propagation down is not allowed

        Raises
        ------
        HierarchyError
            If the graph is not in the database
        RewritingError
            If the provided p and rhs typing are inconsistent
        """
        # Type check the input rule, its instance and typing
        instance, p_typing, rhs_typing = self._check_rule_instance_typing(
            graph_id, rule, instance, p_typing, rhs_typing, strict)

        # Perform a restrictive rewrite
        p_g_m, g_m_g = self._restrictive_rewrite(graph_id, rule, instance)

        # Propagate backward and fix broken homomorphisms
        self._propagate_backward(
            graph_id, rule, instance, p_g_m, g_m_g, p_typing)

        # Propagate forward and fix broken homomorphisms
        rhs_g_prime = self._expansive_rewrite_and_propagate_forward(
            graph_id, rule, instance, p_g_m, rhs_typing)

        return rhs_g_prime

    def new_apply_rule_hierarchy(self, rule_hierarchy, instances):
        """Apply rule hierarchy.

        Parameters
        ----------
        rule_hierarchy : dict
            Dictionary containing the input rule hierarchy
        instances : dict
            Dictionary containing an instance for every rule in the hierarchy

        Returns
        -------
        rhs_instances : dict
            Dictionary containing the RHS instances for every
            graph in the hierarchy
        """
        # Check if the rule hierarchy is applicable
        self._check_applicability(rule_hierarchy, instances)
        pass

    def apply_rule_hierarchy(self, rule_hierarchy, instances):
        """Apply rule hierarchy.

        Parameters
        ----------
        rule_hierarchy : dict
            Dictionary containing the input rule hierarchy
        instances : dict
            Dictionary containing an instance for every rule in the hierarchy

        Returns
        -------
        rhs_instances : dict
            Dictionary containing the RHS instances for every
            graph in the hierarchy
        """
        # Check if the rule hierarchy is applicable
        self._check_applicability(rule_hierarchy, instances)

        updated_graphs = {}
        # Apply rules to the hierarchy
        for graph_id, rule in rule_hierarchy["rules"].items():
            instance = instances[graph_id]
            graph_obj = self.get_graph(graph_id)

            if rule.is_restrictive():
                p_g_m, g_m_g = self._restrictive_rewrite(
                    graph_id, rule, instance)
            else:
                p_g_m = {
                    k: instance[v]
                    for k, v in rule.p_lhs.items()
                }
                g_m_g = {
                    n: n for n in graph_obj.nodes()
                }
            updated_graphs[graph_id] = {
                "p_g_m": p_g_m,
                "g_m_g": g_m_g
            }

        # Restore homomorphisms after restrictive rewrite
        # and backward propagation
        for (source, target), (_, p_h, _) in rule_hierarchy[
                "rule_homomorphisms"].items():
            old_typing = self.get_typing(source, target)
            source_m_target_m = get_unique_map_to_pullback_complement(
                updated_graphs[target]["p_g_m"],
                updated_graphs[target]["g_m_g"],
                p_h,
                updated_graphs[source]["p_g_m"],
                compose(
                    updated_graphs[source]["g_m_g"],
                    old_typing)
            )
            self._update_mapping(source, target, source_m_target_m)

        for graph_id, rule in rule_hierarchy["rules"].items():
            graph_obj = self.get_graph(graph_id)
            if rule.is_relaxing():
                r_g_prime, g_m_g_prime = self._expansive_rewrite(
                    graph_id, rule, updated_graphs[graph_id]["p_g_m"])
            else:
                g_m_g_prime = {
                    n: n for n in graph_obj.nodes()
                }
                r_g_prime = {
                    v: updated_graphs[graph_id]["p_g_m"][k]
                    for k, v in rule.p_rhs.items()
                }

            updated_graphs[graph_id] = {
                "g_m_g_prime": g_m_g_prime,
                "r_g_prime": r_g_prime
            }

        # Restore homomorphisms after expansive rewrite
        # and forward propagation
        for (source, target), (_, _, rhs_h) in rule_hierarchy[
                "rule_homomorphisms"].items():
            old_typing = self.get_typing(source, target)
            source_p_target_p = get_unique_map_from_pushout(
                self.get_graph(source).nodes(),
                updated_graphs[source]["g_m_g_prime"],
                updated_graphs[source]["r_g_prime"],
                compose(
                    old_typing,
                    updated_graphs[target]["g_m_g_prime"]),
                compose(
                    rhs_h,
                    updated_graphs[target]["r_g_prime"])
            )
            self._update_mapping(source, target, source_p_target_p)

        return {k: v["r_g_prime"] for k, v in updated_graphs.items()}

    def _check_rule_instance_typing(self, origin_id, rule, instance,
                                    p_typing, rhs_typing, strict):
        # Normalize the instance, p_typing and rhs_typing
        if instance is None:
            instance = {
                n: n for n in rule.lhs.nodes()
            }

        if p_typing is None:
            p_typing = dict()
        else:
            p_typing = normalize_typing_relation(p_typing)
        if rhs_typing is None:
            rhs_typing = dict()
        else:
            rhs_typing = normalize_typing_relation(rhs_typing)

        # Check that the instance is valid
        try:
            check_homomorphism(
                rule.lhs,
                self.get_graph(origin_id),
                instance,
                total=True
            )
        except InvalidHomomorphism as e:
            raise RewritingError(
                "Homomorphism from the pattern to the instance subgraph "
                "is not valid, got: '{}'".format(e))

        # Check that the instance is a mono
        if not is_monic(instance):
            raise RewritingError(
                "Homomorphism from the pattern to the instance subgraph "
                "is not injective")

        # Check p_typing does not retype nodes
        for graph_id, typing in p_typing.items():
            graph_to_origin = self.get_typing(graph_id, origin_id)
            for k, v in typing.items():
                for vv in v:
                    if graph_to_origin[k] != instance[rule.p_lhs[vv]]:
                        raise RewritingError(
                            "The specified typing of '{}' ".format(graph_id) +
                            "by the interface is not valid: "
                            "node '{}' is typed by '{}' ".format(
                                k, graph_to_origin[k]) +
                            "in the origin of rewriting, while the interface "
                            "node '{}' is typed by '{}'.".format(
                                vv, instance[rule.p_lhs[vv]]))

        # Check composability of p_typing
        for graph_id, typing in p_typing.items():
            predecessors = self.predecessors(graph_id)
            for pred in predecessors:
                if pred not in p_typing:
                    # check that the typing of 'graph_id' is canonical
                    canonical = False
                    for graph_n, p_nodes in typing.items():
                        if len(p_nodes) > 0:
                            lhs_n = rule.p_lhs[list(p_nodes)[0]]
                            canonical_clones = set(keys_by_value(rule.p_lhs, lhs_n))
                            if p_nodes == canonical_clones:
                                canonical = False
                    if not canonical:
                        raise RewritingError(
                            "Typing of '{}' by the interface ".format(
                                graph_id) +
                            "is not composable with the "
                            "typig of '{}': ".format(pred) +
                            "propagation to '{}' ".format(pred) +
                            "is canonical and produces instances for {}, ".format(
                                canonical_clones) +
                            "while propagation to '{}' ".format(
                                graph_id) +
                            "produces only for '{}' ".format(
                                p_nodes)
                        )
            successors = self.successors(graph_id)
            for suc in successors:
                suc_typing = self.get_typing(graph_id, suc)
                # check p_typing for suc is composable
                for graph_n, p_nodes in typing.items():
                    suc_n = suc_typing[graph_n]
                    if suc in p_typing and suc_n in p_typing[suc]:
                        suc_p_nodes = p_typing[suc][suc_n]
                        if not p_nodes.issubset(suc_p_nodes):
                            raise RewritingError(
                                "Typing of '{}' by the interface ".format(
                                    graph_id) +
                                "is not composable with the "
                                "typig of '{}': ".format(suc) +
                                "propagation to the node "
                                "'{}' of '{}' ".format(graph_n, graph_id) +
                                "will produce instances for {} ".format(
                                    p_nodes) +
                                "while propagation to '{}' ".format(
                                    suc_n) +
                                "typing it produces only {} ".format(
                                    suc_p_nodes)
                            )
                    else:
                        # ok, because suc_n is canonically cloned
                        pass

        # Autocomplete and check rhs_typing
        new_rhs_typing = {}
        for graph_id, typing in rhs_typing.items():
            for descendant, descendant_typing in self.get_descendants(
                    graph_id).items():
                if descendant not in rhs_typing:
                    # autocomplete descendant typing in the new rhs typing
                    new_rhs_typing[descendant] = {
                        rhs_n: {
                            descendant_typing[graph_n]
                            for graph_n in graph_ns
                        }
                        for rhs_n, graph_ns in typing.items()
                    }
                else:
                    # autocomplete descendant typing with missing rhs nodes
                    # and check that already specified types for descendant
                    # are composable with the typing for 'graph_id'
                    descendant_rhs_typing = rhs_typing[descendant]
                    for rhs_n, graph_ns in typing.items():
                        if rhs_n in descendant_rhs_typing:
                            descendant_ns = descendant_rhs_typing[rhs_n]
                            for graph_n in graph_ns:
                                if descendant_typing[graph_n] not in descendant_ns:
                                    raise RewritingError(
                                        "Typing of the RHS "
                                        "by '{}' is not composable ".format(
                                            graph_id) +
                                        "with its typing by '{}': ".format(
                                            descendant) +
                                        "node '{}' is typed by '{}' ".format(
                                            rhs_n, graph_n) +
                                        "in '{}' that is not typed by ".format(
                                            graph_id) +
                                        "either of {} from '{}'".format(
                                            descendant_ns, descendant)
                                    )

                        else:
                            new_rhs_typing[descendant] = rhs_typing[descendant]
                            new_rhs_typing[descendant][rhs_n] = {
                                descendant_typing[graph_n]
                                for graph_n in graph_ns
                            }

        for g, t in new_rhs_typing.items():
            rhs_typing[g] = t

        # Check rhs_typing does not retype nodes
        for graph_id, typing in rhs_typing.items():
            origin_to_graph = self.get_typing(origin_id, graph_id)
            for k, v in typing.items():
                p_nodes = keys_by_value(rule.p_rhs, k)
                if len(p_nodes) > 0:
                    graph_nodes = set([
                        origin_to_graph[instance[rule.p_lhs[p_node]]]
                        for p_node in p_nodes])
                    if graph_nodes != v:
                        raise RewritingError(
                            "The specified typing of the RHS "
                            "by the graph '{}' ".format(graph_id) +
                            "is not valid: "
                            "node '{}' is a typed by {} ".format(
                                k, graph_nodes) +
                            "in the origin of rewriting, while it is "
                            "typed by {} in the typing.".format(v))

        # If rewriting is strict, check p_typing types all clones,
        # there are no instances of removed elements and
        # and rhs typing types all new nodes and no different
        # types are merged
        if strict is True:
            test_strictness(self, origin_id, rule, instance, p_typing, rhs_typing)

        return instance, p_typing, rhs_typing

    def _restrictive_rewrite(self, graph_id, rule, instance):
        """Perform a restrictive rewrite of the specified graph.

        This method rewrites the graph and updates its typing by
        the immediate successors. Note that as the result of this
        update, some homomorphisms (from ancestors) are broken!
        """
        # Extract the restrictive part of the rule
        restrictive_rule = Rule(p=rule.p, lhs=rule.lhs, p_lhs=rule.p_lhs)
        g = self.get_graph(graph_id)
        p_g_m = g.rewrite(
            restrictive_rule, instance)
        g_m_g = {
            v: instance[restrictive_rule.p_lhs[k]] for k, v in p_g_m.items()
        }
        g_m_g.update(
            {
                n: n for n in g.nodes() if n not in p_g_m.values()
            })
        self._restrictive_update_incident_homs(graph_id, g_m_g)
        self._restrictive_update_incident_rels(graph_id, g_m_g)

        return p_g_m, g_m_g

    def _expansive_rewrite(self, graph_id, rule, instance):
        """Perform an expansive rewrite of the specified graph.

        This method rewrites the graph and updates its typing by
        the immediate predecessors. Note that as the result of this
        update, some homomorphisms (to descendants) are broken!
        """
        # Extract the expansive part of the rule
        expansive_rule = Rule(p=rule.p, rhs=rule.rhs, p_rhs=rule.p_rhs)
        g = self.get_graph(graph_id)

        pred_typings = {
            p: self.get_typing(p, graph_id)
            for p in self.predecessors(graph_id)
        }

        adj_relations = {
            a: self.get_relation(graph_id, a)
            for a in self.adjacent_relations(graph_id)
        }
        r_g_prime = g.rewrite(
            expansive_rule, instance)

        g_m_g_prime = {
            v: r_g_prime[expansive_rule.p_rhs[k]] for k, v in instance.items()
        }
        g_m_g_prime.update(
            {
                n: n for n in g.nodes() if n not in instance.values()
            })
        self._expansive_update_incident_homs(graph_id, g_m_g_prime, pred_typings)
        self._expansive_update_incident_rels(graph_id, g_m_g_prime, adj_relations)
        return r_g_prime, g_m_g_prime

    def _compose_backward(self, pred_id, graph_id, g_m_g, graph_m_origin_m,
                          pred_m_origin_m, pred_typing):
        graph_nodes = self.get_graph(graph_id).nodes()
        return get_unique_map_to_pullback(
            graph_nodes,
            g_m_g,
            graph_m_origin_m,
            pred_typing,
            pred_m_origin_m)

    def _propagate_backward(self, origin_id, rule, instance, p_origin_m,
                            origin_m_origin, p_typing):
        """Peform backward propagation of the original rewriting.

        Parameters
        ----------

        Returns
        -------
        """
        g_m_gs = {origin_id: origin_m_origin}
        g_m_origin_ms = {}

        for graph_id in self.bfs_tree(origin_id, reverse=True):
            graph_p_typing = {}
            if graph_id in p_typing.keys():
                graph_p_typing = p_typing[graph_id]

            origin_typing = self.get_typing(graph_id, origin_id)

            g_m_g = self._get_identity_map(graph_id)

            g_m_origin_m = copy.deepcopy(origin_typing)
            # Propagate node clones
            if len(rule.cloned_nodes()) > 0:
                self._propagate_clone(
                    origin_id, graph_id, p_origin_m,
                    origin_m_origin, graph_p_typing,
                    g_m_g, g_m_origin_m)

            # Propagate node deletes
            if len(rule.removed_nodes()) > 0:
                self._propagate_node_removal(
                    origin_id, graph_id, rule, instance,
                    g_m_g, g_m_origin_m)

            # Propagate node attrs deletes
            if len(rule.removed_node_attrs()) > 0:
                self._propagate_node_attrs_removal(
                    origin_id, graph_id, rule,
                    p_origin_m, g_m_origin_m)

            # Propagate edge deletes
            if len(rule.removed_edges()) > 0:
                self._propagate_edge_removal(
                    origin_id, graph_id, g_m_origin_m)

            # Propagate edge attrs deletes
            if len(rule.removed_edge_attrs()) > 0:
                self._propagate_edge_attrs_removal(
                    origin_id, graph_id, rule, p_origin_m,
                    g_m_origin_m)

            g_m_gs[graph_id] = g_m_g
            g_m_origin_ms[graph_id] = g_m_origin_m

        # Reconnect broken homomorphisms by composability
        for graph_id, g_m_g in g_m_gs.items():
            for pred in self.predecessors(graph_id):
                pred_typing = self.get_typing(pred, graph_id)
                if graph_id != origin_id:
                    pred_graph = self._compose_backward(
                        pred,
                        graph_id,
                        g_m_g,
                        g_m_origin_ms[graph_id],
                        g_m_origin_ms[pred],
                        pred_typing)
                else:
                    pred_graph = g_m_origin_ms[pred]

                self._update_mapping(pred, graph_id, pred_graph)

    def _expansive_rewrite_and_propagate_forward(self, origin_id, rule,
                                                 instance, p_origin_m,
                                                 rhs_typing):
        bfs_tree = self.bfs_tree(origin_id)
        bfs_tree.reverse()

        g_g_primes = {}
        rhs_g_primes = {}

        for graph in bfs_tree:

            origin_typing = self.get_typing(origin_id, graph)

            rhs_graph_typing = {}
            if graph in rhs_typing.keys():
                rhs_graph_typing = rhs_typing[graph]

            g_g_prime = {
                n: n for n in self.get_graph(graph).nodes()
            }

            rhs_g_prime = compose(p_origin_m, origin_typing)

            pred_typings = {
                p: self.get_typing(p, graph)
                for p in self.predecessors(graph)
            }
            adj_relations = {
                a: self.get_relation(graph, a)
                for a in self.adjacent_relations(graph)
            }

            # Propagate node merges
            if len(rule.merged_nodes()) > 0:
                self._propagate_merge(
                    origin_id, graph, rule,
                    p_origin_m, g_g_prime, rhs_g_prime)

            # Propagate node additions
            if len(rule.added_nodes()) > 0:
                self._propagate_node_addition(
                    origin_id, graph, rule,
                    rhs_graph_typing,
                    g_g_prime, rhs_g_prime)

            self._expansive_update_incident_homs(
                graph, g_g_prime, pred_typings)
            self._expansive_update_incident_rels(
                graph, g_g_prime, adj_relations)

            # Propagate node attrs additions
            if len(rule.added_node_attrs()) > 0:
                self._propagate_node_attrs_addition(
                    origin_id, graph, rule,
                    rhs_g_prime)

            # Propagate edge additions
            if len(rule.added_edges()) > 0:
                self._propagate_edge_addition(
                    origin_id, graph, rule,
                    rhs_g_prime)

            # Propagate edge attrs additions
            if len(rule.added_edge_attrs()) > 0:
                self._propagate_edge_attrs_addition(
                    origin_id, graph, rule,
                    rhs_g_prime)

            g_g_primes[graph] = g_g_prime
            rhs_g_primes[graph] = rhs_g_prime

        # Perform an expansive rewrite
        rhs_origin_prime, origin_m_origin_prime = self._expansive_rewrite(
            origin_id, rule, p_origin_m)

        rhs_g_primes[origin_id] = rhs_origin_prime
        g_g_primes[origin_id] = origin_m_origin_prime

        # Reconnect broken homomorphisms by composability
        for graph_id, g_g_prime in g_g_primes.items():
            graph_nodes = self.get_graph(graph_id).nodes()
            for suc in self.successors(graph_id):
                suc_typing = self.get_typing(graph_id, suc)
                for rhs_node in rule.rhs.nodes():
                    g_nodes = keys_by_value(
                        g_g_prime, rhs_g_primes[graph_id][rhs_node])

                    suc_node = rhs_g_primes[suc][rhs_node]
                    for n in g_nodes:
                        suc_typing[n] = suc_node

                graph_suc = get_unique_map_from_pushout(
                    graph_nodes,
                    rhs_g_primes[graph_id],
                    g_g_prime,
                    rhs_g_primes[suc],
                    suc_typing)
                self._update_mapping(graph_id, suc, graph_suc)
        return rhs_origin_prime

    @staticmethod
    def _produce_clones(origin_clones, p_origin_m, g, origin_typing, graph_p,
                        local_g_m_g, local_g_m_origin_m):
        cloned_nodes = {}
        for n, clones in origin_clones.items():
            nodes_to_clone = keys_by_value(origin_typing, n)
            for node in nodes_to_clone:
                if node in graph_p.keys():
                    p_nodes = graph_p[node]
                else:
                    p_nodes = [
                        keys_by_value(p_origin_m, c)[0] for c in clones
                    ]
                for i, p_node in enumerate(p_nodes):
                    if i == 0:
                        cloned_nodes[node] = p_node
                        local_g_m_g[node] = node
                        local_g_m_origin_m[node] = p_origin_m[p_node]
                    else:
                        new_name = g.clone_node(node)
                        cloned_nodes[new_name] = p_node
                        local_g_m_g[new_name] = node
                        local_g_m_origin_m[new_name] = p_origin_m[p_node]
        return cloned_nodes

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
        cloned_origin_nodes = {}
        for n in set(origin_m_origin.values()):
            clones = keys_by_value(origin_m_origin, n)
            if len(clones) > 1:
                cloned_origin_nodes[n] = clones

        graph = self.get_graph(node_id)
        origin_typing = self.get_typing(node_id, origin_id)

        cloned_origin_nodes = {}
        for n in set(origin_m_origin.values()):
            clones = keys_by_value(origin_m_origin, n)
            if len(clones) > 1:
                cloned_origin_nodes[n] = clones

        self._produce_clones(
            cloned_origin_nodes, p_origin_m,
            graph, origin_typing, p_typing,
            g_m_g, g_m_origin_m)

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
        graph = self.get_graph(node_id)
        origin_typing = self.get_typing(node_id, origin_id)

        for lhs_node in rule.removed_nodes():
            origin_n = instance[lhs_node]
            graph_nodes = keys_by_value(origin_typing, origin_n)
            for node in graph_nodes:
                graph.remove_node(node)
                del g_m_g[node]
                del g_m_origin_m[node]

        for node in graph.nodes():
            if node not in origin_typing.keys():
                graph.remove_node(node)
                del g_m_g[node]
                del g_m_origin_m[node]

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
        graph = self.get_graph(node_id)
        # origin_typing = self.get_typing(node_id, origin_id)
        for p_node, attrs in rule.removed_node_attrs().items():
            nodes_to_remove_attrs = keys_by_value(
                g_m_origin_m, p_origin_m[p_node])
            for node in nodes_to_remove_attrs:
                graph.remove_node_attrs(node, attrs)

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
        graph = self.get_graph(node_id)
        origin_graph = self.get_graph(origin_id)

        edges_to_remove = set()
        for s, t in graph.edges():
            origin_s = g_m_origin_m[s]
            origin_t = g_m_origin_m[t]
            if (origin_s, origin_t) not in origin_graph.edges():
                edges_to_remove.add((s, t))

        for s, t in edges_to_remove:
            graph.remove_edge(s, t)

    def _propagate_edge_attrs_removal(self, origin_id, node_id, rule, p_origin_m,
                                      g_m_origin_m):
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
        graph = self.get_graph(node_id)

        for (p_u, p_v), attrs in rule.removed_edge_attrs().items():
            us = keys_by_value(g_m_origin_m, p_origin_m[p_u])
            vs = keys_by_value(g_m_origin_m, p_origin_m[p_v])
            for u in us:
                for v in vs:
                    if (u, v) in graph.edges():
                        graph.remove_edge_attrs(u, v, attrs)

    def _propagate_merge(self, origin_id, graph_id, rule, p_origin_m,
                         g_g_prime, rhs_g_prime):
        """Propagate merges from 'origin_id' to 'graph_id'.

        Perform a propagation of merges to 'graph'

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
        rhs_origin_prime : dict
            Instance of rule's rhs inside the updated origin
        g_g_prime : dict
            Map from the nodes of the graph 'graph_id' to the updated graph
        rhs_g_prime : dict
            Map from the RHS to the updated graph with 'graph_id'
        """
        graph = self.get_graph(graph_id)

        for rhs_node, p_nodes in rule.merged_nodes().items():
            graph_nodes = set([
                rhs_g_prime[p_node]
                for p_node in p_nodes
            ])
            if len(graph_nodes) > 1:
                merged_node_id = graph.merge_nodes(graph_nodes)
                for n in graph_nodes:
                    g_g_prime[n] = merged_node_id
                for p_node in p_nodes:
                    if p_node in rhs_g_prime:
                        del rhs_g_prime[p_node]
                rhs_g_prime[rhs_node] = merged_node_id
                map_to_merge_node = set()
                for rhs_n, g_prime_n in rhs_g_prime.items():
                    if g_prime_n in graph_nodes:
                        map_to_merge_node.add(rhs_n)
                for n in map_to_merge_node:
                    rhs_g_prime[n] = merged_node_id
            else:
                for p_node in p_nodes:
                    if p_node in rhs_g_prime:
                        del rhs_g_prime[p_node]
                rhs_g_prime[rhs_node] = list(graph_nodes)[0]

    def _propagate_node_addition(self, origin_id, graph_id, rule,
                                 rhs_typing, g_g_prime, rhs_g_prime):
        """Propagate node additions from 'origin_id' to 'graph_id'.

        Perform a propagation of additions to 'graph'

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        rule : regraph.Rule
            Original rewriting rule
        rhs_origin_prime : dict
            Instance of rule's rhs inside the updated origin
        rhs_typing : dict
            Typing of the nodes from the rhs in 'graph_id'
        rhs_g_prime : dict
            Map from the RHS to the updated graph with 'graph_id'
        """
        graph = self.get_graph(graph_id)

        for rhs_node in rule.added_nodes():
            if rhs_node in rhs_typing:
                if len(rhs_typing[rhs_node]) == 1:
                    rhs_g_prime[rhs_node] = list(
                        rhs_typing[rhs_node])[0]
                else:
                    nodes_to_merge = rhs_typing[rhs_node]
                    new_node_id = graph.merge_nodes(nodes_to_merge)
                    for n in nodes_to_merge:
                        g_g_prime[n] = new_node_id
                        p_nodes = keys_by_value(rhs_g_prime, n)
                        for p_node in p_nodes:
                            if p_node in rhs_g_prime:
                                del rhs_g_prime[p_node]
                    rhs_g_prime[rhs_node] = new_node_id
                    map_to_merge_node = set()
                    for rhs_n, g_prime_n in rhs_g_prime.items():
                        if g_prime_n in nodes_to_merge:
                            map_to_merge_node.add(rhs_n)
                    for n in map_to_merge_node:
                        rhs_g_prime[n] = new_node_id
            else:
                new_node_id = graph.generate_new_node_id(rhs_node)
                graph.add_node(new_node_id)
                rhs_g_prime[rhs_node] = new_node_id

    def _propagate_node_attrs_addition(self, origin_id, graph_id, rule,
                                       rhs_g_prime):
        """Propagate node attrs additions from 'origin_id' to 'graph_id'.

        Perform a propagation of additions to 'graph'

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        rule : regraph.Rule
            Original rewriting rule
        rhs_origin_prime : dict
            Instance of rule's rhs inside the updated origin
        origin_prime_g_prime : dict
            Map from the updated origin to the updated graph with 'graph_id'
        """
        graph = self.get_graph(graph_id)

        for rhs_node, attrs in rule.added_node_attrs().items():
            graph.add_node_attrs(
                rhs_g_prime[rhs_node],
                attrs)

    def _propagate_edge_addition(self, origin_id, graph_id, rule,
                                 rhs_g_prime):
        """Propagate edge additions from 'origin_id' to 'graph_id'.

        Perform a propagation of additions to 'graph'

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        rule : regraph.Rule
            Original rewriting rule
        rhs_origin_prime : dict
            Instance of rule's rhs inside the updated origin
        origin_prime_g_prime : dict
            Map from the updated origin to the updated graph with 'graph_id'
        """
        graph = self.get_graph(graph_id)
        for s, t in rule.added_edges():
            g_s = rhs_g_prime[s]
            g_t = rhs_g_prime[t]
            if (g_s, g_t) not in graph.edges():
                graph.add_edge(g_s, g_t)

    def _propagate_edge_attrs_addition(self, origin_id, graph_id, rule,
                                       rhs_g_prime):
        """Propagate edge attrs additions from 'origin_id' to 'graph_id'.

        Perform a propagation of additions to 'graph'

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        """
        graph = self.get_graph(graph_id)
        for (s, t), attrs in rule.added_edge_attrs().items():
            g_s = rhs_g_prime[s]
            g_t = rhs_g_prime[t]
            graph.add_edge_attrs(g_s, g_t, attrs)

    def _get_identity_map(self, graph_id):
        return {
            n: n for n in self.get_graph(graph_id).nodes()
        }

    def _restrictive_update_incident_homs(self, node_id, g_m_g):
        for suc in self.successors(node_id):
            typing = self.get_typing(node_id, suc)
            self._update_mapping(node_id, suc, compose(g_m_g, typing))

    def _restrictive_update_incident_rels(self, graph_id, g_m_g):
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
        for pred, typing in pred_typings.items():
            self._update_mapping(
                pred, graph_id, compose(typing, g_m_g_prime))

    def _expansive_update_incident_rels(self, graph_id, g_m_g_prime,
                                        adj_relations):
        for related_g, rel in adj_relations.items():
            new_rel = dict()

            for node in self.get_graph(graph_id).nodes():
                new_node = g_m_g_prime[node]
                if node in rel.keys():
                    new_rel[new_node] = rel[node]

            self._update_relation(graph_id, related_g, new_rel)

    def _check_applicability(self, rule_hierarchy, instances):
        """Check if a rule hierarchy is applicable."""
        # Check that instances commute
        for (s, t) in self.typings():
            typing = self.get_typing(s, t)
            lhs_s_t1 = compose(instances[s], typing)
            lhs_s_t2 = compose(
                rule_hierarchy["rule_homomorphisms"][(s, t)][0],
                instances[t])
            if (lhs_s_t1 != lhs_s_t2):
                raise RewritingError(
                    "Instance of a specified rule for '{}' ({}) ".format(
                        s, instances[s]) +
                    "is not compatible with such instance for '{}' ({})".format(
                        t, instances[t]))

            # Check the applicability
            t_rule = rule_hierarchy["rules"][t]
            if t_rule.is_restrictive():
                # Check the square L_S -> S -> T and L_S -> L_T -> T is a PB
                for lhs_t_node in t_rule.lhs.nodes():
                    t_node = instances[t][lhs_t_node]
                    s_nodes = keys_by_value(typing, t_node)
                    if lhs_t_node in t_rule.removed_nodes():
                        for s_node in s_nodes:
                            error = False
                            if s_node not in instances[s].values():
                                error = True
                            elif keys_by_value(instances[s], s_node)[
                                    0] not in rule_hierarchy[
                                        "rules"][s].removed_nodes():
                                error = True
                            if error:
                                raise RewritingError(
                                    "Specified rule hierarchy is not applicable "
                                    "the typing of the node '{}' ".format(s_node) +
                                    "from the graph '{}' is removed ".format(s) +
                                    "by rewriting of '{}', but ".format(t) +
                                    "this node is not removed by the rule " +
                                    "applied to '{}'".format(s)
                                )

                    if lhs_t_node in t_rule.cloned_nodes():
                        for s_node in s_nodes:
                            if s_node not in instances[s].values():
                                raise RewritingError(
                                    "Specified rule hierarchy is not applicable "
                                    "the typing of the node '{}' ".format(s_node) +
                                    "from the graph '{}' is cloned ".format(s) +
                                    "by rewriting of '{}', but the ".format(t) +
                                    "retyping of this node is not specified, i.e. " +
                                    "'{}' is not in the instances of ".format(s_node) +
                                    "the rule applied to '{}'".format(s)
                                )

    def relabel_nodes(self, graph, mapping):
        """Relabel nodes of a graph in the hierarchy."""
        graph = self.get_graph(graph)
        graph.relabel_nodes(mapping)
