"""TEMPORARY ``zero_ms``-only release shim -- DELETE ME once the timing model ships.

The input-aware Perfect-window timing model (and its startup timing frontier) is under
active development and is intentionally NOT built on the ``website-no-timing-frontiers``
release branch. Until it lands, ``zero_ms`` (every hit at its chart timestamp) is the ONLY
timing model this build can serve -- there is no other mode yet.

This module is the single, deliberately-obvious home for the temporary coercion that keeps
production answering while only ``zero_ms`` exists: a request that arrives stamped for another
(unbuilt) timing model is collapsed to ``zero_ms`` so the caller "still gets through" instead
of raising ``MissingFrontierCacheError`` for a frontier that was never built.

Cleanup is tracked in GitHub issue #125. ``git grep ZERO_MS_ONLY_TEMP`` (and
``git grep zero_ms_only_temp``) enumerates every site. When the real timing model is
integrated, delete this file, restore the original fail-loud / mode-selection behavior at each
marked site, and close the issue.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

logger = logging.getLogger(__name__)

# GitHub issue tracking removal of every ZERO_MS_ONLY_TEMP coercion in this build.
ZERO_MS_ONLY_TEMP_ISSUE = 125

# The only timing model the website-no-timing-frontiers branch can serve.
SERVICEABLE_TIMING_MODE = "zero_ms"

_warned_modes: set[str] = set()


def _warn_once(mode: str) -> None:
    """Log once per distinct non-serviceable mode so the coercion is visible, not silent."""
    if mode and mode != SERVICEABLE_TIMING_MODE and mode not in _warned_modes:
        _warned_modes.add(mode)
        logger.warning(
            "[ZERO_MS_ONLY_TEMP issue #%s] timing model %r is not built on this release branch; "
            "serving %r instead. Remove this shim when the timing model ships.",
            ZERO_MS_ONLY_TEMP_ISSUE,
            mode,
            SERVICEABLE_TIMING_MODE,
        )


def enforce_serviceable_timing_mode(mode: str) -> str:
    """Collapse any requested timing mode to the only one this release branch can serve.

    The website bridge already hardcodes ``zero_ms``, but the /optimize service must not depend on
    that: this is the single request-level gate so an internal caller that stamps ``perfect_window``
    still gets a serviceable answer (coerced to ``zero_ms``, warned once) instead of a frontier that
    was never built. Remove this call and restore mode selection when the timing model ships.
    """
    normalized = str(mode or "").strip().lower()
    if normalized == SERVICEABLE_TIMING_MODE:
        return SERVICEABLE_TIMING_MODE
    _warn_once(normalized)
    return SERVICEABLE_TIMING_MODE


def coerce_calc_song_to_zero_ms(calc_song: Mapping[str, Any]) -> dict:
    """Return a shallow copy of ``calc_song`` re-stamped ``TimingEnvelopeMode='zero_ms'``.

    The song keeps its chart timestamps -- the ``zero_ms`` hit timeline IS the chart timeline
    (``fg_timestamps == chart_timestamps`` for the Perfect-window preparation, and both equal
    the chart array when no custom offset is applied) -- so the fixed chart-time timeline
    payload can be built for a request that arrived stamped for another, unbuilt timing model.
    Does not mutate the caller's dict.
    """
    metadata = dict(calc_song.get("metadata", {}) or {})
    _warn_once(str(metadata.get("TimingEnvelopeMode", "") or "").strip().lower())
    metadata["TimingEnvelopeMode"] = SERVICEABLE_TIMING_MODE
    coerced = dict(calc_song)
    coerced["metadata"] = metadata
    return coerced
