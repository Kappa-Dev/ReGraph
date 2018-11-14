"""Graph rewriting rules.

This package contains the `Rule` data structure for representation
of graph rewriting rules (for more on sesqui-pushout rewriting see:
https://link.springer.com/chapter/10.1007/11841883_4).
"""
import copy
import warnings

import networkx as nx

from regraph.command_parser import parser
from regraph.utils import (keys_by_value,
                           make_canonical_commands,
                           dict_sub,
                           attrs_union,
                           remove_forbidden,
                           normalize_attrs)
from regraph.networkx.category_utils import (identity,
                                             check_homomorphism,
                                             pullback_complement,
                                             pushout)
from regraph import primitives
from regraph.networkx.plotting import plot_rule
from regraph.exceptions import (ReGraphWarning, ParsingError,
                                RuleError)
import regraph.neo4j.cypher_utils as cypher


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
        lhs = nx.DiGraph()
        for n in pattern.nodes():
            attrs = primitives.get_node(pattern, n)
            primitives.add_node(lhs, n, attrs)

        for u, v in pattern.edges():
            attrs = primitives.get_edge(pattern, u, v)
            primitives.add_edge(lhs, u, v, attrs)

        p = copy.deepcopy(lhs)
        rhs = copy.deepcopy(lhs)

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
                    rule.inject_clone_node(action["node"], node_name)
                elif action["keyword"] == "merge":
                    node_name = None
                    if "node_name" in action.keys():
                        node_name = action["node_name"]
                    rule.inject_merge_nodes(
                        action["nodes"],
                        node_name)
                elif action["keyword"] == "add_node":
                    name = None
                    attrs = {}
                    if "node" in action.keys():
                        name = action["node"]
                    if "attributes" in action.keys():
                        attrs = action["attributes"]
                    rule.inject_add_node(name, attrs)
                elif action["keyword"] == "delete_node":
                    rule.inject_remove_node(action["node"])
                elif action["keyword"] == "add_edge":
                    attrs = {}
                    if "attributes" in action.keys():
                        attrs = action["attributes"]
                    rule.inject_add_edge(
                        action["node_1"],
                        action["node_2"],
                        attrs)
                elif action["keyword"] == "delete_edge":
                    rule.inject_remove_edge(
                        action["node_1"],
                        action["node_2"])
                elif action["keyword"] == "add_node_attrs":
                    rule.inject_add_node_attrs(
                        action["node"],
                        action["attributes"])
                elif action["keyword"] == "add_edge_attrs":
                    rule.inject_add_edge_attrs(
                        action["node_1"],
                        action["node_2"],
                        action["attributes"])
                elif action["keyword"] == "delete_node_attrs":
                    rule.inject_remove_node_attrs(
                        action["node"],
                        action["attributes"])
                elif action["keyword"] == "delete_edge_attrs":
                    rule.inject_remove_edge_attrs(
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

    def inject_clone_node(self, n, new_node_id=None):
        """Inject cloning of a node by the rule.

        This procedure clones `n` in the preserved part
        and the right-hand side.

        Parameters
        ----------
        n : hashable
            Node from `lhs` to clone
        new_node_id : hashable
            Id for the clone

        Returns
        -------
        p_new_node_id : hashable
            Id of the new clone node in the preserved part
        rhs_new_node_id : hashable
            Id of the new clone node in the right-hand side


        Raises
        ------
        RuleError
            If the node to clone is already being removed by the rule
            or if node with the specified clone id already exists in p.
        """
        p_nodes = keys_by_value(self.p_lhs, n)
        if len(p_nodes) == 0:
            raise RuleError(
                "Cannot inject cloning: node '%s' is already "
                "being removed by the rule, revert its removal "
                "first" % n)
        else:
            if new_node_id is not None and new_node_id in self.p.nodes():
                raise RuleError(
                    "Node with id '%s' already exists in the "
                    "preserved part!")
            some_p_node = p_nodes[0]
            p_new_node_id = primitives.clone_node(
                self.p, some_p_node, new_node_id)
            self.p_lhs[p_new_node_id] = n
            # add it to the rhs
            # generate a new id for rhs
            rhs_new_node_id = p_new_node_id
            if rhs_new_node_id in self.rhs.nodes():
                rhs_new_node_id = primitives.unique_node_id(
                    self.rhs, rhs_new_node_id)
            primitives.add_node(
                self.rhs, rhs_new_node_id, self.p.node[p_new_node_id])
            self.p_rhs[p_new_node_id] = rhs_new_node_id
            # reconnect the new rhs node with necessary edges
            for pred in self.p.predecessors(p_new_node_id):
                if (self.p_rhs[pred], rhs_new_node_id) not in self.rhs.edges():
                    primitives.add_edge(
                        self.rhs,
                        self.p_rhs[pred], rhs_new_node_id,
                        self.p.edges[pred, p_new_node_id])
            for suc in self.p.successors(p_new_node_id):
                if (rhs_new_node_id, self.p_rhs[suc]) not in self.rhs.edges():
                    primitives.add_edge(
                        self.rhs,
                        rhs_new_node_id, self.p_rhs[suc],
                        self.p.edges[p_new_node_id, suc])

        return (p_new_node_id, rhs_new_node_id)

    def inject_remove_node(self, lhs_node_id):
        """Inject a new node removal to the rule.

        This method removes from `p` all the nodes that map
        to the node with the id `lhs_node_id`. In addition,
        all the nodes from `rhs` that are mapped by the nodes
        removed in `p` are also removed.

        Parameters
        ----------
        lhs_node_id
            Id of the node in `lhs` that should be removed
            by the rule.
        """
        # remove corresponding nodes from p and rhs
        p_keys = keys_by_value(self.p_lhs, lhs_node_id)
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

    def inject_remove_edge(self, n1, n2):
        """Inject removal of an edge by the rule.

        Parameters
        ----------
        n1 : hashable
            Id of an edge's source node in `lhs`.
        n2 : hashable
            Id of an edge's target node in `lhs`.

        Raises
        ------
        RuleError
            If some of the nodes are not found in neither
            `lhs` nor `p`, or if a corresponding edge in
            `p` does not exist.
        """
        # Find nodes in p mapping to n1 & n2
        p_keys_1 = keys_by_value(self.p_lhs, n1)
        p_keys_2 = keys_by_value(self.p_lhs, n2)

        # n1 is actually a node from `p`
        if len(p_keys_1) == 0:
            if n1 in self.p.nodes():
                p_keys_1 = [n1]
            else:
                raise RuleError(
                    "Node '{}' is not found in neither left-hand "
                    "side nor preserved part".format(n1))

        if len(p_keys_2) == 0:
            if n2 in self.p.nodes():
                p_keys_2 = [n2]
            else:
                raise RuleError(
                    "Node '{}' is not found in neither left-hand "
                    "side nor preserved part".format(n2))

        for k1 in p_keys_1:
            for k2 in p_keys_2:
                if (k1, k2) in self.p.edges():
                    primitives.remove_edge(self.p, k1, k2)
                    primitives.remove_edge(self.rhs, self.p_rhs[k1], self.p_rhs[k2])
                else:
                    raise RuleError(
                        "Edge '{}->{}' does not exist in the preserved part".format(k1, k2))

        return

    def inject_remove_node_attrs(self, n, attrs):
        """Inject a removal of node attrs by the rule.

        First, tries to find a node with the id `n` in the
        left-hand side, injects its attrs removal if found,
        otherwise, tries to find the corresponding node in
        the preserved part (it helps us to implement injection
        of the node attrs removal to only one of the clone nodes).


        Parameters
        ----------
        n : hashable
            Id of a node whose attrs to remove (node from the
            left-hand side or the preserved part).
        attrs : dict
            Dictionary with attributes to remove.

        Raises
        ------
        RuleError
            If `n` does not exist in neither the left-hand side
            nor the preserved part of the rule, or when the node
            whose attrs should be removed is itself is being removed
            by the rule.

        """
        if n not in self.lhs.nodes() and n not in self.p.nodes():
            raise RuleError(
                "Node '%s' exists in neither the left "
                "hand side of the rule nor the preserved part" % n)

        if n in self.lhs.nodes():
            p_keys = keys_by_value(self.p_lhs, n)
            if len(p_keys) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, "
                    "cannot remove attributes" % n)
        else:
            p_keys = [n]

        for k in p_keys:
            primitives.remove_node_attrs(self.p, k, attrs)
            primitives.remove_node_attrs(self.rhs, self.p_rhs[k], attrs)
        return

    def inject_remove_edge_attrs(self, n1, n2, attrs):
        """Inject a removal of edge attrs by the rule.

        For both `n1` and `n2`, first, tries to find
        a node with this id in the left-hand side,
        injects the removal of the respective edge attrs if found,
        otherwise, tries to find the corresponding node in
        the preserved part (it helps us to implement injection
        of the edge attrs removal to only one of the edges
        incident to the clone).

        Parameters
        ----------
        n1 : hashable
            Id of an edge's source node in `lhs` or `p`.
        n2 : hashable
            Id of an edge's target node in `lhs` or `p`.
        attrs : dict
            Dictionary with attributes to remove.

        Raises
        ------
        RuleError

        """
        if n1 not in self.lhs.nodes() and n1 not in self.p.nodes():
            raise RuleError(
                "Node '%s' exists in neither the left "
                "hand side of the rule nor the preserved part" % n1
            )
        if n2 not in self.lhs.nodes() and n2 not in self.p.nodes():
            raise RuleError(
                "Node '%s' exists in neither the left "
                "hand side of the rule nor the preserved part" % n2
            )

        if n1 in self.lhs.nodes():
            p_keys_1 = keys_by_value(self.p_lhs, n1)
            if len(p_keys_1) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n1
                )
        else:
            p_keys_1 = [n1]
        if n2 in self.lhs.nodes():
            p_keys_2 = keys_by_value(self.p_lhs, n2)
            if len(p_keys_2) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot remove "
                    "attributes from the incident edge" %
                    n2
                )
        else:
            p_keys_2 = [n2]

        for k1 in p_keys_1:
            for k2 in p_keys_2:
                if self.p.is_directed():
                    if (k1, k2) not in self.p.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the preserved "
                            "part of the rule" %
                            (k1, k2)
                        )
                else:
                    if (k1, k2) not in self.p.edges() and\
                       (k2, k1) not in self.p.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the preserved "
                            "part of the rule" % (k1, k2)
                        )
                primitives.remove_edge_attrs(self.p, k1, k2, attrs)
                primitives.remove_edge_attrs(
                    self.rhs, self.p_rhs[k1], self.p_rhs[k2], attrs)
        return

    def inject_add_node(self, node_id, attrs=None):
        """Inject an addition of a new node by the rule.

        This method adds a node with `node_id` (and the specified
        attributes `attrs`) to `rhs`.

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
            primitives.add_node(self.rhs, node_id, attrs)
        else:
            raise RuleError(
                "Node with the id '%s' already exists in the "
                "right hand side of the rule" %
                node_id
            )

    def inject_add_nodes_from(self, node_list):
        """Inject an addition of a new node by the rule.

        This method adds a nodes from the list (and the specified
        attributes `attrs`) to `rhs`.

        Parameters
        ----------
        node_list : iterable
            Collection of nodes to add, where every element is
            either a tuple of the form (<node_id>, <node_attrs>)
            or a single value <node_id>

        Raises
        ------
        RuleError
            If some node from the list already exists in the `rhs`.
        """
        for n in node_list:
            try:
                node_id, node_attrs = n
                self.inject_add_node(node_id, node_attrs)
            except (TypeError, ValueError):
                self.inject_add_node(node_id)
        return

    def inject_add_edge(self, n1, n2, attrs=None):
        """Inject addition of a new edge to the rule.

        This method adds an edge between two nodes of the
        `rhs`.

        Parameters
        ----------
        n1 : hashable
            Id of an edge's source node in `rhs`.
        n2 : hashable
            Id of an edge's target node in `rhs`.

        Raises
        ------
        RuleError
            If some of the nodes (`n1` or `n2`) do not exist
            or if there is already an edge between them in `rhs`.
        """
        if n1 not in self.rhs.nodes():
            raise RuleError(
                "Node with the id '%s' does not exist in the "
                "right-hand side of the rule" % n1)
        if n2 not in self.rhs.nodes():
            raise RuleError(
                "Node with the id '%s' does not exist in the "
                "right-hand side of the rule" % n2)
        if (n1, n2) in self.rhs.edges():
            raise RuleError(
                "Edge '%s->%s' already exists in the right-"
                "hand side of the rule" %
                (n1, n2)
            )
        primitives.add_edge(self.rhs, n1, n2, attrs)
        return

    def inject_add_edges_from(self, edge_list):
        """Inject addition of a new edge to the rule.

        This method injects addition of edges from the list.

        Parameters
        ----------
        edge_list : iterable
            Collection of edges to add, where every element is
            either a tuple of the form (<source_id>, <target_id>)
            or (<source_id>, <target_id>, <edge_attrs>). Here
            source and target nodes are assumed to be from the `rhs`.

        Raises
        ------
        RuleError
            If some of the nodes (`n1` or `n2`) do not exist
            or if there is already an edge between them in `rhs`.
        """
        for e in edge_list:
            if len(e) == 2:
                self.inject_add_edge(e[0], e[1])
            elif len(e) == 3:
                self.inject_add_edge(e[0], e[1], e[2])
            else:
                raise RuleError(
                    "Was expecting 2 or 3 elements per tuple, got %s." %
                    str(len(e))
                )

    def inject_merge_nodes(self, node_list, node_id=None):
        """Inject merge of a collection of nodes by the rule.

        Parameters
        ----------
        node_list : iterable
            Collection of ids of nodes from the preserved part or
            the rhs to merge.
        node_id : hashable
            Id of the new node corresponding to the result of merge.

        Returns
        -------
        new_name : hashable
            Id of the new node corresponding to the result of merge.

        Raises
        ------
        RuleError
            If a node with some id specified in `node_lust` does not
            exist in the preserved part of the rule.
        """
        # Update graphs
        new_name = None

        nodes_to_merge = set()
        for n in node_list:
            if n in self.p.nodes():
                rhs_node = self.p_rhs[n]
            elif n in self.rhs.nodes():
                rhs_node = n
            else:
                raise RuleError(
                    "Node with the id '%s' does not exist in neither the "
                    "preserved part of the rule nor its rhs" % n
                )
            nodes_to_merge.add(rhs_node)
        new_name = primitives.merge_nodes(
            self.rhs,
            list(nodes_to_merge),
            node_id=node_id
        )
        # Update mappings
        for n in node_list:
            if n in self.p.nodes():
                self.p_rhs[n] = new_name
        for r_node in nodes_to_merge:
            merged_ps = keys_by_value(self.p_rhs, r_node)
            for p in merged_ps:
                self.p_rhs[p] = new_name
        return new_name

    def inject_add_node_attrs(self, n, attrs):
        """Inject addition of  node attributes by the rule.

        First, tries to find a node with the id `n` in the
        left-hand side, injects its attrs add to all the `rhs` nodes
        related to it through l<-p->r, if found,
        otherwise, tries to find the corresponding node in
        the preserved part and adds attrs to the node to which `n`
        maps in p->r, if it is not found in `p`, tries to find it in
        the `rhs` (it helps us to implement injection
        of the node attrs add to only one of the clone nodes, or to new nodes,
        or to merged nodes).

        Parameters
        ----------
        n1 : hashable
            Id of an edge's source node in `lhs`, `p` or `rhs`.
        n2 : hashable
            Id of an edge's target node in `lhs`, `p` or `rhs`.
        attrs : dict
            Dictionary with attrs to add

        Raises
        ------
        RuleError
            If node `n` does not exist in the rhs of the rule

        """
        if n not in list(self.lhs.nodes()) + list(self.p.nodes()) + list(self.rhs.nodes()):
            raise RuleError(
                "Node '%s' exists in neither lhs, nor p, nor rhs of the rule" %
                n)
        r_nodes = set()
        if n in self.lhs.nodes():
            p_keys = keys_by_value(self.p_lhs, n)
            for p in p_keys:
                r_nodes.add(self.p_rhs[p])
        elif n in self.p.nodes():
            r_nodes.add(self.p_rhs[n])
        elif n in self.rhs.nodes():
            r_nodes.add(n)
        for r in r_nodes:
            primitives.add_node_attrs(self.rhs, r, attrs)
        return

    def inject_add_edge_attrs(self, n1, n2, attrs):
        """Inject addition of edge attributes by the rule.

        For `n1` and `n2`, first, tries to find a node with this id in the
        left-hand side, finds a node from `rhs` related to it through
        l<-p->r, if found, otherwise, tries to find the corresponding node in
        the preserved part and finds the node to which `n` maps in p->r,
        if it is not found in `p`, tries to find it in
        the `rhs` (it helps us to implement injection
        of the edge attrs add to only one of the edges incident to clones,
        or to new edges, or to edges produced by merges).

        Parameters
        ----------
        n1 : hashable
        n2 : hashable
        attrs : dict
            Dictionary with attrs to add

        Raises
        ------
        RuleError
            If some of the nodes defining an edge are not found in neither
            `lhs`, nor `p` nor `rhs`, or if an edge is incident to smth thats
            is going to be removed by the rule.
        """
        if n1 not in list(self.lhs.nodes()) + list(self.rhs.nodes()) + list(self.p.nodes()):
            raise RuleError(
                "Node '%s' exists in neither lhs, nor p, nor rhs "
                "of the rule" % n1
            )

        if n2 not in list(self.lhs.nodes()) + list(self.rhs.nodes()) + list(self.p.nodes()):
            raise RuleError(
                "Node '%s' exists in neither lhs, nor p, nor rhs "
                "of the rule" % n2
            )

        if n1 in self.lhs.nodes():
            p_keys = keys_by_value(self.p_lhs, n1)
            if len(p_keys) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n1
                )
            rhs_keys_1 = [self.p_rhs[p] for p in p_keys]
        elif n1 in self.p.nodes():
            rhs_keys_1 = [self.p_rhs[n1]]
        elif n1 in self.rhs.nodes():
            rhs_keys_1 = [n1]

        if n2 in self.lhs.nodes():
            p_keys = keys_by_value(self.p_lhs, n2)
            if len(p_keys) == 0:
                raise RuleError(
                    "Node '%s' is being removed by the rule, cannot add "
                    "attributes to the incident edge" %
                    n2
                )
            rhs_keys_2 = [self.p_rhs[p] for p in p_keys]
        elif n2 in self.p.nodes():
            rhs_keys_2 = [self.p_rhs[n2]]
        elif n2 in self.rhs.nodes():
            rhs_keys_2 = [n2]

        for r1 in rhs_keys_1:
            for r2 in rhs_keys_2:
                if self.rhs.is_directed() and (r1, r2) not in self.rhs.edges():
                        raise RuleError(
                            "Edge '%s->%s' does not exist in the right "
                            "hand side of the rule" %
                            (r1, r2))
                elif (r1, r2) not in self.rhs.edges() and\
                     (r2, r1) not in self.rhs.edges():
                    raise RuleError(
                        "Edge '%s->%s' does not exist in the right "
                        "hand side of the rule" %
                        (r1, r2)
                    )
                primitives.add_edge_attrs(
                    self.rhs, r1, r2, attrs)
        return

    def inject_update_node_attrs(self, n, attrs):
        """Inject an update of node attrs by the rule.

        Parameters
        ----------
        n : hashable
            Id of a node from the left-hand side whose attrs
            should be updated
        attrs : dict
            Dictionary of new attrs that will replace the old ones

        Raises
        ------
        RuleError
            If node `n` does not exist in the left-hand side or
            is being removed by the rule.
        """
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

    def inject_update_edge_attrs(self, n1, n2, attrs):
        """Inject an update of edge attrs by the rule."""
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
                    self.p.edges[k1, k2] = None
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
                    self.p.edges[k1, k2] = None
                    primitives.update_edge_attrs(
                        self.rhs,
                        self.p_rhs[k1],
                        self.p_rhs[k2],
                        attrs
                    )
        return

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
    def from_json(cls, json_data, directed=True):
        """Create a rule obj from JSON repr."""
        lhs = primitives.graph_from_json(json_data["lhs"], directed)
        p = primitives.graph_from_json(json_data["p"], directed)
        rhs = primitives.graph_from_json(json_data["rhs"], directed)
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
        """Get nodes added by the rule.

        Returns
        -------
        nodes : set
            Set of nodes from `rhs` added by the rule.
        """
        nodes = set()
        for r_node in self.rhs.nodes():
            p_nodes = keys_by_value(self.p_rhs, r_node)
            if len(p_nodes) == 0:
                nodes.add(r_node)
        return nodes

    def added_edges(self):
        """Get edges added by the rule.

        Returns
        -------
        edges : set
            Set of edges from `rhs` added by the rule.
        """
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
        """Get node attributes added by the rule.

        Returns
        -------
        attrs : dict
            Dictionary where keys are nodes from `rhs`
            and values are attribute dictionaries to add.
        """
        attrs = dict()
        for node in self.rhs.nodes():
            p_nodes = keys_by_value(self.p_rhs, node)
            if len(p_nodes) == 0:
                if len(self.rhs.node[node]) > 0:
                    attrs[node] = self.rhs.node[node]
            new_attrs = {}
            for p_node in p_nodes:
                new_attrs = attrs_union(new_attrs, dict_sub(
                    self.rhs.node[node], self.p.node[p_node]))
            if len(new_attrs) > 0:
                attrs[node] = new_attrs
        return attrs

    def added_edge_attrs(self):
        """Get edge attributes added by the rule.

        Returns
        -------
        attrs : dict
            Dictionary where keys are edges from `rhs`
            and values are attribute dictionaries to add.
        """
        attrs = dict()
        for s, t in self.rhs.edges():
            s_p_nodes = keys_by_value(self.p_rhs, s)
            t_p_nodes = keys_by_value(self.p_rhs, t)
            if len(s_p_nodes) == 0 or len(t_p_nodes) == 0:
                if len(self.rhs.edges[s, t]) > 0:
                    attrs[(s, t)] = self.rhs.edges[s, t]
            new_attrs = {}
            for s_p_node in s_p_nodes:
                for t_p_node in t_p_nodes:
                    if (s_p_node, t_p_node) in self.p.edges():
                        new_attrs = attrs_union(
                            new_attrs,
                            dict_sub(
                                self.rhs.edges[s, t],
                                self.p.edges[s_p_node, t_p_node]
                            )
                        )
            if len(new_attrs) > 0:
                attrs[(s, t)] = new_attrs
        return attrs

    def merged_nodes(self):
        """Get nodes merged by the rule.

        Returns
        -------
        nodes : dict
            Dictionary where keys are nodes from `rhs` and
            values are sets of nodes from `p` that are merged.
        """
        nodes = dict()
        for node in self.rhs.nodes():
            p_nodes = keys_by_value(self.p_rhs, node)
            if len(p_nodes) > 1:
                nodes[node] = set(p_nodes)
        return nodes

    def removed_nodes(self):
        """Get nodes removed by the rule.

        Returns
        -------
        nodes : set
            Set of nodes from `lhs` removed by the rule.
        """
        nodes = set()
        for node in self.lhs.nodes():
            p_nodes = keys_by_value(self.p_lhs, node)
            if len(p_nodes) == 0:
                nodes.add(node)
        return nodes

    def removed_edges(self):
        """Get edges removed by the rule.

        Returns
        -------
        edges : set
            Set of edges from `lhs` removed by the rule.
        """
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
        """Get node attributes removed by the rule.

        Returns
        -------
        attrs : dict
            Dictionary where keys are nodes from `lhs`
            and values are attribute dictionaries to remove.
        """
        attrs = dict()
        for node in self.lhs.nodes():
            p_nodes = keys_by_value(self.p_lhs, node)
            for p_node in p_nodes:
                new_attrs = dict_sub(
                    self.lhs.node[node], self.p.node[p_node])
                if len(new_attrs) > 0:
                    normalize_attrs(new_attrs)
                    attrs[p_node] = new_attrs
        return attrs

    def removed_edge_attrs(self):
        """Get edge attributes removed by the rule.

        Returns
        -------
        attrs : dict
            Dictionary where keys are edges from `lhs`
            and values are attribute dictionaries to remove.
        """
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
                                self.lhs.edges[s, t],
                                self.p.edges[s_p_node, t_p_node]
                            )
                        )
            if len(new_attrs) > 0:
                normalize_attrs(new_attrs)
                attrs[(s, t)] = new_attrs
        return attrs

    def cloned_nodes(self):
        """Get nodes cloned by the rule.

        Returns
        -------
        nodes : dict
            Dictionary where keys are nodes from `lhs` and
            values are sets of corresponding nodes from `p`.
        """
        nodes = dict()
        for node in self.lhs.nodes():
            p_nodes = keys_by_value(self.p_lhs, node)
            if len(p_nodes) > 1:
                nodes[node] = set(p_nodes)
        return nodes

    def is_restrictive(self):
        """Check if the rule is  restrictive.

        Rule is restictive if it removes
        nodes/edges/attributes or clones nodes.

        Returns
        -------
        `True` if the rule is restrictive, `False`
        otherwise

        """
        return len(self.removed_nodes()) > 0 or\
            len(self.cloned_nodes()) > 0 or\
            len(self.removed_node_attrs()) > 0 or\
            len(self.removed_edges()) > 0 or\
            len(self.removed_edge_attrs()) > 0

    def is_relaxing(self):
        """Check if the rule is relaxing.

        Rule is relaxing if it adds
        nodes/edges/attributes or merges nodes.

        Returns
        -------
        `True` if the rule is relaxing, `False` otherwise

        """
        return len(self.added_nodes()) > 0 or\
            len(self.merged_nodes()) > 0 or\
            len(self.added_node_attrs()) > 0 or\
            len(self.added_edges()) > 0 or\
            len(self.added_edge_attrs()) > 0

    def to_commands(self):
        """Convert the rule to a list of commands.

        This method produces a list of commands
        corresponding to the rule. These commands
        follow a simple grammar of transformations
        that can be recognized by `regraph.parser` module.

        Returns
        -------
        commands : str
            Commands representing primitive transformations on the
            the `lhs` that are preformed in the rule.

        """
        commands = ""
        for lhs_node, p_nodes in self.cloned_nodes().items():
            new_names = set()
            for p_node in p_nodes:
                if p_node != lhs_node:
                    new_names.add(p_node)
            for name in new_names:
                commands += "CLONE %s AS %s.\n" % (lhs_node, name)
        for node in self.removed_nodes():
            commands += "DELETE_NODE %s.\n" % node
        for u, v in self.removed_edges():
            commands += "DELETE_EDGE %s %s.\n" % (u, v)
        for node, attrs in self.removed_node_attrs().items():
            commands += "DELETE_NODE_ATTRS %s %s.\n" % (node, attrs)
        for (u, v), attrs in self.removed_edge_attrs().items():
            commands += "DELETE_EDGE_ATTRS %s %s %s.\n" % (u, v, attrs)

        for node, p_nodes in self.merged_nodes().items():
            commands += "MERGE [%s] AS '%s'.\n" %\
                (", ".join([str(n) for n in p_nodes]), str(node))
        for node in self.added_nodes():
            commands += "ADD_NODE %s %s.\n" % (node, self.rhs.node[node])
        for (u, v) in self.added_edges():
            commands += "ADD_EDGE %s %s %s.\n" % (u, v, self.rhs.edges[u, v])
        for node, attrs in self.added_node_attrs().items():
            commands += "ADD_NODE_ATTRS %s %s.\n" % (node, attrs)
        for (u, v), attrs in self.added_edge_attrs().items():
            commands += "ADD_EDGE_ATTRS %s %s %s.\n" % (u, v, attrs)
        return commands

    def _add_node_lhs(self, node_id, attrs=None):
        if node_id not in self.lhs.nodes():
            primitives.add_node(self.lhs, node_id, attrs)
            new_p_node_id = node_id
            if new_p_node_id in self.p.nodes():
                new_p_node_id = primitives.unique_node_id(new_p_node_id)
            primitives.add_node(self.p, new_p_node_id, attrs)
            self.p_lhs[new_p_node_id] = node_id
            new_rhs_node_id = node_id
            if new_rhs_node_id in self.rhs.nodes():
                new_rhs_node_id = primitives.unique_node_id(new_rhs_node_id)
            primitives.add_node(self.rhs, new_rhs_node_id, attrs)
            self.p_rhs[new_p_node_id] = new_rhs_node_id
        else:
            raise RuleError(
                "Node '%s' already exists in the left-hand side "
                "of the rule" % node_id)

    def _add_edge_lhs(self, source, target, attrs=None):
        if (source, target) not in self.lhs.edges():
            if source in self.lhs.nodes() and target in self.rhs.nodes():
                primitives.add_edge(self.lhs, source, target, attrs)
                p_sources = keys_by_value(self.p_lhs, source)
                p_targets = keys_by_value(self.p_lhs, target)
                if len(p_sources) > 0 and len(p_targets) > 0:
                    for p_s in p_sources:
                        for p_t in p_targets:
                            primitives.add_edge(self.p, p_s, p_t, attrs)
                            primitives.add_edge(
                                self.rhs, self.p_rhs[p_s],
                                self.p_rhs[p_t], attrs)
            else:
                raise RuleError(
                    "Cannot add an edge between nodes '{}' and '{}': "
                    "one of the nodes does not exist".format(source, target))
        else:
            raise RuleError(
                "Edge '{}'->'{}' already exists in the left-hand side "
                "of the rule".format(source, target))

    def _remove_node_rhs(self, node_id):
        """Remove a node from the `rhs`.

        This method removes a given node from the `rhs`,
        if there exist nodes from `p` that map to this node
        they are removed as well.
        """
        p_keys = keys_by_value(self.p_rhs, node_id)
        for p_node in p_keys:
            primitives.remove_node(self.p, p_node)
            del self.p_rhs[p_node]
            del self.p_lhs[p_node]
        primitives.remove_node(self.rhs, node_id)

    def _add_edge_rhs(self, n1, n2, attrs=None):
        """Add an edge in the rhs."""
        primitives.add_edge(self.rhs, n1, n2, attrs)

    def _remove_edge_p(self, node1, node2):
        """Remove edge from the p of the graph."""
        primitives.remove_edge(self.p, node1, node2)

    def _remove_edge_rhs(self, node1, node2):
        """Remove edge from the rhs of the graph."""
        primitives.remove_edge(self.rhs, node1, node2)
        for pn1 in keys_by_value(self.p_rhs, node1):
            for pn2 in keys_by_value(self.p_rhs, node2):
                if (pn1, pn2) in self.p.edges():
                    primitives.remove_edge(self.p, pn1, pn2)

    def _clone_rhs_node(self, node, new_name=None):
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

    def _merge_nodes_rhs(self, n1, n2, new_name):
        """Merge nodes in rhs."""
        if n1 not in self.rhs.nodes():
            raise RuleError("Node '%s' is not a node of the rhs" % n1)
        if n2 not in self.rhs.nodes():
            raise RuleError("Node '%s' is not a node of the rhs" % n2)
        primitives.merge_nodes(self.rhs, [n1, n2], node_id=new_name)
        for (source, target) in self.p_rhs.items():
            if target == n1 or target == n2:
                self.p_rhs[source] = new_name

    def _add_node_attrs_rhs(self, n, attrs):
        """Add attrs to a node in the rhs."""
        if n not in self.rhs.nodes():
            raise RuleError(
                "Node %s does not exist in the right "
                "hand side of the rule" % n)
        primitives.add_node_attrs(self.rhs, n, attrs)

    def _remove_node_attrs_rhs(self, n, attrs):
        """Remove attrs of a node in the rhs."""
        if n not in self.rhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the right hand "
                "side of the rule" % n)

        p_keys = keys_by_value(self.p_rhs, n)
        for p_node in p_keys:
            primitives.remove_node_attrs(self.p, p_node, attrs)
        primitives.remove_node_attrs(self.rhs, n, attrs)

    def _remove_node_attrs_p(self, n, attrs):
        """Remove attrs of a node in the p."""
        if n not in self.p.nodes():
            raise RuleError(
                "Node '%s' does not exist in the preserved "
                "part of the rule" % n)
        primitives.remove_node_attrs(self.p, n, attrs)

    def _merge_node_list(self, node_list, node_name=None):
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

    def _add_node_attrs_lhs(self, n, attrs):
        if n not in self.lhs.nodes():
            raise RuleError(
                "Node '%s' does not exist in the lhs "
                "of the rule" % n)
        primitives.add_node_attrs(self.lhs, n, attrs)
        p_nodes = keys_by_value(self.p_rhs, n)
        for p_node in p_nodes:
            primitives.add_node_attrs(self.p, p_node, attrs)

    def _remove_attrs(self):
        for n in self.lhs.nodes():
            self.lhs.node[n] = dict()
        for n in self.p.nodes():
            self.p.node[n] = dict()
        for n in self.rhs.nodes():
            self.rhs.node[n] = dict()

        for u, v in self.lhs.edges():
            self.lhs.edges[u, v] = dict()
        for u, v in self.p.edges():
            self.p.edges[u, v] = dict()
        for u, v in self.rhs.edges():
            self.rhs.edges[u, v] = dict()

    def _escape(self):

        lhs_relabel = {}
        for node in self.lhs.nodes():
            new_name = remove_forbidden(node)
            lhs_relabel[node] = new_name

        p_relabel = {}
        for node in self.p.nodes():
            new_name = remove_forbidden(node)
            p_relabel[node] = new_name

        rhs_relabel = {}
        for node in self.rhs.nodes():
            new_name = remove_forbidden(node)
            rhs_relabel[node] = new_name

        nx.relabel_nodes(self.lhs, lhs_relabel, copy=False)
        nx.relabel_nodes(self.p, p_relabel, copy=False)
        nx.relabel_nodes(self.rhs, rhs_relabel, copy=False)

        new_p_lhs = dict()
        for k, v in self.p_lhs.items():
            new_key = remove_forbidden(k)
            new_v = remove_forbidden(v)
            new_p_lhs[new_key] = new_v

        new_p_rhs = dict()
        for k, v in self.p_rhs.items():
            new_key = remove_forbidden(k)
            new_v = remove_forbidden(v)
            new_p_rhs[new_key] = new_v

        self.p_lhs = new_p_lhs
        self.p_rhs = new_p_rhs

    def to_cypher(self, instance, node_label="node",
                  edge_label="edge", generate_var_ids=False):
        """Convert a rule on the instance to a Cypher query.

        instance : dict
            Dictionary specifying an instance of the lhs of the rule
        rhs_typing : dict
        node_label : iterable, optional
        edge_label : iterable, optional
        generate_var_ids : boolean
            If True the names of the variables will be generated as uuid
            (unreadable, but more secure: guaranteed to avoid any var name
            collisions)
        """
        # If names of nodes of the rule graphs (L, P, R) are used as
        # var names, we need to perform escaping on these names
        # for neo4j not to complain (some symbols are forbidden in
        # Cypher's var names)

        # fix the order of nodes from P
        # this is to avoid problems with different
        # selection of the cloning origin
        preserved_nodes = self.p.nodes()
        preserved_nodes_positions = {
            n: i + 0 for i, n in enumerate(preserved_nodes)
        }
        if generate_var_ids:
            # Generate unique variable names corresponding to node names
            lhs_vars = {
                n: cypher.generate_var_name() for n in self.lhs.nodes()}
            p_vars = {
                n: cypher.generate_var_name() for n in preserved_nodes}
            rhs_vars = {
                n: cypher.generate_var_name() for n in self.rhs.nodes()}
        else:
            # rule._escape()
            lhs_vars = {n: "lhs_" + str(n) for n in self.lhs.nodes()}
            p_vars = {n: "p_" + str(n) for n in preserved_nodes}
            rhs_vars = {n: "rhs_" + str(n) for n in self.rhs.nodes()}

        # Variables of the nodes of instance
        match_instance_vars = {lhs_vars[k]: v for k, v in instance.items()}
        query = ""

        # If instance is not empty, generate Cypher that matches the nodes
        # of the instance
        if len(instance) > 0:
            query += "// Match nodes and edges of the instance \n"
            query += cypher.match_pattern_instance(
                self.lhs, lhs_vars, match_instance_vars,
                node_label=node_label, edge_label=edge_label)
            query += "\n\n"
        else:
            query += "// Empty instance \n\n"

        # Add instance nodes to the set of vars to carry
        carry_variables = set(match_instance_vars.keys())
        for u, v in self.lhs.edges():
            carry_variables.add(str(lhs_vars[u]) + "_" + str(lhs_vars[v]))

        # Generate cloning subquery
        for lhs_node, p_nodes in self.cloned_nodes().items():
            query += "// Cloning node '{}' of the lhs \n".format(lhs_node)
            clones = set()
            preds_to_ignore = dict()
            sucs_to_ignore = dict()
            for p_node in p_nodes:
                if (lhs_node in p_nodes and p_node != lhs_node) or\
                   (lhs_node not in p_nodes and preserved_nodes_positions[
                        p_node] != 0):
                    clones.add(p_node)

            for n in clones:
                preds_to_ignore = set()
                sucs_to_ignore = set()
                for u, v in self.removed_edges():
                        if u == n and v not in p_nodes:
                            try:
                                sucs_to_ignore.add(
                                    instance[self.p_lhs[v]])
                            except(KeyError):
                                pass
                                # sucs_to_ignore.add(v)
                        if v == n and u not in p_nodes:
                            try:
                                preds_to_ignore.add(
                                    instance[self.p_lhs[u]])
                            except(KeyError):
                                pass
                                # preds_to_ignore[p_node].add(u)

                query +=\
                    "// Create clone corresponding to '{}' ".format(n) +\
                    "of the preserved part\n"
                if generate_var_ids:
                    clone_id_var = cypher.generate_var_name()
                else:
                    clone_id_var = "p_" + str(n) + "_id"

                q, carry_variables = cypher.cloning_query(
                    original_var=lhs_vars[lhs_node],
                    clone_var=p_vars[n],
                    clone_id=n,
                    clone_id_var=clone_id_var,
                    node_label=node_label,
                    edge_labels=["edge", "typing", "related"],
                    sucs_to_ignore=sucs_to_ignore,
                    preds_to_ignore=preds_to_ignore,
                    carry_vars=carry_variables,
                    ignore_naming=True)
                query += q
                query += cypher.with_vars(carry_variables)
                query += "\n\n"

        # Generate nodes removal subquery
        for node in self.removed_nodes():
            query += "// Removing node '{}' of the lhs \n".format(node)
            query += cypher.remove_nodes([lhs_vars[node]])
            carry_variables.remove(lhs_vars[node])
            query += "\n"

        # Generate edges removal subquery
        for u, v in self.removed_edges():
            if self.p_lhs[u] not in self.cloned_nodes().keys() and\
               self.p_lhs[v] not in self.cloned_nodes().keys():
                # if u in instance.keys() and v in instance.keys():
                query += "// Removing pattern matched edges '{}->{}' of the lhs \n".format(
                    self.p_lhs[u], self.p_lhs[v])
                edge_var = "{}_{}".format(
                    str(lhs_vars[self.p_lhs[u]]),
                    str(lhs_vars[self.p_lhs[v]]))
                query += cypher.remove_edge(edge_var)
                query += "\n"
                carry_variables.remove(edge_var)

        if len(self.removed_nodes()) > 0 or len(self.removed_edges()) > 0:
            query += cypher.with_vars(carry_variables)

        # Rename untouched vars as they are in P
        vars_to_rename = {}
        for n in self.lhs.nodes():
            if n not in self.removed_nodes():
                new_var_name = p_vars[keys_by_value(self.p_lhs, n)[0]]
                vars_to_rename[lhs_vars[n]] = new_var_name
                carry_variables.remove(lhs_vars[n])
        if len(vars_to_rename) > 0:
            query += "\n// Renaming vars to correspond to the vars of P\n"
            if len(carry_variables) > 0:
                query +=\
                    cypher.with_vars(carry_variables) +\
                    ", " + ", ".join(
                        "{} as {}".format(k, v)
                        for k, v in vars_to_rename.items()) +\
                    " "
            else:
                query +=\
                    "WITH " + ", ".join(
                        "{} as {}".format(k, v)
                        for k, v in vars_to_rename.items()) +\
                    " "
            query += "\n\n"
        for k, v in vars_to_rename.items():
            carry_variables.add(v)

        # Generate removal of edges between clones
        matches = []
        for u, v in self.removed_edges():
            if self.p_lhs[u] in self.cloned_nodes().keys() or\
               self.p_lhs[v] in self.cloned_nodes().keys():
                matches.append((
                    "({})-[{}:{}]->({})".format(
                        p_vars[u],
                        p_vars[u] + "_" + p_vars[v],
                        edge_label,
                        p_vars[v]),
                    p_vars[u] + "_" + p_vars[v]))

        if len(matches) > 0:
            query += "// Removing edges not bound to vars by matching (edges from/to clones)\n"
            for edge, var in matches:
                query += (
                    "// Removing '{}->{}' in P \n".format(u, v) +
                    "OPTIONAL MATCH {}\n".format(edge) +
                    "DELETE {}\n".format(var) +
                    cypher.with_vars(carry_variables)
                )

        # Generate node attrs removal subquery
        for node, attrs in self.removed_node_attrs().items():
            query += "// Removing properties from node '{}' of P \n".format(node)
            query += cypher.remove_attributes(p_vars[node], attrs)
            query += "\n\n"

        # Generate edge attrs removal subquery
        for e, attrs in self.removed_edge_attrs().items():
            u = e[0]
            v = e[1]
            query += "// Removing properties from edge {}->{} of P \n".format(
                u, v)
            query += cypher.with_vars(carry_variables)
            query += "MATCH ({})-[{}:edge]->({})\n".format(
                p_vars[u], p_vars[u] + "_" + p_vars[v], p_vars[v])
            carry_variables.add(p_vars[u] + "_" + p_vars[v])
            query += cypher.remove_attributes(p_vars[u] + "_" + p_vars[v], attrs)
            query += "\n\n"

        # Generate merging subquery
        for rhs_key, p_nodes in self.merged_nodes().items():
            query +=\
                "// Merging nodes '{}' of the preserved part ".format(p_nodes) +\
                "into '{}' \n".format(rhs_key)
            merged_id = "_".join(instance[self.p_lhs[p_n]]for p_n in p_nodes)
            q, carry_variables = cypher.merging_query1(
                original_vars=[p_vars[n] for n in p_nodes],
                merged_var=rhs_vars[rhs_key],
                merged_id=merged_id,
                merged_id_var=cypher.generate_var_name(),
                node_label=node_label,
                edge_label=edge_label,
                merge_typing=True,
                carry_vars=carry_variables,
                ignore_naming=True)
            query += q
            query += "\n\n"

        # Generate nodes addition subquery
        for rhs_node in self.added_nodes():
            query += "// Adding node '{}' from the rhs \n".format(rhs_node)
            if generate_var_ids:
                new_node_id_var = cypher.generate_var_name()
            else:
                new_node_id_var = "rhs_" + str(rhs_node) + "_id"
            q, carry_variables = cypher.add_node(
                rhs_vars[rhs_node], rhs_node, new_node_id_var,
                node_label=node_label,
                carry_vars=carry_variables,
                ignore_naming=True)
            query += q
            query += "\n\n"

        # Rename untouched vars as they are in rhs
        vars_to_rename = {}
        for n in self.rhs.nodes():
            if n not in self.added_nodes() and\
               n not in self.merged_nodes().keys():
                prev_var_name = p_vars[keys_by_value(self.p_rhs, n)[0]]
                vars_to_rename[prev_var_name] = rhs_vars[n]
                if prev_var_name in carry_variables:
                    carry_variables.remove(prev_var_name)

        if len(vars_to_rename) > 0:
            query += "// Renaming vars to correspond to the vars of rhs\n"
            if len(carry_variables) > 0:
                query +=\
                    cypher.with_vars(carry_variables) +\
                    ", " + ", ".join(
                        "{} as {}".format(k, v)
                        for k, v in vars_to_rename.items()) +\
                    " "
            else:
                query +=\
                    "WITH " + ", ".join(
                        "{} as {}".format(k, v)
                        for k, v in vars_to_rename.items()) +\
                    " "
            query += "\n\n"

        for k, v in vars_to_rename.items():
            carry_variables.add(v)

        # Generate node attrs addition subquery
        for rhs_node, attrs in self.added_node_attrs().items():
            query += "// Adding properties to the node " +\
                "'{}' from the rhs \n".format(rhs_node)
            query += cypher.add_attributes(rhs_vars[rhs_node], attrs)
            query += "\n\n"

        # Generate edges addition subquery
        # query += (
        #     "WITH [] as added_edges, " +
        #     ", ".join(carry_variables) + "\n"
        # )
        for u, v in self.added_edges():
            query += "// Adding edge '{}->{}' from the rhs \n".format(u, v)
            new_edge_var = rhs_vars[u] + "_" + rhs_vars[v]
            query += cypher.add_edge(
                edge_var=new_edge_var,
                source_var=rhs_vars[u],
                target_var=rhs_vars[v],
                edge_label=edge_label)
            if (u, v) in self.added_edge_attrs().keys():
                carry_variables.add(new_edge_var)
            query += "\n\n"

        # Generate edge attrs addition subquery
        for e, attrs in self.added_edge_attrs().items():
            u = e[0]
            v = e[1]
            query += "// Adding properties to an edge " +\
                "'{}'->'{}' from the rhs \n".format(u, v)
            query += cypher.with_vars(carry_variables) + '\n'

            edge_var = rhs_vars[u] + "_" + rhs_vars[v]
            if (u, v) not in self.added_edges():
                query += "MATCH ({})-[{}:edge]->({})\n".format(
                    rhs_vars[u], edge_var, rhs_vars[v])
                carry_variables.add(edge_var)

            query += cypher.add_attributes(edge_var, attrs)
            query += cypher.with_vars(carry_variables)
            query += "\n\n"

        query += "// Return statement \n"
        query += cypher.return_vars(carry_variables)

        # Dictionary defining a mapping from the generated
        # unique variable names to the names of nodes of the rhs
        rhs_vars_inverse = {v: k for k, v in rhs_vars.items()}

        return query, rhs_vars_inverse

    def plot(self, filename=None, title=None):
        plot_rule(self, filename, title)
