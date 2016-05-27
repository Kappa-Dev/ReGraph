"""Define data structures used by graph rewriting tool."""

import networkx as nx

from regraph.library.utils import is_subdict


class TypedNode:
    """Define the datastructure for typed node."""

    def __init__(self, n_type=None, attrs=None):
        self.type_ = n_type
        self.attrs_ = attrs
        return


class TypedDiGraph(nx.DiGraph):
    """Define simple typed directed graph.

    Main framework is the following:
    1) Initialize the graph
    2) Add nodes one by one (node_id and type is required)
    3) Add edges between them

    Keep in mind that it is not possible to add an edges
    between the node if one of them does not exist
    """

    def __init__(self):
        nx.DiGraph.__init__(self)

    def add_node(self, node_id, type, attrs={}):
        nx.DiGraph.add_node(self, node_id)
        self.node[node_id] = TypedNode(type, attrs)

    def add_nodes_from(self, node_list):
        raise NotImplementedError(
            "Adding the nodes from the list is not impemented!")

    def add_edges_from(self, edge_list):
        for edge in edge_list:
            if not edge[0] in self.nodes():
                raise ValueError("Node %s is not defined!" % edge[0])
            if not edge[1] in self.nodes():
                raise ValueError("Node %s is not defined!" % edge[1])
        nx.DiGraph.add_edges_from(self, edge_list)

    def get_edge(self, source, target):
        return self.edge[source][target]

    def set_edge(self, source, target, attrs):
        if not (source, target) in self.edges():
            raise ValueError(
                "Edge %s-%s does not exist" % (str(source), str(target)))
        self.edge[source][target] = attrs


# class TypedGraph:
#     """Define simple typed undirected graph."""

#     def __init__(self):
#         self.graph_ = nx.Graph()

#     def add_node(self, node_id, type, attrs={}):
#         nx.Graph.add_node(self, node_id)
#         self.node[node_id] = TypedNode(type, attrs)

#     def add_nodes_from(self, node_list):
#         raise NotImplementedError(
#             "Adding the nodes from the list is not impemented!")

#     def add_edges_from(self, edge_list):
#         for edge in edge_list:
#             if not edge[0] in self.nodes():
#                 raise ValueError("Node %s is not defined!" % edge[0])
#             if not edge[1] in self.nodes():
#                 raise ValueError("Node %s is not defined!" % edge[1])
#         nx.Graph.add_edges_from(self, edge_list)

#     def get_edge(self, source, target):
#         return self.edge[source][target]

#     def set_edge(self, source, target, attrs):
#         self.edge[source][target] = attrs


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
        nodes_to_remove = [n for n in self.target_.nodes() if n not in self.mapping_.values()]
        edges_to_remove = []
        for edge in self.target_.edges():
            for p_node, l_node in self.mapping_.items():
                if l_node == edge[0]:
                    s = p_node
                if l_node == edge[1]:
                    t = p_node
            if (s, t) not in self.source_.edges():
                edges_to_remove.append(edge)
        return (nodes_to_remove, edges_to_remove)

    def find_PO(self):
        nodes_to_add = [n for n in self.target_.nodes() if n not in self.mapping_.values()]
        edges_to_add = []
        for edge in self.target_.edges():
            for p_node, l_node in self.mapping_.items():
                if p_node == edge[0]:
                    s = p_node
                if p_node == edge[1]:
                    t = p_node
            if (s, t) not in self.source_.edges():
                edges_to_add.append(edge)
        return (nodes_to_add, edges_to_add)
