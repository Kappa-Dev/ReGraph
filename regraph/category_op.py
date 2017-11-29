"""Category operations used by graph rewriting tool."""
import networkx as nx
import copy

from regraph.primitives import (add_node,
                                add_edge,
                                set_edge,
                                add_node_attrs,
                                get_edge,
                                add_edge_attrs,
                                clone_node,
                                merge_nodes,
                                update_node_attrs,
                                remove_node,
                                remove_edge,
                                remove_node_attrs,
                                remove_edge_attrs,
                                unique_node_id,
                                subtract,
                                print_graph)
from regraph.utils import (keys_by_value,
                           merge_attributes,
                           restrict_mapping,
                           dict_sub,
                           id_of,
                           valid_attributes,
                           attrs_intersection)
from regraph.exceptions import (InvalidHomomorphism, ReGraphError)


def subgraph(gr, nodes):
    subg = copy.deepcopy(gr)
    for node in gr.nodes():
        if node not in nodes:
            remove_node(subg, node)
    return subg


def compose(d1, d2):
    """Compose two homomorphisms given by dicts."""
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
        raise InvalidHomomorphism(
            "Invalid homomorphism: Mapping is not "
            "covering all the nodes of source graph! "
            "domain: {}, domain of definition: {}"
            .format(set(elements), set(dictionary.keys())))


def check_homomorphism(source, target, dictionary, total=True):
    """Check if the homomorphism is valid.

    Valid homomorphism preserves edges,
    and attributes if requires.
    """
    # check if there is mapping for all the nodes of source graph
    if total:
        check_totality(source.nodes(), dictionary)
    if not set(dictionary.values()).issubset(target.nodes()):
        raise InvalidHomomorphism(
            "Some of the image nodes in mapping %s do not "
            "exist in target graph (target graph nodes %s) "
            "namely %s" %
            (dictionary.values(),
             target.nodes(),
             set(dictionary.values()) - set(target.nodes()))
        )

    # check connectivity
    for s, t in source.edges():
        try:
            if (s in dictionary.keys() and
                    t in dictionary.keys() and
                    not (dictionary[s], dictionary[t])
                    in target.edges()):
                if not target.is_directed():
                    if not (dictionary[t], dictionary[s]) in target.edges():
                        raise InvalidHomomorphism(
                            "Connectivity is not preserved!"
                            " Was expecting an edge '%s' and '%s'" %
                            (dictionary[t], dictionary[s]))
                else:
                    raise InvalidHomomorphism(
                        "Connectivity is not preserved!"
                        " Was expecting an edge between '%s' and '%s'" %
                        (dictionary[s], dictionary[t]))
        except KeyError:
            pass

    for s, t in dictionary.items():
            # check sets of attributes of nodes (here homomorphism = set
            # inclusion)
        if not valid_attributes(source.node[s], target.node[t]):
            raise InvalidHomomorphism(
                "Attributes of nodes source:'%s' %s and "
                "target:'%s' %s do not match!" %
                (s, source.node[s], t, target.node[t])
            )

    # check sets of attributes of edges (homomorphism = set inclusion)
    for s1, s2 in source.edges():
        try:
            if (s1 in dictionary.keys() and s2 in dictionary.keys() and
                    not valid_attributes(
                        source.edge[s1][s2],
                        target.edge[dictionary[s1]][dictionary[s2]])):
                raise InvalidHomomorphism(
                    "Attributes of edges (%s)-(%s) (%s) and "
                    "(%s)-(%s) (%s) do not match!" %
                    (s1, s2, source.edge[s1][s2], dictionary[s1],
                     dictionary[s2],
                     target.edge[dictionary[s1]][dictionary[s2]]))
        except KeyError:
            pass
    return True


def compose_chain(chain):
    """Compose a chain of homomorphisms."""
    homomorphism = chain[0]
    for i in range(1, len(chain)):
        homomorphism = compose(
            homomorphism,
            chain[i]
        )
    return homomorphism


def get_unique_map_to_pullback(p, p_a, p_b, z_a, z_b):
    """Find a unique map to pullback."""
    z_p = dict()
    for value in p:
        z_keys_from_a = set()
        if value in p_a.keys():
            a_value = p_a[value]
            z_keys_from_a = set(keys_by_value(z_a, a_value))

        z_keys_from_b = set()
        if value in p_b.keys():
            b_value = p_b[value]
            z_keys_from_b.update(keys_by_value(z_b, b_value))

        z_keys = z_keys_from_a.intersection(z_keys_from_b)
        for z_key in z_keys:
            z_p[z_key] = value

    return z_p


def get_unique_map_from_pushout(p, a_p, b_p, a_z, b_z):
    """Find a unique map to pushout."""
    p_z = dict()
    for value in p:
        z_values = set()

        a_values = set(keys_by_value(a_p, value))
        for a_value in a_values:
            if a_value in a_z.keys():
                z_values.add(a_z[a_value])

        b_values = set(keys_by_value(b_p, value))
        for b_value in b_values:
            if b_value in b_z.keys():
                z_values.add(b_z[b_value])

        if len(z_values) > 0:
            if len(z_values) > 1:
                raise ReGraphError("Cannot construct a unique map!")
            p_z[value] = z_values.pop()
    return p_z


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
                    raise ReGraphError("Map is not unique!")
                else:
                    for i, a_key in enumerate(a_keys):
                        a_c[a_key] = c_keys[i]
    return a_c


def identity(a, b):
    """Return identity homomorphism from a to b."""
    dic = {}
    for n in a.nodes():
        if n in b.nodes():
            dic[n] = n
        else:
            raise ReGraphError(
                "Cannot construct morphism by names: "
                "node '%s' not found in the second graph!" % n
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
            a_b1 = compose(a1_old_a1, a_b1)
            # update a_c
            for c_name, old_a_c in a_c.items():
                a_c[c_name] = compose(a1_old_a1, old_a_c)
            a_c[c_name2] = compose(a1_a2, a_c2)

        # at the end of pullback iterations assign right a and a_b
        a_b = a_b1
        a = a1

        check_homomorphism(a, b, a_b, total=False)
        for c_name, a_c_guy in a_c.items():
            check_homomorphism(a, cds[c_name][0], a_c_guy, total=False)
        return (a, a_b, a_c)


# def pullback(b, c, d, b_d, c_d, total=False):
#     if total:
#         return total_pullback(b, c, d, b_d, c_d)
#     else:
#         return partial_pullback(b, c, d, b_d, c_d)


# def partial_pullback(b, c, d, b_d, c_d):
#     try:
#         check_totality(b, b_d)
#         check_totality(c, c_d)
#         return total_pullback(b, c, d, b_d, c_d)

#     except InvalidHomomorphism as e:
#         check_homomorphism(b, d, b_d, total=False)
#         check_homomorphism(c, d, c_d, total=False)

#         bd_dom = subgraph(b, b_d.keys())
#         cd_dom = subgraph(c, c_d.keys())

#         bd_b = {n: n for n in bd_dom.nodes()}
#         cd_c = {n: n for n in cd_dom.nodes()}
#         (tmp, tmp_bddom, tmp_cddom) = total_pullback(bd_dom, cd_dom, d, b_d, c_d)
#         (b2, tmp_b2, b2_b) = pullback_complement(
#             tmp, bd_dom, b, tmp_bddom, bd_b)
#         (c2, tmp_c2, c2_c) = pullback_complement(
#             tmp, cd_dom, c, tmp_cddom, cd_c)
#         (new, b2_new, c2_new) = pushout(tmp, b2, c2, tmp_b2, tmp_c2)
#         hom1 = {v: b2_b[k] for (k, v) in b2_new.items()}
#         hom2 = {v: c2_c[k] for (k, v) in c2_new.items()}
#         return(new, hom1, hom2)


def pullback(b, c, d, b_d, c_d, inplace=False):
    """Find the pullback from b -> d <- c.

    Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
    with rh1 : A -> B; rh2 : A -> C and A the pullback.
    """
    if inplace is True:
        a = b
    else:
        a = type(b)()

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
                new_attrs = merge_attributes(b.node[n1],
                                             c.node[n2],
                                             'intersection')
                if n1 not in a.nodes():
                    add_node(a, n1, new_attrs)
                    hom1[n1] = n1
                    hom2[n1] = n2
                else:
                    i = 1
                    new_name = str(n1) + str(i)
                    while new_name in a.nodes():
                        i += 1
                        new_name = str(n1) + str(i)
                    # if n2 not in a.nodes():
                    add_node(a, new_name, new_attrs)
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


# def pushout(a, b, c, a_b, a_c, total=False):
#     """Find the pushout from b <- a -> c.

#     Given h1 : A -> B; h2 : A -> C returns D, rh1, rh2
#     with rh1 : B -> D; rh2 : C -> D and D the pushout.
#     """
#     if total:
#         return total_pushout(a, b, c, a_b, a_c)
#     else:
#         return total_pushout(a, b, c, a_b, a_c)
#         # return partial_pushout(a, b, c, a_b, a_c)


# def partial_pushout(a, b, c, a_b, a_c):
#     try:
#         check_totality(a, a_b)
#         check_totality(a, a_c)
#         return total_pushout(a, b, c, a_b, a_c)

#     except InvalidHomomorphism:
#         check_homomorphism(a, b, a_b, total=False)
#         check_homomorphism(a, c, a_c, total=False)
#         if a.is_directed():
#             ab_dom = nx.DiGraph(a.subgraph(a_b.keys()))
#             ac_dom = nx.DiGraph(a.subgraph(a_c.keys()))
#         else:
#             ab_dom = nx.Graph(a.subgraph(a_b.keys()))
#             ac_dom = nx.Graph(a.subgraph(a_c.keys()))

#         ac_a = {n: n for n in ac_dom.nodes()}
#         ab_a = {n: n for n in ab_dom.nodes()}

#         (c2, a_c2, c_c2) = total_pushout(ac_dom, a, c, ac_a, a_c)
#         (b2, a_b2, b_b2) = total_pushout(ab_dom, a, b, ab_a, a_b)

#         (d, b2_d, c2_d) = total_pushout(a, b2, c2, a_b2, a_c2)
#         b_d = compose(b_b2, b2_d)
#         c_d = compose(c_c2, c2_d)

#         return(d, b_d, c_d)


def merge_classes(equ_elems, classes):
    """Merge the equivalence classes containing elements from equ_elems."""
    new_classes = []
    merged_class = set()
    for cl in classes:
        if len(cl & equ_elems) > 0:
            merged_class |= cl
        else:
            new_classes.append(cl)
    if len(merged_class) > 0:
        new_classes.append(merged_class)
    return new_classes


# def total_pushout(a, b, c, a_b, a_c, inplace=False):
#     """Find the pushout from a span.

#     :param a:
#     :param b:
#     :param c:
#     :param a_b:
#     :param a_c:
#     :param inplace:

#     :return:
#     """
#     check_homomorphism(a, b, a_b)
#     check_homomorphism(a, c, a_c)

#     hom1 = {}
#     hom2 = {}

#     if inplace is True:
#         d = b
#     else:
#         d = type(b)()

#     f = a_b
#     g = a_c

#     # add nodes to the graph

#     classes = [{node} for node in a.nodes()]

#     for node in c.nodes():
#         a_keys = set(keys_by_value(g, node))
#         if len(a_keys) >= 2:
#             classes = merge_classes(a_keys, classes)
#     for node in b.nodes():
#         a_keys = set(keys_by_value(f, node))
#         if len(a_keys) >= 2:
#             classes = merge_classes(a_keys, classes)

#     for cl in classes:
#         b_nodes = {f[node] for node in cl}
#         c_nodes = {g[node] for node in cl}
#         if len(b_nodes) > 1:
#             new_name = "_".join((str(b_node) for b_node in b_nodes))
#         else:
#             new_name = list(b_nodes)[0]

#         new_name = unique_node_id(d, new_name)
#         new_attrs = {}
#         for node in b_nodes:
#             new_attrs = merge_attributes(new_attrs, b.node[node])
#             hom1[node] = new_name
#         for node in c_nodes:
#             new_attrs = merge_attributes(new_attrs, c.node[node])
#             hom2[node] = new_name
#         add_node(d, new_name, new_attrs)

#     for n in c.nodes():
#         if n not in g.values():
#             new_name = n
#             i = 1
#             while new_name in d.nodes():
#                 new_name = str(n) + "_" + str(i)
#                 i += 1
#             add_node(
#                 d,
#                 new_name,
#                 c.node[n]
#             )
#             hom2[n] = n

#     for n in b.nodes():
#         if n not in f.values():
#             new_name = n
#             i = 1
#             while new_name in d.nodes():
#                 new_name = str(n) + "_" + str(i)
#                 i += 1
#             add_node(
#                 d,
#                 new_name,
#                 b.node[n]
#             )
#             hom1[n] = new_name

#     # add edges to the graph
#     for (n1, n2) in c.edges():
#         a_keys_1 = keys_by_value(g, n1)
#         a_keys_2 = keys_by_value(g, n2)
#         if len(a_keys_1) == 0 or len(a_keys_2) == 0:
#             add_edge(d, hom2[n1], hom2[n2], get_edge(c, n1, n2))
#         else:
#             for a_key_1 in a_keys_1:
#                 for a_key_2 in a_keys_2:
#                     if (f[a_key_1], f[a_key_2]) in b.edges():
#                         if (hom2[n1], hom2[n2]) not in d.edges():
#                             add_edge(d, hom2[n1], hom2[n2], get_edge(
#                                 b, f[a_key_1], f[a_key_2]))
#                             if (a_key_1, a_key_2) in a.edges():
#                                 add_edge_attrs(d, hom2[n1],
#                                                hom2[n2],
#                                                dict_sub(get_edge(c, n1, n2),
#                                                         get_edge(a, a_key_1, a_key_2)))

#                             else:
#                                 add_edge_attrs(d, hom2[n1],
#                                                hom2[n2],
#                                                get_edge(c, n1, n2))
#                         else:
#                             if (f[a_key_1], f[a_key_2]) in b.edges():
#                                 add_edge_attrs(d, hom2[n1],
#                                                hom2[n2],
#                                                get_edge(b, f[a_key_1], f[a_key_2]))
#                             if (a_key_1, a_key_2) in a.edges():
#                                 add_edge_attrs(d, hom2[n1],
#                                                hom2[n2],
#                                                dict_sub(get_edge(c, n1, n2),
#                                                         get_edge(a, a_key_1, a_key_2)))
#                     elif (hom2[n1], hom2[n2]) not in d.edges():
#                         add_edge(d, hom2[n1], hom2[n2], get_edge(c, n1, n2))

#     for (n1, n2) in b.edges():
#         a_keys_1 = keys_by_value(f, n1)
#         a_keys_2 = keys_by_value(f, n2)
#         if len(a_keys_1) == 0 or len(a_keys_2) == 0:
#             add_edge(d, hom1[n1], hom1[n2], get_edge(b, n1, n2))
#         elif (hom1[n1], hom1[n2]) not in d.edges():
#             add_edge(d, hom1[n1], hom1[n2], get_edge(b, n1, n2))

#     check_homomorphism(b, d, hom1)
#     check_homomorphism(c, d, hom2)
#     return (d, hom1, hom2)


def pushout(a, b, c, a_b, a_c, inplace=False):

    check_homomorphism(a, b, a_b)
    check_homomorphism(a, c, a_c)

    if inplace is True:
        d = b
    else:
        d = copy.deepcopy(b)

    b_d = dict()
    c_d = dict()

    # Add/merge nodes
    for c_n in c.nodes():
        a_keys = keys_by_value(a_c, c_n)
        # Add nodes
        if len(a_keys) == 0:
            add_node(d, c_n, c.node[c_n])
            c_d[c_n] = c_n
        # Keep nodes
        elif len(a_keys) == 1:
            c_d[a_c[a_keys[0]]] = a_b[a_keys[0]]
        # Merge nodes
        else:
            nodes_to_merge = []
            for k in a_keys:
                nodes_to_merge.append(a_b[k])
            new_name = merge_nodes(d, nodes_to_merge)
            c_d[c_n] = new_name

    # Add edges
    for (n1, n2) in c.edges():
        if b.is_directed():
            if (c_d[n1], c_d[n2]) not in b.edges():
                add_edge(
                    d, c_d[n1], c_d[n2],
                    get_edge(c, n1, n2))
        else:
            if (c_d[n1], c_d[n2]) not in b.edges() and\
               (c_d[n2], c_d[n1]) not in b.edges():
                add_edge(
                    d, c_d[n1], c_d[n2],
                    get_edge(c, n1, n2)
                )

    # Add node attrs
    for c_n in c.nodes():
        a_keys = keys_by_value(a_c, c_n)
        # Add attributes to the nodes which stayed invariant
        if len(a_keys) == 1:
            attrs_to_add = dict_sub(
                c.node[c_n],
                a.node[a_keys[0]]
            )
            add_node_attrs(d, c_d[c_n], attrs_to_add)
        # Add attributes to the nodes which were merged
        elif len(a_keys) > 1:
            merged_attrs = {}
            for k in a_keys:
                merged_attrs = merge_attributes(
                    merged_attrs,
                    a.node[k]
                )
            attrs_to_add = dict_sub(c.node[c_n], merged_attrs)
            add_node_attrs(d, c_d[c_n], attrs_to_add)

    # Add edge attrs
    for (n1, n2) in c.edges():
        p_keys_1 = keys_by_value(c_d, n1)
        p_keys_2 = keys_by_value(c_d, n2)
        for k1 in p_keys_1:
            for k2 in p_keys_2:
                if b.is_directed():
                    if (k1, k2) in a.edges():
                        attrs_to_add = dict_sub(
                            get_edge(c, n1, n2),
                            get_edge(a, k1, k2)
                        )
                        add_edge_attrs(
                            d, c_d[n1], c_d[n2],
                            attrs_to_add
                        )
                else:
                    if (k1, k2) in a.edges() or (k2, k1) in a.edges():
                        attrs_to_add = dict_sub(
                            get_edge(c, n1, n2),
                            get_edge(a, k1, k2)
                        )
                        add_edge_attrs(
                            d, c_d[n1], c_d[n2],
                            attrs_to_add
                        )
    return (d, b_d, c_d)


# def pullback_complement(a, b, d, a_b, b_d, inplace=False):
#     """Find the pullback complement.

#     Given h1 : A -> B; h2 : B -> D returns C, rh1, rh2
#     with rh1 : A -> C; rh2 : C -> D and C the pullback_complement.
#     Doesn't work if h2 is not a matching
#     """
#     check_homomorphism(a, b, a_b, total=True)
#     check_homomorphism(b, d, b_d, total=True)

#     if not is_monic(b_d):
#         raise InvalidHomomorphism(
#             "Second homomorphism is not monic, "
#             "cannot find final pullback complement!"
#         )

#     if inplace is True:
#         c = d
#     else:
#         c = type(b)()

#     f = a_b
#     g = b_d

#     hom1 = {}
#     hom2 = {}

#     # a_d = compose(g, f)
#     d_m_b = subtract(d, b, g)

#     for n in a.nodes():
#         if g[f[n]] not in c.nodes():
#             add_node(c, g[f[n]],
#                      dict_sub(d.node[g[f[n]]], b.node[f[n]]))
#             add_node_attrs(c, g[f[n]], a.node[n])
#             hom1[n] = g[f[n]]
#             hom2[g[f[n]]] = g[f[n]]
#         else:
#             new_name = clone_node(c, g[f[n]])
#             update_node_attrs(
#                 c, new_name,
#                 dict_sub(d.node[g[f[n]]], b.node[f[n]])
#             )
#             add_node_attrs(c, new_name, a.node[n])
#             hom1[n] = new_name
#             hom2[new_name] = g[f[n]]

#     for n in d_m_b.nodes():
#         is_in_a = False
#         for n0 in a.nodes():
#             if g[f[n0]] == n:
#                 is_in_a = True
#                 break
#         if not is_in_a:
#             new_name = n
#             i = 1
#             while new_name in c.nodes():
#                 new_name = str(n) + "_" + str(i)
#                 i += 1
#             add_node(c, new_name, d_m_b.node[n])
#             hom2[new_name] = n

#     # Add edges from preserved part
#     for (n1, n2) in a.edges():
#         attrs = dict_sub(
#             get_edge(d, g[f[n1]], g[f[n2]]), get_edge(b, f[n1], f[n2]))
#         add_edge(c, hom1[n1], hom1[n2], attrs)
#         add_edge_attrs(c, hom1[n1], hom1[n2], get_edge(a, n1, n2))

#     # Add remaining edges from D
#     for (n1, n2) in d.edges():
#         b_key_1 = keys_by_value(g, n1)
#         b_key_2 = keys_by_value(g, n2)
#         if len(b_key_1) == 0 or len(b_key_2) == 0:
#             if len(b_key_1) == 0 and len(b_key_2) != 0:
#                 a_keys_2 = keys_by_value(f, b_key_2[0])
#                 for k in a_keys_2:
#                     add_edge(c, n1, hom1[k], get_edge(d, n1, n2))
#             elif len(b_key_1) != 0 and len(b_key_2) == 0:
#                 a_keys_1 = keys_by_value(f, b_key_1[0])
#                 for k in a_keys_1:
#                     add_edge(c, hom1[k], n2, get_edge(d, n1, n2))
#             else:
#                 add_edge(c, n1, n2, get_edge(d, n1, n2))
#         else:
#             if (b_key_1[0], b_key_2[0]) not in b.edges():
#                 c_keys_1 = keys_by_value(hom2, n1)
#                 c_keys_2 = keys_by_value(hom2, n2)
#                 for c1 in c_keys_1:
#                     for c2 in c_keys_2:
#                         if (c1, c2) not in c.edges():
#                             add_edge(c, c1, c2, get_edge(d, n1, n2))

#     check_homomorphism(a, c, hom1)
#     check_homomorphism(c, d, hom2)

#     return (c, hom1, hom2)


def pullback_complement(a, b, d, a_b, b_d, inplace=False):
    """Inplace pullback complement.

    Makes changes to d inplace.
    """
    check_homomorphism(a, b, a_b, total=True)
    check_homomorphism(b, d, b_d, total=True)

    if not is_monic(b_d):
        raise InvalidHomomorphism(
            "Second homomorphism is not monic, "
            "cannot find final pullback complement!"
        )

    a_c = dict()
    c_d = dict()

    if inplace is True:
        c = d
    else:
        c = copy.deepcopy(d)

    check_homomorphism(a, b, a_b, total=True)
    check_homomorphism(b, d, b_d, total=True)

    if not is_monic(b_d):
        raise InvalidHomomorphism(
            "Second homomorphism is not monic, "
            "cannot find final pullback complement!"
        )

    # Remove/clone nodes
    for b_node in b.nodes():
        a_keys = keys_by_value(a_b, b_node)
        # Remove nodes
        if len(a_keys) == 0:
            remove_node(c, b_d[b_node])
        # Keep nodes
        elif len(a_keys) == 1:
            a_c[a_keys[0]] = b_d[b_node]
        # Clone nodes
        else:
            i = 1
            for k in a_keys:
                if i == 1:
                    a_c[k] = b_d[b_node]
                else:
                    new_name = clone_node(c, b_d[b_node])
                    a_c[k] = new_name
                i += 1

    # Remove edges
    for (b_n1, b_n2) in b.edges():
        a_keys_1 = keys_by_value(a_b, b_n1)
        a_keys_2 = keys_by_value(a_b, b_n2)
        if len(a_keys_1) > 0 and len(a_keys_2) > 0:
            for k1 in a_keys_1:
                for k2 in a_keys_2:
                    if d.is_directed():
                        if (k1, k2) not in a.edges():
                            if (a_c[k1], a_c[k2]) in d.edges():
                                remove_edge(c, a_c[k1], a_c[k2])
                                # removed_edges.add((a_c[k1], a_c[k2]))
                    else:
                        if (k1, k2) not in a.edges() and\
                           (k2, k1) not in a.edges():
                            if (a_c[k1], a_c[k2]) in d.edges() or\
                               (a_c[k2], a_c[k1]) in d.edges():
                                remove_edge(c, a_c[k1], a_c[k2])
    # Remove node attrs
    for a_node in a.nodes():
        attrs_to_remove = dict_sub(
            b.node[a_b[a_node]],
            a.node[a_node]
        )
        remove_node_attrs(c, a_c[a_node], attrs_to_remove)
        # removed_node_attrs[a_c[a_node]] = attrs_to_remove

    # Remove edge attrs
    for (n1, n2) in a.edges():
        attrs_to_remove = dict_sub(
            get_edge(b, a_b[n1], a_b[n2]),
            get_edge(a, n1, n2)
        )
        remove_edge_attrs(c, a_c[n1], a_c[n2], attrs_to_remove)
        # removed_edge_attrs[(a_c[n1], a_c[n2])] = attrs_to_remove

    return (c, a_c, c_d)


def pullback_pushout(b, c, d, b_d, c_d, pullback_filter=None):
    """do a pullback and then a pushout"""
    (a, a_b, a_c) = pullback(b, c, d, b_d, c_d)
    if pullback_filter is not None:
        valid_nodes = [n for n in a.nodes()
                       if pullback_filter(a, b, c, d, a_b, a_c, b_d, c_d, n)]
        a = a.subgraph(valid_nodes)
        a_b = restrict_mapping(valid_nodes, a_b)
        a_c = restrict_mapping(valid_nodes, a_c)

    (d2, b_d2, c_d2) = pushout(a, b, c, a_b, a_c)
    d2_d = {}
    for node in b.nodes():
        d2_d[b_d2[node]] = b_d[node]
    for node in c.nodes():
        d2_d[c_d2[node]] = c_d[node]
    return(d2, b_d2, c_d2, d2_d)


def multi_pullback_pushout(d, graphs, pullback_filter=None):
    """graphs: list of graphs and typings by d
               [(g1, t1), (g2, t2), ...] """
    if graphs == []:
        raise ReGraphError("multi pullback_pushout with empty list")
    tmp_graph = graphs[0][0]
    tmp_typing = graphs[0][1]
    for (graph, typing) in graphs[1:]:
        (tmp_graph, _, _, tmp_typing) = pullback_pushout(tmp_graph, graph, d,
                                                         tmp_typing, typing,
                                                         pullback_filter)
    return (tmp_graph, tmp_typing)


def typing_of_pushout(b, c, p, b_p, c_p, b_typgr, c_typgr):
    """get the typings of the pushout"""
    p_typgr = {}
    for node in b.nodes():
        if node in b_typgr:
            p_typgr[b_p[node]] = b_typgr[node]
    for node in c.nodes():
        if node in c_typgr:
            p_typgr[c_p[node]] = c_typgr[node]
    return p_typgr


def typings_of_pushout(b, c, p, b_p, c_p, b_typings, c_typings):
    """b_typings and c_typings are dict of Typing objects
    returns a dict of pairs (mapping:dict, total:bool)}
    """
    p_typings = {}
    for typid, b_typ in b_typings.items():
        if typid in c_typings:
            total = b_typ.total and c_typings[typid].total
            c_mapping = c_typings[typid].mapping
        else:
            total = False
            c_mapping = {}

        p_typings[typid] = (typing_of_pushout(b, c, p, b_p, c_p,
                                              b_typ.mapping,
                                              c_mapping),
                            total)
    for typid, c_typ in c_typings.items():
        if typid not in b_typings:
            p_typings[typid] = (typing_of_pushout(b, c, p, b_p, c_p,
                                                  {},
                                                  c_typ.mapping),
                                False)
    return p_typings


def pushout_from_partial_mapping(b, c, b_c, b_typings, c_typings):
    """typings are dict {id_of_typing_graph:mapping}"""
    # a = b.subgraph(b_c.keys())
    a = nx.DiGraph()
    a.add_nodes_from(b_c.keys())
    a_b = id_of(a)
    a_c = b_c
    (d, b_d, c_d) = pushout(a, b, c, a_b, a_c)
    d_typings = typing_of_pushout(b, c, d, b_d, c_d, b_typings, c_typings)
    return (d, d_typings)


def relation_to_span(g1, g2, relation, edges=False, attrs=False, directed=True):
        """Convert a relation to a span."""
        if directed:
            new_graph = nx.DiGraph()
        else:
            new_graph = nx.Graph()
        left_h = dict()
        right_h = dict()

        for a, b in relation:
            new_node = str(a) + "_" + str(b)
            new_graph.add_node(new_node)
            if attrs:
                common_attrs = attrs_intersection(
                    g1.node[a],
                    g2.node[b]
                )
                add_node_attrs(new_graph, new_node, common_attrs)
            left_h[new_node] = a
            right_h[new_node] = b

        for n1 in new_graph.nodes():
            for n2 in new_graph.nodes():
                if (left_h[n1], left_h[n2]) in g1.edges() and\
                   (right_h[n1], right_h[n2]) in g2.edges():
                    new_graph.add_edge(n1, n2)
                    common_attrs = attrs_intersection(
                        g1.edge[left_h[n1]][left_h[n2]],
                        g2.edge[right_h[n1]][right_h[n2]],
                    )
                    add_edge_attrs(
                        new_graph,
                        n1, n2,
                        common_attrs
                    )

        return (new_graph, left_h, right_h)
