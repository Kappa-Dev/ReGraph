MATCH (a:node { id : 'a'}), (b:node { id : 'b'}) 

// accumulate all the attrs of the nodes to be merged
// here we collect properties of theses nodes into a list of pairs
// here dicts with keys 'key' and 'value'
WITH [] as new_props, b, a
WITH new_props + REDUCE(pairs = [], k in keys(a) | 
	pairs + REDUCE(inner_pairs = [], v in a[k] | 
		inner_pairs + {key: k, value: v})) as new_props, b, a
WITH new_props + REDUCE(pairs = [], k in keys(b) | 
	pairs + REDUCE(inner_pairs = [], v in b[k] | 
		inner_pairs + {key: k, value: v})) as new_props, b, a
WITH apoc.map.groupByMulti(new_props, 'key') as new_props, b, a
WITH apoc.map.fromValues(REDUCE(pairs=[], k in keys(new_props) | 
	pairs + [k, REDUCE(values=[], v in new_props[k] | 
		values + CASE WHEN v.value IN values THEN [] ELSE v.value END)])) as new_props, b, a
SET a = new_props
WITH a as merged_node, b
SET merged_node.id = 'a_b'
WITH b, merged_node

// accumulate all the attrs of the edges incident to the merged nodes
WITH [] as suc_maps, [] as pred_maps, [toString(id(b)), toString(id(merged_node))] as self_loops, b, merged_node

OPTIONAL MATCH (merged_node)-[out_rel:edge]->(suc)
WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, pred_maps, merged_node, b, self_loops

OPTIONAL MATCH (pred)-[in_rel:edge]->(merged_node)
WITH pred_maps + collect({id: id(pred), neighbor: pred, edge: in_rel}) as pred_maps, suc_maps, merged_node, b, self_loops

OPTIONAL MATCH (b)-[out_rel:edge]->(suc)
WITH suc_maps + collect({id: id(suc), neighbor: suc, edge: out_rel}) as suc_maps, pred_maps, merged_node, b, self_loops

OPTIONAL MATCH (pred)-[in_rel:edge]->(b)
WITH pred_maps + collect({id: id(pred), neighbor: pred, edge: in_rel}) as pred_maps, suc_maps, merged_node, b, self_loops

//
WITH apoc.map.groupByMulti(suc_maps, 'id') as suc_props, REDUCE(list=[], map in suc_maps | 
	list + map['neighbor']) as suc_nodes, apoc.map.groupByMulti(pred_maps, 'id') as pred_props, REDUCE(list=[], map in pred_maps | 
	list + map['neighbor']) as pred_nodes, merged_node, b, self_loops

//
WITH suc_nodes, pred_nodes, apoc.map.fromValues(REDUCE(edge_props=[], k in keys(suc_props) | 
	edge_props + [k, apoc.map.groupByMulti(REDUCE(props=[], el in suc_props[k] | 
		props + REDUCE(pairs=[], kk in keys(el['edge']) | 
			pairs + REDUCE(values=[], v in el['edge'][kk] | 
				values + {key: kk, value: v}))), 'key')])) as suc_props, 
	apoc.map.fromValues(REDUCE(edge_props=[], k in keys(pred_props) | 
	edge_props + [k, apoc.map.groupByMulti(REDUCE(props=[], el in pred_props[k] | 
		props + REDUCE(pairs=[], kk in keys(el['edge']) | 
			pairs + REDUCE(values=[], v in el['edge'][kk] | 
				 values + {key: kk, value: v}))), 'key')])) as pred_props,  
	REDUCE(edge_props=[], k IN filter(k IN keys(suc_props) WHERE k IN self_loops) |
		edge_props + suc_props[k]) + 
	REDUCE(edge_props=[], k IN filter(k IN keys(pred_props) WHERE k IN self_loops) |
		edge_props + pred_props[k]) as self_loop_props, merged_node, b, self_loops

WITH suc_nodes, suc_props, pred_nodes, pred_props, apoc.map.groupByMulti(REDUCE(pairs=[], el in self_loop_props |
	pairs + REDUCE(inner_pairs=[], k in keys(el['edge']) | 
		inner_pairs + REDUCE(values=[], v in el['edge'][k] |
			values + {key: k, value: v}))), 'key') as self_loop_props, merged_node, b, self_loops


FOREACH(suc IN filter(suc IN suc_nodes WHERE NOT id(suc) in self_loops) |
	MERGE (merged_node)-[new_rel:edge]->(suc)
	SET new_rel = apoc.map.fromValues(REDUCE(pairs=[], k in keys(suc_props[toString(id(suc))]) | 
		 pairs + [k, REDUCE(values=[], v in suc_props[toString(id(suc))][k] | 
			values + CASE WHEN v.value IN values THEN [] ELSE v.value END)])))


FOREACH(pred IN filter(pred IN pred_nodes WHERE NOT id(pred) in self_loops) |
	MERGE (pred)-[new_rel:edge]->(merged_node)
	SET new_rel = apoc.map.fromValues(REDUCE(pairs=[], k in keys(pred_props[toString(id(pred))]) | 
		 pairs + [k, REDUCE(values=[], v in pred_props[toString(id(pred))][k] | 
			values + CASE WHEN v.value IN values THEN [] ELSE v.value END)])))

// add self loop 
FOREACH(dummy in CASE WHEN length(self_loops) > 0 THEN [NULL] ELSE [] END |
	MERGE (merged_node)-[new_rel:edge]->(merged_node)
	SET new_rel = apoc.map.fromValues(REDUCE(pairs=[], k in keys(self_loop_props) |
		pairs + [k, REDUCE(values=[], v in self_loop_props[k] |
			values + CASE WHEN v.value IN values THEN [] ELSE v.value END)])))

DETACH DELETE (b)

RETURN merged_node
