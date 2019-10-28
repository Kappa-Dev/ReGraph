"""."""

from abc import ABC, abstractmethod

from regraph import propagation_utils
from regraph.exception import HierarchyError
from regraph.utils import (attrs_from_json,
                           attrs_to_json)


class Hierarchy(ABC):
    """Abstract class for graph hierarchy objects in ReGraph.

    A graph hierarchy is a DAG, where nodes are graphs with attributes and
    edges are homomorphisms representing graph typing in the system.
    """

    # factories of node/edge dictionaries
    graph_dict_factory = dict
    typing_dict_factory = dict
    rel_dict_factory = dict

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

    # Alternatively
    # def graphs(self):
    #     """Return a list of graphs in the hierarchy."""
    #     return list(self.graph.keys())

    # def typings(self):
    #     """Return a list of graph typing edges in the hierarchy."""
    #     typings = list()
    #     for k, vals in self.typing.items():
    #         for v, vv in vals.items():
    #             typings.append((k, v))
    #     return typings

    # def relations(self):
    #     """Return a list of relations."""
    #     return list(set(self.relation_edges.keys()))

    @abstractmethod
    def successors(self, node_id):
        """Return the set of successors."""
        pass

    @abstractmethod
    def predecessors(self, node_id):
        """Return the set of predecessors."""
        pass

    @abstractmethod
    def get_graph_attrs(self, graph_id):
        """Get attributes of a graph in the hierarchy.

        graph_id : hashable
            Id of the graph
        """
        pass

    @abstractmethod
    def set_graph_attrs(self, node_id, attrs):
        """Set attributes of a graph in the hierarchy.

        graph_id : hashable
            Id of the graph
        """
        pass

    @abstractmethod
    def get_typing_attrs(self, source, target):
        """Get attributes of a typing in the hierarchy.

        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        pass

    @abstractmethod
    def set_typing_attrs(self, source, target, attrs):
        """Set attributes of a typing in the hierarchy.

        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        pass

    @abstractmethod
    def get_relation_attrs(self, left, right):
        """Get attributes of a reltion in the hierarchy.

        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
        """
        pass

    @abstractmethod
    def set_relation_attrs(self, left, right, attrs):
        """Set attributes of a relation in the hierarchy.
        
        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
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
            should be among parents of the `graph_id` graph; values are mappings
            of nodes from pattern to the typing graph;
        nodes : iterable
            Subset of nodes where matching should be performed
        """
        pass

    @abstractmethod
    def _propagate_backward(self):
        pass

    @abstractmethod
    def _get_rule_liftings(self, graph_id, rule, instance, p_typing):
        pass

    @abstractmethod
    def _propagate_forward():
        pass

    @abstractmethod
    def _get_rule_projections(self, graph_id, rule, instance, rhs_typing):
        pass

    def __init__(self):
        """Initialize an abstract hierarchy of graphs."""
        self.graph_dict_factory = gdf = self.graph_dict_factory
        self.graph = gdf()
        self.typing_dict_factory = tdf = self.typing_dict_factory
        self.typing = tdf()
        self.rel_dict_factory = reldf = self.rel_dict_factory
        self.relation_edges = reldf()
        self.relation = reldf()

    def __str__(self):
        """String representation of the hierarchy."""
        res = ""
        res += "\nGraphs (directed == {}): \n".format(self.directed)
        res += "\nNodes:\n"
        for n in self.nodes():
            res += "Graph:"
            res += " {} {}\n".format(n, self.get_graph_attrs(n))
        res += "\nTyping homomorphisms: \n"
        for n1, n2 in self.edges():
            res += "{} -> {}: {}\n".format(
                n1, n2, self.get_typing_attrs(n1, n2))

        res += "\nRelations:\n"
        for n1, n2 in self.relations():
            res += "{}-{}: {}\n".format(
                n1, n2, self.get_relation_attrs(n1, n2))

        return res

    def __eq__(self, hierarchy):
        """Hierarchy equality test."""
        g1 = self.to_nx_graph()
        g2 = hierarchy.to_nx_graph()
        if g1 != g2:
            return False

        for node in self.graphs():
            if self.get_graph_attrs(node) != hierarchy.get_graph_attrs(node):
                return False
            if not self.graph[node] != hierarchy.graph[node]:
                return False

        for s, t in self.edges():
            if self.adj[s][t]["attrs"] != hierarchy.adj[s][t]["attrs"]:
                return False
            if self.is_typing(s, t) and\
               hierarchy.is_typing(s, t):
                if self.adj[s][t]["mapping"] != hierarchy.adj[s][t]["mapping"]:
                    return False
            elif "lhs_typing" in self.adj[s][t] and\
                    "lhs_typing" in hierarchy.adj[s][t]:
                if self.adj[s][t]["lhs_mapping"] != hierarchy.adj[s][t]["lhs_mapping"]:
                    return False
                if self.adj[s][t]["rhs_mapping"] != hierarchy.adj[s][t]["rhs_mapping"]:
                    return False
                if self.adj[s][t]["lhs_total"] != hierarchy.adj[s][t]["lhs_total"]:
                    return False
                if self.adj[s][t]["rhs_total"] != hierarchy.adj[s][t]["rhs_total"]:
                    return False
        for n1, n2 in self.relations():
            if self.relation_edges[n1, n2]["attrs"] !=\
               hierarchy.relation_edges[n1, n2]["attrs"]:
                return False
            if self.relation_edges[n1, n2]["rel"] !=\
               hierarchy.relation_edges[n1, n2]["rel"]:
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
        for node in self.graphs():
            if rename_nodes and node in rename_nodes.keys():
                node_id = rename_nodes[node]
            else:
                node_id = node

            json_data["graphs"].append({
                "id": node_id,
                "graph": self.graph[node].to_json(),
                "attrs": attrs_to_json(self.get_graph_attrs(node))
            })

        for s, t in self.typings():
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
                "mapping": self.typing[s][t],
                "attrs": attrs_to_json(self.get_typing_attrs(s, t))
            })

        visited = set()
        for u, v in self.relations():
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
                        a: list(b) for a, b in self.relation[u][v].items()
                    },
                    "attrs": attrs_to_json(self.get_relation_attrs(u, v))
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
                graph = hierarchy.add_graph_from_json(
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
        return list(self.relation[g].keys())

    def node_type(self, graph_id, node_id):
        """Get a list of the immediate types of a node."""
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Graph '{}' is not defined in the hierarchy!".format(graph_id)
            )
        if node_id not in self.graph[graph_id].nodes():
            raise HierarchyError(
                "Graph '{}'' does not have a node with id '{}'!".format(
                    graph_id, node_id)
            )
        types = dict()
        for successor in self.successors(graph_id):
            mapping = self.typing[graph_id][successor]
            if node_id in mapping.keys():
                types[typing] = mapping[node_id]
        return types

    def ancestors(self, graph_id):
        pass

    def descendents(self, graph_id):
        pass

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
        homomorphism = self.typing[s][t]
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
        """Find rule hierarchy corresponding to propagation of the input rewriting.

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
        """Refine the input rule hierarchy to its reversible version (in-place).

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

    def duplicate_subgraph(self, nodes, suffix):
        """Duplicate a subgraph of the hierarchy."""
        pass
