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
                primitives.add_edge(
                    self.rhs,
                    self.p_rhs[pred], rhs_new_node_id,
                    self.p.edge[pred][p_new_node_id])
            for suc in self.p.successors(p_new_node_id):
                primitives.add_edge(
                    self.rhs,
                    rhs_new_node_id, self.p_rhs[suc],
                    self.p.edge[p_new_node_id][suc])

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
                    "Node '%s' is not found in neither left-hand "
                    "side nor preserved part" % n2)

        if len(p_keys_2) == 0:
            if n2 in self.p.nodes():
                p_keys_2 = [n2]
            else:
                raise RuleError(
                    "Node '%s' is not found in neither left-hand "
                    "side nor preserved part" % str(n2))

        for k1 in p_keys_1:
            for k2 in p_keys_2:
                if (k1, k2) in self.p.edges():
                    primitives.remove_edge(self.p, k1, k2)
                    primitives.remove_edge(self.rhs, self.p_rhs[k1], self.p_rhs[k2])
                else:
                    raise RuleError(
                        "Edge '%s->%s' does not exist in the preserved part"
                        % (k1, k2))

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

    def inject_merge_nodes(self, node_list, node_id=None):
        """Inject merge of a collection of nodes by the rule.

        Parameters
        ----------
        node_list : iterable
            Collection of ids of nodes from the preserved part to merge.
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
        rhs_merged_nodes = set()
        for n in node_list:
            rhs_merged_nodes.add(self.p_rhs[n])
            if n not in self.p.nodes():
                raise RuleError(
                    "Node with the id '%s' does not exist in the "
                    "preserved part of the rule" % n
                )
            nodes_to_merge.add(self.p_rhs[n])
        new_name = primitives.merge_nodes(
            self.rhs,
            list(nodes_to_merge),
            node_id=node_id
        )
        # Update mappings
        for n in node_list:
            self.p_rhs[n] = new_name
        for r_node in rhs_merged_nodes:
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
        if n not in self.lhs.nodes() + self.p.nodes() + self.rhs.nodes():
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
        if n1 not in self.lhs.nodes() + self.rhs.nodes() + self.p.nodes():
            raise RuleError(
                "Node '%s' exists in neither lhs, nor p, nor rhs "
                "of the rule" % n1
            )

        if n2 not in self.lhs.nodes() + self.rhs.nodes() + self.p.nodes():
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
            new_attrs = {}
            for p_node in p_nodes:
                new_attrs = attrs_union(new_attrs, dict_sub(
                    self.lhs.node[node], self.p.node[p_node]))
            if len(new_attrs) > 0:
                attrs[node] = new_attrs
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
                                self.lhs.edge[s][t],
                                self.p.edge[s_p_node][t_p_node]
                            )
                        )
            if len(new_attrs) > 0:
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

    def _add_node_lhs(self, node_id, attrs=None):
        if node_id not in self.lhs.nodes():
            primitives.add_node(self.lhs, node_id, attrs)

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
