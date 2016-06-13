"""."""

import networkx as nx
import matplotlib.pyplot as plt


# taken from projx https://github.com/davebshow/projx
def colors_by_type(graph):
    """
    Generate colors for node by types.

    :returns: Dict. Nodes as keys, colors as values.
    """
    colors_dict = {}
    colors = []
    counter = 1
    for node in graph.nodes():
        if graph.node[node].type_ not in colors_dict:
            colors_dict[graph.node[node].type_] =\
                float(counter)
            colors.append(float(counter))
            counter += 1
        else:
            colors.append(colors_dict[graph.node[node].type_])
    return colors


def plot_graph(graph, types=True, filename=None):
        """Plot graph with node colors corresponding to types."""
        if types:
            color_list = colors_by_type(graph)
        else:
            color_list = None

        pos = nx.spring_layout(graph)
        nx.draw_networkx_nodes(graph, pos,
                               node_color=color_list,
                               node_size=100, arrows=True)
        nx.draw_networkx_edges(graph, pos, alpha=0.4)

        labels = {}
        for node in graph.nodes():
            labels[node] = node
        offset = 0.05
        for p in pos:  # raise text positions
            pos[p][1] += offset
        nx.draw_networkx_labels(graph, pos, labels, font_size=11)

        # save to the file
        if filename is not None:
            with open(filename, "w") as f:
                plt.savefig(f)
                plt.clf()
        else:
            plt.show()
        return


def plot_instance(graph, pattern, instance, filename=None):
        """Plot the graph with instance of pattern highlighted."""
        new_colors = ["g" if not graph.nodes()[i] in instance.values()
                      else "r" for i, c in enumerate(graph.nodes())]
        pos = nx.spring_layout(graph)
        nx.draw_networkx_nodes(
            graph, pos, node_color=new_colors,
            node_size=100, arrows=True)
        nx.draw_networkx_edges(graph, pos, alpha=0.4)

        # Draw pattern edges highlighted
        edgelist = [(instance[edge[0]], instance[edge[1]])
                    for edge in pattern.edges()]
        nx.draw_networkx_edges(
            graph, pos,
            edgelist=edgelist,
            width=3, alpha=0.5, edge_color='r')

        labels = {}
        for node in graph.nodes():
            labels[node] = node
        offset = 0.05
        for p in pos:  # raise text positions
            pos[p][1] += offset
        nx.draw_networkx_labels(graph, pos, labels, font_size=11)

        # color the instances
        plt.title("Graph with instance of pattern highlighted")
        if filename is not None:
            with open(filename, "w") as f:
                plt.savefig(f)
                plt.clf()
        else:
            plt.show()
        return


def is_subdict(small_dict, big_dict):
    """Check if the dictionary is a subset of other."""

    if small_dict is None:
        return True
    if len(small_dict) == 0:
        return True
    if big_dict is None and len(small_dict) != 0:
        return True
    if len(big_dict) == 0 and len(small_dict) != 0:
        return False
    for key, value in small_dict.items():
        if key not in big_dict.keys():
            return False
        else:
            if type(value) == set:
                small_attrs = value
            else:
                small_attrs = set([value])
            if type(big_dict[key]) == set:
                big_attrs = big_dict[key]
            else:
                big_attrs = set([big_dict[key]])
            if not small_attrs.issubset(big_attrs):
                return False
    return True


def keys_by_value(dictionary, val):
    res = []
    for key, value in dictionary.items():
        if value == val:
            res.append(key)
    return res

def fold_left(f, init, l):
    """ f : a -> b -> b
        init : b
        l : a list
        Returns f(...f(l[1],f(l[0], init)) """
    res = init
    for x in l:
        res = f(x, res)
    return res

def normalize_attrs(attrs_):
    if attrs_ != None:
        for k,v in attrs_.items():
            if type(v) != set:
                if type(v) == list:
                    attrs_[k] = set(v)
                else:
                    attrs_[k] = {v}
