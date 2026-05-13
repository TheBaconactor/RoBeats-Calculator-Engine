from __future__ import annotations
import logging
import queue
import threading
import time
from typing import Optional

from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.parsing import env_flag, env_get, truthy
from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg_dict
from gear_optimizer.data.database import (
    get_evolution_db_path,
    get_evolution_overlay_db_path,
    get_song_counters,
    save_loadouts_batch,
    update_song_counters,
)


logger = logging.getLogger(__name__)
_TEAM_BUFF_REF_ARRAYS_LOCK = threading.Lock()
_TEAM_BUFF_REF_ARRAYS_CACHE: dict | None = None


def _build_ref_arrays_from_stats_table(stats_table) -> dict:
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats

    return build_ref_arrays_from_stats(stats_table)


def _get_team_buff_ref_arrays_cached() -> dict | None:
    """
    Load the Stats.txt lookup arrays used by on-demand TeamBuff replay.

    The main app preloads these during a normal optimizer run; DB-manager callers
    need the same tables without constructing `GearOptimizerApp`.
    """
    global _TEAM_BUFF_REF_ARRAYS_CACHE
    with _TEAM_BUFF_REF_ARRAYS_LOCK:
        if isinstance(_TEAM_BUFF_REF_ARRAYS_CACHE, dict) and _TEAM_BUFF_REF_ARRAYS_CACHE:
            return _TEAM_BUFF_REF_ARRAYS_CACHE

        try:
            from gear_optimizer.core.config import load_paths_cache
            from gear_optimizer.data.csv_parser import read_table

            paths = load_paths_cache()
            stats_path = str((paths or {}).get("Stats", "") or PATHS.stats_csv)
            stats_table = read_table(stats_path)
            _TEAM_BUFF_REF_ARRAYS_CACHE = _build_ref_arrays_from_stats_table(stats_table)
        except Exception as e:
            logger.warning(f"app_async_db:_get_team_buff_ref_arrays_cached: {e}")
            _TEAM_BUFF_REF_ARRAYS_CACHE = None
        return _TEAM_BUFF_REF_ARRAYS_CACHE


def _async_db_strict() -> bool:
    """
    Strict async DB policy.

    When enabled, async DB failures should surface to the caller so the optimizer
    doesn't continue "successfully" while persistence is broken.
    """
    raw = env_get("METAFINDER_ASYNC_DB_STRICT")
    if raw is not None:
        return truthy(raw)
    return env_flag("GPU_STRICT", "1")


def _overlay_backend_mode_enabled() -> bool:
    """
    Enable overlay DB mirroring only when the optimizer is paired with the backend/live site.
    """
    if env_flag("ROBEATSMETA_OVERLAY_DB_ENABLE"):
        return True
    try:
        from gear_optimizer.robeatsmeta_api import RoBeatsMetaOptimizerApi

        return bool(RoBeatsMetaOptimizerApi.service_mode_enabled())
    except Exception as e:
        logger.warning(f"app_async_db:_overlay_backend_mode_enabled: {e}")
        return env_flag("ROBEATSMETA_OPTIMIZER_SERVICE_MODE")


def _resolve_base_team_buff_for_persistence(cfg_dict: dict) -> str:
    """
    Resolve the baseline TeamBuff tier used by the optimizer for this run.

    This matches runtime semantics:
    - runtime baseline TeamBuff tier => T5
    - Otherwise => TeamContributionBuffConstant.TeamBuff (fallback T5)
    """
    try:
        return resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
    except Exception as e:
        logger.warning(f"app_async_db:_resolve_base_team_buff_for_persistence: {e}")
        return "T5"


class AsyncDbSaver:
    """
    Background DB writer to avoid blocking the main loop between songs.

    This keeps `save_loadouts_batch()` off the critical path so the next song can
    start immediately (GPU stays busier) while DB inserts/dedup/prune run in a
    background thread.
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._error_lock = threading.Lock()
        self._last_error: BaseException | None = None
        self._last_error_msg: str = ""
        self._last_error_kind: str = ""
        self._last_error_song: str = ""
        self._last_error_ts: float = 0.0
        self._failures_total = 0

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._loop,
                name="AsyncDbSaver",
                daemon=True,
            )
            self._thread.start()

    def submit(self, song_name: str, entries: list[dict], *, meta: dict | None = None) -> None:
        self.raise_if_failed()
        meta = meta or {}
        # Allow "meta-only" submissions (no entries) so per-song attempt counters can
        # advance even when we intentionally skip persistence (e.g., score=0).
        if not entries and not meta.get("_processed_run"):
            return
        if not self._running:
            self.start()
        self._queue.put(("save", song_name, entries or [], meta))

    def submit_pending_fg_job(self, song_name: str, candidates: list[dict]) -> None:
        self.raise_if_failed()
        if not song_name:
            return
        if not self._running:
            self.start()
        self._queue.put(("upsert_pending_fg_job", str(song_name), candidates or []))

    def delete_pending_fg_job(self, song_name: str) -> None:
        self.raise_if_failed()
        if not song_name:
            return
        if not self._running:
            self.start()
        self._queue.put(("delete_pending_fg_job", str(song_name)))

    def flush(self, timeout: float = 30.0) -> None:
        if not self._running:
            return
        deadline = time.monotonic() + max(0.0, float(timeout))
        while getattr(self._queue, "unfinished_tasks", 0) > 0:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))

        if getattr(self._queue, "unfinished_tasks", 0) > 0:
            try:
                pending = int(getattr(self._queue, "unfinished_tasks", 0))
            except Exception as e:
                logger.warning(f"app_async_db:flush: {e}")
                pending = -1
            msg = f"[DB] Warning: async DB flush timed out; pending_tasks={pending}"
            try:
                print(msg)
            except Exception as e:
                logger.warning(f"app_async_db:flush: {e}")
            try:
                logging.warning(msg)
            except Exception as e:
                logger.warning(f"app_async_db:flush: {e}")
            if _async_db_strict():
                raise RuntimeError(msg)
        self.raise_if_failed()

    def shutdown(self, timeout: float = 30.0) -> None:
        if not self._running:
            return

        flush_exc: BaseException | None = None
        try:
            # Best-effort flush before stopping.
            self.flush(timeout=timeout)
        except BaseException as exc:
            # Still shut down the thread to avoid leaving it running across a "failed" shutdown.
            flush_exc = exc

        try:
            self._queue.put(None)
        except Exception as e:
            logger.warning(f"app_async_db:shutdown: {e}")

        try:
            if self._thread is not None:
                self._thread.join(timeout=timeout)
        except Exception as e:
            logger.warning(f"app_async_db:shutdown: {e}")

        with self._lock:
            self._running = False
            self._thread = None
        if flush_exc is not None:
            raise flush_exc
        self.raise_if_failed()

    def last_error(self) -> dict | None:
        with self._error_lock:
            if self._last_error is None:
                return None
            return {
                "kind": str(self._last_error_kind or ""),
                "song": str(self._last_error_song or ""),
                "message": str(self._last_error_msg or ""),
                "ts_monotonic": float(self._last_error_ts or 0.0),
                "failures_total": int(self._failures_total),
            }

    def raise_if_failed(self) -> None:
        if not _async_db_strict():
            return
        err = self.last_error()
        if not err:
            return
        kind = err.get("kind") or "unknown"
        song = err.get("song") or "?"
        msg = err.get("message") or "unknown error"
        raise RuntimeError(f"[DB][ASYNC][{kind}] {song}: {msg}")

    def _record_error(self, kind: str, exc: BaseException, *, song_name: str = "") -> None:
        msg = f"{type(exc).__name__}: {exc}"
        try:
            now = float(time.monotonic())
        except Exception as e:
            logger.warning(f"app_async_db:_record_error: {e}")
            now = 0.0
        with self._error_lock:
            self._last_error = exc
            self._last_error_msg = str(msg)
            self._last_error_kind = str(kind or "unknown")
            self._last_error_song = str(song_name or "")
            self._last_error_ts = float(now)
            self._failures_total = int(self._failures_total) + 1

    def _loop(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                if not isinstance(item, tuple) or not item:
                    continue

                kind = item[0]
                if kind == "delete_pending_fg_job":
                    try:
                        _, song_name = item
                    except Exception as e:
                        logger.warning(f"app_async_db:_loop: {e}")
                        continue
                    try:
                        from gear_optimizer.data.database import delete_pending_fg_job

                        delete_pending_fg_job(str(song_name))
                    except Exception as exc:
                        self._record_error("delete_pending_fg_job", exc, song_name=str(song_name))
                    continue

                if kind == "upsert_pending_fg_job":
                    try:
                        _, song_name, candidates = item
                    except Exception as e:
                        logger.warning(f"app_async_db:_loop: {e}")
                        continue
                    try:
                        from gear_optimizer.data.database import upsert_pending_fg_job

                        upsert_pending_fg_job(str(song_name), list(candidates or []))
                    except Exception as exc:
                        self._record_error("upsert_pending_fg_job", exc, song_name=str(song_name))
                    continue

                if kind != "save":
                    continue

                try:
                    _, song_name, entries, meta = item
                except Exception as e:
                    logger.warning(f"app_async_db:_loop: {e}")
                    continue
                if not isinstance(meta, dict):
                    meta = {}

                try:
                    db_key = meta.get("db_key") or song_name
                    processed_run = bool(meta.get("_processed_run", True))
                    cfg_dict = meta.get("cfg_dict") or {}
                    canonical_db_path = str(get_evolution_db_path() or "").strip()
                    overlay_db_path = ""
                    overlay_enabled = False
                    try:
                        overlay_enabled = _overlay_backend_mode_enabled()
                        if overlay_enabled:
                            overlay_db_path = str(get_evolution_overlay_db_path() or "").strip()
                            overlay_enabled = bool(overlay_db_path) and overlay_db_path != canonical_db_path
                    except Exception as e:
                        logger.warning(f"app_async_db:_loop: {e}")
                        overlay_db_path = ""
                        overlay_enabled = False

                    prev_life, prev_attempts, prev_best_score, prev_best_fg = get_song_counters(
                        db_key,
                        db_path=canonical_db_path or None,
                    )
                    if overlay_enabled:
                        try:
                            _ov_life, _ov_attempts, _ov_best_score, _ov_best_fg = get_song_counters(
                                db_key,
                                db_path=overlay_db_path,
                            )
                            prev_best_score = max(int(prev_best_score or 0), int(_ov_best_score or 0))
                            prev_best_fg = max(int(prev_best_fg or 0), int(_ov_best_fg or 0))
                        except Exception as e:
                            logger.warning(f"app_async_db:_loop: {e}")

                    run_score = 0
                    run_best_fg = 0
                    for e in entries or []:
                        if not isinstance(e, dict):
                            continue
                        try:
                            s = int(e.get("score", 0) or 0)
                        except Exception as e:
                            logger.warning(f"app_async_db:_loop: {e}")
                            s = 0
                        try:
                            fg = int(e.get("fg_score", 0) or 0)
                        except Exception as e:
                            logger.warning(f"app_async_db:_loop: {e}")
                            fg = 0
                        if fg <= 0:
                            try:
                                force_obj = e.get("force")
                            except Exception as e:
                                logger.warning(f"app_async_db:_loop: {e}")
                                force_obj = None
                            if isinstance(force_obj, dict):
                                try:
                                    fg = max(fg, int(force_obj.get("score", 0) or 0))
                                except Exception as e:
                                    logger.warning(f"app_async_db:_loop: {e}")
                                det = force_obj.get("details") or {}
                                if isinstance(det, dict):
                                    fg_meta = det.get("ForceGreats") or {}
                                    if isinstance(fg_meta, dict):
                                        try:
                                            fg = max(fg, int(fg_meta.get("final_score", 0) or 0))
                                        except Exception as e:
                                            logger.warning(f"app_async_db:_loop: {e}")
                        if s > run_score:
                            run_score = s
                        if e.get("force") is not None and fg > s and fg > run_best_fg:
                            run_best_fg = fg

                    record_improved = (run_score > int(prev_best_score or 0)) or (run_best_fg > int(prev_best_fg or 0))

                    # Apply attempt metadata to persisted details (per-song semantics).
                    if processed_run:
                        attempt_lifetime = int(prev_life or 0) + 1
                        attempts_first = (
                            1 if record_improved else (int(prev_attempts or 0) + 1 if int(prev_attempts or 0) else 1)
                        )
                        for e in entries or []:
                            if not isinstance(e, dict):
                                continue
                            details = e.get("details") or {}
                            if not isinstance(details, dict):
                                details = {}
                            details = dict(details)
                            details["attempt_lifetime"] = attempt_lifetime
                            details["attempts_first"] = attempts_first
                            e["details"] = details

                    # Timing-envelope runs are deterministic and no longer persist
                    # sampled hit contexts or sampled offset-delta backfills.

                    target_db_path = overlay_db_path if overlay_enabled else canonical_db_path
                    if entries and target_db_path:
                        base_team_buff = _resolve_base_team_buff_for_persistence(cfg_dict or {})
                        save_loadouts_batch(
                            db_key,
                            entries,
                            db_path=target_db_path,
                            team_buff=base_team_buff,
                            preserve_attempt_meta=bool(overlay_enabled),
                        )

                    # Update per-song counters (even if there were no entries to persist).
                    # NOTE: For deferred FG-only updates, `processed_run=False` is still meaningful:
                    # we do not increment attempt counters, but we may reset `attempts_first` when
                    # the best FG score improves.
                    update_song_counters(
                        db_key,
                        processed_run=processed_run,
                        record_improved=record_improved,
                        db_path=canonical_db_path or None,
                    )
                    # Derived TeamBuff tiers are computed on demand (never persisted).
                except Exception as exc:
                    self._record_error("save", exc, song_name=str(song_name))
                    msg = f"[DB] Async save failed for {song_name}: {type(exc).__name__}: {exc}"
                    try:
                        print(msg)
                    except Exception as e:
                        logger.warning(f"app_async_db:_loop: {e}")
                    try:
                        logging.error(msg)
                    except Exception as e:
                        logger.warning(f"app_async_db:_loop: {e}")
            finally:
                try:
                    self._queue.task_done()
                except Exception as e:
                    logger.warning(f"app_async_db:_loop: {e}")
