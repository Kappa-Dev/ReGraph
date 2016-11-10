
var IRegraphHttpApi = require('i_regraph_http_api');

var api = new IRegraphHttpApi.DefaultApi();

var callback = function(error, data, response) {
  if (error) {
    console.error(error.response.error.status + " : " + error.response.error.text);
  } else {
    console.log(response.status+" : data = "+JSON.stringify(data));
  }
};

var hierarchy_test={
  "name": "tyty",
  "top_graph": {
    "nodes": [
      {
        "id": "c",
        "type": "c" 
      },
      {
        "id": "b",
        "type": "b"
      },
      {
        "id": "a",
        "type": "a"
      }
    ],
    "edges": [
      {
        "to": "c",
        "from": "b",
        "attrs": {}
      },
      {
        "to": "b",
        "from": "a",
        "attrs": {}
      }
    ]
  },
  "children": [
    {
      "name": "subgraph2",
      "top_graph": {
        "nodes": [],
        "edges": []
      },
      "children": [
        {
          "name": "subgraph12",
          "top_graph": {
            "nodes": [],
            "edges": []
          },
          "children": []
        }
      ]
    },
    {
      "name": "subgraph1",
      "top_graph": {
        "nodes": [
          {
            "id": "z",
            "type": "b"
          },
          {
            "id": "y",
            "type": "b"
          },
          {
            "id": "x",
            "type": "a"
          }
        ],
        "edges": [
          {
            "to": "y",
            "from": "x",
            "attrs": {}
          }
        ]
      },
      "children": [
        {
          "name": "subgraph12",
          "top_graph": {
            "nodes": [],
            "edges": []
          },
          "children": [
            {
              "name": "toto",
              "top_graph": {
                "nodes": [],
                "edges": []
              },
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
var hierarchy_test2={
  "name": "/",
  "top_graph": {
    "nodes": [
      {
        "id": "c",
        "type": null
      },
      {
        "id": "b",
        "type": null
      },
      {
        "id": "a",
        "type": null
      }
    ],
    "edges": [
      {
        "to": "c",
        "from": "b",
        "attrs": {}
      },
      {
        "to": "b",
        "from": "a",
        "attrs": {}
      }
    ]
  },
  "children": [
    {
      "name": "subgraph2",
      "top_graph": {
        "nodes": [],
        "edges": []
      },
      "children": [
        {
          "name": "subgraph12",
          "top_graph": {
            "nodes": [],
            "edges": []
          },
          "children": []
        }
      ]
    },
    {
      "name": "subgraph1",
      "top_graph": {
        "nodes": [
          {
            "id": "z",
            "type": "b"
          },
          {
            "id": "y",
            "type": "b"
          },
          {
            "id": "x",
            "type": "a"
          }
        ],
        "edges": [
          {
            "to": "y",
            "from": "x",
            "attrs": {}
          }
        ]
      },
      "children": [
        {
          "name": "subgraph12",
          "top_graph": {
            "nodes": [],
            "edges": []
          },
          "children": [
            {
              "name": "toto",
              "top_graph": {
                "nodes": [],
                "edges": []
              },
              "children": []
            }
          ]
        }
      ]
    }
  ]
};

api.graphgraphIdPost("/toto/",callback);
api.graphgraphIdPost("/tutu/",callback);
api.graphgraphIdPost("/toto/titi/",callback);
api.graphAddNodegraphIdPut("/toto/","a",null,callback);
api.graphAddNodegraphIdPut("/toto/","b",null,callback);
api.graphAddNodegraphIdPut("/toto/tutu/","x","a",callback);
api.graphAddNodegraphIdPut("/toto/titi/","x",{nodeType:"a"},callback);
api.graphAddNodegraphIdPut("/toto/titi/","y",{nodeType:"b"},callback);
api.graphAddNodegraphIdPut("/toto/titi/","y",{nodeType:"b"},callback);
api.graphAddEdgegraphIdPut("/toto/titi/", "x", "y", callback);
api.graphAddEdgegraphIdPut("/toto/titi/", "asdasdsadx", "y", callback);
api.graphAddEdgegraphIdPut("/toto/", "a", "b", callback);
api.graphAddEdgegraphIdPut("/toto/titi/", "x", "y", callback);
api.graphgraphIdGet("/toto",callback);
api.graphAddEdgegraphIdPut("/toto/titi/", "y", "x", callback);
api.graphgraphIdGet("/toto/titi/",callback);
api.graphgraphIdGet("/toto/titi///",callback);
api.graphgraphIdGet("/toto///titi///",callback);
api.hierarchyhierarchyPathGet("/",{},callback);
api.hierarchyhierarchyPathGet("/",{includeGraphs:true},callback);

h1 =  {"name":"/","children":[{"children":[],"name":"tutu","top_graph":{"edges":[],"nodes":[]}},{"children":[{"children":[],"name":"titi","top_graph":{"edges":[{"to":"y","attrs":{},"from":"x"}],"nodes":[{"id":"x","type":"a"},{"id":"y","type":"b"}]}}],"name":"toto","top_graph":{"edges":[{"to":"b","attrs":{},"from":"a"}],"nodes":[{"id":"b","type":null},{"id":"a","type":null}]}}]};
h2 =  {"name":"/","children":[{"children":[],"name":"test","top_graph":{"edges":[],"nodes":[]}},{"children":[{"children":[],"name":"titi","top_graph":{"edges":[{"to":"y","attrs":{},"from":"x"}],"nodes":[{"id":"x","type":"a"},{"id":"y","type":"b"}]}}],"name":"toto","top_graph":{"edges":[{"to":"b","attrs":{},"from":"a"}],"nodes":[{"id":"b","type":null},{"id":"a","type":null}]}}]};
h3 =  {"name":"/","children":[{"children":[],"name":"test","top_graph":{"edges":[],"nodes":[]}},{"children":[{"children":[],"name":"titi2","top_graph":{"edges":[{"to":"y","attrs":{},"from":"x"}],"nodes":[{"id":"x","type":"a"},{"id":"y","type":"b"}]}}],"name":"toto","top_graph":{"edges":[{"to":"b","attrs":{},"from":"a"}],"nodes":[{"id":"b","type":null},{"id":"a","type":null}]}}]};

api.hierarchyhierarchyPathPut("/", h1, callback);
api.hierarchyhierarchyPathPut("/", h2, callback);
api.hierarchyhierarchyPathPut("/", h3, callback);
api.hierarchyhierarchyPathGet("/",{includeGraphs:true},callback);

h4 =  {"children":[{"children":[],"name":"titi2","top_graph":{"edges":[{"to":"y","attrs":{},"from":"x"}],"nodes":[{"id":"x","type":"a"},{"id":"y","type":"b"}]}}],"name":"toadd","top_graph":{"edges":[{"to":"b","attrs":{},"from":"a"}],"nodes":[{"id":"b","type":null},{"id":"a","type":null}]}};
api.hierarchyhierarchyPathPost("/toadd/",h4,callback);
// api.graphgraphIdPost("/tutu/",callback);
// api.hierarchyhierarchyPathGet("/",{includeGraphs:true},callback);
api.graphValidateConstraintsgraphIdPut("/toto/titi/", callback);
api.graphAddConstraintgraphIdPut("/toto/","a","output","b","3","le",callback);
api.graphAddConstraintgraphIdPut("/toto/","a","output","b","2","ge",callback);
api.graphValidateConstraintsgraphIdPut("/toto/titi/", callback);
api.graphCloneNodegraphIdPut("/toto/titi/","y","y1");
api.graphValidateConstraintsgraphIdPut("/toto/titi/", callback);
api.graphCloneNodegraphIdPut("/toto/titi/","y","y2");
api.graphValidateConstraintsgraphIdPut("/toto/titi/", callback);
api.graphCloneNodegraphIdPut("/toto/titi/","y","y3");
api.graphValidateConstraintsgraphIdPut("/toto/titi/", callback);
api.graphgraphIdGet("/toto/",callback);
api.ruleruleIdPost("/r/", "toto", callback);
api.ruleAddNoderuleIdPut("/r/","added",{},callback);
api.ruleAddEdgeruleIdPut("/r/","added","a",callback);
api.ruleCloneNoderuleIdPut("/r/","a","a1",callback);
api.ruleMergeNoderuleIdPut("/r/","a","b","ab",callback);
api.ruleRmEdgeruleIdPut("/r/","added","ab",callback);
api.ruleCloneNoderuleIdPut("/r/","ab","ab1",callback);	
api.ruleRmNoderuleIdPut("/r/","ab",callback);
