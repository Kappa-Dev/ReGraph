"""ReGraph tutorial part 1."""
import networkx as nx
import regraph as rg


# create a graph
graph = nx.DiGraph()

nodes = [
    (1, {"name": "alice", "color": "blue"}),
    (2, {"name": "bob", "color": "blue"}),
    (3, {"name": "john", "color": "red"})
]
edges = [
    (1, 2),
    (3, 2, {"friends": False})
]
rg.add_nodes_from(graph, nodes)
rg.add_edges_from(graph, edges)

rg.plot_graph(graph)

# perform primitive graph transformations
rg.add_node_attrs(graph, 1, {"age": 20})
print("Attributes of the node '1': ", graph.node[1])
rg.add_edge_attrs(graph, 1, 2, {"friends": True})
print("Attributes of the edge '1'->'2': ", graph.edge[1][2])
rg.remove_node_attrs(graph, 3, {"color": "red"})
print("Attributes of the node '3': ", graph.node[3])
rg.remove_edge_attrs(graph, 3, 2, {"friends": False})
print("Attributes of the edge '3'->'2': ", graph.edge[3][2])
rg.clone_node(graph, 2, "2_clone")
print("Nodes after cloning: ", graph.nodes())
print("Edges after cloning: ", graph.edges())
rg.merge_nodes(graph, [1, 3])
print("Nodes after merging: ", graph.nodes())
print("Edges after merging: ", graph.edges())
print("Attributes of the merge node '1_3': ", graph.node["1_3"])
print("Attributes of the edge '1_3'->'2': ", graph.edge["1_3"][2])
print("Attributes of the edge '1_3'->'2': ", graph.edge["1_3"]["2_clone"])

# convert graph to its json representation
json_data = rg.graph_to_json(graph)
print("Keys: ", json_data.keys())
print("Nodes representation: ")
print(json_data["nodes"])
print("Edges representation: ")
print(json_data["edges"])

# define a pattern graph
pattern = nx.DiGraph()
rg.add_nodes_from(pattern, ["x", "y"])
rg.add_edges_from(pattern, [("x", "y", {"friends": True})])
rg.print_graph(pattern)

# find its instances in the original graph
instances = rg.find_matching(graph, pattern)
print("instances of the pattern: ", instances)

# remove some edge attrs
rg.remove_edge_attrs(graph, "1_3", 2, {"friends": {True}})

# find instances of the pattern again
instances = rg.find_matching(graph, pattern)
print("instances of the pattern after edge attrs removal: ", instances)


