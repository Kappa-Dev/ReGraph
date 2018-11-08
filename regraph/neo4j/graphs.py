"""Neo4j driver for regraph."""
import warnings
from neo4j.v1 import GraphDatabase

from regraph.utils import normalize_attrs
from regraph.exceptions import TypedNeo4jGraphError, ReGraphWarning
from . import cypher_utils as cypher
from . import hierarchy


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
        print(query)
        with self._driver.session() as session:
            if len(query) > 0:
                result = session.run(query)
                return result

    def _clear(self):
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

    def _drop_constraint(self, prop):
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
            {"n_" + source: source, "n_" + target: target},
            node_label=self._node_label)
        query += cypher.add_edge(
            edge_var='new_edge',
            source_var="n_" + source,
            target_var="n_" + target,
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
            if type(n) != str:
                try:
                    n_id, attrs = n
                    normalize_attrs(
                        attrs)
                    q, carry_variables =\
                        cypher.add_node(
                            n_id, n_id, 'new_id_' + n_id,
                            node_label=self._node_label,
                            attrs=attrs)
                except ValueError as e:
                    q, carry_variables =\
                        cypher.add_node(
                            n, n, 'new_id_' + n,
                            node_label=self._node_label)
            else:
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

    def add_node_attrs(self, node, attrs):
        """Add attributes to the node."""
        normalize_attrs(attrs)
        query = (
            cypher.match_node("n", node, self._node_label) +
            cypher.add_attributes("n", attrs)
        )
        result = self.execute(query)
        return result

    def set_node_attrs(self, node, attrs, update=False):
        """Overwrite all the node attributes.

        node :
            Id of the node whose attrs should be set
        attrs : dict
            Dictionary containing attrs
        update : optional
            If is set to False, updates only the attributes
            whose keys are in 'attrs', all the attributes not
            mentioned in 'attrs' stay the same. Otherwise,
            overwrites all the attributes (default: False)
        """
        normalize_attrs(attrs)
        query = (
            cypher.match_node("n", node, self._node_label) +
            cypher.set_attributes("n", attrs, update)
        )
        result = self.execute(query)
        return result

    def remove_node_attrs(self, node, attrs):
        """Remove attributes from the node."""
        normalize_attrs(attrs)
        query = (
            cypher.match_node(
                "n", node, self._node_label) +
            cypher.remove_attributes("n", attrs)
        )
        result = self.execute(query)
        return result

    def add_edge_attrs(self, source, target, attrs):
        """Add attributes to the edge."""
        normalize_attrs(attrs)
        query = (
            cypher.match_edge(
                "s", "t", source, target, "rel", self._edge_label) +
            cypher.add_attributes("rel", attrs)
        )
        result = self.execute(query)
        return result

    def set_edge_attrs(self, source, target, attrs, update=False):
        """Overwrite all the edge attributes.

        source :
            Id of the source node of the edge
        target :
            Id of the target node of the edge
        attrs : dict
            Dictionary containing attrs
        update : optional
            If is set to False, updates only the attributes
            whose keys are in 'attrs', all the attributes not
            mentioned in 'attrs' stay the same. Otherwise,
            overwrites all the attributes (default: False)
        """
        normalize_attrs(attrs)
        query = (
            cypher.match_edge(
                "s", "t", source, target, "rel", self._edge_label) +
            cypher.set_attributes("rel", attrs, update)
        )
        result = self.execute(query)
        return result

    def remove_edge_attrs(self, source, target, attrs):
        """Remove attributes from the edge."""
        normalize_attrs(attrs)
        query = (
            cypher.match_edge(
                "s", "t", source, target, "rel", self._edge_label) +
            cypher.remove_attributes("rel", attrs)
        )
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
            cypher.remove_node(node)
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

    def get_node_attrs(self, node_id):
        """Return node's attributes."""
        query = cypher.get_node_attrs(
            node_id, self._node_label,
            "attributes")
        result = self.execute(query)
        return cypher.properties_to_attributes(
            result, "attributes")

    def get_node(self, node_id):
        """Call 'get_node_attrs'."""
        return self.get_node_attrs(node_id)

    def get_edge_attrs(self, s, t):
        """Return edge attributes."""
        query = cypher.get_edge_attrs(
            s, t, self._edge_label,
            "attributes")
        result = self.execute(query)
        return cypher.properties_to_attributes(
            result, "attributes")

    def get_edge(self, s, t):
        """Call 'get_edge_attrs'."""
        return self.get_edge_attrs(s, t)

    def exists_edge(self, s, t):
        """Test if an edge 's'->'t' exists."""
        query = cypher.exists_edge(
            s, t,
            node_label=self._node_label,
            edge_label=self._edge_label)
        result = self.execute(query)
        for record in result:
            if "result" in record.keys():
                return record["result"]

    def relabel_node(self, node_id, new_id):
        """Change the 'id' property of the node."""
        attrs = {"id": new_id}
        normalize_attrs(attrs)
        query = (
            cypher.match_node("n", node_id) +
            cypher.set_node_attrs("n", attrs, update=False)
        )
        result = self.execute(query)
        return result

    def successors(self, node):
        """Return node's successors id."""
        query = cypher.successors_query(
            node, node,
            node_label=self._node_label,
            edge_label=self._edge_label)
        result = self.execute(query)
        succ = set()
        for record in result:
            if record["suc"] is not None:
                succ.add(record["suc"])
        return succ

    def predecessors(self, node):
        """Return node's predecessors id."""
        query = cypher.predecessors_query(
            node, node,
            node_label=self._node_label,
            edge_label=self._edge_label)
        result = self.execute(query)
        pred = set()
        for record in result:
            if record["pred"] is not None:
                pred.add(record["pred"])
        return pred

    def clone_node(self, node, name=None, edge_labels=None,
                   ignore_naming=False, profiling=False):
        """Clone a node of the graph."""
        if edge_labels is None:
            edge_labels = [self._edge_label]

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
                edge_labels=edge_labels,
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

    def find_matching(self, pattern, nodes=None, pattern_typing=None):
        """Find matchings of a pattern in the graph."""
        if len(pattern.nodes()) != 0:
            result = self.execute(
                cypher.find_matching(
                    pattern,
                    node_label=self._node_label,
                    edge_label=self._edge_label,
                    nodes=nodes,
                    pattern_typing=pattern_typing))
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


class TypedNeo4jGraph(hierarchy.Neo4jHierarchy):
    """Class implementing two level hiearchy.

    Top level represents a data instance, while bottom level represents
    a graphical schema.
    """

    def __init__(self, uri, user, password,
                 schema_graph=None, data_graph=None,
                 typing=None):
        """Initialize driver.

        Parameters:
        ----------
        uri : str
            Uri of bolt listener, for example 'bolt://127.0.0.1:7687'
        user : str
            Neo4j database user id
        password : str
            Neo4j database password
        schema_graph : dict, optional
            Schema graph to initialize the TypedGraph in JSON representation:
            {"nodes": <networkx_like_nodes>, "edges": <networkx_like_edges>}.
            By default is empty.
        data_graph : dict, optional
            Data graph to initialize the TypedGraph in JSON representation:
            {"nodes": <networkx_like_nodes>, "edges": <networkx_like_edges>}.
            By default is empty.
        typing : dict, optional
            Dictionary contaning typing of data nodes by schema nodes. By default is
            empty.
        """
        if data_graph is not None:
            if schema_graph is None:
                raise TypedNeo4jGraphError(
                    "Cannot initialize a typed graph by "
                    "empty schema and non-empty data: "
                    "typing should be total")
            if len(typing) == 0:
                raise TypedNeo4jGraphError(
                    "Cannot initialize a typed graph with "
                    "non-total typing '{}'".format(typing))
        else:
            data_graph = {"nodes": [], "edges": []}

        if schema_graph is None:
            schema_graph = {"nodes": [], "edges": []}
        if typing is None:
            typing = dict()

        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))

        self._graph_label = "graph"
        self._typing_label = "homomorphism"
        self._relation_label = "binaryRelation"

        self._data_label = "node"
        self._schema_label = "type"

        query = "CREATE " + cypher.constraint_query(
            'n', self._graph_label, 'id')
        self.execute(query)

        # create data/schema nodes
        skeleton = self._access_graph(
            self._graph_label, self._typing_label)
        skeleton_nodes = skeleton.nodes()
        if self._data_label not in skeleton_nodes:
            self.add_graph(
                self._data_label,
                node_list=data_graph["nodes"],
                edge_list=data_graph["edges"])
        else:
            if len(data_graph["nodes"]) > 0:
                old_data = self._access_graph(self._data_label)
                if len(old_data.nodes()) > 0:
                    warnings.warn(
                        "Data graph was non-empty and was overwritten with "
                        "provided nodes and edges!", ReGraphWarning
                    )
                old_data._clear()
                old_data.add_nodes_from(data_graph["nodes"])
                old_data.add_edges_from(data_graph["edges"])

        if self._schema_label not in skeleton_nodes:
            self.add_graph(
                self._schema_label,
                node_list=schema_graph["nodes"],
                edge_list=schema_graph["edges"])
        else:
            if len(schema_graph["nodes"]) > 0:
                old_schema = self._access_graph(self._schema_label)
                if len(old_schema.nodes()) > 0:
                    warnings.warn(
                        "Schema graph was non-empty and was overwritten with "
                        "provided nodes and edges!", ReGraphWarning
                    )
                old_schema._clear()
                old_schema.add_nodes_from(schema_graph["nodes"])
                old_schema.add_edges_from(schema_graph["edges"])
        if (self._data_label, self._schema_label) not in skeleton.edges():
            self.add_typing(self._data_label, self._schema_label, typing)

    def find_data_matching(self, pattern,
                           pattern_typing=None, nodes=None):
        return self.find_matching(
            self._data_label,
            pattern,
            pattern_typing={
                self._schema_label: pattern_typing
            },
            nodes=nodes)

    def find_schema_matching(self, pattern, nodes=None):
        return self.find_matching(
            self._schema_label,
            pattern,
            nodes=nodes)

    def rewrite_data(self, rule, instance,
                     rhs_typing=None, strict=False):
        return self.rewrite(
            self._data_label,
            rule=rule,
            instance=instance,
            rhs_typing={
                self._schema_label: rhs_typing
            },
            strict=strict)

    def rewrite_schema(self, rule, instance,
                       p_typing=None, strict=False):
        return self.rewrite(
            self._schema_label,
            rule=rule,
            instance=instance,
            p_typing={
                self._data_label: p_typing
            },
            strict=strict)
