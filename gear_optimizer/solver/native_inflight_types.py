from __future__ import annotations

import concurrent.futures
import configparser
from dataclasses import dataclass, field, fields
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.types import CalcSong, JsonDict, RefArrays
from gear_optimizer.solver.item_registry import ItemRegistry


@dataclass
class NativeSongConfig:
    fp: str = ""
    song_name: str = ""
    task_key: str = ""
    ga_seed: int | None = None
    db_key: str = ""
    effective_difficulty: str = ""
    cfg_dict: JsonDict = field(default_factory=dict)
    cfg: configparser.ConfigParser | None = None
    paths: dict[str, Any] | None = None
    ga_depth: int = 0
    fg_debug: bool = False


@dataclass
class NativeSongGPUInputs:
    ref_arrays: RefArrays = field(default_factory=dict)
    all_gears: list[Any] = field(default_factory=list)
    all_minis: list[Any] = field(default_factory=list)
    gears_by_name: dict[str, Any] = field(default_factory=dict)
    minis_by_name: dict[str, Any] = field(default_factory=dict)
    calc_song: CalcSong | JsonDict = field(default_factory=dict)
    meta_primary_color: str = ""
    meta_secondary_color: str = ""
    fixed_stats: JsonDict = field(default_factory=dict)
    current_gear_list: list[Any] = field(default_factory=list)
    current_mini_list: list[Any] = field(default_factory=list)
    force_greats_config: list[Any] = field(default_factory=list)
    manual_force_greats: bool = False
    registry: ItemRegistry | None = None
    cfg_data: JsonDict = field(default_factory=dict)
    color_flags: dict[str, Any] = field(default_factory=dict)
    gens_per_run: int = 0
    num_runs: int = 0
    n_genomes: int = 0
    item_stats: np.ndarray | None = None
    slot_start: np.ndarray | None = None
    slot_count: np.ndarray | None = None
    base_fixed_stats_arr: np.ndarray | None = None
    elite_count: int = 0
    mutation_rate: float = 0.0
    immigrant_rate: float = 0.0
    tournament_k: int = 0
    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k: int = 0
    init_heuristic_copies: int = 25
    db_seed_ids: Optional[np.ndarray] = None
    db_seed_prob: float = 0.0
    db_seed_copies: int = 1
    db_seed_mutations: int = 1


@dataclass
class NativeSongPrepState:
    cpu_prewarm_future: Optional[concurrent.futures.Future] = None
    cpu_prewarm_s: float = 0.0
    cpu_prewarm_submit_t0: float | None = None
    cpu_prep_s: float = 0.0
    fg_chart_scorer_prewarmed: bool = False


@dataclass
class NativeSongGAState:
    ga_future: Optional[concurrent.futures.Future] = None
    ga_submit_t0: float | None = None
    ga_initial_populations: Optional[list[Any]] = None
    outer_engine: str = ""


@dataclass
class NativeSongDecodeState:
    decode_future: Optional[concurrent.futures.Future] = None
    decode_submit_t0: float | None = None
    ga_candidates: Optional[list[JsonDict]] = None
    ga_persistence_candidates: Optional[list[JsonDict]] = None
    best_data: Optional[JsonDict] = None
    best_gear: Optional[list[Any]] = None
    best_minis: Optional[list[Any]] = None
    cpu_decode_s: float = 0.0


@dataclass
class NativeSongFGState:
    fg_variants: Optional[list[JsonDict]] = None
    fg_candidate_limit: int = 0
    fg_search_radius: Optional[int] = None
    fg_calc_song: Optional[CalcSong | JsonDict] = None
    fg_prep_future: Optional[concurrent.futures.Future] = None
    fg_queued_t0: float | None = None
    fg_direct_ga_candidates: bool = False
    fg_static_prep_future: Optional[concurrent.futures.Future] = None
    fg_static_prep_done: bool = False
    fg_dynamic_prep_done: bool = False
    fg_static_prep_submit_t0: float | None = None
    fg_prep_submit_t0: float | None = None
    fg_build_details: Any | None = None
    loadout_entries: Optional[dict[str, JsonDict]] = None
    cpu_fg_static_prep_s: float = 0.0
    cpu_fg_prep_s: float = 0.0
    cpu_fg_run_s: float = 0.0


@dataclass
class NativeSongDBState:
    prev_record: Optional[JsonDict] = None
    db_best_score: int = 0
    db_best_fg_score: int = 0
    db_baseline_valid: bool = False
    attempt_lifetime: int = 0
    prev_attempts_first: int = 0
    record_info: Optional[JsonDict] = None
    db_loadouts_future: Optional[concurrent.futures.Future] = None
    db_loadouts_full: Optional[list[JsonDict]] = None


@dataclass
class NativeSongBundleState:
    bundle_parent_task: Any | None = None
    bundle_task_key: str = ""
    bundle_repeat_index: int = 0
    bundle_repeat_total: int = 0
    bundle_wait_for_fg: bool = False


@dataclass
class NativeSongPostState:
    deferred_post_emitted: bool = False
    await_fg_completion_progress: bool = False


@dataclass
class NativeSongRuntimeState:
    song_slot: int = 0
    prep: NativeSongPrepState = field(default_factory=NativeSongPrepState)
    ga: NativeSongGAState = field(default_factory=NativeSongGAState)
    decode: NativeSongDecodeState = field(default_factory=NativeSongDecodeState)
    fg: NativeSongFGState = field(default_factory=NativeSongFGState)
    db: NativeSongDBState = field(default_factory=NativeSongDBState)
    bundle: NativeSongBundleState = field(default_factory=NativeSongBundleState)
    post: NativeSongPostState = field(default_factory=NativeSongPostState)


def _field_names(cls: type) -> tuple[str, ...]:
    return tuple(field.name for field in fields(cls))


_FIELD_PATH_BY_NAME = {
    **{field_name: ("config",) for field_name in _field_names(NativeSongConfig)},
    **{field_name: ("gpu_inputs",) for field_name in _field_names(NativeSongGPUInputs)},
    "song_slot": ("runtime",),
    **{field_name: ("runtime", "prep") for field_name in _field_names(NativeSongPrepState)},
    **{field_name: ("runtime", "ga") for field_name in _field_names(NativeSongGAState)},
    **{field_name: ("runtime", "decode") for field_name in _field_names(NativeSongDecodeState)},
    **{field_name: ("runtime", "fg") for field_name in _field_names(NativeSongFGState)},
    **{field_name: ("runtime", "db") for field_name in _field_names(NativeSongDBState)},
    **{field_name: ("runtime", "bundle") for field_name in _field_names(NativeSongBundleState)},
    **{field_name: ("runtime", "post") for field_name in _field_names(NativeSongPostState)},
}


@dataclass
class NativeSong:
    config: NativeSongConfig
    gpu_inputs: NativeSongGPUInputs
    runtime: NativeSongRuntimeState


def _resolve_owner(root: object | None, path: tuple[str, ...]) -> object | None:
    current = root
    for segment in path:
        if current is None:
            return None
        current = getattr(current, str(segment), None)
    return current


def native_song_get(song: object, field_name: str, default=None):
    path = _FIELD_PATH_BY_NAME.get(str(field_name))
    if path is None:
        return default
    owner = _resolve_owner(song, path)
    if owner is None:
        return default
    return getattr(owner, str(field_name), default)


def native_song_group(song: object, group_name: str):
    group = _resolve_owner(song, tuple(str(group_name).split(".")))
    if group is None:
        raise AttributeError(f"Unknown native song group: {group_name}")
    return group


def native_song_set(song: object, field_name: str, value) -> None:
    path = _FIELD_PATH_BY_NAME.get(str(field_name))
    if path is None:
        raise AttributeError(f"Unknown native song field: {field_name}")
    owner = _resolve_owner(song, path)
    if owner is None:
        raise AttributeError(f"Unknown native song field owner for: {field_name}")
    setattr(owner, str(field_name), value)


def native_song_label(song: object, *, fallback_id: bool = False) -> str:
    try:
        config = getattr(song, "config", None)
        label = str(getattr(config, "task_key", "") or getattr(config, "song_name", "") or "").strip()
        if label:
            return label
    except Exception:
        pass
    return str(id(song)) if bool(fallback_id) else ""


def make_native_song(**kwargs) -> NativeSong:
    """Build a NativeSong from flat keyword args, distributing to the correct sub-struct."""
    config = NativeSongConfig()
    gpu_inputs = NativeSongGPUInputs()
    runtime = NativeSongRuntimeState()
    roots = {
        "config": config,
        "gpu_inputs": gpu_inputs,
        "runtime": runtime,
    }
    pending_assignments: list[tuple[object, str, Any]] = []
    unknown_fields: list[str] = []
    for k, v in kwargs.items():
        key = str(k)
        if hasattr(config, key):
            pending_assignments.append((config, key, v))
            continue
        if hasattr(gpu_inputs, key):
            pending_assignments.append((gpu_inputs, key, v))
            continue
        path = _FIELD_PATH_BY_NAME.get(key)
        if path:
            owner = _resolve_owner(roots.get(path[0]), path[1:])
            if owner is not None:
                pending_assignments.append((owner, key, v))
                continue
        unknown_fields.append(key)
    if unknown_fields:
        raise TypeError(
            "Unexpected native song field(s): " + ", ".join(sorted(dict.fromkeys(unknown_fields)))
        )
    for owner, key, value in pending_assignments:
        setattr(owner, key, value)
    return NativeSong(config=config, gpu_inputs=gpu_inputs, runtime=runtime)
