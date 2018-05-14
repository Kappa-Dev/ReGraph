"""Collection of tests for ReGraph_neo4j graphs."""

from regraph.neo4j.graphs import *


class TestGraphs(object):

    def __init__(self):
        """Init of the test class."""
        self.g = Neo4jGraph(
              uri="bolt://localhost:7687", user="neo4j", password="admin")
        res = self.g.clear()
        nodes = [
            ("a", {"name": "EGFR", "state": "p"}),
            ("b", {"name": "BND"}),
            ("c", {"name": "Grb2", "aa": "S", "loc": 90}),
            ("d", {"name": "SH2"}),
            ("e", {"name": "EGFR"}),
            ("f", {"name": "BND"}),
            ("g", {"name": "Grb2"}),
            ("h", {"name": "WAF1"}),
            ("i", {"name": "BND"}),
            ("j", {"name": "G1-S/CDK", "state": "p"}),
            "k", "l", "m"
            ]
        edges = [
            ("a", "b", {"s": "p"}),
            ("d", "b", {"s": "u"}),
            ("d", "c"),
            ("e", "f", {"s": "p"}),
            ("g", "f", {"s": "u"}),
            ("h", "i"),
            ("i", "h"),
            ("j", "h", {"act": {1}}),
            ("j", "i", {"act": {2}}),
            ("k", "l"),
            ("l", "k"),
            ("l", "m"),
            ("m", "l"),
            ("k", "m"),
            ("m", "k"),
            ("e", "b", {"s": "u"})
            ]
        self.g.add_nodes_from(nodes)
        self.g.add_edges_from(edges)

    def test_add_node(self):
        # Case 1 : "x" is not in the graph
        attrs = {"act": {1}}
        self.g.add_node("x", attrs)
        query = get_node("x")
        result = self.g.execute(query)
        try:
            res_node = dict(result.value()[0])
        except(IndexError):
            res_node = dict(result.value())
        assert(len(res_node) != 0)
        for k in attrs.keys():
            for v in attrs[k]:
                assert(v in res_node[k])

    def test_add_edge(self):
        # Case 1 : (s, t) is not in the graph
        s = "a"
        t = "d"
        attrs = {"act": {1}}
        self.g.add_edge(s, t, attrs)
        query = get_edge(s, t)
        result = self.g.execute(query)
        try:
            res_edge = dict(result.value()[0])
        except(IndexError):
            res_edge = dict(result.value())
            assert(len(res_edge) != 0)
        for k in attrs.keys():
            for v in attrs[k]:
                assert(v in res_edge[k])

    def test_remove_node(self):
        # Case 1 : "a" is in the graph
        self.g.remove_node("x")
        query = get_node("x")
        result = self.g.execute(query)
        try:
            res_node = dict(result.value()[0])
        except(IndexError):
            res_node = dict(result.value())
        assert(len(res_node) == 0)

    def test_remove_edge(self):
        s = "a"
        t = "d"
        self.g.remove_edge(s, t)
        query = get_edge(s, t)
        result = self.g.execute(query)
        try:
            res_edge = dict(result.value()[0])
        except(IndexError):
            res_edge = dict(result.value())
        assert(len(res_edge) == 0)

    def test_clone_node(self):
        node = "a"
        clone = "a_clone"
        res = self.g.clone_node(node, clone)
        print(res)


t = TestGraphs()
t.test_clone_node()
