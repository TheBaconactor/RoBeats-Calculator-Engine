"""
Taichi Kernels - exact GA evaluation.
Includes:
- ga_find_best_combo_warmstart_kernel
"""
import taichi as ti
from .. import kernels_helpers
from ..kernels_scoring import (
    optimize_core_device_exact_bound,
    optimize_core_device_refined as optimize_core_device,
    score_solution_from_gems_preloaded,
)
MAX_STAT = 160  # gear_optimizer.core.constants.MAX_STAT_INDEX
@ti.func
def _same_grid_sig(song_slot: ti.i32, sig0: ti.u64, sig1: ti.u64, ft_i: ti.i32, ff_i: ti.i32) -> ti.i32:
    same = ti.i32(0)
    frontier_count = ti.cast(kernels_helpers.grid_frontier_count[song_slot, ft_i, ff_i], ti.i32)
    if frontier_count <= 1:
        same = ti.cast(
            (kernels_helpers.grid_sig0[song_slot, ft_i, ff_i] == sig0)
            & (kernels_helpers.grid_sig1[song_slot, ft_i, ff_i] == sig1),
            ti.i32,
        )
    return same
@ti.func
def _solve_combo_warmstart_preloaded(
    genome_idx: ti.i32,
    combo_idx: ti.i32,
    combo_budget: ti.i32,
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
    w_ft: ti.i32,
    w_ff: ti.i32,
    base_pp: ti.i32,
    base_cm: ti.i32,
    base_fm: ti.i32,
    base_p_val: ti.i32,
    base_s_val: ti.i32,
    base_ft_stat: ti.i32,
    base_ff_stat: ti.i32,
    max_ft_gems: ti.i32,
    max_ff_gems: ti.i32,
    prune_plateaus: ti.template(),
    use_exact_inner_solver: ti.template(),
) -> ti.types.vector(5, ti.i32):
    """
    Solve a single (genome, combo) work item and return [score, pp, cm, fm, ov].
    Returns:
        Vector [score, pp, cm, fm, ov].
        score is -1 when the combo is invalid/pruned.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
    ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
    out_res = ti.Vector([ti.i32(-1), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0)])
    if ft <= max_ft_gems and ff <= max_ff_gems:
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        pruned: ti.i32 = 0
        if ti.static(prune_plateaus):
            sig0 = kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx]
            sig1 = kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx]
            if pruned == 0 and w_ft == 0 and ft > 0:
                ft2 = ft - 1
                ff2 = ff
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff_idx) != 0:
                        pruned = 1
            if pruned == 0 and w_ff == 0 and ff > 0:
                ft2 = ft
                ff2 = ff - 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ff2_val = ff_stat_val - gem_scale_fever
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft_idx, ff2_idx) != 0:
                        pruned = 1
            if pruned == 0 and w_ft > w_ff and ff > 0 and (ft + 1) <= max_ft_gems:
                ft2 = ft + 1
                ff2 = ff - 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val + gem_scale_fever
                    ff2_val = ff_stat_val - gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1
            if pruned == 0 and w_ff > w_ft and ft > 0 and (ff + 1) <= max_ff_gems:
                ft2 = ft - 1
                ff2 = ff + 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ff2_val = ff_stat_val + gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1
            if pruned == 0 and w_ff == w_ft and w_ft != 0 and ft > 0 and (ff + 1) <= max_ff_gems:
                ft2 = ft - 1
                ff2 = ff + 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ff2_val = ff_stat_val + gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1
        if pruned == 0:
            count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
            count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
            head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]
            budget: ti.i32 = combo_budget - ft - ff
            p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
            s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
            score: ti.i32 = -1
            res_vec = ti.Vector([ti.i32(-1), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0)])
            if ti.static(use_exact_inner_solver):
                res_vec = optimize_core_device_exact_bound(
                    budget,
                    base_pp,
                    base_cm,
                    base_fm,
                    p_val,
                    s_val,
                    is_p_pp,
                    is_s_pp,
                    is_p_cm,
                    is_s_cm,
                    is_p_fm,
                    is_s_fm,
                    is_p_ov,
                    is_s_ov,
                    head_len,
                    count_fever,
                    count_normal,
                    song_slot,
                    ft_idx,
                    ff_idx,
                )
            else:
                res_vec = optimize_core_device(
                    budget,
                    base_pp,
                    base_cm,
                    base_fm,
                    p_val,
                    s_val,
                    is_p_pp,
                    is_s_pp,
                    is_p_cm,
                    is_s_cm,
                    is_p_fm,
                    is_s_fm,
                    is_p_ov,
                    is_s_ov,
                    head_len,
                    count_fever,
                    count_normal,
                    song_slot,
                    ft_idx,
                    ff_idx,
                )
            raw_score = res_vec[0]
            if raw_score >= 0:
                score = score_solution_from_gems_preloaded(
                    ft,
                    ff,
                    res_vec[1],
                    res_vec[2],
                    res_vec[3],
                    res_vec[4],
                    base_pp,
                    base_cm,
                    base_fm,
                    base_p_val,
                    base_s_val,
                    base_ft_stat,
                    base_ff_stat,
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
                    ft_idx,
                    ff_idx,
                    head_len,
                    count_fever,
                    count_normal,
                )
                out_res = ti.Vector([score, res_vec[1], res_vec[2], res_vec[3], res_vec[4]])
    return out_res
@ti.func
def _compute_combo_key_warmstart_preloaded(
    genome_idx: ti.i32,
    combo_idx: ti.i32,
    combo_budget: ti.i32,
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
    w_ft: ti.i32,
    w_ff: ti.i32,
    base_pp: ti.i32,
    base_cm: ti.i32,
    base_fm: ti.i32,
    base_p_val: ti.i32,
    base_s_val: ti.i32,
    base_ft_stat: ti.i32,
    base_ff_stat: ti.i32,
    max_ft_gems: ti.i32,
    max_ff_gems: ti.i32,
    prune_plateaus: ti.template(),
    use_exact_inner_solver: ti.template(),
) -> ti.u64:
    """
    Compute a packed max-key for a single (genome, combo) work item.
    Returns:
        u64 key in format: ((score + 1) << 32) | combo_idx
        0 when the combo is invalid/pruned or yields a negative score.
    """
    res_vec = _solve_combo_warmstart_preloaded(
        genome_idx,
        combo_idx,
        combo_budget,
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
    )
    score = res_vec[0]
    if score >= 0:
        return (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
    return ti.u64(0)
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
    use_exact_inner_solver: ti.template(),  # 0 = greedy/refined, 1 = bounded exact fixed-(FT,FF) solve
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
        if kernels_helpers.ga_base_candidate_cache_hit[genome_idx] != 0:
            skip_row = ti.i32(1)
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
        local_best_pp: ti.i32 = 0
        local_best_cm: ti.i32 = 0
        local_best_fm: ti.i32 = 0
        local_best_ov: ti.i32 = 0
        local_c: ti.i32 = lane
        while skip_row == 0 and local_c < combo_count:
            combo_idx: ti.i32 = combo_offset + local_c
            res_vec = _solve_combo_warmstart_preloaded(
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
            )
            score = res_vec[0]
            if score >= 0:
                key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                if key > local_best_key:
                    local_best_key = key
                    local_best_pp = res_vec[1]
                    local_best_cm = res_vec[2]
                    local_best_fm = res_vec[3]
                    local_best_ov = res_vec[4]
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
