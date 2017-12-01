import copy

import networkx as nx
import numpy as np

from regraph.utils import keys_by_value
from matplotlib import pyplot as plt


def _ticks_off():
    plt.tick_params(
        axis='x',           # changes apply to the x-axis
        which='both',       # both major and minor ticks are affected
        bottom='off',       # ticks along the bottom edge are off
        top='off',          # ticks along the top edge are off
        labelbottom='off')  # labels along the bottom edge are off
    plt.tick_params(
        axis='y',           # changes apply to the x-axis
        which='both',       # both major and minor ticks are affected
        left='off',         # ticks along the bottom edge are off
        right='off',        # ticks along the top edge are off
        labelleft='off')    # labels along the bottom edge are off


def _set_limits(nodes, labels, margin=0.1):
    xmin = min([
        p[0] for _, p in nodes.items()
    ])
    xmax = max([
        p[0] for _, p in nodes.items()
    ])
    ymin = min([
        p[1] for _, p in nodes.items()
    ])
    ymax = max([
        p[1] for _, p in labels.items()
    ])

    plt.xlim([
        xmin - margin * abs(xmax - xmin),
        xmax + margin * abs(xmax - xmin)
    ])
    plt.ylim([
        ymin - margin * abs(ymax - ymin),
        ymax + margin * abs(ymax - ymin)
    ])
    return


def plot_graph(graph, types=True, filename=None, parent_pos=None):
    """Plot graph with node colors corresponding to types."""
    # if types:
    #     color_list = colors_by_type(graph)
    # else:
    #     color_list = None
    if not parent_pos:
        pos = nx.spring_layout(graph)
    else:
        pos = copy.deepcopy(parent_pos)
        random_pos = nx.spring_layout(graph)
        for node in graph.nodes():
            if node not in pos:
                pos[node] = random_pos[node]

    nx.draw_networkx_nodes(graph, pos,
                           node_color='green',
                           # node_color=color_list,
                           node_size=100, arrows=True)
    nx.draw_networkx_edges(graph, pos, alpha=0.4)

    labels = {}
    for node in graph.nodes():
        labels[node] = str(node)
        # if types:
        #     labels[node] += ":" + str(graph.node[node].type_)
    offset = 0.1
    labels_pos = copy.deepcopy(pos)
    for p in pos:  # raise text positions
        labels_pos[p][1] += offset
    nx.draw_networkx_labels(graph, labels_pos, labels, font_size=11)

    _ticks_off()
    _set_limits(pos, labels_pos)
    # save to the file
    if filename is not None:
        # with open(filename, "w") as f:
            # plt.savefig(f)
        plt.savefig(filename)
        plt.clf()
    else:
        plt.show()
    return pos


def plot_instance(graph, pattern, instance, filename=None, parent_pos=None):
    """Plot the graph with instance of pattern highlighted."""
    new_colors = ["g" if not graph.nodes()[i] in instance.values()
                  else "r" for i, c in enumerate(graph.nodes())]
    if not parent_pos:
        pos = nx.spring_layout(graph)
    else:
        pos = copy.deepcopy(parent_pos)
        random_pos = nx.spring_layout(graph)
        for node in graph.nodes():
            if node not in pos:
                pos[node] = random_pos[node]

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
    offset = 0.1
    labels_pos = copy.deepcopy(pos)
    for p in pos:  # raise text positions
        labels_pos[p][1] += offset
    nx.draw_networkx_labels(graph, labels_pos, labels, font_size=11)

    # color the instances
    # plt.title("Graph with instance of pattern highlighted")
    _ticks_off()
    _set_limits(pos, labels_pos)
    if filename is not None:
        with open(filename, "w") as f:
            plt.savefig(f)
            plt.clf()
    else:
        plt.show()
    return


def plot_rule(rule, filename=None):
    plt.figure(figsize=(14, 3))

    # generate colors
    p_colors_dict = {}
    p_colors = []
    for node in rule.p.nodes():
        lhs_node = rule.p_lhs[node]
        all_p_keys = keys_by_value(rule.p_lhs, lhs_node)
        if len(all_p_keys) > 1:
            found = None
            for p_key in all_p_keys:
                if p_key != node and p_key in p_colors_dict.keys():
                    found = p_key
                    break
            if found:
                p_colors_dict[node] = p_colors_dict[found]
                p_colors.append(p_colors_dict[found])
            else:
                p_colors_dict[node] = np.random.rand(3,)
                p_colors.append(p_colors_dict[node])
        else:
            p_colors_dict[node] = np.random.rand(3,)
            p_colors.append(p_colors_dict[node])

    lhs_colors = []
    for node in rule.lhs.nodes():
        p_keys = keys_by_value(rule.p_lhs, node)
        if len(p_keys) > 0:
            lhs_colors.append(p_colors_dict[p_keys[0]])
        else:
            lhs_colors.append(np.random.rand(3,))

    rhs_colors = []
    for node in rule.rhs.nodes():
        p_keys = keys_by_value(rule.p_rhs, node)
        if len(p_keys) > 0:
            rhs_colors.append(p_colors_dict[p_keys[0]])
        else:
            rhs_colors.append(np.random.rand(3,))

    p_pos = nx.spring_layout(rule.p)
    lhs_pos = nx.spring_layout(rule.lhs)
    rhs_pos = nx.spring_layout(rule.rhs)
    for node in rule.lhs.nodes():
        p_keys = keys_by_value(rule.p_lhs, node)
        if len(p_keys) > 0:
            lhs_pos[node] = p_pos[p_keys[0]]

    for node in rule.rhs.nodes():
        p_keys = keys_by_value(rule.p_rhs, node)
        if len(p_keys) > 0:
            rhs_pos[node] = p_pos[p_keys[0]]

    plt.subplot(1, 3, 1)
    plt.title("LHS")
    _ticks_off()
    plt.xlim([-0.5, 1.5])
    plt.ylim([-0.5, 1.5])
    nx.draw_networkx_nodes(rule.lhs, lhs_pos,
                           node_color=lhs_colors,
                           node_size=100, arrows=True)
    nx.draw_networkx_edges(rule.lhs, lhs_pos, alpha=0.4)

    labels = {}
    for node in rule.lhs.nodes():
        labels[node] = str(node)
        # if types:
        #     labels[node] += ":" + str(graph.node[node].type_)
    offset = 0.2
    lhs_label_pos = copy.deepcopy(lhs_pos)
    for p in lhs_pos:  # raise text positions
        lhs_label_pos[p][1] += offset
    nx.draw_networkx_labels(rule.lhs, lhs_label_pos, labels, font_size=11)

    plt.subplot(1, 3, 2)
    plt.title("P")
    _ticks_off()
    plt.xlim([-0.5, 1.5])
    plt.ylim([-0.5, 1.5])
    nx.draw_networkx_nodes(rule.p, p_pos,
                           node_color=p_colors,
                           node_size=100, arrows=True)
    nx.draw_networkx_edges(rule.p, p_pos, alpha=0.4)

    labels = {}
    for node in rule.p.nodes():
        labels[node] = str(node)
        # if types:
        #     labels[node] += ":" + str(graph.node[node].type_)
    offset = 0.2
    p_label_pos = copy.deepcopy(p_pos)
    for p in p_pos:  # raise text positions
        p_label_pos[p][1] += offset
    nx.draw_networkx_labels(rule.p, p_label_pos, labels, font_size=11)

    plt.subplot(1, 3, 3)
    plt.title("RHS")
    _ticks_off()
    plt.xlim([-0.5, 1.5])
    plt.ylim([-0.5, 1.5])
    nx.draw_networkx_nodes(rule.rhs, rhs_pos,
                           node_color=rhs_colors,
                           node_size=100, arrows=True)
    nx.draw_networkx_edges(rule.rhs, rhs_pos, alpha=0.4)

    labels = {}
    for node in rule.rhs.nodes():
        labels[node] = str(node)
    offset = 0.2
    rhs_label_pos = copy.deepcopy(rhs_pos)
    for p in rhs_pos:  # raise text positions
        rhs_label_pos[p][1] += offset
    nx.draw_networkx_labels(rule.rhs, rhs_label_pos, labels, font_size=11)

    if filename is not None:
        with open(filename, "w") as f:
            plt.savefig(f)
            plt.clf()
    else:
        plt.show()
    return
