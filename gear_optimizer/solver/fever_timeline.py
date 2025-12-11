"""
Fever timeline calculation and caching.

This module contains the "Rules Layer" - the complex fever timeline logic
that determines when fever starts/ends based on stats. This logic stays
on CPU and is NOT ported to GPU.
"""
import numpy as np
from math import ceil

from ..core.jit_setup import jit
from ..core.constants import TOTAL_ROWS


# Global cache for SongTimelineGrid instances (one per song)
SONG_TIMELINE_GRIDS = {}


def lookup_reference_py(value, ref_array, total_rows=TOTAL_ROWS):
    """
    Python implementation of reference lookup.
    Clamps value to valid range and returns corresponding reference value.
    """
    clamped = max(0, min(total_rows, int(value)))
    return ref_array[clamped]


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
        tuple: (fever_mask_head, count_body_fever, count_body_normal, fever_activations)
    """
    non_fever_cas = (total_notes - long_notes_count) * 0.333
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    fever_time_cas = last_note_time * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_stat

    is_fever = fever_mask_buffer
    is_fever[:] = False
    current_note_idx = 0
    fever_activations = 0
    fever_section = 0

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
    return fever_mask_head, count_body_fever, count_body_normal, fever_activations


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
        
        # Extract song data
        self.song_timestamps = calc_song["song_data"]["timestamps"]
        self.total_notes = len(self.song_timestamps)
        self.long_notes = int(calc_song["metadata"].get("Long Notes", 0))
        self.last_note_time = float(calc_song["metadata"].get("Last Note Time", 0))
        
        # Precompute constants that don't change with stats
        self.non_fever_cas = (self.total_notes - self.long_notes) * 0.333
        self.fever_time_cas = self.last_note_time * 0.15 + 0.15
        
        # Precompute all FT/FF multipliers (161 each)
        ref_ft = ref_arrays["Fever Time"]
        ref_ff = ref_arrays["Fever Fill Rate"]
        self.ft_factors = [lookup_reference_py(i, ref_ft, TOTAL_ROWS) for i in range(self.GRID_SIZE)]
        self.ff_factors = [lookup_reference_py(i, ref_ff, TOTAL_ROWS) for i in range(self.GRID_SIZE)]
        
        # Lazy-loaded 2D grid: [ft_idx][ff_idx] -> (mask_head, body_fever, body_normal, activations)
        # Using None to indicate not-yet-computed
        self._timeline_grid = [[None] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]
        
        # Shared buffer for timeline calculation
        self._fever_mask_buffer = np.zeros(self.total_notes, dtype=np.bool_)
        
        # Flag to track if precompute_all has been called
        self._precomputed = False
    
    def get_timeline(self, ft_idx, ff_idx):
        """
        Get cached timeline for given FT/FF stat indices.
        Computes and caches if not already present.
        
        Args:
            ft_idx: Fever Time stat index (0-160)
            ff_idx: Fever Fill Rate stat index (0-160)
            
        Returns:
            tuple: (fever_mask_head, count_body_fever, count_body_normal, fever_activations)
        """
        # Clamp indices to valid range
        ft_idx = max(0, min(TOTAL_ROWS, int(ft_idx)))
        ff_idx = max(0, min(TOTAL_ROWS, int(ff_idx)))
        
        cached = self._timeline_grid[ft_idx][ff_idx]
        if cached is not None:
            return cached
        
        # Compute timeline
        ft_factor = self.ft_factors[ft_idx]
        ff_factor = self.ff_factors[ff_idx]
        
        fever_mask_head, count_body_fever, count_body_normal, fever_activations = calculate_fever_timeline_indices(
            self.song_timestamps,
            self.total_notes,
            ff_factor,
            ft_factor,
            self.long_notes,
            self.last_note_time,
            self._fever_mask_buffer,
        )
        
        # Copy the head slice (buffer is reused)
        result = (fever_mask_head.copy(), count_body_fever, count_body_normal, fever_activations)
        self._timeline_grid[ft_idx][ff_idx] = result
        return result
    
    def get_fever_params(self, ft_idx, ff_idx):
        """
        Get fever parameters for Force Greats calculation.
        
        Args:
            ft_idx: Fever Time stat index (0-160)
            ff_idx: Fever Fill Rate stat index (0-160)
            
        Returns:
            tuple: (non_fever_base, real_fever_time, non_fever_great_to_fill)
        """
        ft_idx = max(0, min(TOTAL_ROWS, int(ft_idx)))
        ff_idx = max(0, min(TOTAL_ROWS, int(ff_idx)))
        
        ft_factor = self.ft_factors[ft_idx]
        ff_factor = self.ff_factors[ff_idx]
        
        non_fever_base = ceil(self.non_fever_cas * ff_factor)
        real_fever_time = self.fever_time_cas * ft_factor
        # Max greats to fill: effectively 2x the base (perfect judgement fills faster)
        non_fever_great_to_fill = ceil(max(1.0, self.non_fever_cas * ff_factor * 2.0))
        
        return non_fever_base, real_fever_time, non_fever_great_to_fill
    
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
        
        for ft in range(self.GRID_SIZE):
            for ff in range(self.GRID_SIZE):
                timeline = self._timeline_grid[ft][ff]
                if timeline:
                    _, cbf, cbn, acts = timeline
                    count_body_fever[ft, ff] = cbf
                    count_body_normal[ft, ff] = cbn
                    fever_activations[ft, ff] = acts
        
        return {
            'count_body_fever': count_body_fever,
            'count_body_normal': count_body_normal,
            'fever_activations': fever_activations,
            'ft_factors': np.array(self.ft_factors, dtype=np.float32),
            'ff_factors': np.array(self.ff_factors, dtype=np.float32),
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
    # Use song name + note count as cache key
    song_key = (
        calc_song["metadata"].get("Song Name", ""),
        len(calc_song["song_data"]["timestamps"]),
    )
    
    if song_key not in SONG_TIMELINE_GRIDS:
        SONG_TIMELINE_GRIDS[song_key] = SongTimelineGrid(calc_song, ref_arrays)
    
    return SONG_TIMELINE_GRIDS[song_key]
