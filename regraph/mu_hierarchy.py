from lrparsing import ParseError

from regraph.hierarchy import Hierarchy, AttributeContainter
from regraph.mu import parse_formula


def _verify(phi_str, current_typing, graph):
    phi = parse_formula(phi_str)
    const_names = phi.constants()
    constants = {const_name: (lambda n, const_name=const_name:
                              (str(current_typing[n]).lower() ==
                               const_name.lower()))
                 for const_name in const_names}
    relations = {
        "Adj": graph.__getitem__,
        "Suc": graph.successors,
        "Pre": graph.predecessors}

    res = phi.evaluate(graph.nodes(), relations, constants)
    return [n for (n, v) in res.items() if not v]


class MuHierarchy(Hierarchy):
    """Hierarchy with mu-calculus verification methods.

    Extends the hierarchy class with mu-calculus functionality.
    """

    def check(self, graph_id, parent_id, typing):
        """Check every formulae on given ancestor."""
        if "formulae" in self.node[parent_id].attrs.keys():
            current_rep = {}
            for formula_id, formula in self.node[parent_id].attrs["formulae"]:
                try:
                    failed_nodes = _verify(formula,
                                           typing,
                                           self.node[graph_id].graph)
                    current_rep[formula_id] = str(failed_nodes)
                except (ValueError, ParseError) as err:
                    current_rep[formula_id] = str(err)
            return current_rep

    def check_all_ancestors(self, graph_id):
        """Check every formulae on every ancestors."""
        response = {}
        for (ancestor, mapping) in self.get_ancestors(graph_id).items():
            rep = self.check(graph_id, ancestor, mapping)
            if rep is not None:
                response[ancestor] = rep
        return response


class MuContainer(AttributeContainter):
    """."""
    pass


class MuGraphNode(MuContainer):
    """Constraints containing graph node."""

    def __init__(self, graph, attrs=None, formulae=None):
        """Init constraints containing graph node."""
        self.graph = graph
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        if formulae:
            self.formulae = formulae
        else:
            self.formulae = list()
        return

    # def __eq__(self, other):
    #     """Equality operator between two MuGraphNodes."""
    #     return isinstance(other, MuGraphNode) and\
    #         equal(self.graph, other.graph)

    # def __ne__(self, other):
    #     return not (self == other)


class NewMuHierarchy(Hierarchy):
    """Hierarchy with mu-calculus verification methods.

    Extends the hierarchy class with mu-calculus functionality.
    """

    def add_graph(self, graph_id, graph_obj, attrs=None, formulae=None):
        """Add a new graph to the hierarchy."""

    def add_constraints(self, graph_id, formula):
        """Add constraints to a graph node."""
        pass

    def check(self, graph_id, parent_id, typing):
        """Check every formulae on given ancestor."""

    def check_all_ancestors(self, graph_id):
        """Check every formulae on every ancestors."""
