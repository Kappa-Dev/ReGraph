"""Category operations used by neo4j graph rewriting tool."""

import regraph.neo4j.cypher_utils as cypher


def pullback(b, c, d, a=None, inplace=False):
    """Find the pullback from b -> d <- c.

    Returns
    -------
    query1 : str
        Generated query for creating all the nodes in A
        and the typing edges
    query2 : str
        Generated query for creating all the edges of A
    """
    if a is None:
        a = "pb_" + "_".join([b, c, d])
    query1 = ""
    carry_vars = set()

    # Match all the pair of nodes with the same image in d
    query1 +=\
        "OPTIONAL MATCH (n:{})-[:typing]->(:{})<-[:typing]-(m:{})\n".format(
            b, d, c)

    # For each pair, collect all the merged properties
    query1 += cypher.merge_properties(["n", "m"], 'new_props',
                                      method='intersection',
                                      carry_vars=carry_vars)
    # For each pair, create a new node
    query1 += cypher.create_node(
                        var_name="new_node_a",
                        node_id="pb",
                        node_id_var="id_var",
                        label='node:'+a,
                        carry_vars=carry_vars,
                        ignore_naming=True)[0]
    carry_vars.remove("id_var")
    query1 += "SET new_node_a += new_props\n"
    carry_vars.remove("new_props")

    # Add the typing edges
    query1 += cypher.with_vars(carry_vars) + "\n"
    query1 += cypher.create_edge('new_node_a', 'n', edge_label='typing') + "\n"
    query1 += cypher.create_edge('new_node_a', 'm', edge_label='typing') + "\n"

    # Add the graph edges
    carry_vars = set()
    query2 = ""
    query2 +=\
        "OPTIONAL MATCH (x:{})-[:typing]->(:{})-[r1:edge]->(:{})<-[:typing]-(y:{}),\n".format(
            a, b, b, a) +\
        "(x)-[:typing]->(:{})-[r2:edge]->(:{})<-[:typing]-(y)\n".format(
            c, c)
    # Collect all the merged properties of the edges r1 and r2
    query2 += cypher.merge_properties(["r1", "r2"], 'new_props',
                                      method='intersection',
                                      carry_vars={'x', 'y'})
    query2 += "MERGE (x)-[r:edge]->(y)\n"
    query2 += "SET r += new_props"

    return query1, query2


def pushout(a, b, c, d=None, inplace=False):
    """Find the pushout of the span b <- a -> c.

    Returns
    -------
    query1 : str
        Generated query for copying the nodes of B in D
    query2 : str
        Generated query for creating the exclusive images
        (nodes of D) of the nodes of C
    query3 : str
        Generated query for merging the nodes in D that need
        to be merged
    query4 : str
        Generated query for creating all the edges of D
    """
    if d is None:
        d = "pb_" + "_".join([a, b, c])
    carry_vars = set()

    query1 =\
        "\n//We copy the nodes of B in D\n" +\
        cypher.clone_graph(b, d, attach=True, carry_vars=carry_vars)[0]

    query12 =\
        "OPTIONAL MATCH (n:{})<-[:typing]-(:{})-[r:edge]->(:{})-[:typing]->(m:{})".format(
            d, b, b, d) + "\n" +\
        "WHERE r IS NOT NULL\n" +\
        "MERGE (n)-[new_rel:edge]->(m)\n" +\
        "ON CREATE SET new_rel += properties(r)"

    query13 =\
        "OPTIONAL MATCH (n:{})<-[:typing]-(m:{})-[r:edge]->(m)\n".format(
            d, b, b) +\
        "WHERE r IS NOT NULL\n" +\
        "MERGE (n)-[new_rel:edge]->(n)\n" +\
        "ON CREATE SET new_rel += properties(r)"

    query2 =\
        "\n//We create the images of the exclusive nodes of C\n" +\
        "MATCH (m:{})\n".format(c) +\
        "WHERE NOT (m)<-[:typing]-(:{})\n".format(a) +\
        cypher.create_node(
                        var_name="new_node_d",
                        node_id="pb",
                        node_id_var="id_var",
                        label='node:'+d,
                        carry_vars={"m"},
                        ignore_naming=True)[0] +\
        "SET new_node_d += properties(m)\n" +\
        "SET new_node_d.id = id(new_node_d)\n" +\
        "MERGE (m)-[:typing]->(new_node_d) \n"
    carry_vars = set()

    query3 =\
        "\n//We search for all the nodes in C with at least 1 equivalent in D\n" +\
        "OPTIONAL MATCH (n:{})<-[:typing]-(:{})<-[:typing]-(:{})-[:typing]->(m:{})\n".format(
            d, b, a, c) +\
        "WITH collect(n) as nodes_to_merge, m\n" +\
        "WITH m, nodes_to_merge, size(nodes_to_merge) as number_of_nodes\n"
    carry_vars.update(["m", "nodes_to_merge", "number_of_nodes"])
    query3 +=\
        "WITH nodes_to_merge[0] as node1, " + ", ".join(carry_vars) + "\n"
    carry_vars.add("node1")
    query3 +=\
        "\n//We merge the nodes in D that need to be merged\n" +\
        "MERGE (m)-[:typing]->(node1)\n" +\
        cypher.with_vars(carry_vars) + "\n" +\
        "WHERE number_of_nodes <> 1\n" +\
        "UNWIND nodes_to_merge[1..] AS node2\n" +\
        cypher.merging_query(original_vars=["node1", "node2"],
                             merged_var="merged_node",
                             merged_id="id",
                             merged_id_var="new_id",
                             node_label='node:'+d,
                             edge_label=None,
                             carry_vars={"m", "node1", "node2"},
                             ignore_naming=True)[0] + "\n" +\
        cypher.return_vars(['new_id'])

    query4 =\
        "\n//We create the edges of D\n" +\
        "MATCH (x:{}), (y:{})\n".format(d, d) +\
        "WITH x, y, [] as new_props\n" +\
        "OPTIONAL MATCH (x)<-[:typing]-()-[r:edge]->()-[:typing]->(y)\n" +\
        "WITH x, y, collect(r) as BC_rel WHERE size(BC_rel)<>0\n" +\
        "WITH x, y, BC_rel, BC_rel[0] as rel1, size(BC_rel) AS nb_rel\n" +\
        "MERGE (x)-[new_rel:edge]->(y)\n" +\
        "SET new_rel += properties(rel1)\n" +\
        "WITH BC_rel, new_rel, nb_rel\n" +\
        "UNWIND range(1, nb_rel-1) AS i\n" +\
        "WITH BC_rel, new_rel, BC_rel[i] as rel2\n" +\
        cypher.merge_properties(["new_rel", "rel2"], "new_props",
                                carry_vars={"BC_rel"},
                                method='union') +\
        "SET new_rel += new_props\n"

    return query1, query2, query3, query4


def pullback_complement(a, b, d, c=None, inplace=False):
    pass


def check_homomorphism(domain, codomain, total=True):
    pass
