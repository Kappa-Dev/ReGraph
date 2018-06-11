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

    query1 =\
        "\n//We copy the nodes of B in D\n" +\
        cypher.clone_graph(b, d, attach=True)[0]

    query2 =\
        "\n//We create the images of the exclusive nodes of C\n" +\
        "MATCH (m:node:{})\n".format(c) +\
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

    query3 =\
        "OPTIONAL MATCH " + c_to_d.format("m", c, a, b, "x", d) + "\n" +\
        "WHERE x IS NOT NULL\n" +\
        "MERGE (m)-[:typing]->(x)" +\
        cypher.merge_properties(["m", "x"], 'new_props',
                                method='union') +\
        "SET x += new_props\n" +\
        "SET x.id = toString(id(x))\n"

    query4 =\
        "OPTIONAL MATCH (x:node:{})<-[:typing]-(:node:{})-[rel_c:edge]->(:node:{})-[:typing]->(y:node:{})\n".format(
            d, c, c, d) +\
        "WHERE rel_c IS NOT NULL\n" +\
        "OPTIONAL MATCH (x)-[rel_d:edge]->(y)\n" +\
        "FOREACH(ignoreMe IN CASE WHEN rel_d IS NULL THEN [1] ELSE [] END |\n" +\
        "\tMERGE (x)-[new_rel:edge]->(y)\n" +\
        "\tON CREATE SET new_rel = properties(rel_c) )\n" +\
        "WITH rel_c, rel_d\n" +\
        "WHERE rel_d IS NOT NULL\n" +\
        cypher.merge_properties(["rel_c", "rel_d"], 'new_props',
                                method='union') +\
        "SET rel_d += new_props\n"

    carry_vars = set()

    query5 =\
        "\n//We search for all the nodes in D that we need to merge\n" +\
        "OPTIONAL MATCH (n:{})<-[:typing]-(:{})<-[:typing]-(:{})-[:typing]->(m:{})\n".format(
            d, b, a, c) +\
        "WITH collect(n) as nodes_to_merge, m\n"
    carry_vars.update(["m", "nodes_to_merge"])
    query5 +=\
        "WITH nodes_to_merge[0] as node1, size(nodes_to_merge) as number_of_nodes," +\
        ", ".join(carry_vars) + "\n" +\
        "WHERE number_of_nodes <> 1\n"
    carry_vars.update(["number_of_nodes", "node1"])
    query5 +=\
        "\n//We merge the nodes in D that need to be merged\n" +\
        "UNWIND nodes_to_merge[1..] AS node2\n"
    carry_vars.add("node2")
    query5 +=\
        cypher.merging_query2(original_vars=["node1", "node2"],
                              merged_var="merged_node",
                              merged_id="id",
                              merged_id_var="new_id",
                              node_label='node:'+d,
                              edge_label=None,
                              carry_vars=carry_vars,
                              ignore_naming=True,
                              multiple_rows=True)[0] + "\n" +\
        "RETURN merged_node.id"

    return query1, query2, query3, query4, query5


def pullback_complement(a, b, d, c=None, inplace=False):
    pass


def check_homomorphism(domain, codomain, total=True):
    pass


def graph_predecessors_query(graph):
    """Generate query for getting the labels of the predecessors of a graph."""
    query = cypher.match_node(
                        var_name='g',
                        node_id=graph,
                        label='hierarchyNode')
    query += (
        "OPTIONAL MATCH (predecessor)-[:hierarchyEdge]->(g)\n"
        "RETURN collect(predecessor.id)"
        )
    return query


def graph_successors_query(graph):
    """Generate query for getting the labels of the successors of a graph."""
    query = ""
    query += cypher.match_node(
                        var_name='g',
                        node_id=graph,
                        label='hierarchyNode')
    query += (
        "OPTIONAL MATCH (g)-[:hierarchyEdge]->(successor)\n"
        "RETURN collect(successor.id)"
        )
    return query


def propagate_up(rewritten_graph, predecessor):
    """Generate the queries for propagating the changes up from H-->G.

    Returns
    -------
    query1 : str
        Generated query for removing nodes from H
    query2 : str
        Generated query for removing nodes from H
    query3 : str
    Generated query for cloning nodes in H
    """
    query1 = (
        "OPTIONAL MATCH (n:node:{})\n".format(predecessor) +
        "WHERE NOT (n)-[:typing]->(:node:{})\n".format(rewritten_graph) +
        "DETACH DELETE n\n"
        )

    query2 = (
        "OPTIONAL MATCH (n:node:{})-[rel_pred:edge]->(m:node:{})\n".format(
            predecessor, predecessor) +
        "WHERE rel_pred IS NOT NULL\n" +
        "OPTIONAL MATCH (n)-[:typing]->(:node:{})-[rel:edge]->(:node:{})<-[:typing]-(m)\n".format(
            rewritten_graph, rewritten_graph) +
        "WITH rel_pred WHERE rel IS NULL\n" +
        "WITH DISTINCT rel_pred\n" +
        "DELETE rel_pred"
        )

    carry_vars = set()
    query3 = (
        "OPTIONAL MATCH (node_to_clone:node:{})-[t:typing]->(n:node:{})\n".format(
            predecessor, rewritten_graph) +
        "WITH node_to_clone, collect(n) as sucs, collect(t) as typ_sucs\n" +
        "WHERE node_to_clone IS NOT NULL AND size(sucs) >= 2\n"
        "FOREACH(t IN typ_sucs | DELETE t)\n" +
        "WITH node_to_clone, sucs, sucs[0] as suc1\n"
        )
    carry_vars.update(['node_to_clone', 'suc1', 'node_suc'])
    query3 += (
        "UNWIND sucs[1..] AS node_suc" +
        cypher.cloning_query1(
                    original_var='node_to_clone',
                    clone_var='cloned_node',
                    clone_id='clone_id',
                    clone_id_var='clone_id_var',
                    original_graph=predecessor,
                    carry_vars=carry_vars,
                    preserv_typing=True,
                    ignore_naming=True)[0] +
        cypher.with_vars(carry_vars) + "\n" +
        "MERGE (cloned_node)-[:typing]->(node_suc)\n" +
        "MERGE (node_to_clone)-[:typing]->(suc1)\n"
        )

    return query1, query2, query3


def propagate_down(rewritten_graph, successor):
    """Generate the queries for propagating the changes down from G-->T.

    Returns
    -------
    query1 : str
        Generated query for adding nodes in T
    query2 : str
        Generated query for adding edges in T
    query3 : str
    Generated query for merging nodes in H
    """
    query1 = (
        "OPTIONAL MATCH (n:node:{})".format(rewritten_graph) +
        "WHERE NOT (n)-[:typing]->(:node:{})\n".format(successor) +
        "MERGE (n)-[:typing]->(new_node:node:{})\n".format(successor) +
        "ON CREATE SET new_node += properties(n)\n" +
        "ON CREATE SET new_node.id = id(new_node)\n"
        )

    query2 = (
        "OPTIONAL MATCH (n:node:{})<-[:typing]-(:node:{})-[rel:edge]->(:node:{})-[:typing]->(m:node:{})\n".format(
            successor, rewritten_graph, rewritten_graph, successor) +
        "WHERE NOT (n)-[:edge]->(m)\n" +
        "MERGE (n)-[new_rel:edge]->(m)\n" +
        "ON CREATE SET new_rel += properties(rel)\n"
        )

    query3 = (
        "OPTIONAL MATCH (n:node:{})-[:typing]->(node_to_merge:node:{})\n".format(
            rewritten_graph, successor) +
        "WITH n, collect(node_to_merge) as nodes_to_merge\n" +
        "WHERE n IS NOT NULL AND size(nodes_to_merge) >= 2\n" +
        "WITH n, nodes_to_merge, nodes_to_merge[0] as node1\n"
        )
    query3 += (
        "UNWIND nodes_to_merge[1..] as node2\n" +
        cypher.merging_query2(
                    original_vars=["node1", "node2"],
                    merged_var="merged_node",
                    merged_id="id",
                    merged_id_var="new_id",
                    node_label='node:'+successor,
                    edge_label=None,
                    ignore_naming=True,
                    multiple_rows=True)[0] +
        "RETURN merged_node.id\n"
        )

    return query1, query2, query3
