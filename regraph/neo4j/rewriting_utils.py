import regraph.neo4j.cypher_utils as cypher


def propagate_up(tx, rewritten_graph, predecessor):
    """Generate the queries for propagating the changes up from H-->G.

    Returns
    -------
    query1 : str
        Generated query for removing nodes from H
    query2 : str
        Generated query for removing nodes from H
    query3_1 : str
        Generated query for matching the nodes to clone in H
    query3 : str
        Generated query for cloning nodes in H, depending on their ids
    """
    # We remove the nodes of H without image in G
    query1 = (
        "// Removal of nodes in '{}'\n".format(predecessor) +
        "MATCH (n:node:{})\n".format(predecessor) +
        "WHERE NOT (n)-[:typing]->(:node:{})\n".format(rewritten_graph) +
        "DETACH DELETE n\n\n"
        )
    tx.run(query1)

    # We remove the edges without image in G
    query2 = (
        "// Removal of edges in '{}'\n".format(predecessor) +
        "MATCH (n:node:{})-[rel_pred:edge]->(m:node:{})\n".format(
            predecessor, predecessor) +
        "OPTIONAL MATCH (n)-[:typing]->(:node:{})-[rel:edge]->(:node:{})<-[:typing]-(m)\n".format(
            rewritten_graph, rewritten_graph) +
        "WITH rel_pred WHERE rel IS NULL\n" +
        "WITH DISTINCT rel_pred\n" +
        "DELETE rel_pred\n\n"
        )
    tx.run(query2)

    # We clone the nodes that have more than 1 image and
    # reassign the typing edges
    carry_vars = set()
    query3_1 = (
        "// Matching of the nodes to clone in '{}'\n".format(predecessor) +
        "MATCH (node_to_clone:node:{})-[:typing]->(n:node:{})\n".format(
            predecessor, rewritten_graph) +
        "WITH node_to_clone, collect(n) as sucs\n" +
        "WHERE size(sucs) >= 2\n" +
        "RETURN node_to_clone.id as node_id\n"
        )
    query3 = (
        "// Cloning of the node '$id' of the graph '{}'\n".format(predecessor) +
        "MATCH (node_to_clone:node:{}) WHERE node_to_clone.id = $id\n".format(
                    predecessor) +
        "MATCH (node_to_clone)-[t:typing]->(n:node:{})\n".format(
                    rewritten_graph) +
        "WITH node_to_clone, collect(n) as sucs, collect(t) as typ_sucs\n" +
        "FOREACH(t IN typ_sucs | DELETE t)\n" +
        "WITH node_to_clone, sucs, sucs[0] as suc1\n"
        )
    carry_vars.update(['node_to_clone', 'suc1', 'node_suc'])
    query3 += (
        "UNWIND sucs[1..] AS node_suc\n" +
        cypher.cloning_query(
                    original_var='node_to_clone',
                    clone_var='cloned_node',
                    clone_id='clone_id',
                    clone_id_var='clone_id_var',
                    node_label='node:'+predecessor,
                    preserv_typing=True,
                    carry_vars=carry_vars,
                    ignore_naming=True)[0] +
        cypher.with_vars(carry_vars) + "\n" +
        "MERGE (cloned_node)-[:typing]->(node_suc)\n" +
        "MERGE (node_to_clone)-[:typing]->(suc1)\n"
        )
    result = tx.run(query3_1)
    for record in result:
        node_id = record['node_id']
        tx.run(query3, id=node_id)

    return query1, query2, query3_1, query3


def propagate_down(tx, rewritten_graph, successor):
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
    # add nodes in T for each node without image in G
    query1 = (
        "// Addition of nodes in '{}'\n".format(successor) +
        "MATCH (n:node:{})".format(rewritten_graph) +
        "WHERE NOT (n)-[:typing]->(:node:{})\n".format(successor) +
        "MERGE (n)-[:typing]->(new_node:node:{})\n".format(successor) +
        "ON CREATE SET new_node += properties(n)\n" +
        "ON CREATE SET new_node.id = id(new_node)\n"
        )
    tx.run(query1)

    # add edges in T for each edge without image in G
    query2 = (
        "// Addition of edges in '{}'\n".format(successor) +
        "MATCH (n:node:{})<-[:typing]-(:node:{})-[rel:edge]->(:node:{})-[:typing]->(m:node:{})\n".format(
            successor, rewritten_graph, rewritten_graph, successor) +
        "WHERE NOT (n)-[:edge]->(m)\n" +
        "MERGE (n)-[new_rel:edge]->(m)\n" +
        "ON CREATE SET new_rel += properties(rel)\n"
        )
    tx.run(query2)

    # match nodes of T with the same pre-image in G and merge them
    query3 = (
        "// Matching of the nodes to merge in '{}'\n".format(successor) +
        "MATCH (n:node:{})-[:typing]->(node_to_merge:node:{})\n".format(
            rewritten_graph, successor) +
        "WITH n, collect(node_to_merge.id) as nodes_to_merge\n" +
        "WHERE n IS NOT NULL AND size(nodes_to_merge) >= 2\n" +
        "RETURN n, nodes_to_merge\n"
        )
    result = tx.run(query3)

    for record in result:
        nodes_to_merge = record['nodes_to_merge']
        query = (
            "// Merging of the nodes {}\n".format(
                ", ".join(nodes_to_merge)) +
            cypher.match_nodes(
                        var_id_dict={n: n for n in nodes_to_merge},
                        label='node:'+successor) + "\n" +
            cypher.merging_query(
                        original_vars=nodes_to_merge,
                        merged_var='merged_node',
                        merged_id='id',
                        merged_id_var='new_id',
                        node_label='node:'+successor,
                        edge_label=None,
                        ignore_naming=True)[0] + "\n" +
            cypher.return_vars(['new_id'])
            )
        tx.run(query)
    """
    query3 += (
        "WITH n, nodes_to_merge, nodes_to_merge[0] as node1\n" +
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
    """
    return query1, query2, query3
