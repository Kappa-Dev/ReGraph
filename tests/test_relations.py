"""."""
import networkx as nx

from regraph.rules import Rule
from regraph.hierarchy import Hierarchy
from regraph.primitives import print_graph
from regraph.exceptions import (HierarchyError)
import regraph.primitives as prim

class TestRelations(object):

    def __init__(self):
        hierarchy = Hierarchy()

        base = nx.DiGraph()
        prim.add_nodes_from(base, [
            ("circle", {"a": {1, 2, 3}}),
            ("square", {"b": {1, 2, 3}})
        ])
        prim.add_edges_from(base, [
            ("circle", "circle"),
            ("square", "square"),
            ("circle", "square", {"c": {5, 6, 7}}),
            ("square", "circle")
        ])

        hierarchy.add_graph("base", base)

        a1 = nx.DiGraph()
        prim.add_nodes_from(a1, [
            ("black_circle", {"a": {1}}),
            ("white_circle", {"a": {2}}),
            ("black_square", {"b": {1}}),
            ("white_square", {"b": {1}})
        ])

        prim.add_edges_from(a1, [
            ("white_circle", "white_circle"),
            ("white_circle", "white_square", {"c": {5}}),
            ("black_circle", "black_square"),
            ("black_square", "white_square"),
            ("black_circle", "white_square", {"c": {6}})
        ])

        hierarchy.add_graph("a1", a1)
        hierarchy.add_typing(
            "a1", "base",
            {
                "black_circle": "circle",
                "white_circle": "circle",
                "white_square": "square",
                "black_square": "square"
            }
        )

        a2 = nx.DiGraph()
        prim.add_nodes_from(a2, [
            ("right_circle", {"a": {1, 2}}),
            ("middle_square", {"b": {1}}),
            ("left_circle", {"a": 1})
        ])

        prim.add_edges_from(a2, [
            ("right_circle", "middle_square", {"c": {5, 6, 7}}),
            ("left_circle", "middle_square", {"c": {6, 7}})
        ])

        hierarchy.add_graph("a2", a2)
        hierarchy.add_typing(
            "a2", "base",
            {
                "right_circle": "circle",
                "middle_square": "square",
                "left_circle": "circle"
            }
        )

        self.hierarchy = hierarchy

    def test_add_relation(self):
        self.hierarchy.add_relation(
            "a1", "a2",
            [
                ("white_circle", "right_circle"),
                ("white_square", "middle_square"),
                ("black_circle", "left_circle"),
                ("black_circle", "right_circle")
            ],
            {"name": "Some relation"}
        )
        # print(self.hierarchy.relations())
        # print(self.hierarchy.relation)
        g, l, r = self.hierarchy.relation_to_span(
            "a1", "a2", edges=True, attrs=True
        )
        # print_graph(g)
        # print(l)
        # print(r)
        # print(self.hierarchy)
        # self.hierarchy.remove_graph("a1")
        # print(self.hierarchy.relation)

        lhs = nx.DiGraph()
        lhs.add_nodes_from(["s", "c"])

        rule = Rule.from_transform(lhs)
        rule.clone_node("s")

        # instances = self.hierarchy.find_matching(
        #     "base",
        #     rule.lhs
        # )

        new_hierarchy, _ = self.hierarchy.rewrite(
            "base",
            rule,
            {"s": "square", "c": "circle"},
            inplace=False
        )
        g, l, r = new_hierarchy.relation_to_span(
            "a1", "a2"
        )
        # print_graph(g)
        # print(l)
        # print(r)
