.. _advanced_attributes:

=================================
Advanced node and edge attributes
=================================


ReGraph implements a collection of data structures for representation of potentially infinite sets of attribute values, together with all the default set operations on them (such as union, intersection, inclusion test etc.):

* `FiniteSet`, a wrapper for Python finite sets.
* `RegexSet`, a class for possibly infinite sets of strings given by regular expressions.
* `IntegerSet`, a class for possibly infinite sets of integers defined by a set of disjoint intervals.

Import module containing attribute sets data structures:

::

    from math import inf
    
    import regraph.attribute_sets as atsets

Define an infinite integer set:

>>> ints = atsets.IntegerSet({(0, 8), (11, inf)})

Test if an interger value is in the set:

>>> ints.contains(5)
True
>>> ints.contains(9)
False

Test if another integer set is a subset:

>>> a = atsets.IntegerSet({(0, 3), (20, 30)})
>>> a.issubset(ints)
True
>>> b = atsets.IntegerSet({(0, 10)})
>>> b.issubset(ints)
False

Find the intersection of two `IntegerSet` objects:

>>> a_and_ints = a.intersection(ints)
>>> a_and_ints
[0, 3], [20, 30]
>>> b_and_ints = b.intersection(ints)
[0, 8]


Find the union of two `IntegerSet` objects:

>>> a_or_ints = a.union(ints)
>>> a_or_ints
[0, 8], [11, inf]
>>> b_or_ints = b.union(ints)
>>> b_or_ints
[0, inf]

We can also find unions and intersections of integer sets with 
ordinary Python sets, as long as these sets contain integer values:

>>> a.union({13, 14})
>>> a
[0, 3] [13, 14] [20, 30]

The following line of code with cause the `AttributeSetError` exception:

>>> a.union({13, 14, "a"})
AttributeSetError: Set '{'a', 13, 14}' contains non-integer elements!

Now, define objects of `RegexSet`:

>>> words = atsets.RegexSet("[A-Za-z]+")
>>> integers = atsets.RegexSet("\d+")
>>> alphanums = atsets.RegexSet("[A-Za-z\d]+")

Test if strings are matched by regex's defining our `RegexSet` objects:

>>> words.match("42")
False
>>> integers.match("42")
True
>>> words.match("hello")
True
>>> integers.match("hello")
False

Test if one regex set is a subset of another:

>>> integers.issubset(words)
False
>>> integers.issubset(alphanums)
True

Find the intersection of two regex sets:

>>> integers.intersection(words)
[]
>>> integers.intersection(alphanums)
\d+

Find the union of two regex sets:

>>> integers.union(words)
\d+|[A-Za-z]+


Subtract a finite set of strings from a regex set:

>>> words.difference({"hi", "bye"})
([A-Zac-gi-z]|b([A-Za-xz]|y([A-Za-df-z]|e[A-Za-z]))|h([A-Za-hj-z]|i[A-Za-z]))[A-Za-z]*|by?|h

The result may be not extremely readable, but we can test it in the following way:

>>> no_hi_bye = words.difference({"hi", "bye"})
>>> no_hi_bye.match("hi")
False
>>> no_hi_bye.match("bye")
False
>>> no_hi_bye.match("afternoon")
True

Now, we can also wrap Python set objects into `FiniteSet` class provided in ReGraph.

>>> a = atsets.FiniteSet({1, 2, 3})

It allows us to apply to them any set operations from the common interface of ReGraph's
attribute sets. For example:

>>> from math import inf
>>> int_regex = atsets.RegexSet("\d+")
>>> positive_integers = atsets.IntegerSet([(0, inf)])
>>> a.issubset(int_regex)
True
>>> a.issubset(positive_integers)
True

ReGraph provides two special classes of attribute sets: `UniversalSet` and `EmptySet`,
which in their essence are static classes. These classes contain all standard
set theoretic operations and follow the common interface defined in the base class
`AttributeSet` (as all previously presented attribute set classes).
Consider a couple of examples illustrating the behaviour of `UniversalSet` and `EmptySet`:

>>> univ = atsets.UniversalSet()
>>> empty = atsets.EmptySet()
>>> univ.union(empty)
UniversalSet
>>> univ.intersection(empty)
EmptySet
>>> a = atsets.FiniteSet({1, 2, 3})
>>> a.issubset(univ)
True
>>> a.issubset(empty)
False
>>> univ.intersection(a)
{1, 2, 3}
>>> univ.union(a)
UniversalSet


See more
--------

Module reference: :ref:`attribute_sets`
