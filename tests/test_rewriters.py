"""."""
import os

from nose.tools import assert_equals
# from nose.tools import raises

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import (Rule,
                                       Rewriter)
from regraph.library.utils import (merge_attributes,
                                   plot_graph)
from nose.tools import raises
import copy


class TestRule(object):
    
    def __init__(self):
        # Define meta-model for rules
        self.meta_model = TypedDiGraph()

        self.meta_model.add_node('black_square', 'square')
        self.meta_model.add_node('white_square', 'square')
        self.meta_model.add_node('black_circle', 'circle')
        self.meta_model.add_node('white_circle', 'circle')

        self.meta_model.add_edges_from([
                ('black_square', 'black_square'),
                ('black_square', 'white_square'),
                ('black_square', 'white_circle'),
                ('white_square', 'black_circle'),
                ('black_circle', 'white_circle'),
                ('white_circle', 'black_square')
            ])

        # Define the left hand side of the rule
        self.pattern = TypedDiGraph()
        self.pattern.add_node(1, 'black_circle')
        self.pattern.add_node(2, 'white_circle')
        self.pattern.add_node(3, 'black_square')
        self.pattern.add_node(4, 'black_circle', {'a': 1})
        
        self.pattern.add_edges_from([
                (1, 2),
                (3, 2),
                (2, 3, {'a': {1}}),
                (4, 1)
            ])

        # Define preserved part of the rule
        self.p = TypedDiGraph()
        self.p.add_node('a', 'black_circle')
        self.p.add_node('b', 'white_circle')
        self.p.add_node('c', 'black_square')
        self.p.add_node('d', 'black_circle', {'a': 1})

        self.p.add_edges_from([
            ('a', 'b'),
            ('b', 'c', {'a': {1}}),
            ('d', 'a')
        ])

        # Define the right hand side of the rule
        self.rhs = TypedDiGraph()
        self.rhs.add_node('x', 'black_circle')
        self.rhs.add_node('y', 'white_circle')
        self.rhs.add_node('z', 'black_square')
        self.rhs.add_node('s', 'black_circle', {'a': 1})
        self.rhs.add_node('t', 'black_circle')

        self.rhs.add_edges_from([
            ('x', 'y'),
            ('y', 'z', {'a': {1}}),
            ('s', 'x'),
            ('t', 'y')
        ])

        # Define mappings
        self.p_lhs = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.p_rhs = {'a': 'x', 'b': 'y', 'c': 'z', 'd': 's'}
        return

    def test_add_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.add_node('g', 'black_circle', {'a': 1})
        assert(rule.p == self.p)
        assert(rule.lhs == self.pattern)
        assert('g' in rule.rhs)
        assert(rule.rhs.node['g'].type_ == 'black_circle')
        assert(rule.rhs.node['g'].attrs_ == {'a': set([1])})
        return
    
    def test_remove_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.remove_node(2)
        assert(rule.lhs == self.pattern)
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
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.add_edge(4, 2)
        assert(rule.lhs == self.pattern)
        assert(rule.p == self.p)
        assert(('s', 'y') in rule.rhs.edges())
        return

    @raises(ValueError)
    def test_remove_non_existing_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.remove_edge(3, 2)
        return

    def test_remove_edge(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.remove_edge(1, 2)
        assert(rule.lhs == self.pattern)
        assert(('d', 'a') in rule.p.edges())
        assert(('s', 'x') in rule.rhs.edges())
        return

    def test_clone_node(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        new_name = rule.clone_node(2)
        assert(rule.lhs == self.pattern)
        assert('b1' in rule.p.nodes())
        assert('y1' in rule.rhs.nodes())
        assert(('a', 'b1') in rule.p.edges())
        assert(('b1', 'c') in rule.p.edges())
        assert(('x', 'y1') in rule.rhs.edges())
        assert(('t', 'y1') in rule.rhs.edges())
        return

    def test_merge_nodes(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        new_name = rule.merge_nodes(1, 4)
        assert(rule.lhs == self.pattern)
        assert(rule.p == self.p)
        assert(new_name in rule.rhs.nodes())
        assert((new_name, new_name) in rule.rhs.edges())
        assert((new_name, 'y') in rule.rhs.edges())
        return

    def test_add_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.add_node_attrs(1, {'a': 1})
        assert(rule.rhs.node['x'].attrs_ == {'a': {1}})
        rule.add_node_attrs(4, {'a': 1})
        assert(rule.rhs.node['s'].attrs_ == {'a': {1}})
        rule.add_node_attrs(4, {'a': 2})
        assert(rule.rhs.node['s'].attrs_ == {'a': {1, 2}})
        rule.add_node_attrs(4, {'b': 1})
        assert(rule.rhs.node['s'].attrs_ == {'a': {1, 2}, 'b': {1}})
        return

    def test_remove_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.add_node_attrs(4, {'a': 2})
        rule.remove_node_attrs(4, {'a': 1})
        assert(rule.p.node['d'].attrs_ == {'a': set()})
        assert(rule.rhs.node['s'].attrs_ == {'a': set([2])})
        return   

    def test_update_node_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.update_node_attrs(4, {'b': 2})
        assert(rule.p.node['d'].attrs_ is None)
        assert(rule.rhs.node['s'].attrs_ == {'b': {2}})
        return

    def test_add_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.add_edge_attrs(4, 1, {'amazing': True})
        assert(rule.p == self.p)
        assert(rule.rhs.edge['s']['x'] == {'amazing': {True}})
        return

    def test_remove_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.remove_edge_attrs(2, 3, {'a': set()})
        assert(rule.p.edge['b']['c'] == {'a': {1}})
        assert(rule.rhs.edge['y']['z'] == {'a': {1}})
        rule.remove_edge_attrs(2, 3, {'a': {1}})
        assert(rule.p.edge['b']['c'] == {'a': set()})
        assert(rule.rhs.edge['y']['z'] == {'a': set()})
        return

    def test_update_edge_attrs(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.update_edge_attrs(2, 3, {'b': 1})
        assert(rule.p.edge['b']['c'] is None)
        assert(rule.rhs.edge['y']['z'] == {'b': {1}})
        return

    def merge_node_list(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.merge_node_list([2, 3], 'wow_name')
        assert(rule.lhs == self.pattern)
        assert(rule.p == self.p)
        assert('wow_name' in rule.rhs.nodes())
        assert(('wow_name', 'wow_name') in rule.rhs.edges())
        assert(('wow_name', 'y') in rule.rhs.edges())

    def test_all(self):
        rule = Rule(self.p, self.pattern, self.rhs,
                    self.p_lhs, self.p_rhs, typing_graph=self.meta_model)
        rule.clone_node(2)
        rule.remove_node(1)
        # print(rule)

    def test_from_script(self):
        commands = """""" 
        pass

class TestRewriter(object):
    
    def __init__(self):
        self.meta_meta_model = TypedDiGraph()

        self.meta_meta_model.add_node('square', None)
        self.meta_meta_model.add_node('circle', None)

        self.meta_meta_model.add_edges_from([
                ('square', 'square'),
                ('square', 'circle'),
                ('circle', 'circle'),
                ('circle', 'square')
            ]
        )

        self.meta_model = TypedDiGraph(self.meta_meta_model)

        self.meta_model.add_node('black_square', 'square')
        self.meta_model.add_node('white_square', 'square')
        self.meta_model.add_node('black_circle', 'circle')
        self.meta_model.add_node('white_circle', 'circle')

        self.meta_model.add_edges_from([
                ('black_square', 'black_square'),
                ('black_square', 'white_square'),
                ('black_square', 'white_circle'),
                ('white_square', 'black_circle'),
                ('black_circle', 'white_circle'),
                ('black_circle', 'black_circle'),
                ('white_circle', 'black_square')
            ])

        self.model = TypedDiGraph(self.meta_model)

        self.model.add_node(1, 'black_square', {"a": {1, 2, 3}})
        self.model.add_node(2, 'black_square')

        self.model.add_node(3, 'white_square')
        self.model.add_node(4, 'white_square')

        self.model.add_node(5, 'black_circle', {'c': {2, 11}})
        self.model.add_node(6, 'black_circle', {'c': {1, 10}})

        self.model.add_node(7, 'white_circle', {"b": {1, 2}})
        self.model.add_node(8, 'white_circle')

        self.model.add_edges_from([
                (1, 2),
                (1, 4),
                (1, 7),
                (2, 4),
                (4, 5),
                (5, 8),
                (6, 7, {"a": {1, 2, 3}}),
                (7, 1),
                (5, 6, {"a": {1, 2}})
            ])
        return

    def test_simple_rewrite(self):
        graph = copy.deepcopy(self.model)

        # Define rewriting rule
        pattern = TypedDiGraph()
        pattern.add_node(1, 'black_circle', {'c': {1}})
        pattern.add_node(2, 'white_circle', {'b': {1, 2}})
        pattern.add_node(3, 'black_square', {'a': {1, 2}})
        pattern.add_node(4, 'black_circle', {'c': {2}})
        
        pattern.add_edges_from([
                (1, 2, {"a": {1, 2}}),
                (3, 2),
                (2, 3),
                (4, 1, {"a": 1})
            ])

        # Define preserved part of the rule
        p = TypedDiGraph()
        p.add_node('a',  'black_circle', {'c': {1}})
        p.add_node('b',  'white_circle', {'b': {1}})
        p.add_node('b1', 'white_circle', {'b': {2}})
        p.add_node('c',  'black_square', {'a': {1}})
        p.add_node('d',  'black_circle', {'c': {2}})

        p.add_edges_from([
            ('a', 'b', {'a': {1}}),
            ('b', 'c'),
            ('a', 'b1', {'a': {2}}),
            ('b1', 'c'),
            ('d', 'a')
        ])

        # Define the right hand side of the rule
        rhs = TypedDiGraph()
        rhs.add_node('x',  'black_circle', {'c': {1, 2, 3}})
        rhs.add_node('y',  'white_circle', {'b': {1, 5}})
        rhs.add_node('y1', 'white_circle', {'b': {2, 6}})
        rhs.add_node('z',  'black_square', {'a': {1,5}})
        rhs.add_node('t',  'black_circle')

        rhs.add_edges_from([
            ('x', 'y', {"a": {1, 5}}),
            ('x', 'y1', {"a": {2, 5}}),
            ('y', 'z', {'a': {1}}),
            ('y1', 'z'),
            ('x', 'x'),
            ('t', 'y')
        ])

        # Define mappings
        p_lhs = {'a': 1, 'b': 2, 'b1': 2, 'c': 3, 'd': 4}
        p_rhs = {'a': 'x', 'b': 'y', 'b1': 'y1', 'c': 'z', 'd': 'x'}

        rule = Rule(p, pattern, rhs, p_lhs, p_rhs)

        rewriter = Rewriter(graph)
        instances = rewriter.find_matching(pattern)
        res_graph = rewriter.apply_rule(instances[0], rule)

        rewriter.apply_rule_in_place(instances[0], rule)
        assert(res_graph == graph)
    