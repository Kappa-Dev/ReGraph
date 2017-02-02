import networkx as nx

from nose.tools import raises, assert_equals
from copy import deepcopy

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
        self.G0.add_node('1_1', {'typ' : 1})
        self.G0.add_node('1_2', {'typ' : 2})
        self.G0.add_node('1_3', {'typ' : 3})
        self.G0.add_node(2)
        self.G0.add_node('2_1', {'typ' : 1})
        self.G0.add_node('2_2', {'typ' : 2})
        self.G0.add_node('2_3', {'typ' : 3})
        self.G0.add_node(3, {'typ' : 'BND'})

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
        self.G1.add_node('site', {'typ' : {1, 2, 3}})
        self.G1.add_node('action', {'typ' : ['BND']})

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
        self.G2.add_node('circle', {'typ' : {1, 2, 3}})
        self.G2.add_node('square', {'typ' : ['BND']})

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
        assert_equals(trans.G, self.modeler.graph_chain[0])

    def test_remove_layer(self):
        self.modeler.remove_layer(1)

        assert_equals(len(self.modeler.graph_chain), 2)

    def test_insert_layer(self):
        everything = nx.DiGraph()
        everything.add_node('everything', {'typ' : {1, 2, 3, 'BND'}})
        everything.add_edge('everything', 'everything')

        hup = {
            'circle' : 'everything',
            'square' : 'everything'
        }

        self.modeler.insert_layer(everything, name='Everything', i=0, hup = hup)

        assert_equals(len(self.modeler.graph_chain), 4)
        assert_equals(self.modeler.graph_chain[0].nodes(), everything.nodes())

    def test_get_by_id(self):
        assert_equals(set(self.modeler.get_by_id(0).nodes()), set(self.G2.nodes()))

    @raises(ValueError)
    def test_get_by_name(self):
        self.modeler.get_by_name("Graph")

    def test_rewrites_and_propagations(self):
        transformations = Rewriter.gen_transformations(10, self.modeler.get_by_id(1))

        mod2 = deepcopy(self.modeler)
        trans = Rewriter.transformer_from_command(mod2.get_by_id(1), transformations)
        mod2.rewrite(1,
                     Homomorphism.identity(trans.L,
                                           trans.G),
                     trans)
        mod2.propagate_all()

        mod1 = deepcopy(self.modeler)
        mod1.canonical_rewrite_and_propagate(1, transformations)
