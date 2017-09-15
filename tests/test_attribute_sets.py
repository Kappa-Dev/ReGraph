"""Collection of tests for ReGraph attribute sets."""
import math
from attribute_sets import *


class TestAttributeSets:
    """Class for tests."""

    def test_regexset(self):
        """Test RegexSet data structure."""
        univ = RegexSet.universal()
        assert(RegexSet("foo bar").issubset(univ))

        empty = RegexSet.empty()
        assert(RegexSet("").issubset(empty) is False)

        words = RegexSet("(\w|\d|\s)*")
        assert(RegexSet("foo").issubset(words))
        assert(RegexSet("\w*").issubset(words))

        exceptions_set = {1, 2, 3, "foo"}
        exceptions = RegexSet.from_finite_set(exceptions_set)

        diff = words.difference(exceptions)

        assert(univ.intersection(words) == words)
        assert(univ.intersection(empty) == empty)
        assert(univ.union(empty).is_universal())
        assert(univ.union(univ).is_universal())
        assert(empty.intersection(univ) == empty)
        assert(words.intersection(empty) == empty)

        assert(diff.match("1") is False)
        assert(diff.match("2") is False)
        assert(diff.match("3") is False)
        assert(diff.match("foo") is False)
        assert(diff.match("fo"))
        assert(diff.match("fooo"))
        assert(diff.match("foo bar"))
        assert(diff.match("bar foo"))
