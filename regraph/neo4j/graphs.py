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
from .cypher_utils import generic
from .cypher_utils import rewriting


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
            try:
                self.set_constraint('id')
            except:
                warnings.warn(
                    "Failed to create id uniqueness constraint")

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
        query = generic.clear_graph(self._node_label)
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
        query = "CREATE " + generic.constraint_query(
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
        try:
            query = "DROP " + generic.constraint_query('n', self._node_label, prop)
            result = self.execute(query)
            return result
        except:
            warnings.warn("Failed to drop constraint")

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
            rewriting.add_node(
                "n", node, 'new_id',
                node_label=self._node_label,
                attrs=attrs,
                literal_id=True,
                ignore_naming=ignore_naming)[0] +\
            generic.return_vars(['new_id'])

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
        query += generic.match_nodes(
            {"s": source, "t": target},
            node_label=self._node_label)
        query += rewriting.add_edge(
            edge_var='new_edge',
            source_var="s",
            target_var="t",
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
                            rewriting.add_node(
                                n_id, n_id, 'new_id_' + n_id,
                                node_label=self._node_label,
                                attrs=attrs,
                                ignore_naming=ignore_naming)
                    except ValueError as e:
                        q, carry_variables =\
                            rewriting.add_node(
                                n, n, 'new_id_' + n,
                                node_label=self._node_label,
                                ignore_naming=ignore_naming)
                else:
                    q, carry_variables =\
                        rewriting.add_node(
                            n, n, 'new_id_' + n,
                            node_label=self._node_label,
                            ignore_naming=ignore_naming)
                query += q + generic.with_vars(carry_variables)
            if len(carry_variables) > 0:
                query += generic.return_vars(carry_variables)
            result = self.execute(query)
            return result
        else:
            for n in nodes:
                if type(n) != str:
                    try:
                        n_id, attrs = n
                        self.add_node(n_id, attrs)
                    except ValueError:
                        self.add_node(n)
                else:
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
                        rewriting.add_edge(
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
                        rewriting.add_edge(
                            edge_var=u + "_" + v,
                            source_var=u,
                            target_var=v,
                            edge_label=self._edge_label))
            if len(edges) > 0:
                query += rewriting.match_nodes(
                    {n: n for n in nodes_to_match},
                    node_label=self._node_label)
                for q in edge_creation_queries:
                    query += q
                result = self.execute(query)
                return result
        else:
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
            generic.match_node("n", node, self._node_label) +
            rewriting.add_attributes("n", attrs)
        )
        result = self.execute(query)
        return result

    def set_node_attrs(self, node, attrs, update=False):
        """Set node attributes.

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
            generic.match_node("n", node, self._node_label) +
            generic.set_attributes("n", attrs, update)
        )
        result = self.execute(query)
        return result

    def set_node_attrs_from_json(self, node, attrs, update=False):
        """Set node attributes from json repr of attrs.

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
        return self.set_node_attrs(node, attrs_from_json(attrs), update)

    def remove_node_attrs(self, node, attrs):
        """Remove attributes from the node."""
        normalize_attrs(attrs)
        query = (
            generic.match_node(
                "n", node, self._node_label) +
            rewriting.remove_attributes("n", attrs)
        )
        result = self.execute(query)
        return result

    def add_edge_attrs(self, source, target, attrs):
        """Add attributes to the edge."""
        normalize_attrs(attrs)
        query = (
            generic.match_edge(
                "s", "t", source, target, "rel",
                self._node_label, self._node_label,
                self._edge_label) +
            rewriting.add_attributes("rel", attrs)
        )
        result = self.execute(query)
        return result

    def set_edge_attrs(self, source, target, attrs, update=False):
        """Set edge attributes.

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
            generic.match_edge(
                "s", "t", source, target, "rel",
                self._node_label, self._node_label,
                self._edge_label) +
            generic.set_attributes("rel", attrs, update)
        )
        result = self.execute(query)
        return result

    def set_edge_attrs_from_json(self, source, target, attrs, update=False):
        """Set edge attributes.

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
        return self.set_edge_attrs(source, target, attrs_from_json(attrs))

    def remove_edge_attrs(self, source, target, attrs):
        """Remove attributes from the edge."""
        normalize_attrs(attrs)
        query = (
            generic.match_edge(
                "s", "t", source, target, "rel",
                self._node_label, self._edge_label,
                self._edge_label) +
            rewriting.remove_attributes("rel", attrs)
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
            generic.match_node(
                "n", node,
                node_label=self._node_label) +\
            rewriting.remove_node("n")
        result = self.execute(query)
        return result

    def remove_edge(self, source, target, profiling=False):
        """Remove an edge from the graph db."""
        if profiling:
            query = "PROFILE\n"
        else:
            query = ""
        query +=\
            generic.match_edge(
                "s", "t", source, target, 'edge_var',
                self._node_label, self._node_label,
                edge_label='edge') +\
            rewriting.remove_edge('edge_var')
        result = self.execute(query)
        return result

    def nodes(self):
        """Return a list of nodes of the graph."""
        query = generic.get_nodes(node_label=self._node_label)
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        """Return the list of edges of the graph."""
        query = generic.get_edges(
            self._node_label,
            self._node_label,
            self._edge_label)
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]

    def get_node_attrs(self, node_id):
        """Return node's attributes."""
        query = generic.get_node_attrs(
            node_id, self._node_label,
            "attributes")
        result = self.execute(query)
        return generic.properties_to_attributes(
            result, "attributes")

    def get_node(self, node_id):
        """Call 'get_node_attrs'."""
        return self.get_node_attrs(node_id)

    def get_edge_attrs(self, s, t):
        """Return edge attributes."""
        query = generic.get_edge_attrs(
            s, t, self._edge_label,
            "attributes")
        result = self.execute(query)
        return generic.properties_to_attributes(
            result, "attributes")

    def get_edge(self, s, t):
        """Call 'get_edge_attrs'."""
        return self.get_edge_attrs(s, t)

    def exists_edge(self, s, t):
        """Test if an edge 's'->'t' exists."""
        query = generic.exists_edge(
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
            generic.match_node("n", node_id) +
            generic.set_node_attrs("n", attrs, update=False)
        )
        result = self.execute(query)
        return result

    def successors(self, node):
        """Return node's successors id."""
        query = generic.successors_query(
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
        query = generic.predecessors_query(
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
            generic.match_node(
                'x', node,
                node_label=self._node_label) +\
            rewriting.cloning_query(
                original_var='x',
                clone_var='new_node',
                clone_id=name,
                clone_id_var='uid',
                node_label=self._node_label,
                edge_labels=edge_labels,
                ignore_naming=ignore_naming)[0] +\
            generic.return_vars(['uid'])

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
            generic.match_nodes(
                {"n" + str(i + 1): n for i, n in enumerate(node_list)},
                node_label=self._node_label) + "\n" +\
            rewriting.merging_query(
                original_vars=["n" + str(i + 1) for i, _ in enumerate(node_list)],
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_label=self._node_label,
                edge_label=self._edge_label,
                ignore_naming=ignore_naming)[0] +\
            generic.return_vars(['new_id'])
        result = self.execute(query)
        uid_records = []
        for record in result:
            uid_records.append(record['new_id'])
        if len(uid_records) > 0:
            return uid_records[0]
        else:
            # This is a bad solution of the following problem:
            # if unwind in the merging query loops
            # over an empty list of edges, query does not return
            # any records
            return name

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
            generic.match_nodes(
                {n: n for n in node_list},
                node_label=self._node_label) + "\n" +\
            rewriting.merging_query1(
                original_vars=node_list,
                merged_var='merged_node',
                merged_id=name,
                merged_id_var='new_id',
                node_label=self._node_label,
                edge_label=self._edge_label,
                merge_typing=merge_typing,
                ignore_naming=ignore_naming)[0] +\
            generic.return_vars(['new_id'])
        result = self.execute(query)
        uid_records = []
        for record in result:
            uid_records.append(record['new_id'])
        if len(uid_records) > 0:
            return uid_records[0]

    def find_matching(self, pattern, nodes=None, pattern_typing=None):
        """Find matchings of a pattern in the graph."""
        if len(pattern.nodes()) != 0:
            query = rewriting.find_matching(
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
                    [p_g[p] for p in p_nodes])
                merged_nodes.add(rhs)
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
        query = generic.add_nodes_from_json(json_data, self._node_label)
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
            query = generic.load_graph_from_json(
                j_data, graph._node_label, graph._edge_label)
            graph.execute(query)
        else:
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

    def find_connected_components(self):
        query = (
            "CALL algo.unionFind.stream('{}', '{}', {{}})\n".format(
                self._node_label, self._edge_label) +
            "YIELD nodeId, setId\n"
            "MATCH (node) where id(node) = nodeId\n"
            "RETURN node.id as node, setId as component\n"
        )
        result = self.execute(query)
        cc = {}
        for record in result:
            if record["component"] in cc.keys():
                cc[record["component"]].append(record["node"])
            else:
                cc[record["component"]] = [record["node"]]
        return {
            i + 1: cc[k]
            for i, k in enumerate(cc.keys())
        }

