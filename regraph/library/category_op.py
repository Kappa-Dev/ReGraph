"""Category operations used by graph rewriting tool."""
import networkx as nx

from regraph.library.primitives import (add_node,
                                        add_edge,
                                        set_edge,
                                        add_node_attrs,
                                        get_edge,
                                        add_edge_attrs,
                                        clone_node,
                                        update_node_attrs,
                                        subtract,
                                        print_graph)
from regraph.library.utils import (keys_by_value,
                                   merge_attributes,
                                   dict_sub,
                                   valid_attributes)


def compose_homomorphisms(d2, d1):
    res = dict()
    for key, value in d1.items():
        if value in d2.keys():
            res[key] = d2[value]
    return res


def is_total_homomorphism(elements, mapping):
    """Return True if mapping is total."""
    return set(elements) == set(mapping.keys())


def check_totality(elements, dictionary):
    """Check that a mapping is total."""
    if set(elements) != set(dictionary.keys()):
        raise ValueError(
            "Invalid homomorphism: Mapping is not "
            "covering all the nodes of source graph!")


def check_homomorphism(source, target, dictionary,
                       ignore_attrs=False, total=True):
    """Check if the homomorphism is valid.

    Valid homomorphism preserves edges,
    and attributes if requires.
    """
    # check if there is mapping for all the nodes of source graph
    if total:
        check_totality(source.nodes(), dictionary)
    if not set(dictionary.values()).issubset(target.nodes()):
        raise ValueError(
            "invalid homomorphism: image not in target graph"
        )

    # check connectivity
    for s_edge in source.edges():
        try:
            if (s_edge[0] in dictionary.keys() and
                    s_edge[1] in dictionary.keys() and
                    not (dictionary[s_edge[0]], dictionary[s_edge[1]])
                    in target.edges()):
                if not target.is_directed():
                    if not (dictionary[s_edge[1]], dictionary[s_edge[0]]) in target.edges():
                        raise ValueError(
                            "Invalid homomorphism: Connectivity is not preserved!" +\
                            " Was expecting an edge '%s' and '%s'" %
                            (dictionary[s_edge[1]], dictionary[s_edge[0]]))
                else:
                    raise ValueError(
                        "Invalid homomorphism: Connectivity is not preserved!" +\
                        " Was expecting an edge between '%s' and '%s'" %
                        (dictionary[s_edge[0]], dictionary[s_edge[1]]))
        except KeyError:
            pass

    for s, t in dictionary.items():
        if not ignore_attrs:
            # check sets of attributes of nodes (here homomorphism = set inclusion)
            if not valid_attributes(source.node[s], target.node[t]):
                raise ValueError(
                    "Invalid homomorphism: Attributes of nodes source:'%s' and target:'%s' do not match!" %
                    (str(s), str(t)))

    if not ignore_attrs:
        # check sets of attributes of edges (homomorphism = set inclusion)
        for s1, s2 in source.edges():
            try:
                if (s1 in dictionary.keys() and s2 in dictionary.keys() and
                        not valid_attributes(
                            source.edge[s1][s2],
                            target.edge[dictionary[s1]][dictionary[s2]])):
                    raise ValueError(
                        "Invalid homomorphism: Attributes of edges (%s)-(%s) and (%s)-(%s) do not match!" %
                        (s1, s2, dictionary[s1], dictionary[s2]))
            except KeyError:
                pass
    return True


def compose_chain_homomorphisms(chain):
    homomorphism = chain[0]
    for i in range(1, len(chain)):
        homomorphism = compose_homomorphisms(
            chain[i],
            homomorphism
        )
    return homomorphism


def get_unique_map(a, b, c, d, a_b, b_d, c_d):
    a_c = dict()
    for node in b.nodes():
        a_keys = keys_by_value(a_b, node)
        if len(a_keys) > 0:
            # node stayed in the rule
            if node in b_d.keys():
                d_node = b_d[node]
                c_keys = keys_by_value(
                    c_d,
                    d_node
                )
                if len(a_keys) != len(c_keys):
                    raise ValueError("Map is not unique!")
                else:
                    for i, a_key in enumerate(a_keys):
                        a_c[a_key] = c_keys[i]
    return a_c


def identity(a, b):
    dic = {}
    for n in a.nodes():
        if n in b.nodes():
            dic[n] = n
        else:
            raise ValueError(
                "Node '%s' not found in the second graph!" % n
            )
    return dic


def is_monic(f):
    """Check if the homomorphism is monic."""
    return len(set(f.keys())) ==\
        len(set(f.values()))


def nary_pullback(b, cds):
    """Find a pullback with multiple conspans."""

    # 1. find individual pullbacks
    pullbacks = []
    for c_name, (c, d, b_d, c_d) in cds.items():
        pb = pullback(b, c, d, b_d, c_d, total=False)
        pullbacks.append((
            c_name, pb
        ))

    # 2. find pullbacks of pullbacks
    if len(pullbacks) > 1:
        c_name1, (a1, a_b1, a_c1) = pullbacks[0]
        a_c = dict([(c_name1, a_c1)])
        for i in range(1, len(pullbacks)):
            c_name2, (a2, a_b2, a_c2) = pullbacks[i]
            a1, a1_old_a1, a1_a2 = pullback(
                a1, a2, b, a_b1, a_b2,
                total=False
            )
            a_b1 = compose_homomorphisms(a_b1, a1_old_a1)
            # update a_c
            for c_name, old_a_c in a_c.items():
                a_c[c_name] = compose_homomorphisms(old_a_c, a1_old_a1)
            a_c[c_name2] = compose_homomorphisms(a_c2, a1_a2)

        # at the end of pullback iterations assign right a and a_b
        a_b = a_b1
        a = a1

        check_homomorphism(a, b, a_b, total=False)
        for c_name, a_c_guy in a_c.items():
            check_homomorphism(a, cds[c_name][0], a_c_guy, total=False)
        return (a, a_b, a_c)


def pullback(b, c, d, b_d, c_d, total=False):
    if total:
        return total_pullback(b, c, d, b_d, c_d)
    else:
        return partial_pullback(b, c, d, b_d, c_d)


def partial_pullback(b, c, d, b_d, c_d):
    try:
        check_totality(b, b_d)
        check_totality(c, c_d)
        return total_pullback(b, c, d, b_d, c_d)

    except ValueError:
        check_homomorphism(b, d, b_d, total=False)
        check_homomorphism(c, d, c_d, total=False)

        if b.is_directed():
            bd_dom = nx.DiGraph(b.subgraph(b_d.keys()))
            cd_dom = nx.DiGraph(c.subgraph(c_d.keys()))
        else:
            bd_dom = nx.Graph(b.subgraph(b_d.keys()))
            cd_dom = nx.Graph(c.subgraph(c_d.keys()))

        bd_b = {n: n for n in bd_dom.nodes()}
        cd_c = {n: n for n in cd_dom.nodes()}
        (tmp, tmp_bddom, tmp_cddom) = total_pullback(bd_dom, cd_dom, d, b_d, c_d)
        (b2, tmp_b2, b2_b) = pullback_complement(tmp, bd_dom, b, tmp_bddom, bd_b)
        (c2, tmp_c2, c2_c) = pullback_complement(tmp, cd_dom, c, tmp_cddom, cd_c)
        (new, b2_new, c2_new) = pushout(tmp, b2, c2, tmp_b2, tmp_c2)
        hom1 = {v: b2_b[k] for (k, v) in b2_new.items()}
        hom2 = {v: c2_c[k] for (k, v) in c2_new.items()}
        return(new, hom1, hom2)


def total_pullback(b, c, d, b_d, c_d):
    """Find pullback.

    Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
    with rh1 : A -> B; rh2 : A -> C and A the pullback.
    """
    if b.is_directed():
        a = nx.DiGraph()
    else:
        a = nx.Graph()

    # Check homomorphisms
    check_homomorphism(b, d, b_d)

    check_homomorphism(c, d, c_d)

    hom1 = {}
    hom2 = {}

    f = b_d
    g = c_d

    for n1 in b.nodes():
        for n2 in c.nodes():
            if f[n1] == g[n2]:
                if n1 not in a.nodes():
                    add_node(a,
                             n1,
                             merge_attributes(b.node[n1],
                                              c.node[n2],
                                              'intersection'))
                    hom1[n1] = n1
                    hom2[n1] = n2
                else:
                    i = 1
                    new_name = str(n1) + str(i)
                    while new_name in a.nodes():
                        i += 1
                        new_name = str(n1) + str(i)
                    # if n2 not in a.nodes():
                    add_node(a,
                             new_name,
                             merge_attributes(b.node[n1],
                                              c.node[n2],
                                              'intersection'))
                    hom1[new_name] = n1
                    hom2[new_name] = n2

    for n1 in a.nodes():
        for n2 in a.nodes():
            if (hom1[n1], hom1[n2]) in b.edges() or \
               ((not a.is_directed()) and (hom1[n2], hom1[n1]) in b.edges()):
                if (hom2[n1], hom2[n2]) in c.edges() or \
                   ((not a.is_directed) and (hom2[n2], hom2[n1]) in c.edges()):
                    add_edge(a, n1, n2)
                    set_edge(
                        a,
                        n1,
                        n2,
                        merge_attributes(
                            get_edge(b, hom1[n1], hom1[n2]),
                            get_edge(c, hom2[n1], hom2[n2]),
                            'intersection'))
    check_homomorphism(a, b, hom1)
    check_homomorphism(a, c, hom2)
    return (a, hom1, hom2)


def pushout(a, b, c, a_b, a_c, total=False):
    """Find pushout.

    Given h1 : A -> B; h2 : A -> C returns D, rh1, rh2
    with rh1 : B -> D; rh2 : C -> D and D the pushout.
    """
    if total:
        return total_pushout(a, b, c, a_b, a_c)
    else:
        return total_pushout(a, b, c, a_b, a_c)
        # return partial_pushout(a, b, c, a_b, a_c)


def partial_pushout(a, b, c, a_b, a_c):
    try:
        check_totality(a, a_b)
        check_totality(a, a_c)
        return total_pushout(a, b, c, a_b, a_c)

    except ValueError:
        check_homomorphism(a, b, a_b, total=False)
        check_homomorphism(a, c, a_c, total=False)
        if a.is_directed():
            ab_dom = nx.DiGraph(a.subgraph(a_b.keys()))
            ac_dom = nx.DiGraph(a.subgraph(a_c.keys()))
        else:
            ab_dom = nx.Graph(a.subgraph(a_b.keys()))
            ac_dom = nx.Graph(a.subgraph(a_c.keys()))

        ac_a = {n: n for n in ac_dom.nodes()}
        ab_a = {n: n for n in ab_dom.nodes()}

        (c2, a_c2, c_c2) = total_pushout(ac_dom, a, c, ac_a, a_c)
        (b2, a_b2, b_b2) = total_pushout(ab_dom, a, b, ab_a, a_b)

        (d, b2_d, c2_d) = total_pushout(a, b2, c2, a_b2, a_c2)
        b_d = compose_homomorphisms(b2_d, b_b2)
        c_d = compose_homomorphisms(c2_d, c_c2)

        return(d, b_d, c_d)


def total_pushout(a, b, c, a_b, a_c):
    # if h1.source_ != h2.source_:
    #     raise ValueError(
    #         "Domain of homomorphism 1 and domain of homomorphism 2 " +
    #         "don't match, can't do pushout"
    #     )
    check_homomorphism(a, b, a_b)
    check_homomorphism(a, c, a_c)

    hom1 = {}
    hom2 = {}

    d = type(b)()
    f = a_b
    g = a_c

    # add nodes to the graph
    for n in c.nodes():
        a_keys = keys_by_value(g, n)
        # addition of new nodes
        if len(a_keys) == 0:
            new_name = n
            i = 1
            while new_name in d.nodes():
                new_name = str(n) + "_" + str(i)
                i += 1
            add_node(
                d,
                new_name,
                c.node[n]
            )
            hom2[n] = n
        # addition of preserved nodes
        elif len(a_keys) == 1:
            a_key = a_keys[0]
            add_node(d, f[a_key],
                     b.node[f[a_key]])
            add_node_attrs(d, f[a_key],
                           dict_sub(c.node[g[a_key]], a.node[a_key]))
            hom1[f[a_key]] = f[a_key]
            hom2[g[a_key]] = f[a_key]
        # addition of merged nodes
        else:
            merging_nodes = []
            attrs = {}
            for a_key in a_keys:
                merging_nodes.append(f[a_key])
                attrs = merge_attributes(attrs, b.node[f[a_key]])
            new_name = "_".join([str(node) for node in merging_nodes])
            add_node(d, new_name, attrs)
            add_node_attrs(d, new_name, dict_sub(c.node[n], attrs))

            for a_key in a_keys:
                hom1[f[a_key]] = new_name
                hom2[n] = new_name

    for n in b.nodes():
        if n not in f.values():
            # if n not in d.nodes():
            new_name = n
            i = 1
            while new_name in d.nodes():
                new_name = str(n) + "_" + str(i)
                i += 1
            add_node(
                d,
                new_name,
                b.node[n]
            )
            hom1[n] = new_name

    # add edges to the graph
    for (n1, n2) in c.edges():
        a_keys_1 = keys_by_value(g, n1)
        a_keys_2 = keys_by_value(g, n2)
        if len(a_keys_1) == 0 or len(a_keys_2) == 0:
            add_edge(d, hom2[n1], hom2[n2], get_edge(c, n1, n2))
        else:
            for a_key_1 in a_keys_1:
                for a_key_2 in a_keys_2:
                    if (f[a_key_1], f[a_key_2]) in b.edges():
                        if (hom2[n1], hom2[n2]) not in d.edges():
                            add_edge(d, hom2[n1], hom2[n2], get_edge(b, f[a_key_1], f[a_key_2]))
                            if (a_key_1, a_key_2) in a.edges():
                                add_edge_attrs(d, hom2[n1],
                                               hom2[n2],
                                               dict_sub(get_edge(c, n1, n2),
                                               get_edge(a, a_key_1, a_key_2)))

                            else:
                                add_edge_attrs(d, hom2[n1],
                                               hom2[n2],
                                               get_edge(c, n1, n2))
                        else:
                            add_edge_attrs(d, hom2[n1],
                                           hom2[n2],
                                           get_edge(b, f[a_key_1], f[a_key_2]))
                            add_edge_attrs(d, hom2[n1],
                                           hom2[n2],
                                           dict_sub(get_edge(c, n1, n2),
                                                    get_edge(a, a_key_1, a_key_2)))
                    elif (hom2[n1], hom2[n2]) not in d.edges():
                        add_edge(d, hom2[n1], hom2[n2], get_edge(c, n1, n2))

    for (n1, n2) in b.edges():
        a_keys_1 = keys_by_value(f, n1)
        a_keys_2 = keys_by_value(f, n2)
        if len(a_keys_1) == 0 or len(a_keys_2) == 0:
            add_edge(d, hom1[n1], hom1[n2], get_edge(b, n1, n2))
        elif (hom1[n1], hom1[n2]) not in d.edges():
            add_edge(d, hom1[n1], hom1[n2], get_edge(b, n1, n2))

    check_homomorphism(b, d, hom1)
    check_homomorphism(c, d, hom2)
    return (d, hom1, hom2)


def pullback_complement(a, b, d, a_b, b_d):
    """Find pullback complement.

    Given h1 : A -> B; h2 : B -> D returns C, rh1, rh2
    with rh1 : A -> C; rh2 : C -> D and C the pullback_complement.
    Doesn't work if h2 is not a matching
    """

    check_homomorphism(a, b, a_b, total=True)
    check_homomorphism(b, d, b_d, total=True)

    if not is_monic(b_d):
        raise ValueError(
            "Second homomorphism is not monic, "
            "cannot find final pullback complement!"
        )

    c = type(b)()
    f = a_b
    g = b_d

    hom1 = {}
    hom2 = {}

    # a_d = compose_homomorphisms(g, f)
    d_m_b = subtract(d, b, g)

    for n in a.nodes():
        if g[f[n]] not in c.nodes():
            add_node(c, g[f[n]],
                     dict_sub(d.node[g[f[n]]], b.node[f[n]]))
            add_node_attrs(c, g[f[n]], a.node[n])
            hom1[n] = g[f[n]]
            hom2[g[f[n]]] = g[f[n]]
        else:
            new_name = clone_node(c, g[f[n]])
            update_node_attrs(
                c, new_name,
                dict_sub(d.node[g[f[n]]], b.node[f[n]])
            )
            add_node_attrs(c, new_name, a.node[n])
            hom1[n] = new_name
            hom2[new_name] = g[f[n]]

    for n in d_m_b.nodes():
        is_in_a = False
        for n0 in a.nodes():
            if g[f[n0]] == n:
                is_in_a = True
                break
        if not is_in_a:
            add_node(c, n, d_m_b.node[n])
            hom2[n] = n

    # Add edges from preserved part
    for (n1, n2) in a.edges():
        attrs = dict_sub(get_edge(d, g[f[n1]], g[f[n2]]), get_edge(b, f[n1], f[n2]))
        add_edge(c, hom1[n1], hom1[n2], attrs)
        add_edge_attrs(c, hom1[n1], hom1[n2], get_edge(a, n1, n2))

    # Add remaining edges from D
    for (n1, n2) in d.edges():
        b_key_1 = keys_by_value(g, n1)
        b_key_2 = keys_by_value(g, n2)
        if len(b_key_1) == 0 or len(b_key_2) == 0:
            if len(b_key_1) == 0 and len(b_key_2) != 0:
                a_keys_2 = keys_by_value(f, b_key_2[0])
                for k in a_keys_2:
                    add_edge(c, n1, hom1[k], get_edge(d, n1, n2))
            elif len(b_key_1) != 0 and len(b_key_2) == 0:
                a_keys_1 = keys_by_value(f, b_key_1[0])
                for k in a_keys_1:
                    add_edge(c, hom1[k], n2, get_edge(d, n1, n2))
            else:
                add_edge(c, n1, n2, get_edge(d, n1, n2))
        else:
            if (b_key_1[0], b_key_2[0]) not in b.edges():
                c_keys_1 = keys_by_value(hom2, n1)
                c_keys_2 = keys_by_value(hom2, n2)
                for c1 in c_keys_1:
                    for c2 in c_keys_2:
                        if (c1, c2) not in c.edges():
                            add_edge(c, c1, c2, get_edge(d, n1, n2))

    check_homomorphism(a, c, hom1)
    check_homomorphism(c, d, hom2)

    return (c, hom1, hom2)
