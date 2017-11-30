"""A collection of utils for rewriting and propagation in the hierarchy."""
import copy
import networkx as nx
import warnings

from regraph.category_op import (compose,
                                 compose_chain,
                                 get_unique_map_from_pushout,
                                 get_unique_map_to_pullback,
                                 id_of,
                                 is_total_homomorphism,
                                 pullback,
                                 pullback_complement,
                                 pushout,
                                 relation_to_span,
                                 pullback_complement,
                                 pushout)
from regraph import primitives
from regraph.exceptions import RewritingError, TotalityWarning
from regraph.rules import Rule
from regraph.utils import keys_by_value


def _rewrite_base(hierarchy, graph_id, rule, instance,
                  lhs_typing, rhs_typing, inplace=False):
    g_m, p_g_m, g_m_g =\
        pullback_complement(rule.p, rule.lhs, hierarchy.node[graph_id].graph,
                            rule.p_lhs, instance, inplace)

    g_prime, g_m_g_prime, r_g_prime = pushout(rule.p, g_m, rule.rhs,
                                              p_g_m, rule.p_rhs, inplace)

    # Update typings of the graph_id after rewriting
    typing_updates =\
        _update_typing(
            hierarchy, graph_id, rule, instance, lhs_typing,
            rhs_typing, p_g_m, r_g_prime)

    relation_updates = []
    for related_g in hierarchy.adjacent_relations(graph_id):
        relation_updates.append((graph_id, related_g))

    return {
        "graph": (g_m, p_g_m, g_m_g, g_prime, g_m_g_prime, r_g_prime),
        "homomorphisms": typing_updates,
        "relations": relation_updates
    }


def _temp_helper(graph, origin_typing, rule, instance, inplace=False):

    if inplace is True:
        graph_prime = graph
    else:
        graph_prime = copy.deepcopy(graph)

    lhs_removed_nodes = rule.removed_nodes()
    lhs_removed_node_attrs = rule.removed_node_attrs()
    lhs_removed_edges = rule.removed_edges()
    lhs_removed_edge_attrs = rule.removed_edge_attrs()
    lhs_cloned_nodes = rule.cloned_nodes()

    graph_prime_graph = id_of(graph.nodes())
    graph_prime_p = dict()

    for lhs_node in rule.lhs.nodes():
        g_nodes = keys_by_value(
            origin_typing, instance[lhs_node])
        for node in g_nodes:
            if lhs_node in lhs_removed_nodes:
                primitives.remove_node(
                    graph_prime, node)
                del graph_prime_graph[node]
            else:
                p_nodes = keys_by_value(rule.p_lhs, lhs_node)
                if len(p_nodes) == 1:
                    graph_prime_p[node] = p_nodes[0]

    for lhs_node, attrs in lhs_removed_node_attrs.items():
        nodes_to_remove_attrs = keys_by_value(
            origin_typing, instance[lhs_node])
        for node in nodes_to_remove_attrs:
            primitives.remove_node_attrs(
                graph_prime,
                node, attrs)

    for lhs_u, lhs_v in lhs_removed_edges:

        us = keys_by_value(origin_typing, instance[lhs_u])
        vs = keys_by_value(origin_typing, instance[lhs_v])
        for u in us:
            for v in vs:
                if (u, v) in graph_prime.edges():
                    primitives.remove_edge(
                        graph_prime, u, v)

    for (lhs_u, lhs_v), attrs in lhs_removed_edge_attrs.items():
        us = keys_by_value(origin_typing, instance[lhs_u])
        vs = keys_by_value(origin_typing, instance[lhs_v])
        for u in us:
            for v in vs:
                primitives.removed_edge_attrs(
                    graph_prime, u, v, attrs)

    for lhs_node, p_nodes in lhs_cloned_nodes.items():
        nodes_to_clone = keys_by_value(origin_typing, lhs_node)
        for node in nodes_to_clone:
            for i, p_node in enumerate(p_nodes):
                if i == 0:
                    graph_prime_p[node] = p_node
                else:
                    new_name = primitives.clone_node(
                        graph_prime,
                        node)
                    graph_prime_p[new_name] = p_node

    return (graph_prime, graph_prime_graph, graph_prime_p)


def _propagate_up(hierarchy, graph_id, rule, instance,
                  p_origin_m, origin_m_origin_prime, inplace=False):

    updated_graphs = dict()
    updated_homomorphisms = dict()
    updated_relations = set()
    updated_rules = dict()
    updated_rule_h = dict()

    for graph in nx.bfs_tree(hierarchy, graph_id, reverse=True):
        if graph != graph_id:
            if isinstance(hierarchy.node[graph], hierarchy.graph_node_cls):

                origin_typing = hierarchy.get_typing(graph, graph_id)

                (graph_prime, graph_prime_graph, graph_prime_p) =\
                    _temp_helper(hierarchy.node[graph].graph,
                                 origin_typing, rule, instance,
                                 inplace)
                updated_graphs[graph] =\
                    (graph_prime, graph_prime_graph, None, graph_prime_p)

                for suc in hierarchy.successors(graph):

                    if suc == graph_id:
                        updated_homomorphisms[(graph, suc)] =\
                            compose(graph_prime_p, p_origin_m)

                    elif suc in updated_graphs.keys():
                        graph_prime_suc_prime =\
                            get_unique_map_to_pullback(
                                updated_graphs[suc][0].nodes(),
                                updated_graphs[suc][1],
                                updated_graphs[suc][3],
                                graph_prime_graph,
                                graph_prime_p)

                        updated_homomorphisms[
                            (graph, suc)] = graph_prime_suc_prime
                        pass

                    else:
                        graph_prime_suc = compose(
                            graph_prime_graph, hierarchy.edge[graph][suc].mapping)
                        updated_homomorphisms[
                            (graph, suc)] = graph_prime_suc

                for pred in hierarchy.predecessors(graph):
                    if pred in updated_graphs.keys():
                        pred_m_graph_m = get_unique_map_to_pullback(
                            graph_prime.nodes(),
                            graph_prime_graph,
                            graph_prime_p,
                            updated_graphs[pred][1],
                            updated_graphs[pred][3]
                        )
                        updated_homomorphisms[
                            (pred, graph)] = pred_m_graph_m

                # propagate changes to adjacent relations
                for related_g in hierarchy.adjacent_relations(graph):
                    updated_relations.add((graph, related_g))
            else:
                if isinstance(hierarchy.node[graph], hierarchy.graph_node_cls):

                    rule_to_rewrite = hierarchy.node[graph].rule

                    (lhs_origin_typing,
                     p_origin_typing,
                     rhs_origin_typing) =\
                        hierarchy.get_rule_typing(graph, graph_id)

                    (lhs_prime, lhs_prime_lhs, lhs_prime_p) =\
                        _temp_helper(rule_to_rewrite.lhs,
                                     lhs_origin_typing, rule, instance,
                                     inplace)

                    (pr_prime, pr_prime_pr, pr_prime_p) =\
                        _temp_helper(rule_to_rewrite.p,
                                     p_origin_typing, rule, instance,
                                     inplace)

                    (rhs_prime, rhs_prime_rhs, rhs_prime_p) =\
                        _temp_helper(rule_to_rewrite.rhs,
                                     rhs_origin_typing, rule, instance,
                                     inplace)

                    # find p_m -> lhs_m
                    new_p_lhs = get_unique_map_to_pullback(
                        lhs_prime.nodes(),
                        lhs_prime_lhs,
                        lhs_prime_p,
                        compose(pr_prime_pr, rule.p_lhs),
                        pr_prime_p
                    )

                    # find p_m -> rhs_m
                    new_p_rhs = get_unique_map_to_pullback(
                        rhs_prime.nodes(),
                        rhs_prime_rhs,
                        rhs_prime_p,
                        compose(pr_prime_pr, rule.p_rhs),
                        pr_prime_p
                    )

                    new_rule =\
                        Rule(pr_prime, lhs_prime, rhs_prime,
                             new_p_lhs, new_p_rhs)

                    updated_rules[graph] = new_rule

                    for suc in hierarchy.successors(graph):
                        if suc in updated_graphs.keys():
                            lhs_prime_suc_prime = get_unique_map_to_pullback(
                                updated_graphs[suc][0].nodes(),
                                updated_graphs[suc][1],
                                updated_graphs[suc][2],
                                compose(
                                    lhs_prime_lhs,
                                    hierarchy.edge[graph][suc].lhs_mapping),
                                lhs_prime_p
                            )
                            rhs_prime_suc_prime = get_unique_map_to_pullback(
                                updated_graphs[suc][0],
                                updated_graphs[suc][1],
                                updated_graphs[suc][2],
                                compose(
                                    rhs_prime_rhs,
                                    hierarchy.edge[graph][suc].rhs_mapping
                                ),
                                rhs_prime_p
                            )

                        else:
                            lhs_prime_suc_prime =\
                                compose(
                                    lhs_prime_lhs,
                                    hierarchy.edge[graph][suc].lhs_mapping)
                            rhs_prime_suc_prime =\
                                compose(
                                    rhs_prime_rhs,
                                    hierarchy.edge[graph][suc].rhs_mapping)

                        updated_rule_h[(graph, suc)] =\
                            (lhs_prime_suc_prime, rhs_prime_suc_prime)

    return {
        "graphs": updated_graphs,
        "homomorphisms": updated_homomorphisms,
        "rules": updated_rules,
        "rule_homomorphisms": updated_rule_h,
        "relations": updated_relations
    }


# def _propagate_up(hierarchy, graph_id, origin_m, origin_m_origin,
#                   origin_prime, origin_m_origin_prime, inplace=False):
#     """Propagation steps: based on reverse BFS on neighbours."""
#     updated_graphs = {
#         graph_id: (
#             origin_m,
#             origin_m_origin,
#             origin_prime,
#             origin_m_origin_prime
#         )
#     }
#     updated_homomorphisms = {}

#     updated_rules = dict()
#     updated_rule_h = dict()
#     updated_relations = []

#     current_level = set(hierarchy.predecessors(graph_id))

#     visited = set()

#     g_m_origin_m = dict()
#     lhs_m_origin_m = dict()
#     rhs_m_origin_m = dict()

#     while len(current_level) > 0:

#         next_level = set()

#         for graph in current_level:

#             visited.add(graph)

#             if isinstance(hierarchy.node[graph], hierarchy.graph_node_cls):

#                 origin_typing = hierarchy.get_typing(graph, graph_id)
#                 g_m, g_m_g, g_m_origin_m[graph] =\
#                     pullback(hierarchy.node[graph].graph, updated_graphs[graph_id][0],
#                              hierarchy.node[graph_id].graph, origin_typing,
#                              updated_graphs[graph_id][1], total=False)
#                 updated_graphs[graph] = (g_m, g_m_g, g_m, id_of(g_m.nodes()))
#                 for suc in hierarchy.successors(graph):
#                     if suc == graph_id:
#                         updated_homomorphisms[(graph, suc)] =\
#                             compose(g_m_origin_m[graph], origin_m_origin_prime)
#                     else:
#                         if suc in visited:
#                             graph_m_suc_m = get_unique_map_to_pullback(
#                                 updated_graphs[suc][0].nodes(),
#                                 updated_graphs[suc][1],
#                                 g_m_origin_m[suc],
#                                 compose(g_m_g, hierarchy.edge[graph][suc].mapping),
#                                 g_m_origin_m[graph]
#                             )
#                             updated_homomorphisms[
#                                 (graph, suc)] = graph_m_suc_m
#                         else:
#                             graph_m_suc = compose(g_m_g, hierarchy.edge[graph][suc].mapping)
#                             updated_homomorphisms[
#                                 (graph, suc)] = graph_m_suc

#                 for pred in hierarchy.predecessors(graph):
#                     if pred in visited:
#                         pred_m_graph_m = get_unique_map_to_pullback(
#                             g_m.nodes(),
#                             g_m_g,
#                             g_m_origin_m[graph],
#                             hierarchy.edge[pred][graph].mapping,
#                             g_m_origin_m[pred]
#                         )
#                         updated_homomorphisms[
#                             (pred, graph)] = pred_m_graph_m

#                 # propagate changes to adjacent relations
#                 for related_g in hierarchy.adjacent_relations(graph):
#                     updated_relations.append((graph, related_g))

#             elif isinstance(hierarchy.node[graph], hierarchy.rule_node_cls):
#                 rule = hierarchy.node[graph].rule
#                 (
#                     lhs_origin_typing, p_origin_typing, rhs_origin_typing
#                 ) = hierarchy.get_rule_typing(graph, graph_id)

#                 # propagation to lhs
#                 lhs_m, lhs_m_lhs, lhs_m_origin_m[graph] = pullback(
#                     rule.lhs,
#                     updated_graphs[graph_id][0],
#                     hierarchy.node[graph_id].graph,
#                     lhs_origin_typing,
#                     updated_graphs[graph_id][1],
#                     total=False
#                 )

#                 # propagation to p
#                 p_m, p_m_p, p_m_origin_m = pullback(
#                     rule.p,
#                     updated_graphs[graph_id][0],
#                     hierarchy.node[graph_id].graph,
#                     p_origin_typing,
#                     updated_graphs[graph_id][1],
#                 )

#                 # propagation to rhs
#                 rhs_m, rhs_m_rhs, rhs_m_origin_m[graph] = pullback(
#                     rule.rhs,
#                     updated_graphs[graph_id][0],
#                     hierarchy.node[graph_id].graph,
#                     rhs_origin_typing,
#                     updated_graphs[graph_id][1],
#                 )

#                 # find p_m -> lhs_m
#                 new_p_lhs = get_unique_map_to_pullback(
#                     lhs_m.nodes(),
#                     lhs_m_lhs,
#                     lhs_m_origin_m[graph],
#                     compose(p_m_p, rule.p_lhs),
#                     p_m_origin_m
#                 )

#                 # find p_m -> rhs_m
#                 new_p_rhs = get_unique_map_to_pullback(
#                     rhs_m.nodes(),
#                     rhs_m_rhs,
#                     rhs_m_origin_m[graph],
#                     compose(p_m_p, rule.p_rhs),
#                     p_m_origin_m
#                 )

#                 new_rule = Rule(
#                     p_m, lhs_m, rhs_m, new_p_lhs, new_p_rhs
#                 )

#                 updated_rules[graph] = new_rule

#                 for suc in hierarchy.successors(graph):
#                     if suc in visited:
#                         lhs_m_suc_m = get_unique_map_to_pullback(
#                             updated_graphs[suc][0].nodes(),
#                             updated_graphs[suc][1],
#                             g_m_origin_m[suc],
#                             compose(
#                                 lhs_m_origin_m[graph],
#                                 hierarchy.edge[graph][suc].lhs_mapping),
#                             lhs_m_lhs
#                         )
#                         rhs_m_suc_m = get_unique_map_to_pullback(
#                             updated_graphs[suc][0],
#                             updated_graphs[suc][1],
#                             g_m_origin_m[suc],
#                             compose(
#                                 rhs_m_rhs,
#                                 hierarchy.edge[graph][suc].rhs_mapping
#                             ),
#                             rhs_m_origin_m[graph]
#                         )

#                     else:
#                         lhs_m_suc_m = compose(
#                             lhs_m_lhs, hierarchy.edge[graph][suc].lhs_mapping
#                         )
#                         rhs_m_suc_m = compose(
#                             rhs_m_rhs, hierarchy.edge[graph][suc].rhs_mapping
#                         )
#                     updated_rule_h[(graph, suc)] =\
#                         (lhs_m_suc_m, rhs_m_suc_m)

#             else:
#                 raise RewritingError(
#                     "Unknown type '%s' of the node '%s'!" %
#                     (type(hierarchy.node[graph]), graph)
#                 )

#             # update step
#             next_level.update(
#                 [p for p in hierarchy.predecessors(graph) if p not in visited]
#             )

#         current_level = next_level

#     del updated_graphs[graph_id]
#     return {
#         "graphs": updated_graphs,
#         "homomorphisms": updated_homomorphisms,
#         "rules": updated_rules,
#         "rule_homomorphisms": updated_rule_h,
#         "relations": updated_relations
#     }


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

    for graph in nx.bfs_tree(hierarchy, origin_id):
        if graph != origin_id:

            relation_rhs_g = set()
            for key, values in rhs_typing_rels[graph].items():
                for v in values:
                    relation_rhs_g.add((key, v))

            rhs_g, rhs_g_rhs, rhs_g_g =\
                relation_to_span(
                    rule.rhs,
                    hierarchy.node[graph].graph,
                    relation_rhs_g,
                    directed=hierarchy.directed)

            (g_prime, g_g_prime, rhs_g_prime) =\
                pushout(rhs_g, hierarchy.node[graph].graph,
                        rule.rhs, rhs_g_g, rhs_g_rhs)

            updated_graphs[graph] = (g_prime, g_g_prime, rhs_g_prime)

            for suc in hierarchy.successors(graph):
                if suc in updated_graphs.keys():
                    updated_homomorphisms[(graph, suc)] =\
                        get_unique_map_from_pushout(
                            g_prime, g_g_prime, rhs_g_prime,
                            compose(
                                hierarchy.edge[graph][suc].mapping,
                                updated_graphs[suc][1]),
                            updated_graphs[suc][2])

            for pred in hierarchy.predecessors(graph):
                if pred == origin_id:

                    updated_homomorphisms[(pred, graph)] =\
                        get_unique_map_from_pushout(
                            origin_prime.nodes(),
                            origin_m_origin_prime,
                            rhs_origin_prime,
                            compose_chain(
                                [origin_m_origin,
                                 hierarchy.edge[pred][graph].mapping,
                                 g_g_prime]),
                            rhs_g_prime)

                elif pred in updated_graphs.keys():
                    updated_homomorphisms[(pred, graph)] =\
                        get_unique_map_from_pushout(
                            updated_graphs[pred][0],
                            updated_graphs[pred][1],
                            updated_graphs[pred][2],
                            compose(
                                hierarchy.edge[pred][graph].mapping,
                                g_g_prime),
                            rhs_g_prime)

            # propagate changes to adjacent relations
            for related_g in hierarchy.adjacent_relations(graph):
                updated_relations.append((graph, related_g))

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
    for g1, g2 in upstream_changes["relations"]:
        if (g1, g2) not in visited:
            common_g, left_h, right_h = hierarchy.relation_to_span(g1, g2)
            left_g, left_g_common_g, left_g_g_m =\
                pullback(common_g, upstream_changes["graphs"][g1][0],
                         hierarchy.node[g1].graph, left_h,
                         upstream_changes["graphs"][g1][1])
            # upstream changes in both related graphs
            if (g2, g1) in upstream_changes["relations"]:
                right_g, right_g_common_g, right_g_g_m =\
                    pullback(common_g, upstream_changes["graphs"][g2][0],
                             hierarchy.node[g2].graph, right_h,
                             upstream_changes["graphs"][g2][1])

                new_common_g, new_left_g, new_right_g =\
                    pullback(left_g, right_g, common_g,
                             left_g_common_g, right_g_common_g)

                new_left_g_m = compose(new_left_g, left_g_g_m)
                new_right_g_m = compose(new_right_g, right_g_g_m)
            # downstream changes in one of the related graphs
            elif downstream_changes is not None and (g2, g1) in downstream_changes["relations"]:
                new_left_g_m = left_g_g_m
                new_right_g_m = compose(
                    [left_g_common_g, right_h, downstream_changes["graphs"][g2][1]]
                )
            # updates in a single graph involved in the relation
            else:
                new_left_g_m = left_g_g_m
                new_right_g_m = compose(left_g_common_g, right_h)

            new_rel = list()
            for node in new_common_g.nodes():
                new_rel.append((new_left_g_m[node], new_right_g_m[node]))

            visited.add((g1, g2))
            rels.update({(g1, g2): new_rel})

    if downstream_changes is not None:
        for g1, g2 in downstream_changes["relations"]:
            if (g1, g2) not in visited:
                common_g, left_h, right_h = hierarchy.relation_to_span(g1, g2)
                # downstream changes in both related graphs
                if (g2, g1) in downstream_changes["relations"]:
                    new_left_g_m = compose(
                        downstream_changes["graphs"][g1], left_h)
                    new_right_g_m = compose(
                        downstream_changes["graphs"][g2], right_h)
                else:
                    new_left_g_m = compose(
                        downstream_changes["graphs"][g1], left_h)
                    new_right_g_m = right_h

                new_rel = list()
                for node in new_common_g.nodes():
                    new_rel.append((new_left_g_m[node], new_right_g_m[node]))

                visited.add((g1, g2))
                rels.update({(g1, g2): new_rel})

    # update graphs
    for graph, (graph_m, _, graph_prime, _) in upstream_changes["graphs"].items():
        if graph_prime is not None:
            hierarchy.node[graph].graph = graph_prime
        else:
            hierarchy.node[graph].graph = graph_m
    if downstream_changes is not None:
        for graph, (graph_prime, _, _) in downstream_changes["graphs"].items():
            hierarchy.node[graph].graph = graph_prime

    for (g1, g2), rel in rels.items():
        old_attrs = copy.deepcopy(hierarchy.relation[g1][g2])
        hierarchy.remove_relation(g1, g2)
        hierarchy.add_relation(g1, g2, rel, old_attrs)

    # update homomorphisms
    updated_homomorphisms = dict()
    updated_homomorphisms.update(upstream_changes["homomorphisms"])
    if downstream_changes is not None:
        updated_homomorphisms.update(downstream_changes["homomorphisms"])
    for (s, t), mapping in updated_homomorphisms.items():
        total = False

        if hierarchy.edge[s][t].total:
            if not is_total_homomorphism(hierarchy.node[s].graph.nodes(), mapping):
                warnings.warn(
                    "Total typing '%s->%s' became partial after rewriting!" %
                    (s, t),
                    TotalityWarning
                )
            else:
                total = True
        hierarchy.edge[s][t] = hierarchy.graph_typing_cls(
            mapping, total, hierarchy.edge[s][t].attrs
        )

    # update rules & rule homomorphisms
    for rule, new_rule in upstream_changes["rules"].items():
        hierarchy.node[rule] = hierarchy.rule_node_cls(
            new_rule, hierarchy.node[rule].attrs
        )
    for (s, t), (lhs_h, rhs_h) in upstream_changes["rule_homomorphisms"].items():
        hierarchy.edge[s][t] = hierarchy.rule_typing_cls(
            lhs_h, rhs_h,
            hierarchy.edge[s][t].attrs
        )
    return


def _update_typing(hierarchy, graph_id, rule, instance,
                   new_lhs_typing, new_rhs_typing,
                   p_g_m, r_g_prime):

    updated_homomorphisms = dict()

    for typing_graph in hierarchy.successors(graph_id):

        new_hom = copy.deepcopy(hierarchy.edge[graph_id][typing_graph].mapping)
        removed_nodes = set()
        new_nodes = dict()

        for node in rule.lhs.nodes():
            p_keys = keys_by_value(rule.p_lhs, node)
            # nodes that were removed
            if len(p_keys) == 0:
                removed_nodes.add(instance[node])
            elif len(p_keys) == 1:
                if typing_graph not in new_rhs_typing.keys() or\
                   rule.p_rhs[p_keys[0]] not in new_rhs_typing[typing_graph].keys():
                    if r_g_prime[rule.p_rhs[p_keys[0]]] in new_hom.keys():
                        removed_nodes.add(r_g_prime[rule.p_rhs[p_keys[0]]])
            # nodes were clonned
            elif len(p_keys) > 1:
                for k in p_keys:
                    if typing_graph in new_rhs_typing.keys() and\
                       rule.p_rhs[k] in new_rhs_typing[typing_graph].keys():
                        new_nodes[r_g_prime[rule.p_rhs[k]]] =\
                            new_rhs_typing[typing_graph][rule.p_rhs[k]]
                    else:
                        removed_nodes.add(r_g_prime[rule.p_rhs[k]])

        for node in rule.rhs.nodes():
            p_keys = keys_by_value(rule.p_rhs, node)

            # nodes that were added
            if len(p_keys) == 0:
                if typing_graph in new_rhs_typing.keys():
                    if node in new_rhs_typing[typing_graph].keys():
                        new_nodes[node] = new_rhs_typing[
                            typing_graph][node]

            # nodes that were merged
            elif len(p_keys) > 1:
                for k in p_keys:
                    removed_nodes.add(p_g_m[k])
                # assign new type of node
                if typing_graph in new_rhs_typing.keys():
                    if node in new_rhs_typing[typing_graph].keys():
                        new_type = new_rhs_typing[typing_graph][node]
                        new_nodes[r_g_prime[node]] = new_type

        # update homomorphisms
        for n in removed_nodes:
            if n in new_hom.keys():
                del new_hom[n]

        new_hom.update(new_nodes)

        updated_homomorphisms.update({
            (graph_id, typing_graph): new_hom
        })

    return updated_homomorphisms
