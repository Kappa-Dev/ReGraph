// (1) Add node $V := V \cup \{a_1\}$
// (2) Add attrs to it 
// (3) Add edge (for all sucs/preds)
// (4) Add attrs to them

// We are not allowed to do
// neither `CREATE (a1)-[new_edge:edge]->(suc_map.neighbor)`
// nor     `CREATE (a1)-[new_edge:edge]->(suc_map["neighbor"])`
// so I made up some hack of the following form:
// ```
// FOREACH (suc in [suc_map.neighbor] |
//    CREATE (a1)-[new_edge:edge]->(suc)     
// )
// ```
MATCH (a { id : 'a' })
// create a node corresponding to the clone
CREATE (a1) 
WITH a, a1
// copy all the properties of the original node to the clone
SET a1 = a
WITH a, a1

// match successors and out-edges of a node to be cloned
OPTIONAL MATCH (a)-[out_edge:edge]->(suc)
WITH a, a1, filter(
	el IN collect({neighbor: suc, edge: out_edge}) WHERE NOT el.neighbor IS NULL) as suc_maps
// match predecessors and in-edges of a node to be cloned
OPTIONAL MATCH (pred)-[in_edge:edge]->(a) 
WITH a, a1, suc_maps, filter(
	el IN collect({neighbor: pred, edge: in_edge}) WHERE NOT el.neighbor IS NULL) as pred_maps

// copy all incident edges of the original node to the clone
FOREACH (suc_map IN suc_maps |
	FOREACH(suc IN [suc_map.neighbor] |
		CREATE (a1)-[new_edge:edge]->(suc) 
		SET new_edge = suc_map.edge)
	)
FOREACH (pred_map IN pred_maps |
	FOREACH(pred in [pred_map.neighbor] |
		CREATE (pred)-[new_edge:edge]->(a1) 
		SET new_edge = pred_map.edge
	)
)

// copy self loop
FOREACH (suc_map IN suc_maps | 
	FOREACH (self_loop IN CASE WHEN suc_map.neighbor=a THEN [suc_map.edge] ELSE [] END |
		CREATE (a1)-[new_edge:edge]->(a1) 
		SET new_edge = self_loop
	)
)

WITH a, a1
RETURN a1