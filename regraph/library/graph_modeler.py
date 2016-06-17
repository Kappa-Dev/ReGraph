import networkx as nx
import warnings

from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             TypedHomomorphism,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter
from regraph.library.category_op import (pullback,
                                         pushout,
                                         pullback_complement)

class GraphModeler(object):

    def __init__(self, l, homL, names=[]):
        """ l : nx.Graph list (directed or not) [G1, G2 ...]
            homL : dict list (starting with [G1->G2 ... ])
            names : str list
        """
        typing_graph = None
        self.graph_chain = [None for i in range(len(l))]
        self.hom_chain = [None]+[h for h in homL]
        self.graph_names = [None for i in range(len(names))]
        self.changes = [None for i in range(len(l))]

        for i in range(len(l)):
            directed = type(l[i]) == nx.DiGraph
            typing_graph = self.make_tygraph(l[i], typing_graph, self.hom_chain[i], directed)
            self.graph_chain[i] = typing_graph

            for i in range(len(names)):
                if names[i] in self.graph_names:
                    raise ValueError(
                        "Name %s already used for another graph" % names[i]
                    )
                if type(names[i]) != str:
                    raise ValueError(
                        "Graph names have to be Strings"
                    )
                self.graph_names[i] = names[i]

    def make_tygraph(self, G, T, hom, di):
        res = TypedDiGraph(T) if di else TypedGraph(T)
        for n in G.nodes():
            if hom == None:
                res.add_node(n, None, G.node[n])
            else:
                res.add_node(n, hom[n], G.node[n])
        for (n1, n2) in G.edges():
            res.add_edge(n1, n2, G.edge[n1][n2])
            if hom == None or T == None:
                res.hom = None
            else:
                res.hom = TypedHomomorphism(res, T, hom)
        return res

    def get_by_id(self, n):
        return self.graph_chain[n]

    def get_id_from_name(self, name):
        for i in range(self.graph_names):
            if self.graph_names[i] == name:
                return i
        raise ValueError(
            "Graph %s is not defined in the modeler"% name
        )

    def get_by_name(self, name):
        for i in range(self.rw_names):
            if self.graph_names[i] == name:
                return self.graph_chain[i]
        raise ValueError(
            "Graph %s is not defined in the modeler" % name
        )

    def rewrite(self, n_i, L_T, trans):
        """ n_i : name or id
            left_h : P -> L
            right_h : P -> R
        """
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or \
                 name:str" % type(n_i)
            )
        self.changes[i] = Rewriter.rewrite(L_T, trans)

    def propagate_from(self, n_i):
        """ n_i : name or id
        """
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting int or str" %
                type(n_i)
            )
        if i >= len(self.graph_chain)-1:
            return
        else:
            if self.changes[i] != None:
                G = self.graph_chain[i+1]
                T = G.metamodel_
                Tm_Tprime, Tm_T = self.changes[i]
                Gm, Gm_G, Gm_Tm = pullback(G.hom, Tm_T)
                Gprime, Gm_Gprime, Gprime_Tprime = pullback_complement(Gm_Tm, Tm_Tprime)
                Gprime.metamodel_ = Gprime_Tprime.target_
                Gprime.hom = TypedHomomorphism.from_untyped(Gprime_Tprime)
                self.changes[i+1] = Gm_Gprime, Gm_G
                self.propagate_from(i+1)
            else:
                warnings.warn(
                    "Nothing to propagate from here !", RuntimeWarning
                )


    def propagate_all(self):
        for i in range(len(self.changes)-1, -1, -1):
            if self.changes[i] != None:
                self.propagate_from(i)

    def commit_changes(self):
        for i in range(len(self.changes)):
            if self.changes[i] != None:
                self.graph_chain[i] = self.changes[i][0].target_
                self.changes[i] = None
