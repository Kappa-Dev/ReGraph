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
parser.add_argument('-log', dest='log', action='store', default=None,
                        help='log file to output')
parser.add_argument('--debug', dest='debug', action='store_const', const=True,
                    default=False, help='prints useful informations')

args = parser.parse_args()

if args.out[-1] != "/":
    args.out += "/"

directory = args.out

if args.log != None:
    sys.stdout = open(args.log, 'w')

if not os.path.exists(directory):
    os.makedirs(directory)

graph_type = TypedDiGraph if args.di else TypedGraph

if args.meta==None:
    meta = graph_type.random_graph(n_nodes = 10)
else:
    meta = graph_type(load_file=args.meta)

meta.export(directory+"meta"+args.ext)
if args.plot:
    plot_graph(meta, filename=directory+"meta.png")
f = open(directory+"meta.txt", "w")
print(meta, file = f, end='')
graph = graph_type.random_graph(metamodel=meta, n_nodes=args.nodes,
                                                  p_edges=args.edges)
graph.export(directory+"graph"+args.ext)
if args.plot:
    plot_graph(graph, filename=directory+"graph.png")
f = open(directory+"graph.txt", "w")
print(graph, file = f, end='')
transformations = Rewriter.gen_transformations(args.trans, graph)
f = open(directory+"transformations.txt", "w")
print("Transformations:\n%s\n" % transformations, file = f, end='')
transformations = Rewriter.simplify_commands(transformations)


trans = Rewriter.transformer_from_command(graph, transformations)

if args.debug:
    edges_in_R = [(trans.P_R_dict[n1], trans.P_R_dict[n2]) for (n1, n2) in trans.P.edges()]
    edges_in_L = [(trans.P_L_dict[n1], trans.P_L_dict[n2]) for (n1, n2) in trans.P.edges()]
    print("\nMapping:\nn_P\\n_P-R: %s\nn_P\\n_P-L: %s\nn_P-R\\n_P: %s\nn_P-L\\n_P: %s\n" %\
          (str([n for n in trans.P.nodes() if n not in trans.P_R_dict.keys()])+"\n",
          str([n for n in trans.P.nodes() if n not in trans.P_L_dict.keys()])+"\n",
          str([n for n in trans.P_R_dict.keys() if n not in trans.P.nodes()])+"\n",
          str([n for n in trans.P_L_dict.keys() if n not in trans.P.nodes()])))
    print("Connectivity:\ne_P\\e_R: %s\ne_P\\e_L: %s\ne_L\\e_G: %s\n" %\
          (str([e for e in edges_in_R if e not in trans.R.edges()])+"\n",
          str([e for e in edges_in_L if e not in trans.L.edges()])+"\n",
          str([e for e in trans.L.edges() if e not in trans.G.edges()])))

if args.plot:
    plot_graph(trans.P, filename = directory+"trans_P.png")
    plot_graph(trans.L, filename = directory+"trans_LHS.png")
    plot_graph(trans.R, filename = directory+"trans_RHS.png")
f = open(directory+"transformer.txt", "w")
print("Transformer:\n%s\n" % trans, file = f, end='')

Gprime = Rewriter.rewrite(Homomorphism.identity(trans.L, trans.G), trans)
if args.plot:
    plot_graph(Gprime, filename=directory+"result.png")
Gprime.export(directory+"result"+args.ext)
f = open(directory+"result.txt", "w")
print(Gprime, file = f, end='')
