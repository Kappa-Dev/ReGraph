"""Define category operations used by graph rewriting tool."""

from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism)
from regraph.library.utils import keys_by_value, merge_attributes


def pullback(h1, h2):
    """ Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
        with rh1 : A -> B; rh2 : A -> C and A the pullback"""

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
            "Homomorphisms don't have the same codomain, can't do pullback.\nh1: %s\nh2:%s\n" %
            (h1, h2)
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
        with rh1 : B -> D; rh2 : C -> D and D the pushout"""

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
    D = type(B)()
    f = h1.mapping_
    g = h2.mapping_

    for n in C.nodes():
        D.add_node(n,
                   C.node[n].type_,
                   C.node[n].attrs_)
        hom2[n] = n

    for n in B.nodes():
        pred_n = keys_by_value(f, n)
        if len(pred_n) == 0:
            new_name = n
            i = 1
            while new_name in D.nodes():
                new_name = str(n) + str(i)
                i += 1
            D.add_node(new_name,
                       B.node[n].type_,
                       B.node[n].attrs_)
            hom1[n] = new_name
        else:
            hom1[n] = hom2[g[pred_n[0]]]
            D.add_node_attrs(hom1[n], B.node[n].attrs_)

    for (n1, n2) in C.edges():
        D.add_edge(n1, n2, C.get_edge(n1, n2))

    for (n1, n2) in B.edges():
        if (hom1[n1], hom1[n2]) in D.edges():
            D.add_edge_attrs(hom1[n1], hom1[n2], B.get_edge(n1, n2))
        else:
            D.add_edge(hom1[n1], hom1[n2], B.get_edge(n1, n2))

    return (D, Homomorphism(B, D, hom1), Homomorphism(C, D, hom2))

def pullback_complement(h1, h2):
    """ Given h1 : A -> B; h2 : B -> D returns C, rh1, rh2
        with rh1 : A -> C; rh2 : C -> D and C the pullback_complement.
        Doesn't work if h2 is not a matching"""

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
    C = type(B)()
    f = h1.mapping_
    g = h2.mapping_

    hom1 = {}
    hom2 = {}

    A_D = Homomorphism.compose(h2, h1)

    DmB = D.sub(B, h2)

    for n in A.nodes():
        C.add_node(n,
                   A.node[n].type_,
                   A.node[n].attrs_)
        hom1[n] = n
        hom2[n] = g[f[n]]

    for n in DmB.nodes():
        is_in_A = False
        for n0 in A.nodes():
            if g[f[n0]] == n:
                is_in_A = True
                break;
        if not is_in_A:
            if DmB.node[n].type_ is None:
                C.add_node(n,
                           None,
                           DmB.node[n].attrs_)
            else:
                C.add_node(n,
                           DmB.node[n].type_,
                           DmB.node[n].attrs_)
            hom2[n] = n

    for n1 in C.nodes():
        for n2 in C.nodes():
            if n1 in A.nodes():
                if n2 in A.nodes():
                    if (n1, n2) in A.edges():
                        C.add_edge(n1,
                                   n2,
                                   A.get_edge(n1, n2))
                    pred_n1 = keys_by_value(hom1, n1)[0]
                    pred_n2 = keys_by_value(hom1, n2)[0]
                    n11 = f[n1]
                    n21 = f[n2]
                    if ((g[n11], g[n21]) in D.edges() and\
                        (n11, n21) not in B.edges()):
                        C.add_edge(n1,
                                   n2,
                                   D.get_edge(g[n11], g[n21]))
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

    return C, Homomorphism(A, C, hom1), Homomorphism(C, D, hom2)
