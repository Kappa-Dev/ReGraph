"""Neo4j driver for regraph."""

from neo4j.v1 import GraphDatabase
from neo4j.exceptions import ConstraintError

from regraph.neo4j.graphs import Neo4jGraph
import regraph.neo4j.cypher_utils as cypher
from regraph.neo4j.category_utils import (pullback,
                                          pushout,
                                          _check_homomorphism,
                                          _check_consistency,
                                          _check_rhs_consistency)
from regraph.neo4j.rewriting_utils import (propagate_up,
                                           propagate_down,
                                           preserve_tmp_typing,
                                           remove_tmp_typing)
from regraph.default.exceptions import (HierarchyError,
                                        InvalidHomomorphism)
from regraph.default.utils import normalize_attrs


class Neo4jHierarchy(object):
    """Class implementing neo4j hierarchy driver."""

    def __init__(self, uri, user, password):
        """Initialize driver."""
        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))
        query = "CREATE " + cypher.constraint_query(
            'n', ['hierarchyNode'], 'id')
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
        # self.drop_all_constraints()
        return result

    def drop_all_constraints(self):
        """Drop all the constraints on the hierarchy."""
        with self._driver.session() as session:
            for constraint in session.run("CALL db.constraints"):
                session.run("DROP " + constraint[0])

    def add_graph(self, graph_id, node_list=None, edge_list=None, graph_attrs=None):
        """Add a graph to the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        node_list : iterable
            Iterable containing a collection of nodes, optionally,
            with their attributes
        edge_list : iterable
            Iterable containing a collection of edges, optionally,
            with their attributes
        graph_attrs : dict
            Dictionary containing attributes of the new graph

        Raises
        ------
        HierarchyError
            If graph with provided id already exists in the hierarchy

        """
        try:
            # Create a node in the hierarchy
            query = "CREATE ({}:{} {{ id : '{}' }}) \n".format(
                'new_graph',
                'hierarchyNode',
                graph_id)
            if graph_attrs is not None:
                query += cypher.set_attributes(
                    var_name='new_graph',
                    attrs=graph_attrs)
            self.execute(query)
        except(ConstraintError):
            raise HierarchyError(
                "The graph '{}' is already in the database.".format(graph_id))
        g = Neo4jGraph(
            driver=self._driver,
            node_labels=[graph_id],
            unique_node_ids=True)
        if node_list is not None:
            g.add_nodes_from(node_list)
        if edge_list is not None:
            g.add_edges_from(edge_list)

    def remove_graph(self, graph_id, reconnect=False):
        """Remove a graph from the hierarchy.

        Parameters
        ----------
        node_id
            Id of the graph to remove
        reconnect : bool
            Reconnect the descendants of the removed graph to
            its predecessors

        Raises
        ------
        HierarchyError
            If graph with `graph_id` is not defined in the hierarchy
        """
        g = self.access_graph(graph_id)

        if reconnect:
            query = (
                "MATCH (n:node:{})".format(graph_id) +
                "OPTIONAL MATCH (pred)-[:typing]->(n)-[:typing]->(suc)\n" +
                "WITH pred, suc WHERE pred IS NOT NULL\n" +
                cypher.create_edge(
                    edge_var='recennect_typing',
                    source_var='pred',
                    target_var='suc',
                    edge_labels=['typing'])
            )
            self.execute(query)
        # Clear the graph and drop the constraint on the ids
        g.drop_constraint('id')
        g.clear()

        # Remove the hierarchyNode (and reconnect if True)
        if reconnect:
            query = (
                cypher.match_node(
                    var_name="graph_to_rm",
                    node_id=graph_id,
                    node_labels=['hierarchyNode']) +
                "OPTIONAL MATCH (pred)-[:hierarchyEdge]->(n)-[:hierarchyEdge]->(suc)\n" +
                "WITH pred, suc WHERE pred IS NOT NULL\n" +
                cypher.create_edge(
                    edge_var='recennect_typing',
                    source_var='pred',
                    target_var='suc',
                    edge_labels=['hierarchyEdge'])
            )
            self.execute(query)
        query = cypher.match_node(var_name="graph_to_rm",
                                  node_id=graph_id,
                                  node_label=['hierarchyNode'])
        query += cypher.delete_nodes_var(["graph_to_rm"])
        self.execute(query)

    def access_graph(self, label):
        """Access a graph of the hierarchy."""
        query = "MATCH (n:hierarchyNode) WHERE n.id='{}' RETURN n".format(
            label)
        res = self.execute(query)
        if res.single() is None:
            raise HierarchyError(
                "The graph '{}' is not in the database.".format(label))
        g = Neo4jGraph(self._driver,
                       node_labels=[label], edge_labels=["edge"])
        return g

    def add_typing(self, source, target, mapping, attrs=None, check=True):
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

        Raises
        ------
        HierarchyError
            This error is raised in the following cases:

                * source or target ids are not found in the hierarchy
                * addition of an edge between source and target produces
                paths that do not commute with some already existing paths

        InvalidHomomorphism
            If a homomorphism from a graph at the source to a graph at
            the target given by `mapping` is not a valid homomorphism.
        """
        g_src = self.access_graph(source)
        g_tar = self.access_graph(target)

        query = ""
        nodes_to_match_src = set()
        nodes_to_match_tar = set()
        edge_creation_queries = []
        tmp_attrs = {'tmp': {'true'}}
        normalize_attrs(tmp_attrs)
        for u, v in mapping.items():
            nodes_to_match_src.add(u)
            nodes_to_match_tar.add(v)
            edge_creation_queries.append(
                cypher.create_edge(
                    edge_var="typ_" + u + "_" + v,
                    source_var=u + "_src",
                    target_var=v + "_tar",
                    edge_labels=['typing'],
                    attrs=tmp_attrs))

        query += cypher.match_nodes(
            {n + "_src": n for n in nodes_to_match_src},
            node_labels=g_src._node_labels)
        query += cypher.with_vars([s + "_src" for s in nodes_to_match_src])
        query += cypher.match_nodes(
            {n + "_tar": n for n in nodes_to_match_tar},
            node_labels=g_tar._node_labels)
        for q in edge_creation_queries:
            query += q

        result = self.execute(query)

        valid_typing = True
        paths_commute = True
        if check:
            # We first check that the homorphism is valid
            try:
                with self._driver.session() as session:
                    tx = session.begin_transaction()
                    valid_typing = _check_homomorphism(tx, source, target)
                    tx.commit()
            except InvalidHomomorphism as homomorphism_error:
                valid_typing = False
                del_query = (
                    "MATCH (:node:{})-[t:typing]-(:node:{})\n".format(
                        source, target) +
                    "DELETE t\n"
                )
                self.execute(del_query)
                raise homomorphism_error
            # We then check that the new typing preserv consistency
            try:
                with self._driver.session() as session:
                    tx = session.begin_transaction()
                    paths_commute = _check_consistency(tx, source, target)
                    tx.commit()
            except InvalidHomomorphism as consistency_error:
                paths_commute = False
                del_query = (
                    "MATCH (:node:{})-[t:typing]-(:node:{})\n".format(
                        source, target) +
                    "DELETE t\n"
                )
                self.execute(del_query)
                raise consistency_error

        if valid_typing and paths_commute:
            query2 = (
                cypher.match_nodes(
                    var_id_dict={'g_src': source, 'g_tar': target},
                    node_labels=['hierarchyNode']) +
                cypher.create_edge(
                    edge_var='new_hierarchy_edge',
                    source_var='g_src',
                    target_var='g_tar',
                    edge_labels=['hierarchyEdge'],
                    attrs=attrs) +
                cypher.with_vars(["new_hierarchy_edge"]) +
                "MATCH (:node:{})-[t:typing]-(:node:{})\n".format(
                    source, target) +
                "REMOVE t.tmp\n"

            )
            self.execute(query2)
        return result

    def check_typing(self, source, target):
        """Check if a typing is a homomorphism."""
        g_src = self.access_graph(source)
        g_tar = self.access_graph(target)

        with self._driver.session() as session:
            tx = session.begin_transaction()
            res = _check_homomorphism(tx, source, target)
            tx.commit()
        print(res)

    def pullback(self, b, c, d, a):
        self.add_graph(a)
        query1, query2 = pullback(b, c, d, a)
        self.execute(query1)
        self.execute(query2)

    def pushout(self, a, b, c, d):
        self.add_graph(d)
        queries = pushout(a, b, c, d)
        for q in queries:
            print(q)
            print('--------------------')
            self.execute(q)

    def rewrite(self, graph_id, rule, instance, rhs_typing=None):
        """Rewrite and propagate the changes up & down.

        Rewriting in the hierarchy cosists of an application of the
        SqPO-rewriting rule (given by the `rule` parameter) to a
        graph in the hierarchy. Such rewriting often triggers a set of
        changes that are applied to other graphs and homomorphisms in the
        hierarchy, which are necessary to ensure that the hierarchy stays
        consistent. If the rule is restrictive (deletes nodes/edges/attrs
        or clones nodes), in general, the respective changes to all the graphs
        (transitively) typed by the graph subject to rewriting are made.
        On the other hand, if the rule is relaxing (adds nodes/edges/attrs
        or merges nodes), in general, the respective changes to all the graphs
        that (tansitively) type the graph subject to rewriting are made.


        Parameters
        ----------
        graph_id
            Id of the graph in the hierarchy to rewrite
        rule : regraph.rule.Rule
            Rule object to apply
        instance : dict, optional
            Dictionary containing an instance of the lhs of the rule in
            the graph subject to rewriting, by default, tries to construct
            identity morphism of the nodes of the pattern
        rhs_typing : dict, optional
            Dictionary containing typing of the rhs by graphs of the hierarchy,
            keys are ids of hierarchy graphs, values are dictionaries
            containing the mapping of nodes from the lhs to the nodes of
            the typing graph given by the respective key of the value
            (note that a node from the rhs can be typed by a set of nodes of
            some graph, e.g. if we want to perform merging of some types, etc).

        Raises
        ------
        HierarchyError
            If the graph is not in the database
        TypingWarning
            If the rhs typing is inconsistent
        """
        # Rewriting of the base graph
        g = self.access_graph(graph_id)
        rhs_g = g.rewrite(rule, instance, rhs_typing)

        # Checking if the rhs typing is consistent
        with self._driver.session() as session:
            tx = session.begin_transaction()
            consistent_typing = _check_rhs_consistency(tx, graph_id)
            tx.commit()

        if consistent_typing:
            self.execute(preserve_tmp_typing(graph_id))
        else:
            self.execute(remove_tmp_typing(graph_id))

        # Propagate the changes up and down
        self._propagation_up(graph_id)
        self._propagation_down(graph_id)
        return rhs_g

    def successors(self, graph_label):
        """Get all the ids of the successors of a graph."""
        query = cypher.successors_query(var_name='g',
                                        node_id=graph_label,
                                        node_labels=['hierarchyNode'],
                                        edge_labels=['hierarchyEdge'])
        succ = self.execute(query).value()
        if succ[0] is None:
            succ = []
        return succ

    def predecessors(self, graph_label):
        """Get all the ids of the predecessors of a graph."""
        query = cypher.predecessors_query(var_name='g',
                                          node_id=graph_label,
                                          node_labels=['hierarchyNode'],
                                          edge_labels=['hierarchyEdge'])
        preds = self.execute(query).value()
        if preds[0] is None:
            preds = []
        return preds

    def _propagation_up(self, rewritten_graph):
        """Propagate the changes of a rewritten graph up."""
        predecessors = self.predecessors(rewritten_graph)
        print("Rewritting ancestors of {}...".format(rewritten_graph))
        for predecessor in predecessors:
            print('--> ', predecessor)
            q_clone, q_rm_node, q_rm_edge = propagate_up(
                rewritten_graph,
                predecessor)
            # run multiple queries in one transaction
            with self._driver.session() as session:
                tx = session.begin_transaction()
                tx.run(q_clone)
                tx.run(q_rm_node)
                tx.run(q_rm_edge)
                tx.commit()
        for ancestor in predecessors:
            self._propagation_up(ancestor)

    # def _propagation_up_v2(self, rewritten_graph):
    #     """Propagate the changes of a rewritten graph up."""
    #     predecessors = self.predecessors(rewritten_graph)
    #     print("Rewritting ancestors of {}...".format(rewritten_graph))
    #     for predecessor in predecessors:
    #         print('--> ', predecessor)
    #         # run multiple queries in one transaction
    #         with self._driver.session() as session:
    #             tx = session.begin_transaction()
    #             query = propagate_up_v2(rewritten_graph, predecessor)
    #             tx.run(query)
    #             tx.commit()
    #     for ancestor in predecessors:
    #         self._propagation_up(ancestor)

    def _propagation_down(self, rewritten_graph):
        successors = self.successors(rewritten_graph)
        print("Rewritting children of {}...".format(rewritten_graph))
        for successor in successors:
            print('--> ', successor)
            q_merge_node, q_add_node, q_add_edge = propagate_down(
                rewritten_graph,
                successor)
            # run multiple queries in one transaction
            with self._driver.session() as session:
                tx = session.begin_transaction()
                tx.run(q_merge_node).single()
                tx.run(q_add_node).single()
                tx.run(q_add_edge).single()
                tx.commit()
        for successor in successors:
            self._propagation_down(successor)

    # def _propagation_down_v2(self, rewritten_graph, changes):
    #     successors = self.successors(rewritten_graph)
    #     print("Rewritting children of {}...".format(rewritten_graph))
    #     for successor in successors:
    #         print('--> ', successor)
    #         # run multiple queries in one transaction
    #         with self._driver.session() as session:
    #             tx = session.begin_transaction()
    #             query = propagate_down_v2(rewritten_graph, successor)
    #             tx.run(query, added_edges_list=changes['added_edges'])
    #             tx.commit()
