import argparse
import json
import os
import sqlite3
import sys

import numpy as np


def _parse_counts(raw: str) -> list[int]:
    raw = (raw or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",")]
    out: list[int] = []
    for p in parts:
        if not p:
            continue
        out.append(int(p))
    return out


def _find_song_file(repo_root: str, song_name: str) -> str | None:
    data_root = os.path.join(repo_root, "Data")
    if not os.path.isdir(data_root):
        return None
    for diff in ("Easy", "Normal", "Hard"):
        candidate = os.path.join(data_root, diff, f"{song_name}.txt")
        if os.path.exists(candidate):
            return candidate
    return None


def _load_ref_arrays(repo_root: str) -> dict[str, np.ndarray]:
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.core.constants import TOTAL_ROWS

    table_path = os.path.join(repo_root, "Data", "Gear", "Stats.txt")
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
    return ref_arrays


def _load_calc_song(song_fp: str) -> dict:
    from gear_optimizer.pipeline.song_processor import read_song_file

    data = read_song_file(song_fp)
    return {
        "metadata": data["song_details"],
        "song_data": {"timestamps": np.array(data["timestamps"], dtype=np.float64)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe ForceGreats configurations for a song/loadout using full FT/FF search."
    )
    parser.add_argument("--db", default="evolution.db", help="Path to evolution.db (default: evolution.db)")
    parser.add_argument(
        "--song", required=True, help="Song name key (must match DB song_name, including difficulty suffix if present)"
    )
    parser.add_argument(
        "--forced",
        action="append",
        default=[],
        help="Comma-separated forced-great counts per non-fever section (e.g. '2,0'). Can be repeated.",
    )
    parser.add_argument(
        "--range",
        default="",
        help="Optional FT/FF gem bounds as start_ft,end_ft,start_ff,end_ff (e.g. '0,90,0,90').",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    os.chdir(repo_root)
    sys.path.insert(0, repo_root)

    song_name = args.song.strip()
    song_fp = _find_song_file(repo_root, song_name)
    if not song_fp:
        raise SystemExit(f"Could not find song file for {song_name!r} in Data/(Easy|Normal|Hard)/")

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    row = cur.execute(
        "select details_json from team_buff_loadouts where song_name=? order by score desc limit 1",
        (song_name,),
    ).fetchone()
    if not row:
        raise SystemExit(f"No loadouts found in DB for song {song_name!r}")

    details = json.loads(row[0])
    stats = details.get("Stats") or {}
    ft = int(details.get("FT", 0) or 0)
    ff = int(details.get("FF", 0) or 0)
    gem_counts = details.get("GemCounts") or {}
    selected = details.get("SelectedElement") or details.get("Selected Element") or ""

    from gear_optimizer.solver.scoring.force_greats import _extract_base_stats, evaluate_fg_with_gem_iteration

    base_stats = _extract_base_stats(stats, gem_counts, selected, ft, ff)
    calc_song = _load_calc_song(song_fp)
    ref_arrays = _load_ref_arrays(repo_root)

    search_ranges = None
    if args.range:
        bounds = _parse_counts(args.range)
        if len(bounds) != 4:
            raise SystemExit("--range must be start_ft,end_ft,start_ff,end_ff")
        search_ranges = tuple(bounds)

    baseline = evaluate_fg_with_gem_iteration(
        base_stats,
        calc_song,
        ref_arrays,
        selected,
        forced_counts=[0, 0],
        search_ranges=search_ranges,
        use_gpu=False,
    )
    if not baseline:
        raise SystemExit("Baseline evaluation failed.")

    base_score = int(baseline["final_score"])
    print(f"Song: {song_name}")
    print(
        f"DB Best (forced=[0,0]): {base_score:,}  (FT={baseline['FT']}, FF={baseline['FF']}, gems={baseline['gem_counts']})"
    )

    forced_specs = args.forced or []
    if not forced_specs:
        return 0

    for raw in forced_specs:
        forced = _parse_counts(raw)
        if not forced:
            continue
        res = evaluate_fg_with_gem_iteration(
            base_stats,
            calc_song,
            ref_arrays,
            selected,
            forced_counts=forced,
            search_ranges=search_ranges,
            use_gpu=False,
        )
        if not res:
            print(f"forced={forced} -> (evaluation failed)")
            continue
        score = int(res["final_score"])
        delta = score - base_score
        print(
            f"forced={forced} -> {score:,}  (delta {delta:+,})  (FT={res['FT']}, FF={res['FF']}, gems={res['gem_counts']})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
