"""."""
import itertools
import json
import os
import networkx as nx
from networkx.algorithms import isomorphism
import warnings

from abc import ABC, abstractmethod

from regraph.category_utils import (pullback_complement,
                                    pushout)
from regraph.exceptions import (ReGraphError,
                                GraphError,
                                GraphAttrsWarning,
                                )
from regraph.utils import (load_nodes_from_json,
                           load_edges_from_json,
                           generate_new_id,
                           normalize_attrs,
                           safe_deepcopy_dict,
                           set_attrs,
                           add_attrs,
                           remove_attrs,
                           merge_attributes,
                           valid_attributes
                           )


class Graph(ABC):
    """Abstract class for graph objects in ReGraph."""

    @abstractmethod
    def nodes(self):
        """Return the list of nodes."""
        pass

    @abstractmethod
    def edges(self):
        """Return the list of edges."""
        pass

    @abstractmethod
    def get_node(self, n):
        """Get node attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph or regraph.neo4j.Neo4jGraph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        pass

    @abstractmethod
    def get_edge(self, s, t):
        """Get edge attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        pass

    @abstractmethod
    def add_node(self, node_id, attrs=None):
        """Abstract method for adding a node.

        Parameters
        ----------
        node_id : hashable
            Prefix that is prepended to the new unique name.
        attrs : dict, optional
            Node attributes.
        """
        pass

    @abstractmethod
    def remove_node(self, node_id):
        """Remove node.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node_id : hashable, node to remove.
        """
        pass

    @abstractmethod
    def add_edge(self, s, t, attrs=None, **attr):
        """Add an edge to a graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dict
            Edge attributes.
        """
        pass

    @abstractmethod
    def remove_edge(self, source_id, target_id):
        """Remove edge from the graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        pass

    @abstractmethod
    def update_node_attrs(self, node_id, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        node_id : hashable, node to update.
        attrs : dict
            New attributes to assign to the node

        """
        pass

    @abstractmethod
    def update_edge_attrs(self, s, t, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        s : hashable, source node of the edge to update.
        t : hashable, target node of the edge to update.
        attrs : dict
            New attributes to assign to the node

        """
        pass

    @abstractmethod
    def in_edges(self, node_id):
        """Return the set of in-coming edges."""
        pass

    @abstractmethod
    def out_edges(self, node_id):
        """Return the set of out-going edges."""
        pass

    @abstractmethod
    def successors(self, node_id):
        """Return the set of successors."""
        pass

    @abstractmethod
    def predecessors(self, node_id):
        """Return the set of predecessors."""
        pass

    @abstractmethod
    def find_matching(self, pattern, nodes=None):
        """Find matching of a pattern in a graph."""
        pass

    def add_nodes_from(self, node_list):
        """Add nodes from a node list.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node_list : iterable
            Iterable containing a collection of nodes, optionally,
            with their attributes
        """
        for n in node_list:
            if type(n) != str:
                try:
                    node_id, node_attrs = n
                    self.add_node(node_id, node_attrs)
                except (TypeError, ValueError):
                    self.add_node(n)
            else:
                self.add_node(n)

    def add_edges_from(self, edge_list):
        """Add edges from an edge list.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        edge_list : iterable
            Iterable containing a collection of edges, optionally,
            with their attributes
        """
        for e in edge_list:
            if len(e) == 2:
                self.add_edge(e[0], e[1])
            elif len(e) == 3:
                self.add_edge(e[0], e[1], e[2])
            else:
                raise ReGraphError(
                    "Was expecting 2 or 3 elements per tuple, got %s." %
                    str(len(e))
                )

    def exists_edge(self, s, t):
        """Check if an edge exists.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        return((s, t) in self.edges())

    def set_node_attrs(self, node_id, attrs, normalize=True, update=True):
        """Abstract method for setting node attrs.

        This sets key/values specified in the input attrs, but
        does not change other the values of other keys.
        """
        if node_id not in self.nodes():
            raise GraphError("Node '{}' does not exist!".format(node_id))

        node_attrs = safe_deepcopy_dict(self.get_node(node_id))
        set_attrs(node_attrs, attrs, normalize, update)
        self.update_node_attrs(node_id, node_attrs)

    def add_node_attrs(self, node, attrs):
        """Add new attributes to a node.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node : hashable
            Id of a node to add attributes to.
        attrs : dict
            Attributes to add.

        """
        if node not in self.nodes():
            raise GraphError("Node '{}' does not exist!".format(node))

        node_attrs = safe_deepcopy_dict(self.get_node(node))
        add_attrs(node_attrs, attrs, normalize=True)
        self.update_node_attrs(node, node_attrs)

    def remove_node_attrs(self, node_id, attrs):
        """Remove attrs of a node specified by attrs_dict.

        Parameters
        ----------
        node_id : hashable
            Node whose attributes to remove.
        attrs : dict
            Dictionary with attributes to remove.

        Raises
        ------
        GraphError
            If a node with the specified id does not exist.
        """
        if node_id not in self.nodes():
            raise GraphError("Node '%s' does not exist!" % str(node_id))
        elif attrs is None:
            warnings.warn(
                "You want to remove attrs from '{}' with an empty attrs_dict!".format(
                    node_id), GraphAttrsWarning
            )

        node_attrs = safe_deepcopy_dict(self.get_node(node_id))
        remove_attrs(node_attrs, attrs, normalize=True)
        self.update_node_attrs(node_id, node_attrs)

    def set_edge_attrs(self, s, t, attrs, normalize=True, update=True):
        """Set edge attrs.

        Parameters
        ----------
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dictionary
            Dictionary with attributes to set.

        Raises
        ------
        GraphError
            If an edge between `s` and `t` does not exist.
        """
        if not self.exists_edge(s, t):
            raise GraphError(
                "Edge {}->{} does not exist".format(s, t))

        edge_attrs = safe_deepcopy_dict(self.get_edge(s, t))
        set_attrs(edge_attrs, attrs, normalize, update)
        self.update_edge_attrs(s, t, edge_attrs)

    def set_edge(self, s, t, attrs, normalize=True, update=True):
        """Set edge attrs.

        Parameters
        ----------
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dictionary
            Dictionary with attributes to set.

        Raises
        ------
        GraphError
            If an edge between `s` and `t` does not exist.
        """
        self.set_edge_attrs(s, t, attrs, normalize, update)

    def add_edge_attrs(self, s, t, attrs):
        """Add attributes of an edge in a graph.

        Parameters
        ----------
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dict
            Dictionary with attributes to remove.

        Raises
        ------
        GraphError
            If an edge between `s` and `t` does not exist.
        """
        if not self.exists_edge(s, t):
            raise GraphError(
                "Edge {}->{} does not exist".format(s, t))

        edge_attrs = safe_deepcopy_dict(self.get_edge(s, t))
        add_attrs(edge_attrs, attrs, normalize=True)
        self.update_edge_attrs(s, t, edge_attrs)

    def remove_edge_attrs(self, s, t, attrs):
        """Remove attrs of an edge specified by attrs.

        Parameters
        ----------
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dict
            Dictionary with attributes to remove.

        Raises
        ------
        GraphError
            If an edge between `s` and `t` does not exist.
        """
        if not self.exists_edge(s, t):
            raise GraphError(
                "Edge {}->{} does not exist".format(s, t))

        edge_attrs = safe_deepcopy_dict(self.get_edge(s, t))
        remove_attrs(edge_attrs, attrs, normalize=True)
        self.update_edge_attrs(s, t, edge_attrs)

    def clone_node(self, node_id, name=None):
        """Clone node.

        Create a new node, a copy of a node with `node_id`, and reconnect it
        with all the adjacent nodes of `node_id`.

        Parameters
        ----------
        node_id : id of a node to clone.
        name : id for the clone, optional
            If is not specified, new id will be generated.

        Returns
        -------
        new_node : hashable, clone's id

        Raises
        ------
        GraphError
            If node wiht `node_id` does not exists or a node with
            `name` (clone's name) already exists.

        """
        if node_id not in self.nodes():
            raise GraphError("Node '{}' does not exist!".format(node_id))

        # generate new name for a clone
        if name is None:
            i = 1
            new_node = str(node_id) + str(i)
            while new_node in self.nodes():
                i += 1
                new_node = str(node_id) + str(i)
        else:
            if name in self.nodes():
                raise GraphError("Node '{}' already exists!".format(name))
            else:
                new_node = name

        self.add_node(new_node, **safe_deepcopy_dict(self.get_node(node_id)))

        # Connect all the edges
        self.add_edges_from(
            set([(n, new_node) for n, _ in self.in_edges(node_id)
                 if (n, new_node) not in self.edges()]))
        self.add_edges_from(
            set([(new_node, n) for _, n in self.out_edges(node_id)
                 if (new_node, n) not in self.edges()]))

        # Copy the attributes of the edges
        for s, t in self.in_edges(node_id):
            self.set_edge(
                s, new_node,
                safe_deepcopy_dict(self.get_edge(s, t)))
        for s, t in self.out_edges(node_id):
            self.set_edge(
                new_node, t,
                safe_deepcopy_dict(self.get_edge(s, t)))
        return new_node

    def relabel_node(self, node_id, new_id):
        """Relabel a node in the graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node_id : id of a node to relabel.
        new_id : hashable, new label of a node.
        """
        self.clone_node(node_id, new_id)
        self.remove_node(node_id)

    def merge_nodes(self, nodes, node_id=None, method="union", edge_method="union"):
        """Merge a list of nodes.

        Parameters
        ----------

        graph : nx.(Di)Graph
        nodes : iterable
            Collection of node id's to merge.
        node_id : hashable, optional
            Id of a new node corresponding to the result of merge.
        method : optional
            Method of node attributes merge: if `"union"` the resulting node
            will contain the union of all attributes of the merged nodes,
            if `"intersection"`, the resulting node will contain their
            intersection. Default value is `"union"`.
        edge_method : optional
            Method of edge attributes merge: if `"union"` the edges that were
            merged will contain the union of all attributes,
            if `"intersection"` -- their ntersection. Default value is `"union"`.
        """
        if len(nodes) == 1:
            if node_id is not None:
                self.relabel_node(nodes[0], node_id)
        elif len(nodes) > 1:

            if method is None:
                method = "union"

            if edge_method is None:
                method = "union"

            # Generate name for new node
            if node_id is None:
                node_id = "_".join(sorted([str(n) for n in nodes]))
                if node_id in self.nodes():
                    node_id = self.generate_new_node_id(node_id)

            elif node_id in self.nodes() and (node_id not in nodes):
                raise GraphError(
                    "New name for merged node is not valid: "
                    "node with name '%s' already exists!" % node_id
                )
            # Merge data attached to node according to the method specified
            # restore proper connectivity
            if method == "union":
                attr_accumulator = {}
            elif method == "intersection":
                attr_accumulator = safe_deepcopy_dict(
                    self.get_node(nodes[0]))
            else:
                raise ReGraphError("Merging method '{}' is not defined!".format(
                    method))

            self_loop = False
            self_loop_attrs = {}

            source_nodes = set()
            target_nodes = set()

            source_dict = {}
            target_dict = {}

            for node in nodes:
                attr_accumulator = merge_attributes(
                    attr_accumulator, self.get_node(node), method)

                in_edges = self.in_edges(node)
                out_edges = self.out_edges(node)

                # manage self loops
                for s, t in in_edges:
                    if s in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = self.get_edge(s, t)
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                self.get_edge(s, t),
                                edge_method)

                for s, t in out_edges:
                    if t in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = self.get_edge(s, t)
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                self.get_edge(s, t),
                                edge_method)

                source_nodes.update(
                    [n if n not in nodes else node_id
                     for n, _ in in_edges])
                target_nodes.update(
                    [n if n not in nodes else node_id
                     for _, n in out_edges])

                for edge in in_edges:
                    if not edge[0] in source_dict.keys():
                        attrs = self.get_edge(edge[0], edge[1])
                        source_dict.update({edge[0]: attrs})
                    else:
                        attrs = merge_attributes(
                            source_dict[edge[0]],
                            self.get_edge(edge[0], edge[1]),
                            edge_method)
                        source_dict.update({edge[0]: attrs})

                for edge in out_edges:
                    if not edge[1] in target_dict.keys():
                        attrs = self.get_edge(edge[0], edge[1])
                        target_dict.update({edge[1]: attrs})
                    else:
                        attrs = merge_attributes(
                            target_dict[edge[1]],
                            self.get_edge(edge[0], edge[1]),
                            edge_method)
                        target_dict.update({edge[1]: attrs})

            self.add_node(node_id, attr_accumulator)

            if self_loop:
                self.add_edges_from([(node_id, node_id)])
                self.set_edge(node_id, node_id, self_loop_attrs)
            for n in source_nodes:
                if not self.exists_edge(n, node_id):
                    self.add_edge(n, node_id)
            for n in target_nodes:
                if not self.exists_edge(node_id, n):
                    self.add_edge(node_id, n)

            # Attach accumulated attributes to edges
            for node, attrs in source_dict.items():
                if node not in nodes:
                    self.set_edge(node, node_id, attrs)
            for node, attrs in target_dict.items():
                if node not in nodes:
                    self.set_edge(node_id, node, attrs)

            return node_id
        else:
            raise ReGraphError("Cannot merge an empty set of nodes!")

    def copy_node(self, node_id):
        """Copy node.

        Create a copy of a node in a graph. A new id for the copy is
        generated by regraph.primitives.unique_node_id.

        Parameters
        ----------
        node_id : hashable, node to copy.

        Returns
        -------
        new_name
            Id of the copy node.

        """
        new_name = self.generate_new_node_id(node_id)
        attrs = self.get_node(node_id)
        self.add_node(new_name, attrs)
        return new_name

    def relabel_nodes(self, mapping):
        """Relabel graph nodes inplace given a mapping.

        Similar to networkx.relabel.relabel_nodes:
        https://networkx.github.io/documentation/development/_modules/networkx/relabel.html

        Parameters
        ----------
        mapping: dict
            A dictionary with keys being old node ids and their values
            being new id's of the respective nodes.

        Raises
        ------
        ReGraphError
            If new id's do not define a set of distinct node id's.

        """
        unique_names = set(mapping.values())
        if len(unique_names) != len(self.nodes()):
            raise ReGraphError(
                "Attempt to relabel nodes failed: the IDs are not unique!")

        temp_names = {}
        # Relabeling of the nodes: if at some point new ID conflicts
        # with already existing ID - assign temp ID
        for key, value in mapping.items():
            if key != value:
                if value not in self.nodes():
                    new_name = value
                else:
                    new_name = self.generate_new_node_id(value)
                    temp_names[new_name] = value
                self.relabel_node(key, new_name)
        # Relabeling the nodes with the temp ID to their new IDs
        for key, value in temp_names:
            if key != value:
                self.relabel_node(key, value)
        return

    def generate_new_node_id(self, basename):
        """Generate new unique node identifier."""
        return generate_new_id(self.nodes(), basename)

    def filter_edges_by_attributes(self, attr_key, attr_cond):
        """Filter graph edges by attributes.

        Removes all the edges of the graph (inplace) that do not
        satisfy `attr_cond`.

        Parameters
        ----------
        attrs_key : attribute key
        attrs_cond : callable
            Condition for an attribute to satisfy: callable that returns
            `True` if condition is satisfied, `False` otherwise.

        """
        for (s, t) in self.edges():
            edge_attrs = self.get_edge(s, t)
            if (attr_key not in edge_attrs.keys() or
                    not attr_cond(edge_attrs[attr_key])):
                self.remove_edge(s, t)

    def graph_to_json(self):
        """Create a JSON representation of a graph."""
        j_data = {"edges": [], "nodes": []}
        # dump nodes
        for node in self.nodes():
            node_data = {}
            node_data["id"] = node
            node_attrs = self.get_node(node)
            if node_attrs is not None:
                attrs = {}
                for key, value in node_attrs.items():
                    attrs[key] = value.to_json()
                node_data["attrs"] = attrs
            j_data["nodes"].append(node_data)

        # dump edges
        for s, t in self.edges():
            edge_data = {}
            edge_data["from"] = s
            edge_data["to"] = t
            edge_attrs = self.get_edge(s, t)
            if edge_attrs is not None:
                attrs = {}
                for key, value in edge_attrs.items():
                    attrs[key] = value.to_json()
                edge_data["attrs"] = attrs
            j_data["edges"].append(edge_data)
        return j_data

    def graph_to_d3_json(self,
                         attrs=True,
                         node_attrs_to_attach=None,
                         edge_attrs_to_attach=None,
                         nodes=None):
        """Create a JSON representation of a graph."""
        j_data = {"links": [], "nodes": []}
        if nodes is None:
            nodes = self.nodes()
        # dump nodes
        for node in nodes:
            node_data = {}
            node_data["id"] = node
            if attrs:
                node_attrs = self.get_node(node)
                normalize_attrs(node_attrs)
                attrs_json = dict()
                for key, value in node_attrs.items():
                    attrs_json[key] = value.to_json()
                node_data["attrs"] = attrs_json
            else:
                node_attrs = self.get_node(node)
                if node_attrs_to_attach is not None:
                    for key in node_attrs_to_attach:
                        if key in node_attrs.keys():
                            node_data[key] = list(node_attrs[key])
            j_data["nodes"].append(node_data)

        # dump edges
        for s, t in self.edges():
            if s in nodes and t in nodes:
                edge_data = {}
                edge_data["source"] = s
                edge_data["target"] = t
                if attrs:
                    edge_attrs = self.get_edge(s, t)
                    normalize_attrs(edge_attrs)
                    attrs_json = dict()
                    for key, value in edge_attrs.items():
                        attrs_json[key] = value.to_json()
                    edge_data["attrs"] = attrs_json
                else:
                    if edge_attrs_to_attach is not None:
                        for key in edge_attrs_to_attach:
                            edge_attrs = self.get_edge(s, t)
                            if key in edge_attrs.keys():
                                edge_data[key] = list(edge_attrs[key])
                j_data["links"].append(edge_data)

        return j_data

    def export_graph(self, filename):
        """Export graph to JSON file.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        filename : str
            Name of the file to save the json serialization of the graph


        """
        with open(filename, 'w') as f:
            j_data = self.graph_to_json()
            json.dump(j_data, f)
        return

    @classmethod
    def networkx_from_json(cls, j_data, directed=True):
        """Create a NetworkX graph from a json-like dictionary."""
        graph = cls()
        graph.add_nodes_from(load_nodes_from_json(j_data))
        graph.add_edges_from(load_edges_from_json(j_data))
        return graph

    @classmethod
    def load_networkx_graph(cls, filename, directed=True):
        """Load a NetworkX graph from a JSON file.

        Create a `networkx.(Di)Graph` object from
        a JSON representation stored in a file.

        Parameters
        ----------
        filename : str
            Name of the file to load the json serialization of the graph
        directed : bool, optional
            `True` if the graph to load is directed, `False` otherwise.
            Default value `True`.

        Returns
        -------
        nx.(Di)Graph object

        Raises
        ------
        ReGraphError
            If was not able to load the file

        """
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                j_data = json.loads(f.read())
                return cls.networkx_from_json(j_data, directed)
        else:
            raise ReGraphError(
                "Error loading graph: file '%s' does not exist!" %
                filename
            )


class NetworkXGraph(Graph):
    """Wrapper for NetworkX directed graphs."""

    node_dict_factory = dict
    adj_dict_factory = dict

    def __init___(self, incoming_graph_data=None, **attr):
        """Initialize NetworkX graph."""
        self.node_dict_factory = ndf = self.node_dict_factory
        self.adj_dict_factory = adf = self.adj_dict_factory

        super().__init__()
        self._graph = nx.DiGraph()
        self.node = ndf()
        self.adj = adf()

    def nodes(self):
        """Return the list of nodes."""
        return self._graph.nodes()

    def edges(self):
        """Return the list of edges."""
        return self._graph.edges()

    def get_node(self, n):
        """Get node attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph or regraph.neo4j.Neo4jGraph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        return self._graph.node[n]

    def get_edge(self, s, t):
        """Get edge attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        self._graph.adj[s][t]

    def add_node(self, node_id, attrs=None):
        """Abstract method for adding a node.

        Parameters
        ----------
        node_id : hashable
            Prefix that is prepended to the new unique name.
        attrs : dict, optional
            Node attributes.
        """
        if attrs is None:
            new_attrs = dict()
        else:
            new_attrs = safe_deepcopy_dict(attrs)
            normalize_attrs(new_attrs)
        if node_id not in self.nodes():
            self._graph.add_node(node_id)
            self.node[node_id] = dict()
            for k, v in new_attrs.items():
                self._graph.node[node_id][k] = v
                self.node[node_id][k] = v

        else:
            raise GraphError("Node '%s' already exists!" % node_id)

    def remove_node(self, node_id):
        """Remove node.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node_id : hashable, node to remove.
        """
        if node_id in self.nodes():
            self._graph.remove_node(node_id)
            del self.node[node_id]
            for k, v in self.adj.items():
                if k == node_id:
                    del self.adj[k]
                if v == node_id:
                    del self.adj[k][v]
        else:
            raise GraphError("Node %s does not exist!" % str(node_id))
        return

    def add_edge(self, s, t, attrs=None, **attr):
        """Add an edge to a graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dict
            Edge attributes.
        """
        if attrs is None:
            attrs = attr
        else:
            try:
                attrs.update(attr)
            except AttributeError:
                raise ReGraphError(
                    "The attr_dict argument must be a dictionary."
                )

        new_attrs = safe_deepcopy_dict(attrs)
        if s not in self.nodes():
            raise GraphError("Node '{}' does not exist!".format(s))
        if t not in self.nodes():
            raise GraphError("Node '{}' does not exist!".format(t))
        normalize_attrs(new_attrs)

        if (s, t) in self.edges():
            raise GraphError(
                "Edge '{}'->'{}' already exists!".format(s, t))
        self._graph.add_edge(s, t, **new_attrs)
        if s in self.adj.keys():
            self.adj[s][t] = new_attrs
        else:
            self.adj[s] = {t: new_attrs}

    def remove_edge(self, s, t):
        """Remove edge from the graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        if (s, t) not in self.edges():
            raise GraphError(
                "Edge '{}->{}' does not exist!".format(s, t))
        self._graph.remove_edge(s, t)
        del self.adj[s][t]

    def update_node_attrs(self, node_id, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        node_id : hashable, node to update.
        attrs : dict
            New attributes to assign to the node

        """
        new_attrs = safe_deepcopy_dict(attrs)
        if node_id not in self.nodes():
            raise GraphError(
                "Node '{}' does not exist!".format(node_id))
        elif new_attrs is None:
            warnings.warn(
                "You want to update '{}' attrs with an empty attrs_dict!".format(
                    node_id),
                GraphAttrsWarning
            )
        else:
            if normalize is True:
                normalize_attrs(new_attrs)
            attrs_to_remove = set()
            for k in self._graph.node[node_id].keys():
                if k not in new_attrs.keys():
                    attrs_to_remove.add(k)
            self._graph.add_node(node_id, **new_attrs)
            self.node[node_id] = new_attrs
            for k in attrs_to_remove:
                del self._graph.node[node_id][k]
                del self.node[node_id][k]

    def update_edge_attrs(self, s, t, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        s : hashable, source node of the edge to update.
        t : hashable, target node of the edge to update.
        attrs : dict
            New attributes to assign to the node

        """
        if not self._graph.has_edge(s, t):
            raise GraphError("Edge '{}->{}' does not exist!".format(
                             s, t))
        elif attrs is None:
            warnings.warn(
                "You want to update '{}->{}' attrs with an empty attrs_dict".format(
                    s, t), GraphAttrsWarning
            )
        else:
            if normalize is True:
                normalize_attrs(attrs)
            attrs_to_remove = set()
            for k in self._graph.adj[s][t].keys():
                if k not in attrs.keys():
                    attrs_to_remove.add(k)
            self._graph.add_edge(s, t, **attrs)
            self.adj[s][t] = attrs
            for k in attrs_to_remove:
                del self._graph.adj[s][t]
                del self.adj[s][t]

    def in_edges(self, node_id):
        """Return the set of in-coming edges."""
        return self._graph.in_edges(node_id)

    def out_edges(self, node_id):
        """Return the set of out-going edges."""
        return self._graph.out_edges(node_id)

    def successors(self, node_id):
        """Return the set of successors."""
        return self._graph.successors(node_id)

    def predecessors(self, node_id):
        """Return the set of predecessors."""
        return self._graph.predecessors(node_id)

    def get_relabeled_graph(self, mapping):
        """Return a graph with node labeling specified in the mapping.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        mapping: dict
            A dictionary with keys being old node ids and their values
            being new id's of the respective nodes.

        Returns
        -------
        g : networkx.(Di)Graph
            New graph object isomorphic to the `graph` with the relabled nodes.

        Raises
        ------
        ReGraphError
            If new id's do not define a set of distinct node id's.


        See also
        --------
        regraph.primitives.relabel_nodes
        """
        g = nx.DiGraph()
        old_nodes = set(mapping.keys())

        for old_node in old_nodes:
            try:
                new_node = mapping[old_node]
            except KeyError:
                continue
            try:
                g.add_node(
                    new_node,
                    **self.get_node(old_node))
            except KeyError:
                raise GraphError("Node '%s' does not exist!" % old_node)

        new_edges = list()
        attributes = dict()
        for s, t in self.edges():
            new_edges.append((
                mapping[s],
                mapping[t]))
            attributes[(mapping[s], mapping[t])] =\
                self.get_edge(s, t)

        g.add_edges_from(new_edges)
        for s, t in g.edges():
            g.adj[s][t] = attributes[(s, t)]
        return g

    def find_matching(self, pattern, nodes=None):
        """Find matching of a pattern in a graph.

        This function takes as an input a graph and a pattern graph, optionally,
        it also takes a collection of nodes specifying the subgraph of the
        original graph, where the matching should be searched in, then it
        searches for a matching of the pattern inside of the graph (or induced
        subragh), which corresponds to solving subgraph matching problem.
        The matching is defined by a map from the nodes of the pattern
        to the nodes of the graph such that:

        * edges are preserved, i.e. if there is an edge between nodes `n1` and `n2`
          in the pattern, there is an edge between the nodes of the graph that
          correspond to the image of `n1` and `n2`, moreover, the attribute
          dictionary of the edge between `n1` and `n2` is the subdictiotary of
          the edge it corresponds to in the graph;
        * the attribute dictionary of a pattern node is a subdictionary of
          its image in the graph;

        Uses `networkx.isomorphism.(Di)GraphMatcher` class, which implements
        subgraph matching algorithm.

        Parameters
        ----------
        graph : nx.(Di)Graph
        pattern : nx.(Di)Graph
            Pattern graph to search for
        nodes : iterable, optional
            Subset of nodes to search for matching

        Returns
        -------
        instances : list of dict's
            List of instances of matching found in the graph, every instance
            is represented with a dictionary where keys are nodes of the
            pattern, and values are corresponding nodes of the graph.

        """
        if nodes is not None:
            g = self._graph.subgraph(nodes)
        else:
            g = self._graph

        labels_mapping = dict([(n, i + 1) for i, n in enumerate(g.nodes())])
        g = self.get_relabeled_graph(g, labels_mapping)
        matching_nodes = set()

        # find all the nodes matching the nodes in pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if valid_attributes(
                    pattern.node[pattern_node],
                        g.node[node]):
                    matching_nodes.add(node)
        reduced_graph = g.subgraph(matching_nodes)
        instances = []
        isomorphic_subgraphs = []
        for sub_nodes in itertools.combinations(reduced_graph.nodes(),
                                                len(pattern.nodes())):
            subg = reduced_graph.subgraph(sub_nodes)
            for edgeset in itertools.combinations(subg.edges(),
                                                  len(pattern.edges())):
                if g.is_directed():
                    edge_induced_graph = nx.DiGraph(list(edgeset))
                    edge_induced_graph.add_nodes_from(
                        [n for n in subg.nodes()
                         if n not in edge_induced_graph.nodes()])
                    matching_obj = isomorphism.DiGraphMatcher(
                        pattern, edge_induced_graph)
                    for isom in matching_obj.isomorphisms_iter():
                        isomorphic_subgraphs.append((subg, isom))
                else:
                    edge_induced_graph = nx.Graph(edgeset)
                    edge_induced_graph.add_nodes_from(
                        [n for n in subg.nodes()
                         if n not in edge_induced_graph.nodes()])
                    matching_obj = isomorphism.GraphMatcher(
                        pattern, edge_induced_graph)
                    for isom in matching_obj.isomorphisms_iter():
                        isomorphic_subgraphs.append((subg, isom))

        for subgraph, mapping in isomorphic_subgraphs:
            # check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if not valid_attributes(
                    pattern.node[pattern_node],
                        subgraph.node[node]):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.adj[edge[0]][edge[1]]
                    target_attrs = subgraph.adj[
                        mapping[edge[0]]][mapping[edge[1]]]
                    if not valid_attributes(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # bring back original labeling
        inverse_mapping = dict(
            [(value, key) for key, value in labels_mapping.items()]
        )
        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]

        return instances

    def rewrite(self, rule, instance=None):
        """Perform graph rewriting with the rule.

        Parameters
        ----------
        rule : regraph.rules.Rule
        instance : dict
            Instance of the `lhs` pattern in the graph
            defined by a dictionary where keys are nodes
            of `lhs` and values are nodes of the graph.

        Returns
        -------
        rhs_g_prime : dict
            Matching of the `rhs` in `g_prime`, a dictionary,
            where keys are nodes of `rhs` and values are
            nodes of `g_prime`.

        """
        if instance is None:
            instance = {
                n: n for n in rule.lhs.nodes()
            }
        g_m, p_g_m, g_m_g = pullback_complement(
            rule.p, rule.lhs, self, rule.p_lhs, instance,
            inplace=False
        )
        g_prime, g_m_g_prime, rhs_g_prime = pushout(
            rule.p, g_m, rule.rhs, p_g_m, rule.p_rhs, inplace=False)

        return rhs_g_prime


class Neo4jGraph(Graph):
    """."""

    def __init__(self):
        """."""
        pass

    def nodes(self):
        """Return the list of nodes."""
        pass

    def edges(self):
        """Return the list of edges."""
        pass

    def get_node(self, n):
        """Get node attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph or regraph.neo4j.Neo4jGraph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        pass

    def get_edge(self, s, t):
        """Get edge attributes.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        pass

    def add_node(self, node_id, attrs=None):
        """Abstract method for adding a node.

        Parameters
        ----------
        node_id : hashable
            Prefix that is prepended to the new unique name.
        attrs : dict, optional
            Node attributes.
        """
        pass

    def remove_node(self, node_id):
        """Remove node.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        node_id : hashable, node to remove.
        """
        pass

    def add_edge(self, s, t, attrs=None, **attr):
        """Add an edge to a graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        attrs : dict
            Edge attributes.
        """
        pass

    def remove_edge(self, source_id, target_id):
        """Remove edge from the graph.

        Parameters
        ----------
        graph : networkx.(Di)Graph
        s : hashable, source node id.
        t : hashable, target node id.
        """
        pass

    def update_node_attrs(self, node_id, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        node_id : hashable, node to update.
        attrs : dict
            New attributes to assign to the node

        """
        pass

    def update_edge_attrs(self, s, t, attrs, normalize=True):
        """Update attributes of a node.

        Parameters
        ----------
        s : hashable, source node of the edge to update.
        t : hashable, target node of the edge to update.
        attrs : dict
            New attributes to assign to the node

        """
        pass

    def in_edges(self, node_id):
        """Return the set of in-coming edges."""
        pass

    def out_edges(self, node_id):
        """Return the set of out-going edges."""
        pass

    def successors(self, node_id):
        """Return the set of successors."""
        pass

    def predecessors(self, node_id):
        """Return the set of predecessors."""
        pass

    def find_matching(self, pattern, nodes=None):
        """Find matching of a pattern in a graph."""
        pass
