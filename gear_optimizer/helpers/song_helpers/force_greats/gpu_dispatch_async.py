from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from ....core.fallback_monitor import warn_fallback

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuServiceClient


@dataclass(frozen=True)
class FgAsyncBatchingSettings:
    in_process: bool
    max_inflight: int
    tasks_per_request: int
    enforce_single_request: bool


@dataclass(frozen=True)
class FgAsyncThresholdFlushPlan:
    submit_count: int
    keep_queued_count: int


def plan_fg_async_threshold_flush(*, pending_tasks: int, tasks_per_request: int) -> FgAsyncThresholdFlushPlan:
    """
    Decide how many queued FG tasks to submit once the async request threshold is checked.

    Policy:
    - Below the threshold, keep everything queued.
    - At or above the threshold, flush the full pending batch so the next request boundary
      is not gated on building one more CPU-side task.
    """
    pending = max(0, int(pending_tasks))
    threshold = max(1, int(tasks_per_request))
    if pending < threshold:
        return FgAsyncThresholdFlushPlan(submit_count=0, keep_queued_count=int(pending))
    return FgAsyncThresholdFlushPlan(submit_count=int(pending), keep_queued_count=0)


def warmup_force_greats_finder_runtime_imports() -> None:
    """
    Load the heavy ForceGreatsFinder runtime modules before per-song FG prep starts.

    Importing the Taichi FG API path can take seconds on cold Windows/Vulkan runs.
    Doing it under the per-song prep lock makes the prep pool look parallel while
    all threads actually queue behind one import. The GPU executor calls this
    during its warmup; the prep path calls it only as a cheap cached fallback.
    """
    from gear_optimizer.helpers.fg_utils import (
        _sample_stat_pairs,
        collect_analytical_breakpoints,
        iter_analytical_breakpoint_groups,
    )
    from gear_optimizer.solver.analytical_fg import create_chart_scorer_from_calc_song, create_scorer_from_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        fg_select_signature_frontier_batch,
        solve_force_greats_finder_gpu,
    )

    _ = (
        _sample_stat_pairs,
        collect_analytical_breakpoints,
        iter_analytical_breakpoint_groups,
        create_chart_scorer_from_calc_song,
        create_scorer_from_calc_song,
        fg_fields,
        fg_download_global_best,
        fg_reset_global_best,
        fg_select_signature_frontier_batch,
        solve_force_greats_finder_gpu,
    )


def resolve_fg_async_batching_settings(
    *,
    gpu_client: Optional["GpuServiceClient"],
    song_slot: int,
    perf: bool,
) -> FgAsyncBatchingSettings:
    """
    Resolve Force Greats async batching settings.

    This logic is intentionally conservative in in-process mode to reduce the risk of multi-second
    continuous GPU work (Windows TDR / UI freezes).
    """
    in_process = False
    if gpu_client is not None:
        try:
            ex = getattr(gpu_client, "executor", None)
            in_process = bool(getattr(ex, "_in_process_queues", False))
        except Exception:
            in_process = False

    fg_async_max_inflight_default = 8
    if gpu_client is not None:
        # Allow deeper pipelining to keep the GPU queue saturated. IPC and in-process both benefit.
        fg_async_max_inflight_default = 32

    try:
        fg_async_max_inflight = int(os.environ.get("FG_ASYNC_MAX_INFLIGHT", str(fg_async_max_inflight_default)))
    except Exception:
        fg_async_max_inflight = fg_async_max_inflight_default
    fg_async_max_inflight = max(1, int(fg_async_max_inflight))

    fg_async_tasks_per_request_default = 8
    if gpu_client is not None and "FG_ASYNC_TASKS_PER_REQUEST" not in os.environ:
        try:
            if in_process:
                # In in-process (thread-queue) mode, larger batches reduce submit-side bubbles between
                # FG requests, but we still cap the default at the proven safe window for Windows/TDR.
                fg_async_tasks_per_request_default = 512
            else:
                # IPC mode: batch aggressively enough to reduce per-request overhead.
                fg_async_tasks_per_request_default = 256
        except Exception:
            fg_async_tasks_per_request_default = 8

    fg_async_tasks_per_request = fg_async_tasks_per_request_default
    try:
        fg_async_tasks_per_request = int(
            os.environ.get("FG_ASYNC_TASKS_PER_REQUEST", str(fg_async_tasks_per_request_default))
        )
    except Exception:
        fg_async_tasks_per_request = fg_async_tasks_per_request_default
    fg_async_tasks_per_request = max(1, int(fg_async_tasks_per_request))

    if gpu_client is not None and in_process and int(fg_async_tasks_per_request) > 512:
        if not hasattr(resolve_fg_async_batching_settings, "_fg_tasks_per_req_clamp_warned"):
            resolve_fg_async_batching_settings._fg_tasks_per_req_clamp_warned = True
            print(
                "[FG][WARN] FG_ASYNC_TASKS_PER_REQUEST is very high "
                f"({int(fg_async_tasks_per_request)}); clamping to 512 to reduce TDR/freezing risk."
            )
        fg_async_tasks_per_request = 512

    if perf and gpu_client is not None:
        mode = "in_process" if in_process else "ipc"
        print(
            f"[FG][ASYNC] mode={mode} max_inflight={fg_async_max_inflight} tasks_per_request={fg_async_tasks_per_request}"
        )

    unsafe_multi_request_slot = False
    try:
        unsafe_multi_request_slot = int(song_slot) <= 0
    except Exception:
        unsafe_multi_request_slot = True

    enforce_single_request = False
    if gpu_client is not None and unsafe_multi_request_slot:
        enforce_single_request = True
        if not hasattr(resolve_fg_async_batching_settings, "_fg_multi_request_slot_warned"):
            resolve_fg_async_batching_settings._fg_multi_request_slot_warned = True
            warn_fallback(
                "fg.async.single_request_slot_guard",
                "multi-request FG requires non-zero song_slot; forcing single-request execution",
                context={"song_slot": int(song_slot) if str(song_slot).strip("-").isdigit() else 0},
                fatal=False,
            )

    if enforce_single_request:
        fg_async_max_inflight = 1
        fg_async_tasks_per_request = 1_000_000_000

    return FgAsyncBatchingSettings(
        in_process=bool(in_process),
        max_inflight=int(fg_async_max_inflight),
        tasks_per_request=int(fg_async_tasks_per_request),
        enforce_single_request=bool(enforce_single_request),
    )
