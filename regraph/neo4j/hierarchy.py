"""Neo4j driver for regraph."""

from neo4j.v1 import GraphDatabase

from regraph.neo4j.graphs import Neo4jGraph
import regraph.neo4j.cypher_utils as cypher
from regraph.neo4j.category_utils import (pullback,
                                          pushout,
                                          check_homomorphism)
from regraph.neo4j.rewriting_utils import (propagate_up,
                                           propagate_down,)


class Neo4jHierarchy(object):
    """Class implementing neo4j hierarchy driver."""

    def __init__(self, uri, user, password):
        """Initialize driver."""
        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))
        query = "CREATE " + cypher.constraint_query('n', 'hierarchyNode', 'id')
        self.execute(query)

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
        self.drop_all_constraints()
        return result

    def drop_all_constraints(self):
        """Drop all the constraints on the hierarchy."""
        with self._driver.session() as session:
            for constraint in session.run("CALL db.constraints"):
                session.run("DROP " + constraint[0])

    def add_graph(self, label):
        """Add a graph to the hierarchy."""
        # Create a node in the hierarchy...
        try:
            query = "CREATE (:{} {{id: '{}' }})".format('hierarchyNode', label)
            self.execute(query)
        except:  #ConstraintError
            raise ValueError(
                "The graph '{}' is already in the database.".format(label))
        Neo4jGraph(label, self, set_constraint=True)

    def remove_graph(self, label):
        """Remove a graph from the hierarchy."""
        g = self.access_graph(label)
        g.drop_constraint('id')
        g.clear()
        # Remove the hierarchyNode
        query = cypher.match_node(var_name="graph_to_rm",
                                  node_id=label,
                                  label='hierarchyNode')
        query += cypher.delete_nodes_var(["graph_to_rm"])
        self.execute(query)

    def access_graph(self, label):
        """Access a graph of the hierarchy."""
        query = "MATCH (n:hierarchyNode) WHERE n.id='{}' RETURN n".format(label)
        res = self.execute(query)
        if res.single() is None:
            raise ValueError(
                "The graph '{}' is not in the database.".format(label))
        g = Neo4jGraph(label, self)
        return g

    def add_typing(self, source, target, mapping=None, attrs=None):
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

        if mapping is not None:
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

        query2 = cypher.match_nodes(var_id_dict={'g_src':source, 'g_tar':target},
                                    label='hierarchyNode')
        query2 += cypher.create_edge(source_var='g_src',
                                     target_var='g_tar',
                                     edge_label='hierarchyEdge')
        result = self.execute(query2)
        return result

    def check_typing(self, source, target):
        """Check if a typing is a homomorphism."""
        g_src = self.access_graph(source)
        g_tar = self.access_graph(target)

        with self._driver.session() as session:
            tx = session.begin_transaction()
            res = check_homomorphism(tx, source, target)
            tx.commit()
        print(res)

    def pullback(self, b, c, d, a):
        self.add_graph(a)
        self.add_typing(a, b)
        self.add_typing(a, c)
        query1, query2 = pullback(b, c, d, a)
        print(query1)
        print('--------------------')
        print(query2)
        self.execute(query1)
        self.execute(query2)

    def pushout(self, a, b, c, d):
        self.add_graph(d)
        self.add_typing(b, d)
        self.add_typing(c, d)
        queries = pushout(a, b, c, d)
        for q in queries:
            print(q)
            print('--------------------')
            self.execute(q)

    def rewrite(self, graph_label, rule, instance):
        """Perform SqPO rewriting of the graph with a rule."""
        g = self.access_graph(graph_label)
        rhs_g = g.rewrite(rule, instance)
        return rhs_g

    def rewrite_v2(self, graph_label, rule, instance):
        """Perform SqPO rewriting of the graph with a rule."""
        g = self.access_graph(graph_label)
        maps_vars_ids = g.rule_to_cypher_v2(rule, instance)
        return (maps_vars_ids)

    def graph_successors(self, graph_label):
        """Get all the ids of the successors of a graph."""
        query = cypher.successors_query(var_name='g',
                                        node_id=graph_label,
                                        node_label='hierarchyNode',
                                        edge_label='hierarchyEdge')
        succ = self.execute(query).value()
        if succ[0] is None:
            succ = []
        return succ

    def graph_predecessors(self, graph_label):
        """Get all the ids of the predecessors of a graph."""
        query = cypher.predecessors_query(var_name='g',
                                          node_id=graph_label,
                                          node_label='hierarchyNode',
                                          edge_label='hierarchyEdge')
        preds = self.execute(query).value()
        if preds[0] is None:
            preds = []
        return preds

    def propagation_up(self, rewritten_graph):
        """Propagate the changes of a rewritten graph up."""
        predecessors = self.graph_predecessors(rewritten_graph)
        print("Rewritting ancestors of {}...".format(rewritten_graph))
        for predecessor in predecessors:
            print('--> ', predecessor)
            # run multiple queries in one transaction
            with self._driver.session() as session:
                tx = session.begin_transaction()
                propagate_up(tx, rewritten_graph, predecessor)
                tx.commit()
        for ancestor in predecessors:
            self.propagation_up(ancestor)

    def propagation_down(self, rewritten_graph):
        """Propagate the changes of a rewritten graph down."""
        successors = self.graph_successors(rewritten_graph)
        print("Rewritting children of {}...".format(rewritten_graph))
        for successor in successors:
            print('--> ', successor)
            # run multiple queries in one transaction
            with self._driver.session() as session:
                tx = session.begin_transaction()
                propagate_down(tx, rewritten_graph, successor)
                tx.commit()
        for successor in successors:
            self.propagation_down(successor)
