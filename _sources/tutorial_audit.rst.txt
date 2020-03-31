.. _audit_tutorial:

==============================
Audit trails for graph objects
==============================

ReGraph implements a framework for the version control (VC) of graph transformations

The data structure `VersionedGraph` allows to store the history of transformations of a graph object and perform the following VC operations:

- **Rewrite**: perform a rewriting of the object with a commit to the revision history
- **Branch**: create a new branch (with a diverged version of the graph object)
- **Merge branches**: merge branches
- **Rollback**: rollback to a point in the history of transformations

Let us start this tutorial by performing necessary imports:

::

    from regraph import NXGraph
    from regraph.audit import VersionedGraph
    from regraph.rules import Rule
    from regraph import print_graph, plot_rule, plot_graph

First, we create a graph and pass it to the `VersionedGraph` wrapper that will take care of the version control.

>>> graph_obj = NXGraph()
>>> g = VersionedGraph(graph_obj)

Now let's create a rule that adds to the graph two nodes connected with an edge and apply it. If we want the changes to be commited to the version control we rewrite through the `rewrite` method of a `VersioneGraph` object.


::

    rule = Rule.from_transform(NXGraph())
    rule.inject_add_node("a")
    rule.inject_add_node("b")
    rule.inject_add_edge("a", "b")

    rhs_instance, _ = g.rewrite(rule, {}, message="Add a -> b")
    plot_graph(g.graph)

.. image:: _static/audit/g1.png


We create a new branch called "branch":

>>> branch_commit = g.branch("branch")
>>> print("Branches: ", g.branches())
Branches:  ['master', 'branch']
>>> print("Current branch '{}'".format(g.current_branch()))
Current branch 'branch'

Apply a rule that clones the node 'b' to the current vesion of the graph (branch 'branch').

::

    pattern = NXGraph()
    pattern.add_node("b")
    rule = Rule.from_transform(pattern)
    rule.inject_clone_node("b")
    plot_rule(rule)

    rhs_instance, commit_id = g.rewrite(
        rule,
        {"b": rhs_instance["b"]},
        message="Clone b")
    plot_graph(g.graph)


.. image:: _static/audit/r1.png

.. image:: _static/audit/g2.png

The `rewrite` method of `VersionedGraph` returns the RHS instance of the applied and the id of the newly created commit corresponding to this rewrite.

>>> print("RHS instance: ", rhs_instance)
RHS instance: {'b': 'b1', 'b1': 'b'}
>>> print("Commit ID: ", commit_id)
Commit ID:  afbab03b-2d7c-4363-a3c6-59c6032b9e5b

Switch back to the 'master' branch:

>>> g.switch_branch("master")
>>> print(g.current_branch())
master


Apply a rule that adds a loop form 'a' to itself, a new node 'c' and connects it with 'a':

::

    pattern = NXGraph()
    pattern.add_node("a")
    rule = Rule.from_transform(pattern)
    rule.inject_add_node("c")
    rule.inject_add_edge("c", "a")
    rule.inject_add_edge("a", "a")

    rhs_instance, _ = g.rewrite(rule, {"a": "a"}, message="Add c and c->a")
    plot_graph(g.graph)

.. image:: _static/audit/g3.png

Create a new branch 'dev':

>>> g.branch("dev")
'06ef2284-e360-4733-87c6-dcae7602d3ef'

In this branch remove an edge from 'c' to 'a' and merge two nodes together.


::

    pattern = NXGraph()
    pattern.add_node("c")
    pattern.add_node("a")
    pattern.add_edge("c", "a")
    rule = Rule.from_transform(pattern)
    rule.inject_remove_edge("c", "a")
    rule.inject_merge_nodes(["c", "a"])
    plot_rule(rule)

    g.rewrite(
        rule,
        {"a": rhs_instance["a"], "c": rhs_instance["c"]},
        message="Merge c and a")
    plot_graph(g.graph)


.. image:: _static/audit/r2.png

.. image:: _static/audit/g4.png

Switch back to the 'master' branch:

>>> g.switch_branch("master")

Apply a rule that clones a node 'a'.

::

    pattern = NXGraph()
    pattern.add_node("a")
    rule = Rule.from_transform(pattern)
    _, rhs_clone = rule.inject_clone_node("a")
    rhs_instance, rollback_commit = g.rewrite(
        rule,
        {"a": rhs_instance["a"]},
        message="Clone a")
    plot_graph(g.graph)

.. image:: _static/audit/g5.png


Create a new branch 'test':


>>> g.branch("test")
'fb18eb3d-e663-4f3a-ad11-2fbd03336f87'

In this branch apply the rule that adds a new node 'd' and connects it with an edge to one of the cloned 'a' nodes:


::

    pattern = NXGraph()
    pattern.add_node("a")
    rule = Rule.from_transform(pattern)
    rule.inject_add_node("d")
    rule.inject_add_edge("a", "d")
    g.rewrite(rule, {"a": rhs_instance[rhs_clone]}, message="Add d -> clone of a")
    plot_graph(g.graph)

.. image:: _static/audit/g6.png

Switch back to 'master':

>>> g.switch_branch("master")

Remove a node 'a':

::

    pattern = NXGraph()
    pattern.add_node("a")
    rule = Rule.from_transform(pattern)
    rule.inject_remove_node("a")
    rhs_instance, _ = g.rewrite(
        rule,
        {"a": rhs_instance["a"]},
        message="Remove a")
    plot_graph(g.graph)

.. image:: _static/audit/g7.png

Merge the branch 'dev' into 'master':

>>> g.merge_with("dev")
'7787c77f-c44d-4419-9416-155b139b6e9d'
>>> plot_graph(g.graph)

.. image:: _static/audit/g8.png

Merge 'test' into 'master':

>>> g.merge_with("test")
'd86ac7e8-8868-435d-a108-805341097170'
>>> plot_graph(g.graph)

.. image:: _static/audit/g9.png

We can inspect the version control object in more details and look at its attribute `_revision_graph`, whose nodes represent the commits and whose edges represent graph deltas between different commits (basically, rewriting rules that constitute commits). Here we can see that on the nodes of the revision graph are stored branch names to which commits belong and user specified commit messages.

::

    for n, attrs in g._revision_graph.nodes(data=True):
        print("Node ID: ", n)
        print("Attributes: ")
        print("\t", attrs)

We can pretty-print the entire revision history:

>>> g.print_history()
2020-01-24 14:13:03.731569 0f29d379-e76a-4433-bcc2-97082776b4b6 master Initial commit
2020-01-24 14:13:17.508136 499f6881-ce03-4463-9000-8d4ba714599b master Add a -> b
2020-01-24 14:13:21.678884 a98d7050-be6c-444e-9e1e-c02f40a6efc4 branch Created branch 'branch'
2020-01-24 14:13:26.471732 ee04e1dd-e276-4023-8fd4-299d698f26a1 branch Clone b
2020-01-24 14:13:35.370027 cf32caf3-9c36-4c3b-9119-0472b06c09fc master Add c and c->a
2020-01-24 14:13:37.486220 06ef2284-e360-4733-87c6-dcae7602d3ef dev Created branch 'dev'
2020-01-24 14:13:39.841916 acd5c76f-98b3-40ab-9df9-8e657483f246 dev Merge c and a
2020-01-24 14:13:42.991329 a7d13243-df91-42c5-a38c-16240fa0ae2c master Clone a
2020-01-24 14:13:44.766558 fb18eb3d-e663-4f3a-ad11-2fbd03336f87 test Created branch 'test'
2020-01-24 14:13:46.703745 d79e9972-5d9d-4dc6-9ccb-60a15e34ff64 test Add d -> clone of a
2020-01-24 14:13:49.858790 5fc6208f-03e2-4134-bc36-1daac67a8359 master Remove a
2020-01-24 14:13:51.439732 7787c77f-c44d-4419-9416-155b139b6e9d master Merged branch 'dev' into 'master'
2020-01-24 14:13:53.726947 d86ac7e8-8868-435d-a108-805341097170 master Merged branch 'test' into 'master'


Now we can rollback to some previous commit (commit where we first cloned the node 'a'):

>>> g.rollback(rollback_commit)
Created the new head for 'dev'
Created the new head for 'master'

Now the following snippet:

::

    print("Branches: ", g.branches())
    print("Current branch '{}'".format(g.current_branch()))
    plot_graph(g.graph)

outputs:

::

    Branches:  ['master', 'branch', 'dev']
    Current branch 'master'

.. image:: _static/audit/g10.png

Let us see the updated revision history:

>>> g.print_history()
2020-01-24 14:13:03.731569 0f29d379-e76a-4433-bcc2-97082776b4b6 master Initial commit
2020-01-24 14:13:17.508136 499f6881-ce03-4463-9000-8d4ba714599b master Add a -> b
2020-01-24 14:13:21.678884 a98d7050-be6c-444e-9e1e-c02f40a6efc4 branch Created branch 'branch'
2020-01-24 14:13:26.471732 ee04e1dd-e276-4023-8fd4-299d698f26a1 branch Clone b
2020-01-24 14:13:35.370027 cf32caf3-9c36-4c3b-9119-0472b06c09fc master Add c and c->a
2020-01-24 14:13:37.486220 06ef2284-e360-4733-87c6-dcae7602d3ef dev Created branch 'dev'
2020-01-24 14:13:39.841916 acd5c76f-98b3-40ab-9df9-8e657483f246 dev Merge c and a
2020-01-24 14:13:42.991329 a7d13243-df91-42c5-a38c-16240fa0ae2c master Clone a


---------
See more
--------

Module reference: :ref:`audit`
