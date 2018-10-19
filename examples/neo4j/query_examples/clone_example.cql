MATCH (x:node { id : 'a' })
WITH [] as sucIgnore, [] as predIgnore, x 
// match successors and out-edges of a node to be cloned
OPTIONAL MATCH (x)-[out_edge:edge]->(suc) 
WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore
WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, predIgnore, x 
// match predecessors and in-edges of a node to be cloned
OPTIONAL MATCH (pred)-[in_edge:edge]->(x) 
WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore
WITH collect({neighbor: pred, edge: in_edge}) as pred_maps, suc_maps, x 
// search for a node with the same id as the clone id
CREATE (clone:node) 
WITH x, x.id as original_id, suc_maps, pred_maps, clone
// set the id property of the original node to NULL
SET x.id = NULL
// copy all the properties of the original node to the clone
SET clone = x
// set id property of the clone to the generated id
SET clone.id = 'a_clone'
// set back the id property of the original node
SET x.id = original_id
// copy all incident edges of the original node to the clone
FOREACH (suc_map IN suc_maps | 
	FOREACH (suc IN CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |
		MERGE (clone)-[new_edge:edge]->(suc) 
		SET new_edge = suc_map.edge))
FOREACH (pred_map IN pred_maps | 
	FOREACH (pred IN CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |
		MERGE (pred)-[new_edge:edge]->(clone) 
		SET new_edge = pred_map.edge))
RETURN uid