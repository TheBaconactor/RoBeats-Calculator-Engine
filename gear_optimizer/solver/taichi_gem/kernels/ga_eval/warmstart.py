"""
Taichi Kernels - exact GA evaluation.
Includes:
- ga_find_best_combo_warmstart_kernel
"""
import taichi as ti
from .. import kernels_helpers
from ..warmstart_common import MAX_STAT, solve_combo_warmstart_preloaded
@ti.kernel
def ga_find_best_combo_warmstart_kernel(
    n_genomes: ti.i32,
    n_combos: ti.i32,
    combo_offset: ti.i32,
    combo_count: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    song_slot: ti.i32,
    prune_plateaus: ti.template(),  # 0 = disabled, 1 = prune timeline plateaus via dominated representatives
    use_exact_inner_solver: ti.template(),  # retained ABI flag; production requires exact inner solving
    reuse_exact_eval_results: ti.template(),
):
    """
    GPU-parallel evaluation with exact or refined per-(genome, FT/FF) solving.
    Vulkan path reduces the winning key into `chunk_best_key` via an exact
    per-genome `ti.atomic_max` and intentionally does NOT write
    `chunk_best_results` (materialization validates cached payloads and recomputes
    when needed).
    Args:
        n_genomes: Number of genomes to evaluate
        n_combos: Total number of FT/FF combinations
        combo_offset: Starting index in combo tables (for chunked processing)
        combo_count: Number of combos in this chunk
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags (0/1)
        song_slot: Grid slot for batch coalescing
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    w_ft: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ft << 1) + is_s_ft)
    w_ff: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ff << 1) + is_s_ff)
    block_dim = ti.cast(kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM, ti.i32)
    total_threads = n_genomes * block_dim
    ti.loop_config(block_dim=kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)
    for tid in range(total_threads):
        genome_idx = tid // block_dim
        lane = tid - genome_idx * block_dim
        kernels_helpers.ga_warmstart_lane_best_key[genome_idx, lane] = ti.u64(0)
        for i in ti.static(range(4)):
            kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, i] = 0
        skip_row = ti.i32(0)
        if ti.static(reuse_exact_eval_results):
            if kernels_helpers.ga_exact_eval_rep_idx[genome_idx] != genome_idx:
                skip_row = ti.i32(1)
        stats = kernels_helpers.genome_base_stats[genome_idx]
        base_pp: ti.i32 = stats[0]
        base_cm: ti.i32 = stats[1]
        base_fm: ti.i32 = stats[2]
        base_p_val: ti.i32 = stats[3]
        base_s_val: ti.i32 = stats[4]
        base_ft_stat: ti.i32 = stats[5]
        base_ff_stat: ti.i32 = stats[6]
        remaining_ft: ti.i32 = MAX_STAT - base_ft_stat
        remaining_ff: ti.i32 = MAX_STAT - base_ff_stat
        max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        if max_ft_gems > total_budget:
            max_ft_gems = total_budget
        if max_ff_gems > total_budget:
            max_ff_gems = total_budget
        local_best_key = ti.u64(0)
        local_best_score: ti.i32 = 0
        local_best_pp: ti.i32 = 0
        local_best_cm: ti.i32 = 0
        local_best_fm: ti.i32 = 0
        local_best_ov: ti.i32 = 0
        local_c: ti.i32 = lane
        while skip_row == 0 and local_c < combo_count:
            combo_idx: ti.i32 = combo_offset + local_c
            # Exact UB combo culling: skip the inner solve when even the relaxed
            # upper bound cannot reach the best exact score already found for
            # this genome (lane-local plus the cross-lane shared incumbent).
            # The threshold is the incumbent score itself, NOT incumbent+1:
            # culling only ub < incumbent keeps every potential tie, so the
            # winning combo identity (and its tie-break order) is unchanged.
            # Stale reads of the shared incumbent only reduce culling.
            cull_threshold: ti.i32 = ti.max(
                local_best_score,
                kernels_helpers.ga_eval_incumbent_score[genome_idx],
            )
            res_vec = solve_combo_warmstart_preloaded(
                genome_idx,
                combo_idx,
                total_budget,  # combo_budget
                gem_scale_fever,
                is_p_ft,
                is_s_ft,
                is_p_ff,
                is_s_ff,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                song_slot,
                w_ft,
                w_ff,
                base_pp,
                base_cm,
                base_fm,
                base_p_val,
                base_s_val,
                base_ft_stat,
                base_ff_stat,
                max_ft_gems,
                max_ff_gems,
                prune_plateaus,
                use_exact_inner_solver,
                False,
                cull_threshold,
            )
            score = res_vec[0]
            if score >= 0:
                key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                if key > local_best_key:
                    local_best_key = key
                    local_best_score = score
                    local_best_pp = res_vec[1]
                    local_best_cm = res_vec[2]
                    local_best_fm = res_vec[3]
                    local_best_ov = res_vec[4]
                    ti.atomic_max(kernels_helpers.ga_eval_incumbent_score[genome_idx], score)
            local_c += block_dim
        if local_best_key != ti.u64(0):
            kernels_helpers.ga_warmstart_lane_best_key[genome_idx, lane] = local_best_key
            kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 0] = local_best_pp
            kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 1] = local_best_cm
            kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 2] = local_best_fm
            kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 3] = local_best_ov
@ti.kernel
def ga_finalize_warmstart_lane_best_kernel(n_genomes: ti.i32):
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        best_key = kernels_helpers.chunk_best_key[g]
        best_lane = ti.i32(-1)
        for lane in ti.static(range(kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)):
            key = kernels_helpers.ga_warmstart_lane_best_key[g, lane]
            if key > best_key:
                best_key = key
                best_lane = lane
        if best_lane >= 0:
            kernels_helpers.chunk_best_key[g] = best_key
            for i in ti.static(range(4)):
                kernels_helpers.chunk_best_results[g, i] = kernels_helpers.ga_warmstart_lane_best_results[g, best_lane, i]


@ti.kernel
def ga_compute_exact_eval_rep_kernel(n_genomes: ti.i32):
    # GPU-side exact-eval dedup: rep[g] = lowest-index genome with identical
    # genome_base_stats (the full per-genome eval input), else g itself. The exact
    # eval reads ONLY genome_base_stats[g] per row (combos/grid/refs are shared), so
    # identical 7-tuples => identical result => a duplicate can reuse its rep's result.
    # Replaces the removed HOST rep-map (which cost more than it saved); this is O(g)
    # per row but tiny vs the O(n_combos) exact eval it lets us skip.
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        s = kernels_helpers.genome_base_stats[g]
        rep = g
        for j in range(g):
            t = kernels_helpers.genome_base_stats[j]
            same = 1
            for k in ti.static(range(7)):
                if s[k] != t[k]:
                    same = 0
            if same == 1:
                rep = j
                break
        kernels_helpers.ga_exact_eval_rep_idx[g] = rep


@ti.kernel
def ga_scatter_dup_results_kernel(n_genomes: ti.i32):
    # After eval+finalize, copy each duplicate genome's winning key/results from its
    # representative (the row that was actually evaluated). Bit-exact: the rep's result
    # is independent of the skipped duplicates (per-genome incumbent, no cross-row state).
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        rep = kernels_helpers.ga_exact_eval_rep_idx[g]
        if rep != g:
            kernels_helpers.chunk_best_key[g] = kernels_helpers.chunk_best_key[rep]
            for i in ti.static(range(4)):
                kernels_helpers.chunk_best_results[g, i] = kernels_helpers.chunk_best_results[rep, i]
