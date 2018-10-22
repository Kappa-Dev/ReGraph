import time
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pickle
import importlib
import regraph
import uuid

from scipy import stats

from regraph import Rule, plot_rule, clone_node, merge_nodes, add_node, add_edge, remove_node, remove_edge
from regraph.neo4j.graphs import Neo4jGraph
from regraph.neo4j.cypher_utils import *

import statsmodels.api as sm


def simplify_graph(g):
    simple_g = nx.DiGraph()
    simple_g.add_nodes_from(g.nodes())
    simple_g.add_edges_from(set(g.edges()))
    return simple_g

def detect_outliers(x, y):
    log_x = np.log2(x)
    log_y = np.log2(y)
    lm = sm.OLS(log_x, log_y).fit()
    test =lm.outlier_test()
    outliers = np.where(test[:, 2] < 0.5)[0]
    return outliers.tolist()


def clone_benchmark(stats, graphs, samples=30):
    # Connect the db
    neo4j_g = Neo4jGraph("bolt://localhost:7687", "neo4j", "admin") 

    stats["neo4j"]["full_clone"] = []
    stats["neo4j"]["no_id_gen_clone"] = []
    stats["nx"]["clone"] = []
    # Collect statistics on clone
    for g in graphs:

        graph = nx.relabel_nodes(g, {n: "n" + str(n) for n in g.nodes()})
        
        print("Graph of size {}...".format(len(graph.nodes())))

        # dump graph into 'graph.csv'
        with open('/var/lib/neo4j/import/graph.csv', "w+") as f:
            f.write("uId,vId\n")
            for u, v in graph.edges():
                f.write("{},{}\n".format(u, v))

        # load csv into neo4j database
        neo4j_g.clear()
        load_csv_query =\
            "LOAD CSV WITH HEADERS FROM 'file:///graph.csv' AS csvLine " +\
            "MERGE (u:node {id: csvLine.uId }) " +\
            "MERGE (v:node {id: csvLine.vId }) " +\
            "CREATE (u)-[:edge]->(v) "
        neo4j_g.execute(load_csv_query)
        nodes = graph.nodes()

        # select 100 random nodes to clone
        random_nodes = np.random.choice(nodes, samples)

        # Clone with no pretty id's generation
        elapsed_times = []
        for node in random_nodes:
            start = time.time()
            res = neo4j_g.clone_node(node, ignore_naming=True)
            elapsed_times.append(time.time() - start)
        print("Neo4j no names")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["neo4j"]["no_id_gen_clone"].append((np.mean(elapsed_times), np.var(elapsed_times)))
    
        # Clone with pretty id's + ignore edges
        elapsed_times = []
        for node in random_nodes:
            start = time.time()
            res = neo4j_g.clone_node(node)
            elapsed_times.append(time.time() - start)
        print("Neo4j")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["neo4j"]["full_clone"].append((np.mean(elapsed_times), np.var(elapsed_times)))

        # Clone with nx
        elapsed_times = []
        for node in random_nodes:
            start = time.time()
            res = clone_node(graph, node)
            elapsed_times.append(time.time() - start)
        print("Nx")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["nx"]["clone"].append((np.mean(elapsed_times), np.var(elapsed_times)))


def merge_benchmark(stats, graphs, samples=30):
    # Connect the db
    neo4j_g = Neo4jGraph("bolt://localhost:7687", "neo4j", "admin") 

    stats["neo4j"]["full_merge"] = []
    stats["neo4j"]["no_id_gen_merge"] = []
    stats["nx"]["merge"] = []
    # Collect statistics on merge
    for g in graphs:
        
        graph = nx.relabel_nodes(g, {n: "n" + str(n) for n in g.nodes()})
        
        print("Graph of size {}...".format(len(graph.nodes())))

        # dump graph into 'graph.csv'
        with open('/var/lib/neo4j/import/graph.csv', "w+") as f:
            f.write("uId,vId\n")
            for u, v in graph.edges():
                f.write("{},{}\n".format(u, v))

        # load csv into neo4j database
        neo4j_g.clear()
        load_csv_query =\
            "LOAD CSV WITH HEADERS FROM 'file:///graph.csv' AS csvLine " +\
            "MERGE (u:node {id: csvLine.uId }) " +\
            "MERGE (v:node {id: csvLine.vId }) " +\
            "CREATE (u)-[:edge]->(v) "
        neo4j_g.execute(load_csv_query)
        nodes = graph.nodes()

        # select random nodes to clone
        random_nodes1 = []
        random_nodes2 = []
        visited = set()

        # Clone with no pretty id's generation
        for i in range(samples):
            node1 = str(list(np.random.choice(nodes, 1))[0])
            node2 = str(list(np.random.choice(nodes, 1))[0])
            while node1 in visited or node2 in visited or node1 == node2:
                node1 = str(list(np.random.choice(nodes, 1))[0])
                node2 = str(list(np.random.choice(nodes, 1))[0])
            random_nodes1.append(node1)
            random_nodes2.append(node2)
            visited.add(node1)
            visited.add(node2)
            
        elapsed_times = []
        for i in range(len(random_nodes1)):
            node1 = random_nodes1[i]
            node2 = random_nodes2[i]

            start = time.time()
            res = neo4j_g.merge_nodes([node1, node2], ignore_naming=True)
            elapsed_times.append(time.time() - start)
        print("Neo4j no names")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["neo4j"]["no_id_gen_merge"].append((np.mean(elapsed_times), np.var(elapsed_times)))
        
        # load csv into neo4j database
        neo4j_g.clear()
        load_csv_query =\
            "LOAD CSV WITH HEADERS FROM 'file:///graph.csv' AS csvLine " +\
            "MERGE (u:node {id: csvLine.uId }) " +\
            "MERGE (v:node {id: csvLine.vId }) " +\
            "CREATE (u)-[:edge]->(v) "
        neo4j_g.execute(load_csv_query)
        nodes = graph.nodes()
        
        elapsed_times = []
        for i in range(len(random_nodes1)):
            node1 = random_nodes1[i]
            node2 = random_nodes2[i]

            start = time.time()
            res = neo4j_g.merge_nodes([node1, node2])
            elapsed_times.append(time.time() - start)
        print("Neo4j")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["neo4j"]["full_merge"].append((np.mean(elapsed_times), np.var(elapsed_times)))

        # Clone with nx
        elapsed_times = []
        for i in range(len(random_nodes1)):
            node1 = random_nodes1[i]
            node2 = random_nodes2[i]

            start = time.time()
            res = merge_nodes(graph, [node1, node2])
            elapsed_times.append(time.time() - start)
        print("Nx")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["nx"]["merge"].append((np.mean(elapsed_times), np.var(elapsed_times)))


def add_node_benchmark(stats, graphs, samples=30):
    # Connect the db
    neo4j_g = Neo4jGraph("bolt://localhost:7687", "neo4j", "admin") 

    stats["neo4j"]["full_add"] = []
    stats["neo4j"]["no_id_gen_add"] = []
    stats["nx"]["add"] = []
    # Collect statistics on clone
    for g in graphs:

        graph = nx.relabel_nodes(g, {n: "n" + str(n) for n in g.nodes()})
        
        print("Graph of size {}...".format(len(graph.nodes())))

        # dump graph into 'graph.csv'
        with open('/var/lib/neo4j/import/graph.csv', "w+") as f:
            f.write("uId,vId\n")
            for u, v in graph.edges():
                f.write("{},{}\n".format(u, v))

        # load csv into neo4j database
        neo4j_g.clear()
        load_csv_query =\
            "LOAD CSV WITH HEADERS FROM 'file:///graph.csv' AS csvLine " +\
            "MERGE (u:node {id: csvLine.uId }) " +\
            "MERGE (v:node {id: csvLine.vId }) " +\
            "CREATE (u)-[:edge]->(v) "
        neo4j_g.execute(load_csv_query)
        nodes = graph.nodes()

        # generate random nodes to add
        random_nodes = ["uid" + str(uuid.uuid4()).replace("-", "") for n in range(samples)]

        # Clone with no pretty id's generation
        elapsed_times = []
        for node in random_nodes:
            start = time.time()
            res = neo4j_g.add_node(node, ignore_naming=True)
            elapsed_times.append(time.time() - start)
        print("Neo4j no names")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["neo4j"]["no_id_gen_add"].append((np.mean(elapsed_times), np.var(elapsed_times)))
    
        # Clone with pretty id's + ignore edges
        elapsed_times = []
        for node in random_nodes:
            start = time.time()
            res = neo4j_g.add_node(node)
            elapsed_times.append(time.time() - start)
        print("Neo4j")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["neo4j"]["full_add"].append((np.mean(elapsed_times), np.var(elapsed_times)))

        # Clone with nx
        elapsed_times = []
        for node in random_nodes:
            start = time.time()
            res = add_node(graph, node)
            elapsed_times.append(time.time() - start)
        print("Nx")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["nx"]["add"].append((np.mean(elapsed_times), np.var(elapsed_times)))


def add_edge_benchmark(stats, graphs, samples):
    # Connect the db
    neo4j_g = Neo4jGraph("bolt://localhost:7687", "neo4j", "admin") 

    stats["neo4j"]["add_edge"] = []
    stats["nx"]["add_edge"] = []    # Collect statistics on merge
    for g in graphs:
        
        graph = nx.relabel_nodes(g, {n: "n" + str(n) for n in g.nodes()})
        
        print("Graph of size {}...".format(len(graph.nodes())))

        # dump graph into 'graph.csv'
        with open('/var/lib/neo4j/import/graph.csv', "w+") as f:
            f.write("uId,vId\n")
            for u, v in graph.edges():
                f.write("{},{}\n".format(u, v))

        # load csv into neo4j database
        neo4j_g.clear()
        load_csv_query =\
            "LOAD CSV WITH HEADERS FROM 'file:///graph.csv' AS csvLine " +\
            "MERGE (u:node {id: csvLine.uId }) " +\
            "MERGE (v:node {id: csvLine.vId }) " +\
            "CREATE (u)-[:edge]->(v) "
        neo4j_g.execute(load_csv_query)
        nodes = graph.nodes()

        # select random nodes to add edge
        # generate random nodes to add
        random_nodes1 = ["uid" + str(uuid.uuid4()).replace("-", "") for n in range(samples)]
        random_nodes2 = []
        visited = set()

        # Clone with no pretty id's generation
        for node1 in random_nodes1:
            node2 = str(list(np.random.choice(nodes, 1))[0])
            while (node1, node2) in visited:
                node2 = str(list(np.random.choice(nodes, 1))[0])
            random_nodes2.append(node2)
            visited.add((node1, node2))
            
        elapsed_times = []
        for i in range(len(random_nodes1)):
            node1 = random_nodes1[i]
            node2 = random_nodes2[i]

            neo4j_g.add_node(node1)

            start = time.time()
            res = neo4j_g.add_edge(node1, node2)
            elapsed_times.append(time.time() - start)
        print("Neo4j")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["neo4j"]["add_edge"].append((np.mean(elapsed_times), np.var(elapsed_times)))
        
        # add edge with nx
        elapsed_times = []
        for i in range(len(random_nodes1)):
            node1 = random_nodes1[i]
            node2 = random_nodes2[i]

            add_node(graph, node1)

            start = time.time()
            res = add_edge(graph, node1, node2)
            elapsed_times.append(time.time() - start)
        print("Nx")
        print(np.mean(elapsed_times), np.var(elapsed_times))
        stats["nx"]["add_edge"].append((np.mean(elapsed_times), np.var(elapsed_times))) 

def remove_node_benchmark(graphs):
    pass

def remove_edge_benchmark(graphs):
    pass

def individual_benchmark(stats, graphs, samples=30):
    
    new_graphs = []
    for g in graphs:
        simple_g = nx.DiGraph()
        simple_g.add_nodes_from(g.nodes())
        simple_g.add_edges_from(set(g.edges()))
        new_graphs.append(simple_g)

    clone_benchmark(stats, graphs, samples)
    merge_benchmark(stats, new_graphs, samples)
    add_node_benchmark(stats, new_graphs, samples)
    add_edge_benchmark(stats, new_graphs, samples)
    
    return stats


def plot_stat(stats, ns, datatitle=None, log=False):
    fig = plt.figure(figsize=(10, 20))
    
    y1 = [v[0] for v in stats["nx"]["clone"]]
    y2 = [v[0] for v in stats["neo4j"]["full_clone"]]
    y3 = [v[0] for v in stats["neo4j"]["no_id_gen_clone"]]

    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2) +
        detect_outliers(ns, y3))

    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)
    y3 = np.take(y3, filtered_indices)
                                         
    ax = fig.add_subplot(411)
    ax.plot(
        x, y1, "bo",
        x, y2, "ro", 
        x, y3, "go")
    ax.set_xscale('log')
    if log is True:
        ax.set_yscale('log')
    ax.set_title('Time to clone a node')
    ax.set_xlabel('N, size of a graph')
    ax.set_ylabel('Time to clone a node in ms')
    ax.legend(["NetworkX", "Neo4j basic", "Neo4j no ids"])
    
    
    y1 = [v[0] for v in stats["nx"]["add"]]
    y2 = [v[0] for v in stats["neo4j"]["full_add"]]
    y3 = [v[0] for v in stats["neo4j"]["no_id_gen_add"]]
                                         
    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2) +
        detect_outliers(ns, y3))

    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)
    y3 = np.take(y3, filtered_indices)

    ax = fig.add_subplot(412)
    ax.plot(
        x, y1, "bo",
        x, y2, "ro", 
        x, y3, "go")
    ax.set_xscale('log')
    if log is True:
        ax.set_yscale('log')
    ax.set_title('Time to add a node')
    ax.set_xlabel('N, size of a graph')
    ax.set_ylabel('Time to add a node in ms')
    ax.legend(["NetworkX", "Neo4j basic", "Neo4j no ids"])
    
    y1 = [v[0] for v in stats["nx"]["merge"]]
    y2 = [v[0] for v in stats["neo4j"]["full_merge"]]
    y3 = [v[0] for v in stats["neo4j"]["no_id_gen_merge"]]
                                         
    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2) +
        detect_outliers(ns, y3))

    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)
    y3 = np.take(y3, filtered_indices)

    ax = fig.add_subplot(413)
    ax.plot(
        x, y1, "bo",
        x, y2, "ro", 
        x, y3, "go")
    ax.set_xscale('log')
    if log is True:
        ax.set_yscale('log')
    ax.set_title('Time to merge two node')
    ax.set_xlabel('N, size of a graph')
    ax.set_ylabel('Time to merge two node in ms')
    ax.legend(["NetworkX", "Neo4j basic", "Neo4j no ids"])
    
    y1 = [v[0] for v in stats["nx"]["add_edge"]]
    y2 = [v[0] for v in stats["neo4j"]["add_edge"]]
                                         
                                         
    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2))
 
    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)

    ax = fig.add_subplot(414)
    ax.plot(
        x, y1, "bo",
        x, y2, "ro")
    ax.set_xscale('log')
    if log is True:
        ax.set_yscale('log')
    ax.set_title('Time to add an edge')
    ax.set_xlabel('N, size of a graph')
    ax.set_ylabel('Time in ms')
    ax.legend(["NetworkX", "Neo4j basic"])
    
    plt.show()


def plot_aggregated_stat(stats, ns, datatitle=None, log=False):
    fig = plt.figure(figsize=(20, 10))
    ax = fig.add_subplot(111)

    y1 = [v[0] for v in stats["nx"]["clone"]]
    y2 = [v[0] for v in stats["neo4j"]["full_clone"]]
    y3 = [v[0] for v in stats["neo4j"]["no_id_gen_clone"]]

    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2) +
        detect_outliers(ns, y3))

    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)
    y3 = np.take(y3, filtered_indices)
                                         
    ax.plot(
        x, y1, "ro",
        x, y2, "r^", 
        x, y3, "rs")
    ax.set_xscale('log')
    if log is True:
        ax.set_yscale('log')
#     ax.set_title('Time to clone a node')
#     ax.set_xlabel('N, size of a graph')
#     ax.set_ylabel('Time to clone a node in ms')
#     ax.legend(["NetworkX", "Neo4j basic", "Neo4j no ids"])
    
    y1 = [v[0] for v in stats["nx"]["add"]]
    y2 = [v[0] for v in stats["neo4j"]["full_add"]]
    y3 = [v[0] for v in stats["neo4j"]["no_id_gen_add"]]
                                         
    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2) +
        detect_outliers(ns, y3))

    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)
    y3 = np.take(y3, filtered_indices)

#     ax = fig.add_subplot(412)
    ax.plot(
        x, y1, "bo",
        x, y2, "b^", 
        x, y3, "bs")
#     ax.set_xscale('log')
#     if log is True:
#         ax.set_yscale('log')
#     ax.set_title('Time to add a node')
#     ax.set_xlabel('N, size of a graph')
#     ax.set_ylabel('Time to add a node in ms')
#     ax.legend(["NetworkX", "Neo4j basic", "Neo4j no ids"])
    
    y1 = [v[0] for v in stats["nx"]["merge"]]
    y2 = [v[0] for v in stats["neo4j"]["full_merge"]]
    y3 = [v[0] for v in stats["neo4j"]["no_id_gen_merge"]]
                                         
    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2) +
        detect_outliers(ns, y3))

    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)
    y3 = np.take(y3, filtered_indices)

#     ax = fig.add_subplot(413)
    ax.plot(
        x, y1, "go",
        x, y2, "g^", 
        x, y3, "gs")
#     ax.set_xscale('log')
#     if log is True:
#         ax.set_yscale('log')
#     ax.set_title('Time to merge two node')
#     ax.set_xlabel('N, size of a graph')
#     ax.set_ylabel('Time to merge two node in ms')
#     ax.legend(["NetworkX", "Neo4j basic", "Neo4j no ids"])
    
    y1 = [v[0] for v in stats["nx"]["add_edge"]]
    y2 = [v[0] for v in stats["neo4j"]["add_edge"]]
                                                                           
    outliers = set(
        detect_outliers(ns, y1) +
        detect_outliers(ns, y2))
 
    filtered_indices = [i for i in range(len(y1)) if i not in outliers]
    x = np.take(ns, filtered_indices)
    y1 = np.take(y1, filtered_indices)
    y2 = np.take(y2, filtered_indices)

#     ax = fig.add_subplot(414)
#     ax.plot(
#         x, y1, "bo",
#         x, y2, "ro")
#     ax.set_xscale('log')
#     if log is True:
#         ax.set_yscale('log')
#     ax.set_title('Time to add an edge')
#     ax.set_xlabel('N, size of a graph')
#     ax.set_ylabel('Time in ms')
#     ax.legend(["NetworkX", "Neo4j basic"])
    
    plt.show()