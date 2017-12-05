"""ReGraph exceptions."""


class ReGraphException(Exception):
    """Base ReGraph exceptions class."""


class ReGraphError(ReGraphException):
    """Exception for errors in ReGraph."""


class GraphError(ReGraphException):
    """Class for errors in graph transformation with primitives."""


class ReGraphWarning(UserWarning):
    """Class for ReGraph warnings."""


class GraphAttrsWarning(ReGraphWarning):
    """Class for warnings about empty attrs dict."""


class ParsingError(ReGraphException):
    """Exceptions class for error in command parsing."""


class RuleError(ReGraphException):
    """Exceptions class for errors in rules."""


class FormulaError(ReGraphException):
    """Exceptions class for formulae."""


class InvalidHomomorphism(ReGraphException):
    """Exceptions class for invalid homomorphisms."""


class HierarchyError(ReGraphException):
    """Exceptions class for hierarchy handling."""


class TotalityWarning(ReGraphWarning):
    """Warning about the edge in the hierarchy becoming partial."""


class RewritingError(ReGraphException):
    """Exceptions class for errors in rewriting in a hierarchy."""


class AttributeSetError(ReGraphException):
    """Exceptions class for errors in attribute sets."""
