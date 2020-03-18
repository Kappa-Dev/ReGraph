import copy

from regraph import Rule, NXGraph
from regraph.utils import (valid_attributes,
                           normalize_attrs)
from regraph.category_utils import identity
from regraph.primitives import *


class TestPrimitives(object):

    def __init__(self):
        self.graph = NXGraph()
        add_node(self.graph, '1', {'name': 'EGFR', 'state': 'p'})
        add_node(self.graph, '2', {'name': 'BND'})
        add_node(self.graph, '3', {'name': 'Grb2', 'aa': 'S', 'loc': 90})
        add_node(self.graph, '4', {'name': 'SH2'})
        add_node(self.graph, '5', {'name': 'EGFR'})
        add_node(self.graph, '6', {'name': 'BND'})
        add_node(self.graph, '7', {'name': 'Grb2'})
        add_node(self.graph, '8', {'name': 'WAF1'})
        add_node(self.graph, '9', {'name': 'BND'})
        add_node(self.graph, '10', {'name': 'G1-S/CDK', 'state': 'p'})
        add_node(self.graph, '11')
        add_node(self.graph, '12')
        add_node(self.graph, '13')

        edges = [
            ('1', '2', {'s': 'p'}),
            ('4', '2', {'s': 'u'}),
            ('4', '3'),
            ('5', '6', {'s': 'p'}),
            ('7', '6', {'s': 'u'}),
            ('8', '9'),
            ('9', '8'),
            ('10', '8', {"a": {1}}),
            ('10', '9', {"a": {2}}),
            ('11', '12'),
            ('12', '11'),
            ('12', '13'),
            ('13', '12'),
            ('11', '13'),
            ('13', '11'),
            ('5', '2', {'s': 'u'})
        ]

        add_edges_from(self.graph, edges)

    def test_add_node(self):
        attrs = {"a": {1}}
        add_node(self.graph, "a", attrs)
        assert("a" in self.graph.nodes())
        normalize_attrs(attrs)
        assert(self.graph.node["a"] == attrs)
        assert(id(attrs) != id(self.graph.node["a"]))

    def test_remove_node(self):
        try:
            remove_node(self.graph, "b")
            raise ValueError()
        except:
            pass
        node_to_remove = '13'
        in_edges = list(self.graph.in_edges(node_to_remove))
        out_edges = list(self.graph.out_edges(node_to_remove))
        remove_node(self.graph, node_to_remove)
        assert(node_to_remove not in self.graph.nodes())
        for edge in in_edges + out_edges:
            assert(edge not in self.graph.edges())

    def test_add_edge(self):
        try:
            add_edge(self.graph, '1', '2')
            raise ValueError("")
        except:
            pass

        s = '1'
        t = '5'
        attrs = {"a": {1}}
        add_edge(self.graph, s, t, attrs)
        normalize_attrs(attrs)
        assert((s, t) in self.graph.edges())
        assert(self.graph.adj[s][t] == attrs)
        assert(id(self.graph.adj[s][t]) != id(attrs))

    def test_remove_edge(self):
        # g = self.graph.to_undirected()

        remove_edge(self.graph, '11', '12')
        assert(('11', '12') not in self.graph.nodes())

    def test_update_node_attrs(self):
        new_attr = {"b": {1}}
        add_node_attrs(self.graph, '1', new_attr)
        assert(id(self.graph.node['1']) != id(new_attr))

    def test_clone_node(self):
        node_to_clone = '1'

        in_edges = self.graph.in_edges(node_to_clone)
        out_edges = self.graph.out_edges(node_to_clone)

        new_name = clone_node(self.graph, node_to_clone)

        assert(new_name in self.graph.nodes())
        assert(self.graph.node[new_name] == self.graph.node[node_to_clone])
        assert(
            id(self.graph.node[new_name]) !=
            id(self.graph.node[node_to_clone])
        )
        for u, _ in in_edges:
            assert((u, new_name) in self.graph.edges())
            assert(
                self.graph.adj[u][node_to_clone] ==
                self.graph.adj[u][new_name]
            )
            assert(
                id(self.graph.adj[u][node_to_clone]) !=
                id(self.graph.adj[u][new_name])
            )
        for _, v in out_edges:
            assert((new_name, v) in self.graph.edges())

    def test_clone_node_undirected(self):
        g = self.graph
        node_to_clone = '1'
        new_name = 'a'
        new_node = clone_node(g, node_to_clone, new_name)
        assert(new_name in g.nodes())
        assert(g.node[new_name] == self.graph.node[node_to_clone])
        assert(id(g.node[new_name]) != id(self.graph.node[node_to_clone]))

    def test_merge_nodes(self):
        g = self.graph

        old_attrs1 = self.graph.node['8']
        old_attrs2 = self.graph.node['9']
        old_edge_attrs1 = self.graph.adj['10']['8']
        old_edge_attrs2 = self.graph.adj['10']['9']
        new_name = merge_nodes(self.graph, ["8", "9"])
        assert(new_name in self.graph.nodes())
        assert("8" not in self.graph.nodes())
        assert("9" not in self.graph.nodes())
        assert(valid_attributes(old_attrs1, self.graph.node[new_name]))
        assert(valid_attributes(old_attrs2, self.graph.node[new_name]))
        assert((new_name, new_name) in self.graph.edges())
        assert(valid_attributes(old_edge_attrs1, self.graph.adj['10'][new_name]))
        assert(valid_attributes(old_edge_attrs2, self.graph.adj['10'][new_name]))

    def test_relabel_node(self):
        g = self.graph
        relabel_node(g, '1', 'a')
        assert('1' not in g.nodes())
        assert('a' in g.nodes())

    def test_subtract(self):
        g = copy.deepcopy(self.graph)
        remove_node(g, '1')
        remove_node(g, '4')
        remove_node(g, '2')
        sub_graph = subtract(self.graph, g, identity(g, self.graph))
        assert('1' in sub_graph.nodes())
        assert(('4', '2') in sub_graph.edges())

    def test_append_to_node_names(self):
        g = copy.deepcopy(self.graph)
        mapping = dict((str(n) + '_lala', n) for n in g.nodes())
        append_to_node_names(g, 'lala')
        relabel_nodes(g, mapping)
        assert(set(g.nodes()) == set(self.graph.nodes()))

    # def test_from_json_like(self):
    #     pass

    # def test_to_json_like(self):
    #     pass

    def test_load_export(self):
        g1 = load_networkx_graph("tests/graph_example.json")
        export_graph(g1, "tests/graph_output.json")
        g2 = load_networkx_graph("tests/graph_output.json")
        assert(set(g1.nodes()) == set(g2.nodes()))
        assert(set(g1.edges()) == set(g2.edges()))

    def test_find_matching(self):
        pattern = NXGraph()
        add_nodes_from(pattern,
            [(1, {'state': 'p'}),
             (2, {'name': 'BND'}),
             (3),
             (4)]
        )
        add_edges_from(pattern,
            [(1, 2, {'s': 'p'}),
             (3, 2, {'s': 'u'}),
             (3, 4)]
        )
        find_matching(self.graph, pattern)
        # assert smth here

    def test_rewrite(self):
        pattern = NXGraph()
        add_nodes_from(pattern,
            [(1, {'state': 'p'}),
             (2, {'name': 'BND'}),
             3,
             4]
        )
        add_edges_from(pattern,
            [(1, 2, {'s': 'p'}),
             (3, 2, {'s': 'u'}),
             (3, 4)]
        )

        p = NXGraph()
        add_nodes_from(p, [
            (1, {'state': 'p'}),
            (2, {'name': 'BND'}),
            3,
            4
        ])
        p.add_edges_from([
            (1, 2),
            (3, 4)
        ])

        rhs = NXGraph()
        add_nodes_from(rhs, [
            (1, {'state': 'p'}),
            (2, {'name': 'BND'}),
            (3, {'merged': 'yes'}),
            (4, {'new': 'yes'})
        ])

        add_edges_from(rhs, [
            (1, 2, {'s': 'u'}),
            (2, 4),
            (3, 3),
            (3, 4, {'from': 'merged'})
        ])

        p_lhs = {1: 1, 2: 2, 3: 3, 4: 4}
        p_rhs = {1: 1, 2: 2, 3: 3, 4: 3}

        rule = Rule(p, pattern, rhs, p_lhs, p_rhs)
        # instances = find_matching_with_types(self.graph, rule.lhs, {}, {}, {})
        instances = self.graph.find_matching(rule.lhs)
        self.graph.rewrite(rule, instances[0])
