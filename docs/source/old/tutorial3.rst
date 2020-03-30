
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
* :ref:`tutorial_part3`
    * :ref:`neo4j_tutorial`
        * :ref:`neo4j_graph_tutorial`
        * :ref:`typed_neo4j_graph_tutorial`
        * :ref:`neo4j_hierarchy_tutorial`


.. _tutorial_part3:

Tutorial: part 3
================

.. _neo4j_tutorial:

-------------------------------
Rewriting Neo4j property graphs
-------------------------------

So far in this tutorial we have used NetworkX graphs. Such graphs were in-memory objects whose lifetime was limited by the lifetime of our Python applications (unless they where exported to some external representation, e.g. JSON-files). Unsurprisingly, it is often desirable to build our knowledge representation systems on graphs that would be persistent (whose lifetime would therefore be independent from the one of the application manipulating them, not mentioning scalability issues related to working with in-memory graphs). For this reason  ReGraph allows to use most of its functionality on `Neo4j <https://neo4j.com/>`_ property graphs.

ReGraph provides three data structures that allow the user to work with Neo4j property graphs in the backend:

- `regraph.neo4j.Neo4jGraph` for simple graphs
- `regraph.neo4j.TypedNeo4jGraph` for simple graphs typed by a simple graph (in this context called schema)
- `regraph.neo4j.Neo4jHierarchy` for simple graphs structured in a graph hierarchy


.. _neo4j_graph_tutorial:

^^^^^^^^^^^^^^^^^
Neo4jGraph object
^^^^^^^^^^^^^^^^^

"""""""""""""""""""""
Starting Neo4j server
"""""""""""""""""""""

- When installing neo4j you will be asked to choose login/password for you DB (in this example we assume it is "neo4j"/"admin"). 

- To start neo4j server run `sudo service neo4j start`

- Check status by running `sudo service neo4j status`. Here you can check the bolt port uri needed to initialize our Neo4jGraph object.

- You can also query the DB by using the Neo4j browser, the address can be found also in the result of 'status', e.g. "Remote interface available at http://localhost:7474/".

""""""""""""""""""""""""
Creating Neo4jGraph objects
""""""""""""""""""""""""

Creation of `Neo4jGraph` object initializes a driver that provides connection to a Neo4j database. It can be created providing credentials necessary to connect to the DB (uri, username, password). ::

    from regraph.neo4j import Neo4jGraph


    g = Neo4jGraph(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="admin",
        node_label="Person",
        edge_label="KNOWS")

Alternatively, an existing driver can be used, for example:
::
    from regraph.neo4j import Neo4jGraph
    from neo4j.v1 import GraphDatabase


    neo4j_driver = GraphDatabase.driver(
        uri, auth=(user, password))
    g = Neo4jGraph(
        driver=neo4j_driver,
        node_label="Person",
        edge_label="KNOWS")

You can now access graph sitting in the DB through the inteface provided by `Neo4jGraph`. Note that when initializing `Neo4jGraph` we have specified node/edge labels (arguments `node_label` and `edge_label`), which means that our graph object will operate _only_ on the subgraph of the property graph stored in the DB induced by the nodes and relations possessing the right labels. In our previous example we will operate on nodes labeled `:Person` and relations of type `:KNOWS`. By default, ReGraph scopes nodes and relations with labels `:node` and `:edge` respectively.

**Node identifiers.** Identifiers for graph elements. For all elements of a proprerty graph (both nodes and edges) Neo4j generates unique internal identifiers. However, these identifiers are unsuitable for our purposes of defining. One of the main reasons for for that is due to
the fact the user has virtually no control over them, i.e. they are automatically allocated,
can be reassigned in some particular scenarios, and as the result. Using them as reference
identifiers in our system can cause dangling reference problems.
Therefore, in the concrete implementation of attribute graphs the value of the property
id is reserved and chosen to encode such an identifier. We also create the uniqueness
constraint on the values of this property for every namespace (corresponding to G and T ,
i.e. the ids of the nodes of the same graph are required to be unique) with the following
two queries:

::

    CREATE CONSTRAINT ON (n:Person) ASSERT n.id IS UNIQUE


Now we can add nodes/edges to the graph using NetworkX-like interface provided by Neo4jGraph. For example:
::

    nodes = [
        ("a", {"name": "Jack", "age": 23,
               "hobby": {"hiking", "music"}, "weight": 75}), 
        ("b", {"name": "Bob", "age": 24,
               "hobby": {"sport", "music"}, "height": 178}),
        "c", 
        ("d", {"name": "Paul"}), "e", "f"
    ]
    edges = [
        ("a", "b", {"type": {"friends", "colleagues"}}), 
        ("d", "b", {"type": "enemies"}), 
        ("a", "c"),
        ("d", "a", {"type": "friends"}),
        ("e", "a"), 
        ("f", "d")
    ]
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)

We can also access nodes/edges in a similar way:

>>> g.nodes()
['a', 'b', 'c', 'd', 'e', 'f', 'x']
>>> g.edges()
[('a', 'b'),
 ('a', 'c'),
 ('d', 'b'),
 ('d', 'a'),
 ('e', 'a'),
 ('f', 'd'),
 ('x', 'c')]


as well as node/edge attributes:

>>> g.get_node("a")
{'age': {23}, 'hobby': {'hiking', 'music'}, 'name': {'Jack'}, 'weight': {75}}


To get node's properties on the level of the DB ReGraph performs the following Cypher query:
::

    MATCH (n:node { id: 'a' }) 
    RETURN properties(n) as attributes


"""""""""""""""""""""""""""""""
Primitive graph transformations through Neo4jGraph 
"""""""""""""""""""""""""""""""

ReGraph provides a set of utils (implemented as methods of Neo4jGraph) for node/edge/attribute addition/removal, node cloning and merging. Under the hood of all these utils lie (automatically) generated Cypher queries produced and executed by ReGraph using the DB connection associated with the driver inside of the Neo4jGraph object.

**Attention:** on the current stage of its development, ReGraph assumes that the underlying graphs are **simple** (no multuple edges allowed).

For example, we can do the following:

>>> g.add_node("x", {"name": "Roberto"})
>>> g.add_edge("x", "c", {"type": {"friends", "colleagues"}, "since": 1993})

We can clone and merge nodes as well:

>>> clone_res = g.clone_node('a')
>>> print(clone_res)
a1
>>> g.get_node(clone_res)
{'name': {'Jack'}, 'weight': {75}, 'age': {23}, 'hobby': {'hiking', 'music'}}
>>> g.get_edge(clone_res, 'b')
{'type': {'friends', 'colleagues'}}

>>> merge_res = g.merge_nodes1(["a", "b"])
>>> g.get_node(merge_res)
{'name': {'Jack', 'Bob'}, 'weight': {75}, 'age': {24, 23}, 'height': {178}, 'hobby': {'hiking', 'music', 'sport'}}

You can find all the available utils in :ref:`neo4j_graphs`.


"""""""""""""""""""""
Rewriting Neo4jGraphs
"""""""""""""""""""""

Finally, we can perform rewriting on property graphs manipulated by Neo4jGraph objects in a similar way to the NetworkX graphs.

::

    from regraph import Rule


    pattern = nx.DiGraph()
    pattern.add_nodes_from(["x", "y", "z"])
    pattern.add_edges_from([("y", "x"), ("y", "z"), ("z", "z")])

    rule = Rule.from_transform(pattern)
    clone_name1, _ = rule.inject_clone_node("y")
    clone_name2, _ = rule.inject_clone_node("y")
    rule.inject_remove_edge(clone_name2, "z")
    rule.inject_remove_node("x")
    rule.inject_add_node("new_node")
    rule.inject_add_edge("new_node", "z")
    instances = g.find_matching(pattern)


>>> print(instances[0])
{'x': 'c', 'y': 'a_clone', 'z': 'a_b_d'}

>>> rhs_g = g.rewrite(rule, instances[0])

>>> rhs_g
{'y2': '166399',
 'y1': '166398',
 'new_node': '166400',
 'y': 'a_clone',
 'z': 'a_b_d'}


.. _typed_neo4j_graph_tutorial:

^^^^^^^^^^^^^^^^^^^^^^
TypedNeo4jGraph object
^^^^^^^^^^^^^^^^^^^^^^



.. _neo4j_hierarchy_tutorial:

^^^^^^^^^^^^^^^^^^^^^
Neo4jHierarchy object
^^^^^^^^^^^^^^^^^^^^^
