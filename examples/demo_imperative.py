"""Testing of the rewriters module."""
import os

from regraph.library.rewriters import Rewriter

from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import Homomorphism

from regraph.library.utils import plot_graph
from regraph.library.utils import plot_instance



def init_test_graph():
    graph = TypedDiGraph()

    graph.add_node(1, 'agent',
                   {'name': 'EGFR'})
    graph.add_node(2, 'action', attrs={'name': 'BND'})
    graph.add_node(3, 'agent',
                   {'name': 'Grb2', 'aa': 'S', 'loc': 90})
    graph.add_node(4, 'region', attrs={'name': 'SH2'})
    graph.add_node(5, 'agent', attrs={'name': 'EGFR', 'state': 'p'})
    graph.add_node(6, 'action', attrs={'name': 'BND'})
    graph.add_node(7, 'agent', attrs={'name': 'Grb2'})

    graph.add_node(8, 'agent', attrs={'name': 'WAF1'})
    graph.add_node(9, 'action', {'name': 'BND'})
    graph.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

    edges = [
        (1, 2),
        (4, 2),
        (4, 3),
        (5, 6),
        (7, 6),
        (8, 9),
        (10, 9),
        (5, 2)
    ]

    graph.add_edges_from(edges)

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
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))

    test_graph = init_test_graph()
    LHS = init_pattern_graph()

    plot_graph(
        test_graph,
        filename=os.path.join(__location__, "imp_initial.png"))

    rw1 = Rewriter(test_graph)
    rw2 = Rewriter(test_graph.copy())

    instances = rw1.find_matching(LHS)

    print("Instances:")
    print("----------------------------------------")
    print(instances)
    print("\n")

    for i, instance in enumerate(instances):
        plot_instance(
            test_graph,
            LHS,
            instance,
            os.path.join(__location__, "imp_instance_%d.png" % i))

    # Define graph rewriting
    print("Graph rewriting with class method calls:")
    print("----------------------------------------")
    rw1.delete_node(instances[0], 6)
    rw1.merge(instances[0], [1, 5])
    rw1.merge(instances[0], [4, 7], node_name="merge_1")
    rw1.add_edge(instances[0], "merge_1", 2)
    plot_graph(
        rw1.graph_,
        filename=os.path.join(__location__, "imp_result_1.png"))

    print("Resulting graph:")
    print("---------------")
    print("Nodes: ", rw1.graph_.nodes())
    for node in rw1.graph_.nodes():
        print("Node %s " % str(node), rw1.graph_.node[node].attrs_)
    print("\nEdges: ", rw1.graph_.edges())
    for edge in rw1.graph_.edges():
        print("Edge (%s)-(%s) " % edge, rw1.graph_.edge[edge[0]][edge[1]])
    print("\n")

    print("Graph rewriting with script:")
    print("----------------------------------------")
    with open(os.path.join(__location__, "transform.regraph"), "r") as f:
        commands = f.read()
        print("Script:\n")
        print(commands)
        print()
        rw2.transform_instance(
            instances[0],
            commands
        )
        plot_graph(
            rw2.graph_,
            filename=os.path.join(__location__, "imp_result_2.png"))

    print("Resulting graph:")
    print("---------------")
    print("Nodes: ", rw2.graph_.nodes())
    for node in rw2.graph_.nodes():
        print("Node %s " % str(node), rw2.graph_.node[node].attrs_)
    print("\nEdges: ", rw2.graph_.edges())
    for edge in rw2.graph_.edges():
        print("Edge (%s)-(%s) " % edge, rw2.graph_.edge[edge[0]][edge[1]])
