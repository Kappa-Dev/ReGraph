from nose.tools import raises
from nose.tools import assert_equals

from regraph.library.data_structures import (TypedGraph,
                                             Homomorphism)
from regraph.library.category_op import (pullback,
                                         pullback_complement,
                                         pushout)


class TestCategoryOp:
    def __init__(self):
        self.D = TypedGraph()

        self.D.add_node('square', 'light')
        self.D.add_node('circle', 'light')
        self.D.add_node('dark_square', 'dark')
        self.D.add_node('dark_circle', 'dark')

        self.D.add_edge('square', 'circle')
        self.D.add_edge('circle', 'dark_circle')
        self.D.add_edge('circle', 'dark_square')
        self.D.add_edge('circle', 'circle')

        self.B = TypedGraph()

        self.B.add_node('1', 'square')
        self.B.add_node('2', 'circle')
        self.B.add_node('3', 'dark_circle')

        self.B.add_edge('1', '2')
        self.B.add_edge('2', '3')

        self.C = TypedGraph(self.D)

        self.C.add_node('1', 'circle')
        self.C.add_node('2', 'circle')
        self.C.add_node('3', 'dark_circle')
        self.C.add_node('4', 'dark_square')

        self.C.add_edge('1', '2')
        self.C.add_edge('1', '3')
        self.C.add_edge('1', '4')

        self.A = TypedGraph()

        self.A.add_node('1', 'circle')
        self.A.add_node('2', 'dark_circle')

        dic_homAB = {
            '1' : '1',
            '2' : '3'
        }

        dic_homAC = {
            '1' : '1',
            '2' : '3'
        }

        dic_homBD = {
            '1': 'square',
            '2': 'circle',
            '3': 'dark_circle'
        }

        dic_homCD = {
            '1': 'circle',
            '2': 'circle',
            '3': 'dark_circle',
            '4': 'dark_square'
        }

        self.homAB = Homomorphism(self.A, self.B, dic_homAB)
        self.homAC = Homomorphism(self.A, self.C, dic_homAC)
        self.homBD = Homomorphism(self.B, self.D, dic_homBD)
        self.homCD = Homomorphism(self.C, self.D, dic_homCD)

        self.A_, homAB, homAC = pullback(self.homBD, self.homCD)
        self.C_, homAC, homCD = pullback_complement(self.homAB, self.homBD)
        self.D_, homBD, homCD = pushout(self.homAB, self.homAC)

    def test_type(self):
        assert_equals(type(self.A), TypedGraph)
