"""Collection of Cypher utils."""


def add_node(node, attrs=None):
    pass


def add_edge(node, attrs=None):
    pass


def remove_node(node):
    pass


def remove_edge(node):
    pass


def add_nodes_from(nodes):
    pass


def add_edges_from(edges):
    pass


def create_graph(nodes, edges=None):
    """Generate Cypher query for graph creation."""
    nodes_statement = "CREATE {}".format(
        ", ".join("({}:node {{ id : '{}' }})".format(n, n) for n in nodes))
    edges_statement = ", ".join(
        "({})-[:edge]->({})".format(u, v) for u, v in edges)
    query = nodes_statement
    if edges is not None and len(edges) > 0:
        query += ", " + edges_statement
    print(query)
    return query


def clear_graph():
    (query) = (
        "MATCH (n)"
        "OPTIONAL MATCH (n)-[r]-()"
        "DELETE n,r"
    )
    return query
