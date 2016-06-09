"""."""
import networkx as nx
from networkx.algorithms import isomorphism

import itertools

from regraph.library.parser import parser
from regraph.library.primitives import (merge_nodes,
                                        clone_node,
                                        add_node,
                                        remove_node,
                                        add_edge,
                                        remove_edge,
                                        remove_node_attrs,
                                        add_node_attrs,
                                        remove_edge_attrs,
                                        add_edge_attrs,
                                        update_edge_attrs,
                                        update_node_attrs)
from regraph.library.utils import is_subdict
from regraph.library.data_structures import (Homomorphism)


class Rewriter:
    """Class implements the transformation on the graph."""

    def __init__(self, graph):
        """Initialize Rewriter object with input graph."""
        self.graph_ = graph
        self.parser_ = parser
        return

    def find_matching(self, pattern):
        """Perform matching of the pattern graph."""
        # NetworkX isomorphism lib crushes if the ids of nodes
        # have different types (e.g ints and strings).
        # For the sake of security we will temporarily make
        # all the nodes ids to be int
        labels_mapping = dict([(n, i + 1) for i, n in enumerate(self.graph_.nodes())])
        g = self.graph_.relabel_nodes(labels_mapping)
        matching_nodes = set()
        # find all the nodes matching the nodes in pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if pattern.node[pattern_node].type_ == g.node[node].type_:
                    if is_subdict(pattern.node[pattern_node].attrs_,
                                  g.node[node].attrs_):
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
                        GM = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
                        for isom in GM.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))
                    else:
                        edge_induced_graph = nx.Graph(edgeset)
                        edge_induced_graph.add_nodes_from(
                            [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                        GM = isomorphism.GraphMatcher(pattern, edge_induced_graph)
                        for isom in GM.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))
        for subgraph, mapping in isomorphic_subgraphs:
            # check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if not pattern.node[pattern_node].type_ == subgraph.node[node].type_:
                    break
                if not is_subdict(pattern.node[pattern_node].attrs_, subgraph.node[node].attrs_):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.get_edge(edge[0], edge[1])
                    target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
                    if not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # bring back original labeling
        inverse_mapping = dict([(value, key) for key, value in labels_mapping.items()])
        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]
        return instances

    def clone(self, instance, node, name=None):
        if node in instance.keys():
            new_name = clone_node(self.graph_, instance[node], name)
        else:
            new_name = clone_node(self.graph_, node, name)
        return new_name

    def merge(self, instance, nodes, method=None,
              node_name=None, edges_method=None):
        nodes_to_merge =\
            [instance[n] if n in instance.keys() else n
             for n in nodes]
        new_name = merge_nodes(
            self.graph_,
            nodes_to_merge,
            method,
            node_name)
        return new_name

    def add_node(self, instance, node_type, name=None, attrs={}):
        new_name = add_node(self.graph_, node_type, name, attrs)
        return new_name

    def delete_node(self, instance, node):
        if node in instance.keys():
            remove_node(self.graph_, instance[node])
        else:
            remove_node(self.graph_, node)
        return

    def add_edge(self, instance, node_1, node_2, attrs={}):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        add_edge(self.graph_, source, target, attrs)
        return

    def delete_edge(self, instance, node_1, node_2):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        remove_edge(self.graph_, source, target)

    def delete_node_attrs(self, instance, node, attrs_dict):
        if node in instance.keys():
            remove_node_attrs(self.graph_, instance[node], attrs_dict)
        else:
            remove_node_attrs(self.graph_, node, attrs_dict)

    def delete_edge_attrs(self, instance, node_1, node_2, attrs_dict):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        remove_edge_attrs(self.graph_, source, target, attrs_dict)

    def add_node_attrs(self, instance, node, attrs_dict):
        if node in instance.keys():
            add_node_attrs(self.graph_, instance[node], attrs_dict)
        else:
            add_node_attrs(self.graph_, node, attrs_dict)

    def add_edge_attrs(self, instance, node_1, node_2, attrs_dict):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        add_edge_attrs(self.graph_, source, target, attrs_dict)

    def update_node_attrs(self, instance, node, new_attrs):
        if node in instance.keys():
            update_node_attrs(self.graph_, instance[node], new_attrs)
        else:
            update_node_attrs(self.graph_, node, new_attrs)

    def update_edge_attrs(self, instance, node_1, node_2, new_attrs):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        update_edge_attrs(self.graph_, source, target, new_attrs)

    def transform_instance(self, instance, commands):
        """Transform the instance of LHS of the rule in the graph."""
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        for command in command_strings:
            try:
                parsed = parser.parseString(command).asDict()
                if parsed["keyword"] == "clone":
                    node_name = None
                    if "node_name" in parsed.keys():
                        node_name = parsed["node_name"]
                    self.clone(instance, parsed["node"], node_name)
                elif parsed["keyword"] == "merge":
                    method = None
                    node_name = None
                    edges_method = None
                    if "method" in parsed.keys():
                        method = parsed["method"]
                    if "node_name" in parsed.keys():
                        node_name = parsed["node_name"]
                    if "edges_method" in parsed.keys():
                        edges_method = parsed["edges_method"]
                    self.merge(
                        instance,
                        parsed["nodes"],
                        method,
                        node_name,
                        edges_method)
                elif parsed["keyword"] == "add_node":
                    name = None
                    node_type = None
                    attrs = {}
                    if "node" in parsed.keys():
                        name = parsed["node"]
                    if "type" in parsed.keys():
                        node_type = parsed["type"]
                    if "attrubutes" in parsed.keys():
                        attrs = parsed["attrubutes"]
                    self.add_node(node_type, name, attrs)
                elif parsed["keyword"] == "delete_node":
                    self.delete_node(instance, parsed["node"])
                elif parsed["keyword"] == "add_edge":
                    attrs = {}
                    if "attrubutes" in parsed.keys():
                        attrs = parsed["attrubutes"]
                    self.add_edge(instance, parsed["node_1"], parsed["node_2"], attrs)
                elif parsed["keyword"] == "delete_edge":
                    self.delete_edge(instance, parsed["node_1"], parsed["node_2"])
                elif parsed["keyword"] == "add_node_attrs":
                    self.add_node_attrs(
                        parsed["node"],
                        parsed["attrubutes"])
                elif parsed["keyword"] == "add_edge_attrs":
                    self.add_edge_attrs(
                        parsed["node_1"],
                        parsed["node_2"],
                        parsed["attrubutes"])
                elif parsed["keyword"] == "delete_node_attrs":
                    self.delete_node_attrs(
                        parsed["node"],
                        parsed["attrubutes"])
                elif parsed["keyword"] == "delete_edge_attrs":
                    self.delete_edge_attrs(
                        parsed["node_1"],
                        parsed["node_2"],
                        parsed["attrubutes"])
                elif parsed["keyword"] == "update_node_attrs":
                    self.update_node_attrs(
                        parsed["node"],
                        parsed["attrubutes"])
                elif parsed["keyword"] == "update_edge_attrs":
                    self.update_edge_attrs(
                        parsed["node_1"],
                        parsed["node_2"],
                        parsed["attrubutes"])
                else:
                    raise ValueError("Unknown command")
            except:
                raise ValueError("Cannot parse command '%s'" % command)

    def apply_rule(self, instance, left_h, right_h):

        # check left_h.source == right_h.source
        if left_h.source_.nodes() != right_h.source_.nodes():
            raise ValueError("Preserving part does not match!")
        if left_h.source_.edges() != right_h.source_.edges():
            raise ValueError("Preserving part does not match!")

        RHS_instance =\
            dict([(r, instance[left_h.mapping_[p]]) for p, r in right_h.mapping_.items()])
        P_instance =\
            dict([(p, instance[l]) for p, l in left_h.mapping_.items()])

        (nodes_to_remove,
         edges_to_remove,
         node_attrs_to_remove,
         edge_attrs_to_remove) = left_h.find_final_PBC()

        (nodes_to_add,
         edges_to_add,
         node_attrs_to_add,
         edge_attrs_to_add) = right_h.find_PO()

        # 1) Delete nodes/edges
        for node in nodes_to_remove:
            self.delete_node(instance, node)

        merge_dict = {}
        for n in right_h.target_.nodes():
            merge_dict.update({n: []})
        for p_node, r_node in right_h.mapping_.items():
            if left_h.mapping_[p_node] not in nodes_to_remove:
                merge_dict[r_node].append(p_node)
        nodes_to_merge =\
            dict([(key, value) for key, value in merge_dict.items()
                  if len(value) > 1])

        # 2) Clone nodes
        clone_dict = {}
        for n in left_h.target_.nodes():
            clone_dict.update({n: []})
        for p_node, r_node in left_h.mapping_.items():
            clone_dict[r_node].append(p_node)
        for node, value in clone_dict.items():
            if value is not None and len(value) > 1:
                i = 0
                for val in value:
                    will_be_merged = False
                    for r_node, p_nodes in nodes_to_merge.items():
                        if val in p_nodes:
                            will_be_merged = True
                    if i > 0:
                        new_name = self.clone(instance, node)
                        P_instance.update(
                            {val: new_name})
                        if not will_be_merged:
                            RHS_instance.update(
                                {right_h.mapping_[val]: new_name})
                    else:
                        P_instance.update(
                            {val: instance[node]})
                        if not will_be_merged:
                            RHS_instance.update(
                                {right_h.mapping_[val]: instance[node]})
                    i += 1

        for edge in edges_to_remove:
            self.delete_edge(
                P_instance,
                edge[0],
                edge[1])

        # 3) Delete attrs
        for node, attrs in node_attrs_to_remove.items():
            if len(attrs) > 0:
                self.delete_node_attrs(
                    P_instance,
                    node,
                    attrs)

        for edge, attrs in edge_attrs_to_remove.items():
            self.delete_edge_attrs(
                P_instance,
                edge[0],
                edge[1],
                attrs)

        # 4) Add attrs
        for node, attrs in node_attrs_to_add.items():
            if len(attrs) > 0:
                self.add_node_attrs(P_instance, node, attrs)

        for edge, attrs in edge_attrs_to_add.items():
            self.add_edge_attrs(
                P_instance,
                edge[0],
                edge[1],
                attrs)

        # 5) Merge
        for rhs_node, nodes in nodes_to_merge.items():
            new_name = self.merge(P_instance, nodes)
            RHS_instance.update({rhs_node: new_name})

        # 6) Add nodes/edges
        for node in nodes_to_add:
            new_name = self.add_node(
                instance,
                right_h.target_.node[node].type_,
                attrs=right_h.target_.node[node].attrs_)
            RHS_instance.update({node: new_name})

        for s, t, attrs in edges_to_add:
            try:
                self.add_edge(
                    RHS_instance,
                    s,
                    t,
                    attrs)
            except:
                pass
        return RHS_instance

    def rule_to_homomorphisms(self, LHS, commands):
        """Cast sequence of commands to homomorphisms."""
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        actions = []
        for command in command_strings:
            try:
                parsed = parser.parseString(command).asDict()
                actions.append(parsed)
            except:
                raise ValueError("Cannot parse command '%s'" % command)

        P = LHS.copy()
        RHS = LHS.copy()

        pl_mapping = dict(zip(LHS.nodes(), LHS.nodes()))
        pr_mapping = dict(zip(LHS.nodes(), LHS.nodes()))
        # We modify P, RHS and respective mapping
        # in the course of command parsing
        for action in actions:
            if action["keyword"] == "clone":
                node_name = None
                if "node_name" in action.keys():
                    node_name = action["node_name"]
                cloned_node = clone_node(P, action["node"], node_name)
                pl_mapping[action["node"]] = action["node"]
                pl_mapping.update({cloned_node: action["node"]})
                clone_node(RHS, action["node"], node_name)
            elif action["keyword"] == "merge":
                method = None
                node_name = None
                edges_method = None
                if "method" in action.keys():
                    method = action["method"]
                if "node_name" in action.keys():
                    node_name = action["node_name"]
                if "edges_method" in action.keys():
                    edges_method = action["edges_method"]
                merged_node = merge_nodes(
                    RHS,
                    action["nodes"],
                    method,
                    node_name,
                    edges_method)
                for node in action["nodes"]:
                    pr_mapping.update({node: merged_node})
            elif action["keyword"] == "add_node":
                name = None
                node_type = None
                attrs = {}
                if "node" in action.keys():
                    name = action["node"]
                if "type" in action.keys():
                    node_type = action["type"]
                if "attrubutes" in action.keys():
                    attrs = action["attrubutes"]
                add_node(RHS, node_type, name, attrs)
            elif action["keyword"] == "delete_node":
                remove_node(P, action["node"])
                del pl_mapping[action["node"]]
                del pr_mapping[action["node"]]
                remove_node(RHS, action["node"])
            elif action["keyword"] == "add_edge":
                attrs = {}
                if "attrubutes" in action.keys():
                    attrs = action["attrubutes"]
                add_edge(
                    RHS,
                    action["node_1"],
                    action["node_2"],
                    attrs)
            elif action["keyword"] == "delete_edge":
                remove_edge(
                    P,
                    action["node_1"],
                    action["node_2"])
                remove_edge(
                    RHS,
                    action["node_1"],
                    action["node_2"])
            elif action["keyword"] == "add_node_attrs":
                add_node_attrs(
                    RHS,
                    action["node"],
                    action["attributes"])
            elif action["keyword"] == "add_edge_attrs":
                add_edge_attrs(
                    RHS,
                    action["node_1"],
                    action["node_2"],
                    action["attributes"])
            elif action["keyword"] == "delete_node_attrs":
                remove_node_attrs(
                    P,
                    action["node"],
                    action["attributes"])
                remove_node_attrs(
                    RHS,
                    action["node"],
                    action["attributes"])
            elif action["keyword"] == "delete_edge_attrs":
                remove_edge_attrs(
                    P,
                    action["node_1"],
                    action["node_2"],
                    action["attributes"])
                remove_edge_attrs(
                    RHS,
                    action["node_1"],
                    action["node_2"],
                    action["attributes"])
            elif action["keyword"] == "update_node_attrs":
                remove_node_attrs(
                    P,
                    action["node"],
                    P.node[action["node"]].attrs_)
                update_node_attrs(
                    RHS,
                    action["node"],
                    action["attributes"])
            elif action["keyword"] == "update_edge_attrs":
                remove_edge_attrs(
                    P,
                    action["node_1"],
                    action["node_2"],
                    P.edge[action["node_1"]][action["node_2"]])
                update_edge_attrs(
                    RHS,
                    action["node_1"],
                    action["node_2"],
                    action["attributes"])
            else:
                raise ValueError("Unknown command")
        h_p_lhs = Homomorphism(P, LHS, pl_mapping)
        h_p_rhs = Homomorphism(P, RHS, pr_mapping)
        return (h_p_lhs, h_p_rhs)
