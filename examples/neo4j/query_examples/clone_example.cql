MATCH (a:node { id : 'a' })
// create a node corresponding to the clone
CREATE (a1:node) 
WITH a1, toString(id(a1)) as uid, a.id as original_old, a 
// set the id property of the original node to NULL
SET a.id = NULL
// copy all the properties of the original node to the clone
SET a1 = a
// set id property of the clone to neo4j-generated id
SET a1.id = toString(id(a1)), a1.count = NULL
// set back the id property of the original node
SET a.id = original_old
WITH a1, toString(id(a1)) as uid, a 
WITH [] as sucIgnore, [] as predIgnore, uid, a1, a 
// match successors and out-edges of a node to be cloned
OPTIONAL MATCH (a)-[out_edge:edge]->(suc) 
WHERE NOT suc.id IS NULL AND NOT suc.id IN sucIgnore
WITH collect({neighbor: suc, edge: out_edge}) as suc_maps, a1, uid, sucIgnore, a, predIgnore 
// match predecessors and in-edges of a node to be cloned
OPTIONAL MATCH (pred)-[in_edge:edge]->(a) 
WHERE NOT pred.id IS NULL AND NOT pred.id IN predIgnore
WITH collect({neighbor: pred, edge: in_edge}) as pred_maps, a1, uid, sucIgnore, suc_maps, a, predIgnore 
// copy all incident edges of the original node to the clone
FOREACH (suc_map IN suc_maps | 
	FOREACH (suc IN CASE WHEN suc_map.neighbor IS NOT NULL THEN [suc_map.neighbor] ELSE [] END |
		CREATE (a1)-[new_edge:edge]->(suc) 
		SET new_edge = suc_map.edge))
FOREACH (pred_map IN pred_maps | 
	FOREACH (pred IN CASE WHEN pred_map.neighbor IS NOT NULL THEN [pred_map.neighbor] ELSE [] END |
		CREATE (pred)-[new_edge:edge]->(a1) 
		SET new_edge = pred_map.edge))
// copy self loop
FOREACH (suc_map IN suc_maps | 
	FOREACH (self_loop IN CASE WHEN suc_map.neighbor = a THEN [suc_map.edge] ELSE [] END |
		CREATE (a1)-[new_edge:edge]->(a1) 
		SET new_edge = self_loop))
WITH a1, uid, sucIgnore, a, predIgnore
RETURN uid