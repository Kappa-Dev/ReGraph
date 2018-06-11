"""Neo4j driver for regraph."""
import uuid

from regraph.default.utils import keys_by_value, normalize_attrs
from regraph.neo4j.cypher_utils import *


def generate_var_name():
    """Generate unique variable names."""
    uid = "uid" + str(uuid.uuid4()).replace("-", "")
    return uid


class Neo4jGraph(object):
    """Class implementing neo4j graph instance."""

    def __init__(self, label, db, set_constraint=False):
        self._label = label
        self._node_label = ":".join(['node', self._label])
        self._db = db
        if set_constraint:
            self.set_constraint('id')

    def execute(self, query):
        """Execute a Cypher query."""
        with self._db._driver.session() as session:
            result = session.run(query)
            return result

    def clear(self):
        """Clear graph database."""
        query = clear_graph(label=self._node_label)
        result = self.execute(query)
        return result

    def set_constraint(self, prop):
        """Set a constraint on the database."""
        query = "CREATE " + constraint_query('n', self._label, prop)
        result = self.execute(query)
        return result

    def drop_constraint(self, prop):
        """Drop a constraint on the database."""
        query = "DROP " + constraint_query('n', self._label, prop)
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
            create_node(
                node, node, 'new_id',
                label=self._node_label,
                attrs=attrs,
                literal_id=True,
                ignore_naming=ignore_naming)[0] +\
            return_vars(['new_id'])

        result = self.execute(query)
        # print(result)
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
        query += match_nodes({
            source: source,
            target: target
        }, label=self._node_label)
        query += create_edge(source, target,
                             edge_label='edge',
                             attrs=attrs)
        result = self.execute(query)
        # print(result)
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
                    create_node(
                        n_id, n_id, 'new_id_' + n_id,
                        label=self._node_label,
                        attrs=attrs)
            except:
                q, carry_variables =\
                    create_node(
                        n, n, 'new_id_' + n,
                        label=self._node_label)
            query += q + with_vars(carry_variables)
        query += return_vars(carry_variables)
        result = self.execute(query)
        # print(result)
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
                    create_edge(u, v,
                                edge_label='edge',
                                attrs=attrs))
            except:
                u, v = e
                nodes_to_match.add(u)
                nodes_to_match.add(v)
                edge_creation_queries.append(
                    create_edge(u, v,
                                edge_label='edge'))
        query += match_nodes({n: n for n in nodes_to_match},
                             label=self._node_label)
        for q in edge_creation_queries:
            query += q
        result = self.execute(query)
        # print(result)
        return result

    def remove_node(self, node, profiling=False):
        """Remove a node from the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        query +=\
            match_node(node, node,
                       label=self._node_label) +\
            delete_nodes_var([node])
        result = self.execute(query)
        # print(result)
        return result

    def remove_edge(self, source, target, profiling=False):
        """Remove an edge from the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        query +=\
            match_edge(source, target, source, target, 'edge_var',
                       edge_label='edge') +\
            delete_edge_var('edge_var')
        result = self.execute(query)
        # print(result)
        return result

    def nodes(self):
        """Return a list of nodes of the graph."""
        query = get_nodes(label=self._node_label)
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        """Return the list of edges of the graph."""
        query = get_edges(label_source=self._node_label,
                          label_target=self._node_label,
                          edge_label='edge')
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]

    def get_node(self, node_id):
        """Return node's attributes."""
        query = get_node(node_id, node_label=self._node_label)
        result = self.execute(query)
        try:
            return dict(result.value()[0])
        except(IndexError):
            return None

    def get_edge(self, s, t):
        """Return edge attributes."""
        query = get_edge(s, t,
                         source_label=self._node_label,
                         target_label=self._node_label,
                         edge_label='edge')
        result = self.execute(query)
        try:
            return dict(result.value()[0])
        except(IndexError):
            return None

    def find_successors(self, node):
        """Return node's successors id."""
        query = successors_query(node, node,
                                 node_label=self._node_label)
        succ = set(self.execute(query).value())
        return(succ)

    def find_predecessors(self, node):
        """Return node's predecessors id."""
        query = predecessors_query(node, node,
                                   node_label=self._node_label)
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
            match_node('x', node,
                       label=self._node_label) +\
            cloning_query(
                original_var='x',
                clone_var='new_node',
                clone_id=name,
                clone_id_var='uid',
                node_label=self._node_label,
                preserv_typing=preserv_typing,
                ignore_naming=ignore_naming)[0] +\
            return_vars(['uid'])
        # print(query)
        result = self.execute(query)
        return result

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
            match_nodes({n: n for n in node_list},
                        label=self._node_label) + "\n" +\
            merging_query(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_label=self._node_label,
                edge_label='edge',
                ignore_naming=ignore_naming)[0] +\
            return_vars(['new_id'])
        # print(query)
        result = self.execute(query)
        # print(result.value())
        # print(result.single())
        return result

    def merge_nodes1(self, node_list, name=None,
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
            match_nodes({n: n for n in node_list},
                        label=self._node_label) + "\n" +\
            merging_query1(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_label=self._node_label,
                edge_label='edge',
                ignore_naming=ignore_naming)[0] +\
            return_vars(['new_id'])
        # print(query)
        result = self.execute(query)
        return result

    def find_matching(self, pattern, nodes=None):
        """Find matchings of a pattern in the graph."""
        result = self.execute(find_matching(
            pattern, nodes,
            node_label=self._node_label, edge_label='edge'))
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
            query += match_pattern_instance(
                rule.lhs, lhs_vars, match_instance_vars,
                node_label=self._node_label, edge_label='edge')
            query += "\n\n"
        else:
            query += "// Empty instance \n\n"

        # Add instance nodes to the set of vars to carry
        carry_variables = set(match_instance_vars.keys())

        # Generate cloning subquery
        for lhs_node, p_nodes in rule.cloned_nodes().items():
            print(lhs_node, p_nodes)
            print('-------------')
            query += "// Cloning node '{}' of the lhs \n".format(lhs_node)
            clones = set()
            preds_to_ignore = dict()
            sucs_to_ignore = dict()
            for p_node in p_nodes:
                print(p_node)
                if p_node != lhs_node:
                    clones.add(p_node)
                    preds_to_ignore[p_node] = set()
                    sucs_to_ignore[p_node] = set()
                    for u, v in rule.removed_edges():
                        print(u,v)
                        print(preds_to_ignore)
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

                q, carry_variables = cloning_query(
                    original_var=lhs_vars[lhs_node],
                    clone_var=p_vars[n],
                    clone_id=n,
                    clone_id_var=clone_id_var,
                    node_label=self._node_label,
                    preserv_typing=True,
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
                node_label=self._node_label,
                edge_label=None,
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
                label=self._node_label,
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
            query += create_edge(rhs_vars[u], rhs_vars[v],
                                 edge_label='edge')
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

    def rule_to_cypher_v2(self, rule, instance, generate_var_ids=False):
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
            # rule._escape()
            lhs_vars = {n: "lhs_" + str(n) for n in rule.lhs.nodes()}
            p_vars = {n: "p_" + str(n) for n in rule.p.nodes()}
            rhs_vars = {n: "rhs_" + str(n) for n in rule.rhs.nodes()}

        # ids of the nodes of instance
        match_instance_ids = {lhs_vars[k]: v for k, v in instance.items()}

        # Cloning the nodes of LHS
        for lhs_node, p_nodes in rule.cloned_nodes().items():
            q_clone_match = match_node(
                                var_name=lhs_vars[lhs_node],
                                node_id=match_instance_ids[lhs_vars[lhs_node]],
                                label=self._node_label)
            q_clone_match += "// Cloning node '{}' of the lhs \n".format(lhs_node)
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
                q_clone =\
                    q_clone_match +\
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
                    node_label=self._node_label,
                    preserv_typing=True,
                    sucs_to_ignore=sucs_to_ignore[n],
                    preds_to_ignore=preds_to_ignore[n],
                    ignore_naming=True)
                q_clone += q
                q_clone += "RETURN {}".format(clone_id_var)
                q_clone += "\n"
                result = self.execute(q_clone).single().value()
                match_instance_ids[p_vars[n]] = result

        # Removing of  nodes
        for node in rule.removed_nodes():
            node_var = lhs_vars[node]
            q_node_rm = "// Removing node '{}' of the lhs \n".format(node)
            q_clone_match = match_node(
                                var_name=lhs_vars[node_var],
                                node_id=match_instance_ids[node_var],
                                label=self._node_label)
            q_node_rm += delete_nodes_var([node_var])
            q_node_rm += "\n"
            self.execute(q_node_rm)
            del match_instance_ids[node_var]

        # Removing of edges
        for u, v in rule.removed_edges():
            if u in match_instance_ids.keys() and v in match_instance_ids.keys():
                u_var = lhs_vars[u]
                v_var = lhs_vars[v]
                u_id = match_instance_ids[lhs_vars[u]]
                v_id = match_instance_ids[lhs_vars[v]]
                edge_var = 'e'
                q_edge_rm = "// Removing edge '{}->{}' of the lhs \n".format(u, v)
                q_edge_rm += match_edge(u_var, v_var, u_id, v_id, edge_var)
                q_edge_rm += delete_edge_var(edge_var)
                q_edge_rm += "\n"
                self.execute(q_edge_rm)

        # Rename untouched vars as they are in P
        for n in rule.lhs.nodes():
            if n not in rule.removed_nodes():
                match_instance_ids[p_vars[n]] = match_instance_ids[lhs_vars[n]]
                del match_instance_ids[lhs_vars[n]]

        # Merging nodes of P
        for rhs_key, p_nodes in rule.merged_nodes().items():
            q_merge =\
                "// Merging nodes '{}' of the preserved part ".format(p_nodes) +\
                "into '{}' \n".format(rhs_key)
            merged_id = generate_var_name()
            match_dict = {p_vars[n]: match_instance_ids[p_vars[n]] for n in p_nodes}
            q_merge += match_nodes(match_dict, label=self._node_label)
            merged_id_var = "merged_id_var"
            q, carry_variables = merging_query(
                original_vars=[p_vars[n] for n in p_nodes],
                merged_var=rhs_vars[rhs_key],
                merged_id=merged_id,
                merged_id_var=merged_id_var,
                node_label=self._node_label,
                edge_label=None,
                ignore_naming=False)
            q_merge += q
            q_merge += "\n"
            q_merge += "RETURN {}".format(merged_id_var)
            result = self.execute(q_merge)
            match_instance_ids[rhs_vars[rhs_key]] = merged_id

        # Generate nodes addition subquery
        for rhs_node in rule.added_nodes():
            q_node_add = "// Adding node '{}' from the rhs \n".format(rhs_node)
            if generate_var_ids:
                new_node_id_var = generate_var_name()
            else:
                new_node_id_var = "rhs_" + str(rhs_node) + "_id"
            q, carry_variables = create_node(
                rhs_vars[rhs_node], rhs_node, new_node_id_var,
                label=self._node_label,
                ignore_naming=True)
            q_node_add += q
            q_node_add += return_vars([new_node_id_var])
            q_node_add += "\n"
            result = self.execute(q_node_add).single().value()
            match_instance_ids[rhs_vars[rhs_node]] = result

        # Rename untouched vars as they are in RHS
        for n in rule.rhs.nodes():
            if n not in rule.added_nodes() and\
               n not in rule.merged_nodes().keys():
                match_instance_ids[rhs_vars[n]] = match_instance_ids[p_vars[n]]
                del match_instance_ids[p_vars[n]]

        # Generate edges addition subquery
        for u, v in rule.added_edges():
            q_edge_add = "// Adding edge '{}->{}' from the rhs \n".format(u, v)
            u_var = rhs_vars[u]
            v_var = rhs_vars[v]
            u_id = match_instance_ids[rhs_vars[u]]
            v_id = match_instance_ids[rhs_vars[v]]
            q_edge_add += match_nodes({u_var: u_id, v_var: v_id},
                                      label=self._node_label)
            q_edge_add += create_edge(u_var, v_var,
                                      edge_label='edge')
            q_edge_add += "\n"
            self.execute(q_edge_add)

        # Dictionary defining a mapping from the generated
        # unique variable names to the names of nodes of the rhs
        rhs_vars_inverse = {v: k for k, v in rhs_vars.items()}

        return rhs_vars_inverse


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
