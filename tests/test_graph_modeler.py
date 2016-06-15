import networkx as nx

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism,
                                             TypedHomomorphism)
from regraph.library.graph_modeler import GraphModeler

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

    def test_modeler(self):
        modeler = GraphModeler([self.G2, self.G1, self.G0], [self.G1_G2, self.G0_G1])

        trans = Transformer(self.G2)

        trans.clone_node('square')

        instances = Rewriter.find_matching(trans.L, self.G2)

        modeler.rewrite(0, instances[0], trans)

        print(modeler.get_by_id(0).nodes())
        print(modeler.get_by_id(0).edges())

        modeler.propagate_all()

        for g in modeler.graph_chain:
            print(g.nodes())
            print(g.edges())
