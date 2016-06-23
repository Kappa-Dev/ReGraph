from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter
import argparse

parser = argparse.ArgumentParser(description='Takes G, Transformations and Result and returns True if\
                                              G after transformations is Result')
parser.add_argument('graph', metavar='G', type=str, help="the graph G")
parser.add_argument('transformations', metavar='trans', type=str, help='the transformations')
parser.add_argument('result', metavar='res', type=str, help='the result')
parser.add_argument('--di', dest='di', action='store_const', const=True, default=False, help='graph is directed')

args = parser.parse_args()

graph = TypedDiGraph(load_file=args.graph) if args.di else TypedGraph(load_file=args.graph)

f = open(args.transformations, 'r')
f.readline()
trans_string = f.read()

result = TypedDiGraph(load_file=args.result) if args.di else TypedGraph(load_file=args.result)

trans = Rewriter.transformer_from_command(graph, trans_string)

rw = Rewriter(graph)
rw.apply_rule(Homomorphism.identity(trans.L, trans.G), trans)

assert(graph==result)
