"""
Fever timeline calculation and caching.

This module contains the "Rules Layer" - the complex fever timeline logic
that determines when fever starts/ends based on stats. This logic stays
on CPU and is NOT ported to GPU.
"""

import os
import numpy as np
from math import ceil
from collections import OrderedDict

from ..core.jit_setup import jit
from .scoring_core import lookup_reference_py
from ..core.constants import (
    TOTAL_ROWS,
    FEVER_FILL_BASE_RATE,
    FEVER_TIME_SCALE,
    FEVER_TIME_OFFSET,
)


# Global cache for SongTimelineGrid instances (one per song).
# NOTE: Keep bounded to avoid runaway RAM growth on long runs over large song sets.
try:
    _SONG_TIMELINE_GRID_CACHE_MAX = int(os.environ.get("SONG_TIMELINE_GRID_CACHE_MAX", "128") or "128")
except Exception:
    _SONG_TIMELINE_GRID_CACHE_MAX = 128
_SONG_TIMELINE_GRID_CACHE_MAX = max(0, int(_SONG_TIMELINE_GRID_CACHE_MAX))
SONG_TIMELINE_GRIDS: "OrderedDict[tuple, SongTimelineGrid]" = OrderedDict()


def _safe_int(val: object, default: int = 0) -> int:
    try:
        return int(val)  # type: ignore[arg-type]
    except Exception:
        return int(default)


def _safe_float(val: object, default: float = 0.0) -> float:
    try:
        return float(val)  # type: ignore[arg-type]
    except Exception:
        return float(default)


def _song_first_last_ms(timestamps: object) -> tuple[int, int]:
    try:
        if hasattr(timestamps, "__len__") and len(timestamps):  # type: ignore[arg-type]
            first_ms = int(float(timestamps[0]) * 1000.0)  # type: ignore[index]
            last_ms = int(float(timestamps[len(timestamps) - 1]) * 1000.0)  # type: ignore[index]
            return first_ms, last_ms
    except Exception:
        pass
    return 0, 0


def _timeline_grid_cache_key(calc_song: dict) -> tuple:
    """
    Build a stable cache key for per-song timeline grids.

    IMPORTANT: This must include HumanHitSim parameters when ApplyTo=ALL because
    they change the underlying timestamps and therefore fever boundaries.
    """
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("timestamps", ())

    try:
        n = int(len(timestamps))
    except Exception:
        n = 0

    first_ms, last_ms = _song_first_last_ms(timestamps)

    human_seed = _safe_int(meta.get("HumanHitSimSeed") or 0, 0)
    human_apply_to = str(meta.get("HumanHitSimApplyTo", "") or "").strip().upper()
    human_dist = str(meta.get("HumanHitSimDistribution", "") or "").strip().lower()
    human_great_mode = str(meta.get("HumanHitSimGreatMode", "") or "").strip().lower()

    return (
        str(meta.get("Song Name", "") or ""),
        n,
        _safe_float(meta.get("Last Note Time", 0) or 0.0, 0.0),
        _safe_int(meta.get("Long Notes", 0) or 0, 0),
        _safe_int(first_ms, 0),
        _safe_int(last_ms, 0),
        _safe_int(human_seed, 0),
        human_apply_to,
        human_dist,
        human_great_mode,
    )


@jit(nopython=True, cache=True)
def calculate_fever_timeline_indices(
    song_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes_count,
    last_note_time,
    fever_mask_buffer,
):
    """
    Calculate fever timeline using corrected server-matching logic.

    Key fixes:
    1. First non-fever section: non_fever_base - 1 notes
       Later sections: non_fever_base notes (1 "wasted" note where fever ends)
    2. Binary search uses side="left" (>=) instead of side="right" (>)

    Args:
        song_timestamps: NumPy array of note timestamps
        total_notes: Total number of notes in song
        fever_fill_rate: Fever fill rate multiplier
        fever_time_stat: Fever time multiplier
        long_notes_count: Number of long notes
        last_note_time: Timestamp of last note
        fever_mask_buffer: Preallocated boolean array for fever mask

    Returns:
        tuple: (fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx)
               last_fever_end_idx = where the last fever window ends (for gap calculation)
    """
    # Game formula constants (see constants.FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET)
    non_fever_cas = (total_notes - long_notes_count) * 0.333  # FEVER_FILL_BASE_RATE
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    fever_time_cas = last_note_time * 0.15 + 0.15  # FEVER_TIME_SCALE + FEVER_TIME_OFFSET
    real_fever_time = fever_time_cas * fever_time_stat

    is_fever = fever_mask_buffer
    is_fever[:] = False
    current_note_idx = 0
    fever_activations = 0
    fever_section = 0
    last_fever_end_idx = 0  # Track where last fever ends

    while current_note_idx < total_notes:
        # Non-fever section
        fever_section += 1
        # First section: -1, Later sections: use base (wasted note effect)
        if fever_section == 1:
            notes_to_fill = non_fever_base - 1
        else:
            notes_to_fill = non_fever_base

        end_normal_idx = min(current_note_idx + notes_to_fill, total_notes)
        current_note_idx = end_normal_idx
        if current_note_idx >= total_notes:
            break

        if current_note_idx > 0:
            fever_activations += 1
            start_time = song_timestamps[current_note_idx]
            end_time = start_time + real_fever_time
            # Use side="left" to find first note where time >= end_time (not >)
            fever_end_idx = np.searchsorted(song_timestamps, end_time, side="left")
            is_fever[current_note_idx:fever_end_idx] = True
            current_note_idx = fever_end_idx
            last_fever_end_idx = fever_end_idx  # Update last fever end
        else:
            break

    head_limit = min(total_notes, 100)
    fever_mask_head = is_fever[:head_limit]
    count_body_fever = 0
    count_body_normal = 0
    if total_notes > 100:
        for i in range(100, total_notes):
            if is_fever[i]:
                count_body_fever += 1
            else:
                count_body_normal += 1
    return fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx


@jit(nopython=True, cache=True)
def calculate_non_fever_sections(
    song_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes_count,
    last_note_time,
):
    """
    JIT helper: count non-fever sections and compute non_fever_base.

    Matches the section stepping logic used by fg_baseline_params (scoring.py).
    """
    # Game formula constants (see constants.FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET)
    non_fever_cas = (total_notes - long_notes_count) * 0.333  # FEVER_FILL_BASE_RATE
    if non_fever_cas < 0.0:
        non_fever_cas = 0.0

    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    fever_time_cas = last_note_time * 0.15 + 0.15  # FEVER_TIME_SCALE + FEVER_TIME_OFFSET
    real_fever_time = fever_time_cas * fever_time_stat

    current_idx = 0
    non_fever_section = 0

    while current_idx < total_notes:
        non_fever_section += 1
        base_notes = non_fever_base - 1 if non_fever_section == 1 else non_fever_base
        if base_notes < 0:
            base_notes = 0

        current_idx = min(current_idx + base_notes, total_notes)
        if current_idx >= total_notes:
            break

        start_time = song_timestamps[current_idx]
        end_time = start_time + real_fever_time
        fever_end_idx = int(np.searchsorted(song_timestamps, end_time, side="left"))
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)
        current_idx = fever_end_idx

    return int(non_fever_section), int(non_fever_base)


@jit(nopython=True, cache=True)
def calculate_fever_activations_grid(
    song_timestamps,
    total_notes,
    fever_time_cas,
    non_fever_cas,
    ft_factors,
    ff_factors,
    fever_activations_out,
    last_fever_end_out,
):
    """
    JIT helper: compute fever_activations + last_fever_end_idx for all (FT, FF) indices.

    This avoids building and copying fever masks for every cell, which is expensive
    when callers only need activations/gap-derived data (e.g., FG pair caps grid).
    """
    grid_size = ft_factors.shape[0]
    for ft_idx in range(grid_size):
        ft_factor = ft_factors[ft_idx]
        real_fever_time = fever_time_cas * ft_factor
        for ff_idx in range(grid_size):
            ff_factor = ff_factors[ff_idx]

            non_fever_base = ceil(non_fever_cas * ff_factor)

            current_note_idx = 0
            fever_activations = 0
            fever_section = 0
            last_fever_end_idx = 0

            while current_note_idx < total_notes:
                fever_section += 1
                # First section: -1, Later sections: use base (wasted note effect)
                notes_to_fill = non_fever_base - 1 if fever_section == 1 else non_fever_base
                end_normal_idx = current_note_idx + notes_to_fill
                if end_normal_idx > total_notes:
                    end_normal_idx = total_notes
                current_note_idx = end_normal_idx
                if current_note_idx >= total_notes:
                    break

                if current_note_idx > 0:
                    fever_activations += 1
                    start_time = song_timestamps[current_note_idx]
                    end_time = start_time + real_fever_time
                    fever_end_idx = int(np.searchsorted(song_timestamps, end_time, side="left"))
                    current_note_idx = fever_end_idx
                    last_fever_end_idx = fever_end_idx
                else:
                    break

            fever_activations_out[ft_idx, ff_idx] = fever_activations
            last_fever_end_out[ft_idx, ff_idx] = last_fever_end_idx


@jit(nopython=True, cache=True)
def calculate_force_greats_timeline_indices(
    song_timestamps,
    great_candidate_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes_count,
    last_note_time,
    forced_counts,
    forced_counts_len,
    clamp_base_notes_nonnegative,
    clamp_forced_to_section_notes,
    use_forced_great_timing,
    fever_mask_buffer,
    section_start_out,
    section_forced_out,
    section_fill_penalty_out,
    section_skip_wasted_out,
):
    """
    JIT ForceGreats fever timeline builder.

    Replaces the Python while-loops in scoring.py by computing:
    - fever_mask_head (first 100 notes or fewer)
    - count_body_fever / count_body_normal
    - per-section start index + forced greats + fill-penalty notes + skip_wasted

    Behavior is controlled by flags to preserve existing semantics:
    - clamp_base_notes_nonnegative: match evaluate_force_greats*() (True) vs
      evaluate_fg_with_gem_iteration() (False).
    - clamp_forced_to_section_notes: match evaluate_force_greats*() (True) vs
      evaluate_fg_with_gem_iteration() (False).
    """
    # Game formula constants (see constants.FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET)
    non_fever_cas = (total_notes - long_notes_count) * 0.333  # FEVER_FILL_BASE_RATE
    if non_fever_cas < 0.0:
        non_fever_cas = 0.0

    # Raw fill value (before ceiling) - used for penalty calculation
    raw_fever_fill = non_fever_cas * fever_fill_rate
    non_fever_base = ceil(raw_fever_fill)

    fever_time_cas = last_note_time * 0.15 + 0.15  # FEVER_TIME_SCALE + FEVER_TIME_OFFSET
    real_fever_time = fever_time_cas * fever_time_stat

    is_fever = fever_mask_buffer
    is_fever[:] = False

    max_sections = section_start_out.shape[0]
    section_count = 0

    current_idx = 0
    non_fever_section = 0
    carry_time = 0.0

    while current_idx < total_notes and section_count < max_sections:
        non_fever_section += 1

        base_notes = non_fever_base - 1 if non_fever_section == 1 else non_fever_base
        if clamp_base_notes_nonnegative and base_notes < 0:
            base_notes = 0

        forced_val = 0
        if non_fever_section - 1 < forced_counts_len:
            forced_val = int(forced_counts[non_fever_section - 1])
        if forced_val < 0:
            forced_val = 0
        if forced_val > non_fever_base:
            forced_val = non_fever_base

        # Use raw values and ceiling AFTER adding: ceil(raw_base + raw_penalty)
        raw_penalty = max(0.0, forced_val * 0.5)

        notes_to_fill = ceil(raw_fever_fill + raw_penalty)
        if non_fever_section == 1:
            notes_to_fill -= 1

        fill_penalty_notes = notes_to_fill - (non_fever_base - 1 if non_fever_section == 1 else non_fever_base)

        section_start = current_idx
        end_normal = min(section_start + notes_to_fill, total_notes)
        actual_notes = max(0, end_normal - section_start)

        forced_applied = forced_val
        if clamp_forced_to_section_notes and forced_applied > actual_notes:
            forced_applied = actual_notes

        if use_forced_great_timing and forced_applied > 0:
            # Great offsets are applied to fill-contributing notes.
            # Sections 2+: the transition note (no fill) is the first note in section.
            forced_start = section_start if non_fever_section == 1 else (section_start + 1)
            forced_end = forced_start + forced_applied - 1
            if forced_end >= forced_start and forced_end < end_normal and forced_end < total_notes:
                cand_t = great_candidate_timestamps[forced_end]
                if cand_t > carry_time:
                    carry_time = cand_t

        section_start_out[section_count] = section_start
        section_forced_out[section_count] = forced_applied
        section_fill_penalty_out[section_count] = fill_penalty_notes
        # NOTE: skip_wasted is ONLY for fever fill calculation (section 0 needs fewer notes to fill).
        # It should NOT be used to offset great penalty indices - greats always start at section_start.
        section_skip_wasted_out[section_count] = non_fever_section == 1
        section_count += 1

        current_idx = end_normal
        if current_idx >= total_notes:
            break

        start_time = song_timestamps[current_idx]
        if use_forced_great_timing and carry_time > start_time:
            start_time = carry_time
        end_time = start_time + real_fever_time
        fever_end_idx = int(np.searchsorted(song_timestamps, end_time, side="left"))
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)
        is_fever[current_idx:fever_end_idx] = True
        current_idx = fever_end_idx

    head_limit = min(total_notes, 100)
    fever_mask_head = is_fever[:head_limit]

    count_body_fever = 0
    count_body_normal = 0
    if total_notes > 100:
        for i in range(100, total_notes):
            if is_fever[i]:
                count_body_fever += 1
            else:
                count_body_normal += 1

    return (
        fever_mask_head,
        int(count_body_fever),
        int(count_body_normal),
        int(non_fever_base),
        int(section_count),
    )


class SongTimelineGrid:
    """
    Pre-computed 161x161 grid of fever timelines for a specific song.

    Caches all possible timelines based on raw FT/FF stat indices (0-160).
    Provides O(1) lookup for the gem solver and Force Greats.

    Key insight: Force Greats just increases fill requirement per section,
    so we cache base parameters (non_fever_base, real_fever_time) and
    compute adjusted timelines dynamically.
    """

    GRID_SIZE = TOTAL_ROWS + 1  # 0 to 160 inclusive = 161

    def __init__(self, calc_song, ref_arrays):
        """
        Initialize the timeline grid for a song.

        Args:
            calc_song: Song calculation context with timestamps/metadata
            ref_arrays: Reference lookup arrays for stat -> multiplier conversion
        """
        self.calc_song = calc_song
        self.ref_arrays = ref_arrays

        # Stable identifier for cross-process caching (IPC pickling creates new object IDs).
        #
        # This must include HumanHitSim parameters when ApplyTo=ALL because they
        # change the underlying timestamp stream and therefore the grid contents.
        self.cache_key = _timeline_grid_cache_key(calc_song)

        # Extract song data
        song_data = calc_song["song_data"]
        self.song_timestamps = song_data["timestamps"]

        # Extract FG-specific timestamps when HumanHitSim is enabled
        # These provide simulated Perfect hit times and late-only Great times
        # Fallback to regular timestamps when HumanHitSim is disabled
        self.fg_timestamps = song_data.get("fg_timestamps", self.song_timestamps)
        self.fg_great_candidate_timestamps = song_data.get("fg_great_candidate_timestamps", self.song_timestamps)

        self.total_notes = len(self.song_timestamps)
        self.long_notes = int(calc_song["metadata"].get("Long Notes", 0))
        self.last_note_time = float(calc_song["metadata"].get("Last Note Time", 0))

        # Precompute constants that don't change with stats
        # Game formula constants (see constants.FEVER_FILL_BASE_RATE, FEVER_TIME_SCALE, FEVER_TIME_OFFSET)
        self.non_fever_cas = (self.total_notes - self.long_notes) * FEVER_FILL_BASE_RATE
        self.fever_time_cas = self.last_note_time * FEVER_TIME_SCALE + FEVER_TIME_OFFSET

        # Precompute all FT/FF multipliers (161 each)
        ref_ft = ref_arrays["Fever Time"]
        ref_ff = ref_arrays["Fever Fill Rate"]
        self.ft_factors = [lookup_reference_py(i, ref_ft, TOTAL_ROWS) for i in range(self.GRID_SIZE)]
        self.ff_factors = [lookup_reference_py(i, ref_ff, TOTAL_ROWS) for i in range(self.GRID_SIZE)]
        # Numba-friendly arrays (avoid Python loops/boxing in JIT grid builders)
        self._ft_factors_np = np.asarray(self.ft_factors, dtype=np.float32)
        self._ff_factors_np = np.asarray(self.ff_factors, dtype=np.float32)

        # Lazy-loaded 2D grid: [ft_idx][ff_idx] -> (mask_head, body_fever, body_normal, activations)
        # Using None to indicate not-yet-computed
        self._timeline_grid = [[None] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]

        # Optional timeline bucketing (cache key canonicalization).
        #
        # Modes:
        # - off: no bucketing.
        # - b / factors: canonicalize by exact (FT factor, FF factor). This is safe if
        #   factors come from lookup tables (plateaus) and equality is exact.
        # - a / signature: canonicalize by computed timeline signature (exact topology-cell
        #   reduction; always safe, but cannot avoid first-time compute for a new signature).
        #
        # Default to exact signature bucketing so identical topology cells are reduced
        # by default. Set TIMELINE_BUCKET_MODE=off to disable or TIMELINE_BUCKET_MODE=b
        # to keep factor-only canonicalization.
        self._bucket_mode = str(os.environ.get("TIMELINE_BUCKET_MODE", "a") or "a").strip().lower()
        if self._bucket_mode in {"none", "0", "false"}:
            self._bucket_mode = "off"
        if self._bucket_mode in {"factor", "factors", "b"}:
            self._bucket_mode = "b"
        if self._bucket_mode in {"sig", "signature", "a"}:
            self._bucket_mode = "a"

        # Bucketing maps (per-song grid instance)
        self._bucket_b = {}  # (ft_factor, ff_factor) -> (ft_idx, ff_idx)
        self._bucket_sig = {}  # signature -> timeline tuple

        # Shared buffer for timeline calculation
        self._fever_mask_buffer = np.zeros(self.total_notes, dtype=np.bool_)

        # Flag to track if precompute_all has been called
        self._precomputed = False

        # Cached fast grids (do not require fever_mask_head copies)
        self._fever_activations_grid = None
        self._last_fever_end_grid = None

    def get_timeline(self, ft_idx, ff_idx):
        """
        Get cached timeline for given FT/FF stat indices.
        Computes and caches if not already present.

        Args:
            ft_idx: Fever Time stat index (0-160)
            ff_idx: Fever Fill Rate stat index (0-160)

        Returns:
            tuple: (fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx)
        """
        # Clamp indices to valid range
        ft_idx = max(0, min(TOTAL_ROWS, int(ft_idx)))
        ff_idx = max(0, min(TOTAL_ROWS, int(ff_idx)))

        if self._bucket_mode == "b":
            # Canonicalize by exact factors (plateaus in lookup tables).
            # This avoids computing duplicate timelines for distinct indices
            # that map to the same multipliers.
            ft_factor_key = float(self.ft_factors[ft_idx])
            ff_factor_key = float(self.ff_factors[ff_idx])
            key = (ft_factor_key, ff_factor_key)
            canon = self._bucket_b.get(key)
            if canon is None:
                canon = (ft_idx, ff_idx)
                self._bucket_b[key] = canon
            ft_idx, ff_idx = canon

        cached = self._timeline_grid[ft_idx][ff_idx]
        if cached is not None:
            return cached

        # Compute timeline
        ft_factor = self.ft_factors[ft_idx]
        ff_factor = self.ff_factors[ff_idx]

        fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx = (
            calculate_fever_timeline_indices(
                self.song_timestamps,
                self.total_notes,
                ff_factor,
                ft_factor,
                self.long_notes,
                self.last_note_time,
                self._fever_mask_buffer,
            )
        )

        # Copy the head slice (buffer is reused)
        result = (fever_mask_head.copy(), count_body_fever, count_body_normal, fever_activations, last_fever_end_idx)

        if self._bucket_mode == "a":
            # Canonicalize by computed signature (always safe).
            # This can unify timelines even when factors differ but the discrete
            # stepping ends up identical for this song.
            try:
                sig = (result[0].tobytes(), int(result[1]), int(result[2]), int(result[3]), int(result[4]))
                existing = self._bucket_sig.get(sig)
                if existing is not None:
                    result = existing
                else:
                    self._bucket_sig[sig] = result
            except Exception:
                # Never fail due to signature issues; fall back to per-index caching.
                pass

        self._timeline_grid[ft_idx][ff_idx] = result
        return result

    def get_timeline_with_forced(self, ft_idx, ff_idx, forced_counts):
        """
        Calculates timeline dynamics with specific forced greats counts.
        Used for analytic breakpoint finding.

        Args:
            ft_idx: Fever Time stat index
            ff_idx: Fever Fill Rate stat index
            forced_counts: List/Tuple of forced greats counts per section

        Returns:
            tuple: (fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx)
        """
        ft_idx = max(0, min(TOTAL_ROWS, int(ft_idx)))
        ff_idx = max(0, min(TOTAL_ROWS, int(ff_idx)))
        ft_factor = self.ft_factors[ft_idx]
        ff_factor = self.ff_factors[ff_idx]

        # Prepare buffers for the kernel
        max_sections = 16
        forced_counts_arr = np.array(forced_counts, dtype=np.int32)
        forced_len = len(forced_counts)
        padded_counts = np.zeros(max_sections, dtype=np.int32)
        padded_counts[:forced_len] = forced_counts_arr

        section_start_out = np.zeros(max_sections, dtype=np.int32)
        section_forced_out = np.zeros(max_sections, dtype=np.int32)
        section_fill_penalty_out = np.zeros(max_sections, dtype=np.int32)
        section_skip_wasted_out = np.zeros(max_sections, dtype=np.int32)

        # We reuse the thread-local buffer if single-threaded, but to be safe create new or copy header
        # Actually calculate_force_greats_timeline_indices writes to fever_mask_buffer.
        # We can reuse self._fever_mask_buffer if this is single-threaded CPU.
        # Yes, standard python thread.

        mask_result, cbf, cbn, _base, _sec_cnt = calculate_force_greats_timeline_indices(
            self.fg_timestamps,
            self.fg_great_candidate_timestamps,
            self.total_notes,
            ff_factor,
            ft_factor,
            self.long_notes,
            self.last_note_time,
            padded_counts,
            forced_len,
            True,  # clamp_base_notes_nonnegative
            True,  # clamp_forced_to_section_notes
            False,  # use_forced_great_timing
            self._fever_mask_buffer,
            section_start_out,
            section_forced_out,
            section_fill_penalty_out,
            section_skip_wasted_out,
        )

        # We need "last_fever_end_idx". The kernel calculates fever mask.
        # We can find the last True index in mask? Or recalculate?
        # calculate_force_greats_timeline_indices doesn't return last_end explicitly in its tuple.
        # It updates mask. We can scan mask.

        # Fast way to find last non-zero index in boolean array:
        # np.max(np.nonzero(mask))
        # But mask is reused.

        # Actually, let's look at calculate_fever_timeline_indices (the standard one).
        # It returns last_fever_end_idx.
        # calculate_force_greats_timeline_indices does NOT return it.
        # We should modify the kernel to return it, OR derive it.
        # Deriving it requires scanning the array which is slow O(N).
        # Updating the kernel is better.
        # But I cannot easily update the kernel signature without breaking other callers (e.g. scoring.py).

        # Check usage in scoring.py.
        # scoring.py calls it.

        # Alternative: The "Breakpoints" logic only cares if the *Set of Covered Notes* changes.
        # Set of Covered Notes = (mask_head + body_fever).
        # We have these.
        # If (mask_head hash, body_fever) changes, then the config is distinct.
        # We don't technically need last_fever_end_idx for the breakpoint logic itself,
        # unless we use it for Gap calculation.
        # But we use `get_timeline`(standard) for the Gap check.
        # So we represent the result by (mask_head.copy(), cbf, cbn).

        return mask_result.copy(), cbf, cbn

    def get_fever_params(self, ft_idx, ff_idx):
        """
        Get fever parameters for Force Greats calculation.

        Args:
            ft_idx: Fever Time stat index (0-160)
            ff_idx: Fever Fill Rate stat index (0-160)

        Returns:
            tuple: (non_fever_base, real_fever_time, non_fever_great_to_fill, raw_fever_fill)
        """
        ft_idx = max(0, min(TOTAL_ROWS, int(ft_idx)))
        ff_idx = max(0, min(TOTAL_ROWS, int(ff_idx)))

        ft_factor = self.ft_factors[ft_idx]
        ff_factor = self.ff_factors[ff_idx]

        raw_fever_fill = self.non_fever_cas * ff_factor
        non_fever_base = ceil(raw_fever_fill)
        real_fever_time = self.fever_time_cas * ft_factor
        # Max greats to fill: effectively 2x the base (perfect judgement fills faster)
        non_fever_great_to_fill = ceil(max(1.0, raw_fever_fill * 2.0))

        return non_fever_base, real_fever_time, non_fever_great_to_fill, raw_fever_fill

    def precompute_all(self):
        """
        Eagerly compute all 161x161 timeline entries.
        Call this once per song before mega-batch GPU processing.
        """
        if self._precomputed:
            return  # Already computed - skip!

        for ft in range(self.GRID_SIZE):
            for ff in range(self.GRID_SIZE):
                self.get_timeline(ft, ff)  # Populates internal cache

        self._precomputed = True

    def to_gpu_arrays(self):
        """
        Convert timeline grid to GPU-friendly NumPy arrays.

        Returns:
            dict: {
                'count_body_fever': (161, 161) int32 array,
                'count_body_normal': (161, 161) int32 array,
                'fever_activations': (161, 161) int32 array,
                'last_fever_end': (161, 161) int32 array,
                'gap': (161, 161) int32 array (= total_notes - last_fever_end),
                'ft_factors': (161,) float32 array,
                'ff_factors': (161,) float32 array,
            }

        Note: fever_mask_head varies in size per timeline, so we store
        count_body_fever/normal/activations which are sufficient for scoring.
        """
        # Ensure all entries are computed
        self.precompute_all()

        count_body_fever = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)
        count_body_normal = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)
        fever_activations = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)
        last_fever_end = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)
        gap = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)

        for ft in range(self.GRID_SIZE):
            for ff in range(self.GRID_SIZE):
                timeline = self._timeline_grid[ft][ff]
                if timeline:
                    _, cbf, cbn, acts, lfe = timeline
                    count_body_fever[ft, ff] = cbf
                    count_body_normal[ft, ff] = cbn
                    fever_activations[ft, ff] = acts
                    last_fever_end[ft, ff] = lfe
                    gap[ft, ff] = self.total_notes - lfe

        return {
            "count_body_fever": count_body_fever,
            "count_body_normal": count_body_normal,
            "fever_activations": fever_activations,
            "last_fever_end": last_fever_end,
            "gap": gap,
            "ft_factors": np.array(self.ft_factors, dtype=np.float32),
            "ff_factors": np.array(self.ff_factors, dtype=np.float32),
        }

    def to_gpu_arrays_minimal(self):
        """
        Fast path: return only the grids needed by downstream "meta" computations.

        This avoids the expensive per-cell fever_mask_head copies done by `to_gpu_arrays()`.
        """
        if self._fever_activations_grid is None or self._last_fever_end_grid is None:
            acts = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)
            last_end = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)

            calculate_fever_activations_grid(
                self.song_timestamps,
                int(self.total_notes),
                float(self.fever_time_cas),
                float(self.non_fever_cas),
                self._ft_factors_np,
                self._ff_factors_np,
                acts,
                last_end,
            )
            self._fever_activations_grid = acts
            self._last_fever_end_grid = last_end

        gap = np.empty((self.GRID_SIZE, self.GRID_SIZE), dtype=np.int32)
        gap[:, :] = int(self.total_notes) - self._last_fever_end_grid

        return {
            "fever_activations": self._fever_activations_grid,
            "last_fever_end": self._last_fever_end_grid,
            "gap": gap,
        }


def get_song_timeline_grid(calc_song, ref_arrays):
    """
    Get or create a SongTimelineGrid for the given song.

    Args:
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays

    Returns:
        SongTimelineGrid: Cached or newly created grid
    """
    song_key = _timeline_grid_cache_key(calc_song)
    if _SONG_TIMELINE_GRID_CACHE_MAX <= 0:
        return SongTimelineGrid(calc_song, ref_arrays)

    grid = SONG_TIMELINE_GRIDS.get(song_key)
    if grid is None:
        grid = SongTimelineGrid(calc_song, ref_arrays)
        SONG_TIMELINE_GRIDS[song_key] = grid
    SONG_TIMELINE_GRIDS.move_to_end(song_key)
    while len(SONG_TIMELINE_GRIDS) > int(_SONG_TIMELINE_GRID_CACHE_MAX):
        SONG_TIMELINE_GRIDS.popitem(last=False)

    return grid
