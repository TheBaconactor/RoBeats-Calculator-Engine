"""Direction-1 A/B: is the fused FG response-frontier path cheaper per candidate than the
current Skyline base eval? (Track A de-risking measurement.)

Direction-1's premise: route Skyline's base eval through the FG response-frontier DP so the
FT/FF combo loop collapses. BUT the fused path computes base+FG for EVERY candidate, while the
current path does base-eval-all + FG-only-top-K. So this measures per-candidate wall-clock for:
  (A) current base eval:  skyline_evaluate_population  (base only, the production base pass)
  (B) fused base+FG:      score_fused_owner_base_components_on_gpu_owner  (base AND FG)
on the SAME real-frontier 7-tuples. If (B) per-candidate <= (A), Direction-1 is a win (FG for
free, or cheaper). If (B) >> (A), the fused FG cost dominates and Direction-1 does NOT pay --
Track A falls back to layout/cell-major + the corpus SLO.

Score correctness is separately PROVEN bit-exact (test_gpu_base_stats7_equivalence.py); this
measures COST only.

Usage:
  python tools/bench/bench_direction1_ab.py --song "Starry Night" --n 256
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _log(m):
    print(m, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulty", default="Easy")
    ap.add_argument("--song", default="Starry Night")
    ap.add_argument("--n", type=int, default=256, help="candidates to score through both paths")
    ap.add_argument("--warmups", type=int, default=2)
    ap.add_argument("--timed", type=int, default=5)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.constants import MAX_STAT_INDEX, TOTAL_GEM_BUDGET, GEM_SCALE_FEVER
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
    from gear_optimizer.solver.solver_common import prepare_solver_context, gear_ids_from_code, mini_ids_from_code
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope
    from gear_optimizer.solver.gear_skyline_gpu import global_gear_skyline_points_6d_gpu_from_arrays
    from gear_optimizer.solver.fg_response_frontier_cache_prebuild import build_fg_response_frontier_cache_for_path
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import skyline_operations
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload, precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import all_response_stat_keys, load_response_frontier_scoring_bundle
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import score_fused_owner_base_components_on_gpu_owner
    from tests.parity.exact_skyline import (
        _dp_gear_ff_base_frontier_with_codes,
        _combined_global_skyline_pairs_6d_lane_base_with_indices,
    )

    cfg = load_config()
    ref_arrays = build_ref_arrays_from_stats(read_table(os.path.join(REPO_ROOT, "Data", "Gear", "Stats.txt")), dtype=np.float64)
    folder = os.path.join(REPO_ROOT, "Data", args.difficulty)
    fp = next(os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(".txt") and args.song.lower() in f.lower())
    calc_song = get_base_calc_song(fp, {})
    apply_timing_envelope(calc_song)  # FG bundle is keyed on the envelope-applied song
    meta = calc_song.get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color") or ""); s_color = str(meta.get("Secondary Color") or "")
    _log(f"[d1ab] song={os.path.basename(fp)} colors={p_color}/{s_color} notes={meta.get('Total Notes')} n={args.n}")

    all_gears = list(get_gears_by_name_cached().values())
    all_minis = list(get_minis_by_name_cached().values())

    _log("[d1ab] ensure_ready + precompute timeline ...")
    ensure_ready()
    prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)

    _log("[d1ab] prepare_solver_context + frontier ...")
    ctx = prepare_solver_context(cfg, {}, calc_song, ref_arrays, all_gears, all_minis, status_cb=None, song_slot=0, gpu_client=None)
    dp_points, dp_codes, _ = _dp_gear_ff_base_frontier_with_codes(ctx.gear_pool, p_color=p_color, s_color=s_color, pack=ctx.gear_pack)
    _pin, gear_points, gear_codes, _s = global_gear_skyline_points_6d_gpu_from_arrays(dp_points, dp_codes)
    pair_g, pair_m = _combined_global_skyline_pairs_6d_lane_base_with_indices(gear_points, ctx.mini_points)
    n_front = int(pair_g.shape[0])
    _log(f"[d1ab] frontier n_candidates={n_front:,}")

    # Decode a random real-frontier sample into population_indices (N, 9) of registry item IDs.
    N = int(min(args.n, n_front))
    rng = np.random.default_rng(20260613)
    sample = rng.choice(n_front, size=N, replace=False)
    pop = np.zeros((N, 9), dtype=np.int32)
    for k, j in enumerate(sample.tolist()):
        g_ids = gear_ids_from_code(int(gear_codes[int(pair_g[j])]), pack=ctx.gear_pack, slot_item_ids=ctx.slot_item_ids)
        m_ids = mini_ids_from_code(int(ctx.mini_codes[int(pair_m[j])]), pack=ctx.mini_pack, mini_item_ids=ctx.mini_item_ids)
        pop[k, :6] = g_ids; pop[k, 6:] = m_ids

    # Skyline GPU upload (mirror bench_ga_plateau_ab).
    gpu_arrays = ctx.gpu_arrays
    item_stats = np.asarray(gpu_arrays["item_stats"], dtype=np.int32)
    slot_start = np.asarray(gpu_arrays["slot_start"], dtype=np.int32)
    slot_count = np.asarray(gpu_arrays["slot_count"], dtype=np.int32)
    gear_name_rank, mini_sig_id = effective_tables_for_context(ctx.registry, primary_color=p_color, secondary_color=s_color, selected_color=ctx.selected_color)
    cf = build_color_flags(p_color, s_color, ctx.selected_color)
    cf12 = {k: int(cf.get(k, 0)) for k in ("is_p_ft","is_s_ft","is_p_ff","is_s_ff","is_p_pp","is_s_pp","is_p_cm","is_s_cm","is_p_fm","is_s_fm","is_p_ov","is_s_ov")}
    skyline_operations.skyline_upload_item_stats(item_stats, slot_start, slot_count)
    skyline_operations.skyline_upload_base_fixed_stats(np.asarray(ctx.base_fixed_stats_arr, dtype=np.int32))
    skyline_operations.skyline_upload_fg_effective_tables(gear_name_rank, mini_sig_id)
    skyline_operations.skyline_upload_population_indices(pop, n_slots=9)

    # Build the FG response-frontier scoring bundle for this song (the prebuild M1 was missing).
    _log("[d1ab] building FG response-frontier bundle (candidate-independent all-FT/FF) ...")
    tb = time.perf_counter()
    build_fg_response_frontier_cache_for_path(fp, ref_arrays, stat_keys=all_response_stat_keys())
    bundle = load_response_frontier_scoring_bundle(calc_song, ref_arrays, stat_keys=all_response_stat_keys())
    _log(f"[d1ab] bundle ready ({time.perf_counter()-tb:.1f}s)")

    def _path_a():
        skyline_operations.skyline_evaluate_population(N, 9, total_budget=int(TOTAL_GEM_BUDGET), gem_scale_fever=int(GEM_SCALE_FEVER),
                                                       materialize_mode="results", **cf12)
        import taichi as ti; ti.sync()

    # warm + capture 7-tuples after aggregation
    for _ in range(max(1, args.warmups)):
        _path_a()
    base_components = np.ascontiguousarray(fields.genome_base_stats.to_numpy()[:N, :7].astype(np.int32))
    _log(f"[d1ab] base_components[0]={base_components[0].tolist()}  (PP,CM,FM,p_val,s_val,FT,FF)")

    def _path_b():
        return score_fused_owner_base_components_on_gpu_owner(
            base_components=base_components, calc_song=calc_song, ref_arrays=ref_arrays,
            selected_color=str(ctx.selected_color or p_color), scoring_bundle=bundle, total_budget=int(TOTAL_GEM_BUDGET))
    for _ in range(max(1, args.warmups)):
        _path_b()

    ta, tbb = [], []
    for _ in range(max(1, args.timed)):
        t0 = time.perf_counter(); _path_a(); ta.append((time.perf_counter()-t0)*1000.0)
        t0 = time.perf_counter(); _path_b(); tbb.append((time.perf_counter()-t0)*1000.0)
    a_ms = min(ta); b_ms = min(tbb)
    _log("\n=== DIRECTION-1 A/B (per-candidate cost) ===")
    _log(f"  (A) current base eval (base only):  {a_ms:8.2f} ms / {N} = {a_ms/N*1000:8.2f} us/candidate")
    _log(f"  (B) fused base+FG path:             {b_ms:8.2f} ms / {N} = {b_ms/N*1000:8.2f} us/candidate")
    _log(f"  ratio B/A = {b_ms/a_ms:.2f}x   (>1 => fused is SLOWER per candidate; it also does FG which (A) does not)")
    _log("  READ: Direction-1 wins only if (B) <= (A) + the separate FG-of-survivors cost it replaces.")
    _log("  Since (A) is base-only over ALL candidates and (B) is base+FG over ALL, B/A >> 1 means")
    _log("  folding FG into the all-candidate pass costs MORE than the current base-all + FG-top-K split.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
