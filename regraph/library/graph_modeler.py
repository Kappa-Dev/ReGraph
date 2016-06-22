"""Define GraphModeler used by graph rewriting tool."""

import networkx as nx
import warnings

from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             TypedNode,
                                             TypedHomomorphism,
                                             Homomorphism)
from regraph.library.rewriters import (Transformer,
                                       Rewriter)
from regraph.library.category_op import (pullback,
                                         pushout,
                                         pullback_complement)

class GraphModeler(object):
    """ Class implements a chain of graph typed by their follower in the list.
        It allows you to build a system where each graph has a model and where
        the modification of a model can propagate to the upper graphs
    """

    def __init__(self, l, homL, names=[], do_pbc = False):
        """ l : nx.Graph list (directed or not) [G1, G2 ...]
            homL : dict list (starting with [G1->G2 ... ])
            names : str list
        """
        typing_graph = None
        self.graph_chain = [None for i in range(len(l))]
        self.hom_chain = [None]+[h for h in homL]
        self.graph_names = [None for i in range(len(l))]
        self.changes = [None for i in range(len(l))]
        self.do_pbc = do_pbc

        for i in range(len(l)):
            directed = type(l[i]) == nx.DiGraph
            typing_graph = self.make_tygraph(l[i], typing_graph, self.hom_chain[i], directed)
            self.graph_chain[i] = typing_graph
            self.hom_chain[i] = self.graph_chain[i].hom

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

    def __str__(self):
        res = ''
        for i in range(len(self.graph_chain)-1, -1, -1):
            res += '--- Graph %s:\n\n' %\
                    (self.graph_names[i] if self.graph_names[i] != None else i)
            res += str(self.graph_chain[i])
            res += '' if self.hom_chain[i] == None else "Mapping :\n"
            res += '' if self.hom_chain[i] == None else str(self.hom_chain[i])
            res += '\n\n'
        return res

    def __doc__(self):
        return "Class implements a chain of graph typed by their follower in the list.\
                It allows you to build a system where each graph has a model and where\
                the modification of a model can propagate to the upper graphs"

    def init_rewriting(self, n_i):
        if type(n_i) == int:
            g = self.get_by_id(n_i)

        elif type(n_i) == str:
            g = self.get_by_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or \
                 name:str" % type(n_i)
            )
        return Transformer(g)

    def make_tygraph(self, G, T, hom, di):
        res = TypedDiGraph(T) if di else TypedGraph(T)
        for n in G.nodes():
            if hom == None:
                if type(G.node[n]) == TypedNode:
                    res.add_node(n, None, G.node[n].attrs_)
                else:
                    res.add_node(n, None, G.node[n])
            else:
                if type(G.node[n]) == TypedNode:
                    res.add_node(n, hom[n], G.node[n].attrs_)
                else:
                    res.add_node(n, hom[n], G.node[n])
        for (n1, n2) in G.edges():
            if type(G.node[n1]) == TypedNode:
                res.add_edge(n1, n2, G.get_edge(n1, n2))
            else:
                res.add_edge(n1, n2, G.edge[n1][n2])
            if hom == None or T == None:
                res.hom = None
            else:
                res.hom = TypedHomomorphism(res, T, hom)
        return res

    def remove_layer(self, n_i):
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or \
                 name:str" % type(n_i)
            )
        if (i < len(self.graph_chain)-1) and i >= 0:

            del self.graph_chain[i]
            if i > 0:
                prev_g = self.make_tygraph(self.graph_chain[i],
                                           self.graph_chain[i-1],
                                           Homomorphism.compose(self.hom_chain[i], self.hom_chain[i+1]).mapping_,
                                           type(self.graph_chain[i] == TypedDiGraph))
            else:
                prev_g = self.make_tygraph(self.graph_chain[i],
                                           None,
                                           None,
                                           type(self.graph_chain[i] == TypedDiGraph))

            self.graph_chain[i] = prev_g

            if i > 0:
                self.hom_chain[i+1] = Homomorphism.compose(self.hom_chain[i], self.hom_chain[i+1])
            del self.hom_chain[i]
            self.hom_chain[0] = None

            del self.graph_names[i]
            del self.changes[i]

    def insert_layer(self, graph, name=None, i=None,
                  hup=None, hdown=None):
        if name in self.graph_names:
            raise ValueError(
                "Name %s already used for another graph" % names[i]
            )
        if type(name) != str:
            raise ValueError(
                "Graph names have to be Strings"
            )

        if type(i) != int:
            i = len(self.graph_chain)

        if i > 0:
            new_g = self.make_tygraph(graph,
                                      self.graph_chain[i-1],
                                      hdown,
                                      type(graph) == nx.DiGraph)
        else:
            new_g = self.make_tygraph(graph,
                                      None,
                                      None,
                                      type(graph) == nx.DiGraph)

        if i < len(self.graph_chain)-1:
            prev_g = self.make_tygraph(self.graph_chain[i],
                                       new_g,
                                       hup,
                                       type(self.graph_chain[i]) == TypedDiGraph)
            self.graph_chain[i] = prev_g
            self.graph_chain[i].hom = hup
            self.hom_chain[i] = hup

        self.graph_chain.insert(i, new_g)
        self.hom_chain.insert(i, hdown)
        self.graph_names.insert(i, name)

    def get_by_id(self, n):
        return self.graph_chain[n]

    def get_id_from_name(self, name):
        for i in range(len(self.graph_names)):
            if self.graph_names[i] == name:
                return i
        raise ValueError(
            "Graph %s is not defined in the modeler"% name
        )

    def get_by_name(self, name):
        for i in range(len(self.graph_names)):
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
        self.changes[i] = Rewriter.rewrite(L_T, trans, True)

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
            if self.do_pbc:
                self.graph_chain[i] = self.changes[i][0].target_
            else:
                self.graph_chain[i] = self.changes[i][1].source_
            self.graph_chain[i].metamodel_ = self.graph_chain[i-1]

            self.changes[i] = None
        else:
            if self.changes[i] != None:
                G = self.graph_chain[i+1]
                T = G.metamodel_
                Tm_Tprime, Tm_T = self.changes[i]
                Gm, Gm_G, Gm_Tm = pullback(G.hom, Tm_T)
                if self.do_pbc :
                    Gprime, Gm_Gprime, Gprime_Tprime = pullback_complement(Gm_Tm, Tm_Tprime)
                    Gprime.metamodel_ = Gprime_Tprime.target_
                    Gprime.hom = TypedHomomorphism.from_untyped(Gprime_Tprime)
                    self.changes[i+1] = Gm_Gprime, Gm_G
                    self.graph_chain[i] = Tm_Tprime.target_
                else:
                    if self.changes[i][0] == None:
                        Gm.metamodel_ = Tm_T.source_
                        Gm.hom = Gm_Tm
                        self.graph_chain[i] = Tm_T.source_
                    else:
                        Gm.metamodel_ = Tm_Tprime.target_
                        Gm.hom = Homomorphism.compose(Tm_Tprime, Gm_Tm)
                        self.graph_chain[i] = Tm_Tprime.target_
                    self.changes[i+1] = None, Gm_G
                if i>0:
                    self.graph_chain[i].metamodel_ = self.graph_chain[i-1]
                self.changes[i] = None
                self.propagate_from(i+1)
            else:
                warnings.warn(
                    "Nothing to propagate from here !", RuntimeWarning
                )

    def propagate_all(self):
        for i in range(len(self.changes)-1, -1, -1):
            if self.changes[i] != None:
                self.propagate_from(i)
