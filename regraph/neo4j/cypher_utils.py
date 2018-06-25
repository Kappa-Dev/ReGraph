"""Collection of utils for Cypher queries generation."""
from regraph.default.attribute_sets import *


def set_attributes(var_name, attrs):
    """Generate a subquery to set the attributes for some variable."""
    query = ""
    for k, value in attrs.items():
        if isinstance(value, FiniteSet):
            elements = []
            for el in value:
                if type(el) == str:
                    elements.append("'{}'".format(el))
                else:
                    elements.append("{}".format(el))
            query += "SET {}.{}=[{}] ".format(var_name, k, ", ".join(
                el for el in elements))
        else:
            raise ValueError(
                "Unknown type of attribute '{}': '{}'".format(k, type(value)))
    return query


def add_attributes(var_name, attrs):
    """Generate a subquery to add attributes to an existing node."""
    query = ""
    for k, value in attrs.items():
        if isinstance(value, FiniteSet):
            elements = []
            for el in value:
                if type(el) == str:
                    elements.append("'{}'".format(el))
                else:
                    elements.append("{}".format(el))
            query += (
                "FOREACH(dummy IN CASE WHEN NOT '{}' IN keys({}) THEN [1] ELSE [] END |\n".format(
                    k, var_name) +
                "\tSET {}.{} = [{}])\n".format(
                    var_name, k, ", ".join(el for el in elements))
            )
            query += (
                "FOREACH(dummy IN CASE WHEN '{}' IN keys({}) THEN [1] ELSE [] END |\n".format(
                        k, var_name) +
                "\tFOREACH(val in [{}] |\n".format(", ".join(el for el in elements)) +
                "\t\tFOREACH(dummy IN CASE WHEN NOT val IN {}.{} THEN [1] ELSE [] END |\n".format(
                    var_name, k) +
                "\t\t\tSET {}.{} = {}.{} + [val])))\n".format(var_name, k, var_name, k)
            )
        else:
            raise ValueError(
                "Unknown type of attribute '{}': '{}'".format(k, type(value)))
    return query


def remove_attributes(var_name, attrs):
    """Generate a subquery to remove attributes to an existing node."""
    query = ""
    for k, value in attrs.items():
        if isinstance(value, FiniteSet):
            elements = []
            for el in value:
                if type(el) == str:
                    elements.append("'{}'".format(el))
                else:
                    elements.append("{}".format(el))
            query += (
                "FOREACH(dummy IN CASE WHEN '{}' IN keys({}) THEN [1] ELSE [] END |\n".format(
                        k, var_name) +
                "\tSET {}.{} = filter(v in {}.{} WHERE NOT v IN [{}])".format(
                    var_name, k, var_name, k,
                    ", ".join(["'{}'".format(val) for val in value])) +
                "\tFOREACH(dumy2 IN CASE WHEN size({}.{})=0 THEN [1] ELSE [] END |\n".format(
                    var_name, k) +
                "\t\tREMOVE {}.{}))\n".format(
                    var_name, k)
            )
        else:
            raise ValueError(
                "Unknown type of attribute '{}': '{}'".format(k, type(value)))
    return query


def generate_attributes(attrs):
    """Generate a string converting attrs to Cypher compatible format."""
    if attrs is None:
        return ""
    else:
        attrs_items = []
        for k, value in attrs.items():
            if isinstance(value, FiniteSet):
                elements = []
                for el in value:
                    if type(el) == str:
                        elements.append("'{}'".format(el))
                    else:
                        elements.append("{}".format(el))
                attrs_items.append("{}: [{}]".format(k, ", ".join(
                    el for el in elements)))
            else:
                raise ValueError(
                    "Unknown type of attribute '{}': '{}'".format(k, type(value)))
        return ", ".join(i for i in attrs_items)


def match_node(var_name, node_id, label='node'):
    """Query to match a node into the variable.

    Parameters
    ----------
    var_name
        Variable name to use for the matched node
    node_id
        Id of the node to match
    label
        Label of the node to match, default is 'node'
    """
    return "MATCH ({}:{} {{ id : '{}' }})\n".format(
        var_name, label, node_id)


def match_nodes(var_id_dict, label='node'):
    """Match a collection of nodes by their id.

    Parameters
    ----------
    var_id_dict : dict
        Dictionary whose keys are names of the variables to use for
        the matched nodes and whose values are the ids of the nodes
        to match
    label : strt
        Label of the nodes to clone, default is 'node'
    """
    query =\
        "MATCH " +\
        ", ".join("({}:{} {{ id : '{}'}})".format(var_name, label, node_id)
                  for var_name, node_id in var_id_dict.items()) + " "
    return query


def match_edge(u_var, v_var, u_id, v_id, edge_var, edge_label='edge'):
    """Query for matching an edge.

    Parameters
    ----------
    u_var
        Name of the variable corresponding to the source of
        the edge
    v_var
        Name of the variable corresponding to the target of
        the edge
    u_id
        Id of the source node
    v_id
        Id of the target node
    edge_var
        Name of the variable to use for the matched edge
    label
        Label of the edge to match, default is 'edge'
    """
    query =\
        match_nodes({u_var: u_id, v_var: v_id}) + ", " +\
        "({})-[{}:{}]->({})".format(u_var, edge_var, edge_label, v_var) + "\n"
    return query


def create_node(var_name, node_id, node_id_var, label='node',
                attrs=None, literal_id=True, carry_vars=None,
                ignore_naming=False):
    """Generate query for node creation.

    Parameters
    ----------
    var_name
        Name of the variable corresponding to the created
        node in the query
    node_id
        Id of the node to create
    node_id_var
        Variable corresponding to the new id of the node to create
    label
        Label of the node to create, default is 'node'
    literal_id : bool
        True if parameter `node_id` is a literal, otherwise it is
        treated as the variable name
    carry_vars : iterable
        Collection of variables to carry

    Returns
    -------
    query : str
        String containing generated Cypher query
    carry_vars : set
        Set of updated variables to carry

    """
    if literal_id:
        node_id = "'{}'".format(node_id)

    if carry_vars is None:
        carry_vars = set()
    if not ignore_naming:
        query = (
            "OPTIONAL MATCH (same_id_node:{}) \n".format(label) +
            "WHERE same_id_node.id = {} \n".format(node_id) +
            "FOREACH(new_count \n\tIN CASE WHEN same_id_node IS NOT NULL\n"
            "\tTHEN [coalesce(same_id_node.count, 0) + 1]\n"
            "\tELSE [] END | \n"
            "\t\tSET same_id_node.count = new_count) \n"
            "WITH same_id_node "
        )
        if len(carry_vars) > 0:
            query += ", " + ", ".join(carry_vars) + "\n"
        else:
            query += "\n"
        query += (
            "UNWIND\n\tCASE WHEN same_id_node IS NOT NULL\n"
            "\tTHEN [{} + same_id_node.count]\n".format(node_id) +
            "\tELSE [{}] END AS {} \n".format(node_id, node_id_var) +
            "\t\tCREATE ({}:{} {{ id : {} }}) \n".format(
                var_name, label, node_id_var)
        )
    else:
        query =\
            "CREATE ({}:{}) \n".format(var_name, label) +\
            "SET {}.id = toString(id({})) \n".format(var_name, var_name)
        query += "WITH toString(id({})) as {} ".format(var_name, node_id_var)
        carry_vars.add(var_name)
        query += ", " + ", ".join(carry_vars) + "\n"

    if attrs is not None:
        query += set_attributes(var_name, attrs)

    carry_vars.add(node_id_var)
    carry_vars.add(var_name)
    return query, carry_vars


def create_edge(edge_var, source_var, target_var,
                edge_label='edge', attrs=None):
    """Generate query for edge creation.

    source_var
        Name of the variable corresponding to the source
        node
    target_var
        Name of the variable corresponding to the target
        node
    attrs
        Attributes of the new edge
    """
    attrs_str = generate_attributes(attrs)
    query = "MERGE ({})-[{}:{} {{ {} }}]->({})\n".format(
        source_var, edge_var, edge_label, attrs_str, target_var)
    return query


def delete_nodes_var(var_names):
    """Query for deleting nodes corresponding to the input variables.

    Parameters
    ----------
    var_names : iterable
        Collection of variables corresponding to nodes to remove
    """
    return "DETACH DELETE {}\n".format(
        ', '.join(v for v in var_names))


def delete_edge_var(edge_var):
    """Query for deleting an edge corresponding to the input variable.

    Parameters
    ----------
    edge_var
        Name of the variable corresponding to the edge to remove
    """
    return "DELETE {}\n".format(edge_var)


def with_vars(carry_vars):
    """Generate WITH statement using the input variables to carry."""
    return "WITH {} ".format(", ".join(carry_vars))


def return_vars(var_list):
    """Generate RETURN query with the input variables."""
    return "RETURN {}\n".format(", ".join(var_list))


def clear_graph(label=None):
    """Generate query for removing everything from the graph.

    Parameters
    ----------
    label
        Label of the graph to remove. If None, all the database is cleared
    """
    if label is None:
        query = "MATCH (n)\n"
    else:
        query = "MATCH (n:{})\n".format(label)
    query += \
        "OPTIONAL MATCH (n)-[r]-()\n" +\
        "DELETE n, r\n"
    return query


def get_nodes(label='node'):
    """Generate query returning ids of all nodes of the graph.

    Parameters
    ----------
    label
        Label of the nodes to match, default is 'node'
    """
    query = "MATCH (n:{}) RETURN n.id\n".format(label)
    return query


def get_edges(label_source='node', label_target='node',
              edge_label='edge'):
    """Generate query for getting all the edges of the graph.

    Parameters
    ----------
    label_source
        Label of the source nodes to match, default is 'node'
    label_target
        Label of the target nodes to match, default is 'node'
    edge_label
        Label of the edges to match, default is 'edge'
    """
    query = "MATCH (n:{})-[r:{}]->(m:{})\nRETURN n.id, m.id\n".format(
            label_source, edge_label, label_target)
    return query


def successors_query(var_name, node_id, node_label='node',
                     edge_label='edge', label_succ=None):
    """Generate query for getting the ids of all the successors of a node.

    Parameters
    ----------
    var_name
        Name of the variable corresponding to the node to match
    node_id
        Id of the node to match
    node_label
        Label of the node to match, default is 'node'
    edge_label
        Label of the edge to match, default is 'edge'
    label_succ
        Label of the successors we want to find. node_label if None.
    """
    if label_succ is None:
        label_succ = node_label
    query = (
            "OPTIONAL MATCH ({}:{} {{id : '{}'}})-[:{}]-> (suc:{})".format(
                var_name, node_label, node_id, edge_label, label_succ) +
            "RETURN suc.id"
        )
    return query


def predecessors_query(var_name, node_id, node_label='node',
                       edge_label='edge', label_pred=None):
    """Generate query for getting the ids of all the predecessors of a node.

    Parameters
    ----------
    var_name
        Name of the variable corresponding to the node to match
    node_id
        Id of the node to match
    node_label
        Label of the node to match, default is 'node'
    edge_label
        Label of the edge to match, default is 'edge'
    label_pred
        Label of the predecessors we want to find. node_label if None.
    """
    if label_pred is None:
        label_pred = node_label
    query = (
            "OPTIONAL MATCH (pred:{})-[:{}]-> ({}:{} {{id : '{}'}})".format(
                label_pred, edge_label, var_name, node_label, node_id) +
            "RETURN pred.id"
        )
    return query


def cloning_query(original_var, clone_var, clone_id, clone_id_var,
                  node_label='node', preserv_typing=False,
                  sucs_to_ignore=None, preds_to_ignore=None,
                  carry_vars=None, ignore_naming=False):
    """Generate query for cloning a node.

    Parameters
    ----------
    original_var : str
        Name of the variable corresponding to the original node to clone
    clone_var : str
        Name of the variable corresponding to the new clone node
    clone_id : str
        Id to use for the new node that corresponds to the clone
    clone_id_var : str
        Name of the variable for the id of the new clone node
    node_label
        Label of the node to clone, default is 'node'
    preserv_typing : boolean
        If True, typing edges are preserved on the clone
    sucs_to_ignore : iterable
        List of ids of successors of the original node to ignore
        while reconnecting edges to the new clone node
    preds_to_ignore : iterable
        List of ids of predecessors of the original node to ignore
        while reconnecting edges to the new clone node
    carry_vars : iterable
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
    if sucs_to_ignore is None:
        sucs_to_ignore = set()
    if preds_to_ignore is None:
        preds_to_ignore = set()

    carry_vars.add(original_var)
    query = ""

    if ignore_naming is True:
        query += (
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_var) +
            "CREATE ({}:{}) \n".format(
                clone_var, node_label) +
            "WITH {}, toString(id({})) as {}, {}.id as original_old, ".format(
                clone_var, clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + " \n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to neo4j-generated id\n" +
            "SET {}.id = toString(id({})), {}.count = NULL\n".format(
                clone_var, clone_var, clone_var) +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var) +
            "WITH {}, toString(id({})) as {}, ".format(
                clone_var, clone_var, clone_id_var) +
            ", ".join(carry_vars) + " \n"
        )
    else:
        query += (
            "// search for a node with the same id as the clone id\n" +
            "OPTIONAL MATCH (same_id_node:{} {{ id : '{}'}}) \n".format(
                node_label, clone_id) +
            "WITH same_id_node,  " +
            "CASE WHEN same_id_node IS NOT NULL "
            "THEN (coalesce(same_id_node.count, 0) + 1) " +
            "ELSE 0 END AS same_id_node_new_count, " +
            ", ".join(carry_vars) + "\n" +
            "// generate new id if the same id node was found\n" +
            "// and filter edges which will be removed \n" +
            "WITH same_id_node, same_id_node_new_count, " +
            "'{}' + CASE WHEN same_id_node_new_count <> 0 ".format(clone_id) +
            "THEN toString(same_id_node_new_count) ELSE '' END as {}, ".format(
                clone_id_var) +
            ", ".join(carry_vars) + "\n" +
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_id_var) +
            "CREATE ({}:{}) \n".format(
                clone_var, node_label) +
            "WITH same_id_node, same_id_node_new_count, {}, {}, "
            "{}.id as original_old, ".format(
                clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + "\n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to the generated id\n" +
            "SET {}.id = {}, {}.count = NULL, ".format(
                clone_var, clone_id_var, clone_var) +
            "same_id_node.count = same_id_node_new_count + 1\n" +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var)
        )
    carry_vars.add(clone_id_var)
    carry_vars.add(clone_var)

    query += (
        "WITH [{}] as sucIgnore, ".format(
            ", ".join("'{}'".format(n) for n in sucs_to_ignore)) +
        "[{}] as predIgnore, ".format(
            ", ".join("'{}'".format(n) for n in preds_to_ignore)) +
        ", ".join(carry_vars) + " \n"
    )
    query += (
        "// match successors and out-edges of a node to be cloned\n" +
        "OPTIONAL MATCH ({})-[out_edge:edge]->(suc) \n".format(original_var) +
        "WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore\n" +
        "WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, predIgnore, " +
        ", ".join(carry_vars) + " \n"
    )

    carry_vars.add("suc_maps")
    query += (
        "// match predecessors and in-edges of a node to be cloned\n" +
        "OPTIONAL MATCH (pred)-[in_edge:edge]->({}) \n".format(original_var) +
        "WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore\n" +
        "WITH collect({neighbor: pred, edge: in_edge}) as pred_maps, " +
        ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("pred_maps")

    query += (
        "// copy all incident edges of the original node to the clone\n" +
        "FOREACH (suc_map IN suc_maps | \n"
        "\tFOREACH (suc IN "
        "CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE ({})-[new_edge:edge]->(suc) \n".format(clone_var) +
        "\t\tSET new_edge = suc_map.edge))\n"
        "FOREACH (pred_map IN pred_maps | \n"
        "\tFOREACH (pred IN "
        "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE (pred)-[new_edge:edge]->({}) \n".format(clone_var) +
        "\t\tSET new_edge = pred_map.edge))\n" +
        "// copy self loop\n" +
        "FOREACH (suc_map IN suc_maps | \n"
        "\tFOREACH (self_loop IN "
        "CASE WHEN suc_map.neighbor = {} THEN [suc_map.edge] ELSE [] END |\n".format(
            original_var) +
        "\t\tMERGE ({})-[new_edge:edge]->({}) \n".format(clone_var, clone_var) +
        "\t\tSET new_edge = self_loop))\n"
    )
    carry_vars.remove("suc_maps")
    carry_vars.remove("pred_maps")

    if preserv_typing:
        query += (
            with_vars(carry_vars) + "\n" +
            "OPTIONAL MATCH ({})-[out_typ_edge:typing]->(suc_typ:node)\n".format(
                                                                original_var) +
            "WITH collect({neighbor: suc_typ, edge: out_typ_edge}) as suc_typ_maps, " +
            ", ".join(carry_vars) + " \n"
            )
        carry_vars.add("suc_typ_maps")
        query += (
            "OPTIONAL MATCH (pred_typ:node)-[in_typ_edge:typing]->({}) \n".format(
                                                                original_var) + 
            "WITH collect({neighbor: pred_typ, edge: in_typ_edge}) as pred_typ_maps, " +
            ", ".join(carry_vars) + " \n"
            )
        carry_vars.add("pred_typ_maps")

        query += (
            "// copy all incident typing edges of the original node to the clone\n" +
            "FOREACH (suc_map IN suc_typ_maps | \n"
            "\tFOREACH (suc IN "
            "CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE ({})-[new_edge:typing]->(suc) \n".format(clone_var) +
            "\t\tSET new_edge = suc_map.edge))\n"
            "FOREACH (pred_map IN pred_typ_maps | \n"
            "\tFOREACH (pred IN "
            "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE (pred)-[new_edge:typing]->({}) \n".format(clone_var) +
            "\t\tSET new_edge = pred_map.edge))\n"
        )
        carry_vars.remove("suc_typ_maps")
        carry_vars.remove("pred_typ_maps")

    return query, carry_vars


def merging_query(original_vars, merged_var, merged_id, merged_id_var,
                  node_label='node', edge_label='edge',
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
    if edge_label is None:
        edge_label = ""
    else:
        edge_label = ":" + edge_label

    if carry_vars is None:
        carry_vars = set(original_vars)

    query = ""

    query += (
        "// use the APOC procedure 'apoc.refactor.mergeNodes' to merge nodes\n"
        "CALL apoc.refactor.mergeNodes([{}], {{properties: 'combine'}})\n".format(
            ", ".join(original_vars)) +
        "YIELD node as {}\n".format(merged_var)
    )
    carry_vars.add(merged_var)
    for n in original_vars:
        if n != merged_var:
            carry_vars.remove(n)

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

    query += (
        "// find and merge multiple relations resulting from the node merge\n"
        "OPTIONAL MATCH ({})-[out_rel{}]->(suc)\n".format(merged_var,
                                                          edge_label) +
        "WITH collect({neighbor: suc, edge: out_rel}) as suc_maps, " +
        ", ".join(carry_vars) + "\n" +
        "OPTIONAL MATCH (pred)-[in_rel{}]->({})\n".format(edge_label,
                                                          merged_var) +
        "WHERE pred.id <> {}.id\n".format(merged_var) +
        "WITH collect({neighbor: pred, edge: in_rel}) as pred_maps, suc_maps, " +
        ", ".join(carry_vars) + "\n" +
        "WITH apoc.map.groupByMulti(suc_maps, 'neighbor') as suc_maps, "
        "apoc.map.groupByMulti(pred_maps, 'neighbor') as pred_maps, " +
        ", ".join(carry_vars) + "\n" +
        "WITH REDUCE(edges=[],  k in filter(k in keys(suc_maps) "
        "WHERE length(suc_maps[k]) > 1 ) | \n"
        "\tedges + [suc_maps[k]]) + \n"
        "\tREDUCE(edges=[],  k in filter(k in keys(pred_maps) "
        "WHERE length(pred_maps[k]) > 1)| \n"
        "\t\tedges + [pred_maps[k]]) as all_merge_edges, " +
        ", ".join(carry_vars) + "\n" +
        "UNWIND all_merge_edges as edge_list\n"
        "\tCALL apoc.refactor.mergeRelationships(\n"
        "\t\tREDUCE(rels=[], el in edge_list | rels + el['edge']), "
        " {properties: 'combine'})\n"
        "\tYIELD rel\n"
    )
    return query, carry_vars


def merging_query1(original_vars, merged_var, merged_id, merged_id_var,
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
        carry_vars = set(original_vars)

    query = "// accumulate all the attrs of the nodes to be merged\n"
    query += "WITH [] as new_props, " + ", ".join(carry_vars) + "\n"

    for n in original_vars:
        query += (
            "WITH new_props + REDUCE(pairs = [], k in keys({}) | \n".format(n) +
            "\tpairs + REDUCE(inner_pairs = [], v in {}[k] | \n".format(n) +
            "\t\tinner_pairs + {key: k, value: v})) as new_props, " +
            ", ".join(carry_vars) + "\n"
        )

    query += (
        "WITH apoc.map.groupByMulti(new_props, 'key') as new_props, " +
        ", ".join(carry_vars) + "\n" +
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys(new_props) | \n"
        "\tpairs + [k, REDUCE(values=[], v in new_props[k] | \n"
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as new_props, " +
        ", ".join(carry_vars) + "\n"
        "SET {} = new_props\n".format(original_vars[0])
    )

    carry_vars.remove(original_vars[0])
    query += (
        "WITH {} as {}, ".format(original_vars[0], merged_var) +
        ", ".join(carry_vars) + "\n"
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

    query += (
        "// accumulate all the attrs of the edges incident to the merged nodes\n"
        "WITH [] as suc_maps, [] as pred_maps, " +
        # "\t[{}] as self_loops, ".format(", ".join(
        #     "toString(id({}))".format(n) for n in original_vars[1:]) + ", toString(id({}))".format(
        #         merged_var)) +
        ", ".join(carry_vars) + "\n"
    )

    query += (
        "OPTIONAL MATCH ({})-[out_rel:{}]->(suc)\n".format(merged_var,
                                                           edge_label) +
        "WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, " +
        "pred_maps, " + ", ".join(carry_vars) + "\n" +
        "OPTIONAL MATCH (pred)-[in_rel:{}]->({})\n".format(edge_label,
                                                           merged_var) +
        "WITH pred_maps + collect({id: id(pred), neighbor: pred, edge: in_rel}) as pred_maps, " +
        "suc_maps, " + ", ".join(carry_vars) + "\n"
    )
    for n in original_vars[1:]:
        query += (
            "OPTIONAL MATCH ({})-[out_rel:{}]->(suc)\n".format(n, edge_label) +
            "WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, " +
            "pred_maps, " + ", ".join(carry_vars) + "\n" +
            "OPTIONAL MATCH (pred)-[in_rel:{}]->({})\n".format(edge_label, n) +
            "WITH pred_maps + collect({id: id(pred), neighbor: pred, edge: in_rel}) as pred_maps, " +
            "suc_maps, " + ", ".join(carry_vars) + "\n"
        )

    query += (
        "WITH apoc.map.groupByMulti(suc_maps, 'id') as suc_props, " +
        "REDUCE(list=[], map in suc_maps | \n"
        "\tlist + CASE WHEN NOT map['neighbor'] IS NULL THEN [map['neighbor']] ELSE [] END) as suc_nodes, "
        "apoc.map.groupByMulti(pred_maps, 'id') as pred_props, " +
        "REDUCE(list=[], map in pred_maps | \n"
        "\tlist + CASE WHEN NOT map['neighbor'] IS NULL THEN [map['neighbor']] ELSE [] END) as pred_nodes, " +
        "\tREDUCE(l=[], el in suc_maps + pred_maps| \n" +
        "\t\tl + CASE WHEN el['id'] IN [{}] THEN [toString(el['id'])] ELSE [] END)".format(
            ",".join(["id({})".format(v) for v in [merged_var] + original_vars[1:]])) +
        " as self_loops, " +
        ", ".join(carry_vars) + "\n"
    )
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
        query += (
            "// accumulate all the attrs of the edges incident to the merged nodes\n"
            "WITH [] as suc_typings, [] as pred_typings, " +
            ", ".join(carry_vars) + "\n"
        )
        query += (
            "OPTIONAL MATCH ({})-[:typing]->(suc)\n".format(merged_var) +
            "WITH suc_typings + collect(suc) as suc_typings, " +
            "pred_typings, " + ", ".join(carry_vars) + "\n" +
            "OPTIONAL MATCH (pred)-[:typing]->({})\n".format(merged_var) +
            "WITH pred_typings + collect(pred) as pred_typings, " +
            "suc_typings, " + ", ".join(carry_vars) + "\n"
        )
        for n in original_vars[1:]:
            query += (
                "OPTIONAL MATCH ({})-[:typing]->(suc)\n".format(n) +
                "WITH suc_typings + collect(suc) as suc_typings, " +
                "pred_typings, " + ", ".join(carry_vars) + "\n" +
                "OPTIONAL MATCH (pred)-[:typing]->({})\n".format(n) +
                "WITH pred_typings + collect(pred) as pred_typings, " +
                "suc_typings, " + ", ".join(carry_vars) + "\n"
            )
        query += (
            "FOREACH(suc in suc_typings |\n" +
            "\tMERGE ({})-[:typing]->(suc))\n".format(merged_var) +
            "FOREACH(pred in pred_typings |\n" +
            "\tMERGE (pred)-[:typing]->({}))\n".format(merged_var)
        )

    for n in original_vars[1:]:
        query += "DETACH DELETE ({})\n".format(n)

    return query, carry_vars


def find_matching(pattern, nodes=None, node_label='node', edge_label='edge'):
    """Query that performs pattern match in the graph.

    Parameters
    ----------
    pattern : nx.(Di)Graph
        Graph object representing a pattern to search for
    nodes : iterable, optional
        Collection of ids of nodes to constraint the search space of matching
    node_label
        Label of the node to match, default is 'node'
    edge_label
        Label of the edges to match, default is 'edge'
    """
    query =\
        "MATCH {}".format(
            ", ".join("({}:{})".format(n, node_label) for n in pattern.nodes()))
    if len(pattern.edges()) > 0:
        query += ", {}".format(
            ", ".join("({})-[:{}]->({})".format(u, edge_label, v) for u, v in pattern.edges())) + "\n"
    else:
        query += "\n"

    if nodes is not None:
        query +=\
            "WHERE " + " AND ".join(
                "{}.id IN [{}]".format(
                    pattern_n, ", ".join("'{}'".format(n) for n in nodes))
                for pattern_n in pattern.nodes()) + "\n"
    else:
        nodes_with_attrs = []
        for n, attrs in pattern.nodes(data=True):
            if len(attrs) != 0:
                for k in attrs.keys():
                    nodes_with_attrs.append((n, k, attrs[k]))
        print(nodes_with_attrs)
        if len(nodes_with_attrs) != 0:
            query += (
                "WHERE " + 
                " AND ".join(["{}.{} = [{}]".format(
                    n, k, ", ".join(
                        "'{}'".format(v) for v in val)) for n, k, val in nodes_with_attrs]) + "\n"
            )

    query += "RETURN {}".format(", ".join(pattern.nodes()))

    return query


def match_pattern_instance(pattern, pattern_vars, instance,
                           node_label='node', edge_label='edge'):
    """Query to match an instance of the pattern.

    Parameters
    ----------
    pattern : nx.(Di)Graph
        Graph object representing a pattern
    instance : dict
        Instance of the pattern in the graph, dictionary
        whose keys are node ids of the pattern and whose
        values are ids of the nodes of the graph
    """
    if edge_label is None:
        edge_label = ""
    else:
        edge_label = ":" + edge_label
    query =\
        match_nodes(instance, label=node_label)

    if len(pattern.edges()) > 0:
        query +=\
            ", " +\
            ", ".join(
                "({})-[{}{}]->({})".format(
                    pattern_vars[u],
                    str(pattern_vars[u]) + "_" + str(pattern_vars[v]),
                    edge_label,
                    pattern_vars[v])
                for u, v in pattern.edges())
    else:
        query += "\n"
    return query


def get_node(node_id, node_label='node'):
    """Get node by its id (match and return it)."""
    return match_node("n", node_id, label=node_label) + return_vars(["n"])


def get_edge(s, t, source_label='node', target_label='node', edge_label='edge'):
    """Get edge by the ids of its incident nodes."""
    query =\
        "MATCH (n:{} {{id: '{}'}})-[rel:{}]->(m:{} {{id: '{}'}})".format(
            source_label,
            s,
            edge_label,
            target_label,
            t) +\
        "RETURN rel\n"

    return query


def constraint_query(node_var, node_label, node_property):
    """Generate query for creating a constraint on a property."""
    query = "CONSTRAINT ON ({}:{}) ASSERT {}.{} IS UNIQUE".format(
                node_var,
                node_label,
                node_var,
                node_property
                    )
    return query


def merge_properties(var_list, new_props_var, carry_vars=None,
                     method='union'):
    """Merge properties of a list of nodes/edges.

    Parameters
    ----------
    var_list : iterable
        Collection of variables corresponding to the
        nodes/edges whose properties are merged
    new_props_var : str
        Name of the variable corresponding to the
        map of new properties
    carry_vars : iterable
        Collection of variables to carry
    method : str
        'union' or 'intersection'
    """
    if method == 'union':
        return props_union(var_list, new_props_var, carry_vars)
    elif method == "intersection":
        return props_intersection(var_list, new_props_var, carry_vars)
    else:
        raise ValueError("Merging method {} is not defined!".format(method))


def merge_properties_from_list(list_var, new_props_var, carry_vars=None,
                               method='union'):
    """Merge properties of a list of nodes/edges.

    Parameters
    ----------
    list_var : str
        Name of the variable corresponding to the list
        of nodes/edges whose properties are merged
    new_props_var : str
        Name of the variable corresponding to the
        map of new properties
    carry_vars : iterable
        Collection of variables to carry
    method : str
        'union' or 'intersection'
    """
    if method == 'union':
        return props_union_from_list(list_var, new_props_var, carry_vars)
    elif method == "intersection":
        return props_intersection_from_list(list_var, new_props_var, carry_vars)
    else:
        raise ValueError("Merging method {} is not defined!".format(method))


def props_union(var_list, new_props_var, carry_vars=None):
    """Perform the union of the properties of a list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set(var_list)
    else:
        carry_vars.update(var_list)

    query = "//Perform the union of the properties of "
    query += ", ".join(var_list) + "\n"
    query += "WITH [] as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"

    for var in var_list:
        query +=\
            "WITH {} + REDUCE(pairs = [], k in filter(k in keys({}) WHERE k <> 'id') | \n".format(
                new_props_var, var) +\
            "\tpairs + REDUCE(inner_pairs = [], v in {}[k] | \n".format(
                var) +\
            "\t\t inner_pairs + {{key: k, value: v}})) as {},  ".format(
                new_props_var) +\
            ", ".join(carry_vars) + "\n"
    query +=\
        "WITH apoc.map.groupByMulti({}, 'key') as {}, ".format(
            new_props_var, new_props_var) +\
        ", ".join(carry_vars) + "\n" +\
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys({}) | \n".format(
            new_props_var) +\
        "\tpairs + [k, REDUCE(values=[], v in {}[k] | \n".format(
            new_props_var) +\
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as {}, ".format(
            new_props_var) +\
        ", ".join(carry_vars) + "\n"

    carry_vars.add(new_props_var)
    return query


def props_union_from_list(list_var, new_props_var, carry_vars=None):
    """Perform the union of the properties of a list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set([list_var])
    else:
        carry_vars.add(list_var)

    carry_vars.remove(list_var)
    query = "UNWIND {} as prop_to_merge\n".format(list_var)

    query += (
        "// accumulate all the attrs of the nodes to be merged\n" +
        "WITH [] as new_props, prop_to_merge, " + ", ".join(carry_vars) + "\n" +
        "WITH new_props + REDUCE(pairs = [], k in filter(k in keys(prop_to_merge) WHERE k <> 'id') | \n" +
        "\tpairs + REDUCE(inner_pairs = [], v in prop_to_merge[k] | \n" +
        "\t\tinner_pairs + {key: k, value: v})) as new_props, prop_to_merge, " +
        ", ".join(carry_vars) + "\n"
    )

    query += (
        "WITH collect(prop_to_merge) as {}, ".format(list_var) +
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
        ", ".join(carry_vars) + "\n"
    )
    return query


def props_intersection(var_list, new_props_var, carry_vars=None):
    """Perform the intersection of the properties of a list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set(var_list)
    else:
        carry_vars.update(var_list)

    query = "\n//Perform the intersection of the properties of "
    query += ", ".join(var_list) + "\n"
    query += "WITH [] as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"

    var_first = var_list[0]

    query +=\
        "WITH {} + REDUCE(pairs = [], k in keys({}) | \n".format(
            new_props_var, var_first) +\
        "\tCASE WHEN ALL(others in [{}] WHERE k in keys(others))\n".format(
            ", ".join(var_list[1:])) +\
        "\tTHEN\n" +\
        "\t\tpairs + REDUCE(inner_pairs = [], v in {}[k] | \n".format(
            var_first) +\
        "\t\t\tCASE WHEN ALL(others in [{}] WHERE v in others[k])\n".format(
            ", ".join(var_list[1:])) +\
        "\t\t\tTHEN\n" +\
        "\t\t\t\tinner_pairs + {key: k, value: v}\n" +\
        "\t\t\tELSE\n" +\
        "\t\t\t\tinner_pairs\n" +\
        "\t\t\tEND)\n" +\
        "\tELSE\n" +\
        "\t\tpairs\n" +\
        "\tEND) as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"
    query +=\
        "WITH apoc.map.groupByMulti({}, 'key') as {}, ".format(
            new_props_var, new_props_var) +\
        ", ".join(carry_vars) + "\n" +\
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys({}) | \n".format(
            new_props_var) +\
        "\tpairs + [k, REDUCE(values=[], v in {}[k] | \n".format(
            new_props_var) +\
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as {}, ".format(
            new_props_var) +\
        ", ".join(carry_vars) + "\n"

    carry_vars.add(new_props_var)
    return query


def props_intersection_from_list(list_var, new_props_var, carry_vars=None):
    """Perform the intersection of the properties of a list of nodes/edges."""
    if carry_vars is None:
        carry_vars = set([list_var])
    else:
        carry_vars.add(list_var)

    query = "\n//Perform the intersection of the properties of {}".format(
        list_var) + "\n"
    query += "WITH [] as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"

    query +=\
        "WITH {} + REDUCE(pairs = [], k in keys({}[0]) | pairs +\n".format(
            new_props_var, list_var) +\
        "\tCASE WHEN ALL(other in {} WHERE k in keys(other))\n".format(
            list_var) +\
        "\tTHEN\n" +\
        "\t\tREDUCE(inner_pairs = [], v in {}[0][k] | inner_pairs +\n".format(
            list_var) +\
        "\t\t\tCASE WHEN ALL(other in {} WHERE v in other[k])\n".format(
            list_var) +\
        "\t\t\tTHEN\n" +\
        "\t\t\t\t{key: k, value: v}\n" +\
        "\t\t\tELSE\n" +\
        "\t\t\t\t[]\n" +\
        "\t\t\tEND)\n" +\
        "\tELSE\n" +\
        "\t\t[]\n" +\
        "\tEND) as {}, ".format(new_props_var) +\
        ", ".join(carry_vars) + "\n"
    query +=\
        "WITH apoc.map.groupByMulti({}, 'key') as {}, ".format(
            new_props_var, new_props_var) +\
        ", ".join(carry_vars) + "\n" +\
        "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys({}) | \n".format(
            new_props_var) +\
        "\tpairs + [k, REDUCE(values=[], v in {}[k] | \n".format(
            new_props_var) +\
        "\t\tvalues + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as {}, ".format(
            new_props_var) +\
        ", ".join(carry_vars) + "\n"

    carry_vars.add(new_props_var)
    return query


def duplicate_node(original_var, clone_var, clone_id, clone_id_var,
                   original_graph, clone_graph,
                   attach=True, preserv_typing=False,
                   sucs_to_ignore=None, preds_to_ignore=None,
                   carry_vars=None, ignore_naming=False):
    """Generate query for duplicating a node in an other graph.

    Parameters
    ----------
    original_var : str
        Name of the variable corresponding to the original node to clone
    clone_var : str
        Name of the variable corresponding to the new clone node
    clone_id : str
        Id to use for the new node that corresponds to the clone
    clone_id_var : str
        Name of the variable for the id of the new clone node
    original_graph : str
        Label of the graph with the node to clone
    clone_graph : str
        Label of the graph where to clone the node
    sucs_to_ignore : iterable
        List of ids of successors of the original node to ignore
        while reconnecting edges to the new clone node
    preds_to_ignore : iterable
        List of ids of predecessors of the original node to ignore
        while reconnecting edges to the new clone node
    carry_vars : iterable
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
    if sucs_to_ignore is None:
        sucs_to_ignore = set()
    if preds_to_ignore is None:
        preds_to_ignore = set()

    carry_vars.add(original_var)

    if ignore_naming is True:
        query = (
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_var) +
            "CREATE ({}:node:{}) \n".format(
                clone_var, clone_graph) +
            "MERGE ({})-[:typing]->({})".format(original_var, clone_var) +
            "WITH {}, toString(id({})) as {}, {}.id as original_old, ".format(
                clone_var, clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + " \n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to neo4j-generated id\n" +
            "SET {}.id = toString(id({})), {}.count = NULL\n".format(
                clone_var, clone_var, clone_var) +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var) +
            "WITH {}, toString(id({})) as {}, ".format(
                clone_var, clone_var, clone_id_var) +
            ", ".join(carry_vars) + " \n"
        )
    else:
        query = (
            "// search for a node with the same id as the clone id\n" +
            "OPTIONAL MATCH (same_id_node:node:{} {{ id : '{}'}}) \n".format(
                clone_graph, clone_id) +
            "WITH same_id_node,  " +
            "CASE WHEN same_id_node IS NOT NULL "
            "THEN (coalesce(same_id_node.count, 0) + 1) " +
            "ELSE 0 END AS same_id_node_new_count, " +
            ", ".join(carry_vars) + "\n" +
            "// generate new id if the same id node was found\n" +
            "// and filter edges which will be removed \n" +
            "WITH same_id_node, same_id_node_new_count, " +
            "'{}' + CASE WHEN same_id_node_new_count <> 0 ".format(clone_id) +
            "THEN toString(same_id_node_new_count) ELSE '' END as {}, ".format(
                clone_id_var) +
            ", ".join(carry_vars) + "\n" +
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_id_var) +
            "CREATE ({}:node:{}) \n".format(
                clone_var, clone_graph) +
            "MERGE ({})-[:typing]->({})".format(original_var,
                                                clone_var) +
            "WITH same_id_node, same_id_node_new_count, {}, {}, "
            "{}.id as original_old, ".format(
                clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + "\n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to the generated id\n" +
            "SET {}.id = {}, {}.count = NULL, ".format(
                clone_var, clone_id_var, clone_var) +
            "same_id_node.count = same_id_node_new_count + 1\n" +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var)
        )
    carry_vars.add(clone_var)
    query += (
        "WITH [{}] as sucIgnore, ".format(
            ", ".join("'{}'".format(n) for n in sucs_to_ignore)) +
        "[{}] as predIgnore, ".format(
            ", ".join("'{}'".format(n) for n in preds_to_ignore)) +
        ", ".join(carry_vars) + " \n"
    )
    query += (
        "// Match successors and out-edges of a node to be cloned in the clone graph\n" +
        "OPTIONAL MATCH ({})-[out_edge:edge]->(:node:{})-[:typing]->(suc:node:{})\n".format(
                                                            original_var,
                                                            original_graph,
                                                            clone_graph)
    )
    query += (
        "WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore\n" +
        "WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, " +
        "predIgnore, " + ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("suc_maps")

    query += (
        "// match predecessors and in-edges of a node to be cloned in the clone graph\n" +
        "OPTIONAL MATCH (pred:node:{})<-[:typing]-(:node:{})-[in_edge:edge]->({}) \n".format(
                                                            clone_graph,
                                                            original_graph,
                                                            original_var)
        )
    query += (
        "WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore\n" +
        "WITH collect({neighbor: pred, edge: in_edge}) as pred_maps, " +
        ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("pred_maps")

    query += (
        "// copy all incident edges of the original node to the clone\n" +
        "FOREACH (suc_map IN suc_maps | \n"
        "\tFOREACH (suc IN "
        "CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE ({})-[new_edge:edge]->(suc) \n".format(clone_var) +
        "\t\tSET new_edge = suc_map.edge))\n"
        "FOREACH (pred_map IN pred_maps | \n"
        "\tFOREACH (pred IN "
        "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE (pred)-[new_edge:edge]->({}) \n".format(clone_var) +
        "\t\tSET new_edge = pred_map.edge))\n"
    )
    carry_vars.remove("suc_maps")
    carry_vars.remove("pred_maps")

    if preserv_typing:
        query += (
            with_vars(carry_vars) + "\n" +
            "OPTIONAL MATCH ({})-[out_typ_edge:typing]->(suc_typ:node)\n".format(
                                                                original_var) +
            "WITH collect({neighbor: suc_typ, edge: out_typ_edge}) as suc_typ_maps, " +
            ", ".join(carry_vars) + " \n"
            )
        carry_vars.add("suc_typ_maps")
        query += (
            "OPTIONAL MATCH (pred_typ:node)-[in_typ_edge:typing]->({}) \n".format(
                                                                original_var) + 
            "WITH collect({neighbor: pred_typ, edge: in_typ_edge}) as pred_typ_maps, " +
            ", ".join(carry_vars) + " \n"
            )
        carry_vars.add("pred_typ_maps")

        query += (
            "// copy all incident typing edges of the original node to the clone\n" +
            "FOREACH (suc_map IN suc_typ_maps | \n"
            "\tFOREACH (suc IN "
            "CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE ({})-[new_edge:typing]->(suc) \n".format(clone_var) +
            "\t\tSET new_edge = suc_map.edge))\n"
            "FOREACH (pred_map IN pred_typ_maps | \n"
            "\tFOREACH (pred IN "
            "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE (pred)-[new_edge:typing]->({}) \n".format(clone_var) +
            "\t\tSET new_edge = pred_map.edge))\n"
        )
        carry_vars.remove("suc_typ_maps")
        carry_vars.remove("pred_typ_maps")

    return query, carry_vars


def clone_graph(original_graph, cloned_graph, carry_vars=None):
    """Clone all the nodes and edges of a graph in an other.
    """
    if carry_vars is None:
        carry_vars = set()

    query =\
        "MATCH (n:node:{})\n".format(original_graph) +\
        duplicate_node('n', 'm', 'id', 'm_id_var',
                       original_graph=original_graph,
                       clone_graph=cloned_graph,
                       carry_vars=carry_vars,
                       ignore_naming=True)[0]
    return query, carry_vars


def merging_from_list(list_var, merged_var, merged_id, merged_id_var,
                      node_label='node', edge_label='edge', merge_typing=False,
                      carry_vars=None, ignore_naming=False,
                      multiple_rows=False, multiple_var=None):
    """Generate query for merging nodes.

    Parameters
    ----------
    list_var : str
        Name of the variable corresponding to the list of nodes to clone
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
    merge_typing : boolean
        If true, typing edges are merged
    carry_vars : str
        Collection of variables to carry
    multiple_rows : boolean
        True when multiple merging are happening in the same time
         on diferent rows
    multiple_var : str
        Variable which has a different value on each row. Used for controlling
        the merging on multiple rows

    Returns
    -------
    query : str
        Generated query
    carry_vars : set
        Updated collection of variables to carry
    """
    if carry_vars is None:
        carry_vars = set()

    carry_vars.remove(list_var)
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

    if multiple_rows:
        query += "UNWIND {} AS node_to_merge\n".format(list_var)
        carry_vars.remove(list_var)
        query += (
            "//create a map from node ids to the id of the merged_node\n" +
            "WITH {{old_node:node_to_merge.id,  new_node:{}}} as id_to_merged_id, ".format(
                merged_var) +
            "node_to_merge, " + ", ".join(carry_vars) + "\n" +
            "WITH collect(id_to_merged_id) as ids_to_merged_id, collect(node_to_merge) as {}, ".format(
                list_var) + ", ".join(carry_vars) + "\n"
            )
        carry_vars.add(list_var)
        query += (
            "WITH apoc.map.groupByMulti(ids_to_merged_id, 'old_node') as ids_to_merged_id, " +
            ", ".join(carry_vars) + "\n" +
            "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys(ids_to_merged_id) | \n"
            "\tpairs + [k, REDUCE(values=[], v in ids_to_merged_id[k] | \n"
            "\t\tvalues + CASE WHEN v.new_node IN values THEN [] ELSE v.new_node END)])) as ids_to_merged_id, " +
            ", ".join(carry_vars) + "\n"
            )
        carry_vars.difference_update([multiple_var, list_var, merged_var, merged_id_var])
        query += (
            "WITH collect({{n:{}, nodes_to_merge:{}, merged_node: {}, merged_id: {}}}) ".format(
                multiple_var, list_var, merged_var, merged_id_var) +
            "as all_n, collect(ids_to_merged_id) as ids_to_merged_id, " +
            ", ".join(carry_vars) + "\n" +
            "WITH reduce(acc={}, x in ids_to_merged_id | apoc.map.merge(acc, x))" +
            " as ids_to_merged_id, all_n, " +
            ", ".join(carry_vars) + "\n" +
            "UNWIND all_n as n_maps\n" +
            "WITH n_maps.n as {}, n_maps.nodes_to_merge as {}, ".format(
                multiple_var, list_var) +
            "n_maps.merged_node as {}, n_maps.merged_id as {}, ".format(
                merged_var, merged_id_var) +
            "ids_to_merged_id, " + ", ".join(carry_vars) + "\n"
            )
        carry_vars.update([multiple_var, list_var, merged_var, merged_id_var, 'ids_to_merged_id'])

    query += "UNWIND {} AS node_to_merge\n".format(list_var)
    carry_vars.remove(list_var)

    if multiple_rows:
        query += (
            "// accumulate all the attrs of the edges incident to the merged nodes\n"
            "WITH node_to_merge, " + ", ".join(carry_vars) + "\n"
            "OPTIONAL MATCH (node_to_merge)-[out_rel:{}]->(suc)\n".format(edge_label) +
            "WITH CASE WHEN suc.id IN keys(ids_to_merged_id)\n" +
            "\t\tTHEN {id: id(ids_to_merged_id[suc.id][0]), neighbor: ids_to_merged_id[suc.id][0], edge: out_rel}\n" +
            "\t\tELSE {id: id(suc), neighbor: suc, edge: out_rel} END AS suc_map, " +
            "node_to_merge, " + ", ".join(carry_vars) + "\n" +
            "WITH collect(suc_map) as suc_maps, " +
            "node_to_merge, " + ", ".join(carry_vars) + "\n" +
            "OPTIONAL MATCH (pred)-[in_rel:{}]->(node_to_merge)\n".format(edge_label) +
            "WITH CASE WHEN pred.id IN keys(ids_to_merged_id)\n" +
            "\t\tTHEN {id: id(ids_to_merged_id[pred.id][0]), neighbor: ids_to_merged_id[pred.id][0], edge: in_rel}\n" +
            "\t\tELSE {id: id(pred), neighbor: pred, edge: in_rel} END AS pred_map, " +
            "node_to_merge, suc_maps, " + ", ".join(carry_vars) + "\n" +
            "WITH collect(pred_map) as pred_maps, " +
            "suc_maps, node_to_merge, " + ", ".join(carry_vars) + "\n"
        )
    else:
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
        ", ".join(carry_vars) + "\n"
    )
    query += (
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

    query += (
        "WITH " + ", ".join(carry_vars) + "\n" +
        "FOREACH(node in filter(x IN {} WHERE x <> {}) |\n".format(
            list_var, merged_var) +
        "\tDETACH DELETE node)\n"
    )


    carry_vars.remove(list_var)

    return query, carry_vars


def multiple_cloning_query(original_var, clone_var, clone_id, clone_id_var,
                           number_of_clone_var=None,
                           node_label='node', preserv_typing=False,
                           sucs_to_ignore=None, preds_to_ignore=None,
                           carry_vars=None, ignore_naming=False,
                           multiple_rows=False):
    """Generate query for cloning a node.

    Parameters
    ----------
    original_var : str
        Name of the variable corresponding to the original node to clone
    clone_var : str
        Name of the variable corresponding to the new clone node
    clone_id : str
        Id to use for the new node that corresponds to the clone
    clone_id_var : str
        Name of the variable for the id of the new clone node
    node_label
        Label of the node to clone, default is 'node'
    preserv_typing : boolean
        If True, typing edges are preserved on the clone
    sucs_to_ignore : iterable
        List of ids of successors of the original node to ignore
        while reconnecting edges to the new clone node
    preds_to_ignore : iterable
        List of ids of predecessors of the original node to ignore
        while reconnecting edges to the new clone node
    carry_vars : iterable
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
    if sucs_to_ignore is None:
        sucs_to_ignore = set()
    if preds_to_ignore is None:
        preds_to_ignore = set()

    carry_vars.add(original_var)
    query = ""

    query += "UNWIND range(1, {}) as clone_number\n".format(
                                                        number_of_clone_var)
    carry_vars.add('clone_number')
    if ignore_naming is True:
        query += (
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_var) +
            "CREATE ({}:{}) \n".format(
                clone_var, node_label) +
            "WITH {}, toString(id({})) as {}, {}.id as original_old, ".format(
                clone_var, clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + " \n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to neo4j-generated id\n" +
            "SET {}.id = toString(id({})), {}.count = NULL\n".format(
                clone_var, clone_var, clone_var) +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var) +
            "WITH {}, toString(id({})) as {}, ".format(
                clone_var, clone_var, clone_id_var) +
            ", ".join(carry_vars) + " \n"
        )
    else:
        query += (
            "// search for a node with the same id as the clone id\n" +
            "OPTIONAL MATCH (same_id_node:{} {{ id : '{}'}}) \n".format(
                node_label, clone_id) +
            "WITH same_id_node,  " +
            "CASE WHEN same_id_node IS NOT NULL "
            "THEN (coalesce(same_id_node.count, 0) + 1) " +
            "ELSE 0 END AS same_id_node_new_count, " +
            ", ".join(carry_vars) + "\n" +
            "// generate new id if the same id node was found\n" +
            "// and filter edges which will be removed \n" +
            "WITH same_id_node, same_id_node_new_count, " +
            "'{}' + CASE WHEN same_id_node_new_count <> 0 ".format(clone_id) +
            "THEN toString(same_id_node_new_count) ELSE '' END as {}, ".format(
                clone_id_var) +
            ", ".join(carry_vars) + "\n" +
            "// create a node corresponding to the clone\n" +
            # "CREATE ({}:node) \n".format(clone_var, clone_id_var) +
            "CREATE ({}:{}) \n".format(
                clone_var, node_label) +
            "WITH same_id_node, same_id_node_new_count, {}, {}, "
            "{}.id as original_old, ".format(
                clone_var, clone_id_var, original_var) +
            ", ".join(carry_vars) + "\n" +
            "// set the id property of the original node to NULL\n" +
            "SET {}.id = NULL\n".format(original_var) +
            "// copy all the properties of the original node to the clone\n" +
            "SET {} = {}\n".format(clone_var, original_var) +
            "// set id property of the clone to the generated id\n" +
            "SET {}.id = {}, {}.count = NULL, ".format(
                clone_var, clone_id_var, clone_var) +
            "same_id_node.count = same_id_node_new_count + 1\n" +
            "// set back the id property of the original node\n" +
            "SET {}.id = original_old\n".format(original_var)
        )

    carry_vars.remove('clone_number')
    if multiple_rows:
        query += (
            "\n//create a map from original node id to the clone\n" +
            "WITH {{original_node:{}.id, clones:collect({})+[{}]}} ".format(
                original_var, clone_var, original_var) +
            "as orig_id_to_clone, collect({{clone_id:{}, clone:{}}}) ".format(
                clone_id_var, clone_var) +
            "as clone_maps, " + ", ".join(carry_vars) + "\n"
        )
        carry_vars.difference_update([original_var])
        query += (
            "WITH collect(orig_id_to_clone) as orig_ids_to_clone, " +
            "collect({{orig:{}, clone_maps:clone_maps}}) ".format(original_var) +
            "as all_orig, " + ", ".join(carry_vars) + "\n"
        )
        query += (
            "WITH apoc.map.groupByMulti(orig_ids_to_clone, 'original_node') as orig_ids_to_clone, " +
            "all_orig, " + ", ".join(carry_vars) + "\n" +
            "WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys(orig_ids_to_clone) | \n"
            "\tpairs + [k, REDUCE(values=[], v in orig_ids_to_clone[k] | \n"
            "\t\tvalues + CASE WHEN v.clones IN values THEN [] ELSE v.clones END)])) as orig_ids_to_clone, " +
            "all_orig, " + ", ".join(carry_vars) + "\n"
        )
        carry_vars.add('orig_ids_to_clone')
        query += (
            "UNWIND all_orig as original_map\n" +
            "WITH original_map.orig as {}, ".format(original_var) +
            "original_map.clone_maps as clone_maps, " +
            ", ".join(carry_vars) + "\n"
        )
        carry_vars.add(original_var)
        query += (
            "UNWIND clone_maps as clone_map\n" +
            "WITH clone_map.clone_id as {}, ".format(clone_id_var) +
            "clone_map.clone as {}, ".format(clone_var) +
            ", ".join(carry_vars) + "\n"
        )

    carry_vars.add(clone_id_var)
    carry_vars.add(clone_var)

    query += (
        "WITH [{}] as sucIgnore, ".format(
            ", ".join("'{}'".format(n) for n in sucs_to_ignore)) +
        "[{}] as predIgnore, ".format(
            ", ".join("'{}'".format(n) for n in preds_to_ignore)) +
        ", ".join(carry_vars) + " \n"
    )
    query += (
        "// match successors and out-edges of a node to be cloned\n" +
        "OPTIONAL MATCH ({})-[out_edge:edge]->(suc) \n".format(original_var) +
        "WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore\n" +
        "WITH collect({neighbor: suc, id: suc.id, edge: out_edge}) as suc_maps, predIgnore, " +
        ", ".join(carry_vars) + " \n"
    )

    carry_vars.add("suc_maps")
    query += (
        "// match predecessors and in-edges of a node to be cloned\n" +
        "OPTIONAL MATCH (pred)-[in_edge:edge]->({}) \n".format(original_var) +
        "WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore\n" +
        "WITH collect({neighbor: pred, id: pred.id, edge: in_edge}) as pred_maps, " +
        ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("pred_maps")

    query += (
        "// copy all incident edges of the original node to the clone\n" +
        "FOREACH (suc_map IN suc_maps | \n"
        "\tFOREACH (suc IN CASE\n"
        "\t\t\tWHEN suc_map.neighbor IS NOT NULL AND suc_map.id IN keys(orig_ids_to_clone)\n"
        "\t\t\t\tTHEN orig_ids_to_clone[suc_map.id] \n"
        "\t\t\tWHEN suc_map.neighbor IS NOT NULL\n"
        "\t\t\t\tTHEN [suc_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE ({})-[new_edge:edge]->(suc) \n".format(clone_var) +
        "\t\tSET new_edge = suc_map.edge))\n"
        "FOREACH (pred_map IN pred_maps | \n"
        "\tFOREACH (pred IN CASE\n"
        "\t\t\tWHEN pred_map.neighbor IS NOT NULL AND pred_map.id IN keys(orig_ids_to_clone)\n"
        "\t\t\t\tTHEN orig_ids_to_clone[pred_map.id] \n"
        "\t\t\tWHEN pred_map.neighbor IS NOT NULL\n"
        "\t\t\t\tTHEN [pred_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE (pred)-[new_edge:edge]->({}) \n".format(clone_var) +
        "\t\tSET new_edge = pred_map.edge))\n" +
        "// copy self loop\n" +
        "FOREACH (suc_map IN suc_maps | \n"
        "\tFOREACH (self_loop IN "
        "CASE WHEN suc_map.neighbor = {} THEN [suc_map.edge] ELSE [] END |\n".format(
            original_var) +
        "\t\tMERGE ({})-[new_edge:edge]->({}) \n".format(clone_var, clone_var) +
        "\t\tSET new_edge = self_loop))\n"
    )
    carry_vars.remove("suc_maps")
    carry_vars.remove("pred_maps")

    if preserv_typing:
        query += (
            with_vars(carry_vars) + "\n" +
            "OPTIONAL MATCH ({})-[out_typ_edge:typing]->(suc_typ:node)\n".format(
                                                                original_var) +
            "WITH collect({neighbor: suc_typ, edge: out_typ_edge}) as suc_typ_maps, " +
            ", ".join(carry_vars) + " \n"
            )
        carry_vars.add("suc_typ_maps")
        query += (
            "OPTIONAL MATCH (pred_typ:node)-[in_typ_edge:typing]->({}) \n".format(
                                                                original_var) + 
            "WITH collect({neighbor: pred_typ, edge: in_typ_edge}) as pred_typ_maps, " +
            ", ".join(carry_vars) + " \n"
            )
        carry_vars.add("pred_typ_maps")

        query += (
            "// copy all incident typing edges of the original node to the clone\n" +
            "FOREACH (suc_map IN suc_typ_maps | \n"
            "\tFOREACH (suc IN "
            "CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE ({})-[new_edge:typing]->(suc) \n".format(clone_var) +
            "\t\tSET new_edge = suc_map.edge))\n"
            "FOREACH (pred_map IN pred_typ_maps | \n"
            "\tFOREACH (pred IN "
            "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
            "\t\tMERGE (pred)-[new_edge:typing]->({}) \n".format(clone_var) +
            "\t\tSET new_edge = pred_map.edge))\n"
        )
        carry_vars.remove("suc_typ_maps")
        carry_vars.remove("pred_typ_maps")

    return query, carry_vars


def nb_of_attrs_mismatch(source, target):
    query = (
        "REDUCE(invalid = 0, k in filter(k in keys({}) WHERE k <> 'id') |\n".format(source) +
        "\tinvalid + CASE\n" +
        "\t\tWHEN NOT k IN keys({}) THEN 1\n".format(target) +
        "\t\tELSE REDUCE(invalid_values = 0, v in {}[k] |\n".format(source) +
        "\t\t\tinvalid_values + CASE\n" +
        "\t\t\t\tWHEN NOT v IN {}[k] THEN 1 ELSE 0 END)\n".format(target) +
        "\t\tEND)"
        )
    return query
