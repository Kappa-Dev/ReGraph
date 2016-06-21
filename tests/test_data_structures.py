"""Test data structures of graph rewriting."""

import os

from nose.tools import assert_equals
from nose.tools import raises

from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import TypedGraph
from regraph.library.data_structures import Homomorphism
from regraph.library.data_structures import TypedHomomorphism

def assert_edges_undir(edges1, edges2):

    edgeset1 = set(edges1)
    edgeset2 = set(edges2)

    for edge in edgeset1:
        if edge not in edgeset2 and (edge[1], edge[0]) not in edgeset2:
            assert False

class TestDataStructures(object):
    """Class for testing data structures with Python nose tests."""

    def __init__(self):
        self.graph_ = TypedDiGraph()
        self.graph_.add_node('1', 'agent',
                             {'name': 'EGFR', 'state': 'p'})
        self.graph_.add_node('2', 'action', attrs={'name': 'BND'})
        self.graph_.add_node('3', 'agent',
                             {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        self.graph_.add_node('4', 'region', attrs={'name': 'SH2'})
        self.graph_.add_node('5', 'agent', attrs={'name': 'EGFR'})
        self.graph_.add_node('6', 'action', attrs={'name': 'BND'})
        self.graph_.add_node('7', 'agent', attrs={'name': 'Grb2'})

        self.graph_.add_node('8', 'agent', attrs={'name': 'WAF1'})
        self.graph_.add_node('9', 'action', {'name': 'BND'})
        self.graph_.add_node('10', 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

        self.graph_.add_node('11', 'agent')
        self.graph_.add_node('12', 'agent')
        self.graph_.add_node('13', 'agent')

        edges = [
            ('1', '2'),
            ('4', '2'),
            ('4', '3'),
            ('5', '6'),
            ('7', '6'),
            ('8', '9'),
            ('10', '9'),
            ('11', '12'),
            ('12', '11'),
            ('12', '13'),
            ('13', '12'),
            ('11', '13'),
            ('13', '11'),
            ('5', '2')
        ]

        self.graph_.add_edges_from(edges)

        # later you can add some attributes to the edge

        self.graph_.set_edge('1', '2', {'s': 'p'})
        self.graph_.set_edge('4', '2', {'s': 'u'})
        self.graph_.set_edge('5', '6', {'s': 'p'})
        self.graph_.set_edge('7', '6', {'s': 'u'})
        self.graph_.set_edge('5', '2', {'s': 'u'})

        self.LHS_ = TypedDiGraph()

        self.LHS_.add_node('1', 'agent', {'name': 'EGFR'})
        self.LHS_.add_node('2', 'action', {'name': 'BND'})
        self.LHS_.add_node('3', 'region')
        self.LHS_.add_node('4', 'agent', {'name': 'Grb2'})
        self.LHS_.add_node('5', 'agent', {'name': 'EGFR'})
        self.LHS_.add_node('6', 'action', {'name': 'BND'})
        self.LHS_.add_node('7', 'agent', {'name': 'Grb2'})

        self.LHS_.add_edges_from([('1', '2'), ('3', '2'), ('3', '4'), ('5', '6'), ('7', '6')])

        self.LHS_.set_edge('1', '2', {'s': 'p'})
        self.LHS_.set_edge('5', '6', {'s': 'p'})

    def test_homorphism_init(self):
        # Test homomorphisms functionality
        mapping = {'1': '1',
                   '2': '2',
                   '3': '4',
                   '4': '3',
                   '5': '5',
                   '6': '6',
                   '7': '7'}
        Homomorphism(self.LHS_, self.graph_, mapping)

    @raises(ValueError)
    def test_homomorphism_not_covered(self):
        mapping = {'1': '1',
                   '2': '2',
                   '3': '4',
                   '4': '3',
                   '5': '5',
                   '6': '6'}
        Homomorphism(self.LHS_, self.graph_, mapping)

    @raises(ValueError)
    def test_homomorphism_type_mismatch(self):
        mapping = {'1': '1',
                   '2': '2',
                   '3': '4',
                   '4': '3',
                   '5': '5',
                   '6': '6',
                   '7': '7'}
        self.LHS_.cast_node('1', 'other_type')
        TypedHomomorphism(self.LHS_, self.graph_, mapping)

    @raises(ValueError)
    def test_homomorphism_attributes_mismatch(self):
        mapping = {'1': '1',
                   '2': '2',
                   '3': '4',
                   '4': '3',
                   '5': '5',
                   '6': '6',
                   '7': '7'}
        self.LHS_.add_node_attrs(1,{'new_attr': 0})
        TypedHomomorphism(self.LHS_, self.graph_, mapping)

    @raises(ValueError)
    def test_homomorphism_connectivity_fails(self):
        mapping = {'1': '1',
                   '2': '2',
                   '3': '4',
                   '4': '3',
                   '5': '5',
                   '6': '6',
                   '7': '7'}
        self.graph_.remove_edge('4', '5')
        Homomorphism(self.LHS_, self.graph_, mapping)

    @raises(ValueError)
    def test_homomorphism_edge_attributes_mismatch(self):
        mapping = {'1': '1',
                   '2': '2',
                   '3': '4',
                   '4': '3',
                   '5': '5',
                   '6': '6',
                   '7': '7'}
        self.LHS_.add_edge_attrs('5', '6', {'new_attr': 0})
        TypedHomomorphism(self.LHS_, self.graph_, mapping)

    def test_homomorphism(self):
        new_pattern = TypedDiGraph()
        new_pattern.add_node('34', "agent")
        new_pattern.add_node('35', "agent")
        new_pattern.add_node('36', "action")
        new_pattern.add_edges_from([('34', '36'), ('35', '36')])
        mapping = {'34': '5',
                   '35': '5',
                   '36': '6'}
        h = Homomorphism(new_pattern, self.graph_, mapping)
        assert_equals(h.is_monic(), False)

    def test_init_with_metamodel_directed(self):
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
            ('1', "protein"),
            ('2', "region"),
            ('3', "action"),
            ('4', "region"),
            ('5', "protein"),
            ('6', "region"),
            ('7', "protein")])
        graph.add_edge('2', '1')
        graph.add_edge('2', '3')
        graph.add_edge('4', '3')
        graph.add_edge('4', '5')
        graph.add_edge('6', '3')
        graph.add_edge('6', '7')

    def test_init_with_metamodel_undirected(self):
        meta_meta = TypedGraph()
        meta_meta.add_node("agent", "node")
        meta_meta.add_node("action", "node")
        meta_meta.add_edges_from([
            ("agent", "agent"),
            ("action", "action"),
            ("action", "agent")])

        meta = TypedGraph(meta_meta)
        meta.add_node("protein", "agent")
        meta.add_node("region", "agent")
        meta.add_node("action", "agent")
        meta.add_edges_from([
            ("protein", "protein", {'a': 1}),
            ("region", "region"),
            ("action", "action"),
            ("protein", "region", {'a': 2}),
            ("action", "region"),
        ])
        assert_equals(
            meta.edge["protein"]["region"],
            meta.edge["region"]["protein"])

        graph = TypedGraph(meta)
        graph.add_nodes_from([
            ('1', "protein"),
            ('2', "region"),
            ('3', "action"),
            ('4', "region"),
            ('5', "protein"),
            ('6', "region"),
            ('7', "protein")])
        graph.add_edge('2', '1', {'x': 1})
        graph.add_edge('2', '3', {'x': 2})
        graph.add_edge('4', '3', {'x': 3})
        graph.add_edge('4', '5', {'x': 4})
        graph.add_edge('6', '3', {'x': 5})
        graph.add_edge('6', '7', {'x': 6})
        assert_equals(graph.edge['1']['2'], graph.edge['2']['1'])

    def test_load_graph_dir(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        filename = os.path.join(__location__, "graph_example.json")
        a = TypedDiGraph()
        a.load(filename)

        assert_equals(a.nodes(), [1, 2, 3])
        assert_equals(a.edges(), [(1, 2), (2, 3), (3, 1)])
        assert_equals(a.node[1].type_, "agent")
        assert_equals(a.node[2].type_, "agent")
        assert_equals(a.node[3].type_, "action")
        assert_equals(a.node[1].attrs_, {"u": {1}, "k": {33}})
        assert_equals(a.node[2].attrs_, None)
        assert_equals(a.node[3].attrs_, {"x": {33, 55, 66}})

    def test_load_graph_undir(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        filename = os.path.join(__location__, "graph_example.json")
        a = TypedGraph()
        a.load(filename)

        assert_equals(a.nodes(), [1, 2, 3])
        assert_edges_undir(a.edges(), [(1, 2), (2, 3), (3, 1)])
        assert_equals(a.node[1].type_, "agent")
        assert_equals(a.node[2].type_, "agent")
        assert_equals(a.node[3].type_, "action")
        assert_equals(a.node[1].attrs_, {"u": {1}, "k": {33}})
        assert_equals(a.node[2].attrs_, None)
        assert_equals(a.node[3].attrs_, {"x": {33, 55, 66}})

    def test_load_export(self):
        __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        filename = os.path.join(__location__, "graph_example.json")
        a = TypedGraph()
        a.load(filename)
        out_filename = os.path.join(__location__, "output_graph.json")
        a.export(out_filename)
        b = TypedGraph()
        b.load(out_filename)

        assert_equals(a.nodes(), b.nodes())
        assert_edges_undir(a.edges(), b.edges())
        assert_equals(a.node[3].attrs_, b.node[3].attrs_)
