"""."""

import networkx as nx

def is_subdict(small_dict, big_dict):
    """Check if the dictionary is a subset of other."""

    if small_dict is None:
        return True
    if len(small_dict) == 0:
        return True
    if big_dict is None and len(small_dict) != 0:
        return True
    if len(big_dict) == 0 and len(small_dict) != 0:
        return False
    for key, value in small_dict.items():
        if key not in big_dict.keys():
            return False
        else:
            if type(value) == set:
                small_attrs = value
            else:
                small_attrs = set([value])
            if type(big_dict[key]) == set:
                big_attrs = big_dict[key]
            else:
                big_attrs = set([big_dict[key]])
            if not small_attrs.issubset(big_attrs):
                return False
    return True


def keys_by_value(dictionary, val):
    res = []
    for key, value in dictionary.items():
        if value == val:
            res.append(key)
    return res

def fold_left(f, init, l):
    """ f : a -> b -> b
        init : b
        l : a list
        Returns f(...f(l[1],f(l[0], init)) """
    res = init
    for x in l:
        res = f(x, res)
    return res

def to_set(value):
    if (type(value) == set) | (type(value) == list):
        return set(value)
    else:
        return {value}

def normalize_attrs(attrs_):
    if attrs_ != None:
        for k,v in attrs_.items():
            attrs_[k] = to_set(v)

def merge_attributes(attr1, attr2, method="union"):
    """Merge two dictionaries of attributes."""
    result = {}
    if attr1 is None:
        attr1 = {}
    if attr2 is None:
        attr2 = {}
    if method == "union":
        for key1 in attr1.keys():
            if key1 in attr2.keys():
                if attr1[key1] == attr2[key1]:
                    result.update(
                        {key1: attr1[key1]})
                else:
                    attr_set = set()
                    attr_set.update(attr1[key1])
                    attr_set.update(attr2[key1])
                    result.update(
                        {key1: attr_set})
            else:
                result.update({key1: attr1[key1]})

        for key2 in attr2.keys():
            if key2 not in result:
                result.update({key2: attr2[key2]})
    elif method == "intersection":
        for key1 in attr1.keys():
            if key1 in attr2.keys():
                if attr1[key1] == attr2[key1]:
                    result.update(
                        {key1: attr1[key1]})
                else:
                    attr_set1 = set()
                    attr_set2 = set()
                    attr_set1.update(attr1[key1])
                    attr_set2.update(attr2[key1])
                    intersect = set.intersection(attr_set1, attr_set2)
                    if len(intersect) == 1:
                        result.update({key1: {list(intersect)[0]}})
                    elif len(intersect) > 1:
                        result.update({key1: intersect})
    else:
        raise ValueError("Merging method %s is not defined!" % method)
    return result
