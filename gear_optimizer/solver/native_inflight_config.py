"""
GPU-native in-flight pipeline configuration parsing.

Extracts all config/ENV-driven settings for the native in-flight orchestrator
into a frozen dataclass so the orchestrator body stays focused on runtime logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

import numpy as np


if TYPE_CHECKING:
    from gear_optimizer.pipeline.results import SolvedFg, SolvedLoadout

logger = logging.getLogger(__name__)


from gear_optimizer.core.types import JsonDict
from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.gamedata import SongMini, StatCurves
from gear_optimizer.solver.item_registry import ItemRegistry


@dataclass
class NativeSongConfig:
    fp: str = ""
    song_name: str = ""
    task_key: str = ""
    ga_seed: int | None = None
    db_key: str = ""


@dataclass
class NativeSongGPUInputs:
    curves: StatCurves | None = None
    # The song's minis by name (Mini Ascension applied).
    minis_by_name: dict[str, SongMini] = field(default_factory=dict)
    timed_song: TimedSong | None = None
    meta_primary_color: str = ""
    meta_secondary_color: str = ""
    fixed_stats: JsonDict = field(default_factory=dict)
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
    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k: int = 0
    init_heuristic_copies: int = 25
    # GA->FG effective-dedup equivalence tables for this song's color context
    # (Slice 1). Built at prep, uploaded by the GA run before candidate select.
    fg_gear_name_rank: Optional[np.ndarray] = None
    fg_mini_sig_id: Optional[np.ndarray] = None


@dataclass
class NativeSongGAState:
    ga_initial_populations: Optional[list[Any]] = None


@dataclass
class NativeSongDecodeState:
    ga_candidates: Optional[list[JsonDict]] = None
    fg_surface_prepared: bool = False
    best_data: Optional[JsonDict] = None
    best_gear: Optional[list[Any]] = None
    best_minis: Optional[list[Any]] = None


@dataclass
class NativeSongFGState:
    fg_results: Optional[tuple[tuple[SolvedLoadout, SolvedFg], ...]] = None  # best FG score first
    fg_response_scoring_bundle: Any | None = None
    fg_response_frontier_plan: Any | None = None
    # Slice 3 fused GA->FG handoff: the owner-scored per-base_components FG result map
    # ({base_components_7tuple -> FgFusedOwnerScoreRow}) returned by the GA run on the
    # owner thread. The FG worker materializes from this instead of submitting
    # BUILD+SCORE owner requests. Set by decode_ga_payload_sync from the GA response.
    fg_owner_score_map: Any | None = None


@dataclass
class NativeSongDBState:
    db_best_score: int = 0
    db_best_fg_score: int = 0
    db_baseline_valid: bool = False
    record_info: Optional[JsonDict] = None


@dataclass
class NativeSongRuntimeState:
    song_slot: int = 0
    ga: NativeSongGAState = field(default_factory=NativeSongGAState)
    decode: NativeSongDecodeState = field(default_factory=NativeSongDecodeState)
    fg: NativeSongFGState = field(default_factory=NativeSongFGState)
    db: NativeSongDBState = field(default_factory=NativeSongDBState)


# eq=False (identity equality/hash): conveyor deques remove songs by identity,
# and the auto-generated value __eq__ would recurse into NativeSongGPUInputs'
# numpy fields (ambiguous-truth crash) and, on a not-found miss, into the deep
# repr (a proven multi-second stall). No code compares NativeSong by value.
# This enforces the identity-conveyor invariant at the producer rather than per
# call site (see _remove_song_by_identity for the absence-tolerant variant).
@dataclass(eq=False)
class NativeSong:
    config: NativeSongConfig
    gpu_inputs: NativeSongGPUInputs
    runtime: NativeSongRuntimeState


def native_song_label(song: object, *, fallback_id: bool = False) -> str:
    try:
        config = getattr(song, "config", None)
        label = str(getattr(config, "task_key", "") or getattr(config, "song_name", "") or "").strip()
        if label:
            return label
    except Exception:
        pass
    return str(id(song)) if bool(fallback_id) else ""

