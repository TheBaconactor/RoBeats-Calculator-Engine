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
from fractions import Fraction

from ..core.constants import TOTAL_ROWS, FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET
from ..core.time_quantize import quantize_to_int_ms
from .scoring_core import lookup_reference_py, fast_calculate_score


_BOUNDARY_DOMAIN_CACHE_LOCK = threading.Lock()
_BOUNDARY_DOMAIN_CACHE: dict[tuple, dict] = {}
_BOUNDARY_DOMAIN_CACHE_ORDER: list[tuple] = []
_BOUNDARY_DOMAIN_CACHE_MAX = 8
_EXACT_REGIME_PLAN_CACHE_LOCK = threading.Lock()
_EXACT_REGIME_PLAN_CACHE: dict[tuple, dict] = {}
_EXACT_REGIME_PLAN_CACHE_ORDER: list[tuple] = []
_EXACT_REGIME_PLAN_CACHE_MAX = 16


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


def _hash_reference_array(arr: np.ndarray) -> int:
    ref = np.asarray(arr, dtype=np.float32)
    return int(zlib.crc32(ref.tobytes()) & 0xFFFFFFFF)


def _hash_int32_array(arr: np.ndarray | list | tuple) -> int:
    ref = np.asarray(arr, dtype=np.int32)
    if ref.size <= 0:
        return 0
    return int(zlib.crc32(ref.tobytes()) & 0xFFFFFFFF)


def _normalize_hitsim_refine_mode(raw_mode: object) -> str:
    mode = str(raw_mode or "exact").strip().lower()
    if mode in {"table", "boundary_table", "analytical", "seed"}:
        return "exact"
    if mode != "exact":
        return "exact"
    return mode


def _normalize_hitsim_refine_device(raw_device: object) -> str:
    device = str(raw_device or "gpu").strip().lower()
    if device in {"cpu", "auto"}:
        return "gpu"
    if device != "gpu":
        return "gpu"
    return device


def _refine_stats_identity(stats: dict) -> tuple[tuple[str, int], ...]:
    if not isinstance(stats, dict):
        return ()
    out: list[tuple[str, int]] = []
    for key, value in stats.items():
        try:
            out.append((str(key), int(_safe_int(value, 0))))
        except Exception:
            continue
    out.sort(key=lambda item: item[0])
    return tuple(out)


def _build_refine_score_inputs(
    stats: dict,
    *,
    ref_arrays: dict,
    primary_color: str,
    secondary_color: str,
    total_notes: int,
    long_count: int,
    last_note_time: float,
) -> dict | None:
    if not isinstance(stats, dict) or not stats:
        return None

    fever_fill_rate = lookup_reference_py(stats.get("Fever Fill Rate", 0), ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats.get("Fever Time", 0), ref_arrays["Fever Time"], TOTAL_ROWS)
    base_pp = lookup_reference_py(stats.get("Perfect Points", 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats.get("Combo Multiplier", 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats.get("Fever Multiplier", 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS)

    primary_val = _safe_int(stats.get(primary_color, 0), 0)
    secondary_val = _safe_int(stats.get(secondary_color, 0), 0)
    total_base = (int(primary_val) * 2) + int(secondary_val) + float(base_pp)

    non_fever_cas = (int(total_notes) - int(long_count)) * float(FEVER_FILL_BASE_RATE)
    non_fever_base = int(np.ceil(float(non_fever_cas) * float(fever_fill_rate)))
    fever_time_cas = float(last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    real_fever_time = float(fever_time_cas) * float(fever_time_stat)
    real_fever_time_ms = int(np.ceil(float(real_fever_time) * 1000.0 - 1e-9))
    if real_fever_time_ms < 0:
        real_fever_time_ms = 0

    return {
        "non_fever_base": int(non_fever_base),
        "real_fever_time_ms": int(real_fever_time_ms),
        "timeline_key": (int(non_fever_base), int(real_fever_time_ms)),
        "total_base": float(total_base),
        "combo_mul": float(combo_mul),
        "fever_mul": float(fever_mul),
    }


def _build_full_ftff_boundary_domain(
    *,
    ref_arrays: dict,
    total_notes: int,
    long_count: int,
    last_note_time: float,
) -> dict:
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32)
    key = (
        int(total_notes),
        int(long_count),
        int(round(float(last_note_time) * 1000.0)),
        _hash_reference_array(ref_ft),
        _hash_reference_array(ref_ff),
    )

    with _BOUNDARY_DOMAIN_CACHE_LOCK:
        cached = _BOUNDARY_DOMAIN_CACHE.get(key)
        if cached is not None:
            return cached

    non_fever_cas = (int(total_notes) - int(long_count)) * FEVER_FILL_BASE_RATE
    fever_time_cas = float(last_note_time) * FEVER_TIME_SCALE + FEVER_TIME_OFFSET
    param_rows: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for ft_idx in range(int(TOTAL_ROWS) + 1):
        ft_factor = lookup_reference_py(ft_idx, ref_ft, TOTAL_ROWS)
        real_fever_time_ms = int(np.ceil(float(fever_time_cas * ft_factor) * 1000.0 - 1e-9))
        if real_fever_time_ms < 0:
            real_fever_time_ms = 0
        for ff_idx in range(int(TOTAL_ROWS) + 1):
            ff_factor = lookup_reference_py(ff_idx, ref_ff, TOTAL_ROWS)
            non_fever_base = int(np.ceil(float(non_fever_cas) * float(ff_factor)))
            row = (int(non_fever_base), int(real_fever_time_ms))
            if row in seen:
                continue
            seen.add(row)
            param_rows.append(row)

    payload = {
        "param_rows": tuple(param_rows),
        "full_pair_count": int((int(TOTAL_ROWS) + 1) * (int(TOTAL_ROWS) + 1)),
        "unique_param_count": int(len(param_rows)),
    }

    with _BOUNDARY_DOMAIN_CACHE_LOCK:
        _BOUNDARY_DOMAIN_CACHE[key] = payload
        _BOUNDARY_DOMAIN_CACHE_ORDER.append(key)
        while len(_BOUNDARY_DOMAIN_CACHE_ORDER) > int(_BOUNDARY_DOMAIN_CACHE_MAX):
            old_key = _BOUNDARY_DOMAIN_CACHE_ORDER.pop(0)
            _BOUNDARY_DOMAIN_CACHE.pop(old_key, None)
    return payload


def _collect_refine_candidates(
    *,
    best_data: dict,
    candidate_pool: list | None,
    candidate_limit: int,
    ref_arrays: dict,
    primary_color: str,
    secondary_color: str,
    total_notes: int,
    long_count: int,
    last_note_time: float,
) -> list[dict]:
    merged: dict[tuple[tuple[str, int], ...], dict] = {}

    raw_candidates = [
        {
            "entry": None,
            "data": best_data,
            "gear": None,
            "minis": None,
            "is_current": True,
            "base_score": _safe_int(best_data.get("BaseScore", best_data.get("Score", 0)), 0),
        }
    ]

    for entry in list(candidate_pool or []):
        if not isinstance(entry, dict):
            continue
        data = entry.get("Data")
        if not isinstance(data, dict):
            data = entry.get("data")
        if not isinstance(data, dict):
            continue
        raw_candidates.append(
            {
                "entry": entry,
                "data": data,
                "gear": entry.get("Gear", entry.get("gear")),
                "minis": entry.get("Minis", entry.get("minis")),
                "is_current": data is best_data,
                "base_score": _safe_int(
                    data.get("BaseScore", data.get("Score", entry.get("BaseScore", entry.get("Score", 0)))),
                    0,
                ),
            }
        )

    for row in raw_candidates:
        stats = row["data"].get("Stats")
        ident = _refine_stats_identity(stats)
        if not ident:
            continue
        score_inputs = _build_refine_score_inputs(
            stats,
            ref_arrays=ref_arrays,
            primary_color=primary_color,
            secondary_color=secondary_color,
            total_notes=int(total_notes),
            long_count=int(long_count),
            last_note_time=float(last_note_time),
        )
        if score_inputs is None:
            continue

        existing = merged.get(ident)
        if existing is None:
            merged[ident] = {
                "identity": ident,
                "entry": row["entry"],
                "data": row["data"],
                "gear": row["gear"],
                "minis": row["minis"],
                "is_current": bool(row["is_current"]),
                "base_score": int(row["base_score"]),
                "score_inputs": score_inputs,
            }
            continue

        if row["entry"] is not None and existing.get("entry") is None:
            existing["entry"] = row["entry"]
        if existing.get("gear") is None and row.get("gear") is not None:
            existing["gear"] = row.get("gear")
        if existing.get("minis") is None and row.get("minis") is not None:
            existing["minis"] = row.get("minis")
        if int(row["base_score"]) > int(existing.get("base_score", 0)):
            existing["base_score"] = int(row["base_score"])
            existing["data"] = row["data"]
            if row["entry"] is not None:
                existing["entry"] = row["entry"]
            if row.get("gear") is not None:
                existing["gear"] = row.get("gear")
            if row.get("minis") is not None:
                existing["minis"] = row.get("minis")
        existing["is_current"] = bool(existing.get("is_current")) or bool(row["is_current"])

    candidates = list(merged.values())
    candidates.sort(
        key=lambda row: (
            -int(row.get("base_score", 0)),
            0 if row.get("is_current") else 1,
        )
    )
    limit = max(1, int(candidate_limit))
    return candidates[:limit]


def _collect_signature_param_rows_for_candidates(refine_candidates: list[dict]) -> tuple[tuple[int, int], ...]:
    rows: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for candidate in list(refine_candidates or []):
        if not isinstance(candidate, dict):
            continue
        score_inputs = candidate.get("score_inputs") or {}
        try:
            key = tuple(score_inputs.get("timeline_key") or ())
        except Exception:
            key = ()
        if len(key) != 2:
            continue
        try:
            row = (int(key[0]), int(key[1]))
        except Exception:
            continue
        if row in seen:
            continue
        seen.add(row)
        rows.append(row)
    rows.sort(key=lambda row: (int(row[0]), int(row[1])))
    return tuple(rows)


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
    group_low = np.empty(group_count, dtype=np.int32)
    group_high = np.empty(group_count, dtype=np.int32)
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        g_low = int(np.max(note_low_ms[s:e]))
        g_high = int(np.min(note_high_ms[s:e]))
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


def _interpolate_group_offset(g_low: int, g_high: int, *, alpha_num: int, alpha_den: int) -> int:
    if alpha_den <= 0 or alpha_num <= 0:
        return int(g_low)
    if alpha_num >= alpha_den:
        return int(g_high)
    span = int(g_high) - int(g_low)
    if span <= 0:
        return int(g_low)
    return int(g_low) + int((int(span) * int(alpha_num) + int(alpha_den // 2)) // int(alpha_den))


def generate_deterministic_hit_times_ms(
    prepared: dict,
    *,
    alpha_num: int,
    alpha_den: int,
    monotonic: bool,
) -> tuple[np.ndarray, int]:
    n = int(prepared.get("n", 0) or 0)
    if n <= 0:
        return np.zeros((0,), dtype=np.int32), 0

    group_starts = np.asarray(prepared["group_starts"], dtype=np.int32)
    group_ends = np.asarray(prepared["group_ends"], dtype=np.int32)
    group_base_t = np.asarray(prepared["group_base_t"], dtype=np.int32)
    group_low = np.asarray(prepared["group_low"], dtype=np.int32)
    group_high = np.asarray(prepared["group_high"], dtype=np.int32)
    group_count = int(group_starts.shape[0])

    _tls = getattr(generate_deterministic_hit_times_ms, "_tls", None)
    if _tls is None:
        _tls = threading.local()
        setattr(generate_deterministic_hit_times_ms, "_tls", _tls)

    event_ms = getattr(_tls, "event_ms", None)
    if event_ms is None or int(getattr(event_ms, "shape", (0,))[0]) < int(n):
        event_ms = np.empty(int(n), dtype=np.int32)
        setattr(_tls, "event_ms", event_ms)
    event_ms = event_ms[:n]

    prev_event_ms: int | None = None
    forced_monotonic = 0
    for g in range(group_count):
        s = int(group_starts[g])
        e = int(group_ends[g])
        base_t = int(group_base_t[g])
        g_low = int(group_low[g])
        g_high = int(group_high[g])
        off = _interpolate_group_offset(g_low, g_high, alpha_num=int(alpha_num), alpha_den=int(alpha_den))
        event = base_t + int(off)
        if monotonic and prev_event_ms is not None and event < int(prev_event_ms):
            event = int(prev_event_ms)
            forced_monotonic += 1
        event_ms[s:e] = int(event)
        prev_event_ms = int(event)

    return event_ms, int(forced_monotonic)


def _event_ms_to_sec(event_ms: np.ndarray) -> np.ndarray:
    out = np.asarray(event_ms, dtype=np.float32).copy()
    out *= np.float32(0.001)
    return out


def _build_exact_alpha_regimes(*prepared_variants: dict) -> list[dict]:
    unique_spans: set[int] = set()
    for prepared in prepared_variants:
        if not isinstance(prepared, dict):
            continue
        group_low = np.asarray(prepared.get("group_low", ()), dtype=np.int32)
        group_high = np.asarray(prepared.get("group_high", ()), dtype=np.int32)
        if group_low.shape != group_high.shape:
            continue
        spans = np.asarray(group_high, dtype=np.int32) - np.asarray(group_low, dtype=np.int32)
        for span in spans.tolist():
            span_i = int(span)
            if span_i > 0:
                unique_spans.add(span_i)

    if not unique_spans:
        return [
            {
                "alpha_num": 1,
                "alpha_den": 2,
                "left_num": 0,
                "left_den": 1,
                "right_num": 1,
                "right_den": 1,
            }
        ]

    boundary_points: set[Fraction] = set()
    for span in sorted(unique_spans):
        for step in range(span):
            boundary = Fraction(2 * int(step) + 1, 2 * int(span))
            if Fraction(0, 1) < boundary < Fraction(1, 1):
                boundary_points.add(boundary)

    cuts = [Fraction(0, 1), *sorted(boundary_points), Fraction(1, 1)]
    regimes: list[dict] = []
    for left, right in zip(cuts[:-1], cuts[1:]):
        mid = (left + right) / 2
        regimes.append(
            {
                "alpha_num": int(mid.numerator),
                "alpha_den": int(mid.denominator),
                "left_num": int(left.numerator),
                "left_den": int(left.denominator),
                "right_num": int(right.numerator),
                "right_den": int(right.denominator),
            }
        )
    return regimes


def _serialize_regime_signature(signature_rows: tuple | list) -> int:
    crc = 0
    for row in list(signature_rows or ()):
        try:
            head_len, count_body_fever, count_body_normal, packed = _normalize_signature_row(row)
        except Exception:
            continue
        crc = zlib.crc32(int(head_len).to_bytes(2, "little", signed=False), crc)
        crc = zlib.crc32(int(count_body_fever).to_bytes(4, "little", signed=True), crc)
        crc = zlib.crc32(int(count_body_normal).to_bytes(4, "little", signed=True), crc)
        crc = zlib.crc32(bytes(packed), crc)
    return int(crc & 0xFFFFFFFF)


def _normalize_signature_row(row: tuple | list) -> tuple[int, int, int, bytes]:
    if len(row) >= 7 and not isinstance(row[3], (bytes, bytearray, memoryview)):
        head_len = int(row[0])
        packed_words = [int(row[idx]) & 0xFFFFFFFF for idx in range(3, min(len(row), 7))]
        while len(packed_words) < 4:
            packed_words.append(0)
        packed = b"".join(int(word).to_bytes(4, "little", signed=False) for word in packed_words)
        packed = packed[: max(0, (head_len + 7) // 8)]
        return (
            head_len,
            int(row[1]),
            int(row[2]),
            bytes(packed),
        )
    head_len, count_body_fever, count_body_normal, packed = row
    return (
        int(head_len),
        int(count_body_fever),
        int(count_body_normal),
        bytes(packed),
    )


def compute_fever_timeline_signature_compact(
    event_ms: np.ndarray,
    *,
    non_fever_base: int,
    real_fever_time_ms: int,
) -> tuple[int, int, int, int, int, int, int]:
    """
    Compact planner-only signature that avoids allocating a head mask array.

    The first 100-note fever mask is packed into four 32-bit words, which is
    enough to preserve exact equality for regime-family planning.
    """
    ev = np.asarray(event_ms, dtype=np.int32)
    total_notes = int(ev.shape[0])
    head_limit = min(total_notes, 100)
    packed_head = [0, 0, 0, 0]

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

        if current_note_idx <= 0:
            break

        fever_start = int(current_note_idx)
        end_ms = int(ev[fever_start]) + int(real_fever_time_ms)
        fever_end_idx = int(np.searchsorted(ev, end_ms, side="left"))

        if fever_start < head_limit:
            head_s = max(0, fever_start)
            head_e = min(head_limit, fever_end_idx)
            for note_idx in range(head_s, head_e):
                packed_head[int(note_idx >> 5)] |= 1 << int(note_idx & 31)

        if fever_end_idx > 100:
            body_start = max(100, fever_start)
            if fever_end_idx > body_start:
                count_body_fever += int(fever_end_idx - body_start)

        current_note_idx = fever_end_idx

    count_body_normal = max(0, int(total_notes - head_limit - int(count_body_fever)))
    return (
        int(head_limit),
        int(count_body_fever),
        int(count_body_normal),
        int(packed_head[0]),
        int(packed_head[1]),
        int(packed_head[2]),
        int(packed_head[3]),
    )


def _compute_compact_timeline_signature_rows(
    event_ms: np.ndarray,
    *,
    signature_param_rows: tuple[tuple[int, int], ...] | list[tuple[int, int]] | None = None,
) -> tuple[tuple[int, int, int, int, int, int, int], ...]:
    rows = list(signature_param_rows or ())
    combined_timeline_sig: list[tuple[int, int, int, int, int, int, int]] = []
    for non_fever_base, real_fever_time_ms in rows:
        timeline_sig = compute_fever_timeline_signature_compact(
            event_ms,
            non_fever_base=int(non_fever_base),
            real_fever_time_ms=int(real_fever_time_ms),
        )
        combined_timeline_sig.append(timeline_sig)
    return tuple(combined_timeline_sig)


def _midpoint_fraction(*, left_num: int, left_den: int, right_num: int, right_den: int) -> Fraction:
    left = Fraction(int(left_num), max(1, int(left_den)))
    right = Fraction(int(right_num), max(1, int(right_den)))
    return (left + right) / 2


def _derive_regime_identity(
    *,
    song_name: str,
    mode_tag: str,
    family: str,
    left_num: int,
    left_den: int,
    right_num: int,
    right_den: int,
    signature_crc: int,
    dist: str,
    great_mode: str,
) -> str:
    token = (
        f"{mode_tag}|{song_name}|{family}|"
        f"{left_num}/{left_den}->{right_num}/{right_den}|"
        f"sig={int(signature_crc):08x}|{dist}|{great_mode}"
    )
    return f"{mode_tag}:{int(zlib.crc32(token.encode('utf-8', errors='replace')) & 0xFFFFFFFF):08x}"


def _select_planned_regimes(
    regimes: list[dict],
    *,
    max_regimes: int,
    selection_mode: str,
) -> list[dict]:
    limit = max(0, int(max_regimes))
    if limit <= 0 or len(regimes) <= limit:
        return list(regimes or [])

    mode = str(selection_mode or "all").strip().lower()
    if mode not in {"head", "even"}:
        mode = "even"
    if mode == "head":
        return list(regimes[:limit])

    if limit == 1:
        return [regimes[0]]
    selected_indices = {
        max(0, min(len(regimes) - 1, int(round((slot * (len(regimes) - 1)) / float(limit - 1)))))
        for slot in range(limit)
    }
    if len(selected_indices) < limit:
        for idx in range(len(regimes)):
            selected_indices.add(idx)
            if len(selected_indices) >= limit:
                break
    ordered_indices = sorted(selected_indices)
    return [regimes[idx] for idx in ordered_indices[:limit]]


def _plan_exact_boundary_regimes(
    *,
    prepared: dict,
    great_prepared: dict,
    signature_param_rows: tuple[tuple[int, int], ...] | list[tuple[int, int]],
    song_name: str,
    dist: str,
    great_mode: str,
    family_mode: str = "ftff_boundary_rows",
    max_regimes: int = 0,
    selection_mode: str = "all",
) -> dict:
    # `great_prepared` is kept for signature compatibility; the current exact
    # planner only needs the base-score surface.
    del great_prepared
    cache_key = (
        str(song_name or ""),
        str(dist or ""),
        str(great_mode or ""),
        str(family_mode or "ftff_boundary_rows"),
        int(prepared.get("n", 0) or 0),
        _hash_int32_array(prepared.get("group_starts", ())),
        _hash_int32_array(prepared.get("group_ends", ())),
        _hash_int32_array(prepared.get("group_base_t", ())),
        _hash_int32_array(prepared.get("group_low", ())),
        _hash_int32_array(prepared.get("group_high", ())),
        _hash_int32_array(signature_param_rows or ()),
    )
    with _EXACT_REGIME_PLAN_CACHE_LOCK:
        cached = _EXACT_REGIME_PLAN_CACHE.get(cache_key)
        if cached is not None:
            cached_core = copy.deepcopy(cached)
            selected_regimes = _select_planned_regimes(
                list(cached_core.get("regimes", ())),
                max_regimes=max_regimes,
                selection_mode=selection_mode,
            )
            return {
                "raw_interval_count": int(cached_core.get("raw_interval_count", 0)),
                "active_param_count": int(cached_core.get("active_param_count", 0)),
                "active_family_row_count": int(cached_core.get("active_family_row_count", 0)),
                "family_mode": str(cached_core.get("family_mode", family_mode or "ftff_boundary_rows") or "ftff_boundary_rows"),
                "regime_cap": int(max(0, int(max_regimes))),
                "selection_mode": str(selection_mode or "all"),
                "full_regime_count": int(cached_core.get("full_regime_count", len(cached_core.get("regimes", ()) or ()))),
                "selected_regime_count": int(len(selected_regimes)),
                "regimes": selected_regimes,
            }

    raw_regimes = _build_exact_alpha_regimes(prepared)
    raw_interval_count = 0
    raw_entries: list[dict] = []
    for raw_regime in raw_regimes:
        raw_interval_count += 1
        alpha_num = int(raw_regime["alpha_num"])
        alpha_den = int(raw_regime["alpha_den"])
        left_num = int(raw_regime["left_num"])
        left_den = int(raw_regime["left_den"])
        right_num = int(raw_regime["right_num"])
        right_den = int(raw_regime["right_den"])
        try:
            event_ms, _forced_monotonic = generate_deterministic_hit_times_ms(
                prepared,
                alpha_num=alpha_num,
                alpha_den=alpha_den,
                monotonic=True,
            )
            combined_sig = _compute_compact_timeline_signature_rows(
                event_ms,
                signature_param_rows=signature_param_rows,
            )
        except Exception:
            continue
        raw_entries.append(
            {
                "left_num": int(left_num),
                "left_den": int(left_den),
                "right_num": int(right_num),
                "right_den": int(right_den),
                "alpha_num": int(alpha_num),
                "alpha_den": int(alpha_den),
                "combined_sig": tuple(combined_sig),
            }
        )

    if not raw_entries:
        payload = {
            "raw_interval_count": int(raw_interval_count),
            "active_param_count": 0,
            "active_family_row_count": 0,
            "family_mode": str(family_mode or "ftff_boundary_rows"),
            "full_regime_count": 0,
            "regimes": [],
        }
        with _EXACT_REGIME_PLAN_CACHE_LOCK:
            _EXACT_REGIME_PLAN_CACHE[cache_key] = copy.deepcopy(payload)
            _EXACT_REGIME_PLAN_CACHE_ORDER.append(cache_key)
            while len(_EXACT_REGIME_PLAN_CACHE_ORDER) > int(_EXACT_REGIME_PLAN_CACHE_MAX):
                old_key = _EXACT_REGIME_PLAN_CACHE_ORDER.pop(0)
                _EXACT_REGIME_PLAN_CACHE.pop(old_key, None)
        return {
            "raw_interval_count": int(payload["raw_interval_count"]),
            "active_param_count": int(payload["active_param_count"]),
            "active_family_row_count": int(payload["active_family_row_count"]),
            "family_mode": str(payload["family_mode"]),
            "regime_cap": int(max(0, int(max_regimes))),
            "selection_mode": str(selection_mode or "all"),
            "full_regime_count": int(payload["full_regime_count"]),
            "selected_regime_count": 0,
            "regimes": [],
        }

    row_count = len(signature_param_rows or ())
    row_family_ids: list[list[int]] = []
    active_row_indices: list[int] = []
    for row_idx in range(int(row_count)):
        last_row_sig = None
        next_family_id = -1
        family_ids_for_row: list[int] = []
        for entry in raw_entries:
            combined_sig = tuple(entry.get("combined_sig", ()))
            row_sig = combined_sig[row_idx] if row_idx < len(combined_sig) else None
            if last_row_sig is None or row_sig != last_row_sig:
                next_family_id += 1
                last_row_sig = row_sig
            family_ids_for_row.append(int(next_family_id))
        row_family_ids.append(family_ids_for_row)
        if next_family_id > 0:
            active_row_indices.append(int(row_idx))

    active_param_count = int(len(active_row_indices))
    planned: list[dict] = []
    last_family_vector = None
    for raw_idx, entry in enumerate(raw_entries):
        left_num = int(entry["left_num"])
        left_den = int(entry["left_den"])
        right_num = int(entry["right_num"])
        right_den = int(entry["right_den"])
        combined_sig = tuple(entry.get("combined_sig", ()))
        active_family_vector = tuple(int(row_family_ids[row_idx][raw_idx]) for row_idx in active_row_indices)
        if planned and active_family_vector == last_family_vector:
            planned[-1]["right_num"] = int(right_num)
            planned[-1]["right_den"] = int(right_den)
            planned[-1]["raw_interval_count"] = int(planned[-1]["raw_interval_count"]) + 1
            mid = _midpoint_fraction(
                left_num=int(planned[-1]["left_num"]),
                left_den=int(planned[-1]["left_den"]),
                right_num=int(planned[-1]["right_num"]),
                right_den=int(planned[-1]["right_den"]),
            )
            planned[-1]["alpha_num"] = int(mid.numerator)
            planned[-1]["alpha_den"] = int(mid.denominator)
            continue

        if active_row_indices:
            regime_signature_rows = tuple(combined_sig[row_idx] for row_idx in active_row_indices)
        else:
            regime_signature_rows = tuple(combined_sig[:1])
        signature_crc = _serialize_regime_signature(regime_signature_rows)
        mid = _midpoint_fraction(
            left_num=left_num,
            left_den=left_den,
            right_num=right_num,
            right_den=right_den,
        )
        planned.append(
            {
                "family": str(family_mode or "ftff_boundary_rows"),
                "planner_family_mode": str(family_mode or "ftff_boundary_rows"),
                "scope": "ALL",
                "left_num": int(left_num),
                "left_den": int(left_den),
                "right_num": int(right_num),
                "right_den": int(right_den),
                "alpha_num": int(mid.numerator),
                "alpha_den": int(mid.denominator),
                "signature_crc": int(signature_crc),
                "raw_interval_count": 1,
                "active_param_count": int(active_param_count),
                "active_family_row_count": int(active_param_count),
                "regime_id": _derive_regime_identity(
                    song_name=str(song_name or ""),
                    mode_tag="exact",
                    family=str(family_mode or "ftff_boundary_rows"),
                    left_num=int(left_num),
                    left_den=int(left_den),
                    right_num=int(right_num),
                    right_den=int(right_den),
                    signature_crc=int(signature_crc),
                    dist=str(dist),
                    great_mode=str(great_mode),
                ),
            }
        )
        last_family_vector = active_family_vector
    selected_regimes = _select_planned_regimes(
        planned,
        max_regimes=max_regimes,
        selection_mode=selection_mode,
    )
    payload = {
        "raw_interval_count": int(raw_interval_count),
        "active_param_count": int(active_param_count),
        "active_family_row_count": int(active_param_count),
        "family_mode": str(family_mode or "ftff_boundary_rows"),
        "full_regime_count": int(len(planned)),
        "regimes": planned,
    }
    with _EXACT_REGIME_PLAN_CACHE_LOCK:
        _EXACT_REGIME_PLAN_CACHE[cache_key] = copy.deepcopy(payload)
        _EXACT_REGIME_PLAN_CACHE_ORDER.append(cache_key)
        while len(_EXACT_REGIME_PLAN_CACHE_ORDER) > int(_EXACT_REGIME_PLAN_CACHE_MAX):
            old_key = _EXACT_REGIME_PLAN_CACHE_ORDER.pop(0)
            _EXACT_REGIME_PLAN_CACHE.pop(old_key, None)
    return {
        "raw_interval_count": int(raw_interval_count),
        "active_param_count": int(active_param_count),
        "active_family_row_count": int(active_param_count),
        "family_mode": str(family_mode or "ftff_boundary_rows"),
        "regime_cap": int(max(0, int(max_regimes))),
        "selection_mode": str(selection_mode or "all"),
        "full_regime_count": int(len(planned)),
        "selected_regime_count": int(len(selected_regimes)),
        "regimes": selected_regimes,
    }


def _derive_deterministic_regime_seed(
    *,
    song_name: str,
    mode_tag: str,
    alpha_num: int,
    alpha_den: int,
    dist: str,
    great_mode: str,
) -> int:
    token = f"{mode_tag}|{song_name}|{alpha_num}/{alpha_den}|{dist}|{great_mode}"
    seed = int(zlib.crc32(token.encode("utf-8", errors="replace")) & 0xFFFFFFFF)
    return int(seed or 1)


def _build_refined_candidate_payload(
    *,
    candidate: dict,
    score: int,
    refine_mode: str,
    seed: int,
    regime_id: str,
    regime_family: str,
    regime_scope: str,
    alpha_num: int,
    alpha_den: int,
    left_num: int,
    left_den: int,
    right_num: int,
    right_den: int,
) -> dict:
    source_data = candidate.get("data")
    data = copy.deepcopy(source_data) if isinstance(source_data, dict) else {}
    data["Score"] = int(score)
    data["BaseScore"] = int(score)
    data["HumanHitSimRefineMode"] = str(refine_mode)
    data["HumanHitSimRefineBestScore"] = int(score)
    data["HumanHitSimSeed"] = int(seed)
    if int(alpha_den) > 0:
        data["HumanHitSimRegimeAlphaNumerator"] = int(alpha_num)
        data["HumanHitSimRegimeAlphaDenominator"] = int(alpha_den)
    if str(regime_id or "").strip():
        data["HumanHitSimRegimeId"] = str(regime_id)
    if str(regime_family or "").strip():
        data["HumanHitSimRegimeFamily"] = str(regime_family)
    if str(regime_scope or "").strip():
        data["HumanHitSimRegimeScope"] = str(regime_scope)
    if int(left_den) > 0:
        data["HumanHitSimRegimeLeftNumerator"] = int(left_num)
        data["HumanHitSimRegimeLeftDenominator"] = int(left_den)
    if int(right_den) > 0:
        data["HumanHitSimRegimeRightNumerator"] = int(right_num)
        data["HumanHitSimRegimeRightDenominator"] = int(right_den)

    entry = candidate.get("entry")
    payload = copy.deepcopy(entry) if isinstance(entry, dict) else {}
    payload["Score"] = int(score)
    payload["BaseScore"] = int(score)
    if candidate.get("gear") is not None:
        payload["Gear"] = copy.deepcopy(candidate.get("gear"))
    if candidate.get("minis") is not None:
        payload["Minis"] = copy.deepcopy(candidate.get("minis"))
    payload["Data"] = data
    if "data" in payload:
        payload["data"] = data
    if str(regime_id or "").strip():
        payload["HumanHitSimRegimeId"] = str(regime_id)
    if str(regime_family or "").strip():
        payload["HumanHitSimRegimeFamily"] = str(regime_family)
    if str(regime_scope or "").strip():
        payload["HumanHitSimRegimeScope"] = str(regime_scope)
    return payload


def _record_refine_regime_result(
    *,
    regime_winners: list[dict],
    merged_by_identity: dict[tuple, dict],
    candidate: dict,
    score: int,
    refine_mode: str,
    seed: int,
    regime_id: str,
    regime_family: str,
    regime_scope: str,
    alpha_num: int,
    alpha_den: int,
    left_num: int,
    left_den: int,
    right_num: int,
    right_den: int,
    candidate_idx: int,
) -> None:
    payload = _build_refined_candidate_payload(
        candidate=candidate,
        score=int(score),
        refine_mode=str(refine_mode),
        seed=int(seed),
        regime_id=str(regime_id or ""),
        regime_family=str(regime_family or ""),
        regime_scope=str(regime_scope or ""),
        alpha_num=int(alpha_num),
        alpha_den=int(alpha_den),
        left_num=int(left_num),
        left_den=int(left_den),
        right_num=int(right_num),
        right_den=int(right_den),
    )
    payload["HumanHitSimRefineCandidateIndex"] = int(candidate_idx)
    regime_winners.append(payload)

    ident = tuple(candidate.get("identity") or ()) or (("__candidate_idx__", int(candidate_idx)),)
    existing = merged_by_identity.get(ident)
    if existing is None:
        merged_by_identity[ident] = {
            "payload": copy.deepcopy(payload),
            "regime_ids": [str(regime_id)] if str(regime_id or "").strip() else [],
        }
        return

    regime_ids = list(existing.get("regime_ids") or [])
    if str(regime_id or "").strip() and str(regime_id) not in regime_ids:
        regime_ids.append(str(regime_id))
    existing["regime_ids"] = regime_ids

    current_payload = existing.get("payload") if isinstance(existing.get("payload"), dict) else {}
    current_score = _safe_int(current_payload.get("Score", current_payload.get("BaseScore", 0)), 0)
    if int(score) > int(current_score):
        existing["payload"] = copy.deepcopy(payload)


def _finalize_refine_merged_candidates(merged_by_identity: dict[tuple, dict]) -> list[dict]:
    out: list[dict] = []
    for entry in list(merged_by_identity.values()):
        if not isinstance(entry, dict):
            continue
        payload = copy.deepcopy(entry.get("payload")) if isinstance(entry.get("payload"), dict) else None
        if not isinstance(payload, dict):
            continue
        regime_ids = [str(x) for x in list(entry.get("regime_ids") or ()) if str(x or "").strip()]
        if regime_ids:
            payload["HumanHitSimMergedRegimeIds"] = list(regime_ids)
        payload["HumanHitSimMergedRegimeCount"] = int(len(regime_ids))
        data = payload.get("Data")
        if isinstance(data, dict):
            if regime_ids:
                data["HumanHitSimMergedRegimeIds"] = list(regime_ids)
            data["HumanHitSimMergedRegimeCount"] = int(len(regime_ids))
            payload["Data"] = data
            if "data" in payload:
                payload["data"] = data
        out.append(payload)
    out.sort(
        key=lambda row: (
            -_safe_int(row.get("Score", row.get("BaseScore", 0)), 0),
            -_safe_int(row.get("HumanHitSimMergedRegimeCount", 0), 0),
        )
    )
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
        song_data["timestamps"] = np.asarray(sim_ts, dtype=np.float32)

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
    candidate_pool: list | None = None,
) -> dict | None:
    """
    Post-GA HumanHitSim refinement for ApplyTo=ALL.

    The canonical path is exact deterministic boundary-regime evaluation on the
    GPU. Legacy `seed`, sampled `analytical`, and CPU refine branches have been
    removed; old config values are normalized onto this exact GPU path.
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

    requested_refine_mode = str(
        _get_cfg_value(human_cfg, "RefineMode", _get_cfg_value(human_cfg, "refinemode", "exact"))
    ).strip().lower()
    requested_refine_device = str(
        _get_cfg_value(human_cfg, "RefineDevice", _get_cfg_value(human_cfg, "refinedevice", "gpu"))
    ).strip().lower()
    refine_mode = _normalize_hitsim_refine_mode(requested_refine_mode)
    refine_device = _normalize_hitsim_refine_device(requested_refine_device)

    candidate_limit = _safe_int(
        _get_cfg_value(human_cfg, "RefineCandidateLimit", _get_cfg_value(human_cfg, "refinecandidatelimit", "8")),
        8,
    )
    if candidate_limit <= 0:
        candidate_limit = 1
    exact_regime_cap = _safe_int(
        _get_cfg_value(human_cfg, "RefineMaxRegimes", _get_cfg_value(human_cfg, "refinemaxregimes", "0")),
        0,
    )
    exact_regime_selection = str(
        _get_cfg_value(
            human_cfg,
            "RefineRegimeSelection",
            _get_cfg_value(human_cfg, "refineregimeselection", "all"),
        )
        or "all"
    ).strip().lower()
    if exact_regime_selection not in {"all", "head", "even"}:
        exact_regime_selection = "all"

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
    base_ts = np.asarray(chart_ts, dtype=np.float32)
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
    current_ts_np = np.asarray(current_ts, dtype=np.float32)
    current_fg_ts_np = np.asarray(song_data.get("fg_timestamps", current_ts_np), dtype=np.float32)
    current_fg_gc_np = np.asarray(song_data.get("fg_great_candidate_timestamps", current_fg_ts_np), dtype=np.float32)
    current_seed = _safe_int(meta0.get("HumanHitSimSeed", 0), 0)
    if current_seed <= 0:
        current_seed = 1

    p_color = str(meta0.get("Primary Color", "") or "")
    s_color = str(meta0.get("Secondary Color", "") or "")
    long_count = _safe_int(meta0.get("Long Notes", 0), 0)
    default_last_note = float(base_ts[-1]) if int(base_ts.shape[0]) > 0 else 0.0
    last_note_time = _safe_float(meta0.get("Last Note Time", default_last_note), default_last_note)

    refine_candidates = _collect_refine_candidates(
        best_data=best_data,
        candidate_pool=candidate_pool,
        candidate_limit=int(candidate_limit),
        ref_arrays=ref_arrays,
        primary_color=p_color,
        secondary_color=s_color,
        total_notes=int(base_ts.shape[0]),
        long_count=int(long_count),
        last_note_time=float(last_note_time),
    )
    if not refine_candidates:
        return None

    current_candidate_idx = 0
    for idx, candidate in enumerate(refine_candidates):
        if candidate.get("is_current"):
            current_candidate_idx = int(idx)
            break

    unique_scores: set[int] = {int(prev_score)}
    best_score = int(prev_score)
    best_seed = int(current_seed)
    best_candidate_idx = int(current_candidate_idx)
    best_ts = current_fg_ts_np
    best_gc = current_fg_gc_np
    best_alpha_num = 0
    best_alpha_den = 1
    best_regime_id = ""
    best_regime_family = ""
    best_regime_scope = ""
    best_regime_left_num = 0
    best_regime_left_den = 1
    best_regime_right_num = 1
    best_regime_right_den = 1
    regime_winners: list[dict] = []
    merged_by_identity: dict[tuple, dict] = {}

    # Exact-mode refinement is GPU-resident. We still quantize chart timestamps to
    # integer ms on CPU with the float32-first snap quantizer to match server floor
    # behavior near integer-ms boundaries without requiring f64 on GPU.
    ts_ms = _floor_to_int_ms(base_ts)
    boundary_domain = _build_full_ftff_boundary_domain(
        ref_arrays=ref_arrays,
        total_notes=int(base_ts.shape[0]),
        long_count=int(long_count),
        last_note_time=float(last_note_time),
    )
    signature_param_rows = boundary_domain["param_rows"]
    planner_signature_param_rows = _collect_signature_param_rows_for_candidates(refine_candidates)
    if not planner_signature_param_rows:
        planner_signature_param_rows = tuple(signature_param_rows or ())
    boundary_domain_full_pairs = int(boundary_domain["full_pair_count"])
    boundary_domain_unique_params = int(boundary_domain["unique_param_count"])
    boundary_domain_planner_params = int(len(planner_signature_param_rows or ()))
    exact_planner_family_mode = (
        "candidate_timeline_rows"
        if int(boundary_domain_planner_params) < int(boundary_domain_unique_params)
        else "ftff_boundary_rows"
    )

    seen_timeline_signatures: set[tuple] = set()
    evaluated_trials = 0
    skipped_timeline_duplicates = 0
    seed_attempts = 0
    exact_regime_count = 0
    exact_full_regime_count = 0
    exact_raw_interval_count = 0
    exact_family_mode = ""
    from gear_optimizer.solver.taichi_gem.api.hitsim_refine import refine_human_hitsim_exact_after_ga_gpu

    try:
        gpu_out = refine_human_hitsim_exact_after_ga_gpu(
            ts_ms=ts_ms,
            note_types=note_types,
            signature_param_rows=planner_signature_param_rows or (),
            refine_candidates=refine_candidates,
            prev_score=int(prev_score),
            max_regimes=int(exact_regime_cap),
            selection_mode=str(exact_regime_selection),
            perfect_lower_ms=-20,
            perfect_upper_ms=40,
            held_tail_type=3,
            held_tail_time_multiplier=2,
            great_lower_ms=-75,
            great_extra_upper_ms=150,
            great_mode=str(great_mode),
            ref_arrays=ref_arrays,
        )
    except Exception as exc:
        raise RuntimeError(
            "HumanHitSim exact refine requires GPU; legacy CPU refine fallback has been removed"
        ) from exc
    if not isinstance(gpu_out, dict) or not gpu_out:
        raise RuntimeError("HumanHitSim exact refine returned no GPU output")

    exact_raw_interval_count = int(gpu_out.get("raw_interval_count", 0) or 0)
    exact_regime_count = int(gpu_out.get("selected_regime_count", 0) or 0)
    exact_full_regime_count = int(gpu_out.get("full_regime_count", exact_regime_count) or exact_regime_count)
    boundary_domain_active_params = int(gpu_out.get("active_param_count", 0) or 0)
    exact_family_mode = str(exact_planner_family_mode or "ftff_boundary_rows")
    seed_attempts = int(exact_raw_interval_count)
    evaluated_trials = int(exact_regime_count)

    unique_score_count = max(1, int(gpu_out.get("unique_scores", 1) or 1))
    unique_scores = set(range(unique_score_count))
    seen_timeline_signatures = set(range(int(exact_regime_count)))
    skipped_timeline_duplicates = 0

    best_score = int(gpu_out.get("best_score", best_score) or best_score)
    best_candidate_idx = int(gpu_out.get("best_candidate_idx", best_candidate_idx) or best_candidate_idx)
    if best_candidate_idx < 0 or best_candidate_idx >= len(refine_candidates):
        best_candidate_idx = int(current_candidate_idx)
    best_alpha_num = int(gpu_out.get("best_alpha_num", 0) or 0)
    best_alpha_den = int(gpu_out.get("best_alpha_den", 1) or 1)
    best_regime_left_num = int(gpu_out.get("best_left_num", 0) or 0)
    best_regime_left_den = int(gpu_out.get("best_left_den", 1) or 1)
    best_regime_right_num = int(gpu_out.get("best_right_num", 1) or 1)
    best_regime_right_den = int(gpu_out.get("best_right_den", 1) or 1)
    best_regime_family = str(exact_family_mode or "ftff_boundary_rows")
    best_regime_scope = "ALL"
    best_seed = _derive_deterministic_regime_seed(
        song_name=str(meta0.get("Song Name", "") or ""),
        mode_tag="exact",
        alpha_num=int(best_alpha_num),
        alpha_den=int(best_alpha_den),
        dist=str(dist),
        great_mode=str(great_mode),
    )

    event_ms_np = np.asarray(gpu_out.get("best_event_ms", ()), dtype=np.int32)
    great_event_ms_np = np.asarray(gpu_out.get("best_great_ms", ()), dtype=np.int32)
    best_ts = _event_ms_to_sec(event_ms_np)
    best_gc = _event_ms_to_sec(great_event_ms_np)

    sig_rows = np.asarray(gpu_out.get("sig_rows", ()), dtype=np.int32)
    active_mask = np.asarray(gpu_out.get("active_row_mask", ()), dtype=np.int32)
    active_row_indices = [i for i in range(int(sig_rows.shape[0])) if int(active_mask[i]) != 0]
    if active_row_indices:
        regime_signature_rows = tuple(tuple(int(x) for x in sig_rows[int(i)].tolist()) for i in active_row_indices)
    elif int(sig_rows.shape[0]) > 0:
        regime_signature_rows = (tuple(int(x) for x in sig_rows[0].tolist()),)
    else:
        regime_signature_rows = ()

    signature_crc = _serialize_regime_signature(regime_signature_rows)
    best_regime_id = _derive_regime_identity(
        song_name=str(meta0.get("Song Name", "") or ""),
        mode_tag="exact",
        family=str(best_regime_family or "ftff_boundary_rows"),
        left_num=int(best_regime_left_num),
        left_den=int(best_regime_left_den),
        right_num=int(best_regime_right_num),
        right_den=int(best_regime_right_den),
        signature_crc=int(signature_crc),
        dist=str(dist),
        great_mode=str(great_mode),
    )
    for regime in list(gpu_out.get("selected_regimes", ()) or ()):
        if not isinstance(regime, dict):
            continue
        regime_candidate_idx = _safe_int(regime.get("best_candidate_idx", -1), -1)
        if regime_candidate_idx < 0 or regime_candidate_idx >= len(refine_candidates):
            continue
        regime_score = _safe_int(regime.get("best_score", 0), 0)
        regime_alpha_num = _safe_int(regime.get("alpha_num", 0), 0)
        regime_alpha_den = _safe_int(regime.get("alpha_den", 1), 1)
        regime_left_num = _safe_int(regime.get("left_num", 0), 0)
        regime_left_den = _safe_int(regime.get("left_den", 1), 1)
        regime_right_num = _safe_int(regime.get("right_num", 1), 1)
        regime_right_den = _safe_int(regime.get("right_den", 1), 1)
        regime_family = str(regime.get("family", "") or exact_family_mode or "ftff_boundary_rows")
        regime_scope = str(regime.get("scope", "ALL") or "ALL")
        regime_id = str(regime.get("regime_id", "") or "")
        if not regime_id:
            regime_id = _derive_regime_identity(
                song_name=str(meta0.get("Song Name", "") or ""),
                mode_tag="exact",
                family=str(regime_family),
                left_num=int(regime_left_num),
                left_den=int(regime_left_den),
                right_num=int(regime_right_num),
                right_den=int(regime_right_den),
                signature_crc=0,
                dist=str(dist),
                great_mode=str(great_mode),
            )
        _record_refine_regime_result(
            regime_winners=regime_winners,
            merged_by_identity=merged_by_identity,
            candidate=refine_candidates[int(regime_candidate_idx)],
            score=int(regime_score),
            refine_mode=str(refine_mode),
            seed=_derive_deterministic_regime_seed(
                song_name=str(meta0.get("Song Name", "") or ""),
                mode_tag="exact",
                alpha_num=int(regime_alpha_num),
                alpha_den=int(regime_alpha_den),
                dist=str(dist),
                great_mode=str(great_mode),
            ),
            regime_id=str(regime_id),
            regime_family=str(regime_family),
            regime_scope=str(regime_scope),
            alpha_num=int(regime_alpha_num),
            alpha_den=int(regime_alpha_den),
            left_num=int(regime_left_num),
            left_den=int(regime_left_den),
            right_num=int(regime_right_num),
            right_den=int(regime_right_den),
            candidate_idx=int(regime_candidate_idx),
        )

    # Never regress persisted score: keep prior winner if refinement does not improve.
    best_score = max(int(best_score), int(prev_score))
    selected_candidate = refine_candidates[best_candidate_idx]
    selected_identity = tuple(selected_candidate.get("identity") or ()) or (("__candidate_idx__", int(best_candidate_idx)),)
    if selected_identity not in merged_by_identity:
        fallback_family = str(best_regime_family or exact_family_mode or exact_planner_family_mode or "ftff_boundary_rows")
        fallback_left_num = int(best_regime_left_num)
        fallback_left_den = int(best_regime_left_den)
        fallback_right_num = int(best_regime_right_num)
        fallback_right_den = int(best_regime_right_den)
        fallback_alpha_num = int(best_alpha_num)
        fallback_alpha_den = int(best_alpha_den)
        fallback_regime_id = str(best_regime_id or "")
        if not fallback_regime_id:
            fallback_regime_id = _derive_regime_identity(
                song_name=str(meta0.get("Song Name", "") or ""),
                mode_tag="exact",
                family=str(fallback_family),
                left_num=int(fallback_left_num),
                left_den=max(1, int(fallback_left_den)),
                right_num=int(fallback_right_num),
                right_den=max(1, int(fallback_right_den)),
                signature_crc=0,
                dist=str(dist),
                great_mode=str(great_mode),
            )
        _record_refine_regime_result(
            regime_winners=regime_winners,
            merged_by_identity=merged_by_identity,
            candidate=selected_candidate,
            score=int(best_score),
            refine_mode=str(refine_mode),
            seed=int(best_seed),
            regime_id=str(fallback_regime_id),
            regime_family=str(fallback_family),
            regime_scope=str(best_regime_scope or "ALL"),
            alpha_num=int(fallback_alpha_num),
            alpha_den=max(1, int(fallback_alpha_den)),
            left_num=int(fallback_left_num),
            left_den=max(1, int(fallback_left_den)),
            right_num=int(fallback_right_num),
            right_den=max(1, int(fallback_right_den)),
            candidate_idx=int(best_candidate_idx),
        )
    merged_candidates = _finalize_refine_merged_candidates(merged_by_identity)

    song_data["fg_timestamps"] = np.asarray(best_ts, dtype=np.float32)
    song_data["fg_great_candidate_timestamps"] = np.asarray(best_gc, dtype=np.float32)
    song_data["timestamps"] = np.asarray(best_ts, dtype=np.float32)
    calc_song["song_data"] = song_data

    meta = _copy_metadata_shallow(meta0)
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
    meta["HumanHitSimRefineSeedAttempts"] = int(seed_attempts)
    meta["HumanHitSimRefineCandidateCount"] = int(len(refine_candidates))
    meta["HumanHitSimRefineRegimeWinnerCount"] = int(len(regime_winners))
    meta["HumanHitSimRefineMergedCandidateCount"] = int(len(merged_candidates))
    meta["HumanHitSimRefineMode"] = str(refine_mode)
    meta["HumanHitSimRefineVariantBudgetMode"] = "exact_boundary_table"
    meta["HumanHitSimRefineCandidateChanged"] = bool(not refine_candidates[best_candidate_idx].get("is_current"))
    meta["HumanHitSimRefineExactRegimeCount"] = int(exact_regime_count)
    meta["HumanHitSimRefineExactFullRegimeCount"] = int(exact_full_regime_count)
    meta["HumanHitSimRefineExactRawIntervalCount"] = int(exact_raw_interval_count)
    meta["HumanHitSimRefineExactRegimeCap"] = int(max(0, int(exact_regime_cap)))
    meta["HumanHitSimRefineExactRegimeSelection"] = str(exact_regime_selection)
    meta["HumanHitSimRefineBoundaryDomainFullPairs"] = int(boundary_domain_full_pairs)
    meta["HumanHitSimRefineBoundaryDomainUniqueParams"] = int(boundary_domain_unique_params)
    meta["HumanHitSimRefineBoundaryDomainActiveParams"] = int(boundary_domain_active_params)
    meta["HumanHitSimRefineBoundaryPlannerParams"] = int(boundary_domain_planner_params)
    if requested_refine_mode and str(requested_refine_mode) != str(refine_mode):
        meta["HumanHitSimRefineRequestedMode"] = str(requested_refine_mode)
    if requested_refine_device and str(requested_refine_device) != str(refine_device):
        meta["HumanHitSimRefineRequestedDevice"] = str(requested_refine_device)
    if exact_planner_family_mode:
        meta["HumanHitSimRefineExactPlannerFamilyMode"] = str(exact_planner_family_mode)
    if exact_family_mode:
        meta["HumanHitSimRefineExactFamilyMode"] = str(exact_family_mode)
    meta["HumanHitSimRegimeAlphaNumerator"] = int(best_alpha_num)
    meta["HumanHitSimRegimeAlphaDenominator"] = int(best_alpha_den)
    if best_regime_id:
        meta["HumanHitSimRegimeId"] = str(best_regime_id)
        meta["HumanHitSimRegimeFamily"] = str(best_regime_family)
        meta["HumanHitSimRegimeScope"] = str(best_regime_scope)
        meta["HumanHitSimRegimeLeftNumerator"] = int(best_regime_left_num)
        meta["HumanHitSimRegimeLeftDenominator"] = int(best_regime_left_den)
        meta["HumanHitSimRegimeRightNumerator"] = int(best_regime_right_num)
        meta["HumanHitSimRegimeRightDenominator"] = int(best_regime_right_den)
    meta.pop("HumanHitSimPlanned", None)
    calc_song["metadata"] = meta

    selected_data = selected_candidate["data"]
    selected_data["Score"] = int(best_score)
    selected_data["BaseScore"] = int(best_score)
    if isinstance(selected_candidate.get("entry"), dict):
        selected_candidate["entry"]["Score"] = int(best_score)
        selected_candidate["entry"]["BaseScore"] = int(best_score)

    if selected_data is not best_data:
        best_data.clear()
        best_data.update(selected_data)
    else:
        best_data["Score"] = int(best_score)
        best_data["BaseScore"] = int(best_score)

    return {
        "best_seed": int(best_seed),
        "best_score": int(best_score),
        "prev_score": int(prev_score),
        "trials": int(trials),
        "seed_attempts": int(seed_attempts),
        "unique_scores": int(len(unique_scores)),
        "evaluated_trials": int(evaluated_trials),
        "timeline_variants": int(len(seen_timeline_signatures)),
        "skipped_timeline_duplicates": int(skipped_timeline_duplicates),
        "candidate_count": int(len(refine_candidates)),
        "regime_winner_count": int(len(regime_winners)),
        "merged_candidate_count": int(len(merged_candidates)),
        "candidate_changed": bool(not selected_candidate.get("is_current")),
        "refine_mode": str(refine_mode),
        "requested_refine_mode": str(requested_refine_mode),
        "requested_refine_device": str(requested_refine_device),
        "variant_budget_mode": "exact_boundary_table",
        "exact_regime_count": int(exact_regime_count),
        "exact_full_regime_count": int(exact_full_regime_count),
        "exact_raw_interval_count": int(exact_raw_interval_count),
        "exact_regime_cap": int(max(0, int(exact_regime_cap))),
        "exact_regime_selection": str(exact_regime_selection),
        "boundary_domain_full_pairs": int(boundary_domain_full_pairs),
        "boundary_domain_unique_params": int(boundary_domain_unique_params),
        "boundary_domain_active_params": int(boundary_domain_active_params),
        "boundary_domain_planner_params": int(boundary_domain_planner_params),
        "exact_planner_family_mode": str(exact_planner_family_mode),
        "exact_family_mode": str(exact_family_mode),
        "regime_alpha_num": int(best_alpha_num),
        "regime_alpha_den": int(best_alpha_den),
        "regime_id": str(best_regime_id),
        "regime_family": str(best_regime_family),
        "regime_scope": str(best_regime_scope),
        "regime_left_num": int(best_regime_left_num),
        "regime_left_den": int(best_regime_left_den),
        "regime_right_num": int(best_regime_right_num),
        "regime_right_den": int(best_regime_right_den),
        "selected_candidate": {
            "Gear": selected_candidate.get("gear"),
            "Minis": selected_candidate.get("minis"),
            "Data": selected_data,
        },
        "regime_winners": regime_winners,
        "merged_candidates": merged_candidates,
    }


def materialize_human_hit_sim_regime(
    calc_song: dict,
    *,
    regime_data: dict,
) -> dict | None:
    """
    Apply one previously selected refine regime to `calc_song` in-place.

    This is used by selective continuation to rebuild deterministic regime
    timestamps without carrying full per-regime timeline arrays around.
    """
    if not isinstance(calc_song, dict) or not isinstance(regime_data, dict):
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
    base_ts = np.asarray(chart_ts, dtype=np.float32)
    if int(base_ts.shape[0]) <= 0:
        return None

    note_types = np.asarray(song_data.get("note_types", ()), dtype=np.int16)
    if note_types.shape[0] != base_ts.shape[0]:
        note_types = np.ones(base_ts.shape[0], dtype=np.int16)

    requested_refine_mode = str(regime_data.get("HumanHitSimRefineMode", regime_data.get("HumanHitSimMode", "")) or "").strip().lower()
    if requested_refine_mode == "seed":
        return None
    refine_mode = _normalize_hitsim_refine_mode(requested_refine_mode)

    dist = str(
        regime_data.get(
            "HumanHitSimDistribution",
            meta0.get("HumanHitSimDistribution", "uniform"),
        )
        or "uniform"
    ).strip().lower()
    great_mode = str(
        regime_data.get(
            "HumanHitSimGreatMode",
            meta0.get("HumanHitSimGreatMode", "late"),
        )
        or "late"
    ).strip().lower()

    alpha_num = _safe_int(regime_data.get("HumanHitSimRegimeAlphaNumerator", 0), 0)
    alpha_den = _safe_int(regime_data.get("HumanHitSimRegimeAlphaDenominator", 1), 1)
    if alpha_den <= 0:
        alpha_den = 1

    from gear_optimizer.solver.taichi_gem.api.hitsim_refine import materialize_human_hitsim_regime_gpu

    try:
        gpu_out = materialize_human_hitsim_regime_gpu(
            ts_ms=_floor_to_int_ms(base_ts),
            note_types=note_types,
            alpha_num=int(alpha_num),
            alpha_den=int(alpha_den),
            perfect_lower_ms=-20,
            perfect_upper_ms=40,
            held_tail_type=3,
            held_tail_time_multiplier=2,
            great_lower_ms=-75,
            great_extra_upper_ms=150,
            great_mode=str(great_mode),
        )
    except Exception as exc:
        raise RuntimeError(
            "HumanHitSim regime materialization requires GPU; legacy CPU rebuild has been removed"
        ) from exc

    event_ms = np.asarray(gpu_out.get("event_ms", ()), dtype=np.int32)
    great_event_ms = np.asarray(gpu_out.get("great_ms", ()), dtype=np.int32)
    best_ts = _event_ms_to_sec(event_ms)
    best_gc = _event_ms_to_sec(great_event_ms)

    song_data["fg_timestamps"] = np.asarray(best_ts, dtype=np.float32)
    song_data["fg_great_candidate_timestamps"] = np.asarray(best_gc, dtype=np.float32)
    song_data["timestamps"] = np.asarray(best_ts, dtype=np.float32)
    calc_song["song_data"] = song_data

    meta = _copy_metadata_shallow(meta0)
    meta["HumanHitSimApplyTo"] = "ALL"
    meta["HumanHitSimDistribution"] = str(dist)
    meta["HumanHitSimGreatMode"] = str(great_mode)
    meta["HumanHitSimSeedIsRandom"] = False
    meta["HumanHitSimApplied"] = True
    meta["HumanHitSimRefined"] = True
    meta["HumanHitSimRefineMode"] = str(refine_mode)
    if requested_refine_mode and str(requested_refine_mode) != str(refine_mode):
        meta["HumanHitSimRefineRequestedMode"] = str(requested_refine_mode)
    if "HumanHitSimSeed" in regime_data:
        meta["HumanHitSimSeed"] = int(_safe_int(regime_data.get("HumanHitSimSeed", meta.get("HumanHitSimSeed", 0)), 0))
    if "HumanHitSimRegimeId" in regime_data:
        meta["HumanHitSimRegimeId"] = str(regime_data.get("HumanHitSimRegimeId", "") or "")
    if "HumanHitSimRegimeFamily" in regime_data:
        meta["HumanHitSimRegimeFamily"] = str(regime_data.get("HumanHitSimRegimeFamily", "") or "")
    if "HumanHitSimRegimeScope" in regime_data:
        meta["HumanHitSimRegimeScope"] = str(regime_data.get("HumanHitSimRegimeScope", "") or "")
    if "HumanHitSimRegimeLeftNumerator" in regime_data:
        meta["HumanHitSimRegimeLeftNumerator"] = int(_safe_int(regime_data.get("HumanHitSimRegimeLeftNumerator", 0), 0))
    if "HumanHitSimRegimeLeftDenominator" in regime_data:
        meta["HumanHitSimRegimeLeftDenominator"] = int(
            max(1, _safe_int(regime_data.get("HumanHitSimRegimeLeftDenominator", 1), 1))
        )
    if "HumanHitSimRegimeRightNumerator" in regime_data:
        meta["HumanHitSimRegimeRightNumerator"] = int(_safe_int(regime_data.get("HumanHitSimRegimeRightNumerator", 0), 0))
    if "HumanHitSimRegimeRightDenominator" in regime_data:
        meta["HumanHitSimRegimeRightDenominator"] = int(
            max(1, _safe_int(regime_data.get("HumanHitSimRegimeRightDenominator", 1), 1))
        )
    if "HumanHitSimRegimeAlphaNumerator" in regime_data:
        meta["HumanHitSimRegimeAlphaNumerator"] = int(_safe_int(regime_data.get("HumanHitSimRegimeAlphaNumerator", 0), 0))
    if "HumanHitSimRegimeAlphaDenominator" in regime_data:
        meta["HumanHitSimRegimeAlphaDenominator"] = int(
            max(1, _safe_int(regime_data.get("HumanHitSimRegimeAlphaDenominator", 1), 1))
        )
    calc_song["metadata"] = meta
    return {
        "timestamps": np.asarray(best_ts, dtype=np.float32),
        "fg_timestamps": np.asarray(best_gc, dtype=np.float32),
        "refine_mode": str(refine_mode),
        "seed": int(_safe_int(meta.get("HumanHitSimSeed", 0), 0)),
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
