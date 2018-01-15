"""ReGraph tutorial part 1, example 2 (attribute sets)."""
import regraph.attribute_sets as atsets
from math import inf


print("Integer Attribute Sets")
print("----------------------")

ints = atsets.IntegerSet({(0, 8), (11, inf)})
print("Integer attribute set 'ints': ", ints)
print("Contains 5:", ints.contains(5))
print("Contains 9:", ints.contains(9))
print()

a = atsets.IntegerSet({(0, 3), (20, 30)})
print("Integer attribute set 'a': ", a)
print("'a' is subset if 'ints' :", a.issubset(ints))
b = atsets.IntegerSet({(0, 10)})
print("Integer attribute set 'b': ", b)
print("'b' is subset if 'ints' :", b.issubset(ints))
print()

a_and_ints = a.intersection(ints)
print("Intersection of 'a' with 'ints' :", a_and_ints)
b_and_ints = b.intersection(ints)
print("Intersection of 'b' with 'ints' :", b_and_ints)

a_or_ints = a.union(ints)
print("Union of 'a' with 'ints' :", a_or_ints)
b_or_ints = b.union(ints)
print("Union of 'b' with 'ints' :", b_or_ints)


print("Union of 'a' with a set {} of type '{}': ".format(
    {13, 14}, type({13, 14})), a.union({13, 14}))

print("\n")


print("Regex Attribute Sets")
print("---------------------")

words = atsets.RegexSet("[A-Za-z]+")
integers = atsets.RegexSet("\d+")
alphanums = atsets.RegexSet("[A-Za-z\d]+")

print("Regex set 'words': ", words)
print("Regex set 'integers': ", integers)
print("Regex set 'alphanums': ", alphanums)
print()

print("'{}' matches 'words': ".format("42"), words.match("42"))
print("'{}' matches 'words': ".format("hello"), words.match("hello"))
print("'{}' matches 'integers': ".format("hello"), integers.match("hello"))
print()

print("'integers' is subset of 'words': ", integers.issubset(words))
print("'integers' is subset of 'alphanums': ", integers.issubset(alphanums))
print()

print("Intersection of 'integers' with 'words' :", integers.intersection(words))
print("Union of 'integers' and 'words' :", integers.union(words))

no_hi_bye = words.difference({"hi", "bye"})
print("Subtract a finite set of strings from a regex set: ", no_hi_bye)
print("'{}' matches the result: ".format("hi"), no_hi_bye.match("hi"))
print("'{}' matches the result: ".format("bye"), no_hi_bye.match("bye"))
print("'{}' matches the result: ".format("afternoon"), no_hi_bye.match("afternoon"))
print("\n")


print("Finite Attribute Sets (wrapper around pythonic sets):")
print("-----------------------------------------------------")

a = atsets.FiniteSet({1, 2, 3})
print("Finite set 'a': ", a)
int_regex = atsets.RegexSet("\d+")
print("Regex set 'int_regex': ", int_regex)
positive_integers = atsets.IntegerSet([(0, inf)])
print("Integer set 'positive_integers': ", positive_integers)
print("'a' is subset of 'int_regex': ", a.issubset(int_regex))
print("'a' is subset of 'positive_integers': ", a.issubset(positive_integers))
print("\n")


print("Universal and Empty Attribute Sets")
print("----------------------------------")

univ = atsets.UniversalSet()
print("Universal set 'univ': ", univ)

empty = atsets.EmptySet()
print("Empty set 'empty': ", empty)

print("Union of 'univ' with 'empty': ", univ.union(empty))
print("Intersection of 'univ' with 'empty': ", univ.intersection(empty))

a = atsets.FiniteSet({1, 2, 3})
print("Finite set 'a': ", a)
print("'a' is subset of 'univ': ", a.issubset(univ))
print("'a' is subset of 'empty': ", a.issubset(empty))
print("Intersection of 'univ' with 'a': ", univ.intersection(a))
print("Union of 'univ' with 'a': ", univ.union(a))
