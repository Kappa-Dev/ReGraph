
var IRegraphHttpApi = require('i_regraph_http_api');

var api = new IRegraphHttpApi.DefaultApi();

var callback = function (error, data, response) {
	if (error) {
		console.error(error.response.error.status + " : " + error.response.error.text);
	} else {
		console.log(response.status + " : data = " + JSON.stringify(data));
	}
};

	api.graphgraphIdPost("/kami_base/kami/action_graph/", callback);
	api.graphgraphIdPost("/kami_base/kami/action_graph/nug1/", callback);
	api.graphgraphIdPost("/kami_base/kami/action_graph/nug2/", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "A1", { nodeType: "agent" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "s1", { nodeType: "locus" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "s2", { nodeType: "locus" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "r1", { nodeType: "region" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "state_r1", { nodeType: "state" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "bnd1", { nodeType: "bnd" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "s1", "A1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "state_r1", "r1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "r1", "A1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "s2", "r1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "s1", "bnd1", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug1/", "A1_1", { nodeType: "A1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug1/", "A1_2", { nodeType: "A1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug1/", "s1_1", { nodeType: "s1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug1/", "s1_2", { nodeType: "s1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug1/", "bnd1", { nodeType: "bnd1" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug1/", "s1_1", "A1_1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug1/", "s1_2", "A1_2", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug1/", "s1_1", "bnd1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug1/", "s1_2", "bnd1", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "A1", { nodeType: "A1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "state_r1", { nodeType: "state_r1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "r1", { nodeType: "r1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "s2", { nodeType: "s2" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "s2", { nodeType: "s2" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug2/", "s2", "r1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug2/", "r1", "A1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug2/", "state_r1", "r1", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "A2", { nodeType: "agent" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "state1", { nodeType: "state" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "state2", { nodeType: "state" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "state1", "A1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "state2", "A2", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "state1", { nodeType: "state1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "state2", { nodeType: "state2" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "A2", { nodeType: "A2" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug2/", "state1", "A1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug2/", "state2", "A2", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "free", { nodeType: "is_free" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "s2", "free", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug2/", "free", { nodeType: "free" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug2/", "s2", "free", callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "state_r1", { "val": "X"}, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "state_r1", { "val": "Y"}, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/nug2/", "state_r1", { "val": "X" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "state1", { "val": "2" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "state1", { "val": "1" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/nug1/", "state1", { "val": "1" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "bnd1", { "rate": "1" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "bnd1", { "rate": "2" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/nug1/", "bnd1", { "rate": "1" }, callback);
    api.graphgraphIdDelete("/kami_base/kami/action_graph/nug2/", callback);
	api.graphgraphIdPost("/kami_base/kami/action_graph/nug3/", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "syn", { nodeType: "syn" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "syn", "A1", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug3/", "syn", { nodeType: "syn" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug3/", "A1", { nodeType: "A1" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug3/", "syn", "A1", callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/nug3/", "syn", { "rate": "0.75" }, callback);
	api.graphgraphIdPost("/kami_base/kami/action_graph/nug4/", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/", "mod", { nodeType: "mod" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/", "mod", "state_r1", callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug4/", "mod", { nodeType: "mod" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug4/", "r1", { nodeType: "r1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug4/", "A1", { nodeType: "A1" }, callback);
	api.graphAddNodegraphIdPut("/kami_base/kami/action_graph/nug4/", "state_r1", { nodeType: "state_r1" }, callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug4/", "mod", "state_r1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug4/", "r1", "A1", callback);
	api.graphAddEdgegraphIdPut("/kami_base/kami/action_graph/nug4/", "state_r1", "r1", callback);
	api.graphAddAttrgraphIdPut("/kami_base/", "action", { "fun": "0.75" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/", "mod", { "fun": "0.75" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "mod", { "fun": "0.75" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/nug4/", "mod", { "fun": "0.75" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/", "state_r1", { "val": "10" }, callback);
	api.graphAddAttrgraphIdPut("/kami_base/kami/action_graph/nug4/", "state_r1", { "val": "10" }, callback);
    api.graphUpdateGraphAttrgraphIdPut("/kami_base/kami/action_graph/nug4/",{"rate":"2"}, callback);

