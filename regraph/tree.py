"""Functions for manipulating a hierarchy as a tree"""

import copy
import itertools
import networkx as nx

from regraph.hierarchy import GraphNode, RuleNode, Hierarchy
import regraph.primitives as prim
from regraph.primitives import (graph_to_json,
                                add_node_attrs,
                                unique_node_id,
                                graph_from_json)
from regraph.rules import Rule
from regraph.category_op import (pushout, compose_homomorphisms,
                                 check_totality,
                                 typing_of_pushout,
                                 is_monic,
                                 check_homomorphism)


# def _complete_rewrite(hie, g_id, rule, match, lhs_typing=None,
#                       rhs_typing=None):
#     (lhs_t, rhs_t) = hie.get_complete_typing(g_id, match, lhs_typing,
#                                              rhs_typing, rule)
#     hie.rewrite(g_id, rule, match, lhs_t, rhs_t)

# def unique_node_id(self, prefix):
#     """ generate a new node id """
#     return self.graph.unique_node_id(prefix)

def _rewrite(hie, g_id, rule, mapping, lhs_typing=None, rhs_typing=None,
             total=None, inplace=True, ignore_attrs=False):
    if total is None:
        if g_id in graph_children(hie, "/"):
            return hie.rewrite(g_id, rule, mapping, lhs_typing, rhs_typing,
                               total=False, inplace=inplace,
                               ignore_attrs=ignore_attrs)
        else:
            return hie.rewrite(g_id, rule, mapping, lhs_typing, rhs_typing,
                               total=True, inplace=inplace,
                               ignore_attrs=ignore_attrs)
    else:
        return hie.rewrite(g_id, rule, mapping, lhs_typing, rhs_typing,
                           total=total, inplace=inplace,
                           ignore_attrs=ignore_attrs)


def fmap(hie, g_id, f):
    f(g_id)
    for child in all_children(hie, g_id):
        fmap(hie, child, f)


def _valid_name(hie, g_id, new_name):
    for parent in hie.out_edges(g_id):
        if not valid_child_name(hie, parent, new_name):
            return False
    return True


def get_valid_name(hie, g_id, prefix):
    if _valid_name(hie, g_id, prefix):
        return prefix
    i = 0
    while not _valid_name(hie, g_id, "{}_{}".format(prefix, i)):
        i += 1
    return "{}_{}".format(prefix, i)


def rule_children(hie, g_id):
    """Returns the rukes typed by g_id"""
    return (source for source, _ in hie.in_edges(g_id)
            if isinstance(hie.node[source], RuleNode))


def graph_children(hie, g_id):
    """Returns the graphs typed by g_id"""
    return (source for source, _ in hie.in_edges(g_id)
            if isinstance(hie.node[source], GraphNode))


def all_children(hie, g_id):
    """Returns all the nodes (even partially) typed by g_id"""
    return (source for source, _ in hie.in_edges(g_id))


def check_rule_typings(typings, rule):
    for (typing, rule_typing) in typings:
        check_homomorphism(
            rule.lhs,
            typing,
            rule_typing.lhs_mapping,
            rule_typing.ignore_attrs,
            rule_typing.lhs_total
        )
        check_homomorphism(
            rule.rhs,
            typing,
            rule_typing.rhs_mapping,
            rule_typing.ignore_attrs,
            rule_typing.rhs_total
        )


def from_json_tree(hie, json_data, parent_id):
    """convert json tree to hierarchy"""
    if "id" not in json_data.keys():
        json_data["id"] = hie.unique_graph_id(json_data["name"])
    if not json_data["id"] in hie.nodes():
        if json_data["top_graph"] is None and hie.directed:
            hie.add_graph(json_data["id"], nx.DiGraph(),
                          {"name": json_data["name"]})
        elif json_data["top_graph"] is None:
            hie.add_graph(json_data["id"], nx.Graph(),
                          {"name": json_data["name"]})
        else:
            hie.add_graph(json_data["id"],
                          graph_from_json(json_data["top_graph"]),
                          json_data["top_graph"]["attributes"])
            hie.node[json_data["id"]].attrs["name"] = json_data["name"]
    if parent_id is not None:
        if (json_data["id"], parent_id) not in hie.edges():
            typing = {n["id"]: n["type"]
                      for n in json_data["top_graph"]["nodes"]
                      if n["type"] != "" and n["type"] is not None and n["type"] != "notype"}
            hie.add_typing(json_data["id"], parent_id, typing,
                           ignore_attrs=True, total=False)
    for child in json_data["children"]:
        from_json_tree(hie, child, json_data["id"])
    return json_data["id"]


def to_json_tree(hie, g_id, parent, include_rules=True,
                 include_graphs=True, depth_bound=None):
    """export a hierarchy as a json tree with root g_id"""
    if not isinstance(hie.node[g_id], GraphNode):
        raise ValueError("node {} must be a graph".format(g_id))
    if depth_bound is not None and depth_bound <= 0:
        children = []
    elif depth_bound is not None:
        children = [to_json_tree(hie, c, g_id, include_rules, include_graphs,
                                 depth_bound - 1)
                    for c in graph_children(hie, g_id)]
    else:
        children = [to_json_tree(hie, c, g_id, include_rules,
                                 include_graphs, None)
                    for c in graph_children(hie, g_id)]
    json_data = {"id": g_id,
                 "name": hie.node[g_id].attrs["name"],
                 "children": children}

    if include_graphs:
        json_data["top_graph"] = typed_graph_to_json(hie, g_id, parent)
        # if json_data["top_graph"] is not None:
        #     json_data["top_graph"]["attributes"] = hie.node[g_id].attrs

        if include_rules:
            json_data["rules"] = [typed_rule_to_json(hie, r, g_id)
                                  for r in rule_children(hie, g_id)]
    elif include_rules:
        json_data["rules"] = [hie.node[r].attrs["name"]
                              for r in rule_children(hie, g_id)]

    return json_data


def _type_json_nodes(nodes, typing):
    for node in nodes:
        if node["id"] in typing.keys():
            node["type"] = typing[node["id"]]
        else:
            node["type"] = ""


def typed_graph_to_json(hie, g_id, parent):
    if hie.node[g_id].graph is None:
        return None
    json_data = graph_to_json(hie.node[g_id].graph)
    json_data["attributes"] = hie.node[g_id].attrs
    if parent is not None:
        typing = hie.edge[g_id][parent].mapping
        _type_json_nodes(json_data["nodes"], typing)
    return json_data


def typed_rule_to_json(hie, g_id, parent):
    rule = hie.node[g_id].rule
    json_data = {}
    json_data["name"] = hie.node[g_id].attrs["name"]
    json_data["L"] = graph_to_json(rule.lhs)
    json_data["P"] = graph_to_json(rule.p)
    json_data["R"] = graph_to_json(rule.rhs)
    # json_data["PR"] = [{"left": k, "right": v}
    #                    for (k, v) in rule.p_rhs.items()]
    # json_data["PL"] = [{"left": k, "right": v}
    #                    for (k, v) in rule.p_lhs.items()]
    json_data["PR"] = rule.p_rhs
    json_data["PL"] = rule.p_lhs
    if parent is not None:
        lhs_mapping = hie.edge[g_id][parent].lhs_mapping
        rhs_mapping = hie.edge[g_id][parent].rhs_mapping
    _type_json_nodes(json_data["R"]["nodes"], rhs_mapping)
    p_mapping = compose_homomorphisms(rhs_mapping, rule.p_rhs)
    _type_json_nodes(json_data["P"]["nodes"], p_mapping)
    lhs_mapping.update({rule.p_lhs[n]: p_mapping[n]
                        for n in rule.p
                        if rule.p_lhs[n] not in lhs_mapping.keys() and
                        n in p_mapping.keys()})
    _type_json_nodes(json_data["L"]["nodes"], lhs_mapping)
    return json_data


def valid_child_name(hie, g_id, new_name):
    """ check if node g_id already has a child named new_name"""
    children_name = [hie.node[source].attrs["name"]
                     for source in all_children(hie, g_id)]
    return new_name not in children_name


def rename_child(hie, g_id, parent, new_name):
    """rename a graph """
    if valid_child_name(hie, parent, new_name):
        hie.node[g_id].attrs["name"] = new_name
    else:
        raise ValueError("name {} is not valid".format(new_name))


def child_from_name(hie, g_id, name):
    """return the id of the child of g_id named name"""
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
        child = child_from_name(hie, g_id, path[0])
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
        ch_id = hie.unique_graph_id(name)
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
            pattern_id = child_from_name(hie, parent, pattern_name)
            pattern = hie.node[pattern_id].graph
        rule_id = hie.unique_graph_id(name)
        rule = Rule(pattern, pattern, pattern)
        hie.add_rule(rule_id, rule, {"name": name})
        if parent is not None:
            if pattern_name is None:
                hie.add_rule_typing(rule_id, parent, {}, {})
            else:
                mapping = hie.edge[pattern_id][parent].mapping
                ignore = hie.edge[pattern_id][parent].ignore_attrs
                hie.add_rule_typing(rule_id, parent, mapping, mapping,
                                    ignore_attrs=ignore)
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
        _rewrite(hie,g_id, rule, {}, lhs_typing, rhs_typing)
    elif isinstance(hie.node[g_id], RuleNode):
        tmp_rule = copy.deepcopy(hie.node[g_id].rule)
        tmp_rule.add_node(node_id)
        typings = [(hie.node[typing].graph, hie.edge[g_id][typing])
                   for _, typing in hie.out_edges(g_id)
                   if typing != parent]
        # tmp_parent_typing = copy.deepcopy(hie.edge[g_id][parent])
        # tmp_parent_typing.rhs_mapping[node_id] = node_type
        if parent is not None and node_type is not None:
            parent_typing = copy.deepcopy(hie.edge[g_id][parent])
            if node_type is not None:
                parent_typing.rhs_mapping[node_id] = node_type
            typings.append((hie.node[parent].graph, parent_typing))
        check_rule_typings(typings, tmp_rule)
        hie.node[g_id].rule = tmp_rule
        if parent is not None:
            hie.edge[g_id][parent] = parent_typing
    else:
        raise ValueError("node is neither a rule nor a graph")


def add_edge(hie, g_id, parent, node1, node2):
    """add an edge to a node of the hierarchy"""
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
        _rewrite(hie,g_id, rule, {node1: node1, node2: node2})
    elif isinstance(hie.node[g_id], RuleNode):
        tmp_rule = copy.deepcopy(hie.node[g_id].rule)
        tmp_rule.add_edge_rhs(node1, node2)
        typings = [(hie.node[typing].graph, hie.edge[g_id][typing])
                   for _, typing in hie.out_edges(g_id)]
        check_rule_typings(typings, tmp_rule)
        hie.node[g_id].rule = tmp_rule
    else:
        raise ValueError("node is neither a rule nor a graph")


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
        _rewrite(hie,g_id, rule, {node_id: node_id})
    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.remove_node_rhs(node_id)
        for _, typing in hie.out_edges(g_id):
            if node_id in hie.edge[g_id][typing].rhs_mapping.keys():
                del hie.edge[g_id][typing].rhs_mapping[node_id]
    else:
        raise ValueError("node is neither a rule nor a graph")


# TODO: merge if different types and remove types (strong rules for now)
def merge_nodes(hie, g_id, parent, node1, node2, new_name):
    """merge node1 and node2 in graph or rule"""
    if isinstance(hie.node[g_id], GraphNode):
        if new_name in hie.node[g_id].graph.nodes():
            raise ValueError("node {} already exists".format(new_name))
        lhs = nx.DiGraph()
        lhs.add_node(node1)
        lhs.add_node(node2)
        ppp = nx.DiGraph()
        ppp.add_node(node1)
        ppp.add_node(node2)
        rhs = nx.DiGraph()
        rhs.add_node(new_name)
        rule = Rule(ppp, lhs, rhs, None, {node1: new_name, node2: new_name})
        _rewrite(hie,g_id, rule, {node1: node1, node2: node2})
    elif isinstance(hie.node[g_id], RuleNode):
        tmp_rule = copy.deepcopy(hie.node[g_id].rule)
        tmp_rule.merge_nodes_rhs(node1, node2, new_name)
        typings = {typing: copy.deepcopy(hie.edge[g_id][typing])
                   for _, typing in hie.out_edges(g_id)}
        for typing_rule in typings.values():
            mapping = typing_rule.rhs_mapping
            if node1 in mapping.keys():
                if node2 in mapping.keys():
                    if mapping[node1] == mapping[node2]:
                        mapping[new_name] = mapping[node1]
                        del mapping[node1]
                        del mapping[node2]
                    else:
                        raise ValueError("merge nodes of different types")
                else:
                    raise ValueError("merge nodes of different types")
            else:
                if node2 in mapping.keys():
                    raise ValueError("merge nodes of different types")
        for _, typing in hie.out_edges(g_id):
            hie.edge[g_id][typing] = typings[typing]
        hie.node[g_id].rule = tmp_rule
    else:
        raise ValueError("node is neither a rule nor a graph")


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
        _rewrite(hie,g_id, rule, {node: node})
    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.clone_rhs_node(node, new_name)
        for _, typing in hie.out_edges(g_id):
            mapping = hie.edge[g_id][typing].rhs_mapping
            if node in mapping.keys():
                mapping[new_name] = mapping[node]

    else:
        raise ValueError("node is neither a rule nor a graph")


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
        _rewrite(hie,g_id, rule, {node1: node1, node2: node2})

    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.remove_edge_rhs(node1, node2)
    else:
        raise ValueError("node is neither a rule nor a graph")


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
        _rewrite(hie, g_id, rule, {node: node})
    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.add_node_attrs_rhs(node, attrs)
    else:
        raise ValueError("node is neither a rule nor a graph")


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
        _rewrite(hie,g_id, rule, {node: node})
    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.remove_node_attrs_rhs(node, attrs)
    else:
        raise ValueError("node is neither a rule nor a graph")


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

def get_children_by_node(hie, g_id, node_id):
    """Return the children containing a node typed by node_id"""
    return [hie.node[child].attrs["name"]
            for child in graph_children(hie, g_id)
            if node_id in hie.edge[child][g_id].mapping.values()]


# only works on a tree
def ancestor(hie, g_id, degree):
    """get the id of ancestor of degree"""
    if degree == 0:
        return g_id
    else:
        parents = [target for _, target in hie.out_edges(g_id)]
        if len(parents) != 1:
            raise ValueError("ancestor can only be used on a tree")
        return ancestor(hie, parents[0], degree-1)


def _mapping_to_json(mapping):
    return [{"left": n, "right": t} for (n, t) in mapping.items()]


# only works on a tree
def ancestors_mapping(hie, g_id, degree):
    """get the typing of g_id according to degree"""
    if degree <= 0:
        raise ValueError("degree should be > 0")
    mapping = hie.get_typing(g_id, ancestor(hie, g_id, degree))
    return _mapping_to_json(mapping)


def ancestors_graph_mapping(hie, top, g_id, ancestor_path):
    """get the typing of graph g_id by ancestor"""
    path_list = [s for s in ancestor_path.split("/") if s and not s.isspace()]
    ancestor_id = child_from_path(hie, top, path_list)
    mapping = hie.get_typing(g_id, ancestor_id)
    return {"typing": _mapping_to_json(mapping)}


def ancestors_rule_mapping(hie, top, g_id, ancestor_path):
    """get the typing of rule g_id by ancestor"""
    path_list = [s for s in ancestor_path.split("/") if s and not s.isspace()]
    ancestor_id = child_from_path(hie, top, path_list)
    rule_mappings = hie.get_rule_typing(g_id, ancestor_id)
    (lhs_t, p_t, rhs_t) = tuple(map(_mapping_to_json, rule_mappings))
    return {"lhs_typing": lhs_t,
            "p_typing": p_t,
            "rhs_typing": rhs_t}


def new_graph_from_nodes(hie, nodes, g_id, new_name):
    """create a child graph from a set of nodes"""
    if valid_child_name(hie, g_id, new_name):
        ch_id = hie.unique_graph_id(new_name)
        hie.new_graph_from_nodes(nodes, g_id, ch_id, {"name": new_name})
    else:
        raise ValueError("Invalid new name")

 
def child_rule_from_nodes(hie, nodes, g_id, new_name):
    """create a rule typed by g_id"""
    if valid_child_name(hie, g_id, new_name):
        ch_id = hie.unique_graph_id(new_name)
        hie.child_rule_from_nodes(nodes, g_id, ch_id, {"name": new_name})
    else:
        raise ValueError("Invalid new name")


def rewrite_parent(hie, g_id, parent, suffix):
    """rewrite the parent of rule g_id, using typing as a matching"""
    if not isinstance(hie.node[g_id], RuleNode):
        raise ValueError("{} is not a rule".format(g_id))
    rule = hie.node[g_id].rule
    mapping = hie.edge[g_id][parent]
    if not mapping.lhs_total:
        check_totality(rule.lhs, mapping.lhs_mapping)
    if not is_monic(mapping.lhs_mapping):
        raise ValueError("matching must be monic")
    new_names = hie.duplicate_subgraph(hie.descendents(parent), suffix)
    for new_id in new_names.values():
        old_name = hie.node[new_id].attrs["name"]
        hie.node[new_id].attrs["name"] = \
            get_valid_name(hie, new_id, old_name+"_"+suffix)
    ignore_attrs = True
    (_, updated_graphs) = _rewrite(hie, new_names[parent], rule,
                                   mapping.lhs_mapping,
                                   ignore_attrs=ignore_attrs)
    print("updated_graph:tree 682")
    for (old_id, new_id) in new_names.items():
        if old_id != parent and isinstance(hie.node[old_id], GraphNode):
            valid_nuggets = hie.create_valid_nuggets(old_id, new_id,
                                                     updated_graphs)
            for nug_id in valid_nuggets:
                nug_name = get_valid_name(hie, nug_id,
                                          hie.node[new_id].attrs["name"])
                hie.node[nug_id].attrs["name"] = nug_name
            hie.remove_graph(new_id)


def unfold_nuggets(hie, ag_id, metamodel_id, nug_list=None):
    """creates nuggets with exactly one value per node
    ag_id: id of the action graph
    warning: do not modify returned typings as they point to the old typings
    """
    if nug_list is None:
        nug_list = graph_children(hie, ag_id)
    new_nug_list = []
    for nug_id in nug_list:
        meta_typing = hie.get_typing(nug_id, metamodel_id)
        nug = hie.node[nug_id].graph
        states = {n: nug.node[n]["value"] for n in nug.nodes()
                  if (meta_typing[n] == "state" and
                      "value" in nug.node[n].keys())}
        for values in itertools.product(states.values()):
            new_nug = copy.deepcopy(hie.node[nug_id])
            for (i, node) in enumerate(states.keys()):
                new_nug.graph.node[node]["value"] = values[i]
            new_nug_list.append((new_nug, hie.edge[nug_id][ag_id]))
    return new_nug_list


# for total typings
# TODO: test if name is valid
# TODO: typing types
def merge_graphs(hie, g_id, name1, name2, mapping, new_name):
    """ merge two graph based  on an identity relation
        between their nodes.
        We first build a span from the given relation.
        The new graph is then computed as the pushout. """
    new_name = get_valid_name(hie, g_id, new_name)
    id1 = child_from_name(hie, g_id, name1)
    id2 = child_from_name(hie, g_id, name2)
    g1 = hie.node[id1].graph
    g2 = hie.node[id2].graph
    g1_typ = hie.get_typing(id1, g_id)
    g2_typ = hie.get_typing(id2, g_id)
    if hie.directed:
        g0 = nx.DiGraph()
    else:
        g0 = nx.Graph()
    left_mapping = {}
    right_mapping = {}
    for (n1, n2) in mapping:
        new_node = unique_node_id(g0, n2)
        prim.add_node(g0, new_node)
        left_mapping[new_node] = n1
        right_mapping[new_node] = n2
    (new_graph, g1_new_graph, g2_new_graph) = \
        pushout(g0, g1, g2, left_mapping, right_mapping)
    new_id = hie.unique_graph_id(new_name)
    hie.add_graph(new_id, new_graph, {"name": new_name})
    hie.add_typing(new_id, g_id, typing_of_pushout(g1, g2, new_graph,
                                                   g1_new_graph,
                                                   g2_new_graph,
                                                   g1_typ, g2_typ))

    for nug in graph_children(hie, id1):
        new_nug_id = hie.unique_graph_id(nug)
        nug_typing = hie.edge[nug][id1].mapping
        # use name instead  of id
        new_nug_name = get_valid_name(hie, new_id, nug)
        hie.add_graph(new_nug_id, copy.deepcopy(hie.node[nug].graph),
                      {"name": new_nug_name})
        hie.add_typing(new_nug_id, new_id,
                       compose_homomorphisms(g1_new_graph, nug_typing))

    for nug in graph_children(hie, id2):
        new_nug_id = hie.unique_graph_id(nug)
        nug_typing = hie.edge[nug][id2].mapping
        # use name instead  of id
        new_nug_name = get_valid_name(hie, new_id, nug)
        hie.add_graph(new_nug_id, copy.deepcopy(hie.node[nug].graph),
                      {"name": new_nug_name})
        hie.add_typing(new_nug_id, new_id,
                       compose_homomorphisms(g2_new_graph, nug_typing))


def _put_path_in_attr(hie, top, tmp_key):
    def _put_path_aux(g_id, path):
        new_path = path + [hie.node[g_id]["name"]]
        hie.node[g_id].add_attrs({tmp_key: new_path})
        for child in all_children(hie, g_id):
            _put_path_aux(child, new_path)

    _put_path_aux(top, [])


def _remove_path_from_attr(hie, top, tmp_key):
    def _remove_path(g_id):
        del hie.node[g_id].attrs[tmp_key]
    fmap(hie, top, _remove_path)


def merge_json_into_hierarchy(hie, json_data, top):
    """incorporate json hierarchy into existing one"""
    tmp_key = "tmp_path_for_merge"
    new_hie = Hierarchy(hie.directed, graph_node_constuctor=GraphNode)
    new_top = from_json_tree(new_hie, json_data, None)
    _put_path_in_attr(new_hie, new_top, tmp_key)
    _put_path_in_attr(hie, top, tmp_key)
    hie.merge_by_attr(new_hie, tmp_key)
    _remove_path_from_attr(hie, top, tmp_key)


def new_action_graph(hie, nug_typings):
    """replace partial ag by total ag"""

    nugs = nug_typings.keys()
    ag = hie.node["action_graph"].graph
    ag_kami = {}
    for nug in nugs:
        nug_kami = hie.edge[nug]["kami"].mapping
        nug_ag = nug_typings[nug]
        for nug_node, ag_node in nug_ag.items():
            ag_kami[ag_node] = nug_kami[nug_node]

    for nug in nugs:
        graph = hie.node[nug].graph
        nug_kami = hie.edge[nug]["kami"].mapping
        nug_ag = nug_typings[nug]
        bot = nx.DiGraph()
        bot.add_nodes_from(nug_ag.keys())
        bot_nug = {node: node for node in bot.nodes()}
        bot_ag = {node: nug_ag[node] for node in bot.nodes()}
        (new_ag, ag_newag, nug_newag) = pushout(bot, ag, graph, bot_ag,
                                                bot_nug)
        for other_nug in nug_typings:
            if other_nug != nug:
                nug_typings[other_nug] =\
                    compose_homomorphisms(ag_newag, nug_typings[other_nug])
        nug_typings[nug] = nug_newag
        newag_kami = {}
        for node in ag:
            newag_kami[ag_newag[node]] = ag_kami[node]
        for node in graph:
            newag_kami[nug_newag[node]] = nug_kami[node]
        hie.remove_edge(nug, "kami")
        ag = new_ag
        ag_kami = newag_kami

    hie.remove_graph("action_graph")
    hie.add_graph("action_graph", ag, {"name": "action_graph"})
    hie.add_typing("action_graph", "kami", ag_kami, total=True,
                   ignore_attrs=True)
    for nug in nug_typings:
        hie.add_typing(nug, "action_graph", nug_typings[nug], total=True)

