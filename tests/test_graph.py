"""Collection of tests for ReGraph_neo4j graphs."""

from regraph.neo4j.graphs import *


class TestGraphs(object):

    def __init__(self):
        """Init of the test class."""
        self.g = Neo4jGraph(
              uri="bolt://localhost:7687", user="neo4j", password="admin")
        res = self.g.clear()
        nodes = [
            ('1', {'name': 'EGFR', 'state': 'p'}),
            ('2', {'name': 'BND'}),
            ('3', {'name': 'Grb2', 'aa': 'S', 'loc':90}),
            ('4', {'name': 'SH2'}),
            ('5', {'name': 'EGFR'}),
            ('6', {'name': 'BND'}),
            ('7', {'name': 'Grb2'}),
            ('8', {'name': 'WAF1'}),
            ('9', {'name': 'BND'}),
            ('10', {'name': 'G1-S/CDK', 'state': 'p'}),
            '11', '12', '13'
            ]
        edges = [
            ('1', '2', {'s': 'p'}),
            ('4', '2', {'s': 'u'}),
            ('4', '3'),
            ('5', '6', {'s': 'p'}),
            ('7', '6', {'s': 'u'}),
            ('8', '9'),
            ('9', '8'),
            ('10', '8', {'a': {1}}),
            ('10', '9', {'a': {2}}),
            ('11', '12'),
            ('12', '11'),
            ('12', '13'),
            ('13', '12'),
            ('11', '13'),
            ('13', '11'),
            ('5', '2', {'s': 'u'})
            ]
        self.g.add_nodes_from(nodes)
        self.g.add_edges_from(edges)

    def test_add_node(self):
        # Case 1 : "x" is not in the graph
        attrs = {'a': {1}}
        self.g.add_node("x", attrs)
        query = get_node("x")
        print(query)
        result = self.g.execute(query)
        try:
            res_node = dict(result.value()[0])
        except(ValueError):
            res_node = dict(result.value())
        assert(len(res_node)!=0)
        for k in attrs.keys():
            for v in attrs[k]:
                assert(v in res_node[k])

    def test_add_edge(self):
        s = '1'
        t = '5'
        attrs = {'a': {1}}
        g.add_edge(s, t, attrs)


#t = TestGraphs()
#t.test_add_node()
