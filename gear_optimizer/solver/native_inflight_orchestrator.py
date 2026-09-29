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
from gear_optimizer import settings
from gear_optimizer.domain.jobs import extract_repeat_context, task_file_path, task_queue_label, task_song_name
from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError
from gear_optimizer.solver.native_inflight_config import (
    default_worker_threads,
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
from gear_optimizer.solver import native_inflight_pipeline_fg as native_fg_pipeline
from gear_optimizer.solver.native_inflight_pipeline import GADecodeQueue, InflightGAPipeline
from gear_optimizer.solver.native_inflight_lifecycle import (
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
    gpu_executor, gpu_client = start_native_inflight_gpu_client(progress_cb=progress_cb)
    post_sender = PostSender(post_queue, stop_requested=stop_requested) if post_queue is not None else None
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
            fg_pipeline.submit_materialization(
                fg_song,
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

    def _emit_deferred_post_payload(song: NativeSong) -> bool:
        return emit_deferred_post_payload(
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
        event_wait_timeout_s = float(read_inflight_event_wait_timeout_s())
        event_wait_gpu_cap_s = float(read_inflight_event_wait_gpu_cap_s())
        event_wait_short_spin_s = float(read_inflight_event_wait_short_spin_s())
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
            if stop_signal.requested(now):
                if not stopping:
                    stopping = True
                    gpu_abort_requester.request("native in-flight stop requested")
                    pending_tasks.clear()
                    prepared.clear()
                    pending_fg.clear()
                    prep_queue.cancel_all()
                    decode_queue.cancel_all()
            did_work = False
            for prep_completion in prep_queue.pop_completed():
                task = prep_completion.task
                logical_task = prep_completion.logical_task
                fut = prep_completion.future
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
                    prepared.append(prepared_song)
                    progress_tracker.seed_valid_baseline(
                        prepared_song.config.db_key,
                        best_score=int(prepared_song.runtime.db.db_best_score or 0),
                        best_fg=int(prepared_song.runtime.db.db_best_fg_score or 0),
                        baseline_valid=bool(prepared_song.runtime.db.db_baseline_valid),
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
                if prep_completion.error is None:
                    ready_fg_from_prep = True
                    continue
                if stopping and is_stop_abort_exception(prep_completion.error):
                    pass
                else:
                    bundle_parent = song.runtime.bundle.bundle_parent_task
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
                if int(started_fg_prep) > 0:
                    did_work = True
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
                        ga_pipeline.release_slot(song, slot_pool)
                        bundle_parent = song.runtime.bundle.bundle_parent_task
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
                    bundle_parent = song.runtime.bundle.bundle_parent_task
                    if not (stopping and is_stop_abort_exception(exc)):
                        _post(
                            build_native_song_error_payload(
                                song,
                                exc=exc,
                                trace=traceback.format_exc(),
                            )
                        )
                    ga_pipeline.release_slot(song, slot_pool)
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
            for decode_completion in decode_queue.pop_completed():
                song = decode_completion.song
                decode_future = decode_completion.future
                did_work = True
                try:
                    decode_result = decode_future.result()
                except Exception as exc:
                    bundle_parent = song.runtime.bundle.bundle_parent_task
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
                ga_pipeline.store_decode_result(song, decode_result)
                song.runtime.post.deferred_post_emitted = False
                fg_pipeline.queue(song)
                started_fg_prep = fg_pipeline.start_pending_prep(
                    prepare_fg_job_sync,
                    gpu_client=gpu_client,
                    max_new=1,
                    register_future=completion_tracker.register,
                )
                if int(started_fg_prep) > 0:
                    did_work = True
                did_work = True
            for fg_completion in fg_pipeline.pop_completed_jobs():
                fg_song = fg_completion.song
                fut = fg_completion.future
                did_work = True
                try:
                    materialization_result = fut.result()
                    native_fg_pipeline.apply_fg_materialization_result(
                        fg_song,
                        materialization_result,
                        progress_cb=progress_cb,
                        progress_tracker=progress_tracker,
                    )
                except GpuServiceTimeoutError:
                    raise
                except Exception as exc:
                    if stopping and is_stop_abort_exception(exc):
                        pass
                    else:
                        logger.exception("[NativeInflight][FG] worker failed for %s", fg_song.config.task_key)
                        raise RuntimeError(f"FG worker failed for {fg_song.config.task_key}") from exc
                finally:
                    native_fg_pipeline.release_fg_song_surfaces(fg_song)
                if fg_song.runtime.post.deferred_post_emitted:
                    raise RuntimeError(
                        "FG completion found an already-emitted deferred payload for "
                        f"{fg_song.config.task_key}; native in-flight persistence must emit "
                        "one combined GA+FG payload"
                    )
                if not _emit_deferred_post_payload(fg_song):
                    raise RuntimeError(
                        "FG completion failed to emit the combined deferred payload for "
                        f"{fg_song.config.task_key}"
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
            ready_fg_count = fg_pipeline.ready_count()
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
            if not did_work:
                if has_waitable_work(
                    ga_inflight,
                    prep_inflight,
                    decode_inflight,
                    fg_prep_inflight,
                    fg_futures,
                    pending_fg=pending_fg,
                ):
                    has_gpu = bool(ga_inflight)
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
                else:
                    time.sleep(0.001)
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
        shutdown_native_inflight_resources(
            fg_pipeline=fg_pipeline,
            decode_queue=decode_queue,
            prep_queue=prep_queue,
            post_sender=post_sender,
            gpu_client=gpu_client,
            gpu_executor=gpu_executor,
            keep_gpu_executor_running=settings.persistent_worker(),
        )
