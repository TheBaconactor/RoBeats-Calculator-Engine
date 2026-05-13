"""
Core typing helpers for runtime boundaries.

This module intentionally focuses on *interfaces between subsystems* (pipeline ↔ solver ↔ persistence ↔ GPU IPC).
The goal is to make refactors and performance work safer without forcing a full codebase-wide typing overhaul.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple, TypedDict

import numpy as np

JsonDict = Dict[str, Any]


class CalcSongData(TypedDict, total=False):
    """
    Normalized song arrays used by scoring / GPU timeline precompute.

    Notes:
    - Arrays are typically numpy, but may be lists during early parsing.
    - Some pipelines add additional analysis keys used by FG timing.
    """

    timestamps: np.ndarray
    chart_timestamps: np.ndarray
    note_types: np.ndarray


class CalcSong(TypedDict, total=False):
    """
    Canonical per-song payload.

    Shapes:
    - metadata: dict with song header values (Song Name, Difficulty, Primary Color, Secondary Color, etc.)
    - song_data: dict of arrays (timestamps/note_types/...)
    """

    metadata: JsonDict
    song_data: CalcSongData | JsonDict


RefArrays = Mapping[str, np.ndarray]


class DbLoadoutPayload(TypedDict, total=False):
    """DB payload for a single loadout insert/update."""

    score: int
    fg_score: int
    gear: List[Any]
    minis: List[Any]
    details: JsonDict
    force: Optional[JsonDict]
    base_score: int
    selected_element: str
    _source: str


class PersistenceEntry(DbLoadoutPayload, total=False):
    """
    A single persistence entry passed to DB batch insert.

    This corresponds to the `entries` element passed into `save_loadouts_batch(...)`.
    """


class StageTiming(TypedDict, total=False):
    """Per-song stage timing emitted by song_processor/native inflight pipelines."""

    song_wall_sec: float
    cpu_read_sec: float
    cpu_setup_sec: float
    cpu_db_load_sec: float
    cpu_prep_sec: float
    cpu_human_hit_sim_sec: float
    gpu_timeline_precompute_sec: float
    cpu_ga_wall_sec: float
    cpu_fg_wall_sec: float
    cpu_post_sec: float


class GpuTiming(TypedDict, total=False):
    """Per-song GPU timing summary (from gpu_profiler)."""

    kernel_sec: float
    upload_sec: float
    download_sec: float
    kernel_calls: int
    genome_evaluations: int
    total_sec: float


class SongResultPayload(TypedDict, total=False):
    """
    Result payload emitted by native in-flight/post-processing pipelines.

    This is consumed by `gear_optimizer/app.py` and/or `pipeline/post_processor.py`.
    """

    # Identity
    song: str
    _song_name: str
    _queue_key: str
    _queue_label: str
    _repeat_index: int
    _repeat_total: int
    _ga_seed: Optional[int]

    # Inputs
    file_path: str
    difficulty: str
    cfg_dict: JsonDict

    # Outputs
    db_key: str
    db_payload: DbLoadoutPayload
    best_data: Optional[JsonDict]
    best_gear: List[Any]
    best_minis: List[Any]
    persist_entries: List[PersistenceEntry]
    log: str

    # Diagnostics
    _stage_timing: StageTiming
    _gpu_timing: GpuTiming

    # Error contract (when failures are returned instead of raised)
    _error: str
    _error_type: str
    _trace: str


# ----------------------------- GPU IPC payloads -----------------------------

BoolFlags = Tuple[bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool]


class SolveGenomesFromRegistryPayload(TypedDict, total=False):
    """Payload for `GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY`."""

    population_indices: np.ndarray
    timeline_grid: np.ndarray
    ref_arrays: RefArrays
    song_slot: int
    total_budget: int
    gem_scale_fever: int
    item_stats: np.ndarray
    slot_start: np.ndarray
    slot_count: np.ndarray
    base_fixed_stats: np.ndarray

    # color/stat flags (p/s x {ft,ff,pp,cm,fm,ov})
    is_p_ft: bool
    is_s_ft: bool
    is_p_ff: bool
    is_s_ff: bool
    is_p_pp: bool
    is_s_pp: bool
    is_p_cm: bool
    is_s_cm: bool
    is_p_fm: bool
    is_s_fm: bool
    is_p_ov: bool
    is_s_ov: bool


class SolveForceGreatsFinderPayload(TypedDict, total=False):
    """Payload for `GpuRequestType.SOLVE_FORCE_GREATS_FINDER`."""

    args: Tuple[Any, ...]
    kwargs: JsonDict
