import copy
from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import Homomorphism
from regraph.library.rewriters import Transformer
from regraph.library.rewriters import Rewriter
from regraph.library.rules import Rule
from regraph.library.kami_to_metakappa import to_kappa_like

import json
from regraph.library.nugget_rules import AbstractRules

class Hierarchy():
    suffix_node_name = 0

    def __init__(self, name, parent):
        self.name = name
        self.subCmds = {}
        self.subRules = {}
        self.parent = parent
        if parent is not None and parent.graph is not None:
            self.graph = TypedDiGraph(metamodel=parent.graph)
        else:
            self.graph = TypedDiGraph(metamodel=None)

    def main_graph(self):
        return(self.graph)

    def hierarchy_to_json(self, include_rules):
        h = {"name": self.name,
             "top_graph": (self.graph.to_json_like()
                           if self.graph is not None
                           else None),
             "children": [sub.hierarchy_to_json(include_rules)
                          for sub in self.subCmds.values()]}
        if include_rules:
            h["rules"] = [r.to_json_like() for r in self.subRules.values()]
        return h

    def hierarchy_of_names(self, include_rules):
        print(self.subCmds.keys())
        h = {"name": self.name,
             "children": [sub.hierarchy_of_names(include_rules)
                          for sub in self.subCmds.values()]}
        if include_rules:
            h["rules"] = list(self.subRules.keys())
        return h

    def valid_new_name(self, new_name):
        return(new_name not in self.subCmds.keys() and
               new_name not in self.subRules.keys())

    def subCmd(self, path):
        if path == []:
            return(self)
        elif path[0] == "":
            return(self.subCmd(path[1:]))
        elif path[0] in self.subCmds.keys():
            return(self.subCmds[path[0]].subCmd(path[1:]))
        else:
            raise KeyError("Path does not correspond to an existing graph")

    def updateMetamodel(self, new_typing_graph):
        self.graph.updateMetamodel(new_typing_graph)

    def updateSubMetamodels(self, new_typing_graph):
        if all(sub.graph.validNewMetamodel(new_typing_graph)
               for sub in self.subCmds.values())\
           and all(rule.validNewMetamodel(new_typing_graph)
                   for rule in self.subRules.values()):
            for sub in self.subCmds.values():
                sub.updateMetamodel(new_typing_graph)
            for rule in self.subRules.values():
                rule.updateMetamodel(new_typing_graph)
        else:
            raise ValueError("Metamodel update cannot work")

    def possibleEdge(self, node1, node2):
        if self.parent is None:
            return True
        else:
            type1 = self.graph.node[node1].type_
            type2 = self.graph.node[node2].type_
            return(self.graph.metamodel_.exists_edge(type1, type2))

    def nodesTypedBy(self, node_id):
        return([n for sub in self.subCmds.values() for n in sub.graph.nodes()
                if sub.graph.node[n].type_ == node_id])

    def possibleOutgoingEdge(self, node1):
        # improvement : test if a node of the target type actually exists
        if self.parent is None:
            return True
        else:
            type1 = self.graph.node[node1].type_
            return(self.graph.metamodel_.exists_outgoing_edge(type1))


    def _do_mkdir(self, name):
        self.subCmds[name] = Hierarchy(name, self)

    def _do_add_not_catched(self, nodeId, nodeType):
        tr = Transformer(self.graph)
        tr.add_node(nodeId, nodeType)
        self.graph = Rewriter.rewrite_simple(tr)
        self.updateSubMetamodels(self.graph)

    def _do_ln_not_catched(self, node1, node2):
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

    def _do_clone_node_not_catched(self, node1, clone_name):
        tr = Transformer(self.graph)
        tr.clone_node(node1, clone_name)
        self.graph = Rewriter.rewrite_simple(tr)
        self.updateSubMetamodels(self.graph)

    def _do_rm_edge_uncatched(self, node1, node2, force):
        if force:
            for sub in self.subCmds.values():
                for (n1, n2) in sub.graph.edges():
                    if (sub.graph.node[n1].type_ == node1
                            and sub.graph.node[n2].type_ == node2):
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

    def _do_apply_rule_no_catching(self, rule, graph_name, new_name, matching):
        graph = self.subCmds[graph_name].graph
        trans = copy.deepcopy(self.subRules[rule].transformer)
        trans.appendToNodesNames(Hierarchy.suffix_node_name)
        new_matching = {(str(k) + "_" + str(Hierarchy.suffix_node_name)): v for (k, v) in matching.items()}
        Hierarchy.suffix_node_name += 1
        pattern = trans.L
        trans.G = graph
        L_G = Homomorphism(pattern, graph, new_matching)
        new_graph = Rewriter.rewrite(L_G, trans)
        self.subCmds[new_name] = Hierarchy(
            new_name,self)
        self.subCmds[new_name].graph = new_graph

    def _add_subgraph_no_catching(self, graph, name):
        if name not in self.subCmds.keys():
            self.subCmds[name] = Hierarchy(name, self)
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
        cmd = Hierarchy(subHierarchy["name"], self)
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

    def checkHierarchy(self):
        for sub in self.subCmds.values():
            sub.graph.checkConstraint(all_nodes=True)
            sub.checkHierarchy()

    def checkConstraintsOfTypes(self, types):
        # possible optimisation : only check one constraint
        for sub in self.subCmds.values():
            to_check = set(sub.graph.nodesOfTypes(types))
            sub.graph.unckecked_nodes |= to_check
            sub.graph.checkConstraints()
            sub.checkConstraintsOfTypes(to_check)

    def addInputConstraint(self, n1, n2, cond, viewableCond):
        self.graph.addInputConstraint(n1, n2, cond, viewableCond)
        self.checkConstraintsOfTypes({n1})

    def addOutputConstraint(self, n1, n2, cond, viewableCond):
        self.graph.addOutputConstraint(n1, n2, cond, viewableCond)
        self.checkConstraintsOfTypes({n1})

    def deleteInputConstraint(self, n1, viewableCond):
        self.graph.deleteInputConstraint(n1, viewableCond)
        self.checkConstraintsOfTypes({n1})

    def deleteOutputConstraint(self, n1, viewableCond):
        self.graph.deleteOutputConstraint(n1, viewableCond)
        self.checkConstraintsOfTypes({n1})

    def _do_rename_graph_no_catching(self, old_name, new_name):
        if old_name not in self.subCmds.keys():
            raise ValueError("The graph "+old_name+" does not exist")
        if not self.valid_new_name(new_name):
            raise ValueError("a rule or graph named " +
                             new_name + " already exists")
        self.subCmds[new_name] = self.subCmds.pop(old_name)
        self.subCmds[new_name].name = new_name

    def _do_rename_rule_no_catching(self, old_name, new_name):
        if old_name not in self.subRules.keys():
            raise ValueError("The rule "+old_name+" does not exist")
        if not self.valid_new_name(new_name):
            raise ValueError("a rule or graph named " +
                             new_name + " already exists")
        self.subRules[new_name] = self.subRules.pop(old_name)
        self.subRules[new_name].name = new_name

    # def unfold_abstract_nugget(self, new_metamodel_name):
    #     if (self.parent is None or
    #        self.parent.graph is None or
    #        self.parent.parent.graph is None):
    #         raise ValueError("An abstract nugget must have\
    #                          a parent and a granparent")

    #     if new_metamodel_name in self.parent.parent.subCmds.keys():
    #         raise ValueError("There is already a graph with name: " +
    #                          new_metamodel_name)
    #     abstract_nug = AbstractNugget(self.graph, "Var")
    #     (new_nuggets, new_metamodel) = abstract_nug.unfold_variables()
    #     self.parent.parent.subCmds[new_metamodel_name] =\
    #         Hierarchy(new_metamodel_name, self.parent.parent)
    #     parent_cmd = self.parent.parent.subCmds[new_metamodel_name]
    #     parent_cmd.graph = new_metamodel
    #     for (i, new_nugget) in enumerate(new_nuggets):
    #         new_nugget_name = self.name + "_" + str(i)
    #         parent_cmd.subCmds[new_nugget_name] = Hierarchy(
    #                                                  new_nugget_name,
    #                                                  parent_cmd)
    #         parent_cmd.subCmds[new_nugget_name].graph = new_nugget

    def unfold_abstract_nuggets(self, new_metamodel_name, nuggetsNames):
        for name in nuggetsNames:
            if (name not in self.subCmds.keys() and
               name not in self.subRules.keys()):
                raise ValueError(name + " is not a nugget name")
        if self.graph.metamodel_ is None:
            raise ValueError("The graph does not have a metamodel")
        if new_metamodel_name in self.parent.subCmds.keys():
            raise ValueError("There is already a graph with name: " +
                             new_metamodel_name)
        concrete_nuggets = [(name, self.subCmds[name]) for name in nuggetsNames
                            if name in self.subCmds.keys()]
        abstract_nuggets = [(name, self.subRules[name].transformer)
                            for name in nuggetsNames
                            if name in self.subRules.keys()]
        exceptions = [e.graph for e in self.subCmds.values()
                      if "exception_nugget" in e.graph.graph_attr.keys()]
        aNugs = AbstractRules(abstract_nuggets, "Var", exceptions)
        (new_metamodel, new_nuggets) = aNugs.fixed_point()
        self.parent.subCmds[new_metamodel_name] =\
            Hierarchy(new_metamodel_name, self.parent)
        parent_cmd = self.parent.subCmds[new_metamodel_name]
        parent_cmd.graph = new_metamodel
        for (name, nugs) in new_nuggets:
            for (i, new_nugget) in enumerate(nugs):
                new_nugget_name = name + "_" + str(i)
                parent_cmd.subCmds[new_nugget_name] = Hierarchy(
                                                        new_nugget_name,
                                                        parent_cmd)
                parent_cmd.subCmds[new_nugget_name].graph = new_nugget

        # copy the selected concrete nuggets to the new metamodel
        for (nug_name, nug) in concrete_nuggets:
            new_nug = Hierarchy(
                nug_name,
                parent_cmd)
            new_nug.graph = copy.deepcopy(nug.graph)
            new_nug.graph.metamodel_ = parent_cmd.graph
            parent_cmd.subCmds[nug_name] = new_nug

Hierarchy.to_kappa_like = to_kappa_like
