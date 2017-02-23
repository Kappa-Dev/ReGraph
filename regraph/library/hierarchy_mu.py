"""Hierarchy with mu-calculus verification methods """
from regraph.library.hierarchy import Hierarchy
from regraph.library.mu import parse_formula
from lrparsing import ParseError


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
    """ extends the hierarchy class with mu-calculus functionalities """

    def __init__(self):
        super().__init__()

    def check(self, graph_id, parent_id, typing):
        """ check every formulae on given ancestor """
        if "formulae" in self.node[parent_id].attrs.keys():
            current_rep = {}
            for phi_str in self.node[parent_id].attrs["formulae"]:
                try:
                    failed_nodes = _verify(phi_str["formula"],
                                           typing,
                                           self.node[graph_id].graph)
                    current_rep[phi_str["id"]] = str(failed_nodes)
                except (ValueError, ParseError) as err:
                    current_rep[phi_str["id"]] = str(err)
            return current_rep

    def check_all_ancestors(self, graph_id):
        """check every formulae on every ancestors"""
        response = {}
        for (ancestor, mapping) in self.get_ancestors(graph_id).items():
            response[ancestor] = self.check(graph_id, ancestor, mapping)
        return response
