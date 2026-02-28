"""
Synthetic human hit-time simulation for server-parity fever modeling.

The real (server-authoritative) fever timeline depends on the *times* notes are
validated at (integer milliseconds), not just the chart timestamps. For the
optimizer, we can optionally generate a seeded, human-like hit-time sequence by
sampling offsets within the judgement windows.

This module currently targets Perfect-only simulation (i.e., all notes hit as
Perfect), with support for held tail notes having a wider window (x2), matching
the game code (GearStats.note_hit_mode_get_time_multiplier).
"""

from __future__ import annotations

import os
import secrets
import numpy as np
import copy
import threading
import zlib

from ..core.constants import TOTAL_ROWS, FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET
from .scoring_core import lookup_reference_py, fast_calculate_score


def _env_debug_fixed_seeds_enabled() -> bool:
    return str(os.environ.get("METAFINDER_DEBUG_FIXED_SEEDS", "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_debug_human_hit_sim_seed() -> int | None:
    raw = str(os.environ.get("METAFINDER_DEBUG_HUMAN_HIT_SIM_SEED", "") or "").strip()
    if not raw:
        return None
    try:
        seed = int(raw)
    except Exception:
        return None
    if seed <= 0:
        return None
    return seed


def _floor_to_int_ms(timestamps_sec: np.ndarray) -> np.ndarray:
    ts = np.asarray(timestamps_sec, dtype=np.float64)
    # Server/client event time uses floor(audio_time_ms). Song dumps store timestamps
    # with ~3 decimals; adding a tiny epsilon avoids float -> int off-by-1 near integers.
    return np.floor(ts * 1000.0 + 1e-6).astype(np.int32)


def _build_per_note_perfect_window_ms(
    note_types: np.ndarray,
    *,
    perfect_lower_ms: int,
    perfect_upper_ms: int,
    held_tail_type: int,
    held_tail_time_multiplier: int,
) -> tuple[np.ndarray, np.ndarray]:
    note_types = np.asarray(note_types, dtype=np.int16)
    is_tail = note_types == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int16)
    lower = (int(perfect_lower_ms) * mult).astype(np.int16)
    upper = (int(perfect_upper_ms) * mult).astype(np.int16)
    return lower, upper


def _truthy(val: object) -> bool:
    return str(val or "").strip().lower() in {"1", "true", "yes", "on"}


def _get_cfg_section(cfg_dict: dict, name: str) -> dict:
    if not isinstance(cfg_dict, dict):
        return {}
    if name in cfg_dict:
        section = cfg_dict.get(name)
        return section if isinstance(section, dict) else {}
    lower = str(name).lower()
    for key, section in cfg_dict.items():
        if str(key).lower() == lower and isinstance(section, dict):
            return section
    return {}


def _get_cfg_value(section: dict, key: str, default: object = None) -> object:
    """
    Best-effort case-insensitive config dict lookup.

    Many call sites build cfg_dict from ConfigParser where key casing can vary
    (e.g., ApplyTo vs applyto). This helper makes HumanHitSim knobs robust.
    """
    if not isinstance(section, dict):
        return default
    if key in section:
        return section.get(key, default)
    lk = str(key).lower()
    for k, v in section.items():
        try:
            if str(k).lower() == lk:
                return v
        except Exception:
            continue
    return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value) if value is not None else int(default)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return int(default)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else float(default)
    except Exception:
        try:
            return float(int(value))
        except Exception:
            return float(default)


def _derive_refine_seed_base(*, song_name: str, ga_seed: int | None, configured_base: int) -> int:
    base = int(configured_base or 0)
    if base == 0:
        song_crc = int(zlib.crc32(str(song_name or "").encode("utf-8", errors="replace")) & 0xFFFFFFFF)
        ga_seed_i = int(_safe_int(ga_seed, 0)) & 0xFFFFFFFF
        base = int((song_crc ^ ga_seed_i) & 0xFFFFFFFF)
    base &= 0xFFFFFFFF
    if base == 0:
        base = 1
    return int(base)


def _seed_with_trial_offset(base_seed: int, trial_idx: int) -> int:
    seed = (int(base_seed) + int(trial_idx)) & 0xFFFFFFFF
    if seed == 0:
        seed = 1
    return int(seed)


def compute_fever_timeline_signature(
    event_ms: np.ndarray,
    *,
    non_fever_base: int,
    real_fever_time_ms: int,
) -> tuple[tuple[int, int, int, bytes], np.ndarray, int, int]:
    """
    Build a compact score-relevant signature for fixed stats on one timestamp stream.

    For evaluate_stats_score(), score contribution depends on:
    - fever_mask_head (first up to 100 notes)
    - count_body_fever
    - count_body_normal
    For fixed base/combo/fever multipliers, identical values here imply identical score.
    """
    ev = np.asarray(event_ms, dtype=np.int32)
    total_notes = int(ev.shape[0])
    head_limit = min(total_notes, 100)
    fever_mask_head = np.zeros(head_limit, dtype=np.bool_)

    current_note_idx = 0
    fever_section = 0
    count_body_fever = 0
    while current_note_idx < total_notes:
        fever_section += 1
        notes_to_fill = int(non_fever_base) - 1 if fever_section == 1 else int(non_fever_base)
        end_normal_idx = current_note_idx + notes_to_fill
        if end_normal_idx > total_notes:
            end_normal_idx = total_notes
        current_note_idx = end_normal_idx
        if current_note_idx >= total_notes:
            break

        if current_note_idx > 0:
            fever_start = int(current_note_idx)
            end_ms = int(ev[fever_start]) + int(real_fever_time_ms)
            fever_end_idx = int(np.searchsorted(ev, end_ms, side="left"))

            if fever_start < head_limit:
                head_s = max(0, fever_start)
                head_e = min(head_limit, fever_end_idx)
                if head_e > head_s:
                    fever_mask_head[head_s:head_e] = True

            if fever_end_idx > 100:
                body_start = max(100, fever_start)
                if fever_end_idx > body_start:
                    count_body_fever += int(fever_end_idx - body_start)

            current_note_idx = fever_end_idx
        else:
            break

    count_body_normal = max(0, int(total_notes - head_limit - int(count_body_fever)))
    head_u8 = np.asarray(fever_mask_head, dtype=np.uint8)
    packed_head = np.packbits(head_u8, bitorder="little")
    signature = (
        int(head_u8.shape[0]),
        int(count_body_fever),
        int(count_body_normal),
        bytes(packed_head.tobytes()),
    )
    return signature, fever_mask_head, int(count_body_fever), int(count_body_normal)


# Back-compat for in-progress experiment callers/tests.
_timeline_signature_for_fixed_stats = compute_fever_timeline_signature


def prepare_perfect_hit_simulation(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    perfect_lower_ms: int,
    perfect_upper_ms: int,
    held_tail_type: int,
    held_tail_time_multiplier: int,
    quantize_ms: bool,
) -> dict:
    ts_sec = np.asarray(timestamps_sec, dtype=np.float64)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return {
            "n": 0,
            "ts_ms": np.zeros((0,), dtype=np.int32),
            "group_starts": np.zeros((0,), dtype=np.int32),
            "group_ends": np.zeros((0,), dtype=np.int32),
            "group_base_t": np.zeros((0,), dtype=np.int32),
            "group_low": np.zeros((0,), dtype=np.int32),
            "group_high": np.zeros((0,), dtype=np.int32),
        }

    if quantize_ms:
        ts_ms = _floor_to_int_ms(ts_sec)
    else:
        ts_ms = (ts_sec * 1000.0).astype(np.int32)

    if note_types is None or len(note_types) != n:
        nt = np.ones(n, dtype=np.int16)
    else:
        nt = np.asarray(note_types, dtype=np.int16)

    perfect_low_ms, perfect_high_ms = _build_per_note_perfect_window_ms(
        nt,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )

    if n == 1:
        group_starts = np.asarray([0], dtype=np.int32)
        group_ends = np.asarray([1], dtype=np.int32)
    else:
        boundaries = np.nonzero(ts_ms[1:] != ts_ms[:-1])[0].astype(np.int32) + 1
        group_count = int(boundaries.shape[0]) + 1
        group_starts = np.empty(group_count, dtype=np.int32)
        group_ends = np.empty(group_count, dtype=np.int32)
        group_starts[0] = 0
        if group_count > 1:
            group_starts[1:group_count] = boundaries
            group_ends[: group_count - 1] = boundaries
        group_ends[group_count - 1] = int(n)

    group_count = int(group_starts.shape[0])
    group_base_t = ts_ms[group_starts].astype(np.int32, copy=False)
    group_low = np.empty(group_count, dtype=np.int32)
    group_high = np.empty(group_count, dtype=np.int32)
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        g_low = int(np.max(perfect_low_ms[s:e]))
        g_high = int(np.min(perfect_high_ms[s:e]))
        if g_low > g_high:
            g_low, g_high = g_high, g_low
        group_low[g] = g_low
        group_high[g] = g_high

    return {
        "n": int(n),
        "ts_ms": ts_ms.astype(np.int32, copy=False),
        "group_starts": group_starts,
        "group_ends": group_ends,
        "group_base_t": group_base_t,
        "group_low": group_low,
        "group_high": group_high,
    }


# Back-compat for in-progress experiment callers/tests.
_prepare_perfect_hit_simulation = prepare_perfect_hit_simulation


def generate_perfect_hit_times_ms(prepared: dict, *, seed: int) -> np.ndarray:
    """
    Fast path: generate Perfect event times in integer ms for a prepared chart.

    Returned array is a view into a thread-local buffer; callers must treat it
    as ephemeral and consume it immediately.
    """
    n = int(prepared.get("n", 0) or 0)
    if n <= 0:
        return np.zeros((0,), dtype=np.int32)

    group_starts = np.asarray(prepared["group_starts"], dtype=np.int32)
    group_ends = np.asarray(prepared["group_ends"], dtype=np.int32)
    group_base_t = np.asarray(prepared["group_base_t"], dtype=np.int32)
    group_low = np.asarray(prepared["group_low"], dtype=np.int32)
    group_high = np.asarray(prepared["group_high"], dtype=np.int32)
    group_count = int(group_starts.shape[0])

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)

    _tls = getattr(generate_perfect_hit_times_ms, "_tls", None)
    if _tls is None:
        _tls = threading.local()
        setattr(generate_perfect_hit_times_ms, "_tls", _tls)

    event_ms = getattr(_tls, "event_ms", None)
    if event_ms is None or int(getattr(event_ms, "shape", (0,))[0]) < int(n):
        event_ms = np.empty(int(n), dtype=np.int32)
        setattr(_tls, "event_ms", event_ms)
    event_ms = event_ms[:n]

    prev_event_ms: int | None = None
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(group_base_t[g])
        g_low = int(group_low[g])
        g_high = int(group_high[g])

        if prev_event_ms is None:
            eff_low = g_low
        else:
            required_off = int(prev_event_ms) - base_t
            eff_low = max(g_low, required_off)

        if eff_low <= g_high:
            off = int(rng.integers(eff_low, g_high + 1, endpoint=False))
        else:
            off = g_high
            if prev_event_ms is not None and base_t + off < int(prev_event_ms):
                off = int(prev_event_ms) - base_t

        event = base_t + off
        event_ms[s:e] = event
        prev_event_ms = event

    return event_ms

def plan_human_hit_sim(calc_song: dict, *, cfg_dict: dict) -> dict | None:
    """
    Plan (but do not execute) HumanHitSim.

    This is a CPU-optimization hook for in-flight mode:
    - If ApplyTo=ALL, the timestamps must be simulated up-front (affects GA scoring).
    - If ApplyTo=FG, we can defer the expensive simulation until the FG stage actually runs.

    Planning selects/records the seed + knobs so deferred application is deterministic.
    Returns a summary dict when planned, or None if disabled/invalid.
    """
    if not isinstance(calc_song, dict):
        return None
    meta = calc_song.get("metadata", {}) or {}
    if meta.get("HumanHitSimApplied") or meta.get("HumanHitSimPlanned"):
        return None

    human_cfg = _get_cfg_section(cfg_dict, "HumanHitSim")
    if not _truthy(_get_cfg_value(human_cfg, "Enabled", _get_cfg_value(human_cfg, "enabled", "0"))):
        return None

    song_data = calc_song.get("song_data", {}) or {}
    if song_data.get("timestamps") is None:
        return None

    apply_to = str(_get_cfg_value(human_cfg, "ApplyTo", _get_cfg_value(human_cfg, "applyto", "FG"))).strip().upper()
    if apply_to not in {"FG", "ALL"}:
        apply_to = "FG"

    try:
        seed_in = int(str(_get_cfg_value(human_cfg, "Seed", _get_cfg_value(human_cfg, "seed", "0")) or "0"))
    except Exception:
        seed_in = 0

    dist = (
        str(_get_cfg_value(human_cfg, "Distribution", _get_cfg_value(human_cfg, "distribution", "uniform")))
        .strip()
        .lower()
    )
    great_mode = (
        str(_get_cfg_value(human_cfg, "GreatMode", _get_cfg_value(human_cfg, "greatmode", "late"))).strip().lower()
    )

    seed_is_random = False
    if seed_in == 0:
        if _env_debug_fixed_seeds_enabled():
            env_seed = _env_debug_human_hit_sim_seed()
            seed_in = int(env_seed) if env_seed is not None else 1337
        else:
            refine_after = _truthy(
                _get_cfg_value(human_cfg, "RefineAfterGA", _get_cfg_value(human_cfg, "refineafterga", "0"))
            )
            refine_trials = _safe_int(
                _get_cfg_value(human_cfg, "RefineTrials", _get_cfg_value(human_cfg, "refinetrials", "0")), 0
            )
            if apply_to == "ALL" and refine_after and refine_trials > 0:
                song_crc = int(zlib.crc32(str(meta.get("Song Name", "") or "").encode("utf-8", errors="replace")))
                seed_in = int(song_crc & 0xFFFFFFFF) or 1
                seed_is_random = False
            else:
                seed_in = secrets.randbits(32)
                seed_is_random = True

    # Record planning info (but do NOT generate fg arrays yet).
    meta = copy.deepcopy(meta)
    meta["HumanHitSimSeed"] = int(seed_in)
    meta["HumanHitSimApplyTo"] = apply_to
    meta["HumanHitSimDistribution"] = dist
    meta["HumanHitSimGreatMode"] = great_mode
    meta["HumanHitSimSeedIsRandom"] = bool(seed_is_random)
    meta["HumanHitSimPlanned"] = True
    calc_song["metadata"] = meta
    return {
        "apply_to": apply_to,
        "distribution": dist,
        "seed": int(seed_in),
        "great_mode": great_mode,
        "planned": True,
    }


def apply_human_hit_sim(calc_song: dict, *, cfg_dict: dict) -> dict | None:
    """
    Apply HumanHitSim to calc_song in-place if enabled.

    Returns a summary dict when applied, or None if disabled/invalid.
    """
    if not isinstance(calc_song, dict):
        return None
    meta = calc_song.get("metadata", {}) or {}
    if meta.get("HumanHitSimApplied"):
        return None

    human_cfg = _get_cfg_section(cfg_dict, "HumanHitSim")
    if not _truthy(_get_cfg_value(human_cfg, "Enabled", _get_cfg_value(human_cfg, "enabled", "0"))):
        return None

    song_data = calc_song.get("song_data", {}) or {}
    if song_data.get("timestamps") is None:
        return None

    apply_to = str(_get_cfg_value(human_cfg, "ApplyTo", _get_cfg_value(human_cfg, "applyto", "FG"))).strip().upper()
    if apply_to not in {"FG", "ALL"}:
        apply_to = "FG"

    planned_seed = None
    if meta.get("HumanHitSimPlanned") and ("HumanHitSimSeed" in meta):
        try:
            planned_seed = int(meta.get("HumanHitSimSeed") or 0)
        except Exception:
            planned_seed = None
        if planned_seed is not None and planned_seed <= 0:
            planned_seed = None

    try:
        seed_in = int(str(_get_cfg_value(human_cfg, "Seed", _get_cfg_value(human_cfg, "seed", "0")) or "0"))
    except Exception:
        seed_in = 0

    dist = (
        str(_get_cfg_value(human_cfg, "Distribution", _get_cfg_value(human_cfg, "distribution", "uniform")))
        .strip()
        .lower()
    )
    great_mode = (
        str(_get_cfg_value(human_cfg, "GreatMode", _get_cfg_value(human_cfg, "greatmode", "late"))).strip().lower()
    )

    seed_is_random = False
    if planned_seed is not None:
        seed_in = int(planned_seed)
        seed_is_random = bool(meta.get("HumanHitSimSeedIsRandom"))
    elif seed_in == 0:
        if _env_debug_fixed_seeds_enabled():
            env_seed = _env_debug_human_hit_sim_seed()
            seed_in = int(env_seed) if env_seed is not None else 1337
        else:
            refine_after = _truthy(
                _get_cfg_value(human_cfg, "RefineAfterGA", _get_cfg_value(human_cfg, "refineafterga", "0"))
            )
            refine_trials = _safe_int(
                _get_cfg_value(human_cfg, "RefineTrials", _get_cfg_value(human_cfg, "refinetrials", "0")), 0
            )
            if apply_to == "ALL" and refine_after and refine_trials > 0:
                song_crc = int(zlib.crc32(str(meta.get("Song Name", "") or "").encode("utf-8", errors="replace")))
                seed_in = int(song_crc & 0xFFFFFFFF) or 1
                seed_is_random = False
            else:
                seed_in = secrets.randbits(32)
                seed_is_random = True

    chart_ts = song_data.get("chart_timestamps")
    if chart_ts is None:
        chart_ts = song_data.get("timestamps", ())
        song_data["chart_timestamps"] = np.asarray(chart_ts, dtype=np.float64)
    base_ts = np.asarray(chart_ts, dtype=np.float64)
    base_types = np.asarray(song_data.get("note_types", ()), dtype=np.int16)
    if base_types.shape[0] != base_ts.shape[0]:
        base_types = np.ones(base_ts.shape[0], dtype=np.int16)

    sim_ts, sim_great_candidates, sim_dbg = simulate_perfect_hit_timestamps_with_great_candidates(
        base_ts,
        base_types,
        seed=seed_in,
        distribution=dist,
        great_mode=great_mode,
    )

    song_data["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
    song_data["fg_great_candidate_timestamps"] = np.asarray(sim_great_candidates, dtype=np.float64)
    meta = copy.deepcopy(meta)
    meta["HumanHitSimSeed"] = int(seed_in)
    meta["HumanHitSimApplyTo"] = apply_to
    meta["HumanHitSimDistribution"] = dist
    meta["HumanHitSimGreatMode"] = great_mode
    meta["HumanHitSimSeedIsRandom"] = bool(seed_is_random)
    meta["HumanHitSimDebug"] = sim_dbg
    meta["HumanHitSimApplied"] = True
    meta.pop("HumanHitSimPlanned", None)
    calc_song["metadata"] = meta
    calc_song["song_data"] = song_data

    if apply_to == "ALL":
        song_data["timestamps"] = np.asarray(sim_ts, dtype=np.float64)

    return {
        "apply_to": apply_to,
        "distribution": dist,
        "seed": int(seed_in),
        "great_mode": great_mode,
        "debug": sim_dbg,
    }


def refine_human_hit_sim_after_ga(
    calc_song: dict,
    *,
    cfg_dict: dict,
    best_data: dict,
    ref_arrays: dict,
    ga_seed: int | None = None,
) -> dict | None:
    """
    Post-GA HumanHitSim refinement (best-of-N seeds) for ApplyTo=ALL.

    This evaluates multiple deterministic seeds against a fixed stats snapshot and
    applies the best timestamps back into `calc_song` before persistence.
    """
    if not isinstance(calc_song, dict) or not isinstance(best_data, dict) or not isinstance(ref_arrays, dict):
        return None

    human_cfg = _get_cfg_section(cfg_dict, "HumanHitSim")
    if not _truthy(_get_cfg_value(human_cfg, "Enabled", _get_cfg_value(human_cfg, "enabled", "0"))):
        return None

    apply_to = str(_get_cfg_value(human_cfg, "ApplyTo", _get_cfg_value(human_cfg, "applyto", "FG"))).strip().upper()
    if apply_to != "ALL":
        return None

    if not _truthy(_get_cfg_value(human_cfg, "RefineAfterGA", _get_cfg_value(human_cfg, "refineafterga", "0"))):
        return None

    trials = _safe_int(_get_cfg_value(human_cfg, "RefineTrials", _get_cfg_value(human_cfg, "refinetrials", "0")), 0)
    if trials <= 0:
        return None

    stats = best_data.get("Stats")
    if not isinstance(stats, dict) or not stats:
        return None

    song_data = calc_song.get("song_data", {}) or {}
    meta0 = calc_song.get("metadata", {}) or {}
    if not isinstance(song_data, dict) or not isinstance(meta0, dict):
        return None

    chart_ts = song_data.get("chart_timestamps")
    if chart_ts is None:
        chart_ts = song_data.get("timestamps")
    if chart_ts is None:
        return None
    base_ts = np.asarray(chart_ts, dtype=np.float64)
    if int(base_ts.shape[0]) <= 0:
        return None

    note_types = np.asarray(song_data.get("note_types", ()), dtype=np.int16)
    if note_types.shape[0] != base_ts.shape[0]:
        note_types = np.ones(base_ts.shape[0], dtype=np.int16)

    dist = str(_get_cfg_value(human_cfg, "Distribution", _get_cfg_value(human_cfg, "distribution", "uniform"))).strip().lower()
    great_mode = str(_get_cfg_value(human_cfg, "GreatMode", _get_cfg_value(human_cfg, "greatmode", "late"))).strip().lower()

    prev_score = _safe_int(best_data.get("BaseScore", best_data.get("Score", 0)), 0)

    current_ts = song_data.get("timestamps")
    if current_ts is None:
        current_ts = base_ts
    current_ts_np = np.asarray(current_ts, dtype=np.float64)
    current_fg_ts_np = np.asarray(song_data.get("fg_timestamps", current_ts_np), dtype=np.float64)
    current_fg_gc_np = np.asarray(song_data.get("fg_great_candidate_timestamps", current_fg_ts_np), dtype=np.float64)
    current_seed = _safe_int(meta0.get("HumanHitSimSeed", 0), 0)

    refine_seed_base_cfg = _safe_int(
        _get_cfg_value(human_cfg, "RefineSeedBase", _get_cfg_value(human_cfg, "refineseedbase", "0")),
        0,
    )
    derived_seed_base = _derive_refine_seed_base(
        song_name=str(meta0.get("Song Name", "") or ""),
        ga_seed=ga_seed,
        configured_base=int(refine_seed_base_cfg),
    )
    if current_seed <= 0:
        current_seed = int(derived_seed_base)

    unique_scores: set[int] = {int(prev_score)}
    best_score = int(prev_score)
    best_seed = int(current_seed)
    best_ts = current_fg_ts_np
    best_gc = current_fg_gc_np

    fever_fill_rate = lookup_reference_py(stats.get("Fever Fill Rate", 0), ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats.get("Fever Time", 0), ref_arrays["Fever Time"], TOTAL_ROWS)
    base_pp = lookup_reference_py(stats.get("Perfect Points", 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats.get("Combo Multiplier", 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats.get("Fever Multiplier", 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS)
    p_color = str(meta0.get("Primary Color", "") or "")
    s_color = str(meta0.get("Secondary Color", "") or "")
    primary_val = _safe_int(stats.get(p_color, 0), 0)
    secondary_val = _safe_int(stats.get(s_color, 0), 0)
    total_base = (int(primary_val) * 2) + int(secondary_val) + float(base_pp)
    long_count = _safe_int(meta0.get("Long Notes", 0), 0)
    default_last_note = float(base_ts[-1]) if int(base_ts.shape[0]) > 0 else 0.0
    last_note_time = _safe_float(meta0.get("Last Note Time", default_last_note), default_last_note)
    non_fever_cas = (int(base_ts.shape[0]) - int(long_count)) * float(FEVER_FILL_BASE_RATE)
    non_fever_base = int(np.ceil(float(non_fever_cas) * float(fever_fill_rate)))
    fever_time_cas = float(last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    real_fever_time = float(fever_time_cas) * float(fever_time_stat)
    real_fever_time_ms = int(np.ceil(float(real_fever_time) * 1000.0 - 1e-9))
    if real_fever_time_ms < 0:
        real_fever_time_ms = 0

    prepared = prepare_perfect_hit_simulation(
        base_ts,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )

    seen_timeline_signatures: set[tuple[int, int, int, bytes]] = set()
    evaluated_trials = 0
    skipped_timeline_duplicates = 0

    for trial_idx in range(int(trials)):
        seed = _seed_with_trial_offset(derived_seed_base, trial_idx)
        try:
            event_ms = generate_perfect_hit_times_ms(prepared, seed=int(seed))
            timeline_sig, fever_mask_head, count_body_fever, count_body_normal = compute_fever_timeline_signature(
                event_ms,
                non_fever_base=int(non_fever_base),
                real_fever_time_ms=int(real_fever_time_ms),
            )
            if timeline_sig in seen_timeline_signatures:
                skipped_timeline_duplicates += 1
                continue
            seen_timeline_signatures.add(timeline_sig)
            evaluated_trials += 1
            score = _safe_int(
                fast_calculate_score(
                    total_base,
                    combo_mul,
                    fever_mul,
                    fever_mask_head,
                    int(count_body_fever),
                    int(count_body_normal),
                ),
                0,
            )
        except Exception:
            continue
        unique_scores.add(int(score))
        if int(score) > int(best_score):
            best_score = int(score)
            best_seed = int(seed)

    # Never regress persisted score: keep prior winner if refinement does not improve.
    best_score = max(int(best_score), int(prev_score))

    need_apply = True
    if meta0.get("HumanHitSimApplied") and int(_safe_int(meta0.get("HumanHitSimSeed", 0), 0)) == int(best_seed):
        if isinstance(song_data.get("fg_timestamps"), np.ndarray) and isinstance(song_data.get("fg_great_candidate_timestamps"), np.ndarray):
            need_apply = False

    if need_apply:
        sim_ts, sim_gc, _sim_dbg = simulate_perfect_hit_timestamps_with_great_candidates(
            base_ts,
            note_types,
            seed=int(best_seed),
            distribution=dist,
            great_mode=great_mode,
        )
        best_ts = np.asarray(sim_ts, dtype=np.float64)
        best_gc = np.asarray(sim_gc, dtype=np.float64)

    song_data["fg_timestamps"] = np.asarray(best_ts, dtype=np.float64)
    song_data["fg_great_candidate_timestamps"] = np.asarray(best_gc, dtype=np.float64)
    song_data["timestamps"] = np.asarray(best_ts, dtype=np.float64)
    calc_song["song_data"] = song_data

    meta = copy.deepcopy(meta0)
    meta["HumanHitSimSeed"] = int(best_seed)
    meta["HumanHitSimApplyTo"] = "ALL"
    meta["HumanHitSimDistribution"] = dist
    meta["HumanHitSimGreatMode"] = great_mode
    meta["HumanHitSimSeedIsRandom"] = False
    meta["HumanHitSimApplied"] = True
    meta["HumanHitSimRefined"] = True
    meta["HumanHitSimRefineTrials"] = int(trials)
    meta["HumanHitSimRefineBestSeed"] = int(best_seed)
    meta["HumanHitSimRefineBestScore"] = int(best_score)
    meta["HumanHitSimRefinePrevScore"] = int(prev_score)
    meta["HumanHitSimRefineUniqueScores"] = int(len(unique_scores))
    meta["HumanHitSimRefineEvaluatedTrials"] = int(evaluated_trials)
    meta["HumanHitSimRefineTimelineVariants"] = int(len(seen_timeline_signatures))
    meta["HumanHitSimRefineSkippedTimelineDuplicates"] = int(skipped_timeline_duplicates)
    meta.pop("HumanHitSimPlanned", None)
    calc_song["metadata"] = meta

    best_data["Score"] = int(best_score)
    best_data["BaseScore"] = int(best_score)

    return {
        "best_seed": int(best_seed),
        "best_score": int(best_score),
        "prev_score": int(prev_score),
        "trials": int(trials),
        "unique_scores": int(len(unique_scores)),
        "evaluated_trials": int(evaluated_trials),
        "timeline_variants": int(len(seen_timeline_signatures)),
        "skipped_timeline_duplicates": int(skipped_timeline_duplicates),
    }


def simulate_perfect_hit_timestamps_with_great_candidates(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray | None,
    *,
    seed: int,
    distribution: str = "uniform",
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    great_lower_ms: int = -75,
    great_extra_upper_ms: int = 150,
    great_mode: str = "late",
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Generate:
    - Perfect event times (monotonic, chord-grouped)
    - Great-candidate times (sampled from Great window based on great_mode)

    "Great-candidate" is intentionally *not* monotonic by itself; monotonicity is
    handled in FG timeline simulation via a carry (prefix-max) rule:
      effective_time[i] = max(perfect_event_time[i], max(great_candidate_time[j] for forced j<=i))

    In the game code, "GreatTime" is an *extension beyond Perfect* (see
    `GearStats.get_note_times`), so Great's upper bound is:
      great_upper = perfect_upper + great_extra_upper

    Args:
        great_mode: Great timing mode for forced greats simulation:
            - "late": Late-only Great band [perfect_upper+1, great_upper] (default)
            - "early": Early-only Great band [great_lower, perfect_lower-1]
            - "full": Full Great window [great_lower, great_upper]

    Great offsets are sampled from the configured band with held tails using x2 multiplier.
    """
    if distribution != "uniform":
        raise ValueError(f"Unsupported HumanHitSim distribution: {distribution!r}")
    if great_mode not in ("early", "late", "full"):
        raise ValueError(f"Unsupported great_mode: {great_mode!r}. Must be 'early', 'late', or 'full'")
    if int(great_extra_upper_ms) < 0:
        raise ValueError("great_extra_upper_ms must be >= 0")

    ts_sec = np.asarray(timestamps_sec, dtype=np.float64)
    n = int(ts_sec.shape[0])
    if n == 0:
        empty = ts_sec.astype(np.float64)
        return empty, empty, {"notes": 0, "groups": 0, "forced_monotonic": 0}

    if quantize_ms:
        ts_ms = _floor_to_int_ms(ts_sec)
    else:
        ts_ms = (ts_sec * 1000.0).astype(np.int32)

    if note_types is None or len(note_types) != n:
        note_types = np.ones(n, dtype=np.int16)
    else:
        note_types = np.asarray(note_types, dtype=np.int16)

    # Perfect windows per note (ms, with tail multiplier).
    perfect_low_ms, perfect_high_ms = _build_per_note_perfect_window_ms(
        note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )

    # Great window per note (ms, with tail multiplier) - mode-based.
    is_tail = note_types == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int16)

    # Calculate Great window bounds based on mode
    great_upper_ms = ((int(perfect_upper_ms) + int(great_extra_upper_ms)) * mult).astype(np.int32)

    if great_mode == "late":
        # Late-only: [perfect_upper+1, great_upper]
        great_low_ms = (int(perfect_upper_ms) * mult + 1).astype(np.int32)
        great_high_ms = great_upper_ms
    elif great_mode == "early":
        # Early-only: [great_lower, perfect_lower-1]
        # In `GearStats.get_note_times`, Great extends Perfect on the early side too:
        #   great_lower_abs = perfect_lower + great_lower_extra
        perfect_low_abs_ms = perfect_low_ms.astype(np.int32)
        great_low_abs_ms = perfect_low_abs_ms + (int(great_lower_ms) * mult).astype(np.int32)
        great_low_ms = great_low_abs_ms
        great_high_ms = perfect_low_abs_ms - 1
    elif great_mode == "full":
        # Full window: [great_lower, great_upper]
        # See note above for early-side absolute lower bound.
        perfect_low_abs_ms = perfect_low_ms.astype(np.int32)
        great_low_abs_ms = perfect_low_abs_ms + (int(great_lower_ms) * mult).astype(np.int32)
        great_low_ms = great_low_abs_ms
        great_high_ms = great_upper_ms
    else:
        raise ValueError(f"Invalid great_mode: {great_mode}")

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)

    # PERF: reduce allocations in hot path (thread-local buffers).
    # This does NOT cache HitSim outputs between repeats; it only reuses scratch arrays.
    _tls = getattr(simulate_perfect_hit_timestamps_with_great_candidates, "_tls", None)
    if _tls is None:
        _tls = threading.local()
        setattr(simulate_perfect_hit_timestamps_with_great_candidates, "_tls", _tls)

    def _buf(name: str, dtype, size: int) -> np.ndarray:
        arr = getattr(_tls, name, None)
        if arr is None or int(getattr(arr, "shape", (0,))[0]) < int(size):
            arr = np.empty(int(size), dtype=dtype)
            setattr(_tls, name, arr)
        return arr

    # Chord grouping by identical timestamp_ms runs.
    # Vectorized boundary detection (much less Python looping than a nested while).
    if n == 1:
        group_starts = np.asarray([0], dtype=np.int32)
        group_ends = np.asarray([1], dtype=np.int32)
        group_count = 1
    else:
        boundaries = np.nonzero(ts_ms[1:] != ts_ms[:-1])[0].astype(np.int32) + 1
        group_count = int(boundaries.shape[0]) + 1
        starts = _buf("group_starts", np.int32, group_count)
        ends = _buf("group_ends", np.int32, group_count)
        starts[0] = 0
        if group_count > 1:
            starts[1:group_count] = boundaries
            ends[: group_count - 1] = boundaries
        ends[group_count - 1] = int(n)
        group_starts = starts[:group_count]
        group_ends = ends[:group_count]

    # Perfect event times (monotonic per chord group).
    perfect_event_ms = _buf("perfect_event_ms", np.int32, n)[:n]
    prev_event_ms: int | None = None
    forced_monotonic = 0

    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(ts_ms[s])

        g_low = int(np.max(perfect_low_ms[s:e]))
        g_high = int(np.min(perfect_high_ms[s:e]))
        if g_low > g_high:
            g_low, g_high = g_high, g_low

        if prev_event_ms is None:
            eff_low = g_low
        else:
            required_off = int(prev_event_ms) - base_t
            eff_low = max(g_low, required_off)

        if eff_low <= g_high:
            off = int(rng.integers(eff_low, g_high + 1, endpoint=False))
        else:
            off = g_high
            if prev_event_ms is not None and base_t + off < int(prev_event_ms):
                off = int(prev_event_ms) - base_t
                forced_monotonic += 1

        event_ms = base_t + off
        perfect_event_ms[s:e] = event_ms
        prev_event_ms = event_ms

    # Great-candidate times (chord-grouped, no monotonic clamp).
    great_candidate_ms = _buf("great_candidate_ms", np.int32, n)[:n]
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(ts_ms[s])

        g_low = int(np.max(great_low_ms[s:e]))
        g_high = int(np.min(great_high_ms[s:e]))
        if g_low > g_high:
            # No late-only Great band available (shouldn't happen for stat=0),
            # fall back to "latest perfect" to avoid invalid output.
            g_low = int(np.min(perfect_high_ms[s:e]))
            g_high = g_low

        off = int(rng.integers(g_low, g_high + 1, endpoint=False))
        great_candidate_ms[s:e] = base_t + off

    # PERF: avoid allocating intermediate float arrays from astype(); reuse thread-local buffers.
    out_perfect = _buf("perfect_sec", np.float64, n)[:n]
    out_great = _buf("great_sec", np.float64, n)[:n]
    np.multiply(perfect_event_ms, 0.001, out=out_perfect, casting="unsafe")
    np.multiply(great_candidate_ms, 0.001, out=out_great, casting="unsafe")
    debug = {"notes": n, "groups": int(group_count), "forced_monotonic": int(forced_monotonic)}
    # Return copies sized exactly to n (callers may store these long-term).
    return out_perfect.copy(), out_great.copy(), debug
