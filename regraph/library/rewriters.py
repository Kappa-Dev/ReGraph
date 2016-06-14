"""."""
import networkx as nx
from networkx.algorithms import isomorphism
import warnings

import itertools

from regraph.library.parser import parser
from regraph.library.utils import (is_subdict)
from regraph.library.data_structures import (Homomorphism)


class Rewriter:
    """Class implements the transformation on the graph."""

    def __init__(self, graph):
        """Initialize Rewriter object with input graph."""
        self.graph_ = graph
        self.parser_ = parser
        return

    def fold_attr(self, typ, attr):
        fold_dict = {}
        for n in self.graph_.nodes():
            if self.graph_.node[n].type_ == typ:
                if attr in self.graph_.node[n].attrs_:
                    if self.graph_.node[n].attrs_[attr] in fold_dict.keys():
                        fold_dict[self.graph_.node[n].attrs_[attr]].append(n)
                    else:
                        fold_dict[self.graph_.node[n].attrs_[attr]] = [n]
                else:
                    if "__NOT_DEFINED__" in fold_dict.keys():
                        fold_dict["__NOT_DEFINED__"].append(n)
                    else:
                        fold_dict["__NOT_DEFINED__"] = [n]
        for (k, l) in fold_dict.items():
            merge_nodes(self.graph_, l, node_name=attr+":"+k)
            for n in l:
                for n0 in self.fully_expanded_graph.nodes():
                    if self.h_exp.mapping_[n0] == n:
                        self.h_exp.mapping_[n0] = attr+":"+k

    def fold_nodes(self, l):
        ty = []
        for n in l:
            if n in self.graph_.nodes():
                if not self.graph_.node[n].type_ in ty:
                    ty.append(str(self.graph_.node[n].type_))
            else:
                raise ValueError(
                    "Node %s isn't a valid node" % str(n)
                )
        new_ty = fold_left(lambda x, acc : acc+"_"+x, "_", sorted(ty))
        i = 0
        new_name = new_ty+"0"
        while(new_name in self.graph_.nodes()):
            i += 1
            new_name = new_ty+str(i)
        for n in l:
            cast_node(self.graph_, n, new_ty)
            for n0 in self.fully_expanded_graph.nodes():
                if self.h_exp.mapping_[n0] == n:
                    self.h_exp.mapping_[n0] = new_name
        merge_nodes(self.graph_, l, node_name = new_name)


    def expand_node(self, n0):
        origin = []
        for n in self.fully_expanded_graph.nodes():
            if self.h_exp.mapping_[n] == n0:
                origin.append(n)
        if len(origin) > 1 :
            exp_graph = self.fully_expanded_graph.subgraph(origin).copy()
            self.graph_ = union(self.graph_, exp_graph)
            for n in exp_graph.nodes():
                neighbors = self.fully_expanded_graph.neighbors(n)
                for n1 in neighbors:
                    self.graph_.add_edge(n, self.h_exp.mapping_[n1], self.fully_expanded_graph.get_edge(n,n1))
                self.h_exp.mapping_[n] = n
            remove_node(self.graph_, n0)
        elif len(origin) == 1 :
            warnings.warn(
                "Node %s is atomic, can't expand it further" % str(origin[0]),
                Warning
            )
        else:
            raise ValueError(
                "Node %s does not exist, can't expand it" % (str(n0))
            )

    def rewriting(self, left_h, right_h):
        """ left_h : P -> L
            right_h : P -> R
        """
        if left_h.source_ != right_h.source_:
            raise ValueError(
                "Can't rewrite, homomorphisms don't have the same preserved part"
            )

        L_G_instances = self.find_matching(left_h.target_)
        Gprime = self.graph_
        for L_G in L_G_instances :
            G-, P_G-, G-_G = pullback_complement(left_h, L_G)
            Gprime, G-_Gprime, R_Gprime = pushout(P_G-, P_R)
            Gprime.metamodel_ = self.graph_.metamodel_
            Gprime.hom = Homomorphism.canonic_homomorphism (Gprime, self.metamodel_)
        return G-_Gprime, G-_G
