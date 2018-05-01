"""Neo4j driver for regraph."""
import uuid

from neo4j.v1 import GraphDatabase

from regraph.default.utils import keys_by_value, normalize_attrs
from regraph.neo4j.cypher_utils import *


def generate_var_name():
    """Generate unique variable names."""
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

    def add_node(self, node, attrs=None, ignore_naming=False):
        """Add a node to the graph db."""
        if attrs is None:
            attrs = dict()
        normalize_attrs(attrs)
        query =\
            create_node(
                node, node, 'new_id', attrs,
                literal_id=True, ignore_naming=ignore_naming)[0] +\
            return_vars(['new_id'])

        result = self.execute(query)
        # print(result)

    def add_edge(self, source, target, attrs=None):
        """Add an edge to the graph db."""
        if attrs is None:
            attrs = dict()
        normalize_attrs(attrs)
        query = match_nodes({
            source: source,
            target: target
        })
        query += create_edge(source, target, attrs)
        result = self.execute(query)
        # print(result)

    def add_nodes_from(self, nodes):
        """Add nodes to the graph db."""
        query = ""
        carry_variables = set()
        for n in nodes:
            try:
                n_id, attrs = n
                normalize_attrs(attrs)
                q, carry_variables =\
                    create_node(
                        n_id, n_id, 'new_id_' + n_id, attrs)
            except:
                q, carry_variables =\
                    create_node(
                        n, n, 'new_id_' + n)
            query += q + with_vars(carry_variables)
        query += return_vars(carry_variables)
        result = self.execute(query)
        # print(result)

    def add_edges_from(self, edges):
        """Add edges to the graph db."""
        nodes_to_match = set()
        edge_creation_queries = []
        for e in edges:
            try:
                u, v, attrs = e
                nodes_to_match.add(u)
                nodes_to_match.add(v)
                normalize_attrs(attrs)
                edge_creation_queries.append(create_edge(u, v, attrs))
            except:
                u, v = e
                nodes_to_match.add(u)
                nodes_to_match.add(v)
                edge_creation_queries.append(create_edge(u, v))
        query = match_nodes(
            {n: n for n in nodes_to_match})
        for q in edge_creation_queries:
            query += q
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

    def get_node(self, node_id):
        """Return node's attributes."""
        query = get_node(node_id)
        result = self.execute(query)
        return dict(result.value()[0])

    def get_edge(self, s, t):
        """Return edge attributes."""
        query = get_edge(s, t)
        result = self.execute(query)
        return dict(result.value()[0])

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
        print(query)
        result = self.execute(query)
        return result.single().value()

    def merge_nodes(self, node_list, name=None, ignore_naming=False):
        """Merge nodes of the graph."""
        if name is not None:
            pass
        else:
            name = "_".join(node_list)
        query =\
            match_nodes({n: n for n in node_list}) + "\n" +\
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

    def merge_nodes1(self, node_list, name=None, ignore_naming=False):
        """Merge nodes of the graph."""
        if name is not None:
            pass
        else:
            name = "_".join(node_list)
        query =\
            match_nodes({n: n for n in node_list}) + "\n" +\
            merging_query1(
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
                instance[k] = dict(v)["id"]
            instances.append(instance)
        return instances

    def rule_to_cypher(self, rule, instance, generate_var_ids=False):
        """Convert a rule on the instance to a Cypher query.

        rule : regraph.Rule
            Input rule
        instance : dict
            Dictionary specifying an instance of the lhs of the rule
        generate_var_ids : boolean
            If True the names of the variables will be generated as uuid
            (unreadable, but more secure: guaranteed to avoid any var name
            collisions)
        """
        # If names of nodes of the rule graphs (L, P, R) are used as
        # var names, we need to perform escaping on these names
        # for neo4j not to complain (some symbols are forbidden in
        # Cypher's var names)

        if generate_var_ids:
            # Generate unique variable names corresponding to node names
            lhs_vars = {n: generate_var_name() for n in rule.lhs.nodes()}
            p_vars = {n: generate_var_name() for n in rule.p.nodes()}
            rhs_vars = {n: generate_var_name() for n in rule.rhs.nodes()}
        else:
            rule._escape()
            lhs_vars = {n: "lhs_" + str(n) for n in rule.lhs.nodes()}
            p_vars = {n: "p_" + str(n) for n in rule.p.nodes()}
            rhs_vars = {n: "rhs_" + str(n) for n in rule.rhs.nodes()}

        # Variables of the nodes of instance
        match_instance_vars = {lhs_vars[k]: v for k, v in instance.items()}

        query = ""

        # If instance is not empty, generate Cypher that matches the nodes
        # of the instance
        if len(instance) > 0:
            query += "// Match nodes and edges of the instance \n"
            query += match_pattern_instance(
                rule.lhs, lhs_vars, match_instance_vars)
            query += "\n\n"
        else:
            query += "// Empty instance \n\n"

        # Add instance nodes to the set of vars to carry
        carry_variables = set(match_instance_vars.keys())

        # Generate cloning subquery
        for lhs_node, p_nodes in rule.cloned_nodes().items():
            query += "// Cloning node '{}' of the lhs \n".format(lhs_node)
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
                query +=\
                    "// Create clone corresponding to '{}' ".format(n) +\
                    "of the preserved part\n"
                if generate_var_ids:
                    clone_id_var = generate_var_name()
                else:
                    clone_id_var = "p_" + str(n) + "_id"

                q, carry_variables = cloning_query(
                    original_var=lhs_vars[lhs_node],
                    clone_var=p_vars[n],
                    clone_id=n,
                    clone_id_var=clone_id_var,
                    sucs_to_ignore=sucs_to_ignore[n],
                    preds_to_ignore=preds_to_ignore[n],
                    carry_vars=carry_variables,
                    ignore_naming=True)
                query += q
                query += with_vars(carry_variables)
                query += "\n\n"

        # Generate nodes removal subquery
        for node in rule.removed_nodes():
            query += "// Removing node '{}' of the lhs \n".format(node)
            query += delete_nodes_var([lhs_vars[node]])
            carry_variables.remove(lhs_vars[node])
            query += "\n"

        # Generate edges removal subquery
        for u, v in rule.removed_edges():
            if u in instance.keys() and v in instance.keys():
                query += "// Removing edge '{}->{}' of the lhs \n".format(u, v)
                query += delete_edge_var(
                    str(lhs_vars[u]) + "_" + str(lhs_vars[v]))
                query += "\n"

        if len(rule.removed_nodes()) > 0 or len(rule.removed_edges()) > 0:
            query += with_vars(carry_variables)

        # Rename untouched vars as they are in P
        vars_to_rename = {}
        for n in rule.lhs.nodes():
            if n not in rule.removed_nodes():
                new_var_name = p_vars[keys_by_value(rule.p_lhs, n)[0]]
                vars_to_rename[lhs_vars[n]] = new_var_name
                carry_variables.remove(lhs_vars[n])
        if len(vars_to_rename) > 0:
            query += "// Renaming vars to correspond to the vars of rhs\n"
            if len(carry_variables) > 0:
                query +=\
                    with_vars(carry_variables) +\
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

        # Generate merging subquery
        for rhs_key, p_nodes in rule.merged_nodes().items():
            query +=\
                "// Merging nodes '{}' of the preserved part ".format(p_nodes) +\
                "into '{}' \n".format(rhs_key)
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
            query += "\n\n"

        # Generate nodes addition subquery
        for rhs_node in rule.added_nodes():
            query += "// Adding node '{}' from the rhs \n".format(rhs_node)
            if generate_var_ids:
                new_node_id_var = generate_var_name()
            else:
                new_node_id_var = "rhs_" + str(rhs_node) + "_id"
            q, carry_variables = create_node(
                rhs_vars[rhs_node], rhs_node, new_node_id_var,
                carry_vars=carry_variables,
                ignore_naming=True)
            query += q
            query += with_vars(carry_variables)
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
                    with_vars(carry_variables) +\
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

        # Generate edges addition subquery
        for u, v in rule.added_edges():
            query += "// Adding edge '{}->{}' from the rhs \n".format(u, v)
            query += create_edge(rhs_vars[u], rhs_vars[v])
            query += "\n"

        query += "// Return statement \n"
        query += return_vars(carry_variables)

        # Dictionary defining a mapping from the generated
        # unique variable names to the names of nodes of the rhs
        rhs_vars_inverse = {v: k for k, v in rhs_vars.items()}

        return query, rhs_vars_inverse

    def rewrite(self, rule, instance):
        """Perform SqPO rewiting of the graph with a rule."""
        # Generate corresponding Cypher query
        query, rhs_vars_inverse = self.rule_to_cypher(rule, instance)
        print("Rewriting rule to Cypher: \n")
        print(query)
        # Execute query
        result = self.execute(query)
        # Retrieve a dictionary mapping the nodes of the rhs to the nodes
        # of the resulting graph
        rhs_g = dict()
        for record in result:
            for k, v in record.items():
                try:
                    rhs_g[k] = v.properties["id"]
                except:
                    pass
        rhs_g = {rhs_vars_inverse[k]: v for k, v in rhs_g.items()}
        return rhs_g

    # def rule_to_cypher1(self, rule, instance):
    #     # here we will bind the edges of the nodes to clone/merge to some vars
    #     rule._escape()

    #     query = ""

    #     lhs_vars = {n: generate_var_name() for n in rule.lhs.nodes()}
    #     p_vars = {n: generate_var_name() for n in rule.p.nodes()}
    #     rhs_vars = {n: generate_var_name() for n in rule.rhs.nodes()}

    #     edge_side_effect_neighbours = set()
    #     for lhs_node, p_nodes in rule.cloned_nodes().items():
    #         edge_side_effect_neighbours.add(instance[lhs_node])
    #     for rhs_key, p_nodes in rule.merged_nodes().items():
    #         for p_node in p_nodes:
    #             edge_side_effect_neighbours.add(rule.p_lhs[p_node])

    #     match_instance_vars = {lhs_vars[k]: v for k, v in instance.items()}

    #     side_effect_edge_vars = {e for e in rule.lhs.edges()}

    #     # if len(instance) > 0:
    #     #     query += match_pattern_instance(
    #     #         rule.lhs, lhs_vars, match_instance_vars)

    #     # carry_variables = set(match_instance_vars.keys())
