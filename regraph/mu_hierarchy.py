"""Hierarchy whose graph nodes are equipped with constraints."""
from regraph.networkx.hierarchy import NetworkXHierarchy
from regraph.networkx.components import (AttributeContainter,
                                         RuleNode,
                                         Typing,
                                         RuleTyping,
                                         GraphRelation)
from regraph.mu import parse_formula
from regraph.primitives import (equal, graph_to_json, graph_from_json)

from regraph.utils import (normalize_attrs)
from regraph.exceptions import (ParsingError, HierarchyError)


def _verify(formula, current_typing, graph):
    const_names = formula.constants()
    constants = {const_name: (lambda n, const_name=const_name:
                              (str(current_typing[n]).lower() ==
                               const_name.lower()))
                 for const_name in const_names}
    relations = {
        "Adj": graph.__getitem__,
        "Suc": graph.successors,
        "Pre": graph.predecessors}

    res = formula.evaluate(graph.nodes(), relations, constants)
    return [n for (n, v) in res.items() if not v]


class MuGraphNode(AttributeContainter):
    """Constraints containing graph node."""

    def __init__(self, graph, attrs=None, formulae=None):
        """Init constraints containing graph node."""
        self.graph = graph
        if attrs:
            normalize_attrs(attrs)
            self.attrs = attrs
        else:
            self.attrs = dict()
        if formulae:
            self.formulae = dict()
            for f_id, f_str in formulae.items():
                try:
                    formula = parse_formula(f_str)
                except ParsingError as e:
                    raise HierarchyError(
                        "Cannot create a node with mu-formulas, "
                        "formula {} is not valid: MuParser error: {}".format(
                            f_str, e))
                self.formulae[f_id] = formula
        else:
            self.formulae = dict()
        return

    def __eq__(self, other):
        """Equality operator between two MuGraphNodes."""
        return isinstance(other, MuGraphNode) and\
            equal(self.graph, other.graph)

    def __ne__(self, other):
        """Not equal test."""
        return not (self == other)

    def to_json(self):
        """Create JSON representation of the object."""
        formulae_json = dict()
        if self.formulae is not None:
            for f_id, f in self.formulae.items():
                formulae_json[f_id] = str(f)
        return {
            "graph": graph_to_json(self.graph),
            "attrs": self.attrs_to_json(),
            "formulae": formulae_json
        }

    @classmethod
    def from_json(cls, json_data, directed=True):
        """Create an object from json representation."""
        graph, attrs, formulae = cls.process_json(json_data)
        return cls(graph, attrs, formulae)

    @staticmethod
    def process_json(json_data, directed=True):
        """Get data from json representation."""
        graph = graph_from_json(json_data["graph"], directed)
        if "attrs" not in json_data.keys():
            attrs = dict()
        else:
            attrs = AttributeContainter.attrs_from_json(
                json_data["attrs"])
        formulae = json_data["formulae"]
        return graph, attrs, formulae


class MuHierarchy(NetworkXHierarchy):
    """Hierarchy with mu-calculus verification methods.

    Extends the hierarchy class with mu-calculus functionality,
    allows to add constraints expressed with mu-formulas.
    """

    def __init__(self, directed=True,
                 attrs=None,
                 graph_node_cls=MuGraphNode,
                 rule_node_cls=RuleNode,
                 graph_typing_cls=Typing,
                 rule_typing_cls=RuleTyping,
                 relation_cls=GraphRelation):
        """Init of MuHierarchy object."""
        super().__init__(directed, attrs, graph_node_cls,
                         rule_node_cls, graph_typing_cls, rule_typing_cls,
                         relation_cls)

    def add_formula(self, graph_id, formula_id, formula):
        """Add formula to a graph node."""
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Node '{}' does not exist in the hierarchy!".format(graph_id))
        if formula_id in self.node[graph_id].formulae.keys():
            raise HierarchyError(
                "Formula '{}' already exists on the node '{}'"
                "(use `update_formula` to update it)!".format(
                    formula_id, graph_id))
        try:
            self.node[graph_id].formulae[formula_id] = parse_formula(
                formula)
        except ParsingError as e:
            raise HierarchyError(
                "Cannot add a formula, formula {} is not "
                "valid: MuParser error: {}".format(
                    formula, e))

    def remove_formula(self, graph_id, formula_id):
        """Remove formula to a graph node."""
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Node '{}' does not exist in the hierarchy!".format(graph_id))
        if formula_id not in self.node[graph_id].formulae.keys():
            raise HierarchyError(
                "Formula '{}' does not exist on the node '{}'"
                "(use `update_formula` to update it)!".format(
                    formula_id, graph_id))
        del self.node[graph_id].formulae[formula_id]

    def update_formula(self, graph_id, formula_id, formula):
        """Update formula in a graph node."""
        if graph_id not in self.nodes():
            raise HierarchyError(
                "Node '{}' does not exist in the hierarchy!".format(graph_id))
        try:
            self.node[graph_id].formulae[formula_id] = parse_formula(
                formula)
        except ParsingError as e:
            raise HierarchyError(
                "Cannot update the formula '{}', formula '{}' is not "
                "valid: MuParser error: {}".format(
                    formula_id, formula, e))

    def check(self, graph_id, parent_id, typing):
        """Check every formulae on a given ancestor."""
        if self.node[parent_id].formulae is not None:
            current_rep = {}
            for formula_id, formula in self.node[parent_id].formulae.items():
                try:
                    failed_nodes = _verify(formula,
                                           typing,
                                           self.graph[graph_id])
                    current_rep[formula_id] = str(failed_nodes)

                except Exception as err:
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
