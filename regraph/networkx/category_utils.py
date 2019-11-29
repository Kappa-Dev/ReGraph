"""Category operations used by graph rewriting tool."""
import copy

from regraph.graphs import NXGraph

from regraph.utils import (keys_by_value,
                           merge_attributes,
                           restrict_mapping,
                           dict_sub,
                           id_of,
                           valid_attributes,
                           attrs_intersection)
from regraph.exceptions import (InvalidHomomorphism, ReGraphError)


# def subgraph(graph, nodes):
#     """Get a subgraph induced by a set nodes.

#     :param graph:
#     :param nodes:

#     :return:
#     """
#     subgraph = copy.deepcopy(graph)
#     for node in graph.nodes():
#         if node not in nodes:
#             remove_node(subgraph, node)
#     return subgraph


# Homomorphism related utils

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
            "The image nodes {} do not exist ".format(
                set(dictionary.values()) - set(target.nodes())) +
            "in the target graph (existing nodes '{}') ".format(
                target.nodes()) +
            "in dictionary '{}'".format(dictionary)
        )

    # check connectivity
    for s, t in source.edges():
        try:
            if (s in dictionary.keys() and
                    t in dictionary.keys() and
                    not (dictionary[s], dictionary[t])
                    in target.edges()):
                raise InvalidHomomorphism(
                    "Connectivity is not preserved!"
                    " Was expecting an edge between '{}' and '{}'".format(
                        dictionary[s], dictionary[t]))
        except KeyError:
            pass

    for s, t in dictionary.items():
            # check sets of attributes of nodes (here homomorphism = set
            # inclusion)
        if not valid_attributes(source.node[s], target.node[t]):
            raise InvalidHomomorphism(
                "Attributes of nodes source: '{}' {} and ".format(
                    s, source.get_node(s)) +
                "target: '{}' {} do not match!".format(
                    t, target.get_node(t))
            )

    # check sets of attributes of edges (homomorphism = set inclusion)
    for s1, s2 in source.edges():
        try:
            if (s1 in dictionary.keys() and s2 in dictionary.keys() and
                    not valid_attributes(
                        source.get_edge(s1, s2),
                        target.get_edge(dictionary[s1], dictionary[s2]))):
                raise InvalidHomomorphism(
                    "Attributes of edges ({})-({}) ({}) and ".format(
                        s1, s2, source.get_edge(s1, s2)) +
                    "({})-({}) ({}) do not match!".format(
                        dictionary[s1],
                        dictionary[s2],
                        target.get_edge(dictionary[s1], dictionary[s2])))
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


# Categorical constructions on simple graphs

def pullback(b, c, d, b_d, c_d, inplace=False):
    """Find the pullback from b -> d <- c.

    Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
    with rh1 : A -> B; rh2 : A -> C and A the pullback.
    """
    if inplace is True:
        a = b
    else:
        a = NXGraph()
        a.add_nodes_from(b.nodes(data=True))
        a.add_edges_from(b.edges(data=True))

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
                    a.add_node(n1, new_attrs)
                    hom1[n1] = n1
                    hom2[n1] = n2
                else:
                    i = 1
                    new_name = str(n1) + str(i)
                    while new_name in a.nodes():
                        i += 1
                        new_name = str(n1) + str(i)
                    # if n2 not in a.nodes():
                    a.add_node(new_name, new_attrs)
                    hom1[new_name] = n1
                    hom2[new_name] = n2

    for n1 in a.nodes():
        for n2 in a.nodes():
            if (hom1[n1], hom1[n2]) in b.edges():
                if (hom2[n1], hom2[n2]) in c.edges():
                    a.add_edge(n1, n2)
                    a.set_edge(
                        a,
                        n1,
                        n2,
                        merge_attributes(
                            b.get_edge(hom1[n1], hom1[n2]),
                            c.get_edge(hom2[n1], hom2[n2]),
                            'intersection'))
    check_homomorphism(a, b, hom1)
    check_homomorphism(a, c, hom2)
    return (a, hom1, hom2)


def pushout(a, b, c, a_b, a_c, inplace=False):
    """Find the pushour of the span b <- a -> c."""
    def get_classes_to_merge():
        pass

    check_homomorphism(a, b, a_b)
    check_homomorphism(a, c, a_c)

    if inplace is True:
        d = b
    else:
        d = NXGraph()
        d.add_nodes_from(b.nodes(data=True))
        d.add_edges_from(b.edges(data=True))

    b_d = id_of(b.nodes())
    c_d = dict()

    # Add/merge nodes
    merged_nodes = dict()
    for c_n in c.nodes():
        a_keys = keys_by_value(a_c, c_n)
        # Add nodes
        if len(a_keys) == 0:
            if c_n not in d.nodes():
                new_name = c_n
            else:
                new_name = d.generate_new_node_id(c_n)
            d.add_node(new_name, c.node[c_n])
            c_d[c_n] = new_name
        # Keep nodes
        elif len(a_keys) == 1:
            c_d[a_c[a_keys[0]]] = b_d[a_b[a_keys[0]]]
        # Merge nodes
        else:
            nodes_to_merge = set()
            # find the nodes that need to be merged
            for k in a_keys:
                nodes_to_merge.add(a_b[k])

            # find if exists already some merged node to
            # which the new node should be merged
            groups_to_remove = set()
            new_groups = set()
            merge_done = False
            for k in merged_nodes.keys():
                if nodes_to_merge.issubset(merged_nodes[k]):
                    merge_done = True
                else:
                    intersect_with_group = nodes_to_merge.intersection(
                        merged_nodes[k])
                    if len(intersect_with_group) > 0:
                        new_nodes_to_merge =\
                            nodes_to_merge.difference(merged_nodes[k])
                        if len(new_nodes_to_merge) > 0:
                            new_nodes_to_merge.add(k)
                            new_name = d.merge_nodes(new_nodes_to_merge)
                            merged_nodes[new_name] = merged_nodes[k].union(
                                nodes_to_merge)
                            groups_to_remove.add(k)
                            new_groups.add(new_name)

            if len(groups_to_remove) > 0:
                new_name = d.merge_nodes(new_groups)
                merged_nodes[new_name] = set()
                for g in new_groups:
                    merged_nodes[new_name] = merged_nodes[new_name].union(
                        merged_nodes[g])
                for group in groups_to_remove:
                    del merged_nodes[group]
            elif not merge_done:
                if len(nodes_to_merge) > 1:
                    new_name = d.merge_nodes(nodes_to_merge)
                    merged_nodes[new_name] = nodes_to_merge
                else:
                    new_name = list(nodes_to_merge)[0]

            c_d[c_n] = new_name

            for node in nodes_to_merge:
                b_d[node] = new_name

            for k in c_d.keys():
                for vv in keys_by_value(a_c, k):
                    if b_d[a_b[vv]] == new_name:
                        c_d[k] = new_name

    # Add edges
    for (n1, n2) in c.edges():
        if (c_d[n1], c_d[n2]) not in d.edges():
            d.add_edge(
                c_d[n1], c_d[n2],
                c.get_edge(n1, n2))

    # Add node attrs
    for c_n in c.nodes():
        a_keys = keys_by_value(a_c, c_n)
        # Add attributes to the nodes which stayed invariant
        if len(a_keys) == 1:
            attrs_to_add = dict_sub(
                c.node[c_n],
                a.node[a_keys[0]]
            )
            d.add_node_attrs(c_d[c_n], attrs_to_add)
        # Add attributes to the nodes which were merged
        elif len(a_keys) > 1:
            merged_attrs = {}
            for k in a_keys:
                merged_attrs = merge_attributes(
                    merged_attrs,
                    a.node[k]
                )
            attrs_to_add = dict_sub(c.node[c_n], merged_attrs)
            d.add_node_attrs(c_d[c_n], attrs_to_add)

    # Add edge attrs
    for (n1, n2) in c.edges():
        d_n1 = c_d[n1]
        d_n2 = c_d[n2]
        attrs_to_add = dict_sub(
            c.get_edge(n1, n2),
            d.get_edge(d_n1, d_n2)
        )
        d.add_edge_attrs(
            c_d[n1], c_d[n2],
            attrs_to_add
        )
    return (d, b_d, c_d)


def pullback_complement(a, b, d, a_b, b_d, inplace=False):
    """Find the final pullback complement from a->b->d.

    Makes changes to d inplace.
    """
    check_homomorphism(a, b, a_b, total=True)
    check_homomorphism(b, d, b_d, total=True)

    if not is_monic(b_d):
        raise InvalidHomomorphism(
            "Second homomorphism is not monic, "
            "cannot find final pullback complement!"
        )

    if inplace is True:
        c = d
    else:
        c = NXGraph()
        c.add_nodes_from(d.nodes(data=True))
        c.add_edges_from(d.edges(data=True))

    a_c = dict()
    c_d = id_of(c.nodes())

    # Remove/clone nodes
    for b_node in b.nodes():
        a_keys = keys_by_value(a_b, b_node)
        # Remove nodes
        if len(a_keys) == 0:
            c.remove_node(b_d[b_node])
            del c_d[b_d[b_node]]
        # Keep nodes
        elif len(a_keys) == 1:
            a_c[a_keys[0]] = b_d[b_node]
        # Clone nodes
        else:
            i = 1
            for k in a_keys:
                if i == 1:
                    a_c[k] = b_d[b_node]
                    c_d[b_d[b_node]] = b_d[b_node]
                else:
                    new_name = c.clone_node(b_d[b_node])
                    a_c[k] = new_name
                    c_d[new_name] = b_d[b_node]
                i += 1

    # Remove edges
    for (b_n1, b_n2) in b.edges():
        a_keys_1 = keys_by_value(a_b, b_n1)
        a_keys_2 = keys_by_value(a_b, b_n2)
        if len(a_keys_1) > 0 and len(a_keys_2) > 0:
            for k1 in a_keys_1:
                for k2 in a_keys_2:
                    if (k1, k2) not in a.edges() and\
                       (a_c[k1], a_c[k2]) in c.edges():
                        c.remove_edge(a_c[k1], a_c[k2])

    # Remove node attrs
    for a_node in a.nodes():
        attrs_to_remove = dict_sub(
            b.node[a_b[a_node]],
            a.node[a_node]
        )
        c.remove_node_attrs(a_c[a_node], attrs_to_remove)
        # removed_node_attrs[a_c[a_node]] = attrs_to_remove

    # Remove edge attrs
    for (n1, n2) in a.edges():
        attrs_to_remove = dict_sub(
            b.get_edge(a_b[n1], a_b[n2]),
            a.get_edge(n1, n2)
        )
        c.remove_edge_attrs(a_c[n1], a_c[n2], attrs_to_remove)
        # removed_edge_attrs[(a_c[n1], a_c[n2])] = attrs_to_remove

    return (c, a_c, c_d)


def image_factorization(a, b, a_b):
    """Compute the image factorization given A, B and A->B."""
    c = NXGraph()
    c.add_nodes_from(a.nodes(data=True))
    c.add_edges_from(a.edges(data=True))

    a_c = {}
    c_b = {}

    for n in b.nodes():
        if n in a_b.values():
            a_nodes = keys_by_value(a_b, n)
            if len(a_nodes) > 1:
                new_id = c.merge_nodes(a_nodes)
            else:
                new_id = a_nodes[0]
            for a_node in a_nodes:
                a_c[a_node] = new_id
            c_b[new_id] = n

    return c, a_c, c_b


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


def get_unique_map_to_pullback_complement(a_p, p_c,
                                          a_prime_a, a_prime_z,
                                          z_c):
    """Find morphism z->p using the UP of PBC."""
    # Preliminary checks
    if not is_monic(a_p):
        raise ReGraphError(
            "Morphism 'a_p' is required to be a mono "
            "to use the UP of the pullback complement")
    z_p = {}
    for z_element, c_element in z_c.items():
        a_prime_elements = keys_by_value(a_prime_z, z_element)
        p_elements1 = set()  # candidate p elements
        for a_prime_element in a_prime_elements:
            p_elements1.add(a_p[a_prime_a[a_prime_element]])
        # resolve ambiguity going the other way
        p_elements2 = keys_by_value(p_c, c_element)
        if len(p_elements1) == 0:
            if len(p_elements2) == 1:
                z_p[z_element] = list(p_elements2)[0]
            else:
                raise ValueError("Something is wrong")
        else:
            intersection = p_elements1.intersection(p_elements2)
            if len(intersection) == 1:
                z_p[z_element] = list(intersection)[0]
            else:
                raise ValueError("Something is wrong")
    return z_p

# def get_unique_map(a, b, c, d, a_b, b_d, c_d):
#     """Get a map a->c that makes a PBC square commute."""
#     a_c = dict()
#     for node in b.nodes():
#         a_keys = keys_by_value(a_b, node)
#         if len(a_keys) > 0:
#             # node stayed in the rule
#             if node in b_d.keys():
#                 d_node = b_d[node]
#                 c_keys = keys_by_value(
#                     c_d,
#                     d_node
#                 )
#                 if len(a_keys) != len(c_keys):
#                     raise ReGraphError("Map is not unique!")
#                 else:
#                     for i, a_key in enumerate(a_keys):
#                         a_c[a_key] = c_keys[i]
#     return a_c


# Relations related utils

def relation_to_span(g1, g2, relation, edges=False, attrs=False):
        """Convert a relation to a span."""
        new_graph = type(g1)()

        left_h = dict()
        right_h = dict()

        for a, bs in relation.items():
            for b in bs:
                new_node = str(a) + "_" + str(b)
                new_graph.add_node(new_node)
                if attrs:
                    common_attrs = attrs_intersection(
                        g1.node[a],
                        g2.node[b]
                    )
                    new_graph.add_node_attrs(new_node, common_attrs)
                left_h[new_node] = a
                right_h[new_node] = b

        for n1 in new_graph.nodes():
            for n2 in new_graph.nodes():
                if (left_h[n1], left_h[n2]) in g1.edges() and\
                   (right_h[n1], right_h[n2]) in g2.edges():
                    new_graph.add_edge(n1, n2)
                    common_attrs = attrs_intersection(
                        g1.adj[left_h[n1]][left_h[n2]],
                        g2.adj[right_h[n1]][right_h[n2]],
                    )
                    new_graph.add_edge_attrs(
                        n1, n2,
                        common_attrs
                    )

        return new_graph, left_h, right_h


def left_relation_dict(relation):
    dictionary = dict()
    for u, v in relation:
        if u in dictionary.keys():
            dictionary[u].add(v)
        else:
            dictionary[u] = set([v])
    return dictionary


def right_relation_dict(relation):
    dictionary = dict()
    for u, v in relation:
        if v in dictionary.keys():
            dictionary[v].add(u)
        else:
            dictionary[v] = set([u])
    return dictionary


def pushout_from_relation(g1, g2, relation, inplace=False):
    """Find the pushout from a relation."""

    left_dict = left_relation_dict(relation)
    right_dict = right_relation_dict(relation)

    if inplace is True:
        g12 = g1
    else:
        g12 = copy.deepcopy(g1)

    g1_g12 = id_of(g12.nodes())
    g2_g12 = dict()

    for node in g1.nodes():
        if node in left_dict.keys():
            for g2_node in left_dict[node]:
                g2_g12[g2_node] = node

    for node in g2.nodes():
        if node not in right_dict.keys():
            node_id = node
            if node_id in g12.nodes():
                node_id = g12.generate_new_node_id(g12, node)
            g12.add_node(node_id, g2.node[node])
            g2_g12[node] = node_id
        elif len(right_dict[node]) == 1:
            node_attrs_diff = dict_sub(
                g2.node[node],
                g1.node[list(right_dict[node])[0]])
            g12.add_node_attrs(
                list(right_dict[node])[0], node_attrs_diff)
        elif len(right_dict[node]) > 1:
            new_name = g12.merge_nodes(right_dict[node])
            for g1_node in right_dict[node]:
                g1_g12[g1_node] = new_name
            g2_g12[node] = new_name
            node_attrs_diff = dict_sub(
                g2.node[node],
                g12.node[new_name])
            g12.add_node_attrs(new_name, node_attrs_diff)

    for u, v in g2.edges():
        if (g2_g12[u], g2_g12[v]) not in g12.edges():
            g12.add_edge(g2_g12[u], g2_g12[v], g2.get_edge(u, v))
        else:
            edge_attrs_diff = dict_sub(
                g2.adj[u][v],
                g12.adj[g2_g12[u]][g2_g12[v]])
            g12.add_edge_attrs(g2_g12[u], g2_g12[v], edge_attrs_diff)
    return (g12, g1_g12, g2_g12)


def compose_relation_dicts(left_dict, right_dict):
    result_dict = dict()
    for left_el, right_els in left_dict.items():
        for right_el in right_els:
            if right_el in right_dict.keys():

                if left_el in result_dict.keys():
                    result_dict[left_el].add(right_el)
                else:
                    result_dict[left_el] = set([right_el])
    return result_dict
