MATCH (x:node { id : 'a' })
WITH [] as sucIgnore, [] as predIgnore, x 
// match successors and out-edges of a node to be cloned
OPTIONAL MATCH (x)-[out_edge:edge]->(suc) 
WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore
WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, predIgnore, x 
// match predecessors and in-edges of a node to be cloned
OPTIONAL MATCH (pred)-[in_edge:edge]->(x) 
WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore
WITH collect({neighbor: pred, edge: in_edge}) as pred_maps, x, suc_maps 
// search for a node with the same id as the clone id
OPTIONAL MATCH (same_id_node:node { id : 'a'}) 
WITH same_id_node,  CASE WHEN same_id_node IS NOT NULL THEN (coalesce(same_id_node.count, 0) + 1) ELSE 0 END AS same_id_node_new_count, x, suc_maps, pred_maps
// generate new id if the same id node was found
// and filter edges which will be removed 
WITH same_id_node, same_id_node_new_count, 'a' + CASE WHEN same_id_node_new_count <> 0 THEN toString(same_id_node_new_count) ELSE '' END as uid, x, suc_maps, pred_maps
// create a node corresponding to the clone
CREATE (new_node:node) 
WITH same_id_node, same_id_node_new_count, new_node, uid, x.id as original_old, x, suc_maps, pred_maps
// set the id property of the original node to NULL
SET x.id = NULL
// copy all the properties of the original node to the clone
SET new_node = x
// set id property of the clone to the generated id
SET new_node.id = uid, new_node.count = NULL, same_id_node.count = same_id_node_new_count + 1
// set back the id property of the original node
SET x.id = original_old
// copy all incident edges of the original node to the clone
FOREACH (suc_map IN suc_maps | 
	FOREACH (suc IN CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |
		MERGE (new_node)-[new_edge:edge]->(suc) 
		SET new_edge = suc_map.edge))
FOREACH (pred_map IN pred_maps | 
	FOREACH (pred IN CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |
		MERGE (pred)-[new_edge:edge]->(new_node) 
		SET new_edge = pred_map.edge))
RETURN uid