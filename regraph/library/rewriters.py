"""."""
import networkx as nx
from networkx.algorithms import isomorphism
import warnings
from copy import deepcopy

import itertools

from regraph.library.parser import parser
from regraph.library.utils import (is_subdict)
from regraph.library.data_structures import (Homomorphism)


class Transformer(object):

    def __init__(self, graph):
        self.directed = type(graph) == TypedDiGraph
        self.G = graph
        self.P = TypedDiGraph() if self.directed else TypedGraph()
        self.R = TypedDiGraph() if self.directed else TypedGraph()
        self.L = TypedDiGraph() if self.directed else TypedGraph()
        self.P_L_dict = {}
        self.P_R_dict = {}

    # Canonic operations

    def get(self):
        return Homomorphism(P, L, P_L_dict), Homomorphism(P, L, P_R_dict)

    def add_node(self, node_id, node_type, attrs=None):
        if not node in self.R.nodes():
            self.R.add_node(node_id, node_type, attrs)
        else:
            raise ValueError(
                "Node %s has already been added!" % str(node_id)
            )

    def merge_nodes(self, n1, n2, node_name=None):
        if not n1 in self.P.nodes():
            self.P.add_node(n1,
                            self.G.node[n1].type_,
                            self.G.node[n1].attrs_)
        if not n2 in self.P.nodes():
            self.P.add_node(n2,
                            self.G.node[n2].type_,
                            self.G.node[n2].attrs_)

        if n1 in self.P_R_dict.keys():
            if n2 in self.P_R.keys():
                new_name = self.R.merge_nodes([P_R_dict[n1]; P_R_dict[n2]],
                                   node_name=node_name)
            else:
                self.R.add_node(n2,
                                self.G.node[n2].type_
                                self.G.node[n2].attrs_)
                new_name = self.R.merge_nodes([P_R_dict[n1]; n2],
                                   node_name=node_name)
        else:
            if n2 in self.P_R.keys():
                self.R.add_node(n1,
                                self.G.node[n1].type_
                                self.G.node[n1].attrs_)
                new_name = self.R.merge_nodes([n1; P_R_dict[n2]],
                                   node_name=node_name)
            else:
                self.R.add_node(n1,
                                self.G.node[n1].type_
                                self.G.node[n1].attrs_)
                self.R.add_node(n2,
                                self.G.node[n2].type_
                                self.G.node[n2].attrs_)
                new_name = self.R.merge_nodes(n1; n2],
                                   node_name=node_name)
        P_R_dict[n1] = new_name
        P_R_dict[n2] = new_name

    def remove_node(self, n):
        if not node in self.L.nodes():
            self.L.add_node(n, self.G.node[n].type_, self.G.node[n].attrs_)
        else:
            for k,v in self.P_L_dict.items():
                if v == n:
                    raise ValueError(
                        "You cloned %s (or one of its adjacent edges) \
                        and now you want to delete it.." % str(n)
                    )

    def clone_node(self, n, node_name=None):
        if not n in self.P.nodes():
            self.P.add_node(n,
                            self.G.node[n].type_,
                            self.G.node[n].attrs_)
        if not n in self.L.nodes():
            self.L.add_node(n,
                            self.G.node[n].type_,
                            self.G.node[n].attrs_)
        else:
            try:
                for k,v in self.P_L_dict.items():
                    if v == n:
                        return
                raise ValueError(
                    "You deleted %s (or one of its adjacent edges) \
                    and now you want to clone it.." % str(n)
                )
            with:
                raise ValueError(
                    "You deleted %s (or one of its adjacent edges) \
                    and now you want to clone it.." % str(n)
                )
        if node_name = None:
            i = 1
            node_name = str(n)+str(i)
            while node_name in self.P.nodes():
                i+=1
                node_name = str(n)+str(i)

        self.P.add_node(node_name,
                        self.G.node[n].type_,
                        self.G.node[n].attrs_)
        try:
            if self.P_L_dict[n] != n:
                raise ValueError(
                    "Node %s already has an image in L" % str(n)
                )
        with:
            pass
        self.P_L_dict[n] = n
        self.P_L_dict[str(n)+str(i)] = n

    def add_edge(self, n1, n2, attrs=None):
        if not n1 in self.P.nodes():
            self.P.add_node(n1,
                            self.G.node[n1].type_,
                            self.G.node[n1].attrs_)
        if not n2 in self.P.nodes():
            self.P.add_node(n2,
                            self.G.node[n2].type_,
                            self.G.node[n2].attrs_)

        if n1 in self.P_R_dict.keys():
            if n2 in self.P_R_dict.keys():
                if (P_R_dict[n1], P_R_dict[n2]) in self.R.edges():
                    warnings.warn(
                        "Edge (%s->%s)-(%s->%s) already exists, \
                         nothing has been changed!" %
                            (str(n1), str(P_R_dict[n1]),
                             str(n2), str(P_R_dict[n2]))
                    )
                else:
                    self.R.add_edge(P_R_dict[n1], P_R_dict[n2], attrs)
            else:
                self.R.add_edge(P_R_dict[n1], n2, attrs)
        else:
            self.R.add_edge(n1, n2, attrs)

    def remove_edge(self, n1, n2):
        if not n1 in self.P.nodes():
            self.P.add_node(n1,
                            self.G.node[n1].type_,
                            self.G.node[n1].attrs_)
        if not n2 in self.P.nodes():
            self.P.add_node(n2,
                            self.G.node[n2].type_,
                            self.G.node[n2].attrs_)

        if n1 in self.L.nodes():
            self.L.add_node(n1,
                            self.G.node[n1].type_,
                            self.G.node[n1].attrs_)
        if not n2 in self.L.nodes():
            self.L.add_node(n2,
                            self.G.node[n2].type_,
                            self.G.node[n2].attrs_)

        if not (n1, n2) in self.L.edges():
            self.L.add_edge(n1,
                            n2,
                            self.G.get_edge(n1, n2)
        else:
            warnings.warn(
                "You already deleted the edge %s-%s !" %
                    (str(n1), str(n2))
            )

        self.P_L_dict[n1] = n1
        self.P_L_dict[n2] = n2

    # Advanced operations

    def merge_edges(self, e1, e2, name_n1=None, name_n2=None):
        n1_1, n2_1 = e1
        n2_1, n2_1 = e2
        self.merge_nodes(n1, n2, name_n1)
        self.merge_nodes(n1, n2, name_n2)

    def clone_edge(self, n1, n2):
        self.clone_node(n1)
        self.clone_node(n2)

    def merge_nodes_list(self, l, node_name=None):
        for i in range(1, len(l))
            self.merge_nodes(l[i-1], l[i], node_name)


class Rewriter:
    """Class implements the transformation on the graph."""

    def __init__(self, graph):
        """Initialize Rewriter object with input graph."""
        self.graph_ = graph
        self.fully_expanded_graph = deepcopy(graph)
        self.h_exp = dict([(n,n) for n in graph.nodes()])
        self.parser_ = parser
        return

    @staticmethod
    def rewriting(graph, L_G, left_h, right_h):
        """ left_h : P -> L
            right_h : P -> R
        """
        if left_h.source_ != right_h.source_:
            raise ValueError(
                "Can't rewrite, homomorphisms don't have the same preserved part"
            )

        G-, P_G-, G-_G = pullback_complement(left_h, L_G)
        Gprime, G-_Gprime, R_Gprime = pushout(P_G-, P_R)
        Gprime.metamodel_ = graph.metamodel_
        Gprime.hom = Homomorphism.canonic_homomorphism (Gprime, graph.metamodel_)
        return G-_Gprime, G-_G

    @staticmethod
    def find_matching(graph, pattern):
        """Perform matching of the pattern graph."""
        # NetworkX isomorphism lib crushes if the ids of nodes
        # have different types (e.g ints and strings).
        # For the sake of security we will temporarily make
        # all the nodes ids to be int
        labels_mapping = dict([(n, i + 1) for i, n in enumerate(graph.nodes())])
        g = graph.relabel_nodes(labels_mapping)
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

    @staticmethod
    def generate_rule(G, commands):
        """Cast sequence of commands to homomorphisms."""
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        actions = []
        for command in command_strings:
            try:
                parsed = parser.parseString(command).asDict()
                actions.append(parsed)
            except:
                raise ValueError("Cannot parse command '%s'" % command)

        trans = Transformer(G)

        for action in actions:
            if action["keyword"] == "clone":
                node_name = None
                if "node_name" in action.keys():
                    node_name = action["node_name"]
                cloned_node = clone_node(P, action["node"], node_name)
                pl_mapping[action["node"]] = action["node"]
                pl_mapping.update({cloned_node: action["node"]})
                trans.clone_node(action["node"], node_name)
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
                merged_node = trans.merge_nodes(
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
