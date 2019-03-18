"""Neo4j driver for regraph."""
import os
import json
import warnings
from neo4j.v1 import GraphDatabase

from regraph.utils import (normalize_attrs,
                           load_nodes_from_json,
                           load_edges_from_json,
                           attrs_from_json, keys_by_value)
from regraph.exceptions import ReGraphWarning, ReGraphError
from . import cypher_utils as cypher
from . import hierarchy


class Neo4jGraph(object):
    """Class implementing Neo4j graph instance.

    This class encapsulates neo4j.v1.GraphDatabase object.
    It provides an interface for accessing graph sitting
    in the DB. This interface is similar (in fact is
    intended to be as similar as possible) to the
    `networkx.DiGraph` object.

    Attributes
    ----------
    _driver :  neo4j.v1.GraphDatabase
        Driver providing connection to a Neo4j database
    _node_label : str
        Label of nodes inducing the manipulated subgraph.
    _edge_label : str
        Type of relations used in the manipulated subgraph.
    """

    def __init__(self, driver=None, uri=None,
                 user=None, password=None,
                 node_label="node",
                 edge_label="edge",
                 unique_node_ids=True):
        """Initialize Neo4jGraph object.

        Parameters
        ----------
        driver : neo4j.v1.direct.DirectDriver, optional
            Driver providing connection to a Neo4j database
        uri : str, optional
            Uri for a new Neo4j database connection (bolt)
        user : str, optional
            Username for the Neo4j database connection
        password : str, optional
            Password for the Neo4j database connection
        node_label : optional
            Label of nodes inducing the subgraph to scope.
            By default `"node"`.
        edge_label : optional
            Type of relations inducing the subgraph to scope.
            By default `"edge"`.
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
        self.unique_node_ids = unique_node_ids
        if unique_node_ids:
            self.set_constraint('id')

    def execute(self, query):
        """Execute a Cypher query."""
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

    @classmethod
    def copy(cls, graph, node_label, edge_label="edge"):
        """Create a copy of the graph."""
        # copy all the nodes
        copy_nodes_q = (
            "MATCH (n:{}) CREATE (n1:{}) SET n1=n\n".format(
                graph._node_label, node_label)
        )
        graph.execute(copy_nodes_q)
        copy_edges_q = (
            "MATCH (n:{})-[r:{}]->(m:{}), (n1:{}), (m1:{}) \n".format(
                graph._node_label, graph._edge_label, graph._node_label,
                node_label, node_label) +
            "WHERE n1.id=n.id AND m1.id=m.id \n" +
            "MERGE (n1)-[r1:{}]->(m1) SET r1=r\n".format(edge_label)
        )
        graph.execute(copy_edges_q)
        return cls(
            driver=graph._driver,
            node_label=node_label,
            edge_label=edge_label,
            unique_node_ids=graph.unique_node_ids)

    def close(self):
        """Close connection to the database."""
        self._driver.close()

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

    def add_node(self, node, attrs=None, ignore_naming=False,
                 profiling=False):
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
                "n_" + node, node, 'new_id',
                node_label=self._node_label,
                attrs=attrs,
                literal_id=True,
                ignore_naming=ignore_naming)[0] +\
            cypher.return_vars(['new_id'])

        result = self.execute(query)
        new_id = result.single()['new_id']
        return new_id

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

    def add_nodes_from(self, nodes, ignore_naming=False, profiling=False,
                       holistic=False):
        """Add nodes to the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        if holistic:
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
                                attrs=attrs,
                                ignore_naming=ignore_naming)
                    except ValueError as e:
                        q, carry_variables =\
                            cypher.add_node(
                                n, n, 'new_id_' + n,
                                node_label=self._node_label,
                                ignore_naming=ignore_naming)
                else:
                    q, carry_variables =\
                        cypher.add_node(
                            n, n, 'new_id_' + n,
                            node_label=self._node_label,
                            ignore_naming=ignore_naming)
                query += q + cypher.with_vars(carry_variables)
            if len(carry_variables) > 0:
                query += cypher.return_vars(carry_variables)
            result = self.execute(query)
            return result
        else:
            print("Addind non-holistic nodes")
            for n in nodes:
                try:
                    n_id, attrs = n
                    self.add_node(n_id, attrs)
                except ValueError:
                    self.add_node(n)

    def add_edges_from(self, edges, profiling=False, holistic=False):
        """Add edges to the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""

        if holistic:
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
        else:
            print("Addind non-holistic edges")
            for e in edges:
                try:
                    u, v, attrs = e
                    self.add_edge(u, v, attrs)
                except ValueError:
                    u, v = e
                    self.add_edge(u, v)

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
                "s", "t", source, target, "rel",
                self._node_label, self._node_label,
                self._edge_label) +
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
                "s", "t", source, target, "rel",
                self._node_label, self._edge_label,
                self._edge_label) +
            cypher.set_attributes("rel", attrs, update)
        )
        result = self.execute(query)
        return result

    def remove_edge_attrs(self, source, target, attrs):
        """Remove attributes from the edge."""
        normalize_attrs(attrs)
        query = (
            cypher.match_edge(
                "s", "t", source, target, "rel",
                self._node_label, self._edge_label,
                self._edge_label) +
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
                "s", "t", source, target, 'edge_var',
                self._node_label, self._node_label,
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
        # print(query)
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
            query = cypher.find_matching(
                pattern,
                node_label=self._node_label,
                edge_label=self._edge_label,
                nodes=nodes,
                pattern_typing=pattern_typing)
            result = self.execute(query)
            instances = list()

            for record in result:
                instance = dict()
                for k, v in record.items():
                    instance[k] = dict(v)["id"]
                instances.append(instance)
        else:
            instances = []
        return instances

    def rewrite(self, rule, instance, holistic=True, edge_labels=None):
        """Perform SqPO rewiting of the graph with a rule."""
        # Generate corresponding Cypher query
        if holistic:
            query, rhs_vars_inverse = rule.to_cypher(
                instance, self._node_label, self._edge_label)
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
        else:
            if edge_labels is None:
                edge_labels = [self._edge_label]

            # 1st phase
            p_g = dict()
            cloned_lhs_nodes = set()
            # Clone nodes
            for lhs, p_nodes in rule.cloned_nodes().items():
                for i, p in enumerate(p_nodes):
                    if i == 0:
                        p_g[p] = instance[lhs]
                        cloned_lhs_nodes.add(lhs)
                    else:
                        clone_id = self.clone_node(
                            instance[lhs], edge_labels=edge_labels)
                        p_g[p] = clone_id
            # Delete nodes and add preserved nodes to p_g dictionary
            removed_nodes = rule.removed_nodes()
            for n in rule.lhs.nodes():
                if n in removed_nodes:
                    self.remove_node(instance[n])
                elif n not in cloned_lhs_nodes:
                    p_g[keys_by_value(rule.p_lhs, n)[0]] =\
                        instance[n]

            # Delete edges
            for u, v in rule.removed_edges():
                self.remove_edge(p_g[u], p_g[v])

            # Remove node attributes
            for p_node, attrs in rule.removed_node_attrs().items():
                self.remove_node_attrs(
                    p_g[p_node],
                    attrs)

            # Remove edge attributes
            for (u, v), attrs in rule.removed_edge_attrs().items():
                self.remove_edge_attrs(p_g[u], p_g[v], attrs)

            # 2nd phase
            rhs_g = dict()
            merged_nodes = set()
            # Merge nodes
            for rhs, p_nodes in rule.merged_nodes().items():
                merge_id = self.merge_nodes(
                    ["n_" + p_g[p] for p in p_nodes])
                merged_nodes.update(rhs)
                rhs_g[rhs] = merge_id

            # Add nodes and add preserved nodes to rhs_g dictionary
            added_nodes = rule.added_nodes()
            for n in rule.rhs.nodes():
                if n in added_nodes:
                    new_id = self.add_node(n)
                    rhs_g[n] = new_id
                elif n not in merged_nodes:
                    rhs_g[n] = p_g[keys_by_value(rule.p_rhs, n)[0]]

            # Add edges
            for u, v in rule.added_edges():
                self.add_edge(rhs_g[u], rhs_g[v])

            # Add node attributes
            for rhs_node, attrs in rule.added_node_attrs().items():
                self.add_node_attrs(
                    rhs_g[rhs_node], attrs)

            # Add edge attributes
            for (u, v), attrs in rule.added_edge_attrs().items():
                self.add_edge_attrs(
                    rhs_g[u], rhs_g[v], attrs)

        return rhs_g

    def to_json(self):
        """Create a JSON representation of a graph."""
        j_data = {"edges": [], "nodes": []}
        # dump nodes
        for node in self.nodes():
            node_data = {}
            node_data["id"] = node
            node_attrs = self.get_node(node)
            if node_attrs is not None:
                attrs = {}
                for key, value in node_attrs.items():
                    attrs[key] = value.to_json()
                node_data["attrs"] = attrs
            j_data["nodes"].append(node_data)

        # dump edges
        for s, t in self.edges():
            edge_data = {}
            edge_data["from"] = s
            edge_data["to"] = t
            edge_attrs = self.get_edge(s, t)
            if edge_attrs is not None:
                attrs = {}
                for key, value in edge_attrs.items():
                    attrs[key] = value.to_json()
                edge_data["attrs"] = attrs
            j_data["edges"].append(edge_data)
        return j_data

    def to_d3_json(self):
        query = (
            "MATCH (n:{})".format(self._node_label) +
            "OPTIONAL MATCH (n)-[r:{}]-()\n".format(self._edge_label) +
            "WITH collect(n) as nodes, collect(r) as edges\n" +
            "WITH reduce(acc=[], n in nodes | acc + {id: n.id, attrs: n}) as node_aggregate, \n" +
            "reduce(acc=[], e in filter(e IN edges WHERE e IS NOT NULL) | acc + {source: e.start, target: e.end, attrs: e}) as edge_aggregate\n" +
            "RETURN {nodes: node_aggregate, links: edge_aggregate} as graph\n"
        )
        result = self.execute(query)
        return result.single()["graph"]

    def export(self, filename):
        """Export graph to JSON file.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        filename : str
            Name of the file to save the json serialization of the graph


        """
        with open(filename, 'w') as f:
            j_data = self.to_json()
            json.dump(j_data, f)
        return

    def _nodes_from_json(self, json_data):
        query = cypher.add_nodes_from_json(json_data, self._node_label)
        self.execute(query)

    @classmethod
    def from_json(cls, driver=None, uri=None, user=None, password=None,
                  j_data=None, node_label="node", edge_label="edge",
                  holistic=False):
        """Create a Neo4jGraph from a json-like dictionary."""
        graph = cls(
            driver=driver, uri=uri, user=user, password=password,
            node_label=node_label, edge_label=edge_label)
        if holistic:
            query = cypher.load_graph_from_json(
                j_data, graph._node_label, graph._edge_label)
            graph.execute(query)
        else:
            print("Adding not holistic")
            graph.add_nodes_from([
                (n["id"], attrs_from_json(n["attrs"]))
                for n in j_data["nodes"]])
            graph.add_edges_from([
                (e["from"], e["to"], attrs_from_json(e["attrs"]))
                for e in j_data["edges"]])
        return graph

    @classmethod
    def load(cls, driver=None, uri=None, user=None,
             password=None, filename=None, clear=False):
        """Load a Neo4j graph from a JSON file.

        Create a `networkx.(Di)Graph` object from
        a JSON representation stored in a file.

        Parameters
        ----------
        filename : str
            Name of the file to load the json serialization of the graph
        directed : bool, optional
            `True` if the graph to load is directed, `False` otherwise.
            Default value `True`.

        Returns
        -------
        nx.(Di)Graph object

        Raises
        ------
        ReGraphError
            If was not able to load the file

        """
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                j_data = json.loads(f.read())
                return cls.from_json(driver=driver, uri=uri,
                                     user=user, password=password,
                                     j_data=j_data, clear=clear)
        else:
            raise ReGraphError(
                "Error loading graph: file '%s' does not exist!" %
                filename
            )


class TypedNeo4jGraph(hierarchy.Neo4jHierarchy):
    """Class implementing two level hiearchy.

    This class encapsulates neo4j.v1.GraphDatabase object.
    It provides an interface for accessing typed graphs
    sitting in the Neo4j DB. Our system is assumed to
    consist of two graphs (the data graph) and (the schema graph)
    connected with a graph homomorphisms (defining typing of
    the data graph by the schema graph).

    Attributes
    ----------
    _driver :  neo4j.v1.GraphDatabase
        Driver providing connection to a Neo4j database
    _graph_label : str
    _typing_label : str
    _graph_edge_label : str
    _graph_typing_label : str
    _schema_node_label : str
        Label of nodes inducing the schema graph.
    _data_node_label : str

    Top level represents a data instance, while bottom level represents
    a graphical schema.
    """

    def __init__(self, 
                 uri=None, user=None, password=None, driver=None,
                 schema_graph=None, data_graph=None, typing=None, clear=False,
                 graph_label="graph",
                 typing_label="homomorphism",
                 graph_edge_label="edge",
                 graph_typing_label="typing",
                 schema_node_label="type", data_node_label="node"):
        """Initialize driver.

        Parameters:
        ----------
        uri : str, optional
            Uri of bolt listener, for example 'bolt://127.0.0.1:7687'
        user : str, optional
            Neo4j database user id
        password : str, optional
            Neo4j database password
        driver : neo4j.v1.direct.DirectDriver, optional
        graph_label : str, optional
            Label to use for skeleton nodes representing graphs.
        typing_label : str, optional
            Relation type to use for skeleton edges
            representing homomorphisms.
        graph_edge_label : str, optional
            Relation type to use for all graph edges.
        graph_typing_label : str, optional
            Relation type to use for edges encoding homomorphisms.
        schema_graph : dict, optional
            Schema graph to initialize the TypedGraph in JSON representation:
            {"nodes": <networkx_like_nodes>, "edges": <networkx_like_edges>}.
            By default is empty.
        data_graph : dict, optional
            Data graph to initialize the TypedGraph in JSON representation:
            {"nodes": <networkx_like_nodes>, "edges": <networkx_like_edges>}.
            By default is empty.
        typing : dict, optional
            Dictionary contaning typing of data nodes by schema nodes.
            By default is empty.
        """

        if data_graph is None:
            data_graph = {"nodes": [], "edges": []}

        if schema_graph is None:
            schema_graph = {"nodes": [], "edges": []}
        if typing is None:
            typing = dict()

        if clear is True:
            self._clear()

        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))

        self._graph_label = "graph"
        self._typing_label = "homomorphism"
        self._relation_label = None

        self._graph_edge_label = "edge"
        self._graph_typing_label = "typing"
        self._graph_relation_label = "relation"

        self._schema_node_label = "type"
        self._data_node_label = "node"

        # create data/schema nodes
        # skeleton = self._access_graph(
        #     self._graph_label, self._typing_label)
        # skeleton_nodes = skeleton.nodes()
        # if self._data_node_label not in skeleton_nodes:
        #     self.add_graph(
        #         self._data_node_label,
        #         node_list=data_graph["nodes"],
        #         edge_list=data_graph["edges"])
        # else:
        #     if len(data_graph["nodes"]) > 0:
        #         old_data = self._access_graph(self._data_node_label)
        #         if len(old_data.nodes()) > 0:
        #             warnings.warn(
        #                 "Data graph was non-empty and was overwritten with "
        #                 "provided nodes and edges!", ReGraphWarning
        #             )
        #         old_data._clear()
        #         old_data.add_nodes_from(data_graph["nodes"])
        #         old_data.add_edges_from(data_graph["edges"])

        # if self._schema_node_label not in skeleton_nodes:
        #     self.add_graph(
        #         self._schema_node_label,
        #         node_list=schema_graph["nodes"],
        #         edge_list=schema_graph["edges"])
        # else:
        #     if len(schema_graph["nodes"]) > 0:
        #         old_schema = self._access_graph(self._schema_node_label)
        #         if len(old_schema.nodes()) > 0:
        #             warnings.warn(
        #                 "Schema graph was non-empty and was overwritten with "
        #                 "provided nodes and edges!", ReGraphWarning
        #             )
        #         old_schema._clear()
        #         old_schema.add_nodes_from(schema_graph["nodes"])
        #         old_schema.add_edges_from(schema_graph["edges"])

        # # if (self._data_node_label, self._schema_node_label) not in skeleton.edges():
        # self.add_typing(self._data_node_label, self._schema_node_label, typing)

    def find_data_matching(self, pattern,
                           pattern_typing=None, nodes=None):
        schema_typing = None
        if pattern_typing is not None:
            schema_typing = {
                self._schema_node_label: pattern_typing
            }
        return self.find_matching(
            self._data_node_label,
            pattern,
            pattern_typing=schema_typing,
            nodes=nodes)

    def find_schema_matching(self, pattern, nodes=None):
        return self.find_matching(
            self._schema_node_label,
            pattern,
            nodes=nodes)

    def rewrite_data(self, rule, instance,
                     rhs_typing=None, strict=False):
        if rhs_typing is None:
            rhs_typing = dict()
        return self.rewrite(
            self._data_node_label,
            rule=rule,
            instance=instance,
            rhs_typing={
                self._schema_node_label: rhs_typing
            },
            strict=strict)

    def rewrite_schema(self, rule, instance,
                       p_typing=None, strict=False):
        return self.rewrite(
            self._schema_node_label,
            rule=rule,
            instance=instance,
            p_typing={
                self._data_node_label: p_typing
            },
            strict=strict)

    def rename_schema_node(self, node_id, new_node_id):
        self.rename_node(self._schema_node_label, node_id, new_node_id)

    def rename_data_node(self, node_id, new_node_id):
        self.rename_node(self._data_node_label, node_id, new_node_id)

    def get_data(self):
        return self.get_graph(self._data_node_label)

    def get_schema(self):
        return self.get_graph(self._schema_node_label)

    def get_data_nodes(self):
        data = self.get_data()
        return data.nodes()

    def get_data_edges(self):
        data = self.get_data()
        return data.edges()

    def get_schema_nodes(self):
        schema = self.get_schema()
        return schema.nodes()

    def get_schema_edges(self):
        schema = self.get_schema()
        return schema.edges()

    def get_data_typing(self):
        return self.get_typing(
            self._data_node_label, self._schema_node_label)

    def get_node_type(self, node_id):
        t = self.node_type(self._data_node_label, node_id)
        return t[self._schema_node_label]

    def remove_data_node_attrs(self, node_id, attrs):
        g = self._access_graph(self._data_node_label)
        g.remove_node_attrs(node_id, attrs)

    def remove_schema_node_attrs(self, node_id, attrs):
        g = self._access_graph(self._schema_node_label)
        g.remove_node_attrs(node_id, attrs)

    def add_data_node_attrs(self, node_id, attrs):
        g = self._access_graph(self._data_node_label)
        g.add_node_attrs(node_id, attrs)

    def add_schema_node_attrs(self, node_id, attrs):
        g = self._access_graph(self._schema_node_label)
        g.add_node_attrs(node_id, attrs)

    def get_data_node(self, node_id):
        g = self._access_graph(self._data_node_label)
        return g.get_node(node_id)

    def get_schema_node(self, node_id):
        g = self._access_graph(self._schema_node_label)
        return g.get_node(node_id)

    # @classmethod
    # def from_json(cls, uri=None, user=None, password=None,
    #               driver=None, json_data=None, ignore=None, clear=False):
    #     """Create hierarchy object from JSON representation.

    #     Parameters
    #     ----------

    #     uri : str, optional
    #         Uri for Neo4j database connection
    #     user : str, optional
    #         Username for Neo4j database connection
    #     password : str, optional
    #         Password for Neo4j database connection
    #     driver : neo4j.v1.direct.DirectDriver, optional
    #         DB driver object
    #     json_data : dict, optional
    #         JSON-like dict containing representation of a hierarchy
    #     ignore : dict, optional
    #         Dictionary containing components to ignore in the process
    #         of converting from JSON, dictionary should respect the
    #         following format:
    #         {
    #             "graphs": <collection of ids of graphs to ignore>,
    #             "rules": <collection of ids of rules to ignore>,
    #             "typing": <collection of tuples containing typing
    #                 edges to ignore>,
    #             "rule_typing": <collection of tuples containing rule
    #                 typing edges to ignore>>,
    #             "relations": <collection of tuples containing
    #                 relations to ignore>,
    #         }
    #     directed : bool, optional
    #         True if graphs from JSON representation should be loaded as
    #         directed graphs, False otherwise, default value -- True

    #     Returns
    #     -------
    #     hierarchy : regraph.neo4j.TypedGraph
    #     """
    #     print("Started creating object")
    #     g = cls(
    #         uri=uri, user=user, password=password, driver=driver)
    #     print("Finished creating object")

    #     if clear is True:
    #         g._clear()

    #     print("Started filling up graphs")
    #     # add graphs
    #     for graph_data in json_data["graphs"]:
    #         if graph_data["id"] in ["node", "type"]:
    #             if "attrs" not in graph_data.keys():
    #                 attrs = dict()
    #             else:
    #                 attrs = attrs_from_json(graph_data["attrs"])
    #             g.add_graph(
    #                 graph_data["id"],)
    #     print("Finished filling up graphs")

    #     print("Started additng typing")
    #     # add typing
    #     for typing_data in json_data["typing"]:
    #         if typing_data["from"] == "node" and\
    #            typing_data["to"] == "type":
    #             if "attrs" not in typing_data.keys():
    #                 attrs = dict()
    #             else:
    #                 attrs = attrs_from_json(typing_data["attrs"])
    #             g.remove_typing("node", "type")
    #             g.add_typing(
    #                 typing_data["from"],
    #                 typing_data["to"],
    #                 typing_data["mapping"],
    #                 attrs)
    #     print("Finished addiing typing")
    #     return g
