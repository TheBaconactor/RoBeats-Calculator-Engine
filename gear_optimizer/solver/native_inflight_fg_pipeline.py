from __future__ import annotations

import concurrent.futures
import time
import traceback
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable
import logging

from gear_optimizer.core.utils import safe_int
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
from gear_optimizer.helpers.song_helpers.force_greats.native_ga_variants import score_native_ga_force_greats
from gear_optimizer.helpers.song_helpers.loadout_builder import merge_db_loadouts_into_entries
from gear_optimizer.helpers.song_helpers.persistence import evaluate_progress_record_update, make_build_details_fn
from gear_optimizer.solver.inflight_utils import _truthy
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.native_inflight_progress import ProgressTracker
from gear_optimizer.solver.native_inflight_persistence import _build_fg_persist_entries
from gear_optimizer.solver.native_inflight_config import _read_db_prefetch_workers, _read_fg_static_prep_max_inflight
from gear_optimizer.solver.native_inflight_result_events import fg_enabled_for_song
from gear_optimizer.solver.native_inflight_stages import _prepare_fg_job_sync, _resolve_active_fg_calc_song
from gear_optimizer.solver.native_inflight_support import _PostSender, _loadout_entries_have_db_source
from gear_optimizer.solver.native_inflight_timing import _thread_cpu_time_s
from gear_optimizer.solver.native_inflight_types import _NativeSong

logger = logging.getLogger(__name__)
@dataclass(frozen=True)
class NativeFGPipelineSettings:
    workers: int
    batch_max: int
    prep_workers: int
    ga_credit_budget: int
    static_prep_max_inflight: int = 0
    db_prefetch_workers: int = 1


@dataclass(frozen=True)
class NativeFGPrepCompletion:
    song: _NativeSong
    submit_t0: float | None
    cpu_seconds: float | None
    error: Exception | None = None
    trace: str = ""
    future_missing: bool = False


@dataclass(frozen=True)
class NativeFGJobCompletion:
    song: _NativeSong
    future: concurrent.futures.Future
    submit_t0: float


def read_native_fg_pipeline_settings(
    cfg0: Any,
    *,
    inflight_limit: int,
    ga_credit_budget_cfg: int,
    cpu_prewarm_lookahead: int = 0,
    default_worker_threads: Callable[..., int],
) -> NativeFGPipelineSettings:
    inflight_limit_i = max(1, int(inflight_limit))

    fg_workers_default = min(8, inflight_limit_i)
    fg_workers = fg_workers_default
    if cfg0 is not None:
        try:
            fg_workers = safe_int(
                cfg0.get("IterationEngine", "InFlight_FGWorkers", fallback=str(fg_workers_default)),
                fg_workers_default,
            )
        except (ValueError, TypeError):
            fg_workers = fg_workers_default
    raw = env_get("INFLIGHT_FG_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_workers = int(raw)
        except (ValueError, TypeError):
            pass
    fg_workers = max(1, min(int(fg_workers), int(inflight_limit_i), 8))

    fg_batch_max = int(fg_workers)
    try:
        raw = env_get("INFLIGHT_FG_BATCH_MAX")
        if raw is not None and str(raw).strip() != "":
            fg_batch_max = int(raw)
    except (ValueError, TypeError):
        fg_batch_max = int(fg_workers)
    fg_batch_max = max(1, min(int(fg_batch_max), int(fg_workers), 8))

    fg_prep_workers = 0
    if cfg0 is not None:
        try:
            fg_prep_workers = safe_int(cfg0.get("IterationEngine", "InFlight_FGPrepWorkers", fallback="0"), 0)
        except (ValueError, TypeError):
            fg_prep_workers = 0
    raw = env_get("INFLIGHT_FG_PREP_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_prep_workers = int(raw)
        except (ValueError, TypeError):
            pass
    if fg_prep_workers <= 0:
        fg_prep_workers = default_worker_threads(inflight_limit=inflight_limit_i, kind="fg_prep")
    fg_prep_workers = max(1, min(int(fg_prep_workers), int(inflight_limit_i), 8))
    static_prep_max_inflight = _read_fg_static_prep_max_inflight(
        cfg0,
        fg_prep_workers=int(fg_prep_workers),
        inflight_limit=int(inflight_limit_i),
        cpu_prewarm_lookahead=int(cpu_prewarm_lookahead),
    )
    db_prefetch_workers = _read_db_prefetch_workers(cfg0, fg_prep_workers=int(fg_prep_workers))

    return NativeFGPipelineSettings(
        workers=int(fg_workers),
        batch_max=int(fg_batch_max),
        prep_workers=int(fg_prep_workers),
        ga_credit_budget=max(1, int(ga_credit_budget_cfg)),
        static_prep_max_inflight=int(static_prep_max_inflight),
        db_prefetch_workers=int(db_prefetch_workers),
    )


class NativeFGPipeline:
    """
    Host-side ForceGreats pipeline for native in-flight mode.

    The pipeline owns FG queueing, FG prep workers, FG worker submissions, and
    FG fairness credit. GPU execution still goes through the shared single owner.
    """

    def __init__(self, settings: NativeFGPipelineSettings) -> None:
        self.settings = settings
        self.pending: deque[_NativeSong] = deque()
        self.prep_inflight: deque[_NativeSong] = deque()
        self.futures: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
        self.ga_credit_budget = max(1, int(settings.ga_credit_budget))
        self.ga_credit = int(self.ga_credit_budget)
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(settings.workers)),
            thread_name_prefix="FG",
        )
        self.prep_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(settings.prep_workers)),
            thread_name_prefix="FGPrep",
        )

    @property
    def workers(self) -> int:
        return int(self.settings.workers)

    @property
    def batch_max(self) -> int:
        return int(self.settings.batch_max)

    @property
    def prep_workers(self) -> int:
        return int(self.settings.prep_workers)

    def queue(self, song: _NativeSong, *, now_s: float | None = None) -> None:
        runtime = getattr(song, 'runtime', song)
        self.pending.append(song)
        try:
            if not bool(getattr(song.runtime.fg, "fg_dynamic_prep_done", False)):
                song.runtime.fg.fg_dynamic_prep_done = False
        except AttributeError:
            pass
        try:
            if not isinstance(getattr(song.runtime.fg, "fg_queued_t0", None), (int, float)):
                runtime.fg.fg_queued_t0 = float(time.monotonic() if now_s is None else now_s)
        except (KeyError, TypeError, ValueError):
            pass

    def requeue_front(self, song: _NativeSong) -> None:
        self.pending.appendleft(song)

    def start_prep(
        self,
        song: _NativeSong,
        prep_fn: Callable[..., Any],
        *,
        gpu_client: GpuServiceClient | None,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> bool:
        runtime = getattr(song, 'runtime', song)
        if runtime.fg.fg_prep_future is not None:
            return False
        try:
            song.runtime.fg.fg_dynamic_prep_done = False
        except AttributeError:
            pass
        song.runtime.fg.fg_prep_submit_t0 = time.perf_counter()
        runtime.fg.fg_prep_future = self.prep_executor.submit(prep_fn, song, gpu_client=gpu_client)
        if register_future is not None:
            register_future(runtime.fg.fg_prep_future)
        self.prep_inflight.append(song)
        return True

    def active_prep_count(self) -> int:
        active = 0
        seen: set[int] = set()
        for song in self.prep_inflight:
            fut = getattr(song.runtime.fg, "fg_prep_future", None)
            if fut is None:
                continue
            try:
                fut_id = int(id(fut))
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:active_prep_count: {e}")
                fut_id = 0
            if fut_id and fut_id in seen:
                continue
            if fut_id:
                seen.add(fut_id)
            try:
                if fut.done():
                    continue
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:active_prep_count: {e}")
                continue
            active += 1
        return int(active)

    def has_active_prep(self) -> bool:
        if self.active_prep_count() > 0:
            return True
        for song in self.pending:
            fut = getattr(song.runtime.fg, "fg_prep_future", None)
            if fut is None:
                continue
            try:
                if not fut.done():
                    return True
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:has_active_prep: {e}")
                continue
        return False

    def finish_completed_prep(self) -> list[NativeFGPrepCompletion]:
        completions: list[NativeFGPrepCompletion] = []
        for song in list(self.prep_inflight):
            future = getattr(song.runtime.fg, "fg_prep_future", None)
            if future is None:
                self.prep_inflight.remove(song)
                completions.append(
                    NativeFGPrepCompletion(
                        song=song,
                        submit_t0=None,
                        cpu_seconds=None,
                        future_missing=True,
                    )
                )
                continue
            if not future.done():
                continue

            self.prep_inflight.remove(song)
            submit_t0 = getattr(song.runtime.fg, "fg_prep_submit_t0", None)
            cpu_seconds = getattr(song.runtime.fg, "cpu_fg_prep_s", None)
            error: Exception | None = None
            trace = ""
            try:
                if submit_t0 is not None:
                    song.runtime.fg.fg_prep_submit_t0 = None
                future.result()
                try:
                    song.runtime.fg.fg_dynamic_prep_done = True
                except Exception as e:
                    logger.debug(f"native_inflight_fg_pipeline:finish_completed_prep: {e}")
            except Exception as exc:
                error = exc
                trace = traceback.format_exc()
            finally:
                song.runtime.fg.fg_prep_future = None

            completions.append(
                NativeFGPrepCompletion(
                    song=song,
                    submit_t0=submit_t0,
                    cpu_seconds=cpu_seconds,
                    error=error,
                    trace=trace,
                )
            )
        return completions

    def active_static_prep_count(self, *external_song_groups: Iterable[_NativeSong]) -> int:
        active = 0
        seen_ids: set[int] = set()

        def _track(song: _NativeSong) -> None:
            nonlocal active
            try:
                song_id = int(id(song))
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:active_static_prep_count: {e}")
                return
            if song_id in seen_ids:
                return
            seen_ids.add(song_id)
            fut = getattr(song.runtime.fg, "fg_static_prep_future", None)
            if fut is None:
                return
            try:
                if fut.done():
                    return
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:active_static_prep_count: {e}")
                return
            active += 1

        for group in external_song_groups:
            for song in group:
                _track(song)
        for song in self.pending:
            _track(song)
        for song in self.prep_inflight:
            _track(song)
        for song, _future, _t_submit in self.futures:
            _track(song)
        return int(active)

    def static_prep_budget(self) -> int:
        if int(self.settings.static_prep_max_inflight) <= 0:
            return 0
        dynamic_fg_prep = max(0, int(len(self.prep_inflight)))
        spare_workers = max(0, int(self.prep_workers) - int(dynamic_fg_prep))
        return max(0, min(int(self.settings.static_prep_max_inflight), int(spare_workers)))

    def start_static_prep(
        self,
        song: _NativeSong,
        prep_fn: Callable[..., Any],
        *,
        external_song_groups: Iterable[Iterable[_NativeSong]] = (),
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> bool:
        if int(self.settings.static_prep_max_inflight) <= 0:
            return False
        if not bool(getattr(song.gpu_inputs, "manual_force_greats", False) or getattr(song.gpu_inputs, "force_greats_finder", False)):
            return False
        if getattr(song.runtime.fg, "fg_static_prep_future", None) is not None:
            return False
        if bool(getattr(song.runtime.fg, "fg_static_prep_done", False)):
            return False
        if int(self.active_static_prep_count(*external_song_groups)) >= int(self.static_prep_budget()):
            return False
        try:
            song.runtime.fg.fg_static_prep_submit_t0 = time.perf_counter()
            static_future = self.prep_executor.submit(prep_fn, song)
            song.runtime.fg.fg_static_prep_future = static_future
            if register_future is not None:
                register_future(static_future)
            return True
        except Exception as e:
            logger.debug(f"native_inflight_fg_pipeline:start_static_prep: {e}")
            try:
                song.runtime.fg.fg_static_prep_future = None
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:start_static_prep: {e}")
            return False

    def start_pending_prep(
        self,
        prep_fn: Callable[..., Any],
        *,
        gpu_client: GpuServiceClient | None,
        max_new: int | None = None,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> int:
        """
        Top up the dynamic FG-prep runway from pending FG songs.

        This keeps backlog/drain CPU prep in the prep executor instead of letting
        FG worker threads serialize on not-ready songs before each GPU burst.
        """
        budget = max(0, int(self.prep_workers) - int(self.active_prep_count()))
        if max_new is not None:
            budget = min(int(budget), max(0, int(max_new)))
        if budget <= 0:
            return 0

        started = 0
        for song in list(self.pending):
            if started >= budget:
                break
            if bool(getattr(song.runtime.fg, "fg_dynamic_prep_done", False)):
                continue
            if getattr(song.runtime.fg, "fg_prep_future", None) is not None:
                continue
            if self.start_prep(
                song,
                prep_fn,
                gpu_client=gpu_client,
                register_future=register_future,
            ):
                started += 1
        return int(started)

    def submit_warmup(
        self,
        warmup_fn: Callable[..., Any],
        calc_song: dict,
        ref_arrays: dict,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> concurrent.futures.Future:
        fut = self.prep_executor.submit(warmup_fn, calc_song, ref_arrays)
        if register_future is not None:
            register_future(fut)
        return fut

    def pop_next(self, *, allow_not_ready: bool) -> _NativeSong | None:
        """
        Pick a song for FG submission.

        Normally, only pop songs whose FG prep is complete. When slot pressure
        blocks GA, allow a not-yet-ready song so the FG worker can wait on prep
        instead of losing the job or stalling the owner loop.
        """
        for candidate in list(self.pending):
            runtime = getattr(candidate, 'runtime', candidate)
            fut = runtime.fg.fg_prep_future
            if fut is None:
                if not bool(getattr(candidate.runtime.fg, "fg_dynamic_prep_done", False)):
                    if not allow_not_ready:
                        continue
                    try:
                        self.pending.remove(candidate)
                    except ValueError:
                        pass
                    return candidate
                try:
                    self.pending.remove(candidate)
                except ValueError:
                    pass
                return candidate
            if allow_not_ready:
                try:
                    self.pending.remove(candidate)
                except ValueError:
                    pass
                return candidate
            try:
                if fut.done():
                    self.pending.remove(candidate)
                    return candidate
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:pop_next: {e}")
                continue
        return None

    def oldest_wait_s(self, now_s: float) -> float:
        if not self.pending:
            return 0.0
        oldest_t0 = None
        for candidate in self.pending:
            runtime = getattr(candidate, 'runtime', candidate)
            t0 = getattr(candidate.runtime.fg, "fg_queued_t0", None)
            if not isinstance(t0, (int, float)) or float(t0) <= 0.0:
                try:
                    runtime.fg.fg_queued_t0 = float(now_s)
                except (KeyError, TypeError, ValueError):
                    pass
                t0 = float(now_s)
            if oldest_t0 is None or float(t0) < float(oldest_t0):
                oldest_t0 = float(t0)
        if oldest_t0 is None:
            return 0.0
        return max(0.0, float(now_s) - float(oldest_t0))

    def ready_count(self) -> int:
        ready = 0
        for candidate in self.pending:
            runtime = getattr(candidate, 'runtime', candidate)
            fut = runtime.fg.fg_prep_future
            if fut is None:
                if not bool(getattr(candidate.runtime.fg, "fg_dynamic_prep_done", False)):
                    continue
                ready += 1
                continue
            try:
                if fut.done():
                    ready += 1
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:ready_count: {e}")
                continue
        return int(ready)

    def submit_job(
        self,
        run_fn: Callable[..., Any],
        song: _NativeSong,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
        **kwargs: Any,
    ) -> concurrent.futures.Future:
        try:
            getattr(song, 'runtime', song).fg.fg_queued_t0 = None
        except (KeyError, TypeError, ValueError):
            pass
        t_submit = time.perf_counter()
        future = self.executor.submit(run_fn, song, **kwargs)
        if register_future is not None:
            register_future(future)
        self.futures.append((song, future, t_submit))
        self.note_fg_submit()
        return future

    def run_job_sync(
        self,
        song: _NativeSong,
        *,
        gpu_client: GpuServiceClient,
        post_sender: _PostSender | None = None,
        progress_cb=None,
        progress_tracker: ProgressTracker | None = None,
    ) -> None:
        run_fg_job_sync(
            song,
            gpu_client=gpu_client,
            post_sender=post_sender,
            progress_cb=progress_cb,
            progress_tracker=progress_tracker,
        )

    def replace_futures(self, futures: deque[tuple[_NativeSong, concurrent.futures.Future, float]]) -> None:
        self.futures.clear()
        self.futures.extend(futures)

    def pop_completed_jobs(self) -> list[NativeFGJobCompletion]:
        completions: list[NativeFGJobCompletion] = []
        still_pending: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
        for song, future, submit_t0 in list(self.futures):
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:pop_completed_jobs: {e}")
                done = False
            if done:
                completions.append(
                    NativeFGJobCompletion(
                        song=song,
                        future=future,
                        submit_t0=float(submit_t0),
                    )
                )
            else:
                still_pending.append((song, future, submit_t0))
        self.replace_futures(still_pending)
        return completions

    def note_ga_submit(self) -> None:
        if self.pending:
            self.ga_credit = max(-int(self.ga_credit_budget), int(self.ga_credit) - 1)
        else:
            self.ga_credit = int(self.ga_credit_budget)

    def note_fg_submit(self) -> None:
        self.ga_credit = int(self.ga_credit_budget)

    def reset_credit_if_empty(self) -> None:
        if not self.pending:
            self.ga_credit = int(self.ga_credit_budget)

    def active_song_keys(self) -> set[str]:
        keys: set[str] = set()
        for song in self.pending:
            key = self._song_key(song)
            if key:
                keys.add(key)
        for song in self.prep_inflight:
            key = self._song_key(song)
            if key:
                keys.add(key)
        for song, _fut, _t_submit in self.futures:
            key = self._song_key(song)
            if key:
                keys.add(key)
        return keys

    def shutdown_fg(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def shutdown_prep(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.prep_executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    @staticmethod
    def _song_key(song: _NativeSong) -> str:
        try:
            return str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "")).strip()
        except (KeyError, TypeError, ValueError):
            return ""


def run_fg_job_sync(
    song: _NativeSong,
    *,
    gpu_client: GpuServiceClient,
    post_sender: _PostSender | None = None,
    progress_cb=None,
    progress_tracker: ProgressTracker | None = None,
) -> None:
    cpu_t0 = _thread_cpu_time_s()
    song_key = str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or "")
    active_fg_calc_song = _resolve_active_fg_calc_song(song)
    if not isinstance(active_fg_calc_song, dict):
        active_fg_calc_song = getattr(song.gpu_inputs, "calc_song", {})

    def _count_fg_group_meta_ready(candidates: Any) -> int:
        ready = 0
        for candidate in candidates or []:
            if not isinstance(candidate, dict):
                continue
            data = candidate.get("Data")
            if not isinstance(data, dict):
                continue
            if isinstance(data.get("_fg_group_meta"), dict):
                ready += 1
        return int(ready)

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="start",
            song_key=song_key,
            metrics={
                "had_prep_future": int(getattr(song.runtime.fg, "fg_prep_future", None) is not None),
                "ga_candidates": int(len(getattr(song.runtime.decode, "ga_candidates", None) or [])),
                "ga_candidates_group_meta_ready": int(_count_fg_group_meta_ready(getattr(song.runtime.decode, "ga_candidates", None))),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")
    fg_prep_future = getattr(song.runtime.fg, "fg_prep_future", None)
    if fg_prep_future is not None:
        prep_wait_t0 = time.perf_counter()
        try:
            fg_prep_future.result()
            try:
                song.runtime.fg.fg_dynamic_prep_done = True
            except AttributeError:
                pass
        except Exception as e:
            logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")
        finally:
            try:
                emit_profile_event(
                    component="inflight_fg_worker",
                    event="prep_wait",
                    song_key=song_key,
                    metrics={
                        "wait_ms": max(0.0, (time.perf_counter() - float(prep_wait_t0)) * 1000.0),
                    },
                )
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")
            song.runtime.fg.fg_prep_future = None

    if getattr(song.runtime.fg, "loadout_entries", None) is None:
        _prepare_fg_job_sync(song, gpu_client=gpu_client)
        try:
            song.runtime.fg.fg_dynamic_prep_done = True
        except AttributeError:
            pass

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="prep_ready",
            song_key=song_key,
            metrics={
                "loadout_entries": int(len(getattr(song.runtime.fg, "loadout_entries", None) or {}))
                if isinstance(getattr(song.runtime.fg, "loadout_entries", None), dict)
                else 0,
                "ga_candidates": int(len(getattr(song.runtime.decode, "ga_candidates", None) or [])),
                "ga_candidates_group_meta_ready": int(_count_fg_group_meta_ready(getattr(song.runtime.decode, "ga_candidates", None))),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")

    # Late non-blocking DB prefetch consume:
    # - If FG prep skipped DB rows because prefetch was still in-flight, harvest now if ready.
    # - Never block FG worker threads on SQLite here.
    if getattr(song.runtime.db, "db_loadouts_full", None) is None and getattr(song.runtime.db, "db_loadouts_future", None) is not None:
        fut = getattr(song.runtime.db, "db_loadouts_future", None)
        try:
            if fut.done():
                try:
                    db_rows = fut.result(timeout=0)
                    if isinstance(db_rows, list):
                        song.runtime.db.db_loadouts_full = db_rows
                except Exception as e:
                    logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")
                    song.runtime.db.db_loadouts_full = None
            else:
                # Best effort: avoid keeping stale prefetch work around if FG is already running.
                try:
                    fut.cancel()
                except Exception as e:
                    logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")
        except Exception as e:
            logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")
        finally:
            song.runtime.db.db_loadouts_future = None

    build_details = song.runtime.fg.fg_build_details
    if not callable(build_details):
        build_details = make_build_details_fn(
            getattr(song.gpu_inputs, "meta_primary_color", ""),
            getattr(song.gpu_inputs, "meta_secondary_color", ""),
            getattr(song.config, "effective_difficulty", ""),
        )
        try:
            song.runtime.fg.fg_build_details = build_details
        except AttributeError:
            pass

    # If FG prep built GA-only entries while DB prefetch was pending, merge DB rows now
    # without rebuilding the full GA union.
    db_loadouts_full = getattr(song.runtime.db, "db_loadouts_full", None)
    loadout_entries = getattr(song.runtime.fg, "loadout_entries", None)
    if db_loadouts_full is not None and not _loadout_entries_have_db_source(loadout_entries):
        if not isinstance(loadout_entries, dict):
            loadout_entries = {}
            song.runtime.fg.loadout_entries = loadout_entries
        merge_db_loadouts_into_entries(loadout_entries, db_loadouts_full)

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="pre_dispatch",
            song_key=song_key,
            metrics={
                "loadout_entries": int(len(getattr(song.runtime.fg, "loadout_entries", None) or {}))
                if isinstance(getattr(song.runtime.fg, "loadout_entries", None), dict)
                else 0,
                "ga_candidates": int(len(getattr(song.runtime.decode, "ga_candidates", None) or [])),
                "ga_candidates_group_meta_ready": int(_count_fg_group_meta_ready(getattr(song.runtime.decode, "ga_candidates", None))),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")

    fg_solver_mode = str((getattr(song.gpu_inputs, "cfg_data", None) or {}).get("fg_solver_mode") or "finder").strip().lower()
    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="dispatch_start",
            song_key=song_key,
            metrics={
                "solver_mode": str(fg_solver_mode),
                "song_slot": int(getattr(song.runtime, "song_slot", 0) or 0),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")
    if fg_solver_mode == "off":
        fg_variants = []
    elif bool(getattr(song.gpu_inputs, "force_greats_finder", False)):
        fg_variants = score_native_ga_force_greats(
            loadout_entries=getattr(song.runtime.fg, "loadout_entries", None) or {},
            ga_candidates=getattr(song.runtime.decode, "ga_candidates", None)
            if bool(getattr(song.runtime.fg, "fg_direct_ga_candidates", False))
            else None,
            calc_song=active_fg_calc_song,
            ref_arrays=getattr(song.gpu_inputs, "ref_arrays", None),
            default_selected_color=getattr(song.gpu_inputs, "meta_primary_color", ""),
            primary_color=getattr(song.gpu_inputs, "meta_primary_color", ""),
            secondary_color=getattr(song.gpu_inputs, "meta_secondary_color", ""),
            minis_by_name=getattr(song.gpu_inputs, "minis_by_name", None),
            registry=getattr(song.gpu_inputs, "registry", None)
            if bool(getattr(song.runtime.fg, "fg_direct_ga_candidates", False))
            else None,
            search_radius=getattr(song.runtime.fg, "fg_search_radius", None),
        )
    else:
        fg_variants = process_force_greats(
            getattr(song.runtime.fg, "loadout_entries", None) or {},
            bool(getattr(song.gpu_inputs, "manual_force_greats", False)),
            bool(getattr(song.gpu_inputs, "force_greats_finder", False)),
            getattr(song.gpu_inputs, "force_greats_config", None),
            active_fg_calc_song,
            getattr(song.gpu_inputs, "ref_arrays", None),
            getattr(song.gpu_inputs, "meta_primary_color", ""),
            build_details,
            use_gpu=True,
            fg_search_radius=getattr(song.runtime.fg, "fg_search_radius", None),
            perf_timing=_truthy(env_get("PERF_TIMING", "0")),
            gpu_client=gpu_client,
            ga_candidates=getattr(song.runtime.decode, "ga_candidates", None) if bool(getattr(song.runtime.fg, "fg_direct_ga_candidates", False)) else None,
            ga_registry=getattr(song.gpu_inputs, "registry", None) if bool(getattr(song.runtime.fg, "fg_direct_ga_candidates", False)) else None,
        )

    song.runtime.fg.fg_variants = list(fg_variants or [])
    try:
        song.runtime.fg.cpu_fg_run_s = max(0.0, _thread_cpu_time_s() - float(cpu_t0))
    except AttributeError:
        pass
    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="dispatch_done",
            song_key=song_key,
            metrics={
                "fg_variants": int(len(getattr(song.runtime.fg, "fg_variants", None) or [])),
                "solver_mode": str(fg_solver_mode),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")

    if progress_cb is not None:
        fg_record_info = None
        try:
            key = str(getattr(song.config, "db_key", "") or "").strip()
            prev_best_score = safe_int(getattr(song.runtime.db, "db_best_score", 0), 0)
            prev_best_fg = safe_int(getattr(song.runtime.db, "db_best_fg_score", 0), 0)
            baseline_valid = bool(getattr(song.runtime.db, "db_baseline_valid", True))
            if progress_tracker is not None and key:
                prev_best_score, prev_best_fg, baseline_valid = progress_tracker.snapshot(key)

            fg_record_info = evaluate_progress_record_update(
                getattr(song.runtime.decode, "best_data", None) or {},
                {"score": int(prev_best_score)},
                getattr(song.runtime.fg, "fg_variants", None) or [],
                db_best_fg_score=int(prev_best_fg),
                baseline_valid=bool(baseline_valid),
                fg_only=True,
            )
        except (ValueError, TypeError, KeyError):
            fg_record_info = None
        if isinstance(fg_record_info, dict):
            fg_record_info = dict(fg_record_info)
            if fg_record_info.get("is_fg_better") and progress_tracker is not None:
                try:
                    best_fg_new = safe_int(fg_record_info.get("best_fg_score_run", 0), 0)
                except (ValueError, TypeError):
                    best_fg_new = 0
                if best_fg_new > 0:
                    key = str(getattr(song.config, "db_key", "") or "").strip()
                    if key:
                        progress_tracker.update(
                            key,
                            best_fg=best_fg_new,
                            mark_valid=bool(baseline_valid),
                        )
            try:
                progress_cb(completed_delta=0, failed_delta=0, record_info=fg_record_info)
            except Exception as e:
                logger.debug(f"native_inflight_fg_pipeline:_count_fg_group_meta_ready: {e}")

    if post_sender is not None:
        post_sender.send(
            {
                "_fg_update": True,
                "song": getattr(song.config, "song_name", ""),
                "db_key": getattr(song.config, "db_key", ""),
                "use_evo_db": bool(getattr(song.config, "use_evo_db", True)),
                "persist_entries": _build_fg_persist_entries(song),
                # Allow downstream post-process / async DB hooks (e.g., TeamBuff tier leaderboards)
                # to run without requiring ForceGreatsDebug (which ships large objects).
                "file_path": getattr(song.config, "fp", ""),
                "cfg_dict": getattr(song.config, "cfg_dict", None),
            }
        )


def score_fg_inside_ga(
    song: _NativeSong,
    *,
    gpu_client: GpuServiceClient,
) -> None:
    if not fg_enabled_for_song(song):
        return
    run_fg_job_sync(
        song,
        gpu_client=gpu_client,
        post_sender=None,
        progress_cb=None,
        progress_tracker=None,
    )
    if getattr(song.runtime.fg, "fg_variants", None) is None:
        song.runtime.fg.fg_variants = []
