"""Neo4j driver for regraph."""
import uuid
import networkx as nx

from neo4j.v1 import GraphDatabase

from regraph.default.utils import keys_by_value
from regraph.neo4j.cypher_utils import *


def generate_var_name():
    uid = "uid" + str(uuid.uuid4()).replace("-", "")
    return uid


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

    def add_node(self, node, attrs=None):
        """Add a node to the graph db."""
        query =\
            create_node(
                node, node, 'new_id',
                literal_id=True)[0] +\
            return_vars(['new_id'])

        result = self.execute(query)
        # print(result)

    def add_edge(self, source, target, attrs=None):
        """Add an edge to the graph db."""
        query = match_nodes({
            source: source,
            target: target
        })
        query += create_edge(source, target)
        result = self.execute(query)
        # print(result)

    def add_nodes_from(self, nodes):
        """Add nodes to the graph db."""
        query = ""
        carry_variables = set()
        for n in nodes:
            q, carry_variables =\
                create_node(
                    n, n, 'new_id_' + n)
            query += q + with_vars(carry_variables)
        query += return_vars(carry_variables)
        result = self.execute(query)
        # print(result)

    def add_edges_from(self, edges):
        """Add edges to the graph db."""
        query = match_nodes(
            {n: n for n in set(sum(edges, ()))})
        for u, v in edges:
            query += create_edge(u, v)
        result = self.execute(query)
        # print(result)

    def remove_node(self, node):
        """Remove a node from the graph db."""
        query =\
            match_node(node, node) +\
            delete_nodes_var([node])
        result = self.execute(query)
        # print(result)

    def remove_edge(self, source, target):
        """Remove an edge from the graph db."""
        query =\
            match_edge(source, target, source, target, 'edge_var') +\
            delete_edge_var('edge_var')
        result = self.execute(query)
        # print(result)

    def nodes(self):
        """Return a list of nodes of the graph."""
        query = get_nodes()
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        """Return the list of edges of the graph."""
        query = get_edges()
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]

    def clone_node(self, node, name=None, ignore_naming=False):
        """Clone a node of the graph."""
        if name is None:
            name = node
        query =\
            match_node('x', node) +\
            cloning_query(
                original_var='x',
                clone_var='new_node',
                clone_id=name,
                clone_id_var='uid',
                ignore_naming=ignore_naming)[0] +\
            return_vars(['uid'])
        result = self.execute(query)
        return result.single().value()

    def merge_nodes(self, node_list, name=None, ignore_naming=False):
        """Merge nodes of the graph."""
        if name is not None:
            pass
        else:
            name = "_".join(node_list)
        query =\
            match_nodes({n: n for n in node_list}) +\
            merging_query(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                ignore_naming=ignore_naming)[0] +\
            return_vars(['new_id'])
        print(query)
        result = self.execute(query)
        return result.single().value()

    def find_matching(self, pattern, nodes=None):
        """Find matchings of a pattern in the graph."""
        result = self.execute(find_matching(pattern, nodes))
        instances = list()

        for record in result:
            instance = dict()
            for k, v in record.items():
                instance[k] = v.properties["id"]
            instances.append(instance)
        return instances

    def rewrite(self, rule, instance):
        """Perform SqPO rewiting of the graph with a rule."""

        rule._escape()

        query = ""

        lhs_vars = {n: generate_var_name() for n in rule.lhs.nodes()}
        p_vars = {n: generate_var_name() for n in rule.p.nodes()}
        rhs_vars = {n: generate_var_name() for n in rule.rhs.nodes()}

        match_instance_vars = {lhs_vars[k]: v for k, v in instance.items()}

        if len(instance) > 0:
            query += match_pattern_instance(
                rule.lhs, lhs_vars, match_instance_vars)

        carry_variables = set(match_instance_vars.keys())

        # Generate clone subquery
        for lhs_node, p_nodes in rule.cloned_nodes().items():

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

            for n in clones:
                q, carry_variables = cloning_query(
                    original_var=lhs_vars[lhs_node],
                    clone_var=p_vars[n],
                    clone_id=n,
                    clone_id_var=generate_var_name(),
                    neighbours_to_ignore=sucs_to_ignore[n].union(preds_to_ignore[n]),
                    carry_vars=carry_variables,
                    ignore_naming=True)
                query += q
                query += with_vars(carry_variables)

        for node in rule.removed_nodes():
            query += delete_nodes_var([lhs_vars[node]])
            carry_variables.remove(lhs_vars[node])

        for u, v in rule.removed_edges():
            if u in instance.keys() and v in instance.keys():
                query += delete_edge_var(
                    str(lhs_vars[u]) + "_" + str(lhs_vars[v]))

        if len(rule.removed_nodes()) > 0 or len(rule.removed_edges()) > 0:
            query += with_vars(carry_variables)

        # rename untouched vars as they are in p
        vars_to_rename = {}
        for n in rule.lhs.nodes():
            if n not in rule.removed_nodes():
                new_var_name = p_vars[keys_by_value(rule.p_lhs, n)[0]]
                vars_to_rename[lhs_vars[n]] = new_var_name
                carry_variables.remove(lhs_vars[n])
        if len(vars_to_rename) > 0:
            if len(carry_variables) > 0:
                query +=\
                    with_vars(carry_variables) +\
                    ", " + ", ".join("{} as {}".format(k, v) for k, v in vars_to_rename.items()) +\
                    " "
            else:
                query +=\
                    "WITH " + ", ".join("{} as {}".format(k, v) for k, v in vars_to_rename.items()) +\
                    " "

        for k, v in vars_to_rename.items():
            carry_variables.add(v)

        for rhs_key, p_nodes in rule.merged_nodes().items():
            merged_id = "_".join(instance[rule.p_lhs[p_n]]for p_n in p_nodes)
            q, carry_variables = merging_query(
                original_vars=[p_vars[n] for n in p_nodes],
                merged_var=rhs_vars[rhs_key],
                merged_id=merged_id,
                merged_id_var=generate_var_name(),
                carry_vars=carry_variables,
                ignore_naming=True)
            query += q
            query += with_vars(carry_variables)

        for rhs_node in rule.added_nodes():
            q, carry_variables = create_node(
                rhs_vars[rhs_node], rhs_node, generate_var_name(), carry_vars=carry_variables,
                ignore_naming=True)
            query += q
            query += with_vars(carry_variables)

        # rename untouched vars as they are in rhs
        vars_to_rename = {}
        for n in rule.rhs.nodes():
            if n not in rule.added_nodes() and\
               n not in rule.merged_nodes().keys():
                prev_var_name = p_vars[keys_by_value(rule.p_rhs, n)[0]]
                vars_to_rename[prev_var_name] = rhs_vars[n]
                carry_variables.remove(prev_var_name)

        if len(vars_to_rename) > 0:
            if len(carry_variables) > 0:
                query +=\
                    with_vars(carry_variables) +\
                    ", " + ", ".join("{} as {}".format(k, v) for k, v in vars_to_rename.items()) +\
                    " "
            else:
                query +=\
                    "WITH " + ", ".join("{} as {}".format(k, v) for k, v in vars_to_rename.items()) +\
                    " "

        for k, v in vars_to_rename.items():
            carry_variables.add(v)

        for u, v in rule.added_edges():
            query += create_edge(rhs_vars[u], rhs_vars[v])

        query += return_vars(carry_variables)

        print(query)
        result = self.execute(query)
        # print(query)
        rhs_g = dict()
        for record in result:
            for k, v in record.items():
                try:
                    rhs_g[k] = v.properties["id"]
                except:
                    pass

        rhs_vars_inverse = {v: k for k, v in rhs_vars.items()}
        rhs_g = {rhs_vars_inverse[k]: v for k, v in rhs_g.items()}
        assert(set(rhs_g.keys()) == set(rule.rhs.nodes()))
        return rhs_g
