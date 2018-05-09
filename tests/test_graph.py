"""Collection of tests for ReGraph_neo4j graphs."""

from regraph.neo4j.graphs import *


class TestGraphs(object):

    def __init__(self):
        self.g = Neo4jGraph(
              uri="bolt://localhost:7687", user="neo4j", password="admin")
        res = self.g.clear()
        nodes = [
            ("a", {"name": "Jack", "age": 23, "hobby": {"hiking", "music"},
                   "weight": 75}),
            ("b", {"name": "Bob", "age": 24, "hobby": {"sport", "music"},
                   "height": 178}),
            "c",
            ("d", {"name": "Paul"}), "e", "f"
            ]
        edges = [
            ("a", "b", {"type": {"friends", "colleagues"}}),
            ("d", "b", {"type": "enemies"}),
            ("a", "c"),
            ("d", "a", {"type": "friends"}),
            ("e", "a"),
            ("f", "d")
            ]
        self.g.add_nodes_from(nodes)
        self.g.add_edges_from(edges)

    def test_add_node(self):
        """Test add_node() method."""
        attrs = {"name": "Roberto"}
        self.g.add_node("x", attrs)
        query = get_node("x")
        print(query)
        result = self.g.execute(query)
        try:
            res_node = dict(result.value()[0])
        except(ValueError):
            res_node = dict(result.value())
        assert(len(res_node)!=0)
        for k in attrs.keys():
            for v in attrs[k]:
                assert(v in res_node[k])




#t = TestGraphs()
#t.test_add_node()
