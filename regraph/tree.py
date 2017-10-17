"""Functions for manipulating a hierarchy as a tree"""

import copy
import itertools
import networkx as nx

from regraph.hierarchy import GraphNode, RuleNode, Hierarchy, Typing
import regraph.primitives as prim
from regraph.primitives import (graph_to_json,
                                add_node_attrs,
                                update_node_attrs,
                                graph_from_json,
                                unique_node_id)
from regraph.rules import Rule
from regraph.atset import univ_set
from regraph.category_op import (pushout, compose_homomorphisms,
                                 check_totality,
                                 typing_of_pushout,
                                 typings_of_pushout,
                                 is_monic,
                                 check_homomorphism)
from regraph.attribute_sets import UniversalSet, FiniteSet
from regraph.utils import is_subdict, recursive_merge, valid_attributes

# def _complete_rewrite(hie, g_id, rule, match, lhs_typing=None,
#                       rhs_typing=None):
#     (lhs_t, rhs_t) = hie.get_complete_typing(g_id, match, lhs_typing,
#                                              rhs_typing, rule)
#     hie.rewrite(g_id, rule, match, lhs_t, rhs_t)

# def unique_node_id(self, prefix):
#     """ generate a new node id """
#     return self.graph.unique_node_id(prefix)


def _rewrite(hie, g_id, rule, mapping, lhs_typing=None, rhs_typing=None,
             total=None, inplace=True):
    if total is None:
        if g_id in graph_children(hie, "/"):
            return hie.rewrite(g_id, rule, mapping, lhs_typing, rhs_typing,
                               total=False, inplace=inplace)
        else:
            return hie.rewrite(g_id, rule, mapping, lhs_typing, rhs_typing,
                               total=True, inplace=inplace)
    else:
        return hie.rewrite(g_id, rule, mapping, lhs_typing, rhs_typing,
                           total=total, inplace=inplace)


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


# must be fully typed
def add_graph(hie, graph, g_id, parent, typing):
    """add a graph as a child of parent"""
    new_id = hie.unique_graph_id(g_id)
    new_name = get_valid_child_name(hie, parent, new_id)
    hie.add_graph(new_id, graph, {"name": new_name})
    hie.add_typing(new_id, parent, typing, total=True)


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
            rule_typing.lhs_total
        )
        check_homomorphism(
            rule.rhs,
            typing,
            rule_typing.rhs_mapping,
            rule_typing.rhs_total
        )


def _ignore_attrs(hie, id):
    graph = hie.node[id].graph
    for node in graph.nodes():
        graph.node[node] = None


def _add_empty_attrs(hie, id):
    graph = hie.node[id].graph
    for node in graph.nodes():
        if graph.node[node] is None:
            graph.node[node] = {}


def _propagate_values(hie, id, parent, mapping):
    anc = hie.get_ancestors(parent)
    graph = hie.node[id].graph
    parent_gr = hie.node[parent].graph
    for (anc_id, anc_typ) in anc.items():
        anc_gr = hie.node[anc_id].graph
        for node in mapping:
            if mapping[node] in anc_typ:
                prim.add_node_attrs(anc_gr, anc_typ[mapping[node]],
                                    graph.node[node])
    for node in mapping:
        prim.add_node_attrs(parent_gr, mapping[node],
                            graph.node[node])


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
    # if json_data["id"] in ["kami_base", "kami"]:
    #     _ignore_attrs(hie, json_data["id"])
    # else:
    #     _add_empty_attrs(hie, json_data["id"])

    if parent_id is not None:
        if (json_data["id"], parent_id) not in hie.edges():
            typing = {n["id"]: n["type"]
                      for n in json_data["top_graph"]["nodes"]
                      if n["type"] != "" and
                      n["type"] is not None and n["type"] != "notype"}
            _propagate_values(hie, json_data["id"], parent_id, typing)
            hie.add_typing(json_data["id"], parent_id, typing, total=False)
    for child in json_data["children"]:
        from_json_tree(hie, child, json_data["id"])
    return json_data["id"]


# temporary (types should be in a well formated JSON)
def add_types(hie, top):
    kami_id = child_from_path(hie, top, ["kami_base", "kami"])
    for node in hie.nodes():
        if kami_id in hie[node] and isinstance(hie.node[node], GraphNode):
            hie.node[node].attrs["children_types"] = ["nugget", "rule",
                                                      "variant"]
            for child in all_children(hie, node):
                if "type" not in hie.node[child].attrs:
                    if isinstance(hie.node[child], GraphNode):
                        hie.node[child].attrs["type"] = "nugget"
                    elif isinstance(hie.node[child], RuleNode):
                        hie.node[child].attrs["type"] = "rule"


# temporary (correct attributes should be in a well formated JSON)
def tmp_add_attributes(hie, top):
    kami_base_id = child_from_path(hie, top, ["kami_base"])
    kami_id = child_from_path(hie, top, ["kami_base", "kami"])
    kami_base_gr = hie.node[kami_base_id].graph
    kami_gr = hie.node[kami_id].graph
    for gr in [kami_base_gr, kami_gr]:
        for node in gr:
            attrs = gr.node[node]
            attrs["val"] = UniversalSet()


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
                 "name": hie.node[g_id].attrs["name"].to_json(),
                 "children": children}

    if include_graphs:
        json_data["top_graph"] = typed_graph_to_json(hie, g_id, parent)
        # if json_data["top_graph"] is not None:
        #     json_data["top_graph"]["attributes"] = hie.node[g_id].attrs

        if include_rules:
            json_data["rules"] = [typed_rule_to_json(hie, r, g_id)
                                  for r in rule_children(hie, g_id)]
    elif include_rules:
        json_data["rules"] = [hie.node[r].attrs["name"].to_json()
                              for r in rule_children(hie, g_id)]

    return json_data


def _type_json_nodes(nodes, typing):
    for node in nodes:
        if node["id"] in typing.keys():
            node["type"] = typing[node["id"]]
        else:
            node["type"] = ""


def _extract_from_sets(attrs):
    def _from_set(key, value):
        if key == "children_types":
            return list(value)
        else:
            return min(value)
    return {key: _from_set(key, value) for (key, value) in attrs.items()}


def typed_graph_to_json(hie, g_id, parent):
    if hie.node[g_id].graph is None:
        return None
    json_data = graph_to_json(hie.node[g_id].graph)
    generated_list = []
    for k, v in hie.node[g_id].attrs.items():
        try:
            generated_list.append((k, v.to_json()))
        except:
            generated_list.append((k, v))
    json_data["attributes"] = (generated_list)
    if parent is not None:
        typing = hie.edge[g_id][parent].mapping
        _type_json_nodes(json_data["nodes"], typing)
    return json_data


def typed_rule_to_json(hie, g_id, parent):
    rule = hie.node[g_id].rule
    json_data = {}
    json_data["name"] = hie.node[g_id].attrs["name"].to_json()
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


def get_valid_child_name(hie, g_id, new_name):
    """ builds a valid name from new name for a new child of g_id"""
    if valid_child_name(hie, g_id, new_name):
        return new_name
    i = 0
    while not valid_child_name(hie, g_id, "{}_{}".format(new_name, i)):
        i += 1
    return "{}_{}".format(new_name, i)


def rename_child(hie, g_id, parent, new_name):
    """rename a graph """
    if valid_child_name(hie, parent, new_name):
        hie.node[g_id].attrs["name"] = FiniteSet([new_name])
    else:
        raise ValueError("name {} is not valid".format(new_name))


def child_from_name(hie, g_id, name):
    """return the id of the child of g_id named name"""
    print(name, type(name))
    for c in all_children(hie, g_id):
        print(hie.node[c].attrs["name"], type(hie.node[c].attrs["name"]))
    children = [c for c in all_children(hie, g_id)
                if name in hie.node[c].attrs["name"]]
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
                hie.add_rule_typing(rule_id, parent, mapping, mapping)
    else:
        raise ValueError("Invalid new name")


# TODO : undirected ?
def add_node(hie, g_id, parent, node_id, node_type, new_name=False):
    """add a node to a graph in the hierarchy"""
    # if parent is not None and node_type is None:
    #     raise ValueError("node {} must have a type".format(node_id))
    if isinstance(hie.node[g_id], GraphNode):
        if node_id in hie.node[g_id].graph.nodes():
            if new_name:
                node_id = prim.unique_node_id(hie.node[g_id].graph, node_id)
            else:
                raise ValueError(
                    "node {} already exists in graph".format(node_id))

        # check that we have sufficient typings
        for typing in hie.successors(g_id):
            if hie.edge[g_id][typing].total:
                if typing != parent or (typing == parent and node_type is None):
                    raise ValueError("new node must be typed by {}"
                                     .format(typing))
        prim.add_node(hie.node[g_id].graph, node_id)
        if parent is not None and node_type is not None:
            hie.edge[g_id][parent].mapping[node_id] = node_type
        return node_id
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
        return node_id
    else:
        raise ValueError("node is neither a rule nor a graph")


def _valid_edge(hie, g_id, node1, node2):
    """ Raise an exeption is the edge is not allowed """
    for typing in hie.successors(g_id):
        mapping = hie.edge[g_id][typing].mapping
        if node1 in mapping and node2 in mapping:
            if not hie.node[typing].graph.has_edge(mapping[node1],
                                                   mapping[node2]):
                raise ValueError("no edge betweeen {} and {} in {}"
                                 .format(mapping[node1],
                                         mapping[node2],
                                         typing))


def add_edge(hie, g_id, parent, node1, node2):
    """add an edge to a node of the hierarchy"""
    if isinstance(hie.node[g_id], GraphNode):
        _valid_edge(hie, g_id, node1, node2)
        prim.add_edge(hie.node[g_id].graph, node1, node2)
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
        _rewrite(hie, g_id, rule, {node_id: node_id})
    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.remove_node_rhs(node_id)
        for _, typing in hie.out_edges(g_id):
            if node_id in hie.edge[g_id][typing].rhs_mapping.keys():
                del hie.edge[g_id][typing].rhs_mapping[node_id]
    else:
        raise ValueError("node is neither a rule nor a graph")


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
        _rewrite(hie, g_id, rule, {node1: node1, node2: node2})
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


def clone_node(hie, g_id, parent, node, new_name, propagate=False):
    """Create a clone of a node. If propagate is True, also clone all the nodes typed by it"""
    if isinstance(hie.node[g_id], GraphNode):
        if new_name in hie.node[g_id].graph.nodes():
            raise ValueError("node {} already in graph".format(new_name))
        if propagate:
            lhs = nx.DiGraph()
            lhs.add_node(node)
            ppp = nx.DiGraph()
            ppp.add_node(node)
            ppp.add_node(new_name)
            rhs = nx.DiGraph()
            rhs.add_node(node)
            rhs.add_node(new_name)
            rule = Rule(ppp, lhs, rhs, {node: node, new_name: node}, None)
            _rewrite(hie, g_id, rule, {node: node})
        else:
            prim.clone_node(hie.node[g_id].graph, node, new_name)
            for _, typing in hie.out_edges(g_id):
                mapping = hie.edge[g_id][typing].mapping
                if node in mapping.keys():
                    mapping[new_name] = mapping[node]

    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.clone_rhs_node(node, new_name)
        for _, typing in hie.out_edges(g_id):
            mapping = hie.edge[g_id][typing].rhs_mapping
            if node in mapping:
                mapping[new_name] = mapping[node]
    else:
        raise ValueError("node is neither a rule nor a graph")


def rm_edge(hie, g_id, parent, node1, node2):
    """remove an edge from a graph, and all the edges typed by it"""
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
        _rewrite(hie, g_id, rule, {node1: node1, node2: node2})

    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.remove_edge_rhs(node1, node2)
    else:
        raise ValueError("node is neither a rule nor a graph")


def add_attributes(hie, g_id, parent, node, json_attrs):
    """add the attributes from the json_attrs dict to a node"""
    attrs = prim.json_dict_to_attrs(json_attrs)
    if isinstance(hie.node[g_id], GraphNode):
        for typing in hie.successors(g_id):
            mapping = hie.edge[g_id][typing].mapping
            if node in mapping:
                parent_attrs = hie.node[typing].graph.node[mapping[node]]
                if not valid_attributes(attrs, parent_attrs):
                    raise ValueError("Attributes not in node {} of {}"
                                     .format(mapping[node], typing))
        prim.add_node_attrs(hie.node[g_id].graph, node, attrs)

    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.add_node_attrs_rhs(node, attrs)
    else:
        raise ValueError("node is neither a rule nor a graph")


def remove_attributes(hie, g_id, parent, node, json_attrs):
    """remove the attributes from json_attrs from the node"""
    attrs = prim.json_dict_to_attrs(json_attrs)
    if isinstance(hie.node[g_id], GraphNode):
        lhs = nx.DiGraph()
        lhs.add_node(node)
        add_node_attrs(lhs, node, attrs)
        ppp = nx.DiGraph()
        ppp.add_node(node)
        rhs = nx.DiGraph()
        rhs.add_node(node)
        rule = Rule(ppp, lhs, rhs)
        _rewrite(hie, g_id, rule, {node: node})
    elif isinstance(hie.node[g_id], RuleNode):
        hie.node[g_id].rule.remove_node_attrs_rhs(node, attrs)
    else:
        raise ValueError("node is neither a rule nor a graph")


def get_children_by_node(hie, g_id, node_id):
    """Return the children containing a node typed by node_id"""
    return [hie.node[child].attrs["name"]
            for child in graph_children(hie, g_id)
            if node_id in hie.edge[child][g_id].mapping.values()]


def get_children_id_by_node(hie, g_id, node_id):
    """Return the children containing a node typed by node_id"""
    return [child for child in graph_children(hie, g_id)
            if node_id in hie.edge[child][g_id].mapping.values()]


# only works if the hierarchy is a tree
def ancestor(hie, g_id, degree):
    """get the id of ancestor of degree"""
    if degree == 0:
        return g_id
    else:
        parents = [target for _, target in hie.out_edges(g_id)]
        if len(parents) != 1:
            raise ValueError("ancestor can only be used on a tree")
        return ancestor(hie, parents[0], degree - 1)


def _mapping_to_json(mapping):
    return [{"left": n, "right": t} for (n, t) in mapping.items()]


# only works if the hierarchy is a tree
# use ancestors_graph_mapping instead
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
    """create a child graph of g_id induced by a set of its nodes"""
    if valid_child_name(hie, g_id, new_name):
        ch_id = hie.unique_graph_id(new_name)
        hie.new_graph_from_nodes(nodes, g_id, ch_id, {"name": new_name})
    else:
        raise ValueError("Invalid new name")


def child_rule_from_nodes(hie, nodes, g_id, new_name):
    """create a rule typed by g_id (the identity rule where the
     pattern is induced by the selected nodes)"""
    if valid_child_name(hie, g_id, new_name):
        ch_id = hie.unique_graph_id(new_name)
        hie.child_rule_from_nodes(nodes, g_id, ch_id, {"name": new_name})
    else:
        raise ValueError("Invalid new name")


def rewrite_parent(hie, g_id, parent, suffix):
    """rewrite the parent of rule g_id,
    using the typing of the left hand side as the matching.
    The right hand side must be the same as the preserved part
    (no adding or merging of nodes)"""
    if not isinstance(hie.node[g_id], RuleNode):
        raise ValueError("{} is not a rule".format(g_id))
    rule = hie.node[g_id].rule
    mapping = hie.edge[g_id][parent]
    if not mapping.lhs_total:
        check_totality(rule.lhs, mapping.lhs_mapping)
    if not is_monic(mapping.lhs_mapping):
        raise ValueError("matching must be monic")
    new_names = hie.duplicate_subgraph(hie.descendents(parent), suffix)
    old_name = hie.node[new_names[parent]].attrs["name"]
    hie.node[new_names[parent]].attrs["name"] =\
        get_valid_name(hie, new_names[parent], old_name + "_" + suffix)
    (_, updated_graphs) = _rewrite(hie, new_names[parent], rule,
                                   mapping.lhs_mapping)
    for (old_id, new_id) in new_names.items():
        if old_id != parent and isinstance(hie.node[old_id], GraphNode):
            valid_nuggets = hie.create_valid_nuggets(old_id, new_id,
                                                     updated_graphs)
            base_name = hie.node[new_id].attrs["name"]
            hie.remove_graph(new_id)
            for nug_id in valid_nuggets:
                hie.node[nug_id].attrs["name"] = None
            for nug_id in valid_nuggets:
                nug_name = get_valid_name(hie, nug_id, base_name)
                hie.node[nug_id].attrs["name"] = nug_name
    return new_names


# def unfold_nuggets(hie, ag_id, metamodel_id, nug_list=None):
#     """creates nuggets with exactly one value per node
#     ag_id: id of the action graph
#     warning: do not modify returned typings as they point to the old typings
#     """
#     if nug_list is None:
#         nug_list = graph_children(hie, ag_id)
#     new_nug_list = []
#     for nug_id in nug_list:
#         meta_typing = hie.get_typing(nug_id, metamodel_id)
#         nug = hie.node[nug_id].graph
#         states = {n: nug.node[n]["value"] for n in nug.nodes()
#                   if (meta_typing[n] == "state" and
#                       "value" in nug.node[n].keys())}
#         for values in itertools.product(states.values()):
#             new_nug = copy.deepcopy(hie.node[nug_id])
#             for (i, node) in enumerate(states.keys()):
#                 new_nug.graph.node[node]["value"] = values[i]
#             new_nug_list.append((new_nug, hie.edge[nug_id][ag_id]))
#     return new_nug_list


def _copy_graph(hie, g_id):
    """ Create a copy of a graph and returns the new id"""
    new_node = copy.deepcopy(hie.node[g_id])
    new_id = hie.unique_graph_id(g_id)
    hie.add_graph(new_id, new_node.graph, new_node.attrs)
    return new_id


# create a new dict of graph attributes by merging the attributes of id1
# and id2
def _new_merged_graph_attrs(hie, id1, id2, new_name):
    new_attrs = copy.deepcopy(hie.node[id1].attrs)
    attrs2 = hie.node[id2].attrs
    recursive_merge(new_attrs, attrs2)
    new_attrs["name"] = new_name
    return new_attrs


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

    # build the span from the relation
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

    # compute the pushout
    (new_graph, g1_new_graph, g2_new_graph) = \
        pushout(g0, g1, g2, left_mapping, right_mapping)
    new_id = hie.unique_graph_id(new_name)
    new_attrs = _new_merged_graph_attrs(hie, id1, id2, new_name)
    hie.add_graph(new_id, new_graph, new_attrs)

    # recover the typings of the new pushout graph
    g1_typings = {t: hie.edge[id1][t] for t in hie.successors(id1)}
    g2_typings = {t: hie.edge[id2][t] for t in hie.successors(id2)}
    new_typings = typings_of_pushout(g1, g2, new_graph, g1_new_graph,
                                     g2_new_graph, g1_typings, g2_typings)

    for (typ_id, (typ_mapping, typ_total)) in new_typings.items():
        hie.add_typing(new_id, typ_id, typ_mapping, total=typ_total)

    # recover the typings of children by the new pushout graph
    new_id1 = _copy_graph(hie, new_id)
    for child in all_children(hie, id1):
        hie.add_edge(child, new_id1)
        tmp_typ = Typing(g1_new_graph, total=hie.edge[child][id1].all_total())
        hie.edge[child][new_id1] = tmp_typ * hie.edge[child][id1]

    new_id2 = _copy_graph(hie, new_id)
    for child in all_children(hie, id2):
        hie.add_edge(child, new_id2)
        tmp_typ = Typing(g2_new_graph, total=hie.edge[child][id2].all_total())
        hie.edge[child][new_id2] = tmp_typ * hie.edge[child][id2]

    _merge_hierarchy(hie, hie, new_id, new_id1)
    _merge_hierarchy(hie, hie, new_id, new_id2)
    hie.remove_node(new_id1)
    hie.remove_node(new_id2)


# builds a relation between identical graphs of two hierarchies
# used when merging two hierarchies together
# graphs and paths must be the same for the graphs to be identified
def _same_graphs(hie1, hie2, rel):
    for id1, id2s in rel.items():
        for id2 in id2s:
            new_rel = copy.deepcopy(rel)
            for ch2 in all_children(hie2, id2):
                for ch1 in all_children(hie1, id1):
                    if hie1.node[ch1].attrs["name"] == hie2.node[ch2].attrs["name"]\
                            and hie1.node[ch1] == hie2.node[ch2]:
                        if ch1 in new_rel:
                            new_rel[ch1].add(ch2)
                        else:
                            new_rel[ch1] = {ch2}
    if valid_attributes(new_rel, rel):
        return rel
    else:
        return _same_graphs(hie1, hie2, new_rel)


def _update_typing(hie, n1, n2, typing):
    if hie.has_edge(n1, n2):
        typ = hie.edge[n1][n2].mapping
        for (s, t) in typing.mapping.items():
            if s in typ and typ[s] != t:
                raise ValueError("conflict in Update Typing")
            else:
                typ[s] = t
    else:
        hie.add_typing(n1, n2, typing.mapping, typing.total)
        _update_name(hie, n1)


def _update_name(hie, g_id):
    old = hie.node[g_id].attrs["name"]
    hie.node[g_id].attrs["name"] = None
    hie.node[g_id].attrs["name"] =\
        get_valid_name(hie, g_id, old)
    new = hie.node[g_id].attrs["name"]


# TODO: add  support for rules
def _add_new_graphs(hie1, hie2, rel, visited2):
    new_graphs = {}

    def _fix_attrs(attrs_input):
        new_attrs = dict()
        for key, value in attrs_input.items():
            if type(value) is dict:
                if "strSet" in value.keys() and "numSet" in value.keys():
                    if "neg_list" in value["strSet"].keys() and\
                       len(value["strSet"]["neg_list"]) == 0:
                        new_attrs[key] = UniversalSet()
            else:
                new_attrs[key] = value
        return new_attrs

    # duplicate nodes from hie1 if they have multiple equivalents in hie2
    for node1 in rel:
        for (i, node2) in enumerate(rel[node1]):
            if node2 in visited2:
                visited2.remove(node2)
            if i == 0:
                new_graphs[node1] = (node1, node2)
            else:
                new_id = hie1.unique_graph_id(node1)
                new_gr = copy.deepcopy(hie1.node[node1].graph)
                dic1 = copy.deepcopy(hie1.node[node1].attrs)
                dic2 = copy.deepcopy(hie2.node[node2].attrs)
                recursive_merge(dic1, dic2)
                hie1.add_graph(new_id, new_gr, dic1)
                new_graphs[new_id] = (node1, node2)

    # add visited nodes from hie2 that are not in hie1
    for node2 in visited2:
        new_id = hie1.unique_graph_id(node2)
        new_gr = copy.deepcopy(hie2.node[node2].graph)
        new_attrs = copy.deepcopy(hie2.node[node2].attrs)
        hie1.add_graph(new_id, new_gr, new_attrs)
        new_graphs[new_id] = (None, node2)

    for n_id, (node1, node2) in new_graphs.items():

        # duplicate typings of duplicated nodes of hie1
        if node1 != n_id and node1 is not None:
            for suc in hie1.successors(node1):
                typ = hie1.edge[node1][suc]
                hie1.add_typing(n_id, suc, typ.mapping, typ.total)
                _update_name(hie1, n_id)
            for pre in hie1.predecessors(node1):
                typ = hie1.edge[pre][node1]
                hie1.add_typing(pre, n_id, typ.mapping, typ.total)
                _update_name(hie1, pre)

        # add typings in hie1 for the nodes that only appear in hie2
        if node1 is None:
            for suc in hie2.successors(node2):
                hie1_sucs = [g_id for g_id in new_graphs
                             if new_graphs[g_id][1] == suc]
                typ = hie2.edge[node2][suc]
                for suc1 in hie1_sucs:
                    if not hie1.has_edge(n_id, suc1):
                        hie1.add_typing(n_id, suc1, typ.mapping, typ.total)
                        _update_name(hie1, n_id)
            for pre in hie2.predecessors(node2):
                hie1_pres = [g_id for g_id in new_graphs
                             if new_graphs[g_id][1] == pre]
                typ = hie2.edge[pre][node2]
                for pre1 in hie1_pres:
                    if not hie1.has_edge(pre1, n_id):
                        hie1.add_typing(pre1, n_id, typ.mapping, typ.total)
                        _update_name(hie1, pre1)

        # add or complete typings between nodes that are both in hie1 and hie2
        else:
            for n_id_2, (node1_2, node2_2) in new_graphs.items():
                if n_id_2 != n_id and node1_2 is not None:
                    if hie1.has_edge(node1, node1_2):
                        _update_typing(hie1, n_id, n_id_2,
                                       hie1.edge[node1][node1_2])
                    if hie2.has_edge(node2, node2_2):
                        _update_typing(hie1, n_id, n_id_2,
                                       hie2.edge[node2][node2_2])


def merge_json_into_hierarchy(hie, json_data, top):
    """incorporate json hierarchy into existing one"""
    new_hie = Hierarchy(hie.directed, graph_node_cls=GraphNode)
    # here we preprocess json_data a bit
    # _preprocess(json_data)
    new_top = from_json_tree(new_hie, json_data, None)
    add_types(new_hie, top)
    tmp_add_attributes(new_hie, top)
    _merge_hierarchy(hie, new_hie, top, new_top)


def _merge_hierarchy(hie1, hie2, top1, top2):
    rel = _same_graphs(hie1, hie2, {top1: {top2}})
    visited2 = hie2.descendents(top2)
    _add_new_graphs(hie1, hie2, rel, visited2)


def new_action_graph(hie, nug_typings):
    """replace partial ag by total ag (adding non typed nodes to it)"""
    """(used for import from indra)"""

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
    hie.add_typing("action_graph", "kami", ag_kami, total=True)
    for nug in nug_typings:
        hie.add_typing(nug, "action_graph", nug_typings[nug], total=True)


def get_metadata(hie, graph_id, path):
    """ returns information about the graph and it's direct children"""

    def _graph_data(graph_id, path):
        node = hie.node[graph_id]
        tmp_data = {}
        tmp_data["id"] = graph_id
        tmp_data["name"] = node.attrs["name"].to_json()
        tmp_data["path"] = path
        if "children_types" in node.attrs:
            tmp_data["children_types"] = node.attrs["children_types"]
        else:
            tmp_data["children_types"] = ["graph", "rule"]
        if "rate" in node.attrs:
            tmp_data["rate"] = node.attrs["rate"]
        if path == "/":
            tmp_data["type"] = "top"
        elif "type" in node.attrs:
            tmp_data["type"] = node.attrs["type"]
        elif isinstance(node, RuleNode):
            tmp_data["type"] = "rule"
        elif isinstance(node, GraphNode):
            tmp_data["type"] = "graph"
        return tmp_data

    json_data = _graph_data(graph_id, path)

    if path == "/":
        json_data["children"] =\
            [_graph_data(child,
                         "/{}".format(list(hie.node[child].attrs["name"].fset)[0]))
             for child in all_children(hie, graph_id)]
    else:
        json_data["children"] =\
            [_graph_data(child,
                         "{}/{}".format(
                             path, list(hie.node[child].attrs["name"].fset)[0]))
             for child in all_children(hie, graph_id)]
    return json_data


def add_positions(mouse_x, mouse_y, positions_old, positions_new, old_to_new):
    """add positions of copy/pasted nodes to the graph attributes"""
    old_positions = {}
    for node in old_to_new:
        if node in positions_old:
            old_positions[node] = positions_old[node]
    nodes_number = len(old_positions)
    if nodes_number != 0:
        barycenter_x =\
            sum(pos["x"] for pos in old_positions.values()) / nodes_number
        barycenter_y =\
            sum(pos["y"] for pos in old_positions.values()) / nodes_number
        for node in old_positions:
            positions_new[old_to_new[node]] = {
                "x": mouse_x - barycenter_x + positions_old[node]["x"],
                "y": mouse_y - barycenter_y + positions_old[node]["y"]}


def paste_nodes(hie, top, graph_id, parent_path, nodes, mouse_x, mouse_y):
    """paste the selected nodes from graph at parent_path to graph_id"""
    path_list = [s for s in parent_path.split("/") if s and not s.isspace()]
    other_id = child_from_path(hie, top, path_list)
    gr = hie.node[graph_id].graph
    other_gr = hie.node[other_id].graph
    old_to_new = {}

    # check that all copied nodes exist in the graph
    for node in nodes:
        if node not in other_gr:
            raise ValueError(
                "copied node {} does not exist anymore".format(node))

    if hie.has_edge(graph_id, other_id):
        mapping = hie.edge[graph_id][other_id].mapping
        for node in nodes:
            n_id = prim.unique_node_id(gr, node)
            prim.add_node(gr, n_id, other_gr.node[node])
            old_to_new[node] = n_id
            mapping[n_id] = node
        for (source, target) in other_gr.subgraph(nodes).edges():
            prim.add_edge(gr, old_to_new[source], old_to_new[target],
                          other_gr.edge[source][target])
    else:
        # check that all necessary typings are there
        necessary_typings = [typing for typing in hie.successors(graph_id)]
        #  if hie.edge[graph_id][typing].total]
        # until UI can handle partial typings
        typings = [typing for typing in hie.successors(graph_id)
                   if typing in hie.successors(other_id)]
        for typing in necessary_typings:
            if typing not in typings:
                raise ValueError("copied nodes not typed by {}".format(typing))
            for node in nodes:
                if node not in hie.edge[other_id][typing].mapping:
                    raise ValueError("copied node {} is not typed by {}"
                                     .format(node, typing))
        for node in nodes:
            node_id = prim.unique_node_id(gr, node)
            old_to_new[node] = node_id
            prim.add_node(gr, node_id, other_gr.node[node])
            for typing in typings:
                other_mapping = hie.edge[other_id][typing].mapping
                if node in other_mapping:
                    hie.edge[graph_id][typing].mapping[old_to_new[node]] =\
                        other_mapping[node]
        for (source, target) in other_gr.subgraph(nodes).edges():
            prim.add_edge(gr, old_to_new[source], old_to_new[target],
                          other_gr.edge[source][target])

    if "positions" in hie.node[other_id].attrs:
        if "positions" not in hie.node[graph_id].attrs:
            hie.node[graph_id].attrs["positions"] = {}
        positions_old = hie.node[other_id].attrs["positions"]
        positions_new = hie.node[graph_id].attrs["positions"]
        add_positions(mouse_x, mouse_y, positions_old, positions_new,
                      old_to_new)
