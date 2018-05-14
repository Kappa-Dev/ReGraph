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

    def get_node_attributes(self, node):
        query = get_node("x")
        result = self.g.execute(query)
        try:
            res_node = dict(result.value()[0])
        except(IndexError):
            res_node = dict(result.value())
        return(res_node)

    def test_add_node(self):
        # Case 1 : "x" is not in the graph
        node = "x"
        attrs = {"act": {1}}
        self.g.add_node(node, attrs)
        res_node = self.get_node_attributes(node)
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
        node = "x"
        self.g.remove_node(node)
        res_node = self.get_node_attributes(node)
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
        self.g.clone_node(node, clone)
        # Assert that the 2 nodes have the same properties
        res_node_a = self.get_node_attributes(node)
        res_node_clone = self.get_node_attributes(clone)
        assert(res_node_a.keys() == res_node_clone.keys())
        for k in res_node_clone.keys():
            for v in res_node_clone[k]:
                assert(v in res_node_a[k])
        # Assert that the 2 nodes have the same target nodes
        query1 = (
            "MATCH (s:node {{id : '{}'}})-[]-> (t)".format(node) +
            "RETURN t.id"
        )
        query2 = (
            "MATCH (s:node {{id : '{}'}})-[]-> (t)".format(clone) +
            "RETURN t.id"
        )
        targets_a = self.g.execute(query1).value()
        targets_clone = self.g.execute(query2).value()
        assert(targets_a == targets_clone)
        # Assert that the 2 nodes have the same source nodes
        query3 = (
            "MATCH (s)-[]-> (t:node {{id : '{}'}})".format(node) +
            "RETURN t.id"
        )
        query4 = (
            "MATCH (s)-[]-> (t:node {{id : '{}'}})".format(clone) +
            "RETURN t.id"
        )
        sources_a = self.g.execute(query3).value()
        sources_clone = self.g.execute(query4).value()
        assert(sources_a == sources_clone)



t = TestGraphs()
t.test_clone_node()
