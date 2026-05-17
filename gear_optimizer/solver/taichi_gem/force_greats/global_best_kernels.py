"""
ForceGreats global-best and staged-download kernels.
"""

# ruff: noqa: F405,F821

import taichi as ti

from ..kernels import kernels_helpers
from .fields import FG_DOWNLOAD_BATCH_MAX, FG_DOWNLOAD_TOPK_MAX, FG_MAX_SECTIONS

__all__ = [
    "fg_pack_results_kernel",
    "fg_copy_best_packed_to_download_staging_kernel",
    "fg_copy_global_best_packed_to_download_staging_kernel",
    "fg_pack_global_best_kernel",
    "fg_select_global_best_topk_kernel",
    "fg_pack_selected_global_best_kernel",
    "fg_pack_selected_global_best_batch_kernel",
    "fg_copy_selected_packed_batch_to_download_staging_kernel",
    "fg_reset_global_best_kernel",
    "fg_update_global_best_kernel",
]

# Reuse the shared kernel block dim to keep launch config consistent with other kernels.
_KERNEL_BLOCK_DIM = kernels_helpers._KERNEL_BLOCK_DIM


@ti.kernel
def fg_pack_results_kernel(n_genomes: ti.i32):
    """
    Pack best result fields + cfg_counts into a single contiguous array for efficient CPU download.

    This eliminates 11 separate to_numpy() calls (11 CPU waits) into 1 single download.
    MASSIVE speedup on weak CPUs that bottleneck on GPU synchronization.

    Column order: [final_score, base_score, cfg_idx, ft, ff, g_pp, g_cm, g_fm, g_ov, score_penalty, fill_penalty, cfg_counts...]
    """
    for g in range(n_genomes):
        fg_best_packed[g, 0] = fg_best_final_score[g]
        fg_best_packed[g, 1] = fg_best_base_score[g]
        fg_best_packed[g, 2] = fg_best_cfg_idx[g]
        fg_best_packed[g, 3] = fg_best_ft[g]
        fg_best_packed[g, 4] = fg_best_ff[g]
        fg_best_packed[g, 5] = fg_best_g_pp[g]
        fg_best_packed[g, 6] = fg_best_g_cm[g]
        fg_best_packed[g, 7] = fg_best_g_fm[g]
        fg_best_packed[g, 8] = fg_best_g_ov[g]
        fg_best_packed[g, 9] = fg_best_score_penalty[g]
        fg_best_packed[g, 10] = fg_best_fill_penalty[g]
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_best_packed[g, 11 + s] = fg_best_cfg_counts[g, s]


@ti.kernel
def fg_copy_best_packed_to_download_staging_kernel(out_packed: ti.template(), n_genomes: ti.i32):
    """
    Copy the populated prefix of `fg_best_packed` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES buffer can add avoidable sync/transfer overhead when only a small
    number of genomes are active (e.g., a compact GA run).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    total_cols = 11 + FG_MAX_SECTIONS
    for g, c in ti.ndrange(n_genomes, total_cols):
        out_packed[g, c] = fg_best_packed[g, c]


@ti.kernel
def fg_copy_global_best_packed_to_download_staging_kernel(out_packed: ti.template(), n_genomes: ti.i32):
    """
    Copy the populated prefix of `fg_global_best_packed` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES buffer can add avoidable sync/transfer overhead when only a small
    number of genomes are active (e.g., a compact GA run).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    total_cols = 11 + FG_MAX_SECTIONS
    for g, c in ti.ndrange(n_genomes, total_cols):
        out_packed[g, c] = fg_global_best_packed[g, c]


@ti.kernel
def fg_pack_global_best_kernel(session_slot: ti.i32, n_genomes: ti.i32):
    """
    Pack all global-best fields + cfg_counts into a single contiguous array for efficient CPU download.

    Mirrors `fg_pack_results_kernel`, but for the GPU-resident global best buffers used by
    multi-group accumulation.
    """
    for g in range(n_genomes):
        fg_global_best_packed[g, 0] = fg_global_best_final_score[session_slot, g]
        fg_global_best_packed[g, 1] = fg_global_best_base_score[session_slot, g]
        fg_global_best_packed[g, 2] = fg_global_best_cfg_idx[session_slot, g]
        fg_global_best_packed[g, 3] = fg_global_best_ft[session_slot, g]
        fg_global_best_packed[g, 4] = fg_global_best_ff[session_slot, g]
        fg_global_best_packed[g, 5] = fg_global_best_g_pp[session_slot, g]
        fg_global_best_packed[g, 6] = fg_global_best_g_cm[session_slot, g]
        fg_global_best_packed[g, 7] = fg_global_best_g_fm[session_slot, g]
        fg_global_best_packed[g, 8] = fg_global_best_g_ov[session_slot, g]
        fg_global_best_packed[g, 9] = fg_global_best_score_penalty[session_slot, g]
        fg_global_best_packed[g, 10] = fg_global_best_fill_penalty[session_slot, g]
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_global_best_packed[g, 11 + s] = fg_global_best_cfg_counts[session_slot, g, s]


@ti.kernel
def fg_select_global_best_topk_kernel(session_slot: ti.i32, n_genomes: ti.i32, topk: ti.i32):
    """
    Build a compact list of genome indices worth downloading from global_best.

    Output order:
    - keep items first (in ascending genome index)
    - then top-k candidates by final_score (descending), tie-breaking by lower genome index (stable)

    Eligibility filter for candidates:
    - final_score > fg_input_base_score
    - fg_global_best_fill_penalty > 0 (implies at least one forced section; matches CPU "valid config" intent)
    """
    k: ti.i32 = topk
    if k < 0:
        k = 0
    if k > ti.i32(FG_DOWNLOAD_TOPK_MAX):
        k = ti.i32(FG_DOWNLOAD_TOPK_MAX)

    # Clear output
    fg_selected_count[None] = 0
    ti.loop_config(serialize=True)
    for j in range(FG_DOWNLOAD_TOPK_MAX):
        fg_selected_indices[j] = -1

    # Keep set: include these indices unconditionally
    keep_count: ti.i32 = 0
    ti.loop_config(serialize=True)
    for i in range(n_genomes):
        if fg_keep_mask[i] != 0:
            if keep_count < ti.i32(FG_DOWNLOAD_TOPK_MAX):
                fg_selected_indices[keep_count] = i
                keep_count += 1

    start: ti.i32 = keep_count
    max_k: ti.i32 = k
    if start + max_k > ti.i32(FG_DOWNLOAD_TOPK_MAX):
        max_k = ti.i32(FG_DOWNLOAD_TOPK_MAX) - start
    if max_k < 0:
        max_k = 0

    # Initialize candidate slots
    ti.loop_config(serialize=True)
    for j in range(max_k):
        fg_selected_indices[start + j] = -1

    # Insert-sort top-k candidates by packed key
    ti.loop_config(serialize=True)
    for i in range(n_genomes):
        if fg_keep_mask[i] != 0:
            continue
        score: ti.i32 = fg_global_best_final_score[session_slot, i]
        if score <= fg_input_base_score[i]:
            continue
        if fg_global_best_fill_penalty[session_slot, i] <= 0:
            continue

        key: ti.i64 = (ti.cast(score, ti.i64) << 32) | ti.cast(0x7FFFFFFF - i, ti.i64)
        pos: ti.i32 = max_k

        # Find insertion point
        for j in range(max_k):
            idx_j: ti.i32 = fg_selected_indices[start + j]
            if idx_j < 0:
                pos = j
                break
            score_j: ti.i32 = fg_global_best_final_score[session_slot, idx_j]
            key_j: ti.i64 = (ti.cast(score_j, ti.i64) << 32) | ti.cast(0x7FFFFFFF - idx_j, ti.i64)
            if key > key_j:
                pos = j
                break

        if pos < max_k:
            # Shift down to make room
            for off in range(max_k - 1):
                s: ti.i32 = (max_k - 1) - off
                if s > pos:
                    fg_selected_indices[start + s] = fg_selected_indices[start + s - 1]
            fg_selected_indices[start + pos] = i

    # Compute final count (keep + filled candidates)
    count: ti.i32 = keep_count
    ti.loop_config(serialize=True)
    for j in range(max_k):
        if fg_selected_indices[start + j] >= 0:
            count += 1
        else:
            break
    fg_selected_count[None] = count


@ti.kernel
def fg_pack_selected_global_best_kernel(session_slot: ti.i32, n_selected: ti.i32):
    """Pack selected rows from global_best into fg_selected_packed for fast CPU download.

    Column order (12 + FG_MAX_SECTIONS):
      [genome_idx, final_score, base_score, cfg_idx, ft, ff, g_pp, g_cm, g_fm, g_ov, score_penalty, fill_penalty, cfg_counts...]
    """
    total_cols = 12 + FG_MAX_SECTIONS
    for j in range(n_selected):
        idx: ti.i32 = fg_selected_indices[j]
        fg_selected_packed[j, 0] = idx
        if idx < 0:
            for c in range(1, total_cols):
                fg_selected_packed[j, c] = 0
            continue
        fg_selected_packed[j, 1] = fg_global_best_final_score[session_slot, idx]
        fg_selected_packed[j, 2] = fg_global_best_base_score[session_slot, idx]
        fg_selected_packed[j, 3] = fg_global_best_cfg_idx[session_slot, idx]
        fg_selected_packed[j, 4] = fg_global_best_ft[session_slot, idx]
        fg_selected_packed[j, 5] = fg_global_best_ff[session_slot, idx]
        fg_selected_packed[j, 6] = fg_global_best_g_pp[session_slot, idx]
        fg_selected_packed[j, 7] = fg_global_best_g_cm[session_slot, idx]
        fg_selected_packed[j, 8] = fg_global_best_g_fm[session_slot, idx]
        fg_selected_packed[j, 9] = fg_global_best_g_ov[session_slot, idx]
        fg_selected_packed[j, 10] = fg_global_best_score_penalty[session_slot, idx]
        fg_selected_packed[j, 11] = fg_global_best_fill_penalty[session_slot, idx]
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_selected_packed[j, 12 + s] = fg_global_best_cfg_counts[session_slot, idx, s]


@ti.kernel
def fg_pack_selected_global_best_batch_kernel(session_slot: ti.i32, n_selected: ti.i32, batch_idx: ti.i32):
    """Pack selected rows from global_best into `fg_selected_packed_batch[batch_idx]`.

    This is used by executor-side batching so multiple payloads can be downloaded via a single `to_numpy()`.
    """
    if batch_idx >= 0 and batch_idx < ti.i32(FG_DOWNLOAD_BATCH_MAX):
        total_cols = 12 + FG_MAX_SECTIONS
        for j in range(n_selected):
            idx: ti.i32 = fg_selected_indices[j]
            fg_selected_packed_batch[batch_idx, j, 0] = idx
            if idx < 0:
                for c in range(1, total_cols):
                    fg_selected_packed_batch[batch_idx, j, c] = 0
                continue
            fg_selected_packed_batch[batch_idx, j, 1] = fg_global_best_final_score[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 2] = fg_global_best_base_score[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 3] = fg_global_best_cfg_idx[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 4] = fg_global_best_ft[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 5] = fg_global_best_ff[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 6] = fg_global_best_g_pp[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 7] = fg_global_best_g_cm[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 8] = fg_global_best_g_fm[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 9] = fg_global_best_g_ov[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 10] = fg_global_best_score_penalty[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 11] = fg_global_best_fill_penalty[session_slot, idx]
            for s in ti.static(range(FG_MAX_SECTIONS)):
                fg_selected_packed_batch[batch_idx, j, 12 + s] = fg_global_best_cfg_counts[session_slot, idx, s]


@ti.kernel
def fg_copy_selected_packed_batch_to_download_staging_kernel(out_packed: ti.template(), n_payloads: ti.i32):
    """
    Copy the populated prefix of `fg_selected_packed_batch` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    FG_DOWNLOAD_BATCH_MAX buffer can dominate throughput when only a small number of
    payloads are active in a fused executor bundle.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    total_cols = 12 + FG_MAX_SECTIONS
    for batch_idx, j in ti.ndrange(n_payloads, FG_DOWNLOAD_TOPK_MAX):
        for c in range(total_cols):
            out_packed[batch_idx, j, c] = fg_selected_packed_batch[batch_idx, j, c]


@ti.kernel
def fg_reset_global_best_kernel(session_slot: ti.i32, n_genomes: ti.i32):
    """
    Reset global best fields to sentinel values before multi-group processing.

    Call this once at the start of a batch of FG groups, before the loop.
    """
    for i in range(n_genomes):
        fg_global_best_final_score[session_slot, i] = -1
        fg_global_best_base_score[session_slot, i] = 0
        fg_global_best_cfg_idx[session_slot, i] = -1
        fg_global_best_ft[session_slot, i] = 0
        fg_global_best_ff[session_slot, i] = 0
        fg_global_best_g_pp[session_slot, i] = 0
        fg_global_best_g_cm[session_slot, i] = 0
        fg_global_best_g_fm[session_slot, i] = 0
        fg_global_best_g_ov[session_slot, i] = 0
        fg_global_best_score_penalty[session_slot, i] = 0
        fg_global_best_fill_penalty[session_slot, i] = 0
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_global_best_cfg_counts[session_slot, i, s] = 0


@ti.kernel
def fg_update_global_best_kernel(session_slot: ti.i32, n_genomes: ti.i32):
    """
    Compare current fg_best_* results with fg_global_best_*, update if better.

    Call this after each solve_force_greats_finder_gpu() call to accumulate
    the best results across all groups without downloading to CPU.
    """
    for gid in range(n_genomes):
        new_score = fg_best_final_score[gid]
        old_score = fg_global_best_final_score[session_slot, gid]
        new_cfg = fg_best_cfg_idx[gid]
        old_cfg = fg_global_best_cfg_idx[session_slot, gid]
        new_ft = fg_best_ft[gid]
        old_ft = fg_global_best_ft[session_slot, gid]
        new_ff = fg_best_ff[gid]
        old_ff = fg_global_best_ff[session_slot, gid]

        # Deterministic tie-breaking:
        # 1) Higher final score wins.
        # 2) If scores tie, prefer lower cfg_idx (matches stage1 packed tie-break).
        # 3) If still tied, prefer lower (ft, ff) lexicographically for stability.
        better = False
        if new_score > old_score:
            better = True
        elif new_score == old_score:
            if old_cfg < 0 and new_cfg >= 0:
                better = True
            elif new_cfg >= 0 and new_cfg < old_cfg:
                better = True
            elif new_cfg == old_cfg:
                if new_ft < old_ft:
                    better = True
                elif new_ft == old_ft and new_ff < old_ff:
                    better = True

        if better:
            fg_global_best_final_score[session_slot, gid] = new_score
            fg_global_best_base_score[session_slot, gid] = fg_best_base_score[gid]
            fg_global_best_cfg_idx[session_slot, gid] = new_cfg
            fg_global_best_ft[session_slot, gid] = new_ft
            fg_global_best_ff[session_slot, gid] = new_ff
