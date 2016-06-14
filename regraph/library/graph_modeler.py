import networkx as nx

from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism)
from regraph.library.category_op import (find_PB,
                                         find_PO,
                                         find_final_PBC)

class GraphModeler(object):
    """ Arguments : l : nx.Graph * dict list
                       (   G     * hom  list)
                    names : string list
                    directed : bool
    """

    def __init__(self, l, names):
        """ l : nx.Graph list (directed or not)
            names : str list
        """
        typing_graph = None
        self.rw_chain = []
        self.rw_names = []
        self.gr_homs = []
        for i in range(len(l)):
            directed = type(l[î]) == nx.DiGraph
            typing_graph, gr_homs[i] = self.make_tygraph(l[i][0], typing_graph, l[i][1], directed)
            self.rw_chain[i] = Rewriter(typing_graph)

            if i>len(names):
                self.rw_names[i] = None
            else:
                if names[i] in self.rw_names:
                    raise ValueError(
                        "Name %s already used for another graph" % names[i]
                    )
                if type(names[i]) != str:
                    raise ValueError(
                        "Graph names have to be Strings"
                    )
                self.rw_names[i] = names[i]

    def make_tygraph(self, G, T, hom, di):
        res = TypedDiGraph(T) if di else TypedGraph(T)
        for n in G.nodes():
            res.add_node(n, hom[n], G.node[n])
        for (n1, n2) in G.edges():
            res.add_edge(n1, n2, G.edge[n1][n2])
        return res, Homomorphism(res, T, hom)

    def get_by_id(self, n):
        return self.rw_chain[n]

    def get_by_name(self, name):
        for i in range(self.rw_names):
            if self.rw_names[i] == name:
                return self.rw_chain[i]
        raise ValueError(
            "Graph %s is not defined in the modeler" % name
        )

    def rewrite(self, n_i, left_h, right_h):
        """ n_i : name or id
            ops : operations (imperative)
        """
        if type(n_i) == int:
            rew = self.get_by_id(n_i)
        elif type(n_i) == str:
            rew = self.get_by_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting int or str" %
                type(n_i)
            )

        if left_h.source_ != right_h.source_:
            raise ValueError(
                "Can't rewrite, homomorphisms don't have the same preserved part"
            )

        L_T_instances = rew.find_matching(left_h.target_)
        Gprime = rew.graph_
        for L_T in L_T_instances :
            T-, P_T-, T-_T = pullback_complement(left_h, L_T)
            G-, G-_G, G-_T- = pullback(G.hom, T-_T)
            Tprime, T-_Tprime, R_Tprime = pushout(P_T-, P_R)
            Gprime, G-_Gprime, Gprime_Tprime = pullback_complement(G-_T-, T-_Tprime)
            Gprime.metamodel_ = Tprime
            Gprime.hom = Gprime_Tprime
        return Gprime


    def propagate(self):
        pass
