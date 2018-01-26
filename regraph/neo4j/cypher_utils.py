"""Collection of Cypher utils."""


def add_node(node, attrs=None):
    return add_nodes_from([node])


def add_edge(source, target, attrs=None):
    return add_edges_from([(source, target)])


def remove_node(node):
    query = ("MATCH (n:node) WHERE n.id='{}' "
             "OPTIONAL MATCH (n)-[r:edge]->(m)"
             "DELETE n, r".format(node))
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


def get_nodes():
    query = "MATCH (n) RETURN n.id"
    return query


def get_edges():
    query = "MATCH (n)-[r]->(m) RETURN n.id, m.id"
    return query


def copy_node(node):
    """Copy node in the persistent graph."""
    pass


def relabel_node(node_id, new_id):
    """Relabel a node in the graph."""
    i = 1
    new_node = str(node_id) + str(i)
    while new_node in graph.nodes():
        i += 1
        new_node = str(node_id) + str(i)


def generate_new_name(prefix=None):
    pass


def clone_node(node, name=None):
    """Clone node in the persistent graph."""
    if name is None:
        # Generate new id
        (create_clone) = (
            "MATCH (x:node {{ id : '{}' }}) "
            "SET x.count = coalesce(x.count, 0) + 1 "
            "WITH '{}' + x.count AS uid, x "
            "CREATE (new_node:node {{ id : uid }}) "
            "WITH new_node, x "
            "OPTIONAL MATCH (x)-[:edge]->(m:node), "
            "(o:node)-[:edge]->(x) "
            "CREATE UNIQUE (new_node)-[:edge]->(m), "
            "(o)-[:edge]->(new_node) ".format(node, node, node)
        )
    else:
        (create_clone) = (
            "MATCH (original:node) WHERE original.id = '{}' "
            "OPTIONAL MATCH (original)-[:edge]->(m:node), "
            "(o:node)-[:edge]->(original) "
            "WITH COLLECT(m) as sucs, COLLECT(o) as preds "
            "OPTIONAL MATCH (x:node) WHERE x.id = '{}' "
            "FOREACH(new_count IN CASE WHEN x IS NOT NULL "
            "THEN [coalesce(x.count, 0) + 1] "
            "ELSE [] END | "
            "SET x.count=coalesce(x.count, 0) + 1 ) "
            "FOREACH(new_id IN CASE WHEN x IS NOT NULL "
            "THEN ['{}' + x.count] "
            "ELSE ['{}'] END | "
            "CREATE  (new_node:node {{id : new_id}}) "
            "FOREACH(p in preds | "
            "CREATE UNIQUE (p)-[:edge]->(new_node)) "
            "FOREACH(s in sucs | "
            "CREATE UNIQUE (new_node)-[:edge]->(s))"
            ") ".format(
                node, name, name, name))
    reconnect_edges = ""
    query = create_clone + reconnect_edges
    return query


def merge_nodes(node_list, name=None):
    """Merge nodes in the persistent graph."""
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
    new_node = "CREATE ({}:node {{ id: '{}' }}) ".format(name, name)
    reconnect_edges = (
        " ".join(
            "FOREACH(s IN sucs_{} | "
            "CREATE UNIQUE ({})-[:edge]->(s)) ".format(
                n, name) for n in node_list) +\
        " ".join(
            "FOREACH(p IN preds_{} | CREATE UNIQUE (p)-[:edge]->({})) ".format(
                n, name) for n in node_list) +\
        "FOREACH(n IN {} | "
        "FOREACH(x IN CASE WHEN n IN [{}] THEN ['dummy'] ELSE [] END | "
        "CREATE UNIQUE ({})-[:edge]->({})) "
        ")".format(
            " + ".join("sucs_{} + preds_{}".format(n, n) for n in node_list),
            ", ".join(n for n in node_list),
            name, name) + " "
    )
    delete_nodes =\
        " DETACH DELETE " + ", ".join(n for n in node_list)
    query = match_nodes + match_edges +\
        new_node + reconnect_edges + delete_nodes
    return query


def find_matching(pattern, nodes=None):
    pass
