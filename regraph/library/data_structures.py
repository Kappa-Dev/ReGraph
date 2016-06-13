"""Define data structures used by graph rewriting tool."""

import networkx as nx

from regraph.library.utils import (is_subdict, keys_by_value)
from regraph.library.primitives import (normalize_attrs)


class TypedNode:
    """Define the datastructure for typed node."""

    def __init__(self, n_type=None, attrs=None):
        self.type_ = n_type
        self.attrs_ = attrs
        normalize_attrs(self.attrs_)
        return

    def set_attrs(self, attrs):
        normalize_attrs(attrs)
        self.attrs_ = attrs


class TypedDiGraph(nx.DiGraph):
    """Define simple typed directed graph.

    Main framework is the following:
    1) Initialize the graph
    2) Add nodes one by one (node_id and type is required)
    3) Add edges between them

    Keep in mind that it is not possible to add an edges
    between the node if one of them does not exist
    """

    def __init__(self, metamodel=None):
        nx.DiGraph.__init__(self)
        self.metamodel_ = metamodel

    def add_node(self, node_id, node_type, attrs=None):
        if node_id not in self.nodes():
            if self.metamodel_ is not None:
                if node_type not in self.metamodel_.nodes():
                    raise ValueError(
                        "Type '%s' is not allowed by metamodel!" % node_type)
            nx.DiGraph.add_node(self, node_id)
            self.node[node_id] = TypedNode(node_type, attrs)
        else:
            raise ValueError("Node %s already exists!" % node_id)

    def add_nodes_from(self, node_list):
        for node_id, node_type in node_list:
            self.add_node(node_id, node_type)

    def add_edge(self, s, t, attrs=None, **attr):
        # set up attribute dict (from Networkx to preserve the signature)
        if attrs is None:
            attrs = attr
        else:
            try:
                attrs.update(attr)
            except AttributeError:
                raise ValueError(
                    "The attr_dict argument must be a dictionary."
                )
        if s not in self.nodes():
            raise ValueError("Node %s is not defined!" % s)
        if t not in self.nodes():
            raise ValueError("Node %s is not defined!" % t)
        source_type = self.node[s].type_
        target_type = self.node[t].type_
        if self.metamodel_ is not None:
            if (source_type, target_type) not in self.metamodel_.edges():
                raise ValueError(
                    "Edge from '%s' to '%s' is not allowed by metamodel" %
                    (source_type, target_type)
                )
        normalize_attrs(attrs)
        nx.DiGraph.add_edge(self, s, t, attrs)

    def add_edges_from(self, edge_list, attrs=None, **attr):
        # set up attribute dict (from Networkx to preserve the signature)
        if attrs is None:
            attrs = attr
        else:
            try:
                attrs.update(attr)
            except AttributeError:
                raise ValueError(
                    "The attr_dict argument must be a dictionary."
                )
        for edge in edge_list:
            if not edge[0] in self.nodes():
                raise ValueError("Node %s is not defined!" % edge[0])
            if not edge[1] in self.nodes():
                raise ValueError("Node %s is not defined!" % edge[1])
            source_type = self.node[edge[0]].type_
            target_type = self.node[edge[1]].type_
            if self.metamodel_ is not None:
                if (source_type, target_type) not in self.metamodel_.edges():
                    raise ValueError(
                        "Edge from '%s' to '%s' is not allowed by metamodel" %
                        (source_type, target_type)
                    )
        normalize_attrs(attrs)
        nx.DiGraph.add_edges_from(self, edge_list, attrs)

    def get_edge(self, source, target):
        return self.edge[source][target]

    def set_edge(self, source, target, attrs):
        if not (source, target) in self.edges():
            raise ValueError(
                "Edge %s-%s does not exist" % (str(source), str(target)))
        normalize_attrs(attrs)
        self.edge[source][target] = attrs

    def relabel_nodes(self, mapping):
        """Relabel graph nodes in place.

        Similar to networkx.relabel.relabel_nodes:
        https://networkx.github.io/documentation/development/_modules/networkx/relabel.html
        """
        if self.metamodel_ is not None:
            g = TypedDiGraph(self.metamodel_.copy())
        else:
            g = TypedDiGraph()

        old_nodes = set(mapping.keys())

        for old_node in old_nodes:
            try:
                new_node = mapping[old_node]
            except KeyError:
                continue
            try:
                g.add_node(
                    new_node,
                    self.node[old_node].type_,
                    self.node[old_node].attrs_)
            except KeyError:
                raise ValueError("Node %s does not exist!" % old_node)
        new_edges = []
        attributes = {}
        for s, t in self.edges():
            new_edges.append((
                mapping[s],
                mapping[t]))
            attributes[(mapping[s], mapping[t])] =\
                self.edge[s][t]

        g.add_edges_from(new_edges)
        for s, t in g.edges():
            g.set_edge(s, t, attributes[(s, t)])
        return g


class TypedGraph(nx.Graph):
    """Define simple typed undirected graph."""

    def __init__(self, metamodel=None):
        nx.Graph.__init__(self)
        self.metamodel_ = metamodel

    def add_node(self, node_id, node_type, attrs=None):
        if node_id not in self.nodes():
            if self.metamodel_ is not None:
                if node_type not in self.metamodel_.nodes():
                    raise ValueError(
                        "Type '%s' is not allowed by metamodel!" % node_type)
            nx.Graph.add_node(self, node_id)
            self.node[node_id] = TypedNode(node_type, attrs)
        else:
            raise ValueError("Node %s already exists!" % node_id)

    def add_nodes_from(self, node_list):
        for node_id, node_type in node_list:
            self.add_node(node_id, node_type)

    def add_edge(self, s, t, attrs=None, **attr):
        # set up attribute dict (from Networkx to preserve the signature)
        if attrs is None:
            attrs = attr
        else:
            try:
                attrs.update(attr)
            except AttributeError:
                raise ValueError(
                    "The attr_dict argument must be a dictionary."
                )
        if s not in self.nodes():
            raise ValueError("Node %s is not defined!" % s)
        if t not in self.nodes():
            raise ValueError("Node %s is not defined!" % t)
        source_type = self.node[s].type_
        target_type = self.node[t].type_
        if self.metamodel_ is not None:
            if (source_type, target_type) not in self.metamodel_.edges():
                if (target_type, source_type) not in self.metamodel_.edges():
                    raise ValueError(
                        "Edge from '%s' to '%s' is not allowed by metamodel" %
                        (source_type, target_type)
                    )
        # There is some strange things with edge attributes in NetworkX
        # for undirected graphs: if I say graph.edge[1][2] = <some attributes>
        # it will not update value of graph.edge[2][1]
        normalize_attrs(attrs)
        nx.Graph.add_edge(self, s, t, attrs)
        nx.Graph.add_edge(self, t, s, attrs)

    def add_edges_from(self, edge_list, attrs=None, **attr):
        # set up attribute dict (from Networkx to preserve the signature)
        if attrs is None:
            attrs = attr
        else:
            try:
                attrs.update(attr)
            except AttributeError:
                raise ValueError(
                    "The attr_dict argument must be a dictionary."
                )
        for edge in edge_list:
            if not edge[0] in self.nodes():
                raise ValueError("Node %s is not defined!" % edge[0])
            if not edge[1] in self.nodes():
                raise ValueError("Node %s is not defined!" % edge[1])
            source_type = self.node[edge[0]].type_
            target_type = self.node[edge[1]].type_
            if self.metamodel_ is not None:
                if (source_type, target_type) not in self.metamodel_.edges():
                    if (target_type, source_type) not in self.metamodel_.edges():
                        raise ValueError(
                            "Edge from '%s' to '%s' is not allowed by metamodel" %
                            (source_type, target_type)
                        )
        normalize_attrs(attrs)
        nx.Graph.add_edges_from(self, edge_list, attrs)

    def get_edge(self, source, target):
        return self.edge[source][target]

    def set_edge(self, u, v, attrs):
        if (not (u, v) in self.edges()) and (not (v,u) in self.edges()):
            raise ValueError(
                "Edge %s-%s does not exist" % (str(u), str(v)))
        normalize_attrs(attrs)
        self.edge[u][v] = attrs
        self.edge[v][u] = attrs

    def relabel_nodes(self, mapping):
        """Relabel graph nodes in place.

        Similar to networkx.relabel.relabel_nodes:
        https://networkx.github.io/documentation/development/_modules/networkx/relabel.html
        """
        if self.metamodel_ is not None:
            g = TypedGraph(self.metamodel_.copy())
        else:
            g = TypedGraph()

        old_nodes = set(mapping.keys())

        for old_node in old_nodes:
            try:
                new_node = mapping[old_node]
            except KeyError:
                continue
            try:
                g.add_node(
                    new_node,
                    self.node[old_node].type_,
                    self.node[old_node].attrs_)
            except KeyError:
                raise ValueError("Node %s does not exist!" % old_node)
        new_edges = []
        attributes = {}
        for s, t in self.edges():
            new_edges.append((
                mapping[s],
                mapping[t]))
            attributes[(mapping[s], mapping[t])] =\
                self.edge[s][t]

        g.add_edges_from(new_edges)
        for s, t in g.edges():
            g.set_edge(s, t, attributes[(s, t)])
        return g


def is_valid_homomorphism(source, target, dictionary):
    """Check if the homomorphism is valid (preserves edges and types)."""
    # check if there is mapping for all the nodes of source graph
    if set(source.nodes()) != set(dictionary.keys()):
        raise ValueError(
            "Invalid homomorphism: Mapping is not covering all the nodes of source graph!")

    # check nodes match with types and sets of attributes
    for s, t in dictionary.items():
        if source.node[s].type_ != target.node[t].type_:
            raise ValueError(
                "Invalid homomorphism: Node type does not match ('%s' and '%s')!" %
                (str(source.node[s].type_), str(target.node[t].type_)))
        if not is_subdict(source.node[s].attrs_, target.node[t].attrs_):
            raise ValueError(
                "Invalid homomorphism: Attributes of nodes source:'%s' and target:'%s' does not match!" %
                (str(s), str(t)))

    # check connectivity and edges attr matches
    for s_edge in source.edges():
        if not (dictionary[s_edge[0]], dictionary[s_edge[1]]) in target.edges():
            if not target.is_directed():
                if not (dictionary[s_edge[1]], dictionary[s_edge[0]]) in target.edges():
                    raise ValueError(
                        "Invalid homomorphism: Connectivity is not preserved!")
            else:
                raise ValueError(
                    "Invalid homomorphism: Connectivity is not preserved!")
        source_edge_attrs = source.get_edge(s_edge[0], s_edge[1])
        target_edge_attrs = target.get_edge(dictionary[s_edge[0]],
                                            dictionary[s_edge[1]])
        if not is_subdict(source_edge_attrs, target_edge_attrs):
            raise ValueError(
                "Invalid homomorphism: Attributes of edges (%s)-(%s) and (%s)-(%s) does not match!" %
                (s_edge[0], s_edge[1], dictionary[s_edge[0]],
                    dictionary[s_edge[1]]))

    return True


class Homomorphism:
    """Define graph homomorphism data structure."""

    def __init__(self, source, target, dictionary):
        if is_valid_homomorphism(source, target, dictionary):
            self.source_ = source
            self.target_ = target
            self.mapping_ = dictionary
        else:
            raise ValueError("Homomorphism is not valid!")

    def is_monic(self):
        """Check if the homomorphism is monic."""
        return len(set(self.mapping_.keys())) ==\
            len(set(self.mapping_.values()))

    def find_final_PBC(self):
        # edges to remove will be removed automatically upon removal of the nodes
        nodes = set([n for n in self.target_.nodes()
                     if n not in self.mapping_.values()])
        node_attrs = {}
        for node in self.source_.nodes():
            if node not in node_attrs.keys():
                node_attrs.update({node: {}})

            mapped_node = self.mapping_[node]
            mapped_attrs = self.target_.node[mapped_node].attrs_

            attrs = self.source_.node[node].attrs_
            if mapped_attrs is not None and attrs is not None:
                for key, value in mapped_attrs.items():
                    if key not in attrs.keys():
                        node_attrs[node].update({key: value})
                    else:
                        if type(value) != set:
                            value = set([value])
                        else:
                            node_attrs[node].update(
                                {key: set([el for el in value if el not in attrs[key]])})

        edge_attrs = {}
        edges = set()
        for edge in self.target_.edges():
            if self.source_.is_directed():
                sources = keys_by_value(self.mapping_, edge[0])
                targets = keys_by_value(self.mapping_, edge[1])
                if len(sources) == 0 or len(targets) == 0:
                    continue
                for s in sources:
                    for t in targets:
                        if (s, t) not in self.source_.edges():
                            edges.add((s, t))
            else:
                sources = keys_by_value(self.mapping_, edge[0])
                targets = keys_by_value(self.mapping_, edge[1])
                if len(sources) == 0 or len(targets) == 0:
                    continue
                for s in sources:
                    for t in targets:
                        if (s, t) not in self.source_.edges():
                            if (t, s) not in self.source_.edges():
                                edges.add((s, t))

        for edge in self.source_.edges():
            if edge not in edge_attrs.keys():
                edge_attrs.update({edge: {}})

            mapped_edge = (self.mapping_[edge[0]], self.mapping_[edge[1]])
            mapped_attrs = self.target_.edge[mapped_edge[0]][mapped_edge[1]]

            attrs = self.source_.edge[edge[0]][edge[1]]

            for key, value in mapped_attrs.items():
                if key not in attrs.keys():
                    edge_attrs[edge].update({key: value})
                else:
                    if type(value) != set:
                        value = set([value])
                    else:
                        edge_attrs[edge].update(
                            {key: set([el for el in value if el not in attrs[key]])})
        return (nodes, edges, node_attrs, edge_attrs)

    def find_PO(self):
        nodes = set([n for n in self.target_.nodes() if n not in self.mapping_.values()])

        node_attrs = {}
        for node in self.source_.nodes():
            if node not in node_attrs.keys():
                node_attrs.update({node: {}})

            mapped_node = self.mapping_[node]
            mapped_attrs = self.target_.node[mapped_node].attrs_

            attrs = self.source_.node[node].attrs_
            if mapped_attrs is not None and attrs is not None:
                for key, value in mapped_attrs.items():
                    if key not in attrs.keys():
                        node_attrs[node].update({key: value})
                    else:
                        if type(value) != set:
                            value = set([value])
                        else:
                            node_attrs[node].update(
                                {key: set([el for el in value if el not in attrs[key]])})

        edges = dict()
        edge_attrs = {}

        for edge in self.target_.edges():
            sources = keys_by_value(self.mapping_, edge[0])
            targets = keys_by_value(self.mapping_, edge[1])
            if len(sources) == 0 or len(targets) == 0:
                edges[(edge[0], edge[1])] = self.target_.edge[edge[0]][edge[1]]
                continue
            for s in sources:
                for t in targets:
                    if (s, t) not in self.source_.edges():
                        edges[(edge[0], edge[1])] = self.target_.edge[edge[0]][edge[1]]

        for edge in self.source_.edges():
            if edge not in edge_attrs.keys():
                edge_attrs.update({edge: {}})

            mapped_edge = (self.mapping_[edge[0]], self.mapping_[edge[1]])
            mapped_attrs = self.target_.edge[mapped_edge[0]][mapped_edge[1]]

            attrs = self.source_.edge[edge[0]][edge[1]]

            for key, value in mapped_attrs.items():
                if key not in attrs.keys():
                    edge_attrs[edge].update({key: value})
                else:
                    if type(value) != set:
                        value = set([value])
                    else:
                        if type(attrs[key]) != set:
                            edge_attrs[edge].update(
                                {key: set([el for el in value
                                           if el not in set([attrs[key]])])})
                        else:
                            edge_attrs[edge].update(
                                {key: set([el for el in value
                                           if el not in attrs[key]])})
        return (nodes, edges, node_attrs, edge_attrs)
