"""Loadout legality / reachability audit -- the "no fake/illegal loadout" monitor.

Sweeps a DB's FG loadouts and verifies EACH is REACHABLE-as-reported against the canonical
server fill-crossing model plus the weighted lane-aware input-engine owner. For every fever section it checks:
  - the reported activation index == the canonical server fill-crossing for the placement, and
  - that activation is reachable under earliest-hittable-first lane matching, and
  - the reported fever_end is within the reachable drain range [base_e, great_e]
    (issue #42 Perfect-floor drain .. issue #44 early-Great extension).
A section that fails is a PHANTOM (over-report): fever started on a note the bar had not yet
filled, or drained past a reachable window -> an illegal/unreachable surface.

Self-sufficient: recomputes raw_fever_fill / real_fever_time from the persisted loadout Stats
(no debug fields needed), so it runs on any production DB.

Usage:
    python tools/dev/audit_loadout_legality.py [--db evolution.db] [--limit N] [--song NAME]
    python tools/dev/audit_loadout_legality.py --db evolution.db --apply
Exit code 1 if any illegal loadout is found (so it can gate a deploy).
"""
from __future__ import annotations
import argparse, json, sqlite3, sys
from math import ceil
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gear_optimizer.core.constants import (
    FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET, TOTAL_ROWS)
from gear_optimizer.data.song_io import get_base_calc_song, scan_song_header
from gear_optimizer.data.database_codecs import _unpack_stats_after_load
from gear_optimizer.solver.score_math import lookup_reference_py
from gear_optimizer.solver.timing_envelope import apply_timing_envelope
from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
    activation_schedule_witnesses_weighted_lane_aware,
    activation_hit_is_reachable_weighted_lane_aware,
    exact_label_hit_intervals,
    server_fill_crossing,
    server_fever_end,
)
from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached

_DIFF_DIRS = ("Easy", "Normal", "Hard")
_CHART_PATHS_BY_NAME: dict[str, str] | None = None


def _chart_path(song_name: str) -> str | None:
    global _CHART_PATHS_BY_NAME
    if _CHART_PATHS_BY_NAME is None:
        paths: dict[str, str] = {}
        for diff in _DIFF_DIRS:
            for fp in (ROOT / "Data" / diff).glob("*.txt"):
                name = str((scan_song_header(str(fp)) or {}).get("Song Name", "") or "").strip()
                if name:
                    paths.setdefault(name, str(fp))
        _CHART_PATHS_BY_NAME = paths
    return _CHART_PATHS_BY_NAME.get(str(song_name))


def _factor(stats: dict, key: str, ref: dict) -> float:
    return float(lookup_reference_py(int(stats[key]), np.asarray(ref[key], dtype=np.float32), TOTAL_ROWS))


def audit_fg_loadout(fg: dict, calc_song: dict, ref: dict) -> list[str]:
    """Return a list of violation strings (empty == legal/reachable)."""
    sd = calc_song["song_data"]
    n = int(len(sd["timestamps"]))
    ts = np.asarray(sd["timestamps"], np.float32)
    floor = np.asarray(sd["fg_perfect_floor_timestamps"], np.float32)
    gfloor = np.asarray(sd["fg_great_floor_timestamps"], np.float32)
    pcand = np.asarray(sd["fg_perfect_candidate_timestamps"], np.float32)
    gcand = np.asarray(sd["fg_great_candidate_timestamps"], np.float32)
    lanes = np.asarray(sd["lanes"], np.int32).reshape(-1)
    if any(int(arr.shape[0]) != n for arr in (floor, gfloor, pcand, gcand, lanes)):
        raise ValueError("audit timing arrays and lanes must match timestamps")
    fgp = fg["ForceGreats"]
    # Authoritative fever-window params persisted with the surface (raw_fever_fill == the server's
    # feverFillDenom; real_fever_time == fever duration s). Older DBs carry the _debug_ variants.
    raw = fgp.get("raw_fever_fill", fgp.get("_debug_raw_fever_fill"))
    rft = fgp.get("real_fever_time", fgp.get("_debug_real_fever_time"))
    if raw is None or rft is None:
        raise KeyError("loadout missing raw_fever_fill/real_fever_time (re-solve to persist them)")
    raw = float(raw); rft = float(rft)
    trace = fgp["frontier_trace"]
    viol: list[str] = []
    state = -1
    for e in trace:
        sec = e["section"]
        start = int(e["forced_start_index"])
        run_start = int(e["forced_run_start_index"])
        pc = int(e["forced_run_count"])
        run_count = int(e.get("forced_run_count", pc))
        ra = int(e["activation_index"]); re = int(e["fever_end_index"]); j = e["activation_judgment"]
        run_end = min(n, max(0, run_start) + max(0, run_count))
        ig = np.zeros(n, bool); ig[max(0, run_start):run_end] = True
        if j == "late_great" and ra < n:
            ig[ra] = True
        cross, is_g = server_fill_crossing(ig, raw, start=start, n=n)
        if cross is None:
            viol.append(f"sec{sec}: reported {j}@{ra} but the bar never fills (unreachable)")
            state = re; continue
        lo, hi, secondary_lo, secondary_hi = exact_label_hit_intervals(
            is_great=ig,
            timestamps=ts,
            perfect_floor_timestamps=floor,
            perfect_candidate_timestamps=pcand,
            great_floor_timestamps=gfloor,
            great_candidate_timestamps=gcand,
        )
        units = np.where(ig, np.float32(0.5), np.float32(1.0)).astype(np.float32)
        uncapped_hit = float(gcand[cross]) if is_g else float(pcand[cross])
        hit = float(
            e.get(
                "activation_hit_window_upper_ms",
                e.get("activation_hit_ms", float(uncapped_hit) * 1000.0),
            )
        ) / 1000.0
        base_e = server_fever_end(floor, hit, rft, cross, n=n)
        great_e = server_fever_end(gfloor, hit, rft, cross, n=n)
        kind = "late_great" if is_g else "perfect"
        reachable = activation_hit_is_reachable_weighted_lane_aware(
            activation_index=int(cross),
            activation_hit_timestamp=float(hit),
            low_hit_timestamps=lo,
            high_hit_timestamps=hi,
            lanes=lanes,
            fill_units=units,
            fever_fill_denom=float(raw),
            section_start=int(start),
            section_end=n,
            secondary_low_hit_timestamps=secondary_lo,
            secondary_high_hit_timestamps=secondary_hi,
            predecessor_hit_timestamp=(None if start == 0 else float(floor[start - 1])),
        )
        trace_hit = float(e.get("activation_hit_ms", float(hit) * 1000.0)) / 1000.0
        required_half = e.get("preactivation_fill_half_units")
        preactivation_count = e.get("preactivation_event_count")
        if required_half is None or preactivation_count is None:
            viol.append(f"sec{sec}: missing exact preactivation surface signature")
            state = re
            continue
        exact_surface_witness = activation_schedule_witnesses_weighted_lane_aware(
            activation_index=int(ra),
            activation_hit_timestamp=float(trace_hit),
            low_hit_timestamps=lo,
            high_hit_timestamps=hi,
            lanes=lanes,
            fill_units=units,
            fever_fill_denom=float(raw),
            section_start=int(start),
            section_end=n,
            required_preactivation_fill_half_units=int(required_half),
            required_preactivation_event_count=int(preactivation_count),
            secondary_low_hit_timestamps=secondary_lo,
            secondary_high_hit_timestamps=secondary_hi,
            predecessor_hit_timestamp=(None if start == 0 else float(floor[start - 1])),
        )
        if cross != ra or kind != j:
            viol.append(f"sec{sec}: reported {j}@{ra} but canonical crossing is {kind}@{cross} (PHANTOM activation)")
        elif not reachable:
            viol.append(f"sec{sec}: {kind}@{ra} is index-legal but input-engine unreachable under "
                        f"weighted lane-aware fill (PHANTOM activation)")
        elif not exact_surface_witness:
            viol.append(
                f"sec{sec}: {kind}@{ra} has no exact lane-prefix witness for cached surface "
                f"signature fill_half={required_half}, events={preactivation_count}"
            )
        elif not (base_e <= re <= great_e):
            viol.append(f"sec{sec}: fever_end {re} outside reachable drain [{base_e},{great_e}] (PHANTOM drain)")
        state = re
    return viol


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "evolution.db"))
    ap.add_argument("--limit", type=int, default=0, help="max loadouts to check (0 = all)")
    ap.add_argument("--song", default=None, help="only this song name prefix")
    ap.add_argument("--apply", action="store_true", help="transactionally delete proven-illegal FG rows")
    ap.add_argument("--quiet", action="store_true", help="print only the final summary")
    args = ap.parse_args(argv)

    ref = get_exact_replay_ref_arrays_cached()
    c = sqlite3.connect(args.db); c.row_factory = sqlite3.Row
    if args.apply:
        c.execute("BEGIN IMMEDIATE")
    q = "SELECT rowid, song_name, fg_score, force_details_json FROM team_buff_fg_loadouts WHERE force_details_json IS NOT NULL"
    params: tuple[str, ...] = ()
    if args.song:
        q += " AND song_name LIKE ?"
        params = (f"{args.song}%",)
    q += " ORDER BY song_name"
    rows = c.execute(q, params).fetchall()
    if args.limit:
        rows = rows[: args.limit]

    calc_cache: dict[str, dict] = {}
    checked = illegal = skipped = 0
    illegal_rowids: list[int] = []
    affected_songs: set[str] = set()
    top_rows_removed = 0
    songs_without_fg = 0
    for r in rows:
        name = r["song_name"]
        if name not in calc_cache:
            fp = _chart_path(name)
            if not fp:
                calc_cache[name] = None
            else:
                cs = get_base_calc_song(fp, {}); apply_timing_envelope(cs, mode="perfect_window")
                calc_cache[name] = cs
        calc_song = calc_cache[name]
        if calc_song is None:
            skipped += 1; continue
        try:
            fg = _unpack_stats_after_load(json.loads(r["force_details_json"]))
            if "ForceGreats" not in fg or not fg["ForceGreats"].get("frontier_trace"):
                skipped += 1; continue
            viol = audit_fg_loadout(fg, calc_song, ref)
        except Exception as exc:
            print(f"  [skip] {name}: {exc}"); skipped += 1; continue
        checked += 1
        if viol:
            illegal += 1
            illegal_rowids.append(int(r["rowid"]))
            affected_songs.add(str(name))
            if not args.quiet:
                print(f"ILLEGAL  {name} (fg={int(r['fg_score']):,}):")
                for v in viol:
                    print(f"           {v}")
    if args.apply:
        if skipped:
            c.rollback()
            c.close()
            raise RuntimeError("refusing legality cleanup because one or more rows could not be audited")
        illegal_rowid_set = set(illegal_rowids)
        for song_name in affected_songs:
            top = c.execute(
                "SELECT rowid FROM team_buff_fg_loadouts WHERE song_name=? AND UPPER(COALESCE(team_buff,''))='T5' "
                "ORDER BY fg_score DESC, loadout_hash ASC LIMIT 1",
                (song_name,),
            ).fetchone()
            top_rows_removed += int(top is not None and int(top[0]) in illegal_rowid_set)
        c.executemany("DELETE FROM team_buff_fg_loadouts WHERE rowid=?", [(rowid,) for rowid in illegal_rowids])
        for song_name in sorted(affected_songs):
            row = c.execute(
                "SELECT MAX(fg_score) FROM team_buff_fg_loadouts WHERE song_name=? AND UPPER(COALESCE(team_buff,''))='T5'",
                (song_name,),
            ).fetchone()
            c.execute(
                "UPDATE songs SET best_fg_score=?, last_updated=strftime('%s','now') WHERE name=?",
                (int(row[0] or 0) if row else 0, song_name),
            )
            songs_without_fg += int(row is None or int(row[0] or 0) <= 0)
        if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            c.rollback()
            c.close()
            raise RuntimeError("database integrity_check failed after legality cleanup")
        c.commit()
    c.close()
    verb = "removed" if args.apply else "found"
    print(
        f"=== legality audit: {checked} checked, {illegal} ILLEGAL {verb}, "
        f"{skipped} skipped, {len(affected_songs)} songs affected, "
        f"{top_rows_removed} top rows removed, {songs_without_fg} songs without FG ({args.db}) ==="
    )
    return 0 if args.apply or illegal == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
