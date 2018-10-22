"""Neo4j driver for regraph."""
import networkx as nx

from neo4j.v1 import GraphDatabase
from neo4j.exceptions import ConstraintError

from regraph.neo4j.graphs import Neo4jGraph
import regraph.neo4j.cypher_utils as cypher
from regraph.neo4j.category_utils import (_check_homomorphism,
                                          _check_consistency,
                                          _check_rhs_consistency)
import regraph.neo4j.propagation_utils as propagation
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
            'n', 'hierarchyNode', 'id')
        self.execute(query)

    def close(self):
        """Close connection to the database."""
        self._driver.close()

    def execute(self, query):
        """Execute a Cypher query."""
        with self._driver.session() as session:
            if len(query) > 0:
                result = session.run(query)
                return result

    def _clear(self):
        """Clear the hierarchy."""
        query = cypher.clear_graph()
        result = self.execute(query)
        # self.drop_all_constraints()
        return result

    def _drop_all_constraints(self):
        """Drop all the constraints on the hierarchy."""
        with self._driver.session() as session:
            for constraint in session.run("CALL db.constraints"):
                session.run("DROP " + constraint[0])

    def graphs(self):
        """Return a list of graphs in the hierarchy."""
        pass

    def typings(self):
        """Return a list of graph typing edges in the hierarchy."""
        pass

    # def rules(self):
    #     """Return a list of rules in the hierary."""
    #     pass

    # def relations(self):
    #     """Return a list of relations."""
    #     pass

    def add_graph(self, graph_id, node_list=None, edge_list=None,
                  graph_attrs=None):
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
            node_label=graph_id,
            unique_node_ids=True)
        if node_list is not None:
            g.add_nodes_from(node_list)
        if edge_list is not None:
            g.add_edges_from(edge_list)

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
        g_src = self._access_graph(source)
        g_tar = self._access_graph(target)

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
                    edge_label='typing',
                    attrs=tmp_attrs))

        if len(nodes_to_match_src) > 0:
            query += cypher.match_nodes(
                {n + "_src": n for n in nodes_to_match_src},
                node_label=g_src._node_label)
            query += cypher.with_vars([s + "_src" for s in nodes_to_match_src])
            query += cypher.match_nodes(
                {n + "_tar": n for n in nodes_to_match_tar},
                node_label=g_tar._node_label)
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
            skeleton_query = (
                cypher.match_nodes(
                    var_id_dict={'g_src': source, 'g_tar': target},
                    node_label='hierarchyNode') +
                cypher.create_edge(
                    edge_var='new_hierarchy_edge',
                    source_var='g_src',
                    target_var='g_tar',
                    edge_label='hierarchyEdge',
                    attrs=attrs) +
                cypher.with_vars(["new_hierarchy_edge"]) +
                "MATCH (:node:{})-[t:typing]-(:node:{})\n".format(
                    source, target) +
                "REMOVE t.tmp\n"

            )
            self.execute(skeleton_query)
        return result

    def remove_node(self, node_id, reconnect=False):
        """Remove node from the hierarchy.

        Removes a node from the hierarchy, if the `reconnect`
        parameter is set to True, adds typing from the
        predecessors of the removed node to all its successors,
        by composing the homomorphisms (for every predecessor `p`
        and for every successor 's' composes two homomorphisms
        `p`->`node_id` and `node_id`->`s`, then removes `node_id` and
        all its incident edges, by which makes node's
        removal a procedure of 'forgetting' one level
        of 'abstraction').

        Parameters
        ----------
        node_id
            Id of a node to remove
        reconnect : bool
            Reconnect the descendants of the removed node to
            its predecessors

        Raises
        ------
        HierarchyError
            If node with `node_id` is not defined in the hierarchy
        """
        g = self._access_graph(node_id)

        if reconnect:
            query = (
                "MATCH (n:node:{})".format(node_id) +
                "OPTIONAL MATCH (pred)-[:typing]->(n)-[:typing]->(suc)\n" +
                "WITH pred, suc WHERE pred IS NOT NULL\n" +
                cypher.create_edge(
                    edge_var='recennect_typing',
                    source_var='pred',
                    target_var='suc',
                    edge_label='typing')
            )
            self.execute(query)
        # Clear the graph and drop the constraint on the ids
        g._drop_constraint('id')
        g._clear()

        # Remove the hierarchyNode (and reconnect if True)
        if reconnect:
            query = (
                cypher.match_node(
                    var_name="graph_to_rm",
                    node_id=node_id,
                    node_label='hierarchyNode') +
                "OPTIONAL MATCH (pred)-[:hierarchyEdge]->(n)-[:hierarchyEdge]->(suc)\n" +
                "WITH pred, suc WHERE pred IS NOT NULL\n" +
                cypher.create_edge(
                    edge_var='recennect_typing',
                    source_var='pred',
                    target_var='suc',
                    edge_label='hierarchyEdge')
            )
            self.execute(query)
        query = cypher.match_node(var_name="graph_to_rm",
                                  node_id=node_id,
                                  node_label='hierarchyNode')
        query += cypher.delete_nodes_var(["graph_to_rm"])
        self.execute(query)

    def remove_edge(self, u, v):
        """Remove an edge from the hierarchy."""
        pass

    def _access_graph(self, graph_id):
        """Access a graph of the hierarchy."""
        query = "MATCH (n:hierarchyNode) WHERE n.id='{}' RETURN n".format(
            graph_id)
        res = self.execute(query)
        if res.single() is None:
            raise HierarchyError(
                "The graph '{}' is not in the database.".format(graph_id))
        g = Neo4jGraph(self._driver,
                       node_label=graph_id, edge_label="edge")
        return g

    def _check_typing(self, source, target):
        """Check if a typing is a valid homomorphism."""
        with self._driver.session() as session:
            tx = session.begin_transaction()
            res = _check_homomorphism(tx, source, target)
            tx.commit()
        print(res)

    def find_matching(self, graph_id, pattern,
                      pattern_typing=None, nodes=None):
        """Find an instance of a pattern in a specified graph.

        This function takes as an input a graph and a pattern graph,
        optionally, it also takes a dictionary specifying pattern typing
        and a collection of nodes specifying the subgraph of the
        original graph, where the matching should be searched in, then it
        searches for a matching of the pattern inside of the graph (or induced
        subragh), which corresponds to solving subgraph matching problem.
        The matching is defined by a map from the nodes of the pattern
        to the nodes of the graph such that:

        * edges are preserved, i.e. if there is an edge between nodes `n1`
          and `n2` in the pattern, there is an edge between the nodes of
          the graph that correspond to the image of `n1` and `n2`, moreover,
          the attribute dictionary of the edge between `n1` and `n2` is the
          subdictiotary of the edge it corresponds to in the graph;
        * the attribute dictionary of a pattern node is a subdictionary of
          its image in the graph;
        * (if pattern typing is specified) if node `n1` of the pattern
          is typed by some node `t` in the graph `T` of the hierarchy,
          then its image is also typed by `t` from the graph `T`.

        Uses `networkx.isomorphism.(Di)GraphMatcher` class, which implements
        subgraph matching algorithm.

        Parameters
        ----------
        graph_id
            Id of the graph in the hierarchy to search for matches
        pattern : nx.(Di)Graph
            Pattern graph to search for
        pattern_typing : dict, optional
            Dictionary defining the (partial) pattern typing,
            where keys are graph nodes of the hierarchy and
            values are (partial) mappings from the nodes
            of the pattern to the nodes of its typing graph given
            by the respective key
        nodes : iterable
            Subset of nodes to search for matching

        Returns
        -------
        instances : list of dict's
            List of instances of matching found in the graph, every instance
            is represented with a dictionary where keys are nodes of the
            pattern, and values are corresponding nodes of the graph.

        Raises
        ------
        ReGraphError
            If `graph_id` is a rule node or pattern is not valid under the
            provided `pattern_typing`
        """
        graph = self._access_graph(graph_id)
        if pattern_typing is None:
            instances = graph.find_matching(pattern, nodes)
        else:
            pass
        return instances

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
        if rhs_typing is None:
            rhs_typing = dict()

        # Rewriting of the base graph
        g = self._access_graph(graph_id)
        rhs_g = g.rewrite(rule, instance, rhs_typing)

        # Add tmp rhs typing
        rhs_temp_typing_query = ""
        for graph in rhs_typing.keys():
            rhs_typed_vars = {
                rhs_g[rhs_node]: "node_{}_{}".format(rhs_g[rhs_node], graph_id)
                for rhs_node in rhs_typing[graph].keys()
            }

            # Match subquery for rhs_nodes
            rhs_temp_typing_query +=\
                cypher.match_nodes(
                    {v: k for k, v in rhs_typed_vars.items()},
                    node_label=graph_id) +\
                cypher.with_vars([v for v in rhs_typed_vars.values()])

            # Add temp typing subquery
            rhs_temp_typing_query += "OPTIONAL MATCH "

            nodes_to_match = []
            merge_subqueres = []
            for node in rhs_typing[graph].keys():
                rhs_typed_var = "node_{}_{}".format(rhs_g[node], graph_id)
                rhs_typing_var = "node_{}_{}".format(
                    rhs_typing[graph][node], graph)
                if node in rule.added_nodes():
                    nodes_to_match.append(
                        "({}:{} {{id:'{}'}}), ".format(
                            rhs_typed_var, graph_id, rhs_g[node]) +
                        "({}:{} {{id:'{}'}})".format(
                            rhs_typing_var, graph, rhs_typing[graph][node]))
                    merge_subqueres.append(
                        "MERGE ({})-[:tmp_typing]->({})".format(
                            rhs_typed_var, rhs_typing_var)
                    )
            rhs_temp_typing_query += (
                ", ".join(nodes_to_match) + "\n" +
                "\n".join(merge_subqueres)
            )

            print(rhs_temp_typing_query)
            self.execute(rhs_temp_typing_query)

        # Checking if the rhs typing is consistent
        with self._driver.session() as session:
            tx = session.begin_transaction()
            consistent_typing = _check_rhs_consistency(tx, graph_id)
            tx.commit()

        if consistent_typing:
            self.execute(propagation.preserve_tmp_typing(graph_id))
            # self.execute(remove_tmp_typing(graph_id))
        else:
            self.execute(propagation.remove_tmp_typing(graph_id))

        if rule.is_restrictive():
            self._propagate_up(graph_id, rule)
        if rule.is_relaxing():
            self._propagate_down(graph_id, rule)

        return rhs_g

    def node_type(self, graph_id, node_id):
        """Get a list of the immediate types of a node.

        Returns
        -------
        types : dict
            Dictionary whose keys are ids of the graphs in the
            hierarchy that type `graph_id` and values are the
            nodes typing `node_id` from `graph_id`

        Raises
        ------
        HierarchyError
            If graph with a given id does not exist in the hierarchy or
            the node with `node_id` is not in the graph
        """
        pass

    def get_typing(self, source, target):
        """Get typing dict of `source` by `target`."""
        pass

    def successors(self, graph_label):
        """Get all the ids of the successors of a graph."""
        query = cypher.successors_query(var_name='g',
                                        node_id=graph_label,
                                        node_label='hierarchyNode',
                                        edge_label='hierarchyEdge')
        succ = self.execute(query).value()
        if succ[0] is None:
            succ = []
        return succ

    def predecessors(self, graph_label):
        """Get all the ids of the predecessors of a graph."""
        query = cypher.predecessors_query(var_name='g',
                                          node_id=graph_label,
                                          node_label='hierarchyNode',
                                          edge_label='hierarchyEdge')
        preds = self.execute(query).value()
        if preds[0] is None:
            preds = []
        return preds

    def to_nx_graph(self):
        """Create a simple networkx graph representing the hierarchy.

        Note that the relation edges are ignored.

        Returns
        -------
        g : nx.DiGraph
            Simple NetworkX graph representing the structure of the
            hierarchy
        """
        g = nx.DiGraph()
        for node in self.nodes():
            g.add_node(node, self.node[node].attrs)
        for s, t in self.edges():
            g.add_edge(s, t, self.edge[s][t].attrs)
        return g

    def rename_graph(self, graph_id, new_graph_id):
        """Rename a graph in the hierarchy."""
        pass

    def rename_node(self, graph_id, node, new_name):
        """Rename a node in a graph of the hierarchy."""
        pass

    def unique_graph_id(self, prefix):
        """Generate a new graph id starting with a prefix."""
        pass

    def _propagate_up(self, graph_id, rule):
        predecessors = self.predecessors(graph_id)
        for predecessor in predecessors:
            clone_query = None
            remove_node_query = None
            remove_edge_query = None

            # Propagate node clones
            if len(rule.cloned_nodes()) > 0:
                clone_query = propagation.clone_propagation_query(
                    graph_id, predecessor)

            # Propagate node deletes
            if len(rule.removed_nodes()) > 0:
                remove_node_query = propagation.remove_node_query(
                    graph_id, predecessor)

            # Propagate edge deletes
            if len(rule.removed_edges()) > 0:
                remove_edge_query = propagation.remove_edge_query(
                    graph_id, predecessor)

            # run multiple queries in one transaction
            with self._driver.session() as session:
                tx = session.begin_transaction()
                if clone_query:
                    print(clone_query)
                    tx.run(clone_query)
                if remove_node_query:
                    print(remove_node_query)
                    tx.run(remove_node_query)
                if remove_edge_query:
                    print(remove_edge_query)
                    tx.run(remove_edge_query)
                tx.commit()
        for ancestor in predecessors:
            self._propagate_up(ancestor, rule)

    def _propagate_down(self, graph_id, rule):
        successors = self.successors(graph_id)
        for successor in successors:
                # Propagate merges
                merge_query = None
                add_nodes_query = None
                add_edges_query = None

                # Propagate node merges
                if len(rule.merged_nodes()) > 0:
                    # match nodes of T with the same pre-image in G and merge them
                    merge_query = propagation.merge_propagation_query(
                        graph_id, successor)

                # Propagate node adds
                if len(rule.added_nodes()) > 0:
                    add_nodes_query = propagation.add_node_propagation_query(
                        graph_id, successor)

                # (Propagate edge adds
                if len(rule.added_edges()) > 0:
                    add_edges_query = propagation.add_edge_propagation_query(
                        graph_id, successor)

                # Run multiple queries in one transaction
                with self._driver.session() as session:
                    tx = session.begin_transaction()
                    if merge_query:
                        print(merge_query)
                        tx.run(merge_query).single()
                    if add_nodes_query:
                        print(add_nodes_query)
                        tx.run(add_nodes_query).single()
                    if add_edges_query:
                        print(add_edges_query)
                        tx.run(add_edges_query).single()
                    tx.commit()

        for successor in successors:
            self._propagate_down(successor, rule)
