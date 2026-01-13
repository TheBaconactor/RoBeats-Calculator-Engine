"""
GPU-native in-flight multi-song orchestrator (single process, single GPU owner thread).

This pipeline is designed to keep the GPU continuously busy in GPU_Native_GA mode by:
- Preparing the next songs' CPU-only data while the GPU runs the current song.
- Executing GPU-native GA on the Taichi/Vulkan owner thread (GpuExecutor) via an in-process
  request queue (no per-song process overhead, minimal transfers).
- Interleaving ForceGreatsFinder work at a controlled cadence (default: 1 FG job every
  12 GA jobs), with CPU grouping/prep performed off the GPU thread and GPU kernels
  submitted via the executor.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import queue
import threading
import time
import traceback
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit, read_fg_search_radius
from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.utils import cfg_from_dict, get_selected_element, safe_float, safe_int
from gear_optimizer.helpers.song_helpers.database_context import load_database_context
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.helpers.song_helpers.fg_combo_booster import (
    build_fg_combo_booster_candidates,
    finalize_fg_combo_booster_candidates_job,
    hydrate_fg_candidate_stats,
    prepare_fg_combo_booster_candidates_job,
)
from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.helpers.song_helpers.song_config import setup_song_config
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.genetic import GA_POPULATION_SIZE, decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.inflight_utils import (
    _build_calc_song_from_file,
    _compact_items,
    _compact_prev_record,
    _summarize_db_context,
    _truthy,
)
from gear_optimizer.solver.item_registry import ItemRegistry


_POOL_CACHE_MAX = 32
_REGISTRY_CACHE_MAX = 32
_PREP_CACHE_LOCK = threading.Lock()
_POOL_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[list, list]]" = OrderedDict()
_REGISTRY_GPU_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[ItemRegistry, dict]]" = OrderedDict()
_FG_JIT_WARMED = False


def _thread_cpu_time_s() -> float:
    """
    Best-effort per-thread CPU timer for CPU-only profiling.

    Uses `time.thread_time()` when available (Python 3.7+). Returns 0.0 on unsupported platforms.
    """
    try:
        return float(time.thread_time())
    except Exception:
        return 0.0


def _extract_repeat_ctx(task: tuple) -> dict | None:
    if not isinstance(task, (tuple, list)) or len(task) <= 16:
        return None
    for extra in task[16:]:
        if not isinstance(extra, dict):
            continue
        if "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra:
            return extra
    return None


def _task_key(task: tuple) -> str:
    if not isinstance(task, (tuple, list)) or len(task) < 2:
        return "Unknown"
    base = str(task[1])
    repeat_ctx = _extract_repeat_ctx(task)
    if repeat_ctx:
        try:
            idx = int(repeat_ctx.get("repeat_index") or 0)
            total = int(repeat_ctx.get("repeat_total") or 0)
        except Exception:
            idx = 0
            total = 0
        if idx > 0 and total > 1:
            return f"{base} (Run {idx}/{total})"
    return base


def _task_ga_seed(task: tuple) -> int | None:
    repeat_ctx = _extract_repeat_ctx(task)
    if not repeat_ctx:
        return None
    try:
        seed = repeat_ctx.get("ga_seed")
        return int(seed) if seed is not None else None
    except Exception:
        return None


def _lru_get(cache: OrderedDict, key: tuple) -> Any:
    try:
        value = cache.get(key)
    except Exception:
        return None
    if value is not None:
        try:
            cache.move_to_end(key)
        except Exception:
            pass
    return value


def _lru_put(cache: OrderedDict, key: tuple, value: Any, *, maxsize: int) -> None:
    try:
        cache[key] = value
        cache.move_to_end(key)
    except Exception:
        return
    try:
        while len(cache) > int(maxsize):
            cache.popitem(last=False)
    except Exception:
        pass


class _InFlightStageProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None = None) -> None:
        self.enabled = bool(enabled)
        self.out_path = out_path
        self._t0 = time.perf_counter()
        self._stage: dict[str, dict[str, Any]] = {}
        self._song: dict[str, dict[str, float]] = {}

    def record(self, stage: str, seconds: float, *, cpu_seconds: float | None = None, song: str | None = None) -> None:
        if not self.enabled:
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
        from gear_optimizer.solver.scoring.stats_scoring import fg_baseline_params

        fg_baseline_params({"Fever Time": 0, "Fever Fill Rate": 0}, calc_song, ref_arrays)
    except Exception:
        pass
    try:
        from gear_optimizer.core.constants import TOTAL_ROWS
        from gear_optimizer.solver.fever_timeline import get_song_timeline_grid

        grid = get_song_timeline_grid(calc_song, ref_arrays)
        grid.get_timeline(0, int(TOTAL_ROWS))
        grid.to_gpu_arrays_minimal()
    except Exception:
        pass
    _FG_JIT_WARMED = True


class _PostSender:
    def __init__(self, post_queue, *, stop_requested=None) -> None:
        self._post_queue = post_queue
        self._stop_requested = stop_requested
        backlog = 256
        try:
            backlog = int(os.environ.get("POST_LOCAL_BACKLOG", backlog))
        except Exception:
            backlog = 256
        self._q: queue.Queue[Any] = queue.Queue(maxsize=max(1, backlog))
        self._sentinel = object()
        self._thread = threading.Thread(target=self._run, name="PostQueueSender", daemon=True)
        self._thread.start()

    def send(self, item: Any) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(item, block=False)
        except queue.Full:
            self._q.put(item, block=True)

    def close(self, *, timeout: float = 30.0) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(self._sentinel, block=True, timeout=max(0.0, float(timeout)))
        except Exception:
            return
        try:
            self._thread.join(timeout=timeout)
        except Exception:
            pass

    def _run(self) -> None:
        timing = str(os.environ.get("POST_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
        threshold_ms = 50.0
        try:
            threshold_ms = float(os.environ.get("POST_TIMING_THRESHOLD_MS", str(threshold_ms)))
        except Exception:
            threshold_ms = 50.0
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            try:
                t0 = time.perf_counter()
                while True:
                    if self._stop_requested is not None and callable(self._stop_requested) and self._stop_requested():
                        return
                    try:
                        self._post_queue.put(item, block=True, timeout=0.5)
                        break
                    except Exception:
                        continue
                if timing:
                    ms = (time.perf_counter() - t0) * 1000.0
                    if ms >= threshold_ms:
                        kind = None
                        try:
                            kind = item.get("song") if isinstance(item, dict) else None
                        except Exception:
                            kind = None
                        prefix = f"[PostSender][TIMING] {kind} " if kind else "[PostSender][TIMING] "
                        print(f"{prefix}post_queue_put={ms:.1f}ms")
            except Exception:
                pass


@dataclass
class _NativeSong:
    fp: str
    song_name: str
    task_key: str
    ga_seed: int | None
    db_key: str
    effective_difficulty: str
    cfg_dict: dict
    cfg: Any
    paths: Any
    ref_arrays: dict
    all_gears: list
    all_minis: list
    gears_by_name: dict
    minis_by_name: dict
    use_evo_db: bool
    auto_buff: bool
    ga_depth: int
    fg_debug: bool

    calc_song: dict
    meta_primary_color: str
    meta_secondary_color: str
    fixed_stats: dict
    current_gear_list: list
    current_mini_list: list
    enable_gear: bool
    enable_mini: bool
    force_greats_finder: bool
    force_greats_config: list
    manual_force_greats: bool

    prev_record: Optional[dict]
    attempt_lifetime: int
    prev_attempts_first: int
    db_best_fg_score: int

    # Prepared GPU-native GA inputs
    registry: ItemRegistry
    cfg_data: dict
    color_flags: dict
    gens_per_run: int
    num_runs: int
    n_genomes: int
    item_stats: np.ndarray
    slot_start: np.ndarray
    slot_count: np.ndarray
    base_fixed_stats_arr: np.ndarray
    elite_count: int
    mutation_rate: float
    immigrant_rate: float
    tournament_k: int
    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k: int = 0
    init_heuristic_copies: int = 25
    db_seed_ids: Optional[np.ndarray] = None
    db_seed_prob: float = 0.0
    db_seed_copies: int = 1
    db_seed_mutations: int = 1

    # Runtime state
    song_slot: int = 0
    ga_future: Optional[concurrent.futures.Future] = None
    decode_future: Optional[concurrent.futures.Future] = None
    ga_candidates: Optional[list[dict]] = None
    best_data: Optional[dict] = None
    best_gear: Optional[list] = None
    best_minis: Optional[list] = None

    # DB prefetch for FG (can overlap with GA)
    db_loadouts_future: Optional[concurrent.futures.Future] = None
    db_loadouts_full: Optional[list[dict]] = None

    loadout_entries: Optional[dict] = None
    fg_variants: Optional[list[dict]] = None
    fg_candidate_limit: int = 0
    fg_search_radius: Optional[int] = None
    fg_db_loadouts_full_count: int = 0
    fg_prep_future: Optional[concurrent.futures.Future] = None

    def __post_init__(self) -> None:
        if self.ga_candidates is None:
            self.ga_candidates = []
        if self.fg_variants is None:
            self.fg_variants = []


def _prepare_song(task: tuple) -> _NativeSong:
    cpu_t0 = _thread_cpu_time_s()
    from gear_optimizer.core.constants import GA_ELITISM, GA_MUTATION_RATE
    from gear_optimizer.core.constants import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import initialize_pools

    task_key = _task_key(task)
    ga_seed = _task_ga_seed(task)

    (
        fp,
        found_song_name,
        effective_difficulty,
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        use_evo_db,
        auto_buff,
        ga_depth,
        _status_queue,
        _parallel_workers,
        fg_debug,
    ) = task[:16]

    cfg = cfg_from_dict(cfg_dict)

    try:
        gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
    except Exception:
        gpu_mode = False
    if not gpu_mode:
        raise RuntimeError("GPU-native in-flight requires IterationEngine.GPU_Mode=true")

    try:
        gpu_native = cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=False)
    except Exception:
        gpu_native = False
    if not gpu_native:
        raise RuntimeError("GPU-native in-flight requires IterationEngine.GPU_Native_GA=true")

    calc_song = _build_calc_song_from_file(
        fp=fp,
        found_song_name=found_song_name,
        cfg=cfg,
        cfg_dict=cfg_dict,
    )
    meta_primary_color = str(calc_song.get("metadata", {}).get("Primary Color", "") or "")
    meta_secondary_color = str(calc_song.get("metadata", {}).get("Secondary Color", "") or "")

    (
        ga_settings,
        fixed_stats,
        _current_gear_stats,
        current_gear_list,
        _current_mini_stats,
        current_mini_list,
        _meta_finder,
        _enable_fever,
        enable_mini,
        enable_gear,
        _force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = setup_song_config(cfg, calc_song, bool(auto_buff), paths, gears_by_name, minis_by_name)

    if not (enable_gear or enable_mini):
        raise RuntimeError("GPU-native in-flight currently requires MetaFinder (enable gear or minis).")

    from gear_optimizer.helpers.song_helpers.database_context import build_db_key

    db_key = build_db_key(found_song_name, calc_song)
    if use_evo_db:
        try:
            meta0 = calc_song.get("metadata", {}) or {}
            if meta0.get("HumanHitSimSeedIsRandom"):
                print(
                    "[DB][WARN] HumanHitSim seed is random; DB key includes it (no cross-run reuse). "
                    "Set [HumanHitSim].Seed to a fixed value to accumulate comparable results."
                )
        except Exception:
            pass

    # Load database context (prev_record, known_loadouts)
    #
    # When HumanHitSim uses randomized seeds, some users prefer not to seed GA/known-loadout
    # caches from the DB (comparability concerns). However we still want to fetch the
    # previous best record so we don't spam "NEW RECORD" on songs that already exist.
    skip_db_lookup = False
    if use_evo_db:
        try:
            hitsim_enabled = cfg.getboolean("HumanHitSim", "Enabled", fallback=False)
        except Exception:
            hitsim_enabled = False

        try:
            cfg_seed = int(str(cfg.get("HumanHitSim", "Seed", fallback="0") or "0"))
        except Exception:
            cfg_seed = 0

        try:
            song_repeats = int(str(cfg.get("IterationEngine", "SongRepeats", fallback="1") or "1"))
        except Exception:
            song_repeats = 1

        try:
            # Default to reusing DB seeds/known loadouts even when HumanHitSim.Seed=0 (randomized).
            # Users can still opt out via SkipDBLookupWhenSeedIsRandom=true.
            skip_when_random = cfg.getboolean("HumanHitSim", "SkipDBLookupWhenSeedIsRandom", fallback=False)
        except Exception:
            skip_when_random = False

        try:
            meta0 = calc_song.get("metadata", {}) or {}
            seed_is_random = bool(meta0.get("HumanHitSimSeedIsRandom"))
        except Exception:
            seed_is_random = False

        if skip_when_random and hitsim_enabled and (seed_is_random or (song_repeats > 1 and int(cfg_seed) == 0)):
            skip_db_lookup = True

    allow_db_seed = True
    if skip_db_lookup:
        allow_db_seed = False
        try:
            print("[DB] Skipping DB seed/known-loadout reuse (HumanHitSim random seed).")
        except Exception:
            pass
        # Still load the previous-best record for correct record comparison/messaging.
        prev_record, _known = load_database_context(
            db_key,
            bool(use_evo_db),
            gears_by_name,
            minis_by_name,
            load_known_loadouts=False,
        )
        known_loadouts = {}
    else:
        prev_record, known_loadouts = load_database_context(db_key, bool(use_evo_db), gears_by_name, minis_by_name)
    db_best_fg_score, attempt_lifetime, prev_attempts_first = _summarize_db_context(prev_record, known_loadouts)

    p_color = calc_song.get("metadata", {}).get("Primary Color", "Rush")
    s_color = calc_song.get("metadata", {}).get("Secondary Color", "")
    selected_color = p_color
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    pool_key = (str(p_color), str(s_color), tuple(slots))
    with _PREP_CACHE_LOCK:
        cached_pools = _lru_get(_POOL_CACHE, pool_key)
    if cached_pools is None:
        pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
        if pools is None:
            raise RuntimeError("initialize_pools returned None")
        if len(pools) == 4:
            gear_pool, mini_pool, _total_before, _total_after = pools
        else:
            gear_pool, mini_pool, _total_before, _total_after, _whitelisted_minis = pools
        if gear_pool is None:
            raise RuntimeError("initialize_pools failed (gear_pool is None)")
        with _PREP_CACHE_LOCK:
            _lru_put(_POOL_CACHE, pool_key, (gear_pool, mini_pool), maxsize=_POOL_CACHE_MAX)
    else:
        gear_pool, mini_pool = cached_pools

    cacheable_registry = bool(enable_gear and enable_mini)
    if cacheable_registry:
        with _PREP_CACHE_LOCK:
            cached_registry = _lru_get(_REGISTRY_GPU_CACHE, pool_key)
        if cached_registry is None:
            registry = ItemRegistry(gear_pool, mini_pool, slots)
            gpu_data = registry.to_gpu_arrays()
            with _PREP_CACHE_LOCK:
                _lru_put(_REGISTRY_GPU_CACHE, pool_key, (registry, gpu_data), maxsize=_REGISTRY_CACHE_MAX)
        else:
            registry, gpu_data = cached_registry
    else:
        fixed_gear = list(current_gear_list or [])[:6] if not enable_gear else None
        fixed_minis = list(current_mini_list or [])[:3] if not enable_mini else None
        registry = ItemRegistry(gear_pool, mini_pool, slots, fixed_gear=fixed_gear, fixed_minis=fixed_minis)
        gpu_data = registry.to_gpu_arrays()

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )

    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": True,
        "use_gpu_native": True,
        "fg_candidate_limit": int(fg_candidate_limit),
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0), 0),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0), 0),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0), 0),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0), 0),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0), 0),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0), 0),
    }

    base_fixed_stats_arr, _ = build_base_fixed_stats_array(fixed_stats, cfg_data)

    tournament_k = safe_int(cfg.get("IterationEngine", "GPU_GA_TournamentK", fallback=3), 3)
    tournament_k = max(1, min(8, int(tournament_k)))

    mutation_rate = safe_float(
        cfg.get("IterationEngine", "GPU_GA_MutationRate", fallback=GA_MUTATION_RATE), GA_MUTATION_RATE
    )
    mutation_rate = max(0.0, min(1.0, float(mutation_rate)))

    immigrant_rate = safe_float(cfg.get("IterationEngine", "GPU_GA_ImmigrantRate", fallback=0.0), 0.0)
    immigrant_rate = max(0.0, min(1.0, float(immigrant_rate)))

    db_seed = prev_record if (allow_db_seed and prev_record) else None
    num_runs = int(getattr(ga_settings, "multi_start", 1) or 1)
    if num_runs <= 0:
        num_runs = 1

    ga_depth = int(ga_depth or 0)
    if ga_depth <= 0:
        ga_depth = 1
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    n_genomes = int(GA_POPULATION_SIZE)

    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k = 0
    try:
        init_heuristic_k = int(str(os.environ.get("GPU_GA_INIT_HEURISTIC_K", "64") or "64"))
    except Exception:
        init_heuristic_k = 64
    init_heuristic_k = max(0, int(init_heuristic_k))
    init_heuristic_copies = 25

    db_seed_ids: Optional[np.ndarray] = None

    try:
        from gear_optimizer.solver.genetic import build_ga_init_heuristic_topk, extract_db_seed_ids

        if init_heuristic_k > 0:
            init_heuristic_topk = build_ga_init_heuristic_topk(
                item_stats=np.asarray(gpu_data["item_stats"], dtype=np.int32),
                slot_start=np.asarray(gpu_data["slot_start"], dtype=np.int32),
                slot_count=np.asarray(gpu_data["slot_count"], dtype=np.int32),
                primary_color=str(p_color or ""),
                secondary_color=str(s_color or ""),
                heuristic_k=int(init_heuristic_k),
                n_slots=9,
            )

        db_seed_ids = extract_db_seed_ids(db_seed=db_seed, registry=registry, n_slots=9)
    except Exception:
        init_heuristic_topk = None
        db_seed_ids = None

    if init_heuristic_topk is None or init_heuristic_k <= 0:
        init_heuristic_topk = None
        init_heuristic_k = 0
        init_heuristic_copies = 0

    color_flags = build_color_flags(p_color, s_color, selected_color)

    elite_count = safe_int(cfg.get("IterationEngine", "GPU_GA_EliteCount", fallback=GA_ELITISM), GA_ELITISM)
    elite_count = max(0, int(elite_count))

    song = _NativeSong(
        fp=str(fp),
        song_name=str(found_song_name),
        task_key=str(task_key),
        ga_seed=int(ga_seed) if ga_seed is not None else None,
        db_key=str(db_key),
        effective_difficulty=str(effective_difficulty),
        cfg_dict=cfg_dict,
        cfg=cfg,
        paths=paths,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        use_evo_db=bool(use_evo_db),
        auto_buff=bool(auto_buff),
        ga_depth=int(ga_depth),
        fg_debug=bool(fg_debug),
        calc_song=calc_song,
        meta_primary_color=meta_primary_color,
        meta_secondary_color=meta_secondary_color,
        fixed_stats=fixed_stats,
        current_gear_list=current_gear_list,
        current_mini_list=current_mini_list,
        enable_gear=bool(enable_gear),
        enable_mini=bool(enable_mini),
        force_greats_finder=bool(force_greats_finder),
        force_greats_config=force_greats_config,
        manual_force_greats=bool(manual_force_greats),
        prev_record=prev_record,
        attempt_lifetime=int(attempt_lifetime),
        prev_attempts_first=int(prev_attempts_first),
        db_best_fg_score=int(db_best_fg_score),
        registry=registry,
        cfg_data=cfg_data,
        color_flags=color_flags,
        gens_per_run=int(gens_per_run),
        num_runs=int(num_runs),
        n_genomes=int(n_genomes),
        init_heuristic_topk=init_heuristic_topk,
        init_heuristic_k=int(init_heuristic_k),
        init_heuristic_copies=int(init_heuristic_copies),
        db_seed_ids=db_seed_ids,
        db_seed_prob=float(getattr(ga_settings, "db_seed_prob", 0.0) or 0.0) if db_seed_ids is not None else 0.0,
        db_seed_copies=1 if db_seed_ids is not None else 0,
        db_seed_mutations=int(getattr(ga_settings, "db_seed_mutations", 1) or 0) if db_seed_ids is not None else 0,
        item_stats=np.asarray(gpu_data["item_stats"], dtype=np.int32),
        slot_start=np.asarray(gpu_data["slot_start"], dtype=np.int32),
        slot_count=np.asarray(gpu_data["slot_count"], dtype=np.int32),
        base_fixed_stats_arr=np.asarray(base_fixed_stats_arr, dtype=np.int32),
        elite_count=int(elite_count),
        mutation_rate=float(mutation_rate),
        immigrant_rate=float(immigrant_rate),
        tournament_k=int(tournament_k),
    )
    try:
        setattr(song, "_cpu_prep_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
    return song


def run_native_inflight_song_pipeline(
    tasks: list[tuple],
    *,
    in_flight_songs: int,
    completed_songs: set[str],
    memory_resume_tracker=None,
    post_queue=None,
    total_tasks: int | None = None,
    stop_requested=None,
) -> None:
    if not tasks:
        return

    cfg0 = None
    try:
        cfg0 = cfg_from_dict(tasks[0][3] or {})
    except Exception:
        cfg0 = None

    inflight_limit = max(1, int(in_flight_songs))
    inflight_limit = min(inflight_limit, len(tasks))

    # Limit concurrent in-flight songs by available GPU timeline slots.
    # Slot 0 is shared/fallback; we reserve 1..MAX_SONG_SLOTS-1 for deterministic reuse.
    try:
        from gear_optimizer.solver.taichi_gem.fields import MAX_SONG_SLOTS

        max_song_slots = int(MAX_SONG_SLOTS)
    except Exception:
        max_song_slots = 8
    song_slot_limit = max(1, int(max_song_slots) - 1)
    inflight_limit = min(int(inflight_limit), int(song_slot_limit))
    if int(in_flight_songs) > 1:
        try:
            msg = (
                f"[InFlight] enabled: requested={int(in_flight_songs)} effective={int(inflight_limit)} "
                f"(GPU_SONG_SLOTS={int(max_song_slots)}, usable_slots={int(song_slot_limit)})"
            )
            if int(inflight_limit) < int(in_flight_songs):
                msg += " [capped by song slots; set GPU_SONG_SLOTS >= InFlightSongs + 1]"
            print(msg)
        except Exception:
            pass

    from gear_optimizer.solver.inflight_utils import SongSlotPool

    slot_pool = SongSlotPool(max_song_slots=int(max_song_slots))

    # How deep we allow the GPU-native GA queue to get (number of submitted GA jobs).
    # A deeper backlog reduces GPU idle gaps when CPU-side decode / FG prep briefly stalls.
    ga_queue_mult = 0
    if cfg0 is not None:
        try:
            ga_queue_mult = safe_int(cfg0.get("IterationEngine", "InFlight_GA_QueueMult", fallback="0"), 0)
        except Exception:
            ga_queue_mult = 0
    try:
        ga_queue_mult = int(os.environ.get("INFLIGHT_GA_QUEUE_MULT", "0") or "0")
    except Exception:
        ga_queue_mult = 0
    if ga_queue_mult <= 0:
        ga_queue_mult = 2
    ga_queue_mult = max(1, min(int(ga_queue_mult), 8))
    ga_queue_limit = max(1, int(inflight_limit) * int(ga_queue_mult))
    ga_queue_limit = min(int(ga_queue_limit), int(song_slot_limit))

    # CPU prep staging buffer size (prepared songs + in-flight preps).
    # Larger buffers avoid starvation on fast GPUs at the cost of RAM.
    prep_buffer_mult = 0
    if cfg0 is not None:
        try:
            prep_buffer_mult = safe_int(cfg0.get("IterationEngine", "InFlight_PrepBufferMult", fallback="0"), 0)
        except Exception:
            prep_buffer_mult = 0
    try:
        prep_buffer_mult = int(os.environ.get("INFLIGHT_PREP_BUFFER_MULT", "0") or "0")
    except Exception:
        prep_buffer_mult = 0
    if prep_buffer_mult <= 0:
        prep_buffer_mult = 4
    prep_buffer_mult = max(1, min(int(prep_buffer_mult), 16))
    prep_limit = max(1, int(inflight_limit) * int(prep_buffer_mult))

    fg_every = 12
    try:
        if cfg0 is not None:
            fg_every = safe_int(cfg0.get("IterationEngine", "FG_InterleaveEvery", fallback=12), 12)
    except Exception:
        fg_every = 12
    fg_every = max(1, int(fg_every))

    fg_drain_at_end = True
    try:
        if cfg0 is not None:
            fg_drain_at_end = cfg0.getboolean("IterationEngine", "FG_DrainAtEnd", fallback=True)
    except Exception:
        fg_drain_at_end = True

    # Configure GPU-native GA run buffers BEFORE the GPU executor initializes Taichi fields.
    # The executor warms FG kernels on startup which triggers taichi_gem field allocation; if
    # we don't size buffers up front, GA payload downloads become padded and require staging.
    try:
        from gear_optimizer.solver.taichi_gem import fields as gpu_fields

        ga_runs = 1
        try:
            from gear_optimizer.data.models import GASettings

            settings = GASettings.from_cfg(cfg0) if cfg0 is not None else GASettings.from_cfg(None)
            ga_runs = int(settings.multi_start)
        except Exception:
            ga_runs = 1

        gpu_fields.configure_ga_run_buffers(max_runs=ga_runs, max_genomes=GA_POPULATION_SIZE)
    except Exception:
        pass

    gpu_executor = get_gpu_executor()
    gpu_executor.start(in_process=True)
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)

    stage_profile_enabled = _truthy(os.environ.get("INFLIGHT_STAGE_PROFILE", "0"))
    stage_profile_path = os.environ.get("INFLIGHT_STAGE_PROFILE_PATH")
    if stage_profile_enabled and not stage_profile_path:
        try:
            from gear_optimizer.core.constants import PATHS

            stage_profile_path = PATHS.bin_path("inflight_stage_profile.json")
        except Exception:
            stage_profile_path = None
    stage_profiler = _InFlightStageProfiler(enabled=stage_profile_enabled, out_path=stage_profile_path)

    post_sender = _PostSender(post_queue, stop_requested=stop_requested) if post_queue is not None else None

    def _post(item: dict) -> None:
        if post_sender is not None:
            post_sender.send(item)

    pending_tasks = deque(t for t in tasks if _task_key(t) not in completed_songs)
    # If the queue is shorter than the configured FG cadence, cap the effective cadence
    # so small runs still execute at least one FG job (instead of deferring forever).
    fg_every = max(1, min(int(fg_every), len(pending_tasks)))
    prepared: deque[_NativeSong] = deque()
    pending_fg: deque[_NativeSong] = deque()

    # GA jobs submitted to the GPU executor (in-order). We intentionally keep a
    # backlog so CPU-side decode/post-processing can't create GPU idle gaps.
    ga_inflight: deque[_NativeSong] = deque()

    ga_seed = str(os.environ.get("GA_SEED") or "").strip()
    prep_workers = 0
    if cfg0 is not None:
        try:
            prep_workers = safe_int(cfg0.get("IterationEngine", "InFlight_PrepWorkers", fallback="0"), 0)
        except Exception:
            prep_workers = 0
    try:
        prep_workers = int(os.environ.get("INFLIGHT_PREP_WORKERS", "0") or "0")
    except Exception:
        prep_workers = 0
    if prep_workers <= 0:
        if ga_seed:
            prep_workers = 1
        else:
            prep_workers = max(1, min(inflight_limit, os.cpu_count() or 1))

    prep_executor = concurrent.futures.ThreadPoolExecutor(max_workers=prep_workers, thread_name_prefix="SongPrep")
    prep_inflight: deque[tuple[tuple, concurrent.futures.Future, float]] = deque()

    decode_workers = 0
    if cfg0 is not None:
        try:
            decode_workers = safe_int(cfg0.get("IterationEngine", "InFlight_DecodeWorkers", fallback="0"), 0)
        except Exception:
            decode_workers = 0
    try:
        decode_workers = int(os.environ.get("INFLIGHT_DECODE_WORKERS", "0") or "0")
    except Exception:
        decode_workers = 0
    if decode_workers <= 0:
        decode_workers = max(1, min(inflight_limit, os.cpu_count() or 1))
    decode_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=decode_workers,
        thread_name_prefix="GADecode",
    )
    decode_inflight: deque[_NativeSong] = deque()

    fg_workers_default = min(4, inflight_limit)
    fg_workers = fg_workers_default
    try:
        fg_workers = int(os.environ.get("INFLIGHT_FG_WORKERS", str(fg_workers_default)) or str(fg_workers_default))
    except Exception:
        fg_workers = fg_workers_default
    fg_workers = max(1, min(int(fg_workers), inflight_limit))

    fg_executor = concurrent.futures.ThreadPoolExecutor(max_workers=fg_workers, thread_name_prefix="FG")
    fg_futures: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
    ga_completed_since_last_fg = 0

    fg_prep_workers = 0
    if cfg0 is not None:
        try:
            fg_prep_workers = safe_int(cfg0.get("IterationEngine", "InFlight_FGPrepWorkers", fallback="0"), 0)
        except Exception:
            fg_prep_workers = 0
    try:
        fg_prep_workers = int(os.environ.get("INFLIGHT_FG_PREP_WORKERS", "0") or "0")
    except Exception:
        fg_prep_workers = 0
    if fg_prep_workers <= 0:
        fg_prep_workers = max(1, min(inflight_limit, os.cpu_count() or 1))
    fg_prep_executor = concurrent.futures.ThreadPoolExecutor(max_workers=fg_prep_workers, thread_name_prefix="FGPrep")
    fg_prep_inflight: deque[_NativeSong] = deque()
    fg_jit_warmup_submitted = False

    def _log_abort(exc: Exception) -> None:
        try:
            from gear_optimizer.core.constants import PATHS

            path = PATHS.bin_path("inflight_native_abort.log")
        except Exception:
            path = None
        if not path:
            return
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            snapshot = (
                f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)}"
            )
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"\n[{ts}] {type(exc).__name__}: {exc}\n")
                fh.write(snapshot + "\n")
                fh.write(traceback.format_exc() + "\n")
        except Exception:
            pass

    # Prime the pipeline: pre-prepare a backlog synchronously so the GPU queue
    # doesn't starve on early song boundaries while prep workers spin up.
    #
    # High-end GPUs can burn through the first GA jobs quickly; priming only 1–2 songs
    # can still leave the GPU idle while CPU prep catches up. Default to priming up to
    # `inflight_limit`, but allow override via env var for experimentation.
    prime_target = 0
    if cfg0 is not None:
        try:
            prime_target = safe_int(cfg0.get("IterationEngine", "InFlight_PrimeTarget", fallback="0"), 0)
        except Exception:
            prime_target = 0
    try:
        prime_target = int(os.environ.get("INFLIGHT_PRIME_TARGET", "0") or "0")
    except Exception:
        prime_target = 0
    if prime_target <= 0:
        prime_target = inflight_limit
    prime_target = max(1, min(int(prime_target), inflight_limit, len(pending_tasks)))
    for _ in range(int(prime_target)):
        first = pending_tasks.popleft()
        song_name = first[1]
        task_key = _task_key(first)
        if task_key in completed_songs:
            continue
        try:
            t0 = time.perf_counter()
            prepared_song = _prepare_song(first)
            prepared.append(prepared_song)
            stage_profiler.record(
                "prep",
                time.perf_counter() - t0,
                cpu_seconds=getattr(prepared_song, "_cpu_prep_s", None),
                song=task_key,
            )
        except Exception as exc:
            _post(
                {
                    "_error": str(exc),
                    "_error_type": type(exc).__name__,
                    "_song_name": song_name,
                    "song": song_name,
                    "_queue_key": task_key,
                    "_queue_label": task_key,
                }
            )
            completed_songs.add(task_key)
            if memory_resume_tracker:
                memory_resume_tracker.mark_completed(song_name)

    try:
        if prepared and not fg_jit_warmup_submitted:
            fg_prep_executor.submit(_warmup_fg_jit, prepared[0].calc_song, prepared[0].ref_arrays)
            fg_jit_warmup_submitted = True
    except Exception:
        pass

    def _pop_next_ready_fg() -> Optional[_NativeSong]:
        for candidate in list(pending_fg):
            fut = candidate.fg_prep_future
            if fut is None:
                try:
                    pending_fg.remove(candidate)
                except Exception:
                    pass
                return candidate
            try:
                if fut.done():
                    pending_fg.remove(candidate)
                    return candidate
            except Exception:
                continue
        return None

    try:
        last_progress = time.monotonic()
        last_stall_report = last_progress
        last_heartbeat = last_progress
        last_throughput = last_progress
        last_stage_emit = last_progress
        heartbeat_sec = 0.0
        try:
            heartbeat_sec = float(os.environ.get("INFLIGHT_HEARTBEAT_SEC", "0") or "0")
        except Exception:
            heartbeat_sec = 0.0

        throughput_sec = 0.0
        try:
            throughput_sec = float(os.environ.get("INFLIGHT_THROUGHPUT_SEC", "0") or "0")
        except Exception:
            throughput_sec = 0.0

        stage_emit_sec = 0.0
        try:
            stage_emit_sec = float(os.environ.get("INFLIGHT_STAGE_PROFILE_EMIT_SEC", "0") or "0")
        except Exception:
            stage_emit_sec = 0.0

        profile_max_songs = 0
        try:
            profile_max_songs = int(os.environ.get("INFLIGHT_PROFILE_MAX_SONGS", "0") or "0")
        except Exception:
            profile_max_songs = 0
        profile_max_songs = max(0, int(profile_max_songs))
        completed_baseline = 0
        try:
            completed_baseline = int(len(completed_songs))
        except Exception:
            completed_baseline = 0

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
            if memory_release_requested():
                break

            # Optional profiling cap: stop after N completed songs/tasks.
            if (not stopping) and profile_max_songs > 0:
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception:
                    completed_now = 0
                if completed_now >= int(profile_max_songs):
                    stopping = True
                    try:
                        pending_tasks.clear()
                    except Exception:
                        pass
                    try:
                        prepared.clear()
                    except Exception:
                        pass
                    try:
                        pending_fg.clear()
                    except Exception:
                        pass

            if stop_requested is not None and callable(stop_requested) and stop_requested():
                if not stopping:
                    stopping = True
                    try:
                        pending_tasks.clear()
                    except Exception:
                        pass
                    try:
                        prepared.clear()
                    except Exception:
                        pass
                    try:
                        pending_fg.clear()
                    except Exception:
                        pass
                    # Best-effort cancel of queued prep/decode work.
                    try:
                        for _task, fut, _t0 in list(prep_inflight):
                            try:
                                fut.cancel()
                            except Exception:
                                pass
                        prep_inflight.clear()
                    except Exception:
                        pass
                    try:
                        for song in list(decode_inflight):
                            try:
                                if song.decode_future is not None:
                                    song.decode_future.cancel()
                            except Exception:
                                pass
                        # Keep entries so we can still drain the deque safely.
                    except Exception:
                        pass

            # Periodic throughput reporting (opt-in via env).
            now = time.monotonic()
            if throughput_sec > 0 and (now - last_throughput) >= float(throughput_sec):
                last_throughput = now
                try:
                    completed_now = int(len(completed_songs)) - int(completed_baseline)
                except Exception:
                    completed_now = 0
                if completed_now > 0:
                    wall_s = max(1e-9, float(time.perf_counter() - float(stage_profiler._t0)))
                    per_h = float(completed_now) * 3600.0 / wall_s
                    try:
                        pending_now = int(len(pending_tasks)) + int(len(prepared)) + int(len(pending_fg))
                    except Exception:
                        pending_now = 0
                    try:
                        avg_s = wall_s / float(completed_now)
                        eta_s = float(pending_now) * avg_s if pending_now > 0 else 0.0
                    except Exception:
                        avg_s = 0.0
                        eta_s = 0.0
                    try:
                        print(
                            f"[InFlight][Throughput] done={completed_now} pending~{pending_now} "
                            f"rate={per_h:.1f}/h avg={avg_s:.2f}s ETA={eta_s/60.0:.1f}m"
                        )
                    except Exception:
                        pass

            # Periodic stage profile emission (opt-in via env).
            if stage_emit_sec > 0 and stage_profiler.enabled and (now - last_stage_emit) >= float(stage_emit_sec):
                last_stage_emit = now
                try:
                    stage_profiler.emit()
                except Exception:
                    pass

            did_work = False
            blocked_on_slot_acquire = False

            # Move completed song preps into the staging queue.
            for task, fut, t_submit in list(prep_inflight):
                if not fut.done():
                    continue
                prep_inflight.remove((task, fut, t_submit))
                did_work = True
                song_name = task[1]
                task_key = _task_key(task)
                if task_key in completed_songs:
                    continue
                try:
                    prepared_song = fut.result()
                    stage_profiler.record(
                        "prep",
                        time.perf_counter() - float(t_submit),
                        cpu_seconds=getattr(prepared_song, "_cpu_prep_s", None),
                        song=task_key,
                    )
                    prepared.append(prepared_song)
                    if prepared and not fg_jit_warmup_submitted:
                        try:
                            fg_prep_executor.submit(_warmup_fg_jit, prepared[0].calc_song, prepared[0].ref_arrays)
                            fg_jit_warmup_submitted = True
                        except Exception:
                            pass
                except Exception as exc:
                    _post(
                        {
                            "_error": str(exc),
                            "_error_type": type(exc).__name__,
                            "_song_name": song_name,
                            "song": song_name,
                            "_queue_key": task_key,
                            "_queue_label": task_key,
                        }
                    )
                    completed_songs.add(task_key)
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(song_name)

            # Finalize prepared FG jobs (CPU prep done) so the GPU stage can start immediately when scheduled.
            for song in list(fg_prep_inflight):
                # `fg_prep_future` may be consumed by the FG worker (it waits on the
                # future and then clears it). Ensure we still drain the tracking deque
                # so the main loop can terminate cleanly.
                if song.fg_prep_future is None:
                    fg_prep_inflight.remove(song)
                    did_work = True
                    continue
                if not song.fg_prep_future.done():
                    continue
                fg_prep_inflight.remove(song)
                did_work = True
                try:
                    t_submit = getattr(song, "_fg_prep_submit_t0", None)
                    if t_submit is not None:
                        stage_profiler.record(
                            "fg_prep",
                            time.perf_counter() - float(t_submit),
                            cpu_seconds=getattr(song, "_cpu_fg_prep_s", None),
                            song=song.song_name,
                        )
                        setattr(song, "_fg_prep_submit_t0", None)
                    song.fg_prep_future.result()
                except Exception as exc:
                    _post(
                        {
                            "_error": str(exc),
                            "_error_type": type(exc).__name__,
                            "_song_name": song.song_name,
                            "song": song.song_name,
                            "_queue_key": song.task_key,
                            "_queue_label": song.task_key,
                        }
                    )
                finally:
                    song.fg_prep_future = None

            # Keep the GPU queue full while using spare CPU time to prep future songs.
            #
            # - `ga_inflight` bounds the number of submitted GPU-native GA jobs.
            # - `prepared` is a CPU-side staging buffer; keeping it non-empty prevents
            #   starvation if CPU prep briefly falls behind GPU throughput.
            # - We alternate submit/prep to minimize the initial "startup bubble".
            while True:
                # Submit GA jobs whenever we have prepared work and GPU queue capacity.
                # We allow `ga_inflight` to exceed `inflight_limit` to create a backlog
                # that keeps the GPU fed while CPU decode/FG prep runs.
                if stopping:
                    break
                if prepared and len(ga_inflight) < ga_queue_limit:
                    song = prepared.popleft()
                    # Reserve a per-song GPU timeline slot so GA -> FG can reuse the resident grid
                    # even while other songs are in-flight (avoids clobbering slot 0).
                    if int(getattr(song, "song_slot", 0) or 0) <= 0:
                        try:
                            song.song_slot = int(slot_pool.acquire())
                        except Exception:
                            # No free slots: defer GA submission until FG drains.
                            blocked_on_slot_acquire = True
                            prepared.appendleft(song)
                            break
                        try:
                            song.calc_song["_gpu_song_slot"] = int(song.song_slot)
                        except Exception:
                            pass
                    setattr(song, "_ga_submit_t0", time.perf_counter())
                    payload = {
                        "calc_song": song.calc_song,
                        "ref_arrays": song.ref_arrays,
                        "song_slot": int(song.song_slot),
                        "item_stats": song.item_stats,
                        "slot_start": song.slot_start,
                        "slot_count": song.slot_count,
                        "base_fixed_stats_arr": song.base_fixed_stats_arr,
                        "initial_populations": None,
                        "num_runs": int(song.num_runs),
                        "n_genomes": int(song.n_genomes),
                        "init_heuristic_topk": song.init_heuristic_topk,
                        "init_heuristic_k": int(song.init_heuristic_k),
                        "init_heuristic_copies": int(song.init_heuristic_copies),
                        "db_seed_ids": song.db_seed_ids,
                        "db_seed_prob": float(song.db_seed_prob),
                        "db_seed_copies": int(song.db_seed_copies),
                        "db_seed_mutations": int(song.db_seed_mutations),
                        "n_generations": int(song.gens_per_run),
                        "elite_count": int(song.elite_count),
                        "mutation_rate": float(song.mutation_rate),
                        "immigrant_rate": float(song.immigrant_rate),
                        "tournament_k": int(song.tournament_k),
                        "color_flags": dict(song.color_flags),
                        "cfg_data": dict(song.cfg_data),
                        "ga_seed": song.ga_seed,
                    }
                    try:
                        handle = gpu_client.submit_gpu_native_ga_run(payload)
                    except Exception as exc:
                        # Ensure we don't leak the reserved slot on submission failure.
                        try:
                            slot_pool.release(int(song.song_slot))
                            song.song_slot = 0
                        except Exception:
                            pass
                        _post(
                            {
                                "_error": str(exc),
                                "_error_type": type(exc).__name__,
                                "_song_name": song.song_name,
                                "song": song.song_name,
                                "_queue_key": song.task_key,
                                "_queue_label": song.task_key,
                            }
                        )
                        completed_songs.add(song.task_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song.song_name)
                        did_work = True
                        continue

                    song.ga_future = handle.future
                    ga_inflight.append(song)
                    did_work = True

                    # Prefetch DB loadouts early so FG prep after GA decode doesn't stall
                    # waiting on SQLite reads (keeps the GPU fed during song boundaries).
                    if (
                        (song.manual_force_greats or song.force_greats_finder)
                        and song.use_evo_db
                        and song.db_loadouts_future is None
                        and song.db_loadouts_full is None
                    ):
                        try:
                            prefetch_limit = safe_int(
                                song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
                                FG_CANDIDATE_LIMIT,
                            )
                            song.db_loadouts_future = fg_prep_executor.submit(
                                _prefetch_db_loadouts_sync,
                                song.db_key,
                                limit=int(prefetch_limit),
                                gears_by_name=song.gears_by_name,
                                minis_by_name=song.minis_by_name,
                            )
                        except Exception:
                            song.db_loadouts_future = None
                    continue

                # CPU prep: keep a staging buffer of prepared jobs so the GPU queue
                # doesn't starve if CPU prep briefly falls behind GPU throughput.
                if stopping:
                    break
                if pending_tasks and (len(prepared) + len(prep_inflight) < prep_limit):
                    nxt = pending_tasks.popleft()
                    nxt_key = _task_key(nxt)
                    if nxt_key in completed_songs:
                        did_work = True
                        continue
                    try:
                        prep_inflight.append((nxt, prep_executor.submit(_prepare_song, nxt), time.perf_counter()))
                    except Exception as exc:
                        _post(
                            {
                                "_error": str(exc),
                                "_error_type": type(exc).__name__,
                                "_song_name": nxt[1],
                                "song": nxt[1],
                                "_queue_key": nxt_key,
                                "_queue_label": nxt_key,
                            }
                        )
                        completed_songs.add(nxt_key)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(nxt[1])
                        did_work = True
                        continue
                    did_work = True
                    continue

                break

            # Drain completed GA jobs quickly to free inflight capacity; do the heavier
            # CPU-side decode on a background thread so the GPU queue stays fed.
            for song in list(ga_inflight):
                if song.ga_future is None or not song.ga_future.done():
                    continue
                ga_inflight.remove(song)
                did_work = True

                try:
                    runs_payload = song.ga_future.result()
                except Exception as exc:
                    _post(
                        {
                            "_error": str(exc),
                            "_error_type": type(exc).__name__,
                            "_song_name": song.song_name,
                            "song": song.song_name,
                            "_queue_key": song.task_key,
                            "_queue_label": song.task_key,
                        }
                    )
                    # GA failed: release the reserved timeline slot for this song.
                    try:
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass
                    completed_songs.add(song.task_key)
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(song.song_name)
                    continue

                t_submit = getattr(song, "_ga_submit_t0", None)
                if t_submit is not None:
                    stage_profiler.record("ga_gpu", time.perf_counter() - float(t_submit), song=song.task_key)
                    setattr(song, "_ga_submit_t0", None)

                song.ga_future = None
                setattr(song, "_decode_submit_t0", time.perf_counter())
                song.decode_future = decode_executor.submit(_decode_ga_payload_sync, song, runs_payload)
                decode_inflight.append(song)
                ga_completed_since_last_fg += 1

            # Finalize decoded GA results (lightweight formatting + enqueue for post/FG).
            for song in list(decode_inflight):
                if song.decode_future is None or not song.decode_future.done():
                    continue
                decode_inflight.remove(song)
                did_work = True

                try:
                    best_data, best_gear, best_minis, ga_candidates = song.decode_future.result()
                except Exception as exc:
                    _post(
                        {
                            "_error": str(exc),
                            "_error_type": type(exc).__name__,
                            "_song_name": song.song_name,
                            "song": song.song_name,
                        }
                    )
                    # Decode failed: release the reserved timeline slot for this song.
                    try:
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass
                    completed_songs.add(song.task_key)
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(song.song_name)
                    continue
                finally:
                    song.decode_future = None

                t_decode = getattr(song, "_decode_submit_t0", None)
                if t_decode is not None:
                    stage_profiler.record(
                        "decode",
                        time.perf_counter() - float(t_decode),
                        cpu_seconds=getattr(song, "_cpu_decode_s", None),
                        song=song.task_key,
                    )
                    setattr(song, "_decode_submit_t0", None)

                song.best_data = best_data
                song.best_gear = best_gear
                song.best_minis = best_minis
                song.ga_candidates = list(ga_candidates or [])

                if song.manual_force_greats or song.force_greats_finder:
                    pending_fg.append(song)
                    if song.fg_prep_future is None:
                        try:
                            setattr(song, "_fg_prep_submit_t0", time.perf_counter())
                            song.fg_prep_future = fg_prep_executor.submit(_prepare_fg_job_sync, song, gpu_client=gpu_client)
                            fg_prep_inflight.append(song)
                        except Exception:
                            song.fg_prep_future = None
                else:
                    # No FG stage for this song: release its reserved timeline slot immediately.
                    try:
                        slot_pool.release(int(getattr(song, "song_slot", 0) or 0))
                        song.song_slot = 0
                    except Exception:
                        pass

                _post(
                    {
                        "_deferred_post": True,
                        "_pending_fg_job": bool(song.manual_force_greats or song.force_greats_finder),
                        "song": song.song_name,
                        "_queue_key": song.task_key,
                        "_queue_label": song.task_key,
                        "_ga_seed": song.ga_seed,
                        "db_key": song.db_key,
                        "file_path": song.fp,
                        "difficulty": song.effective_difficulty,
                        "use_evo_db": bool(song.use_evo_db),
                        "cfg_dict": song.cfg_dict,
                        # Avoid pickling large song/ref objects across the post-process queue
                        # unless FG debug output explicitly needs them.
                        "ref_arrays": song.ref_arrays if song.fg_debug else None,
                        "calc_song": song.calc_song if song.fg_debug else None,
                        "best_data": song.best_data or {},
                        "best_gear": _compact_items(best_gear),
                        "best_minis": _compact_items(best_minis),
                        "current_gear": _compact_items(song.current_gear_list),
                        "current_minis": _compact_items(song.current_mini_list),
                        "enable_gear": bool(song.enable_gear),
                        "enable_mini": bool(song.enable_mini),
                        "fg_variants": [],
                        "ga_candidates": [
                            {
                                "Score": c.get("Score", 0),
                                "BaseScore": c.get("BaseScore", c.get("Score", 0)),
                                "Gear": _compact_items(c.get("Gear")),
                                "Minis": _compact_items(c.get("Minis")),
                                "Data": c.get("Data") or {},
                                "_fg_priority": c.get("_fg_priority", 0),
                            }
                            for c in (song.ga_candidates or [])
                        ],
                        "loadout_entries": None,
                        "prev_record": _compact_prev_record(song.prev_record),
                        "attempt_lifetime": int(song.attempt_lifetime or 0),
                        "prev_attempts_first": int(song.prev_attempts_first or 0),
                        "db_best_fg_score": int(song.db_best_fg_score or 0),
                        "meta_primary_color": song.meta_primary_color,
                        "meta_secondary_color": song.meta_secondary_color,
                        "fg_debug": bool(song.fg_debug),
                        "log": "",
                    }
                )

                completed_songs.add(song.task_key)
                if memory_resume_tracker:
                    memory_resume_tracker.mark_completed(song.song_name)

            # Reap completed FG workers (capture errors).
            if fg_futures:
                still_pending: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
                for fg_song, fut, t_submit in list(fg_futures):
                    try:
                        done = fut.done()
                    except Exception:
                        done = False
                    if done:
                        did_work = True
                        try:
                            fut.result()
                        except Exception:
                            pass
                        # Release this song's reserved timeline slot now that FG is complete.
                        try:
                            slot_pool.release(int(getattr(fg_song, "song_slot", 0) or 0))
                            fg_song.song_slot = 0
                        except Exception:
                            pass
                        stage_profiler.record(
                            "fg_run",
                            time.perf_counter() - float(t_submit),
                            cpu_seconds=getattr(fg_song, "_cpu_fg_run_s", None),
                            song=fg_song.task_key,
                        )
                    else:
                        still_pending.append((fg_song, fut, t_submit))
                fg_futures = still_pending

            should_start_fg = bool(pending_fg) and (
                ga_completed_since_last_fg >= fg_every
                or (
                    fg_drain_at_end and (not pending_tasks and not prepared and not prep_inflight) and (not ga_inflight)
                )
                # If GA can't currently feed the GPU (no in-flight GA and no prepared
                # work), run FG to avoid GPU idle gaps even if the configured cadence
                # hasn't been met yet.
                or (not ga_inflight and not prepared)
                # Avoid a deadlock-like state where all GPU timeline slots are reserved by
                # songs awaiting FG, while `prepared` is non-empty and GA submission keeps
                # failing due to "no free slots". In that case, starting FG is the only
                # way to release slots and resume GA progress.
                or blocked_on_slot_acquire
            )

            if should_start_fg:
                drain_mode = bool(
                    fg_drain_at_end and (not pending_tasks and not prepared and not prep_inflight) and (not ga_inflight)
                )
                if (not drain_mode) and fg_futures:
                    pass
                elif len(fg_futures) < fg_workers:
                    submit_budget = fg_workers if drain_mode else 1
                    while submit_budget > 0 and len(fg_futures) < fg_workers and pending_fg:
                        fg_song = _pop_next_ready_fg()
                        if fg_song is None:
                            break
                        t_submit = time.perf_counter()
                        fg_futures.append(
                            (
                                fg_song,
                                fg_executor.submit(
                                    _run_fg_job_sync,
                                    fg_song,
                                    gpu_client=gpu_client,
                                    post_sender=post_sender,
                                ),
                                t_submit,
                            )
                        )
                        ga_completed_since_last_fg = 0
                        did_work = True
                        submit_budget -= 1

            if did_work:
                last_progress = time.monotonic()

            # If we're not draining FG at end, allow the GA pipeline to finish once all
            # GA work is complete, even if some FG jobs remain deferred.
            if (
                (not fg_drain_at_end)
                and pending_fg
                and (ga_completed_since_last_fg < fg_every)
                and (not pending_tasks)
                and (not prepared)
                and (not prep_inflight)
                and (not ga_inflight)
                and (not decode_inflight)
                and (not fg_prep_inflight)
                and (not fg_futures)
            ):
                try:
                    print(
                        f"[InFlight][FG] Deferred {len(pending_fg)} pending FG job(s) "
                        f"(FG_InterleaveEvery={fg_every}, FG_DrainAtEnd=false). "
                        "Candidates were persisted to DB for later processing."
                    )
                except Exception:
                    pass
                # We are intentionally skipping FG; release reserved timeline slots.
                try:
                    for s in list(pending_fg):
                        try:
                            slot_pool.release(int(getattr(s, "song_slot", 0) or 0))
                            s.song_slot = 0
                        except Exception:
                            continue
                    pending_fg.clear()
                except Exception:
                    pass
                break

            # Avoid tight spin.
            if not did_work:
                if heartbeat_sec > 0.0 and (time.monotonic() - last_heartbeat) >= heartbeat_sec:
                    last_heartbeat = time.monotonic()
                    oldest_ga_s = None
                    try:
                        now = time.perf_counter()
                        t0s = [getattr(s, "_ga_submit_t0", None) for s in ga_inflight]
                        t0s = [t for t in t0s if t is not None]
                        if t0s:
                            oldest_ga_s = max(0.0, now - float(min(t0s)))
                    except Exception:
                        oldest_ga_s = None

                    try:
                        msg = (
                            "[InFlight][HB] "
                            f"idle={time.monotonic() - last_progress:.1f}s "
                            f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                            f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                            f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} fg_futures={len(fg_futures)}"
                        )
                        if blocked_on_slot_acquire:
                            msg += " blocked_slots=1"
                        if oldest_ga_s is not None:
                            msg += f" oldest_ga={oldest_ga_s:.1f}s"
                        print(msg)
                    except Exception:
                        pass

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
                    and _truthy(os.environ.get("INFLIGHT_STALL_DEBUG", "0"))
                ):
                    last_stall_report = time.monotonic()
                    try:
                        fg_done = sum(1 for _song, fut, _t0 in fg_futures if fut.done())
                        fg_inflight = len(fg_futures)
                    except Exception:
                        fg_done = None
                        fg_inflight = None
                    print(
                        "[InFlight][STALL] "
                        f"pending={len(pending_tasks)} prepared={len(prepared)} prep_inflight={len(prep_inflight)} "
                        f"ga_inflight={len(ga_inflight)} decode_inflight={len(decode_inflight)} "
                        f"pending_fg={len(pending_fg)} fg_prep={len(fg_prep_inflight)} "
                        f"fg_inflight={fg_inflight} fg_done={fg_done}"
                    )

                wait_futures: list[concurrent.futures.Future] = []
                for song in ga_inflight:
                    if song.ga_future is not None:
                        wait_futures.append(song.ga_future)
                for _task, fut, _t0 in prep_inflight:
                    if fut is not None:
                        wait_futures.append(fut)
                for song in decode_inflight:
                    if song.decode_future is not None:
                        wait_futures.append(song.decode_future)
                for song in fg_prep_inflight:
                    if song.fg_prep_future is not None:
                        wait_futures.append(song.fg_prep_future)
                for _song, fut, _t0 in fg_futures:
                    wait_futures.append(fut)
                if wait_futures:
                    t_wait = time.perf_counter()
                    concurrent.futures.wait(
                        wait_futures,
                        timeout=0.02,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    stage_profiler.record("main_wait", time.perf_counter() - t_wait)
                else:
                    t_sleep = time.perf_counter()
                    time.sleep(0.001)
                    stage_profiler.record("main_sleep", time.perf_counter() - t_sleep)

    except Exception as exc:
        _log_abort(exc)
        raise
    finally:
        try:
            stage_profiler.emit()
        except Exception:
            pass
        shutdown_debug = _truthy(os.environ.get("INFLIGHT_SHUTDOWN_DEBUG", "0"))
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] fg_executor.shutdown")
            fg_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] decode_executor.shutdown")
            decode_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] fg_prep_executor.shutdown")
            fg_prep_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] prep_executor.shutdown")
            prep_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            if post_sender is not None:
                if shutdown_debug:
                    print("[InFlight][SHUTDOWN] post_sender.close")
                post_sender.close(timeout=10.0)
        except Exception:
            pass
        try:
            if shutdown_debug:
                print("[InFlight][SHUTDOWN] gpu_client.close")
            gpu_client.close(timeout=2.0)
        except Exception:
            pass
        try:
            if gpu_executor.is_running:
                if shutdown_debug:
                    print("[InFlight][SHUTDOWN] gpu_executor.stop")
                gpu_executor.stop()
        except Exception:
            pass


def _decode_ga_payload_sync(song: _NativeSong, runs_payload: np.ndarray) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = _thread_cpu_time_s()
    out = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=song.registry,
        cfg_data=song.cfg_data,
        base_stats_fixed=song.fixed_stats,
        fg_candidate_limit=safe_int(
            song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        ),
    )
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
        from gear_optimizer.data.database import get_best_loadouts

        return get_best_loadouts(song_name, limit=int(limit), gears_by_name=gears_by_name, minis_by_name=minis_by_name)
    except Exception:
        return []


def _prepare_fg_job_sync(song: _NativeSong, gpu_client: Optional[GpuServiceClient] = None) -> None:
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

    ga_candidates = list(song.ga_candidates or [])
    ga_candidates = select_fg_candidates(
        ga_candidates,
        limit=fg_candidate_limit,
        primary_color=str(song.meta_primary_color or ""),
        secondary_color=str(song.meta_secondary_color or ""),
    )
    song.ga_candidates = ga_candidates
    t_select = time.perf_counter() if perf else 0.0

    db_loadouts_full = song.db_loadouts_full
    if db_loadouts_full is None and song.db_loadouts_future is not None:
        try:
            db_loadouts_full = song.db_loadouts_future.result()
            song.db_loadouts_full = db_loadouts_full
        except Exception:
            db_loadouts_full = None
        finally:
            song.db_loadouts_future = None
    t_db = time.perf_counter() if perf else 0.0

    build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, song.effective_difficulty)

    song.loadout_entries = build_loadout_entries(
        song.db_key,
        bool(song.use_evo_db),
        ga_candidates,
        fg_candidate_limit,
        song.gears_by_name,
        song.minis_by_name,
        build_details,
        db_loadouts_full=db_loadouts_full,
        lean_ga_candidates=not bool(song.fg_debug),
    )
    t_build = time.perf_counter() if perf else 0.0

    song.fg_db_loadouts_full_count = 0

    # Native in-flight optimization: submit the combo-booster GPU eval early (during FG prep)
    # so `_run_fg_job_sync()` doesn't block on a `solve_genomes_from_registry` call right
    # before starting the heavy FG kernels.
    try:
        combo_enabled = _truthy(os.environ.get("FG_COMBO_BOOSTER_ENABLED", "1"))
        existing_job = getattr(song, "fg_combo_job", None)
        if combo_enabled and gpu_client is not None and song.force_greats_finder and song.ga_candidates and not existing_job:
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


def _run_fg_job_sync(
    song: _NativeSong,
    *,
    gpu_client: GpuServiceClient,
    post_sender: Optional[_PostSender] = None,
) -> None:
    cpu_t0 = _thread_cpu_time_s()
    if song.fg_prep_future is not None:
        try:
            song.fg_prep_future.result()
        except Exception:
            pass
        finally:
            song.fg_prep_future = None

    if song.loadout_entries is None:
        _prepare_fg_job_sync(song, gpu_client=gpu_client)

    build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, song.effective_difficulty)

    # Always-on (ForceGreatsFinder): evaluate a capped set of 1–2-position combos around
    # GA seeds to improve FG coverage when deeper GA runs crowd out fever-heavy variants.
    try:
        combo_enabled = _truthy(os.environ.get("FG_COMBO_BOOSTER_ENABLED", "1"))

        boosted = None
        if song.force_greats_finder and song.ga_candidates and combo_enabled:
            job = getattr(song, "fg_combo_job", None)
            if isinstance(job, dict):
                boosted = finalize_fg_combo_booster_candidates_job(job)
                song.fg_combo_job = None
            if not boosted:
                boosted = build_fg_combo_booster_candidates(
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

            if boosted:
                song.ga_candidates = select_fg_candidates(
                    list(song.ga_candidates or []) + list(boosted),
                    limit=int(song.fg_candidate_limit or 0),
                    primary_color=str(song.meta_primary_color or ""),
                    secondary_color=str(song.meta_secondary_color or ""),
                )
                hydrate_fg_candidate_stats(
                    song.ga_candidates,
                    base_stats_fixed=song.fixed_stats,
                    selected_color=str(song.cfg_data.get("selected_color", "") or ""),
                )
                song.loadout_entries = build_loadout_entries(
                    song.db_key,
                    bool(song.use_evo_db),
                    song.ga_candidates,
                    int(song.fg_candidate_limit or 0),
                    song.gears_by_name,
                    song.minis_by_name,
                    build_details,
                    db_loadouts_full=song.db_loadouts_full,
                    lean_ga_candidates=not bool(song.fg_debug),
                )
    except Exception:
        pass

    fg_variants = process_force_greats(
        song.loadout_entries or {},
        bool(song.manual_force_greats),
        bool(song.force_greats_finder),
        song.force_greats_config,
        song.calc_song,
        song.ref_arrays,
        song.meta_primary_color,
        build_details,
        int(song.fg_db_loadouts_full_count or 0),
        use_gpu=True,
        fg_search_radius=song.fg_search_radius,
        perf_timing=_truthy(os.environ.get("PERF_TIMING", "0")),
        gpu_client=gpu_client,
    )

    song.fg_variants = list(fg_variants or [])
    try:
        setattr(song, "_cpu_fg_run_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass

    if post_sender is not None:
        post_sender.send(
            {
                "_fg_update": True,
                "song": song.song_name,
                "db_key": song.db_key,
                "use_evo_db": bool(song.use_evo_db),
                "persist_entries": _build_fg_persist_entries(song),
            }
        )


def _build_fg_persist_entries(song: _NativeSong) -> list[dict]:
    entries: list[dict] = []
    for v in song.fg_variants or []:
        if not isinstance(v, dict):
            continue
        base_score = v.get("score", 0) or 0
        fg_score = v.get("fg_score", 0) or 0
        gear = v.get("gear") or []
        minis = v.get("minis") or []
        data = v.get("data") or {}
        details = {
            "FT": data.get("FT", 0),
            "FF": data.get("FF", 0),
            "GemCounts": data.get("GemCounts", {}),
            "Stats": data.get("Stats", {}),
            "SelectedElement": get_selected_element(data, ""),
            "PrimaryColor": song.meta_primary_color,
            "SecondaryColor": song.meta_secondary_color,
            "Difficulty": song.effective_difficulty,
            "ForceGreats": data.get("ForceGreats", {}),
        }

        force_obj = None
        try:
            fg_meta = details.get("ForceGreats") or {}
            cfg_obj = fg_meta.get("config") if isinstance(fg_meta, dict) else None
            if cfg_obj and isinstance(cfg_obj, dict) and sum(int(x or 0) for x in cfg_obj.values()) > 0:
                force_obj = {
                    "score": int(fg_score),
                    "gear": _compact_items(gear),
                    "minis": _compact_items(minis),
                    "details": details,
                }
        except Exception:
            force_obj = None
        entries.append(
            {
                "score": int(base_score),
                "fg_score": int(fg_score),
                "gear": _compact_items(gear),
                "minis": _compact_items(minis),
                "details": details,
                "force": force_obj,
            }
        )
    return entries
