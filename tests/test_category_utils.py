import networkx as nx
import copy

from nose.tools import assert_equals

from regraph import (print_graph,
                     NXGraph)
# from regraph.utils import assert_nx_graph_eq
from regraph.category_utils import (pullback,
                                    pushout,
                                    pullback_complement,
                                    get_unique_map_to_pullback_complement)


def assert_edges_undir(edges1, edges2):

    edgeset1 = set(edges1)
    edgeset2 = set(edges2)

    for edge in edgeset1:
        if edge not in edgeset2 and (edge[1], edge[0]) not in edgeset2:
            assert False


class TestCategoryUtils:
    def __init__(self):
        D = NXGraph()

        D.add_node('square')
        D.add_node('circle')
        D.add_node('dark_square')
        D.add_node('dark_circle')
        D.add_edge('square', 'circle')
        D.add_edge('circle', 'dark_circle')
        D.add_edge('circle', 'dark_square')
        D.add_edge('circle', 'circle')

        self.D = D

        A = NXGraph()

        A.add_node(2)
        A.add_node(3)
        A.add_edge(2, 3)

        self.A = A

        B = NXGraph()

        B.add_node(1)
        B.add_node(2)
        B.add_node(3)
        B.add_edge(1, 2)
        B.add_edge(2, 3)

        self.B = B

        C = NXGraph()

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
            self.B, self.C, self.D, self.homBD, self.homCD,
        )
        assert_equals(type(A), NXGraph)
        assert_equals(set(A.nodes()), set(self.A.nodes()))
        assert_edges_undir(A.edges(), self.A.edges())
        assert_equals(homAB, self.homAB)
        assert_equals(homAC, self.homAC)

    def test_pullback_complement(self):
        C, homAC, homCD = pullback_complement(
            self.A, self.B, self.D, self.homAB, self.homBD
        )
        assert_equals(type(C), NXGraph)
        test_graph = self.C.get_relabeled_graph(
            {2: "circle", 3: "dark_circle", "dark_square": "dark_square"}
        )
        # assert_nx_graph_eq(test_graph, C)
        assert(test_graph == C)
        assert(id(self.D) != id(C))

    def test_pullpack_complement_inplace(self):
        D_copy = copy.deepcopy(self.D)
        C, homAC, homCD = pullback_complement(
            self.A, self.B, D_copy, self.homAB, self.homBD, inplace=True
        )
        assert_equals(type(C), NXGraph)
        test_graph = self.C.get_relabeled_graph(
            {2: "circle", 3: "dark_circle", "dark_square": "dark_square"}
        )
        assert(test_graph == C)
        assert(id(D_copy) == id(C))

    def test_pushout(self):
        D, homBD, homCD = pushout(
            self.A, self.B, self.C, self.homAB, self.homAC
        )
        assert_equals(type(D), NXGraph)

        assert_equals(len(D.nodes()),
                      len(self.D.nodes()))

        assert_equals(len(D.edges()),
                      len(self.D.edges()))
        assert(id(self.B) != id(D))

    def test_pushout_inplace(self):
        B_copy = copy.deepcopy(self.B)
        D, homBD, homCD = pushout(
            self.A, B_copy, self.C, self.homAB, self.homAC, inplace=True
        )
        assert_equals(type(D), NXGraph)

        assert_equals(len(D.nodes()),
                      len(self.D.nodes()))

        assert_equals(len(D.edges()),
                      len(self.D.edges()))
        assert(id(B_copy) == id(D))

    def test_pushout_symmetry_directed(self):

        A = NXGraph()
        A.add_nodes_from(["a", "b"])
        A.add_edges_from([("a", "b")])

        B = NXGraph()
        B.add_nodes_from([1, 2, 3])
        B.add_edges_from([(2, 3), (3, 2), (1, 3)])

        C = NXGraph()
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
        assert_equals(len(D.nodes()), len(D_inv.nodes()))
        assert_equals(len(D.edges()), len(D_inv.edges()))

    def test_get_unique_map_to_pullback_complement(self):
        # a_b = {
        #     "circle1": "circle",
        #     "circle2": "circle"
        # }

        # b_c = {
        #     "circle": "circle",
        #     "triangle": "triangle",
        # }

        a_p = {
            "circle1": "c1",
            "circle2": "c2"
        }

        p_c = {
            "c1": "circle",
            "c2": "circle",
            "square": "square"
        }

        a_prime_a = {
            "circle1": "circle1",
            "circle2": "circle2"
        }

        a_prime_z = {
            "circle1": "circle1",
            "circle2": "circle2"
        }

        z_c = {
            "circle1": "circle",
            "circle2": "circle",
            "square": "square"
        }

        # z_p = get_unique_map_to_pullback_complement(
        #     a_b, b_c, a_p, p_c, a_z, z_c)

        z_p = get_unique_map_to_pullback_complement(
            a_p, p_c,
            a_prime_a, a_prime_z,
            z_c)
        assert(z_p == {'circle1': 'c1', 'circle2': 'c2', 'square': 'square'})
