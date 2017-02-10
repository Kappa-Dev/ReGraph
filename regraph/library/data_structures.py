"""Define data structures used by graph rewriting tool."""

from regraph.library.utils import (is_subdict,
                                   valid_attributes)


class Homomorphism(object):
    """Define graph homomorphism data structure."""

    def __init__(self, source, target, dictionary, ignore_types=False, ignore_attrs=False):
        if Homomorphism.is_valid_homomorphism(source, target, dictionary):
            self.source_ = source
            self.target_ = target
            self.mapping_ = dictionary
            self.ignore_types = ignore_types
            self.ignore_attrs = ignore_attrs
        else:
            raise ValueError("Homomorphism is not valid!")

    def __str__(self):
        return "Source :\n%sTarget :\n%sMapping :\n%s" % \
            (str(self.source_),str(self.target_),str(self.mapping_))

    def __getitem__(self, index):
        return self.mapping_.__getitem__(index)

    def __setitem__(self, index, value):
        self.mapping_.__setitem__(index, value)

    def __delitem__(self, index):
        self.mapping_.__delitem__(index)

    def __len__(self):
        return self.mapping_.__len__()

    def __missing__(self, index):
        self.mapping_.__missing__(index)

    def is_monic(self):
        """Check if the homomorphism is monic."""
        return len(set(self.mapping_.keys())) ==\
            len(set(self.mapping_.values()))

    @staticmethod
    def is_valid_homomorphism(source, target, dictionary, ignore_types=False, ignore_attrs=False):
        """Check if the homomorphism is valid (preserves edges, 
        preserves types and attributes if requires)."""

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
                            "Invalid homomorphism: Connectivity is not preserved!"+\
                            " Was expecting an edge between %s and %s" %
                            (dictionary[s_edge[1]], dictionary[s_edge[0]]))
                else:
                    raise ValueError(
                        "Invalid homomorphism: Connectivity is not preserved!"+\
                        " Was expecting an edge between %s and %s" %
                        (dictionary[s_edge[0]], dictionary[s_edge[1]]))

        if not ignore_types:
            # check nodes match with types
            for s, t in dictionary.items():
                if (source.node[s].type_ != None) and (source.node[s].type_ != target.node[t].type_):
                    raise ValueError(
                        "Invalid homomorphism: Node types do not match (%s:%s and %s:%s)!" %
                        (s, str(source.node[s].type_), str(t), str(target.node[t].type_)))
                if not ignore_attrs:
                    # check sets of attributes of nodes (here homomorphism = set inclusion)
                    if not valid_attributes(source.node[s].attrs_, target.node[t]):
                        raise ValueError(
                            "Invalid homomorphism: Attributes of nodes source:'%s' and target:'%s' do not match!" %
                            (str(s), str(t)))

        if not ignore_attrs:
            # check sets of attributes of edges (homomorphism = set inclusion)
            for s_edge in source.edges():
                source_edge_attrs = source.get_edge(s_edge[0], s_edge[1])
                target_edge_attrs = target.get_edge(dictionary[s_edge[0]],
                                                    dictionary[s_edge[1]])
                if not is_subdict(source_edge_attrs, target_edge_attrs):
                    raise ValueError(
                        "Invalid homomorphism: Attributes of edges (%s)-(%s) and (%s)-(%s) do not match!" %
                        (s_edge[0], s_edge[1], dictionary[s_edge[0]],
                            dictionary[s_edge[1]]))
        return True

    @staticmethod
    def identity(A, B, ignore_types=False, ignore_attrs=False):
        """ Tries to create the identity homomorphism of A from A to B,
            fails if some nodes of A aren't found in B
        """
        dic = {}
        for n in A.nodes():
            if n in B.nodes():
                dic[n] = n
            else:
                raise ValueError(
                    "Node %s not found in the second graph" % n
                )
        return Homomorphism(A, B, dic, ignore_types, ignore_attrs)

    @staticmethod
    def compose(h1, h2):
        """ Returns h1.h2 : A -> C given h1 : B -> C and h2 : A -> B"""
        return Homomorphism(
            h2.source_,
            h1.target_,
            dict([(n, h1.mapping_[h2.mapping_[n]]) for n in h2.mapping_.keys()]),
        )


class TypingHomomorphism(Homomorphism):
    def __init__(self, source, target, dictionary):
        if TypingHomomorphism.is_valid_homomorphism(source, target, dictionary):
            self.source_ = source
            self.target_ = target
            self.mapping_ = dictionary
        else:
            raise ValueError("TypingHomomorphism is not valid!")

    @staticmethod
    def is_valid_homomorphism(source, target, dictionary, ignore_attrs=False):
        """Check if the homomorphism is valid (preserves edges and types)."""

        #check preserving of edges
        Homomorphism.is_valid_homomorphism(
            source,
            target,
            dictionary,
            ignore_types=True,
            ignore_attrs=ignore_attrs,
        )

        # check nodes match with types and sets of attributes
        for s, t in dictionary.items():
            if (source.node[s].type_ != None) and (source.node[s].type_ != t):
                raise ValueError(
                    "Invalid homomorphism: Node types do not form a chain (%s:%s and %s:%s)!" %
                    (s, str(source.node[s].type_), str(t), str(target.node[t].type_)))

            # pred = target.node[t].attributes_typing
            # if pred is not None and pred(source.node[s].attrs_):
            #     continue
        #     if not ignore_attrs:
        #         if not valid_attributes(source.node[s].attrs_, target.node[t]):
        #             raise ValueError(
        #                 "Invalid homomorphism: Attributes of nodes source:'%s' and target:'%s' does not match!" %
        #                 (str(s), str(t)))

        # # check edges attr matches
        # if not ignore_attrs:
        #     for s_edge in source.edges():
        #         source_edge_attrs = source.get_edge(s_edge[0], s_edge[1])
        #         target_edge_attrs = target.get_edge(dictionary[s_edge[0]],
        #                                             dictionary[s_edge[1]])
        #         if not is_subdict(source_edge_attrs, target_edge_attrs):
        #             raise ValueError(
        #                 "Invalid homomorphism: Attributes of edges (%s)-(%s) and (%s)-(%s) does not match!" %
        #                 (s_edge[0], s_edge[1], dictionary[s_edge[0]],
        #                     dictionary[s_edge[1]]))

        return True
