"""
Taichi Kernels - Pack GA snapshots for CPU download.

Includes:
- ga_pack_run_payload_kernel
- ga_pack_and_store_run_payload_kernel
- ga_pack_fg_candidates_table_segmented_kernel
- ga_copy_fg_candidates_table_to_download_staging_kernel
- ga_stage_genome_base_stats_from_fg_candidates_table_kernel
"""

import os

import taichi as ti

from .. import kernels_helpers


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default


# IMPORTANT: must match `fields.GA_FG_CANDIDATES_PER_RUN` at allocation time.
_GA_FG_CANDIDATES_PER_RUN = max(1, min(128, int(_env_int("GPU_GA_FG_CANDIDATES_PER_RUN", 64))))
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
        # Default to zeros (avoid stale columns when n_slots < 9).
        for c in ti.static(range(_GA_FG_COLS)):
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, 0, c] = 0

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
        # Rows 1..K: top candidates from final population (per run).
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

            # Default clear (avoid stale data when fewer than K candidates exist).
            for c in ti.static(range(_GA_FG_COLS)):
                kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, c] = 0

            if g < 0 or score <= 0:
                continue

            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, 0] = score

            # Copy genome IDs; canonicalize minis in output.
            for s in range(n_slots):
                kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, 1 + s] = (
                    kernels_helpers.population_indices[g, s]
                )
            mm = _sort3_i32(
                kernels_helpers.population_indices[g, 6],
                kernels_helpers.population_indices[g, 7],
                kernels_helpers.population_indices[g, 8],
            )
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, 1 + 6] = mm[0]
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, 1 + 7] = mm[1]
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, 1 + 8] = mm[2]

            res = kernels_helpers.genome_result_stats[g]
            for t in ti.static(range(_GA_FG_RESULTS_COLS)):
                kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, 1 + 9 + t] = res[t]

            stats7 = kernels_helpers.genome_base_stats[g]
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, base_col0 + 0] = ti.cast(
                stats7[0], ti.i32
            )
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, base_col0 + 1] = ti.cast(
                stats7[1], ti.i32
            )
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, base_col0 + 2] = ti.cast(
                stats7[2], ti.i32
            )
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, base_col0 + 3] = ti.cast(
                stats7[3], ti.i32
            )
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, base_col0 + 4] = ti.cast(
                stats7[4], ti.i32
            )
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, base_col0 + 5] = ti.cast(
                stats7[5], ti.i32
            )
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, out_row, base_col0 + 6] = ti.cast(
                stats7[6], ti.i32
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


@ti.kernel
def ga_stage_genome_base_stats_from_fg_candidates_table_kernel(
    table_slot: ti.i32,
    n_genomes: ti.i32,
    n_slots: ti.i32,
    coords: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    """
    Stage `genome_base_stats[0:n_genomes]` directly from the packed GA->FG candidate table.

    coords: (n_genomes, 2) int32 array of (run_idx, row_idx) into the candidate table.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    base_col0 = 1 + 9 + _GA_FG_RESULTS_COLS
    for i in range(n_genomes):
        run_idx = coords[i, 0]
        row_idx = coords[i, 1]
        # Read base_stats7 from candidate table and write to shared genome_base_stats.
        # [pp, cm, fm, p_val, s_val, ft_stat, ff_stat]
        kernels_helpers.genome_base_stats[i][0] = ti.cast(
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 0], ti.i16
        )
        kernels_helpers.genome_base_stats[i][1] = ti.cast(
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 1], ti.i16
        )
        kernels_helpers.genome_base_stats[i][2] = ti.cast(
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 2], ti.i16
        )
        kernels_helpers.genome_base_stats[i][3] = ti.cast(
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 3], ti.i16
        )
        kernels_helpers.genome_base_stats[i][4] = ti.cast(
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 4], ti.i16
        )
        kernels_helpers.genome_base_stats[i][5] = ti.cast(
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 5], ti.i16
        )
        kernels_helpers.genome_base_stats[i][6] = ti.cast(
            kernels_helpers.ga_fg_candidates_packed[table_slot, run_idx, row_idx, base_col0 + 6], ti.i16
        )
