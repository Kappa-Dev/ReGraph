from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import TypedGraph
from regraph.library.data_structures import Homomorphism

from regraph.library.primitives import cast_node, remove_edge
from regraph.library.category_op import pullback

D = TypedGraph()

D.add_node('square', 'square')
D.add_node('circle', 'circle')
D.add_node('dark_square', 'dark_square')
D.add_node('dark_circle', 'dark_circle')

D.add_edge('square', 'circle')
D.add_edge('circle', 'dark_circle')
D.add_edge('circle', 'dark_square')
D.add_edge('circle', 'circle')

B = TypedGraph(D)

B.add_node(1, 'square')
B.add_node(2, 'circle')
B.add_node(3, 'dark_circle')

B.add_edge(1, 2)
B.add_edge(2, 3)

C = TypedGraph(D)

C.add_node(1, 'circle')
C.add_node(2, 'circle')
C.add_node(3, 'dark_circle')
C.add_node(4, 'dark_square')

C.add_edge(1, 2)
C.add_edge(1, 3)
C.add_edge(1, 4)

dic_homBD = {
    1: 'square',
    2: 'circle',
    3: 'dark_circle'
}

dic_homCD = {
    1: 'circle',
    2: 'circle',
    3: 'dark_circle',
    4: 'dark_square'
}

homBD = Homomorphism(B, D, dic_homBD)
homCD = Homomorphism(C, D, dic_homCD)

A, homAB, homAC = pullback(homBD, homCD)
