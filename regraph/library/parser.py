"""Parsing of the graph transformation commands."""

from pyparsing import (Word, alphanums, nums, CaselessKeyword, Suppress,
                       Literal, delimitedList, Dict, Group,
                       Optional, Forward, Combine)

# Definition of literals
point = Literal('.')
plusorminus = (Literal('+') | Literal('-'))

# For names of the nodes and the attributes definition
number = Word(nums).setParseAction(lambda s, l, t: [int(t[0])])

integer = Optional(plusorminus) + Word(nums)
def eval_int(s, l, t):
    if len(t) > 1:
        if t[0] == '-' or t[0] == '+':
            return [int(t[0] + t[1])]
        else:
            return [int(t[0])]
    else:
        return [int(t[0])]

integer.setParseAction(eval_int)

floatnumber = Optional(plusorminus).setResultsName("sign") + Combine(
    Word(nums) + point + Optional(number)
)
def eval_float(s, l, t):
    if len(t) > 1:
        if t[0] == '-' or t[0] == '+':
            return [float(t[0] + t[1])]
        else:
            return [float(t[0])]
    else:
        return [float(t[0])]
floatnumber.setParseAction(eval_float)

var = Word(alphanums, "_" + alphanums)

node = (number | var)

type_name = Word(alphanums, "_" + alphanums).setResultsName("type")

# define here list of nodes

list_open = Suppress(Literal("["))
list_close = Suppress(Literal("]"))
list_of_nodes = delimitedList(node, delim=r',')

# define here attributes format

attr_open = Suppress(Literal("{"))
attr_close = Suppress(Literal("}"))

colon = Suppress(Literal(":"))
field_name = Word(alphanums)

list_member_val = Forward()
list_member_val << (
    floatnumber |
    integer |
    var |
    list_open + delimitedList(list_member_val, delim=r',') + list_close)


dictMembers = Forward()
field_val = Forward()
field_val << (
    floatnumber |
    integer |
    var |
    attr_open + Optional(dictMembers) + attr_close |
    list_open + Group(delimitedList(list_member_val)) + list_close
)

memberDef = Dict(Group(field_name + colon + field_val))

dictMembers << delimitedList(memberDef)

attributes = attr_open + Optional(dictMembers).setResultsName("attributes") +\
    attr_close


clone = CaselessKeyword("CLONE")
clone.setParseAction(lambda t: t[0].lower())
clone = clone + node.setResultsName("node")

merge = CaselessKeyword("MERGE")
merge.setParseAction(lambda t: t[0].lower())
method = CaselessKeyword("METHOD")
union = CaselessKeyword("UNION")
as_keyword = CaselessKeyword("AS")
intersection = CaselessKeyword("INTERSECTION")
method_id = (union | intersection).setResultsName("method")
method_id.setParseAction(lambda t: t[0].lower())
merge = merge + list_open +\
    Group(list_of_nodes).setResultsName("nodes") +\
    list_close +\
    Optional(method + method_id) +\
    Optional(as_keyword + node.setResultsName("node_name"))

delete_node = CaselessKeyword("DELETE_NODE")
delete_node.setParseAction(lambda t: t[0].lower())
delete_node = delete_node + node.setResultsName("node")

type_keyword = CaselessKeyword("TYPE")
type_keyword.setParseAction(lambda t: t[0].lower())

typing = type_keyword + type_name

add_node = CaselessKeyword("ADD_NODE")
add_node.setParseAction(lambda t: t[0].lower())
add_node = add_node + Optional(node.setResultsName("node")) +\
    Optional(typing) + Optional(attributes)

delete_edge = CaselessKeyword("DELETE_EDGE")
delete_edge.setParseAction(lambda t: t[0].lower())
delete_edge = delete_edge + node.setResultsName("node_1") +\
    node.setResultsName("node_2")

add_edge = CaselessKeyword("ADD_EDGE")
add_edge.setParseAction(lambda t: t[0].lower())
add_edge = add_edge + node.setResultsName("node_1") +\
    node.setResultsName("node_2")

command = (
    add_node |
    clone |
    merge |
    delete_node |
    delete_edge |
    add_edge
)

parser = command.setResultsName("keyword") + "."
