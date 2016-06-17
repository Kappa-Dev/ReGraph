"""."""
import os

from nose.tools import assert_equals
from nose.tools import raises

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import (Rewriter,
                                       Transformer)
from regraph.library.utils import (merge_attributes)


class TestRewrites(object):
    """."""

    def __init__(self):
        self.graph = TypedDiGraph()
        self.graph.add_node(1, 'agent',
                          {'name': 'EGFR', 'state': 'p'})
        self.graph.add_node(2, 'action', attrs={'name': 'BND'})
        self.graph.add_node(3, 'agent',
                          {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        self.graph.add_node(4, 'region', attrs={'name': 'SH2'})
        self.graph.add_node(5, 'agent', attrs={'name': 'EGFR'})
        self.graph.add_node(6, 'action', attrs={'name': 'BND'})
        self.graph.add_node(7, 'agent', attrs={'name': 'Grb2'})

        self.graph.add_node(8, 'agent', attrs={'name': 'WAF1'})
        self.graph.add_node(9, 'action', {'name': 'BND'})
        self.graph.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

        self.graph.add_node(11, 'agent')
        self.graph.add_node(12, 'agent')
        self.graph.add_node(13, 'agent')

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

        self.graph.add_edges_from(edges)

        self.graph.set_edge(1, 2, {'s': 'p'})
        self.graph.set_edge(4, 2, {'s': 'u'})
        self.graph.set_edge(5, 6, {'s': 'p'})
        self.graph.set_edge(7, 6, {'s': 'u'})
        self.graph.set_edge(5, 2, {'s': 'u'})

    def test_add_node(self):
        trans = Transformer(self.graph.copy())

        trans.add_node(14, 'agent', {'name' : 'Grb3'})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(14 in Gprime.nodes())
        assert(Gprime.node[14].type_ == 'agent')
        assert(Gprime.node[14].attrs_ == {'name' : {'Grb3'}})

    def test_merge_nodes(self):
        trans = Transformer(self.graph.copy())

        trans.merge_nodes(1, 3, 14)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(14 in Gprime.nodes())
        assert(Gprime.node[14].type_ == 'agent')
        assert(Gprime.node[14].attrs_ ==
               merge_attributes(self.graph.node[1].attrs_,
                                self.graph.node[3].attrs_))

    def test_remove_node(self):
        trans = Transformer(self.graph.copy())

        trans.remove_node(1)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(1 not in Gprime.nodes())

    def test_clone_node(self):
        trans = Transformer(self.graph.copy())

        trans.clone_node(1, 111)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(1 in Gprime.nodes())
        assert(111 in Gprime.nodes())
        assert(Gprime.node[1].type_ == Gprime.node[111].type_)
        assert(Gprime.node[1].attrs_ == Gprime.node[111].attrs_)

    def test_add_edge(self):
        trans = Transformer(self.graph.copy())

        trans.add_edge(8, 10)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert((8,10) in Gprime.edges())

    def test_remove_edge(self):
        trans = Transformer(self.graph.copy())

        trans.remove_edge(13, 11)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert((13,11) not in Gprime.edges())

    def test_add_node_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.add_node_attrs(1, {'name' : {'Grb1'}})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(Gprime.node[1].attrs_ == {'name': {'EGFR','Grb1'}, 'state': {'p'}})

    def test_add_edge_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.add_edge_attrs(1, 2, {'name' : 'Grb1'})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(Gprime.get_edge(1, 2) ==  {'s': {'p'}, 'name' : {'Grb1'}})

    def test_remove_node_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.remove_node_attrs(1, {'name' : {'EGFR'}})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(Gprime.node[1].attrs_ ==  {'state': {'p'}, 'name' : set()})

    def test_remove_edge_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.remove_edge_attrs(1, 2, {'s' : 'p'})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)[0].target_

        assert(Gprime.get_edge(1, 2) ==  {'s' : set()})

    def test_multiple_rewrites(self):


        trans = Transformer(self.graph.copy())

        trans.add_node(14, 'action', {'name' : 'BND'})
        trans.remove_node(2)
        trans.clone_node(4, 15)
        trans.merge_nodes(11, 12)

        instance = Homomorphism.identity(trans.L, trans.G)
        Rewriter.rewrite(instance, trans)
