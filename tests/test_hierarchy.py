import copy

import networkx as nx

from regraph.library.data_structures import Hierarchy
from regraph.library.graphs import (TypedGraph,
                                    TypedDiGraph)


class TestHierarchy(object):
    def __init__(self):

        self.hierarchy = Hierarchy(directed=True)

        g0 = nx.DiGraph()
        g0.add_node("circle")
        g0.add_node("square")
        g0.add_node("triangle")

        g0.add_edges_from([
            ("circle", "circle"),
            ("circle", "square"),
            ("square", "circle"),
            ("square", "triangle")
        ])

        g1 = TypedDiGraph()
        g1.add_nodes_from([
            ("black_circle", "circle", {"a": {1, 2, 3}}),
            ("white_circle", "circle"),
            ("black_square", "square"),
            ("white_square", "square", {"a": {1}}),
            ("black_triangle", "triangle"),
            ("white_triangle", "triangle")
        ])

        g1.add_edges_from([
            ("black_circle", "black_circle", {"b": {1, 2, 3, 4}}),
            ("black_circle", "white_circle"),
            ("black_circle", "black_square"),
            ("white_circle", "black_circle"),
            ("white_circle", "white_square"),
            ("black_square", "black_circle"),
            ("black_square", "black_triangle"),
            ("black_square", "white_triangle"),
            ("white_square", "white_circle"),
            ("white_square", "black_triangle"),
            ("white_square", "white_triangle")
        ])

        g2 = TypedDiGraph()
        g2.add_nodes_from([
            (1, "black_circle", {"a": {1, 2}}),
            (2, "black_circle"),
            (3, "black_square"),
            (4, "white_circle"),
            (5, "white_square", {"a": {1}}),
            (6, "white_triangle"),
            (7, "black_triangle")
        ])

        g2.add_edges_from([
            (1, 2, {"b": {1, 2, 3}}),
            (2, 3),
            (3, 6),
            (3, 7),
            (4, 2),
            (4, 5),
            (5, 7)
        ])

        g3 = TypedDiGraph()
        g3.add_nodes_from([
            (1, "black_circle", {"a": {1, 2}}),
            (2, "white_circle"),
            (3, "white_circle"),
            (5, "black_square"),
            (4, "white_square", {"a": {1}}),
            (6, "white_triangle"),
            (7, "black_triangle")
        ])

        g3.add_edges_from([
            (1, 1, {"b": {1, 2, 3}}),
            (1, 2),
            (1, 3),
            (1, 5),
            (2, 1),
            (3, 1),
            (3, 4),
            (4, 7),
            (4, 6),
            (5, 6),
            (5, 7)
        ])

        g4 = nx.DiGraph()
        g4.add_nodes_from([1, 2, 3, 4, 5])
        g4.add_edges_from([
            (1, 1),
            (1, 2),
            (2, 1),
            (1, 3),
            (3, 1),
            (3, 4)
        ])

        self.hierarchy.add_graph("g0", g0)
        self.hierarchy.add_graph("g1", g1)
        self.hierarchy.add_graph("g2", g2)
        self.hierarchy.add_graph("g3", g3)
        self.hierarchy.add_graph("g4", g4)
        self.hierarchy.add_homomorphism("g1", "g0", typing=True, ignore_attrs=True)
        self.hierarchy.add_homomorphism("g2", "g1", typing=True)
        self.hierarchy.add_homomorphism("g3", "g1", typing=True)
        self.hierarchy.add_homomorphism(
            "g2", "g3",
            {1: 1, 2: 1, 3: 5, 4: 3, 5: 4, 6: 6, 7: 7}
        )
        self.hierarchy.add_homomorphism(
            "g4", "g3",
            {1: 1, 2: 3, 3: 3, 4: 4, 5: 5},
            ignore_types=True,
            ignore_attrs=True
        )
        g5 = TypedDiGraph()
        g5.add_nodes_from([
            (1, 'black_circle'),
            (2, 'white_circle'),
            (3, 'black_square'),
            (4, 'white_square'),
            (5, 'white_triangle'),
            (6, 'black_triangle'),
            (7, 'black_square')
        ])
        g5.add_edges_from([
            (1, 1),
            (1, 2),
            (1, 3),
            (1, 7),
            (2, 1),
            (2, 4),
            (3, 5),
            (3, 6),
            (4, 2),
            (4, 5),
            (4, 6),
            (7, 6)
        ])
        self.hierarchy.add_graph("g5", g5)
        self.hierarchy.add_homomorphism(
            "g3", "g5",
            {1: 1, 2: 2, 3: 2, 4: 4, 5: 3, 6: 5, 7: 6},
            ignore_attrs=True
        )

        g00 = nx.DiGraph()
        g00.add_nodes_from(['white', 'black'])
        g00.add_edges_from([
            ('white', 'white'),
            ('white', 'black'),
            ('black', 'black'),
            ('black', 'white')
        ])
        self.hierarchy.add_graph("g00", g00)
        self.hierarchy.add_homomorphism(
            "g1", "g00",
            {
                "black_square": "black",
                "black_circle": "black",
                "black_triangle": "black",
                "white_square": "white",
                "white_circle": "white",
                "white_triangle": "white"
            },
            ignore_types=True,
            ignore_attrs=True
        )

    def test_add_graph_with_types(self):
        assert("g5" in self.hierarchy.nodes())
        assert(("g3", "g5") in self.hierarchy.edges())
        assert(self.hierarchy.edge["g3"]["g5"].ignore_attrs is True)
        assert(self.hierarchy.edge["g3"]["g5"].ignore_types is False)

    def test_add_graph_with_attrs(self):
        g6 = nx.DiGraph()
        g6.add_nodes_from([
            (1, {"a": {1}}),
            2,
            3,
            4,
            (5, {"a": {1}}),
        ])

        g6.add_edges_from([
            (1, 2, {"b": {1}}),
            (2, 3),
            (4, 2),
            (4, 5)
        ])
        self.hierarchy.add_graph("g6", g6)
        self.hierarchy.add_homomorphism(
            "g6",
            "g2",
            {1: 1, 2: 2, 3: 3, 4: 4, 5: 5},
            ignore_types=True
        )
        assert("g6" in self.hierarchy.nodes())
        assert(("g6", "g2") in self.hierarchy.edges())
        assert(self.hierarchy.edge["g6"]["g2"].ignore_attrs is False)
        assert(self.hierarchy.edge["g6"]["g2"].ignore_types is True)

    def test_remove_graph(self):
        h = copy.deepcopy(self.hierarchy)
        h.remove_graph("g1", reconnect=True)
        print(h)
        print("G2", h.node["g2"])
        print("G3", h.node["g3"])
        print("G5", h.node["g5"])
