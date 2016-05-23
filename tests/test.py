"""Testing of the rewriters module."""
from regraph.library.rewriters import Rewriter

import networkx as nx


def init_test_graph():
    graph = nx.DiGraph()

    edges = [
        (1, 2),
        (4, 2),
        (4, 3),
        (5, 6),
        (7, 6),
        (8, 9),
        (10, 9),
        (11, 12),
        (12, 11),
        (12, 13),
        (13, 12),
        (11, 13),
        (13, 11)
    ]

    graph.add_edges_from(edges)

    # Graph from example in the paper page 5 and something more
    graph.node[1] = {'type': 'agent', 'name': 'EGFR', 'state': 'p'}
    graph.node[2] = {'type': 'action', 'name': 'BND'}
    graph.node[3] = {'type': 'agent', 'name': 'Grb2', 'aa': 'S', 'loc': 90}
    graph.node[4] = {'type': 'region', 'name': 'SH2'}

    graph.node[5] = {'type': 'agent', 'name': 'EGFR'}
    graph.node[6] = {'type': 'action', 'name': 'BND'}
    graph.node[7] = {'type': 'agent', 'name': 'Grb2'}

    graph.node[8] = {'type': 'agent', 'name': 'WAF1'}
    graph.node[9] = {'type': 'action', 'name': 'BND'}
    graph.node[10] = {'type': 'agent', 'name': 'G1-S/CDK', 'state': 'p'}

    graph.node[11] = {'type': 'agent'}
    graph.node[12] = {'type': 'agent'}
    graph.node[13] = {'type': 'agent'}

    return graph


def init_pattern_graph():
    pattern = nx.DiGraph()
    pattern.add_edges_from([(1, 2), (3, 2), (3, 4), (5, 6), (7, 6)])

    pattern.node[1] = {'type': 'agent', 'name': 'EGFR'}
    pattern.node[2] = {'type': 'action', 'name': 'BND'}
    pattern.node[3] = {'type': 'region'}
    pattern.node[4] = {'type': 'agent', 'name': 'Grb2'}

    pattern.node[5] = {'type': 'agent', 'name': 'EGFR'}
    pattern.node[6] = {'type': 'action', 'name': 'BND'}
    pattern.node[7] = {'type': 'agent', 'name': 'Grb2'}

    return pattern


if __name__ == '__main__':
    test_graph = init_test_graph()
    rw = Rewriter(test_graph)
    rw.plot_graph("initial.png")
    LHS = init_pattern_graph()
    instances = rw.find_matching(LHS)
    for i, instance in enumerate(instances):
        rw.plot_instance(
            LHS,
            instance,
            "instance_%d" % i)
    rw.transform_instance(
        instances[0],
        """delete_node 6.
merge [1, 5] method union.
merge [4, 7]."""
    )
    rw.plot_graph("result.png")
