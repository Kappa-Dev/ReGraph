"""A collection of data structures for values of attributes on nodes/edges of graphs.

Implements the following data structures:

* `AttributeSet` -- a base class for attribute sets in `ReGraph`,
  provides an interface, implements some common behaviour;
* `FiniteSet` -- wrapper for Python finite sets, inherits `AttributeSet`;
* `RegexSet` -- a class for possibly infinite sets of strings given by
  regular expressions. It uses the `greenery <https://github.com/qntm/greenery>`_
  library for finding inclusion and intersection of regular expressions,
  its method `match` can be used to test if a given string is in
  a set of strings defined by regular expressions;

* `IntegerSet` -- a class for possibly infinite sets of integers
  defined by a set of disjoint intervals, inherits `AttributeSet`,
  provides the method `contains` for testing if a given integer is in
  the set of integers.

TODO:

* `RealSet` -- a class for possibly infinite sets of reals
  defined by a set of open/closed intervals, inherits `AttributeSet`,
  provides the method `contains` for testing if a given real is in
  the set of reals.
"""

import copy
import re
import numpy as np
import math
import sys

from greenery.lego import parse

from regraph.exceptions import AttributeSetError


def _hashify(d):
    """Hashify a dictionary to a list of tuples."""
    result = []
    for key, value in d.items():
        if type(value) is dict:
            result.append((key, _hashify(value)))
        else:
            result.append((key, value))
    return tuple(result)


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
        raise AttributeSetError("Cannot convert regex to string!")


class AttributeSet(object):
    """Base class for ReGraph attribute sets."""

    def __bool__(self):
        """Bool representation of attribute set."""
        return not self.is_empty()

    def __repr__(self):
        """Representation of attribute set."""
        return str(self)

    def __len__(self):
        """Length of attribute set."""
        return len(self)

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
        """Test if  less or equal than another set."""
        return self.issubset(other)

    def union(self, other):
        """Find union attribute set."""
        pass

    def intersect(self, other):
        """Find intersection attribute set."""
        pass

    def difference(self, other):
        """Find difference attribute set."""
        pass

    def issubset(self, other):
        """Test if subset of another set."""
        pass

    @classmethod
    def from_json(cls, json_data):
        """Create attribute set object from json-like dictionary."""
        if "type" in json_data.keys():
            init_args = None
            if "data" in json_data.keys():
                if not (len(json_data["data"]) == 1 and
                        json_data["data"][0] is None):
                    init_args = json_data["data"]

            # JSON cannot dump tuples, so finite set of tuples is usually
            # represented as a list of lists, if we read from json list of
            # lists, we interpret them as a set of tuples
            if json_data["type"] == "FiniteSet" and init_args is not None:
                for i, element in enumerate(init_args):
                    if type(element) == list:
                        init_args[i] = tuple(element)
            return getattr(sys.modules[__name__], json_data["type"])(init_args)


class FiniteSet(AttributeSet):
    """Wrapper for finite sets as attribute sets.

    Attributes
    ----------
    fset : set
        Python finite set that is being wrapped by the object

    """

    def __init__(self, fset=None):
        """Initialize finite set object."""
        if fset is None or fset == {None}:
            self.fset = set()
        else:
            if type(fset) == set:
                self.fset = copy.deepcopy(fset)
            elif type(fset) == list:
                self.fset = set(fset)
            elif type(fset) == dict:
                self.fset = set(_hashify(fset))
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
        """Test if subset of another set.

        Parameters
        ----------
        other : set, FiniteSet, RegexSet, IntegerSet, EmptySet or UniversalSet

         Returns
        -------
        `True` is `self` defines a subset of `other`, `False` otherwise
        """
        if type(other) == set:
            return self.fset.issubset(other)
        elif isinstance(other, FiniteSet):
            return self.fset.issubset(other.fset)
        elif isinstance(other, RegexSet):
            for element in self.fset:
                if element is not None:
                    if not other.match(str(element)):
                        return False
        elif isinstance(other, IntegerSet):
            for element in self.fset:
                if element is not None:
                    if type(element) != int:
                        try:
                            element = int(element)
                        except:
                            raise AttributeSetError(
                                "Element '%s' of a finite set is not an "
                                "integer (%s)" %
                                (str(element), str(type(element)))
                            )
                    if not other.contains(element):
                        return False
        elif isinstance(other, EmptySet):
            return False
        elif isinstance(other, UniversalSet):
            return True
        else:
            return False
        return True

    def union(self, other):
        """Find the union with another set.

        Parameters
        ----------
        other : set, FiniteSet, RegexSet, IntegerSet, EmptySet or UniversalSet

        Returns
        -------
        The union set
        """
        if type(other) == set:
            return FiniteSet(self.fset.union(other))
        elif isinstance(other, FiniteSet):
            return FiniteSet(self.fset.union(other.fset))
        elif isinstance(other, RegexSet):
            return RegexSet(self.fset).union(other)
        elif isinstance(other, IntegerSet):
            for element in self.fset:
                if type(element) != int:
                    try:
                        element = int(element)
                    except:
                        raise AttributeSetError(
                            "Element '%s' of a finite set is not an "
                            "integer (%s)" %
                            (str(element), str(type(element)))
                        )
            return IntegerSet(self.fset).union(other)
        elif isinstance(other, EmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, UniversalSet):
            return UniversalSet()
        else:
            raise AttributeSetError("Invalid type of attribute set!")

    def intersection(self, other):
        """Find the intersection set with another set.

        Parameters
        ----------
        other : set, FiniteSet, RegexSet, IntegerSet, EmptySet or UniversalSet

        Returns
        -------
        The intersection set
        """
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
                    try:
                        element = int(element)
                    except:
                        raise AttributeSetError(
                            "Element '%s' of a finite set is not an "
                            "integer (%s)" %
                            (str(element), str(type(element)))
                        )
            return IntegerSet(self.fset).intersection(other)
        elif isinstance(other, EmptySet):
            return EmptySet()
        elif isinstance(other, UniversalSet):
            return copy.deepcopy(self)
        else:
            raise AttributeSetError("Invalid type of attribute set!")

    def difference(self, other):
        """Find the difference set with another set.

        Finds a `self` - `other` set.

        Parameters
        ----------
        other : set, FiniteSet, RegexSet, IntegerSet, EmptySet or UniversalSet

        Returns
        -------
        The difference set
        """
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
                    try:
                        element = int(element)
                    except:
                        raise AttributeSetError(
                            "Element '%s' of a finite set is not an "
                            "integer (%s)" %
                            (str(element), str(type(element)))
                        )
            return IntegerSet(self.fset).difference(other)
        elif isinstance(other, EmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, UniversalSet):
            return FiniteSet()
        else:
            raise AttributeSetError("Invalid type of attribute set!")

    def is_empty(self):
        """Test if finite set is empty."""
        return self.fset is None or len(self.fset) == 0

    def is_universal(self):
        """Test if finite set is universal.

        Returns
        -------
        False, as finite set is never a universal set
        """
        return False

    def to_json(self):
        """JSON represenation."""
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
    """Class defining a set of strings recognized by a regular expression.

    RegexSet is defined by a regular expression, and
    is morally associated to a set of strings that
    the regular expression recognizes.

    Attributes
    ----------
    pattern : str
        Regular expression pattern
    """

    def __init__(self, regexp):
        """Initialize a set of strings defined by a regexp pattern.

        Parameters
        ----------
        regexp : str
            Regular expression pattern
        """
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
            if self.is_universal():
                return "<UniversalRegexSet>"
            return self.pattern
        else:
            return "<EmptyRegexSet>"

    def issubset(self, other):
        """Test regexp inclusion relation.

        Tests if a set defined by `self` is a included
        in a set defined by `other`.

        Parameters
        ----------
        other : set, str, re._pattern_type, RegexSet
            Another regex to test inclusion.

        Returns
        -------
        `True` is `self` defines a subset of `other`, `False` otherwise

        Raises
        ------
        AttributeSetError
            If the type `other` is not recognized.
        """
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
                    raise AttributeSetError(
                        "Regexp object should be of type `str` or `re._pattern_type`!"
                    )
                return (self_exp & other_exp.everythingbut()).empty()

            if isinstance(other, set):
                res = True

                for element in other:
                    if element is not None and not included(element):
                        res = False
                        break
            else:
                res = included(other)
            return res

    def union(self, other):
        """Find the union with another set.

        The union is found in the following ways:

        * If `other` is a string, a Python dict or a FiniteSet
          the result of the union is a simple concatenation of the
          string representations of the elements of `other`
          with the pattern of `self`.

        * If `other` is an instance of `UniversalSet`, the union
          is a `UniversalSet` object.

        * If `other` is an instance of `EmptySet`, the union is
          a copy of `self`.

        Parameters
        ----------
        other : set, str, re._pattern_type, RegexSet

        Returns
        -------
        result : RegexSet
            The union set
        """
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
        elif isinstance(other, UniversalSet):
            return UniversalSet()
        elif isinstance(other, EmptySet):
            return copy.deepcopy(self)
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
        """Find the intersection of two regexps.

        This method uses greenery library to find and
        reduce the intersection pattern.

        * If `other` is a string, a Python dict or a FiniteSet,
          it is converted to a regex pattern, after which it
          is parsed by `greenery.lego.parse` method and its
          intersection with the pattern of the `self` is found.
          The library `greenery` finds the intersection between two
          regex's by constructing corresponding FSM's (finite state
          machines) and finding their intersection, after which it
          is converted back to a regex. See more details here:
          https://github.com/qntm/greenery

        * If `other` is an instance of `EmpySet`, the intersection
          is a `EmpySet` object.

        * If `other` is an instance of `UniversalSet`, the intersection
          is a copy of `self`.

        Parameters
        ----------
        other : set, str, re._pattern_type, RegexSet

        Returns
        -------
        result : RegexSet
            The union set
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
        elif isinstance(other, UniversalSet):
            return copy.deepcopy(self)
        elif isinstance(other, EmptySet):
            return EmptySet()
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
        """Find the difference of two regexps.

        This method uses greenery library to find and
        reduce the difference pattern between two regex's.

        * If `other` is a string, a Python dict or a FiniteSet,
          it is converted to a regex pattern, after which it
          is parsed by `greenery.lego.parse` method and its
          difference with the pattern of the `self` is found.
          See more details here:
          https://github.com/qntm/greenery

        * If `other` is an instance of `EmpySet`, the difference
          is a copy of `self`.

        * If `other` is an instance of `UniversalSet`, the difference
          is an instance of `EmptySet`.

        Parameters
        ----------
        other : set, str, re._pattern_type, RegexSet

        Returns
        -------
        result : RegexSet
            The union set
        """
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
    """Set of integers defined by a list of disjoint intervals.

    Attributes
    ----------
    intervals : list
        List of sorted intervals defining an integer set.
    """

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
                    raise AttributeSetError(
                        "Invalid integer interval: [%s, %s]" %
                        (str(start), str(end))
                    )
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
        if isinstance(other, IntegerSet):
            return IntegerSet(self.intervals + other.intervals)
        elif isinstance(other, set):
            other_intervals = []
            try:
                for element in other:
                    int_element = int(element)
                    if self.contains(int_element):
                        other_intervals.append((int_element, int_element))
                return IntegerSet(self.intervals + other_intervals)
            except:
                raise AttributeSetError(
                    "Set '%s' contains non-integer elements!" % str(other)
                )
        elif isinstance(other, FiniteSet):
            other_intervals = []
            try:
                for element in other.fset:
                    int_element = int(element)
                    if self.contains(int_element):
                        other_intervals.append((int_element, int_element))
                return IntegerSet(self.intervals + other_intervals)
            except:
                raise AttributeSetError(
                    "Set '%s' contains non-integer elements!" % str(other)
                )
        elif isinstance(other, UniversalSet):
            return UniversalSet()
        elif isinstance(other, EmptySet):
            return copy.deepcopy(self)
        else:
            raise AttributeSetError(
                "Cannot intersect '%s' with an integer set!" % str(other)
            )

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
        if isinstance(other, IntegerSet):
            for interval1 in self.intervals:
                for interval2 in other.intervals:
                    common = interval_intersect(interval1, interval2)
                    if common:
                        new_intervals.append(common)
            return IntegerSet(new_intervals)
        elif isinstance(other, set):
            try:
                for element in other:
                    int_element = int(element)
                    if self.contains(int_element):
                        new_intervals.append((int_element, int_element))
                return IntegerSet(new_intervals)
            except:
                raise AttributeSetError(
                    "Set '%s' contains non-integer elements!" % str(other)
                )
        elif isinstance(other, FiniteSet):
            try:
                for element in other.fset:
                    int_element = int(element)
                    if self.contains(int_element):
                        new_intervals.append((int_element, int_element))
                return IntegerSet(new_intervals)
            except:
                raise AttributeSetError(
                    "Set '%s' contains non-integer elements!" % str(other)
                )
        elif isinstance(other, UniversalSet):
            return copy.deepcopy(self)
        elif isinstance(other, EmptySet):
            return EmptySet()
        else:
            raise AttributeSetError(
                "Cannot intersect '%s' with an integer set!" % str(other)
            )

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

    def contains(self, num):
        """Test if provided integer is in integer set."""
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

    def __init__(self, *arg):
        super().__init__()
        return

    def __len__(self):
        """Return length."""
        return math.inf

    def __str__(self):
        """."""
        return "UniversalSet"

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

    def intersection(self, other):
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
