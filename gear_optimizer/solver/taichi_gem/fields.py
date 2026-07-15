"""
Taichi Fields - GPU field declarations and allocation.
This module handles:
- All ti.Field declarations (reference tables, work items, loadout data, results)
- Field allocation functions
- Grid fields for timeline lookups
- bind_fields() to inject live field objects into kernels module
"""
import logging
import taichi as ti
from gear_optimizer.core.parsing import env_int
from .runtime import is_initialized, init_taichi
# Skyline uses this to select the 32-bit-atomic reduction path on macOS.
# That includes MoltenVK (`ti.vulkan` on Darwin), whose shaders still compile
# through Metal and therefore cannot use the packed-u64 atomic reduction.
IS_METAL = False
logger = logging.getLogger(__name__)
GRID_SIZE = 161  # Timeline grid dimension (161x161 = 26,521 entries per song)
MAX_LOADOUTS = 4608  # Exact candidate batch capacity.
MAX_SLOTS = 9  # 6 gear + 3 minis.
MAX_ITEMS = 65536  # Upper bound for (type,Name)-deduped items per song (row 0 reserved)
ITEM_STAT_DIM = 10  # PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill
MAX_SONG_NOTES = 32768  # Max chart length for GPU timeline computation. Real-world max is ~7027
# notes (M1LLI0N PP (Full Version) [EXTENDED CUT]); 32768 is 4.6x that (~110 min of continuous
# notes -- beyond any conceivable chart). Sized down from 200000 (28x over) to reclaim ~102 MB on
# the dominant field fever_end_idx_song = (MAX_SONG_NOTES, GRID_SIZE) i32 (was 122.8 MB, now 21 MB)
# plus the ~7 per-note (MAX_SONG_NOTES,) arrays. A chart exceeding this fails loud at
# timeline.py (`Song has N notes, max is ...`), never silent truncation -- bump it if ever hit.
MAX_EVALS_PER_DISPATCH = 8_388_608  # Vulkan safety bound for loadouts * FT/FF combos.
def _clamp_song_slots(n: int) -> int:
    if n < 2:
        return 2
    if n > 256:
        try:
            logger.warning("[GPU] GPU_SONG_SLOTS=%s too large; clamping to 256 to avoid VRAM OOM.", int(n))
        except Exception as e:
            logger.debug(f"fields:_clamp_song_slots: {e}")
        return 256
    return n
MAX_TIMELINE_FRONTIER_SURFACES = 262144  # GPU frontier field-size cap (within [1, 1_048_576] VRAM bound)
MAX_SONG_SLOTS = _clamp_song_slots(env_int("GPU_SONG_SLOTS", 8))
MAX_TOTAL_BUDGET = 90  # Max supported total_budget for FT/FF combo tables
MAX_FTFF_COMBOS = (MAX_TOTAL_BUDGET + 1) * (MAX_TOTAL_BUDGET + 2) // 2  # 4186 when MAX_TOTAL_BUDGET=90
SKYLINE_FTFF_REDUCE_BLOCK_DIM = 256  # Vulkan reduce block dim; MUST match kernels_helpers.py.
ref_pp_field: ti.Field = None
ref_cm_field: ti.Field = None
ref_fm_field: ti.Field = None
ref_ft_field: ti.Field = None  # Fever Time multipliers
ref_ff_field: ti.Field = None  # Fever Fill Rate multipliers
exact_pp_best_gems_prefix: ti.Field = None  # (16, 161, MAX_TOTAL_BUDGET+1) i16
grid_count_body_fever: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_count_body_normal: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_head_len: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_fever_masks_bits: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161, 4) u32 - bitpacked head masks
grid_frontier_count: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - retained packed frontier count
grid_frontier_offset: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - packed frontier start offset
grid_frontier_body_fever_pool: ti.Field = None  # (MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES) i32
grid_frontier_body_normal_pool: ti.Field = None  # (MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES) i32
grid_frontier_masks_bits_pool: ti.Field = None  # (MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES, 4) u32
grid_frontier_head_coeffs_pool: ti.Field = None  # (MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES, 4) i16 - per-variant (n_hn, n_hf, sigma_hn, sigma_hf)
grid_gap: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - gap to song end per (FT, FF)
grid_fever_activations: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - fever activations per (FT, FF)
song_timestamps: ti.Field = None  # (MAX_SONG_NOTES,) f32
fever_end_idx_song: ti.Field = None  # (MAX_SONG_NOTES, GRID_SIZE) i32
song_note_group_idx: ti.Field = None  # (MAX_SONG_NOTES,) i32: note_idx -> group_idx
song_group_starts: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> first note_idx
song_group_base_t_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> chart time in integer ms
song_group_low_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> min feasible carry (ms)
song_group_high_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> max feasible carry (ms)
loadout_base_stats: ti.Field = None
loadout_indices: ti.Field = None  # (MAX_LOADOUTS, MAX_SLOTS) item_id per (loadout, slot)
item_stats: ti.Field = None  # (MAX_ITEMS, ITEM_STAT_DIM) dense item stats table
base_fixed_stats: ti.Field = None  # (ITEM_STAT_DIM,) fixed base stats (added to all loadouts)
slot_start: ti.Field = None  # (MAX_SLOTS,) int32 - first valid item_id for slot
slot_count: ti.Field = None  # (MAX_SLOTS,) int32 - number of items in slot pool
loadout_result_stats: ti.Field = None  # Vector field [score, ft, ff, pp, cm, fm, ov]
loadout_result_stats_download_staging_256: ti.Field = None  # (256,) vec7 i32
loadout_result_stats_download_staging_1024: ti.Field = None  # (1024,) vec7 i32
chunk_best_key: ti.Field = None  # (MAX_LOADOUTS,) u64 packed key for safe per-chunk reduction
ftff_combo_ft: ti.Field = None  # (MAX_FTFF_COMBOS,) i32 FT gems per combo
ftff_combo_ff: ti.Field = None  # (MAX_FTFF_COMBOS,) i32 FF gems per combo
chunk_best_score: ti.Field = None  # (MAX_LOADOUTS,) i32 best score per loadout
chunk_best_idx: ti.Field = None  # (MAX_LOADOUTS,) i32 winning combo index
chunk_best_results: ti.Field = None  # (MAX_LOADOUTS, 4) i32 - [pp, cm, fm, ov] from winning combo
skyline_scores: ti.Field = None
_fields_allocated = False
_grid_fields_allocated = False


def is_fields_allocated() -> bool:
    """Check if main fields have been allocated."""
    return _fields_allocated
def is_grid_fields_allocated() -> bool:
    """Check if grid fields have been allocated."""
    return _grid_fields_allocated
def reset_fields_state() -> None:
    """
    Reset module-level allocation state after `ti.reset()`.
    All field objects become invalid after a Taichi runtime reset; we clear the
    globals so `ensure_fields_allocated()` can safely re-allocate and re-bind.
    """
    global _fields_allocated, _grid_fields_allocated
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global exact_pp_best_gems_prefix
    global grid_count_body_fever, grid_count_body_normal, grid_head_len
    global grid_fever_masks_bits
    global grid_frontier_count, grid_frontier_offset
    global grid_frontier_body_fever_pool, grid_frontier_body_normal_pool, grid_frontier_masks_bits_pool
    global grid_frontier_head_coeffs_pool
    global grid_gap, grid_fever_activations
    global song_timestamps, fever_end_idx_song
    global song_note_group_idx, song_group_starts, song_group_base_t_ms, song_group_low_ms, song_group_high_ms
    global loadout_base_stats
    global loadout_indices
    global item_stats, base_fixed_stats
    global skyline_scores
    global slot_start, slot_count
    global loadout_result_stats
    global loadout_result_stats_download_staging_256, loadout_result_stats_download_staging_1024
    global chunk_best_key, chunk_best_score, chunk_best_idx, chunk_best_results
    global ftff_combo_ft, ftff_combo_ff
    ref_pp_field = None
    ref_cm_field = None
    ref_fm_field = None
    ref_ft_field = None
    ref_ff_field = None
    exact_pp_best_gems_prefix = None
    grid_count_body_fever = None
    grid_count_body_normal = None
    grid_head_len = None
    grid_fever_masks_bits = None
    grid_frontier_count = None
    grid_frontier_offset = None
    grid_frontier_body_fever_pool = None
    grid_frontier_body_normal_pool = None
    grid_frontier_masks_bits_pool = None
    grid_frontier_head_coeffs_pool = None
    grid_gap = None
    grid_fever_activations = None
    song_timestamps = None
    fever_end_idx_song = None
    song_note_group_idx = None
    song_group_starts = None
    song_group_base_t_ms = None
    song_group_low_ms = None
    song_group_high_ms = None
    loadout_base_stats = None
    loadout_indices = None
    item_stats = None
    base_fixed_stats = None
    skyline_scores = None
    slot_start = None
    slot_count = None
    loadout_result_stats = None
    loadout_result_stats_download_staging_256 = None
    loadout_result_stats_download_staging_1024 = None
    chunk_best_key = None
    chunk_best_score = None
    chunk_best_idx = None
    chunk_best_results = None
    ftff_combo_ft = None
    ftff_combo_ff = None
    _fields_allocated = False
    _grid_fields_allocated = False
    _last_uploaded_grid_id = None
def allocate_fields():
    """
    Allocate GPU fields. Must be called after ti.init().
    This allocates the baseline Taichi fields used by exact GPU solving.
    """
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global exact_pp_best_gems_prefix
    global loadout_base_stats
    global loadout_indices, item_stats, base_fixed_stats
    global skyline_scores
    global slot_start, slot_count
    global loadout_result_stats
    global loadout_result_stats_download_staging_256, loadout_result_stats_download_staging_1024
    global chunk_best_key, chunk_best_score, chunk_best_idx, chunk_best_results
    global ftff_combo_ft, ftff_combo_ff
    global _fields_allocated
    if _fields_allocated:
        return
    ref_pp_field = ti.field(dtype=ti.f32, shape=161)
    ref_cm_field = ti.field(dtype=ti.f32, shape=161)
    ref_fm_field = ti.field(dtype=ti.f32, shape=161)
    ref_ft_field = ti.field(dtype=ti.f32, shape=161)
    ref_ff_field = ti.field(dtype=ti.f32, shape=161)
    exact_pp_best_gems_prefix = ti.field(dtype=ti.i16, shape=(16, GRID_SIZE, MAX_TOTAL_BUDGET + 1))
    loadout_base_stats = ti.Vector.field(n=7, dtype=ti.i16, shape=MAX_LOADOUTS)
    loadout_indices = ti.field(dtype=ti.i32, shape=(MAX_LOADOUTS, MAX_SLOTS))
    item_stats = ti.field(dtype=ti.i32, shape=(MAX_ITEMS, ITEM_STAT_DIM))
    base_fixed_stats = ti.field(dtype=ti.i32, shape=ITEM_STAT_DIM)
    skyline_scores = ti.field(dtype=ti.i32, shape=MAX_LOADOUTS)
    slot_start = ti.field(dtype=ti.i32, shape=MAX_SLOTS)
    slot_count = ti.field(dtype=ti.i32, shape=MAX_SLOTS)
    loadout_result_stats = ti.Vector.field(n=7, dtype=ti.i32, shape=MAX_LOADOUTS)
    loadout_result_stats_download_staging_256 = ti.Vector.field(n=7, dtype=ti.i32, shape=256)
    loadout_result_stats_download_staging_1024 = ti.Vector.field(n=7, dtype=ti.i32, shape=1024)
    chunk_best_key = ti.field(dtype=ti.u64, shape=MAX_LOADOUTS)
    chunk_best_score = ti.field(dtype=ti.i32, shape=MAX_LOADOUTS)
    chunk_best_idx = ti.field(dtype=ti.i32, shape=MAX_LOADOUTS)
    ftff_combo_ft = ti.field(dtype=ti.i32, shape=MAX_FTFF_COMBOS)
    ftff_combo_ff = ti.field(dtype=ti.i32, shape=MAX_FTFF_COMBOS)
    chunk_best_results = ti.field(dtype=ti.i32, shape=(MAX_LOADOUTS, 4))
    _fields_allocated = True
    logger.debug("[Taichi] Allocated GPU fields: %s loadouts", MAX_LOADOUTS)
def allocate_grid_fields():
    """
    Allocate GPU fields for timeline grid. Must be called after ti.init().
    This allocates MAX_SONG_SLOTS Ã— 161Ã—161 timeline grids for batch coalescing.
    Each song slot can hold a different song's grid for parallel processing.
    """
    global grid_count_body_fever, grid_count_body_normal, grid_head_len
    global grid_fever_masks_bits
    global grid_frontier_count, grid_frontier_offset
    global grid_frontier_body_fever_pool, grid_frontier_body_normal_pool, grid_frontier_masks_bits_pool
    global grid_frontier_head_coeffs_pool
    global grid_gap, grid_fever_activations
    global song_timestamps, fever_end_idx_song
    global song_note_group_idx, song_group_starts, song_group_base_t_ms, song_group_low_ms, song_group_high_ms
    global _grid_fields_allocated
    if _grid_fields_allocated:
        return
    grid_count_body_fever = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_count_body_normal = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_head_len = ti.field(dtype=ti.i8, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_fever_masks_bits = ti.field(dtype=ti.u32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, 4))
    grid_frontier_count = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_frontier_offset = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_frontier_body_fever_pool = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES))
    grid_frontier_body_normal_pool = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES))
    grid_frontier_masks_bits_pool = ti.field(dtype=ti.u32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES, 4))
    grid_frontier_head_coeffs_pool = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES, 4))
    grid_gap = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_fever_activations = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    if song_timestamps is None:
        song_timestamps = ti.field(dtype=ti.f32, shape=MAX_SONG_NOTES)
    if fever_end_idx_song is None:
        fever_end_idx_song = ti.field(dtype=ti.i32, shape=(MAX_SONG_NOTES, GRID_SIZE))
    if song_note_group_idx is None:
        song_note_group_idx = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_starts is None:
        song_group_starts = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_base_t_ms is None:
        song_group_base_t_ms = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_low_ms is None:
        song_group_low_ms = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_high_ms is None:
        song_group_high_ms = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    _grid_fields_allocated = True
    logger.debug(
        "[Taichi] Allocated grid fields: %s x %s x %s timeline grid slots",
        MAX_SONG_SLOTS,
        GRID_SIZE,
        GRID_SIZE,
    )
def bind_fields(kernels_module):
    """
    Bind live field objects to the kernels module.
    This must be called AFTER field allocation, so that kernels can access
    the actual ti.field objects rather than None placeholders.
    If kernels is a package (has kernels_helpers submodule), binds to kernels_helpers.
    Otherwise binds to the module directly.
    Args:
        kernels_module: The kernels module or package to bind fields to
    """
    try:
        from . import kernels
        target = kernels.kernels_helpers
    except (ImportError, AttributeError):
        target = kernels_module
    target.ref_pp_field = ref_pp_field
    target.ref_cm_field = ref_cm_field
    target.ref_fm_field = ref_fm_field
    target.ref_ft_field = ref_ft_field
    target.ref_ff_field = ref_ff_field
    target.exact_pp_best_gems_prefix = exact_pp_best_gems_prefix
    target.grid_count_body_fever = grid_count_body_fever
    target.grid_count_body_normal = grid_count_body_normal
    target.grid_head_len = grid_head_len
    target.grid_fever_masks_bits = grid_fever_masks_bits
    target.grid_frontier_count = grid_frontier_count
    target.grid_frontier_offset = grid_frontier_offset
    target.grid_frontier_body_fever_pool = grid_frontier_body_fever_pool
    target.grid_frontier_body_normal_pool = grid_frontier_body_normal_pool
    target.grid_frontier_masks_bits_pool = grid_frontier_masks_bits_pool
    target.grid_frontier_head_coeffs_pool = grid_frontier_head_coeffs_pool
    target.grid_gap = grid_gap
    target.grid_fever_activations = grid_fever_activations
    target.song_timestamps = song_timestamps
    target.fever_end_idx_song = fever_end_idx_song
    target.song_note_group_idx = song_note_group_idx
    target.song_group_starts = song_group_starts
    target.song_group_base_t_ms = song_group_base_t_ms
    target.song_group_low_ms = song_group_low_ms
    target.song_group_high_ms = song_group_high_ms
    target.loadout_base_stats = loadout_base_stats
    target.loadout_indices = loadout_indices
    target.item_stats = item_stats
    target.base_fixed_stats = base_fixed_stats
    target.slot_start = slot_start
    target.slot_count = slot_count
    target.loadout_result_stats = loadout_result_stats
    target.chunk_best_key = chunk_best_key
    target.chunk_best_score = chunk_best_score
    target.chunk_best_idx = chunk_best_idx
    target.ftff_combo_ft = ftff_combo_ft
    target.ftff_combo_ff = ftff_combo_ff
    target.chunk_best_results = chunk_best_results
    target.skyline_scores = skyline_scores
def ensure_fields_allocated():
    """
    Ensure Taichi is initialized and fields are allocated.
    This is the main entry point for ensuring the GPU is ready.
    Initializes Taichi if needed, allocates fields, and binds them to kernels.
    """
    if not is_initialized():
        init_taichi()
    if not _fields_allocated:
        allocate_fields()
        global song_timestamps
        if song_timestamps is None:
            song_timestamps = ti.field(dtype=ti.f32, shape=MAX_SONG_NOTES)
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
        from . import kernels
        bind_fields(kernels)
