from regraph.rules import Rule

from regraph.networkx.category_utils import (compose,
                                             pushout,
                                             pullback,
                                             image_factorization)

from regraph.utils import (keys_by_value)


def get_rule_propagations(hierarchy, origin_id, rule, instance=None,
                          p_typing=None, rhs_typing=None):
    """."""
    instances = {origin_id: instance}
    rule_hierarchy = {
        "rules": {origin_id: rule},
        "rule_homomorphisms": {}
    }

    # Compute rules and their map to the original rule
    l_g_ls = {}  # LHS's of rule liftings to LHS of the original rule
    p_g_ps = {}  # interfaces of rule liftings to LHS of the original rule

    ancestors = hierarchy.get_ancestors(origin_id)
    descendants = hierarchy.get_descendants(origin_id)

    # Compute rule liftings
    for ancestor, origin_typing in ancestors:

        # Compute L_G
        l_g, l_g_g, l_g_l = pullback(
            hierarchy.get_graph(ancestor),
            rule.lhs,
            hierarchy.get_graph(origin_id),
            origin_typing,
            instance)

        # Compute canonical P_G
        canonical_p_g, p_g_l_g, p_g_p = pullback(
            l_g, rule.p, rule.lhs, l_g_l, rule.p_lhs)

        # Remove controlled things from P_G
        if ancestor in p_typing.keys():
            l_g_factorization = {
                keys_by_value(l_g_g, k)[0]: v
                for k, v in p_typing[ancestor].items()
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
                canonical_p_g.remove_node(n)
        rule_hierarchy["rules"][ancestor] =\
            Rule(p=canonical_p_g, lhs=l_g, p_lhs=p_g_l_g)

        instances[ancestor] = l_g_g
        l_g_ls[ancestor] = l_g_l
        p_g_ps[ancestor] = p_g_p

    l_l_ts = {}  # Original rule LHS to the LHS of rule projections
    p_p_ts = {}  # Original rule interface to the inter. of rule projections
    r_r_ts = {}  # Original rule RHS to the RHS of rule projections

    # Compute rule projections
    for descendant, origin_typing in descendants:
        # Compute canonical P_T
        l_t, l_l_t, l_t_t = image_factorization(
            rule.lhs, hierarchy.get_graph(descendant),
            compose(instance, origin_typing))

        # Compute canonical R_T
        r_t, l_t_r_t, r_r_t = pushout(
            rule.p, l_t, rule.rhs,
            l_l_t, rule.p_rhs)

        # Modify P_T and R_T according to the controlling
        # relation rhs_typing
        if descendant in rhs_typing.keys():
            r_t_factorization = {
                r_r_t[k]: v
                for k, v in rhs_typing[descendant].items()
            }
            added_t_nodes = set()
            for n in r_t.nodes():
                if n in r_t_factorization.keys():
                    # If corresponding R_T node is specified in
                    # the controlling relation add nodes of T
                    # that type it to P
                    t_nodes = r_t_factorization[n]
                    for t_node in t_nodes:
                        if t_node not in l_t_t.values() and\
                           t_node not in added_t_nodes:
                            new_p_node = l_t.generate_new_node_id(
                                t_node)
                            l_t.add_node(new_p_node)
                            added_t_nodes.add(t_node)
                            l_t_r_t[new_p_node] = n
                            l_t_t[new_p_node] = t_node
                        else:
                            l_t_r_t[keys_by_value(l_t_t, t_node)[0]] = n

        rule_hierarchy["rules"][descendant] =\
            Rule(lhs=l_t, p=l_t, rhs=r_t, p_rhs=l_t_r_t)

        instances[descendant] = l_t_t
        l_l_ts[descendant] = l_l_t
        p_p_ts[descendant] = {k: l_l_t[v] for k, v in rule.p_lhs.items()},
        r_r_ts[descendant] = r_r_t

    # Compute homomorphisms between rules
    for graph_id, graph_rule in rule_hierarchy["rules"]:
        if graph_id in ancestors:
            for successor in hierarchy.successors(graph_id):
                old_typing = hierarchy.get_typing(graph_id, successor)
                if successor == origin_id:
                    graph_lhs_successor_lhs = l_g_ls[graph_id]
                    graph_p_successor_p = p_g_p[graph_id]
                    rule_hierarchy["rule_homomorphisms"][
                        (graph_id, successor)] = (
                            graph_lhs_successor_lhs,
                            graph_p_successor_p,
                            graph_p_successor_p
                    )
                else:
                    l_graph_successor = compose(
                        instances[graph_id],
                        old_typing)
                    # already lifted to the successor
                    if successor in ancestors:
                        p_graph_successor = compose(
                            rule_hierarchy["rules"][graph_id].p_lhs,
                            l_graph_successor)
                        p_successor_successor = compose(
                            rule_hierarchy["rules"][successor].p_lhs,
                            instances[successor])
                        graph_lhs_successor_lhs = {}
                        for k, v in l_graph_successor.items():
                            l_node_g = l_g_ls[graph_id][k]
                            for vv in keys_by_value(instances[successor], v):
                                l_node_s = l_g_ls[successor][vv]
                                if (l_node_s == l_node_g):
                                    graph_lhs_successor_lhs[k] = vv
                                    break

                        graph_p_successor_p = {}
                        for k, v in p_graph_successor.items():
                            p_node_g = p_g_ps[graph_id][k]
                            for vv in keys_by_value(p_successor_successor, v):
                                p_node_s = p_g_ps[successor][vv]
                                if (p_node_s == p_node_g):
                                    graph_p_successor_p[p_node_g] = p_node_s
                                    break

                        rule_hierarchy["rule_homomorphisms"][
                            (graph_id, successor)] = (
                                graph_lhs_successor_lhs,
                                graph_p_successor_p,
                                graph_p_successor_p
                        )
                    elif successor in descendants:
                        rule_hierarchy["rule_homomorphisms"][(graph_id, successor)] = (
                            compose(l_g_ls[graph_id],
                                    l_l_ts[successor]),
                            compose(p_g_ps[graph_id],
                                    p_p_ts[successor]),
                            compose(
                                compose(p_g_ps[graph_id],
                                        rule.p_rhs),
                                r_r_ts[successor])
                        )
                    # didn't touch the successor or projected to it
                    else:
                        pass

        if graph_id in descendants:
            for predecessor in hierarchy.predecessors(graph_id):
                old_typing = hierarchy.get_typing(predecessor, graph_id)
                if predecessor == origin_id:
                    predecessor_l_graph_l = l_l_ts[graph_id]
                    predecessor_p_graph_p = p_p_t[graph_id]
                    predecessor_rhs_graph_rhs = r_r_ts[graph_id]
                    rule_hierarchy["rule_homomorphisms"][
                        (predecessor, graph_id)] = (
                            predecessor_l_graph_l,
                            predecessor_p_graph_p,
                            predecessor_rhs_graph_rhs
                    )
                else:
                    # already projected to the predecessor
                    if predecessor in descendants:
                        l_pred_graph = compose(
                            instances[predecessor],
                            old_typing)
                        predecessor_l_graph_l = {}
                        for k, v in instances[
                                predecessor].items():
                            predecessor_l_graph_l[k] = keys_by_value(
                                instances[graph_id],
                                l_pred_graph[k])[0]
                        predecessor_rhs_graph_rhs = {}
                        for r_node, r_pred_node in r_r_ts[
                                predecessor].items():
                            p_pred_nodes = keys_by_value(
                                rule_hierarchy["rules"][predecessor].p_rhs,
                                r_pred_node)
                            for v in p_pred_nodes:
                                p_graph_node = predecessor_l_graph_l[v]
                                r_graph_node = rule_hierarchy["rules"][graph_id][
                                    "rule"].p_rhs[p_graph_node]
                            if len(p_pred_nodes) == 0:
                                r_graph_node = r_r_ts[graph_id][r_node]
                            predecessor_rhs_graph_rhs[r_pred_node] = r_graph_node
                        rule_hierarchy["rule_homomorphisms"][
                            (predecessor, graph_id)] = (
                                predecessor_l_graph_l,
                                predecessor_l_graph_l,
                                predecessor_rhs_graph_rhs
                        )
                    # didn't touch the predecessor or lifter to it
                    else:
                        pass

    return rule_hierarchy, instances


def refine_rule_hierarchy(hierarchy, rule_hierarchy, instances):
    """."""
    new_lhs_instances = {}

    new_rules = {}
    new_rule_homomorphisms = {}

    for graph, rule in rule_hierarchy["rules"].items():
        # refine rule
        new_lhs_instance = rule.refine(
            hierarchy.get_graph(graph), instances[graph])
        new_lhs_instances[graph] = new_lhs_instance

    # Update rule homomorphisms
    for (source, target), (lhs_h, p_h, rhs_h) in rule_hierarchy[
            "rule_homomorphisms"].items():
        typing = hierarchy.get_typing(source, target)
        source_rule = rule_hierarchy["rules"][source]
        target_rule = rule_hierarchy["rules"][target]
        for node in source_rule.lhs.nodes():
            if node not in lhs_h.keys():
                source_node = new_lhs_instances[source][node]
                target_node = typing[source_node]
                target_lhs_node = keys_by_value(
                    new_lhs_instances[target], target_node)[0]
                lhs_h[node] = target_lhs_node

                if node in source_rule.p_lhs.values():
                    source_p_node = keys_by_value(
                        source_rule.p_lhs, node)[0]
                    target_p_node = keys_by_value(
                        target_rule.p_lhs, node)[0]
                    p_h[source_p_node] = target_p_node

                    source_rhs_node = source_rule.p_rhs[source_p_node]
                    target_rhs_node = target_rule.p_rhs[target_p_node]
                    rhs_h[source_rhs_node] = target_rhs_node

    if len(rule_hierarchy["rules"]) == 0:
        for graph in hierarchy.graphs():
            rule_hierarchy["rules"][graph] = Rule.identity_rule()
            new_lhs_instances[graph] = dict()
        for (s, t) in hierarchy.typings():
            rule_hierarchy["rule_homomorphisms"][(s, t)] = (
                dict(), dict(), dict())
    else:
        for graph, rule in rule_hierarchy["rules"].items():
            # add identity rules where needed
            # to preserve the info on p/rhs_typing
            # add ancestors that are not included in rule hierarchy
            for ancestor, typing in hierarchy.get_ancestors(graph).items():
                if ancestor not in rule_hierarchy["rules"] and\
                   ancestor not in new_rules:
                    # Find a typing of ancestor by the graph
                    l_pred, l_pred_pred, l_pred_l_graph = pullback(
                        hierarchy.get_graph(ancestor), rule.lhs,
                        hierarchy.get_graph(graph), typing,
                        new_lhs_instances[graph])
                    new_rules[ancestor] = Rule(p=l_pred, lhs=l_pred)
                    new_lhs_instances[ancestor] = l_pred_pred
                    r_pred_r_graph = {
                        v: rule.p_rhs[k]
                        for k, v in l_pred_l_graph.items()
                    }
                    for successor in hierarchy.successors(ancestor):
                        if successor in rule_hierarchy["rules"]:
                            if successor == graph:
                                new_rule_homomorphisms[
                                    (ancestor, graph)] = (
                                        l_pred_l_graph, l_pred_l_graph,
                                        r_pred_r_graph
                                )
                            else:
                                path = hierarchy.shortest_path(graph, successor)
                                lhs_h, p_h, rhs_h = rule_hierarchy[
                                    "rule_homomorphisms"][
                                        (path[0], path[1])]
                                for i in range(2, len(path)):
                                    new_lhs_h, new_p_h, new_rhs_h =\
                                        rule_hierarchy[
                                            "rule_homomorphisms"][
                                                (path[i - 1], path[i])]
                                    lhs_h = compose(lhs_h, new_lhs_h)
                                    p_h = compose(p_h, new_p_h)
                                    rhs_h = compose(rhs_h, new_rhs_h)

                                new_rule_homomorphisms[
                                    (ancestor, successor)] = (
                                        compose(l_pred_l_graph, lhs_h),
                                        compose(l_pred_l_graph, p_h),
                                        compose(r_pred_r_graph, rhs_h)
                                )
                        if successor in new_rules:
                            lhs_h = {
                                k: keys_by_value(
                                    new_lhs_instances[successor],
                                    hierarchy.get_typing(
                                        ancestor, successor)[v])[0]
                                for k, v in new_lhs_instances[
                                    ancestor].items()
                            }
                            new_rule_homomorphisms[
                                (ancestor, successor)] = (
                                    lhs_h, lhs_h, lhs_h
                            )
                    for predecessor in hierarchy.predecessors(ancestor):
                        if predecessor in rule_hierarchy["rules"] or\
                           predecessor in new_rules:
                            lhs_h = {
                                k: keys_by_value(
                                    new_lhs_instances[ancestor],
                                    hierarchy.get_typing(
                                        predecessor, ancestor)[v])[0]
                                for k, v in new_lhs_instances[
                                    predecessor].items()
                            }
                            new_rule_homomorphisms[
                                (predecessor, ancestor)] = (
                                    lhs_h, lhs_h, lhs_h
                            )

            for descendant, typing in hierarchy.get_descendants(graph).items():
                if descendant not in rule_hierarchy["rules"] and\
                   descendant not in new_rules:
                    l_suc, l_graph_l_suc, l_suc_suc = image_factorization(
                        rule.lhs, hierarchy.get_graph(descendant),
                        compose(
                            new_lhs_instances[graph],
                            typing))
                    new_rules[descendant] = Rule(p=l_suc, lhs=l_suc)
                    new_lhs_instances[descendant] = l_suc_suc
                    p_graph_p_suc = {
                        k: l_graph_l_suc[v]
                        for k, v in rule.p_lhs.items()
                    }
                    for predecessor in hierarchy.predecessors(descendant):
                        if predecessor in rule_hierarchy["rules"]:
                            if predecessor == graph:
                                new_rule_homomorphisms[
                                    (predecessor, descendant)] = (
                                        l_graph_l_suc,
                                        p_graph_p_suc,
                                        p_graph_p_suc
                                )
                            else:
                                path = hierarchy.shortest_path(
                                    predecessor, graph)
                                lhs_h, p_h, rhs_h = rule_hierarchy[
                                    "rule_homomorphisms"][
                                        (path[0], path[1])]
                                for i in range(2, len(path)):
                                    new_lhs_h, new_p_h, new_rhs_h =\
                                        rule_hierarchy[
                                            "rule_homomorphisms"][
                                                (path[i - 1], path[i])]
                                    lhs_h = compose(lhs_h, new_lhs_h)
                                    p_h = compose(p_h, new_p_h)
                                    rhs_h = compose(rhs_h, new_rhs_h)
                                new_rule_homomorphisms[
                                    (predecessor, descendant)] = (
                                        compose(lhs_h, l_graph_l_suc),
                                        compose(p_h, p_graph_p_suc),
                                        compose(rhs_h, p_graph_p_suc)
                                )
                        if predecessor in new_rules:
                            lhs_h = {
                                k: keys_by_value(
                                    new_lhs_instances[descendant],
                                    hierarchy.get_typing(
                                        predecessor, descendant)[v])[0]
                                for k, v in new_lhs_instances[
                                    predecessor].items()
                            }
                            new_rule_homomorphisms[
                                (predecessor, descendant)] = (
                                lhs_h, lhs_h, lhs_h
                            )

                    for successor in hierarchy.successors(descendant):
                        if successor in rule_hierarchy["rules"] or\
                           successor in new_rules:
                            lhs_h = {
                                k: keys_by_value(
                                    new_lhs_instances[successor],
                                    hierarchy.get_typing(
                                        descendant, successor)[v])[0]
                                for k, v in new_lhs_instances[
                                    descendant].items()
                            }
                            new_rule_homomorphisms[
                                (descendant, successor)] = (
                                    lhs_h, lhs_h, lhs_h
                            )

    rule_hierarchy["rules"].update(new_rules)
    rule_hierarchy["rule_homomorphisms"].update(
        new_rule_homomorphisms)

    return new_lhs_instances
