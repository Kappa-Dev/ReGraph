"""Neo4j driver for regraph."""
import uuid

from neo4j.v1 import GraphDatabase

from regraph.default.utils import keys_by_value, normalize_attrs
import regraph.neo4j.cypher_utils as cu


def generate_var_name():
    """Generate unique variable names."""
    uid = "uid" + str(uuid.uuid4()).replace("-", "")
    return uid


class Neo4jGraph(object):
    """Class implementing Neo4j graph instance.

    This class encapsulates neo4j.v1.GraphDatabase object
    Attributes
    ----------
    _db :
    _label :
    _node_label :
    """

    def __init__(self, driver=None, uri=None,
                 user=None, password=None,
                 node_labels=None,
                 edge_labels=None,
                 unique_node_ids=True):
        """Initialize Neo4jGraph object.

        Parameters
        ----------
        label : str ?
        driver : neo4j.v1.direct.DirectDriver, optional
        uri : str, optional
            Uri for Neo4j database connection
        user : str, optional
            Username for Neo4j database connection
        password : str, optional
            Password for Neo4j database connection
        node_labels : itarable, optional
        edge_labels : iterable, optional
        unique_node_ids : bool, optional
            Flag, if True the uniqueness constraint on the property
            'id' of nodes is imposed, by default True

        If database driver is provided, uses it for
        connecting to database, otherwise creates
        a new driver object using provided credentials.
        """
        if driver is None:
            self._driver = GraphDatabase.driver(
                uri, auth=(user, password))
        else:
            self._driver = driver

        if node_labels is not None:
            self._node_labels = node_labels
        else:
            self._node_labels = ["node"]

        if edge_labels is not None:
            self._edge_labels = edge_labels
        else:
            self._edge_labels = ["edge"]

        if unique_node_ids:
            self.set_constraint('id')

    def execute(self, query):
        """Execute a Cypher query."""
        with self._driver.session() as session:
            result = session.run(query)
            return result

    def clear(self):
        """Clear graph database.

        Returns
        -------
        result : BoltStatementResult
        """
        query = cu.clear_graph(self._node_labels)
        result = self.execute(query)
        return result

    def set_constraint(self, prop):
        """Set a uniqueness constraint on the property.

        Parameters
        ----------
        prop : str
            Name of the property that is required to be unique
            for the nodes of the database


        Returns
        -------
        result : BoltStatementResult
        """
        query = "CREATE " + cu.constraint_query(
            'n', self._node_labels, prop)
        result = self.execute(query)
        return result

    def drop_constraint(self, prop):
        """Drop a uniqueness constraint on the property.

        Parameters
        ----------
        prop : str
            Name of the property

        Returns
        -------
        result : BoltStatementResult
        """
        query = "DROP " + cu.constraint_query('n', self._node_labels, prop)
        result = self.execute(query)
        return result

    def add_node(self, node, attrs=None, ignore_naming=False, profiling=False):
        """Add a node to the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        if attrs is None:
            attrs = dict()
        normalize_attrs(attrs)
        query +=\
            cu.create_node(
                node, node, 'new_id',
                node_labels=self._node_labels,
                attrs=attrs,
                literal_id=True,
                ignore_naming=ignore_naming)[0] +\
            cu.return_vars(['new_id'])

        result = self.execute(query)
        return result

    def add_edge(self, source, target, attrs=None, profiling=False):
        """Add an edge to the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        if attrs is None:
            attrs = dict()
        normalize_attrs(attrs)
        query += cu.match_nodes(
            {source: source, target: target},
            node_labels=self._node_labels)
        query += cu.create_edge(
            edge_var='new_edge',
            source_var=source,
            target_var=target,
            edge_labels=self._edge_labels,
            attrs=attrs)
        result = self.execute(query)
        return result

    def add_nodes_from(self, nodes, profiling=False):
        """Add nodes to the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        carry_variables = set()
        for n in nodes:
            try:
                n_id, attrs = n
                normalize_attrs(attrs)
                q, carry_variables =\
                    cu.create_node(
                        n_id, n_id, 'new_id_' + n_id,
                        node_labels=self._node_labels,
                        attrs=attrs)
            except ValueError:
                q, carry_variables =\
                    cu.create_node(
                        n, n, 'new_id_' + n,
                        node_labels=self._node_labels)
            query += q + cu.with_vars(carry_variables)
        query += cu.return_vars(carry_variables)
        result = self.execute(query)
        return result

    def add_edges_from(self, edges, profiling=False):
        """Add edges to the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        nodes_to_match = set()
        edge_creation_queries = []
        for e in edges:
            try:
                u, v, attrs = e
                nodes_to_match.add(u)
                nodes_to_match.add(v)
                normalize_attrs(attrs)
                edge_creation_queries.append(
                    cu.create_edge(
                        edge_var=u + "_" + v,
                        source_var=u,
                        target_var=v,
                        edge_labels=self._edge_labels,
                        attrs=attrs))
            except ValueError:
                u, v = e
                nodes_to_match.add(u)
                nodes_to_match.add(v)
                edge_creation_queries.append(
                    cu.create_edge(
                        edge_var=u + "_" + v,
                        source_var=u,
                        target_var=v,
                        edge_labels=self._edge_labels))
        query += cu.match_nodes(
            {n: n for n in nodes_to_match},
            node_labels=self._node_labels)
        for q in edge_creation_queries:
            query += q
        result = self.execute(query)
        return result

    def remove_node(self, node, profiling=False):
        """Remove a node from the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        query +=\
            cu.match_node(
                node, node,
                node_labels=self._node_labels) +\
            cu.delete_nodes_var([node])
        result = self.execute(query)
        return result

    def remove_edge(self, source, target, profiling=False):
        """Remove an edge from the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        query +=\
            cu.match_edge(source, target, source, target, 'edge_var',
                          edge_label='edge') +\
            cu.delete_edge_var('edge_var')
        result = self.execute(query)
        return result

    def nodes(self):
        """Return a list of nodes of the graph."""
        query = cu.get_nodes(node_labels=self._node_labels)
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        """Return the list of edges of the graph."""
        query = cu.get_edges(self._node_labels,
                             self._node_labels,
                             self._edge_labels)
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]

    def get_node(self, node_id):
        """Return node's attributes."""
        query = cu.get_node(node_id, node_labels=self._node_labels)
        result = self.execute(query)
        try:
            return dict(result.value()[0])
        except(IndexError):
            return None

    def get_edge(self, s, t):
        """Return edge attributes."""
        query = cu.get_edge(s, t,
                            source_labels=self._node_labels,
                            target_labels=self._node_labels,
                            edge_labels=self._edge_labels)
        result = self.execute(query)
        try:
            return dict(result.value()[0])
        except(IndexError):
            return None

    def successors(self, node):
        """Return node's successors id."""
        query = cu.successors_query(node, node,
                                    node_labels=self._node_labels)
        succ = set(self.execute(query).value())
        return(succ)

    def predecessors(self, node):
        """Return node's predecessors id."""
        query = cu.predecessors_query(node, node,
                                      node_labels=self._node_labels)
        pred = set(self.execute(query).value())
        return(pred)

    def clone_node(self, node, name=None, preserv_typing=False,
                   ignore_naming=False, profiling=False):
        """Clone a node of the graph."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        if name is None:
            name = node
        query +=\
            cu.match_node(
                'x', node,
                node_labels=self._node_labels) +\
            cu.cloning_query(
                original_var='x',
                clone_var='new_node',
                clone_id=name,
                clone_id_var='uid',
                node_labels=self._node_labels,
                preserv_typing=preserv_typing,
                ignore_naming=ignore_naming)[0] +\
            cu.return_vars(['uid'])
        result = self.execute(query)
        uid_records = []
        for record in result:
            uid_records.append(record['uid'])
        if len(uid_records) > 0:
            return uid_records[0]

    def merge_nodes(self, node_list, name=None,
                    ignore_naming=False, profiling=False):
        """Merge nodes of the graph."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        if name is not None:
            pass
        else:
            name = "_".join(node_list)
        query +=\
            cu.match_nodes({n: n for n in node_list},
                           node_labels=self._node_labels) + "\n" +\
            cu.merging_query(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_labels=self._node_labels,
                edge_labels=self._edge_labels,
                ignore_naming=ignore_naming)[0] +\
            cu.return_vars(['new_id'])
        result = self.execute(query)
        uid_records = []
        for record in result:
            uid_records.append(record['new_id'])
        if len(uid_records) > 0:
            return uid_records[0]

    def merge_nodes1(self, node_list, name=None, merge_typing=False,
                     ignore_naming=False, profiling=False):
        """Merge nodes of the graph."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        if name is not None:
            pass
        else:
            name = "_".join(node_list)
        query +=\
            cu.match_nodes({n: n for n in node_list},
                           node_labels=self._node_labels) + "\n" +\
            cu.merging_query1(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_labels=self._node_labels,
                edge_labels=self._edge_labels,
                merge_typing=merge_typing,
                ignore_naming=ignore_naming)[0] +\
            cu.return_vars(['new_id'])
        result = self.execute(query)
        uid_records = []
        for record in result:
            uid_records.append(record['new_id'])
        if len(uid_records) > 0:
            return uid_records[0]

    def find_matching(self, pattern, nodes=None):
        """Find matchings of a pattern in the graph."""
        if len(pattern.nodes()) != 0:
            result = self.execute(
                cu.find_matching(
                    pattern, nodes,
                    node_labels=self._node_labels,
                    edge_labels=self._edge_labels))
            instances = list()

            for record in result:
                instance = dict()
                for k, v in record.items():
                    instance[k] = dict(v)["id"]
                instances.append(instance)
        else:
            instances = []
        return instances

    def rule_to_cypher(self, rule, instance, rhs_typing=None,
                       generate_var_ids=False):
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
        if rhs_typing is None:
            rhs_typing = dict()

        if generate_var_ids:
            # Generate unique variable names corresponding to node names
            lhs_vars = {n: generate_var_name() for n in rule.lhs.nodes()}
            p_vars = {n: generate_var_name() for n in rule.p.nodes()}
            rhs_vars = {n: generate_var_name() for n in rule.rhs.nodes()}
        else:
            # rule._escape()
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
            query += cu.match_pattern_instance(
                rule.lhs, lhs_vars, match_instance_vars,
                node_labels=self._node_labels, edge_labels=self._edge_labels)
            query += "\n\n"
        else:
            query += "// Empty instance \n\n"

        # Add instance nodes to the set of vars to carry
        carry_variables = set(match_instance_vars.keys())
        for u, v in rule.lhs.edges():
            carry_variables.add(str(lhs_vars[u]) + "_" + str(lhs_vars[v]))

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
                            try:
                                sucs_to_ignore[p_node].add(instance[v])
                            except(KeyError):
                                sucs_to_ignore[p_node].add(v)
                        if v == p_node:
                            try:
                                preds_to_ignore[p_node].add(instance[u])
                            except(KeyError):
                                preds_to_ignore[p_node].add(u)
            for n in clones:
                query +=\
                    "// Create clone corresponding to '{}' ".format(n) +\
                    "of the preserved part\n"
                if generate_var_ids:
                    clone_id_var = generate_var_name()
                else:
                    clone_id_var = "p_" + str(n) + "_id"

                q, carry_variables = cu.cloning_query(
                    original_var=lhs_vars[lhs_node],
                    clone_var=p_vars[n],
                    clone_id=n,
                    clone_id_var=clone_id_var,
                    node_labels=self._node_labels,
                    preserv_typing=True,
                    sucs_to_ignore=sucs_to_ignore[n],
                    preds_to_ignore=preds_to_ignore[n],
                    carry_vars=carry_variables,
                    ignore_naming=True)
                query += q
                query += cu.with_vars(carry_variables)
                query += "\n\n"

        # Generate nodes removal subquery
        for node in rule.removed_nodes():
            query += "// Removing node '{}' of the lhs \n".format(node)
            query += cu.delete_nodes_var([lhs_vars[node]])
            carry_variables.remove(lhs_vars[node])
            query += "\n"

        # Generate edges removal subquery
        for u, v in rule.removed_edges():
            if u in instance.keys() and v in instance.keys():
                query += "// Removing edge '{}->{}' of the lhs \n".format(u, v)
                query += cu.delete_edge_var(
                    str(lhs_vars[u]) + "_" + str(lhs_vars[v]))
                query += "\n"

        if len(rule.removed_nodes()) > 0 or len(rule.removed_edges()) > 0:
            query += cu.with_vars(carry_variables)

        # Rename untouched vars as they are in P
        vars_to_rename = {}
        for n in rule.lhs.nodes():
            if n not in rule.removed_nodes():
                if len(keys_by_value(rule.p_lhs, n)) > 1:
                    new_var_name = generate_var_name()
                    for key in keys_by_value(rule.p_lhs, n):
                        if p_vars[key] not in carry_variables:
                            new_var_name = p_vars[key]
                else:
                    new_var_name = p_vars[keys_by_value(rule.p_lhs, n)[0]]
                vars_to_rename[lhs_vars[n]] = new_var_name
                carry_variables.remove(lhs_vars[n])
        if len(vars_to_rename) > 0:
            query += "// Renaming vars to correspond to the vars of P\n"
            if len(carry_variables) > 0:
                query +=\
                    cu.with_vars(carry_variables) +\
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

        # Generate node attrs removal subquery
        for node, attrs in rule.removed_node_attrs().items():
            query += "// Removing properties from node '{}' of P \n".format(node)
            query += cu.remove_attributes(p_vars[node], attrs)
            query += "\n\n"

        # Generate edge attrs removal subquery
        for e, attrs in rule.removed_edge_attrs().items():
            u = e[0]
            v = e[1]
            query += "// Removing properties from edge {}->{} of P \n".format(
                u, v)
            query += cu.with_vars(carry_variables)
            query += "MATCH ({})-[{}:edge]->({})\n".format(
                p_vars[u], p_vars[u] + "_" + p_vars[v], p_vars[v])
            carry_variables.add(p_vars[u] + "_" + p_vars[v])
            query += cu.remove_attributes(p_vars[u] + "_" + p_vars[v], attrs)
            query += "\n\n"

        # Generate merging subquery
        for rhs_key, p_nodes in rule.merged_nodes().items():
            query +=\
                "// Merging nodes '{}' of the preserved part ".format(p_nodes) +\
                "into '{}' \n".format(rhs_key)
            merged_id = "_".join(instance[rule.p_lhs[p_n]]for p_n in p_nodes)
            q, carry_variables = cu.merging_query1(
                original_vars=[p_vars[n] for n in p_nodes],
                merged_var=rhs_vars[rhs_key],
                merged_id=merged_id,
                merged_id_var=generate_var_name(),
                node_labels=self._node_labels,
                merge_typing=True,
                carry_vars=carry_variables,
                ignore_naming=True)
            query += q
            query += "\n\n"

        # Generate nodes addition subquery
        for rhs_node in rule.added_nodes():
            query += "// Adding node '{}' from the rhs \n".format(rhs_node)
            if generate_var_ids:
                new_node_id_var = generate_var_name()
            else:
                new_node_id_var = "rhs_" + str(rhs_node) + "_id"
            q, carry_variables = cu.create_node(
                rhs_vars[rhs_node], rhs_node, new_node_id_var,
                node_labels=self._node_labels,
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
                    cu.with_vars(carry_variables) +\
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
            query += cu.add_attributes(rhs_vars[rhs_node], attrs)

        # Generate edges addition subquery
        # query += (
        #     "WITH [] as added_edges, " +
        #     ", ".join(carry_variables) + "\n"
        # )
        for u, v in rule.added_edges():
            query += "// Adding edge '{}->{}' from the rhs \n".format(u, v)
            query += cu.create_edge(
                edge_var=rhs_vars[u] + "_" + rhs_vars[v],
                source_var=rhs_vars[u],
                target_var=rhs_vars[v],
                edge_labels=self._edge_labels)
            # query += (
            #     "WITH added_edges + {{source: {}.id, ".format(rhs_vars[u]) +
            #     "target: {}.id}} as added_edges, ".format(rhs_vars[v]) +
            #     ", ".join(carry_variables) + "\n"
            # )
            query += "\n\n"
        # carry_variables.add('added_edges')

        # Generate edge attrs addition subquery
        for e, attrs in rule.added_edge_attrs().items():
            u = e[0]
            v = e[1]
            query += "// Adding properties to the node " +\
                "'{}' from the rhs \n".format(rhs_node)
            query += cu.with_vars(carry_variables)
            query += "MATCH ({})-[{}:edge]->({})\n".format(
                rhs_vars[u], rhs_vars[u] + "_" + rhs_vars[v], rhs_vars[v])
            carry_variables.add(rhs_vars[u] + "_" + rhs_vars[v])
            query += cu.add_attributes(rhs_vars[u] + "_" + rhs_vars[v], attrs)
            query += cu.with_vars(carry_variables)
            query += "\n\n"

        # Genearate rhs_typing
        for graph in rhs_typing.keys():
            for node in rhs_typing[graph].keys():
                if node in rule.added_nodes():
                    query += (
                        cu.with_vars(carry_variables) +
                        "OPTIONAL MATCH ({}:node:{} {{id:'{}'}})\n".format(
                            node + '_' + graph, graph, rhs_typing[graph][node]) +
                        "MERGE ({})-[:tmp_typing]->({})\n".format(
                            rhs_vars[node], node + '_' + graph)
                    )

        query += "// Return statement \n"
        query += cu.return_vars(carry_variables)

        # Dictionary defining a mapping from the generated
        # unique variable names to the names of nodes of the rhs
        rhs_vars_inverse = {v: k for k, v in rhs_vars.items()}

        return query, rhs_vars_inverse

    def rewrite(self, rule, instance, rhs_typing=None):
        """Perform SqPO rewiting of the graph with a rule."""
        # Generate corresponding Cypher query
        query, rhs_vars_inverse = self.rule_to_cypher(
            rule, instance, rhs_typing)
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
                    if v["id"] is not None:
                        rhs_g[k] = v["id"]
                except:
                    pass
        rhs_g = {
            rhs_vars_inverse[k]: v for k, v in rhs_g.items()
        }
        return rhs_g
