.. _audit_tutorial_hierarchies:

==================================
Audit trails for hierarchy objects
==================================


ReGraph implements a framework for the version control (VC) of graph transformations in hierarchies.

The data structure `VersionedHierarchy` allows to store the history of transformations of a hierarchy and perform the following VC operations:

- **Rewrite**: perform a rewriting of the hierarchy with a commit to the revision history
- **Branch**: create a new branch (with a diverged version of the graph object)
- **Merge branches**: merge branches
- **Rollback**: rollback to a point in the history of transformations

Let us start this tutorial by performing necessary imports:

::

    from regraph import NXGraph, NXHierarchy
    from regraph.audit import VersionedHierarchy
    from regraph.rules import Rule
    from regraph import print_graph, plot_rule, plot_graph

Let us now create a small hierarchy.

::

    hierarchy = NXHierarchy()

    shapes = NXGraph()
    shapes.add_nodes_from(["circle", "square"])
    hierarchy.add_graph("shapes", shapes)

    colors = NXGraph()
    colors.add_nodes_from(["white", "black"])
    hierarchy.add_graph("colors", colors)

    ag = NXGraph()
    ag.add_nodes_from(
        ["wc", "bc", "ws", "bs"])
    hierarchy.add_graph("metamodel", ag)

    nugget = NXGraph()
    nugget.add_nodes_from(
        ["wc1", "wc2", "bc1", "ws1", "bs2"])
    hierarchy.add_graph("data", nugget)

    hierarchy.add_typing(
        "metamodel", "shapes", {
            "wc": "circle",
            "bc": "circle",
            "ws": "square",
            "bs": "square"
        })
    hierarchy.add_typing(
        "metamodel", "colors", {
            "wc": "white",
            "bc": "black",
            "ws": "white",
            "bs": "black"
        })
    hierarchy.add_typing(
        "data", "metamodel", {
            "wc1": "wc",
            "wc2": "wc",
            "bc1": "bc",
            "ws1": "ws",
            "bs2": "bs"
        })
    hierarchy.add_typing(
        "data", "colors", {
            "wc1": "white",
            "wc2": "white",
            "bc1": "black",
            "ws1": "white",
            "bs2": "black"
        })

    base = NXGraph()
    base.add_nodes_from(["node"])
    hierarchy.add_graph("base", base)
    hierarchy.add_typing(
        "colors",
        "base", {
            "white": "node",
            "black": "node"
        })

We pass the hierarchy to the `VersionedHierarchy` wrapper that will take care of the version control:

>>> h = VersionedHierarchy(hierarchy)
>>> print("Branches: ", h.branches())
Branches:  ['master']
>>> print("Current branch: ", h.current_branch())
Current branch:  master

Let us create a new branch `test1`:

>>> h.branch("test1")

We will now rewrite our hierarchy at the current branch of the audit trail.

::

    pattern = NXGraph()
    pattern.add_nodes_from(["s"])
    rule = Rule.from_transform(pattern)
    rule.inject_remove_node("s")

    rhs_instances, commit_id = h.rewrite(
        "shapes",
        rule, {"s": "square"},
        message="Remove square in shapes")


The `rewrite` method of `VersionedHierarchy` returns the instances of the RHS of the applied rule in different graphs and the id of the newly created commit corresponding to this rewrite.

>>> print(rhs_instances)
{'shapes': {}, 'metamodel': {}, 'data': {}, 'colors': {'ws': 'white', 'bs': 'black'}, 'base': {'bs_ws': 'node'}}
>>> print(commit_id)
5ebdb406-eee6-44b9-a2a0-005e4b5ef94f

We switch back to the `master` branch.

>>> h.switch_branch("master")

We will now rewrite the hierarchy corresponding to the current branch.

::
    
    pattern = NXGraph()
    pattern.add_nodes_from(["wc"])

    rule = Rule.from_transform(pattern)
    rule.inject_clone_node("wc")

    _, clone_commit = h.rewrite(
        "metamodel",
        rule, {"wc": "wc"},
        message="Clone 'wc' in ag")


After running the snippet above, we obtain the following resivions history:

>>> h.print_history()
2020-01-24 14:37:14.627367 78f98e3c-2361-4d96-9737-31678d507ac6 master Initial commit
2020-01-24 14:37:14.635519 b135a358-2af2-41f8-9c66-aa392ca21660 test1 Created branch 'test1'
2020-01-24 14:37:14.646972 5ebdb406-eee6-44b9-a2a0-005e4b5ef94f test1 Remove square in shapes
2020-01-24 14:37:14.697650 4e00034e-17d5-48ed-9078-d070a0d65d03 master Clone 'wc' in ag

Let us perform another rewriting as follows:

::

    pattern = NXGraph()
    pattern.add_nodes_from(["wc1"])

    rule = Rule.from_transform(pattern)
    rule.inject_add_node("new_node")
    rule.inject_add_edge("new_node", "wc1")

    _ = h.rewrite(
        "data",
        rule, {"wc1": "wc1"},
        message="Add a new node to 'data'")

Now we merge the branch `test1` in into `master`.

>>> h.merge_with("test1")
>>> h.print_history()
2020-01-24 14:37:14.627367 78f98e3c-2361-4d96-9737-31678d507ac6 master Initial commit
2020-01-24 14:37:14.635519 b135a358-2af2-41f8-9c66-aa392ca21660 test1 Created branch 'test1'
2020-01-24 14:37:14.646972 5ebdb406-eee6-44b9-a2a0-005e4b5ef94f test1 Remove square in shapes
2020-01-24 14:37:14.697650 4e00034e-17d5-48ed-9078-d070a0d65d03 master Clone 'wc' in ag
2020-01-24 14:37:14.728376 dc371f55-18fb-4797-ba75-8ff9217bfe65 master Add a new node to 'data' 
2020-01-24 14:37:14.751670 f2239fa2-2632-4650-8b53-78f03cf2d795 master Merged branch 'test1' into 'master'

Let us now rollback to the commit `clone_commit`.

>>> h.rollback(clone_commit)
Created the new head for 'test1'
Created the new head for 'master'

>>> h.print_history()
2020-01-24 14:37:14.627367 78f98e3c-2361-4d96-9737-31678d507ac6 master Initial commit
2020-01-24 14:37:14.635519 b135a358-2af2-41f8-9c66-aa392ca21660 test1 Created branch 'test1'
2020-01-24 14:37:14.646972 5ebdb406-eee6-44b9-a2a0-005e4b5ef94f test1 Remove square in shapes
2020-01-24 14:37:14.697650 4e00034e-17d5-48ed-9078-d070a0d65d03 master Clone 'wc' in ag
>>> print(h.branches())
['master', 'test1']

We can see that the revision history came back to the previous state (right after the clone commit), and we still have two branches `master` and `test1`.



See more
--------

Module reference: :ref:`audit`
