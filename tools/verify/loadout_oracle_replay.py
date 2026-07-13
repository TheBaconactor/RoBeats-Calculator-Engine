"""Game-faithful replay of a persisted FG loadout through the WebPort ScoreEngine oracle.

Given a DB, a song, and a rank (0 = top by fg_score), this tool:
  1. decodes the loadout's persisted ForceGreats surface (frontier_trace and visible stats),
  2. reconstructs the per-note play (Perfect/Great + hit offsets) via the canonical
     ``force_greats_note_graph`` witness reconstruction,
  3. reads the persisted post-gem visible stat vector and maps it into the WebPort
     ``GEAR_STAT_TYPES`` raw-point statsdict the oracle expects,
  4. replays the resulting event stream through ``tools/verify/webport_oracle/oracle.mjs`` (a 1:1
     port of the game's ScoreEngine / fever gate),
  5. prints the GAME score + fever membership (feverHits, per-section activation/end/noteCount)
     and DIFFS it against the persisted surface -- in particular the PHANTOM fever notes: surface
     notes the game does NOT fever because its (reachable) activation ends the window earlier.

This is the trouble-checking harness for the chord-reachability workstream: the surface score is
what the optimizer *claims*; the oracle score is what the game would *actually* award for the
exact same reconstructed play. A gap is an over-report (surface fevers notes the reachable
activation can't reach) or, run against an old phantom loadout, the LEGAL replay value of a
placement the fixed frontier now forbids.

Usage:
    python tools/verify/loadout_oracle_replay.py --db .calc/aurora_fix.db --song "Aurora" [--rank 0]

The fever MEMBERSHIP (which notes are fevered, per-section activation index/ms + window endMs,
feverHits) is gem-INDEPENDENT and authoritative. The exact SCORE additionally requires the
post-gem visible stat vector stored in ``BaseStats`` by the current DB contract.
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gear_optimizer.data.database_codecs import _unpack_stats_after_load  # noqa: E402
from gear_optimizer.data.song_io import get_base_calc_song, scan_song_header  # noqa: E402
from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats  # noqa: E402
from gear_optimizer.solver.fg_response_scoring.note_graph import (  # noqa: E402
    force_greats_note_graph,
)
from gear_optimizer.solver.fg_response_scoring.physical_replay import (  # noqa: E402
    validate_force_greats_physical_replay,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (  # noqa: E402
    reconstruct_force_greats_response_trace,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_types import (  # noqa: E402
    FgResponseSurface,
)
from tools.verify.game_sim import _synth_offset  # noqa: E402

_DIFF_DIRS = ("Easy", "Normal", "Hard")
_ORACLE = ROOT / "tools" / "verify" / "webport_oracle" / "oracle.mjs"

# Optimizer stat name -> WebPort GEAR_STAT_TYPE (score-relevant subset). The oracle runs these
# RAW point counts through its own fN curves, so we feed the FINAL (base+gem) point count.
_STAT_TO_WEBPORT = {
    "Perfect Points": "PerfectPoints",
    "Combo Multiplier": "ComboMultiplier",
    "Fever Multiplier": "FeverMultiplier",
    "Fever Time": "FeverTime",
    "Fever Fill Rate": "FeverFillRate",
}
# Elemental color stat -> WebPort color-stat key (colorStatForName parity).
_COLOR_TO_WEBPORT = {
    "Chill": "ColorBlue",
    "Vibe": "ColorGreen",
    "Flow": "ColorPurple",
    "Rush": "ColorRed",
    "Beat": "ColorOrange",
}


def _chart_path(song_name_or_prefix: str) -> tuple[str, str]:
    """Return (abs_path, exact_song_name) for a song name / prefix. Fails loud if ambiguous/absent."""
    matches: list[tuple[str, str]] = []
    for diff in _DIFF_DIRS:
        for fp in glob.glob(str(ROOT / "Data" / diff / "*.txt")):
            name = (scan_song_header(fp) or {}).get("Song Name", "")
            if name == song_name_or_prefix or name.lower().startswith(song_name_or_prefix.lower()):
                matches.append((fp, name))
    if not matches:
        raise SystemExit(f"no chart file found for song {song_name_or_prefix!r}")
    exact = [m for m in matches if m[1] == song_name_or_prefix]
    if exact:
        return exact[0]
    if len(matches) > 1:
        names = sorted({m[1] for m in matches})
        raise SystemExit(f"song {song_name_or_prefix!r} is ambiguous: {names}")
    return matches[0]


def _load_loadout(db: str, song_name_or_prefix: str, rank: int) -> tuple[dict, str, int, int, str, str]:
    """Return (force_details, exact_song_name, surface_fg_score, surface_base_score,
    primary_color, secondary_color) at rank N. The color pair (`details_json` `pc`/`sc`) is
    needed so the oracle gets BOTH chart colors -- feeding only the Selected Element manufactures a
    single-color colorPointBonus and a spurious delta on two-color loadouts."""
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    # Resolve the exact stored song_name (the DB stores the full "Name (Diff) by Artist").
    like = f"{song_name_or_prefix}%"
    rows = con.execute(
        "SELECT song_name, score, fg_score, force_details_json, details_json FROM team_buff_fg_loadouts "
        "WHERE force_details_json IS NOT NULL AND (song_name = ? OR song_name LIKE ?) "
        "ORDER BY fg_score DESC",
        (song_name_or_prefix, like),
    ).fetchall()
    if not rows:
        raise SystemExit(f"no FG loadout in {db} for song {song_name_or_prefix!r}")
    names = sorted({r["song_name"] for r in rows})
    if len(names) > 1:
        raise SystemExit(f"song {song_name_or_prefix!r} matches multiple stored songs: {names}")
    if rank < 0 or rank >= len(rows):
        raise SystemExit(f"rank {rank} out of range (only {len(rows)} loadouts for {names[0]!r})")
    row = rows[rank]
    fd = _unpack_stats_after_load(json.loads(row["force_details_json"]))
    det = json.loads(row["details_json"]) if row["details_json"] else {}
    primary = str(det.get("pc") or fd.get("Selected Element") or fd.get("SelectedElement") or "")
    secondary = str(det.get("sc") or primary)
    return fd, row["song_name"], int(row["fg_score"]), int(row["score"]), primary, secondary


def _visible_stats(fd: dict) -> tuple[dict, str]:
    """Read the persisted post-gem visible stats exactly once. Returns (stats, selected color)."""
    stats = read_visible_stats(fd)
    if not stats:
        raise SystemExit("loadout missing visible Stats/BaseStats")
    sel = str(fd.get("Selected Element") or fd.get("SelectedElement") or "")
    return stats, sel


def _statsdict_for_oracle(final: dict, primary: str, secondary: str = "") -> tuple[dict, list[str]]:
    """Map FINAL optimizer stats -> WebPort raw-point statsdict + color-stat key list.

    Feeds BOTH chart colors ([primary, secondary]) so the oracle's colorPointBonus matches the
    game's two-color scoring (primary 2x, secondary 1x). A single-color loadout has secondary ==
    primary and collapses to one entry. Feeding only the Selected Element (the old bug) manufactured
    a spurious ~30% delta on two-color songs.
    """
    sd: dict[str, int] = {}
    for opt_key, wp_key in _STAT_TO_WEBPORT.items():
        sd[wp_key] = int(final.get(opt_key, 0) or 0)
    colors: list[str] = []
    for col in (primary, secondary):
        if not col:
            continue
        wp_color = _COLOR_TO_WEBPORT.get(col)
        if wp_color is None:
            raise SystemExit(f"no WebPort color-stat mapping for color {col!r}")
        sd[wp_color] = int(final.get(col, 0) or 0)
        if wp_color not in colors:
            colors.append(wp_color)  # [primary, secondary]; dedupe single-color (secondary==primary)
    return sd, colors


def _events_from_note_graph(note_graph: list[dict], note_types: np.ndarray) -> list[dict]:
    """One legal physical event per note, including synthesized selector-Great timing."""
    events = []
    if int(note_types.shape[0]) != len(note_graph):
        raise ValueError("note_types length must match note_graph")
    for i, node in enumerate(note_graph):
        result = "great" if node["note_result"] == "Great" else "perfect"
        delta = _synth_offset(result, int(note_types[i]) == 3, node.get("delta_ms"))
        hit_ms = float(node["hit_time_ms"]) + float(delta)
        events.append({"eventMs": hit_ms, "result": result, "kind": "note"})
    return events


def _run_oracle(payload: dict) -> dict:
    if not _ORACLE.exists():
        raise SystemExit(f"oracle not found at {_ORACLE} (build the bundle first, see its README)")
    proc = subprocess.run(
        ["node", str(_ORACLE), "-"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"oracle failed (exit {proc.returncode}):\n{proc.stderr}")
    return json.loads(proc.stdout)


def _surface_sections(fd: dict) -> list[dict]:
    """Compact per-section surface view from the persisted frontier_trace."""
    out = []
    for e in fd["ForceGreats"]["frontier_trace"]:
        out.append(
            {
                "section": int(e.get("section", 0)),
                "activation_index": int(e["activation_index"]),
                "activation_ms": float(e.get("activation_ms", 0.0)),
                "activation_hit_ms": float(e.get("activation_hit_ms", 0.0)),
                "activation_hit_offset_ms": float(e.get("activation_hit_offset_ms", 0.0) or 0.0),
                "activation_judgment": str(e.get("activation_judgment", "")),
                "fever_end_index": int(e["fever_end_index"]),
                "fever_window_end_ms": float(e.get("fever_window_end_ms", 0.0)),
                "forced_start_index": int(e["forced_start_index"]),
                "forced_prefix_count": int(e["forced_prefix_count"]),
                "forced_run_start_index": int(e.get("forced_run_start_index", e["forced_start_index"])),
                "forced_run_count": int(e.get("forced_run_count", e["forced_prefix_count"])),
                "body_fever": int(e.get("body_fever", 0)),
                "early_great_start": int(e.get("early_great_start", -1)),
                "early_great_end": int(e.get("early_great_end", -1)),
            }
        )
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="SQLite DB with team_buff_fg_loadouts")
    ap.add_argument("--song", required=True, help="song name or unique prefix")
    ap.add_argument("--rank", type=int, default=0, help="0 = top by fg_score (default)")
    ap.add_argument("--dump-input", default=None, help="write the oracle input JSON here (debug)")
    ap.add_argument(
        "--reconstruct-current-trace",
        action="store_true",
        help="rebuild the persisted surface's trace with the current canonical witness owner",
    )
    args = ap.parse_args(argv)

    fd, song_name, surface_fg, surface_base, primary_color, secondary_color = _load_loadout(
        args.db, args.song, args.rank)
    chart_fp, chart_name = _chart_path(song_name)

    cs = get_base_calc_song(chart_fp, {})
    apply_timing_envelope(cs, mode="perfect_window")
    sd = cs["song_data"]
    meta = cs["metadata"]
    ts = np.asarray(sd["timestamps"])
    nt = np.asarray(sd["note_types"])
    lanes = np.asarray(sd["lanes"])
    n = int(len(ts))

    if args.reconstruct_current_trace:
        force = fd["ForceGreats"]
        surface_values = tuple(int(value) for value in fd["response_surface"])
        if len(surface_values) != 11:
            raise ValueError("persisted response_surface must contain exactly 11 fields")
        force["frontier_trace"] = list(
            reconstruct_force_greats_response_trace(
                non_fever_base=int(force["non_fever_base"]),
                target_surface=FgResponseSurface(*surface_values),
                timestamps=np.asarray(sd["fg_timestamps"], dtype=np.float32),
                perfect_candidate_timestamps=np.asarray(
                    sd["fg_perfect_candidate_timestamps"], dtype=np.float32
                ),
                great_candidate_timestamps=np.asarray(
                    sd["fg_great_candidate_timestamps"], dtype=np.float32
                ),
                perfect_floor_timestamps=np.asarray(
                    sd["fg_perfect_floor_timestamps"], dtype=np.float32
                ),
                great_floor_timestamps=np.asarray(
                    sd["fg_great_floor_timestamps"], dtype=np.float32
                ),
                raw_fever_fill=float(force["raw_fever_fill"]),
                real_fever_time=float(force["real_fever_time"]),
                lanes=lanes,
                use_forced_great_timing=True,
            )
        )

    note_graph = force_greats_note_graph(
        frontier_trace=fd["ForceGreats"]["frontier_trace"],
        total_notes=n,
        timestamps=ts,
        note_types=nt,
        lanes=lanes,
        timing_mode="perfect_window",
    )
    physical_replay = validate_force_greats_physical_replay(
        frontier_trace=fd["ForceGreats"]["frontier_trace"],
        surface=FgResponseSurface(*[int(value) for value in fd["response_surface"]]),
        timestamps=ts,
        note_types=nt,
        lanes=lanes,
        raw_fever_fill=float(fd["ForceGreats"]["raw_fever_fill"]),
        real_fever_time=float(fd["ForceGreats"]["real_fever_time"]),
    )
    events = _events_from_note_graph(note_graph, nt)

    final, sel_color = _visible_stats(fd)
    statsdict, colors = _statsdict_for_oracle(final, primary_color, secondary_color)

    taps = int((nt == 1).sum())
    heads = int((nt == 2).sum())
    hit_objects_count = taps + heads  # taps + holds (fever-fill normaliser)
    last_note_time_ms = float(meta.get("Last Note Time", ts[-1] * 1000.0))
    if last_note_time_ms < 1000.0:  # metadata stores seconds in this repo's charts
        last_note_time_ms = float(meta["Last Note Time"]) * 1000.0
    last_note_time_sec = (last_note_time_ms + 1000.0) / 1000.0

    config = {
        "hitCount": n,  # rank-accuracy denominator only; does NOT affect score
        "hitObjectsCount": hit_objects_count,
        "lastNoteTimeSec": last_note_time_sec,
    }
    payload = {"config": config, "statsdict": statsdict, "colors": colors, "events": events}
    if args.dump_input:
        Path(args.dump_input).write_text(json.dumps(payload, indent=1))

    result = _run_oracle(payload)

    # --- Surface reference + phantom diff -------------------------------------------------------
    surface_secs = _surface_sections(fd)
    surface_fever_idx = {node["note_index"] for node in note_graph if node["fever"]}
    game_secs = result["feverSections"]

    # A "phantom" fevered note: fevered on the surface but its physical hit ms lands AFTER the
    # game's reachable fever-window endMs for that section (the game's window closed earlier).
    game_end_bounds = [(s["activationMs"], s["endMs"]) for s in game_secs]
    phantoms = []
    for node in note_graph:
        if not node["fever"]:
            continue
        delta = node.get("delta_ms")
        hit_ms = float(node["hit_time_ms"]) + (float(delta) if delta is not None else 0.0)
        # Which game section (by activation window) would this note belong to?
        in_any = any(a <= hit_ms <= e for (a, e) in game_end_bounds)
        if not in_any and game_end_bounds:
            phantoms.append(
                {
                    "note_index": node["note_index"],
                    "hit_ms": round(hit_ms, 1),
                    "note_result": node["note_result"],
                }
            )

    # ---- Report ----
    lines: list[str] = []
    lines.append(f"SONG      : {song_name}   (chart: {chart_name})")
    lines.append(f"DB        : {args.db}   rank {args.rank}")
    lines.append(f"CONFIG    : hitObjectsCount={hit_objects_count} lastNoteTimeSec={last_note_time_sec:.6f} n={n}")
    lines.append(
        "PHYSICAL  : canonical event-order + judgment + fever replay passed "
        f"({len(physical_replay.event_order)} events)"
    )
    lines.append(f"SELECTED  : element={sel_color} colors={colors}")
    lines.append(f"STATSDICT : {json.dumps(statsdict)}")
    lines.append("")
    lines.append(f"GAME SCORE      : {result['score']:,}")
    lines.append(f"SURFACE FG_SCORE: {surface_fg:,}   (base {surface_base:,})")
    diff = result["score"] - surface_fg
    lines.append(f"DELTA (game-surf): {diff:+,}   ({100.0*diff/surface_fg:+.4f}%)")
    lines.append(
        f"TALLY           : perfect={result['tally']['perfect']} great={result['tally']['great']} "
        f"okay={result['tally']['okay']} miss={result['tally']['miss']}  maxChain={result['maxChain']}"
    )
    lines.append(
        f"FEVER           : feverHits={result['feverHits']} surface_fever_nodes={len(surface_fever_idx)} "
        f"feverPct={result['feverPercentage']:.4f} feverMult={result['feverMult']:.4f} "
        f"feverTimeSec={result['feverTimeSec']:.4f} feverFillDenom={result['feverFillDenom']:.4f}"
    )
    lines.append("")
    lines.append("PER-SECTION (game vs surface):")
    for i, gs in enumerate(game_secs):
        ss = surface_secs[i] if i < len(surface_secs) else {}
        lines.append(
            f"  sec{i+1} GAME: activationIndex={gs['activationEventIndex']} "
            f"activationMs={gs['activationMs']:.1f} endMs={gs['endMs']:.1f} noteCount={gs['noteCount']}"
        )
        if ss:
            lines.append(
                f"        SURF: activation_index={ss['activation_index']} "
                f"activation_hit_ms={ss['activation_hit_ms']:.1f} "
                f"fever_window_end_ms={ss['fever_window_end_ms']:.1f} "
                f"fever_end_index={ss['fever_end_index']} "
                f"forced_prefix={ss['forced_prefix_count']} judgment={ss['activation_judgment']}"
            )
    lines.append("")
    lines.append(f"PHANTOM fevered notes (surface-fevered, past game window end): {len(phantoms)}")
    for p in phantoms:
        lines.append(f"    note {p['note_index']} @{p['hit_ms']}ms result={p['note_result']}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
