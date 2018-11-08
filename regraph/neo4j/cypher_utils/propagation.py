"""Collection of utils for generation of propagation-related Cypher queries."""
import warnings

from regraph.exceptions import (TypingWarning, InvalidHomomorphism)

from . import generic
from . import rewriting


# def check_functional()

def get_typing(domain, codomain, typing_label):
    query = (
        "MATCH (n:{})-[:{}]-(m:{})\n".format(
            domain, typing_label, codomain) +
        "RETURN n.id as node, m.id as type"
    )
    return query


def set_intergraph_edge(domain, codomain, domain_node,
                        codomain_node, typing_label):
    query = (
        "MATCH (n:{} {{ id: '{}' }}), (m:{} {{ id: '{}' }})\n".format(
            domain, domain_node, codomain, codomain_node) +
        "MERGE (n)-[:{}]->(m)".format(typing_label)
    )
    return query


def check_homomorphism(tx, domain, codomain, total=True):
    """Check if the homomorphism is valid.

    Parameters
    ----------
    tx
        Variable of a cypher transaction
    domain : str
        Label of the graph at the domain of the homomorphism
    codmain : str
        Label of the graph at the codomain of the homomorphism

    Raises
    ------
    InvalidHomomorphism
        This error is raised in the following cases:

            * a node at the domain does not have exactly 1 image
            in the codoamin
            * an edge at the domain does not have an image in
            the codomain
            * a property does not match between a node and its image
            * a property does not match between an edge and its image
    """
    # Check if all the nodes of the domain have exactly 1 image
    query1 = (
        "MATCH (n:{})\n".format(domain) +
        "OPTIONAL MATCH (n)-[:typing]->(m:{})\n".format(codomain) +
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
                    n, domain, str(nb), codomain) for n, nb in nodes]))

    # Check if all the edges of the domain have an image
    query2 = (
        "MATCH (n:{})-[:edge]->(m:{})\n".format(
            domain, domain) +
        "MATCH (n)-[:typing]->(x:{}), (y:{})<-[:typing]-(m)\n".format(
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

    # "CASE WHEN size(apoc.text.regexGroups(m_props, 'IntegerSet\\[(\\d+|minf)-(\\d+|inf)\\]') AS value"

    # Check if all the attributes of a node of the domain are in its image
    query3 = (
        "MATCH (n:{})-[:typing]->(m:{})\n".format(
            domain, codomain) +
        "WITH properties(n) as n_props, properties(m) as m_props, " +
        "n.id as n_id, m.id as m_id\n" +
        "WITH REDUCE(invalid = 0, k in filter(k in keys(n_props) WHERE k <> 'id') |\n" +
        "\tinvalid + CASE\n" +
        "\t\tWHEN NOT k IN keys(m_props) THEN 1\n" +
        "\t\tELSE REDUCE(invalid_values = 0, v in n_props[k] |\n" +
        "\t\t\tinvalid_values + CASE m_props[k][0]\n" +
        "\t\t\t\tWHEN 'IntegerSet' THEN CASE WHEN toInt(v) IS NULL THEN 1 ELSE 0 END\n" +
        "\t\t\t\tWHEN 'StringSet' THEN CASE WHEN toString(v) <> v THEN 1 ELSE 0 END\n" +
        "\t\t\t\tWHEN 'BooleanSet' THEN CASE WHEN v=true OR v=false THEN 0 ELSE 1 END\n" +
        "\t\t\t\tELSE CASE WHEN NOT v IN m_props[k] THEN 1 ELSE 0 END END)\n" +
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
            "Node attributes are not preserved!\n" +
            "\n".join(["Attributes of nodes source: '{}' ".format(n) +
                       "and target: '{}' do not match!".format(m)
                       for n, m in invalid_typings]))

    # Check if all the attributes of an edge of the domain are in its image
    query4 = (
        "MATCH (n:{})-[rel_orig:edge]->(m:{})\n".format(
            domain, domain) +
        "MATCH (n)-[:typing]->(x:{}), (y:{})<-[:typing]-(m)\n".format(
            codomain, codomain) +
        "MATCH (x)-[rel_img:edge]->(y)\n" +
        "WITH n.id as n_id, m.id as m_id, x.id as x_id, y.id as y_id, " +
        "properties(rel_orig) as rel_orig_props, " +
        "properties(rel_img) as rel_img_props\n" +
        "WITH REDUCE(invalid = 0, k in keys(rel_orig_props) |\n" +
        "\tinvalid + CASE\n" +
        "\t\tWHEN NOT k IN keys(rel_img_props) THEN 1\n" +
        "\t\tELSE REDUCE(invalid_values = 0, v in rel_orig_props[k] |\n" +
        "\t\t\tinvalid_values + CASE rel_img_props[k][0]\n" +
        "\t\t\t\tWHEN 'IntegerSet' THEN CASE WHEN toInt(v) IS NULL THEN 1 ELSE 0 END\n" +
        "\t\t\t\tWHEN 'StringSet' THEN CASE WHEN toString(v) <> v THEN 1 ELSE 0 END\n" +
        "\t\t\t\tWHEN 'BooleanSet' THEN CASE WHEN v=true OR v=false THEN 0 ELSE 1 END\n" +
        "\t\t\t\tELSE CASE WHEN NOT v IN rel_img_props[k] THEN 1 ELSE 0 END END)\n" +
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
            "Edge attributes are not preserved!\n" +
            "\n".join(["Attributes of edges '{}'->'{}' ".format(n, m) +
                       "and '{}'->'{}' do not match!".format(x, y)
                       for n, m, x, y in invalid_edges])
        )

    return True


def check_consistency(tx, source, target):
    """Check if the adding of a homomorphism is consistent."""
    query = (
        "// match all typing pairs between '{}' and '{}'\n".format(
            source, target) +
        "MATCH (s:{}), (t:{})\n".format(
            source, target) +
        "WITH s, t\n"
    )
    query += (
        "// match all the predecessors of 's' and successors of 't'\n"
        "MATCH (pred), (suc)\n" +
        "WHERE (pred)-[:typing*0..]->(s)\n" +
        "\tAND (t)-[:typing*0..]->(suc)\n" +
        "WITH s, t, collect(DISTINCT pred) as pred_list, " +
        "collect(DISTINCT suc) as suc_list\n"
    )
    query += (
        "// select all the pairs 'pred' 'suc' with a path between\n"
        "UNWIND pred_list as pred\n" +
        "UNWIND suc_list as suc\n" +
        "OPTIONAL MATCH (pred)-[r:typing*]->(suc)\n" +
        "WHERE NONE(rel in r WHERE rel.tmp = 'True')\n"
        "WITH s, t, r, labels(pred)[1] as pred_label, labels(suc)[1] as suc_label\n" +
        "WHERE r IS NOT NULL\n" +
        "WITH DISTINCT s, t, pred_label, suc_label\n"
    )
    query += (
        "// return the pairs 's' 't' where there should be a typing edge\n"
        "OPTIONAL MATCH (s)-[new_typing:typing]->(t)\n" +
        "WHERE new_typing.tmp IS NOT NULL\n" +
        "WITH pred_label, suc_label, s.id as s_id, t.id as t_id, new_typing\n" +
        "WHERE new_typing IS NULL\n" +
        "RETURN pred_label, suc_label, s_id, t_id\n"
    )

    result = tx.run(query)

    missing_typing = []
    for record in result:
        missing_typing.append((record['pred_label'], record['suc_label']))
    if len(missing_typing) != 0:
        raise InvalidHomomorphism(
            "Homomorphism does not commute with existing paths:\n" +
            ",\n".join(["\t- from {} to {}".format(
                s, t) for s, t in missing_typing]) + "."
        )

    return True


def check_tmp_consistency(tx, source, target, typing_label):
    """Check consistency of typing of the rhs of the rule."""
    query1 = (
        "// Checking consistency of introduced rhs\n"
        "MATCH (G:{})\n".format(source) +
        "WHERE G.id = '{}'\n".format(source) +
        "OPTIONAL MATCH (t_i:{})\n".format(target) +
        "WHERE (t_i)<-[:{}*1..]-(G)-[:{}*1..]->(t_i)\n".format(
            typing_label, typing_label) +
        "WITH DISTINCT t_i\n" +
        "RETURN collect(t_i.id)\n"
    )

    # If graph doesn't have multiple paths to the same successorts
    # then there is nothing to check
    multiple_paths_successors = tx.run(query1).value()[0]
    if len(multiple_paths_successors) == 0:
        return True

    inconsistent_paths = []
    for graph in multiple_paths_successors:
        query2 = (
            "MATCH (n:{})-[:tmp_typing]->()-[:typing*0..]->(m:{})\n".format(
                source, graph) +
            "WITH n, collect(DISTINCT m.id) as imgs\n" +
            "WHERE size(imgs) > 1\n" +
            "RETURN n.id as n_id, imgs\n"
        )
        result = tx.run(query2)
        for record in result:
            inconsistent_paths.append((record['n_id'], record['imgs'], graph))

    if len(inconsistent_paths) == 0:
        return True

    else:
        warn_message = (
            "\nTyping of the rhs is self inconsistent:\n" +
            "\n".join(["\t- Node '{}' is typed as {} in {}".format(
                n,
                " and ".join(["'{}'".format(i) for i in imgs]),
                g) for n, imgs, g in inconsistent_paths]) +
            "\n\n" +
            "The rhs typing of the rule will be ignored and a canonical " +
            "rewriting will be performed!\n"
        )
        warnings.warn(warn_message, TypingWarning)
        return False


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
        rewriting.multiple_cloning_query(
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
        "\t\t\t" + rewriting.add_edge(
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
        "\t" + rewriting.remove_nodes(['n']) + ")\n"
        "// Removal of node attributes in '{}'\n".format(predecessor_id) +
        "WITH n, x\n".format(
            predecessor_id, graph_id) +
        "WHERE x IS NOT NULL AND " +
        generic.nb_of_attrs_mismatch('n', 'x') + " <> 0\n"
        "WITH n, x, [x, n] as node_to_merge_props\n"
    )
    carry_vars.update(['n', 'x'])
    query += (
        generic.merge_properties_from_list(
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
        "\t" + rewriting.remove_edge('rel_pred') + ")\n" +
        "WITH rel, rel_pred\n" +
        "WHERE rel IS NOT NULL AND " +
        generic.nb_of_attrs_mismatch('rel_pred', 'rel') + " <> 0\n"
        "WITH rel, rel_pred, [rel_pred, rel] as edges_to_merge_props\n"
    )
    carry_vars.update(['rel_pred', 'rel'])
    query += (
        generic.merge_properties_from_list(
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
        rewriting.merging_from_list(
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


def add_node_propagation_query(origin_graph_id, graph_id, successor_id):
    """Generate query for propagation of node adds to a successor graph.."""
    carry_vars = set()
    # add nodes in T for each node without image in G + add new_props
    query = (
        "// Addition of nodes and attributes in '{}'\n".format(
            successor_id) +
        "MATCH (n:{})\n".format(graph_id) +
        "OPTIONAL MATCH (n)<-[:typing*0..]-()-[:typing*]->(existing_img:{})\n".format(
            successor_id) +
        "FOREACH(dummy IN CASE WHEN existing_img IS NOT NULL THEN [1] ELSE [] END |\n" +
        "\tMERGE (n)-[:typing]->(existing_img))\n" +
        generic.with_vars(['n']) +
        "OPTIONAL MATCH (n)<-[:typing*]-" +
        "(:{})-[trans_type:transitive_typing]->(successor_node:{})\n".format(
            origin_graph_id, successor_id) +
        "\tFOREACH(dummy IN CASE WHEN trans_type IS NULL THEN [] ELSE [1] END |\n" +
        "\t\tMERGE (n)-[:typing]->(successor_node)\n" +
        "\t\tDELETE trans_type)\n" +
        generic.with_vars(['n']) +
        "MERGE (n)-[:typing]->(node_img:{})\n".format(successor_id) +
        "WITH n, node_img\n" +
        "FOREACH(dummy IN CASE WHEN node_img.id IS NULL THEN [1] ELSE [] END |\n" +
        "\tSET node_img.id = toString(id(node_img)))\n" +
        "WITH n, node_img WHERE " +
        generic.nb_of_attrs_mismatch('n', 'node_img') + " <> 0\n" +
        "WITH node_img, collect(n) + [node_img] as nodes_to_merge_props\n"
    )
    carry_vars.add('node_img')
    query += (
        generic.merge_properties_from_list(
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
        "\n// Addition of edges and attributes in '{}'\n".format(
            successor_id) +
        "MATCH (n:{})-[rel:edge]->(m:{}), ".format(
            graph_id, graph_id) +
        "(n)-[:typing]->(x:{}), (m)-[:typing]->(y:{})\n".format(
            successor_id, successor_id) +
        "MERGE (x)-[rel_img:edge]->(y)\n" +
        "WITH x, y, rel, rel_img WHERE " +
        generic.nb_of_attrs_mismatch('rel', 'rel_img') + " <> 0\n"
        "WITH x, y, rel_img, collect(rel) + rel_img as edges_to_merge_props\n"
    )
    carry_vars.update(['x', 'y', 'rel_img'])
    query += (
        generic.merge_properties_from_list(
            list_var='edges_to_merge_props',
            new_props_var='new_props',
            carry_vars=carry_vars,
            method='union') +
        "SET rel_img += new_props\n"
    )
    return query


def remove_tmp_typing(rewritten_graph, direction="successors"):
    if direction == "predecessors":
        left_arrow = "<"
        right_arrow = ""
    else:
        left_arrow = ""
        right_arrow = ">"
    query = (
        "Removing ':tmp_typing' relationships."
        "MATCH (n:{}){}-[t:tmp_typing]-{}()\n".format(
            rewritten_graph, left_arrow, right_arrow) +
        "DELETE t\n"
    )
    return query


def preserve_tmp_typing(rewritten_graph, graph_label, typing_label,
                        direction="successors"):
    if direction == "predecessors":
        left_arrow = "<"
        right_arrow = ""
    else:
        left_arrow = ""
        right_arrow = ">"
    query = (
        "// Replacing ':tmp_typing' with ':typing'\n"
        "MATCH (n:{}){}-[t:tmp_typing]-{}(m)\n".format(
            rewritten_graph, left_arrow, right_arrow) +
        "OPTIONAL MATCH (:{} {{id: '{}'}})".format(
            graph_label, rewritten_graph) +
        "{}-[skeleton_rel:{}]-{}(:{} {{id: labels(m)[0]}}) \n".format(
            left_arrow, typing_label, right_arrow, graph_label) +
        "FOREACH( dummy IN (CASE skeleton_rel WHEN null THEN [] ELSE [1] END) | \n" +
        "\tDELETE t\n" +
        "\tMERGE (n){}-[:typing]-{}(m)\n".format(left_arrow, right_arrow) +
        ")\n" +
        "FOREACH( dummy IN (CASE skeleton_rel WHEN null THEN [1] ELSE [] END) | \n" +
        "\tDELETE t\n" +
        "\tMERGE (n){}-[:transitive_typing]-{}(m)\n".format(
            left_arrow, right_arrow) +
        ")\n"
    )
    return query
