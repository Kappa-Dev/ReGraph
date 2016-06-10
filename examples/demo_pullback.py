from regraph.library.data_structures import (TypedGraph,
                                             Homomorphism)
from regraph.library.tmp import (pullback)

D = TypedGraph()

D.add_node(1, 'square')
D.add_node(2, 'circle')
D.add_node(3, 'circle2')
D.add_node(4, 'dark_square')
D.add_node(5, 'dark_circle')

D.add_edge(2, 1)
D.add_edge(2, 3)
D.add_edge(2, 4)
D.add_edge(2, 5)

B = TypedGraph(D)

B.add_node(1, 'square')
B.add_node(2, 'circle')
B.add_node(3, 'dark_circle')
B.add_node(4, 'circle2')

B.add_edge(1, 2)
B.add_edge(3, 2)

C = TypedGraph(D)

C.add_node(1, 'circle')
C.add_node(2, 'circle2')
C.add_node(3, 'dark_circle')
C.add_node(4, 'dark_square')

C.add_edge(1, 2)
C.add_edge(1, 3)
C.add_edge(1, 4)

dic_homBD = {
    1 : 1,
    2 : 2,
    3 : 5,
    4 : 3
}

dic_homCD = {
    1 : 2,
    2 : 3,
    3 : 5,
    4 : 4
}

homBD = Homomorphism(B, D, dic_homBD)
homCD = Homomorphism(C, D, dic_homCD)

A, homAB, homAC = pullback(homBD, homCD)

print(A.nodes())
print(A.edges())
