"""Defines primitives for self transformation."""
import warnings
from copy import deepcopy

def remove_edge(self, source, target):
    """Remove edge from the graph."""
    if (source, target) in self.edges() or (target, source) in self.edges():
        nx.DiGraph.remove_edge(source, target)
    else:
        raise ValueError(
            "Edge %s->%s does not exist!" % (str(source), str(target)))

def add_edge_attrs(self, node_1, node_2, attrs_dict):
    if (node_1, node_2) not in self.edges() and (node_2, node_1) not in self.edges():
        raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
    else:
        normalize_attrs(attrs_dict)
        for key, value in attrs_dict.items():
            if key not in self.edge[node_1][node_2].keys():
                self.edge[node_1][node_2].update({key: value})
                self.edge[node_2][node_1].update({key: value})
            else:
                self.edge[node_1][node_2][key].update(value)
                self.edge[node_2][node_1][key].update(value)


def remove_edge_attrs(self, node_1, node_2, attrs_dict):
    if (node_1, node_2) not in self.edges() and (node_2, node_1) not in self.edges():
        raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
    else:
        normalize_attrs(attrs_dict)
        for key, value in attrs_dict.items():
            if key not in self.edge[node_1][node_2].keys():
                warnings.warn(
                    "Edge %s-%s does not have attribute '%s'" %
                    (str(node_1), str(node_2), str(key)), RuntimeWarning)
            else:
                elements_to_remove = []
                for el in value:
                    if el in self.edge[node_1][node_2][key]:
                        elements_to_remove.append(el)
                    else:
                        warnings.warn(
                            "Edge %s-%s does not have attribute '%s' with value '%s'" %
                            (str(node_1), str(node_2), str(key), str(el)), RuntimeWarning)
                for el in elements_to_remove:
                    self.edge[node_1][node_2][key].remove(el)


def update_node_attrs(self, node, new_attrs):
    if node not in self.nodes():
        raise ValueError("Node %s does not exist" % str(node))
    else:
        normalize_attrs(new_attrs)
        if self.node[node].attrs_ is None:
            self.node[node].attrs_ = new_attrs
        else:
            for key, value in new_attrs.items():
                self.node[node].attrs_[key] = value


def update_edge_attrs(self, node_1, node_2, new_attrs):
    if (node_1, node_2) not in self.edges() and (node_2, node_1) not in self.edges():
        raise ValueError("Edge %s-%s does not exist" % (str(node_1), str(node_2)))
    else:
        normalize_attrs(new_attrs)
        for key, value in new_attrs.items():
            self.edge[node_1][node_2][key] = value
            if not self.is_directed():
                self.edge[node_2][node_1][key] = value
