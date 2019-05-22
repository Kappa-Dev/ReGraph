import networkx as nx

from regraph.audit import VersionedGraph
from regraph.rules import Rule
from regraph.primitives import print_graph


class TestVersioning(object):
    """Class for testing `regraph.audit` module."""

    def __init__(self):
        graph = nx.DiGraph()
        graph.add_nodes_from(["circle", "square"])
        graph.add_edge("circle", "square")
        self.initial_graph = graph

    def test_rollback(self):
        g = VersionedGraph(self.initial_graph)

        # Branch 'test'
        g.branch("test")

        pattern = nx.DiGraph()
        pattern.add_node("square")
        rule = Rule.from_transform(pattern)
        # _, rhs_clone =
        rule.inject_clone_node("square")
        g.rewrite(
            rule, {"square": "square"},
            "Clone square")

        # Switch to master
        g.switch_branch("master")

        # Add edge and triangle
        pattern = nx.DiGraph()
        pattern.add_nodes_from(["circle"])
        rule = Rule.from_transform(pattern)
        # _, rhs_clone =
        rule.inject_add_edge("circle", "circle")
        rule.inject_add_node("triangle")
        rule.inject_add_edge("triangle", "circle")
        rhs_instance, _ = g.rewrite(
            rule, {"circle": "circle"},
            "Add edge to circle and triangle")
        triangle = rhs_instance["triangle"]

        # Clone circle
        pattern = nx.DiGraph()
        pattern.add_node("circle")
        rule = Rule.from_transform(pattern)
        _, rhs_clone = rule.inject_clone_node("circle")

        rhs_instance, rollback_commit = g.rewrite(
            rule, {"circle": "circle"},
            "Clone circle")

        print("\n")
        print(g._deltas["test"]["rule"])

        # Remove original circle
        pattern = nx.DiGraph()
        pattern.add_node("circle")
        rule = Rule.from_transform(pattern)
        rule.inject_remove_node("circle")

        rhs_instance, _ = g.rewrite(
            rule,
            {"circle": rhs_instance["circle"]},
            message="Remove circle")

        # Merge circle clone and triangle
        pattern = nx.DiGraph()
        pattern.add_nodes_from(["circle", "triangle"])
        rule = Rule.from_transform(pattern)
        rule.inject_merge_nodes(["circle", "triangle"])

        rhs_instance, _ = g.rewrite(
            rule,
            {
                "circle": rhs_instance[rhs_clone],
                "triangle": triangle
            },
            message="Merge circle and triangle")

        # print("\n")
        # print(g._deltas["test"]["rule"])

        g.rollback(rollback_commit)
        print("\n")
        print(g._deltas["test"]["rule"])

        g.merge_with("test")

        print_graph(g.graph)