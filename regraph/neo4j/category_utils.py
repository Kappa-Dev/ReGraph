"""Category operations used by neo4j graph rewriting tool."""

import regraph.neo4j.cypher_utils as cypher


def pullback(b, c, d, a=None):
    """Find the pullback from b -> d <- c."""
    if a is None:
        a = "pb_" + "_".join([b, c, d])
    query = ""

    # Match all the pair of nodes with the same image in d
    query += "OPTIONAL MATCH (n:{})-[:typing]->(:{})<-[:typing]-(m:{})\n".format(
            b, d, c)

    # For each pair, collect all the properties
    query += new_props_merge(["n", "m"], 'new_props')

    # With blablabla... 
    query += "CREATE (x:{})".format(a) # a tester : provisoire
    query += "SET x += new_props"

    return query


def new_props_merge(node_var_list, new_props_var, carry_vars=None):
    if carry_vars is None:
        carry_vars = set(node_var_list)
    query = ""
    for node in node_var_list:
        query +=\
            "WITH {} + REDUCE(pairs = [], k in keys({}) | \n".format(
                new_props_var, node) +\
            "\tpairs + REDUCE(inner_pairs = [], v in {}[k] | \n".format(
                node) +\
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

    return query

print(pullback('graphB', 'graphC', 'graphD'))




"""
OPTIONAL MATCH (n:graphB)-[:typing]->(:graphD)<-[:typing]-(m:graphC)
WITH [] as new_props, n, m
WITH new_props + REDUCE(pairs = [], k in keys(n) | 
      pairs + REDUCE(inner_pairs = [], v in n[k] | 
         inner_pairs + {key: k, value: v})) as new_props, n, m
WITH new_props + REDUCE(pairs = [], k in keys(m) | 
    pairs + REDUCE(inner_pairs = [], v in m[k] | 
         inner_pairs + {key: k, value: v})) as new_props,n,m
WITH apoc.map.groupByMulti(new_props, 'key') as new_props, n, m
WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys(new_props) | 
    pairs + [k, REDUCE(values=[], v in new_props[k] | 
        values + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as new_props
return new_props
"""