from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...core.utils import require_int

from ...solver.scoring.exact_rescore import (
    score_force_greats_response_surface_exact,
    score_stats_exact_with_timeline_trace,
    score_stats_fixed_timing_exact,
)
from .fg_config import extract_fg_config, has_valid_fg_config, require_response_surface
from .persistence_payload import normalize_force_payload


def _config_counts(config: Mapping[str, Any]) -> list[int]:
    pairs: list[tuple[int, int]] = []
    for key, value in dict(config or {}).items():
        if not isinstance(key, str) or not key.startswith("NonFever"):
            continue
        try:
            idx = int(key.replace("NonFever", "")) - 1
        except Exception as exc:
            raise ValueError(f"Invalid ForceGreats section key {key!r}.") from exc
        pairs.append((idx, max(0, require_int(value, field=key))))
    if not pairs:
        return []

    pairs.sort(key=lambda pair: pair[0])
    max_idx = pairs[-1][0]
    counts = [0] * (max_idx + 1)
    for idx, value in pairs:
        if idx < 0:
            raise ValueError(f"Invalid ForceGreats section index {idx + 1}.")
        counts[idx] = int(value)
    return counts


def _force_stats(force_obj: Mapping[str, Any]) -> dict[str, Any]:
    payload = force_obj.get("details") if isinstance(force_obj.get("details"), dict) else force_obj
    normalized = normalize_force_payload(dict(payload))
    stats = normalized.get("Stats")
    if not isinstance(stats, dict) or not stats:
        raise ValueError("Authoritative FG persistence requires replayable force Stats.")
    return {str(key): int(value) for key, value in stats.items()}


def _details_stats(entry: Mapping[str, Any]) -> dict[str, Any]:
    details = entry.get("details")
    if not isinstance(details, dict):
        return {}
    stats = details.get("Stats")
    if not isinstance(stats, dict) or not stats:
        return {}
    return {str(key): int(value) for key, value in stats.items()}


def _canonicalize_base_score(
    out: dict[str, Any],
    *,
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> None:
    stats = _details_stats(out)
    if not stats:
        return
    metadata = calc_song.get("metadata", {}) if isinstance(calc_song, Mapping) else {}
    timing_mode = str((metadata or {}).get("TimingEnvelopeMode", "") or "").strip().lower()
    if timing_mode == "zero_ms":
        out["score"] = int(score_stats_fixed_timing_exact(stats, calc_song, ref_arrays))
        details = out.get("details")
        if isinstance(details, dict) and "TimelineFrontier" in details:
            details_out = dict(details)
            details_out.pop("TimelineFrontier", None)
            out["details"] = details_out
        return
    replay = score_stats_exact_with_timeline_trace(stats, calc_song, ref_arrays)
    out["score"] = int(replay.get("score", 0) or 0)
    details = out.get("details")
    if isinstance(details, dict):
        timeline = replay.get("TimelineFrontier")
        if isinstance(timeline, dict):
            details_out = dict(details)
            details_out["TimelineFrontier"] = dict(timeline)
            out["details"] = details_out


def _canonical_force_payload(
    force_obj: Mapping[str, Any],
    *,
    fg_base_score: int,
    fg_score: int,
    fg_eval: Mapping[str, Any],
) -> dict[str, Any]:
    out = normalize_force_payload(dict(force_obj))
    out["BaseScore"] = int(fg_base_score)
    out["Score"] = int(fg_score)
    out["score"] = int(fg_score)

    fg_meta = dict(out.get("ForceGreats") or {})
    config_dict = fg_eval.get("config_dict")
    if isinstance(config_dict, dict) and config_dict:
        fg_meta["config"] = dict(config_dict)
    fg_meta["final_score"] = int(fg_score)
    out["ForceGreats"] = fg_meta

    config_counts = fg_eval.get("config_counts")
    if isinstance(config_counts, list) and config_counts:
        out["forced_counts"] = [int(value) for value in config_counts]
    return out


def _source_paired_base_score(entry: Mapping[str, Any], force_obj: Mapping[str, Any]) -> int:
    for value in (
        entry.get("fg_base_score"),
        force_obj.get("BaseScore"),
        force_obj.get("base_score"),
    ):
        try:
            score = int(value or 0)
        except (TypeError, ValueError):
            score = 0
        if score > 0:
            return int(score)
    return 0


def _replay_force_payload(
    force_obj: Mapping[str, Any],
    *,
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    counts: list[int],
) -> dict[str, Any]:
    surface = require_response_surface(force_obj)
    final_score = score_force_greats_response_surface_exact(stats, calc_song, ref_arrays, surface)
    if final_score is None:
        raise ValueError("Authoritative FG response surface replay failed.")
    return {
        "final_score": int(final_score),
        "config_counts": [int(value) for value in counts],
        "config_dict": extract_fg_config(force_obj),
    }


def _assert_canonical_fg_invariants(entry: Mapping[str, Any], *, expected_fg: int | None) -> None:
    """Cross-field invariants over a just-canonicalized entry.

    ``expected_fg`` is the exact surface replay the canonicalizer computed ONCE for this
    entry -- the check validates every independently-written field against it instead of
    re-deriving the same pure function from the same inputs (recompute-and-compare-to-self
    protects nothing). ``None`` asserts the FG-less shape.
    """
    force_obj = entry.get("force")
    if force_obj is None:
        if int(entry.get("fg_score", 0) or 0) != 0:
            raise AssertionError("FG-less persistence entry must carry fg_score=0.")
        return
    if expected_fg is None:
        raise AssertionError("Canonical FG entry requires the once-computed exact surface score.")
    expected_fg = int(expected_fg)

    actual_base = require_int(entry.get("fg_base_score"), field="fg_base_score")
    actual_fg = require_int(entry.get("fg_score"), field="fg_score")
    force_base = require_int(force_obj.get("BaseScore"), field="force.BaseScore")
    force_score = require_int(force_obj.get("Score"), field="force.Score")
    fg_meta = force_obj.get("ForceGreats")
    meta_final = require_int((fg_meta or {}).get("final_score"), field="force.ForceGreats.final_score")

    if actual_base <= 0 or force_base != actual_base:
        raise AssertionError(
            "FG persistence base score is not paired-source authoritative "
            f"(entry={actual_base}, force={force_base})."
        )
    if expected_fg <= actual_base:
        raise AssertionError(
            "FG persistence entry does not beat its paired base "
            f"(fg={expected_fg}, base={actual_base})."
        )
    if actual_fg != expected_fg or force_score != expected_fg or meta_final != expected_fg:
        raise AssertionError(
            "FG persistence final score is not authoritative "
            f"(expected={expected_fg}, entry={actual_fg}, force={force_score}, meta={meta_final})."
        )


def canonicalize_authoritative_fg_entry(
    entry: Mapping[str, Any],
    *,
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> dict[str, Any]:
    out = dict(entry)
    _canonicalize_base_score(out, calc_song=calc_song, ref_arrays=ref_arrays)

    force_obj = out.get("force")
    if not (isinstance(force_obj, dict) and has_valid_fg_config(force_obj)):
        out["force"] = None
        out["fg_score"] = 0
        out.pop("fg_base_score", None)
        _assert_canonical_fg_invariants(out, expected_fg=None)
        return out

    force_normalized = normalize_force_payload(force_obj)
    stats = _force_stats(force_normalized)
    fg_base_score = _source_paired_base_score(out, force_normalized)
    if fg_base_score <= 0:
        raise ValueError("Authoritative FG persistence is missing paired source base score.")
    config = extract_fg_config(force_normalized)
    counts = _config_counts(config)
    if not counts or sum(int(value) for value in counts) <= 0:
        out["force"] = None
        out["fg_score"] = 0
        out.pop("fg_base_score", None)
        _assert_canonical_fg_invariants(out, expected_fg=None)
        return out

    fg_eval = _replay_force_payload(
        force_normalized,
        stats=stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        counts=counts,
    )
    fg_score = int(fg_eval.get("final_score", 0) or 0)
    if fg_score <= fg_base_score:
        out["force"] = None
        out["fg_score"] = 0
        out.pop("fg_base_score", None)
        _assert_canonical_fg_invariants(out, expected_fg=None)
        return out

    out["fg_base_score"] = int(fg_base_score)
    out["fg_score"] = int(fg_score)
    out["force"] = _canonical_force_payload(
        force_normalized,
        fg_base_score=int(fg_base_score),
        fg_score=int(fg_score),
        fg_eval=fg_eval,
    )
    _assert_canonical_fg_invariants(out, expected_fg=fg_score)
    return out


def canonicalize_authoritative_fg_entries(
    entries: list[dict[str, Any]],
    *,
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(calc_song, Mapping) or not calc_song:
        raise ValueError("calc_song is required for authoritative FG persistence canonicalization.")
    if not isinstance(ref_arrays, Mapping) or not ref_arrays:
        raise ValueError("ref_arrays are required for authoritative FG persistence canonicalization.")
    return [
        canonicalize_authoritative_fg_entry(entry, calc_song=calc_song, ref_arrays=ref_arrays)
        if isinstance(entry, dict)
        else entry
        for entry in list(entries or [])
    ]
