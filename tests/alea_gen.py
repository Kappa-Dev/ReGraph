from regraph.library.data_structures import (TypedDiGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter

meta = TypedDiGraph.random_graph(n_nodes = 50)
print("Meta :\n%s\n" % meta)
graph = TypedDiGraph.random_graph(metamodel=meta, n_nodes=500)
print("Graph :\n%s\n" % graph)
transformations = Rewriter.gen_transformations(100, graph)
print("Transformations :\n%s\n" % transformations)

trans = Rewriter.transformer_from_command(graph, transformations)

print("Transformer :\n%s\n" % trans)

Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)

print("Result :\n%s" % Gprime)
