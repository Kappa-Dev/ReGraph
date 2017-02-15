"""."""
import networkx as nx
# import copy

from regraph.library.utils import (compose_homomorphisms,
                                   check_homomorphism)


class Hierarchy(nx.DiGraph):
    """."""

    def __init__(self, directed=True):
        nx.DiGraph.__init__(self)
        self.hierarchy_attrs = dict()
        self.directed = directed
        return

    def __str__(self):
        res = ""
        res += "\nGraphs (directed == %s): \n" % self.directed
        for n in self.nodes():
            res += str(n) + " "
        res += "\n"
        res += "Homomorphisms : \n"
        for n1, n2 in self.edges():
            res += "%s -> %s: ignore_attrs == %s,\n" %\
                (n1, n2, self.edge[n1][n2][1])
            res += "mapping: %s\n" % str(self.edge[n1][n2][0])

        res += "\n"
        res += "attributes : \n"
        res += str(self.hierarchy_attrs)
        res += "\n"

        return res

    def add_graph(self, graph_id, graph):
        """Add graph to the hierarchy."""
        if self.directed != graph.is_directed():
            if self.directed:
                raise ValueError("Hierarchy is defined for directed graphs!")
            else:
                raise ValueError("Hierarchy is defined for undirected graphs!")
        if graph_id in self.nodes():
            raise ValueError("Graph '%s' already exists in the hierarchy!")
        self.add_node(graph_id)
        self.node[graph_id] = graph
        return

    def add_homomorphism(self, source, target, mapping, ignore_attrs=False):
        """Add homomorphism to the hierarchy."""
        if source not in self.nodes():
            raise ValueError(
                "Graph '%s' is not defined in the hierarchy!" % source)
        if target not in self.nodes():
            raise ValueError(
                "Graph '%s' is not defined in the hierarchy!" % target)

        # check no cycles are produced
        self.add_edge(source, target)
        if not nx.is_directed_acyclic_graph(self):
            self.remove_edge(source, target)
            raise ValueError(
                "Edge '%s->%s' creates a cycle in the hierarchy!" % (source, target)
            )
        self.remove_edge(source, target)

        # check if the homomorphism is valid
        check_homomorphism(
            self.node[source],
            self.node[target],
            mapping,
            ignore_attrs
        )

        self.add_edge(source, target)
        self.edge[source][target] = (mapping, ignore_attrs)
        return

    def remove_graph(self, graph_id, reconnect=False):
        """Remove graph from the hierarchy.

        If `reconnect`, map the children homomorphisms
        of this graph to its parents.
        """
        if graph_id not in self.nodes():
            raise ValueError(
                "Graph `%s` is not defined in the hierarchy!" % graph_id)

        if reconnect:
            out_graphs = self.successors(graph_id)
            in_graphs = self.predecessors(graph_id)

            for source in in_graphs:
                for target in out_graphs:

                    # compose two homomorphisms
                    mapping = compose_homomorphisms(
                        self.edge[source][graph_id][0],
                        self.edge[graph_id][target][0]
                    )

                    if (source, target) not in self.edges():
                        self.add_homomorphism(
                            source,
                            target,
                            mapping,
                            self.edge[source][graph_id][1] or self.edge[graph_id][target][1]
                        )

        self.remove_node(graph_id)

    def find_matching(self, graph_id, rule):
        """."""
        pass

    def rewrite(self, graph_id, instance, rule):
        """."""
        pass
