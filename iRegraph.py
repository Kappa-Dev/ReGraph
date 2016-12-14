import cmd
import os
import copy
import sys
from regraph.library.data_structures import TypedDiGraph
from regraph.library.data_structures import Homomorphism
from regraph.library.rewriters import Transformer
from regraph.library.rewriters import Rewriter
from subprocess import Popen, STDOUT
from regraph.library.utils import plot_graph, plot_instance
import readline
import json
from regraph.library.nugget_rules import AbstractNugget, AbstractRules


class MakeRuleCmd(cmd.Cmd):

    def __init__(self, name, fullname, pattern, parent, png_viewer_location):
        super().__init__()
        readline.set_completer_delims(' ')
        self.name = name
        self.fullname = fullname
        self.pattern = copy.deepcopy(pattern)
        self.pattern.input_constraints = {}
        self.pattern.output_constraints = {}
        self.prompt = "#rulz_factory :" + self.fullname + ">"
        self.parent = parent
        self.location_ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        self.start_image_fileName_ = self.fullname.replace(
            "/", "__") + "_start.png"
        self.absolute_start_image_filename_ = os.path.join(
            self.location_, self.start_image_fileName_)
        self.end_image_fileName_ = self.fullname.replace(
            "/", "__") + "_end.png"
        self.absolute_end_image_filename_ = os.path.join(
            self.location_, self.end_image_fileName_)
        self.image_reader_ = png_viewer_location
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
        self.do_update("")

    def convertType(self, old_type, new_type):
        self.pattern.convertType(old_type, new_type)
        self.transformer.convertType(old_type, new_type)
        self.initTransformer.convertType(old_type, new_type)
        self.do_update("")

    def removeEdgesByType(self, source_type, target_type):
        self.pattern.removeEdgesByType(source_type, target_type)
        self.transformer.removeEdgesByType(source_type, target_type)
        self.initTransformer.removeEdgesByType(source_type, target_type)
        self.do_update("")

    def _do_draw_start(self):
        plot_graph(
            self.transformer.L,
            types=self.parent,
            filename=self.absolute_start_image_filename_)

    def _do_draw_end(self):
        plot_graph(
            self.transformer.R,
            types=self.parent,
            filename=self.absolute_end_image_filename_)

    def do_cd(self, arguments):
        if arguments == "..":
            return(True)
        else:
            print("Usage: 'cd ..' to get out of rule definition mode")

    def emptyline(self):
        pass

    def do_EOF(self, _):
        return(True)

    def _open_image_reader_end(self):
        FNULL = open(os.devnull, 'w')
        Popen([self.image_reader_, self.absolute_end_image_filename_],
              stdout=FNULL, stderr=STDOUT)

    def open_end(self):
        self._do_draw_end()
        self._open_image_reader_end()

    def _open_image_reader_start(self):
        FNULL = open(os.devnull, 'w')
        Popen([self.image_reader_, self.absolute_start_image_filename_],
              stdout=FNULL, stderr=STDOUT)

    def open_start(self):
        self._do_draw_start()
        self._open_image_reader_start()

    def do_update(self, arguments):
        self._do_draw_end()
        self._do_draw_start()

    def do_cat(self, arguments):
        self.open_start()
        self.open_end()

    def main_graph(self):
        return(self.transformer.R)

    def preloop(self):
        print("script:", [com for (com, fun) in self.history])

    def do_script(self, arguments):
        for (com, _) in self.history:
            print(com)

    def _do_add_not_catched(self, node_id, node_type):
        t2 = copy.deepcopy(self.transformer)
        t2.add_node(node_id, node_type)
        new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("add " + node_id + ":" + str(node_type),
                             lambda t: t.add_node(node_id, node_type)))

    def _do_add_node(self, node_id, node_type):
        t2 = copy.deepcopy(self.transformer)
        try:
            t2.add_node(node_id, node_type)
            new_graph = Rewriter.rewrite_simple(t2)
            self.transformer = t2
            self.history.append(("add " + node_id + ":" + str(node_type),
                                 lambda t: t.add_node(node_id, node_type)))
            print("script:", [com for (com, fun) in self.history])
        except ValueError as error_message:
            print(error_message)
        self._do_draw_end()

    def do_add(self, arguments):
        argv = arguments.split()
        if len(argv) == 2:
            [node_id, node_type] = argv
            self._do_add_node(node_id, node_type)
        else:
            print("Usage: add_node node_id node_type")

    def complete_add(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 2 and line[-1] == " ") or (argc == 3 and line[-1] != " "):
            return([n for n in self.pattern.metamodel_.nodes()
                    if n.startswith(text)])

    def _do_ln_not_catched(self, node1, node2):
        t2 = copy.deepcopy(self.transformer)
        t2.add_edge(node1, node2)
        new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("ln " + node1 + " " + node2,
                             lambda t: t.add_edge(node1, node2)))

    def _do_ln(self, node1, node2):
        try:
            self._do_ln_not_catched(node1, node2)
            print("script:", [com for (com, fun) in self.history])
        except ValueError as error_message:
            print(error_message)
        self._do_draw_end()

    def do_ln(self, arguments):
        argv = arguments.split()
        if len(argv) != 2:
            print("Usage : ln source target")
        else:
            [node1, node2] = argv
            self._do_ln(node1, node2)

    def complete_ln(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.transformer.R.nodes()
                    if s.startswith(text)])

        elif (argc == 2) or (argc == 3 and line[-1] != " "):
            node1 = argv[1]
            return([s for s in self.transformer.R.nodes()
                    if s.startswith(text) and
                    not self.transformer.R.exists_edge(node1, s)])
        else:
            return([])

    def _do_rm_node_not_catched(self, node_id):
        t2 = copy.deepcopy(self.transformer)
        t2.remove_node(node_id)
        new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("rm_node " + node_id,
                             lambda t: t.remove_node(node_id)))

    def _do_rm_node_force_not_catched(self, node_id):
        self._do_rm_node_not_catched(node_id)

    def _do_rm_node(self, node_id):
        try:
            self._do_rm_node_not_catched(node_id)
            print("script:", [com for (com, fun) in self.history])
        except ValueError as error_message:
            print(error_message)
        self._do_draw_end()

    def do_rm_node(self, arguments):
        argv = arguments.split()
        if len(argv) == 1:
            nodeId = argv[0]
            if nodeId in self.transformer.R.nodes():
                self._do_rm_node(nodeId)
            else:
                print("Le noeud", nodeId, " n'existe pas")
        else:
            print("Usage : rm_node [-f] node")

    def complete_rm_node(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if argc == 1 or (argc == 2 and line[-1] != " "):
            return([s for s in self.transformer.R.nodes()
                    if s.startswith(text)])

    def _do_merge_nodes_not_catched(self, node1, node2, new_name):
        t2 = copy.deepcopy(self.transformer)
        t2.merge_nodes(node1, node2, new_name)
        new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(
            ("merge_nodes " + node1 + " " + node2 + " " + new_name,
             lambda t: t.merge_nodes(node1, node2, new_name))
             )

    def _do_merge_nodes_force_not_catched(self, node1, node2, new_node_id):
        self._do_merge_nodes_not_catched(node1, node2, new_node_id)

    def _do_merge_nodes(self, node1, node2, new_name):
        try:
            self._do_merge_nodes_not_catched(node1, node2, new_name)
            print("script:", [com for (com, fun) in self.history])
        except ValueError as error_message:
            print(error_message)
        self._do_draw_end()

    def do_merge_nodes(self, arguments):
        argv = arguments.split()
        if len(argv) == 3:
            [node1, node2, new_name] = argv
            if node1 not in self.transformer.R.nodes():
                print(node1, "is not a node of the graph")
            elif node2 not in self.transformer.R.nodes():
                print(node2, "is not a node of the graph")
            elif node1 == node2:
                print("You cannot merge a node with itself")
            else:
                self._do_merge_nodes(node1, node2, new_name)
        else:
            print("Usage merge_nodes node1 node2 new_name")

    def complete_merge_nodes(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.transformer.R.nodes()
                    if (s.startswith(text))])
        elif (argc == 2 or (argc == 3 and line[-1] != " ")):
            return([s for s in self.transformer.R.nodes()
                    if s.startswith(text) and s != argv[1]])

    def _do_clone_node_not_catched(self, node_id, new_name):
        t2 = copy.deepcopy(self.transformer)
        t2.clone_node(node_id, new_name)
        new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("clone_node " + node_id + " " + new_name,
                             lambda t: t.clone_node(node_id, new_name)))

    def _do_clone_node(self, node_id, new_name):
        try:
            self._do_clone_node_not_catched(node_id, new_name)
            print("script:", [com for (com, fun) in self.history])
        except ValueError as error_message:
            print(error_message)
        self._do_draw_end()

    def do_clone_node(self, arguments):
        argv = arguments.split()
        if len(argv) != 2:
            print("Usage : clone_node node_id new_name")
        else:
            [node1, node2] = argv
            self._do_clone_node(node1, node2)

    def complete_clone_node(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.transformer.R.nodes()
                    if s.startswith(text)])

    def _do_rm_edge_uncatched(self, source, target, force_flag):
        t2 = copy.deepcopy(self.transformer)
        t2.remove_edge(source, target)
        new_graph = Rewriter.rewrite_simple(t2)
        self.transformer = t2
        self.history.append(("remove_edge " + source + " " + target,
                             lambda t: t.remove_edge(source, target)))

    def _do_rm_edge(self, source, target):
        try:
            self._do_rm_edge_not_catched(source, target)
            print("script:", [com for (com, fun) in self.history])
        except ValueError as error_message:
            print(error_message)
        self._do_draw_end()

    def do_rm_edge(self, arguments):
        argv = arguments.split()
        if len(argv) == 2:
            [node1, node2] = argv
            if node1 not in self.transformer.R.nodes():
                print(node1, "is not a node of the graph")
            elif node2 not in self.transformer.R.nodes():
                print(node2, "is not a node of the graph")
            elif node2 not in self.transformer.R.edge[node1].keys():
                print("no edge exists from", node1, "to", node2)
            else:
                self._do_rm_edge(node1, node2)

        else:
            print("Usage: rm_edge source target")

    def complete_rm_edge(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.transformer.R.nodes()
                    if s.startswith(text) and
                    self.transformer.R.exists_outgoing_edge(s)])

        elif (argc == 2 or (argc == 3 and line[-1] != " ")):
            return([s for s in (self.transformer.R.edge[argv[1]].keys()
                    if argv[1] in self.graph.transformer.R.nodes() else [])
                    if s.startswith(text)
                    ]
                   )

class MyCmd(cmd.Cmd):
    suffix_node_name = 0

    def __init__(self, name, fullname, parent, png_viewer_location):
        super().__init__()
        readline.set_completer_delims(' ')
        self.name = name
        self.fullname = fullname
        self.prompt = "# " + self.fullname + " > "
        self.subCmds = {}
        self.subRules = {}
        self.parent = parent
        self.location_ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        self.image_fileName_ = self.fullname.replace("/", "__") + ".png"
        self.absolute_image_filename_ = os.path.join(
            self.location_, self.image_fileName_)
        self.image_reader_ = png_viewer_location
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

    def open_image_reader(self):
        FNULL = open(os.devnull, 'w')
        Popen([self.image_reader_, self.absolute_image_filename_],
              stdout=FNULL, stderr=STDOUT)

    def do_EOF(self, _):
        return(True)

    def emptyline(self):
        pass

    def do_ls(self, _):
        if not self.subCmds.keys():
            print("Nothing typed by this graph yet")
        else:
            print("Subgraphs:")
            for subCmd in self.subCmds.keys():
                print(subCmd, end=" ")
            print()
            print("Rules:")
            for subRule in self.subRules.keys():
                print(subRule, end=" ")
            print()

    # todo : ls of a subgraph
    # def complete_ls(self, text, line, begidx, endidx):

    def do_printGraph(self, arguments):
        # print(self.graph.nodes())
        print("nodes:", [(n, self.graph.node[n].type_)
                         for n in self.graph.nodes()])
        print("edges:", self.graph.edges())

    def do_printMetaModel(self, arguments):
        # print(self.parent.graph.nodes())
        # print(self.parent.graph.edges())
        if self.parent:
            print(self.graph.metamodel_.nodes())
            print(self.graph.metamodel_.edges())
        else:
            print("This graph is not typed")

    def _do_mkdir(self, name):
        self.subCmds[name] = MyCmd(
            name, self.fullname + name + "/", self, self.image_reader_)

    def do_mkdir(self, arguments):
        argv = arguments.split()  # arguments start at position 0
        if len(argv) != 1:
            print("mkdir needs exactly one argument")
        else:
            name = argv[0]
            if name in self.subCmds.keys() or name in self.subRules.keys():
                print("One graph already named that way")
            else:
                self._do_mkdir(name)
                self.subCmds[name].do_cat("")

    def do_cd(self, name):
        if name == "..":
            return(True)
        if (name not in self.subCmds.keys() and
           name not in self.subRules.keys()):
            print("The graph is not a direct subgraph or rule of",
                  self.fullname)
        elif name in self.subCmds.keys():
            self.subCmds[name].cmdloop()
        else:
            self.subRules[name].cmdloop("enter instructions to modify pattern")

    def complete_cd(self, text, line, begidx, endidx):
        return([sub.name for sub in self.subCmds.values()
                if sub.name.startswith(text)] +
               [sub.name for sub in self.subRules.values()
                if sub.name.startswith(text)])

    def _do_add(self, nodeId, nodeType):
        try:
            self._do_add_not_catched(nodeId, nodeType)
        except ValueError as error_message:
            print(error_message)

    def _do_add_not_catched(self, nodeId, nodeType):
        tr = Transformer(self.graph)
        tr.add_node(nodeId, nodeType)
        self.graph = Rewriter.rewrite_simple(tr)
        self._do_cat()
        self.updateSubMetamodels(self.graph)

    def do_add(self, arguments):
        argv = arguments.split()
        if self.parent is None:
            if len(argv) != 1:
                print("Usage : add node_id")
            else:
                nodeId = argv[0]
                if nodeId in self.graph.nodes():
                    print("The node id already exists")
                else:
                    nodeType = None
                    self._do_add(nodeId, nodeType)
        else:
            if len(argv) != 2:
                print("Usage : add node_id node_type")
            else:
                [nodeId, nodeType] = argv
                if nodeId in self.graph.nodes():
                    print("The node id already exists")
                else:
                    self._do_add(nodeId, nodeType)

    def complete_add(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 2 and line[-1] == " ") or (argc == 3 and line[-1] != " "):
            return([n for n in self.graph.metamodel_.nodes()
                    if n.startswith(text)])

    def _do_ln(self, node1, node2):
        try:
            self._do_ln_not_catched(node1, node2)
        except ValueError as error_message:
            print(error_message)

    def _do_ln_not_catched(self, node1, node2):
        tr = Transformer(self.graph)
        tr.add_edge(node1, node2)
        self.graph = Rewriter.rewrite_simple(tr)
        self.updateSubMetamodels(self.graph)
        self._do_cat()

    def do_ln(self, arguments):
        argv = arguments.split()
        if len(argv) != 2:
            print("Usage : ln source target")
        else:
            [node1, node2] = argv
            self._do_ln(node1, node2)

    def complete_ln(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.graph.nodes()
                    if s.startswith(text) and self.possibleOutgoingEdge(s)])

        elif (argc == 2) or (argc == 3 and line[-1] != " "):
            node1 = argv[1]
            return([s for s in self.graph.nodes()
                    if (s.startswith(text) and self.possibleEdge(node1, s)) and
                    not self.graph.exists_edge(node1, s)])
        else:
            return([])

    def _do_rm_node(self, nodeId):
        try:
            self._do_rm_node_not_catched(nodeId)
        except ValueError as error_message:
            print(error_message)
            print("Use rm_node -f to delete all nodes of this type")

    def _do_rm_node_not_catched(self, nodeId):
        tr = Transformer(self.graph)
        tr.remove_node(nodeId)
        new_graph = Rewriter.rewrite_simple(tr)
        self.updateSubMetamodels(new_graph)
        self.graph = new_graph
        self._do_cat()

    def _do_rm_node_force(self, nodeId):
        try:
            self._do_rm_node_force_not_catched(nodeId)
        except ValueError as error_message:
            print(error_message)

    def _do_rm_node_force_not_catched(self, nodeId):
        for sub in self.subCmds.values():
            for n in sub.graph.nodes():
                if sub.graph.node[n].type_ == nodeId:
                    sub.do_rm_node("-f " + n)
        for rule in self.subRules.values():
            rule.removeType(nodeId)

        tr = Transformer(self.graph)
        tr.remove_node(nodeId)
        new_graph = Rewriter.rewrite_simple(tr)
        self.updateSubMetamodels(new_graph)
        self.graph = new_graph
        self._do_cat()

    def do_rm_node(self, arguments):
        argv = arguments.split()
        if len(argv) == 1:
            nodeId = argv[0]
            if nodeId in self.graph.nodes():
                self._do_rm_node(nodeId)
            elif nodeId == "-f":
                print("Usage : rm_node [-f] node")
            else:
                print("Le noeud", nodeId, " n'existe pas")

        elif (len(argv) == 2 and argv[0] == "-f"):
            nodeId = argv[1]
            if nodeId in self.graph.nodes():
                self._do_rm_node_force(nodeId)
            else:
                print("Le noeud n'existe pas")
        else:
            print("Usage : rm_node [-f] node")

    def complete_rm_node(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.graph.nodes()
                    if s.startswith(text) and not self.nodesTypedBy(s)] +
                   (["-f"] if "-f".startswith(text) else []))

        elif (argv[1] == "-f" and ((argc == 2) or
              (argc == 3 and line[-1] != " "))):
            return([s for s in self.graph.nodes()
                    if s.startswith(text)])
        else:
            return([])

    def _do_merge_nodes(self, node1, node2, newName):
        try:
            self._do_merge_nodes_not_catched(node1, node2, newName)
        except ValueError as error_message:
            print(error_message)
            if "image not in target graph" in str(error_message):
                print("Use merge_node -f : nodes typed by", node1,
                      "or", node2, "will then be typed by", newName)

    def _do_merge_nodes_not_catched(self, node1, node2, newName):
        tr = Transformer(self.graph)
        tr.merge_nodes(node1, node2, node_name=newName)
        new_graph = Rewriter.rewrite_simple(tr)
        self.updateSubMetamodels(new_graph)
        self.graph = new_graph
        self._do_cat()

    def _do_merge_nodes_force(self, node1, node2, newName):
        try:
            self._do_merge_nodes_force_not_catched(node1, node2, newName)
        except ValueError as error_message:
            print(error_message)

    def _do_merge_nodes_force_not_catched(self, node1, node2, newName):
        tr = Transformer(self.graph)
        tr.merge_nodes(node1, node2, node_name=newName)
        new_graph = Rewriter.rewrite_simple(tr)
        for sub in self.subCmds.values():
            sub.graph.convertType(node1, newName)
            sub.graph.convertType(node2, newName)
            sub._do_cat()
        for rule in self.subRules.values():
            rule.convertType(node1, newName)
            rule.convertType(node2, newName)
        self.updateSubMetamodels(new_graph)
        self.graph = new_graph
        self._do_cat()

    def do_merge_nodes(self, arguments):
        argv = arguments.split()
        if len(argv) == 3:
            [node1, node2, new_name] = argv
            if node1 == "-f":
                print("Usage merge_nodes [-f] node1 node2 new_name")
            elif node1 not in self.graph.nodes():
                print(node1, "is not a node of the graph")
            elif node2 not in self.graph.nodes():
                print(node2, "is not a node of the graph")
            elif node1 == node2:
                print("You cannot merge a node with itself")
            else:
                self._do_merge_nodes(node1, node2, new_name)

        elif len(argv) == 4:
            [_, node1, node2, new_name] = argv
            if argv[0] != "-f":
                print("Usage merge_nodes [-f] node1 node2 new_name")
            elif node1 not in self.graph.nodes():
                print(node1, "is not a node of the graph")
            elif node2 not in self.graph.nodes():
                print(node2, "is not a node of the graph")
            elif node1 == node2:
                print("You cannot merge a node with itself")
            else:
                self._do_merge_nodes_force(node1, node2, new_name)

        else:
            print("Usage merge_nodes [-f] node1 node2 new_name")

    def complete_merge_nodes(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.graph.nodes()
                    if (s.startswith(text) and (not self.nodesTypedBy(s)))] +
                   (["-f"] if "-f".startswith(text) else []))
        elif ((argc == 2 or (argc == 3 and line[-1] != " ")) and
              argv[1] != "-f"):
            return([s for s in self.graph.nodes()
                    if s.startswith(text) and
                    (not self.nodesTypedBy(s)) and
                    s != argv[1]
                    ]
                   )
        elif argv[1] == "-f" and argc == 2:
            return([s for s in self.graph.nodes()
                    if s.startswith(text)])
        elif argv[1] == "-f" and (argc == 3 or (argc == 4 and line[-1] != " ")):
            return([s for s in self.graph.nodes()
                    if s.startswith(text) and (s != argv[2])])
        else:
            return([])

    def _do_clone_node(self, node1, clone_name):
        try:
            self._do_clone_node_not_catched(node1, clone_name)
        except ValueError as error_message:
            print(error_message)

    def _do_clone_node_not_catched(self, node1, clone_name):
        tr = Transformer(self.graph)
        tr.clone_node(node1, clone_name)
        self.graph = Rewriter.rewrite_simple(tr)
        self._do_cat()
        self.updateSubMetamodels(self.graph)

    def do_clone_node(self, arguments):
        argv = arguments.split()
        if len(argv) == 2:
            [node1, clone_name] = argv
            self._do_clone_node(node1, clone_name)
        else:
            print("Usage: clone_node node clone_name")

    def complete_clone_node(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.graph.nodes()
                    if s.startswith(text)])

    def _do_rm_edge(self, node1, node2):
        try:
            self._do_rm_edge_uncatched(node1, node2, force=False)
        except ValueError as error_message:
            print(error_message)
            print("Use rm_edge -f to delete all edges between type",
                  node1, "and type", node2)

    def _do_rm_edge_force(self, node1, node2):
        try:
            self._do_rm_edge_uncatched(node1, node2, force=True)
        except ValueError as error_message:
            print(error_message)

    def _do_rm_edge_uncatched(self, node1, node2, force):
        if force:
            for sub in self.subCmds.values():
                for (n1, n2) in sub.graph.edges():
                    if (sub.graph.node[n1].type_ == node1
                            and sub.graph.node[n2].type_ == node2):
                        sub.do_rm_edge("-f " + n1 + " " + n2)
            for rule in self.subRules.values():
                rule.removeEdgesByType(node1, node2)
        tr = Transformer(self.graph)
        tr.remove_edge(node1, node2)
        new_graph = Rewriter.rewrite_simple(tr)
        self.updateSubMetamodels(new_graph)
        self.graph = new_graph
        self._do_cat()

    def do_rm_edge(self, arguments):
        argv = arguments.split()
        if len(argv) == 2:
            if argv[1] == "-f":
                print("Usage: rm_edge [-f] source target")
            [node1, node2] = argv
            if node1 not in self.graph.nodes():
                print(node1, "is not a node of the graph")
            elif node2 not in self.graph.nodes():
                print(node2, "is not a node of the graph")
            elif node2 not in self.graph.edge[node1].keys():
                print("no edge exists from", node1, "to", node2)
            else:
                self._do_rm_edge(node1, node2)

        elif len(argv) == 3 and argv[0] == "-f":
            [_, node1, node2] = argv
            if node1 not in self.graph.nodes():
                print(node1, "is not a node of the graph")
            elif node2 not in self.graph.nodes():
                print(node2, "is not a node of the graph")
            elif node2 not in self.graph.edge[node1].keys():
                print("no edge exists from", node1, "to", node2)
            else:
                self._do_rm_edge_force(node1, node2)

        else:
            print("Usage: rm_edge [-f] source target")

    def complete_rm_edge(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if (argc == 1) or (argc == 2 and line[-1] != " "):
            return([s for s in self.graph.nodes()
                    if s.startswith(text) and self.graph.exists_outgoing_edge(s)] +
                   (["-f"] if "-f".startswith(text) else []))

        elif (argc == 2 or (argc == 3 and line[-1] != " ")) and argv[1] != "-f":
            return([s for s in (self.graph.edge[argv[1]].keys() if argv[1] in self.graph.nodes() else [])
                    if s.startswith(text)
                    ]
                   )

        elif argv[1] == "-f" and argc == 2:
            return([s for s in self.graph.nodes()
                    if s.startswith(text) and self.graph.exists_outgoing_edge(s)])

        elif argv[1] == "-f" and (argc == 3 or (argc == 4 and line[-1] != " ")):
            return([s for s in (self.graph.edge[argv[2]].keys() if argv[2] in self.graph.nodes() else [])
                    if s.startswith(text)
                    ]
                   )

        else:
            return([])

    def do_update(self, arguments):
        self._do_cat()

    def _do_cat(self):
        if self.image_reader_ is not None:
            __location__ = os.path.realpath(
                os.path.join(os.getcwd(), os.path.dirname(__file__)))
            fileName = self.fullname.replace("/", "__") + ".png"
            plot_graph(
                self.graph,
                types=self.parent,
                filename=os.path.join(__location__, fileName))

    def do_cat(self, arguments):
        if self.image_reader_ is not None:
            argv = arguments.split()
            if len(argv) == 0:
                self._do_cat()
                self.open_image_reader()
            if len(argv) == 1:
                subGraphName = argv[0]
                if subGraphName in self.subCmds.keys():
                    self.subCmds[subGraphName].do_cat("")
                elif subGraphName in self.subRules.keys():
                    self.subRules[subGraphName].open_end()
                    self.subRules[subGraphName].open_start()
                else:
                    print(subGraphName, "is not a subgraph or rule of", self.name)

    def complete_cat(self, text, line, begidx, endidx):
        return([s for s in self.subCmds.keys() if s.startswith(text)])

    def _do_new_rule(self, name, pattern):
        self.subRules[name] = MakeRuleCmd(
            name, self.fullname + name + "/", self.subCmds[pattern].graph, self, self.image_reader_)
        if self.image_reader_:
            self.subRules[name].open_end()
            self.subRules[name].open_start()

    def do_new_rule(self, arguments):
        argv = arguments.split()
        if len(argv) == 2:
            [name, subgraph] = arguments.split()
            if self.valid_new_name(name):
                if subgraph in self.subCmds.keys():
                    self._do_new_rule(name, subgraph)
                else:
                    print(subgraph, "is not a subgraph of", self.name)
            else:
                print("the name ", name, "is already taken")
        else:
            print("Usage: new_rule rule_name pattern_name")

    def complete_new_rule(self, text, line, begidx, endidx):
        argv = line.split()
        argc = len(argv)
        if argc == 2 or (argc == 3 and line[-1] != " "):
            return([s for s in self.subCmds.keys() if s.startswith(text)])

    def get_matchings(self, rule, graphName):
        graph = self.subCmds[graphName].graph
        pattern = self.subRules[rule].transformer.L
        matchings = Rewriter.find_matching(graph, pattern)
        return matchings

    def _do_apply_rule_no_catching(self, rule, graph_name, new_name, matching):
        graph = self.subCmds[graph_name].graph
        trans = copy.deepcopy(self.subRules[rule].transformer)
        trans.appendToNodesNames(MyCmd.suffix_node_name)
        new_matching = {(str(k) + "_" + str(MyCmd.suffix_node_name)): v for (k, v) in matching.items()}
        MyCmd.suffix_node_name += 1
        pattern = trans.L
        trans.G = graph
        L_G = Homomorphism(pattern, graph, new_matching)
        new_graph = Rewriter.rewrite(L_G, trans)
        self.subCmds[new_name] = MyCmd(
            new_name, self.fullname + new_name + "/", self, self.image_reader_)
        self.subCmds[new_name].graph = new_graph

    def _do_apply_rule(self, rule, graphName, newName):
        graph = self.subCmds[graphName].graph
        trans = copy.deepcopy(self.subRules[rule].transformer)
        trans.appendToNodesNames(MyCmd.suffix_node_name)
        MyCmd.suffix_node_name += 1
        pattern = trans.L
        matchings = Rewriter.find_matching(graph, pattern)
        if matchings:
            print("Matchings:", matchings)
            print("Please chose a matching number between 0 and", len(matchings) - 1)
            matching_number = int(input())
            if 0 <= matching_number < len(matchings):
                try:
                    trans.G = graph
                    L_G = Homomorphism(
                        pattern, graph, matchings[matching_number])
                    new_graph = Rewriter.rewrite(L_G, trans)
                    self.subCmds[newName] = MyCmd(
                        newName, self.fullname + newName + "/", self, self.image_reader_)
                    self.subCmds[newName].graph = new_graph
                    self.subCmds[newName].do_cat("")

                except ValueError as e:
                    print(e)
        else:
            print("No matching for rule", rule,
                  " were found in the graph", graphName)

    def do_apply_rule(self, arguments):
        argv = arguments.split()
        if len(argv) == 3:
            [rule, graph, newName] = argv
            self._do_apply_rule(*argv)

    def _add_subgraph_no_catching(self, graph, name):
        if name not in self.subCmds.keys():
            self.subCmds[name] = MyCmd(
                name, self.fullname + name + "/", self, self.image_reader_)
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
                    new_rule = MakeRuleCmd(r["name"], "",
                                           TypedDiGraph(metamodel=top_graph),
                                           self, self.image_reader_)
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
                    new_rule = MakeRuleCmd(r["name"],
                                           self.fullname+r["name"]+"/",
                                           TypedDiGraph(metamodel=top_graph),
                                           self, self.image_reader_)
                    new_rule.from_json_like(r)
                    self.subRules[r["name"]] = new_rule

    def add_subHierarchy(self, subHierarchy, force=False):
        g = TypedDiGraph(metamodel=self.graph)
        g.from_json_like(subHierarchy["top_graph"])
        if (subHierarchy["name"] in self.subCmds.keys() or
           subHierarchy["name"] in self.subRules.keys()):
            raise(KeyError("name already exists"))

        # self._add_subgraph_no_catching(g,subHierarchy["name"])
        cmd = MyCmd(subHierarchy["name"], self.fullname +
                    subHierarchy["name"] + "/", self, self.image_reader_)
        cmd.graph = g
        for child in subHierarchy["children"]:
            cmd.add_subHierarchy(child)
        if "rules" in subHierarchy.keys():
            for r in subHierarchy["rules"]:
                if (r["name"] in cmd.subCmds.keys() or
                   r["name"] in cmd.subRules.keys()):
                    raise(KeyError("name " + r["name"] + " already exists"))
                new_rule = MakeRuleCmd(r["name"], self.fullname+r["name"]+"/",
                                       TypedDiGraph(metamodel=g), cmd,
                                       self.image_reader_)
                new_rule.from_json_like(r)
                cmd.subCmds[r["name"]] = new_rule
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

    def unfold_abstract_nugget(self, new_metamodel_name):
        if (self.parent is None or
           self.parent.graph is None or
           self.parent.parent.graph is None):
            raise ValueError("An abstract nugget must have\
                             a parent and a granparent")

        if new_metamodel_name in self.parent.parent.subCmds.keys():
            raise ValueError("There is already a graph with name: " +
                             new_metamodel_name)
        abstract_nug = AbstractNugget(self.graph, "Var")
        (new_nuggets, new_metamodel) = abstract_nug.unfold_variables()
        self.parent.parent.subCmds[new_metamodel_name] =\
            MyCmd(new_metamodel_name, "", self.parent.parent,
                  self.image_reader_)
        parent_cmd = self.parent.parent.subCmds[new_metamodel_name]
        parent_cmd.graph = new_metamodel
        for (i, new_nugget) in enumerate(new_nuggets):
            new_nugget_name = self.name + "_" + str(i)
            parent_cmd.subCmds[new_nugget_name] = MyCmd(
                                                     new_nugget_name, "",
                                                     parent_cmd,
                                                     self.image_reader_)
            parent_cmd.subCmds[new_nugget_name].graph = new_nugget

    # def unfold_abstract_nuggets(self, new_metamodel_name, nuggetsNames):
    #     for name in nuggetsNames:
    #         if name not in self.subCmds.keys():
    #             raise ValueError(name + " is not a nugget name")
    #     if self.graph.metamodel_ is None:
    #         raise ValueError("The graph does not have a metamodel")
    #     if new_metamodel_name in self.parent.subCmds.keys():
    #         raise ValueError("There is already a graph with name: " +
    #                          new_metamodel_name)
    #     aNugs = AbstractNuggets([self.subCmds[name].graph for name in nuggetsNames],
    #                             "Var")
    #     (new_metamodel, new_nuggets) = aNugs.fixed_point()
    #     self.parent.subCmds[new_metamodel_name] =\
    #         MyCmd(new_metamodel_name, "", self.parent,
    #               self.image_reader_)
    #     parent_cmd = self.parent.subCmds[new_metamodel_name]
    #     parent_cmd.graph = new_metamodel
    #     for (i, new_nugget) in enumerate(new_nuggets):
    #         new_nugget_name = self.name + "_" + str(i)
    #         parent_cmd.subCmds[new_nugget_name] = MyCmd(
    #                                                  new_nugget_name, "",
    #                                                  parent_cmd,
    #                                                  self.image_reader_)
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
        aNugs = AbstractRules(abstract_nuggets, "Var")
        (new_metamodel, new_nuggets) = aNugs.fixed_point()
        self.parent.subCmds[new_metamodel_name] =\
            MyCmd(new_metamodel_name, "", self.parent,
                  self.image_reader_)
        parent_cmd = self.parent.subCmds[new_metamodel_name]
        parent_cmd.graph = new_metamodel
        for (name, nugs) in new_nuggets:
            for (i, new_nugget) in enumerate(nugs):
                new_nugget_name = name + "_" + str(i)
                parent_cmd.subCmds[new_nugget_name] = MyCmd(
                                                        new_nugget_name, "",
                                                        parent_cmd,
                                                        self.image_reader_)
                parent_cmd.subCmds[new_nugget_name].graph = new_nugget

        # copy the selected concrete nuggets to the new metamodel
        for (nug_name, nug) in concrete_nuggets:
            new_nug = MyCmd(
                nug_name,
                "",
                parent_cmd,
                self.image_reader_
            )
            new_nug.graph = copy.deepcopy(nug.graph)
            new_nug.graph.metamodel_ = parent_cmd.graph
            parent_cmd.subCmds[nug_name] = new_nug

    # self.graph must be typed by kami metamodel
    def to_kappa_like(self):
        contact_map_com = MyCmd(self.name+"_CM", "", None,
                                self.image_reader_)
        contact_map = copy.deepcopy(self.graph)
        contact_map.metamodel_ = None
        #contact_map_com.graph = contact_map
        for nugget in self.subCmds.values():
            new_nugget = MyCmd(nugget.name, "", None,
                               self.image_reader_)
            new_nugget.graph = copy.deepcopy(nugget.graph)
            new_nugget.graph.metamodel_ = None
            contact_map_com.subCmds[nugget.name] = new_nugget

        # add input for binds
        bnd_pattern = TypedDiGraph(self.graph.metamodel_)
        bnd_pattern.add_nodes_from([("b", "bnd"), ("l", "locus")])
        bnd_pattern.add_edges_from([("l", "b")])
        matchings = Rewriter.find_matching(self.graph, bnd_pattern)
        for (i, mat) in enumerate(matchings):
            # rewrite the action graph
            new_s_bnd = "s_bnd_{}".format(i)
            contact_map.add_node(new_s_bnd, "s_BND")
            # contact_map.remove_edge(mat["l"], mat["b"])
            contact_map.add_edge(mat["l"], new_s_bnd)
            contact_map.add_edge(new_s_bnd, mat["b"])
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from([("b", mat["b"]), ("l", mat["l"])])
            nug_pattern.add_edges_from([("l", "b")])
            # we rewrite the nuggets
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                if len(nug_matchings) == 0:
                    pass
                elif len(nug_matchings) == 2:
                    for (j, nug_matching) in enumerate(nug_matchings):
                        new_s_bnd = "s_bnd_{}_{}".format(i, j)
                        nugget.graph.add_node(new_s_bnd, "s_bnd_{}".format(i))
                        # nugget.graph.remove_edge(nug_matching["l"],
                        #                          nug_matching["b"])
                        nugget.graph.add_edge(nug_matching["l"], new_s_bnd)
                        nugget.graph.add_edge(new_s_bnd, nug_matching["b"])

                else:
                    raise ValueError("There must be 2 or 0 matching for the"
                                     " binding pattern in a nugget")

        # add input for free
        free_pattern = TypedDiGraph(self.graph.metamodel_)
        free_pattern.add_nodes_from([("f", "is_free"), ("l", "locus")])
        free_pattern.add_edges_from([("l", "f")])
        matchings = Rewriter.find_matching(self.graph, free_pattern)
        for (i, mat) in enumerate(matchings):
            # rewrite the action graph
            new_t_free = "t_free_{}".format(i)
            contact_map.add_node(new_t_free, "t_FREE")
            # contact_map.remove_edge(mat["l"], mat["b"])
            contact_map.add_edge(new_t_free,mat["l"])
            contact_map.add_edge(new_t_free, mat["f"])
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from([("f", mat["f"]), ("l", mat["l"])])
            nug_pattern.add_edges_from([("l", "f")])
            # we rewrite the nuggets
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    t_free = "t_free_{}_{}".format(i, j)
                    nugget.graph.add_node(t_free, new_t_free)
                    # nugget.graph.remove_edge(nug_matching["l"],
                    #                             nug_matching["f"])
                    nugget.graph.add_edge(t_free, nug_matching["l"])
                    nugget.graph.add_edge(t_free, nug_matching["f"])

        # add input for mod
        ag_pattern = TypedDiGraph(self.graph.metamodel_)
        ag_pattern.add_nodes_from([("m", "mod"), ("s", "state")])
        ag_pattern.add_edges_from([("m", "s")])
        matchings = Rewriter.find_matching(self.graph, ag_pattern)
        for (i, mat) in enumerate(matchings):
            # rewrite the action graph
            new_ag_node = "t_mod_{}".format(i)
            contact_map.add_node(new_ag_node, "t_MOD")
            # contact_map.remove_edge(mat["l"], mat["b"])
            contact_map.add_edge(new_ag_node, mat["s"])
            contact_map.add_edge(new_ag_node, mat["m"])
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from([("m", mat["m"]), ("s", mat["s"])])
            nug_pattern.add_edges_from([("m", "s")])
            # we rewrite the nuggets
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    new_nug_node = "t_mod_{}_{}".format(i, j)
                    nugget.graph.add_node(new_nug_node, new_ag_node)
                    # nugget.graph.remove_edge(nug_matching["l"],
                    #                             nug_matching["f"])
                    nugget.graph.add_edge(new_nug_node, nug_matching["s"])
                    nugget.graph.add_edge(new_nug_node, nug_matching["m"])

        # add input for brk
        brk_pattern = TypedDiGraph(self.graph.metamodel_)
        brk_pattern.add_nodes_from([("b", "brk"), ("l", "locus")])
        brk_pattern.add_edges_from([("l", "b")])
        matchings = Rewriter.find_matching(self.graph, brk_pattern)
        for (i, mat) in enumerate(matchings):
            # rewrite the action graph
            new_t_brk = "t_brk_{}".format(i)
            contact_map.add_node(new_t_brk, "t_BRK")
            # contact_map.remove_edge(mat["l"], mat["b"])
            contact_map.add_edge(new_t_brk, mat["l"])
            contact_map.add_edge(new_t_brk, mat["b"])
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from([("b", mat["b"]), ("l", mat["l"])])
            nug_pattern.add_edges_from([("l", "b")])
            # we rewrite the nuggets
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                if len(nug_matchings) == 0:
                    pass
                elif len(nug_matchings) == 2:
                    for (j, nug_matching) in enumerate(nug_matchings):
                        t_brk = "t_brk_{}_{}".format(i, j)
                        nugget.graph.add_node(t_brk, new_t_brk)
                        # nugget.graph.remove_edge(nug_matching["l"],
                        #                          nug_matching["b"])
                        nugget.graph.add_edge(nug_matching["l"], t_brk)
                        nugget.graph.add_edge(t_brk, nug_matching["b"])

                else:
                    raise ValueError("There must be 2 or 0 matching for the"
                                     " brk pattern in a nugget")

        # add input for is_bnd
        is_bnd_pattern = TypedDiGraph(self.graph.metamodel_)
        is_bnd_pattern.add_nodes_from([("b", "is_bnd"), ("l", "locus")])
        is_bnd_pattern.add_edges_from([("l", "b")])
        matchings = Rewriter.find_matching(self.graph, is_bnd_pattern)
        for (i, mat) in enumerate(matchings):
            # rewrite the action graph
            new_is_bnd = "is_bnd_{}".format(i)
            contact_map.add_node(new_is_bnd, "s_BND")
            # contact_map.remove_edge(mat["l"], mat["b"])
            contact_map.add_edge(mat["l"], new_is_bnd)
            contact_map.add_edge(new_is_bnd, mat["b"])
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from([("b", mat["b"]), ("l", mat["l"])])
            nug_pattern.add_edges_from([("l", "b")])
            # we rewrite the nuggets
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    is_bnd = "is_bnd_{}_{}".format(i, j)
                    nugget.graph.add_node(is_bnd, new_is_bnd)
                    # nugget.graph.remove_edge(nug_matching["l"],
                    #                          nug_matching["b"])
                    nugget.graph.add_edge(nug_matching["l"], is_bnd)
                    nugget.graph.add_edge(is_bnd, nug_matching["b"])

        ## move loci to agents
        # build the pattern for action graph
        region_pattern = TypedDiGraph(self.graph.metamodel_)
        region_pattern.add_nodes_from(
            [("r", "region"), ("l", "locus"), ("a", "agent")])
        region_pattern.add_edges_from(
            [("l", "r"), ("r", "a")])
        matchings = Rewriter.find_matching(self.graph, region_pattern)
        for mat in matchings:
            contact_map.add_edge(mat["l"], mat["a"])
            # build the pattern to look for in nuggets
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from(
                [("r", mat["r"]), ("l", mat["l"]), ("a", mat["a"])])
            nug_pattern.add_edges_from(
                [("l", "r"), ("r", "a")])
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for nug_matching in nug_matchings:
                    nugget.graph.add_edge(nug_matching["l"], nug_matching["a"])

        # SYN
        ag_pattern = TypedDiGraph(self.graph.metamodel_)
        ag_pattern.add_nodes_from(
            [("s", "syn"), ("a", "agent")])
        ag_pattern.add_edges_from(
            [("s", "a")])
        matchings = Rewriter.find_matching(self.graph, ag_pattern)
        for (i, mat) in enumerate(matchings):

            # modify action graph
            ag_node_name = "syn_{}_{}".format(mat["a"], i)
            contact_map.add_node(ag_node_name, "t_SD")
            contact_map.add_edge(ag_node_name, mat["s"])
            contact_map.add_edge(ag_node_name, mat["a"])

            # modify nuggets
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from(
                [("s", mat["s"]), ("a", mat["a"])])
            nug_pattern.add_edges_from(
                [("s", "a")])
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    node_name = "syn_{}_{}_{}".format(nug_matching["a"],
                                                        i, j)
                    nugget.graph.add_node(node_name, ag_node_name)
                    nugget.graph.add_edge(node_name, nug_matching["s"])
                    nugget.graph.add_edge(node_name, nug_matching["a"])

        # DEG
        ag_pattern = TypedDiGraph(self.graph.metamodel_)
        ag_pattern.add_nodes_from(
            [("d", "deg"), ("a", "agent")])
        ag_pattern.add_edges_from(
            [("d", "a")])
        matchings = Rewriter.find_matching(self.graph, ag_pattern)
        for (i, mat) in enumerate(matchings):

            # modify action graph
            ag_node_name = "deg_{}_{}".format(mat["a"], i)
            contact_map.add_node(ag_node_name, "s_SD")
            contact_map.add_edge(ag_node_name, mat["d"])
            contact_map.add_edge(mat["a"], ag_node_name)

            # modify nuggets
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from(
                [("d", mat["d"]), ("a", mat["a"])])
            nug_pattern.add_edges_from(
                [("d", "a")])
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    node_name = "deg_{}_{}_{}".format(nug_matching["a"],
                                                        i, j)
                    nugget.graph.add_node(node_name, ag_node_name)
                    nugget.graph.add_edge(node_name, nug_matching["d"])
                    nugget.graph.add_edge(nug_matching["a"], node_name)
        # create sites for the states
        # states associated to agents
        sites_pattern = TypedDiGraph(self.graph.metamodel_)
        sites_pattern.add_nodes_from(
            [("s", "state"), ("a", "agent")])
        sites_pattern.add_edges_from(
            [("s", "a")])
        matchings = Rewriter.find_matching(self.graph, sites_pattern)
        for (i, mat) in enumerate(matchings):

            # modify action graph
            new_node_name = "{}_state_{}".format(mat["a"], i)
            contact_map.add_node(new_node_name, "site")
            contact_map.add_edge(mat["s"], new_node_name)
            contact_map.add_edge(new_node_name, mat["a"])

            # modify nuggets
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from(
                [("s", mat["s"]), ("a", mat["a"])])
            nug_pattern.add_edges_from(
                [("s", "a")])
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    node_name = "{}_state_{}_{}".format(nug_matching["a"],
                                                        i, j)
                    nugget.graph.add_node(node_name, new_node_name)
                    nugget.graph.add_edge(nug_matching["s"], node_name)
                    nugget.graph.add_edge(node_name, nug_matching["a"])

        # states associated to regions
        sites_region_pattern = TypedDiGraph(self.graph.metamodel_)
        sites_region_pattern.add_nodes_from(
            [("s", "state"), ("r", "region"), ("a", "agent")])
        sites_region_pattern.add_edges_from(
            [("s", "r"), ("r", "a")])
        matchings = Rewriter.find_matching(self.graph, sites_region_pattern)
        for (i, mat) in enumerate(matchings):

            # modify action graph
            new_node_name = "{}_state_{}".format(mat["r"], i)
            contact_map.add_node(new_node_name, "site")
            contact_map.add_edge(mat["s"], new_node_name)
            contact_map.add_edge(new_node_name, mat["a"])

            # modify nuggets
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from(
                [("s", mat["s"]), ("a", mat["a"]), ("r", mat["r"])])
            nug_pattern.add_edges_from(
                [("s", "r"), ("r", "a")])
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    node_name = "{}_state_{}_{}".format(nug_matching["r"],
                                                        i, j)
                    nugget.graph.add_node(node_name, new_node_name)
                    nugget.graph.add_edge(nug_matching["s"], node_name)
                    nugget.graph.add_edge(node_name, nug_matching["a"])

        # states associated to residues
        sites_residue_pattern = TypedDiGraph(self.graph.metamodel_)
        sites_residue_pattern.add_nodes_from(
            [("s", "state"), ("r", "residue"), ("a", "agent")])
        sites_residue_pattern.add_edges_from(
            [("s", "r"), ("r", "a")])
        matchings = Rewriter.find_matching(self.graph, sites_residue_pattern)
        for (i, mat) in enumerate(matchings):

            # modify action graph
            new_node_name = "{}_state_{}".format(mat["r"], i)
            contact_map.add_node(new_node_name, "site")
            contact_map.add_edge(mat["s"], new_node_name)
            contact_map.add_edge(new_node_name, mat["a"])

            # modify nuggets
            nug_pattern = TypedDiGraph(self.graph)
            nug_pattern.add_nodes_from(
                [("s", mat["s"]), ("a", mat["a"]), ("r", mat["r"])])
            nug_pattern.add_edges_from(
                [("s", "r"), ("r", "a")])
            for nugget in contact_map_com.subCmds.values():
                nug_matchings = Rewriter.find_matching(nugget.graph,
                                                       nug_pattern)
                for (j, nug_matching) in enumerate(nug_matchings):
                    node_name = "{}_state_{}_{}".format(nug_matching["r"],
                                                        i, j)
                    nugget.graph.add_node(node_name, new_node_name)
                    nugget.graph.add_edge(nug_matching["s"], node_name)
                    nugget.graph.add_edge(node_name, nug_matching["a"])

        # change and remove old types and edges
        contact_map_com.graph = contact_map
        for nugget in contact_map_com.subCmds.values():
            nugget.parent = contact_map_com
            nugget.graph.parent = contact_map_com.graph
        to_delete = []
        for n in contact_map.nodes():
            type_of_n = contact_map.node[n].type_
            print(n, type_of_n)
            if type_of_n == "locus":
                contact_map.node[n].type_ = "site"
                print("locus", n, "-->", contact_map.node[n].type_)
            if type_of_n == "mod":
                contact_map.node[n].type_ = "MOD"
            if type_of_n == "bnd":
                contact_map.node[n].type_ = "BND"
            if type_of_n == "syn" or type_of_n == "deg":
                contact_map.node[n].type_ = "SYN/DEG"
            if type_of_n == "brk":
                contact_map.node[n].type_ = "BRK"
            if type_of_n == "is_free":
                contact_map.node[n].type_ = "is_FREE"
            if type_of_n == "is_bnd":
                contact_map.node[n].type_ = "is_BND"
            if type_of_n == "region" or type_of_n == "residue":
                to_delete.append(n)
        for n in to_delete:
            contact_map_com._do_rm_node_force_not_catched(n)
        to_delete = []
        for (n1, n2) in contact_map.edges():
            tn1 = contact_map.node[n1].type_
            tn2 = contact_map.node[n2].type_
            if ((tn1, tn2) == ("site", "BND") or
               (tn1, tn2) == ("site", "BRK") or
               (tn1, tn2) == ("site", "is_BND") or
               (tn1, tn2) == ("state", "agent") or
               (tn1, tn2) == ("MOD", "site") or
               (tn1, tn2) == ("MOD", "state") or
               (tn1, tn2) == ("SYN/DEG", "agent") or
               (tn1, tn2) == ("site", "is_FREE")):
                to_delete.append((n1, n2))

        for (n1, n2) in to_delete:
            contact_map_com._do_rm_edge_uncatched(n1, n2, force=True)
        print("same:", contact_map is contact_map_com.graph)
        print(contact_map_com.graph)
        return contact_map_com

    def postloop(self):
        print()

    def preloop(self):
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python iregraph.py \"/path/to/imageViewer\"")
    elif not os.path.isfile(sys.argv[1]):
        print("png viewer not found at location", sys.argv[1])
    else:
        top = MyCmd("/", "/", None, sys.argv[1])
        top.do_cat("")
        top.cmdloop("Interactive graph manipulation")
