"""Neo4j driver for regraph."""
from neo4j.v1 import GraphDatabase

from regraph.neo4j.cypher_utils import *


class Neo4jGraph(object):
    """Class implementing neo4j graph db driver."""

    def __init__(self, uri, user, password):
        """Initialize driver."""
        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))

    def close(self):
        """Close connection."""
        self._driver.close()

    def execute(self, query):
        """Execute a Cypher query."""
        with self._driver.session() as session:
            result = session.run(query)
            return result

    def clear(self):
        """Clear graph database."""
        query = clear_graph()
        result = self.execute(query)
        return result

    def add_nodes_from(self, nodes):
        """Add nodes to the graph db."""
        query = add_nodes_from(nodes)
        result = self.execute(query)
        print(result)

    def add_edges_from(self, edges, attrs=None):
        """Add edges to the graph db."""
        query = add_edges_from(edges)
        result = self.execute(query)
        print(result)

    def add_node(self, node, attrs=None):
        """Add a node to the graph db."""
        query = add_node(node, attrs)
        result = self.execute(query)
        print(result)

    def add_edge(self, source, target, attrs=None):
        """Add an edge to the graph db."""
        query = add_edge(source, target, attrs)
        result = self.execute(query)
        print(result)

    def remove_node(self, node):
        """Remove a node from the graph db."""
        query = remove_node(node)
        result = self.execute(query)
        print(result)

    def remove_edge(self, source, target):
        """Remove an edge from the graph db."""
        query = remove_edge(source, target)
        result = self.execute(query)
        print(result)

    def nodes(self):
        query = nodes()
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        query = edges()
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]

    def clone_node(self, node, name=None):
        result = self.execute(clone_node(node, name))
        return result.single().value()

    def merge_nodes(self, node_list, name=None):
        result = self.execute(merge_nodes(node_list, name))
        return result.single().value()

    def find_matching(self, pattern, nodes=None):
        result = self.execute(find_matching(pattern, nodes))
        instances = list()

        for record in result:
            instance = dict()
            for k, v in record.items():
                instance[k] = v.properties["id"]
            instances.append(instance)
        return instances

    def rewrite(self, rule, instance):
        """Generate cypher query that corresponds to a rule."""

        query = match(rule.lhs, instance)
        carry_variables = set(instance.keys())
        for lhs_node, p_nodes in rule.cloned_nodes().items():
            # generate query for clonning
            clones = set()
            preds_to_ignore = dict()
            sucs_to_ignore = dict()
            for p_node in p_nodes:
                if p_node != lhs_node:
                    clones.add(p_node)
                    preds_to_ignore[p_node] = set()
                    sucs_to_ignore[p_node] = set()
                    for u, v in rule.removed_edges():
                        if u == p_node:
                            sucs_to_ignore[p_node].add(instance[v])
                        if v == p_node:
                            preds_to_ignore[p_node].add(instance[u])

            clone_ids = set()
            for n in clones:
                q, carry_variables = clonning_query(
                    lhs_node, n, n, n + "_clone_id",
                    sucs_to_ignore[n], preds_to_ignore[n],
                    carry_variables)
                clone_ids.add(lhs_node + "_clone_id")
                query += q
                query += with_vars(carry_variables)

        for node in rule.removed_nodes():
            query += delete_nodes_var(node)
            carry_variables.remove(node)

        for u, v in rule.removed_edges():
            if u in instance.values() and v in instance.values():
                query += delete_edge_var(str(u) + "_" + str(v))

        if len(rule.removed_nodes()) > 0 or len(rule.removed_edges()) > 0:
            query += with_vars(carry_variables)

        for rhs_key, p_nodes in rule.merged_nodes().items():
            merged_id = "_".join(instance[rule.p_lhs[p_n]]for p_n in p_nodes)
            q, carry_variables = merging_query(
                p_nodes, rhs_key, str(rhs_key) + "_id",
                merged_id=merged_id,
                carry_vars=carry_variables)
            query += q

        if len(rule.merged_nodes()) > 0:
            query += with_vars(carry_variables)

        for rhs_node in rule.added_nodes():
            q, carry_variables = create_node(
                rhs_node, rhs_node, rhs_node + "_id", carry_vars=carry_variables)
            query += q

        for u, v in rule.added_edges():
            query += create_edge(u, v)

        query += return_vars(carry_variables)

        result = self.execute(query)
        print(query)
        rhs_g = dict()
        for record in result:
            for k, v in record.items():
                try:
                    rhs_g[k] = v.properties["id"]
                except:
                    pass
        return rhs_g
