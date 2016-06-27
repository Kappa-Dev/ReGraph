from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter
from regraph.library.utils import plot_graph
import argparse
import os
import subprocess

parser = argparse.ArgumentParser(description='Run tests')
parser.add_argument('-f', dest='file', action='store', default='tests/alea_gen.py',
                    type=str, help="test script to run.\
                    Should have arguments -n for nodes number, -e for edge \
                    probability, -t for transformations number and -meta \
                    for metamodel. All those args are optional")
parser.add_argument('-N', dest='tests', action='store',  default=20,
                    type=int, help="number of tests to run")
parser.add_argument('-in', dest='input', action='store',  default="tests/rand",
                    type=str, help="input directory")
parser.add_argument('-o', dest='out', action='store',  default="tests/tester",
                    type=str, help="output directory")
parser.add_argument('-ext', dest='ext', action='store',  default=".json",
                    type=str, help="extension of graph files")
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
parser.add_argument('-m', dest='method', action='store', type=str,
                    default="prop", help='method to use : prop or rew or all')
parser.add_argument('--debug', dest='debug', action='store_const', const=True,
                    default=False, help='print useful informations')
parser.add_argument('-p', dest='plot', action='store_const', const=True,
                    default=False, help='plot')

args = parser.parse_args()

if args.out[-1] != "/":
    args.out += "/"
if args.input[-1] != "/":
    args.input += "/"
if args.ext[0] != ".":
    args.ext = "."+args.ext

if not os.path.exists(args.out):
    os.makedirs(args.out)

os.system("rm -rf "+args.out)

i = 1
for n in range(args.tests):
    print("Generating test", i)

    if not os.path.exists(args.out+str(i)+"/"):
        os.makedirs(args.out+str(i)+"/")

    directory = args.out+str(i)+"/"

    process = subprocess.check_output(("python3 -W ignore "+args.file+" -o %s -n %s -e %s -t %s%s%s%s%s" %
              (args.input, args.nodes, args.edges, args.trans,
               " --meta "+args.meta if args.meta != None else '',
               ' --di' if args.di else '',
               ' --debug' if args.debug else '',
               ' -p' if args.plot else '')).split(" "))
    print(process.decode("UTF-8"), end='')

    meta = TypedDiGraph(load_file=args.input+'meta'+args.ext) if args.di else TypedGraph(load_file=args.input+'meta'+args.ext)
    meta.export(directory+"meta"+args.ext)
    plot_graph(meta, filename = directory+"meta.png")

    graph = TypedDiGraph(load_file=args.input+'graph'+args.ext) if args.di else TypedGraph(load_file=args.input+'graph'+args.ext)
    graph.export(directory+"graph"+args.ext)
    if args.plot:
        plot_graph(graph, filename = directory+"graph.png")

    f = open(args.input+'transformations.txt', 'r')
    f.readline()
    trans_string = f.read()
    fprime = open(directory+'transformations.txt', 'w')
    print(trans_string, file=fprime, end='')

    trans = Rewriter.transformer_from_command(graph, trans_string)
    f = open(directory+"transformer.txt", "w")
    print(trans, file=f, end='')
    trans.P.export(directory+"trans_P"+args.ext)
    trans.L.export(directory+"trans_LHS"+args.ext)
    trans.R.export(directory+"trans_RHS"+args.ext)
    if args.plot:
        plot_graph(trans.P, filename = directory+"trans_P.png")
        plot_graph(trans.L, filename = directory+"trans_LHS.png")
        plot_graph(trans.R, filename = directory+"trans_RHS.png")

    if args.method == "prop" or args.method == "all":
        result = TypedDiGraph(load_file=args.input+'result'+args.ext) if args.di else TypedGraph(load_file=args.input+'result'+args.ext)
        result.export(directory+"result_cat_op"+args.ext)
        if args.plot:
            plot_graph(result, filename = directory+"result_cat_op.png")

    if args.method == "rew" or args.method == "all":
        rw = Rewriter(graph)
        rw.apply_rule(Homomorphism.identity(trans.L, trans.G), trans)
        graph.export(directory+"result_rul"+args.ext)
        if args.plot:
            plot_graph(graph, filename = directory+"result_rul.png")

    i += 1

    print("Done"+("\n" if args.debug else ''))
