"""Collection of utils for Statement Results of queries."""


def execution_time(result):
    """Return the execution time of a query."""
    avail = result.summary().result_available_after
    cons = result.summary().result_consumed_after
    return avail + cons


def total_db_hits(result):
    """Return the # of db hits of the query."""
    profile = result.summary().profile
    if profile is None:
        print("The query must be profiled to access the # of hits.")
    else:
        return total_db_hits_profile(profile)


def total_db_hits_profile(profile):
    """Compute the total number of db hits of a query profile."""
    nb = 0
    for child in profile.children:
        nb += total_db_hits_profile(child)
    nb += profile.db_hits
    return nb


def total_rows(result):
    """Return the # of rows of the query."""
    profile = result.summary().profile
    if profile is None:
        print("The query must be profiled to access the # of rows.")
    else:
        return total_db_hits_profile(profile)


def total_rows_profile(profile):
    """Compute the total number of rows of a query profile."""
    nb = 0
    for child in profile.children:
        nb += total_rows_profile(child)
    nb += profile.rows
    return nb


def total_cache_hits(result):
    """Return the # of cache hits of the query."""
    profile = result.summary().profile
    if profile is None:
        print("The query must be profiled to access the # of hits.")
    else:
        return total_cache_hits_profile(profile)


def total_cache_hits_profile(profile):
    """Compute the total number of cache hits of a query profi"""
    nb = 0
    for child in profile.children:
        nb += total_cache_hits_profile(child)
    nb += profile.arguments['PageCacheHits']
    return nb


def single_value(result):
    """Return the value of the result."""
    return result.single().value()


def summary_counters(result):
    """Return a set of statistics from a Cypher statement execution."""
    return result.summary().counters
