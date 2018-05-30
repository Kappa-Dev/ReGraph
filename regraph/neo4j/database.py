"""Neo4j driver for regraph."""

from neo4j.v1 import GraphDatabase

from regraph.neo4j.graph import Neo4jGraph


class Neo4jDatabase(object):
    """Class implementing neo4j graph db driver."""

    def __init__(self, uri, user, password):
        """Initialize driver."""
        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))
        self._graphs = set()

    def close(self):
        """Close connection."""
        self._driver.close()

    def access_graph(self, label):
        """Add a graph to the database."""
        if label in self._graphs:
            g = Neo4jGraph(label, self)
        else:
            self._graphs.update(label)
            g = Neo4jGraph(label, self, set_constraint=True)
            # Create a node in the hierarchy...
        return g
