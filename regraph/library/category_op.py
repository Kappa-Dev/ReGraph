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
            str(f[node]) + "_" + str(g[node]),
            A.node[node].type_,
            merge_attributes(
                B.node[f[node]].attrs_,
                C.node[g[node]].attrs_,
                "union"
            )
        )
        hom1[f[node]] =\
            str(f[node]) + "_" + str(g[node])
        hom2[g[node]] =\
            str(f[node]) + "_" + str(g[node])

    for s, t in A.edges():
        D.add_edge(
            str(f[s]) + "_" + str(g[s]),
            str(f[t]) + "_" + str(g[t]),
            merge_attributes(
                B.get_edge(f[s], f[t]),
                C.get_edge(g[s], g[t]),
                "union"
            )
        )

    for node in B.nodes():
        if node not in f.values():
            D.add_node(
                str(node) + "_",
                B.node[node].type_,
                B.node[node].attrs_
            )
            hom1[node] = str(node) + "_"

    for node in C.nodes():
        if node not in g.values():
            if str(node)+"_" not in D.nodes():
                D.add_node(
                    str(node) + "_",
                    C.node[node].type_,
                    C.node[node].attrs_
                )
            hom2[node] = str(node) + "_"

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

    if type(h1.source_) == TypedGraph:
        C = TypedGraph()
    else:
        C = TypedDiGraph()

    A = h1.source_
    B = h1.target_
    D = h2.target_
    f = h1.mapping_
    g = h2.mapping_


    hom1 = {}
    hom2 = {}

    for node in D.nodes():
        B_node = keys_by_value(g, node)
        if len(B_node) > 0:
            mapped_A_nodes = keys_by_value(f, B_node[0])
            for A_node in mapped_A_nodes:
                C.add_node(
                    A_node,
                    D.node[g[f[A_node]]].type_,
                    merge_attributes(
                        A.node[A_node].attrs_,
                        D.node[g[f[A_node]]].attrs_,
                        "intersection"
                    )
                )
                hom1[A_node] = A_node
                hom2[A_node] = g[f[A_node]]
        else:
            C.add_node(
                str(node) + "_",
                D.node[node].type_,
                D.node[node].attrs_
            )
            hom2[str(node) + "_"] = node
    for s, t in D.edges():
        B_s = keys_by_value(g, s)
        B_t = keys_by_value(g, t)
        if len(B_s) > 0 and len(B_t) > 0:
            mapped_A_ss = keys_by_value(f, B_s[0])
            mapped_A_ts = keys_by_value(f, B_t[0])
            for A_s in mapped_A_ss:
                for A_t in mapped_A_ts:
                    if C.is_directed():
                        if (A_s, A_t) not in A.edges() or \
                           (C.is_directed() and ((A_s, A_t) not in A.edges() and \
                           (A_t, A_s) not in A.edges())):
                            C.add_edge(
                                hom1[A_s],
                                hom1[A_t],
                                D.get_edge(
                                    g[f[A_s]],
                                    g[f[A_t]])
                            )
                        else:
                            C.add_edge(
                                hom1[A_s],
                                hom1[A_t],
                                merge_attributes(
                                    A.get_edge(A_s, A_t),
                                    D.get_edge(
                                        g[f[A_s]],
                                        g[f[A_t]]),
                                    "intersection"
                                )
                            )
        else:
            if len(B_s) == 0:
                sources_to_add = [str(s) + "_"]
            else:
                mapped_A_ss = keys_by_value(f, B_s[0])
                sources_to_add = [hom1[A_s] for A_s in mapped_A_ss]
            if len(B_t) == 0:
                targets_to_add = [str(t) + "_"]
            else:
                mapped_A_ts = keys_by_value(f, B_t[0])
                targets_to_add = [hom1[A_t] for A_t in mapped_A_ts]
            for new_s in sources_to_add:
                for new_t in targets_to_add:
                    C.add_edge(
                        new_s,
                        new_t,
                        D.edge[s][t])

    return C, Homomorphism(A, C, hom1), Homomorphism(C, D, hom2)
