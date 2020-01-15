"""."""
from regraph.exceptions import (InvalidHomomorphism,
                                RewritingError)

from regraph.networkx.category_utils import (check_homomorphism,
                                             is_monic,)
from regraph.utils import (keys_by_value,
                           normalize_typing_relation)


def check_rule_instance_typing(hierarchy, origin_id, rule, instance,
                               p_typing, rhs_typing, strict):
    """."""
    if instance is None:
        instance = {
            n: n for n in rule.lhs.nodes()
        }

    if p_typing is None:
        p_typing = dict()
    else:
        p_typing = normalize_typing_relation(p_typing)
    if rhs_typing is None:
        rhs_typing = dict()
    else:
        rhs_typing = normalize_typing_relation(rhs_typing)

    # Check that the instance is valid
    try:
        check_homomorphism(
            rule.lhs,
            hierarchy.get_graph(origin_id),
            instance,
            total=True
        )
    except InvalidHomomorphism as e:
        raise RewritingError(
            "Homomorphism from the pattern to the instance subgraph "
            "is not valid, got: '{}'".format(e))

    # Check that the instance is a mono
    if not is_monic(instance):
        raise RewritingError(
            "Homomorphism from the pattern to the instance subgraph "
            "is not injective")

    # Check p_typing does not retype nodes
    for graph_id, typing in p_typing.items():
        graph_to_origin = hierarchy.get_typing(graph_id, origin_id)
        for k, v in typing.items():
            for vv in v:
                if graph_to_origin[k] != instance[rule.p_lhs[vv]]:
                    raise RewritingError(
                        "The specified typing of '{}' ".format(graph_id) +
                        "by the interface is not valid: "
                        "node '{}' is typed by '{}' ".format(
                            k, graph_to_origin[k]) +
                        "in the origin of rewriting, while the interface "
                        "node '{}' is typed by '{}'.".format(
                            vv, instance[rule.p_lhs[vv]]))

    # Check composability of p_typing
    for graph_id, typing in p_typing.items():
        predecessors = hierarchy.predecessors(graph_id)
        for pred in predecessors:
            if pred not in p_typing:
                # check that the typing of 'graph_id' is canonical
                canonical = False
                for graph_n, p_nodes in typing.items():
                    if len(p_nodes) > 0:
                        lhs_n = rule.p_lhs[list(p_nodes)[0]]
                        canonical_clones = set(keys_by_value(rule.p_lhs, lhs_n))
                        if p_nodes == canonical_clones:
                            canonical = False
                if not canonical:
                    raise RewritingError(
                        "Typing of '{}' by the interface ".format(
                            graph_id) +
                        "is not composable with the "
                        "typig of '{}': ".format(pred) +
                        "propagation to '{}' ".format(pred) +
                        "is canonical and produces instances for {}, ".format(
                            canonical_clones) +
                        "while propagation to '{}' ".format(
                            graph_id) +
                        "produces only for '{}' ".format(
                            p_nodes)
                    )
        successors = hierarchy.successors(graph_id)
        for suc in successors:
            suc_typing = hierarchy.get_typing(graph_id, suc)
            # check p_typing for suc is composable
            for graph_n, p_nodes in typing.items():
                suc_n = suc_typing[graph_n]
                if suc in p_typing and suc_n in p_typing[suc]:
                    suc_p_nodes = p_typing[suc][suc_n]
                    if not p_nodes.issubset(suc_p_nodes):
                        raise RewritingError(
                            "Typing of '{}' by the interface ".format(
                                graph_id) +
                            "is not composable with the "
                            "typig of '{}': ".format(suc) +
                            "propagation to the node "
                            "'{}' of '{}' ".format(graph_n, graph_id) +
                            "will produce instances for {} ".format(
                                p_nodes) +
                            "while propagation to '{}' ".format(
                                suc_n) +
                            "typing it produces only {} ".format(
                                suc_p_nodes)
                        )
                else:
                    # ok, because suc_n is canonically cloned
                    pass

    # Autocomplete and check rhs_typing
    new_rhs_typing = {}
    for graph_id, typing in rhs_typing.items():
        for descendant, descendant_typing in hierarchy.get_descendants(
                graph_id).items():
            if descendant not in rhs_typing:
                # autocomplete descendant typing in the new rhs typing
                new_rhs_typing[descendant] = {
                    rhs_n: {
                        descendant_typing[graph_n]
                        for graph_n in graph_ns
                    }
                    for rhs_n, graph_ns in typing.items()
                }
            else:
                # autocomplete descendant typing with missing rhs nodes
                # and check that already specified types for descendant
                # are composable with the typing for 'graph_id'
                descendant_rhs_typing = rhs_typing[descendant]
                for rhs_n, graph_ns in typing.items():
                    if rhs_n in descendant_rhs_typing:
                        descendant_ns = descendant_rhs_typing[rhs_n]
                        for graph_n in graph_ns:
                            if descendant_typing[graph_n] not in descendant_ns:
                                raise RewritingError(
                                    "Typing of the RHS "
                                    "by '{}' is not composable ".format(
                                        graph_id) +
                                    "with its typing by '{}': ".format(
                                        descendant) +
                                    "node '{}' is typed by '{}' ".format(
                                        rhs_n, graph_n) +
                                    "in '{}' that is not typed by ".format(
                                        graph_id) +
                                    "either of {} from '{}'".format(
                                        descendant_ns, descendant)
                                )

                    else:
                        new_rhs_typing[descendant] = rhs_typing[descendant]
                        new_rhs_typing[descendant][rhs_n] = {
                            descendant_typing[graph_n]
                            for graph_n in graph_ns
                        }

    for g, t in new_rhs_typing.items():
        rhs_typing[g] = t

    # Check rhs_typing does not retype nodes
    for graph_id, typing in rhs_typing.items():
        origin_to_graph = hierarchy.get_typing(origin_id, graph_id)
        for k, v in typing.items():
            p_nodes = keys_by_value(rule.p_rhs, k)
            if len(p_nodes) > 0:
                graph_nodes = set([
                    origin_to_graph[instance[rule.p_lhs[p_node]]]
                    for p_node in p_nodes])
                if graph_nodes != v:
                    raise RewritingError(
                        "The specified typing of the RHS "
                        "by the graph '{}' ".format(graph_id) +
                        "is not valid: "
                        "node '{}' is a typed by {} ".format(
                            k, graph_nodes) +
                        "in the origin of rewriting, while it is "
                        "typed by {} in the typing.".format(v))

    # If rewriting is strict, check rhs typing types all new nodes
    if strict is True:
        if len(rule.added_nodes()) > 0:
            descendants = hierarchy.get_descendants(origin_id).keys()
            for desc in descendants:
                if desc not in rhs_typing:
                    raise RewritingError(
                        "Rewriting is strict (no propagation of types is "
                        "allowed), typing of the added nodes '{}' ".format(
                            rule.added_nodes()) +
                        "by '{}' is required".format(desc))
                else:
                    for rhs_n in rule.added_nodes():
                        if rhs_n not in rhs_typing[desc] or\
                                len(rhs_typing[desc][rhs_n]) != 1:
                            raise RewritingError(
                                "Rewriting is strict (no propagation of "
                                "types is allowed), typing of the added "
                                "nodee '{}' by '{}' is required".format(
                                    rhs_n, desc))

    return instance, p_typing, rhs_typing
