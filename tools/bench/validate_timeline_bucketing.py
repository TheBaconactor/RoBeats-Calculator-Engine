"""
Validate timeline bucketing safety by comparing bucketed vs unbucketed outputs.

This is intentionally synthetic (does not require Data/), but can be extended to
real calc_song/ref_arrays if desired.

Usage (PowerShell):
  python tools/bench/validate_timeline_bucketing.py

Environment:
  TIMELINE_BUCKET_MODE=off|b|a
"""

from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Ensure repo root is importable when running as a script.
from gear_optimizer.core.parsing import env_get
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from gear_optimizer.solver.fever_timeline import SongTimelineGrid


def _make_calc_song(*, name: str, n_notes: int, duration: float, long_notes: int = 0) -> dict:
    # Add jitter to exercise searchsorted boundary behavior.
    ts = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float64)
    if len(ts) >= 3:
        rng = np.random.default_rng(12345 + int(n_notes) + int(duration * 10))
        jitter = rng.normal(loc=0.0, scale=1e-6, size=len(ts)).astype(np.float64)
        jitter[0] = 0.0
        jitter[-1] = 0.0
        ts = ts + jitter
        ts = np.maximum.accumulate(ts)  # ensure monotonic
    return {
        "song_data": {"timestamps": ts},
        "metadata": {
            "Song Name": str(name),
            "Difficulty": "Test",
            "Last Note Time": str(float(duration)),
            "Total Notes": str(int(n_notes)),
            "Long Notes": str(int(long_notes)),
            "Primary Color": "Rush",
            "Secondary Color": "Beat",
        },
    }


def _make_ref_arrays_with_plateaus() -> dict:
    # Make plateaus so bucket mode "b" actually merges keys.
    # - FT factor: 161 entries but only 41 distinct values
    # - FF factor: 161 entries but only 33 distinct values
    ft = np.repeat(np.linspace(0.75, 1.25, 41, dtype=np.float64), repeats=4)[:161]
    ff = np.repeat(np.linspace(0.6, 2.0, 33, dtype=np.float64), repeats=5)[:161]

    # Other arrays unused here, but keep shape consistent.
    pp = np.linspace(100.0, 300.0, 161, dtype=np.float64)
    cm = np.linspace(1.0, 2.0, 161, dtype=np.float64)
    fm = np.linspace(1.0, 2.0, 161, dtype=np.float64)

    return {
        "Fever Time": ft,
        "Fever Fill Rate": ff,
        "Perfect Points": pp,
        "Combo Multiplier": cm,
        "Fever Multiplier": fm,
    }


@dataclass
class _Result:
    mode: str
    songs: int
    pairs_checked: int
    mismatches: int
    elapsed_sec: float
    bucketed_unique_cells: int
    bucketed_b_factor_pairs: int


def _timeline_sig(t) -> tuple:
    # t = (mask_head, cbf, cbn, acts, last_end)
    mh, cbf, cbn, acts, last_end = t
    return (mh.tobytes(), int(cbf), int(cbn), int(acts), int(last_end))


def main() -> int:
    # We will compare "off" vs mode set by env, for a handful of songs.
    mode = str(env_get("TIMELINE_BUCKET_MODE", "b") or "b").strip().lower()
    if mode in {"factor", "factors"}:
        mode = "b"
    if mode in {"sig", "signature"}:
        mode = "a"

    songs = [
        _make_calc_song(name="S1_short", n_notes=80, duration=25.0, long_notes=0),
        _make_calc_song(name="S2_mid", n_notes=500, duration=60.0, long_notes=20),
        _make_calc_song(name="S3_long", n_notes=1400, duration=120.0, long_notes=0),
    ]
    ref_arrays = _make_ref_arrays_with_plateaus()

    # Random sample of index pairs (plus some structured points)
    rng = random.Random(1337)
    sample_pairs = {(0, 0), (160, 160), (80, 80), (0, 160), (160, 0)}
    for _ in range(8000):
        sample_pairs.add((rng.randrange(0, 161), rng.randrange(0, 161)))
    sample_pairs = sorted(sample_pairs)

    # Build baseline grids (mode=off)
    baseline_grids = [SongTimelineGrid(cs, ref_arrays, bucket_mode="off") for cs in songs]

    # Build bucketed grids
    bucketed_grids = [SongTimelineGrid(cs, ref_arrays, bucket_mode=mode) for cs in songs]

    t0 = time.perf_counter()
    mismatches = 0
    checked = 0

    for base, buck in zip(baseline_grids, bucketed_grids):
        for ft_idx, ff_idx in sample_pairs:
            t_base = base.get_timeline(ft_idx, ff_idx)
            t_buck = buck.get_timeline(ft_idx, ff_idx)
            checked += 1
            if _timeline_sig(t_base) != _timeline_sig(t_buck):
                mismatches += 1
                if mismatches <= 5:
                    print(
                        f"[MISMATCH] song={base.cache_key} ft={ft_idx} ff={ff_idx} "
                        f"base={_timeline_sig(t_base)[1:]} buck={_timeline_sig(t_buck)[1:]}"
                    )
                if mismatches > 20:
                    break
        if mismatches > 20:
            break

    dt = time.perf_counter() - t0

    # Estimate how much bucketed caching is collapsing states (roughly).
    bucketed_unique = 0
    bucketed_pairs = 0
    try:
        for g in bucketed_grids:
            # Count computed cells
            for row in g._timeline_grid:
                for cell in row:
                    if cell is not None:
                        bucketed_unique += 1
            bucketed_pairs += len(getattr(g, "_bucket_b", {}) or {})
    except Exception:
        pass

    out = _Result(
        mode=mode,
        songs=len(songs),
        pairs_checked=checked,
        mismatches=mismatches,
        elapsed_sec=dt,
        bucketed_unique_cells=bucketed_unique,
        bucketed_b_factor_pairs=bucketed_pairs,
    )

    print(
        f"[TimelineBucketing] mode={out.mode} songs={out.songs} "
        f"pairs={out.pairs_checked} mismatches={out.mismatches} "
        f"dt={out.elapsed_sec:.2f}s unique_cells={out.bucketed_unique_cells} "
        f"factor_pairs={out.bucketed_b_factor_pairs}"
    )

    return 0 if mismatches == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
