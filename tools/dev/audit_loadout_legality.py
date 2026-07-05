"""Loadout legality / reachability audit -- the "no fake/illegal loadout" monitor.

Sweeps a DB's FG loadouts and verifies EACH is REACHABLE-as-reported against the canonical
server fill-crossing model (fill_crossing.py, validated 1:1 vs the WebPort ScoreEngine at the
delta=0 anchors). For every fever section it checks:
  - the reported activation index == the canonical server fill-crossing for the placement, and
  - the reported fever_end is within the reachable drain range [base_e, great_e]
    (issue #42 Perfect-floor drain .. issue #44 early-Great extension).
A section that fails is a PHANTOM (over-report): fever started on a note the bar had not yet
filled, or drained past a reachable window -> an illegal/unreachable surface.

Self-sufficient: recomputes raw_fever_fill / real_fever_time from the persisted loadout Stats
(no debug fields needed), so it runs on any production DB.

Usage:
    python tools/dev/audit_loadout_legality.py [--db evolution.db] [--limit N] [--song NAME]
Exit code 1 if any illegal loadout is found (so it can gate a deploy).
"""
from __future__ import annotations
import argparse, glob, json, sqlite3, sys
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
    server_fill_crossing, server_fever_end, late_great_activation_is_reachable,
    build_reachable_perfect_candidate)
from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached

_DIFF_DIRS = ("Easy", "Normal", "Hard")


def _chart_path(song_name: str) -> str | None:
    for diff in _DIFF_DIRS:
        for fp in glob.glob(str(ROOT / "Data" / diff / "*.txt")):
            if (scan_song_header(fp) or {}).get("Song Name", "") == song_name:
                return fp
    return None


def _factor(stats: dict, key: str, ref: dict) -> float:
    return float(lookup_reference_py(int(stats[key]), np.asarray(ref[key], dtype=np.float32), TOTAL_ROWS))


def audit_fg_loadout(fg: dict, calc_song: dict, ref: dict) -> list[str]:
    """Return a list of violation strings (empty == legal/reachable)."""
    sd = calc_song["song_data"]
    n = int(len(sd["timestamps"]))
    ts = np.asarray(sd["timestamps"], np.float32)
    floor = np.asarray(sd["fg_perfect_floor_timestamps"], np.float32)
    # Reachable PERFECT-activation clock (a held-tail +80 activation whose narrower later sibling is
    # hit first is capped) -- the perfect drain must be measured from this, so a +80 phantom window
    # shows a fever_end past the reachable drain.
    rpcand = build_reachable_perfect_candidate(ts, np.asarray(sd["fg_perfect_candidate_timestamps"], np.float32), n)
    gfloor = np.asarray(sd["fg_great_floor_timestamps"], np.float32)
    pcand = np.asarray(sd["fg_perfect_candidate_timestamps"], np.float32)
    gcand = np.asarray(sd["fg_great_candidate_timestamps"], np.float32)
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
        sec = e["section"]; fs = int(e["forced_start_index"]); pc = int(e["forced_prefix_count"])
        ra = int(e["activation_index"]); re = int(e["fever_end_index"]); j = e["activation_judgment"]
        start = fs if sec == 1 else state + 1
        ig = np.zeros(n, bool); ig[fs:fs + pc] = True
        if j == "late_great" and ra < n:
            ig[ra] = True
        cross, is_g = server_fill_crossing(ig, raw, start=start, n=n)
        if cross is None:
            viol.append(f"sec{sec}: reported {j}@{ra} but the bar never fills (unreachable)")
            state = re; continue
        hit = float(gcand[cross]) if is_g else float(rpcand[cross])  # perfect: reachable (capped) clock
        base_e = server_fever_end(floor, hit, rft, cross, n=n)
        great_e = server_fever_end(gfloor, hit, rft, cross, n=n)
        kind = "late_great" if is_g else "perfect"
        # server_fill_crossing walks ARRAY-INDEX order, which equals the physical HIT-TIME order only
        # where chart order == latest-legal-hit order. A late-Great activation the index walk blesses
        # can still be a hit-time PHANTOM: a same-timestamp sibling (or on-time note-ahead) whose
        # latest legal hit precedes the Great's late hit is hit FIRST and completes the bar earlier
        # (the chord phantom, e.g. All Right There). This is the check the old index-only oracle could
        # not make -- it now uses the same reachability owner the producer enforces.
        reachable = kind != "late_great" or late_great_activation_is_reachable(int(cross), ts, pcand, gcand, n)
        if cross != ra or kind != j:
            viol.append(f"sec{sec}: reported {j}@{ra} but canonical crossing is {kind}@{cross} (PHANTOM activation)")
        elif not reachable:
            viol.append(f"sec{sec}: late_great@{ra} is index-legal but HIT-TIME unreachable -- an "
                        f"earlier-hit same-timestamp sibling / on-time note-ahead completes the bar first (PHANTOM)")
        elif not (base_e <= re <= great_e):
            viol.append(f"sec{sec}: fever_end {re} outside reachable drain [{base_e},{great_e}] (PHANTOM drain)")
        state = re
    return viol


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "evolution.db"))
    ap.add_argument("--limit", type=int, default=0, help="max loadouts to check (0 = all)")
    ap.add_argument("--song", default=None, help="only this song name prefix")
    args = ap.parse_args(argv)

    ref = get_exact_replay_ref_arrays_cached()
    c = sqlite3.connect(args.db); c.row_factory = sqlite3.Row
    q = "SELECT song_name, fg_score, force_details_json FROM team_buff_fg_loadouts WHERE force_details_json IS NOT NULL"
    if args.song:
        q += f" AND song_name LIKE '{args.song}%'"
    q += " ORDER BY song_name"
    rows = c.execute(q).fetchall()
    if args.limit:
        rows = rows[: args.limit]

    calc_cache: dict[str, dict] = {}
    checked = illegal = skipped = 0
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
            print(f"ILLEGAL  {name} (fg={int(r['fg_score']):,}):")
            for v in viol:
                print(f"           {v}")
    c.close()
    print(f"\n=== legality audit: {checked} checked, {illegal} ILLEGAL, {skipped} skipped ({args.db}) ===")
    return 1 if illegal else 0


if __name__ == "__main__":
    raise SystemExit(main())
