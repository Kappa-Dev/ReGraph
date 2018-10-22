"""Collection of utils for generation of propagation-related Cypher queries."""
import regraph.neo4j.cypher_utils as cypher


def clone_propagation_query(graph_id, predecessor_id):
    """Generate query for propagation of cloning to a predecessor graph."""
    # We clone the nodes that have more than 1 image and
    # reassign the typing edges
    carry_vars = set()
    query = (
        "// Matching of the nodes to clone in '{}'\n".format(predecessor_id) +
        "OPTIONAL MATCH (node_to_clone:{})-[t:typing]->(n:{})\n".format(
            predecessor_id, graph_id) +
        "WITH node_to_clone, collect(n) as sucs, collect(t) as typ_sucs, "
        "count(n) as number_of_img\n" +
        "WHERE number_of_img >= 2 AND node_to_clone IS NOT NULL\n"
    )
    query += (
        "FOREACH(t IN typ_sucs | DELETE t)\n" +
        "WITH node_to_clone, sucs, number_of_img-1 as number_of_clone\n"
    )
    carry_vars.update(['node_to_clone', 'sucs'])
    query += (
        cypher.multiple_cloning_query(
            original_var='node_to_clone',
            clone_var='cloned_node',
            clone_id='clone_id',
            clone_id_var='clone_id',
            number_of_clone_var='number_of_clone',
            node_label=predecessor_id,
            edge_label='edge',
            preserv_typing=True,
            carry_vars=carry_vars,
            ignore_naming=True,
            multiple_rows=True)[0]
    )
    carry_vars.difference_update(['cloned_node', 'clone_id'])
    query += (
        "WITH collect(cloned_node)+[node_to_clone] as nodes_to_typ, " +
        "collect(clone_id) as clone_ids, " +
        ", ".join(carry_vars) + "\n" +
        "FOREACH (i IN range(0, size(sucs)-1) |\n" +
        "\tFOREACH(source in [nodes_to_typ[i]] |\n"
        "\t\tFOREACH(target in [sucs[i]] |\n"
        "\t\t\t" + cypher.create_edge(
            edge_var='restored_typing',
            source_var='source',
            target_var='target',
            edge_label='typing') + ")))\n"
    )
    query += "RETURN clone_ids"
    return query


def remove_node_propagation_query(graph_id, predecessor_id):
    """Generate query for propagation of node deletes to a predecessor."""
    # Removes nodes and node attrs
    carry_vars = set()
    query = (
        "// Removal of nodes in '{}'\n".format(predecessor_id) +
        "MATCH (n:{})\n".format(predecessor_id) +
        "OPTIONAL MATCH (n)-[:typing]->(x:{})\n".format(graph_id) +
        "FOREACH(dummy IN CASE WHEN x IS NULL THEN [1] ELSE [] END |\n" +
        "\t" + cypher.delete_nodes_var(['n']) + ")\n"
        "// Removal of node properties in '{}'\n".format(predecessor_id) +
        "WITH n, x\n".format(
            predecessor_id, graph_id) +
        "WHERE x IS NOT NULL AND " +
        cypher.nb_of_attrs_mismatch('n', 'x') + " <> 0\n"
        "WITH n, x, [x, n] as node_to_merge_props\n"
    )
    carry_vars.update(['n', 'x'])
    query += (
        cypher.merge_properties_from_list(
            list_var='node_to_merge_props',
            new_props_var='new_props',
            carry_vars=carry_vars,
            method='intersection') +
        "WITH n.id as n_id, " + ", ".join(carry_vars) + "\n"
        "SET n = new_props\n" +
        "SET n.id = n_id\n"
    )
    return query


def remove_edge_propagation_query(graph_id, predecessor_id):
    """Generate query for propagation of edge deletes to a predecessor."""
    carry_vars = set()
    query = (
        "// Removal of edges attributes in '{}'\n".format(predecessor_id) +
        "MATCH (n:{})-[rel_pred:edge]->(m:{})\n".format(
            predecessor_id, predecessor_id) +
        "OPTIONAL MATCH (x:{})-[rel:edge]->(y:{})".format(
            graph_id, graph_id) +
        "WHERE (n)-[:typing]->(x) AND (m)-[:typing]->(y)\n" +
        "FOREACH(dummy IN CASE WHEN rel IS NULL THEN [1] ELSE [] END |\n" +
        "\t" + cypher.delete_edge_var('rel_pred') + ")\n" +
        "WITH rel, rel_pred\n" +
        "WHERE rel IS NOT NULL AND " +
        cypher.nb_of_attrs_mismatch('rel_pred', 'rel') + " <> 0\n"
        "WITH rel, rel_pred, [rel_pred, rel] as edges_to_merge_props\n"
    )
    carry_vars.update(['rel_pred', 'rel'])
    query += (
        cypher.merge_properties_from_list(
            list_var='edges_to_merge_props',
            new_props_var='new_props',
            carry_vars=carry_vars,
            method='intersection') +
        "SET rel_pred = new_props\n"
    )
    return query


def merge_propagation_query(graph_id, successor_id):
    """Generate query for propagation of merges to a successor graph."""
    carry_vars = set()
    carry_vars.add('merged_nodes')
    query = "\n// Up-propagation to the graph '{}'\n".format(successor_id)
    query += (
        "\n// Matching of the nodes to merge in '{}'\n".format(successor_id) +
        "WITH [] as merged_nodes\n"
        "OPTIONAL MATCH (n:{})-[:typing]->(node_to_merge:{})\n".format(
            graph_id, successor_id) +
        "WITH n, collect(node_to_merge) as nodes_to_merge, " +
        ", ".join(carry_vars) + "\n"
        "WHERE n IS NOT NULL AND size(nodes_to_merge) >= 2\n"
    )
    carry_vars.add('n')
    carry_vars.add('nodes_to_merge')
    query += (
        cypher.merging_from_list(
            list_var='nodes_to_merge',
            merged_var='merged_node',
            merged_id='id',
            merged_id_var='merged_id',
            node_label=successor_id,
            edge_label='edge',
            merge_typing=True,
            carry_vars=carry_vars,
            ignore_naming=True,
            multiple_rows=True,
            multiple_var='n')[0]
    )
    carry_vars.remove('merged_node')
    carry_vars.remove('merged_id')
    query += "RETURN collect(merged_id) as merged_nodes"
    return query


def add_node_propagation_query(graph_id, successor_id):
    """Generate query for propagation of node adds to a successor graph.."""
    carry_vars = set()
    # add nodes in T for each node without image in G + add new_props
    query = (
        "\n// Addition of nodes and properties in '{}'\n".format(
            successor_id) +
        "MATCH (n:{})\n".format(graph_id) +
        "OPTIONAL MATCH (n)<-[:typing*0..]-()-[:typing*]->(existing_img:{})\n".format(
            successor_id) +
        "FOREACH(dummy IN CASE WHEN existing_img IS NOT NULL THEN [1] ELSE [] END |\n" +
        "\tMERGE (n)-[:typing]->(existing_img))\n" +
        cypher.with_vars(['n']) +
        "MERGE (n)-[:typing]->(node_img:{})\n".format(successor_id) +
        "WITH n, node_img\n" +
        "FOREACH(dummy IN CASE WHEN node_img.id IS NULL THEN [1] ELSE [] END |\n" +
        "\tSET node_img.id = id(node_img))\n" +
        "WITH n, node_img WHERE " +
        cypher.nb_of_attrs_mismatch('n', 'node_img') + " <> 0\n" +
        "WITH node_img, collect(n) + [node_img] as nodes_to_merge_props\n"
    )
    carry_vars.add('node_img')
    query += (
        cypher.merge_properties_from_list(
            list_var='nodes_to_merge_props',
            new_props_var='new_props',
            carry_vars=carry_vars,
            method='union') +
        "SET node_img += new_props\n"
    )
    return query


def add_edge_propagation_query(graph_id, successor_id):
    """Generate query for propagation of edge adds to a successor graph."""
    carry_vars = set()
    # add edges in T for each edge without image in G + add new_props
    query = (
        "\n// Addition of edges and properties in '{}'\n".format(
            successor_id) +
        "MATCH (n:{})-[rel:edge]->(m:{}), ".format(
            graph_id, graph_id) +
        "(n)-[:typing]->(x:{}), (m)-[:typing]->(y:{})\n".format(
            successor_id, successor_id) +
        "MERGE (x)-[rel_img:edge]->(y)\n" +
        "WITH x, y, rel, rel_img WHERE " +
        cypher.nb_of_attrs_mismatch('rel', 'rel_img') + " <> 0\n"
        "WITH x, y, rel_img, collect(rel) + rel_img as edges_to_merge_props\n"
    )
    carry_vars.update(['x', 'y', 'rel_img'])
    query += (
        cypher.merge_properties_from_list(
            list_var='edges_to_merge_props',
            new_props_var='new_props',
            carry_vars=carry_vars,
            method='union') +
        "SET rel_img += new_props\n"
    )
    return query


def remove_tmp_typing(rewritten_graph):
    query = (
        "MATCH (n:{})-[t:tmp_typing]->()\n".format(rewritten_graph) +
        "DELETE t\n"
    )
    return query


def preserve_tmp_typing(rewritten_graph):
    query = (
        "MATCH (n:{})-[t:tmp_typing]->(m)\n".format(rewritten_graph) +
        "OPTIONAL MATCH (:hierarchyNode {{id: '{}'}})".format(
            rewritten_graph) +
        "-[skeleton_rel:hierarchyEdge]->(:hierarchyNode {id: labels(m)[0]}) \n" +
        "FOREACH( dummy IN (CASE skeleton_rel WHEN null THEN [] ELSE [1] END) | \n" +
        "\tDELETE t\n" +
        "\tMERGE (n)-[:typing]->(m)\n" +
        ")\n"
    )
    return query
