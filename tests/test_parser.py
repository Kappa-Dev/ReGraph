"""Test primitives of commands parsing."""
from regraph.library.parser import parser

from nose.tools import assert_equals


class TestParser(object):
    """Class for testing parser with Python nose tests."""

    # def __init__(self):
    #     self.commands_ = {}
    #     self.commands_.update({"delete": })


    def test_delete_node(self):
        parsed = parser.parseString("    delete_node 6\n.").asDict()
        if "keyword" not in parsed.keys():
            assert False

        if parsed["keyword"] != "delete_node":
            assert False

        if "node" not in parsed.keys():
            assert False

        if type(parsed["node"]) != int:
            assert False

        assert_equals(parsed["node"], 6)

    def test_add_node(self):
        parsed = parser.parseString("    add_node 6 type agent\n.").asDict()
        if "keyword" not in parsed.keys():
            assert False

        if parsed["keyword"] != "add_node":
            assert False

        if "node" not in parsed.keys():
            assert False

        if type(parsed["node"]) != int:
            assert False

        assert_equals(parsed["node"], 6)

        if "type" not in parsed.keys():
            assert False

        if parsed["type"] != "agent":
            assert False

        parsed = parser.parseString(
            "add_node 6 type agent \n{a:[1,sd], b:bb, c:{c:d, d:c}}\n."
        ).asDict()

        if "attributes" not in parsed.keys():
            assert False

        if type(parsed["attributes"]) != dict:
            assert False
        if type(parsed["attributes"]["a"]) != list:
            assert False
        if type(parsed["attributes"]["a"][0]) != int:
            assert False
        if type(parsed["attributes"]["a"][1]) != str:
            assert False
        if type(parsed["attributes"]["c"]) != dict:
            assert False

    def test_delete_edge(self):
        parsed = parser.parseString("\ndelete_edge 6 ab.    ").asDict()

        if "keyword" not in parsed.keys():
            assert False

        if parsed["keyword"] != "delete_edge":
            assert False

        if "node_1" not in parsed.keys():
            assert False

        if "node_2" not in parsed.keys():
            assert False

        if type(parsed["node_1"]) != int:
            assert False

        if type(parsed["node_2"]) != str:
            assert False

        assert_equals(parsed["node_1"], 6)
        assert_equals(parsed["node_2"], "ab")

    def test_add_edge(self):
        parsed = parser.parseString("\nadd_edge 6 A {a:v}.    ").asDict()

        if "keyword" not in parsed.keys():
            assert False

        if parsed["keyword"] != "add_edge":
            assert False

        if "node_1" not in parsed.keys():
            assert False

        if "node_2" not in parsed.keys():
            assert False

        if type(parsed["node_1"]) != int:
            assert False

        if type(parsed["node_2"]) != str:
            assert False

        if "attributes" not in parsed.keys():
            assert False

        assert_equals(parsed["attributes"], {"a": "v"})


    def test_clone(self):
        parsed = parser.parseString("\n clone 6 as A.    ").asDict()
        if "keyword" not in parsed.keys():
            assert False

        if parsed["keyword"] != "clone":
            assert False

        if "node" not in parsed.keys():
            assert False

        if "node_name" not in parsed.keys():
            assert False

        if type(parsed["node"]) != int:
            assert False

        if type(parsed["node_name"]) != str:
            assert False

        assert_equals(parsed["node"], 6)
        assert_equals(parsed["node_name"], "A")

    def test_merge_nodes(self):
        parsed = parser.parseString(
            "\n merge [6, A, 2] method union as mergee edges union.    "
        ).asDict()
        assert_equals(
            parsed,
            {"keyword": "merge",
             "nodes": [6, "A", 2],
             "method": "union",
             "node_name": "mergee",
             "edges_method": "union"}
        )
