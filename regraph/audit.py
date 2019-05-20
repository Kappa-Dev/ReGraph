"""Collection of utils for audit trails."""
from abc import ABC, abstractmethod

import datetime
import uuid
import warnings

import networkx as nx


from regraph.exceptions import RevisionError, RevisionWarning
from regraph.rules import compose_rules, Rule, _create_merging_rule
from regraph.primitives import relabel_nodes


def _generate_new_commit_meta_data():
    time = datetime.datetime.now()
    commit_id = str(uuid.uuid1())
    return time, commit_id


class Versioning(ABC):
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
    commit(graph, rule, instance)
    branch(new_branch)
    switch_branch(branch)
    merge(branch1, branch2)
    """

    def __init__(self, init_branch="master"):
        """Initialize revision object."""
        self._current_branch = init_branch
        self._delatas = {}
        self._heads = {}
        self._commits = []
        self._revision_graph = nx.DiGraph()

    @abstractmethod
    def _updated_delta(self, delta, commit):
        """Abstract method for computing delta updated with the commit."""
        pass

    @abstractmethod
    def _compose_deltas(self, delta1, delta2):
        """Abstract method for composing deltas."""
        pass

    @abstractmethod
    def _invert_delta(self, delta1):
        """Abstract method for inverting deltas."""
        pass

    @abstractmethod
    def _merge_into_current_branch(self, delta):
        """Abstract method for merging a branch into the current one."""
        pass

    @abstractmethod
    def _create_identity_delta(self):
        """Abstract method for creating an identity-delta."""
        pass

    def _compose_delta_path(self, path):
        if length(path) > 1:
            result_delta = self._revision_graph.edge[
                path[0]][path[1]]["delta"]
            previous_commit = path[1]
            for current_commit in path[2:]:
                result_delta = self._compose_deltas(
                    result_delta,
                    self._revision_graph.edge[
                        current_commit][previous_commit]["delta"])
                previous_commit = current_commit
            return result_delta
        else:
            return self._create_identity_delta()

    def branches(self):
        """Return list of branches."""
        return [self._current_branch] + list(self._heads.keys())

    def current_branch(self):
        """Return the name of the current branch."""
        return self._current_branch

    def commit(self, delta, message=None, previous_commit=None):
        """Add a commit."""
        time, commit_id = _generate_new_commit_meta_data()

        if previous_commit is None:
            previous_commit = self._heads[self._current_branch]

        # Update heads and revision graph
        self._heads[self._current_branch] = commit_id
        self._revision_graph.add_node(
            commit_id, {
                "time": time,
                "message": message if message is not None else ""
            })
        self._revision_graph.add_edge(
            previous_commit, commit_id, {
                "delta": delta
            })

        for branch, branch_delta in self._delatas.items():
            self._deltas[branch] = self._compose_deltas(
                branch_delta, delta)

        return commit_id

    def switch_branch(self, branch):
        """Switch branches."""
        if branch not in self.branches():
            raise RevisionError(
                "Branch '{}' does not exist".format(branch))
        if branch == self._current_branch:
            warnings.warn("Already in branch '{}'".format(branch), RevisionWarning)

        # Set as the current branch
        previous_branch = self._current_branch
        self._current_branch = branch

        # Apply delta to the versioned object
        delta = self._delatas[branch]
        self._apply_delta(delta)
        self._deltas[previous_branch] = self._invert_delta(delta)

        # Recompute deltas
        for name, another_delta in self._delatas.items():
            if name != previous_branch:
                self._deltas[name] = self._compose_deltas(
                    self._deltas[previous_branch],
                    another_delta
                )

    def branch(self, new_branch, message=None):
        """Create a new branch with identity commit."""
        if new_branch in self.branches():
            raise RevisionError(
                "Branch '{}' already exists".format(new_branch))

        if message is None:
            message = "Created branch '{}'".format(new_branch)

        # Set this as a current branch
        previous_branch = self._current_branch
        previous_commit = self._heads[self._current_branch]
        self._current_branch = new_branch

        identity_delta = self._create_identity_delta()

        # Add a new delta
        self._deltas[previous_branch] = identity_delta

        # Create a new identity commit
        commit_id = self.commit(
            identity_delta,
            message=message,
            previous_commit=previous_commit)
        self._heads[self._current_branch] = commit_id

    def merge_with(self, branch, message=None):
        """Merge the current branch with the specified one."""
        if branch in self.branches():
            raise RevisionError(
                "Branch '{}' does not exist".format(branch))

        if message is None:
            message = "Merged branch '{}' into '{}'".format(
                branch, self._current_branch)

        delta = self._deltas[branch]
        delta_to_current, delta_to_branch = self._merge_into_current_branch(
            delta)

        commit_id = self.commit(delta_to_current, message=message)

        self._revision_graph.add_edge(
            self._heads[branch], commit_id,
            {
                "delta": delta_to_branch
            })
        del self._heads[branch]
        return commit_id

    def rollback(self, commit_id, message=None):
        """Rollback the current branch to a specific commit."""
        if commit_id not in self._revision_graph.nodes():
            raise RevisionError(
                "Commit '{}' does not exist in the revision graph".format(
                    commit_id))

        # Find paths from the last commit of the current branch
        # to the commit with id 'commit_id'
        try:
            shortest_path = list(nx.shortest_path(
                self._revision_graph, commit_id, self._heads[self._current_branch]))
        except nx.NetworkXNoPath:
            raise RevisionError(
                "Branch '{}' does not contain a path to the commit '{}'".format(
                    self._current_branch, commit_id))

        if message is None:
            message = "Rollback to commit '{}'".format(commit_id)

        # Generate a big rollback commit
        rollback_commit = self._compose_deltas(shortest_path)

        # Update the revision graph structure and deltas
        head_paths = {}
        for h in self._heads.values():
            head_paths[h] = list(nx.all_simple_paths(
                self._revision_graph, commit_id, h))

        # All paths to the heads originating from the commit to
        # which we rollaback are removed
        for paths in head_paths.values():
            for p in paths:
                s = p[0]
                for i in range(1, len(p)):
                    t = p[i]
                    if (s, t) in self._revision_graph.edges():
                        self._revision_graph.remove_edge(s, t)
                    s = t

        # Cleanup disconnected commits and update heads
        new_heads = {}
        for node in self._revision_graph.nodes():
            preds = self._revision_graph.predecessors(node)
            sucs = self._revision_graph.successors(node)
            if len(sucs) == 0:
                if len(preds) == 0:
                    branch_name = self._revision_graph.node[node]["branch"]
                    self._revision_graph.remove_node(node)
                    if branch_name in self._heads:
                        print("Removed the head of ", branch_name)
                        del self._heads[branch_name]
                elif node not in self._heads.values():
                    # add a new head
                    branch_name = self._revision_graph.node[node]["branch"]
                    new_heads[branch_name] = node
                    print("Added the head of ", branch_name)

        # Recompute deltas
        new_current_branch = self._revision_graph.node[commit_id]["branch"]
        self._current_branch = new_current_branch
        self._heads[self._current_branch] = commit_id

        # Update deltas of the preserved heads
        for h in self._heads:
            self._deltas[h] = self._compose_deltas(
                self._invert_delta(rollback_commit),
                self._deltas[h])

        # Compute deltas of the new heads
        for head, merge_commit in new_heads.items():
            pred_commits = self._revision_graph.predecessors(
                merge_commit)
            for p in pred_commits:
                branch = self._revision_graph.node[p]["branch"]
                self._head[branch] = p
                self._deltas[branch] = self._compose_deltas(
                    h,
                    self._invert_delta(
                        self._revision_graph.edge[p][merge_commit]["delta"]))


        # Apply the rollback commit generated before
        pass


class VersionedGraph(Versioning):
    """Class for versioned ."""

    def __init__(self, graph, init_branch="master"):
        """Initialize versioned graph object."""
        self.graph = graph
        super().__init__(init_branch)

    def _compose_deltas(self, delta1, delta2):
        """Computing composition of two deltas."""
        rule, lhs, rhs = compose_rules(
            delta1["rule"],
            delta1["lhs_instance"],
            delta1["rhs_instance"],
            delta2["rule"],
            delta2["lhs_instance"],
            delta2["rhs_instance"])
        return {
            "rule": rule,
            "lhs_instance": lhs,
            "rhs_instance": rhs
        }

    def _invert_delta(self, delta):
        """Reverse the direction of delta."""
        return {
            "rule": delta["rule"].get_inverted_rule(),
            "lhs_instance": delta["rhs_instance"],
            "rhs_instance": delta["lhs_instance"]
        }

    def _create_identity_delta(self):
        """Create an identity-delta."""
        rule = Rule.identity_rule()
        identity_delta = {
            "rule": rule,
            "lhs_instance": {},
            "rhs_instance": {}
        }
        return identity_delta

    def _apply_delta(self, delta, commit, relabel=True):
        """Apply delta to the current graph version."""
        _, rhs_instance = delta["rule"].apply_to(
            self.graph, delta["lhs_instance"], instance=True)

        if relabel:
            # Relabel nodes to correspond to the stored rhs
            new_labels = {
                v: delta["rhs_instance"][k]
                for k, v in rhs_instance.items()
            }
            relabel_nodes(self.graph, new_labels)
            rhs_instance = {
                k: new_labels[v]
                for k, v in rhs_instance.items()
            }
        return rhs_instance

    def _merge_into_current_branch(self, delta):
        """Merge branch with delta into the current branch."""
        current_to_merged_rule, ctm_instance = _create_merging_rule(
            delta["rule"], delta["lhs_instance"], delta["rhs_instance"])

        _, rhs_instance = current_to_merged_rule.apply_to(
            self.graph, ctm_instance)

        current_to_merged_delta = {
            "rule": current_to_merged_rule,
            "lhs_instance": ctm_instance,
            "rhs_instance": rhs_instance
        }

        other_to_merged_delta = self._compose_deltas(
            self._invert_delta(delta, current_to_merged_delta))

        return current_to_merged_delta, other_to_merged_delta

    def rewrite(self, rule, instance, message=None):
        """Rewrite the versioned graph and commit."""
        _, rhs_instance = rule.apply_to(
            self.graph, instance, inplace=True)
        return self.commit({
            "rule": rule,
            "lhs_instance": instance,
            "rhs_instance": rhs_instance,
            "message": message if message else ""
        })


# class VersionedHierarchy(Versioning);
#     pass
