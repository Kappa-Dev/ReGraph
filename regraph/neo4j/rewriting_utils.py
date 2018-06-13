import regraph.neo4j.cypher_utils as cypher


def propagate_up(rewritten_graph, predecessor):
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
    query1 = (
        "MATCH (n:node:{})\n".format(predecessor) +
        "WHERE NOT (n)-[:typing]->(:node:{})\n".format(rewritten_graph) +
        "DETACH DELETE n\n"
        )

    query2 = (
        "MATCH (n:node:{})-[rel_pred:edge]->(m:node:{})\n".format(
            predecessor, predecessor) +
        "OPTIONAL MATCH (n)-[:typing]->(:node:{})-[rel:edge]->(:node:{})<-[:typing]-(m)\n".format(
            rewritten_graph, rewritten_graph) +
        "WITH rel_pred WHERE rel IS NULL\n" +
        "WITH DISTINCT rel_pred\n" +
        "DELETE rel_pred"
        )

    carry_vars = set()
    query3_1 = (
        "MATCH (node_to_clone:node:{})-[:typing]->(n:node:{})\n".format(
            predecessor, rewritten_graph) +
        "WITH node_to_clone, collect(n) as sucs\n" +
        "WHERE size(sucs) >= 2\n" +
        "RETURN node_to_clone.id as node_id\n"
        )
    query3 = (
        "MATCH (node_to_clone:node:{}) WHERE node_to_clone.id = $id\n".format(
                    predecessor) +
        "MATCH (node_to_clone)-[t:typing]->(n:node:{})\n".format(
                    rewritten_graph) +
        "WITH node_to_clone, collect(n) as sucs, collect(t) as typ_sucs\n" +
        "WHERE size(sucs) >= 2\n" +
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

    return query1, query2, query3_1, query3


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
        "WITH n, collect(node_to_merge.id) as nodes_to_merge\n" +
        "WHERE n IS NOT NULL AND size(nodes_to_merge) >= 2\n" +
        "RETURN n, nodes_to_merge\n"
        )
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
