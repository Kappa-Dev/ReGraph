
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


.. _tutorial_part2:

Tutorial: part 2
================


If you missed the part of the ReGraph tutorial about primitive graph transformations, advanced graph attributes and rewriting rules, go back to :ref:`tutorial_part1`.


.. _hierarchy_tutorial:

---------
Hierarchy
---------

A graph hierarchy is a directed acyclic graph where nodes are graphs with attributes and edges are
homomorphisms representing graph typing in the system. This construction provides means
for mathematically robust procedures of propagation of changes (expressed through graph rewriting
rules) on any level of the hierarchy, up to all the graphs which are transitively typed by the graph
subject to rewriting. In the following section we give a simple example of such hierarchy and its
functionality implemented in ReGraph.

.. _hierarchy_creation:

^^^^^^^^^^^^^^^^^^
Hierarchy creation
^^^^^^^^^^^^^^^^^^
Create an empty hierarchy and add graphs to the hierarchy: ::
    
    import networkx as nx

    from regraph import Hierarchy, plot_graph, primitives


    hierarchy = Hierarchy()

    t = nx.DiGraph()
    primitives.add_nodes_from(
        ["agent", "action", "state"])
    primitives.add_edges_from([
        ("agent", "agent"),
        ("state", "agent"),
        ("agent", "action"),
        ("action", "state")
    ])

    g = nx.DiGraph()
    primitives.add_nodes_from(
        ["protein", "region",
         "activity", "mod"])
    primitives.add_edges_from([
        ("region", "protein"),
        ("activity", "protein"),
        ("activity", "region"),
        ("protein", "mod"),
        ("region", "mod"),
        ("")
    ])

    hierarchy.add_graph("T", t)
    hierarchy.add_graph("G", g)
    

>>> plot_graph(hierarchy.graph["T"])

.. image:: _images/ex1_meta_meta_model.png

>>> plot_graph(hierarchy.graph["G"])

.. image:: _static/ex1_meta_model.png


>>> hierarchy.graphs()
['T', 'G']

Add typing of the graph `G` by `T`: ::
    
    mapping = {
        "protein": "agent",
        "region": "agent",
        "activity": "state",
        "mod": "action"
    }
    hierarchy.add_typing("G", "T", mapping)

>>> hierarchy.typing["G"]["T"]
{'activity': 'state', 'mod': 'action', 'protein': 'agent', 'region': 'agent'}

You can check typing of a particular node of a graph, for example:

>>> hierarchy.node_type("G", "region")
{'T': 'agent'}

Create another graph, let's call it `model`, and type it by `G` ::
    
    model = nx.DiGraph()
    primitives.add_nodes_from(
        model,
        ["A", "R", "B", "B_activity",
         "A_activity", "activation"])
    primitives.add_edges_from(model, [
        ("R", "A"),
        ("R", "activation"),
        ("activation", "B_activity"),
        ("B_activity", "B"),
        ("activation", "A_activity"),
        ("A_activity", "A")
    ])
    hierarchy.add_graph("model", model)

    mapping = {
        "A": "protein",
        "R": "region",
        "B": "protein",
        "B_activity": "activity",
        "A_activity": "activity",
        "activation": "mod"
    }
    hierarchy.add_typing("model", "G", mapping)

    plot_graph(hierarchy.graph["model"])

.. image:: _static/ex1_model.png

>>> hierarchy.typings()
[('G', 'T'), ('model', 'G')]

Remove a node from the hierarchy and reconnect its predecessors with its successors:

>>> hierarchy.remove_node("G", reconnect=True)
>>> hierarchy.typings()
[('model', 'T')]
>>> hierarchy.typing["model"]["T"]
{'A': 'agent',
 'B': 'agent',
 'B_activity': 'state',
 'A_activity': 'state',
 'R': 'agent',
 'activation': 'action'}

Graph hierarchy allows to accommodate binary symmetric relations on graphs.
Consider the following graph:

::

    catalysis = nx.DiGraph()
    primitives.add_nodes_from(
        catalysis,
        ["enzyme", "substrate",
         "mod", "mod_state"]
    )
    primitives.add_edges_from(catalysis, [
        ("enzyme", "mod"),
        ("mod", "mod_state"),
        ("mod_state", "substrate")
    ])

    hierarchy.add_graph("catalysis", catalysis)

    plot_graph(hierarchy.graph["catalysis"])


.. image:: _static/ex1_catalysis.png

Create a relation between graph `model` and graph `catalysis`: ::

    relation = {
        "A": {"enzyme", "substrate"},
        "B": "substrate",
        "B_activity": "mod_state",
        "A_activity": "mod_state",
        "activation": "mod"
    }
    hierarchy.add_relation('model', 'catalysis', relation)

Note that in a relation between two graphs a node from one graph can be related to a set of nodes
from another graph (in our example node `A` in the graph `model` is related to both
`enzyme` and `substrate` from the graph `catalysis`):

>>> hierarchy.relation['model']['catalysis']
{'A': {'enzyme', 'substrate'},
 'A_activity': {'mod_state'},
 'B': {'substrate'},
 'B_activity': {'mod_state'},
 'activation': {'mod'}}
>>> hierarchy.relation['catalysis']['model']
{'enzyme': {'A'},
 'mod': {'activation'},
 'mod_state': {'A_activity', 'B_activity'},
 'substrate': {'A', 'B'}}

.. _rewriting_in_hierarchy:

^^^^^^^^^^^^^^^^^^^^^^^^^^
Rewriting in the hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^^
