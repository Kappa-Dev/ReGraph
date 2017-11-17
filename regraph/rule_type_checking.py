"""A collection of (internal usage) utils for rule type checking."""
import networkx as nx
from networkx.exception import NetworkXNoPath

from regraph.category_op import check_homomorphism
from regraph.exceptions import RewritingError, ReGraphError
from regraph.utils import keys_by_value, format_typing


def _new_check_rhs_sideffects(hierarchy, graph_id, rule, instance, typing_dict):
    for node in rule.rhs.nodes():
        p_keys = keys_by_value(rule.p_rhs, node)
        g_keys = [instance[rule.p_lhs[p]] for p in p_keys]
        if len(p_keys) > 1:
            if hierarchy.directed:
                succs = set()
                preds = set()
                for g in g_keys:
                    succs.update([
                        s for s in hierarchy.node[graph_id].graph.successors(g)
                        if s not in g_keys
                    ])
                    preds.update([
                        s for s in hierarchy.node[graph_id].graph.predecessors(g)
                        if s not in g_keys
                    ])


def _check_rhs_sideffects(hierarchy, graph_id, rule, instance, typing_dict):
    for typing_graph, mapping in typing_dict.items():

        # check edges out of the g-(im(g->lhs)) do not violate typing
        for node in rule.rhs.nodes():
            p_keys = keys_by_value(rule.p_rhs, node)
            g_keys = [instance[rule.p_lhs[p]] for p in p_keys]
            if len(p_keys) > 1:
                if hierarchy.directed:
                    succs = set()
                    preds = set()
                    for p in p_keys:
                        g = instance[rule.p_lhs[p]]
                        succs.update([
                            s for s in hierarchy.node[graph_id].graph.successors(g)
                            if s not in g_keys
                        ])
                        preds.update([
                            s for s in hierarchy.node[graph_id].graph.predecessors(g)
                            if s not in g_keys
                        ])
                    for s in succs:
                        path = nx.shortest_path(
                            hierarchy, graph_id, typing_graph)
                        graph_mapping = hierarchy.compose_path_typing(path)
                        if s in graph_mapping.keys() and node in mapping:
                            if (mapping[node], graph_mapping[s]) not in\
                               hierarchy.node[typing_graph].graph.edges():
                                raise RewritingError(
                                    "Merge produces a forbidden edge "
                                    "between nodes of types `%s` and `%s`!" %
                                    (mapping[node], graph_mapping[s])
                                )
                    for p in preds:
                        path = nx.shortest_path(
                            hierarchy, graph_id, typing_graph)
                        graph_mapping = hierarchy.compose_path_typing(path)
                        if p in graph_mapping.keys() and node in mapping:
                            if (graph_mapping[p], mapping[node]) not in\
                               hierarchy.node[typing_graph].graph.edges():
                                raise RewritingError(
                                    "Merge produces a forbidden edge "
                                    "between nodes of types `%s` and `%s`!" %
                                    (graph_mapping[p], mapping[node])
                                )

                else:
                    neighbours = set()
                    for p in p_keys:
                        g_node = instance[rule.p_lhs[p]]
                        neighbours.update(
                            hierarchy.node[graph_id].graph.neighbors(g_node)
                        )
                    for n in neighbours:
                        graph_mapping = hierarchy.edge[
                            graph_id][typing_graph].mapping
                        if s in graph_mapping.keys():
                            if (mapping[node], graph_mapping[s]) not in\
                               hierarchy.node[typing_graph].graph.edges():
                                raise RewritingError(
                                    "Merge produces a forbidden edge "
                                    "between nodes of types `%s` and `%s`!" %
                                    (mapping[node], graph_mapping[s])
                                )
    return


def _autocomplete_typing(hierarchy, graph_id, instance,
                         lhs_typing, rhs_typing, p_lhs, p_rhs):
    if len(hierarchy.successors(graph_id)) > 0:
        if lhs_typing is None:
            new_lhs_typing = dict()
        else:
            new_lhs_typing = format_typing(lhs_typing)
        if rhs_typing is None:
            new_rhs_typing = dict()
        else:
            new_rhs_typing = format_typing(rhs_typing)

        for typing_graph in hierarchy.successors(graph_id):
            typing = hierarchy.edge[graph_id][typing_graph].mapping
            # Autocomplete lhs and rhs typings
            # by immediate successors induced by an instance
            for (source, target) in instance.items():
                if typing_graph not in new_lhs_typing.keys():
                    new_lhs_typing[typing_graph] = dict()
                if source not in new_lhs_typing[typing_graph].keys():
                    if target in typing.keys():
                        new_lhs_typing[typing_graph][source] = typing[target]
            for (p_node, l_node) in p_lhs.items():
                if l_node in new_lhs_typing[typing_graph].keys():
                    if typing_graph not in new_rhs_typing.keys():
                        new_rhs_typing[typing_graph] = dict()
                    if p_rhs[p_node] not in new_rhs_typing[typing_graph].keys():
                        new_rhs_typing[typing_graph][p_rhs[p_node]] =\
                            new_lhs_typing[typing_graph][l_node]

        # Second step of autocompletion of rhs typing
        for typing_graph, typing in new_rhs_typing.items():
            ancestors = hierarchy.get_ancestors(typing_graph)
            for ancestor, ancestor_typing in ancestors.items():
                if ancestor in new_rhs_typing.keys():
                    dif = set(typing.keys()) -\
                        set(new_rhs_typing[ancestor].keys())
                    for node in dif:
                        new_rhs_typing[ancestor][node] =\
                            ancestor_typing[new_rhs_typing[typing_graph][node]]

        return (new_lhs_typing, new_rhs_typing)
    else:
        return (None, None)


def _check_lhs_rhs_consistency(hierarchy, graph_id, rule, instance,
                               lhs_typing, rhs_typing):
    for typing_graph, typing in lhs_typing.items():
        typing_graph_ancestors = hierarchy.get_ancestors(typing_graph)
        for ancestor, ancestor_typing in typing_graph_ancestors.items():
            if ancestor in rhs_typing.keys():
                for p_node in rule.p.nodes():
                    if rule.p_rhs[p_node] in rhs_typing[ancestor] and\
                       rhs_typing[ancestor][rule.p_rhs[p_node]] !=\
                       ancestor_typing[typing[rule.p_lhs[p_node]]]:
                        raise RewritingError(
                            "Inconsistent typing of the rule: "
                            "node '%s' from the preserved part is typed "
                            "by a graph '%s' as "
                            "'%s' from the lhs and as a '%s' from the rhs." %
                            (p_node, ancestor,
                             rhs_typing[ancestor][rule.p_rhs[p_node]],
                             ancestor_typing[typing[rule.p_lhs[p_node]]])
                        )


def _check_self_consistency(hierarchy, typing):
    for typing_graph, mapping in typing.items():
        ancestors = hierarchy.get_ancestors(typing_graph)
        for anc, anc_typing in ancestors.items():
            if anc in typing.keys():
                for key, value in mapping.items():
                    if key in typing[anc].keys() and\
                       anc_typing[value] != typing[anc][key]:
                        raise ReGraphError("typing is self inconsistent!")


def _check_totality(hierarchy, graph_id, rule, instance,
                    lhs_typing, rhs_typing):
    """"Check that everything is typed at the end of the rewriting."""
    for node in rule.rhs.nodes():
        p_nodes = keys_by_value(rule.p_rhs, node)
        for typing_graph in hierarchy.successors(graph_id):
            typing = hierarchy.edge[graph_id][typing_graph].mapping
            # Totality can be broken in two cases
            if len(p_nodes) > 1:
                # node will be merged
                all_untyped = True
                for p_node in p_nodes:
                    if instance[rule.p_lhs[p_node]] in typing.keys():
                        all_untyped = False
                        break
                if all_untyped:
                    continue

            if typing_graph in rhs_typing.keys() and\
               node in rhs_typing[typing_graph].keys():
                continue
            else:
                visited_successors = set()
                resolved_successors = set()
                successors_to_visit = set(
                    hierarchy.successors(typing_graph)
                )
                while len(successors_to_visit) > 0:
                    for suc in successors_to_visit:
                        visited_successors.add(suc)
                        if suc in rhs_typing.keys() and\
                           node in rhs_typing[suc].keys():
                            resolved_successors.add(suc)

                    new_successors_to_visit = set()
                    for suc in successors_to_visit:
                        new_successors_to_visit.update(
                            [s for s in hierarchy.successors(suc)
                             if s not in visited_successors]
                        )
                    successors_to_visit = new_successors_to_visit

                if len(visited_successors - resolved_successors) > 0:
                    raise RewritingError(
                        "Rewriting parameter `total` is set to True, "
                        "typing of the node `%s` "
                        "in rhs is required (typing by the following "
                        "graphs stays unresolved: %s)!" %
                        (node,
                         ", ".join(visited_successors - resolved_successors))
                    )


def _check_instance(hierarchy, graph_id, pattern, instance, pattern_typing):
    check_homomorphism(
        pattern,
        hierarchy.node[graph_id].graph,
        instance,
        total=True
    )
    # check that instance typing and lhs typing coincide
    for node in pattern.nodes():
        if pattern_typing:
            for typing_graph, typing in pattern_typing.items():
                try:
                    instance_typing = hierarchy.compose_path_typing(
                        nx.shortest_path(hierarchy, graph_id, typing_graph)
                    )
                    if node in pattern_typing.keys() and\
                       instance[node] in instance_typing.keys():
                        if typing[node] != instance_typing[instance[node]]:
                            raise RewritingError(
                                "Typing of the instance of LHS does not " +
                                " coincide with typing of LHS!"
                            )
                except NetworkXNoPath:
                    raise ReGraphError(
                        "Graph '%s' is not typed by '%s' specified "
                        "as a typing graph of the lhs of the rule." %
                        (graph_id, typing_graph)
                    )
    return
