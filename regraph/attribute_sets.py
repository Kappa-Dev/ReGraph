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
