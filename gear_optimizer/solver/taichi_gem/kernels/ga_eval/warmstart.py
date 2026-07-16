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
    n_genomes_launch: ti.i32,
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
    use_exact_inner_solver: ti.template(),  # retained ABI flag; production requires exact inner solving
    probe_mode: ti.template(),  # 0=production (byte-identical); 1=counting pass; 2=perfect-incumbent replay (DEBUG GA_CULL_PROBE)
):
    """
    GPU-parallel exact per-(genome, FT/FF) evaluation over COMPACTED unique rows.

    The launch is sized by the host-known population width (`n_genomes_launch`);
    the number of live compacted slots is read ON-DEVICE from
    `ga_exact_eval_unique_count[0]` (written by the immediately preceding
    ga_build_unique_slot_table_kernel in the same stream) and slots at or past it
    exit before touching any state. This keeps the whole GA generation stream
    free of host readbacks: sizing the launch by the exact unique count required
    a per-generation `to_numpy()` — a full pipeline drain that serialized the
    deferred generation stream against the host launch loop. Slot s < count maps
    to its genome via `ga_unique_slot_to_genome[s]` and computes exactly what the
    exact-count launch computed; `ga_scatter_dup_results_kernel` copies each
    duplicate's winning key/results from its representative afterwards.
    (`ga_build_unique_slot_table_kernel`'s serial ascending emit bounds the count
    to [1, n_genomes] structurally, and the launch width is the host-validated
    population size, so the dispatch-safety bound is unchanged.)

    Each (genome, lane) strides the chunk's combos and stages its lane-local
    winner in `ga_warmstart_lane_best_key/_results`; the separate
    `ga_finalize_warmstart_lane_best_kernel` then reduces lanes into
    `chunk_best_key` + `chunk_best_results` (no u64 atomics — MoltenVK/Metal
    rejects `atomic_fetch_max` on ulong, so the lane-array + reduce shape is
    the cross-platform path).
    Args:
        n_genomes_launch: Host-known population width (launch bound; live slots
            are gated on-device by ga_exact_eval_unique_count[0])
        n_combos: Total number of FT/FF combinations
        combo_offset: Starting index in combo tables (for chunked processing)
        combo_count: Number of combos in this chunk
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags (0/1)
        song_slot: Grid slot for batch coalescing
        probe_mode: DEBUG cull-instrumentation selector, statically specialized so
            probe_mode == 0 dead-code-eliminates every probe branch and compiles to
            byte-identical production code (all production call sites pass 0):
            - 0: production. No counters, all result writes as-is.
            - 1: counting pass with normal semantics — production result writes are
              unchanged AND ga_cull_probe_counters[0]/[1] count examined/solved combos
              against the live (lagging) incumbent.
            - 2: perfect-incumbent replay — cull_threshold is this genome's FINAL winning
              score (chunk_best_key high 32 bits minus 1, clamped >= 0), counters[2]/[3]
              count examined/solved, and ALL result writes (lane reset, lane winner,
              incumbent atomic_max) are compiled out so it is side-effect-free.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    w_ft: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ft << 1) + is_s_ft)
    w_ff: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ff << 1) + is_s_ff)
    block_dim = ti.cast(kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM, ti.i32)
    total_threads = n_genomes_launch * block_dim
    ti.loop_config(block_dim=kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)
    for tid in range(total_threads):
        slot_idx = tid // block_dim
        if slot_idx >= kernels_helpers.ga_exact_eval_unique_count[0]:
            continue
        lane = tid - slot_idx * block_dim
        genome_idx = kernels_helpers.ga_unique_slot_to_genome[slot_idx]
        # Mode 2 (perfect-incumbent replay) is side-effect-free: it must not touch the
        # lane arrays pass 1 already finalized into chunk_best_key.
        if ti.static(probe_mode != 2):
            kernels_helpers.ga_warmstart_lane_best_key[genome_idx, lane] = ti.u64(0)
            for i in ti.static(range(4)):
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, i] = 0
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
        while local_c < combo_count:
            combo_idx: ti.i32 = combo_offset + local_c
            # Exact UB combo culling: skip the inner solve when even the relaxed
            # upper bound cannot reach the best exact score already found for
            # this genome (lane-local plus the cross-lane shared incumbent).
            # The threshold is the incumbent score itself, NOT incumbent+1:
            # culling only ub < incumbent keeps every potential tie, so the
            # winning combo identity (and its tie-break order) is unchanged.
            # Stale reads of the shared incumbent only reduce culling.
            cull_threshold: ti.i32 = 0
            if ti.static(probe_mode == 2):
                # Perfect-incumbent replay: cull against this genome's FINAL winning
                # score (chunk_best_key packs (score+1) in the high 32 bits), exposing
                # the cull floor a zero-lag incumbent would leave. Loop-invariant read;
                # the compiler hoists it.
                cull_threshold = ti.max(
                    0,
                    ti.cast(kernels_helpers.chunk_best_key[genome_idx] >> ti.u64(32), ti.i32) - 1,
                )
            else:
                cull_threshold = ti.max(
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
                use_exact_inner_solver,
                False,
                cull_threshold,
            )
            score = res_vec[0]
            # DEBUG cull-instrumentation: examined = every combo the loop reaches;
            # solved = a non-culled valid solve (culled/invalid combos return score < 0).
            if ti.static(probe_mode == 1):
                ti.atomic_add(kernels_helpers.ga_cull_probe_counters[0], 1)
                if score >= 0:
                    ti.atomic_add(kernels_helpers.ga_cull_probe_counters[1], 1)
            if ti.static(probe_mode == 2):
                ti.atomic_add(kernels_helpers.ga_cull_probe_counters[2], 1)
                if score >= 0:
                    ti.atomic_add(kernels_helpers.ga_cull_probe_counters[3], 1)
            if ti.static(probe_mode != 2):
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
        if ti.static(probe_mode != 2):
            if local_best_key != ti.u64(0):
                kernels_helpers.ga_warmstart_lane_best_key[genome_idx, lane] = local_best_key
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 0] = local_best_pp
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 1] = local_best_cm
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 2] = local_best_fm
                kernels_helpers.ga_warmstart_lane_best_results[genome_idx, lane, 3] = local_best_ov
@ti.kernel
def ga_finalize_warmstart_lane_best_kernel(n_genomes_launch: ti.i32):
    # Compacted like the eval kernel: only unique rows have freshly-written lane
    # arrays; iterating all rows would reduce stale lanes for duplicate rows.
    # Launch width is the host-known population size; live slots are gated
    # on-device (same no-host-readback contract as the eval kernel).
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for s in range(n_genomes_launch):
        if s >= kernels_helpers.ga_exact_eval_unique_count[0]:
            continue
        g = kernels_helpers.ga_unique_slot_to_genome[s]
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


@ti.kernel
def ga_build_unique_slot_table_kernel(n_genomes: ti.i32):
    # Emit representative rows (rep[g] == g) into a dense slot table in ascending
    # genome order and publish the unique count. Serialized single-thread pass:
    # bounded by MAX_GENOMES (~4.6k iterations), deterministic table order, and
    # tiny vs the O(n_combos) eval it sizes.
    ti.loop_config(serialize=True)
    count = 0
    for g in range(n_genomes):
        if kernels_helpers.ga_exact_eval_rep_idx[g] == g:
            kernels_helpers.ga_unique_slot_to_genome[count] = g
            count += 1
    kernels_helpers.ga_exact_eval_unique_count[0] = count
