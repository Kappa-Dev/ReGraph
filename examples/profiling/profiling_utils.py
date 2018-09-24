"""Utils for profiling Cypher queries."""


def total_db_hits(profile):
    """Compute the total number of db hits of a query profile."""
    nb = 0
    for child in profile.children:
        nb += total_db_hits(child)
    nb += profile.db_hits
    return nb
