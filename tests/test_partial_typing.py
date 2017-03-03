"""Test of the hierarchy functionality with all typings being partial."""
import copy
import networkx as nx

from regraph.library.hierarchy import Hierarchy
from regraph.library.rules import Rule
from regraph.library.primitives import print_graph


class TestPartialTyping(object):
    """Implements unit testing of partial typing."""

    def __init__(self):
        """Initialize a test hierarchy."""
        self.hierarchy = Hierarchy()

        colors = nx.DiGraph()
        colors.add_nodes_from([
            "green", "red", "blue"
        ])
        colors.add_edges_from([
            ("red", "green"),
            ("red", "red"),
            ("green", "green"),
            ("blue", "red")
        ])
        self.hierarchy.add_graph("colors", colors, {"id": "https://some_url"})

        shapes = nx.DiGraph()
        shapes.add_nodes_from(["circle", "square"])
        shapes.add_edges_from([
            ("circle", "square"),
            ("square", "circle"),
            ("circle", "circle")
        ])
        self.hierarchy.add_graph("shapes", shapes)

        quality = nx.DiGraph()
        quality.add_nodes_from(["good", "bad"])
        quality.add_edges_from([
            ("bad", "bad"),
            ("bad", "good"),
            ("good", "good")
        ])
        self.hierarchy.add_graph("quality", quality)

        g1 = nx.DiGraph()
        g1.add_nodes_from([
            "red_circle",
            "red_square",
            "green_circle",
            "green_square",
            "some_circle",
        ])
        g1.add_edges_from([
            ("red_circle", "green_circle"),
            ("red_circle", "red_square"),
            ("red_circle", "red_circle"),
            ("red_square", "red_circle"),
            ("green_circle", "green_square"),
            ("green_square", "green_circle"),
            ("some_circle", "red_circle")
        ])
        g1_colors = {
            "red_circle": "red",
            "red_square": "red",
            "green_circle": "green",
            "green_square": "green"
        }
        g1_shapes = {
            "red_circle": "circle",
            "red_square": "square",
            "green_circle": "circle",
            "green_square": "square",
            "some_circle": "circle"
        }

        self.hierarchy.add_graph("g1", g1)
        self.hierarchy.add_typing("g1", "colors", g1_colors, total=False)
        self.hierarchy.add_typing("g1", "shapes", g1_shapes, total=True)

        g2 = nx.DiGraph()
        g2.add_nodes_from([
            "good_circle",
            "good_square",
            "bad_circle",
            "bad_square",
            "good_guy",
            "bad_guy",
            "some_node"
        ])
        g2.add_edges_from([
            ("good_circle", "good_square"),
            ("good_square", "good_circle"),
            ("bad_circle", "good_circle"),
            ("bad_square", "bad_circle"),
            ("bad_circle", "good_square"),
            ("bad_circle", "bad_circle"),
            ("bad_guy", "good_guy"),
            ("some_node", "good_circle"),
            ("bad_guy", "bad_square")
        ])
        g2_shapes = {
            "good_circle": "circle",
            "good_square": "square",
            "bad_circle": "circle",
            "bad_square": "square"
        }
        g2_quality = {
            "good_circle": "good",
            "good_square": "good",
            "bad_circle": "bad",
            "bad_square": "bad",
            "bad_guy": "bad",
            "good_guy": "good"
        }

        self.hierarchy.add_graph("g2", g2)
        self.hierarchy.add_typing("g2", "shapes", g2_shapes)
        self.hierarchy.add_typing("g2", "quality", g2_quality)

        assert(self.hierarchy.node_type("g2", "good_guy") == {"quality": "good"})
        self.hierarchy.add_node_type("g2", "good_guy", "shapes", "circle")
        assert(
            self.hierarchy.node_type("g2", "good_guy") ==
            {"quality": "good", "shapes": "circle"}
        )

        g3 = nx.DiGraph()
        g3.add_nodes_from([
            "good_red_circle",
            "bad_red_circle",
            "good_green_square",
            "bad_green_circle",
            "good_red_square",
            "some_circle_node",
            "some_strange_node"
        ])
        g3.add_edges_from([
            ("bad_red_circle", "good_red_circle"),
            ("bad_red_circle", "good_red_square"),
            ("bad_red_circle", "bad_green_circle"),
            ("bad_green_circle", "good_green_square"),
            ("good_red_square", "good_red_circle"),
            ("good_red_circle", "good_red_square")
        ])

        g3_g1 = {
            "good_red_circle": "red_circle",
            "bad_red_circle": "red_circle",
            "good_green_square": "green_square",
            "bad_green_circle": "green_circle",
            "good_red_square": "red_square",
            "some_circle_node": "some_circle"
        }

        g3_g2 = {
            "good_red_circle": "good_circle",
            "bad_red_circle": "bad_circle",
            "good_green_square": "good_square",
            "bad_green_circle": "bad_circle",
            "good_red_square": "good_square",
            "some_strange_node": "some_node"
        }

        self.hierarchy.add_graph("g3", g3)
        self.hierarchy.add_typing("g3", "g1", g3_g1)
        self.hierarchy.add_typing("g3", "g2", g3_g2)

        # add rule to the hierarchy
        lhs = nx.DiGraph()
        lhs.add_nodes_from([1, 2])
        lhs.add_edges_from([(1, 2)])

        p = nx.DiGraph()
        p.add_nodes_from([1, 11, 2])
        p.add_edges_from([(1, 2)])

        rhs = copy.deepcopy(p)

        p_lhs = {1: 1, 11: 1, 2: 2}
        p_rhs = {1: 1, 11: 11, 2: 2}

        r1 = Rule(p, lhs, rhs, p_lhs, p_rhs)
        self.hierarchy.add_rule(
            "r1", r1, {"desc": "Rule 1: typed by two graphs"}
        )

        lhs_typing1 = {1: "red_circle", 2: "red_square"}
        rhs_typing1 = {1: "red_circle", 11: "red_circle", 2: "red_square"}

        lhs_typing2 = {1: "good_circle", 2: "good_square"}
        rhs_typing2 = {1: "good_circle", 11: "good_circle", 2: "good_square"}

        self.hierarchy.add_rule_typing(
            "r1", "g1", lhs_typing1, rhs_typing1,
            lhs_total=True, rhs_total=True
        )
        self.hierarchy.add_rule_typing(
            "r1", "g2", lhs_typing2, rhs_typing2,
            lhs_total=True, rhs_total=True
        )

        print(self.hierarchy)

    def test_add_node_with_partial_types(self):
        new_graph = nx.DiGraph()
        new_graph.add_nodes_from([
            1, 2, 3, 4, 5
        ])
        new_graph.add_edges_from([
            (1, 2),
            (2, 3),
            (3, 4),
        ])

        new_graph_g3_typing = {
            1: "bad_red_circle",
            2: "bad_green_circle",
            3: "good_green_square",
            5: "some_strange_node"
        }
        self.hierarchy.add_graph("new_g", new_graph)
        self.hierarchy.add_typing(
            "new_g", "g3", new_graph_g3_typing, total=False
        )

        for node in self.hierarchy.node["new_g"].graph.nodes():
            print(node, self.hierarchy.node_type("new_g", node))
        # self.hierarchy.remove_graph("g3", reconnect=True)
        # for node in self.hierarchy.node["new_g"].graph.nodes():
        #     print(node, self.hierarchy.node_type("new_g", node))

        lhs = nx.DiGraph()
        lhs.add_nodes_from(["a", "b"])
        lhs.add_edges_from([
            ("a", "b"),
            ("b", "a")
        ])
        p = nx.DiGraph()
        p.add_nodes_from(["a", "a1", "b"])
        p.add_edges_from([
            ("a", "b"),
            ("a1", "b")
        ])
        rhs = copy.deepcopy(p)
        rule = Rule(
            p, lhs, rhs,
            {"a": "a", "a1": "a", "b": "b"},
            {"a": "a", "a1": "a1", "b": "b"},
        )

        instances = self.hierarchy.find_matching("shapes", lhs)
        self.hierarchy.rewrite(
            "shapes", rule, instances[0]
        )

        print("Shapes: ")
        print_graph(self.hierarchy.node["shapes"].graph)
        print()

        print("G1: ")
        print_graph(self.hierarchy.node["g1"].graph)
        print()

        print("G2: ")
        print_graph(self.hierarchy.node["g2"].graph)
        print()

        print("G3: ")
        print_graph(self.hierarchy.node["g3"].graph)
        print()

        print("RULE: ")
        print(self.hierarchy.node["r1"].rule)
        print_graph(self.hierarchy.node["r1"].rule.lhs)
        print_graph(self.hierarchy.node["r1"].rule.p)
        print_graph(self.hierarchy.node["r1"].rule.rhs)
        print()

        print("New graph: ")
        print_graph(self.hierarchy.node["new_g"].graph)

    def test_partially_typed_rule(self):
        lhs = nx.DiGraph()
        lhs.add_nodes_from([1, 2, 3])
        lhs.add_edges_from([(1, 2), (1, 3)])

        rule = Rule.from_transform(lhs)
        # rule.merge_nodes(2, 3)
        rule.clone_node(1)
        rule.add_node(4, {"a": {1}})

        lhs_typing = {
            "g1":
                {1: "red_circle"},
            "g2":
                {1: "bad_circle"}
        }
        instances = self.hierarchy.find_matching(
            "g3",
            rule.lhs,
            lhs_typing
        )
        print(instances[0])
        print("\nRewriting instance: ", instances[0])
        self.hierarchy.rewrite(
            "g3",
            rule,
            instances[0],
            lhs_typing
        )
        print_graph(self.hierarchy.node["g3"].graph)
        print(self.hierarchy.edge["g3"]["g1"].mapping)
        print(self.hierarchy.edge["g3"]["g2"].mapping)

    def test_apply_rule(self):
        instances = self.hierarchy.find_rule_matching("g3", "r1")
        self.hierarchy.apply_rule(
            "g3",
            "r1",
            instances[0]
        )
        