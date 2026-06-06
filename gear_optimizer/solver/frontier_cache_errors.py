from __future__ import annotations


class MissingFrontierCacheError(ValueError):
    """A required prebuilt frontier cache artifact was absent at runtime.

    Startup cache prebuild owns building the candidate-independent timeline and FG
    response frontiers before scoring. A miss at runtime means the lookup key did not
    match a prebuilt artifact (for example, a consumer that prepared the song without
    the canonical timing envelope), not that the song is genuinely unscorable.

    Subclasses ``ValueError`` so existing callers that catch the historical
    ``ValueError`` keep working, while fail-loud consumers can catch this specific
    infrastructure-invariant violation and refuse to silently degrade -- such as
    persisting a base score while silently dropping the paired FG score.
    """
