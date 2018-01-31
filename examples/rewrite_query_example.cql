// ------------- Match an instance of a pattern
MATCH (x:node { id : 'e'}), (y:node { id : 'a1'}), (z:node { id : 'a_b'}), (a:node { id : 'c'}) , (x)-[x_y:edge]->(y), (y)-[y_z:edge]->(z), (z)-[z_z:edge]->(z), (z)-[z_a:edge]->(a) 
//-------------------------------------------------------

// -------------- Clone node 'y' as 'y1'
OPTIONAL MATCH (same_id_node:node) 
WHERE same_id_node.id = 'y1' 
FOREACH(
	new_count IN 
	CASE WHEN same_id_node IS NOT NULL 
	THEN [coalesce(same_id_node.count, 0) + 1] 
	ELSE [] END | 
		SET same_id_node.count=coalesce(same_id_node.count, 0) + 1 
) 
WITH same_id_node , a, x, y, z 
UNWIND 
CASE WHEN same_id_node IS NOT NULL 
THEN ['y1' + same_id_node.count] 
ELSE ['y1'] END 
AS y1_clone_id 
	CREATE (y1:node { id : y1_clone_id }) 
	WITH y, x, y1_clone_id, y1, a, z 
OPTIONAL MATCH (y)-[:edge]->(m:node), (o:node)-[:edge]->(y) 
WITH COLLECT(m) AS ms, COLLECT(o) AS os, y, x, y1_clone_id, y1, a, z 

FOREACH(o IN os | 
	FOREACH(p IN CASE WHEN NOT o.id IN [] THEN [o] ELSE [] END | 
		CREATE UNIQUE (p)-[:edge]->(y1) 
	)
) 
FOREACH(m IN ms | 
	FOREACH(p IN CASE WHEN NOT m.id IN [] THEN [m] ELSE [] END | 
		CREATE UNIQUE (y1)-[:edge]->(m) 
	)
) 
WITH y, x, y1_clone_id, y1, a, z  
//-------------------------------------------------

//------------- Clone node 'y' as 'y1'
OPTIONAL MATCH (same_id_node:node) 
WHERE same_id_node.id = 'y2' 
FOREACH(
	new_count IN 
	CASE WHEN same_id_node IS NOT NULL 
	THEN [coalesce(same_id_node.count, 0) + 1] 
	ELSE [] END | 
		SET same_id_node.count=coalesce(same_id_node.count, 0) + 1 
) 
WITH same_id_node , y, x, y1_clone_id, y1, a, z 
UNWIND 
CASE WHEN same_id_node IS NOT NULL 
THEN ['y2' + same_id_node.count] 
ELSE ['y2'] END 
AS y2_clone_id 
	CREATE (y2:node { id : y2_clone_id }) 
WITH y, y2, x, y1_clone_id, y1, a, y2_clone_id, z 

OPTIONAL MATCH (y)-[:edge]->(m:node), (o:node)-[:edge]->(y) 
WITH COLLECT(m) AS ms, COLLECT(o) AS os, y, y2, x, y1_clone_id, y1, a, y2_clone_id, z 
FOREACH(o IN os | 
	FOREACH(p IN CASE WHEN NOT o.id IN [] THEN [o] ELSE [] END | 
		CREATE UNIQUE (p)-[:edge]->(y2)
	)
)
FOREACH(m IN ms | 
	FOREACH(p IN CASE WHEN NOT m.id IN ['a_b'] THEN [m] ELSE [] END | 
		CREATE UNIQUE (y2)-[:edge]->(m) 
	)
)
WITH y, y2, x, y1_clone_id, y1, a, y2_clone_id, z 
// --------------------------------------------------------


// ----------------- Delete node 'x'
DETACH DELETE x
WITH y, y2, y1_clone_id, y1, a, y2_clone_id, z 
//-------------------------------------------------------

// ----------------- Merge nodes 'a' and 'y'
OPTIONAL MATCH (y)-[:edge]->(suc_y)
OPTIONAL MATCH (pred_y)-[:edge]->(y)
OPTIONAL MATCH (a)-[:edge]->(suc_a)
OPTIONAL MATCH (pred_a)-[:edge]->(a) 
WITH COLLECT(suc_y) as sucs_y, COLLECT(pred_y) as preds_y, COLLECT(suc_a) as sucs_a, COLLECT(pred_a) as preds_a, y, y2, y1_clone_id, y1, a, y2_clone_id, z 

OPTIONAL MATCH (same_id_node:node)
WHERE same_id_node.id = 'a1_c'
FOREACH(
	new_count IN
	CASE WHEN same_id_node IS NOT NULL 
	THEN [coalesce(same_id_node.count, 0) + 1] 
	ELSE [] END | 
		SET same_id_node.count=coalesce(same_id_node.count, 0) + 1
) 
WITH same_id_node , sucs_a, preds_a, y, y2, preds_y, y1_clone_id, y1, a, sucs_y, y2_clone_id, z 
UNWIND 
CASE WHEN same_id_node IS NOT NULL
THEN ['a1_c' + same_id_node.count] 
ELSE ['a1_c'] END AS y_a_id 
	CREATE (y_a:node { id : y_a_id }) 

FOREACH(s IN sucs_y | 
	CREATE UNIQUE (y_a)-[:edge]->(s)
) 
FOREACH(s IN sucs_a | 
	CREATE UNIQUE (y_a)-[:edge]->(s)
) 
FOREACH(p IN preds_y | 
	CREATE UNIQUE (p)-[:edge]->(y_a)
)  
FOREACH(p IN preds_a | 
	CREATE UNIQUE (p)-[:edge]->(y_a)
) 
FOREACH(n IN sucs_y + preds_y + sucs_a + preds_a | 
	FOREACH(dummy_var IN CASE WHEN n IN [y, a]	
			THEN ['dummy'] ELSE [] END | 
				CREATE UNIQUE (y_a)-[:edge]->(y_a)
	) 
)
DETACH DELETE y, a 
WITH sucs_a, preds_a, y2, preds_y, y_a_id, y1_clone_id, y_a, y1, sucs_y, y2_clone_id, z  
// --------------------------------------------------------

// --------------- Add node 'new_node'
OPTIONAL MATCH (same_id_node:node) 
WHERE same_id_node.id = 'new_node' 
FOREACH(
	new_count IN 
	CASE WHEN same_id_node IS NOT NULL 
	THEN [coalesce(same_id_node.count, 0) + 1] 
	ELSE [] END | 
		SET same_id_node.count=coalesce(same_id_node.count, 0) + 1
) 
WITH same_id_node , sucs_a, preds_a, y2, preds_y, y_a_id, y1_clone_id, y_a, y1, sucs_y, y2_clone_id, z 
UNWIND
CASE WHEN same_id_node IS NOT NULL
THEN ['new_node' + same_id_node.count] 
ELSE ['new_node'] END 
AS new_node_id 
	CREATE (new_node:node { id : new_node_id }) 
// -----------------------------------------------------------------


// --------------- Add edge 'new_node' -> 'z'
CREATE UNIQUE (new_node)-[:edge]->(z) 
//-------------------------------------------------------------

// ------------------ Return everything
RETURN sucs_a, preds_a, new_node_id, y2, preds_y, new_node, y_a_id, y1_clone_id, y_a, y1, sucs_y, y2_clone_id, z 