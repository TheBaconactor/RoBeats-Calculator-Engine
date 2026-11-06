"""A song being solved: its configuration, its GPU inputs, and the state each stage leaves on it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from gear_optimizer.gamedata import SongMini
from gear_optimizer.solver.genetic_pipeline import GaInputs
from gear_optimizer.solver.item_registry import ItemRegistry


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
