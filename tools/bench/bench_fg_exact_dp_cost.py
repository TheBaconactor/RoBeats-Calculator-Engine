"""
Benchmark: exact Force Greats DP cost (count-only vs timing-aware carry).

This is a reference-only bench. It does NOT change production behavior.

Examples:
  python tools/bench/bench_fg_exact_dp_cost.py --song-fp "Data/Hard/Insight by Haywyre.txt" --mode timing_aware
  python tools/bench/bench_fg_exact_dp_cost.py --song-fp "Data/Hard/Insight by Haywyre.txt" --mode count_only

Notes:
  - Timing-aware mode uses the shared timing-envelope FG stream.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _resolve_song_fp(cfg_dict: dict, song_fp: str | None) -> str:
    if song_fp:
        return str(song_fp)

    calc = cfg_dict.get("CalculateSong", {}) if isinstance(cfg_dict, dict) else {}
    song_name = str(calc.get("Song_Name") or "").strip()
    difficulty = str(calc.get("Difficulty") or "").strip()
    if not song_name or not difficulty:
        raise SystemExit("Missing --song-fp and config.ini CalculateSong.Song_Name/Difficulty not set. Pass --song-fp.")

    folder = os.path.join("Data", difficulty)
    if not os.path.isdir(folder):
        raise SystemExit(f"Could not find difficulty folder: {folder!r}. Pass --song-fp.")

    exact = os.path.join(folder, f"{song_name}.txt")
    if os.path.isfile(exact):
        return exact

    matches: list[str] = []
    for fn in os.listdir(folder):
        if not fn.lower().endswith(".txt"):
            continue
        if song_name.lower() in fn.lower():
            matches.append(os.path.join(folder, fn))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"No chart match for {song_name!r} in {folder!r}. Pass --song-fp.")
    raise SystemExit("Multiple chart matches; pass --song-fp:\n" + "\n".join(f"  - {m}" for m in matches[:30]))


def _load_ref_arrays() -> dict:
    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
    from gear_optimizer.data.csv_parser import read_table
    import numpy as np

    paths = {}
    try:
        paths = load_paths_cache() or {}
    except Exception:
        paths = {}

    stats_path = str((paths.get("Stats", "") or "").strip() or PATHS.stats_csv)
    stats_table = read_table(stats_path)

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]

    ref_arrays: dict = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(v)
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.asarray(temp_list, dtype=np.float32)
    return ref_arrays


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song-fp", type=str, default=None, help="Path to chart .txt (Data/<diff>/<name>.txt).")
    ap.add_argument("--mode", type=str, default="timing_aware", choices=("count_only", "timing_aware"))
    ap.add_argument("--prune", type=int, default=0, help="Enable monotone upper-bound pruning (default 0).")

    # Stat indices (0..160). Defaults are intentionally conservative (worst-case FF cost is often near FF=0).
    ap.add_argument("--pp", type=int, default=0)
    ap.add_argument("--cm", type=int, default=0)
    ap.add_argument("--fm", type=int, default=0)
    ap.add_argument("--ff", type=int, default=0)
    ap.add_argument("--ft", type=int, default=0)

    # Element stats for primary/secondary colors (do not affect DP cost materially; keep simple defaults).
    ap.add_argument("--pval", type=int, default=0)
    ap.add_argument("--sval", type=int, default=0)

    args = ap.parse_args()

    from gear_optimizer.core.config import load_config
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.fg_exact_dp import solve_force_greats_exact_dp

    cfg = load_config()
    cfg_dict = {}
    try:
        # Keep bench lightweight; only CalculateSong is needed for --song-fp auto-resolution.
        if cfg.has_section("CalculateSong"):
            cfg_dict["CalculateSong"] = dict(cfg.items("CalculateSong"))
    except Exception:
        cfg_dict = {}

    song_fp = _resolve_song_fp(cfg_dict, args.song_fp)
    base = get_base_calc_song(song_fp, cfg_dict)
    calc_song = clone_calc_song(base)

    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    apply_timing_envelope(calc_song)

    ref_arrays = _load_ref_arrays()

    meta = calc_song.get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color", "") or "")
    s_color = str(meta.get("Secondary Color", "") or "")

    stats = {
        "Perfect Points": int(args.pp),
        "Combo Multiplier": int(args.cm),
        "Fever Multiplier": int(args.fm),
        "Fever Fill Rate": int(args.ff),
        "Fever Time": int(args.ft),
    }
    if p_color:
        stats[p_color] = int(args.pval)
    if s_color:
        stats[s_color] = int(args.sval)

    # Print minimal context for the run.
    song_data = calc_song.get("song_data", {}) or {}
    ts = song_data.get("fg_timestamps", song_data.get("timestamps"))
    n = len(ts) if ts is not None else 0
    use_carry = bool(song_data.get("fg_great_candidate_timestamps") is not None)
    print(
        f"[fg-dp] song_fp={song_fp!r} notes={n} mode={args.mode} prune={bool(_truthy(args.prune))} "
        f"timing_envelope=True carry_ts={use_carry}"
    )
    print(f"[fg-dp] stats(pp,cm,fm,ff,ft)=({args.pp},{args.cm},{args.fm},{args.ff},{args.ft})")

    t0 = time.perf_counter()
    sol = solve_force_greats_exact_dp(
        stats=stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        mode=str(args.mode),
        prune=bool(_truthy(args.prune)),
    )
    dt = time.perf_counter() - t0

    print(
        f"[fg-dp] wall={dt:.3f}s states={sol.profile.states:,} transitions={sol.profile.transitions:,} "
        f"sections={len(sol.section_counts)} best_delta={sol.best_delta:,}"
    )
    if sol.section_counts:
        head = sol.section_counts[:12]
        suf = "" if len(sol.section_counts) <= 12 else f" ... (+{len(sol.section_counts)-12} more)"
        print(f"[fg-dp] counts_head={head}{suf}")


if __name__ == "__main__":
    main()
