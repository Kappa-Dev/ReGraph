import networkx as nx

from nose.tools import raises

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism,
                                             TypedHomomorphism)
from regraph.library.rewriters import (Transformer,
                                       Rewriter)
from regraph.library.graph_modeler import GraphModeler

import os

class TestGraphModeler(object):
    """."""

    def __init__(self):

        self.G0 = nx.DiGraph()
        self.G0.add_node(1)
        self.G0.add_node('1_1', {'type' : 1})
        self.G0.add_node('1_2', {'type' : 2})
        self.G0.add_node('1_3', {'type' : 3})
        self.G0.add_node(2)
        self.G0.add_node('2_1', {'type' : 1})
        self.G0.add_node('2_2', {'type' : 2})
        self.G0.add_node('2_3', {'type' : 3})
        self.G0.add_node(3, {'type' : 'BND'})

        edges = [
            ('1_1', 1),
            ('1_2', 1),
            ('1_3', 1),
            ('2_1', 2),
            ('2_2', 2),
            ('2_3', 2),
            ('1_1', 3),
            ('2_1', 3)
        ]

        self.G0.add_edges_from(edges)

        self.G1 = nx.DiGraph()
        self.G1.add_node('agent')
        self.G1.add_node('site', {'type' : {1, 2, 3}})
        self.G1.add_node('action', {'type' : ['BND']})

        edges = [
            ('site', 'agent'),
            ('site', 'action')
        ]

        self.G1.add_edges_from(edges)

        self.G0_G1 = {
            1 : 'agent',
            2 : 'agent',
            3 : 'action',
            '1_1' : 'site',
            '1_2' : 'site',
            '1_3' : 'site',
            '2_1' : 'site',
            '2_2' : 'site',
            '2_3' : 'site',
        }

        self.G2 = nx.DiGraph()
        self.G2.add_node('circle', {'type' : {1, 2, 3}})
        self.G2.add_node('square', {'type' : ['BND']})

        edges = [
            ('circle', 'circle'),
            ('circle', 'square')
        ]

        self.G2.add_edges_from(edges)

        self.G1_G2 = {
            'agent' : 'circle',
            'site' : 'circle',
            'action' : 'square'
        }

        self.modeler = GraphModeler([self.G2, self.G1, self.G0], [self.G1_G2, self.G0_G1])

    def test_init_with_ty_graphs(self):
        self.modeler = GraphModeler(self.modeler.graph_chain)

    def test_init_with_files(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        filename_graph = os.path.join(__location__, "graph_example.xml")
        filename_meta = os.path.join(__location__, "meta_example.xml")
        self.modeler = GraphModeler([filename_meta, filename_graph])

    def test_init_rewriting(self):
        trans = self.modeler.init_rewriting(0)
        assert(trans.G == self.modeler.graph_chain[0])

    def test_remove_layer(self):
        self.modeler.remove_layer(1)

        assert(len(self.modeler.graph_chain) == 2)

    def test_insert_layer(self):
        everything = nx.DiGraph()
        everything.add_node('everything', {'type' : {1, 2, 3, 'BND'}})
        everything.add_edge('everything', 'everything')

        hup = {
            'circle' : 'everything',
            'square' : 'everything'
        }

        self.modeler.insert_layer(everything, name='Everything', i=0, hup = hup)

        assert(len(self.modeler.graph_chain) == 4)
        assert(self.modeler.graph_chain[0].nodes() == everything.nodes())

    def test_get_by_id(self):
        assert(self.modeler.get_by_id(0).nodes() == self.G2.nodes())

    @raises(ValueError)
    def test_get_by_name(self):
        self.modeler.get_by_name("Graph")
