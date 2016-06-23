"""Define Transformer and Rewriter used by graph rewriting tool."""

import networkx as nx
from networkx.algorithms import isomorphism
import warnings
from copy import deepcopy

import itertools
import random

from regraph.library.parser import parser
from regraph.library.utils import (is_subdict,
                                   merge_attributes,
                                   dict_sub)
from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism,
                                             TypedHomomorphism)
from regraph.library.category_op import (pullback,
                                         pullback_complement,
                                         pushout)


class Transformer(object):
    """ Class implements P, L, R, P->L and P->R """

    def __init__(self, graph):
        self.directed = type(graph) == TypedDiGraph
        self.G = graph
        self.P = TypedDiGraph() if self.directed else TypedGraph()
        self.R = TypedDiGraph() if self.directed else TypedGraph()
        self.L = TypedDiGraph() if self.directed else TypedGraph()
        self.P_L_dict = {}
        self.P_R_dict = {}

    def identity(self):
        return Homomorphism.identity(self.L, self.G)

    def __str__(self):
        return "Current graph\n%s\n" % self.G +\
               "Preserved part\n%s\n" % self.P +\
               "Left hand side\n%s\n" % self.L +\
               "P->L Homomorphism : %s\n" % self.P_L_dict +\
               "Right hand side\n%s\n" % self.R +\
               "P->R Homomorphism : %s\n" % self.P_R_dict

    def __doc__(self):
        return "A Tranformer instance is the representation of an instance of \
                P, L and R graphs and P->L, P->R homomorphisms. It allows you \
                stack changes and apply them later on thanks to the Rewriter \
                or the GraphModeler class"

    # Canonic operations

    def get(self):
        """ Gives you the homomorphisms P->L and P->R """
        return (Homomorphism(self.P, self.L, self.P_L_dict),
                Homomorphism(self.P, self.R, self.P_R_dict))

    # Basic operations

    def add_node(self, node_id, node_type, attrs=None):
        if not node_id in self.R.nodes():
            self.R.add_node(node_id, node_type, attrs)
        else:
            raise ValueError(
                "Node %s has already been added!" % str(node_id)
            )

    def merge_nodes(self, n1, n2, node_name=None):
        if n1 in self.G.nodes():
            if not n1 in self.P.nodes():
                self.P.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
            if not n1 in self.L.nodes():
                self.L.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_L_dict[n1] = n1

        if n2 in self.G.nodes():
            if not n2 in self.P.nodes():
                self.P.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
            if not n2 in self.L.nodes():
                self.L.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_L_dict[n2] = n2

        if not n1 in self.R.nodes():
            self.R.add_node(n1,
                            self.G.node[n1].type_,
                            self.G.node[n1].attrs_)
            self.P_R_dict[n1] = n1
        if not n2 in self.R.nodes():
            self.R.add_node(n2,
                            self.G.node[n2].type_,
                            self.G.node[n2].attrs_)
            self.P_R_dict[n2] = n2

        del_n1 = False
        del_n2 = False
        if not n1 in self.P_R_dict.keys():
            self.P_R_dict[n1] = n1
            del_n1 = True
        if not n2 in self.P_R_dict.keys():
            self.P_R_dict[n2] = n2
            del_n2 = True


        new_name = self.R.merge_nodes([self.P_R_dict[n1], self.P_R_dict[n2]],
                           node_name=node_name)

        if del_n1:
            del self.P_R_dict[n1]
        if del_n2:
            del self.P_R_dict[n2]

        if n1 in self.P.nodes():
            self.P_R_dict[n1] = new_name
        if n2 in self.P.nodes():
            self.P_R_dict[n2] = new_name

    def remove_node(self, n):
        if not n in self.L.nodes():
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

        if not n in self.R.nodes():
            self.R.add_node(n,
                            self.G.node[n].type_,
                            self.G.node[n].attrs_)

        if node_name == None:
            i = 1
            node_name = str(n)+str(i)
            while node_name in self.P.nodes():
                i+=1
                node_name = str(n)+str(i)

        self.P.add_node(node_name,
                        self.G.node[n].type_,
                        self.G.node[n].attrs_)
        self.R.add_node(node_name,
                        self.G.node[n].type_,
                        self.G.node[n].attrs_)

        if not n in self.L.nodes():
            self.L.add_node(n,
                            self.G.node[n].type_,
                            self.G.node[n].attrs_)
            self.P_L_dict[n] = n
            self.P_L_dict[node_name] = n
            self.P_R_dict[n] = n
            self.P_R_dict[node_name] = node_name
        else:
            for k,v in self.P_L_dict.items():
                if v == n:
                    return
            raise ValueError(
            "You deleted %s (or one of its adjacent edges) \
            and now you want to clone it.." % str(n)
            )

    def add_edge(self, n1, n2, attrs=None):
        if n1 in self.G:
            if not n1 in self.P.nodes():
                self.P.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_R_dict[n1] = n1
            if not n1 in self.L.nodes():
                self.L.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_L_dict[n1] = n1

        if n2 in self.G:
            if not n2 in self.P.nodes():
                self.P.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_R_dict[n2] = n2
            if not n2 in self.L.nodes():
                self.L.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_L_dict[n2] = n2

        if not n1 in self.R.nodes():
            if not n1 in self.G:
                raise ValueError(
                    "Node %s doesn't exist" % n1
                )
            self.R.add_node(n1,
                            self.G.node[n1].type_,
                            self.G.node[n1].attrs_)
            self.P_R_dict[n1] = n1
        if not n2 in self.R.nodes():
            if not n2 in self.G:
                raise ValueError(
                    "Node %s doesn't exist" % n2
                )
            self.R.add_node(n2,
                            self.G.node[n2].type_,
                            self.G.node[n2].attrs_)
            self.P_R_dict[n2] = n2

        del_n1 = False
        del_n2 = False
        if not n1 in self.P_R_dict.keys():
            self.P_R_dict[n1] = n1
            del_n1 = True
        if not n2 in self.P_R_dict.keys():
            self.P_R_dict[n2] = n2
            del_n2 = True

        if (self.P_R_dict[n1], self.P_R_dict[n2]) in self.R.edges():
            warnings.warn(
                "Edge %s-%s already exists, \
                 nothing has been changed!" %
                    (str(n1), str(n2))
            )
        else:
            self.R.add_edge(self.P_R_dict[n1], self.P_R_dict[n2], attrs)

        if del_n1:
            del self.P_R_dict[n1]
        if del_n2:
            del self.P_R_dict[n2]

    def remove_edge(self, n1, n2):
        if n1 in self.G:
            if not n1 in self.P.nodes():
                self.P.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
            if not n1 in self.L.nodes():
                self.L.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)

        if n2 in self.G:
            if not n2 in self.P.nodes():
                self.P.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
            if not n2 in self.L.nodes():
                self.L.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)

        if not n1 in self.R.nodes():
            self.R.add_node(n1,
                            self.G.node[n1].type_,
                            self.G.node[n1].attrs_)
        if not n2 in self.R.nodes():
            self.R.add_node(n2,
                            self.G.node[n2].type_,
                            self.G.node[n2].attrs_)



        if not (n1, n2) in self.L.edges():
            self.L.add_edge(n1,
                            n2,
                            self.G.get_edge(n1, n2))
        else:
            warnings.warn(
                "You already deleted the edge %s-%s !" %
                    (str(n1), str(n2))
            )

        self.P_L_dict[n1] = n1
        self.P_L_dict[n2] = n2
        self.P_R_dict[n1] = n1
        self.P_R_dict[n2] = n2

    def add_node_attrs(self, n, attrs):
        if n in self.G.nodes():
            if not n in self.P.nodes():
                self.P.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_R_dict[n] = n

            if not n in self.L.nodes():
                self.L.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_L_dict[n] = n
            if not n in self.R.nodes():
                self.R.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)

        if n in self.P_R_dict.keys():
            self.R.add_node_attrs(self.P_R_dict[n], attrs)
        elif n in self.R.nodes():
            self.R.add_node_attrs(n, attrs)
        else:
            raise ValueError(
                "Node %s doesn't exist" % n
            )


    def add_edge_attrs(self, n1, n2, attrs):
        if n1 in self.G:
            if not n1 in self.R.nodes():
                self.R.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_R_dict[n1] = n1
            if not n1 in self.P.nodes():
                self.P.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
            if not n1 in self.L.nodes():
                self.L.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_L_dict[n1] = n1
        else:
            if not n1 in self.R.nodes():
                raise ValueError(
                    "Node %s doesn't exist" % n1
                )

        if n2 in self.G:
            if not n2 in self.P_R_dict.keys():
                self.R.add_node(n2,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_R_dict[n2] = n2
            if not n2 in self.P.nodes():
                self.P.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
            if not n2 in self.L.nodes():
                self.L.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_L_dict[n2] = n2
        else:
            if not n2 in self.R.nodes():
                raise ValueError(
                    "Node %s doesn't exist" % n2
                )

        if (n1, n2) in self.G.edges():
            self.P.add_edge(n1, n2, self.G.get_edge(n1, n2))
            self.R.add_edge(self.P_R_dict[n1], self.P_R_dict[n2], self.G.get_edge(n1, n2))
            self.L.add_edge(self.P_L_dict[n1], self.P_L_dict[n2], self.G.get_edge(n1, n2))
            self.R.add_edge_attrs(self.P_R_dict[n1], self.P_R_dict[n2], attrs)
        else:
            if (n1,n2) in self.R.edges():
                self.R.add_edge_attrs(n1, n2, attrs)
            else:
                if n1 in self.P_L_dict.keys():
                    self.R.add_edge_attrs(self.P_L_dict[n1], n2, attrs)
                if n2 in self.P_L_dict.keys():
                    self.R.add_edge_attrs(n1, self.P_L_dict[n2], attrs)
                else:
                    raise ValueError(
                        "Edge %s-%s doesn't exist, please create it before adding\
                         attributes!" %
                            (str(n1), str(n2))
                    )

    def remove_node_attrs(self, n, attrs):

        if n in self.G.nodes():
            if not n in self.R.nodes():
                self.R.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_R_dict[n] = n
            self.R.remove_node_attrs(self.P_R_dict[n], attrs)

            if not n in self.L.nodes():
                self.L.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P.remove_node_attrs(n, attrs)
                self.P_L_dict[n] = n
            else:
                for k,v in self.P_L_dict.items():
                    if v == n:
                        self.P.remove_node_attrs(n, attrs)
                raise ValueError(
                    "Deleted %s (or one of its adjacent edges) \
                    and now you want to remove an attribute from it.." % str(n)
                )
        else:
            if n in self.R.nodes():
                self.R.remove_node_attrs(n, attrs)
            else:
                raise ValueError(
                    "Trying to remove attributes from node %s that doesn't \
                    exist" % n
                )

    def remove_edge_attrs(self, n1, n2, attrs):
        if n1 in self.G.nodes():
            if not n1 in self.P.nodes():
                self.P.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
            if not n1 in self.L.nodes():
                self.L.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_L_dict[n1] = n1

            if not n1 in self.R.nodes():
                self.R.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_R_dict[n1] = n1
        else:
            if not n1 in self.R.nodes():
                raise ValueError(
                    "Please add node %s before working on one of its \
                    adjacent edges" % n1
                )

        if n2 in self.G.nodes():
            if not n2 in self.P.nodes():
                self.P.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)

            if not n2 in self.L.nodes():
                self.L.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_L_dict[n2] = n2

            if not n2 in self.R.nodes():
                self.R.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_R_dict[n2] = n2
        else:
            if not n1 in self.R.nodes():
                raise ValueError(
                    "Please add node %s before working on one of its \
                    adjacent edges" % n2
                )

        if n1 in self.G.nodes() and n2 in self.G.nodes():
            if not (n1, n2) in self.L.edges():
                self.L.add_edge(n1, n2, self.G.get_edge(n1, n2))
            self.L.remove_edge_attrs(n1, n2, attrs)
        else:
            if n1 in self.P_L_dict.keys() and n2 in self.P_L_dict.keys():
                if (self.P_L_dict[n1], self.P_L_dict[n2]) in self.L.edges():
                    self.L.remove_edge_attrs(self.P_L_dict[n1], self.P_L_dict[n2], attrs)

        if not (n1, n2) in self.R.edges():
            if (n1, n2) in self.G.edges():
                self.R.add_edge(n1,
                                n2,
                                self.G.get_edge(n1, n2))
            if (n1 in self.P_L_dict.keys() and (self.P_L_dict[n1], n2) in self.G.edges()):
                self.R.add_edge(n1,
                                n2,
                                self.G.get_edge(self.P_L_dict[n1], n2))
            if (n2 in self.P_L_dict.keys() and (n1, self.P_L_dict[n2]) in self.G.edges()):
                self.R.add_edge(n1,
                                n2,
                                self.G.get_edge(n1, self.P_L_dict[n2]))
            if (n1 in self.P_L_dict.keys() and n2 in self.P_L_dict.keys() and\
               (self.P_L_dict[n1], self.P_L_dict[n2]) in self.G.edges()):
                self.R.add_edge(n1,
                                n2,
                                self.G.get_edge(self.P_L_dict[n1],
                                                self.P_L_dict[n2]))
            if not (n1, n2) in self.R.edges():
                raise ValueError(
                    "There is no edge %s-%s" % (n1, n2)
                )
        self.R.remove_edge_attrs(n1, n2, attrs)


    # Advanced operations

    def merge_edges(self, e1, e2, name_n1=None, name_n2=None):
        n1_1, n1_2 = e1
        n2_1, n2_2 = e2
        if (n1_1 == n2_2) or (n1_2 == n2_1):
            if self.G.is_directed():
                raise ValueError(
                    "Can't merge edges with pattern %s->%s and %s->%s" %
                    (n1_1, n1_2, n2_1, n2_2)
                )
            else:
                if n1_1 == n2_2:
                    self.merge_nodes(n1_2, n2_1, name_n2)
                else:
                    self.merge_nodes(n1_1, n2_2, name_n1)
        else:
            self.merge_nodes(n1_1, n2_1, name_n1)
            self.merge_nodes(n1_2, n2_2, name_n2)
            self.R.add_edge(name_n1, name_n2)

    def clone_edge(self, n1, n2, new_n1, new_n2):
        self.clone_node(n1, new_n1)
        self.clone_node(n2, new_n2)
        self.R.add_edge(new_n1, new_n2)

    def merge_nodes_list(self, l, node_name=None):
        self.merge_nodes(l[0], l[1], node_name)
        for i in range(2, len(l)):
            self.merge_nodes(l[i], node_name, node_name)


class Rewriter:
    """Class implements the transformation on the graph."""

    def __init__(self, graph):
        """Initialize Rewriter object with input graph."""
        self.graph_ = graph
        self.fully_expanded_graph = deepcopy(graph)
        self.h_exp = dict([(n,n) for n in graph.nodes()])
        self.parser_ = parser
        return

    def __doc__(self):
        return "A Rewriter instance alows you to do a horizontal rewrite on \
                a single graph, it also gives the needed informations (the \
                G- -> G and G- -> Gprime homomorphisms) to propagate that \
                change in the GraphModeler"

    @staticmethod
    def rewrite(L_G, trans, get_details=False):
        """ Simple rewriting using category operations """
        left_h, right_h = trans.get()
        graph = trans.G

        if left_h.source_ != right_h.source_:
            raise ValueError(
                "Can't rewrite, homomorphisms don't have the same preserved part"
            )

        Gm, P_Gm, Gm_G = pullback_complement(left_h, L_G)
        Gprime, Gm_Gprime, R_Gprime = pushout(P_Gm, right_h)
        Gprime.metamodel_ = graph.metamodel_
        Gprime.hom = TypedHomomorphism.canonic(Gprime, graph.metamodel_)
        if get_details:
            return Gm_Gprime, Gm_G
        else:
            return Gprime

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
    def transformer_from_command(G, commands):
        """Cast sequence of commands to Transformer instance."""
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
                merged_node = trans.merge_nodes_list(
                    action["nodes"],
                    node_name)
            elif action["keyword"] == "add_node":
                name = None
                node_type = None
                attrs = {}
                if "node" in action.keys():
                    name = action["node"]
                if "type" in action.keys():
                    node_type = action["type"]
                if "attributes" in action.keys():
                    attrs = action["attributes"]
                trans.add_node(name, node_type, attrs)
            elif action["keyword"] == "delete_node":
                trans.remove_node(action["node"])
            elif action["keyword"] == "add_edge":
                attrs = {}
                if "attributes" in action.keys():
                    attrs = action["attributes"]
                trans.add_edge(
                    action["node_1"],
                    action["node_2"],
                    attrs)
            elif action["keyword"] == "delete_edge":
                trans.remove_edge(
                    action["node_1"],
                    action["node_2"])
            elif action["keyword"] == "add_node_attrs":
                trans.add_node_attrs(
                    action["node"],
                    action["attributes"])
            elif action["keyword"] == "add_edge_attrs":
                trans.add_edge_attrs(
                    action["node_1"],
                    action["node_2"],
                    action["attributes"])
            elif action["keyword"] == "delete_node_attrs":
                trans.remove_node_attrs(
                    action["node"],
                    action["attributes"])
            elif action["keyword"] == "delete_edge_attrs":
                trans.remove_edge_attrs(
                    action["node_1"],
                    action["node_2"],
                    action["attributes"])
            else:
                raise ValueError("Unknown command %s" % action["keyword"])
        return trans

    def apply_rule(self, instance, trans):

        left_h, right_h = trans.get()

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
            self.graph_.remove_node(node)

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
                        if node != val:
                            new_name = self.graph_.clone_node(node, val)
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
            if (edge[0],edge[1]) in self.graph_.edges():
                self.graph_.remove_edge(
                    edge[0],
                    edge[1])

        # 3) Delete attrs
        for node, attrs in node_attrs_to_remove.items():
            if len(attrs) > 0:
                self.graph_.remove_node_attrs(
                    node,
                    attrs)

        for edge, attrs in edge_attrs_to_remove.items():
            self.graph_.remove_edge_attrs(
                edge[0],
                edge[1],
                attrs)

        # 4) Add attrs
        for node, attrs in node_attrs_to_add.items():
            if len(attrs) > 0:
                self.graph_.add_node_attrs(node, attrs)

        for edge, attrs in edge_attrs_to_add.items():
            self.graph_.add_edge_attrs(
                edge[0],
                edge[1],
                attrs)

        # 5) Merge
        for rhs_node, nodes in nodes_to_merge.items():
            new_name = self.graph_.merge_nodes(nodes, node_name=rhs_node)
            RHS_instance.update({rhs_node: new_name})

        # 6) Add nodes/edges
        for node in nodes_to_add:
            self.graph_.add_node(
                node,
                right_h.target_.node[node].type_,
                attrs=right_h.target_.node[node].attrs_)
            RHS_instance.update({node: node})

        for edge, attrs in edges_to_add.items():
            try:
                self.graph_.add_edge(
                    edge[0],
                    edge[1],
                    attrs)
            except:
                pass
        return RHS_instance

    @staticmethod
    def gen_transformations(n, graph, p_opt=0.5, merge_prop_av = 0.2,
                            merge_prop_dev = 0.05, p_attrs = 0.5, p_attrs_value=0.5):

        def rand_attrs(attrs):
            if attrs == None:
                return {}

            new_attrs = {}
            for k,v in attrs.items():
                if random.random() <= p_attrs:
                    value = []
                    for val in v:
                        if random.random() <= p_attrs_value:
                            value.append(val)
                    new_attrs[k] = set(value)
            return new_attrs

        trans = []
        env = graph.copy()
        if graph.metamodel_ == None:
            types = ["anything"]
        else:
            types = graph.metamodel_.nodes()
        actions = [
            "CLONE",
            "MERGE",
            "ADD_NODE",
            "DELETE_NODE",
            "ADD_EDGE",
            "DELETE_EDGE",
            "ADD_NODE_ATTRS",
            "ADD_EDGE_ATTRS",
            "DELETE_NODE_ATTRS",
            "DELETE_EDGE_ATTRS"
        ]

        def pick_node():
            if len(env.nodes()) > 0:
                return random.sample(env.nodes(), 1)[0]
            else:
                return None

        def pick_nodes():
            if env.metamodel_ == None:
                ty = random.choice([None, "anything"])
            else:
                ty = pick_type()
            node_list = [n for n in env.nodes() if env.node[n].type_ == ty]
            n = abs(int(random.gauss(merge_prop_av*len(node_list),
                                     merge_prop_dev*len(node_list))))
            res = []
            for node in random.sample(node_list, n):
                res.append(node)
            return res

        def pick_edge():
            if len(env.edges()) > 0:
                return random.sample(env.edges(), 1)[0]
            else:
                return None,None

        def pick_new_edge():
            i = 500
            while i > 0:
                n1 = pick_node()
                n2 = pick_node()
                if env.metamodel_ == None or (env.node[n1].type_, env.node[n2].type_) in env.metamodel_.edges():
                    return (n1, n2)
                else:
                    i-=1
            return None

        def pick_type():
            return random.sample(types, 1)[0]

        def pick_attrs_from(node):
            return rand_attrs(env.node[node].attrs_)

        def pick_attrs_for(node):
            if graph.metamodel_ == None:
                return {}
            else:
                return rand_attrs(graph.metamodel_.node[env.node[node].type_].attrs_)

        def pick_edge_attrs_from(n1, n2):
            return rand_attrs(env.get_edge(n1, n2))

        def pick_edge_attrs_for(n1, n2):
            if env.metamodel_ == None:
                return {}
            else:
                return rand_attrs(env.metamodel_.get_edge(
                    env.node[n1].type_,
                    env.node[n2].type_
                ))

        def pick_name():
            generated_name = 1
            while str(generated_name) in env.nodes():
                generated_name += 1
            return str(generated_name)

        def pick_method():
            return random.choice(["UNION", "INTERSECTION"])

        def add_req(op, s):
            op += s
            return op

        def add_opt(op, s):
            if random.random() <= p_opt:
                op += s
                return True, op
            else:
                return False, op

        while len(trans) < n:
            op = random.choice(actions)
            if op == "CLONE":
                node = pick_node()
                if node == None:
                    continue
                name = pick_name()

                op = add_req(op, " '%s'" % str(node))
                opt,op = add_opt(op, " AS '%s'" % str(name))
                if not opt:
                    name = None

                env.clone_node(node, name)
            elif op == "MERGE":
                nodes = pick_nodes()
                if nodes == []:
                    continue
                method = pick_method()
                new_name = pick_name()
                edges = pick_method()
                new_node_attrs = None
                new_edge_attrs = None

                op = add_req(op, " "+str(nodes))
                opt,op = add_opt(op, " METHOD "+str(method))
                if not opt:
                    method = "UNION"
                opt,op = add_opt(op, " AS '%s'" % str(new_name))
                if not opt:
                    new_name = None
                opt,op = add_opt(op, " EDGES "+str(edges))
                if not opt:
                    edges = "UNION"

                if nodes != []:
                    env.merge_nodes(nodes,
                                method.lower(),
                                new_name,
                                edges.lower())
            elif op == "ADD_NODE":
                name = pick_name()
                typ = pick_type()

                attrs = rand_attrs(env.metamodel_.node[typ].attrs_)

                op = add_req(op, " '%s'" % str(name))
                op = add_req(op, " TYPE '%s'" % str(typ))
                opt,op = add_opt(op, " "+str(attrs))
                if not opt:
                    attrs = None

                env.add_node(name, typ, attrs)
            elif op == "DELETE_NODE":
                node = pick_node()
                if node == None:
                    continue

                op = add_req(op, " '%s'" % str(node))

                env.remove_node(node)
            elif op == "ADD_EDGE":
                e = pick_new_edge()
                if e == None:
                    continue
                else:
                    n1, n2 = e
                attrs = pick_edge_attrs_for(n1, n2)

                op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))
                opt,op = add_opt(op, " "+str(attrs))
                if not opt:
                    attrs = None

                env.add_edge(n1, n2, attrs)
            elif op == "DELETE_EDGE":
                n1, n2 = pick_edge()
                if n1 == None or n2 == None:
                    continue

                op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))

                env.remove_edge(n1, n2)
            elif op == "ADD_NODE_ATTRS":
                node = pick_node()
                if node == None:
                    continue
                if env.metamodel_ == None:
                    attrs = {}
                else:
                    if env.metamodel_.node[env.node[node].type_].attrs_ == None:
                        attrs = {}
                    else:
                        attrs = rand_attrs(dict_sub(env.metamodel_.node[env.node[node].type_].attrs_,
                                            env.node[node].attrs_))

                op = add_req(op, " '%s'" % node)
                op = add_req(op, " "+str(attrs))

                if attrs == {}:
                    continue

                env.add_node_attrs(node, attrs)
            elif op == "ADD_EDGE_ATTRS":
                n1, n2 = pick_edge()
                if n1 == None or n2 == None:
                    continue
                if env.metamodel_ == None:
                    attrs = {}
                else:
                    attrs = rand_attrs(dict_sub(
                        env.metamodel_.get_edge(
                            env.node[n1].type_,
                            env.node[n2].type_),
                        env.get_edge(n1, n2)
                        )
                    )

                op = add_req(op, " '%s' '%s'" % (n1,n2))
                op = add_req(op, " "+str(attrs))

                if attrs == {}:
                    continue

                env.add_edge_attrs(n1, n2, attrs)
            elif op == "DELETE_NODE_ATTRS":
                node = pick_node()
                if node == None:
                    continue
                attrs = pick_attrs_from(node)

                if attrs == {} or attrs == None:
                    continue

                op = add_req(op, " '%s'" % node)
                op = add_req(op, " "+str(attrs))

                env.remove_node_attrs(node, attrs)
            elif op == "DELETE_EDGE_ATTRS":
                n1, n2 = pick_edge()
                if n1 == None or n2 == None:
                    continue
                attrs = pick_edge_attrs_from(n1, n2)

                if attrs == {} or attrs == None:
                    continue

                op = add_req(op, " '%s' '%s'" % (n1,n2))
                op = add_req(op, " "+str(attrs))

                env.remove_edge_attrs(n1, n2, attrs)
            else:
                raise ValueError(
                    "Unknown action"
                )

            trans.append(op)
        return ".\n".join(trans)
