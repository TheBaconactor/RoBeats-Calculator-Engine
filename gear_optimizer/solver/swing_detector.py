"""
SwingDetector - quantify score variance under HumanHitSim.

This module runs *post-processing* sweeps over many HumanHitSim seeds for a
fixed loadout/stats snapshot, and stores the per-seed score deltas ("swings")
relative to the run's baseline score.

Design goals:
- CPU-only (must not block GPU execution).
- Deterministic per seed (seed -> simulated hit timestamps -> score).
- Store only non-zero deltas (per user request).
"""

from __future__ import annotations

import configparser
import json
import os
from dataclasses import dataclass
from io import StringIO
from typing import Any

import numpy as np

from ..core.constants import PATHS, TOTAL_ROWS
from ..data.csv_parser import read_table
from .hit_simulation import simulate_perfect_hit_timestamps_with_great_candidates
from .scoring.force_greats import evaluate_force_greats
from .scoring.stats_scoring import evaluate_stats_score


@dataclass(frozen=True)
class SwingDetectorConfig:
    enabled: bool
    seed_start: int
    seed_count: int
    max_entries_base: int
    max_entries_fg: int
    print_values: bool
    distribution: str
    great_mode: str

    @classmethod
    def from_cfg(cls, cfg: configparser.ConfigParser | None) -> "SwingDetectorConfig":
        enabled = False
        seed_start = 0
        seed_count = 1000
        max_entries_base = 1
        max_entries_fg = 1
        print_values = True

        distribution = "uniform"
        great_mode = "full"

        if cfg is None:
            return cls(
                enabled=enabled,
                seed_start=seed_start,
                seed_count=seed_count,
                max_entries_base=max_entries_base,
                max_entries_fg=max_entries_fg,
                print_values=print_values,
                distribution=distribution,
                great_mode=great_mode,
            )

        try:
            enabled = cfg.getboolean("SwingDetector", "Enabled", fallback=enabled)
            seed_start = int(cfg.get("SwingDetector", "SeedStart", fallback=str(seed_start)) or str(seed_start))
            seed_count = int(cfg.get("SwingDetector", "SeedCount", fallback=str(seed_count)) or str(seed_count))
            max_entries_base = int(
                cfg.get("SwingDetector", "MaxEntriesBase", fallback=str(max_entries_base)) or str(max_entries_base)
            )
            max_entries_fg = int(
                cfg.get("SwingDetector", "MaxEntriesFG", fallback=str(max_entries_fg)) or str(max_entries_fg)
            )
            print_values = cfg.getboolean("SwingDetector", "Print", fallback=print_values)
        except Exception:
            # Keep defaults on parse errors.
            pass

        try:
            distribution = str(cfg.get("HumanHitSim", "Distribution", fallback=distribution) or distribution).strip()
        except Exception:
            distribution = distribution
        try:
            great_mode = str(cfg.get("HumanHitSim", "GreatMode", fallback=great_mode) or great_mode).strip()
        except Exception:
            great_mode = great_mode

        distribution = distribution.lower() or "uniform"
        great_mode = great_mode.lower() or "full"
        if great_mode not in {"late", "early", "full"}:
            great_mode = "full"

        seed_start = max(0, int(seed_start))
        seed_count = max(0, int(seed_count))
        max_entries_base = max(0, int(max_entries_base))
        max_entries_fg = max(0, int(max_entries_fg))

        return cls(
            enabled=bool(enabled),
            seed_start=seed_start,
            seed_count=seed_count,
            max_entries_base=max_entries_base,
            max_entries_fg=max_entries_fg,
            print_values=bool(print_values),
            distribution=distribution,
            great_mode=great_mode,
        )


_REF_ARRAYS_CACHE: dict[str, dict[str, np.ndarray]] = {}


def _load_ref_arrays() -> dict[str, np.ndarray]:
    cache_key = "default"
    cached = _REF_ARRAYS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    table_path = os.path.join(PATHS.data_dir, "Gear", "Stats.txt")
    stats_table = read_table(table_path)
    names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays: dict[str, np.ndarray] = {}
    for i, name in enumerate(names):
        ref_arrays[name] = np.array(
            [(stats_table[TOTAL_ROWS - v][i] if stats_table else 0.0) for v in range(TOTAL_ROWS + 1)],
            dtype=np.float64,
        )
    _REF_ARRAYS_CACHE[cache_key] = ref_arrays
    return ref_arrays


def _read_song_file_minimal(fp: str) -> dict[str, Any]:
    """
    Minimal song reader for SwingDetector.

    Avoids importing `pipeline.song_processor.read_song_file` to keep this module
    free of pipeline<->solver circular dependencies.
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

    marker = -1
    for i, line in enumerate(lines):
        if line.strip() == "Song Data":
            marker = i
            break
    if marker == -1:
        return out

    # Metadata is tab-separated: Key\tValue
    for line in lines[:marker]:
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        key = parts[0].strip()
        if key in out["song_details"]:
            out["song_details"][key] = parts[1].strip() or "0"

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
        if nd.size:
            nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
            if nd.shape[1] >= 4:
                out["timestamps"] = nd[:, 0].astype(float).tolist()
                out["note_types"] = nd[:, 3].astype(int).tolist()
    except Exception:
        return out

    return out


def _force_counts_from_force_obj(force_obj: dict[str, Any] | None) -> list[int]:
    if not isinstance(force_obj, dict):
        return []
    details = force_obj.get("details") or {}
    if not isinstance(details, dict):
        return []
    fg_meta = details.get("ForceGreats") or {}
    if not isinstance(fg_meta, dict):
        return []
    config = fg_meta.get("config") or {}
    if not isinstance(config, dict):
        return []

    indexed: dict[int, int] = {}
    for k, v in config.items():
        key = str(k)
        if not key.lower().startswith("nonfever"):
            continue
        try:
            idx = int(key[len("NonFever") :]) - 1
        except Exception:
            continue
        try:
            indexed[idx] = max(0, int(v))
        except Exception:
            indexed[idx] = 0

    if not indexed:
        return []
    max_idx = max(indexed)
    out = [0] * (max_idx + 1)
    for i, val in indexed.items():
        if 0 <= i < len(out):
            out[i] = int(val)
    return out


def _format_swings(swings: list[int]) -> str:
    parts = []
    for d in swings:
        if not d:
            continue
        parts.append(f"{d:+d}")
    return ", ".join(parts)


def compute_score_swings(
    *,
    song_file_path: str,
    stats: dict[str, Any],
    baseline_score: int,
    seed_start: int,
    seed_count: int,
    distribution: str,
    great_mode: str,
    ref_arrays: dict[str, np.ndarray] | None = None,
) -> list[int]:
    """
    Compute swings for the base score (no forced greats penalty).

    Returns:
        list[int]: Non-zero deltas: score(seed) - baseline_score.
    """
    ref_arrays = ref_arrays or _load_ref_arrays()
    song_data = _read_song_file_minimal(song_file_path)
    base_ts = np.asarray(song_data.get("timestamps") or (), dtype=np.float64)
    note_types = np.asarray(song_data.get("note_types") or (), dtype=np.int16)
    if note_types.shape[0] != base_ts.shape[0]:
        note_types = np.ones(base_ts.shape[0], dtype=np.int16)

    calc_song = {
        "metadata": dict(song_data.get("song_details") or {}),
        "song_data": {
            "timestamps": base_ts,
            "note_types": note_types,
            # Align with HumanHitSim behavior in the main pipeline: FG uses the simulated
            # timestamps even when ApplyTo=FG (baseline solver uses chart ts).
            "fg_timestamps": base_ts,
        },
    }

    fever_mask = np.zeros(int(base_ts.shape[0]), dtype=np.bool_)
    swings: list[int] = []
    for seed in range(int(seed_start), int(seed_start) + int(seed_count)):
        sim_ts, sim_great_candidates, _dbg = simulate_perfect_hit_timestamps_with_great_candidates(
            base_ts,
            note_types,
            seed=int(seed),
            distribution=distribution,
            great_mode=great_mode,
        )
        # Mirror ApplyTo=ALL scoring: use simulated timestamps for fever timeline + scoring.
        calc_song["song_data"]["timestamps"] = np.asarray(sim_ts, dtype=np.float64)
        calc_song["song_data"]["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
        calc_song["song_data"]["fg_great_candidate_timestamps"] = np.asarray(sim_great_candidates, dtype=np.float64)

        score = int(evaluate_stats_score(stats, calc_song, ref_arrays, fever_mask_buffer=fever_mask))
        delta = int(score) - int(baseline_score)
        if delta:
            swings.append(delta)
    return swings


def compute_fg_score_swings(
    *,
    song_file_path: str,
    stats: dict[str, Any],
    forced_counts: list[int],
    baseline_fg_score: int,
    seed_start: int,
    seed_count: int,
    distribution: str,
    great_mode: str,
    ref_arrays: dict[str, np.ndarray] | None = None,
) -> list[int]:
    """
    Compute swings for the ForceGreats score (with forced greats penalty).

    Returns:
        list[int]: Non-zero deltas: fg_score(seed) - baseline_fg_score.
    """
    ref_arrays = ref_arrays or _load_ref_arrays()
    song_data = _read_song_file_minimal(song_file_path)
    base_ts = np.asarray(song_data.get("timestamps") or (), dtype=np.float64)
    note_types = np.asarray(song_data.get("note_types") or (), dtype=np.int16)
    if note_types.shape[0] != base_ts.shape[0]:
        note_types = np.ones(base_ts.shape[0], dtype=np.int16)

    calc_song = {
        "metadata": dict(song_data.get("song_details") or {}),
        "song_data": {
            "timestamps": base_ts,
            "note_types": note_types,
            "fg_timestamps": base_ts,
        },
    }

    swings: list[int] = []
    for seed in range(int(seed_start), int(seed_start) + int(seed_count)):
        sim_ts, sim_great_candidates, _dbg = simulate_perfect_hit_timestamps_with_great_candidates(
            base_ts,
            note_types,
            seed=int(seed),
            distribution=distribution,
            great_mode=great_mode,
        )
        calc_song["song_data"]["timestamps"] = np.asarray(sim_ts, dtype=np.float64)
        calc_song["song_data"]["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
        calc_song["song_data"]["fg_great_candidate_timestamps"] = np.asarray(sim_great_candidates, dtype=np.float64)

        res = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=forced_counts)
        if not res:
            continue
        score = int(res.get("final_score", 0) or 0)
        delta = int(score) - int(baseline_fg_score)
        if delta:
            swings.append(delta)
    return swings


def attach_swings_to_entries(
    *,
    song_name: str,
    song_file_path: str | None,
    entries: list[dict[str, Any]],
    cfg: configparser.ConfigParser | None,
) -> None:
    """
    Mutates `entries` in-place to add:
    - `swing_score`: list[int] swings vs `score`
    - `swing_fg`: list[int] swings vs `fg_score` (only when FG config exists)
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

    # Shared ref arrays load once.
    ref_arrays = _load_ref_arrays()

    def _score(e: dict) -> int:
        try:
            return int(e.get("score", 0) or 0)
        except Exception:
            return 0

    def _fg_score(e: dict) -> int:
        try:
            return int(e.get("fg_score", 0) or 0)
        except Exception:
            return 0

    # Top-N by base score (for loadouts.swing_json)
    base_targets = sorted(entries, key=_score, reverse=True)[: int(settings.max_entries_base or 0)]

    # Top-N by FG score when valid FG config exists (for fg_loadouts.swing_json)
    fg_candidates = []
    for e in entries:
        if _fg_score(e) <= _score(e):
            continue
        force_obj = e.get("force")
        if not isinstance(force_obj, dict):
            continue
        forced_counts = _force_counts_from_force_obj(force_obj)
        if not forced_counts or sum(forced_counts) <= 0:
            continue
        fg_candidates.append(e)
    fg_targets = sorted(fg_candidates, key=_fg_score, reverse=True)[: int(settings.max_entries_fg or 0)]

    # De-dup: a single loadout may be both the best base and best FG entry.
    seen_ids = set()

    # Base swings (relative to entry.score, using entry.details.Stats)
    for e in base_targets:
        eid = id(e)
        if eid in seen_ids:
            continue
        seen_ids.add(eid)

        details = e.get("details") or {}
        stats = (details.get("Stats") or {}) if isinstance(details, dict) else {}
        if not isinstance(stats, dict) or not stats:
            continue

        baseline = _score(e)
        swings = compute_score_swings(
            song_file_path=song_file_path,
            stats=stats,
            baseline_score=baseline,
            seed_start=settings.seed_start,
            seed_count=settings.seed_count,
            distribution=settings.distribution,
            great_mode=settings.great_mode,
            ref_arrays=ref_arrays,
        )
        e["swing_score"] = swings
        if settings.print_values:
            print(f"[SwingDetector] {song_name} score_swings: {_format_swings(swings)}")

    # FG swings (relative to entry.fg_score, using force.details.Stats + ForceGreats config)
    for e in fg_targets:
        details = e.get("details") or {}
        stats = (details.get("Stats") or {}) if isinstance(details, dict) else {}
        force_obj = e.get("force")
        if not isinstance(force_obj, dict):
            continue
        forced_counts = _force_counts_from_force_obj(force_obj)
        if not forced_counts or sum(forced_counts) <= 0:
            continue

        # For "top1 base" entries, entry.details may be base stats while the FG score uses the
        # force payload's stats (finder can re-optimize FT/FF). Prefer force.details.Stats.
        force_details = force_obj.get("details") or {}
        force_stats = (force_details.get("Stats") or {}) if isinstance(force_details, dict) else {}
        if isinstance(force_stats, dict) and force_stats:
            stats = force_stats

        baseline = _fg_score(e)
        swings = compute_fg_score_swings(
            song_file_path=song_file_path,
            stats=stats,
            forced_counts=forced_counts,
            baseline_fg_score=baseline,
            seed_start=settings.seed_start,
            seed_count=settings.seed_count,
            distribution=settings.distribution,
            great_mode=settings.great_mode,
            ref_arrays=ref_arrays,
        )
        e["swing_fg"] = swings
        if settings.print_values:
            print(f"[SwingDetector] {song_name} fg_score_swings: {_format_swings(swings)}")


def swing_json_from_entry(e: dict[str, Any], *, key: str) -> str | None:
    """
    Convert an entry's swing list to compact JSON for DB storage.

    - If the key is absent: return NULL (not computed).
    - If the key is present (including empty list): return JSON string.
    """
    if key not in e:
        return None
    try:
        swings = e.get(key)
        if swings is None:
            return json.dumps([], separators=(",", ":"))
        if isinstance(swings, str):
            # Already JSON or stringified; keep as-is.
            return swings
        if not isinstance(swings, list):
            return json.dumps([], separators=(",", ":"))
        # Ensure ints, drop zeros (defensive; caller already drops).
        cleaned = [int(x) for x in swings if int(x) != 0]
        return json.dumps(cleaned, separators=(",", ":"))
    except Exception:
        return None

