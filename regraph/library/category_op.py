"""Define category operations used by graph rewriting tool."""

from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism)
from regraph.library.utils import keys_by_value, merge_attributes, dict_sub


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

    # add nodes to the graph
    for n in C.nodes():
        a_keys = keys_by_value(g, n)
        # addition of new nodes
        if len(a_keys) == 0:
            new_name = n
            i = 1
            while new_name in D.nodes():
                new_name = str(n) + "_" + str(i)
                i += 1
            D.add_node(new_name,
                       C.node[n].type_,
                       C.node[n].attrs_)
            hom2[n] = n
        # addition of preserved nodes
        elif len(a_keys) == 1:
            a_key = a_keys[0]
            D.add_node(f[a_key],
                       C.node[n].type_,
                       B.node[f[a_key]].attrs_)
            D.add_node_attrs(f[a_key],
                             dict_sub(C.node[g[a_key]].attrs_, A.node[a_key].attrs_))
            hom1[f[a_key]] = f[a_key]
            hom2[g[a_key]] = f[a_key]
        # addition of merged nodes
        else:
            merging_nodes = []
            attrs = {}
            for a_key in a_keys:
                merging_nodes.append(f[a_key])
                attrs = merge_attributes(attrs, B.node[f[a_key]].attrs_)
            new_name = "_".join([str(node) for node in merging_nodes])

            D.add_node(new_name, C.node[n].type_, attrs)
            D.add_node_attrs(new_name, dict_sub(C.node[n].attrs_, attrs))
            
            for a_key in a_keys:
                hom1[f[a_key]] = new_name
                hom2[n] = new_name

    for n in B.nodes():
        if n not in f.values():
            D.add_node(n, B.node[n].type_, B.node[n].attrs_)
            hom1[n] = n

    # add edges to the graph
    for (n1, n2) in C.edges():
        a_keys_1 = keys_by_value(g, n1)
        a_keys_2 = keys_by_value(g, n2)
        if len(a_keys_1) == 0 or len(a_keys_2) == 0:
            D.add_edge(hom2[n1], hom2[n2], C.get_edge(n1, n2))
        else:
            for a_key_1 in a_keys_1:
                for a_key_2 in a_keys_2:
                    if A.is_directed():
                        if (f[a_key_1], f[a_key_2]) in B.edges():
                            D.add_edge(hom2[n1], hom2[n2], B.get_edge(f[a_key_1], f[a_key_2]))
                            D.add_edge_attrs(hom2[n1],
                                             hom2[n2],
                                             dict_sub(C.get_edge(n1, n2), A.get_edge(a_key_1, a_key_2)))
                    else:
                        if (f[a_key_1], f[a_key_2]) in B.edges() or (f[a_key_2], f[a_key_1]) in B.edges():
                            D.add_edge(hom2[n1], hom2[n2], B.get_edge(f[a_key_1], f[a_key_2]))
                            D.add_edge_attrs(hom2[n1],
                                             hom2[n2],
                                             dict_sub(C.get_edge(n1, n2), A.get_edge(a_key_1, a_key_2)))
    for (n1, n2) in B.edges():
        a_keys_1 = keys_by_value(f, n1)
        a_keys_2 = keys_by_value(f, n2)
        if len(a_keys_1) == 0 or len(a_keys_2) == 0:
            D.add_edge(hom1[n1], hom1[n2], B.get_edge(n1, n2))
    return (D,
            Homomorphism(B, D, hom1),
            Homomorphism(C, D, hom2))

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
        C.add_node(g[f[n]],
                   A.node[n].type_,
                   dict_sub(D.node[g[f[n]]].attrs_, B.node[f[n]].attrs_))
        C.add_node_attrs(g[f[n]], A.node[n].attrs_)
        hom1[n] = g[f[n]]
        hom2[g[f[n]]] = g[f[n]]

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

    # Add edges from preserved part
    for (n1, n2) in A.edges():
        attrs = dict_sub(D.get_edge(g[f[n1]], g[f[n2]]), B.get_edge(f[n1], f[n2]))
        C.add_edge(hom1[n1], hom1[n2], attrs)
        C.add_edge_attrs(hom1[n1], hom1[n2], A.get_edge(n1, n2))

    # Add remaining edges from D
    for (n1, n2) in D.edges():
        b_key_1 = keys_by_value(g, n1) 
        b_key_2 = keys_by_value(g, n2)
        if len(b_key_1) == 0 or len(b_key_2) == 0:
            C.add_edge(n1, n2, D.get_edge(n1, n2))

    return C, Homomorphism(A, C, hom1), Homomorphism(C, D, hom2)
