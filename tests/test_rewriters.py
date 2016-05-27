"""."""
from nose.tools import assert_equals

from regraph.library.data_structures import TypedDiGraph
from regraph.library.rewriters import Rewriter


class TestRewrites(object):
    """."""

    def __init__(self):
        graph = TypedDiGraph()
        graph.add_node(1, 'agent',
                          {'name': 'EGFR', 'state': 'p'})
        graph.add_node(2, 'action', attrs={'name': 'BND'})
        graph.add_node(3, 'agent',
                          {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        graph.add_node(4, 'region', attrs={'name': 'SH2'})
        graph.add_node(5, 'agent', attrs={'name': 'EGFR'})
        graph.add_node(6, 'action', attrs={'name': 'BND'})
        graph.add_node(7, 'agent', attrs={'name': 'Grb2'})

        graph.add_node(8, 'agent', attrs={'name': 'WAF1'})
        graph.add_node(9, 'action', {'name': 'BND'})
        graph.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

        graph.add_node(11, 'agent')
        graph.add_node(12, 'agent')
        graph.add_node(13, 'agent')

        edges = [
            (1, 2),
            (4, 2),
            (4, 3),
            (5, 6),
            (7, 6),
            (8, 9),
            (10, 9),
            (11, 12),
            (12, 11),
            (12, 13),
            (13, 12),
            (11, 13),
            (13, 11),
            (5, 2)
        ]

        graph.add_edges_from(edges)

        graph.set_edge(1, 2, {'s': 'p'})
        graph.set_edge(4, 2, {'s': 'u'})
        graph.set_edge(5, 6, {'s': 'p'})
        graph.set_edge(7, 6, {'s': 'u'})
        graph.set_edge(5, 2, {'s': 'u'})

        self.LHS_ = TypedDiGraph()

        self.LHS_.add_node(1, 'agent', {'name': 'EGFR'})
        self.LHS_.add_node(2, 'action', {'name': 'BND'})
        self.LHS_.add_node(3, 'region')
        self.LHS_.add_node(4, 'agent', {'name': 'Grb2'})
        self.LHS_.add_node(5, 'agent', {'name': 'EGFR'})
        self.LHS_.add_node(6, 'action', {'name': 'BND'})
        self.LHS_.add_node(7, 'agent', {'name': 'Grb2'})

        self.LHS_.add_edges_from([(1, 2), (3, 2), (3, 4), (5, 6), (7, 6)])

        self.LHS_.set_edge(1, 2, {'s': 'p'})
        self.LHS_.set_edge(5, 6, {'s': 'p'})

        self.rw_ = Rewriter(graph)
        self.instances_ = self.rw_.find_matching(self.LHS_)

    def test_find_matching(self):
        assert_equals(self.instances_, [{1: 1, 2: 2, 3: 4, 4: 3, 5: 5, 6: 6, 7: 7}])

        new_pattern = TypedDiGraph()
        new_pattern.add_node("a", "agent")
        new_pattern.add_node("b", "agent")
        new_pattern.add_node("c", "agent")

        new_pattern.add_edges_from([("a", "b"), ("a", "c")])
        instances = self.rw_.find_matching(new_pattern)
        assert_equals(3, len(instances))

    def test_transform_instance(self):
        self.rw_.transform_instance(
            self.instances_[0],
            """delete_node 6.\n"""
            """merge [1, 5] method union as merge_1.\n"""
            """merge [4, 7] as merge_2.\n"""
            """add_edge merge_1 merge_2.\n"""
            """clone merge_1 as clone_1.\n"""
            """clone 3 as clone_2.""")
