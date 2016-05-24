"""."""
import networkx as nx
from networkx.algorithms import isomorphism

import matplotlib.pyplot as plt

import itertools

from regraph.library.parser import parser
from regraph.library.primitives import (is_subdict,
                                        merge_nodes,
                                        clone_node,
                                        add_node,
                                        remove_node,
                                        add_edge,
                                        remove_edge)


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

    def clone(self, instance, node):
        if node in instance.keys():
            clone_node(self.graph_, instance[node])
        else:
            clone_node(self.graph_, node)
        return

    def merge(self, instance, nodes, method=None, node_name=None):
        nodes_to_merge =\
            [instance[n] if n in instance.keys() else n
             for n in nodes]
        merge_nodes(
            self.graph_,
            nodes_to_merge,
            method,
            node_name)
        return

    def add_node(self, name, node_type, attrs):
        add_node(self.graph_, name, node_type, attrs)
        return

    def delete_node(self, instance, node):
        if node in instance.keys():
            remove_node(self.graph_, instance[node])
        else:
            remove_node(self.graph_, node)
        return

    def add_edge(self, instance, node_1, node_2):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        add_edge(self.graph_, source, target)
        return

    def delete_edge(self, instance, node_1, node_2):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        remove_edge(self.graph_, source, target)

    def transform_instance(self, instance, commands):
        """Transform the instance of LHS of the rule in the graph."""
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        for command in command_strings:
            parsed = parser.parseString(command)
            if parsed["keyword"] == "clone":
                self.clone(instance, parsed["node"])
            elif parsed["keyword"] == "merge":
                method = None
                node_name = None
                if "method" in parsed.keys():
                    method = parsed["method"]
                if "node_name" in parsed.keys():
                    node_name = parsed["node_name"]
                self.merge(instance, parsed["nodes"], method, node_name)
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
                self.delete_node(instance, parsed["node"])
            elif parsed["keyword"] == "add_edge":
                self.add_edge(instance, parsed["node_1"], parsed["node_2"])
            elif parsed["keyword"] == "delete_edge":
                self.delete_edge(instance, parsed["node_1"], parsed["node_2"])
            else:
                raise ValueError("Unknown command")

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
