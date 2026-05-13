"""
Verify the GPU ceiling timing-envelope timeline against the repo root DB "top 1" winners.

Goal
  For a sample of songs from `evolution.db`, take the persisted best base-score loadout
  and re-evaluate it using the production GPU ceiling timeline (`GPU_TIMELINE_CEILING_ENVELOPE=1`).

  The ceiling evaluator should never score *below* an observed persisted best score for the
  same stats snapshot (it is a best-case timing envelope under the modeled Perfect window).

Default sampling
  Top N songs ordered by `attempt_lifetime` (highest first), since those are the most
  important / most-run charts in the DB.

Run
  python tools/verify/verify_ceiling_vs_db_top1_sample.py --n 25

Exit codes
  0: all checked songs satisfy ceiling_score >= db_best_score
  1: at least one song violates the bound (potential regression / model mismatch)
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Ensure repo root is on sys.path (so `import gear_optimizer` works when run as a script).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@dataclass(frozen=True)
class _DbSong:
    name: str
    best_score: int
    attempt_lifetime: int
    attempts_first: int


@dataclass(frozen=True)
class _DbLoadout:
    team_buff: str
    score: int
    stats: dict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_ref_arrays() -> dict[str, np.ndarray]:
    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.csv_parser import read_table

    paths = load_paths_cache()
    stats_table = read_table(paths.get("Stats", ""))
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    out: dict[str, np.ndarray] = {}
    for i, name in enumerate(stat_names):
        tmp = []
        for v in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(v)
            try:
                val = stats_table[lookup_index][i] if stats_table else 0.0
            except Exception:
                val = 0.0
            tmp.append(float(val))
        out[name] = np.asarray(tmp, dtype=np.float32)
    return out


def _build_song_path_map() -> dict[str, list[str]]:
    root = _repo_root()
    out: dict[str, list[str]] = {}
    for diff in ("Easy", "Normal", "Hard"):
        d = root / "Data" / diff
        if not d.is_dir():
            continue
        for fp in d.glob("*.txt"):
            key = fp.stem
            out.setdefault(key, []).append(str(fp))
            # Also map by the header "Song Name" (handles filenames that must be sanitized on Windows).
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    line0 = (f.readline() or "").strip()
                if line0.startswith("Song Name"):
                    parts = line0.split("\t", 1)
                    if len(parts) == 2:
                        header_name = parts[1].strip()
                        if header_name:
                            out.setdefault(header_name, []).append(str(fp))
            except Exception:
                pass
    return out


def _find_song_path(song_name: str, mapping: dict[str, list[str]]) -> str | None:
    paths = mapping.get(str(song_name), None)
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]
    # Prefer Hard if there are multiple.
    for p in paths:
        if f"{os.sep}Hard{os.sep}" in p:
            return p
    return paths[0]


def _query_sample_songs(db_path: str, *, n: int) -> list[_DbSong]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        """
        SELECT name, best_score, attempt_lifetime, attempts_first
        FROM songs
        WHERE best_score IS NOT NULL AND best_score > 0
        ORDER BY attempt_lifetime DESC
        LIMIT ?
        """,
        (int(n),),
    ).fetchall()
    out: list[_DbSong] = []
    for name, best_score, lifetime, first in rows:
        out.append(
            _DbSong(
                name=str(name or ""),
                best_score=int(best_score or 0),
                attempt_lifetime=int(lifetime or 0),
                attempts_first=int(first or 0),
            )
        )
    con.close()
    return out


def _query_best_loadout(db_path: str, *, song_name: str) -> _DbLoadout | None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute(
        """
        SELECT team_buff, score, details_json
        FROM team_buff_loadouts
        WHERE song_name = ?
        ORDER BY score DESC, timestamp DESC
        LIMIT 1
        """,
        (str(song_name),),
    ).fetchone()
    con.close()
    if not row:
        return None
    team_buff, score, details_json = row
    try:
        details = json.loads(details_json) if details_json else {}
    except Exception:
        details = {}
    stats = details.get("Stats") if isinstance(details, dict) else None
    if not isinstance(stats, dict) or not stats:
        return None
    return _DbLoadout(team_buff=str(team_buff or ""), score=int(score or 0), stats=dict(stats))


def _read_calc_song(song_path: str) -> dict:
    from gear_optimizer.data.song_io import read_song_file

    song = read_song_file(str(song_path))
    details = song.get("song_details", {}) or {}
    timestamps = np.asarray(song.get("timestamps", ()), dtype=np.float32)
    note_types = np.asarray(song.get("note_types", ()), dtype=np.int16)

    # Fall back if header is malformed.
    try:
        long_notes = int(float(details.get("Long Notes", 0) or 0))
    except Exception:
        long_notes = 0

    meta = {
        "Song Name": str(details.get("Song Name") or Path(song_path).stem),
        "Difficulty": str(details.get("Difficulty") or "Hard"),
        "Primary Color": str(details.get("Primary Color") or ""),
        "Secondary Color": str(details.get("Secondary Color") or ""),
        "Long Notes": int(long_notes),
        "Last Note Time": float(timestamps[-1]) if timestamps.size else 0.0,
        "Total Notes": int(timestamps.size),
    }
    return {
        "metadata": meta,
        "song_data": {
            "timestamps": timestamps.copy(),
            # Ceiling mode is chart-structure driven; keep this explicit.
            "chart_timestamps": timestamps.copy(),
            "note_types": note_types.copy(),
        },
    }


def _unpack_head_bits(bits_u32x4: np.ndarray, head_len: int) -> np.ndarray:
    head_len_i = int(max(0, head_len))
    if head_len_i <= 0:
        return np.zeros((0,), dtype=np.bool_)
    packed = np.asarray(bits_u32x4, dtype=np.uint32).reshape(4).view(np.uint8)
    out = np.unpackbits(packed, bitorder="little")[:head_len_i]
    return np.asarray(out, dtype=np.bool_)


def _score_with_ceiling_timeline(
    *,
    calc_song: dict,
    ref_arrays: dict[str, np.ndarray],
    stats: dict,
) -> int:
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.scoring_core import fast_calculate_score, lookup_reference_py
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    meta = calc_song.get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color") or "")
    s_color = str(meta.get("Secondary Color") or "")

    base_pp = lookup_reference_py(int(stats.get("Perfect Points", 0) or 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(
        int(stats.get("Combo Multiplier", 0) or 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS
    )
    fever_mul = lookup_reference_py(
        int(stats.get("Fever Multiplier", 0) or 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS
    )
    primary_val = int(stats.get(p_color, 0) or 0)
    secondary_val = int(stats.get(s_color, 0) or 0)
    total_base = (primary_val * 2) + secondary_val + float(base_pp)

    ft_idx = int(stats.get("Fever Time", 0) or 0)
    ff_idx = int(stats.get("Fever Fill Rate", 0) or 0)
    if ft_idx < 0:
        ft_idx = 0
    if ff_idx < 0:
        ff_idx = 0
    if ft_idx > int(TOTAL_ROWS):
        ft_idx = int(TOTAL_ROWS)
    if ff_idx > int(TOTAL_ROWS):
        ff_idx = int(TOTAL_ROWS)

    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

    # NOTE: Vulkan `to_numpy()` transfers the full field, but these grids are small enough
    # (161×161, plus 4 u32 words) to be acceptable for a 25-song sample.
    head_len_grid = np.asarray(gpu_fields.grid_head_len.to_numpy()[0], dtype=np.int32)
    bits_grid = np.asarray(gpu_fields.grid_fever_masks_bits.to_numpy()[0], dtype=np.uint32)
    body_fever_grid = np.asarray(gpu_fields.grid_count_body_fever.to_numpy()[0], dtype=np.int32)
    body_normal_grid = np.asarray(gpu_fields.grid_count_body_normal.to_numpy()[0], dtype=np.int32)

    head_len = int(head_len_grid[ft_idx, ff_idx])
    bits = bits_grid[ft_idx, ff_idx, :].reshape(4)
    head_mask = _unpack_head_bits(bits, head_len)
    body_fever = int(body_fever_grid[ft_idx, ff_idx])
    body_normal = int(body_normal_grid[ft_idx, ff_idx])

    return int(fast_calculate_score(total_base, float(combo_mul), float(fever_mul), head_mask, body_fever, body_normal))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=str, default="evolution.db", help="Path to evolution.db (default: ./evolution.db).")
    ap.add_argument("--n", type=int, default=25, help="Number of songs to sample (default: 25).")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any ceiling score is below the DB best_score for that song.",
    )
    args = ap.parse_args()

    db_path = str(args.db or "").strip()
    if not db_path:
        raise SystemExit("Missing --db path")
    if not os.path.exists(db_path):
        raise SystemExit(f"DB not found: {db_path!r}")

    # Force ceiling mode for this verification run.
    os.environ["GPU_TIMELINE_CEILING_ENVELOPE"] = "1"
    os.environ.setdefault("GPU_TIMELINE_WRITE_UNPACKED_MASKS", "0")

    # Init Taichi once.
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem.api.timeline import reset_timeline_state

    init_taichi()
    reset_timeline_state()

    ref_arrays = _load_ref_arrays()
    song_paths = _build_song_path_map()
    # Query a larger window so we can still check N songs even if some charts are missing locally.
    want_n = max(1, int(args.n))
    sample = _query_sample_songs(db_path, n=max(want_n, want_n * 4))

    bad = 0
    missing_chart = 0
    missing_loadout = 0
    checked = 0

    t0 = time.perf_counter()
    for i, song in enumerate(sample, start=1):
        if checked >= want_n:
            break
        loadout = _query_best_loadout(db_path, song_name=song.name)
        if loadout is None:
            missing_loadout += 1
            print(f"[{i:02d}] SKIP loadout-missing song={song.name!r}")
            continue

        fp = _find_song_path(song.name, song_paths)
        if not fp:
            missing_chart += 1
            print(f"[{i:02d}] SKIP chart-missing song={song.name!r}")
            continue

        calc_song = _read_calc_song(fp)
        try:
            ceiling_score = _score_with_ceiling_timeline(calc_song=calc_song, ref_arrays=ref_arrays, stats=loadout.stats)
        except Exception as exc:
            bad += 1
            print(f"[{i:02d}] ERROR song={song.name!r} exc={type(exc).__name__}: {exc}")
            continue

        db_best = int(song.best_score)
        ok = int(ceiling_score) >= int(db_best)
        delta = int(ceiling_score) - int(db_best)

        status = "OK " if ok else "BAD"
        if not ok:
            bad += 1
        checked += 1
        print(
            f"[{i:02d}] {status} song={song.name!r} team_buff={loadout.team_buff} "
            f"db_best={db_best} ceiling={ceiling_score} delta={delta:+d} "
            f"(attempt_lifetime={song.attempt_lifetime} attempts_first={song.attempts_first})"
        )

    t1 = time.perf_counter()
    print("")
    print(
        f"[summary] checked={checked} scanned={len(sample)} bad={bad} missing_loadout={missing_loadout} "
        f"missing_chart={missing_chart} "
        f"wall_ms={((t1 - t0) * 1000.0):.1f}"
    )

    if bad and bool(args.strict):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
