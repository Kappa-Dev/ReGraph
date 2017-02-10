"""Graph rewriting tools."""
import itertools

import networkx as nx
from networkx.algorithms import isomorphism

from regraph.library.category_op import (pullback_complement,
                                         pushout)
from regraph.library.utils import (is_subdict,
                                   valid_attributes,
                                   keys_by_value,
                                   dict_sub,
                                   merge_attributes)
from regraph.library.data_structures import Homomorphism


def find_matching(graph, pattern, ignore_types=False, ignore_attrs=False):
        """Perform matching of the pattern graph."""
        # NetworkX isomorphism lib crushes if the ids of nodes
        # have different types (e.g ints and strings).
        # For the sake of security we will temporarily make
        # all the nodes ids to be int
        labels_mapping = dict([(n, i + 1) for i, n in enumerate(graph.nodes())])
        g = graph.get_relabeled_graph(labels_mapping)
        matching_nodes = set()

        # find all the nodes matching the nodes in pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if ignore_types is False:
                    if pattern.node[pattern_node].type_ == g.node[node].type_:
                        if type(pattern.node[pattern_node]) == dict():
                            source_attrs = pattern.node[pattern_node]
                        else:
                            source_attrs = pattern.node[pattern_node].attrs_
                        if type(g.node[node]) == dict():
                            target_attrs = g.node[node]
                        else:
                            target_attrs = g.node[node].attrs_

                        if ignore_attrs or valid_attributes(source_attrs, target_attrs):
                            matching_nodes.add(node)
                else:
                    if type(pattern.node[pattern_node]) == dict():
                        source_attrs = pattern.node[pattern_node]
                    else:
                        source_attrs = pattern.node[pattern_node].attrs_
                    if type(g.node[node]) == dict():
                        target_attrs = g.node[node]
                    else:
                        target_attrs = g.node[node].attrs_

                    if ignore_attrs or valid_attributes(source_attrs, target_attrs):
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
                        GM = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
                        for isom in GM.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))
                    else:
                        edge_induced_graph = nx.Graph(edgeset)
                        edge_induced_graph.add_nodes_from(
                            [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                        GM = isomorphism.GraphMatcher(pattern, edge_induced_graph)
                        for isom in GM.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))

        for subgraph, mapping in isomorphic_subgraphs:
            # check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if not pattern.node[pattern_node].type_ == subgraph.node[node].type_:
                    break
                if type(pattern.node[pattern_node]) == dict():
                    source_attrs = pattern.node[pattern_node]
                else:
                    source_attrs = pattern.node[pattern_node].attrs_
                if type(g.node[node]) == dict():
                    target_attrs = subgraph.node[node]
                else:
                    target_attrs = subgraph.node[node].attrs_
                if not ignore_attrs and not valid_attributes(source_attrs, target_attrs):
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = pattern.get_edge(edge[0], edge[1])
                    target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
                    if not ignore_attrs and not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # bring back original labeling
        inverse_mapping = dict([(value, key) for key, value in labels_mapping.items()])
        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]
        return instances


def apply(graph, instance, rule):
        """Apply a rewriting rule for a given graph."""

        p_lhs = Homomorphism(rule.p, rule.lhs, rule.p_lhs)
        p_rhs = Homomorphism(rule.p, rule.rhs, rule.p_rhs)
        l_g = Homomorphism(rule.lhs, graph, instance)

        (g_m, p_g_m, g_m_g) = pullback_complement(p_lhs, l_g)
        (g_prime, g_m_g_prime, r_g_prime) = pushout(p_g_m, p_rhs)

        return g_prime


class Rewriter(object):
    """Rewriter object incapsulates graph hierarchy and performs
       applications of the rules to the given graph alongside with
       propagation of the changes up the hierarchy.
    """
    def __init__(self, graph, ignore_types=False, ignore_attrs=False):
        # if graph is not None:
        #     if graph.typing_graph is not None:
        #         if ignore_types is True:
        #             raise ValueError("Input graph has a typing graph, cannot initialize a type ignoring Rewriter!")
        self.graph = graph
        self.ignore_types = ignore_types
        self.ignore_attrs = ignore_attrs
        return

    def propagate(self):
        """Propagate some changes if they were made."""
        pass

    def apply_propagate(self, rule, level=None):
        """Apply rule at the given level and propagate the changes up."""
        pass

    def apply_transform(self, instance, rule):

        p_g_m = {}
        # Remove/clone nodes
        for n in rule.lhs.nodes():
            p_keys = keys_by_value(rule.p_lhs, n)
            # Remove nodes
            if len(p_keys) == 0:
                self.graph.remove_node(instance[n])
            # Keep nodes
            elif len(p_keys) == 1:
                p_g_m[p_keys[0]] = instance[n]
            # Clone nodes
            else:
                i = 1
                for k in p_keys:
                    if i == 1:
                        p_g_m[k] = instance[n]
                    else:
                        new_name = self.graph.clone_node(instance[n])
                        p_g_m[k] = new_name
                    i += 1
        
        # Remove edges
        for (n1, n2) in rule.lhs.edges():
            p_keys_1 = keys_by_value(rule.p_lhs, n1)
            p_keys_2 = keys_by_value(rule.p_lhs, n2)
            if len(p_keys_1) > 0 and  len(p_keys_2) > 0:
                for k1 in p_keys_1:
                    for k2 in p_keys_2:
                        if self.graph.is_directed():
                            if (k1, k2) not in rule.p.edges():
                                if (p_g_m[k1], p_g_m[k2]) in self.graph.edges():
                                    self.graph.remove_edge(p_g_m[k1], p_g_m[k2])
                        else:
                            if (k1, k2) not in rule.p.edges() and (k2, k1) not in rule.p.edges():
                                if (p_g_m[k1], p_g_m[k2]) in self.graph.edges() or\
                                   (p_g_m[k2], p_g_m[k1]) in self.graph.edges():
                                    self.graph.remove_edge(p_g_m[k1], p_g_m[k2])
        # Remove node attrs
        for n in rule.p.nodes():
            attrs_to_remove = dict_sub(
                rule.lhs.node[rule.p_lhs[n]].attrs_,
                rule.p.node[n].attrs_
            )
            self.graph.remove_node_attrs(p_g_m[n], attrs_to_remove)

        # Remove edge attrs
        for (n1, n2) in rule.p.edges():
            attrs_to_remove = dict_sub(
                rule.lhs.get_edge(rule.p_lhs[n1], rule.p_lhs[n2]),
                rule.p.get_edge(n1, n2)
            )
            self.graph.remove_edge_attrs(p_g_m[n1], p_g_m[n2], attrs_to_remove)
        

        # Add/merge nodes
        rhs_g_prime = {}
        for n in rule.rhs.nodes():
            p_keys = keys_by_value(rule.p_rhs, n)
            # Add nodes
            if len(p_keys) == 0:
                self.graph.add_node(n,
                                    rule.rhs.node[n].type_,
                                    rule.rhs.node[n].attrs_)
                rhs_g_prime[n] = n
            # Keep nodes
            elif len(p_keys) == 1:
                rhs_g_prime[rule.p_rhs[p_keys[0]]] = p_g_m[p_keys[0]]
            # Merge nodes
            else:
                nodes_to_merge = []
                for k in p_keys:
                    nodes_to_merge.append(p_g_m[k])
                new_name = self.graph.merge_nodes(nodes_to_merge)
                rhs_g_prime[n] = new_name

        # Add edges
        for (n1, n2) in rule.rhs.edges():
            if self.graph.is_directed():
                if (rhs_g_prime[n1], rhs_g_prime[n2]) not in self.graph.edges():
                    self.graph.add_edge(
                        rhs_g_prime[n1],
                        rhs_g_prime[n2],
                        rule.rhs.get_edge(n1, n2))
            else:
                if (rhs_g_prime[n1], rhs_g_prime[n2]) not in self.graph.edges() and\
                   (rhs_g_prime[n2], rhs_g_prime[n1]) not in self.graph.edges():
                    self.graph.add_edge(
                        rhs_g_prime[n1],
                        rhs_g_prime[n2],
                        rule.rhs.get_edge(n1, n2))

        # Add node attrs
        for n in rule.rhs.nodes():
            p_keys = keys_by_value(rule.p_rhs, n)
            # Add attributes to the nodes which stayed invariant
            if len(p_keys) == 1:
                attrs_to_add = dict_sub(
                    rule.rhs.node[n].attrs_,
                    rule.p.node[p_keys[0]].attrs_
                )
                self.graph.add_node_attrs(rhs_g_prime[n], attrs_to_add)
            # Add attributes to the nodes which were merged
            elif len(p_keys) > 1:
                merged_attrs = {}
                for k in p_keys:
                    merged_attrs = merge_attributes(
                        merged_attrs,
                        rule.p.node[k].attrs_
                    )
                attrs_to_add = dict_sub(rule.rhs.node[n].attrs_, merged_attrs)
                self.graph.add_node_attrs(rhs_g_prime[n], attrs_to_add)

        # Add edge attrs
        for (n1, n2) in rule.rhs.edges():
            p_keys_1 = keys_by_value(rule.p_rhs, n1)
            p_keys_2 = keys_by_value(rule.p_rhs, n2)
            for k1 in p_keys_1:
                for k2 in p_keys_2:
                    if self.graph.is_directed():
                        if (k1, k2) in rule.p.edges():
                            attrs_to_add = dict_sub(
                                rule.rhs.get_edge(n1, n2),
                                rule.p.get_edge(k1, k2)
                            )
                            self.graph.add_edge_attrs(
                                rhs_g_prime[n1],
                                rhs_g_prime[n2], 
                                attrs_to_add
                            )
                    else:
                        if (k1, k2) in rule.p.edges() or (k2, k1) in rule.p.edges():
                            attrs_to_add = dict_sub(
                                rule.rhs.get_edge(n1, n2),
                                rule.p.get_edge(k1, k2)
                            )
                            self.graph.add_edge_attrs(
                                rhs_g_prime[n1],
                                rhs_g_prime[n2],
                                attrs_to_add
                            )

        return rhs_g_prime

# class Rewriter:
#     """Class implements the transformation on the graph."""

#     def __init__(self, graph=None):
#         """Initialize Rewriter object with input graph."""
#         self.graph_ = graph
#         self.parser_ = parser
#         return

#     def __doc__(self):
#         return "A Rewriter instance alows you to do a horizontal rewrite on "+\
#                 "a single graph, it also gives the needed informations (the "+\
#                 "G- -> G and G- -> Gprime homomorphisms) to propagate that "+\
#                 "change in the GraphModeler"

#     @staticmethod
#     def rewrite_simple(trans, get_details=False):
#        return(Rewriter.rewrite(Homomorphism.identity(trans.L,trans.G),trans,get_details))

#     @staticmethod
#     def rewrite(L_G, trans, get_details=False):
#         """ Simple rewriting using category operations """
#         left_h, right_h = trans.get()
#         graph = trans.G

#         if left_h.source_ != right_h.source_:
#             raise ValueError(
#                 "Can't rewrite, homomorphisms don't have the same preserved part"
#             )
#         Gm, P_Gm, Gm_G = pullback_complement(left_h, L_G)
#         Gprime, Gm_Gprime, R_Gprime = pushout(P_Gm, right_h)

#         for n in Gm.nodes():
#             n2 = Gm_G[n]
#             if graph.node[n2].attributes_typing:
#                 Gprime.node[Gm_Gprime[n]].attributes_typing = copy.deepcopy(graph.node[n2].attributes_typing)

#         Gprime.metamodel_ = graph.metamodel_
#         if graph.graph_attr:
#             Gprime.graph_attr = copy.deepcopy(graph.graph_attr) 
#         Gprime.hom = TypedHomomorphism.canonic(Gprime, graph.metamodel_)
        
#         if get_details:
#             return Gm_Gprime, Gm_G
#         else:
#             return Gprime

#     @staticmethod
#     def do_canonical_rewrite(G, transformations, get_details=False):
#         """ Does a simple rewriting by decomposing the transformations string
#             into a list of canonical transformations strings """
#         di = type(G) == TypedDiGraph
#         trans_list = Rewriter.make_canonical_commands(G, transformations, di)
#         return Rewriter.chain_rewrite(G, trans_list, get_details)

#     def do_rewrite(G, transformations, get_details=False):
#         trans = Rewriter.transformer_from_command(G, transformations)
#         L_G = Homomorphism.identity(trans.L, trans.G)
#         return Rewriter.rewrite(L_G, trans, get_details)

#     @staticmethod
#     def chain_rewrite(G, trans_list, get_details=False):
#         """ Does multiple simple rewritings on G given a list of transformations """
#         res = []
#         for transformation in trans_list:
#             if get_details:
#                 trans = Rewriter.transformer_from_command(res[-1][0].target_ if res != [] else G, transformation)
#                 rw_res = Rewriter.rewrite(Homomorphism.identity(trans.L,
#                                                                 trans.G),
#                                           trans,
#                                           get_details)
#                 res.append(rw_res)
#             else:
#                 trans = Rewriter.transformer_from_command(res[-1] if res != [] else G, transformation)
#                 rw_res = Rewriter.rewrite(Homomorphism.identity(trans.L,
#                                                                 trans.G),
#                                           trans,
#                                           get_details)
#                 res = [rw_res]
#         if get_details:
#             return res
#         else:
#             return res[0]


#     @staticmethod
#     def find_matching(graph, pattern, ignore_attrs = False):
#         """Perform matching of the pattern graph."""
#         # NetworkX isomorphism lib crushes if the ids of nodes
#         # have different types (e.g ints and strings).
#         # For the sake of security we will temporarily make
#         # all the nodes ids to be int
#         labels_mapping = dict([(n, i + 1) for i, n in enumerate(graph.nodes())])
#         g = graph.relabel_nodes(labels_mapping)
#         matching_nodes = set()
#         # find all the nodes matching the nodes in pattern
#         for pattern_node in pattern.nodes():
#             for node in g.nodes():
#                 if pattern.node[pattern_node].type_ == g.node[node].type_:
#                     # if ignore_attrs or is_subdict(pattern.node[pattern_node].attrs_,
#                     #                                     g.node[node].attrs_):
#                     #     matching_nodes.add(node)
#                     if ignore_attrs or valid_attributes(pattern.node[pattern_node].attrs_,
#                                                         g.node[node]):
#                         matching_nodes.add(node)
#         reduced_graph = g.subgraph(matching_nodes)
#         instances = []
#         isomorphic_subgraphs = []
#         for sub_nodes in itertools.combinations(reduced_graph.nodes(),
#                                                 len(pattern.nodes())):
#                 subg = reduced_graph.subgraph(sub_nodes)
#                 for edgeset in itertools.combinations(subg.edges(),
#                                                       len(pattern.edges())):
#                     if g.is_directed():
#                         edge_induced_graph = nx.DiGraph(list(edgeset))
#                         edge_induced_graph.add_nodes_from(
#                             [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
#                         GM = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
#                         for isom in GM.isomorphisms_iter():
#                             isomorphic_subgraphs.append((subg, isom))
#                     else:
#                         edge_induced_graph = nx.Graph(edgeset)
#                         edge_induced_graph.add_nodes_from(
#                             [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
#                         GM = isomorphism.GraphMatcher(pattern, edge_induced_graph)
#                         for isom in GM.isomorphisms_iter():
#                             isomorphic_subgraphs.append((subg, isom))
#         for subgraph, mapping in isomorphic_subgraphs:
#             # check node matches
#             # exclude subgraphs which nodes information does not
#             # correspond to pattern
#             for (pattern_node, node) in mapping.items():
#                 if not pattern.node[pattern_node].type_ == subgraph.node[node].type_:
#                     break
#                 # if not ignore_attrs and not is_subdict(pattern.node[pattern_node].attrs_, subgraph.node[node].attrs_):
#                 if not ignore_attrs and not valid_attributes(pattern.node[pattern_node].attrs_, subgraph.node[node]):
#                     break
#             else:
#                 # check edge attribute matched
#                 for edge in pattern.edges():
#                     pattern_attrs = pattern.get_edge(edge[0], edge[1])
#                     target_attrs = subgraph.get_edge(mapping[edge[0]], mapping[edge[1]])
#                     if not ignore_attrs and not is_subdict(pattern_attrs, target_attrs):
#                         break
#                 else:
#                     instances.append(mapping)

#         # bring back original labeling
#         inverse_mapping = dict([(value, key) for key, value in labels_mapping.items()])
#         for instance in instances:
#             for key, value in instance.items():
#                 instance[key] = inverse_mapping[value]
#         return instances

#     @staticmethod
#     def transformer_from_command(G, commands):
#         """Cast sequence of commands to Transformer instance."""
#         command_strings = [c for c in commands.splitlines() if len(c) > 0]
#         actions = []
#         for command in command_strings:
#             try:
#                 parsed = parser.parseString(command).asDict()
#                 actions.append(parsed)
#             except:
#                 raise ValueError("Cannot parse command '%s'" % command)

#         trans = Transformer(G)

#         for action in actions:
#             if action["keyword"] == "clone":
#                 node_name = None
#                 if "node_name" in action.keys():
#                     node_name = action["node_name"]
#                 trans.clone_node(action["node"], node_name)
#             elif action["keyword"] == "merge":
#                 method = None
#                 node_name = None
#                 edges_method = None
#                 if "method" in action.keys():
#                     method = action["method"]
#                 if "node_name" in action.keys():
#                     node_name = action["node_name"]
#                 if "edges_method" in action.keys():
#                     edges_method = action["edges_method"]
#                 merged_node = trans.merge_nodes_list(
#                     action["nodes"],
#                     node_name)
#             elif action["keyword"] == "add_node":
#                 name = None
#                 node_type = None
#                 attrs = {}
#                 if "node" in action.keys():
#                     name = action["node"]
#                 if "type" in action.keys():
#                     node_type = action["type"]
#                 if "attributes" in action.keys():
#                     attrs = action["attributes"]
#                 trans.add_node(name, node_type, attrs)
#             elif action["keyword"] == "delete_node":
#                 trans.remove_node(action["node"])
#             elif action["keyword"] == "add_edge":
#                 attrs = {}
#                 if "attributes" in action.keys():
#                     attrs = action["attributes"]
#                 trans.add_edge(
#                     action["node_1"],
#                     action["node_2"],
#                     attrs)
#             elif action["keyword"] == "delete_edge":
#                 trans.remove_edge(
#                     action["node_1"],
#                     action["node_2"])
#             elif action["keyword"] == "add_node_attrs":
#                 trans.add_node_attrs(
#                     action["node"],
#                     action["attributes"])
#             elif action["keyword"] == "add_edge_attrs":
#                 trans.add_edge_attrs(
#                     action["node_1"],
#                     action["node_2"],
#                     action["attributes"])
#             elif action["keyword"] == "delete_node_attrs":
#                 trans.remove_node_attrs(
#                     action["node"],
#                     action["attributes"])
#             elif action["keyword"] == "delete_edge_attrs":
#                 trans.remove_edge_attrs(
#                     action["node_1"],
#                     action["node_2"],
#                     action["attributes"])
#             else:
#                 raise ValueError("Unknown command %s" % action["keyword"])
#         return trans



#     @staticmethod
#     def gen_transformations(n, graph, p_opt=0.5, merge_prop_av = 0.2,
#                             merge_prop_dev = 0.05, p_attrs = 0.5, p_attrs_value=0.5):

#         def rand_attrs(attrs):
#             """ Picks random attributes from attrs using the probabilities in
#                 the main function arguments """
#             if attrs is None:
#                 return {}

#             new_attrs = {}
#             for k,v in attrs.items():
#                 if random.random() <= p_attrs:
#                     value = []
#                     for val in v:
#                         if random.random() <= p_attrs_value:
#                             value.append(val)
#                     new_attrs[k] = set(value)
#             keys_to_remove = []
#             for k,v in new_attrs.items():
#                 if v == set():
#                     keys_to_remove.append(k)
#             for k in keys_to_remove:
#                 new_attrs.pop(k)
#             return new_attrs

#         trans = []
#         env = graph.copy()
#         base_nodes = [n for n in graph.nodes()]
#         if graph.metamodel_ is None:
#             types = ["anything"]
#         else:
#             types = graph.metamodel_.nodes()
#         actions = [
#             "CLONE",
#             "MERGE",
#             "ADD_NODE",
#             "DELETE_NODE",
#             "ADD_EDGE",
#             "DELETE_EDGE",
#             "ADD_NODE_ATTRS",
#             "ADD_EDGE_ATTRS",
#             "DELETE_NODE_ATTRS",
#             "DELETE_EDGE_ATTRS"
#         ]

#         def pick_node():
#             """ Picks a node in the graph if possible """
#             if len(base_nodes) > 0:
#                 return random.sample(base_nodes, 1)[0]
#             else:
#                 return None

#         def pick_nodes():
#             """ Picks multiple node (a random number following a gaussian law
#                 with parameters merge_prop_av and merge_prop_dev) if possible """
#             if env.metamodel_ is None:
#                 ty = random.choice([None, "anything"])
#             else:
#                 ty = pick_type()
#             node_list = [n for n in base_nodes if env.node[n].type_ == ty]
#             n = abs(int(random.gauss(merge_prop_av*len(node_list),
#                                      merge_prop_dev*len(node_list))))
#             while n < 2 and len(node_list) > 5:
#                 n = abs(int(random.gauss(merge_prop_av*len(node_list),
#                                          merge_prop_dev*len(node_list))))
#             if n < 2:
#                 return []
#             res = []
#             for node in random.sample(node_list, n):
#                 res.append(node)
#             return res

#         def pick_edge():
#             """ Picks an existing edge if possible """
#             if len(env.edges()) > 0 and len(base_nodes) > 1:
#                 edge = random.sample(env.edges(), 1)[0]
#                 if edge[0] in base_nodes and edge[1] in base_nodes:
#                     return edge
#             return None,None

#         def pick_new_edge():
#             """ Picks two nodes that can have an edge between them and don't yet
#                 if possible """
#             i = 500
#             while i > 0:
#                 n1 = pick_node()
#                 n2 = pick_node()
#                 if n1 is not None and n2 is not None:
#                     if env.metamodel_ is None or\
#                        (env.node[n1].type_, env.node[n2].type_) in env.metamodel_.edges() and\
#                        (n1, n2) not in env.edges() and n1 != n2:
#                         return (n1, n2)
#                     else:
#                         i-=1
#             return None

#         def pick_type():
#             """ Picks a type """
#             return random.sample(types, 1)[0]

#         def pick_attrs_from(node):
#             """ Picks random attrs from the attrs of node """
#             return rand_attrs(env.node[node].attrs_)

#         def pick_attrs_for(node):
#             """ Picks random attrs from the attrs of the typing node of node """
#             if graph.metamodel_ is None:
#                 return {}
#             else:
#                 return rand_attrs(graph.metamodel_.node[env.node[node].type_].attrs_)

#         def pick_edge_attrs_from(n1, n2):
#             """ Picks random attrs from the attrs of edge """
#             return rand_attrs(env.get_edge(n1, n2))

#         def pick_edge_attrs_for(n1, n2):
#             """ Picks random attrs from the attrs of the typing edge of edge """
#             if env.metamodel_ is None:
#                 return {}
#             else:
#                 return rand_attrs(env.metamodel_.get_edge(
#                     env.node[n1].type_,
#                     env.node[n2].type_
#                 ))

#         def pick_name():
#             """ Picks a node_name that isn't in the graph yet """
#             i = random.randint(0, 500)
#             if len(env.nodes()) > 1:
#                 generated_name = ".".join(random.sample(env.nodes(), 2))
#             else:
#                 generated_name = "newNode"+str(i)
#             while str(generated_name) in env.nodes():
#                 i = random.randint(0, 500)
#                 if len(env.nodes()) > 1:
#                     generated_name = ".".join(random.sample(env.nodes(), 2))
#                 else:
#                     generated_name = "newNode"+str(i)
#             return str(generated_name)

#         def pick_method():
#             """ Picks a method to use for merging """
#             return random.choice(["UNION", "INTERSECTION"])

#         def add_req(op, s):
#             """ Updates the transformation list with a required argument """
#             op += s
#             return op

#         def add_opt(op, s):
#             """ Updates the transformation list with an optional argument """
#             if random.random() <= p_opt:
#                 op += s
#                 return True, op
#             else:
#                 return False, op

#         # We pick a random operation each time and try to do it

#         while len(trans) < n:
#             op = random.choice(actions)
#             if op == "CLONE":
#                 node = pick_node()
#                 if node is None or "_" in node:
#                     continue
#                 name = pick_name()

#                 op = add_req(op, " '%s'" % str(node))
#                 opt,op = add_opt(op, " AS '%s'" % str(name))
#                 if not opt:
#                     name = None
#                 else:
#                     base_nodes.append(name)

#                 env.clone_node(node, name)
#                 trans.append(op)
#             elif op == "MERGE":
#                 nodes = pick_nodes()
#                 if nodes == []:
#                     continue
#                 method = pick_method()
#                 new_name = pick_name()
#                 edges = pick_method()
#                 new_node_attrs = None
#                 new_edge_attrs = None

#                 op = add_req(op, " "+str(nodes))
#                 opt,op = add_opt(op, " METHOD "+str(method))
#                 if not opt:
#                     method = "UNION"
#                 opt,op = add_opt(op, " AS '%s'" % str(new_name))
#                 if not opt:
#                     new_name = None
#                 else:
#                     base_nodes.append(new_name)
#                 opt,op = add_opt(op, " EDGES "+str(edges))
#                 if not opt:
#                     edges = "UNION"

#                 if nodes != []:
#                     env.merge_nodes(nodes,
#                                 method.lower(),
#                                 new_name,
#                                 edges.lower())
#                 for node in nodes:
#                     base_nodes.remove(node)

#                 trans.append(op)
#             elif op == "ADD_NODE":
#                 name = pick_name()
#                 typ = pick_type()

#                 attrs = rand_attrs(env.metamodel_.node[typ].attrs_)

#                 op = add_req(op, " '%s'" % str(name))
#                 op = add_req(op, " TYPE '%s'" % str(typ))
#                 opt,op = add_opt(op, " "+str(attrs))
#                 if not opt:
#                     attrs = None

#                 base_nodes.append(name)
#                 env.add_node(name, typ, attrs)
#                 trans.append(op)
#             elif op == "DELETE_NODE":
#                 node = pick_node()
#                 if node is None:
#                     continue

#                 op = add_req(op, " '%s'" % str(node))

#                 base_nodes.remove(node)
#                 env.remove_node(node)
#                 trans.append(op)
#             elif op == "ADD_EDGE":
#                 e = pick_new_edge()
#                 if e is None:
#                     continue
#                 else:
#                     n1, n2 = e
#                 attrs = pick_edge_attrs_for(n1, n2)

#                 op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))
#                 opt,op = add_opt(op, " "+str(attrs))
#                 if not opt:
#                     attrs = None

#                 env.add_edge(n1, n2, attrs)
#                 trans.append(op)
#             elif op == "DELETE_EDGE":
#                 n1, n2 = pick_edge()
#                 if n1 is None or n2 is None:
#                     continue

#                 op = add_req(op, " '%s' '%s'" % (str(n1),str(n2)))

#                 env.remove_edge(n1, n2)
#                 trans.append(op)
#             elif op == "ADD_NODE_ATTRS":
#                 node = pick_node()
#                 if node is None:
#                     continue
#                 if env.metamodel_ is None:
#                     attrs = {}
#                 else:
#                     if env.metamodel_.node[env.node[node].type_].attrs_ is None:
#                         attrs = {}
#                     else:
#                         attrs = rand_attrs(dict_sub(env.metamodel_.node[env.node[node].type_].attrs_,
#                                             env.node[node].attrs_))

#                 op = add_req(op, " '%s'" % node)
#                 op = add_req(op, " "+str(attrs))

#                 if attrs == {}:
#                     continue

#                 env.add_node_attrs(node, attrs)
#                 trans.append(op)
#             elif op == "ADD_EDGE_ATTRS":
#                 n1, n2 = pick_edge()
#                 if n1 is None or n2 is None:
#                     continue
#                 if env.metamodel_ is None:
#                     attrs = {}
#                 else:
#                     attrs = rand_attrs(dict_sub(
#                         env.metamodel_.get_edge(
#                             env.node[n1].type_,
#                             env.node[n2].type_),
#                         env.get_edge(n1, n2)
#                         )
#                     )

#                 op = add_req(op, " '%s' '%s'" % (n1,n2))
#                 op = add_req(op, " "+str(attrs))

#                 if attrs == {}:
#                     continue

#                 env.add_edge_attrs(n1, n2, attrs)
#                 trans.append(op)
#             elif op == "DELETE_NODE_ATTRS":
#                 node = pick_node()
#                 if node is None:
#                     continue
#                 attrs = pick_attrs_from(node)

#                 if attrs == {} or attrs is None:
#                     continue

#                 op = add_req(op, " '%s'" % node)
#                 op = add_req(op, " "+str(attrs))

#                 env.remove_node_attrs(node, attrs)
#                 trans.append(op)
#             elif op == "DELETE_EDGE_ATTRS":
#                 n1, n2 = pick_edge()
#                 if n1 is None or n2 is None:
#                     continue
#                 attrs = pick_edge_attrs_from(n1, n2)

#                 if attrs == {} or attrs is None:
#                     continue

#                 op = add_req(op, " '%s' '%s'" % (n1,n2))
#                 op = add_req(op, " "+str(attrs))

#                 env.remove_edge_attrs(n1, n2, attrs)
#                 trans.append(op)
#             else:
#                 raise ValueError(
#                     "Unknown action"
#                 )

#         return ".\n".join(trans)+"."
