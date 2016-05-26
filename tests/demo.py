"""Testing of the rewriters module."""
from regraph.library.rewriters import Rewriter

from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import Homomorphism

from regraph.library.utils import plot_graph
from regraph.library.utils import plot_instance

from regraph.library.primitives import merge_attributes


def init_test_graph():
    graph = TypedDiGraph()

    graph.add_node(1, 'agent',
                   {'name': 'EGFR', 'state': 'p'})
    graph.add_node(2, 'action', attrs={'name': 'BND'})
    graph.add_node(3, 'agent',
                   {'name': 'Grb2', 'aa': 'S', 'loc': 90})
    graph.add_node(4, 'region', attrs={'name': 'SH2'})
    graph.add_node(5, 'agent', attrs={'name': 'EGFR'})
    graph.add_node(6, 'action', attrs={'name': 'BND'})
    graph.add_node(7, 'agent', attrs={'name': 'Grb2'})

    graph.add_node(8, 'agent', attrs={'name': 'WAF1'})
    graph.add_node(9, 'action', {'name': 'BND'})
    graph.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

    graph.add_node(11, 'agent')
    graph.add_node(12, 'agent')
    graph.add_node(13, 'agent')

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
        (13, 11),
        (5, 2)
    ]

    graph.add_edges_from(edges)

    # later you can add some attributes to the edge

    graph.set_edge(1, 2, {'s': 'p'})
    graph.set_edge(4, 2, {'s': 'u'})
    graph.set_edge(5, 6, {'s': 'p'})
    graph.set_edge(7, 6, {'s': 'u'})
    graph.set_edge(5, 2, {'s': 'u'})
    return graph


def init_pattern_graph():
    pattern = TypedDiGraph()

    pattern.add_node(1, 'agent', {'name': 'EGFR'})
    pattern.add_node(2, 'action', {'name': 'BND'})
    pattern.add_node(3, 'region')
    pattern.add_node(4, 'agent', {'name': 'Grb2'})
    pattern.add_node(5, 'agent', {'name': 'EGFR'})
    pattern.add_node(6, 'action', {'name': 'BND'})
    pattern.add_node(7, 'agent', {'name': 'Grb2'})

    pattern.add_edges_from([(1, 2), (3, 2), (3, 4), (5, 6), (7, 6)])

    pattern.set_edge(1, 2, {'s': 'p'})
    pattern.set_edge(5, 6, {'s': 'p'})

    return pattern


if __name__ == '__main__':

    # Test TypedGraph functionality
    test_graph = init_test_graph()

    # plot_graph(test_graph, filename="initial.png")
    LHS = init_pattern_graph()

    # Test homomorphisms functionality
    mapping = {1: 1,
               2: 2,
               3: 4,
               4: 3,
               5: 5,
               6: 6,
               7: 7}
    # h1 = Homomorphism(LHS, test_graph, mapping)

    rw1 = Rewriter(test_graph)
    rw2 = Rewriter(test_graph.copy())

    instances = rw1.find_matching(LHS)
    # print(instances)
    for i, instance in enumerate(instances):
        plot_instance(
            test_graph,
            LHS,
            instance,
            "instance_%d.png" % i)

    # Define graph rewriting:

    # 1. In the form of script
    rw1.transform_instance(
        instances[0],
        """delete_node 6.\n"""
        """merge [1, 5] method union as merge_1.\n"""
        """merge [4, 7] as merge_2.\n"""
        """add_edge merge_1 merge_2.\n"""
        """clone merge_1 as clone_1.\n"""
        """clone 3 as clone_2."""
    )
    plot_graph(rw1.graph_, filename="result_1.png")

    # 2. With a simple sequence of class method calls
    rw2.delete_node(instances[0], 6)
    rw2.merge(instances[0], [1, 5], node_name='merge_1')
    rw2.merge(instances[0], [4, 7], node_name='merge_2')
    rw2.add_edge(instances[0], 'merge_1', 'merge_2', {'state': 0})
    rw2.clone(instances[0], 'merge_1', 'clone_1')
    rw2.clone(instances[0], 3, 'clone_2')
    plot_graph(rw2.graph_, filename="result_2.png")

    # 3. With LHS <-h1- P -h2-> RHS
