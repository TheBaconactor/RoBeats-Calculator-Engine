"""
GPU-native in-flight multi-song orchestrator (single process, single GPU owner thread).
This pipeline is designed to keep the GPU continuously busy in native GA mode by:
- Preparing the next songs' CPU-only data while the GPU runs the current song.
- Executing GPU-native GA on the Taichi/Vulkan owner thread (GpuExecutor) via an in-process
  request queue (no per-song process overhead, minimal transfers).
- Keeping the owner's GA queue at full slot depth: a song's slot is held only for the
  lifetime of its GA request (the fused GA turn already scores FG on-device), so every
  usable slot stays in the GA conveyor and the owner never idles while prepared work exists.
- Running ForceGreats materialization host-only on FG workers (fused owner score map),
  bounded by a single FG-backlog admission gate instead of credit/lane scheduling.
"""
from __future__ import annotations
import logging
import time
import traceback
from collections import deque
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.domain.jobs import extract_repeat_context, task_file_path, task_queue_label, task_song_name
from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError
from gear_optimizer.solver.native_inflight_config import (
    default_worker_threads,
    inflight_stall_debug_enabled,
    parse_inflight_config,
)
from gear_optimizer.solver.inflight_wait import (
    read_inflight_event_wait_timeout_s,
    read_inflight_event_wait_gpu_cap_s,
    read_inflight_event_wait_short_spin_s,
)
from gear_optimizer.solver.native_inflight_completion import (
    CompletionTracker,
    build_native_song_error_payload,
    build_native_task_error_payload,
    emit_deferred_post_payload,
    finish_deferred_fg_completion,
    has_waitable_work,
    mark_song_completed,
)
from gear_optimizer.solver.native_inflight_lifecycle import prepare_native_song
from gear_optimizer.solver.native_inflight_scheduler_policy import (
    continuous_fg_allow_not_ready,
    continuous_fg_prep_start_budget,
    continuous_fg_submit_budget,
    count_active_song_lanes,
    ga_admission_fg_backlog_limit,
    ga_should_pause_for_fg_backlog,
)
from gear_optimizer.solver import native_inflight_pipeline as native_fg_pipeline
from gear_optimizer.solver.native_inflight_pipeline import GADecodeQueue, InflightGAPipeline
from gear_optimizer.solver.native_inflight_lifecycle import (
    BubbleTracker,
    CachedRuntimeSignal,
    GpuAbortRequester,
    InflightBundleTracker,
    PostSender,
    SongPrepQueue,
    is_stop_abort_exception,
    log_native_abort,
    shutdown_native_inflight_resources,
    start_native_inflight_gpu_client,
)
from gear_optimizer.solver.native_inflight_lifecycle import ActiveRuntimeProgressReporter, ProgressTracker
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_pipeline import (
    InFlightStageProfiler,
    decode_ga_payload_sync,
    prepare_fg_job_sync,
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
    icfg = parse_inflight_config(tasks, in_flight_songs=in_flight_songs)
    ga_queue_limit = int(icfg.ga_queue_limit)
    from gear_optimizer.solver.song_slot_pool import SongSlotPool
    slot_pool = SongSlotPool(max_song_slots=int(icfg.max_song_slots))
    gpu_executor, gpu_client = start_native_inflight_gpu_client(icfg, progress_cb=progress_cb)
    stage_profiler = InFlightStageProfiler(enabled=icfg.stage_profile_enabled, out_path=icfg.stage_profile_path)
    post_sender = PostSender(post_queue, stop_requested=stop_requested) if post_queue is not None else None
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
    decode_queue = GADecodeQueue(max_workers=int(icfg.decode_workers))
    decode_inflight = decode_queue.inflight
    fg_pipeline_settings = native_fg_pipeline.read_native_fg_pipeline_settings(
        inflight_limit=int(icfg.inflight_limit),
        default_worker_threads=default_worker_threads,
    )
    fg_pipeline = native_fg_pipeline.NativeFGPipeline(fg_pipeline_settings)
    pending_fg = fg_pipeline.pending
    fg_prep_inflight = fg_pipeline.prep_inflight
    fg_futures = fg_pipeline.futures
    active_runtime_reporter = ActiveRuntimeProgressReporter(_emit_progress)
    fg_workers = int(fg_pipeline.workers)
    fg_batch_max = int(fg_pipeline.batch_max)
    completion_tracker = CompletionTracker()
    stop_signal = CachedRuntimeSignal(stop_requested, poll_interval_s=0.05)
    memory_release_signal = CachedRuntimeSignal(memory_release_requested, poll_interval_s=0.05)
    gpu_abort_requester = GpuAbortRequester(gpu_executor)
    fg_backlog_limit = ga_admission_fg_backlog_limit(
        fg_workers=int(fg_pipeline.workers),
        fg_prep_workers=int(fg_pipeline.prep_workers),
    )
    def _ga_slots_held() -> int:
        # Every song in ga_inflight holds a slot from reserve-at-admission until
        # the completion handler releases it — including futures that are DONE
        # but not yet processed. Admission must gate on slot holders, not on
        # still-running futures, or the pool overruns.
        return len(ga_inflight)
    def _active_song_lane_count() -> int:
        return count_active_song_lanes(
            ga_inflight=ga_inflight,
            decode_inflight=decode_inflight,
            fg_active_keys=fg_pipeline.active_song_keys(),
        )
    def _submit_fg_jobs(*, submit_budget: int, allow_not_ready: bool) -> int:
        submitted = 0
        while int(submit_budget) > 0 and len(fg_futures) < fg_workers and pending_fg:
            effective_allow_not_ready = bool(allow_not_ready)
            if effective_allow_not_ready and fg_pipeline.has_active_prep():
                effective_allow_not_ready = False
            fg_song = fg_pipeline.pop_next(allow_not_ready=bool(effective_allow_not_ready))
            if fg_song is None:
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
                    logger.debug(f"native_inflight_orchestrator:_submit_fg_jobs: {e}")
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
            submitted += 1
            submit_budget -= 1
        return int(submitted)
    # First-wave prep goes through the same prep-worker runway as steady state (the
    # first loop iteration fills it): the old synchronous prime loop prepared 8-12
    # songs serially on this thread while the already-warm GPU idled.
    def _fill_song_prep_runway() -> bool:
        submitted_any = False
        while (
            (not stopping)
            and pending_tasks
            and (len(prepared) + len(prep_inflight) < icfg.prep_limit)
        ):
            nxt = pending_tasks.popleft()
            nxt_bundle_key = task_queue_label(nxt)
            if nxt_bundle_key in completed_songs:
                submitted_any = True
                continue
            logical_nxt, _repeat_ctx = _next_logical_task(nxt)
            nxt_key = task_queue_label(logical_nxt)
            try:
                prep_queue.submit(
                    nxt,
                    logical_nxt,
                    register_future=completion_tracker.register,
                )
            except Exception as exc:
                is_repeat_bundle = bool(bundle_tracker.bundle_runs(nxt))
                payload = build_native_task_error_payload(
                    song_name=task_song_name(nxt),
                    queue_key=str(nxt_key),
                    exc=exc,
                    trace=traceback.format_exc(),
                    suppress_progress=is_repeat_bundle,
                )
                _post(payload)
                advanced = False
                if is_repeat_bundle:
                    advanced = _advance_bundle(nxt, song_name=task_song_name(nxt), failed=True)
                if not advanced:
                    mark_song_completed(
                        completed_songs=completed_songs,
                        task_key=nxt_key,
                        song_name=task_song_name(nxt),
                        song_path=task_file_path(nxt),
                        memory_resume_tracker=memory_resume_tracker,
                    )
                submitted_any = True
                continue
            submitted_any = True
        return bool(submitted_any)

    def _emit_deferred_post_payload(song: NativeSong) -> None:
        emit_deferred_post_payload(
            song,
            post=_post,
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
        heartbeat_sec = float(icfg.loop_observer.heartbeat_sec)
        throughput_sec = float(icfg.loop_observer.throughput_sec)
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
                decode_inflight_count=len(decode_inflight),
                pending_fg_count=len(pending_fg),
                fg_prep_inflight_count=len(fg_prep_inflight),
                ga_inflight_count=len(ga_inflight),
                fg_futures_count=len(fg_futures),
                last_progress=float(last_progress),
                oldest_fg_wait_s=float(oldest_fg_wait_s),
            )
        stopping = False
        while (
            pending_tasks
            or prepared
            or prep_inflight
            or pending_fg
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
            did_work = False
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
                    prep_elapsed_s = time.perf_counter() - float(t_submit)
                    prep_wall_s = float(getattr(prepared_song.runtime.prep, "wall_prep_s", 0.0) or 0.0)
                    if prep_wall_s <= 0.0 or prep_wall_s > prep_elapsed_s:
                        prep_wall_s = float(prep_elapsed_s)
                    prep_queue_s = max(0.0, float(prep_elapsed_s) - float(prep_wall_s))
                    if prep_queue_s > 0.0:
                        stage_profiler.record("prep_queue", prep_queue_s, song=task_key)
                    stage_profiler.record(
                        "prep",
                        prep_wall_s,
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
                except Exception as exc:
                    if stopping and is_stop_abort_exception(exc):
                        continue
                    is_repeat_bundle = bool(bundle_tracker.bundle_runs(task))
                    payload = build_native_task_error_payload(
                        song_name=str(song_name),
                        queue_key=str(task_key),
                        exc=exc,
                        trace=traceback.format_exc(),
                        suppress_progress=is_repeat_bundle,
                    )
                    _post(payload)
                    advanced = False
                    if is_repeat_bundle:
                        advanced = _advance_bundle(task, song_name=str(song_name), failed=True)
                    if not advanced:
                        mark_song_completed(
                            completed_songs=completed_songs,
                            task_key=task_key,
                            song_name=song_name,
                            song_path=task_file_path(task),
                            memory_resume_tracker=memory_resume_tracker,
                        )
            ready_fg_from_prep = False
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
                        ready_fg_from_prep = True
                        continue
                    if stopping and is_stop_abort_exception(prep_completion.error):
                        pass
                    else:
                        bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
                        _post(
                            build_native_song_error_payload(
                                song,
                                exc=prep_completion.error,
                                trace=prep_completion.trace,
                            )
                        )
                        if bundle_parent is not None:
                            _advance_bundle(bundle_parent, song_name=str(song.config.song_name), failed=True)
                        else:
                            mark_song_completed(
                                completed_songs=completed_songs,
                                task_key=song.config.task_key,
                                song_name=song.config.song_name,
                                song_path=song.config.fp,
                                memory_resume_tracker=memory_resume_tracker,
                            )
                except Exception as exc:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {exc}")
            if ready_fg_from_prep and pending_fg:
                ready_budget = continuous_fg_submit_budget(
                    pending_fg_count=len(pending_fg),
                    ready_fg_count=int(fg_pipeline.ready_count()),
                    fg_inflight_count=len(fg_futures),
                    fg_workers=int(fg_workers),
                    fg_batch_max=int(fg_batch_max),
                    no_ga_remaining=False,
                )
                if ready_budget > 0:
                    submitted_fg = _submit_fg_jobs(
                        submit_budget=int(ready_budget),
                        allow_not_ready=False,
                    )
                    if int(submitted_fg) > 0:
                        did_work = True
            if _fill_song_prep_runway():
                did_work = True
            if pending_fg:
                try:
                    fg_prep_start_budget = continuous_fg_prep_start_budget(
                        pending_fg_count=len(pending_fg),
                        fg_prep_inflight_count=len(fg_prep_inflight),
                        fg_prep_worker_count=int(fg_pipeline.prep_workers),
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
                if ga_should_pause_for_fg_backlog(
                    pending_fg_count=len(pending_fg),
                    fg_inflight_count=len(fg_futures),
                    backlog_limit=int(fg_backlog_limit),
                ):
                    break
                can_submit_ga = bool(prepared) and _ga_slots_held() < ga_queue_limit
                if can_submit_ga:
                    song = prepared.popleft()
                    # ga_queue_limit is capped at the usable slot count and admission
                    # gates on slot holders (every ga_inflight song holds one until
                    # its completion is processed), so admission implies a free slot;
                    # NoFreeSongSlotError here is an invariant breach and must raise.
                    ga_pipeline.reserve_slot(song, slot_pool)
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
                                song_path=song.config.fp,
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
                    continue
                if stopping:
                    break
                if _fill_song_prep_runway():
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
                            song_path=song.config.fp,
                            memory_resume_tracker=memory_resume_tracker,
                        )
                    continue
                t_submit = getattr(song.runtime.ga, "ga_submit_t0", None)
                if t_submit is not None:
                    stage_profiler.record("ga_gpu", time.perf_counter() - float(t_submit), song=song.config.task_key)
                    song.runtime.ga.ga_submit_t0 = None
                song.runtime.ga.ga_future = None
                # The GA request (GA loop + fused FG owner score + payload download)
                # is the only consumer of the song's device slot. Everything after it
                # (decode, FG prep, FG materialization, persist) is host-only, so the
                # slot returns to the conveyor immediately.
                ga_pipeline.release_slot(song, slot_pool)
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
                        metrics={},
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
                    if stopping and is_stop_abort_exception(exc):
                        continue
                    if bundle_parent is not None:
                        _advance_bundle(bundle_parent, song_name=str(song.config.song_name), failed=True)
                    else:
                        mark_song_completed(
                            completed_songs=completed_songs,
                            task_key=song.config.task_key,
                            song_name=song.config.song_name,
                            song_path=song.config.fp,
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
                            "ga_candidates": int(len(song.runtime.decode.ga_candidates or [])),
                        },
                    )
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                song.runtime.post.deferred_post_emitted = False
                fg_pipeline.queue(song, now_s=time.monotonic())
                try:
                    started_fg_prep = fg_pipeline.start_pending_prep(
                        prepare_fg_job_sync,
                        gpu_client=gpu_client,
                        max_new=1,
                        register_future=completion_tracker.register,
                    )
                except Exception as e:
                    logger.debug(f"native_inflight_orchestrator:_note_bubble_snapshot: {e}")
                    started_fg_prep = 0
                if int(started_fg_prep) > 0:
                    did_work = True
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
            no_ga_remaining = (
                (not pending_tasks)
                and (not prepared)
                and (not prep_inflight)
                and (not ga_inflight)
                and (not decode_inflight)
            )
            # FG jobs are host-only materialization: hand every free FG worker a
            # prep-ready song. No owner-cycle arbitration is needed anymore.
            submit_budget = continuous_fg_submit_budget(
                pending_fg_count=len(pending_fg),
                ready_fg_count=int(ready_fg_count),
                fg_inflight_count=len(fg_futures),
                fg_workers=int(fg_workers),
                fg_batch_max=int(fg_batch_max),
                no_ga_remaining=bool(no_ga_remaining),
            )
            if submit_budget > 0:
                submitted_fg = _submit_fg_jobs(
                    submit_budget=int(submit_budget),
                    allow_not_ready=continuous_fg_allow_not_ready(
                        no_ga_remaining=bool(no_ga_remaining),
                    ),
                )
                if int(submitted_fg) > 0:
                    did_work = True
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
                            f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                            f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)} "
                            f"lanes={int(heartbeat_bubble.get('active_song_lanes', 0) or 0)}"
                        )
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
                            "ga_inflight": int(len(ga_inflight)),
                            "decode_inflight": int(len(decode_inflight)),
                            "pending_fg": int(len(pending_fg)),
                            "fg_prep_inflight": int(len(fg_prep_inflight)),
                            "fg_futures": int(len(fg_futures)),
                            "oldest_ga_sec": float(oldest_ga_s) if oldest_ga_s is not None else -1.0,
                            "bubble_kpi": float(heartbeat_bubble.get("bubble_kpi", 0.0) or 0.0),
                            "bubble_ready_ga": int(heartbeat_bubble.get("ready_ga_count", 0) or 0),
                            "bubble_ready_fg": int(heartbeat_bubble.get("ready_fg_count", 0) or 0),
                            "active_song_lanes": int(heartbeat_bubble.get("active_song_lanes", 0) or 0),
                            "bubble_backlog": int(heartbeat_bubble.get("backlog_count", 0) or 0),
                            "bubble_oldest_fg_wait_sec": float(fg_oldest_wait_s),
                        },
                    )
                no_active_work = (
                    (not ga_inflight)
                    and (not decode_inflight)
                    and (not prep_inflight)
                    and (not fg_prep_inflight)
                    and (not fg_futures)
                )
                if (
                    no_active_work
                    and (pending_tasks or prepared or pending_fg or fg_futures)
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
                        "decode_inflight=%s pending_fg=%s fg_prep=%s fg_inflight=%s fg_done=%s",
                        len(pending_tasks),
                        len(prepared),
                        len(prep_inflight),
                        len(ga_inflight),
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
                            "bubble_backlog": int(bubble_snapshot.get("backlog_count", 0) or 0),
                            "bubble_oldest_fg_wait_sec": float(fg_oldest_wait_s),
                        },
                    )
                if has_waitable_work(
                    ga_inflight,
                    prep_inflight,
                    decode_inflight,
                    fg_prep_inflight,
                    fg_futures,
                    pending_fg=pending_fg,
                ):
                    t_wait = time.perf_counter()
                    has_gpu = bool(ga_inflight) or bool(fg_futures)
                    has_cpu = (
                        bool(prep_inflight)
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
            )
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
            prep_queue=prep_queue,
            post_sender=post_sender,
            gpu_client=gpu_client,
            gpu_executor=gpu_executor,
        )
