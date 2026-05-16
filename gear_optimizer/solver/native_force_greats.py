from __future__ import annotations

import importlib
from itertools import product
from types import SimpleNamespace
from typing import Any

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_PLATEAU_REP_STRIDE, GEM_SCALE_FEVER, TOTAL_GEM_BUDGET, TOTAL_ROWS
from gear_optimizer.core.utils import safe_float, safe_int
from gear_optimizer.helpers.song_helpers.force_greats.result_application import fp_targets_to_forced_counts
from gear_optimizer.solver.analytical_fg import create_scorer_from_calc_song
from gear_optimizer.solver.candidate_solver_cache import FgCandidateCacheShard, fg_context_digest
from gear_optimizer.solver.gpu_executor_types import GpuRequestType
from gear_optimizer.solver.scoring.force_greats import _compute_force_greats_timeline
from gear_optimizer.solver.scoring.stats_scoring import _force_greats_counts_to_dict
from gear_optimizer.solver.scoring.gpu_solver import FORCE_GREATS_ALGO_VERSION
from gear_optimizer.solver.scoring_core import lookup_reference_py


def _ftff_pairs(search_ranges: tuple[int, int, int, int] | None) -> list[tuple[int, int]]:
    if search_ranges is None:
        start_ft, end_ft = 0, int(TOTAL_GEM_BUDGET)
        start_ff, end_ff = 0, int(TOTAL_GEM_BUDGET)
    else:
        start_ft, end_ft, start_ff, end_ff = search_ranges
        start_ft = max(0, int(start_ft))
        end_ft = min(int(TOTAL_GEM_BUDGET), int(end_ft))
        start_ff = max(0, int(start_ff))
        end_ff = min(int(TOTAL_GEM_BUDGET), int(end_ff))

    out: list[tuple[int, int]] = []
    for ft_gems in range(start_ft, end_ft + 1):
        remaining = int(TOTAL_GEM_BUDGET) - int(ft_gems)
        if remaining < 0:
            break
        for ff_gems in range(start_ff, min(end_ff, remaining) + 1):
            out.append((int(ft_gems), int(ff_gems)))
    return out


def _counts_list(num_sections: int, non_fever_base: int) -> list[tuple[int, ...]]:
    n = int(num_sections)
    if n <= 0:
        return []
    cap_s0 = min(int(non_fever_base or 0), 50)
    cap_s1 = min(int(non_fever_base or 0), 25)
    cap_s2 = min(int(non_fever_base or 0), 15)
    if n == 1:
        return [(s0,) for s0 in range(cap_s0 + 1)]
    if n == 2:
        return [(s0, s1) for s0 in range(cap_s0 + 1) for s1 in range(cap_s1 + 1)]
    if n == 3:
        return [
            (s0, s1, s2)
            for s0 in range(cap_s0 + 1)
            for s1 in range(cap_s1 + 1)
            for s2 in range(cap_s2 + 1)
        ]
    cap = min(int(non_fever_base or 0), 5)
    return [tuple(int(v) for v in counts) for counts in product(range(cap + 1), repeat=n)]


def _section_summary(
    base_stats: dict[str, Any], calc_song: dict[str, Any], ref_arrays: dict[str, Any]
) -> tuple[int, int]:
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    great_candidates = song_data.get("fg_great_candidate_timestamps", timestamps)
    use_forced_great_timing = bool(song_data.get("fg_great_candidate_timestamps") is not None)
    total_notes = int(len(timestamps)) if timestamps is not None else 0
    if total_notes <= 0:
        return 0, 0

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    base_ts = song_data.get("timestamps", timestamps)
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    fever_fill_rate = lookup_reference_py(
        safe_int(base_stats.get("Fever Fill Rate", 0), 0),
        ref_arrays["Fever Fill Rate"],
        TOTAL_ROWS,
    )
    fever_time_stat = lookup_reference_py(
        safe_int(base_stats.get("Fever Time", 0), 0),
        ref_arrays["Fever Time"],
        TOTAL_ROWS,
    )
    _, _, _, non_fever_base, section_details = _compute_force_greats_timeline(
        timestamps,
        great_candidates,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        [],
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
        use_forced_great_timing=use_forced_great_timing,
    )
    return int(len(section_details)), int(non_fever_base)


def _local_gear_response_key(base_stats: dict[str, Any], *, primary: str, secondary: str) -> tuple[int, ...]:
    return (
        safe_int(base_stats.get("Perfect Points", 0), 0),
        safe_int(base_stats.get("Combo Multiplier", 0), 0),
        safe_int(base_stats.get("Fever Multiplier", 0), 0),
        safe_int(base_stats.get(primary, 0), 0),
        safe_int(base_stats.get(secondary, 0), 0),
        safe_int(base_stats.get("Fever Time", 0), 0),
        safe_int(base_stats.get("Fever Fill Rate", 0), 0),
    )


def _timing_response_key(base_stats: dict[str, Any]) -> tuple[int, int]:
    return (
        safe_int(base_stats.get("Fever Time", 0), 0),
        safe_int(base_stats.get("Fever Fill Rate", 0), 0),
    )


def _genome_stats_array(stats_rows: list[dict[str, Any]], *, primary: str, secondary: str) -> np.ndarray:
    genome_stats = np.zeros((len(stats_rows), 7), dtype=np.int16)
    for local_idx, base_stats in enumerate(stats_rows):
        genome_stats[local_idx, :] = np.asarray(
            _local_gear_response_key(base_stats, primary=primary, secondary=secondary),
            dtype=np.int16,
        )
    return genome_stats


def _search_ranges_for(
    center_ft: int | None, center_ff: int | None, search_radius: int | None
) -> tuple[int, int, int, int] | None:
    if center_ft is None or center_ff is None or search_radius is None:
        return None

    radius = int(search_radius)
    return (
        int(center_ft) - radius,
        int(center_ft) + radius,
        int(center_ff) - radius,
        int(center_ff) + radius,
    )


def _materialize_best(
    best: dict[str, Any] | None,
    *,
    counts: list[tuple[int, ...]],
    num_sections: int,
    non_fever_base: int,
    base_stats: dict[str, Any],
    fg_scorer: Any,
) -> dict[str, Any] | None:
    if not best:
        return None

    cfg_idx = safe_int(best.get("cfg_idx", -1), -1)
    raw_counts_obj = best.get("cfg_counts")
    if raw_counts_obj is not None:
        raw_counts = list(raw_counts_obj)[: int(num_sections)]
    else:
        raw_counts = list(counts[cfg_idx]) if 0 <= cfg_idx < len(counts) else []

    fp_targets: list[int] = []
    rep_flags: list[int] = []
    for raw_val in raw_counts:
        raw_i = safe_int(raw_val, 0)
        if raw_i < 0:
            raw_i = 0
        rep_flag = 0
        fp_target = int(raw_i)
        if raw_i >= int(FG_PLATEAU_REP_STRIDE):
            rep_flag = 1
            fp_target = int(raw_i % int(FG_PLATEAU_REP_STRIDE))
        fp_targets.append(int(fp_target))
        rep_flags.append(int(rep_flag))

    forced_counts = fp_targets_to_forced_counts(
        fp_targets,
        rep_flags,
        base_stats,
        safe_int(best.get("FT", 0), 0),
        safe_int(best.get("FF", 0), 0),
        fg_scorer,
    )
    return {
        "base_score": int(best.get("base_score", 0) or 0),
        "final_score": int(best.get("final_score", 0) or 0),
        "score_penalty": int(best.get("score_penalty", 0) or 0),
        "fill_penalty": int(best.get("fill_penalty", 0) or 0),
        "total_penalty": int(best.get("score_penalty", 0) or 0) + int(best.get("fill_penalty", 0) or 0),
        "num_non_fever_sections": int(num_sections),
        "penalty_analysis": {},
        "config_counts": list(forced_counts),
        "config_dict": _force_greats_counts_to_dict(forced_counts, max(2, len(forced_counts))),
        "fp_targets": list(fp_targets),
        "non_fever_base": int(non_fever_base),
        "gem_counts": best.get("gem_counts", {}) or {},
        "FT": int(best.get("FT", 0) or 0),
        "FF": int(best.get("FF", 0) or 0),
    }


def _materialize_raw_best_list(raw: dict[str, Any], n: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx in range(int(n)):
        out.append(
            {
                "final_score": int(raw["final_score"][idx]),
                "base_score": int(raw["base_score"][idx]),
                "cfg_idx": int(raw["cfg_idx"][idx]),
                "FT": int(raw["FT"][idx]),
                "FF": int(raw["FF"][idx]),
                "gem_counts": {
                    "Perfect Points": int(raw["g_pp"][idx]),
                    "Combo Multiplier": int(raw["g_cm"][idx]),
                    "Fever Multiplier": int(raw["g_fm"][idx]),
                    "Element": int(raw["g_ov"][idx]),
                },
                "score_penalty": int(raw["score_penalty"][idx]),
                "fill_penalty": int(raw["fill_penalty"][idx]),
                "cfg_counts": [int(x) for x in raw["cfg_counts"][idx]],
            }
        )
    return out


def solve_native_force_greats_gpu_batch(
    *,
    base_stats_list: list[dict[str, Any]],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_colors: list[str],
    center_fts: list[int | None],
    center_ffs: list[int | None],
    search_radius: int | None,
    gpu_client: Any | None = None,
) -> tuple[list[dict[str, Any] | None], dict[str, int]]:
    if not base_stats_list:
        return [], {
            "gpu_batches": 0,
            "groups": 0,
            "input_genomes": 0,
            "unique_genomes": 0,
            "deduped_genomes": 0,
            "dedupe_groups": 0,
            "section_summary_cache_hits": 0,
            "section_summary_cache_misses": 0,
            "candidate_cache_hits": 0,
            "candidate_cache_misses": 0,
            "candidate_cache_writes": 0,
        }

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    total_notes = int(len(timestamps)) if timestamps is not None else 0
    if total_notes <= 0:
        empty = [None for _ in base_stats_list]
        return empty, {
            "gpu_batches": 0,
            "groups": 0,
            "input_genomes": 0,
            "unique_genomes": 0,
            "deduped_genomes": 0,
            "dedupe_groups": 0,
            "section_summary_cache_hits": 0,
            "section_summary_cache_misses": 0,
            "candidate_cache_hits": 0,
            "candidate_cache_misses": 0,
            "candidate_cache_writes": 0,
        }

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    base_ts = song_data.get("timestamps", timestamps)
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    primary = str(metadata.get("Primary Color", "") or "")
    secondary = str(metadata.get("Secondary Color", "") or "")
    fg_scorer = create_scorer_from_calc_song(calc_song, ref_arrays)

    prepared_groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    results: list[dict[str, Any] | None] = [None for _ in base_stats_list]
    input_genomes = 0
    section_summary_cache: dict[tuple[int, int], tuple[int, int]] = {}
    section_summary_cache_hits = 0
    section_summary_cache_misses = 0

    for idx, base_stats in enumerate(base_stats_list):
        timing_key = _timing_response_key(base_stats)
        section_summary = section_summary_cache.get(timing_key)
        if section_summary is None:
            section_summary = _section_summary(base_stats, calc_song, ref_arrays)
            section_summary_cache[timing_key] = section_summary
            section_summary_cache_misses += 1
        else:
            section_summary_cache_hits += 1
        num_sections, non_fever_base = section_summary
        if num_sections <= 0:
            continue
        if num_sections > 20:
            raise RuntimeError(f"native FG requires <=20 non-fever sections, got {num_sections}")

        counts = _counts_list(num_sections, non_fever_base)
        if not counts:
            continue

        search_ranges = _search_ranges_for(center_fts[idx], center_ffs[idx], search_radius)
        pairs = _ftff_pairs(search_ranges)
        if not pairs:
            continue

        selected_color = str(selected_colors[idx] or "")
        key = (selected_color, int(num_sections), int(non_fever_base), search_ranges)
        group = prepared_groups.get(key)
        if group is None:
            group = {
                "indices": [],
                "stats": [],
                "counts": counts,
                "pairs": pairs,
                "num_sections": int(num_sections),
                "non_fever_base": int(non_fever_base),
                "selected_color": selected_color,
            }
            prepared_groups[key] = group

        group["indices"].append(int(idx))
        group["stats"].append(base_stats)
        input_genomes += 1

    if not prepared_groups:
        return results, {
            "gpu_batches": 0,
            "groups": 0,
            "input_genomes": int(input_genomes),
            "unique_genomes": 0,
            "deduped_genomes": 0,
            "dedupe_groups": 0,
            "section_summary_cache_hits": int(section_summary_cache_hits),
            "section_summary_cache_misses": int(section_summary_cache_misses),
            "candidate_cache_hits": 0,
            "candidate_cache_misses": 0,
            "candidate_cache_writes": 0,
        }

    try:
        gem_fields = importlib.import_module("gear_optimizer.solver.taichi_gem.fields")
        fg_fields = importlib.import_module("gear_optimizer.solver.taichi_gem.force_greats.fields")
    except ModuleNotFoundError as exc:
        if exc.name != "taichi" or gpu_client is None:
            raise
        gem_fields = SimpleNamespace(MAX_GENOMES=4096)
        fg_fields = SimpleNamespace(FG_MAX_FTFF=1024)
    if gpu_client is None:
        from gear_optimizer.solver.taichi_gem.force_greats.api import (
            fg_download_global_best,
            fg_reset_global_best,
            solve_force_greats_finder_gpu,
        )

    def _fg_solve_owner(*args: Any, **kwargs: Any) -> Any:
        if gpu_client is None:
            return solve_force_greats_finder_gpu(*args, **kwargs)
        return gpu_client.submit_solve_force_greats_finder(*args, **kwargs).future.result()

    def _fg_reset_owner(n_genomes: int, *, session_slot: int) -> None:
        if gpu_client is None:
            fg_reset_global_best(int(n_genomes), session_slot=int(session_slot))
            return
        gpu_client.submit(
            GpuRequestType.FG_RESET_GLOBAL_BEST,
            {"n_genomes": int(n_genomes), "song_slot": int(session_slot)},
        ).future.result()

    def _fg_download_owner(n_genomes: int, *, session_slot: int) -> Any:
        if gpu_client is None:
            return fg_download_global_best(int(n_genomes), session_slot=int(session_slot))
        return gpu_client.submit(
            GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
            {"n_genomes": int(n_genomes), "song_slot": int(session_slot)},
        ).future.result()

    gpu_batches = 0
    unique_genomes = 0
    deduped_genomes = 0
    dedupe_groups = 0
    candidate_cache_hits = 0
    candidate_cache_misses = 0
    candidate_cache_writes = 0
    max_genomes = int(getattr(gem_fields, "MAX_GENOMES", 4096) or 4096)

    for group in prepared_groups.values():
        indices = list(group["indices"])
        stats_rows = list(group["stats"])
        counts = list(group["counts"])
        pairs = list(group["pairs"])
        selected_color = str(group["selected_color"] or "")
        flags = build_color_flags(primary, secondary, selected_color)
        cache = FgCandidateCacheShard.load(
            fg_context_digest(
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                primary_color=primary,
                secondary_color=secondary,
                selected_color=selected_color,
                num_sections=int(group["num_sections"]),
                non_fever_base=int(group["non_fever_base"]),
                search_ranges=_search_ranges_for(center_fts[indices[0]], center_ffs[indices[0]], search_radius),
                solver_version=int(FORCE_GREATS_ALGO_VERSION),
            )
        )

        unique_stats: list[dict[str, Any]] = []
        fanout: list[list[int]] = []
        by_response: dict[tuple[int, ...], int] = {}
        for original_local_idx, base_stats in enumerate(stats_rows):
            response_key = _local_gear_response_key(base_stats, primary=primary, secondary=secondary)
            unique_idx = by_response.get(response_key)
            if unique_idx is None:
                unique_idx = len(unique_stats)
                by_response[response_key] = int(unique_idx)
                unique_stats.append(base_stats)
                fanout.append([])
            fanout[int(unique_idx)].append(int(original_local_idx))

        unique_genomes += int(len(unique_stats))
        deduped_genomes += int(len(stats_rows) - len(unique_stats))
        dedupe_groups += sum(1 for members in fanout if len(members) > 1)

        miss_unique_indices: list[int] = []
        miss_stats: list[dict[str, Any]] = []
        for unique_idx, base_stats in enumerate(unique_stats):
            response_key = _local_gear_response_key(base_stats, primary=primary, secondary=secondary)
            cached = cache.get(response_key)
            if isinstance(cached, dict):
                candidate_cache_hits += 1
                for original_local_idx in fanout[int(unique_idx)]:
                    src_idx = indices[int(original_local_idx)]
                    results[src_idx] = dict(cached)
                continue
            candidate_cache_misses += 1
            miss_unique_indices.append(int(unique_idx))
            miss_stats.append(base_stats)

        for start in range(0, len(miss_stats), max_genomes):
            end = min(int(start) + int(max_genomes), len(miss_stats))
            chunk_stats = miss_stats[int(start) : int(end)]
            genome_stats = _genome_stats_array(chunk_stats, primary=primary, secondary=secondary)
            n_chunk = int(len(chunk_stats))
            song_slot = safe_int(calc_song.get("_gpu_song_slot", 0), 0) if isinstance(calc_song, dict) else 0

            solve_kwargs = {
                "n_sections": len(counts[0]),
                "is_p_ft": flags["is_p_ft"],
                "is_s_ft": flags["is_s_ft"],
                "is_p_ff": flags["is_p_ff"],
                "is_s_ff": flags["is_s_ff"],
                "is_p_pp": flags["is_p_pp"],
                "is_s_pp": flags["is_s_pp"],
                "is_p_cm": flags["is_p_cm"],
                "is_s_cm": flags["is_s_cm"],
                "is_p_fm": flags["is_p_fm"],
                "is_s_fm": flags["is_s_fm"],
                "is_p_ov": flags["is_p_ov"],
                "is_s_ov": flags["is_s_ov"],
                "ref_arrays": ref_arrays,
                "total_budget": TOTAL_GEM_BUDGET,
                "gem_scale_fever": GEM_SCALE_FEVER,
                "song_slot": int(song_slot),
            }

            max_ftff = int(getattr(fg_fields, "FG_MAX_FTFF", 1024) or 1024)
            if len(pairs) > max_ftff:
                _fg_reset_owner(n_chunk, session_slot=int(song_slot))
                for pair_start in range(0, len(pairs), max_ftff):
                    pair_chunk = pairs[int(pair_start) : int(pair_start) + int(max_ftff)]
                    _fg_solve_owner(
                        genome_stats,
                        timestamps,
                        song_data.get("fg_great_candidate_timestamps"),
                        long_notes,
                        last_note_time,
                        counts,
                        pair_chunk,
                        accumulate_global=True,
                        **solve_kwargs,
                    )
                    gpu_batches += 1
                raw = _fg_download_owner(n_chunk, session_slot=int(song_slot))
                out = _materialize_raw_best_list(raw, n_chunk)
            else:
                out = _fg_solve_owner(
                    genome_stats,
                    timestamps,
                    song_data.get("fg_great_candidate_timestamps"),
                    long_notes,
                    last_note_time,
                    counts,
                    pairs,
                    **solve_kwargs,
                )
                gpu_batches += 1

            for local_idx, best in enumerate(out or []):
                unique_idx = miss_unique_indices[int(start) + int(local_idx)]
                materialized = _materialize_best(
                    best,
                    counts=counts,
                    num_sections=int(group["num_sections"]),
                    non_fever_base=int(group["non_fever_base"]),
                    base_stats=chunk_stats[int(local_idx)],
                    fg_scorer=fg_scorer,
                )
                if materialized is not None:
                    response_key = _local_gear_response_key(
                        chunk_stats[int(local_idx)], primary=primary, secondary=secondary
                    )
                    if cache.put(response_key, materialized):
                        candidate_cache_writes += 1
                for original_local_idx in fanout[int(unique_idx)]:
                    src_idx = indices[int(original_local_idx)]
                    results[src_idx] = dict(materialized) if materialized is not None else None

    return results, {
        "gpu_batches": int(gpu_batches),
        "groups": int(len(prepared_groups)),
        "input_genomes": int(input_genomes),
        "unique_genomes": int(unique_genomes),
        "deduped_genomes": int(deduped_genomes),
        "dedupe_groups": int(dedupe_groups),
        "section_summary_cache_hits": int(section_summary_cache_hits),
        "section_summary_cache_misses": int(section_summary_cache_misses),
        "candidate_cache_hits": int(candidate_cache_hits),
        "candidate_cache_misses": int(candidate_cache_misses),
        "candidate_cache_writes": int(candidate_cache_writes),
    }
