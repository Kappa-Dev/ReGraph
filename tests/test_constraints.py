""" nose test for constraints"""

from nose.tools import assert_equals

from regraph.library.graphs import TypedDiGraph


class TestConstraints(object):
    """Class for testing the verification of constraints in a hierarchy"""

    def __init__(self):

        self.g1 = TypedDiGraph()
        g1 = self.g1
        g1.add_node("n1", None)
        g1.add_node("n2", None)
        g1.add_edge("n2", "n1")

        # something of type "1" has at most 2 adjascent nodes of type 2
        g1.add_input_constraint("n1", "n2", lambda n: n <= 2, "n2 <= 2")

        # something of type "2" has exactly one adjascent node of type 1
        g1.add_output_constraint("n2", "n1", lambda n: n <= 1, "n1 <= 1")
        g1.add_output_constraint("n2", "n1", lambda n: n >= 1, "n1 >= 1")

        self.g2 = TypedDiGraph(g1)
        g2 = self.g2

        g2.add_node("m1", "n1")
        g2.add_node("m2", "n1")
        g2.add_node("m3", "n2")
        g2.add_node("m4", "n2")
        g2.add_node("m5", "n2")

        g2.add_edge("m3", "m1")
        g2.add_edge("m4", "m1")

        self.g3 = TypedDiGraph(g2)
        g3 = self.g3

        g3.add_node("m1", "m1")
        g3.add_node("m2", "m2")
        g3.add_node("m3", "m3")
        g3.add_node("m4", "m4")
        g3.add_node("m5", "m5")

        g3.add_edge("m3", "m1")
        g3.add_edge("m4", "m1")

    def test_constraints1(self):
        """ m5 is not linked to anything of type n1"""
        assert_equals(set(self.g2.check_constraints()), {"n1 >= 1"})
        assert_equals(self.g2.unckecked_nodes, {"m5"})

    def test_constraints2(self):
        """ now it's ok"""
        self.g2.add_edge("m5", "m2")
        assert_equals(set(self.g2.check_constraints()), set())
        assert_equals(self.g2.unckecked_nodes, set())

    def test_constraints3(self):
        """ m1 has 3 input edges from nodes of type m2, which is to many"""
        self.g2.add_edge("m5", "m1")
        assert_equals(set(self.g2.check_constraints()), {"n2 <= 2"})
        assert_equals(self.g2.unckecked_nodes, {"m1"})

    # g3 is typed by g2 and heritates the constraints from g1
    def test_constraints4(self):
        """ m5 is not linked to anything of type n1"""
        assert_equals(set(self.g3.check_constraints()), {"n1 >= 1"})
        assert_equals(self.g3.unckecked_nodes, {"m5"})

    def test_constraints5(self):
        """ now it's ok"""
        self.g2.add_edge("m5", "m2")
        self.g3.add_edge("m5", "m2")
        assert_equals(set(self.g3.check_constraints()), set())
        assert_equals(self.g3.unckecked_nodes, set())
