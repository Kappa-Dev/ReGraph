
var IRegraphHttpApi = require('i_regraph_http_api');

var api = new IRegraphHttpApi.DefaultApi()

var callback = function(error, data, response) {
  if (error) {
    console.error(error.response.error.status + " : " + error.response.error.text);
  } else {
    console.log(response.status+" : data = "+JSON.stringify(data));
  }
};

var opts = { 
  'force': true, // Boolean | with rm_node, merge_nodes, rm_edge; force operation and modify children graphs
  'nodeId': "nodeId_example", // String | with add_node, remove_node and clone_node; id of node to manipulate
  'nodeType': "nodeType_example", // String | with add_node; type of node to create
  'sourceNode': "sourceNode_example", // String | with add_edge and rm_edge; id of source node
  'targetNode': "targetNode_example", // String | with add_edge and rm_edge; id of target node
  'node1': "node1_example", // String | with merge_node; id of first node to merge
  'node2': "node2_example", // String | with merge_node; id of second node to merge
  'newNodeId': "newNodeId_example" // String | with merge_nodes and clone_node; new name for the node resulting of the merge
};

var opts_post = { 
  'patternName': "",
  'targetGraph': "",
  'ruleName': "",
  'matching': "",
};
//var opts1 = Object.assign({}, opts);
opts.nodeId='a'
api.graphIdPut(" ", "add_node", opts, callback);
opts.nodeId='b'
api.graphIdPut(" ", "add_node", opts, callback);
opts.nodeId='c'
api.graphIdPut(" ", "add_node", opts, callback);
opts.sourceNode='a'
opts.targetNode='b'
api.graphIdPut(" ", "add_edge", opts, callback);
opts.sourceNode='b'
opts.targetNode='c'
api.graphIdPut(" ", "add_edge", opts, callback);
api.graphIdGet(' ', 'single',callback);
api.graphIdPost("subgraph1","new_graph",opts_post,callback)
api.graphIdPost("subgraph2","new_graph",opts_post,callback)
opts.nodeId='x'
opts.nodeType='a'
api.graphIdPut("subgraph1", "add_node", opts, callback);
opts.nodeId='y'
opts.nodeType='b'
api.graphIdPut("subgraph1", "add_node", opts, callback);
opts.nodeId='z'
opts.nodeType='b'
api.graphIdPut("subgraph1", "add_node", opts, callback);
opts.nodeId='t'
opts.nodeType='g'
api.graphIdPut("subgraph1", "add_node", opts, callback);
opts.sourceNode='x'
opts.targetNode='y'
api.graphIdPut("subgraph1", "add_edge", opts, callback);
opts.sourceNode='y'
opts.targetNode='x'
api.graphIdPut("subgraph1", "add_edge", opts, callback);
api.graphIdPost("subgraph1/subgraph12","new_graph",opts_post,callback)
api.graphIdPost("subgraph2/subgraph12","new_graph",opts_post,callback)
api.graphIdPost("subgraph1/subgraph12/toto","new_graph",opts_post,callback)
opts_post.patternName = "subgraph1"
api.graphIdPost("r1","new_rule",opts_post,callback)
api.graphIdPut("r1", "add_edge", opts, callback);
opts.sourceNode='y'
opts.targetNode='x'