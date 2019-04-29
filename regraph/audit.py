"""Collection of utils for audit trails."""
import warnings
from regraph.exceptions import RevisionError, RevisionWarning


class RevisionTree(object):
    """Class for version control.

    Attributes
    ----------
    _current_branch
        Name of the current branch
    _deltas : dict
        Dictionary with delta's to all other branches

    Methods
    -------
    branches()
    current_branch()
    switch_branch(branch)
    commit(graph, rule, instance)
    branch(new_branch)
    merge(branch1, branch2)
    """

    def __init__(self):
        """Initialize revision object."""
        self._current_branch
        self._delatas = {

        }

    def branches(self):
        """Return list of branches."""
        return [self._current_branch] + list(self._delatas.keys())

    def current_branch(self):
        """Return the name of the current branch."""
        return self._current_branch

    def switch_branch(self, branch):
        """Switch branches."""
        if branch not in self.branches():
            raise RevisionError(
                "Branch '{}' does not exist".format(branch))
        if branch == self._current_branch:
            warnings.warn("Already in branch '{}'".format(branch), RevisionWarning)

        # Apply delta to the hierarchy
        delta = self._delatas[branch]

        # Recompute deltas

        self._current_branch = branch

    def commit(self, graph, rule, instance):
        pass

    def branch(self, new_branch):
        pass

    def merge(self, branch1, branch2):
        pass
