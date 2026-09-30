"""
Core typing helpers for runtime boundaries.

This module intentionally focuses on *interfaces between subsystems* (pipeline ↔ solver ↔ persistence ↔ GPU IPC).
The goal is to make refactors and performance work safer without forcing a full codebase-wide typing overhaul.
"""

from __future__ import annotations

from typing import Any, TypedDict

JsonDict = dict[str, Any]


class DbLoadoutPayload(TypedDict, total=False):
    """DB payload for a single loadout insert/update."""

    score: int
    fg_score: int
    gear: list[Any]
    minis: list[Any]
    details: JsonDict
    force: JsonDict | None
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
    gpu_timeline_precompute_sec: float
    cpu_ga_wall_sec: float
    cpu_fg_wall_sec: float
    cpu_post_sec: float


class GpuTiming(TypedDict, total=False):
    """Per-song GPU timing summary."""

    kernel_sec: float
    upload_sec: float
    download_sec: float
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
    _ga_seed: int | None

    # Inputs
    file_path: str
    difficulty: str

    # Outputs
    db_key: str
    db_payload: DbLoadoutPayload
    best_data: JsonDict | None
    best_gear: list[Any]
    best_minis: list[Any]
    persist_entries: list[PersistenceEntry]
    log: str

    # Diagnostics
    _stage_timing: StageTiming
    _gpu_timing: GpuTiming

    # Error contract (when failures are returned instead of raised)
    _error: str
    _error_type: str
    _trace: str


# ----------------------------- GPU IPC payloads -----------------------------

BoolFlags = tuple[bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool, bool]


