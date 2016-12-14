
var IRegraphHttpApi = require('i_regraph_http_api');

var api = new IRegraphHttpApi.DefaultApi();

var callback = function(error, data, response) {
  if (error) {
    console.error(error.response.error.status + " : " + error.response.error.text);
  } else {
    console.log(response.status+" : data = "+JSON.stringify(data));
  }
};

api.graphToMetakappagraphIdPut("/kami_base/kami/action_graph/","newmetakappa", callback);