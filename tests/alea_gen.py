from regraph.library.data_structures import (TypedDiGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter

meta = TypedDiGraph.random_graph(n_nodes = 10)
meta.export("tests/rand/meta.json")
graph = TypedDiGraph.random_graph(metamodel=meta, n_nodes=50)
graph.export("tests/rand/graph.json")
transformations = Rewriter.gen_transformations(100, graph)
f = open("tests/rand/transformations.txt", "w")
print("Transformations :\n%s\n" % transformations, file = f, end='')

trans = Rewriter.transformer_from_command(graph, transformations)

f = open("tests/rand/transformer.txt", "w")
print("Transformer :\n%s\n" % trans, file = f, end='')

Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)
Gprime.export("tests/rand/result.json")
