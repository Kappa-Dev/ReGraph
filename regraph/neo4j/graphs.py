"""Neo4j driver for regraph."""
from neo4j.v1 import GraphDatabase

from regraph.neo4j.cypher_utils import (clear_graph,
                                        add_node,
                                        add_edge,
                                        add_nodes_from,
                                        add_edges_from,
                                        remove_node,
                                        remove_edge,
                                        nodes,
                                        edges)


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

    def add_nodes_from(self, nodes):
        """Add nodes to the graph db."""
        query = add_nodes_from(nodes)
        result = self.execute(query)
        print(result)

    def add_edges_from(self, edges, attrs=None):
        """Add edges to the graph db."""
        query = add_edges_from(edges)
        result = self.execute(query)
        print(result)

    def add_node(self, node, attrs=None):
        """Add a node to the graph db."""
        query = add_node(node, attrs)
        result = self.execute(query)
        print(result)

    def add_edge(self, source, target, attrs=None):
        """Add an edge to the graph db."""
        query = add_edge(source, target, attrs)
        result = self.execute(query)
        print(result)

    def remove_node(self, node):
        """Remove a node from the graph db."""
        query = remove_node(node)
        result = self.execute(query)
        print(result)

    def remove_edge(self, source, target):
        """Remove an edge from the graph db."""
        query = remove_edge(source, target)
        result = self.execute(query)
        print(result)

    def nodes(self):
        query = nodes()
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        query = edges()
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]