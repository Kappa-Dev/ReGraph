"""."""

from abc import ABC, abstractmethod
import copy
import json
import networkx as nx
import os

from regraph import propagation_utils
from regraph.exceptions import (HierarchyError,
                                ReGraphError,
                                InvalidHomomorphism,
                                RewritingError)
from regraph.graphs import NXGraph

from regraph.networkx.category_utils import (compose,
                                             check_homomorphism,
                                             right_relation_dict,
                                             pullback_complement,
                                             pushout,
                                             get_unique_map_to_pullback,
                                             get_unique_map_from_pushout,
                                             is_monic)
from regraph.utils import (attrs_from_json,
                           attrs_to_json,
                           normalize_attrs,
                           normalize_relation,
                           relation_to_span,
                           keys_by_value,
                           normalize_typing_relation)


class Hierarchy(ABC):
    """Abstract class for graph hierarchy objects in ReGraph.

    A graph hierarchy is a DAG, where nodes are graphs with attributes and
    edges are homomorphisms representing graph typing in the system.
    """

    @abstractmethod
    def graphs(self):
        """Return a list of graphs in the hierarchy."""
        pass

    @abstractmethod
    def typings(self):
        """Return a list of graph typing edges in the hierarchy."""
        pass

    @abstractmethod
    def relations(self):
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
    def get_relation(self, left_id, target_id):
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
    def add_graph_from_data(self, node_list, edge_list, attrs=None):
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
    def add_typing(self):
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
    def add_relation(self):
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
    def find_matching(self, graph_id, pattern, pattern_typing=None,
                      nodes=None):
        """Find an instance of a pattern in a specified graph.

        graph_id : hashable
            Id of a graph in the hierarchy to search for matches
        pattern : regraph.Graph or nx.DiGraph object
            A pattern to match
        pattern_typing : dict
            A dictionary that specifies a typing of a pattern,
            keys of the dictionary -- graph id that types a pattern, this graph
            should be among parents of the `graph_id` graph; values are
            mappings of nodes from pattern to the typing graph;
        nodes : iterable
            Subset of nodes where matching should be performed
        """
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
    def apply_rule_hierarchy(self, rule_hierarchy, instances):
        """Apply a rule hierarchy.

        Parameters
        ----------
        rule_hierarchy : dict
            Dictionary contraing a rule hierarchy, keys are id's of
            graphs, values are rules
        instances : dict
            Dictionary contraing rule instances from the rule hierarchy
            keys are id's of graphs, values are instance dictionaries
        """
        pass

    @abstractmethod
    def _restrictive_rewrite(self, graph_id, rule, instance):
        """Perform a restrictive rewrite of the specified graph.

        This method rewrites the graph and updates its typing by
        the immediate successors. Note that as the result of this
        update, some homomorphisms (from ancestors) are broken!
        """
        pass

    @abstractmethod
    def _expansive_rewrite(self, graph_id, rule, instance):
        """Perform an expansive rewrite of the specified graph.

        This method rewrites the graph and updates its typing by
        the immediate predecessors. Note that as the result of this
        update, some homomorphisms (to descendants) are broken!
        """
        pass

    @abstractmethod
    def _propagate_clone(self, origin_id, graph_id, p_origin_m,
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
        """
        pass

    @abstractmethod
    def _propagate_node_removal(self, origin_id, graph_id, rule, instance,
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

        """
        pass

    @abstractmethod
    def _propagate_node_attrs_removal(self, origin_id, graph_id, rule, instance):
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
        pass

    @abstractmethod
    def _propagate_edge_removal(self, origin_id, graph_id, g_m_origin_m):
        """Propagate edge removal from 'origin_id' to 'graph_id'.

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
        """
        pass

    @abstractmethod
    def _propagate_edge_attrs_removal(self, origin_id, graph_id, rule, p_origin_m):
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
        pass

    @abstractmethod
    def _propagate_merge(self, origin_id, graph_id, rule, p_origin_m,
                         rhs_origin_prime, g_g_prime, origin_prime_g_prime):
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
        origin_prime_g_prime : dict
            Map from the updated origin to the updated graph with 'graph_id'
        """
        pass

    @abstractmethod
    def _propagate_node_addition(self, origin_id, graph_id, rule,
                                 rhs_origin_prime, rhs_typing,
                                 origin_prime_g_prime):
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
        origin_prime_g_prime : dict
            Map from the updated origin to the updated graph with 'graph_id'
        """
        pass

    @abstractmethod
    def _propagate_node_attrs_addition(self, origin_id, graph_id, rule,
                                       rhs_origin_prime, origin_prime_g_prime):
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
        pass

    @abstractmethod
    def _propagate_edge_addition(self, origin_id, graph_id, rule,
                                 rhs_origin_prime, origin_prime_g_prime):
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
        pass

    @abstractmethod
    def _propagate_edge_attrs_addition(self, origin_id, graph_id, rule,
                                       rhs_origin_prime, origin_prime_g_prime):
        """Propagate edge attrs additions from 'origin_id' to 'graph_id'.

        Perform a propagation of additions to 'graph'

        Parameters
        ----------
        origin_id : hashable
            ID of the graph corresponding to the origin of rewriting
        graph_id : hashable
            ID of the graph where propagation is performed
        """
        pass

    @abstractmethod
    def _get_rule_liftings(self, graph_id, rule, instance, p_typing):
        pass

    @abstractmethod
    def _get_rule_projections(self, graph_id, rule, instance, rhs_typing):
        pass

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
                "Node '{}' is not defined in the hierarchy!".format(g))
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
        for pred, _ in self.in_edges(graph_id):
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
        for _, typing in self.out_edges(graph_id):
            mapping = self.get_typing(graph_id, typing)["mapping"]
            typing_descendants = self.get_descendants(typing, maybe)
            if typing in descendants.keys():
                descendants[typing].update(mapping)
            else:
                descendants[typing] = mapping
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
                self.typing[s][t]
            )
        return homomorphism

    def get_rule_propagations(self, graph_id, rule, instance=None,
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
        if instance is None:
            instance = {
                n: n for n in rule.lhs.nodes()
            }
        p_typing, rhs_typing = self._check_rule_instance_typing(
            self, graph_id, rule, instance, p_typing, rhs_typing, False)

        rule_hierarchy = propagation_utils.get_rule_hierarchy(
            self, graph_id, rule, instance,
            self._get_rule_liftings(graph_id, rule, instance, p_typing),
            self._get_rule_projections(graph_id, rule, instance, rhs_typing)
        )

        return rule_hierarchy

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
        new_instances = propagation_utils._refine_rule_hierarchy(
            self, rule_hierarchy, instances)
        return new_instances

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
            attrs,
            True)
        return common, left_h, right_h

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
            containing the mapping of nodes from the lhs to the nodes of
            the typing graph given by the respective key of the value
            (note that a node from the rhs can be typed by a set of nodes of
            some graph, e.g. if we want to perform merging of some types, etc).
        strict : bool, optional
            Rewriting is strict when propagation down is not allowed

        Raises
        ------
        HierarchyError
            If the graph is not in the database
        TypingWarning
            If the rhs typing is inconsistent
        """
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

        # Type check the input rule, its instance and typing
        p_typing, rhs_typing = self._check_rule_instance_typing(
            self, graph_id, rule, instance, p_typing, rhs_typing, strict)

        # Perform a restrictive rewrite
        p_g_m, g_m_g = self._restrictive_rewrite(graph_id, rule, instance)

        # Propagate backward and fix broken homomorphisms
        self._propagate_backward(
            graph_id, rule, instance, p_g_m, g_m_g, p_typing)

        # Perform an expansive rewrite
        rhs_g_prime, g_m_g_prime = self._expansive_rewrite(
            graph_id, rule, instance)

        # Propagate forward and fix broken homomorphisms
        self._propagate_forward(
            graph_id, rule, instance, rhs_g_prime, g_m_g_prime, rhs_typing)

    def _check_rule_instance_typing(self, origin_id, rule, instance,
                                    p_typing, rhs_typing, strict):

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
                            "The specified typing of the RHS"
                            "by the graph '{}' ".format(graph_id) +
                            "is not valid: "
                            "node '{}' is a merge of {} ".format(
                                k, graph_nodes) +
                            "in the origin of rewriting, while it is "
                            "typed by {} in the typing.".format(vv))

        # Check composability of p_typing
        # Check composability of rhs_typing

    def _propagate_backward(self, origin_id, rule, instance, p_origin_m,
                            origin_m_origin, p_typing):
        """Peform backward propagation of the original rewriting.

        Parameters
        ----------

        Returns
        -------
        """
        g_m_gs = {}
        g_m_origin_ms = {}
        for graph in self.bfs_tree(origin_id, reverse=True):

            graph_p_typing = {}
            if graph in p_typing.keys():
                graph_p_typing = p_typing[graph]

            g_m_g = {
                n: n for n in self.get_graph(graph)
            }
            g_m_origin_m = {
                self.get_typing(graph, origin_id)
            }

            # Propagate node clones
            if len(rule.cloned_nodes()) > 0:
                self._propagate_clone(
                    origin_id, graph, p_origin_m,
                    origin_m_origin, graph_p_typing,
                    g_m_g, g_m_origin_m)

            # Propagate node deletes
            if len(rule.removed_nodes()) > 0:
                self._propagate_node_removal(
                    origin_id, graph, rule, instance,
                    g_m_g, g_m_origin_m)

            # Propagate node attrs deletes
            if len(rule.removed_node_attrs()) > 0:
                self._propagate_node_attrs_removal(origin_id, graph, g_m_g)

            # Propagate edge deletes
            if len(rule.removed_edges()) > 0:
                self._propagate_edge_removal(
                    origin_id, graph, g_m_origin_m)

            # Propagate edge attrs deletes
            if len(rule.removed_edge_attrs()) > 0:
                self._propagate_edge_attrs_removal(
                    origin_id, graph, rule, p_origin_m)

            g_m_gs[graph] = g_m_g
            g_m_origin_ms[graph] = g_m_g

        # Reconnect broken homomorphisms by composability
        for graph_id, g_m_g in g_m_gs.items():
            graph_nodes = self.get_graph(graph_id).nodes()
            for pred in self.predecessors(graph_id):
                pred_typing = self.get_typing(pred, graph_id)
                pred_graph = get_unique_map_to_pullback(
                    graph_nodes,
                    g_m_g,
                    g_m_origin_ms[graph_id],
                    pred_typing,
                    g_m_origin_ms[pred])
                self.remove_typing(pred, graph_id)
                self.add_typing(pred, graph_id, pred_graph)

    def _propagate_forward(self, origin_id, rule, instance, p_origin_m,
                           rhs_origin_prime, origin_m_origin_prime,
                           rhs_typing):

        g_g_primes = {}
        origin_prime_g_primes = {}

        for graph in self.bfs_tree(origin_id):

            rhs_graph_typing = {}
            if graph in rhs_typing.keys():
                rhs_graph_typing = rhs_typing[graph]

            g_g_prime = {
                n: n for n in self.get_graph(graph)
            }

            origin_prime_g_prime = {
                self.get_typing(graph, origin_id)
            }

            # Propagate node merges
            if len(rule.merged_nodes()) > 0:
                self._propagate_merge(
                    origin_id, graph, rule,
                    p_origin_m, rhs_origin_prime,
                    g_g_prime, origin_prime_g_prime)

            # Propagate node additions
            if len(rule.added_nodes()) > 0:
                self._propagate_node_addition(
                    origin_id, graph, rule,
                    rhs_origin_prime, rhs_graph_typing,
                    origin_prime_g_prime)

            # Propagate node attrs additions
            if len(rule.added_node_attrs()) > 0:
                self._propagate_node_attrs_addition(
                    origin_id, graph, rule, rhs_origin_prime,
                    origin_prime_g_prime)

            # Propagate edge additions
            if len(rule.added_edges()) > 0:
                self._propagate_edge_addition(
                    origin_id, graph, rule, rhs_origin_prime,
                    origin_prime_g_prime)

            # Propagate edge attrs additions
            if len(rule.added_edge_attrs()) > 0:
                self._propagate_edge_attrs_addition(
                    origin_id, graph, rule, rhs_origin_prime,
                    origin_prime_g_prime)

            g_g_primes[graph] = g_g_prime
            origin_prime_g_primes[graph] = origin_prime_g_prime

        # Reconnect broken homomorphisms by composability
        for graph_id, g_g_prime in g_g_primes.items():
            graph_nodes = self.get_graph(graph_id).nodes()
            for suc in self.successors(graph_id):
                suc_typing = self.get_typing(graph_id, suc)
                graph_suc = get_unique_map_from_pushout(
                    graph_nodes,
                    g_g_prime,
                    origin_prime_g_primes[graph_id],
                    suc_typing, origin_prime_g_primes[suc])
                self.remove_typing(graph_id, suc)
                self.add_typing(graph_id, suc, graph_suc)


class NXHierarchy(NXGraph, Hierarchy):
    """Class for in-memory graphs.

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
                for n, n_data in self.nodes(True).items()
                if "graph" in n_data]
        else:
            return [n for n, n_data in self.nodes(True) if "graph" in n_data]

    def typings(self, data=False):
        """Return a list of graph typing edges in the hierarchy."""
        if data:
            return [
                (s, t, e_data["attrs"])
                for s, t, e_data in self.edges(True).items()
                if "mapping" in e_data]
        else:
            return [
                (s, t)
                for s, t, e_data in self.edges(True)
                if "mapping" in e_data]

    def relations(self):
        """Return a list of relations."""
        return list(set(self.relation_edges.keys()))

    def get_graph(self, graph_id):
        """Get a graph object associated to the node 'graph_id'."""
        if graph_id not in self.nodes():
            pass
        if not self.is_graph(graph_id):
            pass
        return self.node[graph_id]["graph"]

    def get_typing(self, source, target):
        """Get a typing dict associated to the edge 'source->target'."""
        if (source, target) in self.edges():
            return self.adj[source][target]["mapping"]
        else:
            try:
                path = nx.shortest_path(self, source, target)
            except:
                raise HierarchyError(
                    "No path from '{}' to '{}' in the hierarchy".format(
                        source, target))
            return self.compose_path_typing(path)

    def get_relation(self, left, right):
        """Get a relation dict associated to the rel 'left-right'."""
        return self.relation[left][right]

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
            attrs = dict()
        self.update_node_attrs(
            graph_id, {
                "graph": graph,
                "attrs": attrs
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
        if not nx.is_directed_acyclic_graph(self):
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
            total=True
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
        return nx.bfs_tree(self, graph, reverse=reverse)

    def shortest_path(self, source, target):
        """Shortest path from 'source' to 'target'."""
        return nx.shortest_path(self, source, target)

    def find_matching(self, graph_id, pattern,
                      pattern_typing=None, nodes=None):
        """Find an instance of a pattern in a specified graph.

        graph_id : hashable
            Id of a graph in the hierarchy to search for matches
        pattern : regraph.Graph or nx.DiGraph object
            A pattern to match
        pattern_typing : dict
            A dictionary that specifies a typing of a pattern,
            keys of the dictionary -- graph id that types a pattern, this graph
            should be among parents of the `graph_id` graph;
            values are mappings of nodes from pattern to the typing graph;
        nodes : iterable
            Subset of nodes where matching should be performed
        """
        if pattern_typing is None:
            pattern_typing = dict()

        if self.is_rule(graph_id):
            raise ReGraphError(
                "Pattern matching in a rule is not implemented!")

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
            self.compose_path_typing(
                nx.shortest_path(self, graph_id, typing_graph))
            for typing_graph in pattern_typing.keys()
        }

        instances = self.get_graph(graph_id).find_matching(
            pattern, nodes, graph_typing, pattern_typing)
        return instances

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
        self.relabel_nodes(mapping)

    def _check_rule_instance_typing(self, graph_id, rule, instance,
                                    p_typing, rhs_typing, strict):
        pass

    def _restrictive_rewrite(self, graph_id, rule, instance):
        """Perform a restrictive rewrite of the specified graph.

        This method rewrites the graph and updates its typing by
        the immediate successors. Note that as the result of this
        update, some homomorphisms (from ancestors) are broken!
        """
        g_m, p_g_m, g_m_g =\
            pullback_complement(rule.p, rule.lhs, self.get_graph(graph_id),
                                rule.p_lhs, instance)

        self._update_graph(graph_id, g_m)
        self._restrictive_update_incident_homs(graph_id, g_m_g)
        self._restrictive_update_adjacent_rels(graph_id, g_m_g)

        return p_g_m, g_m_g

    def _expansive_rewrite(self, graph_id, rule, instance):
        """Perform an expansive rewrite of the specified graph.

        This method rewrites the graph and updates its typing by
        the immediate predecessors. Note that as the result of this
        update, some homomorphisms (to descendants) are broken!
        """
        g_prime, g_m_g_prime, r_g_prime = pushout(
            rule.p, self.get_graph(graph_id), rule.rhs,
            instance, rule.p_rhs)

        self._update_graph(graph_id, g_prime)

        self._expansive_update_incident_homs(graph_id, g_m_g_prime)
        self._expansive_update_adjacent_rels(graph_id, g_m_g_prime)

        return g_m_g_prime, r_g_prime

    def _propagate_clone(self, origin_id, graph_id, p_origin_m,
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
        graph = self.get_graph(graph_id)
        origin_typing = self.get_typing(graph_id, origin_id)

        cloned_origin_nodes = {}
        for n in set(origin_m_origin.values()):
            clones = keys_by_value(origin_m_origin, n)
            if (clones) > 1:
                cloned_origin_nodes[n] = clones

        cloned_nodes = {}
        for n, clones in cloned_origin_nodes.items():
            nodes_to_clone = keys_by_value(origin_typing, n)
            for node in nodes_to_clone:
                cloned_nodes[node] = set()
                if node in p_typing.keys():
                    p_nodes = p_typing[node]
                else:
                    p_nodes = [
                        keys_by_value(p_origin_m, c)[0] for c in clones
                    ]
                for i, p_node in enumerate(p_nodes):
                    if i == 0:
                        g_m_g[node] = node
                        g_m_origin_m[node] = p_origin_m[p_node]
                    else:
                        new_name = graph.clone_node(node)
                        g_m_g[new_name] = node
                        g_m_origin_m[new_name] = p_origin_m[p_node]

        self._restrictive_update_incident_homs(graph_id, g_m_g)
        self._restrictive_update_adjacent_rels(graph_id, g_m_g)

        return g_m_g, g_m_origin_m

    def _propagate_node_removal(self, origin_id, graph_id, rule, instance,
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
        graph = self.get_graph(graph_id)
        origin_typing = self.get_typing(graph_id, origin_id)

        for lhs_node in rule.removed_nodes():
            origin_n = instance[lhs_node]
            graph_nodes = keys_by_value(origin_typing, origin_n)
            for node in graph_nodes:
                graph.remove_node(node)
                del g_m_g[node]
                del g_m_origin_m[node]

        self._restrictive_update_incident_homs(graph_id, g_m_g)
        self._restrictive_update_adjacent_rels(graph_id, g_m_g)

        return g_m_g, g_m_origin_m

    def _propagate_node_attrs_removal(self, origin_id, graph_id, rule, instance):
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
        graph = self.get_graph(graph_id)
        origin_typing = self.get_typing(graph_id, origin_id)
        for lhs_node, attrs in rule.removed_node_attrs().items():
            nodes_to_remove_attrs = keys_by_value(
                origin_typing, instance[lhs_node])
            for node in nodes_to_remove_attrs:
                graph.remove_node_attrs(node, attrs)

    def _propagate_edge_removal(self, origin_id, graph_id, g_m_origin_m):
        """Propagate edge removal from 'origin_id' to 'graph_id'.

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
        """
        graph = self.get_graph(graph_id)
        origin_graph = self.get_graph(origin_id)

        for s, t in graph.edges():
            origin_s = g_m_origin_m[s]
            origin_t = g_m_origin_m[t]
            if (origin_s, origin_t) not in origin_graph.edges():
                graph.remove_edge(s, t)

    def _propagate_edge_attrs_removal(self, origin_id, graph_id, rule, p_origin_m):
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
        graph = self.get_graph(graph_id)
        origin_typing = self.get_typing(graph_id, origin_id)

        for (p_u, p_v), attrs in rule.removed_edge_attrs().items():
            us = keys_by_value(origin_typing, p_origin_m[p_u])
            vs = keys_by_value(origin_typing, p_origin_m[p_v])
            for u in us:
                for v in vs:
                    graph.removed_edge_attrs(u, v, attrs)

    def _propagate_merge(self, origin_id, graph_id, rule, p_origin_m,
                         rhs_origin_prime, g_g_prime, origin_prime_g_prime):
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
        origin_prime_g_prime : dict
            Map from the updated origin to the updated graph with 'graph_id'
        """
        graph = self.get_graph(graph_id)
        origin_typing = self.get_typing(origin_id, graph_id)

        for rhs_node, p_nodes in rule.merged_nodes():
            graph_nodes = set([
                origin_typing[p_origin_m[p_node]]
                for p_node in p_nodes
            ])
            if len(graph_nodes) > 1:
                merged_node_id = graph.merged_nodes(graph_nodes)
                for n in graph_nodes:
                    g_g_prime[n] = merged_node_id
                    origin_prime_g_prime[
                        rhs_origin_prime[rhs_node]] = merged_node_id

        self._expansive_update_incident_homs(graph_id, g_g_prime)
        self._expansive_update_adjacent_rels(graph_id, g_g_prime)

    def _propagate_node_addition(self, origin_id, graph_id, rule,
                                 rhs_origin_prime, rhs_typing,
                                 origin_prime_g_prime):
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
        origin_prime_g_prime : dict
            Map from the updated origin to the updated graph with 'graph_id'
        """
        graph = self.get_graph(graph_id)

        for rhs_node in rule.added_nodes():
            origin_node = rhs_origin_prime[rhs_node]
            if rhs_node in rhs_typing:
                origin_prime_g_prime[origin_node] = rhs_typing[rhs_node]
            else:
                new_node_id = graph.generate_new_node_id(rhs_node)
                graph.add_node(new_node_id)
                origin_prime_g_prime[origin_node] = new_node_id

    def _propagate_node_attrs_addition(self, origin_id, graph_id, rule,
                                       rhs_origin_prime, origin_prime_g_prime):
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

        for rhs_node, attrs in rule.added_node_attrs():
            graph.add_node_attrs(
                origin_prime_g_prime[rhs_origin_prime[rhs_node]],
                attrs)

    def _propagate_edge_addition(self, origin_id, graph_id, rule,
                                 rhs_origin_prime, origin_prime_g_prime):
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
            origin_s = rhs_origin_prime[s]
            origin_t = rhs_origin_prime[t]
            g_s = origin_prime_g_prime[origin_s]
            g_t = origin_prime_g_prime[origin_t]
            if (g_s, g_t) not in graph.edges():
                graph.add_edge(g_s, g_t)

    def _propagate_edge_attrs_addition(self, origin_id, graph_id, rule,
                                       rhs_origin_prime, origin_prime_g_prime):
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
        for (s, t), attrs in rule.added_edge_attrs():
            origin_s = rhs_origin_prime[s]
            origin_t = rhs_origin_prime[t]
            g_s = origin_prime_g_prime[origin_s]
            g_t = origin_prime_g_prime[origin_t]
            graph.add_edge_attrs(g_s, g_t, attrs)

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
                        "types (types that being merged: %s)!" %
                        type_set
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
        type_checking._check_rule_typing(
            self, rule_id, graph_id, lhs_mapping, new_rhs_mapping)

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

        nx.DiGraph.remove_node(self, node_id)

        # Update dicts representing relations
        for u, v in self.relation_edges.keys():
            if u == node_id or v == node_id:
                del self.relation_edges[u, v]

        # Update graph/rule dict
        if node_id in self.graph.keys():
            del self.graph[node_id]
        if node_id in self.rule.keys():
            del self.rule[node_id]

        # Update (rule) typing dict
        if node_id in self.typing.keys():
            del self.typing[node_id]
        for k, v in self.typing.items():
            if node_id in v.keys():
                del self.typing[k][node_id]

        if node_id in self.rule_lhs_typing.keys():
            del self.rule_lhs_typing[node_id]
        for k, v in self.rule_lhs_typing.items():
            if node_id in v.keys():
                del self.rule_lhs_typing[k][node_id]

        if node_id in self.rule_rhs_typing.keys():
            del self.rule_rhs_typing[node_id]
        for k, v in self.rule_rhs_typing.items():
            if node_id in v.keys():
                del self.rule_rhs_typing[k][node_id]
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
                    self.typing[s][t]
                )
            return homomorphism
        else:
            lhs_typing, p_typing, rhs_typing = self.get_rule_typing(s, t)
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                lhs_typing = compose(
                    lhs_typing,
                    self.typing[s][t]
                )
                p_typing = compose(
                    p_typing,
                    self.typing[s][t]
                )
                rhs_typing = compose(
                    rhs_typing,
                    self.typing[s][t]
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
            }
        )
        self.graph[graph_id] = self.node[graph_id]["graph"]

    def _update_mapping(self, source, target, mapping):
        """Update the mapping dictionary from source to target."""
        self.update_edge_attrs(
            source, target,
            {
                "mapping": mapping,
                "attrs": self.get_typing_attrs(source, target)
            }
        )

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
            }
        )

    def _update_rule_homomorphism(self, source, target, lhs_h, rhs_h):
        self.update_edge_attrs(
            source, target,
            {
                "lhs_mapping": lhs_h,
                "rhs_mapping": rhs_h,
                "attrs": self.get_typing_attrs(source, target)
            }
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

    def _restrictive_update_incident_homs(self, graph_id, g_m_g):
        for suc in self.successors(graph_id):
            typing = self.get_typing(graph_id, suc)
            self._update_mapping(graph_id, suc, compose(g_m_g, typing))

    def _restrictive_update_adjacent_rels(self, graph_id, g_m_g):
        for related_g in self.adjacent_relations(graph_id):
            rel = self.get_relation(graph_id, related_g)
            new_rel = dict()

            for node in self.get_graph(graph_id).nodes():
                old_node = g_m_g[node]
                if old_node in rel.keys():
                    new_rel[node] = rel[old_node]

            self._update_relation(graph_id, related_g, new_rel)

    def _expansive_update_incident_homs(self, graph_id, g_m_g_prime):
        for pred in self.predecessors(graph_id):
            typing = self.get_typing(pred, graph_id)
            self._update_mapping(pred, graph_id, compose(typing, g_m_g_prime))

    def _expansive_update_adjacent_rels(self, graph_id, g_m_g_prime):
        for related_g in self.adjacent_relations(graph_id):
            rel = self.get_relation(graph_id, related_g)
            new_rel = dict()

            for node in self.get_graph(graph_id).nodes():
                new_node = g_m_g_prime[node]
                if node in rel.keys():
                    new_rel[new_node] = rel[node]

            self._update_relation(graph_id, related_g, new_rel)

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
