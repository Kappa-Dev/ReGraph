"""Neo4j driver for regraph."""

from neo4j.v1 import GraphDatabase

from regraph.neo4j.graphs import Neo4jGraph
import regraph.neo4j.cypher_utils as cypher


class Neo4jHierarchy(object):
    """Class implementing neo4j hierarchy driver."""

    def __init__(self, uri, user, password):
        """Initialize driver."""
        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))
        self._graphs = set()

    def close(self):
        """Close connection."""
        self._driver.close()

    def execute(self, query):
        """Execute a Cypher query."""
        with self._driver.session() as session:
            result = session.run(query)
            return result

    def clear(self):
        """Clear the hierarchy."""
        query = cypher.clear_graph()
        result = self.execute(query)
        self._graphs = set()
        return result

    def drop_all_constraints(self):
        """Drop all the constraints on the hierarchy."""
        with self._driver.session() as session:
            for constraint in session.run("CALL db.constraints"):
                session.run("DROP " + constraint[0])

    def add_graph(self, label):
        """Add a graph to the hierarchy."""
        if label in self._graphs:
            raise ValueError(
                "The graph '{}' is already in the database.".format(label))
        self._graphs.update([label])
        Neo4jGraph(label, self, set_constraint=True)
        # Create a node in the hierarchy...

    def remove_graph(self, label):
        """Remove a graph from the hierarchy."""
        if label not in self._graphs:
            raise ValueError(
                "The graph '{}' is not in the database.".format(label))
        g = self.access_graph(label)
        g.drop_constraint('id')
        g.clear()
        self._graphs.remove(label)

    def access_graph(self, label):
        """Access a graph of the hierarchy."""
        if label not in self._graphs:
            raise ValueError(
                "The graph '{}' is not in the database.".format(label))
        g = Neo4jGraph(label, self)
        return g

    def add_typing(self, source, target, mapping, attrs=None):
        """Add homomorphism to the hierarchy.

        Parameters
        ----------
        source
            Label of a source graph node of typing
        target
            Label of a target graph node of typing
        mapping : dict
            Dictionary representing a mapping of nodes ids
            from the source graph to target's nodes
        attrs : dict
            Dictionary containing attributes of the new
            typing edge
        """
        g_src = self.access_graph(source)
        g_tar = self.access_graph(target)

        query = ""
        nodes_to_match_src = set()
        nodes_to_match_tar = set()
        edge_creation_queries = []

        for u, v in mapping.items():
            nodes_to_match_src.add(u)
            nodes_to_match_tar.add(v)
            edge_creation_queries.append(
                cypher.create_edge(u+"_src", v+"_tar", edge_label='typing'))



        query += cypher.match_nodes({n+"_src": n for n in nodes_to_match_src},
                                    label=g_src._node_label)
        query += cypher.with_vars([s+"_src" for s in nodes_to_match_src])
        query += cypher.match_nodes({n+"_tar": n for n in nodes_to_match_tar},
                                    label=g_tar._node_label)
        for q in edge_creation_queries:
            query += q
        result = self.execute(query)
        return result



