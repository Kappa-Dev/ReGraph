.. _tutorial:

Tutorial
========

* :ref:`installation`
* :ref:`simple_rewriting`
    * :ref:`graph_creation`
    * :ref:`advanced_attributes`
    * :ref:`rewiting_rules`
* :ref:`hierarchy`
    * :ref:`hierarchy_creation`
    * :ref:`rewriting_in_hierarchy`
    * :ref:`propagation_in_hierarchy`

.. _installation:

============
Installation 
============

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

=========================================
Simple graph rewriting
=========================================

ReGraph works with NetworkX v1 graph objects, both undirected graphs (`networkx.Graph`) and directed ones (`networkx.DiGraph`). The workflow of the graph initialization in NetworkX can be found `here <https://networkx.github.io/documentation/networkx-1.9.1/tutorial/tutorial.html>`_. This tutorial consists of some examples of usage of the functionality provided by the ReGraph library.



.. _graph_creation:

--------------------------------------------------
Primitive graph transformations
--------------------------------------------------

Create an empty NetworkX graph object:
::
    import networkx as nx

    graph = nx.DiGraph()

Define nodes and edges (possibly equipped with attributes), then add them to the graph
using ReGraph primitives `regraph.primitives.add_nodes_from` and
`regraph.primitives.add_edges_from`.::

    from regraph import primitives

    nodes = [
        (1, {"name": "alice", "color": "blue"}),
        (2, {"name": "bob", "color": "blue"}),
        (3, {"name": "john", "color": "red"})
    ]
    edges = [
        (1, 2),
        (3, 2, {"friends": False})
    ]
    primitives.add_nodes_from(graph, nodes)
    primitives.add_edges_from(graph, edges)

Add attributes to the the nodes/edges of the graph:

>>> primitives.add_node_attrs(graph, 1, {"age": 20})
>>> graph.node[1]
{"name": {"alice"}, "color": {"blue"}, {"age": {20}}}
>>> primitives.add_edge_attrs(graph, 1, 2, {"friends": True})
>>> graph.edge[1][2]
{"friends": {True}}

Remove attributes from the nodes/edges of the graph:

>>> primitives.remove_node_attrs(graph, 3, {"color": "red"})
>>> graph.node[3]
{"name": {"john"}}
>>> primitives.remove_edge_attrs(graph, 3, 2, {"friends": False})
>>> graph.edge[3][2]
{}

Clone a node of the graph:

>>> primitives.clone_node(graph, 2, "2_clone")
>>> graph.nodes()
[1, 2, "2_clone", 3]
>>> graph.edges()
[(1, 2), (1, "2_clone"), (3, 2), (3, "2_clone")]

The new node corresponding to the clone is created in the hierarchy, and 
all the nodes adjacent to the original node become connected to the clone as well.

Merge two nodes of the graph.

>>> primitives.merge_nodes(graph, [1, 3])
>>> graph.nodes()
["1_3", 2, "2_clone"]
>>> graph.edges()
[("1_3", 2), ("1_3", "2_clone")]
>>> graph.node["1_3"]
{"name": {"alice", "john"}, "color": {"blue"}}
>>> graph.edge["1_3"][2]
{"friends": {True}}
>>> graph.edge["1_3"]["2_clone"]
{"friends": {True}}

The original nodes are removed, instead a new node corresponding
to the result of merge is created. All the edges incident to the original nodes
stay incident to the result of merge, and all the attribute dictionaries of nodes/edges
are merged.

Dump your graph object to its JSON representation (Python dict):

>>> json_data = primitives.graph_to_json(graph)
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

>>> type(graph.node["1_3"]["name"])
regraph.attribute_sets.FiniteSet

For more details on attribute sets see the next section :ref:`advanced_attributes`.


Consider the following pattern graph:

>>> pattern = nx.DiGraph()
>>> primitives.add_nodes_from(pattern, ["x", "y"])
>>> primitives.add_edges_from(pattern, [("x", "y", {"friends": True})])

Find all the instances of `pattern` in the graph:

>>> instances = primitives.find_matching(graph, pattern)
>>> instances
[{"x": "1_3", "y": 2}, {"x": "1_3", "y": "2_clone"}]

Now, let us remove the attributes ``{"friends": True}`` from the edge from "1_3" to 2:

>>> primitives.remove_edge_attrs(graph, "1_3", 2, {"friends": {True}})

Then, find again all the instances of `pattern` in the graph:

>>> instances = primitives.find_matching(graph, pattern)
>>> instances
[{"x": "1_3", "y": "2_clone"}]

As can be seen, the pattern has only one instance in the graph, as the edge between "1_3" and 2
no longer satisfies the condition of the presence of the attribute ``{"friends": {True}})``
imposed in the pattern's edge from "x" to "y"

See more
--------

Module reference: :ref:`primitives`


.. _advanced_attributes:

-------------------
Advanced attributes
-------------------

.. _rewiting_rules:

---------------
Rewriting rules
---------------

.. _hierarchy_tutorial:

=========
Hierarchy
=========
    
.. _hierarchy_creation:

------------------
Hierarchy creation
------------------

.. _rewriting_in_hierarchy:

--------------------------
Rewriting in the hierarchy
--------------------------

.. _propagation_in_hierarchy:

----------------------------
Propagation in the hierarchy
----------------------------
