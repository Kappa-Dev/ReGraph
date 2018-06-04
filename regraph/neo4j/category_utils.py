"""Category operations used by neo4j graph rewriting tool."""

import regraph.neo4j.cypher_utils as cypher


def pullback(b, c, d, a=None, inplace=False):
    """Find the pullback from b -> d <- c."""
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
                        label=a,
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
    """Find the pushout of the span b <- a -> c."""
    if d is None:
        d = "pb_" + "_".join([a, b, c])
    carry_vars = set()

    query1 =\
        "OPTIONAL MATCH (n:{})\n".format(b) +\
        "WHERE n IS NOT NULL\n" +\
        "MERGE (n)-[:typing]->(m:{})\n".format(d) +\
        "SET m += properties(n)" +\
        "SET m.id = id(m)"

    query2 =\
        "//Add all the edges\n" +\
        "OPTIONAL MATCH (x:{})<-[:typing]-(:{})-[r:edge]->(:{})-[:typing]->(y:{})\n".format(
            d, b, b, d) +\
        "WITH x, y, r WHERE r IS NOT NULL\n" +\
        "MERGE (x)-[new_r:edge]->(y)\n" +\
        "SET new_r += properties(r)"
    query22 =\
        "//We search for self loops\n" +\
        "OPTIONAL MATCH (z:{})<-[:typing]-(y:{})-[r:edge]->(y)\n".format(
            d, b, b) +\
        "WITH z, r WHERE r IS NOT NULL\n" +\
        "MERGE (x)-[new_r:edge]->(x)\n" +\
        "SET new_r += properties(r)"

    query3 =\
        "OPTIONAL MATCH (n:{})\n".format(c) +\
        "WHERE n IS NOT NULL\n" +\
        "MERGE (n)-[:typing]->(m:{})\n".format(d) +\
        "SET m += properties(n)"

    query4 =\
        "OPTIONAL MATCH (x:{})<-[:typing]-(:{})-[r:edge]->(:{})-[:typing]->(y:{})\n".format(
            d, c, c, d) +\
        "WITH x, y, r WHERE r IS NOT NULL\n" +\
        "MERGE (x)-[new_r:edge]->(y)\n" +\
        "SET new_r += properties(r)"
    query44 =\
        "//We search for self loops\n" +\
        "OPTIONAL MATCH (z:{})<-[:typing]-(y:{})-[r:edge]->(y)\n".format(
            d, c, c) +\
        "WITH z, r WHERE r IS NOT NULL\n" +\
        "MERGE (z)-[new_r:edge]->(z)\n" +\
        "SET new_r += properties(r)"

    query5 =\
        "OPTIONAL MATCH (n:{})<-[:typing]-(:{})<-[:typing]-(:{})-[:typing]->(m:{})\n".format(
            d, b, a, c)

    query55 =\
        "OPTIONAL MATCH (n:{})<-[:typing]-(:{})<-[:typing]-(:{})-[:typing]->(:{})-[:typing]->(m:{})\n".format(
            d, b, a, c, d) +\
        cypher.merging_query(original_vars=["n", "m"],
                             merged_var="merged_node",
                             merged_id="id",
                             merged_id_var="new_id",
                             node_label=d,
                             edge_label=None,
                             ignore_naming=True)[0] + "\n" +\
        cypher.return_vars(['new_id'])

    return query1, query2, query22, query3, query4, query44, query5, query55


def pullback_complement(a, b, d, c=None, inplace=False):
    pass


def check_homomorphism(domain, codomain, total=True):
    pass

"""
res = pushout('graphA', 'graphB', 'graphC', 'graphD')
print(res[0])
print('//---------------')
print(res[1])
print('//---------------')
print(res[2])
print('//---------------')
print(res[3])
print('//---------------')
print(res[4])
print('//---------------')
print(res[5])
print('//---------------')
print(res[6])
print('//---------------')
print(res[7])
print('//---------------')
"""