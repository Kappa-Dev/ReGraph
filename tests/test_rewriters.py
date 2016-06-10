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
        g.add_node(2, "agent", {"u": {0, 1}})
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
        g.set_edge(2, 3, {"k": {1, 2, 3}})

        rw = Rewriter(g)

        LHS = TypedGraph()
        LHS.add_nodes_from(
            [(10, "action"),
             (20, "agent"),
             (30, "agent")])
        LHS.node[20].attrs_ = {"u": 0}

        LHS.add_edges_from([
            (10, 20),
            (20, 30)])
        LHS.set_edge(20, 30, {"k": {1, 2}})

        P = TypedGraph()
        P.add_node(100, "agent")
        P.add_node(200, "agent", {"u": {0}})
        P.add_node(300, "agent")
        P.add_edges_from([(300, 100), (200, 300)])
        P.set_edge(100, 300, {"k": {1, 2}})
        P.set_edge(200, 300, {"k": set()})

        RHS = TypedGraph()
        RHS.add_node(1000, "region")
        RHS.add_node(2000, "agent", {"u": {3}})
        RHS.add_node(3000, "agent", {"u": {0, 2}})

        RHS.add_edges_from(
            [(1000, 3000),
             (2000, 3000),
             (3000, 3000)])
        RHS.set_edge(3000, 3000, {"k": {5, 6}})
        RHS.set_edge(2000, 3000, {"k": {1, 2, 10}})
        RHS.set_edge(1000, 3000, {"a": 12})

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
            {100: 20, 200: 20, 300: 30})
        righ_h = Homomorphism(
            P,
            RHS,
            {100: 2000, 200: 3000, 300: 3000})
        RHS_instance = rw.apply_rule(instances[0], left_h, righ_h)
        plot_instance(
            rw.graph_,
            RHS,
            RHS_instance,
            filename=os.path.join(__location__, "undir_dec_RHS.png"))

    def test_rule_to_homomorphism(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))

        g = TypedGraph()
        g.add_node(1, "action")
        g.add_node(2, "agent", {"u": {0, 1}})
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
        g.set_edge(2, 3, {"k": {1, 2, 3}})

        rw = Rewriter(g)

        LHS = TypedGraph()
        LHS.add_nodes_from(
            [(1, "action"),
             (2, "agent"),
             (3, "agent")])
        LHS.node[2].attrs_ = {"u": 0}

        LHS.add_edges_from([
            (1, 2),
            (2, 3)])
        LHS.set_edge(2, 3, {"k": {1, 2}})

        instances = rw.find_matching(LHS)

        rw.add_node_attrs(
            instances[0],
            1,
            {"u": 55, "x": 0})
        h1, h2 = rw.generate_rule(
            LHS,
            """delete_node 1.
            clone 2 as clone.
            delete_node_attrs clone {u: 0}.
            delete_edge 2 3.
            delete_edge_attrs clone 3 {k: {1}}.
            update_edge_attrs clone 3 {t: 333}.
            update_node_attrs 2 {u: {12, 13}}.
            merge [clone, 3] as merged.
            add_node_attrs merged {m: 1}.
            add_node new_node type region.
            add_node_attrs new_node {x: 1}.
            add_edge new_node merged.
            add_edge_attrs merged new_node {j: 33}."""
        )

        RHS_instance = rw.apply_rule(instances[0], h1, h2)
        plot_instance(
            rw.graph_,
            h2.target_, RHS_instance,
            filename=os.path.join(__location__, "undir_rule_to_hom_RHS.png"))

    def test_cloning_cases(self):
        g = TypedDiGraph()
        g.add_node(10, "agent", {"a": 0})
        g.add_node(20, "agent", {"b": 0})
        g.add_node(30, "action", {"c": 0})
        g.add_edges_from(
            [(10, 30),
             (20, 30)])
        g.set_edge(10, 30, {"x": 0})
        g.set_edge(20, 30, {"y": 0})

        LHS = TypedDiGraph()
        LHS.add_node(1, "agent")

        rw = Rewriter(g)
        instances = rw.find_matching(LHS)

        # simple clone
        P1 = TypedDiGraph()
        P1.add_node("a", "agent")
        P1.add_node("b", "agent")

        RHS1 = TypedDiGraph()
        RHS1.add_node("x", "agent")
        RHS1.add_node("y", "agent")

        h1 = Homomorphism(
            P1, LHS,
            {"a": 1, "b": 1})
        h2 = Homomorphism(
            P1, RHS1,
            {"a": "x", "b": "y"})
        RHS_instance = rw.apply_rule(instances[0], h1, h2)

        # clone merge on the same nodes
        RHS2 = TypedGraph()
        RHS2.add_node("x", "agent")
        h2 = Homomorphism(
            P1, RHS2, {"a": "x", "b": "x"})
        RHS_instance = rw.apply_rule(instances[0], h1, h2)

        # clone and merge one with other node
        LHS.add_node(2, "agent")
        # update matching
        instances = rw.find_matching(LHS)

        P3 = TypedDiGraph()
        P3.add_node("a", "agent")
        P3.add_node("b", "agent")
        P3.add_node("c", "agent")

        RHS3 = TypedDiGraph()
        RHS3.add_node("x", "agent")
        RHS3.add_node("y", "agent")

        h1 = Homomorphism(
            P3, LHS,
            {"a": 1, "b": 1, "c": 2})
        h2 = Homomorphism(
            P3, RHS3,
            {"a": "x", "b": "y", "c": "y"})
        RHS_instance = rw.apply_rule(instances[0], h1, h2)

    def test_merging(self):
        g = TypedDiGraph()
        g.add_node(10, "agent", {"a": 0})
        g.add_node(20, "agent", {"b": 0})
        g.add_node(30, "action", {"c": 0})
        g.add_edges_from(
            [(10, 30),
             (20, 30)])
        g.set_edge(10, 30, {"x": 0})
        g.set_edge(20, 30, {"y": 0})

        LHS = TypedDiGraph()
        LHS.add_node(1, "agent")
        LHS.add_node(2, "agent")

        P = TypedDiGraph()
        P.add_node("a", "agent")
        P.add_node("b", "agent")

        RHS = TypedDiGraph()
        RHS.add_node("x", "agent")

        h1 = Homomorphism(
            P, LHS, {"a": 1, "b": 2})
        h2 = Homomorphism(
            P, RHS, {"a": "x", "b": "x"})

        rw = Rewriter(g)
        instances = rw.find_matching(LHS)
        RHS_instance = rw.apply_rule(
            instances[0],
            h1, h2)
