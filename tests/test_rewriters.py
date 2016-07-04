"""."""
import os

from nose.tools import assert_equals
from nose.tools import raises

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import (Rewriter,
                                       Transformer)
from regraph.library.utils import (merge_attributes,
                                   plot_graph)


class TestRewrites(object):
    """."""

    def __init__(self):
        self.graph = TypedDiGraph()
        self.graph.add_node(1, 'agent',
                          {'name': 'EGFR', 'state': 'p'})
        self.graph.add_node(2, 'action', attrs={'name': 'BND'})
        self.graph.add_node(3, 'agent',
                          {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        self.graph.add_node(4, 'region', attrs={'name': 'SH2'})
        self.graph.add_node(5, 'agent', attrs={'name': 'EGFR'})
        self.graph.add_node(6, 'action', attrs={'name': 'BND'})
        self.graph.add_node(7, 'agent', attrs={'name': 'Grb2'})

        self.graph.add_node(8, 'agent', attrs={'name': 'WAF1'})
        self.graph.add_node(9, 'action', {'name': 'BND'})
        self.graph.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

        self.graph.add_node(11, 'agent')
        self.graph.add_node(12, 'agent')
        self.graph.add_node(13, 'agent')
        self.graph.add_node(14, 'agent')

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
            (13, 14),
            (5, 2)
        ]

        self.graph.add_edges_from(edges)

        self.graph.set_edge(1, 2, {'s': 'p'})
        self.graph.set_edge(4, 2, {'s': 'u'})
        self.graph.set_edge(5, 6, {'s': 'p'})
        self.graph.set_edge(7, 6, {'s': 'u'})
        self.graph.set_edge(5, 2, {'s': 'u'})

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

        self.rw_ = Rewriter(self.graph)
        self.instances_ = Rewriter.find_matching(self.graph, self.LHS_)

    def test_add_node(self):
        trans = Transformer(self.graph.copy())

        trans.add_node(15, 'agent', {'name' : 'Grb3'})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(15 in Gprime.nodes())
        assert(Gprime.node[15].type_ == 'agent')
        assert(Gprime.node[15].attrs_ == {'name' : {'Grb3'}})

    def test_merge_nodes(self):
        trans = Transformer(self.graph.copy())

        trans.merge_nodes(1, 3, 15)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(15 in Gprime.nodes())
        assert(Gprime.node[15].type_ == 'agent')
        assert(Gprime.node[15].attrs_ ==
               merge_attributes(self.graph.node[1].attrs_,
                                self.graph.node[3].attrs_))

    def test_remove_node(self):
        trans = Transformer(self.graph.copy())

        trans.remove_node(1)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(1 not in Gprime.nodes())

    def test_clone_node(self):
        trans = Transformer(self.graph.copy())

        trans.clone_node(1, 111)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(1 in Gprime.nodes())
        assert(111 in Gprime.nodes())
        assert(Gprime.node[1].type_ == Gprime.node[111].type_)
        assert(Gprime.node[1].attrs_ == Gprime.node[111].attrs_)

    def test_add_edge(self):
        trans = Transformer(self.graph.copy())

        trans.add_edge(8, 10)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert((8,10) in Gprime.edges())

    def test_remove_edge(self):
        trans = Transformer(self.graph.copy())

        trans.remove_edge(13, 11)


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert((13,11) not in Gprime.edges())

    def test_add_node_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.add_node_attrs(1, {'name' : {'Grb1'}})

        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)
        assert(Gprime.node[1].attrs_ == {'name': {'EGFR','Grb1'}, 'state': {'p'}})

    def test_add_edge_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.add_edge_attrs(1, 2, {'name' : 'Grb1'})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(Gprime.get_edge(1, 2) ==  {'s': {'p'}, 'name' : {'Grb1'}})

    def test_remove_node_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.remove_node_attrs(1, {'name' : {'EGFR'}})


        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(Gprime.node[1].attrs_ ==  {'state': {'p'}, 'name' : set()})

    def test_remove_edge_attrs(self):
        trans = Transformer(self.graph.copy())

        trans.remove_edge_attrs(1, 2, {'s' : 'p'})

        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)
        
        assert(Gprime.get_edge(1, 2) == {'s': set()} or\
               Gprime.get_edge(1, 2) == {})

    def test_merge_edges(self):
        trans = Transformer(self.graph.copy())

        trans.merge_edges((11,12),(13,14), 15, 16)

        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(15 in Gprime.nodes())
        assert(16 in Gprime.nodes())
        assert((15,16) in Gprime.edges())

    def test_clone_edge(self):
        trans = Transformer(self.graph.copy())

        trans.clone_edge(11, 12, 15, 16)

        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(15 in Gprime.nodes())
        assert(16 in Gprime.nodes())
        assert((15,16) in Gprime.edges())

    def test_merge_nodes_list(self):
        trans = Transformer(self.graph.copy())

        trans.merge_nodes_list([11,12,13,14], 15)

        Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

        assert(15 in Gprime.nodes())

    def test_multiple_rewrites(self):


        trans = Transformer(self.graph.copy())

        trans.add_node(15, 'action', {'name' : 'BND'})
        trans.remove_node(2)
        trans.clone_node(4, 16)
        trans.merge_nodes(11, 12)

        instance = Homomorphism.identity(trans.L, trans.G)
        Rewriter.rewrite(instance, trans)

    def test_find_matching(self):
        assert_equals(self.instances_, [{1: 1, 2: 2, 3: 4, 4: 3, 5: 5, 6: 6, 7: 7}])

        new_pattern = TypedDiGraph()
        new_pattern.add_node("a", "agent")
        new_pattern.add_node("b", "agent")
        new_pattern.add_node("c", "agent")

        new_pattern.add_edges_from([("a", "b"), ("a", "c")])

        graph = self.graph.copy()
        graph.remove_node(14)

        instances = Rewriter.find_matching(graph, new_pattern)
        assert_equals(6, len(instances))

    def test_transformer_from_command(self):
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
        g.set_edge(1, 2, {"a": {0}})
        g.set_edge(2, 3, {"k": {1, 2, 3}})

        rw = Rewriter(g)

        trans_list = Rewriter.make_canonical_commands(g,
            """delete_node 1.
            clone 2 as 'clone'.
            delete_node_attrs 'clone' {'u': 0}.
            delete_edge 2 3.
            delete_edge_attrs 'clone' 3 {'k': {1}}.
            merge ['clone', 3] as 'merged'.
            add_node_attrs 'merged' {'m': 1}.
            add_node 'new_node' type 'region'.
            add_node_attrs 'new_node' {'x': 1}.
            add_edge 'new_node' 'merged'.
            add_edge_attrs 'merged' 'new_node' {'j': 33}."""
        )

        for i in range(len(trans_list)):
            g = rw.graph_
            trans = Rewriter.transformer_from_command(g, trans_list[i])

            h1,h2 = trans.get()
            instances = Rewriter.find_matching(g, trans.L)

            instance = Homomorphism(trans.L, g, instances[0])

            rw.graph_ = Rewriter.rewrite(instance, trans)

            plot_graph(
                rw.graph_,
                filename=os.path.join(__location__, "undir_rule_to_hom_RHS.png"))

            rw = Rewriter(rw.graph_)

    def test_rewriting_with_metamodel(self):
        meta_meta = TypedDiGraph()
        meta_meta.add_node("agent", "node")
        meta_meta.add_node("action", "node")
        meta_meta.add_edges_from([
            ("agent", "agent"),
            ("action", "action"),
            ("action", "agent"),
            ("agent", "action")])

        meta = TypedDiGraph(meta_meta)
        meta.add_node("protein", "agent")
        meta.add_node("region", "agent")
        meta.add_node("action", "agent")
        meta.add_edges_from([
            ("protein", "protein"),
            ("region", "region"),
            ("action", "action"),
            ("region", "protein"),
            ("region", "action"),
            ("action", "region"),
        ])

        graph = TypedDiGraph(meta)
        graph.add_nodes_from([
            (1, "protein"),
            (2, "region"),
            (3, "action"),
            (4, "region"),
            (5, "protein"),
            (6, "region"),
            (7, "protein")])
        graph.add_edge(2, 1)
        graph.add_edge(2, 3)
        graph.add_edge(4, 3)
        graph.add_edge(4, 5)
        graph.add_edge(6, 3)
        graph.add_edge(6, 7)

        rw = Rewriter(graph)

        LHS = TypedDiGraph()
        LHS.add_node("a", "protein")
        LHS.add_node("b", "region")
        LHS.add_node(33, "action")
        LHS.add_edges_from([
            ("b", "a"),
            ("b", 33)])
        instances = Rewriter.find_matching(graph, LHS)

        try:
            trans = Transformer(graph)
            trans.add_node("new_type", 2)
            Rewriter.rewrite(instances[0], trans)
            assert False
        except:
            assert True
        try:
            trans = Transformer(graph)
            trans.add_edge("a", 33)
            Rewriter.rewrite(instances[0], trans)
            assert False
        except:
            assert True
