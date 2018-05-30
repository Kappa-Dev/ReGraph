"""Neo4j driver for regraph."""

from neo4j.v1 import GraphDatabase


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
