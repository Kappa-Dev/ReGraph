"""Define data structures used by graph rewriting tool."""

import networkx as nx
import warnings
from copy import deepcopy

from regraph.library.utils import (is_subdict,
                                   keys_by_value,
                                   to_set,
                                   normalize_attrs,
                                   merge_attributes)

import json
import os.path


class TypedNode:
    """Define the datastructure for typed node."""

    def __init__(self, n_type=None, attrs=None):
        self.type_ = n_type
        self.attrs_ = attrs
        normalize_attrs(self.attrs_)
        return

    def __str__(self):
        return "Node:\nType: %s\nAttributes: %s\n" % (self.type_, self.attrs_)

    def set_attrs(self, attrs):
        self.attrs_ = attrs
        normalize_attrs(self.attrs_)

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
        self.hom = None

    def __eq__(self, A):
        if not (type(A) == type(self)):
            return False

        for n in A.nodes():
            if not (n in self.nodes() and\
                   (self.node[n].type_ == A.node[n].type_) and\
                   (self.node[n].attrs_ == A.node[n].attrs_)):
                   return False
        for n in self.nodes():
            if not (n in A.nodes() and\
                   (self.node[n].type_ == A.node[n].type_) and\
                   (self.node[n].attrs_ == A.node[n].attrs_)):
                   return False

        for e in A.edges():
            if not (e in self.edges() and\
                    self.get_edge(e[0],e[1]) == A.get_edge(e[0], e[1])):
                    return False
        for e in self.edges():
            if not (e in A.edges() and\
                    self.get_edge(e[0],e[1]) == A.get_edge(e[0], e[1])):
                    return False

        return True

    def __ne__(self, B):
        return not self.__eq__(B)

    def sub(self, B, homBA):
        res = type(self)()
        for n in self.nodes():
            if n not in homBA.mapping_.values():
                res.add_node(n,
                             self.node[n].type_,
                             self.node[n].attrs_)

        for n1 in res.nodes():
            for n2 in res.nodes():
                if (n1, n2) in self.edges():
                    if (n1, n2) not in B.edges():
                        res.add_edge(n1,
                                     n2,
                                     self.get_edge(n1, n2))

        return res

    def __str__(self):
        res = ""
        res += "Nodes : \n"
        for n in self.nodes():
            res += str(n)+" : "+str(self.node[n].type_)
            res += " | "+str(self.node[n].attrs_)+"\n"
        res += "\n"
        res += "Edges : \n"
        for n1,n2 in self.edges():
            res += str((n1,n2))+" : "+str(self.get_edge(n1, n2))+"\n"
        res += "\n"

        return res

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

    def remove_node(self, node):
        """Remove node from the self."""
        if node in self.nodes():
            nx.DiGraph.remove_node(self, node)
        else:
            raise ValueError("Node %s does not exist!" % str(node))
        return

    def add_nodes_from(self, node_list):
        for n in node_list:
            if len(n) == 3:
                node_id, node_type, node_attrs = n
                self.add_node(node_id, node_type, node_attrs)
            elif len(n) == 2:
                node_id, node_type = n
                self.add_node(node_id, node_type)
            else:
                raise ValueError(
                    "Each element of the node list should match pattern\
                    (node_id, node_type) or (node_id, node_type, node_attrs)"
                )

    def add_node_attrs(self, node, attrs_dict):
        if node not in self.nodes():
            raise ValueError("Node %s does not exist" % str(node))
        elif attrs_dict == None:
            # warnings.warn(
            #     "You want to add attrs to %s with an empty attrs_dict" % node
            # )
            pass
        else:
            if self.node[node].attrs_ is None:
                self.node[node].attrs_ = deepcopy(attrs_dict)
                normalize_attrs(self.node[node].attrs_)
            else:
                for key, value in attrs_dict.items():
                    if key not in self.node[node].attrs_.keys():
                        self.node[node].attrs_.update({key: to_set(value)})
                    else:
                        self.node[node].attrs_[key] =\
                            self.node[node].attrs_[key].union(to_set(value))

    def update_node_attrs(self, node, new_attrs):
        if node not in self.nodes():
            raise ValueError("Node %s does not exist" % str(node))
        elif new_attrs == None:
            warnings.warn(
                "You want to update %s attrs with an empty attrs_dict" % node
            )
        else:
            normalize_attrs(new_attrs)
            if self.node[node].attrs_ is None:
                self.node[node].attrs_ = new_attrs
                normalize_attrs(self.node[node].attrs_)
            else:
                for key, value in new_attrs.items():
                    self.node[node].attrs_[key] = to_set(value)

    def remove_node_attrs(self, node, attrs_dict):
        if node not in self.nodes():
            raise ValueError("Node %s does not exist" % str(node))
        elif attrs_dict == None:
            warnings.warn(
                "You want to remove attrs from %s with an empty attrs_dict" % node
            )
        else:
            for key, value in attrs_dict.items():
                if key not in self.node[node].attrs_.keys():
                    warnings.warn(
                        "Node %s does not have attribute '%s'" % (str(node), str(key)), RuntimeWarning)
                else:
                    elements_to_remove = []
                    for el in to_set(value):
                        if el in self.node[node].attrs_[key]:
                            elements_to_remove.append(el)
                        else:
                            warnings.warn(
                                "Node %s does not have attribute '%s' with value '%s'" %
                                (str(node), str(key), str(el)), RuntimeWarning)
                    for el in elements_to_remove:
                        self.node[node].attrs_[key].remove(el)

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

    def remove_edge(self, source, target):
        """Remove edge from the graph."""
        if (source, target) in self.edges():
            nx.DiGraph.remove_edge(self, source, target)
        else:
            raise ValueError(
                "Edge %s->%s does not exist!" % (str(source), str(target)))

    def add_edges_from(self, edge_list):
        for e in edge_list:
            if len(e) == 2 :
                self.add_edge(e[0], e[1])
            elif len(e) == 3 :
                self.add_edge(e[0], e[1], e[2])
            else:
                raise ValueError(
                    "Was expecting 2 or 3 elements per tuple, got %s." %
                    str(len(e))
                )

    def add_edge_attrs(self, node_1, node_2, attrs_dict):
        if (node_1, node_2) not in self.edges():
            raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
        elif attrs_dict == None:
        #     warnings.warn(
        #         "You want to add attrs to %s-%s attrs with an empty attrs_dict" %\
        #         (str(node_1), str(node_2))
        #     )
            pass
        else:
            for key, value in attrs_dict.items():
                if key not in self.edge[node_1][node_2].keys():
                    self.edge[node_1][node_2].update({key: to_set(value)})
                else:
                    self.edge[node_1][node_2][key].update(to_set(value))

    def update_edge_attrs(self, node_1, node_2, new_attrs):
        if (node_1, node_2) not in self.edges():
            raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
        elif new_attrs == None:
            warnings.warn(
                "You want to update %s-%s attrs with an empty attrs_dict" %\
                (str(node_1), str(node_2))
            )
        else:
            for key, value in new_attrs.items():
                self.edge[node_1][node_2][key] = to_set(value)

    def remove_edge_attrs(self, node_1, node_2, attrs_dict):
        if (node_1, node_2) not in self.edges():
            raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
        elif attrs_dict == None:
            warnings.warn(
                "You want to remove attrs from %s-%s attrs with an empty attrs_dict" %\
                (str(node_1), str(node_2))
            )
        else:
            for key, value in attrs_dict.items():
                if key not in self.edge[node_1][node_2].keys():
                    warnings.warn(
                        "Edge %s-%s does not have attribute '%s'" %
                        (str(node_1), str(node_2), str(key)), RuntimeWarning)
                else:
                    elements_to_remove = []
                    for el in to_set(value):
                        if el in self.edge[node_1][node_2][key]:
                            elements_to_remove.append(el)
                        else:
                            warnings.warn(
                                "Edge %s-%s does not have attribute '%s' with value '%s'" %
                                (str(node_1), str(node_2), str(key), str(el)), RuntimeWarning)
                    for el in elements_to_remove:
                        self.edge[node_1][node_2][key].remove(el)

    def get_edge(self, source, target):
        return self.edge[source][target]

    def set_edge(self, source, target, attrs):
        if not (source, target) in self.edges():
            raise ValueError(
                "Edge %s-%s does not exist" % (str(source), str(target)))
        normalize_attrs(attrs)
        self.edge[source][target] = attrs

    def get_node(self, n):
        return self.node[n]

    def cast_node(self, node, new_type):
        """Changes the node type in the graph"""
        self.node[node].type_ = new_type

    def merge_nodes(self, nodes, method="union",
                    node_name=None, edge_method="union"):
        """Merge list of nodes."""
        # Type checking
        node_type = self.node[nodes[0]].type_
        for node in nodes:
            if self.node[node].type_ != node_type:
                raise ValueError(
                    "Merge error: Non consistent node types ('%s', '%s')!" %
                    (str(self.node[node].type_), str(node_type)))

        if method is None:
            method = "union"

        if edge_method is None:
            method = "union"

        # Generate name for new node
        if node_name is None:
            node_name = "_".join([str(n) for n in nodes])
        elif node_name in self.nodes() and (node_name not in nodes):
            raise ValueError(
                "The node with name '%s' already exists!" % str(node_name))

        # Merge data attached to node according to the method specified
        # restore proper connectivity
        if method == "union":
            attr_accumulator = {}
        elif method == "intersection":
            attr_accumulator = deepcopy(self.node[nodes[0]].attrs_)
        else:
            raise ValueError("Merging method %s is not defined!" % method)

        self_loop = False
        self_loop_attrs = {}

        if self.is_directed():
            source_nodes = set()
            target_nodes = set()

            source_dict = {}
            target_dict = {}
        else:
            neighbors = set()
            neighbors_dict = {}

        for node in nodes:

            attr_accumulator = merge_attributes(
                attr_accumulator, self.node[node].attrs_, method)

            if self.is_directed():
                in_edges = self.in_edges(node)
                out_edges = self.out_edges(node)

                # manage self loops
                for s, t in in_edges:
                    if s in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = self.edge[s][t]
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                self.edge[s][t],
                                edge_method)

                for s, t in out_edges:
                    if t in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = self.edge[s][t]
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                self.edge[s][t],
                                edge_method)

                source_nodes.update(
                    [n if n not in nodes else node_name
                     for n, _ in in_edges])
                target_nodes.update(
                    [n if n not in nodes else node_name
                     for _, n in out_edges])

                for edge in in_edges:
                    if not edge[0] in source_dict.keys():
                        attrs = self.edge[edge[0]][edge[1]]
                        source_dict.update({edge[0]: attrs})
                    else:
                        attrs = merge_attributes(
                            source_dict[edge[0]],
                            self.edge[edge[0]][edge[1]],
                            edge_method)
                        source_dict.update({edge[0]: attrs})

                for edge in out_edges:
                    if not edge[1] in target_dict.keys():
                        attrs = self.edge[edge[0]][edge[1]]
                        target_dict.update({edge[1]: attrs})
                    else:
                        attrs = merge_attributes(
                            target_dict[edge[1]],
                            self.edge[edge[0]][edge[1]],
                            edge_method)
                        target_dict.update({edge[1]: attrs})
            else:
                for n in self.neighbors(node):
                    if n in nodes:
                        self_loop = True
                        if len(self_loop_attrs) == 0:
                            self_loop_attrs = self.edge[n][node]
                        else:
                            self_loop_attrs = merge_attributes(
                                self_loop_attrs,
                                self.edge[n][node],
                                edge_method)

                neighbors.update(
                    [n for n in self.neighbors(node) if n not in nodes])
                for n in self.neighbors(node):
                    if n not in nodes:
                        if n not in neighbors_dict.keys():
                            attrs = self.edge[n][node]
                            neighbors_dict.update({n: attrs})
                        else:
                            attrs = merge_attributes(
                                neighbors_dict[n],
                                self.edge[n][node],
                                edge_method)
                            neighbors_dict.update({n: attrs})

            self.remove_node(node)

        self.add_node(node_name, node_type, attr_accumulator)

        if self.is_directed():
            if self_loop:
                self.add_edges_from([(node_name, node_name)])
                self.edge[node_name][node_name] = self_loop_attrs

            self.add_edges_from([(n, node_name) for n in source_nodes])
            self.add_edges_from([(node_name, n) for n in target_nodes])

            # Attach accumulated attributes to edges
            for node, attrs in source_dict.items():
                if node not in nodes:
                    self.edge[node][node_name] = attrs
            for node, attrs in target_dict.items():
                if node not in nodes:
                    self.edge[node_name][node] = attrs
        else:
            if self_loop:
                self.add_edges_from([(node_name, node_name)])
                self.set_edge(node_name, node_name, self_loop_attrs)

            self.add_edges_from([(n, node_name) for n in neighbors])

            # Attach accumulated attributes to edges
            for node, attrs in neighbors_dict.items():
                if node not in nodes:
                    self.set_edge(node, node_name, attrs)

        return node_name

    def clone_node(self, node, name=None):
        """Clone existing node and all its edges."""
        if node not in self.nodes():
            raise ValueError("Node %s does not exist" % str(node))

        if name is None:
            new_node = "%s_copy" % str(node)
            while new_node in self.nodes():
                new_node = "%s_copy" % new_node
        else:
            if name in self.nodes():
                raise ValueError("Node %s already exist!" % str(name))
            else:
                new_node = name

        self.add_node(new_node, self.node[node].type_,
                       deepcopy(self.node[node].attrs_))

        # Connect all the edges
        if self.is_directed():
            self.add_edges_from(
                [(n, new_node) for n, _ in self.in_edges(node)])
            self.add_edges_from(
                [(new_node, n) for _, n in self.out_edges(node)])

            # Copy the attributes of the edges
            for s, t in self.in_edges(node):
                self.edge[s][new_node] = deepcopy(self.edge[s][t])
            for s, t in self.out_edges(node):
                self.edge[new_node][t] = deepcopy(self.edge[s][t])
        else:
            self.add_edges_from(
                [(n, new_node) for n in self.neighbors(node)])

            # Copy the attributes of the edges
            for n in self.neighbors(node):
                self.set_edge(new_node, n, deepcopy(self.edge[n][node]))

        return new_node

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

    def load(self, filename):
        """Create graph from JSON file"""
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                j_data = json.loads(f.read())
                # start graph init
                loaded_nodes = []
                if "nodes" in j_data.keys():
                    j_nodes = j_data["nodes"]
                    for node in j_nodes:
                        if "id" in node.keys():
                            node_id = node["id"]
                        else:
                            raise ValueError(
                                "Error loading graph: node id is not specified!")
                        if "type" in node.keys():
                            node_type = node["type"]
                        else:
                            raise ValueError(
                                "Error loading graph: node type is not specified!")
                        attrs = None
                        if "attrs" in node.keys():
                            attrs = node["attrs"]
                        loaded_nodes.append((node_id, node_type, attrs))
                else:
                    raise ValueError(
                        "Error loading graph: no nodes specified!")
                loaded_edges = []
                if "edges" in j_data.keys():
                    j_edges = j_data["edges"]
                    for edge in j_edges:
                        if "from" in edge.keys():
                            s_node = edge["from"]
                        else:
                            raise ValueError(
                                "Error loading graph: edge source is not specified!")
                        if "to" in edge.keys():
                            t_node = edge["to"]
                        else:
                            raise ValueError(
                                "Error loading graph: edge target is not specified!")
                        if "attrs" in edge.keys():
                            attrs = edge["attrs"]
                            if type(attrs) == list:
                                attrs = set(attrs)
                            loaded_edges.append((s_node, t_node, attrs))
                        else:
                            loaded_edges.append((s_node, t_node))
                else:
                    raise ValueError(
                        "Error loading graph: no edges specified!")
                nx.DiGraph.clear(self)
                self.add_nodes_from(loaded_nodes)
                self.add_edges_from(loaded_edges)
        else:
            raise ValueError(
                "Error loading graph: file '%s' does not exist!" %
                filename)

    def export(self, filename):
        """Export graph to JSON file"""
        j_data = {"edges": [], "nodes": []}
        # dump nodes
        for node in self.nodes():
            node_data = {}
            node_data["id"] = node
            node_data["type"] = self.node[node].type_
            if self.node[node].attrs_ is not None:
                attrs = {}
                for key, value in self.node[node].attrs_.items():
                    if type(value) == set:
                        attrs[key] = list(value)
                    else:
                        attrs[key] = value
                node_data["attrs"] = attrs
            j_data["nodes"].append(node_data)
        # dump edges
        for s, t in self.edges():
            edge_data = {}
            edge_data["from"] = s
            edge_data["to"] = t
            if self.edge[s][t] is not None:
                attrs = {}
                for key, value in self.edge[s][t].items():
                    if type(value) == set:
                        attrs[key] = list(value)
                    else:
                        attrs[key] = value
                edge_data["attrs"] = attrs
            j_data["edges"].append(edge_data)

        with open(filename, 'w') as f:
            json.dump(j_data, f)


class TypedGraph(TypedDiGraph):
    """Define simple typed undirected graph."""

    def __init__(self, metamodel=None):
        TypedDiGraph.__init__(self, metamodel)

    def add_edge(self, s, t, attrs=None, **attr):
        TypedDiGraph.add_edge(self, s, t, attrs, **attr)
        TypedDiGraph.add_edge(self, t, s, attrs, **attr)

    def remove_edge(self, source, target):
        TypedDiGraph.remove_edge(self, source, target)
        TypedDiGraph.remove_edge(self, target, source)

    def add_edge_attrs(self, node_1, node_2, attrs_dict):
        TypedDiGraph.add_edge_attrs(self, node_1, node_2, attrs_dict)
        TypedDiGraph.add_edge_attrs(self, node_2, node_1, attrs_dict)

    def update_edge_attrs(self, node_1, node_2, new_attrs):
        TypedDiGraph.update_edge_attrs(self, node_1, node_2, new_attrs)
        TypedDiGraph.update_edge_attrs(self, node_1, node_2, new_attrs)

    def remove_edge_attrs(self, node_1, node_2, attrs_dict):
        TypedDiGraph.remove_edge_attrs(self, node_1, node_2, attrs_dict)
        TypedDiGraph.remove_edge_attrs(self, node_2, node_1, attrs_dict)

    def set_edge(self, u, v, attrs):
        TypedDiGraph.set_edge(self, u, v, attrs)
        TypedDiGraph.set_edge(self, v, u, attrs)

class Homomorphism(object):
    """Define graph homomorphism data structure."""

    def __init__(self, source, target, dictionary):
        if Homomorphism.is_valid_homomorphism(source, target, dictionary):
            self.source_ = source
            self.target_ = target
            self.mapping_ = dictionary
        else:
            raise ValueError("Homomorphism is not valid!")

    def __str__(self):
        return "Source :\n%sTarget :\n%sMapping :\n%s" % \
            (str(self.source_),str(self.target_),str(self.mapping_))

    def is_monic(self):
        """Check if the homomorphism is monic."""
        return len(set(self.mapping_.keys())) ==\
            len(set(self.mapping_.values()))

    @staticmethod
    def is_valid_homomorphism(source, target, dictionary):
        """Check if the homomorphism is valid (preserves edges)."""
        # check if there is mapping for all the nodes of source graph
        if set(source.nodes()) != set(dictionary.keys()):
            raise ValueError(
                "Invalid homomorphism: Mapping is not covering all the nodes of source graph!")

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
        return True

    @staticmethod
    def identity(A, B):
        """ Tries to create the identity homomorphism of A from A to B,
            fails if some nodes of A aren't found in B
        """
        dic = {}
        for n in A.nodes():
            if n in B.nodes():
                dic[n] = n
            else:
                raise ValueError(
                    "Node %s not found in the second graph" % n
                )
        return Homomorphism(A, B, dic)

    @staticmethod
    def compose(h1, h2):
        """ Returns h1.h2 : A -> C given h1 : B -> C and h2 : A -> B"""
        return Homomorphism(
            h2.source_,
            h1.target_,
            dict([(n, h1.mapping_[h2.mapping_[n]]) for n in h2.mapping_.keys()])
        )

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




class TypedHomomorphism(Homomorphism):
    """Define graph typed homomorphism data structure."""

    def __init__(self, source, target, dictionary):
        if TypedHomomorphism.is_valid_homomorphism(source, target, dictionary):
            self.source_ = source
            self.target_ = target
            self.mapping_ = dictionary
        else:
            raise ValueError("TypedHomomorphism is not valid!")


    @staticmethod
    def from_untyped(hom):
        """ Convert untyped Homomorphism to TypedHomomorphism by checking the
            types condition on the graphs
        """
        return TypedHomomorphism(hom.source_, hom.target_, hom.mapping_)

    @staticmethod
    def is_valid_homomorphism(source, target, dictionary):
        """Check if the homomorphism is valid (preserves edges and types)."""

        #check preserving of edges
        Homomorphism.is_valid_homomorphism(source, target, dictionary)

        # check nodes match with types and sets of attributes
        for s, t in dictionary.items():
            if (source.node[s].type_ != None) and (source.node[s].type_ != t):
                raise ValueError(
                    "Invalid homomorphism: Node type does not match (%s:%s and %s)!" %
                    (s, str(source.node[s].type_), str(t)))
            if not is_subdict(source.node[s].attrs_, target.node[t].attrs_):
                raise ValueError(
                    "Invalid homomorphism: Attributes of nodes source:'%s' and target:'%s' does not match!" %
                    (str(s), str(t)))

        # check edges attr matches
        for s_edge in source.edges():
            source_edge_attrs = source.get_edge(s_edge[0], s_edge[1])
            target_edge_attrs = target.get_edge(dictionary[s_edge[0]],
                                                dictionary[s_edge[1]])
            if not is_subdict(source_edge_attrs, target_edge_attrs):
                raise ValueError(
                    "Invalid homomorphism: Attributes of edges (%s)-(%s) and (%s)-(%s) does not match!" %
                    (s_edge[0], s_edge[1], dictionary[s_edge[0]],
                        dictionary[s_edge[1]]))

        return True

    @staticmethod
    def canonic(G, T):
        """ Tries to create the canonic TypedHomomorphism where each node is
            mapped to its type in the typing graph
        """
        if T == None:
            return None
        hom_dict = {}
        for n in G.nodes():
            if G.node[n].type_ == None:
                hom_dict[n] = n
            else:
                if not G.node[n].type_ in T.nodes():
                    raise ValueError(
                        "Type %s not found in typing graph" % str(G.node[n].type_)
                    )
                hom_dict[n] = G.node[n].type_
        return TypedHomomorphism(G, T, hom_dict)
