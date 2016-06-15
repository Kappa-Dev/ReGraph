from regraph.library.data_structures import (TypedGraph,
                                             TypedDiGraph,
                                             Homomorphism)
from regraph.library.primitives import (merge_attributes)
from regraph.library.utils import keys_by_value


def pullback(h1, h2):
    """ Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
        with rh1 : A -> B; rh2 : A -> C """
    if h1.target_ != D:
        raise ValueError(
            "Homomorphisms don't have the same codomain, can't do pullback"
        )
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

    for n1 in B.nodes():
        for n2 in C.nodes():
            if not f[n1] in A.nodes():
                if f[n1] == g[n2]:
                    A.add_node(f[n1],
                                       h1.target_.node[f[n1]].type_,
                                       merge_attributes(B.node[n1].attrs_,
                                                        C.node[n2].attrs_,
                                                        'intersection'))

                    hom1[f[n1]] = n1
                    hom2[g[n2]] = n2

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
            "Homomorphisms don't have the same codomain, can't do pushout"
        )

    if type(h1.source_) == TypedGraph:
        D = TypedGraph()
    else:
        D = TypedDiGraph()

    hom1 = {}
    hom2 = {}

    A = h1.source_
    B = h1.target_
    C = h2.target_
    f = h1.mapping_
    g = h2.mapping_

    for n1 in B.nodes():
        D.add_node(n1,
                   B.node[n1].type_,
                   B.node[n1].attrs_)
        hom1[n1] = n1
    for n2 in C.nodes():
        if not n2 in D.nodes():
            D.add_node(n2,
                       C.node[n2].type_,
                       C.node[n2].attrs_)
        hom2[n2] = n2

    equiv_set = {}
    for n in A.nodes():
        if B.node[f[n]].type_ = C.node[g[n].type_]:
            if not hom1[f[n]] == hom2[g[n]]:
                D.merge_nodes([hom1[f[n]];
                               hom2[g[n]]],
                              node_name = B.node[f[n]].type_)
            hom1[f[n]] = B.node[f[n]].type_
            hom2[g[n]] = B.node[f[n]].type_
        else:
            raise ValueError(
                "Unconsistant types for %s and %s, they should have \
                the same type since they have the same predecessor in \
                their source graph. Can't do pushout."
            )

    for n1 in D.nodes():
        for n2 in D.nodes():
            if (n1, n2) in B.edges():
                if (n1, n2) in C.edges():
                    D.add_edge(hom1[n1],
                               hom2[n2],
                               merge_attributes(B.get_edge(n1, n2),
                                                C.get_edge(n1, n2)))
                else:
                    D.add_edge(hom1[n1],
                               hom2[n2],
                               B.get_edge(n1, n2))
            else:
                if (n1, n2) in C.edges():
                    D.add_edge(hom1[n1],
                               hom2[n2],
                               C.get_edge(n1, n2))

    return D, Homomorphism(B, D, hom1), Homomorphism(C, D, hom2)

def pullback_complement(h1, h2):
    """ Given h1 : A -> B; h2 : B -> D returns C, rh1, rh2
        with rh1 : A -> C; rh2 : C -> D """

    if h1.target_ != h2.source_:
        raise ValueError(
            "Homomorphisms don't match, can't do pullback_complement"
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

    for n in B.nodes():
        if n in f.values():
            count_n = fold_left(lambda (k,v), acc : acc+[k] if x == n else acc,
                                f.items(),
                                [])
            while len(count_n) > 1:
                C.clone_node(n, name=count_n[-1])
                del count_n[-1]
        else:
            C.remove_node(g[n])

    for (n1, n2) in B.edges():
        pred_n1 = fold_left(lambda (k, v), acc : k if v == n1 else acc,
                            f.items(),
                            None)
        pred_n2 = fold_left(lambda (k, v), acc : k if v == n2 else acc,
                            g.items(),
                            None)
        if not (pred_n1, pred_n2) in A.edges():
            C.remove_edge(g[n1], g[n2])

    hom1 = dict[(n, g[f[n]]) for n in A.nodes()]
    hom2 = dict[(n, n) for n in C.nodes():]



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
                    str(A_node) + "_" + str(node),
                    D.node[g[f[A_node]]].type_,
                    merge_attributes(
                        A.node[A_node].attrs_,
                        D.node[g[f[A_node]]].attrs_,
                        "intersection"
                    )
                )
                hom1[A_node] = str(A_node) + "_" + str(node)
                hom2[str(A_node) + "_" + str(node)] = g[f[A_node]]
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
                        if (A_s, A_t) not in A.edges():
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
                        if (A_s, A_t) not in A.edges() and (A_t, A_s) not in A.edges():
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
