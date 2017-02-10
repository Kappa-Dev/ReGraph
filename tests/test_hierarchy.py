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
            ("black_circle", "circle"),
            ("white_circle", "circle"),
            ("black_square", "square"),
            ("white_square", "square"),
            ("black_triangle", "triangle"),
            ("white_triangle", "triangle")
        ])

        g1.add_edges_from([
            ("black_circle", "black_circle"),
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
            (1, "black_circle"),
            (2, "black_circle"),
            (3, "black_square"),
            (4, "white_circle"),
            (5, "white_square"),
            (6, "white_triangle"),
            (7, "black_triangle")
        ])

        g2.add_edges_from([
            (1, 2),
            (2, 3),
            (3, 6),
            (3, 7),
            (4, 2),
            (4, 5),
            (5, 7)
        ])

        g3 = TypedDiGraph()
        g3.add_nodes_from([
            (1, "black_circle"),
            (2, "white_circle"),
            (3, "white_circle"),
            (5, "black_square"),
            (4, "white_square"),
            (6, "white_triangle"),
            (7, "black_triangle")
        ])

        g3.add_edges_from([
            (1, 1),
            (1, 2),
            (1, 5),
            (2, 1),
            (3, 1),
            (3, 4),
            (4, 7),
            (4, 6),
            (5, 6),
            (5, 7)
        ])

        self.hierarchy.add_graph("g0", g0)
        self.hierarchy.add_graph("g1", g1)
        self.hierarchy.add_graph("g2", g2)
        self.hierarchy.add_graph("g3", g3)
        self.hierarchy.add_homomorphism("g1", "g0", typing=True)
        self.hierarchy.add_homomorphism("g2", "g1", typing=True)
        self.hierarchy.add_homomorphism("g3", "g1", typing=True)
        self.hierarchy.add_homomorphism(
            "g2", "g3",
            {1: 1, 2: 1, 3: 5, 4: 3, 5: 4, 6: 6, 7: 7}
        )

    def test_add_graph(self):
        pass
    #     g = TypedDiGraph()
    #     g.add_nodes_from([
    #         (1, 'a', {"a": {1}}),
    #         (2, 'b'),
    #         (3, 'c'),
    #         (4, 'c')
    #     ])
    #     self.hierarchy.add_graph("G3", g)
    #     assert("G3" in self.hierarchy.nodes())

    #     self.hierarchy.add_homomorphism(
    #         "G3", "G2", {1: 1, 2: 2, 3: 3, 4: 3}, ignore_attrs=True)
    #     assert(("G3", "G2") in self.hierarchy.edges())

    #     g.remove_node_attrs(1, {"a": {1}})
    #     self.hierarchy.add_graph("G4", g)
    #     self.hierarchy.add_homomorphism(
    #         "G4", "G2", {1: 1, 2: 2, 3: 3, 4: 3})

    #     g1 = TypedDiGraph()
    #     g1.add_nodes_from([
    #         (1, 'x'),
    #         (2, 'x'),
    #         (3, 'x')
    #     ])
    #     self.hierarchy.add_graph("G5", g1)
    #     self.hierarchy.add_homomorphism(
    #         "G5",
    #         "G1",
    #         {1: 1, 2: 1, 3: 1},
    #         ignore_types=True,
    #         ignore_attrs=True
    #     )

    # def test_remove_graph(self):
    #     h = copy.deepcopy(self.hierarchy)
    #     g1 = TypedDiGraph()
    #     g1.add_nodes_from([
    #         (1, 'x'),
    #         (2, 'x'),
    #         (3, 'x')
    #     ])
    #     h.add_graph("G6", g1)
    #     h.add_homomorphism(
    #         "G6",
    #         "G1",
    #         {1: 1, 2: 1, 3: 1},
    #         ignore_types=True,
    #         ignore_attrs=True
    #     )
    #     print(h)
    #     h.remove_graph("G1", reconnect=True)
    #     print(h)
