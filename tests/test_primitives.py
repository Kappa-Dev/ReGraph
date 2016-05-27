"""Test primitives of graph rewriting."""

from nose.tools import assert_equals
from nose.tools import raises

from regraph.library.data_structures import TypedDiGraph
from regraph.library import primitives


class TestPrimitives(object):
    """Class for testing primitives with Python nose tests."""

    def __init__(self):
        """Initialize test graph."""
        self.graph_ = TypedDiGraph()
        self.graph_.add_node(1, 'agent',
                             {'name': 'EGFR', 'state': 'p'})
        self.graph_.add_node(2, 'action', attrs={'name': 'BND'})
        self.graph_.add_node(3, 'agent',
                             {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        self.graph_.add_node(4, 'region', attrs={'name': 'SH2'})
        self.graph_.add_node(5, 'agent', attrs={'name': 'EGFR'})
        self.graph_.add_node(6, 'action', attrs={'name': 'BND'})
        self.graph_.add_node(7, 'agent', attrs={'name': 'Grb2'})

        self.graph_.add_node(8, 'agent', attrs={'name': 'WAF1'})
        self.graph_.add_node(9, 'action', {'name': 'BND'})
        self.graph_.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

        self.graph_.add_node(11, 'agent')
        self.graph_.add_node(12, 'agent')
        self.graph_.add_node(13, 'agent')

        edges = [
            (1, 2),
            (4, 2),
            (4, 3),
            (5, 6),
            (7, 6),
            (8, 9),
            (10, 9),
            (11, 12),
            (12, 11),
            (12, 13),
            (13, 12),
            (11, 13),
            (13, 11),
            (5, 2)
        ]

        self.graph_.add_edges_from(edges)

        self.graph_.set_edge(1, 2, {'s': 'p'})
        self.graph_.set_edge(4, 2, {'s': 'u'})
        self.graph_.set_edge(5, 6, {'s': 'p'})
        self.graph_.set_edge(7, 6, {'s': 'u'})
        self.graph_.set_edge(5, 2, {'s': 'u'})

    def test_cast_node(self):
        nodes = self.graph_.nodes()
        primitives.cast_node(self.graph_, nodes[0], 'new_type')
        assert_equals(self.graph_.node[nodes[0]].type_, 'new_type')

    @raises(ValueError)
    def test_add_node_exists(self):
        primitives.add_node(self.graph_, 'anytype', name=1, attrs={})

    def test_add_node(self):
        new_graph = self.graph_.copy()
        primitives.add_node(
            new_graph,
            node_type="my_type",
            name="new_node",
            attrs={"a": 33, "b": 44})

        if "new_node" not in new_graph.nodes():
            assert False

        assert_equals(new_graph.node["new_node"].type_, "my_type")
        assert_equals(
            new_graph.node["new_node"].attrs_,
            {"a": 33, "b": 44})

    @raises(ValueError)
    def test_remove_node_non_existing(self):
        primitives.remove_node(self.graph_, 34)

    def test_remove_node(self):
        new_graph = self.graph_.copy()
        primitives.remove_node(
            new_graph, 13)
        if 13 in new_graph.nodes():
            assert False
        if (13, 11) in new_graph.edges():
            assert False
        if (13, 12) in new_graph.edges():
            assert False
        if (11, 13) in new_graph.edges():
            assert False
        if (12, 13) in new_graph.edges():
            assert False

    @raises(ValueError)
    def test_add_edge_non_existing_node(self):
        primitives.add_edge(self.graph_, 1, 23)

    @raises(ValueError)
    def test_add_edge_exists(self):
        primitives.add_edge(self.graph_, 8, 9)

    def test_add_edge(self):
        new_graph = self.graph_.copy()
        primitives.add_edge(
            new_graph, 8, 2, {"a": 4})
        primitives.add_edge(
            new_graph, 6, 2)
        if (8, 2) not in new_graph.edges():
            assert False
        if (6, 2) not in new_graph.edges():
            assert False
        assert_equals(
            new_graph.edge[8][2],
            {"a": 4})

    @raises(ValueError)
    def test_remove_edge_non_existing(self):
        primitives.remove_edge(self.graph_, 13, 8)

    def test_remove_edge(self):
        new_graph = self.graph_.copy()
        primitives.remove_edge(
            new_graph, 8, 9)
        if (8, 9) in new_graph.edges():
            assert False

    def test_merge_attributes(self):
        attr1 = {"a": 23,
                 "b": (1, 2),
                 "c": {(4, 4), (4, 5), (6, 7)},
                 "d": {(1, 2), (3, 4)}}
        attr2 = {"a": 12,
                 "c": {(4, 4), (6, 7)},
                 "d": (1, 2)}
        res1 = primitives.merge_attributes(attr1, attr2, "union")
        res2 = primitives.merge_attributes(attr1, attr2, "intersection")

        assert_equals(res1, {
            "a": {12, 23},
            "b": (1, 2),
            "c": {(4, 4), (4, 5), (6, 7)},
            "d": {(1, 2), (3, 4)}})

        assert_equals(res2, {"c": {(4, 4), (6, 7)},
                             "d": (1, 2)})

    @raises(ValueError)
    def test_merge_nodes_type_fail(self):
        primitives.merge_nodes(self.graph_, [1, 4])

    @raises(ValueError)
    def test_merge_nodes_name_exists(self):
        primitives.merge_nodes(self.graph_, [1, 5], node_name=5)

    @raises(ValueError)
    def test_merge_nodes_method(self):
        primitives.merge_nodes(self.graph_, [1, 5], method="unknown")

    def test_merge_nodes(self):
        # test with union
        new_graph = self.graph_.copy()
        primitives.merge_nodes(new_graph,
                               [1, 5],
                               "union",
                               "merge_1",
                               "union")
        assert_equals(
            new_graph.node["merge_1"].type_,
            "agent")
        assert_equals(
            new_graph.node["merge_1"].attrs_,
            {'name': 'EGFR', 'state': 'p'})
        assert_equals(
            new_graph.edge["merge_1"][2],
            {"s": {"u", "p"}})

        # test with intersections
        new_graph = self.graph_.copy()
        primitives.merge_nodes(new_graph,
                               [1, 5],
                               "intersection",
                               "merge_1",
                               "intersection")
        assert_equals(
            new_graph.node["merge_1"].type_,
            "agent")
        assert_equals(
            new_graph.node["merge_1"].attrs_,
            {"name": "EGFR"})
        assert_equals(
            new_graph.edge["merge_1"][2],
            {})

    @raises(ValueError)
    def test_clone_node_non_existing(self):
        primitives.clone_node(self.graph_, 34)

    def test_clone_node(self):
        new_graph = self.graph_.copy()
        primitives.clone_node(new_graph, 4, "clone")

        if "clone" not in new_graph.nodes():
            assert False

        assert_equals(
            new_graph.node["clone"].type_,
            new_graph.node[4].type_)

        assert_equals(
            new_graph.node["clone"].attrs_,
            new_graph.node[4].attrs_)

        assert_equals(
            new_graph.in_edges("clone"),
            new_graph.in_edges(4))

        for s, t in new_graph.in_edges(4):
            assert_equals(
                new_graph.edge[s]["clone"],
                new_graph.edge[s][t])
        for s, t in new_graph.out_edges(4):
            assert_equals(
                new_graph.edge["clone"][t],
                new_graph.edge[s][t])
