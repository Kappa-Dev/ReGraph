"""."""
import os

from nose.tools import assert_equals

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter

from regraph.library.utils import plot_graph
from regraph.library.utils import plot_instance
from regraph.library.primitives import cast_node


class TestRewrites(object):
    """."""

    def __init__(self):
        graph = TypedDiGraph()
        graph.add_node(1, 'agent',
                          {'name': 'EGFR', 'state': 'p'})
        graph.add_node(2, 'action', attrs={'name': 'BND'})
        graph.add_node(3, 'agent',
                          {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        graph.add_node(4, 'region', attrs={'name': 'SH2'})
        graph.add_node(5, 'agent', attrs={'name': 'EGFR'})
        graph.add_node(6, 'action', attrs={'name': 'BND'})
        graph.add_node(7, 'agent', attrs={'name': 'Grb2'})

        graph.add_node(8, 'agent', attrs={'name': 'WAF1'})
        graph.add_node(9, 'action', {'name': 'BND'})
        graph.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

        graph.add_node(11, 'agent')
        graph.add_node(12, 'agent')
        graph.add_node(13, 'agent')

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

        graph.add_edges_from(edges)

        graph.set_edge(1, 2, {'s': 'p'})
        graph.set_edge(4, 2, {'s': 'u'})
        graph.set_edge(5, 6, {'s': 'p'})
        graph.set_edge(7, 6, {'s': 'u'})
        graph.set_edge(5, 2, {'s': 'u'})

        self.LHS_ = TypedDiGraph()

        self.LHS_.add_node(1, 'agent', {'name': 'EGFR'})
        self.LHS_.add_node(2, 'action', {'name': 'BND'})
        self.LHS_.add_node(3, 'region')
        self.LHS_.add_node(4, 'agent', {'name': 'Grb2'})
        self.LHS_.add_node(5, 'agent', {'name': 'EGFR'})
        self.LHS_.add_node(6, 'action', {'name': 'BND'})
        self.LHS_.add_node(7, 'agent', {'name': 'Grb2'})

        self.LHS_.add_edges_from([(1, 2), (3, 2), (3, 4), (5, 6), (7, 6)])

        self.LHS_.set_edge(1, 2, {'s': 'p'})
        self.LHS_.set_edge(5, 6, {'s': 'p'})

        self.rw_ = Rewriter(graph)
        self.instances_ = self.rw_.find_matching(self.LHS_)

    def test_find_matching(self):
        assert_equals(self.instances_, [{1: 1, 2: 2, 3: 4, 4: 3, 5: 5, 6: 6, 7: 7}])

        new_pattern = TypedDiGraph()
        new_pattern.add_node("a", "agent")
        new_pattern.add_node("b", "agent")
        new_pattern.add_node("c", "agent")

        new_pattern.add_edges_from([("a", "b"), ("a", "c")])
        instances = self.rw_.find_matching(new_pattern)
        assert_equals(6, len(instances))

    def test_transform_instance(self):
        self.rw_.transform_instance(
            self.instances_[0],
            """delete_node 6.\n"""
            """merge [1, 5] method union as merge_1.\n"""
            """merge [4, 7] as merge_2.\n"""
            """add_edge merge_1 merge_2.\n"""
            """clone merge_1 as clone_1.\n"""
            """clone 3 as clone_2.""")

    def test_clonning_merging_sequence(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))

        g = TypedDiGraph()

        g.add_node(1, "agent", {"name": "John"})
        g.add_node(2, "action", {})

        g.add_edges_from([(1, 2), (2, 1)])

        plot_graph(
            g,
            filename=os.path.join(__location__, "cms_test_init.png"))

        LHS = TypedDiGraph()
        LHS.add_node('entity', 'agent')
        LHS.add_node('media', 'action')

        LHS.add_edges_from([('entity', 'media'), ('media', 'entity')])

        rewriter = Rewriter(g)
        instances = rewriter.find_matching(LHS)

        for i, instance in enumerate(instances):
            plot_instance(
                rewriter.graph_,
                LHS,
                instance,
                os.path.join(__location__, "cms_instance_%d.png" % i))
        for instance in instances:
            new_name = rewriter.clone(instance, 'media')
            rewriter.add_edge(instance, 'media', new_name)
            # rewriter.merge(instance, ['media', new_name])
        plot_graph(
            rewriter.graph_,
            filename=os.path.join(__location__, "cms_test_clone1.png"))

    def test_undirected_imp_init(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))

        g = TypedGraph()
        g.add_node(1, "agent", {"name": "John"})
        g.add_node(2, "action")
        g.add_node(3, "agent", {"name": "Paul"})

        g.add_edges_from([(1, 2), (3, 2)])
        g.set_edge(1, 2, {"a": 0})

        rw = Rewriter(g)
        LHS = TypedGraph()
        LHS.add_nodes_from([(1, "agent"), (2, "action")])
        LHS.add_edges_from([(1, 2)])
        instances = rw.find_matching(LHS)
        for i, instance in enumerate(instances):
            plot_instance(
                rw.graph_,
                LHS,
                instance,
                os.path.join(__location__, "undir_instance_%d.png" % i))
        rw.add_node(instances[0], 'region', 'Europe', {"a": 44})
        rw.delete_node(instances[0], 1)
        rw.add_edge(instances[0], 2, 'Europe', {"a": 55})
        rw.delete_edge(instances[0], 2, 3)
        rw.clone(instances[0], 2)
        cast_node(rw.graph_, "Europe", "action")
        rw.merge(instances[0], ["Europe", 2])
        plot_graph(
            rw.graph_,
            filename=os.path.join(__location__, "undir_cloned.png"))

    def test_undirected_dec_init(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))

        g = TypedGraph()
        g.add_node(1, "action")
        g.add_node(2, "agent", {"u": {0, 100}})
        g.add_node(3, "agent", {"u": {4}, "name": "Paul"})
        g.add_node(4, "action")
        g.add_node(5, "agent", {"u": {0}})
        g.add_node(6, "agent", {"u": {7}})
        g.add_node(7, "agent", {"u": {4}})

        g.add_edges_from([
            (1, 2),
            (3, 2),
            (1, 5),
            (5, 4),
            (5, 6)])
        g.set_edge(1, 2, {"a": 0})
        g.set_edge(2, 3, {"k": {55, 66, 45}})

        rw = Rewriter(g)

        LHS = TypedGraph()
        LHS.add_nodes_from(
            [(1000, "action"),
             (2000, "agent"),
             (3000, "agent")])
        LHS.node[2000].attrs_ = {"u": 0}

        LHS.add_edges_from([
            (1000, 2000),
            (2000, 3000)])
        LHS.set_edge(2000, 3000, {"k": {45, 66}})

        RHS = TypedGraph()
        RHS.add_node(33, "region")
        RHS.add_node(44, "agent", {"u": {3}})
        RHS.add_node(55, "agent", {"u": {0, 2}})

        RHS.add_edges_from([(33, 55), (44, 55), (55, 55)])
        RHS.set_edge(55, 55, {"k": {45, 99, 66, 105}})
        RHS.set_edge(44, 55, {"k": {18}})
        RHS.set_edge(33, 55, {"a": 12})

        P = TypedGraph()
        P.add_node(101, "agent")
        P.add_node(201, "agent", {"u": {0}})
        P.add_node(301, "agent")
        P.add_edges_from([(301, 101), (201, 301)])
        P.set_edge(201, 301, {"k": {45, 66}})

        instances = rw.find_matching(LHS)
        for i, instance in enumerate(instances):
            plot_instance(
                rw.graph_,
                LHS,
                instance,
                os.path.join(__location__, "undir_dec_instance_%d.png" % i))
        left_h = Homomorphism(
            P,
            LHS,
            {101: 2000, 201: 2000, 301: 3000})
        righ_h = Homomorphism(
            P,
            RHS,
            {101: 44, 201: 55, 301: 55})
        RHS_instance = rw.apply_rule(instances[0], left_h, righ_h)
        print(rw.graph_.edges())
        # print(rw.graph_.node['2_copy'].attrs_)
        # print(rw.graph_.node['2_3'].attrs_)
        print(rw.graph_.edge['2_3']['2_3'])
        print(rw.graph_.edge['2_copy']['2_3'])
        print(rw.graph_.edge['new_node_0']['2_3'])
        plot_instance(
            rw.graph_,
            RHS,
            RHS_instance,
            filename=os.path.join(__location__, "undir_dec_RHS_instance.png"))
