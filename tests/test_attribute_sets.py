"""Collection of tests for ReGraph attribute sets."""
import math
from regraph.attribute_sets import (RegexSet,
                                    IntegerSet,
                                    FiniteSet,
                                    UniversalSet,
                                    EmptySet)


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

    def test_integerset(self):
        """Test IntegerSet data structure."""
        set1 = IntegerSet(
            [25, 1, 5, (-math.inf, -3), (-1, 0), (1, 2), (-5, -2), (2, 10)]
        )

        set2 = IntegerSet([25, [-5, -2], [-1, 0]])
        set3 = IntegerSet([24, [11, 12]])
        set4 = IntegerSet([25, [-5, 2]])
        set5 = IntegerSet([25, [-3, -2], [-1, 2]])

        assert(set2.issubset(set1))
        assert(set3.issubset(set1) is False)
        assert(set4.issubset(set1))
        assert(set5.issubset(set1))
        assert(set1.issubset(IntegerSet([[-math.inf, math.inf]])))

        assert(set1.union(set2) == set1)

        assert((-math.inf, 12) in set1.union(set3).intervals)

        assert((-math.inf, 10) in set1.union(set4).intervals)
        assert((-math.inf, 10) in set1.union(set5).intervals)

        neg = IntegerSet([[-math.inf, 0]])
        pos = IntegerSet([[1, math.inf]])
        assert(neg.union(pos) == IntegerSet([[-math.inf, math.inf]]))

        ref_set = IntegerSet([[-math.inf, -2], [3, 5], [12, math.inf]])
        assert((-5, -2) in ref_set.intersection(set2).intervals)
        assert((12, 12) in ref_set.intersection(set3).intervals)
        assert((24, 24) in ref_set.intersection(set3).intervals)
        assert((-5, -2) in ref_set.intersection(set4).intervals)
        assert((-3, -2) in ref_set.intersection(set5).intervals)

        assert((-math.inf, -6) in ref_set.difference(set2).intervals)
        assert((13, 23) in ref_set.difference(set3).intervals)
        assert((25, math.inf) in ref_set.difference(set3).intervals)
        assert((-math.inf, -6) in ref_set.difference(set4).intervals)
        assert((-math.inf, -4) in ref_set.difference(set5).intervals)

        assert((-math.inf, math.inf) in IntegerSet.universal().intervals)
        assert(len(IntegerSet.empty().intervals) == 0)
        assert(
            IntegerSet.universal().intersection(
                IntegerSet.empty()
            ) == IntegerSet.empty()
        )
        assert(
            IntegerSet.universal().difference(
                IntegerSet.empty()
            ) == IntegerSet.universal()
        )

        a = IntegerSet({(0, 3), (20, 30)})
        b1 = a.intersection({1, 2, 3})
        b2 = a.intersection(FiniteSet({1, 2, 3}))
        assert(b1 == b2)
        a = IntegerSet({(0, 3), (20, 30)})
        b1 = a.union({1, 2, 3})
        b2 = a.union(FiniteSet({1, 2, 3}))
        assert(b1 == b2)

    def test_finite_set(self):
        """Test FiniteSet data structure."""
        uniprot =\
            "[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}"

        meta_integer_set = IntegerSet([(0, 10000)])
        meta_string_set = RegexSet(uniprot)

        ints_set = {1, 2}
        ints_list = [1, 2]
        ints_singleton = 3

        string_set = {"P29358", "P23346"}
        string_list = ["P29358", "P23346"]
        string_singleton = "P29358"

        ints1 = FiniteSet(ints_set)
        ints2 = FiniteSet(ints_list)
        ints3 = FiniteSet(ints_singleton)

        strs1 = FiniteSet(string_set)
        strs2 = FiniteSet(string_list)
        strs3 = FiniteSet(string_singleton)

        assert(ints1.issubset(meta_integer_set))
        assert(ints2.issubset(meta_integer_set))
        assert(ints3.issubset(meta_integer_set))

        assert(strs1.issubset(meta_string_set))
        assert(strs2.issubset(meta_string_set))
        assert(strs3.issubset(meta_string_set))

        assert(ints1.union(meta_integer_set) == meta_integer_set)
        assert(isinstance(ints1.union(meta_integer_set), IntegerSet))
        assert(isinstance(strs1.union(meta_string_set), RegexSet))

        ints4 = FiniteSet([-2, 3])
        assert((3, 3) in ints4.intersection(meta_integer_set).intervals)

        strs4 = FiniteSet(["P29358", "12222"])
        assert("P29358" in strs4.intersection(meta_string_set).fset)
        assert(ints4.intersection(strs4).is_empty())
        assert(ints4.issubset(UniversalSet()))
        assert(ints4.issubset(EmptySet()) is False)
