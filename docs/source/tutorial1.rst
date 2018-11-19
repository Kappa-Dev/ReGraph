.. _tutorial:

Tutorial
========
* :ref:`tutorial_part1`
    * :ref:`installation`
    * :ref:`simple_rewriting`
        * :ref:`graph_creation`
        * :ref:`advanced_attributes`
        * :ref:`rewiting_rules`
* :ref:`tutorial_part2`
    * :ref:`hierarchy_tutorial`
        * :ref:`hierarchy_creation`
        * :ref:`rewriting_in_hierarchy`
        * :ref:`propagation_in_hierarchy`


.. _tutorial_part1:

================
Tutorial: part 1
================

.. _installation:

------------
Installation 
------------

    In order to install the ReGraph library you have to clone this repository using SSH

    .. code-block:: console

        git clone git@github.com:Kappa-Dev/ReGraph.git

    or using HTTPS

    .. code-block:: console

        git clone https://github.com/Kappa-Dev/ReGraph.git


    Install the library and its dependencies with `setup.py`

    .. code-block:: console

        cd ReGraph
        python setup.py install

.. _simple_rewriting:

----------------------
Simple graph rewriting
----------------------

ReGraph works with NetworkX v1 graph objects, both undirected graphs (`networkx.Graph`) and directed ones (`networkx.DiGraph`). The workflow of the graph initialization in NetworkX can be found `here <https://networkx.github.io/documentation/networkx-1.9.1/tutorial/tutorial.html>`_. This tutorial consists of some examples of usage of the functionality provided by the ReGraph library.



.. _graph_creation:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Primitive graph transformations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create an empty NetworkX graph object:
::
    import networkx as nx

    graph = nx.DiGraph()

Define nodes and edges (possibly equipped with attributes), then add them to the graph
using ReGraph primitives `regraph.primitives.add_nodes_from` and
`regraph.primitives.add_edges_from`.::

    import regraph as rg

    nodes = [
        (1, {"name": "alice", "color": "blue"}),
        (2, {"name": "bob", "color": "blue"}),
        (3, {"name": "john", "color": "red"})
    ]
    edges = [
        (1, 2),
        (3, 2, {"friends": False})
    ]
    rg.add_nodes_from(graph, nodes)
    rg.add_edges_from(graph, edges)

We can plot this graph:

>>> rg.plot_graph(graph)

.. image:: _images/graph1.png

Add attributes to the the nodes/edges of the graph:

>>> rg.add_node_attrs(graph, 1, {"age": 20})
>>> graph.nodes[1]
{"name": {"alice"}, "color": {"blue"}, {"age": {20}}}
>>> rg.add_edge_attrs(graph, 1, 2, {"friends": True})
>>> graph.edges[1, 2]
{"friends": {True}}

Remove attributes from the nodes/edges of the graph:

>>> rg.remove_node_attrs(graph, 3, {"color": "red"})
>>> graph.nodes[3]
{"name": {"john"}}
>>> rg.remove_edge_attrs(graph, 3, 2, {"friends": False})
>>> graph.edges[3, 2]
{}

Clone a node of the graph:

>>> rg.clone_node(graph, 2, "2_clone")
'2_clone'
>>> graph.nodes()
[1, 2, "2_clone", 3]
>>> graph.edges()
[(1, 2), (1, "2_clone"), (3, 2), (3, "2_clone")]

The new node corresponding to the clone is created in the hierarchy, and 
all the nodes adjacent to the original node become connected to the clone as well:

.. image:: _images/graph1_clone.png

Merge two nodes of the graph.

>>> rg.merge_nodes(graph, [1, 3])
>>> graph.nodes()
["1_3", 2, "2_clone"]
>>> graph.edges()
[("1_3", 2), ("1_3", "2_clone")]
>>> rg.get_node(graph, "1_3")
{"name": {"alice", "john"}, "color": {"blue"}}
>>> rg.get_edge(graph, "1_3", 2)
{"friends": {True}}
>>> rg.get_edge(graph, "1_3", "2_clone")
{"friends": {True}}

The original nodes are removed, instead a new node corresponding
to the result of merge is created. All the edges incident to the original nodes
stay incident to the result of merge, and all the attribute dictionaries of nodes/edges
are merged.

.. image:: _images/graph1_merge.png

Dump your graph object to its JSON representation (Python dict):

>>> json_data = rg.graph_to_json(graph)
>>> json_data.keys()
dict_keys(["nodes", "edges"])
>>> json_data["nodes"]
[
    {
        "id": "1_3",
        "attrs": {
            "name": {
                "type": "FiniteSet",
                "data": ["alice", "john"]
            },
            "color": {
                "type": "FiniteSet",
                "data": ["blue"]
            }
        }
    },
    {
        "id": 2,
        "attrs": {
            "name": {
                "type": "FiniteSet",
                "data": ["bob"]
            },
            "color": {
                "type": "FiniteSet",
                "data": ["blue"]
            }
        }
    },
    {
        "id": "2_clone",
        "attrs": {
            "name": {
                "type": "FiniteSet",
                "data": ["bob"]
            },
            "color": {
                "type": "FiniteSet",
                "data": ["blue"]
            }
        }
    }
]
>>> json_data["edges"]
[
    {
        "from": "1_3",
        "to": 2,
        "attrs": {
            "friends": {
                "type": "FiniteSet",
                "data": [True]
            }
        }
    },
    {
        "from": "1_3",
        "to": "2_clone",
        "attrs": {
            "friends": {
                "type": "FiniteSet",
                "data": [True]
            }
        }
    }
]


Note that the attributes of the nodes/edges added using `regraph.primitives` are
Python dictionaries, whose keys correspond to the attribute names, but whose
values are converted by primitives to :ref:`attribute_sets` objects
(which is reflected in their JSON serialization as well):

>>> type(get_node(graph, "1_3")["name"])
regraph.attribute_sets.FiniteSet

For more details on attribute sets see the next section :ref:`advanced_attributes`.


Consider the following pattern graph:

>>> pattern = nx.DiGraph()
>>> rg.add_nodes_from(pattern, ["x", "y"])
>>> rg.add_edges_from(pattern, [("x", "y", {"friends": True})])

Find all the instances of `pattern` in the graph:

>>> instances = rg.find_matching(graph, pattern)
>>> instances
[{"x": "1_3", "y": 2}, {"x": "1_3", "y": "2_clone"}]

Now, let us remove the attributes ``{"friends": True}`` from the edge from "1_3" to 2:

>>> rg.remove_edge_attrs(graph, "1_3", 2, {"friends": {True}})

Then, find again all the instances of `pattern` in the graph:

>>> instances = rg.find_matching(graph, pattern)
>>> instances
[{"x": "1_3", "y": "2_clone"}]

As can be seen, the pattern has only one instance in the graph, as the edge between "1_3" and 2
no longer satisfies the condition of the presence of the attribute ``{"friends": {True}})``
imposed in the pattern's edge from "x" to "y"

This example can be found in the following :download:`script <_static/tutorial1_ex1.py>`.

See more
--------

Module reference: :ref:`primitives`


.. _advanced_attributes:

^^^^^^^^^^^^^^^^^^^
Advanced attributes
^^^^^^^^^^^^^^^^^^^

ReGraph implements a collection of data structures for 
representation of potentially infinite sets of attribute values,
together with all the default set operations on them (such as union,
intersection, inclusion test etc.):

* `FiniteSet` -- wrapper for Python finite sets.
* `RegexSet` -- a class for possibly infinite sets of strings given by
  regular expressions.
* `IntegerSet` -- a class for possibly infinite sets of integers
  defined by a set of disjoint intervals.

Import module containing attribute sets data structures:

::

    import regraph.attribute_sets as atsets

Define an infinite integer set:

>>> from math import inf
>>> ints = atsets.IntegerSet({(0, 8), (11, inf)})

Test if interger value is in the set:

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


.. >>> atsets.RexegSet
.. >>> atsets.UniversalSet
.. >>> atsets.EmptySet
.. >>> fs = atsets.FiniteSet({1, 2, 3, 10})

This example can be found in the following :download:`script <_static/tutorial1_ex2.py>`.


See more
--------

Module reference: :ref:`attribute_sets`


.. _rewiting_rules:

^^^^^^^^^^^^^^^
Rewriting rules
^^^^^^^^^^^^^^^

In the context of ReGraph, by rewriting rules we mean the rules of
*sesqui-pushout rewriting* (see more details `here <https://link.springer.com/chapter/10.1007/11841883_4>`_).
A rewriting rule consists of the three graphs: `p` -- preserved part, `lhs` -- left hand side, `rhs` -- right hand side, and two mappings: from `p` to `lhs` and from `p` to `rhs`.
    
Informally, `lhs` represents a pattern to match in a graph, subject to rewriting. `p` together with `p` -> `lhs` mapping specifies a part of the pattern which stays preseved during rewriting, i.e. all the nodes/edges/attributes present in `lhs` but not `p` will be removed. `rhs` and `p` -> `rhs` specify
nodes/edges/attributes to add to the `p`. In addition, rules defined is such a way allow to clone and merge nodes.
If two nodes from `p` map to the same node in `lhs`, the node corresponding to this node of the
pattern will be cloned. Symmetrically, if two nodes from `p` map to the same node in `rhs`,
the corresponding two nodes will be merged.

The following examples will hopefully illustrate the idea behind the sesqui-pushout rewriting rules more clearly:

Create a rewriting rule: 
::

    from regraph import Rule
    from regraph import plot_rule
    from regraph import primitives


    # Define the left-hand side of the rule
    lhs = nx.DiGraph()
    primitives.add_nodes_from(lhs, [1, 2, 3])
    primitives.add_edges_from(lhs, [(1, 2), (2, 3)])

    # Define the preserved part of the rule
    p = nx.DiGraph()
    primitives.add_nodes_from(p, [1, "1_clone", 2, 3])
    primitives.add_edges_from(p, [(1, 2), ("1_clone", 2)])

    # Define the right-hand side of the rule
    rhs = nx.DiGraph()
    primitives.add_nodes_from(rhs, [1, "1_clone", 2, 3, "new_node"])
    primitives.add_edges_from(rhs, [(1, 2), ("1_clone", 2), ("new_node", 1)])

    p_lhs = {1: 1, "1_clone": 1, 2: 2, 3: 3}
    p_rhs = {1: 1, "1_clone": 1, 2: 2, 3: 3}

    # Initialize a rule object
    rule1 = Rule(p, lhs, rhs, p_lhs)

    plot_rule(rule1)

Invoking the `plot_rule` function on the last line produces the following plot of the rule:

.. image:: _images/rule1.png

From this plot we can see that the node `1` is cloned and its clone is represented with the node `1_clone`,
then the edge between the nodes `2` and `3` is removed, and finally, the new node (with id `new_node`) is created and attached with an edge to the `1_clone` node.

Now, let's try to apply this rule and rewrite some graph, for example the following one:

::
    graph = nx.DiGraph()
    nodes = ["a", "b", "c", "d"]
    edges = [("a", "b"), ("a", "c"), ("c", "d")]
    rg.add_nodes_from(graph, nodes)
    rg.add_edges_from(graph, edges)
    pos = rg.plot_graph(graph)


.. image:: _images/graph_to_rewrite.png

First, we need to find instances of the `lhs` of the rule in this graph,
which can be done by `regraph.primitives.find_matching` function presented above:

>>> instances = rg.find_matching(graph, rule1.lhs)
>>> instances
[{1: 'a', 2: 'c', 3: 'd'}]

We can also plot the instance in the graph:

>>> plot_instance(graph, rule1.lhs, instances[0], parent_pos=pos)

.. image:: _images/graph_to_rewrite_instance.png

Finally, perform graph rewriting on the instance that was found:

>>> new_graph, rhs_instance = rule1.apply_to(graph, instances[0])

The method `apply_to` retured two values: first, a new graph -- the result of 
rewriting, second, a mapping from the `rhs` of the rule to the resulting graph.
Plot the new graph and the `rhs` instance:

>>> plot_instance(new_graph, rule1.rhs, rhs_instance, parent_pos=pos)

.. image:: _images/graph_to_rewrite_result.png


::

    pattern = nx.DiGraph()
    rg.add_nodes_from(pattern, [1, 2, 3])
    rg.add_edges_from(pattern, [(1, 2), (2, 3)])

    new_rule1 = Rule.from_transform(pattern)
    new_rule1.inject_clone_node(1)
    new_rule1.inject_remove_edge(2, 3)
    new_rule1.inject_add_node("new_node")
    new_rule1.inject_add_edge("new_node", 1)
    plot_rule(new_rule1)



Continue to :ref:`tutorial_part2` to learn about graph hierarchies.