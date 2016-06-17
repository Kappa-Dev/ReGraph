from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism)
from regraph.library.utils import keys_by_value, merge_attributes


def pullback(h1, h2):
    """ Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
        with rh1 : A -> B; rh2 : A -> C """

    if type(h1.target_) == TypedGraph:
        A = TypedGraph()
    else:
        A = TypedDiGraph()

    hom1 = {}
    hom2 = {}

    B = h1.source_
    C = h2.source_
    D = h2.target_
    f = h1.mapping_
    g = h2.mapping_

    if h1.target_ != D:
        raise ValueError(
            "Homomorphisms don't have the same codomain, can't do pullback"
        )

    for n1 in B.nodes():
        for n2 in C.nodes():
            if f[n1] == g[n2]:
                if not n1 in A.nodes():
                    A.add_node(n1,
                               B.node[n1].type_,
                               merge_attributes(B.node[n1].attrs_,
                                                C.node[n2].attrs_,
                                                'intersection'))

                    hom1[n1] = n1
                    hom2[n1] = n2
                else:
                    i=1
                    new_name = str(n1)+str(i)
                    while new_name in A.nodes():
                        i+=1
                        new_name = str(n1)+str(i)
                    if not n2 in A.nodes():
                        A.add_node(new_name,
                                   n2,
                                   merge_attributes(B.node[n1].attrs_,
                                                    C.node[n2].attrs_,
                                                    'intersection'))

                        hom1[new_name] = n1
                        hom2[new_name] = n2

    for n1 in A.nodes():
        for n2 in A.nodes():
            if (hom1[n1], hom1[n2]) in B.edges() or \
               ((not A.is_directed) and (hom1[n2], hom1[n1]) in B.edges()):
                if (hom2[n1], hom2[n2]) in C.edges() or \
                   ((not A.is_directed) and (hom2[n2], hom2[n1]) in C.edges()):
                    A.add_edge(n1, n2)
                    A.set_edge(
                        n1,
                        n2,
                        merge_attributes(
                            B.get_edge(hom1[n1], hom1[n2]),
                            C.get_edge(hom2[n1], hom2[n2]),
                            'intersection'))

    return A, Homomorphism(A, B, hom1), Homomorphism(A, C, hom2)

def pushout(h1, h2):
    """ Given h1 : A -> B; h2 : A -> C returns D, rh1, rh2
        with rh1 : B -> D; rh2 : C -> D """

    if h1.source_ != h2.source_:
        raise ValueError(
            "Domain of homomorphism 1 and domain of homomorphism 2 " +
            "don't match, can't do pushout"
        )

    hom1 = {}
    hom2 = {}

    A = h1.source_
    B = h1.target_
    C = h2.target_
    f = h1.mapping_
    g = h2.mapping_

    if type(B) == TypedGraph:
        D = TypedGraph()
    else:
        D = TypedDiGraph()

    for node in A.nodes():
        D.add_node(
            node,
            A.node[node].type_,
            merge_attributes(
                B.node[f[node]].attrs_,
                C.node[g[node]].attrs_,
                "union"
            )
        )
        hom1[f[node]] =\
            node
        hom2[g[node]] =\
            node

    for s, t in A.edges():
        D.add_edge(
            s,
            t,
            merge_attributes(
                B.get_edge(f[s], f[t]),
                C.get_edge(g[s], g[t]),
                "union"
            )
        )

    for node in B.nodes():
        if node not in f.values():
            if node in D.nodes():
                D.add_node(
                    str(node) + "_",
                    B.node[node].type_,
                    B.node[node].attrs_
                )
                hom1[node] = str(node) + "_"
            else:
                D.add_node(
                    node,
                    B.node[node].type_,
                    B.node[node].attrs_
                )
                hom1[node] = node
        else:
            hom1[node] = keys_by_value(f, node)[0]

    for node in C.nodes():
        if node not in g.values():
            new_name = node
            i = 1
            while new_name in D.nodes():
                new_name = str(node)+str(i)
                i += 1
            D.add_node(
                new_name,
                C.node[node].type_,
                C.node[node].attrs_
            )
            hom2[node] = new_name
        else:
            pred_node = keys_by_value(g, node)
            if len(pred_node) == 1:
                hom2[node] = pred_node[0]
            else:
                i = 1
                new_name = node
                while new_name in D.nodes():
                    new_name = str(node)+str(i)
                    i += 1
                D.merge_nodes(pred_node, node_name = new_name)
                hom2[node] = new_name

    for s, t in B.edges():
        if s not in f.values() or t not in f.values():
            D.add_edge(
                hom1[s],
                hom1[t],
                B.get_edge(s, t)
            )
        if (hom1[s], hom1[t]) not in D.edges() and \
           (D.is_directed or (hom1[t], hom1[s]) not in D.edges()):
            D.add_edge(
                hom1[s],
                hom1[t],
                B.get_edge(s, t)
            )

    for s, t in C.edges():
        if s not in g.values() or t not in g.values():
            D.add_edge(
                hom2[s],
                hom2[t],
                C.get_edge(s, t)
            )
        if (hom2[s], hom2[t]) not in D.edges() and \
           (D.is_directed or (hom2[t], hom2[s]) not in D.edges()):
            D.add_edge(
                hom2[s],
                hom2[t],
                C.get_edge(s, t)
            )

    return (D, Homomorphism(B, D, hom1), Homomorphism(C, D, hom2))

def pullback_complement(h1, h2):
    """ Given h1 : A -> B; h2 : B -> D returns C, rh1, rh2
        with rh1 : A -> C; rh2 : C -> D """

    if h1.target_ != h2.source_:
        raise ValueError(
            "Codomain of homomorphism 1 and domain of homomorphism 2 " +
            "don't match, can't do pullback complement"
        )

    if not h2.is_monic():
        raise ValueError(
            "Second homomorphism is not monic, cannot find final pullback complement"
        )

    A = h1.source_
    B = h1.target_
    D = h2.target_
    f = h1.mapping_
    g = h2.mapping_

    A_D = Homomorphism.compose(h2, h1)
    C = (D.sub(B, h2).add_nodes(A, A_D))

    for n1 in C.nodes():
        for n2 in C.nodes():
            if n1 in A.nodes():
                if n2 in A.nodes():
                    if (n1, n2) in A.edges():
                        C.add_edge(n1,
                                   n2,
                                   A.get_edge(n1, n2))
                else:
                    if (A_D.mapping_[n1], n2) in D.edges():
                        pred_n2 = keys_by_value(g, n2)
                        if len(pred_n2) == 0 or\
                           (len(pred_n2)>0 and (pred_n2[0], f[n2]) not in B.edges()):
                            C.add_edge(n1,
                                       n2,
                                       D.get_edge(A_D.mapping_[n1], n2))
            else:
                if n2 in A.nodes():
                    if (n1, A_D.mapping_[n2]) in D.edges():
                        pred_n1 = keys_by_value(g, n1)
                        if len(pred_n1) == 0 or\
                           (len(pred_n1)>0 and (pred_n1[0], f[n2]) not in B.edges()):
                            C.add_edge(n1,
                                       n2,
                                       D.get_edge(n1, A_D.mapping_[n2]))

                else:
                    if (n1, n2) in D.edges():
                        C.add_edge(n1,
                                   n2,
                                   D.get_edge(n1, n2))


    hom1 = Homomorphism.identity(A, C)
    hom2 = {}
    for n in C.nodes():
        if n in A.nodes():
            hom2[n] = A_D.mapping_[n]
        else:
            hom2[n] = n
    hom2 = Homomorphism(C, D, hom2)
    return C, hom1, hom2
