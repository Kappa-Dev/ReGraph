"""Neo4j-based persisent graph hierarchies.

This module implements data structures that allow working with persistent
graph hierarchies stored in an instance of the Neo4j database:

* `Neo4jHierarchy` -- class for persistent graph hierarchies.
* `TypedNeo4jGraph` -- class for schema-aware property graph.
"""
import os
import json
import warnings

from neo4j.v1 import GraphDatabase
from neo4j.exceptions import ConstraintError

from regraph.rules import Rule
from regraph.backends.networkx.graphs import NXGraph
from regraph.exceptions import (HierarchyError,
                                InvalidHomomorphism,
                                ReGraphError,
                                ReGraphWarning,
                                RewritingError)
from regraph.hierarchies import Hierarchy
from regraph.backends.neo4j.graphs import Neo4jGraph
from .cypher_utils.generic import (constraint_query,
                                   get_nodes,
                                   get_edges,
                                   clear_graph,
                                   successors_query,
                                   predecessors_query,
                                   get_edge_attrs,
                                   properties_to_attributes,
                                   get_node_attrs,
                                   set_attributes,
                                   match_nodes,
                                   with_vars,
                                   match_node,
                                   shortest_path_query,
                                   match_edge,
                                   )
from .cypher_utils.propagation import (set_intergraph_edge,
                                       check_homomorphism,
                                       check_consistency,
                                       get_typing,
                                       get_relation)
from .cypher_utils.rewriting import (add_edge,
                                     remove_nodes,
                                     remove_edge)
from regraph.utils import (normalize_attrs,
                           attrs_from_json,
                           normalize_relation,
                           valid_attributes,
                           keys_by_value)


class Neo4jHierarchy(Hierarchy):
    """
    Class for persistent hierarchies.

    Attributes
    ----------

    """

    # Implementation of abstract methods

    def graphs(self, data=False):
        """Return a list of graphs in the hierarchy."""
        query = get_nodes(node_label=self._graph_label, data=data)
        result = self.execute(query)
        graphs = []
        for d in result:
            if data:
                normalize_attrs(d["attrs"])
                del d["attrs"]["id"]
                graphs.append((d["node_id"], d["attrs"]))
            else:
                graphs.append(d["node_id"])
        return graphs

    def typings(self, data=False):
        """Return a list of graph typing edges in the hierarchy."""
        query = get_edges(
            self._graph_label,
            self._graph_label,
            self._typing_label,
            data=data)
        result = self.execute(query)
        typings = []
        for d in result:
            if data:
                normalize_attrs(d["attrs"])
                typings.append((d["source_id"], d["target_id"], d["attrs"]))
            else:
                typings.append((d["source_id"], d["target_id"]))
        return typings

    def relations(self, data=False):
        """Return a list of relations."""
        query = get_edges(
            self._graph_label,
            self._graph_label,
            self._relation_label,
            data=data)
        result = self.execute(query)
        relations = []
        for d in result:
            if data:
                normalize_attrs(d["attrs"])
                relations.append((d["source_id"], d["target_id"], d["attrs"]))
            else:
                relations.append((d["source_id"], d["target_id"]))
        return relations

    def successors(self, node_id):
        """Return the set of successors."""
        query = successors_query(var_name='g',
                                 node_id=node_id,
                                 node_label=self._graph_label,
                                 edge_label=self._typing_label)
        succ = self.execute(query).value()
        if succ[0] is None:
            succ = []
        return succ

    def predecessors(self, node_id):
        """Return the set of predecessors."""
        query = predecessors_query(var_name='g',
                                   node_id=node_id,
                                   node_label=self._graph_label,
                                   edge_label=self._typing_label)
        preds = self.execute(query).value()
        if preds[0] is None:
            preds = []
        return preds

    def get_graph(self, graph_id):
        """Get a graph object associated to the node 'graph_id'."""
        return self._access_graph(graph_id)

    def get_typing(self, source_id, target_id):
        """Get a typing dict associated to the edge 'source_id->target_id'."""
        query = get_typing(source_id, target_id, "typing")
        result = self.execute(query)
        typing = {}
        source_nodes = self.get_graph(source_id).nodes()
        target_nodes = self.get_graph(target_id).nodes()
        for record in result:
            node_id = record["node"]
            if node_id not in source_nodes:
                try:
                    node_id = int(node_id)
                except:
                    pass
            type_id = record["type"]
            if type_id not in target_nodes:
                try:
                    type_id = int(type_id)
                except:
                    pass
            typing[node_id] = type_id
        return typing

    def get_relation(self, left_id, right_id):
        """Get a relation dict associated to the rel 'left_id->target_id'."""
        query = get_relation(left_id, right_id, "relation")
        result = self.execute(query)
        relation = {}
        for record in result:
            if record["node"] in relation.keys():
                relation[record["node"]].add(record["type"])
            else:
                relation[record["node"]] = {record["type"]}
        return relation

    def get_graph_attrs(self, graph_id):
        """Get attributes of a graph in the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph
        """
        query = get_node_attrs(
            graph_id, self._graph_label,
            "attributes")
        result = self.execute(query)
        return properties_to_attributes(
            result, "attributes")

    def set_graph_attrs(self, graph_id, attrs, update=False):
        """Set attributes of a graph in the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph
        """
        skeleton = self._access_graph(self._graph_label)
        skeleton.set_node_attrs(graph_id, attrs, update)

    def get_typing_attrs(self, source_id, target_id):
        """Get attributes of a typing in the hierarchy.

        Parameters
        ----------
        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        query = get_edge_attrs(
            source_id, target_id, self._typing_label,
            "attributes")
        result = self.execute(query)
        return properties_to_attributes(result, "attributes")

    def set_typing_attrs(self, source, target, attrs):
        """Set attributes of a typing in the hierarchy.

        Parameters
        ----------
        source : hashable
            Id of the source graph
        target : hashable
            Id of the target graph
        """
        skeleton = self._access_graph(self._graph_label, self._typing_label)
        skeleton.set_edge_attrs(source, target, attrs)

    def get_relation_attrs(self, left_id, right_id):
        """Get attributes of a reltion in the hierarchy.

        Parameters
        ----------
        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
        """
        query = get_edge_attrs(
            left_id, right_id, self._relation_label,
            "attributes")
        result = self.execute(query)
        return properties_to_attributes(result, "attributes")

    def set_relation_attrs(self, left, right, attrs):
        """Set attributes of a relation in the hierarchy.

        Parameters
        ----------
        left : hashable
            Id of the left graph
        right : hashable
            Id of the right graph
        """
        skeleton = self._access_graph(self._graph_label, self._relation_label)
        skeleton.set_edge_attrs(left, right, attrs)

    def set_node_relation(self, left_graph, right_graph, left_node,
                          right_node):
        """Set relation for a particular node.

        Parameters
        ----------
        """
        query = set_intergraph_edge(
            left_graph, right_graph, left_node, right_node,
            "relation")
        self.execute(query)

    def add_graph(self, graph_id, graph, attrs=None):
        """Add a new graph to the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        graph : regraph.Graph
            Graph object corresponding to the new node of
            the hierarchy
        graph_attrs : dict, optional
            Dictionary containing attributes of the new node
        """
        self.add_graph_from_data(
            graph_id, graph.nodes(data=True), graph.edges(data=True), attrs)

    def add_graph_from_data(self, graph_id, node_list, edge_list, attrs=None):
        """Add a new graph to the hierarchy from the input node/edge lists.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        node_list : iterable
            List of nodes (with attributes)
        edge_list : iterable
            List of edges (with attributes)
        graph_attrs : dict, optional
            Dictionary containing attributes of the new node
        """
        try:
            # Create a node in the hierarchy
            query = "CREATE ({}:{} {{ id : '{}' }}) \n".format(
                'new_graph',
                self._graph_label,
                graph_id)
            if attrs is not None:
                normalize_attrs(attrs)
                query += set_attributes(
                    var_name='new_graph',
                    attrs=attrs)
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

    def add_empty_graph(self, graph_id, attrs=None):
        """"Add a new empty graph to the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of a new node in the hierarchy
        graph_attrs : dict, optional
            Dictionary containing attributes of the new node
        """
        self.add_graph_from_data(
            graph_id, node_list=[], edge_list=[], attrs=attrs)

    def add_typing(self, source, target, mapping, attrs=None, check=True):
        """Add homomorphism to the hierarchy.

        Parameters
        ----------
        source : hashable
            Id of the source graph node of typing
        target : hashable
            Id of the target graph node of typing
        mapping : dict
            Dictionary representing a mapping of nodes
            from the source graph to target's nodes
        attrs : dict
            Dictionary containing attributes of the new
            typing edge

        Raises
        ------
        HierarchyError
            This error is raised in the following cases:

                * source or target ids are not found in the hierarchy
                * a typing edge between source and target already exists
                * addition of an edge between source and target creates
                a cycle or produces paths that do not commute with
                some already existing paths

        InvalidHomomorphism
            If a homomorphisms from a graph at the source to a graph at
            the target given by `mapping` is not a valid homomorphism.

        """
        query = ""
        tmp_attrs = {'tmp': {'true'}}
        normalize_attrs(tmp_attrs)

        if len(mapping) > 0:
            with self._driver.session() as session:
                tx = session.begin_transaction()
                for u, v in mapping.items():
                    query = (
                        set_intergraph_edge(
                            source, target,
                            u, v, "typing",
                            attrs=tmp_attrs))
                    tx.run(query)
                tx.commit()

        valid_typing = True
        paths_commute = True
        if check:
            # We first check that the homorphism is valid
            try:
                with self._driver.session() as session:
                    tx = session.begin_transaction()
                    valid_typing = check_homomorphism(tx, source, target)
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
                    paths_commute = check_consistency(tx, source, target)
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
                match_nodes(
                    var_id_dict={'g_src': source, 'g_tar': target},
                    node_label=self._graph_label) +
                add_edge(
                    edge_var='new_hierarchy_edge',
                    source_var='g_src',
                    target_var='g_tar',
                    edge_label=self._typing_label,
                    attrs=attrs) +
                with_vars(["new_hierarchy_edge"]) +
                "MATCH (:{})-[t:typing]-(:{})\n".format(
                    source, target) +
                "REMOVE t.tmp\n"

            )
            self.execute(skeleton_query)
        # return result

    def add_relation(self, left, right, relation, attrs=None):
        """Add relation to the hierarchy.

        This method adds a relation between two graphs in
        the hierarchy corresponding to the nodes with ids
        `left` and `right`, the relation itself is defined
        by a dictionary `relation`, where a key is a node in
        the `left` graph and its corresponding value is a set
        of nodes from the `right` graph to which the node is
        related. Relations in the hierarchy are symmetric
        (see example below).

        Parameters
        ----------
        left
            Id of the hierarchy's node represening the `left` graph
        right
            Id of the hierarchy's node represening the `right` graph
        relation : dict
            Dictionary representing a relation of nodes from `left`
            to the nodes from `right`, a key of the dictionary is
            assumed to be a node from `left` and its value a set
            of ids of related nodes from `right`
        attrs : dict
            Dictionary containing attributes of the new relation

        Raises
        ------
        HierarchyError
            This error is raised in the following cases:

                * node with id `left`/`right` is not defined in the hierarchy;
                * node with id `left`/`right` is not a graph;
                * a relation between `left` and `right` already exists;
                * some node ids specified in `relation` are not found in the
                `left`/`right` graph.
        """
        new_rel = normalize_relation(relation)

        if attrs is not None:
            normalize_attrs(attrs)

        for key, values in new_rel.items():
            for v in values:
                query = (
                    "MATCH (u:{} {{id: '{}'}}), (v:{} {{id: '{}'}})\n".format(
                        left, key, right, v) +
                    add_edge(
                        edge_var="rel",
                        source_var="u",
                        target_var="v",
                        edge_label="relation")
                )
                self.execute(query)

        # query = ""
        # rel_creation_queries = []
        # nodes_to_match_left = set()
        # nodes_to_match_right = set()
        # for key, values in relation.items():
        #     nodes_to_match_left.add(key)
        #     for value in values:
        #         nodes_to_match_right.add(value)
        #         rel_creation_queries.append(
        #             add_edge(
        #                 edge_var="rel_" + key + "_" + value,
        #                 source_var="n" + key + "_left",
        #                 target_var="n" + value + "_right",
        #                 edge_label="relation"))

        # if len(nodes_to_match_left) > 0:
        #     query += match_nodes(
        #         {"n" + n + "_left": n for n in nodes_to_match_left},
        #         node_label=g_left._node_label)
        #     query += with_vars(
        #         ["n" + s + "_left" for s in nodes_to_match_left])
        #     query += match_nodes(
        #         {"n" + n + "_right": n for n in nodes_to_match_right},
        #         node_label=g_right._node_label)
        #     for q in rel_creation_queries:
        #         query += q
        # print(query)
        # rel_addition_result = self.execute(query)

        skeleton_query = (
            match_nodes(
                var_id_dict={'g_left': left, 'g_right': right},
                node_label=self._graph_label) +
            add_edge(
                edge_var='new_hierarchy_edge',
                source_var='g_left',
                target_var='g_right',
                edge_label=self._relation_label,
                attrs=attrs)
        )
        skeleton_addition_result = self.execute(skeleton_query)
        return (None, skeleton_addition_result)

    def remove_graph(self, graph_id, reconnect=False):
        """Remove graph from the hierarchy.

        Removes a graph from the hierarchy, if the `reconnect`
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
            Id of a graph to remove
        reconnect : bool
            Reconnect the descendants of the removed node to
            its predecessors

        Raises
        ------
        HierarchyError
            If graph with `node_id` is not defined in the hierarchy
        """
        g = self._access_graph(graph_id)

        if reconnect:
            query = (
                "MATCH (n:{})".format(graph_id) +
                "OPTIONAL MATCH (pred)-[:typing]->(n)-[:typing]->(suc)\n" +
                "WITH pred, suc WHERE pred IS NOT NULL\n" +
                add_edge(
                    edge_var='reconnect_typing',
                    source_var='pred',
                    target_var='suc',
                    edge_label="typing")
            )
            self.execute(query)
        # Clear the graph and drop the constraint on the ids
        g._drop_constraint('id')
        g._clear()

        # Remove the graph (and reconnect if True)
        if reconnect:
            query = (
                match_node(
                    var_name="graph_to_rm",
                    node_id=graph_id,
                    node_label=self._graph_label) +
                "OPTIONAL MATCH (pred)-[:{}]->(n)-[:{}]->(suc)\n".format(
                    self._typing_label, self._typing_label) +
                "WITH pred, suc WHERE pred IS NOT NULL\n" +
                add_edge(
                    edge_var='reconnect_typing',
                    source_var='pred',
                    target_var='suc',
                    edge_label="typing")
            )
            self.execute(query)
        query = match_node(var_name="graph_to_rm",
                           node_id=graph_id,
                           node_label=self._graph_label)
        query += remove_nodes(["graph_to_rm"])
        self.execute(query)

    def remove_typing(self, s, t):
        """Remove a typing from the hierarchy."""
        # Clean-up the represenation of the homomorphism
        query = (
            "MATCH (:{})-[r:{}]->(:{})\n".format(
                s, self._graph_typing_label, t) +
            "DELETE r\n"
        )
        self.execute(query)
        # Remove the corresponding edge from the skeleton
        query = match_edge(
            "source", "target", s, t, "e",
            self._graph_label, self._graph_label,
            edge_label=self._typing_label)
        query += remove_edge("e")
        self.execute(query)

    def remove_relation(self, left, right):
        """Remove a relation from the hierarchy."""
        query = (
            "MATCH (:{})-[r:{}]-(:{})\n".format(
                left, self._graph_relation_label, right) +
            "DELETE r\n"
        )
        self.execute(query)
        # Remove the corresponding edge from the skeleton
        query = match_edge(
            "left", "right", left, right, "e",
            self._graph_label, self._graph_label,
            edge_label=self._relation_label)
        query += remove_edge("e")
        self.execute(query)

    def bfs_tree(self, graph, reverse=False):
        """BFS tree from the graph to all other reachable graphs."""
        bfs_result = []
        if reverse:
            current_level = self.predecessors(graph)
        else:
            current_level = self.successors(graph)
        bfs_result += current_level

        while len(current_level) > 0:
            next_level = []
            for g in current_level:
                if reverse:
                    next_level += [
                        p for p in self.predecessors(g)
                        if p not in set(bfs_result)]
                else:
                    next_level += [
                        s for s in self.successors(g)
                        if s not in set(bfs_result)
                    ]
            current_level = next_level
            bfs_result += next_level

        return bfs_result

    def shortest_path(self, source, target):
        """Shortest path from 'source' to 'target'."""
        query = shortest_path_query(
            source, target, self._graph_label, self._typing_label)
        result = self.execute(query)
        return result.single()["path"]

    def copy_graph(self, graph_id, new_graph_id, attach_graphs=[]):
        """Create a copy of a graph in a hierarchy."""
        if new_graph_id in self.graphs():
            raise HierarchyError(
                "Graph with id '{}' already exists in the hierarchy".format(
                    new_graph_id))
        self.add_graph(new_graph_id, attrs=self.get_graph_attrs(graph_id))
        copy_nodes_q = (
            "MATCH (n:{}) CREATE (n1:{}) SET n1=n\n ".format(
                graph_id, new_graph_id)
            # "SET n1.oldId = n.id, n1.id = toString(id(n1))\n"
        )
        self.execute(copy_nodes_q)
        copy_edges_q = (
            "MATCH (n:{})-[r:{}]->(m:{}), (n1:{}), (m1:{}) \n".format(
                graph_id, self._graph_edge_label, graph_id,
                new_graph_id, new_graph_id) +
            "WHERE n1.id=n.id AND m1.id=m.id \n" +
            "MERGE (n1)-[r1:{}]->(m1) SET r1=r\n".format(
                self._graph_edge_label)
        )
        self.execute(copy_edges_q)
        # copy all typings
        for g in attach_graphs:
            if g in self.successors(graph_id):
                self.add_typing(new_graph_id, g, self.get_typing(graph_id, g))
            if g in self.predecessors(graph_id):
                self.add_typing(g, new_graph_id, self.get_typing(g, graph_id))
            if g in self.adjacent_relations(graph_id):
                self.add_relation(g, new_graph_id, self.get_relation(g, graph_id))

    def relabel_graph_node(self, graph_id, node, new_name):
        """Rename a node in a graph of the hierarchy."""
        g = self.get_graph(graph_id)
        g.relabel_node(node, new_name)

    def relabel_graph(self, graph_id, new_graph_id):
        """Relabel a graph in the hierarchy.

        Parameters
        ----------
        graph_id : hashable
            Id of the graph to relabel
        new_graph_id : hashable
            New graph id to assign to this graph
        """
        if new_graph_id in self.graphs():
            raise ReGraphError(
                "Cannot relabel '{}' to '{}', '{}' ".format(
                    graph_id, new_graph_id, new_graph_id) +
                "already exists in the hierarchy")
        # Change labels of data nodes
        query = (
            "MATCH (n:{})\n".format(graph_id) +
            "SET n:{}\n".format(new_graph_id)
        )
        self.execute(query)

        # Relabel node in the skeleton
        skeleton = self._access_graph(self._graph_label)
        skeleton.relabel_node(graph_id, new_graph_id)

    def relabel_graphs(self, mapping):
        """Relabel graphs in the hierarchy.

        Parameters
        ----------
        mapping: dict
            A dictionary with keys being old graph ids and their values
            being new id's of the respective graphs.

        Raises
        ------
        ReGraphError
            If new id's do not define a set of distinct graph id's.
        """
        # Relabel nodes in the skeleton
        skeleton = self._access_graph(self._graph_label)
        skeleton.relabel_nodes(mapping)

        temp_names = {}
        # Relabeling of the nodes: if at some point new ID conflicts
        # with already existing ID - assign temp ID
        for key, value in mapping.items():
            if key != value:
                if value not in self.graphs():
                    new_name = value
                else:
                    new_name = self.generate_new_node_id(value)
                    temp_names[new_name] = value
                query = (
                    "MATCH (n:{})\n".format(key) +
                    "SET n:{}\n".format(value)
                )
                self.execute(query)
        # Relabeling the nodes with the temp ID to their new IDs
        for key, value in temp_names:
            if key != value:
                query = (
                    "MATCH (n:{})\n".format(key) +
                    "SET n:{}\n".format(value)
                )
                self.execute(query)
        return

    def _update_mapping(self, source, target, mapping):
        """Update the mapping dictionary from source to target."""
        old_mapping = self.get_typing(source, target)

        typing_to_update = {
            k: mapping[k]
            for k, v in old_mapping.items()
            if k in mapping and mapping[k] != v
        }
        for k, v in typing_to_update.items():
            query = (
                "MATCH (s:{} {{id: '{}'}})-[r:{}]->(t:{} {{id: '{}'}}), ".format(
                    source, k, self._graph_typing_label, target, old_mapping[k]) +
                "(new_t:{} {{id: '{}'}})\n".format(target, v) +
                "DELETE r\n" +
                "MERGE (s)-[:{}]->(new_t)\n".format(self._graph_typing_label)
            )
            self.execute(query)

        new_typing = {
            k: v for k, v in mapping.items() if k not in typing_to_update
        }
        for k, v in new_typing.items():
            query = (
                "MATCH (s:{} {{id: '{}'}}), (new_t:{} {{id: '{}'}})\n".format(
                    source, k, target, v) +
                "MERGE (s)-[:{}]->(new_t)\n".format(self._graph_typing_label)
            )
            self.execute(query)

    def _update_relation(self, left, right, relation):
        """Update the relation dictionaries (left and right)."""
        old_relation = self.get_relation(left, right)
        relations_to_add = dict([
            (k, v.difference(old_relation[k]))
            if k in old_relation
            else (k, v)
            for k, v in relation.items()
        ])

        relation_to_remove = dict([
            (k, v.difference(relation[k]))
            if k in relation
            else (k, v)
            for k, v in old_relation.items()
        ])
        for k, vs in relations_to_add.items():
            for v in vs:
                query = (
                    "MATCH (s:{} {{id: '{}'}}), (t:{} {{id: '{}'}}) \n".format(
                        left, k, right, v) +
                    "MERGE (s)-[:{}]->(new_t)\n".format(
                        self._graph_relation_label)
                )
            self.execute(query)

        for k, vs in relation_to_remove.items():
            for v in vs:
                query = (
                    "MATCH (s:{} {{id: '{}'}})-[r:{}]-(t:{} {{id: '{}'}})\n".format(
                        left, k, self._graph_relation_label, right, v) +
                    "DELETE r\n"
                )
            self.execute(query)

    def _get_rule_liftings(self, graph_id, rule, instance, p_typing):
        pass

    def _get_rule_projections(self, graph_id, rule, instance, rhs_typing):
        pass

    # Implementation of the Neo4jHierarchy-specific methods

    def __init__(self, uri=None, user=None, password=None,
                 driver=None,
                 graph_label="graph",
                 typing_label="homomorphism",
                 relation_label="binaryRelation",
                 graph_edge_label="edge",
                 graph_typing_label="typing",
                 graph_relation_label="relation"):
        """Initialize driver.

        Parameters
        ----------

        uri : str, optional
            Uri for Neo4j database connection
        user : str, optional
            Username for Neo4j database connection
        password : str, optional
            Password for Neo4j database connection
        driver : neo4j.v1.direct.DirectDriver, optional
            Driver providing connection to a Neo4j database.
        graph_label : str, optional
            Label to use for skeleton nodes representing graphs.
        typing_label : str, optional
            Relation type to use for skeleton edges
            representing homomorphisms.
        relation_label : str, optional
            Relation type to use for skeleton edges
            representing relations.
        graph_edge_label : str, optional
            Relation type to use for all graph edges.
        graph_typing_label : str, optional
            Relation type to use for edges encoding homomorphisms.
        graph_relation_label : str, optional
            Relation type to use for edges encoding relations.
        """
        # The following idea is cool but it's not so easy:
        # as we have two types of nodes in the hierarchy:
        # graphs and rules, as well as two types of edges:
        # homomorphisms and relations, and so far Neo4jGraph
        # supports only a single label for nodes and for edges
        # Neo4jGraph.__init__(
        #     self, uri=uri, user=user, password=password,
        #     node_label="hierarchyNode",
        #     edge_label="hierarchyEdge")

        if driver is None:
            self._driver = GraphDatabase.driver(
                uri, auth=(user, password))
        else:
            self._driver = driver

        self._graph_label = graph_label
        self._typing_label = typing_label
        self._relation_label = relation_label
        self._graph_edge_label = graph_edge_label
        self._graph_typing_label = graph_typing_label
        self._graph_relation_label = graph_relation_label

        try:
            query = "CREATE " + constraint_query(
                'n', self._graph_label, 'id')
            self.execute(query)
        except:
            pass

    @classmethod
    def load(cls, uri=None, user=None, password=None,
             driver=None, filename=None, ignore=None,
             clear=False):
        """Load the hierarchy."""
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                json_data = json.loads(f.read())
                hierarchy = cls.from_json(
                    uri=uri, user=user, password=password,
                    driver=driver, json_data=json_data, ignore=ignore,
                    clear=clear)
            return hierarchy
        else:
            raise ReGraphError("File '{}' does not exist!".format(filename))

    @classmethod
    def from_json(cls, uri=None, user=None, password=None,
                  driver=None, json_data=None, ignore=None,
                  clear=False):
        """Create hierarchy object from JSON representation.

        Parameters
        ----------

        uri : str, optional
            Uri for Neo4j database connection
        user : str, optional
            Username for Neo4j database connection
        password : str, optional
            Password for Neo4j database connection
        driver : neo4j.v1.direct.DirectDriver, optional
            DB driver object
        json_data : dict, optional
            JSON-like dict containing representation of a hierarchy
        ignore : dict, optional
            Dictionary containing components to ignore in the process
            of converting from JSON, dictionary should respect the
            following format:
            {
                "graphs": <collection of ids of graphs to ignore>,
                "rules": <collection of ids of rules to ignore>,
                "typing": <collection of tuples containing typing
                    edges to ignore>,
                "rule_typing": <collection of tuples containing rule
                    typing edges to ignore>>,
                "relations": <collection of tuples containing
                    relations to ignore>,
            }
        directed : bool, optional
            True if graphs from JSON representation should be loaded as
            directed graphs, False otherwise, default value -- True

        Returns
        -------
        hierarchy : regraph.hierarchy.Hierarchy
        """
        hierarchy = cls(
            uri=uri, user=user, password=password, driver=driver)

        if clear is True:
            hierarchy._clear()

        # add graphs
        for graph_data in json_data["graphs"]:
            if ignore is not None and\
               "graphs" in ignore.keys() and\
               graph_data["id"] in ignore["graphs"]:
                pass
            else:
                if "attrs" not in graph_data.keys():
                    attrs = dict()
                else:
                    attrs = attrs_from_json(graph_data["attrs"])
                hierarchy.add_graph_from_json(
                    graph_data["id"], graph_data["graph"], attrs)

        # add typing
        for typing_data in json_data["typing"]:
            if ignore is not None and\
               "typing" in ignore.keys() and\
               (typing_data["from"], typing_data["to"]) in ignore["typing"]:
                pass
            else:
                if "attrs" not in typing_data.keys():
                    attrs = dict()
                else:
                    attrs = attrs_from_json(typing_data["attrs"])
                hierarchy.add_typing(
                    typing_data["from"],
                    typing_data["to"],
                    typing_data["mapping"],
                    attrs)

        # add relations
        for relation_data in json_data["relations"]:
            from_g = relation_data["from"]
            to_g = relation_data["to"]
            if ignore is not None and\
               "relations" in ignore.keys() and\
               ((from_g, to_g) in ignore["relations"] or
                    (to_g, from_g) in ignore["relations"]):
                pass
            else:
                if "attrs" not in relation_data.keys():
                    attrs = dict()
                else:
                    attrs = attrs_from_json(relation_data["attrs"])
                if (from_g, to_g) not in hierarchy.relations():
                    hierarchy.add_relation(
                        relation_data["from"],
                        relation_data["to"],
                        {a: set(b) for a, b in relation_data["rel"].items()},
                        attrs
                    )
        return hierarchy

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
        query = clear_graph()
        result = self.execute(query)
        # self.drop_all_constraints()
        return result

    def _clear_all(self):
        query = "MATCH (n) DETACH DELETE n"
        self.execute(query)

    def _drop_all_constraints(self):
        """Drop all the constraints on the hierarchy."""
        with self._driver.session() as session:
            for constraint in session.run("CALL db.constraints"):
                session.run("DROP " + constraint[0])

    def _access_graph(self, graph_id, edge_label=None):
        """Access a graph of the hierarchy."""
        if edge_label is None:
            edge_label = "edge"
        g = Neo4jGraph(
            self._driver,
            node_label=graph_id, edge_label=edge_label)
        return g


class TypedNeo4jGraph(Neo4jHierarchy):
    """Class implementing two level hiearchy.

    This class encapsulates neo4j.v1.GraphDatabase object.
    It provides an interface for accessing typed graphs
    accommodated in the Neo4j DB. Our system is assumed to
    consist of two graphs (the data graph) and (the schema graph)
    connected with a graph homomorphisms (defining typing of
    the data graph by the schema graph).

    Attributes
    ----------
    _driver :  neo4j.v1.GraphDatabase
        Driver providing connection to a Neo4j database
    _graph_label : str
    _typing_label : str
    _graph_edge_label : str
    _graph_typing_label : str
    _schema_node_label : str
        Label of nodes inducing the schema graph.
    _data_node_label : str

    Top level represents a data instance, while bottom level represents
    a graphical schema.
    """

    def __init__(self,
                 uri=None, user=None, password=None,
                 driver=None,
                 schema_graph=None, data_graph=None,
                 typing=None, clear=False,
                 graph_label="graph",
                 typing_label="homomorphism",
                 graph_edge_label="edge",
                 graph_typing_label="typing",
                 schema_node_label="type", data_node_label="node"):
        """Initialize driver.

        Parameters:
        ----------
        uri : str, optional
            Uri of bolt listener, for example 'bolt://127.0.0.1:7687'
        user : str, optional
            Neo4j database user id
        password : str, optional
            Neo4j database password
        driver : neo4j.v1.direct.DirectDriver, optional
        graph_label : str, optional
            Label to use for skeleton nodes representing graphs.
        typing_label : str, optional
            Relation type to use for skeleton edges
            representing homomorphisms.
        graph_edge_label : str, optional
            Relation type to use for all graph edges.
        graph_typing_label : str, optional
            Relation type to use for edges encoding homomorphisms.
        schema_graph : dict, optional
            Schema graph to initialize the TypedGraph in JSON representation:
            {"nodes": <networkx_like_nodes>, "edges": <networkx_like_edges>}.
            By default is empty.
        data_graph : dict, optional
            Data graph to initialize the TypedGraph in JSON representation:
            {"nodes": <networkx_like_nodes>, "edges": <networkx_like_edges>}.
            By default is empty.
        typing : dict, optional
            Dictionary contaning typing of data nodes by schema nodes.
            By default is empty.
        """
        self._driver = GraphDatabase.driver(
            uri, auth=(user, password))

        if clear is True:
            self._clear()

        self._graph_label = "graph"
        self._typing_label = "homomorphism"
        self._relation_label = None

        self._graph_edge_label = "edge"
        self._graph_typing_label = "typing"
        self._graph_relation_label = "relation"

        self._schema_node_label = "type"
        self._data_node_label = "node"

        # create data/schema nodes
        if schema_graph is not None:
            if self._schema_node_label not in self.graphs():
                self.add_graph_from_data(
                    self._schema_node_label,
                    schema_graph["nodes"],
                    schema_graph["edges"])
            else:
                warnings.warn(
                    "The database already contains an instance of the "
                    "schema graph, ignoring provided node and edge list",
                    ReGraphWarning
                )

        if data_graph is not None:
            if self._data_node_label not in self.graphs():
                self.add_graph_from_data(
                    self._data_node_label,
                    data_graph["nodes"],
                    data_graph["edges"])
            else:
                warnings.warn(
                    "The database already contains an instance of the "
                    "data graph, ignoring provided node and edge list",
                    ReGraphWarning
                )

        if typing is not None:
            if (self._data_node_label,
                    self._schema_node_label) not in self.typings():
                self.add_typing(
                    self._data_node_label,
                    self._schema_node_label, typing)
            else:
                warnings.warn(
                    "The database already contains a typing of the "
                    "data by the schema, ignoring provided typing",
                    ReGraphWarning
                )

    def get_instances(self, schema_node):
        """Get all the instances of the schema node."""
        return keys_by_value(self.get_data_typing(), schema_node)

    def find_data_matching(self, pattern, pattern_typing=None, nodes=None):
        """Find matching of a pattern in the data graph.

        Parameters
        ----------
        pattern : Graph object
            A pattern to match
        pattern_typing : dict
            A dictionary that specifies a typing of a pattern,
            keys of the dictionary -- graph id that types a pattern, this graph
            should be among parents of the `graph_id` graph;
            values are mappings of nodes from pattern to the typing graph;
        nodes : iterable
            Subset of nodes where matching should be performed

        Returns
        -------
        instances : list of dict
            List of matched instances
        """
        schema_typing = None
        if pattern_typing is not None:
            schema_typing = {
                self._schema_node_label: pattern_typing
            }
        return self.find_matching(
            self._data_node_label,
            pattern,
            pattern_typing=schema_typing,
            nodes=nodes)

    def find_schema_matching(self, pattern, nodes=None):
        """Find matching of a pattern in the schema graph.

        Parameters
        ----------
        pattern : Graph object
            A pattern to match
        pattern_typing : dict
            A dictionary that specifies a typing of a pattern,
            keys of the dictionary -- graph id that types a pattern, this graph
            should be among parents of the `graph_id` graph;
            values are mappings of nodes from pattern to the typing graph;
        nodes : iterable
            Subset of nodes where matching should be performed

        Returns
        -------
        instances : list of dict
            List of matched instances
        """
        return self.find_matching(
            self._schema_node_label,
            pattern,
            nodes=nodes)

    def rewrite_data(self, rule, instance,
                     rhs_typing=None, strict=False):
        """Rewrite the data graph.

         Parameters
        ----------
        rule : regraph.rule.Rule
            Rule object to apply
        instance : dict, optional
            Dictionary containing an instance of the lhs of the rule in
            the data graph, by default, tries to construct the
            identity morphism of the nodes of the pattern
        rhs_typing : dict, optional
            Dictionary containing typing of the rhs by the schema.
        strict : bool, optional
            Rewriting is strict when propagation down is not allowed

        Raises
        ------
        HierarchyError
            If the graph is not in the database
        RewritingError
            If the provided p and rhs typing are inconsistent
        """
        if rhs_typing is None:
            rhs_typing = dict()

        res = self.rewrite(
            self._data_node_label,
            rule=rule,
            instance=instance,
            rhs_typing={
                self._schema_node_label: rhs_typing
            },
            strict=strict)
        return res

    def rewrite_schema(self, rule, instance=None,
                       data_typing=None, strict=False):
        """Rewrite the schema graph.

         Parameters
        ----------
        rule : regraph.rule.Rule
            Rule object to apply
        instance : dict, optional
            Dictionary containing an instance of the lhs of the rule in
            the schema graph, by default, tries to construct the
            identity morphism of the nodes of the pattern
        data_typing : dict, optional
            Dictionary containing typing of data by the
            interface of the rule.
        strict : bool, optional
            Rewriting is strict when propagation down is not allowed

        Raises
        ------
        HierarchyError
            If the graph is not in the database
        RewritingError
            If the provided p and rhs typing are inconsistent
        """
        p_typing = None
        if data_typing is not None:
            p_typing = {
                self._data_node_label: data_typing
            }

        return self.rewrite(
            self._schema_node_label,
            rule=rule,
            instance=instance,
            p_typing=p_typing,
            strict=strict)

    def relabel_schema_node(self, node_id, new_node_id):
        """Relabel a node in the schema."""
        self.relabel_graph_node(
            self._schema_node_label, node_id, new_node_id)

    def relabel_data_node(self, node_id, new_node_id):
        """Relabel a node in the data."""
        self.relabel_graph_node(self._data_node_label, node_id, new_node_id)

    def get_data(self):
        """Get the data graph object."""
        return self.get_graph(self._data_node_label)

    def get_schema(self):
        """Get the schema graph object."""
        return self.get_graph(self._schema_node_label)

    def get_data_nodes(self, data=False):
        """Get to nodes of the data."""
        data_g = self.get_data()
        return data_g.nodes(data=data)

    def get_data_edges(self, data=False):
        """Get the edges of the data."""
        data_g = self.get_data()
        return data_g.edges(data=data)

    def get_schema_nodes(self, data=False):
        """Get the nodes of the schema."""
        schema = self.get_schema()
        return schema.nodes(data=data)

    def get_schema_edges(self, data=False):
        """Get the edges of the schema."""
        schema = self.get_schema()
        return schema.edges(data=data)

    def get_data_typing(self):
        """Get the typing of the data."""
        return self.get_typing(
            self._data_node_label, self._schema_node_label)

    def get_node_type(self, node_id):
        """Get the type of a node in the data."""
        t = self.node_type(self._data_node_label, node_id)
        return t[self._schema_node_label]

    def get_data_node(self, node_id):
        """Get the attributes of a data node."""
        g = self.get_graph(self._data_node_label)
        return g.get_node(node_id)

    def get_schema_node(self, node_id):
        """Get the attributes of a schema node."""
        g = self.get_graph(self._schema_node_label)
        return g.get_node(node_id)

    # Set of utils for type-respecting transformations

    def remove_data_node(self, node_id):
        """Remove a data node."""
        g = self.get_graph(self._data_node_label)
        g.remove_node(node_id)

    def remove_data_edge(self, source, target):
        """Remove a data edge."""
        g = self.get_graph(self._data_node_label)
        g.remove_edge(source, target)

    def remove_data_node_attrs(self, node_id, attrs):
        """Remove the attributes of a data node."""
        g = self.get_data()
        g.remove_node_attrs(node_id, attrs)

    def add_data_node(self, node_id, typing, attrs=None):
        """Add a data node typed by the specified schema node."""
        rule = Rule.from_transform(NXGraph())
        rule.inject_add_node(node_id, attrs)
        rhs_typing = {node_id: typing}
        rhs_instance = self.rewrite_data(
            rule, {}, rhs_typing=rhs_typing, strict=True)
        return rhs_instance[node_id]

    def add_data_edge(self, source, target, attrs=None):
        """Add a data edge."""
        schema_s = self.get_node_type(source)
        schema_t = self.get_node_type(target)
        schema = self.get_schema()

        if (schema_s, schema_t) not in schema.edges():
            raise RewritingError(
                "Cannot add an edge '{}->{}': ".format(
                    source, target) +
                "edge '{}->{}' is not allowed by the schema".format(
                    schema_s, schema_t))
        else:
            normalize_attrs(attrs)
            schema_attrs = schema.get_edge(schema_s, schema_t)
            if not valid_attributes(attrs, schema_attrs):
                raise RewritingError(
                    "Cannot add attributes {} to '{}->{}': ".format(
                        attrs, source, target) +
                    "the typing schema edge '{}->{}' does not allow ".format(
                        schema_s, schema_t) +
                    "these attributes (allowed {})".format(schema_attrs))
        data = self.get_data()
        data.add_edge(source, target, attrs)
        return

    def add_data_node_attrs(self, node_id, attrs):
        """Add the attributes to a data node."""
        normalize_attrs(attrs)
        schema_node = self.get_node_type(node_id)
        schema_attrs = self.get_schema_node(schema_node)

        if not valid_attributes(attrs, schema_attrs):
            raise RewritingError(
                "Cannot add attributes {} to '{}': ".format(
                    attrs, node_id) +
                "the typing schema node '{}' does not allow ".format(
                    schema_node) +
                "these attributes (allowed {})".format(schema_attrs))
        else:
            g = self.get_data()
            g.add_node_attrs(node_id, attrs)

    def add_data_edge_attrs(self, source, target, attrs):
        """Add a data edge."""
        schema_s = self.get_node_type(source)
        schema_t = self.get_node_type(target)
        schema = self.get_schema()

        normalize_attrs(attrs)
        schema_attrs = schema.get_edge(schema_s, schema_t)
        if not valid_attributes(attrs, schema_attrs):
            raise RewritingError(
                "Cannot add attributes {} to '{}->{}': ".format(
                    attrs, source, target) +
                "the typing schema edge '{}->{}' does not allow ".format(
                    schema_s, schema_t) +
                "these attributes (allowed {})".format(schema_attrs))
        else:
            data = self.get_data()
            data.add_edge_attrs(source, target, attrs)
        return

    def merge_data_nodes(self, node_list):
        """Merge data nodes."""
        data_typing = self.get_data_typing()
        schema_nodes = set([
            data_typing[n] for n in node_list
        ])
        if len(schema_nodes) > 1:
            raise RewritingError(
                "Cannot merge the data nodes {} ".format(node_list) +
                "of different types (i.e. {})".format(schema_nodes)
            )

        pattern = NXGraph()
        pattern.add_nodes_from(node_list)
        rule = Rule.from_transform(pattern)
        merged_node = rule.inject_merge_nodes(node_list)
        rhs_instance = self.rewrite_data(rule, instance=None, strict=True)
        return rhs_instance[merged_node]

    def add_schema_node(self, node_id, attrs=None):
        """Add a schema node."""
        g = self.get_graph(self._schema_node_label)
        g.add_node(node_id, attrs)

    def add_schema_edge(self, source, target, attrs=None):
        """Add a schema node."""
        g = self.get_graph(self._schema_node_label)
        g.add_edge(source, target, attrs)

    def add_schema_node_attrs(self, node_id, attrs):
        """Add the attributes of a schema node."""
        g = self.get_graph(self._schema_node_label)
        g.add_node_attrs(node_id, attrs)

    def remove_schema_node(self, node_id):
        """Remove a schema node."""
        data_typing = self.get_data_typing()
        instances = keys_by_value(data_typing, node_id)

        if len(instances) > 0:
            raise RewritingError(
                "Cannot remove '{}' from the schema: ".format(
                    node_id) +
                "'{}' has instances in the data ({})".format(
                    node_id, instances))
        else:
            g = self.get_schema()
            g.remove_node(node_id)

    def remove_schema_node_attrs(self, node_id, attrs):
        """Remove a schema node."""
        data_typing = self.get_data_typing()
        instances = keys_by_value(data_typing, node_id)

        if len(instances) > 0:
            for instance in instances:
                instance_attrs = self.get_data_node(instance)
                if valid_attributes(attrs, instance_attrs):
                    raise RewritingError(
                        "Cannot remove attributes {} from '{}' in the schema: ".format(
                            attrs, node_id) +
                        "the instance '{}' in the data has attributes {}".format(
                            instance, instance_attrs))

        normalize_attrs(attrs)
        g = self.get_schema()
        g.remove_node_attrs(node_id, attrs)

    def remove_schema_edge(self, source, target):
        """Remove a schema node."""
        data_typing = self.get_data_typing()
        instances_s = keys_by_value(data_typing, source)
        instances_t = keys_by_value(data_typing, target)
        data = self.get_data()
        for s in instances_s:
            for t in instances_t:
                if (s, t) in data.edges():
                    raise RewritingError(
                        "Cannot remove '{}->{}' from the schema: ".format(
                            source, target) +
                        "'{}->{}' has an instance in the data ('{}->{}'')".format(
                            source, target, s, t))
        g = self.get_schema()
        g.remove_edge(source, target)

    def remove_schema_edge_attrs(self, source, target, attrs):
        """Remove a schema node."""
        data_typing = self.get_data_typing()
        instances_s = keys_by_value(data_typing, source)
        instances_t = keys_by_value(data_typing, target)
        data = self.get_data()
        normalize_attrs(attrs)
        for s in instances_s:
            for t in instances_t:
                if (s, t) in data.edges():
                    data_attrs = data.get_edge(source, target)
                    if valid_attributes(attrs, data_attrs):
                        raise RewritingError(
                            "Cannot remove attributes {} from '{}->{}' ".format(
                                attrs, source, target) +
                            "in the schema: the instance '{}->{}' ".format(
                                s, t) +
                            "in the data has attributes {}".format(
                                data_attrs))
        g = self.get_schema()
        g.remove_edge_attrs(source, target, attrs)

    def clone_schema_node(self, node, data_typing):
        """Clone a schema node."""
        pattern = NXGraph()
        pattern.add_nodes_from(node)
        rule = Rule.from_transform(pattern)
        _, rhs_clone = rule.inject_clone_node(node)
        rhs_instance = self.rewrite_schema(
            rule, instance=None, data_typing=data_typing, strict=True)
        return rhs_instance[rhs_clone]
