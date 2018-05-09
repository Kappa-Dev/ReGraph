"""Collection of tests for ReGraph_neo4j graphs."""

from regraph.neo4j.graphs import *


class TestGraphs(object):

    def __init__(self):
        g = Neo4jGraph(
              uri="bolt://localhost:7687", user="neo4j", password="admin")
        res = g.clear()
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
        g.add_nodes_from(nodes)
        g.add_edges_from(edges)


t = TestGraphs()
