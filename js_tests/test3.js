
var IRegraphHttpApi = require('i_regraph_http_api');

var api = new IRegraphHttpApi.DefaultApi();

var callback = function (error, data, response) {
	if (error) {
		console.error(error.response.error.status + " : " + error.response.error.text);
	} else {
		console.log(response.status + " : data = " + JSON.stringify(data));
	}
};
var nuggetNames = new IRegraphHttpApi.NuggetNames({"name":["nug1"]}); 
api.graphGetKappagraphIdPost("/kappa_base_metamodel/kappa_metamodel/newmetakappa/", nuggetNames, callback);