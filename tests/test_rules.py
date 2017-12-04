import networkx as nx

from nose.tools import raises

from regraph.attribute_sets import FiniteSet
from regraph.rules import Rule
from regraph.utils import assert_graph_eq, normalize_attrs
from regraph.exceptions import RuleError
import regraph.primitives as prim


class TestRule(object):
    """Class for testing `regraph.rules` module."""

    def __init__(self):
        """Initialize test."""
        # Define the left hand side of the rule
        self.pattern = nx.DiGraph()
        self.pattern.add_node(1)
        self.pattern.add_node(2)
        self.pattern.add_node(3)
        prim.add_node(self.pattern, 4, {'a': 1})

        self.pattern.add_edges_from([
            (1, 2),
            (3, 2),
            (4, 1)
        ])
        prim.add_edge(self.pattern, 2, 3, {'a': {1}})

        # Define preserved part of the rule
        self.p = nx.DiGraph()
        self.p.add_node('a')
        self.p.add_node('b')
        self.p.add_node('c')
        prim.add_node(self.p, 'd', {'a': 1})

        self.p.add_edges_from([
            ('a', 'b'),
            ('d', 'a')
        ])
        prim.add_edge(self.p, 'b', 'c', {'a': {1}})

        # Define the right hand side of the rule
        self.rhs = nx.DiGraph()
        self.rhs.add_node('x')
        self.rhs.add_node('y')
        self.rhs.add_node('z')
        # self.rhs.add_node('s', {'a': 1})
        prim.add_node(self.rhs, 's', {'a': 1})
        self.rhs.add_node('t')

        self.rhs.add_edges_from([
            ('x', 'y'),
            # ('y', 'z', {'a': {1}}),
            ('s', 'x'),
            ('t', 'y')
        ])
        prim.add_edge(self.rhs, 'y', 'z', {'a': {1}})

        # Define mappings
        self.p_lhs = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.p_rhs = {'a': 'x', 'b': 'y', 'c': 'z', 'd': 's'}
        return

    def test_add_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_node('g', {'a': 1})
        assert_graph_eq(rule.p, self.p)
        assert_graph_eq(rule.lhs, self.pattern)
        assert('g' in rule.rhs)
        t = {'a': set([1])}
        normalize_attrs(t)
        assert(rule.rhs.node['g'] == t)
        return

    def test_remove_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_node(2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert('b' not in rule.p.nodes())
        assert(('a', 'b') not in rule.p.edges())
        assert(('b', 'c') not in rule.p.edges())
        assert('y' not in rule.rhs.nodes())
        assert(('x', 'y') not in rule.rhs.edges())
        assert(('t', 'y') not in rule.rhs.edges())
        assert(('y', 'z') not in rule.rhs.edges())
        return

    def test_add_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_edge(4, 2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert_graph_eq(rule.p, self.p)
        assert(('s', 'y') in rule.rhs.edges())
        return

    @raises(RuleError)
    def test_remove_non_existing_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_edge(3, 2)
        return

    def test_remove_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_edge(1, 2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert(('d', 'a') in rule.p.edges())
        assert(('s', 'x') in rule.rhs.edges())
        return

    def test_clone_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.clone_node(2)
        assert_graph_eq(rule.lhs, self.pattern)
        assert('b1' in rule.p.nodes())
        assert('y1' in rule.rhs.nodes())
        assert(('a', 'b1') in rule.p.edges())
        assert(('b1', 'c') in rule.p.edges())
        assert(('x', 'y1') in rule.rhs.edges())
        assert(('t', 'y1') in rule.rhs.edges())
        return

    def test_merge_nodes(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        new_name = rule.merge_nodes(1, 4)
        assert_graph_eq(rule.lhs, self.pattern)
        assert_graph_eq(rule.p, self.p)
        assert(new_name in rule.rhs.nodes())
        assert((new_name, new_name) in rule.rhs.edges())
        assert((new_name, 'y') in rule.rhs.edges())
        return

    def test_add_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_node_attrs(1, {'a': 1})
        t1 = {'a': {1}}
        t2 = {'a': {1, 2}}
        t3 = {'a': {1, 2}, 'b': {1}}
        normalize_attrs(t1)
        normalize_attrs(t2)
        normalize_attrs(t3)
        assert(rule.rhs.node['x'] == t1)
        rule.add_node_attrs(4, {'a': 1})
        assert(rule.rhs.node['s'] == t1)
        rule.add_node_attrs(4, {'a': 2})
        assert(rule.rhs.node['s'] == t2)
        rule.add_node_attrs(4, {'b': 1})
        assert(rule.rhs.node['s'] == t3)
        return

    def test_remove_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_node_attrs(4, {'a': 2})
        rule.remove_node_attrs(4, {'a': 1})
        t1 = {'a': set()}
        t2 = {'a': set([2])}
        normalize_attrs(t1)
        normalize_attrs(t2)
        assert(rule.p.node['d'] == t1)
        assert(rule.rhs.node['s'] == t2)
        return

    def test_update_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.update_node_attrs(4, {'b': 2})
        assert(rule.p.node['d'] is None)
        test_dict = {'b': {2}}
        normalize_attrs(test_dict)
        assert(rule.rhs.node['s'] == test_dict)
        return

    def test_add_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.add_edge_attrs(4, 1, {'amazing': True})
        assert_graph_eq(rule.p, self.p)
        t = {'amazing': {True}}
        normalize_attrs(t)
        assert(rule.rhs.edge['s']['x'] == t)
        return

    def test_remove_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.remove_edge_attrs(2, 3, {'a': set()})
        t1 = {'a': {1}}
        normalize_attrs(t1)
        assert(rule.p.edge['b']['c'] == t1)
        assert(rule.rhs.edge['y']['z'] == t1)
        rule.remove_edge_attrs(2, 3, {'a': {1}})
        t2 = {'a': set()}
        normalize_attrs(t2)
        print(t2)
        print(rule.p.edge['b']['c'])
        assert(rule.p.edge['b']['c'] == t2)
        assert(rule.rhs.edge['y']['z'] == t2)
        return

    def test_update_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.update_edge_attrs(2, 3, {'b': 1})
        assert(rule.p.edge['b']['c'] is None)
        test_dict = {'b': FiniteSet({1})}
        # normalize_attrs(test_dict)
        assert(rule.rhs.edge['y']['z'] == test_dict)
        return

    def merge_node_list(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.merge_node_list([2, 3], 'wow_name')
        assert(rule.lhs == self.pattern)
        assert(rule.p == self.p)
        assert('wow_name' in rule.rhs.nodes())
        assert(('wow_name', 'wow_name') in rule.rhs.edges())
        assert(('wow_name', 'y') in rule.rhs.edges())

    def test_all(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs)
        rule.clone_node(2)
        rule.remove_node(1)

    def test_from_script(self):
        commands = "clone 2 as 21.\nadd_node 'a' {'a': 1}.\ndelete_node 3."
        rule = Rule.from_transform(self.pattern, commands=commands)
        assert('a' in rule.rhs.nodes())
        assert('21' in rule.rhs.nodes())
        assert(3 not in rule.rhs.nodes())

    def test_component_getters(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(
            pattern,
            [(1, {"a1": {1}}), (2, {"a2": {2}}), (3, {"a3": {3}})]
        )
        prim.add_edges_from(
            pattern,
            [
                (1, 2, {"a12": {12}}),
                (2, 3),
                (3, 2, {"a32": {32}})
            ]
        )

        rule = Rule.from_transform(pattern)
        rule.remove_node(1)
        rule.remove_edge(2, 3)
        new_name, _ = rule.clone_node(2)
        print(new_name)
        rule.remove_node_attrs(3, {"a3": {3}})
        rule.remove_edge_attrs(3, 2, {"a32": {32}})
        rule.add_node_attrs(3, {"a3": {100}})
        rule.add_node(4)
        rule.add_edge_rhs(4, "21")

        assert(rule.removed_nodes() == {1})
        print(rule.removed_edges())
        assert(rule.removed_edges() == {(2, 3), (new_name[0], 3)})
        assert(len(rule.cloned_nodes()) == 1 and
               2 in rule.cloned_nodes().keys())
        assert(len(rule.removed_node_attrs()) == 1 and
               3 in rule.removed_node_attrs()[3]["a3"])
        assert(len(rule.removed_edge_attrs()) == 1 and
               32 in rule.removed_edge_attrs()[(3, 2)]["a32"])

        assert(rule.added_nodes() == {4})
        assert(rule.added_edges() == {(4, "21")})
        # rule.merged_nodes()
        # rule.added_edge_attrs()
        assert(len(rule.added_node_attrs()) == 1 and
               100 in rule.added_node_attrs()[3]["a3"])
        assert(rule.is_restrictive() and rule.is_relaxing())

    def test_from_commands(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(
            pattern,
            [(1, {'state': 'p'}),
             (2, {'name': 'BND'}),
             3,
             4]
        )
        prim.add_edges_from(
            pattern,
            [(1, 2, {'s': 'p'}),
             (3, 2, {'s': 'u'}),
             (3, 4)]
        )

        p = nx.DiGraph()
        prim.add_nodes_from(
            p,
            [(1, {'state': 'p'}), ("1_clone", {'state': 'p'}), (2, {'name': 'BND'}), 3, 4])
        prim.add_edges_from(
            p, [(1, 2), ('1_clone', 2), (3, 4)])

        rhs = nx.DiGraph()
        prim.add_nodes_from(
            rhs,
            [(1, {'state': 'p'}), ("1_clone", {'state': 'p'}), (2, {'name': 'BND'}), 3, 4, 5])

        prim.add_edges_from(
            rhs, [(1, 2, {'s': 'u'}), ('1_clone', 2), (2, 4), (3, 4), (5, 3)])

        p_lhs = {1: 1, '1_clone': 1, 2: 2, 3: 3, 4: 4}
        p_rhs = {1: 1, '1_clone': '1_clone', 2: 2, 3: 3, 4: 4}
        rule1 = Rule(p, pattern, rhs, p_lhs, p_rhs)

        commands = "clone 1.\n" +\
            "delete_edge 3 2.\n" +\
            "add_node 5.\n" +\
            "add_edge 2 4.\n" +\
            "add_edge 5 3."

        rule2 = Rule.from_transform(pattern, commands)
        assert((5, 3) in rule2.rhs.edges())
        assert(5 in rule2.rhs.nodes() and 5 not in rule2.p.nodes())
        assert((2, 4) in rule2.rhs.edges())
