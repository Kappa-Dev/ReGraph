"""Define data structures used by graph rewriting tool."""

import networkx as nx


class TypedNode:
    """Define the datastructure for typed node."""

    def __init__(self, n_type=None, attrs=None):
        self.type_ = n_type
        self.attrs_ = attrs
        return


class TypedDiGraph:
    """Define simple typed directed graph.

    Main framework is the following:
    1) Initialize the graph
    2) Add nodes one by one (node_id and type is required)
    3) Add edges between them

    Keep in mind that it is not possible to add an edges
    between the node if one of them does not exist
    """

    def __init__(self):
        self.graph_ = nx.DiGraph()
        return

    def add_node(self, node_id, type, attrs=None):
        self.graph_.add_node(node_id)
        self.graph_.node[node_id] = TypedNode(type, attrs)
        return

    def add_edges_from(self):
        pass


class TypedGraph:
    """Define simple typed undirected graph."""

    def __init__(self):
        self.graph_ = nx.DiGraph()
    pass


def is_valid_homomorphism(source, target, dictionary, types):
    """Check if the homomorphism is valid (preserves edges and types)."""
    # check if there is mapping for all the nodes of source graph
    if set(source.nodes()) != set(dictionary.keys()):
        return False

    # check nodes match with types
    for s, t in dictionary.items():
        if source.node[s].type_ != source.node[t].type_:
            return False

    # check connectivity
    for s_edge in source.edges():
        if not (dictionary[s_edge[0]], dictionary[s_edge[1]]) in target.edges():
            return False

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
        return len(set(self.dictionary_.keys())) ==\
            len(set(self.dictionary_.value()))
