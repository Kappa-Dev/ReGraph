"""Graph hierarchy related data structures.

This module contains a data structure implementing
graph hierarchy. Graph hierarchy is a DAG, whose nodes
can be graphs or rules of sesqui-pushout rewriting,
and whose edges (directed) represent
homomorphisms between graphs. In addition, hierarchies are
equipped with relations on graphs (which can be thought of as
undirected edges or, alternatively, spans).

* `Hierarchy` -- class for graph hierarchies, based on `networkx.DiGraph`,
  additionally constrained to be acyclic and to respect the property of
  commuting paths.
"""
import copy
import itertools
import json
import networkx as nx
import os
import warnings


from networkx.algorithms import isomorphism
from networkx.exception import NetworkXNoPath

from regraph.networkx import rewriting_utils
from regraph.networkx import type_checking

from regraph.networkx.category_utils import (compose,
                                             check_homomorphism,
                                             is_total_homomorphism,
                                             relation_to_span,
                                             right_relation_dict)
from regraph.primitives import (attrs_to_json,
                                assign_attrs,
                                get_relabeled_graph,
                                relabel_node,
                                get_edge,
                                graph_to_json,
                                graph_from_json,
                                equal,
                                update_node_attrs,
                                update_edge_attrs)
from regraph.utils import (is_subdict,
                           keys_by_value,
                           normalize_attrs,
                           json_dict_to_attrs)
from regraph.rules import Rule
from regraph.exceptions import (HierarchyError,
                                TotalityWarning,
                                ReGraphError,
                                RewritingError,
                                InvalidHomomorphism,
                                GraphError)
from regraph.networkx.components import (AttributeContainter,
                                         GraphNode,
                                         RuleNode,
                                         Typing,
                                         RuleTyping,
                                         GraphRelation)


class NetworkXHierarchy(nx.DiGraph, AttributeContainter):
    """Class implementing graph hierarchy.

    A graph hierarchy is a DAG, where nodes are graphs with attributes and
    edges are homomorphisms representing graph typing in the system.
    This construction provides means for mathematically robust
    procedures ofpropagation of changes (expressed through
    graph rewriting rules) on any level of the hierarchy,
    up to all the graphs which are transitively typed by the graph
    subject to rewriting.

    This class inherits the `networkx.DiGraph` class, and ensures that
    at any time the hierarchy graph is acyclic, and all paths from the same
    source to the same target commute.

    Examples
    --------
    >>> hierarchy = NetworkXHierarchy() # create empty hierarchy
    >>> t = nx.DiGraph([("red", "blue"), ("blue", "blue")])
    >>> hierarchy.add_graph("t", t)
    >>> g = nx.DiGraph([("a", "b"), ("c", "b"), ("b", "d")])
    >>> hierarchy.add_graph("g", g)
    >>> g_t_typing = {"a": "red", "b": "blue", "c": "red", "d": "blue"}
    >>> hierarchy.add_typing("g", "t", g_t_typing)
    >>> hierarchy.graphs()
    ["t", "g"]
    >>> hierarchy.typings()
    [("g", "t")]

    """

    # factories of node/edge dictionaries
    graph_dict_factory = dict
    rule_dict_factory = dict
    typing_dict_factory = dict
    rule_lhs_typing_dict_factory = dict
    rule_rhs_typing_dict_factory = dict
    rel_dict_factory = dict

    def __init__(self, directed=True,
                 attrs=None,
                 graph_node_cls=GraphNode,
                 rule_node_cls=RuleNode,
                 graph_typing_cls=Typing,
                 rule_typing_cls=RuleTyping,
                 relation_cls=GraphRelation):
        """Initialize an hierarchy of graphs.

        Parameters
        ----------
        directed : bool, optional
            Flag indicating if a new hierarchy consists of directed
            or undirected graphs (by default is set to True.
        attrs : dict
            Dictionary with hierarchy attrs.

        Advanced parameters
        -------------------
        graph_node_cls
        rule_node_cls
        graph_typing_cls
        rule_typing_cls
        relation_cls
        """
        nx.DiGraph.__init__(self)

        self.graph_dict_factory = gdf = self.graph_dict_factory
        self.graph = gdf()
        self.rule_dict_factory = rdf = self.rule_dict_factory
        self.rule = rdf()
        self.typing_dict_factory = tdf = self.typing_dict_factory
        self.typing = tdf()
        self.rule_lhs_typing_dict_factory = rltdf =\
            self.rule_lhs_typing_dict_factory
        self.rule_lhs_typing = rltdf()
        self.rule_rhs_typing_dict_factory = rrtdf =\
            self.rule_rhs_typing_dict_factory
        self.rule_rhs_typing = rrtdf()
        self.rel_dict_factory = reldf = self.rel_dict_factory
        self.relation_edge = reldf()
        self.relation = reldf()

        self.attrs = dict()
        self.directed = directed
        self.graph_node_cls = graph_node_cls
        self.rule_node_cls = rule_node_cls
        self.graph_typing_cls = graph_typing_cls
        self.rule_typing_cls = rule_typing_cls
        self.relation_cls = relation_cls

        return

    def __str__(self):
        """String representation of the hierarchy."""
        res = ""
        res += "\nGraphs (directed == {}): \n".format(self.directed)
        res += "\nNodes:\n"
        for n in self.nodes():
            if self.is_graph(n):
                res += "Graph:"
            elif self.is_rule(n):
                res += "Rule:"
            else:
                raise HierarchyError(
                    "Hierarchy error: unknown type '{}' of "
                    "the node '{}'".format(type(self.nodes[n]), n))
            res += " {} {}\n".format(n, self.nodes[n]["attrs"])
        res += "\nTyping homomorphisms: \n"
        for n1, n2 in self.edges():
            if self.is_typing(n1, n2):
                res += "{} -> {}\n".format(n1, n2,)

            elif self.is_rule_typing(n1, n2):
                res +=\
                    ("{} -> {}: lhs_total == {}, rhs_total == {},").format(
                        n1, n2, self.edges[n1, n2]["lhs_total"],
                        self.edges[n1, n2]["rhs_total"])
            else:
                raise HierarchyError(
                    "Hierarchy error: unknown type '{}' "
                    "of the edge '{}->{}'".format(
                        type(self.edges[n1, n2]), n1, n2))

        res += "\nRelations:\n"
        for n1, n2 in self.relations():
            res += "{}-{}: {}\n".format(
                n1, n2, str(self.relation_edge[n1][n2]["attrs"]))

        res += "\nattributes : \n{}\n".format(self.attrs)
        return res

    def __eq__(self, hie):
        """Hierarchy equality test."""
        g1 = self.to_nx_graph()
        g2 = hie.to_nx_graph()
        if not equal(g1, g2):
            return False

        for node in self.nodes():
            if self.nodes[node]["attrs"] != hie.nodes[node]["attrs"]:
                return
            if self.is_graph(node) and\
               hie.is_graph(node):
                if not equal(
                    self.nodes[node]["graph"],
                    hie.nodes[node]["graph"]
                ):
                    return False
            elif self.is_rule(node) and\
                    hie.is_rule(node):
                if self.nodes[node]["rule"] != hie.nodes[node]["rule"]:
                    return False
            else:
                return False

        for s, t in self.edges():

            if self.edges[s, t]["attrs"] != hie.edges[s, t]["attrs"]:
                return False
            if self.is_typing(s, t) and\
               hie.is_typing(s, t):

                if self.edges[s, t]["mapping"] != hie.edges[s, t]["mapping"]:
                    return False
            elif "lhs_typing" in self.edges[s, t] and\
                    "lhs_typing" in hie.edges[s, t]:
                if self.edges[s, t]["lhs_mapping"] != hie.edges[s, t]["lhs_mapping"]:
                    return False
                if self.edges[s, t]["rhs_mapping"] != hie.edges[s, t]["rhs_mapping"]:
                    return False
                if self.edges[s, t]["lhs_total"] != hie.edges[s, t]["lhs_total"]:
                    return False
                if self.edges[s, t]["rhs_total"] != hie.edges[s, t]["rhs_total"]:
                    return False
        for n1, n2 in self.relations():
            if set(self.relation[n1][n2]) != set(hie.relation[n1][n2]):
                return False
        return True

    def is_graph(self, node_id):
        return "graph" in self.nodes[node_id]

    def is_rule(self, node_id):
        return "rule" in self.nodes[node_id]

    def is_typing(self, s, t):
        return "mapping" in self.edges[s, t]

    def is_rule_typing(self, s, t):
        return "lhs_mapping" in self.edges[s, t]

    def to_json(self):
        """Return json representation of the hierarchy."""
        json_data = {
            "rules": [],
            "graphs": [],
            "typing": [],
            "rule_typing": [],
            "relations": []
        }
        for node in self.nodes():
            if self.is_rule(node):
                json_data["rules"].append({
                    "id": node,
                    "rule": self.nodes[node]["rule"].to_json(),
                    "attrs": attrs_to_json(self.nodes[node]["attrs"])
                })
            elif self.is_graph(node):
                json_data["graphs"].append({
                    "id": node,
                    "graph": graph_to_json(self.nodes[node]["graph"]),
                    "attrs": attrs_to_json(self.nodes[node]["attrs"])
                })

            else:
                raise HierarchyError("Unknown type of the node '{}'".format(node))
        for s, t in self.edges():
            if self.is_typing(s, t):
                json_data["typing"].append({
                    "from": s,
                    "to": t,
                    "mapping": self.edges[s, t]["mapping"],
                    "attrs": attrs_to_json(self.edges[s, t]["attrs"])
                })
            elif self.is_rule_typing(s, t):
                json_data["rule_typing"].append({
                    "from": s,
                    "to": t,
                    "lhs_mapping": self.edges[s, t]["lhs_mapping"],
                    "rhs_mapping": self.edges[s, t]["rhs_mapping"],
                    "lhs_total": self.edges[s, t]["lhs_total"],
                    "rhs_total": self.edges[s, t]["rhs_total"],
                    "attrs": attrs_to_json(self.edges[s, t]["attrs"])
                })
            else:
                raise HierarchyError(
                    "Unknown type of the edge '{}->{}'!".format(s, t))

        for u, v in self.relations():
            json_data["relations"].append({
                "from": u,
                "to": v,
                "rel": {a: list(b) for a, b in self.relation[u][v].items()},
                "attrs": attrs_to_json(self.relation_edge[u][v])
            })
        return json_data

    @classmethod
    def from_json(cls, json_data, ignore=None, directed=True):
        """Create hierarchy object from JSON representation.

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
        directed : bool, optional
            True if graphs from JSON representation should be loaded as
            directed graphs, False otherwise, default value -- True

        Returns
        -------
        hierarchy : regraph.hierarchy.Hierarchy
        """
        hierarchy = cls()

        # add graphs
        for graph_data in json_data["graphs"]:
            if ignore is not None and\
               "graphs" in ignore.keys() and\
               graph_data["id"] in ignore["graphs"]:
                pass
            else:
                graph = graph_from_json(graph_data["graph"], directed)
                if "attrs" not in graph_data.keys():
                    attrs = dict()
                else:
                    attrs = AttributeContainter.attrs_from_json(
                        graph_data["attrs"])

                hierarchy.add_graph(
                    graph_data["id"], graph, attrs)

        # add rules
        for rule_data in json_data["rules"]:
            if ignore is not None and\
               "rules" in ignore.keys() and\
               rule_data["id"] in ignore["rules"]:
                pass
            else:
                rule = Rule.from_json(rule_data["rule"])
                if "attrs" not in rule_data.keys():
                    attrs = dict()
                else:
                    attrs = AttributeContainter.attrs_from_json(
                        rule_data["attrs"])
                hierarchy.add_rule(
                    rule_data["id"], rule, attrs)

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
                    attrs = AttributeContainter.attrs_from_json(
                        typing_data["attrs"])
                hierarchy.add_typing(
                    typing_data["from"],
                    typing_data["to"],
                    typing_data["mapping"],
                    attrs)

        # add rule typing
        for rule_typing_data in json_data["rule_typing"]:
            if ignore is not None and\
               "rule_typing" in ignore.keys() and\
               (rule_typing_data["from"], rule_typing_data["to"]) in ignore[
                    "rule_typing"]:
                pass
            else:
                if "attrs" not in rule_typing_data.keys():
                    attrs = dict()
                else:
                    attrs = AttributeContainter.attrs_from_json(
                        rule_typing_data["attrs"])
                hierarchy.add_rule_typing(
                    rule_typing_data["from"],
                    rule_typing_data["to"],
                    rule_typing_data["lhs_mapping"],
                    rule_typing_data["rhs_mapping"],
                    rule_typing_data["lhs_total"],
                    rule_typing_data["rhs_total"],
                    attrs
                )

        # add relations
        for relation_data in json_data["relations"]:
            if ignore is not None and\
               "relations" in ignore.keys() and\
               ((relation_data["from"], relation_data["to"]) in ignore[
                    "relations"] or (relation_data["to"],
                                     relation_data["from"]) in ignore["relations"]):
                pass
            else:
                if "attrs" not in relation_data.keys():
                    attrs = dict()
                else:
                    attrs = AttributeContainter.attrs_from_json(
                        relation_data["attrs"])
                hierarchy.add_relation(
                    relation_data["from"],
                    relation_data["to"],
                    {a: set(b) for a, b in relation_data["rel"].items()},
                    attrs
                )
        return hierarchy

    @classmethod
    def load(cls, filename, ignore=None, directed=True):
        """Load the hierarchy from a file.

        Parameters
        ----------
        Returns
        -------
        Raises
        ------
        """
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                json_data = json.loads(f.read())
                hierarchy = cls.from_json(json_data, ignore, directed)
            return hierarchy
        else:
            raise ReGraphError("File '%s' does not exist!" % filename)

    def export(self, filename):
        """Export the hierarchy to a file."""
        with open(filename, 'w') as f:
            j_data = self.to_json()
            json.dump(j_data, f)

    def graphs(self):
        """Return a list of graphs in the hierarchy."""
        return list(self.graph.keys())

    def typings(self):
        """Return a list of graph typing edges in the hierarchy."""
        typings = list()
        for k, vals in self.typing.items():
            for v, vv in vals.items():
                typings.append((k, v))
        return typings

    def rules(self):
        """Return a list of rules in the hierary."""
        return list(self.rule.keys())

    def relations(self):
        """Return a list of relations."""
        rel = list()
        for k, v in self.relation_edge.items():
            if len(self.relation_edge[k]) > 0:
                for v, _ in self.relation_edge[k].items():
                    if (k, v) not in rel and (v, k) not in rel:
                        rel.append((k, v))
        return rel

    def add_graph(self, graph_id, graph, attrs=None, **kwargs):
        """Add graph to the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        graph : nx.(Di)Graph
            Graph object corresponding to the new node of
            the hierarchy
        graph_attrs : dict
            Dictionary containing attributes of the new node

        Raises
        ------
        HierarchyError
            If the graph object is directed/undirected while the
            hierarchy's parameter `directed` is False/True
            (the hierarchy accommodates undirected/directed graphs);
            if node with provided id already exists in the hierarchy

        """
        if self.directed != graph.is_directed():
            if self.directed:
                raise HierarchyError(
                    "Hierarchy is defined for directed == {} graphs!".format(
                        self.directed))
            else:
                raise HierarchyError(
                    "Hierarchy is defined for undirected graphs!")
        if graph_id in self.nodes():
            raise HierarchyError(
                "Node '{}' already exists in the hierarchy!".format(graph_id))
        self.add_node(graph_id)
        assign_attrs(
            self.nodes[graph_id], {
                "graph": graph,
                "attrs": attrs
            })
        if graph_id not in self.relation_edge.keys():
            self.relation_edge.update({graph_id: dict()})
        if graph_id not in self.relation.keys():
            self.relation.update({graph_id: dict()})
        self.graph[graph_id] = self.nodes[graph_id]["graph"]
        if graph_id not in self.typing.keys():
            self.typing[graph_id] = dict()
        return

    def add_empty_graph(self, graph_id, attrs):
        if self.directed is True:
            graph_obj = nx.DiGraph()
        else:
            graph_obj = nx.Graph()
        self.add_graph(graph_id, graph_obj, attrs=attrs)

    def add_rule(self, rule_id, rule, rule_attrs=None):
        """Add rule to the hierarchy.

        Parameters
        ----------
        rule_id : hashable
            Id of a new node in the hierarchy
        rule : regraph.rules.Rule
            Rule object corresponding to the new node of
            the hierarchy
        rule_attrs : dict
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
        if self.directed != rule.lhs.is_directed():
            raise HierarchyError(
                "Hierarchy is defined for directed == %s graphs: " +
                "lhs of the rule is directed == %s!" %
                (self.directed, rule.lhs.is_directed())
            )
        if self.directed != rule.p.is_directed():
            raise HierarchyError(
                "Hierarchy is defined for directed == %s graphs: " +
                "p of the rule is directed == %s!" %
                (self.directed, rule.p.is_directed())
            )
        if self.directed != rule.rhs.is_directed():
            raise HierarchyError(
                "Hierarchy is defined for directed == %s graphs: " +
                "rhs of the rule is directed == %s!" %
                (self.directed, rule.rhs.is_directed())
            )
        if rule_id in self.nodes():
            raise HierarchyError(
                "Node '%s' already exists in the hierarchy!" %
                rule_id
            )
        self.add_node(rule_id)
        if rule_attrs is not None:
            normalize_attrs(rule_attrs)
        assign_attrs(
            self.nodes[rule_id],
            {
                "rule": rule,
                "attrs": rule_attrs
            })
        self.rule[rule_id] = self.nodes[rule_id]["rule"]
        if rule_id not in self.rule_lhs_typing.keys():
            self.rule_lhs_typing[rule_id] = dict()
        if rule_id not in self.rule_rhs_typing.keys():
            self.rule_rhs_typing[rule_id] = dict()
        return

    def add_typing(self, source, target, mapping, attrs=None):
        """Add homomorphism to the hierarchy.

        Parameters
        ----------
        source
            Id of a source graph node of typing
        target
            Id of a target graph node of typing
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
                * a source node is not a graph
                * addition of an edge between source and target creates
                a cycle or produces paths that do not commute with
                some already existing paths

        InvalidHomomorphism
            If a homomorphisms from a graph at the source to a graph at
            the target given by `mapping` is not a valid homomorphism.

        """
        if source not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % source)
        if target not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % target)

        if (source, target) in self.edges():
            raise HierarchyError(
                "Edge '%s->%s' already exists in the hierarchy: "
                "no muliple edges allowed!" %
                (source, target)
            )
        if "graph" not in self.nodes[source]:
            if self.is_rule(source):
                raise HierarchyError(
                    "Source node is a rule, use `add_rule_typing` "
                    "method instead!"
                )
            else:
                raise HierarchyError(
                    "Source of a typing should be a graph, `%s` is provided!" %
                    type(self.nodes[source])
                )
        if "graph" not in self.nodes[target]:
            raise HierarchyError(
                "Target of a typing should be a graph, `%s` is provided!" %
                type(self.nodes[target])
            )

        # check no cycles are produced
        self.add_edge(source, target)
        if not nx.is_directed_acyclic_graph(self):
            self.remove_edge(source, target)
            raise HierarchyError(
                "Edge '%s->%s' creates a cycle in the hierarchy!" %
                (source, target)
            )
        self.remove_edge(source, target)

        # check if the homomorphism is valid
        check_homomorphism(
            self.nodes[source]["graph"],
            self.nodes[target]["graph"],
            mapping,
            total=True
        )

        # check if newly created path commutes with existing shortest paths
        type_checking._check_consistency(self, source, target, mapping)

        self.add_edge(source, target)
        if attrs is not None:
            normalize_attrs(attrs)
        assign_attrs(
            self.edges[source, target],
            {
                "mapping": mapping,
                "attrs": attrs
            })
        self.typing[source][target] = self.edges[source, target]["mapping"]
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
                "Node '%s' is not defined in the hierarchy!" % rule_id)
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % graph_id)

        if not self.is_rule(rule_id):
            raise HierarchyError(
                "Source of a rule typing should be a rule, `%s` is provided!" %
                type(self.nodes[rule_id])
            )
        if not self.is_graph(graph_id):
            raise HierarchyError(
                "Target of a rule typing should be a graph, "
                "'{}' is provided!".format(
                    type(self.nodes[graph_id])))

        # check if an lhs typing is valid
        check_homomorphism(
            self.nodes[rule_id]["rule"].lhs,
            self.nodes[graph_id]["graph"],
            lhs_mapping,
            total=lhs_total
        )

        new_rhs_mapping = rhs_mapping
        if new_rhs_mapping is None:
            new_rhs_mapping = dict()
        rule = self.nodes[rule_id]["rule"]
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
            self.nodes[rule_id]["rule"].rhs,
            self.nodes[graph_id]["graph"],
            new_rhs_mapping,
            total=rhs_total
        )

        # check if newly created path commutes with existing shortest paths
        type_checking._check_rule_typing(
            self, rule_id, graph_id, lhs_mapping, new_rhs_mapping)

        self.add_edge(rule_id, graph_id)
        if attrs is not None:
            normalize_attrs(attrs)

        assign_attrs(
            self.edges[rule_id, graph_id],
            {
                "lhs_mapping": lhs_mapping,
                "rhs_mapping": new_rhs_mapping,
                "lhs_total": lhs_total,
                "rhs_total": rhs_total,
                "attrs": attrs
            })
        self.rule_lhs_typing[rule_id][graph_id] =\
            self.edges[rule_id, graph_id]["lhs_mapping"]
        self.rule_rhs_typing[rule_id][graph_id] =\
            self.edges[rule_id, graph_id]["rhs_mapping"]
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

        Examples
        --------
        >>> hierarchy = Hierarchy()
        >>> g1 = nx.DiGraph([("a", "b"), ("a", "a")])
        >>> g2 = nx.DiGraph([(1, 2), (2, 3)])
        >>> hierarchy.add_graph("G1", g1)
        >>> hierarchy.add_graph("G2", g2)
        >>> hierarchy.add_relation("G1", "G2", {"a": {1, 2}, "b": 3})
        >>> hierarchy.relation["G1"]["G2"].rel
        {'a': {1, 2}, 'b': {3}}
        >>> hierarchy.relation["G2"]["G1"].rel
        {1: {'a'}, 2: {'a'}, 3: {'b'}}
        """
        if left not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % left)
        if right not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % right)

        if "graph" not in self.nodes[left]:
            raise HierarchyError(
                "Relation can be defined on graphs, '%s' is provided" %
                type(self.nodes[left])
            )
        if "graph" not in self.nodes[right]:
            raise HierarchyError(
                "Relation can be defined on graphs, '%s' is provided" %
                type(self.nodes[right])
            )

        if (left, right) in self.relations():
            raise HierarchyError(
                "Relation '%s-%s' already exists in the hierarchy "
                "multiple edges are not allowed!" %
                (left, right)
            )

        # normalize relation dict
        new_relation_dict = dict()
        for key, values in relation.items():
            if type(values) == set:
                new_relation_dict[key] = values
            elif type(values) == str:
                new_relation_dict[key] = {values}
            else:
                try:
                    new_set = set()
                    for v in values:
                        new_set.add(v)
                    new_relation_dict[key] = new_set
                except TypeError:
                    new_relation_dict[key] = {values}
        relation = new_relation_dict

        # check relation is well-defined on left and right side
        for key, values in relation.items():
            if key not in self.nodes[left]["graph"].nodes():
                raise HierarchyError(
                    "Relation is not valid: node '%s' does not "
                    "exist in a graph '%s'" %
                    (key, left)
                )
            for v in values:
                if v not in self.nodes[right]["graph"].nodes():
                    raise HierarchyError(
                        "Relation is not valid: node '%s' does not "
                        "exist in a graph '%s'" %
                        (v, right)
                    )

        if attrs is not None:
            normalize_attrs(attrs)

        pairs = set()
        for k, values in relation.items():
            for v in values:
                pairs.add((k, v))
        right_relation = right_relation_dict(pairs)
        rel_ab_obj = GraphRelation(relation, attrs)
        rel_ba_obj = GraphRelation(right_relation, attrs)
        self.relation_edge[left].update({right: rel_ab_obj})
        self.relation[left].update(
            {right: self.relation_edge[left][right].rel})
        self.relation_edge[right].update({left: rel_ba_obj})
        self.relation[right].update(
            {left: self.relation_edge[right][left].rel})
        return

    def get_graph(self, graph_id):
            return self.nodes[graph_id]["graph"]

    def get_node_attrs(self, node_id):
            return self.nodes[node_id]["attrs"]

    def get_graph_attrs(self, graph_id):
            return self.get_node_attrs(graph_id)

    def set_node_attrs(self, node_id, attrs):
        normalize_attrs(attrs)
        for k, v in attrs:
            self.nodes[node_id]["attrs"][k] = v

    def set_graph_attrs(self, graph_id, attrs):
        self.set_node_attrs(graph_id, attrs)

    def set_edge_attrs(self, source, target, attrs):
        normalize_attrs(attrs)
        for k, v in attrs:
            self.edges[source, target]["attrs"][k] = v

    def set_typing_attrs(self, source, target, attrs):
        self.set_edge_attrs(source, target, attrs)

    def add_cycle(self, nodes, **attr):
        """Method of adding cycle to the graph hierarchy."""
        raise HierarchyError("Cycles are not allowed in graph hierarchy")

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
                "Node `%s` is not defined in the hierarchy!" % node_id)

        if reconnect:
            out_graphs = self.successors(node_id)
            in_graphs = self.predecessors(node_id)

            for source in in_graphs:
                for target in out_graphs:
                    if self.is_rule_typing(source, node_id):
                        lhs_mapping = compose(
                            self.edges[source, node_id]["lhs_mapping"],
                            self.edges[node_id, target]["mapping"]
                        )
                        rhs_mapping = compose(
                            self.edges[source, node_id]["rhs_mapping"],
                            self.edges[node_id, target]["mapping"]
                        )
                        if (source, target) not in self.edges():
                            self.add_rule_typing(
                                source,
                                target,
                                lhs_mapping,
                                rhs_mapping,
                                self.edges[source, node_id]["lhs_total"] and
                                self.edges[node_id, target]["lhs_total"],
                                self.edges[source, node_id]["rhs_total"] and
                                self.edges[node_id, target]["rhs_total"]
                            )
                    elif self.is_typing(source, node_id):
                        # compose two homomorphisms
                        mapping = compose(
                            self.edges[source, node_id]["mapping"],
                            self.edges[node_id, target]["mapping"]
                        )

                        if (source, target) not in self.edges():
                            self.add_typing(
                                source, target, mapping)

        nx.DiGraph.remove_node(self, node_id)

        # Update dicts representing relations
        if node_id in self.relation_edge.keys():
            del self.relation_edge[node_id]
        for k, v in self.relation_edge.items():
            if node_id in v.keys():
                del self.relation_edge[k][node_id]

        if node_id in self.relation.keys():
            del self.relation[node_id]
        for k, v in self.relation.items():
            if node_id in v.keys():
                del self.relation[k][node_id]

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

    def remove_edge(self, u, v):
        """Remove an edge from the hierarchy."""
        nx.DiGraph.remove_edge(self, u, v)
        if u in self.typing.keys():
            if v in self.typing[u].keys():
                del self.typing[u][v]
        if v in self.typing.keys():
            if u in self.typing[v].keys():
                del self.typing[v][u]
        if u in self.rule_lhs_typing.keys():
            if v in self.rule_lhs_typing.keys():
                del self.rule_lhs_typing[u][v]
        if v in self.rule_rhs_typing.keys():
            if u in self.rule_rhs_typing.keys():
                del self.rule_rhs_typing[v][u]
        return

    def remove_relation(self, g1, g2):
        """Remove relation from the hierarchy."""
        if (g1, g2) not in self.relations() and\
           (g2, g1) not in self.relations():
            raise HierarchyError(
                "Relation '%s-%s' is not defined in the hierarchy" %
                (g1, g2)
            )
        del self.relation_edge[g1][g2]
        del self.relation[g1][g2]
        del self.relation_edge[g2][g1]
        del self.relation[g2][g1]

    def adjacent_relations(self, g):
        """Return a list of related graphs."""
        if g not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % g)
        return list(self.relation_edge[g].keys())

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
                "Node '%s' is not defined in the hierarchy!" % left)
        if right not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % right)

        if (left, right) not in self.relations() and\
           (right, left) not in self.relations():
            raise HierarchyError(
                "Relation between graphs '%s' and '%s' is not defined" %
                (left, right)
            )
        common, left_h, right_h = relation_to_span(
            self.nodes[left]["graph"],
            self.nodes[right]["graph"],
            self.relation[left][right],
            edges,
            attrs,
            self.directed)
        return common, left_h, right_h

    def node_type(self, graph_id, node_id):
        """Get a list of the immediate types of a node."""
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Graph '%s' is not defined in the hierarchy!"
                % graph_id
            )
        if node_id not in self.graph[graph_id].nodes():
            raise HierarchyError(
                "Graph '%s' does not have a node with id '%s'!"
                % (graph_id, node_id)
            )
        types = {}
        for _, typing in self.out_edges(graph_id):
            mapping = self.edges[graph_id, typing]["mapping"]
            if node_id in mapping.keys():
                types[typing] = mapping[node_id]
        return types

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
        if self.is_graph(s):
            t = path[1]
            homomorphism = self.edges[s, t]["mapping"]
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                homomorphism = compose(
                    homomorphism,
                    self.edges[s, t]["mapping"]
                )
            return homomorphism
        else:
            t = path[1]
            lhs_homomorphism = self.edges[s, t]["lhs_mapping"]
            rhs_homomorphism = self.edges[s, t]["rhs_mapping"]
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                lhs_homomorphism = compose(
                    lhs_homomorphism, self.edges[s, t]["mapping"])
                rhs_homomorphism = compose(
                    rhs_homomorphism, self.edges[s, t]["mapping"])
            return lhs_homomorphism, rhs_homomorphism

    def _path_from_rule(self, path):
        s = path[0]
        return self.is_rule(s)

    def _get_ancestors_paths(self, graph_id):
        ancestors = {}
        for typing in self.successors(graph_id):
            typing_ancestors = self._get_ancestors_paths(typing)
            if typing in ancestors.keys():
                ancestors[typing].append([graph_id, typing])
            else:
                ancestors[typing] = [[graph_id, typing]]

            for (anc, paths) in typing_ancestors.items():
                if anc in ancestors.keys():
                    for p in paths:
                        ancestors[anc] += [[graph_id] + p]
                else:
                    for p in paths:
                        ancestors[anc] = [[graph_id] + p]
        return ancestors

    def add_node_type(self, graph_id, node_id, typing_dict):
        """Type a node in a graph according to `typing_dict`."""
        if node_id not in self.nodes[graph_id]["graph"].nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy graph '%s'!" %
                (node_id, graph_id)
            )

        # check edges exist
        for typing_graph, _ in typing_dict.items():
            if (graph_id, typing_graph) not in self.edges():
                raise HierarchyError(
                    "Typing `%s->%s` does not exist!" %
                    (graph_id, typing_graph)
                )

        # check consistency
        # 1. find pairs of successors that have common ancestors
        ancestors = {}
        for n in self.successors(graph_id):
            ancestors[n] = self._get_ancestors_paths(n)
        common_ancestors = {}
        for s1 in self.successors(graph_id):
            for s2 in self.successors(graph_id):
                if s1 != s2 and (s1, s2) not in common_ancestors.keys() and\
                   (s2, s1) not in common_ancestors.keys():
                    c_anc = set(ancestors[s1].keys()).intersection(
                        set(ancestors[s2].keys())
                    )
                    if len(c_anc) > 0:
                        common_ancestors[(s1, s2)] = c_anc

        # check all the paths to the common ancestors are commuting
        for (s1, s2), ancs in common_ancestors.items():
            new_mapping_s1 = copy.deepcopy(self.edges[graph_id, s1]["mapping"])
            new_mapping_s2 = copy.deepcopy(self.edges[graph_id, s2]["mapping"])

            if s1 in typing_dict.keys():
                new_mapping_s1[node_id] = typing_dict[s1]
            if s2 in typing_dict.keys():
                new_mapping_s2[node_id] = typing_dict[s2]

            for anc in ancs:
                for p1 in ancestors[s1][anc]:
                    for p2 in ancestors[s2][anc]:
                        h1 = self.compose_path_typing(p1)
                        h2 = self.compose_path_typing(p2)
                        if compose(new_mapping_s1, h1) !=\
                           compose(new_mapping_s2, h2):
                            if s1 not in typing_dict.keys():
                                type_1 = None
                            else:
                                type_1 = typing_dict[s1]
                            if s2 not in typing_dict.keys():
                                type_2 = None
                            else:
                                type_2 = typing_dict[s2]
                            raise HierarchyError(
                                "Cannot add new typing of the node `%s` in `%s`: "
                                "typing by `%s` in  `%s` and `%s` in `%s` create "
                                "paths that do not commute" %
                                (node_id, graph_id, type_1, s1, type_2, s2)
                            )

        # add new types (specified + inferred)
        for typing_graph, type_id in typing_dict.items():
            self.edges[graph_id, typing_graph]["mapping"].update({
                node_id: type_id
            })
        return

    def find_matching(self, graph_id, pattern,
                      pattern_typing=None, nodes=None):
        """Find an instance of a pattern in a specified graph.

        `graph_id` -- id of a graph in the hierarchy to search for matches;
        `pattern` -- nx.(Di)Graph object defining a pattern to match;
        `pattern_typing` -- a dictionary that specifies a typing of a pattern,
        keys of the dictionary -- graph id that types a pattern, this graph
        should be among parents of the `graph_id` graph; values are mappings
        of nodes from pattern to the typing graph;
        """
        if type(self.nodes[graph_id]) == RuleNode:
            raise ReGraphError(
                "Pattern matching in a rule is not implemented!")
        # Check that 'typing_graph' and 'pattern_typing' are correctly
        # specified

        ancestors = self.get_ancestors(graph_id)
        if pattern_typing is not None:
            for typing_graph, _ in pattern_typing.items():
                if typing_graph not in ancestors.keys():
                    raise HierarchyError(
                        "Pattern typing graph '%s' is not in "
                        "the (transitive) typing graphs of '%s'!" %
                        (typing_graph, graph_id)
                    )
            new_pattern_typing = dict()
            for key, value in pattern_typing.items():
                if type(value) == dict:
                    new_pattern_typing[key] = (value, False)
                else:
                    try:
                        if len(value) == 2:
                            new_pattern_typing[key] = value
                        elif len(value) == 1:
                            new_pattern_typing[key] = (value[0], False)
                    except:
                        raise HierarchyError("Invalid pattern typing!")
            # Check pattern typing is a valid homomorphism
            for typing_graph, (mapping, _) in new_pattern_typing.items():
                try:
                    check_homomorphism(
                        pattern,
                        self.nodes[typing_graph]["graph"],
                        mapping,
                        total=False
                    )
                except InvalidHomomorphism as e:
                    raise ReGraphError(
                        "Specified pattern is not valid in the "
                        "hierarchy (it produces the following error: %s) " % e
                    )
            pattern_typing = new_pattern_typing

        if nodes is not None:
            g = self.nodes[graph_id]["graph"].subgraph(nodes)
        else:
            g = self.nodes[graph_id]["graph"]
        labels_mapping = dict(
            [(n, i + 1) for i, n in
             enumerate(g.nodes())]
        )
        g = get_relabeled_graph(g, labels_mapping)

        inverse_mapping = dict(
            [(value, key) for key, value in labels_mapping.items()]
        )
        if pattern_typing:
            try:
                g_typing = dict([
                    (typing_graph, dict([
                        (labels_mapping[k], v) for k, v in
                        self.compose_path_typing(
                            nx.shortest_path(self, graph_id, typing_graph)
                        ).items() if nodes is None or k in nodes
                    ])) for typing_graph in pattern_typing.keys()
                ])
            except NetworkXNoPath:
                raise ReGraphError(
                    "One of the specified pattern typing graphs "
                    "is not in the set of ancestors of '%s'" % graph_id
                )

        matching_nodes = set()

        # Find all the nodes matching the nodes in a pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if pattern_typing:
                    # check types match
                    match = False
                    for typing_graph, (typing, _) in pattern_typing.items():
                        if node in g_typing[typing_graph].keys() and\
                           pattern_node in typing.keys():
                            if g_typing[typing_graph][node] == typing[
                                    pattern_node]:
                                if is_subdict(pattern.nodes[pattern_node],
                                              g.nodes[node]):
                                    match = True
                            else:
                                # there is no mapping of this node in the
                                # typing by `typing_graph`
                                pass
                        else:
                            if is_subdict(pattern.nodes[pattern_node],
                                          g.nodes[node]):
                                match = True
                    if match:
                        matching_nodes.add(node)
                else:
                    if is_subdict(pattern.nodes[pattern_node], g.nodes[node]):
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
                        [n for n in subg.nodes()
                         if n not in edge_induced_graph.nodes()])
                    matching_obj = isomorphism.DiGraphMatcher(
                        pattern, edge_induced_graph)
                    for isom in matching_obj.isomorphisms_iter():
                        isomorphic_subgraphs.append((subg, isom))
                else:
                    edge_induced_graph = nx.Graph(edgeset)
                    edge_induced_graph.add_nodes_from(
                        [n for n in subg.nodes()
                         if n not in edge_induced_graph.nodes()])
                    matching_obj = isomorphism.GraphMatcher(
                        pattern, edge_induced_graph)
                    for isom in matching_obj.isomorphisms_iter():
                        isomorphic_subgraphs.append((subg, isom))

        for subgraph, mapping in isomorphic_subgraphs:
            # Check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if pattern_typing:
                    for typing_graph, (typing, _) in pattern_typing.items():
                        if node in g_typing[typing_graph].keys() and\
                           pattern_node in typing.keys():
                            if g_typing[typing_graph][node] != typing[
                                    pattern_node]:
                                break
                        if not is_subdict(pattern.nodes[pattern_node],
                                          subgraph.nodes[node]):
                            break
                    else:
                        continue
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = get_edge(pattern, edge[0], edge[1])
                    target_attrs = get_edge(
                        subgraph, mapping[edge[0]], mapping[edge[1]])
                    if not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # Bring back the original labeling
        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]

        return instances

    def find_rule_matching(self, graph_id, rule_id):
        """Find matching of a rule `rule_id` form the hierarchy."""
        if self.is_rule(graph_id):
            raise ReGraphError(
                "Pattern matching in a rule is not implemented!")

        if not self.is_rule(rule_id):
            raise HierarchyError("Invalid rule `%s` to match!" % rule_id)

        rule = self.nodes[rule_id]["rule"]

        lhs_typing = {}
        rhs_typing = {}

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] = self.edges[rule_id, suc]["lhs_mapping"]
            rhs_typing[suc] = self.edges[rule_id, suc]["rhs_mapping"]

        instances = self.find_matching(
            graph_id,
            rule.lhs,
            lhs_typing
        )
        return instances

    def _get_common_successors(self, node_list):
        common_sucs = {}
        for n1 in node_list:
            for n2 in node_list:
                if n1 != n2:
                    if (n1, n2) not in common_sucs.keys() and\
                            (n2, n1) not in common_sucs.keys():
                        suc1 = set(self.successors(n1))
                        suc2 = set(self.successors(n2))
                        common_sucs[(n1, n2)] =\
                            suc1.intersection(suc2)
        return common_sucs

    def rewrite(self, graph_id, rule, instance=None,
                lhs_typing=None, rhs_typing=None, strict=False, inplace=True):
        """Rewrite and propagate the changes up & down."""
        # start = time.time()
        if self.is_rule(graph_id):
            raise ReGraphError("Rewriting of a rule is not implemented!")

        if instance is None:
            instance = {
                n: n for n in rule.lhs.nodes()
            }

        # 1. Check consistency of the input
        # 1a. Autocomplete typing

        new_lhs_typing, new_rhs_typing =\
            type_checking._autocomplete_typing(
                self, graph_id, instance, lhs_typing,
                rhs_typing, rule.p_lhs, rule.p_rhs)

        # 1b. Check that instance is consistent with lhs & rhs typing
        type_checking._check_instance(
            self, graph_id, rule.lhs, instance, new_lhs_typing)

        # 1c. Check consistency of the (autocompleted) rhs & lhs typings
        if new_lhs_typing is not None and new_rhs_typing is not None:
            try:
                type_checking._check_self_consistency(
                    self, new_lhs_typing)
            except ReGraphError as e:
                raise RewritingError(
                    "Typing of the lhs is self inconsistent: %s" % str(e)
                )
            try:
                type_checking._check_self_consistency(
                    self, new_rhs_typing, strict)
            except ReGraphError as e:
                raise RewritingError(
                    "Typing of the rhs is self inconsistent: %s" % str(e)
                )

            type_checking._check_lhs_rhs_consistency(
                self, graph_id, rule, instance,
                new_lhs_typing, new_rhs_typing,
                strict)

            if strict is True:
                type_checking._check_totality(
                    self, graph_id, rule, instance,
                    new_lhs_typing, new_rhs_typing)

        # end = time.time() - start
        # print("\t\t\t\tTime to type check: ", end)
        # 2. Rewrite a graph `graph_id`

        # start = time.time()
        base_changes = rewriting_utils._rewrite_base(
            self, graph_id, rule, instance,
            new_lhs_typing, new_rhs_typing, inplace)

        (g_m, p_g_m, g_m_g, g_prime, g_m_g_prime, r_g_prime) =\
            base_changes["graph"]

        upstream_changes = {
            "graphs": {graph_id: (g_m, g_m_g, g_prime, g_m_g_prime)},
            "homomorphisms": base_changes["homomorphisms"],
            "rule_homomorphisms": dict(),
            "rules": dict(),
            "relations": base_changes["relations"]
        }

        # end = time.time() - start
        # print("\t\t\t\tTime to compute base: ", end)

        # start = time.time()
        # 4. Propagate rewriting up the hierarchy
        new_upstream_changes =\
            rewriting_utils._propagate_up(
                self, graph_id, rule, instance, p_g_m, g_m_g_prime, inplace)

        upstream_changes["graphs"].update(new_upstream_changes["graphs"])
        upstream_changes["homomorphisms"].update(
            new_upstream_changes["homomorphisms"])
        upstream_changes["rules"].update(new_upstream_changes["rules"])
        upstream_changes["rule_homomorphisms"].update(
            new_upstream_changes["rule_homomorphisms"])
        upstream_changes["relations"] += new_upstream_changes["relations"]

        graph_construct = (g_m, g_m_g, g_prime, g_m_g_prime, r_g_prime)
        # end = time.time() - start
        # print("\t\t\t\tTime to propagate up: ", end)

        # start = time.time()
        downstream_changes = dict()
        downstream_changes =\
            rewriting_utils._propagate_down(
                self, graph_id, graph_construct,
                rule, instance, new_rhs_typing, inplace)
        # end = time.time() - start
        # print("\t\t\t\tTime to propagate down: ", end)

        # 6. Apply all the changes in the hierarchy
        if inplace:
            # start = time.time()
            rewriting_utils._apply_changes(
                self, upstream_changes, downstream_changes)
            # end = time.time() - start
            # print("\t\t\t\tTime to apply changes: ", end)

            return (self, r_g_prime)
        else:
            # start = time.time()
            # First, create a new hierarchy
            new_graph = copy.deepcopy(self)
            rewriting_utils._apply_changes(
                new_graph, upstream_changes, downstream_changes)
            return (new_graph, r_g_prime)

    def apply_rule(self, graph_id, rule_id, instance,
                   strong_typing=True, inplace=True):
        """Apply rule from the hierarchy."""
        if self.is_rule(graph_id):
            raise ReGraphError("Rewriting of a rule is not implemented!")

        if not self.is_rule(rule_id):
            raise RewritingError("Invalid rewriting rule `%s`!" % rule_id)

        rule = self.nodes[rule_id]["rule"]

        lhs_typing = dict()
        rhs_typing = dict()

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] =\
                self.edges[rule_id, suc]["lhs_mapping"]
            rhs_typing[suc] =\
                self.edges[rule_id, suc]["rhs_mapping"]

        return self.rewrite(
            graph_id,
            rule,
            instance,
            lhs_typing,
            rhs_typing,
            inplace=inplace)

    def to_json(self):
        """Return json representation of the hierarchy."""
        json_data = {
            "rules": [],
            "graphs": [],
            "typing": [],
            "rule_typing": [],
            "relations": []
        }
        for node in self.nodes():
            if self.is_rule(node):
                rule_json = self.nodes[node].to_json()
                rule_json["id"] = node
                json_data["rules"].append(rule_json)
            elif self.is_graph(node):
                graph_json = self.nodes[node].to_json()
                graph_json["id"] = node
                json_data["graphs"].append(graph_json)
            else:
                raise HierarchyError("Unknown type of the node '%s'!" % node)
        for s, t in self.edges():
            if self.is_typing(s, t):
                typing_json = {
                    "mapping": self.edges[s, t]["mapping"],
                    "attrs": attrs_to_json(self.edges[s, t]["attrs"])
                }
                typing_json["from"] = s
                typing_json["to"] = t
                json_data["typing"].append(typing_json)
            elif self.is_rule_typing(s, t):
                rule_typing_json = {
                    "lhs_mapping": self.edges[s, t]["lhs_mapping"],
                    "rhs_mapping": self.edges[s, t]["rhs_mapping"],
                    "lhs_total": self.edges[s, t]["lhs_total"],
                    "rhs_total": self.edges[s, t]["rhs_total"],
                    "attrs": attrs_to_json(self.edges[s, t]["attrs"])
                }
                rule_typing_json["from"] = s
                rule_typing_json["to"] = t
                json_data["rule_typing"].append(rule_typing_json)
            else:
                raise HierarchyError(
                    "Unknown type of the edge '%s->%s'!" % (s, t)
                )
        for u, v in self.relations():
            relation_json = self.relation_edge[u][v].to_json()
            relation_json["from"] = u
            relation_json["to"] = v
            json_data["relations"].append(relation_json)
        attrs = {}
        for key, value in self.attrs.items():
            attrs[key] = value.to_json()
        json_data["attrs"] = attrs
        return json_data

    @classmethod
    def from_json(cls, json_data, ignore=None, directed=True):
        """Create hierarchy obj from json repr."""
        hierarchy = cls()

        # add graphs
        for graph_data in json_data["graphs"]:
            if ignore is not None and\
               "graphs" in ignore.keys() and\
               graph_data["id"] in ignore["graphs"]:
                pass
            else:
                graph, attrs = hierarchy.graph_node_cls.process_json(
                    graph_data, directed)
                hierarchy.add_graph(graph_data["id"], graph, attrs=attrs)

        # add rules
        for rule_data in json_data["rules"]:
            if ignore is not None and\
               "rules" in ignore.keys() and\
               rule_data["id"] in ignore["rules"]:
                pass
            else:
                rule, attrs = hierarchy.rule_node_cls.process_json(
                    rule_data, directed)
                hierarchy.add_rule(rule_data["id"], rule, attrs=attrs)

        # add typing
        for typing_data in json_data["typing"]:
            if ignore is not None and\
               "typing" in ignore.keys() and\
               (typing_data["from"], typing_data["to"]) in ignore["typing"]:
                pass
            else:
                mapping, attrs =\
                    hierarchy.graph_typing_cls.process_json(typing_data)
                hierarchy.add_typing(
                    typing_data["from"],
                    typing_data["to"],
                    mapping, attrs)

        # add rule typing
        for rule_typing_data in json_data["rule_typing"]:
            if ignore is not None and\
               "rule_typing" in ignore.keys() and\
               (rule_typing_data["from"], rule_typing_data["to"]) in ignore[
                    "rule_typing"]:
                pass
            else:
                lhs_map, rhs_map, lhs_total, rhs_total, attrs =\
                    hierarchy.rule_typing_cls.process_json(rule_typing_data)
                hierarchy.add_rule_typing(
                    rule_typing_data["from"],
                    rule_typing_data["to"],
                    lhs_map, rhs_map, lhs_total, rhs_total, attrs)

        # add relations
        for relation_data in json_data["relations"]:
            if ignore is not None and\
               "relations" in ignore.keys() and\
               ((relation_data["from"], relation_data["to"]) in ignore[
                    "relations"] or (relation_data["to"],
                                     relation_data["from"]) in ignore["relations"]):
                pass
            else:
                rel, attrs = hierarchy.relation_cls.process_json(relation_data)
                hierarchy.add_relation(
                    relation_data["from"],
                    relation_data["to"],
                    rel, attrs)

        if "attrs" in json_data.keys():
            hierarchy.attrs = json_dict_to_attrs(json_data["attrs"])
        # for k, v in json_data["attrs"].items():
        #     hierarchy.add_attrs(
        #         {k: json_dict_to_attrs(v)})

        return hierarchy

    @classmethod
    def load(cls, filename, ignore=None, directed=True):
        """Load the hierarchy from a file."""
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                json_data = json.loads(f.read())
                hierarchy = cls.from_json(json_data, ignore, directed)
            return hierarchy
        else:
            raise HierarchyError("File '%s' does not exist!" % filename)

    def export(self, filename):
        """Export the hierarchy to a file."""
        with open(filename, 'w') as f:
            j_data = self.to_json()
            json.dump(j_data, f)

    def get_ancestors(self, graph_id, maybe=None):
        """Return ancestors of a graph as well as the typing morphisms."""
        ancestors = {}
        for _, typing in self.out_edges(graph_id):
            if maybe is not None and typing not in maybe:
                continue
            mapping = self.edges[graph_id, typing]["mapping"]
            typing_ancestors = self.get_ancestors(typing, maybe)
            if typing in ancestors.keys():
                ancestors[typing].update(mapping)
            else:
                ancestors[typing] = mapping
            for anc, typ in typing_ancestors.items():
                if anc in ancestors.keys():
                    ancestors[anc].update(compose(mapping, typ))
                else:
                    ancestors[anc] = compose(mapping, typ)
        return ancestors

    def to_nx_graph(self):
        """Create a simple networkx graph representing the hierarchy."""
        g = nx.DiGraph()
        for node in self.nodes():
            g.add_node(node, self.nodes[node]["attrs"])
        for s, t in self.edges():
            g.add_edge(s, t, self.edges[s, t]["attrs"])
        return g

    def rename_graph(self, graph_id, new_graph_id):
        """Rename a graph in the hierarchy."""
        graph_obj = copy.deepcopy(self.nodes[graph_id])
        edges_obj = {}

        for s in self.successors(graph_id):
            obj = copy.deepcopy(self.edges[graph_id, s])
            edges_obj[(new_graph_id, s)] = obj
        for p in self.predecessors(graph_id):
            obj = copy.deepcopy(self.edges[p, graph_id])
            edges_obj[(p, new_graph_id)] = obj

        self.remove_node(graph_id)
        self.add_node(new_graph_id)
        self.nodes[new_graph_id] = graph_obj
        for (s, t), obj in edges_obj.items():
            self.add_edge(s, t)
            self.edges[s][t] = obj
        return

    def rename_node(self, graph_id, node, new_name):
        """Rename a node in a graph of the hierarchy."""
        if new_name in self.nodes[graph_id]["graph"].nodes():
            raise GraphError(
                "Node '%s' already in graph '%s'" %
                (new_name, graph_id)
            )
        if node not in self.nodes[graph_id]["graph"].nodes():
            raise GraphError(
                "Node '%s' does not exist in graph %s" %
                (node, graph_id)
            )
        relabel_node(self.nodes[graph_id]["graph"], node, new_name)
        for (source, _) in self.in_edges(graph_id):
            self.edges[source, graph_id].rename_target(node, new_name)
        for (_, target) in self.out_edges(graph_id):
            self.edges[graph_id, target].rename_source(node, new_name)

    def descendents(self, graph_id):
        """Get descentants (TODO: reverse names)."""
        desc = {graph_id}
        for source, _ in self.in_edges(graph_id):
            desc |= self.descendents(source)
        return desc

    def get_typing(self, source, target):
        """Get typing dict of `source` by `target`."""
        if (source, target) in self.edges():
            return self.edges[source, target]["mapping"]
        else:
            path = nx.shortest_path(self, source, target)
            return self.compose_path_typing(path)

    def get_relation(self, left, right):
        return self.relation[left][right]

    def set_node_typing(self, source_graph, target_graph, node_id, type_id):
        """Set typing to of a particular node."""
        self.edges[source_graph, target_graph]["mapping"][node_id] = type_id

    def get_rule_typing(self, source, target):
        """Get typing dict of `source` by `target` (`source` is rule)."""
        desc = self.descendents(target)
        if source not in desc:
            return None
        lhs_typing = {}
        rhs_typing = {}
        for (_, parent) in self.out_edges(source):
            parent_lhs = self.edges[source, parent]["lhs_mapping"]
            parent_rhs = self.edges[source, parent]["rhs_mapping"]
            if parent == target:
                lhs_typing.update(parent_lhs)
                rhs_typing.update(parent_rhs)
            elif parent in desc:
                parent_typing = self.get_typing(parent, target)
                lhs_typing.update(compose(parent_lhs, parent_typing))
                rhs_typing.update(compose(parent_rhs, parent_typing))
        # the typing of the preserved part coresponds to the typing
        # of the right hand side
        rule = self.nodes[source]["rule"]
        p_typing = {n: rhs_typing[rule.p_rhs[n]] for n in rule.p.nodes()}
        return (lhs_typing, p_typing, rhs_typing)

    def new_graph_from_nodes(self, nodes, graph_id, new_name, attrs):
        """Build a subgraph from nodes and type it by these nodes."""
        new_graph = self.nodes[graph_id]["graph"].subgraph(nodes)
        self.add_graph(new_name, new_graph, attrs)
        self.add_typing(new_name, graph_id, {n: n for n in nodes})

    def child_rule_from_nodes(self, nodes, graph_id, new_name, attrs):
        """Build a subrule from nodes and type it by these nodes."""
        pattern = self.nodes[graph_id]["graph"].subgraph(nodes)
        new_rule = Rule(pattern, pattern, pattern)
        self.add_rule(new_name, new_rule, attrs)
        mapping = {n: n for n in nodes}
        self.add_rule_typing(new_name, graph_id, mapping, mapping, attrs=attrs)

    def unique_graph_id(self, prefix):
        """Generate a new graph id starting with a prefix."""
        if prefix not in self.nodes():
            return prefix
        i = 0
        while "{}_{}".format(prefix, i) in self.nodes():
            i += 1
        return "{}_{}".format(prefix, i)

    def merge_by_id(self, hierarchy):
        """Recursive merge with a hierarchy."""
        common_ids = set(self.nodes()).intersection(
            set(hierarchy.nodes())
        )
        to_merge = []
        to_rename = {}
        for node in common_ids:
            if self.is_graph(node) and\
               hierarchy.is_graph(node):
                if equal(self.nodes[node]["graph"], hierarchy.nodes[node]["graph"]):
                    to_merge.append(node)
                else:
                    new_name = self.unique_graph_id(node)
                    to_rename[node] = new_name
            elif self.is_rule(node) and\
                    hierarchy.is_rule(node):
                if self.nodes[node]["rule"] == hierarchy.nodes[node]["rule"]:
                    to_merge.append(node)
                else:
                    new_name = self.unique_graph_id(node)
                    to_rename[node] = new_name
            else:
                new_name = self.unique_graph_id(node)
                to_rename[node] = new_name

        visited = []

        # Check consistency of the mappings to be merged
        for n1, n2 in self.edges():
            if n1 in to_merge and n2 in to_merge:
                if (n1, n2) in hierarchy.edges():
                    mapping = hierarchy.edges[n1, n2]["mapping"]
                    for key, value in mapping.items():
                        if key in self.edges[n1, n2]["mapping"].keys():
                            if self.edges[n1, n2].maping[key] != value:
                                raise HierarchyError(
                                    "Cannot merge with the input hierarchy: "
                                    "typing of nodes in `%s->%s` does not "
                                    "coincide with present typing!" %
                                    (n1, n2)
                                )

        # aux recursive function for merging by ids
        def _merge_node(node):
            if node in visited:
                return
            successors = hierarchy.successors(node)
            predecessors = hierarchy.predecessors(node)
            if node in to_merge:
                # merge node attrs
                self.nodes[node].add_attrs(
                    hierarchy.nodes[node]["attrs"]
                )
                visited.append(node)
                for suc in successors:
                    if suc in visited:
                        if suc in to_merge:
                            # merge edge mappings
                            mapping = hierarchy.edges[node, suc]["mapping"]
                            for key, value in mapping.items():
                                self.edges[node, suc]["mapping"][key] = value
                            # merge edge attrs
                            self.edges[node, suc].add_attrs(
                                hierarchy.edges[node, suc]
                            )
                        else:
                            if suc in to_rename.keys():
                                new_name = to_rename[suc]
                            else:
                                new_name = suc
                            if (node, new_name) not in self.edges():
                                self.add_edge(node, new_name)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edges[node, suc])
                                self.edges[node, new_name] = edge_obj
                    else:
                        _merge_node(suc)

                for pred in predecessors:
                    if pred in visited:
                        if pred in to_merge:
                            # merge edge mappings
                            mapping = hierarchy.edges[pred, node]["mapping"]
                            for key, value in mapping.items():
                                self.edges[pred, node]["mapping"][key] = value
                            # merge edge attrs
                            self.edges[pred, node].add_attrs(
                                hierarchy.edges[pred, node]["attrs"]
                            )
                        else:
                            if pred in to_rename.keys():
                                new_name = to_rename[pred]
                            else:
                                new_name = pred
                            if (new_name, node) not in self.edges():
                                self.add_edge(new_name, node)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edges[pred, node])
                                self.edges[new_name, node] = edge_obj
                    else:
                        _merge_node(pred)
            else:
                if node in to_rename:
                    new_name = to_rename[node]
                else:
                    new_name = node
                self.add_node(new_name)
                node_obj = copy.deepcopy(hierarchy.nodes[node])
                self.nodes[new_name] = node_obj
                visited.append(node)
                for suc in successors:
                    if suc in visited:
                        if suc in to_rename.keys():
                            new_suc_name = to_rename[suc]
                        else:
                            new_suc_name = suc
                        if (new_name, new_suc_name) not in self.edges():
                            self.add_edge(new_name, new_suc_name)
                            edge_obj = copy.deepcopy(hierarchy.edges[node, suc])
                            self.edges[new_name, new_suc_name] = edge_obj
                    else:
                        _merge_node(suc)

                for pred in predecessors:
                    if pred in visited:
                        if pred in to_rename.keys():
                            new_pred_name = to_rename[pred]
                        else:
                            new_pred_name = pred
                        if (new_pred_name, new_name) not in self.edges():
                            self.add_edge(new_pred_name, new_name)
                            edge_obj = copy.deepcopy(
                                hierarchy.edges[pred, node])
                            self.edges[new_pred_name, new_name] = edge_obj
                    else:
                        _merge_node(pred)
            return

        for node in hierarchy.nodes():
            _merge_node(node)

    def merge_by_attr(self, hierarchy, attr):
        """Merge with a hierarchy by nodes with matching attr."""
        to_merge = {}
        to_rename = {}
        for n1 in self.nodes():
            if attr in self.nodes[n1]["attrs"].keys():
                value = self.nodes[n1]["attrs"][attr]
                for n2 in hierarchy.nodes():
                    if attr in hierarchy.nodes[n2]["attrs"].keys():
                        if hierarchy.nodes[n2]["attrs"][attr] == value:
                            if n1 in to_merge.keys() or\
                               n2 in to_merge.values():
                                raise HierarchyError(
                                    "Cannot merge with the input hierarchy: "
                                    "matching of nodes by attr '%s' with "
                                    "value'%s' is ambiguous!" % (attr, value)
                                )
                            else:
                                if self.is_graph(n1) and\
                                   hierarchy.is_graph(n2):
                                    if equal(self.nodes[n1]["graph"],
                                             hierarchy.nodes[n2]["graph"]):
                                        to_merge[n1] = n2
                                elif self.is_rule(n1) and\
                                        hierarchy.is_rule(n2):
                                    if self.nodes[n1]["rule"] ==\
                                       hierarchy.nodes[n1]["rule"]:
                                        to_merge[n1] = n2
            else:
                continue

        for n in hierarchy.nodes():
            if n not in to_merge.values() and n in self.nodes():
                to_rename[n] = self.unique_graph_id(n)

        # Check consistency of the mappings to be merged
        for n1, n2 in self.edges():
            if n1 in to_merge.keys() and n2 in to_merge.keys():
                if (to_merge[n1], to_merge[n2]) in hierarchy.edges():
                    mapping = hierarchy.edges[
                        to_merge[n1],
                        to_merge[n2]]["mapping"].items()
                    for key, value in mapping:
                        if key in self.edges[n1, n2]["mapping"].keys():
                            if self.edges[n1, n2].maping[key] != value:
                                raise HierarchyError(
                                    "Cannot merge with the input hierarchy: "
                                    "typing of nodes in `%s->%s` does not "
                                    "coincide with present typing!" %
                                    (str(n1), str(n2)))
        visited = []
        new_names = {}

        # aux recursive function for merging by ids
        def _merge_node(node):
            if node in visited:
                return

            if node in to_merge.values():
                original_node = keys_by_value(to_merge, node)[0]
                new_name = str(original_node) + "_" + str(node)
                new_names[original_node] = new_name
                self.rename_graph(original_node, new_name)
                self.nodes[new_name].add_attrs(
                    hierarchy.nodes[node]["attrs"]
                )
                # recursive_merge(self.nodes[new_name]["attrs"],
                # hierarchy.nodes[node]["attrs"])
                visited.append(node)

                successors = hierarchy.successors(node)
                predecessors = hierarchy.predecessors(node)

                for suc in successors:
                    if suc in visited:
                        if suc in to_merge.values():
                            original_suc = keys_by_value(to_merge, suc)
                            # merge edge mappings
                            mapping = hierarchy.edges[node, suc]["mapping"]
                            for key, value in mapping.items():
                                self.edges[
                                    new_name,
                                    new_names[original_suc]]["mapping"][key] = value
                            # merge edge attrs
                            self.edges[
                                new_name,
                                new_names[original_suc]].add_attrs(
                                    hierarchy.edges[node, suc]["attrs"])
                        else:
                            if suc in to_rename.keys():
                                new_suc_name = to_rename[suc]
                            else:
                                new_suc_name = suc
                            if (new_name, new_suc_name) not in self.edges():
                                self.add_edge(new_name, new_suc_name)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edges[node, suc])
                                self.edges[new_name, new_suc_name] = edge_obj
                    else:
                        _merge_node(suc)

                for pred in predecessors:
                    if pred in visited:
                        if pred in to_merge.values():
                            original_pred = keys_by_value(to_merge, pred)[0]
                            # merge edge mappings
                            mapping = hierarchy.edges[pred, node]["mapping"]
                            for key, value in mapping.items():
                                self.edges[
                                    new_names[original_pred],
                                    new_name]["mapping"][key] = value
                            # merge edge attrs
                            self.edges[new_names[original_pred], new_name].add_attrs(
                                hierarchy.edges[pred, node]["attrs"]
                            )
                        else:
                            if pred in to_rename.keys():
                                new_pred_name = to_rename[pred]
                            else:
                                new_pred_name = pred
                            if (new_pred_name, new_name) not in self.edges():
                                self.add_edge(new_pred_name, new_name)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edges[pred, node])
                                self.edges[new_pred_name, new_name] = edge_obj
                    else:
                        _merge_node(pred)
            else:
                if node in to_rename.keys():
                    new_name = to_rename[node]
                else:
                    new_name = node
                self.add_node(new_name)
                node_obj = copy.deepcopy(hierarchy.nodes[node])
                self.nodes[new_name] = node_obj
                visited.append(node)

                successors = hierarchy.successors(node)
                predecessors = hierarchy.predecessors(node)

                for suc in successors:
                    if suc in visited:
                        if suc in to_merge.values():
                            # new_suc_name = new_names[original_node]
                            original_suc = keys_by_value(to_merge, suc)[0]
                            new_suc_name = new_names[suc]
                            # new_suc_name = new_names[original_suc]
                        elif suc in to_rename.keys():
                            new_suc_name = to_rename[suc]
                        else:
                            new_suc_name = suc

                        if (new_name, new_suc_name) not in self.edges():
                            self.add_edge(new_name, new_suc_name)
                            edge_obj = copy.deepcopy(hierarchy.edges[node, suc])
                            self.edges[new_name, new_suc_name] = edge_obj
                    else:
                        _merge_node(suc)

                for pred in predecessors:
                    if pred in visited:
                        if pred in to_merge.values():
                            original_pred = keys_by_value(to_merge, pred)[0]
                            new_pred_name = new_names[original_pred]
                        elif pred in to_rename.keys():
                            new_pred_name = to_rename[pred]
                        else:
                            new_pred_name = pred

                        if (new_pred_name, new_name) not in self.edges():
                            self.add_edge(new_pred_name, new_name)
                            edge_obj = copy.deepcopy(
                                hierarchy.edges[pred, node])
                            self.edges[new_pred_name, new_name] = edge_obj
                    else:
                        _merge_node(pred)

            return

        for node in hierarchy.nodes():
            _merge_node(node)

        return new_names

    def duplicate_subgraph(self, nodes, suffix):
        new = {}
        for node in nodes:
            new_id = self.unique_graph_id(node + suffix)
            new[node] = new_id
            self.add_node(new_id)
            self.nodes[new_id] = copy.deepcopy(self.nodes[node])
        for (source, target) in self.edges():
            if source in nodes:
                if target in nodes:
                    self.add_edge(new[source], new[target])
                    self.edges[new[source], new[target]] = copy.deepcopy(
                        self.edges[source, target])
                else:
                    self.add_edge(new[source], target)
                    self.edges[new[source], target] = copy.deepcopy(
                        self.edges[source, target])
            elif target in nodes:
                self.add_edge(source, new[target])
                self.edges[source, new[target]] = copy.deepcopy(
                    self.edges[source, target])
        return new

    def delete_all_children(self, graph_id):
        desc = self.descendents(graph_id)
        for node in desc:
            self.remove_node(node)
