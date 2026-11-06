"""The GPU's fields, in one table. Their shapes never change: Taichi bakes them into the compiled kernels, so one offline
kernel cache serves every search size. allocate_fields sets each name of the table on this module, where the kernels
read it."""

from gear_optimizer.frontier.timeline_producer import GRID_SIZE, MAX_TIMELINE_FRONTIER_SURFACES
from gear_optimizer.rules import GEM_BUDGET
from gear_optimizer.solver.genetic_pipeline import GA_INIT_HEURISTIC_K

from .runtime import ti

MAX_GENOMES = 4608  # The active population: 13 runs of 352 genomes per GA batch (one batch for 5 or 10 runs).
MAX_SLOTS = 9  # 6 gear + 3 minis
MAX_ITEMS = 65536  # Items per song (id 0 is the empty slot).
ITEM_STAT_DIM = 10  # PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill
MAX_GA_RUNS = 128  # Runs per song.
MAX_FTFF_COMBOS = (GEM_BUDGET + 1) * (GEM_BUDGET + 2) // 2
GA_FTFF_LANES = 256  # Lanes of one genome's FT/FF combo search.
GA_EVAL_CACHE_SIZE = 16384  # Device memo of evaluations; full stats verify every hit.
GA_RESULT_COLS = 7  # score, FT, FF, PP, CM, FM and element gems
GA_RUN_BEST_COLS = 1 + MAX_SLOTS + GA_RESULT_COLS  # score, item ids, result
GA_FG_CANDIDATES_PER_RUN = 64
GA_FG_CANDIDATE_COLS = GA_RUN_BEST_COLS + 7  # the run-best columns, then the pre-gem stats

# Name: (type, shape), or (type, shape, vector size).
_FIELDS = {
    # The stat curves, the PP-vs-element prefix argmax of the gem search (by flags, PP stat, gems) and the FT/FF combos.
    "ref_pp_field": (ti.f32, GRID_SIZE),
    "ref_cm_field": (ti.f32, GRID_SIZE),
    "ref_fm_field": (ti.f32, GRID_SIZE),
    "exact_pp_best_gems_prefix": (ti.i16, (16, GRID_SIZE, GEM_BUDGET + 1)),
    "ftff_combo_ft": (ti.i32, MAX_FTFF_COMBOS),
    "ftff_combo_ff": (ti.i32, MAX_FTFF_COMBOS),
    # The song's timeline frontier: per (FT, FF) cell, then its surfaces in one pool.
    "grid_body_total": (ti.i32, (GRID_SIZE, GRID_SIZE)),
    "grid_head_len": (ti.i8, (GRID_SIZE, GRID_SIZE)),
    "grid_frontier_count": (ti.i32, (GRID_SIZE, GRID_SIZE)),
    "grid_frontier_offset": (ti.i32, (GRID_SIZE, GRID_SIZE)),
    "grid_frontier_body_fever_pool": (ti.i32, MAX_TIMELINE_FRONTIER_SURFACES),
    "grid_frontier_body_normal_pool": (ti.i32, MAX_TIMELINE_FRONTIER_SURFACES),
    "grid_frontier_masks_bits_pool": (ti.u32, (MAX_TIMELINE_FRONTIER_SURFACES, 4)),
    "grid_frontier_head_coeffs_pool": (ti.i16, (MAX_TIMELINE_FRONTIER_SURFACES, 4)),  # n_hn, n_hf, sigma_hn, sigma_hf
    # The song's items.
    "item_stats": (ti.i32, (MAX_ITEMS, ITEM_STAT_DIM)),
    "base_fixed_stats": (ti.i32, ITEM_STAT_DIM),
    "slot_start": (ti.i32, MAX_SLOTS),
    "slot_count": (ti.i32, MAX_SLOTS),
    "ga_init_heuristic_topk": (ti.i32, (MAX_SLOTS, GA_INIT_HEURISTIC_K)),
    # The population.
    "population_indices": (ti.i32, (MAX_GENOMES, MAX_SLOTS)),
    "population_next_indices": (ti.i32, (MAX_GENOMES, MAX_SLOTS)),
    "genome_base_stats": (ti.i16, MAX_GENOMES, 7),  # PP, CM, FM, primary, secondary, FT, FF
    "ga_scores": (ti.i32, MAX_GENOMES),
    "ga_rng_state": (ti.u32, MAX_GENOMES),
    # Evaluation: the memo, the unique uncached rows, and each genome's winner ((score + 1) << 32 | combo, its gems).
    "ga_eval_cache_stats": (ti.i32, GA_EVAL_CACHE_SIZE, 7),
    "ga_eval_cache_key": (ti.u64, GA_EVAL_CACHE_SIZE),
    "ga_eval_cache_results": (ti.i32, GA_EVAL_CACHE_SIZE, 4),
    "ga_eval_cache_owner": (ti.i32, GA_EVAL_CACHE_SIZE),
    "ga_exact_eval_rep_idx": (ti.i32, MAX_GENOMES),
    "ga_exact_eval_unique_count": (ti.i32, 1),
    "ga_unique_slot_to_genome": (ti.i32, MAX_GENOMES),
    "ga_eval_incumbent_score": (ti.i32, MAX_GENOMES),
    "ga_lane_best_key": (ti.u64, (MAX_GENOMES, GA_FTFF_LANES)),
    "ga_lane_best_results": (ti.i32, (MAX_GENOMES, GA_FTFF_LANES, 4)),
    "chunk_best_key": (ti.u64, MAX_GENOMES),
    "chunk_best_results": (ti.i32, (MAX_GENOMES, 4)),  # PP, CM, FM, element gems
    # What the runs hand back: each run's best across generations, and its candidate table (row 0: that best).
    "ga_run_best": (ti.i32, (MAX_GA_RUNS, GA_RUN_BEST_COLS)),
    "ga_fg_candidates": (ti.i32, (MAX_GA_RUNS, GA_FG_CANDIDATES_PER_RUN + 1, GA_FG_CANDIDATE_COLS)),
}


def allocate_fields() -> None:
    for name, (dtype, shape, *vector) in _FIELDS.items():
        globals()[name] = (
            ti.Vector.field(vector[0], dtype=dtype, shape=shape) if vector else ti.field(dtype=dtype, shape=shape)
        )
