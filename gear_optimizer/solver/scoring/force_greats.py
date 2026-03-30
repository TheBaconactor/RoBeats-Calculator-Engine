"""
Force Greats - Force Greats Timeline, Evaluation, and Hill Climb.

This module provides the force greats optimization pipeline:
- _compute_force_greats_timeline: Compute fever timeline with force greats applied
- evaluate_force_greats: Recompute fever timeline and penalties when greats are forced
- evaluate_fg_with_gem_iteration: ForceGreats evaluation WITH full gem solver (FT/FF iteration)
- run_force_greats_hill_climb: Brute-force enumeration of all ForceGreats configurations
- apply_force_greats_to_result: Apply FG penalties to a result dict
- _extract_base_stats: Extract base stats by reversing gem contributions

Force Greats optimization allows forcing greats in non-fever sections to reduce
fill penalties at the cost of score penalties from great notes.
"""

import numpy as np
import threading
from math import floor, ceil
from cachetools import LRUCache

from ...core.constants import (
    TOTAL_ROWS,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    FG_SEARCH_RADIUS,
    FEVER_FILL_BASE_RATE,
    FEVER_TIME_SCALE,
    FEVER_TIME_OFFSET,
)
from ...core.color_flags import build_color_flags
from ...core.utils import safe_int, safe_float, stats_signature
from ...core.time_quantize import quantize_to_int_ms

from ..fever_timeline import (
    calculate_force_greats_timeline_indices,
)

from ..scoring_core import (
    fast_calculate_score,
    lookup_reference_py,
    optimize_core_jit,
)

from .gpu_solver import FORCE_GREATS_ALGO_VERSION, FG_CACHE
from .stats_scoring import build_great_penalty_table, _force_greats_counts_to_dict, _song_cache_key
from .stats_ops import apply_gems_to_base_stats


# Constants
MAX_FT_FF_GEMS = TOTAL_GEM_BUDGET
FG_TIMELINE_CACHE = LRUCache(maxsize=1000)

# Thread-local scratch buffers for Force Greats timeline computation.
# This avoids per-call NumPy allocations in hot loops without introducing
# cross-thread aliasing issues.
_FG_TIMELINE_TLS = threading.local()


def _floor_to_int_ms(timestamps_sec: np.ndarray) -> np.ndarray:
    # Keep float32-first quantization for CPU/GPU parity.
    return quantize_to_int_ms(timestamps_sec)


def _fg_config_to_counts(config: object) -> list[int]:
    if not isinstance(config, dict) or not config:
        return []

    lowered: dict[str, object] = {}
    for k, v in config.items():
        try:
            lowered[str(k).strip().lower()] = v
        except Exception:
            continue

    max_idx = 0
    prefix = "nonfever"
    for k in lowered.keys():
        if not k.startswith(prefix):
            continue
        suf = k[len(prefix) :].strip()
        try:
            idx = int(suf)
        except Exception:
            continue
        if idx > max_idx:
            max_idx = idx

    if max_idx <= 0:
        return []

    out: list[int] = []
    for idx in range(1, max_idx + 1):
        raw = lowered.get(f"{prefix}{idx}", 0)
        try:
            val = int(raw or 0)
        except Exception:
            val = 0
        out.append(max(0, val))
    return out


def summarize_hitsim_offset_deltas_ms_for_fg_variant(
    calc_song: dict, fg_data: dict, ref_arrays: dict
) -> list[int] | None:
    """
    Return a list of signed ms offsets (vs chart time) for the notes that activate *each* FG fever window.

    The i-th entry corresponds to the activation note at the end of non-fever section i. For each section,
    the effective activation time is:
      max(simulated_hit_time, carry_time_from_forced_great_candidates)

    Returns None when HumanHitSim timing data is not available.
    """
    if not isinstance(calc_song, dict) or not isinstance(fg_data, dict) or not isinstance(ref_arrays, dict):
        return None

    fg_meta = fg_data.get("ForceGreats") or {}
    if not isinstance(fg_meta, dict):
        return None

    config = fg_meta.get("config") or {}
    forced_counts = _fg_config_to_counts(config)
    if not forced_counts or sum(forced_counts) <= 0:
        return None

    stats = fg_data.get("Stats") or {}
    if not isinstance(stats, dict) or not stats:
        return None

    song_data = calc_song.get("song_data", {}) or {}
    chart_ts = song_data.get("chart_timestamps")
    great_candidates = song_data.get("fg_great_candidate_timestamps")
    if chart_ts is None or great_candidates is None:
        return None

    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    if timestamps is None:
        return None

    timestamps = np.asarray(timestamps, dtype=np.float32)
    great_candidates = np.asarray(great_candidates, dtype=np.float32)
    total_notes = int(timestamps.shape[0])
    if total_notes <= 0:
        return None

    try:
        fever_fill_rate = lookup_reference_py(stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
        fever_time_stat = lookup_reference_py(stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
    except Exception:
        return None

    meta0 = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(meta0.get("Long Notes"), 0)

    base_ts = song_data.get("timestamps", timestamps)
    try:
        default_last_note = float(base_ts[-1]) if len(base_ts) else 0.0
    except Exception:
        default_last_note = 0.0
    last_note_time = safe_float(meta0.get("Last Note Time"), default_last_note)

    try:
        _, _, _, _non_fever_base, section_details = _compute_force_greats_timeline(
            timestamps,
            great_candidates,
            total_notes,
            fever_fill_rate,
            fever_time_stat,
            long_notes,
            last_note_time,
            forced_counts,
            clamp_base_notes_nonnegative=True,
            clamp_forced_to_section_notes=True,
            use_forced_great_timing=True,
        )
    except Exception:
        return None

    chart_ms = _floor_to_int_ms(np.asarray(chart_ts, dtype=np.float32))
    cand_ms = _floor_to_int_ms(great_candidates)
    song_ms = _floor_to_int_ms(timestamps)
    n = min(int(chart_ms.shape[0]), int(cand_ms.shape[0]), int(song_ms.shape[0]), int(total_notes))
    if n <= 0:
        return None

    deltas: list[int] = []
    for detail in section_details or []:
        try:
            section_start = int(detail.get("start_idx", 0) or 0)
        except Exception:
            section_start = 0
        try:
            notes_to_fill = int(detail.get("notes", 0) or 0)
        except Exception:
            notes_to_fill = 0
        try:
            forced = int(detail.get("forced", 0) or 0)
        except Exception:
            forced = 0

        end_normal = section_start + notes_to_fill
        if end_normal < 0:
            end_normal = 0
        if end_normal >= n:
            break

        carry_time_ms = 0
        if forced > 0:
            skip_wasted = bool(detail.get("skip_wasted"))
            forced_start = section_start + (0 if skip_wasted else 1)
            if forced_start < 0:
                forced_start = 0
            forced_end = forced_start + forced - 1
            if forced_end >= n:
                forced_end = n - 1
            if forced_end >= forced_start:
                cand_t_ms = int(cand_ms[forced_end])
                if cand_t_ms > carry_time_ms:
                    carry_time_ms = cand_t_ms

        start_time_ms = int(song_ms[end_normal])
        effective_start_ms = int(carry_time_ms) if carry_time_ms > start_time_ms else int(start_time_ms)
        deltas.append(int(effective_start_ms) - int(chart_ms[end_normal]))

    return deltas or None


def summarize_hitsim_offset_deltas_ms_for_base(calc_song: dict, base_data: dict, ref_arrays: dict) -> list[int] | None:
    """
    Return a list of signed ms offsets (vs chart time) for the notes that activate *each* base fever window.

    This only applies when HumanHitSim.ApplyTo=ALL (timestamps are simulated).
    """
    if not isinstance(calc_song, dict) or not isinstance(base_data, dict) or not isinstance(ref_arrays, dict):
        return None

    meta0 = calc_song.get("metadata", {}) or {}
    if not meta0.get("HumanHitSimApplied"):
        return None
    apply_to = str(meta0.get("HumanHitSimApplyTo", "") or "").strip().upper()
    if apply_to != "ALL":
        return None

    stats = base_data.get("Stats") or {}
    if not isinstance(stats, dict) or not stats:
        return None

    song_data = calc_song.get("song_data", {}) or {}
    chart_ts = song_data.get("chart_timestamps")
    timestamps = song_data.get("timestamps")
    if chart_ts is None or timestamps is None:
        return None

    timestamps = np.asarray(timestamps, dtype=np.float32)
    total_notes = int(timestamps.shape[0])
    if total_notes <= 0:
        return None

    try:
        fever_fill_rate = lookup_reference_py(stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
        fever_time_stat = lookup_reference_py(stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
    except Exception:
        return None

    long_notes = safe_int(meta0.get("Long Notes"), 0)

    base_ts = song_data.get("timestamps", timestamps)
    try:
        default_last_note = float(base_ts[-1]) if len(base_ts) else 0.0
    except Exception:
        default_last_note = 0.0
    last_note_time = safe_float(meta0.get("Last Note Time"), default_last_note)

    chart_ms = _floor_to_int_ms(np.asarray(chart_ts, dtype=np.float32))
    sim_ms = _floor_to_int_ms(timestamps)
    n = min(int(chart_ms.shape[0]), int(sim_ms.shape[0]), int(total_notes))
    if n <= 0:
        return None

    deltas: list[int] = []

    # Avoid calling the ForceGreats timeline JIT in DB/persistence paths; base fever stepping is small
    # and can be computed exactly here via searchsorted (matches `fever_timeline.calculate_fever_timeline_indices`).
    non_fever_cas = (total_notes - long_notes) * FEVER_FILL_BASE_RATE
    if non_fever_cas < 0.0:
        non_fever_cas = 0.0

    try:
        non_fever_base = int(ceil(float(non_fever_cas) * float(fever_fill_rate)))
    except Exception:
        return None

    try:
        fever_time_cas = float(last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
        real_fever_time = float(fever_time_cas) * float(fever_time_stat)
    except Exception:
        return None

    current_note_idx = 0
    fever_section = 0
    while int(current_note_idx) < int(total_notes):
        fever_section += 1
        notes_to_fill = int(non_fever_base) - 1 if fever_section == 1 else int(non_fever_base)

        end_normal_idx = int(min(int(current_note_idx) + int(notes_to_fill), int(total_notes)))
        current_note_idx = end_normal_idx
        if int(current_note_idx) >= int(total_notes):
            break

        if int(current_note_idx) <= 0:
            break

        if int(current_note_idx) >= int(n):
            break

        a = int(current_note_idx)
        deltas.append(int(sim_ms[a]) - int(chart_ms[a]))

        start_time = float(timestamps[a])
        end_time = float(start_time) + float(real_fever_time)
        try:
            fever_end_idx = int(np.searchsorted(timestamps, end_time, side="left"))
        except Exception:
            break
        current_note_idx = fever_end_idx

    return deltas or None


def _get_fg_timeline_buffers(total_notes: int):
    """
    Get (or allocate) reusable scratch buffers sized for `total_notes`.

    Returns:
        tuple: (fever_mask_buffer, section_start, section_forced, section_fill_penalty, section_skip_wasted)
    """
    n = int(total_notes)
    if n < 0:
        n = 0
    # Worst-case: section count is bounded by note count (+1 for safety).
    section_cap = n + 1

    buf = getattr(_FG_TIMELINE_TLS, "buf", None)
    if buf is None:
        buf = {}
        _FG_TIMELINE_TLS.buf = buf

    fever_mask = buf.get("fever_mask")
    if fever_mask is None or int(getattr(fever_mask, "shape", (0,))[0]) != n:
        fever_mask = np.zeros(n, dtype=np.bool_)
        buf["fever_mask"] = fever_mask
    else:
        fever_mask[:] = False

    section_start = buf.get("section_start")
    if section_start is None or int(getattr(section_start, "shape", (0,))[0]) != section_cap:
        section_start = np.zeros(section_cap, dtype=np.int32)
        buf["section_start"] = section_start
    else:
        section_start[:] = 0

    section_forced = buf.get("section_forced")
    if section_forced is None or int(getattr(section_forced, "shape", (0,))[0]) != section_cap:
        section_forced = np.zeros(section_cap, dtype=np.int32)
        buf["section_forced"] = section_forced
    else:
        section_forced[:] = 0

    section_fill_penalty = buf.get("section_fill_penalty")
    if section_fill_penalty is None or int(getattr(section_fill_penalty, "shape", (0,))[0]) != section_cap:
        section_fill_penalty = np.zeros(section_cap, dtype=np.int32)
        buf["section_fill_penalty"] = section_fill_penalty
    else:
        section_fill_penalty[:] = 0

    section_skip_wasted = buf.get("section_skip_wasted")
    if section_skip_wasted is None or int(getattr(section_skip_wasted, "shape", (0,))[0]) != section_cap:
        section_skip_wasted = np.zeros(section_cap, dtype=np.bool_)
        buf["section_skip_wasted"] = section_skip_wasted
    else:
        section_skip_wasted[:] = False

    return fever_mask, section_start, section_forced, section_fill_penalty, section_skip_wasted


def _normalize_ft_ff_search_ranges(search_ranges):
    if search_ranges:
        start_ft, end_ft, start_ff, end_ff = search_ranges
        start_ft = max(0, int(start_ft))
        end_ft = min(MAX_FT_FF_GEMS, int(end_ft))
        start_ff = max(0, int(start_ff))
        end_ff = min(MAX_FT_FF_GEMS, int(end_ff))
    else:
        start_ft, end_ft = 0, MAX_FT_FF_GEMS
        start_ff, end_ff = 0, MAX_FT_FF_GEMS

    return start_ft, end_ft, start_ff, end_ff


def _iter_ft_ff_budget_pairs(start_ft, end_ft, start_ff, end_ff, total_budget):
    total_budget = int(total_budget)
    start_ft = int(start_ft)
    end_ft = int(end_ft)
    start_ff = int(start_ff)
    end_ff = int(end_ff)

    for ft_gems in range(start_ft, end_ft + 1):
        remaining_after_ft = total_budget - ft_gems
        if remaining_after_ft < 0:
            break

        ff_end = min(end_ff, remaining_after_ft)
        for ff_gems in range(start_ff, ff_end + 1):
            current_budget = remaining_after_ft - ff_gems
            if current_budget < 0:
                break
            yield ft_gems, ff_gems, current_budget


def _compute_force_greats_timeline(
    timestamps,
    great_candidate_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes,
    last_note_time,
    force_counts,
    *,
    clamp_base_notes_nonnegative,
    clamp_forced_to_section_notes,
    use_forced_great_timing,
):
    """
    Compute fever timeline with force greats applied.

    Args:
        timestamps: Song timestamps array
        total_notes: Total number of notes
        fever_fill_rate: Fever fill rate factor
        fever_time_stat: Fever time factor
        long_notes: Number of long notes
        last_note_time: Last note timestamp
        force_counts: List of forced great counts per section
        clamp_base_notes_nonnegative: Whether to clamp base notes to non-negative
        clamp_forced_to_section_notes: Whether to clamp forced counts to section notes

    Returns:
        tuple: (fever_mask_head, count_body_fever, count_body_normal, non_fever_base, section_details)
    """
    forced_arr = np.asarray(force_counts, dtype=np.int32) if force_counts else np.zeros(0, dtype=np.int32)

    fever_mask_buffer, section_start, section_forced, section_fill_penalty, section_skip_wasted = (
        _get_fg_timeline_buffers(int(total_notes))
    )

    (
        fever_mask_head_view,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_count,
    ) = calculate_force_greats_timeline_indices(
        timestamps,
        great_candidate_timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        forced_arr,
        int(forced_arr.shape[0]),
        bool(clamp_base_notes_nonnegative),
        bool(clamp_forced_to_section_notes),
        bool(use_forced_great_timing),
        fever_mask_buffer,
        section_start,
        section_forced,
        section_fill_penalty,
        section_skip_wasted,
    )

    section_details = []
    for i in range(int(section_count)):
        base_notes = non_fever_base - 1 if (i == 0) else non_fever_base
        if clamp_base_notes_nonnegative:
            base_notes = max(0, int(base_notes))
        notes_to_fill = int(base_notes) + int(section_fill_penalty[i])

        section_details.append(
            {
                "start_idx": int(section_start[i]),
                "forced": int(section_forced[i]),
                "fill_penalty_notes": int(section_fill_penalty[i]),
                "skip_wasted": bool(section_skip_wasted[i]),
                "notes": notes_to_fill,
            }
        )

    return (
        fever_mask_head_view.copy(),
        int(count_body_fever),
        int(count_body_normal),
        int(non_fever_base),
        section_details,
    )


def evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=None):
    """
    Recompute fever timeline and penalties when greats are forced in non-fever sections.
    Returns None when prerequisites are missing.
    """
    if not stats or not calc_song:
        return None

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    great_candidates = song_data.get("fg_great_candidate_timestamps", timestamps)
    use_forced_great_timing = bool(song_data.get("fg_great_candidate_timestamps") is not None)
    total_notes = len(timestamps)
    if total_notes <= 0:
        return None

    metadata = calc_song["metadata"]
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    # last_note_time is derived from chart length, not simulated hits.
    base_ts = song_data.get("timestamps", timestamps)
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    primary_color = metadata.get("Primary Color", "")
    secondary_color = metadata.get("Secondary Color", "")
    primary_val = stats.get(primary_color, 0)
    secondary_val = stats.get(secondary_color, 0)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    pp_factor = lookup_reference_py(stats["Perfect Points"], ref_pp, TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_cm, TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_fm, TOTAL_ROWS)
    fever_fill_rate = lookup_reference_py(stats["Fever Fill Rate"], ref_ff, TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats["Fever Time"], ref_ft, TOTAL_ROWS)

    base_value = (primary_val * 2) + secondary_val + pp_factor
    combo_value = floor(base_value * combo_mul)
    # Great scoring:
    # - For ramped notes (<100), we use an integer base derived from per-term floors.
    # - For full-combo (>=100), the game effectively floors *after* applying the combo multiplier to the
    #   underlying float expression. This matters for borderline cases where 2/3 introduces a tiny
    #   floating error (e.g., 1689.999999999...), which can shift the floor result by 1–2.
    great_penalty_base_head = floor((primary_val * 2) * (2.0 / 3.0)) + floor(secondary_val * (2.0 / 3.0)) + 150
    great_penalty_base_raw = ((primary_val * 2) * (2.0 / 3.0)) + (secondary_val * (2.0 / 3.0)) + 150.0

    great_combo_value = floor(great_penalty_base_raw * combo_mul)
    body_penalty = max(0, combo_value - great_combo_value)

    penalty_table = build_great_penalty_table(base_value, combo_mul, great_penalty_base_head)
    # Ensure the last ramp note (100th hit) matches the constant full-combo body penalty.
    if penalty_table:
        penalty_table[-1] = body_penalty

    force_counts = list(forced_counts or [])
    (
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_details,
    ) = _compute_force_greats_timeline(
        timestamps,
        great_candidates,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        force_counts,
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
        use_forced_great_timing=use_forced_great_timing,
    )

    base_score = fast_calculate_score(
        base_value,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )

    total_score_penalty = 0
    total_fill_penalty = 0
    penalty_analysis = {}
    for idx, detail in enumerate(section_details):
        section_key = f"NonFever{idx + 1}"
        fill_penalty_score = detail["fill_penalty_notes"] * combo_value
        total_fill_penalty += fill_penalty_score
        forced = detail["forced"]
        if forced > 0:
            # For sections 2+, the first non-fever note is the transition note (no fill).
            # Forced Greats should apply to fill-contributing notes, so offset by +1.
            start_idx = detail["start_idx"] + (0 if detail.get("skip_wasted") else 1)
            score_penalty = 0
            note_idx = start_idx
            remaining = forced
            while remaining > 0:
                if note_idx < len(penalty_table):
                    score_penalty += penalty_table[note_idx]
                else:
                    score_penalty += body_penalty
                note_idx += 1
                remaining -= 1
        else:
            score_penalty = 0
        total_score_penalty += score_penalty
        penalty_analysis[section_key] = {
            "forced_greats": forced,
            "score_penalty": score_penalty,
            "fill_penalty": fill_penalty_score,
            "total_penalty": score_penalty + fill_penalty_score,
        }

    used_counts = force_counts[:]
    if len(used_counts) < len(section_details):
        used_counts.extend([0] * (len(section_details) - len(used_counts)))

    return {
        "base_score": base_score,
        "final_score": max(0, base_score - total_score_penalty),
        "score_penalty": total_score_penalty,
        "fill_penalty": total_fill_penalty,
        "total_penalty": total_score_penalty + total_fill_penalty,
        "num_non_fever_sections": len(section_details),
        "config_counts": used_counts[: len(section_details)],
        "config_dict": _force_greats_counts_to_dict(used_counts, len(section_details)),
        "penalty_analysis": penalty_analysis,
        "non_fever_base": non_fever_base,
    }


def evaluate_fg_with_gem_iteration(
    base_stats,
    calc_song,
    ref_arrays,
    selected_color,
    forced_counts,
    search_ranges=None,
    use_gpu: bool = False,
):
    """
    ForceGreats evaluation WITH full gem solver (FT/FF iteration).

    This function:
    1. Calculates the FG timeline for the given forced_counts
    2. Iterates ALL (FT, FF) combinations (like the main gem solver)
    3. For each (FT, FF), optimizes PP/CM/FM/OV gems
    4. Returns the best result with optimal gems for this FG config

    Args:
        base_stats: Stats BEFORE gem optimization (gear+mini only)
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        selected_color: Selected elemental color for overflow gems
        forced_counts: List of forced great counts per non-fever section

    Returns:
        dict: Result with final_score and optimal gem allocation
    """
    if not base_stats or not calc_song:
        return None

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    great_candidates = song_data.get("fg_great_candidate_timestamps", timestamps)
    use_forced_great_timing = bool(song_data.get("fg_great_candidate_timestamps") is not None)
    total_notes = len(timestamps)
    if total_notes <= 0:
        return None

    metadata = calc_song["metadata"]
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    # last_note_time is derived from chart length, not simulated hits.
    base_ts = song_data.get("timestamps", timestamps)
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    p_color = metadata.get("Primary Color", "")
    s_color = metadata.get("Secondary Color", "")

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    flags = build_color_flags(p_color, s_color, selected_color)
    is_p_pp = flags["is_p_pp"]
    is_s_pp = flags["is_s_pp"]
    is_p_cm = flags["is_p_cm"]
    is_s_cm = flags["is_s_cm"]
    is_p_fm = flags["is_p_fm"]
    is_s_fm = flags["is_s_fm"]
    is_p_ov = flags["is_p_ov"]
    is_s_ov = flags["is_s_ov"]

    # Base stats (pre-gem)
    base_pp = base_stats.get("Perfect Points", 0)
    base_cm = base_stats.get("Combo Multiplier", 0)
    base_fm = base_stats.get("Fever Multiplier", 0)
    base_ff_stat = base_stats.get("Fever Fill Rate", 0)
    base_ft_stat = base_stats.get("Fever Time", 0)
    base_beat = base_stats.get("Beat", 0)
    base_vibe = base_stats.get("Vibe", 0)

    non_fever_cas = max(0.0, (total_notes - long_notes) * 0.333)
    force_counts = list(forced_counts or [])
    song_key = _song_cache_key(calc_song)

    start_ft, end_ft, start_ff, end_ff = _normalize_ft_ff_search_ranges(search_ranges)

    # Collect candidates first (preserve deterministic (ft, ff) iteration order).
    candidates = []

    for ft_gems, ff_gems, current_budget in _iter_ft_ff_budget_pairs(
        start_ft,
        end_ft,
        start_ff,
        end_ff,
        TOTAL_GEM_BUDGET,
    ):
        # Look up fever parameters with FT/FF gems applied
        cur_ft_stat = base_ft_stat + ft_gems * GEM_SCALE_FEVER
        cur_ff_stat = base_ff_stat + ff_gems * GEM_SCALE_FEVER
        fever_fill_rate = lookup_reference_py(cur_ff_stat, ref_ff, TOTAL_ROWS)
        fever_time_stat = lookup_reference_py(cur_ft_stat, ref_ft, TOTAL_ROWS)
        non_fever_base = ceil(non_fever_cas * fever_fill_rate)

        # Timeline cache includes FT, FF, forced_counts, and song identity.
        # We also cache section_details because FG penalties need start indices.
        fg_cache_key = (ft_gems, ff_gems, tuple(force_counts), song_key)
        cached = FG_TIMELINE_CACHE.get(fg_cache_key)

        if cached is None:
            (
                fever_mask_head,
                count_body_fever,
                count_body_normal,
                _nf_base_from_jit,
                section_details,
            ) = _compute_force_greats_timeline(
                timestamps,
                great_candidates,
                total_notes,
                fever_fill_rate,
                fever_time_stat,
                long_notes,
                last_note_time,
                force_counts,
                clamp_base_notes_nonnegative=False,
                clamp_forced_to_section_notes=False,
                use_forced_great_timing=use_forced_great_timing,
            )

            cached = (fever_mask_head, count_body_fever, count_body_normal, section_details)
            FG_TIMELINE_CACHE[fg_cache_key] = cached

        fever_mask_head, count_body_fever, count_body_normal, section_details = cached

        # CPU optimizer expects p/s values with FT/FF elemental contributions already applied.
        cur_beat = base_beat + ft_gems * GEM_STAT_TO_ELEMENT_SCALE
        cur_vibe = base_vibe + ff_gems * GEM_STAT_TO_ELEMENT_SCALE
        cur_p_val = cur_beat if p_color == "Beat" else (cur_vibe if p_color == "Vibe" else base_stats.get(p_color, 0))
        cur_s_val = cur_beat if s_color == "Beat" else (cur_vibe if s_color == "Vibe" else base_stats.get(s_color, 0))

        candidates.append(
            (
                ft_gems,
                ff_gems,
                current_budget,
                non_fever_base,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
                section_details,
                cur_p_val,
                cur_s_val,
            )
        )

    best_result = None
    best_score = -1

    # Evaluate each candidate in deterministic order (CPU reference path).
    for cand in candidates:
        (
            ft_gems,
            ff_gems,
            current_budget,
            non_fever_base,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
            section_details,
            cur_p_val,
            cur_s_val,
        ) = cand

        (
            final_pp,
            final_cm,
            final_fm,
            final_p_val,
            final_s_val,
            gems_pp,
            gems_cm,
            gems_fm,
            gems_ov,
        ) = optimize_core_jit(
            current_budget,
            base_pp,
            base_cm,
            base_fm,
            cur_p_val,
            cur_s_val,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            ref_pp,
            ref_cm,
            ref_fm,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
            GEM_SCALE_NORMAL,
            GEM_SCALE_FEVER,
            GEM_STAT_TO_ELEMENT_SCALE,
            ELEMENTAL_GEM_SCALE,
            TOTAL_ROWS,
            MAX_STAT_INDEX,
        )

        pp_factor = lookup_reference_py(final_pp, ref_pp, TOTAL_ROWS)
        combo_mul = lookup_reference_py(final_cm, ref_cm, TOTAL_ROWS)
        fever_mul = lookup_reference_py(final_fm, ref_fm, TOTAL_ROWS)

        base_value = (final_p_val * 2) + final_s_val + pp_factor
        base_score = fast_calculate_score(
            base_value,
            combo_mul,
            fever_mul,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
        )

        # FG penalties (score penalty for greats + fill penalty)
        combo_value = floor(base_value * combo_mul)
        great_penalty_base_head = floor((final_p_val * 2) * (2.0 / 3.0)) + floor(final_s_val * (2.0 / 3.0)) + 150
        great_penalty_base_raw = ((final_p_val * 2) * (2.0 / 3.0)) + (final_s_val * (2.0 / 3.0)) + 150.0
        penalty_table = build_great_penalty_table(base_value, combo_mul, great_penalty_base_head)
        body_penalty = max(0, combo_value - floor(great_penalty_base_raw * combo_mul))
        if penalty_table:
            penalty_table[-1] = body_penalty

        total_score_penalty = 0
        total_fill_penalty = 0
        penalty_analysis = {}

        for s_idx, detail in enumerate(section_details):
            section_key = f"NonFever{s_idx + 1}"
            fill_p_score = detail["fill_penalty_notes"] * combo_value
            total_fill_penalty += fill_p_score

            forced = detail["forced"]
            score_p = 0
            if forced > 0:
                # For sections 2+, the first non-fever note is the transition note (no fill).
                # Forced Greats should apply to fill-contributing notes, so offset by +1.
                start_idx = detail["start_idx"] + (0 if detail.get("skip_wasted") else 1)

                note_idx = start_idx
                remaining = forced
                while remaining > 0:
                    if note_idx < len(penalty_table):
                        score_p += penalty_table[note_idx]
                    else:
                        score_p += body_penalty
                    note_idx += 1
                    remaining -= 1

            total_score_penalty += score_p
            penalty_analysis[section_key] = {
                "forced_greats": forced,
                "score_penalty": score_p,
                "fill_penalty": fill_p_score,
                "total_penalty": score_p + fill_p_score,
            }

        final_score = max(0, base_score - total_score_penalty)

        if final_score > (best_score if best_result else -1):
            best_score = final_score
            best_result = {
                "base_score": base_score,
                "final_score": final_score,
                "score_penalty": total_score_penalty,
                "fill_penalty": total_fill_penalty,
                "total_penalty": total_score_penalty + total_fill_penalty,
                "num_non_fever_sections": len(section_details),
                "penalty_analysis": penalty_analysis,
                "config_counts": force_counts[:],
                "config_dict": _force_greats_counts_to_dict(force_counts, max(2, len(force_counts))),
                "non_fever_base": non_fever_base,
                "gem_counts": {
                    "Perfect Points": gems_pp,
                    "Combo Multiplier": gems_cm,
                    "Fever Multiplier": gems_fm,
                    "Element": gems_ov,
                },
                "FT": ft_gems,
                "FF": ff_gems,
            }

    return best_result


def run_force_greats_hill_climb(
    stats,
    calc_song,
    ref_arrays,
    selected_color=None,
    center_ft=None,
    center_ff=None,
    search_radius=FG_SEARCH_RADIUS,
    use_gpu: bool = False,
):
    """
    Brute-force enumeration of all ForceGreats configurations WITH gem re-optimization.

    For each FG config, re-runs the full gem solver (FT/FF iteration) to find
    optimal gems for that specific FG timeline. This guarantees finding the
    global optimum instead of getting stuck with gems optimized for normal timeline.

    NOTE: This function now expects stats to be the gem-optimized Stats dict from
    the main solver. It extracts base stats and uses the new gem iteration function.
    """
    # Get baseline info from existing stats
    baseline = evaluate_force_greats(stats, calc_song, ref_arrays, [])
    if not baseline:
        return None

    num_sections = baseline["num_non_fever_sections"]
    if num_sections == 0:
        return baseline

    # Safety: excessive sections (e.g. 0 fill rate -> 1000+ sections) breaks brute force & GPU limits.
    # Return baseline as-is since FG is effectively impossible/useless in this case.
    if num_sections > 20:
        return baseline

    # Selected element is a loadout/config property (overflow target), not always the song primary.
    # Default to song primary only if missing.
    selected_color = selected_color or calc_song["metadata"].get("Primary Color", "Rush")

    # Extract base stats (before gems) - use stats directly since we want gear+mini stats
    # The GPU path now returns gem-adjusted stats, so we need to reverse
    # For simplicity, we can use the stats as-is since evaluate_fg_with_gem_iteration
    # handles the gem allocation internally
    base_stats = {}
    for key in [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Chill",
        "Flow",
        "Rush",
        "Beat",
        "Vibe",
    ]:
        base_stats[key] = stats.get(key, 0)

    non_fever_base = baseline.get("non_fever_base", 20)
    # Calculate FT/FF search window (kept tight; full FT/FF × all FG configs explodes combinatorially)
    search_ranges = None
    if center_ft is not None and center_ff is not None:
        search_ranges = (
            center_ft - search_radius,
            center_ft + search_radius,
            center_ff - search_radius,
            center_ff + search_radius,
        )

    # Build FG config list in deterministic order (matches the nested-loop ordering)
    counts_list = []

    # Per-section caps requested by user
    cap_s0 = min(int(non_fever_base or 0), 50)
    cap_s1 = min(int(non_fever_base or 0), 25)
    cap_s2 = min(int(non_fever_base or 0), 15)

    if num_sections == 1:
        for s0 in range(cap_s0 + 1):
            counts_list.append((s0,))
    elif num_sections == 2:
        for s0 in range(cap_s0 + 1):
            for s1 in range(cap_s1 + 1):
                counts_list.append((s0, s1))
    elif num_sections == 3:
        for s0 in range(cap_s0 + 1):
            for s1 in range(cap_s1 + 1):
                for s2 in range(cap_s2 + 1):
                    counts_list.append((s0, s1, s2))
    else:
        from itertools import product

        cap = min(int(non_fever_base or 0), 5)
        for counts in product(range(cap + 1), repeat=num_sections):
            counts_list.append(tuple(counts))

    # --------------------------------------------------------------------
    # FULL GPU FINDER PATH (when enabled):
    #   Runs FG timeline + gem optimization + penalties entirely on GPU and
    #   reduces to the best FG config per loadout.
    # --------------------------------------------------------------------
    if use_gpu:
        try:
            from ..taichi_gem.force_greats.api import solve_force_greats_finder_gpu

            song_data = calc_song.get("song_data", {}) or {}
            timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
            great_candidates = song_data.get("fg_great_candidate_timestamps")
            total_notes = len(timestamps)
            if total_notes <= 0:
                return None

            meta = calc_song.get("metadata", {}) or {}
            long_notes = safe_int(meta.get("Long Notes"), 0)
            # last_note_time is derived from chart length, not simulated hits.
            base_ts = song_data.get("timestamps", timestamps)
            default_last_note = base_ts[-1] if total_notes else 0.0
            last_note_time = safe_float(meta.get("Last Note Time"), default_last_note)
            p_color = meta.get("Primary Color", "")
            s_color = meta.get("Secondary Color", "")

            flags = build_color_flags(p_color, s_color, selected_color)
            is_p_pp = flags["is_p_pp"]
            is_s_pp = flags["is_s_pp"]
            is_p_cm = flags["is_p_cm"]
            is_s_cm = flags["is_s_cm"]
            is_p_fm = flags["is_p_fm"]
            is_s_fm = flags["is_s_fm"]
            is_p_ft = flags["is_p_ft"]
            is_s_ft = flags["is_s_ft"]
            is_p_ff = flags["is_p_ff"]
            is_s_ff = flags["is_s_ff"]
            is_p_ov = flags["is_p_ov"]
            is_s_ov = flags["is_s_ov"]

            # FT/FF window list (no budgets here; GPU computes budget=total_budget-ft-ff)
            start_ft, end_ft, start_ff, end_ff = _normalize_ft_ff_search_ranges(search_ranges)
            ftff_pairs = [
                (ft, ff)
                for ft, ff, _ in _iter_ft_ff_budget_pairs(
                    start_ft,
                    end_ft,
                    start_ff,
                    end_ff,
                    TOTAL_GEM_BUDGET,
                )
            ]

            # Single-genome input (base stats; GPU allocates gems)
            genome_stats_list = [
                {
                    "base_pp": int(base_stats.get("Perfect Points", 0)),
                    "base_cm": int(base_stats.get("Combo Multiplier", 0)),
                    "base_fm": int(base_stats.get("Fever Multiplier", 0)),
                    "base_ft_stat": int(base_stats.get("Fever Time", 0)),
                    "base_ff_stat": int(base_stats.get("Fever Fill Rate", 0)),
                    "base_p_val": int(base_stats.get(p_color, 0)),
                    "base_s_val": int(base_stats.get(s_color, 0)),
                }
            ]

            out = solve_force_greats_finder_gpu(
                genome_stats_list,
                timestamps,
                great_candidates,
                long_notes,
                last_note_time,
                counts_list,
                ftff_pairs,
                n_sections=len(counts_list[0]) if counts_list else 1,
                is_p_ft=is_p_ft,
                is_s_ft=is_s_ft,
                is_p_ff=is_p_ff,
                is_s_ff=is_s_ff,
                is_p_pp=is_p_pp,
                is_s_pp=is_s_pp,
                is_p_cm=is_p_cm,
                is_s_cm=is_s_cm,
                is_p_fm=is_p_fm,
                is_s_fm=is_s_fm,
                is_p_ov=is_p_ov,
                is_s_ov=is_s_ov,
                ref_arrays=ref_arrays,
                total_budget=TOTAL_GEM_BUDGET,
                gem_scale_fever=GEM_SCALE_FEVER,
            )
            best = out[0] if out else None
            if not best:
                return None

            cfg_idx = best.get("cfg_idx", -1)
            cfg_counts = (
                list(counts_list[cfg_idx]) if (cfg_idx is not None and 0 <= int(cfg_idx) < len(counts_list)) else []
            )

            result = {
                "base_score": best.get("base_score", 0),
                "final_score": best.get("final_score", 0),
                "score_penalty": best.get("score_penalty", 0),
                "fill_penalty": best.get("fill_penalty", 0),
                "total_penalty": (best.get("score_penalty", 0) or 0) + (best.get("fill_penalty", 0) or 0),
                "num_non_fever_sections": num_sections,
                "penalty_analysis": {},  # optional; GPU path currently omits per-section breakdown
                "config_counts": cfg_counts,
                "config_dict": _force_greats_counts_to_dict(cfg_counts, max(2, len(cfg_counts))),
                "non_fever_base": non_fever_base,
                "gem_counts": best.get("gem_counts", {}) or {},
                "FT": best.get("FT", 0),
                "FF": best.get("FF", 0),
            }
            result["ForceGreats"] = {
                "config": result.get("config_dict", {}),
                "base_score": result.get("base_score", 0),
            }
            return result
        except Exception as e:
            raise RuntimeError(f"FG full finder failed: {type(e).__name__}: {e}") from e

    if use_gpu:
        raise RuntimeError("FG full finder produced no result.")

    # --------------------------------------------------------------------
    # CPU reference path: evaluate each FG config individually (CPU-only)
    # --------------------------------------------------------------------
    best_result = None
    best_score = -1

    for counts in counts_list:
        candidate = evaluate_fg_with_gem_iteration(
            base_stats,
            calc_song,
            ref_arrays,
            selected_color,
            list(counts),
            search_ranges,
            use_gpu=False,
        )
        if candidate and candidate.get("final_score", -1) > (best_score if best_score >= 0 else -1):
            best_result = candidate
            best_score = candidate["final_score"]

    if best_result:
        best_result["ForceGreats"] = {
            "config": best_result.get("config_dict", {}),
            "base_score": best_result.get("base_score", 0),
        }

    return best_result


def _extract_base_stats(stats, gem_counts, selected_color, ft_gems=0, ff_gems=0):
    """
    Extract base stats (before gem optimization) by reversing gem contributions.

    NOTE: The GPU batch path returns pre-gem stats, while CPU path returns post-gem stats.
    This function detects which case we're in and acts accordingly.

    Args:
        stats: Stats dict (may or may not have gem contributions)
        gem_counts: GemCounts dict from result
        selected_color: Selected elemental color for overflow
        ft_gems: Number of Fever Time gems allocated
        ff_gems: Number of Fever Fill gems allocated

    Returns:
        dict: Base stats before gem optimization
    """
    if not isinstance(stats, dict) or not stats:
        return {}

    # Only these keys affect gem optimization + FG math; copying full stats dicts is unnecessary
    # and can be expensive for DB-cached payloads.
    keys = (
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Beat",
        "Vibe",
        "Rush",
        "Flow",
        "Chill",
    )
    gs = stats.get

    if not gem_counts:
        return {k: gs(k, 0) for k in keys}

    # Quick check: would reversal make any key negative?
    # If so, stats is already pre-gem (some GPU batch paths return base stats directly).
    try:
        g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
        g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
        g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
        g_ov = int(gem_counts.get("Element", 0) or 0)

        deltas = {
            "Perfect Points": int(g_pp) * int(GEM_SCALE_NORMAL),
            "Chill": int(g_pp) * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Combo Multiplier": int(g_cm) * int(GEM_SCALE_NORMAL),
            "Flow": int(g_cm) * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Multiplier": int(g_fm) * int(GEM_SCALE_FEVER),
            "Rush": int(g_fm) * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Time": int(ft_gems) * int(GEM_SCALE_FEVER),
            "Beat": int(ft_gems) * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Fill Rate": int(ff_gems) * int(GEM_SCALE_FEVER),
            "Vibe": int(ff_gems) * int(GEM_STAT_TO_ELEMENT_SCALE),
        }
        if selected_color:
            deltas[str(selected_color)] = int(g_ov) * int(ELEMENTAL_GEM_SCALE)

        for k, d in deltas.items():
            if int(d) <= 0:
                continue
            cur = gs(k, 0)
            if (int(cur) - int(d)) < -50:  # small tolerance for rounding
                return {kk: gs(kk, 0) for kk in keys}
    except Exception:
        pass

    # Stats has gem contributions baked in - reverse them.
    base = {k: gs(k, 0) for k in keys}

    # Reverse gem contributions
    g_pp = gem_counts.get("Perfect Points", 0)
    g_cm = gem_counts.get("Combo Multiplier", 0)
    g_fm = gem_counts.get("Fever Multiplier", 0)

    # Subtract stat gem contributions
    base["Perfect Points"] = base.get("Perfect Points", 0) - g_pp * GEM_SCALE_NORMAL
    base["Chill"] = base.get("Chill", 0) - g_pp * GEM_STAT_TO_ELEMENT_SCALE

    base["Combo Multiplier"] = base.get("Combo Multiplier", 0) - g_cm * GEM_SCALE_NORMAL
    base["Flow"] = base.get("Flow", 0) - g_cm * GEM_STAT_TO_ELEMENT_SCALE

    base["Fever Multiplier"] = base.get("Fever Multiplier", 0) - g_fm * GEM_SCALE_FEVER
    base["Rush"] = base.get("Rush", 0) - g_fm * GEM_STAT_TO_ELEMENT_SCALE

    # Subtract FT gem contributions (Fever Time + Beat color)
    base["Fever Time"] = base.get("Fever Time", 0) - ft_gems * GEM_SCALE_FEVER
    base["Beat"] = base.get("Beat", 0) - ft_gems * GEM_STAT_TO_ELEMENT_SCALE

    # Subtract FF gem contributions (Fever Fill Rate + Vibe color)
    base["Fever Fill Rate"] = base.get("Fever Fill Rate", 0) - ff_gems * GEM_SCALE_FEVER
    base["Vibe"] = base.get("Vibe", 0) - ff_gems * GEM_STAT_TO_ELEMENT_SCALE

    # Subtract overflow gem contributions
    if selected_color:
        base[selected_color] = base.get(selected_color, 0) - g_ov * ELEMENTAL_GEM_SCALE

    return base


def apply_force_greats_to_result(
    data_dict,
    calc_song,
    ref_arrays,
    manual_counts=None,
    use_finder=False,
    use_gpu: bool = False,
    search_radius=FG_SEARCH_RADIUS,
):
    """
    Evaluate forced-great penalties (manual config or hill-climb finder) for a result dict.
    Returns a cloned variant with the adjusted score while leaving the original untouched.
    Uses FG_CACHE to avoid redundant calculations for identical stats.

    FIXED: Now properly re-runs gem optimization for the FG timeline instead of
    using stats optimized for the normal timeline.
    """
    if not data_dict or "Stats" not in data_dict:
        return None

    stats = data_dict.get("Stats") or {}
    if not stats:
        return None

    gem_counts = data_dict.get("GemCounts") or {}
    selected_color = data_dict.get("Selected Element", calc_song["metadata"].get("Primary Color", ""))
    ft_gems = data_dict.get("FT", 0)
    ff_gems = data_dict.get("FF", 0)

    # Extract base stats (remove gems) to avoid double counting during FG re-optimization.
    # Needed even on cache hits so the returned FG variant can report the *actual*
    # gem allocations/stats used for the FG score.
    base_stats = _extract_base_stats(stats, gem_counts, selected_color, ft_gems, ff_gems)

    # Use stats directly - the original evaluate_force_greats correctly uses
    # the FT/FF values already in stats (from the main gem solver)
    # Our "optimized" version was broken because optimize_core_jit doesn't allocate FT/FF

    # Build cache key from stats signature + FG parameters
    sig = stats_signature(stats, calc_song, selected_color)
    manual_tuple = tuple(manual_counts) if manual_counts else ()
    if use_finder:
        # Finder depends on the FT/FF search window center and (optionally) GPU mode.
        fg_cache_key = (sig, "finder", int(ft_gems), int(ff_gems), int(search_radius), bool(use_gpu))
    else:
        fg_cache_key = (sig, "manual", manual_tuple)

    # Check cache first
    cached_fg = FG_CACHE.get(fg_cache_key)
    if cached_fg is not None:
        fg_result = cached_fg
    else:
        if use_finder:
            fg_result = run_force_greats_hill_climb(
                base_stats,
                calc_song,
                ref_arrays,
                selected_color=selected_color,
                center_ft=ft_gems,
                center_ff=ff_gems,
                search_radius=search_radius,
                use_gpu=use_gpu,
            )
        else:
            # Manual path - does NOT re-optimize gems, so uses original stats (with gems)
            # Evaluate penalty on existing configuration
            fg_result = evaluate_force_greats(stats, calc_song, ref_arrays, manual_counts)

        # Cache the result (even if None)
        FG_CACHE[fg_cache_key] = fg_result

    if not fg_result:
        return None

    fg_info = {
        "enabled": True,
        "mode": "finder" if use_finder else "manual",
        "algo_version": FORCE_GREATS_ALGO_VERSION,
        "search_radius": int(search_radius),
        "center_ft": int(ft_gems),
        "center_ff": int(ff_gems),
        "use_gpu": bool(use_gpu),
        "config": fg_result["config_dict"],
        "final_score": fg_result["final_score"],
    }

    # Memory leak fix: Shallow copy is sufficient (only modifying top-level keys)
    # Eliminates 28K deepcopy operations per song
    fg_variant = data_dict.copy()
    fg_variant["Score"] = fg_result["final_score"]
    fg_variant["ForceGreats"] = fg_info

    # Finder path re-optimizes gems for the FG timeline; reflect the actual
    # gem allocation and resulting Stats in the returned variant so persistence/UI
    # matches the computed FG score.
    if use_finder:
        try:
            fg_gem_counts = fg_result.get("gem_counts") or {}
            fg_ft = int(fg_result.get("FT", ft_gems) or 0)
            fg_ff = int(fg_result.get("FF", ff_gems) or 0)

            g_pp = int(fg_gem_counts.get("Perfect Points", 0) or 0)
            g_cm = int(fg_gem_counts.get("Combo Multiplier", 0) or 0)
            g_fm = int(fg_gem_counts.get("Fever Multiplier", 0) or 0)
            g_ov = int(fg_gem_counts.get("Element", 0) or 0)

            final_stats = apply_gems_to_base_stats(
                base_stats,
                selected_color,
                fg_ft,
                fg_ff,
                g_pp,
                g_cm,
                g_fm,
                g_ov,
                add_missing_element_key=True,
            )

            fg_variant["FT"] = fg_ft
            fg_variant["FF"] = fg_ff
            fg_variant["GemCounts"] = fg_gem_counts
            fg_variant["Stats"] = final_stats
        except Exception:
            pass
    return fg_variant
