""" Run tests using different methods and compare the results
    Example of command line :
      > python3 -W ignore tests/tester.py -N 10 -n 20 -e 0.1 -t 500 --meta tests/big_graph/metametameta.xml -m 'prop;canonic' -log logs.txt -comp
"""

from regraph.library.data_structures import (TypedDiGraph,
                                             TypedGraph,
                                             Homomorphism)
from regraph.library.rewriters import Rewriter
from regraph.library.utils import plot_graph
import argparse
import os
import subprocess
import sys

parser = argparse.ArgumentParser(description='Run tests using different methods and compare the results')
parser.add_argument('-f', dest='file', action='store', default='tests/alea_gen.py',
                    type=str, help="test script to run.\
                    Should have arguments -n for nodes number, -e for edge \
                    probability, -t for transformations number and -meta \
                    for metamodel. All those args are optional")
parser.add_argument('-N', dest='tests', action='store',  default=20,
                    type=int, help="number of tests to run")
parser.add_argument('-in', dest='input', action='store',  default="tests/rand",
                    type=str, help="input directory, where graphs will be generated and read")
parser.add_argument('-o', dest='out', action='store',  default="tests/tester",
                    type=str, help="output directory, where results will be written")
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
parser.add_argument('-m', dest='methods', action='store', type=str,
                    default="prop", help='method to use : prop or rew or canonic or all (can combine them eg. prop;canonic)')
parser.add_argument('--debug', dest='debug', action='store_const', const=True,
                    default=False, help='print useful informations')
parser.add_argument('-log', dest='log', action='store', default=None,
                    help='log file to output')
parser.add_argument('-p', dest='plot', action='store_const', const=True,
                    default=False, help='plot')
parser.add_argument('-comp', dest='compare', action='store_const', const=True,
                    default=False, help='compare outputs')

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

gen = 1
for n in range(args.tests):
    print("Generating test", gen)

    if not os.path.exists(args.out+str(gen)+"/"):
        os.makedirs(args.out+str(gen)+"/")

    directory = args.out+str(gen)+"/"

    # Generate a random graph and transformations with alea_gen.py
    process = subprocess.check_output(("python3 -W ignore "+args.file+" -o %s -n %s -e %s -t %s -ext %s%s%s%s%s" %
              (args.input, args.nodes, args.edges, args.trans, args.ext,
               " --meta "+args.meta if args.meta != None else '',
               ' --di' if args.di else '',
               ' --debug' if args.debug else '',
               ' -p' if args.plot else '')).split(" "))
    print(process.decode("UTF-8"), end='')

    # Import the meta-model, by default alea_gen.py creates a random graph without attributes
    meta = TypedDiGraph(load_file=args.input+'meta'+args.ext) if args.di else TypedGraph(load_file=args.input+'meta'+args.ext)
    meta.export(directory+"meta"+args.ext)
    plot_graph(meta, filename = directory+"meta.png")

    # Import the random graph we generated
    graph = TypedDiGraph(load_file=args.input+'graph'+args.ext) if args.di else TypedGraph(load_file=args.input+'graph'+args.ext)
    graph.export(directory+"graph"+args.ext)
    if args.plot:
        plot_graph(graph, filename = directory+"graph.png")

    # Import the random transformations
    f = open(args.input+'trans.txt', 'r')
    trans_string = f.read()

    # Simplify the random transformations
    simplified = Rewriter.simplify_commands(trans_string)
    fprime = open(directory+'transformations.txt', 'w')
    print(trans_string, file=fprime, end='')

    # Create the transformer instance (we only use it for the apply_rule method
    # since do_rewrite and do_canonical_rewrite create their own transformer
    # with the transformations we provide them but we compute it every time
    # to print the P, L and R instance)
    trans = Rewriter.transformer_from_command(graph, simplified)
    f = open(directory+"transformer.txt", "w")
    trans.P.export(directory+"trans_P"+args.ext)
    trans.L.export(directory+"trans_LHS"+args.ext)
    trans.R.export(directory+"trans_RHS"+args.ext)
    if args.plot:
        plot_graph(trans.P, filename = directory+"trans_P.png")
        plot_graph(trans.L, filename = directory+"trans_LHS.png")
        plot_graph(trans.R, filename = directory+"trans_RHS.png")

    # Do the rewriting with the methods that the user wants
    methods = args.methods.split(";")
    if "prop" in methods or "all" in methods:
        # Tries to do all the transformations in one step
        g1 = graph.copy()

        result = Rewriter.do_rewrite(g1, simplified)

        result.export(directory+"result_cat_op"+args.ext)
        if args.plot:
            plot_graph(result, filename = directory+"result_cat_op.png")

    if "rew" in methods or "all" in methods:
        # Uses apply_rule function, doesn't generate homomorphisms for the
        # propagation of changes
        g2 = graph.copy()
        rw = Rewriter(g2)

        rw.apply_rule(Homomorphism.identity(trans.L, trans.G), trans)

        g2.export(directory+"result_rul"+args.ext)
        if args.plot:
            plot_graph(g2, filename = directory+"result_rul.png")

    if "canonic" in methods or "all" in methods:
        # Tries to respect the intuitive behaviour of the transformations
        # by doing multiple steps of rewriting while keeping the necessary
        # informations for the propagation
        g3 = graph.copy()

        print("\nSimplified:\n%s\n" % simplified, file=fprime)
        print("\nCanonical:\nTrans:\n%s\n" % ("\nTrans:\n".join(Rewriter.make_canonical_commands(g3, simplified, args.di))), file = fprime)

        result_can = Rewriter.do_canonical_rewrite(g3, simplified)

        result_can.export(directory+"result_canonic"+args.ext)
        if args.plot:
            plot_graph(result_can, filename = directory+"result_canonic.png")

    if args.compare :
        # We compare the results of the methods we used and print the differences
        # between graphs if differences there are
        f = open(directory+"compare.txt", 'w')
        for i in range(len(methods)):
            for j in range(i+1, len(methods)):
                m1 = methods[i]
                m2 = methods[j]
                if m1 != m2:
                    if m1 == "prop":
                        r1 = result
                    elif m1 == "rew":
                        r1 = g2
                    elif m1 == "canonic":
                        r1 = result_can

                    if m2 == "prop":
                        r2 = result
                    elif m2 == "rew":
                        r2 = g2
                    elif m2 == "canonic":
                        r2 = result_can

                    if r1 == r2:
                        print("%s == %s" % (m1, m2), file=f)
                    else:
                        print("%s != %s:" % (m1, m2), file=f)
                        print("Nodes in %s and not in %s:" % (m1,m2), file=f)
                        print([n for n in r1.nodes() if n not in r2.nodes()], file=f)
                        print("Nodes in %s and not in %s:" % (m2,m1), file=f)
                        print([n for n in r2.nodes() if n not in r1.nodes()], file=f)
                        print("Edges in %s and not in %s:" % (m1,m2), file=f)
                        print([n for n in r1.edges() if n not in r2.edges()], file=f)
                        print("Edges in %s and not in %s:" % (m2,m1), file=f)
                        print([n for n in r2.edges() if n not in r1.edges()], file=f)
                        print("", file=f)

                        for n in r1.nodes():
                            if n in r2.nodes():
                               if r1.node[n].type_ != r2.node[n].type_:
                                   print("Node %s in %s have type %s while having type %s in %s" %
                                         (n, m1, r1.node[n].type_, r2.node[n].type_, m2), file=f)
                               if r1.node[n].attrs_ != r2.node[n].attrs_:
                                   print("Node %s in %s have attrs %s while having attrs %s in %s" %
                                         (n, m1, r1.node[n].attrs_, r2.node[n].attrs_, m2), file=f)

                        for e in r1.edges():
                            if e in r2.edges():
                                if r1.get_edge(e[0], e[1]) != r2.get_edge(e[0], e[1]):
                                    print("Edge %s in %s have attrs %s while having attrs %s in %s" %
                                          (e, m1, r1.get_edge(e[0], e[1]) , r2.get_edge(e[0], e[1]) , m2), file=f)


                        print("", file=f)
                        print("%s:\n%s\n" % (m1,r1), file=f)
                        print("%s:\n%s\n" % (m2,r2), file=f)
    gen += 1

    print("Done"+("\n" if args.debug else ''))
