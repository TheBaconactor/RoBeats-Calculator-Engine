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
import os
import queue
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.utils import cfg_from_dict, safe_float, safe_int
from gear_optimizer.helpers.song_helpers.database_context import load_database_context
from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.song_config import setup_song_config
from gear_optimizer.solver.genetic import _build_base_stats_array, decode_gpu_native_ga_runs_payload
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.item_registry import ItemRegistry


def _truthy(v: Any) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


_POOL_CACHE_MAX = 32
_REGISTRY_CACHE_MAX = 32
_PREP_CACHE_LOCK = threading.Lock()
_POOL_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[list, list]]" = OrderedDict()
_REGISTRY_GPU_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[ItemRegistry, dict]]" = OrderedDict()
_FG_JIT_WARMED = False


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
    def __init__(self, post_queue) -> None:
        self._post_queue = post_queue
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
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            try:
                self._post_queue.put(item)
            except Exception:
                pass


def _compact_items(items: list) -> list[str]:
    out: list[str] = []
    for it in items or []:
        if isinstance(it, dict):
            name = it.get("Name", "")
        else:
            name = str(it) if it else ""
        if name:
            out.append(name)
    return out


def _compact_prev_record(record: Optional[dict]) -> Optional[dict]:
    if not isinstance(record, dict):
        return None
    out = dict(record)
    out["gear"] = _compact_items(record.get("gear"))
    out["minis"] = _compact_items(record.get("minis"))
    if isinstance(out.get("loadout"), (list, tuple)):
        out["loadout"] = [str(x) if x is not None else "" for x in out.get("loadout")]
    force_obj = out.get("force")
    if isinstance(force_obj, dict):
        force_copy = dict(force_obj)
        if isinstance(force_copy.get("gear"), (list, tuple)):
            force_copy["gear"] = [str(x) if x is not None else "" for x in force_copy.get("gear")]
        if isinstance(force_copy.get("minis"), (list, tuple)):
            force_copy["minis"] = [str(x) if x is not None else "" for x in force_copy.get("minis")]
        out["force"] = force_copy
    return out


def _build_calc_song_from_file(*, fp: str, found_song_name: str, cfg) -> dict:
    from gear_optimizer.pipeline.song_processor import read_song_file

    song_data = read_song_file(fp)
    song_timestamps_np = np.array(song_data.get("timestamps") or [], dtype=np.float64)
    song_note_types_np = np.array(song_data.get("note_types") or [], dtype=np.int16)
    if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
        song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)

    calc_song = {
        "metadata": song_data.get("song_details") or {},
        "song_data": {"timestamps": song_timestamps_np, "note_types": song_note_types_np},
    }

    # Optional: HumanHitSim (match song_processor.py semantics).
    try:
        sim_enabled = cfg.getboolean("HumanHitSim", "Enabled", fallback=False)
    except Exception:
        sim_enabled = False

    if sim_enabled and calc_song.get("song_data", {}).get("timestamps") is not None:
        from gear_optimizer.solver.hit_simulation import (
            simulate_perfect_hit_timestamps_with_great_candidates,
            stable_seed_from_text,
        )

        apply_to = cfg.get("HumanHitSim", "ApplyTo", fallback="FG").strip().upper()
        if apply_to not in {"FG", "ALL"}:
            apply_to = "FG"

        try:
            seed_in = int(cfg.get("HumanHitSim", "Seed", fallback="0") or "0")
        except Exception:
            seed_in = 0

        dist = cfg.get("HumanHitSim", "Distribution", fallback="uniform").strip().lower()
        great_mode = cfg.get("HumanHitSim", "GreatMode", fallback="late").strip().lower()

        if seed_in == 0:
            song_key = str(calc_song.get("metadata", {}).get("Song Name", "")) or str(found_song_name)
            seed_in = stable_seed_from_text(song_key)

        base_ts = np.asarray(calc_song["song_data"].get("timestamps", ()), dtype=np.float64)
        base_types = np.asarray(calc_song["song_data"].get("note_types", ()), dtype=np.int16)
        if base_types.shape[0] != base_ts.shape[0]:
            base_types = np.ones(base_ts.shape[0], dtype=np.int16)

        sim_ts, sim_great_candidates, sim_dbg = simulate_perfect_hit_timestamps_with_great_candidates(
            base_ts,
            base_types,
            seed=seed_in,
            distribution=dist,
            great_mode=great_mode,
        )

        calc_song["song_data"]["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
        calc_song["song_data"]["fg_great_candidate_timestamps"] = np.asarray(sim_great_candidates, dtype=np.float64)
        calc_song["metadata"]["HumanHitSimSeed"] = int(seed_in)
        calc_song["metadata"]["HumanHitSimApplyTo"] = apply_to
        calc_song["metadata"]["HumanHitSimDistribution"] = dist
        calc_song["metadata"]["HumanHitSimGreatMode"] = great_mode
        calc_song["metadata"]["HumanHitSimDebug"] = sim_dbg
        calc_song["metadata"]["HumanHitSimApplied"] = True
        if apply_to == "ALL":
            calc_song["song_data"]["timestamps"] = np.asarray(sim_ts, dtype=np.float64)

    return calc_song


@dataclass
class _NativeSong:
    fp: str
    song_name: str
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
    initial_populations: np.ndarray
    item_stats: np.ndarray
    slot_start: np.ndarray
    slot_count: np.ndarray
    base_fixed_stats_arr: np.ndarray
    elite_count: int
    mutation_rate: float
    immigrant_rate: float
    tournament_k: int

    # Runtime state
    ga_future: Optional[concurrent.futures.Future] = None
    decode_future: Optional[concurrent.futures.Future] = None
    ga_candidates: Optional[list[dict]] = None
    best_data: Optional[dict] = None
    best_gear: Optional[list] = None
    best_minis: Optional[list] = None

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
    from gear_optimizer.core.constants import GA_ELITISM, GA_MUTATION_RATE
    from gear_optimizer.core.constants import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import build_initial_population, create_genome_functions, initialize_pools

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
    ) = task

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

    calc_song = _build_calc_song_from_file(fp=fp, found_song_name=found_song_name, cfg=cfg)
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

    prev_record, known_loadouts = load_database_context(found_song_name, bool(use_evo_db), gears_by_name, minis_by_name)

    db_best_fg_score = 0
    if known_loadouts:
        try:
            db_best_fg_score = max(v[1] for v in known_loadouts.values() if v[1])
        except Exception:
            db_best_fg_score = 0

    attempt_lifetime_prev = 0
    prev_attempts_first = 0
    if prev_record and "details" in prev_record:
        attempt_lifetime_prev = prev_record["details"].get("attempt_lifetime", 0) or 0
        prev_attempts_first = prev_record["details"].get("attempts_first", 0) or 0
    attempt_lifetime = int(attempt_lifetime_prev) + 1

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

    with _PREP_CACHE_LOCK:
        cached_registry = _lru_get(_REGISTRY_GPU_CACHE, pool_key)
    if cached_registry is None:
        registry = ItemRegistry(gear_pool, mini_pool, slots)
        gpu_data = registry.to_gpu_arrays()
        with _PREP_CACHE_LOCK:
            _lru_put(_REGISTRY_GPU_CACHE, pool_key, (registry, gpu_data), maxsize=_REGISTRY_CACHE_MAX)
    else:
        registry, gpu_data = cached_registry

    fg_candidate_limit = max(
        LOADOUTS_PER_SONG_LIMIT,
        min(
            5000,
            safe_int(
                cfg.get("IterationEngine", "FG_CandidateLimit", fallback=FG_CANDIDATE_LIMIT),
                FG_CANDIDATE_LIMIT,
            ),
        ),
    )

    cfg_data = {
        "selected_color": selected_color,
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

    base_fixed_stats_arr, _ = _build_base_stats_array(fixed_stats, cfg_data)

    tournament_k = safe_int(cfg.get("IterationEngine", "GPU_GA_TournamentK", fallback=3), 3)
    tournament_k = max(1, min(8, int(tournament_k)))

    mutation_rate = safe_float(
        cfg.get("IterationEngine", "GPU_GA_MutationRate", fallback=GA_MUTATION_RATE), GA_MUTATION_RATE
    )
    mutation_rate = max(0.0, min(1.0, float(mutation_rate)))

    immigrant_rate = safe_float(cfg.get("IterationEngine", "GPU_GA_ImmigrantRate", fallback=0.0), 0.0)
    immigrant_rate = max(0.0, min(1.0, float(immigrant_rate)))

    gear_rank_cache = {s: gear_pool[s] for s in slots}
    mini_rank_cache = mini_pool
    (
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
    ) = create_genome_functions(
        gear_pool,
        mini_pool,
        gear_rank_cache,
        mini_rank_cache,
        gears_by_name,
        minis_by_name,
        slots,
        bool(enable_gear),
        bool(enable_mini),
        current_gear_list,
        current_mini_list,
    )

    db_seed = prev_record if prev_record else None
    num_runs = int(getattr(ga_settings, "multi_start", 1) or 1)
    if num_runs <= 0:
        num_runs = 1

    ga_depth = int(ga_depth or 0)
    if ga_depth <= 0:
        ga_depth = 1
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)

    fast_init = True
    try:
        fast_init = cfg.getboolean("IterationEngine", "GPU_GA_FastInit", fallback=True)
    except Exception:
        fast_init = True

    if fast_init:
        import hashlib

        seed_list = build_seed_list_from_record(db_seed) if db_seed else []

        fixed_genome: list[dict] = []
        fixed_genome.extend(list(current_gear_list or [])[:6])
        while len(fixed_genome) < 6:
            fixed_genome.append({})
        fixed_genome.extend(list(current_mini_list or [])[:3])
        while len(fixed_genome) < 9:
            fixed_genome.append({})
        fixed_ids = registry.encode_genome(fixed_genome)

        heuristic_ids: list[np.ndarray] = []
        for _ in range(25):
            heuristic_ids.append(registry.encode_genome(create_heuristic_genome()))
        heuristic_block = np.stack(heuristic_ids, axis=0).astype(np.int32, copy=False) if heuristic_ids else None
        heuristic_len = int(heuristic_block.shape[0]) if heuristic_block is not None else 0

        seed_base = None
        ga_seed_env = str(os.environ.get("GA_SEED") or "").strip()
        if ga_seed_env:
            try:
                seed_base = int(ga_seed_env)
            except Exception:
                seed_base = None

        if seed_base is not None:
            digest = hashlib.md5(str(found_song_name).encode("utf-8")).digest()
            song_seed = int.from_bytes(digest[:4], "little", signed=False)
            rng = np.random.default_rng((int(seed_base) ^ song_seed) & 0xFFFFFFFF)
        else:
            rng = np.random.default_rng()

        slot_start_arr = np.asarray(gpu_data["slot_start"], dtype=np.int32).reshape(-1)
        slot_count_arr = np.asarray(gpu_data["slot_count"], dtype=np.int32).reshape(-1)
        if slot_start_arr.shape[0] < 9 or slot_count_arr.shape[0] < 9:
            raise RuntimeError("Invalid registry slot arrays for GPU-native GA (expected 9 slots).")

        mini_start = int(slot_start_arr[6])
        mini_count = int(slot_count_arr[6])

        def _fill_random_rows(out: np.ndarray, start_row: int) -> None:
            n_rows = int(out.shape[0] - start_row)
            if n_rows <= 0:
                return
            for slot_idx in range(9):
                if slot_idx < 6 and not enable_gear:
                    out[start_row:, slot_idx] = int(fixed_ids[slot_idx])
                    continue
                if slot_idx >= 6 and not enable_mini:
                    out[start_row:, slot_idx] = int(fixed_ids[slot_idx])
                    continue
                c = int(slot_count_arr[slot_idx])
                if c <= 0:
                    continue
                out[start_row:, slot_idx] = int(slot_start_arr[slot_idx]) + rng.integers(
                    0, c, size=n_rows, dtype=np.int32
                )

            if enable_mini and mini_count >= 3:
                dup = (
                    (out[start_row:, 6] == out[start_row:, 7])
                    | (out[start_row:, 6] == out[start_row:, 8])
                    | (out[start_row:, 7] == out[start_row:, 8])
                )
                if np.any(dup):
                    idxs = np.nonzero(dup)[0]
                    for j in idxs:
                        picks = rng.choice(mini_count, size=3, replace=False)
                        out[start_row + int(j), 6:9] = np.asarray(mini_start + picks, dtype=np.int32)

        populations = np.zeros((int(num_runs), int(GA_POPULATION_SIZE), 9), dtype=np.int32)
        for run_idx in range(int(num_runs)):
            row = 0
            # Optional DB seed injection (mirrors build_initial_population probability gate).
            if seed_list:
                try:
                    should_inject = bool(rng.random() < float(getattr(ga_settings, "db_seed_prob", 0.0) or 0.0))
                except Exception:
                    should_inject = False
                if should_inject:
                    try:
                        seed_genome = reconstruct_genome_from_db_list(seed_list)
                        populations[run_idx, row] = registry.encode_genome(seed_genome)
                        row += 1
                        populations[run_idx, row] = registry.encode_genome(mutate_genome_once(seed_genome))
                        row += 1
                    except Exception:
                        row = row

            if heuristic_block is not None and heuristic_len > 0 and row < GA_POPULATION_SIZE:
                take = min(int(heuristic_len), int(GA_POPULATION_SIZE - row))
                populations[run_idx, row : row + take] = heuristic_block[:take]
                row += take

            _fill_random_rows(populations[run_idx], row)

            # Enforce fixed slots for non-optimized dimensions (heuristics/seed may have picked different items).
            if not enable_gear:
                populations[run_idx, :, :6] = fixed_ids[:6]
            if not enable_mini:
                populations[run_idx, :, 6:9] = fixed_ids[6:9]

            # Randomize row order for this run so seeded genomes don't always occupy
            # the same indices (preserves multi-start diversity).
            perm = rng.permutation(int(GA_POPULATION_SIZE))
            populations[run_idx] = populations[run_idx][perm]

        initial_populations = populations
    else:
        pops_encoded: list[np.ndarray] = []
        n_genomes = None
        for _ in range(num_runs):
            pop = build_initial_population(
                create_random_genome,
                create_heuristic_genome,
                reconstruct_genome_from_db_list,
                build_seed_list_from_record,
                mutate_genome_once,
                db_seed,
                ga_settings,
                current_gear_list,
                current_mini_list,
                force_db_seed=False,
            )
            if n_genomes is None:
                n_genomes = len(pop)
            if len(pop) != int(n_genomes):
                raise RuntimeError(f"Population size changed across runs: {len(pop)} != {n_genomes}")
            pops_encoded.append(registry.encode_population(pop))

        initial_populations = np.stack(pops_encoded, axis=0).astype(np.int32, copy=False)

    color_flags = {
        "is_p_ft": 1 if p_color == "Beat" else 0,
        "is_s_ft": 1 if s_color == "Beat" else 0,
        "is_p_ff": 1 if p_color == "Vibe" else 0,
        "is_s_ff": 1 if s_color == "Vibe" else 0,
        "is_p_pp": 1 if p_color == "Chill" else 0,
        "is_s_pp": 1 if s_color == "Chill" else 0,
        "is_p_cm": 1 if p_color == "Flow" else 0,
        "is_s_cm": 1 if s_color == "Flow" else 0,
        "is_p_fm": 1 if p_color == "Rush" else 0,
        "is_s_fm": 1 if s_color == "Rush" else 0,
        "is_p_ov": 1 if selected_color == p_color else 0,
        "is_s_ov": 1 if selected_color == s_color else 0,
    }

    elite_count = safe_int(cfg.get("IterationEngine", "GPU_GA_EliteCount", fallback=GA_ELITISM), GA_ELITISM)
    elite_count = max(0, int(elite_count))

    return _NativeSong(
        fp=str(fp),
        song_name=str(found_song_name),
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
        initial_populations=initial_populations,
        item_stats=np.asarray(gpu_data["item_stats"], dtype=np.int32),
        slot_start=np.asarray(gpu_data["slot_start"], dtype=np.int32),
        slot_count=np.asarray(gpu_data["slot_count"], dtype=np.int32),
        base_fixed_stats_arr=np.asarray(base_fixed_stats_arr, dtype=np.int32),
        elite_count=int(elite_count),
        mutation_rate=float(mutation_rate),
        immigrant_rate=float(immigrant_rate),
        tournament_k=int(tournament_k),
    )


def run_native_inflight_song_pipeline(
    tasks: list[tuple],
    *,
    in_flight_songs: int,
    completed_songs: set[str],
    memory_resume_tracker=None,
    post_queue=None,
    total_tasks: int | None = None,
) -> None:
    if not tasks:
        return

    inflight_limit = max(1, int(in_flight_songs))
    inflight_limit = min(inflight_limit, len(tasks))
    prep_limit = max(1, inflight_limit * 2)

    fg_every = 12
    try:
        cfg0 = cfg_from_dict(tasks[0][3] or {})
        fg_every = safe_int(cfg0.get("IterationEngine", "FG_InterleaveEvery", fallback=12), 12)
    except Exception:
        fg_every = 12
    fg_every = max(1, int(fg_every))

    fg_drain_at_end = True
    try:
        fg_drain_at_end = cfg0.getboolean("IterationEngine", "FG_DrainAtEnd", fallback=True)
    except Exception:
        fg_drain_at_end = True

    gpu_executor = get_gpu_executor()
    gpu_executor.start(in_process=True)
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)

    post_sender = _PostSender(post_queue) if post_queue is not None else None

    def _post(item: dict) -> None:
        if post_sender is not None:
            post_sender.send(item)

    pending_tasks = deque(t for t in tasks if t[1] not in completed_songs)
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
    prep_inflight: deque[tuple[tuple, concurrent.futures.Future]] = deque()

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
    fg_futures: deque[concurrent.futures.Future] = deque()
    ga_completed_since_last_fg = 0

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

    # Prime the pipeline: pre-prepare a small backlog synchronously so the GPU queue
    # doesn't starve on the first few song boundaries while prep workers spin up.
    prime_target = min(2, inflight_limit, len(pending_tasks))
    for _ in range(int(prime_target)):
        first = pending_tasks.popleft()
        song_name = first[1]
        if song_name in completed_songs:
            continue
        try:
            prepared.append(_prepare_song(first))
        except Exception as exc:
            _post(
                {
                    "_error": str(exc),
                    "_error_type": type(exc).__name__,
                    "_song_name": song_name,
                    "song": song_name,
                }
            )
            completed_songs.add(song_name)
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

            did_work = False

            # Move completed song preps into the staging queue.
            for task, fut in list(prep_inflight):
                if not fut.done():
                    continue
                prep_inflight.remove((task, fut))
                did_work = True
                song_name = task[1]
                if song_name in completed_songs:
                    continue
                try:
                    prepared.append(fut.result())
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
                        }
                    )
                    completed_songs.add(song_name)
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
                    song.fg_prep_future.result()
                except Exception as exc:
                    _post(
                        {
                            "_error": str(exc),
                            "_error_type": type(exc).__name__,
                            "_song_name": song.song_name,
                            "song": song.song_name,
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
                if prepared and len(ga_inflight) < inflight_limit:
                    song = prepared.popleft()
                    payload = {
                        "calc_song": song.calc_song,
                        "ref_arrays": song.ref_arrays,
                        "song_slot": 0,
                        "item_stats": song.item_stats,
                        "slot_start": song.slot_start,
                        "slot_count": song.slot_count,
                        "base_fixed_stats_arr": song.base_fixed_stats_arr,
                        "initial_populations": song.initial_populations,
                        "n_generations": int(song.gens_per_run),
                        "elite_count": int(song.elite_count),
                        "mutation_rate": float(song.mutation_rate),
                        "immigrant_rate": float(song.immigrant_rate),
                        "tournament_k": int(song.tournament_k),
                        "color_flags": dict(song.color_flags),
                        "cfg_data": dict(song.cfg_data),
                    }
                    try:
                        handle = gpu_client.submit_gpu_native_ga_run(payload)
                    except Exception as exc:
                        _post(
                            {
                                "_error": str(exc),
                                "_error_type": type(exc).__name__,
                                "_song_name": song.song_name,
                                "song": song.song_name,
                            }
                        )
                        completed_songs.add(song.song_name)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song.song_name)
                        did_work = True
                        continue

                    song.ga_future = handle.future
                    ga_inflight.append(song)
                    did_work = True
                    continue

                # CPU prep: keep a staging buffer of prepared jobs so the GPU queue
                # doesn't starve if CPU prep briefly falls behind GPU throughput.
                if pending_tasks and (len(prepared) + len(prep_inflight) < prep_limit):
                    nxt = pending_tasks.popleft()
                    if nxt[1] in completed_songs:
                        did_work = True
                        continue
                    try:
                        prep_inflight.append((nxt, prep_executor.submit(_prepare_song, nxt)))
                    except Exception as exc:
                        _post(
                            {
                                "_error": str(exc),
                                "_error_type": type(exc).__name__,
                                "_song_name": nxt[1],
                                "song": nxt[1],
                            }
                        )
                        completed_songs.add(nxt[1])
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
                        }
                    )
                    completed_songs.add(song.song_name)
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(song.song_name)
                    continue

                song.ga_future = None
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
                    completed_songs.add(song.song_name)
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(song.song_name)
                    continue
                finally:
                    song.decode_future = None

                song.best_data = best_data
                song.best_gear = best_gear
                song.best_minis = best_minis
                song.ga_candidates = list(ga_candidates or [])

                if song.manual_force_greats or song.force_greats_finder:
                    pending_fg.append(song)
                    if song.fg_prep_future is None:
                        try:
                            song.fg_prep_future = fg_prep_executor.submit(_prepare_fg_job_sync, song)
                            fg_prep_inflight.append(song)
                        except Exception:
                            song.fg_prep_future = None

                _post(
                    {
                        "_deferred_post": True,
                        "_pending_fg_job": bool(song.manual_force_greats or song.force_greats_finder),
                        "song": song.song_name,
                        "db_key": song.song_name,
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

                completed_songs.add(song.song_name)
                if memory_resume_tracker:
                    memory_resume_tracker.mark_completed(song.song_name)

            # Reap completed FG workers (capture errors).
            if fg_futures:
                still_pending: deque[concurrent.futures.Future] = deque()
                for fut in list(fg_futures):
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
                    else:
                        still_pending.append(fut)
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
                        fg_futures.append(
                            fg_executor.submit(
                                _run_fg_job_sync,
                                fg_song,
                                gpu_client=gpu_client,
                                post_sender=post_sender,
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
                break

            # Avoid tight spin.
            if not did_work:
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
                        fg_done = sum(1 for f in fg_futures if f.done())
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
                for _task, fut in prep_inflight:
                    if fut is not None:
                        wait_futures.append(fut)
                for song in decode_inflight:
                    if song.decode_future is not None:
                        wait_futures.append(song.decode_future)
                for song in fg_prep_inflight:
                    if song.fg_prep_future is not None:
                        wait_futures.append(song.fg_prep_future)
                for fut in fg_futures:
                    wait_futures.append(fut)
                if wait_futures:
                    concurrent.futures.wait(
                        wait_futures,
                        timeout=0.02,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                else:
                    time.sleep(0.001)

    finally:
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
    return decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=song.registry,
        cfg_data=song.cfg_data,
        base_stats_fixed=song.fixed_stats,
        fg_candidate_limit=safe_int(
            song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        ),
    )


def _prepare_fg_job_sync(song: _NativeSong) -> None:
    cfg = song.cfg

    fg_candidate_limit = safe_int(
        cfg.get("IterationEngine", "FG_CandidateLimit", fallback=FG_CANDIDATE_LIMIT),
        FG_CANDIDATE_LIMIT,
    )
    fg_candidate_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(fg_candidate_limit)))
    song.fg_candidate_limit = int(fg_candidate_limit)

    fg_search_radius = None
    try:
        raw_fg_radius = str(cfg.get("IterationEngine", "FG_SearchRadius", fallback="") or "").strip()
    except Exception:
        raw_fg_radius = ""
    if raw_fg_radius:
        fg_search_radius = safe_int(raw_fg_radius, -1)
    song.fg_search_radius = fg_search_radius

    ga_candidates = list(song.ga_candidates or [])
    ga_candidates.sort(key=lambda x: x.get("Score", 0), reverse=True)
    if ga_candidates and len(ga_candidates) > fg_candidate_limit:
        ga_candidates = ga_candidates[:fg_candidate_limit]
    song.ga_candidates = ga_candidates

    def build_details(data_dict: dict) -> dict:
        if not data_dict:
            return {}
        return {
            "FT": data_dict.get("FT", 0),
            "FF": data_dict.get("FF", 0),
            "GemCounts": data_dict.get("GemCounts", {}),
            "Stats": data_dict.get("Stats", {}),
            "SelectedElement": data_dict.get("Selected Element", ""),
            "PrimaryColor": song.meta_primary_color,
            "SecondaryColor": song.meta_secondary_color,
            "Difficulty": song.effective_difficulty,
            "ForceGreats": data_dict.get("ForceGreats", {}),
        }

    song.loadout_entries = build_loadout_entries(
        song.song_name,
        bool(song.use_evo_db),
        ga_candidates,
        fg_candidate_limit,
        song.gears_by_name,
        song.minis_by_name,
        build_details,
    )

    song.fg_db_loadouts_full_count = 0
    if song.use_evo_db:
        try:
            from gear_optimizer.data.database import get_best_loadouts

            db_loadouts_full = get_best_loadouts(
                song.song_name,
                limit=fg_candidate_limit,
                gears_by_name=song.gears_by_name,
                minis_by_name=song.minis_by_name,
            )
            song.fg_db_loadouts_full_count = len(db_loadouts_full)
        except Exception:
            song.fg_db_loadouts_full_count = 0


def _run_fg_job_sync(
    song: _NativeSong,
    *,
    gpu_client: GpuServiceClient,
    post_sender: Optional[_PostSender] = None,
) -> None:
    if song.fg_prep_future is not None:
        try:
            song.fg_prep_future.result()
        except Exception:
            pass
        finally:
            song.fg_prep_future = None

    if song.loadout_entries is None:
        _prepare_fg_job_sync(song)

    def build_details(data_dict: dict) -> dict:
        if not data_dict:
            return {}
        return {
            "FT": data_dict.get("FT", 0),
            "FF": data_dict.get("FF", 0),
            "GemCounts": data_dict.get("GemCounts", {}),
            "Stats": data_dict.get("Stats", {}),
            "SelectedElement": data_dict.get("Selected Element", ""),
            "PrimaryColor": song.meta_primary_color,
            "SecondaryColor": song.meta_secondary_color,
            "Difficulty": song.effective_difficulty,
            "ForceGreats": data_dict.get("ForceGreats", {}),
        }

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

    if post_sender is not None:
        post_sender.send(
            {
                "_fg_update": True,
                "song": song.song_name,
                "db_key": song.song_name,
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
            "SelectedElement": data.get("Selected Element", ""),
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
