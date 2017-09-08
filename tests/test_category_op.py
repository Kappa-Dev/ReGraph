import networkx as nx


from nose.tools import assert_equals

from regraph.primitives import (get_relabeled_graph,
                                print_graph)
from regraph.utils import assert_graph_eq
from regraph.category_op import (pullback,
                                 pushout,
                                 pullback_complement,
                                 nary_pullback)


def assert_edges_undir(edges1, edges2):

    edgeset1 = set(edges1)
    edgeset2 = set(edges2)

    for edge in edgeset1:
        if edge not in edgeset2 and (edge[1], edge[0]) not in edgeset2:
            assert False


class TestCategoryOp:
    def __init__(self):
        D = nx.DiGraph()

        D.add_node('square')
        D.add_node('circle')
        D.add_node('dark_square')
        D.add_node('dark_circle')
        D.add_edge('square', 'circle')
        D.add_edge('circle', 'dark_circle')
        D.add_edge('circle', 'dark_square')
        D.add_edge('circle', 'circle')

        self.D = D

        A = nx.DiGraph()

        A.add_node(2)
        A.add_node(3)
        A.add_edge(2, 3)

        self.A = A

        B = nx.DiGraph()

        B.add_node(1)
        B.add_node(2)
        B.add_node(3)
        B.add_edge(1, 2)
        B.add_edge(2, 3)

        self.B = B

        C = nx.DiGraph()

        C.add_node(2)
        C.add_node(3)
        C.add_node('dark_square')

        C.add_edge(2, 3)
        C.add_edge(2, 'dark_square')
        C.add_edge(2, 2)

        self.C = C

        self.homAB = {
            2: 2,
            3: 3
        }
        self.homAC = {
            2: 2,
            3: 3
        }
        self.homBD = {
            1: 'square',
            2: 'circle',
            3: 'dark_circle'
        }

        self.homCD = {
            2: 'circle',
            3: 'dark_circle',
            'dark_square': 'dark_square'
        }

    def test_pullback(self):
        A, homAB, homAC = pullback(
            self.B, self.C, self.D, self.homBD, self.homCD
        )
        assert_equals(type(A), nx.DiGraph)
        assert_equals(set(A.nodes()), set(self.A.nodes()))
        assert_edges_undir(A.edges(), self.A.edges())
        assert_equals(homAB, self.homAB)
        assert_equals(homAC, self.homAC)

    def test_pullback_complement(self):
        C, homAC, homCD = pullback_complement(
            self.A, self.B, self.D, self.homAB, self.homBD
        )
        assert_equals(type(C), nx.DiGraph)
        test_graph = get_relabeled_graph(
            self.C, {2: "circle", 3: "dark_circle", "dark_square": "dark_square"}
        )
        assert_graph_eq(test_graph, C)

    def test_pushout(self):
        D, homBD, homCD = pushout(
            self.A, self.B, self.C, self.homAB, self.homAC
        )
        assert_equals(type(D), nx.DiGraph)

        assert_equals(len(D.nodes()),
                      len(self.D.nodes()))

        assert_equals(len(D.edges()),
                      len(self.D.edges()))

    def test_pushout_symmetry_directed(self):

        A = nx.DiGraph()
        A.add_nodes_from(["a", "b"])
        A.add_edges_from([("a", "b")])

        B = nx.DiGraph()
        B.add_nodes_from([1, 2, 3])
        B.add_edges_from([(2, 3), (3, 2), (1, 3)])

        C = nx.DiGraph()
        C.add_nodes_from(["x", "y"])
        C.add_edges_from([("x", "x"), ("x", "y")])

        homAB = {"a": 2, "b": 3}
        homAC = {"a": "x", "b": "x"}

        D, homBD, homCD = pushout(
            A, B, C, homAB, homAC
        )
        D_inv, homCD_inv, homBD_inv = pushout(
            A, C, B, homAC, homAB
        )

        # print("\n\n\n\n\n\n\n")
        # print_graph(D)
        # print_graph(D_inv)
        # print(homBD, homBD_inv)
        # print(homCD, homCD_inv)
        # print("\n\n\n\n\n\n\n")

    def test_multi_pullback(self):
        B = nx.DiGraph()
        B.add_nodes_from([
            1,
            2,
            3,
            4,
            5
        ])
        B.add_edges_from([
            (1, 3),
            (2, 2),
            (3, 2),
            (4, 5),
            (5, 4)
        ])

        D1 = nx.DiGraph()
        D1.add_nodes_from(['c', 's'])
        D1.add_edges_from([('c', 's'), ('s', 'c'), ('c', 'c')])

        D2 = nx.DiGraph()
        D2.add_nodes_from(['b', 'w'])
        D2.add_edges_from([('b', 'b'), ('w', 'w')])

        D3 = nx.DiGraph()
        D3.add_nodes_from(['u', 'p'])
        D3.add_edges_from([('p', 'p'), ('p', 'u'), ('u', 'u')])

        b_d1 = {1: 'c', 2: 'c', 3: 's', 4: 'c', 5: 's'}
        b_d2 = {1: 'b', 2: 'b', 3: 'b', 4: 'w', 5: 'w'}
        b_d3 = {1: 'p', 2: 'u', 3: 'u', 4: 'p', 5: 'p'}

        C1 = nx.DiGraph()
        C1.add_nodes_from(['c1', 'c2', 's'])
        C1.add_edges_from([('c1', 's'), ('c2', 's'), ('c1', 'c1'), ('c2', 'c2')])
        c_d1 = {'c1': 'c', 'c2': 'c', 's': 's'}

        C2 = nx.DiGraph()
        C2.add_nodes_from(['b1', 'b2', 'w'])
        C2.add_edges_from([('b1', 'b1'), ('w', 'w')])
        c_d2 = {'b1': 'b', 'b2': 'b', 'w': 'w'}

        C3 = nx.DiGraph()
        C3.add_nodes_from(['u', 'p'])
        C3.add_edges_from([('p', 'u'), ('u', 'u'), ('p', 'p')])
        c_d3 = {'u': 'u', 'p': 'p'}

        A, A_B, A_Cs = nary_pullback(
            B,
            {'d1': (C1, D1, b_d1, c_d1),
             'd2': (C2, D2, b_d2, c_d2),
             'd3': (C3, D3, b_d3, c_d3)}
        )
        # print_graph(A)
        # print(A_B)
        # print(A_Cs)

    def test_multi_pullback_clones(self):
        B = nx.DiGraph()
        B.add_nodes_from([
            1,
        ])

        D1 = nx.DiGraph()
        D1.add_nodes_from(['a'])

        D2 = nx.DiGraph()
        D2.add_nodes_from(['x'])

        b_d1 = {1: 'a'}
        b_d2 = {1: 'x'}

        C1 = nx.DiGraph()
        C1.add_nodes_from(['a', 'a1'])

        C2 = nx.DiGraph()
        C2.add_nodes_from(['x', 'x1'])

        c_d1 = {'a': 'a', 'a1': 'a'}
        c_d2 = {'x': 'x', 'x1': 'x'}

        a, a_b, a_cs = nary_pullback(
            B,
            {
                'd1': (C1, D1, b_d1, c_d1),
                'd2': (C2, D2, b_d2, c_d2)
            }
        )
        # print(a_b)
        # print(a_cs)
