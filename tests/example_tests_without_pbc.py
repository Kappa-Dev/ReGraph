import networkx as nx

from regraph.library.data_structures import (TypedDiGraph,
                                             Homomorphism,
                                             TypedHomomorphism)
from regraph.library.category_op import pullback_complement
from regraph.library.rewriters import Transformer, Rewriter
from regraph.library.graph_modeler import GraphModeler

MMM = nx.DiGraph()

MMM.add_node('circle')
MMM.add_node('square')

MMM.add_edge('circle', 'circle', {'state' : 'p'})
MMM.add_edge('circle', 'square')

Model = nx.DiGraph()

Model.add_node('agent')
Model.add_node('site')
Model.add_node('action')

Model.add_edge('site', 'action')

hom_Model_MMM = {
    'agent' : 'circle',
    'site' : 'circle',
    'action' : 'square',
}

Rule = nx.DiGraph()

Rule.add_node('protein1')
Rule.add_node('site1_1')
Rule.add_node('site1_2')
Rule.add_node('protein2')
Rule.add_node('site2_1')
Rule.add_node('site2_2')
Rule.add_node('BND')
Rule.add_node('BND1')

Rule.add_edge('site1_1', 'BND')
Rule.add_edge('site2_2', 'BND')

hom_Rule_Model = {
    'protein1' : 'agent',
    'site1_1' : 'site',
    'site1_2' : 'site',
    'protein2' : 'agent',
    'site2_1' : 'site',
    'site2_2' : 'site',
    'BND' : 'action',
    'BND1' : 'action'
}

modeler = GraphModeler([MMM, Model, Rule],
                       [hom_Model_MMM, hom_Rule_Model],
                       ['MMM', 'Model', 'Rule'])


# -----------------------------------------

trans = modeler.init_rewriting('MMM')

trans.add_node('dark_square', None)
trans.add_edge('square', 'dark_square')

modeler.rewrite('MMM', trans.identity(), trans)

print("---------------------- Propagation\n")
modeler.propagate_all()

print(modeler)

# -----------------------------------------

trans = modeler.init_rewriting("Model")

trans.add_node('dark_action', 'dark_square')

modeler.rewrite('Model', trans.identity(), trans)

print("---------------------- Propagation\n")
modeler.propagate_all()

print(modeler)

# -----------------------------------------

trans = modeler.init_rewriting("Rule")

trans.clone_node('protein1', 'protein3')

modeler.rewrite('Rule', trans.identity(), trans)

print("---------------------- Propagation\n")
modeler.propagate_all()

print(modeler)

# -----------------------------------------
