import networkx as nx

from regraph.atset import to_atset
from regraph.rules import Rule
from regraph.utils import (dict_sub,
                           valid_attributes,
                           normalize_attrs,
                           is_subdict)
from regraph.category_op import identity
from regraph.primitives import *
import regraph.primitives as prim


class TestPrimitives(object):

    def __init__(self):
        self.graph = nx.DiGraph()
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
        in_edges = self.graph.in_edges(node_to_remove)
        out_edges = self.graph.out_edges(node_to_remove)
        remove_node(self.graph, node_to_remove)
        assert(node_to_remove not in self.graph.nodes())
        for edge in in_edges + out_edges:
            assert(edge not in self.graph.edges())

    def test_remove_node_undirected(self):
        g = self.graph.to_undirected()

        node_to_remove = '12'
        neighbors = g.neighbors(node_to_remove)
        remove_node(g, node_to_remove)
        assert(node_to_remove not in g.nodes())
        for n in neighbors:
            assert((n, node_to_remove) not in g.edges())
            assert((node_to_remove, n) not in g.edges())

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
        assert(self.graph.edge[s][t] == attrs)
        assert(id(self.graph.edge[s][t]) != id(attrs))

    def test_add_edge_undirected(self):
        g = self.graph.to_undirected()
        try:
            add_edge(g, '1', '2')
            raise ValueError("")
        except:
            pass

        s = '1'
        t = '5'
        attrs = {'a': FiniteSet(1)}
        add_edge(g, s, t, attrs)
        assert((s, t) in g.edges() or (t, s) in g.edges())
        attrs = {'a': FiniteSet({1})}
        assert(g.edge[s][t] == attrs)
        assert(g.edge[t][s] == attrs)
        assert(id(g.edge[s][t]) != id(attrs) and id(g.edge[t][s]) != id(attrs))
        assert(id(g.edge[s][t]) == id(g.edge[t][s]))

    def test_remove_edge(self):
        g = self.graph.to_undirected()

        remove_edge(self.graph, '11', '12')
        assert(('11', '12') not in self.graph.nodes())

        # try with undirected
        remove_edge(g, '11', '12')
        assert(('11', '12') not in self.graph.nodes())
        assert(('12', '11') not in self.graph.nodes())

    def test_update_node_attrs(self):
        new_attr = {"b": {1}}
        add_node_attrs(self.graph, '1', new_attr)
        assert(id(self.graph.node['1']) != id(new_attr))

    def test_add_edge_attrs(self):
        g = self.graph.to_undirected()
        new_attrs = {"b": FiniteSet({1})}
        add_edge_attrs(g, '1', '2', new_attrs)
        normalize_attrs(new_attrs)
        assert(valid_attributes(new_attrs, g.edge['1']['2']))
        assert(valid_attributes(new_attrs, g.edge['2']['1']))

    def test_remove_edge_attrs(self):
        g = self.graph.to_undirected()
        attrs = {"s": FiniteSet({"p"})}
        remove_edge_attrs(g, '1', '2', attrs)
        assert(not valid_attributes(attrs, g.edge['1']['2']))
        assert(not valid_attributes(attrs, g.edge['2']['1']))

    def test_update_edge_attrs(self):
        g = self.graph.to_undirected()
        attrs = {"b": FiniteSet({1})}
        update_edge_attrs(g, '1', '2', attrs)
        assert(id(g.edge['1']['2']) != id(attrs))
        assert(id(g.edge['2']['1']) == id(g.edge['1']['2']))

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
                self.graph.edge[u][node_to_clone] ==
                self.graph.edge[u][new_name]
            )
            assert(
                id(self.graph.edge[u][node_to_clone]) !=
                id(self.graph.edge[u][new_name])
            )
        for _, v in out_edges:
            assert((new_name, v) in self.graph.edges())

    def test_clone_node_undirected(self):
        g = self.graph.to_undirected()
        node_to_clone = '1'
        neighbors = g.neighbors(node_to_clone)
        new_name = 'a'
        clone_node(g, node_to_clone, new_name)
        assert(new_name in g.nodes())
        assert(g.node[new_name] == self.graph.node[node_to_clone])
        assert(id(g.node[new_name]) != id(self.graph.node[node_to_clone]))
        for n in neighbors:
            assert((n, new_name) in g.edges() or (new_name, n) in g.edges())
            assert(g.edge[n][new_name] == g.edge[new_name][n])
            assert(id(g.edge[n][new_name]) == id(g.edge[new_name][n]))

            assert(g.edge[n][new_name] == g.edge[n][node_to_clone])
            assert(id(g.edge[n][new_name]) != id(g.edge[n][node_to_clone]))

    def test_merge_nodes(self):
        g = self.graph.to_undirected()

        old_attrs1 = self.graph.node['8']
        old_attrs2 = self.graph.node['9']
        old_edge_attrs1 = self.graph.edge['10']['8']
        old_edge_attrs2 = self.graph.edge['10']['9']
        new_name = merge_nodes(self.graph, ["8", "9"])
        assert(new_name in self.graph.nodes())
        assert("8" not in self.graph.nodes())
        assert("9" not in self.graph.nodes())
        assert(valid_attributes(old_attrs1, self.graph.node[new_name]))
        assert(valid_attributes(old_attrs2, self.graph.node[new_name]))
        assert((new_name, new_name) in self.graph.edges())
        assert(valid_attributes(old_edge_attrs1, self.graph.edge['10'][new_name]))
        assert(valid_attributes(old_edge_attrs2, self.graph.edge['10'][new_name]))

        # test undirected case
        old_attrs1 = g.node['8']
        old_attrs2 = g.node['9']
        old_edge_attrs1 = g.edge['10']['8']
        old_edge_attrs2 = g.edge['10']['9']
        new_name = merge_nodes(g, ["8", "9"])
        assert(new_name in g.nodes())
        assert("8" not in g.nodes())
        assert("9" not in g.nodes())
        assert(valid_attributes(old_attrs1, g.node[new_name]))
        assert(valid_attributes(old_attrs2, g.node[new_name]))
        assert((new_name, new_name) in g.edges())
        assert(valid_attributes(old_edge_attrs1, g.edge['10'][new_name]))
        assert(valid_attributes(old_edge_attrs1, g.edge[new_name]['10']))
        assert(valid_attributes(old_edge_attrs2, g.edge['10'][new_name]))
        assert(valid_attributes(old_edge_attrs2, g.edge[new_name]['10']))
        assert(g.edge['10'][new_name] == g.edge[new_name]['10'])
        assert(id(g.edge['10'][new_name]) == id(g.edge[new_name]['10']))

    def test_set_edge(self):
        g = self.graph.to_undirected()
        old_edge = g.edge['6']['7']
        set_edge(g, '6', '7', {'a': 'b'})
        assert(id(old_edge) != id(g.edge['6']['7']))
        assert(id(g.edge['6']['7']) == id(g.edge['7']['6']))

    def test_relabel_node(self):
        g = self.graph.to_undirected()
        relabel_node(g, '1', 'a')
        assert('1' not in g.nodes())
        assert('a' in g.nodes())

    def test_subtract(self):
        g = deepcopy(self.graph)
        remove_node(g, '1')
        remove_node(g, '4')
        remove_node(g, '2')
        sub_graph = subtract(self.graph, g, identity(g, self.graph))
        assert('1' in sub_graph.nodes())
        assert(('4', '2') in sub_graph.edges())

    def test_append_to_node_names(self):
        g = deepcopy(self.graph)
        mapping = dict((str(n) + '_lala', n) for n in g.nodes())
        append_to_node_names(g, 'lala')
        relabel_nodes(g, mapping)
        assert(set(g.nodes()) == set(self.graph.nodes()))

    # def test_from_json_like(self):
    #     pass

    # def test_to_json_like(self):
    #     pass

    def test_load_export(self):
        g1 = load_graph("tests/graph_example.json")
        export_graph(g1, "tests/graph_output.json")
        g2 = load_graph("tests/graph_output.json")
        assert(set(g1.nodes()) == set(g2.nodes()))
        assert(set(g1.edges()) == set(g2.edges()))

    def test_find_matching(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern,
            [(1, {'state': 'p'}),
             (2, {'name': 'BND'}),
             (3),
             (4)]
        )
        prim.add_edges_from(pattern,
            [(1, 2, {'s': 'p'}),
             (3, 2, {'s': 'u'}),
             (3, 4)]
        )
        find_matching(self.graph, pattern)
        # assert smth here

    def test_rewrite(self):
        pattern = nx.DiGraph()
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

        p = nx.DiGraph()
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

        rhs = nx.DiGraph()
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
        instances = find_matching_with_types(self.graph, rule.lhs, {}, {}, {})
        rule.apply_to(self.graph, instances[0], rule)
        # print_graph(self.graph)
