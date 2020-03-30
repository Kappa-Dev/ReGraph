.. ReGraph documentation master file, created by
   sphinx-quickstart on Mon Dec  4 16:51:07 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to ReGraph's documentation!
===================================

The ReGraph Python library is a generic framework for building graph-based knowledge representations.


ReGraph provides various utilities for rewriting simple graphs with attributes (based on the `sesqui-pushout rewriting <https://ncatlab.org/nlab/show/span+rewriting#sesquipushout_rewriting/>`_ approach). It allows the user to create and manipulate graph objects equipped with dictionary attributes, create rewriting rules, apply them to graphs, construct graph hierarchies and perform rewriting and propagation in these hierarchies. Moreover, it provides tools for audit of updates performed in individual graph objects as well as hierarchies of graphs.

ReGraph supports two graph backends: in-memory `NetworkX  <https://networkx.github.io/>`_ graph objects (directed graphs) and persistent `Neo4j  <https://neo4j.com/>`_ property graphs.

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Tutorials
=========
* :ref:`network_tutorial1`
    * :ref:`nx_tutorial_part1`
    * :ref:`nx_tutorial_part2`
* :ref:`neo4j_tutorial1`
    * :ref:`n4_tutorial_part1`
    * :ref:`n4_tutorial_part2`
* :ref:`tutorial_rules`
    * :ref:`tutorial_rules1`
    * :ref:`tutorial_rules2`
* :ref:`advanced_attributes`
* :ref:`audit_tutorial`
* :ref:`audit_tutorial_hierarchies`
* :ref:`tutorial_typedneo4j`


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
