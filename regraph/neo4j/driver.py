"""Neo4j driver for regraph."""
from neo4j.v1 import GraphDatabase

from regraph.neo4j.cypher_utils import (clear_graph,
                                        add_node,
                                        add_edge,
                                        add_nodes_from,
                                        add_edges_from,
                                        remove_node,
                                        remove_edge)


class Neo4jGraph(object):
    """Class implementing neo4j driver."""

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
        print(result)

    def add_nodes_from(self, nodes):
        query = add_nodes_from(nodes)
        result = self.execute(query)
        print(result)

    def add_edges_from(self, edges, attrs=None):
        query = add_edges_from(edges)
        result = self.execute(query)
        print(result)

    def add_node(self, node, attrs=None):
        query = add_node(node, attrs)
        result = self.execute(query)
        print(result)

    def add_edge(self, source, target, attrs=None):
        query = add_edge(source, target, attrs)
        result = self.execute(query)
        print(result)

    def remove_node(self, node):
        query = remove_node(node)
        result = self.execute(query)
        print(result)

    def remove_edge(self, source, target):
        query = remove_edge(source, target)
        result = self.execute(query)
        print(result)
