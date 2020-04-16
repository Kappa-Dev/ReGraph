"""Neo4j-based persisent graph objects.

This module implements data structures that allow working with persistent
graphs stored in an instance of the Neo4j database.
"""
import os
import json
import warnings

from neo4j.v1 import GraphDatabase

from regraph.graphs import Graph
from regraph.utils import (normalize_attrs,
                           load_nodes_from_json,
                           load_edges_from_json,)
from regraph.exceptions import ReGraphError
from .cypher_utils import generic
from .cypher_utils import rewriting


class Neo4jGraph(Graph):
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
                self._set_constraint('id')
            except:
                warnings.warn(
                    "Failed to create id uniqueness constraint")

    def _execute(self, query):
        """Execute a Cypher query."""
        with self._driver.session() as session:
            if len(query) > 0:
                result = session.run(query)
                return result

    def _close(self):
        """Close connection to the database."""
        self._driver.close()

    def _clear(self):
        """Clear graph database.

        Returns
        -------
        result : BoltStatementResult
        """
        query = generic.clear_graph(self._node_label)
        result = self._execute(query)
        return result

    def _set_constraint(self, prop):
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
        result = self._execute(query)
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

    def nodes(self, data=False):
        """Return a list of nodes of the graph."""
        query = generic.get_nodes(node_label=self._node_label, data=data)
        result = self._execute(query)

        node_list = []
        for d in result:
            node_id = d["node_id"]
            if data:
                attrs = d["attrs"]
                del attrs["id"]
                normalize_attrs(attrs)
                node_list.append((node_id, attrs))
            else:
                node_list.append(node_id)
        return node_list

    def edges(self, data=False):
        """Return the list of edges of the graph."""
        query = generic.get_edges(
            self._node_label,
            self._node_label,
            self._edge_label,
            data=data)
        result = self._execute(query)
        edges = []

        for d in result:
            if d["source_id"] not in self.nodes():
                s = int(d["source_id"])
            else:
                s = d["source_id"]
            if d["target_id"] not in self.nodes():
                t = int(d["target_id"])
            else:
                t = d["target_id"]
            if data:
                normalize_attrs(d["attrs"])
                edges.append((s, t, d["attrs"]))
            else:
                edges.append((s, t))

        return edges

    def get_node(self, node_id):
        """Get node attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph or regraph.neo4j.Neo4jGraph
        node_id : hashable, node id.
        """
        query = generic.get_node_attrs(
            node_id, self._node_label,
            "attributes")
        result = self._execute(query)
        attrs = generic.properties_to_attributes(
            result, "attributes")
        return attrs

    def get_edge(self, s, t):
        """Get edge attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        query = generic.get_edge_attrs(
            s, t,
            self._node_label,
            self._edge_label,
            "attributes")
        result = self._execute(query)
        return generic.properties_to_attributes(
            result, "attributes")

    def add_node(self, node, attrs=None, ignore_naming=False):
        """Abstract method for adding a node.

        Parameters
        ----------
        node : hashable
            Prefix that is prepended to the new unique name.
        attrs : dict, optional
            Node attributes.
        """
        if attrs is None:
            attrs = dict()
        normalize_attrs(attrs)
        query =\
            rewriting.add_node(
                "n", node, 'new_id',
                node_label=self._node_label,
                attrs=attrs,
                literal_id=True,
                ignore_naming=ignore_naming)[0] +\
            generic.return_vars(['new_id'])

        result = self._execute(query)
        new_id = result.single()['new_id']
        return new_id

    def remove_node(self, node):
        """Remove node.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node_id : hashable, node to remove.
        """
        query =\
            generic.match_node(
                "n", node,
                node_label=self._node_label) +\
            rewriting.remove_node("n")
        result = self._execute(query)
        return result

    def add_edge(self, s, t, attrs=None, **attr):
        """Add an edge to a graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dict
            Edge attributes.
        """
        if attrs is None:
            attrs = dict()
        normalize_attrs(attrs)
        query = generic.match_nodes(
            {"s": s, "t": t},
            node_label=self._node_label)
        query += rewriting.add_edge(
            edge_var='new_edge',
            source_var="s",
            target_var="t",
            edge_label=self._edge_label,
            attrs=attrs)
        result = self._execute(query)
        return result

    def remove_edge(self, s, t):
        """Remove edge from the graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        query =\
            generic.match_edge(
                "s", "t", s, t, 'edge_var',
                self._node_label, self._node_label,
                edge_label='edge') +\
            rewriting.remove_edge('edge_var')
        result = self._execute(query)
        return result

    def update_node_attrs(self, node_id, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        node_id : hashable, node to update.
        attrs : dict
            New attributes to assign to the node

        """
        normalize_attrs(attrs)
        query = (
            generic.match_node("n", node_id, self._node_label) +
            generic.set_attributes("n", attrs, update=True)
        )
        result = self._execute(query)
        return result

    def update_edge_attrs(self, s, t, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        s : hashable, source node of the edge to update.
        t : hashable, target node of the edge to update.
        attrs : dict
            New attributes to assign to the node

        """
        normalize_attrs(attrs)
        query = (
            generic.match_edge(
                "s", "t", s, t, "rel",
                self._node_label, self._node_label,
                self._edge_label) +
            generic.set_attributes("rel", attrs, update=True)
        )
        result = self._execute(query)
        return result

    def successors(self, node_id):
        """Return the set of successors."""
        query = generic.successors_query(
            node_id, node_id,
            node_label=self._node_label,
            edge_label=self._edge_label)
        result = self._execute(query)
        succ = set()
        for record in result:
            if record["suc"] is not None:
                succ.add(record["suc"])
        return succ

    def predecessors(self, node_id):
        """Return the set of predecessors."""
        query = generic.predecessors_query(
            node_id, node_id,
            node_label=self._node_label,
            edge_label=self._edge_label)
        result = self._execute(query)
        pred = set()
        for record in result:
            if record["pred"] is not None:
                pred.add(record["pred"])
        return pred

    def find_matching(self, pattern, nodes=None,
                      graph_typing=None, pattern_typing=None):
        """Find matching of a pattern in a graph."""
        if len(pattern.nodes()) != 0:

            # filter nodes by typing
            matching_nodes = set()
            for pattern_node in pattern.nodes():
                for node in self.nodes():
                    type_matches = True
                    if pattern_typing:
                        # check types match
                        for graph, pattern_mapping in pattern_typing.items():
                            if node in graph_typing[graph].keys() and\
                               pattern_node in pattern_mapping.keys():
                                if graph_typing[graph][node] != pattern_mapping[
                                        pattern_node]:
                                    type_matches = False
                    if type_matches and nodes and node in nodes:
                        matching_nodes.add(node)

            query = rewriting.find_matching(
                pattern,
                node_label=self._node_label,
                edge_label=self._edge_label,
                nodes=matching_nodes,
                pattern_typing=pattern_typing)

            result = self._execute(query)
            instances = list()

            for record in result:
                instance = dict()
                for k, v in record.items():
                    instance[k] = dict(v)["id"]

                new_instance = dict()
                for pattern_node, v in instance.items():
                    if pattern_node not in pattern.nodes():
                        new_instance[int(pattern_node)] = v
                    else:
                        new_instance[pattern_node] = v

                instances.append(new_instance)
        else:
            instances = []
        return instances

    def relabel_node(self, node_id, new_id):
        """Relabel a node in the graph.

        Parameters
        ----------
        node_id : hashable
            Id of the node to relabel.
        new_id : hashable
            New label of a node.
        """
        if new_id in self.nodes():
            raise ReGraphError(
                "Cannot relabel '{}' to '{}', '{}' ".format(
                    node_id, new_id, new_id) +
                "already exists in the graph")
        query = generic.set_id(self._node_label, node_id, new_id)
        result = self._execute(query)
        return result

    @classmethod
    def from_json(cls, driver=None, uri=None, user=None, password=None,
                  json_data=None, node_label="node", edge_label="edge"):
        """Create a Neo4jGraph from a json-like dictionary.

        Parameters
        ----------
        json_data : dict
            JSON-like dictionary with graph representation
        """
        graph = cls(
            driver=driver, uri=uri, user=user, password=password,
            node_label=node_label, edge_label=edge_label)
        graph.add_nodes_from(load_nodes_from_json(json_data))
        graph.add_edges_from(load_edges_from_json(json_data))
        return graph

    @classmethod
    def load(cls, driver=None, uri=None, user=None, password=None,
             filename=None, node_label="node", edge_label="edge"):
        """Load a Neo4jGraph from a JSON file.

        Create a graph object from
        a JSON representation stored in a file.

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
        filename : str, optional
            Name of the file to load the json serialization of the graph
        node_label : optional
            Label of nodes inducing the subgraph to scope.
            By default `"node"`.
        edge_label : optional
            Type of relations inducing the subgraph to scope.
            By default `"edge"`.

        Returns
        -------
        Graph object

        Raises
        ------
        ReGraphError
            If was not able to load the file

        """
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                j_data = json.loads(f.read())
                return cls.from_json(
                    driver=driver, uri=uri, user=user, password=password,
                    json_data=j_data, node_label=node_label, edge_label=edge_label)
        else:
            raise ReGraphError(
                "Error loading graph: file '{}' does not exist!".format(
                    filename)
            )

    def nodes_disconnected_from(self, node_id):
        """Find nodes disconnected from the input node."""
        query = (
            "MATCH (n:{} {{id: '{}'}}), (m:{})\n".format(
                self._node_label, node_id, self._node_label) +
            "WHERE NOT (n)-[:{}*1..]-(m) AND n.id <> m.id\n".format(
                self._edge_label) +
            "RETURN collect(m.id) as disconnected_nodes"
        )
        res = self._execute(query)
        for record in res:
            return record["disconnected_nodes"]
