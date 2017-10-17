"""Possibly Set."""

from regraph.exceptions import ReGraphError
from sympy.sets.sets import (Set, FiniteSet, UniversalSet, EmptySet,
                             Intersection, Union, Complement)
from sympy import sympify
import copy
import math


class AtSetError(ReGraphError):
    """Type error in Attribute sets."""


class AtSet():
    """Possibly infinite Sets used for node attributes."""

    def __init__(self, num_set, str_set):
        self.num_set = num_set
        self.str_set = str_set

    def __bool__(self):
        return bool(self.num_set) or bool(self.str_set)

    def __repr__(self):
        return str(self.to_json())

    def __iter__(self):
        for elm in self.num_set:
            yield elm
        for elm in self.str_set:
            yield elm

    def __len__(self):
        return len(self.num_set) + len(self.str_set)

    def union(self, other):
        """union with other (returns new set)"""
        return AtSet(self.num_set.union(other.num_set),
                     self.str_set.union(other.str_set))

    def intersect(self, other):
        """intersection with other (returns new set)"""
        return AtSet(self.num_set.intersect(other.num_set),
                     self.str_set.intersect(other.str_set))

    def complement(self, other):
        """complement relative to other (other-self) (returns new set)"""
        return AtSet(self.num_set.complement(other.num_set),
                     self.str_set.complement(other.str_set))

    def issubset(self, other):
        """test if self is a subset of other"""
        return self.num_set.issubset(other.num_set) and\
            self.str_set.issubset(other.str_set)

    def to_json(self):
        """ convert set to JSON like dictionnary """
        return {"numSet": self.num_set.to_json(),
                "strSet": self.str_set.to_json()}

    def __eq__(self, other):
        return self.issubset(other) and other.issubset(self)

    def __ge__(self, other):
        return other.issubset(self)

    def __gt__(self, other):
        return other.issubset(self) and not self.issubset(other)

    def __lt__(self, other):
        return self.issubset(other) and not other.issubset(self)

    __le__ = issubset

    @staticmethod
    def from_json(json_data):
        if "numSet" in json_data:
            if "pos_list" in json_data["numSet"]:
                num_set = AtFinSet.from_json(json_data["numSet"])
            elif "string" in json_data["numSet"]:
                num_set = AtSymSet.from_json(json_data["numSet"])
            else:
                num_set = AtEmptySet()
        else:
            num_set = AtEmptySet()
        if "strSet" in json_data:
            if "pos_list" in json_data["strSet"]:
                str_set = AtPosStringSet.from_json(
                    json_data["strSet"])
            elif "neg_list" in json_data["strSet"]:
                str_set = AtNegStringSet.from_json(
                    json_data["strSet"])
            else:
                str_set = AtEmptySet()
        else:
            str_set = AtEmptySet()

        return AtSet(num_set, str_set)


class AtFinSet():
    """Finite Set numerical values"""

    def __init__(self, at_set):
        # test that elements are numerical values
        # super(AtFinSet, self).__init__(*elements)
        self.at_set = at_set

    def __bool__(self):
        return bool(self.at_set)

    def __iter__(self):
        return iter(self.at_set)

    def __len__(self):
        return len(self.at_set)

    def issubset(self, other):
        if isinstance(other, AtEmptySet):
            return False
        elif isinstance(other, AtUnivSet):
            return True
        elif isinstance(other, AtSymSet):
            return FiniteSet(*list(self.at_set)).issubset(other.at_set)
        elif isinstance(other, AtFinSet):
            return self.at_set.issubset(other.at_set)
        # elif isinstance(other, AtPosStringSet):
        #     return False
        # elif isinstance(other, AtNegStringSet):
        #     return False
        else:
            raise AtSetError("""Finite Numerical set state cannot
                               test subset with type {}"""
                             .format(type(other)))

    def intersect(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return copy.deepcopy(self)
        elif isinstance(other, AtSymSet):
            # return convert(AtSymSet(FiniteSet(*list(self.at_set))
            #                .intersect(other.at_set)) )
            return convert(AtSymSet(Intersection(FiniteSet(*list(self.at_set)),
                                                 other.at_set,
                                                 evaluate=True)))
        elif isinstance(other, AtFinSet):
            return convert(AtFinSet(self.at_set.intersection(other.at_set)))
        elif isinstance(other, AtPosStringSet):
            return AtEmptySet()
        elif isinstance(other, AtNegStringSet):
            return AtEmptySet()
        else:
            raise AtSetError("Finite Numerical set cannot intersect with type {}"
                             .format(type(other)))

    def union(self, other):
        if isinstance(other, AtEmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, AtUnivSet):
            return AtUnivSet()
        elif isinstance(other, AtSymSet):
            # return
            # convert(AtSymSet(FiniteSet(*list(self.at_set)).union(other.at_set)))
            return convert(AtSymSet(reduce_union(Union(FiniteSet(*list(self.at_set)),
                                                       other.at_set,
                                                       evaluate=True))))
        elif isinstance(other, AtFinSet):
            return AtFinSet(self.at_set.union(other.at_set))
        # elif isinstance(other, AtPosStringSet):
        # elif isinstance(other, AtNegStringSet):
        else:
            raise AtSetError("Finite Numerical set cannot union with type {}"
                             .format(type(other)))

    def complement(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return AtSymSet(FiniteSet(*list(self.at_set))
                            .complement(UniversalSet()))
        elif isinstance(other, AtSymSet):
            # return convert(AtSymSet(FiniteSet(*list(self.at_set))
            #                         .complement(other.at_set)))
            # return convert(AtSymSet(Complement(FiniteSet(*list(self.at_set)),
            #                         other.at_set,
            #                         evaluate=True)) )
            return convert(AtSymSet(Complement(
                                    other.at_set,
                                    FiniteSet(*list(self.at_set)),
                                    evaluate=True)))
        elif isinstance(other, AtFinSet):
            return convert(AtFinSet(other.at_set - self.at_set))
        # elif isinstance(other, AtPosStringSet):
        #     return copy.deepcopy(other)
        # elif isinstance(other, AtNegStringSet):
        #     return copy.deepcopy(other)
        else:
            raise AtSetError("Finite Numerical set cannot complement with type {}"
                             .format(type(other)))

    def to_json(self):
        return {"pos_list": [str(el) for el in self.at_set]}

    @staticmethod
    def from_json(json_data):
        if not isinstance(json_data["pos_list"], list):
            raise ReGraphError("pos_list field should contain a list")
        for el in json_data["pos_list"]:
            if not test_number(el):
                raise ReGraphError("{} is not a number".format(el))
        return convert(AtFinSet(set(sympify(json_data["pos_list"]))))


class AtSymSet():
    """Symbolic numerical sets"""

    def __init__(self, at_set):
        self.at_set = at_set

    def __bool__(self):
        return bool(self.at_set)

    def __len__(self):
        return math.inf

    def issubset(self, other):
        if isinstance(other, AtEmptySet):
            return False
        elif isinstance(other, AtUnivSet):
            return True
        elif isinstance(other, AtSymSet):
            return self.at_set.issubset(other.at_set)
        elif isinstance(other, AtFinSet):
            return self.at_set.issubset(FiniteSet(*list(other.at_set)))
        # elif isinstance(other, AtPosStringSet):
        #     return False
        # elif isinstance(other, AtNegStringSet):
        #     return False
        else:
            raise AtSetError("Symbolic set cannot test subset with type {}"
                             .format(type(other)))

    def intersect(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return copy.deepcopy(self)
        elif isinstance(other, AtSymSet):
            return convert(AtSymSet(Intersection(self.at_set, other.at_set,
                                                 evaluate=True)))
        elif isinstance(other, AtFinSet):
            return convert(AtSymSet(Intersection(
                self.at_set,
                FiniteSet(*list(other.at_set)),
                evaluate=True)))
        # elif isinstance(other, AtPosStringSet):
        #     return AtEmptySet()
        # elif isinstance(other, AtNegStringSet):
        #     return AtEmptySet()
        else:
            raise AtSetError("Symbolic set cannot intersect with type {}"
                             .format(type(other)))

    def union(self, other):
        if isinstance(other, AtEmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, AtUnivSet):
            return AtUnivSet()
        elif isinstance(other, AtSymSet):
            return convert(AtSymSet(reduce_union(Union(self.at_set,
                                                       other.at_set,
                                                       evaluate=True))))
        elif isinstance(other, AtFinSet):
            return convert(AtSymSet(reduce_union(Union(
                self.at_set,
                FiniteSet(*list(other.at_set)),
                evaluate=True))))
        else:
            raise AtSetError("Symbolic set cannot union with type {}"
                             .format(type(other)))

    def complement(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return convert(AtSymSet(Complement(UniversalSet(),
                                               self.at_set,
                                               evaluate=True)))
        elif isinstance(other, AtSymSet):
            return convert(AtSymSet(Complement(other.at_set,
                                               self.at_set,
                                               evaluate=True)))
        elif isinstance(other, AtFinSet):
            return convert(AtSymSet(Complement(FiniteSet(*list(other.at_set)),
                                               self.at_set,
                                               evaluate=True)))
        # elif isinstance(other, AtPosStringSet):
        #     return copy.deepcopy(other)
        # elif isinstance(other, AtNegStringSet):
        #     return copy.deepcopy(other)
        else:
            raise AtSetError("Symbolic set cannot complement with type {}"
                             .format(type(other)))

    def to_json(self):
        return {"string": str(self.at_set)}

    @staticmethod
    def from_json(json_data):
        if not isinstance(json_data["string"], str):
            raise ReGraphError("string field should contain a string")
        symset = safe_sympify(json_data["string"])
        return convert(AtSymSet(symset))


class AtPosStringSet():
    """Positive set of string."""

    def __init__(self, at_set):
        self.at_set = at_set

    def __bool__(self):
        return bool(self.at_set)

    def __len__(self):
        return len(self.at_set)

    def issubset(self, other):
        if isinstance(other, AtEmptySet):
            if not self.at_set:
                raise ValueError("set should not be empty")
            return False
        elif isinstance(other, AtUnivSet):
            return True
        elif isinstance(other, AtNegStringSet):
            return not other.at_set & self.at_set
        elif isinstance(other, AtPosStringSet):
            return self.at_set.issubset(other.at_set)
        # elif isinstance(other, AtSymSet):
        #     return False
        # elif isinstance(other, AtFinSet):
        #     return False
        else:
            raise AtSetError("Set of strings should not be be compared with type {}"
                             .format(type(other)))

    def intersect(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return copy.deepcopy(self)
        elif isinstance(other, AtNegStringSet):
            return convert(AtPosStringSet(self.at_set - other.at_set))
        elif isinstance(other, AtPosStringSet):
            return convert(AtPosStringSet(self.at_set & other.at_set))
        # elif isinstance(other, AtSymSet):
        #     return EmptySet()
        # elif isinstance(other, AtFinSet):
        #     return EmptySet()
        else:
            raise AtSetError("Set of strings cannot intersect with type {}"
                             .format(type(other)))

    def union(self, other):
        if isinstance(other, AtEmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, AtUnivSet):
            return AtUnivSet()
        elif isinstance(other, AtNegStringSet):
            return convert(AtNegStringSet(other.at_set - self.at_set))
        elif isinstance(other, AtPosStringSet):
            return AtPosStringSet(self.at_set | other.at_set)
        else:
            raise AtSetError("Set of strings cannot union with type {}"
                             .format(type(other)))

    def complement(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return AtNegStringSet(self.at_set)
        elif isinstance(other, AtNegStringSet):
            return AtNegStringSet(other.at_set | self.at_set)
        elif isinstance(other, AtPosStringSet):
            return convert(AtPosStringSet(other.at_set - self.at_set))
        else:
            raise AtSetError("Set of strings cannot complement with type {}"
                             .format(type(other)))

    def to_json(self):
        return {"pos_list": list(self.at_set)}

    def __iter__(self):
        return iter(self.at_set)

    @staticmethod
    def from_json(json_data):
        if not isinstance(json_data["pos_list"], list):
            raise ReGraphError("pos_list field should contain a list")
        for el in json_data["pos_list"]:
            if test_number(el):
                raise ReGraphError("{} is a number".format(el))
        return convert(AtPosStringSet(set(json_data["pos_list"])))


class AtNegStringSet():

    def __init__(self, at_set):
        self.at_set = at_set

    def __bool__(self):
        return True

    def __len__(self):
        return math.inf

    def issubset(self, other):
        if isinstance(other, AtEmptySet):
            return False
        elif isinstance(other, AtUnivSet):
            return True
        elif isinstance(other, AtNegStringSet):
            return other.at_set.issubset(self.at_set)
        elif isinstance(other, AtPosStringSet):
            return False
        else:
            raise AtSetError("Set of strings should not be be compared with type {}"
                             .format(type(other)))

    def intersect(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return copy.deepcopy(self)
        elif isinstance(other, AtNegStringSet):
            return convert(AtNegStringSet(self.at_set | other.at_set))
        elif isinstance(other, AtPosStringSet):
            return convert(AtPosStringSet(other.at_set - self.at_set))
        else:
            raise AtSetError("Set of strings cannot intersect with type {}"
                             .format(type(other)))

    def union(self, other):
        if isinstance(other, AtEmptySet):
            return copy.deepcopy(self)
        elif isinstance(other, AtUnivSet):
            return AtUnivSet()
        elif isinstance(other, AtNegStringSet):
            return convert(AtNegStringSet(self.at_set & other.at_set))
        elif isinstance(other, AtPosStringSet):
            return convert(AtNegStringSet(self.at_set - other.at_set))
        else:
            raise AtSetError("Set of strings cannot union with type {}"
                             .format(type(other)))

    def complement(self, other):
        if isinstance(other, AtEmptySet):
            return AtEmptySet()
        elif isinstance(other, AtUnivSet):
            return AtPosStringSet(self.at_set)
        elif isinstance(other, AtNegStringSet):
            return convert(AtPosStringSet(self.at_set - other.at_set))
        elif isinstance(other, AtPosStringSet):
            return convert(AtPosStringSet(self.at_set & other.at_set))
        else:
            raise AtSetError("Set of strings cannot complement with type {}"
                             .format(type(other)))

    def to_json(self):
        return {"neg_list": list(self.at_set)}

    @staticmethod
    def from_json(json_data):
        if not isinstance(json_data["neg_list"], list):
            raise ReGraphError("neg_list field should contain a list")
        for el in json_data["neg_list"]:
            if test_number(el):
                raise ReGraphError("{} is a number".format(el))
        return convert(AtNegStringSet(set(json_data["neg_list"])))


class AtEmptySet():
    """The empty set."""

    def __init__(self):
        pass

    def __bool__(self):
        return False

    def __len__(self):
        return 0

    def issubset(self, other):
        return True

    def intersect(self, other):
        return AtEmptySet()

    def union(self, other):
        return copy.deepcopy(other)

    def complement(self, other):
        return copy.deepcopy(other)

    def to_json(self):
        return {"pos_list": []}

    def __iter__(self):
        return(self)

    def __next__(self):
        raise StopIteration


class AtUnivSet():
    """The Universal set."""

    def __init__(self):
        pass

    def __bool__(self):
        return True

    def __len__(self):
        return math.inf

    def issubset(self, other):
        if isinstance(other, AtUnivSet):
            return True
        elif isinstance(other, AtNegStringSet):
            return not other.at_set
        elif isinstance(other, AtSymSet):
            return UniversalSet().issubset(other.at_set)
        else:
            return False

    def intersect(self, other):
        return copy.deepcopy(other)

    def union(self, other):
        return AtUnivSet()

    def complement(self, other):
        return AtEmptySet()

    def to_json(self):
        # return {"string": "UniversalSet()"}
        return {"neg_list": []}


def convert(atset):
    """Convert sets to AtEmptySet or AtUniversalSets if possible"""
    if isinstance(atset, AtPosStringSet):
        if not atset.at_set:
            return AtEmptySet()
    elif isinstance(atset, AtNegStringSet):
        if not atset.at_set:
            return AtUnivSet()
    elif isinstance(atset, AtFinSet):
        if not atset.at_set:
            return AtEmptySet()
    elif isinstance(atset, AtSymSet):
        if not atset.at_set:
            return AtEmptySet()
        elif isinstance(atset.at_set, UniversalSet):
            return AtUnivSet()
        elif isinstance(atset.at_set, FiniteSet):
            return AtFinSet(set(atset.at_set))
    return atset


def reduce_union(sets):
    """sympy.set does not reduce complements in a union"""
    if isinstance(sets, Union):
        new_args = []
        for sset in sets._args:
            if not sset.is_Complement:
                new_args.append(sset)
            if sset.is_Complement:
                if len(sset.args) != 2:
                    raise ReGraphError("complement without 2 args")
                other_sets = [s for s in sets._args if s != sset]
                new_sset = Complement(sset.args[0],
                                      Complement(sset.args[1],
                                                 *other_sets,
                                                 evaluate=True),
                                      evaluate=True)
                new_args.append(new_sset)
        return Union(*new_args, evaluate=True)
    else:
        return sets


def empty_set():
    return AtSet(EmptySet(), EmptySet())


def univ_set():
    return AtSet(AtUnivSet(), AtUnivSet())


def test_number(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _check_input(value):
    pass


def safe_sympify(value):
    _check_input(value)
    return sympify(value)


def to_atset(value):
    """Convert an attribute value to AtSet object."""
    if isinstance(value, str):
        symset = safe_sympify(value)
        # check that there are no symbols
        return AtSet(convert(AtSymSet(symset)), AtEmptySet())
    elif isinstance(value, list) or isinstance(value, set):
        str_vals = []
        num_vals = []
        for val in value:
            if test_number(val):
                num_vals.append(val)
            else:
                str_vals.append(val)
        res = AtSet(convert(AtFinSet(set(sympify(num_vals)))),
                    convert(AtPosStringSet(set(str_vals))))
        return res
    elif isinstance(value, dict):
        return AtSet.from_json(value)
    elif isinstance(value, AtSet):
        return value
    else:
        raise ReGraphError("value {} should be a list, set, string or dict "
                           "representation of AtSet".format(value))
