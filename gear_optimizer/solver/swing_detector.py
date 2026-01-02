"""
SwingDetector (mock) - fast fever-timeline swing estimation under HumanHitSim.

This is a full rewrite of the previous SwingDetector implementation.

Goal (per user request):
- Use a *mock* scoring model:
    - base_value = 200
    - non-fever body note = 400  (combo_mul = 2.0)
    - fever body note     = 1200 (fever_mul = 3.0)
- Use the song's cached FT/FF fever timeline logic (no gear/gem solving).
- Sweep N HumanHitSim seeds + include the original hit timeline (OFF).
- Always pick the best scenario; never prefer negative deltas.
- Persist *deduped* positive deltas (>0) into DB via `swing_json` (through entries).
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from io import StringIO
from typing import Any, Iterable

import numpy as np

from ..core.constants import PATHS, TOTAL_ROWS
from ..data.csv_parser import read_table
from .fever_timeline import calculate_fever_timeline_indices
from .scoring_core import fast_calculate_score


MOCK_BASE_VALUE = 200
MOCK_COMBO_MUL = 2.0
MOCK_FEVER_MUL = 3.0


@dataclass(frozen=True)
class SwingDetectorConfig:
    enabled: bool
    seed_start: int
    seed_count: int
    max_entries: int
    print_values: bool
    positive_only: bool
    distribution: str

    @classmethod
    def from_cfg(cls, cfg: configparser.ConfigParser | None) -> "SwingDetectorConfig":
        enabled = False
        seed_start = 0
        seed_count = 1000
        max_entries = 1
        print_values = True
        positive_only = True
        distribution = "uniform"

        if cfg is None:
            return cls(
                enabled=enabled,
                seed_start=seed_start,
                seed_count=seed_count,
                max_entries=max_entries,
                print_values=print_values,
                positive_only=positive_only,
                distribution=distribution,
            )

        try:
            enabled = cfg.getboolean("SwingDetector", "Enabled", fallback=enabled)
            seed_start = int(cfg.get("SwingDetector", "SeedStart", fallback=str(seed_start)) or str(seed_start))
            seed_count = int(cfg.get("SwingDetector", "SeedCount", fallback=str(seed_count)) or str(seed_count))
            # Prefer the new single knob, but fall back to older keys if present.
            max_entries = int(cfg.get("SwingDetector", "MaxEntries", fallback=str(max_entries)) or str(max_entries))
            if max_entries <= 0:
                max_entries = int(cfg.get("SwingDetector", "MaxEntriesBase", fallback=str(max_entries)) or str(max_entries))
            print_values = cfg.getboolean("SwingDetector", "Print", fallback=print_values)
            positive_only = cfg.getboolean("SwingDetector", "PositiveOnly", fallback=positive_only)
        except Exception:
            pass

        try:
            distribution = str(cfg.get("HumanHitSim", "Distribution", fallback=distribution) or distribution).strip()
        except Exception:
            distribution = distribution

        seed_start = max(0, int(seed_start))
        seed_count = max(0, int(seed_count))
        max_entries = max(0, int(max_entries))
        distribution = distribution.lower() or "uniform"
        if distribution != "uniform":
            # The mock detector only supports the current hitsim implementation.
            distribution = "uniform"

        return cls(
            enabled=bool(enabled),
            seed_start=seed_start,
            seed_count=seed_count,
            max_entries=max_entries,
            print_values=bool(print_values),
            positive_only=bool(positive_only),
            distribution=distribution,
        )


_FT_FF_FACTORS_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def _load_ft_ff_factors() -> tuple[np.ndarray, np.ndarray]:
    """
    Return (ft_factors, ff_factors) arrays indexed by stat index [0..160].

    Mirrors how other parts of the optimizer interpret `Data/Gear/Stats.txt`.
    """
    cache_key = "default"
    cached = _FT_FF_FACTORS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    table_path = os.path.join(PATHS.data_dir, "Gear", "Stats.txt")
    stats_table = read_table(table_path)
    # Column order in Stats.txt: PP, CM, FM, FF, FT (see legacy loader patterns).
    col_ff = 3
    col_ft = 4

    # stats_table is stored from MAX->MIN; invert so index i maps to the correct row.
    ft = np.array(
        [(stats_table[TOTAL_ROWS - v][col_ft] if stats_table else 0.0) for v in range(TOTAL_ROWS + 1)],
        dtype=np.float64,
    )
    ff = np.array(
        [(stats_table[TOTAL_ROWS - v][col_ff] if stats_table else 0.0) for v in range(TOTAL_ROWS + 1)],
        dtype=np.float64,
    )
    _FT_FF_FACTORS_CACHE[cache_key] = (ft, ff)
    return ft, ff


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return default


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _read_song_file_minimal(fp: str) -> dict[str, Any]:
    """
    Minimal song reader used by SwingDetector.

    Intentionally avoids importing pipeline modules (prevents circular deps).
    """
    out: dict[str, Any] = {
        "song_details": {
            "Song Name": "",
            "Difficulty": "",
            "Primary Color": "",
            "Secondary Color": "",
            "Last Note Time": "",
            "Total Notes": "",
            "Fever Fill": "",
            "Fever Time": "",
            "Long Notes": "",
        },
        "timestamps": [],
        "note_types": [],
    }
    if not fp:
        return out

    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
    except Exception:
        return out

    marker = next((i for i, line in enumerate(lines) if line.strip() == "Song Data"), -1)
    if marker == -1:
        return out

    # Metadata: support both TAB and COLON separators (scan_song_header is flexible too).
    details = out["song_details"]
    for line in lines[:marker]:
        s = line.strip()
        if not s:
            continue
        if "\t" in s:
            parts = s.split("\t", 1)
        elif ":" in s:
            parts = s.split(":", 1)
        else:
            continue
        if len(parts) != 2:
            continue
        key = parts[0].strip()
        if key in details:
            details[key] = parts[1].strip() or "0"

    note_lines: list[str] = []
    for line in lines[marker + 1 :]:
        s = line.strip()
        if not s:
            continue
        c = s[0]
        if ("0" <= c <= "9") or c == ".":
            note_lines.append(line)

    if not note_lines:
        return out

    try:
        nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
    except Exception:
        return out

    if nd.size == 0:
        return out

    nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
    if nd.shape[1] >= 1:
        out["timestamps"] = nd[:, 0].astype(float).tolist()
    if nd.shape[1] >= 4:
        out["note_types"] = nd[:, 3].astype(int).tolist()
    else:
        out["note_types"] = [1] * len(out["timestamps"])

    # Fill some common derived metadata if missing.
    try:
        if not details.get("Total Notes"):
            details["Total Notes"] = str(len(out["timestamps"]))
        if not details.get("Last Note Time") and out["timestamps"]:
            details["Last Note Time"] = str(out["timestamps"][-1])
        if not details.get("Long Notes") and out["note_types"]:
            details["Long Notes"] = str(sum(1 for t in out["note_types"] if int(t) == 3))
    except Exception:
        pass

    return out


def _floor_to_int_ms(timestamps_sec: np.ndarray) -> np.ndarray:
    ts = np.asarray(timestamps_sec, dtype=np.float64)
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


@dataclass(frozen=True)
class _PerfectHitsimPlan:
    n_notes: int
    group_starts: np.ndarray  # int32
    group_ends: np.ndarray  # int32
    base_t_ms: np.ndarray  # int32
    low_off_ms: np.ndarray  # int32
    high_off_ms: np.ndarray  # int32


def _build_perfect_hitsim_plan(
    timestamps_sec: np.ndarray,
    note_types: np.ndarray,
    *,
    perfect_lower_ms: int = -20,
    perfect_upper_ms: int = 40,
    held_tail_type: int = 3,
    held_tail_time_multiplier: int = 2,
    quantize_ms: bool = True,
) -> _PerfectHitsimPlan:
    ts_sec = np.asarray(timestamps_sec, dtype=np.float64)
    n = int(ts_sec.shape[0])
    if n <= 0:
        return _PerfectHitsimPlan(
            n_notes=0,
            group_starts=np.zeros(0, dtype=np.int32),
            group_ends=np.zeros(0, dtype=np.int32),
            base_t_ms=np.zeros(0, dtype=np.int32),
            low_off_ms=np.zeros(0, dtype=np.int32),
            high_off_ms=np.zeros(0, dtype=np.int32),
        )

    if quantize_ms:
        ts_ms = _floor_to_int_ms(ts_sec)
    else:
        ts_ms = (ts_sec * 1000.0).astype(np.int32)

    note_types = np.asarray(note_types, dtype=np.int16)
    if note_types.shape[0] != n:
        note_types = np.ones(n, dtype=np.int16)

    lower_ms, upper_ms = _build_per_note_perfect_window_ms(
        note_types,
        perfect_lower_ms=perfect_lower_ms,
        perfect_upper_ms=perfect_upper_ms,
        held_tail_type=held_tail_type,
        held_tail_time_multiplier=held_tail_time_multiplier,
    )

    # Build chord groups by identical timestamp_ms runs (song data is already sorted).
    group_starts = np.empty(n, dtype=np.int32)
    group_ends = np.empty(n, dtype=np.int32)
    base_t_ms = np.empty(n, dtype=np.int32)
    low_off_ms = np.empty(n, dtype=np.int32)
    high_off_ms = np.empty(n, dtype=np.int32)
    group_count = 0

    i = 0
    while i < n:
        j = i + 1
        t = ts_ms[i]
        while j < n and ts_ms[j] == t:
            j += 1

        group_starts[group_count] = i
        group_ends[group_count] = j
        base_t_ms[group_count] = int(t)

        g_low = int(np.max(lower_ms[i:j]))
        g_high = int(np.min(upper_ms[i:j]))
        if g_low > g_high:
            g_low, g_high = g_high, g_low
        low_off_ms[group_count] = int(g_low)
        high_off_ms[group_count] = int(g_high)

        group_count += 1
        i = j

    return _PerfectHitsimPlan(
        n_notes=n,
        group_starts=group_starts[:group_count],
        group_ends=group_ends[:group_count],
        base_t_ms=base_t_ms[:group_count],
        low_off_ms=low_off_ms[:group_count],
        high_off_ms=high_off_ms[:group_count],
    )


def _simulate_perfect_hit_timestamps_from_plan(plan: _PerfectHitsimPlan, *, seed: int) -> np.ndarray:
    n = int(plan.n_notes)
    if n <= 0:
        return np.zeros(0, dtype=np.float64)

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    hit_ms = np.empty(n, dtype=np.int32)
    prev_event_ms: int | None = None

    for g in range(int(plan.group_starts.shape[0])):
        s = int(plan.group_starts[g])
        e = int(plan.group_ends[g])
        base_t = int(plan.base_t_ms[g])
        g_low = int(plan.low_off_ms[g])
        g_high = int(plan.high_off_ms[g])

        if prev_event_ms is None:
            eff_low = g_low
        else:
            eff_low = max(g_low, int(prev_event_ms) - base_t)

        if eff_low <= g_high:
            off = int(rng.integers(eff_low, g_high + 1))
        else:
            # Infeasible; clamp to the latest legal offset (rare in practice).
            off = g_high
            if prev_event_ms is not None and base_t + off < int(prev_event_ms):
                off = int(prev_event_ms) - base_t

        event_ms = base_t + off
        hit_ms[s:e] = int(event_ms)
        prev_event_ms = int(event_ms)

    return hit_ms.astype(np.float64) / 1000.0


def _mock_score_for_timeline(
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    return int(
        fast_calculate_score(
            MOCK_BASE_VALUE,
            MOCK_COMBO_MUL,
            MOCK_FEVER_MUL,
            fever_mask_head,
            int(count_body_fever),
            int(count_body_normal),
        )
    )


def _mock_score_for_song(
    *,
    timestamps: np.ndarray,
    ff_stat: int,
    ft_stat: int,
    long_notes: int,
    last_note_time: float,
    fever_mask_buffer: np.ndarray,
    ff_factors: np.ndarray,
    ft_factors: np.ndarray,
) -> int:
    total_notes = int(timestamps.shape[0])
    if total_notes <= 0:
        return 0

    ff_stat = max(0, min(TOTAL_ROWS, int(ff_stat)))
    ft_stat = max(0, min(TOTAL_ROWS, int(ft_stat)))
    ff_factor = float(ff_factors[ff_stat])
    ft_factor = float(ft_factors[ft_stat])

    fever_mask_head, count_body_fever, count_body_normal, _, _ = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        int(long_notes),
        float(last_note_time),
        fever_mask_buffer,
    )
    return _mock_score_for_timeline(fever_mask_head, count_body_fever, count_body_normal)


def compute_mock_swings_for_song(
    *,
    song_file_path: str,
    ff_stat: int,
    ft_stat: int,
    seed_start: int,
    seed_count: int,
    positive_only: bool,
    distribution: str,
) -> tuple[list[int], dict[str, Any]]:
    """
    Return (deduped_positive_deltas, meta).

    Deltas are computed vs the OFF baseline (chart timestamps).
    """
    if distribution != "uniform":
        distribution = "uniform"

    song = _read_song_file_minimal(song_file_path)
    base_ts = np.asarray(song.get("timestamps") or [], dtype=np.float64)
    note_types = np.asarray(song.get("note_types") or [], dtype=np.int16)
    if note_types.shape[0] != base_ts.shape[0]:
        note_types = np.ones(base_ts.shape[0], dtype=np.int16)

    meta = song.get("song_details") or {}
    long_notes = _safe_int(meta.get("Long Notes"), 0)
    last_note_time = _safe_float(meta.get("Last Note Time"), float(base_ts[-1]) if base_ts.size else 0.0)

    ft_factors, ff_factors = _load_ft_ff_factors()

    fever_mask_buffer = np.zeros(int(base_ts.shape[0]), dtype=np.bool_)

    baseline_off = _mock_score_for_song(
        timestamps=base_ts,
        ff_stat=ff_stat,
        ft_stat=ft_stat,
        long_notes=long_notes,
        last_note_time=last_note_time,
        fever_mask_buffer=fever_mask_buffer,
        ff_factors=ff_factors,
        ft_factors=ft_factors,
    )

    # Sweep ON seeds.
    plan = _build_perfect_hitsim_plan(base_ts, note_types, quantize_ms=True)
    best_on_score = baseline_off
    best_on_seed: int | None = None

    deltas: set[int] = set()
    seed_start_i = int(seed_start or 0)
    seed_count_i = int(seed_count or 0)

    for seed in range(seed_start_i, seed_start_i + seed_count_i):
        sim_ts = _simulate_perfect_hit_timestamps_from_plan(plan, seed=seed)
        # Reuse mask buffer (safe: calculate_fever_timeline_indices fully overwrites it).
        score = _mock_score_for_song(
            timestamps=sim_ts,
            ff_stat=ff_stat,
            ft_stat=ft_stat,
            long_notes=long_notes,
            last_note_time=last_note_time,
            fever_mask_buffer=fever_mask_buffer,
            ff_factors=ff_factors,
            ft_factors=ft_factors,
        )
        if score > best_on_score:
            best_on_score = int(score)
            best_on_seed = int(seed)
        delta = int(score) - int(baseline_off)
        if positive_only and delta <= 0:
            continue
        if delta != 0:
            deltas.add(int(delta))

    # Always pick the best scenario; never negative (OFF baseline is included by construction).
    best_mode = "OFF" if best_on_seed is None else "HITSIM"
    best_score = int(baseline_off) if best_on_seed is None else int(best_on_score)
    best_delta = int(best_score) - int(baseline_off)
    if best_delta < 0:
        best_delta = 0
        best_mode = "OFF"
        best_on_seed = None
        best_score = int(baseline_off)

    swings = sorted(deltas)
    summary = {
        "ff_stat": int(ff_stat),
        "ft_stat": int(ft_stat),
        "mock_base_value": int(MOCK_BASE_VALUE),
        "mock_combo_mul": float(MOCK_COMBO_MUL),
        "mock_fever_mul": float(MOCK_FEVER_MUL),
        "baseline_off_score": int(baseline_off),
        "best_score": int(best_score),
        "best_delta_vs_off": int(best_delta),
        "best_mode": str(best_mode),
        "best_seed": int(best_on_seed) if best_on_seed is not None else None,
        "seed_start": int(seed_start_i),
        "seed_count": int(seed_count_i),
        "distribution": str(distribution),
        "positive_only": bool(positive_only),
    }
    return swings, summary


def _format_swings(swings: Iterable[int]) -> str:
    vals = [int(v) for v in (swings or []) if int(v) != 0]
    if not vals:
        return "[]"
    return "[" + ", ".join(str(v) for v in vals) + "]"


def attach_swings_to_entries(
    *,
    song_name: str,
    song_file_path: str | None,
    entries: list[dict[str, Any]],
    cfg: configparser.ConfigParser | None,
) -> None:
    """
    Mutates `entries` in-place to add:
    - `swing_score`: list[int] of deduped positive deltas vs OFF baseline.
    - `details.MockSwing`: summary meta (best seed/mode/delta).
    """
    if not entries:
        return

    settings = SwingDetectorConfig.from_cfg(cfg)
    if not settings.enabled:
        return

    if not song_file_path:
        return
    song_file_path = str(song_file_path)
    if not os.path.exists(song_file_path):
        return

    def _score(e: dict) -> int:
        try:
            return int(e.get("score", 0) or 0)
        except Exception:
            return 0

    targets = sorted(entries, key=_score, reverse=True)[: int(settings.max_entries or 0)]
    for e in targets:
        details = e.get("details")
        if not isinstance(details, dict):
            continue
        stats = details.get("Stats") or {}
        if not isinstance(stats, dict) or not stats:
            continue

        ff_stat = _safe_int(stats.get("Fever Fill Rate"), 0)
        ft_stat = _safe_int(stats.get("Fever Time"), 0)

        swings, meta = compute_mock_swings_for_song(
            song_file_path=song_file_path,
            ff_stat=ff_stat,
            ft_stat=ft_stat,
            seed_start=settings.seed_start,
            seed_count=settings.seed_count,
            positive_only=settings.positive_only,
            distribution=settings.distribution,
        )
        e["swing_score"] = swings
        details.setdefault("MockSwing", {})
        if isinstance(details.get("MockSwing"), dict):
            details["MockSwing"].update(meta)

        if settings.print_values:
            try:
                best_mode = meta.get("best_mode")
                best_seed = meta.get("best_seed")
                best_delta = meta.get("best_delta_vs_off")
                suffix = f"{best_mode}" + (f":{best_seed}" if best_seed is not None else "")
                print(f"[SwingDetector] {song_name} mock swings: {_format_swings(swings)} | best {suffix} (Δ={best_delta})")
            except Exception:
                pass

