"""Graph rewriting tools."""

import networkx as nx
from networkx.algorithms import isomorphism
import warnings

import itertools
import copy
import random

from regraph.library.parser import parser
from regraph.library.utils import (is_subdict,
                                   valid_attributes,
                                   dict_sub,
                                   fold_left,
                                   keys_by_value,
                                   make_canonical_commands)
from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism,)
                                             # TypedHomomorphism)
from regraph.library.category_op import (pullback_complement,
                                         pushout)


class Rule(object):
    """
    Class implements a rewriting rule.
    A rewriting rule consists of the three graphs:
    `p` - preserved part, `lhs` - left hand side,
    `rhs` - right hand side, and two mappings
    p -> lhs, p -> rhs. The rule can be type preserving or not,
    which is set by the attribute `ignore_types`
    """

    def __init__(self, p, lhs, rhs, p_lhs=None,
                 p_rhs=None, typing_graph=None,
                 ignore_types=False, ignore_attrs=False):
        """Initialize a rule by p, lhs and rhs and two homomorphisms:
        p -> lhs & p -> rhs. By default the homomorphisms are None, and
        they are created as Homomorphism.identity(p, lhs) etc with the
        correspondance according to the node names."""
        self.p = copy.deepcopy(p)
        self.lhs = copy.deepcopy(lhs) 
        self.rhs = copy.deepcopy(rhs)
        self.typing_graph = typing_graph
        self.ignore_types = ignore_types
        self.ignore_attrs = ignore_attrs
        
        if not p_lhs:
            self.p_lhs = Homomorphism.identity(p, lhs, ignore_types, ignore_attrs).mapping_
        else:
            self.p_lhs = copy.deepcopy(p_lhs)

        if not p_rhs:
            self.p_rhs = Homomorphism.identity(p, rhs, ignore_types, ignore_attrs).mapping_
        else:
            self.p_rhs = copy.deepcopy(p_rhs)
        return

    @classmethod
    def from_homomorphisms(cls, p_lhs, p_rhs, typing_graph=None,
                           ignore_types=False, ignore_attrs=False):
        """Initialize rule from input homomorphisms."""
        if P_LHS.source_ != P_RHS.source_:
            raise ValueError("Preserved part of the homomorphisms does not match!")
        p = copy.deepcopy(p_lhs.source_)
        lhs = copy.deepcopy(p_lhs.target_)
        rhs = copy.deepcopy(p_rhs.target_)
        p_lhs = copy.deepcopy(p_lhs.mapping_)
        p_rhs = copy.deepcopy(p_rhs.mapping_)
        ignore_types = ignore_types
        ignore_attrs = ignore_attrs
        return cls(p, lhs, rhs, p_lhs, p_rhs, typing_graph, ignore_types, ignore_attrs)

    @classmethod
    def from_transform(cls, pattern, typing_graph=None, ignore_types=False, ignore_attrs=False, commands=None):
        """Initialize a rule from the transformation.
        On input takes a pattern which is used as LHS of the rule,
        as an optional argument transformation commands can be provided,
        by default the list of commands is empty and all P, LHS and RHS
        are initialized to be the same graph (pattern), later on
        when transformations are applied P and RHS are being updated.
        If list of commands is specified, """
        p = copy.deepcopy(pattern)
        lhs = copy.deepcopy(pattern)
        rhs = copy.deepcopy(pattern)
        p_lhs = dict([(n, n) for n in pattern.nodes()])
        p_rhs = dict([(n, n) for n in pattern.nodes()])
        ignore_types = ignore_types
        ignore_attrs = ignore_attrs

        rule = cls(p, lhs, rhs, p_lhs, p_rhs, typing_graph, ignore_types, ignore_attrs)

        # if the commands are provided, perform respecitive transformations
        if commands:
            # 1. make the commands canonical
            commands = make_canonical_commands(p, commands, p.is_directed())
            print(commands)
            # 2. apply the commands
            print([c for block in commands for c in block.splitlines() ])

            command_strings = [c for block in commands if len(block) > 0 for c in block.splitlines()]

            actions = []
            for command in command_strings:
                try:
                    parsed = parser.parseString(command).asDict()
                    actions.append(parsed)
                except:
                    raise ValueError("Cannot parse command '%s'" % command)

            for action in actions:
                if action["keyword"] == "clone":
                    node_name = None
                    if "node_name" in action.keys():
                        node_name = action["node_name"]
                    rule.clone_node(action["node"], node_name)
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
                    merged_node = rule.merge_nodes_list(
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
                    rule.add_node(name, node_type, attrs)
                elif action["keyword"] == "delete_node":
                    rule.remove_node(action["node"])
                elif action["keyword"] == "add_edge":
                    attrs = {}
                    if "attributes" in action.keys():
                        attrs = action["attributes"]
                    rule.add_edge(
                        action["node_1"],
                        action["node_2"],
                        attrs)
                elif action["keyword"] == "delete_edge":
                    rule.remove_edge(
                        action["node_1"],
                        action["node_2"])
                elif action["keyword"] == "add_node_attrs":
                    rule.add_node_attrs(
                        action["node"],
                        action["attributes"])
                elif action["keyword"] == "add_edge_attrs":
                    rule.add_edge_attrs(
                        action["node_1"],
                        action["node_2"],
                        action["attributes"])
                elif action["keyword"] == "delete_node_attrs":
                    rule.remove_node_attrs(
                        action["node"],
                        action["attributes"])
                elif action["keyword"] == "delete_edge_attrs":
                    rule.remove_edge_attrs(
                        action["node_1"],
                        action["node_2"],
                        action["attributes"])
                else:
                    raise ValueError("Unknown command %s" % action["keyword"])
        return rule

    def __eq__(self, rule):
        return (
            self.p == rule.p and
            self.lhs == rule.lhs  and
            self.rhs == rule.rhs and
            self.p_lhs == rule.p_lhs and
            self.p_rhs == rule.p_rhs and
            self.typing_graph == rule.typing_graph and
            self.ignore_types == rule.ignore_types and
            self.ignore_attrs == rule.ignore_attrs
        )

    def __str__(self):
        return "Preserved part\n%s\n" % self.p +\
               "Left hand side\n%s\n" % self.lhs +\
               "P->L Homomorphism : %s\n" % self.p_lhs +\
               "Right hand side\n%s\n" % self.rhs +\
               "P->R Homomorphism : %s\n" % self.p_rhs

    def __doc__(self):
        return "An instance of rule is an instance of `p` (preserved part), " +\
               "`lhs` (lef-hand side of the rule) and `rhs` (right-hand side) graphs " +\
               "together with two mappings p -> lhs & p -> rhs. The graph typing the rule " +\
               "is specified with `typing_graph` attribute."

    # Canonic operations

    def get(self):
        """Return the homomorphisms P -> LHS and P -> RHS."""
        return (
            Homomorphism(self.p, self.lhs, self.p_lhs, self.ignore_types, self.ignore_attrs),
            Homomorphism(self.p, self.rhs, self.p_rhs, self.ignore_types, self.ignore_attrs)
        )

    def add_node(self, node_id, node_type, attrs=None):
        """Add node to the graph."""
        if node_id not in self.rhs.nodes(): 
            p_keys = keys_by_value(self.p_rhs, node_id)
            # here we check for the nodes with the same name in the lhs
            for k in p_keys:
                lhs_key = self.p_lhs[k]
                if lhs_key == node_id:
                    raise ValueError(
                        "Node with the id '%s' already exists in the left hand side of the rule" %
                        node_id
                    )
            self.rhs.add_node(node_id, node_type, attrs)
        else:
            raise ValueError(
                "Node with the id '%s' already exists in the right hand side of the rule" %
                node_id
            )

    def remove_node(self, n):
        """Remove a node in the graph."""

        # remove corresponding nodes from p and rhs
        p_keys = keys_by_value(self.p_lhs, n)
        for k in p_keys:
            if k in self.p.nodes():
                self.p.remove_node(k)
            if self.p_rhs[k] in self.rhs.nodes():
                self.rhs.remove_node(self.p_rhs[k])
                affected_nodes = keys_by_value(self.p_rhs, self.p_rhs[k])
                for node in affected_nodes:
                    del self.p_rhs[node]
            del self.p_lhs[k]
        return

    def add_edge(self, n1, n2, attrs=None):
        """Add an edge in the graph."""
        
        # Find nodes in p mapping to n1 & n2
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise ValueError(
                    "Node with the id '%s' does not exist in the preserved part of the rule" % k2
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise ValueError(
                        "Node with the id '%s' does not exist in the preserved part of the rule" % k2
                    )
                rhs_key_1 = self.p_rhs[k1]
                rhs_key_2 = self.p_rhs[k2]
                if self.rhs.is_directed():
                    if (rhs_key_1, rhs_key_2) in self.rhs.edges():
                        raise ValueError(
                            "Edge %s-%s already exists in the right hand side of the rule" % 
                            (rhs_key_1, rhs_key_2)
                        )
                    self.rhs.add_edge(rhs_key_1, rhs_key_2, attrs)
                else:
                    if (rhs_key_1, rhs_key_2) in self.rhs.edges() or\
                       (rhs_key_2, rhs_key_1) in self.rhs.edges():
                        raise ValueError(
                            "Edge %s-%s already exists in the right hand side of the rule" % 
                            (rhs_key_1, rhs_key_2)
                        )
                    self.rhs.add_edge(rhs_key_1, rhs_key_2, attrs)
        return

    def remove_edge(self, n1, n2):
        """Remove edge from the graph."""

        # Find nodes in p mapping to n1 & n2
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        # Remove edge from the preserved part & rhs of the rule
        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise ValueError(
                    "Node with the id '%s' does not exist in the preserved part" % k1
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise ValueError(
                        "Node with the id '%s' does not exist in the preserved part" % k2
                    )
                rhs_key_1 = self.p_rhs[k1]
                rhs_key_2 = self.p_rhs[k2]
                if self.p.is_directed():
                    if (k1, k2) not in self.p.edges():
                        raise ValueError(
                            "Edge '%s->%s' does not exist in the preserved part of the rule " %
                            (k1, k2)
                        )
                    if (rhs_key_1, rhs_key_2) not in self.rhs.edges():
                        raise ValueError(
                            "Edge '%s->%s' does not exist in the right hand side of the rule " %
                            (rhs_key_1, rhs_key_2)
                        )
                    self.p.remove_edge(k1, k2)
                    self.rhs.remove_edge(rhs_key_1, rhs_key_2)                      
                else:
                    if (k1, k2) not in self.p.edges() and (k2, k1) not in self.p.edges():
                        raise ValueError(
                            "Edge '%s-%s' does not exist in the preserved part of the rule " %
                            (k1, k2)
                        ) 
                    if (rhs_key_1, rhs_key_2) not in self.rhs.edges() and\
                       (rhs_key_2, rhs_key_1) not in self.rhs.edges():
                        raise ValueError(
                            "Edge '%s-%s' does not exist in the right hand side of the rule " %
                            (rhs_key_1, rhs_key_2)
                        )
                    self.p.remove_edge(k1, k2)                      
        return

    def clone_node(self, n, node_name=None):
        """Clone a node of the graph."""
        p_new_nodes = []
        rhs_new_nodes = []
        p_keys = keys_by_value(self.p_lhs, n)
        for k in p_keys:
            p_new_node = self.p.clone_node(k)
            p_new_nodes.append(p_new_node)
            rhs_new_node = self.rhs.clone_node(self.p_rhs[k])
            rhs_new_nodes.append(rhs_new_node)
            # self.p_lhs[k] = n
            self.p_lhs[p_new_node] = n
            self.p_rhs[p_new_node] = rhs_new_node
        return (p_new_nodes, rhs_new_nodes)

    def merge_nodes(self, n1, n2, node_name=None):
        """Merge two nodes of the graph."""
        
        # Update graphs
        new_name = None
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        nodes_to_merge = set()
        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise ValueError(
                    "Node with the id '%s' does not exist in the preserved part of the rule" % k1
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise ValueError(
                        "Node with the id '%s' does not exist in the preserved part of the rule" % k2
                    )
                nodes_to_merge.add(self.p_rhs[k1])
                nodes_to_merge.add(self.p_rhs[k2])    
     
        new_name = self.rhs.merge_nodes(list(nodes_to_merge))
        # Update mappings
        keys = p_keys_1 + p_keys_2
        for k in keys:
            self.p_rhs[k] = new_name  
        return new_name

    def add_node_attrs(self, n, attrs):
        """Add node attributes to a node in the graph."""
        if n not in self.lhs.nodes():
            raise ValueError("Node %s does not exist in the left hand side of the rule" % n)
        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise ValueError("Node %s is being removed by the rule, cannot add attributes" % n)
        for k in p_keys:
            self.rhs.add_node_attrs(self.p_rhs[k], attrs)
        return

    def remove_node_attrs(self, n, attrs):
        """Remove nodes attributes from a node in the graph."""

        if n not in self.lhs.nodes():
            raise ValueError("Node %s does not exist in the left hand side of the rule" % n)
            
        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise ValueError("Node %s is being removed by the rule, cannot remove attributes" % n)
        
        for k in p_keys:
            self.p.remove_node_attrs(k, attrs)
            self.rhs.remove_node_attrs(self.p_rhs[k], attrs)
        return

    def update_node_attrs(self, n, attrs):
        """Update attributes of a node."""
        if n not in self.lhs.nodes():
            raise ValueError("Node %s does not exist in the left hand side of the rule" % n)

        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise ValueError("Node %s is being removed by the rule, cannot update attributes" % n)
        for k in p_keys:
            self.p.node[k].attrs_ = None
            self.rhs.update_node_attrs(self.p_rhs[k], attrs)            
        return

    def add_edge_attrs(self, n1, n2, attrs):
        """Add attributes to an edge."""
        if n1 not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n1
            )

        if n2 not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n2
            )

        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise ValueError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )
            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot add attributes to the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot add attributes to the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.rhs.add_edge_attrs(self.p_rhs[k1], self.p_rhs[k2], attrs)

        else:
            if (n1, n2) not in self.lhs.edges() and (n2, n1) not in self.lhs.edges():
                raise ValueError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot add attributes to the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot add attributes to the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.rhs.add_edge_attrs(self.p_rhs[k1], self.p_rhs[k2], attrs)
        return

    def remove_edge_attrs(self, n1, n2, attrs):
        """Remove edge attributes from an edge in the graph."""
        if n1 not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n1
            )
        if n2 not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n2
            )
        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise ValueError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot remove attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot remove attributes from the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.p.remove_edge_attrs(k1, k2, attrs)
                    self.rhs.remove_edge_attrs(self.p_rhs[k1], self.p_rhs[k2], attrs)
        else:
            if (n1, n2) not in self.lhs.edges() and (n2, n1) not in self.lhs.edges():
                raise ValueError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )
            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot remove attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot remove attributes from the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.p.remove_edge_attrs(k1, k2, attrs)
                    self.rhs.remove_edge_attrs(self.p_rhs[k1], self.p_rhs[k2], attrs)
        return

    def update_edge_attrs(self, n1, n2, attrs):
        """Update the attributes of an edge with a new set `attrs`."""
        if n1 not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n1
            )
        if n2 not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n2
            )
        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise ValueError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            
            if len(p_keys_1) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot update attributes from the incident edge" %
                    n2
                )
            if len(p_keys_2) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot update attributes from the incident edge" %
                    n1
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.p.edge[k1][k2] = None
                    self.rhs.update_edge_attrs(self.p_rhs[k1], self.p_rhs[k2], attrs)                
        else:
            if (n1, n2) not in self.lhs.edges() and (n2, n1) not in self.lhs.edges():
                raise ValueError(
                    "Edge '%s->%s' does not exist in the left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot update attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise ValueError(
                    "Node %s is being removed by the rule, cannot update attributes from the incident edge" %
                    n2
                )
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    self.p.edge[k1][k2] = None
                    self.rhs.update_edge_attrs(self.p_rhs[k1], self.p_rhs[k2], attrs)          
        return


    # Advanced operations

    # def merge_edges(self, e1, e2, name_n1=None, name_n2=None):
    #     """ Merges two edges """
    #     n1_1, n1_2 = e1
    #     n2_1, n2_2 = e2
    #     if (n1_1 == n2_2) or (n1_2 == n2_1):
    #         if self.G.is_directed():
    #             raise ValueError(
    #                 "Can't merge edges with pattern %s->%s and %s->%s" %
    #                 (n1_1, n1_2, n2_1, n2_2)
    #             )
    #         else:
    #             if n1_1 == n2_2:
    #                 self.merge_nodes(n1_2, n2_1, name_n2)
    #             else:
    #                 self.merge_nodes(n1_1, n2_2, name_n1)
    #     else:
    #         self.merge_nodes(n1_1, n2_1, name_n1)
    #         self.merge_nodes(n1_2, n2_2, name_n2)
    #         self.R.add_edge(name_n1, name_n2)

    # def clone_edge(self, n1, n2, new_n1, new_n2):
    #     """ Clones an edge """
    #     self.clone_node(n1, new_n1)
    #     self.clone_node(n2, new_n2)
    #     self.R.add_edge(new_n1, new_n2)

    # def relabel_node(self, n, node_name):
    #     """ Relabels a node """
    #     if n in self.base_nodes:
    #         if not n in self.P.nodes():
    #             self.P.add_node(n,
    #                             self.G.node[n].type_,
    #                             self.G.node[n].attrs_)
    #         if not n in self.L.nodes():
    #             self.L.add_node(n,
    #                             self.G.node[n].type_,
    #                             self.G.node[n].attrs_)
    #             self.P_L_dict[n] = n
    #         self.base_nodes.remove(n)

    #     if n in self.R.nodes():
    #         self.R.relabel_node(n, node_name)
    #     else:
    #         self.R.add_node(node_name,
    #                         self.P.node[n].type_,
    #                         self.P.node[n].attrs_)
    #         self.P_R_dict[n] = node_name
    #     pred = keys_by_value(self.P_R_dict, n)
    #     for n0 in pred:
    #         self.P_R_dict[n0] = node_name

    def merge_node_list(self, node_list, node_name=None):
        """ Merge a list of nodes """
        if len(node_list) > 1:
            node_name = self.merge_nodes(node_list[0], node_list[1], node_name)
            for i in range(2, len(node_list)):
                node_name = self.merge_nodes(node_list[i], node_name, node_name)
        else:
            warnings.warn(
                "Cannot merge less than two nodes!", RuntimeWarning
            )


#     def appendToNodesNames(self, token):
#         self.P = self.P.appendToNodesNames(token)
#         self.R = self.R.appendToNodesNames(token)
#         self.L = self.L.appendToNodesNames(token)
#         self.P_R_dict = {(str(k) + "_" + str(token)): (str(v) + "_" + str(token)) for (k, v) in self.P_R_dict.items()}
#         self.P_L_dict = {(str(k) + "_" + str(token)): (str(v) + "_" + str(token)) for (k, v) in self.P_L_dict.items()}

#     def validNewMetamodel(self, new_meta_model):
#         return(all([g.validNewMetamodel for g in [self.G, self.P, self.R, self.L]]))

#     def updateMetaModel(self, new_meta_model):
#         self.G.updateMetamodel(new_meta_model)
#         self.P.updateMetamodel(new_meta_model)
#         self.R.updateMetamodel(new_meta_model)
#         self.L.updateMetamodel(new_meta_model)

    def remove_by_type(self, type_to_remove):
        nodes_removed_from_p = self.P.remove_type(type_to_remove)
        
        for n in nodes_removed_from_p:
            del self.p_lhs[n]
            del self.p_rhs[n]
        self.rhs.remove_by_type(type_to_remove)
        self.lhs.remove_by_type(type_to_remove)

    def convert_type(self, old_type, new_type):
        self.G.convertType(old_type, new_type)
        self.P.convertType(old_type, new_type)
        self.R.convertType(old_type, new_type)
        self.L.convertType(old_type, new_type)

    def removeEdgesByType(self,source_type,target_type): 
        self.G.removeEdgesByType(source_type,target_type) 
        self.P.removeEdgesByType(source_type,target_type) 
        self.R.removeEdgesByType(source_type,target_type) 
        self.L.removeEdgesByType(source_type,target_type) 

class Rewriter(object):
    """Rewriter object incapsulates graph hierarchy and performs
       applications of the rules to the given graph alongside with
       propagation of the changes up the hierarchy.
    """
    def __init__(self, graph, ignore_types=False, ignore_attrs=False):
        # if graph is not None:
        #     if graph.typing_graph is not None:
        #         if ignore_types is True:
        #             raise ValueError("Input graph has a typing graph, cannot initialize a type ignoring Rewriter!")
        self.graph = graph
        self.ignore_types = ignore_types
        self.ignore_attrs = ignore_attrs
        return
        
    # @classmethod
    # def from_graph(cls, graph):
    #     """Initialize Rewriter from a signle graph."""
    #     # hierarchy = Hierarchy(graph)
    #     # return cls(hierarchy)
    #     pass

    def find_matching(self, pattern):
        """Perform matching of the pattern graph."""
        # NetworkX isomorphism lib crushes if the ids of nodes
        # have different types (e.g ints and strings).
        # For the sake of security we will temporarily make
        # all the nodes ids to be int
        labels_mapping = dict([(n, i + 1) for i, n in enumerate(self.graph.nodes())])
        g = self.graph.relabel_nodes(labels_mapping)
        matching_nodes = set()

        # find all the nodes matching the nodes in pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if self.ignore_types is False:
                    if pattern.node[pattern_node].type_ == g.node[node].type_:
                        if self.ignore_attrs or valid_attributes(pattern.node[pattern_node].attrs_,
                                                                 g.node[node]):
                            matching_nodes.add(node)
                else:
                    if self.ignore_attrs or valid_attributes(pattern.node[pattern_node].attrs_,
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
                if not self.ignore_attrs and not valid_attributes(pattern.node[pattern_node].attrs_, subgraph.node[node]):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.get_edge(edge[0], edge[1])
                    target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
                    if not self.ignore_attrs and not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # bring back original labeling
        inverse_mapping = dict([(value, key) for key, value in labels_mapping.items()])
        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]
        return instances

    def apply_rule(self, instance, rule, level=None):
        """Apply rule at the given level of the hierarchy."""

        # if self.graphs.typing_graph:
        #     if rule.typing_graph != self.graph.typing_graph:
        #         raise ValueError("Typing graphs of the rule and the graph do not match!")
        
        p_lhs = Homomorphism(rule.p, rule.lhs, rule.p_lhs)
        p_rhs = Homomorphism(rule.p, rule.rhs, rule.p_rhs)
        l_g = Homomorphism(rule.lhs, self.graph, instance)

        (g_m, p_g_m, g_m_g) = pullback_complement(p_lhs, l_g)
        (g_prime, g_m_g_prime, r_g_prime) = pushout(p_g_m, p_rhs)
        # print(p_g_m)
        # print(g_prime)           

    def propagate(self):
        """Propagate some changes if they were made."""
        pass

    def apply_propagate(self, rule, level=None):
        """Apply rule at the given level and propagate the changes up."""
        pass



# class Rewriter:
#     """Class implements the transformation on the graph."""

#     def __init__(self, graph=None):
#         """Initialize Rewriter object with input graph."""
#         self.graph_ = graph
#         self.parser_ = parser
#         return

#     def __doc__(self):
#         return "A Rewriter instance alows you to do a horizontal rewrite on "+\
#                 "a single graph, it also gives the needed informations (the "+\
#                 "G- -> G and G- -> Gprime homomorphisms) to propagate that "+\
#                 "change in the GraphModeler"

#     @staticmethod
#     def rewrite_simple(trans, get_details=False):
#        return(Rewriter.rewrite(Homomorphism.identity(trans.L,trans.G),trans,get_details))
       
#     @staticmethod
#     def rewrite(L_G, trans, get_details=False):
#         """ Simple rewriting using category operations """
#         left_h, right_h = trans.get()
#         graph = trans.G

#         if left_h.source_ != right_h.source_:
#             raise ValueError(
#                 "Can't rewrite, homomorphisms don't have the same preserved part"
#             )
#         Gm, P_Gm, Gm_G = pullback_complement(left_h, L_G)
#         Gprime, Gm_Gprime, R_Gprime = pushout(P_Gm, right_h)

#         for n in Gm.nodes():
#             n2 = Gm_G[n]
#             if graph.node[n2].attributes_typing:
#                 Gprime.node[Gm_Gprime[n]].attributes_typing = copy.deepcopy(graph.node[n2].attributes_typing)

#         Gprime.metamodel_ = graph.metamodel_
#         if graph.graph_attr:
#             Gprime.graph_attr = copy.deepcopy(graph.graph_attr) 
#         Gprime.hom = TypedHomomorphism.canonic(Gprime, graph.metamodel_)
        
#         if get_details:
#             return Gm_Gprime, Gm_G
#         else:
#             return Gprime

#     @staticmethod
#     def do_canonical_rewrite(G, transformations, get_details=False):
#         """ Does a simple rewriting by decomposing the transformations string
#             into a list of canonical transformations strings """
#         di = type(G) == TypedDiGraph
#         trans_list = Rewriter.make_canonical_commands(G, transformations, di)
#         return Rewriter.chain_rewrite(G, trans_list, get_details)

#     def do_rewrite(G, transformations, get_details=False):
#         trans = Rewriter.transformer_from_command(G, transformations)
#         L_G = Homomorphism.identity(trans.L, trans.G)
#         return Rewriter.rewrite(L_G, trans, get_details)

#     @staticmethod
#     def chain_rewrite(G, trans_list, get_details=False):
#         """ Does multiple simple rewritings on G given a list of transformations """
#         res = []
#         for transformation in trans_list:
#             if get_details:
#                 trans = Rewriter.transformer_from_command(res[-1][0].target_ if res != [] else G, transformation)
#                 rw_res = Rewriter.rewrite(Homomorphism.identity(trans.L,
#                                                                 trans.G),
#                                           trans,
#                                           get_details)
#                 res.append(rw_res)
#             else:
#                 trans = Rewriter.transformer_from_command(res[-1] if res != [] else G, transformation)
#                 rw_res = Rewriter.rewrite(Homomorphism.identity(trans.L,
#                                                                 trans.G),
#                                           trans,
#                                           get_details)
#                 res = [rw_res]
#         if get_details:
#             return res
#         else:
#             return res[0]


#     @staticmethod
#     def find_matching(graph, pattern, ignore_attrs = False):
#         """Perform matching of the pattern graph."""
#         # NetworkX isomorphism lib crushes if the ids of nodes
#         # have different types (e.g ints and strings).
#         # For the sake of security we will temporarily make
#         # all the nodes ids to be int
#         labels_mapping = dict([(n, i + 1) for i, n in enumerate(graph.nodes())])
#         g = graph.relabel_nodes(labels_mapping)
#         matching_nodes = set()
#         # find all the nodes matching the nodes in pattern
#         for pattern_node in pattern.nodes():
#             for node in g.nodes():
#                 if pattern.node[pattern_node].type_ == g.node[node].type_:
#                     # if ignore_attrs or is_subdict(pattern.node[pattern_node].attrs_,
#                     #                                     g.node[node].attrs_):
#                     #     matching_nodes.add(node)
#                     if ignore_attrs or valid_attributes(pattern.node[pattern_node].attrs_,
#                                                         g.node[node]):
#                         matching_nodes.add(node)
#         reduced_graph = g.subgraph(matching_nodes)
#         instances = []
#         isomorphic_subgraphs = []
#         for sub_nodes in itertools.combinations(reduced_graph.nodes(),
#                                                 len(pattern.nodes())):
#                 subg = reduced_graph.subgraph(sub_nodes)
#                 for edgeset in itertools.combinations(subg.edges(),
#                                                       len(pattern.edges())):
#                     if g.is_directed():
#                         edge_induced_graph = nx.DiGraph(list(edgeset))
#                         edge_induced_graph.add_nodes_from(
#                             [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
#                         GM = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
#                         for isom in GM.isomorphisms_iter():
#                             isomorphic_subgraphs.append((subg, isom))
#                     else:
#                         edge_induced_graph = nx.Graph(edgeset)
#                         edge_induced_graph.add_nodes_from(
#                             [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
#                         GM = isomorphism.GraphMatcher(pattern, edge_induced_graph)
#                         for isom in GM.isomorphisms_iter():
#                             isomorphic_subgraphs.append((subg, isom))
#         for subgraph, mapping in isomorphic_subgraphs:
#             # check node matches
#             # exclude subgraphs which nodes information does not
#             # correspond to pattern
#             for (pattern_node, node) in mapping.items():
#                 if not pattern.node[pattern_node].type_ == subgraph.node[node].type_:
#                     break
#                 # if not ignore_attrs and not is_subdict(pattern.node[pattern_node].attrs_, subgraph.node[node].attrs_):
#                 if not ignore_attrs and not valid_attributes(pattern.node[pattern_node].attrs_, subgraph.node[node]):
#                     break
#             else:
#                 # check edge attribute matched
#                 for edge in pattern.edges():
#                     pattern_attrs = pattern.get_edge(edge[0], edge[1])
#                     target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
#                     if not ignore_attrs and not is_subdict(pattern_attrs, target_attrs):
#                         break
#                 else:
#                     instances.append(mapping)

#         # bring back original labeling
#         inverse_mapping = dict([(value, key) for key, value in labels_mapping.items()])
#         for instance in instances:
#             for key, value in instance.items():
#                 instance[key] = inverse_mapping[value]
#         return instances

#     @staticmethod
#     def transformer_from_command(G, commands):
#         """Cast sequence of commands to Transformer instance."""
#         command_strings = [c for c in commands.splitlines() if len(c) > 0]
#         actions = []
#         for command in command_strings:
#             try:
#                 parsed = parser.parseString(command).asDict()
#                 actions.append(parsed)
#             except:
#                 raise ValueError("Cannot parse command '%s'" % command)

#         trans = Transformer(G)

#         for action in actions:
#             if action["keyword"] == "clone":
#                 node_name = None
#                 if "node_name" in action.keys():
#                     node_name = action["node_name"]
#                 trans.clone_node(action["node"], node_name)
#             elif action["keyword"] == "merge":
#                 method = None
#                 node_name = None
#                 edges_method = None
#                 if "method" in action.keys():
#                     method = action["method"]
#                 if "node_name" in action.keys():
#                     node_name = action["node_name"]
#                 if "edges_method" in action.keys():
#                     edges_method = action["edges_method"]
#                 merged_node = trans.merge_nodes_list(
#                     action["nodes"],
#                     node_name)
#             elif action["keyword"] == "add_node":
#                 name = None
#                 node_type = None
#                 attrs = {}
#                 if "node" in action.keys():
#                     name = action["node"]
#                 if "type" in action.keys():
#                     node_type = action["type"]
#                 if "attributes" in action.keys():
#                     attrs = action["attributes"]
#                 trans.add_node(name, node_type, attrs)
#             elif action["keyword"] == "delete_node":
#                 trans.remove_node(action["node"])
#             elif action["keyword"] == "add_edge":
#                 attrs = {}
#                 if "attributes" in action.keys():
#                     attrs = action["attributes"]
#                 trans.add_edge(
#                     action["node_1"],
#                     action["node_2"],
#                     attrs)
#             elif action["keyword"] == "delete_edge":
#                 trans.remove_edge(
#                     action["node_1"],
#                     action["node_2"])
#             elif action["keyword"] == "add_node_attrs":
#                 trans.add_node_attrs(
#                     action["node"],
#                     action["attributes"])
#             elif action["keyword"] == "add_edge_attrs":
#                 trans.add_edge_attrs(
#                     action["node_1"],
#                     action["node_2"],
#                     action["attributes"])
#             elif action["keyword"] == "delete_node_attrs":
#                 trans.remove_node_attrs(
#                     action["node"],
#                     action["attributes"])
#             elif action["keyword"] == "delete_edge_attrs":
#                 trans.remove_edge_attrs(
#                     action["node_1"],
#                     action["node_2"],
#                     action["attributes"])
#             else:
#                 raise ValueError("Unknown command %s" % action["keyword"])
#         return trans

#     def apply_rule(self, L_G, trans):

#         left_h, right_h = trans.get()

#         # check left_h.source == right_h.source
#         if left_h.source_.nodes() != right_h.source_.nodes():
#             raise ValueError("Preserving part does not match!")
#         if left_h.source_.edges() != right_h.source_.edges():
#             raise ValueError("Preserving part does not match!")
#         instance = L_G.mapping_
#         RHS_instance =\
#             dict([(r, instance[left_h.mapping_[p]]) for p, r in right_h.mapping_.items()])
#         P_instance =\
#             dict([(p, instance[l]) for p, l in left_h.mapping_.items()])

#         (nodes_to_remove,
#          edges_to_remove,
#          node_attrs_to_remove,
#          edge_attrs_to_remove) = left_h.find_final_PBC()

#         (nodes_to_add,
#          edges_to_add,
#          node_attrs_to_add,
#          edge_attrs_to_add) = right_h.find_PO()

#         # 1) Delete nodes/edges
#         for node in nodes_to_remove:
#             self.graph_.remove_node(node)

#         merge_dict = {}
#         for n in right_h.target_.nodes():
#             merge_dict.update({n: []})
#         for p_node, r_node in right_h.mapping_.items():
#             if left_h.mapping_[p_node] not in nodes_to_remove:
#                 merge_dict[r_node].append(p_node)
#         nodes_to_merge =\
#             dict([(key, value) for key, value in merge_dict.items()
#                   if len(value) > 1])

#         # 2) Clone nodes
#         clone_dict = {}
#         for n in left_h.target_.nodes():
#             clone_dict.update({n: []})
#         for p_node, r_node in left_h.mapping_.items():
#             clone_dict[r_node].append(p_node)
#         for node, value in clone_dict.items():
#             if value is not None and len(value) > 1:
#                 i = 0
#                 for val in value:
#                     will_be_merged = False
#                     for r_node, p_nodes in nodes_to_merge.items():
#                         if val in p_nodes:
#                             will_be_merged = True
#                     if i > 0:
#                         if node != val:
#                             new_name = self.graph_.clone_node(node, val)
#                             P_instance.update(
#                                 {val: new_name})
#                             if not will_be_merged:
#                                 RHS_instance.update(
#                                     {right_h.mapping_[val]: new_name})
#                     else:
#                         P_instance.update(
#                             {val: instance[node]})
#                         if not will_be_merged:
#                             RHS_instance.update(
#                                 {right_h.mapping_[val]: instance[node]})
#                     i += 1

#         for edge in edges_to_remove:
#             if (edge[0],edge[1]) in self.graph_.edges():
#                 self.graph_.remove_edge(
#                     edge[0],
#                     edge[1])

#         # 3) Delete attrs
#         for node, attrs in node_attrs_to_remove.items():
#             if len(attrs) > 0:
#                 self.graph_.remove_node_attrs(
#                     node,
#                     attrs)

#         for edge, attrs in edge_attrs_to_remove.items():
#             self.graph_.remove_edge_attrs(
#                 edge[0],
#                 edge[1],
#                 attrs)

#         # 4) Add attrs
#         for node, attrs in node_attrs_to_add.items():
#             if len(attrs) > 0:
#                 self.graph_.add_node_attrs(node, attrs)

#         for edge, attrs in edge_attrs_to_add.items():
#             self.graph_.add_edge_attrs(
#                 edge[0],
#                 edge[1],
#                 attrs)

#         # 5) Merge
#         for rhs_node, nodes in nodes_to_merge.items():
#             new_name = self.graph_.merge_nodes(nodes, node_name=rhs_node)
#             RHS_instance.update({rhs_node: new_name})

#         # 6) Add nodes/edges
#         for node in nodes_to_add:
#             self.graph_.add_node(
#                 node,
#                 right_h.target_.node[node].type_,
#                 attrs=right_h.target_.node[node].attrs_)
#             RHS_instance.update({node: node})

#         for edge, attrs in edges_to_add.items():
#             try:
#                 self.graph_.add_edge(
#                     edge[0],
#                     edge[1],
#                     attrs)
#             except:
#                 pass
#         return RHS_instance

#     @staticmethod
#     def gen_transformations(n, graph, p_opt=0.5, merge_prop_av = 0.2,
#                             merge_prop_dev = 0.05, p_attrs = 0.5, p_attrs_value=0.5):

#         def rand_attrs(attrs):
#             """ Picks random attributes from attrs using the probabilities in
#                 the main function arguments """
#             if attrs is None:
#                 return {}

#             new_attrs = {}
#             for k,v in attrs.items():
#                 if random.random() <= p_attrs:
#                     value = []
#                     for val in v:
#                         if random.random() <= p_attrs_value:
#                             value.append(val)
#                     new_attrs[k] = set(value)
#             keys_to_remove = []
#             for k,v in new_attrs.items():
#                 if v == set():
#                     keys_to_remove.append(k)
#             for k in keys_to_remove:
#                 new_attrs.pop(k)
#             return new_attrs

#         trans = []
#         env = graph.copy()
#         base_nodes = [n for n in graph.nodes()]
#         if graph.metamodel_ is None:
#             types = ["anything"]
#         else:
#             types = graph.metamodel_.nodes()
#         actions = [
#             "CLONE",
#             "MERGE",
#             "ADD_NODE",
#             "DELETE_NODE",
#             "ADD_EDGE",
#             "DELETE_EDGE",
#             "ADD_NODE_ATTRS",
#             "ADD_EDGE_ATTRS",
#             "DELETE_NODE_ATTRS",
#             "DELETE_EDGE_ATTRS"
#         ]

#         def pick_node():
#             """ Picks a node in the graph if possible """
#             if len(base_nodes) > 0:
#                 return random.sample(base_nodes, 1)[0]
#             else:
#                 return None

#         def pick_nodes():
#             """ Picks multiple node (a random number following a gaussian law
#                 with parameters merge_prop_av and merge_prop_dev) if possible """
#             if env.metamodel_ is None:
#                 ty = random.choice([None, "anything"])
#             else:
#                 ty = pick_type()
#             node_list = [n for n in base_nodes if env.node[n].type_ == ty]
#             n = abs(int(random.gauss(merge_prop_av*len(node_list),
#                                      merge_prop_dev*len(node_list))))
#             while n < 2 and len(node_list) > 5:
#                 n = abs(int(random.gauss(merge_prop_av*len(node_list),
#                                          merge_prop_dev*len(node_list))))
#             if n < 2:
#                 return []
#             res = []
#             for node in random.sample(node_list, n):
#                 res.append(node)
#             return res

#         def pick_edge():
#             """ Picks an existing edge if possible """
#             if len(env.edges()) > 0 and len(base_nodes) > 1:
#                 edge = random.sample(env.edges(), 1)[0]
#                 if edge[0] in base_nodes and edge[1] in base_nodes:
#                     return edge
#             return None,None

#         def pick_new_edge():
#             """ Picks two nodes that can have an edge between them and don't yet
#                 if possible """
#             i = 500
#             while i > 0:
#                 n1 = pick_node()
#                 n2 = pick_node()
#                 if n1 is not None and n2 is not None:
#                     if env.metamodel_ is None or\
#                        (env.node[n1].type_, env.node[n2].type_) in env.metamodel_.edges() and\
#                        (n1, n2) not in env.edges() and n1 != n2:
#                         return (n1, n2)
#                     else:
#                         i-=1
#             return None

#         def pick_type():
#             """ Picks a type """
#             return random.sample(types, 1)[0]

#         def pick_attrs_from(node):
#             """ Picks random attrs from the attrs of node """
#             return rand_attrs(env.node[node].attrs_)

#         def pick_attrs_for(node):
#             """ Picks random attrs from the attrs of the typing node of node """
#             if graph.metamodel_ is None:
#                 return {}
#             else:
#                 return rand_attrs(graph.metamodel_.node[env.node[node].type_].attrs_)

#         def pick_edge_attrs_from(n1, n2):
#             """ Picks random attrs from the attrs of edge """
#             return rand_attrs(env.get_edge(n1, n2))

#         def pick_edge_attrs_for(n1, n2):
#             """ Picks random attrs from the attrs of the typing edge of edge """
#             if env.metamodel_ is None:
#                 return {}
#             else:
#                 return rand_attrs(env.metamodel_.get_edge(
#                     env.node[n1].type_,
#                     env.node[n2].type_
#                 ))

#         def pick_name():
#             """ Picks a node_name that isn't in the graph yet """
#             i = random.randint(0, 500)
#             if len(env.nodes()) > 1:
#                 generated_name = ".".join(random.sample(env.nodes(), 2))
#             else:
#                 generated_name = "newNode"+str(i)
#             while str(generated_name) in env.nodes():
#                 i = random.randint(0, 500)
#                 if len(env.nodes()) > 1:
#                     generated_name = ".".join(random.sample(env.nodes(), 2))
#                 else:
#                     generated_name = "newNode"+str(i)
#             return str(generated_name)

#         def pick_method():
#             """ Picks a method to use for merging """
#             return random.choice(["UNION", "INTERSECTION"])

#         def add_req(op, s):
#             """ Updates the transformation list with a required argument """
#             op += s
#             return op

#         def add_opt(op, s):
#             """ Updates the transformation list with an optional argument """
#             if random.random() <= p_opt:
#                 op += s
#                 return True, op
#             else:
#                 return False, op

#         # We pick a random operation each time and try to do it

#         while len(trans) < n:
#             op = random.choice(actions)
#             if op == "CLONE":
#                 node = pick_node()
#                 if node is None or "_" in node:
#                     continue
#                 name = pick_name()

#                 op = add_req(op, " '%s'" % str(node))
#                 opt,op = add_opt(op, " AS '%s'" % str(name))
#                 if not opt:
#                     name = None
#                 else:
#                     base_nodes.append(name)

#                 env.clone_node(node, name)
#                 trans.append(op)
#             elif op == "MERGE":
#                 nodes = pick_nodes()
#                 if nodes == []:
#                     continue
#                 method = pick_method()
#                 new_name = pick_name()
#                 edges = pick_method()
#                 new_node_attrs = None
#                 new_edge_attrs = None

#                 op = add_req(op, " "+str(nodes))
#                 opt,op = add_opt(op, " METHOD "+str(method))
#                 if not opt:
#                     method = "UNION"
#                 opt,op = add_opt(op, " AS '%s'" % str(new_name))
#                 if not opt:
#                     new_name = None
#                 else:
#                     base_nodes.append(new_name)
#                 opt,op = add_opt(op, " EDGES "+str(edges))
#                 if not opt:
#                     edges = "UNION"

#                 if nodes != []:
#                     env.merge_nodes(nodes,
#                                 method.lower(),
#                                 new_name,
#                                 edges.lower())
#                 for node in nodes:
#                     base_nodes.remove(node)

#                 trans.append(op)
#             elif op == "ADD_NODE":
#                 name = pick_name()
#                 typ = pick_type()

#                 attrs = rand_attrs(env.metamodel_.node[typ].attrs_)

#                 op = add_req(op, " '%s'" % str(name))
#                 op = add_req(op, " TYPE '%s'" % str(typ))
#                 opt,op = add_opt(op, " "+str(attrs))
#                 if not opt:
#                     attrs = None

#                 base_nodes.append(name)
#                 env.add_node(name, typ, attrs)
#                 trans.append(op)
#             elif op == "DELETE_NODE":
#                 node = pick_node()
#                 if node is None:
#                     continue

#                 op = add_req(op, " '%s'" % str(node))

#                 base_nodes.remove(node)
#                 env.remove_node(node)
#                 trans.append(op)
#             elif op == "ADD_EDGE":
#                 e = pick_new_edge()
#                 if e is None:
#                     continue
#                 else:
#                     n1, n2 = e
#                 attrs = pick_edge_attrs_for(n1, n2)

#                 op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))
#                 opt,op = add_opt(op, " "+str(attrs))
#                 if not opt:
#                     attrs = None

#                 env.add_edge(n1, n2, attrs)
#                 trans.append(op)
#             elif op == "DELETE_EDGE":
#                 n1, n2 = pick_edge()
#                 if n1 is None or n2 is None:
#                     continue

#                 op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))

#                 env.remove_edge(n1, n2)
#                 trans.append(op)
#             elif op == "ADD_NODE_ATTRS":
#                 node = pick_node()
#                 if node is None:
#                     continue
#                 if env.metamodel_ is None:
#                     attrs = {}
#                 else:
#                     if env.metamodel_.node[env.node[node].type_].attrs_ is None:
#                         attrs = {}
#                     else:
#                         attrs = rand_attrs(dict_sub(env.metamodel_.node[env.node[node].type_].attrs_,
#                                             env.node[node].attrs_))

#                 op = add_req(op, " '%s'" % node)
#                 op = add_req(op, " "+str(attrs))

#                 if attrs == {}:
#                     continue

#                 env.add_node_attrs(node, attrs)
#                 trans.append(op)
#             elif op == "ADD_EDGE_ATTRS":
#                 n1, n2 = pick_edge()
#                 if n1 is None or n2 is None:
#                     continue
#                 if env.metamodel_ is None:
#                     attrs = {}
#                 else:
#                     attrs = rand_attrs(dict_sub(
#                         env.metamodel_.get_edge(
#                             env.node[n1].type_,
#                             env.node[n2].type_),
#                         env.get_edge(n1, n2)
#                         )
#                     )

#                 op = add_req(op, " '%s' '%s'" % (n1,n2))
#                 op = add_req(op, " "+str(attrs))

#                 if attrs == {}:
#                     continue

#                 env.add_edge_attrs(n1, n2, attrs)
#                 trans.append(op)
#             elif op == "DELETE_NODE_ATTRS":
#                 node = pick_node()
#                 if node is None:
#                     continue
#                 attrs = pick_attrs_from(node)

#                 if attrs == {} or attrs is None:
#                     continue

#                 op = add_req(op, " '%s'" % node)
#                 op = add_req(op, " "+str(attrs))

#                 env.remove_node_attrs(node, attrs)
#                 trans.append(op)
#             elif op == "DELETE_EDGE_ATTRS":
#                 n1, n2 = pick_edge()
#                 if n1 is None or n2 is None:
#                     continue
#                 attrs = pick_edge_attrs_from(n1, n2)

#                 if attrs == {} or attrs is None:
#                     continue

#                 op = add_req(op, " '%s' '%s'" % (n1,n2))
#                 op = add_req(op, " "+str(attrs))

#                 env.remove_edge_attrs(n1, n2, attrs)
#                 trans.append(op)
#             else:
#                 raise ValueError(
#                     "Unknown action"
#                 )

#         return ".\n".join(trans)+"."
