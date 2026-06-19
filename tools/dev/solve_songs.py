#!/usr/bin/env python3
"""Solve specific songs and print the #1 (base + ForceGreats) loadout.

Reusable replacement for the ad-hoc single-song dance: resolve a loose song name
to exactly one chart, run the production optimizer (`main.py`) into a dedicated
DB, then decode and print the top base + top ForceGreats loadout (gear, minis,
gems, scores) with a fever-activation legality note.

Usage:
    python tools/dev/solve_songs.py "00 (Hard) by garlagan|Hard" "Canon In D Major|Normal"
    python tools/dev/solve_songs.py --repeats 2 "ATHAZA|Easy"
    python tools/dev/solve_songs.py --db .calc/run.db --reuse-db "00|Hard"
    python tools/dev/solve_songs.py --no-run --db .calc/run.db "00|Hard"   # decode only

Each positional SONG arg is  "NAME|DIFFICULTY":
    NAME        case-insensitive substring of the chart header "Song Name"
    DIFFICULTY  Easy | Normal | Hard
NAME is resolved against Data/<DIFFICULTY>/ and must match exactly one chart
(fails loud on 0 or >1 matches -- the >1 listing tells you how to disambiguate).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from gear_optimizer.data.database_codecs import _unpack_id_groups, _unpack_id_list
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.data.piece_encoding_store import _load_piece_name_encoding_maps
from gear_optimizer.data.song_io import scan_song_header

DIFF_FOLDERS = {"easy": "Easy", "normal": "Normal", "hard": "Hard"}


def _fail(msg: str):
    raise SystemExit(f"[solve_songs] {msg}")


def parse_song_arg(arg: str) -> tuple[str, str]:
    if "|" not in arg:
        _fail(f"bad SONG arg {arg!r}; expected 'NAME|DIFFICULTY'")
    name_q, diff_raw = (p.strip() for p in arg.rsplit("|", 1))
    diff_key = diff_raw.lower()
    if diff_key not in DIFF_FOLDERS:
        _fail(f"bad difficulty {diff_raw!r} in {arg!r}; expected Easy|Normal|Hard")
    if not name_q:
        _fail(f"empty song name in {arg!r}")
    return name_q, DIFF_FOLDERS[diff_key]


def resolve_chart(name_q: str, difficulty: str) -> str:
    """Return the one chart header 'Song Name' in Data/<difficulty>/ whose name
    contains name_q (case-insensitive). Fail loud on 0 or >1 matches."""
    diff_dir = REPO / "Data" / difficulty
    if not diff_dir.is_dir():
        _fail(f"missing chart folder: {diff_dir}")
    q = name_q.lower()
    matches: list[str] = []
    for fp in sorted(diff_dir.glob("*.txt")):
        meta = scan_song_header(str(fp))
        nm = str((meta or {}).get("Song Name", "") or "")
        if nm and q in nm.lower():
            matches.append(nm)
    if not matches:
        _fail(f"no chart in Data/{difficulty}/ matches {name_q!r}")
    if len(matches) > 1:
        listing = "\n".join(f"      - {m}" for m in matches)
        _fail(f"{len(matches)} charts match {name_q!r} in {difficulty}; be more specific:\n{listing}")
    return matches[0]


def run_solve(song_name: str, difficulty: str, db_path: Path, repeats: int, idx: int) -> None:
    cfg_path = db_path.parent / f"_solve_cfg_{idx}.ini"
    cfg_path.write_text(
        "[CalculateSong]\n"
        f"Song_Name = {song_name}\n"
        f"Difficulty = {difficulty}\n"
        "TargetPrimary = All\n"
        "TargetSecondary = All\n"
        "LoopForever = false\n\n"
        "[IterationEngine]\n"
        f"SongRepeats = {repeats}\n"
        "SongQueueLimit = 1\n",
        encoding="utf-8",
    )
    log_path = db_path.parent / f"_solve_log_{idx}.log"
    env = dict(os.environ)
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["METAFINDER_CONFIG_PATH"] = str(cfg_path)
    print(f"  solving: {song_name} ({difficulty})  [repeats={repeats}] ...", flush=True)
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.run(
            [sys.executable, str(REPO / "main.py")],
            env=env, stdout=log, stderr=subprocess.STDOUT,
        )
    cfg_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-25:])
        _fail(f"solve failed for {song_name!r} (exit {proc.returncode}); log tail:\n{tail}")
    log_path.unlink(missing_ok=True)


def _decode_loadout(row: sqlite3.Row, emaps) -> dict:
    gids = _unpack_id_list(row["gear_ids_blob"]) or []
    gear = [emaps.gear_id_to_name.get(int(i), "?") for i in gids if int(i) > 0]
    groups = _unpack_id_groups(row["minis_ids_blob"]) or []
    mgroups = [[emaps.mini_id_to_name.get(int(i), "?") for i in g if int(i) > 0] for g in groups]
    minis = representative_mini_names([g for g in mgroups if g])
    det = json.loads(row["details_json"]) if row["details_json"] else {}
    return {"gear": gear, "minis": minis, "det": det}


def _gem_line(det: dict) -> str:
    gc = list(det.get("gc", [0, 0, 0, 0])) + [0, 0, 0, 0]
    ft, ff = int(det.get("FT", 0)), int(det.get("FF", 0))
    total = ft + ff + sum(int(x) for x in gc[:4])
    return (f"FeverTime {ft} | FeverFill {ff} | Perfect {int(gc[0])} | Combo {int(gc[1])} | "
            f"FeverMul {int(gc[2])} | Element/Overflow {int(gc[3])}   (total {total})")


def _activation_summary(row: sqlite3.Row) -> str:
    """Per-section fever activation judgments; flag late_great (the kind that can
    exceed the game's legal Great window: +150 ms solo / +300 ms held-tail)."""
    try:
        fg = json.loads(row["force_details_json"]).get("ForceGreats", {})
    except Exception:
        return "n/a"
    trace = fg.get("frontier_trace") or []
    if not trace:
        return "no fever sections"
    parts: list[str] = []
    suspect = False
    for i, e in enumerate(trace):
        j = e.get("activation_judgment")
        off = e.get("activation_hit_offset_ms")
        offs = f"{off:+.0f}ms" if isinstance(off, (int, float)) else "?"
        parts.append(f"sec{i}:{j}@{offs}")
        if j == "late_great":
            suspect = True
    flag = ("  [!] late_great present -- verify against legal Great window (+150 solo/+300 held)"
            if suspect else "  [ok] activations within Perfect/early-Great")
    return " ".join(parts) + flag


def _emit_loadout(title: str, row: sqlite3.Row, dec: dict) -> None:
    det = dec["det"]
    print(f"\n  [{title}]  team_buff={row['team_buff']}  element={det.get('se')}  "
          f"colors={det.get('pc')}/{det.get('sc')}")
    print(f"    base = {int(row['score'] or 0):,}    fg = {int(row['fg_score'] or 0):,}")
    print(f"    Gear : {', '.join(dec['gear'])}")
    print(f"    Minis: {', '.join(dec['minis'])}")
    print(f"    Gems : {_gem_line(det)}")


def report_song(db_path: Path, song_name: str) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        emaps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))
        srow = conn.execute("SELECT best_score, best_fg_score FROM songs WHERE name=?", (song_name,)).fetchone()
        base = conn.execute(
            "SELECT * FROM team_buff_loadouts WHERE song_name=? ORDER BY score DESC LIMIT 1", (song_name,)
        ).fetchone()
        fg = conn.execute(
            "SELECT * FROM team_buff_fg_loadouts WHERE song_name=? ORDER BY fg_score DESC LIMIT 1", (song_name,)
        ).fetchone()
        print("=" * 78)
        print(f"SONG: {song_name}")
        if srow:
            print(f"  best base = {int(srow['best_score'] or 0):,}    best FG = {int(srow['best_fg_score'] or 0):,}")
        if base is None and fg is None:
            print("  (no loadouts found in DB -- run without --no-run first)")
            return
        bdec = _decode_loadout(base, emaps) if base else None
        fdec = _decode_loadout(fg, emaps) if fg else None
        same_gear = bool(bdec and fdec and bdec["gear"] == fdec["gear"] and bdec["minis"] == fdec["minis"])

        if bdec:
            _emit_loadout("TOP LOADOUT (best base)", base, bdec)
        if fdec and not same_gear and int(fg["fg_score"] or 0) > int((base["fg_score"] if base else 0) or 0):
            _emit_loadout("FG-SPECIALIZED (best FG, different gear)", fg, fdec)
        elif fdec and same_gear:
            print("    FG-optimal: same gear as above (force-greats need no gear change)")
        if fg is not None:
            print(f"    FG activations: {_activation_summary(fg)}")
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Solve specific songs and print the #1 loadout.")
    ap.add_argument("songs", nargs="+", help="one or more 'NAME|DIFFICULTY' (e.g. \"00|Hard\")")
    ap.add_argument("--db", default=".calc/solve.db", help="DB path (default .calc/solve.db, relative to repo root)")
    ap.add_argument("--repeats", type=int, default=1, help="SongRepeats per song (default 1)")
    ap.add_argument("--reuse-db", action="store_true", help="don't wipe the DB before solving (accumulate best)")
    ap.add_argument("--no-run", action="store_true", help="skip solving; just decode the existing DB")
    args = ap.parse_args(argv)

    specs = [parse_song_arg(a) for a in args.songs]
    db_path = Path(args.db) if os.path.isabs(args.db) else (REPO / args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    resolved: list[tuple[str, str]] = []
    for name_q, diff in specs:
        full = resolve_chart(name_q, diff)
        resolved.append((full, diff))
        print(f"resolved: {name_q!r} ({diff}) -> {full}")

    if not args.no_run:
        if not args.reuse_db:
            for suffix in ("", "-wal", "-shm"):
                p = Path(str(db_path) + suffix)
                if p.exists():
                    p.unlink()
        for i, (full, diff) in enumerate(resolved):
            run_solve(full, diff, db_path, args.repeats, i)

    if not db_path.exists():
        _fail(f"DB not found: {db_path} (run without --no-run first)")
    print()
    for full, _diff in resolved:
        report_song(db_path, full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
