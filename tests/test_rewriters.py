"""."""
import os

from nose.tools import assert_equals

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import (Rewriter,
                                       Transformer)


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
        self.instances_ = Rewriter.find_matching(graph, self.LHS_)

        self.trans = Transformer(graph)

        self.trans.add_node(14, 'action', {'name' : 'BND'})
        self.trans.remove_node(2)
        self.trans.clone_node(4, 15)
        self.trans.merge_nodes(11, 12)

        self.instances_ = Rewriter.find_matching(graph, self.trans.L)

        Rewriter.rewrite(self.graph, self.instances_[0], self.trans)
