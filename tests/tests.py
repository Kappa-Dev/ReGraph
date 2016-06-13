from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import TypedGraph
from regraph.library.data_structures import Homomorphism

from regraph.library.primitives import cast_node, remove_edge

graph_ = TypedDiGraph()
graph_.add_node(1, 'agent',
                     {'name': 'EGFR', 'state': 'p'})
graph_.add_node(2, 'action', attrs={'name': 'BND'})
graph_.add_node(3, 'agent',
                     {'name': 'Grb2', 'aa': 'S', 'loc': 90})
graph_.add_node(4, 'region', attrs={'name': 'SH2'})
graph_.add_node(5, 'agent', attrs={'name': 'EGFR'})
graph_.add_node(6, 'action', attrs={'name': 'BND'})
graph_.add_node(7, 'agent', attrs={'name': 'Grb2'})

graph_.add_node(8, 'agent', attrs={'name': 'WAF1'})
graph_.add_node(9, 'action', {'name': 'BND'})
graph_.add_node(10, 'agent', {'name': 'G1-S/CDK', 'state': 'p'})

graph_.add_node(11, 'agent')
graph_.add_node(12, 'agent')
graph_.add_node(13, 'agent')

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

print(graph_.nodes())
print(graph_.edges())

graph_.add_edge(1,3)
graph_.add_edges_from(edges)

# later you can add some attributes to the edge

graph_.set_edge(1, 2, {'s': 'p'})
graph_.set_edge(4, 2, {'s': 'u'})
graph_.set_edge(5, 6, {'s': 'p'})
graph_.set_edge(7, 6, {'s': 'u'})
graph_.set_edge(5, 2, {'s': 'u'})

LHS_ = TypedDiGraph()

LHS_.add_node(1, 'agent', {'name': 'EGFR'})
LHS_.add_node(2, 'action', {'name': 'BND'})
LHS_.add_node(3, 'region')
LHS_.add_node(4, 'agent', {'name': 'Grb2'})
LHS_.add_node(5, 'agent', {'name': 'EGFR'})
LHS_.add_node(6, 'action', {'name': 'BND'})
LHS_.add_node(7, 'agent', {'name': 'Grb2'})

LHS_.add_edges_from([(1, 2), (3, 2), (3, 4), (5, 6), (7, 6)])

LHS_.set_edge(1, 2, {'s': 'p'})
LHS_.set_edge(5, 6, {'s': 'p'})
