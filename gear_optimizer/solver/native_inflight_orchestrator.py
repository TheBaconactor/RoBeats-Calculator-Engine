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
import time
from collections import deque
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
    ga_candidates: Optional[list[dict]] = None
    best_data: Optional[dict] = None
    best_gear: Optional[list] = None
    best_minis: Optional[list] = None

    loadout_entries: Optional[dict] = None
    fg_variants: Optional[list[dict]] = None

    def __post_init__(self) -> None:
        if self.ga_candidates is None:
            self.ga_candidates = []
        if self.fg_variants is None:
            self.fg_variants = []


def _prepare_song(task: tuple) -> _NativeSong:
    from gear_optimizer.core.constants import GA_ELITISM, GA_MUTATION_RATE
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

    prev_record, known_loadouts = load_database_context(
        found_song_name, bool(use_evo_db), gears_by_name, minis_by_name
    )

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

    pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
    if pools is None:
        raise RuntimeError("initialize_pools returned None")
    if len(pools) == 4:
        gear_pool, mini_pool, _total_before, _total_after = pools
    else:
        gear_pool, mini_pool, _total_before, _total_after, _whitelisted_minis = pools
    if gear_pool is None:
        raise RuntimeError("initialize_pools failed (gear_pool is None)")

    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_data = registry.to_gpu_arrays()

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

    mutation_rate = safe_float(cfg.get("IterationEngine", "GPU_GA_MutationRate", fallback=GA_MUTATION_RATE), GA_MUTATION_RATE)
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

    gpu_executor = get_gpu_executor()
    gpu_executor.start(in_process=True)
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)

    pending_tasks = deque(t for t in tasks if t[1] not in completed_songs)
    prepared: deque[_NativeSong] = deque()
    pending_fg: deque[_NativeSong] = deque()

    # GA jobs submitted to the GPU executor (in-order). We intentionally keep a
    # backlog so CPU-side decode/post-processing can't create GPU idle gaps.
    ga_inflight: deque[_NativeSong] = deque()

    fg_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="FG")
    fg_future: Optional[concurrent.futures.Future] = None
    ga_completed_since_last_fg = 0

    try:
        while pending_tasks or prepared or pending_fg or ga_inflight or fg_future is not None:
            if memory_release_requested():
                break

            did_work = False

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
                        if post_queue is not None:
                            post_queue.put(
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
                if pending_tasks and len(prepared) < prep_limit:
                    nxt = pending_tasks.popleft()
                    if nxt[1] in completed_songs:
                        did_work = True
                        continue
                    try:
                        prepared.append(_prepare_song(nxt))
                    except Exception as exc:
                        if post_queue is not None:
                            post_queue.put(
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

            # Finalize completed GA jobs in FIFO order.
            while ga_inflight and ga_inflight[0].ga_future is not None and ga_inflight[0].ga_future.done():
                song = ga_inflight.popleft()
                did_work = True

                try:
                    runs_payload = song.ga_future.result()
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
                except Exception as exc:
                    if post_queue is not None:
                        post_queue.put(
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

                song.best_data = best_data
                song.best_gear = best_gear
                song.best_minis = best_minis
                song.ga_candidates = list(ga_candidates or [])

                if song.manual_force_greats or song.force_greats_finder:
                    pending_fg.append(song)

                if post_queue is not None:
                    post_queue.put(
                        {
                            "_deferred_post": True,
                            "_pending_fg_job": bool(song.manual_force_greats or song.force_greats_finder),
                            "song": song.song_name,
                            "db_key": song.song_name,
                            "file_path": song.fp,
                            "difficulty": song.effective_difficulty,
                            "use_evo_db": bool(song.use_evo_db),
                            "cfg_dict": song.cfg_dict,
                            "ref_arrays": song.ref_arrays,
                            "calc_song": song.calc_song,
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
                ga_completed_since_last_fg += 1

            # Reap FG worker (capture errors) and schedule the next one.
            if fg_future is not None and fg_future.done():
                did_work = True
                try:
                    fg_future.result()
                except Exception:
                    pass
                fg_future = None

            if (
                fg_future is None
                and pending_fg
                and (ga_completed_since_last_fg >= fg_every or (not pending_tasks and not prepared and not ga_inflight))
            ):
                fg_song = pending_fg.popleft()
                fg_future = fg_executor.submit(
                    _run_fg_job_sync,
                    fg_song,
                    gpu_client=gpu_client,
                    post_queue=post_queue,
                )
                ga_completed_since_last_fg = 0
                did_work = True

            # Avoid tight spin.
            if not did_work:
                wait_futures: list[concurrent.futures.Future] = []
                if ga_inflight and ga_inflight[0].ga_future is not None:
                    wait_futures.append(ga_inflight[0].ga_future)
                if fg_future is not None:
                    wait_futures.append(fg_future)
                if wait_futures:
                    concurrent.futures.wait(
                        wait_futures,
                        timeout=0.05,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                else:
                    time.sleep(0.001)

    finally:
        try:
            fg_executor.shutdown(wait=True, cancel_futures=True)
        except Exception:
            pass
        try:
            gpu_client.close(timeout=2.0)
        except Exception:
            pass
        try:
            if gpu_executor.is_running:
                gpu_executor.stop()
        except Exception:
            pass


def _run_fg_job_sync(song: _NativeSong, *, gpu_client: GpuServiceClient, post_queue=None) -> None:
    cfg = song.cfg

    fg_candidate_limit = safe_int(
        cfg.get("IterationEngine", "FG_CandidateLimit", fallback=FG_CANDIDATE_LIMIT),
        FG_CANDIDATE_LIMIT,
    )
    fg_candidate_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(fg_candidate_limit)))

    fg_search_radius = None
    try:
        raw_fg_radius = str(cfg.get("IterationEngine", "FG_SearchRadius", fallback="") or "").strip()
    except Exception:
        raw_fg_radius = ""
    if raw_fg_radius:
        fg_search_radius = safe_int(raw_fg_radius, -1)

    ga_candidates = list(song.ga_candidates or [])
    ga_candidates.sort(key=lambda x: x.get("Score", 0), reverse=True)
    if ga_candidates and len(ga_candidates) > fg_candidate_limit:
        ga_candidates = ga_candidates[:fg_candidate_limit]

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

    loadout_entries = build_loadout_entries(
        song.song_name,
        bool(song.use_evo_db),
        ga_candidates,
        fg_candidate_limit,
        song.gears_by_name,
        song.minis_by_name,
        build_details,
    )
    song.loadout_entries = loadout_entries

    db_loadouts_full_count = 0
    if song.use_evo_db:
        try:
            from gear_optimizer.data.database import get_best_loadouts

            db_loadouts_full = get_best_loadouts(
                song.song_name,
                limit=fg_candidate_limit,
                gears_by_name=song.gears_by_name,
                minis_by_name=song.minis_by_name,
            )
            db_loadouts_full_count = len(db_loadouts_full)
        except Exception:
            db_loadouts_full_count = 0

    fg_variants = process_force_greats(
        loadout_entries,
        bool(song.manual_force_greats),
        bool(song.force_greats_finder),
        song.force_greats_config,
        song.calc_song,
        song.ref_arrays,
        song.meta_primary_color,
        build_details,
        int(db_loadouts_full_count),
        use_gpu=True,
        fg_search_radius=fg_search_radius,
        perf_timing=_truthy(os.environ.get("PERF_TIMING", "0")),
        gpu_client=gpu_client,
    )

    song.fg_variants = list(fg_variants or [])

    if post_queue is not None:
        post_queue.put(
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
