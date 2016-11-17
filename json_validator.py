# from jsonschema import validate
# import jsonschema

import flex
from flex.loading.schema.paths.path_item.operation.responses.single.schema import (
    schema_validator,
)




context = flex.load('swagger.yaml')

raw_schema = {
        '$ref': '#/definitions/GraphHierarchy'
    }
schema = schema_validator(raw_schema, context=context)

if __name__ == "__main__":
    try:
        print(flex.core.validate(schema, {"name": "asdad","top_graph":{}}, context=context))
        # print(validate([1,2,3],sch))
    except ValueError as e:
        print(str(e))
     