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
    plot_graph(
        test_graph,
        filename=os.path.join(__location__, "dec_initial.png"))

    rw = Rewriter(test_graph.copy())
    LHS = init_pattern_graph()

    instances = rw.find_matching(LHS)

    print("Instances:")
    print("----------------------------------------")
    print(instances)
    print("\n")

    for i, instance in enumerate(instances):
        plot_instance(
            test_graph,
            LHS,
            instance,
            os.path.join(__location__, "dec_instance_%d.png" % i))

    # Define graph rewriting:
    print("Graph rewriting with homomorphisms:")
    print("----------------------------------------")

    RHS = TypedDiGraph()
    RHS.add_node(1, "agent", {'state': 'u'})
    RHS.add_node(2, "action")
    RHS.add_node(3, "region", {'x': 33})
    RHS.add_node(4, "agent")

    RHS.add_edges_from([(1, 2), (3, 2), (3, 4), (2, 4)])
    RHS.edge[1][2] = {"g": 0}

    plot_graph(
        RHS,
        filename=os.path.join(__location__, "RHS.png"))

    P = TypedDiGraph()
    P.add_node(1, "agent")
    P.add_node(2, "action")
    P.add_node(3, "region")
    P.add_node(4, "agent")
    P.add_node(5, "agent")
    P.add_node(6, "agent")

    P.add_edges_from([(1, 2), (3, 2), (3, 4)])

    h_p_lhs = Homomorphism(
        P,
        LHS,
        {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 7})

    h_p_rhs = Homomorphism(
        P,
        RHS,
        {1: 1, 2: 2, 3: 3, 4: 4, 5: 1, 6: 4})

    RHS_instance = rw.apply_rule(instances[0], h_p_lhs, h_p_rhs)

    print("Resulting graph:")
    print("---------------")
    print("Nodes: ", rw.graph_.nodes())
    for node in rw.graph_.nodes():
        print("Node %s " % str(node), rw.graph_.node[node].attrs_)
    print("\nEdges: ", rw.graph_.edges())
    for edge in rw.graph_.edges():
        print("Edge (%s)-(%s) " % edge, rw.graph_.edge[edge[0]][edge[1]])
    plot_graph(
        rw.graph_,
        filename=os.path.join(__location__, "dec_result.png"))

    print("Instance of RHS: ", RHS_instance)

    plot_instance(
        rw.graph_,
        RHS,
        RHS_instance,
        os.path.join(__location__, "instance_RHS_%d.png" % i))
