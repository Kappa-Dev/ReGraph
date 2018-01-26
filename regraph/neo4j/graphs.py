"""Neo4j driver for regraph."""
from neo4j.v1 import GraphDatabase

from regraph.neo4j.cypher_utils import (clear_graph,
                                        add_node,
                                        add_edge,
                                        add_nodes_from,
                                        add_edges_from,
                                        remove_node,
                                        remove_edge,
                                        get_nodes,
                                        get_edges,
                                        clone_node,
                                        merge_nodes,
                                        find_matching)


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
        query = get_nodes()
        result = self.execute(query)
        return [list(d.values())[0] for d in result]

    def edges(self):
        query = get_edges()
        result = self.execute(query)
        return [(d["n.id"], d["m.id"]) for d in result]

    def clone_node(self, node, name=None):
        result = self.execute(clone_node(node, name))
        return result.single().value()

    def merge_nodes(self, node_list, name=None):
        result = self.execute(merge_nodes(node_list, name))
        return result.single().value()

    def find_matching(self, pattern, nodes=None):
        result = self.execute(find_matching(pattern, nodes))
        instances = list()

        for record in result:
            instance = dict()
            for k, v in record.items():
                instance[k] = v.properties["id"]
            instances.append(instance)
        return instances