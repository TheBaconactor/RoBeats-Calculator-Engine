from __future__ import annotations
import logging
import queue
import threading
import time
import os
from collections import OrderedDict
from typing import Optional

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.env_config import TRUTHY_ENV_VALUES
from gear_optimizer.data.database import (
    get_evolution_db_path,
    get_evolution_overlay_db_path,
    get_song_counters,
    save_loadouts_batch,
    update_song_counters,
)


_TEAM_BUFF_REF_ARRAYS_LOCK = threading.Lock()
_TEAM_BUFF_REF_ARRAYS_CACHE: dict | None = None

_TEAM_BUFF_BASE_CALC_SONG_LOCK = threading.Lock()
_TEAM_BUFF_BASE_CALC_SONG_CACHE: "OrderedDict[str, dict]" = OrderedDict()
_TEAM_BUFF_BASE_CALC_SONG_CACHE_DEFAULT = 16
_TEAM_BUFF_COLOR_TIERS = ("T1", "T5", "T10", "T15")
_TEAM_COLOR_VARIANT_SECONDARY = "SECONDARY"
_TEAM_COLOR_VARIANT_NONE = "NONE"


def _compose_team_buff_color_key(team_buff: str, color_variant: str) -> str:
    return f"{str(team_buff or '').strip().upper()}__{str(color_variant or '').strip().upper()}"


def _truthy_env(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default) or "").strip().lower() in TRUTHY_ENV_VALUES


def _overlay_backend_mode_enabled() -> bool:
    """
    Enable overlay DB mirroring only when the optimizer is paired with the backend/live site.
    """
    if _truthy_env("ROBEATSMETA_OVERLAY_DB_ENABLE", "0"):
        return True
    try:
        from gear_optimizer.robeatsmeta_api import RoBeatsMetaOptimizerApi

        return bool(RoBeatsMetaOptimizerApi.service_mode_enabled())
    except Exception:
        return _truthy_env("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "0")


def _team_buff_base_calc_song_cache_max() -> int:
    """
    Cache size for TeamBuff base calc_song derivation.

    This can materially affect throughput on LoopForever/in-flight runs because the post processor may
    repeatedly need `get_base_calc_song(fp, cfg_dict)` for the same song files.
    """
    raw = os.environ.get("TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX")
    if raw is not None and str(raw).strip() != "":
        try:
            return max(0, int(raw))
        except Exception:
            return _TEAM_BUFF_BASE_CALC_SONG_CACHE_DEFAULT
    return 256 if _truthy_env("INFLIGHT_RAM_MODE", "0") else _TEAM_BUFF_BASE_CALC_SONG_CACHE_DEFAULT


def _team_buff_tier_limit() -> int:
    """
    Tier recomputation can be CPU-heavy; allow a smaller retained set when desired.

    Default is `LOADOUTS_PER_SONG_LIMIT` to preserve current behavior.
    """
    limit = int(LOADOUTS_PER_SONG_LIMIT)
    raw = os.environ.get("TEAM_BUFF_TIER_LIMIT")
    if raw is not None and str(raw).strip() != "":
        try:
            limit = int(raw)
        except Exception:
            pass
    limit = max(1, min(int(limit), int(LOADOUTS_PER_SONG_LIMIT)))
    return int(limit)


def _get_team_buff_ref_arrays_cached() -> dict | None:
    """
    Lazily load `ref_arrays` for TeamBuff tier postprocess in contexts where we don't
    ship ref arrays across process boundaries (e.g. native in-flight deferred post).
    """
    global _TEAM_BUFF_REF_ARRAYS_CACHE
    if _TEAM_BUFF_REF_ARRAYS_CACHE is not None:
        return _TEAM_BUFF_REF_ARRAYS_CACHE

    with _TEAM_BUFF_REF_ARRAYS_LOCK:
        if _TEAM_BUFF_REF_ARRAYS_CACHE is not None:
            return _TEAM_BUFF_REF_ARRAYS_CACHE

        try:
            from gear_optimizer.core.config import load_paths_cache
            from gear_optimizer.core.constants import TOTAL_ROWS, PATHS
            from gear_optimizer.data.csv_parser import read_table

            paths = {}
            try:
                paths = load_paths_cache() or {}
            except Exception:
                paths = {}

            stats_path = str((paths.get("Stats", "") or "").strip() or PATHS.stats_csv)
            stats_table = read_table(stats_path)

            stat_names = [
                "Perfect Points",
                "Combo Multiplier",
                "Fever Multiplier",
                "Fever Fill Rate",
                "Fever Time",
            ]

            ref_arrays: dict = {}
            for i, name in enumerate(stat_names):
                temp_list = []
                for v in range(int(TOTAL_ROWS) + 1):
                    lookup_index = int(TOTAL_ROWS) - int(v)
                    try:
                        val = stats_table[lookup_index][i] if stats_table else 0
                    except Exception:
                        val = 0
                    temp_list.append(val)
                # Keep float32 tables for CPU/GPU parity and lower memory bandwidth.
                import numpy as np

                ref_arrays[name] = np.array(temp_list, dtype=np.float32)

            _TEAM_BUFF_REF_ARRAYS_CACHE = ref_arrays
            return _TEAM_BUFF_REF_ARRAYS_CACHE
        except Exception:
            _TEAM_BUFF_REF_ARRAYS_CACHE = None
            return None


def _get_team_buff_base_calc_song_cached(file_path: str, cfg_dict: dict) -> dict | None:
    """
    Cache base chart parsing for TeamBuff tier postprocess.

    We still clone+apply per-run HitSim (if any) on each call; only the base parse is cached.
    """
    fp = str(file_path or "").strip()
    if not fp:
        return None

    # Allow opting out if memory-sensitive.
    if _truthy_env("TEAM_BUFF_TIER_DISABLE_SONG_CACHE", "0"):
        try:
            from gear_optimizer.pipeline.song_processor import get_base_calc_song

            return get_base_calc_song(fp, cfg_dict)
        except Exception:
            return None

    with _TEAM_BUFF_BASE_CALC_SONG_LOCK:
        cached = _TEAM_BUFF_BASE_CALC_SONG_CACHE.get(fp)
        if cached is not None:
            _TEAM_BUFF_BASE_CALC_SONG_CACHE.move_to_end(fp)
            return cached

    try:
        from gear_optimizer.pipeline.song_processor import get_base_calc_song

        base = get_base_calc_song(fp, cfg_dict)
    except Exception:
        return None

    with _TEAM_BUFF_BASE_CALC_SONG_LOCK:
        _TEAM_BUFF_BASE_CALC_SONG_CACHE[fp] = base
        _TEAM_BUFF_BASE_CALC_SONG_CACHE.move_to_end(fp)
        max_n = int(_team_buff_base_calc_song_cache_max())
        if max_n <= 0:
            _TEAM_BUFF_BASE_CALC_SONG_CACHE.clear()
        else:
            while len(_TEAM_BUFF_BASE_CALC_SONG_CACHE) > int(max_n):
                try:
                    _TEAM_BUFF_BASE_CALC_SONG_CACHE.popitem(last=False)
                except Exception:
                    break
    return base


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
        meta = meta or {}
        # Allow "meta-only" submissions (no entries) so per-song attempt counters can
        # advance even when we intentionally skip persistence (e.g., score=0).
        if not entries and not meta.get("_processed_run"):
            return
        if not self._running:
            self.start()
        self._queue.put(("save", song_name, entries or [], meta))

    def submit_pending_fg_job(self, song_name: str, candidates: list[dict]) -> None:
        if not song_name:
            return
        if not self._running:
            self.start()
        self._queue.put(("upsert_pending_fg_job", str(song_name), candidates or []))

    def delete_pending_fg_job(self, song_name: str) -> None:
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
            except Exception:
                pending = -1
            msg = f"[DB] Warning: async DB flush timed out; pending_tasks={pending}"
            try:
                print(msg)
            except Exception:
                pass
            try:
                logging.warning(msg)
            except Exception:
                pass

    def shutdown(self, timeout: float = 30.0) -> None:
        if not self._running:
            return

        # Best-effort flush before stopping.
        self.flush(timeout=timeout)

        try:
            self._queue.put(None)
        except Exception:
            pass

        try:
            if self._thread is not None:
                self._thread.join(timeout=timeout)
        except Exception:
            pass

        with self._lock:
            self._running = False
            self._thread = None

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
                    except Exception:
                        continue
                    try:
                        from gear_optimizer.data.database import delete_pending_fg_job

                        delete_pending_fg_job(str(song_name))
                    except Exception:
                        pass
                    continue

                if kind == "upsert_pending_fg_job":
                    try:
                        _, song_name, candidates = item
                    except Exception:
                        continue
                    try:
                        from gear_optimizer.data.database import upsert_pending_fg_job

                        upsert_pending_fg_job(str(song_name), list(candidates or []))
                    except Exception:
                        pass
                    continue

                if kind != "save":
                    continue

                try:
                    _, song_name, entries, meta = item
                except Exception:
                    continue
                if not isinstance(meta, dict):
                    meta = {}

                try:
                    db_key = meta.get("db_key") or song_name
                    processed_run = bool(meta.get("_processed_run", True))
                    file_path = meta.get("file_path")
                    cfg_dict = meta.get("cfg_dict") or {}
                    ref_arrays = meta.get("ref_arrays")
                    hitsim_seed = meta.get("hitsim_seed")
                    try:
                        hitsim_seed = int(hitsim_seed) if hitsim_seed is not None else None
                    except Exception:
                        hitsim_seed = None
                    if hitsim_seed is not None and int(hitsim_seed) <= 0:
                        hitsim_seed = None
                    # Allow reusing a single calc_song/ref_arrays for both base backfill + tier postprocess.
                    team_buff_calc_song = None
                    team_buff_ref_arrays = ref_arrays
                    canonical_db_path = str(get_evolution_db_path() or "").strip()
                    overlay_db_path = ""
                    overlay_enabled = False
                    try:
                        overlay_enabled = _overlay_backend_mode_enabled()
                        if overlay_enabled:
                            overlay_db_path = str(get_evolution_overlay_db_path() or "").strip()
                            overlay_enabled = bool(overlay_db_path) and overlay_db_path != canonical_db_path
                    except Exception:
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
                        except Exception:
                            pass

                    run_score = 0
                    run_best_fg = 0
                    for e in entries or []:
                        if not isinstance(e, dict):
                            continue
                        try:
                            s = int(e.get("score", 0) or 0)
                        except Exception:
                            s = 0
                        try:
                            fg = int(e.get("fg_score", 0) or 0)
                        except Exception:
                            fg = 0
                        if fg <= 0:
                            try:
                                force_obj = e.get("force")
                            except Exception:
                                force_obj = None
                            if isinstance(force_obj, dict):
                                try:
                                    fg = max(fg, int(force_obj.get("score", 0) or 0))
                                except Exception:
                                    pass
                                det = force_obj.get("details") or {}
                                if isinstance(det, dict):
                                    fg_meta = det.get("ForceGreats") or {}
                                    if isinstance(fg_meta, dict):
                                        try:
                                            fg = max(fg, int(fg_meta.get("final_score", 0) or 0))
                                        except Exception:
                                            pass
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

                    # Backfill base HitSim delta for all persisted base rows (top51).
                    #
                    # Why:
                    # - The frontend expects `details_json.hitsim_offset_delta_ms` for every retained base row.
                    # - TeamBuff tier postprocess intentionally excludes T5 recomputation, so missing values
                    #   in the base entries would otherwise remain null (common in native in-flight mode).
                    #
                    # NOTE: This computes the delta from `details["Stats"]` (FFR) + a per-run calc_song
                    # (HumanHitSim applied). It does not modify scores.
                    try:
                        needs_hitsim = False
                        for e in entries or []:
                            if not isinstance(e, dict):
                                continue
                            det0 = e.get("details")
                            if isinstance(det0, dict) and det0.get("hitsim_offset_delta_ms") is None:
                                needs_hitsim = True
                                break

                        human_cfg = cfg_dict.get("HumanHitSim") if isinstance(cfg_dict, dict) else None
                        enabled_raw = None
                        apply_to = ""
                        try:
                            if isinstance(human_cfg, dict):
                                enabled_raw = human_cfg.get("Enabled", human_cfg.get("enabled"))
                                apply_to = str(human_cfg.get("ApplyTo", human_cfg.get("applyto", "")) or "")
                        except Exception:
                            enabled_raw = None
                            apply_to = ""
                        enabled_all = str(enabled_raw or "").strip().lower() in TRUTHY_ENV_VALUES
                        apply_to_all = str(apply_to or "").strip().upper() == "ALL"

                        if needs_hitsim and enabled_all and apply_to_all and file_path:
                            from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
                            from gear_optimizer.solver.hit_simulation import apply_human_hit_sim
                            from gear_optimizer.solver.scoring.force_greats import (
                                summarize_hitsim_offset_delta_ms_for_base,
                            )

                            if ref_arrays is None:
                                ref_arrays = _get_team_buff_ref_arrays_cached()

                            base_calc_song = _get_team_buff_base_calc_song_cached(str(file_path), cfg_dict)
                            if base_calc_song is None:
                                base_calc_song = get_base_calc_song(str(file_path), cfg_dict)
                            calc_song = clone_calc_song(base_calc_song)
                            # Preserve per-run HitSim seed semantics when config uses Seed=0.
                            if hitsim_seed is not None:
                                try:
                                    meta0 = calc_song.get("metadata") if isinstance(calc_song, dict) else None
                                    if not isinstance(meta0, dict):
                                        meta0 = {}
                                    meta1 = dict(meta0)
                                    meta1["HumanHitSimPlanned"] = True
                                    meta1["HumanHitSimSeed"] = int(hitsim_seed)
                                    calc_song["metadata"] = meta1
                                except Exception:
                                    pass
                            try:
                                apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
                            except Exception:
                                calc_song = calc_song
                            team_buff_calc_song = calc_song
                            team_buff_ref_arrays = ref_arrays

                            meta0 = calc_song.get("metadata", {}) or {}
                            apply_to0 = str(meta0.get("HumanHitSimApplyTo", "") or "").strip().upper()
                            if meta0.get("HumanHitSimApplied") and apply_to0 == "ALL":
                                delta_cache_by_ff: dict[int, int] = {}
                                for e in entries or []:
                                    if not isinstance(e, dict):
                                        continue
                                    det0 = e.get("details")
                                    if not isinstance(det0, dict):
                                        continue
                                    if det0.get("hitsim_offset_delta_ms") is not None:
                                        continue
                                    stats0 = det0.get("Stats")
                                    if not isinstance(stats0, dict) or not stats0:
                                        continue
                                    try:
                                        ff0 = int(stats0.get("Fever Fill Rate", 0) or 0)
                                    except Exception:
                                        ff0 = 0
                                    delta0 = delta_cache_by_ff.get(int(ff0))
                                    if delta0 is None:
                                        try:
                                            computed = summarize_hitsim_offset_delta_ms_for_base(
                                                calc_song,
                                                {"Stats": stats0},
                                                ref_arrays or {},
                                            )
                                        except Exception:
                                            computed = None
                                        if computed is not None:
                                            delta0 = int(computed)
                                            delta_cache_by_ff[int(ff0)] = int(delta0)
                                    if delta0 is not None:
                                        det_out = dict(det0)
                                        det_out["hitsim_offset_delta_ms"] = int(delta0)
                                        e["details"] = det_out
                    except Exception:
                        pass

                    target_db_path = overlay_db_path if overlay_enabled else canonical_db_path
                    if entries and target_db_path:
                        save_loadouts_batch(db_key, entries, db_path=target_db_path)

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

                    # Optional: Populate TeamBuff-tier tables (T1/T5/T10/T15/NONE) in async mode.
                    # This is intentionally after base persistence so it never blocks GPU work.
                    tiers_enabled = str(os.environ.get("POST_TEAM_BUFF_TIERS", "1") or "").strip().lower() in (
                        TRUTHY_ENV_VALUES | {""}
                    )
                    if tiers_enabled and entries and file_path:
                        try:
                            from gear_optimizer.data.database import (
                                get_db_connection,
                                save_team_buff_loadouts_batch,
                            )
                            from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
                                build_team_buff_tier_db_batches,
                            )
                            from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song

                            if team_buff_ref_arrays is not None:
                                ref_arrays = team_buff_ref_arrays
                            if ref_arrays is None:
                                ref_arrays = _get_team_buff_ref_arrays_cached()
                            if not ref_arrays:
                                raise RuntimeError("TeamBuff tier postprocess missing ref_arrays")

                            if team_buff_calc_song is not None:
                                calc_song = team_buff_calc_song
                            else:
                                base_calc_song = _get_team_buff_base_calc_song_cached(str(file_path), cfg_dict)
                                if base_calc_song is None:
                                    # Fallback (no caching).
                                    base_calc_song = get_base_calc_song(str(file_path), cfg_dict)
                                calc_song = clone_calc_song(base_calc_song)
                                # Match per-run timestamp semantics when HumanHitSim is enabled.
                                try:
                                    from gear_optimizer.solver.hit_simulation import apply_human_hit_sim

                                    if hitsim_seed is not None:
                                        try:
                                            meta0 = calc_song.get("metadata") if isinstance(calc_song, dict) else None
                                            if not isinstance(meta0, dict):
                                                meta0 = {}
                                            meta1 = dict(meta0)
                                            meta1["HumanHitSimPlanned"] = True
                                            meta1["HumanHitSimSeed"] = int(hitsim_seed)
                                            calc_song["metadata"] = meta1
                                        except Exception:
                                            pass
                                    apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
                                except Exception:
                                    pass

                            # Exclude T5 from tier recomputation: base runs already persist T5 directly.
                            # Recomputing T5 can slightly diverge from runtime scores and desync songs.best_score.
                            batches = build_team_buff_tier_db_batches(
                                entries=entries,
                                calc_song=calc_song,
                                ref_arrays=ref_arrays,
                                cfg_dict=cfg_dict,
                                limit=int(_team_buff_tier_limit()),
                                tiers=("NONE", "T1", "T10", "T15"),
                            )
                            resolved_tier_db_path = str(target_db_path or canonical_db_path or "").strip()
                            tier_conn = get_db_connection(resolved_tier_db_path or None)
                            did_write = False
                            try:
                                for tier, tier_entries in (batches or {}).items():
                                    if not tier_entries:
                                        continue
                                    save_team_buff_loadouts_batch(
                                        db_key,
                                        str(tier),
                                        tier_entries,
                                        conn=tier_conn,
                                        commit=False,
                                        db_path=resolved_tier_db_path or None,
                                    )
                                    did_write = True

                                # Color-tier persistence is opt-in: these rows are not surfaced by
                                # canonical frontend tier views and can significantly inflate DB size.
                                color_tiers_enabled = (
                                    str(os.environ.get("POST_TEAM_BUFF_COLOR_TIERS", "0") or "").strip().lower()
                                    in TRUTHY_ENV_VALUES
                                )
                                if color_tiers_enabled:
                                    meta0 = calc_song.get("metadata", {}) or {}
                                    primary_color = str(meta0.get("Primary Color", "") or "").strip()
                                    secondary_color = str(meta0.get("Secondary Color", "") or "").strip()

                                    color_variants: list[tuple[str, str]] = [(_TEAM_COLOR_VARIANT_NONE, "")]
                                    if secondary_color and secondary_color.lower() != primary_color.lower():
                                        color_variants.append((_TEAM_COLOR_VARIANT_SECONDARY, secondary_color))

                                    for color_variant, target_color in color_variants:
                                        color_batches = build_team_buff_tier_db_batches(
                                            entries=entries,
                                            calc_song=calc_song,
                                            ref_arrays=ref_arrays,
                                            cfg_dict=cfg_dict,
                                            limit=int(_team_buff_tier_limit()),
                                            tiers=_TEAM_BUFF_COLOR_TIERS,
                                            target_team_color_override=target_color,
                                        )
                                        for tier, tier_entries in (color_batches or {}).items():
                                            if not tier_entries:
                                                continue
                                            tier_key = _compose_team_buff_color_key(str(tier), color_variant)
                                            save_team_buff_loadouts_batch(
                                                db_key,
                                                tier_key,
                                            tier_entries,
                                            conn=tier_conn,
                                            commit=False,
                                            db_path=resolved_tier_db_path or None,
                                        )
                                        did_write = True

                                if did_write:
                                    tier_conn.commit()
                            finally:
                                tier_conn.close()
                        except Exception:
                            pass
                except Exception as exc:
                    msg = f"[DB] Async save failed for {song_name}: {type(exc).__name__}: {exc}"
                    try:
                        print(msg)
                    except Exception:
                        pass
                    try:
                        logging.error(msg)
                    except Exception:
                        pass
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass
