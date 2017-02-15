import copy

import networkx as nx

from regraph.library.hierarchy import Hierarchy
from nose.tools import raises


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
        self.hierarchy.add_graph("g0", g0)

        g00 = nx.DiGraph()
        g00.add_nodes_from(['white', 'black'])
        g00.add_edges_from([
            ('white', 'white'),
            ('white', 'black'),
            ('black', 'black'),
            ('black', 'white')
        ])
        self.hierarchy.add_graph("g00", g00)

        g1 = nx.DiGraph()
        g1.add_nodes_from([
            ("black_circle", {"a": {1, 2, 3}}),
            "white_circle",
            "black_square",
            ("white_square", {"a": {1}}),
            "black_triangle",
            "white_triangle"
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

        self.hierarchy.add_graph("g1", g1)
        self.hierarchy.add_homomorphism(
            "g1", "g0",
            {"black_circle": "circle",
             "white_circle": "circle",
             "black_square": "square",
             "white_square": "square",
             "black_triangle": "triangle",
             "white_triangle": "triangle"},
            ignore_attrs=True
        )

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
            ignore_attrs=True
        )

        g2 = nx.DiGraph()
        g2.add_nodes_from([
            (1, {"a": {1, 2}}),
            2,
            3,
            4,
            (5, {"a": {1}}),
            6,
            7,
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
        self.hierarchy.add_graph("g2", g2)
        self.hierarchy.add_homomorphism(
            "g2", "g1",
            {1: "black_circle",
             2: "black_circle",
             3: "black_square",
             4: "white_circle",
             5: "white_square",
             6: "white_triangle",
             7: "black_triangle"},
            ignore_attrs=False
        )

        g3 = nx.DiGraph()
        g3.add_nodes_from([
            (1, {"a": {1, 2}}),
            2,
            3,
            5,
            (4, {"a": {1}}),
            6,
            7,
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
        self.hierarchy.add_graph("g3", g3)
        self.hierarchy.add_homomorphism(
            "g3", "g1",
            {1: "black_circle",
             2: "white_circle",
             3: "white_circle",
             5: "black_square",
             4: "white_square",
             6: "white_triangle",
             7: "black_triangle"},
            ignore_attrs=False
        )

        # g4 = nx.DiGraph()
        # g4.add_nodes_from([1, 2, 3, 4, 5])
        # g4.add_edges_from([
        #     (1, 1),
        #     (1, 2),
        #     (2, 1),
        #     (1, 3),
        #     (3, 1),
        #     (3, 4)
        # ])

        # self.hierarchy.add_graph("g0", g0)
        # self.hierarchy.add_graph("g1", g1)
        # self.hierarchy.add_graph("g2", g2)
        # self.hierarchy.add_graph("g3", g3)
        # self.hierarchy.add_graph("g4", g4)
        # self.hierarchy.add_homomorphism("g1", "g0", typing=True, ignore_attrs=True)
        # self.hierarchy.add_homomorphism("g2", "g1", typing=True)
        # self.hierarchy.add_homomorphism("g3", "g1", typing=True)
        # self.hierarchy.add_homomorphism(
        #     "g2", "g3",
        #     {1: 1, 2: 1, 3: 5, 4: 3, 5: 4, 6: 6, 7: 7}
        # )
        # self.hierarchy.add_homomorphism(
        #     "g4", "g3",
        #     {1: 1, 2: 3, 3: 3, 4: 4, 5: 5},
        #     ignore_types=True,
        #     ignore_attrs=True
        # )
        # g5 = TypedDiGraph()
        # g5.add_nodes_from([
        #     (1, 'black_circle'),
        #     (2, 'white_circle'),
        #     (3, 'black_square'),
        #     (4, 'white_square'),
        #     (5, 'white_triangle'),
        #     (6, 'black_triangle'),
        #     (7, 'black_square')
        # ])
        # g5.add_edges_from([
        #     (1, 1),
        #     (1, 2),
        #     (1, 3),
        #     (1, 7),
        #     (2, 1),
        #     (2, 4),
        #     (3, 5),
        #     (3, 6),
        #     (4, 2),
        #     (4, 5),
        #     (4, 6),
        #     (7, 6)
        # ])
        # self.hierarchy.add_graph("g5", g5)
        # self.hierarchy.add_homomorphism(
        #     "g3", "g5",
        #     {1: 1, 2: 2, 3: 2, 4: 4, 5: 3, 6: 5, 7: 6},
        #     ignore_attrs=True
        # )

    def test_add_graph(self):
        g4 = nx.DiGraph()
        g4.add_nodes_from([1, 2, 3])
        g4.add_edges_from([
            (1, 2),
            (2, 3)
        ])

        self.hierarchy.add_graph("g4", g4)
        self.hierarchy.add_homomorphism("g4", "g2", {1: 2, 2: 3, 3: 6})
        self.hierarchy.add_homomorphism("g4", "g3", {1: 1, 2: 5, 3: 6})
        return

    @raises(ValueError)
    def test_add_homomorphism_cycle(self):
        self.hierarchy.add_homomorphism(
            "g0", "g1",
            {"circle": "black_circle",
             "square": "white_square",
             "triangle": "black_triangle"},
            ignore_attrs=True)

    def test_remove_graph(self):
        h = copy.deepcopy(self.hierarchy)
        h.remove_graph("g1", reconnect=True)
        print(h)
        print(self.hierarchy)
