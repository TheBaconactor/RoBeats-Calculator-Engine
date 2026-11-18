"""A song being solved: its configuration, its GPU inputs, and the state each stage leaves on it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from gear_optimizer.gamedata import SongMini
from gear_optimizer.solver.genetic_pipeline import GaInputs
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.timing_envelope import TimedSong


@dataclass
class NativeSongConfig:
    song_name: str = ""
    task_key: str = ""
    ga_seed: int | None = None
    db_key: str = ""


@dataclass
class NativeSongGPUInputs(GaInputs):
    # The song's minis by name (Mini Ascension applied).
    minis_by_name: dict[str, SongMini]
    meta_primary_color: str
    meta_secondary_color: str
    registry: ItemRegistry
    # The GA selection's effective-loadout tables for the song's colors (solver.ga_selection.effective_tables).
    fg_gear_name_rank: np.ndarray
    fg_mini_sig_id: np.ndarray

    def as_ga_inputs(self) -> GaInputs:
        """Compact GA-only inputs without host item registries or cached FG envelopes."""
        timed = self.timed_song
        slim_timed = TimedSong(
            chart=timed.chart,
            mode=timed.mode,
            baseline_hash=timed.baseline_hash,
            hit_timestamps=timed.hit_timestamps,
            perfect_candidates=timed.perfect_candidates,
            perfect_floor=timed.perfect_floor,
            great_floor=timed.great_floor,
            great_candidates=timed.great_candidates,
            late_great_floor=timed.late_great_floor,
            exit_ceiling=timed.exit_ceiling,
        )
        slim_timed.__dict__["timeline_key"] = timed.timeline_key
        return GaInputs(
            timed_song=slim_timed,
            curves=self.curves,
            color_flags=self.color_flags,
            gens_per_run=self.gens_per_run,
            num_runs=self.num_runs,
            n_genomes=self.n_genomes,
            item_stats=self.item_stats,
            slot_start=self.slot_start,
            slot_count=self.slot_count,
            base_fixed_stats_arr=self.base_fixed_stats_arr,
            init_heuristic_topk=self.init_heuristic_topk,
            init_heuristic_copies=self.init_heuristic_copies,
            ftff_shortlist=self.ftff_shortlist,
        )


@dataclass
class NativeSongFGState:
    # The song's FG scoring bundle (pipeline.fg.prepare_fg_static), released once its FG results are materialized.
    fg_response_scoring_bundle: Any | None = None


@dataclass
class NativeSongRuntimeState:
    fg: NativeSongFGState = field(default_factory=NativeSongFGState)


# eq=False (identity equality and hash): a generated value __eq__ would compare NativeSongGPUInputs' numpy fields
# (ambiguous truth) and recurse into the deep repr. No code compares songs by value.
@dataclass(eq=False)
class NativeSong:
    config: NativeSongConfig
    gpu_inputs: NativeSongGPUInputs
    runtime: NativeSongRuntimeState
