"""Category operations used by neo4j graph rewriting tool."""

import regraph.neo4j.cypher_utils as cypher

from regraph.default.exceptions import (InvalidHomomorphism)


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

    carry_vars = set()

    # Match all the pair of nodes with the same image in d
    query1 = "MATCH (n:{})-[:typing]->(:{})<-[:typing]-(m:{})\n".format(
                    b, d, c)
    # For each pair, collect all the merged properties
    # create a new node and set the properties
    query1 += (
        cypher.merge_properties(
                    var_list=["n", "m"],
                    new_props_var='new_props',
                    method='intersection',
                    carry_vars=carry_vars) +
        cypher.create_node(
                    var_name="new_node_a",
                    node_id="pb",
                    node_id_var="id_var",
                    label='node:'+a,
                    carry_vars=carry_vars,
                    ignore_naming=True)[0] +
        "SET new_node_a += new_props\n" +
        "SET new_node_a.id = toString(id(new_node_a))\n"
        )
    carry_vars.remove("id_var")
    carry_vars.remove("new_props")
    # Add the typing edges
    query1 += (
        cypher.with_vars(carry_vars) + "\n" +
        cypher.create_edge(
                    edge_var='new_typing_to_n',
                    source_var='new_node_a',
                    target_var='n',
                    edge_label='typing') + "\n" +
        cypher.create_edge(
                    edge_var='new_typing_to_m',
                    source_var='new_node_a',
                    target_var='m',
                    edge_label='typing') + "\n"
        )

    # Add the graph edges
    carry_vars = set()
    query2 = (
        "MATCH (x:{})-[:typing]->(:{})-[r1:edge]->(:{})<-[:typing]-(y:{}),\n".format(
                    a, b, b, a) +
        "(x)-[:typing]->(:{})-[r2:edge]->(:{})<-[:typing]-(y)\n".format(
                    c, c)
        )
    # Collect all the merged properties of the edges r1 and r2
    query2 += (
        cypher.merge_properties(
                    var_list=["r1", "r2"],
                    new_props_var='new_props',
                    method='intersection',
                    carry_vars={'x', 'y'}) +
        "MERGE (x)-[r:edge]->(y)\n" +
        "SET r += new_props"
        )

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
        Generated query for adding the typing edges between C and D
    query4 : str
        Generated query for adding edges of C in D
    query5 : str
        Generated query for merging the nodes in D that need
        to be merged
    """
    if d is None:
        d = "pb_" + "_".join([a, b, c])
    carry_vars = set()

    c_to_d = "({}:node:{})<-[:typing]-(:node:{})-[:typing]->(:node:{})-[:typing]->({}:node:{})"

    query1 = (
        "\n// We copy the nodes of B in D\n" +
        cypher.clone_graph(
                    original_graph=b,
                    cloned_graph=d)[0]
        )

    query2 = (
        "\n// We create the images of the exclusive nodes of C\n" +
        "MATCH (m:node:{})\n".format(c) +
        "WHERE NOT (m)<-[:typing]-(:{})\n".format(a) +
        cypher.create_node(
                    var_name="new_node_d",
                    node_id="pb",
                    node_id_var="id_var",
                    label='node:'+d,
                    carry_vars={"m"},
                    ignore_naming=True)[0] +
        "SET new_node_d += properties(m)\n" +
        "SET new_node_d.id = toString(id(new_node_d))\n" +
        cypher.create_edge(
                    edge_var='new_typing',
                    source_var='m',
                    target_var='new_node_d',
                    edge_label='typing')
        )

    query3 = (
        "\n// We add the missing typing edges between C and D " +
        "and merge the properties\n" +
        "MATCH " + c_to_d.format("m", c, a, b, "x", d) + "\n" +
        cypher.create_edge(
                    edge_var='new_typing',
                    source_var='m',
                    target_var='x',
                    edge_label='typing') +
        cypher.merge_properties(
                    var_list=["m", "x"],
                    new_props_var='new_props',
                    method='union') +
        "SET x += new_props\n" +
        "SET x.id = toString(id(x))\n"
        )

    query4 = (
        "\n// We add the edges of C in D\n" +
        "MATCH (x:node:{})<-[:typing]-(:node:{})-[rel_c:edge]->(:node:{})-[:typing]->(y:node:{})\n".format(
                    d, c, c, d) +
        "OPTIONAL MATCH (x)-[rel_d:edge]->(y)\n" +
        "FOREACH(_ IN CASE WHEN rel_d IS NULL THEN [1] ELSE [] END |\n" +
        "\tMERGE (x)-[new_rel:edge]->(y)\n" +
        "\tON CREATE SET new_rel = properties(rel_c) )\n" +
        cypher.with_vars(['rel_c', 'rel_d']) + "\n" +
        "WHERE rel_d IS NOT NULL\n" +
        cypher.merge_properties(
                    var_list=["rel_c", "rel_d"],
                    new_props_var='new_props',
                    method='union') +
        "SET rel_d += new_props\n"
        )

    carry_vars = set()

    query5 = (
        "\n//We search for all the nodes in D that we need to merge\n" +
        "MATCH (n:{})<-[:typing]-(:{})<-[:typing]-(:{})-[:typing]->(m:{})\n".format(
                    d, b, a, c) +
        "WITH collect(n) as nodes_to_merge, m\n"
        )
    carry_vars.update(["m", "nodes_to_merge"])
    query5 += (
        "WITH nodes_to_merge[0] as node1, size(nodes_to_merge) as number_of_nodes," +
        ", ".join(carry_vars) + "\n" +
        "WHERE number_of_nodes <> 1\n"
        )
    carry_vars.update(["number_of_nodes", "node1"])
    query5 += (
        "\n//We merge the nodes in D that need to be merged\n" +
        "UNWIND nodes_to_merge[1..] AS node2\n"
        )
    carry_vars.add("node2")
    query5 += (
        cypher.merging_query2(
                    original_vars=["node1", "node2"],
                    merged_var="merged_node",
                    merged_id="id",
                    merged_id_var="new_id",
                    node_label='node:'+d,
                    edge_label=None,
                    carry_vars=carry_vars,
                    ignore_naming=True,
                    multiple_rows=True)[0] + "\n" +
        cypher.return_vars(["merged_node.id"])
        )

    return query1, query2, query3, query4, query5


def pullback_complement(a, b, d, c=None, inplace=False):
    pass


def check_homomorphism(tx, domain, codomain, total=True):
    """Check if the homomorphism is valid."""

    # Check if all the nodes of the domain have exactly 1 image
    query1 = (
        "MATCH (n:node:{})\n".format(domain) +
        "OPTIONAL MATCH (n)-[:typing]->(m:node:{})\n".format(codomain) +
        "WITH n, collect(m) as images\n" +
        "WHERE size(images) <> 1\n" +
        "RETURN n.id as ids, size(images) as nb_of_img\n"
        )
    result = tx.run(query1)
    nodes = []
    for record in result:
        nodes.append((record['ids'], record['nb_of_img']))
    if len(nodes) != 0:
        raise InvalidHomomorphism(
            "Wrong number of images!\n" +
            "\n".join(
                ["The node '{}' of the graph {} have {} image(s) in the graph {}.".format(
                    n, domain, str(nb), codomain) for n, nb in nodes]
                )
            )

    query2 = (
        "MATCH (n:node:{})-[:edge]->(m:node:{})\n".format(
            domain, domain) +
        "MATCH (n)-[:typing]->(x:node:{}), (y:node:{})<-[:typing]-(m)\n".format(
            codomain, codomain) +
        "OPTIONAL MATCH (x)-[r:edge]->(y)\n" +
        "WITH x.id as x_id, y.id as y_id, r\n" +
        "WHERE r IS NULL\n" +
        "WITH x_id, y_id, collect(r) as rs\n" +
        "RETURN x_id, y_id\n"
        )
    result = tx.run(query2)
    xy_ids = []
    for record in result:
        xy_ids.append((record['x_id'], record['y_id']))
    if len(xy_ids) != 0:
        raise InvalidHomomorphism(
            "Connectivity is not preserved!\n" +
            "\n".join([" Was expecting an edge between '{}' and '{}'.".format(
                x, y) for x, y in xy_ids])
            )

    query3 = (
        "MATCH (n:node:{})-[:typing]->(m:node:{})\n".format(
                domain, codomain) +
        "WITH properties(n) as n_props, properties(m) as m_props, " +
        "n.id as n_id, m.id as m_id\n" +
        "WITH REDUCE(invalid = 0, k in filter(k in keys(n_props) WHERE k <> 'id') |\n" +
        "\tinvalid + CASE\n" +
        "\t\tWHEN NOT k IN keys(m_props) THEN 1\n" +
        "\t\tELSE REDUCE(invalid_values = 0, v in n_props[k] |\n" +
        "\t\t\tinvalid_values + CASE\n" +
        "\t\t\t\tWHEN NOT v IN m_props[k] THEN 1 ELSE 0 END)\n" +
        "\t\tEND) AS invalid, n_id, m_id\n" +
        "WHERE invalid <> 0\n" +
        "RETURN n_id, m_id, invalid\n"
        )
    result = tx.run(query3)
    invalid_typings = []
    for record in result:
        invalid_typings.append((record['n_id'], record['m_id']))
    if len(invalid_typings) != 0:
        raise InvalidHomomorphism(
            "Node properties are not preserved!\n" +
            "\n".join(["Properties of nodes source: '{}'".format(n) +
                       "and target: '{}' do not match!".format(m)
                       for n, m in invalid_typings])
            )

    query4 = (
        "MATCH (n:node:{})-[rel_orig:edge]->(m:node:{})\n".format(
            domain, domain) +
        "MATCH (n)-[:typing]->(x:node:{}), (y:node:{})<-[:typing]-(m)\n".format(
            codomain, codomain) +
        "MATCH (x)-[rel_img:edge]->(y)\n" +
        "WITH n.id as n_id, m.id as m_id, x.id as x_id, y.id as y_id, " +
        "properties(rel_orig) as rel_orig_props, " +
        "properties(rel_img) as rel_img_props\n" +
        "WITH REDUCE(invalid = 0, k in keys(rel_orig_props) |\n" +
        "\tinvalid + CASE\n" +
        "\t\tWHEN NOT k IN keys(rel_img_props) THEN 1\n" +
        "\t\tELSE REDUCE(invalid_values = 0, v in rel_orig_props[k] |\n" +
        "\t\t\tinvalid_values + CASE\n" +
        "\t\t\t\tWHEN NOT v IN rel_img_props[k] THEN 1 ELSE 0 END)\n" +
        "\t\tEND) AS invalid, n_id, m_id, x_id, y_id\n" +
        "WHERE invalid <> 0\n" +
        "RETURN n_id, m_id, x_id, y_id, invalid\n"
        )
    result = tx.run(query4)
    invalid_edges = []
    for record in result:
        invalid_edges.append((record['n_id'], record['m_id'],
                              record['x_id'], record['y_id']))
    if len(invalid_edges) != 0:
        raise InvalidHomomorphism(
            "Edge properties are not preserved!\n" +
            "\n".join(["Properties of edges ({})->({})".format(n, m) +
                       "and ({})->({}) do not match!".format(x, y)
                       for n, m, x, y in invalid_edges])
            )

    return True


def check_consistency(tx, source, target):
    pass
