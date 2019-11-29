"""Units tests for graph classes."""
from regraph import Rule
from regraph.graphs import Neo4jGraph, NXGraph

import logging

neo4j_log = logging.getLogger("neobolt")
neo4j_log.setLevel(logging.WARNING)
matplotlib_log = logging.getLogger("matplotlib")
matplotlib_log.setLevel(logging.WARNING)


class TestGraphClasses:
    """Main test class."""

    def __init__(self):
        """Initialize test object."""
        self.nx_graph = NXGraph()
        self.neo4j_graph = Neo4jGraph(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="admin")
        self.neo4j_graph._clear()
        node_list = [
            ("b", {"name": "Bob", "age": 20}),
            ("a", {"name": "Alice", "age": 35}),
            ("d", {"name": "dummy"})]

        edge_list = [
            ("a", "b", {"type": "friends", "since": 1999}),
            ("d", "a"), ("b", "d")]

        self.nx_graph.add_nodes_from(node_list)
        self.nx_graph.add_edges_from(edge_list)

        self.neo4j_graph.add_nodes_from(node_list)
        self.neo4j_graph.add_edges_from(edge_list)

        node = "c"
        attrs = {"name": "Claire", "age": 66}
        self.nx_graph.add_node(node, attrs)
        self.neo4j_graph.add_node(node, attrs)
        edge_attrs = {"type": "parent"}
        self.nx_graph.add_edge("c", "b", edge_attrs)
        self.neo4j_graph.add_edge("c", "b", edge_attrs)

        self.nx_graph.remove_edge("d", "a")
        self.neo4j_graph.remove_edge("d", "a")
        self.nx_graph.remove_node("d")
        self.neo4j_graph.remove_node("d")

        self.nx_graph.update_node_attrs("a", {"name": "Alison"})
        self.neo4j_graph.update_node_attrs("a", {"name": "Alison"})
        self.nx_graph.update_edge_attrs("a", "b", {"type": "enemies"})
        self.neo4j_graph.update_edge_attrs("a", "b", {"type": "enemies"})

        self.nx_graph.set_node_attrs("a", {"age": 19}, update=False)
        self.neo4j_graph.set_node_attrs("a", {"age": 19}, update=False)
        self.nx_graph.set_edge_attrs("a", "b", {"since": 1945}, update=False)
        self.neo4j_graph.set_edge_attrs("a", "b", {"since": 1945}, update=False)

        self.nx_graph.add_node_attrs("a", {"gender": {"M", "F"}})
        self.neo4j_graph.add_node_attrs("a", {"gender": {"M", "F"}})
        self.nx_graph.add_edge_attrs("a", "b", {"probability": 0.5})
        self.neo4j_graph.add_edge_attrs("a", "b", {"probability": 0.5})

        self.nx_graph.remove_node_attrs("a", {"gender": "F"})
        self.neo4j_graph.remove_node_attrs("a", {"gender": "F"})
        self.nx_graph.remove_edge_attrs("a", "b", {"probability": 0.5})
        self.neo4j_graph.remove_edge_attrs("a", "b", {"probability": 0.5})

        clone_id = self.nx_graph.clone_node("b", "b_clone")
        self.neo4j_graph.clone_node("b", "b_clone")

        # Test relabeling
        self.nx_graph.relabel_node("b", "baba")
        self.neo4j_graph.relabel_node("b", "baba")
        self.nx_graph.relabel_node("baba", "b")
        self.neo4j_graph.relabel_node("baba", "b")
        self.nx_graph.relabel_nodes(
            {clone_id: "lala", "b": "b1", "a": "a1", "c": "c1"})
        self.neo4j_graph.relabel_nodes(
            {clone_id: "lala", "b": "b1", "a": "a1", "c": "c1"})
        self.nx_graph.relabel_nodes(
            {"b1": "b", "a1": "a", "c1": "c", "lala": clone_id})
        self.neo4j_graph.relabel_nodes(
            {"b1": "b", "a1": "a", "c1": "c", "lala": clone_id})

        self.nx_graph.merge_nodes(["b", "c"])
        self.neo4j_graph.merge_nodes(["b", "c"])

        self.nx_graph.copy_node("a", "a_copy")
        self.neo4j_graph.copy_node("a", "a_copy")

        # Test find matching
        pattern = NXGraph()
        pattern.add_nodes_from(["x", ("y", {"name": "Claire"}), "z"])
        pattern.add_edges_from([("x", "y"), ("y", "y"), ("y", "z")])
        instances1 = self.nx_graph.find_matching(pattern)
        instances2 = self.neo4j_graph.find_matching(pattern)
        assert(instances1 == instances2)

        rule = Rule.from_transform(pattern)
        p_n, r_n = rule.inject_clone_node("y")
        rule.inject_remove_edge(p_n, "y")
        rule.inject_remove_edge("y", "y")
        rule.inject_add_node("w", {"name": "Frank"})
        rule.inject_add_edge("w", r_n, {"type": "parent"})
        rhs_g1 = self.nx_graph.rewrite(rule, instances1[0])
        rhs_g2 = self.neo4j_graph.rewrite(rule, instances1[0])

        self.nx_graph.relabel_node(rhs_g1[r_n], "b")
        self.neo4j_graph.relabel_node(rhs_g2[r_n], "b")
        self.nx_graph.relabel_node(rhs_g1["y"], "c")
        self.neo4j_graph.relabel_node(rhs_g2["y"], "c")

        # Test the two obtained graphs are the same
        assert(self.nx_graph == self.neo4j_graph)
        assert(set(
            self.nx_graph.predecessors("b")) == set(
                self.neo4j_graph.predecessors("b")))
        assert(set(
            self.nx_graph.successors("a")) == set(
                self.neo4j_graph.successors("a")))
        assert(self.nx_graph.get_node("c") == self.neo4j_graph.get_node("c"))
        assert(self.nx_graph.get_edge("c", "b") == self.neo4j_graph.get_edge(
            "c", "b"))

    def test_getters(self):
        """Test various getters."""
        assert(set(self.nx_graph.nodes()) == set(self.neo4j_graph.nodes()))
        assert(set(self.nx_graph.edges()) == set(self.neo4j_graph.edges()))
        self.neo4j_graph.nodes(data=True)
        self.neo4j_graph.edges(data=True)
        assert(self.nx_graph.get_node("a") == self.neo4j_graph.get_node("a"))
        assert(self.nx_graph.get_edge("a", "b") == self.neo4j_graph.get_edge(
            "a", "b"))
        assert(set(
            self.nx_graph.in_edges("b")) == set(
                self.neo4j_graph.in_edges("b")))
        assert(set(
            self.nx_graph.out_edges("a")) == set(
                self.neo4j_graph.out_edges("a")))

    def test_load_export(self):
        self.nx_graph.export("nxgraph.json")
        self.neo4j_graph.export("neo4jgraph.json")

        g1 = NXGraph.load("nxgraph.json")
        p = Neo4jGraph(
            driver=self.neo4j_graph._driver, node_label="new_node", edge_label="new_edge")
        p._clear()
        g2 = Neo4jGraph.load(
            driver=self.neo4j_graph._driver, filename="neo4jgraph.json",
            node_label="new_node", edge_label="new_edge")
        assert(g1 == g2)
