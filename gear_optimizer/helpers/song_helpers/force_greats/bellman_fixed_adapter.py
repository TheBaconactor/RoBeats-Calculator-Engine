from __future__ import annotations

from math import ceil
from typing import Any

import numpy as np

from ....core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE, LOADOUTS_PER_SONG_LIMIT
from ....core.utils import safe_int
from ....solver.scoring.fg_policy import build_penalty_table_and_body, extract_fg_song_inputs, resolve_stat_factors
from ....solver.scoring.runtime_state import FORCE_GREATS_ALGO_VERSION
from ....solver.scoring.stats_scoring import evaluate_stats_score
from ....solver.scoring.stats_scoring import _force_greats_counts_to_dict
from ....solver.taichi_gem.force_greats import solve_force_greats_bellman_fixed_stats_gpu
from ..ga_entry_utils import materialize_entry_names
from . import cache_validation
from .entry_resolution import build_direct_ga_entry_items, entry_base_score
from .entry_utils import eval_data_from_entry, expected_selected_element
from .result_application import materialize_stats_from_payload


def _fixed_note_surfaces(stats: dict[str, Any], calc_song: dict[str, Any], ref_arrays: dict[str, Any]):
    song_inputs = extract_fg_song_inputs(calc_song)
    n = int(song_inputs.total_notes)
    if n <= 0:
        raise ValueError("ForceGreats Bellman requires a song with at least one note")

    factors = resolve_stat_factors(stats, ref_arrays)
    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    base_value = (primary_val * 2) + secondary_val + float(factors.pp_factor)

    base_f = np.float32(base_value)
    combo_mul_f = np.float32(factors.combo_mul)
    fever_mul_f = np.float32(factors.fever_mul)
    combo_val = int(base_f * combo_mul_f)
    fever_val = int(base_f * combo_mul_f * fever_mul_f)
    factor = (combo_mul_f - np.float32(1.0)) * base_f / np.float32(100.0)

    normal = np.full((n,), int(combo_val), dtype=np.int32)
    fever = np.full((n,), int(fever_val), dtype=np.int32)
    head_n = min(100, n)
    for i in range(head_n):
        current = base_f + (np.float32(i + 1) * factor)
        normal[i] = int(current)
        fever[i] = int(current * fever_mul_f)

    penalty_table, body_penalty, _combo_value = build_penalty_table_and_body(
        base_value=float(base_value),
        combo_mul=float(factors.combo_mul),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
    )
    penalty_prefix = np.zeros((n + 1,), dtype=np.int64)
    for i in range(n):
        penalty = int(penalty_table[i]) if i < len(penalty_table) else int(body_penalty)
        penalty_prefix[i + 1] = int(penalty_prefix[i]) + int(penalty)

    non_fever_cas = max(0.0, float(n - int(song_inputs.long_notes)) * float(FEVER_FILL_BASE_RATE))
    raw_fever_fill = float(non_fever_cas) * float(factors.fever_fill_rate)
    real_fever_time = (
        float(song_inputs.last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    ) * float(factors.fever_time_stat)

    return song_inputs, normal, fever, penalty_prefix, raw_fever_fill, ceil(raw_fever_fill), real_fever_time


def _force_payload_from_bellman(
    *,
    eval_data: dict[str, Any],
    stats: dict[str, Any],
    selected_element: str,
    base_score: int,
    fg_score: int,
    forced_counts: tuple[int, ...],
) -> dict[str, Any]:
    config = _force_greats_counts_to_dict(list(forced_counts), max(2, len(forced_counts)))
    payload = dict(eval_data)
    payload["Stats"] = dict(stats)
    payload["BaseScore"] = int(base_score)
    payload["Score"] = int(fg_score)
    payload["Selected Element"] = str(selected_element or payload.get("Selected Element", "") or "")
    payload["forced_counts"] = list(forced_counts)
    payload["ForceGreats"] = {
        "enabled": True,
        "mode": "bellman",
        "algo_version": int(FORCE_GREATS_ALGO_VERSION),
        "config": config,
        "final_score": int(fg_score),
    }
    return payload


def _int_gem(gems: dict[str, Any], *keys: str) -> int:
    for key in keys:
        if key in gems:
            return int(gems.get(key) or 0)
    return 0


def _fixed_stat_payloads_for_bellman(
    eval_data: dict[str, Any],
    *,
    selected: str,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    paired_base_score: int,
):
    stats = materialize_stats_from_payload(eval_data, selected_element=selected, mutate_payload=True)
    if not stats:
        raise ValueError("ForceGreats Bellman requires materialized fixed Stats for each candidate")
    yield eval_data, stats, int(paired_base_score)

    base_stats = eval_data.get("BaseStats")
    gems = eval_data.get("GemCounts")
    if not (isinstance(base_stats, dict) and base_stats and isinstance(gems, dict)):
        return

    overflow = _int_gem(gems, "Element", "Element Overflow", "ElementOverflow")
    if overflow <= 0:
        return

    ft0 = int(eval_data.get("FT", gems.get("Fever Time", 0)) or 0)
    ff0 = int(eval_data.get("FF", gems.get("Fever Fill", gems.get("Fever Fill Rate", 0))) or 0)
    seen = {(ft0, ff0, overflow)}
    for field in ("FT", "FF"):
        ft = ft0 + (1 if field == "FT" else 0)
        ff = ff0 + (1 if field == "FF" else 0)
        key = (int(ft), int(ff), int(overflow - 1))
        if key in seen:
            continue
        seen.add(key)
        candidate = dict(eval_data)
        next_gems = dict(gems)
        next_gems["Element"] = int(overflow - 1)
        candidate["GemCounts"] = next_gems
        candidate["FT"] = int(ft)
        candidate["FF"] = int(ff)
        candidate.pop("Stats", None)
        expanded_stats = materialize_stats_from_payload(candidate, selected_element=selected, mutate_payload=True)
        if not expanded_stats:
            raise ValueError("ForceGreats Bellman core expansion produced no materialized Stats")
        base_score = evaluate_stats_score(expanded_stats, calc_song, ref_arrays)
        candidate["BaseScore"] = int(base_score)
        candidate["Score"] = int(base_score)
        yield candidate, expanded_stats, int(base_score)


def process_force_greats_bellman_fixed_gpu(
    loadout_entries,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_candidates=None,
    ga_registry=None,
):
    direct_ga_items = build_direct_ga_entry_items(ga_candidates, ga_registry=ga_registry)
    base_items = list(loadout_entries.items()) if isinstance(loadout_entries, dict) else []
    if direct_ga_items:
        base_items = [(k, v) for k, v in base_items if not (isinstance(v, dict) and bool(v.get("_fg_direct_ga")))]
    entry_items = list(base_items) + list(direct_ga_items)

    variants: list[dict[str, Any]] = []
    for _key, entry in entry_items:
        if not isinstance(entry, dict):
            continue
        eval_data = eval_data_from_entry(entry, str(meta_primary_color or ""))
        if not isinstance(eval_data, dict) or not eval_data:
            continue
        selected = expected_selected_element(entry, str(meta_primary_color or ""))
        center_ft = int(eval_data.get("FT", 0) or 0)
        center_ff = int(eval_data.get("FF", 0) or 0)
        cached_force = entry.get("force")
        if cached_force and cache_validation.is_cached_force_valid_for_bellman(cached_force, selected, center_ft, center_ff):
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            fg_score = int(entry.get("fg_score", 0) or cached_force.get("Score", 0) or 0)
            base_score = int(cached_force.get("BaseScore", 0) or entry_base_score(entry))
            variants.append(
                {
                    "data": cached_force,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": int(base_score),
                    "base_score": int(base_score),
                    "fg_score": int(fg_score),
                    "_entry_ref": entry,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )
            continue

        paired_base_score = int(entry_base_score(entry))
        for fixed_eval_data, stats, fixed_base_score in _fixed_stat_payloads_for_bellman(
            eval_data,
            selected=selected,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            paired_base_score=paired_base_score,
        ):
            song_inputs, normal, fever, penalty_prefix, raw_fill, non_fever_base, real_fever_time = _fixed_note_surfaces(
                stats,
                calc_song,
                ref_arrays,
            )
            bellman = solve_force_greats_bellman_fixed_stats_gpu(
                timestamps=song_inputs.timestamps,
                great_candidate_timestamps=song_inputs.great_candidates,
                raw_fever_fill=float(raw_fill),
                non_fever_base=int(non_fever_base),
                real_fever_time=float(real_fever_time),
                normal_score_per_note=normal,
                fever_score_per_note=fever,
                forced_great_penalty_prefix=penalty_prefix,
                use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
            )
            if not bellman.best_forced_counts or max(int(v) for v in bellman.best_forced_counts) <= 0:
                continue
            if int(bellman.best_score) <= int(fixed_base_score):
                continue

            payload = _force_payload_from_bellman(
                eval_data=fixed_eval_data,
                stats=stats,
                selected_element=selected,
                base_score=int(fixed_base_score),
                fg_score=int(bellman.best_score),
                forced_counts=bellman.best_forced_counts,
            )
            if int(bellman.best_score) > safe_int(entry.get("fg_score", 0), 0):
                entry["force"] = payload
                entry["fg_score"] = int(bellman.best_score)
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            variants.append(
                {
                    "data": payload,
                    "gear": gear_names,
                    "minis": mini_names,
                    "score": int(payload["BaseScore"]),
                    "base_score": int(payload["BaseScore"]),
                    "fg_score": int(bellman.best_score),
                    "_entry_ref": entry,
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )

    variants.sort(key=lambda v: int(v.get("fg_score", 0) or 0), reverse=True)
    return variants[: int(LOADOUTS_PER_SONG_LIMIT)]
