"""
GPU-native in-flight multi-song orchestrator (single process, single GPU owner thread).

This pipeline is designed to keep the GPU continuously busy in native GA mode by:
- Preparing the next songs' CPU-only data while the GPU runs the current song.
- Executing GPU-native GA on the Taichi/Vulkan owner thread (GpuExecutor) via an in-process
  request queue (no per-song process overhead, minimal transfers).
- Scheduling ForceGreatsFinder work via continuous credit-based interleaving,
  with CPU grouping/prep performed off the GPU thread and GPU kernels submitted via the executor.
"""

from __future__ import annotations

import logging
import time
import traceback
from collections import deque

from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.domain.jobs import extract_repeat_context, task_queue_label, task_song_name
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient, GpuServiceTimeoutError
from gear_optimizer.solver.native_inflight_config import (
    default_worker_threads,
    first_task_config,
    inflight_shutdown_debug_enabled,
    inflight_stall_debug_enabled,
    parse_inflight_config,
)
from gear_optimizer.solver.inflight_wait import (
    read_inflight_event_wait_timeout_s,
    read_inflight_event_wait_gpu_cap_s,
    read_inflight_event_wait_short_spin_s,
)
from gear_optimizer.solver.native_inflight_prepare import prepare_native_song
from gear_optimizer.solver.native_inflight_scheduler import (
    GAQueueLimitController,
    continuous_fg_allow_not_ready,
    continuous_ga_should_yield_to_fg,
    continuous_fg_should_fill_song_lanes,
    continuous_fg_should_start,
    continuous_fg_submit_budget,
    continuous_ga_warm_queue_limit,
    count_active_song_lanes,
    read_prime_target,
)
from gear_optimizer.solver import native_inflight_fg_pipeline as native_fg_pipeline
from gear_optimizer.solver.native_inflight_ga_pipeline import GADecodeQueue, InflightGAPipeline
from gear_optimizer.solver.native_inflight_persistence import InflightDBPersistence
from gear_optimizer.solver.native_inflight_result_events import (
    build_failed_fg_update_payload as _build_failed_fg_update_payload,
    build_native_song_error_payload as _build_native_song_error_payload,
    build_native_task_error_payload as _build_native_task_error_payload,
)
from gear_optimizer.solver.native_inflight_progress import ActiveRuntimeProgressReporter, ProgressTracker
from gear_optimizer.solver.native_inflight_post_sender import PostSender
from gear_optimizer.solver.native_inflight_completion import (
    CompletionTracker,
    emit_deferred_post_payload as _emit_deferred_post_payload_once,
    finish_deferred_fg_completion,
    has_waitable_work,
    mark_song_completed,
)
from gear_optimizer.solver.native_inflight_bubble import BubbleTracker
from gear_optimizer.solver.native_inflight_bundle import InflightBundleTracker
from gear_optimizer.solver.native_inflight_cpu_prewarm import CpuPrewarmQueue
from gear_optimizer.solver.native_inflight_song_prep_queue import SongPrepQueue
from gear_optimizer.solver.native_inflight_runtime_signals import (
    CachedRuntimeSignal,
    GpuAbortRequester,
    is_stop_abort_exception,
)
from gear_optimizer.solver.native_inflight_abort_log import log_native_abort
from gear_optimizer.solver.native_inflight_types import NativeSong
from gear_optimizer.solver.native_inflight_fg_db_cache import prefetch_db_loadouts_sync
from gear_optimizer.solver.native_inflight_stages import (
    InFlightStageProfiler,
    decode_ga_payload_sync,
    prepare_fg_static_sync,
    prepare_fg_job_sync,
    run_cpu_prewarm_for_song,
)

logger = logging.getLogger(__name__)


def run_native_inflight_song_pipeline(
    tasks: list[tuple],
    *,
    in_flight_songs: int,
    completed_songs: set[str],
    memory_resume_tracker=None,
    post_queue=None,
    total_tasks: int | None = None,
    stop_requested=None,
    progress_cb=None,
    bundle_completed_cb=None,
) -> None:
    if not tasks:
        return

    cfg0 = first_task_config(tasks)

    icfg = parse_inflight_config(tasks, in_flight_songs=in_flight_songs)

    ga_queue_limit_base = icfg.ga_queue_limit_base
    inflight_fg_hold_slots = icfg.inflight_fg_hold_slots
    fg_hold_budget = icfg.fg_hold_budget

    from gear_optimizer.solver.song_slot_pool import SongSlotPool

    slot_pool = SongSlotPool(max_song_slots=int(icfg.max_song_slots))

    gpu_executor = get_gpu_executor()
    if progress_cb is not None:
        # Make startup visible in the TUI: Taichi/Vulkan init + warmup can take noticeable time on cold caches.
        try:
            progress_cb(completed_delta=0, failed_delta=0, record_info={"status": "GPU init (Taichi/Vulkan)"})
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:run_native_inflight_song_pipeline: {e}")
    gpu_executor.start(in_process=True)
    # GPU readiness includes Taichi/Vulkan init plus the configured GA/FG warmups. On cold
    # Windows/Vulkan caches, that warmup can be minute-scale; do not let work queue behind an
    # owner that is not accepting requests yet.
    init_timeout = float(icfg.runtime.gpu_executor_init_timeout_sec)
    if not gpu_executor.wait_until_ready(timeout=init_timeout):
        err = getattr(gpu_executor, "last_init_error", None)
        msg = "[InFlight] GPU executor Taichi init failed or timed out"
        if err:
            msg = f"{msg} ({err})"
        try:
            gpu_executor.stop()
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:run_native_inflight_song_pipeline: {e}")
        raise RuntimeError(msg)
    if progress_cb is not None:
        # Executor is initialized and warm; requests submitted after this point can be processed.
        try:
            progress_cb(completed_delta=0, failed_delta=0, record_info={"status": "GPU warmup (Taichi JIT)"})
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:run_native_inflight_song_pipeline: {e}")
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)

    stage_profiler = InFlightStageProfiler(enabled=icfg.stage_profile_enabled, out_path=icfg.stage_profile_path)

    post_sender = PostSender(post_queue, stop_requested=stop_requested) if post_queue is not None else None
    fg_decision_debug = icfg.fg_decision_debug
    fg_submit_debug = icfg.fg_submit_debug

    # Progress UI "New" counter should reflect *session-best* improvements, not the stale DB snapshot
    # that in-flight tasks can start with (DB persistence is async, and many repeats can overlap).
    progress_tracker = ProgressTracker()

    def _emit_progress(*, completed_delta: int = 0, failed_delta: int = 0, record_info: dict | None = None) -> None:
        progress_tracker.emit_progress(
            progress_cb,
            completed_delta=completed_delta,
            failed_delta=failed_delta,
            record_info=record_info,
        )

    def _post(item: dict) -> None:
        if post_sender is not None:
            post_sender.send(item)
        progress_tracker.emit_error_item_progress(progress_cb, item)

    pending_tasks = deque(t for t in tasks if task_queue_label(t) not in completed_songs)
    prepared: deque[NativeSong] = deque()
    pending_fg: deque[NativeSong] = deque()
    bundle_tracker = InflightBundleTracker(
        pending_tasks=pending_tasks,
        completed_songs=completed_songs,
        memory_resume_tracker=memory_resume_tracker,
        bundle_completed_cb=bundle_completed_cb,
        emit_progress=_emit_progress,
    )
    _next_logical_task = bundle_tracker.next_logical_task
    _bind_bundle_song = bundle_tracker.bind_song
    _advance_bundle = bundle_tracker.advance

    # GA jobs submitted to the GPU executor (in-order). We intentionally keep a
    # backlog so CPU-side decode/post-processing can't create GPU idle gaps.
    ga_pipeline = InflightGAPipeline()
    ga_inflight = ga_pipeline.inflight

    prep_queue = SongPrepQueue(max_workers=int(icfg.prep_workers), prep_fn=prepare_native_song)
    prep_inflight = prep_queue.inflight

    cpu_prewarm_queue = CpuPrewarmQueue(
        max_workers=int(icfg.cpu_prewarm_workers),
        lookahead=int(icfg.cpu_prewarm_lookahead),
        prewarm_fn=run_cpu_prewarm_for_song,
    )
    cpu_prewarm_inflight = cpu_prewarm_queue.inflight

    decode_queue = GADecodeQueue(max_workers=int(icfg.decode_workers))
    decode_inflight = decode_queue.inflight

    fg_pipeline_settings = native_fg_pipeline.read_native_fg_pipeline_settings(
        cfg0,
        inflight_limit=int(icfg.inflight_limit),
        ga_credit_budget_cfg=int(icfg.fg_ga_credit_budget_cfg),
        cpu_prewarm_lookahead=int(icfg.cpu_prewarm_lookahead),
        default_worker_threads=default_worker_threads,
    )
    fg_pipeline = native_fg_pipeline.NativeFGPipeline(fg_pipeline_settings)
    db_persistence = InflightDBPersistence(prefetch_workers=int(fg_pipeline.settings.db_prefetch_workers))
    pending_fg = fg_pipeline.pending
    fg_prep_inflight = fg_pipeline.prep_inflight
    fg_futures = fg_pipeline.futures
    active_runtime_reporter = ActiveRuntimeProgressReporter(_emit_progress)
    post_emit_pending: deque[NativeSong] = deque()
    fg_workers = int(fg_pipeline.workers)
    fg_batch_max = int(fg_pipeline.batch_max)

    last_slot_block_t: float | None = None
    ga_queue_debug = bool(icfg.runtime.ga_queue_debug)
    last_ga_queue_limit_effective: int | None = None
    completion_tracker = CompletionTracker()
    ga_queue_limit_controller = GAQueueLimitController(
        base_limit=int(ga_queue_limit_base),
        pressure_window_s=float(icfg.ga_queue_pressure_window_s),
        extra_free_on_slot_pressure=int(icfg.ga_queue_extra_free_on_slot_pressure),
        fg_slot_reserve=int(icfg.fg_slot_reserve),
        song_slot_limit=int(icfg.song_slot_limit),
    )
    stop_signal = CachedRuntimeSignal(stop_requested, poll_interval_s=0.05)
    memory_release_signal = CachedRuntimeSignal(memory_release_requested, poll_interval_s=0.05)
    gpu_abort_requester = GpuAbortRequester(gpu_executor)
    lane_fill_hold_count = 0

    def _active_song_lane_count() -> int:
        return count_active_song_lanes(
            ga_inflight=ga_inflight,
            decode_inflight=decode_inflight,
            fg_active_keys=fg_pipeline.active_song_keys(),
        )

    def _submit_fg_static_prewarm(song: NativeSong) -> bool:
        return fg_pipeline.start_static_prep(
            song,
            prepare_fg_static_sync,
            external_song_groups=(ga_inflight, prepared, decode_inflight),
            register_future=completion_tracker.register,
        )

    def _submit_cpu_prewarm_backlog() -> int:
        return cpu_prewarm_queue.submit_prepared_backlog(
            prepared,
            register_future=completion_tracker.register,
            extra_submit=_submit_fg_static_prewarm,
        )

    def _finish_cpu_prewarm_jobs() -> int:
        finished = 0
        for completion in cpu_prewarm_queue.finish_completed():
            finished += 1
            if completion.error is not None:
                # Prewarm is an accelerator only; the dispatch path will rebuild
                # synchronously if the background attempt failed.
                logger.debug(f"native_inflight_orchestrator:_finish_cpu_prewarm_jobs: {completion.error}")
                continue
            stage_profiler.record(
                "cpu_prewarm",
                time.perf_counter() - float(completion.submit_t0),
                cpu_seconds=None,
                song=completion.label,
            )
        return int(finished)

    def _current_ga_queue_limit() -> int:
        return int(
            continuous_ga_warm_queue_limit(
                ga_queue_limit=ga_queue_limit_controller.effective_limit(last_slot_block_t=last_slot_block_t),
                inflight_limit=int(icfg.inflight_limit),
                prepared_count=len(prepared),
                prep_inflight_count=len(prep_inflight),
                decode_inflight_count=len(decode_inflight),
                pending_fg_count=len(pending_fg),
                fg_prep_inflight_count=len(fg_prep_inflight),
                fg_inflight_count=len(fg_futures),
                target_song_lanes=int(icfg.target_song_lanes),
                active_song_lanes=int(_active_song_lane_count()),
                dispatch_burst=int(icfg.continuous_ga_dispatch_burst),
            )
        )

    # Prime the pipeline: pre-prepare a backlog synchronously so the GPU queue
    # doesn't starve on early song boundaries while prep workers spin up.
    #
    # High-end GPUs can burn through the first GA jobs quickly; priming only 1–2 songs
    # can still leave the GPU idle while CPU prep catches up. Default to priming up to
    # a modest 4-8 song backlog on smaller in-flight runs, but allow override via env
    # var/config for experimentation.
    prime_target = read_prime_target(
        cfg0,
        inflight_limit=int(icfg.inflight_limit),
        prep_limit=int(icfg.prep_limit),
        pending_count=len(pending_tasks),
    )
    for _ in range(int(prime_target)):
        first = pending_tasks.popleft()
        song_name = task_song_name(first)
        bundle_key = task_queue_label(first)
        if bundle_key in completed_songs:
            continue
        logical_task, repeat_ctx = _next_logical_task(first)
        task_key = task_queue_label(logical_task)
        try:
            t0 = time.perf_counter()
            prepared_song = prepare_native_song(logical_task)
            _bind_bundle_song(prepared_song, first, repeat_ctx)
            prepared.append(prepared_song)
            stage_profiler.record(
                "prep",
                time.perf_counter() - t0,
                cpu_seconds=getattr(prepared_song.runtime.prep, "cpu_prep_s", None),
                song=task_key,
            )
        except Exception as exc:
            payload = _build_native_task_error_payload(
                song_name=str(song_name),
                queue_key=str(task_key),
                exc=exc,
                trace=traceback.format_exc(),
                suppress_progress=repeat_ctx is not None,
            )
            _post(payload)
            if repeat_ctx is not None:
                _advance_bundle(first, song_name=str(song_name), failed=True)
            else:
                mark_song_completed(
                    completed_songs=completed_songs,
                    task_key=task_key,
                    song_name=song_name,
                    memory_resume_tracker=memory_resume_tracker,
                )

    _submit_cpu_prewarm_backlog()

    def _emit_deferred_post_payload(song: NativeSong) -> None:
        _emit_deferred_post_payload_once(
            song,
            post=_post,
            persist_pending_fg_job=False,
            completed_songs=completed_songs,
            memory_resume_tracker=memory_resume_tracker,
            bundle_completed_cb=bundle_completed_cb,
            advance_bundle=_advance_bundle,
            progress_tracker=progress_tracker,
            progress_cb=progress_cb,
        )

    try:
        last_progress = time.monotonic()
        last_stall_report = last_progress
        last_heartbeat = last_progress
        last_throughput = last_progress
        last_stage_emit = last_progress
        heartbeat_sec = float(icfg.loop_observer.heartbeat_sec)
        throughput_sec = float(icfg.loop_observer.throughput_sec)
        stage_emit_sec = float(icfg.loop_observer.stage_profile_emit_sec)

        event_wait_timeout_s = float(read_inflight_event_wait_timeout_s())
        event_wait_gpu_cap_s = float(read_inflight_event_wait_gpu_cap_s())
        event_wait_short_spin_s = float(read_inflight_event_wait_short_spin_s())

        profile_max_songs = int(icfg.loop_observer.profile_max_songs)
        completed_baseline = 0
        try:
            completed_baseline = int(len(completed_songs))
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:completed_baseline: {e}")
            completed_baseline = 0
        bubble_tracker = BubbleTracker()

        def _bubble_snapshot(now_mono: float, *, oldest_fg_wait_s: float = 0.0) -> dict[str, float | int]:
            return bubble_tracker.snapshot_from_pipeline_counts(
                now_mono=float(now_mono),
                prepared_count=len(prepared),
                ready_fg_count=fg_pipeline.ready_count(),
                active_song_lanes=_active_song_lane_count(),
                pending_tasks_count=len(pending_tasks),
                prep_inflight_count=len(prep_inflight),
                cpu_prewarm_inflight_count=len(cpu_prewarm_inflight),
                decode_inflight_count=len(decode_inflight),
                pending_fg_count=len(pending_fg),
                fg_prep_inflight_count=len(fg_prep_inflight),
                ga_inflight_count=len(ga_inflight),
                fg_futures_count=len(fg_futures),
                last_progress=float(last_progress),
                oldest_fg_wait_s=float(oldest_fg_wait_s),
                lane_fill_hold_count=int(lane_fill_hold_count),
                target_song_lanes=int(icfg.target_song_lanes),
            )

        stopping = False
        while (
            pending_tasks
            or prepared
            or prep_inflight
            or pending_fg
            or post_emit_pending
            or ga_inflight
            or decode_inflight
            or fg_prep_inflight
            or fg_futures
        ):
            now = time.monotonic()
            if memory_release_signal.requested(now):
                break

            # Optional profiling cap: stop after N completed songs/tasks.
            if (not stopping) and profile_max_songs > 0:
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    completed_now = 0
                if completed_now >= int(profile_max_songs):
                    stopping = True
                    try:
                        pending_tasks.clear()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        prepared.clear()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        pending_fg.clear()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

            if stop_signal.requested(now):
                if not stopping:
                    stopping = True
                    gpu_abort_requester.request("native in-flight stop requested")
                    try:
                        pending_tasks.clear()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        prepared.clear()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        pending_fg.clear()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    # Best-effort cancel of queued prep/decode work.
                    try:
                        prep_queue.cancel_all()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        decode_queue.cancel_all()
                        # Keep entries so we can still drain the deque safely.
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

            # Periodic throughput reporting (opt-in via env).
            if throughput_sec > 0 and (now - last_throughput) >= float(throughput_sec):
                last_throughput = now
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    completed_now = 0
                if completed_now > 0:
                    wall_s = max(1e-9, float(time.perf_counter() - float(stage_profiler._t0)))
                    per_h = float(completed_now) * 3600.0 / wall_s
                    try:
                        pending_now = int(len(pending_tasks)) + int(len(prepared)) + int(len(pending_fg))
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        pending_now = 0
                    try:
                        avg_s = wall_s / float(completed_now)
                        eta_s = float(pending_now) * avg_s if pending_now > 0 else 0.0
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        avg_s = 0.0
                        eta_s = 0.0
                    try:
                        logger.debug(
                            "[InFlight][Throughput] done=%s pending~%s rate=%.1f/h avg=%.2fs ETA=%.1fm",
                            completed_now,
                            pending_now,
                            per_h,
                            avg_s,
                            eta_s / 60.0,
                        )
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="throughput",
                        metrics={
                            "completed": int(completed_now),
                            "pending": int(pending_now),
                            "rate_per_hour": float(per_h),
                            "avg_task_sec": float(avg_s),
                            "eta_sec": float(eta_s),
                        },
                    )

            # Periodic stage profile emission (opt-in via env).
            if stage_emit_sec > 0 and stage_profiler.enabled and (now - last_stage_emit) >= float(stage_emit_sec):
                last_stage_emit = now
                try:
                    stage_profiler.emit()
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

            did_work = False
            blocked_on_slot_acquire = False
            if _finish_cpu_prewarm_jobs() > 0:
                did_work = True

            # Move completed song preps into the staging queue.
            for prep_completion in prep_queue.pop_completed():
                task = prep_completion.task
                logical_task = prep_completion.logical_task
                fut = prep_completion.future
                t_submit = prep_completion.submit_t0
                did_work = True
                song_name = task_song_name(task)
                bundle_key = task_queue_label(task)
                task_key = task_queue_label(logical_task)
                if bundle_key in completed_songs:
                    continue
                try:
                    prepared_song = fut.result()
                    repeat_ctx = extract_repeat_context(logical_task)
                    _bind_bundle_song(prepared_song, task, repeat_ctx)
                    stage_profiler.record(
                        "prep",
                        time.perf_counter() - float(t_submit),
                        cpu_seconds=getattr(prepared_song.runtime.prep, "cpu_prep_s", None),
                        song=task_key,
                    )
                    prepared.append(prepared_song)
                    progress_tracker.seed_valid_baseline(
                        prepared_song.config.db_key,
                        best_score=int(getattr(prepared_song.runtime.db, "db_best_score", 0) or 0),
                        best_fg=int(getattr(prepared_song.runtime.db, "db_best_fg_score", 0) or 0),
                        baseline_valid=bool(getattr(prepared_song.runtime.db, "db_baseline_valid", True)),
                    )
                    _submit_cpu_prewarm_backlog()
                except Exception as exc:
                    if stopping and is_stop_abort_exception(exc):
                        continue
                    repeat_ctx = extract_repeat_context(logical_task)
                    payload = _build_native_task_error_payload(
                        song_name=str(song_name),
                        queue_key=str(task_key),
                        exc=exc,
                        trace=traceback.format_exc(),
                        suppress_progress=repeat_ctx is not None,
                    )
                    _post(payload)
                    if repeat_ctx is not None:
                        _advance_bundle(task, song_name=str(song_name), failed=True)
                    else:
                        mark_song_completed(
                            completed_songs=completed_songs,
                            task_key=task_key,
                            song_name=song_name,
                            memory_resume_tracker=memory_resume_tracker,
                        )

            # Finalize prepared FG jobs (CPU prep done) so the GPU stage can start immediately when scheduled.
            for prep_completion in fg_pipeline.finish_completed_prep():
                song = prep_completion.song
                did_work = True
                try:
                    if prep_completion.submit_t0 is not None:
                        stage_profiler.record(
                            "fg_prep",
                            time.perf_counter() - float(prep_completion.submit_t0),
                            cpu_seconds=prep_completion.cpu_seconds,
                            song=song.config.song_name,
                        )
                    if prep_completion.error is None:
                        continue
                    if stopping and is_stop_abort_exception(prep_completion.error):
                        pass
                    else:
                        _post(
                            _build_native_task_error_payload(
                                song_name=str(song.config.song_name),
                                queue_key=str(song.config.task_key),
                                exc=prep_completion.error,
                                trace=prep_completion.trace,
                            )
                        )
                except Exception as exc:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {exc}")

            if pending_fg:
                try:
                    started_fg_prep = fg_pipeline.start_pending_prep(
                        prepare_fg_job_sync,
                        gpu_client=gpu_client,
                        register_future=completion_tracker.register,
                    )
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    started_fg_prep = 0
                if int(started_fg_prep) > 0:
                    did_work = True

            # Keep the GPU queue full while using spare CPU time to prep future songs.
            #
            # - `ga_inflight` bounds the number of submitted GPU-native GA jobs.
            # - `prepared` is a CPU-side staging buffer; keeping it non-empty prevents
            #   starvation if CPU prep briefly falls behind GPU throughput.
            # - We alternate submit/prep to minimize the initial "startup bubble".
            fg_oldest_wait_s = 0.0
            try:
                if pending_fg:
                    fg_oldest_wait_s = fg_pipeline.oldest_wait_s(float(now))
            except Exception as e:
                logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                fg_oldest_wait_s = 0.0

            while True:
                # Submit GA jobs whenever we have prepared work and GPU queue capacity.
                # We allow `ga_inflight` to exceed `icfg.inflight_limit` to create a backlog
                # that keeps the GPU fed while CPU decode/FG prep runs.
                if stopping:
                    break
                ga_queue_limit_effective = _current_ga_queue_limit()
                if ga_queue_debug and ga_queue_limit_effective != last_ga_queue_limit_effective:
                    last_ga_queue_limit_effective = int(ga_queue_limit_effective)
                    try:
                        logger.debug(
                            "[InFlight][GAQueue] effective=%s base=%s ga_inflight=%s prepared=%s pending_fg=%s "
                            "fg_prep=%s fg_inflight=%s slot_reserve=%s oldest_fg_wait_ms=%.0f",
                            int(ga_queue_limit_effective),
                            int(ga_queue_limit_base),
                            len(ga_inflight),
                            len(prepared),
                            len(pending_fg),
                            len(fg_prep_inflight),
                            len(fg_futures),
                            int(icfg.fg_slot_reserve),
                            fg_oldest_wait_s * 1000.0,
                        )
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

                ready_fg_for_ga_admission = fg_pipeline.ready_count() if pending_fg else 0
                if continuous_ga_should_yield_to_fg(
                    pending_fg_count=len(pending_fg),
                    ready_fg_count=int(ready_fg_for_ga_admission),
                    fg_prep_inflight_count=len(fg_prep_inflight),
                    fg_inflight_count=len(fg_futures),
                    fg_worker_count=int(fg_workers),
                    target_song_lanes=int(icfg.target_song_lanes),
                    oldest_wait_s=float(fg_oldest_wait_s),
                    aging_trigger_s=float(icfg.fg_aging_trigger_s),
                    blocked_on_slot=bool(blocked_on_slot_acquire),
                ):
                    break

                can_submit_ga = bool(prepared) and len(ga_inflight) < ga_queue_limit_effective

                if can_submit_ga:
                    song = prepared.popleft()
                    # Reserve a per-song GPU timeline slot so GA -> FG can reuse the resident grid
                    # even while other songs are in-flight (avoids clobbering slot 0).
                    try:
                        ga_pipeline.reserve_slot(song, slot_pool)
                    except Exception as e:
                        # No free slots: defer GA submission until FG drains.
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        blocked_on_slot_acquire = True
                        last_slot_block_t = time.monotonic()
                        stage_profiler.record("slot_block", 0.0)
                        prepared.appendleft(song)
                        break
                    ga_pipeline.prepare_submit(song)
                    payload = ga_pipeline.build_payload(song)
                    try:
                        handle = gpu_client.submit_gpu_native_ga_run(payload)
                    except Exception as exc:
                        # Ensure we don't leak the reserved slot on submission failure.
                        try:
                            ga_pipeline.release_slot(song, slot_pool)
                        except Exception as e:
                            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
                        payload = _build_native_song_error_payload(
                            song,
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                        _post(payload)
                        if bundle_parent is not None:
                            _advance_bundle(bundle_parent, song_name=str(song.config.song_name), failed=True)
                        else:
                            mark_song_completed(
                                completed_songs=completed_songs,
                                task_key=song.config.task_key,
                                song_name=song.config.song_name,
                                memory_resume_tracker=memory_resume_tracker,
                            )
                        did_work = True
                        continue

                    ga_pipeline.track_submitted(
                        song,
                        handle.future,
                        register_future=completion_tracker.register,
                    )
                    did_work = True
                    fg_pipeline.note_ga_submit()
                    if _submit_cpu_prewarm_backlog() > 0:
                        did_work = True

                    # Prefetch DB loadouts early so FG prep after GA decode doesn't stall
                    # waiting on SQLite reads (keeps the GPU fed during song boundaries).
                    db_persistence.maybe_submit_prefetch(
                        song,
                        prefetch_db_loadouts_sync,
                        register_future=completion_tracker.register,
                    )

                    if _submit_fg_static_prewarm(song):
                        did_work = True

                    continue

                # CPU prep: keep a staging buffer of prepared jobs so the GPU queue
                # doesn't starve if CPU prep briefly falls behind GPU throughput.
                if stopping:
                    break
                if pending_tasks and (len(prepared) + len(prep_inflight) < icfg.prep_limit):
                    nxt = pending_tasks.popleft()
                    nxt_bundle_key = task_queue_label(nxt)
                    if nxt_bundle_key in completed_songs:
                        did_work = True
                        continue
                    logical_nxt, repeat_ctx = _next_logical_task(nxt)
                    nxt_key = task_queue_label(logical_nxt)
                    try:
                        prep_queue.submit(
                            nxt,
                            logical_nxt,
                            register_future=completion_tracker.register,
                        )
                    except Exception as exc:
                        payload = _build_native_task_error_payload(
                            song_name=task_song_name(nxt),
                            queue_key=str(nxt_key),
                            exc=exc,
                            trace=traceback.format_exc(),
                            suppress_progress=repeat_ctx is not None,
                        )
                        _post(payload)
                        if repeat_ctx is not None:
                            _advance_bundle(nxt, song_name=task_song_name(nxt), failed=True)
                        else:
                            mark_song_completed(
                                completed_songs=completed_songs,
                                task_key=nxt_key,
                                song_name=task_song_name(nxt),
                                memory_resume_tracker=memory_resume_tracker,
                            )
                        did_work = True
                        continue
                    did_work = True
                    continue

                break

            # Drain completed GA jobs quickly to free inflight capacity; do the heavier
            # CPU-side decode on a background thread so the GPU queue stays fed.
            for ga_completion in ga_pipeline.pop_completed_runs():
                song = ga_completion.song
                ga_future = ga_completion.future
                did_work = True

                try:
                    ga_result = ga_future.result()
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
                    if not (stopping and is_stop_abort_exception(exc)):
                        _post(
                            _build_native_song_error_payload(
                                song,
                                exc=exc,
                                trace=traceback.format_exc(),
                            )
                        )
                    # GA failed: release the reserved timeline slot for this song.
                    try:
                        ga_pipeline.release_slot(song, slot_pool)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    if stopping and is_stop_abort_exception(exc):
                        continue
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.config.song_name), failed=True)
                    else:
                        mark_song_completed(
                            completed_songs=completed_songs,
                            task_key=song.config.task_key,
                            song_name=song.config.song_name,
                            memory_resume_tracker=memory_resume_tracker,
                        )
                    continue

                t_submit = getattr(song.runtime.ga, "ga_submit_t0", None)
                if t_submit is not None:
                    stage_profiler.record("ga_gpu", time.perf_counter() - float(t_submit), song=song.config.task_key)
                    song.runtime.ga.ga_submit_t0 = None

                song.runtime.ga.ga_future = None

                needs_fg_stage = True
                hold_budget = int(fg_hold_budget or 0)
                keep_slot_for_fg = False
                if inflight_fg_hold_slots and needs_fg_stage and hold_budget > 0:
                    held_slots = 0
                    try:
                        for s in decode_inflight:
                            if int(getattr(s.runtime, "song_slot", 0) or 0) <= 0:
                                continue
                            held_slots += 1
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        for s in pending_fg:
                            if int(getattr(s.runtime, "song_slot", 0) or 0) > 0:
                                held_slots += 1
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        for fg_song, _fut, _t_submit in fg_futures:
                            if int(getattr(fg_song.runtime, "song_slot", 0) or 0) > 0:
                                held_slots += 1
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    keep_slot_for_fg = int(held_slots) < int(hold_budget)

                if not keep_slot_for_fg:
                    # Release the song slot immediately after GA completes unless we're keeping it
                    # resident for FG reuse (bounded by `fg_hold_budget` so GA won't deadlock on slots).
                    if inflight_fg_hold_slots and needs_fg_stage and hold_budget > 0:
                        stage_profiler.record("fg_hold_drop", 0.0)
                    try:
                        ga_pipeline.release_slot(song, slot_pool)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

                decode_queue.submit(
                    song,
                    ga_result,
                    decode_ga_payload_sync,
                    register_future=completion_tracker.register,
                )
                try:
                    emit_profile_event(
                        component="inflight_decode",
                        event="submit",
                        song_key=str(song.config.task_key),
                        metrics={"song_slot": int(getattr(song.runtime, "song_slot", 0) or 0)},
                    )
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

            # Finalize decoded GA results (lightweight formatting + enqueue for post/FG).
            for decode_completion in decode_queue.pop_completed():
                song = decode_completion.song
                decode_future = decode_completion.future
                did_work = True

                try:
                    decode_result = decode_future.result()
                except Exception as exc:
                    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
                    if not (stopping and is_stop_abort_exception(exc)):
                        _post(
                            _build_native_song_error_payload(
                                song,
                                exc=exc,
                                trace=traceback.format_exc(),
                            )
                        )
                    # Decode failed: release the reserved timeline slot for this song.
                    try:
                        ga_pipeline.release_slot(song, slot_pool)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    if stopping and is_stop_abort_exception(exc):
                        continue
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.config.song_name), failed=True)
                    else:
                        mark_song_completed(
                            completed_songs=completed_songs,
                            task_key=song.config.task_key,
                            song_name=song.config.song_name,
                            memory_resume_tracker=memory_resume_tracker,
                        )
                    continue
                finally:
                    song.runtime.decode.decode_future = None

                t_decode = decode_completion.submit_t0
                if t_decode is not None:
                    stage_profiler.record(
                        "decode",
                        time.perf_counter() - float(t_decode),
                        cpu_seconds=getattr(song.runtime.decode, "cpu_decode_s", None),
                        song=song.config.task_key,
                    )
                    song.runtime.decode.decode_submit_t0 = None

                ga_pipeline.store_decode_result(song, decode_result)
                try:
                    emit_profile_event(
                        component="inflight_decode",
                        event="consume",
                        song_key=str(song.config.task_key),
                        metrics={
                            "song_slot": int(getattr(song.runtime, "song_slot", 0) or 0),
                            "ga_candidates": int(len(song.runtime.decode.ga_candidates or [])),
                        },
                    )
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

                fg_t0 = time.perf_counter()
                try:
                    native_fg_pipeline.score_fg_inside_ga(song, gpu_client=gpu_client)
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
                    _post(
                        _build_native_song_error_payload(
                            song,
                            exc=exc,
                            trace=traceback.format_exc(),
                        )
                    )
                    try:
                        ga_pipeline.release_slot(song, slot_pool)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    if stopping and is_stop_abort_exception(exc):
                        continue
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.config.song_name), failed=True)
                    else:
                        mark_song_completed(
                            completed_songs=completed_songs,
                            task_key=song.config.task_key,
                            song_name=song.config.song_name,
                            memory_resume_tracker=memory_resume_tracker,
                        )
                    continue
                stage_profiler.record(
                    "fg_run",
                    time.perf_counter() - float(fg_t0),
                    cpu_seconds=getattr(song.runtime.fg, "cpu_fg_run_s", None),
                    song=song.config.task_key,
                )

                # GA and its native FG scoring now share one result authority; release
                # the resident timeline slot only after that combined result exists.
                try:
                    ga_pipeline.release_slot(song, slot_pool)
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

                record_info = None
                try:
                    record_info = progress_tracker.evaluate_record_update(
                        song.config.db_key,
                        song.runtime.decode.best_data or {},
                        getattr(song.runtime.fg, "fg_variants", None) or [],
                    )
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    record_info = None
                song.runtime.db.record_info = record_info
                try:
                    song.runtime.post.deferred_post_emitted = False
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                post_emit_pending.append(song)

            # Reap completed FG workers (capture errors).
            for fg_completion in fg_pipeline.pop_completed_jobs():
                fg_song = fg_completion.song
                fut = fg_completion.future
                t_submit = fg_completion.submit_t0
                did_work = True
                fg_failed = False
                try:
                    fut.result()
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    if stopping and is_stop_abort_exception(exc):
                        fg_failed = False
                    else:
                        fg_failed = True
                        try:
                            emit_profile_event(
                                component="inflight_fg_worker",
                                event="dispatch_error",
                                song_key=str(
                                    getattr(fg_song.config, "task_key", "")
                                    or getattr(fg_song.config, "song_name", "")
                                    or ""
                                ),
                                metrics={
                                    "exc_type": type(exc).__name__,
                                    "exc": str(exc),
                                },
                            )
                        except Exception as e:
                            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        try:
                            logger.exception("[NativeInflight][FG] worker failed for %s", fg_song.config.task_key)
                        except Exception as e:
                            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                if not bool(getattr(fg_song.runtime.post, "deferred_post_emitted", False)):
                    try:
                        _emit_deferred_post_payload(fg_song)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                if fg_failed:
                    try:
                        if post_sender is not None and bool(getattr(fg_song.runtime.bundle, "bundle_wait_for_fg", False)):
                            post_sender.send(_build_failed_fg_update_payload(fg_song))
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                # Release this song's reserved timeline slot now that FG is complete.
                try:
                    ga_pipeline.release_slot(fg_song, slot_pool)
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                stage_profiler.record(
                    "fg_run",
                    time.perf_counter() - float(t_submit),
                    cpu_seconds=getattr(fg_song.runtime.fg, "cpu_fg_run_s", None),
                    song=fg_song.config.task_key,
                )
                finish_deferred_fg_completion(
                    fg_song,
                    fg_failed=bool(fg_failed),
                    completed_songs=completed_songs,
                    memory_resume_tracker=memory_resume_tracker,
                    bundle_completed_cb=bundle_completed_cb,
                    advance_bundle=_advance_bundle,
                    progress_tracker=progress_tracker,
                    progress_cb=progress_cb,
                )

            fg_oldest_wait_s = 0.0
            try:
                if pending_fg:
                    fg_oldest_wait_s = fg_pipeline.oldest_wait_s(float(now))
            except Exception as e:
                logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                fg_oldest_wait_s = 0.0
            ready_fg_count = fg_pipeline.ready_count()
            bubble_snapshot = _bubble_snapshot(float(now), oldest_fg_wait_s=float(fg_oldest_wait_s))
            bubble_tracker.note(
                bubble_snapshot,
                now_mono=float(now),
                oldest_fg_wait_s=float(fg_oldest_wait_s),
            )

            if not pending_fg:
                fg_pipeline.reset_credit_if_empty()

            no_ga_remaining = (
                (not pending_tasks)
                and (not prepared)
                and (not prep_inflight)
                and (not ga_inflight)
                and (not decode_inflight)
            )

            ga_queue_limit_effective = _current_ga_queue_limit()
            ready_ga_for_lane_fill = len(prepared) if len(ga_inflight) < int(ga_queue_limit_effective) else 0
            if continuous_fg_should_fill_song_lanes(
                target_song_lanes=int(icfg.target_song_lanes),
                active_song_lanes=int(_active_song_lane_count()),
                ready_ga_count=int(ready_ga_for_lane_fill),
                pending_fg_count=len(pending_fg),
                ready_fg_count=int(ready_fg_count),
                blocked_on_slot=bool(blocked_on_slot_acquire),
                no_ga_remaining=bool(no_ga_remaining),
                oldest_wait_s=float(fg_oldest_wait_s),
                aging_trigger_s=float(icfg.fg_aging_trigger_s),
                aging_hard_s=float(icfg.fg_aging_hard_s),
            ):
                lane_fill_hold_count += 1
                should_start_fg = False
            else:
                should_start_fg = continuous_fg_should_start(
                    pending_fg_count=len(pending_fg),
                    ready_fg_count=int(ready_fg_count),
                    ga_credit=int(fg_pipeline.ga_credit),
                    oldest_wait_s=float(fg_oldest_wait_s),
                    blocked_on_slot=bool(blocked_on_slot_acquire),
                    no_ga_remaining=bool(no_ga_remaining),
                    aging_trigger_s=float(icfg.fg_aging_trigger_s),
                    aging_hard_s=float(icfg.fg_aging_hard_s),
                    ga_queue_limit=int(ga_queue_limit_effective),
                    fg_slot_reserve=int(icfg.fg_slot_reserve),
                )

            if should_start_fg:
                if fg_decision_debug:
                    try:
                        reasons: list[str] = []
                        if no_ga_remaining:
                            reasons.append("drain_end")
                        if blocked_on_slot_acquire:
                            reasons.append("slot_pressure")
                        if (
                            int(icfg.fg_slot_reserve) > 0
                            and int(ready_fg_count) > 0
                            and len(ga_inflight) >= max(1, int(ga_queue_limit_effective))
                        ):
                            reasons.append("reserve_ready")
                        if fg_oldest_wait_s >= float(icfg.fg_aging_hard_s) and float(icfg.fg_aging_hard_s) > 0.0:
                            reasons.append("aging_hard")
                        elif fg_oldest_wait_s >= float(icfg.fg_aging_trigger_s) and float(icfg.fg_aging_trigger_s) > 0.0:
                            reasons.append("aging_trigger")
                        if int(fg_pipeline.ga_credit) <= 0:
                            reasons.append("credit")

                        logger.debug(
                            "[InFlight][FGDecision] start reasons=%s pending=%s prepared=%s prep_inflight=%s "
                            "ga_inflight=%s decode_inflight=%s pending_fg=%s fg_prep=%s fg_inflight=%s "
                            "oldest_fg_wait_ms=%.0f",
                            ",".join(reasons) or "unknown",
                            len(pending_tasks),
                            len(prepared),
                            len(prep_inflight),
                            len(ga_inflight),
                            len(decode_inflight),
                            len(pending_fg),
                            len(fg_prep_inflight),
                            len(fg_futures),
                            fg_oldest_wait_s * 1000.0,
                        )
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")

                submit_budget = continuous_fg_submit_budget(
                    pending_fg_count=len(pending_fg),
                    ready_fg_count=int(ready_fg_count),
                    fg_inflight_count=len(fg_futures),
                    fg_workers=int(fg_workers),
                    fg_batch_max=int(fg_batch_max),
                    no_ga_remaining=bool(no_ga_remaining),
                    blocked_on_slot=bool(blocked_on_slot_acquire),
                    oldest_wait_s=float(fg_oldest_wait_s),
                    aging_trigger_s=float(icfg.fg_aging_trigger_s),
                    aging_hard_s=float(icfg.fg_aging_hard_s),
                    ga_queue_limit=int(ga_queue_limit_effective),
                    adaptive_max_burst=int(icfg.fg_adaptive_submit_max_burst),
                    fg_slot_reserve=int(icfg.fg_slot_reserve),
                )

                if submit_budget > 0 and len(fg_futures) < fg_workers:
                    # Process pending FG jobs (up to worker + batch budget).
                    while submit_budget > 0 and len(fg_futures) < fg_workers and pending_fg:
                        allow_not_ready = continuous_fg_allow_not_ready(
                            blocked_on_slot=bool(blocked_on_slot_acquire),
                            no_ga_remaining=bool(no_ga_remaining),
                        )
                        if allow_not_ready and fg_pipeline.has_active_prep():
                            allow_not_ready = False
                        fg_song = fg_pipeline.pop_next(allow_not_ready=allow_not_ready)
                        if fg_song is None:
                            break
                        if int(getattr(fg_song.runtime, "song_slot", 0) or 0) <= 0:
                            try:
                                ga_pipeline.reserve_slot(fg_song, slot_pool)
                            except Exception as e:
                                # No free slots: put the song back and defer FG submission
                                # until GA releases slots. Without this, the song would be
                                # dropped from FG processing entirely (it was removed from
                                # pending_fg by the FG pipeline pop but never submitted).
                                logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                                fg_pipeline.requeue_front(fg_song)
                                break
                        if fg_submit_debug:
                            try:
                                logger.debug(
                                    "[InFlight][FGSubmit] song=%s pending_fg=%s fg_inflight=%s",
                                    fg_song.config.task_key,
                                    len(pending_fg),
                                    len(fg_futures),
                                )
                            except Exception as e:
                                logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        try:
                            fg_song.runtime.fg.fg_queued_t0 = None
                        except Exception as e:
                            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        fg_pipeline.submit_job(
                            native_fg_pipeline.run_fg_job_sync,
                            fg_song,
                            gpu_client=gpu_client,
                            post_sender=post_sender,
                            progress_cb=progress_cb,
                            progress_tracker=progress_tracker,
                            register_future=completion_tracker.register,
                        )
                        did_work = True
                        submit_budget -= 1

            if post_emit_pending:
                post_emit_budget = 1
                if not (
                    pending_tasks
                    or prepared
                    or prep_inflight
                    or ga_inflight
                    or decode_inflight
                    or pending_fg
                    or fg_prep_inflight
                    or fg_futures
                ):
                    post_emit_budget = int(len(post_emit_pending))
                while post_emit_budget > 0 and post_emit_pending:
                    post_song = post_emit_pending.popleft()
                    if bool(getattr(post_song.runtime.post, "deferred_post_emitted", False)):
                        continue
                    _emit_deferred_post_payload(post_song)
                    did_work = True
                    post_emit_budget -= 1

            active_runtime_reporter.emit(
                ga_inflight=ga_inflight,
                decode_inflight=decode_inflight,
                fg_futures=fg_futures,
            )

            if did_work:
                last_progress = time.monotonic()

            # Avoid tight spin.
            if not did_work:
                if heartbeat_sec > 0.0 and (time.monotonic() - last_heartbeat) >= heartbeat_sec:
                    last_heartbeat = time.monotonic()
                    heartbeat_bubble = _bubble_snapshot(float(last_heartbeat), oldest_fg_wait_s=float(fg_oldest_wait_s))
                    oldest_ga_s = None
                    try:
                        now = time.perf_counter()
                        t0s = [getattr(s.runtime.ga, "ga_submit_t0", None) for s in ga_inflight]
                        t0s = [t for t in t0s if t is not None]
                        if t0s:
                            oldest_ga_s = max(0.0, now - float(min(t0s)))
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        oldest_ga_s = None

                    try:
                        msg = (
                            "[InFlight][HB] "
                            f"idle={time.monotonic() - last_progress:.1f}s "
                            f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                            f"cpu_prewarm={len(cpu_prewarm_inflight)} "
                            f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                            f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)} "
                            f"lanes={int(heartbeat_bubble.get('active_song_lanes', 0) or 0)}/{int(icfg.target_song_lanes)} "
                            f"lane_holds={int(lane_fill_hold_count)}"
                        )
                        if blocked_on_slot_acquire:
                            msg += " blocked_slots=1"
                        if oldest_ga_s is not None:
                            msg += f" oldest_ga={oldest_ga_s:.1f}s"
                        if float(heartbeat_bubble.get("bubble_kpi", 0.0) or 0.0) > 0.0:
                            msg += (
                                f" bubble_kpi={float(heartbeat_bubble.get('bubble_kpi', 0.0)):.2f}"
                                f" ready_ga={int(heartbeat_bubble.get('ready_ga_count', 0) or 0)}"
                                f" ready_fg={int(heartbeat_bubble.get('ready_fg_count', 0) or 0)}"
                            )
                        logger.debug(msg)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="heartbeat",
                        metrics={
                            "idle_sec": float(time.monotonic() - last_progress),
                            "pending_tasks": int(len(pending_tasks)),
                            "prepared": int(len(prepared)),
                            "prep_inflight": int(len(prep_inflight)),
                            "cpu_prewarm_inflight": int(len(cpu_prewarm_inflight)),
                            "ga_inflight": int(len(ga_inflight)),
                            "decode_inflight": int(len(decode_inflight)),
                            "pending_fg": int(len(pending_fg)),
                            "fg_prep_inflight": int(len(fg_prep_inflight)),
                            "fg_futures": int(len(fg_futures)),
                            "blocked_slots": int(bool(blocked_on_slot_acquire)),
                            "oldest_ga_sec": float(oldest_ga_s) if oldest_ga_s is not None else -1.0,
                            "bubble_kpi": float(heartbeat_bubble.get("bubble_kpi", 0.0) or 0.0),
                            "bubble_ready_ga": int(heartbeat_bubble.get("ready_ga_count", 0) or 0),
                            "bubble_ready_fg": int(heartbeat_bubble.get("ready_fg_count", 0) or 0),
                            "active_song_lanes": int(heartbeat_bubble.get("active_song_lanes", 0) or 0),
                            "icfg.target_song_lanes": int(icfg.target_song_lanes),
                            "lane_fill_holds": int(lane_fill_hold_count),
                            "bubble_backlog": int(heartbeat_bubble.get("backlog_count", 0) or 0),
                            "bubble_oldest_fg_wait_sec": float(fg_oldest_wait_s),
                        },
                    )

                no_active_work = (
                    (not ga_inflight)
                    and (not decode_inflight)
                    and (not prep_inflight)
                    and (not cpu_prewarm_inflight)
                    and (not fg_prep_inflight)
                    and (not fg_futures)
                )
                if (
                    no_active_work
                    and (pending_tasks or prepared or pending_fg or fg_futures or post_emit_pending)
                    and (time.monotonic() - last_stall_report) >= 10.0
                    and inflight_stall_debug_enabled()
                ):
                    last_stall_report = time.monotonic()
                    try:
                        fg_done = sum(1 for _song, fut, _t0 in fg_futures if fut.done())
                        fg_inflight = len(fg_futures)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        fg_done = None
                        fg_inflight = None
                    logger.debug(
                        "[InFlight][STALL] pending=%s prepared=%s prep_inflight=%s ga_inflight=%s "
                        "cpu_prewarm=%s decode_inflight=%s pending_fg=%s fg_prep=%s fg_inflight=%s fg_done=%s",
                        len(pending_tasks),
                        len(prepared),
                        len(prep_inflight),
                        len(ga_inflight),
                        len(cpu_prewarm_inflight),
                        len(decode_inflight),
                        len(pending_fg),
                        len(fg_prep_inflight),
                        fg_inflight,
                        fg_done,
                    )
                    emit_profile_event(
                        component="inflight_orchestrator",
                        event="stall",
                        metrics={
                            "pending_tasks": int(len(pending_tasks)),
                            "prepared": int(len(prepared)),
                            "prep_inflight": int(len(prep_inflight)),
                            "cpu_prewarm_inflight": int(len(cpu_prewarm_inflight)),
                            "ga_inflight": int(len(ga_inflight)),
                            "decode_inflight": int(len(decode_inflight)),
                            "pending_fg": int(len(pending_fg)),
                            "fg_prep_inflight": int(len(fg_prep_inflight)),
                            "fg_inflight": int(fg_inflight) if fg_inflight is not None else -1,
                            "fg_done": int(fg_done) if fg_done is not None else -1,
                            "bubble_kpi": float(bubble_snapshot.get("bubble_kpi", 0.0) or 0.0),
                            "bubble_ready_ga": int(bubble_snapshot.get("ready_ga_count", 0) or 0),
                            "bubble_ready_fg": int(bubble_snapshot.get("ready_fg_count", 0) or 0),
                            "active_song_lanes": int(bubble_snapshot.get("active_song_lanes", 0) or 0),
                            "icfg.target_song_lanes": int(icfg.target_song_lanes),
                            "lane_fill_holds": int(lane_fill_hold_count),
                            "bubble_backlog": int(bubble_snapshot.get("backlog_count", 0) or 0),
                            "bubble_oldest_fg_wait_sec": float(fg_oldest_wait_s),
                        },
                    )

                if has_waitable_work(
                    ga_inflight,
                    prep_inflight,
                    cpu_prewarm_inflight,
                    decode_inflight,
                    fg_prep_inflight,
                    fg_futures,
                    pending_fg=pending_fg,
                ):
                    t_wait = time.perf_counter()
                    has_gpu = bool(ga_inflight) or bool(fg_futures)
                    has_cpu = (
                        bool(prep_inflight)
                        or bool(cpu_prewarm_inflight)
                        or bool(decode_inflight)
                        or bool(fg_prep_inflight)
                    )
                    signaled = bool(completion_tracker.is_set())
                    if signaled:
                        completion_tracker.clear()
                    if not signaled:
                        wait_timeout_s = float(event_wait_timeout_s)
                        if has_gpu and float(event_wait_gpu_cap_s) > 0.0:
                            wait_timeout_s = min(float(wait_timeout_s), float(event_wait_gpu_cap_s))
                        signaled = completion_tracker.wait(
                            timeout_s=float(wait_timeout_s),
                            short_spin_s=float(event_wait_short_spin_s),
                        )
                        if signaled:
                            completion_tracker.clear()
                    dt_wait = time.perf_counter() - t_wait
                    stage_profiler.record("main_wait", dt_wait)
                    if (not has_gpu) and has_cpu:
                        stage_profiler.record("underfed_wait", dt_wait)
                else:
                    t_sleep = time.perf_counter()
                    time.sleep(0.001)
                    stage_profiler.record("main_sleep", time.perf_counter() - t_sleep)

    except Exception as exc:
        log_native_abort(
            exc,
            pending_tasks=len(pending_tasks),
            prepared=len(prepared),
            prep_inflight=len(prep_inflight),
            ga_inflight=len(ga_inflight),
            decode_inflight=len(decode_inflight),
            pending_fg=len(pending_fg),
            fg_prep=len(fg_prep_inflight),
            fg_futures=len(fg_futures),
            trace=traceback.format_exc(),
        )
        raise
    finally:
        try:
            now_mono = time.monotonic()
            bubble_tracker.finish_active(now_mono=float(now_mono))
            bubble_metrics = bubble_tracker.summary(
                active_song_lanes=int(_active_song_lane_count()),
                target_song_lanes=int(icfg.target_song_lanes),
            )
            bubble_metrics["lane_fill_holds"] = int(lane_fill_hold_count)
            emit_profile_event(
                component="inflight_orchestrator",
                event="bubble_summary",
                metrics=bubble_metrics,
            )
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            stage_profiler.emit()
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        shutdown_debug = inflight_shutdown_debug_enabled()
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] fg_executor.shutdown")
            fg_pipeline.shutdown_fg(wait=True, cancel_futures=True)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] decode_executor.shutdown")
            decode_queue.shutdown(wait=True, cancel_futures=True)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] db_prefetch_executor.shutdown")
            db_persistence.shutdown_prefetch(wait=True, cancel_futures=True)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] fg_prep_executor.shutdown")
            fg_pipeline.shutdown_prep(wait=True, cancel_futures=True)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] cpu_prewarm_executor.shutdown")
            cpu_prewarm_queue.shutdown(wait=True, cancel_futures=True)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] prep_executor.shutdown")
            prep_queue.shutdown(wait=True, cancel_futures=True)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if post_sender is not None:
                if shutdown_debug:
                    logger.debug("[InFlight][SHUTDOWN] post_sender.close")
                post_sender.close(timeout=10.0)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if shutdown_debug:
                logger.debug("[InFlight][SHUTDOWN] gpu_client.close")
            gpu_client.close(timeout=2.0)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
        try:
            if gpu_executor.is_running:
                if shutdown_debug:
                    logger.debug("[InFlight][SHUTDOWN] gpu_executor.stop")
                gpu_executor.stop()
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")


# NOTE: `decode_ga_payload_sync`, `prefetch_db_loadouts_sync`, and `prepare_fg_job_sync`
# are imported from their own modules to keep the orchestrator leaner.
