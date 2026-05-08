"""Single entrypoint for authoritative score replay verification."""

from __future__ import annotations

from typing import Any, Mapping

from .exact_rescore import score_stats_exact


def verify_score_replay(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    *,
    expected_score: int | None = None,
) -> int:
    """Replay-score from stored Stats. If *expected_score* given, assert parity."""
    replayed = score_stats_exact(stats, calc_song, ref_arrays)
    if expected_score is not None and replayed != expected_score:
        raise ValueError(
            f"Replay authority mismatch: replayed={replayed}, expected={expected_score}"
        )
    return replayed
