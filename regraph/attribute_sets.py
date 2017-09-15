"""A collection of data structures for attributes on the nodes of graphs.

Implements the following data structures:
    - `AttributeSet` -- abstract class for attribute sets in `ReGraph`
    (provides interface, implements some common behaviour);
    - `FiniteSet` -- wrapper for Python finite sets, inherits `AttributeSet`;
    - `RegexSet` -- a class for possibly infinite sets of strings given by
    regular expressions. It uses the `greenery` library for finding
    inclusion and intersection of regular expressions, its method `match` can
    be used to test if a given string is in a set of strings defined by
    regular expressions;
    - `IntegerSet` -- a class for possibly infinite sets of integers
    defined by a set of disjoint intervals, inherits `AttributeSet`,
    provides the method `in_range` for testing if a given integer is in
    the set of integers.

TODO:

    - `RealSet`
"""

import copy
import re
import numpy as np
import math

from greenery.lego import parse


def _regex_to_string(a):
    if isinstance(a, str):
        return a
    elif isinstance(a, re._pattern_type):
        return a.pattern
    elif isinstance(a, RegexSet):
        if a.pattern is not None:
            return a.pattern.pattern
        else:
            return None
    else:
        raise ValueError("")


class AttributeSet(object):
    """Parent class for attribute sets."""

    def __bool__(self):
        """Bool representation of attribute set."""
        return self.is_empty()

    def __repr__(self):
        """Representation of attribute set."""
        return str(self)

    def __len__(self):
        """Length of attribute set."""
        return len(self)

    def union(self, other):
        """Find union attribute set."""
        pass

    def intersect(self, other):
        """Find intersection attribute set."""
        pass

    def difference(self, other):
        """Find difference."""
        pass

    def issubset(self, other):
        """Test if subset of another set."""
        pass

    def __eq__(self, other):
        """Test equality with another set."""
        return self.issubset(other) and other.issubset(self)

    def __ge__(self, other):
        """Test if greater or equal than another set."""
        return other.issubset(self)

    def __gt__(self, other):
        """Test if strictly greater than another set."""
        return other.issubset(self) and not self.issubset(other)

    def __lt__(self, other):
        """Test if strictly less than another set."""
        return self.issubset(other) and not other.issubset(self)

    def __le__(self, other):
        """Less or equal."""
        return self.issubset(other)

class RegexSet(AttributeSet):
    """A set of strings defined by regular expression."""

    def __init__(self, regexp):
        """Initialize a set of strings defined by a regexp."""
        if regexp is not None:
            if type(regexp) != str:
                strings = []
                for element in regexp:
                    strings.append(str(element))
                concat = "|".join(strings)
                self.pattern = re.compile(concat)
            else:
                self.pattern = re.compile(regexp)
        else:
            self.pattern = None

    def __str__(self):
        """String representation of RegexSet obj."""
        if self.pattern:
            return self.pattern.pattern
        else:
            return "<EmptyRegexSet>"

    def issubset(self, other):
        """Test for regexp inclusion."""
        if self.pattern is None:
            return True
        else:
            self_exp = parse(self.pattern.pattern)

            def included(a):
                if isinstance(a, str):
                    other_exp = parse(a)
                elif isinstance(a, re._pattern_type):
                    other_exp = parse(a.pattern)
                elif isinstance(a, RegexSet):
                    if a.pattern:
                        other_exp = parse(a.pattern.pattern)
                    else:
                        return False
                else:
                    raise ValueError(
                        "Regexp object should be `str` or `re._pattern_type`!"
                    )
                return (self_exp & other_exp.everythingbut()).empty()

            if isinstance(other, set):
                res = True

                for element in other:
                    if not included(element):
                        res = False
                        break
            else:
                res = included(other)
            return res

    def union(self, other):
        """Union of two regexps."""
        if self.pattern is None:
            other_str = _regex_to_string(other)
            if other_str is None:
                return RegexSet.empty()
            else:
                return RegexSet(other_str)
        if self.is_universal():
            return RegexSet.universal()

        patterns = []
        if isinstance(other, set):
            for element in other:
                element_str = _regex_to_string(element)
                if element_str is not None:
                    patterns.append(element_str)
        else:
            other_str = _regex_to_string(other)
            if other_str is None:
                return self.copy()
            else:
                patterns.append(other_str)

        new_pattern = self.pattern.pattern + "|" + "|".join(patterns)
        result = RegexSet(new_pattern)
        return result

    def intersection(self, other):
        """Smart intersection of two regexps.

        Uses greenery library to find and reduce intersection.
        """
        if self.pattern is None:
            return RegexSet.empty()

        if self.is_universal():
            if isinstance(other, set):
                universal_flag = True
                other_exp = []
                for el in other:
                    exp = RegexSet(_regex_to_string(el))
                    other_exp.append(exp)
                    if not exp.is_universal():
                        universal_flag = False
                if universal_flag:
                    return RegexSet.universal()
                else:
                    result_obj = RegexSet.empty()
                    for exp in other_exp:
                        result_obj.union(exp)
                    return result_obj
            else:
                other_obj = RegexSet(_regex_to_string(other))
                if other_obj.is_universal():
                    return RegexSet.universal()
                else:
                    return other_obj

        self_exp = parse(self.pattern.pattern)

        other_exp = []
        if isinstance(other, set):
            for exp in other:
                exp_str = _regex_to_string(exp)
                if exp_str is None:
                    return RegexSet.empty()
                other_exp.append(parse(exp_str))
        else:
            other_str = _regex_to_string(other)
            if other_str is None:
                return RegexSet.empty()
            other_exp.append(parse(other_str))

        intersect_exp = self_exp
        for exp in other_exp:
            intersect_exp = intersect_exp.intersection(exp)

        return RegexSet(str(intersect_exp))

    def difference(self, other):
        """Difference of self with other regex."""
        if self.pattern is None:
            return RegexSet.empty()

        other_exp = []

        if isinstance(other, set):
            for exp in other:
                exp_str = _regex_to_string(exp)
                if exp_str is not None:
                    other_exp.append(parse(exp_str))
        else:
            other_str = _regex_to_string(other)
            if other_str is not None:
                other_exp.append(parse(other_str))
            else:
                return self.copy()
        complement_exp = parse(self.pattern.pattern)
        for exp in other_exp:
            complement_exp = complement_exp.difference(exp)

        return RegexSet(str(complement_exp.reduce()))

    @classmethod
    def from_finite_set(cls, fset):
        """Create a regexp from ordinary finite set.

        All the elements of the set will be cast to str.
        """
        return cls("|".join([str(el) for el in fset]))

    @classmethod
    def universal(cls):
        """Create a RegexSet object matching any string."""
        return cls("(.|\n)*")

    @classmethod
    def empty(cls):
        """Create a RegexSet object not matching any string."""
        return cls(None)

    def is_universal(self):
        """Test if an object is a universal RegexSet."""
        if self.pattern and self.pattern.pattern == "(.|\n)*":
            return True
        return False

    def is_empty(self):
        """Test if an object is an empty RegexSet."""
        return self.pattern is None

    def match(self, string):
        """Check if a string is in RegexSet."""
        if self.pattern is not None:
            return self.pattern.fullmatch(string) is not None
        else:
            return False
