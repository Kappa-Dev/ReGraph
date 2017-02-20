"""."""
import copy
import warnings

from matplotlib import pyplot as plt

import networkx as nx

from regraph.library.parser import parser


def valid_attributes(attrs, typed_node_target):
    # pred = typed_node_target.attributes_typing
    # # print("")
    # # print("target",typed_node_target)
    # # print("node",attrs)
    # if pred is not None:
    #     return pred(attrs)
    return is_subdict(attrs, typed_node_target)


def is_subdict(small_dict, big_dict):
    """Check if the dictionary is a subset of other."""
    normalize_attrs(small_dict)
    normalize_attrs(big_dict)
    if small_dict is None:
        return True
    if len(small_dict) == 0:
        return True
    if all([len(v) == 0 for k, v in small_dict.items()]):
        return True
    if big_dict is None and len(small_dict) != 0:
        return False
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
        return set([value])


def normalize_attrs(attrs_):
    if attrs_ is not None:
        for k, v in attrs_.items():
            attrs_[k] = to_set(v)
    else:
        attrs_ = dict()


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


def dict_sub(a, b):
    res = copy.deepcopy(a)
    normalize_attrs(res)
    if b is None:
        return res
    for key, value in b.items():
        if key not in a.keys():
            warnings.warn(
                "Dict A does not have attribute '%s'" %
                (str(key)), RuntimeWarning)
        else:
            elements_to_remove = []
            for el in to_set(value):
                if el in a[key]:
                    elements_to_remove.append(el)
                else:
                    warnings.warn(
                        "Dict A doesn't have '%s' with key '%s'" %
                        (str(el), str(key)), RuntimeWarning)
            for el in elements_to_remove:
                res[key].remove(el)
    return res


def listOr(*l):
    return(lambda x: any([f(x) for f in l]))


def simplify_commands(commands, di=False):
    """ Returns a simplified list of transformations that have the same
        behaviour as commands """
    command_strings = [c for c in commands.splitlines() if len(c) > 0]
    actions = []
    for command in command_strings:
        try:
            parsed = parser.parseString(command).asDict()
            actions.append(parsed)
        except:
            raise ValueError("Cannot parse command '%s'" % command)

    # We keep updated a list of the element we added, the lines of
    # transformations that added them or added attributes to them
    # and the type of addition we did (node or edge)

    added = []
    ad_index = []
    ad_type = []

    # We keep updated a list of the element we deleted and the lines of
    # transformation that deleted them or deleted attributes from them

    deleted = []
    del_index = []

    # We keep updated a list of the element we cloned and the line of
    # transformation that cloned them

    cloned = []
    clone_index = []

    # List of elements to remove at the end

    elements_to_remove = []

    # For each line of command we change what to remove and what to keep
    # We update the lists at each step, the only operations that actually
    # do simplify the commands are the deletion of nodes and edges and the
    # merges. They try to find the all the operations they can remove
    # without changing the behaviour

    for i in range(len(actions)):
        action = actions[i]
        if action["keyword"] == "add_node":
            added.append(action["node"])
            ad_index.append([i])
            ad_type.append("node")
        elif action["keyword"] == "delete_node":
            if action["node"] not in cloned:
                # If the node haven't been cloned before
                rem_el = []
                for j in range(len(added)):
                    el = added[j]
                    if (type(el) == tuple and (el[0] == action["node"] or
                                               el[1] == action["node"])) or\
                       el == action["node"]:
                        # If the node have been involved in an addition
                        # we remove that addition since it has been
                        # deleted now, if there are not more lines that
                        # refers to the addition of that node, we can
                        # remove the deletion of the node
                        # Finding the node in added is not enough to
                        # remove the deletion since it can be an
                        # addition of an edge, we have to check if it
                        # the node itself that we added
                        if el == action["node"]:
                            elements_to_remove.append(i)
                        for k in ad_index[j]:
                            elements_to_remove.append(k)
                        rem_el.append(j)
                k = 0
                for j in rem_el:
                    del added[j - k]
                    del ad_index[j - k]
                    del ad_type[j - k]
                    k += 1
                rem_el = []
                for j in range(len(deleted)):
                    el = deleted[j]
                    if (type(el) == tuple and (el[0] == action["node"] or
                                               el[1] == action["node"])) or\
                       el == action["node"]:
                        # If the node have been involved in a deletion
                        # we can remove that deletion since the deletion
                        # of the node itself will delete what the deletion
                        # would have deleted
                        for k in del_index[j]:
                            elements_to_remove.append(k)
                        rem_el.append(j)
                k = 0
                for j in rem_el:
                    del deleted[j - k]
                    del del_index[j - k]
                    k += 1
            else:
                # If the node have been cloned before, we can't delete the
                # transformations that happened before the cloning since
                # they affected the clones too. We do so by comparing the
                # line of the transformation we are looking at and the line
                # of the last cloning operation that happened
                rem_el = []
                ind = max([clone_index[i] for i in range(len(cloned)) if cloned[i] == action["node"]])
                for j in range(len(added)):
                    el = added[j]
                    if (type(el) == tuple and (el[0] == action["node"] or\
                                               el[1] == action["node"])) or\
                        el == action["node"]:
                        rem_ind = []
                        for k in ad_index[j]:
                            if k > ind:
                                elements_to_remove.append(k)
                                rem_ind.append(k)
                        if ad_index[j] == rem_ind:
                            rem_el.append(j)
                        else:
                            for k in rem_ind:
                                ad_index[j].remove(k)
                m = 0
                for j in rem_el:
                    del added[j - m]
                    del ad_index[j - m]
                    del ad_type[j - m]
                    m += 1
                rem_el = []
                for j in range(len(deleted)):
                    el = deleted[j]
                    if (type(el) == tuple and (el[0] == action["node"] or\
                                               el[1] == action["node"])) or\
                        el == action["node"]:
                        rem_ind = []
                        for k in del_index[j]:
                            if k > ind:
                                elements_to_remove.append(k)
                                rem_ind.append(k)
                        if del_index[j] == rem_ind:
                            rem_el.append(j)
                        else:
                            for k in rem_ind:
                                del_index[j].remove(k)
                m = 0
                for j in rem_el:
                    del deleted[j - m]
                    del del_index[j - m]
                    m += 1
                ind = clone_index.index(ind)
                del cloned[ind]
                del clone_index[ind]
            deleted.append(action["node"])
            del_index.append([i])
        elif action["keyword"] == "add_node_attrs":
            if action["node"] in added:
                j = added.index(action["node"])
                ad_index[j].append(i)
            else:
                added.append(action["node"])
                ad_index.append([i])
                ad_type.append("node_attrs")
        elif action["keyword"] == "delete_node_attrs":
            if action["node"] in deleted:
                j = deleted.index(action["node"])
                del_index[j].append(i)
            else:
                deleted.append(action["node"])
                del_index.append([i])
        elif action["keyword"] == "add_edge":
            e = (action["node_1"], action["node_2"])
            added.append(e)
            ad_index.append([i])
            ad_type.append("edge")
        elif action["keyword"] == "delete_edge":
            # It is the same idea as in the delete_node function, but with
            # a little bit more complexity since we have two nodes that
            # can possibly be cloned.
            # This time, finding the edge in the added list automatically
            # means we have to remove the deletion and the addition in the
            # case we didn't clone any of our nodes
            e = (action["node_1"], action["node_2"])
            if e[0] not in cloned and e[1] not in cloned:
                rem_el = []
                for j in range(len(added)):
                    el = added[j]
                    if type(el) == tuple and\
                       (el == e or (not di and el == (e[1], e[0]))):
                        elements_to_remove.append(i)
                        for k in ad_index[j]:
                            elements_to_remove.append(k)
                        rem_el.append(j)
                k = 0
                for j in rem_el:
                    del added[j - k]
                    del ad_index[j - k]
                    del ad_type[j - k]
                    k += 1
                rem_el = []
                for j in range(len(deleted)):
                    el = deleted[j]
                    if type(el) == tuple and\
                       (el == e or (not di and el == (e[1], e[0]))):
                        for k in del_index[j]:
                            elements_to_remove.append(k)
                        rem_el.append(j)
                k = 0
                for j in rem_el:
                    del deleted[j - k]
                    del del_index[j - k]
                    k += 1
            else:
                # Same idea as before if one of the nodes have been cloned,
                # but we have to take the max of the line number of all the
                # cloning operation on node 0 and node 1
                ind = 0
                if e[0] in cloned:
                    ind = max([clone_index[i] for i in range(len(cloned)) if cloned[i] == e[0]])
                if e[1] in cloned:
                    ind = max([ind] + [clone_index[i] for i in range(len(cloned)) if cloned[i] == e[1]])

                ind = clone_index.index(ind)

                if e[0] in cloned:
                    rem_el = []
                    for j in range(len(added)):
                        el = added[j]
                        if type(el) == tuple and\
                           (el == e or (not di and el == (e[1], e[0]))):
                            rem_ind = []
                            for k in ad_index[j]:
                                if k > clone_index[ind]:
                                    elements_to_remove.append(k)
                                    # We remove the delete_edge operation
                                    # iff the same edge have been added
                                    # after the last cloning operation
                                    if ad_type[j] == "edge":
                                        elements_to_remove.append(i)
                                    rem_ind.append(k)
                            if ad_index[j] == rem_ind:
                                rem_el.append(j)
                            else:
                                for k in rem_ind:
                                    ad_index[j].remove(k)
                    m = 0
                    for j in rem_el:
                        del added[j - m]
                        del ad_index[j - m]
                        del ad_type[j - m]
                        m += 1
                    rem_el = []
                    for j in range(len(deleted)):
                        el = deleted[j]
                        if type(el) == tuple and\
                           (el == e or (not di and el == (e[1], e[0]))):
                            rem_ind = []
                            for k in del_index[j]:
                                if k > clone_index[ind]:
                                    elements_to_remove.append(k)
                                    rem_ind.append(k)
                            if del_index[j] == rem_ind:
                                rem_el.append(j)
                            else:
                                for k in rem_ind:
                                    del_index[j].remove(k)
                    m = 0
                    for j in rem_el:
                        del deleted[j - m]
                        del del_index[j - m]
                        m += 1
                if e[1] in cloned:
                    rem_el = []
                    for j in range(len(added)):
                        el = added[j]
                        if type(el) == tuple and\
                           (el == e or (not di and el == (e[1], e[0]))):
                            rem_ind = []
                            for k in ad_index[j]:
                                if k > clone_index[ind]:
                                    elements_to_remove.append(k)
                                    if ad_type[j] == "edge":
                                        elements_to_remove.append(i)
                                    rem_ind.append(k)
                            if ad_index[j] == rem_ind:
                                rem_el.append(j)
                            else:
                                for k in rem_ind:
                                    ad_index[j].remove(k)
                    m = 0
                    for j in rem_el:
                        del added[j - m]
                        del ad_index[j - m]
                        del ad_type[j - m]
                        m += 1
                    rem_el = []
                    for j in range(len(deleted)):
                        el = deleted[j]
                        if type(el) == tuple and\
                           (el == e or (not di and el == (e[1], e[0]))):
                            rem_ind = []
                            for k in del_index[j]:
                                if k > clone_index[ind]:
                                    elements_to_remove.append(k)
                                    rem_ind.append(k)
                            if del_index[j] == rem_ind:
                                rem_el.append(j)
                            else:
                                for k in rem_ind:
                                    del_index[j].remove(k)
                    m = 0
                    for j in rem_el:
                        del deleted[j - m]
                        del del_index[j - m]
                        m += 1
            deleted.append(e)
            del_index.append([i])
        elif action["keyword"] == "add_edge_attrs":
            e = (action["node_1"], action["node_2"])
            if e in added:
                j = added.index(e)
                ad_index[j].append(i)
            elif not di and (e[1], e[0]) in added:
                j = added.index((e[1], e[0]))
                ad_index[j].append(i)
            else:
                added.append(e)
                ad_index.append([i])
                ad_type.append("edge_attrs")
        elif action["keyword"] == "delete_edge_attrs":
            e = (action["node_1"], action["node_2"])
            if e in deleted:
                j = deleted.index(e)
                del_index[j].append(i)
            elif not di and (e[1], e[0]) in deleted:
                j = deleted.index((e[1], e[0]))
                del_index[j].append(i)
            else:
                deleted.append(e)
                del_index.append([i])
        elif action["keyword"] == "clone":
            if "node_name" in action.keys():
                added.append(action["node_name"])
                ad_index.append([i])
                ad_type.append("node")
            cloned.append(action["node"])
            clone_index.append(i)
        elif action["keyword"] == "merge":
            if "node_name" in action.keys():
                node_name = action["node_name"]
            else:
                node_name = "_".join(action["nodes"])

            added.append(node_name)
            ad_index.append([i])
            ad_type.append("node")

    return "\n".join(
        [command_strings[i] for i in range(len(actions)) if i not in elements_to_remove])


def make_canonical_commands(g, commands, di=False):
    """ Takes commands and the graph it refers to and returns a list of
        canonical transformations that have the same behaviour.
        The canonical form of a transformation follows this pattern :
            DELETIONS (DELETE_NODE, DELETE_NODE_ATTRS, DELETE_EDGE, DELETE_EDGE_ATTRS)
            CLONING (CLONE)
            ADDING and MERGING (ADD_NODE, ADD_NODE_ATTRS, ADD_EDGE, ADD_EDGE_ATTRS, MERGE)
    """
    res = []

    # We do multiple steps of simplification, until we found a fixed-point

    aux = commands
    next_step = simplify_commands(commands, di)
    while next_step != aux:
        aux = next_step
        next_step = simplify_commands(aux, di)

    # We keep updated an environment with our nodes and our edges

    env_nodes = [n for n in g.nodes()]
    env_edges = [e for e in g.edges()]

    if not di:
        for e in g.edges():
            if not (e[1], e[0]) in env_edges:
                env_edges.append((e[1], e[0]))

    # For each transformation we choose if we do it in this step or if we
    # keep it for later

    while next_step != '':
        command_strings = [c for c in next_step.splitlines() if len(c) > 0]
        actions = []
        for command in command_strings:
            try:
                parsed = parser.parseString(command).asDict()
                actions.append(parsed)
            except:
                raise ValueError("Cannot parse command '%s'" % command)

        next_step = ''

        # We have 3 strings for each line of the canonical pattern

        add_step = ''
        del_step = ''
        clone_step = ''

        # Added is the list of elements we will add at to our environment
        # at the end of the step, we add them at the end so they are not
        # taken into account in the current step

        added = []
        cloned = []

        # If a node is in clone_wait, every cloning operation on it will
        # be delayed to next step. Same for other lists

        clone_wait = []
        merge_wait = []
        del_wait = []
        ad_wait = []

        # If we can't add a node with name n in this step, we don't want
        # another node with the same name to be added before it

        protected_names = []

        # For each action we update our lists and we chose what to do

        for i in range(len(actions)):
            action = actions[i]
            if action["keyword"] == "add_node":
                if action["node"] not in protected_names:
                    add_step += command_strings[i] + "\n"
                    added.append(action["node"])
            elif action["keyword"] == "delete_node":
                if action["node"] in env_nodes and\
                   action["node"] not in del_wait:
                    del_step += command_strings[i] + "\n"
                    env_nodes.remove(action["node"])
                else:
                    next_step += command_strings[i] + "\n"
                    ad_wait.append(action["node"])
            elif action["keyword"] == "add_node_attrs":
                if action["node"] in env_nodes and\
                   action["node"] not in ad_wait:
                    add_step += command_strings[i] + "\n"
                    added.append(action["node"])
                    clone_wait.append(action["node"])
                else:
                    next_step += command_strings[i] + "\n"
                    ad_wait.append(action["node"])
                    clone_wait.append(action["node"])
            elif action["keyword"] == "delete_node_attrs":
                if action["node"] in env_nodes and\
                   action["node"] not in del_wait:
                    del_step += command_strings[i] + "\n"
                else:
                    next_step += command_strings[i] + "\n"
                    clone_wait.append(action["node"])
                    ad_wait.append(action["node"])
            elif action["keyword"] == "add_edge":
                e = (action["node_1"], action["node_2"])
                if e[0] in env_nodes and\
                   e[1] in env_nodes and\
                   e[0] not in ad_wait and\
                   e[1] not in ad_wait:
                    add_step += command_strings[i] + "\n"
                    added.append(e)
                    if not di:
                        added.append((e[1], e[0]))
                    clone_wait.append(action["node_1"])
                    clone_wait.append(action["node_2"])
                else:
                    next_step += command_strings[i] + "\n"
                    clone_wait.append(action["node_1"])
                    clone_wait.append(action["node_2"])
                    merge_wait.append(action["node_1"])
                    merge_wait.append(action["node_2"])
            elif action["keyword"] == "delete_edge":
                e = (action["node_1"], action["node_2"])
                if (e in env_edges or
                   (not di and (e[1], e[0]) in env_edges)) and\
                   e[0] not in del_wait and\
                   e[1] not in del_wait:
                    is_cloned = False
                    for l in cloned:
                        if e[0] in l:
                            next_step += command_strings[i] + "\n"
                            clone_wait.append(action["node_1"])
                            clone_wait.append(action["node_2"])
                            merge_wait.append(action["node_1"])
                            merge_wait.append(action["node_2"])
                            is_cloned = True
                            break
                    if not is_cloned:
                        del_step += command_strings[i] + "\n"
                        clone_wait.append(action["node_1"])
                        clone_wait.append(action["node_2"])
                        env_edges.remove(e)
                        if not di:
                            env_edges.remove((e[1], e[0]))
                else:
                    next_step += command_strings[i] + "\n"
                    clone_wait.append(action["node_1"])
                    clone_wait.append(action["node_2"])
                    merge_wait.append(action["node_1"])
                    merge_wait.append(action["node_2"])
            elif action["keyword"] == "add_edge_attrs":
                e = (action["node_1"], action["node_2"])
                if (e in env_edges or
                   (not di and (e[1], e[0]) in env_edges)) and\
                   e[0] not in ad_wait and\
                   e[1] not in ad_wait:
                    add_step += command_strings[i] + "\n"
                    added.append(e)
                    if not di:
                        added.append((e[1], e[0]))
                    clone_wait.append(action["node_1"])
                    clone_wait.append(action["node_2"])
                else:
                    next_step += command_strings[i] + "\n"
                    clone_wait.append(action["node_1"])
                    clone_wait.append(action["node_2"])
                    merge_wait.append(action["node_1"])
                    merge_wait.append(action["node_2"])
            elif action["keyword"] == "delete_edge_attrs":
                e = (action["node_1"], action["node_2"])
                if (e in env_edges or
                   (not di and (e[1], e[0]) in env_edges)) and\
                   e[0] not in del_wait and\
                   e[1] not in del_wait:
                    is_cloned = False
                    for l in cloned:
                        if e[0] in l:
                            next_step += command_strings[i] + "\n"
                            clone_wait.append(action["node_1"])
                            clone_wait.append(action["node_2"])
                            merge_wait.append(action["node_1"])
                            merge_wait.append(action["node_2"])
                            is_cloned = True
                        elif e[1] in l:
                            next_step += command_strings[i] + "\n"
                            clone_wait.append(action["node_1"])
                            clone_wait.append(action["node_2"])
                            merge_wait.append(action["node_1"])
                            merge_wait.append(action["node_2"])
                            is_cloned = True
                    if not is_cloned:
                        del_step += command_strings[i] + "\n"
                        clone_wait.append(action["node_1"])
                        clone_wait.append(action["node_2"])
                else:
                    next_step += command_strings[i] + "\n"
                    clone_wait.append(action["node_1"])
                    clone_wait.append(action["node_2"])
                    merge_wait.append(action["node_1"])
                    merge_wait.append(action["node_2"])
            elif action["keyword"] == "clone":
                node = action["node"]
                if "node_name" in action.keys():
                    new_node = action["node_name"]
                else:
                    j = 1
                    new_node = str(node) + str(j)
                    while new_node in env_nodes or new_node in added:
                        j += 1
                        new_node = str(node) + str(j)
                if node in env_nodes and\
                   node not in clone_wait and\
                   new_node not in protected_names and\
                   fold_left(lambda e, acc: (e != node or
                             (type(e) == tuple and
                              e[1] != node and
                              e[0] != node)) and
                             acc,
                             True,
                             added):
                    clone_step += command_strings[i] + "\n"
                    added.append(new_node)
                    del_wait.append(node)
                    found = False
                    for i in range(len(cloned)):
                        if node in cloned[i]:
                            cloned[i].append(new_node)
                            found = True
                    if not found:
                        cloned.append([new_node, node])
                    to_add = []
                    for e in env_edges:
                        if e[0] == node:
                            to_add.append((new_node, e[1]))
                        elif e[1] == node:
                            to_add.append((e[0], new_node))
                    for e in added:
                        if type(e) == tuple:
                            if e[0] == node and\
                               e[1] != node:
                                to_add.append((new_node, e[1]))
                            elif e[1] == node and e[0] != node:
                                to_add.append((e[0], new_node))
                    for e in to_add:
                        added.append(e)
                else:
                    next_step += command_strings[i] + "\n"
                    del_wait.append(node)
                    merge_wait.append(node)
                    ad_wait.append(node)
                    protected_names.append(new_node)
            elif action["keyword"] == "merge":
                if "node_name" in actions[i].keys():
                    node_name = actions[i]["node_name"]
                else:
                    node_name = "_".join(actions[i]["nodes"])
                if fold_left(lambda n, acc: (n in env_nodes and
                                             n not in merge_wait) and
                                             acc,
                             True,
                             action["nodes"]) and\
                    node_name not in protected_names:
                    add_step += command_strings[i] + "\n"

                    added.append(node_name)
                    clone_wait.append(node_name)

                    rem_el = []
                    for e in env_edges:
                        if e[0] in action["nodes"] and\
                           e[1] in action["nodes"]:
                           if not e in rem_el:
                               rem_el.append(e)
                        if e[0] in action["nodes"]:
                            if not e in rem_el:
                                rem_el.append(e)
                            if e[1] not in action["nodes"]:
                                added.append((node_name, e[1]))
                        elif e[1] in action["nodes"]:
                            if not e in rem_el:
                                rem_el.append(e)
                            if e[0] not in action["nodes"]:
                                added.append((e[0], node_name))
                    for e in rem_el:
                        while e in env_edges:
                            env_edges.remove(e)
                            if not di:
                                env_edges.remove((e[1], e[0]))
                    rem_el = []
                    for e in added:
                        if type(e) == tuple:
                            if e[0] in action["nodes"] and\
                               e[1] in action["nodes"]:
                               if not e in rem_el:
                                   rem_el.append(e)
                            if e[0] in action["nodes"]:
                               if not e in rem_el:
                                   rem_el.append(e)
                               if e[1] not in action["nodes"]:
                                   added.append((node_name, e[1]))
                            elif e[1] in action["nodes"]:
                                if not e in rem_el:
                                    rem_el.append(e)
                                if e[0] not in action["nodes"]:
                                    added.append((e[0], node_name))
                    for e in rem_el:
                        while e in added:
                            added.remove(e)
                            if not di:
                                added.remove((e[1], e[0]))
                else:
                    next_step += command_strings[i] + "\n"
                    protected_names.append(node_name)

        for el in added:
            if type(el) == tuple:
                env_edges.append(el)
            else:
                env_nodes.append(el)

        if del_step + clone_step + add_step == '':
            raise ValueError(
                "Can't find any new transformations and actions is non-empty :\n%s" %
                next_step
            )

        res.append(del_step + clone_step + add_step)

    return res


def compose_homomorphisms(d2, d1):
    return dict([(key, d2[value]) for key, value in d1.items()])


def check_homomorphism(source, target, dictionary, ignore_attrs=False):
    """Check if the homomorphism is valid (preserves edges,
    and attributes if requires)."""

    # check if there is mapping for all the nodes of source graph
    if set(source.nodes()) != set(dictionary.keys()):
        raise ValueError(
            "Invalid homomorphism: Mapping is not covering all the nodes of source graph!")
    if not set(dictionary.values()).issubset(target.nodes()):
        raise ValueError(
            "invalid homomorphism: image not in target graph"
        )

    # check connectivity
    for s_edge in source.edges():
        if not (dictionary[s_edge[0]], dictionary[s_edge[1]]) in target.edges():
            if not target.is_directed():
                if not (dictionary[s_edge[1]], dictionary[s_edge[0]]) in target.edges():
                    raise ValueError(
                        "Invalid homomorphism: Connectivity is not preserved!" +\
                        " Was expecting an edge %s->%s" %
                        (dictionary[s_edge[1]], dictionary[s_edge[0]]))
            else:
                raise ValueError(
                    "Invalid homomorphism: Connectivity is not preserved!" +\
                    " Was expecting an edge between %s and %s" %
                    (dictionary[s_edge[0]], dictionary[s_edge[1]]))

    for s, t in dictionary.items():
        if not ignore_attrs:
            # check sets of attributes of nodes (here homomorphism = set inclusion)
            if not valid_attributes(source.node[s], target.node[t]):
                raise ValueError(
                    "Invalid homomorphism: Attributes of nodes source:'%s' and target:'%s' do not match!" %
                    (str(s), str(t)))

    if not ignore_attrs:
        # check sets of attributes of edges (homomorphism = set inclusion)
        for s1, s2 in source.edges():
            if not valid_attributes(
               source.edge[s1][s2], target.edge[dictionary[s1]][dictionary[s2]]):
                raise ValueError(
                    "Invalid homomorphism: Attributes of edges (%s)-(%s) and (%s)-(%s) do not match!" %
                    (s1, s2, dictionary[s1],
                        dictionary[s2]))
    return True


def identity(a, b):
    dic = {}
    for n in a.nodes():
        if n in b.nodes():
            dic[n] = n
        else:
            raise ValueError(
                "Node '%s' not found in the second graph!" % n
            )
    return dic


def is_monic(f):
    """Check if the homomorphism is monic."""
    return len(set(f.keys())) ==\
        len(set(f.values()))


def assert_graph_eq(g1, g2):
    assert(set(g1.nodes()) == set(g2.nodes()))
    if g1.is_directed() and g2.is_directed():
        assert(set(g1.edges()) == set(g2.edges()))
    else:
        for s, t in g1.edges():
            assert((s, t) in g2.edges() or (t, s) in g2.edges())
    for n in g1.nodes():
        assert(g1.node[n] == g2.node[n])
    for e1, e2 in g1.edges():
        assert(g1.edge[e1][e2] == g2.edge[e1][e2])
    return
