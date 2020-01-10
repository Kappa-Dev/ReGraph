"""A collection of (internal usage) utils for rule type checking."""
import networkx as nx
from networkx.exception import NetworkXNoPath

from regraph.exceptions import (ReGraphError,
                                RewritingError,
                                HierarchyError,
                                InvalidHomomorphism)
from regraph.utils import (keys_by_value,
                           format_typing,
                           normalize_typing_relation)
from regraph.networkx.category_utils import (check_homomorphism,
                                             compose,
                                             is_monic)


def _check_rule_typing(hierarchy, rule_id, graph_id, lhs_mapping, rhs_mapping):
    all_paths = dict(nx.all_pairs_shortest_path(hierarchy))

    paths_from_target = {}
    for s in hierarchy.nodes():
        if s == graph_id:
            for key in all_paths[graph_id].keys():
                paths_from_target[key] = all_paths[graph_id][key]

    for t in paths_from_target.keys():
        if t != graph_id:
            new_lhs_h = compose(
                lhs_mapping,
                hierarchy.compose_path_typing(paths_from_target[t]))
            new_rhs_h = compose(
                rhs_mapping,
                hierarchy.compose_path_typing(paths_from_target[t]))
            try:
                # find homomorphisms from s to t via other paths
                s_t_paths = nx.all_shortest_paths(hierarchy, rule_id, t)
                for path in s_t_paths:
                    lhs_h, rhs_h = hierarchy.compose_path_typing(path)
                    if lhs_h != new_lhs_h:
                        raise HierarchyError(
                            "Invalid lhs typing: homomorphism does not "
                            "commute with an existing "
                            "path from '%s' to '%s'!" % (s, t)
                        )
                    if rhs_h != new_rhs_h:
                        raise HierarchyError(
                            "Invalid rhs typing: homomorphism does not "
                            "commute with an existing " +
                            "path from '%s' to '%s'!" % (s, t)
                        )
            except(nx.NetworkXNoPath):
                pass
    return


def _check_consistency(hierarchy, source, target, mapping=None):
    all_paths = dict(nx.all_pairs_shortest_path(hierarchy))

    paths_to_source = {}
    paths_from_target = {}
    for s in hierarchy.nodes():
        if source in all_paths[s].keys():
            paths_to_source[s] = all_paths[s][source]
        if s == target:
            for key in all_paths[target].keys():
                paths_from_target[key] = all_paths[target][key]

    for s in paths_to_source.keys():
        if hierarchy._path_from_rule(paths_to_source[s]):
            for t in paths_from_target.keys():
                # find homomorphism from s to t via new path
                if s == source:
                    raise HierarchyError(
                        "Found a rule typing some node in the hierarchy!"
                    )
                new_lhs_h, new_rhs_h = hierarchy.compose_path_typing(
                    paths_to_source[s])
                new_lhs_h = compose(new_lhs_h, mapping)
                new_rhs_h = compose(new_rhs_h, mapping)

                if t != target:
                    new_lhs_h = compose(
                        new_lhs_h,
                        hierarchy.compose_path_typing(paths_from_target[t])
                    )
                    new_rhs_h = compose(
                        new_rhs_h,
                        hierarchy.compose_path_typing(paths_from_target[t]),
                    )
                try:
                    # find homomorphisms from s to t via other paths
                    s_t_paths = nx.all_shortest_paths(hierarchy, s, t)
                    for path in s_t_paths:
                        lhs_h, rhs_h = hierarchy.compose_path_typing(path)
                        if lhs_h != new_lhs_h:
                            raise HierarchyError(
                                "Invalid lhs typing: homomorphism does "
                                "not commute with an existing " +
                                "path from '%s' to '%s'!" % (s, t)
                            )
                        if rhs_h != new_rhs_h:
                            raise HierarchyError(
                                "Invalid rhs typing: homomorphism does "
                                "not commute with an existing " +
                                "path from '%s' to '%s'!" % (s, t)
                            )
                except(nx.NetworkXNoPath):
                    pass
        else:
            for t in paths_from_target.keys():
                # find homomorphism from s to t via new path
                if s != source:
                    new_homomorphism = hierarchy.compose_path_typing(
                        paths_to_source[s])
                else:
                    new_homomorphism = dict([(key, key)
                                             for key, _ in mapping.items()])
                new_homomorphism = compose(
                    new_homomorphism, mapping)
                if t != target:
                    new_homomorphism = compose(
                        new_homomorphism,
                        hierarchy.compose_path_typing(paths_from_target[t])
                    )

                # find homomorphisms from s to t via other paths
                s_t_paths = nx.all_shortest_paths(hierarchy, s, t)
                try:
                    # check only the first path
                    for path in s_t_paths:
                        path_homomorphism = hierarchy.compose_path_typing(path)
                        if path_homomorphism != new_homomorphism:
                            raise HierarchyError(
                                "Homomorphism does not commute with an " +
                                "existing path from '%s' to '%s'!" % (s, t)
                            )
                except(nx.NetworkXNoPath):
                        pass


def _autocomplete_typing(hierarchy, graph_id, instance,
                         lhs_typing, p_typing, rhs_typing_rel, p_lhs, p_rhs):
    if lhs_typing is None:
        new_lhs_typing = dict()
    else:
        new_lhs_typing = format_typing(lhs_typing)
    if p_typing is None:
        new_p_typing = dict()
    else:
        new_p_typing = normalize_typing_relation(p_typing)
    if rhs_typing_rel is None:
        new_rhs_typing_rel = dict()
    else:
        new_rhs_typing_rel = normalize_typing_relation(rhs_typing_rel)
    successors = list(hierarchy.successors(graph_id))
    if len(successors) > 0:
        ancestors = hierarchy.get_descendants(graph_id)
        for anc, anc_typing in ancestors.items():
            if anc not in new_rhs_typing_rel.keys():
                new_rhs_typing_rel[anc] = dict()

        merged_nodes = set()
        for r_node in p_rhs.values():
            p_nodes = keys_by_value(p_rhs, r_node)
            if len(p_nodes) > 1:
                merged_nodes.add(r_node)

        for typing_graph in hierarchy.successors(graph_id):
            typing = hierarchy.typing[graph_id][typing_graph]
            # Autocomplete lhs and rhs typings
            # by immediate successors induced by an instance
            if typing_graph not in new_lhs_typing.keys():
                new_lhs_typing[typing_graph] = dict()
            for (source, target) in instance.items():
                if source not in new_lhs_typing[typing_graph].keys():
                    if target in typing.keys():
                        new_lhs_typing[typing_graph][source] = typing[target]

            for (p_node, l_node) in p_lhs.items():
                if l_node in new_lhs_typing[typing_graph].keys():
                    if p_rhs[p_node] not in new_rhs_typing_rel[typing_graph].keys():
                        new_rhs_typing_rel[typing_graph][p_rhs[p_node]] = set()

                    new_rhs_typing_rel[typing_graph][p_rhs[p_node]].add(
                        new_lhs_typing[typing_graph][l_node])

        # Second step of autocompletion of rhs typing
        for graph, typing in new_rhs_typing_rel.items():
            ancestors = hierarchy.get_descendants(graph)
            for ancestor, ancestor_typing in ancestors.items():
                dif = set(typing.keys()) -\
                    set(new_rhs_typing_rel[ancestor].keys())
                for node in dif:
                    type_set = set()
                    for el in new_rhs_typing_rel[graph][node]:
                        type_set.add(ancestor_typing[el])
                    new_rhs_typing_rel[ancestor][node] = type_set
    return (new_lhs_typing, new_p_typing, new_rhs_typing_rel)


def _check_self_consistency(hierarchy, typing, strict=True):
    for typing_graph, mapping in typing.items():
        ancestors = hierarchy.get_descendants(typing_graph)
        for anc, anc_typing in ancestors.items():
            if anc in typing.keys():
                for key, value in mapping.items():
                    if key in typing[anc].keys():
                        if type(value) == str:
                            if value in anc_typing.keys() and\
                               anc_typing[value] != typing[anc][key]:
                                raise RewritingError(
                                    "Node '%s' is typed as "
                                    "'%s' and '%s' in the graph '%s'" %
                                    (key, anc_typing[value], typing[anc][key],
                                        anc))
                        else:
                            try:
                                for val in value:
                                    if val in anc_typing.keys() and\
                                       anc_typing[val] not in typing[anc][key]:
                                        raise RewritingError(
                                            "Node '%s' is typed as "
                                            "'%s' and '%s' in the graph '%s'" %
                                            (key, anc_typing[val],
                                             ", ".join(typing[anc][key]),
                                             anc))
                            except TypeError:
                                if value in anc_typing.keys() and\
                                   anc_typing[value] != typing[anc][key]:
                                    raise RewritingError(
                                        "Node '%s' is typed as "
                                        "'%s' and '%s' in the graph '%s'" %
                                        (key, anc_typing[value],
                                         ", ".join(typing[anc][key]),
                                         anc))


def _check_lhs_p_consistency(hierarchy, graph_id, rule, instance,
                             lhs_typing, p_typing):
    """ Check consistency of typing of the lhs and the p of the rule."""
    for typed_graph, typing in p_typing.items():
        origin_typing = hierarchy.get_typing(typed_graph, graph_id)
        for k, v in typing.items():
            for vv in v:
                if instance[rule.p_lhs[vv]] != origin_typing[k]:
                    raise RewritingError(
                        "Inconsistent typing of the rule: the node "
                        "'{}' of '{}' typed by ".format(
                            k, typed_graph) +
                        "'{}' in '{}' ".format(
                            origin_typing[k], graph_id) +
                        "is re-typed by the node '{}' through the preserved part".format(
                            instance[rule.p_lhs[vv]]))

def _check_lhs_rhs_consistency(hierarchy, graph_id, rule, instance,
                               lhs_typing, rhs_typing, strict=True):
    """Check consistency of typing of the lhs and the rhs of the rule."""
    for typing_graph, typing in lhs_typing.items():
        for p_node in rule.p.nodes():
            if typing_graph in rhs_typing.keys():
                if strict is True and\
                   rule.p_rhs[p_node] in rhs_typing[typing_graph].keys() and\
                   len(rhs_typing[typing_graph][rule.p_rhs[p_node]]) > 1:
                    raise RewritingError(
                        "Inconsistent typing of the rule: node "
                        "'%s' from the preserved part is typed "
                        "by a graph '%s' as '%s' from the lhs and "
                        "as a '%s' from the rhs." %
                        (p_node, typing_graph,
                         typing[rule.p_lhs[p_node]],
                         ", ".join(
                             rhs_typing[typing_graph][rule.p_rhs[p_node]])))
            typing_graph_ancestors = hierarchy.get_descendants(typing_graph)
            for anc, anc_typing in typing_graph_ancestors.items():
                if anc in rhs_typing.keys():
                    if rule.p_rhs[p_node] in rhs_typing[anc]:
                        if strict is True:
                            if len(rhs_typing[anc][rule.p_rhs[p_node]]) > 1:
                                raise RewritingError(
                                    "Inconsistent typing of the rule: node "
                                    "'%s' from the preserved part is typed "
                                    "by a graph '%s' as '%s' from the lhs and "
                                    "as a '%s' from the rhs." %
                                    (p_node, anc,
                                     anc_typing[typing[rule.p_lhs[p_node]]],
                                     ", ".join(
                                         rhs_typing[anc][rule.p_rhs[p_node]])))
                        if len(rhs_typing[anc][rule.p_rhs[p_node]]) == 1 and\
                            anc_typing[typing[rule.p_lhs[p_node]]] not in\
                                rhs_typing[anc][rule.p_rhs[p_node]]:
                            raise RewritingError(
                                "Inconsistent typing of the rule: node "
                                "'%s' from the preserved part is typed "
                                "by a graph '%s' as '%s' from the lhs and "
                                "as a '%s' from the rhs." %
                                (p_node, anc,
                                 anc_typing[typing[rule.p_lhs[p_node]]],
                                 list(rhs_typing[anc][rule.p_rhs[p_node]])[0]))


def _check_totality(hierarchy, graph_id, rule, instance,
                    lhs_typing, rhs_typing):
    """"Check that everything is typed at the end of the rewriting."""
    for node in rule.rhs.nodes():
        p_nodes = keys_by_value(rule.p_rhs, node)
        for typing_graph in hierarchy.successors(graph_id):
            typing = hierarchy.typing[graph_id][typing_graph]
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
                raise RewritingError(
                    "Rewriting is strict (no propagation of types is "
                    "allowed), typing of the node `%s` "
                    "in rhs is required (typing by the following "
                    "graph stays unresolved: '%s')!" %
                    (node, typing_graph))


def _check_instance(hierarchy, graph_id, pattern, instance, pattern_typing):
    # Check that the homomorphism is valid
    try:
        check_homomorphism(
            pattern,
            hierarchy.get_graph(graph_id),
            instance,
            total=True
        )
    except InvalidHomomorphism as e:
        raise RewritingError(
            "Homomorphism from the pattern to the instance subgraph "
            "is not valid, got: '{}'".format(e))

    # Check that it is a mono
    if not is_monic(instance):
        raise RewritingError(
            "Homomorphism from the pattern to the instance subgraph "
            "is not injective")

    # Check that instance typing and lhs typing coincide
    for node in pattern.nodes():
        if pattern_typing:
            for typing_graph, typing in pattern_typing.items():
                try:
                    instance_typing = hierarchy.compose_path_typing(
                        nx.shortest_path(hierarchy, graph_id, typing_graph))
                    if node in pattern_typing.keys() and\
                       instance[node] in instance_typing.keys():
                        if typing[node] != instance_typing[instance[node]]:
                            raise RewritingError(
                                "Typing of the instance of LHS does not " +
                                " coincide with typing of LHS!")
                except NetworkXNoPath:
                    raise RewritingError(
                        "Graph '%s' is not typed by '%s' specified "
                        "as a typing graph of the lhs of the rule." %
                        (graph_id, typing_graph))


def _check_rule_instance_typing(hierarchy, graph_id, rule, instance,
                                p_typing, rhs_typing, strict):
    """Check consistency of the input."""
    lhs_typing = {}

    # Autocomplete typings
    lhs_typing, p_typing, rhs_typing =\
        _autocomplete_typing(
            hierarchy, graph_id,
            instance=instance,
            lhs_typing=lhs_typing,
            p_typing=p_typing,
            rhs_typing_rel=rhs_typing,
            p_lhs=rule.p_lhs,
            p_rhs=rule.p_rhs)

    # Check the instance
    _check_instance(
        hierarchy, graph_id, rule.lhs, instance, lhs_typing)

    # Check consistency of the (autocompleted) rhs/p/lhs typings
    if lhs_typing is not None and rhs_typing is not None:
        try:
            _check_self_consistency(
                hierarchy, lhs_typing)
        except ReGraphError as e:
            raise RewritingError(
                "Typing of the lhs is self inconsistent: %s" % str(e)
            )
        try:
            _check_p_consistency(
                hierarchy, rule.p_lhs, rule.cloned_nodes(), p_typing)
        except ReGraphError as e:
            raise RewritingError(
                "Typing of the preserved part is "
                "self inconsistent: {}".format(e)
            )
        try:
            _check_self_consistency(
                hierarchy, rhs_typing, strict)
        except ReGraphError as e:
            raise RewritingError(
                "Typing of the rhs is self inconsistent: %s" % str(e)
            )

        _check_lhs_p_consistency(
            hierarchy, graph_id, rule, instance,
            lhs_typing, p_typing)

        _check_lhs_rhs_consistency(
            hierarchy, graph_id, rule, instance,
            lhs_typing, rhs_typing,
            strict)

        if strict is True:
            _check_totality(
                hierarchy, graph_id, rule, instance,
                lhs_typing, rhs_typing)
    return p_typing, rhs_typing


def _check_p_consistency(hierarchy, p_lhs, cloned_nodes, p_typing):
    def get_canonical_clones(l_node):
        if l_node in cloned_nodes.keys():
            return cloned_nodes[l_node]
        return None

    def test_canonicity(typing, graph_node):
        # check that what is mentioned in the cotrolled
        # relation for the graph node is canonical
        p_nodes = typing[graph_node]
        if len(p_nodes) > 0:
            l_node = p_lhs[list(p_nodes)[0]]
            canonical_clones = get_canonical_clones(l_node)
            if canonical_clones != p_nodes:
                raise RewritingError(
                    "Constrolled relation of the preserved part "
                    "is not consistent: propagation to the node "
                    "'{}' of '{}' ".format(ancestor_node, ancestor) +
                    "typed by '{}' in '{}' ".format(
                        graph_node, graph) +
                    "will produce instances for {} ".format(
                        canonical_clones) +
                    "while propagation to '{}' only {}".format(
                        graph_node, p_nodes)
                )

    # for every graph specified in the controlling relation
    for graph, typing in p_typing.items():
        ancestors = hierarchy.get_ancestors(graph)
        # for every its ancestor
        for ancestor, ancestor_typing in ancestors.items():
            for ancestor_node, graph_node in ancestor_typing.items():
                if graph_node in typing.keys():
                    # we need to check that what mentioned in the
                    # controlling relation is consistent
                    # (i.e. we will be able to reconstruct all the types)
                    if ancestor in p_typing.keys():
                        if ancestor_node in p_typing[ancestor].keys():
                            if not p_typing[ancestor][ancestor_node].issubset(
                                    typing[graph_node]):
                                raise RewritingError(
                                    "Constrolled relation of the preserved part "
                                    "is not consistent: propagation to the node "
                                    "'{}' of '{}' ".format(ancestor_node, ancestor) +
                                    "typed by '{}' in '{}' ".format(
                                        graph_node, graph) +
                                    "will produce instances for {} ".format(
                                        p_typing[ancestor][ancestor_node]) +
                                    "while propagation to '{}' only {}".format(
                                        graph_node, typing[graph_node])
                                )
                        else:
                            test_canonicity(typing, graph_node)
                    else:
                        test_canonicity(typing, graph_node)
                else:
                    # it is ok as graph_node will be propagated canonically
                    pass
