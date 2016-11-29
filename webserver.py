from flask import Flask, Response, request, send_from_directory, redirect, url_for
from iRegraph import MyCmd
from flask_cors import CORS, cross_origin
from flex.loading.schema.paths.path_item.operation.responses.single.schema\
    import schema_validator
import json
import flex
from metamodels import (base_metamodel, metamodel_kappa)
from exporters import KappaExporter
import os


class MyFlask(Flask):

    def __init__(self, name):
        super().__init__(name, static_url_path="")
        self.cmd = MyCmd("/", "/", None, None)
        self.cmd.graph = None

def include_kappa_metamodel(app, base_name, metamodel_name):
    try:
        app.cmd._do_mkdir(base_name)
        app.cmd.subCmds[base_name].graph = base_metamodel
        app.cmd.subCmds[base_name]._do_mkdir(metamodel_name)
        app.cmd.subCmds[base_name].subCmds[metamodel_name].graph = metamodel_kappa
    except KeyError as e:
        return (str(e), 404)

app = MyFlask(__name__)
app.config['DEBUG'] = True
CORS(app)
json_schema_context = flex.load('iRegraph_api.yaml')
base_name = "kappa_base_metamodel"
metamodel_name = "kappa_metamodel"
include_kappa_metamodel(app, base_name, metamodel_name)



def parse_path(path_to_graph):
    l = [s for s in path_to_graph.split("/") if s and not s.isspace()]
    if l == []:
        graph_name = None
        parent_cmd = app.cmd
    else:
        graph_name = l[-1]
        parent_cmd = app.cmd.subCmd(l[:-1])
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
        return("the empty path is not valid", 404)
    sub_hierarchy = request.json
    try:
        schema = schema_validator({'$ref': '#/definitions/GraphHierarchy'},
                                  context=json_schema_context)
        flex.core.validate(schema, sub_hierarchy, context=json_schema_context)
    except ValueError as e:
        return(str(e), 404)
    top_graph_name = sub_hierarchy["name"]
    if top_graph_name != graph_name:
        return("the name of the top graph must be the same as the url", 404)
    try:
        parent_cmd.add_subHierarchy(sub_hierarchy)
        return("Hierarchy added successfully", 200)
    except (ValueError, KeyError) as e:
        return (str(e), 404)


@app.route("/hierarchy/", methods=["PUT"])
@app.route("/hierarchy/<path:path_to_graph>", methods=["PUT"])
def merge_hierachy(path_to_graph=""):
    try:
        (_, graph_name) = parse_path(path_to_graph)
        cmd = get_cmd(path_to_graph)
        hierarchy = request.json
        top_graph_name = hierarchy["name"]
        if graph_name is None and top_graph_name != "/":
            return ("the name of the top graph must be '/'", 404)
        if graph_name is not None and top_graph_name != graph_name:
            return ("the name of the top graph must be the same as the url",
                    404)
        if cmd.merge_conflict(hierarchy):
            return ("some different graphs have the same name", 404)
        cmd.merge_hierarchy(hierarchy)
        return("merge was succesfull", 200)
    except (ValueError, KeyError) as e:
        return (str(e), 404)


@app.route("/hierarchy/", methods=["GET"])
@app.route("/hierarchy/<path:path_to_graph>", methods=["GET"])
def get_hierarchy(path_to_graph=""):
    include_rules = request.args.get("rules") == "true"
    include_graphs = request.args.get("include_graphs")
    if include_graphs == "true":
        return get_graph_hierarchy(path_to_graph, include_rules)
    else:
        return get_graph_hierarchy_only_names(path_to_graph, include_rules)


@app.route("/hierarchy/", methods=["DELETE"])
@app.route("/hierarchy/<path:path_to_graph>", methods=["DELETE"])
def delete_hierarchy(path_to_graph=""):
    try:
        (parent_cmd, graph_name) = parse_path(path_to_graph)
        if graph_name is None:
            parent_cmd.subCmds = {}
            parent_cmd.subRules = {}
            return("hierarchy deleted", 200)
        else:
            del parent_cmd.subCmds[graph_name]
            return("hierarchy deleted", 200)
    except KeyError as e:
        return("Path not valid", 404)


@app.route("/graph/", methods=["DELETE"])
@app.route("/graph/<path:path_to_graph>/", methods=["DELETE"])
def delete_graph(path_to_graph=""):
    (parent_cmd, graph_name) = parse_path(path_to_graph)
    if graph_name is None:
        return("The empty path does not contain a graph", 404)
    try:
        parent_cmd.deleteSubCmd(graph_name)
        return("graph deleted", 200)
    except ValueError as e:
        return(str(e), 409)
    except KeyError as e:
        return(str(e), 404)


@app.route("/graph/", methods=["GET"])
@app.route("/graph/<path:path_to_graph>", methods=["GET"])
def dispach_get_graph(path_to_graph=""):
    return(get_graph(path_to_graph))


def get_graph(path_to_graph):
    try:
        (_, graph_name) = parse_path(path_to_graph)
        if graph_name is None:
            return("the empty path does not contain a top graph", 404)
        cmd = get_cmd(path_to_graph)
        resp = Response(response=json.dumps(cmd.graph.to_json_like()),
                        status=200,
                        mimetype="application/json")
        return (resp)
    except KeyError as e:
        return(Response(response="graph not found : " + str(e), status=404))


def get_graph_hierarchy(path_to_graph, include_rules):
    try:
        cmd = get_cmd(path_to_graph)
        resp = Response(
                 response=json.dumps(cmd.hierarchy_to_json(include_rules)),
                 status=213 if include_rules else 210,
                 mimetype="application/json")
        return (resp)
    except KeyError as e:
        return(Response(response="graph not found : " + str(e), status=404))


def get_graph_hierarchy_only_names(path_to_graph, include_rules):
    try:
        cmd = get_cmd(path_to_graph)
        resp = Response(
                response=json.dumps(cmd.hierarchy_of_names(include_rules)),
                status=212 if include_rules else 211,
                mimetype="application/json")
        return (resp)
    except KeyError as e:
        return(Response(response="graph not found : " + str(e), status=404))


@app.route("/rule/", methods=["POST"])
@app.route("/rule/<path:path_to_graph>", methods=["POST"])
def create_rule(path_to_graph=""):
    try:
        (parent_cmd, rule_name) = parse_path(path_to_graph)
        if rule_name is None:
            return("the empty path is not valid for graph creation", 404)
        if not parent_cmd.valid_new_name(rule_name):
            return("Graph or rule already exists with this name", 409)
        pattern_name = request.args.get("pattern_name")
        if not pattern_name:
            return("the pattern_name argument is required", 404)
        else:
            parent_cmd._do_new_rule(rule_name, pattern_name)
            return("rule created", 200)
    except KeyError as e:
        return(str(e), 404)
# def create_rule(path_to_graph=""):
#     path_list = path_to_graph.split("/")
#     parent_path = path_list[:-1]
#     new_name = path_list[-1]
#     try :
#         (parent_com,rule_name)=parse_path(path_to_graph)
#     except KeyError as e:
#         return(str(e),404)

#     if rule_name is None:
#         return ("the empty path is not valid to create a rule", 404)
#     pattern_name = request.args.get("pattern_name")
#     if not pattern_name:
#         return("the pattern_name argument is required", 404)
#     try :
#         parent_cmd = app.cmd.subCmd(parent_path)
#         if not parent_cmd.valid_new_name(new_name):
#             return("Graph or rule already exists with this name", 409)
#         elif pattern_name not in parent_cmd.subCmds.keys():
#             return("The pattern graph does not exist", 409)
#         else:
#             parent_cmd._do_new_rule(new_name,pattern_name)
#             return("rule created", 200)
#     except KeyError as e:
#         return(str(e),404)


@app.route("/graph/", methods=["POST"])
@app.route("/graph/<path:path_to_graph>", methods=["POST"])
def create_graph(path_to_graph=""):
    try:
        (parent_cmd, graph_name) = parse_path(path_to_graph)
        if graph_name is None:
            return("the empty path is not valid for graph creation", 404)
        if not parent_cmd.valid_new_name(graph_name):
            return("Graph or rule already exists with this name", 409)
        else:
            parent_cmd._do_mkdir(graph_name)
            return("Graph created", 200)
    except KeyError as e:
        return(str(e), 404)


@app.route("/graph/matchings/", methods=["GET"])
@app.route("/graph/matchings/<path:path_to_graph>", methods=["GET"])
def get_matchings(path_to_graph=""):
    try:
        (parent_cmd, graph_name) = parse_path(path_to_graph)
        if graph_name is None:
            return("the empty path does not contain a top graph", 404)
        rule_name = request.args.get("rule_name")
        if not rule_name:
            return("the rule_name argument is missing", 404)
        if rule_name not in parent_cmd.subRules.keys():
            return("the rule does not exists", 404)
        if graph_name not in parent_cmd.subCmds.keys():
            return("the graph does not exists", 404)

        resp = Response(
                 response=json.dumps(parent_cmd.get_matchings(rule_name,
                                                              graph_name)),
                 status=200,
                 mimetype="application/json")
        return resp
    except KeyError as e:
        return Response(response="graph not found : " + str(e), status=404)


@app.route("/graph/apply/", methods=["POST"])
@app.route("/graph/apply/<path:path_to_graph>", methods=["POST"])
def apply_rule(path_to_graph=""):
    rule_name = request.args.get("rule_name")
    target_graph = request.args.get("target_graph")
    try:
        matching = {d["left"]: d["right"] for d in request.json}
    except KeyError as e:
        return("the matching argument is necessary", 404)
    if not (rule_name and target_graph):
        return("the rule_name and target_graph arguments are necessary", 404)
    try:
        (parent_cmd, new_name) = parse_path(path_to_graph)
        if not parent_cmd.valid_new_name(new_name):
            return("Graph or rule already exists with this name", 409)
        elif rule_name not in parent_cmd.subRules.keys():
            return("The rule does not exist", 409)
        elif target_graph not in parent_cmd.subCmds.keys():
            return("The target_graph does not exist", 409)
        else:
            parent_cmd._do_apply_rule_no_catching(
                rule_name, target_graph, new_name, matching)
            return("new graph created", 200)

    except (KeyError, ValueError) as e:
        return(str(e), 404)


def get_command(path_to_graph, callback):
    try:
        (parent_cmd, child_name) = parse_path(path_to_graph)
        if child_name in parent_cmd.subCmds.keys():
            command = parent_cmd.subCmds[child_name]
            return callback(command)
        elif child_name in parent_cmd.subRules.keys():
            command = parent_cmd.subRules[child_name]
            return callback(command)
            # return("rules update not supported yet", 404)
        else:
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
    return(get_command(path_to_graph, merge_nodes))


@app.route("/graph/clone_node/", methods=["PUT"])
@app.route("/graph/clone_node/<path:path_to_graph>", methods=["PUT"])
def clone_node_graph(path_to_graph=""):
    return(get_command(path_to_graph, clone_node))


@app.route("/graph/rm_edge/", methods=["PUT"])
@app.route("/graph/rm_edge/<path:path_to_graph>", methods=["PUT"])
def rm_edge_graph(path_to_graph=""):
    return(get_command(path_to_graph, rm_edge))


@app.route("/graph/add_attr/", methods=["PUT"])
@app.route("/graph/add_attr/<path:path_to_graph>", methods=["PUT"])
def add_attr_graph(path_to_graph=""):
    return(get_command(path_to_graph, add_attr))


@app.route("/graph/update_attr/", methods=["PUT"])
@app.route("/graph/update_attr/<path:path_to_graph>", methods=["PUT"])
def update_attr_graph(path_to_graph=""):
    return(get_command(path_to_graph, update_attr))


@app.route("/graph/rm_attr/", methods=["PUT"])
@app.route("/graph/rm_attr/<path:path_to_graph>", methods=["PUT"])
def rm_attr_graph(path_to_graph=""):
    return(get_command(path_to_graph, remove_attr))


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
    return(get_command(path_to_rule, merge_nodes))


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
    if command.main_graph().metamodel_ is None:
        node_type = None
    else:
        node_type = request.args.get("node_type")
        if node_type is None:
            return("this graph is typed, the node_type argument is necessary",
                   412)
    if node_id in command.main_graph().nodes():
        return(Response("the node already exists", 412))
    try:
        command._do_add_not_catched(node_id, node_type)
        return("node added", 200)
    except ValueError as e:
        return("error: " + str(e), 412)


def modify_attr(f):
    node_id = request.args.get("node_id")
    if not node_id:
        return("the node_id argument is necessary")
    try:
        attributes = request.json
        f(node_id, attributes)
        return("attributes modified", 200)
    except ValueError as e:
        return("error: " + str(e), 412)


def update_attr(command):
    return modify_attr(command.graph.update_node_attrs)


def remove_attr(command):
    return modify_attr(command.graph.remove_node_attrs)


def add_attr(command):
    return modify_attr(command.graph.add_node_attrs)


def add_edge(command):
    source_node = request.args.get("source_node")
    target_node = request.args.get("target_node")
    if not (source_node and target_node):
        return("The source_node and target_node arguments are necessary", 412)
    if command.main_graph().exists_edge(source_node, target_node):
        return("The edge already exists", 412)
    try:
        command._do_ln_not_catched(source_node, target_node)
        return("edge added", 200)
    except ValueError as e:
        return("error: " + str(e), 412)


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
            return("node was not deleted, set the force argument to true\
                    to delete all nodes of this type from subgraphs", 412)
    else:
        try:
            command._do_rm_node_force_not_catched(node_id)
            return("node deleted", 200)
        except ValueError as e:
            return("error " + str(e), 412)


def merge_nodes(command):
    node1 = request.args.get("node1")
    node2 = request.args.get("node2")
    new_node_id = request.args.get("new_node_id")
    if not (node1 and node2 and new_node_id):
        return("the arguments node1, node2 and new_node_id are necessary", 412)
    if node1 == node2:
        return("You cannot merge a node with it self", 412)
    if node1 not in command.main_graph().nodes():
        return(str(node1) + " is not a node of the graph", 412)
    if node2 not in command.main_graph().nodes():
        return(str(node2) + " is not a node of the graph", 412)
    force_flag = request.args.get("force") == "true"
    if force_flag:
        try:
            command._do_merge_nodes_force_not_catched(
                node1, node2, new_node_id)
            return("nodes merged", 200)
        except ValueError as e:
            return(str(e), 412)
    else:
        try:
            command._do_merge_nodes_not_catched(node1, node2, new_node_id)
            return("nodes merged", 200)
        except ValueError as e:
            if "image not in target graph" in str(e):
                return("nodes were not merged, the force argument must be set",
                       412)
            else:
                return(str(e), 412)


def clone_node(command):
    node_id = request.args.get("node_id")
    new_node_id = request.args.get("new_node_id")
    if not (node_id and new_node_id):
        return("the node_id and new_node_id arguments are necessary", 412)
    if node_id not in command.main_graph().nodes():
        return(str(node_id) + " is not a node of the graph", 412)
    if new_node_id in command.main_graph().nodes():
        return(str(new_node_id) + " is already a node of the graph", 412)
    try:
        command._do_clone_node_not_catched(node_id, new_node_id)
        return("node cloned", 200)
    except ValueError as e:
        return(str(e), 412)


def rm_edge(command):
    source_node = request.args.get("source_node")
    target_node = request.args.get("target_node")
    if not (source_node and target_node):
        return("The source_node and target_node arguments are necessary", 412)
    force_flag = request.args.get("force") == "true"
    try:
        command._do_rm_edge_uncatched(source_node, target_node, force_flag)
        return("Edge removed", 200)
    except ValueError as e:
        error_message = str(e) if force_flag else str(
            e) + ", use the force flag if there are some sub edges"
        return(error_message, 412)


@app.route("/graph/add_constraint/", methods=["PUT"])
@app.route("/graph/add_constraint/<path:path_to_graph>", methods=["PUT"])
def add_constraint(path_to_graph=""):
    input_or_output = request.args.get("input_or_output")
    node_id = request.args.get("node_id")
    constraint_node = request.args.get("constraint_node")
    le_or_ge = request.args.get("le_or_ge")
    bound = request.args.get("bound")
    if not (input_or_output and node_id and
            constraint_node and le_or_ge and bound):
        return("argument missing", 404)
    try:
        int_bound = int(bound)
    except ValueError:
        return("could not convert bound to integer", 404)

    if le_or_ge == "le":
        def condition(x):
            return x <= int_bound
        viewableCondition = constraint_node + " <= " + bound
    elif le_or_ge == "ge":
        def condition(x):
            return x >= int_bound
        viewableCondition = constraint_node + " >= " + bound
    else:
        return ("uncorrect value for argument ge_or_le", 404)

    if input_or_output == "input":
        def add_constraint_to(command):
            try:
                command.addInputConstraint(
                    node_id, constraint_node, condition, viewableCondition)
                return ("constraint added", 200)
            except ValueError as e:
                return(str(e), 412)
    elif input_or_output == "output":
        def add_constraint_to(command):
            try:
                command.addOutputConstraint(
                    node_id, constraint_node, condition, viewableCondition)
                return("constraint added", 200)
            except ValueError as e:
                return (str(e), 412)
    else:
        return ("uncorrect value for argument input_or_output", 404)

    return(get_command(path_to_graph, add_constraint_to))


@app.route("/graph/delete_constraint/", methods=["PUT"])
@app.route("/graph/delete_constraint/<path:path_to_graph>", methods=["PUT"])
def delete_constraint(path_to_graph=""):
    input_or_output = request.args.get("input_or_output")
    node_id = request.args.get("node_id")
    constraint_node = request.args.get("constraint_node")
    le_or_ge = request.args.get("le_or_ge")
    bound = request.args.get("bound")
    if not (input_or_output and node_id and
            constraint_node and le_or_ge and bound):
        return("argument missing", 404)
    try:
        int_bound = int(bound)
    except ValueError:
        return("could not convert bound to integer", 404)

    if le_or_ge == "le":
        viewableCondition = constraint_node + " <= " + bound
    elif le_or_ge == "ge":
        viewableCondition = constraint_node + " >= " + bound
    else:
        return ("uncorrect value for argument ge_or_le", 404)

    if input_or_output == "input":
        def delete_constraint_to(command):
            try:
                command.deleteInputConstraint(node_id, viewableCondition)
                return ("constraint deleted", 200)
            except ValueError as e:
                return(str(e), 412)
    elif input_or_output == "output":
        def delete_constraint_to(command):
            try:
                command.deleteOutputConstraint(node_id, viewableCondition)
                return("constraint deleted", 200)
            except ValueError as e:
                return (str(e), 412)
    else:
        return ("uncorrect value for argument input_or_output", 404)

    return(get_command(path_to_graph, delete_constraint_to))


@app.route("/graph/validate_constraints/", methods=["PUT"])
@app.route("/graph/validate_constraints/<path:path_to_graph>", methods=["PUT"])
def validate_constraint(path_to_graph=""):
    def check_constraint(command):
        wrong_nodes = command.graph.checkConstraints()
        if wrong_nodes:
            return (json.dumps(wrong_nodes), 412)
        else:
            return("graph validated", 200)
    return(get_command(path_to_graph, check_constraint))


@app.route("/graph/rename_graph/", methods=["PUT"])
@app.route("/graph/rename_graph/<path:path_to_graph>", methods=["PUT"])
def rename_graph(path_to_graph=""):
    return rename(path_to_graph)


@app.route("/rule/rename_rule/", methods=["PUT"])
@app.route("/rule/rename_rule/<path:path_to_graph>", methods=["PUT"])
def rename_rule(path_to_graph=""):
    return rename(path_to_graph, rename_rule=True)


def rename(path_to_graph, rename_rule=False):
    try:
        (parent_cmd, child_name) = parse_path(path_to_graph)
        if child_name is None:
            return ("/ cannot be renamed", 412)
        new_name = request.args.get("new_name")
        if not new_name:
            return ("The argument new_name is necessary", 404)
        if rename_rule:
            parent_cmd._do_rename_rule_no_catching(child_name, new_name)
            return ("rule renamed", 200)
        else:
            parent_cmd._do_rename_graph_no_catching(child_name, new_name)
            return ("graph renamed", 200)
    except KeyError:
        return ("Graph not found", 404)
    except ValueError as e:
        return (str(e), 412)


@app.route("/graph/get_kappa/", methods=["POST"])
@app.route("/graph/get_kappa/<path:path_to_graph>", methods=["POST"])
def get_kappa(path_to_graph=""):
    def get_kappa_aux(command):
        if "names" not in request.json.keys():
            return ("the nugget names object does not contain a field names",
                    404)
        nuggets_names = request.json["names"]
        if command.graph.metamodel_ != metamodel_kappa:
            return("not a valid action graph", 404)
        for n in nuggets_names:
            if n not in command.subCmds.keys():
                return ("Nugget " + n + " does not exist in action graph: " +
                        path_to_graph, 404)
        nugget_list = [command.subCmds[n].graph for n in nuggets_names]
        try:
            (agent_dec, rules) = KappaExporter.compile_nugget_list(nugget_list)
            json_rep = {}
            json_rep["agent_decl"] = agent_dec
            json_rep["rules"] = rules
            resp = Response(response=json.dumps(json_rep),
                            status=200,
                            mimetype="application/json")
            return (resp)
        except ValueError as e:
            return (str(e), 412)
    return get_command(path_to_graph, get_kappa_aux)


@app.route("/version/", methods=["GET"])
def get_version():
    return ("0.0", 200)


@app.route("/", methods=["GET"])
def goto_gui():
    return redirect(url_for("get_gui"))

@app.route("/gui/", methods=["GET"])
@app.route("/gui/<path:path>", methods=["GET"])
def get_gui(path="index.html"):
    if os.path.isdir("RegraphGui"):
        return send_from_directory('RegraphGui', path)
    else:
        return ("The gui is not in the directory", 404)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
