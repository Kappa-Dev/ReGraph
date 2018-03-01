"""Collection of utils for Cypher queries generation."""
from regraph.default.attribute_sets import *


def set_attributes(var_name, attrs):
    """."""
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
    """."""
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
    """Query for match a node into the variable.

    Parameters
    ----------
    var_name
        Variable name to use for the matched node
    node_id
        Id of the node to match
    """
    return "MATCH ({}:node {{ id : '{}' }}) ".format(
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
        "({})-[{}:edge]->({})".format(u_var, edge_var, v_var) + " "
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
            " OPTIONAL MATCH (same_id_node:node) " +
            "WHERE same_id_node.id = {} ".format(node_id) +
            "FOREACH(new_count IN CASE WHEN same_id_node IS NOT NULL "
            "THEN [coalesce(same_id_node.count, 0) + 1] "
            "ELSE [] END | "
            "SET same_id_node.count = new_count) "
            "WITH same_id_node "
        )
        if len(carry_vars) > 0:
            query += ", " + ", ".join(carry_vars) + " "
        else:
            query += " "
        query += (
            "UNWIND CASE WHEN same_id_node IS NOT NULL "
            "THEN [{} + same_id_node.count] ".format(node_id) +
            "ELSE [{}] END AS {} ".format(node_id, node_id_var) +
            "CREATE ({}:node {{ id : {} }}) ".format(var_name, node_id_var)
        )
    else:
        query =\
            "CREATE ({}:node) ".format(var_name) +\
            "SET {}.id=toString(id({})) ".format(var_name, var_name)
        query += "WITH toString(id({})) as {} ".format(var_name, node_id_var)
        carry_vars.add(var_name)
        query += ", " + ", ".join(carry_vars) + " "

    if attrs is not None:
        query += set_attributes(var_name, attrs)

    carry_vars.add(node_id_var)
    carry_vars.add(var_name)
    return query, carry_vars


def create_edge(u_var, v_var, attrs=None):
    """Generate query for edge creation.

    u_var
        Name of the variable corresponding to the source
        of the edge
    v_var
        Name of the variable corresponding to the source
        of the edge
    """
    attrs_str = generate_attributes(attrs)
    query = "MERGE ({})-[:edge {{ {} }}]->({}) ".format(
        u_var, attrs_str, v_var)
    return query


def delete_nodes_var(var_names):
    """Query for deleting nodes corresponding to the input variables.

    Parameters
    ----------
    var_names : iterable
        Collection of variables corresponding to nodes to remove
    """
    return "DETACH DELETE {} ".format(
        ', '.join(v for v in var_names))


def delete_edge_var(edge_var):
    """Query for deleting an edge corresponding to the input variable.

    Parameters
    ----------
    edge_var
        Name of the variable corresponding to the edge to remove
    """
    return "DELETE {} ".format(edge_var)


def with_vars(carry_vars):
    """Generate with statement with input variables to carry."""
    return "WITH {} ".format(", ".join(carry_vars))


def return_vars(var_list):
    """Generate return query with variables in the list."""
    return "RETURN {} ".format(", ".join(var_list))


def clear_graph():
    """Generate query for removing everything from the graph."""
    (query) = (
        "MATCH (n)"
        "OPTIONAL MATCH (n)-[r]-()"
        "DELETE n, r"
    )
    return query


def get_nodes():
    """Generate query returning ids of all nodes of the graph."""
    query = "MATCH (n:node) RETURN n.id"
    return query


def get_edges():
    """Generate query for getting all the edges of the graph."""
    query = "MATCH (n)-[r]->(m) RETURN n.id, m.id"
    return query


def cloning_query(original_var, clone_var, clone_id, clone_id_var,
                  neighbours_to_ignore=None, carry_vars=None,
                  ignore_naming=False):
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
    if neighbours_to_ignore is None:
        neighbours_to_ignore = set()

    carry_vars.add(original_var)
    query =\
        "WITH [{}] as ignoredNodes".format(
            ", ".join("'{}'".format(n) for n in neighbours_to_ignore)) +\
        ", " + ", ".join(carry_vars) + " "
    query += (
        "OPTIONAL MATCH ({})-[:edge]->(succ) ".format(original_var) +
        "OPTIONAL MATCH (pred)-[:edge]->({}) ".format(original_var) +
        "WITH collect(succ) as listSucc, collect(pred) as listPred, " +
        " ignoredNodes as ig" +
        ", " + ", ".join(carry_vars) + " "
    )
    if ignore_naming is True:
        query += (
            "WITH filter(varNode in listSucc WHERE NOT " +
            "(varNode.id in ig)) AS filtSucc, " +
            "filter(varNode in listPred " +
            "WHERE NOT (varNode.id in ig)) AS filtPred, " +
            ", ".join(carry_vars) + " "
        )
        query += (
            "CREATE ({}:node) ".format(
                clone_var, clone_var) +
            "WITH {}, filtPred, filtSucc, toString(id({})) as {}, "
            "{}.id as original_old, ".format(
                clone_var, clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + " " +
            "SET {}.id = NULL SET {}={} SET {}.id = toString(id({})) "
            "SET {}.id=original_old ".format(
                original_var, original_var, clone_var,
                clone_var, clone_var, original_var) +
            "WITH {}, filtPred, filtSucc, toString(id({})) as {}, ".format(
                clone_var, clone_var, clone_id_var) +
            ", ".join(carry_vars) + " " +
            "FOREACH (succ in filtSucc | " +
            "MERGE ({})-[:edge]->(succ)) ".format(clone_var) +
            "FOREACH (pred in filtPred | MERGE (pred)-[:edge]->({})) ".format(
                clone_var)
        )
        carry_vars.add(clone_var)
    else:
        query += (
            "OPTIONAL MATCH (same_id_node:node {{ id : '{}'}}) ".format(
                clone_id) +
            "WITH same_id_node, listSucc, listPred, ig,  " +
            "CASE WHEN same_id_node IS NOT NULL "
            "THEN (coalesce(same_id_node.count, 0) + 1) " +
            "ELSE 0 END AS same_id_node_new_count, " +
            ", ".join(carry_vars) + " " +
            "WITH same_id_node, same_id_node_new_count, " +
            "'{}' + CASE WHEN same_id_node_new_count <> 0 ".format(clone_id) +
            "THEN toString(same_id_node_new_count) ELSE '' END as {}, ".format(
                clone_id_var) +
            "filter(var in listSucc WHERE NOT (var.id in ig)) AS filtSucc, " +
            "filter(var in listPred WHERE NOT (var.id in ig)) AS filtPred, " +
            ", ".join(carry_vars) + " "
        )
        query += (
            "CREATE ({}:node) ".format(
                clone_var, clone_id_var) +
            "WITH same_id_node, same_id_node_new_count, {}, {}, "
            "filtSucc, filtPred, {}.id as original_old, ".format(
                clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + " " +
            "SET {}.id=null, {} = {}, {}.id = {}, "
            "same_id_node.count = same_id_node_new_count + 1, "
            "{}.id=original_old ".format(
                original_var, clone_var, original_var,
                clone_var, clone_id_var, original_var) +
            "FOREACH (succ in filtSucc | MERGE ({})-[:edge]->(succ)) ".format(
                clone_var) +
            "FOREACH (pred in filtPred | MERGE (pred)-[:edge]->({})) ".format(
                clone_var)
        )
        carry_vars.add(clone_var)
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

    match_edges = ""
    for n in original_vars:
        match_edges +=\
            "OPTIONAL MATCH ({})-[:edge]->({}), ".format(n, "suc_" + n) +\
            "({})-[:edge]->({}) ".format("pred_" + n, n) +\
            "WITH COLLECT({}) as sucs_{}, COLLECT({}) as preds_{} ".format(
                "suc_" + n, n, "pred_" + n, n, n)

        if len(carry_vars) > 0:
            match_edges += ", " + ", ".join(carry_vars) + " "
        else:
            match_edges += " "

        carry_vars.add("sucs_{}".format(n))
        carry_vars.add("preds_{}".format(n))

    # match_edges =\
    #     "OPTIONAL MATCH " + ", ".join(
    #         "({})-[:edge]->({}), "
    #         "({})-[:edge]->({})".format(
    #             n, "suc_" + n, "pred_" + n, n) for n in original_vars) + " " +\
    #     " WITH " + ", ".join(
    #         "COLLECT({}) as sucs_{}, COLLECT({}) as preds_{}".format(
    #             "suc_" + n, n, "pred_" + n, n) for n in original_vars)

    # if len(carry_vars) > 0:
    #     match_edges += ", " + ", ".join(carry_vars) + " "
    # else:
    #     match_edges += " "

    # merged_var += "_merged_var"
    new_node, carry_vars = create_node(
        merged_var, merged_id, merged_id_var,
        carry_vars=carry_vars, ignore_naming=ignore_naming)

    reconnect_edges =\
        " ".join(
            "FOREACH(s IN sucs_{} | MERGE ({})-[:edge]->(s)) ".format(
                n, merged_var) for n in original_vars) +\
        " ".join(
            "FOREACH(p IN preds_{} | MERGE (p)-[:edge]->({})) ".format(
                n, merged_var) for n in original_vars) +\
        "FOREACH(n IN {} | ".format(
            " + ".join("sucs_{} + preds_{}".format(n, n) for n in original_vars)) +\
        "FOREACH(dummy_var IN CASE WHEN n IN [{}] THEN ['dummy'] ELSE [] END | ".format(
            ", ".join(n for n in original_vars)) +\
        "MERGE ({})-[:edge]->({})) )".format(merged_var, merged_var) + " "

    delete_nodes = delete_nodes_var(original_vars)

    for n in original_vars:
        if n in carry_vars and n != merged_id:
            carry_vars.remove(n)
        if "sucs_{}".format(n) in carry_vars:
            carry_vars.remove("sucs_{}".format(n))
        if "preds_{}".format(n) in carry_vars:
            carry_vars.remove("preds_{}".format(n))
        # carry_vars.remove(merged_id_var)
    carry_vars.add(merged_var)

    query = match_edges + new_node + reconnect_edges + delete_nodes

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
            ", ".join("({})-[:edge]->({})".format(u, v) for u, v in pattern.edges())) + " "
    else:
        query += " "

    if nodes is not None:
        query +=\
            " WHERE " + " AND ".join(
                "{}.id IN [{}]".format(
                    pattern_n,
                    ", ".join("'{}'".format(n) for n in nodes))
                for pattern_n in pattern.nodes()) + " "

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
            ", ".join("({})-[{}:edge]->({})".format(
                pattern_vars[u], 
                str(pattern_vars[u]) + "_" + str(pattern_vars[v]), 
                pattern_vars[v])
                      for u, v in pattern.edges())
    else:
        query += " "
    return query
