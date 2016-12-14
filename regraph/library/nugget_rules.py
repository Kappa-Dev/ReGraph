from regraph.library.data_structures import Homomorphism
from regraph.library.rewriters import Rewriter
from copy import deepcopy
from itertools import groupby

# in_nugget:
# nugget must have metamodel


def in_nugget(nugget, variable_type):
    return [n for n in nugget.graph.nodes()
            if nugget.graph.node[n].type_ == variable_type]


class AbstractNugget():

    def __init__(self, graph, pattern_key,
                 new_meta_model=None):
        if graph.metamodel_ is None or graph.metamodel_.metamodel_ is None:
            raise ValueError("the graph must have a metamodel\
                             as well as a metametamodel")
        self.graph = graph
        self.pattern_key = pattern_key
        if new_meta_model:
            self.new_meta_model = new_meta_model
        else:
            self.new_meta_model = deepcopy(graph.metamodel_)

    def find_patterns(self):
        def variable_name_of_occurence(n):
            try:
                typeOfn = self.graph.node[n].type_
                label = min((self.graph.metamodel_.node[typeOfn]
                             .attrs_[self.pattern_key]))
            except (KeyError, TypeError):
                label = ""
            return label

        def variable_name(t):
            try:
                label = min((self.graph.metamodel_.node[t]
                             .attrs_[self.pattern_key]))
            except (KeyError, TypeError):
                label = ""
            return label

        def partition_nodes_into_occurences(nodes, variable_graph):
            all_occurences = self.graph.subgraph(nodes)
            variable = deepcopy(variable_graph)
            for n in variable.nodes():
                variable.node[n].type_ = n

            occurences = Rewriter.find_matching(all_occurences, variable, ignore_attrs=True)
            nodes_partition = [mapping.values() for mapping in occurences]
            multiset_images = [n for image in nodes_partition
                               for n in image]
            if (len(multiset_images) == len(nodes) and
               set(multiset_images) == nodes):
                return occurences
            else:
                raise ValueError("could not partition the nodes "
                                 "into suitable occurences of a variable")

        # create patterns for the variables
        nodes_groups = groupby(sorted(self.graph.metamodel_.nodes(),
                                      key=variable_name),
                               variable_name)

        variable_dict = {variable_id: self.graph.metamodel_
                                          .subgraph(list(variable_nodes))
                                          .filter_edges_by_attributes(
                                                self.pattern_key,
                                                lambda v: v == {variable_id})
                         for variable_id, variable_nodes in nodes_groups
                         if variable_id != ""}
        # group the nodes into occurences of variables
        groups_dict = {}
        for pattern_id, group in groupby(sorted(self.graph.nodes(),
                                                key=variable_name_of_occurence),
                                         variable_name_of_occurence):
            if pattern_id != "":
                groups_dict[pattern_id] =\
                  partition_nodes_into_occurences(
                        set(group),
                        variable_dict[pattern_id])
        return (groups_dict, variable_dict)

    def possible_instances(self, variable_graph):
        ag = self.graph.metamodel_
        variable = deepcopy(variable_graph)
        # for n in variable.nodes():
        #     del variable.node[n].attrs_[self.pattern_key]
        # for (n1, n2) in variable.edges():
        #     del variable.edge[n1][n2][self.pattern_key]
        matchings = Rewriter.find_matching(ag, variable, ignore_attrs=True)


        # keep instances without variable nodes
        def variable_nodes(nodes):
            return [n for n in nodes
                    if ag.node[n].attrs_ and
                    self.pattern_key in ag.node[n].attrs_.keys() and
                    ag.node[n].attrs_[self.pattern_key] != ""]
        return [m for m in matchings
                if not variable_nodes(m.values())]

    def substitute(self, nugget, variable, occurences, instance):
        # occurences are mapping from the variable to the nugget
        # an instance is a mapping from the variable to the actionGraph
        new_nugget = deepcopy(nugget)
        for occ in occurences:
            for (source, target) in occ.items():
                new_nugget.node[target].type_ = instance[source]
        # we correct the meta model
        for (n1, n2) in new_nugget.edges():
            tn1 = new_nugget.node[n1].type_
            tn2 = new_nugget.node[n2].type_
            if not self.new_meta_model.exists_edge(tn1, tn2):
                self.new_meta_model.add_edge(tn1, tn2)
        new_nugget.metamodel_ = self.new_meta_model
        for occ in occurences:
            for (source, target) in occ.items():
                mapping = {target:str(target)+"_"+str(instance[source])}
                new_nugget.myRelabelNode(target,str(target)+"_"+str(instance[source]))
        return new_nugget

    def unfold_variable(self, nugget, variable, occurences, instances):
        return [self.substitute(nugget, variable, occurences, i)
                for i in instances]

    def unfold_variables(self):
        (group_dict, variable_dict) = self.find_patterns()
        nuggets = [self.graph]
        for (variable_id, occurences) in group_dict.items():
            new_nuggets = []
            for nug in nuggets:
                new_nuggets += self.unfold_variable(
                       nug, variable_dict[variable_id],
                       occurences,
                       self.possible_instances(variable_dict[variable_id]))
            nuggets = new_nuggets
        return (nuggets, self.new_meta_model)


class AbstractRule():
    def __init__(self, rule, pattern_key, new_metamodel=None):
        if new_metamodel is None:
            self.new_metamodel = rule.L.metamodel_
        else:
            self.new_metamodel = new_metamodel
        self.pattern_key = pattern_key
        self.transformer = rule
        self.variable_nodes = {}
        self.variable_types = {}
        self.check_rule()

    def check_rule(self):
        rule = self.transformer
        if not Homomorphism(rule.P, rule.R, rule.P_R_dict).is_monic():
            raise ValueError("the right morphism of abstract"
                             " nugget is not monic")
        L = self.transformer.L

        def is_variable_node(n):
            type_of_n = L.node[n].type_
            try:
                return L.metamodel_.node[type_of_n].attrs_[self.pattern_key]
            except (KeyError, TypeError):
                return False

        self.variable_nodes = {n for n in L.nodes() if is_variable_node(n)}
        if (not set(self.transformer.P_L_dict.values())
                .issubset(self.variable_nodes)):
            raise ValueError("There should not be a non variable node in P")

        def variable_type(t):
            try:
                return self.new_metamodel.node[t].attrs_[self.pattern_key]
            except (KeyError, TypeError):
                return False

        self.variable_types = {n for n in self.new_metamodel.nodes()
                               if variable_type(n)}

    def get_matchings(self):
        pattern = deepcopy(self.transformer.L)
        for n in pattern.nodes():
            typeOfn = pattern.node[n].type_
            pattern.node[n].type_ = pattern.metamodel_.node[typeOfn].type_
        instances = Rewriter.find_matching(self.new_metamodel, pattern)
        print(instances)

        def verify_matching(matching):
            for n in set(pattern.nodes()) - self.variable_nodes:
                if matching[n] != self.transformer.L.node[n].type_:
                    return False
            print(self.variable_types)
            print(set(matching.values()))
            if (set(matching.values()) & self.variable_types) != set():
                return False
            return True

        return [i for i in instances if verify_matching(i)]

    def get_nugget(self, matching):
        new_nugget = deepcopy(self.transformer.R)
        for n in self.transformer.P.nodes():
            new_nugget.node[self.transformer.P_R_dict[n]].type_ =\
                                    matching[self.transformer.P_L_dict[n]]

        # we correct the meta model
        for (n1, n2) in new_nugget.edges():
            tn1 = new_nugget.node[n1].type_
            tn2 = new_nugget.node[n2].type_
            if not self.new_metamodel.exists_edge(tn1, tn2):
                self.new_metamodel.add_edge(tn1, tn2)
        new_nugget.metamodel_ = self.new_metamodel
        for n in self.transformer.P.nodes():
                new_nugget.myRelabelNode(
                    self.transformer.P_R_dict[n],
                    str(self.transformer.P_R_dict[n]) +
                    "_" +
                    str(matching[self.transformer.P_L_dict[n]]))
        return new_nugget

    def get_nuggets(self):
        matchings = self.get_matchings()
        return [self.get_nugget(m) for m in matchings]


class AbstractRules():
    # pre: metamodels must be the same
    def __init__(self, rules, pattern_key):
        if rules:
            self.shared_metamodel = rules[0][1].L.metamodel_
        self.abstract_rules = [(name, AbstractRule(rule, pattern_key,
                                                   self.shared_metamodel))
                               for (name, rule) in rules]

    def unfold_once(self):
        all_nuggets = []
        for (name, ARule) in self.abstract_rules:
            nuggets = ARule.get_nuggets()
            all_nuggets.append((name, nuggets))
        return all_nuggets

    def fixed_point(self):
        while True:
            ag = deepcopy(self.shared_metamodel)
            nuggets = self.unfold_once()
            if ag == self.shared_metamodel:
                return (ag, nuggets)

class AbstractNuggets():
    # pre: metamodels must be the same
    def __init__(self, nuggets, pattern_key):
        if nuggets:
            self.shared_metamodel = nuggets[0].metamodel_
        self.abstract_nuggets = [AbstractNugget(nug, pattern_key,
                                                self.shared_metamodel)
                                 for nug in nuggets]
        for ANug in self.abstract_nuggets:
            ANug.graph.metamodel = self.shared_metamodel

    def unfold_once(self):
        all_nuggets = []
        for ANug in self.abstract_nuggets:
            (nuggets, _) = ANug.unfold_variables()
            all_nuggets += nuggets
        return all_nuggets

    def fixed_point(self):
        while True:
            ag = deepcopy(self.shared_metamodel)
            nuggets = self.unfold_once()
            if ag == self.shared_metamodel:
                return (ag, nuggets)


