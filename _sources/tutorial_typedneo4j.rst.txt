.. _tutorial_typedneo4j:

==================================================
Rewriting schema-aware PGs through TypedNeo4jGraph
==================================================

Let us start by importing the necessary data structures and functions:

::

    from regraph import NXGraph, TypedNeo4jGraph, Rule
    from regraph.attribute_sets import IntegerSet, RegexSet
    from regraph import plot_rule


.. _create_tn4:

--------------------------------------------------
Creating and modifying a schema-aware graph object
--------------------------------------------------

Let us start by defining elements for the data and the schema graph:

::

    # Define schema graph elements
    schema_nodes = [
        ("Person", {"age": IntegerSet.universal()}),
        ("Organization", {"location": RegexSet.universal()})]
    schema_edges = [
        ("Person", "Person", {"type": {"friend", "parent", "colleague"}}),
        ("Organization", "Organization"),
        ("Person", "Organization", {"type": {"works_in", "studies_in"}})
    ]

    # Define data graph elements
    data_nodes = [
        ("Alice", {"age": 15}),
        ("Bob"),
        ("Eric", {"age": 45}),
        ("Sandra", {"age": 47}),
        ("ENS Lyon", {"location": "Lyon"}),
        ("UN", {"location": "Geneva"}),
        ("INTERPOL", {"location": "Lyon"})
    ]
    data_edges = [
        ("Alice", "Bob", {"type": "friend"}),
        ("Bob", "Alice", {"type": "friend"}),
        ("Sandra", "Eric", {"type": "friend"}),
        ("Sandra", "Bob", {"type": "parent"}),
        ("Eric", "Alice", {"type": "parent"}),
        ("Eric", "UN"),
        ("Eric", "Sandra", {"type": "colleague"})
    ]

    # Provide typing of the data by the schema
    data_typing = {
        "Alice": "Person",
        "Bob": "Person",
        "Eric": "Person",
        "Sandra": "Person",
        "ENS Lyon": "Organization",
        "UN": "Organization",
        "INTERPOL": "Organization"
    }

Now, let us create a schema-aware PG:

::
 
    graph = TypedNeo4jGraph(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="admin",
        data_graph={"nodes": data_nodes, "edges": data_edges},
        schema_graph={"nodes": schema_nodes, "edges": schema_edges},
        typing=data_typing)

The following snippet illustrates how different graph objects can be accessed:

>>> print("Schema object: ", type(graph.get_schema()))
Schema object:  <class 'regraph.backends.neo4j.graphs.Neo4jGraph'>
>>> print("Schema nodes: ", graph.get_schema_nodes())
Schema nodes:  ['Person', 'Organization']
>>> print("Schema edges: ", graph.get_schema_edges())
Schema edges:  [('Person', 'Organization'), ('Person', 'Person'), ('Organization', 'Organization')]
>>> print("Data object: ", type(graph.get_data()))
Data object:  <class 'regraph.backends.neo4j.graphs.Neo4jGraph'>
>>> print("Data nodes: ", graph.get_data_nodes())
Data nodes:  ['Alice', 'Bob', 'Eric', 'Sandra', 'ENS Lyon', 'UN', 'INTERPOL']
>>> print("Data edges: ", graph.get_data_edges())
Data edges:  [('Alice', 'Bob'), ('Bob', 'Alice'), ('Eric', 'Sandra'), ('Eric', 'UN'), ('Eric', 'Alice'), ('Sandra', 'Bob'), ('Sandra', 'Eric')]
>>> print("Data typing:", graph.get_data_typing())
Data typing: {
   "Sandra": "Person",
   "Eric": "Person",
   "Alice": "Person",
   "Bob": "Person",
   "UN": "Organization",
   "ENS Lyon": "Organization",
   "INTERPOL": "Organization"
}

.. _rewrite_tn4:

-----------------------------
Rewriting schema-aware graphs
-----------------------------

ReGraph implements the rewriting technique called `sesqui-pushout rewriting` that allows to transform graphs by applying rules through their instances (matchings). Rewriting of the data or the schema may require an update to the other graph, such updates are called *propagation* and are distinguished into two types: *backward* and *forward* propagation.

*Backward propagation briefly*: 
- If some graph elements (nodes/edges or attributes) are removed from the schema, then all the respective elements that are typed by them in the data **should** be removed.
- If a graph node is cloned in the schema, then for every instance of this node in the data we either: (a) specify to which clone it corresponds or (b) clone it.

*Forward propagation briefly*: 
- If some data nodes are merged and these nodes are typed by different nodes in the schema, the corresponding schema nodes **should** be merged.
- If a new graph element (node/edge or attribute) is added to the data, then we either (a) select an existing element to type the added element by the schema or (b) add a new element to the schema to type the added element.

ReGraph allows to rewrite schema-aware PGs and their schemas using the methods `rewrite_data` and `rewrite_schema` of `TypedNeo4jGraph`. The rewriting can be done in two modes:

1. *Strict rewriting* rewriting that does not allow propagation.

2. *Not strict rewriting* that allows propagation.


^^^^^^^^^^^^^^^^
Strict rewriting
^^^^^^^^^^^^^^^^

`TypedNeo4jGraph` implements a set of methods that perform transformations of both data and schema that do not require propagation. Conider the following examples.

>>> graph.add_schema_node("Country", {"location": RegexSet.universal()})
>>> graph.add_schema_edge("Organization", "Country", {"type": {"located_in"}})
>>> print("Schema nodes: ", graph.get_schema_nodes())
Schema nodes:  ['Person', 'Organization', 'Country']
>>> print("Schema edges: ", graph.get_schema_edges())
Schema edges:  [('Person', 'Organization'), ('Person', 'Person'), ('Organization', 'Country'), ('Organization', 'Organization')]

>>> graph.add_data_node("France", typing="Country", attrs={"location": "Europe"})
>>> graph.add_data_edge("INTERPOL", "France", {"type": "located_in"})
>>> print("Data nodes: ", graph.get_data_nodes())
Data nodes:  ['Alice', 'Bob', 'Eric', 'Sandra', 'ENS Lyon', 'UN', 'INTERPOL', 'France']
>>> print("Data edges: ", graph.get_data_edges())
Data edges:  [('Alice', 'Bob'), ('Bob', 'Alice'), ('Eric', 'Sandra'), ('Eric', 'UN'), ('Eric', 'Alice'), ('Sandra', 'Bob'), ('Sandra', 'Eric'), ('INTERPOL', 'France')]

We will now create a rule that applied to the schema and that clones the node `Organization` into two nodes.

::

    lhs = NXGraph()
    lhs.add_nodes_from(["Organization"])

    rule = Rule.from_transform(lhs)
    _, rhs_clone = rule.inject_clone_node("Organization")

    instance = {
        "Organization": "Organization"
    }

    plot_rule(rule)


..image:: _static/typedn4/r1.png

We try to apply the created rule to the graph `T` in the strict mode. The following snippet:

::

    try:
        rhs_instance = graph.rewrite_schema(rule, strict=True)
    except Exception as e:
        print("Error message: ", e)
        print("Type: ", type(e))


outputs

::

    Error message:  Rewriting is strict (no propagation of clones is allowed), the cloned node 'Organization' in 'type' has instances '['UN', 'ENS Lyon', 'INTERPOL']' in 'node' and their typing by P is not specified
    Type:  <class 'regraph.exceptions.RewritingError'>


We have failed to rewrite the schema, because we have not specified typing for instances of `Organization` in the rule's interface. Let us try again, but this time we will prove such typing.

::

    data_typing = {
        'ENS Lyon': rhs_clone,
        'UN': "Organization",
        'INTERPOL': 'Organization'
    }
    rhs_instance = graph.rewrite_schema(
        rule, data_typing=data_typing, strict=True)


>>> print("Instance of the RHS in G", rhs_instance)
Instance of the RHS in G {'Organization': 'Organization', 'Organization1': 'Organization1'}

Let us relabel nodes in `T`.

>>> graph.relabel_schema_node(rhs_instance[rhs_clone], 'University')
>>> graph.relabel_schema_node(rhs_instance["Organization"], "International_Organization")
>>> print(json.dumps(graph.get_data_typing(), indent="   "))
{
   "Sandra": "Person",
   "Eric": "Person",
   "Alice": "Person",
   "Bob": "Person",
   "UN": "International_Organization",
   "INTERPOL": "International_Organization",
   "France": "Country",
   "ENS Lyon": "University"
}



^^^^^^^^^^^^^^^^^^^
Rewriting and propagation
^^^^^^^^^^^^^^^^^^^^^^^^^

We now show how graph rewriting that requires propagation can be performed in such schema-aware PG. Let us first consider a small example of *forward propagation*. We will create a rule that performs some additions of new nodes not typed  by schema.

::

    pattern = NXGraph()
    pattern.add_nodes_from(["a", "b", "c"])
    pattern.add_edges_from([
            ("a", "b", {"type": "colleague"}),
            ("a", "c")
        ])

    rule = Rule.from_transform(pattern)
    rule.inject_remove_edge("a", "c")
    rule.inject_add_node("Crime_Division")
    rule.inject_add_edge("Crime_Division", "c", {"type": "part_of"})
    rule.inject_add_edge("a", "Crime_Division")
    rule.inject_add_edge("b", "Crime_Division")

    plot_rule(rule)

..image:: _static/typedn4/r2.png

We have created a rule that clones the node `a` and reconnects the edges between `a` and `b`. 

::

    pattern_typing = {
        "a": "Person",
        "b":  "Person",
        "c": "International_Organization"
    }
    instances = graph.find_data_matching(pattern, pattern_typing=pattern_typing)

We obtain the following instances:

>>> print(instances)
{'a': 'Eric', 'b': 'Sandra', 'c': 'UN'}

We rewrite the graph `shapes` with the fixed instances (so, the node `circle` is cloned).

>>> rhs_instance = graph.rewrite_data(rule, instance=instances[0])
>>> print(rhs_instance)
{'a': 'Eric', 'b': 'Sandra', 'c': 'UN', 'Crime_Division': 'Crime_Division'}


To type the new node 'Crime_Division', we have created a new node in the schema.

>>> schema_node = graph.get_node_type(rhs_instance["Crime_Division"])
>>> graph.relabel_schema_node(schema_node, "Division")
>>> print("Schema nodes: ", graph.get_schema_nodes())
Schema nodes:  ['Division', 'Person', 'International_Organization', 'Country', 'University']
>>> print("Schema edges: ", graph.get_schema_edges())
Schema edges:  [('Division', 'International_Organization'), ('Person', 'Division'), ('Person', 'University'), ('Person', 'International_Organization'), ('Person', 'Person'), ('International_Organization', 'University'), ('International_Organization', 'Country'), ('International_Organization', 'International_Organization'), ('University', 'University'), ('University', 'International_Organization'), ('University', 'Country')]

Now, let us consider an example of *backward propagation*. We will clone the node `Person` in the schema into a `Child` and `Adult`. We will determine which instances of `Person` are typed by `Child` or `Adult` by looking a the age attribute.


::

    pattern = NXGraph()
    pattern.add_nodes_from(["Person"])
    pattern.add_edges_from([("Person", "Person", {"type": {"friend", "parent", "colleague"}})])

    interface =  NXGraph()
    interface.add_nodes_from(["Adult", "Child"])
    interface.add_edges_from([
        ("Adult", "Adult", {"type": {"friend", "parent", "colleague"}}),
        ("Child", "Child", {"type": {"friend"}}),
        ("Adult", "Child", {"type": {"friend", "parent"}}),
        ("Child", "Adult", {"type": {"friend"}}),
    ])

    rule = Rule(p=interface, lhs=pattern, p_lhs={"Adult": "Person", "Child": "Person"})

Let us determine which instances of `Person` are typed by `Child` or `Adult` as follows.

::

    data_typing = {}

    persons = graph.get_instances("Person")
    for p in persons:
        p_attrs = graph.get_data_node(p)
        if "age" in p_attrs:
            age = list(p_attrs["age"])[0]
            if age > 18:
                data_typing[p] = "Adult"
            else:
                data_typing[p] = "Child"

>>> print("Data typing: ", data_typing)
Data typing:  {'Sandra': 'Adult', 'Eric': 'Adult', 'Alice': 'Child'}
>>> rhs_instance = graph.rewrite_schema(rule, data_typing=data_typing)
>>> print(rhs_instance)
{'Adult': 'Person1', 'Child': 'Person'}

Let us relabel nodes appropriately:

::

    graph.relabel_schema_node(rhs_instance["Adult"], "Adult")
    graph.relabel_schema_node(rhs_instance["Child"], "Child")
    print("Schema nodes: ", graph.get_schema_nodes())
    print("Schema edges: ")
    for s, t in graph.get_schema_edges():
        print("\t", s, "->", t)

    print("Data nodes: ", graph.get_data_nodes())
    print("Data edges: ")
    for s, t, attrs in graph.get_data_edges(data=True):
        print("\t", s, "->", t, attrs)

We obtain the following output:

::

    Schema nodes:  ['Child', 'University', 'Country', 'International_Organization', 'Division',  'Adult']
    Schema edges: 
         Child -> Adult
         Child -> Division
         Child -> International_Organization
         Child -> University
         Child -> Child
         University -> International_Organization
         University -> Country
         University -> University
         International_Organization -> University
         International_Organization -> International_Organization
         International_Organization -> Country
         Division -> International_Organization
         Adult -> Child
         Adult -> Division
         Adult -> Adult
         Adult -> University
         Adult -> International_Organization

    Data nodes:  ['Alice', 'Bob', 'Eric', 'Sandra', 'ENS Lyon', 'UN', 'INTERPOL', 'France', 'Crime_Division', 'Bob1']
    Data edges: 
         Alice -> Bob1 {'type': {'friend'}}
         Alice -> Bob {'type': {'friend'}}
         Bob -> Alice {'type': {'friend'}}
         Eric -> Crime_Division {}
         Eric -> Sandra {'type': {'colleague'}}
         Eric -> Alice {'type': {'parent'}}
         Sandra -> Bob1 {'type': {'parent'}}
         Sandra -> Crime_Division {}
         Sandra -> Bob {'type': {'parent'}}
         Sandra -> Eric {'type': {'friend'}}
         INTERPOL -> France {'type': {'located_in'}}
         Crime_Division -> UN {'type': {'part_of'}}
         Bob1 -> Alice {'type': {'friend'}}

Observe that we have cloned the node `Bob` into two nodes `Bob` and `Bob1`, one being an instance of `Adult` and another of `Child`.

>>> print(json.dumps(graph.get_data_typing(), indent="  "))
{
  "Alice": "Child",
  "Bob1": "Child",
  "ENS Lyon": "University",
  "France": "Country",
  "UN": "International_Organization",
  "INTERPOL": "International_Organization",
  "Crime_Division": "Division",
  "Eric": "Adult",
  "Bob": "Adult",
  "Sandra": "Adult"
}