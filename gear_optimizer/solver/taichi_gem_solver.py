"""
Taichi Gem Solver - GPU-accelerated gem optimization for RX 7900 XTX (Vulkan).

This module ports the CPU scoring_core.py functions to Taichi kernels:
- lookup_ref: O(1) reference table lookup
- calc_score_device: Score calculation with fever/normal notes
- optimize_core_device: Greedy gem allocation optimizer
- solve_batch_kernel: Main entry point - processes all work items in parallel

Architecture:
    Python (scoring.py) --> load_ref_arrays() --> GPU fields (device-resident)
                       --> optimize_gems_batch_gpu() --> solve_batch_kernel
                       <-- results (score, gem counts)
"""
import taichi as ti
import numpy as np

# ============================================================================
# TAICHI INITIALIZATION
# ============================================================================

_ti_initialized = False


def init_taichi_vulkan():
    """
    Initialize Taichi with Vulkan backend for AMD GPUs.
    
    Called once by gpu_scheduler.py on the GPU thread, or lazily on first use.
    Uses f32 precision for performance (sufficient for score accuracy).
    """
    global _ti_initialized
    if not _ti_initialized:
        ti.init(arch=ti.vulkan, default_fp=ti.f32, default_ip=ti.i32)
        _ti_initialized = True
        print("[Taichi] Initialized with Vulkan backend (RX 7900 XTX) - f32 precision")


# ============================================================================
# GPU FIELDS (Device-resident data)
# ============================================================================

# Reference lookup tables (161 entries each, index 0-160)
ref_pp_field: ti.Field = None
ref_cm_field: ti.Field = None
ref_fm_field: ti.Field = None
ref_ft_field: ti.Field = None  # Fever Time multipliers
ref_ff_field: ti.Field = None  # Fever Fill Rate multipliers

# Timeline grid (161x161 = 26,521 entries per song)
GRID_SIZE = 161
grid_count_body_fever: ti.Field = None   # (161, 161) i32
grid_count_body_normal: ti.Field = None  # (161, 161) i32
grid_head_len: ti.Field = None           # (161, 161) i32
grid_fever_masks: ti.Field = None        # (161, 161, 100) i8 - head masks

# MEGA-BATCH work items (max 524k work items for V2 parallel kernel)
MAX_WORK_ITEMS = 524288  # 512k - supports 500 genomes × ~800 FT/FF combinations
MAX_HEAD_NOTES = 100
MAX_GENOMES = 512  # Support up to 512 unique genomes per batch

fever_masks: ti.Field = None  # (MAX_WORK_ITEMS, MAX_HEAD_NOTES) - i8

# Per-work-item inputs
work_budgets: ti.Field = None
work_count_fever: ti.Field = None
work_count_normal: ti.Field = None
work_ft_gems: ti.Field = None
work_ff_gems: ti.Field = None
work_head_len: ti.Field = None
work_genome_id: ti.Field = None  # Maps work item -> genome index

# Per-genome base stats (lookup by genome_id in kernel)
genome_base_pp: ti.Field = None
genome_base_cm: ti.Field = None
genome_base_fm: ti.Field = None
genome_base_p_val: ti.Field = None
genome_base_s_val: ti.Field = None
genome_base_ft: ti.Field = None  # Base Fever Time stat (for FT/FF iteration)
genome_base_ff: ti.Field = None  # Base Fever Fill Rate stat

# Per-work-item outputs
result_scores: ti.Field = None
result_pp: ti.Field = None
result_cm: ti.Field = None
result_fm: ti.Field = None
result_ov: ti.Field = None
result_p_val: ti.Field = None
result_s_val: ti.Field = None

# Per-genome outputs (for FT/FF iteration kernel)
genome_result_scores: ti.Field = None
genome_result_ft: ti.Field = None
genome_result_ff: ti.Field = None
genome_result_pp: ti.Field = None
genome_result_cm: ti.Field = None
genome_result_fm: ti.Field = None
genome_result_ov: ti.Field = None

_fields_allocated = False
_grid_fields_allocated = False
_last_uploaded_grid_id = None  # Cache to skip redundant grid uploads


def _allocate_fields():
    """Allocate GPU fields. Must be called after ti.init()."""
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global fever_masks, work_budgets, work_count_fever, work_count_normal
    global work_ft_gems, work_ff_gems, work_head_len, work_genome_id
    global genome_base_pp, genome_base_cm, genome_base_fm, genome_base_p_val, genome_base_s_val
    global genome_base_ft, genome_base_ff
    global result_scores, result_pp, result_cm, result_fm, result_ov
    global result_p_val, result_s_val, _fields_allocated
    global genome_result_scores, genome_result_ft, genome_result_ff
    global genome_result_pp, genome_result_cm, genome_result_fm, genome_result_ov
    
    if _fields_allocated:
        return
    
    # Reference tables (f32 for performance)
    ref_pp_field = ti.field(dtype=ti.f32, shape=161)
    ref_cm_field = ti.field(dtype=ti.f32, shape=161)
    ref_fm_field = ti.field(dtype=ti.f32, shape=161)
    ref_ft_field = ti.field(dtype=ti.f32, shape=161)
    ref_ff_field = ti.field(dtype=ti.f32, shape=161)
    
    # Work item inputs
    fever_masks = ti.field(dtype=ti.i8, shape=(MAX_WORK_ITEMS, MAX_HEAD_NOTES))
    work_budgets = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_count_fever = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_count_normal = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_ft_gems = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_ff_gems = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_head_len = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_genome_id = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    
    # Per-genome base stats (lookup by work_genome_id in kernel)
    genome_base_pp = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_cm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_fm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_p_val = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_s_val = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_ft = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_ff = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    
    # Per-work-item results
    result_scores = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_pp = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_cm = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_fm = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_ov = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_p_val = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_s_val = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    
    # Per-genome results (for FT/FF iteration kernel)
    genome_result_scores = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_ft = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_ff = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_pp = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_cm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_fm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_ov = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    
    _fields_allocated = True
    print(f"[Taichi] Allocated GPU fields: {MAX_WORK_ITEMS} work items, {MAX_HEAD_NOTES} head notes, {MAX_GENOMES} genomes")


# ============================================================================
# @ti.func IMPLEMENTATIONS (Ported from scoring_core.py)
# ============================================================================

@ti.func
def lookup_ref_pp(value: ti.i32) -> ti.f32:
    """O(1) lookup from Perfect Points reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_pp_field[idx]


@ti.func
def lookup_ref_cm(value: ti.i32) -> ti.f32:
    """O(1) lookup from Combo Multiplier reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_cm_field[idx]


@ti.func
def lookup_ref_fm(value: ti.i32) -> ti.f32:
    """O(1) lookup from Fever Multiplier reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_fm_field[idx]


@ti.func
def calc_score_device(
    base_value: ti.f32,  # Changed to f32 for performance
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    work_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    GPU port of fast_calculate_score (scoring_core.py:48-96).
    
    Calculates total score by:
    1. Body score: simple multiply (all notes past head at full combo)
    2. Head score: ramped combo scaling for first head_len notes
    
    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier from lookup
        fever_mul: Fever multiplier from lookup
        work_idx: Index into fever_masks for this work item
        head_len: Number of notes in the head (<=100)
        count_fever: Fever notes in body
        count_normal: Normal notes in body
        
    Returns:
        Total score as int32
    """
    # Body score (notes 101+) - base_value is already f32
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (ti.cast(count_normal, ti.f32) * combo_val)
    
    # Head score (notes 1-100) with ramped combo
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0
    
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if fever_masks[work_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    
    return ti.cast(body_score + head_score, ti.i32)


@ti.func
def optimize_core_device(
    work_idx: ti.i32,
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    GPU port of optimize_core_jit (scoring_core.py:99-278).
    
    Greedy gem allocation: at each iteration, evaluates 4 options:
    - PP gem (Perfect Points)
    - CM gem (Combo Multiplier)
    - FM gem (Fever Multiplier)
    - OV gem (Overflow/Elemental)
    
    Picks the option that maximizes score. Repeats until budget exhausted.
    
    Returns:
        Best final score after gem allocation
    """
    # Constants (matching constants.py)
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    
    gems_pp: ti.i32 = 0
    gems_cm: ti.i32 = 0
    gems_fm: ti.i32 = 0
    gems_ov: ti.i32 = 0
    remaining: ti.i32 = budget
    
    # Mutable state
    pp: ti.i32 = cur_pp
    cm: ti.i32 = cur_cm
    fm: ti.i32 = cur_fm
    p_val: ti.i32 = cur_p_val
    s_val: ti.i32 = cur_s_val
    
    best_final_score: ti.i32 = 0
    
    while remaining > 0:
        best_score: ti.i32 = -1
        best_opt: ti.i32 = -1
        fill_budget: ti.i32 = remaining - 1
        fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0
        
        # Option 0: PP gem
        if pp < MAX_STAT:
            t_pp: ti.i32 = pp + GEM_SCALE_NORMAL
            t_p: ti.i32 = p_val + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
            t_s: ti.i32 = s_val + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor: ti.f32 = lookup_ref_pp(t_pp)
            base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(cm)
            f_mul: ti.f32 = lookup_ref_fm(fm)
            score: ti.i32 = calc_score_device(base, c_mul, f_mul, work_idx, head_len, count_fever, count_normal)
            if score >= best_score:
                best_score = score
                best_opt = 0
        
        # Option 1: CM gem
        if cm < MAX_STAT:
            t_cm: ti.i32 = cm + GEM_SCALE_NORMAL
            t_p: ti.i32 = p_val + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
            t_s: ti.i32 = s_val + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor: ti.f32 = lookup_ref_pp(pp)
            base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(t_cm)
            f_mul: ti.f32 = lookup_ref_fm(fm)
            score: ti.i32 = calc_score_device(base, c_mul, f_mul, work_idx, head_len, count_fever, count_normal)
            if score > best_score:
                best_score = score
                best_opt = 1
        
        # Option 2: FM gem
        if fm < MAX_STAT:
            t_fm: ti.i32 = fm + GEM_SCALE_FEVER
            t_p: ti.i32 = p_val + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
            t_s: ti.i32 = s_val + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor: ti.f32 = lookup_ref_pp(pp)
            base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(cm)
            f_mul: ti.f32 = lookup_ref_fm(t_fm)
            score: ti.i32 = calc_score_device(base, c_mul, f_mul, work_idx, head_len, count_fever, count_normal)
            if score > best_score:
                best_score = score
                best_opt = 2
        
        # Option 3: Overflow (elemental gem on selected color)
        t_p: ti.i32 = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s: ti.i32 = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor: ti.f32 = lookup_ref_pp(pp)
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
        c_mul: ti.f32 = lookup_ref_cm(cm)
        f_mul: ti.f32 = lookup_ref_fm(fm)
        score: ti.i32 = calc_score_device(base, c_mul, f_mul, work_idx, head_len, count_fever, count_normal)
        if score >= best_score:
            best_score = score
            best_opt = 3
        
        # Apply best option
        if best_opt == 0:
            pp += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_pp
            s_val += GEM_STAT_TO_ELEMENT * is_s_pp
            gems_pp += 1
        elif best_opt == 1:
            cm += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_cm
            s_val += GEM_STAT_TO_ELEMENT * is_s_cm
            gems_cm += 1
        elif best_opt == 2:
            fm += GEM_SCALE_FEVER
            p_val += GEM_STAT_TO_ELEMENT * is_p_fm
            s_val += GEM_STAT_TO_ELEMENT * is_s_fm
            gems_fm += 1
        else:
            p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
        
        remaining -= 1
        best_final_score = best_score
    
    # Store results in output fields
    result_pp[work_idx] = gems_pp
    result_cm[work_idx] = gems_cm
    result_fm[work_idx] = gems_fm
    result_ov[work_idx] = gems_ov
    result_p_val[work_idx] = p_val
    result_s_val[work_idx] = s_val
    
    return best_final_score


# ============================================================================
# @ti.kernel ENTRY POINTS
# ============================================================================

@ti.kernel
def solve_batch_kernel(
    n_items: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    Main kernel - processes all work items in parallel.
    
    Each work item represents one (FT_gems, FF_gems) timeline combination
    for one genome. The kernel parallelizes across all work items.
    
    Per-genome base stats are looked up from genome_base_* fields using
    work_genome_id mapping (fixes per-genome stats bug).
    
    Args:
        n_items: Number of work items to process
        is_*: Boolean flags (0/1) for color contributions
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    
    for i in range(n_items):
        budget: ti.i32 = work_budgets[i]
        count_fever: ti.i32 = work_count_fever[i]
        count_normal: ti.i32 = work_count_normal[i]
        ft_gems: ti.i32 = work_ft_gems[i]
        ff_gems: ti.i32 = work_ff_gems[i]
        head_len: ti.i32 = work_head_len[i]
        
        # Look up per-genome base stats (fixes the per-genome stats bug!)
        genome_id: ti.i32 = work_genome_id[i]
        base_pp: ti.i32 = genome_base_pp[genome_id]
        base_cm: ti.i32 = genome_base_cm[genome_id]
        base_fm: ti.i32 = genome_base_fm[genome_id]
        base_p_val: ti.i32 = genome_base_p_val[genome_id]
        base_s_val: ti.i32 = genome_base_s_val[genome_id]
        
        # Adjust base p/s values for FT/FF gem contributions to elemental stats
        # FT gems add to Beat (is_p_ft/is_s_ft tells us if Beat is primary/secondary)
        # FF gems add to Vibe (is_p_ff/is_s_ff tells us if Vibe is primary/secondary)
        p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        score: ti.i32 = optimize_core_device(
            i, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            head_len, count_fever, count_normal,
        )
        result_scores[i] = score


def _allocate_grid_fields():
    """Allocate GPU fields for timeline grid. Must be called after ti.init()."""
    global grid_count_body_fever, grid_count_body_normal, grid_head_len, grid_fever_masks
    global _grid_fields_allocated
    
    if _grid_fields_allocated:
        return
    
    # Timeline grid (161x161 = 26,521 entries)
    grid_count_body_fever = ti.field(dtype=ti.i32, shape=(GRID_SIZE, GRID_SIZE))
    grid_count_body_normal = ti.field(dtype=ti.i32, shape=(GRID_SIZE, GRID_SIZE))
    grid_head_len = ti.field(dtype=ti.i32, shape=(GRID_SIZE, GRID_SIZE))
    grid_fever_masks = ti.field(dtype=ti.i8, shape=(GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES))
    
    _grid_fields_allocated = True
    print(f"[Taichi] Allocated grid fields: {GRID_SIZE}x{GRID_SIZE} timeline grid")


@ti.kernel
def solve_genomes_with_ftff_kernel(
    n_genomes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    New kernel that iterates FT/FF combinations INSIDE the GPU thread.
    
    Each thread handles one genome and iterates through all valid FT/FF
    combinations, using the preloaded timeline grid for O(1) lookups.
    
    This eliminates ~400k work item transfers per generation.
    
    Args:
        n_genomes: Number of genomes to process
        total_budget: Total gem budget (typically 90)
        gem_scale_fever: Gems per fever stat point (typically 3)
        is_*: Color contribution flags (0/1)
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    
    for genome_idx in range(n_genomes):
        # Load genome base stats
        base_pp: ti.i32 = genome_base_pp[genome_idx]
        base_cm: ti.i32 = genome_base_cm[genome_idx]
        base_fm: ti.i32 = genome_base_fm[genome_idx]
        base_p_val: ti.i32 = genome_base_p_val[genome_idx]
        base_s_val: ti.i32 = genome_base_s_val[genome_idx]
        base_ft_stat: ti.i32 = genome_base_ft[genome_idx]
        base_ff_stat: ti.i32 = genome_base_ff[genome_idx]
        
        # Compute max FT/FF gems based on stat headroom
        remaining_ft = MAX_STAT - base_ft_stat
        remaining_ff = MAX_STAT - base_ff_stat
        max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        
        # Track best result across all FT/FF combinations
        best_score: ti.i32 = -1
        best_ft: ti.i32 = 0
        best_ff: ti.i32 = 0
        best_g_pp: ti.i32 = 0
        best_g_cm: ti.i32 = 0
        best_g_fm: ti.i32 = 0
        best_g_ov: ti.i32 = 0
        
        # Iterate all valid FT/FF combinations
        for ft in range(ti.min(total_budget, max_ft_gems) + 1):
            remaining_for_ff: ti.i32 = total_budget - ft
            
            for ff in range(ti.min(remaining_for_ff, max_ff_gems) + 1):
                # Compute stat indices for grid lookup
                ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
                
                # O(1) lookup from grid
                count_fever: ti.i32 = grid_count_body_fever[ft_idx, ff_idx]
                count_normal: ti.i32 = grid_count_body_normal[ft_idx, ff_idx]
                head_len: ti.i32 = grid_head_len[ft_idx, ff_idx]
                
                # Budget remaining for PP/CM/FM/OV gems
                budget: ti.i32 = total_budget - ft - ff
                
                # Adjust p/s values for FT/FF gem contributions
                p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                
                # Run greedy gem allocation (inlined optimize_core_device variant)
                # We can't call optimize_core_device because it stores to work_item arrays
                gems_pp: ti.i32 = 0
                gems_cm: ti.i32 = 0
                gems_fm: ti.i32 = 0
                gems_ov: ti.i32 = 0
                cur_pp: ti.i32 = base_pp
                cur_cm: ti.i32 = base_cm
                cur_fm: ti.i32 = base_fm
                cur_p: ti.i32 = p_val
                cur_s: ti.i32 = s_val
                cur_remaining: ti.i32 = budget
                local_best_score: ti.i32 = 0
                
                GEM_SCALE_NORMAL: ti.i32 = 2
                GEM_SCALE_FEVER_LOCAL: ti.i32 = 3
                ELEMENTAL_GEM_SCALE: ti.i32 = 6
                
                while cur_remaining > 0:
                    best_opt_score: ti.i32 = -1
                    best_opt: ti.i32 = -1
                    fill_budget: ti.i32 = cur_remaining - 1
                    fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0
                    
                    # Option 0: PP gem
                    if cur_pp < MAX_STAT:
                        t_pp: ti.i32 = cur_pp + GEM_SCALE_NORMAL
                        t_p: ti.i32 = cur_p + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
                        t_s: ti.i32 = cur_s + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
                        pp_factor: ti.f32 = lookup_ref_pp(t_pp)
                        base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        c_mul: ti.f32 = lookup_ref_cm(cur_cm)
                        f_mul: ti.f32 = lookup_ref_fm(cur_fm)
                        score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if score >= best_opt_score:
                            best_opt_score = score
                            best_opt = 0
                    
                    # Option 1: CM gem
                    if cur_cm < MAX_STAT:
                        t_cm: ti.i32 = cur_cm + GEM_SCALE_NORMAL
                        t_p: ti.i32 = cur_p + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
                        t_s: ti.i32 = cur_s + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
                        pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
                        base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        c_mul: ti.f32 = lookup_ref_cm(t_cm)
                        f_mul: ti.f32 = lookup_ref_fm(cur_fm)
                        score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if score > best_opt_score:
                            best_opt_score = score
                            best_opt = 1
                    
                    # Option 2: FM gem
                    if cur_fm < MAX_STAT:
                        t_fm: ti.i32 = cur_fm + GEM_SCALE_FEVER_LOCAL
                        t_p: ti.i32 = cur_p + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
                        t_s: ti.i32 = cur_s + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
                        pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
                        base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        c_mul: ti.f32 = lookup_ref_cm(cur_cm)
                        f_mul: ti.f32 = lookup_ref_fm(t_fm)
                        score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if score > best_opt_score:
                            best_opt_score = score
                            best_opt = 2
                    
                    # Option 3: OV gem
                    t_p: ti.i32 = cur_p + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
                    t_s: ti.i32 = cur_s + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
                    pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
                    base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                    c_mul: ti.f32 = lookup_ref_cm(cur_cm)
                    f_mul: ti.f32 = lookup_ref_fm(cur_fm)
                    score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                    if score >= best_opt_score:
                        best_opt_score = score
                        best_opt = 3
                    
                    # Apply best option
                    if best_opt == 0:
                        cur_pp += GEM_SCALE_NORMAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_pp
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_pp
                        gems_pp += 1
                    elif best_opt == 1:
                        cur_cm += GEM_SCALE_NORMAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_cm
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_cm
                        gems_cm += 1
                    elif best_opt == 2:
                        cur_fm += GEM_SCALE_FEVER_LOCAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_fm
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_fm
                        gems_fm += 1
                    else:
                        cur_p += ELEMENTAL_GEM_SCALE * is_p_ov
                        cur_s += ELEMENTAL_GEM_SCALE * is_s_ov
                        gems_ov += 1
                    
                    cur_remaining -= 1
                    local_best_score = best_opt_score
                
                # Check if this FT/FF combo is better
                if local_best_score > best_score:
                    best_score = local_best_score
                    best_ft = ft
                    best_ff = ff
                    best_g_pp = gems_pp
                    best_g_cm = gems_cm
                    best_g_fm = gems_fm
                    best_g_ov = gems_ov
        
        # Store best result for this genome
        genome_result_scores[genome_idx] = best_score
        genome_result_ft[genome_idx] = best_ft
        genome_result_ff[genome_idx] = best_ff
        genome_result_pp[genome_idx] = best_g_pp
        genome_result_cm[genome_idx] = best_g_cm
        genome_result_fm[genome_idx] = best_g_fm
        genome_result_ov[genome_idx] = best_g_ov


@ti.func
def calc_score_with_grid(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using grid-stored fever masks.
    Reads fever mask from grid_fever_masks[ft_idx, ff_idx, :].
    """
    # Body score (notes 101+)
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (ti.cast(count_normal, ti.f32) * combo_val)
    
    # Head score (notes 1-100) with ramped combo
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0
    
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if grid_fever_masks[ft_idx, ff_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    
    return ti.cast(body_score + head_score, ti.i32)


# Work item fields for parallel FT/FF kernel (reuse existing result fields at genome level)
# We'll use a 2D parallelization: n_genomes × n_ftff_combos

@ti.kernel
def solve_ftff_parallel_kernel(
    n_work_items: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    V2 kernel: Parallelize across (genome, ft, ff) combinations.
    
    Each thread handles ONE (genome, ft, ff) combination.
    This gives 500 genomes × ~800 combos = 400k parallel threads.
    
    Uses work_* fields for input (genome_id, ft, ff) and result_* for output.
    Reduction to find best per genome is done on CPU after kernel.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    GEM_SCALE_NORMAL: ti.i32 = 2
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    
    for i in range(n_work_items):
        genome_idx: ti.i32 = work_genome_id[i]
        ft: ti.i32 = work_ft_gems[i]
        ff: ti.i32 = work_ff_gems[i]
        
        # Load genome base stats
        base_pp: ti.i32 = genome_base_pp[genome_idx]
        base_cm: ti.i32 = genome_base_cm[genome_idx]
        base_fm: ti.i32 = genome_base_fm[genome_idx]
        base_p_val: ti.i32 = genome_base_p_val[genome_idx]
        base_s_val: ti.i32 = genome_base_s_val[genome_idx]
        base_ft_stat: ti.i32 = genome_base_ft[genome_idx]
        base_ff_stat: ti.i32 = genome_base_ff[genome_idx]
        
        # Compute stat indices for grid lookup
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        
        # O(1) lookup from grid
        count_fever: ti.i32 = grid_count_body_fever[ft_idx, ff_idx]
        count_normal: ti.i32 = grid_count_body_normal[ft_idx, ff_idx]
        head_len: ti.i32 = grid_head_len[ft_idx, ff_idx]
        
        # Budget remaining for PP/CM/FM/OV gems
        budget: ti.i32 = total_budget - ft - ff
        
        # Adjust p/s values for FT/FF gem contributions
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        # Run greedy gem allocation
        gems_pp: ti.i32 = 0
        gems_cm: ti.i32 = 0
        gems_fm: ti.i32 = 0
        gems_ov: ti.i32 = 0
        cur_pp: ti.i32 = base_pp
        cur_cm: ti.i32 = base_cm
        cur_fm: ti.i32 = base_fm
        cur_p: ti.i32 = p_val
        cur_s: ti.i32 = s_val
        cur_remaining: ti.i32 = budget
        final_score: ti.i32 = 0
        
        while cur_remaining > 0:
            best_opt_score: ti.i32 = -1
            best_opt: ti.i32 = 3  # Default to OV
            fill_budget: ti.i32 = cur_remaining - 1
            fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0
            
            # Option 0: PP gem
            if cur_pp < MAX_STAT:
                t_pp: ti.i32 = cur_pp + GEM_SCALE_NORMAL
                t_p: ti.i32 = cur_p + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
                t_s: ti.i32 = cur_s + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
                pp_factor: ti.f32 = lookup_ref_pp(t_pp)
                base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                c_mul: ti.f32 = lookup_ref_cm(cur_cm)
                f_mul: ti.f32 = lookup_ref_fm(cur_fm)
                score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if score >= best_opt_score:
                    best_opt_score = score
                    best_opt = 0
            
            # Option 1: CM gem
            if cur_cm < MAX_STAT:
                t_cm: ti.i32 = cur_cm + GEM_SCALE_NORMAL
                t_p: ti.i32 = cur_p + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
                t_s: ti.i32 = cur_s + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
                pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
                base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                c_mul: ti.f32 = lookup_ref_cm(t_cm)
                f_mul: ti.f32 = lookup_ref_fm(cur_fm)
                score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if score > best_opt_score:
                    best_opt_score = score
                    best_opt = 1
            
            # Option 2: FM gem
            if cur_fm < MAX_STAT:
                t_fm: ti.i32 = cur_fm + gem_scale_fever
                t_p: ti.i32 = cur_p + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
                t_s: ti.i32 = cur_s + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
                pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
                base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                c_mul: ti.f32 = lookup_ref_cm(cur_cm)
                f_mul: ti.f32 = lookup_ref_fm(t_fm)
                score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if score > best_opt_score:
                    best_opt_score = score
                    best_opt = 2
            
            # Option 3: OV gem
            t_p: ti.i32 = cur_p + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
            t_s: ti.i32 = cur_s + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
            pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
            base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(cur_cm)
            f_mul: ti.f32 = lookup_ref_fm(cur_fm)
            score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
            if score >= best_opt_score:
                best_opt_score = score
                best_opt = 3
            
            # Apply best option
            if best_opt == 0:
                cur_pp += GEM_SCALE_NORMAL
                cur_p += GEM_STAT_TO_ELEMENT * is_p_pp
                cur_s += GEM_STAT_TO_ELEMENT * is_s_pp
                gems_pp += 1
            elif best_opt == 1:
                cur_cm += GEM_SCALE_NORMAL
                cur_p += GEM_STAT_TO_ELEMENT * is_p_cm
                cur_s += GEM_STAT_TO_ELEMENT * is_s_cm
                gems_cm += 1
            elif best_opt == 2:
                cur_fm += gem_scale_fever
                cur_p += GEM_STAT_TO_ELEMENT * is_p_fm
                cur_s += GEM_STAT_TO_ELEMENT * is_s_fm
                gems_fm += 1
            else:
                cur_p += ELEMENTAL_GEM_SCALE * is_p_ov
                cur_s += ELEMENTAL_GEM_SCALE * is_s_ov
                gems_ov += 1
            
            cur_remaining -= 1
            final_score = best_opt_score
        
        # Store result for this work item (reduction done on CPU)
        result_scores[i] = final_score
        result_pp[i] = gems_pp
        result_cm[i] = gems_cm
        result_fm[i] = gems_fm
        result_ov[i] = gems_ov


# ============================================================================
# PYTHON WRAPPER API
# ============================================================================

_ref_loaded = False


def load_ref_arrays(ref_arrays: dict):
    """
    Upload reference arrays to GPU fields.
    
    Must be called once before using optimize_gems_batch_gpu().
    Typically called when switching songs or on first use.
    
    Args:
        ref_arrays: Dict with keys "Perfect Points", "Combo Multiplier", "Fever Multiplier"
                    Each value is a NumPy array of shape (161,)
    """
    global _ref_loaded
    
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    ref_pp_field.from_numpy(ref_arrays["Perfect Points"].astype(np.float32))
    ref_cm_field.from_numpy(ref_arrays["Combo Multiplier"].astype(np.float32))
    ref_fm_field.from_numpy(ref_arrays["Fever Multiplier"].astype(np.float32))
    
    _ref_loaded = True


def optimize_gems_gpu(
    budget: int,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
    cur_pp: int, cur_cm: int, cur_fm: int,
    cur_p_val: int, cur_s_val: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
):
    """
    Single-item GPU gem optimization (for compatibility with existing code).
    
    Wraps the batch API for single-item use.
    """
    batch_input = [{
        "budget": budget,
        "fever_mask_head": fever_mask_head,
        "count_body_fever": count_body_fever,
        "count_body_normal": count_body_normal,
        "ft_gems": 0,
        "ff_gems": 0,
    }]
    
    results = optimize_gems_batch_gpu(
        batch_input,
        cur_pp, cur_cm, cur_fm,
        base_p_val=cur_p_val,
        base_s_val=cur_s_val,
        is_p_ft=0, is_s_ft=0,
        is_p_ff=0, is_s_ff=0,
        is_p_pp=is_p_pp, is_s_pp=is_s_pp,
        is_p_cm=is_p_cm, is_s_cm=is_s_cm,
        is_p_fm=is_p_fm, is_s_fm=is_s_fm,
        is_p_ov=is_p_ov, is_s_ov=is_s_ov,
        ref_arrays=ref_arrays,
    )
    
    return results[0] if results else None


def optimize_gems_batch_gpu(
    batch_input: list,
    cur_pp: int, cur_cm: int, cur_fm: int,
    base_p_val: int, base_s_val: int,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
) -> list:
    """
    Batch GPU gem optimization - main entry point.
    
    Processes multiple work items in a single kernel launch.
    Automatically handles per-item base stat overrides (for batch coalescing)
    by mapping unique base stat combinations to temporary genome IDs.
    
    Args:
        batch_input: List of dicts. Optional keys "_base_p_val", "_base_s_val"
                     override the function arguments for that specific item.
    """
    global _ref_loaded
    
    n = len(batch_input)
    if n == 0:
        return []
    
    # Handle large batches by chunking
    if n > MAX_WORK_ITEMS:
        all_results = []
        for chunk_start in range(0, n, MAX_WORK_ITEMS):
            chunk_end = min(chunk_start + MAX_WORK_ITEMS, n)
            chunk = batch_input[chunk_start:chunk_end]
            chunk_results = optimize_gems_batch_gpu(
                chunk, cur_pp, cur_cm, cur_fm,
                base_p_val, base_s_val,
                is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm,
                is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                ref_arrays,
            )
            all_results.extend(chunk_results)
        return all_results
    
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    # ========================================================================
    # DYNAMIC GENOME MAPPING (Fix for Batch Coalescing)
    # ========================================================================
    # Identify unique (base_p, base_s) pairs to support merged batches
    
    unique_stats_map = {}  # (p, s) -> genome_id
    next_genome_id = 0
    
    # Default stats
    default_stats = (base_p_val, base_s_val)
    
    # Preallocate NumPy arrays
    budgets_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    count_fever_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    count_normal_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    ft_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    ff_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    head_len_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    genome_id_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    fever_masks_np = np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8)
    
    for i, item in enumerate(batch_input):
        budgets_np[i] = item["budget"]
        count_fever_np[i] = item["count_body_fever"]
        count_normal_np[i] = item["count_body_normal"]
        ft_gems_np[i] = item.get("ft_gems", 0)
        ff_gems_np[i] = item.get("ff_gems", 0)
        
        mask = item.get("fever_mask_head")
        if mask is not None:
            hl = min(len(mask), MAX_HEAD_NOTES)
            head_len_np[i] = hl
            fever_masks_np[i, :hl] = mask[:hl].astype(np.int8)
            
        # Check for overrides
        p = item.get("_base_p_val", base_p_val)
        s = item.get("_base_s_val", base_s_val)
        stats_key = (p, s)
        
        if stats_key not in unique_stats_map:
            unique_stats_map[stats_key] = next_genome_id
            next_genome_id += 1
            
        genome_id_np[i] = unique_stats_map[stats_key]
    
    # Ensure we don't exceed max genomes (unlikely for reasonable batches)
    if next_genome_id > MAX_GENOMES:
        # Fallback: Process sequentially or raise error. 
        # For now, just error as 512 distinct stat combos in one batch is extreme.
        raise RuntimeError(f"Too many unique base stat combinations in batch ({next_genome_id} > {MAX_GENOMES})")
        
    # Upload per-genome stats
    genome_pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_p_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_s_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    
    # Fill standard stats for all used genomes
    # Note: pp/cm/fm are still constant for the whole batch based on function args
    # If they needed to vary, we'd need them in the unique key too.
    for (p, s), gid in unique_stats_map.items():
        genome_pp_np[gid] = cur_pp
        genome_cm_np[gid] = cur_cm
        genome_fm_np[gid] = cur_fm
        genome_p_np[gid] = p
        genome_s_np[gid] = s
        
    genome_base_pp.from_numpy(genome_pp_np)
    genome_base_cm.from_numpy(genome_cm_np)
    genome_base_fm.from_numpy(genome_fm_np)
    genome_base_p_val.from_numpy(genome_p_np)
    genome_base_s_val.from_numpy(genome_s_np)
    
    # BULK transfer
    work_budgets.from_numpy(budgets_np)
    work_count_fever.from_numpy(count_fever_np)
    work_count_normal.from_numpy(count_normal_np)
    work_ft_gems.from_numpy(ft_gems_np)
    work_ff_gems.from_numpy(ff_gems_np)
    work_head_len.from_numpy(head_len_np)
    work_genome_id.from_numpy(genome_id_np)
    fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel
    solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = result_scores.to_numpy()[:n]
    pp_np = result_pp.to_numpy()[:n]
    cm_np = result_cm.to_numpy()[:n]
    fm_np = result_fm.to_numpy()[:n]
    ov_np = result_ov.to_numpy()[:n]
    p_val_np = result_p_val.to_numpy()[:n]
    s_val_np = result_s_val.to_numpy()[:n]
    
    results = [
        (int(scores_np[i]), int(pp_np[i]), int(cm_np[i]), int(fm_np[i]),
         int(p_val_np[i]), int(s_val_np[i]),
         int(pp_np[i]), int(cm_np[i]), int(fm_np[i]), int(ov_np[i]))
        for i in range(n)
    ]
    
    return results


def mega_batch_solve_population(
    work_items: list,
    genome_ids: np.ndarray,
    genome_stats: dict,  # NEW: {genome_idx: (base_pp, base_cm, base_fm, base_p_val, base_s_val)}
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
) -> dict:
    """
    MEGA-BATCH solver - processes all work items from ALL genomes in one kernel.
    
    This is the highest-performance path: flatten all timelines from all genomes,
    launch one kernel, then reduce to find best score per genome.
    
    FIXED: Now accepts per-genome stats instead of shared stats.
    
    Args:
        work_items: Flattened list of all work items from all genomes
        genome_ids: np.ndarray mapping work_item index -> genome index
        genome_stats: Dict mapping genome_idx -> (base_pp, base_cm, base_fm, base_p_val, base_s_val)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup tables
        
    Returns:
        dict: {genome_idx: (score, pp, cm, fm, p_val, s_val, g_pp, g_cm, g_fm, g_ov)}
    """
    global _ref_loaded
    
    n = len(work_items)
    if n == 0:
        return {}
    
    n_genomes = len(genome_stats)
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Number of genomes {n_genomes} exceeds maximum {MAX_GENOMES}")
    
    # Ensure Taichi is initialized
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    # Handle large batches by chunking
    if n > MAX_WORK_ITEMS:
        all_results = {}
        for chunk_start in range(0, n, MAX_WORK_ITEMS):
            chunk_end = min(chunk_start + MAX_WORK_ITEMS, n)
            chunk_items = work_items[chunk_start:chunk_end]
            chunk_genome_ids = genome_ids[chunk_start:chunk_end]
            chunk_results = mega_batch_solve_population(
                chunk_items, chunk_genome_ids, genome_stats,
                is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm,
                is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                ref_arrays,
            )
            # Merge results (keep best per genome)
            for gid, result in chunk_results.items():
                if gid not in all_results or result[0] > all_results[gid][0]:
                    all_results[gid] = result
        return all_results
    
    # ========================================================================
    # UPLOAD PER-GENOME STATS (fixes the per-genome stats bug!)
    # ========================================================================
    
    genome_pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_p_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_s_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    
    for gid, (base_pp, base_cm, base_fm, base_p, base_s) in genome_stats.items():
        genome_pp_np[gid] = base_pp
        genome_cm_np[gid] = base_cm
        genome_fm_np[gid] = base_fm
        genome_p_np[gid] = base_p
        genome_s_np[gid] = base_s
    
    genome_base_pp.from_numpy(genome_pp_np)
    genome_base_cm.from_numpy(genome_cm_np)
    genome_base_fm.from_numpy(genome_fm_np)
    genome_base_p_val.from_numpy(genome_p_np)
    genome_base_s_val.from_numpy(genome_s_np)
    
    # ========================================================================
    # UPLOAD WORK ITEMS WITH GENOME IDS
    # ========================================================================
    
    budgets_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    count_fever_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    count_normal_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    ft_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    ff_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    head_len_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    genome_id_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
    fever_masks_np = np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8)
    
    for i, item in enumerate(work_items):
        budgets_np[i] = item["budget"]
        count_fever_np[i] = item["count_body_fever"]
        count_normal_np[i] = item["count_body_normal"]
        ft_gems_np[i] = item.get("ft_gems", 0)
        ff_gems_np[i] = item.get("ff_gems", 0)
        genome_id_np[i] = genome_ids[i]
        
        mask = item.get("fever_mask_head")
        if mask is not None:
            head_len = min(len(mask), MAX_HEAD_NOTES)
            head_len_np[i] = head_len
            fever_masks_np[i, :head_len] = mask[:head_len].astype(np.int8)
    
    work_budgets.from_numpy(budgets_np)
    work_count_fever.from_numpy(count_fever_np)
    work_count_normal.from_numpy(count_normal_np)
    work_ft_gems.from_numpy(ft_gems_np)
    work_ff_gems.from_numpy(ff_gems_np)
    work_head_len.from_numpy(head_len_np)
    work_genome_id.from_numpy(genome_id_np)
    fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel (uses genome lookup for base stats)
    solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = result_scores.to_numpy()[:n]
    pp_np = result_pp.to_numpy()[:n]
    cm_np = result_cm.to_numpy()[:n]
    fm_np = result_fm.to_numpy()[:n]
    ov_np = result_ov.to_numpy()[:n]
    p_val_np = result_p_val.to_numpy()[:n]
    s_val_np = result_s_val.to_numpy()[:n]
    
    # Reduce: find best score per genome
    best_per_genome = {}
    
    for i in range(n):
        genome_idx = int(genome_ids[i])
        score = int(scores_np[i])
        
        if genome_idx not in best_per_genome or score > best_per_genome[genome_idx][0]:
            best_per_genome[genome_idx] = (
                score,
                int(pp_np[i]), int(cm_np[i]), int(fm_np[i]),
                int(p_val_np[i]), int(s_val_np[i]),
                int(pp_np[i]), int(cm_np[i]), int(fm_np[i]), int(ov_np[i]),
                int(ft_gems_np[i]), int(ff_gems_np[i])  # Added FT/FF specific to this result
            )
    
    return best_per_genome


def solve_genomes_with_ftff(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
) -> list:
    """
    NEW: Solve gem allocation for multiple genomes with GPU-resident FT/FF iteration.
    
    This function uploads the timeline grid ONCE, then processes all genomes
    in a single kernel launch that iterates FT/FF combinations on-GPU.
    
    This is ~100x faster than the old approach which transferred 400k work items.
    
    Args:
        genome_stats_list: List of dicts, each with keys:
            - base_pp, base_cm, base_fm, base_p_val, base_s_val
            - base_ft_stat, base_ff_stat
        timeline_grid: SongTimelineGrid object (must have precompute_all() called)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Total gem budget (default 90)
        gem_scale_fever: Stat points per fever gem (default 3)
        
    Returns:
        List of result tuples: (score, ft, ff, pp, cm, fm, ov) per genome
    """
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _grid_fields_allocated:
        _allocate_grid_fields()
    
    # Upload reference arrays if needed
    global _ref_loaded
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Upload timeline grid to GPU (once per song)
    _upload_timeline_grid(timeline_grid)
    
    # Upload per-genome stats
    pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    p_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    s_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ft_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ff_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    
    for i, stats in enumerate(genome_stats_list):
        pp_np[i] = stats["base_pp"]
        cm_np[i] = stats["base_cm"]
        fm_np[i] = stats["base_fm"]
        p_val_np[i] = stats["base_p_val"]
        s_val_np[i] = stats["base_s_val"]
        ft_np[i] = stats["base_ft_stat"]
        ff_np[i] = stats["base_ff_stat"]
    
    genome_base_pp.from_numpy(pp_np)
    genome_base_cm.from_numpy(cm_np)
    genome_base_fm.from_numpy(fm_np)
    genome_base_p_val.from_numpy(p_val_np)
    genome_base_s_val.from_numpy(s_val_np)
    genome_base_ft.from_numpy(ft_np)
    genome_base_ff.from_numpy(ff_np)
    
    # Launch kernel
    solve_genomes_with_ftff_kernel(
        n_genomes,
        total_budget,
        gem_scale_fever,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = genome_result_scores.to_numpy()[:n_genomes]
    ft_out_np = genome_result_ft.to_numpy()[:n_genomes]
    ff_out_np = genome_result_ff.to_numpy()[:n_genomes]
    pp_out_np = genome_result_pp.to_numpy()[:n_genomes]
    cm_out_np = genome_result_cm.to_numpy()[:n_genomes]
    fm_out_np = genome_result_fm.to_numpy()[:n_genomes]
    ov_out_np = genome_result_ov.to_numpy()[:n_genomes]
    
    results = []
    for i in range(n_genomes):
        results.append((
            int(scores_np[i]),
            int(ft_out_np[i]),
            int(ff_out_np[i]),
            int(pp_out_np[i]),
            int(cm_out_np[i]),
            int(fm_out_np[i]),
            int(ov_out_np[i]),
        ))
    
    return results


_grid_uploaded = False


def _upload_timeline_grid(timeline_grid):
    """Upload timeline grid to GPU fields (with caching)."""
    global _grid_uploaded, _last_uploaded_grid_id
    
    # Skip if same grid already uploaded (major optimization!)
    grid_id = id(timeline_grid)
    if _grid_uploaded and _last_uploaded_grid_id == grid_id:
        return
    
    # Ensure all timelines are computed
    timeline_grid.precompute_all()
    
    # Get grid data
    grid_size = timeline_grid.GRID_SIZE
    
    # Allocate numpy arrays
    cbf_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    cbn_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    hl_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    masks_np = np.zeros((GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int8)
    
    # Fill from grid
    for ft_idx in range(grid_size):
        for ff_idx in range(grid_size):
            timeline = timeline_grid._timeline_grid[ft_idx][ff_idx]
            if timeline is not None:
                fever_mask_head, count_fever, count_normal, _ = timeline
                cbf_np[ft_idx, ff_idx] = count_fever
                cbn_np[ft_idx, ff_idx] = count_normal
                head_len = min(len(fever_mask_head), MAX_HEAD_NOTES)
                hl_np[ft_idx, ff_idx] = head_len
                masks_np[ft_idx, ff_idx, :head_len] = fever_mask_head[:head_len].astype(np.int8)
    
    # Upload to GPU
    grid_count_body_fever.from_numpy(cbf_np)
    grid_count_body_normal.from_numpy(cbn_np)
    grid_head_len.from_numpy(hl_np)
    grid_fever_masks.from_numpy(masks_np)
    
    _grid_uploaded = True
    _last_uploaded_grid_id = grid_id


def solve_genomes_parallel(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
) -> list:
    """
    V2: Solve gem allocation with MAXIMUM parallelism.
    
    Parallelizes across (genome, ft, ff) combinations = ~400k threads.
    This combines the parallelism of the old approach with the low transfer
    overhead of the new approach.
    
    Args:
        genome_stats_list: List of dicts with base stats per genome
        timeline_grid: SongTimelineGrid (precompute_all will be called)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)
        
    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _grid_fields_allocated:
        _allocate_grid_fields()
    
    global _ref_loaded
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Upload timeline grid
    _upload_timeline_grid(timeline_grid)
    
    # Upload per-genome stats
    pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    p_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    s_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ft_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ff_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    
    # Also track max allowed FT/FF per genome for work item generation
    max_ft_list = []
    max_ff_list = []
    
    for i, stats in enumerate(genome_stats_list):
        pp_np[i] = stats["base_pp"]
        cm_np[i] = stats["base_cm"]
        fm_np[i] = stats["base_fm"]
        p_val_np[i] = stats["base_p_val"]
        s_val_np[i] = stats["base_s_val"]
        ft_np[i] = stats["base_ft_stat"]
        ff_np[i] = stats["base_ff_stat"]
        
        # Compute max FT/FF gems
        remaining_ft = 160 - stats["base_ft_stat"]
        remaining_ff = 160 - stats["base_ff_stat"]
        max_ft = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        max_ft_list.append(min(total_budget, max_ft))
        max_ff_list.append(min(total_budget, max_ff))
    
    genome_base_pp.from_numpy(pp_np)
    genome_base_cm.from_numpy(cm_np)
    genome_base_fm.from_numpy(fm_np)
    genome_base_p_val.from_numpy(p_val_np)
    genome_base_s_val.from_numpy(s_val_np)
    genome_base_ft.from_numpy(ft_np)
    genome_base_ff.from_numpy(ff_np)
    
    # Generate work items: (genome_id, ft, ff) for all valid combinations
    work_genome = []
    work_ft = []
    work_ff = []
    
    for genome_idx in range(n_genomes):
        max_ft = max_ft_list[genome_idx]
        max_ff = max_ff_list[genome_idx]
        
        for ft in range(max_ft + 1):
            remaining = total_budget - ft
            for ff in range(min(remaining, max_ff) + 1):
                work_genome.append(genome_idx)
                work_ft.append(ft)
                work_ff.append(ff)
    
    n_work = len(work_genome)
    
    if n_work == 0:
        return [(0, 0, 0, 0, 0, 0, 0) for _ in range(n_genomes)]
    
    # Track best results per genome across all chunks
    best_per_genome = {}
    
    # Process in chunks if exceeds MAX_WORK_ITEMS
    chunk_size = MAX_WORK_ITEMS
    num_chunks = (n_work + chunk_size - 1) // chunk_size
    
    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, n_work)
        chunk_n = end - start
        
        # Upload work items for this chunk
        genome_id_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
        ft_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
        ff_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
        
        genome_id_np[:chunk_n] = work_genome[start:end]
        ft_gems_np[:chunk_n] = work_ft[start:end]
        ff_gems_np[:chunk_n] = work_ff[start:end]
        
        work_genome_id.from_numpy(genome_id_np)
        work_ft_gems.from_numpy(ft_gems_np)
        work_ff_gems.from_numpy(ff_gems_np)
        
        # Launch kernel
        solve_ftff_parallel_kernel(
            chunk_n,
            total_budget,
            gem_scale_fever,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm,
            is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        )
        
        ti.sync()
        
        # Download results for this chunk
        scores_np = result_scores.to_numpy()[:chunk_n]
        pp_out = result_pp.to_numpy()[:chunk_n]
        cm_out = result_cm.to_numpy()[:chunk_n]
        fm_out = result_fm.to_numpy()[:chunk_n]
        ov_out = result_ov.to_numpy()[:chunk_n]
        
        # Reduce: find best score per genome (merge with global best)
        for i in range(chunk_n):
            gid = work_genome[start + i]
            score = int(scores_np[i])
            
            if gid not in best_per_genome or score > best_per_genome[gid][0]:
                best_per_genome[gid] = (
                    score,
                    work_ft[start + i],
                    work_ff[start + i],
                    int(pp_out[i]),
                    int(cm_out[i]),
                    int(fm_out[i]),
                    int(ov_out[i]),
                )
    
    # Return in order
    results = []
    for i in range(n_genomes):
        if i in best_per_genome:
            results.append(best_per_genome[i])
        else:
            results.append((0, 0, 0, 0, 0, 0, 0))
    
    return results


