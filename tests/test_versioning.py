from neobolt.exceptions import ServiceUnavailable

from regraph import NXHierarchy, Neo4jHierarchy, NXGraph

from regraph.audit import VersionedGraph, VersionedHierarchy
from regraph.rules import Rule


import logging

neo4j_log = logging.getLogger("neobolt")
neo4j_log.setLevel(logging.WARNING)
matplotlib_log = logging.getLogger("matplotlib")
matplotlib_log.setLevel(logging.WARNING)


class TestVersioning(object):
    """Class for testing `regraph.audit` module."""

    def __init__(self):
        graph = NXGraph()
        graph.add_nodes_from(["circle", "square"])
        graph.add_edge("circle", "square")
        self.initial_graph = graph

    def test_graph_rollback(self):
        g = VersionedGraph(self.initial_graph)

        # Branch 'test'
        g.branch("test")

        pattern = NXGraph()
        pattern.add_node("square")
        rule = Rule.from_transform(pattern)
        # _, rhs_clone =
        rule.inject_clone_node("square")
        g.rewrite(
            rule, {"square": "square"},
            "Clone square")

        # Switch to master
        g.switch_branch("master")

        print("\n\n\nasserting...............")
        for s, t in g._revision_graph.edges():
            print(g._revision_graph.nodes[s]["message"])
            print(g._revision_graph.nodes[t]["message"])
            d = g._revision_graph.adj[s][t]["delta"]
            assert(
                set(d["rule"].rhs.nodes()) ==
                set(d["rhs_instance"].keys())
            )

        # Add edge and triangle
        pattern = NXGraph()
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
        pattern = NXGraph()
        pattern.add_node("circle")
        rule = Rule.from_transform(pattern)
        _, rhs_clone = rule.inject_clone_node("circle")

        rhs_instance, rollback_commit = g.rewrite(
            rule, {"circle": "circle"},
            "Clone circle")

        rhs_circle_clones = list({
            rule.p_rhs[p] for p in rule.cloned_nodes()["circle"]
        })

        # Remove original circle
        pattern = NXGraph()
        pattern.add_node("circle")
        rule = Rule.from_transform(pattern)
        rule.inject_remove_node("circle")

        rhs_instance, _ = g.rewrite(
            rule,
            {"circle": rhs_instance[rhs_circle_clones[0]]},
            message="Remove circle")

        # Merge circle clone and triangle
        pattern = NXGraph()
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
        g.print_history()
        g.rollback(rollback_commit)

        g.merge_with("test")

    def test_networkx_hierarchy_versioning(self):
        """Test hierarchy versioning functionality."""
        hierarchy = NXHierarchy()
        shapes = NXGraph()
        shapes.add_nodes_from(["c", "s"])
        hierarchy.add_graph("shapes", shapes)

        colors = NXGraph()
        colors.add_nodes_from(["w", "b"])
        hierarchy.add_graph("colors", colors)

        ag = NXGraph()
        ag.add_nodes_from(
            ["wc", "bc", "ws", "bs"])
        hierarchy.add_graph("ag", ag)

        nugget = NXGraph()
        nugget.add_nodes_from(
            ["wc1", "wc2", "bc1", "ws1", "bs2"])
        hierarchy.add_graph("nugget", nugget)

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

        base = NXGraph()
        base.add_nodes_from(["node"])
        hierarchy.add_graph("base", base)
        hierarchy.add_typing(
            "colors",
            "base", {
                "w": "node",
                "b": "node"
            })

        h = VersionedHierarchy(hierarchy)

        h.branch("test1")

        pattern = NXGraph()
        pattern.add_nodes_from(["s"])
        rule2 = Rule.from_transform(pattern)
        rule2.inject_remove_node("s")

        h.rewrite(
            "shapes",
            rule2, {"s": "s"},
            message="Remove square in shapes")

        h.switch_branch("master")

        pattern = NXGraph()
        pattern.add_nodes_from(["wc"])

        rule1 = Rule.from_transform(pattern)
        rule1.inject_clone_node("wc")

        _, clone_commit = h.rewrite(
            "ag",
            rule1, {"wc": "wc"},
            message="Clone 'wc' in ag")

        pattern = NXGraph()
        pattern.add_nodes_from(["wc1"])

        rule3 = Rule.from_transform(pattern)
        rule3.inject_add_node("new_node")
        rule3.inject_add_edge("new_node", "wc1")

        h.rewrite("nugget", rule3, {"wc1": "wc1"})
        # print(h.print_history())
        h.switch_branch("test1")
        h.switch_branch("master")
        h.merge_with("test1")

        h.rollback(clone_commit)
        h.switch_branch("test1")

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

            pattern = NXGraph()
            pattern.add_nodes_from(["s", "c"])
            rule = Rule.from_transform(pattern)
            rule.inject_add_edge("s", "c", {"c": 3})

            hierarchy.rewrite(
                "nugget",
                rule,
                {"s": "bs2", "c": "wc1"})

            h = VersionedHierarchy(hierarchy)
            rollback_commit = h._heads["master"]

            pattern = NXGraph()
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

            pattern = NXGraph()
            pattern.add_nodes_from(["ws"])
            rule3 = Rule.from_transform(pattern)
            rule3.inject_remove_node("ws")

            h.rewrite(
                "ag", rule3, {"ws": "ws"},
                message="Removed ws from ag")

            h.switch_branch("master")

            pattern = NXGraph()
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

    def test_irreversible_hierarchy(self):
        hierarchy = NXHierarchy()
        d = NXGraph()
        d.add_nodes_from(["c1", "c2", "s1", "s2"])
        hierarchy.add_graph("d", d)

        s = NXGraph()
        s.add_nodes_from(["c", "s"])
        hierarchy.add_graph("s", s)

        hierarchy.add_typing(
            "d", "s", {
                "c1": "c",
                "c2": "c",
                "s1": "s",
                "s2": "s"
            })
        h = VersionedHierarchy(hierarchy)

        pattern = NXGraph()
        pattern.add_nodes_from(["c1", "s1"])
        rule = Rule.from_transform(pattern)
        rule.inject_merge_nodes(["c1", "s1"])

        instance = {
            "c1": "c1",
            "s1": "s1"
        }

        h.rewrite("d", rule, instance)

        h.rollback(h.initial_commit())
        print(h.hierarchy.get_typing("d", "s"))
