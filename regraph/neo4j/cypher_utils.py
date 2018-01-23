"""Collection of Cypher utils."""


def add_node(node, attrs=None):
    return add_nodes_from([node])

def add_edge(source, target, attrs=None):
    return add_edges_from([(source, target)])


def remove_node(node):
    query = "MATCH {} WHERE {} DELETE {}".format(
            "({})".format(n),
            "{}.id = '{}'".format(n, n),
            n
        )
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


def create_graph(nodes, edges=None):
    """Generate Cypher query for graph creation."""
    query = nodes_statement
    if edges is not None and len(edges) > 0:
        query += ", " + edges_statement
    return query


def clear_graph():
    (query) = (
        "MATCH (n)"
        "OPTIONAL MATCH (n)-[r]-()"
        "DELETE n, r"
    )
    return query

def nodes():
    query = "MATCH (n) RETURN n.id"
    return query

def edges():
    query = "MATCH (n)-[r]->(m) RETURN n.id, m.id"
    return query