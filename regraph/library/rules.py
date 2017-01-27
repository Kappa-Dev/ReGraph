import copy
from regraph.library.rewriters import Transformer
from regraph.library.rewriters import Rewriter
import json
class Rule():

    def __init__(self, name, pattern, parent):
        self.name = name
        self.pattern = copy.deepcopy(pattern)
        self.pattern.input_constraints = {}
        self.pattern.output_constraints = {}
        self.parent = parent
        self.transformer = Transformer(self.pattern)
        self.transformer.L = copy.deepcopy(self.pattern)
        self.transformer.P = copy.deepcopy(self.pattern)
        self.transformer.R = copy.deepcopy(self.pattern)
        self.transformer.P_L_dict = copy.deepcopy(
            self.transformer.identity().mapping_)
        self.transformer.P_R_dict = copy.deepcopy(
            self.transformer.identity().mapping_)
        self.initTransformer = copy.deepcopy(self.transformer)
        self.history = []
    
    def __eq__(self, value):
        return(self.transformer == value.transformer)

    def to_json_like(self):
        h = dict()
        h["L"] = self.transformer.L.to_json_like()
        h["P"] = self.transformer.P.to_json_like()
        h["R"] = self.transformer.R.to_json_like()
        h["PL"] = self.transformer.P_L_dict
        h["PR"] = self.transformer.P_R_dict
        h["name"] = self.name
        return h

    def from_json_like(self, rule):
        self.transformer.L.from_json_like(rule["L"])
        self.transformer.P.from_json_like(rule["P"])
        self.transformer.R.from_json_like(rule["R"])
        self.transformer.P_L_dict = rule["PL"]
        self.transformer.P_R_dict = rule["PR"]

    def validNewMetamodel(self, new_metamodel):
        return(self.pattern.validNewMetamodel(new_metamodel) and
               self.transformer.validNewMetamodel(new_metamodel) and
               self.initTransformer.validNewMetamodel(new_metamodel))

    def updateMetamodel(self, new_metamodel):
        if self.validNewMetamodel(new_metamodel):
            self.pattern.updateMetamodel(new_metamodel)
            self.transformer.updateMetaModel(new_metamodel)
            self.initTransformer.updateMetaModel(new_metamodel)

    def removeType(self, type_to_remove):
        self.pattern.removeType(type_to_remove)
        self.transformer.removeType(type_to_remove)
        self.initTransformer.removeType(type_to_remove)

    def convertType(self, old_type, new_type):
        self.pattern.convertType(old_type, new_type)
        self.transformer.convertType(old_type, new_type)
        self.initTransformer.convertType(old_type, new_type)

    def removeEdgesByType(self, source_type, target_type):
        self.pattern.removeEdgesByType(source_type, target_type)
        self.transformer.removeEdgesByType(source_type, target_type)
        self.initTransformer.removeEdgesByType(source_type, target_type)

    def main_graph(self):
        return(self.transformer.R)

    def _do_add_not_catched(self, node_id, node_type):
        t2 = copy.deepcopy(self.transformer)
        t2.add_node(node_id, node_type)
        # new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("add " + node_id + ":" + str(node_type),
                             lambda t: t.add_node(node_id, node_type)))

    def _do_ln_not_catched(self, node1, node2):
        t2 = copy.deepcopy(self.transformer)
        t2.add_edge(node1, node2)
        # new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("ln " + node1 + " " + node2,
                             lambda t: t.add_edge(node1, node2)))

    def _do_rm_node_not_catched(self, node_id):
        t2 = copy.deepcopy(self.transformer)
        t2.remove_node(node_id)
        # new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("rm_node " + node_id,
                             lambda t: t.remove_node(node_id)))

    def _do_rm_node_force_not_catched(self, node_id):
        self._do_rm_node_not_catched(node_id)


    def _do_merge_nodes_not_catched(self, node1, node2, new_name):
        t2 = copy.deepcopy(self.transformer)
        t2.merge_nodes(node1, node2, new_name)
        # new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(
            ("merge_nodes " + node1 + " " + node2 + " " + new_name,
             lambda t: t.merge_nodes(node1, node2, new_name))
             )

    def _do_merge_nodes_force_not_catched(self, node1, node2, new_node_id):
        self._do_merge_nodes_not_catched(node1, node2, new_node_id)


    def _do_clone_node_not_catched(self, node_id, new_name):
        t2 = copy.deepcopy(self.transformer)
        t2.clone_node(node_id, new_name)
        # new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("clone_node " + node_id + " " + new_name,
                             lambda t: t.clone_node(node_id, new_name)))

    def _do_rm_edge_uncatched(self, source, target, force_flag):
        t2 = copy.deepcopy(self.transformer)
        t2.remove_edge(source, target)
        # new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("remove_edge " + source + " " + target,
                             lambda t: t.remove_edge(source, target)))

    def remove_attrs(self, node, attr_dict, force=False):
        self.transformer.remove_node_attrs(node,attr_dict)

    #precondition: degree > 0
    def ancestors(self, degree):
        if not self.parent:
            raise ValueError("the command does not have a parent")
        if degree == 1:
            leftMapping = [{"left":n,"right":self.transformer.L.node[n].type_}
                           for n in self.transformer.L.nodes()]
            rightMapping = [{"left":n,"right":self.transformer.R.node[n].type_}
                           for n in self.transformer.R.nodes()]
            preservedMapping = [{"left":n,"right":self.transformer.P.node[n].type_}
                           for n in self.transformer.P.nodes()]
            return {"L":leftMapping,"P":preservedMapping,"R":rightMapping}               
        else:
            parentMapping = self.parent.ancestors_aux(degree-1)
            leftMapping = [{"left":n,"right":parentMapping[self.transformer.L.node[n].type_]}
                           for n in self.transformer.L.nodes()]
            rightMapping = [{"left":n,"right":parentMapping[self.transformer.R.node[n].type_]}
                           for n in self.transformer.R.nodes()]
            preservedMapping = [{"left":n,"right":parentMapping[self.transformer.P.node[n].type_]}
                           for n in self.transformer.P.nodes()]
            return {"L":leftMapping,"P":preservedMapping,"R":rightMapping}


                             