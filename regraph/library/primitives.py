"""Defines primitives for graph transformation."""

import itertools


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


def merge_nodes(graph, nodes, method="union", node_name=None):
    """Merge two nodes."""
    if method is None:
        method = "union"

    # generate name for new node
    if node_name is None:
        node_name = "_".join([str(n) for n in nodes])
    elif node_name in graph.nodes():
        raise ValueError(
            "The node with name '%s' already exists!" % str(node_name))

    graph.add_node(node_name)

    # merge data attached to node according to the method specified
    # restore proper connectivity
    if method == "union":
        attr_accumulator = {}
    elif method == "intersection":
        attr_accumulator = graph.node[nodes[0]]
    else:
        raise ValueError("Merging method %s is not defined!" % method)
    source_nodes = set()
    target_nodes = set()
    for node in nodes:
        attr_accumulator = merge_attributes(
            attr_accumulator, graph.node[node], method)
        source_nodes.update(
            [n if n not in nodes else node_name
             for n, _ in graph.in_edges(node)])
        target_nodes.update(
            [n if n not in nodes else node_name
             for _, n in graph.out_edges(node)])
        graph.remove_node(node)

    graph.node[node_name] = attr_accumulator
    print(graph.node[node_name])
    graph.add_edges_from([(n, node_name) for n in source_nodes])
    graph.add_edges_from([(node_name, n) for n in target_nodes])


def clone_node(graph, node):
    """Clone existing node and all its edges."""
    new_node = "%s_copy" % str(node)
    while new_node in graph.nodes():
        new_node = "%s_copy" % new_node

    graph.add_node(new_node)

    # Copy the attributes
    graph.node[new_node] = graph.node[node]

    # Connect all the edges
    graph.add_edges_from(
        [(n, new_node) for n, _ in graph.in_edges(node)])
    graph.add_edges_from(
        [(new_node, n) for _, n in graph.out_edges(node)])


def add_node(graph, name=None, type=None, attrs={}):
    """Add new node to the graph."""
    if name is not None:
        graph.add_node(name)
        graph.node[name] = attrs
    else:
        i = 0
        new_name = "new_node_%d" % i
        while new_name in graph.nodes():
            i += 1
            new_name = "new_node_%d" % i
        graph.add_node(new_name)
        graph.node[new_name] = attrs
    return


def remove_node(graph, node):
    """Remove node from the graph."""
    if node in graph.nodes():
        graph.remove_node(node)
    return


def add_edge(graph, source, target):
    """Add edge to the graph."""
    if not (source, target) in graph.edges():
        graph.add_edge(source, target)
    return


def remove_edge(graph, source, target):
    """Remove edge from the graph."""
    if (source, target) in graph.edges():
        graph.remove_edge(source, target)
    return
