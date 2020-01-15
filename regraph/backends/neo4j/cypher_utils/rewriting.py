"""Collection of utils for generation of rewriting-related queries."""
from . import generic

from regraph.attribute_sets import (FiniteSet,
                                    IntegerSet,
                                    RegexSet)
from regraph.exceptions import ReGraphError
from regraph.utils import keys_by_value


def add_node(var_name, node_id, node_id_var, node_label,
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
            "OPTIONAL MATCH (same_id_node:{}) \n".format(
                node_label) +
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
                var_name, node_label, node_id_var)
        )
    else:
        query =\
            "CREATE ({}:{}) \n".format(var_name, node_label) +\
            "SET {}.id = toString(id({})) \n".format(var_name, var_name)
        query += "WITH toString(id({})) as {} ".format(var_name, node_id_var)
        carry_vars.add(var_name)
        query += ", " + ", ".join(carry_vars) + "\n"

    if attrs is not None:
        query += generic.set_attributes(var_name, attrs)

    carry_vars.add(node_id_var)
    carry_vars.add(var_name)
    return query, carry_vars


def add_edge(edge_var, source_var, target_var,
             edge_label, attrs=None, merge=False):
    """Generate query for edge creation.

    source_var
        Name of the variable corresponding to the source
        node
    target_var
        Name of the variable corresponding to the target
        node
    edge_label : optional
        Labels associated with the new edge
    attrs : dict, optional
        Attributes of the new edge
    """
    if merge:
        keyword = "MERGE"
    else:
        keyword = "CREATE"

    query = "{} ({})-[{}:{} {{ {} }}]->({})\n".format(
        keyword, source_var, edge_var, edge_label,
        generic.generate_attributes(attrs), target_var)
    return query


def remove_node(node_var, breakline=True):
    """Query for removal of a node (with side-effects)."""
    return "DETACH DELETE {}\n".format(node_var)


def remove_edge(edge_var, breakline=True):
    """Query for deleting an edge corresponding to the input variable.

    Parameters
    ----------
    edge_var
        Name of the variable corresponding to the edge to remove
    """
    return generic.delete_var(edge_var, False, breakline)


def remove_nodes(var_names, breakline=True):
    """Query for deleting nodes corresponding to the input variables.

    Parameters
    ----------
    var_names : iterable
        Collection of variables corresponding to nodes to remove
    """
    n = ""
    if breakline is True:
        n = "\n"

    return "DETACH DELETE {}{}".format(', '.join(v for v in var_names), n)


def add_attributes(var_name, attrs):
    """Generate a subquery to add attributes to an existing node."""
    query = ""
    for k, value in attrs.items():
        if isinstance(value, IntegerSet):
            if value.is_universal:
                query += "\tSET {}.{} = 'IntegerSet')\n".format(var_name, k)
            else:
                raise ReGraphError(
                    "Non universal IntegerSet is not allowed as "
                    "an attribute value (not implemented)")
        elif isinstance(value, RegexSet):
            if value.is_universal:
                query += "\tSET {}.{} = 'StringSet')\n".format(var_name, k)
            else:
                raise ReGraphError(
                    "Non universal RegexSet is not allowed as "
                    "an attribute value (not implemented)")
        elif isinstance(value, FiniteSet):
            # normalize elements to string
            elements = []
            for el in value:
                if type(el) == str:
                    elements.append("'{}'".format(el))
                else:
                    elements.append("{}".format(el))
            query += (
                "FOREACH (dummy IN CASE WHEN '{}' IN keys({}) THEN [] ELSE [1] END |".format(
                    k, var_name) +
                "\tSET {}.{} = [{}])\n".format(var_name, k, ", ".join(
                    el for el in elements)) +
                "FOREACH(dummy IN CASE WHEN '{}' IN keys({}) THEN [1] ELSE [] END |\n".format(
                    k, var_name) +
                "\tFOREACH(val in [{}] |\n".format(", ".join(el for el in elements)) +
                "\t\tFOREACH(dummy1 IN CASE WHEN NOT val IN {}.{} THEN [1] ELSE [] END |\n".format(
                    var_name, k) +
                "\t\t\tSET {}.{} = extract(el in {}.{} | toString(el)) + [val])))\n".format(var_name, k, var_name, k)
            )
        else:
            raise ValueError(
                "Unknown type of attribute '{}': '{}'".format(k, type(value)))

    return query


def remove_attributes(var_name, attrs):
    """Generate a subquery to remove attributes to an existing node."""
    query = ""
    for k, value in attrs.items():
        if isinstance(value, IntegerSet):
            if value.is_universal:
                query += "\tSET {}.{} = [])\n".format(var_name, k)
            else:
                raise ReGraphError(
                    "Non universal IntegerSet is not allowed as "
                    "an attribute value (not implemented)")
        elif isinstance(value, RegexSet):
            if value.is_universal:
                query += "\tSET {}.{} = [])\n".format(var_name, k)
            else:
                raise ReGraphError(
                    "Non universal RegexSet is not allowed as "
                    "an attribute value (not implemented)")
        elif isinstance(value, FiniteSet):
            elements = []
            for el in value:
                if type(el) == str:
                    elements.append("'{}'".format(el))
                else:
                    elements.append("{}".format(el))
            query += (
                "FOREACH(dummy IN CASE WHEN '{}' IN keys({}) THEN [1] ELSE [] END |\n".format(
                    k, var_name) +
                "\tSET {}.{} = filter(v in {}.{} WHERE NOT v IN [{}])\n".format(
                    var_name, k, var_name, k,
                    ", ".join(["{}".format(
                        "'{}'".format(val) if type(val) != bool else "true" if val else "false") for val in value])) +
                "\tFOREACH(dumy2 IN CASE WHEN size({}.{})=0 THEN [1] ELSE [] END |\n".format(
                    var_name, k) +
                "\t\tREMOVE {}.{}))\n".format(
                    var_name, k)
            )
        else:
            raise ValueError(
                "Unknown type of attribute '{}': '{}'".format(k, type(value)))
    return query


def cloning_query(original_var, clone_var, clone_id, clone_id_var,
                  node_label, edge_labels, sucs_to_ignore=None,
                  preds_to_ignore=None, suc_vars_to_ignore=None,
                  pred_vars_to_ignore=None,
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
    if suc_vars_to_ignore is None:
        suc_vars_to_ignore = set()
    if pred_vars_to_ignore is None:
        pred_vars_to_ignore = set()

    carry_vars.add(original_var)
    query = ""

    if ignore_naming is True:
        query += (
            "// create a node corresponding to the clone\n" +
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
            ", ".join(
                ["'{}'".format(n) for n in sucs_to_ignore] +
                ["id({})".format(n) for n in suc_vars_to_ignore])) +
        "[{}] as predIgnore, ".format(
            ", ".join(
                ["'{}'".format(n) for n in preds_to_ignore] +
                ["id({})".format(n) for n in pred_vars_to_ignore])) +
        ", ".join(carry_vars) + " \n"
    )

    carry_vars.add("sucIgnore")
    carry_vars.add("predIgnore")

    for label in edge_labels:
        query += (
            "// match successors and out-edges of a node to be cloned\n" +
            "OPTIONAL MATCH ({})-[out_edge:{}]->(suc) \n".format(
                original_var, label) +
            "WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore\n" +
            "WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, " +
            ", ".join(carry_vars) + " \n"
        )

        carry_vars.add("suc_maps")
        query += (
            "// match predecessors and in-edges of a node to be cloned\n" +
            "OPTIONAL MATCH (pred)-[in_edge:{}]->({}) \n".format(
                label, original_var) +
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
            "\t\tCREATE ({})-[new_edge:{}]->(suc) \n".format(clone_var, label) +
            "\t\tSET new_edge = suc_map.edge))\n"
            "FOREACH (pred_map IN pred_maps | \n"
            "\tFOREACH (pred IN "
            "CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |\n"
            "\t\tCREATE (pred)-[new_edge:{}]->({}) \n".format(label, clone_var) +
            "\t\tSET new_edge = pred_map.edge))\n" +
            "// copy self loop\n" +
            "FOREACH (suc_map IN suc_maps | \n"
            "\tFOREACH (self_loop IN "
            "CASE WHEN suc_map.neighbor = {} THEN [suc_map.edge] ELSE [] END |\n".format(
                original_var) +
            "\t\tCREATE ({})-[new_edge:{}]->({}) \n".format(
                clone_var, label, clone_var) +
            "\t\tSET new_edge = self_loop))\n"
        )
        carry_vars.remove("suc_maps")
        carry_vars.remove("pred_maps")
        query += "WITH " + ", ".join(carry_vars) + "\n"
    carry_vars.remove("sucIgnore")
    carry_vars.remove("predIgnore")

    return query, carry_vars


def merging_query(original_vars, merged_var, merged_id, merged_id_var,
                  node_label, edge_label,
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
        Label of the nodes to merge
    edge_label
        Label of the edges to merge
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
        "OPTIONAL MATCH ({})-[out_rel:{}]->(suc)\n".format(
            merged_var, edge_label) +
        "WITH collect({neighbor: suc, edge: out_rel}) as suc_maps, " +
        ", ".join(carry_vars) + "\n" +
        "OPTIONAL MATCH (pred)-[in_rel:{}]->({})\n".format(
            edge_label, merged_var) +
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
                   node_label, edge_label, merge_typing=False,
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
        Labels of the edges to merge, default is 'edge'
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
        "OPTIONAL MATCH ({})-[out_rel:{}]->(suc)\n".format(
            merged_var, edge_label) +
        "WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, " +
        "pred_maps, " + ", ".join(carry_vars) + "\n" +
        "OPTIONAL MATCH (pred)-[in_rel:{}]->({})\n".format(
            edge_label, merged_var) +
        "WITH pred_maps + collect({id: id(pred), neighbor: pred, edge: in_rel}) as pred_maps, " +
        "suc_maps, " + ", ".join(carry_vars) + "\n"
    )
    for n in original_vars[1:]:
        query += (
            "OPTIONAL MATCH ({})-[out_rel:{}]->(suc)\n".format(
                n, edge_label) +
            "WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, " +
            "pred_maps, " + ", ".join(carry_vars) + "\n" +
            "OPTIONAL MATCH (pred)-[in_rel:{}]->({})\n".format(
                edge_label, n) +
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
        "\tMERGE ({})-[new_rel:{}]->({})\n".format(
            merged_var, edge_label, merged_var) +
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


def find_matching(pattern, node_label, edge_label,
                  nodes=None, pattern_typing=None):
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
    # normalize pattern typing
    pattern_nodes = list(pattern.nodes())

    query =\
        "MATCH {}".format(
            ", ".join(
                "(`{}`:{})".format(n, node_label)
                for n in pattern_nodes))
    if len(pattern.edges()) > 0:
        query += ", {}".format(
            ", ".join("(`{}`)-[:{}]->(`{}`)".format(
                u, edge_label, v)
                for u, v in pattern.edges())) + "\n"
    else:
        query += "\n"

    where_appeared = False
    if len(pattern_nodes) > 1:
        injectivity_clauses = []
        for i, n in enumerate(pattern_nodes):
            if i < len(pattern_nodes) - 1:
                injectivity_clauses.append(
                    "id(`{}`) <> id(`{}`)".format(
                        pattern_nodes[i], pattern_nodes[i + 1]))
        query += "WHERE {}\n".format(
            " AND ".join(c for c in injectivity_clauses))
        where_appeared = True

    if nodes is not None and len(nodes) > 0:
        if where_appeared is False:
            query += "WHERE "
            where_appeared = True
        else:
            query += "AND "
        query +=\
            " AND ".join(
                "`{}`.id IN [{}]".format(
                    pattern_n, ", ".join("'{}'".format(n) for n in nodes))
                for pattern_n in pattern_nodes) + "\n"

    if pattern_typing is not None and len(pattern_typing) > 0:
        if where_appeared is True:
            and_needed = True
        else:
            query += " WHERE "
            where_appeared = True
            and_needed = False
        for typing_graph, mapping in pattern_typing.items():
            if and_needed and len(pattern_typing[typing_graph]) > 0:
                query += " AND "
            query +=\
                " AND ".join(
                    "(`{}`)-[:typing*..]->(:{} {{id: '{}'}})".format(
                        n, typing_graph, pattern_typing[typing_graph][n])
                    for n in pattern.nodes() if n in pattern_typing[typing_graph].keys()
                ) + "\n "

    nodes_with_attrs = []
    for n, attrs in pattern.nodes(data=True):
        if len(attrs) != 0:
            for k in attrs.keys():
                for el in attrs[k]:
                    if type(el) == str:
                        nodes_with_attrs.append((n, k, "'{}'".format(el)))
                    else:
                        nodes_with_attrs.append((n, k, "{}".format(el)))
    if len(nodes_with_attrs) != 0:
        if where_appeared is True:
            query += " AND "
        else:
            query += " WHERE "
            where_appeared = True
        query += (
            " AND ".join(["{} IN `{}`.{}".format(
                v, n, k) for n, k, v in nodes_with_attrs]) + "\n"
        )

    query += "RETURN {}".format(", ".join(["`{}`".format(n) for n in pattern.nodes()]))
    return query


def match_pattern_instance(pattern, pattern_vars, instance,
                           node_label, edge_label, match_edges=True):
    """Query to match an instance of the pattern.

    Parameters
    ----------
    pattern : nx.(Di)Graph
        Graph object representing a pattern
    pattern_vars : ?
    instance : dict
        Instance of the pattern in the graph, dictionary
        whose keys are node ids of the pattern and whose
        values are ids of the nodes of the graph
    node_label :
    edge_label :
    """
    query =\
        generic.match_nodes(instance, node_label=node_label)

    if match_edges and len(pattern.edges()) > 0:
        query +=\
            ", " +\
            ", ".join(
                "({})-[{}:{}]->({})".format(
                    pattern_vars[u],
                    str(pattern_vars[u]) + "_" + str(pattern_vars[v]),
                    edge_label,
                    pattern_vars[v])
                for u, v in pattern.edges())
    else:
        query += "\n"
    return query


def merging_from_list(list_var, merged_var, merged_id, merged_id_var,
                      node_label, edge_label, merge_typing=False,
                      carry_vars=None, ignore_naming=False,
                      multiple_rows=False, multiple_var=None):
    """Generate query for merging the nodes of a neo4j list.

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
        Must be True when the previous matching resulted in more than one
        record (for example when there is more than one group of nodes to
        merge). When True, a map linking the original ids of the nodes to
        the id of the merged one is created so that the edges between the
        merged nodes are always preserved
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
        carry_vars = set([list_var])

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
        carry_vars.update([
            multiple_var, list_var, merged_var,
            merged_id_var, 'ids_to_merged_id'])

    query += "UNWIND {} AS node_to_merge\n".format(list_var)
    carry_vars.remove(list_var)

    if multiple_rows:
        query += (
            "// accumulate all the attrs of the edges incident to the merged nodes\n"
            "WITH node_to_merge, " + ", ".join(carry_vars) + "\n"
            "OPTIONAL MATCH (node_to_merge)-[out_rel:{}]->(suc)\n".format(
                edge_label) +
            "WITH CASE WHEN suc.id IN keys(ids_to_merged_id)\n" +
            "\t\tTHEN {id: id(ids_to_merged_id[suc.id][0]), neighbor: ids_to_merged_id[suc.id][0], edge: out_rel}\n" +
            "\t\tELSE {id: id(suc), neighbor: suc, edge: out_rel} END AS suc_map, " +
            "node_to_merge, " + ", ".join(carry_vars) + "\n" +
            "WITH collect(suc_map) as suc_maps, " +
            "node_to_merge, " + ", ".join(carry_vars) + "\n" +
            "OPTIONAL MATCH (pred)-[in_rel:{}]->(node_to_merge)\n".format(
                edge_label) +
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
            "OPTIONAL MATCH (node_to_merge)-[out_rel:{}]->(suc)\n".format(
                edge_label) +
            "WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, " +
            "pred_maps, node_to_merge, " + ", ".join(carry_vars) + "\n" +
            "OPTIONAL MATCH (pred)-[in_rel:{}]->(node_to_merge)\n".format(
                edge_label) +
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
                           number_of_clone_var,
                           node_label, edge_label, preserv_typing=False,
                           sucs_to_ignore=None, preds_to_ignore=None,
                           carry_vars=None, multiple_rows=False):
    """Generate query for cloning a node X times.

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
    multiple_rows : boolean
        Must be True when the previous matching resulted in more than one
        record (for example when there is more than one node to clone).
        When True, a map linking the original ids of the nodes to the ids
        of its clones is created so that the edges between the clones are
        always preserved

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
    else:
        query += (
            "WITH {{}} as orig_ids_to_clone, {}, {}, ".format(
                clone_id_var, clone_var) +
            ", ".join(carry_vars) + "\n"
        )
        carry_vars.add('orig_ids_to_clone')

    carry_vars.add(clone_id_var)
    carry_vars.add(clone_var)

    query += (
        "WITH [{}] as sucIgnore, ".format(
            ", ".join("'{}'".format(n) for n in sucs_to_ignore)) +
        "[{}] as predIgnore, ".format(
            ", ".join("'{}'".format(n) for n in preds_to_ignore)) +
        ", ".join(carry_vars) + " \n"
    )
    carry_vars.add("predIgnore")
    carry_vars.add("sucIgnore")

    query += (
        "// match successors and out-edges of a node to be cloned\n" +
        "OPTIONAL MATCH ({})-[out_edge:{}]->(suc) \n".format(
            original_var, edge_label) +
        "WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore\n" +
        "WITH collect({neighbor: suc, id: suc.id, edge: out_edge}) as suc_maps, " +
        ", ".join(carry_vars) + " \n"
    )

    carry_vars.add("suc_maps")
    query += (
        "// match predecessors and in-edges of a node to be cloned\n" +
        "OPTIONAL MATCH (pred)-[in_edge:{}]->({}) \n".format(
            edge_label, original_var) +
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
        "\t\tMERGE ({})-[new_edge:{}]->(suc) \n".format(
            clone_var, edge_label) +
        "\t\tSET new_edge = suc_map.edge))\n"
        "FOREACH (pred_map IN pred_maps | \n"
        "\tFOREACH (pred IN CASE\n"
        "\t\t\tWHEN pred_map.neighbor IS NOT NULL AND pred_map.id IN keys(orig_ids_to_clone)\n"
        "\t\t\t\tTHEN orig_ids_to_clone[pred_map.id] \n"
        "\t\t\tWHEN pred_map.neighbor IS NOT NULL\n"
        "\t\t\t\tTHEN [pred_map.neighbor] ELSE [] END |\n"
        "\t\tMERGE (pred)-[new_edge:{}]->({}) \n".format(
            edge_label, clone_var) +
        "\t\tSET new_edge = pred_map.edge))\n" +
        "// copy self loop\n" +
        "FOREACH (suc_map IN suc_maps | \n"
        "\tFOREACH (self_loop IN "
        "CASE WHEN suc_map.neighbor = {} THEN [suc_map.edge] ELSE [] END |\n".format(
            original_var) +
        "\t\tMERGE ({})-[new_edge:{}]->({}) \n".format(
            clone_var, edge_label, clone_var) +
        "\t\tSET new_edge = self_loop))\n"
    )
    carry_vars.remove("suc_maps")
    carry_vars.remove("pred_maps")
    carry_vars.remove("predIgnore")
    carry_vars.remove("sucIgnore")

    if preserv_typing:
        query += (
            generic.with_vars(carry_vars) + "\n" +
            "OPTIONAL MATCH ({})-[out_typ_edge:typing]->(suc_typ)\n".format(
                original_var) +
            "WITH collect({neighbor: suc_typ, edge: out_typ_edge}) as suc_typ_maps, " +
            ", ".join(carry_vars) + " \n"
        )
        carry_vars.add("suc_typ_maps")
        query += (
            "OPTIONAL MATCH (pred_typ)-[in_typ_edge:typing]->({}) \n".format(
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

def rule_to_cypher(rule, instance, node_label="node",
                   edge_label="edge", generate_var_ids=False):
    """Convert a rule on the instance to a Cypher query.

    instance : dict
        Dictionary specifying an instance of the lhs of the rule
    rhs_typing : dict
    node_label : iterable, optional
    edge_label : iterable, optional
    generate_var_ids : boolean
        If True the names of the variables will be generated as uuid
        (unreadable, but more secure: guaranteed to avoid any var name
        collisions)
    """
    # If names of nodes of the rule graphs (L, P, R) are used as
    # var names, we need to perform escaping on these names
    # for neo4j not to complain (some symbols are forbidden in
    # Cypher's var names)

    # fix the order of nodes from P
    # this is to avoid problems with different
    # selection of the cloning origin
    preserved_nodes = rule.p.nodes()
    # Index of preserved nodes helps us to count clones
    preserved_nodes_index = {
        n: i for i, n in enumerate(preserved_nodes)
    }
    if generate_var_ids:
        # Generate unique variable names corresponding to node names
        lhs_vars = {
            n: generic.generate_var_name() for n in rule.lhs.nodes()}
        p_vars = {
            n: generic.generate_var_name() for n in preserved_nodes}
        rhs_vars = {
            n: generic.generate_var_name() for n in rule.rhs.nodes()}
    else:
        # rule._escape()
        lhs_vars = {n: "lhs_" + str(n) for n in rule.lhs.nodes()}
        p_vars = {n: "p_" + str(n) for n in preserved_nodes}
        rhs_vars = {n: "rhs_" + str(n) for n in rule.rhs.nodes()}

    # Variables of the nodes of instance
    match_instance_vars = {lhs_vars[k]: v for k, v in instance.items()}
    query = ""

    # If instance is not empty, generate Cypher that matches the nodes
    # of the instance
    if len(instance) > 0:
        query += "// Match nodes and edges of the instance \n"
        query += match_pattern_instance(
            rule.lhs, lhs_vars, match_instance_vars,
            node_label=node_label, edge_label=edge_label)
        query += "\n\n"
    else:
        query += "// Empty instance \n\n"

    # Add instance nodes to the set of vars to carry
    carry_variables = set(match_instance_vars.keys())
    for u, v in rule.lhs.edges():
        carry_variables.add(str(lhs_vars[u]) + "_" + str(lhs_vars[v]))

    # Here we store nodes of lhs that we keep as one of the clones
    fixed_nodes = dict()
    all_p_clones = set()

    # Generate cloning subquery
    for lhs_node, p_nodes in rule.cloned_nodes().items():
        query += "// Cloning node '{}' of the lhs \n".format(lhs_node)
        clones = set()
        preds_to_ignore = dict()
        sucs_to_ignore = dict()

        # Set a p_node that will correspond to the original
        fixed_node = generic.keys_by_value(
            preserved_nodes_index,
            min([preserved_nodes_index[p_node] for p_node in p_nodes]))[0]
        fixed_nodes[lhs_node] = fixed_node
        clones = [
            p_node for p_node in p_nodes if p_node != fixed_node]
        all_p_clones.update(clones)

        for n in clones:
            preds_to_ignore = set()
            sucs_to_ignore = set()
            suc_vars_to_ignore = set()
            pred_vars_to_ignore = set()
            for u, v in rule.removed_edges():
                if u == n:
                    if v not in clones:
                        if v not in all_p_clones:
                            sucs_to_ignore.add(
                                instance[rule.p_lhs[v]])
                        else:
                            suc_vars_to_ignore.add(p_vars[v])
                if v == n:
                    if u not in clones:
                        if u not in all_p_clones:
                            preds_to_ignore.add(
                                instance[rule.p_lhs[u]])
                        else:
                            pred_vars_to_ignore.add(p_vars[u])
            query +=\
                "// Create clone corresponding to '{}' ".format(n) +\
                "of the preserved part\n"
            if generate_var_ids:
                clone_id_var = generic.generate_var_name()
            else:
                clone_id_var = "p_" + str(n) + "_id"

            q, carry_variables = cloning_query(
                original_var=lhs_vars[lhs_node],
                clone_var=p_vars[n],
                clone_id=n,
                clone_id_var=clone_id_var,
                node_label=node_label,
                edge_labels=["edge", "typing", "related"],
                sucs_to_ignore=sucs_to_ignore,
                preds_to_ignore=preds_to_ignore,
                suc_vars_to_ignore=suc_vars_to_ignore,
                pred_vars_to_ignore=pred_vars_to_ignore,
                carry_vars=carry_variables,
                ignore_naming=True)
            query += q
            query += generic.with_vars(carry_variables)
            query += "\n\n"

    # Generate nodes removal subquery
    for node in rule.removed_nodes():
        query += "// Removing node '{}' of the lhs \n".format(node)
        query += remove_nodes([lhs_vars[node]])
        carry_variables.remove(lhs_vars[node])
        query += "\n"

    # Generate edges removal subquery
    for u, v in rule.removed_edges():
        if rule.p_lhs[u] not in rule.cloned_nodes().keys() and\
           rule.p_lhs[v] not in rule.cloned_nodes().keys():
            # if u in instance.keys() and v in instance.keys():
            query += "// Removing pattern matched edges '{}->{}' of the lhs \n".format(
                rule.p_lhs[u], rule.p_lhs[v])
            edge_var = "{}_{}".format(
                str(lhs_vars[rule.p_lhs[u]]),
                str(lhs_vars[rule.p_lhs[v]]))
            query += remove_edge(edge_var)
            query += "\n"
            carry_variables.remove(edge_var)

    if len(rule.removed_nodes()) > 0 or len(rule.removed_edges()) > 0:
        query += generic.with_vars(carry_variables)

    # Rename untouched vars as they are in P
    vars_to_rename = {}
    for n in rule.lhs.nodes():
        if n not in rule.removed_nodes():
            if n not in rule.cloned_nodes().keys():
                new_var_name = p_vars[generic.keys_by_value(rule.p_lhs, n)[0]]
                vars_to_rename[lhs_vars[n]] = new_var_name
                carry_variables.remove(lhs_vars[n])
            elif n in fixed_nodes.keys():
                vars_to_rename[lhs_vars[n]] = p_vars[fixed_nodes[n]]
                carry_variables.remove(lhs_vars[n])

    if len(vars_to_rename) > 0:
        query += "\n// Renaming vars to correspond to the vars of P\n"
        if len(carry_variables) > 0:
            query +=\
                generic.with_vars(carry_variables) +\
                ", " + ", ".join(
                    "{} as {}".format(k, v)
                    for k, v in vars_to_rename.items()) +\
                " "
        else:
            query +=\
                "WITH " + ", ".join(
                    "{} as {}".format(k, v)
                    for k, v in vars_to_rename.items()) +\
                " "
        query += "\n\n"
    for k, v in vars_to_rename.items():
        carry_variables.add(v)

    # Generate removal of edges between clones
    matches = []
    for u, v in rule.removed_edges():
        if rule.p_lhs[u] in rule.cloned_nodes().keys() or\
           rule.p_lhs[v] in rule.cloned_nodes().keys():
            matches.append((
                "({})-[{}:{}]->({})".format(
                    p_vars[u],
                    p_vars[u] + "_" + p_vars[v],
                    edge_label,
                    p_vars[v]),
                p_vars[u] + "_" + p_vars[v]))

    if len(matches) > 0:
        query += "// Removing edges not bound to vars by matching (edges from/to clones)\n"
        for edge, var in matches:
            query += (
                "// Removing '{}->{}' in P \n".format(u, v) +
                "OPTIONAL MATCH {}\n".format(edge) +
                "DELETE {}\n".format(var) +
                generic.with_vars(carry_variables)
            )

    # !!we forget to add interclone edges!!
    for (p_u, p_v) in rule.p.edges():
        if p_u not in fixed_nodes.keys() and\
           p_v not in fixed_nodes.keys() and\
           (p_u, p_v) not in rule.removed_edges():
            # lhs_u = rule.p_lhs[p_u]
            # lhs_v = rule.p_lhs[p_v]
            query += "MERGE ({})-[{}:{}]->({})\n".format(
                p_vars[p_u], p_vars[p_u] + "_" + p_vars[p_v],
                edge_label, p_vars[p_v])

    # Generate node attrs removal subquery
    for node, attrs in rule.removed_node_attrs().items():
        query += "// Removing properties from node '{}' of P \n".format(node)
        query += remove_attributes(p_vars[node], attrs)
        query += "\n\n"

    # Generate edge attrs removal subquery
    for e, attrs in rule.removed_edge_attrs().items():
        u = e[0]
        v = e[1]
        query += "// Removing properties from edge {}->{} of P \n".format(
            u, v)
        query += generic.with_vars(carry_variables)
        query += "MATCH ({})-[{}:edge]->({})\n".format(
            p_vars[u], p_vars[u] + "_" + p_vars[v], p_vars[v])
        carry_variables.add(p_vars[u] + "_" + p_vars[v])
        query += remove_attributes(p_vars[u] + "_" + p_vars[v], attrs)
        query += "\n\n"

    # Generate merging subquery
    for rhs_key, p_nodes in rule.merged_nodes().items():
        query +=\
            "// Merging nodes '{}' of the preserved part ".format(p_nodes) +\
            "into '{}' \n".format(rhs_key)
        merged_id = "_".join(instance[rule.p_lhs[p_n]]for p_n in p_nodes)
        q, carry_variables = merging_query1(
            original_vars=[p_vars[n] for n in p_nodes],
            merged_var=rhs_vars[rhs_key],
            merged_id=merged_id,
            merged_id_var=generic.generate_var_name(),
            node_label=node_label,
            edge_label=edge_label,
            merge_typing=True,
            carry_vars=carry_variables,
            ignore_naming=True)
        query += q
        query += "\n\n"

    # Generate nodes addition subquery
    for rhs_node in rule.added_nodes():
        query += "// Adding node '{}' from the rhs \n".format(rhs_node)
        if generate_var_ids:
            new_node_id_var = generic.generate_var_name()
        else:
            new_node_id_var = "rhs_" + str(rhs_node) + "_id"
        q, carry_variables = add_node(
            rhs_vars[rhs_node], rhs_node, new_node_id_var,
            node_label=node_label,
            carry_vars=carry_variables,
            ignore_naming=True)
        query += q
        query += "\n\n"

    # Rename untouched vars as they are in rhs
    vars_to_rename = {}
    for n in rule.rhs.nodes():
        if n not in rule.added_nodes() and\
           n not in rule.merged_nodes().keys():
            prev_var_name = p_vars[keys_by_value(rule.p_rhs, n)[0]]
            vars_to_rename[prev_var_name] = rhs_vars[n]
            if prev_var_name in carry_variables:
                carry_variables.remove(prev_var_name)

    if len(vars_to_rename) > 0:
        query += "// Renaming vars to correspond to the vars of rhs\n"
        if len(carry_variables) > 0:
            query +=\
                generic.with_vars(carry_variables) +\
                ", " + ", ".join(
                    "{} as {}".format(k, v)
                    for k, v in vars_to_rename.items()) +\
                " "
        else:
            query +=\
                "WITH " + ", ".join(
                    "{} as {}".format(k, v)
                    for k, v in vars_to_rename.items()) +\
                " "
        query += "\n\n"

    for k, v in vars_to_rename.items():
        carry_variables.add(v)

    # Generate node attrs addition subquery
    for rhs_node, attrs in rule.added_node_attrs().items():
        query += "// Adding properties to the node " +\
            "'{}' from the rhs \n".format(rhs_node)
        query += add_attributes(rhs_vars[rhs_node], attrs)
        query += "\n\n"

    # Generate edges addition subquery
    # query += (
    #     "WITH [] as added_edges, " +
    #     ", ".join(carry_variables) + "\n"
    # )
    for u, v in rule.added_edges():
        query += "// Adding edge '{}->{}' from the rhs \n".format(u, v)
        new_edge_var = rhs_vars[u] + "_" + rhs_vars[v]
        query += add_edge(
            edge_var=new_edge_var,
            source_var=rhs_vars[u],
            target_var=rhs_vars[v],
            edge_label=edge_label,
            attrs=rule.rhs.adj[u][v])
        if (u, v) in rule.added_edge_attrs().keys():
            carry_variables.add(new_edge_var)
        query += "\n\n"

    # Generate edge attrs addition subquery
    for e, attrs in rule.added_edge_attrs().items():
        u = e[0]
        v = e[1]
        query += "// Adding properties to an edge " +\
            "'{}'->'{}' from the rhs \n".format(u, v)
        query += generic.with_vars(carry_variables) + '\n'

        edge_var = rhs_vars[u] + "_" + rhs_vars[v]
        if (u, v) not in rule.added_edges():
            query += "MATCH ({})-[{}:edge]->({})\n".format(
                rhs_vars[u], edge_var, rhs_vars[v])
            carry_variables.add(edge_var)

        query += add_attributes(edge_var, attrs)
        query += generic.with_vars(carry_variables)
        query += "\n\n"

    query += "// Return statement \n"
    query += generic.return_vars(carry_variables)

    # Dictionary defining a mapping from the generated
    # unique variable names to the names of nodes of the rhs
    rhs_vars_inverse = {v: k for k, v in rhs_vars.items()}

    return query, rhs_vars_inverse
