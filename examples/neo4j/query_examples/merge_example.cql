MATCH (a:node { id : 'a'}), (b:node { id : 'b'}) 
// use the APOC procedure 'apoc.refactor.mergeNodes' to merge nodes
CALL apoc.refactor.mergeNodes([a, b], {properties: 'combine'})
YIELD node as merged_node
// search for a node with the same id as the clone id
SET merged_node.id = 'a_b'
WITH merged_node
// find and merge multiple relations resulting from the node merge
OPTIONAL MATCH (merged_node)-[out_rel:edge]->(suc)
WITH collect({neighbor: suc, edge: out_rel}) as suc_maps, new_id, merged_node
OPTIONAL MATCH (pred)-[in_rel:edge]->(merged_node)
WHERE pred.id <> merged_node.id
WITH collect({neighbor: pred, edge: in_rel}) as pred_maps, suc_maps, new_id, merged_node
WITH apoc.map.groupByMulti(suc_maps, 'neighbor') as suc_maps, apoc.map.groupByMulti(pred_maps, 'neighbor') as pred_maps, new_id, merged_node
WITH REDUCE(edges=[],  k in filter(k in keys(suc_maps) WHERE length(suc_maps[k]) > 1 ) | 
	edges + [suc_maps[k]]) + 
	REDUCE(edges=[],  k in filter(k in keys(pred_maps) WHERE length(pred_maps[k]) > 1)| 
		edges + [pred_maps[k]]) as all_merge_edges, new_id, merged_node
UNWIND all_merge_edges as edge_list
	CALL apoc.refactor.mergeRelationships(
		REDUCE(rels=[], el in edge_list | rels + el['edge']),  {properties: 'combine'})
	YIELD rel
RETURN new_id