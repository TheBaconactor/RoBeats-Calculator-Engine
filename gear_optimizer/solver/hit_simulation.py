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
    if not _truthy(human_cfg.get("enabled", "0")):
        return None

    song_data = calc_song.get("song_data", {}) or {}
    if song_data.get("timestamps") is None:
        return None

    apply_to = str(human_cfg.get("applyto", "FG")).strip().upper()
    if apply_to not in {"FG", "ALL"}:
        apply_to = "FG"

    try:
        seed_in = int(str(human_cfg.get("seed", "0") or "0"))
    except Exception:
        seed_in = 0

    dist = str(human_cfg.get("distribution", "uniform")).strip().lower()
    great_mode = str(human_cfg.get("greatmode", "late")).strip().lower()

    if seed_in == 0:
        if _env_debug_fixed_seeds_enabled():
            env_seed = _env_debug_human_hit_sim_seed()
            seed_in = int(env_seed) if env_seed is not None else 1337
        else:
            seed_in = secrets.randbits(32)

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
    meta["HumanHitSimSeed"] = int(seed_in)
    meta["HumanHitSimApplyTo"] = apply_to
    meta["HumanHitSimDistribution"] = dist
    meta["HumanHitSimGreatMode"] = great_mode
    meta["HumanHitSimDebug"] = sim_dbg
    meta["HumanHitSimApplied"] = True
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

    # Chord grouping by identical timestamp_ms runs.
    group_starts = np.empty(n, dtype=np.int32)
    group_ends = np.empty(n, dtype=np.int32)
    group_count = 0
    i = 0
    while i < n:
        j = i + 1
        t = ts_ms[i]
        while j < n and ts_ms[j] == t:
            j += 1
        group_starts[group_count] = i
        group_ends[group_count] = j
        group_count += 1
        i = j

    group_starts = group_starts[:group_count]
    group_ends = group_ends[:group_count]

    # Perfect event times (monotonic per chord group).
    perfect_event_ms = np.empty(n, dtype=np.int32)
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

    # Great-candidate times (late-only band, chord-grouped, no monotonic clamp).
    great_candidate_ms = np.empty(n, dtype=np.int32)
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

    perfect_sec = perfect_event_ms.astype(np.float64) / 1000.0
    great_sec = great_candidate_ms.astype(np.float64) / 1000.0
    debug = {"notes": n, "groups": int(group_count), "forced_monotonic": int(forced_monotonic)}
    return perfect_sec, great_sec, debug
