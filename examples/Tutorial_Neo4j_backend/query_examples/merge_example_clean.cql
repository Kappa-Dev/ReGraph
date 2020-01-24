// I. Pick a node
//  (1) merge node attrs
//  (2) add edges
//  (3) merge edge attrs
//  (4) delete node


// Add to the set of nodes, add to the set of  edges
// Merge two dicts
// dict diff
// (merge in two ways:
//  (1) new node and remove all,
//	(2) choose a node and fuse all the rest into it)

// We are not allowed to do:
// neither `MERGE (a1)-[new_edge:edge]->(suc_map.neighbor)`
// nor     `MERGE (a1)-[new_edge:edge]->(suc_map["neighbor"])`
// so I use the following hack of the following form:
// ```
// FOREACH (suc in [suc_map.neighbor] |
//    MERGE (a1)-[new_edge:edge]->(suc)     
// )
// ```
// and moreover we are not allowed to do:
// `SET a[key] = b[key]`
// so to do this I use APOC
// `SET a = apoc.map.setKey(a, key, b[key])`
// APOC docs:
// "`apoc.map.setKey` returns the map with the value for this key added or replaced"
MATCH (a { id : 'a'}), (b { id : 'b'}) 

// Add properties of 'b' to 'a' (preserving their uniqueness)
FOREACH(key in keys(b) |
	// for all properties that are not in 'a' assign their value as
	// the value of b
	// if key not in a.keys():
	FOREACH(dummy IN CASE WHEN key IN keys(a) THEN [] ELSE [NULL] END |
		// SET a[key] = b[key]
		SET a = apoc.map.setKey(a, key, b[key])
	)
	// else:
	// for all properties that are already in 'a' add the elements that
	// are not in thier value of a
	FOREACH(dummy IN CASE WHEN key IN keys(a) THEN [NULL] ELSE [] END |
		//SET a[key] = a[key] + filter(el IN b[key] WHERE NOT el in a[key]) 
		SET a = apoc.map.setKey(a, key, a[key] + filter(
			el IN b[key] WHERE NOT el in a[key]))
	)
)
// we create a list with ids of nodes that are merged to track self loops
WITH a as merged_node, b, [id(a), id(b)] as merged_nodes

// match successors of 'b'
OPTIONAL MATCH (b)-[out_edge:edge]->(suc)
WITH merged_node, b, merged_nodes, filter(
	el IN collect(
		{neighbor: suc, edge: out_edge}) WHERE NOT el.neighbor IS NULL) as all_suc_maps
WITH merged_node, b, merged_nodes, filter(
	el in all_suc_maps WHERE NOT id(el.neighbor) IN merged_nodes) as new_suc_maps,
filter(el in all_suc_maps WHERE id(el.neighbor) IN merged_nodes) as loop_suc_maps

//  match predecessors of 'b' 
OPTIONAL MATCH (pred)-[in_edge:edge]->(b)
WITH merged_node, b, merged_nodes, new_suc_maps, loop_suc_maps, filter(
	el IN collect(
		{neighbor: pred, edge: in_edge}) WHERE NOT el.neighbor IS NULL) as all_pred_maps
WITH merged_node, b, merged_nodes, new_suc_maps, loop_suc_maps, filter(
	el IN all_pred_maps WHERE NOT id(el.neighbor) IN merged_nodes) as new_pred_maps,
filter(el IN all_pred_maps WHERE id(el.neighbor) IN merged_nodes) as loop_pred_maps

// create edges for sucs/preds that didn't exist before and/or merge their attributes into existing edges
FOREACH (suc_map IN new_suc_maps |
	// MERGE (merged_node)-[edge:edge]->(suc_map.neighbor)
	FOREACH(suc IN [suc_map.neighbor] | // start of syntactic weirdness
		MERGE (merged_node)-[edge:edge]->(suc)
		// Merge dicts
		FOREACH(key in keys(suc_map.edge) |
			FOREACH(dummy IN CASE WHEN key IN keys(edge) THEN [] ELSE [NULL] END |
				// SET edge[key] = suc_map.edge[key]
				SET edge = apoc.map.setKey(edge, key, suc_map.edge[key])
			)
			FOREACH(dummy IN CASE WHEN key IN keys(edge) THEN [NULL] ELSE [] END |
				// SET edge[key] = edge[key] + filter(
				//		el IN suc_map.edge[key] WHERE NOT el in edge[key])
				SET edge = apoc.map.setKey(edge, key, edge[key] + filter(
								el IN suc_map.edge[key] WHERE NOT el in edge[key]))
			)
		)
	) // end
)
FOREACH (pred_map IN new_pred_maps | 
	// MERGE (pred_map.neighbor)-[edge:edge]->(merged_node)
	FOREACH(pred in [pred_map.neighbor] | // start of syntactic weirdness 
		MERGE (pred)-[edge:edge]->(merged_node)
		FOREACH(key in keys(pred_map.edge) |
			FOREACH(dummy IN CASE WHEN key IN keys(edge) THEN [] ELSE [NULL] END |
				// SET edge[key] = pred_map.edge[key]
				SET edge = apoc.map.setKey(edge, key, pred_map.edge[key])
			)
			FOREACH(dummy IN CASE WHEN key IN keys(edge) THEN [NULL] ELSE [] END |
				// SET edge[key] = edge[key] + filter(
				// 	el IN pred_map.edge[key] WHERE NOT el in edge[key]) 
				SET edge = apoc.map.setKey(edge, key, edge[key] + filter(
								el IN pred_map.edge[key] WHERE NOT el in edge[key]))
			)
		)
	) // end
)


// handle self loops: the outer-most foreach is to simulate the following if:
// the loop to the merged node is created either if the original node 'a' already
// had a self loop, or 'b' had a self loop, or 'b' had an in/out edge from/to 'a'
WITH merged_node, b, loop_suc_maps, loop_pred_maps
OPTIONAL MATCH (merged_node)-[old_loop:edge]->(merged_node)
// If we need to create a loop
FOREACH(dummy IN 
	CASE WHEN NOT old_loop IS NULL OR length(loop_suc_maps) > 0 OR length(loop_pred_maps) > 0
	THEN [NULL] ELSE [] END |
	MERGE (merged_node)-[old_loop:edge]->(merged_node)
	FOREACH (map IN loop_suc_maps + loop_pred_maps |
		FOREACH(key in keys(map.edge) |
			FOREACH(dummy IN CASE WHEN key IN keys(old_loop) THEN [] ELSE [NULL] END |
				// SET old_loop[key] = map.edge[key]
				SET old_loop = apoc.map.setKey(old_loop, key, map.edge[key])
			)
			FOREACH(dummy IN CASE WHEN key IN keys(old_loop) THEN [NULL] ELSE [] END |
				// SET old_loop[key] = old_loop[key] + filter(
				//	el IN map.edge[key] WHERE NOT el in old_loop[key])
				SET old_loop = apoc.map.setKey(old_loop, key, old_loop[key] + filter(
						el IN map.edge[key] WHERE NOT el in old_loop[key]))
			)
		)
	)
)

DETACH DELETE b

RETURN merged_node