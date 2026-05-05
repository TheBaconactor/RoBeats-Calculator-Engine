from __future__ import annotations

import concurrent.futures
import configparser
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.types import CalcSong, JsonDict, RefArrays
from gear_optimizer.solver.item_registry import ItemRegistry


@dataclass
class _NativeSongConfig:
    fp: str = ""
    song_name: str = ""
    task_key: str = ""
    ga_seed: int | None = None
    db_key: str = ""
    effective_difficulty: str = ""
    cfg_dict: JsonDict = field(default_factory=dict)
    cfg: configparser.ConfigParser | None = None
    paths: dict[str, Any] | None = None
    use_evo_db: bool = True
    auto_buff: bool = False
    ga_depth: int = 0
    fg_debug: bool = False


@dataclass
class _NativeSongGPUInputs:
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
    enable_gear: bool = False
    enable_mini: bool = False
    force_greats_finder: bool = False
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
class _NativeSongRuntimeState:
    song_slot: int = 0
    ga_future: Optional[concurrent.futures.Future] = None
    decode_future: Optional[concurrent.futures.Future] = None
    ga_candidates: Optional[list[JsonDict]] = None
    ga_persistence_candidates: Optional[list[JsonDict]] = None
    best_data: Optional[JsonDict] = None
    best_gear: Optional[list[Any]] = None
    best_minis: Optional[list[Any]] = None
    record_info: Optional[JsonDict] = None
    db_loadouts_future: Optional[concurrent.futures.Future] = None
    db_loadouts_full: Optional[list[JsonDict]] = None
    cpu_prewarm_future: Optional[concurrent.futures.Future] = None
    loadout_entries: Optional[dict[str, JsonDict]] = None
    fg_variants: Optional[list[JsonDict]] = None
    fg_candidate_limit: int = 0
    fg_search_radius: Optional[int] = None
    fg_calc_song: Optional[CalcSong | JsonDict] = None
    fg_prep_future: Optional[concurrent.futures.Future] = None
    fg_queued_t0: float | None = None
    fg_direct_ga_candidates: bool = False
    prev_record: Optional[JsonDict] = None
    db_best_score: int = 0
    attempt_lifetime: int = 0
    prev_attempts_first: int = 0
    db_best_fg_score: int = 0
    db_baseline_valid: bool = False


_CONFIG_FIELDS = (
    "fp",
    "song_name",
    "task_key",
    "ga_seed",
    "db_key",
    "effective_difficulty",
    "cfg_dict",
    "cfg",
    "paths",
    "use_evo_db",
    "auto_buff",
    "ga_depth",
    "fg_debug",
)

_GPU_INPUT_FIELDS = (
    "ref_arrays",
    "all_gears",
    "all_minis",
    "gears_by_name",
    "minis_by_name",
    "calc_song",
    "meta_primary_color",
    "meta_secondary_color",
    "fixed_stats",
    "current_gear_list",
    "current_mini_list",
    "enable_gear",
    "enable_mini",
    "force_greats_finder",
    "force_greats_config",
    "manual_force_greats",
    "registry",
    "cfg_data",
    "color_flags",
    "gens_per_run",
    "num_runs",
    "n_genomes",
    "item_stats",
    "slot_start",
    "slot_count",
    "base_fixed_stats_arr",
    "elite_count",
    "mutation_rate",
    "immigrant_rate",
    "tournament_k",
    "init_heuristic_topk",
    "init_heuristic_k",
    "init_heuristic_copies",
    "db_seed_ids",
    "db_seed_prob",
    "db_seed_copies",
    "db_seed_mutations",
)

_RUNTIME_FIELDS = (
    "song_slot",
    "ga_future",
    "decode_future",
    "ga_candidates",
    "ga_persistence_candidates",
    "best_data",
    "best_gear",
    "best_minis",
    "record_info",
    "db_loadouts_future",
    "db_loadouts_full",
    "cpu_prewarm_future",
    "loadout_entries",
    "fg_variants",
    "fg_candidate_limit",
    "fg_search_radius",
    "fg_calc_song",
    "fg_prep_future",
    "fg_queued_t0",
    "fg_direct_ga_candidates",
    "prev_record",
    "db_best_score",
    "attempt_lifetime",
    "prev_attempts_first",
    "db_best_fg_score",
    "db_baseline_valid",
)

_FIELD_GROUP_BY_NAME = {
    **{field_name: "config" for field_name in _CONFIG_FIELDS},
    **{field_name: "gpu_inputs" for field_name in _GPU_INPUT_FIELDS},
    **{field_name: "runtime" for field_name in _RUNTIME_FIELDS},
}


@dataclass
class _NativeSong:
    config: _NativeSongConfig
    gpu_inputs: _NativeSongGPUInputs
    runtime: _NativeSongRuntimeState


def native_song_get(song: object, field_name: str, default=None):
    group_name = _FIELD_GROUP_BY_NAME.get(str(field_name))
    if group_name:
        group = getattr(song, group_name, None)
        if group is not None:
            return getattr(group, str(field_name), default)
    return getattr(song, str(field_name), default)


def native_song_group(song: object, group_name: str):
    group = getattr(song, str(group_name), None)
    return group if group is not None else song


def native_song_set(song: object, field_name: str, value) -> None:
    group_name = _FIELD_GROUP_BY_NAME.get(str(field_name))
    if group_name:
        group = getattr(song, group_name, None)
        if group is not None:
            setattr(group, str(field_name), value)
            return
    setattr(song, str(field_name), value)
