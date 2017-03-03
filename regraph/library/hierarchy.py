"""."""
import itertools
import copy
import os
import json
import warnings

import networkx as nx
# import copy

from networkx.algorithms import isomorphism
from regraph.library.category_op import (compose_homomorphisms,
                                         check_homomorphism,
                                         is_total_homomorphism,
                                         get_unique_map,
                                         pullback,
                                         pullback_complement,
                                         pushout)
from regraph.library.primitives import (get_relabeled_graph,
                                        relabel_node,
                                        get_edge,
                                        graph_to_json,
                                        graph_from_json,
                                        equal)
from regraph.library.utils import (is_subdict,
                                   keys_by_value,
                                   normalize_attrs,
                                   to_set,
                                   normalize_typing,
                                   replace_source,
                                   replace_target)

from regraph.library.rules import Rule
from regraph.library.mu import parse_formula
from lrparsing import ParseError


class AttributeContainter(object):
    """Abstract class for a container with attributes."""

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
                    self.attrs.update({key: to_set(value)})
                else:
                    self.attrs[key] =\
                        self.attrs[key].union(to_set(value))
        return

    def remove_attrs(self, attrs):
        """Remove attributes."""
        normalize_attrs(self.attrs)
        for key, value in attrs.items():
            if key not in self.attrs.keys():
                pass
                # warnings.warn(
                #     "Node '%s' does not have attribute '%s'!" %
                #     (str(node), str(key)), RuntimeWarning)
            else:
                elements_to_remove = []
                for el in to_set(value):
                    if el in self.attrs[key]:
                        elements_to_remove.append(el)
                    else:
                        pass
                        # warnings.warn(
                        #     "Node '%s' does not have attribute '%s'"
                        #     " with value '%s'!" %
                        #     (str(node), str(key), str(el)), RuntimeWarning)
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


class Typing(AttributeContainter):
    """Incapsulate homomorphism in the edge of the hierarchy."""

    def __init__(self, mapping, total=False, ignore_attrs=False,
                 attrs=None):
        """Initialize homomorphism."""
        self.mapping = mapping
        self.ignore_attrs = ignore_attrs
        self.total = total
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def rename_source(self, old_name, new_name):
        replace_source(old_name, new_name, self.mapping)

    def rename_target(self, old_name, new_name):
        replace_target(old_name, new_name, self.mapping)


class RuleTyping(AttributeContainter):
    """Incapsulate rule typing in the edge of the hierarchy."""

    def __init__(self, lhs_mapping, rhs_mapping,
                 lhs_total=False, rhs_total=False,
                 ignore_attrs=False, attrs=None):
        """Initialize homomorphism."""
        self.lhs_mapping = lhs_mapping
        self.rhs_mapping = rhs_mapping
        self.ignore_attrs = ignore_attrs
        self.lhs_total = lhs_total
        self.rhs_total = rhs_total
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def rename_source(self, old_name, new_name):
        replace_source(old_name, new_name, self.lhs_mapping)
        replace_source(old_name, new_name, self.rhs_mapping)

    def rename_target(self, old_name, new_name):
        replace_target(old_name, new_name, self.lhs_mapping)
        replace_target(old_name, new_name, self.rhs_mapping)


class Hierarchy(nx.DiGraph):
    """Implements a hierarchy of graphs as a DAG."""

    def __init__(self, directed=True, graph_node_constuctor=GraphNode,
                 data=None):
        """Initialize an hierarchy of graphs."""
        nx.DiGraph.__init__(self, data)
        self.hierarchy_attrs = dict()
        self.directed = directed
        self.graph_node_constructor = graph_node_constuctor
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
                raise ValueError(
                    "Hierarchy error: unknown type '%s' of the node '%s'!" %
                    (type(self.node[n]), n)
                )
            res += " " + str(n) + " " +\
                str(self.node[n].attrs) + "\n"
        res += "\n"
        res += "Typing homomorphisms: \n"
        for n1, n2 in self.edges():
            if type(self.edge[n1][n2]) == Typing:
                res += "%s -> %s: total == %s, ignore_attrs == %s\n" %\
                    (
                        n1, n2, self.edge[n1][n2].total,
                        self.edge[n1][n2].ignore_attrs
                    )
                # res += "mapping: %s\n" % str(self.edge[n1][n2].mapping)
            elif type(self.edge[n1][n2]) == RuleTyping:
                res +=\
                    ("%s -> %s: lhs_total == %s, rhs_total == %s," +
                        " ignore_attrs == %s\n") %\
                    (
                        n1, n2, self.edge[n1][n2].lhs_total,
                        self.edge[n1][n2].rhs_total,
                        self.edge[n1][n2].ignore_attrs
                    )
                # res += "lhs mapping: %s\n" % str(self.edge[n1][n2].lhs_mapping)
                # res += "rhs mapping: %s\n" % str(self.edge[n1][n2].rhs_mapping)
            else:
                raise ValueError(
                    "Hierarchy error: unknown type '%s' of the edge '%s->%s'!" %
                    (type(self.edge[n1][n2]), n1, n2)
                )

        res += "\n"
        res += "attributes : \n"
        res += str(self.hierarchy_attrs)
        res += "\n"

        return res

    def __eq__(self, hierarchy):
        """Equality test."""
        g1 = self.to_nx_graph()
        g2 = hierarchy.to_nx_graph()
        if not equal(g1, g2):
            return False

        for node in self.nodes():
            normalize_attrs(self.node[node].attrs)
            normalize_attrs(hierarchy.node[node].attrs)
            if self.node[node].attrs != hierarchy.node[node].attrs:
                return False
            if isinstance(self.node[node], GraphNode) and\
               isinstance(hierarchy.node[node], GraphNode):
                if not equal(
                    self.node[node].graph,
                    hierarchy.node[node].graph
                ):
                    return False
            elif isinstance(self.node[node], RuleNode) and\
                    isinstance(hierarchy.node[node], RuleNode):
                if self.node[node].rule != hierarchy.node[node].rule:
                    return False
            else:
                return False

        for s, t in self.edges():
            normalize_attrs(self.edge[s][t].attrs)
            normalize_attrs(hierarchy.edge[s][t].attrs)
            if self.edge[s][t].attrs != hierarchy.edge[s][t].attrs:
                return False
            if isinstance(self.edge[s][t], Typing) and\
               isinstance(hierarchy.edge[s][t], Typing):
                if self.edge[s][t].mapping != hierarchy.edge[s][t].mapping:
                    return False
                if self.edge[s][t].ignore_attrs != hierarchy.edge[s][t].ignore_attrs:
                    return False
                if self.edge[s][t].total != hierarchy.edge[s][t].total:
                    return False
                normalize_attrs(self.edge[s][t].attrs)
                normalize_attrs(hierarchy.edge[s][t].attrs)
                if self.edge[s][t].attrs != hierarchy.edge[s][t].attrs:
                    return False
            elif isinstance(self.edge[s][t], RuleTyping) and\
                    isinstance(hierarchy.edge[s][t], RuleTyping):
                if self.edge[s][t].lhs_mapping != hierarchy.edge[s][t].lhs_mapping:
                    return False
                if self.edge[s][t].rhs_mapping != hierarchy.edge[s][t].rhs_mapping:
                    return False
                if self.edge[s][t].ignore_attrs != hierarchy.edge[s][t].ignore_attrs:
                    return False
                if self.edge[s][t].lhs_total != hierarchy.edge[s][t].lhs_total:
                    return False
                if self.edge[s][t].rhs_total != hierarchy.edge[s][t].rhs_total:
                    return False
                normalize_attrs(self.edge[s][t].attrs)
                normalize_attrs(hierarchy.edge[s][t].attrs)
                if self.edge[s][t].attrs != hierarchy.edge[s][t].attrs:
                    return False
            else:
                return False
        return True

    def add_graph(self, graph_id, graph, graph_attrs=None):
        """Add graph to the hierarchy."""
        if self.directed != graph.is_directed():
            if self.directed:
                raise ValueError(
                    "Hierarchy is defined for directed == %s graphs!" %
                    self.directed
                )
            else:
                raise ValueError("Hierarchy is defined for undirected graphs!")
        if graph_id in self.nodes():
            raise ValueError(
                "Node '%s' already exists in the hierarchy!" %
                graph_id
            )
        self.add_node(graph_id)
        self.node[graph_id] = self.graph_node_constructor(graph, graph_attrs)
        return

    def add_rule(self, rule_id, rule, rule_attrs=None):
        """Add rule to the hierarchy."""
        if self.directed != rule.lhs.is_directed():
            raise ValueError(
                "Hierarchy is defined for directed == %s graphs: " +
                "lhs of the rule is directed == %s!" %
                (self.directed, rule.lhs.is_directed())
            )
        if self.directed != rule.p.is_directed():
            raise ValueError(
                "Hierarchy is defined for directed == %s graphs: " +
                "p of the rule is directed == %s!" %
                (self.directed, rule.p.is_directed())
            )
        if self.directed != rule.rhs.is_directed():
            raise ValueError(
                "Hierarchy is defined for directed == %s graphs: " +
                "rhs of the rule is directed == %s!" %
                (self.directed, rule.rhs.is_directed())
            )
        if rule_id in self.nodes():
            raise ValueError(
                "Node '%s' already exists in the hierarchy!" %
                rule_id
            )
        self.add_node(rule_id)
        self.node[rule_id] = RuleNode(rule, rule_attrs)

    def compose_path_typing(self, path):
        """Compose homomorphisms along the path."""
        s = path[0]
        if isinstance(self.node[s], GraphNode):
            t = path[1]
            homomorphism = self.edge[s][t].mapping
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                homomorphism = compose_homomorphisms(
                    self.edge[s][t].mapping,
                    homomorphism
                )
            return homomorphism
        else:
            t = path[1]
            lhs_homomorphism = self.edge[s][t].lhs_mapping
            rhs_homomorphism = self.edge[s][t].rhs_mapping
            for i in range(2, len(path)):
                s = path[i - 1]
                t = path[i]
                lhs_homomorphism = compose_homomorphisms(
                    self.edge[s][t].mapping,
                    lhs_homomorphism
                )
                rhs_homomorphism = compose_homomorphisms(
                    self.edge[s][t].mapping,
                    rhs_homomorphism
                )
            return lhs_homomorphism, rhs_homomorphism

    def _path_from_rule(self, path):
        s = path[0]
        return isinstance(self.node[s], RuleNode)

    def _check_consistency(self, source, target, mapping):
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
                        raise ValueError(
                            "Found a rule typing some node in the hierarchy!"
                        )
                    new_lhs_h, new_rhs_h = self.compose_path_typing(paths_to_source[s])
                    new_lhs_h = compose_homomorphisms(mapping, new_lhs_h)
                    new_rhs_h = compose_homomorphisms(mapping, new_rhs_h)

                    if t != target:
                        new_lhs_h = compose_homomorphisms(
                            self.compose_path_typing(paths_from_target[t]),
                            new_lhs_h
                        )
                        new_rhs_h = compose_homomorphisms(
                            self.compose_path_typing(paths_from_target[t]),
                            new_rhs_h
                        )
                    try:
                        # find homomorphisms from s to t via other paths
                        s_t_paths = nx.all_shortest_paths(self, s, t)
                        for path in s_t_paths:
                            lhs_h, rhs_h = self.compose_path_typing(path)
                            for key, value in lhs_h.items():
                                if key in new_lhs_h.keys():
                                    if new_lhs_h[key] != value:
                                        raise ValueError(
                                            "Homomorphism does not commute with an existing " +
                                            "path from '%s' to '%s'!" % (s, t)
                                        )
                            for key, value in rhs_h.items():
                                if key in new_rhs_h.keys():
                                    if new_rhs_h[key] != value:
                                        raise ValueError(
                                            "Homomorphism does not commute with an existing " +
                                            "path from '%s' to '%s'!" % (s, t)
                                        )
                    except(nx.NetworkXNoPath):
                        pass
            else:
                for t in paths_from_target.keys():
                    # find homomorphism from s to t via new path
                    if s != source:
                        new_homomorphism = self.compose_path_typing(paths_to_source[s])
                    else:
                        new_homomorphism =\
                            dict([(key, key) for key, _ in mapping.items()])
                    new_homomorphism = compose_homomorphisms(mapping, new_homomorphism)
                    if t != target:
                        new_homomorphism = compose_homomorphisms(
                            self.compose_path_typing(paths_from_target[t]),
                            new_homomorphism
                        )

                    # find homomorphisms from s to t via other paths
                    s_t_paths = nx.all_shortest_paths(self, s, t)
                    try:
                        # check only the first path
                        for path in s_t_paths:
                            path_homomorphism = self.compose_path_typing(path)
                            for key, value in path_homomorphism.items():
                                if key in new_homomorphism.keys():
                                    if new_homomorphism[key] != value:
                                        raise ValueError(
                                            "Homomorphism does not commute with an existing " +
                                            "path from '%s' to '%s'!" % (s, t)
                                        )
                    except(nx.NetworkXNoPath):
                        pass

    def add_typing(self, source, target, mapping,
                   total=False, ignore_attrs=False, attrs=None):
        """Add homomorphism to the hierarchy."""
        if source not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % source)
        if target not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % target)

        if (source, target) in self.edges():
            raise ValueError(
                "Edge '%s->%s' already exists in the hierarchy: no muliple edges allowed!" %
                (source, target)
            )
        if not isinstance(self.node[source], GraphNode):
            if type(self.node[source]) == RuleNode:
                raise ValueError(
                    "Source node is a rule, use `add_rule_typing` method instead!"
                )
            else:
                raise ValueError(
                    "Source of a typing should be a graph, `%s` is provided!" %
                    type(self.node[source])
                )
        if not isinstance(self.node[target], GraphNode):
            raise ValueError(
                "Target of a typing should be a graph, `%s` is provided!" %
                type(self.node[target])
            )

        # check no cycles are produced
        self.add_edge(source, target)
        if not nx.is_directed_acyclic_graph(self):
            self.remove_edge(source, target)
            raise ValueError(
                "Edge '%s->%s' creates a cycle in the hierarchy!" %
                (source, target)
            )
        self.remove_edge(source, target)

        # check if the homomorphism is valid
        check_homomorphism(
            self.node[source].graph,
            self.node[target].graph,
            mapping,
            ignore_attrs,
            total=total
        )

        # check if newly created path commutes with existing shortest paths
        self._check_consistency(source, target, mapping)

        self.add_edge(source, target)
        self.edge[source][target] = Typing(mapping, total, ignore_attrs, attrs)
        return

    def add_partial_typing(self, source, target,
                           mapping, ignore_attrs=False, attrs=None):
        """Add partial homomorphism A -> B."""
        raise ValueError("Deprecated: use `add_typing` with parameter `total=False`!")

    def add_rule_typing(self, rule_id, graph_id, lhs_mapping, rhs_mapping,
                        lhs_total=False, rhs_total=False,
                        ignore_attrs=False, attrs=None):
        """Add typing of a rule."""
        if rule_id not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % rule_id)
        if graph_id not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % graph_id)

        if type(self.node[rule_id]) != RuleNode:
            raise ValueError(
                "Source of a rule typing should be a rule, `%s` is provided!" %
                type(self.node[rule_id])
            )
        if not isinstance(self.node[graph_id], GraphNode):
            raise ValueError(
                "Target of a rule typing should be a graph, `%s` is provided!" %
                type(self.node[graph_id])
            )
        # check if an lhs typing is valid
        check_homomorphism(
            self.node[rule_id].rule.lhs,
            self.node[graph_id].graph,
            lhs_mapping,
            ignore_attrs,
            total=lhs_total
        )
        # check if an rhs typing is valid
        check_homomorphism(
            self.node[rule_id].rule.rhs,
            self.node[graph_id].graph,
            rhs_mapping,
            ignore_attrs,
            total=rhs_total
        )
        self.add_edge(rule_id, graph_id)
        self.edge[rule_id][graph_id] = RuleTyping(
            lhs_mapping,
            rhs_mapping,
            lhs_total,
            rhs_total,
            ignore_attrs,
            attrs
        )
        return

    def remove_graph(self, graph_id, reconnect=False):
        """Remove graph from the hierarchy.

        If `reconnect`, map the children homomorphisms
        of this graph to its parents.
        """
        if graph_id not in self.nodes():
            raise ValueError(
                "Graph `%s` is not defined in the hierarchy!" % graph_id)

        if reconnect:
            out_graphs = self.successors(graph_id)
            in_graphs = self.predecessors(graph_id)

            for source in in_graphs:
                for target in out_graphs:
                    if type(self.edge[source][graph_id]) == RuleTyping:
                        lhs_mapping = compose_homomorphisms(
                            self.edge[graph_id][target].mapping,
                            self.edge[source][graph_id].lhs_mapping
                        )
                        rhs_mapping = compose_homomorphisms(
                            self.edge[graph_id][target].mapping,
                            self.edge[source][graph_id].rhs_mapping
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
                                self.edge[graph_id][target].rhs_total,
                                self.edge[source][graph_id].ignore_attrs or
                                self.edge[graph_id][target].ignore_attrs
                            )
                    else:
                        # compose two homomorphisms
                        mapping = compose_homomorphisms(
                            self.edge[graph_id][target].mapping,
                            self.edge[source][graph_id].mapping
                        )

                        if (source, target) not in self.edges():
                            self.add_typing(
                                source,
                                target,
                                mapping,
                                self.edge[source][graph_id].total and
                                self.edge[graph_id][target].total,
                                self.edge[source][graph_id].ignore_attrs or
                                self.edge[graph_id][target].ignore_attrs
                            )

        self.remove_node(graph_id)

    def node_type(self, graph_id, node_id):
        """Get a list of the immediate types of a node."""
        if graph_id not in self.nodes():
            raise ValueError(
                "Graph '%s' is not defined in the hierarchy!"
                % graph_id
            )
        if node_id not in self.node[graph_id].graph.nodes():
            raise ValueError(
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
            raise ValueError("Node `%s` does not exist!" % source)
        if (source, target) not in self.edges():
            raise ValueError("Typing `%s->%s` does not exist!" %
                             (source, target))
        nodes = self.node[source].graph.nodes()
        typing = self.edge[source][target]
        if is_total_homomorphism(nodes, typing.mapping):
            typing.total = True
        else:
            untyped_nodes = [
                node for node in nodes if node not in typing.mapping.keys()
            ]
            raise ValueError(
                "Cannot make `%s->%s` typing total: nodes [%s] "
                "do not have types, please type them first!" %
                (source, target, ", ".join(untyped_nodes))
            )
        return

    def add_node_type(self, graph_id, node_id, typing_graph, type_id):
        """Type a node in a graph."""
        if (graph_id, typing_graph) not in self.edges():
            raise ValueError(
                "Typing `%s->%s` does not exist!" %
                (graph_id, typing_graph)
            )

        old_mapping = self.edge[graph_id][typing_graph].mapping
        ignore_attrs = self.edge[graph_id][typing_graph].ignore_attrs
        attrs = self.edge[graph_id][typing_graph].attrs

        if node_id in old_mapping.keys():
            raise ValueError(
                "Node `%s` in `%s` is already typed by `%s` as `%s`" %
                (node_id, graph_id, typing_graph, old_mapping[node_id])
            )
        if type_id not in self.node[typing_graph].graph.nodes():
            raise ValueError(
                "Node `%s` does not exist in `%s`!" %
                (type_id, typing_graph)
            )

        new_mapping = copy.deepcopy(old_mapping)
        new_mapping[node_id] = type_id

        try:
            self._check_consistency(graph_id, typing_graph, new_mapping)

            self.remove_edge(graph_id, typing_graph)
            self.add_typing(
                graph_id,
                typing_graph,
                new_mapping,
                total=False,
                ignore_attrs=ignore_attrs,
                attrs=attrs
            )
        except(ValueError):
            raise ValueError(
                "Cannot add type `%s` to the node `%s` in `%s`: type "
                "is inconsistent with existing paths!" %
                (type_id, node_id, graph_id)
            )
        return

    def remove_node_type(self, graph_id, typing_graph, node_id):
        """Remove a type a node in a graph `graph_id`."""
        if (graph_id, typing_graph) not in self.edges():
            raise ValueError(
                "Typing `%s->%s` does not exist!" %
                (graph_id, typing_graph)
            )
        if self.edge[graph_id][typing_graph].total:
            warnings.warn(
                "Total typing '%s->%s' became partial!" %
                (graph_id, typing_graph)
            )
        return

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
            raise ValueError("Pattern matching in a rule is not implemented!")
        # Check that 'typing_graph' and 'pattern_typing' are correctly specified

        if len(self.successors(graph_id)) != 0:
            # if pattern_typing is None:
            #     raise ValueError(
            #         ("Graph '%s' has non-empty set of parents, " +
            #          "pattern should be typed by one of them!") %
            #           graph_id
            #     )
            # Check 'typing_graph' is in successors of 'graph_id'
            if pattern_typing is not None:
                for typing_graph, _ in pattern_typing.items():
                    if typing_graph not in self.successors(graph_id):
                        raise ValueError(
                            "Pattern typing graph '%s' is not in "
                            "the typing graphs of '%s'!" %
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
                            raise ValueError("Invalid pattern typing!")

                # Check pattern typing is a valid homomorphism
                for typing_graph, (mapping, ignore_attrs) in new_pattern_typing.items():
                    check_homomorphism(
                        pattern,
                        self.node[typing_graph].graph,
                        mapping,
                        ignore_attrs,
                        total=False
                    )
                pattern_typing = new_pattern_typing

        labels_mapping = dict(
            [(n, i + 1) for i, n in enumerate(self.node[graph_id].graph.nodes())])
        g = get_relabeled_graph(self.node[graph_id].graph, labels_mapping)

        inverse_mapping = dict(
            [(value, key) for key, value in labels_mapping.items()]
        )

        if pattern_typing:
            g_typing = dict([
                (typing_graph, dict([
                    (labels_mapping[k], v) for k, v in self.edge[graph_id][typing_graph].mapping.items()
                ])) for typing_graph in pattern_typing.keys()
            ])

        matching_nodes = set()

        # Find all the nodes matching the nodes in a pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if pattern_typing:
                    # check types match
                    match = False
                    for typing_graph, (typing, _) in pattern_typing.items():
                        if node in g_typing[typing_graph].keys() and pattern_node in typing.keys():
                            if g_typing[typing_graph][node] == typing[pattern_node]:
                                if is_subdict(pattern.node[pattern_node], g.node[node]):
                                    match = True
                            else:
                                # there is no mapping of this node in the typing by `typing_graph`
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
                        matching_obj = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
                        for isom in matching_obj.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))
                    else:
                        edge_induced_graph = nx.Graph(edgeset)
                        edge_induced_graph.add_nodes_from(
                            [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                        matching_obj = isomorphism.GraphMatcher(pattern, edge_induced_graph)
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
                    target_attrs = get_edge(subgraph, mapping[edge[0]], mapping[edge[1]])
                    if not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # Bring back original labeling

        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]

        return instances

    def find_rule_matching(self, graph_id, rule_id):
        """Find matching of a rule `rule_id` form the hierarchy."""
        if type(self.node[graph_id]) == RuleNode:
            raise ValueError("Pattern matching in a rule is not implemented!")

        if type(self.node[rule_id]) != RuleNode:
            raise ValueError("Invalid rule `%s` to match!" % rule_id)

        rule = self.node[rule_id].rule

        lhs_typing = {}
        rhs_typing = {}

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] =\
                self.edge[rule_id][suc].lhs_mapping
            rhs_typing[suc] =\
                self.edge[rule_id][suc].rhs_mapping

        instances = self.find_matching(
            graph_id,
            rule.lhs,
            lhs_typing
        )
        return instances

    def _check_instance(self, graph_id, pattern, instance, pattern_typing):
        check_homomorphism(
            pattern,
            self.node[graph_id].graph,
            instance,
            total=True
        )

        # check instance typing and lhs typing coincide
        for node in pattern.nodes():
            if pattern_typing:
                for typing_graph, (lhs_mapping, _) in pattern_typing.items():
                    if node in pattern_typing.keys() and\
                       instance[node] in self.edge[graph_id][typing_graph].mapping.keys():
                        if lhs_mapping[node] != self.edge[graph_id][typing_graph].mapping[instance[node]]:
                            raise ValueError(
                                "Typing of the instance of LHS does not " +
                                " coincide with typing of LHS!"
                            )
        return

    def get_complete_typing(self, graph_id, matching, lhs_t, rhs_t, rule):
        """Return complete typings of the rule.

        Typing is found according to the matching
        This ensures that you cannot remove node types when applying the
        rule with the complete typings.
        """
        new_lhs_t = normalize_typing(lhs_t)
        new_rhs_t = normalize_typing(rhs_t)
        return self._complete_typing(graph_id, matching, new_lhs_t, new_rhs_t,
                                     rule.p_lhs, rule.p_rhs)

    def _complete_typing(self, graph_id, matching,
                         lhs_typing, rhs_typing, p_l, p_r,
                         strong=False):

        for typing_graph in self.successors(graph_id):
            typing = self.edge[graph_id][typing_graph].mapping

            if typing_graph not in lhs_typing.keys():
                lhs_typing[typing_graph] = (dict(), False)
            if typing_graph not in rhs_typing.keys():
                rhs_typing[typing_graph] = (dict(), False)

            # Check that no types are redefined
            # forbidden case of * <- * -> A
            # works only if A <- A -> A
            for p_node in p_l.keys():
                l_node = p_l[p_node]
                r_node = p_r[p_node]
                if r_node in rhs_typing[typing_graph][0].keys() and\
                   l_node not in lhs_typing[typing_graph][0].keys():
                    if matching[l_node] not in typing.keys():
                        raise ValueError(
                            "Typing of the rule is not valid: "
                            "type of node `%s` in lhs is being redefined in the rhs!" %
                            l_node
                        )

            if strong:

                # Inherit lhs typing from the matching
                for (src, tgt) in matching.items():
                    if (src not in lhs_typing[typing_graph][0].keys() and
                            tgt in typing.keys()):
                        lhs_typing[typing_graph][0][src] = typing[tgt]

                for (p_node, l_node) in p_l.items():
                    # (print)
                    if l_node in lhs_typing[typing_graph][0].keys():
                        if p_r[p_node] in rhs_typing[typing_graph][0].keys():
                            if (rhs_typing[typing_graph][0][p_r[p_node]] !=
                                    lhs_typing[typing_graph][0][l_node]):
                                raise ValueError(
                                    "Typing of the rule is not valid: "
                                    "lhs node that maps to a node of type "
                                    "`%s` in the matching, is being mapped to `%s` in rhs!" %
                                    (lhs_typing[typing_graph][0][l_node],
                                     rhs_typing[typing_graph][0][p_r[p_node]])
                                )
                        else:
                            rhs_typing[typing_graph][0][p_r[p_node]] =\
                                lhs_typing[typing_graph][0][l_node]
            else:
                for p_node, r_node in p_r.items():
                    l_node = p_l[p_node]
                    if typing_graph in rhs_typing.keys() and\
                       r_node in rhs_typing[typing_graph][0].keys():
                        p_type = rhs_typing[typing_graph][0][r_node]
                        if typing_graph in lhs_typing.keys() and\
                           l_node in lhs_typing[typing_graph][0].keys():
                            l_type = lhs_typing[typing_graph][0][l_node]
                            if p_type != l_type:
                                raise ValueError(
                                    "Typing of the rule is not valid: "
                                    "lhs node that maps to a node of type "
                                    "`%s` in the matching, is being mapped to `%s` in rhs!" %
                                    (lhs_typing[typing_graph][0][l_node],
                                     rhs_typing[typing_graph][0][p_r[p_node]])
                                )
                        else:
                            if matching[l_node] in typing.keys():
                                l_type = typing[matching[l_node]]
                                if p_type != l_type:
                                    raise ValueError(
                                        "Typing of the rule is not valid: "
                                        "type of node `%s` in lhs is being redefined in the rhs!" %
                                        l_node
                                    )
        return

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

    def _propagate(self, graph_id, g_m, g_m_g, g_prime, g_m_g_prime):
        """Propagation steps: based on reverse BFS on neighbours."""
        updated_graphs = {
            graph_id: (g_m, g_m_g, g_prime, g_m_g_prime)
        }
        updated_homomorphisms = {}

        updated_rules = {}
        updated_rule_h = {}

        current_level = set(self.predecessors(graph_id))
        successors = dict([
            (n, [graph_id]) for n in current_level
        ])
        while len(current_level) > 0:
            next_level = set()
            for graph in current_level:
                paths_to_origin = nx.all_shortest_paths(self, graph, graph_id)
                paths_homomorphism = []
                for path in paths_to_origin:
                    paths_homomorphism.append(
                        self.compose_path_typing(path)
                    )
                if isinstance(self.node[graph], GraphNode):
                    origin_typing = {}
                    for node in self.node[graph].graph.nodes():
                        for hom in paths_homomorphism:
                            if node in hom.keys():
                                origin_typing[node] = hom[node]
                                break
                    g_m, g_m_g, g_m_origin_m = pullback(
                        self.node[graph].graph,
                        updated_graphs[graph_id][0],
                        self.node[graph_id].graph,
                        origin_typing,
                        updated_graphs[graph_id][1]
                    )
                    updated_graphs[graph] = (
                        g_m, g_m_g, None, None
                    )
                    # find homomorphisms g_m -> suc_m
                    for suc in successors[graph]:
                        g_m_suc_m = get_unique_map(
                            g_m,
                            self.node[graph].graph,
                            updated_graphs[suc][0],
                            self.node[suc].graph,
                            g_m_g,
                            self.edge[graph][suc].mapping,
                            updated_graphs[suc][1]
                        )
                        updated_homomorphisms[(graph, suc)] =\
                            (g_m_suc_m,
                             self.edge[graph][suc].ignore_attrs)

                elif type(self.node[graph]) == RuleNode:
                    rule = self.node[graph].rule

                    # propagation to lhs
                    lhs_origin_typing = {}
                    for node in rule.lhs.nodes():
                        for hom in paths_homomorphism:
                            if node in hom[0].keys():
                                lhs_origin_typing[node] = hom[0][node]
                                break
                    lhs_m, lhs_m_lhs, lhs_m_origin_m = pullback(
                        rule.lhs,
                        updated_graphs[graph_id][0],
                        self.node[graph_id].graph,
                        lhs_origin_typing,
                        updated_graphs[graph_id][1]
                    )

                    # propagation to p
                    p_origin_typing = {}
                    for node in rule.p.nodes():
                        for hom in paths_homomorphism:
                            if rule.p_lhs[node] in hom[0].keys():
                                p_origin_typing[node] =\
                                    hom[0][rule.p_lhs[node]]
                                break
                    p_m, p_m_p, p_m_origin_m = pullback(
                        rule.p,
                        updated_graphs[graph_id][0],
                        self.node[graph_id].graph,
                        p_origin_typing,
                        updated_graphs[graph_id][1]
                    )

                    # propagation to rhs
                    rhs_origin_typing = {}
                    for node in rule.rhs.nodes():
                        for hom in paths_homomorphism:
                            if node in hom[1].keys():
                                rhs_origin_typing[node] = hom[1][node]
                                break
                    rhs_m, rhs_m_rhs, rhs_m_origin_m = pullback(
                        rule.rhs,
                        updated_graphs[graph_id][0],
                        self.node[graph_id].graph,
                        rhs_origin_typing,
                        updated_graphs[graph_id][1]
                    )

                    # compose homomorphisms to get p_m -> lhs_m
                    new_p_lhs = get_unique_map(
                        p_m,
                        rule.p,
                        rule.lhs,
                        lhs_m,
                        p_m_p,
                        rule.p_lhs,
                        lhs_m_lhs
                    )

                    # compose homomorphisms to get p_m -> rhs_m
                    new_p_rhs = get_unique_map(
                        p_m,
                        rule.p,
                        rule.rhs,
                        rhs_m,
                        p_m_p,
                        rule.p_rhs,
                        rhs_m_rhs
                    )

                    new_rule = Rule(
                        p_m, lhs_m, rhs_m, new_p_lhs, new_p_rhs
                    )

                    updated_rules[graph] = new_rule

                    for suc in successors[graph]:
                        lhs_m_suc_m = get_unique_map(
                            lhs_m,
                            rule.lhs,
                            updated_graphs[suc][0],
                            self.node[suc].graph,
                            lhs_m_lhs,
                            self.edge[graph][suc].lhs_mapping,
                            updated_graphs[suc][1]
                        )

                        rhs_m_suc_m = get_unique_map(
                            rhs_m,
                            rule.rhs,
                            updated_graphs[suc][0],
                            self.node[suc].graph,
                            rhs_m_rhs,
                            self.edge[graph][suc].rhs_mapping,
                            updated_graphs[suc][1]
                        )

                        updated_rule_h[(graph, suc)] =\
                            (lhs_m_suc_m, rhs_m_suc_m)

                else:
                    raise ValueError(
                        "Rewriting error: unknown type '%s' of the node '%s'!" %
                        (type(self.node[graph]), graph)
                    )

                # update step
                next_level.update(self.predecessors(graph))
                for n in self.predecessors(graph):
                    if n in successors.keys():
                        successors[n].append(graph)
                    else:
                        successors[n] = [graph]
                del successors[graph]
            current_level = next_level
        return (
            updated_graphs,
            updated_homomorphisms,
            updated_rules,
            updated_rule_h
        )

    def _apply_changes(self, updated_graphs, updated_homomorphisms,
                       updated_rules, updated_rule_h):
        """Apply changes to the hierarchy."""
        for graph, (graph_m, _, graph_prime, _) in updated_graphs.items():
            if graph_prime is not None:
                self.node[graph].graph = graph_prime
            else:
                self.node[graph].graph = graph_m
        for (s, t), (mapping, ignore_attrs) in updated_homomorphisms.items():
            total = False

            if self.edge[s][t].total:
                if not is_total_homomorphism(self.node[s].graph.nodes(), mapping):
                    warnings.warn(
                        "Total typing '%s->%s' became partial after rewriting!" %
                        (s, t)
                    )
                else:
                    total = True

            self.edge[s][t] = Typing(
                mapping, total, ignore_attrs, self.edge[s][t].attrs
            )
        for rule, new_rule in updated_rules.items():
            self.node[rule] = RuleNode(
                new_rule, self.node[graph].attrs
            )
        for (s, t), (lhs_h, rhs_h) in updated_rule_h.items():
            self.edge[s][t] = RuleTyping(
                lhs_h, rhs_h,
                self.edge[s][t].ignore_attrs,
                self.edge[s][t].attrs
            )
        return

    def _normalize_typing(self, graph_id, rule, instance,
                          lhs_typing, rhs_typing, strong=False,
                          total=True):
        new_lhs_typing = normalize_typing(lhs_typing)
        new_rhs_typing = normalize_typing(rhs_typing)

        self._complete_typing(
            graph_id, instance, new_lhs_typing,
            new_rhs_typing, rule.p_lhs, rule.p_rhs,
            strong=strong
        )

        for typing_graph, (mapping, ignore_attrs) in new_lhs_typing.items():
            check_homomorphism(
                rule.lhs,
                self.node[typing_graph].graph,
                mapping,
                ignore_attrs,
                total=False
            )
        for typing_graph, (mapping, ignore_attrs) in new_rhs_typing.items():
            check_homomorphism(
                rule.rhs,
                self.node[typing_graph].graph,
                mapping,
                ignore_attrs,
                total=False
            )

        if total:
            # check that everything is typed
            for typing_graph in self.successors(graph_id):
                typing = self.edge[graph_id][typing_graph].mapping
                if typing_graph in new_rhs_typing.keys():
                    for node in rule.rhs.nodes():
                        p_nodes = keys_by_value(rule.p_rhs, node)
                        if len(p_nodes) == 1:
                            if instance[rule.p_lhs[p_nodes[0]]] not in typing.keys():
                                continue
                            elif node not in new_rhs_typing[typing_graph][0].keys():
                                raise ValueError(
                                    "Rewriting error: parameter `total` is set to True, "
                                    "typing of the node `%s` "
                                    "in rhs is required!" %
                                    node
                                )
                        elif len(p_nodes) > 1:
                            all_untyped = True
                            for p_node in p_nodes:
                                if instance[rule.p_lhs[p_node]] in typing.keys():
                                    all_untyped = False
                                    break
                            if all_untyped:
                                continue
                            elif node not in new_rhs_typing[typing_graph][0].keys():
                                raise ValueError(
                                    "Rewriting error: parameter `total` is set to True, "
                                    "typing of the node `%s` "
                                    "in rhs is required!" %
                                    node
                                )
                else:
                    raise ValueError(
                        "Rewriting error: parameter `total` is set to True, "
                        "typing of the node `%s` "
                        "in rhs is required!" %
                        node
                    )

        return new_lhs_typing, new_rhs_typing

    def rewrite(self, graph_id, rule, instance,
                lhs_typing=None, rhs_typing=None,
                strong_typing=True, total=True, recursive=False):
        """Rewrite and propagate the changes up."""
        if type(self.node[graph_id]) == RuleNode:
            raise ValueError("Rewriting of a rule is not implemented!")

        # Check consistency of the input parameters &
        # validity of homomorphisms

        new_lhs_typing, new_rhs_typing = self._normalize_typing(
            graph_id,
            rule,
            instance,
            lhs_typing,
            rhs_typing,
            strong=strong_typing,
            total=total
        )

        self._check_instance(
            graph_id, rule.lhs,
            instance, new_lhs_typing
        )

        # 1. Rewrite a graph `graph_id`
        g_m, p_g_m, g_m_g = pullback_complement(
            rule.p,
            rule.lhs,
            self.node[graph_id].graph,
            rule.p_lhs,
            instance
        )
        g_prime, g_m_g_prime, r_g_prime = pushout(
            rule.p,
            g_m,
            rule.rhs,
            p_g_m,
            rule.p_rhs
        )

        # Propagate rewriting up the hierarchy
        (updated_graphs,
         updated_homomorphisms,
         updated_rules,
         updated_rule_h) = self._propagate(graph_id,
                                           g_m,
                                           g_m_g,
                                           g_prime,
                                           g_m_g_prime)

        # Update typings of the graph_id
        for typing_graph in self.successors(graph_id):

            new_hom = copy.deepcopy(self.edge[graph_id][typing_graph].mapping)
            removed_nodes = set()
            new_nodes = dict()

            for node in rule.lhs.nodes():
                p_keys = keys_by_value(rule.p_lhs, node)
                # nodes that were removed
                if len(p_keys) == 0:
                    removed_nodes.add(instance[node])
                elif len(p_keys) == 1:
                    if typing_graph not in new_rhs_typing.keys() or\
                       rule.p_rhs[p_keys[0]] not in new_rhs_typing[typing_graph][0].keys():
                        if r_g_prime[rule.p_rhs[p_keys[0]]] in new_hom.keys():
                            removed_nodes.add(r_g_prime[rule.p_rhs[p_keys[0]]])
                # nodes were clonned
                elif len(p_keys) > 1:
                    for k in p_keys:
                        if typing_graph in new_rhs_typing.keys() and\
                           rule.p_rhs[k] in new_rhs_typing[typing_graph][0].keys():
                            new_nodes[r_g_prime[rule.p_rhs[k]]] =\
                                new_rhs_typing[typing_graph][0][rule.p_rhs[k]]
                        else:
                            removed_nodes.add(r_g_prime[rule.p_rhs[k]])

            for node in rule.rhs.nodes():
                p_keys = keys_by_value(rule.p_rhs, node)

                # nodes that were added
                if len(p_keys) == 0:
                    if typing_graph in new_rhs_typing.keys():
                        if node in new_rhs_typing[typing_graph][0].keys():
                            new_nodes[node] = new_rhs_typing[typing_graph][0][node]

                # nodes that were merged
                elif len(p_keys) > 1:
                    for k in p_keys:
                        removed_nodes.add(p_g_m[k])
                    # assign new type of node
                    if typing_graph in new_rhs_typing.keys():
                        if node in new_rhs_typing[typing_graph][0].keys():
                            new_type = new_rhs_typing[typing_graph][0][node]
                            new_nodes[r_g_prime[node]] = new_type

            # update homomorphisms
            for n in removed_nodes:
                if n in new_hom.keys():
                    del new_hom[n]

            ignore_attrs = False
            new_hom.update(new_nodes)
            if typing_graph in new_rhs_typing.keys():
                ignore_attrs = new_rhs_typing[typing_graph][1]

            updated_homomorphisms.update({
                (graph_id, typing_graph): (new_hom, ignore_attrs)
            })

        # Apply all the changes in the hierarchy

        self._apply_changes(updated_graphs,
                            updated_homomorphisms,
                            updated_rules,
                            updated_rule_h)

        return

    def apply_rule(self, graph_id, rule_id, instance,
                   strong_typing=True, total=False, recursive=False):
        """Apply rule from the hierarchy."""
        if type(self.node[graph_id]) == RuleNode:
            raise ValueError("Rewriting of a rule is not implemented!")

        if type(self.node[rule_id]) != RuleNode:
            raise ValueError("Invalid rewriting rule `%s`!" % rule_id)

        rule = self.node[rule_id].rule

        lhs_typing = dict()
        rhs_typing = dict()

        rule_successors = self.successors(rule_id)

        for suc in rule_successors:
            lhs_typing[suc] =\
                self.edge[rule_id][suc].lhs_mapping
            rhs_typing[suc] =\
                self.edge[rule_id][suc].rhs_mapping

        self.rewrite(
            graph_id,
            rule,
            instance,
            lhs_typing,
            rhs_typing
        )

        return

    def to_json(self):
        """Return json representation of the hierarchy."""
        json_data = {
            "rules": [],
            "graphs": [],
            "typing": [],
            "rule_typing": []
        }
        for node in self.nodes():
            if isinstance(self.node[node], RuleNode):
                json_data["rules"].append({
                    "id": node,
                    "rule": self.node[node].rule.to_json(),
                    "attrs": self.node[node].attrs
                })
            elif isinstance(self.node[node], GraphNode):
                json_data["graphs"].append({
                    "id": node,
                    "graph": graph_to_json(self.node[node].graph),
                    "attrs": self.node[node].attrs
                })
            else:
                raise ValueError("Unknown type of the node '%s'!" % node)
        for s, t in self.edges():
            if isinstance(self.edge[s][t], Typing):
                json_data["typing"].append({
                    "from": s,
                    "to": t,
                    "mapping": self.edge[s][t].mapping,
                    "total": self.edge[s][t].total,
                    "ignore_attrs": self.edge[s][t].ignore_attrs,
                    "attrs": self.edge[s][t].attrs
                })
            elif isinstance(self.edge[s][t], RuleTyping):
                json_data["rule_typing"].append({
                    "from": s,
                    "to": t,
                    "lhs_mapping": self.edge[s][t].lhs_mapping,
                    "rhs_mapping": self.edge[s][t].rhs_mapping,
                    "lhs_total": self.edge[s][t].lhs_total,
                    "rhs_total": self.edge[s][t].rhs_total,
                    "ignore_attrs": self.edge[s][t].ignore_attrs,
                    "attrs": self.edge[s][t].attrs
                })
            else:
                raise ValueError(
                    "Unknown type of the edge '%s->%s'!" % (s, t)
                )
        return json_data

    @classmethod
    def from_json(cls, json_data, directed=True):
        """Create hierarchy obj from json repr."""
        hierarchy = cls()

        # add graphs
        for graph_data in json_data["graphs"]:
            graph = graph_from_json(graph_data["graph"], directed)
            hierarchy.add_graph(
                graph_data["id"],
                graph,
                graph_data["attrs"]
            )

        # add rules
        for rule_data in json_data["rules"]:
            rule = Rule.from_json(rule_data["rule"])
            hierarchy.add_rule(
                rule_data["id"],
                rule,
                rule_data["attrs"]
            )

        # add typing
        for typing_data in json_data["typing"]:
            hierarchy.add_typing(
                typing_data["from"],
                typing_data["to"],
                typing_data["mapping"],
                typing_data["total"],
                typing_data["ignore_attrs"],
                typing_data["attrs"]
            )

        # add rule typing
        for rule_typing_data in json_data["rule_typing"]:
            hierarchy.add_rule_typing(
                rule_typing_data["from"],
                rule_typing_data["to"],
                rule_typing_data["lhs_mapping"],
                rule_typing_data["rhs_mapping"],
                rule_typing_data["lhs_total"],
                rule_typing_data["rhs_total"],
                rule_typing_data["ignore_attrs"],
                rule_typing_data["attrs"]
            )
        return hierarchy

    @classmethod
    def load(cls, filename, directed=True):
        """Load the hierarchy from a file."""
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                json_data = json.loads(f.read())
                hierarchy = Hierarchy.from_json(json_data, directed)
            return hierarchy
        else:
            raise ValueError("File '%s' does not exist!" % filename)

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
            if self.edge[child][graph_id].ignore_attrs is False:
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
        """Returns ancestors of a graph as well as the typing morphisms."""
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
            for (anc, typ) in typing_ancestors.items():
                if anc in ancestors.keys():
                    ancestors[anc].update(compose_homomorphisms(typ,
                                                                mapping))
                else:
                    ancestors[anc] = compose_homomorphisms(typ, mapping)
        return ancestors

    def to_nx_graph(self):
        g = nx.DiGraph()
        for node in self.nodes():
            g.add_node(node, self.node[node].attrs)
        for s, t in self.edges():
            g.add_edge(s, t, self.edge[s][t].attrs)
        return g

    def rename_graph(self, graph_id, new_graph_id):
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
        if new_name in self.node[graph_id].graph.nodes():
            raise ValueError("node {} already in graph {}"
                             .format(new_name, graph_id))
        if node not in self.node[graph_id].graph.nodes():
            raise ValueError("node {} not present in graph {}"
                             .format(node, graph_id))
        relabel_node(self.node[graph_id].graph, node, new_name)
        for (source, _) in self.in_edges(graph_id):
            self.edge[source][graph_id].rename_target(node, new_name)
        for (_, target) in self.out_edges(graph_id):
            self.edge[graph_id][target].rename_source(node, new_name)

    def descendents(self, graph_id):
        desc = {graph_id}
        for source, _ in self.in_edges(graph_id):
            desc |= self.descendents(source)
        return desc

    def get_typing(self, source, target):
        desc = self.descendents(target)
        if source not in desc:
            return None
        ancestors = self.get_ancestors(source, desc)
        return ancestors[target]

    def new_graph_from_nodes(self, nodes, graph_id, new_name, attrs):
        """Build a subgraph from nodes and type it by these nodes."""
        new_graph = self.node[graph_id].graph.subgraph(nodes)
        self.add_graph(new_name, new_graph, attrs)
        self.add_typing(new_name, graph_id, {n: n for n in nodes})

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
                                raise ValueError(
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
                                edge_obj = copy.deepcopy(hierarchy.edge[node][suc])
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
                                edge_obj = copy.deepcopy(hierarchy.edge[pred][node])
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
                            edge_obj = copy.deepcopy(hierarchy.edge[pred][node])
                            self.edge[new_pred_name][new_name] = edge_obj
                    else:
                        _merge_node(pred)
            return

        for node in hierarchy.nodes():
            _merge_node(node)

    def merge_by_attr(self, hierarchy, attr):
        to_merge = {}
        to_rename = {}
        for n1 in self.nodes():
            if attr in self.node[n1].attrs.keys():
                value = self.node[n1].attrs[attr]
                for n2 in hierarchy.nodes():
                    if attr in hierarchy.node[n2].attrs.keys():
                        if hierarchy.node[n2].attrs[attr] == value:
                            if n1 in to_merge.keys() or n2 in to_merge.values():
                                raise ValueError(
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
                    mapping = hierarchy.edge[to_merge[n1]][to_merge[n2]].mapping.items()
                    for key, value in mapping:
                        if key in self.edge[n1][n2].mapping.keys():
                            if self.edge[n1][n2].maping[key] != value:
                                raise ValueError(
                                    "Cannot merge with the input hierarchy: typing of nodes"
                                    "in `%s->%s` does not coincide with present typing!" %
                                    (str(n1), str(n2))
                                )

        visited = []
        new_names = {}

        # aux recursive function for merging by ids
        def _merge_node(node):
            print("Merging, ", node)
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
                                self.edge[new_name][new_names[original_suc]].mapping[key] = value
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
                                edge_obj = copy.deepcopy(hierarchy.edge[node][suc])
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
                                self.edge[new_names[original_pred]][new_name].mapping[key] = value
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
                                edge_obj = copy.deepcopy(hierarchy.edge[pred][node])
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
                            new_suc_name = new_names[original_node]
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
                            edge_obj = copy.deepcopy(hierarchy.edge[pred][node])
                            self.edge[new_pred_name][new_name] = edge_obj
                    else:
                        _merge_node(pred)

            return

        for node in hierarchy.nodes():
            _merge_node(node)

        return


def _verify(phi_str, current_typing, graph):
    phi = parse_formula(phi_str)
    const_names = phi.constants()
    constants = {const_name: (lambda n, const_name=const_name:
                              (str(current_typing[n]).lower() ==
                               const_name.lower()))
                 for const_name in const_names}
    relations = {
        "Adj": graph.__getitem__,
        "Suc": graph.successors,
        "Pre": graph.predecessors}

    res = phi.evaluate(graph.nodes(), relations, constants)
    return [n for (n, v) in res.items() if not v]


class MuHierarchy(Hierarchy):
    """Hierarchy with mu-calculus verification methods.

    Extends the hierarchy class with mu-calculus functionality.
    """

    def check(self, graph_id, parent_id, typing):
        """ check every formulae on given ancestor """
        if "formulae" in self.node[parent_id].attrs.keys():
            current_rep = {}
            for phi_str in self.node[parent_id].attrs["formulae"]:
                try:
                    failed_nodes = _verify(phi_str["formula"],
                                           typing,
                                           self.node[graph_id].graph)
                    current_rep[phi_str["id"]] = str(failed_nodes)
                except (ValueError, ParseError) as err:
                    current_rep[phi_str["id"]] = str(err)
            return current_rep

    def check_all_ancestors(self, graph_id):
        """check every formulae on every ancestors"""
        response = {}
        for (ancestor, mapping) in self.get_ancestors(graph_id).items():
            response[ancestor] = self.check(graph_id, ancestor, mapping)
        return response
