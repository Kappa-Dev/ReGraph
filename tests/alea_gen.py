from regraph.library.data_structures import (TypedDiGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter

import os

directory = "tests/rand/"

if not os.path.exists(directory):
    os.makedirs(directory)


meta = TypedDiGraph.random_graph(n_nodes = 20)
meta.export(directory+"meta.json")
f = open(directory+"meta.txt", "w")
print(meta, file = f, end='')
graph = TypedDiGraph.random_graph(metamodel=meta, n_nodes=100)
graph.export(directory+"graph.json")
f = open(directory+"graph.txt", "w")
print(graph, file = f, end='')
transformations = Rewriter.gen_transformations(500, graph)
f = open(directory+"transformations.txt", "w")
print("Transformations :\n%s\n" % transformations, file = f, end='')

trans = Rewriter.transformer_from_command(graph, transformations)

f = open(directory+"transformer.txt", "w")
print("Transformer :\n%s\n" % trans, file = f, end='')

print(set(trans.P.nodes()).difference(set(trans.P_R_dict.keys())))
print(set(trans.P.nodes()).difference(set(trans.P_L_dict.keys())))

Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)
Gprime.export(directory+"result.json")
f = open(directory+"result.txt", "w")
print(Gprime, file = f, end='')
