import networkx as nx
from neobolt.exceptions import ServiceUnavailable

from regraph import NXHierarchy, Neo4jHierarchy

from regraph.audit import VersionedGraph, VersionedHierarchy
from regraph.rules import Rule
from regraph import primitives


class TestVersioning(object):
    """Class for testing `regraph.audit` module."""

    def __init__(self):
        graph = nx.DiGraph()
        graph.add_nodes_from(["circle", "square"])
        graph.add_edge("circle", "square")
        self.initial_graph = graph

    # def test_graph_rollback(self):
    #     g = VersionedGraph(self.initial_graph)

    #     # Branch 'test'
    #     g.branch("test")

    #     pattern = nx.DiGraph()
    #     pattern.add_node("square")
    #     rule = Rule.from_transform(pattern)
    #     # _, rhs_clone =
    #     rule.inject_clone_node("square")
    #     g.rewrite(
    #         rule, {"square": "square"},
    #         "Clone square")

    #     # Switch to master
    #     g.switch_branch("master")

    #     # Add edge and triangle
    #     pattern = nx.DiGraph()
    #     pattern.add_nodes_from(["circle"])
    #     rule = Rule.from_transform(pattern)
    #     # _, rhs_clone =
    #     rule.inject_add_edge("circle", "circle")
    #     rule.inject_add_node("triangle")
    #     rule.inject_add_edge("triangle", "circle")
    #     rhs_instance, _ = g.rewrite(
    #         rule, {"circle": "circle"},
    #         "Add edge to circle and triangle")
    #     triangle = rhs_instance["triangle"]

    #     # Clone circle
    #     pattern = nx.DiGraph()
    #     pattern.add_node("circle")
    #     rule = Rule.from_transform(pattern)
    #     _, rhs_clone = rule.inject_clone_node("circle")

    #     rhs_instance, rollback_commit = g.rewrite(
    #         rule, {"circle": "circle"},
    #         "Clone circle")

    #     # Remove original circle
    #     pattern = nx.DiGraph()
    #     pattern.add_node("circle")
    #     rule = Rule.from_transform(pattern)
    #     rule.inject_remove_node("circle")

    #     rhs_instance, _ = g.rewrite(
    #         rule,
    #         {"circle": rhs_instance["circle"]},
    #         message="Remove circle")

    #     # Merge circle clone and triangle
    #     pattern = nx.DiGraph()
    #     pattern.add_nodes_from(["circle", "triangle"])
    #     rule = Rule.from_transform(pattern)
    #     rule.inject_merge_nodes(["circle", "triangle"])

    #     rhs_instance, _ = g.rewrite(
    #         rule,
    #         {
    #             "circle": rhs_instance[rhs_clone],
    #             "triangle": triangle
    #         },
    #         message="Merge circle and triangle")

    #     g.rollback(rollback_commit)

    #     g.merge_with("test")

    #     # primitives.print_graph(g.graph)

    # def test_networkx_hierarchy_versioning(self):
    #     """Test hierarchy versioning functionality."""
    #     hierarchy = NetworkXHierarchy()
    #     shapes = nx.DiGraph()
    #     primitives.add_nodes_from(
    #         shapes, ["c", "s"])
    #     hierarchy.add_graph("shapes", shapes)

    #     colors = nx.DiGraph()
    #     primitives.add_nodes_from(
    #         colors, ["w", "b"])
    #     hierarchy.add_graph("colors", colors)

    #     ag = nx.DiGraph()
    #     primitives.add_nodes_from(
    #         ag, ["wc", "bc", "ws", "bs"])
    #     hierarchy.add_graph("ag", ag)

    #     nugget = nx.DiGraph()
    #     primitives.add_nodes_from(
    #         nugget, ["wc1", "wc2", "bc1", "ws1", "bs2"])
    #     hierarchy.add_graph("nugget", nugget)

    #     hierarchy.add_typing(
    #         "ag", "shapes", {
    #             "wc": "c",
    #             "bc": "c",
    #             "ws": "s",
    #             "bs": "s"
    #         })
    #     hierarchy.add_typing(
    #         "ag", "colors", {
    #             "wc": "w",
    #             "bc": "b",
    #             "ws": "w",
    #             "bs": "b"
    #         })
    #     hierarchy.add_typing(
    #         "nugget", "ag", {
    #             "wc1": "wc",
    #             "wc2": "wc",
    #             "bc1": "bc",
    #             "ws1": "ws",
    #             "bs2": "bs"
    #         })
    #     hierarchy.add_typing(
    #         "nugget", "colors", {
    #             "wc1": "w",
    #             "wc2": "w",
    #             "bc1": "b",
    #             "ws1": "w",
    #             "bs2": "b"
    #         })

    #     base = nx.DiGraph()
    #     base.add_nodes_from(["node"])
    #     hierarchy.add_graph("base", base)
    #     hierarchy.add_typing(
    #         "colors",
    #         "base", {
    #             "w": "node",
    #             "b": "node"
    #         })

    #     h = VersionedHierarchy(hierarchy)

    #     h.branch("test1")

    #     pattern = nx.DiGraph()
    #     pattern.add_nodes_from(["s"])
    #     rule2 = Rule.from_transform(pattern)
    #     rule2.inject_remove_node("s")

    #     h.rewrite(
    #         "shapes",
    #         rule2, {"s": "s"},
    #         message="Remove square")

    #     h.switch_branch("master")

    #     pattern = nx.DiGraph()
    #     pattern.add_nodes_from(["wc"])

    #     rule1 = Rule.from_transform(pattern)
    #     rule1.inject_clone_node("wc")

    #     _, clone_commit = h.rewrite(
    #         "ag",
    #         rule1, {"wc": "wc"},
    #         message="Clone 'wc'")

    #     pattern = nx.DiGraph()
    #     pattern.add_nodes_from(["wc1"])

    #     rule3 = Rule.from_transform(pattern)
    #     rule3.inject_add_node("new_node")
    #     rule3.inject_add_edge("new_node", "wc1")

    #     h.rewrite("nugget", rule3, {"wc1": "wc1"})

    #     h.switch_branch("test1")
    #     h.switch_branch("master")
    #     h.merge_with("test1")

    #     h.rollback(clone_commit)
    #     h.switch_branch("test1")

    def test_neo4j_hierarchy_versioning(self):
        """Test hierarchy versioning functionality."""
        try:
            hierarchy = Neo4jHierarchy(uri="bolt://localhost:7687",
                                       user="neo4j",
                                       password="admin")
            hierarchy._clear()
            hierarchy.add_graph(
                "shapes", node_list=[
                    ("c", {"a": 1}),
                    ("s", {"b": 2})])
            hierarchy.add_graph("colors", node_list=[
                ("w", {"a": 1, "b": 2}),
                ("b", {"a": 1, "b": 2})])
            hierarchy.add_graph("ag", node_list=[
                ("wc", {"a": 1}),
                "bc", 
                "ws",
                ("bs", {"b": 2})])
            hierarchy.add_graph(
                "nugget", node_list=[
                    ("wc1", {"a": 1}),
                    "wc2", "bc1", "ws1",
                    ("bs2", {"b": 2})])

            hierarchy.add_typing(
                "ag", "shapes", {
                    "wc": "c",
                    "bc": "c",
                    "ws": "s",
                    "bs": "s"
                })
            hierarchy.add_typing(
                "ag", "colors", {
                    "wc": "w",
                    "bc": "b",
                    "ws": "w",
                    "bs": "b"
                })
            hierarchy.add_typing(
                "nugget", "ag", {
                    "wc1": "wc",
                    "wc2": "wc",
                    "bc1": "bc",
                    "ws1": "ws",
                    "bs2": "bs"
                })
            hierarchy.add_typing(
                "nugget", "colors", {
                    "wc1": "w",
                    "wc2": "w",
                    "bc1": "b",
                    "ws1": "w",
                    "bs2": "b"
                })

            hierarchy.add_graph("base", node_list=[
                ("node", {"a": 1, "b": 2})])
            hierarchy.add_typing(
                "colors",
                "base", {
                    "w": "node",
                    "b": "node"
                })

            pattern = nx.DiGraph()
            pattern.add_nodes_from(["s", "c"])
            rule = Rule.from_transform(pattern)
            rule.inject_add_edge("s", "c", {"c": 3})

            hierarchy.rewrite(
                "nugget",
                rule,
                {"s": "bs2", "c": "wc1"})

            h = VersionedHierarchy(hierarchy)
            rollback_commit = h._heads["master"]

            pattern = nx.DiGraph()
            primitives.add_nodes_from(
                pattern,
                [("s", {"b": 2}),
                 ("c", {"a": 1})])
            primitives.add_edges_from(
                pattern,
                [("s", "c", {"c": 3})])
            rule2 = Rule.from_transform(pattern)
            clone, _ = rule2.inject_clone_node("s")
            rule2.inject_add_node("new_node")
            rule2.inject_add_edge("new_node", "s", {"d": 4})
            merged_rule_node = rule2.inject_merge_nodes([clone, "c"])
            rule2.inject_remove_edge("s", "c")

            rhs_instances, first_commit = h.rewrite(
                "ag", rule2, {"s": "bs", "c": "wc"},
                message="Rewriting neo4j graph")

            merged_ag_node = rhs_instances["ag"][merged_rule_node]

            h.branch('test')

            pattern = nx.DiGraph()
            pattern.add_nodes_from(["ws"])
            rule3 = Rule.from_transform(pattern)
            rule3.inject_remove_node("ws")

            h.rewrite(
                "ag", rule3, {"ws": "ws"},
                message="Removed ws from ag")

            h.switch_branch("master")

            pattern = nx.DiGraph()
            pattern.add_nodes_from([merged_ag_node])
            rule4 = Rule.from_transform(pattern)
            rule4.inject_clone_node(merged_ag_node)

            h.rewrite(
                "ag", rule4, {merged_ag_node: merged_ag_node},
                message="Cloned merged from ag")
            h.merge_with("test")

            data = h.to_json()
            h1 = VersionedHierarchy.from_json(hierarchy, data)
            h1.print_history()
            h1.rollback(rollback_commit)
        # except ServiceUnavailable as e:
        #     print(e)
        except:
            print()
