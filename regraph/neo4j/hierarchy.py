"""Neo4j driver for regraph."""
import networkx as nx

from neo4j.v1 import GraphDatabase
from neo4j.exceptions import ConstraintError

from regraph.neo4j.graphs import Neo4jGraph
import regraph.neo4j.cypher_utils as cypher
from regraph.exceptions import (HierarchyError,
                                InvalidHomomorphism,
                                RewritingError)
from regraph.utils import (normalize_attrs, keys_by_value)


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

    def valid_typing(self, source, target):
        """Check if the typing is valid."""
        with self._driver.session() as session:
            tx = session.begin_transaction()
            valid_typing = cypher.check_homomorphism(tx, source, target)
            tx.commit()
        return valid_typing

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
                cypher.add_edge(
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
                    valid_typing = cypher.check_homomorphism(tx, source, target)
                    tx.commit()
            except InvalidHomomorphism as homomorphism_error:
                valid_typing = False
                del_query = (
                    "MATCH (:{})-[t:typing]-(:{})\n".format(
                        source, target) +
                    "DELETE t\n"
                )
                self.execute(del_query)
                raise homomorphism_error
            # We then check that the new typing preserv consistency
            try:
                with self._driver.session() as session:
                    tx = session.begin_transaction()
                    paths_commute = cypher.check_consistency(tx, source, target)
                    tx.commit()
            except InvalidHomomorphism as consistency_error:
                paths_commute = False
                del_query = (
                    "MATCH (:{})-[t:typing]-(:{})\n".format(
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
                cypher.add_edge(
                    edge_var='new_hierarchy_edge',
                    source_var='g_src',
                    target_var='g_tar',
                    edge_label='hierarchyEdge',
                    attrs=attrs) +
                cypher.with_vars(["new_hierarchy_edge"]) +
                "MATCH (:{})-[t:typing]-(:{})\n".format(
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
                "MATCH (n:{})".format(node_id) +
                "OPTIONAL MATCH (pred)-[:typing]->(n)-[:typing]->(suc)\n" +
                "WITH pred, suc WHERE pred IS NOT NULL\n" +
                cypher.add_edge(
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
                cypher.add_edge(
                    edge_var='recennect_typing',
                    source_var='pred',
                    target_var='suc',
                    edge_label='hierarchyEdge')
            )
            self.execute(query)
        query = cypher.match_node(var_name="graph_to_rm",
                                  node_id=node_id,
                                  node_label='hierarchyNode')
        query += cypher.remove_nodes(["graph_to_rm"])
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
            res = cypher._check_homomorphism(tx, source, target)
            tx.commit()

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
        instances = graph.find_matching(
            pattern, pattern_typing=pattern_typing, nodes=nodes)

        return instances

    def rewrite(self, graph_id, rule, instance,
                rhs_typing=None, strict=True):
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
        strict : bool, optional
            Rewriting is strict when propagation down is not allowed

        Raises
        ------
        HierarchyError
            If the graph is not in the database
        TypingWarning
            If the rhs typing is inconsistent
        """
        if rhs_typing is None:
            rhs_typing = {}

        if strict is True:
            self._check_rhs_typing(graph_id, rule, instance, rhs_typing)

        # Rewriting of the base graph
        g = self._access_graph(graph_id)
        rhs_g = g.rewrite(rule, instance)

        # Additing temporary typing specified by 'rhs_typing'
        if len(rule.added_nodes()) > 0 and rhs_typing:
            self._add_tmp_typing(graph_id, rhs_g, rhs_typing)

        # Propagation
        if rule.is_restrictive():
            self._propagate_up(graph_id, rule)
        if strict is False and rule.is_relaxing():
            self._propagate_down(graph_id, graph_id, rule)

        return rhs_g

    def _propagate_up(self, graph_id, rule):
        predecessors = self.predecessors(graph_id)
        for predecessor in predecessors:
            clone_query = None
            remove_node_query = None
            remove_edge_query = None

            # Propagate node clones
            if len(rule.cloned_nodes()) > 0:
                clone_query = cypher.clone_propagation_query(
                    graph_id, predecessor)

            # Propagate node deletes
            if len(rule.removed_nodes()) > 0 or\
               len(rule.removed_node_attrs()) > 0:
                remove_node_query = cypher.remove_node_propagation_query(
                    graph_id, predecessor)

            # Propagate edge deletes
            if len(rule.removed_edges()) > 0 or\
               len(rule.removed_edge_attrs()) > 0:
                remove_edge_query = cypher.remove_edge_propagation_query(
                    graph_id, predecessor)

            # run multiple queries in one transaction
            with self._driver.session() as session:
                tx = session.begin_transaction()
                if clone_query:
                    tx.run(clone_query)
                if remove_node_query:
                    tx.run(remove_node_query)
                if remove_edge_query:
                    tx.run(remove_edge_query)
                tx.commit()
        for ancestor in predecessors:
            self._propagate_up(ancestor, rule)

    def _propagate_down(self, origin_graph, graph_id, rule):
        successors = self.successors(graph_id)
        for successor in successors:
                # Propagate merges
                merge_query = None
                add_nodes_query = None
                add_edges_query = None

                # Propagate node merges
                if len(rule.merged_nodes()) > 0:
                    # match nodes of T with the same pre-image in G and merge them
                    merge_query = cypher.merge_propagation_query(
                        graph_id, successor)

                # Propagate node adds
                if len(rule.added_nodes()) > 0 or\
                   len(rule.added_node_attrs()) > 0:
                    add_nodes_query = cypher.add_node_propagation_query(
                        origin_graph, graph_id, successor)

                # (Propagate edge adds
                if len(rule.added_edges()) > 0 or\
                   len(rule.added_edge_attrs()) > 0:
                    add_edges_query = cypher.add_edge_propagation_query(
                        graph_id, successor)

                # Run multiple queries in one transaction
                with self._driver.session() as session:
                    tx = session.begin_transaction()
                    if merge_query:
                        tx.run(merge_query).single()
                    if add_nodes_query:
                        tx.run(add_nodes_query).single()
                    if add_edges_query:
                        tx.run(add_edges_query).single()
                    tx.commit()

        for successor in successors:
            self._propagate_down(origin_graph, successor, rule)

    def _add_tmp_typing(self, graph_id, rhs_g, rhs_typing):
        rhs_tmp_typing = ""
        for graph in rhs_typing.keys():
            # Add temp typing subquery
            query = (
                "// Adding temporary typing of the rhs nodes\n" +
                "OPTIONAL MATCH "
            )

            nodes_to_match = []
            merge_subqueres = []
            for node in rhs_typing[graph].keys():
                rhs_typed_var = "n{}_{}".format(rhs_g[node], graph_id)
                rhs_typing_var = "n{}_{}".format(
                    rhs_typing[graph][node], graph)
                nodes_to_match.append(
                    "({}:{} {{id:'{}'}}), ".format(
                        rhs_typed_var, graph_id, rhs_g[node]) +
                    "({}:{} {{id:'{}'}})".format(
                        rhs_typing_var, graph, rhs_typing[graph][node]))
                merge_subqueres.append(
                    "MERGE ({})-[:tmp_typing]->({})".format(
                        rhs_typed_var, rhs_typing_var)
                )
            query += (
                ", ".join(nodes_to_match) + "\n" +
                "\n".join(merge_subqueres)
                # cypher.with_vars(["NULL"]) + "\n"
            )
            rhs_tmp_typing += query + "\n"
            self.execute(query)

        # Checking if the introduces rhs typing is consistent
        with self._driver.session() as session:
            tx = session.begin_transaction()
            consistent_typing = cypher.check_rhs_consistency(tx, graph_id)
            tx.commit()

        if consistent_typing:
            self.execute(cypher.preserve_tmp_typing(graph_id))
        else:
            self.execute(cypher.remove_tmp_typing(graph_id))

    def _check_rhs_typing(self, graph_id, rule, instance, rhs_typing):
        # Check the rhs typing can be consistently inferred
        if rule.is_relaxing():
            for s in self.successors(graph_id):
                # check if there are no untyped new nodes
                for n in rule.added_nodes():
                    if s not in rhs_typing.keys() or\
                       n not in rhs_typing[s].keys():
                        raise RewritingError(
                            "Rewriting is strict (no propagation of types is "
                            "allowed), typing of the node '{}' "
                            "in rhs is required (typing by the following "
                            "graph stays unresolved: '{}')!".format(n, s))

                # check if there are no merges of different types
                merges = {}
                for rhs_node, p_nodes in rule.merged_nodes().items():
                    merged_types = set(
                        [self.node_type(
                            graph_id, instance[rule.p_lhs[n]])[s] for n in p_nodes])
                    if len(merged_types) > 1:
                        raise RewritingError(
                            "Rewriting is strict (no propagation of merges is "
                            "allowed), merging of the nodes [{}] (matched as [{}] in "
                            "P) requires merge of nodes [{}] "
                            "in the graph '{}')!".format(
                                ", ".join([instance[rule.p_lhs[n]] for n in p_nodes]),
                                ", ".join(p_nodes),
                                ", ".join(t for t in merged_types), s))
                    merges[rhs_node] = list(merged_types)[0]

                # check if there are no forbidden edges
                preserved_nodes = {}
                for n in rule.rhs.nodes():
                    if n not in rule.merged_nodes() and\
                       n not in rule.added_nodes():
                        preserved_nodes[n] = list(
                            keys_by_value(rule.p_rhs, n))[0]

                for source, target in rule.added_edges():
                    if source in rule.added_nodes():
                        source_typing = rhs_typing[s][source]
                    elif source in merges.keys():
                        source_typing = merges[source]
                    else:
                        p_source = keys_by_value(rule.p_rhs, source)[0]
                        source_typing = self.node_type(
                            graph_id, instance[rule.p_lhs[p_source]])[s]

                    if target in rule.added_nodes():
                        target_typing = rhs_typing[s][target]
                    elif target in merges.keys():
                        target_typing = merges[target]
                    else:
                        p_target = keys_by_value(rule.p_rhs, target)[0]
                        target_typing = self.node_type(
                            graph_id, instance[rule.p_lhs[p_target]])[s]

                    if not self.exists_edge(s, source_typing, target_typing):
                        raise RewritingError(
                            "Rewriting is strict, and addition of an edge "
                            "'{}'->'{}' from R is not allowed as there ".format(
                                source, target) +
                            "is no edge '{}'->'{}'' in the graph '{}')!".format(
                                source_typing, target_typing, s))

                print(preserved_nodes)

                for n, attrs in rule.added_node_attrs().items():
                    if n in rule.added_nodes():
                        typing = rhs_typing[s][n]
                    elif n in merges.keys():
                        typing = merges[n]
                    else:
                        typing = preserved_nodes[n]
                    if not self.node_attributes_included(graph_id, s, n, typing):
                        raise RewritingError(
                            "Rewriting is strict, and some attributes of " +
                            "'{}' from P added by the rule are not present in ".format(n) +
                            "'{}' of the graph {}!".format(typing, s))

                for (source, target), attrs in rule.added_edge_attrs().items():
                    if source in rule.added_nodes():
                        source_typing = rhs_typing[s][source]
                    elif source in merges.keys():
                        source_typing = merges[source]
                    else:
                        source_typing = preserved_nodes[source]
                    if target in rule.added_nodes():
                        target_typing = rhs_typing[s][target]
                    elif target in merges.keys():
                        target_typing = merges[target]
                    else:
                        target_typing = preserved_nodes[target]
                    if not self.edge_attributes_included(
                        graph_id, s, (source, target),
                            (source_typing, target_typing)):
                        raise RewritingError(
                            "Rewriting is strict, and some attributes of " +
                            "'{}'->'{}' from P added by the rule are not present in ".format(
                                source, target) +
                            "'{}'->'{}' of the graph {}!".format(
                                source_typing, target_typing, s))

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
        query = (
            "MATCH (n:{} {{id: '{}'}})\n".format(graph_id, node_id) +
            "OPTIONAL MATCH (n)-[:typing]->(m)\n" +
            "RETURN labels(m)[0] as successor, m.id as typing_node"
        )
        result = self.execute(query)
        types = {}
        for record in result:
            if "successor" in record.keys() and\
               "typing_node" in record.keys():
                types[record["successor"]] = record["typing_node"]
        return types

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

    def exists_edge(self, graph_id, s, t):
        """Test if an edge 's'->'t' exists in 'graph_id'."""
        query = cypher.exists_edge(
            s, t,
            node_label=graph_id, edge_label="edge")
        result = self.execute(query)
        for record in result:
            if "result" in record.keys():
                return record["result"]

    def edge_attributes_included(self, g1, g2, e1, e2):
        query = (
            cypher.match_edge("s1", "t1", e1[0], e1[0], "rel1") +
            "WITH rel1\n" +
            cypher.match_edge("s2", "t2", e2[0], e2[0], "rel2") +
            "WITH rel1, rel2, \n" +
            "\t" + cypher.attributes_inclusion("rel1", "rel2", "invalid") + " \n" +
            "RETURN invalid <> 0 as result"
        )
        result = self.execute(query)
        for record in result:
            if "result" in record.keys():
                return record["result"]

    def node_attributes_included(self, g1, g2, n1, n2):
        query = (
            cypher.match_nodes({"n1": n1, "n2": n2}) +
            "WITH n1, n2, \n" +
            "\t" + cypher.attributes_inclusion("n1", "n2", "invalid") + " \n" +
            "RETURN invalid <> 0 as result"
        )
        result = self.execute(query)
        for record in result:
            if "result" in record.keys():
                return record["result"]
