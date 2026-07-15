from __future__ import annotations

from dataclasses import dataclass

_FG_DEFAULT_TARGET_THREADS_PER_KERNEL = 2_000_000


def choose_fg_target_threads_per_kernel(
    *,
    n_work_items: int,
    is_metal: bool,
    target_threads_override: int = 0,
) -> int:
    n_work_items = int(n_work_items)
    target_threads_override = int(target_threads_override)
    if target_threads_override > 0:
        return int(target_threads_override)

    if n_work_items <= 0 or is_metal:
        return _FG_DEFAULT_TARGET_THREADS_PER_KERNEL

    if n_work_items <= 40_000:
        return 6_000_000
    if n_work_items <= 100_000:
        return 4_000_000
    if n_work_items <= 250_000:
        return 3_000_000
    return _FG_DEFAULT_TARGET_THREADS_PER_KERNEL


@dataclass(frozen=True)
class FgStage1ChunkPlan:
    target_threads: int
    target_cfg_per_thread: int
    requested_cfg_chunk: int
    cfg_chunk: int
    single_band_forced: bool


def plan_fg_stage1_cfg_chunk(
    *,
    n_work_items: int,
    stage1_block_dim: int,
    cfg_chunk: int | None,
    max_cfg_len: int,
    is_metal: bool,
    target_threads_override: int = 0,
    small_work_single_band: bool,
    small_work_max_work_items: int,
    small_work_max_cfg_len: int,
) -> FgStage1ChunkPlan:
    n_work_items = int(n_work_items)
    stage1_block_dim = int(stage1_block_dim)
    max_cfg_len = int(max_cfg_len)
    target_threads_override = int(target_threads_override)
    small_work_max_work_items = int(small_work_max_work_items)
    small_work_max_cfg_len = int(small_work_max_cfg_len)
    if stage1_block_dim <= 0:
        stage1_block_dim = 64

    target_threads = choose_fg_target_threads_per_kernel(
        n_work_items=n_work_items,
        is_metal=bool(is_metal),
        target_threads_override=target_threads_override,
    )

    target_cfg_per_thread = 0
    requested_cfg_chunk = int(cfg_chunk) if cfg_chunk is not None else 0
    if requested_cfg_chunk <= 0:
        if is_metal:
            requested_cfg_chunk = 16
        else:
            target_cfg_per_thread = max(1, int(target_threads) // max(1, int(n_work_items) * int(stage1_block_dim)))
            requested_cfg_chunk = max(256, int(target_cfg_per_thread) * int(stage1_block_dim))

    single_band_forced = False
    resolved_cfg_chunk = int(requested_cfg_chunk)
    if int(max_cfg_len) > 0:
        if (
            bool(small_work_single_band)
            and int(n_work_items) <= int(small_work_max_work_items)
            and int(max_cfg_len) <= int(small_work_max_cfg_len)
        ):
            resolved_cfg_chunk = int(max_cfg_len)
            single_band_forced = True
        resolved_cfg_chunk = max(1, min(int(resolved_cfg_chunk), int(max_cfg_len)))
    else:
        resolved_cfg_chunk = max(1, int(resolved_cfg_chunk))

    return FgStage1ChunkPlan(
        target_threads=int(target_threads),
        target_cfg_per_thread=int(target_cfg_per_thread),
        requested_cfg_chunk=int(requested_cfg_chunk),
        cfg_chunk=int(resolved_cfg_chunk),
        single_band_forced=bool(single_band_forced),
    )
