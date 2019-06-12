import networkx as nx

from regraph import Rule
from regraph import NetworkXHierarchy
from regraph import primitives
from regraph.networkx.rewriting_utils import get_rule_hierarchy


class TestRuleProjections(object):
    """Test class for testing rule projections."""

    def __init__(self):
        self.hierarchy = NetworkXHierarchy()

        a = nx.DiGraph()
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

        b = nx.DiGraph()
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

        c = nx.DiGraph()
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
        pattern = nx.DiGraph()
        primitives.add_nodes_from(pattern, [
            ("student", {"sex": {"male", "female"}}),
            "prof"
        ])
        primitives.add_edge(pattern, "prof", "student")

        p = nx.DiGraph()
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

        # Test canonical rule lifting
        rule_hierarchy, instances = self.hierarchy.get_rule_propagations(
            "b", rule)

        # Test non-canonical rule lifting
        rule_hierarchy, instances = self.hierarchy.get_rule_propagations(
            "b", rule, p_typing={"c": {"Alice": "girl"}})

        # print(lifting["c"]["rule"])
        # print(lifting["c"]["p_g_p"])

        # Test non-canonical rule lifting
        rule_hierarchy, instances = self.hierarchy.get_rule_propagations(
            "b", rule, p_typing={"c": {"Alice": {"girl", "generic"}, "Bob": "boy"}})

        instance = {
            n: n for n in rule.lhs.nodes()
        }

        new_hierarchy, rhs_g = self.hierarchy.apply_rule_hierarchy(
            "b", rule_hierarchy, instances, inplace=False)
        print(new_hierarchy.graph["b"].nodes())
        print(new_hierarchy.graph["c"].nodes())
        print(new_hierarchy.typing["c"]["b"])
        print(rhs_g)
        # print(lifting["c"]["rule"])
        # print(lifting["c"]["p_g_p"])

    def test_projection(self):
        pattern = nx.DiGraph()
        primitives.add_nodes_from(pattern, [
            "school",
            "institute"
        ])
        rule = Rule.from_transform(pattern)
        rule.inject_add_node("phd")
        rule.inject_add_edge("phd", "institute", {"type": "internship"})

        rule_hierarchy, instances = self.hierarchy.get_rule_propagations(
            "b", rule)

        # print(projections["a"]["rule"])
        # print(projections["a"]["instance"])
        # print(projections["a"]["p_p_t"])
        # print(projections["a"]["r_r_t"])

        rule_hierarchy, instances = self.hierarchy.get_rule_propagations(
            "b", rule, rhs_typing={"a": {"phd": "red"}})

        instance = {
            n: n for n in rule.lhs.nodes()
        }
        print(rule_hierarchy)

        new_hierarchy, rhs_g = self.hierarchy.apply_rule_hierarchy(
            "b", rule_hierarchy, instances, inplace=False)
        print(new_hierarchy.typing["b"]["a"])
        print(new_hierarchy.typing["bb"]["a"])
        print(new_hierarchy.typing["b"]["bb"])
        print(rhs_g)
        print(instances)
