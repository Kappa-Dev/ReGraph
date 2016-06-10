from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism)

class GraphModeler(object):
    """ Arguments : l : nx.Graph * dict list
                       (   G     * hom  list)
                    names : string list
                    directed : bool
    """

    def __init__(self, l, names, directed=False):
        typing_graph = None
        self.rw_chain = []
        self.rw_names = []
        self.gr_homs = []
        for i in range(len(l)):
            typing_graph, gr_homs[i] = self.make_tygraph(l[i][0], typing_graph, l[i][1] directed)
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
        return self.rw_chain[n][1]

    def get_by_name(self, name):
        for i in range(self.rw_names):
            if self.rw_names[i] == name:
                return self.rw_chain[i]
        raise ValueError(
            "Graph %s is not defined in the modeler" % name
        )

    def rewrite(self, n_i, o_f):
        """ n_i : name or id
            o_f : operations (imperative) or function : rg.Rewriter -> unit
        """


    def propagate(self):
        pass
