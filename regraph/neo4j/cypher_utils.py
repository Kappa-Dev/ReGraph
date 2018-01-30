"""Collection of utils for Cypher generation."""


def add_node(node, attrs=None):
    return add_nodes_from([node])


def add_edge(source, target, attrs=None):
    return add_edges_from([(source, target)])


def remove_node(node):
    query = ("MATCH (n:node) WHERE n.id='{}'"
             "DETACH DELETE n, r".format(node))
    return query


def remove_edge(source, target):
    query = "MATCH {} WHERE {} DELETE r".format(
        "({})-[r]->({})".format(source, target),
        "{}.id = '{}' and {}.id = '{}'".format(source, source, target, target)
    )
    return query


def add_nodes_from(nodes):
    nodes_statement = "CREATE {}".format(
        ", ".join("({}:node {{ id : '{}' }})".format(n, n) for n in nodes))
    return nodes_statement


def add_edges_from(edges):
    nodes = set(list(sum(edges, ())))
    match_nodes = "MATCH {} WHERE {} ".format(
        ", ".join("({})".format(n) for n in nodes),
        " and ".join("{}.id = '{}'".format(n, n) for n in nodes)
    )
    edges_statement = "CREATE " + ", ".join(
        "({})-[:edge]->({})".format(u, v) for u, v in edges)
    print(match_nodes + edges_statement)
    return match_nodes + edges_statement


def clear_graph():
    (query) = (
        "MATCH (n)"
        "OPTIONAL MATCH (n)-[r]-()"
        "DELETE n, r"
    )
    return query


def nodes():
    query = "MATCH (n:node) RETURN n.id"
    return query


def edges():
    query = "MATCH (n)-[r]->(m) RETURN n.id, m.id"
    return query


def copy_node(node):
    """Copy node in the persistent graph."""
    pass


def generate_new_name(prefix=None):
    pass


def match_node(var_name, node_id):
    return "MATCH ({}:node {{ id : '{}' }}) ".format(
        var_name, node_id)


def match_nodes(id_var_dict):
    query =\
        "MATCH " +\
        ", ".join("({}:node {{ id : '{}'}})".format(var_name, node_id)
                  for var_name, node_id in id_var_dict.items()) + " "
    return query


def create_node(var_name, node_id, literal_id=True):
    if literal_id:
        node_id = "'{}'".format(node_id)
    return "CREATE ({}:node {{ id : {} }}) ".format(
        var_name, node_id)


def create_edge(u_var, v_var):
    return "CREATE ({})-[:edge]->({}) ".format(u_var, v_var)


def delete_nodes_var(var_names):
    return "DETACH DELETE {} ".format(
        ', '.join(v for v in var_names))


def delete_edge_var(edge_var):
    return "DELETE {} ".format(edge_var)


def with_vars(carry_vars):
    return "WITH {} ".format(", ".join(carry_vars))


def return_vars(var_list):
    return "RETURN {} ".format(", ".join(var_list))


def clonning_query(original_var, clone_var, new_id_var,
                   sucs_to_ignore=None, preds_to_ignore=None,
                   carry_vars=None):
    if carry_vars is None:
        carry_vars = set()
    if sucs_to_ignore is None:
        sucs_to_ignore = set()
    if preds_to_ignore is None:
        preds_to_ignore = set()
    carry_vars.add(original_var)
    query =\
        "SET {}.count = coalesce({}.count, 0) + 1 ".format(
            original_var, original_var) +\
        "WITH {}.id + {}.count AS {}, {} ".format(
            original_var, original_var, new_id_var, ", ".join(carry_vars)) +\
        "CREATE ({}:node {{ id : {} }}) ".format(clone_var, new_id_var)
    carry_vars.add(clone_var)
    carry_vars.add(new_id_var)
    query +=\
        "WITH {} ".format(", ".join(carry_vars)) +\
        "OPTIONAL MATCH ({})-[:edge]->(m:node), ".format(original_var) +\
        "(o:node)-[:edge]->({}) ".format(original_var) +\
        "WITH COLLECT(m) AS ms, COLLECT(o) AS os, {} ".format(
            ", ".join(carry_vars)) +\
        "FOREACH(o IN os | " +\
        "FOREACH(p IN CASE WHEN NOT o.id IN {} THEN [o] ELSE [] END | ".format(
            "[{}]".format(", ".join(
                "'{}'".format(p) for p in preds_to_ignore))) +\
        "CREATE UNIQUE (p)-[:edge]->({}) )) ".format(clone_var) +\
        "FOREACH(m IN ms | " +\
        "FOREACH(p IN CASE WHEN NOT m.id IN {} THEN [m] ELSE [] END | ".format(
            "[{}]".format(", ".join(
                "'{}'".format(s) for s in sucs_to_ignore))) +\
        "CREATE UNIQUE ({})-[:edge]->(m) )) ".format(clone_var)
    return query, carry_vars


def merging_query(original_vars, merged_var, new_id_var, merged_id=None, carry_vars=None):
    if merged_id is None:
        merged_id = "_".join(original_vars)
    if carry_vars is None:
        carry_vars = set()

    match_edges =\
        " ".join(
            "OPTIONAL MATCH ({})-[:edge]->({}) "
            "OPTIONAL MATCH ({})-[:edge]->({})".format(
                n, "suc_" + n, "pred_" + n, n) for n in original_vars) + " " +\
        " WITH " + ", ".join(
            "COLLECT({}) as sucs_{}, COLLECT({}) as preds_{}".format(
                "suc_" + n, n, "pred_" + n, n) for n in original_vars) + ", " + ", ".join(
                    carry_vars) + " "

    new_node =\
        "OPTIONAL MATCH (same_id_node:node) WHERE same_id_node.id = '{}' ".format(merged_id) +\
        "FOREACH(new_count IN CASE WHEN same_id_node IS NOT NULL AND NOT same_id_node.id IN [{}] ".format(
            ", ".join("{}.id".format(n) for n in original_vars)) +\
        "THEN [coalesce(same_id_node.count, 0) + 1] " +\
        "ELSE [] END | " +\
        "SET same_id_node.count=coalesce(same_id_node.count, 0) + 1 ) " +\
        "WITH same_id_node, " + ", ".join(
            "sucs_{}, preds_{}".format(n, n) for n in original_vars) + ", " + ", ".join(carry_vars) + " " +\
        "UNWIND CASE WHEN same_id_node IS NOT NULL " +\
        "THEN ['{}' + same_id_node.count] ".format(merged_id) +\
        "ELSE ['{}'] END AS {} ".format(merged_id, new_id_var) +\
        "CREATE ({}:node {{ id: {} }}) ".format(merged_var, new_id_var)

    reconnect_edges =\
        " ".join(
            "FOREACH(s IN sucs_{} | CREATE UNIQUE ({})-[:edge]->(s)) ".format(
                n, merged_var) for n in original_vars) +\
        " ".join(
            "FOREACH(p IN preds_{} | CREATE UNIQUE (p)-[:edge]->({})) ".format(
                n, merged_var) for n in original_vars) +\
        "FOREACH(n IN {} | ".format(
            " + ".join("sucs_{} + preds_{}".format(n, n) for n in original_vars)) +\
        "FOREACH(dummy_var IN CASE WHEN n IN [{}] THEN ['dummy'] ELSE [] END | ".format(
            ", ".join(n for n in original_vars)) +\
        "CREATE UNIQUE ({})-[:edge]->({})) )".format(merged_var, merged_var) + " "

    delete_nodes =\
        " DETACH DELETE " + ", ".join(n for n in original_vars) + " "
    for n in original_vars:
        if n != merged_id:
            carry_vars.remove(n)
    carry_vars.add(merged_var)

    query = match_edges + new_node + reconnect_edges + delete_nodes
    return query, carry_vars


def clone_node(node, name=None,
               node_variable=False, clone_variable=None):
    """Clone node in the persistent graph."""

    if name is None:
        query =\
            match_node('x', node) + clonning_query('x', 'new_node', 'uid')[0] +\
            return_vars(['uid'])
    else:
        (query) = (
            "MATCH (original:node) WHERE original.id = '{}' "
            "OPTIONAL MATCH (original)-[:edge]->(m:node), "
            "(o:node)-[:edge]->(original) "
            "WITH COLLECT(m) as sucs, COLLECT(o) as preds "
            "OPTIONAL MATCH (x:node) WHERE x.id = '{}' "
            "FOREACH(new_count IN CASE WHEN x IS NOT NULL "
            "THEN [coalesce(x.count, 0) + 1] "
            "ELSE [] END | "
            "SET x.count=coalesce(x.count, 0) + 1 ) "
            "WITH x, preds, sucs "
            "UNWIND CASE WHEN x IS NOT NULL "
            "THEN ['{}' + x.count] "
            "ELSE ['{}'] END AS new_id "
            "CREATE  (new_node:node {{id : new_id}}) "
            "FOREACH(p in preds | "
            "CREATE UNIQUE (p)-[:edge]->(new_node)) "
            "FOREACH(s in sucs | "
            "CREATE UNIQUE (new_node)-[:edge]->(s)) "
            "RETURN new_id ".format(
                node, name, name, name))
    return query


def merge_nodes(node_list, name=None):
    """Merge nodes in the persistent graph.

    TODO: solve unique id issue as before!
    """
    if name is not None:
        pass
    else:
        name = "_".join(node_list)

    match_nodes =\
        " ".join("MATCH ({}:node {{ id : '{}' }})".format(n, n) for n in node_list) + " "
    match_edges =\
        " ".join(
            "OPTIONAL MATCH ({})-[:edge]->({}) "
            "OPTIONAL MATCH ({})-[:edge]->({})".format(
                n, "suc_" + n, "pred_" + n, n) for n in node_list) + " " +\
        " WITH " + ", ".join(n for n in node_list) + ", " + ", ".join(
            "COLLECT({}) as sucs_{}, COLLECT({}) as preds_{}".format(
                "suc_" + n, n, "pred_" + n, n) for n in node_list) + " "

    new_node = (
        "OPTIONAL MATCH (x:node) WHERE x.id = '{}' ".format(name) +
        "FOREACH(new_count IN CASE WHEN x IS NOT NULL AND NOT x.id IN [{}] ".format(
            ", ".join("'{}'".format(n) for n in node_list)) +
        "THEN [coalesce(x.count, 0) + 1] " +
        "ELSE [] END | " +
        "SET x.count=coalesce(x.count, 0) + 1 ) " +
        "WITH x, " + ", ".join(n for n in node_list) + ", " + ", ".join(
            "sucs_{}, preds_{}".format(n, n) for n in node_list) + " " +
        "UNWIND CASE WHEN x IS NOT NULL "
        "THEN ['{}' + x.count] ".format(name) +
        "ELSE ['{}'] END AS new_id ".format(name) +
        "CREATE (new_node:node { id: new_id }) "
    )
    reconnect_edges = (
        " ".join(
            "FOREACH(s IN sucs_{} | "
            "CREATE UNIQUE (new_node)-[:edge]->(s)) ".format(n) for n in node_list) +\
        " ".join(
            "FOREACH(p IN preds_{} | CREATE UNIQUE (p)-[:edge]->(new_node)) ".format(
                n) for n in node_list) +
        "FOREACH(n IN {} | "
        "FOREACH(x IN CASE WHEN n IN [{}] THEN ['dummy'] ELSE [] END | "
        "CREATE UNIQUE (new_node)-[:edge]->(new_node)) "
        ")".format(
            " + ".join("sucs_{} + preds_{}".format(n, n) for n in node_list),
            ", ".join(n for n in node_list)) + " "
    )
    delete_nodes =\
        " DETACH DELETE " + ", ".join(n for n in node_list)
    query = match_nodes + match_edges +\
        new_node + reconnect_edges + delete_nodes + " RETURN new_id"
    return query


def match(pattern, instance, nodes=None):
    query =\
        match_nodes(instance) + ", " +\
        ", ".join("({})-[{}:edge]->({})".format(u, str(u) + "_" + str(v), v)
                  for u, v in pattern.edges())

    return query


def find_matching(pattern, nodes=None):
    query = (
        "MATCH {}, {} RETURN {}".format(
            ", ".join("({}:node)".format(n) for n in pattern.nodes()),
            ", ".join("({})-[:edge]->({})".format(u, v) for u, v in pattern.edges()),
            ", ".join(pattern.nodes())
        )
    )
    return query
