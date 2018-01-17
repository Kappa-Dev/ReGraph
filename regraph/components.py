"""Collection of graph hierarchy components.

This module contains a collection of data structures implementing
graph hierarchy's various components:

* `AttributeContainter` -- base class for objects containing
  attributes, provides an interface for different operations
  on attributes;
* `GraphNode` -- class for graph nodes of a hierarchy;
* `RuleNode` -- class for rule nodes of a hierarchy;
* `Typing` -- class for graph typing edges of a hierarchy,
  encapsulates graph homomorphism from a source graph node
  to a target graph node;
* `RuleTyping` -- class for rule typing edges of a hierarchy
  (its source node is assumed to be a rule and its target -- a graph),
  encapsulated two homomorphisms: from the left-hand side of the rule
  to the target and from the right-hand side of the rule to the target;
* `Relation` -- base class for relations in the hierarchy;
* `GraphRelation` -- class for binary symmetric relations between
  two graphs.

TODO:

* `RuleRelation`
"""
import copy

from regraph.attribute_sets import AttributeSet, FiniteSet
from regraph.category_utils import compose
from regraph.primitives import (equal,
                                graph_to_json,
                                graph_from_json)
from regraph.rules import Rule
from regraph.utils import (to_set,
                           replace_source,
                           replace_target,
                           normalize_attrs)


class AttributeContainter(object):
    """Base class for containers of attributes."""

    def attrs_to_json(self):
        """Convert attributes to json."""
        json_data = dict()
        for key, value in self.attrs.items():
            json_data[key] = value.to_json()
        return json_data

    @staticmethod
    def attrs_from_json(json_data):
        """Retrieve attrs from json-like dict."""
        attrs = dict()
        for key, value in json_data.items():
            attrs[key] = AttributeSet.from_json(value)
        return attrs

    def add_attrs(self, attrs):
        """Add attrs to the container."""
        if attrs:
            new_attrs = copy.deepcopy(attrs)
            normalize_attrs(new_attrs)
        else:
            new_attrs = dict()
        if len(self.attrs) == 0:
            self.attrs = new_attrs
        else:
            for key, value in new_attrs.items():
                if key not in self.attrs.keys():
                    self.attrs[key] = FiniteSet(value)
                else:
                    self.attrs[key] = self.attrs[key].union(value)
        return

    def remove_attrs(self, attrs):
        """Remove attributes."""
        if attrs is None:
            pass
        else:
            normalize_attrs(self.attrs)
            for key, value in attrs.items():
                if key not in self.attrs.keys():
                    pass
                else:
                    elements_to_remove = []
                    for el in to_set(value):
                        if el in self.attrs[key]:
                            elements_to_remove.append(el)
                        else:
                            pass
                    for el in elements_to_remove:
                        self.attrs[key].remove(el)

    def update_attrs(self, attrs):
        """Update attribures."""
        new_attrs = copy.deepcopy(attrs)
        if new_attrs is None:
            pass
        else:
            normalize_attrs(new_attrs)
            self.attrs = new_attrs


class GraphNode(AttributeContainter):
    """Data structure incapsulating graph in the node of the hierarchy.

    Attributes
    ----------
    graph : nx.(Di)Graph
    attrs : dict
        Dictionary with attrs of the graph node
    """

    def __init__(self, graph, attrs=None):
        """Initialize graph node with graph object and attrs."""
        self.graph = graph
        if attrs:
            if attrs is not None:
                normalize_attrs(attrs)
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def __eq__(self, other):
        """Equality of graph nodes."""
        return isinstance(other, GraphNode) and equal(self.graph, other.graph)

    def to_json(self):
        """Create a JSON representation of the object."""
        return {
            "graph": graph_to_json(self.graph),
            "attrs": self.attrs_to_json()
        }

    @classmethod
    def from_json(cls, json_data, directed=True):
        graph, attrs = cls.process_json(json_data["graph"], directed)
        return cls(graph, attrs)

    @staticmethod
    def process_json(json_data, directed=True):
        graph = graph_from_json(json_data["graph"], directed)
        if "attrs" not in json_data.keys():
            attrs = dict()
        else:
            attrs = AttributeContainter.attrs_from_json(
                json_data["attrs"])
        return graph, attrs


class RuleNode(AttributeContainter):
    """Data structure incapsulating a rule in the node of the hierarchy.

    Attributes
    ----------
    rule : regraph.rules.Rule
    attrs : dict
        Dictionary with attrs of the rule node
    """

    def __init__(self, rule, attrs=None):
        """Initialize rule with a Rule object."""
        self.rule = rule
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def __eq__(self, other):
        """Equality of rule nodes."""
        return isinstance(other, RuleNode) and self.rule == other.rule

    def __ne__(self, other):
        """Non-equality of the rule nodes."""
        return not (self == other)

    def to_json(self):
        """Create a JSON representation of the object."""
        return {
            "rule": self.rule.to_json(),
            "attrs": self.attrs_to_json()
        }

    @classmethod
    def from_json(cls, json_data, directed=True):
        rule, attrs = cls.process_json(json_data, directed)
        return cls(rule, attrs)

    @staticmethod
    def process_json(json_data, directed=True):
        rule = Rule.from_json(json_data["rule"], directed)
        if "attrs" not in json_data.keys():
            attrs = dict()
        else:
            attrs = AttributeContainter.attrs_from_json(
                json_data["attrs"])
        return rule, attrs


class Typing(AttributeContainter):
    """Data structure incapsulating a homomorphism between graphs.

    Attributes
    ----------
    mapping : dict
        Dictionary containing a map from nodes of a source graph
        to nodes of a target.
    total : bool
        Flag indication if the typing is forced to be total
    attrs : dict
        Dictionary with attrs of the typing
    """

    def __init__(self, mapping, attrs=None):
        """Initialize homomorphism."""
        self.mapping = mapping
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def is_total(self):
        """Test typing totality attribute."""
        return self.total

    def rename_source(self, old_name, new_name):
        """Rename source of typing."""
        replace_source(old_name, new_name, self.mapping)

    def rename_target(self, old_name, new_name):
        """Rename typing of typing."""
        replace_target(old_name, new_name, self.mapping)

    def __rmul__(self, other):
        """Right multiplication operation."""
        if isinstance(other, Typing):
            return Typing(
                compose(other.mapping),
                self.attrs)
        else:
            return NotImplemented

    def __mul__(self, other):
        """Multiplication operation."""
        if isinstance(other, Typing):
            return Typing(
                compose(other.mapping, self.mapping))

        elif isinstance(other, RuleTyping):
            return RuleTyping(
                compose(other.lhs_mapping, self.mapping),
                compose(other.rhs_mapping, self.mapping),
                other.lhs_total,
                other.rhs_total)
        else:
            return NotImplemented

    def to_json(self):
        return {
            "mapping": self.mapping,
            "attrs": self.attrs_to_json()
        }

    @classmethod
    def from_json(cls, json_data):
        mapping, attrs = cls.process_json(json_data)
        return cls(mapping, attrs)

    @staticmethod
    def process_json(json_data):
        mapping = json_data["mapping"]
        if "attrs" not in json_data.keys():
            attrs = dict()
        else:
            attrs = AttributeContainter.attrs_from_json(
                json_data["attrs"])
        return mapping, attrs


class RuleTyping(AttributeContainter):
    """Data structure incapsulating rule typing.

    A rule typing by a graph is defined by two homomorphisms:
    lhs -> graph and rhs -> graph, such that they commute
    (p -> lhs -> graph and p -> rhs -> graph commute).

    Attributes
    ----------
    lhs_mapping : dict
        Dictionary containing a map from nodes of the lhs of
        the rule to nodes of a target graph.
    rhs_mapping : dict
        Dictionary containing a map from nodes of the rhs of
        the rule to nodes of a target graph.
    lhs_total : bool
        Flag indication if the typing of the lhs is forced to be total
    rhs_total : bool
        Flag indication if the typing of the rhs is forced to be total
    attrs : dict
        Dictionary with attrs of the rule typing
    """

    def __init__(self, lhs_mapping, rhs_mapping,
                 lhs_total=False, rhs_total=False, attrs=None):
        """Initialize homomorphism."""
        self.lhs_mapping = copy.deepcopy(lhs_mapping)
        self.rhs_mapping = copy.deepcopy(rhs_mapping)
        self.lhs_total = lhs_total
        self.rhs_total = rhs_total
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def rename_source(self, old_name, new_name):
        """Name the source of the rule typing."""
        replace_source(old_name, new_name, self.lhs_mapping)
        replace_source(old_name, new_name, self.rhs_mapping)

    def rename_target(self, old_name, new_name):
        """Name the target of the rule typing."""
        replace_target(old_name, new_name, self.lhs_mapping)
        replace_target(old_name, new_name, self.rhs_mapping)

    def all_total(self):
        """All the components of the rule are totally typed."""
        return self.lhs_total and self.rhs_total

    def __rmul__(self, other):
        """Right multiplication."""
        if isinstance(other, Typing):
            return RuleTyping(
                compose(self.lhs_mapping, other.mapping),
                compose(self.rhs_mapping, other.mapping),
                self.lhs_total and other.total,
                self.rhs_total and other.total,
                self.attrs)
        else:
            return NotImplemented

    def to_json(self):
        return {
            "lhs_mapping": self.lhs_mapping,
            "rhs_mapping": self.rhs_mapping,
            "lhs_total": self.lhs_total,
            "rhs_total": self.rhs_total,
            "attrs": self.attrs_to_json()
        }

    @classmethod
    def from_json(cls, json_data):
        lhs_map, rhs_map, lhs_total, rhs_total, attrs =\
            cls.process_json(json_data)
        return cls(lhs_map, rhs_map, lhs_total, rhs_total, attrs)

    @staticmethod
    def process_json(json_data):
        lhs_map = json_data["lhs_mapping"]
        rhs_map = json_data["rhs_mapping"]
        lhs_total = json_data["lhs_total"]
        rhs_total = json_data["rhs_total"]
        if "attrs" not in json_data.keys():
            attrs = dict()
        else:
            attrs = AttributeContainter.attrs_from_json(
                json_data["attrs"])
        return lhs_map, rhs_map, lhs_total, rhs_total, attrs


class Relation(AttributeContainter):
    """Base class for relations equipped with attributes."""


class GraphRelation(Relation):
    """Data structure incapsulating relations on graphs.

    Attributes
    ----------
    rel : dict
        Dictionary represeting a relation between two graphs,
        keys represent nodes of the left graph and values are
        collections of nodes from the right graph to which they
        are related.
    attrs : dict
        Dictionary containing attrs of graph relation.
    """

    def __init__(self, relation_dict, attrs=None):
        """Initialize graph relation."""
        self.rel = relation_dict
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return

    def left_domain(self):
        """Return the definition domain of the left member of relation."""
        return set(self.rel.keys())

    def right_domain(self):
        """Return the definition domain of the right member of relation."""
        return set(self.rel.values())

    def to_json(self):
        return {
            "rel": {a: list(b) for a, b in self.rel.items()},
            "attrs": self.attrs_to_json()
        }

    @classmethod
    def from_json(cls, json_data):
        rel, attrs = cls.process_json(json_data)
        return cls(rel, attrs)

    @staticmethod
    def process_json(json_data):
        rel = {a: set(b) for a, b in json_data["rel"].items()}
        if "attrs" not in json_data.keys():
            attrs = dict()
        else:
            attrs = AttributeContainter.attrs_from_json(
                json_data["attrs"])
        return rel, attrs

# class RuleGraphRelation(Relation):
#     pass


# class RuleRelation(Relation):
#     """Implements relations on rules."""

#     def __init__(self, lhs_pairs, p_pairs, rhs_pairs, attrs=None):
#         """Initialize graph relation."""
#         pass
