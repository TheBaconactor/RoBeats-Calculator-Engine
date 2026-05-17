from __future__ import annotations

import concurrent.futures
import time
import traceback
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable
import logging

from gear_optimizer.core.utils import safe_int
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
from gear_optimizer.helpers.song_helpers.force_greats.native_ga_variants import (
    build_native_fg_candidate_surface,
    score_native_fg_candidate_surface,
)
from gear_optimizer.solver.inflight_utils import _truthy
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.native_inflight_config import read_db_prefetch_workers, read_fg_static_prep_max_inflight


from gear_optimizer.solver.native_inflight_config import NativeSong

if TYPE_CHECKING:
    from gear_optimizer.solver.native_inflight_lifecycle import PostSender, ProgressTracker

logger = logging.getLogger(__name__)


def evaluate_fg_progress_record_update(song: NativeSong, progress_tracker):
    from gear_optimizer.solver.native_inflight_lifecycle import evaluate_fg_progress_record_update as _impl

    return _impl(song, progress_tracker)


def ensure_fg_build_details(song: NativeSong):
    from gear_optimizer.solver.native_inflight_orchestrator import ensure_fg_build_details as _impl

    return _impl(song)


def build_fg_persist_entries(song: NativeSong):
    from gear_optimizer.solver.native_inflight_orchestrator import build_fg_persist_entries as _impl

    return _impl(song)


def build_fg_update_payload(song: NativeSong, *, persist_entries: list[dict]):
    from gear_optimizer.solver.native_inflight_orchestrator import build_fg_update_payload as _impl

    return _impl(song, persist_entries=persist_entries)
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
    song: NativeSong
    submit_t0: float | None
    cpu_seconds: float | None
    error: Exception | None = None
    trace: str = ""
    future_missing: bool = False


@dataclass(frozen=True)
class NativeFGJobCompletion:
    song: NativeSong
    future: concurrent.futures.Future
    submit_t0: float


def count_fg_group_meta_ready(candidates: Any) -> int:
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
    static_prep_max_inflight = read_fg_static_prep_max_inflight(
        cfg0,
        fg_prep_workers=int(fg_prep_workers),
        inflight_limit=int(inflight_limit_i),
        cpu_prewarm_lookahead=int(cpu_prewarm_lookahead),
    )
    db_prefetch_workers = read_db_prefetch_workers(cfg0, fg_prep_workers=int(fg_prep_workers))

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
        self.pending: deque[NativeSong] = deque()
        self.prep_inflight: deque[NativeSong] = deque()
        self.futures: deque[tuple[NativeSong, concurrent.futures.Future, float]] = deque()
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

    def queue(self, song: NativeSong, *, now_s: float | None = None) -> None:
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

    def requeue_front(self, song: NativeSong) -> None:
        self.pending.appendleft(song)

    def start_prep(
        self,
        song: NativeSong,
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
                logger.debug(f"native_inflight_pipeline:active_prep_count: {e}")
                fut_id = 0
            if fut_id and fut_id in seen:
                continue
            if fut_id:
                seen.add(fut_id)
            try:
                if fut.done():
                    continue
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:active_prep_count: {e}")
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
                logger.debug(f"native_inflight_pipeline:has_active_prep: {e}")
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
                    logger.debug(f"native_inflight_pipeline:finish_completed_prep: {e}")
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

    def active_static_prep_count(self, *external_song_groups: Iterable[NativeSong]) -> int:
        active = 0
        seen_ids: set[int] = set()

        def _track(song: NativeSong) -> None:
            nonlocal active
            try:
                song_id = int(id(song))
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:active_static_prep_count: {e}")
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
                logger.debug(f"native_inflight_pipeline:active_static_prep_count: {e}")
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
        song: NativeSong,
        prep_fn: Callable[..., Any],
        *,
        external_song_groups: Iterable[Iterable[NativeSong]] = (),
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> bool:
        if int(self.settings.static_prep_max_inflight) <= 0:
            return False
        if not bool(getattr(song.gpu_inputs, "manual_force_greats", False)):
            return False
        if getattr(song.runtime.fg, "fg_static_prep_future", None) is not None:
            return False
        if bool(getattr(song.runtime.fg, "fg_static_prep_done", False)):
            return False
        if int(self.active_static_prep_count(*external_song_groups)) >= int(self.static_prep_budget()):
            return False
        try:
            static_future = self.prep_executor.submit(prep_fn, song)
            song.runtime.fg.fg_static_prep_future = static_future
            if register_future is not None:
                register_future(static_future)
            return True
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:start_static_prep: {e}")
            try:
                song.runtime.fg.fg_static_prep_future = None
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:start_static_prep: {e}")
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


    def pop_next(self, *, allow_not_ready: bool) -> NativeSong | None:
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
                logger.debug(f"native_inflight_pipeline:pop_next: {e}")
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
                logger.debug(f"native_inflight_pipeline:ready_count: {e}")
                continue
        return int(ready)

    def submit_job(
        self,
        run_fn: Callable[..., Any],
        song: NativeSong,
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


    def replace_futures(self, futures: deque[tuple[NativeSong, concurrent.futures.Future, float]]) -> None:
        self.futures.clear()
        self.futures.extend(futures)

    def pop_completed_jobs(self) -> list[NativeFGJobCompletion]:
        completions: list[NativeFGJobCompletion] = []
        still_pending: deque[tuple[NativeSong, concurrent.futures.Future, float]] = deque()
        for song, future, submit_t0 in list(self.futures):
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:pop_completed_jobs: {e}")
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
    def _song_key(song: NativeSong) -> str:
        try:
            return str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "")).strip()
        except (KeyError, TypeError, ValueError):
            return ""


def run_fg_job_sync(
    song: NativeSong,
    *,
    gpu_client: GpuServiceClient,
    post_sender: PostSender | None = None,
    progress_cb=None,
    progress_tracker: ProgressTracker | None = None,
) -> None:
    cpu_t0 = thread_cpu_time_s()
    song_key = str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or "")
    active_fg_calc_song = resolve_active_fg_calc_song(song)
    if not isinstance(active_fg_calc_song, dict):
        active_fg_calc_song = getattr(song.gpu_inputs, "calc_song", {})

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="start",
            song_key=song_key,
            metrics={
                "had_prep_future": int(getattr(song.runtime.fg, "fg_prep_future", None) is not None),
                "ga_candidates": int(len(getattr(song.runtime.decode, "ga_candidates", None) or [])),
                "ga_candidates_group_meta_ready": int(count_fg_group_meta_ready(getattr(song.runtime.decode, "ga_candidates", None))),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")
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
            logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")
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
                logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")
            song.runtime.fg.fg_prep_future = None

    if getattr(song.runtime.fg, "loadout_entries", None) is None:
        prepare_fg_job_sync(song, gpu_client=gpu_client)
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
                "ga_candidates_group_meta_ready": int(count_fg_group_meta_ready(getattr(song.runtime.decode, "ga_candidates", None))),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")

    build_details = ensure_fg_build_details(song)

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
                "ga_candidates_group_meta_ready": int(count_fg_group_meta_ready(getattr(song.runtime.decode, "ga_candidates", None))),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")

    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="dispatch_start",
            song_key=song_key,
            metrics={
                "song_slot": int(getattr(song.runtime, "song_slot", 0) or 0),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")
    if not bool(getattr(song.gpu_inputs, "manual_force_greats", False)):
        if getattr(song.runtime.fg, "fg_candidate_surface", None) is None:
            prepare_fg_job_sync(song, gpu_client=gpu_client)
            try:
                song.runtime.fg.fg_dynamic_prep_done = True
            except AttributeError:
                pass
        fg_variants = score_native_fg_candidate_surface(
            surface=getattr(song.runtime.fg, "fg_candidate_surface", None),
            loadout_entries=getattr(song.runtime.fg, "loadout_entries", None) or {},
            calc_song=active_fg_calc_song,
            ref_arrays=getattr(song.gpu_inputs, "ref_arrays", None),
            search_radius=getattr(song.runtime.fg, "fg_search_radius", None),
            gpu_client=gpu_client,
        )
    else:
        fg_variants = process_force_greats(
            getattr(song.runtime.fg, "loadout_entries", None) or {},
            bool(getattr(song.gpu_inputs, "manual_force_greats", False)),
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
        song.runtime.fg.cpu_fg_run_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    except AttributeError:
        pass
    try:
        emit_profile_event(
            component="inflight_fg_worker",
            event="dispatch_done",
            song_key=song_key,
            metrics={
                "fg_variants": int(len(getattr(song.runtime.fg, "fg_variants", None) or [])),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")

    if progress_cb is not None:
        fg_record_info = evaluate_fg_progress_record_update(song, progress_tracker)
        if isinstance(fg_record_info, dict):
            song.runtime.db.record_info = fg_record_info
            try:
                progress_cb(completed_delta=0, failed_delta=0, record_info=fg_record_info)
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:_count_fg_group_meta_ready: {e}")
    else:
        fg_record_info = evaluate_fg_progress_record_update(song, progress_tracker)
        if isinstance(fg_record_info, dict):
            song.runtime.db.record_info = fg_record_info

    if post_sender is not None:
        post_sender.send(build_fg_update_payload(song, persist_entries=build_fg_persist_entries(song)))

# ---- merged from native_inflight_pipeline.py ----


from dataclasses import dataclass
import logging




logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GADecodeCompletion:
    song: NativeSong
    future: concurrent.futures.Future
    submit_t0: float | None


@dataclass(frozen=True)
class GARunCompletion:
    song: NativeSong
    future: concurrent.futures.Future


class GADecodeQueue:
    def __init__(self, *, max_workers: int) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="GADecode",
        )
        self.inflight: deque[NativeSong] = deque()

    def submit(
        self,
        song: NativeSong,
        ga_result: Any,
        decode_fn: Callable[[NativeSong, Any], Any],
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> concurrent.futures.Future:
        song.runtime.decode.decode_submit_t0 = time.perf_counter()
        future = self.executor.submit(decode_fn, song, ga_result)
        song.runtime.decode.decode_future = future
        register_future(future)
        self.inflight.append(song)
        return future

    def pop_completed(self) -> list[GADecodeCompletion]:
        completions: list[GADecodeCompletion] = []
        for song in list(self.inflight):
            future = song.runtime.decode.decode_future
            if future is None:
                continue
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:pop_completed: {e}")
                done = False
            if not done:
                continue
            self.inflight.remove(song)
            completions.append(
                GADecodeCompletion(
                    song=song,
                    future=future,
                    submit_t0=getattr(song.runtime.decode, "decode_submit_t0", None),
                )
            )
        return completions

    def cancel_all(self) -> None:
        for song in list(self.inflight):
            try:
                if song.runtime.decode.decode_future is not None:
                    song.runtime.decode.decode_future.cancel()
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:cancel_all: {e}")

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)


class InflightGAPipeline:
    """Owns GA request payload assembly and per-song GPU slot bookkeeping."""

    def __init__(self) -> None:
        self.inflight: deque[NativeSong] = deque()

    @staticmethod
    def reserve_slot(song: NativeSong, slot_pool: Any) -> int:
        if int(song.runtime.song_slot or 0) <= 0:
            song.runtime.song_slot = int(slot_pool.acquire())
        try:
            song.gpu_inputs.calc_song["_gpu_song_slot"] = int(song.runtime.song_slot)
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:reserve_slot: {e}")
        return int(song.runtime.song_slot)

    @staticmethod
    def release_slot(song: NativeSong, slot_pool: Any) -> None:
        song_slot = int(song.runtime.song_slot or 0)
        if song_slot > 0:
            slot_pool.release(song_slot)
        song.runtime.song_slot = 0
        try:
            if isinstance(song.gpu_inputs.calc_song, dict):
                song.gpu_inputs.calc_song.pop("_gpu_song_slot", None)
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:release_slot: {e}")

    @staticmethod
    def prepare_submit(song: NativeSong) -> None:
        song.runtime.ga.ga_submit_t0 = time.perf_counter()

    @staticmethod
    def build_payload(song: NativeSong) -> dict[str, Any]:
        return {
            "calc_song": song.gpu_inputs.calc_song,
            "ref_arrays": song.gpu_inputs.ref_arrays,
            "song_slot": int(song.runtime.song_slot),
            "item_stats": song.gpu_inputs.item_stats,
            "slot_start": song.gpu_inputs.slot_start,
            "slot_count": song.gpu_inputs.slot_count,
            "base_fixed_stats_arr": song.gpu_inputs.base_fixed_stats_arr,
            "initial_populations": song.runtime.ga.ga_initial_populations,
            "num_runs": int(song.gpu_inputs.num_runs),
            "n_genomes": int(song.gpu_inputs.n_genomes),
            "init_heuristic_topk": song.gpu_inputs.init_heuristic_topk,
            "init_heuristic_k": int(song.gpu_inputs.init_heuristic_k),
            "init_heuristic_copies": int(song.gpu_inputs.init_heuristic_copies),
            "n_generations": int(song.gpu_inputs.gens_per_run),
            "elite_count": int(song.gpu_inputs.elite_count),
            "mutation_rate": float(song.gpu_inputs.mutation_rate),
            "immigrant_rate": float(song.gpu_inputs.immigrant_rate),
            "tournament_k": int(song.gpu_inputs.tournament_k),
            "color_flags": dict(song.gpu_inputs.color_flags),
            "cfg_data": dict(song.gpu_inputs.cfg_data),
            "ga_seed": song.config.ga_seed,
        }

    @staticmethod
    def mark_submitted(song: NativeSong, future: Any) -> None:
        song.runtime.ga.ga_future = future
        song.runtime.ga.ga_initial_populations = None

    def track_submitted(
        self,
        song: NativeSong,
        future: concurrent.futures.Future,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> None:
        self.mark_submitted(song, future)
        register_future(song.runtime.ga.ga_future)
        self.inflight.append(song)

    def pop_completed_runs(self) -> list[GARunCompletion]:
        completions: list[GARunCompletion] = []
        for song in list(self.inflight):
            future = song.runtime.ga.ga_future
            if future is None:
                continue
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:pop_completed_runs: {e}")
                done = False
            if not done:
                continue
            self.inflight.remove(song)
            completions.append(GARunCompletion(song=song, future=future))
        return completions

    @staticmethod
    def store_decode_result(song: NativeSong, decode_result: tuple[Any, Any, Any, Any]) -> None:
        best_data, best_gear, best_minis, ga_candidates = decode_result
        song.runtime.decode.best_data = best_data
        song.runtime.decode.best_gear = best_gear
        song.runtime.decode.best_minis = best_minis
        song.runtime.decode.ga_candidates = list(ga_candidates or [])
        song.runtime.decode.ga_persistence_candidates = list(ga_candidates or [])

# ---- merged from native_inflight_pipeline.py ----


import json
import logging
import os
import threading
from typing import Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit, read_fg_search_radius
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.helpers.song_helpers.force_greats.entry_utils import build_fg_group_meta
from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_caches import get_cached_chart_scorer
from gear_optimizer.helpers.song_helpers.database_context import resolve_database_baseline_team_buff
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.data.song_io import clone_calc_song

from gear_optimizer.solver.analytical_fg import create_chart_scorer_from_calc_song
from gear_optimizer.solver.scoring.stats_scoring import fg_baseline_params
from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload

logger = logging.getLogger(__name__)

_FG_FINDER_RUNTIME_WARMED = False
_FG_FINDER_RUNTIME_WARM_LOCK = threading.Lock()
_FG_RUNTIME_CALC_SONG_KEYS = ("_gpu_song_slot",)


def thread_cpu_time_s() -> float:
    """Best-effort per-thread CPU timer for CPU-side stage profiling."""
    try:
        return float(time.thread_time())
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:thread_cpu_time_s: {e}")
        return 0.0


def _sync_fg_runtime_calc_song_keys(source_calc_song: Any, target_calc_song: Any) -> None:
    if not isinstance(source_calc_song, dict) or not isinstance(target_calc_song, dict):
        return
    for key in _FG_RUNTIME_CALC_SONG_KEYS:
        if key in source_calc_song:
            target_calc_song[key] = source_calc_song.get(key)
        else:
            target_calc_song.pop(key, None)


def resolve_active_fg_calc_song(song: NativeSong) -> dict | None:
    calc_song = getattr(song.gpu_inputs, "calc_song", None)
    if not isinstance(calc_song, dict):
        return None

    runtime = getattr(song, 'runtime', song)
    fg_state = getattr(runtime, "fg", None)
    fg_calc_song = getattr(fg_state, "fg_calc_song", None)
    if not isinstance(fg_calc_song, dict):
        try:
            fg_calc_song = clone_calc_song(calc_song)
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:resolve_active_fg_calc_song: {e}")
            fg_calc_song = {
                "metadata": dict(calc_song.get("metadata", {}) or {}),
                "song_data": dict(calc_song.get("song_data", {}) or {}),
            }
    try:
        from gear_optimizer.solver.timing_envelope import apply_timing_envelope

        apply_timing_envelope(fg_calc_song)
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:resolve_active_fg_calc_song: {e}")
        return calc_song

    _sync_fg_runtime_calc_song_keys(calc_song, fg_calc_song)
    try:
        if fg_state is not None:
            fg_state.fg_calc_song = fg_calc_song
    except AttributeError:
        pass
    return fg_calc_song


def _maybe_prewarm_fg_chart_scorer(song: NativeSong) -> None:
    """
    Precompute the expensive per-song AnalyticalFGScorer during FG prep.

    This moves one-time per-song CPU work out of the FG dispatch pre-first-submit window so
    the GPU stays fed when FG work exists.

    Safe-by-default:
    - Only runs for GPU finder when chart prewarm is explicitly enabled.
    - Uses the shared LRU cache, so the later dispatch sees a cheap cache hit.
    """
    try:
        # Prewarming can be expensive on some songs; keep it opt-in so FG prep
        # doesn't stall GA->FG readiness by default.
        if not _truthy(env_get("INFLIGHT_FG_CHART_PREWARM", "0")):
            return
        if bool(getattr(song.gpu_inputs, "manual_force_greats", False)):
            return
        calc_song = resolve_active_fg_calc_song(song)
        ref_arrays = getattr(song.gpu_inputs, "ref_arrays", None)
        if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
            return
        if bool(getattr(song.runtime.prep, "fg_chart_scorer_prewarmed", False)):
            return

        get_cached_chart_scorer(calc_song, ref_arrays, create_chart_scorer_from_calc_song)
        song.runtime.prep.fg_chart_scorer_prewarmed = True
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_maybe_prewarm_fg_chart_scorer: {e}")
        return






class InFlightStageProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None = None) -> None:
        self.enabled = bool(enabled)
        self.out_path = out_path
        self._t0 = time.perf_counter()
        self._stage: dict[str, dict[str, Any]] = {}
        self._song: dict[str, dict[str, float]] = {}
        self._allow_prefixes = self._parse_prefixes(env_get("INFLIGHT_STAGE_PROFILE_PREFIX", ""))
        if _truthy(env_get("INFLIGHT_STAGE_PROFILE_FG_ONLY", "0")) and not self._allow_prefixes:
            # Convenience mode: only record FG-related stages (and the "underfed" wait marker that indicates
            # CPU-side bubbles while no GPU work is in flight).
            self._allow_prefixes = ("fg_", "underfed_wait")

    @staticmethod
    def _parse_prefixes(raw: Any) -> tuple[str, ...]:
        prefixes: list[str] = []
        for part in str(raw or "").split(","):
            part = str(part).strip()
            if part:
                prefixes.append(part)
        return tuple(prefixes)

    def record(self, stage: str, seconds: float, *, cpu_seconds: float | None = None, song: str | None = None) -> None:
        if not self.enabled:
            return
        allow = self._allow_prefixes
        if allow and not any(str(stage).startswith(p) for p in allow):
            return
        try:
            seconds = float(seconds)
        except (ValueError, TypeError):
            return
        if seconds < 0:
            return

        if cpu_seconds is not None:
            try:
                cpu_seconds = float(cpu_seconds)
            except (ValueError, TypeError):
                cpu_seconds = None
            if cpu_seconds is not None and cpu_seconds < 0:
                cpu_seconds = None

        entry = self._stage.get(stage)
        if entry is None:
            entry = {
                "count": 0,
                "total_s": 0.0,
                "max_s": 0.0,
                "samples_s": [],
                "cpu_total_s": 0.0,
                "cpu_max_s": 0.0,
                "cpu_samples_s": [],
            }
            self._stage[stage] = entry
        entry["count"] = int(entry["count"]) + 1
        entry["total_s"] = float(entry["total_s"]) + seconds
        entry["max_s"] = max(float(entry["max_s"]), seconds)
        try:
            entry["samples_s"].append(seconds)
        except (KeyError, TypeError, AttributeError):
            pass

        if cpu_seconds is not None:
            entry["cpu_total_s"] = float(entry.get("cpu_total_s", 0.0) or 0.0) + float(cpu_seconds)
            entry["cpu_max_s"] = max(float(entry.get("cpu_max_s", 0.0) or 0.0), float(cpu_seconds))
            try:
                entry["cpu_samples_s"].append(float(cpu_seconds))
            except (KeyError, TypeError, AttributeError):
                pass

        if song:
            per_song = self._song.get(song)
            if per_song is None:
                per_song = {}
                self._song[song] = per_song
            per_song[stage] = float(per_song.get(stage, 0.0)) + seconds
            if cpu_seconds is not None:
                per_song[f"{stage}_cpu"] = float(per_song.get(f"{stage}_cpu", 0.0)) + float(cpu_seconds)

    @staticmethod
    def _quantile(samples: list[float], p: float) -> float:
        if not samples:
            return 0.0
        xs = sorted(float(x) for x in samples)
        n = len(xs)
        if n == 1:
            return xs[0]
        idx = int(round(float(p) * (n - 1)))
        idx = max(0, min(n - 1, idx))
        return xs[idx]

    def summary(self) -> dict[str, Any]:
        if not self.enabled:
            return {}
        total_wall = time.perf_counter() - self._t0
        stages: dict[str, Any] = {}
        for name, entry in self._stage.items():
            samples = entry.get("samples_s") or []
            cpu_samples = entry.get("cpu_samples_s") or []
            stages[name] = {
                "count": int(entry.get("count", 0) or 0),
                "total_s": float(entry.get("total_s", 0.0) or 0.0),
                "max_s": float(entry.get("max_s", 0.0) or 0.0),
                "p50_s": self._quantile(samples, 0.50),
                "p95_s": self._quantile(samples, 0.95),
                "cpu_total_s": float(entry.get("cpu_total_s", 0.0) or 0.0),
                "cpu_max_s": float(entry.get("cpu_max_s", 0.0) or 0.0),
                "cpu_p50_s": self._quantile(cpu_samples, 0.50),
                "cpu_p95_s": self._quantile(cpu_samples, 0.95),
            }
        return {"total_wall_s": float(total_wall), "stages": stages, "songs": self._song}

    def emit(self) -> None:
        if not self.enabled:
            return
        summary = self.summary()
        stages = summary.get("stages") or {}
        ranked = sorted(stages.items(), key=lambda kv: float(kv[1].get("total_s", 0.0) or 0.0), reverse=True)
        logger.debug("[InFlight][StageProfile] total_wall_s=%.3f", float(summary.get("total_wall_s", 0.0) or 0.0))
        for name, info in ranked[:10]:
            logger.debug(
                "[InFlight][StageProfile] %-12s total=%8.3fs cpu=%8.3fs p50=%6.3fs p95=%6.3fs max=%6.3fs n=%s",
                name,
                float(info.get("total_s", 0.0) or 0.0),
                float(info.get("cpu_total_s", 0.0) or 0.0),
                float(info.get("p50_s", 0.0) or 0.0),
                float(info.get("p95_s", 0.0) or 0.0),
                float(info.get("max_s", 0.0) or 0.0),
                int(info.get("count", 0) or 0),
            )

        ranked_cpu = sorted(stages.items(), key=lambda kv: float(kv[1].get("cpu_total_s", 0.0) or 0.0), reverse=True)
        if ranked_cpu:
            logger.debug("[InFlight][CpuProfile] top_cpu_s")
            for name, info in ranked_cpu[:10]:
                cpu_total = float(info.get("cpu_total_s", 0.0) or 0.0)
                if cpu_total <= 0.0:
                    continue
                logger.debug(
                    "[InFlight][CpuProfile] %-12s cpu_total=%8.3fs p50=%6.3fs p95=%6.3fs max=%6.3fs n=%s",
                    name,
                    cpu_total,
                    float(info.get("cpu_p50_s", 0.0) or 0.0),
                    float(info.get("cpu_p95_s", 0.0) or 0.0),
                    float(info.get("cpu_max_s", 0.0) or 0.0),
                    int(info.get("count", 0) or 0),
                )

        out_path = str(self.out_path or "").strip()
        if not out_path:
            return
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except (OSError, IOError):
            pass
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, sort_keys=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass




def _prewarm_fg_baseline_point(calc_song: dict, ref_arrays: dict) -> None:
    if not calc_song or not ref_arrays:
        return
    try:
        fg_baseline_params({"Fever Time": 0, "Fever Fill Rate": 0}, calc_song, ref_arrays, prefer_grid=False)
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_prewarm_fg_baseline_point: {e}")


def _prewarm_timeline_frontier_payload(calc_song: dict, ref_arrays: dict) -> None:
    if not calc_song or not ref_arrays:
        return
    try:
        from gear_optimizer.solver.taichi_gem.api.timeline import prewarm_timeline_frontier_payload

        prewarm_timeline_frontier_payload(calc_song, ref_arrays)
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:_prewarm_timeline_frontier_payload: {e}")


def run_cpu_prewarm_for_song(song: NativeSong) -> None:
    calc_song = getattr(song.runtime.fg, "fg_calc_song", None) or getattr(song.gpu_inputs, "calc_song", None)
    ref_arrays = getattr(song.gpu_inputs, "ref_arrays", None)
    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict) or not ref_arrays:
        return

    _prewarm_timeline_frontier_payload(calc_song, ref_arrays)

    if not bool(getattr(song.gpu_inputs, "manual_force_greats", False)):
        _prewarm_fg_baseline_point(calc_song, ref_arrays)


def _warmup_fg_finder_runtime(
    calc_song: dict, ref_arrays: dict, *, gpu_client: Optional[GpuServiceClient] = None
) -> None:
    global _FG_FINDER_RUNTIME_WARMED
    if _FG_FINDER_RUNTIME_WARMED:
        return
    if not calc_song or not ref_arrays:
        return
    with _FG_FINDER_RUNTIME_WARM_LOCK:
        if _FG_FINDER_RUNTIME_WARMED:
            return
        try:
            from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_async import (
                plan_fg_async_threshold_flush,
                resolve_fg_async_batching_settings,
                warmup_force_greats_finder_runtime_imports,
            )

            warmup_force_greats_finder_runtime_imports()

            _ = (
                plan_fg_async_threshold_flush,
                resolve_fg_async_batching_settings,
                warmup_force_greats_finder_runtime_imports,
            )
            song_slot = 0
            try:
                if isinstance(calc_song, dict):
                    song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)
            except (ValueError, TypeError, KeyError):
                song_slot = 0
            resolve_fg_async_batching_settings(
                gpu_client=gpu_client,
                song_slot=int(song_slot),
                perf=False,
            )
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:_warmup_fg_finder_runtime: {e}")
            return
        _FG_FINDER_RUNTIME_WARMED = True


def read_fg_group_meta_prime_settings() -> tuple[int, bool, int]:
    prime_group_meta_limit = 0
    prime_group_meta_limit_explicit = False
    try:
        raw = env_get("INFLIGHT_FG_GROUP_META_PRIME_LIMIT")
        if raw is not None and str(raw).strip() != "":
            prime_group_meta_limit = int(raw)
            prime_group_meta_limit_explicit = True
    except (ValueError, TypeError):
        prime_group_meta_limit = 0
        prime_group_meta_limit_explicit = False

    return (
        max(0, min(int(prime_group_meta_limit), 512)),
        bool(prime_group_meta_limit_explicit),
        0,
    )


def _default_fg_group_meta_prime_limit(max_candidates: int) -> int:
    try:
        raw = env_get("INFLIGHT_FG_GROUP_META_AUTO_PRIME_CANDIDATE_LIMIT")
        if raw is not None and str(raw).strip() != "":
            return max(0, min(int(raw), int(max_candidates), 512))
    except (ValueError, TypeError):
        pass
    return max(0, min(8, int(max_candidates), 512))


def collect_fg_group_meta_payload(song: NativeSong, *, limit: int, start_index: int = 0) -> dict[int, dict]:
    ga_candidates = getattr(song.runtime.decode, "ga_candidates", None)
    if not isinstance(ga_candidates, list) or not ga_candidates:
        return {}
    calc_song = resolve_active_fg_calc_song(song)
    if not isinstance(calc_song, dict) or not calc_song:
        return {}

    start_i = max(0, int(start_index))
    if start_i >= len(ga_candidates):
        return {}
    limit_i = int(limit)
    if limit_i <= 0:
        stop_i = int(len(ga_candidates))
    else:
        stop_i = int(start_i + limit_i)
    stop_i = max(start_i, min(int(stop_i), int(len(ga_candidates)), 512))
    if stop_i <= start_i:
        return {}

    ref_arrays = getattr(song.gpu_inputs, "ref_arrays", None)
    if not isinstance(ref_arrays, dict):
        ref_arrays = {}

    payload: dict[int, dict] = {}
    for idx, candidate in enumerate(list(ga_candidates[start_i:stop_i]), start=start_i):
        if not isinstance(candidate, dict):
            continue
        data = candidate.get("Data")
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("_fg_group_meta"), dict):
            continue
        base_stats = data.get("BaseStats")
        if not isinstance(base_stats, dict) or not base_stats:
            continue
        try:
            fg_group_meta = build_fg_group_meta(
                base_stats=base_stats,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                selected_element=str(data.get("Selected Element", "") or ""),
                center_ft=int(data.get("FT", 0) or 0),
                center_ff=int(data.get("FF", 0) or 0),
                primary_color=str(getattr(song.gpu_inputs, "meta_primary_color", "") or ""),
                secondary_color=str(getattr(song.gpu_inputs, "meta_secondary_color", "") or ""),
                run_idx=data.get("_ga_gpu_run_idx"),
                row_idx=data.get("_ga_gpu_row_idx"),
                prefer_grid=False,
            )
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:collect_fg_group_meta_payload: {e}")
            continue
        if isinstance(fg_group_meta, dict):
            payload[int(idx)] = fg_group_meta

    return payload


def apply_fg_group_meta_payload(song: NativeSong, payload: dict[int, dict] | None) -> int:
    if not isinstance(payload, dict) or not payload:
        return 0
    ga_candidates = getattr(song.runtime.decode, "ga_candidates", None)
    if not isinstance(ga_candidates, list) or not ga_candidates:
        return 0

    applied = 0
    for idx, fg_group_meta in payload.items():
        try:
            idx_i = int(idx)
        except (ValueError, TypeError):
            continue
        if idx_i < 0 or idx_i >= len(ga_candidates):
            continue
        candidate = ga_candidates[idx_i]
        if not isinstance(candidate, dict):
            continue
        data = candidate.get("Data")
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("_fg_group_meta"), dict):
            continue
        if not isinstance(fg_group_meta, dict):
            continue
        data["_fg_group_meta"] = fg_group_meta
        applied += 1

    return int(applied)


def _resolve_fg_group_meta_prime_limit(
    song: Any,
    *,
    explicit_limit: int,
    explicit_enabled: bool,
) -> int:
    if bool(getattr(song.gpu_inputs, "manual_force_greats", False)):
        return 0
    ga_candidates = getattr(song.runtime.decode, "ga_candidates", None)
    if not isinstance(ga_candidates, list) or not ga_candidates:
        return 0
    max_candidates = max(0, min(int(len(ga_candidates)), 512))
    if max_candidates <= 0:
        return 0
    if bool(explicit_enabled):
        return max(0, min(int(explicit_limit), int(max_candidates)))
    return _default_fg_group_meta_prime_limit(max_candidates)


def prime_fg_group_meta_for_song(song: NativeSong, *, limit: int) -> int:
    limit_i = max(0, min(int(limit), 512))
    if limit_i <= 0:
        return 0
    return int(
        apply_fg_group_meta_payload(
            song,
            collect_fg_group_meta_payload(song, limit=limit_i),
        )
    )


def decode_ga_payload_sync(song: NativeSong, runs_payload: np.ndarray) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = thread_cpu_time_s()
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    song_key = str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or "")
    try:
        emit_profile_event(
            component="inflight_decode",
            event="future_start",
            song_key=song_key,
            metrics={"song_slot": int(getattr(song.runtime, "song_slot", 0) or 0)},
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:decode_ga_payload_sync: {e}")
    decode_cfg_data = dict(getattr(song.gpu_inputs, "cfg_data", {}) or {})
    best_data, best_gear, best_minis, ga_candidates = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=gpu_inputs.registry,
        cfg_data=decode_cfg_data,
        base_stats_fixed=gpu_inputs.fixed_stats,
        fg_candidate_limit=safe_int(
            decode_cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        ),
        # Keep decode focused on GA payload reconstruction. FG-specific song context,
        # runtime warmup, and group-meta priming belong to the explicit FG prep stage.
        calc_song=None,
        ref_arrays=None,
        fg_group_meta_limit=0,
    )
    out = (best_data, best_gear, best_minis, ga_candidates)
    try:
        cpu_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
        song.runtime.decode.cpu_decode_s = cpu_s
    except (AttributeError, TypeError, ValueError):
        cpu_s = None
    try:
        emit_profile_event(
            component="inflight_decode",
            event="future_done",
            song_key=song_key,
            metrics={
                "song_slot": int(getattr(song.runtime, "song_slot", 0) or 0),
                "ga_candidates": int(len(ga_candidates or [])),
                "cpu_s": float(cpu_s or 0.0),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:decode_ga_payload_sync: {e}")
    return out


def prepare_fg_static_sync(song: NativeSong) -> None:
    """
    Prepare the GA-invariant part of FG while GA is still running.

    Finder-mode FG consumes GA candidates directly. The late FG prep still owns
    candidate selection and any work that depends on GA output.
    """
    cpu_t0 = thread_cpu_time_s()
    config = getattr(song, 'config', song)
    runtime = getattr(song, 'runtime', song)
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    cfg = getattr(config, "cfg", None)

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    runtime.fg.fg_candidate_limit = int(fg_candidate_limit)
    runtime.fg.fg_search_radius = read_fg_search_radius(cfg)
    runtime.fg.fg_direct_ga_candidates = not bool(gpu_inputs.manual_force_greats)
    song.runtime.fg.fg_build_details = make_build_details_fn(
        gpu_inputs.meta_primary_color,
        gpu_inputs.meta_secondary_color,
        config.effective_difficulty,
    )
    resolve_active_fg_calc_song(song)

    # Manual-only FG needs GA candidates merged into loadout_entries, so it stays
    # in the late prep phase. Finder-mode can use DB/static entries immediately.
    if not bool(runtime.fg.fg_direct_ga_candidates):
        try:
            song.runtime.fg.fg_static_prep_done = True
            song.runtime.fg.cpu_fg_static_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
        except AttributeError:
            pass
        return

    if getattr(song.runtime.fg, "loadout_entries", None) is not None:
        try:
            song.runtime.fg.fg_static_prep_done = True
            song.runtime.fg.cpu_fg_static_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
        except AttributeError:
            pass
        return

    runtime.fg.loadout_entries = build_loadout_entries(
        config.db_key,
        [],
        gpu_inputs.gears_by_name,
        gpu_inputs.minis_by_name,
        song.runtime.fg.fg_build_details,
        team_buff=resolve_database_baseline_team_buff(cfg_dict=config.cfg_dict),
        materialize_ga_details=False,
        ga_registry=gpu_inputs.registry,
    )
    try:
        song.runtime.fg.fg_static_prep_done = True
        song.runtime.fg.cpu_fg_static_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    except AttributeError:
        pass


def prepare_fg_job_sync(song: NativeSong, gpu_client: Optional[GpuServiceClient] = None) -> None:
    cpu_t0 = thread_cpu_time_s()
    runtime = getattr(song, 'runtime', song)
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    wall_t0 = time.perf_counter()
    prep_submit_t0 = song.runtime.fg.fg_prep_submit_t0
    queue_wait_ms = 0.0
    if isinstance(prep_submit_t0, (int, float)):
        queue_wait_ms = max(0.0, (float(wall_t0) - float(prep_submit_t0)) * 1000.0)
    static_future = getattr(song.runtime.fg, "fg_static_prep_future", None)
    if static_future is not None:
        static_done = False
        try:
            static_done = bool(static_future.done())
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:prepare_fg_job_sync: {e}")
            static_done = True
        if static_done:
            try:
                static_future.result()
            except Exception as e:
                logger.debug(f"native_inflight_pipeline:prepare_fg_job_sync: {e}")
            try:
                song.runtime.fg.fg_static_prep_future = None
            except AttributeError:
                pass
    # Static prep is a best-effort accelerator only. If it is not ready yet, FG
    # prep proceeds directly so the runtime can keep feeding the GPU owner.

    config = getattr(song, 'config', song)
    runtime = getattr(song, 'runtime', song)
    gpu_inputs = getattr(song, 'gpu_inputs', song)
    cfg = getattr(config, "cfg", None)

    perf = _truthy(env_get("PERF_TIMING", "0"))
    t0 = time.perf_counter()

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    runtime.fg.fg_candidate_limit = int(fg_candidate_limit)
    runtime.fg.fg_search_radius = read_fg_search_radius(cfg)

    active_fg_calc_song = resolve_active_fg_calc_song(song)

    if not bool(getattr(song.gpu_inputs, "manual_force_greats", False)):
        try:
            calc_song = active_fg_calc_song if isinstance(active_fg_calc_song, dict) else None
            ref_arrays = gpu_inputs.ref_arrays if isinstance(gpu_inputs.ref_arrays, dict) else None
            if calc_song and ref_arrays:
                _warmup_fg_finder_runtime(calc_song, ref_arrays, gpu_client=gpu_client)
        except Exception as e:
            logger.debug(f"native_inflight_pipeline:prepare_fg_job_sync: {e}")
    t_finder_warmup = time.perf_counter()

    # Prime expensive per-song FG structures early so FG dispatch doesn't stall before the first GPU submit.
    _maybe_prewarm_fg_chart_scorer(song)
    t_chart_prewarm = time.perf_counter()

    ga_candidates = runtime.decode.ga_candidates if isinstance(runtime.decode.ga_candidates, list) else list(runtime.decode.ga_candidates or [])
    preselect_ga_candidates = len(ga_candidates)
    # If GA came from the GPU-native "selected payload" path, candidates are already GPU-selected
    # (bounded + deduped) and re-running the CPU selector is pure overhead on slower machines.
    is_gpu_selected_payload = False
    try:
        if ga_candidates:
            d0 = ga_candidates[0].get("Data") if isinstance(ga_candidates[0], dict) else None
            if isinstance(d0, dict) and ("_ga_gpu_run_idx" in d0 or "_ga_gpu_row_idx" in d0):
                is_gpu_selected_payload = True
    except (KeyError, TypeError, ValueError, AttributeError):
        is_gpu_selected_payload = False

    t_candidate_select0 = time.perf_counter()
    if is_gpu_selected_payload:
        ga_candidates = ga_candidates[: int(fg_candidate_limit)]
    else:
        ga_candidates = select_fg_candidates(
            ga_candidates,
            limit=fg_candidate_limit,
            primary_color=str(gpu_inputs.meta_primary_color or ""),
            secondary_color=str(gpu_inputs.meta_secondary_color or ""),
        )
    t_candidate_select = time.perf_counter()
    runtime.decode.ga_candidates = ga_candidates
    hydrated_fg_stats = False
    if not bool(getattr(song.gpu_inputs, "manual_force_greats", False)) and ga_candidates:
        hydrated_fg_stats = True
        hydrate_fg_candidate_stats(
            ga_candidates,
            base_stats_fixed=gpu_inputs.fixed_stats,
            selected_color=str((getattr(song.gpu_inputs, "cfg_data", None) or {}).get("selected_color", "") or ""),
            cfg_data=getattr(song.gpu_inputs, "cfg_data", None),
        )
    t_select = time.perf_counter()

    (
        prime_group_meta_limit,
        prime_group_meta_limit_explicit,
        _,
    ) = read_fg_group_meta_prime_settings()
    prime_group_meta_limit = _resolve_fg_group_meta_prime_limit(
        song,
        explicit_limit=int(prime_group_meta_limit),
        explicit_enabled=bool(prime_group_meta_limit_explicit),
    )
    group_meta_primed = 0
    if int(prime_group_meta_limit) > 0:
        # Finder-mode FG depends on selected-candidate group metadata to be
        # genuinely runnable. Prime it during FG prep so `fg_prep_future.done()`
        # once again means "ready to submit", not "ready to start another CPU
        # collect stage".
        group_meta_primed = prime_fg_group_meta_for_song(song, limit=int(prime_group_meta_limit))
    t_group_meta = time.perf_counter()

    t_db = time.perf_counter()

    build_details = song.runtime.fg.fg_build_details
    if not callable(build_details):
        build_details = make_build_details_fn(
            gpu_inputs.meta_primary_color, gpu_inputs.meta_secondary_color, config.effective_difficulty
        )
        song.runtime.fg.fg_build_details = build_details
    runtime.fg.fg_direct_ga_candidates = not bool(gpu_inputs.manual_force_greats)
    # GPU finder consumes GA candidates directly and only the retained GA subset
    # is merged back into `runtime.fg.loadout_entries` after FG.
    loadout_ga_candidates = [] if bool(runtime.fg.fg_direct_ga_candidates) else list(ga_candidates or [])
    if getattr(song.runtime.fg, "loadout_entries", None) is None or not bool(runtime.fg.fg_direct_ga_candidates):
        runtime.fg.loadout_entries = build_loadout_entries(
            config.db_key,
            loadout_ga_candidates,
            gpu_inputs.gears_by_name,
            gpu_inputs.minis_by_name,
            build_details,
            team_buff=resolve_database_baseline_team_buff(cfg_dict=config.cfg_dict),
            # FG grouping reads eval_data/BaseStats directly; defer details materialization
            # until persistence/retained-output paths so CPU prep does not stall the GPU.
            materialize_ga_details=False,
            ga_registry=gpu_inputs.registry,
        )
    runtime.fg.fg_candidate_surface = build_native_fg_candidate_surface(
        loadout_entries=runtime.fg.loadout_entries or {},
        ga_candidates=ga_candidates if bool(runtime.fg.fg_direct_ga_candidates) else None,
        default_selected_color=str(gpu_inputs.meta_primary_color or ""),
        primary_color=str(gpu_inputs.meta_primary_color or ""),
        secondary_color=str(gpu_inputs.meta_secondary_color or ""),
        minis_by_name=gpu_inputs.minis_by_name,
        registry=gpu_inputs.registry if bool(runtime.fg.fg_direct_ga_candidates) else None,
    )
    t_build = time.perf_counter()

    select_ms = (t_select - t0) * 1000.0
    finder_warmup_ms = (t_finder_warmup - t0) * 1000.0
    chart_prewarm_ms = (t_chart_prewarm - t_finder_warmup) * 1000.0
    candidate_select_ms = (t_candidate_select - t_candidate_select0) * 1000.0
    hydrate_stats_ms = (t_select - t_candidate_select) * 1000.0
    group_meta_ms = (t_group_meta - t_select) * 1000.0
    db_wait_ms = (t_db - t_group_meta) * 1000.0
    build_ms = (t_build - t_db) * 1000.0
    total_ms = (t_build - t0) * 1000.0
    try:
        loadouts_n = len(runtime.fg.loadout_entries or {})
    except (TypeError, AttributeError):
        loadouts_n = 0
    if perf:
        logger.debug(
            "[PERF][FGPrep] "
            f"limit={fg_candidate_limit} ga_in={preselect_ga_candidates} ga={len(ga_candidates)} "
            f"loadouts={loadouts_n} select={select_ms:.1f}ms "
            f"finder_warmup={finder_warmup_ms:.1f}ms chart_prewarm={chart_prewarm_ms:.1f}ms "
            f"candidate_select={candidate_select_ms:.1f}ms hydrate={hydrate_stats_ms:.1f}ms "
            f"group_meta={group_meta_ms:.1f}ms db_wait={db_wait_ms:.1f}ms "
            f"build={build_ms:.1f}ms total={total_ms:.1f}ms"
        )

    try:
        song.runtime.fg.cpu_fg_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    except (AttributeError, TypeError, ValueError):
        pass
    try:
        emit_profile_event(
            component="inflight_fg_prep",
            event="prep_done",
            song_key=str(getattr(song.config, "task_key", "") or getattr(song.config, "song_name", "") or ""),
            metrics={
                "queue_wait_ms": float(queue_wait_ms),
                "select_ms": float(select_ms),
                "finder_warmup_ms": float(finder_warmup_ms),
                "chart_prewarm_ms": float(chart_prewarm_ms),
                "candidate_select_ms": float(candidate_select_ms),
                "hydrate_stats_ms": float(hydrate_stats_ms),
                "group_meta_ms": float(group_meta_ms),
                "group_meta_primed": int(group_meta_primed),
                "group_meta_target": int(prime_group_meta_limit),
                "db_wait_ms": float(db_wait_ms),
                "build_ms": float(build_ms),
                "total_ms": float(total_ms),
                "preselect_ga_candidates": int(preselect_ga_candidates),
                "ga_candidates": int(len(ga_candidates or [])),
                "gpu_selected_payload": int(bool(is_gpu_selected_payload)),
                "hydrated_fg_stats": int(bool(hydrated_fg_stats)),
                "loadouts": int(len(getattr(song.runtime.fg, "loadout_entries", {}) or {})),
                "fg_surface_rows": int(len(getattr(song.runtime.fg, "fg_candidate_surface", None) or [])),
                "direct_ga_candidates": int(bool(getattr(song.runtime.fg, "fg_direct_ga_candidates", False))),
            },
        )
    except Exception as e:
        logger.debug(f"native_inflight_pipeline:prepare_fg_job_sync: {e}")
