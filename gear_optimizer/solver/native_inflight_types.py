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
class _NativeSongPrepState:
    cpu_prewarm_future: Optional[concurrent.futures.Future] = None
    cpu_prewarm_s: float = 0.0
    cpu_prewarm_submit_t0: float | None = None
    cpu_prep_s: float = 0.0
    fg_chart_scorer_prewarmed: bool = False


@dataclass
class _NativeSongGAState:
    ga_future: Optional[concurrent.futures.Future] = None
    ga_submit_t0: float | None = None
    ga_initial_populations: Optional[list[Any]] = None
    outer_engine: str = ""


@dataclass
class _NativeSongDecodeState:
    decode_future: Optional[concurrent.futures.Future] = None
    decode_submit_t0: float | None = None
    ga_candidates: Optional[list[JsonDict]] = None
    ga_persistence_candidates: Optional[list[JsonDict]] = None
    best_data: Optional[JsonDict] = None
    best_gear: Optional[list[Any]] = None
    best_minis: Optional[list[Any]] = None
    cpu_decode_s: float = 0.0


@dataclass
class _NativeSongFGState:
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
class _NativeSongDBState:
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
class _NativeSongBundleState:
    bundle_parent_task: Any | None = None
    bundle_task_key: str = ""
    bundle_repeat_index: int = 0
    bundle_repeat_total: int = 0
    bundle_wait_for_fg: bool = False


@dataclass
class _NativeSongPostState:
    deferred_post_emitted: bool = False
    await_fg_completion_progress: bool = False


@dataclass
class _NativeSongRuntimeState:
    song_slot: int = 0
    prep: _NativeSongPrepState = field(default_factory=_NativeSongPrepState)
    ga: _NativeSongGAState = field(default_factory=_NativeSongGAState)
    decode: _NativeSongDecodeState = field(default_factory=_NativeSongDecodeState)
    fg: _NativeSongFGState = field(default_factory=_NativeSongFGState)
    db: _NativeSongDBState = field(default_factory=_NativeSongDBState)
    bundle: _NativeSongBundleState = field(default_factory=_NativeSongBundleState)
    post: _NativeSongPostState = field(default_factory=_NativeSongPostState)

    def __getattr__(self, name: str):
        path = _RUNTIME_COMPAT_FIELD_PATH_BY_NAME.get(str(name))
        if path:
            owner = _resolve_owner(self, path)
            if owner is not None:
                return getattr(owner, str(name))
        raise AttributeError(f"{type(self).__name__!s} object has no attribute {name!r}")

    def __setattr__(self, name: str, value) -> None:
        if name in self.__dataclass_fields__:
            substate_cls = _RUNTIME_SUBSTATE_CLASS_BY_FIELD.get(str(name))
            if substate_cls is not None:
                if isinstance(value, dict):
                    value = substate_cls(**value)
                elif value is None:
                    value = substate_cls()
                elif not isinstance(value, substate_cls):
                    value = value
            object.__setattr__(self, name, value)
            return
        path = _RUNTIME_COMPAT_FIELD_PATH_BY_NAME.get(str(name))
        if path:
            owner = _resolve_owner(self, path)
            if owner is not None:
                setattr(owner, str(name), value)
                return
        object.__setattr__(self, name, value)


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

_RUNTIME_TOP_LEVEL_FIELDS = (
    "song_slot",
)

_RUNTIME_PREP_FIELDS = (
    "cpu_prewarm_future",
    "cpu_prewarm_s",
    "cpu_prewarm_submit_t0",
    "cpu_prep_s",
    "fg_chart_scorer_prewarmed",
)

_RUNTIME_GA_FIELDS = (
    "ga_future",
    "ga_submit_t0",
    "ga_initial_populations",
    "outer_engine",
)

_RUNTIME_DECODE_FIELDS = (
    "decode_future",
    "decode_submit_t0",
    "ga_candidates",
    "ga_persistence_candidates",
    "best_data",
    "best_gear",
    "best_minis",
    "cpu_decode_s",
)

_RUNTIME_FG_FIELDS = (
    "fg_variants",
    "fg_candidate_limit",
    "fg_search_radius",
    "fg_calc_song",
    "fg_prep_future",
    "fg_queued_t0",
    "fg_direct_ga_candidates",
    "fg_static_prep_future",
    "fg_static_prep_done",
    "fg_dynamic_prep_done",
    "fg_static_prep_submit_t0",
    "fg_prep_submit_t0",
    "fg_build_details",
    "loadout_entries",
    "cpu_fg_static_prep_s",
    "cpu_fg_prep_s",
    "cpu_fg_run_s",
)

_RUNTIME_DB_FIELDS = (
    "prev_record",
    "db_best_score",
    "db_best_fg_score",
    "db_baseline_valid",
    "attempt_lifetime",
    "prev_attempts_first",
    "record_info",
    "db_loadouts_future",
    "db_loadouts_full",
)

_RUNTIME_BUNDLE_FIELDS = (
    "bundle_parent_task",
    "bundle_task_key",
    "bundle_repeat_index",
    "bundle_repeat_total",
    "bundle_wait_for_fg",
)

_RUNTIME_POST_FIELDS = (
    "deferred_post_emitted",
    "await_fg_completion_progress",
)

_FIELD_PATH_BY_NAME = {
    **{field_name: ("config",) for field_name in _CONFIG_FIELDS},
    **{field_name: ("gpu_inputs",) for field_name in _GPU_INPUT_FIELDS},
    **{field_name: ("runtime",) for field_name in _RUNTIME_TOP_LEVEL_FIELDS},
    **{field_name: ("runtime", "prep") for field_name in _RUNTIME_PREP_FIELDS},
    **{field_name: ("runtime", "ga") for field_name in _RUNTIME_GA_FIELDS},
    **{field_name: ("runtime", "decode") for field_name in _RUNTIME_DECODE_FIELDS},
    **{field_name: ("runtime", "fg") for field_name in _RUNTIME_FG_FIELDS},
    **{field_name: ("runtime", "db") for field_name in _RUNTIME_DB_FIELDS},
    **{field_name: ("runtime", "bundle") for field_name in _RUNTIME_BUNDLE_FIELDS},
    **{field_name: ("runtime", "post") for field_name in _RUNTIME_POST_FIELDS},
}

_RUNTIME_COMPAT_FIELD_PATH_BY_NAME = {
    name: path[1:]
    for name, path in _FIELD_PATH_BY_NAME.items()
    if path and path[0] == "runtime" and len(path) > 1
}

_RUNTIME_SUBSTATE_CLASS_BY_FIELD = {
    "prep": _NativeSongPrepState,
    "ga": _NativeSongGAState,
    "decode": _NativeSongDecodeState,
    "fg": _NativeSongFGState,
    "db": _NativeSongDBState,
    "bundle": _NativeSongBundleState,
    "post": _NativeSongPostState,
}

_SONG_PRIVATE_COMPAT_FIELD_PATH_BY_NAME = {
    f"_{name}": path for name, path in _RUNTIME_COMPAT_FIELD_PATH_BY_NAME.items()
}

_SONG_PUBLIC_COMPAT_FIELD_PATH_BY_NAME = {
    "fg_static_prep_future": ("fg",),
}


@dataclass
class _NativeSong:
    config: _NativeSongConfig
    gpu_inputs: _NativeSongGPUInputs
    runtime: _NativeSongRuntimeState

    def __getattr__(self, name: str):
        name_s = str(name)
        if name_s.startswith("_"):
            path = _SONG_PRIVATE_COMPAT_FIELD_PATH_BY_NAME.get(name_s)
            if path:
                owner = _resolve_owner(self, ("runtime",) + path)
                if owner is not None:
                    return getattr(owner, name_s[1:])
        path = _SONG_PUBLIC_COMPAT_FIELD_PATH_BY_NAME.get(name_s)
        if path:
            owner = _resolve_owner(self, ("runtime",) + path)
            if owner is not None:
                return getattr(owner, name_s)
        raise AttributeError(f"{type(self).__name__!s} object has no attribute {name!r}")

    def __setattr__(self, name: str, value) -> None:
        if name in self.__dataclass_fields__:
            object.__setattr__(self, name, value)
            return
        name_s = str(name)
        if name_s.startswith("_"):
            path = _SONG_PRIVATE_COMPAT_FIELD_PATH_BY_NAME.get(name_s)
            if path:
                owner = _resolve_owner(self, ("runtime",) + path)
                if owner is not None:
                    setattr(owner, name_s[1:], value)
                    return
        path = _SONG_PUBLIC_COMPAT_FIELD_PATH_BY_NAME.get(name_s)
        if path:
            owner = _resolve_owner(self, ("runtime",) + path)
            if owner is not None:
                setattr(owner, name_s, value)
                return
        raise AttributeError(f"{type(self).__name__!s} object has no attribute {name!r}")


def _resolve_owner(root: object | None, path: tuple[str, ...]) -> object | None:
    current = root
    for segment in path:
        if current is None:
            return None
        current = getattr(current, str(segment), None)
    return current


def native_song_get(song: object, field_name: str, default=None):
    path = _FIELD_PATH_BY_NAME.get(str(field_name))
    if path:
        owner = _resolve_owner(song, path)
        if owner is not None:
            return getattr(owner, str(field_name), default)
    return getattr(song, str(field_name), default)


def native_song_group(song: object, group_name: str):
    group = _resolve_owner(song, tuple(str(group_name).split(".")))
    return group if group is not None else song


def native_song_set(song: object, field_name: str, value) -> None:
    path = _FIELD_PATH_BY_NAME.get(str(field_name))
    if path:
        owner = _resolve_owner(song, path)
        if owner is not None:
            setattr(owner, str(field_name), value)
            return
    setattr(song, str(field_name), value)


def make_native_song(**kwargs) -> _NativeSong:
    """Build a _NativeSong from flat keyword args, distributing to the correct sub-struct."""
    config = _NativeSongConfig()
    gpu_inputs = _NativeSongGPUInputs()
    runtime = _NativeSongRuntimeState()
    roots = {
        "config": config,
        "gpu_inputs": gpu_inputs,
        "runtime": runtime,
    }
    for k, v in kwargs.items():
        if hasattr(config, k):
            setattr(config, k, v)
            continue
        if hasattr(gpu_inputs, k):
            setattr(gpu_inputs, k, v)
            continue
        path = _FIELD_PATH_BY_NAME.get(str(k))
        if path:
            owner = _resolve_owner(roots.get(path[0]), path[1:])
            if owner is not None:
                setattr(owner, str(k), v)
                continue
        if hasattr(runtime, k):
            setattr(runtime, k, v)
    return _NativeSong(config=config, gpu_inputs=gpu_inputs, runtime=runtime)
