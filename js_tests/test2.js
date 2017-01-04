
var IRegraphHttpApi = require('i_regraph_http_api');

var api = new IRegraphHttpApi.DefaultApi();

var callback = function(error, data, response) {
  if (error) {
    console.error(error.response.error.status + " : " + error.response.error.text);
  } else {
    console.log(response.status+" : data = "+JSON.stringify(data));
  }
};

//api.graphToMetakappagraphIdPut("/kami_base/kami/action_graph/","newmetakappa", callback);
//api.graphUnfoldgraphIdPut("/kappa_base_metamodel/kappa_metamodel/action_graph/", "unfolded5", ["arule2"], callback);

	api.ruleruleIdPost("/kami_base/kami/action_graph/ab_nugget1/", "pat1", callback);
	api.ruleruleIdPost("/kami_base/kami/action_graph/ab_nugget2/", "pat1", callback);
	api.ruleAddNoderuleIdPut("/kami_base/kami/action_graph/ab_nugget1/", "A3", { "nodeType": "A3" }, callback);
	api.ruleAddNoderuleIdPut("/kami_base/kami/action_graph/ab_nugget1/", "s3", { "nodeType": "s3" }, callback);
	api.ruleAddNoderuleIdPut("/kami_base/kami/action_graph/ab_nugget1/", "bnd3", { "nodeType": "bnd3" }, callback);
	api.ruleAddEdgeruleIdPut("/kami_base/kami/action_graph/ab_nugget1/", "s3", "A3", callback);
	api.ruleAddEdgeruleIdPut("/kami_base/kami/action_graph/ab_nugget1/", "s3", "bnd3", callback);
	api.ruleAddEdgeruleIdPut("/kami_base/kami/action_graph/ab_nugget1/", "sx", "bnd3", callback);

api.graphUnfoldgraphIdPut("/kami_base/kami/action_graph/", "unfolded1", ["ab_nugget1","nug1"], callback);