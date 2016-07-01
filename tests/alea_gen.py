""" Generate random examples """

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter
from regraph.library.utils import plot_graph

import argparse
import os
import sys

parser = argparse.ArgumentParser(description='Generate random examples')
parser.add_argument('-o', dest='out', action='store',  default="tests/rand",
                    type=str, help="output directory")
parser.add_argument('-ext', dest='ext', action='store',  default=".json",
                    type=str, help="extension to use")
parser.add_argument('-n', dest='nodes', action='store',  default=20,
                    type=int, help="number of nodes of generated graph")
parser.add_argument('-e', dest='edges', action='store', default=0.5,
                    type=float, help="probability of having an edge")
parser.add_argument('-t', dest='trans', action='store', default=20,
                    type=int, help="number of transformations to generate")
parser.add_argument('--meta', dest='meta', type=str, help="metamodel to use",
                    action='store', default=None )
parser.add_argument('--di', dest='di', action='store_const', const=True,
                    default=False, help='if graph is directed')
parser.add_argument('-p', dest='plot', action='store_const', const=True,
                    default=False, help='plot graphs')
parser.add_argument('--result', dest='result', action='store_const', const=True,
                    default=False, help='compute the resulting graph')
parser.add_argument('--debug', dest='debug', action='store_const', const=True,
                    default=False, help='prints useful informations')

args = parser.parse_args()
if args.out[-1] != "/":
    args.out += "/"
directory = args.out

if not os.path.exists(directory):
    os.makedirs(directory)

graph_type = TypedDiGraph if args.di else TypedGraph



# Create or import a meta-model
if args.meta==None:
    meta = graph_type.random_graph(n_nodes = 10)
else:
    meta = graph_type(load_file=args.meta)
meta.export(directory+"meta"+args.ext)

if args.plot:
    plot_graph(meta, filename=directory+"meta.png")
f = open(directory+"meta.txt", "w")
print(meta, file = f, end='')

# Create a random graph respecting the meta-model
graph = graph_type.random_graph(metamodel=meta, n_nodes=args.nodes,
                                                  p_edges=args.edges)
graph.export(directory+"graph"+args.ext)
if args.plot:
    plot_graph(graph, filename=directory+"graph.png")
f = open(directory+"graph.txt", "w")
print(graph, file = f, end='')

# Create random transformations on the graph we created
transformations = Rewriter.gen_transformations(args.trans, graph)
print(transformations, file = open(directory+'trans.txt', 'w'), end='')

if args.result:
    # Compute the result of the transformations on the graph

    f = open(directory+"transformations.txt", "w")
    print("Transformations:\n%s\n" % transformations, file = f, end='')

    transformations = Rewriter.simplify_commands(transformations)
    print("\n\nSimplified:\n%s\n" % transformations, file=f, end='')

    trans_list = Rewriter.make_canonical_commands(graph,
                                                  transformations,
                                                  args.di)
    print("\n\nCanonical:\nTrans:\n"+"\nTrans:\n".join(trans_list), file=f, end='')

    Gprime = Rewriter.do_canonical_rewrite(graph, transformations)
    if args.plot:
        plot_graph(Gprime, filename=directory+"result.png")
    Gprime.export(directory+"result"+args.ext)
    f = open(directory+"result.txt", "w")
    print(Gprime, file = f, end='')
