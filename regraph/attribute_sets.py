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
import sys

from greenery.lego import parse


def _regex_to_string(a):
    if isinstance(a, str):
        return a
    elif isinstance(a, re._pattern_type):
        return a.pattern
    elif isinstance(a, RegexSet):
        if a.pattern is not None:
            return a.pattern
        else:
            return None
    else:
        raise ValueError("")


class AttributeSet(object):
    """Parent class for attribute sets."""

    def __bool__(self):
        """Bool representation of attribute set."""
        return not self.is_empty()

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

    @classmethod
    def from_json(cls, json_data):
        """Create attribute set object from json-like dictionary."""
        init_args = None
        if "data" in json_data.keys():
            init_args = json_data["data"]

        # JSON cannot dump tuples, so finite set of tuples is usually
        # represented as a list of lists, if we read from json list of
        # lists, we interpret them as a set of tuples
        if json_data["type"] == "FiniteSet":
            for i, element in enumerate(init_args):
                if type(element) == list:
                    init_args[i] = tuple(element)
        return getattr(sys.modules[__name__], json_data["type"])(init_args)


class FiniteSet(AttributeSet):
    """Wrapper for finite sets as attribute sets."""

    def __init__(self, fset=None):
        """Initialize finite set object."""
        if fset is None:
            self.fset = set()
        else:
            if type(fset) == set:
                self.fset = copy.deepcopy(fset)
            elif type(fset) == list:
                self.fset = set(fset)
            else:
                self.fset = {fset}

    def __str__(self):
        """String represenation of FiniteSet."""
        return str(self.fset)

    def __iter__(self):
        """Iterator over FiniteSet."""
        for element in self.fset:
            yield element

    def __len__(self):
        """Length of finite set."""
        return len(self.fset)

    def issubset(self, other):
        """Test if subset of another set."""
        if type(other) == set:
            return self.fset.issubset(other)
        elif isinstance(other, FiniteSet):
            return self.fset.issubset(other.fset)
        elif isinstance(other, RegexSet):
            for element in self.fset:
                if not other.match(str(element)):
                    return False
        elif isinstance(other, IntegerSet):
            for element in self.fset:
                if type(element) != int:
                    raise ValueError(
                        "Element %s of a finite set is not an "
                        "integer (%s)" %
                        (str(element), str(type(element)))
                    )
                if not other.in_range(element):
                    return False
        elif isinstance(other, EmptySet):
            return False
        elif isinstance(other, UniversalSet):
            return True
        else:
            return False
        return True

    def union(self, other):
        """Union of a finite set with another set."""
        if type(other) == set:
            return FiniteSet(self.fset.union(other))
        elif isinstance(other, FiniteSet):
            return FiniteSet(self.fset.union(other.fset))
        elif isinstance(other, RegexSet):
            return RegexSet(self.fset).union(other)
        elif isinstance(other, IntegerSet):
            for element in self.fset:
                if type(element) != int:
                    raise ValueError("Element of finite set is not integer")
            return IntegerSet(self.fset).union(other)
        elif isinstance(other, EmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, UniversalSet):
            return UniversalSet()
        else:
            raise ValueError("Invalid type of attribute set!")

    def intersection(self, other):
        """Intesection of a finite set with another set."""
        if type(other) == set:
            return FiniteSet(self.fset.intersection(other))
        elif isinstance(other, FiniteSet):
            return FiniteSet(self.fset.intersection(other.fset))
        elif isinstance(other, RegexSet):
            intersection = []
            for element in self.fset:
                if other.match(str(element)):
                    intersection.append(element)
            return FiniteSet(intersection)
        elif isinstance(other, IntegerSet):
            for element in self.fset:
                if type(element) != int:
                    raise ValueError("Element of finite set is not integer")
            return IntegerSet(self.fset).intersection(other)
        elif isinstance(other, EmptySet):
            return EmptySet()
        elif isinstance(other, UniversalSet):
            return copy.deepcopy(self)
        else:
            raise ValueError("Invalid type of attribute set!")

    def difference(self, other):
        """Difference of self with other finite set."""
        if type(other) == set:
            return FiniteSet(self.fset.difference(other))
        elif isinstance(other, FiniteSet):
            return FiniteSet(self.fset.difference(other.fset))
        elif isinstance(other, RegexSet):
            elements_to_keep = []
            for element in self.fset:
                if not other.match(str(element)):
                    elements_to_keep.append(element)
            return FiniteSet(elements_to_keep)
        elif isinstance(other, IntegerSet):
            for element in self.fset:
                if type(element) != int:
                    raise ValueError("Element of finite set is not integer")
            return IntegerSet(self.fset).difference(other)
        elif isinstance(other, EmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, UniversalSet):
            return FiniteSet()
        else:
            raise ValueError("Invalid type of attribute set!")

    def is_empty(self):
        """Test if finite set is empty."""
        return self.fset is None or len(self.fset) == 0

    def is_universal(self):
        """Test if finite set is universal."""
        return False

    def to_json(self):
        """JSON represenation of finite set."""
        json_data = {}
        json_data["type"] = "FiniteSet"
        json_data["data"] = list(self.fset)
        return json_data

    def update(self, element):
        """Update finite set."""
        self.fset.update(element)

    def add(self, element):
        """Add an element."""
        self.fset.add(element)


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
                self.pattern = concat
            else:
                self.pattern = regexp
        else:
            self.pattern = None

    def __str__(self):
        """String representation of RegexSet obj."""
        if self.pattern:
            return self.pattern
        else:
            return "<EmptyRegexSet>"

    def issubset(self, other):
        """Test for regexp inclusion."""
        if self.pattern is None:
            return True
        else:
            self_exp = parse(self.pattern)

            def included(a):
                if isinstance(a, str):
                    other_exp = parse(a)
                elif isinstance(a, re._pattern_type):
                    other_exp = parse(a.pattern)
                elif isinstance(a, RegexSet):
                    if a.pattern:
                        other_exp = parse(a.pattern)
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

        new_pattern = self.pattern + "|" + "|".join(patterns)
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

        self_exp = parse(self.pattern)

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
        complement_exp = parse(self.pattern)
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
        if self.pattern and self.pattern == "(.|\n)*":
            return True
        return False

    def is_empty(self):
        """Test if an object is an empty RegexSet."""
        return self.pattern is None

    def match(self, string):
        """Check if a string is in RegexSet."""
        if self.pattern is not None:
            return re.compile(self.pattern).fullmatch(string) is not None
        else:
            return False

    def to_json(self):
        """JSON represenation of RegexSet."""
        json_data = {}
        json_data["type"] = "RegexSet"
        json_data["data"] = self.pattern
        return json_data


class IntegerSet(AttributeSet):
    """Set of integers (possible infinite) defined by a set of intervals."""

    def __init__(self, interval_list):
        """Initialize IntegerSet object.

        Takes a collection of tuples or ints
        normalizes the intervals and singletons
        and creates a set of intervals and singletons.
        """
        starts = list()
        ends = list()
        for interval in interval_list:
            try:
                start, end = interval
                if start > end:
                    raise ValueError("Invalid interval")
                else:
                    starts.append(start)
                    ends.append(end)
            except TypeError:
                starts.append(interval)
                ends.append(interval)

        new_intervals = list()
        sorted_starts_ind = np.argsort(starts)
        visited = set()
        for i, index in enumerate(sorted_starts_ind):
            if index not in visited:
                visited.add(index)
                current_end = ends[index]
                for j in range(i + 1, len(sorted_starts_ind)):
                    if starts[sorted_starts_ind[j]] - 1 > ends[index]:
                        break
                    else:
                        visited.add(sorted_starts_ind[j])
                        current_end = max(
                            current_end, ends[sorted_starts_ind[j]]
                        )
                # in case new interval overlaps
                # with newly constructed interval
                if len(new_intervals) > 0 and\
                   starts[index] <= new_intervals[-1][1] + 1:
                    new_intervals[-1] = (
                        new_intervals[-1][0],
                        max(current_end, new_intervals[-1][1])
                    )
                else:
                    new_intervals.append((starts[index], current_end))
        self.intervals = new_intervals
        return

    def __str__(self):
        """String representation of IntegerSet obj."""
        interval_strs = []
        for start, end in self.intervals:
            if start > -math.inf:
                start_str = "%d" % start
            else:
                start_str = "-inf"
            if end < math.inf:
                end_str = "%d" % end
            else:
                end_str = "inf"
            if start_str != end_str:
                interval_strs.append("[" + start_str + ", " + end_str + "]")
            else:
                interval_strs.append("{" + start_str + "}")
        return ", ".join(interval_strs)

    def issubset(self, other):
        """Test set inclusion for intervals of ints."""
        for start, end in self.intervals:
            found = False
            for other_start, other_end in other.intervals:
                if start >= other_start and end <= other_end:
                    found = True
                    break
            if not found:
                return False
        return True

    def union(self, other):
        """Union of two integer sets."""
        return IntegerSet(self.intervals + other.intervals)

    def intersection(self, other):
        """Intersection of two integer sets."""
        def interval_intersect(interval1, interval2):
            start1, end1 = interval1
            start2, end2 = interval2
            common_start = max(start1, start2)
            common_end = min(end1, end2)
            if common_start <= common_end:
                return (common_start, common_end)
            return None

        new_intervals = []
        for interval1 in self.intervals:
            for interval2 in other.intervals:
                common = interval_intersect(interval1, interval2)
                if common:
                    new_intervals.append(common)
        return IntegerSet(new_intervals)

    def difference(self, other):
        """Difference of self with the other."""
        def is_subinterval(a, b):
            start_a, end_a = a
            start_b, end_b = b
            if start_a >= start_b and end_a <= end_b:
                return True
            return False

        def create_cuts(small, large):
            small_start, small_end = small
            large_start, large_end = large
            cuts = []
            if small_start > large_start:
                cuts.append((large_start, small_start - 1))
            if small_end < large_end:
                cuts.append((small_end + 1, large_end))
            return cuts

        new_intervals = []
        intersect = self.intersection(other)
        for interval1 in self.intervals:
            cuts = [interval1]
            for interval2 in intersect.intervals:
                for i, cut in enumerate(cuts):
                    if is_subinterval(interval2, cut):
                        new_cuts = create_cuts(interval2, cut)
                        cuts[i] = new_cuts
                new_cuts = []
                for subcuts in cuts:
                    if isinstance(subcuts, list):
                        for cut in subcuts:
                            new_cuts.append(cut)
                    else:
                        new_cuts.append(subcuts)
                cuts = new_cuts
            if len(cuts) == 0:
                new_intervals.append(interval1)
            else:
                new_intervals += cuts
        return IntegerSet(new_intervals)

    @classmethod
    def universal(cls):
        """Universal integer set."""
        return cls([(-math.inf, math.inf)])

    @classmethod
    def empty(cls):
        """Empty integer set."""
        return cls([])

    def is_universal(self):
        """Test universality."""
        return self == IntegerSet.universal()

    def is_empty(self):
        """Test if empty."""
        return self == IntegerSet.empty()

    @classmethod
    def from_finite_set(cls, s):
        """Create Integer set object from a finite set."""
        intervals = []
        for el in s:
            if type(el) != int:
                val = int(el)
            else:
                val = el
            intervals.append(val)
        return cls(intervals)

    def in_range(self, num):
        """Test if probided integer is in integer set."""
        found = False
        for start, end in self.intervals:
            if num >= start and num <= end:
                found = True
                break
        return found

    def to_json(self):
        """JSON represenation of IntegerSet."""
        json_data = {}
        json_data["type"] = "IntegerSet"
        json_data["data"] = [[start, end] for start, end in self.intervals]
        return json_data


class EmptySet(AttributeSet):
    """Empty attribute set."""

    def __len__(self):
        """Return length."""
        return 0

    def issubset(self, other):
        """Test if subset of another set."""
        return True

    def intersect(self, other):
        """Intersect with another set."""
        return EmptySet()

    def union(self, other):
        """Find union with another set."""
        return copy.deepcopy(other)

    def difference(self, other):
        """Find difference with another."""
        return EmptySet()

    def is_universal(self):
        """Test if universal."""
        return False

    def is_empty(self):
        """Test if empty."""
        return True

    def to_json(self):
        """JSON represenation of EmptySet."""
        json_data = {}
        json_data["type"] = "EmptySet"
        return json_data


class UniversalSet(AttributeSet):
    """Universal attribute set."""

    def __len__(self):
        """Return length."""
        return math.inf

    def issubset(self, other):
        """Test if subset of other set."""
        if isinstance(other, AttributeSet):
            return other.is_universal()
        else:
            return False

    def is_universal(self):
        """Test if universal."""
        return True

    def is_empty(self):
        """Test if empty."""
        return False

    def intersect(self, other):
        """Intersect with another set."""
        return copy.deepcopy(other)

    def union(self, other):
        """Find union with another set."""
        return UniversalSet()

    def difference(self, other):
        """Difference with another set."""
        return other.__class__.universal().difference(other)

    def to_json(self):
        """JSON represenation of UniversalSet."""
        json_data = {}
        json_data["type"] = "UniversalSet"
        return json_data
