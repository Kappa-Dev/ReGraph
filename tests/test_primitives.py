import networkx as nx

from regraph.library.primitives import (clone_node,
                                        merge_nodes)


class TestPrimitives(object):

    def __init__(self):
        self.graph = nx.DiGraph()
        self.graph.add_node('1', {'name': 'EGFR', 'state': 'p'})
        self.graph.add_node('2', {'name': 'BND'})
        self.graph.add_node('3', {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        self.graph.add_node('4', {'name': 'SH2'})
        self.graph.add_node('5', {'name': 'EGFR'})
        self.graph.add_node('6', {'name': 'BND'})
        self.graph.add_node('7', {'name': 'Grb2'})

        self.graph.add_node('8', {'name': 'WAF1'})
        self.graph.add_node('9', {'name': 'BND'})
        self.graph.add_node('10', {'name': 'G1-S/CDK', 'state': 'p'})

        self.graph.add_node('11')
        self.graph.add_node('12')
        self.graph.add_node('13')

        edges = [
            ('1', '2', {'s': 'p'}),
            ('4', '2', {'s': 'u'}),
            ('4', '3'),
            ('5', '6', {'s': 'p'}),
            ('7', '6', {'s': 'u'}),
            ('8', '9'),
            ('10', '9'),
            ('11', '12'),
            ('12', '11'),
            ('12', '13'),
            ('13', '12'),
            ('11', '13'),
            ('13', '11'),
            ('5', '2', {'s': 'u'})
        ]

        self.graph.add_edges_from(edges)

    def test_clone_node(self):
        new_name = clone_node(self.graph, "1")
        assert(new_name in self.graph.nodes())
        assert((new_name, '2') in self.graph.edges())
        assert(self.graph.edge[new_name]['2'] == self.graph.edge['1']['2'])
        assert(self.graph.node[new_name] == self.graph.node['1'])

    def test_clone_node_undir(self):
        g = self.graph.to_undirected()
        clone_node(g, '1', 'a')
        assert('a' in g.nodes())
        assert(g.node['a'] == self.graph.node['1'])
        assert(g.edge['a']['2'] == g.edge['2']['a'])

    def test_merge_nodes(self):
        merge_nodes(self.graph, ["4", "5"])

    def test_merge_nodes_undir(self):
        pass
