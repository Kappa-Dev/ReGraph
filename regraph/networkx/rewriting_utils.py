"""A collection of (internal usage) utils for rewriting in the hierarchy."""
import time
import copy
import networkx as nx
import warnings

from regraph.networkx.category_utils import (compose,
                                             compose_chain,
                                             compose_relation_dicts,
                                             get_unique_map_from_pushout,
                                             get_unique_map_to_pullback,
                                             id_of,
                                             is_total_homomorphism,
                                             pullback_complement,
                                             pushout,
                                             pullback,
                                             pushout_from_relation,
                                             image_factorization)
from regraph import primitives
from regraph.exceptions import TotalityWarning
from regraph.rules import Rule
from regraph.utils import keys_by_value


def _rewrite_base(hierarchy, graph_id, rule, instance,
                  rhs_typing, inplace=False):
    g_m, p_g_m, g_m_g =\
        pullback_complement(rule.p, rule.lhs, hierarchy.graph[graph_id],
                            rule.p_lhs, instance, inplace)

    g_prime, g_m_g_prime, r_g_prime = pushout(rule.p, g_m, rule.rhs,
                                              p_g_m, rule.p_rhs, inplace)

    relation_updates = []
    for related_g in hierarchy.adjacent_relations(graph_id):
        relation_updates.append((graph_id, related_g))

    updated_homomorphisms = dict()

    for typing_graph in hierarchy.successors(graph_id):

        new_hom = copy.deepcopy(hierarchy.adj[graph_id][typing_graph]["mapping"])
        removed_nodes = set()
        new_nodes = dict()

        for node in rule.lhs.nodes():
            p_keys = keys_by_value(rule.p_lhs, node)
            # nodes that were removed
            if len(p_keys) == 0:
                removed_nodes.add(instance[node])
            elif len(p_keys) == 1:
                if typing_graph not in rhs_typing.keys() or\
                   rule.p_rhs[p_keys[0]] not in rhs_typing[typing_graph].keys():
                    if r_g_prime[rule.p_rhs[p_keys[0]]] in new_hom.keys():
                        removed_nodes.add(r_g_prime[rule.p_rhs[p_keys[0]]])
            # nodes were clonned
            elif len(p_keys) > 1:
                for k in p_keys:
                    if typing_graph in rhs_typing.keys() and\
                       rule.p_rhs[k] in rhs_typing[typing_graph].keys():
                        new_nodes[r_g_prime[rule.p_rhs[k]]] =\
                            list(rhs_typing[typing_graph][rule.p_rhs[k]])[0]
                    else:
                        removed_nodes.add(r_g_prime[rule.p_rhs[k]])

        for node in rule.rhs.nodes():
            p_keys = keys_by_value(rule.p_rhs, node)

            # nodes that were added
            if len(p_keys) == 0:
                if typing_graph in rhs_typing.keys():
                    if node in rhs_typing[typing_graph].keys():
                        new_nodes[node] = list(rhs_typing[
                            typing_graph][node])[0]

            # nodes that were merged
            elif len(p_keys) > 1:
                for k in p_keys:
                    removed_nodes.add(p_g_m[k])
                # assign new type of node
                if typing_graph in rhs_typing.keys():
                    if node in rhs_typing[typing_graph].keys():
                        new_type = list(rhs_typing[typing_graph][node])
                        new_nodes[r_g_prime[node]] = new_type

        # update homomorphisms
        for n in removed_nodes:
            if n in new_hom.keys():
                del new_hom[n]

        new_hom.update(new_nodes)

        updated_homomorphisms.update({
            (graph_id, typing_graph): new_hom
        })

    return {
        "graph": (g_m, p_g_m, g_m_g, g_prime, g_m_g_prime, r_g_prime),
        "homomorphisms": updated_homomorphisms,
        "relations": relation_updates
    }


def _propagate_rule_up(graph, origin_typing, rule, instance, p_origin,
                       p_typing, inplace=False):

    if inplace is True:
        graph_prime = graph
    else:
        graph_prime = copy.deepcopy(graph)

    if p_typing is None:
        p_typing = {}

    lhs_removed_nodes = rule.removed_nodes()
    lhs_removed_node_attrs = rule.removed_node_attrs()
    p_removed_edges = rule.removed_edges()
    p_removed_edge_attrs = rule.removed_edge_attrs()
    lhs_cloned_nodes = rule.cloned_nodes()

    graph_prime_graph = id_of(graph.nodes())
    graph_prime_origin = copy.deepcopy(origin_typing)

    for lhs_node in rule.lhs.nodes():
        origin_node = instance[lhs_node]
        g_nodes = keys_by_value(
            origin_typing, origin_node)
        for node in g_nodes:
            if lhs_node in lhs_removed_nodes:
                primitives.remove_node(
                    graph_prime, node)
                del graph_prime_graph[node]
                del graph_prime_origin[node]
            else:
                graph_prime_origin[node] = origin_node

    for lhs_node, p_nodes in lhs_cloned_nodes.items():
        nodes_to_clone = keys_by_value(origin_typing, instance[lhs_node])
        for node in nodes_to_clone:
            if node in p_typing.keys():
                p_nodes = p_typing[node]
            for i, p_node in enumerate(p_nodes):
                if i == 0:
                    graph_prime_origin[node] = p_origin[p_node]
                    graph_prime_graph[node] = node
                else:
                    new_name = primitives.clone_node(
                        graph_prime,
                        node)
                    graph_prime_origin[new_name] = p_origin[p_node]
                    graph_prime_graph[new_name] = node
            if len(p_nodes) == 0:
                primitives.remove_node(graph_prime, node)

    for lhs_node, attrs in lhs_removed_node_attrs.items():
        nodes_to_remove_attrs = keys_by_value(
            origin_typing, instance[lhs_node])
        for node in nodes_to_remove_attrs:
            primitives.remove_node_attrs(
                graph_prime,
                node, attrs)

    for p_u, p_v in p_removed_edges:
        us = keys_by_value(graph_prime_origin, p_origin[p_u])
        vs = keys_by_value(graph_prime_origin, p_origin[p_v])
        for u in us:
            for v in vs:
                if (u, v) in graph_prime.edges():
                    primitives.remove_edge(
                        graph_prime, u, v)

    for (p_u, p_v), attrs in p_removed_edge_attrs.items():
        us = keys_by_value(origin_typing, p_origin[p_u])
        vs = keys_by_value(origin_typing, p_origin[p_v])
        for u in us:
            for v in vs:
                primitives.removed_edge_attrs(
                    graph_prime, u, v, attrs)

    return (graph_prime, graph_prime_graph, graph_prime_origin)


def _propagate_up(hierarchy, graph_id, rule, instance,
                  p_origin_m, origin_m_origin_prime,
                  p_typing, inplace=False):
    updated_graphs = dict()
    updated_homomorphisms = dict()
    updated_relations = set()
    updated_rules = dict()
    updated_rule_h = dict()

    if rule.is_restrictive():
        for graph in nx.bfs_tree(hierarchy, graph_id, reverse=True):
            if graph != graph_id:
                if hierarchy.is_graph(graph):
                    origin_typing = hierarchy.get_typing(graph, graph_id)
                    graph_p_typing = None
                    if graph in p_typing.keys():
                        graph_p_typing = p_typing[graph]
                    (graph_prime, graph_prime_graph, graph_prime_origin) =\
                        _propagate_rule_up(
                            hierarchy.graph[graph],
                            origin_typing, rule, instance,
                            p_origin_m, graph_p_typing, inplace)
                    updated_graphs[graph] =\
                        (graph_prime, graph_prime_graph,
                         None, graph_prime_origin)

                    graph_successors = list(hierarchy.successors(graph))
                    if graph_id in graph_successors:
                        updated_homomorphisms[(graph, graph_id)] =\
                            compose(
                                graph_prime_origin,
                                origin_m_origin_prime)
                    if len(rule.removed_nodes()) > 0 or\
                       len(rule.cloned_nodes()) > 0:
                        for suc in graph_successors:
                            if suc != graph_id:
                                if suc in updated_graphs.keys():
                                    graph_prime_suc_prime =\
                                        get_unique_map_to_pullback(
                                            updated_graphs[suc][0].nodes(),
                                            updated_graphs[suc][1],
                                            updated_graphs[suc][3],
                                            compose(
                                                graph_prime_graph,
                                                hierarchy.adj[graph][suc][
                                                    "mapping"]),
                                            graph_prime_origin)
                                else:
                                    graph_prime_suc_prime = compose(
                                        graph_prime_graph, hierarchy.adj[
                                            graph][suc]["mapping"])
                                updated_homomorphisms[(graph, suc)] =\
                                    graph_prime_suc_prime

                        for pred in hierarchy.predecessors(graph):
                            if pred in updated_graphs.keys():
                                pred_m_graph_m = get_unique_map_to_pullback(
                                    graph_prime.nodes(),
                                    graph_prime_graph,
                                    graph_prime_origin,
                                    updated_graphs[pred][1],
                                    updated_graphs[pred][3]
                                )
                                updated_homomorphisms[
                                    (pred, graph)] = pred_m_graph_m

                        # propagate changes to adjacent relations
                        for related_g in hierarchy.adjacent_relations(graph):
                            updated_relations.add((graph, related_g))
                else:
                    rule_to_rewrite = hierarchy.node[graph]["rule"]

                    (lhs_origin_typing,
                     p_origin_typing,
                     rhs_origin_typing) =\
                        hierarchy.get_rule_typing(graph, graph_id)

                    (lhs_prime, lhs_prime_lhs, lhs_prime_origin) =\
                        _propagate_rule_up(
                            rule_to_rewrite.lhs,
                            lhs_origin_typing, rule, instance,
                            p_origin_m, inplace=False)

                    (pr_prime, pr_prime_pr, pr_prime_origin) =\
                        _propagate_rule_up(
                            rule_to_rewrite.p,
                            p_origin_typing, rule, instance,
                            p_origin_m, inplace=False)

                    (rhs_prime, rhs_prime_rhs, rhs_prime_origin) =\
                        _propagate_rule_up(
                            rule_to_rewrite.rhs,
                            rhs_origin_typing, rule, instance,
                            p_origin_m, inplace=False)

                    # find p_m -> lhs_m
                    new_p_lhs = get_unique_map_to_pullback(
                        lhs_prime.nodes(),
                        lhs_prime_lhs,
                        lhs_prime_origin,
                        compose(pr_prime_pr, rule_to_rewrite.p_lhs),
                        pr_prime_origin
                    )

                    # find p_m -> rhs_m
                    new_p_rhs = get_unique_map_to_pullback(
                        rhs_prime.nodes(),
                        rhs_prime_rhs,
                        rhs_prime_origin,
                        compose(pr_prime_pr, rule_to_rewrite.p_rhs),
                        pr_prime_origin
                    )

                    new_rule =\
                        Rule(pr_prime, lhs_prime, rhs_prime,
                             new_p_lhs, new_p_rhs)

                    updated_rules[graph] = new_rule

                    for suc in hierarchy.successors(graph):
                        if suc == graph_id:
                            lhs_prime_suc_prime =\
                                compose(lhs_prime_origin,
                                        origin_m_origin_prime)
                            rhs_prime_suc_prime =\
                                compose(rhs_prime_origin,
                                        origin_m_origin_prime)

                        if suc in updated_graphs.keys():
                            lhs_prime_suc_prime = get_unique_map_to_pullback(
                                updated_graphs[suc][0].nodes(),
                                updated_graphs[suc][1],
                                updated_graphs[suc][3],
                                compose(
                                    lhs_prime_lhs,
                                    hierarchy.adj[graph][suc]["lhs_mapping"]),
                                lhs_prime_origin
                            )
                            rhs_prime_suc_prime = get_unique_map_to_pullback(
                                updated_graphs[suc][0].nodes(),
                                updated_graphs[suc][1],
                                updated_graphs[suc][3],
                                compose(
                                    rhs_prime_rhs,
                                    hierarchy.adj[graph][suc]["rhs_mapping"]
                                ),
                                rhs_prime_origin
                            )

                        else:
                            lhs_prime_suc_prime =\
                                compose(
                                    lhs_prime_lhs,
                                    hierarchy.adj[graph][suc]["lhs_mapping"])
                            rhs_prime_suc_prime =\
                                compose(
                                    rhs_prime_rhs,
                                    hierarchy.adj[graph][suc]["rhs_mapping"])

                        updated_rule_h[(graph, suc)] =\
                            (lhs_prime_suc_prime, rhs_prime_suc_prime)

    else:
        for pred in hierarchy.predecessors(graph_id):
            if hierarchy.is_graph(pred):
                updated_homomorphisms[(pred, graph_id)] =\
                    compose(
                        hierarchy.adj[pred][graph_id]["mapping"],
                        origin_m_origin_prime)
            else:
                updated_rule_h[(pred, graph_id)] = (
                    compose(
                        hierarchy.adj[pred][graph_id]["lhs_mapping"],
                        origin_m_origin_prime),
                    compose(
                        hierarchy.adj[pred][graph_id]["rhs_mapping"],
                        origin_m_origin_prime)
                )

    return {
        "graphs": updated_graphs,
        "homomorphisms": updated_homomorphisms,
        "rules": updated_rules,
        "rule_homomorphisms": updated_rule_h,
        "relations": updated_relations
    }


def _propagate_down(hierarchy, origin_id, origin_construct,
                    rule, instance, rhs_typing_rels, inplace=False):
    """Propagate changes down the hierarchy."""
    updated_graphs = dict()
    updated_homomorphisms = dict()
    updated_relations = []

    (origin_m,
     origin_m_origin,
     origin_prime,
     origin_m_origin_prime,
     rhs_origin_prime) = origin_construct

    if rule.is_relaxing():
        for graph in nx.bfs_tree(hierarchy, origin_id):
            if graph != origin_id:
                relation_g_rhs = set()
                for key, values in rhs_typing_rels[graph].items():
                    for v in values:
                        relation_g_rhs.add((v, key))

                (g_prime, g_g_prime, rhs_g_prime) =\
                    pushout_from_relation(
                        hierarchy.graph[graph], rule.rhs,
                        relation_g_rhs, inplace)
                updated_graphs[graph] = (g_prime, g_g_prime, rhs_g_prime)

                graph_predecessors = hierarchy.predecessors(graph)
                if origin_id in graph_predecessors:
                    updated_homomorphisms[(origin_id, graph)] =\
                        get_unique_map_from_pushout(
                            origin_prime.nodes(),
                            origin_m_origin_prime,
                            rhs_origin_prime,
                            compose_chain(
                                [origin_m_origin,
                                 hierarchy.adj[origin_id][graph]["mapping"],
                                 g_g_prime]),
                            rhs_g_prime)

                if len(rule.added_nodes()) > 0 or\
                   len(rule.merged_nodes()) > 0:
                    for pred in hierarchy.predecessors(graph):
                        if pred in updated_graphs.keys():
                            if pred != origin_id:
                                updated_homomorphisms[(pred, graph)] =\
                                    get_unique_map_from_pushout(
                                        updated_graphs[pred][0].nodes(),
                                        updated_graphs[pred][1],
                                        updated_graphs[pred][2],
                                        compose(
                                            hierarchy.adj[
                                                pred][graph]["mapping"],
                                            g_g_prime),
                                        rhs_g_prime)
                    for suc in hierarchy.successors(graph):
                        if suc in updated_graphs.keys():
                            updated_homomorphisms[(graph, suc)] =\
                                get_unique_map_from_pushout(
                                    g_prime.nodes(),
                                    g_g_prime,
                                    rhs_g_prime,
                                    compose(
                                        hierarchy.adj[graph][suc]["mapping"],
                                        updated_graphs[suc][1]),
                                    updated_graphs[suc][2])
                if len(rule.merged_nodes()) > 0:
                    # propagate changes to adjacent relations
                    for related_g in hierarchy.adjacent_relations(graph):
                        updated_relations.append((graph, related_g))

    else:
        for suc in hierarchy.successors(origin_id):
            updated_homomorphisms[(origin_id, suc)] =\
                compose(
                    origin_m_origin,
                    hierarchy.adj[origin_id][suc]["mapping"])

    return {
        "graphs": updated_graphs,
        "homomorphisms": updated_homomorphisms,
        "relations": updated_relations
    }


def _apply_changes(hierarchy, upstream_changes, downstream_changes):
    """Apply changes to the hierarchy."""
    # update relations
    visited = set()
    rels = dict()
    start = time.time()
    for g1, g2 in upstream_changes["relations"]:
        if (g1, g2) not in visited and (g2, g1) not in visited:
            new_relation = dict()
            # upstream changes in both related graphs

            if (g2, g1) in upstream_changes["relations"]:

                # update left side
                new_left_dict = dict()
                left_dict = hierarchy.relation[g1][g2]
                for node in upstream_changes["graphs"][g1][0].nodes():
                    old_node = upstream_changes["graphs"][g1][1][node]
                    if old_node in left_dict.keys():
                        new_left_dict[node] = left_dict[old_node]

                # update right side
                new_right_dict = dict()
                right_dict = hierarchy.relation[g2][g1]
                for node in upstream_changes["graphs"][g2][0].nodes():
                    old_node = upstream_changes["graphs"][g2][1][node]
                    if old_node in right_dict.keys():
                        new_right_dict[node] = right_dict[old_node]

                new_relation = compose_relation_dicts(
                    new_left_dict, new_right_dict)

            # downstream changes in one of the related graphs
            elif "relations" in downstream_changes.keys() and\
                 "graphs" in downstream_changes.keys() and\
                 (g2, g1) in downstream_changes["relations"]:
                # update left side
                left_dict = hierarchy.relation[g1][g2]
                for node in upstream_changes["graphs"][g1][0].nodes():
                    old_node = upstream_changes["graphs"][g1][1][node]
                    if old_node in left_dict.keys():
                        for right_el in left_dict[old_node]:
                            if node in new_relation.keys():
                                new_relation[node].add(
                                    downstream_changes[
                                        "graphs"][g2][1][right_el])
                            else:
                                new_relation[node] =\
                                    {downstream_changes[
                                     "graphs"][g2][1][right_el]}

            # updates in a single graph involved in the relation
            else:
                left_dict = hierarchy.relation[g1][g2]
                for node in upstream_changes["graphs"][g1][0].nodes():
                    if node in upstream_changes["graphs"][g1][1].keys():
                        old_node = upstream_changes["graphs"][g1][1][node]
                        if old_node in left_dict.keys():
                            for el in left_dict[old_node]:
                                if node in new_relation.keys():
                                    new_relation[node].add(el)
                                else:
                                    new_relation[node] = {el}
            rels[(g1, g2)] = new_relation
            visited.add((g1, g2))

    if "relations" in downstream_changes.keys() and\
       "graphs" in downstream_changes.keys():
        for g1, g2 in downstream_changes["relations"]:
            if (g1, g2) not in visited and (g2, g1) not in visited:
                # downstream changes in both related graphs
                new_relation = dict()
                if (g2, g1) in downstream_changes["relations"]:
                    left_dict = hierarchy.relation[g1][g2]
                    for left_el, right_els in left_dict.items():
                        new_left_node =\
                            downstream_changes["graphs"][g1][1][left_el]
                        for right_el in right_els:
                            new_right_node =\
                                downstream_changes["graphs"][g2][1][right_el]
                            if new_left_node in new_relation.keys():
                                new_relation[new_left_node].add(new_right_node)
                            else:
                                new_relation[new_left_node] = {new_right_node}
                else:
                    left_dict = hierarchy.relation[g1][g2]
                    for left_el, right_els in left_dict.items():
                        new_left_node =\
                            downstream_changes["graphs"][g1][1][left_el]
                        for right_el in right_els:
                            if new_left_node in new_relation.keys():
                                new_relation[new_left_node].add(right_el)
                            else:
                                new_relation[new_left_node] = {right_el}
                rels[(g1, g2)] = new_relation
                visited.add((g1, g2))

    # update graphs
    for graph, (graph_m, _, graph_prime, _) in upstream_changes["graphs"].items():
        if graph_prime is not None:
            hierarchy.node[graph]["graph"] = graph_prime
        else:
            hierarchy.node[graph]["graph"] = graph_m
        hierarchy.graph[graph] = hierarchy.node[graph]["graph"]

    if "graphs" in downstream_changes.keys():
        for graph, (graph_prime, _, _) in downstream_changes["graphs"].items():
            hierarchy.node[graph]["graph"] = graph_prime
            hierarchy.graph[graph] = hierarchy.node[graph]["graph"]

    # update relation
    for (g1, g2), rel in rels.items():
        old_attrs = copy.deepcopy(hierarchy.relation_edges[g1, g2]["attrs"])
        hierarchy.remove_relation(g1, g2)
        hierarchy.add_relation(g1, g2, rel, old_attrs)

    # update homomorphisms
    updated_homomorphisms = dict()
    updated_homomorphisms.update(upstream_changes["homomorphisms"])
    if "homomorphisms" in downstream_changes.keys():
        updated_homomorphisms.update(downstream_changes["homomorphisms"])

    for (s, t), mapping in updated_homomorphisms.items():
        primitives.assign_attrs(
            hierarchy.adj[s][t],
            {
                "mapping": mapping,
                "attrs": hierarchy.adj[s][t]["attrs"]
            }
        )
        hierarchy.typing[s][t] = hierarchy.adj[s][t]["mapping"]

    # update rules & rule homomorphisms
    for rule, new_rule in upstream_changes["rules"].items():
        primitives.assign_attrs(
            hierarchy.node[rule],
            {
                "rule": new_rule,
                "attrs": hierarchy.node[rule]["attrs"]
            }
        )
        hierarchy.rule[rule] = hierarchy.node[rule]["rule"]
    for (s, t), (lhs_h, rhs_h) in upstream_changes["rule_homomorphisms"].items():
        primitives.assign_attrs(
            hierarchy.adj[s][t],
            {
                "lhs_mapping": lhs_h,
                "rhs_mapping": rhs_h,
                "attrs": hierarchy.adj[s][t]["attrs"]
            }
        )
        hierarchy.rule_lhs_typing[s][t] = hierarchy.adj[s][t]["lhs_mapping"]
        hierarchy.rule_rhs_typing[s][t] = hierarchy.adj[s][t]["rhs_mapping"]
    return


def _get_rule_liftings(hierarchy, origin_id, rule, instance, p_typing):
    liftings = {}
    if rule.is_restrictive():
        for graph in nx.bfs_tree(hierarchy, origin_id, reverse=True):
            if graph != origin_id:
                if hierarchy.is_graph(graph):
                    origin_typing = hierarchy.get_typing(graph, origin_id)

                    # Compute L_G
                    l_g, l_g_g, l_g_l = pullback(
                        hierarchy.graph[graph], rule.lhs,
                        hierarchy.graph[origin_id],
                        origin_typing, instance)

                    # Compute canonical P_G
                    canonical_p_g, p_g_l_g, p_g_p = pullback(
                        l_g, rule.p, rule.lhs, l_g_l, rule.p_lhs)

                    # Remove controlled things from P_G
                    if graph in p_typing.keys():
                        l_g_factorization = {
                            keys_by_value(l_g_g, k)[0]: v
                            for k, v in p_typing[graph].items()
                        }
                        p_g_nodes_to_remove = set()
                        for n in canonical_p_g.nodes():
                            l_g_node = p_g_l_g[n]
                            # If corresponding L_G node is specified in
                            # the controlling relation, remove all
                            # the instances of P nodes not mentioned
                            # in this relations
                            if l_g_node in l_g_factorization.keys():
                                p_nodes = l_g_factorization[l_g_node]
                                if p_g_p[n] not in p_nodes:
                                    del p_g_p[n]
                                    del p_g_l_g[n]
                                    p_g_nodes_to_remove.add(n)

                        for n in p_g_nodes_to_remove:
                            primitives.remove_node(canonical_p_g, n)
                    liftings[graph] = {
                        "rule": Rule(canonical_p_g, l_g, p_lhs=p_g_l_g),
                        "instance": l_g_g,
                        "p_g_p": p_g_p
                    }
    return liftings


def _get_rule_projections(hierarchy, origin_id, rule, instance, rhs_typing):
    projections = {}
    if rule.is_relaxing():
        for graph in nx.bfs_tree(hierarchy, origin_id):
            if graph != origin_id:
                if hierarchy.is_graph(graph):
                    origin_typing = hierarchy.get_typing(origin_id, graph)

                    # Compute canonical P_T
                    p_t, p_p_t, p_t_t = image_factorization(
                        rule.p, hierarchy.graph[graph],
                        compose(
                            compose(rule.p_lhs, instance),
                            origin_typing))

                    # Compute canonical R_T
                    r_t, p_t_r_t, r_r_t = pushout(
                        rule.p, p_t, rule.rhs,
                        p_p_t, rule.p_rhs)

                    # Modify P_T and R_T according to the controlling
                    # relation rhs_typing
                    if graph in rhs_typing.keys():
                        r_t_factorization = {
                            r_r_t[k]: v
                            for k, v in rhs_typing[graph].items()
                        }
                        added_t_nodes = set()
                        for n in r_t.nodes():
                            if n in r_t_factorization.keys():
                                # If corresponding R_T node is specified in
                                # the controlling relation add nodes of T
                                # that type it to P
                                t_nodes = r_t_factorization[n]
                                for t_node in t_nodes:
                                    if t_node not in p_t_t.values() and\
                                       t_node not in added_t_nodes:
                                        print(">>>", t_node)
                                        new_p_node = primitives.generate_new_node_id(
                                            p_t, t_node)
                                        primitives.add_node(p_t, new_p_node)
                                        added_t_nodes.add(t_node)
                                        p_t_r_t[new_p_node] = n
                                        p_t_t[new_p_node] = t_node
                                    else:
                                        p_t_r_t[keys_by_value(p_t_t, t_node)[0]] = n

                    projections[graph] = {
                        "rule": Rule(p_t, p_t, r_t, p_rhs=p_t_r_t),
                        "instance": p_t_t,
                        "p_p_t": p_p_t,
                        "r_r_t": r_r_t
                    }

    return projections
