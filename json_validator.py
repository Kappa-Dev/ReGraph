from jsonschema import validate
import jsonschema

sch = {
    "type" : "object",
    "$schemas" : "#/definition/GraphHierarchy",
    "definitions": {
        "Node": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "ttype": {
                    "type": "string"
                }
            }
        },
        "Edge": {
            "type": "object",
            "properties": {
                "from": {
                    "type": "string"
                },
                "to": {
                    "type": "string"
                }
            }
        },
        "Graph": {
            "type": "object",
            "properties": {
                "edges": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/Edge"
                    }
                },
                "nodes": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/Node"
                    }
                }
            }
        },
        "GraphHierarchy": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "top_graph": {
                    "$ref": "#/definitions/Graph"
                },
                "children": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/GraphHierarchy"
                    }
                }
            }
        },
        "NameHierarchy": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "children": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/NameHierarchy"
                    }
                }
            }
        },
        "Couple": {
            "type": "object",
            "properties": {
                "left": {
                    "type": "string"
                },
                "right": {
                    "type": "string"
                }
            }
        },
        "Matching": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/Couple"
            }
        }
    }
}

schemas = {
    "Node": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string"
            },
            "ttype": {
                "type": "string"
            }
        }
    },
    "Edge": {
        "type": "object",
        "properties": {
            "from": {
                "type": "string"
            },
            "to": {
                "type": "string"
            }
        }
    },
    "Graph": {
        "type": "object",
        "properties": {
            "edges": {
                "type": "array",
                "items": {
                    "$ref": "#/Edge"
                }
            },
            "nodes": {
                "type": "array",
                "items": {
                    "$ref": "#/Node"
                }
            }
        }
    },
    "GraphHierarchy": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "top_graph": {
                "$ref": "#/Graph"
            },
            "children": {
                "type": "array",
                "items": {
                    "$ref": "#/GraphHierarchy"
                }
            }
        }
    },
    "NameHierarchy": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "children": {
                "type": "array",
                "items": {
                    "$ref": "#/NameHierarchy"
                }
            }
        }
    },
    "Couple": {
        "type": "object",
        "properties": {
            "left": {
                "type": "string"
            },
            "right": {
                "type": "string"
            }
        }
    },
    "Matching": {
        "type": "array",
        "items": {
            "$ref": "#/Couple"
        }
    }
}

if __name__ == "__main__":
    try:
        print(validate({"sad":"asdad"},sch))
        print(validate([1,2,3],sch))
        validate([2, 3, 4], {"maxItems" : 2})
    except jsonschema.ValidationError as e:
        print(e.message)
    except jsonschema.SchemaError as e:
        print(e)
     