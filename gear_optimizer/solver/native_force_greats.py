from __future__ import annotations

from itertools import product
from typing import Any

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_GEM_BUDGET, TOTAL_ROWS
from gear_optimizer.core.utils import safe_float, safe_int
from gear_optimizer.solver.force_greats_common import compute_force_greats_timeline
from gear_optimizer.solver.scoring.stats_scoring import _force_greats_counts_to_dict
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


def _section_summary(base_stats: dict[str, Any], calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> tuple[int, int]:
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
    _, _, _, non_fever_base, section_details = compute_force_greats_timeline(
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


def solve_native_force_greats_gpu(
    *,
    base_stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    center_ft: int | None,
    center_ff: int | None,
    search_radius: int | None,
) -> dict[str, Any] | None:
    num_sections, non_fever_base = _section_summary(base_stats, calc_song, ref_arrays)
    if num_sections <= 0:
        return None
    if num_sections > 20:
        raise RuntimeError(f"native FG requires <=20 non-fever sections, got {num_sections}")

    counts = _counts_list(num_sections, non_fever_base)
    if not counts:
        return None

    if center_ft is None or center_ff is None or search_radius is None:
        search_ranges = None
    else:
        radius = int(search_radius)
        search_ranges = (
            int(center_ft) - radius,
            int(center_ft) + radius,
            int(center_ff) - radius,
            int(center_ff) + radius,
        )

    pairs = _ftff_pairs(search_ranges)
    if not pairs:
        return None

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    total_notes = int(len(timestamps)) if timestamps is not None else 0
    if total_notes <= 0:
        return None

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    base_ts = song_data.get("timestamps", timestamps)
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    primary = str(metadata.get("Primary Color", "") or "")
    secondary = str(metadata.get("Secondary Color", "") or "")
    flags = build_color_flags(primary, secondary, selected_color)

    from gear_optimizer.solver.taichi_gem.force_greats.api import solve_force_greats_finder_gpu

    out = solve_force_greats_finder_gpu(
        [
            {
                "base_pp": int(base_stats.get("Perfect Points", 0)),
                "base_cm": int(base_stats.get("Combo Multiplier", 0)),
                "base_fm": int(base_stats.get("Fever Multiplier", 0)),
                "base_ft_stat": int(base_stats.get("Fever Time", 0)),
                "base_ff_stat": int(base_stats.get("Fever Fill Rate", 0)),
                "base_p_val": int(base_stats.get(primary, 0)),
                "base_s_val": int(base_stats.get(secondary, 0)),
            }
        ],
        timestamps,
        song_data.get("fg_great_candidate_timestamps"),
        long_notes,
        last_note_time,
        counts,
        pairs,
        n_sections=len(counts[0]),
        is_p_ft=flags["is_p_ft"],
        is_s_ft=flags["is_s_ft"],
        is_p_ff=flags["is_p_ff"],
        is_s_ff=flags["is_s_ff"],
        is_p_pp=flags["is_p_pp"],
        is_s_pp=flags["is_s_pp"],
        is_p_cm=flags["is_p_cm"],
        is_s_cm=flags["is_s_cm"],
        is_p_fm=flags["is_p_fm"],
        is_s_fm=flags["is_s_fm"],
        is_p_ov=flags["is_p_ov"],
        is_s_ov=flags["is_s_ov"],
        ref_arrays=ref_arrays,
        total_budget=TOTAL_GEM_BUDGET,
        gem_scale_fever=GEM_SCALE_FEVER,
    )
    best = out[0] if out else None
    if not best:
        return None

    cfg_idx = safe_int(best.get("cfg_idx", -1), -1)
    cfg_counts = list(counts[cfg_idx]) if 0 <= cfg_idx < len(counts) else []
    return {
        "base_score": int(best.get("base_score", 0) or 0),
        "final_score": int(best.get("final_score", 0) or 0),
        "score_penalty": int(best.get("score_penalty", 0) or 0),
        "fill_penalty": int(best.get("fill_penalty", 0) or 0),
        "total_penalty": int(best.get("score_penalty", 0) or 0) + int(best.get("fill_penalty", 0) or 0),
        "num_non_fever_sections": int(num_sections),
        "penalty_analysis": {},
        "config_counts": cfg_counts,
        "config_dict": _force_greats_counts_to_dict(cfg_counts, max(2, len(cfg_counts))),
        "non_fever_base": int(non_fever_base),
        "gem_counts": best.get("gem_counts", {}) or {},
        "FT": int(best.get("FT", 0) or 0),
        "FF": int(best.get("FF", 0) or 0),
    }
