"""."""
import itertools
import copy

import networkx as nx
# import copy

from networkx.algorithms import isomorphism
from regraph.library.category_op import (pullback,
                                         pullback_complement,
                                         pushout,
                                         nary_pullback)
from regraph.library.primitives import (get_relabeled_graph,
                                        get_edge,
                                        add_node,
                                        add_edge)
from regraph.library.utils import (compose_homomorphisms,
                                   check_homomorphism,
                                   is_subdict,
                                   keys_by_value)


class Hierarchy(nx.DiGraph):
    """."""

    def __init__(self, directed=True):
        """Initialize an hierarchy of graphs."""
        nx.DiGraph.__init__(self)
        self.hierarchy_attrs = dict()
        self.directed = directed
        return

    def __str__(self):
        res = ""
        res += "\nGraphs (directed == %s): \n" % self.directed
        for n in self.nodes():
            res += str(n) + " "
        res += "\n"
        res += "Typing homomorphisms : \n"
        for n1, n2 in self.edges():
            res += "%s -> %s: ignore_attrs == %s, partial == %s\n" %\
                (n1, n2, self.edge[n1][n2][1], self.edge[n1][n2][2])
            res += "mapping: %s\n" % str(self.edge[n1][n2][0])

        res += "\n"
        res += "attributes : \n"
        res += str(self.hierarchy_attrs)
        res += "\n"

        return res

    def add_graph(self, graph_id, graph):
        """Add graph to the hierarchy."""
        if self.directed != graph.is_directed():
            if self.directed:
                raise ValueError("Hierarchy is defined for directed graphs!")
            else:
                raise ValueError("Hierarchy is defined for undirected graphs!")
        if graph_id in self.nodes():
            raise ValueError("Graph '%s' already exists in the hierarchy!")
        self.add_node(graph_id)
        self.node[graph_id] = graph
        return

    def add_typing(self, source, target, mapping, ignore_attrs=False):
        """Add homomorphism to the hierarchy."""
        if source not in self.nodes():
            raise ValueError(
                "Graph '%s' is not defined in the hierarchy!" % source)
        if target not in self.nodes():
            raise ValueError(
                "Graph '%s' is not defined in the hierarchy!" % target)

        # check no cycles are produced
        self.add_edge(source, target)
        if not nx.is_directed_acyclic_graph(self):
            self.remove_edge(source, target)
            raise ValueError(
                "Edge '%s->%s' creates a cycle in the hierarchy!" %
                (source, target)
            )
        self.remove_edge(source, target)

        # check if the homomorphism is valid
        check_homomorphism(
            self.node[source],
            self.node[target],
            mapping,
            ignore_attrs
        )

        # check if commutes with other shortest paths from source to target

        paths = nx.all_shortest_paths(self, source, target)
        try:
            for p in paths:
                s = p[0]
                t = p[1]
                homomorphism = self.edge[s][t][0]
                for i in range(2, len(p)):
                    s = p[i - 1]
                    t = p[i]
                    homomorphism = compose_homomorphisms(
                        self.edge[s][t][0],
                        homomorphism
                    )
                if homomorphism != mapping:
                    raise ValueError(
                        "Homomorphism does not commute with an existing " +
                        "path from '%s' to '%s'!" % (source, target))
        except(nx.NetworkXNoPath):
            pass

        self.add_edge(source, target)
        self.edge[source][target] = (mapping, ignore_attrs)
        return

    def add_partial_typing(self, source, target,
                           mapping, ignore_attrs=False):
        """Add partial homomorphism A -\ B"""
        # 1. Construct A' (A' >-> A)
        if self.is_directed:
            new_graph = nx.DiGraph()
        else:
            new_graph = nx.Graph()

        new_graph_source = {}
        for node in self.node[source].nodes():
            if node in mapping.keys():
                add_node(new_graph, node, self.node[source].node[node])
                new_graph_source[node] = node

        for s, t in self.node[source].edges():
            if s in new_graph.nodes() and t in new_graph.nodes():
                add_edge(new_graph, s, t, get_edge(self.node[source], s, t))

        # generate_name for the new_graph
        new_name = str(source) + "_" + str(target)
        if new_name in self.nodes():
            i = 1
            new_name = str(source) + "_" + str(target) + str(i)
            while new_name in self.nodes():
                i += 1
                new_name = str(source) + "_" + str(target) + str(i)

        new_graph_target = dict(
            [(node, mapping[node]) for node in new_graph.nodes()]
        )
        self.add_graph(new_name, new_graph)
        self.add_typing(new_name, source, new_graph_source, False)
        self.add_typing(new_name, target, new_graph_target, ignore_attrs)
        return

    def remove_graph(self, graph_id, reconnect=False):
        """Remove graph from the hierarchy.

        If `reconnect`, map the children homomorphisms
        of this graph to its parents.
        """
        if graph_id not in self.nodes():
            raise ValueError(
                "Graph `%s` is not defined in the hierarchy!" % graph_id)

        if reconnect:
            out_graphs = self.successors(graph_id)
            in_graphs = self.predecessors(graph_id)

            for source in in_graphs:
                for target in out_graphs:

                    # compose two homomorphisms
                    mapping = compose_homomorphisms(
                        self.edge[graph_id][target][0],
                        self.edge[source][graph_id][0]
                    )

                    if (source, target) not in self.edges():
                        self.add_typing(
                            source,
                            target,
                            mapping,
                            self.edge[source][graph_id][1] or self.edge[graph_id][target][1]
                        )

        self.remove_node(graph_id)

    def node_type(self, graph_id, node_id):
        if graph_id not in self.nodes():
            raise ValueError(
                "Graph '%s' is not defined in the hierarchy!"
                % graph_id
            )
        if node_id not in self.node[graph_id].nodes():
            raise ValueError(
                "Graph '%s' does not have a node with id '%s'!"
                % (graph_id, node_id)
            )
        types = []
        for _, typing in self.out_edges(graph_id):
            mapping = self.edge[graph_id][typing][0]
            types.append(mapping[node_id])
        return types

    def find_matching(self, graph_id, pattern, pattern_typing=None, ignore_attrs=False):
        """Find an instance of a pattern in a specified graph.

        `graph_id` -- id of a graph in the hierarchy to search for matches;
        `pattern` -- nx.(Di)Graph object defining a pattern to match;
        `typing_graph` -- id of a graph in the hierarchy that types a pattern,
        this graph should be among parents of the `graph_id` graph;
        `pattern_typing` -- a dictionary that specifies a mapping of nodes
        from pattern to the typing graph;
        `ignore_attrs` -- if set to True the matching will ignore
        attributes homomorphism (by defaults attributes are not ignored).
        """

        # Check that 'typing_graph' and 'pattern_typing' are correctly specified
        if len(self.successors(graph_id)) != 0:
            if pattern_typing is None:
                raise ValueError(
                    "Graph '%s' has non-empty set of parents, " +
                    "pattern should be typed by one of them!" %
                    graph_id
                )
            # Check 'typing_graph' is in successors of 'graph_id'
            for typing_graph, _ in pattern_typing.items():
                if typing_graph not in self.successors(graph_id):
                    raise ValueError(
                        "Pattern typing graph '%s' is not in the typing graphs of '%s'!" %
                        (typing_graph, graph_id)
                    )
            # Check pattern typing is a valid homomorphism
            for typing_graph, mapping in pattern_typing.items():
                check_homomorphism(
                    pattern,
                    self.node[typing_graph],
                    mapping,
                    self.edge[graph_id][typing_graph][1]
                )

        labels_mapping = dict(
            [(n, i + 1) for i, n in enumerate(self.node[graph_id].nodes())])
        g = get_relabeled_graph(self.node[graph_id], labels_mapping)

        if pattern_typing:
            g_typing = dict([
                (typing_graph, dict([
                    (labels_mapping[k], v) for k, v in self.edge[graph_id][typing_graph][0].items()
                ])) for typing_graph in pattern_typing.keys()
            ])

        matching_nodes = set()

        # Find all the nodes matching the nodes in a pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if pattern_typing:
                    # check types match
                    for typing_graph, typing in pattern_typing.items():
                        if g_typing[typing_graph][node] == typing[pattern_node]:
                            if ignore_attrs or is_subdict(pattern.node[pattern_node], g.node[node]):
                                matching_nodes.add(node)
                else:
                    if ignore_attrs or is_subdict(pattern.node[pattern_node], g.node[node]):
                        matching_nodes.add(node)
        reduced_graph = g.subgraph(matching_nodes)
        instances = []
        isomorphic_subgraphs = []
        for sub_nodes in itertools.combinations(reduced_graph.nodes(),
                                                len(pattern.nodes())):
                subg = reduced_graph.subgraph(sub_nodes)
                for edgeset in itertools.combinations(subg.edges(),
                                                      len(pattern.edges())):
                    if g.is_directed():
                        edge_induced_graph = nx.DiGraph(list(edgeset))
                        edge_induced_graph.add_nodes_from(
                            [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                        matching_obj = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
                        for isom in matching_obj.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))
                    else:
                        edge_induced_graph = nx.Graph(edgeset)
                        edge_induced_graph.add_nodes_from(
                            [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                        matching_obj = isomorphism.GraphMatcher(pattern, edge_induced_graph)
                        for isom in matching_obj.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))

        for subgraph, mapping in isomorphic_subgraphs:
            # Check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if pattern_typing:
                    for typing_graph, typing in pattern_typing.items():
                        if g_typing[typing_graph][node] != typing[pattern_node]:
                            break
                if not ignore_attrs and\
                   not is_subdict(pattern.node[pattern_node], subgraph.node[node]):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = get_edge(pattern, edge[0], edge[1])
                    target_attrs = get_edge(subgraph, mapping[edge[0]], mapping[edge[1]])
                    if not ignore_attrs and not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # Bring back original labeling
        inverse_mapping = dict(
            [(value, key) for key, value in labels_mapping.items()]
        )
        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]
        return instances

    def rewrite(self, graph_id, instance, rule,
                lhs_typing=None, rhs_typing=None):
        """Rewrite and propagate the changes up."""

        # 0. Check consistency of the input parameters &
        # validity of homomorphisms

        # 1. Rewriting steps
        g_m, p_g_m, g_m_g = pullback_complement(
            rule.p,
            rule.lhs,
            self.node[graph_id],
            rule.p_lhs,
            instance
        )

        g_prime, g_m_g_prime, r_g_prime = pushout(
            rule.p,
            g_m,
            rule.rhs,
            p_g_m,
            rule.p_rhs
        )

        # set g_prime for the 'graph_id' node
        updated_graphs = {
            graph_id: (g_m, g_m_g, g_prime, g_m_g_prime)
        }
        updated_homomorphisms = {}
        removed_homomorphisms = set()

        for typing_graph in self.successors(graph_id):
            if typing_graph not in rhs_typing.keys():
                # check if there are anything added or merged
                removed_homomorphisms.add((graph_id, typing_graph))
                # self.remove_edge(graph_id, typing_graph)
            else:
                new_nodes = {}
                removed_nodes = set()
                new_hom = copy.deepcopy(self.edge[graph_id][typing_graph][0])
                for node in rule.lhs.nodes():
                    p_keys = keys_by_value(rule.p_lhs, node)
                    # nodes that were removed
                    if len(p_keys) == 0:
                        removed_nodes.add(node)
                    # nodes that were cloned
                    elif len(p_keys) > 1:
                        for k in p_keys:
                            new_nodes[p_g_m[k]] =\
                                lhs_typing[typing_graph][node]
                for node in rule.rhs.nodes():
                    p_keys = keys_by_value(rule.p_rhs, node)
                    # nodes that were added
                    if len(p_keys) == 0:
                        new_nodes.update({
                            node: rhs_typing[typing_graph][node]
                        })
                    # nodes that were merged
                    elif len(p_keys) > 1:
                        removed_nodes.add(set([
                            instance[rule.p_lhs[k]] for k in p_keys
                        ]))
                        new_nodes.update({
                            node: rhs_typing[typing_graph][node]
                        })
                # update homomorphisms
                for n in removed_nodes:
                    del new_hom[n]
                new_hom.update(new_nodes)
                updated_homomorphisms.update({
                    (graph_id, typing_graph): new_hom
                })

        # 2. Propagation steps reverse BFS on neighbours
        current_level = set(self.predecessors(graph_id))
        successors = dict([
            (n, [graph_id]) for n in current_level
        ])
        while len(current_level) > 0:
            next_level = set()
            for graph in current_level:
                # print("gonna propagate here: %s", graph)
                # print(successors)
                # make changes to the graph
                if len(successors[graph]) == 1:
                    # simple case
                    suc = successors[graph][0]
                    if suc in updated_graphs.keys():
                        # find pullback
                        graph_m, graph_m_graph, graph_m_suc_m =\
                            pullback(
                                self.node[graph],
                                updated_graphs[suc][0],
                                self.node[suc],
                                self.edge[graph][suc][0],
                                updated_graphs[suc][1]
                            )
                        updated_graphs.update({
                            graph: (graph_m, graph_m_graph, None, None)
                        })
                        updated_homomorphisms.update({
                            (graph, suc): graph_m_suc_m
                        })
                        # TODO!!!: if suc_m_succ_prime is monic try to do final PBC
                else:
                    # complicated case
                    cospans = {}
                    for suc in successors[graph]:
                        if suc in updated_graphs.keys():
                            cospans.update({
                                suc:
                                    (updated_graphs[suc][0],
                                     self.node[suc],
                                     self.edge[graph][suc][0],
                                     updated_graphs[suc][1])
                            })
                    graph_m, graph_m_graph, graph_m_sucs_m =\
                        nary_pullback(self.node[graph], cospans)
                    # apply changes to the hierarchy
                    updated_graphs.update({
                        graph: (graph_m, graph_m_graph, None, None)
                    })
                    for suc, graph_m_suc in graph_m_sucs_m.items():
                        updated_homomorphisms.update({
                            (graph, suc): graph_m_suc
                        })

                # update step
                next_level.update(self.predecessors(graph))
                for n in self.predecessors(graph):
                    if n in successors.keys():
                        successors[n].append(graph)
                    else:
                        successors[n] = [graph]
                del successors[graph]
            current_level = next_level

        # 3. Apply changes to the hierarchy
        for graph, (graph_m, _, graph_prime, _) in updated_graphs.items():
            if graph_prime is not None:
                self.node[graph] = graph_prime
            else:
                self.node[graph] = graph_m
        for (s, t) in removed_homomorphisms:
            self.remove_edge(s, t)
        for (s, t), mapping in updated_homomorphisms.items():
            self.edge[s][t] = (mapping, self.edge[s][t][1])
        return
