.. ReGraph documentation master file, created by
   sphinx-quickstart on Mon Dec  4 16:51:07 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to ReGraph's documentation!
===================================

The ReGraph Python library is a generic framework for modelling graph-based systems.

ReGraph provides various utilities for graph rewriting (based on the sesqui-pushout rewriting procedure). It enables a user to define a typing for models (graphs) that gives specifications for the structure of the models. This later functionality allows both to preserve the specified structure during rewriting and to propagate the changes to the specifications to the models.

ReGraph contains a collection of utilities for graph rewriting. It supports graphs based on two backends: `NetworkX  <https://networkx.github.io/>`_ graph objects (both undirected and directed graphs) and `Neo4j  <https://neo4j.com/>`_ property graphs.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

:ref:`tutorial`
==============

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



:ref:`modules`
================

* :ref:`graphs`
* :ref:`hierarchies`
* :ref:`attribute_sets`
* :ref:`rules`
* :ref:`nxgraphs`
* :ref:`neo4jgraphs`
* :ref:`nxhierarchies`
* :ref:`neo4jhierarchies`
* :ref:`audit`
* :ref:`exceptions`


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
