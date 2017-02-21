import copy

import networkx as nx

from regraph.library.rules import Rule
from regraph.library.hierarchy import Hierarchy
from nose.tools import raises
from regraph.library.primitives import print_graph
from regraph.library.utils import is_monic


class TestHierarchy(object):

    def __init__(self):
        self.hierarchy = Hierarchy(directed=True)

        g0 = nx.DiGraph()
        g0.add_node("circle"),  # , {"a": {1, 2, 3}})
        g0.add_node("square"),  # , {"a": {1}})
        g0.add_node("triangle")

        g0.add_edges_from([
            ("circle", "circle"),  # , {"b": {1, 2, 3, 4}}),
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
        self.hierarchy.add_typing(
            "g1", "g0",
            {"black_circle": "circle",
             "white_circle": "circle",
             "black_square": "square",
             "white_square": "square",
             "black_triangle": "triangle",
             "white_triangle": "triangle"},
            ignore_attrs=True
        )

        self.hierarchy.add_typing(
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
        self.hierarchy.add_typing(
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
        self.hierarchy.add_typing(
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

        g4 = nx.DiGraph()
        g4.add_nodes_from([1, 2, 3])
        g4.add_edges_from([
            (1, 2),
            (2, 3)
        ])

        self.hierarchy.add_graph("g4", g4)
        self.hierarchy.add_typing("g4", "g2", {1: 2, 2: 3, 3: 6})
        self.hierarchy.add_typing("g4", "g3", {1: 1, 2: 5, 3: 6})

        g5 = nx.DiGraph()
        g5.add_nodes_from([
            ("black_circle", {"a": {255}}),
            ("black_square", {"a": {256}}),
            ("white_triangle", {"a": {257}}),
            ("star", {"a": {258}})
        ])
        g5.add_edges_from([
            ("black_circle", "black_square"),
            ("black_square", "white_triangle", {"b": {11}}),
            ("star", "black_square"),
            ("star", "white_triangle")
        ])

        self.hierarchy.add_graph("g5", g5)

    def test_add_graph(self):
        return

    @raises(ValueError)
    def test_add_typing_cycle(self):
        self.hierarchy.add_typing(
            "g0", "g1",
            {"circle": "black_circle",
             "square": "white_square",
             "triangle": "black_triangle"},
            ignore_attrs=True)

    def test_remove_graph(self):
        h = copy.deepcopy(self.hierarchy)
        h.remove_graph("g1", reconnect=True)
        # print(h)
        # print(self.hierarchy)

    def test_find_matching(self):
        pattern = nx.DiGraph()
        pattern.add_nodes_from([
            1,
            (2, {"a": 1}),
            3
        ])
        pattern.add_edges_from([
            (1, 2),
            (2, 3)
        ])
        pattern_typing = {1: "circle", 2: "square", 3: "triangle"}

        instances = self.hierarchy.find_matching(
            graph_id="g1",
            pattern=pattern,
            pattern_typing={
                "g0": pattern_typing,
                "g00": {1: "white", 2: "white", 3: "black"}
            }
        )
        assert(len(instances) == 4)

    def test_rewrite(self):
        pattern = nx.DiGraph()
        pattern.add_nodes_from([
            1,
            (2, {"a": {1, 2}}),
            3
        ])
        pattern.add_edges_from([
            (1, 2),
            (2, 3)
        ])
        lhs_typing = {1: "circle", 2: "square", 3: "triangle"}

        p = nx.DiGraph()
        p.add_nodes_from([
            1,
            2,
            3
        ])
        p.add_edges_from([
            (2, 3)
        ])

        rhs = nx.DiGraph()
        rhs.add_nodes_from([
            1,
            (2, {"a": {3, 5}}),
            (3, {"new_attrs": {1}}),
            4
        ])
        rhs.add_edges_from([
            (1, 4, {"new_attrs": {2}}),
            (2, 4, {"new_attrs": {3}}),
            (2, 3, {"new_attrs": {4}})
        ])
        p_lhs = {1: 1, 2: 2, 3: 3}
        p_rhs = {1: 1, 2: 2, 3: 3}

        rule = Rule(p, pattern, rhs, p_lhs, p_rhs)
        rhs_typing = {
            1: "circle",
            2: "sqaure",
            3: "triangle",
            4: "triangle"
        }

        instances = self.hierarchy.find_matching(
            "g1",
            pattern,
            {
                "g0": lhs_typing,
                "g00": {1: 'white', 2: 'white', 3: 'black'}
            }
        )
        # print(instances[0])
        self.hierarchy.rewrite(
            "g1",
            instances[0],
            rule,
            lhs_typing,
            rhs_typing
        )
        print_graph(self.hierarchy.node["g1"])
        print_graph(self.hierarchy.node["g2"])
        print_graph(self.hierarchy.node["g3"])
        # add nice assertions here

    def test_node_type(self):
        assert(set(self.hierarchy.node_type("g1", "white_circle")) == set(["white", "circle"]))
        assert(set(self.hierarchy.node_type("g1", "black_square")) == set(["black", "square"]))

    def test_add_partial_typing(self):
        self.hierarchy.add_partial_typing(
            "g5",
            "g1",
            {"black_circle": "black_circle",
             "black_square": "black_square",
             "white_triangle": "white_triangle"},
            ignore_attrs=True
        )
        assert("g5_g1" in self.hierarchy.nodes())
        assert(("g5_g1", "g5") in self.hierarchy.edges())
        assert(("g5_g1", "g1") in self.hierarchy.edges())
        assert(is_monic(self.hierarchy.edge["g5_g1"]["g5"][0]))
        print_graph(self.hierarchy.node["g5_g1"])

    def test_rewrite_ignore_attrs(self):
        pass