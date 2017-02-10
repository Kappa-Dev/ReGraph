from nose.tools import raises

from regraph.library.data_structures import Homomorphism
from regraph.library.graphs import (TypedDiGraph,
                                    TypedGraph)
from regraph.library.rules import Rule


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
        commands = "clone 2 as 21.\nadd_node 'a' type 'black_circle'.\ndelete_node 3."
        rule = Rule.from_transform(self.pattern, commands=commands)
        assert('a' in rule.rhs.nodes())
        assert('21' in rule.rhs.nodes())
        assert(3 not in rule.rhs.nodes())

    def test_is_valid_metamodel(self):
        rule = Rule.from_transform(self.pattern)
        meta_model = TypedDiGraph()

        meta_model.add_node('white_square', 'square')
        meta_model.add_node('black_circle', 'circle')
        meta_model.add_node('white_circle', 'circle')

        meta_model.add_edges_from([
            ('white_square', 'black_circle'),
            ('black_circle', 'white_circle'),
        ])

        meta_model_1 = TypedDiGraph()

        meta_model_1.add_node('black_square', 'square')
        meta_model_1.add_node('white_square', 'square')
        meta_model_1.add_node('black_circle', 'circle')
        meta_model_1.add_node('white_circle', 'circle')

        meta_model_1.add_edges_from([
                ('black_square', 'black_square'),
                ('black_square', 'white_square'),
                ('black_square', 'white_circle'),
                ('white_square', 'black_circle'),
                ('white_circle', 'black_square')
            ])

        assert(rule.is_valid_typing(meta_model) is False)
        assert(rule.is_valid_typing(meta_model_1) is False)

    @raises(ValueError)
    def test_update_metamodel_not_valid(self):
        rule = Rule.from_transform(self.pattern)
        meta_model = TypedDiGraph()

        meta_model.add_node('white_square', 'square')
        meta_model.add_node('black_circle', 'circle')
        meta_model.add_node('white_circle', 'circle')

        meta_model.add_edges_from([
            ('white_square', 'black_circle'),
            ('black_circle', 'white_circle'),
        ])
        rule.update_typing(meta_model)

    def test_update_metamodel(self):
        rule = Rule.from_transform(self.pattern)
        meta_model = TypedDiGraph()

        meta_model.add_node('black_square', 'square')
        meta_model.add_node('white_square', 'square')
        meta_model.add_node('black_circle', 'circle')
        meta_model.add_node('white_circle', 'circle')

        meta_model.add_edges_from([
                ('black_square', 'black_square'),
                ('black_square', 'white_square'),
                ('black_square', 'white_circle'),
                ('white_square', 'black_circle'),
                ('black_circle', 'white_circle'),
                ('white_circle', 'black_square'),
                ('black_circle', 'black_circle')
            ])
        rule.update_typing(meta_model)

    def test_remove_by_type(self):
        rule = Rule.from_transform(self.pattern)
        rule.remove_by_type('black_square')
        assert(all([rule.p.node[n].type_ != 'black_square' for n in rule.p.nodes()]))
        assert(all([rule.rhs.node[n].type_ != 'black_square' for n in rule.rhs.nodes()]))

    def test_convert_type(self):
        rule = Rule.from_transform(self.pattern)
        rule.convert_type('black_square', 'white_square')
        assert(rule.p.valid_metamodel() is False)
        assert(rule.lhs.valid_metamodel() is False)
        assert(rule.rhs.valid_metamodel() is False)

    def test_remove_edges_by_type(self):
        rule = Rule.from_transform(self.pattern)
        rule.remove_edges_by_type('black_square', 'white_circle')