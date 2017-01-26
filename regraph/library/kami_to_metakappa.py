import copy
from regraph.library.data_structures import TypedDiGraph
from regraph.library.rewriters import Rewriter


def link_states(self):
    for nugget in self.subCmds.values():
        nug = nugget.graph
        nug_copy = copy.deepcopy(nug)
        while True:
            for n in nug_copy.nodes():
                ag_node = nug.node[n].type_
                if (self.graph.node[ag_node].type_ in ["state", "region", "residue"] and
                    not nug.neighbors(n)):
                    ag_components = self.graph.neighbors(ag_node)
                    if len(ag_components) != 1:
                        raise ValueError("a state must have exaclty one "
                                        "associated component")
                    ag_component = ag_components[0]
                    nug_components = [c for c in nug.nodes()
                                    if nug.node[c].type_ == ag_component]
                    if len(nug_components) > 1:
                        print("components", nug_components)
                        print("name", nugget.name)
                        raise ValueError("a state cannot be associated "
                                        "to a component")
                    if len(nug_components) == 0:
                        comp_name = "comp_{}".format(n)
                        nug.add_node(comp_name, ag_component)
                        nug.add_edge(n, comp_name)
                    else:
                        nug.add_edge(n, nug_components[0])
            if nug_copy == nug:
                break
            else:
                nug_copy = copy.deepcopy(nug)





    # self.graph must be typed by kami metamodel
def to_kappa_like(self):
    from regraph.library.graph_hierarchy import Hierarchy 

    contact_map_com = Hierarchy(self.name+"_CM", None)
    contact_map = copy.deepcopy(self.graph)
    contact_map.metamodel_ = None
    #contact_map_com.graph = contact_map
    for nugget in self.subCmds.values():
        new_nugget = Hierarchy(nugget.name, None)
        new_nugget.graph = copy.deepcopy(nugget.graph)
        new_nugget.graph.metamodel_ = None
        contact_map_com.subCmds[nugget.name] = new_nugget
    
    # add "is_free" node to contact_map
    
    if "is_FREE" not in contact_map.node.keys():
        contact_map.add_node("is_FREE","is_FREE")
    if "t_FREE" not in contact_map.node.keys():
         contact_map.add_node("t_FREE","t_FREE")
    contact_map.add_edge("t_FREE","is_FREE")

    # add input for binds
    bnd_pattern = TypedDiGraph(self.graph.metamodel_)
    bnd_pattern.add_nodes_from([("b", "bnd"), ("l", "locus")])
    bnd_pattern.add_edges_from([("l", "b")])
    matchings = Rewriter.find_matching(self.graph, bnd_pattern)
    for (i, mat) in enumerate(matchings):
        # rewrite the action graph
        new_s_bnd = "s_bnd_{}".format(i)
        contact_map.add_node(new_s_bnd, "s_BND")
        # contact_map.remove_edge(mat["l"], mat["b"])
        contact_map.add_edge(mat["l"], new_s_bnd)
        contact_map.add_edge(new_s_bnd, mat["b"])
        contact_map.add_edge("t_FREE",mat["l"])
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from([("b", mat["b"]), ("l", mat["l"])])
        nug_pattern.add_edges_from([("l", "b")])
        # we rewrite the nuggets
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                is_free_name = "is_free_tmp_bnd_{}_{}".format(i,j)
                t_free_name = "t_free_tmp_bnd_{}_{}".format(i,j)
                if is_free_name not in nugget.graph.node.keys():
                    nugget.graph.add_node(is_free_name, "is_FREE")
                if t_free_name not in nugget.graph.node.keys():
                    nugget.graph.add_node(t_free_name, "t_FREE")
                nugget.graph.add_edge(t_free_name, is_free_name)
                new_s_bnd = "s_bnd_{}_{}".format(i, j)
                nugget.graph.add_node(new_s_bnd, "s_bnd_{}".format(i))
                # nugget.graph.remove_edge(nug_matching["l"],
                #                          nug_matching["b"])
                nugget.graph.add_edge(nug_matching["l"], new_s_bnd)
                nugget.graph.add_edge(new_s_bnd, nug_matching["b"])
                nugget.graph.add_edge(t_free_name,nug_matching["l"])


    # add input for free
    free_pattern = TypedDiGraph(self.graph.metamodel_)
    free_pattern.add_nodes_from([("f", "is_free"), ("l", "locus")])
    free_pattern.add_edges_from([("l", "f")])
    matchings = Rewriter.find_matching(self.graph, free_pattern)
    for (i, mat) in enumerate(matchings):
        # rewrite the action graph
        new_t_free = "t_free_{}".format(i)
        contact_map.add_node(new_t_free, "t_FREE")
        # contact_map.remove_edge(mat["l"], mat["b"])
        contact_map.add_edge(new_t_free,mat["l"])
        contact_map.add_edge(new_t_free, mat["f"])
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from([("f", mat["f"]), ("l", mat["l"])])
        nug_pattern.add_edges_from([("l", "f")])
        # we rewrite the nuggets
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                t_free = "t_free_{}_{}".format(i, j)
                nugget.graph.add_node(t_free, new_t_free)
                # nugget.graph.remove_edge(nug_matching["l"],
                #                             nug_matching["f"])
                nugget.graph.add_edge(t_free, nug_matching["l"])
                nugget.graph.add_edge(t_free, nug_matching["f"])

    # add input for mod
    ag_pattern = TypedDiGraph(self.graph.metamodel_)
    ag_pattern.add_nodes_from([("m", "mod"), ("s", "state")])
    ag_pattern.add_edges_from([("m", "s")])
    matchings = Rewriter.find_matching(self.graph, ag_pattern)
    for (i, mat) in enumerate(matchings):
        # rewrite the action graph
        new_ag_node = "t_mod_{}".format(i)
        contact_map.add_node(new_ag_node, "t_MOD")
        # contact_map.remove_edge(mat["l"], mat["b"])
        contact_map.add_edge(new_ag_node, mat["s"])
        contact_map.add_edge(new_ag_node, mat["m"])
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from([("m", mat["m"]), ("s", mat["s"])])
        nug_pattern.add_edges_from([("m", "s")])
        # we rewrite the nuggets
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                new_nug_node = "t_mod_{}_{}".format(i, j)
                nugget.graph.add_node(new_nug_node, new_ag_node)
                # nugget.graph.remove_edge(nug_matching["l"],
                #                             nug_matching["f"])
                nugget.graph.add_edge(new_nug_node, nug_matching["s"])
                nugget.graph.add_edge(new_nug_node, nug_matching["m"])

    # add input for brk
    brk_pattern = TypedDiGraph(self.graph.metamodel_)
    brk_pattern.add_nodes_from([("b", "brk"), ("l", "locus")])
    brk_pattern.add_edges_from([("l", "b")])
    matchings = Rewriter.find_matching(self.graph, brk_pattern)
    for (i, mat) in enumerate(matchings):
        # rewrite the action graph
        new_t_brk = "t_brk_{}".format(i)
        contact_map.add_node(new_t_brk, "t_BRK")
        # contact_map.remove_edge(mat["l"], mat["b"])
        contact_map.add_edge(new_t_brk, mat["l"])
        contact_map.add_edge(new_t_brk, mat["b"])
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from([("b", mat["b"]), ("l", mat["l"])])
        nug_pattern.add_edges_from([("l", "b")])
        contact_map.add_edge("t_FREE",mat["l"])
        # we rewrite the nuggets
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                # is_free_name = "is_free_tmp_brk_{}_{}".format(i,j)
                # t_free_name = "t_free_tmp_brk_{}_{}".format(i,j)
                # if is_free_name not in nugget.graph.node.keys():
                #     nugget.graph.add_node(is_free_name, "is_FREE")
                # if t_free_name not in nugget.graph.node.keys():
                #     nugget.graph.add_node(t_free_name, "t_FREE")
                # nugget.graph.add_edge(t_free_name, is_free_name)
                t_brk = "t_brk_{}_{}".format(i, j)
                nugget.graph.add_node(t_brk, new_t_brk)
                nugget.graph.add_edge(t_brk, nug_matching["l"])
                nugget.graph.add_edge(t_brk, nug_matching["b"])
                # nugget.graph.add_edge(t_free_name,nug_matching["l"])


    # add input for is_bnd
    is_bnd_pattern = TypedDiGraph(self.graph.metamodel_)
    is_bnd_pattern.add_nodes_from([("b", "is_bnd"), ("l", "locus")])
    is_bnd_pattern.add_edges_from([("l", "b")])
    matchings = Rewriter.find_matching(self.graph, is_bnd_pattern)
    for (i, mat) in enumerate(matchings):
        # rewrite the action graph
        new_is_bnd = "is_bnd_{}".format(i)
        contact_map.add_node(new_is_bnd, "s_BND")
        # contact_map.remove_edge(mat["l"], mat["b"])
        contact_map.add_edge(mat["l"], new_is_bnd)
        contact_map.add_edge(new_is_bnd, mat["b"])
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from([("b", mat["b"]), ("l", mat["l"])])
        nug_pattern.add_edges_from([("l", "b")])
        # we rewrite the nuggets
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                is_bnd = "is_bnd_{}_{}".format(i, j)
                nugget.graph.add_node(is_bnd, new_is_bnd)
                # nugget.graph.remove_edge(nug_matching["l"],
                #                          nug_matching["b"])
                nugget.graph.add_edge(nug_matching["l"], is_bnd)
                nugget.graph.add_edge(is_bnd, nug_matching["b"])

    ## move loci to agents
    # build the pattern for action graph
    region_pattern = TypedDiGraph(self.graph.metamodel_)
    region_pattern.add_nodes_from(
        [("r", "region"), ("l", "locus"), ("a", "agent")])
    region_pattern.add_edges_from(
        [("l", "r"), ("r", "a")])
    matchings = Rewriter.find_matching(self.graph, region_pattern)
    for mat in matchings:
        contact_map.add_edge(mat["l"], mat["a"])
        # build the pattern to look for in nuggets
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from(
            [("r", mat["r"]), ("l", mat["l"]), ("a", mat["a"])])
        nug_pattern.add_edges_from(
            [("l", "r"), ("r", "a")])
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for nug_matching in nug_matchings:
                nugget.graph.add_edge(nug_matching["l"], nug_matching["a"])

    # SYN
    ag_pattern = TypedDiGraph(self.graph.metamodel_)
    ag_pattern.add_nodes_from(
        [("s", "syn"), ("a", "agent")])
    ag_pattern.add_edges_from(
        [("s", "a")])
    matchings = Rewriter.find_matching(self.graph, ag_pattern)
    for (i, mat) in enumerate(matchings):

        # modify action graph
        ag_node_name = "syn_{}_{}".format(mat["a"], i)
        contact_map.add_node(ag_node_name, "t_SD")
        contact_map.add_edge(ag_node_name, mat["s"])
        contact_map.add_edge(ag_node_name, mat["a"])

        # modify nuggets
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from(
            [("s", mat["s"]), ("a", mat["a"])])
        nug_pattern.add_edges_from(
            [("s", "a")])
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                node_name = "syn_{}_{}_{}".format(nug_matching["a"],
                                                    i, j)
                nugget.graph.add_node(node_name, ag_node_name)
                nugget.graph.add_edge(node_name, nug_matching["s"])
                nugget.graph.add_edge(node_name, nug_matching["a"])

    # DEG
    ag_pattern = TypedDiGraph(self.graph.metamodel_)
    ag_pattern.add_nodes_from(
        [("d", "deg"), ("a", "agent")])
    ag_pattern.add_edges_from(
        [("d", "a")])
    matchings = Rewriter.find_matching(self.graph, ag_pattern)
    for (i, mat) in enumerate(matchings):

        # modify action graph
        ag_node_name = "deg_{}_{}".format(mat["a"], i)
        contact_map.add_node(ag_node_name, "s_SD")
        contact_map.add_edge(ag_node_name, mat["d"])
        contact_map.add_edge(mat["a"], ag_node_name)

        # modify nuggets
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from(
            [("d", mat["d"]), ("a", mat["a"])])
        nug_pattern.add_edges_from(
            [("d", "a")])
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                node_name = "deg_{}_{}_{}".format(nug_matching["a"],
                                                    i, j)
                nugget.graph.add_node(node_name, ag_node_name)
                nugget.graph.add_edge(node_name, nug_matching["d"])
                nugget.graph.add_edge(nug_matching["a"], node_name)
    # create sites for the states
    # states associated to agents
    sites_pattern = TypedDiGraph(self.graph.metamodel_)
    sites_pattern.add_nodes_from(
        [("s", "state"), ("a", "agent")])
    sites_pattern.add_edges_from(
        [("s", "a")])
    matchings = Rewriter.find_matching(self.graph, sites_pattern)
    for (i, mat) in enumerate(matchings):

        # modify action graph
        new_node_name = "{}_state_{}".format(mat["a"], i)
        contact_map.add_node(new_node_name, "site")
        contact_map.add_edge(mat["s"], new_node_name)
        contact_map.add_edge(new_node_name, mat["a"])

        # modify nuggets
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from(
            [("s", mat["s"]), ("a", mat["a"])])
        nug_pattern.add_edges_from(
            [("s", "a")])
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                node_name = "{}_state_{}_{}".format(nug_matching["a"],
                                                    i, j)
                nugget.graph.add_node(node_name, new_node_name)
                nugget.graph.add_edge(nug_matching["s"], node_name)
                nugget.graph.add_edge(node_name, nug_matching["a"])

    # states associated to regions
    sites_region_pattern = TypedDiGraph(self.graph.metamodel_)
    sites_region_pattern.add_nodes_from(
        [("s", "state"), ("r", "region"), ("a", "agent")])
    sites_region_pattern.add_edges_from(
        [("s", "r"), ("r", "a")])
    matchings = Rewriter.find_matching(self.graph, sites_region_pattern)
    for (i, mat) in enumerate(matchings):

        # modify action graph
        new_node_name = "{}_state_{}".format(mat["r"], i)
        contact_map.add_node(new_node_name, "site")
        contact_map.add_edge(mat["s"], new_node_name)
        contact_map.add_edge(new_node_name, mat["a"])

        # modify nuggets
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from(
            [("s", mat["s"]), ("a", mat["a"]), ("r", mat["r"])])
        nug_pattern.add_edges_from(
            [("s", "r"), ("r", "a")])
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                node_name = "{}_state_{}_{}".format(nug_matching["r"],
                                                    i, j)
                nugget.graph.add_node(node_name, new_node_name)
                nugget.graph.add_edge(nug_matching["s"], node_name)
                nugget.graph.add_edge(node_name, nug_matching["a"])

    # states associated to residues
    sites_residue_pattern = TypedDiGraph(self.graph.metamodel_)
    sites_residue_pattern.add_nodes_from(
        [("s", "state"), ("r", "residue"), ("a", "agent")])
    sites_residue_pattern.add_edges_from(
        [("s", "r"), ("r", "a")])
    matchings = Rewriter.find_matching(self.graph, sites_residue_pattern)
    for (i, mat) in enumerate(matchings):

        # modify action graph
        new_node_name = "{}_state_{}".format(mat["r"], i)
        contact_map.add_node(new_node_name, "site")
        contact_map.add_edge(mat["s"], new_node_name)
        contact_map.add_edge(new_node_name, mat["a"])

        # modify nuggets
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from(
            [("s", mat["s"]), ("a", mat["a"]), ("r", mat["r"])])
        nug_pattern.add_edges_from(
            [("s", "r"), ("r", "a")])
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                node_name = "{}_state_{}_{}".format(nug_matching["r"],
                                                    i, j)
                nugget.graph.add_node(node_name, new_node_name)
                nugget.graph.add_edge(nug_matching["s"], node_name)
                nugget.graph.add_edge(node_name, nug_matching["a"])


    # states associated to residues associated to agent
    sites_residue_pattern = TypedDiGraph(self.graph.metamodel_)
    sites_residue_pattern.add_nodes_from(
        [("s", "state"), ("r", "residue"),("reg","region"), ("a", "agent")])
    sites_residue_pattern.add_edges_from(
        [("s", "r"), ("r", "reg"), ("reg","a")])
    matchings = Rewriter.find_matching(self.graph, sites_residue_pattern)
    for (i, mat) in enumerate(matchings):

        # modify action graph
        new_node_name = "{}_{}_{}".format(mat["r"],mat["s"], i)
        contact_map.add_node(new_node_name, "site")
        contact_map.add_edge(mat["s"], new_node_name)
        contact_map.add_edge(new_node_name, mat["a"])

        # modify nuggets
        nug_pattern = TypedDiGraph(self.graph)
        nug_pattern.add_nodes_from(
            [("s", mat["s"]), ("a", mat["a"]),("reg",mat["reg"]), ("r", mat["r"])])
        nug_pattern.add_edges_from(
            [("s", "r"), ("r", "reg"), ("reg","a")])
        for nugget in contact_map_com.subCmds.values():
            nug_matchings = Rewriter.find_matching(nugget.graph,
                                                    nug_pattern)
            for (j, nug_matching) in enumerate(nug_matchings):
                node_name = "{}_{}_{}_{}".format(nug_matching["r"], nug_matching["s"],
                                                    i, j)
                nugget.graph.add_node(node_name, new_node_name)
                nugget.graph.add_edge(nug_matching["s"], node_name)
                nugget.graph.add_edge(node_name, nug_matching["a"])

    # change and remove old types and edges
    contact_map_com.graph = contact_map
    for nugget in contact_map_com.subCmds.values():
        nugget.parent = contact_map_com
        nugget.graph.parent = contact_map_com.graph
    to_delete = []
    for n in contact_map.nodes():
        type_of_n = contact_map.node[n].type_
        if type_of_n == "locus":
            contact_map.node[n].type_ = "site"
        if type_of_n == "mod":
            contact_map.node[n].type_ = "MOD"
        if type_of_n == "bnd":
            contact_map.node[n].type_ = "BND"
        if type_of_n == "syn" or type_of_n == "deg":
            contact_map.node[n].type_ = "SYN/DEG"
        if type_of_n == "brk":
            contact_map.node[n].type_ = "BRK"
        if type_of_n == "is_free":
            contact_map.node[n].type_ = "is_FREE"
        if type_of_n == "is_bnd":
            contact_map.node[n].type_ = "is_BND"
        if type_of_n == "region" or type_of_n == "residue":
            to_delete.append(n)
    for n in to_delete:
        contact_map_com._do_rm_node_force_not_catched(n)
    to_delete = []
    for (n1, n2) in contact_map.edges():
        tn1 = contact_map.node[n1].type_
        tn2 = contact_map.node[n2].type_
        if ((tn1, tn2) == ("site", "BND") or
            (tn1, tn2) == ("site", "BRK") or
            (tn1, tn2) == ("site", "is_BND") or
            (tn1, tn2) == ("state", "agent") or
            (tn1, tn2) == ("MOD", "site") or
            (tn1, tn2) == ("MOD", "state") or
            (tn1, tn2) == ("SYN/DEG", "agent") or
            (tn1, tn2) == ("site", "is_FREE")):
            to_delete.append((n1, n2))
    for (n1, n2) in to_delete:
        contact_map_com._do_rm_edge_uncatched(n1, n2, force=True)
    #link_states(self)
    return contact_map_com

