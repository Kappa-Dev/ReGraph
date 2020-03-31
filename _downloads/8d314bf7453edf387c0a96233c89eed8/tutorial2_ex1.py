"""ReGraph hierarchy tutorial ex 1."""
import networkx as nx

from regraph import Hierarchy, plot_graph, primitives

# create an empty hierarchy
hierarchy = Hierarchy()

# initialize graphs `t` & `g`
t = nx.DiGraph()
primitives.add_nodes_from(
    t, ["agent", "action", "state"])
primitives.add_edges_from(
    t,
    [
        ("agent", "agent"),
        ("state", "agent"),
        ("agent", "action"),
        ("action", "state")
    ])

g = nx.DiGraph()
primitives.add_nodes_from(
    g, ["protein", "region", "activity", "mod"])
primitives.add_edges_from(
    g,
    [
        ("region", "protein"),
        ("activity", "protein"),
        ("activity", "region"),
        ("protein", "mod"),
        ("region", "mod"),
        ("mod", "activity")
    ])

# add graphs to the hierarchy
hierarchy.add_graph("T", t)
hierarchy.add_graph("G", g)

# add typing of `g` by `t`
mapping = {
    "protein": "agent",
    "region": "agent",
    "activity": "state",
    "mod": "action"
}
hierarchy.add_typing("G", "T", mapping)

# plot graphs
plot_graph(hierarchy.graph["T"],
           title="Graph 'T'")
plot_graph(hierarchy.graph["G"],
           title="Graph 'G'")

print("Graphs in the hierarchy: ", hierarchy.graphs())
print("Typings in the hierarchy: ", hierarchy.typings())
print("Typing of node '{}' in the graph '{}': {}".format(
    "region", "G", hierarchy.node_type("G", "region")))


print("\nAdding new node ('{}') in the hierarchy...".format("model"))

# initialize a new graph `model` and add it to the hierarchy
# typing it by `g`
model = nx.DiGraph()
primitives.add_nodes_from(
    model,
    ["A", "R", "B", "B_activity",
     "A_activity", "activation"])
primitives.add_edges_from(model, [
    ("R", "A"),
    ("R", "activation"),
    ("activation", "B_activity"),
    ("B_activity", "B"),
    ("activation", "A_activity"),
    ("A_activity", "A")
])
hierarchy.add_graph("model", model)

mapping = {
    "A": "protein",
    "R": "region",
    "B": "protein",
    "B_activity": "activity",
    "A_activity": "activity",
    "activation": "mod"
}
hierarchy.add_typing("model", "G", mapping)
plot_graph(hierarchy.graph["model"],
           title="Graph 'model'")

print("Typings in the hierarchy: ", hierarchy.typings())

print("\nRemoving node '{}' from the hierarchy...".format("G"))
# remove node `g` from the hierarchy and reconnect its predecessors
# with its successors
hierarchy.remove_node("G", reconnect=True)
print("Typings in the hierarchy...", hierarchy.typings())
print(
    "Typing of '{}' by '{}'".format("model", "T"),
    hierarchy.typing["model"]["T"])

print("\nAdding new graph {}...".format("catalysis"))
# create new graph `catalysis`
catalysis = nx.DiGraph()
primitives.add_nodes_from(
    catalysis,
    ["enzyme", "substrate",
     "mod", "mod_state"]
)
primitives.add_edges_from(catalysis, [
    ("enzyme", "mod"),
    ("mod", "mod_state"),
    ("mod_state", "substrate")
])

hierarchy.add_graph("catalysis", catalysis)

plot_graph(hierarchy.graph["catalysis"],
           title="Graph 'catalysis'")

print("\nCreating a relation between '{}' and '{}'".format(
    "model", "catalysis"))
# initialize binary symmetric relation between
# `catalysis` and `model` and add it to the hierarchy
relation = {
    "A": {"enzyme", "substrate"},
    "B": "substrate",
    "B_activity": "mod_state",
    "A_activity": "mod_state",
    "activation": "mod"
}
hierarchy.add_relation('model', 'catalysis', relation)
print(
    "Relation ({}-{}): ".format("model", "catalysis"),
    hierarchy.relation['model']['catalysis'])
print(
    "Relation ({}-{}): ".format("catalysis", "model"),
    hierarchy.relation['catalysis']['model'])
