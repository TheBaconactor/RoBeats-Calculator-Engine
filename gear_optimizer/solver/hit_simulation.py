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

from ..core.time_quantize import quantize_to_int_ms


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
    # Keep float32-first quantization for CPU/GPU parity.
    return quantize_to_int_ms(timestamps_sec)


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


def _build_per_note_great_window_ms(
    note_types: np.ndarray,
    *,
    perfect_low_ms: np.ndarray,
    perfect_upper_ms: int,
    great_lower_ms: int,
    great_extra_upper_ms: int,
    great_mode: str,
    held_tail_type: int,
    held_tail_time_multiplier: int,
) -> tuple[np.ndarray, np.ndarray]:
    note_types = np.asarray(note_types, dtype=np.int16)
    is_tail = note_types == int(held_tail_type)
    mult = np.where(is_tail, int(held_tail_time_multiplier), 1).astype(np.int16)

    great_upper_abs_ms = ((int(perfect_upper_ms) + int(great_extra_upper_ms)) * mult).astype(np.int32)
    perfect_low_abs_ms = np.asarray(perfect_low_ms, dtype=np.int32)

    if great_mode == "late":
        great_low_abs_ms = (int(perfect_upper_ms) * mult + 1).astype(np.int32)
        great_high_abs_ms = great_upper_abs_ms
    elif great_mode == "early":
        great_low_abs_ms = perfect_low_abs_ms + (int(great_lower_ms) * mult).astype(np.int32)
        great_high_abs_ms = perfect_low_abs_ms - 1
    elif great_mode == "full":
        great_low_abs_ms = perfect_low_abs_ms + (int(great_lower_ms) * mult).astype(np.int32)
        great_high_abs_ms = great_upper_abs_ms
    else:
        raise ValueError(f"Invalid great_mode: {great_mode}")

    return great_low_abs_ms, great_high_abs_ms


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


def _copy_metadata_shallow(meta: object):
    """
    Copy metadata without recursively duplicating nested payloads.

    These call sites only update top-level scalar tags, so a shallow copy keeps
    the existing behavior while avoiding the cost of deepcopying large nested
    metadata blobs on every song/repeat.
    """
    try:
        if meta is None:
            return {}
        return dict(meta)
    except Exception:
        return copy.deepcopy(meta)


def _event_ms_to_sec(event_ms: np.ndarray) -> np.ndarray:
    out = np.asarray(event_ms, dtype=np.float32).copy()
    out *= np.float32(0.001)
    return out


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


def _prepare_grouped_hit_windows(
    timestamps_sec: np.ndarray,
    *,
    note_low_ms: np.ndarray,
    note_high_ms: np.ndarray,
    quantize_ms: bool,
) -> dict:
    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
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
        ts_ms = (ts_sec * np.float32(1000.0)).astype(np.int32)

    note_low_ms = np.asarray(note_low_ms, dtype=np.int32)
    note_high_ms = np.asarray(note_high_ms, dtype=np.int32)

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
    # Aggregate per-note timing windows into per-chord windows. Groups are a partition
    # of the notes by quantized chart timestamp, so we can use reduceat() instead of a
    # Python loop over groups.
    raw_low = np.maximum.reduceat(note_low_ms, group_starts)
    raw_high = np.minimum.reduceat(note_high_ms, group_starts)
    group_low = np.minimum(raw_low, raw_high).astype(np.int32, copy=False)
    group_high = np.maximum(raw_low, raw_high).astype(np.int32, copy=False)

    return {
        "n": int(n),
        "ts_ms": ts_ms.astype(np.int32, copy=False),
        "group_starts": group_starts,
        "group_ends": group_ends,
        "group_base_t": group_base_t,
        "group_low": group_low,
        "group_high": group_high,
    }


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
    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return _prepare_grouped_hit_windows(
            ts_sec,
            note_low_ms=np.zeros((0,), dtype=np.int32),
            note_high_ms=np.zeros((0,), dtype=np.int32),
            quantize_ms=quantize_ms,
        )

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
    return _prepare_grouped_hit_windows(
        ts_sec,
        note_low_ms=np.asarray(perfect_low_ms, dtype=np.int32),
        note_high_ms=np.asarray(perfect_high_ms, dtype=np.int32),
        quantize_ms=quantize_ms,
    )


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
            seed_in = secrets.randbits(32)
            seed_is_random = True

    # Record planning info (but do NOT generate fg arrays yet).
    meta = _copy_metadata_shallow(meta)
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
            seed_in = secrets.randbits(32)
            seed_is_random = True

    chart_ts = song_data.get("chart_timestamps")
    if chart_ts is None:
        chart_ts = song_data.get("timestamps", ())
        song_data["chart_timestamps"] = np.asarray(chart_ts, dtype=np.float32)
    base_ts = np.asarray(chart_ts, dtype=np.float32)
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

    song_data["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float32)
    song_data["fg_great_candidate_timestamps"] = np.asarray(sim_great_candidates, dtype=np.float32)
    meta = _copy_metadata_shallow(meta)
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
        ts_all = np.asarray(sim_ts, dtype=np.float32)
        song_data["timestamps"] = ts_all
        # Keep timeline cache keys stable/cheap by maintaining the signature when we mutate timestamps.
        try:
            from gear_optimizer.core.array_signature import array_sig16

            song_data["_timestamps_sig"] = array_sig16(ts_all)
        except Exception:
            song_data.pop("_timestamps_sig", None)

    return {
        "apply_to": apply_to,
        "distribution": dist,
        "seed": int(seed_in),
        "great_mode": great_mode,
        "debug": sim_dbg,
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

    ts_sec = np.asarray(timestamps_sec, dtype=np.float32)
    n = int(ts_sec.shape[0])
    if n == 0:
        empty = ts_sec.astype(np.float32, copy=False)
        return empty, empty, {"notes": 0, "groups": 0, "forced_monotonic": 0}

    if quantize_ms:
        ts_ms = _floor_to_int_ms(ts_sec)
    else:
        ts_ms = (ts_sec * np.float32(1000.0)).astype(np.int32)

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
    great_low_ms, great_high_ms = _build_per_note_great_window_ms(
        note_types,
        perfect_low_ms=perfect_low_ms,
        perfect_upper_ms=int(perfect_upper_ms),
        great_lower_ms=int(great_lower_ms),
        great_extra_upper_ms=int(great_extra_upper_ms),
        great_mode=str(great_mode),
        held_tail_type=int(held_tail_type),
        held_tail_time_multiplier=int(held_tail_time_multiplier),
    )

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
    out_perfect = _buf("perfect_sec", np.float32, n)[:n]
    out_great = _buf("great_sec", np.float32, n)[:n]
    # Avoid int32*float -> float64 promotion; do int->f32 cast first.
    out_perfect[:] = perfect_event_ms
    out_great[:] = great_candidate_ms
    out_perfect *= np.float32(0.001)
    out_great *= np.float32(0.001)
    debug = {"notes": n, "groups": int(group_count), "forced_monotonic": int(forced_monotonic)}
    # Return copies sized exactly to n (callers may store these long-term).
    return out_perfect.copy(), out_great.copy(), debug
