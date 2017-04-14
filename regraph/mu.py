""" mu calculus """


# import regraph

import lrparsing
from lrparsing import Keyword, List, Prio, Ref, Token

from regraph.exceptions import ParsingError, FormulaError


class MuParser(lrparsing.Grammar):
    '''Parse a mu-calculus formula'''

    class T(lrparsing.TokenRegistry):
        integer = Token(re="[0-9]+")
        integer["key"] = "I'm a mapping!"
        ident = Token(re="[A-Z][A-Za-z_0-9]*")
        operator = Token(re="[a-z][A-Za-z_0-9]*")

    r_expr = Ref("r_expr")
    r_mu = Keyword("mu") + " " + T.ident + "(" + r_expr + ")"
    r_not = Keyword("not")+" " + r_expr
    r_or = Keyword('or')+'(' + List(r_expr, ',') + ')'
    r_var = Keyword('var')+"(" + T.ident + ")"
    r_cnt = Keyword("cnt") + "(" + T.ident + ")"
    r_geq = "<" + T.integer + "<=" + T.ident + ">" + r_expr
    r_next = "<" + T.ident + ">" + r_expr

    r_expr = Prio(r_mu | r_not | r_or | r_var | r_cnt | r_geq | r_next)
    START = r_expr


def parsed_tree_to_formula(parsed_tree):
    """ build a Formula object from the result of parsing """

    if parsed_tree[0].name == "START" or parsed_tree[0].name == "r_expr":
        rep = parsed_tree_to_formula(parsed_tree[1])
    elif parsed_tree[0].name == "r_mu":
        variable_name = parsed_tree[3][1]
        phi = parsed_tree_to_formula(parsed_tree[5])
        rep = Mu(variable_name, phi)
    elif parsed_tree[0].name == "r_or":
        sub_formulas = parsed_tree[3::2]
        rep = Or([parsed_tree_to_formula(f) for f in sub_formulas])
    elif parsed_tree[0].name == "r_var":
        variable_name = parsed_tree[3][1]
        rep = Var(variable_name)
    elif parsed_tree[0].name == "r_cnt":
        variable_name = parsed_tree[3][1]
        rep = Cnt(variable_name)
    elif parsed_tree[0].name == "r_next":
        relation_name = parsed_tree[2][1]
        sub_formula = parsed_tree_to_formula(parsed_tree[4])
        rep = Geq(1, relation_name, sub_formula)
    elif parsed_tree[0].name == "r_geq":
        lower_bound = parsed_tree[2][1]
        relation_name = parsed_tree[4][1]
        sub_formula = parsed_tree_to_formula(parsed_tree[6])
        rep = Geq(int(lower_bound), relation_name, sub_formula)
    elif parsed_tree[0].name == "r_not":
        sub_formula = parsed_tree_to_formula(parsed_tree[3])
        rep = Not(sub_formula)
    else:
        raise ParsingError("Parsing of formula failed")

    return rep


def parse_formula(string_formula):
    """parse a string and return a Formula object"""
    return parsed_tree_to_formula(MuParser.parse(string_formula))


class Formula():
    """ abstract formula class
        precondition: variable names are unique """

    def label(self, pos, counter, env):
        """ labels the formula with fixed point structure """
        pass

    def start_label(self):
        """ initalize the label function """
        self.label(True, 0, {})

    def evaluate(self, nodes, relation, constants):
        """ evaluate the formula on a graph
        nodes     : the nodes of the graph
        relations : valuations for the relation names of the formula
        constants : valuations for the constant names of the formula """
        return self.evaluate_aux({}, nodes, relation, constants)

    def evaluate_aux(self, env, nodes, relations, constants):
        """auxiliary function for evaluate"""
        pass

    def is_closed(self):
        """todo test if a formula is closed"""
        pass

    def is_well_formed(self):
        """todo test if a formula is well_formed"""
        pass

    def constants(self):
        """returns the names of the constants of the formula"""


class Mu(Formula):
    """ fixed point formula"""

    def __init__(self, variable_name, sub_formula):
        self.name = variable_name
        self.sub_formulas = [sub_formula]
        self.block_label = None

    def __str__(self):
        if self.block_label is not None:
            return "mu {}_{}({})".format(self.name, self.block_label,
                                         self.sub_formulas[0])
        else:
            return "mu {}({})".format(self.name, self.sub_formulas[0])

    def label(self, pos, l, env):
        if pos:
            self.block_label = l
            env[self.name] = l
            self.sub_formulas[0].label(True, l, env)
        else:
            self.block_label = l+1
            env[self.name] = l+1
            self.sub_formulas[0].label(True, l+1, env)

    def evaluate_aux(self, env, nodes, relations, constants):
        old = {n: False for n in nodes}
        change_happended = True
        while change_happended:
            env[self.name] = old
            new = self.sub_formulas[0].evaluate_aux(env, nodes, relations,
                                                constants)
            change_happended = old != new
            old = new
        return old

    def constants(self):
        return self.sub_formulas[0].constants()


class Or(Formula):
    """ Disjunction """

    def __init__(self, sub_formulas):
        self.sub_formulas = sub_formulas

    def __str__(self):
        return "or({})".format(",".join([str(s) for s in self.sub_formulas]))

    def label(self, *args):
        for sub in self.sub_formulas:
            sub.label(*args)

    def evaluate_aux(self, env, nodes, relations, constants):
        sub_vals = [subf.evaluate_aux(env, nodes, relations, constants)
                    for subf in self.sub_formulas]
        val = {n: False for n in nodes}
        for node in nodes:
            for sub_val in sub_vals:
                if sub_val[node]:
                    val[node] = True
                    break
        return val

    def constants(self):
        return set.union(*[sub.constants() for sub in self.sub_formulas])


class Not(Formula):
    """ Negation """
    def __init__(self, sub_formula):
        self.sub_formulas = [sub_formula]

    def __str__(self):
        return "not({})".format(self.sub_formulas[0])

    def label(self, pos, *args):
        self.sub_formulas[0].label(not pos, *args)

    def evaluate_aux(self, env, nodes, relations, constants):
        rep = self.sub_formulas[0].evaluate_aux(
            env, nodes, relations, constants)
        for node, value in rep.items():
            rep[node] = not value
        return rep

    def constants(self):
        return self.sub_formulas[0].constants()


class Var(Formula):
    """ Variable """
    def __init__(self, name):
        self.name = name
        self.block_label = None

    def __str__(self):
        if self.block_label is not None:
            return "var({}_{})".format(self.name, self.block_label)

        else:
            return "var({})".format(self.name)

    def label(self, pos, counter, env):
        self.block_label = env[self.name]

    def evaluate_aux(self, env, nodes, relations, constants):
        return env[self.name]

    def constants(self):
        return set()


class Cnt(Formula):
    """ Constant """
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "cnt({})".format(self.name)

    def label(self, *args):
        pass

    def evaluate_aux(self, env, nodes, relations, constants):
        if self.name not in constants.keys():
            raise FormulaError(
                "Constant %s is not in the environment" %
                self.name
            )
        test = constants[self.name]
        return {n: test(n) for n in nodes}

    def constants(self):
        return {self.name}


class Geq(Formula):
    """ dynamic operator"""
    def __init__(self, lower_bound, rel_name, sub_formula):
        if lower_bound < 1:
            raise FormulaError(
                "Lower bound must be greater or equal to 1"
            )
        self.lower_bound = lower_bound
        self.name = rel_name
        self.sub_formulas = [sub_formula]

    def __str__(self):
        return "<{}<={}>{}".format(self.lower_bound, self.name,
                                   self.sub_formulas[0])

    def label(self, *args):
        self.sub_formulas[0].label(*args)

    def evaluate_aux(self, env, nodes, relations, constants):
        if self.name not in relations.keys():
            raise FormulaError(
                "Relation %s is not in the environment" %
                self.name
            )

        successors = relations[self.name]
        rep = self.sub_formulas[0].evaluate_aux(env, nodes, relations, constants)

        def valid_node(node):
            """ test if node has enough successors that evaluate to true"""
            return len([n2 for n2 in successors(node)
                        if rep[n2]]) >= self.lower_bound

        return {n: valid_node(n) for n in nodes}

    def constants(self):
        return self.sub_formulas[0].constants()

# PARSE_TREE = MuParser.parse("not mu TOTO(or(var(TOTO),<R>cnt(Action),"
#                             "<2<=R>not mu Y(or(cnt(TOTO),var(Y)))))")

# PARSE_TREE = MuParser.parse("mu TOTO(or(var(TOTO),<R>cnt(Action),"
#                               "<2<=R>not mu Y(or(var(TOTO),var(Y)))))")
# PARSE_TREE = MuParser.parse("mu TOTO(or(var(TOTO),<R>cnt(Action),"
#                               "<2<=R>not cnt(Agent)))")
# PARSE_TREE = MuParser.parse("mu X(or())")


# A = parse_formula("not mu TOTO(or(var(TOTO),<R>cnt(Action),"
#                   "<2<=R>not mu Y(or(cnt(TOTO),var(Y)))))")
# print(A)
# A.start_label()
# print(A)
