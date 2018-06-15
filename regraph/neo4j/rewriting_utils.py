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
    print(query1)
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
    print(query2)
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
        cypher.create_edge(
                    edge_var='restored_typing',
                    source_var='cloned_node',
                    target_var='node_suc',
                    edge_label='typing') + "\n" +
        cypher.create_edge(
                    edge_var='restored_typing1',
                    source_var='node_to_clone',
                    target_var='suc1',
                    edge_label='typing') + "\n"
        )
    print(query3_1)
    result = tx.run(query3_1)
    for record in result:
        node_id = record['node_id']
        print(node_id)
        print(query3)
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
        "ON CREATE SET new_node.id = toString(id(new_node))\n"
        )
    print(query1)
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
    print(query2)
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
    print(query3)
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
        print(query)
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


def propagate_down_v2(rewritten_graph, successor):
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
    carry_vars = set()

    query = (
        "// Addition of nodes in '{}'\n".format(successor) +
        "OPTIONAL MATCH (n:node:{})".format(rewritten_graph) +
        "WHERE n.id IN $added_nodes_list " +
        "AND NOT (n)-[:typing]->(:node:{})\n".format(successor) +
        "MERGE (n)-[:typing]->(new_node:node:{})\n".format(successor) +
        "ON CREATE SET new_node += properties(n)\n" +
        "ON CREATE SET new_node.id = toString(id(new_node))\n"
        )
    query += "WITH collect(new_node.id) as added_nodes\n"
    carry_vars.add('added_nodes')

    # add edges in T for each edge without image in G
    query += (
        "\n// Addition of edges in '{}'\n".format(successor) +
        "OPTIONAL MATCH (n:node:{})-[rel:edge]->(m:node:{})\n".format(
            rewritten_graph, rewritten_graph) +
        "WHERE n.id IN $added_edges_list.source " +
        "AND m.id IN $added_edges_list.target\n" +
        "OPTIONAL MATCH (n)-[:typing]->(x:node:{}), (m)-[:typing]->(y:node:{})\n".format(
            successor, successor) +
        "MERGE (x)-[rel_img:edge]->(y)\n"
    )
    carry_vars.update(['x', 'y'])
    query += (
        cypher.merge_properties(
                    var_list=['rel', 'rel_img'],
                    new_props_var='new_props',
                    carry_vars=carry_vars) +
        "SET rel_img += new_props\n"
        )
    carry_vars.difference_update(['rel', 'rel_img', 'x', 'y', 'new_props'])
    query += (
        "WITH {source:collect(x.id), target:collect(y.id)} as added_edges, " +
        ", ".join(carry_vars) + "\n"
    )
    carry_vars.add('added_edges')

    # match nodes of T with the same pre-image in G and merge them
    query += (
        "\n// Matching of the nodes to merge in '{}'\n".format(successor) +
        "OPTIONAL MATCH (n:node:{}) \n".format(rewritten_graph) +
        "WHERE n.id IN $merged_nodes_list\n" +
        "OPTIONAL MATCH (n)-[:typing]->(node_to_merge:node:{})\n".format(
            successor) +
        "WITH n, collect(node_to_merge) as nodes_to_merge, " +
        ", ".join(carry_vars) + "\n"
        "WHERE n IS NOT NULL AND size(nodes_to_merge) >= 2\n" 
    )
    carry_vars.add('n')
    query += (
        merging_from_list(list_var='nodes_to_merge',
                          merged_var='merged_node',
                          merged_id='id',
                          merged_id_var='merged_id',
                          node_label='node:'+successor,
                          edge_label='edge',
                          merge_typing=True,
                          carry_vars=carry_vars,
                          ignore_naming=True)[0]
        )
    carry_vars.remove('merged_node')
    carry_vars.remove('merged_id')
    query += (
        "RETURN collect(merged_id) as merged_nodes, " +
        ", ".join(carry_vars) + "\n"
        )

    return query


def merging_from_list(list_var, merged_var, merged_id, merged_id_var,
                      node_label='node', edge_label='edge', merge_typing=False,
                      carry_vars=None, ignore_naming=False):
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
    node_label
        Label of the nodes to merge, default is 'node'
    edge_label
        Label of the edges to merge, default is 'edge'
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
        carry_vars = set()

    query = "UNWIND {} as node_to_merge\n".format(list_var)

    query += (
        "// accumulate all the attrs of the nodes to be merged\n" +
        "WITH [] as new_props, node_to_merge, " + ", ".join(carry_vars) + "\n" +
        "WITH new_props + REDUCE(pairs = [], k in keys(node_to_merge) | \n" +
        "\tpairs + REDUCE(inner_pairs = [], v in node_to_merge[k] | \n" +
        "\t\tinner_pairs + {key: k, value: v})) as new_props, node_to_merge, " +
        ", ".join(carry_vars) + "\n"
    )

    query += (
        "WITH collect(node_to_merge) as {}, ".format(list_var) +
        "collect(new_props) as new_props_col, " +
        ", ".join(carry_vars) + "\n"
        "WITH REDUCE(init=[], props in new_props_col | init + props) as new_props, " +
        "{}, ".format(list_var) + ", ".join(carry_vars) + "\n"
    )
    carry_vars.add(list_var)

    query += (
        "WITH apoc.map.groupByMulti(new_props, 'key') as new_props, " +
        ", ".join(carry_vars) + "\n" +
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys(new_props) | \n"
        "\tpairs + [k, REDUCE(values=[], v in new_props[k] | \n"
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as new_props, " +
        ", ".join(carry_vars) + "\n" + 
        "WITH {}[0] as {}, new_props, ".format(list_var, merged_var) +
        ", ".join(carry_vars) + "\n"
        "SET {} = new_props\n".format(merged_var)
    )
    carry_vars.add(merged_var)

    if ignore_naming is True:
        query += (
            "// set appropriate node id\n"
            "SET {}.id = toString(id({}))\n".format(merged_var, merged_var) +
            "SET {}.count = NULL\n".format(merged_var) +
            "WITH toString(id({})) as {}, ".format(merged_var, merged_id_var) +
            ", ".join(carry_vars) + "\n"
        )
    else:
        query += (
            "// search for a node with the same id as the clone id\n" +
            "OPTIONAL MATCH (same_id_node:{} {{ id : '{}'}}) \n".format(
                node_label, merged_id) +
            "WITH same_id_node,  " +
            "CASE WHEN same_id_node IS NOT NULL "
            "THEN (coalesce(same_id_node.count, 0) + 1) " +
            "ELSE 0 END AS same_id_node_new_count, " +
            ", ".join(carry_vars) + "\n" +
            "// generate new id if the same id node was found\n" +
            "// and filter edges which will be removed \n" +
            "WITH same_id_node, same_id_node_new_count, " +
            "'{}' + CASE WHEN same_id_node_new_count <> 0 ".format(merged_id) +
            "THEN toString(same_id_node_new_count) ELSE '' END as {}, ".format(
                merged_id_var) +
            ", ".join(carry_vars) + "\n"
            "// set appropriate node id\n"
            "SET {}.id = {}\n".format(merged_var, merged_id_var) +
            "SET {}.count = NULL\n".format(merged_var) +
            "WITH {}, ".format(merged_id_var) + ", ".join(carry_vars) + "\n"
        )

    carry_vars.add(merged_id_var)

    query += "UNWIND {} AS node_to_merge\n".format(list_var)
    carry_vars.remove(list_var)

    query += (
        "// accumulate all the attrs of the edges incident to the merged nodes\n"
        "WITH [] as suc_maps, [] as pred_maps, node_to_merge, " +
        ", ".join(carry_vars) + "\n"
        "OPTIONAL MATCH (node_to_merge)-[out_rel:{}]->(suc)\n".format(edge_label) +
        "WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, " +
        "pred_maps, node_to_merge, " + ", ".join(carry_vars) + "\n" +
        "OPTIONAL MATCH (pred)-[in_rel:{}]->(node_to_merge)\n".format(edge_label) +
        "WITH pred_maps + collect({id: id(pred), neighbor: pred, edge: in_rel}) as pred_maps, " +
        "suc_maps, node_to_merge, " + ", ".join(carry_vars) + "\n"
    )
    query += (
        "WITH collect(node_to_merge) as {}, ".format(list_var) +
        "collect(node_to_merge.id) as list_ids, "
        "collect(suc_maps) as suc_maps_col, " +
        "collect(pred_maps) as pred_maps_col, " +
        ", ".join(carry_vars) + "\n"
        "WITH REDUCE(init=[], maps in suc_maps_col | init + maps) as suc_maps, " +
        "REDUCE(init=[], maps in pred_maps_col | init + maps) as pred_maps, " +
        "list_ids, {}, ".format(list_var) + ", ".join(carry_vars) + "\n"
    )
    carry_vars.add(list_var)
    carry_vars.add('list_ids')

    query += (
        "WITH apoc.map.groupByMulti(suc_maps, 'id') as suc_props, " +
        "REDUCE(list=[], map in suc_maps | \n"
        "\tlist + CASE WHEN NOT map['neighbor'] IS NULL THEN [map['neighbor']] ELSE [] END) as suc_nodes, "
        "apoc.map.groupByMulti(pred_maps, 'id') as pred_props, " +
        "REDUCE(list=[], map in pred_maps | \n"
        "\tlist + CASE WHEN NOT map['neighbor'] IS NULL THEN [map['neighbor']] ELSE [] END) as pred_nodes, " +
        "\tREDUCE(l=[], el in suc_maps + pred_maps| \n" +
        "\t\tl + CASE WHEN el['id'] IN list_ids THEN [toString(el['id'])] ELSE [] END)" +
        " as self_loops, " +
        ", ".join(carry_vars) + "\n"
    )
    carry_vars.remove('list_ids')
    carry_vars.add("self_loops")

    query += (
        "WITH suc_nodes, pred_nodes, "
        "apoc.map.fromValues(REDUCE(edge_props=[], k in keys(suc_props) | \n"
        "\tedge_props + [k, apoc.map.groupByMulti(REDUCE(props=[], el in suc_props[k] | \n"
        "\t\tprops + REDUCE(pairs=[], kk in keys(el['edge']) | \n"
        "\t\t\tpairs + REDUCE(values=[], v in el['edge'][kk] | \n"
        "\t\t\t\tvalues + {key: kk, value: v}))), 'key')])) as suc_props, \n" +
        "\tapoc.map.fromValues(REDUCE(edge_props=[], k in keys(pred_props) | \n"
        "\tedge_props + [k, apoc.map.groupByMulti(REDUCE(props=[], el in pred_props[k] | \n"
        "\t\tprops + REDUCE(pairs=[], kk in keys(el['edge']) | \n"
        "\t\t\tpairs + REDUCE(values=[], v in el['edge'][kk] | \n"
        "\t\t\t\t values + {key: kk, value: v}))), 'key')])) as pred_props,  \n" +
        "\tREDUCE(edge_props=[], k IN filter(k IN keys(suc_props) WHERE k IN self_loops) |\n"
        "\t\tedge_props + suc_props[k]) + \n"
        "\tREDUCE(edge_props=[], k IN filter(k IN keys(pred_props) WHERE k IN self_loops) |\n"
        "\t\tedge_props + pred_props[k]) as self_loop_props, " +
        ", ".join(carry_vars) + "\n" +
        "WITH suc_nodes, suc_props, pred_nodes, pred_props, " +
        "apoc.map.groupByMulti(REDUCE(pairs=[], el in self_loop_props |\n"
        "\tpairs + REDUCE(inner_pairs=[], k in keys(el['edge']) | \n"
        "\t\tinner_pairs + REDUCE(values=[], v in el['edge'][k] |\n"
        "\t\t\tvalues + {key: k, value: v}))), 'key') as self_loop_props, " +
        ", ".join(carry_vars) + "\n" +
        "FOREACH(suc IN filter(suc IN suc_nodes WHERE NOT id(suc) in self_loops) |\n"
        "\tMERGE ({})-[new_rel:{}]->(suc)\n".format(merged_var, edge_label) +
        "\tSET new_rel = apoc.map.fromValues(REDUCE(pairs=[], k in keys(suc_props[toString(id(suc))]) | \n"
        "\t\t pairs + [k, REDUCE(values=[], v in suc_props[toString(id(suc))][k] | \n"
        "\t\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])))\n"
        "FOREACH(pred IN filter(pred IN pred_nodes WHERE NOT id(pred) in self_loops) |\n"
        "\tMERGE (pred)-[new_rel:{}]->({})\n".format(edge_label, merged_var) +
        "\tSET new_rel = apoc.map.fromValues(REDUCE(pairs=[], k in keys(pred_props[toString(id(pred))]) | \n"
        "\t\t pairs + [k, REDUCE(values=[], v in pred_props[toString(id(pred))][k] | \n"
        "\t\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])))\n"
    )
    query += (
        "// add self loop \n"
        "FOREACH(dummy in CASE WHEN length(self_loops) > 0 THEN [NULL] ELSE [] END |\n"
        "\tMERGE ({})-[new_rel:{}]->({})\n".format(merged_var,
                                                   edge_label,
                                                   merged_var) +
        "\tSET new_rel = apoc.map.fromValues(REDUCE(pairs=[], k in keys(self_loop_props) |\n"
        "\t\tpairs + [k, REDUCE(values=[], v in self_loop_props[k] |\n"
        "\t\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])))\n"
    )
    carry_vars.remove("self_loops")

    if merge_typing:
        query += "WITH " + ", ".join(carry_vars) + "\n"
        query += "UNWIND {} AS node_to_merge\n".format(list_var)
        carry_vars.remove(list_var)

        query += (
            "// accumulate all the attrs of the edges incident to the merged nodes\n"
            "WITH [] as suc_typings, [] as pred_typings, node_to_merge, " +
            ", ".join(carry_vars) + "\n"
        )
        query += (
            "OPTIONAL MATCH (node_to_merge)-[:typing]->(suc)\n" +
            "WITH suc_typings + collect(suc) as suc_typings, node_to_merge, " +
            "pred_typings, " + ", ".join(carry_vars) + "\n" +
            "OPTIONAL MATCH (pred)-[:typing]->(node_to_merge)\n" +
            "WITH pred_typings + collect(pred) as pred_typings, node_to_merge, " +
            "suc_typings, " + ", ".join(carry_vars) + "\n"
        )
        query += (
            "WITH collect(node_to_merge) as {}, ".format(list_var) +
            "collect(suc_typings) as suc_typings_col, " +
            "collect(pred_typings) as pred_typings_col, " +
            ", ".join(carry_vars) + "\n"
            "WITH REDUCE(init=[], sucs in suc_typings_col | init + sucs) as suc_typings, " +
            "REDUCE(init=[], preds in pred_typings_col | init + preds) as pred_typings, " +
            "{}, ".format(list_var) + ", ".join(carry_vars) + "\n"
        )
        carry_vars.add(list_var)

        query += (
            "FOREACH(suc in suc_typings |\n" +
            "\tMERGE ({})-[:typing]->(suc))\n".format(merged_var) +
            "FOREACH(pred in pred_typings |\n" +
            "\tMERGE (pred)-[:typing]->({}))\n".format(merged_var)
        )

    query += "WITH " + ", ".join(carry_vars) + "\n"
    query += "UNWIND {}[1..] AS node_to_merge\n".format(list_var)
    carry_vars.remove(list_var)
    query += "DETACH DELETE (node_to_merge)\n"

    return query, carry_vars
