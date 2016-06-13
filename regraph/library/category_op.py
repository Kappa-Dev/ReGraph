from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism)
from regraph.library.primitives import (merge_attributes)
from regraph.library.utils import keys_by_value


def pullback(h1, h2):
    """ Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
        with rh1 : A -> B; rh2 : A -> C """
    if h1.target_ != h2.target_:
        raise ValueError(
            "Homomorphisms don't have the same codomain, can't do pullback"
        )
    if type(h1.target_) == TypedGraph:
        res_graph = TypedGraph()
    else:
        res_graph = TypedDiGraph()

    hom1 = {}
    hom2 = {}

    nodes = []
    for n1 in h1.source_.nodes():
        for n2 in h2.source_.nodes():
            if not h1.mapping_[n1] in res_graph.nodes():
                if h1.mapping_[n1] == h2.mapping_[n2]:
                    res_graph.add_node(h1.mapping_[n1],
                                       h1.target_.node[h1.mapping_[n1]].type_,
                                       merge_attributes(h1.source_.node[n1].attrs_,
                                                        h2.source_.node[n2].attrs_,
                                                        'intersection'))

                    hom1[h1.mapping_[n1]] = n1
                    hom2[h2.mapping_[n2]] = n2

    for n1 in res_graph.nodes():
        for n2 in res_graph.nodes():
            if (hom1[n1], hom1[n2]) in h1.source_.edges():
                if (hom2[n1], hom2[n2]) in h2.source_.edges():
                    res_graph.add_edge(n1, n2)
                    res_graph.set_edge(
                        n1,
                        n2,
                        merge_attributes(
                            h1.source_.get_edge(hom1[n1], hom1[n2]),
                            h2.source_.get_edge(hom2[n1], hom2[n2]),
                            'intersection'))

    res_h1 = Homomorphism(res_graph, h1.source_, hom1)
    res_h2 = Homomorphism(res_graph, h2.source_, hom2)

    return res_graph, res_h1, res_h2


def pullback_complement(hom):
    # edges to remove will be removed automatically upon removal of the nodes
    nodes = set([n for n in hom.target_.nodes()
                 if n not in hom.mapping_.values()])
    node_attrs = {}
    for node in hom.source_.nodes():
        if node not in node_attrs.keys():
            node_attrs.update({node: {}})

        mapped_node = hom.mapping_[node]
        mapped_attrs = hom.target_.node[mapped_node].attrs_

        attrs = hom.source_.node[node].attrs_
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
    for edge in hom.target_.edges():
        if hom.source_.is_directed():
            sources = keys_by_value(hom.mapping_, edge[0])
            targets = keys_by_value(hom.mapping_, edge[1])
            if len(sources) == 0 or len(targets) == 0:
                continue
            for s in sources:
                for t in targets:
                    if (s, t) not in hom.source_.edges():
                        edges.add((s, t))
        else:
            sources = keys_by_value(hom.mapping_, edge[0])
            targets = keys_by_value(hom.mapping_, edge[1])
            if len(sources) == 0 or len(targets) == 0:
                continue
            for s in sources:
                for t in targets:
                    if (s, t) not in hom.source_.edges():
                        if (t, s) not in hom.source_.edges():
                            edges.add((s, t))

    for edge in hom.source_.edges():
        if edge not in edge_attrs.keys():
            edge_attrs.update({edge: {}})

        mapped_edge = (hom.mapping_[edge[0]], hom.mapping_[edge[1]])
        mapped_attrs = hom.target_.edge[mapped_edge[0]][mapped_edge[1]]

        attrs = hom.source_.edge[edge[0]][edge[1]]

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


def pushout(hom):
    nodes = set([n for n in hom.target_.nodes() if n not in hom.mapping_.values()])

    node_attrs = {}
    for node in hom.source_.nodes():
        if node not in node_attrs.keys():
            node_attrs.update({node: {}})

        mapped_node = hom.mapping_[node]
        mapped_attrs = hom.target_.node[mapped_node].attrs_

        attrs = hom.source_.node[node].attrs_
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

    for edge in hom.target_.edges():
        sources = keys_by_value(hom.mapping_, edge[0])
        targets = keys_by_value(hom.mapping_, edge[1])
        if len(sources) == 0 or len(targets) == 0:
            edges[(edge[0], edge[1])] = hom.target_.edge[edge[0]][edge[1]]
            continue
        for s in sources:
            for t in targets:
                if (s, t) not in hom.source_.edges():
                    edges[(edge[0], edge[1])] = hom.target_.edge[edge[0]][edge[1]]

    for edge in hom.source_.edges():
        if edge not in edge_attrs.keys():
            edge_attrs.update({edge: {}})

        mapped_edge = (hom.mapping_[edge[0]], hom.mapping_[edge[1]])
        mapped_attrs = hom.target_.edge[mapped_edge[0]][mapped_edge[1]]

        attrs = hom.source_.edge[edge[0]][edge[1]]

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
