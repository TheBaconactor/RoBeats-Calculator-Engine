from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...solver.scoring.exact_rescore import evaluate_force_greats_exact, score_stats_exact
from .fg_config import extract_fg_config, has_valid_fg_config
from .persistence_payload import normalize_force_payload


def _to_int(value: Any, *, field: str) -> int:
    try:
        return int(value or 0)
    except Exception as exc:
        raise ValueError(f"Invalid integer for authoritative persistence field {field!r}: {value!r}") from exc


def _config_counts(config: Mapping[str, Any]) -> list[int]:
    pairs: list[tuple[int, int]] = []
    for key, value in dict(config or {}).items():
        if not isinstance(key, str) or not key.startswith("NonFever"):
            continue
        try:
            idx = int(key.replace("NonFever", "")) - 1
        except Exception as exc:
            raise ValueError(f"Invalid ForceGreats section key {key!r}.") from exc
        pairs.append((idx, max(0, _to_int(value, field=key))))
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
    out["score"] = int(score_stats_exact(stats, calc_song, ref_arrays))


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


def assert_authoritative_fg_entry(
    entry: Mapping[str, Any],
    *,
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> None:
    base_stats = _details_stats(entry)
    if base_stats:
        expected_score = int(score_stats_exact(base_stats, calc_song, ref_arrays))
        actual_score = _to_int(entry.get("score"), field="score")
        if actual_score != expected_score:
            raise AssertionError(
                "Persistence base score is not authoritative "
                f"(expected={expected_score}, entry={actual_score})."
            )

    force_obj = entry.get("force")
    if not (isinstance(force_obj, dict) and has_valid_fg_config(force_obj)):
        return

    stats = _force_stats(force_obj)
    expected_base = int(score_stats_exact(stats, calc_song, ref_arrays))
    config = extract_fg_config(force_obj)
    counts = _config_counts(config)
    fg_eval = evaluate_force_greats_exact(stats, calc_song, ref_arrays, counts)
    if not isinstance(fg_eval, dict):
        raise AssertionError("Authoritative FG assertion could not replay ForceGreats.")
    expected_fg = int(fg_eval.get("final_score", 0) or 0)

    actual_base = _to_int(entry.get("fg_base_score"), field="fg_base_score")
    actual_fg = _to_int(entry.get("fg_score"), field="fg_score")
    force_base = _to_int(force_obj.get("BaseScore"), field="force.BaseScore")
    force_score = _to_int(force_obj.get("Score"), field="force.Score")
    fg_meta = force_obj.get("ForceGreats")
    meta_final = _to_int((fg_meta or {}).get("final_score"), field="force.ForceGreats.final_score")

    if actual_base != expected_base or force_base != expected_base:
        raise AssertionError(
            "FG persistence base score is not authoritative "
            f"(expected={expected_base}, entry={actual_base}, force={force_base})."
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
        assert_authoritative_fg_entry(out, calc_song=calc_song, ref_arrays=ref_arrays)
        return out

    force_normalized = normalize_force_payload(force_obj)
    stats = _force_stats(force_normalized)
    fg_base_score = int(score_stats_exact(stats, calc_song, ref_arrays))
    config = extract_fg_config(force_normalized)
    counts = _config_counts(config)
    if not counts or sum(int(value) for value in counts) <= 0:
        out["force"] = None
        out["fg_score"] = 0
        out.pop("fg_base_score", None)
        assert_authoritative_fg_entry(out, calc_song=calc_song, ref_arrays=ref_arrays)
        return out

    fg_eval = evaluate_force_greats_exact(stats, calc_song, ref_arrays, counts)
    if not isinstance(fg_eval, dict):
        raise ValueError("Authoritative FG persistence could not replay ForceGreats.")
    fg_score = int(fg_eval.get("final_score", 0) or 0)
    if fg_score <= fg_base_score:
        out["force"] = None
        out["fg_score"] = 0
        out.pop("fg_base_score", None)
        assert_authoritative_fg_entry(out, calc_song=calc_song, ref_arrays=ref_arrays)
        return out

    out["fg_base_score"] = int(fg_base_score)
    out["fg_score"] = int(fg_score)
    out["force"] = _canonical_force_payload(
        force_normalized,
        fg_base_score=int(fg_base_score),
        fg_score=int(fg_score),
        fg_eval=fg_eval,
    )
    assert_authoritative_fg_entry(out, calc_song=calc_song, ref_arrays=ref_arrays)
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
