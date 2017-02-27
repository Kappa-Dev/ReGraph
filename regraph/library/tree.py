"""Functions for manipulating a hierarchy as a tree"""
from regraph.library.hierarchy import GraphNode
import networkx as nx

import copy


from regraph.library.primitive import graph_to_json
from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import Homomorphism, TypedHomomorphism
from regraph.library.rewriters import Transformer
from regraph.library.rewriters import Rewriter
from regraph.library.rules import Rule
from regraph.library.category_op import pushout

import json
from regraph.library.nugget_rules import AbstractRules


# def unique_node_id(self, prefix):
#     """ generate a new node id """
#     return self.graph.unique_node_id(prefix)

# TODO: put inside hierarchy
def unique_graph_id(hie, prefix):
    """ generate a new graph id """
    if prefix not in hie.nodes():
        return prefix
    i = 0
    while "{}_{}".format(prefix, i) in hie.nodes():
        i += 1
    return "{}_{}".format(prefix, i)


def graph_children(hie, g_id):
    """Returns the graphs (even partially) typed by g_id"""
    return (source for source, _ in hie.in_edges(g_id)
            if isinstance(hie.node[source], GraphNode))


def all_children(hie, g_id):
    """Returns all the nodes (even partially) typed by g_id"""
    return (source for source, _ in hie.in_edges(g_id))


# TODO: include rules
def to_json_tree(hie, g_id, parent, include_rules=True,
                 include_graphs=True, depth_bound=None):
    """export a hierarchy as a json tree with root g_id"""
    if depth_bound and depth_bound <= 0:
        children = []
    elif depth_bound:
        children = [to_json_tree(hie, c, g_id, include_rules, include_graphs,
                                 depth_bound - 1)
                    for c in graph_children(hie, g_id)]
    else:
        children = [to_json_tree(hie, c, g_id, include_rules,
                                 include_graphs, None)
                    for c in graph_children(hie, g_id)]

    json_data = {"name": hie.node[g_id].attrs["name"],
                 "children": children}

    if include_graphs:
        json_data["top_graph"] = (graph_to_json(hie.node[g_id].graph)
                                  if hie.node[g_id].graph is not None
                                  else None)
        if parent is not None:
            json_data["typing"] = hie.edge[g_id, parent].mapping
    # if include_rules:
    #     h["rules"] = [r.to_json_like() for r in self.subRules.values()]
    return json_data


def valid_child_name(hie, g_id, new_name):
    """ check if node g_id already has a child named new_name"""
    children_name = [hie.node[source].attr["name"]
                     for source in all_children(hie, g_id)]
    return new_name not in children_name


def _child_from_name(hie, g_id, name):
    children = [c for c in all_children(hie, g_id)
                if hie.node[c].attrs["name"] == name]
    if len(children) == 0:
        raise ValueError("no child of {} named {}".format(g_id, name))
    if len(children) > 1:
        raise ValueError("{} children of {} named {}"
                         .format(len(children), g_id, name))
    return children[0]


def child_from_path(hie, g_id, path):
    """return the id of the child of g_id according to a path"""
    if path == []:
        return g_id
    elif path[0] == "":
        return child_from_path(hie, g_id, path[1:])
    else:
        child = _child_from_name(hie, g_id, path[0])
        return child_from_path(hie, child, path[1:])

# def updateMetamodel(self, new_typing_graph):
#     self.graph.updateMetamodel(new_typing_graph)

# def updateSubMetamodels(self, new_typing_graph):
#     if all(sub.graph.validNewMetamodel(new_typing_graph)
#             for sub in self.subCmds.values())\
#         and all(rule.validNewMetamodel(new_typing_graph)
#                 for rule in self.subRules.values()):
#         for sub in self.subCmds.values():
#             sub.updateMetamodel(new_typing_graph)
#         for rule in self.subRules.values():
#             rule.updateMetamodel(new_typing_graph)
#     else:
#         raise ValueError("Metamodel update cannot work")


def new_child(hie, g_id, name):
    if valid_child_name(hie, g_id, name):
        ch_id = unique_graph_id(hie, name)
        new_graph = nx.DiGraph()
        hie.add_graph(ch_id, new_graph, {"name": name})
        hie.add_typing(ch_id, g_id, {})


def add_node(hie, g_id, parent, node_id, nodeType):
    if isinstance(hie.node[g_id], GraphNode):
        if node_id not in hie.node[g_id].graph.nodes():
            hie.node[g_id].graph.add_node(node_id)
        if parent is not None:
            hie.edge[g_id][parent].mapping[node_id] = nodeType
    else:
        raise(ValueError("todo rules"))


def add_edge(self, node1, node2):
    tr = Transformer(self.graph)
    tr.add_edge(node1, node2)
    self.graph = Rewriter.rewrite_simple(tr)
    self.updateSubMetamodels(self.graph)


def _do_rm_node_not_catched(self, nodeId):
    tr = Transformer(self.graph)
    tr.remove_node(nodeId)
    new_graph = Rewriter.rewrite_simple(tr)
    self.updateSubMetamodels(new_graph)
    self.graph = new_graph


def _do_rm_node_force_not_catched(self, nodeId):
    for sub in self.subCmds.values():
        for n in sub.graph.nodes():
            if sub.graph.node[n].type_ == nodeId:
                sub._do_rm_node_force_not_catched(n)
    for rule in self.subRules.values():
        rule.removeType(nodeId)

    tr = Transformer(self.graph)
    tr.remove_node(nodeId)
    new_graph = Rewriter.rewrite_simple(tr)
    self.updateSubMetamodels(new_graph)
    self.graph = new_graph


def remove_attrs(self, node, attr_dict, force=False):
    new_graph = copy.deepcopy(self.graph)
    new_graph.remove_node_attrs(node, attr_dict)
    self.updateSubMetamodels(new_graph)
    self.graph = new_graph


def _do_merge_nodes_not_catched(self, node1, node2, newName):
    tr = Transformer(self.graph)
    tr.merge_nodes(node1, node2, node_name=newName)
    new_graph = Rewriter.rewrite_simple(tr)
    self.updateSubMetamodels(new_graph)
    self.graph = new_graph


def _do_merge_nodes_force_not_catched(self, node1, node2, newName):
    tr = Transformer(self.graph)
    tr.merge_nodes(node1, node2, node_name=newName)
    new_graph = Rewriter.rewrite_simple(tr)
    for sub in self.subCmds.values():
        sub.graph.convertType(node1, newName)
        sub.graph.convertType(node2, newName)
    for rule in self.subRules.values():
        rule.convertType(node1, newName)
        rule.convertType(node2, newName)
    self.updateSubMetamodels(new_graph)
    self.graph = new_graph


def rename_node(self, node_id, new_name):
    self.graph.myRelabelNode(node_id, new_name)
    for sub in self.subCmds.values():
        sub.graph.convertType(node_id, new_name)
    for rule in self.subRules.values():
        rule.convertType(node_id, new_name)


def _do_clone_node_not_catched(self, node1, clone_name):
    tr = Transformer(self.graph)
    tr.clone_node(node1, clone_name)
    self.graph = Rewriter.rewrite_simple(tr)
    self.updateSubMetamodels(self.graph)


def _do_rm_edge_uncatched(self, node1, node2, force):
    if force:
        for sub in self.subCmds.values():
            for (n1, n2) in sub.graph.edges():
                if (sub.graph.node[n1].type_ == node1 and
                        sub.graph.node[n2].type_ == node2):
                    sub._do_rm_edge_uncatched(n1, n2, force=True)
        for rule in self.subRules.values():
            rule.removeEdgesByType(node1, node2)
    tr = Transformer(self.graph)
    tr.remove_edge(node1, node2)
    new_graph = Rewriter.rewrite_simple(tr)
    self.updateSubMetamodels(new_graph)
    self.graph = new_graph


def _do_new_rule(self, name, pattern):
    self.subRules[name] = Rule(
        name, self.subCmds[pattern].graph, self)


def get_matchings(self, rule, graphName):
    graph = self.subCmds[graphName].graph
    pattern = self.subRules[rule].transformer.L
    matchings = Rewriter.find_matching(graph, pattern)
    return matchings


def _add_subgraph_no_catching(self, graph, name):
    if name not in self.subCmds.keys():
        self.subCmds[name] = self.__class__(name, self)
        self.subCmds[name].graph = graph
    else:
        raise(KeyError("name already exists"))


def merge_conflict(self, hierarchy):
    if "top_graph" in hierarchy.keys() and hierarchy["top_graph"] is not None:
        top_graph = TypedDiGraph(
            metamodel=self.graph.metamodel_ if self.graph is not None else None)
        top_graph.from_json_like(hierarchy["top_graph"])
    else:
        top_graph = None
    if top_graph != self.graph:
        return(True)
    if "rules" in hierarchy.keys():
        for r in hierarchy["rules"]:
            if r["name"] in self.subRules.keys():
                new_rule = Rule(r["name"],
                                TypedDiGraph(metamodel=top_graph),
                                self)
                new_rule.from_json_like(r)
                if new_rule != self.subRules[r["name"]]:
                    return True
    return any((self.subCmds[child["name"]].merge_conflict(child)
                for child in hierarchy["children"]
                if child["name"] in self.subCmds.keys()))


def merge_hierarchy(self, hierarchy):
    if "top_graph" in hierarchy.keys() and hierarchy["top_graph"] is not None:
        top_graph = TypedDiGraph(metamodel=self.graph.metamodel_)
        top_graph.from_json_like(hierarchy["top_graph"])
    else:
        top_graph = None
    if top_graph != self.graph:
        print("top", top_graph)
        print("self", self.graph)
        raise ValueError("the top graph of the hierarchy\
                            is not the same as the selected graph")
    for child in hierarchy["children"]:
        if child["name"] in self.subCmds.keys():
            self.subCmds[child["name"]].merge_hierarchy(child)
        else:
            self.add_subHierarchy(child)
    if "rules" in hierarchy.keys():
        for r in hierarchy["rules"]:
            if r["name"] not in self.subRules.keys():
                new_rule = Rule(r["name"],
                                TypedDiGraph(metamodel=top_graph),
                                self)
                new_rule.from_json_like(r)
                self.subRules[r["name"]] = new_rule


def add_subHierarchy(self, subHierarchy, force=False):
    g = TypedDiGraph(metamodel=self.graph)
    g.from_json_like(subHierarchy["top_graph"])
    if (subHierarchy["name"] in self.subCmds.keys() or
        subHierarchy["name"] in self.subRules.keys()):
        raise(KeyError("name already exists"))

    # self._add_subgraph_no_catching(g,subHierarchy["name"])
    cmd = self.__class__(subHierarchy["name"], self)
    cmd.graph = g
    for child in subHierarchy["children"]:
        cmd.add_subHierarchy(child)
    if "rules" in subHierarchy.keys():
        for r in subHierarchy["rules"]:
            if (r["name"] in cmd.subCmds.keys() or
                r["name"] in cmd.subRules.keys()):
                raise(KeyError("name " + r["name"] + " already exists"))
            new_rule = Rule(r["name"],
                            TypedDiGraph(metamodel=g), cmd)
            new_rule.from_json_like(r)
            cmd.subRules[r["name"]] = new_rule
    self.subCmds[subHierarchy["name"]] = cmd


def deleteSubCmd(self, name):
    if self.subCmds[name].subCmds or self.subCmds[name].subRules:
        raise ValueError("The graph to delete has children")
    del self.subCmds[name]


def deleteSubRule(self, name):
    del self.subRules[name]


def _do_rename_graph_no_catching(self, old_name, new_name):
    if old_name not in self.subCmds.keys():
        raise ValueError("The graph " + old_name + " does not exist")
    if not self.valid_new_name(new_name):
        raise ValueError("a rule or graph named " +
                         new_name + " already exists")
    self.subCmds[new_name] = self.subCmds.pop(old_name)
    self.subCmds[new_name].name = new_name


def _do_rename_rule_no_catching(self, old_name, new_name):
    if old_name not in self.subRules.keys():
        raise ValueError("The rule " + old_name + " does not exist")
    if not self.valid_new_name(new_name):
        raise ValueError("a rule or graph named " +
                         new_name + " already exists")
    self.subRules[new_name] = self.subRules.pop(old_name)
    self.subRules[new_name].name = new_name


def get_children(self, node_id):
    if node_id not in self.graph.nodes():
        raise ValueError("the node is not in the graph")
    nugget_list = []
    for sub in self.subCmds.values():
        g = sub.graph
        for n in g.nodes():
            if g.node[n].type_ == node_id:
                nugget_list.append(sub.name)
                break
    return nugget_list


def ancestors_aux(self, degree):
    if not self.parent:
        raise ValueError("the command does not have a parent")
    if degree == 1:
        return {n: self.graph.node[n].type_ for n in self.graph.nodes()}
    else:
        parentMapping = self.parent.ancestors_aux(degree-1)
        return {n: parentMapping[self.graph.node[n].type_]
                for n in self.graph.nodes()}


def ancestors(self, degree):
    mapping = self.ancestors_aux(degree)
    return [{"left": n, "right": t} for (n, t) in mapping.items()]


def merge_graphs(self, name1, name2, mapping, new_name):
    """ merge two graph based on an identity relation
        between their nodes.
        We first build a span from the given relation.
        The new graph is then computed as the pushout. """
    if not self.valid_new_name(new_name):
        raise ValueError("name {} already exists")
    if name1 not in self.subCmds.keys():
        raise ValueError("{} not found".format(name1))
    if name2 not in self.subCmds.keys():
        raise ValueError("{} not found".format(name2))
    g1 = self.subCmds[name1].graph
    g2 = self.subCmds[name2].graph
    g0 = TypedDiGraph(self.graph)
    left_mapping = {}
    right_mapping = {}
    for (n1, n2) in mapping:
        new_node = g0.unique_node_id(n2)
        new_type = g2.node[n2].type_ if self.graph is not None else None
        g0.add_node(new_node, new_type)
        left_mapping[new_node] = n1
        right_mapping[new_node] = n2
    print("g0", g0)
    print("g1", g1)
    print("leftMapping", left_mapping)
    h1 = Homomorphism(g0, g1, left_mapping)
    h2 = Homomorphism(g0, g2, right_mapping)
    (new_graph, g1_new_graph, g2_new_graph) = pushout(h1, h2)
    new_cmd = self.__class__(new_name, self)
    new_cmd.graph = new_graph
    self.subCmds[new_name] = new_cmd

    def copy_nugget(sub, type_mapping):
        sub_copy = copy.deepcopy(sub)
        sub_copy.parent = new_cmd
        sub_copy.graph.convert_types(type_mapping)
        sub_copy.graph.updateMetamodel(new_graph)
        if new_cmd.valid_new_name(sub.name):
            new_cmd.subCmds[sub.name] = sub
        else:
            new_sub_name = new_cmd.unique_graph_id(sub.name)
            sub.name = new_sub_name
            new_cmd.subCmds[new_sub_name] = sub

    for sub in self.subCmds[name1].subCmds.values():
        copy_nugget(sub, g1_new_graph.mapping_)
    for sub in self.subCmds[name2].subCmds.values():
        copy_nugget(sub, g2_new_graph.mapping_)
