"""Docs here."""
import copy
import warnings

# from regraph.library.parser import parser
from regraph.library.utils import (keys_by_value,
                                   identity)
#                                    make_canonical_commands)
from regraph.library import primitives


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
                 p_rhs=None, ignore_attrs=False):
        """Initialize a rule by p, lhs and rhs and two homomorphisms:
        p -> lhs & p -> rhs. By default the homomorphisms are None, and
        they are created as Homomorphism.identity(p, lhs) etc with the
        correspondance according to the node names."""
        self.p = copy.deepcopy(p)
        self.lhs = copy.deepcopy(lhs)
        self.rhs = copy.deepcopy(rhs)
        self.ignore_attrs = ignore_attrs

        if not p_lhs:
            self.p_lhs = identity(p, lhs)
        else:
            self.p_lhs = copy.deepcopy(p_lhs)

        if not p_rhs:
            self.p_rhs = identity(p, rhs)
        else:
            self.p_rhs = copy.deepcopy(p_rhs)
        return

    def __eq__(self, rule):
        return (
            self.p == rule.p and
            self.lhs == rule.lhs and
            self.rhs == rule.rhs and
            self.p_lhs == rule.p_lhs and
            self.p_rhs == rule.p_rhs and
            self.ignore_attrs == rule.ignore_attrs
        )

    def __str__(self):
        return "Preserved part\n%s\n" % self.p +\
               "Left hand side\n%s\n" % self.lhs +\
               "P->L Homomorphism : %s\n" % self.p_lhs +\
               "Right hand side\n%s\n" % self.rhs +\
               "P->R Homomorphism : %s\n" % self.p_rhs

    def __doc__(self):
        return(
            "An instance of rule is an instance of `p` (preserved part), " +\
            "`lhs` (lef-hand side of the rule) and `rhs` (right-hand side) graphs " +\
            "together with two mappings p -> lhs & p -> rhs."
        )

    def add_node(self, node_id, attrs=None):
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
            primitives.add_node(self.rhs, node_id, attrs)
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
                primitives.remove_node(self.p, k)
            if self.p_rhs[k] in self.rhs.nodes():
                primitives.remove_node(self.rhs, self.p_rhs[k])
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
                    primitives.add_edge(self.rhs, rhs_key_1, rhs_key_2, attrs)
                else:
                    if (rhs_key_1, rhs_key_2) in self.rhs.edges() or\
                       (rhs_key_2, rhs_key_1) in self.rhs.edges():
                        raise ValueError(
                            "Edge %s-%s already exists in the right hand side of the rule" % 
                            (rhs_key_1, rhs_key_2)
                        )
                    primitives.add_edge(self.rhs, rhs_key_1, rhs_key_2, attrs)
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
                    primitives.remove_edge(self.p, k1, k2)
                    primitives.remove_edge(self.rhs, rhs_key_1, rhs_key_2)
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
                    primitives.remove_edge(self.p, k1, k2)
        return

    def clone_node(self, n, node_name=None):
        """Clone a node of the graph."""
        p_new_nodes = []
        rhs_new_nodes = []
        p_keys = keys_by_value(self.p_lhs, n)
        for k in p_keys:

            p_new_node = primitives.clone_node(self.p, k)
            p_new_nodes.append(p_new_node)
            rhs_new_node = primitives.clone_node(self.rhs, self.p_rhs[k])
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

        new_name = primitives.merge_nodes(self.rhs, list(nodes_to_merge))
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
            primitives.add_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def remove_node_attrs(self, n, attrs):
        """Remove nodes attributes from a node in the graph."""
        if n not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n)

        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise ValueError(
                "Node %s is being removed by the rule, cannot remove attributes" % n)

        for k in p_keys:
            primitives.remove_node_attrs(self.p, k, attrs)
            primitives.remove_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def update_node_attrs(self, n, attrs):
        """Update attributes of a node."""
        if n not in self.lhs.nodes():
            raise ValueError(
                "Node %s does not exist in the left hand side of the rule" % n)

        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise ValueError(
                "Node %s is being removed by the rule, cannot update attributes" % n)
        for k in p_keys:
            self.p.node[k] = None
            primitives.update_node_attrs(self.rhs, self.p_rhs[k], attrs)
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
                    primitives.add_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
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
                    primitives.add_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
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
                    primitives.remove_edge_attrs(self.p, k1, k2, attrs)
                    primitives.remove_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
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
                    primitives.remove_edge_attrs(
                        self.p,
                        k1,
                        k2,
                        attrs
                    )
                    primitives.remove_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
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
                    primitives.update_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
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
                    primitives.update_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        return

    # Advanced operations (???)

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
        """Merge a list of nodes."""
        if len(node_list) > 1:
            node_name = self.merge_nodes(node_list[0], node_list[1], node_name)
            for i in range(2, len(node_list)):
                node_name = self.merge_nodes(node_list[i], node_name, node_name)
        else:
            warnings.warn(
                "Cannot merge less than two nodes!", RuntimeWarning
            )
