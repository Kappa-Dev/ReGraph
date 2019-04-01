"""Collection of generic utils for Cypher queries generation."""
import uuid
import tempfile
import json
import os

from regraph.attribute_sets import (FiniteSet,
                                    IntegerSet,
                                    RegexSet,
                                    UniversalSet)
from regraph.exceptions import ReGraphError
from regraph.utils import attrs_from_json


RESERVED_SET_NAMES = ["IntegerSet", "StringSet", "BooleanSet"]


def load_graph_from_json_apoc(tx, json_data, node_label, edge_label,
                              tmp_dir=None):
    # store json-file somewhere, generate attr repr.
    if tmp_dir is None:
        tmp_dir = "/var/lib/neo4j/import/"
    path = tmp_dir + "kami_tmp.json"
    # fd, path = tempfile.mkstemp(prefix=tmp_dir)
    # try:
    with open(path, 'w+') as tmp:
        for n in json_data["nodes"]:
            n["attrs"] = generate_attributes_json(
                attrs_from_json(n["attrs"]))
            n["attrs"]["id"] = n["id"]
        for e in json_data["edges"]:
            e["attrs"] = generate_attributes_json(
                attrs_from_json(e["attrs"]))
        json.dump(json_data, tmp)

        # load nodes
        node_query = (
            "WITH 'file:///{}' AS url\n".format(path) +
            "CALL apoc.load.json(url) YIELD value\n" +
            "UNWIND value.nodes AS node\n" +
            "MERGE (n:{} {{ id: node.id }}) ON CREATE\n".format(node_label) +
            "\tSET n = node.attrs\n"
        )
        tx.run(node_query)

        # load edges
        edge_query = (
            "WITH 'file:///{}' AS url\n".format(path) +
            "CALL apoc.load.json(url) YIELD value\n" +
            "UNWIND value.edges AS edge\n" +
            "MATCH (u:{} {{ id: edge.from }}), (v:{} {{ id: edge.to }}) \n".format(
                node_label, node_label) +
            "MERGE (u)-[rel:{}]->(v)\n ON CREATE\n".format(edge_label) +
            "\tSET rel = edge.attrs\n"
        )
        tx.run(edge_query)
    # finally:
    #     os.remove(path)


def load_graph_from_json(json_data, node_label, edge_label, literal_id=True,
                         generate_var_names=True):
    query = ""
    if len(json_data["nodes"]) > 0:
        query += "CREATE"

    # Add nodes
    nodes = []

    if (generate_var_names):
        var_names = {
            n["id"]: "n_{}".format(i + 1) for i, n in enumerate(
                json_data["nodes"])
        }
    else:
        var_names = {
            n["id"]: "n_{}".format(n["id"]) for n in json_data["nodes"]
        }

    for node_data in json_data["nodes"]:
        node_id = node_data["id"]
        if literal_id:
            node_id = "'{}'".format(node_id)
        attr_repr = generate_attributes(
            attrs_from_json(node_data["attrs"]))
        nodes.append(
            "({}:{} {{ id: {} {} }})".format(
                var_names[node_data["id"]], node_label, node_id,
                ", " + attr_repr if len(attr_repr) > 0 else ""))

    query += ", ".join(nodes) + ","

    # Add edges
    edges = []
    for edge_data in json_data["edges"]:
        attr_repr = generate_attributes(
            attrs_from_json(edge_data["attrs"]))
        edges.append(
            "({})-[:{} {{ {} }}]->({})".format(
                var_names[edge_data["from"]],
                edge_label,
                attr_repr,
                var_names[edge_data["to"]]))

    query += ", ".join(edges)

    return query


def delete_var(var, detach=False, breakline=True):
    """Query for deleting the input variable.

    Parameters
    ----------
    var
        Name of the variable to remove
    """
    detach = ""
    n = ""
    if detach is True:
        detach = "DETACH "
    if breakline:
        n = "\n"
    return "{}DELETE {}{}".format(detach, var, n)


def set_labels(var_name, labels):
    """Set labels to a var."""
    query = ""
    for label in labels:
        query += "SET {}:{}\n".format(var_name, label)
    return query


def generate_var_name():
    """Generate unique variable names."""
    uid = "uid" + str(uuid.uuid4()).replace("-", "")
    return uid


def set_attributes(var_name, attrs, update=False):
    """Generate a subquery to set the attributes for some variable."""
    query = ""
    if attrs:
        for k, value in attrs.items():
            if isinstance(value, IntegerSet):
                if value.is_universal:
                    query += "\tSET {}.{} = ['IntegerSet']\n".format(var_name, k)
                else:
                    raise ReGraphError(
                        "Non universal IntegerSet is not allowed as "
                        "an attribute value (not implemented)")
            elif isinstance(value, RegexSet):
                if value.is_universal:
                    query += "\tSET {}.{} = ['StringSet']\n".format(var_name, k)
                else:
                    raise ReGraphError(
                        "Non universal RegexSet is not allowed as "
                        "an attribute value (not implemented)")
            elif isinstance(value, FiniteSet):
                elements = []
                for el in value:
                    if type(el) == str:
                        elements.append("'{}'".format(el.replace("'", "\\'")))
                    else:
                        elements.append("{}".format(el))
                if value not in RESERVED_SET_NAMES:
                    query += "SET {}.{}=[{}]\n".format(var_name, k, ", ".join(
                        el for el in elements))
                else:
                    query += "SET {}.{}={}\n".format(var_name, k, ", ".join(
                        el for el in elements))
            else:
                raise ValueError(
                    "Unknown type of attribute '{}': '{}'".format(
                        k, type(value)))
        if update is True:
            # remove all the attributes not mentioned in 'attrs'
            query += (
                "SET {} = apoc.map.clean(properties({}), \n".format(var_name, var_name) +
                "\tfilter(x IN keys({}) WHERE NOT x IN [{}]), [])".format(
                    var_name,
                    ", ".join("'{}'".format(k) for k in attrs.keys()))
            )
    return query


def generate_attributes_json(attrs):
    json_attrs = {}
    if attrs is not None:
        for k, value in attrs.items():
            if isinstance(value, IntegerSet):
                if value.is_universal:
                    json_attrs[k] = ["IntegerSet"]
                else:
                    raise ReGraphError(
                        "Non universal IntegerSet is not allowed as "
                        "an attribute value (not implemented)")
            elif isinstance(value, RegexSet):
                if value.is_universal:
                    json_attrs[k] = ["StringSet"]
                else:
                    raise ReGraphError(
                        "Non universal RegexSet is not allowed as "
                        "an attribute value (not implemented)")
            elif isinstance(value, FiniteSet):
                json_attrs[k] = list(value.fset)
            elif isinstance(value, UniversalSet):
                json_attrs[k] = ["StringSet"]
            else:
                raise ValueError(
                    "Unknown type of attribute '{}': '{}'".format(k, type(value)))
    return json_attrs

def generate_attributes(attrs):
    """Generate a string converting attrs to Cypher compatible format."""
    if attrs is None:
        return ""
    else:
        attrs_items = []
        for k, value in attrs.items():
            if isinstance(value, IntegerSet):
                if value.is_universal:
                    attrs_items.append("{}: ['IntegerSet']\n".format(k))
                else:
                    raise ReGraphError(
                        "Non universal IntegerSet is not allowed as "
                        "an attribute value (not implemented)")
            elif isinstance(value, RegexSet):
                if value.is_universal:
                    attrs_items.append("{}: ['StringSet']\n".format(k))
                else:
                    raise ReGraphError(
                        "Non universal RegexSet is not allowed as "
                        "an attribute value (not implemented)")
            elif isinstance(value, FiniteSet):
                elements = []
                for el in value:
                    if type(el) == str:
                        elements.append("'{}'".format(el.replace("'", "\\'")))
                    else:
                        elements.append("{}".format(el))
                attrs_items.append("{}: [{}]".format(k, ", ".join(
                    el for el in elements)))
            elif isinstance(value, UniversalSet):
                attrs_items.append("{}: ['StringSet']\n".format(k))
            else:
                raise ValueError(
                    "Unknown type of attribute '{}': '{}'".format(k, type(value)))
        return ", ".join(i for i in attrs_items)


def match_node(var_name, node_id, node_label):
    """Query to match a node into the variable.

    Parameters
    ----------
    var_name
        Variable name to use for the matched node
    node_id
        Id of the node to match
    label
        Label of the node to match, default is 'node'
    """
    return "MATCH ({}:{} {{ id : '{}' }})\n".format(
        var_name, node_label, node_id)


def match_nodes(var_id_dict, node_label=None):
    """Match a collection of nodes by their id.

    Parameters
    ----------
    var_id_dict : dict
        Dictionary whose keys are names of the variables to use for
        the matched nodes and whose values are the ids of the nodes
        to match
    label : str
        Label of the nodes to match
    """
    node_label_str = ""
    if node_label:
        node_label_str = ":{}".format(node_label)

    query =\
        "MATCH " +\
        ", ".join("({}{} {{ id : '{}'}}) ".format(
            var_name, node_label_str, node_id)
            for var_name, node_id in var_id_dict.items()) + " "
    return query


def match_edge(u_var, v_var, u_id, v_id, edge_var, u_label, v_label,
               edge_label='edge'):
    """Query for matching an edge.

    Parameters
    ----------
    u_var
        Name of the variable corresponding to the source of
        the edge
    v_var
        Name of the variable corresponding to the target of
        the edge
    u_id
        Id of the source node
    v_id
        Id of the target node
    edge_var
        Name of the variable to use for the matched edge
    label
        Label of the edge to match, default is 'edge'
    """
    query =\
        "MATCH ({}:{} {{id: '{}'}})-[{}:{}]->({}:{} {{id: '{}'}})\n".format(
            u_var, u_label, u_id, edge_var, edge_label, v_var, v_label, v_id)
    return query


def with_vars(carry_vars):
    """Generate WITH statement using the input variables to carry."""
    return "WITH {} ".format(", ".join(carry_vars))


def return_vars(var_list):
    """Generate RETURN query with the input variables."""
    return "RETURN {}\n".format(", ".join(var_list))


def clear_graph(node_label=None):
    """Generate query for removing everything from the graph.

    Parameters
    ----------
    label
        Label of the graph to remove. If None, all the database is cleared
    """
    if node_label is None:
        query = "MATCH (n)\n"
    else:
        query = "MATCH (n:{})\n".format(node_label)
    query += \
        "OPTIONAL MATCH (n)-[r]-()\n" +\
        "DELETE n, r\n"
    return query


def get_nodes(node_label):
    """Generate query returning ids of all nodes of the graph.

    Parameters
    ----------
    label
        Label of the nodes to match, default is 'node'
    """
    query = "MATCH (n:{}) RETURN n.id\n".format(node_label)
    return query


def get_edges(source_label, target_label,
              edge_label):
    """Generate query for getting all the edges of the graph.

    Parameters
    ----------
    source_label : optional
        Label of the source nodes to match
    target_label : optional
        Label of the target nodes to match
    edge_label : iterable, optional
        Label of the edges to match
    """
    query = "MATCH (n:{})-[r:{}]->(m:{})\nRETURN n.id, m.id\n".format(
            source_label,
            edge_label,
            target_label)
    return query


def successors_query(var_name, node_id, node_label,
                     edge_label, successor_label=None,
                     undirected=False):
    """Generate query for getting the ids of all the successors of a node.

    Parameters
    ----------
    var_name
        Name of the variable corresponding to the node to match
    node_id
        Id of the node to match
    node_label : optional
        Label of the node to match, default is 'node'
    edge_label : optional
        Label of the edge to match, default is 'edge'
    successor_label : optional
        Label of the successors we want to find,
        'node_label' is used if None.
    """
    if successor_label is None:
        successor_label = node_label
    if undirected is False:
        arrow = ">"
    else:
        arrow = ""
    query = (
        "OPTIONAL MATCH (n{}:{} {{id : '{}'}})-[:{}]-{} (suc:{})\n".format(
            var_name, node_label,
            node_id, edge_label,
            arrow,
            successor_label) +
        "RETURN suc.id as suc"
    )
    return query


def predecessors_query(var_name, node_id, node_label,
                       edge_label, predecessor_label=None):
    """Generate query for getting the ids of all the predecessors of a node.

    Parameters
    ----------
    var_name
        Name of the variable corresponding to the node to match
    node_id
        Id of the node to match
    node_label
        Label of the node to match
    edge_label
        Label of the edge to match
    predecessor_label
        Label of the predecessors we want to find. node_label if None.
    """
    if predecessor_label is None:
        predecessor_label = node_label
    query = (
        "OPTIONAL MATCH (pred:{})-[:{}]-> (n:{} {{id : '{}'}})\n".format(
            predecessor_label,
            edge_label,
            node_label, node_id) +
        "RETURN pred.id as pred"
    )
    return query


# def get_node(node_id, node_label):
#     """Get node by its id (match and return it)."""
#     return match_node(
#         "n", node_id, node_label=node_label) + return_vars(["n"])


def get_edge(s, t, source_label, target_label, edge_label):
    """Get edge by the ids of its incident nodes."""
    query =\
        "MATCH (n:{} {{id: '{}'}})-[rel:{}]->(m:{} {{id: '{}'}})".format(
            source_label, s, edge_label, target_label, t) +\
        "RETURN rel\n"

    return query


def constraint_query(node_var, node_label, node_property):
    """Generate query for creating a constraint on a property."""
    query = "CONSTRAINT ON ({}:{}) ASSERT {}.{} IS UNIQUE".format(
        node_var,
        node_label,
        node_var,
        node_property
    )
    return query


def merge_properties(var_list, new_props_var, carry_vars=None,
                     method='union'):
    """Merge properties of a list of nodes/edges.

    Parameters
    ----------
    var_list : iterable
        Collection of variables corresponding to the
        nodes/edges whose properties are merged
    new_props_var : str
        Name of the variable corresponding to the
        map of new properties
    carry_vars : iterable
        Collection of variables to carry
    method : str
        'union' or 'intersection'
    """
    if method == 'union':
        return props_union(var_list, new_props_var, carry_vars)
    elif method == "intersection":
        return props_intersection(var_list, new_props_var, carry_vars)
    else:
        raise ValueError("Merging method {} is not defined!".format(method))


def merge_properties_from_list(list_var, new_props_var, carry_vars=None,
                               method='union'):
    """Merge properties of a list of nodes/edges.

    Parameters
    ----------
    list_var : str
        Name of the variable corresponding to the list
        of nodes/edges whose properties are merged
    new_props_var : str
        Name of the variable corresponding to the
        map of new properties
    carry_vars : iterable
        Collection of variables to carry
    method : str
        'union' or 'intersection'
    """
    if method == 'union':
        return props_union_from_list(list_var, new_props_var, carry_vars)
    elif method == "intersection":
        return props_intersection_from_list(list_var, new_props_var, carry_vars)
    else:
        raise ValueError("Merging method {} is not defined!".format(method))


def props_union(var_list, new_props_var, carry_vars=None):
    """Perform the union of the properties of a list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set(var_list)
    else:
        carry_vars.update(var_list)

    query = "//Perform the union of the properties of "
    query += ", ".join(var_list) + "\n"
    query += "WITH [] as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"

    for var in var_list:
        query +=\
            "WITH {} + REDUCE(pairs = [], k in filter(k in keys({}) WHERE k <> 'id') | \n".format(
                new_props_var, var) +\
            "\tpairs + REDUCE(inner_pairs = [], v in {}[k] | \n".format(
                var) +\
            "\t\t inner_pairs + {{key: k, value: v}})) as {},  ".format(
                new_props_var) +\
            ", ".join(carry_vars) + "\n"
    query +=\
        "WITH apoc.map.groupByMulti({}, 'key') as {}, ".format(
            new_props_var, new_props_var) +\
        ", ".join(carry_vars) + "\n" +\
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys({}) | \n".format(
            new_props_var) +\
        "\tpairs + [k, REDUCE(values=[], v in {}[k] | \n".format(
            new_props_var) +\
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as {}, ".format(
            new_props_var) +\
        ", ".join(carry_vars) + "\n" +\
        merge_with_symbolic_sets(new_props_var, new_props_var) + "," +\
        ", ".join(carry_vars) + "\n"

    carry_vars.add(new_props_var)
    return query


def merge_with_symbolic_sets(prop_var, new_props_var):
    query = (
        "WITH apoc.map.fromValues(REDUCE(values=[], k in keys({}) |\n".format(
            prop_var) +
        "\tvalues + [k, CASE WHEN 'StringSet' in {}[k] \n".format(prop_var) +
        "\t\tTHEN ['StringSet'] \n" +
        "\t\tELSE CASE WHEN 'IntegerSet' IN {}[k]\n".format(prop_var) +
        "\t\t\tTHEN ['IntegerSet']\n" +
        "\t\t\tELSE {}[k] END END])) as {}".format(prop_var, new_props_var)
    )
    return query


def props_union_from_list(list_var, new_props_var, carry_vars=None):
    """Perform the union of the properties of a neo4j list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set([list_var])
    else:
        carry_vars.add(list_var)

    carry_vars.remove(list_var)
    query = "UNWIND {} as prop_to_merge\n".format(list_var)

    query += (
        "// accumulate all the attrs of the elements to be merged\n" +
        "WITH [] as new_props, prop_to_merge, " + ", ".join(carry_vars) + "\n" +
        "WITH new_props + REDUCE(pairs = [], k in filter(k in keys(prop_to_merge) WHERE k <> 'id') | \n" +
        "\tpairs + REDUCE(inner_pairs = [], v in prop_to_merge[k] | \n" +
        "\t\tinner_pairs + {key: k, value: v})) as new_props, prop_to_merge, " +
        ", ".join(carry_vars) + "\n"
    )

    query += (
        "WITH collect(prop_to_merge) as {}, ".format(list_var) +
        "collect(new_props) as new_props_col, " +
        ", ".join(carry_vars) + "\n"
        "WITH REDUCE(init=[], props in new_props_col | init + props) as new_props, " +
        "{}, ".format(list_var) + ", ".join(carry_vars) + "\n"
    )
    carry_vars.add(list_var)

    query += (
        "WITH apoc.map.groupByMulti(new_props, 'key') as new_props, " +
        ", ".join(carry_vars) + "\n" +
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys(new_props) | \n"
        "\tpairs + [k, REDUCE(values=[], v in new_props[k] | \n"
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as new_props, " +
        ", ".join(carry_vars) + "\n" +
        merge_with_symbolic_sets("new_props", "new_props") + "," +
        ", ".join(carry_vars) + "\n"
    )
    return query


def props_intersection(var_list, new_props_var, carry_vars=None):
    """Perform the intersection of the properties of a list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set(var_list)
    else:
        carry_vars.update(var_list)

    query = "\n//Perform the intersection of the properties of "
    query += ", ".join(var_list) + "\n"
    query += "WITH [] as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"

    var_first = var_list[0]

    query +=\
        "WITH {} + REDUCE(pairs = [], k in keys({}) | \n".format(
            new_props_var, var_first) +\
        "\tCASE WHEN ALL(others in [{}] WHERE k in keys(others))\n".format(
            ", ".join(var_list[1:])) +\
        "\tTHEN\n" +\
        "\t\tpairs + REDUCE(inner_pairs = [], v in {}[k] | \n".format(
            var_first) +\
        "\t\t\tCASE WHEN ALL(others in [{}] WHERE v in others[k])\n".format(
            ", ".join(var_list[1:])) +\
        "\t\t\tTHEN\n" +\
        "\t\t\t\tinner_pairs + {key: k, value: v}\n" +\
        "\t\t\tELSE\n" +\
        "\t\t\t\tinner_pairs\n" +\
        "\t\t\tEND)\n" +\
        "\tELSE\n" +\
        "\t\tpairs\n" +\
        "\tEND) as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"
    query +=\
        "WITH apoc.map.groupByMulti({}, 'key') as {}, ".format(
            new_props_var, new_props_var) +\
        ", ".join(carry_vars) + "\n" +\
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys({}) | \n".format(
            new_props_var) +\
        "\tpairs + [k, REDUCE(values=[], v in {}[k] | \n".format(
            new_props_var) +\
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as {}, ".format(
            new_props_var) +\
        ", ".join(carry_vars) + "\n"

    carry_vars.add(new_props_var)
    return query


def props_intersection_from_list(list_var, new_props_var, carry_vars=None):
    """Perform the intersection of the properties of a neo4j list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set([list_var])
    else:
        carry_vars.add(list_var)

    query = "\n//Perform the intersection of the properties of {}".format(
        list_var) + "\n"
    query += "WITH [] as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"

    query +=\
        "WITH {} + REDUCE(pairs = [], k in keys({}[0]) | pairs +\n".format(
            new_props_var, list_var) +\
        "\tCASE WHEN ALL(other in {} WHERE k in keys(other))\n".format(
            list_var) +\
        "\tTHEN\n" +\
        "\t\tREDUCE(inner_pairs = [], v in {}[0][k] | inner_pairs +\n".format(
            list_var) +\
        "\t\t\tCASE WHEN ALL(other in {} WHERE v in other[k])\n".format(
            list_var) +\
        "\t\t\tTHEN\n" +\
        "\t\t\t\t{key: k, value: v}\n" +\
        "\t\t\tELSE\n" +\
        "\t\t\t\t[]\n" +\
        "\t\t\tEND)\n" +\
        "\tELSE\n" +\
        "\t\t[]\n" +\
        "\tEND) as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"
    query +=\
        "WITH apoc.map.groupByMulti({}, 'key') as {}, ".format(
            new_props_var, new_props_var) +\
        ", ".join(carry_vars) + "\n" +\
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys({}) | \n".format(
            new_props_var) +\
        "\tpairs + [k, REDUCE(values=[], v in {}[k] | \n".format(
            new_props_var) +\
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as {}, ".format(
            new_props_var) +\
        ", ".join(carry_vars) + "\n"

    carry_vars.add(new_props_var)
    return query


def duplicate_node(original_var, clone_var, clone_id, clone_id_var,
                   original_graph, clone_graph,
                   attach=True, preserv_typing=False,
                   sucs_to_ignore=None, preds_to_ignore=None,
                   carry_vars=None, ignore_naming=False):
    """Generate query for duplicating a node in an other graph.

    Parameters
    ----------
    original_var : str
        Name of the variable corresponding to the original node to clone
    clone_var : str
        Name of the variable corresponding to the new clone node
    clone_id : str
        Id to use for the new node that corresponds to the clone
    clone_id_var : str
        Name of the variable for the id of the new clone node
    original_graph : str
        Label of the graph with the node to clone
    clone_graph : str
        Label of the graph where to clone the node
    sucs_to_ignore : iterable
        List of ids of successors of the original node to ignore
        while reconnecting edges to the new clone node
    preds_to_ignore : iterable
        List of ids of predecessors of the original node to ignore
        while reconnecting edges to the new clone node
    carry_vars : iterable
        Collection of variables to carry

    Returns
    -------
    query : str
        Generated query
    carry_vars : set
        Updated collection of variables to carry
    """
    if carry_vars is None:
            carry_vars = set()
    if sucs_to_ignore is None:
        sucs_to_ignore = set()
    if preds_to_ignore is None:
        preds_to_ignore = set()

    carry_vars.add(original_var)

    if ignore_naming is True:
        query = (
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_var) +
            "CREATE ({}:node:{}) \n".format(
                clone_var, clone_graph) +
            "MERGE ({})-[:typing]->({})".format(original_var, clone_var) +
            "WITH {}, toString(id({})) as {}, {}.id as original_old, ".format(
                clone_var, clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + " \n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to neo4j-generated id\n" +
            "SET {}.id = toString(id({})), {}.count = NULL\n".format(
                clone_var, clone_var, clone_var) +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var) +
            "WITH {}, toString(id({})) as {}, ".format(
                clone_var, clone_var, clone_id_var) +
            ", ".join(carry_vars) + " \n"
        )
    else:
        query = (
            "// search for a node with the same id as the clone id\n" +
            "OPTIONAL MATCH (same_id_node:node:{} {{ id : '{}'}}) \n".format(
                clone_graph, clone_id) +
            "WITH same_id_node,  " +
            "CASE WHEN same_id_node IS NOT NULL "
            "THEN (coalesce(same_id_node.count, 0) + 1) " +
            "ELSE 0 END AS same_id_node_new_count, " +
            ", ".join(carry_vars) + "\n" +
            "// generate new id if the same id node was found\n" +
            "// and filter edges which will be removed \n" +
            "WITH same_id_node, same_id_node_new_count, " +
            "'{}' + CASE WHEN same_id_node_new_count <> 0 ".format(clone_id) +
            "THEN toString(same_id_node_new_count) ELSE '' END as {}, ".format(
                clone_id_var) +
            ", ".join(carry_vars) + "\n" +
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_id_var) +
            "CREATE ({}:node:{}) \n".format(
                clone_var, clone_graph) +
            "MERGE ({})-[:typing]->({})".format(original_var,
                                                clone_var) +
            "WITH same_id_node, same_id_node_new_count, {}, {}, "
            "{}.id as original_old, ".format(
                clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + "\n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to the generated id\n" +
            "SET {}.id = {}, {}.count = NULL, ".format(
                clone_var, clone_id_var, clone_var) +
            "same_id_node.count = same_id_node_new_count + 1\n" +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var)
        )
    carry_vars.add(clone_var)
    query += (
        "WITH [{}] as sucIgnore, ".format(
            ", ".join("'{}'".format(n) for n in sucs_to_ignore)) +
        "[{}] as predIgnore, ".format(
            ", ".join("'{}'".format(n) for n in preds_to_ignore)) +
        ", ".join(carry_vars) + " \n"
    )
    query += (
        "// Match successors and out-edges of a node to be cloned in the clone graph\n" +
        "OPTIONAL MATCH ({})-[out_edge:edge]->(:node:{})-[:typing]->(suc:node:{})\n".format(
            original_var,
            original_graph,
            clone_graph)
    )
    query += (
        "WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore\n" +
        "WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, " +
        "predIgnore, " + ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("suc_maps")

    query += (
        "// match predecessors and in-edges of a node to be cloned in the clone graph\n" +
        "OPTIONAL MATCH (pred:node:{})<-[:typing]-(:node:{})-[in_edge:edge]->({}) \n".format(
            clone_graph,
            original_graph,
            original_var)
    )
    query += (
        "WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore\n" +
        "WITH collect({neighbor: pred, edge: in_edge}) as pred_maps, " +
        ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("pred_maps")

    query += (
        "// copy all incident edges of the original node to the clone\n" +
        "FOREACH (suc_map IN suc_maps | \n"
        "\tFOREACH (suc IN "
        "CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE ({})-[new_edge:edge]->(suc) \n".format(clone_var) +
        "\t\tSET new_edge = suc_map.edge))\n"
        "FOREACH (pred_map IN pred_maps | \n"
        "\tFOREACH (pred IN "
        "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE (pred)-[new_edge:edge]->({}) \n".format(clone_var) +
        "\t\tSET new_edge = pred_map.edge))\n"
    )
    carry_vars.remove("suc_maps")
    carry_vars.remove("pred_maps")

    if preserv_typing:
        query += (
            with_vars(carry_vars) + "\n" +
            "OPTIONAL MATCH ({})-[out_typ_edge:typing]->(suc_typ:node)\n".format(
                original_var) +
            "WITH collect({neighbor: suc_typ, edge: out_typ_edge}) as suc_typ_maps, " +
            ", ".join(carry_vars) + " \n"
        )
        carry_vars.add("suc_typ_maps")
        query += (
            "OPTIONAL MATCH (pred_typ:node)-[in_typ_edge:typing]->({}) \n".format(
                original_var) +
            "WITH collect({neighbor: pred_typ, edge: in_typ_edge}) as pred_typ_maps, " +
            ", ".join(carry_vars) + " \n"
        )
        carry_vars.add("pred_typ_maps")

        query += (
            "// copy all incident typing edges of the original node to the clone\n" +
            "FOREACH (suc_map IN suc_typ_maps | \n"
            "\tFOREACH (suc IN "
            "CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE ({})-[new_edge:typing]->(suc) \n".format(clone_var) +
            "\t\tSET new_edge = suc_map.edge))\n"
            "FOREACH (pred_map IN pred_typ_maps | \n"
            "\tFOREACH (pred IN "
            "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE (pred)-[new_edge:typing]->({}) \n".format(clone_var) +
            "\t\tSET new_edge = pred_map.edge))\n"
        )
        carry_vars.remove("suc_typ_maps")
        carry_vars.remove("pred_typ_maps")

    return query, carry_vars


def clone_graph(original_graph, cloned_graph, carry_vars=None):
    """Clone all the nodes and edges of a graph to another."""
    if carry_vars is None:
        carry_vars = set()

    query =\
        "MATCH (n:node:{})\n".format(original_graph) +\
        duplicate_node('n', 'm', 'id', 'm_id_var',
                       original_graph=original_graph,
                       clone_graph=cloned_graph,
                       carry_vars=carry_vars,
                       ignore_naming=True)[0]
    return query, carry_vars


def nb_of_attrs_mismatch(source, target):
    """Generate a query which returns the number of attributes of a node which
    are not in its image."""
    query = (
        "REDUCE(invalid = 0, k in filter(k in keys({}) WHERE k <> 'id') |\n".format(source) +
        "\tinvalid + CASE\n" +
        "\t\tWHEN NOT k IN keys({}) THEN 1\n".format(target) +
        "\t\tELSE REDUCE(invalid_values = 0, v in {}[k] |\n".format(source) +
        "\t\t\tinvalid_values + CASE\n" +
        "\t\t\t\tWHEN NOT v IN {}[k] THEN 1 ELSE 0 END)\n".format(target) +
        "\t\tEND)"
    )
    return query


def exists_edge(s, t, node_label, edge_label):
    query = (
        "RETURN EXISTS( (:{} {{ id: '{}' }})-[:{}]->(:{} {{ id: '{}' }}) ) AS result".format(
            node_label, s, edge_label, node_label, t)
    )
    return query


def attributes_inclusion(source_var, target_var, result_var):
    query = (
        "REDUCE(invalid = 0, k in filter(k in keys(properties({})) WHERE k <> 'id') |\n".format(
            source_var) +
        "\tinvalid + CASE\n" +
        "\t\tWHEN NOT k IN keys(properties({})) THEN 1\n".format(target_var) +
        "\t\tELSE REDUCE(invalid_values = 0, v in properties({})[k] |\n".format(source_var) +
        "\t\t\tinvalid_values + CASE properties({})[k][0]\n".format(target_var) +
        "\t\t\t\tWHEN 'IntegerSet' THEN CASE WHEN toInt(v) IS NULL THEN 1 ELSE 0 END\n" +
        "\t\t\t\tWHEN 'StringSet' THEN CASE WHEN toString(v) <> v THEN 1 ELSE 0 END\n" +
        "\t\t\t\tWHEN 'BooleanSet' THEN CASE WHEN v=true OR v=false THEN 0 ELSE 1 END\n" +
        "\t\t\t\tELSE CASE WHEN NOT v IN properties({})[k] THEN 1 ELSE 0 END END)\n".format(target_var) +
        "\t\tEND) AS {}".format(result_var)
    )
    return query


def get_node_attrs(node_id, node_label, attrs_var):
    """Query for retreiving node's attributes."""
    query = (
        "MATCH (n:{} {{ id: '{}' }}) \n".format(
            node_label, node_id) +
        "RETURN properties(n) as {}\n".format(attrs_var)
    )
    return query


def get_edge_attrs(source_id, targe_id, edge_label, attrs_var):
    """Query for retreiving edge's attributes."""
    query = (
        "MATCH ({{ id: '{}' }})-[rel:{}]->({{ id: '{}' }}) \n".format(
            source_id, edge_label, targe_id) +
        "RETURN properties(rel) as {}\n".format(attrs_var)
    )
    return query


def properties_to_attributes(result, var_name):
    """Retrieve attributes from raw Neo4j property dict."""
    attrs = {}
    for record in result:
        if var_name in record.keys():
            raw_dict = record[var_name]
            if raw_dict:
                if 'id' in raw_dict:
                    del raw_dict['id']
                for k, v in raw_dict.items():
                    try:
                        if len(v) == 1:
                            if v[0] == "IntegerSet":
                                attrs[k] = IntegerSet.universal()
                            elif v[0] == "StringSet":
                                attrs[k] = RegexSet.universal()
                            else:
                                attrs[k] = FiniteSet(v)
                        else:
                            attrs[k] = FiniteSet(v)
                    except TypeError:
                        attrs[k] = FiniteSet([v])
    return attrs
