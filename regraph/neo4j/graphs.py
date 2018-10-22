"""Neo4j driver for regraph."""
from neo4j.v1 import GraphDatabase

from regraph.default.utils import normalize_attrs
import regraph.neo4j.cypher_utils as cypher


class Neo4jGraph(object):
    """Class implementing Neo4j graph instance.

    This class encapsulates neo4j.v1.GraphDatabase object
    Attributes
    ----------
    _driver
    _node_label
    _edge_label
    """

    def __init__(self, driver=None, uri=None,
                 user=None, password=None,
                 node_label="node",
                 edge_label="edge",
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
        node_label : optional
        edge_label : optional
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

        self._node_label = node_label
        self._edge_label = edge_label

        if unique_node_ids:
            self.set_constraint('id')

    def execute(self, query):
        """Execute a Cypher query."""
        with self._driver.session() as session:
            if len(query) > 0:
                result = session.run(query)
                return result

    def clear(self):
        """Clear graph database.

        Returns
        -------
        result : BoltStatementResult
        """
        query = cypher.clear_graph(self._node_label)
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
        query = "CREATE " + cypher.constraint_query(
            'n', self._node_label, prop)
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
        query = "DROP " + cypher.constraint_query('n', self._node_label, prop)
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
            cypher.add_node(
                node, node, 'new_id',
                node_label=self._node_label,
                attrs=attrs,
                literal_id=True,
                ignore_naming=ignore_naming)[0] +\
            cypher.return_vars(['new_id'])

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
        query += cypher.match_nodes(
            {source: source, target: target},
            node_label=self._node_label)
        query += cypher.add_edge(
            edge_var='new_edge',
            source_var=source,
            target_var=target,
            edge_label=self._edge_label,
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
                    cypher.add_node(
                        n_id, n_id, 'new_id_' + n_id,
                        node_label=self._node_label,
                        attrs=attrs)
            except ValueError:
                q, carry_variables =\
                    cypher.add_node(
                        n, n, 'new_id_' + n,
                        node_label=self._node_label)
            query += q + cypher.with_vars(carry_variables)
        if len(carry_variables) > 0:
            query += cypher.return_vars(carry_variables)

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
                    cypher.add_edge(
                        edge_var=u + "_" + v,
                        source_var=u,
                        target_var=v,
                        edge_label=self._edge_label,
                        attrs=attrs))
            except ValueError:
                u, v = e
                nodes_to_match.add(u)
                nodes_to_match.add(v)
                edge_creation_queries.append(
                    cypher.add_edge(
                        edge_var=u + "_" + v,
                        source_var=u,
                        target_var=v,
                        edge_label=self._edge_label))
        if len(edges) > 0:
            query += cypher.match_nodes(
                {n: n for n in nodes_to_match},
                node_label=self._node_label)
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
            cypher.match_node(
                node, node,
                node_label=self._node_label) +\
            cypher.remove_node([node])
        result = self.execute(query)
        return result

    def remove_edge(self, source, target, profiling=False):
        """Remove an edge from the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        query +=\
            cypher.match_edge(
                source, target, source, target, 'edge_var',
                edge_label='edge') +\
            cypher.remove_edge('edge_var')
        result = self.execute(query)
        return result

    def nodes(self):
        """Return a list of nodes of the graph."""
        query = cypher.get_nodes(node_label=self._node_label)
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        """Return the list of edges of the graph."""
        query = cypher.get_edges(
            self._node_label,
            self._node_label,
            self._edge_label)
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]

    def get_node(self, node_id):
        """Return node's attributes."""
        query = cypher.get_node(node_id, node_label=self._node_label)
        result = self.execute(query)
        try:
            return dict(result.value()[0])
        except(IndexError):
            return None

    def get_edge(self, s, t):
        """Return edge attributes."""
        query = cypher.get_edge(
            s, t,
            source_label=self._node_label,
            target_label=self._node_label,
            edge_label=self._edge_label)
        result = self.execute(query)
        try:
            return dict(result.value()[0])
        except(IndexError):
            return None

    def successors(self, node):
        """Return node's successors id."""
        query = cypher.successors_query(
            node, node,
            node_label=self._node_label)
        succ = set(self.execute(query).value())
        return(succ)

    def predecessors(self, node):
        """Return node's predecessors id."""
        query = cypher.predecessors_query(
            node, node,
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
            cypher.match_node(
                'x', node,
                node_label=self._node_label) +\
            cypher.cloning_query(
                original_var='x',
                clone_var='new_node',
                clone_id=name,
                clone_id_var='uid',
                node_label=self._node_label,
                preserv_typing=preserv_typing,
                ignore_naming=ignore_naming)[0] +\
            cypher.return_vars(['uid'])
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
            cypher.match_nodes(
                {n: n for n in node_list},
                node_label=self._node_label) + "\n" +\
            cypher.merging_query(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_label=self._node_label,
                edge_label=self._edge_label,
                ignore_naming=ignore_naming)[0] +\
            cypher.return_vars(['new_id'])
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
            cypher.match_nodes(
                {n: n for n in node_list},
                node_label=self._node_label) + "\n" +\
            cypher.merging_query1(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_label=self._node_label,
                edge_label=self._edge_label,
                merge_typing=merge_typing,
                ignore_naming=ignore_naming)[0] +\
            cypher.return_vars(['new_id'])
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
                cypher.find_matching(
                    pattern, nodes,
                    node_label=self._node_label,
                    edge_label=self._edge_label))
            instances = list()

            for record in result:
                instance = dict()
                for k, v in record.items():
                    instance[k] = dict(v)["id"]
                instances.append(instance)
        else:
            instances = []
        return instances

    def rewrite(self, rule, instance):
        """Perform SqPO rewiting of the graph with a rule."""
        # Generate corresponding Cypher query
        query, rhs_vars_inverse = rule.to_cypher(
            instance, self._node_label, self._edge_label)

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
