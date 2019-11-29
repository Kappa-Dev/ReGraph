"""."""
import copy

import networkx as nx

from nose.tools import raises

from regraph import Rule
from regraph.graphs import NXGraph
from regraph.hierarchies import NXHierarchy
from regraph import (HierarchyError)
import regraph.primitives as prim


class TestHierarchy(object):

    def __init__(self):
        self.hierarchy = NXHierarchy()

        g0 = NXGraph()
        g0.add_node("circle", {"a": {1, 2, 3}})
        g0.add_node("square", {"a": {1, 2, 3, 5}})
        g0.add_node("triangle", {"new_attrs": {1}})
        g0.add_edges_from([
            ("circle", "circle"),  # , {"b": {1, 2, 3, 4}}),
            ("circle", "square"),
            ("square", "circle", {"new_attrs": {2}}),
            ("square", "triangle", {"new_attrs": {3, 4}})
        ])
        self.hierarchy.add_graph("g0", g0, {"name": "Shapes"})

        g00 = NXGraph()
        g00.add_node('black', {"a": {1, 2, 3}, "new_attrs": {1}})
        g00.add_node('white', {"a": {1, 2, 3, 5}})
        g00.add_edges_from([
            ('white', 'white', {"new_attrs": 2}),
            ('white', 'black', {"new_attrs": {4, 3}}),
            ('black', 'black'),
            ('black', 'white')
        ])
        self.hierarchy.add_graph("g00", g00, {"name": "Colors"})

        g1 = NXGraph()
        g1.add_nodes_from([
            ("black_circle", {"a": {1, 2, 3}}),
            "white_circle",
            "black_square",
            ("white_square", {"a": {1, 2}}),
            "black_triangle",
            "white_triangle"
        ])

        g1.add_edges_from([
            ("black_circle", "black_circle"),  # {"b": {1, 2, 3, 4}}),
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
             "white_triangle": "triangle"}
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
            }
        )

        g2 = NXGraph()
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
            (1, 2),  # {"b": {1, 2, 3}}),
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
             7: "black_triangle"}
        )

        g3 = NXGraph()
        g3.add_nodes_from([
            (1),  # {"a": {1, 2}}),
            2,
            3,
            5,
            (4),  # {"a": {1}}),
            6,
            7,
        ])

        g3.add_edges_from([
            (1, 1),  # , {"b": {1, 2, 3}}),
            (1, 2),
            (1, 3),
            (1, 5),
            (2, 1),
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
             7: "black_triangle"}
        )

        g4 = NXGraph()
        prim.add_nodes_from(g4, [1, 2, 3])
        g4.add_edges_from([
            (1, 2),
            (2, 3)
        ])

        self.hierarchy.add_graph("g4", g4)
        self.hierarchy.add_typing("g4", "g2", {1: 2, 2: 3, 3: 6})
        self.hierarchy.add_typing("g4", "g3", {1: 1, 2: 5, 3: 6})

        g5 = NXGraph()
        g5.add_nodes_from([
            ("black_circle"),  # {"a": {255}}),
            ("black_square"),  # {"a": {256}}),
            ("white_triangle"),  # {"a": {257}}),
            ("star")  # , {"a": {258}})
        ])
        g5.add_edges_from([
            ("black_circle", "black_square"),
            ("black_square", "white_triangle"),  # , {"b": {11}}),
            ("star", "black_square"),
            ("star", "white_triangle")
        ])

        self.hierarchy.add_graph("g5", g5)

    def test_add_graph(self):
        # add nice assertions here!
        return

    @raises(HierarchyError)
    def test_add_typing_cycle(self):
        self.hierarchy.add_typing(
            "g0", "g1",
            {"circle": "black_circle",
             "square": "white_square",
             "triangle": "black_triangle"})

    def test_remove_graph(self):
        h = copy.deepcopy(self.hierarchy)
        h.remove_node("g1", reconnect=True)
        # print(h)
        # print(self.hierarchy.get_typing("g2", "g0"))

    def test_find_matching(self):
        pattern = NXGraph()
        pattern.add_nodes_from([
            1,
            (2, {"a": 1}),
            3
        ])
        pattern.add_edges_from([
            (1, 2),
            (2, 3)
        ])
        pattern_typing = {
            1: "circle",
            2: "square",
            3: "triangle"}

        instances = self.hierarchy.find_matching(
            graph_id="g1",
            pattern=pattern,
            pattern_typing={
                "g0": pattern_typing,
                "g00": {1: "white", 2: "white", 3: "black"}
            }
        )
        assert(len(instances) == 1)

    def test_rewrite(self):
        pattern = NXGraph()
        pattern.add_nodes_from([
            1,
            (2, {"a": {1, 2}}),
            3
        ])
        pattern.add_edges_from([
            (1, 2),
            (2, 3)
        ])
        lhs_typing = {
            "g0": {1: "circle", 2: "square", 3: "triangle"},
            "g00": {1: "white", 2: "white", 3: "black"}
        }

        p = NXGraph()
        p.add_nodes_from([
            1,
            2,
            3
        ])
        p.add_edges_from([
            (2, 3)
        ])

        rhs = NXGraph()
        rhs.add_nodes_from([
            1,
            (2, {"a": {3, 5}}),
            (3, {"new_attrs": {1}}),
            4
        ])
        rhs.add_edges_from([
            (2, 1, {"new_attrs": {2}}),
            (2, 4, {"new_attrs": {3}}),
            (2, 3, {"new_attrs": {4}})
        ])
        p_lhs = {1: 1, 2: 2, 3: 3}
        p_rhs = {1: 1, 2: 2, 3: 3}

        rule = Rule(p, pattern, rhs, p_lhs, p_rhs)
        rhs_typing = {
            "g0": {
                1: "circle",
                2: "square",
                3: "triangle",
                4: "triangle"
            },
            "g00": {
                1: "white",
                2: "white",
                3: "black",
                4: "black"
            }
        }

        instances = self.hierarchy.find_matching(
            "g1",
            pattern,
            pattern_typing=lhs_typing
        )

        old_g0_nodes = self.hierarchy.get_graph("g0").nodes(True)
        old_g0_edges = self.hierarchy.get_graph("g0").edges(True)
        old_g00_nodes = self.hierarchy.get_graph("g00").nodes(True)
        old_g00_edges = self.hierarchy.get_graph("g00").edges(True)
        self.hierarchy.rewrite(
            "g1",
            rule,
            instances[0],
            rhs_typing=rhs_typing
        )
        # Test that no propagation forward happened
        assert(old_g0_nodes == self.hierarchy.get_graph("g0").nodes(True))
        assert(old_g0_edges == self.hierarchy.get_graph("g0").edges(True))
        assert(old_g00_nodes == self.hierarchy.get_graph("g00").nodes(True))
        assert(old_g00_edges == self.hierarchy.get_graph("g00").edges(True))

    def test_node_type(self):
        # print(self.hierarchy.node_type("g1", "white_circle"))
        assert(
            self.hierarchy.node_type("g1", "white_circle") ==
            {"g00": "white", "g0": "circle"}
        )
        # print(self.hierarchy.node_type("g1", "black_square"))
        assert(
            self.hierarchy.node_type("g1", "black_square") ==
            {"g00": "black", "g0": "square"}
        )


    def test_to_json(self):
        res = self.hierarchy.to_json()
        new_h = NXHierarchy.from_json(res)
        assert(self.hierarchy == new_h)

    def test_add_rule(self):
        lhs = NXGraph()
        lhs.add_nodes_from([
            1, 2, 3
        ])
        lhs.add_edges_from([
            (1, 2),
            (2, 1),
            (2, 3)
        ])

        p = NXGraph()
        p.add_nodes_from([
            1, 2, 3, 31
        ])
        p.add_edges_from([
            (1, 2),
            (2, 3),
            (2, 31)
        ])

        rhs = NXGraph()
        rhs.add_nodes_from([
            1, 2, 3, 31, 4
        ])
        rhs.add_edges_from([
            (1, 2),
            (4, 2),
            (2, 3),
            (2, 31)
        ])

        p_lhs = {1: 1, 2: 2, 3: 3, 31: 3}
        p_rhs = {1: 1, 2: 2, 3: 3, 31: 3}

        rule = Rule(p, lhs, rhs, p_lhs, p_rhs)

        lhs_typing = {
            1: "black_circle",
            2: "white_circle",
            3: "white_square"
        }
        rhs_typing = {
            1: "black_circle",
            2: "white_circle",
            3: "white_square",
            31: "white_square",
            4: "black_circle"
        }
        self.hierarchy.add_rule("r1", rule, {"name": "First rule"})
        self.hierarchy.add_rule_typing("r1", "g1", lhs_typing, rhs_typing)

        pattern = NXGraph()
        pattern.add_nodes_from([
            1,
            (2, {"a": {1, 2}}),
            3
        ])
        pattern.add_edges_from([
            (1, 2),
            (2, 3)
        ])
        lhs_typing = {
            "g0": {1: "circle", 2: "square", 3: "triangle"},
            "g00": {1: 'white', 2: 'white', 3: 'black'}
        }

        p = NXGraph()
        p.add_nodes_from([
            1,
            11,
            2,
            3
        ])
        p.add_edges_from([
            (2, 3)
        ])

        rhs = NXGraph()
        rhs.add_nodes_from([
            1,
            11,
            (2, {"a": {3, 5}}),
            (3, {"new_attrs": {1}}),
        ])
        rhs.add_edges_from([
            (2, 3, {"new_attrs": {4}})
        ])
        p_lhs = {1: 1, 11: 1, 2: 2, 3: 3}
        p_rhs = {1: 1, 11: 11, 2: 2, 3: 3}

        rule = Rule(p, pattern, rhs, p_lhs, p_rhs)
        rhs_typing = {
            "g0": {
                1: "circle",
                11: "circle",
                2: "square",
                3: "triangle"
            },
            "g00": {
                1: "white",
                11: "white",
                2: "white",
                3: "black"
            }
        }

        instances = self.hierarchy.find_matching(
            "g1", pattern, lhs_typing)

        self.hierarchy.rewrite(
            "g1", rule, instances[0], rhs_typing=rhs_typing)
        # print(self.hierarchy.get_rule("r1"))

    def test_add_rule_multiple_typing(self):

        lhs = NXGraph()
        lhs.add_nodes_from([1, 2, 3, 4])
        lhs.add_edges_from([
            (1, 3),
            (2, 3),
            (4, 3)
        ])

        p = NXGraph()
        p.add_nodes_from([1, 3, 31, 4])
        p.add_edges_from([
            (1, 3),
            (1, 31),
            (4, 3),
            (4, 31)
        ])

        rhs = copy.deepcopy(p)

        p_lhs = {1: 1, 3: 3, 31: 3, 4: 4}
        p_rhs = {1: 1, 3: 3, 31: 31, 4: 4}

        lhs_typing_g2 = {
            1: 1,
            2: 1,
            3: 2,
            4: 4
        }

        rhs_typing_g2 = {
            1: 1,
            3: 2,
            31: 2,
            4: 4
        }

        lhs_typing_g3 = {
            1: 1,
            2: 1,
            3: 1,
            4: 2
        }

        rhs_typing_g3 = {
            1: 1,
            3: 1,
            31: 1,
            4: 2
        }

        rule = Rule(p, lhs, rhs, p_lhs, p_rhs)
        self.hierarchy.add_rule(
            "r2", rule, {"name": "Second rule: with multiple typing"})
        self.hierarchy.add_rule_typing(
            "r2", "g2", lhs_typing_g2, rhs_typing_g2)
        self.hierarchy.add_rule_typing(
            "r2", "g3", lhs_typing_g3, rhs_typing_g3)

        pattern = NXGraph()
        pattern.add_nodes_from([
            1,
            2
        ])
        pattern.add_edges_from([
            (2, 1)
        ])
        lhs_typing = {
            "g0": {1: "circle", 2: "circle"},
            "g00": {1: "black", 2: "white"}
        }

        p = NXGraph()
        p.add_nodes_from([
            1,
            2,
            21
        ])
        p.add_edges_from([
            (21, 1)
        ])

        rhs = copy.deepcopy(p)

        p_lhs = {1: 1, 2: 2, 21: 2}
        p_rhs = {1: 1, 2: 2, 21: 21}

        rule = Rule(p, pattern, rhs, p_lhs, p_rhs)
        rhs_typing = {
            "g0": ({
                1: "circle",
                2: "circle",
                21: "circle",
            }),
            "g00": ({
                1: "black",
                2: "white",
                21: "white"
            })
        }

        instances = self.hierarchy.find_matching(
            "g1",
            pattern,
            lhs_typing
        )

        self.hierarchy.rewrite(
            "g1",
            rule,
            instances[0],
            rhs_typing=rhs_typing
        )

    def test_get_descendants(self):
        desc = self.hierarchy.get_descendants("g2")
        assert("g1" in desc.keys())
        assert("g0" in desc.keys())
        assert("g00" in desc.keys())

    def test_get_ancestors(self):
        anc = self.hierarchy.get_ancestors("g0")
        assert("g1" in anc.keys())
        assert("g2" in anc.keys())
        assert("g3" in anc.keys())
        assert("g4" in anc.keys())

    @raises(HierarchyError)
    def test_add_typing_advanced(self):
        hierarchy = NXHierarchy()

        g9 = NXGraph()
        g9.add_nodes_from(["a", "b"])
        hierarchy.add_graph(9, g9)

        g8 = NXGraph()
        g8.add_nodes_from(["1_a", "1_b", "2_a", "2_b"])
        hierarchy.add_graph(8, g8)

        hierarchy.add_typing(
            8, 9,
            {"1_a": "a",
             "1_b": "b",
             "2_a": "a",
             "2_b": "b"},
        )

        g7 = NXGraph()
        g7.add_nodes_from(["x_a", "x_b", "y_a", "y_b"])
        hierarchy.add_graph(7, g7)

        hierarchy.add_typing(
            7, 9,
            {
                "x_a": "a",
                "x_b": "b",
                "y_a": "a",
                "y_b": "b"
            },
        )

        g2 = NXGraph()
        g2.add_nodes_from(["s_1_a", "t_1_a", "s_1_b", "t_2_a"])
        hierarchy.add_graph(2, g2)

        hierarchy.add_typing(
            2, 8,
            {
                "s_1_a": "1_a",
                "t_1_a": "1_a",
                "s_1_b": "1_b",
                "t_2_a": "2_a"
            })

        g3 = NXGraph()
        g3.add_nodes_from(["s_x_a", "t_x_a", "g_y_b"])
        hierarchy.add_graph(3, g3)

        hierarchy.add_typing(
            3, 7,
            {
                "s_x_a": "x_a",
                "t_x_a": "x_a",
                "g_y_b": "y_b"
            })

        g4 = NXGraph()
        g4.add_nodes_from(["a_x_a", "t_y_b"])
        hierarchy.add_graph(4, g4)

        hierarchy.add_typing(
            4, 3,
            {
                "a_x_a": "s_x_a",
                "t_y_b": "g_y_b"
            })

        hierarchy.add_typing(
            4, 7,
            {
                "a_x_a": "x_a",
                "t_y_b": "y_b"
            })

        g6 = NXGraph()
        g6.add_nodes_from(["a_x_a", "b_x_a", "a_y_b", "b_y_a", "c_x_b"])
        hierarchy.add_graph(6, g6)

        hierarchy.add_typing(
            6, 7,
            {
                "a_x_a": "x_a",
                "b_x_a": "x_a",
                "a_y_b": "y_b",
                "b_y_a": "y_a",
                "c_x_b": "x_b"
            })

        g5 = NXGraph()
        g5.add_nodes_from(["1_a_x_a", "2_a_x_a", "1_a_y_b"])
        hierarchy.add_graph(5, g5)

        hierarchy.add_typing(
            5, 6,
            {
                "1_a_x_a": "a_x_a",
                "2_a_x_a": "a_x_a",
                "1_a_y_b": "a_y_b"
            })

        hierarchy.add_typing(
            5, 4,
            {
                "1_a_x_a": "a_x_a",
                "2_a_x_a": "a_x_a",
                "1_a_y_b": "t_y_b"
            })

        g1 = NXGraph()
        g1.add_nodes_from(["1_s_1_a", "2_s_1_a", "1_s_1_b"])
        hierarchy.add_graph(1, g1)

        hierarchy.add_typing(
            1, 2,
            {
                "1_s_1_a": "s_1_a",
                "2_s_1_a": "s_1_a",
                "1_s_1_b": "s_1_b"
            })

        hierarchy.add_typing(
            1, 3,
            {
                "1_s_1_a": "s_x_a",
                "2_s_1_a": "t_x_a",
                "1_s_1_b": "g_y_b"
            })
        # start testing
        hierarchy.add_typing(
            3, 8,
            {
                "s_x_a": "1_a",
                "t_x_a": "1_a",
                "g_y_b": "1_b"
            })
        hierarchy.add_typing(
            6, 9,
            {
                "a_x_a": "a",
                "b_x_a": "b",
                "a_y_b": "b",
                "b_y_a": "a",
                "c_x_b": "b"
            })

    @staticmethod
    def _generate_triangle_hierarchy():
        h = NXHierarchy()

        g1 = NXGraph()
        g1.add_nodes_from([
            "1", "2"
        ])

        g2 = NXGraph()
        g2.add_nodes_from([
            "1a", "1b", "2a", "2b"
        ])

        g3 = NXGraph()
        g3.add_nodes_from([
            "1x", "1y", "2x", "2y"
        ])

        h.add_graph("g1", g1)
        h.add_graph("g2", g2)
        h.add_graph("g3", g3)
        h.add_typing(
            "g2", "g1",
            {
                "1a": "1",
                "1b": "1",
                "2a": "2",
                "2b": "2"
            })
        h.add_typing(
            "g3", "g1",
            {
                "1x": "1",
                "1y": "1",
                "2x": "2",
                "2y": "2"
            })
        h.add_typing(
            "g2", "g3",
            {
                "1a": "1x",
                "1b": "1y",
                "2a": "2y",
                "2b": "2x"
            })
        return h

    def test_triangle_1(self):
        h = self._generate_triangle_hierarchy()

        pattern = NXGraph()
        pattern.add_nodes_from([
            1, 2
        ])
        rule = Rule.from_transform(pattern)
        rule.inject_remove_node(1)
        rule.inject_clone_node(2)

        instances = h.find_matching("g1", pattern)
        h.rewrite("g1", rule, instances[0])

        # print(new_h)
        # print_graph(new_h.node["g2"].graph)
        # print_graph(new_h.node["g3"].graph)
        # print(new_h.edge["g2"]["g3"].mapping)

    def test_controlled_forward(self):
        h = self._generate_triangle_hierarchy()
        pattern = NXGraph()
        pattern.add_nodes_from([
            "1a"
        ])
        rule = Rule.from_transform(pattern)
        rule.inject_add_node("1c")

        rhs_typing = {
            "g3": {"1c": "1x"}
        }

        old_g3_nodes = h.get_graph("g3").nodes(True)
        old_g1_nodes = h.get_graph("g1").nodes(True)

        h.rewrite("g2", rule, {"1a": "1a"}, rhs_typing=rhs_typing)

        assert(old_g3_nodes == h.get_graph("g3").nodes(True))
        assert(old_g1_nodes == h.get_graph("g1").nodes(True))

        rhs_typing = {
            "g1": {"1c": "1"}
        }

        h.rewrite("g2", rule, {"1a": "1a"}, rhs_typing=rhs_typing)
        assert(old_g1_nodes == h.get_graph("g1").nodes(True))
        assert(len(old_g3_nodes) + 1 == len(h.get_graph("g3").nodes()))


    def test_controlled_backward(self):
        h = self._generate_triangle_hierarchy()
        pattern = NXGraph()
        pattern.add_nodes_from([
            "1"
        ])
        rule = Rule.from_transform(pattern)
        rule.inject_clone_node("1", "11")

        p_typing = {
            "g2": {"1a": {"1"}, "1b": {"11"}},
        }

        old_g3_nodes = h.get_graph("g3").nodes(True)
        old_g2_nodes = h.get_graph("g2").nodes(True)

        h.rewrite("g1", rule, {"1": "1"}, p_typing=p_typing)

        # assert(old_g3_nodes == h.get_graph("g3").nodes(True))
        assert(old_g2_nodes == h.get_graph("g2").nodes(True))
    
        # print(h.get_graph("g3").nodes())
        # print(h.get_typing("g2", "g3"))







