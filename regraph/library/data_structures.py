"""Define data structures used by graph rewriting tool."""


class TypedNode:
    """."""

    def __init__(self, n_type=None, attrs=None):
        self.type = n_type
        self.attrs = attrs
        return


class TypedDiGraph:
    """Define simple typed directed graph."""

    pass


class TypedGraph:
    """Define simple typed undirected graph."""

    pass


class Homomorphism:
    """Define homomorphism data structure."""

    def is_monic(self):
        """Check if the homomorphism is monic."""
        pass
