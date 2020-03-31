"""ReGraph hierarchy tutorial ex 2."""
import networkx as nx

from regraph import (Hierarchy, Rule,
                     add_nodes_from,
                     add_edges_from,
                     plot_graph, plot_instance, plot_rule)


# create an empty hierarchy
hierarchy = Hierarchy()

# initialize graphs
colors = nx.DiGraph()
add_nodes_from(
    colors,
    ["red", "blue"]
)
add_edges_from(
    colors,
    [("red", "red"), ("blue", "red"), ("red", "blue")]
)
hierarchy.add_graph("colors", colors)

mmm = nx.DiGraph()
add_nodes_from(
    mmm,
    ["component", "state", "action"]
)

add_edges_from(
    mmm,
    [("component", "action"),
     ("component", "component"),
     ("state", "component"),
     ("action", "state")]
)

hierarchy.add_graph("mmm", mmm)

mm = nx.DiGraph()
add_nodes_from(
    mm,
    ["gene", "residue", "state", "mod"]
)
add_edges_from(
    mm,
    [("residue", "gene"),
     ("state", "gene"),
     ("state", "residue"),
     ("mod", "state"),
     ("gene", "mod")]
)
hierarchy.add_graph("mm", mm)

action_graph = nx.DiGraph()
add_nodes_from(
    action_graph,
    ["A", "A_res_1", "p", "B", "mod"]
)

add_edges_from(
    action_graph,
    [("A_res_1", "A"),
     ("p", "A_res_1"),
     ("mod", "p"),
     ("B", "mod")]
)
hierarchy.add_graph(
    "ag", action_graph
)

nugget_1 = nx.DiGraph()
add_nodes_from(
    nugget_1,
    ["A", "A_res_1", "p", "B", "mod"]
)
add_edges_from(
    nugget_1,
    [("A_res_1", "A"),
     ("p", "A_res_1"),
     ("mod", "p"),
     ("B", "mod")]
)
hierarchy.add_graph(
    "n1", nugget_1
)

# add typings
hierarchy.add_typing(
    "mm", "mmm",
    {
        "gene": "component",
        "residue": "component",
        "state": "state",
        "mod": "action"
    }
)

hierarchy.add_typing(
    "mm", "colors",
    {
        "gene": "red",
        "residue": "red",
        "state": "red",
        "mod": "blue"
    }
)
hierarchy.add_typing(
    "ag", "mm",
    {
        "A": "gene",
        "B": "gene",
        "A_res_1": "residue",
        "mod": "mod",
        "p": "state"
    }
)
hierarchy.add_typing(
    "n1", "ag",
    dict((n, n) for n in nugget_1.nodes()),
)

colors_pos = plot_graph(
    hierarchy.graph["colors"], title="Graph 'colors'")
mmm_pos = plot_graph(
    hierarchy.graph["mmm"], title="Graph 'mmm' (meta-meta-model)")
mm_pos = plot_graph(
    hierarchy.graph["mm"], title="Graph 'mm' (meta-model)")
ag_pos = plot_graph(
    hierarchy.graph["ag"], title="Graph 'ag' (action graph)")
n1_pos = plot_graph(
    hierarchy.graph["n1"], title="Graph 'n1' (nugget)")

# define a rule that clones nodes
pattern = nx.DiGraph()
add_nodes_from(pattern, ["gene", "residue"])
add_edges_from(pattern, [("residue", "gene")])

cloning_rule = Rule.from_transform(pattern)
clone_name, _ = cloning_rule.inject_clone_node("gene")
cloning_rule.inject_remove_edge("residue", clone_name)

print("\nRule 1: contains cloning of nodes")
print("---------------------------------")
print(cloning_rule)
plot_rule(cloning_rule, title="Rule 1: contains cloning of nodes")

lhs_typing = {
    "mm": {"gene": "gene", "residue": "residue"}
}
print("with the typing of the left-hand side: ", lhs_typing)

# find matching of the lhs of the cloning rule in 'ag'
instances = hierarchy.find_matching(
    "ag", cloning_rule.lhs, lhs_typing)
print("Instances of the lhs found in 'ag': ", instances)
for i, instance in enumerate(instances):
    plot_instance(
        hierarchy.graph["ag"], cloning_rule.lhs,
        instance, parent_pos=ag_pos,
        title="Graph 'ag' with instance {} highlighted".format(i + 1))

print("\t-> Applying the rule to the instance of 'ag': ", instances[0])

_, rhs_instance = hierarchy.rewrite("ag", cloning_rule, instances[0])

print("\tResult of rewriting with rule 1: ")
plot_instance(hierarchy.graph["ag"], cloning_rule.rhs, rhs_instance,
              parent_pos=ag_pos)
plot_graph(hierarchy.graph["n1"],
           title="Graph 'n1' after rewriting with rule 1", parent_pos=n1_pos)
print("\t\tUpdated typing 'n1'->'ag': ", hierarchy.edge["n1"]["ag"].mapping)
print("\t\tUpdated typing 'ag'->'mm': ", hierarchy.edge["ag"]["mm"].mapping)


# create a rule that adds new nodes
p = nx.DiGraph()
add_nodes_from(p, ["B"])

l = nx.DiGraph()
add_nodes_from(l, ["B"])

r = nx.DiGraph()
add_nodes_from(r, ["B", "B_res_1", "X", "Y"])
add_edges_from(r, [("B_res_1", "B")])

rule = Rule(p, l, r)
print("\nRule 2: contains addition of nodes ")
print("----------------------------------")
print(rule)
plot_rule(rule, title="Rule 2: contains addition of nodes")

instance = {"B": "B"}
plot_instance(
    hierarchy.graph["n1"], rule.lhs, instance,
    title="Graph 'n1' with the instance of a pattern highlighted",
    parent_pos=n1_pos)

# define the right-hand side typing of the rule
rhs_typing = {
    "mm": {"B_res_1": "residue"},
    "mmm": {"X": "component"},
    "colors": {"Y": "red"}
}
print("with the typing of the right-hand side: ", rhs_typing)

print("\t->Applying the rule to the instance: ", instance)

# perform rewriting
_, rhs_instance = hierarchy.rewrite(
    "n1", rule, instance, lhs_typing=None, rhs_typing=rhs_typing)

print("\tResult of rewriting with rule 2: ")
plot_instance(
    hierarchy.node["n1"].graph, rule.rhs, rhs_instance, parent_pos=n1_pos,
    title="Graph 'n1' after rewriting with rule 2 "
          "(instance of the rhs highlighted)")
plot_graph(hierarchy.node["ag"].graph, parent_pos=ag_pos,
           title="Graph 'ag' after rewriting with rule 2")
plot_graph(hierarchy.node["mm"].graph, parent_pos=mm_pos,
           title="Graph 'mm' after rewriting with rule 2")
plot_graph(hierarchy.node["mmm"].graph, parent_pos=mmm_pos,
           title="Graph 'mmm' after rewriting with rule 2")
plot_graph(hierarchy.node["colors"].graph, parent_pos=colors_pos,
           title="Graph 'colors' after rewriting with rule 2")

print("\t\tUpdated typing 'n1'->'ag': ", hierarchy.edge["n1"]["ag"].mapping)
print("\t\tUpdated typing 'ag'->'mm': ", hierarchy.edge["ag"]["mm"].mapping)
print("\t\tUpdated typing 'mm'->'mmm': ", hierarchy.edge["mm"]["mmm"].mapping)
print("\t\tUpdated typing 'mm'->'colors': ",
      hierarchy.edge["mm"]["colors"].mapping)

# define a rule that merges nodes
pattern = nx.DiGraph()
pattern.add_nodes_from([1, 2])
pattern.add_edges_from([(2, 1)])
merging_rule = Rule.from_transform(pattern)
merging_rule.inject_remove_edge(2, 1)
merging_rule.inject_merge_nodes([1, 2], "hybrid")
print("\nRule 3: contains merge of nodes")
print("-------------------------------")
print(merging_rule)

lhs_typing = {"mm": {1: "gene", 2: "residue"}}
rhs_typing = {"mmm": {"hybrid": "component"}}

print("with the typing of the left-hand side: ", lhs_typing)
print("with the typing of the right-hand side: ", rhs_typing)


plot_rule(merging_rule, title="Rule 3: contains merge of nodes")

instances = hierarchy.find_matching("n1", merging_rule.lhs, lhs_typing)

print("\t-> Applying the rule to the instance of 'n1': ", instances[0])
hierarchy.rewrite(
    "n1", merging_rule, instances[0], rhs_typing)


print("\t-> Applying the rule to the instance of 'n1': ", instances[1])
hierarchy.rewrite(
    "n1", merging_rule, instances[1], rhs_typing)


print("\tResult of rewriting with rule 3 both instances ({}): ".format(
    instances))
plot_graph(hierarchy.node["n1"].graph, parent_pos=n1_pos,
           title="Graph 'n1' after rewriting with rule 3")
plot_graph(hierarchy.node["ag"].graph, parent_pos=ag_pos,
           title="Graph 'ag' after rewriting with rule 3")
plot_graph(hierarchy.node["mm"].graph, parent_pos=mm_pos,
           title="Graph 'mm' after rewriting with rule 3")
print("\t\tUpdated typing 'n1'->'ag': ", hierarchy.edge["n1"]["ag"].mapping)
print("\t\tUpdated typing 'ag'->'mm': ", hierarchy.edge["ag"]["mm"].mapping)
print("\t\tUpdated typing 'mm'->'mmm': ", hierarchy.edge["mm"]["mmm"].mapping)
print("\t\tUpdated typing 'mm'->'colors': ",
      hierarchy.edge["mm"]["colors"].mapping)
