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

ReGraph works with NetworkX v1 graph objects, both undirected graphs (`networkx.Graph`) and directed ones (`networkx.DiGraph`). The workflow of the graph initialization in NetworkX can be found `here <https://networkx.github.io/documentation/networkx-1.9.1/tutorial/tutorial.html>`_.



.. _graph_creation:

--------------------------------------------------
Applying primitive graph transformations
--------------------------------------------------

::

	graph = nx.DiGraph()
	add_nodes_from(graph,
	    [
	        ('1', {'name': 'EGFR', 'state': 'p'}),
	        ('2', {'name': 'BND'}),
	        ('3', {'name': 'Grb2', 'aa': 'S', 'loc': 90}),
	        ('4', {'name': 'SH2'}),
	        ('5', {'name': 'EGFR'}),
	        ('6', {'name': 'BND'}),
	        ('7', {'name': 'Grb2'}),
	        ('8', {'name': 'WAF1'}),
	        ('9', {'name': 'BND'}),
	        ('10', {'name': 'G1-S/CDK', 'state': 'p'}),
	])
	edges = [
	    ('1', '2', {'s': 'p'}),
	    ('4', '2', {'s': 'u'}),
	    ('4', '3'),
	    ('5', '6', {'s': 'p'}),
	    ('7', '6', {'s': 'u'}),
	    ('8', '9'),
	    ('9', '8'),
	    ('10', '8', {"a": {1}}),
	    ('10', '9', {"a": {2}}),
	    ('5', '2', {'s': 'u'})
	]

	add_edges_from(graph, edges)


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
