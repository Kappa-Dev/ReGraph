"""Graph rewriting rules.

This package contains the `Rule` data structure for representation
of graph rewriting rules (for more on sesqui-pushout rewriting see:
https://link.springer.com/chapter/10.1007/11841883_4).
"""
import copy
import warnings

from regraph.parser import parser
from regraph.utils import (keys_by_value,
                           normalize_attrs,
                           make_canonical_commands,
                           dict_sub,
                           attrs_union)
from regraph.category_op import (identity,
                                 check_homomorphism,
                                 pullback_complement,
                                 pushout)
from regraph import primitives
from regraph.exceptions import (ReGraphWarning, ParsingError, RuleError,
                                GraphError)


class Rule(object):
    """Class representing rewriting rules.

    A rewriting rule consists of the three graphs:
    `p` -- preserved part, `lhs` -- left hand side,
    `rhs` -- right hand side, and two mappings:
    from `p` to `lhs` and from `p` to `rhs`.
    Informally, `lhs` represents a pattern to match
    in a graph, subject to rewriting. `p` together with
    `p` -> `lhs` mapping specifies a part of
    the pattern which stays preseved during rewriting,
    i.e. all the nodes/edges/attributes present
    in `lhs` but not `p` will be removed.
    `rhs` and `p` -> `rhs` specify nodes/edges/attributes
    to add to the `p`. In addition, rules defined
    is such a way allow to clone and merge nodes.
    If two nodes from `p` map to the same node in `lhs`,
    the node corresponding to this node of the
    pattern will be cloned. Symmetrically, if two nodes
    from `p` map to the same node in `rhs`,
    the corresponding two nodes will be merged.

    Attributes
    ----------
    p : networkx.(Di)Graph
        Preserved part of the rule
    lhs : networkx.(Di)Graph
        Left-hand side (pattern) of the rule
    rhs : networkx.(Di)Graph
        Right-hand side of the rule
    p_lhs : dict
        Homomorphism between `p` and `lhs` given by
        a dictionary with keys -- nodes of `p`,
        values -- nodes of `lhs`.
    p_rhs : dict
        Homomorphism between `p` and `rhs` given by
        a dictionary with keys -- nodes of `p`,
        values -- nodes of `rhs`.
    """

    def __init__(self, p, lhs, rhs, p_lhs=None, p_rhs=None):
        """Rule initialization.

        A rule is initialized with p, lhs, rhs graphs, and
        p -> lhs & p -> rhs homomorphisms, these homomorphisms
        are checked to be valid ones (edge and attribute preserving).
        By default the homomorphisms p -> lhs & p -> rhs are None,
        in this case they are initialized as the identity homomorphism
        (id(p)).

        Parameters
        ----------
        p : networkx.(Di)Graph
            Preserved part of the rule
        lhs : networkx.(Di)Graph
            Left-hand side (pattern) of the rule
        rhs : networkx.(Di)Graph
            Right-hand side of the rule
        p_lhs : dict
            Homomorphism between `p` and `lhs` given by
            a dictionary with keys -- nodes of `p`,
            values -- nodes of `lhs`
        p_rhs : dict
            Homomorphism between `p` and `rhs` given by
            a dictionary with keys -- nodes of `p`,
            values -- nodes of `rhs`
        """
        if not p_lhs:
            self.p_lhs = identity(p, lhs)
        else:
            check_homomorphism(p, lhs, p_lhs)
            self.p_lhs = copy.deepcopy(p_lhs)

        if not p_rhs:
            self.p_rhs = identity(p, rhs)
        else:
            check_homomorphism(p, rhs, p_rhs)
            self.p_rhs = copy.deepcopy(p_rhs)

        self.p = copy.deepcopy(p)
        self.lhs = copy.deepcopy(lhs)
        self.rhs = copy.deepcopy(rhs)

        return

    @classmethod
    def from_transform(cls, pattern, commands=None):
        """Initialize a rule from the transformation.

        On input takes a pattern which is used as `lhs` of the rule,
        as an optional argument transformation commands can be provided,
        by default the list of commands is empty and all `p`, `lhs` and `rhs`
        are initialized to be the same graph (pattern), later on
        when transformations are applied `p` and `rhs` are being updated.
        If list of commands is specified, these commands are simplified,
        transformed to the canonical order, and applied to `p`, `lhs` and `rhs`.

        Parameters
        ----------
        pattern : networkx.(Di)Graph
            Pattern graph to initialize and the lhs of the rule.
        commands : str, optional
            Script containing transformation commands, which
            can be parsed by `regraph.parser.parse`.

        """
        p = copy.deepcopy(pattern)
        lhs = copy.deepcopy(pattern)
        rhs = copy.deepcopy(pattern)
        p_lhs = dict([(n, n) for n in pattern.nodes()])
        p_rhs = dict([(n, n) for n in pattern.nodes()])

        rule = cls(p, lhs, rhs, p_lhs, p_rhs)

        # if the commands are provided, perform respecitive transformations
        if commands:
            # 1. make the commands canonical
            commands = make_canonical_commands(p, commands, p.is_directed())
            # 2. apply the commands

            command_strings = [
                c for b in commands if len(b) > 0 for c in b.splitlines()
            ]

            actions = []
            for command in command_strings:
                try:
                    parsed = parser.parseString(command).asDict()
                    actions.append(parsed)
                except:
                    raise ParsingError("Cannot parse command '%s'" % command)

            for action in actions:
                if action["keyword"] == "clone":
                    node_name = None
                    if "node_name" in action.keys():
                        node_name = action["node_name"]
                    rule.clone_node(action["node"], node_name)
                elif action["keyword"] == "merge":
                    node_name = None
                    if "node_name" in action.keys():
                        node_name = action["node_name"]
                    merged_node = rule.merge_node_list(
                        action["nodes"],
                        node_name)
                elif action["keyword"] == "add_node":
                    name = None
                    attrs = {}
                    if "node" in action.keys():
                        name = action["node"]
                    if "attributes" in action.keys():
                        attrs = action["attributes"]
                    rule.add_node(name, attrs)
                elif action["keyword"] == "delete_node":
                    rule.remove_node(action["node"])
                elif action["keyword"] == "add_edge":
                    attrs = {}
                    if "attributes" in action.keys():
                        attrs = action["attributes"]
                    rule.add_edge_rhs(
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
                    raise ParsingError("Unknown command %s" %
                                       action["keyword"])
        return rule

    def __eq__(self, rule):
        """Rule equality operator."""
        return (
            primitives.equal(self.p, rule.p) and
            primitives.equal(self.lhs, rule.lhs) and
            primitives.equal(self.rhs, rule.rhs) and
            self.p_lhs == rule.p_lhs and
            self.p_rhs == rule.p_rhs
        )

    def __str__(self):
        """String representation of a rule."""
        return "Preserved part\n%s\n%s\n" % (self.p.node, self.p.edges()) +\
            "Left hand side\n%s\n%s\n" % (self.lhs.node, self.lhs.edges()) +\
            "P->L Homomorphism : %s\n" % self.p_lhs +\
            "Right hand side\n%s\n%s\n" % (self.rhs.node, self.rhs.edges()) +\
            "P->R Homomorphism : %s\n" % self.p_rhs

    def add_node(self, node_id, attrs=None):
        """Add node to the graph.

        Parameters
        ----------
        node_id : hashable
            Id of a node to add
        attrs : dict, optional
            Attributes of the node.

        Raises
        ------
        RuleError
            If node with this id already exists in the `rhs`.
        """
        if node_id not in self.rhs.nodes():
            p_keys = keys_by_value(self.p_rhs, node_id)
            # here we check for the nodes with the same name in the lhs
            for k in p_keys:
                lhs_key = self.p_lhs[k]
                if lhs_key == node_id:
                    raise RuleError(
                        "Node with the id '%s' already exists in the "
                        "left hand side of the rule" %
                        node_id
                    )
            primitives.add_node(self.rhs, node_id, attrs)
        else:
            raise RuleError(
                "Node with the id '%s' already exists in the "
                "right hand side of the rule" %
                node_id
            )

    def remove_node_rhs(self, n):
        """Remove a node from a rhs."""
        p_keys = keys_by_value(self.p_rhs, n)
        for p_node in p_keys:
            primitives.remove_node(self.p, p_node)
            del self.p_rhs[p_node]
            del self.p_lhs[p_node]
        primitives.remove_node(self.rhs, n)

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

    def add_edge_rhs(self, n1, n2, attrs=None):
        """Add an edge in the rhs."""
        primitives.add_edge(self.rhs, n1, n2, attrs)

    def add_edge(self, n1, n2, attrs=None):
        """Add an edge in the graph."""
        # Find nodes in p mapping to n1 & n2
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)
        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise RuleError(
                    "Node with the id '%s' does not exist in the "
                    "preserved part of the rule" % k1
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise RuleError(
                        "Node with the id '%s' does not exist in the "
                        "preserved part of the rule" % k2
                    )
                rhs_key_1 = self.p_rhs[k1]
                rhs_key_2 = self.p_rhs[k2]
                if self.rhs.is_directed():
                    if (rhs_key_1, rhs_key_2) in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' already exists in the right "
                            "hand side of the rule" %
                            (rhs_key_1, rhs_key_2)
                        )
                    primitives.add_edge(self.rhs, rhs_key_1, rhs_key_2, attrs)
                else:
                    if (rhs_key_1, rhs_key_2) in self.rhs.edges() or\
                       (rhs_key_2, rhs_key_1) in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' already exists in the right "
                            "hand side of the rule" %
                            (rhs_key_1, rhs_key_2)
                        )
                    primitives.add_edge(self.rhs, rhs_key_1, rhs_key_2, attrs)
        return

    def remove_edge_p(self, node1, node2):
        """Remove edge from the p of the graph."""
        primitives.remove_edge(self.p, node1, node2)

    def remove_edge_rhs(self, node1, node2):
        """Remove edge from the rhs of the graph."""
        primitives.remove_edge(self.rhs, node1, node2)
        for pn1 in keys_by_value(self.p_rhs, node1):
            for pn2 in keys_by_value(self.p_rhs, node2):
                print(pn1, pn2)
                try:
                    primitives.remove_edge(self.p, pn1, pn2)
                except GraphError:
                    continue

    def remove_edge(self, n1, n2):
        """Remove edge from the graph."""
        # Find nodes in p mapping to n1 & n2
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        # Remove edge from the preserved part & rhs of the rule
        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise RuleError(
                    "Node with the id '%s' does not exist in "
                    "the preserved part" % k1
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise RuleError(
                        "Node with the id '%s' does not exist in "
                        "the preserved part" % k2
                    )
                rhs_key_1 = self.p_rhs[k1]
                rhs_key_2 = self.p_rhs[k2]
                if self.p.is_directed():
                    if (k1, k2) not in self.p.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the preserved "
                            "part of the rule " % (k1, k2)
                        )
                    if (rhs_key_1, rhs_key_2) not in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the right hand "
                            "side of the rule " % (rhs_key_1, rhs_key_2)
                        )
                    primitives.remove_edge(self.p, k1, k2)
                    primitives.remove_edge(self.rhs, rhs_key_1, rhs_key_2)
                else:
                    if (k1, k2) not in self.p.edges() and\
                       (k2, k1) not in self.p.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the "
                            "preserved part of the rule " % (k1, k2)
                        )
                    if (rhs_key_1, rhs_key_2) not in self.rhs.edges() and\
                       (rhs_key_2, rhs_key_1) not in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the right "
                            "hand side of the rule " % (rhs_key_1, rhs_key_2)
                        )
                    primitives.remove_edge(self.p, k1, k2)
        return

    def clone_rhs_node(self, node, new_name=None):
        """Clone an rhs node."""
        if node not in self.rhs.nodes():
            raise RuleError(
                "Node '%s' is not a node of right hand side" %
                node
            )
        p_keys = keys_by_value(self.p_rhs, node)
        if len(p_keys) == 0:
            primitives.clone_node(self.rhs, node, new_name)
        elif len(p_keys) == 1:
            primitives.clone_node(self.rhs, node, new_name)
            new_p_node = primitives.clone_node(self.p, p_keys[0])
            self.p_rhs[new_p_node] = new_name
            self.p_lhs[new_p_node] = self.p_lhs[p_keys[0]]
        else:
            raise RuleError("Cannot clone node that is result of merge!")

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

    def merge_nodes_rhs(self, n1, n2, new_name):
        """Merge3 nodes in rhs."""
        if n1 not in self.rhs.nodes():
            raise RuleError("Node '%s' is not a node of the rhs" % n1)
        if n2 not in self.rhs.nodes():
            raise RuleError("Node '%s' is not a node of the rhs" % n2)
        primitives.merge_nodes(self.rhs, [n1, n2], node_id=new_name)
        for (source, target) in self.p_rhs.items():
            if target == n1 or target == n2:
                self.p_rhs[source] = new_name

    def merge_nodes(self, n1, n2, node_id=None):
        """Merge two nodes of the graph."""
        # Update graphs
        new_name = None
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        nodes_to_merge = set()
        for k1 in p_keys_1:
            if k1 not in self.p.nodes():
                raise RuleError(
                    "Node with the id '%s' does not exist in the "
                    "preserved part of the rule" % k1
                )
            for k2 in p_keys_2:
                if k2 not in self.p.nodes():
                    raise RuleError(
                        "Node with the id '%s' does not exist in "
                        "the preserved part of the rule" % k2
                    )
                nodes_to_merge.add(self.p_rhs[k1])
                nodes_to_merge.add(self.p_rhs[k2])
        new_name = primitives.merge_nodes(
            self.rhs,
            list(nodes_to_merge),
            node_id=node_id
        )
        # Update mappings
        keys = p_keys_1 + p_keys_2
        for k in keys:
            self.p_rhs[k] = new_name
        return new_name

    def add_node_attrs_rhs(self, n, attrs):
        """Add attrs to a node in the rhs."""
        if n not in self.rhs.nodes():
            raise RuleError(
                "Node %s does not exist in the right "
                "hand side of the rule" % n)
        primitives.add_node_attrs(self.rhs, n, attrs)

    def add_node_attrs(self, n, attrs):
        """Add node attributes to a node in the graph."""
        if n not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left "
                "hand side of the rule" % n)
        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise RuleError(
                "Node '%s' is being removed by the rule, "
                "cannot add attributes" % n)
        for k in p_keys:
            primitives.add_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def remove_node_attrs_rhs(self, n, attrs):
        """Remove attrs of a node in the rhs."""
        if n not in self.rhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the right hand "
                "side of the rule" % n)

        p_keys = keys_by_value(self.p_rhs, n)
        for p_node in p_keys:
            primitives.remove_node_attrs(self.p, p_node, attrs)
        primitives.remove_node_attrs(self.rhs, n, attrs)

    def remove_node_attrs_p(self, n, attrs):
        """Remove attrs of a node in the p."""
        if n not in self.p.nodes():
            raise RuleError(
                "Node '%s' does not exist in the preserved "
                "part of the rule" % n)
        primitives.remove_node_attrs(self.p, n, attrs)

    def remove_node_attrs(self, n, attrs):
        """Remove nodes attributes from a node in the graph."""
        if n not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left "
                "hand side of the rule" % n)

        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise RuleError(
                "Node '%s' is being removed by the rule, "
                "cannot remove attributes" % n)

        for k in p_keys:
            primitives.remove_node_attrs(self.p, k, attrs)
            primitives.remove_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def update_node_attrs(self, n, attrs):
        """Update attributes of a node."""
        if n not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand "
                "side of the rule" % n)

        p_keys = keys_by_value(self.p_lhs, n)
        if len(p_keys) == 0:
            raise RuleError(
                "Node '%s' is being removed by the rule, "
                "cannot update attributes" % n)
        for k in p_keys:
            self.p.node[k] = None
            primitives.update_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def add_edge_attrs(self, n1, n2, attrs):
        """Add attributes to an edge."""
        if n1 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand "
                "side of the rule" % n1
            )

        if n2 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand "
                "side of the rule" % n2
            )
        normalize_attrs(attrs)
        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left "
                    "hand side of the rule" %
                    (n1, n2)
                )
            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
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
            if (n1, n2) not in self.lhs.edges() and\
               (n2, n1) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left "
                    "hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
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
            raise RuleError(
                "Node '%s' does not exist in the left "
                "hand side of the rule" % n1
            )
        if n2 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left "
                "hand side of the rule" % n2
            )
        normalize_attrs(attrs)
        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left "
                    "hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
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
            if (n1, n2) not in self.lhs.edges() and\
               (n2, n1) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand "
                    "side of the rule" % (n1, n2)
                )
            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
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
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" %
                n1
            )
        if n2 not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the left hand side of the rule" %
                n2
            )
        normalize_attrs(attrs)
        if self.lhs.is_directed():
            if (n1, n2) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the left hand "
                    "side of the rule" % (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)

            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
                    n2
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
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
            if (n1, n2) not in self.lhs.edges() and\
               (n2, n1) not in self.lhs.edges():
                raise RuleError(
                    "Edge '%s->%s' does not exist in the "
                    "left hand side of the rule" %
                    (n1, n2)
                )

            p_keys_1 = keys_by_value(self.p_lhs, n1)
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
                    n1
                )
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot update "
                    "attributes from the incident edge" %
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

    def merge_node_list(self, node_list, node_name=None):
        """Merge a list of nodes."""
        if len(node_list) > 1:
            node_name = self.merge_nodes(
                node_list[0],
                node_list[1],
                node_name)
            for i in range(2, len(node_list)):
                node_name = self.merge_nodes(
                    node_list[i], node_name, node_name)
        else:
            warnings.warn(
                "Cannot merge less than two nodes!", ReGraphWarning
            )

    def to_json(self):
        """Convert the rule to JSON repr."""
        json_data = {}
        json_data["lhs"] = primitives.graph_to_json(self.lhs)
        json_data["p"] = primitives.graph_to_json(self.p)
        json_data["rhs"] = primitives.graph_to_json(self.rhs)
        json_data["p_lhs"] = self.p_lhs
        json_data["p_rhs"] = self.p_rhs
        return json_data

    @classmethod
    def from_json(cls, json_data):
        """Create a rule obj from JSON repr."""
        lhs = primitives.graph_from_json(json_data["lhs"])
        p = primitives.graph_from_json(json_data["p"])
        rhs = primitives.graph_from_json(json_data["rhs"])
        p_lhs = json_data["p_lhs"]
        p_rhs = json_data["p_rhs"]
        rule = cls(p, lhs, rhs, p_lhs, p_rhs)
        return rule

    def apply_to(self, graph, instance, inplace=False):
        """Perform graph rewriting with the rule.

        Parameters
        ----------
        graph : nx.(Di)Graph
            Graph to rewrite with the rule.
        instance : dict
            Instance of the `lhs` pattern in the graph
            defined by a dictionary where keys are nodes
            of `lhs` and values are nodes of the graph.
        inplace : bool, optional
            If `True`, the rewriting will be performed
            in-place by applying primitve transformations
            to the graph object, otherwise the result of
            the rewriting is a new graph object.
            Default value is `False`.

        Returns
        -------
        g_prime : nx.(Di)Graph
            Result of the rewriting. If parameter
            `inplace` was `True`, `g_prime` is exactly
            the (transformed) input graph object `graph`.
        rhs_g_prime : dict
            Matching of the `rhs` in `g_prime`, a dictionary,
            where keys are nodes of `rhs` and values are
            nodes of `g_prime`.

        """
        g_m, p_g_m, g_m_g = pullback_complement(
            self.p, self.lhs, graph, self.p_lhs, instance,
            inplace
        )
        g_prime, g_m_g_prime, rhs_g_prime = pushout(
            self.p, g_m, self.rhs, p_g_m, self.p_rhs, inplace)
        return (g_prime, rhs_g_prime)

    def added_nodes(self):
        """A set of nodes from rhs which are added by a rule."""
        nodes = set()
        for r_node in self.rhs.nodes():
            p_nodes = keys_by_value(self.p_rhs, r_node)
            if len(p_nodes) == 0:
                nodes.add(r_node)
        return nodes

    def added_edges(self):
        """."""
        edges = set()
        for s, t in self.rhs.edges():
            s_p_nodes = keys_by_value(self.p_rhs, s)
            t_p_nodes = keys_by_value(self.p_rhs, t)
            if len(s_p_nodes) == 0 or len(t_p_nodes) == 0:
                edges.add((s, t))
            else:
                found_edge = False
                for s_p_node in s_p_nodes:
                    for t_p_node in t_p_nodes:
                        if (s_p_node, t_p_node) in self.p.edges():
                            found_edge = True
                if not found_edge:
                    edges.add((s, t))
        return edges

    def added_node_attrs(self):
        """."""
        attrs = dict()
        for node in self.rhs.nodes():
            p_nodes = keys_by_value(self.p_rhs, node)
            # if len(p_nodes) == 0:
            #     attrs[node] = self.rhs.node[node]
            new_attrs = {}
            for p_node in p_nodes:
                new_attrs = attrs_union(new_attrs, dict_sub(
                    self.rhs.node[node], self.p.node[p_node]))
            if len(new_attrs) > 0:
                attrs[node] = new_attrs
        return attrs

    def added_edge_attrs(self):
        """."""
        attrs = dict()
        for s, t in self.rhs.edges():
            s_p_nodes = keys_by_value(self.p_rhs, s)
            t_p_nodes = keys_by_value(self.p_rhs, t)
            new_attrs = {}
            for s_p_node in s_p_nodes:
                for t_p_node in t_p_nodes:
                    if (s_p_node, t_p_node) in self.p.edges():
                        new_attrs = attrs_union(
                            new_attrs,
                            dict_sub(
                                self.rhs.edge[s][t],
                                self.p.edge[s_p_node][t_p_node]
                            )
                        )
        return attrs

    def merged_nodes(self):
        """."""
        nodes = dict()
        for node in self.rhs.nodes():
            p_nodes = keys_by_value(self.p_rhs, node)
            if len(p_nodes) > 1:
                nodes[node] = set(p_nodes)
        return nodes

    def removed_nodes(self):
        """."""
        nodes = set()
        for node in self.lhs.nodes():
            p_nodes = keys_by_value(self.p_lhs, node)
            if len(p_nodes) == 0:
                nodes.add(node)
        return nodes

    def removed_edges(self):
        """."""
        edges = set()
        for s, t in self.lhs.edges():
            s_p_nodes = keys_by_value(self.p_lhs, s)
            t_p_nodes = keys_by_value(self.p_lhs, t)
            if len(s_p_nodes) != 0 and len(t_p_nodes) != 0:
                for s_p_node in s_p_nodes:
                    for t_p_node in t_p_nodes:
                        if (s_p_node, t_p_node) not in self.p.edges():
                            edges.add((s_p_node, t_p_node))
        return edges

    def removed_node_attrs(self):
        """."""
        attrs = dict()
        for node in self.lhs.nodes():
            p_nodes = keys_by_value(self.p_lhs, node)
            new_attrs = {}
            for p_node in p_nodes:
                new_attrs = attrs_union(new_attrs, dict_sub(
                    self.lhs.node[node], self.p.node[p_node]))
            if len(new_attrs) > 0:
                attrs[node] = new_attrs
        return attrs

    def removed_edge_attrs(self):
        """."""
        attrs = dict()
        for s, t in self.lhs.edges():
            s_p_nodes = keys_by_value(self.p_lhs, s)
            t_p_nodes = keys_by_value(self.p_lhs, t)
            new_attrs = {}
            for s_p_node in s_p_nodes:
                for t_p_node in t_p_nodes:
                    if (s_p_node, t_p_node) in self.p.edges():
                        new_attrs = attrs_union(
                            new_attrs,
                            dict_sub(
                                self.lhs.edge[s][t],
                                self.p.edge[s_p_node][t_p_node]
                            )
                        )
            if len(new_attrs) > 0:
                attrs[(s, t)] = new_attrs
        return attrs

    def cloned_nodes(self):
        """."""
        nodes = dict()
        for node in self.lhs.nodes():
            p_nodes = keys_by_value(self.p_lhs, node)
            if len(p_nodes) > 1:
                nodes[node] = set(p_nodes)
        return nodes

    def is_restrictive(self):
        """Return True if the rule is restrictive.

        Rule is restictive if it removes
        nodes/edges/attributes or clones nodes.
        """
        return len(self.removed_nodes()) > 0 or\
            len(self.cloned_nodes()) > 0 or\
            len(self.removed_node_attrs()) > 0 or\
            len(self.removed_edges()) > 0 or\
            len(self.removed_edge_attrs()) > 0

    def is_relaxing(self):
        """Return True if the rule is relaxing.

        Rule is relaxing if it adds
        nodes/edges/attributes or merges nodes.
        """
        return len(self.added_nodes()) > 0 or\
            len(self.merged_nodes()) > 0 or\
            len(self.added_node_attrs()) > 0 or\
            len(self.added_edges()) > 0 or\
            len(self.added_edge_attrs()) > 0

    def to_commands(self):
        """Convert the rule to a list of commands."""
        commands = ""
        for node in self.removed_nodes():
            commands += "DELETE_NODE %s.\n" % node
        for u, v in self.removed_edges():
            commands += "DELETE_EDGE %s %s.\n" % (u, v)
        for lhs_node, p_nodes in self.cloned_nodes().items():
            new_name = set()
            for p_node in p_nodes:
                if p_node != lhs_node:
                    new_name.add(p_node)
            commands += "CLONE %s AS %s.\n" % (lhs_node, new_name.pop())
        for node, attrs in self.removed_node_attrs().items():
            commands += "DELETE_NODE_ATTRS %s %s.\n" % (node, attrs)
        for (u, v), attrs in self.removed_edge_attrs().items():
            commands += "DELETE_EDGE_ATTRS %s %s %s.\n" % (u, v, attrs)

        for node in self.added_nodes():
            commands += "ADD_NODE %s %s.\n" % (node, self.rhs.node[node])
        for (u, v) in self.added_edges():
            commands += "ADD_EDGE %s %s %s.\n" % (u, v, self.rhs.edge[u][v])
        for node, p_nodes in self.merged_nodes().items():
            commands += "MERGE [%s] AS '%s'.\n" %\
                (", ".join([str(n) for n in p_nodes]), str(node))
        for node, attrs in self.added_node_attrs().items():
            commands += "ADD_NODE_ATTRS %s %s.\n" % (node, attrs)
        for (u, v), attrs in self.added_edge_attrs().items():
            commands += "ADD_EDGE_ATTRS %s %s %s.\n" % (u, v, attrs)
        return commands
