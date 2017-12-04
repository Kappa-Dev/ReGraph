.. ReGraph documentation master file, created by
   sphinx-quickstart on Mon Dec  4 16:51:07 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to ReGraph's documentation!
===================================

The ReGraph library is a generic framework for modelling graph-based systems, where models are viewed as graphs and graph transformations are viewed as a tool to describe both the system evolution and the model evolution.

ReGraph provides various utilities for graph rewriting (based on the sesqui-pushout rewriting procedure). It enables a user to define a typing for models (graphs) that gives specifications for the structure of the models. This later functionality allows both to preserve the specified structure during rewriting and to propagate the changes to the specifications to the models.

ReGraph contains a collection of utilities for graph rewriting on `NetworkX (version 1)  <https://networkx.github.io/>`_ graph objects, both undirected and directed graphs.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

User's Guide
============

* :ref:`installation`
* :ref:`tutorial`


Reference
=========

* :ref:`primitives`
* :ref:`rules`
* :ref:`attributes`


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
