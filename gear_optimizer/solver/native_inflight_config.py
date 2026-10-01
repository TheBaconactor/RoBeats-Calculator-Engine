"""
GPU-native in-flight pipeline configuration parsing.

Extracts all config/ENV-driven settings for the native in-flight orchestrator
into a frozen dataclass so the orchestrator body stays focused on runtime logic.
"""

from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

import numpy as np


if TYPE_CHECKING:
    from gear_optimizer.pipeline.results import SolvedFg, SolvedLoadout

logger = logging.getLogger(__name__)

# Songs prepared and scheduled concurrently (capped by the queue size and the GPU song slots).
IN_FLIGHT_SONGS = 12
CANONICAL_GA_QUEUE_MULT = 2
CANONICAL_PREP_BUFFER_MULT = 4


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
    effective_difficulty: str = ""
    ga_depth: int = 0


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
class NativeSongPrepState:
    cpu_prep_s: float = 0.0
    wall_prep_s: float = 0.0


@dataclass
class NativeSongGAState:
    ga_future: Optional[concurrent.futures.Future] = None
    ga_submit_t0: float | None = None
    ga_initial_populations: Optional[list[Any]] = None


@dataclass
class NativeSongDecodeState:
    decode_future: Optional[concurrent.futures.Future] = None
    decode_submit_t0: float | None = None
    ga_candidates: Optional[list[JsonDict]] = None
    fg_surface_prepared: bool = False
    best_data: Optional[JsonDict] = None
    best_gear: Optional[list[Any]] = None
    best_minis: Optional[list[Any]] = None
    cpu_decode_s: float = 0.0


@dataclass
class NativeSongFGState:
    fg_results: Optional[tuple[tuple[SolvedLoadout, SolvedFg], ...]] = None  # best FG score first
    fg_prep_future: Optional[concurrent.futures.Future] = None
    fg_static_prep_done: bool = False
    fg_dynamic_prep_done: bool = False
    fg_prep_submit_t0: float | None = None
    fg_response_scoring_bundle: Any | None = None
    fg_response_frontier_plan: Any | None = None
    # Slice 3 fused GA->FG handoff: the owner-scored per-base_components FG result map
    # ({base_components_7tuple -> FgFusedOwnerScoreRow}) returned by the GA run on the
    # owner thread. The FG worker materializes from this instead of submitting
    # BUILD+SCORE owner requests. Set by decode_ga_payload_sync from the GA response.
    fg_owner_score_map: Any | None = None
    cpu_fg_prep_s: float = 0.0
    fg_prep_wall_s: float = 0.0
    cpu_fg_run_s: float = 0.0
    fg_run_wall_s: float = 0.0


@dataclass
class NativeSongDBState:
    db_best_score: int = 0
    db_best_fg_score: int = 0
    db_baseline_valid: bool = False
    record_info: Optional[JsonDict] = None


@dataclass
class NativeSongBundleState:
    bundle_parent_task: Any | None = None
    bundle_task_key: str = ""
    bundle_repeat_index: int = 0
    bundle_repeat_total: int = 0


@dataclass
class NativeSongRuntimeState:
    song_slot: int = 0
    prep: NativeSongPrepState = field(default_factory=NativeSongPrepState)
    ga: NativeSongGAState = field(default_factory=NativeSongGAState)
    decode: NativeSongDecodeState = field(default_factory=NativeSongDecodeState)
    fg: NativeSongFGState = field(default_factory=NativeSongFGState)
    db: NativeSongDBState = field(default_factory=NativeSongDBState)
    bundle: NativeSongBundleState = field(default_factory=NativeSongBundleState)


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

