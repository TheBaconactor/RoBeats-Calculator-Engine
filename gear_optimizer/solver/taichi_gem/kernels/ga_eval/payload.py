"""
Taichi Kernels - Pack GA snapshots for CPU download.

Includes:
- ga_pack_run_payload_kernel
- ga_pack_and_store_run_payload_kernel
- ga_pack_fg_candidates_table_segmented_kernel
- ga_copy_fg_candidates_table_to_download_staging_kernel
"""

import taichi as ti

from gear_optimizer.core.parsing import env_int

from .. import kernels_helpers
from .write_results import _best_combo_idx_from_chunk_state, _materialize_best_combo_stats


# IMPORTANT: must match `fields.GA_FG_CANDIDATES_PER_RUN` at allocation time.
_GA_FG_CANDIDATES_PER_RUN = max(1, min(128, int(env_int("GPU_GA_FG_CANDIDATES_PER_RUN", 64))))
_GA_FG_BASE_STATS_COLS = 7
_GA_FG_RESULTS_COLS = 7
_GA_FG_COLS = 1 + 9 + _GA_FG_RESULTS_COLS + _GA_FG_BASE_STATS_COLS  # score + ids + results + base_stats7


@ti.func
def _sort3_i32(a: ti.i32, b: ti.i32, c: ti.i32) -> ti.types.vector(3, ti.i32):
    x0 = a
    x1 = b
    x2 = c
    if x1 < x0:
        x0, x1 = x1, x0
    if x2 < x1:
        x1, x2 = x2, x1
    if x1 < x0:
        x0, x1 = x1, x0
    return ti.Vector([x0, x1, x2])


@ti.func
def _clear_fg_candidate_row(table_slot: ti.i32, run_idx: ti.i32, row_idx: ti.i32):
    for c in ti.static(range(_GA_FG_COLS)):
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, c] = 0


@ti.func
def _write_fg_candidate_row_from_genome(
    table_slot: ti.i32,
    run_idx: ti.i32,
    row_idx: ti.i32,
    genome_idx: ti.i32,
    n_slots: ti.i32,
    result_stats: ti.types.vector(7, ti.i32),
):
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, 0] = result_stats[0]

    for s in range(n_slots):
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, 1 + s] = (
            kernels_helpers.population_indices[genome_idx, s]
        )
    mm = _sort3_i32(
        kernels_helpers.population_indices[genome_idx, 6],
        kernels_helpers.population_indices[genome_idx, 7],
        kernels_helpers.population_indices[genome_idx, 8],
    )
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, 1 + 6] = mm[0]
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, 1 + 7] = mm[1]
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, 1 + 8] = mm[2]

    for t in ti.static(range(_GA_FG_RESULTS_COLS)):
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, 1 + 9 + t] = result_stats[t]

    base_col0 = 1 + 9 + _GA_FG_RESULTS_COLS
    stats7 = kernels_helpers.genome_base_stats[genome_idx]
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 0] = ti.cast(stats7[0], ti.i32)
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 1] = ti.cast(stats7[1], ti.i32)
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 2] = ti.cast(stats7[2], ti.i32)
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 3] = ti.cast(stats7[3], ti.i32)
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 4] = ti.cast(stats7[4], ti.i32)
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 5] = ti.cast(stats7[5], ti.i32)
    kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 6] = ti.cast(stats7[6], ti.i32)


@ti.func
def _population_key_matches(
    genome_idx: ti.i32,
    g0: ti.i32,
    g1: ti.i32,
    g2: ti.i32,
    g3: ti.i32,
    g4: ti.i32,
    g5: ti.i32,
    m0: ti.i32,
    m1: ti.i32,
    m2: ti.i32,
) -> ti.i32:
    mm = _sort3_i32(
        kernels_helpers.population_indices[genome_idx, 6],
        kernels_helpers.population_indices[genome_idx, 7],
        kernels_helpers.population_indices[genome_idx, 8],
    )
    return ti.cast(
        kernels_helpers.population_indices[genome_idx, 0] == g0
        and kernels_helpers.population_indices[genome_idx, 1] == g1
        and kernels_helpers.population_indices[genome_idx, 2] == g2
        and kernels_helpers.population_indices[genome_idx, 3] == g3
        and kernels_helpers.population_indices[genome_idx, 4] == g4
        and kernels_helpers.population_indices[genome_idx, 5] == g5
        and mm[0] == m0
        and mm[1] == m1
        and mm[2] == m2,
        ti.i32,
    )


@ti.func
def _bubble_fg_candidate_up(
    top_scores: ti.template(),
    top_idx: ti.template(),
    slot: ti.i32,
) -> ti.i32:
    cur = slot
    for _ in range(_GA_FG_CANDIDATES_PER_RUN):
        if cur > 0 and top_scores[cur] > top_scores[cur - 1]:
            score_tmp = top_scores[cur - 1]
            idx_tmp = top_idx[cur - 1]
            top_scores[cur - 1] = top_scores[cur]
            top_idx[cur - 1] = top_idx[cur]
            top_scores[cur] = score_tmp
            top_idx[cur] = idx_tmp
            cur -= 1
    return cur


@ti.kernel
def ga_pack_run_payload_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Pack a GA snapshot into `ga_run_payload_packed` for a single CPU download.

    Layout (int32):
      - Row 0: [best_score, best_genome_ids (n_slots), best_results (7)]
      - Row g+1: [score, genome_ids (n_slots), genome_result_stats (7)]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Row 0: global best (single thread)
    for _ in range(1):
        kernels_helpers.ga_run_payload_packed[0, 0] = kernels_helpers.ga_global_best_score[0]
        for s in range(n_slots):
            kernels_helpers.ga_run_payload_packed[0, 1 + s] = kernels_helpers.ga_global_best_genome[s]
        for r in ti.static(range(7)):
            kernels_helpers.ga_run_payload_packed[0, 1 + n_slots + r] = kernels_helpers.ga_global_best_results[r]

    # Rows 1..n_genomes: per-genome snapshot
    for g in range(n_genomes):
        out_row = g + 1
        kernels_helpers.ga_run_payload_packed[out_row, 0] = kernels_helpers.ga_scores[g]
        for s in range(n_slots):
            kernels_helpers.ga_run_payload_packed[out_row, 1 + s] = kernels_helpers.population_indices[g, s]
        res = kernels_helpers.genome_result_stats[g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_run_payload_packed[out_row, 1 + n_slots + r] = res[r]


@ti.kernel
def ga_copy_run_payload_to_download_staging_kernel(
    out_payload: ti.template(),
    n_genomes: ti.i32,
    n_slots: ti.i32,
):
    """
    Copy the populated slice of `ga_run_payload_packed` into a smaller staging field.

    Vulkan `to_numpy()` transfers the full field shape, so downloading the padded
    `(MAX_GENOMES+1, 17)` buffer can dominate throughput when the active population
    is small (e.g., a compact GA run). This kernel enables a bounded staging
    download.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    cols = 1 + n_slots + 7
    rows = n_genomes + 1
    for row in range(rows):
        for c in ti.static(range(17)):
            if c < cols:
                out_payload[row, c] = kernels_helpers.ga_run_payload_packed[row, c]
            else:
                out_payload[row, c] = 0


@ti.kernel
def ga_pack_and_store_run_payload_kernel(run_idx: ti.i32, n_genomes: ti.i32, n_slots: ti.i32):
    """
    Pack a GA snapshot directly into the multi-run buffer `ga_runs_payload_packed`.

    Layout (int32):
      - [run_idx, 0]: [best_score, best_genome_ids (n_slots), best_results (7)]
      - [run_idx, g+1]: [score, genome_ids (n_slots), genome_result_stats (7)]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Row 0: global best (single thread)
    for _ in range(1):
        kernels_helpers.ga_runs_payload_packed[run_idx, 0, 0] = kernels_helpers.ga_global_best_score[0]
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + s] = kernels_helpers.ga_global_best_genome[s]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + n_slots + r] = (
                kernels_helpers.ga_global_best_results[r]
            )

    # Rows 1..n_genomes: per-genome snapshot
    for g in range(n_genomes):
        out_row = g + 1
        kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 0] = kernels_helpers.ga_scores[g]
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + s] = kernels_helpers.population_indices[g, s]
        res = kernels_helpers.genome_result_stats[g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + n_slots + r] = res[r]


@ti.kernel
def ga_pack_and_store_run_payload_segmented_kernel(
    run_idx: ti.i32,
    start_offset: ti.i32,
    n_genomes: ti.i32,
    n_slots: ti.i32,
):
    """
    Pack a GA snapshot for a run stored at an offset into the active population arrays.

    This is used when multiple independent runs are packed contiguously into
    `population_indices`/`ga_scores`/`genome_result_stats`.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Row 0: best genome for this run (single thread, deterministic scan)
    for _ in range(1):
        best_score: ti.i32 = -1
        best_g: ti.i32 = start_offset
        for local_g in range(n_genomes):
            g = start_offset + local_g
            score = kernels_helpers.ga_scores[g]
            if score > best_score:
                best_score = score
                best_g = g

        kernels_helpers.ga_runs_payload_packed[run_idx, 0, 0] = best_score
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + s] = kernels_helpers.population_indices[best_g, s]
        res_best = kernels_helpers.genome_result_stats[best_g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + n_slots + r] = res_best[r]

    # Rows 1..n_genomes: per-genome snapshot for this run
    for local_g in range(n_genomes):
        g = start_offset + local_g
        out_row = local_g + 1
        kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 0] = kernels_helpers.ga_scores[g]
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + s] = kernels_helpers.population_indices[g, s]
        res = kernels_helpers.genome_result_stats[g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + n_slots + r] = res[r]


@ti.kernel
def ga_init_runs_best_kernel(run_idx_start: ti.i32, n_runs: ti.i32, n_slots: ti.i32):
    """
    Initialize per-run "best row" (row 0) in `ga_runs_payload_packed`.

    This is used for batched multi-run execution where we track each run's best
    across generations directly in the output buffer.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for r in range(n_runs):
        run_idx = run_idx_start + r
        kernels_helpers.ga_runs_payload_packed[run_idx, 0, 0] = -1
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + s] = 0
        # [score, ft, ff, pp, cm, fm, ov]
        kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + n_slots + 0] = -1
        for j in ti.static(range(1, 7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + n_slots + j] = 0


@ti.kernel
def ga_update_runs_best_kernel(run_idx_start: ti.i32, n_runs: ti.i32, n_genomes_per_run: ti.i32, n_slots: ti.i32):
    """
    Update per-run best (row 0) in `ga_runs_payload_packed` for packed multi-run execution.

    Each run is scanned deterministically; ties keep the first-seen genome (strict `>`).
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    if n_runs > 0 and n_genomes_per_run > 0:
        for r in range(n_runs):
            start_offset: ti.i32 = r * n_genomes_per_run

            best_score: ti.i32 = -1
            best_g: ti.i32 = start_offset
            for local_g in range(n_genomes_per_run):
                g = start_offset + local_g
                score = kernels_helpers.ga_scores[g]
                if score > best_score:
                    best_score = score
                    best_g = g

            run_idx = run_idx_start + r
            prev_best: ti.i32 = kernels_helpers.ga_runs_payload_packed[run_idx, 0, 0]
            if best_score > prev_best:
                kernels_helpers.ga_runs_payload_packed[run_idx, 0, 0] = best_score
                for s in range(n_slots):
                    kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + s] = kernels_helpers.population_indices[
                        best_g, s
                    ]
                res_best = kernels_helpers.genome_result_stats[best_g]
                for j in ti.static(range(7)):
                    kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + n_slots + j] = res_best[j]


@ti.kernel
def ga_store_runs_payload_snapshot_segmented_kernel(
    run_idx_start: ti.i32,
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_slots: ti.i32,
):
    """
    Store per-genome snapshot rows (1..n_genomes_per_run) into `ga_runs_payload_packed`
    for packed multi-run execution.

    Row 0 (per-run best) is intentionally left untouched.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    if n_runs > 0 and n_genomes_per_run > 0:
        n_total = n_runs * n_genomes_per_run
        for g in range(n_total):
            run = g // n_genomes_per_run
            local_g = g - run * n_genomes_per_run
            run_idx = run_idx_start + run
            out_row = local_g + 1

            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 0] = kernels_helpers.ga_scores[g]
            for s in range(n_slots):
                kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + s] = kernels_helpers.population_indices[
                    g, s
                ]
            res = kernels_helpers.genome_result_stats[g]
            for j in ti.static(range(7)):
                kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + n_slots + j] = res[j]


@ti.kernel
def ga_copy_runs_payload_to_download_staging_kernel(
    out_payload: ti.template(),
    n_runs: ti.i32,
    n_genomes: ti.i32,
    n_slots: ti.i32,
):
    """
    Copy the populated slice of `ga_runs_payload_packed` into a smaller staging field.

    Vulkan `to_numpy()` transfers the full field shape, so downloading the padded
    `(MAX_GA_RUNS, MAX_GA_RUN_GENOMES+1, 17)` buffer can dominate throughput when
    `MAX_GA_RUN_GENOMES` is large (e.g., 1024) but the active population is small
    (e.g., 250). This kernel enables a bounded staging download.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    cols = 1 + n_slots + 7
    rows = n_genomes + 1
    for r, row in ti.ndrange(n_runs, rows):
        for c in ti.static(range(17)):
            if c < cols:
                out_payload[r, row, c] = kernels_helpers.ga_runs_payload_packed[r, row, c]


@ti.kernel
def ga_pack_fg_candidates_table_segmented_kernel(
    table_slot: ti.i32,
    run_idx_start: ti.i32,
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_slots: ti.i32,
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
    use_exact_inner_solver: ti.template(),
):
    """
    Pack a compact GA->FG candidate table into `ga_fg_candidates_packed`.

    Row layout (int32):
      [score, slot_ids(9), result_row(7), base_stats7(7)]

    - Row 0: per-run best genome tracked across generations (copied from ga_runs_payload_packed row 0).
    - Rows 1..K: top-score genomes from the *final* population for the run (K is env-configured).

    This is intended to replace large `ga_download_runs_payload()` transfers.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    K = ti.static(_GA_FG_CANDIDATES_PER_RUN)

    for r in range(n_runs):
        run_idx = run_idx_start + r

        # ------------------------------------------------------------------
        # Row 0: best (tracked across generations).
        # ------------------------------------------------------------------
        _clear_fg_candidate_row(table_slot, run_idx, 0)

        # Copy (score + ids + result_row) from ga_runs_payload_packed.
        for c in ti.static(range(1 + 9 + _GA_FG_RESULTS_COLS)):
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, c] = kernels_helpers.ga_runs_payload_packed[
                run_idx, 0, c
            ]

        # Canonicalize minis in the packed output (minis are order-invariant).
        m = _sort3_i32(
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + 6],
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + 7],
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + 8],
        )
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, 1 + 6] = m[0]
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, 1 + 7] = m[1]
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, 1 + 8] = m[2]

        # Compute base_stats7 from item IDs (ga_runs_payload_packed row 0 stores genome IDs).
        pp = kernels_helpers.base_fixed_stats[0]
        cm = kernels_helpers.base_fixed_stats[1]
        fm = kernels_helpers.base_fixed_stats[2]
        ft_stat = kernels_helpers.base_fixed_stats[3]
        ff_stat = kernels_helpers.base_fixed_stats[4]
        beat = kernels_helpers.base_fixed_stats[5]
        vibe = kernels_helpers.base_fixed_stats[6]
        rush = kernels_helpers.base_fixed_stats[7]
        flow = kernels_helpers.base_fixed_stats[8]
        chill = kernels_helpers.base_fixed_stats[9]

        for s in range(n_slots):
            item_id = kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + s]
            if item_id > 0:
                pp += kernels_helpers.item_stats[item_id, 0]
                cm += kernels_helpers.item_stats[item_id, 1]
                fm += kernels_helpers.item_stats[item_id, 2]
                ft_stat += kernels_helpers.item_stats[item_id, 3]
                ff_stat += kernels_helpers.item_stats[item_id, 4]
                beat += kernels_helpers.item_stats[item_id, 5]
                vibe += kernels_helpers.item_stats[item_id, 6]
                rush += kernels_helpers.item_stats[item_id, 7]
                flow += kernels_helpers.item_stats[item_id, 8]
                chill += kernels_helpers.item_stats[item_id, 9]

        p_val = (beat * is_p_ft) + (vibe * is_p_ff) + (rush * is_p_fm) + (flow * is_p_cm) + (chill * is_p_pp)
        s_val = (beat * is_s_ft) + (vibe * is_s_ff) + (rush * is_s_fm) + (flow * is_s_cm) + (chill * is_s_pp)

        base_col0 = 1 + 9 + _GA_FG_RESULTS_COLS
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, base_col0 + 0] = pp
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, base_col0 + 1] = cm
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, base_col0 + 2] = fm
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, base_col0 + 3] = p_val
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, base_col0 + 4] = s_val
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, base_col0 + 5] = ft_stat
        kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, base_col0 + 6] = ff_stat

        # ------------------------------------------------------------------
        # Rows 1..K: top unique candidates from final population (per run).
        #
        # This must dedupe before the top-K cutoff. A converged GA population can
        # have dozens of copies of the same high-scoring genome at the front; if
        # we pack raw rows first, downstream FG/persistence selection only sees a
        # thin frontier even when lower-ranked unique genomes still exist.
        # ------------------------------------------------------------------
        top_scores = ti.Vector.zero(ti.i32, K)
        top_idx = ti.Vector.zero(ti.i32, K)
        for j in range(K):
            top_scores[j] = ti.i32(-2147483648)
            top_idx[j] = ti.i32(-1)

        start_offset = r * n_genomes_per_run
        for local_g in range(n_genomes_per_run):
            g = start_offset + local_g
            score = kernels_helpers.ga_scores[g]
            if score <= 0:
                continue

            mm_g = _sort3_i32(
                kernels_helpers.population_indices[g, 6],
                kernels_helpers.population_indices[g, 7],
                kernels_helpers.population_indices[g, 8],
            )

            duplicate_slot = ti.i32(-1)
            for j in range(K):
                prev_g = top_idx[j]
                if (
                    duplicate_slot < 0
                    and prev_g >= 0
                    and _population_key_matches(
                        prev_g,
                        kernels_helpers.population_indices[g, 0],
                        kernels_helpers.population_indices[g, 1],
                        kernels_helpers.population_indices[g, 2],
                        kernels_helpers.population_indices[g, 3],
                        kernels_helpers.population_indices[g, 4],
                        kernels_helpers.population_indices[g, 5],
                        mm_g[0],
                        mm_g[1],
                        mm_g[2],
                    )
                    != 0
                ):
                    duplicate_slot = j

            if duplicate_slot >= 0:
                if score > top_scores[duplicate_slot]:
                    top_scores[duplicate_slot] = score
                    top_idx[duplicate_slot] = g
                    _bubble_fg_candidate_up(top_scores, top_idx, duplicate_slot)
            else:
                inserted = ti.i32(0)
                for j in range(K):
                    if inserted == 0 and score > top_scores[j]:
                        # Shift down 1 slot for indices > j.
                        for t in range(K - 1):
                            tt = (K - 1) - t
                            if tt > j:
                                top_scores[tt] = top_scores[tt - 1]
                                top_idx[tt] = top_idx[tt - 1]
                        top_scores[j] = score
                        top_idx[j] = g
                        inserted = 1

        for j in range(K):
            out_row = 1 + j
            g = top_idx[j]
            score = top_scores[j]

            _clear_fg_candidate_row(table_slot, run_idx, out_row)

            if g < 0 or score <= 0:
                continue

            combo_idx = _best_combo_idx_from_chunk_state(g)
            if combo_idx < 0:
                continue

            result_stats = _materialize_best_combo_stats(
                g,
                combo_idx,
                total_budget,
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
                use_exact_inner_solver,
            )
            _write_fg_candidate_row_from_genome(
                table_slot,
                run_idx,
                out_row,
                g,
                n_slots,
                result_stats,
            )


@ti.kernel
def ga_copy_fg_candidates_table_to_download_staging_kernel(table_slot: ti.i32, n_runs: ti.i32):
    """
    Copy a single table slot slice from `ga_fg_candidates_packed` into `ga_fg_candidates_download_staging`.

    Vulkan `to_numpy()` transfers the full field shape. Keeping the download staging field
    slot-less avoids transferring all (MAX_SONG_SLOTS, ...) table slots when callers want one.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    K = ti.static(_GA_FG_CANDIDATES_PER_RUN)
    rows = ti.static(K + 1)
    for r, row in ti.ndrange(n_runs, rows):
        for c in ti.static(range(_GA_FG_COLS)):
            kernels_helpers.ga_fg_candidates_download_staging[r, row, c] = kernels_helpers.ga_fg_candidates_packed[
                table_slot, r, row, c
            ]


# ============================================================================
# GPU-side GA->FG candidate selection (avoid CPU downloads for funnel selection)
# ============================================================================


@ti.func
def _hash9_i32(
    a0: ti.i32,
    a1: ti.i32,
    a2: ti.i32,
    a3: ti.i32,
    a4: ti.i32,
    a5: ti.i32,
    a6: ti.i32,
    a7: ti.i32,
    a8: ti.i32,
) -> ti.u32:
    """
    Deterministic 32-bit hash of 9 int32 values (FNV-1a).

    Note: This is used only for open-addressing placement; collisions are resolved
    by full key comparison.
    """
    h = ti.u32(2166136261)
    for v in ti.static([a0, a1, a2, a3, a4, a5, a6, a7, a8]):
        h = (h ^ ti.cast(v, ti.u32)) * ti.u32(16777619)
    return h


@ti.func
def _better_base(i: ti.i32, j: ti.i32) -> ti.i32:
    better = ti.i32(0)
    decided = ti.i32(0)

    si = kernels_helpers.ga_fg_select_stub_score[i]
    sj = kernels_helpers.ga_fg_select_stub_score[j]
    if si != sj:
        better = ti.i32(1) if si > sj else ti.i32(0)
        decided = ti.i32(1)

    if decided == 0:
        # Tie-break by canonical IDs (descending, left-to-right).
        for k in ti.static(range(9)):
            ai = kernels_helpers.ga_fg_select_stub_ids[i, k]
            aj = kernels_helpers.ga_fg_select_stub_ids[j, k]
            if decided == 0 and ai != aj:
                better = ti.i32(1) if ai > aj else ti.i32(0)
                decided = ti.i32(1)

    if decided == 0:
        # Final stable tie-breaker: lower stub index wins.
        better = ti.i32(1) if i < j else ti.i32(0)

    return better


@ti.func
def _pick_best_base_stub(n_stub: ti.i32) -> ti.i32:
    best = ti.i32(-1)
    ti.loop_config(serialize=True)
    for i in range(n_stub):
        if kernels_helpers.ga_fg_select_selected_mask[i] != 0:
            continue
        if best < 0 or _better_base(i, best) != 0:
            best = i
    return best


@ti.kernel
def ga_select_top_base_fg_candidate_coords_kernel(
    table_slot: ti.i32,
    n_runs: ti.i32,
    limit: ti.i32,
):
    """
    Select a bounded GA->FG candidate funnel on the GPU and store selected stub indices.

    Output:
      - ga_fg_selected_count[0] = N
      - ga_fg_selected_coords[i,0] = stub_index (for i in [0,N))

    Notes:
    - This kernel keeps the configured top base-score effective-unique rows.
    - The scan includes row 0 (per-run best across generations) so non-final-population
      winners remain eligible for the downstream FG funnel.
    - Minis are canonicalized (sorted) for keys.
    """
    K = ti.static(_GA_FG_CANDIDATES_PER_RUN)

    # Clear hash table + counters.
    for i in range(kernels_helpers.ga_fg_select_hash_used.shape[0]):
        kernels_helpers.ga_fg_select_hash_used[i] = 0
    kernels_helpers.ga_fg_select_stub_count[0] = 0

    # Best-effort clear selection mask (bounded by stub capacity).
    for i in range(kernels_helpers.ga_fg_select_selected_mask.shape[0]):
        kernels_helpers.ga_fg_select_selected_mask[i] = 0
    kernels_helpers.ga_fg_selected_count[0] = 0

    # ------------------------------------------------------------------
    # 1) Build unique stubs.
    #
    # For each canonical (gear + sorted minis) key, keep the occurrence with the
    # highest base score. Tie-breaker matches CPU: earliest scan order among max-score
    # occurrences (we only update on strictly better score).
    #
    # Scan order: runs in order, within each run row 0 is the per-run tracked best,
    # then rows 1..K are the per-run candidate archive.
    # ------------------------------------------------------------------
    ti.loop_config(serialize=True)
    for r in range(n_runs):
        for j in range(K + 1):
            row_idx = j
            score = kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 0]
            if score <= 0:
                continue

            # Canonical key: 6 gear + sorted 3 minis.
            g0 = kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 0]
            g1 = kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 1]
            g2 = kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 2]
            g3 = kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 3]
            g4 = kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 4]
            g5 = kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 5]
            mm = _sort3_i32(
                kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 6],
                kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 7],
                kernels_helpers.ga_fg_candidates_packed[table_slot, r, row_idx, 1 + 8],
            )
            m0 = mm[0]
            m1 = mm[1]
            m2 = mm[2]

            h = _hash9_i32(g0, g1, g2, g3, g4, g5, m0, m1, m2)
            mask = kernels_helpers.ga_fg_select_hash_used.shape[0] - 1
            pos = ti.cast(h & ti.u32(mask), ti.i32)

            handled = ti.i32(0)
            for _ in range(kernels_helpers.ga_fg_select_hash_used.shape[0]):
                entry = kernels_helpers.ga_fg_select_hash_used[pos]
                if entry == 0:
                    # Insert as new key.
                    idx = kernels_helpers.ga_fg_select_stub_count[0]
                    # Store stub index + 1 (0 means empty).
                    kernels_helpers.ga_fg_select_hash_used[pos] = idx + 1
                    kernels_helpers.ga_fg_select_hash_keys[pos, 0] = g0
                    kernels_helpers.ga_fg_select_hash_keys[pos, 1] = g1
                    kernels_helpers.ga_fg_select_hash_keys[pos, 2] = g2
                    kernels_helpers.ga_fg_select_hash_keys[pos, 3] = g3
                    kernels_helpers.ga_fg_select_hash_keys[pos, 4] = g4
                    kernels_helpers.ga_fg_select_hash_keys[pos, 5] = g5
                    kernels_helpers.ga_fg_select_hash_keys[pos, 6] = m0
                    kernels_helpers.ga_fg_select_hash_keys[pos, 7] = m1
                    kernels_helpers.ga_fg_select_hash_keys[pos, 8] = m2

                    if idx < kernels_helpers.ga_fg_select_stub_run.shape[0]:
                        kernels_helpers.ga_fg_select_stub_run[idx] = r
                        kernels_helpers.ga_fg_select_stub_row[idx] = row_idx
                        kernels_helpers.ga_fg_select_stub_score[idx] = score

                        kernels_helpers.ga_fg_select_stub_ids[idx, 0] = g0
                        kernels_helpers.ga_fg_select_stub_ids[idx, 1] = g1
                        kernels_helpers.ga_fg_select_stub_ids[idx, 2] = g2
                        kernels_helpers.ga_fg_select_stub_ids[idx, 3] = g3
                        kernels_helpers.ga_fg_select_stub_ids[idx, 4] = g4
                        kernels_helpers.ga_fg_select_stub_ids[idx, 5] = g5
                        kernels_helpers.ga_fg_select_stub_ids[idx, 6] = m0
                        kernels_helpers.ga_fg_select_stub_ids[idx, 7] = m1
                        kernels_helpers.ga_fg_select_stub_ids[idx, 8] = m2

                        kernels_helpers.ga_fg_select_stub_count[0] = idx + 1
                    handled = 1
                    break

                # Occupied: check full key match.
                if (
                    kernels_helpers.ga_fg_select_hash_keys[pos, 0] == g0
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 1] == g1
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 2] == g2
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 3] == g3
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 4] == g4
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 5] == g5
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 6] == m0
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 7] == m1
                    and kernels_helpers.ga_fg_select_hash_keys[pos, 8] == m2
                ):
                    idx = entry - 1
                    if 0 <= idx and idx < kernels_helpers.ga_fg_select_stub_run.shape[0]:
                        # Keep max score for this key (tie-break by earliest scan: only update on strictly better score).
                        prev_score = kernels_helpers.ga_fg_select_stub_score[idx]
                        if score > prev_score:
                            kernels_helpers.ga_fg_select_stub_run[idx] = r
                            kernels_helpers.ga_fg_select_stub_row[idx] = row_idx
                            kernels_helpers.ga_fg_select_stub_score[idx] = score
                    handled = 1  # Already present; treat as handled.
                    break
                pos = (pos + 1) & mask

            if handled == 0:
                # Hash table saturated; stop adding new unique stubs.
                pass

    n_stub = kernels_helpers.ga_fg_select_stub_count[0]

    # Clamp staging limit.
    limit_v = limit

    if limit_v < 0:
        limit_v = 0
    if limit_v > kernels_helpers.ga_fg_selected_coords.shape[0]:
        limit_v = kernels_helpers.ga_fg_selected_coords.shape[0]

    # ------------------------------------------------------------------
    # 2) Select top base-score stubs into ga_fg_selected_coords.
    # ------------------------------------------------------------------
    selected_n = ti.i32(0)

    while selected_n < limit_v:
        best = _pick_best_base_stub(n_stub)
        if best < 0:
            break
        kernels_helpers.ga_fg_select_selected_mask[best] = 1
        kernels_helpers.ga_fg_selected_coords[selected_n, 0] = best
        kernels_helpers.ga_fg_selected_coords[selected_n, 1] = 0
        selected_n += 1

    kernels_helpers.ga_fg_selected_count[0] = selected_n


@ti.kernel
def ga_copy_fg_selected_payload_to_download_staging_kernel(
    table_slot: ti.i32,
    n_runs: ti.i32,
    out_payload: ti.template(),
):
    """
    Copy selected candidates into a bounded 2D staging buffer for a single CPU download.

    Output `out_payload` shape: (Nmax+1, 26)
      - Row 0: header
      - Rows 1..N: candidates [run,row] + packed candidate row (24)
    """
    base_cols = ti.static(_GA_FG_COLS)  # 24
    results_col0 = ti.static(1 + 9)

    # Header: selected_count, best_score, best_ids(9), best_results(7), best_run_idx
    selected_n = kernels_helpers.ga_fg_selected_count[0]
    if selected_n < 0:
        selected_n = 0
    max_rows = out_payload.shape[0] - 1
    if selected_n > max_rows:
        selected_n = max_rows

    best_score = ti.i32(-1)
    best_run = ti.i32(0)
    # Deterministic scan across per-run best (row 0).
    for r in range(n_runs):
        s = kernels_helpers.ga_fg_candidates_packed[table_slot, r, 0, 0]
        if s > best_score:
            best_score = s
            best_run = r

    # Clear header row (avoid stale data when caller changes staging size).
    for c in range(out_payload.shape[1]):
        out_payload[0, c] = 0

    out_payload[0, 0] = selected_n
    out_payload[0, 1] = best_score
    # Best IDs + results from best run row0.
    for s in ti.static(range(9)):
        out_payload[0, 2 + s] = kernels_helpers.ga_fg_candidates_packed[table_slot, best_run, 0, 1 + s]
    for t in ti.static(range(_GA_FG_RESULTS_COLS)):
        out_payload[0, 2 + 9 + t] = kernels_helpers.ga_fg_candidates_packed[table_slot, best_run, 0, results_col0 + t]
    out_payload[0, 2 + 9 + _GA_FG_RESULTS_COLS] = best_run

    # Candidate rows.
    for i in range(selected_n):
        stub = kernels_helpers.ga_fg_selected_coords[i, 0]
        run_idx = kernels_helpers.ga_fg_select_stub_run[stub]
        row_idx = kernels_helpers.ga_fg_select_stub_row[stub]
        out_payload[i + 1, 0] = run_idx
        out_payload[i + 1, 1] = row_idx
        for c in ti.static(range(base_cols)):
            out_payload[i + 1, 2 + c] = kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, c]
