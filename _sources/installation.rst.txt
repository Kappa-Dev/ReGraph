.. _installation:

============
Installation 
============

1. Clone this repository using SSH

.. code-block:: console

    git clone git@github.com:Kappa-Dev/ReGraph.git

or using HTTPS

.. code-block:: console

    git clone https://github.com/Kappa-Dev/ReGraph.git


2. Install the library and its dependencies with `setup.py`

.. code-block:: console

    cd ReGraph
    python setup.py install

------------------------------------
Neo4j installation and configuration
------------------------------------

1. If you want to use the Neo4j-based backend of ReGraph, you need to install the Neo4j database (see installation `instructions <https://neo4j.com/docs/operations-manual/current/installation/>`_). 


2. Moreover, ReGraph uses the APOC Neo4j plugin, currently not included in the community edition. To install the plugin see the `instructions <https://github.com/neo4j-contrib/neo4j-apoc-procedures/blob/4.0/readme.adoc>`_.

3. ReGraph uses `Neo4j Bolt Driver for Python <https://neo4j.com/docs/api/python-driver/current/#>`_, therefore, having set up your database, you need to provide to ReGraph's API the address of the bolt server (for example, `bolt://127.0.0.1:7687`) and your credentials for connecting the database (i.e. user and password).

