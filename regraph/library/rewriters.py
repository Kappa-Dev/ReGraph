"""."""
from regraph.library.parser import parser

import networkx as nx
from networkx.algorithms import isomorphism

import matplotlib.pyplot as plt

import itertools


def is_subdict(small_dict, big_dict):
    """Check if the dictionary is a subset of other."""
    return set(small_dict.items()).issubset(set(big_dict.items()))


def merge_attributes(attr1, attr2, method="union"):
    """Merge two dictionaries of attributes."""
    result = {}
    if method == "union":
        for key1 in attr1.keys():
            if key1 in attr2.keys():
                if attr1[key1] == attr2[key1]:
                    result.update(
                        {key1: attr1[key1]})
                else:
                    attr_set = set()
                    if type(attr1[key1]) == set:
                        attr_set.update(attr1[key1])
                    else:
                        attr_set.add(attr1[key1])
                    if type(attr2[key1]) == set:
                        attr_set.update(attr2[key1])
                    else:
                        attr_set.add(attr2[key1])
                    result.update(
                        {key1: attr_set})
            else:
                result.update({key1: attr1[key1]})

        for key2 in attr2.keys():
            if key2 not in result:
                result.update({key2: attr2[key2]})
    elif method == "intersection":
        for key1 in attr1.keys():
            if key1 in attr2.keys():
                attr_set1 = set(itertools.chain([attr1[key1]]))
                attr_set2 = set(itertools.chain([attr2[key1]]))
                intersect = set.intersection(attr_set1, attr_set2)
                if len(intersect) == 1:
                    result.update({key1: list(intersect)[0]})
                elif len(intersect) > 0:
                    result.update({key1: intersect})

    else:
        raise ValueError("Merging method %s is not defined!" % method)
    return result


class Rewriter:
    """Class implements the transformation on the graph."""

    def __init__(self, graph):
        """Initialize Rewriter object with input graph."""
        self.graph_ = graph
        self.parser_ = parser
        return

    def find_matching(self, pattern):
        """Perform matching of the pattern graph."""
        matching_nodes = set()
        # find all the nodes matching the nodes in pattern
        for pattern_node in pattern.nodes():
            for node in self.graph_.nodes():
                if is_subdict(pattern.node[pattern_node],
                              self.graph_.node[node]):
                    matching_nodes.add(node)

        reduced_graph = self.graph_.subgraph(matching_nodes)
        instances = []
        isomorphic_subgraphs = []
        for sub_nodes in itertools.combinations(reduced_graph.nodes(),
                                                len(pattern.nodes())):
                subg = reduced_graph.subgraph(sub_nodes)
                for edgeset in itertools.combinations(subg.edges(),
                                                      len(pattern.edges())):
                    edge_induced_graph = nx.DiGraph(edgeset)
                    GM = isomorphism.GraphMatcher(pattern, edge_induced_graph)
                    if GM.is_isomorphic():
                        isomorphic_subgraphs.append((subg, GM.mapping))
        # check node matches
        # exclude subgraphs which nodes information does not
        # correspond to pattern
        for subgraph, mapping in isomorphic_subgraphs:
            for (pattern_node, node) in mapping.items():
                if not is_subdict(pattern.node[pattern_node], subgraph.node[node]):
                    break
            else:
                instances.append(mapping)
        return instances

    def transform_instance(self, instance, commands):
        """Transform the instance of LHS of the rule in the graph."""
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        for command in command_strings:
            print(command)
            parsed = parser.parseString(command)
            if parsed["keyword"] == "clone":
                if parsed["node"] in instance.keys():
                    self.clone_node(instance[parsed["node"]])
                else:
                    self.clone_node(parsed["node"])
            elif parsed["keyword"] == "merge":
                method = None
                node_name = None
                if "method" in parsed.keys():
                    method = parsed["method"]
                if "node_name" in parsed.keys():
                    node_name = parsed["node_name"]
                nodes_to_merge =\
                    [instance[n] if n in instance.keys() else n
                     for n in parsed["nodes"]]
                self.merge_nodes(nodes_to_merge, method, node_name)
            elif parsed["keyword"] == "add_node":
                name = None
                node_type = None
                attrs = {}
                if "node" in parsed.keys():
                    name = parsed["node"]
                if "type" in parsed.keys():
                    node_type = parsed["type"]
                if "attrubutes" in parsed.keys():
                    attrs = parsed["attrubutes"]
                self.add_node(name, node_type, attrs)
            elif parsed["keyword"] == "delete_node":
                if parsed["node"] in instance.keys():
                    self.remove_node(instance[parsed["node"]])
                else:
                    self.remove_node(parsed["node"])
            elif parsed["keyword"] == "add_edge":
                if parsed["node_1"] in instance.keys():
                    node_1 = instance[parsed["node_1"]]
                else:
                    node_1 = parsed["node_1"]
                if parsed["node_2"] in instance.keys():
                    node_2 = instance[parsed["node_2"]]
                else:
                    node_2 = parsed["node_2"]
                self.add_edge(node_1, node_2)
            elif parsed["keyword"] == "delete_edge":
                if parsed["node_1"] in instance.keys():
                    node_1 = instance[parsed["node_1"]]
                else:
                    node_1 = parsed["node_1"]
                if parsed["node_2"] in instance.keys():
                    node_2 = instance[parsed["node_2"]]
                else:
                    node_2 = parsed["node_2"]
                self.remove_edge(node_1, node_2)
            else:
                raise ValueError("Unknown command")

    def merge_nodes(self, nodes, method="union", node_name=None):
        """Merge two nodes."""
        if method is None:
            method = "union"

        # generate name for new node
        if node_name is None:
            node_name = "_".join([str(n) for n in nodes])
        elif node_name in self.graph_.nodes():
            raise ValueError(
                "The node with name '%s' already exists!" % str(node_name))

        self.graph_.add_node(node_name)

        # merge data attached to node according to the method specified
        # restore proper connectivity
        if method == "union":
            attr_accumulator = {}
        elif method == "intersection":
            attr_accumulator = self.graph_.node[nodes[0]]
        else:
            raise ValueError("Merging method %s is not defined!" % method)
        source_nodes = set()
        target_nodes = set()
        for node in nodes:
            attr_accumulator = merge_attributes(
                attr_accumulator, self.graph_.node[node], method)
            source_nodes.update(
                [n if n not in nodes else node_name
                 for n, _ in self.graph_.in_edges(node)])
            target_nodes.update(
                [n if n not in nodes else node_name
                 for _, n in self.graph_.out_edges(node)])
            self.graph_.remove_node(node)

        self.graph_.node[node_name] = attr_accumulator
        print(self.graph_.node[node_name])
        self.graph_.add_edges_from([(n, node_name) for n in source_nodes])
        self.graph_.add_edges_from([(node_name, n) for n in target_nodes])

    def clone_node(self, node):
        """Clone existing node and all its edges."""
        new_node = "%s_copy" % str(node)
        while new_node in self.graph_.nodes():
            new_node = "%s_copy" % new_node

        self.graph_.add_node(new_node)

        # Copy the attributes
        self.graph_.node[new_node] = self.graph_.node[node]

        # Connect all the edges
        self.graph_.add_edges_from(
            [(n, new_node) for n, _ in self.graph_.in_edges(node)])
        self.graph_.add_edges_from(
            [(new_node, n) for _, n in self.graph_.out_edges(node)])

    def add_node(self, name=None, type=None, attrs={}):
        """Add new node to the graph."""
        if name is not None:
            self.graph_.add_node(name)
            self.graph_.node[name] = attrs
        else:
            i = 0
            new_name = "new_node_%d" % i
            while new_name in self.graph_.nodes():
                i += 1
                new_name = "new_node_%d" % i
            self.graph_.add_node(new_name)
            self.graph_.node[new_name] = attrs
        return

    def remove_node(self, node):
        """Remove node from the graph."""
        if node in self.graph_.nodes():
            self.graph_.remove_node(node)
        return

    def add_edge(self, source, target):
        """Add edge to the graph."""
        if not (source, target) in self.graph_.edges():
            self.graph_.add_edge(source, target)
        return

    def remove_edge(self, source, target):
        """Remove edge from the graph."""
        if (source, target) in self.graph_.edges():
            self.graph_.remove_edge(source, target)
        return

    def plot_graph(self, filename=None):
        """Plot the graph that is being currently rewrited."""
        pos = nx.spring_layout(self.graph_)
        nx.draw_networkx_nodes(self.graph_, pos, node_size=100, arrows=True)
        nx.draw_networkx_edges(self.graph_, pos, alpha=0.6)

        labels = {}
        for node in self.graph_.nodes():
            labels[node] = node
        offset = 0.05
        for p in pos:  # raise text positions
            pos[p][1] += offset
        nx.draw_networkx_labels(self.graph_, pos, labels, font_size=11)
        if filename is not None:
            with open(filename, "w") as f:
                plt.savefig(f)
                plt.clf()
        else:
            plt.show()
        return

    def plot_instance(self, pattern, instance, filename):
        """Plot the graph with instance of pattern highlighted."""
        new_colors = ["g" if not self.graph_.nodes()[i] in instance.values()
                      else "r" for i, c in enumerate(self.graph_.nodes())]
        pos = nx.spring_layout(self.graph_)
        nx.draw_networkx_nodes(
            self.graph_, pos, node_color=new_colors,
            node_size=100, arrows=True)
        nx.draw_networkx_edges(self.graph_, pos, alpha=0.6)

        # Draw pattern edges highlighted
        edgelist = [(instance[edge[0]], instance[edge[1]])
                    for edge in pattern.edges()]
        nx.draw_networkx_edges(
            self.graph_, pos,
            edgelist=edgelist,
            width=3, alpha=0.5, edge_color='r')

        labels = {}
        for node in self.graph_.nodes():
            labels[node] = node
        offset = 0.05
        for p in pos:  # raise text positions
            pos[p][1] += offset
        nx.draw_networkx_labels(self.graph_, pos, labels, font_size=11)

        # color the instances
        plt.title("Graph with instance of pattern highlighted")
        if filename is not None:
            with open(filename, "w") as f:
                plt.savefig(f)
                plt.clf()
        else:
            plt.show()
        return
