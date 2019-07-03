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
                                             get_unique_map_from_pushout,
                                             get_unique_map_to_pullback_complement_full,
                                             get_unique_map_to_pullback,
                                             get_unique_map_to_pullback_complement,
                                             pushout,
                                             pullback,
                                             compose)
from regraph import primitives
from regraph.networkx.plotting import plot_rule
from regraph.exceptions import (ReGraphWarning, ParsingError,
                                RuleError)

# from regraph.neo4j.cypher_utils.generic import (generate_var_name,
#                                                 with_vars,
#                                                 return_vars)
# from regraph.neo4j.cypher_utils.rewriting import (match_pattern_instance,
#                                                   cloning_query,
#                                                   remove_nodes,
#                                                   remove_edge,
#                                                   remove_attributes,
#                                                   merging_query1,
#                                                   add_node,
#                                                   add_edge,
#                                                   add_attributes)


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

    def __init__(self, p=None, lhs=None, rhs=None, p_lhs=None, p_rhs=None):
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
        if lhs is None:
            if p is not None:
                lhs = p
            else:
                lhs = p = nx.DiGraph()
        if rhs is None:
            if p is not None:
                rhs = p
            else:
                p = rhs = nx.DiGraph()

        if not p_lhs:
            self.p_lhs = identity(p, lhs)
        else:
            check_homomorphism(p, lhs, p_lhs)
            self.p_lhs = copy.deepcopy(p_lhs)

        if not rhs:
            rhs = p

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
        return "Left hand side\n%s\n%s\n" % (self.lhs.node, self.lhs.edges()) +\
            "Preserved part\n%s\n%s\n" % (self.p.node, self.p.edges()) +\
            "Right hand side\n%s\n%s\n" % (self.rhs.node, self.rhs.edges()) +\
            "P->L Homomorphism : %s\n" % self.p_lhs +\
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
                        self.p.adj[pred][p_new_node_id])
            for suc in self.p.successors(p_new_node_id):
                if (rhs_new_node_id, self.p_rhs[suc]) not in self.rhs.edges():
                    primitives.add_edge(
                        self.rhs,
                        rhs_new_node_id, self.p_rhs[suc],
                        self.p.adj[p_new_node_id][suc])

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
        if n1 not in self.p.nodes():
            raise RuleError(
                "Node '%s' does not exist in the preserved "
                "part of the rule" % n1
            )
        if n2 not in self.p.nodes():
            raise RuleError(
                "Node '%s' does not exist in preserved "
                "part of the rule" % n2
            )

        if (n1, n2) not in self.p.edges():
            raise RuleError(
                "Edge '%s->%s' does not exist in the preserved "
                "part of the rule" %
                (n1, n2)
            )
        else:
            primitives.remove_edge_attrs(self.p, n1, n2, attrs)
            primitives.remove_edge_attrs(
                self.rhs, self.p_rhs[n1], self.p_rhs[n2], attrs)
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
        if n not in list(self.rhs.nodes()):
            raise RuleError(
                "Node '%s' exists in neither lhs, nor p, nor rhs of the rule" %
                n)
        r_nodes = set()
        # if n in self.lhs.nodes():
        #     p_keys = keys_by_value(self.p_lhs, n)
        #     for p in p_keys:
        #         r_nodes.add(self.p_rhs[p])
        # elif n in self.p.nodes():
        #     r_nodes.add(self.p_rhs[n])
        if n in self.rhs.nodes():
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
            # self.p.node[k] = None
            primitives.set_node_attrs(self.p, k, {}, update=True)
            primitives.set_node_attrs(self.rhs, self.p_rhs[k], attrs, update=True)
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
                    self.p.adj[k1][k2] = None
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
                    self.p.adj[k1][k2] = None
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
        lhs = primitives.networkx_from_json(json_data["lhs"], directed)
        p = primitives.networkx_from_json(json_data["p"], directed)
        rhs = primitives.networkx_from_json(json_data["rhs"], directed)
        p_lhs = json_data["p_lhs"]
        p_rhs = json_data["p_rhs"]
        rule = cls(p, lhs, rhs, p_lhs, p_rhs)
        return rule

    def apply_to(self, graph, instance=None, inplace=False):
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
        if instance is None:
            instance = {
                n: n for n in self.lhs.nodes()
            }
        if isinstance(graph, nx.DiGraph):
            g_m, p_g_m, g_m_g = pullback_complement(
                self.p, self.lhs, graph, self.p_lhs, instance,
                inplace
            )
            g_prime, g_m_g_prime, rhs_g_prime = pushout(
                self.p, g_m, self.rhs, p_g_m, self.p_rhs, inplace)
        else:
            g_prime = graph
            rhs_g_prime = graph.rewrite(self, instance)

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
                if len(self.rhs.adj[s][t]) > 0:
                    attrs[(s, t)] = self.rhs.adj[s][t]
            new_attrs = {}
            for s_p_node in s_p_nodes:
                for t_p_node in t_p_nodes:
                    if (s_p_node, t_p_node) in self.p.edges():
                        new_attrs = attrs_union(
                            new_attrs,
                            dict_sub(
                                self.rhs.adj[s][t],
                                self.p.adj[s_p_node][t_p_node]
                            )
                        )
                    else:
                        new_attrs = self.rhs.adj[s][t]
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
            Dictionary where keys are nodes from `p`
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
            Dictionary where keys are edges from `p`
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
                                self.lhs.adj[s][t],
                                self.p.adj[s_p_node][t_p_node]
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
            commands += "ADD_EDGE %s %s %s.\n" % (u, v, self.rhs.adj[u][v])
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
            self.lhs.adj[u][v] = dict()
        for u, v in self.p.edges():
            self.p.adj[u][v] = dict()
        for u, v in self.rhs.edges():
            self.rhs.adj[u][v] = dict()

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

    def plot(self, filename=None, title=None):
        """Plot the rule."""
        plot_rule(self, filename, title)

    def refine(self, graph, instance):
        """Get refined (side-effect-free) version of the rule."""
        new_instance = {}
        for k, v in instance.items():
            new_instance[k] = v

        removed_attrs = self.removed_node_attrs()
        removed_edge_attrs = self.removed_edge_attrs()

        added_nodes = {}

        def add_neighbors_to_rule(n, removed_edges):

            def add_preserved_edges(lhs_source, lhs_target, edge_attrs, removed_edges):
                # Add preserved edges
                p_sources = keys_by_value(self.p_lhs, lhs_source)
                p_targets = keys_by_value(self.p_lhs, lhs_target)
                for sp in p_sources:
                    for tp in p_targets:
                        if (sp, tp) not in removed_edges:
                            if not primitives.exists_edge(self.p, sp, tp):
                                primitives.add_edge(self.p, sp, tp)
                                if not primitives.exists_edge(self.rhs, self.p_rhs[sp], self.p_rhs[tp]):
                                    primitives.add_edge(
                                        self.rhs, self.p_rhs[sp], self.p_rhs[tp])
                            # Compute preserved edge attributes
                            for k, v in edge_attrs.items():
                                if (sp, tp) not in removed_edge_attrs.keys() or\
                                   k not in removed_edge_attrs[(sp, tp)]:
                                    primitives.add_edge_attrs(
                                        self.p, sp, tp, {k: v})
                                    primitives.add_edge_attrs(
                                        self.rhs, self.p_rhs[sp], self.p_rhs[tp],
                                        {k: v})

            visited = set()
            # add successors
            for s in graph.successors(instance[n]):
                if s not in visited:
                    visited.add(s)
                    if s not in instance.values():
                        new_lhs_node = primitives.unique_node_id(self.lhs, s)
                        if s not in added_nodes:
                            self._add_node_lhs(new_lhs_node)
                            added_nodes[s] = new_lhs_node
                        else:
                            new_lhs_node = keys_by_value(added_nodes, s)[0]
                        new_instance[new_lhs_node] = s
                    else:
                        new_lhs_node = keys_by_value(instance, s)[0]
                    edge_attrs = primitives.get_edge(graph, instance[n], s)
                    if not primitives.exists_edge(self.lhs, n, new_lhs_node):
                        primitives.add_edge(self.lhs, n, new_lhs_node, edge_attrs)
                    else:
                        primitives.add_edge_attrs(self.lhs, n, new_lhs_node, edge_attrs)
                    add_preserved_edges(n, new_lhs_node, edge_attrs, removed_edges)

            visited = set()
            # add predecessors
            for p in graph.predecessors(instance[n]):
                if p not in visited:
                    visited.add(p)
                    if p not in instance.values():
                        new_lhs_node = primitives.unique_node_id(self.lhs, p)
                        if p not in added_nodes:
                            self._add_node_lhs(new_lhs_node)
                            added_nodes[p] = new_lhs_node
                        else:
                            new_lhs_node = keys_by_value(added_nodes, p)[0]
                        new_instance[new_lhs_node] = p
                    else:
                        new_lhs_node = keys_by_value(instance, p)[0]
                    edge_attrs = primitives.get_edge(graph, p, instance[n])
                    if not primitives.exists_edge(self.lhs, new_lhs_node, n):
                        primitives.add_edge(self.lhs, new_lhs_node, n, edge_attrs)
                    else:
                        primitives.add_edge_attrs(self.lhs, new_lhs_node, n, edge_attrs)
                    add_preserved_edges(new_lhs_node, n, edge_attrs, removed_edges)

        # Remove side-effects of node removal
        for n in self.removed_nodes():
            # Add nodes adjacent to removed nodes
            all_attrs = primitives.get_node(graph, instance[n])
            primitives.set_node_attrs(
                self.lhs, n, all_attrs, update=True)
            # Add nodes adjacent to removed nodes
            add_neighbors_to_rule(n, self.removed_edges())

        # Remove side-effects of edge removal
        visited_edges = set()
        for sp, tp in self.removed_edges():
            if (instance[self.p_lhs[sp]], instance[self.p_lhs[tp]]) not in visited_edges:
                visited_edges.add((
                    instance[self.p_lhs[sp]], instance[self.p_lhs[tp]]))
                all_edge_attrs = primitives.get_edge(
                    graph, instance[self.p_lhs[sp]], instance[self.p_lhs[tp]])
                primitives.set_edge(
                    self.lhs, self.p_lhs[sp], self.p_lhs[tp],
                    all_edge_attrs)

        # Remove side-effects of merges
        for rhs_node, p_nodes in self.merged_nodes().items():
            for p_node in p_nodes:
                all_attrs = primitives.get_node(
                    graph, instance[self.p_lhs[p_node]])
                primitives.set_node_attrs(
                    self.lhs, self.p_lhs[p_node], all_attrs, update=True)

                for k, v in all_attrs.items():
                    if p_node not in removed_attrs or\
                       k not in removed_attrs[p_node]:
                        primitives.add_node_attrs(
                            self.p, p_node, {k: v})
                        primitives.add_node_attrs(
                            self.rhs, rhs_node, {k: v})

                # Add nodes adjacent to removed nodes
                add_neighbors_to_rule(self.p_lhs[p_node], self.removed_edges())

        return new_instance

    def get_inverted_rule(self):
        """Get inverted rule with LHS and RHS swaped."""
        return Rule(self.p, self.rhs, self.lhs, self.p_rhs, self.p_lhs)

    @classmethod
    def identity_rule(cls):
        """Create an identity rule."""
        return cls(nx.DiGraph(), nx.DiGraph(), nx.DiGraph())

    def is_identity(self):
        """Test if the rule is identity."""
        return not self.is_restrictive() and not self.is_relaxing()


def _generate_p_instance(rule, lhs_instance, rhs_instance):
    # Compute representation of p1/p2 instances.
    p_instance = {}
    for n in rule.p.nodes():
        lhs_node = rule.p_lhs[n]
        rhs_node = rule.p_rhs[n]
        if rhs_node in rule.merged_nodes().keys():
            if lhs_node in rule.cloned_nodes().keys():
                # generate names
                clone_name = str(lhs_instance[lhs_node])
                i = 0
                while clone_name in p_instance.values():
                    i += 1
                    clone_name = str(lhs_instance[lhs_node]) + str(i)
                p_instance[n] = clone_name
            else:
                p_instance[n] = lhs_instance[lhs_node]
        else:
            p_instance[n] = rhs_instance[rhs_node]
    return p_instance


def compose_rules(rule1, lhs_instance1, rhs_instance1,
                  rule2, lhs_instance2, rhs_instance2,
                  return_all=False):
    """Compose two rules respecting instances."""
    if rule1.is_identity() and not return_all:
        return rule2, lhs_instance2, rhs_instance2
    if rule2.is_identity() and not return_all:
        return rule1, lhs_instance1, lhs_instance1

    p1_instance = _generate_p_instance(
        rule1, lhs_instance1, rhs_instance1)
    p2_instance = _generate_p_instance(
        rule2, lhs_instance2, rhs_instance2)

    d_nodes = [
        v
        for v in rhs_instance1.values()
        if v in lhs_instance2.values()
    ]
    d_rhs1 = {
        v: k
        for k, v in rhs_instance1.items()
        if v in lhs_instance2.values()
    }
    d_lhs2 = {
        v: keys_by_value(lhs_instance2, v)[0]
        for v in rhs_instance1.values()
        if v in lhs_instance2.values()
    }

    d = nx.DiGraph()
    d.add_nodes_from(d_nodes)

    h, rhs1_h, lhs2_h = pushout(
        d, rule1.rhs, rule2.lhs, d_rhs1, d_lhs2)

    p1_p, p1_p1_p, p1_p_h = pullback_complement(
        rule1.p, rule1.rhs, h, rule1.p_rhs, rhs1_h)

    p2_p, p2_p2_p, p2_p_h = pullback_complement(
        rule2.p, rule2.lhs, h, rule2.p_lhs, lhs2_h)

    lambd, lhs1_lambda, p1_p_lambda = pushout(
        rule1.p, rule1.lhs, p1_p, rule1.p_lhs, p1_p1_p)

    rho, rhs2_rho, p2_p_rho = pushout(
        rule2.p, rule2.rhs, p2_p, rule2.p_rhs, p2_p2_p)

    pi, pi_p1_p, pi_p2_p = pullback(
        p1_p, p2_p, h, p1_p_h, p2_p_h)

    pi_lambda = compose(pi_p1_p, p1_p_lambda)
    pi_rho = compose(pi_p2_p, p2_p_rho)

    rule = Rule(pi, lambd, rho, pi_lambda, pi_rho)

    # find h instance
    h_instance = get_unique_map_from_pushout(
        h.nodes(), rhs1_h, lhs2_h, rhs_instance1, lhs_instance2)

    # find p1_p instance
    g1_m_g2 = {
        p1_instance[k]: compose(rule1.p_rhs, rhs_instance1)[k]
        for k in rule1.p_rhs.keys()
    }
    for k, v in lhs_instance2.items():
        if v not in g1_m_g2.values():
            g1_m_g2[v] = v

    p1_p_instance = get_unique_map_to_pullback_complement(
        rule1.p_rhs, rhs_instance1, p1_instance,
        g1_m_g2, p1_p1_p, compose(p1_p_h, h_instance))

    # find p2_p instance
    g2_m_g2 = {
        p2_instance[k]: compose(rule2.p_lhs, lhs_instance2)[k]
        for k in rule2.p_lhs.keys()
    }
    for k, v in rhs_instance1.items():
        if v not in g2_m_g2.values():
            g2_m_g2[v] = v

    p2_p_instance = get_unique_map_to_pullback_complement(
        rule2.p_lhs, lhs_instance2, p2_instance,
        g2_m_g2, p2_p2_p, compose(p2_p_h, h_instance))

    g1_m_g1 = {
        p1_instance[k]: compose(rule1.p_lhs, lhs_instance1)[k]
        for k, v in rule1.p_lhs.items()
    }
    for k in g1_m_g2.keys():
        if k not in g1_m_g1.keys():
            g1_m_g1[k] = k

    lhs_instance = get_unique_map_from_pushout(
        lambd.nodes(), lhs1_lambda, p1_p_lambda,
        lhs_instance1, compose(p1_p_instance, g1_m_g1))

    g2_m_g3 = {
        p2_instance[k]: compose(rule2.p_rhs, rhs_instance2)[k]
        for k in rule2.p_rhs.keys()
    }
    for k in g2_m_g2.keys():
        if k not in g2_m_g3.keys():
            g2_m_g3[k] = k

    rhs_instance = get_unique_map_from_pushout(
        rho.nodes(), p2_p_rho, rhs2_rho,
        compose(p2_p_instance, g2_m_g3), rhs_instance2)

    # Remove clone followed by merge
    for lhs_node, p_nodes in rule.cloned_nodes().items():
        rhs_nodes = set([rule.p_rhs[p] for p in p_nodes])
        if len(rhs_nodes) == 1:
            new_p_node = primitives.merge_nodes(rule.p, p_nodes)
            for n in p_nodes:
                del rule.p_lhs[n]
                del rule.p_rhs[n]
            rule.p_lhs[new_p_node] = lhs_node
            rule.p_rhs[new_p_node] = list(rhs_nodes)[0]

    if return_all:
        return rule, lhs_instance, rhs_instance, {
            "h": h,
            "rhs1_h": rhs1_h,
            "lhs2_h": lhs2_h,
            "p1_p1_p": p1_p1_p,
            "p1_p_h": p1_p_h,
            "p2_p2_p": p2_p2_p,
            "p2_p_h": p2_p_h,
            "p1_p_lambda": p1_p_lambda,
            "lhs1_lambda": lhs1_lambda,
            "p2_p_rho": p2_p_rho,
            "rhs2_rho": rhs2_rho,
            "pi_p1_p": pi_p1_p,
            "pi_p2_p": pi_p2_p
        }

    else:
        return rule, lhs_instance, rhs_instance


def _fold_lhs(rule, lhs_instance, rhs_instance):
    # Create a non-injective map from P to G
    # following P -> L >-> G
    p_instance = {
        k: lhs_instance[v]
        for k, v in rule.p_lhs.items()
    }

    # Start from intial P and R from delta
    p = copy.deepcopy(rule.p)

    rhs = copy.deepcopy(rule.rhs)
    p_rhs = {}
    instance = {}

    # Merge all the clones in P and respective nodes of R
    updated_p_nodes = {}
    merged_rhs_nodes = {}
    for v in set(p_instance.values()):
        p_nodes = keys_by_value(p_instance, v)
        if len(p_nodes) > 1:
            p_name = primitives.merge_nodes(p, p_nodes)
            rhs_nodes = set([
                merged_rhs_nodes[rule.p_rhs[n]]
                if rule.p_lhs[n] in merged_rhs_nodes else rule.p_rhs[n]
                for n in p_nodes
            ])
            for n in p_nodes:
                updated_p_nodes[n] = p_name

            if len(rhs_nodes) > 1:
                rhs_name = primitives.merge_nodes(rhs, rhs_nodes)
                for n in rhs_nodes:
                    merged_rhs_nodes[n] = rhs_name

    # Make the rule preserve removed nodes
    for n in rule.removed_nodes():
        p_node = primitives.generate_new_node_id(p, n)
        primitives.add_node(p, p_node)
        updated_p_nodes[n] = p_node
        rhs_node = primitives.generate_new_node_id(rhs, n)
        primitives.add_node(rhs, rhs_node)
        p_rhs[p_node] = rhs_node
        instance[p_node] = lhs_instance[n]

    # Recostructing the dictionaries P->R and P >-> G
    # consistently
    for p_node in rule.p.nodes():
        if p_node not in updated_p_nodes.keys():
            new_p_node = p_node
        else:
            new_p_node = updated_p_nodes[p_node]

        rhs_node = rule.p_rhs[p_node]
        if rhs_node not in merged_rhs_nodes.keys():
            new_rhs_node = rhs_node
        else:
            new_rhs_node = merged_rhs_nodes[rhs_node]

        instance[new_p_node] = p_instance[p_node]
        p_rhs[new_p_node] = new_rhs_node

    new_rule = Rule(p, p, rhs, p_rhs=p_rhs)

    return new_rule, instance, updated_p_nodes


def _create_merging_rule(rule, lhs_instance, rhs_instance):
    # We use pusout from L <- P -> R as a new R'
    # That performs the merge from both sides
    # Then the left rule is L -> R', and the right one is R -> R'
    new_rhs, lhs_new_rhs, rhs_new_rhs = pushout(
        rule.p, rule.lhs, rule.rhs, rule.p_lhs, rule.p_rhs)

    left_rule = Rule(rule.lhs, rule.lhs, new_rhs, p_rhs=lhs_new_rhs)
    right_rule = Rule(rule.rhs, rule.rhs, new_rhs, p_rhs=rhs_new_rhs)
    return left_rule, right_rule


def _create_merging_rule_hierarchy(rule_hierarchy, lhs_instances, rhs_instances):

    left_hierarchy = {
        "rules": {},
        "rule_homomorphisms": {}
    }
    right_hierarchy = {
        "rules": {},
        "rule_homomorphisms": {}
    }
    for graph, rule in rule_hierarchy["rules"].items():
        left_rule, right_rule = _create_merging_rule(
            rule, lhs_instances[graph], rhs_instances[graph])
        left_hierarchy["rules"][graph] = left_rule
        right_hierarchy["rules"][graph] = right_rule

    for (source, target), (lhs_h, p_h, rhs_h) in rule_hierarchy[
            "rule_homomorphisms"].items():
        new_rhs_h = get_unique_map_from_pushout(
            left_hierarchy["rules"][source].rhs.nodes(),
            left_hierarchy["rules"][source].p_rhs,
            right_hierarchy["rules"][source].p_rhs,
            compose(
                lhs_h,
                left_hierarchy["rules"][target].p_rhs),
            compose(
                rhs_h,
                right_hierarchy["rules"][target].p_rhs)
        )
        left_hierarchy["rule_homomorphisms"][(source, target)] = (
            rule_hierarchy["rule_homomorphisms"][(source, target)][0],
            rule_hierarchy["rule_homomorphisms"][(source, target)][0],
            new_rhs_h
        )
        right_hierarchy["rule_homomorphisms"][(source, target)] = (
            rule_hierarchy["rule_homomorphisms"][(source, target)][2],
            rule_hierarchy["rule_homomorphisms"][(source, target)][2],
            new_rhs_h
        )
    return left_hierarchy, right_hierarchy


def compose_rule_hierarchies(rule_hierarchy1, lhs_instances1, rhs_instances1,
                             rule_hierarchy2, lhs_instances2, rhs_instances2):
    """Compose two rule hierarchies."""
    if len(rule_hierarchy1["rules"]) == 0:
        return rule_hierarchy2, lhs_instances2, rhs_instances2
    if len(rule_hierarchy2["rules"]) == 0:
        return rule_hierarchy1, lhs_instances1, rhs_instances1

    graphs = set(rule_hierarchy1["rules"].keys()).union(
        rule_hierarchy2["rules"].keys())
    homomorphisms = set(rule_hierarchy1["rule_homomorphisms"].keys()).union(
        rule_hierarchy2["rule_homomorphisms"].keys())

    new_rule_hierarchy = {
        "rules": {},
        "rule_homomorphisms": {}
    }
    new_lhs_instances = {}
    new_rhs_instances = {}

    composition_data = {}

    # Compose rules
    for graph in graphs:
        if graph in rule_hierarchy1["rules"]:
            rule1 = rule_hierarchy1["rules"][graph]
            lhs_instance1 = lhs_instances1[graph]
            rhs_instance1 = rhs_instances1[graph]
        else:
            rule1 = Rule.identity_rule()
            lhs_instance1 = {}
            rhs_instance1 = {}
        if graph in rule_hierarchy2["rules"]:
            rule2 = rule_hierarchy2["rules"][graph]
            lhs_instance2 = lhs_instances2[graph]
            rhs_instance2 = rhs_instances2[graph]
        else:
            rule2 = Rule.identity_rule()
            lhs_instance2 = {}
            rhs_instance2 = {}

        new_rule, new_lhs_instance, new_rhs_instance, data = compose_rules(
            rule1, lhs_instance1, rhs_instance1,
            rule2, lhs_instance2, rhs_instance2, return_all=True)
        new_rule_hierarchy["rules"][graph] = new_rule
        new_lhs_instances[graph] = new_lhs_instance
        new_rhs_instances[graph] = new_rhs_instance
        composition_data[graph] = data

    # Compute rule homomorphisms
    for source, target in homomorphisms:
        lhs_hom1, p_hom1, rhs_hom1 = rule_hierarchy1["rule_homomorphisms"][
            (source, target)]
        lhs_hom2, p_hom2, rhs_hom2 = rule_hierarchy2["rule_homomorphisms"][
            (source, target)]

        source_data = composition_data[source]
        target_data = composition_data[target]

        # H_G -> H_T
        h_hom = get_unique_map_from_pushout(
            source_data["h"].nodes(),
            source_data["rhs1_h"],
            source_data["lhs2_h"],
            compose(rhs_hom1, target_data["rhs1_h"]),
            compose(lhs_hom2, target_data["lhs2_h"])
        )
        # P*G_1 -> P*T_1
        p1_p_hom = get_unique_map_to_pullback_complement_full(
            target_data["p1_p1_p"], target_data["p1_p_h"],
            p_hom1, source_data["p1_p1_p"],
            compose(source_data["p1_p_h"], h_hom))

        # P*G_2 -> P*T_2
        p2_p_hom = get_unique_map_to_pullback_complement_full(
            target_data["p2_p2_p"], target_data["p2_p_h"],
            p_hom2, source_data["p2_p2_p"],
            compose(source_data["p2_p_h"], h_hom))

        # Pi_G -> Pi_T
        pi_hom = get_unique_map_to_pullback(
            new_rule_hierarchy["rules"][target].p.nodes(),
            target_data["pi_p1_p"], target_data["pi_p2_p"],
            compose(source_data["pi_p1_p"], p1_p_hom),
            compose(source_data["pi_p2_p"], p2_p_hom))

        # L_G -> L_T
        lambda_hom = get_unique_map_from_pushout(
            new_rule_hierarchy["rules"][source].lhs.nodes(),
            source_data["lhs1_lambda"], source_data["p1_p_lambda"],
            compose(lhs_hom1, target_data["lhs1_lambda"]),
            compose(p1_p_hom, target_data["p1_p_lambda"]))

        # R_G -> R_T
        rho_hom = get_unique_map_from_pushout(
            new_rule_hierarchy["rules"][source].rhs.nodes(),
            source_data["p2_p_rho"], source_data["rhs2_rho"],
            compose(p2_p_hom, target_data["p2_p_rho"]),
            compose(rhs_hom2, target_data["rhs2_rho"]))

        new_rule_hierarchy["rule_homomorphisms"][(source, target)] = (
            lambda_hom, pi_hom, rho_hom
        )
    return new_rule_hierarchy, new_lhs_instances, new_rhs_instances


def invert_rule_hierarchy(rule_hierarchy):
    """Get inverted rule hierarchy (swapped lhs and rhs)."""
    new_rule_hierarchy = {
        "rules": {},
        "rule_homomorphisms": {}
    }
    for graph, rule in rule_hierarchy["rules"].items():
        new_rule_hierarchy["rules"][graph] = rule.get_inverted_rule()

    for (source, target), (lhs_h, p_h, rhs_h) in rule_hierarchy[
            "rule_homomorphisms"].items():
        new_rule_hierarchy["rule_homomorphisms"][(source, target)] = (
            rhs_h, p_h, lhs_h
        )
    return new_rule_hierarchy
