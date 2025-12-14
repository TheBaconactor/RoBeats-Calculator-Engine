"""
Taichi Fields - GPU field declarations and allocation.

This module handles:
- All ti.Field declarations (reference tables, work items, genome data, results)
- Field allocation functions
- Grid fields for timeline lookups
- bind_fields() to inject live field objects into kernels module
"""
import taichi as ti
import numpy as np

from .runtime import is_initialized, init_taichi_vulkan

# ============================================================================
# CONSTANTS
# ============================================================================

GRID_SIZE = 161  # Timeline grid dimension (161x161 = 26,521 entries per song)
MAX_WORK_ITEMS = 4194304  # 4M - supports 4000 genomes × ~1000 FT/FF combinations
MAX_HEAD_NOTES = 100  # Maximum notes in head section
MAX_GENOMES = 4096  # Support up to 4096 unique genomes per batch
MAX_SLOTS = 9  # 6 gear + 3 minis (GPU-native GA representation)
MAX_ITEMS = 65536  # Upper bound for (type,Name)-deduped items per song (row 0 reserved)
ITEM_STAT_DIM = 10  # PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill
MAX_SONG_NOTES = 200000  # Maximum song length for GPU timeline computation
MAX_SONG_SLOTS = 8  # Concurrent song grid slots for batch coalescing


# ============================================================================
# GPU FIELDS (Device-resident data)
# ============================================================================

# Reference lookup tables (161 entries each, index 0-160)
ref_pp_field: ti.Field = None
ref_cm_field: ti.Field = None
ref_fm_field: ti.Field = None
ref_ft_field: ti.Field = None  # Fever Time multipliers
ref_ff_field: ti.Field = None  # Fever Fill Rate multipliers

# Timeline grid with song slots (MAX_SONG_SLOTS, 161, 161)
# Slot 0 is default for single-song mode; slots 1-7 for batch mode
grid_count_body_fever: ti.Field = None   # (MAX_SONG_SLOTS, 161, 161) i32
grid_count_body_normal: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_head_len: ti.Field = None           # (MAX_SONG_SLOTS, 161, 161) i32
grid_fever_masks: ti.Field = None        # (MAX_SONG_SLOTS, 161, 161, 100) i8 - head masks
grid_fever_masks_bits: ti.Field = None   # (MAX_SONG_SLOTS, 161, 161, 4) u32 - bitpacked head masks

# Song data for GPU timeline computation
song_timestamps: ti.Field = None  # (MAX_SONG_NOTES,) f32

# Per-work-item fever masks
fever_masks: ti.Field = None  # (MAX_WORK_ITEMS, MAX_HEAD_NOTES) - i8

# Per-work-item inputs
work_budgets: ti.Field = None
work_count_fever: ti.Field = None
work_count_normal: ti.Field = None
work_ft_gems: ti.Field = None
work_ff_gems: ti.Field = None
work_head_len: ti.Field = None
work_genome_id: ti.Field = None
work_items: ti.Field = None  # Vector field [budget, cnt_fever, cnt_normal, ft, ff, hl, gid, song_slot]

# Per-genome base stats (lookup by genome_id in kernel)
genome_base_pp: ti.Field = None
genome_base_cm: ti.Field = None
genome_base_fm: ti.Field = None
genome_base_p_val: ti.Field = None
genome_base_s_val: ti.Field = None
genome_base_ft: ti.Field = None  # Base Fever Time stat (for FT/FF iteration)
genome_base_ff: ti.Field = None  # Base Fever Fill Rate stat
genome_base_stats: ti.Field = None  # Vector field [pp, cm, fm, p, s, ft, ff]

# GPU-native GA fields (UNUSED - Future infrastructure)
# These fields support GPU-side GA operators but are NOT currently wired into genetic.py.
# They exist as prep work for a future GPU-native GA where the entire population lives on GPU.
population_indices: ti.Field = None  # (MAX_GENOMES, MAX_SLOTS) item_id per (genome,slot)
population_next_indices: ti.Field = None  # (MAX_GENOMES, MAX_SLOTS) next generation buffer
item_stats: ti.Field = None          # (MAX_ITEMS, ITEM_STAT_DIM) dense item stats table
base_fixed_stats: ti.Field = None    # (ITEM_STAT_DIM,) fixed base stats (added to all genomes)
ga_scores: ti.Field = None           # (MAX_GENOMES,) int32 fitness scores (from evaluation)
ga_rng_state: ti.Field = None        # (MAX_GENOMES,) uint32 RNG state per genome/thread
ga_parent_a: ti.Field = None         # (MAX_GENOMES,) int32 selected parent index A
ga_parent_b: ti.Field = None         # (MAX_GENOMES,) int32 selected parent index B

# Per-slot song flags for batch coalescing (12 flags per slot)
# Indices: [is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
#           is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov]
song_flags: ti.Field = None  # (MAX_SONG_SLOTS, 12) i32


# Per-work-item outputs
result_scores: ti.Field = None
result_pp: ti.Field = None
result_cm: ti.Field = None
result_fm: ti.Field = None
result_ov: ti.Field = None
result_p_val: ti.Field = None
result_s_val: ti.Field = None
result_stats: ti.Field = None  # Vector field [score, pp, cm, fm, ov, p, s]

# Per-genome outputs (for FT/FF iteration kernel)
genome_result_scores: ti.Field = None
genome_result_ft: ti.Field = None
genome_result_ff: ti.Field = None
genome_result_pp: ti.Field = None
genome_result_cm: ti.Field = None
genome_result_fm: ti.Field = None
genome_result_ov: ti.Field = None
genome_result_stats: ti.Field = None  # Vector field [score, ft, ff, pp, cm, fm, ov]


# ============================================================================
# ALLOCATION STATE
# ============================================================================

_fields_allocated = False
_grid_fields_allocated = False
_last_uploaded_grid_id = None  # Cache to skip redundant grid uploads


def is_fields_allocated() -> bool:
    """Check if main fields have been allocated."""
    return _fields_allocated


def is_grid_fields_allocated() -> bool:
    """Check if grid fields have been allocated."""
    return _grid_fields_allocated


def get_last_uploaded_grid_id():
    """Get the ID of the last uploaded grid (for cache checking)."""
    return _last_uploaded_grid_id


def set_last_uploaded_grid_id(grid_id):
    """Set the ID of the last uploaded grid."""
    global _last_uploaded_grid_id
    _last_uploaded_grid_id = grid_id


# ============================================================================
# FIELD ALLOCATION
# ============================================================================

def allocate_fields():
    """
    Allocate GPU fields. Must be called after ti.init().
    
    This allocates:
    - Reference tables (161 entries each, f32)
    - Work item inputs/outputs (MAX_WORK_ITEMS)
    - Genome base stats and results (MAX_GENOMES)
    - Fever masks (MAX_WORK_ITEMS × MAX_HEAD_NOTES)
    """
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global fever_masks, work_budgets, work_count_fever, work_count_normal
    global work_ft_gems, work_ff_gems, work_head_len, work_genome_id, work_items
    global genome_base_pp, genome_base_cm, genome_base_fm, genome_base_p_val, genome_base_s_val
    global genome_base_ft, genome_base_ff, genome_base_stats
    global population_indices, population_next_indices, item_stats, base_fixed_stats
    global ga_scores, ga_rng_state, ga_parent_a, ga_parent_b
    global song_flags
    global result_scores, result_pp, result_cm, result_fm, result_ov
    global result_p_val, result_s_val, result_stats, _fields_allocated
    global genome_result_scores, genome_result_ft, genome_result_ff
    global genome_result_pp, genome_result_cm, genome_result_fm, genome_result_ov, genome_result_stats
    
    if _fields_allocated:
        return
    
    # Reference tables (f32 for performance)
    ref_pp_field = ti.field(dtype=ti.f32, shape=161)
    ref_cm_field = ti.field(dtype=ti.f32, shape=161)
    ref_fm_field = ti.field(dtype=ti.f32, shape=161)
    ref_ft_field = ti.field(dtype=ti.f32, shape=161)
    ref_ff_field = ti.field(dtype=ti.f32, shape=161)
    
    # Work item inputs (Vector field for single-shot upload)
    # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
    fever_masks = ti.field(dtype=ti.i8, shape=(MAX_WORK_ITEMS, MAX_HEAD_NOTES))
    work_items = ti.Vector.field(n=8, dtype=ti.i32, shape=MAX_WORK_ITEMS)
    
    # Per-genome base stats (lookup by work_genome_id in kernel)
    # [pp, cm, fm, p_val, s_val, ft, ff]
    genome_base_stats = ti.Vector.field(n=7, dtype=ti.i32, shape=MAX_GENOMES)

    # GPU-native GA / stat aggregation (Phase 3/4)
    population_indices = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, MAX_SLOTS))
    population_next_indices = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, MAX_SLOTS))
    item_stats = ti.field(dtype=ti.i32, shape=(MAX_ITEMS, ITEM_STAT_DIM))
    base_fixed_stats = ti.field(dtype=ti.i32, shape=ITEM_STAT_DIM)
    ga_scores = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_rng_state = ti.field(dtype=ti.u32, shape=MAX_GENOMES)
    ga_parent_a = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_parent_b = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    
    # Per-slot song flags for batch coalescing
    # [is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov]
    song_flags = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, 12))
    
    # Per-work-item results (Vector field for single-shot download)
    # [score, pp, cm, fm, ov, p_val, s_val]
    result_stats = ti.Vector.field(n=7, dtype=ti.i32, shape=MAX_WORK_ITEMS)
    
    # Per-genome results (for FT/FF iteration kernel)
    # [score, ft, ff, pp, cm, fm, ov]
    genome_result_stats = ti.Vector.field(n=7, dtype=ti.i32, shape=MAX_GENOMES)
    
    _fields_allocated = True
    print(f"[Taichi] Allocated GPU fields: {MAX_WORK_ITEMS} work items, {MAX_HEAD_NOTES} head notes, {MAX_GENOMES} genomes")



def allocate_grid_fields():
    """
    Allocate GPU fields for timeline grid. Must be called after ti.init().
    
    This allocates MAX_SONG_SLOTS × 161×161 timeline grids for batch coalescing.
    Each song slot can hold a different song's grid for parallel processing.
    """
    global grid_count_body_fever, grid_count_body_normal, grid_head_len, grid_fever_masks, grid_fever_masks_bits
    global song_timestamps
    global _grid_fields_allocated
    
    if _grid_fields_allocated:
        return
    
    # Timeline grid with song slots (MAX_SONG_SLOTS × 161×161)
    # Slot 0 is default for single-song mode; slots 0-7 for batch mode
    grid_count_body_fever = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_count_body_normal = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_head_len = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_fever_masks = ti.field(dtype=ti.i8, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES))
    grid_fever_masks_bits = ti.field(dtype=ti.u32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, 4))
    
    # Song timestamps for GPU timeline computation
    song_timestamps = ti.field(dtype=ti.f32, shape=MAX_SONG_NOTES)
    
    _grid_fields_allocated = True
    print(f"[Taichi] Allocated grid fields: {MAX_SONG_SLOTS}×{GRID_SIZE}×{GRID_SIZE} timeline grid slots")


# ============================================================================
# FIELD BINDING (for kernels module)
# ============================================================================

def bind_fields(kernels_module):
    """
    Bind live field objects to the kernels module.
    
    This must be called AFTER field allocation, so that kernels can access
    the actual ti.field objects rather than None placeholders.
    
    Args:
        kernels_module: The kernels module to bind fields to
    """
    # Reference tables
    kernels_module.ref_pp_field = ref_pp_field
    kernels_module.ref_cm_field = ref_cm_field
    kernels_module.ref_fm_field = ref_fm_field
    kernels_module.ref_ft_field = ref_ft_field
    kernels_module.ref_ff_field = ref_ff_field
    
    # Grid fields
    kernels_module.grid_count_body_fever = grid_count_body_fever
    kernels_module.grid_count_body_normal = grid_count_body_normal
    kernels_module.grid_head_len = grid_head_len
    kernels_module.grid_fever_masks = grid_fever_masks
    kernels_module.grid_fever_masks_bits = grid_fever_masks_bits
    
    # Song data for timeline
    kernels_module.song_timestamps = song_timestamps
    
    # Work item data
    kernels_module.fever_masks = fever_masks
    kernels_module.work_items = work_items
    
    # Genome base stats
    kernels_module.genome_base_stats = genome_base_stats

    # Per-slot song flags (batch coalescing)
    kernels_module.song_flags = song_flags

    # GPU-native GA / stat aggregation
    kernels_module.population_indices = population_indices
    kernels_module.population_next_indices = population_next_indices
    kernels_module.item_stats = item_stats
    kernels_module.base_fixed_stats = base_fixed_stats
    kernels_module.ga_scores = ga_scores
    kernels_module.ga_rng_state = ga_rng_state
    kernels_module.ga_parent_a = ga_parent_a
    kernels_module.ga_parent_b = ga_parent_b
    
    # Results
    kernels_module.result_stats = result_stats
    
    # Genome results
    kernels_module.genome_result_stats = genome_result_stats


def ensure_fields_allocated():
    """
    Ensure Taichi is initialized and fields are allocated.
    
    This is the main entry point for ensuring the GPU is ready.
    Initializes Taichi if needed, allocates fields, and binds them to kernels.
    """
    if not is_initialized():
        init_taichi_vulkan()
    
    if not _fields_allocated:
        allocate_fields()
        # Import kernels here to avoid circular import at module load time
        from . import kernels
        bind_fields(kernels)


def ensure_grid_fields_allocated():
    """
    Ensure grid fields are allocated for timeline lookups.
    
    Call this before uploading or using the timeline grid.
    """
    ensure_fields_allocated()  # Main fields must be allocated first
    
    if not _grid_fields_allocated:
        allocate_grid_fields()
        # Re-bind to include grid fields
        from . import kernels
        bind_fields(kernels)
