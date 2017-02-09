"""Define GraphModeler used by graph rewriting tool."""

import networkx as nx
import warnings

from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             TypedNode,
                                             TypedHomomorphism,
                                             TypingHomomorphism,
                                             Homomorphism)
from regraph.library.rewriters import (Transformer,
                                       Rewriter)
from regraph.library.category_op import (pullback,
                                         pushout,
                                         pullback_complement)

class GraphModeler(object):
    """ Class implements a chain of graphs typed by their follower in the list.
        It allows you to build a system where each graph has a model and where
        the modification of a model can propagate to the upper graphs
    """

    def __init__(self, graph_list, homomorphisms=None, names=None, do_pbc = False, di= True):
        """ graph_list : nx.Graph list (directed or not) [G1, G2 ...]
            homomorphisms : dict list (starting with [G1->G2 ... ])
            names : str list
        """
        if len(graph_list) == 0:
            raise ValueError(
                "Can't create empty modeler"
            )
        if not homomorphisms:
            homomorphisms = []
        if not names:
            names = []

        self.graph_chain = [None for i in range(len(graph_list))]
        self.hom_chain = [None for i in range(len(graph_list))]
        
        for i in range(len(homomorphisms)):
            self.hom_chain[i+1] = homomorphisms[i]
        
        self.graph_names = [None for i in range(len(graph_list))]
        self.changes = [None for i in range(len(graph_list))]
        self.do_pbc = do_pbc
        
        if type(graph_list[0]) == TypedGraph or type(graph_list[0]) == TypedDiGraph:
            self.load_from_ty_graph(graph_list)
        
        elif type(graph_list[0]) == nx.Graph or type(graph_list[0]) == nx.DiGraph:
            self.load_from_nx_graph(graph_list)
        elif type(graph_list[0]) == str:
            self.load_from_files(graph_list, di)
        else:
            raise ValueError(
                "List should be a nx.(Di)Graphs or Typed(Di)Graphs or filenames "+\
                 "list"
            )
        self.make_names(names)


    def __str__(self):
        res = ''
        for i in range(len(self.graph_chain)-1, -1, -1):
            res += '--- Graph %s:\n\n' %\
                    (self.graph_names[i] if self.graph_names[i] is not None else i)
            res += str(self.graph_chain[i])
            res += '' if self.hom_chain[i] is None else "Mapping :\n"
            res += '' if self.hom_chain[i] is None else str(self.hom_chain[i])
            res += '\n\n'
        return res

    def __doc__(self):
        res = "Class implements a chain of graphs typed by their follower in the list. "+\
              "It allows you to build a system where each graph has a model and where "+\
              "the modification of a model can propagate to the upper graphs"
        return res

    def load_from_nx_graph(self, graph_list, hom_chain=None):
        """ Load the graph chain from a list of nx.Graphs or nx.DiGraphs
            If hom_chain (list of dicts) is given, we use is as our
            list of homomorphisms"""
        if hom_chain is not None:
            self.hom_chain = hom_chain

        typing_graph = None
        for i in range(len(graph_list)):
            directed = type(graph_list[i]) == nx.DiGraph
            if i >= len(self.hom_chain):
                raise ValueError(
                    "Homomorphism %d is not provided, cannot type your graph!" % i
                )
            typing_graph = self.make_tygraph(
                graph_list[i],
                typing_graph,
                self.hom_chain[i],
                directed
            )
            self.graph_chain[i] = typing_graph
            self.hom_chain[i] = self.graph_chain[i].hom

    def load_from_files(self, l_files, di, hom_chain=None):
        """ Load the graph chain from a list of file_paths. Each file have to be
            an xml or json file representing the graph (use
            Typed(Di)Graph.export method to generate the files)
            If hom_chain (list of dicts) is given, we use is as our
            list of homomorphisms"""
        graphs = []
        for fil in l_files:
            graphs.append(TypedDiGraph(load_file=fil) if di else TypedGraph(load_file=fil))
        self.load_from_ty_graph(graphs, hom_chain=hom_chain)


    def make_names(self, names):
        """ Updates self.names """
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

    def load_from_ty_graph(self, graph_list, hom_chain=None):
        """ Load the graph chain from a list of TypedGraphs or TypedDiGraphs
            If hom_chain (list of dicts) is given, we use is as our
            list of homomorphisms
            If neither hom_chain nor self.hom_chain are defined, we try to
            create canonic homomorphisms between our graphs (the type of a node
            is the name of its typing node in the typing graph)"""
        if hom_chain is not None:
            self.hom_chain = hom_chain
        for i in range(len(graph_list)):
            if i == 0:
                graph_list[i].metamodel_ = None
                graph_list[i].hom = None
            else:
                graph_list[i].metamodel_ = graph_list[i-1]
                if self.hom_chain[i] is None:
                    graph_list[i].hom = TypingHomomorphism.canonic(
                        graph_list[i], graph_list[i-1]
                    )
                else:
                    graph_list[i].hom = TypingHomomorphism(
                        graph_list[i], graph_list[i-1], self.hom_chain[i]
                    )
            self.graph_chain[i] = graph_list[i]
            self.hom_chain[i] = graph_list[i].hom
        return


    def init_rewriting(self, n_i):
        """ Returns a Transformer instance of the graph you want """
        if type(n_i) == int:
            g = self.get_by_id(n_i)

        elif type(n_i) == str:
            g = self.get_by_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or "+\
                 "name:str" % type(n_i)
            )
        return Transformer(g)

    def make_tygraph(self, G, T, hom, di):
        """ Create a Typed(Di)Graph representing G and typed by T with the
            homomorphism hom """
        res = TypedDiGraph(T) if di else TypedGraph(T)
        for n in G.nodes():
            if hom is None:
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
            if hom is None or T is None:
                res.hom = None
            else:
                res.hom = TypedHomomorphism(res, T, hom)
        return res

    def remove_layer(self, n_i):
        """ Removes a layer from the modeler, updates our graph_chain and our
            homomorphisms list """
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or "+\
                 "name:str" % type(n_i)
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
        """ Adds a new layer to the modeler, updates the hom chain with either
            the given Homomorphism or canonic ones """
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
        """ Get a graph by its id in the modeler """
        return self.graph_chain[n]

    def get_id_from_name(self, name):
        """ Get the id of the graph with name name in the modeler """
        for i in range(len(self.graph_names)):
            if self.graph_names[i] == name:
                return i
        raise ValueError(
            "Graph %s is not defined in the modeler"% name
        )

    def get_by_name(self, name):
        """ Get a graph by its name in the modeler """
        for i in range(len(self.graph_names)):
            if self.graph_names[i] == name:
                return self.graph_chain[i]
        raise ValueError(
            "Graph %s is not defined in the modeler" % name
        )

    def rewrite(self, n_i, L_G, trans):
        """ n_i : name or id
            L_G : L -> G homomorphism
            trans : Transformer instance
            Does a simple rewrite on the selected graph using the commands
            and stores the necessary informations to propagate that change
            If you used the Transformer class properly to generate the
            transformations, L_G = Homomorphism.identity(trans.L, trans.G)
            should work just fine
        """
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or "+\
                 "name:str" % type(n_i)
            )
        self.changes[i] = Rewriter.rewrite(L_G, trans, True)

    def rewrite_and_propagate(self, n_i, transformations):
        """ n_i : name or id
            L_G : L -> G homomorphism
            trans : Transformation string
            Does a simple rewriting on the selected graph and then propagates it
            The L -> G homomorphism used for the rewritings is identity, so
            nodes of L should be named like nodes of G
        """
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or "+\
                 "name:str" % type(n_i)
            )

        trans = Rewriter.transformer_from_command(self.get_by_id(i),
                                                  transformations)
        self.rewrite(n_i, Homomorphism.identity(trans.L, trans.G), trans)
        self.propagate_from(n_i)

    def canonical_rewrite_and_propagate(self, n_i, transformations):
        """ n_i : name or id
            transformations : Transformation string
            Does multiple simple rewritings on the selected graph using the
            canonical form of the commands and propagates those changes
            The L -> G homomorphism used for the rewritings is identity, so
            nodes of L should be named like nodes of G
        """
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or "+\
                 "name:str" % type(n_i)
            )
        changes = Rewriter.do_canonical_rewrite(self.graph_chain[i], transformations, True)
        self.chain_propagation(n_i, changes)

    def chain_propagation(self, n_i, changes_list):
        """ n_i : name or id
            changes_list : List of transformations to propagate the change
            Does the multiple propagations after the multiple simple rewritings
            of the canonical_rewrite_and_propagate function
        """
        if type(n_i) == int:
            i = n_i
        elif type(n_i) == str:
            i = self.get_id_from_name(n_i)
        else:
            raise ValueError(
                "Undefined identifier of type %s, was expecting id:int or "+\
                 "name:str" % type(n_i)
            )

        for change in changes_list:
            self.changes[i] = change
            self.propagate_from(i)

    def propagate_from(self, n_i):
        """ n_i : name or id
            Propagate the changes from the selected graph
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
            if self.changes[i][0] is not None:
                self.graph_chain[i] = self.changes[i][0].target_
            else:
                self.graph_chain[i] = self.changes[i][1].source_
            self.graph_chain[i].metamodel_ = self.graph_chain[i-1]

            self.changes[i] = None
        else:
            if self.changes[i] is not None:
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
                    if self.changes[i][0] is None:
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
        """ Propagate every possible change """
        for i in range(len(self.changes)-1, -1, -1):
            if self.changes[i] is not None:
                self.propagate_from(i)
