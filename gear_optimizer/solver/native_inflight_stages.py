from __future__ import annotations

import copy
import json
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit, read_fg_search_radius
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT, TOTAL_ROWS
from gear_optimizer.core.fallback_monitor import warn_fallback
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.helpers.song_helpers.fg_combo_booster import prepare_fg_combo_booster_candidates_job
from gear_optimizer.helpers.song_helpers.force_greats.entry_utils import build_fg_group_meta
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn

from gear_optimizer.solver.fever_timeline import get_song_timeline_grid
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.scoring.stats_scoring import fg_baseline_params
from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload

_FG_JIT_WARMED = False
_FG_DB_LOADOUTS_CACHE: "OrderedDict[str, tuple[int, list[dict]]]" = OrderedDict()
_FG_DB_LOADOUTS_CACHE_LOCK = threading.Lock()


def _fg_db_cache_max() -> int:
    try:
        raw = os.environ.get("INFLIGHT_FG_DB_CACHE_MAX")
        if raw is not None and str(raw).strip() != "":
            return max(0, int(raw))
    except Exception:
        pass
    return 256


def _fg_db_cache_get(song_name: str, *, limit: int) -> list[dict] | None:
    key = str(song_name or "").strip()
    if not key:
        return None
    try:
        with _FG_DB_LOADOUTS_CACHE_LOCK:
            entry = _FG_DB_LOADOUTS_CACHE.get(key)
            if entry is None:
                return None
            cached_limit, rows = entry
            if int(cached_limit) < int(limit):
                return None
            _FG_DB_LOADOUTS_CACHE.move_to_end(key)
            return list(rows[: int(limit)])
    except Exception:
        return None


def _fg_db_cache_put(song_name: str, *, limit: int, rows: list[dict]) -> None:
    key = str(song_name or "").strip()
    if not key:
        return
    if not isinstance(rows, list):
        return
    try:
        limit_i = max(0, int(limit))
    except Exception:
        limit_i = 0
    try:
        with _FG_DB_LOADOUTS_CACHE_LOCK:
            prev = _FG_DB_LOADOUTS_CACHE.get(key)
            if prev is not None:
                prev_limit, _prev_rows = prev
                # Keep the wider payload for this song key when possible.
                if int(prev_limit) > int(limit_i):
                    return
            _FG_DB_LOADOUTS_CACHE[key] = (int(limit_i), list(rows))
            _FG_DB_LOADOUTS_CACHE.move_to_end(key)
            max_n = int(_fg_db_cache_max())
            if max_n <= 0:
                _FG_DB_LOADOUTS_CACHE.clear()
                return
            while len(_FG_DB_LOADOUTS_CACHE) > max_n:
                _FG_DB_LOADOUTS_CACHE.popitem(last=False)
    except Exception:
        return


def _truthy(raw: Any) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _cfg_section_ci(cfg_dict: dict, name: str) -> dict:
    if not isinstance(cfg_dict, dict):
        return {}
    if name in cfg_dict and isinstance(cfg_dict.get(name), dict):
        return cfg_dict.get(name) or {}
    target = str(name).lower()
    for key, value in cfg_dict.items():
        if str(key).lower() == target and isinstance(value, dict):
            return value
    return {}


def _cfg_value_ci(section: dict, key: str, default: object = None) -> object:
    if not isinstance(section, dict):
        return default
    if key in section:
        return section.get(key, default)
    target = str(key).lower()
    for cur_key, cur_value in section.items():
        if str(cur_key).lower() == target:
            return cur_value
    return default


class _InFlightStageProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None = None) -> None:
        self.enabled = bool(enabled)
        self.out_path = out_path
        self._t0 = time.perf_counter()
        self._stage: dict[str, dict[str, Any]] = {}
        self._song: dict[str, dict[str, float]] = {}
        self._allow_prefixes = self._parse_prefixes(os.environ.get("INFLIGHT_STAGE_PROFILE_PREFIX", ""))
        if _truthy(os.environ.get("INFLIGHT_STAGE_PROFILE_FG_ONLY", "0")) and not self._allow_prefixes:
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
        except Exception:
            return
        if seconds < 0:
            return

        if cpu_seconds is not None:
            try:
                cpu_seconds = float(cpu_seconds)
            except Exception:
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
        except Exception:
            pass

        if cpu_seconds is not None:
            entry["cpu_total_s"] = float(entry.get("cpu_total_s", 0.0) or 0.0) + float(cpu_seconds)
            entry["cpu_max_s"] = max(float(entry.get("cpu_max_s", 0.0) or 0.0), float(cpu_seconds))
            try:
                entry["cpu_samples_s"].append(float(cpu_seconds))
            except Exception:
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
        print(f"[InFlight][StageProfile] total_wall_s={float(summary.get('total_wall_s', 0.0) or 0.0):.3f}")
        for name, info in ranked[:10]:
            print(
                "[InFlight][StageProfile] {:<12} total={:>8.3f}s cpu={:>8.3f}s p50={:>6.3f}s p95={:>6.3f}s max={:>6.3f}s n={}".format(
                    name,
                    float(info.get("total_s", 0.0) or 0.0),
                    float(info.get("cpu_total_s", 0.0) or 0.0),
                    float(info.get("p50_s", 0.0) or 0.0),
                    float(info.get("p95_s", 0.0) or 0.0),
                    float(info.get("max_s", 0.0) or 0.0),
                    int(info.get("count", 0) or 0),
                )
            )

        ranked_cpu = sorted(stages.items(), key=lambda kv: float(kv[1].get("cpu_total_s", 0.0) or 0.0), reverse=True)
        if ranked_cpu:
            print("[InFlight][CpuProfile] top_cpu_s")
            for name, info in ranked_cpu[:10]:
                cpu_total = float(info.get("cpu_total_s", 0.0) or 0.0)
                if cpu_total <= 0.0:
                    continue
                print(
                    "[InFlight][CpuProfile] {:<12} cpu_total={:>8.3f}s p50={:>6.3f}s p95={:>6.3f}s max={:>6.3f}s n={}".format(
                        name,
                        cpu_total,
                        float(info.get("cpu_p50_s", 0.0) or 0.0),
                        float(info.get("cpu_p95_s", 0.0) or 0.0),
                        float(info.get("cpu_max_s", 0.0) or 0.0),
                        int(info.get("count", 0) or 0),
                    )
                )

        out_path = str(self.out_path or "").strip()
        if not out_path:
            return
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, sort_keys=True)
        except Exception:
            pass


def _warmup_fg_jit(calc_song: dict, ref_arrays: dict) -> None:
    global _FG_JIT_WARMED
    if _FG_JIT_WARMED:
        return
    if not calc_song or not ref_arrays:
        return
    try:
        fg_baseline_params({"Fever Time": 0, "Fever Fill Rate": 0}, calc_song, ref_arrays)
    except Exception:
        pass
    try:
        grid = get_song_timeline_grid(calc_song, ref_arrays)
        grid.get_timeline(0, int(TOTAL_ROWS))
        grid.to_gpu_arrays_minimal()
    except Exception:
        pass
    _FG_JIT_WARMED = True


def _decode_ga_payload_sync(song: Any, runs_payload: np.ndarray) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = _thread_cpu_time_s()
    best_data, best_gear, best_minis, ga_candidates = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=song.registry,
        cfg_data=song.cfg_data,
        base_stats_fixed=song.fixed_stats,
        fg_candidate_limit=safe_int(
            song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        ),
    )

    out = (best_data, best_gear, best_minis, ga_candidates)
    try:
        setattr(song, "_cpu_decode_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
    return out


def _prefetch_db_loadouts_sync(
    song_name: str,
    *,
    limit: int,
    gears_by_name: dict,
    minis_by_name: dict,
) -> list[dict]:
    try:
        limit_i = max(0, int(limit))
    except Exception:
        limit_i = 0
    cached = _fg_db_cache_get(song_name, limit=limit_i)
    if cached is not None:
        return cached

    try:
        from gear_optimizer.data.database import get_best_loadouts

        rows = get_best_loadouts(song_name, limit=limit_i, gears_by_name=gears_by_name, minis_by_name=minis_by_name)
        if isinstance(rows, list):
            _fg_db_cache_put(song_name, limit=limit_i, rows=rows)
            return rows
        return []
    except Exception:
        return []


def _prepare_fg_job_sync(song: Any, gpu_client: Optional[GpuServiceClient] = None) -> None:
    cpu_t0 = _thread_cpu_time_s()
    cfg = song.cfg

    perf = _truthy(os.environ.get("PERF_TIMING", "0"))
    t0 = time.perf_counter() if perf else 0.0

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    song.fg_candidate_limit = int(fg_candidate_limit)
    song.fg_search_radius = read_fg_search_radius(cfg)

    # If HumanHitSim is configured for FG-only, we defer the expensive simulation until
    # we actually enter the FG prep stage (keeps CPU prep lighter on low-end machines).
    try:
        meta = song.calc_song.get("metadata") if isinstance(song.calc_song, dict) else None
        if isinstance(meta, dict) and str(meta.get("HumanHitSimApplyTo", "") or "").strip().upper() == "FG":
            from gear_optimizer.solver.hit_simulation import apply_human_hit_sim

            apply_human_hit_sim(song.calc_song, cfg_dict=song.cfg_dict or {})
    except Exception:
        pass

    ga_candidates = list(song.ga_candidates or [])
    # If GA came from the GPU-native "selected payload" path, candidates are already GPU-selected
    # (bounded + deduped) and re-running the CPU selector is pure overhead on slower machines.
    is_gpu_selected_payload = False
    try:
        if ga_candidates:
            d0 = ga_candidates[0].get("Data") if isinstance(ga_candidates[0], dict) else None
            if isinstance(d0, dict) and ("_ga_gpu_run_idx" in d0 or "_ga_gpu_row_idx" in d0):
                is_gpu_selected_payload = True
    except Exception:
        is_gpu_selected_payload = False

    if is_gpu_selected_payload:
        ga_candidates = ga_candidates[: int(fg_candidate_limit)]
    else:
        ga_candidates = select_fg_candidates(
            ga_candidates,
            limit=fg_candidate_limit,
            primary_color=str(song.meta_primary_color or ""),
            secondary_color=str(song.meta_secondary_color or ""),
        )
    song.ga_candidates = ga_candidates
    t_select = time.perf_counter() if perf else 0.0

    def _prime_fg_group_meta_for_candidates(candidates: list[dict] | None, *, calc_song: dict | None) -> None:
        if not isinstance(candidates, list) or not candidates:
            return
        if not isinstance(calc_song, dict) or not calc_song:
            return
        for candidate in candidates:
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
                    ref_arrays=song.ref_arrays if isinstance(song.ref_arrays, dict) else {},
                    selected_element=str(data.get("Selected Element", "") or ""),
                    center_ft=int(data.get("FT", 0) or 0),
                    center_ff=int(data.get("FF", 0) or 0),
                    primary_color=str(song.meta_primary_color or ""),
                    secondary_color=str(song.meta_secondary_color or ""),
                    run_idx=data.get("_ga_gpu_run_idx"),
                    row_idx=data.get("_ga_gpu_row_idx"),
                )
                if isinstance(fg_group_meta, dict):
                    data["_fg_group_meta"] = fg_group_meta
            except Exception:
                continue

    _prime_fg_group_meta_for_candidates(ga_candidates, calc_song=song.calc_song)
    for group in list(getattr(song, "_hitsim_fg_regime_groups", []) or []):
        if not isinstance(group, dict):
            continue
        _prime_fg_group_meta_for_candidates(
            group.get("ga_candidates"),
            calc_song=group.get("calc_song") if isinstance(group.get("calc_song"), dict) else song.calc_song,
        )

    # Non-blocking DB prefetch: check if future is ready without blocking.
    # If the DB read is still in progress, proceed with GA candidates only.
    # This prevents FG worker threads from stalling on DB I/O and starving the GPU.
    db_loadouts_full = song.db_loadouts_full
    prefetch_pending = False
    if db_loadouts_full is None and song.db_loadouts_future is not None:
        try:
            fut = song.db_loadouts_future
            # Use done() check to avoid blocking - if DB read isn't ready, skip it
            if fut.done():
                try:
                    db_loadouts_full = fut.result(timeout=0)
                    song.db_loadouts_full = db_loadouts_full
                    if isinstance(db_loadouts_full, list):
                        _fg_db_cache_put(song.db_key, limit=int(fg_candidate_limit), rows=db_loadouts_full)
                except Exception:
                    db_loadouts_full = None
                finally:
                    song.db_loadouts_future = None
            else:
                # DB prefetch still running - proceed without it to keep GPU fed
                if perf:
                    print("[PERF][FGPrep] db_prefetch not ready, proceeding without DB loadouts")
                prefetch_pending = True
                db_loadouts_full = None
        except Exception:
            db_loadouts_full = None
    t_db = time.perf_counter() if perf else 0.0

    build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, song.effective_difficulty)
    song.fg_direct_ga_candidates = bool(song.force_greats_finder)
    # Keep FG prep focused on DB rows; GPU finder consumes GA candidates directly and
    # only the retained GA subset is merged back into `song.loadout_entries` after FG.
    loadout_ga_candidates = [] if bool(song.fg_direct_ga_candidates) else list(ga_candidates or [])
    song.loadout_entries = build_loadout_entries(
        song.db_key,
        bool(song.use_evo_db),
        loadout_ga_candidates,
        fg_candidate_limit,
        song.gears_by_name,
        song.minis_by_name,
        build_details,
        db_loadouts_full=db_loadouts_full,
        # If prefetch is still in-flight, avoid a duplicate synchronous DB read.
        allow_db_query=not bool(prefetch_pending),
        # FG grouping reads eval_data/BaseStats directly; defer details materialization
        # until persistence/retained-output paths so CPU prep does not stall the GPU.
        materialize_ga_details=False,
        ga_registry=song.registry,
    )
    t_build = time.perf_counter() if perf else 0.0

    # Native in-flight optimization: submit the combo-booster GPU eval early (during FG prep)
    try:
        combo_enabled = _truthy(os.environ.get("FG_COMBO_BOOSTER_ENABLED", "1"))
        existing_job = getattr(song, "fg_combo_job", None)
        if (
            combo_enabled
            and gpu_client is not None
            and song.force_greats_finder
            and song.ga_candidates
            and not existing_job
        ):
            job = prepare_fg_combo_booster_candidates_job(
                existing_candidates=list(song.ga_candidates or []),
                registry=song.registry,
                base_stats_fixed=song.fixed_stats,
                cfg_data=song.cfg_data,
                calc_song=song.calc_song,
                ref_arrays=song.ref_arrays,
                primary_color=str(song.meta_primary_color or ""),
                secondary_color=str(song.meta_secondary_color or ""),
                song_slot=int(song.song_slot or 0),
                gpu_client=gpu_client,
            )
            if job:
                song.fg_combo_job = job
    except Exception:
        pass

    if perf:
        select_ms = (t_select - t0) * 1000.0
        db_wait_ms = (t_db - t_select) * 1000.0
        build_ms = (t_build - t_db) * 1000.0
        total_ms = (t_build - t0) * 1000.0
        try:
            loadouts_n = len(song.loadout_entries or {})
        except Exception:
            loadouts_n = 0
        db_n = -1
        try:
            if isinstance(db_loadouts_full, list):
                db_n = len(db_loadouts_full)
        except Exception:
            db_n = -1
        print(
            "[PERF][FGPrep] "
            f"limit={fg_candidate_limit} ga={len(ga_candidates)} loadouts={loadouts_n} "
            f"select={select_ms:.1f}ms db_wait={db_wait_ms:.1f}ms build={build_ms:.1f}ms total={total_ms:.1f}ms "
            f"db_prefetch={int(db_n >= 0)} db_n={db_n}"
        )

    try:
        setattr(song, "_cpu_fg_prep_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
