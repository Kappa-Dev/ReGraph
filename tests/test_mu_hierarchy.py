"""nose tests for the mu_graph_hierarchy"""

from nose.tools import assert_equals
from regraph.mu_hierarchy import MuHierarchy
import networkx as nx


class TestMuHierarchy(object):
    """verification of formulae from parent graphs"""

    def __init__(self):

        self.hierarchy = MuHierarchy()
        g1 = nx.DiGraph()
        g1.add_node("agent")
        g1.add_node("region")
        g1.add_edge("region", "agent")

        self.hierarchy.add_graph(
            "g1", g1,
            {"formulae":
             [("f1", "or(not cnt(Region),<1<=Adj>cnt(Agent))")]
             }
        )

        g2 = nx.DiGraph()
        g2.add_node("a1")
        g2.add_node("r1")
        g2.add_node("r2")
        g2.add_edge("r1", "a1")

        self.hierarchy.add_graph("g2", g2)
        self.hierarchy.add_typing(
            "g2", "g1",
            {"a1": "agent",
             "r1": "region",
             "r2": "region"}
        )

    def test1(self):
        """r2 does not verify the formula."""
        assert_equals(self.hierarchy.check_all_ancestors("g2"),
                      {'g1':
                       {'f1': "['r2']"}})

    # def test2(self):
    #     """after adding an edge all the node are valid"""
    #     self.hie2.add_edge("r2", "a1")
    #     assert_equals(self.hie2.check(),
    #                   {'g1': {'or(not cnt(Region),<1<=Adj>cnt(Agent))': "[]"}})
