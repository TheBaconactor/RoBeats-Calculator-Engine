"""
Backfill missing HumanHitSim offset deltas into frontend-facing DB rows.

Problem this fixes
------------------
Older DB rows can be missing:
  - `force_details_json["ForceGreats"]["hitsim_offset_deltas_ms"]` (FG per-window offset deltas), and/or
  - `details_json["hitsim_offset_deltas_ms"]` (base per-window offset deltas; only meaningful for ApplyTo=ALL).

Newer optimizer runs already persist these fields, but existing DBs may still
have gaps, which makes "new songs" / top51 outputs appear to lack the delta.

What this script does
---------------------
- Scans the canonical frontend views:
  - `frontend_fg_top51_by_song_tier`
  - `frontend_base_top51_by_song_tier`
- For any row missing the delta field, it re-reads the song chart from `Data/`,
  applies HumanHitSim deterministically (by default), recomputes the delta, and
  writes it back into the underlying tier tables:
  - `team_buff_fg_loadouts`
  - `team_buff_loadouts`

Notes / limitations
-------------------
- This is *best-effort*. If a chart file cannot be found (renamed/removed), the
  row is skipped.
- If the DB rows were generated with `HumanHitSim.Seed=0` (random per run),
  the original seed is not persisted, so this script cannot reproduce the exact
  original per-run offsets. The goal is to populate the field for frontend/
  analysis consumers.

Usage
-----
  python tools/db/backfill_hitsim_offsets.py --db evolution.db --apply
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
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.config import load_config, load_paths_cache
from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.data.database import get_evolution_db_path
from gear_optimizer.pipeline.song_processor import _build_base_calc_song_from_file, scan_song_header
from gear_optimizer.solver.hit_simulation import apply_human_hit_sim
from gear_optimizer.solver.scoring.force_greats import (
    summarize_hitsim_offset_deltas_ms_for_base,
    summarize_hitsim_offset_deltas_ms_for_fg_variant,
)


def _loads_json(s: Any, default: Any) -> Any:
    if s is None:
        return default
    if isinstance(s, (dict, list)):
        return s
    text = str(s).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _dumps_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))


def _coerce_int(v: Any, default: int = 0) -> int:
    try:
        return int(v if v is not None else default)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return int(default)


def _preload_ref_arrays(stats_table: list[list[Any]]) -> dict[str, Any]:
    # Keep identical to GearOptimizerApp._preload_ref_arrays.
    import numpy as np

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays: dict[str, Any] = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    return ref_arrays


def _nonfever_counts_from_config(config: Any) -> tuple[int, ...]:
    if not isinstance(config, dict) or not config:
        return ()
    pairs: list[tuple[int, int]] = []
    for key, val in config.items():
        if not isinstance(key, str) or not key.startswith("NonFever"):
            continue
        try:
            idx = int(key.replace("NonFever", "").strip()) - 1
        except Exception:
            continue
        cnt = _coerce_int(val, 0)
        pairs.append((idx, max(0, cnt)))
    if not pairs:
        return ()
    pairs.sort(key=lambda x: x[0])
    max_idx = pairs[-1][0]
    if max_idx < 0:
        return ()
    out = [0] * (max_idx + 1)
    for idx, cnt in pairs:
        if 0 <= idx < len(out):
            out[idx] = int(cnt)
    if sum(out) <= 0:
        return ()
    return tuple(int(v) for v in out)


def _materialize_stats_from_force(force_obj: dict, *, fallback_stats: dict | None = None) -> dict | None:
    stats_obj = force_obj.get("Stats")
    if isinstance(stats_obj, dict) and stats_obj:
        return stats_obj

    # Older payloads might store Stats in force.details.
    nested = force_obj.get("details")
    if isinstance(nested, dict):
        stats_obj2 = nested.get("Stats")
        if isinstance(stats_obj2, dict) and stats_obj2:
            return stats_obj2

    if isinstance(fallback_stats, dict) and fallback_stats:
        return fallback_stats

    base_stats = force_obj.get("BaseStats")
    if not isinstance(base_stats, dict) or not base_stats:
        if isinstance(nested, dict) and isinstance(nested.get("BaseStats"), dict):
            base_stats = nested.get("BaseStats")
    if not isinstance(base_stats, dict) or not base_stats:
        return None

    gem_counts = force_obj.get("GemCounts")
    if not isinstance(gem_counts, dict):
        if isinstance(nested, dict) and isinstance(nested.get("GemCounts"), dict):
            gem_counts = nested.get("GemCounts")
        else:
            gem_counts = {}

    # Finder payload uses Selected Element, not SelectedElement.
    selected_element = force_obj.get("SelectedElement") or force_obj.get("Selected Element") or ""
    if not selected_element and isinstance(nested, dict):
        selected_element = nested.get("SelectedElement") or nested.get("Selected Element") or ""
    selected_element = str(selected_element or "").strip()

    ft_val = _coerce_int(force_obj.get("FT", gem_counts.get("Fever Time", 0)), 0)
    ff_val = _coerce_int(force_obj.get("FF", gem_counts.get("Fever Fill", gem_counts.get("Fever Fill Rate", 0))), 0)
    g_pp = _coerce_int(gem_counts.get("Perfect Points", 0), 0)
    g_cm = _coerce_int(gem_counts.get("Combo Multiplier", 0), 0)
    g_fm = _coerce_int(gem_counts.get("Fever Multiplier", 0), 0)
    g_ov = _coerce_int(
        gem_counts.get("Element", gem_counts.get("Element Overflow", gem_counts.get("ElementOverflow", 0))),
        0,
    )

    try:
        from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast

        computed = apply_gems_to_base_fast(base_stats, selected_element, ft_val, ff_val, g_pp, g_cm, g_fm, g_ov)
    except Exception:
        computed = None

    if isinstance(computed, dict) and computed:
        return computed
    return None


@dataclass
class _RowKey:
    song_name: str
    team_buff: str
    loadout_hash: str


def _iter_target_rows(conn: sqlite3.Connection, *, song_filter: str = "") -> tuple[list[dict], list[dict]]:
    """
    Returns (base_rows, fg_rows) as lists of dict payloads with:
      - key: _RowKey
      - details: dict
      - force: dict|None
    """
    song_filter = str(song_filter or "").strip().lower()

    base_rows: list[dict] = []
    fg_rows: list[dict] = []

    # Base top51: fill missing top-level details delta; also fill missing force delta when force present.
    for r in conn.execute(
        "SELECT song_name, team_buff, loadout_hash, details_json, force_details_json "
        "FROM frontend_base_top51_by_song_tier"
    ):
        song_name = str(r["song_name"] or "").strip()
        if not song_name:
            continue
        if song_filter and song_filter not in song_name.lower():
            continue

        details = _loads_json(r["details_json"], {})
        force = _loads_json(r["force_details_json"], None)
        if not isinstance(details, dict):
            continue

        needs_base = details.get("hitsim_offset_deltas_ms") is None

        needs_force = False
        if isinstance(force, dict):
            fg_meta = force.get("ForceGreats")
            if isinstance(fg_meta, dict) and fg_meta.get("config"):
                needs_force = fg_meta.get("hitsim_offset_deltas_ms") is None

        if not (needs_base or needs_force):
            continue

        base_rows.append(
            {
                "key": _RowKey(
                    song_name=song_name,
                    team_buff=str(r["team_buff"] or "").strip().upper(),
                    loadout_hash=str(r["loadout_hash"] or "").strip(),
                ),
                "details": details,
                "force": force if isinstance(force, dict) else None,
                "needs_base": bool(needs_base),
                "needs_force": bool(needs_force),
            }
        )

    # FG top51: fill missing force delta (and mirror into details.ForceGreats).
    for r in conn.execute(
        "SELECT song_name, team_buff, loadout_hash, details_json, force_details_json "
        "FROM frontend_fg_top51_by_song_tier"
    ):
        song_name = str(r["song_name"] or "").strip()
        if not song_name:
            continue
        if song_filter and song_filter not in song_name.lower():
            continue

        details = _loads_json(r["details_json"], {})
        force = _loads_json(r["force_details_json"], None)
        if not isinstance(force, dict) or not isinstance(details, dict):
            continue

        fg_meta = force.get("ForceGreats")
        if not isinstance(fg_meta, dict) or not fg_meta.get("config"):
            continue
        if fg_meta.get("hitsim_offset_deltas_ms") is not None:
            continue

        fg_rows.append(
            {
                "key": _RowKey(
                    song_name=song_name,
                    team_buff=str(r["team_buff"] or "").strip().upper(),
                    loadout_hash=str(r["loadout_hash"] or "").strip(),
                ),
                "details": details,
                "force": force,
            }
        )

    return base_rows, fg_rows


def _resolve_song_paths(*, paths: dict, wanted: set[str]) -> dict[str, str]:
    """
    Best-effort map of song_name -> file_path for the wanted set.

    Stops scanning as soon as all wanted songs are found.
    """
    remaining = set(wanted)
    out: dict[str, str] = {}

    for diff in ("Hard", "Normal", "Easy"):
        root = str(paths.get(diff, "") or "").strip()
        if not root or not os.path.exists(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fname in files:
                if not fname.lower().endswith(".txt"):
                    continue
                fp = os.path.join(dirpath, fname)
                meta = scan_song_header(fp)
                if not meta:
                    continue
                song = str(meta.get("Song Name") or "").strip()
                if not song:
                    continue
                if song in remaining:
                    out[song] = fp
                    remaining.remove(song)
                    if not remaining:
                        return out
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill missing ForceGreats/base HitSim offset deltas in top51 views.")
    ap.add_argument("--db", type=str, default="", help="SQLite DB path (default: EVOLUTION_DB_PATH / ./evolution.db).")
    ap.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="HumanHitSim seed to use for recomputation (default: 1337). Must be non-zero for determinism.",
    )
    ap.add_argument(
        "--apply-to",
        type=str,
        default="ALL",
        choices=("ALL", "FG"),
        help="HumanHitSim.ApplyTo to use during recomputation (default: ALL).",
    )
    ap.add_argument(
        "--song-filter",
        type=str,
        default="",
        help="Only backfill songs whose song_name contains this substring (case-insensitive).",
    )
    ap.add_argument("--limit-songs", type=int, default=0, help="Optional cap on number of songs processed.")
    ap.add_argument("--dry-run", action="store_true", help="Analyze + report only (no DB writes).")
    ap.add_argument("--apply", action="store_true", help="Write updates to the DB.")
    args = ap.parse_args()

    if bool(args.apply) == bool(args.dry_run):
        print("Pick exactly one: --dry-run or --apply")
        return 2

    db_path = Path(args.db).expanduser() if args.db else Path(get_evolution_db_path())
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 2

    seed = int(args.seed)
    if seed == 0:
        print("--seed must be non-zero (the DB does not persist per-row random seeds).")
        return 2

    cfg = load_config()
    cfg_dict = cfg_to_dict(cfg)
    cfg_dict.setdefault("HumanHitSim", {})
    if not isinstance(cfg_dict["HumanHitSim"], dict):
        cfg_dict["HumanHitSim"] = {}
    cfg_dict["HumanHitSim"]["Enabled"] = "true"
    cfg_dict["HumanHitSim"]["Seed"] = str(seed)
    cfg_dict["HumanHitSim"]["ApplyTo"] = str(args.apply_to).upper()

    paths = load_paths_cache()
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    ref_arrays = _preload_ref_arrays(stats_table)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    t0 = time.perf_counter()
    base_rows, fg_rows = _iter_target_rows(conn, song_filter=str(args.song_filter or ""))

    if not base_rows and not fg_rows:
        print("No missing offset delta fields detected in top51 views.")
        return 0

    wanted_songs = {e["key"].song_name for e in base_rows} | {e["key"].song_name for e in fg_rows}
    if args.limit_songs and int(args.limit_songs) > 0:
        wanted_songs = set(sorted(wanted_songs)[: int(args.limit_songs)])

    print(f"DB: {db_path}")
    print(f"Songs with missing delta (top51 views): {len(wanted_songs):,}")
    print(f"  base rows needing backfill: {len(base_rows):,}")
    print(f"  fg rows needing backfill:   {len(fg_rows):,}")

    song_to_fp = _resolve_song_paths(paths=paths, wanted=wanted_songs)
    missing_files = sorted(wanted_songs - set(song_to_fp.keys()))
    if missing_files:
        print(f"WARNING: Could not resolve chart file for {len(missing_files):,} song(s); they will be skipped.")

    # Group work per song for locality/caching.
    per_song_base: dict[str, list[dict]] = {}
    for e in base_rows:
        name = e["key"].song_name
        if name in song_to_fp:
            per_song_base.setdefault(name, []).append(e)

    per_song_fg: dict[str, list[dict]] = {}
    for e in fg_rows:
        name = e["key"].song_name
        if name in song_to_fp:
            per_song_fg.setdefault(name, []).append(e)

    # DB write buffers.
    base_details_updates: list[tuple[str, str, str, str]] = []
    base_force_updates: list[tuple[str, str, str, str]] = []
    fg_updates: list[tuple[str, str, str, str, str]] = []

    processed_songs = 0
    filled_base = 0
    filled_force_in_base = 0
    filled_fg = 0

    for song_name in sorted(set(per_song_base.keys()) | set(per_song_fg.keys())):
        fp = song_to_fp.get(song_name)
        if not fp:
            continue

        processed_songs += 1
        if processed_songs % 50 == 0:
            dt = time.perf_counter() - t0
            print(
                f"[{processed_songs:,}/{len(song_to_fp):,}] elapsed={dt:.1f}s "
                f"filled: base={filled_base:,} base_force={filled_force_in_base:,} fg={filled_fg:,}"
            )

        try:
            calc_song = _build_base_calc_song_from_file(fp)
        except Exception:
            continue

        # Apply deterministic hitsim so summarize_* can compute chart-vs-sim deltas.
        try:
            apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
        except Exception:
            # No hitsim => cannot compute offset deltas.
            continue

        base_deltas_cache: dict[tuple[int, int], tuple[int, ...]] = {}
        fg_deltas_cache: dict[tuple[int, int, tuple[int, ...]], tuple[int, ...]] = {}

        # Base view rows (team_buff_loadouts).
        for e in per_song_base.get(song_name, []):
            key: _RowKey = e["key"]
            details: dict = e["details"]
            force_obj = e.get("force") if isinstance(e.get("force"), dict) else None

            details_changed = False
            force_changed = False

            if e.get("needs_base"):
                stats = details.get("Stats")
                if isinstance(stats, dict) and stats:
                    ff_stat = _coerce_int(stats.get("Fever Fill Rate", 0), 0)
                    ft_stat = _coerce_int(stats.get("Fever Time", 0), 0)
                    cache_key = (int(ff_stat), int(ft_stat))
                    deltas_t = base_deltas_cache.get(cache_key)
                    if deltas_t is None:
                        base_data = {"Stats": stats}
                        try:
                            computed = summarize_hitsim_offset_deltas_ms_for_base(calc_song, base_data, ref_arrays)
                        except Exception:
                            computed = None
                        if computed:
                            try:
                                deltas_t = tuple(int(x) for x in computed)
                            except Exception:
                                deltas_t = None
                            if deltas_t:
                                base_deltas_cache[cache_key] = deltas_t
                    if deltas_t:
                        details = dict(details)
                        details.pop("hitsim_offset_delta_ms", None)
                        details["hitsim_offset_deltas_ms"] = list(deltas_t)
                        details_changed = True
                        filled_base += 1

            if e.get("needs_force") and isinstance(force_obj, dict):
                fg_meta = force_obj.get("ForceGreats")
                if isinstance(fg_meta, dict) and fg_meta.get("config"):
                    stats = _materialize_stats_from_force(force_obj, fallback_stats=details.get("Stats"))
                    if isinstance(stats, dict) and stats:
                        counts = _nonfever_counts_from_config(fg_meta.get("config"))
                        if counts:
                            ff_stat = _coerce_int(stats.get("Fever Fill Rate", 0), 0)
                            ft_stat = _coerce_int(stats.get("Fever Time", 0), 0)
                            cache_key = (int(ff_stat), int(ft_stat), tuple(int(x) for x in counts))

                            deltas_t = fg_deltas_cache.get(cache_key)
                            if deltas_t is None:
                                try:
                                    computed = summarize_hitsim_offset_deltas_ms_for_fg_variant(
                                        calc_song, {"ForceGreats": fg_meta, "Stats": stats}, ref_arrays
                                    )
                                except Exception:
                                    computed = None
                                if computed:
                                    try:
                                        deltas_t = tuple(int(x) for x in computed)
                                    except Exception:
                                        deltas_t = None
                                    if deltas_t:
                                        fg_deltas_cache[cache_key] = deltas_t
                            if deltas_t:
                                fg_meta = dict(fg_meta)
                                fg_meta.pop("hitsim_offset_delta_ms", None)
                                fg_meta["hitsim_offset_deltas_ms"] = list(deltas_t)
                                force_obj = dict(force_obj)
                                force_obj["ForceGreats"] = fg_meta
                                force_changed = True

                                # Mirror into details.ForceGreats when present.
                                details = dict(details)
                                det_fg = details.get("ForceGreats")
                                if isinstance(det_fg, dict):
                                    det_fg_out = dict(det_fg)
                                    det_fg_out.pop("hitsim_offset_delta_ms", None)
                                    det_fg_out.setdefault("hitsim_offset_deltas_ms", list(deltas_t))
                                    details["ForceGreats"] = det_fg_out
                                    details_changed = True

                                filled_force_in_base += 1

            if details_changed:
                base_details_updates.append((key.song_name, key.team_buff, key.loadout_hash, _dumps_json(details)))
            if force_changed and isinstance(force_obj, dict):
                base_force_updates.append((key.song_name, key.team_buff, key.loadout_hash, _dumps_json(force_obj)))

        # FG view rows (team_buff_fg_loadouts).
        for e in per_song_fg.get(song_name, []):
            key: _RowKey = e["key"]
            details: dict = e["details"]
            force_obj: dict = e["force"]

            fg_meta = force_obj.get("ForceGreats")
            if not isinstance(fg_meta, dict) or not fg_meta.get("config"):
                continue
            stats = _materialize_stats_from_force(force_obj, fallback_stats=details.get("Stats"))
            if not isinstance(stats, dict) or not stats:
                continue
            counts = _nonfever_counts_from_config(fg_meta.get("config"))
            if not counts:
                continue
            ff_stat = _coerce_int(stats.get("Fever Fill Rate", 0), 0)
            ft_stat = _coerce_int(stats.get("Fever Time", 0), 0)
            cache_key = (int(ff_stat), int(ft_stat), tuple(int(x) for x in counts))

            deltas_t = fg_deltas_cache.get(cache_key)
            if deltas_t is None:
                try:
                    computed = summarize_hitsim_offset_deltas_ms_for_fg_variant(
                        calc_song, {"ForceGreats": fg_meta, "Stats": stats}, ref_arrays
                    )
                except Exception:
                    computed = None
                if computed:
                    try:
                        deltas_t = tuple(int(x) for x in computed)
                    except Exception:
                        deltas_t = None
                    if deltas_t:
                        fg_deltas_cache[cache_key] = deltas_t
            if not deltas_t:
                continue

            fg_meta_out = dict(fg_meta)
            fg_meta_out.pop("hitsim_offset_delta_ms", None)
            fg_meta_out["hitsim_offset_deltas_ms"] = list(deltas_t)
            force_out = dict(force_obj)
            force_out["ForceGreats"] = fg_meta_out

            details_out = dict(details)
            det_fg = details_out.get("ForceGreats")
            if isinstance(det_fg, dict):
                det_fg_out = dict(det_fg)
                det_fg_out.pop("hitsim_offset_delta_ms", None)
                det_fg_out.setdefault("hitsim_offset_deltas_ms", list(deltas_t))
                details_out["ForceGreats"] = det_fg_out

            fg_updates.append(
                (
                    key.song_name,
                    key.team_buff,
                    key.loadout_hash,
                    _dumps_json(details_out),
                    _dumps_json(force_out),
                )
            )
            filled_fg += 1

    if args.dry_run:
        dt = time.perf_counter() - t0
        print(
            f"Dry run complete: songs={processed_songs:,} "
            f"would_fill base={filled_base:,} base_force={filled_force_in_base:,} fg={filled_fg:,} "
            f"elapsed={dt:.1f}s"
        )
        return 0

    # Apply updates.
    t_apply0 = time.perf_counter()
    with conn:
        conn.executemany(
            "UPDATE team_buff_loadouts SET details_json=? WHERE song_name=? AND team_buff=? AND loadout_hash=?",
            [(payload, s, t, h) for (s, t, h, payload) in base_details_updates],
        )
        conn.executemany(
            "UPDATE team_buff_loadouts SET force_details_json=? WHERE song_name=? AND team_buff=? AND loadout_hash=?",
            [(payload, s, t, h) for (s, t, h, payload) in base_force_updates],
        )

        conn.executemany(
            "UPDATE team_buff_fg_loadouts SET details_json=?, force_details_json=? "
            "WHERE song_name=? AND team_buff=? AND loadout_hash=?",
            [(d, f, s, t, h) for (s, t, h, d, f) in fg_updates],
        )

    dt = time.perf_counter() - t0
    print(
        f"Applied updates: songs={processed_songs:,} "
        f"filled base={filled_base:,} base_force={filled_force_in_base:,} fg={filled_fg:,} "
        f"apply_time={time.perf_counter() - t_apply0:.1f}s total_elapsed={dt:.1f}s"
    )
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
