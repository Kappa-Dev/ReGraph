import networkx as nx

from regraph.library.primitives import *


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

    def test_add_node(self):
        try:
            add_node(self.graph, "1")
            raise ValueError()
        except:
            pass
        attrs = {"a": {1}}
        add_node(self.graph, "a", attrs)
        assert("a" in self.graph.nodes())
        assert(self.graph.node["a"] == attrs)
        assert(id(attrs) != id(self.graph.node["a"]))

    def test_remove_node(self):
        try:
            remove_node(self.graph, "b")
            raise ValueError()
        except:
            pass
        node_to_remove = '13'
        in_edges = self.graph.in_edges(node_to_remove)
        out_edges = self.graph.out_edges(node_to_remove)
        remove_node(self.graph, node_to_remove)
        assert(node_to_remove not in self.graph.nodes())
        for edge in in_edges + out_edges:
            assert(edge not in self.graph.edges())

    def test_remove_node_undirected(self):
        g = self.graph.to_undirected()

        node_to_remove = '12'
        neighbors = g.neighbors(node_to_remove)
        remove_node(g, node_to_remove)
        assert(node_to_remove not in g.nodes())
        for n in neighbors:
            assert((n, node_to_remove) not in g.edges())
            assert((node_to_remove, n) not in g.edges())

    def test_add_edge(self):
        try:
            add_edge(self.graph, '1', '2')
            raise ValueError("")
        except:
            pass

        s = '1'
        t = '5'
        attrs = {"a": {1}}
        add_edge(self.graph, s, t, attrs)
        assert((s, t) in self.graph.edges())
        assert(self.graph.edge[s][t] == attrs)
        assert(id(self.graph.edge[s][t]) != id(attrs))

    def test_add_edge_undirected(self):
        g = self.graph.to_undirected()
        try:
            add_edge(g, '1', '2')
            raise ValueError("")
        except:
            pass

        s = '1'
        t = '5'
        attrs = {"a": {1}}
        add_edge(g, s, t, attrs)
        assert((s, t) in g.edges())
        assert(g.edge[s][t] == attrs)
        assert(g.edge[t][s] == attrs)
        assert(id(g.edge[s][t]) != id(attrs) and id(g.edge[t][s]) != id(attrs))
        assert(id(g.edge[s][t]) == id(g.edge[t][s]))

    def test_remove_edge(self):
        pass

    def test_clone_node(self):
        node_to_clone = '1'

        in_edges = self.graph.in_edges(node_to_clone)
        out_edges = self.graph.out_edges(node_to_clone)

        new_name = clone_node(self.graph, node_to_clone)

        assert(new_name in self.graph.nodes())
        assert(self.graph.node[new_name] == self.graph.node[node_to_clone])
        assert(id(self.graph.node[new_name]) != id(self.graph.node[node_to_clone]))
        for u, _ in in_edges:
            assert((u, new_name) in self.graph.edges())
            assert(
                self.graph.edge[u][node_to_clone] ==
                self.graph.edge[u][new_name]
            )
            assert(
                id(self.graph.edge[u][node_to_clone]) !=
                id(self.graph.edge[u][new_name])
            )
        for _, v in out_edges:
            assert((new_name, v) in self.graph.edges())

    def test_clone_node_undirected(self):
        g = self.graph.to_undirected()
        node_to_clone = '1'
        neighbors = g.neighbors(node_to_clone)
        new_name = 'a'
        clone_node(g, node_to_clone, new_name)
        assert(new_name in g.nodes())
        assert(g.node[new_name] == self.graph.node[node_to_clone])
        assert(id(g.node[new_name]) != id(self.graph.node[node_to_clone]))
        for n in neighbors:
            assert((n, new_name) in g.edges() or (new_name, n) in g.edges())
            assert(g.edge[n][new_name] == g.edge[new_name][n])
            assert(id(g.edge[n][new_name]) == id(g.edge[new_name][n]))

            assert(g.edge[n][new_name] == g.edge[n][node_to_clone])
            assert(id(g.edge[n][new_name]) != id(g.edge[n][node_to_clone]))

    def test_merge_nodes(self):
        merge_nodes(self.graph, ["4", "5"])

    def test_merge_nodes_undir(self):
        pass
