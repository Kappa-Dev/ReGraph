import networkx as nx

from regraph import Rule, compose_rule_hierarchies
from regraph import NXHierarchy, NXGraph
from regraph import primitives


class TestRuleProjections(object):
    """Test class for testing rule projections."""

    def __init__(self):
        self.hierarchy = NXHierarchy()

        a = NXGraph()
        primitives.add_nodes_from(a, [
            ("red", {"sex": {"male", "female"}}),
            ("blue", {"location": {"far", "close"}})
        ])
        primitives.add_edges_from(a, [
            ("red", "red", {"type": {"friend", "supervisor"}}),
            ("red", "blue", {"type": "works"}),
            ("blue", "blue")
        ])
        self.hierarchy.add_graph("a", a)

        b = NXGraph()
        primitives.add_nodes_from(b, [
            ("prof", {"sex": {"male", "female"}}),
            ("student", {"sex": {"male", "female"}}),
            ("school", {"location": {"far", "close"}}),
            ("institute", {"location": {"far", "close"}})
        ])
        primitives.add_edges_from(
            b,
            [
                ("prof", "prof", {"type": "friend"}),
                ("student", "student", {"type": "friend"}),
                ("prof", "student", {"type": {"friend", "supervisor"}}),
                ("student", "prof", {"type": "friend"}),
                ("prof", "school"),
                ("prof", "institute"),
                ("student", "school"),
                ("institute", "school")
            ])
        self.hierarchy.add_graph("b", b)
        b_a = {
            "prof": "red",
            "student": "red",
            "school": "blue",
            "institute": "blue"
        }
        self.hierarchy.add_graph("bb", b)
        self.hierarchy.add_typing("b", "bb",
                                  {n: n for n in b.nodes()})
        self.hierarchy.add_typing("b", "a", b_a)
        self.hierarchy.add_typing("bb", "a", b_a)

        c = NXGraph()
        primitives.add_nodes_from(c, [
            ("Alice", {"sex": "female"}),
            ("Bob", {"sex": "male"}),
            ("John", {"sex": "male"}),
            ("Nancy", {"sex": "female"}),
            ("ENS", {"location": "close"}),
            ("INRIA")
        ])
        primitives.add_edges_from(c, [
            ("Alice", "Bob", {"type": "friend"}),
            ("Alice", "ENS"),
            ("John", "Alice", {"type": "supervisor"}),
            ("John", "ENS"),
            ("Nancy", "John", {"type": "friend"}),
            ("Nancy", "INRIA")
        ])
        c_b = {
            "Alice": "student",
            "Bob": "student",
            "John": "prof",
            "Nancy": "prof",
            "ENS": "school",
            "INRIA": "institute"
        }
        self.hierarchy.add_graph("c", c)
        self.hierarchy.add_typing("c", "b", c_b)

    def test_lifting(self):
        pattern = NXGraph()
        primitives.add_nodes_from(pattern, [
            ("student", {"sex": {"male", "female"}}),
            "prof"
        ])
        primitives.add_edge(pattern, "prof", "student")

        p = NXGraph()
        primitives.add_nodes_from(p, [
            ("girl", {"sex": "female"}),
            ("boy", {"sex": "male"}),
            ("generic")
        ])
        p_lhs = {
            "girl": "student",
            "boy": "student",
            "generic": "student"
        }
        rule = Rule(p, pattern, p_lhs=p_lhs)

        # Test non-canonical rule lifting

        rule_hierarchy1, lhs_instances1 = self.hierarchy.get_rule_propagations(
            "b", rule, p_typing={"c": {"Alice": {"girl", "generic"}, "Bob": "boy"}})

        new_hierarchy = NXHierarchy.copy(self.hierarchy)

        rhs_instances1 = new_hierarchy.apply_rule_hierarchy(
            rule_hierarchy1, lhs_instances1)

        pattern = NXGraph()
        primitives.add_nodes_from(pattern, [
            "school",
            "institute"
        ])
        rule = Rule.from_transform(pattern)
        rule.inject_add_node("phd")
        rule.inject_add_edge("phd", "institute", {"type": "internship"})

        rule_hierarchy2, lhs_instances2 = self.hierarchy.get_rule_propagations(
            "b", rule, rhs_typing={"a": {"phd": "red"}})

        new_hierarchy = NXHierarchy.copy(self.hierarchy)

        rhs_instances2 = new_hierarchy.apply_rule_hierarchy(
            rule_hierarchy2, lhs_instances2)

        # h, l, r = compose_rule_hierarchies(
        #     rule_hierarchy1, lhs_instances1, rhs_instances1,
        #     rule_hierarchy2, lhs_instances2, rhs_instances2)

        # print(h, l, r)
        # for k, v in h["rules"].items():
        #     print("Rule for ", k)
        #     print(v)
