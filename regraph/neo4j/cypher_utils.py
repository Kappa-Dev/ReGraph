"""Collection of utils for Cypher queries generation."""
from regraph.default.attribute_sets import *


def set_attributes(var_name, attrs):
    """Generate a subquery to set the attributes for some variable."""
    query = ""
    for k, value in attrs.items():
        if isinstance(value, FiniteSet):
            elements = []
            for el in value:
                if type(el) == str:
                    elements.append("'{}'".format(el))
                else:
                    elements.append("{}".format(el))
            query += "SET {}.{}=[{}] ".format(var_name, k, ", ".join(
                el for el in elements))
        else:
            raise ValueError(
                "Unknown type of attribute '{}': '{}'".format(k, type(value)))
    return query


def generate_attributes(attrs):
    """Generate a string converting attrs to Cypher compatible format."""
    if attrs is None:
        return ""
    else:
        attrs_items = []
        for k, value in attrs.items():
            if isinstance(value, FiniteSet):
                elements = []
                for el in value:
                    if type(el) == str:
                        elements.append("'{}'".format(el))
                    else:
                        elements.append("{}".format(el))
                attrs_items.append("{}: [{}]".format(k, ", ".join(
                    el for el in elements)))
            else:
                raise ValueError(
                    "Unknown type of attribute '{}': '{}'".format(k, type(value)))
        return ", ".join(i for i in attrs_items)


def match_node(var_name, node_id):
    """Query to match a node into the variable.

    Parameters
    ----------
    var_name
        Variable name to use for the matched node
    node_id
        Id of the node to match
    """
    return "MATCH ({}:node {{ id : '{}' }})\n".format(
        var_name, node_id)


def match_nodes(var_id_dict):
    """Match a collection of nodes by their id.

    Parameters
    ----------
    var_id_dict : dict
        Dictionary whose keys are names of the variables to use for
        the matched nodes and whose values are the ids of the nodes
        to match
    """
    query =\
        "MATCH " +\
        ", ".join("({}:node {{ id : '{}'}})".format(var_name, node_id)
                  for var_name, node_id in var_id_dict.items()) + " "
    return query


def match_edge(u_var, v_var, u_id, v_id, edge_var):
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
    """
    query =\
        match_nodes({u_var: u_id, v_var: v_id}) + ", " +\
        "({})-[{}:edge]->({})".format(u_var, edge_var, v_var) + "\n"
    return query


def create_node(var_name, node_id, node_id_var, attrs=None,
                literal_id=True, carry_vars=None,
                ignore_naming=False):
    """Generate query for node creation.

    Parameters
    ----------
    var_name
        Name of the variable corresponding to the created
        node in the query
    node_id
        Id of the node to create
    node_id_var
        Variable corresponding to the new id of the node to create
    literal_id : bool
        True if parameter `node_id` is a literal, otherwise it is
        treated as the variable name
    carry_vars : iterable
        Collection of variables to carry

    Returns
    -------
    query : str
        String containing generated Cypher query
    carry_vars : set
        Set of updated variables to carry

    """
    if literal_id:
        node_id = "'{}'".format(node_id)

    if carry_vars is None:
        carry_vars = set()
    if not ignore_naming:
        query = (
            "OPTIONAL MATCH (same_id_node:node) \n" +
            "WHERE same_id_node.id = {} \n".format(node_id) +
            "FOREACH(new_count \n\tIN CASE WHEN same_id_node IS NOT NULL\n"
            "\tTHEN [coalesce(same_id_node.count, 0) + 1]\n"
            "\tELSE [] END | \n"
            "\t\tSET same_id_node.count = new_count) \n"
            "WITH same_id_node "
        )
        if len(carry_vars) > 0:
            query += ", " + ", ".join(carry_vars) + "\n"
        else:
            query += "\n"
        query += (
            "UNWIND\n\tCASE WHEN same_id_node IS NOT NULL\n"
            "\tTHEN [{} + same_id_node.count]\n".format(node_id) +
            "\tELSE [{}] END AS {} \n".format(node_id, node_id_var) +
            "\t\tCREATE ({}:node {{ id : {} }}) \n".format(
                var_name, node_id_var)
        )
    else:
        query =\
            "CREATE ({}:node) \n".format(var_name) +\
            "SET {}.id = toString(id({})) \n".format(var_name, var_name)
        query += "WITH toString(id({})) as {} ".format(var_name, node_id_var)
        carry_vars.add(var_name)
        query += ", " + ", ".join(carry_vars) + "\n"

    if attrs is not None:
        query += set_attributes(var_name, attrs)

    carry_vars.add(node_id_var)
    carry_vars.add(var_name)
    return query, carry_vars


def create_edge(source_var, target_var, attrs=None):
    """Generate query for edge creation.

    source_var
        Name of the variable corresponding to the source
        node
    target_var
        Name of the variable corresponding to the target
        node
    attrs
        Attributes of the new edge
    """
    attrs_str = generate_attributes(attrs)
    query = "MERGE ({})-[:edge {{ {} }}]->({})\n".format(
        source_var, attrs_str, target_var)
    return query


def delete_nodes_var(var_names):
    """Query for deleting nodes corresponding to the input variables.

    Parameters
    ----------
    var_names : iterable
        Collection of variables corresponding to nodes to remove
    """
    return "DETACH DELETE {}\n".format(
        ', '.join(v for v in var_names))


def delete_edge_var(edge_var):
    """Query for deleting an edge corresponding to the input variable.

    Parameters
    ----------
    edge_var
        Name of the variable corresponding to the edge to remove
    """
    return "DELETE {}\n".format(edge_var)


def with_vars(carry_vars):
    """Generate WITH statement using the input variables to carry."""
    return "WITH {} ".format(", ".join(carry_vars))


def return_vars(var_list):
    """Generate RETURN query with the input variables."""
    return "RETURN {}\n".format(", ".join(var_list))


def clear_graph():
    """Generate query for removing everything from the graph."""
    (query) = (
        "MATCH (n)\n"
        "OPTIONAL MATCH (n)-[r]-()\n"
        "DELETE n, r\n"
    )
    return query


def get_nodes():
    """Generate query returning ids of all nodes of the graph."""
    query = "MATCH (n:node) RETURN n.id\n"
    return query


def get_edges():
    """Generate query for getting all the edges of the graph."""
    query = "MATCH (n)-[r]->(m)\nRETURN n.id, m.id\n"
    return query


def cloning_query(original_var, clone_var, clone_id, clone_id_var,
                  sucs_to_ignore=None, preds_to_ignore=None,
                  carry_vars=None, ignore_naming=False):
    """Generate query for cloning a node.

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
    query = (
        "WITH [{}] as sucIgnore, ".format(
            ", ".join("'{}'".format(n) for n in sucs_to_ignore)) +
        "[{}] as predIgnore, ".format(
            ", ".join("'{}'".format(n) for n in preds_to_ignore)) +
        ", ".join(carry_vars) + " \n"
    )
    query += (
        "// match successors and out-edges of a node to be cloned\n" +
        "OPTIONAL MATCH ({})-[out_edge:edge]->(suc) \n".format(original_var) +
        "WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore\n" +
        "WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, predIgnore, " +
        ", ".join(carry_vars) + " \n"
    )

    carry_vars.add("suc_maps")
    query += (
        "// match predecessors and in-edges of a node to be cloned\n" +
        "OPTIONAL MATCH (pred)-[in_edge:edge]->({}) \n".format(original_var) +
        "WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore\n" +
        "WITH collect({neighbor: pred, edge: in_edge}) as pred_maps, " +
        ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("pred_maps")

    if ignore_naming is True:
        query += (
            "// create a node corresponding to the clone\n" +
            "CREATE ({}:node) \n".format(
                clone_var, clone_var) +
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
        query += (
            "// search for a node with the same id as the clone id\n" +
            "OPTIONAL MATCH (same_id_node:node {{ id : '{}'}}) \n".format(
                clone_id) +
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
            "CREATE ({}:node) \n".format(
                clone_var, clone_id_var) +
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
    carry_vars.add(clone_var)
    carry_vars.remove("suc_maps")
    carry_vars.remove("pred_maps")
    return query, carry_vars


def merging_query(original_vars, merged_var, merged_id,
                  merged_id_var, carry_vars=None, ignore_naming=False):
    """Generate query for merging nodes.

    Parameters
    ----------
    original_vars : iterable
        Collection of names of the variables corresponding
        to the nodes to merge
    merged_var : str
        Name of the variable corresponding to the new merged node
    merged_id : str
        Id to use for the new node that corresponds to the merged node
    merged_id_var : str
        Name of the variable for the id of the new merged node
    carry_vars : str
        Collection of variables to carry

    Returns
    -------
    query : str
        Generated query
    carry_vars : set
        Updated collection of variables to carry
    """
    if carry_vars is None:
        carry_vars = set(original_vars)

    query = ""

    query += (
        "// use the APOC procedure 'apoc.refactor.mergeNodes' to merge nodes\n"
        "CALL apoc.refactor.mergeNodes([{}], {{properties: 'combine'}})\n".format(
            ", ".join(original_vars)) +
        "YIELD node as {}\n".format(merged_var)
    )
    carry_vars.add(merged_var)
    for n in original_vars:
        if n != merged_var:
            carry_vars.remove(n)

    if ignore_naming is True:
        query += (
            "// set appropriate node id\n"
            "SET {}.id = toString(id({}))\n".format(merged_var, merged_var) +
            "SET {}.count = NULL\n".format(merged_var) +
            "WITH toString(id({})) as {}, ".format(merged_var, merged_id_var) +
            ", ".join(carry_vars) + "\n"
        )
    else:
        query += (
            "// search for a node with the same id as the clone id\n" +
            "OPTIONAL MATCH (same_id_node:node {{ id : '{}'}}) \n".format(
                merged_id) +
            "WITH same_id_node,  " +
            "CASE WHEN same_id_node IS NOT NULL "
            "THEN (coalesce(same_id_node.count, 0) + 1) " +
            "ELSE 0 END AS same_id_node_new_count, " +
            ", ".join(carry_vars) + "\n" +
            "// generate new id if the same id node was found\n" +
            "// and filter edges which will be removed \n" +
            "WITH same_id_node, same_id_node_new_count, " +
            "'{}' + CASE WHEN same_id_node_new_count <> 0 ".format(merged_id) +
            "THEN toString(same_id_node_new_count) ELSE '' END as {}, ".format(
                merged_id_var) +
            ", ".join(carry_vars) + "\n"
            "// set appropriate node id\n"
            "SET {}.id = {}\n".format(merged_var, merged_id_var) +
            "SET {}.count = NULL\n".format(merged_var) +
            "WITH {}, ".format(merged_id_var) + ", ".join(carry_vars) + "\n"
        )

    carry_vars.add(merged_id_var)

    query += (
        "// find and merge multiple relations resulting from the node merge\n"
        "OPTIONAL MATCH ({})-[out_rel:edge]->(suc)\n".format(merged_var) +
        "WITH collect({neighbor: suc, edge: out_rel}) as suc_maps, " +
        ", ".join(carry_vars) + "\n" +
        "OPTIONAL MATCH (pred)-[in_rel:edge]->({})\n".format(merged_var) +
        "WHERE pred.id <> {}.id\n".format(merged_var) +
        "WITH collect({neighbor: pred, edge: in_rel}) as pred_maps, suc_maps, " +
        ", ".join(carry_vars) + "\n" +
        "WITH apoc.map.groupByMulti(suc_maps, 'neighbor') as suc_maps, "
        "apoc.map.groupByMulti(pred_maps, 'neighbor') as pred_maps, " +
        ", ".join(carry_vars) + "\n" +
        "WITH REDUCE(edges=[],  k in filter(k in keys(suc_maps) "
        "WHERE length(suc_maps[k]) > 1 ) | \n"
        "\tedges + [suc_maps[k]]) + \n"
        "\tREDUCE(edges=[],  k in filter(k in keys(pred_maps) "
        "WHERE length(pred_maps[k]) > 1)| \n"
        "\t\tedges + [pred_maps[k]]) as all_merge_edges, " +
        ", ".join(carry_vars) + "\n" +
        "UNWIND all_merge_edges as edge_list\n"
        "\tCALL apoc.refactor.mergeRelationships(\n"
        "\t\tREDUCE(rels=[], el in edge_list | rels + el['edge']), "
        " {properties: 'combine'})\n"
        "\tYIELD rel\n"
    )
    return query, carry_vars


def find_matching(pattern, nodes=None):
    """Query that performs pattern match in the graph.

    Parameters
    ----------
    pattern : nx.(Di)Graph
        Graph object representing a pattern to search for
    nodes : iterable, optional
        Collection of ids of nodes to constraint the search space of matching
    """
    query =\
        "MATCH {}".format(
            ", ".join("({}:node)".format(n) for n in pattern.nodes()))
    if len(pattern.edges()) > 0:
        query += ", {}".format(
            ", ".join("({})-[:edge]->({})".format(u, v) for u, v in pattern.edges())) + "\n"
    else:
        query += "\n"

    if nodes is not None:
        query +=\
            "WHERE " + " AND ".join(
                "{}.id IN [{}]".format(
                    pattern_n, ", ".join("'{}'".format(n) for n in nodes))
                for pattern_n in pattern.nodes()) + "\n"

    query += "RETURN {}".format(", ".join(pattern.nodes()))

    return query


def match_pattern_instance(pattern, pattern_vars, instance):
    """Query to match an instance of the pattern.

    Parameters
    ----------
    pattern : nx.(Di)Graph
        Graph object representing a pattern
    instance : dict
        Instance of the pattern in the graph, dictionary
        whose keys are node ids of the pattern and whose
        values are ids of the nodes of the graph
    """
    query =\
        match_nodes(instance)

    if len(pattern.edges()) > 0:
        query +=\
            ", " +\
            ", ".join(
                "({})-[{}:edge]->({})".format(
                    pattern_vars[u],
                    str(pattern_vars[u]) + "_" + str(pattern_vars[v]),
                    pattern_vars[v])
                for u, v in pattern.edges())
    else:
        query += "\n"
    return query


def get_node(node_id):
    """Get node by its id (match and return it)."""
    return match_node("n", node_id) + return_vars(["n"])


def get_edge(s, t):
    """Get edge by the ids of its incident nodes."""
    query =\
        "MATCH (n:node {{id: '{}'}})-[rel:edge]->(m:node {{id: '{}'}})".format(
            s, t) +\
        "RETURN rel\n"

    return query
