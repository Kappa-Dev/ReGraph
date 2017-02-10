# from nose.tools import raises
import copy

from regraph.library.graphs import TypedDiGraph
from regraph.library.rewriters import (Rewriter,
                                       apply,
                                       find_matching,
                                       )
from regraph.library.rules import Rule


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
        ])

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
        p.add_node('a', 'black_circle', {'c': {1}})
        p.add_node('b', 'white_circle', {'b': {1}})
        p.add_node('b1', 'white_circle', {'b': {2}})
        p.add_node('c', 'black_square', {'a': {1}})
        p.add_node('d', 'black_circle', {'c': {2}})

        p.add_edges_from([
            ('a', 'b', {'a': {1}}),
            ('b', 'c'),
            ('a', 'b1', {'a': {2}}),
            ('b1', 'c'),
            ('d', 'a')
        ])

        # Define the right hand side of the rule
        rhs = TypedDiGraph()
        rhs.add_node('x', 'black_circle', {'c': {1, 2, 3}})
        rhs.add_node('y', 'white_circle', {'b': {1, 5}})
        rhs.add_node('y1', 'white_circle', {'b': {2, 6}})
        rhs.add_node('z', 'black_square', {'a': {1, 5}})
        rhs.add_node('t', 'black_circle')

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

        instances = find_matching(graph, pattern)
        rewriter = Rewriter(graph)
        res_graph = apply(graph, instances[0], rule)
        rewriter.apply_transform(instances[0], rule)
        assert(res_graph == graph)
