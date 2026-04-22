from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from typing import Optional

import numpy as np

from gear_optimizer.solver.item_registry import ItemRegistry


@dataclass
class _NativeSong:
    fp: str
    song_name: str
    task_key: str
    ga_seed: int | None
    db_key: str
    effective_difficulty: str
    cfg_dict: dict
    cfg: object
    paths: object
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
    db_best_score: int
    attempt_lifetime: int
    prev_attempts_first: int
    db_best_fg_score: int
    db_baseline_valid: bool

    # Prepared GPU-native GA inputs
    registry: ItemRegistry
    cfg_data: dict
    color_flags: dict
    gens_per_run: int
    num_runs: int
    n_genomes: int
    item_stats: np.ndarray
    slot_start: np.ndarray
    slot_count: np.ndarray
    base_fixed_stats_arr: np.ndarray
    elite_count: int
    mutation_rate: float
    immigrant_rate: float
    tournament_k: int
    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k: int = 0
    init_heuristic_copies: int = 25
    db_seed_ids: Optional[np.ndarray] = None
    db_seed_prob: float = 0.0
    db_seed_copies: int = 1
    db_seed_mutations: int = 1

    # Runtime state
    song_slot: int = 0
    ga_future: Optional[concurrent.futures.Future] = None
    decode_future: Optional[concurrent.futures.Future] = None
    ga_candidates: Optional[list[dict]] = None
    best_data: Optional[dict] = None
    best_gear: Optional[list] = None
    best_minis: Optional[list] = None
    record_info: Optional[dict] = None

    # DB prefetch for FG (can overlap with GA)
    db_loadouts_future: Optional[concurrent.futures.Future] = None
    db_loadouts_full: Optional[list[dict]] = None

    loadout_entries: Optional[dict] = None
    fg_variants: Optional[list[dict]] = None
    fg_candidate_limit: int = 0
    fg_search_radius: Optional[int] = None
    fg_calc_song: Optional[dict] = None
    fg_prep_future: Optional[concurrent.futures.Future] = None
    fg_queued_t0: float | None = None
    fg_direct_ga_candidates: bool = False

    def __post_init__(self) -> None:
        if self.ga_candidates is None:
            self.ga_candidates = []
        if self.fg_variants is None:
            self.fg_variants = []
