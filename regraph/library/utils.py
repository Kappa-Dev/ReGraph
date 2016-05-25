"""."""

import networkx as nx
import matplotlib.pyplot as plt


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
        nx.draw_networkx_edges(graph, pos, alpha=0.6)

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


def plot_instance(graph, pattern, instance, filename):
        """Plot the graph with instance of pattern highlighted."""
        new_colors = ["g" if not graph.nodes()[i] in instance.values()
                      else "r" for i, c in enumerate(graph.nodes())]
        pos = nx.spring_layout(graph)
        nx.draw_networkx_nodes(
            graph, pos, node_color=new_colors,
            node_size=100, arrows=True)
        nx.draw_networkx_edges(graph, pos, alpha=0.6)

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
    return set(small_dict.items()).issubset(set(big_dict.items()))
