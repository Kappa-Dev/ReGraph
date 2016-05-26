"""."""
import networkx as nx
from networkx.algorithms import isomorphism

import itertools

from regraph.library.parser import parser
from regraph.library.primitives import (merge_nodes,
                                        clone_node,
                                        add_node,
                                        remove_node,
                                        add_edge,
                                        remove_edge)
from regraph.library.utils import is_subdict


# taken from projx https://github.com/davebshow/projx

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
                if pattern.node[pattern_node].type_ == self.graph_.node[node].type_:
                    if is_subdict(pattern.node[pattern_node].attrs_,
                                  self.graph_.node[node].attrs_):
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

        for subgraph, mapping in isomorphic_subgraphs:
            # check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if not pattern.node[pattern_node].type_ == subgraph.node[node].type_:
                    break
                if not is_subdict(pattern.node[pattern_node].attrs_, subgraph.node[node].attrs_):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.get_edge(edge[0], edge[1])
                    target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
                    if not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        return instances

    def clone(self, instance, node, name=None):
        if node in instance.keys():
            clone_node(self.graph_, instance[node], name)
        else:
            clone_node(self.graph_, node, name)
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

    def add_edge(self, instance, node_1, node_2, attrs={}):
        if node_1 in instance.keys():
            source = instance[node_1]
        else:
            source = node_1
        if node_2 in instance.keys():
            target = instance[node_2]
        else:
            target = node_2
        add_edge(self.graph_, source, target, attrs)
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
        # for node in self.graph_.nodes():
        #     print(self.graph_.node[node].type_)
        command_strings = [c for c in commands.splitlines() if len(c) > 0]
        for command in command_strings:
            parsed = parser.parseString(command)
            if parsed["keyword"] == "clone":
                node_name = None
                if "node_name" in parsed.keys():
                    node_name = parsed["node_name"]
                self.clone(instance, parsed["node"], node_name)
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
