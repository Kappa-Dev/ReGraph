"""."""
import itertools
import copy
import os
import json
import warnings

import networkx as nx
# import copy

from networkx.algorithms import isomorphism
from regraph.library.category_op import (pullback,
                                         pullback_complement,
                                         pushout,
                                         nary_pullback)
from regraph.library.primitives import (get_relabeled_graph,
                                        get_edge,
                                        add_node,
                                        add_edge,
                                        graph_to_json,
                                        graph_from_json,
                                        print_graph)
from regraph.library.utils import (compose_homomorphisms,
                                   check_homomorphism,
                                   is_subdict,
                                   keys_by_value,
                                   normalize_attrs,
                                   to_set,
                                   is_total_homomorphism)
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
                        #     "Node '%s' does not have attribute '%s' with value '%s'!" %
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


class Hierarchy(nx.DiGraph):
    """Implements a hierarchy of graphs as a DAG."""

    def __init__(self, directed=True, graph_node_constuctor=GraphNode):
        """Initialize an hierarchy of graphs."""
        nx.DiGraph.__init__(self)
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
                    (n1, n2, self.edge[n1][n2].total, self.edge[n1][n2].ignore_attrs)
                # res += "mapping: %s\n" % str(self.edge[n1][n2].mapping)
            elif type(self.edge[n1][n2]) == RuleTyping:
                res += "%s -> %s: lhs_total == %s, rhs_total == %s, ignore_attrs == %s\n" %\
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

    def apply_rule(self, rule_id, graph_id, instance):
        """Apply rule from the hierarchy."""
        pass

    def rewrite(self, graph_id, rule, instance,
                lhs_typing=None, rhs_typing=None):
        """Rewrite and propagate the changes up."""

        if type(self.node[graph_id]) == RuleNode:
            raise ValueError("Rewriting of a rule is not implemented!")

        # 0. Check consistency of the input parameters &
        # validity of homomorphisms

        if lhs_typing is None:
            lhs_typing = dict()
        if rhs_typing is None:
            rhs_typing = dict()

        new_lhs_typing = dict()
        for key, value in lhs_typing.items():
            if type(value) == dict:
                new_lhs_typing[key] = (value, False)
            else:
                try:
                    if len(value) == 2:
                        new_lhs_typing[key] = value
                    elif len(value) == 1:
                        new_lhs_typing[key] = (value[0], False)
                except:
                    raise ValueError("Invalid lhs typing!")

        for typing_graph, (mapping, ignore_attrs) in new_lhs_typing.items():
            check_homomorphism(
                rule.lhs,
                self.node[typing_graph].graph,
                mapping,
                ignore_attrs,
                total=False
            )
        lhs_typing = new_lhs_typing

        new_rhs_typing = dict()
        for key, value in rhs_typing.items():
            if type(value) == dict:
                new_rhs_typing[key] = (value, False)
            else:
                try:
                    if len(value) == 2:
                        new_rhs_typing[key] = value
                    elif len(value) == 1:
                        new_rhs_typing[key] = (value[0], False)
                except:
                    raise ValueError("Invalid lhs typing!")
        for typing_graph, (mapping, ignore_attrs) in new_rhs_typing.items():
            check_homomorphism(
                rule.rhs,
                self.node[typing_graph].graph,
                mapping,
                ignore_attrs,
                total=False
            )
        rhs_typing = new_rhs_typing

        check_homomorphism(
            rule.lhs,
            self.node[graph_id].graph,
            instance,
            total=True
        )

        # check instance typing and lhs typing coincide
        for node in rule.lhs.nodes():
            if lhs_typing:
                for typing_graph, (lhs_mapping, _) in lhs_typing.items():
                    if node in lhs_typing.keys() and\
                       instance[node] in self.edge[graph_id][typing_graph].mapping.keys():
                        if lhs_mapping[node] != self.edge[graph_id][typing_graph].mapping[instance[node]]:
                            raise ValueError(
                                "Typing of the instance of LHS does not " +
                                " coincide with typing of LHS!"
                            )

        # 1. Rewriting steps
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

        # set g_prime for the 'graph_id' node
        updated_graphs = {
            graph_id: (g_m, g_m_g, g_prime, g_m_g_prime)
        }

        updated_homomorphisms = {}

        # Update typings of the graph
        for typing_graph in self.successors(graph_id):

            new_hom = copy.deepcopy(self.edge[graph_id][typing_graph].mapping)
            removed_nodes = set()
            new_nodes = dict()

            for node in rule.lhs.nodes():
                p_keys = keys_by_value(rule.p_lhs, node)
                # nodes that were removed
                if len(p_keys) == 0:
                    removed_nodes.add(instance[node])
                # nodes were clonned
                elif len(p_keys) > 1:
                    if instance[node] in self.edge[graph_id][typing_graph].mapping.keys():
                        for k in p_keys:
                            new_nodes[p_g_m[k]] =\
                                self.edge[graph_id][typing_graph].mapping[instance[node]]

            for node in rule.rhs.nodes():
                p_keys = keys_by_value(rule.p_rhs, node)

                # nodes that were added
                if len(p_keys) == 0:
                    if typing_graph in rhs_typing.keys():
                        if node in rhs_typing[typing_graph][0].keys():
                            new_nodes[node] = rhs_typing[typing_graph][0][node]

                # nodes that were merged
                elif len(p_keys) > 1:
                    for k in p_keys:
                        removed_nodes.add(p_g_m[k])
                    # try to assign new type of node
                    if typing_graph in rhs_typing.keys():
                        if node in rhs_typing[typing_graph][0].keys():
                            new_type = rhs_typing[typing_graph][0][node]
                            type_set = set()
                            for k in p_keys:
                                old_typing =\
                                    self.edge[graph_id][typing_graph].mapping
                                if p_g_m[k] in old_typing.keys():
                                    t = old_typing[p_g_m[k]]
                                    type_set.add(t)
                            # 1. merged nodes had different typed (ERROR)
                            if len(type_set) > 1:
                                raise ValueError(
                                    ("Cannot assign type '%s' for merged nodes:" +
                                     " [%s], nodes have different types!") %
                                    (
                                        new_type,
                                        ", ".join([p_g_m[p] for p in p_keys])
                                    )
                                )
                            # 2. merged nodes were of the same type or some of
                            # them were not typed at all (OK)
                            # then our `type_set` will be a singleton
                            else:
                                if len(type_set) == 1 and list(type_set)[0] == new_type:
                                    new_nodes[node] = new_type
                                else:
                                    raise ValueError(
                                        "Invalid type '%s' of merged nodes: [%s] !" %
                                        (
                                            new_type,
                                            ", ".join([p_g_m[p] for p in p_keys])
                                        )
                                    )

            # update homomorphisms
            for n in removed_nodes:
                if n in new_hom.keys():
                    del new_hom[n]

            ignore_attrs = False
            new_hom.update(new_nodes)
            if typing_graph in rhs_typing.keys():
                ignore_attrs = rhs_typing[typing_graph][1]

            updated_homomorphisms.update({
                (graph_id, typing_graph): (new_hom, ignore_attrs)
            })

        # 2. Propagation steps reverse BFS on neighbours
        current_level = set(self.predecessors(graph_id))
        successors = dict([
            (n, [graph_id]) for n in current_level
        ])

        while len(current_level) > 0:
            next_level = set()
            for graph in current_level:
                # print("gonna propagate here: %s", graph)
                # print(successors)
                # make changes to the graph
                if len(successors[graph]) == 1:
                    # simple case
                    suc = successors[graph][0]
                    if isinstance(self.node[graph], GraphNode):
                        if suc in updated_graphs.keys():
                            # find pullback
                            graph_m, graph_m_graph, graph_m_suc_m =\
                                pullback(
                                    self.node[graph].graph,
                                    updated_graphs[suc][0],
                                    self.node[suc].graph,
                                    self.edge[graph][suc].mapping,
                                    updated_graphs[suc][1]
                                )
                            updated_graphs.update({
                                graph: (graph_m, graph_m_graph, None, None)
                            })
                            updated_homomorphisms.update({
                                (graph, suc): (
                                    graph_m_suc_m,
                                    self.edge[graph][suc].ignore_attrs
                                )
                            })
                    elif type(self.node[graph]) == RuleNode:
                        # propagation to lhs
                        lhs_m, lhs_m_lhs, lhs_m_suc_m =\
                            pullback(
                                self.node[graph].rule.lhs,
                                updated_graphs[suc][0],
                                self.node[suc].graph,
                                self.edge[graph][suc].lhs_mapping,
                                updated_graphs[suc][1]
                            )
                        # propagation to p
                        p_mapping = {}
                        for node in self.node[graph].rule.p.nodes():
                            p_mapping[node] =\
                                self.edge[graph][suc].lhs_mapping[self.node[graph].rule.p_lhs[node]]
                        p_m, p_m_p, _ =\
                            pullback(
                                self.node[graph].rule.p,
                                updated_graphs[suc][0],
                                self.node[suc].graph,
                                p_mapping,
                                updated_graphs[suc][1]
                            )
                        # propagation to rhs
                        rhs_m, rhs_m_rhs, rhs_m_suc_m =\
                            pullback(
                                self.node[graph].rule.rhs,
                                updated_graphs[suc][0],
                                self.node[suc].graph,
                                self.edge[graph][suc].rhs_mapping,
                                updated_graphs[suc][1]
                            )
                        # compose homomorphisms to get p_m -> lhs_m
                        new_p_lhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_lhs[p_m_keys[0]] = lhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_lhs[p_m_key] = lhs_m_keys[i]

                        # compose homomorphisms to get p_m -> rhs_m
                        new_p_rhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_rhs[p_m_keys[0]] = rhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_rhs[p_m_key] = rhs_m_keys[i]

                        # nothing is typed by rule -- the changes can be applied right away
                        new_rule = Rule(
                            p_m, lhs_m, rhs_m, new_p_lhs, new_p_rhs
                        )
                        self.node[graph] = RuleNode(
                            new_rule, self.node[graph].attrs
                        )
                        self.edge[graph][suc] = RuleTyping(
                            lhs_m_suc_m, rhs_m_suc_m,
                            self.edge[graph][suc].ignore_attrs,
                            self.edge[graph][suc].attrs
                        )
                    else:
                        raise ValueError(
                            "Rewriting error: unknown type '%s' of the node '%s'!" %
                            (type(self.node[graph]), graph)
                        )
                else:
                    # complicated case
                    if isinstance(self.node[graph], GraphNode):
                        cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         self.edge[graph][suc].mapping,
                                         updated_graphs[suc][1])
                                })
                        graph_m, graph_m_graph, graph_m_sucs_m =\
                            nary_pullback(self.node[graph].graph, cospans)
                        # apply changes to the hierarchy
                        updated_graphs.update({
                            graph: (graph_m, graph_m_graph, None, None)
                        })
                        for suc, graph_m_suc in graph_m_sucs_m.items():
                            updated_homomorphisms.update({
                                (graph, suc): (
                                    graph_m_suc,
                                    self.edge[graph][suc].ignore_attrs
                                )
                            })
                    elif type(self.node[graph]) == RuleNode:
                        # propagation to lhs
                        lhs_cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                lhs_cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         self.edge[graph][suc].lhs_mapping,
                                         updated_graphs[suc][1])
                                })
                        lhs_m, lhs_m_lhs, lhs_m_sucs_m =\
                            nary_pullback(self.node[graph].rule.lhs, lhs_cospans)
                        # propagation to p

                        p_cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                p_mapping = {}
                                for node in self.node[graph].rule.p.nodes():
                                    p_mapping[node] =\
                                        self.edge[graph][suc].lhs_mapping[self.node[graph].rule.p_lhs[node]]
                                p_cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         p_mapping,
                                         updated_graphs[suc][1])
                                })
                        p_m, p_m_p, p_m_sucs_m =\
                            nary_pullback(self.node[graph].rule.p, p_cospans)
                        # propagation to rhs
                        rhs_cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                rhs_cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         self.edge[graph][suc].rhs_mapping,
                                         updated_graphs[suc][1])
                                })
                        rhs_m, rhs_m_rhs, rhs_m_sucs_m =\
                            nary_pullback(self.node[graph].rule.rhs, rhs_cospans)
                        # compose homomorphisms to get p_m -> lhs_m
                        new_p_lhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_lhs[p_m_keys[0]] = lhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_lhs[p_m_key] = lhs_m_keys[i]

                        # compose homomorphisms to get p_m -> rhs_m
                        new_p_rhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_rhs[p_m_keys[0]] = rhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_rhs[p_m_key] = rhs_m_keys[i]

                        # nothing is typed by rule -- the changes can be applied right away
                        new_rule = Rule(
                            p_m, lhs_m, rhs_m, new_p_lhs, new_p_rhs
                        )
                        self.node[graph] = RuleNode(
                            new_rule, self.node[graph].attrs
                        )
                        for suc in successors[graph]:
                            self.edge[graph][suc] = RuleTyping(
                                lhs_m_sucs_m[suc], rhs_m_sucs_m[suc],
                                self.edge[graph][suc].ignore_attrs,
                                self.edge[graph][suc].attrs
                            )
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

        # 3. Apply changes to the hierarchy
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
        return

    def to_json(self):
        """Return json representation of the hierarchy."""
        json_data = {"graphs": [], "typing": []}
        for node in self.nodes():
            json_data["graphs"].append({
                "id": node,
                "graph": graph_to_json(self.node[node].graph),
                "attrs": self.node[node].attrs
            })
        for s, t in self.edges():
            json_data["typing"].append({
                "from": s,
                "to": t,
                "mapping": self.edge[s][t].mapping,
                "ignore_attrs": self.edge[s][t].ignore_attrs,
                "attrs": self.edge[s][t].attrs
            })
        return json_data

    def load(self, filename):
        """Load the hierarchy from a file."""
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                json_data = json.loads(f.read())

                # add graphs
                for graph_data in json_data["graphs"]:
                    graph = graph_from_json(graph_data["graph"], self.directed)
                    self.add_graph(graph_data["id"], graph, graph_data["attrs"])

                # add typing
                for typing_data in json_data["typing"]:
                    self.add_typing(
                        typing_data["from"],
                        typing_data["to"],
                        typing_data["mapping"],
                        typing_data["ignore_attrs"],
                        typing_data["attrs"]
                    )
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

    def get_ancestors(self, graph_id):
        """Returns ancestors of a graph as well as the typing morphisms."""
        def _get_ancestors_aux(known_ancestors, graph_id):
            ancestors = {}
            for _, typing in self.out_edges(graph_id):
                if typing not in known_ancestors:
                    mapping = self.edge[graph_id][typing].mapping
                    typing_ancestors = _get_ancestors_aux(known_ancestors, typing)
                    ancestors[typing] = mapping
                    for (anc, typ) in typing_ancestors.items():
                        ancestors[anc] = compose_homomorphisms(typ, mapping)
                        known_ancestors.append(anc)
            return ancestors
        return _get_ancestors_aux([], graph_id)

    def to_nx_graph(self):
        g = nx.DiGraph()
        for node in self.nodes():
            g.add_node(node, self.node[node].attrs)
        for s, t in self.edges():
            g.add_edge(s, t, self.edge[s][t].attrs)
        return g


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
