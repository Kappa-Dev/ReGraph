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

    def find_successors(self, node):
        query = (
            "MATCH (p:node {{id : '{}'}})-[]-> (s:node)".format(node) +
            "RETURN s.id"
        )
        succ = set(self.g.execute(query).value())
        return(succ)

    def find_predecessors(self, node):
        query = (
            "MATCH (p:node)-[]-> (s:node {{id : '{}'}})".format(node) +
            "RETURN p.id"
        )
        pred = set(self.g.execute(query).value())
        return(pred)

    def test_add_node(self):
        # Case 1 : "x" is not in the graph
        node = "x"
        attrs = {"act": {1}}
        self.g.add_node(node, attrs)
        attrs_node = self.g.get_node("z")
        assert(attrs_node is not None)
        # if (res_node is not None):
        for k in attrs.keys():
            for v in attrs[k]:
                assert(v in attrs_node[k])

    def test_add_edge(self):
        # Case 1 : (s, t) is not in the graph
        s = "a"
        t = "d"
        attrs = {"act": {1}}
        self.g.add_edge(s, t, attrs)
        query = get_edge(s, t)
        attrs_edge = self.g.execute(query)
        assert(attrs_edge is not None)
        for k in attrs.keys():
            for v in attrs[k]:
                assert(v in attrs_edge[k])

    def test_remove_node(self):
        # Case 1 : "a" is in the graph
        node = "x"
        self.g.remove_node(node)
        attrs_edge = self.g.get_node(node)
        assert(attrs_edge is None)

    def test_remove_edge(self):
        s = "a"
        t = "d"
        self.g.remove_edge(s, t)
        query = get_edge(s, t)
        attrs_edge = self.g.execute(query)
        assert(attrs_edge is None)

    def test_clone_node(self):
        node = "b"
        clone = "b_clone"
        self.g.clone_node(node, clone)
        # Assert that the 2 nodes have the same properties
        attrs_node = self.g.get_node(node)
        attrs_clone = self.g.get_node(clone)
        assert(set(attrs_node.keys()) == set(attrs_clone.keys()))
        for k in attrs_node.keys():
            if (k != 'id') and (k != 'count'):
                for v in attrs_node[k]:
                    assert(v in attrs_clone[k])
        # Assert that the 2 nodes have the same successors
        succ_node = self.find_successors(node)
        succ_clone = self.find_successors(clone)
        assert(succ_node == succ_clone)
        # Assert that the 2 nodes have the same predecessors
        pred_node = self.find_predecessors(node)
        pred_clone = self.find_predecessors(clone)
        assert(pred_node == pred_clone)

    def test_merge_nodes(self):
        n1 = "c"
        attrs_n1 = self.g.get_node(n1)
        succ_n1 = self.find_successors(n1)
        pred_n1 = self.find_predecessors(n1)
        n2 = "j"
        attrs_n2 = self.g.get_node(n2)
        succ_n2 = self.find_successors(n2)
        pred_n2 = self.find_predecessors(n2)
        merged_node = "c_j"
        res = self.g.merge_nodes([n1, n2], merged_node)
        print('-----')
        print(res)
        print('-----')
        attrs_merged = self.g.get_node(merged_node)
        succ_merged = self.find_successors(merged_node)
        pred_merged = self.find_predecessors(merged_node)
        # Assert that the properties are correctly merged_id
        assert(set(attrs_merged.keys())
               == set(attrs_n1.keys()).union(set(attrs_n2.keys())))
        for k in attrs_n1.keys():
            if (k != 'id') and (k != 'count'):
                for v in attrs_n1[k]:
                    assert(v in attrs_merged[k])
        for k in attrs_n2.keys():
            if (k != 'id') and (k != 'count'):
                for v in attrs_n2[k]:
                    assert(v in attrs_merged[k])
        # Assert that the predecesors are correctly merged
        for pred1 in pred_n1:
            if (pred1 != n1) and (pred1 != n2):
                assert(pred1 in pred_merged)
            else:
                assert(merged_node in pred_merged)
        for pred2 in pred_n2:
            if (pred2 != n1) and (pred2 != n2):
                assert(pred2 in pred_merged)
            else:
                assert(merged_node in pred_merged)
        # Assert that the successors are correctly merged
        for suc1 in succ_n1:
            if (suc1 != n1) and (suc1 != n2):
                assert(suc1 in succ_merged)
            else:
                assert(merged_node in succ_merged)
        for suc2 in succ_n2:
            if (suc2 != n1) and (suc2 != n2):
                assert(suc2 in succ_merged)
            else:
                assert(merged_node in succ_merged)
        # Assert that the properties on the edges are merged correctly


t = TestGraphs()
t.test_merge_nodes()
