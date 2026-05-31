"""
GPU-native in-flight multi-song orchestrator (single process, single GPU owner thread).
This pipeline is designed to keep the GPU continuously busy in native GA mode by:
- Preparing the next songs' CPU-only data while the GPU runs the current song.
- Executing GPU-native GA on the Taichi/Vulkan owner thread (GpuExecutor) via an in-process
  request queue (no per-song process overhead, minimal transfers).
- Scheduling ForceGreats response-frontier work via continuous credit-based interleaving,
  with CPU grouping/prep performed off the GPU thread and GPU kernels submitted via the executor.
"""
from __future__ import annotations
import logging
import time
import traceback
import concurrent.futures
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.domain.jobs import extract_repeat_context, task_queue_label, task_song_name
from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError
from gear_optimizer.solver.native_inflight_config import (
    default_worker_threads,
    first_task_config,
    inflight_stall_debug_enabled,
    parse_inflight_config,
)
from gear_optimizer.solver.inflight_wait import (
    read_inflight_event_wait_timeout_s,
    read_inflight_event_wait_gpu_cap_s,
    read_inflight_event_wait_short_spin_s,
    wait_for_completion_event,
)
from gear_optimizer.solver.native_inflight_lifecycle import prepare_native_song
from gear_optimizer.solver.native_inflight_lifecycle import (
    GAQueueLimitController,
    continuous_fg_allow_not_ready,
    continuous_fg_prep_start_budget,
    continuous_ga_should_yield_to_fg,
    continuous_fg_should_fill_song_lanes,
    continuous_fg_should_start,
    continuous_fg_submit_budget,
    continuous_ga_warm_queue_limit,
    count_active_song_lanes,
    read_prime_target,
)
from gear_optimizer.solver import native_inflight_pipeline as native_fg_pipeline
from gear_optimizer.solver.native_inflight_pipeline import GADecodeQueue, InflightGAPipeline
from gear_optimizer.solver.native_inflight_lifecycle import (
    BubbleTracker,
    CachedRuntimeSignal,
    CpuPrewarmQueue,
    GpuAbortRequester,
    InflightBundleTracker,
    PostSender,
    SongPrepQueue,
    is_stop_abort_exception,
    log_native_abort,
    prime_native_inflight_prepared_queue,
    shutdown_native_inflight_resources,
    start_native_inflight_gpu_client,
)
from gear_optimizer.solver.native_inflight_lifecycle import ActiveRuntimeProgressReporter, ProgressTracker
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_pipeline import (
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
    gpu_executor, gpu_client = start_native_inflight_gpu_client(icfg, progress_cb=progress_cb)
    stage_profiler = InFlightStageProfiler(enabled=icfg.stage_profile_enabled, out_path=icfg.stage_profile_path)
    post_sender = PostSender(post_queue, stop_requested=stop_requested) if post_queue is not None else None
    fg_decision_debug = icfg.fg_decision_debug
    fg_submit_debug = icfg.fg_submit_debug
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
    def _active_ga_gpu_count() -> int:
        return int(ga_pipeline.active_count())
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
    prime_target = read_prime_target(
        cfg0,
        inflight_limit=int(icfg.inflight_limit),
        prep_limit=int(icfg.prep_limit),
        pending_count=len(pending_tasks),
    )
    prime_native_inflight_prepared_queue(
        prime_target=int(prime_target),
        pending_tasks=pending_tasks,
        prepared=prepared,
        completed_songs=completed_songs,
        next_logical_task=_next_logical_task,
        bind_bundle_song=_bind_bundle_song,
        prepare_song=prepare_native_song,
        post=_post,
        advance_bundle=_advance_bundle,
        stage_profiler=stage_profiler,
        memory_resume_tracker=memory_resume_tracker,
    )
    _submit_cpu_prewarm_backlog()
    def _emit_deferred_post_payload(song: NativeSong) -> None:
        emit_deferred_post_payload(
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
        completed_baseline = len(completed_songs)
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
            if (not stopping) and profile_max_songs > 0:
                completed_now = len(completed_songs) - int(completed_baseline)
                if completed_now >= int(profile_max_songs):
                    stopping = True
                    pending_tasks.clear()
                    prepared.clear()
                    pending_fg.clear()
            if stop_signal.requested(now):
                if not stopping:
                    stopping = True
                    gpu_abort_requester.request("native in-flight stop requested")
                    pending_tasks.clear()
                    prepared.clear()
                    pending_fg.clear()
                    try:
                        prep_queue.cancel_all()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    try:
                        decode_queue.cancel_all()
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
            if throughput_sec > 0 and (now - last_throughput) >= float(throughput_sec):
                last_throughput = now
                completed_now = len(completed_songs) - int(completed_baseline)
                if completed_now > 0:
                    wall_s = max(1e-9, float(time.perf_counter() - float(stage_profiler._t0)))
                    per_h = float(completed_now) * 3600.0 / wall_s
                    pending_now = len(pending_tasks) + len(prepared) + len(pending_fg)
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
                    payload = build_native_task_error_payload(
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
            for prep_completion in fg_pipeline.finish_completed_prep():
                song = prep_completion.song
                did_work = True
                try:
                    if prep_completion.submit_t0 is not None:
                        fg_prep_elapsed_s = time.perf_counter() - float(prep_completion.submit_t0)
                        fg_prep_wall_s = float(getattr(song.runtime.fg, "fg_prep_wall_s", 0.0) or 0.0)
                        if fg_prep_wall_s <= 0.0 or fg_prep_wall_s > fg_prep_elapsed_s:
                            fg_prep_wall_s = float(fg_prep_elapsed_s)
                        fg_prep_queue_s = max(0.0, float(fg_prep_elapsed_s) - float(fg_prep_wall_s))
                        if fg_prep_queue_s > 0.0:
                            stage_profiler.record("fg_prep_queue", fg_prep_queue_s, song=song.config.song_name)
                        stage_profiler.record(
                            "fg_prep",
                            fg_prep_wall_s,
                            cpu_seconds=prep_completion.cpu_seconds,
                            song=song.config.song_name,
                        )
                    if prep_completion.error is None:
                        continue
                    if stopping and is_stop_abort_exception(prep_completion.error):
                        pass
                    else:
                        _post(
                            build_native_task_error_payload(
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
                    fg_prep_start_budget = continuous_fg_prep_start_budget(
                        pending_fg_count=len(pending_fg),
                        fg_prep_inflight_count=len(fg_prep_inflight),
                        target_song_lanes=int(icfg.target_song_lanes),
                    )
                    started_fg_prep = fg_pipeline.start_pending_prep(
                        prepare_fg_job_sync,
                        gpu_client=gpu_client,
                        max_new=int(fg_prep_start_budget),
                        register_future=completion_tracker.register,
                    )
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    started_fg_prep = 0
                if int(started_fg_prep) > 0:
                    did_work = True
            fg_oldest_wait_s = 0.0
            try:
                if pending_fg:
                    fg_oldest_wait_s = fg_pipeline.oldest_wait_s(float(now))
            except Exception as e:
                logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                fg_oldest_wait_s = 0.0
            while True:
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
                can_submit_ga = bool(prepared) and _active_ga_gpu_count() < ga_queue_limit_effective
                if can_submit_ga:
                    song = prepared.popleft()
                    try:
                        ga_pipeline.reserve_slot(song, slot_pool)
                    except Exception as e:
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
                        try:
                            ga_pipeline.release_slot(song, slot_pool)
                        except Exception as e:
                            logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                        bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
                        payload = build_native_song_error_payload(
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
                    if _submit_fg_static_prewarm(song):
                        did_work = True
                    continue
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
                        payload = build_native_task_error_payload(
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
            for ga_completion in ga_pipeline.pop_completed_runs():
                song = ga_completion.song
                ga_future = ga_completion.future
                did_work = True
                try:
                    ga_result = ga_future.result()
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    try:
                        emit_profile_event(
                            component="inflight_ga",
                            event="future_error",
                            song_key=str(song.config.task_key),
                            metrics={
                                "exc_type": type(exc).__name__,
                                "exc": str(exc),
                            },
                        )
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:ga_future_error_event: {e}")
                    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
                    if not (stopping and is_stop_abort_exception(exc)):
                        _post(
                            build_native_song_error_payload(
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
                            build_native_song_error_payload(
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
                song.runtime.post.deferred_post_emitted = False
                fg_pipeline.queue(song, now_s=time.monotonic())
                did_work = True
            for fg_completion in fg_pipeline.pop_completed_jobs():
                fg_song = fg_completion.song
                fut = fg_completion.future
                t_submit = fg_completion.submit_t0
                did_work = True
                try:
                    fut.result()
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    if stopping and is_stop_abort_exception(exc):
                        pass
                    else:
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
                        raise RuntimeError(f"FG worker failed for {fg_song.config.task_key}") from exc
                if not bool(getattr(fg_song.runtime.post, "deferred_post_emitted", False)):
                    try:
                        _emit_deferred_post_payload(fg_song)
                    except Exception as e:
                        logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                try:
                    ga_pipeline.release_slot(fg_song, slot_pool)
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                fg_elapsed_s = time.perf_counter() - float(t_submit)
                fg_run_wall_s = float(getattr(fg_song.runtime.fg, "fg_run_wall_s", 0.0) or 0.0)
                if fg_run_wall_s <= 0.0 or fg_run_wall_s > fg_elapsed_s:
                    fg_run_wall_s = float(fg_elapsed_s)
                fg_worker_queue_s = max(0.0, float(fg_elapsed_s) - float(fg_run_wall_s))
                if fg_worker_queue_s > 0.0:
                    stage_profiler.record("fg_worker_queue", fg_worker_queue_s, song=fg_song.config.task_key)
                stage_profiler.record(
                    "fg_run",
                    fg_run_wall_s,
                    cpu_seconds=getattr(fg_song.runtime.fg, "cpu_fg_run_s", None),
                    song=fg_song.config.task_key,
                )
                finish_deferred_fg_completion(
                    fg_song,
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
            ready_ga_for_lane_fill = len(prepared) if _active_ga_gpu_count() < int(ga_queue_limit_effective) else 0
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
                        fg_song.runtime.fg.fg_queued_t0 = None
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
                        heartbeat_idle_s = float(heartbeat_bubble.get("idle_sec", 0.0) or 0.0)
                        msg = (
                            "[InFlight][HB] "
                            f"idle={heartbeat_idle_s:.1f}s "
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
                            "idle_sec": float(heartbeat_bubble.get("idle_sec", 0.0) or 0.0),
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
        shutdown_native_inflight_resources(
            fg_pipeline=fg_pipeline,
            decode_queue=decode_queue,
            cpu_prewarm_queue=cpu_prewarm_queue,
            prep_queue=prep_queue,
            post_sender=post_sender,
            gpu_client=gpu_client,
            gpu_executor=gpu_executor,
        )
@dataclass
class CompletionTracker:
    event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    ids: set[int] = field(default_factory=set)
    def register(self, fut: concurrent.futures.Future | None) -> bool:
        if fut is None:
            return False
        fut_id = int(id(fut))
        with self.lock:
            if fut_id in self.ids:
                return False
            self.ids.add(fut_id)
        def _on_done(_fut: concurrent.futures.Future, *, _fut_id: int = fut_id) -> None:
            self.unregister(_fut_id)
            self.event.set()
        try:
            fut.add_done_callback(_on_done)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self.unregister(fut_id)
            self.event.set()
            return False
        return True
    def unregister(self, fut_id: int) -> None:
        with self.lock:
            self.ids.discard(int(fut_id))
    def is_set(self) -> bool:
        return bool(self.event.is_set())
    def wait(self, timeout_s: float, *, short_spin_s: float = 0.0) -> bool:
        return bool(
            wait_for_completion_event(
                self.event,
                timeout_s=float(timeout_s),
                short_spin_s=float(short_spin_s),
                perf_counter=time.perf_counter,
                sleep=time.sleep,
            )
        )
    def clear(self) -> None:
        self.event.clear()
def has_waitable_work(*queue_groups: Iterable[Any], pending_fg: Iterable[Any] = ()) -> bool:
    for group in queue_groups:
        try:
            if group:
                return True
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:has_waitable_work: {e}")
            continue
    _ = pending_fg
    return False
def mark_song_completed(
    *,
    completed_songs: set[str],
    task_key: str,
    song_name: str,
    memory_resume_tracker=None,
    bundle_completed_cb=None,
) -> None:
    key = str(task_key)
    completed_songs.add(key)
    if memory_resume_tracker:
        memory_resume_tracker.mark_completed(str(song_name))
    if bundle_completed_cb is not None:
        try:
            bundle_completed_cb(key, completed_songs)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:mark_song_completed: {e}")
def emit_deferred_post_payload(
    song: NativeSong,
    *,
    post: Callable[[dict], None],
    persist_pending_fg_job: bool,
    completed_songs: set[str],
    memory_resume_tracker=None,
    bundle_completed_cb=None,
    advance_bundle: Callable[..., None],
    progress_tracker=None,
    progress_cb=None,
) -> bool:
    if bool(getattr(song.runtime.post, "deferred_post_emitted", False)):
        return False
    post(build_deferred_post_payload(song, persist_pending_fg_job=bool(persist_pending_fg_job)))
    song.runtime.post.deferred_post_emitted = True
    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
    needs_fg_stage = bool(fg_pending_for_post(song))
    if bundle_parent is not None and needs_fg_stage:
        song.runtime.bundle.bundle_wait_for_fg = True
    elif bundle_parent is not None:
        advance_bundle(
            bundle_parent,
            song_name=str(song.config.song_name),
            record_info=getattr(song.runtime.db, "record_info", None),
            failed=False,
        )
    elif needs_fg_stage:
        song.runtime.post.await_fg_completion_progress = True
    else:
        mark_song_completed(
            completed_songs=completed_songs,
            task_key=song.config.task_key,
            song_name=song.config.song_name,
            memory_resume_tracker=memory_resume_tracker,
            bundle_completed_cb=bundle_completed_cb,
        )
        if progress_tracker is not None:
            progress_tracker.emit_done_song_progress(progress_cb, song)
    return True
def finish_deferred_fg_completion(
    song: NativeSong,
    *,
    completed_songs: set[str],
    memory_resume_tracker=None,
    bundle_completed_cb=None,
    advance_bundle: Callable[..., None],
    progress_tracker=None,
    progress_cb=None,
) -> bool:
    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
    if bundle_parent is not None and bool(getattr(song.runtime.bundle, "bundle_wait_for_fg", False)):
        advance_bundle(
            bundle_parent,
            song_name=str(song.config.song_name),
            record_info=getattr(song.runtime.db, "record_info", None),
            failed=False,
        )
        song.runtime.bundle.bundle_wait_for_fg = False
        return True
    if bool(getattr(song.runtime.post, "await_fg_completion_progress", False)):
        mark_song_completed(
            completed_songs=completed_songs,
            task_key=song.config.task_key,
            song_name=song.config.song_name,
            memory_resume_tracker=memory_resume_tracker,
            bundle_completed_cb=bundle_completed_cb,
        )
        if progress_tracker is not None:
            progress_tracker.emit_done_song_progress(progress_cb, song)
        song.runtime.post.await_fg_completion_progress = False
        return True
    return False
from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_effective_unique_ga_candidates
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_candidate_names
from gear_optimizer.helpers.song_helpers.payload_compaction import compact_fg_variants
from gear_optimizer.solver.inflight_utils import _compact_items, _compact_prev_record
def build_ga_candidates_for_post(
    candidates: list[dict] | None,
    *,
    registry: Any,
    minis_by_name: dict | None,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    limit: int = LOADOUTS_PER_SONG_LIMIT,
    selector: Callable[..., list[dict]] = select_effective_unique_ga_candidates,
    materializer: Callable[..., tuple[list[str], list[str]]] = materialize_candidate_names,
) -> list[dict[str, Any]]:
    selected = selector(
        list(candidates or []),
        limit=int(limit),
        registry=registry,
        minis_by_name=minis_by_name,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
    )
    out: list[dict[str, Any]] = []
    for cand in selected or []:
        if not isinstance(cand, dict):
            continue
        data0 = cand.get("Data") or {}
        candidate_for_post = dict(cand)
        candidate_for_post["Data"] = dict(data0) if isinstance(data0, dict) else {}
        gear_names, mini_names = materializer(
            candidate_for_post,
            registry=registry,
            mutate=False,
        )
        out.append(
            {
                "Score": candidate_for_post.get("Score", 0),
                "BaseScore": candidate_for_post.get("BaseScore", candidate_for_post.get("Score", 0)),
                "Gear": list(gear_names),
                "Minis": list(mini_names),
                "Data": candidate_for_post.get("Data") or {},
                "_fg_priority": candidate_for_post.get("_fg_priority", 0),
                "loadout_hash": candidate_for_post.get("loadout_hash"),
            }
        )
    return out
def fg_scored_for_song(song: NativeSong) -> bool:
    return getattr(song.runtime.fg, "fg_variants", None) is not None
def fg_pending_for_post(song: NativeSong) -> bool:
    return bool(not fg_scored_for_song(song))
def build_native_song_error_payload(
    song: NativeSong,
    *,
    exc: Exception,
    trace: str,
    suppress_for_bundle: bool = True,
) -> dict[str, Any]:
    payload = build_error_payload(
        song_name=str(song.config.song_name),
        queue_key=str(song.config.task_key),
        queue_label=str(song.config.task_key),
        exc=exc,
        trace=trace,
    )
    if bool(suppress_for_bundle) and getattr(song.runtime.bundle, "bundle_parent_task", None) is not None:
        payload["_suppress_progress"] = True
    return payload
def build_native_task_error_payload(
    *,
    song_name: str,
    queue_key: str,
    exc: Exception,
    trace: str,
    queue_label: str | None = None,
    suppress_progress: bool = False,
) -> dict[str, Any]:
    key = str(queue_key)
    payload = build_error_payload(
        song_name=str(song_name),
        queue_key=key,
        queue_label=str(queue_label if queue_label is not None else key),
        exc=exc,
        trace=trace,
    )
    if bool(suppress_progress):
        payload["_suppress_progress"] = True
    return payload
def build_fg_update_payload(song: NativeSong, *, persist_entries: list[dict]) -> dict[str, Any]:
    return {
        "_fg_update": True,
        "song": song.config.song_name,
        "db_key": song.config.db_key,
        "persist_entries": list(persist_entries or []),
        "file_path": song.config.fp,
        "cfg_dict": song.config.cfg_dict,
    }
def build_deferred_post_payload(song: NativeSong, *, persist_pending_fg_job: bool) -> dict[str, Any]:
    best_data_for_post = song.runtime.decode.best_data or {}
    best_data_post = dict(best_data_for_post) if isinstance(best_data_for_post, dict) else {}
    pending_fg_job = fg_pending_for_post(song)
    fg_variants_post = (
        compact_fg_variants(list(getattr(song.runtime.fg, "fg_variants", None) or []))
        if fg_scored_for_song(song)
        else []
    )
    candidates_for_post = (
        song.runtime.decode.ga_persistence_candidates
        if isinstance(getattr(song.runtime.decode, "ga_persistence_candidates", None), list)
        and getattr(song.runtime.decode, "ga_persistence_candidates", None)
        else song.runtime.decode.ga_candidates
    )
    ga_candidates_post = build_ga_candidates_for_post(
        list(candidates_for_post or []),
        registry=song.gpu_inputs.registry,
        minis_by_name=song.gpu_inputs.minis_by_name,
        primary_color=str(song.gpu_inputs.meta_primary_color or ""),
        secondary_color=str(song.gpu_inputs.meta_secondary_color or ""),
        selected_color=str((song.gpu_inputs.cfg_data or {}).get("selected_color", "") or ""),
        selector=select_effective_unique_ga_candidates,
        materializer=materialize_candidate_names,
    )
    return {
        "_deferred_post": True,
        "_pending_fg_job": bool(pending_fg_job),
        "song": song.config.song_name,
        "_queue_key": song.config.task_key,
        "_queue_label": song.config.task_key,
        "_ga_seed": song.config.ga_seed,
        "db_key": song.config.db_key,
        "difficulty": song.config.effective_difficulty,
        "cfg_dict": song.config.cfg_dict,
        "ref_arrays": song.gpu_inputs.ref_arrays,
        "calc_song": song.gpu_inputs.calc_song,
        "best_data": best_data_post,
        "best_gear": _compact_items(song.runtime.decode.best_gear),
        "best_minis": _compact_items(song.runtime.decode.best_minis),
        "current_gear": _compact_items(song.gpu_inputs.current_gear_list),
        "current_minis": _compact_items(song.gpu_inputs.current_mini_list),
        "fg_variants": fg_variants_post,
        "ga_candidates": ga_candidates_post,
        "_persist_pending_fg_job": bool(persist_pending_fg_job and pending_fg_job),
        "prev_record": _compact_prev_record(song.runtime.db.prev_record),
        "attempt_lifetime": int(song.runtime.db.attempt_lifetime or 0),
        "prev_attempts_first": int(song.runtime.db.prev_attempts_first or 0),
        "db_best_fg_score": int(song.runtime.db.db_best_fg_score or 0),
        "meta_primary_color": song.gpu_inputs.meta_primary_color,
        "meta_secondary_color": song.gpu_inputs.meta_secondary_color,
        "fg_debug": bool(song.config.fg_debug),
    }
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_config import has_valid_fg_config
from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload
from gear_optimizer.helpers.song_helpers.ga_entry_utils import entry_loadout_hash, materialize_entry_names
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
def ensure_fg_build_details(song: NativeSong) -> Callable:
    build_details = song.runtime.fg.fg_build_details
    if callable(build_details):
        return build_details
    build_details = make_build_details_fn(
        getattr(song.gpu_inputs, "meta_primary_color", ""),
        getattr(song.gpu_inputs, "meta_secondary_color", ""),
        getattr(song.config, "effective_difficulty", ""),
    )
    song.runtime.fg.fg_build_details = build_details
    return build_details
def build_fg_persist_entries(song: NativeSong) -> list[dict]:
    entries: list[dict] = []
    build_details = ensure_fg_build_details(song)
    raw_loadout_entries = song.runtime.fg.loadout_entries
    loadout_entries = raw_loadout_entries if isinstance(raw_loadout_entries, dict) else {}
    loadout_hash_index: dict[str, dict] = {}
    if loadout_entries:
        for loadout_key, entry in loadout_entries.items():
            if isinstance(entry, dict):
                loadout_hash_index.setdefault(str(loadout_key), entry)
            try:
                loadout_hash = entry_loadout_hash(entry)
            except Exception as e:
                logger.debug(f"native_inflight_orchestrator:build_fg_persist_entries: {e}")
                loadout_hash = None
            if not loadout_hash or not isinstance(entry, dict):
                continue
            loadout_hash_index.setdefault(str(loadout_hash), entry)
    for v in song.runtime.fg.fg_variants or []:
        if not isinstance(v, dict):
            continue
        is_ga = bool(v.get("_is_ga"))
        base_score = safe_int(v.get("base_score", v.get("score", 0)), 0)
        fg_score = safe_int(v.get("fg_score", 0), 0)
        gear_names = _compact_items(v.get("gear") or [])
        mini_names = _compact_items(v.get("minis") or [])
        data = v.get("data")
        if not (isinstance(data, dict) and has_valid_fg_config(data)):
            data = v.get("force")
        if not (isinstance(data, dict) and has_valid_fg_config(data)) and isinstance(v.get("_entry_ref"), dict):
            data = v["_entry_ref"].get("force")
        if not isinstance(data, dict):
            data = {}
        base_entry = None
        if (not gear_names and not mini_names) and isinstance(v.get("_entry_ref"), dict):
            try:
                gear_names, mini_names = materialize_entry_names(v.get("_entry_ref"), mutate=True)
            except Exception as e:
                logger.debug(f"native_inflight_orchestrator:build_fg_persist_entries: {e}")
                gear_names, mini_names = [], []
        if gear_names or mini_names:
            try:
                from gear_optimizer.data.database import get_loadout_hash as _get_loadout_hash
                candidate = loadout_hash_index.get(str(_get_loadout_hash(gear_names, mini_names)))
                if isinstance(candidate, dict):
                    base_entry = candidate
            except Exception as e:
                logger.debug(f"native_inflight_orchestrator:build_fg_persist_entries: {e}")
                base_entry = None
        if isinstance(base_entry, dict):
            entry_base_score = safe_int(
                base_entry.get("base_score"),
                safe_int(base_entry.get("score", 0), base_score),
            )
            if entry_base_score > 0:
                base_score = entry_base_score
        details_obj = base_entry.get("details") if isinstance(base_entry, dict) else None
        if isinstance(details_obj, dict) and details_obj:
            details = dict(details_obj)
        else:
            details_source = base_entry.get("eval_data") if isinstance(base_entry, dict) else None
            if not isinstance(details_source, dict) or not details_source:
                details_source = data if isinstance(data, dict) else {}
            details = build_details(details_source) if callable(build_details) else {}
            if not isinstance(details, dict):
                details = {}
            details = dict(details)
            details["ForceGreats"] = (data.get("ForceGreats", {}) if isinstance(data, dict) else {}) or {}
        force_obj = None
        try:
            if isinstance(data, dict) and has_valid_fg_config(data):
                force_obj = dict(data)
                materialize_stats_from_payload(force_obj, mutate_payload=True)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:build_fg_persist_entries: {e}")
            force_obj = None
        if force_obj is None:
            continue
        entries.append(
            {
                "score": int(base_score),
                "fg_score": int(fg_score),
                "gear": gear_names,
                "minis": mini_names,
                "details": details,
                "force": force_obj,
                "_is_ga": bool(is_ga),
                "_deferred_fg_update": True,
            }
        )
    return entries
