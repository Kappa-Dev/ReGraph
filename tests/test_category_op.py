from nose.tools import raises
from nose.tools import assert_equals

from regraph.library.data_structures import (TypedGraph,
                                             Homomorphism)
from regraph.library.category_op import (pullback, pushout, pullback_complement)


def assert_edges_undir(edges1, edges2):

    edgeset1 = set(edges1)
    edgeset2 = set(edges2)

    for edge in edgeset1:
        if edge not in edgeset2 and (edge[1], edge[0]) not in edgeset2:
            assert False


class TestCategoryOp:
    def __init__(self):
        D = TypedGraph()

        D.add_node('square', 'square')
        D.add_node('circle', 'circle')
        D.add_node('dark_square', 'dark_square')
        D.add_node('dark_circle', 'dark_circle')

        D.add_edge('square', 'circle')
        D.add_edge('circle', 'dark_circle')
        D.add_edge('circle', 'dark_square')
        D.add_edge('circle', 'circle')

        A = TypedGraph(D)

        A.add_node(2, 'circle')
        A.add_node(3, 'dark_circle')

        A.add_edge(2, 3)

        B = TypedGraph(D)

        B.add_node(1, 'square')
        B.add_node(2, 'circle')
        B.add_node(3, 'dark_circle')

        B.add_edge(1, 2)
        B.add_edge(2, 3)

        C = TypedGraph(D)

        C.add_node(2, 'circle')
        C.add_node(3, 'dark_circle')
        C.add_node('dark_square', 'dark_square')

        C.add_edge(2, 3)
        C.add_edge(2, 'dark_square')
        C.add_edge(2, 2)

        dic_homAB = {
            2: 2,
            3: 3
        }
        dic_homAC = {
            2: 2,
            3: 3
        }
        dic_homBD = {
            1: 'square',
            2: 'circle',
            3: 'dark_circle'
        }

        dic_homCD = {
            2: 'circle',
            3: 'dark_circle',
            'dark_square': 'dark_square'
        }

        self.homAB = Homomorphism(A, B, dic_homAB)
        self.homAC = Homomorphism(A, C, dic_homAC)
        self.homBD = Homomorphism(B, D, dic_homBD)
        self.homCD = Homomorphism(C, D, dic_homCD)

    def test_pullback(self):
        A, homAB, homAC = pullback(self.homBD, self.homCD)
        assert_equals(type(A), TypedGraph)
        assert_equals(set(A.nodes()), set(self.homAB.source_.nodes()))
        assert_edges_undir(A.edges(), self.homAB.source_.edges())
        assert_equals(homAB.mapping_, self.homAB.mapping_)
        assert_equals(homAC.mapping_, self.homAC.mapping_)

    def test_pullback_complement(self):
        C, homAC, homCD = pullback_complement(self.homAB, self.homBD)
        assert_equals(type(C), TypedGraph)
        assert_equals(set(C.nodes()), set(self.homAC.target_.nodes()))
        assert_edges_undir(C.edges(), self.homAC.target_.edges())
        assert_equals(homAC.mapping_, self.homAC.mapping_)
        assert_equals(homCD.mapping_, self.homCD.mapping_)

    def test_pushout(self):
        D, homBD, homCD = pushout(self.homAB, self.homAC)
        assert_equals(type(D), TypedGraph)

        assert_equals(len(D.nodes()),
                      len(self.homBD.target_.nodes()))

        assert_equals(len(D.edges()),
                      len(self.homBD.target_.edges()))
