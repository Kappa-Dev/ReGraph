"""."""
import copy
import itertools
import json
import networkx as nx
import os
import warnings


from networkx.algorithms import isomorphism
from networkx.exception import NetworkXNoPath

from regraph import rewriting_utils
from regraph import rule_type_checking
from regraph.attribute_sets import AttributeSet, FiniteSet
from regraph.category_op import (compose,
                                 check_homomorphism,
                                 is_total_homomorphism,
                                 relation_to_span)
from regraph.primitives import (get_relabeled_graph,
                                relabel_node,
                                get_edge,
                                graph_to_json,
                                graph_from_json,
                                equal)
from regraph.utils import (is_subdict,
                           keys_by_value,
                           normalize_attrs,
                           to_set,
                           replace_source,
                           replace_target)
from regraph.rules import Rule
from regraph.exceptions import (HierarchyError,
                                TotalityWarning,
                                ReGraphError,
                                RewritingError,
                                InvalidHomomorphism,
                                GraphError)


class AttributeContainter(object):
    """Abstract class for a container with attributes."""

    def attrs_to_json(self):
        """Convert attributes to json."""
        json_data = dict()
        for key, value in self.attrs.items():
            json_data[key] = value.to_json()
        return json_data

    @staticmethod
    def attrs_from_json(json_data):
        """Retreive attrs from json-like dict."""
        attrs = dict()
        for key, value in json_data.items():
            attrs[key] = AttributeSet.from_json(value)
        return attrs

    def add_attrs(self, attrs):
        """Add attrs to the graph node."""
        if attrs:
            new_attrs = copy.deepcopy(attrs)
            normalize_attrs(new_attrs)
        else:
            new_attrs = dict()
        if len(self.attrs) == 0:
            self.attrs = new_attrs
        else:
            for key, value in new_attrs.items():
                if key not in self.attrs.keys():
                    self.attrs[key] = FiniteSet(value)
                else:
                    self.attrs[key] = self.attrs[key].union(value)
        return

    def remove_attrs(self, attrs):
        """Remove attributes."""
        if attrs is None:
            pass
        else:
            normalize_attrs(self.attrs)
            for key, value in attrs.items():
                if key not in self.attrs.keys():
                    pass
                else:
                    elements_to_remove = []
                    for el in to_set(value):
                        if el in self.attrs[key]:
                            elements_to_remove.append(el)
                        else:
                            pass
                    for el in elements_to_remove:
                        self.attrs[key].remove(el)

    def update_attrs(self, attrs):
        """Update attribures."""
        new_attrs = copy.deepcopy(attrs)
        if new_attrs is None:
            pass
        else:
            normalize_attrs(new_attrs)
            self.attrs = new_attrs


class GraphNode(AttributeContainter):
    """Data structure incapsulating graph in the node of the hierarchy."""

    def __init__(self, graph, attrs=None):
        """Initialize graph node with graph object and attrs."""
        self.graph = graph
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def __eq__(self, other):
        """Equality of graph nodes."""
        return isinstance(other, GraphNode) and equal(self.graph, other.graph)


class RuleNode(AttributeContainter):
    """Data structure incapsulating a rule in the node of the hierarchy."""

    def __init__(self, rule, attrs=None):
        """Initialize rule with a Rule object."""
        self.rule = rule
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def __eq__(self, other):
        """Equality of rule nodes."""
        return isinstance(other, RuleNode) and self.rule == other.rule

    # def __ne__(self, other):
    #     return not (self == other)


class Typing(AttributeContainter):
    """Incapsulate homomorphism in the edge of the hierarchy."""

    def __init__(self, mapping, total=False, attrs=None):
        """Initialize homomorphism."""
        self.mapping = mapping
        self.total = total
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def is_total(self):
        """Test typing totality attribute."""
        return self.total

    def rename_source(self, old_name, new_name):
        """Rename source of typing."""
        replace_source(old_name, new_name, self.mapping)

    def rename_target(self, old_name, new_name):
        """Rename typing of typing."""
        replace_target(old_name, new_name, self.mapping)

    def __rmul__(self, other):
        """Right multiplication operation."""
        if isinstance(other, Typing):
            return Typing(
                compose(other.mapping),
                self.total and other.total,
                self.attrs)
        else:
            return NotImplemented

    def __mul__(self, other):
        """Multiplication operation."""
        if isinstance(other, Typing):
            return Typing(
                compose(other.mapping, self.mapping),
                self.total and other.total)

        elif isinstance(other, RuleTyping):
            return RuleTyping(
                compose(other.lhs_mapping, self.mapping),
                compose(other.rhs_mapping, self.mapping),
                other.lhs_total and self.total,
                other.rhs_total and self.total)
        else:
            return NotImplemented


class RuleTyping(AttributeContainter):
    """Incapsulates rule typing in the edge of the hierarchy."""

    def __init__(self, lhs_mapping, rhs_mapping,
                 lhs_total=False, rhs_total=False, attrs=None):
        """Initialize homomorphism."""
        self.lhs_mapping = copy.deepcopy(lhs_mapping)
        self.rhs_mapping = copy.deepcopy(rhs_mapping)
        self.lhs_total = lhs_total
        self.rhs_total = rhs_total
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def rename_source(self, old_name, new_name):
        """Name the source of the rule typing."""
        replace_source(old_name, new_name, self.lhs_mapping)
        replace_source(old_name, new_name, self.rhs_mapping)

    def rename_target(self, old_name, new_name):
        """Name the target of the rule typing."""
        replace_target(old_name, new_name, self.lhs_mapping)
        replace_target(old_name, new_name, self.rhs_mapping)

    def all_total(self):
        """All the components of the rule are totally typed."""
        return self.lhs_total and self.rhs_total

    def __rmul__(self, other):
        """Right multiplication."""
        if isinstance(other, Typing):
            return RuleTyping(
                compose(self.lhs_mapping, other.mapping),
                compose(self.rhs_mapping, other.mapping),
                self.lhs_total and other.total,
                self.rhs_total and other.total,
                self.attrs)
        else:
            return NotImplemented


class Relation(AttributeContainter):
    """Abstract class for relations in the hierarchy."""


class GraphRelation(Relation):
    """Implements relations on graphs."""

    def __init__(self, rel_pairs, attrs=None):
        """Initialize graph relation."""
        self.rel = rel_pairs
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def left_domain(self):
        """Return definition domain of the left member of relation."""
        return set([a for a, _ in self.rel])

    def right_domain(self):
        """Return definition domain of the right member of relation."""
        return set([b for _, b in self.rel])


# class RuleGraphRelation(Relation):
#     pass


class RuleRelation(Relation):
    """Implements relations on rules."""

    def __init__(self, lhs_pairs, p_pairs, rhs_pairs, attrs=None):
        """Initialize graph relation."""
        pass


class Hierarchy(nx.DiGraph):
    """Implements a hierarchy of graphs as a DAG."""

    # Similar to NetworkX node_dict_factory
    graph_dict_factory = dict
    rule_dict_factory = dict
    typing_dict_factory = dict
    rule_lhs_typing_dict_factory = dict
    rule_rhs_typing_dict_factory = dict
    relation_dict_factory = dict

    def __init__(self, directed=True,
                 graph_node_cls=GraphNode,
                 rule_node_cls=RuleNode,
                 graph_typing_cls=Typing,
                 rule_typing_cls=RuleTyping,
                 relation_cls=GraphRelation,
                 data=None):
        """Initialize an hierarchy of graphs."""
        nx.DiGraph.__init__(self, data)

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

        self.attrs = dict()
        self.directed = directed
        self.graph_node_cls = graph_node_cls
        self.rule_node_cls = rule_node_cls
        self.graph_typing_cls = graph_typing_cls
        self.rule_typing_cls = rule_typing_cls
        self.relation_cls = relation_cls
        self.relation = dict()
        return

    def __str__(self):
        """Print the hierarchy."""
        res = ""
        res += "\nGraphs (directed == %s): \n" % self.directed
        res += "\nNodes:\n"
        for n in self.nodes():
            if isinstance(self.node[n], GraphNode):
                res += "Graph:"
            elif type(self.node[n]) == RuleNode:
                res += "Rule:"
            else:
                raise HierarchyError(
                    "Hierarchy error: unknown type '%s' of the node '%s'!" %
                    (type(self.node[n]), n)
                )
            res += " " + str(n) + " " +\
                str(self.node[n].attrs) + "\n"
        res += "\n"
        res += "Typing homomorphisms: \n"
        for n1, n2 in self.edges():
            if isinstance(self.edge[n1][n2], self.graph_typing_cls):
                res += "%s -> %s: total == %s\n" %\
                    (
                        n1, n2, self.edge[n1][n2].total
                    )
                # res += "mapping: %s\n" % str(self.edge[n1][n2].mapping)
            elif isinstance(self.edge[n1][n2], self.rule_typing_cls):
                res +=\
                    ("%s -> %s: lhs_total == %s, rhs_total == %s,") %\
                    (
                        n1, n2, self.edge[n1][n2].lhs_total,
                        self.edge[n1][n2].rhs_total
                    )
                # res += "lhs mapping: %s\n" % str(self.edge[n1][n2].lhs_mapping)
                # res += "rhs mapping: %s\n" %
                # str(self.edge[n1][n2].rhs_mapping)
            else:
                raise HierarchyError(
                    "Hierarchy error: unknown type '%s' of the edge '%s->%s'!" %
                    (type(self.edge[n1][n2]), n1, n2)
                )
        res += "\nRelations:\n"
        for n1, n2 in self.relations():
            res += "%s-%s: %s\n" % (n1, n2, str(self.relation[n1][n2].attrs))

        res += "\n"
        res += "attributes : \n"
        res += str(self.attrs)
        res += "\n"

        return res

    def __eq__(self, hie):
        """Equality test."""
        g1 = self.to_nx_graph()
        g2 = hie.to_nx_graph()
        if not equal(g1, g2):
            return False

        for node in self.nodes():
            # normalize_attrs(self.node[node].attrs)
            # normalize_attrs(hie.node[node].attrs)
            if self.node[node].attrs != hie.node[node].attrs:
                return
            if isinstance(self.node[node], GraphNode) and\
               isinstance(hie.node[node], GraphNode):
                if not equal(
                    self.node[node].graph,
                    hie.node[node].graph
                ):
                    return False
            elif isinstance(self.node[node], RuleNode) and\
                    isinstance(hie.node[node], RuleNode):
                if self.node[node].rule != hie.node[node].rule:
                    return False
            else:
                return False

        for s, t in self.edges():
            # normalize_attrs(self.edge[s][t].attrs)
            # normalize_attrs(hie.edge[s][t].attrs)
            if self.edge[s][t].attrs != hie.edge[s][t].attrs:
                return False
            if isinstance(self.edge[s][t], self.graph_typing_cls) and\
               isinstance(hie.edge[s][t], self.graph_typing_cls):

                if self.edge[s][t].mapping != hie.edge[s][t].mapping:
                    return False
                if self.edge[s][t].total != hie.edge[s][t].total:
                    return False
            elif isinstance(self.edge[s][t], self.rule_typing_cls) and\
                    isinstance(hie.edge[s][t], self.rule_typing_cls):
                if self.edge[s][t].lhs_mapping != hie.edge[s][t].lhs_mapping:
                    return False
                if self.edge[s][t].rhs_mapping != hie.edge[s][t].rhs_mapping:
                    return False
                if self.edge[s][t].lhs_total != hie.edge[s][t].lhs_total:
                    return False
                if self.edge[s][t].rhs_total != hie.edge[s][t].rhs_total:
                    return False
        for n1, n2 in self.relations():
            if set(self.relation[n1][n2].rel) != set(hie.relation[n1][n2].rel):
                return False
        return True

    def add_attrs(self, attrs_dict):
        """Add attrs_dict to hierarchy attrs."""
        normalize_attrs(attrs_dict)
        old_attrs = self.attrs
        if old_attrs is None:
            self.attrs = copy.deepcopy(attrs_dict)
        else:
            for key in attrs_dict:
                if key in old_attrs:
                    old_attrs[key] = old_attrs[key].union(attrs_dict[key])
                else:
                    old_attrs[key] = attrs_dict[key]

    def remove_node(self, n):
        """Overloading NetworkX method `remove_node`."""
        nx.DiGraph.remove_node(self, n)
        if n in self.relation.keys():
            del self.relation[n]
        for k, v in self.relation.items():
            if n in v.keys():
                del self.relation[k][n]
        return

    def remove_relation(self, g1, g2):
        """Remove relation from the hierarchy."""
        if (g1, g2) not in self.relations() and\
           (g2, g1) not in self.relations():
            raise HierarchyError(
                "Relation '%s-%s' is not defined in the hierarchy" %
                (g1, g2)
            )
        self.relation.update({g1: dict()})
        del self.relation[g2][g1]

    def relations(self):
        """Return a list of relations."""
        rel = list()
        for k, v in self.relation.items():
            if len(self.relation[k]) > 0:
                for v, _ in self.relation[k].items():
                    if (k, v) not in rel and (v, k) not in rel:
                        rel.append((k, v))
        return rel

    def add_graph(self, graph_id, graph, graph_attrs=None):
        """Add graph to the hierarchy."""
        if self.directed != graph.is_directed():
            if self.directed:
                raise HierarchyError(
                    "Hierarchy is defined for directed == %s graphs!" %
                    self.directed
                )
            else:
                raise HierarchyError(
                    "Hierarchy is defined for undirected graphs!")
        if graph_id in self.nodes():
            raise HierarchyError(
                "Node '%s' already exists in the hierarchy!" %
                graph_id
            )
        self.add_node(graph_id)
        if graph_attrs is not None:
            normalize_attrs(graph_attrs)
        self.node[graph_id] = self.graph_node_cls(graph, graph_attrs)
        if graph_id not in self.relation.keys():
            self.relation.update({graph_id: dict()})
        self.graph[graph_id] = self.node[graph_id].graph
        if graph_id not in self.typing.keys():
            self.typing[graph_id] = dict()
        return

    def add_rule(self, rule_id, rule, rule_attrs=None):
        """Add rule to the hierarchy."""
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
        self.node[rule_id] = RuleNode(rule, rule_attrs)
        self.rule[rule_id] = self.node[rule_id].rule
        if rule_id not in self.rule_lhs_typing.keys():
            self.rule_lhs_typing[rule_id] = dict()
        if rule_id not in self.rule_rhs_typing.keys():
            self.rule_rhs_typing[rule_id] = dict()
        return

    def add_typing(self, source, target, mapping,
                   total=False, attrs=None):
        """Add homomorphism to the hierarchy."""
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
        if not isinstance(self.node[source], GraphNode):
            if type(self.node[source]) == RuleNode:
                raise HierarchyError(
                    "Source node is a rule, use `add_rule_typing` "
                    "method instead!"
                )
            else:
                raise HierarchyError(
                    "Source of a typing should be a graph, `%s` is provided!" %
                    type(self.node[source])
                )
        if not isinstance(self.node[target], GraphNode):
            raise HierarchyError(
                "Target of a typing should be a graph, `%s` is provided!" %
                type(self.node[target])
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
            self.node[source].graph,
            self.node[target].graph,
            mapping,
            total=total
        )

        # check if newly created path commutes with existing shortest paths
        self._check_consistency(source, target, mapping)

        self.add_edge(source, target)
        if attrs is not None:
            normalize_attrs(attrs)
        self.edge[source][target] = self.graph_typing_cls(
            mapping, total, attrs)
        self.typing[source][target] = self.edge[source][target].mapping
        return

    def add_rule_typing(self, rule_id, graph_id, lhs_mapping,
                        rhs_mapping=None,
                        lhs_total=False, rhs_total=False,
                        attrs=None):
        """Add typing of a rule."""
        if rule_id not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % rule_id)
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % graph_id)

        if type(self.node[rule_id]) != RuleNode:
            raise HierarchyError(
                "Source of a rule typing should be a rule, `%s` is provided!" %
                type(self.node[rule_id])
            )
        if not isinstance(self.node[graph_id], GraphNode):
            raise HierarchyError(
                "Target of a rule typing should be a graph, `%s` is provided!" %
                type(self.node[graph_id])
            )
        # check if an lhs typing is valid
        check_homomorphism(
            self.node[rule_id].rule.lhs,
            self.node[graph_id].graph,
            lhs_mapping,
            total=lhs_total
        )

        new_rhs_mapping = rhs_mapping
        if new_rhs_mapping is None:
            new_rhs_mapping = dict()
        rule = self.node[rule_id].rule
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
            self.node[rule_id].rule.rhs,
            self.node[graph_id].graph,
            new_rhs_mapping,
            total=rhs_total
        )

        # check if newly created path commutes with existing shortest paths
        self._check_rule_typing(
            rule_id, graph_id, lhs_mapping, new_rhs_mapping)

        self.add_edge(rule_id, graph_id)
        if attrs is not None:
            normalize_attrs(attrs)
        self.edge[rule_id][graph_id] = self.rule_typing_cls(
            lhs_mapping,
            new_rhs_mapping,
            lhs_total,
            rhs_total,
            attrs
        )
        self.rule_lhs_typing[rule_id][graph_id] =\
            self.edge[rule_id][graph_id].lhs_mapping
        self.rule_rhs_typing[rule_id][graph_id] =\
            self.edge[rule_id][graph_id].rhs_mapping
        return

    def add_relation(self, g1, g2, rel_pairs, attrs=None):
        """Add relation to the hierarchy."""
        if g1 not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % g1)
        if g2 not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % g2)

        if not isinstance(self.node[g1], GraphNode):
            raise HierarchyError(
                "Relation can be defined on graphs, '%s' is provided" %
                type(self.node[g1])
            )
        if not isinstance(self.node[g2], GraphNode):
            raise HierarchyError(
                "Relation can be defined on graphs, '%s' is provided" %
                type(self.node[g2])
            )

        if (g1, g2) in self.relations():
            raise HierarchyError(
                "Relation '%s-%s' already exists in the hierarchy "
                "multiple edges are not allowed!" %
                (g1, g2)
            )

        # check relation is well-defined on g1 and g2
        for n1, n2 in rel_pairs:
            if n1 not in self.node[g1].graph.nodes():
                raise HierarchyError(
                    "Relation is not valid: node '%s' does not "
                    "exist in a graph '%s'" %
                    (n1, g1)
                )
            if n2 not in self.node[g2].graph.nodes():
                raise HierarchyError(
                    "Relation is not valid: node '%s' does not "
                    "exist in a graph '%s'" %
                    (n2, g2)
                )
        if attrs is not None:
            normalize_attrs(attrs)
        rel_ab_obj = GraphRelation(rel_pairs, attrs)
        rel_ba_obj = GraphRelation(
            set([(b, a) for a, b in rel_pairs]),
            attrs
        )
        self.relation[g1].update({g2: rel_ab_obj})
        self.relation[g2].update({g1: rel_ba_obj})
        return

    def adjacent_relations(self, g):
        """Return a list of related graphs."""
        if g not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % g)
        return list(self.relation[g].keys())

    def relation_to_span(self, g1, g2, edges=False, attrs=False):
        """Convert relation to a span."""
        if g1 not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % g1)
        if g2 not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % g2)

        if (g1, g2) not in self.relations() and\
           (g2, g1) not in self.relations():
            raise HierarchyError(
                "Relation between graphs '%s' and '%s' is not defined" %
                (g1, g2)
            )

        return relation_to_span(
            self.node[g1].graph,
            self.node[g2].graph,
            self.relation[g1][g2].rel,
            edges,
            attrs,
            self.directed)

    def remove_graph(self, graph_id, reconnect=False):
        """Remove graph from the hierarchy.

        If `reconnect`, map the children homomorphisms
        of this graph to its parents.
        """
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Graph `%s` is not defined in the hierarchy!" % graph_id)

        if reconnect:
            out_graphs = self.successors(graph_id)
            in_graphs = self.predecessors(graph_id)

            for source in in_graphs:
                for target in out_graphs:
                    if isinstance(self.edge[source][graph_id], self.rule_typing_cls):
                        lhs_mapping = compose(
                            self.edge[source][graph_id].lhs_mapping,
                            self.edge[graph_id][target].mapping
                        )
                        rhs_mapping = compose(
                            self.edge[source][graph_id].rhs_mapping,
                            self.edge[graph_id][target].mapping
                        )
                        if (source, target) not in self.edges():
                            self.add_rule_typing(
                                source,
                                target,
                                lhs_mapping,
                                rhs_mapping,
                                self.edge[source][graph_id].lhs_total and
                                self.edge[graph_id][target].lhs_total,
                                self.edge[source][graph_id].rhs_total and
                                self.edge[graph_id][target].rhs_total
                            )
                    elif isinstance(self.edge[source][graph_id], self.graph_typing_cls):
                        # compose two homomorphisms
                        mapping = compose(
                            self.edge[source][graph_id].mapping,
                            self.edge[graph_id][target].mapping
                        )

                        if (source, target) not in self.edges():
                            self.add_typing(
                                source,
                                target,
                                mapping,
                                self.edge[source][graph_id].total and
                                self.edge[graph_id][target].total
                            )

        self.remove_node(graph_id)

    def node_type(self, graph_id, node_id):
        """Get a list of the immediate types of a node."""
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Graph '%s' is not defined in the hierarchy!"
                % graph_id
            )
        if node_id not in self.node[graph_id].graph.nodes():
            raise HierarchyError(
                "Graph '%s' does not have a node with id '%s'!"
                % (graph_id, node_id)
            )
        types = {}
        for _, typing in self.out_edges(graph_id):
            mapping = self.edge[graph_id][typing].mapping
            if node_id in mapping.keys():
                types[typing] = mapping[node_id]
        return types

    def to_total(self, source, target):
        """Make a typing total (if mapping is total)."""
        if source not in self.nodes():
            raise HierarchyError(
                "Node '%s' is not defined in the hierarchy!" % source)
        if (source, target) not in self.edges():
            raise HierarchyError(
                "Typing `%s->%s` does not exist!" %
                (source, target)
            )
        if isinstance(self.node[source], GraphNode):
            nodes = self.node[source].graph.nodes()
            typing = self.edge[source][target]
            if is_total_homomorphism(nodes, typing.mapping):
                typing.total = True
            else:
                untyped_nodes = [
                    node for node in nodes if node not in typing.mapping.keys()
                ]
                raise HierarchyError(
                    "Cannot make `%s->%s` typing total: nodes [%s] "
                    "do not have types, please type them first!" %
                    (source, target, ", ".join(untyped_nodes))
                )
        elif isinstance(self.node[source], RuleNode):
            lhs_nodes = self.node[source].rule.lhs.nodes()
            rhs_nodes = self.node[target].rule.rhs.nodes()
            lhs_typing = self.edge[source][target].lhs_mapping
            rhs_typing = self.edge[source][target].rhs_mapping
            if is_total_homomorphism(lhs_nodes, lhs_typing) and\
               is_total_homomorphism(rhs_nodes, rhs_typing):
                self.edge[source][target].total = True
            else:
                untyped_lhs_nodes = [
                    node for node in lhs_nodes if node not in lhs_typing.keys()
                ]
                untyped_rhs_nodes = [
                    node for node in rhs_nodes if node not in rhs_typing.keys()
                ]
                raise HierarchyError(
                    "Cannot make `%s->%s` typing total: lhs nodes [%s] "
                    "and rhs nodes [%s] do not have types, please type them first!" %
                    (source, target, ", ".join(untyped_lhs_nodes),
                     ", ".join(untyped_rhs_nodes))
                )
        return

    def compose_path_typing(self, path):
        """Compose homomorphisms along the path."""
        s = path[0]
        if isinstance(self.node[s], GraphNode):
            t = path[1]
            homomorphism = self.edge[s][t].mapping
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                homomorphism = compose(
                    homomorphism,
                    self.edge[s][t].mapping
                )
            return homomorphism
        else:
            t = path[1]
            lhs_homomorphism = self.edge[s][t].lhs_mapping
            rhs_homomorphism = self.edge[s][t].rhs_mapping
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                lhs_homomorphism = compose(
                    lhs_homomorphism, self.edge[s][t].mapping)
                rhs_homomorphism = compose(
                    rhs_homomorphism, self.edge[s][t].mapping)
            return lhs_homomorphism, rhs_homomorphism

    def _path_from_rule(self, path):
        s = path[0]
        return isinstance(self.node[s], RuleNode)

    def _check_rule_typing(self, rule_id, graph_id, lhs_mapping, rhs_mapping):
        all_paths = nx.all_pairs_shortest_path(self)

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
                    s_t_paths = nx.all_shortest_paths(self, rule_id, t)
                    for path in s_t_paths:
                        lhs_h, rhs_h = self.compose_path_typing(path)
                        if lhs_h != new_lhs_h:
                            raise HierarchyError(
                                "Invalid lhs typing: homomorphism does not commute with an existing " +
                                "path from '%s' to '%s'!" % (s, t)
                            )
                        if rhs_h != new_rhs_h:
                            raise HierarchyError(
                                "Invalid rhs typing: homomorphism does not commute with an existing " +
                                "path from '%s' to '%s'!" % (s, t)
                            )
                except(nx.NetworkXNoPath):
                    pass
        return

    def _check_consistency(self, source, target, mapping=None):
        all_paths = nx.all_pairs_shortest_path(self)

        paths_to_source = {}
        paths_from_target = {}
        for s in self.nodes():
            if source in all_paths[s].keys():
                paths_to_source[s] = all_paths[s][source]
            if s == target:
                for key in all_paths[target].keys():
                    paths_from_target[key] = all_paths[target][key]

        for s in paths_to_source.keys():
            if self._path_from_rule(paths_to_source[s]):
                for t in paths_from_target.keys():
                    # find homomorphism from s to t via new path
                    if s == source:
                        raise HierarchyError(
                            "Found a rule typing some node in the hierarchy!"
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
                        s_t_paths = nx.all_shortest_paths(self, s, t)
                        for path in s_t_paths:
                            lhs_h, rhs_h = self.compose_path_typing(path)
                            if lhs_h != new_lhs_h:
                                raise HierarchyError(
                                    "Invalid lhs typing: homomorphism does "
                                    "not commute with an existing " +
                                    "path from '%s' to '%s'!" % (s, t)
                                )
                            if rhs_h != new_rhs_h:
                                raise HierarchyError(
                                    "Invalid rhs typing: homomorphism does "
                                    "not commute with an existing " +
                                    "path from '%s' to '%s'!" % (s, t)
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
                    s_t_paths = nx.all_shortest_paths(self, s, t)
                    try:
                        # check only the first path
                        for path in s_t_paths:
                            path_homomorphism = self.compose_path_typing(path)
                            if path_homomorphism != new_homomorphism:
                                raise HierarchyError(
                                    "Homomorphism does not commute with an " +
                                    "existing path from '%s' to '%s'!" % (s, t)
                                )
                    except(nx.NetworkXNoPath):
                        pass

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
        if node_id not in self.node[graph_id].graph.nodes():
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
            new_mapping_s1 = copy.deepcopy(self.edge[graph_id][s1].mapping)
            new_mapping_s2 = copy.deepcopy(self.edge[graph_id][s2].mapping)

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
            self.edge[graph_id][typing_graph].mapping.update({
                node_id: type_id
            })
        return

    def remove_node_type(self, graph_id, typing_graph, node_id):
        """Remove a type a node in a graph `graph_id`."""
        if (graph_id, typing_graph) not in self.edges():
            raise HierarchyError(
                "Typing `%s->%s` does not exist!" %
                (graph_id, typing_graph)
            )

        # find types that will be removed  as a side effect
        types_to_remove = set()
        # 1. find pairs of successors that have common ancestors
        ancestors = {}
        for n in self.successors(graph_id):
            ancestors[n] = self._get_ancestors_paths(n)

        for s in self.successors(graph_id):
            c_anc = set(ancestors[s].keys()).intersection(
                set(ancestors[typing_graph].keys())
            )
            if len(c_anc) > 0:
                types_to_remove.add(s)

        if self.edge[graph_id][typing_graph].total:
            warnings.warn(
                "Total typing '%s->%s' became partial!" %
                (graph_id, typing_graph),
                TotalityWarning
            )

        # remove typing
        for t in types_to_remove:
            del self.edge[graph_id][t].mapping[node_id]
        return

    # def find_matching2(self, graph_id, pattern, pattern_typings=None):
    #     """find matchings of pattern in graph_id"""
    #     graph = self.node[graph_id].graph
    #     graph_typings = {}
    #     typing_graphs = {}
    #     if pattern_typings is None:
    #         pattern_typings = {}
    #     else:
    #         for (typ_id, typ_map) in pattern_typings.items():
    #             typing = self.get_typing(graph_id, typ_id)
    #             if typing is None:
    #                 typing = {}
    #             graph_typings[typ_id] = typing
    #             typing_graphs[typ_id] = self.node[typ_id].graph
    # return find_match(graph, pattern, graph_typings, pattern_typings,
    # typing_graphs)

    def find_matching(self, graph_id, pattern, pattern_typing=None):
        """Find an instance of a pattern in a specified graph.

        `graph_id` -- id of a graph in the hierarchy to search for matches;
        `pattern` -- nx.(Di)Graph object defining a pattern to match;
        `pattern_typing` -- a dictionary that specifies a typing of a pattern,
        keys of the dictionary -- graph id that types a pattern, this graph
        should be among parents of the `graph_id` graph; values are mappings
        of nodes from pattern to the typing graph;
        """
        if type(self.node[graph_id]) == RuleNode:
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
                        self.node[typing_graph].graph,
                        mapping,
                        total=False
                    )
                except InvalidHomomorphism as e:
                    raise ReGraphError(
                        "Specified pattern is not valid in the "
                        "hierarchy (it produces the following error: %s) " % e
                    )
            pattern_typing = new_pattern_typing

        labels_mapping = dict(
            [(n, i + 1) for i, n in
             enumerate(self.node[graph_id].graph.nodes())]
        )
        g = get_relabeled_graph(self.node[graph_id].graph, labels_mapping)

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
                        ).items()
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
                            if g_typing[typing_graph][node] == typing[pattern_node]:
                                if is_subdict(pattern.node[pattern_node], g.node[node]):
                                    match = True
                            else:
                                # there is no mapping of this node in the
                                # typing by `typing_graph`
                                pass
                        else:
                            if is_subdict(pattern.node[pattern_node], g.node[node]):
                                match = True
                    if match:
                        matching_nodes.add(node)
                else:
                    if is_subdict(pattern.node[pattern_node], g.node[node]):
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
            # Check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if pattern_typing:
                    for typing_graph, (typing, _) in pattern_typing.items():
                        if node in g_typing[typing_graph].keys() and\
                           pattern_node in typing.keys():
                            if g_typing[typing_graph][node] != typing[pattern_node]:
                                break
                        if not is_subdict(pattern.node[pattern_node], subgraph.node[node]):
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
        if type(self.node[graph_id]) == RuleNode:
            raise ReGraphError(
                "Pattern matching in a rule is not implemented!")

        if type(self.node[rule_id]) != RuleNode:
            raise HierarchyError("Invalid rule `%s` to match!" % rule_id)

        rule = self.node[rule_id].rule

        lhs_typing = {}
        rhs_typing = {}

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] = self.edge[rule_id][suc].lhs_mapping
            rhs_typing[suc] = self.edge[rule_id][suc].rhs_mapping

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

    def rewrite(self, graph_id, rule, instance,
                lhs_typing=None, rhs_typing=None, strict=True, inplace=True):
        """Rewrite and propagate the changes up & down."""
        if type(self.node[graph_id]) == RuleNode:
            raise ReGraphError("Rewriting of a rule is not implemented!")

        # 1. Check consistency of the input
        # 1a. Autocomplete typing

        new_lhs_typing, new_rhs_typing =\
            rule_type_checking._autocomplete_typing(
                self, graph_id, instance, lhs_typing,
                rhs_typing, rule.p_lhs, rule.p_rhs)

        # 1b. Check that instance is consistent with lhs & rhs typing
        rule_type_checking._check_instance(
            self, graph_id, rule.lhs, instance, new_lhs_typing)

        # 1c. Check consistency of the (autocompleted) rhs & lhs typings
        if new_lhs_typing is not None and new_rhs_typing is not None:
            try:
                rule_type_checking._check_self_consistency(
                    self, new_lhs_typing)
            except ReGraphError as e:
                raise RewritingError(
                    "Typing of the lhs is self inconsistent: %s" % str(e)
                )
            try:
                rule_type_checking._check_self_consistency(
                    self, new_rhs_typing, strict)
            except ReGraphError as e:
                raise RewritingError(
                    "Typing of the rhs is self inconsistent: %s" % str(e)
                )

            rule_type_checking._check_lhs_rhs_consistency(
                self, graph_id, rule, instance,
                new_lhs_typing, new_rhs_typing,
                strict)

            if strict is True:
                rule_type_checking._check_totality(
                    self, graph_id, rule, instance,
                    new_lhs_typing, new_rhs_typing)

        # 2. Rewrite a graph `graph_id`
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

        if rule.is_restrictive():
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

        downstream_changes = dict()
        if strict is False:
            downstream_changes =\
                rewriting_utils._propagate_down(
                    self, graph_id, graph_construct,
                    rule, instance, new_rhs_typing, inplace)

        # 6. Apply all the changes in the hierarchy
        if inplace:
            rewriting_utils._apply_changes(
                self, upstream_changes, downstream_changes)
            updated_graphs = None
            return (self, updated_graphs)
        else:
            # First, create a new hierarchy
            new_graph = copy.deepcopy(self)
            rewriting_utils._apply_changes(
                new_graph, upstream_changes, downstream_changes)
            updated_graphs = None
            return (new_graph, updated_graphs)

    def apply_rule(self, graph_id, rule_id, instance,
                   strong_typing=True, total=False, inplace=True):
        """Apply rule from the hierarchy."""
        if type(self.node[graph_id]) == RuleNode:
            raise ReGraphError("Rewriting of a rule is not implemented!")

        if type(self.node[rule_id]) != RuleNode:
            raise RewritingError("Invalid rewriting rule `%s`!" % rule_id)

        rule = self.node[rule_id].rule

        lhs_typing = dict()
        rhs_typing = dict()

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] =\
                self.edge[rule_id][suc].lhs_mapping
            rhs_typing[suc] =\
                self.edge[rule_id][suc].rhs_mapping

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
            if isinstance(self.node[node], RuleNode):
                json_data["rules"].append({
                    "id": node,
                    "rule": self.node[node].rule.to_json(),
                    "attrs": self.node[node].attrs_to_json()
                })
            elif isinstance(self.node[node], GraphNode):
                json_data["graphs"].append({
                    "id": node,
                    "graph": graph_to_json(self.node[node].graph),
                    "attrs": self.node[node].attrs_to_json()
                })

            else:
                raise HierarchyError("Unknown type of the node '%s'!" % node)
        for s, t in self.edges():
            if isinstance(self.edge[s][t], self.graph_typing_cls):
                json_data["typing"].append({
                    "from": s,
                    "to": t,
                    "mapping": self.edge[s][t].mapping,
                    "total": self.edge[s][t].total,
                    "attrs": self.edge[s][t].attrs_to_json()
                })
            elif isinstance(self.edge[s][t], self.rule_typing_cls):
                json_data["rule_typing"].append({
                    "from": s,
                    "to": t,
                    "lhs_mapping": self.edge[s][t].lhs_mapping,
                    "rhs_mapping": self.edge[s][t].rhs_mapping,
                    "lhs_total": self.edge[s][t].lhs_total,
                    "rhs_total": self.edge[s][t].rhs_total,
                    "attrs": self.edge[s][t].attrs_to_json()
                })
            else:
                raise HierarchyError(
                    "Unknown type of the edge '%s->%s'!" % (s, t)
                )
        for u, v in self.relations():
            json_data["relations"].append({
                "from": u,
                "to": v,
                "rel": [[a, b] for a, b in self.relation[u][v].rel],
                "attrs": self.relation[u][v].attrs_to_json()
            })
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
                graph = graph_from_json(graph_data["graph"], directed)
                if "attrs" not in graph_data.keys():
                    attrs = dict()
                else:
                    attrs = AttributeContainter.attrs_from_json(
                        graph_data["attrs"])

                hierarchy.add_graph(
                    graph_data["id"],
                    graph,
                    attrs
                )

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
                    rule_data["id"],
                    rule,
                    attrs
                )

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
                    typing_data["total"],
                    attrs
                )

        # add rule typing
        for rule_typing_data in json_data["rule_typing"]:
            if ignore is not None and\
               "rule_typing" in ignore.keys() and\
               (rule_typing_data["from"], rule_typing_data["to"]) in ignore["rule_typing"]:
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
               ((relation_data["from"], relation_data["to"]) in ignore["relations"] or
                    (relation_data["to"], relation_data["from"]) in ignore["relations"]):
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
                    [(a, b) for a, b in relation_data["rel"]],
                    attrs
                )
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

    def remove_attrs(self, graph_id, node, attr_dict, force=False):
        """Remove attributes of a node in a graph `graph_id`."""
        # try to remove attrs
        children = self.predecessors(graph_id)
        typing_with_attrs = set()
        for child in children:
            typing_with_attrs.add(child)

        if len(typing_with_attrs) == 0:
            pass
            # remove_node_attrs(self.node[graph_id].graph, node, attr_dict)
        else:
            if force:
                pass
            else:
                # check no homomorphisms are broken
                pass
        return

    def get_ancestors(self, graph_id, maybe=None):
        """Return ancestors of a graph as well as the typing morphisms."""
        ancestors = {}
        for _, typing in self.out_edges(graph_id):
            if maybe is not None and typing not in maybe:
                continue
            mapping = self.edge[graph_id][typing].mapping
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
            g.add_node(node, self.node[node].attrs)
        for s, t in self.edges():
            g.add_edge(s, t, self.edge[s][t].attrs)
        return g

    def rename_graph(self, graph_id, new_graph_id):
        """Rename a graph in the hierarchy."""
        graph_obj = copy.deepcopy(self.node[graph_id])
        edges_obj = {}

        for s in self.successors(graph_id):
            obj = copy.deepcopy(self.edge[graph_id][s])
            edges_obj[(new_graph_id, s)] = obj
        for p in self.predecessors(graph_id):
            obj = copy.deepcopy(self.edge[p][graph_id])
            edges_obj[(p, new_graph_id)] = obj

        self.remove_node(graph_id)
        self.add_node(new_graph_id)
        self.node[new_graph_id] = graph_obj
        for (s, t), obj in edges_obj.items():
            self.add_edge(s, t)
            self.edge[s][t] = obj
        return

    def rename_node(self, graph_id, node, new_name):
        """Rename a node in a graph of the hierarchy."""
        if new_name in self.node[graph_id].graph.nodes():
            raise GraphError(
                "Node '%s' already in graph '%s'" %
                (new_name, graph_id)
            )
        if node not in self.node[graph_id].graph.nodes():
            raise GraphError(
                "Node '%s' does not exist in graph %s" %
                (node, graph_id)
            )
        relabel_node(self.node[graph_id].graph, node, new_name)
        for (source, _) in self.in_edges(graph_id):
            self.edge[source][graph_id].rename_target(node, new_name)
        for (_, target) in self.out_edges(graph_id):
            self.edge[graph_id][target].rename_source(node, new_name)

    def descendents(self, graph_id):
        """Get descentants (TODO: reverse names)."""
        desc = {graph_id}
        for source, _ in self.in_edges(graph_id):
            desc |= self.descendents(source)
        return desc

    def get_typing(self, source, target):
        """Get typing dict of `source` by `target`."""
        desc = self.descendents(target)
        if source not in desc:
            return None
        ancestors = self.get_ancestors(source, desc)
        return ancestors[target]

    def get_rule_typing(self, source, target):
        """Get typing dict of `source` by `target` (`source` is rule)."""
        desc = self.descendents(target)
        if source not in desc:
            return None
        lhs_typing = {}
        rhs_typing = {}
        for (_, parent) in self.out_edges(source):
            parent_lhs = self.edge[source][parent].lhs_mapping
            parent_rhs = self.edge[source][parent].rhs_mapping
            if parent == target:
                lhs_typing.update(parent_lhs)
                rhs_typing.update(parent_rhs)
            elif parent in desc:
                parent_typing = self.get_typing(parent, target)
                lhs_typing.update(compose(parent_lhs, parent_typing))
                rhs_typing.update(compose(parent_rhs, parent_typing))
        # the typing of the preserved part coresponds to the typing
        # of the right hand side
        rule = self.node[source].rule
        p_typing = {n: rhs_typing[rule.p_rhs[n]] for n in rule.p.nodes()}
        return (lhs_typing, p_typing, rhs_typing)

    def new_graph_from_nodes(self, nodes, graph_id, new_name, attrs):
        """Build a subgraph from nodes and type it by these nodes."""
        new_graph = self.node[graph_id].graph.subgraph(nodes)
        self.add_graph(new_name, new_graph, attrs)
        self.add_typing(new_name, graph_id, {n: n for n in nodes})

    def child_rule_from_nodes(self, nodes, graph_id, new_name, attrs):
        """Build a subrule from nodes and type it by these nodes."""
        pattern = self.node[graph_id].graph.subgraph(nodes)
        new_rule = Rule(pattern, pattern, pattern)
        self.add_rule(new_name, new_rule, attrs)
        mapping = {n: n for n in nodes}
        self.add_rule_typing(new_name, graph_id, mapping, mapping, attrs=attrs)

    def _generate_new_name(self, node):
        i = 1
        new_name = "%s_%s" % (node, i)
        while new_name in self.nodes():
            i += 1
            new_name = "%s_%s" % (node, i)
        return new_name

    def merge_by_id(self, hierarchy):
        """Recursive merge with a hierarchy."""
        common_ids = set(self.nodes()).intersection(
            set(hierarchy.nodes())
        )
        to_merge = []
        to_rename = {}
        for node in common_ids:
            if isinstance(self.node[node], GraphNode) and\
               isinstance(hierarchy.node[node], GraphNode):
                if equal(self.node[node].graph, hierarchy.node[node].graph):
                    to_merge.append(node)
                else:
                    new_name = self._generate_new_name(node)
                    to_rename[node] = new_name
            elif isinstance(self.node[node], RuleNode) and\
                    isinstance(hierarchy.node[node], RuleNode):
                if self.node[node].rule == hierarchy.node[node].rule:
                    to_merge.append(node)
                else:
                    new_name = self._generate_new_name(node)
                    to_rename[node] = new_name
            else:
                new_name = self.__generate_new_name(node)
                to_rename[node] = new_name

        visited = []

        # Check consistency of the mappings to be merged
        for n1, n2 in self.edges():
            if n1 in to_merge and n2 in to_merge:
                if (n1, n2) in hierarchy.edges():
                    mapping = hierarchy.edge[n1][n2].mapping
                    for key, value in mapping.items():
                        if key in self.edge[n1][n2].mapping.keys():
                            if self.edge[n1][n2].maping[key] != value:
                                raise HierarchyError(
                                    "Cannot merge with the input hierarchy: typing of nodes"
                                    "in `%s->%s` does not coincide with present typing!" %
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
                self.node[node].add_attrs(
                    hierarchy.node[node].attrs
                )
                visited.append(node)
                for suc in successors:
                    if suc in visited:
                        if suc in to_merge:
                            # merge edge mappings
                            mapping = hierarchy.edge[node][suc].mapping
                            for key, value in mapping.items():
                                self.edge[node][suc].mapping[key] = value
                            # merge edge attrs
                            self.edge[node][suc].add_attrs(
                                hierarchy.edge[node][suc]
                            )
                        else:
                            if suc in to_rename.keys():
                                new_name = to_rename[suc]
                            else:
                                new_name = suc
                            if (node, new_name) not in self.edges():
                                self.add_edge(node, new_name)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edge[node][suc])
                                self.edge[node][new_name] = edge_obj
                    else:
                        _merge_node(suc)

                for pred in predecessors:
                    if pred in visited:
                        if pred in to_merge:
                            # merge edge mappings
                            mapping = hierarchy.edge[pred][node].mapping
                            for key, value in mapping.items():
                                self.edge[pred][node].mapping[key] = value
                            # merge edge attrs
                            self.edge[pred][node].add_attrs(
                                hierarchy.edge[pred][node].attrs
                            )
                        else:
                            if pred in to_rename.keys():
                                new_name = to_rename[pred]
                            else:
                                new_name = pred
                            if (new_name, node) not in self.edges():
                                self.add_edge(new_name, node)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edge[pred][node])
                                self.edge[new_name][node] = edge_obj
                    else:
                        _merge_node(pred)
            else:
                if node in to_rename:
                    new_name = to_rename[node]
                else:
                    new_name = node
                self.add_node(new_name)
                node_obj = copy.deepcopy(hierarchy.node[node])
                self.node[new_name] = node_obj
                visited.append(node)
                for suc in successors:
                    if suc in visited:
                        if suc in to_rename.keys():
                            new_suc_name = to_rename[suc]
                        else:
                            new_suc_name = suc
                        if (new_name, new_suc_name) not in self.edges():
                            self.add_edge(new_name, new_suc_name)
                            edge_obj = copy.deepcopy(hierarchy.edge[node][suc])
                            self.edge[new_name][new_suc_name] = edge_obj
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
                                hierarchy.edge[pred][node])
                            self.edge[new_pred_name][new_name] = edge_obj
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
            if attr in self.node[n1].attrs.keys():
                value = self.node[n1].attrs[attr]
                for n2 in hierarchy.nodes():
                    if attr in hierarchy.node[n2].attrs.keys():
                        if hierarchy.node[n2].attrs[attr] == value:
                            if n1 in to_merge.keys() or n2 in to_merge.values():
                                raise HierarchyError(
                                    "Cannot merge with the input hierarchy: "
                                    "matching of nodes by attr '%s' with value '%s'"
                                    " is ambiguous!" % (attr, value)
                                )
                            else:
                                if isinstance(self.node[n1], GraphNode) and\
                                   isinstance(hierarchy.node[n2], GraphNode):
                                    if equal(self.node[n1].graph, hierarchy.node[n2].graph):
                                        to_merge[n1] = n2
                                elif isinstance(self.node[n1], RuleNode) and\
                                        isinstance(hierarchy.node[n2], RuleNode):
                                    if self.node[n1].rule == hierarchy.node[n1].rule:
                                        to_merge[n1] = n2
            else:
                continue

        for n in hierarchy.nodes():
            if n not in to_merge.values() and n in self.nodes():
                to_rename[n] = self._generate_new_name(n)

        # Check consistency of the mappings to be merged
        for n1, n2 in self.edges():
            if n1 in to_merge.keys() and n2 in to_merge.keys():
                if (to_merge[n1], to_merge[n2]) in hierarchy.edges():
                    mapping = hierarchy.edge[to_merge[n1]][
                        to_merge[n2]].mapping.items()
                    for key, value in mapping:
                        if key in self.edge[n1][n2].mapping.keys():
                            if self.edge[n1][n2].maping[key] != value:
                                raise HierarchyError(
                                    "Cannot merge with the input hierarchy: typing of nodes"
                                    "in `%s->%s` does not coincide with present typing!" %
                                    (str(n1), str(n2))
                                )

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
                self.node[new_name].add_attrs(
                    hierarchy.node[node].attrs
                )
                # recursive_merge(self.node[new_name].attrs,
                # hierarchy.node[node].attrs)
                visited.append(node)

                successors = hierarchy.successors(node)
                predecessors = hierarchy.predecessors(node)

                for suc in successors:
                    if suc in visited:
                        if suc in to_merge.values():
                            original_suc = keys_by_value(to_merge, suc)
                            # merge edge mappings
                            mapping = hierarchy.edge[node][suc].mapping
                            for key, value in mapping.items():
                                self.edge[new_name][
                                    new_names[original_suc]].mapping[key] = value
                            # merge edge attrs
                            self.edge[new_name][new_names[original_suc]].add_attrs(
                                hierarchy.edge[node][suc].attrs
                            )
                        else:
                            if suc in to_rename.keys():
                                new_suc_name = to_rename[suc]
                            else:
                                new_suc_name = suc
                            if (new_name, new_suc_name) not in self.edges():
                                self.add_edge(new_name, new_suc_name)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edge[node][suc])
                                self.edge[new_name][new_suc_name] = edge_obj
                    else:
                        _merge_node(suc)

                for pred in predecessors:
                    if pred in visited:
                        if pred in to_merge.values():
                            original_pred = keys_by_value(to_merge, pred)[0]
                            # merge edge mappings
                            mapping = hierarchy.edge[pred][node].mapping
                            for key, value in mapping.items():
                                self.edge[new_names[original_pred]][
                                    new_name].mapping[key] = value
                            # merge edge attrs
                            self.edge[new_names[original_pred]][new_name].add_attrs(
                                hierarchy.edge[pred][node].attrs
                            )
                        else:
                            if pred in to_rename.keys():
                                new_pred_name = to_rename[pred]
                            else:
                                new_pred_name = pred
                            if (new_pred_name, new_name) not in self.edges():
                                self.add_edge(new_pred_name, new_name)
                                edge_obj = copy.deepcopy(
                                    hierarchy.edge[pred][node])
                                self.edge[new_pred_name][new_name] = edge_obj
                    else:
                        _merge_node(pred)
            else:
                if node in to_rename.keys():
                    new_name = to_rename[node]
                else:
                    new_name = node
                self.add_node(new_name)
                node_obj = copy.deepcopy(hierarchy.node[node])
                self.node[new_name] = node_obj
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
                            edge_obj = copy.deepcopy(hierarchy.edge[node][suc])
                            self.edge[new_name][new_suc_name] = edge_obj
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
                                hierarchy.edge[pred][node])
                            self.edge[new_pred_name][new_name] = edge_obj
                    else:
                        _merge_node(pred)

            return

        for node in hierarchy.nodes():
            _merge_node(node)

        return new_names

    def unique_graph_id(self, prefix):
        """Generate a new graph id."""
        if prefix not in self.nodes():
            return prefix
        i = 0
        while "{}_{}".format(prefix, i) in self.nodes():
            i += 1
        return "{}_{}".format(prefix, i)

    def duplicate_subgraph(self, nodes, suffix):
        new = {}
        for node in nodes:
            new_id = self.unique_graph_id(node + suffix)
            new[node] = new_id
            self.add_node(new_id)
            self.node[new_id] = copy.deepcopy(self.node[node])
        for (source, target) in self.edges():
            if source in nodes:
                if target in nodes:
                    self.add_edge(new[source], new[target])
                    self.edge[new[source]][new[target]] = copy.deepcopy(
                        self.edge[source][target])
                else:
                    self.add_edge(new[source], target)
                    self.edge[new[source]][target] = copy.deepcopy(
                        self.edge[source][target])
            elif target in nodes:
                self.add_edge(source, new[target])
                self.edge[source][new[target]] = copy.deepcopy(
                    self.edge[source][target])
        return new

    # # build new nuggets after rewriting of old one following rewriting of the
    # # action graph.
    # def create_valid_nuggets(self, old_nugget, new_nugget, updated_graphs):
    #     pattern = copy.deepcopy(self.node[old_nugget].graph)
    #     for node in pattern.nodes():
    #         pattern.node[node] = dict()
    #     pattern_typing = {"typing": {node: node for node in pattern.nodes()}}
    #     tmp_hie = Hierarchy(self.directed, GraphNode)
    #     # tmp_hie.add_graph("old", pattern)
    #     tmp_hie.add_graph("typing", self.node[old_nugget].graph)
    #     # tmp_hie.add_typing("old", "typing", pattern_typing)
    #     tmp_hie.add_graph("new", self.node[new_nugget].graph)
    #     tmp_hie.add_typing("new", "typing", updated_graphs[new_nugget][1])
    #     matchings = tmp_hie.find_matching2("new", pattern, pattern_typing)
    #     new_nuggets = []
    #     for matching in matchings:
    #         instance = copy.deepcopy(self.node[old_nugget].graph)
    #         for node in instance.nodes():
    #             attrs = merge_attributes(instance.node[node],
    #                                      self.node[new_nugget].graph.node[
    #                 matching[node]],
    #                 "intersection")
    #             # attrs = instance.node[node]
    #             # if attrs is None:
    #             #     continue
    #             # for (k, v) in attrs.items():
    #             #     nw_attrs = self.node[new_nugget].graph.node[matching[node]]
    #             #     print("image",matching[node], nw_attrs)
    #             #     print("ante",node, attrs)
    #             #     attrs[k] = v & nw_attrs[k]
    #         instance_id = self.unique_graph_id(old_nugget)
    #         self.add_graph(instance_id, instance, copy.deepcopy(
    #             self.node[old_nugget].attrs))
    #         for (_, typing) in self.out_edges(new_nugget):
    #             new_typing = self.edge[new_nugget][typing]
    #             instance_typing = compose(new_typing.mapping,
    #                                                     matching)
    #             # print("new_typing", instance_typing)
    #             # print("stating nodes",self.node[old_nugget].graph.nodes())
    #             # print("ending nodes", self.node[typing].graph.nodes())
    #             # print("typing_new_nugget",typing, new_typing.mapping)
    #             # print("new_nugget_nodes",
    #             # self.node[new_nugget].graph.nodes())
    #             self.add_typing(instance_id, typing, instance_typing,
    #                             total=new_typing.total,
    #                             attrs=new_typing.attrs)
    #         new_nuggets.append(instance_id)
    #     return new_nuggets

    def delete_all_children(self, graph_id):
        desc = self.descendents(graph_id)
        for node in desc:
            self.remove_node(node)


