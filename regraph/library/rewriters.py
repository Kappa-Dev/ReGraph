"""Define Transformer and Rewriter used by graph rewriting tool."""

import networkx as nx
from networkx.algorithms import isomorphism
import warnings

import itertools
import copy
import random

from regraph.library.parser import parser
from regraph.library.utils import (is_subdict,
                                   merge_attributes,
                                   valid_attributes,
                                   dict_sub,
                                   fold_left,
                                   keys_by_value)
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

        # We keep in memory the nodes that are in G at the beginning

        self.base_nodes = [n for n in self.G.nodes()]
        
    def __eq__(self, t):
        return(
            self.G == t.G and
            self.R == t.R and
            self.P == t.P and
            self.L == t.L and
            self.P_L_dict == t.P_L_dict and
            self.P_R_dict == t.P_R_dict)
            
    def appendToNodesNames(self,token):
        self.P = self.P.appendToNodesNames(token)
        self.R = self.R.appendToNodesNames(token)
        self.L = self.L.appendToNodesNames(token)
        self.P_R_dict = {(str(k)+"_"+str(token)):(str(v)+"_"+str(token)) for (k,v) in self.P_R_dict.items()}
        self.P_L_dict = {(str(k)+"_"+str(token)):(str(v)+"_"+str(token)) for (k,v) in self.P_L_dict.items()}
        
        
    def validNewMetamodel(self,new_meta_model):
        return(all([g.validNewMetamodel for g in [self.G,self.P,self.R,self.L]])) 
       
    def updateMetaModel(self,new_meta_model):
        self.G.updateMetamodel(new_meta_model)            
        self.P.updateMetamodel(new_meta_model)            
        self.R.updateMetamodel(new_meta_model)            
        self.L.updateMetamodel(new_meta_model)            
        
        
    def removeType(self,type_to_remove):
        self.G.removeType(type_to_remove)
        nodes_removed_from_p = self.P.removeType(type_to_remove)
        for n in nodes_removed_from_p:
            del self.P_L_dict[n]
            del self.P_R_dict[n]
        self.R.removeType(type_to_remove)            
        self.L.removeType(type_to_remove)           
        
        
    def convertType(self,old_type,new_type):
        self.G.convertType(old_type,new_type)
        self.P.convertType(old_type,new_type)
        self.R.convertType(old_type,new_type)
        self.L.convertType(old_type,new_type)
        
        
    def removeEdgesByType(self,source_type,target_type): 
        self.G.removeEdgesByType(source_type,target_type) 
        self.P.removeEdgesByType(source_type,target_type) 
        self.R.removeEdgesByType(source_type,target_type) 
        self.L.removeEdgesByType(source_type,target_type) 
       
     
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
        return "A Tranformer instance is an instance of P, L and R graphs "+\
                "and P->L, P->R homomorphisms. It allows you "+\
                "stack changes and apply them later on thanks to the Rewriter "+\
                "or the GraphModeler class"

    # Canonic operations

    def get(self):
        """ Gives you the homomorphisms P->L and P->R """
        return (Homomorphism(self.P, self.L, self.P_L_dict),
                Homomorphism(self.P, self.R, self.P_R_dict))

    # Basic operations

    def add_node(self, node_id, node_type, attrs=None):
        """ Adds node to the graph """
        if not node_id in self.R.nodes():
            self.R.add_node(node_id, node_type, attrs)
        else :
            raise ValueError("Node already in R")

    def merge_nodes(self, n1, n2, node_name=None):
        """ Merges two nodes of the graph """
        # If n1 and n2 are in base_nodes, we add them to the graphs and
        # we map them to the merged equivalent in R
        # If one of them is not in base_nodes, the nodes are already in R and
        # we only have to merge them in R
        if n1 in self.base_nodes:
            if not n1 in self.P.nodes():
                self.P.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
            if not n1 in self.L.nodes():
                self.L.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_L_dict[n1] = n1
            self.base_nodes.remove(n1)

        if n2 in self.base_nodes:
            if not n2 in self.P.nodes():
                self.P.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
            if not n2 in self.L.nodes():
                self.L.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_L_dict[n2] = n2
            self.base_nodes.remove(n2)

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

        if n1 in self.P_R_dict.keys():
            if n2 in self.P_R_dict.keys():
                new_name = self.R.merge_nodes([self.P_R_dict[n1], self.P_R_dict[n2]],
                                   node_name=node_name)
            else:
                new_name = self.R.merge_nodes([self.P_R_dict[n1], n2],
                                   node_name=node_name)
        else:
            if n2 in self.P_R_dict.keys():
                new_name = self.R.merge_nodes([n1, self.P_R_dict[n2]],
                                   node_name=node_name)
            else:
                new_name = self.R.merge_nodes([n1, n2],
                                   node_name=node_name)

        # We update the mapping of the nodes in P_R

        if n1 in self.P_R_dict.keys():
            pred_n1 = keys_by_value(self.P_R_dict, self.P_R_dict[n1])
        else:
            pred_n1 = keys_by_value(self.P_R_dict, n1)
        for n11 in pred_n1:
            self.P_R_dict[n11] = new_name
        if n2 in self.P_R_dict.keys():
            pred_n2 = keys_by_value(self.P_R_dict, self.P_R_dict[n2])
        else:
            pred_n2 = keys_by_value(self.P_R_dict, n2)
        for n21 in pred_n2:
            self.P_R_dict[n21] = new_name

        return new_name


    def remove_node(self, n):
        """ Removes a node in the graph """
        # If it is a base node, we have to add it in L and remove it from P,
        # else we have to clear every occurence of the node in the graphs
        if n in self.base_nodes:
            if not n in self.L.nodes():
                self.L.add_node(n, self.G.node[n].type_, self.G.node[n].attrs_)
            if n in self.R.nodes():
                self.R.remove_node(n)
            if n in self.P.nodes():
                self.P.remove_node(n)
            self.base_nodes.remove(n)
        else:
            if n in self.R.nodes():
                self.R.remove_node(n)
            if n in self.P.nodes():
                self.P.remove_node(n)
        if n in self.P_L_dict.keys():
            del self.P_L_dict[n]
        if n in self.P_R_dict.keys():
            del self.P_R_dict[n]
        if n in self.P_R_dict.values():
            pred_n = keys_by_value(self.P_R_dict, n)
            for n0 in pred_n:
                if n0 in self.P.nodes():
                    self.P.remove_node(n0)
                if n0 in self.P_R_dict.keys():
                    del self.P_R_dict[n0]
                if n0 in self.P_L_dict.keys():
                    del self.P_L_dict[n0]


    def clone_node(self, n, node_name=None):
        """ Clones a node of the graph """
        # If it is a base_node we have to create the clone in P and map it to
        # the original one in L, else we have to clone the added node : if it
        # is a clone we have to add a new clone in P and map it in L, if it is
        # an added or a merged node we have to duplicate it in R.
        # We can't clone a merged node in a single step and keep valid
        # homomorphisms (we can't map a node in P to two nodes in R) so we just
        # clone the result node in R and it will be added in the resulting graph
        if n in self.base_nodes:
            if not n in self.P.nodes():
                self.P.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
            if not n in self.L.nodes():
                self.L.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_L_dict[n] = n

            if not n in self.R.nodes():
                self.R.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_R_dict[n] = n

            if node_name is None:
                i = 1
                node_name = str(n)+str(i)
                while node_name in self.G.nodes() or\
                      node_name in self.R.nodes() or\
                      node_name in self.P.nodes():
                    i+=1
                    node_name = str(n)+str(i)

            if not node_name in self.P.nodes():
                self.P.add_node(node_name,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)

            self.R.add_node(node_name,
                            self.G.node[n].type_,
                            self.G.node[n].attrs_)
            self.P_L_dict[node_name] = n
            self.P_R_dict[node_name] = node_name

            # We add to the clone all the edges we added to the original node
            # before the cloning

            for neigh in self.R.in_edges(self.P_R_dict[n]):
                self.R.add_edge(neigh[0],
                                node_name,
                                self.R.get_edge(neigh[0],
                                                n))
            for neigh in self.R.out_edges(self.P_R_dict[n]):
                self.R.add_edge(node_name,
                                neigh[1],
                                self.R.get_edge(n,
                                                neigh[1]))
        elif n in self.P.nodes():
            # If it's not a base node but it's in P, it's a clone, we have to
            # clone it again
            if node_name is None:
                i = 1
                node_name = str(n)+str(i)
                while node_name in self.G.nodes() or\
                      node_name in self.R.nodes() or\
                      node_name in self.P.nodes():
                    i+=1
                    node_name = str(n)+str(i)

            self.P.add_node(node_name,
                            self.P.node[n].type_,
                            self.P.node[n].attrs_)
            self.R.add_node(node_name,
                            self.P.node[n].type_,
                            self.P.node[n].attrs_)
            self.P_L_dict[node_name] = self.P_L_dict[n]
            self.P_R_dict[node_name] = node_name

            # We update the new edges like before

            for neigh in self.R.in_edges(self.P_R_dict[n]):
                self.R.add_edge(neigh[0],
                                node_name,
                                self.R.get_edge(neigh[0],
                                                n))
            for neigh in self.R.out_edges(self.P_R_dict[n]):
                self.R.add_edge(node_name,
                                neigh[1],
                                self.R.get_edge(n,
                                                neigh[1]))
        else:
            # Else it's an added node or a merged node, we duplicate the node in
            # R
            if node_name is None:
                i = 1
                node_name = str(n)+str(i)
                while node_name in self.G.nodes() or\
                      node_name in self.R.nodes() or\
                      node_name in self.P.nodes():
                    i+=1
                    node_name = str(n)+str(i)

            self.R.clone_node(n, node_name)

    def add_edge(self, n1, n2, attrs=None):
        """ Adds an edge in the graph """
        if n1 in self.base_nodes and n2 in self.base_nodes:
            # If both nodes are base nodes, we just have to add them in the
            # graphs and add the edge between them in R
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
                self.R.add_node(n1,
                                self.G.node[n1].type_,
                                self.G.node[n1].attrs_)
                self.P_R_dict[n1] = n1

            if not n2 in self.R.nodes():
                self.R.add_node(n2,
                                self.G.node[n2].type_,
                                self.G.node[n2].attrs_)
                self.P_R_dict[n2] = n2

            if (self.P_R_dict[n1], self.P_R_dict[n2]) in self.R.edges():
                warnings.warn(
                    "Edge %s-%s already exists, "+\
                     "nothing has been changed!" %
                        (str(n1), str(n2)), RuntimeWarning
                )
            else:
                self.R.add_edge(self.P_R_dict[n1],self.P_R_dict[n2], attrs)


        elif n1 in self.base_nodes or n2 in self.base_nodes:
            # If one of them isn't a base node, we add the one in G in all
            # the graphs
            in_G, nin_G = (n1, n2) if n1 in self.base_nodes else (n2, n1)

            if not nin_G in self.R.nodes() and not nin_G in self.P.nodes():
                raise ValueError(
                    "Node %s doesn't exist" % nin_G
                )

            if not in_G in self.P.nodes():
                self.P.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
            if not in_G in self.L.nodes():
                self.L.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
                self.P_L_dict[in_G] = in_G
            if not in_G in self.R.nodes():
                self.R.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
                self.P_R_dict[in_G] = in_G

            # We then add the edge in R

            if n1 in self.base_nodes:
                if (self.P_R_dict[n1], n2) not in self.R.edges():
                    self.R.add_edge(self.P_R_dict[n1],
                                    n2,
                                    attrs)
            else:
                if (n1, self.P_R_dict[n2]) not in self.R.edges():
                    self.R.add_edge(n1,
                                    self.P_R_dict[n2],
                                    attrs)
        else:
            # Else both nodes have been created, they're either added, merged
            # or cloned nodes and we add the edge in R
            if not n1 in self.R.nodes():
                if n1 in self.P.nodes():
                    self.R.add_node(n1,
                                    self.P.node[n1].type_,
                                    self.P.node[n1].attrs_)
                    self.P_R_dict[n1] = n1
                else:
                    raise ValueError(
                        "Node %s doesn't exist" % n1
                    )

            if not n2 in self.R.nodes():
                if n2 in self.P.nodes():
                    self.R.add_node(n2,
                                    self.P.node[n2].type_,
                                    self.P.node[n2].attrs_)
                    self.P_R_dict[n2] = n2
                else:
                    raise ValueError(
                        "Node %s doesn't exist" % n2
                    )

            self.R.add_edge(n1, n2, attrs)

    def remove_edge(self, n1, n2):
        """ Removes edge from the graph """
        if n1 in self.base_nodes and n2 in self.base_nodes:
            # Both nodes are base nodes
            if not (n1, n2) in self.G.edges() and\
               not (n1, n2) in self.R.edges():
                raise ValueError(
                    "Edge %s-%s doesn't exist" %
                    (n1, n2)
                )

            if n1 in self.P_R_dict.keys() and n2 in self.P_R_dict.keys():
                if (self.P_R_dict[n1], self.P_R_dict[n2]) in self.R.edges():
                    # if the edge is in R, it have been added before, we only have
                    # to delete it from R and from P if it is in P
                    self.R.remove_edge(self.P_R_dict[n1], self.P_R_dict[n2])
                    pred_n1 = keys_by_value(self.P_R_dict, n1)
                    pred_n2 = keys_by_value(self.P_R_dict, n2)
                    for n11 in pred_n1:
                        for n21 in pred_n2:
                            if (n11, n21) in self.P.edges():
                                self.P.remove_edge(n11, n21)
                    return

            # Else we add the nodes in the graphs and we put an edge between
            # them in L

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

            if not (self.P_L_dict[n1], self.P_L_dict[n2]) in self.L.edges():
                self.L.add_edge(self.P_L_dict[n1],
                                self.P_L_dict[n2],
                                self.G.get_edge(self.P_L_dict[n1],
                                                self.P_L_dict[n2]))

            # If one of the two nodes have been cloned before, we need to
            # preserve the edges of the other clones so we add those edges
            # in P, L and R so the only one to disappear is the one between
            # our two nodes
            other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n1])
            if len(other_clones) > 1:
                for n3 in other_clones:
                    if n3 != n1:
                        self.P.add_edge(n3,
                                        n2,
                                        self.G.get_edge(self.P_L_dict[n3],
                                                        self.P_L_dict[n2]))
                        self.L.add_edge(self.P_L_dict[n3],
                                        self.P_L_dict[n2],
                                        self.G.get_edge(self.P_L_dict[n3],
                                                        self.P_L_dict[n2]))
                        self.R.add_edge(self.P_R_dict[n3],
                                        self.P_R_dict[n2],
                                        self.G.get_edge(self.P_L_dict[n3],
                                                        self.P_L_dict[n2]))
            other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n2])
            if len(other_clones) > 1:
                for n3 in other_clones:
                    if n3 != n2:
                        self.P.add_edge(n1,
                                        n3,
                                        self.G.get_edge(self.P_L_dict[n1],
                                                        self.P_L_dict[n3]))
                        self.L.add_edge(self.P_L_dict[n1],
                                        self.P_L_dict[n3],
                                        self.G.get_edge(self.P_L_dict[n1],
                                                        self.P_L_dict[n3]))
                        self.R.add_edge(self.P_R_dict[n1],
                                        self.P_R_dict[n3],
                                        self.G.get_edge(self.P_L_dict[n1],
                                                        self.P_L_dict[n3]))

        elif n1 in self.base_nodes or n2 in self.base_nodes:
            # If one of them is the result of a clone, a merge or an add
            if n1 in self.base_nodes:
                in_G = n1
                nin_G = n2
            else:
                in_G = n2
                nin_G = n1

            if not in_G in self.L.nodes():
                self.L.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
                self.P_L_dict[in_G] = in_G
            if not in_G in self.P.nodes():
                self.P.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
            if not in_G in self.P_R_dict.keys():
                self.R.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
                self.P_R_dict[in_G] = in_G

            if nin_G in self.P_L_dict.keys():
                # That means nin_G is a clone
                if n1 in self.P_R_dict.keys() and n2 in self.P_R_dict.keys():
                    if (self.P_R_dict[n1], self.P_R_dict[n2]) in self.R.edges():
                        # If the edge is in R, it's an added edge so we remove
                        # it from R
                        self.R.remove_edge(n1,n2)
                        pred_n1 = keys_by_value(self.P_R_dict, n1)
                        pred_n2 = keys_by_value(self.P_R_dict, n2)
                        for n11 in pred_n1:
                            for n21 in pred_n2:
                                if (n11, n21) in self.P.edges():
                                    self.P.remove_edge(n11, n21)
                        return

                # Else, the edge came from G, or doesn't exist

                if not (self.P_L_dict[n1], self.P_L_dict[n2]) in self.G.edges():
                    raise ValueError("""Can't add edge %s-%s because edge %s-%s
                                     doesn't exist in graph""" %
                                     (n1, n2, self.P_L_dict[n1], self.P_L_dict[n2]))

                # As we did before, we have to preserve the edges of the
                # other clones
                if n1 in self.P_L_dict.keys():
                    other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n1])
                    if len(other_clones) > 1:
                        for n3 in other_clones:
                            if n3 != n1:
                                self.P.add_edge(n3,
                                                n2,
                                                self.G.get_edge(self.P_L_dict[n3],
                                                                self.P_L_dict[n2]))
                                self.L.add_edge(self.P_L_dict[n3],
                                                self.P_L_dict[n2],
                                                self.G.get_edge(self.P_L_dict[n3],
                                                                self.P_L_dict[n2]))
                                self.R.add_edge(self.P_R_dict[n3],
                                                self.P_R_dict[n2],
                                                self.G.get_edge(self.P_L_dict[n3],
                                                                self.P_L_dict[n2]))

                if n2 in self.P_L_dict.keys():
                    other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n2])
                    if len(other_clones) > 1:
                        for n3 in other_clones:
                            if n3 != n2:
                                self.P.add_edge(n1,
                                                n3,
                                                self.G.get_edge(self.P_L_dict[n1],
                                                                self.P_L_dict[n3]))
                                self.L.add_edge(self.P_L_dict[n1],
                                                self.P_L_dict[n3],
                                                self.G.get_edge(self.P_L_dict[n1],
                                                                self.P_L_dict[n3]))
                                self.R.add_edge(self.P_R_dict[n1],
                                                self.P_R_dict[n3],
                                                self.G.get_edge(self.P_L_dict[n1],
                                                                self.P_L_dict[n3]))

                self.L.add_edge(self.P_L_dict[n1],
                                self.P_L_dict[n2],
                                self.G.get_edge(self.P_L_dict[n1],
                                                self.P_L_dict[n2]))

        else:
            # Else both nodes are new
            if (n1, n2) in self.R.edges():
                # If the edge is in R, we can remove it (add or merge)
                self.R.remove_edge(n1, n2)
                pred_n1 = keys_by_value(self.P_R_dict, n1)
                pred_n2 = keys_by_value(self.P_R_dict, n2)
                for n11 in pred_n1:
                    for n21 in pred_n2:
                        if (n11, n21) in self.P.edges():
                            self.P.remove_edge(n11, n21)
            else:
                # Else one of them is a clone and the edge came from that
                if (n1, n2) in self.P.edges():
                    self.P.remove_edge(n1, n2)
                else:
                    if n1 in self.P_L_dict.keys():
                        clone_n1 = keys_by_value(self.P_L_dict, self.P_L_dict[n1])
                    else:
                        clone_n1 = []
                    if n2 in self.P_L_dict.keys():
                        clone_n2 = keys_by_value(self.P_L_dict, self.P_L_dict[n2])
                    else:
                        clone_n2 = []

                    for n1_ in clone_n1:
                        for n2_ in clone_n2:
                            if n1_ != n1 and n2 != n2:
                                self.P.add_edge(n1_,
                                                n2_,
                                                self.G.get_edge(self.P_L_dict[n1_],
                                                                self.P_L_dict[n2_]))
                                self.L.add_edge(self.P_L_dict[n1_],
                                                self.P_L_dict[n2_],
                                                self.P.get_edge(self.P_L_dict[n1],
                                                                self.P_L_dict[n2]))
                                self.R.add_edge(self.P_R_dict[n1_],
                                                self.P_R_dict[n2_],
                                                self.P.get_edge(self.P_L_dict[n1],
                                                                self.P_L_dict[n2]))

    def add_node_attrs(self, n, attrs):
        """ Adds node attributes to a node in the graph """
        # The attributes are added in R
        if n in self.base_nodes:
            if not n in self.P.nodes():
                self.P.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)

            if not n in self.L.nodes():
                self.L.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_L_dict[n] = n
            if not n in self.R.nodes():
                self.R.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_R_dict[n] = n

        if n in self.P_R_dict.keys():
            self.R.add_node_attrs(self.P_R_dict[n], attrs)
        elif n in self.R.nodes():
            self.R.add_node_attrs(n, attrs)
        else:
            raise ValueError(
                "Node %s doesn't exist" % n
            )


    def add_edge_attrs(self, n1, n2, attrs):
        """ Adds edge attributes to an edge in the graph """
        # Same idea as before, but a little more complex since we have two nodes
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
                        "Edge %s-%s doesn't exist, please create it before adding "+\
                         "attributes!" %
                            (str(n1), str(n2))
                    )

    def remove_node_attrs(self, n, attrs):
        """ Remove nodes attributes from a node in the graph """
        # Same idea as in the remove_node function but we remove attributes
        # instead of the node itself
        if n in self.base_nodes:
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
                self.P_L_dict[n] = n

            if not n in self.P.nodes():
                self.P.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
            self.P.remove_node_attrs(n, attrs)
        else:
            if n in self.R.nodes():
                self.R.remove_node_attrs(n, attrs)
                pred_n = keys_by_value(self.P_R_dict, n)
                if len(pred_n) > 0:
                    for pred_n_ in pred_n:
                        self.P.remove_node_attrs(pred_n_, attrs)

            if n in self.P.nodes():
                self.P.remove_node_attrs(n, attrs)


    def remove_edge_attrs(self, n1, n2, attrs):
        """ Removes edge attributes from an edge in the graph """
        # Same idea as in the remove_edge function but we remove attributes
        # instead of the edge itself
        if n1 in self.base_nodes and n2 in self.base_nodes:
            if not (n1, n2) in self.G.edges() and\
               not (n1, n2) in self.R.edges():
                raise ValueError(
                    "Edge %s-%s doesn't exist" %
                    (n1, n2)
                )

            if n1 in self.P_R_dict.keys() and n2 in self.P_R_dict.keys():
                if (self.P_R_dict[n1], self.P_R_dict[n2]) in self.R.edges():
                    self.R.remove_edge_attrs(n1, n2, attrs)
                    pred_n1 = keys_by_value(self.P_R_dict, n1)
                    pred_n2 = keys_by_value(self.P_R_dict, n2)
                    for n11 in pred_n1:
                        for n21 in pred_n2:
                            if (n11, n21) in self.P.edges():
                                self.P.remove_edge_attrs(n11, n21, attrs)
                    return

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

            if not (self.P_L_dict[n1], self.P_L_dict[n2]) in self.L.edges():
                self.P.add_edge(self.P_L_dict[n1],
                                self.P_L_dict[n2],
                                self.G.get_edge(self.P_L_dict[n1],
                                                self.P_L_dict[n2]))
                self.L.add_edge(self.P_L_dict[n1],
                                self.P_L_dict[n2],
                                self.G.get_edge(self.P_L_dict[n1],
                                                self.P_L_dict[n2]))
                self.R.add_edge(self.P_L_dict[n1],
                                self.P_L_dict[n2],
                                self.G.get_edge(self.P_L_dict[n1],
                                                self.P_L_dict[n2]))
                self.P.remove_edge_attrs(n1, n2, attrs)
                self.R.remove_edge_attrs(self.P_R_dict[n1],
                                         self.P_R_dict[n2],
                                         attrs)

            other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n1])
            if len(other_clones) > 1:
                for n3 in other_clones:
                    self.P.add_edge(n3,
                                    n2,
                                    self.G.get_edge(self.P_L_dict[n3],
                                                    self.P_L_dict[n2]))
                    self.L.add_edge(self.P_L_dict[n3],
                                    self.P_L_dict[n2],
                                    self.G.get_edge(self.P_L_dict[n3],
                                                    self.P_L_dict[n2]))
                    self.R.add_edge(self.P_R_dict[n3],
                                    self.P_R_dict[n2],
                                    self.G.get_edge(self.P_L_dict[n3],
                                                    self.P_L_dict[n2]))
            other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n2])
            if len(other_clones) > 1:
                for n3 in other_clones:
                    self.P.add_edge(n1,
                                    n3,
                                    self.G.get_edge(self.P_L_dict[n1],
                                                    self.P_L_dict[n3]))
                    self.L.add_edge(self.P_L_dict[n1],
                                    self.P_L_dict[n3],
                                    self.G.get_edge(self.P_L_dict[n1],
                                                    self.P_L_dict[n3]))
                    self.R.add_edge(self.P_R_dict[n1],
                                    self.P_R_dict[n3],
                                    self.G.get_edge(self.P_L_dict[n1],
                                                    self.P_L_dict[n3]))

        elif n1 in self.base_nodes or n2 in self.base_nodes:
            if n1 in self.base_nodes:
                in_G = n1
                nin_G = n2
            else:
                in_G = n2
                nin_G = n1

            if not in_G in self.L.nodes():
                self.L.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
                self.P_L_dict[in_G] = in_G
            if not in_G in self.P.nodes():
                self.P.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
            if not in_G in self.P_R_dict.keys():
                self.R.add_node(in_G,
                                self.G.node[in_G].type_,
                                self.G.node[in_G].attrs_)
                self.P_R_dict[in_G] = in_G

            if nin_G in self.P_L_dict.keys():
                if n1 in self.P_R_dict.keys() and n2 in self.P_R_dict.keys():
                    if (self.P_R_dict[n1], self.P_R_dict[n2]) in self.R.edges():
                        self.R.remove_edge_attrs(n1,n2, attrs)
                        pred_n1 = keys_by_value(self.P_R_dict, n1)
                        pred_n2 = keys_by_value(self.P_R_dict, n2)
                        for n11 in pred_n1:
                            for n21 in pred_n2:
                                if (n11, n21) in self.P.edges():
                                    self.P.remove_edge_attrs(n11, n21, attrs)
                        return

                if not (self.P_L_dict[n1], self.P_L_dict[n2]) in self.G.edges():
                    raise ValueError("""Can't add edge %s-%s because edge %s-%s
                                     doesn't exist in graph""" %
                                     (n1, n2, self.P_L_dict[n1], self.P_L_dict[n2]))

                if n1 in self.P_L_dict.keys():
                    other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n1])
                    if len(other_clones) > 1:
                        for n3 in other_clones:
                            self.P.add_edge(n3,
                                            n2,
                                            self.G.get_edge(self.P_L_dict[n3],
                                                            self.P_L_dict[n2]))
                            self.L.add_edge(self.P_L_dict[n3],
                                            self.P_L_dict[n2],
                                            self.G.get_edge(self.P_L_dict[n3],
                                                            self.P_L_dict[n2]))
                            self.R.add_edge(self.P_R_dict[n3],
                                            self.P_R_dict[n2],
                                            self.G.get_edge(self.P_L_dict[n3],
                                                            self.P_L_dict[n2]))

                if n2 in self.P_L_dict.keys():
                    other_clones = keys_by_value(self.P_L_dict, self.P_L_dict[n2])
                    if len(other_clones) > 1:
                        for n3 in other_clones:
                            self.P.add_edge(n1,
                                            n3,
                                            self.G.get_edge(self.P_L_dict[n1],
                                                            self.P_L_dict[n3]))
                            self.L.add_edge(self.P_L_dict[n1],
                                            self.P_L_dict[n3],
                                            self.G.get_edge(self.P_L_dict[n1],
                                                            self.P_L_dict[n3]))
                            self.R.add_edge(self.P_R_dict[n1],
                                            self.P_R_dict[n3],
                                            self.G.get_edge(self.P_L_dict[n1],
                                                            self.P_L_dict[n3]))

                self.P.remove_edge_attrs(n1,
                                         n2,
                                         attrs)

        else:
            if (n1, n2) in self.R.edges():
                self.R.remove_edge_attrs(n1, n2, attrs)
                pred_n1 = keys_by_value(self.P_R_dict, n1)
                pred_n2 = keys_by_value(self.P_R_dict, n2)
                for n11 in pred_n1:
                    for n21 in pred_n2:
                        if (n11, n21) in self.P.edges():
                            self.P.remove_edge_attrs(n11, n21, attrs)
            else:
                if (n1, n2) in self.P.edges():
                    self.P.remove_edge_attrs(n1, n2, attrs)
                else:
                    if n1 in self.P_L_dict.keys():
                        clone_n1 = keys_by_value(self.P_L_dict, self.P_L_dict[n1])
                    else:
                        clone_n1 = []
                    if n2 in self.P_L_dict.keys():
                        clone_n2 = keys_by_value(self.P_L_dict, self.P_L_dict[n2])
                    else:
                        clone_n2 = []

                    for n1_ in clone_n1:
                        for n2_ in clone_n2:
                                self.P.add_edge(n1_,
                                                n2_,
                                                self.G.get_edge(self.P_L_dict[n1_],
                                                                self.P_L_dict[n2_]))
                                self.L.add_edge(self.P_L_dict[n1_],
                                                self.P_L_dict[n2_],
                                                self.G.get_edge(self.P_L_dict[n1_],
                                                                self.P_L_dict[n2_]))
                                self.R.add_edge(self.P_R_dict[n1_],
                                                self.P_R_dict[n2_],
                                                self.G.get_edge(self.P_L_dict[n1_],
                                                                self.P_L_dict[n2_]))
                    self.P.remove_edge_attrs(n1,
                                             n2,
                                             attrs)
                    self.R.remove_edge_attrs(self.P_R_dict[n1],
                                             self.P_R_dict[n2],
                                             attrs)


    # Advanced operations

    def merge_edges(self, e1, e2, name_n1=None, name_n2=None):
        """ Merges two edges """
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
        """ Clones an edge """
        self.clone_node(n1, new_n1)
        self.clone_node(n2, new_n2)
        self.R.add_edge(new_n1, new_n2)

    def relabel_node(self, n, node_name):
        """ Relabels a node """
        if n in self.base_nodes:
            if not n in self.P.nodes():
                self.P.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
            if not n in self.L.nodes():
                self.L.add_node(n,
                                self.G.node[n].type_,
                                self.G.node[n].attrs_)
                self.P_L_dict[n] = n
            self.base_nodes.remove(n)

        if n in self.R.nodes():
            self.R.relabel_node(n, node_name)
        else:
            self.R.add_node(node_name,
                            self.P.node[n].type_,
                            self.P.node[n].attrs_)
            self.P_R_dict[n] = node_name
        pred = keys_by_value(self.P_R_dict, n)
        for n0 in pred:
            self.P_R_dict[n0] = node_name


    def merge_nodes_list(self, l, node_name=None):
        """ Merge a list of nodes """
        if len(l)>1:
            node_name = self.merge_nodes(l[0], l[1], node_name)
            for i in range(2, len(l)):
                node_name = self.merge_nodes(l[i], node_name, node_name)
        else:
            warnings.warn(
                "Cannot merge less than one node, list %s is empty" %
                (str(l)), RuntimeWarning
            )


class Rewriter:
    """Class implements the transformation on the graph."""

    def __init__(self, graph=None):
        """Initialize Rewriter object with input graph."""
        self.graph_ = graph
        self.parser_ = parser
        return

    def __doc__(self):
        return "A Rewriter instance alows you to do a horizontal rewrite on "+\
                "a single graph, it also gives the needed informations (the "+\
                "G- -> G and G- -> Gprime homomorphisms) to propagate that "+\
                "change in the GraphModeler"

    @staticmethod
    def rewrite_simple(trans, get_details=False):
       return(Rewriter.rewrite(Homomorphism.identity(trans.L,trans.G),trans,get_details))
       
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

        for n in Gm.nodes():
            n2 = Gm_G[n]
            if graph.node[n2].attributes_typing:
                Gprime.node[Gm_Gprime[n]].attributes_typing = copy.deepcopy(graph.node[n2].attributes_typing)

        Gprime.metamodel_ = graph.metamodel_
        if graph.graph_attr:
            Gprime.graph_attr = copy.deepcopy(graph.graph_attr) 
        Gprime.hom = TypedHomomorphism.canonic(Gprime, graph.metamodel_)
        if get_details:
            return Gm_Gprime, Gm_G
        else:
            return Gprime

    @staticmethod
    def do_canonical_rewrite(G, transformations, get_details=False):
        """ Does a simple rewriting by decomposing the transformations string
            into a list of canonical transformations strings """
        di = type(G) == TypedDiGraph
        trans_list = Rewriter.make_canonical_commands(G, transformations, di)
        return Rewriter.chain_rewrite(G, trans_list, get_details)

    def do_rewrite(G, transformations, get_details=False):
        trans = Rewriter.transformer_from_command(G, transformations)
        L_G = Homomorphism.identity(trans.L, trans.G)
        return Rewriter.rewrite(L_G, trans, get_details)

    @staticmethod
    def chain_rewrite(G, trans_list, get_details=False):
        """ Does multiple simple rewritings on G given a list of transformations """
        res = []
        for transformation in trans_list:
            if get_details:
                trans = Rewriter.transformer_from_command(res[-1][0].target_ if res != [] else G, transformation)
                rw_res = Rewriter.rewrite(Homomorphism.identity(trans.L,
                                                                trans.G),
                                          trans,
                                          get_details)
                res.append(rw_res)
            else:
                trans = Rewriter.transformer_from_command(res[-1] if res != [] else G, transformation)
                rw_res = Rewriter.rewrite(Homomorphism.identity(trans.L,
                                                                trans.G),
                                          trans,
                                          get_details)
                res = [rw_res]
        if get_details:
            return res
        else:
            return res[0]


    @staticmethod
    def find_matching(graph, pattern, ignore_attrs = False):
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
                    # if ignore_attrs or is_subdict(pattern.node[pattern_node].attrs_,
                    #                                     g.node[node].attrs_):
                    #     matching_nodes.add(node)
                    if ignore_attrs or valid_attributes(pattern.node[pattern_node].attrs_,
                                                        g.node[node]):
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
                # if not ignore_attrs and not is_subdict(pattern.node[pattern_node].attrs_, subgraph.node[node].attrs_):
                if not ignore_attrs and not valid_attributes(pattern.node[pattern_node].attrs_, subgraph.node[node]):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.get_edge(edge[0], edge[1])
                    target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
                    if not ignore_attrs and not is_subdict(pattern_attrs, target_attrs):
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

    def apply_rule(self, L_G, trans):

        left_h, right_h = trans.get()

        # check left_h.source == right_h.source
        if left_h.source_.nodes() != right_h.source_.nodes():
            raise ValueError("Preserving part does not match!")
        if left_h.source_.edges() != right_h.source_.edges():
            raise ValueError("Preserving part does not match!")
        instance = L_G.mapping_
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
            """ Picks random attributes from attrs using the probabilities in
                the main function arguments """
            if attrs is None:
                return {}

            new_attrs = {}
            for k,v in attrs.items():
                if random.random() <= p_attrs:
                    value = []
                    for val in v:
                        if random.random() <= p_attrs_value:
                            value.append(val)
                    new_attrs[k] = set(value)
            keys_to_remove = []
            for k,v in new_attrs.items():
                if v == set():
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                new_attrs.pop(k)
            return new_attrs

        trans = []
        env = graph.copy()
        base_nodes = [n for n in graph.nodes()]
        if graph.metamodel_ is None:
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
            """ Picks a node in the graph if possible """
            if len(base_nodes) > 0:
                return random.sample(base_nodes, 1)[0]
            else:
                return None

        def pick_nodes():
            """ Picks multiple node (a random number following a gaussian law
                with parameters merge_prop_av and merge_prop_dev) if possible """
            if env.metamodel_ is None:
                ty = random.choice([None, "anything"])
            else:
                ty = pick_type()
            node_list = [n for n in base_nodes if env.node[n].type_ == ty]
            n = abs(int(random.gauss(merge_prop_av*len(node_list),
                                     merge_prop_dev*len(node_list))))
            while n < 2 and len(node_list) > 5:
                n = abs(int(random.gauss(merge_prop_av*len(node_list),
                                         merge_prop_dev*len(node_list))))
            if n < 2:
                return []
            res = []
            for node in random.sample(node_list, n):
                res.append(node)
            return res

        def pick_edge():
            """ Picks an existing edge if possible """
            if len(env.edges()) > 0 and len(base_nodes) > 1:
                edge = random.sample(env.edges(), 1)[0]
                if edge[0] in base_nodes and edge[1] in base_nodes:
                    return edge
            return None,None

        def pick_new_edge():
            """ Picks two nodes that can have an edge between them and don't yet
                if possible """
            i = 500
            while i > 0:
                n1 = pick_node()
                n2 = pick_node()
                if n1 is not None and n2 is not None:
                    if env.metamodel_ is None or\
                       (env.node[n1].type_, env.node[n2].type_) in env.metamodel_.edges() and\
                       (n1, n2) not in env.edges() and n1 != n2:
                        return (n1, n2)
                    else:
                        i-=1
            return None

        def pick_type():
            """ Picks a type """
            return random.sample(types, 1)[0]

        def pick_attrs_from(node):
            """ Picks random attrs from the attrs of node """
            return rand_attrs(env.node[node].attrs_)

        def pick_attrs_for(node):
            """ Picks random attrs from the attrs of the typing node of node """
            if graph.metamodel_ is None:
                return {}
            else:
                return rand_attrs(graph.metamodel_.node[env.node[node].type_].attrs_)

        def pick_edge_attrs_from(n1, n2):
            """ Picks random attrs from the attrs of edge """
            return rand_attrs(env.get_edge(n1, n2))

        def pick_edge_attrs_for(n1, n2):
            """ Picks random attrs from the attrs of the typing edge of edge """
            if env.metamodel_ is None:
                return {}
            else:
                return rand_attrs(env.metamodel_.get_edge(
                    env.node[n1].type_,
                    env.node[n2].type_
                ))

        def pick_name():
            """ Picks a node_name that isn't in the graph yet """
            i = random.randint(0, 500)
            if len(env.nodes()) > 1:
                generated_name = ".".join(random.sample(env.nodes(), 2))
            else:
                generated_name = "newNode"+str(i)
            while str(generated_name) in env.nodes():
                i = random.randint(0, 500)
                if len(env.nodes()) > 1:
                    generated_name = ".".join(random.sample(env.nodes(), 2))
                else:
                    generated_name = "newNode"+str(i)
            return str(generated_name)

        def pick_method():
            """ Picks a method to use for merging """
            return random.choice(["UNION", "INTERSECTION"])

        def add_req(op, s):
            """ Updates the transformation list with a required argument """
            op += s
            return op

        def add_opt(op, s):
            """ Updates the transformation list with an optional argument """
            if random.random() <= p_opt:
                op += s
                return True, op
            else:
                return False, op

        # We pick a random operation each time and try to do it

        while len(trans) < n:
            op = random.choice(actions)
            if op == "CLONE":
                node = pick_node()
                if node is None or "_" in node:
                    continue
                name = pick_name()

                op = add_req(op, " '%s'" % str(node))
                opt,op = add_opt(op, " AS '%s'" % str(name))
                if not opt:
                    name = None
                else:
                    base_nodes.append(name)

                env.clone_node(node, name)
                trans.append(op)
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
                else:
                    base_nodes.append(new_name)
                opt,op = add_opt(op, " EDGES "+str(edges))
                if not opt:
                    edges = "UNION"

                if nodes != []:
                    env.merge_nodes(nodes,
                                method.lower(),
                                new_name,
                                edges.lower())
                for node in nodes:
                    base_nodes.remove(node)

                trans.append(op)
            elif op == "ADD_NODE":
                name = pick_name()
                typ = pick_type()

                attrs = rand_attrs(env.metamodel_.node[typ].attrs_)

                op = add_req(op, " '%s'" % str(name))
                op = add_req(op, " TYPE '%s'" % str(typ))
                opt,op = add_opt(op, " "+str(attrs))
                if not opt:
                    attrs = None

                base_nodes.append(name)
                env.add_node(name, typ, attrs)
                trans.append(op)
            elif op == "DELETE_NODE":
                node = pick_node()
                if node is None:
                    continue

                op = add_req(op, " '%s'" % str(node))

                base_nodes.remove(node)
                env.remove_node(node)
                trans.append(op)
            elif op == "ADD_EDGE":
                e = pick_new_edge()
                if e is None:
                    continue
                else:
                    n1, n2 = e
                attrs = pick_edge_attrs_for(n1, n2)

                op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))
                opt,op = add_opt(op, " "+str(attrs))
                if not opt:
                    attrs = None

                env.add_edge(n1, n2, attrs)
                trans.append(op)
            elif op == "DELETE_EDGE":
                n1, n2 = pick_edge()
                if n1 is None or n2 is None:
                    continue

                op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))

                env.remove_edge(n1, n2)
                trans.append(op)
            elif op == "ADD_NODE_ATTRS":
                node = pick_node()
                if node is None:
                    continue
                if env.metamodel_ is None:
                    attrs = {}
                else:
                    if env.metamodel_.node[env.node[node].type_].attrs_ is None:
                        attrs = {}
                    else:
                        attrs = rand_attrs(dict_sub(env.metamodel_.node[env.node[node].type_].attrs_,
                                            env.node[node].attrs_))

                op = add_req(op, " '%s'" % node)
                op = add_req(op, " "+str(attrs))

                if attrs == {}:
                    continue

                env.add_node_attrs(node, attrs)
                trans.append(op)
            elif op == "ADD_EDGE_ATTRS":
                n1, n2 = pick_edge()
                if n1 is None or n2 is None:
                    continue
                if env.metamodel_ is None:
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
                trans.append(op)
            elif op == "DELETE_NODE_ATTRS":
                node = pick_node()
                if node is None:
                    continue
                attrs = pick_attrs_from(node)

                if attrs == {} or attrs is None:
                    continue

                op = add_req(op, " '%s'" % node)
                op = add_req(op, " "+str(attrs))

                env.remove_node_attrs(node, attrs)
                trans.append(op)
            elif op == "DELETE_EDGE_ATTRS":
                n1, n2 = pick_edge()
                if n1 is None or n2 is None:
                    continue
                attrs = pick_edge_attrs_from(n1, n2)

                if attrs == {} or attrs is None:
                    continue

                op = add_req(op, " '%s' '%s'" % (n1,n2))
                op = add_req(op, " "+str(attrs))

                env.remove_edge_attrs(n1, n2, attrs)
                trans.append(op)
            else:
                raise ValueError(
                    "Unknown action"
                )

        return ".\n".join(trans)+"."

    @staticmethod
    def simplify_commands(commands, di=False):
        """ Returns a simplified list of transformations that have the same
            behaviour as commands """
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        actions = []
        for command in command_strings:
          try:
              parsed = parser.parseString(command).asDict()
              actions.append(parsed)
          except:
              raise ValueError("Cannot parse command '%s'" % command)

        # We keep updated a list of the element we added, the lines of
        # transformations that added them or added attributes to them
        # and the type of addition we did (node or edge)

        added = []
        ad_index = []
        ad_type = []

        # We keep updated a list of the element we deleted and the lines of
        # transformation that deleted them or deleted attributes from them

        deleted = []
        del_index = []

        # We keep updated a list of the element we cloned and the line of
        # transformation that cloned them

        cloned = []
        clone_index = []

        # List of elements to remove at the end

        elements_to_remove = []

        # For each line of command we change what to remove and what to keep
        # We update the lists at each step, the only operations that actually
        # do simplify the commands are the deletion of nodes and edges and the
        # merges. They try to find the all the operations they can remove
        # without changing the behaviour

        for i in range(len(actions)):
            action = actions[i]
            if action["keyword"] == "add_node":
                added.append(action["node"])
                ad_index.append([i])
                ad_type.append("node")
            elif action["keyword"] == "delete_node":
                if action["node"] not in cloned:
                    # If the node haven't been cloned before
                    rem_el = []
                    for j in range(len(added)):
                        el = added[j]
                        if (type(el) == tuple and (el[0] == action["node"] or\
                                                   el[1] == action["node"])) or\
                            el == action["node"]:
                                # If the node have been involved in an addition
                                # we remove that addition since it has been
                                # deleted now, if there are not more lines that
                                # refers to the addition of that node, we can
                                # remove the deletion of the node
                                # Finding the node in added is not enough to
                                # remove the deletion since it can be an
                                # addition of an edge, we have to check if it
                                # the node itself that we added
                                if el == action["node"]:
                                    elements_to_remove.append(i)
                                for k in ad_index[j]:
                                    elements_to_remove.append(k)
                                rem_el.append(j)
                    k=0
                    for j in rem_el:
                        del added[j-k]
                        del ad_index[j-k]
                        del ad_type[j-k]
                        k += 1
                    rem_el = []
                    for j in range(len(deleted)):
                        el = deleted[j]
                        if (type(el) == tuple and (el[0] == action["node"] or\
                                                   el[1] == action["node"])) or\
                            el == action["node"]:
                                # If the node have been involved in a deletion
                                # we can remove that deletion since the deletion
                                # of the node itself will delete what the deletion
                                # would have deleted
                                for k in del_index[j]:
                                    elements_to_remove.append(k)
                                rem_el.append(j)
                    k=0
                    for j in rem_el:
                        del deleted[j-k]
                        del del_index[j-k]
                        k+=1
                else:
                    # If the node have been cloned before, we can't delete the
                    # transformations that happened before the cloning since
                    # they affected the clones too. We do so by comparing the
                    # line of the transformation we are looking at and the line
                    # of the last cloning operation that happened
                    rem_el = []
                    ind = max([clone_index[i] for i in range(len(cloned)) if cloned[i] == action["node"]])
                    for j in range(len(added)):
                        el = added[j]
                        if (type(el) == tuple and (el[0] == action["node"] or\
                                                   el[1] == action["node"])) or\
                            el == action["node"]:
                            rem_ind = []
                            for k in ad_index[j]:
                                if k > ind:
                                    elements_to_remove.append(k)
                                    rem_ind.append(k)
                            if ad_index[j] == rem_ind:
                                rem_el.append(j)
                            else:
                                for k in rem_ind:
                                    ad_index[j].remove(k)
                    m=0
                    for j in rem_el:
                        del added[j-m]
                        del ad_index[j-m]
                        del ad_type[j-m]
                        m+=1
                    rem_el = []
                    for j in range(len(deleted)):
                        el = deleted[j]
                        if (type(el) == tuple and (el[0] == action["node"] or\
                                                   el[1] == action["node"])) or\
                            el == action["node"]:
                            rem_ind = []
                            for k in del_index[j]:
                                if k > ind:
                                    elements_to_remove.append(k)
                                    rem_ind.append(k)
                            if del_index[j] == rem_ind:
                                rem_el.append(j)
                            else:
                                for k in rem_ind:
                                    del_index[j].remove(k)
                    m=0
                    for j in rem_el:
                        del deleted[j-m]
                        del del_index[j-m]
                        m+=1
                    ind = clone_index.index(ind)
                    del cloned[ind]
                    del clone_index[ind]
                deleted.append(action["node"])
                del_index.append([i])
            elif action["keyword"] == "add_node_attrs":
                if action["node"] in added:
                    j = added.index(action["node"])
                    ad_index[j].append(i)
                else:
                    added.append(action["node"])
                    ad_index.append([i])
                    ad_type.append("node_attrs")
            elif action["keyword"] == "delete_node_attrs":
                if action["node"] in deleted:
                    j = deleted.index(action["node"])
                    del_index[j].append(i)
                else:
                    deleted.append(action["node"])
                    del_index.append([i])
            elif action["keyword"] == "add_edge":
                e = (action["node_1"], action["node_2"])
                added.append(e)
                ad_index.append([i])
                ad_type.append("edge")
            elif action["keyword"] == "delete_edge":
                # It is the same idea as in the delete_node function, but with
                # a little bit more complexity since we have two nodes that
                # can possibly be cloned.
                # This time, finding the edge in the added list automatically
                # means we have to remove the deletion and the addition in the
                # case we didn't clone any of our nodes
                e = (action["node_1"], action["node_2"])
                if e[0] not in cloned and e[1] not in cloned:
                    rem_el = []
                    for j in range(len(added)):
                        el = added[j]
                        if type(el) == tuple and\
                           (el == e or (not di and el == (e[1], e[0]))):
                            elements_to_remove.append(i)
                            for k in ad_index[j]:
                                elements_to_remove.append(k)
                            rem_el.append(j)
                    k=0
                    for j in rem_el:
                        del added[j-k]
                        del ad_index[j-k]
                        del ad_type[j-k]
                        k+=1
                    rem_el = []
                    for j in range(len(deleted)):
                        el = deleted[j]
                        if type(el) == tuple and\
                           (el == e or (not di and el == (e[1], e[0]))):
                            for k in del_index[j]:
                                elements_to_remove.append(k)
                            rem_el.append(j)
                    k=0
                    for j in rem_el:
                        del deleted[j-k]
                        del del_index[j-k]
                        k+=1
                else:
                    # Same idea as before if one of the nodes have been cloned,
                    # but we have to take the max of the line number of all the
                    # cloning operation on node 0 and node 1
                    ind = 0
                    if e[0] in cloned:
                        ind = max([clone_index[i] for i in range(len(cloned)) if cloned[i] == e[0]])
                    if e[1] in cloned:
                        ind = max([ind]+[clone_index[i] for i in range(len(cloned)) if cloned[i] == e[1]])

                    ind = clone_index.index(ind)

                    if e[0] in cloned:
                        rem_el = []
                        for j in range(len(added)):
                            el = added[j]
                            if type(el) == tuple and\
                               (el == e or (not di and el == (e[1], e[0]))):
                                rem_ind = []
                                for k in ad_index[j]:
                                    if k > clone_index[ind]:
                                        elements_to_remove.append(k)
                                        # We remove the delete_edge operation
                                        # iff the same edge have been added
                                        # after the last cloning operation
                                        if ad_type[j] == "edge":
                                            elements_to_remove.append(i)
                                        rem_ind.append(k)
                                if ad_index[j] == rem_ind:
                                    rem_el.append(j)
                                else:
                                    for k in rem_ind:
                                        ad_index[j].remove(k)
                        m=0
                        for j in rem_el:
                            del added[j-m]
                            del ad_index[j-m]
                            del ad_type[j-m]
                            m+=1
                        rem_el = []
                        for j in range(len(deleted)):
                            el = deleted[j]
                            if type(el) == tuple and\
                               (el == e or (not di and el == (e[1], e[0]))):
                                rem_ind = []
                                for k in del_index[j]:
                                    if k > clone_index[ind]:
                                        elements_to_remove.append(k)
                                        rem_ind.append(k)
                                if del_index[j] == rem_ind:
                                    rem_el.append(j)
                                else:
                                    for k in rem_ind:
                                        del_index[j].remove(k)
                        m=0
                        for j in rem_el:
                            del deleted[j-m]
                            del del_index[j-m]
                            m+=1
                    if e[1] in cloned:
                        rem_el = []
                        for j in range(len(added)):
                            el = added[j]
                            if type(el) == tuple and\
                               (el == e or (not di and el == (e[1], e[0]))):
                                rem_ind = []
                                for k in ad_index[j]:
                                    if k > clone_index[ind]:
                                        elements_to_remove.append(k)
                                        if ad_type[j] == "edge":
                                            elements_to_remove.append(i)
                                        rem_ind.append(k)
                                if ad_index[j] == rem_ind:
                                    rem_el.append(j)
                                else:
                                    for k in rem_ind:
                                        ad_index[j].remove(k)
                        m=0
                        for j in rem_el:
                            del added[j-m]
                            del ad_index[j-m]
                            del ad_type[j-m]
                            m+=1
                        rem_el = []
                        for j in range(len(deleted)):
                            el = deleted[j]
                            if type(el) == tuple and\
                               (el == e or (not di and el == (e[1], e[0]))):
                                rem_ind = []
                                for k in del_index[j]:
                                    if k > clone_index[ind]:
                                        elements_to_remove.append(k)
                                        rem_ind.append(k)
                                if del_index[j] == rem_ind:
                                    rem_el.append(j)
                                else:
                                    for k in rem_ind:
                                        del_index[j].remove(k)
                        m=0
                        for j in rem_el:
                            del deleted[j-m]
                            del del_index[j-m]
                            m+=1
                deleted.append(e)
                del_index.append([i])
            elif action["keyword"] == "add_edge_attrs":
                e = (action["node_1"], action["node_2"])
                if e in added:
                    j = added.index(e)
                    ad_index[j].append(i)
                elif not di and (e[1], e[0]) in added:
                    j = added.index((e[1], e[0]))
                    ad_index[j].append(i)
                else:
                    added.append(e)
                    ad_index.append([i])
                    ad_type.append("edge_attrs")
            elif action["keyword"] == "delete_edge_attrs":
                e = (action["node_1"], action["node_2"])
                if e in deleted:
                    j = deleted.index(e)
                    del_index[j].append(i)
                elif not di and (e[1], e[0]) in deleted:
                    j = deleted.index((e[1], e[0]))
                    del_index[j].append(i)
                else:
                    deleted.append(e)
                    del_index.append([i])
            elif action["keyword"] == "clone":
                if "node_name" in action.keys():
                    added.append(action["node_name"])
                    ad_index.append([i])
                    ad_type.append("node")
                cloned.append(action["node"])
                clone_index.append(i)
            elif action["keyword"] == "merge":
                if "node_name" in action.keys():
                    node_name = action["node_name"]
                else:
                    node_name = "_".join(action["nodes"])

                added.append(node_name)
                ad_index.append([i])
                ad_type.append("node")

        return "\n".join([command_strings[i] for i in range(len(actions)) if i not in elements_to_remove])

    @staticmethod
    def make_canonical_commands(g, commands, di=False):
        """ Takes commands and the graph it refers to and returns a list of
            canonical transformations that have the same behaviour.
            The canonical form of a transformation follows this pattern :
                DELETIONS (DELETE_NODE, DELETE_NODE_ATTRS, DELETE_EDGE, DELETE_EDGE_ATTRS)
                CLONING (CLONE)
                ADDING and MERGING (ADD_NODE, ADD_NODE_ATTRS, ADD_EDGE, ADD_EDGE_ATTRS, MERGE)
            eg :
                commands :
                DELETE_EDGE_ATTRS '3' '5' {'3': {'1'}}.
                DELETE_EDGE '14' '1'.
                DELETE_EDGE '8' '1'.
                DELETE_NODE_ATTRS '3' {'2': {'17', '16', '7', '1', '2', '13'}, '1': {'3', '7', '8', '1'}}.
                ADD_EDGE '14' '1' {'3': {'10', '17', '16', '14', '19', '8', '1', '3', '2', '6'}}.
                DELETE_EDGE '14' '18'.
                ADD_NODE '8.7' TYPE '10'.
                DELETE_EDGE '4' '3'.
                DELETE_NODE '11'.
                ADD_NODE '10.13' TYPE '8'.
                DELETE_NODE '10.13'.
                ADD_EDGE '4' '2'.
                ADD_NODE '15.1' TYPE '3' {'3': {'0', '3', '2', '1'}, '4': {'0'}, '2': {'5', '7', '14', '8', '15', '3', '11', '0'}}.
                CLONE '4' AS '8.7.19'.
                CLONE '19' AS '4.8'.
                DELETE_EDGE_ATTRS '10' '4' {'2': {'17', '3', '4', '11', '12'}}.
                ADD_NODE '6.7' TYPE '8' {'3': {'0'}, '1': {'7', '1', '3', '4', '2', '6'}}.
                CLONE '14'.
                CLONE '9'.
                ADD_NODE '5.8.7.19' TYPE '2' {'2': {'10', '22', '5', '14', '8', '23', '15', '25', '27', '24', '29', '0', '6', '13'}}.

                canonical commands :

            0 : DELETE_EDGE_ATTRS '3' '5' {'3': {'1'}}.
                DELETE_EDGE '14' '1'.
                DELETE_EDGE '8' '1'.
                DELETE_NODE_ATTRS '3' {'2': {'17', '16', '7', '1', '2', '13'}, '1': {'3', '7', '8', '1'}}.
                DELETE_EDGE '14' '18'.
                DELETE_EDGE '4' '3'.
                DELETE_NODE '11'.
                CLONE '19' AS '4.8'.
                CLONE '9'.
                ADD_EDGE '14' '1' {'3': {'10', '17', '16', '14', '19', '8', '1', '3', '2', '6'}}.
                ADD_NODE '8.7' TYPE '10'.
                ADD_EDGE '4' '2'.
                ADD_NODE '15.1' TYPE '3' {'3': {'0', '3', '2', '1'}, '4': {'0'}, '2': {'5', '7', '14', '8', '15', '3', '11', '0'}}.
                ADD_NODE '6.7' TYPE '8' {'3': {'0'}, '1': {'7', '1', '3', '4', '2', '6'}}.
                ADD_NODE '5.8.7.19' TYPE '2' {'2': {'10', '22', '5', '14', '8', '23', '15', '25', '27', '24', '29', '0', '6', '13'}}.

            1 : CLONE '4' AS '8.7.19'.
                CLONE '14'.

            2 : DELETE_EDGE_ATTRS '10' '4' {'2': {'17', '3', '4', '11', '12'}}
        """
        res = []

        # We do multiple steps of simplification, until we found a fixed-point

        aux = commands
        next_step = Rewriter.simplify_commands(commands, di)
        while next_step != aux:
            aux = next_step
            next_step = Rewriter.simplify_commands(aux, di)

        # We keep updated an environment with our nodes and our edges

        env_nodes = [n for n in g.nodes()]
        env_edges = [e for e in g.edges()]

        if not di:
            for e in g.edges():
                if not (e[1], e[0]) in env_edges:
                    env_edges.append((e[1], e[0]))

        # For each transformation we choose if we do it in this step or if we
        # keep it for later

        while next_step != '':
            command_strings = [c for c in next_step.splitlines() if len(c) > 0]
            actions = []
            for command in command_strings:
                try:
                    parsed = parser.parseString(command).asDict()
                    actions.append(parsed)
                except:
                    raise ValueError("Cannot parse command '%s'" % command)

            next_step = ''

            # We have 3 strings for each line of the canonical pattern

            add_step = ''
            del_step = ''
            clone_step = ''

            # Added is the list of elements we will add at to our environment
            # at the end of the step, we add them at the end so they are not
            # taken into account in the current step

            added = []
            cloned = []

            # If a node is in clone_wait, every cloning operation on it will
            # be delayed to next step. Same for other lists

            clone_wait = []
            merge_wait = []
            del_wait = []
            ad_wait = []

            # If we can't add a node with name n in this step, we don't want
            # another node with the same name to be added before it

            protected_names = []

            # For each action we update our lists and we chose what to do

            for i in range(len(actions)):
                action = actions[i]
                if action["keyword"] == "add_node":
                    if action["node"] not in protected_names:
                        add_step += command_strings[i]+"\n"
                        added.append(action["node"])
                elif action["keyword"] == "delete_node":
                    if action["node"] in env_nodes and\
                       action["node"] not in del_wait:
                        del_step += command_strings[i]+"\n"
                        env_nodes.remove(action["node"])
                    else:
                        next_step += command_strings[i]+"\n"
                        ad_wait.append(action["node"])
                elif action["keyword"] == "add_node_attrs":
                    if action["node"] in env_nodes and\
                       action["node"] not in ad_wait:
                        add_step += command_strings[i]+"\n"
                        added.append(action["node"])
                        clone_wait.append(action["node"])
                    else:
                        next_step += command_strings[i]+"\n"
                        ad_wait.append(action["node"])
                        clone_wait.append(action["node"])
                elif action["keyword"] == "delete_node_attrs":
                    if action["node"] in env_nodes and\
                       action["node"] not in del_wait:
                        del_step += command_strings[i]+"\n"
                    else:
                        next_step += command_strings[i]+"\n"
                        clone_wait.append(action["node"])
                        ad_wait.append(action["node"])
                elif action["keyword"] == "add_edge":
                    e = (action["node_1"], action["node_2"])
                    if e[0] in env_nodes and\
                       e[1] in env_nodes and\
                       e[0] not in ad_wait and\
                       e[1] not in ad_wait:
                       add_step += command_strings[i]+"\n"
                       added.append(e)
                       if not di:
                           added.append((e[1], e[0]))
                       clone_wait.append(action["node_1"])
                       clone_wait.append(action["node_2"])
                    else:
                        next_step += command_strings[i]+"\n"
                        clone_wait.append(action["node_1"])
                        clone_wait.append(action["node_2"])
                        merge_wait.append(action["node_1"])
                        merge_wait.append(action["node_2"])
                elif action["keyword"] == "delete_edge":
                    e = (action["node_1"], action["node_2"])
                    if (e in env_edges or\
                       (not di and (e[1], e[0]) in env_edges)) and\
                       e[0] not in del_wait and\
                       e[1] not in del_wait:
                        is_cloned = False
                        for l in cloned:
                            if e[0] in l:
                                next_step += command_strings[i]+"\n"
                                clone_wait.append(action["node_1"])
                                clone_wait.append(action["node_2"])
                                merge_wait.append(action["node_1"])
                                merge_wait.append(action["node_2"])
                                is_cloned = True
                                break
                        if not is_cloned:
                            del_step += command_strings[i]+"\n"
                            clone_wait.append(action["node_1"])
                            clone_wait.append(action["node_2"])
                            env_edges.remove(e)
                            if not di:
                                env_edges.remove((e[1], e[0]))
                    else:
                        next_step += command_strings[i]+"\n"
                        clone_wait.append(action["node_1"])
                        clone_wait.append(action["node_2"])
                        merge_wait.append(action["node_1"])
                        merge_wait.append(action["node_2"])
                elif action["keyword"] == "add_edge_attrs":
                    e = (action["node_1"], action["node_2"])
                    if (e in env_edges or\
                       (not di and (e[1], e[0]) in env_edges)) and\
                       e[0] not in ad_wait and\
                       e[1] not in ad_wait:
                        add_step += command_strings[i]+"\n"
                        added.append(e)
                        if not di:
                            added.append((e[1], e[0]))
                        clone_wait.append(action["node_1"])
                        clone_wait.append(action["node_2"])
                    else:
                        next_step += command_strings[i]+"\n"
                        clone_wait.append(action["node_1"])
                        clone_wait.append(action["node_2"])
                        merge_wait.append(action["node_1"])
                        merge_wait.append(action["node_2"])
                elif action["keyword"] == "delete_edge_attrs":
                    e = (action["node_1"], action["node_2"])
                    if (e in env_edges or\
                       (not di and (e[1], e[0]) in env_edges)) and\
                       e[0] not in del_wait and\
                       e[1] not in del_wait:
                        is_cloned = False
                        for l in cloned:
                            if e[0] in l:
                                next_step += command_strings[i]+"\n"
                                clone_wait.append(action["node_1"])
                                clone_wait.append(action["node_2"])
                                merge_wait.append(action["node_1"])
                                merge_wait.append(action["node_2"])
                                is_cloned = True
                            elif e[1] in l:
                                next_step += command_strings[i]+"\n"
                                clone_wait.append(action["node_1"])
                                clone_wait.append(action["node_2"])
                                merge_wait.append(action["node_1"])
                                merge_wait.append(action["node_2"])
                                is_cloned = True
                        if not is_cloned:
                            del_step += command_strings[i]+"\n"
                            clone_wait.append(action["node_1"])
                            clone_wait.append(action["node_2"])
                    else:
                        next_step += command_strings[i]+"\n"
                        clone_wait.append(action["node_1"])
                        clone_wait.append(action["node_2"])
                        merge_wait.append(action["node_1"])
                        merge_wait.append(action["node_2"])
                elif action["keyword"] == "clone":
                    node = action["node"]
                    if "node_name" in action.keys():
                        new_node = action["node_name"]
                    else:
                        j = 1
                        new_node = str(node)+str(j)
                        while new_node in env_nodes or new_node in added:
                            j+=1
                            new_node = str(node)+str(j)
                    if node in env_nodes and\
                       node not in clone_wait and\
                       new_node not in protected_names and\
                       fold_left(lambda e, acc : (e != node or\
                                                 (type(e) == tuple and\
                                                 e[1] != node and\
                                                 e[0] != node)) and\
                                                 acc,
                                 True,
                                 added):
                        clone_step += command_strings[i]+"\n"
                        added.append(new_node)
                        del_wait.append(node)
                        found = False
                        for i in range(len(cloned)):
                            if node in cloned[i]:
                                cloned[i].append(new_node)
                                found = True
                        if not found:
                            cloned.append([new_node, node])
                        to_add = []
                        for e in env_edges:
                            if e[0] == node:
                                to_add.append((new_node, e[1]))
                            elif e[1] == node:
                                to_add.append((e[0], new_node))
                        for e in added:
                            if type(e) == tuple:
                                if e[0] == node and\
                                   e[1] != node:
                                    to_add.append((new_node, e[1]))
                                elif e[1] == node and\
                                     e[0] != node:
                                    to_add.append((e[0], new_node))
                        for e in to_add:
                            added.append(e)
                    else:
                        next_step += command_strings[i]+"\n"
                        del_wait.append(node)
                        merge_wait.append(node)
                        ad_wait.append(node)
                        protected_names.append(new_node)
                elif action["keyword"] == "merge":
                    if "node_name" in actions[i].keys():
                        node_name = actions[i]["node_name"]
                    else:
                        node_name = "_".join(actions[i]["nodes"])
                    if fold_left(lambda n, acc: (n in env_nodes and\
                                                 n not in merge_wait) and\
                                                 acc,
                                 True,
                                 action["nodes"]) and\
                        node_name not in protected_names:
                        add_step += command_strings[i]+"\n"

                        added.append(node_name)
                        clone_wait.append(node_name)

                        rem_el = []
                        for e in env_edges:
                            if e[0] in action["nodes"] and\
                               e[1] in action["nodes"]:
                               if not e in rem_el:
                                   rem_el.append(e)
                            if e[0] in action["nodes"]:
                                if not e in rem_el:
                                    rem_el.append(e)
                                if e[1] not in action["nodes"]:
                                    added.append((node_name, e[1]))
                            elif e[1] in action["nodes"]:
                                if not e in rem_el:
                                    rem_el.append(e)
                                if e[0] not in action["nodes"]:
                                    added.append((e[0], node_name))
                        for e in rem_el:
                            while e in env_edges:
                                env_edges.remove(e)
                                if not di:
                                    env_edges.remove((e[1], e[0]))
                        rem_el = []
                        for e in added:
                            if type(e) == tuple:
                                if e[0] in action["nodes"] and\
                                   e[1] in action["nodes"]:
                                   if not e in rem_el:
                                       rem_el.append(e)
                                if e[0] in action["nodes"]:
                                   if not e in rem_el:
                                       rem_el.append(e)
                                   if e[1] not in action["nodes"]:
                                       added.append((node_name, e[1]))
                                elif e[1] in action["nodes"]:
                                    if not e in rem_el:
                                        rem_el.append(e)
                                    if e[0] not in action["nodes"]:
                                        added.append((e[0], node_name))
                        for e in rem_el:
                            while e in added:
                                added.remove(e)
                                if not di:
                                    added.remove((e[1], e[0]))
                    else:
                        next_step += command_strings[i]+"\n"
                        protected_names.append(node_name)

            for el in added:
                if type(el) == tuple:
                    env_edges.append(el)
                else:
                    env_nodes.append(el)

            if del_step+clone_step+add_step == '':
                raise ValueError(
                    "Can't find any new transformations and actions is non-empty :\n%s" %
                    next_step
                )

            res.append(del_step+clone_step+add_step)


        return res
