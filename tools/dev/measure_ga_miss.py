"""GA miss-structure measurement — HOW does the GA miss, when it misses?

Per song: compute the exact base optimum via the certified skyline reference
(tests/parity/exact_skyline), then run N independently seeded production-shape GA
runs (same kernels, same population/gens/operators as production multi-start).
Report per-run hit/miss, score gap, and the Hamming distance (gear slots +
mini set) from each miss to the nearest known optimal genome.

This arbitrates which GA improvement matters:
  - misses at distance 1-2       -> a 1-swap elite polish converts them to hits
  - misses in distant basins     -> restarts / more runs / diversity pressure
  - triple-miss rate >> p_single^3 -> runs fall into the SAME trap (correlated
    misses; diversity mechanisms, not more repetition)

The exact side costs minutes per song (full frontier eval); results are cached
under artifacts/ga_miss/exact_cache/ keyed on chart+stats mtimes.

Usage:
  python tools/dev/measure_ga_miss.py --difficulty Easy --songs 4 --seeds 96
  python tools/dev/measure_ga_miss.py --song "Aether" --difficulty Easy --seeds 96
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXACT_CACHE_VERSION = 1
EXACT_CACHE_DIR = os.path.join(REPO_ROOT, "artifacts", "ga_miss", "exact_cache")
REPORT_DIR = os.path.join(REPO_ROOT, "artifacts", "ga_miss")
STATS_TXT = os.path.join(REPO_ROOT, "Data", "Gear", "Stats.txt")


def _log(m: str) -> None:
    print(m, flush=True)


def _ref_arrays():
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats

    return build_ref_arrays_from_stats(read_table(STATS_TXT), dtype=np.float64)


def _pick_songs(difficulty: str, song: str, want: int) -> list[str]:
    folder = os.path.join(REPO_ROOT, "Data", difficulty)
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".txt"))
    if song:
        hits = [os.path.join(folder, f) for f in files if song.lower() in f.lower()]
        if not hits:
            raise SystemExit(f"no chart in Data/{difficulty}/ matches {song!r}")
        return hits[: max(1, want)]
    return [os.path.join(folder, f) for f in files[: max(1, want)]]


def _production_ga_shape(cfg) -> dict:
    """Production GA shape: same values the native pipeline derives from GASettings."""
    from gear_optimizer.core.config import GASettings
    from gear_optimizer.core.constants import GA_POPULATION_SIZE

    gs = GASettings.from_config(cfg)
    num_runs = max(1, int(gs.multi_start))
    gens_per_run = max(1, (int(gs.search_depth) + num_runs - 1) // num_runs)
    return {
        "gens_per_run": gens_per_run,
        "multi_start": num_runs,
        "n_genomes": int(GA_POPULATION_SIZE),
        "tournament_k": int(gs.tournament_k),
        "mutation_rate": float(gs.mutation_rate),
        "immigrant_rate": float(gs.immigrant_rate),
        "elite_count": int(gs.elite_count),
    }


# --------------------------- exact arm (skyline reference) ---------------------------


def _exact_cache_path(chart_fp: str) -> str:
    stem = os.path.splitext(os.path.basename(chart_fp))[0]
    return os.path.join(EXACT_CACHE_DIR, f"{stem}.json")


def _exact_cache_key(chart_fp: str) -> dict:
    return {
        "version": EXACT_CACHE_VERSION,
        "chart_path": os.path.abspath(chart_fp),
        "chart_mtime_ns": os.stat(chart_fp).st_mtime_ns,
        "stats_mtime_ns": os.stat(STATS_TXT).st_mtime_ns,
    }


def _exact_optimum(cfg, ctx, calc_song, ref_arrays, all_gears, all_minis, chart_fp: str) -> dict:
    """Exact base optimum + all KNOWN tied-optimal genomes (9 item ids each).

    Ground truth for hit/miss is the exact best BASE score (certified frontier max).
    The tied-optima set is best-effort: ties beyond the skyline's retained top-K are
    not enumerated, so Hamming distances are upper bounds (min over known optima).
    """
    cache_fp = _exact_cache_path(chart_fp)
    key = _exact_cache_key(chart_fp)
    if os.path.exists(cache_fp):
        with open(cache_fp, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("key") == key:
            _log(f"  [exact] cache hit ({cache_fp}); delete the file to force recompute")
            return cached
        _log("  [exact] cache key mismatch (chart or stats changed) -> recompute")

    from tests.parity.exact_skyline import solve_exact_skyline

    t0 = time.perf_counter()
    best_data, _bg, _bm, _fg_summary, _fg_best, _unused, all_evaluated = solve_exact_skyline(
        cfg,
        {},
        None,
        calc_song,
        ref_arrays,
        list(all_gears),
        list(all_minis),
        gears_by_name={},
        minis_by_name={},
        status_cb=lambda m: _log(f"  [exact] {m}"),
        song_slot=0,
        solver_ctx=ctx,
    )
    elapsed = time.perf_counter() - t0
    if not best_data or not best_data.get("GenomeIDs"):
        raise RuntimeError(f"exact skyline returned no best_data for {chart_fp}")

    exact_best = int(best_data["BaseScore"])
    optima: list[list[int]] = [[int(x) for x in best_data["GenomeIDs"]]]
    for rec in all_evaluated or []:
        if int(rec.get("BaseScore", -1)) == exact_best:
            ids = [int(x) for x in (rec.get("GenomeIDs") or [])]
            if len(ids) == 9 and ids not in optima:
                optima.append(ids)
    ev_best = max((int(r.get("BaseScore", -1)) for r in all_evaluated or []), default=exact_best)
    if ev_best > exact_best:
        raise RuntimeError(
            f"exact-side inconsistency: all_evaluated max BaseScore {ev_best} > best_data {exact_best}"
        )

    result = {
        "key": key,
        "exact_best": exact_best,
        "optima": optima,
        "n_known_optima": len(optima),
        "exact_elapsed_s": round(elapsed, 1),
    }
    os.makedirs(EXACT_CACHE_DIR, exist_ok=True)
    with open(cache_fp, "w", encoding="utf-8") as f:
        json.dump(result, f)
    _log(f"  [exact] optimum={exact_best:,}  known_optima={len(optima)}  ({elapsed:.1f}s, cached)")
    return result


# ------------------------------- GA arm (production shape) -------------------------------


def _ga_seeded_runs(ctx, calc_song, ref_arrays, *, shape: dict, seeds: int, seed_base: int, p_color: str, s_color: str) -> list[dict]:
    """Run `seeds` independently seeded single GA runs (production kernels/operators).

    Batches up to MAX_GA_RUNS runs per GPU call; each run in a call gets its own
    deterministic per-run RNG stream (ga_seed_rng_runs_indexed), identical to how
    production multi-start seeds its runs.

    Per-run bests are read from `fields.ga_runs_payload_packed[run, 0, :]`
    ([score, ids(9), results(7)]), the across-generation tracked best written by
    ga_update_runs_best_kernel. The FG-funnel payload cannot serve this purpose:
    its selection kernel dedups effective-equivalent genomes ACROSS runs, so runs
    converging to the same loadout collapse to one row. The direct read is
    validated against the payload header best (max over runs must match).
    """
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
    from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt
    from gear_optimizer.solver.taichi_gem import fields

    cf = build_color_flags(p_color, s_color, ctx.selected_color)
    gnr, msi = effective_tables_for_context(
        ctx.registry, primary_color=p_color, secondary_color=s_color, selected_color=ctx.selected_color
    )
    item_stats = np.asarray(ctx.gpu_arrays["item_stats"], dtype=np.int32)
    slot_start = np.asarray(ctx.gpu_arrays["slot_start"], dtype=np.int32)
    slot_count = np.asarray(ctx.gpu_arrays["slot_count"], dtype=np.int32)
    base_fixed = np.asarray(ctx.base_fixed_stats_arr, dtype=np.int32)

    max_runs_per_call = int(fields.MAX_GA_RUNS)
    out: list[dict] = []
    done = 0
    while done < seeds:
        n_runs = min(seeds - done, max_runs_per_call)
        call_seed = int(seed_base) + done  # distinct seed space per call chunk
        payload = run_gpu_native_ga_runs_payload_prebuilt(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=0,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed,
            n_generations=int(shape["gens_per_run"]),
            initial_populations=None,
            num_runs=int(n_runs),
            n_genomes=int(shape["n_genomes"]),
            elite_count=int(shape["elite_count"]),
            mutation_rate=float(shape["mutation_rate"]),
            immigrant_rate=float(shape["immigrant_rate"]),
            tournament_k=int(shape["tournament_k"]),
            color_flags=cf,
            cfg_data=ctx.cfg_data,
            ga_seed=call_seed,
            fg_gear_name_rank=gnr,
            fg_mini_sig_id=msi,
        )
        p = np.asarray(payload, dtype=np.int64)
        if p.ndim != 2 or p.shape[1] < 2 + 9:
            raise RuntimeError(f"unexpected GA payload shape {p.shape}")
        header_best = int(p[0, 1])

        runs_best = fields.ga_runs_payload_packed.to_numpy()[:n_runs, 0, :]  # (n_runs, 17)
        if runs_best.shape[1] != 1 + 9 + 7:
            raise RuntimeError(f"unexpected ga_runs_payload_packed row width {runs_best.shape[1]} (expected 17)")
        call_best = int(runs_best[:, 0].max())
        if call_best != header_best:
            raise RuntimeError(
                f"per-run best read inconsistent with payload header: max-over-runs {call_best} "
                f"!= header best {header_best} (call_seed={call_seed})"
            )
        for r in range(n_runs):
            score = int(runs_best[r, 0])
            if score <= 0:
                raise RuntimeError(f"run {r} has no tracked best (score={score}, call_seed={call_seed})")
            ids = [int(x) for x in runs_best[r, 1 : 1 + 9]]
            out.append({"seed_label": f"{call_seed}+r{r}", "score": score, "ids": ids})
        done += n_runs
        _log(f"  [ga] {done}/{seeds} runs done (last call: {n_runs} runs, best={call_best:,})")
    return out


# ------------------------------------- analysis -------------------------------------


def _genome_distance(ids: list[int], opt: list[int]) -> int:
    """Slot-aligned gear distance + order-insensitive mini set distance."""
    gear_d = sum(1 for s in range(6) if int(ids[s]) != int(opt[s]))
    mini_d = 3 - len(set(int(x) for x in ids[6:9]) & set(int(x) for x in opt[6:9]))
    return gear_d + mini_d


def _analyze_song(name: str, exact: dict, runs: list[dict], multi_start: int) -> dict:
    exact_best = int(exact["exact_best"])
    optima = exact["optima"]
    for r in runs:
        if r["score"] > exact_best:
            raise RuntimeError(
                f"GA score {r['score']:,} EXCEEDS exact optimum {exact_best:,} on {name} — "
                f"eval-semantics mismatch or frontier bug; investigate before trusting anything"
            )
    hits = [r for r in runs if r["score"] == exact_best]
    misses = [r for r in runs if r["score"] < exact_best]
    for r in misses:
        r["dist"] = min(_genome_distance(r["ids"], o) for o in optima)
        r["gap"] = exact_best - r["score"]
        r["gap_pct"] = 100.0 * r["gap"] / exact_best if exact_best else 0.0

    n = len(runs)
    p_single = len(misses) / n if n else 0.0
    # empirical multi-start product: consecutive groups of `multi_start` runs
    groups = [runs[i : i + multi_start] for i in range(0, n - multi_start + 1, multi_start)]
    group_misses = sum(1 for g in groups if all(x["score"] < exact_best for x in g))
    p_multi_emp = group_misses / len(groups) if groups else 0.0

    dist_hist: dict[int, int] = {}
    for r in misses:
        dist_hist[r["dist"]] = dist_hist.get(r["dist"], 0) + 1
    distinct_miss_genomes = len({tuple(r["ids"][:6]) + tuple(sorted(r["ids"][6:9])) for r in misses})

    return {
        "song": name,
        "seeds": n,
        "exact_best": exact_best,
        "n_known_optima": len(optima),
        "hits": len(hits),
        "misses": len(misses),
        "p_single_miss": p_single,
        "p_multi_expected_independent": p_single**multi_start,
        "p_multi_empirical": p_multi_emp,
        "multi_groups": len(groups),
        "gap_pct_max": max((r["gap_pct"] for r in misses), default=0.0),
        "gap_pct_median": float(np.median([r["gap_pct"] for r in misses])) if misses else 0.0,
        "dist_hist": {str(k): v for k, v in sorted(dist_hist.items())},
        "dist_le2_share": (sum(v for k, v in dist_hist.items() if k <= 2) / len(misses)) if misses else 0.0,
        "distinct_miss_genomes": distinct_miss_genomes,
        "runs": runs,
    }


def _print_song_report(a: dict) -> None:
    _log(f"  seeds={a['seeds']}  hits={a['hits']}  misses={a['misses']}  p(single miss)={a['p_single_miss']:.3f}")
    _log(
        f"  multi-start({a['multi_groups']} groups): empirical miss={a['p_multi_empirical']:.3f}  "
        f"vs independent p^k={a['p_multi_expected_independent']:.4f}"
    )
    if a["misses"]:
        _log(
            f"  miss gaps: median={a['gap_pct_median']:.4f}%  max={a['gap_pct_max']:.4f}%   "
            f"distinct miss genomes={a['distinct_miss_genomes']}"
        )
        _log(f"  miss Hamming distance histogram (swaps to nearest KNOWN optimum): {a['dist_hist']}")
        _log(f"  misses within 1-2 swaps (1-swap/2-swap polish would convert): {a['dist_le2_share']:.1%}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--difficulty", default="Easy")
    ap.add_argument("--song", default="", help="substring of chart filename (optional)")
    ap.add_argument("--songs", type=int, default=1)
    ap.add_argument("--seeds", type=int, default=96, help="independent seeded GA runs per song")
    ap.add_argument("--seed-base", type=int, default=20260703)
    ap.add_argument("--gens", type=int, default=0, help="override gens per run (0 = production shape)")
    ap.add_argument("--genomes", type=int, default=0, help="override population size (0 = production shape)")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from gear_optimizer.core.config import load_config
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.solver_common import prepare_solver_context
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )

    cfg = load_config()
    shape = _production_ga_shape(cfg)
    if args.gens > 0:
        shape["gens_per_run"] = int(args.gens)
    if args.genomes > 0:
        shape["n_genomes"] = int(args.genomes)
    ref_arrays = _ref_arrays()
    all_gears = list(get_gears_by_name_cached().values())
    all_minis = list(get_minis_by_name_cached().values())
    songs = _pick_songs(args.difficulty, args.song, args.songs)

    _log(
        f"[ga-miss] songs={len(songs)} seeds={args.seeds} | production shape: "
        f"gens/run={shape['gens_per_run']} genomes={shape['n_genomes']} k={shape['tournament_k']} "
        f"mut={shape['mutation_rate']} elite={shape['elite_count']} imm={shape['immigrant_rate']} "
        f"multi_start={shape['multi_start']}"
    )
    ensure_ready()

    # TWO PASSES, GA first: solve_exact_skyline's FG phase uploads FG (great-window)
    # fever state that SURVIVES the next song's precompute_timeline_gpu, so any GA
    # call after any in-process skyline solve scores inflated (~1.6x observed, both
    # same-song and cross-song). GA->skyline is clean (verified: fresh exact after
    # GA calls matches GA bit-exact), so all GA arms run before the first solve.
    def _prep_song(fp: str):
        calc_song = get_base_calc_song(fp, {})
        apply_timing_envelope(calc_song)
        meta = (calc_song or {}).get("metadata", {}) or {}
        prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)
        ctx = prepare_solver_context(
            cfg, {}, calc_song, ref_arrays, list(all_gears), list(all_minis), status_cb=None, song_slot=0, gpu_client=None
        )
        name = str(meta.get("Song Name") or os.path.basename(fp))
        return calc_song, ctx, name, str(meta.get("Primary Color") or ""), str(meta.get("Secondary Color") or ""), meta

    ga_results: dict[str, list[dict]] = {}
    song_names: dict[str, str] = {}
    _log("\n--- pass 1: GA arms (no skyline solves in-process yet) ---")
    for fp in songs:
        calc_song, ctx, name, p_color, s_color, meta = _prep_song(fp)
        song_names[fp] = name
        _log(f"\n=== {name[:48]} ({p_color}/{s_color}, notes={meta.get('Total Notes')}) ===")
        t0 = time.perf_counter()
        ga_results[fp] = _ga_seeded_runs(
            ctx, calc_song, ref_arrays, shape=shape, seeds=args.seeds, seed_base=args.seed_base,
            p_color=p_color, s_color=s_color,
        )
        _log(f"  [ga] {args.seeds} runs in {time.perf_counter() - t0:.1f}s")

    song_reports = []
    _log("\n--- pass 2: exact arms (skyline reference) ---")
    for fp in songs:
        _log(f"\n=== {song_names[fp][:48]} ===")
        calc_song, ctx, name, _p, _s, _meta = _prep_song(fp)
        exact = _exact_optimum(cfg, ctx, calc_song, ref_arrays, all_gears, all_minis, fp)
        a = _analyze_song(name, exact, ga_results[fp], shape["multi_start"])
        _print_song_report(a)
        song_reports.append(a)

    if song_reports:
        all_p = [a["p_single_miss"] for a in song_reports]
        all_le2 = [a["dist_le2_share"] for a in song_reports if a["misses"]]
        _log("\n=== GA MISS SUMMARY ===")
        _log(f"  songs={len(song_reports)}  p(single miss): median={np.median(all_p):.3f} max={max(all_p):.3f}")
        if all_le2:
            _log(f"  share of misses within 2 swaps of a known optimum: median={np.median(all_le2):.1%}")
        _log("  READ: dist<=2 dominant  -> 1/2-swap elite polish converts most misses.")
        _log("        dist large        -> basin-selection failures; restarts/more-runs/diversity.")
        _log("        empirical multi-miss >> p^k -> correlated misses; diversity over repetition.")
        os.makedirs(REPORT_DIR, exist_ok=True)
        out_fp = os.path.join(REPORT_DIR, f"miss_report_{time.strftime('%Y%m%d_%H%M%S')}.json")
        with open(out_fp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "shape": shape,
                    "seeds": args.seeds,
                    "seed_base": args.seed_base,
                    "difficulty": args.difficulty,
                    "songs": song_reports,
                },
                f,
                indent=1,
            )
        _log(f"  full per-run data -> {out_fp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
