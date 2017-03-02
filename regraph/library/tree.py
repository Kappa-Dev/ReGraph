"""Functions for manipulating a hierarchy as a tree"""

import copy
import networkx as nx

from regraph.library.hierarchy import GraphNode
from regraph.library.primitives import graph_to_json, add_node_attrs
from regraph.library.rules import Rule
from regraph.library.category_op import pushout


def _complete_rewrite(hie, g_id, rule, match, lhs_typing=None,
                      rhs_typing=None):
    (lhs_t, rhs_t) = hie.get_complete_typing(g_id, match, lhs_typing,
                                             rhs_typing, rule)
    hie.rewrite(g_id, rule, match, lhs_t, rhs_t)

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
    if not isinstance(hie.node[g_id], GraphNode):
        raise ValueError("node {} must be a graph".format(g_id))
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
        json_data["top_graph"] = typed_graph_to_json(hie, g_id, parent)
        if json_data["top_graph"] is not None:
            json_data["top_graph"]["attributes"] = hie.node[g_id].attrs

    if include_rules:
        json_data["rules"] = []
    #     h["rules"] = [r.to_json_like() for r in self.subRules.values()]
    return json_data


def typed_graph_to_json(hie, g_id, parent):
    if hie.node[g_id].graph is None:
        return None
    json_data = graph_to_json(hie.node[g_id].graph)
    if parent is not None:
        typing = hie.edge[g_id][parent].mapping
        for node in json_data["nodes"]:
            if node["id"] in typing.keys():
                node["type"] = typing[node["id"]]
            else:
                node["type"] = ""
    return json_data



def valid_child_name(hie, g_id, new_name):
    """ check if node g_id already has a child named new_name"""
    children_name = [hie.node[source].attrs["name"]
                     for source in all_children(hie, g_id)]
    return new_name not in children_name

def rename_child(hie, g_id, parent, new_name):
    if valid_child_name(hie, parent, new_name):
        hie.node[g_id].attrs["name"] = new_name
    else:
        raise ValueError("name {} is not valid".format(new_name))

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


def new_graph(hie, g_id, name):
    if valid_child_name(hie, g_id, name):
        ch_id = unique_graph_id(hie, name)
        new_graph = nx.DiGraph()
        hie.add_graph(ch_id, new_graph, {"name": name})
        hie.add_typing(ch_id, g_id, {})
    else:
        raise ValueError("Invalid new name")


# copying typing attributes ?
def new_rule(hie, parent, name, pattern_name=None):
    """create a new rule """
    if valid_child_name(hie, parent, name):
        if pattern_name is None:
            pattern = nx.DiGraph()
        else:
            pattern_id = _child_from_name(hie, parent, pattern_name)
            pattern = hie.node[pattern_id].graph
        rule_id = unique_graph_id(hie, name)
        rule = Rule(pattern, pattern, pattern)
        hie.add_rule(rule_id, rule, {name: name})
        if parent is not None:
            if pattern_name is None:
                hie.add_rule_typing(rule_id, parent, {}, {})
            else:
                mapping = hie.edge[pattern_id][parent].mapping
                hie.add_rule_typing(rule_id, parent, mapping, mapping)
    else:
        raise ValueError("Invalid new name")


# TODO : rules, undirected
def add_node(hie, g_id, parent, node_id, node_type):
    """add a node to a graph in the hierarchy"""
    # if parent is not None and node_type is None:
    #     raise ValueError("node {} must have a type".format(node_id))
    if isinstance(hie.node[g_id], GraphNode):
        if node_id in hie.node[g_id].graph.nodes():
            raise ValueError("node {} already exists in graph".format(node_id))
        lhs = nx.DiGraph()
        ppp = nx.DiGraph()
        rhs = nx.DiGraph()
        rhs.add_node(node_id)
        rule = Rule(ppp, lhs, rhs)
        if node_type is not None:
            rhs_typing = {parent: {node_id: node_type}}
            lhs_typing = {parent: {}}
        else:
            lhs_typing = None
            rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {}, lhs_typing, rhs_typing)

    else:
        raise ValueError("todo rules")

# precondition : total typing by parent
def add_edge(hie, g_id, parent, node1, node2):
    if isinstance(hie.node[g_id], GraphNode):
        lhs = nx.DiGraph()
        lhs.add_node(node1)
        lhs.add_node(node2)
        ppp = nx.DiGraph()
        ppp.add_node(node1)
        ppp.add_node(node2)
        rhs = nx.DiGraph()
        rhs.add_node(node1)
        rhs.add_node(node2)
        rhs.add_edge(node1, node2)
        rule = Rule(ppp, lhs, rhs)
        # if parent is not None:
        #     typing = hie.edge[g_id][parent].mapping
        #     lhs_typing = {parent: {node1: typing[node1],
        #                            node2: typing[node2]}}
        #     rhs_typing = lhs_typing
        # else:
        #     lhs_typing = None
        #     rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {node1: node1, node2: node2})
    else:
        raise ValueError("todo rules")


def rm_node(hie, g_id, parent, node_id, force=False):
    """remove a node from a graph """
    if isinstance(hie.node[g_id], GraphNode):
        if [c for c in all_children(hie, g_id)
                if node_id in hie.edge[c][g_id].mapping.values()]:
            if not force:
                raise ValueError(
                    "some nodes are typed by {}"
                    "set the force argument to"
                    "delete the as well"
                    .format(node_id))

        lhs = nx.DiGraph()
        lhs.add_node(node_id)
        ppp = nx.DiGraph()
        rhs = nx.DiGraph()
        rule = Rule(ppp, lhs, rhs)
        # if parent is not None:
        #     typing = hie.edge[g_id][parent].mapping
        #     lhs_typing = {parent: {node_id: typing[node_id]}}
        #     rhs_typing = {}
        # else:
        #     lhs_typing = None
        #     rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {node_id: node_id})
    else:
        raise ValueError("todo rules")


def merge_nodes(hie, g_id, parent, node1, node2, new_name):
    if isinstance(hie.node[g_id], GraphNode):
        if new_name in hie.node[g_id].graph.nodes():
            raise ValueError("node {} already exists in graph".format(new_name))
        lhs = nx.DiGraph()
        lhs.add_node(node1)
        lhs.add_node(node2)
        ppp = nx.DiGraph()
        ppp.add_node(node1)
        ppp.add_node(node2)
        rhs = nx.DiGraph()
        rhs.add_node(new_name)
        rule = Rule(ppp, lhs, rhs, None, {node1: new_name, node2: new_name})
        # if parent is not None:
        #     typing = hie.edge[g_id][parent].mapping
        #     lhs_typing = {parent: {node1: typing[node1],
        #                            node2: typing[node2]}}
        #     rhs_typing = {parent: {new_name: typing[node1]}}
        # else:
        #     lhs_typing = None
        #     rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {node1: node1, node2: node2})
    else:
        raise ValueError("todo rules")




def clone_node(hie, g_id, parent, node, new_name):
    if isinstance(hie.node[g_id], GraphNode):
        if new_name in hie.node[g_id].graph.nodes():
            raise ValueError("node {} already in graph".format(new_name))
        lhs = nx.DiGraph()
        lhs.add_node(node)
        ppp = nx.DiGraph()
        ppp.add_node(node)
        ppp.add_node(new_name)
        rhs = nx.DiGraph()
        rhs.add_node(node)
        rhs.add_node(new_name)
        rule = Rule(ppp, lhs, rhs, {node: node, new_name: node}, None)
        # if parent is not None:
        #     typing = hie.edge[g_id][parent].mapping
        #     lhs_typing = {parent: {node: typing[node]}}
        #     rhs_typing = {parent: {node: typing[node],
        #                            new_name: typing[node]}}
        # else:
        #     lhs_typing = None
        #     rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {node: node})
    else:
        raise ValueError("todo rules")


def rm_edge(hie, g_id, parent, node1, node2):
    if isinstance(hie.node[g_id], GraphNode):
        lhs = nx.DiGraph()
        lhs.add_node(node1)
        lhs.add_node(node2)
        lhs.add_edge(node1, node2)
        ppp = nx.DiGraph()
        ppp.add_node(node1)
        ppp.add_node(node2)
        rhs = nx.DiGraph()
        rhs.add_node(node1)
        rhs.add_node(node2)
        rule = Rule(ppp, lhs, rhs)
        # if parent is not None:
        #     typing = hie.edge[g_id][parent].mapping
        #     lhs_typing = {parent: {node1: typing[node1],
        #                            node2: typing[node2]}}
        #     rhs_typing = lhs_typing
        # else:
        #     lhs_typing = None
        #     rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {node1: node1, node2: node2})

    else:
        raise ValueError("todo rules")


def add_attributes(hie, g_id, parent, node, attrs):
    if isinstance(hie.node[g_id], GraphNode):
        lhs = nx.DiGraph()
        lhs.add_node(node)
        ppp = nx.DiGraph()
        ppp.add_node(node)
        rhs = nx.DiGraph()
        rhs.add_node(node)
        add_node_attrs(rhs, node, attrs)
        rule = Rule(ppp, lhs, rhs)
        # if parent is not None:
        #     typing = hie.edge[g_id][parent].mapping
        #     lhs_typing = {parent: {node: typing[node]}}
        #     rhs_typing = lhs_typing
        # else:
        #     lhs_typing = None
        #     rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {node: node})
    else:
        raise ValueError("todo rules")


def remove_attributes(hie, g_id, parent, node, attrs):
    if isinstance(hie.node[g_id], GraphNode):
        lhs = nx.DiGraph()
        lhs.add_node(node)
        add_node_attrs(lhs, node, attrs)
        ppp = nx.DiGraph()
        ppp.add_node(node)
        rhs = nx.DiGraph()
        rhs.add_node(node)
        rule = Rule(ppp, lhs, rhs)
        # if parent is not None:
        #     typing = hie.edge[g_id][parent].mapping
        #     lhs_typing = {parent: {node: typing[node]}}
        #     rhs_typing = lhs_typing
        # else:
        #     lhs_typing = None
        #     rhs_typing = None
        _complete_rewrite(hie, g_id, rule, {node: node})
    else:
        raise ValueError("todo rules")


# def merge_conflict(self, hierarchy):
#     if "top_graph" in hierarchy.keys() and hierarchy["top_graph"] is not None:
#         top_graph = TypedDiGraph(
#             metamodel=self.graph.metamodel_ if self.graph is not None else None)
#         top_graph.from_json_like(hierarchy["top_graph"])
#     else:
#         top_graph = None
#     if top_graph != self.graph:
#         return(True)
#     if "rules" in hierarchy.keys():
#         for r in hierarchy["rules"]:
#             if r["name"] in self.subRules.keys():
#                 new_rule = Rule(r["name"],
#                                 TypedDiGraph(metamodel=top_graph),
#                                 self)
#                 new_rule.from_json_like(r)
#                 if new_rule != self.subRules[r["name"]]:
#                     return True
#     return any((self.subCmds[child["name"]].merge_conflict(child)
#                 for child in hierarchy["children"]
#                 if child["name"] in self.subCmds.keys()))


# def merge_hierarchy(self, hierarchy):
#     if "top_graph" in hierarchy.keys() and hierarchy["top_graph"] is not None:
#         top_graph = TypedDiGraph(metamodel=self.graph.metamodel_)
#         top_graph.from_json_like(hierarchy["top_graph"])
#     else:
#         top_graph = None
#     if top_graph != self.graph:
#         print("top", top_graph)
#         print("self", self.graph)
#         raise ValueError("the top graph of the hierarchy\
#                             is not the same as the selected graph")
#     for child in hierarchy["children"]:
#         if child["name"] in self.subCmds.keys():
#             self.subCmds[child["name"]].merge_hierarchy(child)
#         else:
#             self.add_subHierarchy(child)
#     if "rules" in hierarchy.keys():
#         for r in hierarchy["rules"]:
#             if r["name"] not in self.subRules.keys():
#                 new_rule = Rule(r["name"],
#                                 TypedDiGraph(metamodel=top_graph),
#                                 self)
#                 new_rule.from_json_like(r)
#                 self.subRules[r["name"]] = new_rule


# def add_subHierarchy(self, subHierarchy, force=False):
#     g = TypedDiGraph(metamodel=self.graph)
#     g.from_json_like(subHierarchy["top_graph"])
#     if (subHierarchy["name"] in self.subCmds.keys() or
#         subHierarchy["name"] in self.subRules.keys()):
#         raise(KeyError("name already exists"))

#     # self._add_subgraph_no_catching(g,subHierarchy["name"])
#     cmd = self.__class__(subHierarchy["name"], self)
#     cmd.graph = g
#     for child in subHierarchy["children"]:
#         cmd.add_subHierarchy(child)
#     if "rules" in subHierarchy.keys():
#         for r in subHierarchy["rules"]:
#             if (r["name"] in cmd.subCmds.keys() or
#                 r["name"] in cmd.subRules.keys()):
#                 raise(KeyError("name " + r["name"] + " already exists"))
#             new_rule = Rule(r["name"],
#                             TypedDiGraph(metamodel=g), cmd)
#             new_rule.from_json_like(r)
#             cmd.subRules[r["name"]] = new_rule
#     self.subCmds[subHierarchy["name"]] = cmd



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
