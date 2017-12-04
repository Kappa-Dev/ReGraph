"""Test of the hierarchy functionality with all typings being partial."""
import copy
import networkx as nx

from regraph.hierarchy import Hierarchy
from regraph.rules import Rule
from regraph.exceptions import RewritingError
from regraph import primitives


class TestPropagation(object):

    def __init__(self):
        hierarchy = Hierarchy()
        hierarchy = Hierarchy()
        colors = nx.DiGraph()
        primitives.add_nodes_from(
            colors,
            [("red", {"r": 255, "g": 0, "b": 0}),
             ("blue", {"r": 0, "g": 0, "b": 255})]
        )
        primitives.add_edges_from(
            colors,
            [("red", "red"), ("blue", "red"), ("red", "blue")]
        )
        hierarchy.add_graph("colors", colors)

        mmm = nx.DiGraph()
        primitives.add_nodes_from(
            mmm,
            ["component", "state", "action"]
        )

        primitives.add_edges_from(
            mmm,
            [("component", "action"),
             ("component", "component"),
             ("state", "component"),
             ("action", "state")]
        )

        hierarchy.add_graph("mmm", mmm)

        mm = nx.DiGraph()
        primitives.add_nodes_from(
            mm,
            ["gene", "residue", "state", "mod"]
        )
        primitives.add_edges_from(
            mm,
            [("residue", "gene"),
             ("state", "gene"),
             ("state", "residue"),
             ("mod", "state"),
             ("gene", "mod")]
        )
        hierarchy.add_graph("mm", mm)

        action_graph = nx.DiGraph()
        primitives.add_nodes_from(
            action_graph,
            ["A", "A_res_1", "p_a", "B", "mod1",
             "mod2", "C", "p_c", "activity"]
        )

        primitives.add_edges_from(
            action_graph,
            [("A_res_1", "A"),
             ("p_a", "A_res_1"),
             ("mod1", "p_a"),
             ("B", "mod1"),
             ("p_c", "C"),
             ("B", "mod2"),
             ("activity", "B"),
             ("mod2", "p_c")]
        )
        hierarchy.add_graph("ag", action_graph)

        nugget_1 = nx.DiGraph()
        primitives.add_nodes_from(
            nugget_1,
            ["A", "A_res_1", "p", "B", "mod"]
        )
        primitives.add_edges_from(
            nugget_1,
            [("A_res_1", "A"),
             ("p", "A_res_1"),
             ("mod", "p"),
             ("B", "mod")]
        )
        hierarchy.add_graph("n1", nugget_1)

        nugget_2 = nx.DiGraph()
        primitives.add_nodes_from(
            nugget_2,
            ["B", "activity", "mod", "p", "C"])
        primitives.add_edges_from(nugget_2, [
            ("activity", "B"),
            ("B", "mod"),
            ("mod", "p"),
            ("p", "C")])
        hierarchy.add_graph("n2", nugget_2)

        # add typings
        hierarchy.add_typing(
            "mm", "mmm",
            {
                "gene": "component",
                "residue": "component",
                "state": "state",
                "mod": "action"
            }, total=True
        )

        hierarchy.add_typing(
            "mm", "colors",
            {
                "gene": "red",
                "residue": "red",
                "state": "red",
                "mod": "blue"
            }
        )
        hierarchy.add_typing(
            "ag", "mm",
            {
                "A": "gene",
                "B": "gene",
                "A_res_1": "residue",
                "mod1": "mod",
                "p_a": "state",
                "C": "gene",
                "activity": "state",
                "p_c": "state",
                "mod2": "mod"
            }, total=True
        )
        hierarchy.add_typing(
            "n1", "ag",
            {
                "A": "A",
                "B": "B",
                "A_res_1": "A_res_1",
                "mod": "mod1",
                "p": "p_a",
            }, total=True
        )

        hierarchy.add_typing(
            "n2", "ag",
            {
                "B": "B",
                "C": "C",
                "p": "p_c",
                "activity": "activity",
                "mod": "mod2",
            }, total=True
        )

        self.hierarchy = hierarchy

    def test_propagation_node_adds(self):
        """Test propagation down of additions."""
        p = nx.DiGraph()
        primitives.add_nodes_from(
            p, ["B"]
        )

        l = nx.DiGraph()
        primitives.add_nodes_from(
            l, ["B"]
        )

        r = nx.DiGraph()
        primitives.add_nodes_from(
            r, ["B", "B_res_1", "X", "Y"]
        )
        primitives.add_edge(r, "B_res_1", "B")

        rule = Rule(p, l, r)

        instance = {"B": "B"}

        rhs_typing = {
            "mm": {"B_res_1": "residue"},
            "mmm": {"X": "component"}, "colors": {"Y": "red"}
        }
        try:
            self.hierarchy.rewrite(
                "n1", rule, instance, lhs_typing=None, rhs_typing=rhs_typing)
            raise ValueError("Error was not caught!")
        except RewritingError:
            pass

        new_hierarchy, _ = self.hierarchy.rewrite(
            "n1", rule, instance,
            lhs_typing=None, rhs_typing=rhs_typing,
            strict=False, inplace=False)

        # test propagation of node adds
        assert("B_res_1" in new_hierarchy.graph["n1"].nodes())
        assert("B_res_1" in new_hierarchy.graph["ag"].nodes())
        assert(new_hierarchy.typing["n1"]["ag"]["B_res_1"] == "B_res_1")
        assert(new_hierarchy.typing["ag"]["mm"]["B_res_1"] == "residue")
        assert(("B_res_1", "B") in new_hierarchy.graph["n1"].edges())
        assert(("B_res_1", "B") in new_hierarchy.graph["ag"].edges())

        assert("X" in new_hierarchy.graph["n1"].nodes())
        assert("X" in new_hierarchy.graph["ag"].nodes())
        assert("X" in new_hierarchy.graph["mm"].nodes())
        assert("X" in new_hierarchy.graph["colors"].nodes())
        assert(new_hierarchy.typing["n1"]["ag"]["X"] == "X")
        assert(new_hierarchy.typing["ag"]["mm"]["X"] == "X")
        assert(new_hierarchy.typing["mm"]["mmm"]["X"] == "component")
        assert(new_hierarchy.typing["mm"]["colors"]["X"] == "X")

        assert("Y" in new_hierarchy.graph["n1"].nodes())
        assert("Y" in new_hierarchy.graph["ag"].nodes())
        assert("Y" in new_hierarchy.graph["mm"].nodes())
        assert("Y" in new_hierarchy.graph["mm"].nodes())
        assert(new_hierarchy.typing["n1"]["ag"]["Y"] == "Y")
        assert(new_hierarchy.typing["ag"]["mm"]["Y"] == "Y")
        assert(new_hierarchy.typing["mm"]["mmm"]["Y"] == "Y")
        assert(new_hierarchy.typing["mm"]["colors"]["Y"] == "red")

    def test_porpagation_node_attrs_adds(self):

        p = nx.DiGraph()
        primitives.add_nodes_from(
            p, [1, 2]
        )

        lhs = nx.DiGraph()
        primitives.add_nodes_from(
            lhs, [1, 2]
        )

        rhs = nx.DiGraph()
        primitives.add_nodes_from(
            rhs,
            [
                (1, {"a1": True}),
                (2, {"a2": 1}),
                (3, {"a3": "x"})]
        )

        rule = Rule(p, lhs, rhs)
        instance = {1: "A", 2: "A_res_1"}

        rhs_typing = {"mm": {3: "state"}}

        try:
            self.hierarchy.rewrite(
                "n1", rule, instance, lhs_typing=None, rhs_typing=rhs_typing)
            raise ValueError("Error was not caught!")
        except RewritingError:
            pass

        new_hierarchy, _ = self.hierarchy.rewrite(
            "n1", rule, instance,
            lhs_typing=None, rhs_typing=rhs_typing,
            strict=False, inplace=False)

        # test propagation of the node attribute adds
        assert("a1" in new_hierarchy.graph["n1"].node["A"])
        assert("a2" in new_hierarchy.graph["n1"].node["A_res_1"])
        assert("a3" in new_hierarchy.graph["n1"].node[3])

        assert("a1" in new_hierarchy.graph["ag"].node["A"])
        assert("a2" in new_hierarchy.graph["ag"].node["A_res_1"])
        assert("a3" in new_hierarchy.graph["ag"].node[3])
        # assert("a" in new_hierarchy.graph["ag"].node["B"])
        # assert("a" in new_hierarchy.graph["mm"].node["gene"])
        # assert("a" in new_hierarchy.graph["mmm"].node["component"])
        # assert("a" in new_hierarchy.graph["colors"].node["red"])

