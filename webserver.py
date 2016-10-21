from flask import Flask, Response, request
from iRegraph import MyCmd
from flask_cors import CORS, cross_origin
import json


class MyFlask(Flask):
    def __init__(self,name):
        super().__init__(name)
        self.cmd = MyCmd("/","/",None,None)
        self.cmd.graph = None
    
app = MyFlask(__name__)
#app.url_map.strict_slashes = True
app.config['DEBUG'] = True
CORS(app)
#app = Flask(__name__)

def parse_path(path_to_graph):
    l = [s for s in path_to_graph.split("/") if s and not s.isspace()]        
    print(l)
    if l == []:
        graph_name = None
        parent_cmd = app.cmd
    else :
        graph_name = l[-1]
        parent_cmd =  app.cmd.subCmd(l[:-1])
    return (parent_cmd, graph_name)

def get_cmd(path):
    # if path.isspace():
    #     return(app.cmd)
    path_list = [s for s in path.split("/") if s and not s.isspace()]        
    return(app.cmd.subCmd(path_list))


@app.route("/hierarchy/", methods=["POST"])
@app.route("/hierarchy/<path:path_to_graph>", methods=["POST"])
def import_sub_hierachy(path_to_graph=""):
    try:
        (parent_cmd, graph_name) = parse_path(path_to_graph)
    except KeyError as e:
        return("the path is not valid", 404)
    if graph_name is None:
        return("the empty path is not valid" ,404)
    sub_hierarchy = request.json
    top_graph_name = sub_hierarchy["name"]
    if top_graph_name != graph_name :
        return("the name of the top graph must be the same as the url" ,404)
    try:
        parent_cmd.add_subHierarchy(sub_hierarchy)
        return("Hierarchy added successfully",200)
    except (ValueError, KeyError) as e:
        return (str(e), 404)

@app.route("/hierarchy/", methods=["PUT"])
@app.route("/hierarchy/<path:path_to_graph>", methods=["PUT"])
def merge_hierachy(path_to_graph=""):
    try:
        (_,graph_name) = parse_path(path_to_graph)
        cmd = get_cmd(path_to_graph)
        hierarchy = request.json
        top_graph_name = hierarchy["name"]
        if graph_name is None and top_graph_name != "/":
            return ("the name of the top graph must be '/'",404)
        if graph_name is not None and top_graph_name != graph_name :
            return ("the name of the top graph must be the same as the url" ,404)
        if cmd.merge_conflict(hierarchy):
            return ("some different graphs have the same name", 404)    
        cmd.merge_hierarchy(hierarchy)
        return("merge was succesfull",200)
    except (ValueError, KeyError) as e:
        return (str(e), 404)

@app.route("/hierarchy/", methods=["GET"])
@app.route("/hierarchy/<path:path_to_graph>", methods=["GET"])
def get_hierarchy(path_to_graph=""):
    include_rules = request.args.get("rules")
    include_graphs = request.args.get("include_graphs")
    if include_graphs:
        return(get_graph_hierarchy(path_to_graph))
    else:
        return(get_graph_hierarchy_only_names(path_to_graph))

@app.route("/hierarchy/", methods=["DELETE"])
@app.route("/hierarchy/<path:path_to_graph>", methods=["DELETE"])
def delete_hierarchy(path_to_graph=""):
    try : 
        (parent_cmd,graph_name) = parse_path(path_to_graph)
        if graph_name is None: 
            parent_cmd.subCmds={}
            parent_cmd.subRules={}
            return("hierarchy deleted", 200)
        else:
            del parent_cmd.subCmds[graph_name]
            return("hierarchy deleted", 200)
    except KeyError as e:
        return("Path not valid", 404)    

@app.route("/graph/", methods=["DELETE"])
@app.route("/graph/<path:path_to_graph>/", methods=["DELETE"])
def delete_graph(path_to_graph=""):
    (parent_cmd,graph_name) = parse_path(path_to_graph)
    if graph_name is None:
        return("The empty path does not contain a graph",404)
    try:
         parent_cmd.deleteSubCmd(graph_name)
         return("graph deleted",200)    
    except ValueError as e:
        return(str(e),409)
    except KeyError as e:
        return(str(e),404)     

@app.route("/graph/", methods=["GET"])
@app.route("/graph/<path:path_to_graph>", methods=["GET"])
def dispach_get_graph(path_to_graph=""):
    return(get_graph(path_to_graph))

def get_graph(path_to_graph):
    try:
        (_,graph_name)=parse_path(path_to_graph)
        if graph_name is None:
            return("the empty path does not contain a top graph", 404)
        cmd = get_cmd(path_to_graph)
        resp = Response(response=json.dumps(cmd.graph.to_json_like()),
                        status=200, 
                        mimetype="application/json")        
        return (resp)
    except KeyError as e:
        return(Response(response="graph not found : "+str(e),status=404))

def get_graph_hierarchy(path_to_graph):
    try:
        cmd = get_cmd(path_to_graph)
        resp = Response(response=json.dumps(cmd.hierarchy_to_json()),
                        status=210, \
                        mimetype="application/json")        
        return (resp)
    except KeyError as e:
        return(Response(response="graph not found : "+str(e),status=404))
        
def get_graph_hierarchy_only_names(path_to_graph):
    try:
        cmd = get_cmd(path_to_graph)
        resp = Response(response=json.dumps(cmd.hierarchy_of_names()),
                        status=211, \
                        mimetype="application/json")        
        return (resp)
    except KeyError as e:
        return(Response(response="graph not found : "+str(e),status=404))
        

@app.route("/rule/", methods=["POST"])
@app.route("/rule/<path:path_to_graph>", methods=["POST"])
def create_rule(path_to_graph=""):
    path_list = path_to_graph.split("/") 
    parent_path = path_list[:-1]
    new_name = path_list[-1]
    try :
        (parent_com,rule_name)=parse_path(path_to_graph)
    except KeyError as e:
        return(str(e),404)        
        
    if rule_name is None:
        return ("the empty path is not valid to create a rule", 404)
    pattern_name = request.args.get("pattern_name")
    if not pattern_name:
        return("the pattern_name argument is required", 404)
    try : 
        parent_cmd = app.cmd.subCmd(parent_path) 
        if not parent_cmd.valid_new_name(new_name):
            return("Graph or rule already exists with this name", 409)
        elif pattern_name not in parent_cmd.subCmds.keys():
            return("The pattern graph does not exist", 409)
        else:    
            parent_cmd._do_new_rule(new_name,pattern_name)
            return("rule created", 200)
    except KeyError as e:
        return(str(e),404)        

@app.route("/graph/", methods=["POST"])
@app.route("/graph/<path:path_to_graph>", methods=["POST"])
def create_graph(path_to_graph=""):
   try: 
       (parent_cmd, graph_name) = parse_path(path_to_graph)
       if graph_name is None:
           return("the empty path is not valid for graph creation",404)
           #parent_cmd = app.cmd.subCmd(parent_path) 
       if not parent_cmd.valid_new_name(graph_name):
           return("Graph or rule already exists with this name",409)
       else : 
               parent_cmd._do_mkdir(graph_name)
               return("Graph created",200) 
   except KeyError as e : 
       return(str(e),404)


@app.route("/graph/apply/", methods=["POST"])
@app.route("/graph/apply/<path:path_to_graph>", methods=["POST"])
def apply_rule(path_to_graph=""):
    path_list = path_to_graph.split("/") 
    parent_path = path_list[:-1]
    new_name = path_list[-1]
    rule_name = request.args.get("rule_name")
    target_graph = request.args.get("target_graph")
    try :
        #matching = json.load(request.form["matching morphism"])
        #matching = json.load(request.data)
        matching = {d["left"]:d["right"] for d in request.json}
        print(matching)
    except KeyError as e:
        return("the matching argument is necessary", 404)    
    if not (rule_name and target_graph):
        return("the rule_name and target_graph arguments are necessary", 404)
    try : 
        parent_cmd = app.cmd.subCmd(parent_path) 
        if not parent_cmd.valid_new_name(new_name):
            return("Graph or rule already exists with this name", 409)
        elif rule_name not in parent_cmd.subRules.keys():
            return("The rule does not exist", 409)
        elif target_graph not in parent_cmd.subCmds.keys():
            return("The target_graph does not exist", 409)
        else:    
            parent_cmd._do_apply_rule_no_catching(rule_name, target_graph, new_name, matching)
            return("new graph created", 200)
            
    except (KeyError, ValueError) as e:
        return(str(e),404)        
        
        
def get_command(path_to_graph, callback):
    try :
        (parent_cmd, child_name) = parse_path(path_to_graph)
        if child_name in parent_cmd.subCmds.keys():
            command = parent_cmd.subCmds[child_name] 
            return(callback(command))
        elif child_name in parent_cmd.subRules.keys():
            command = parent_cmd.subRules[child_name]
            return("rules update not supported yet", 404)
        else :
            raise(KeyError)    
    except KeyError:
        return("Graph not found", 404)

@app.route("/graph/add_node/", methods=["PUT"])
@app.route("/graph/add_node/<path:path_to_graph>", methods=["PUT"])
def add_node_graph(path_to_graph=""):
    return(get_command(path_to_graph, add_node))

@app.route("/graph/add_edge/", methods=["PUT"])
@app.route("/graph/add_edge/<path:path_to_graph>", methods=["PUT"])
def add_edge_graph(path_to_graph=""):
    return(get_command(path_to_graph, add_edge))

@app.route("/graph/rm_node/", methods=["PUT"])
@app.route("/graph/rm_node/<path:path_to_graph>", methods=["PUT"])
def rm_node_graph(path_to_graph=""):
    return(get_command(path_to_graph, rm_node))


@app.route("/graph/merge_node/", methods=["PUT"])
@app.route("/graph/merge_node/<path:path_to_graph>", methods=["PUT"])
def merge_node_graph(path_to_graph=""):
    return(get_command(path_to_graph, merge_node))


@app.route("/graph/clone_node/", methods=["PUT"])
@app.route("/graph/clone_node/<path:path_to_graph>", methods=["PUT"])
def clone_node_graph(path_to_graph=""):
    return(get_command(path_to_graph, clone_node))


@app.route("/graph/rm_edge/", methods=["PUT"])
@app.route("/graph/rm_edge/<path:path_to_graph>", methods=["PUT"])
def rm_edge_graph(path_to_graph=""):
    return(get_command(path_to_graph, rm_edge))


@app.route("/rule/add_node/", methods=["PUT"])
@app.route("/rule/add_node/<path:path_to_rule>", methods=["PUT"])
def add_node_rule(path_to_rule=""):
    return(get_command(path_to_rule, add_node))

@app.route("/rule/add_edge/", methods=["PUT"])
@app.route("/rule/add_edge/<path:path_to_rule>", methods=["PUT"])
def add_edge_rule(path_to_rule=""):
    return(get_command(path_to_rule, add_edge))

@app.route("/rule/rm_node/", methods=["PUT"])
@app.route("/rule/rm_node/<path:path_to_rule>", methods=["PUT"])
def rm_node_rule(path_to_rule=""):
    return(get_command(path_to_rule, rm_node))


@app.route("/rule/merge_node/", methods=["PUT"])
@app.route("/rule/merge_node/<path:path_to_rule>", methods=["PUT"])
def merge_node_rule(path_to_rule=""):
    return(get_command(path_to_rule, merge_node))


@app.route("/rule/clone_node/", methods=["PUT"])
@app.route("/rule/clone_node/<path:path_to_rule>", methods=["PUT"])
def clone_node_rule(path_to_rule=""):
    return(get_command(path_to_rule, clone_node))


@app.route("/rule/rm_edge/", methods=["PUT"])
@app.route("/rule/rm_edge/<path:path_to_rule>", methods=["PUT"])
def rm_edge_rule(path_to_rule=""):
    return(get_command(path_to_rule, rm_edge))

def add_node(command):
    node_id = request.args.get("node_id")
    if not node_id:
        return("the node_id argument is necessary")
    if command.main_graph().metamodel_ == None :
        node_type = None
    else : 
        node_type = request.args.get("node_type")
        if node_type == None:
            return("this graph is typed, the node_type argument is necessary", 412)
    if node_id in command.main_graph().nodes():
        return(Response("the node already exists", 412))
    try: 
        command._do_add_not_catched(node_id, node_type) 
        return("node added", 200)
    except ValueError as e:
        return("error: "+str(e), 412)

def add_edge(command):
    source_node = request.args.get("source_node")
    target_node = request.args.get("target_node")
    if not (source_node and target_node):
        return("The source_node and target_node arguments are necessary",412)
    if command.main_graph().exists_edge(source_node, target_node):
        return("The edge already exists", 412)
    try:    
        command._do_ln_not_catched(source_node, target_node)     
        return("edge added", 200)
    except ValueError as e:
        return("error: "+str(e), 412)

def rm_node(command):
    node_id = request.args.get("node_id")
    force_flag = request.args.get("force") == "true"
    if not node_id:
        return("the node_id argument is necessary")
    if not force_flag:    
        try:
            command._do_rm_node_not_catched(node_id)    
            return("node deleted", 200)
        except ValueError as e:
            return("node was not deleted, set the force argument to true to delete all nodes of this type from subgraphs", 412)    
    else:
        try:
            command._do_rm_node_force_not_catched(node_id)    
            return("node deleted", 200)
        except ValueError as e:
            return("error "+str(e), 412)    
            
def merge_nodes(command):
    node1 = request.args.get("node1")            
    node2 = request.args.get("node2")            
    new_node_id = request.args.get("new_node_id")             
    if not (node1 and node2 and new_node_id):
        return("the arguments node1, node2 and new_node_id are necessary",412)
    if node1 == node2 :
        return("You cannot merge a node with it self", 412)
    if node1 not in command.main_graph().nodes():
        return(str(node1)+" is not a node of the graph", 412)
    if node2 not in command.main_graph().nodes():
        return(str(node2)+" is not a node of the graph", 412)
    force_flag = request.args.get("force") == "true"
    if force_flag:
        try: 
            command._do_merge_nodes_force_not_catched(node1, node2, new_node_id)
            return("nodes merged", 200)
        except ValueError as e:
            return(str(e), 412)    
    else:
        try:
            command._do_merge_nodes_not_catched(node1, node2, new_node_id)
            return("nodes merged", 200)
        except ValueError as e:
            if  "image not in target graph" in str(e) :
                return("nodes were not merged, the force argument must be set", 412)
            else :
                return(str(e), 412)    
    
    
def clone_node(command):
    node_id = request.args.get("node_id")
    new_node_id = request.args.get("new_node_id")             
    if not (node_id and new_node_id):
        return("the node_id and new_node_id arguments are necessary", 412)
    if node_id not in command.graph.nodes():
        return(str(node_id)+" is not a node of the graph", 412)
    if new_node_id in command.graph.nodes():
        return(str(new_node_id)+" is already a node of the graph", 412)
    try:
        command._do_clone_node_not_catched(node_id,new_node_id)    
        return("node cloned", 200)
    except ValueError as e:
        return(str(e), 412)    

def rm_edge(command):
    source_node = request.args.get("source_node")
    target_node = request.args.get("target_node")
    if not (source_node and target_node):
        return("The source_node and target_node arguments are necessary", 412)
    force_flag = request.args.get("force") == "true"
    try : 
        command._do_rm_edge_uncatched(source_node, target_node, force_flag)
        return("Edge removed", 200)
    except ValueError as e:
        error_message = str(e) if force_flag else str(e)+", use the force flag if there are some sub edges"    
        return(error_message, 412)
        
if __name__ == "__main__":
    app.run()
    
    