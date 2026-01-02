"""
Taichi Kernels - Pack GA snapshots for CPU download.

Includes:
- ga_pack_run_payload_kernel
- ga_pack_and_store_run_payload_kernel
"""

import taichi as ti

from .. import kernels_helpers


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
