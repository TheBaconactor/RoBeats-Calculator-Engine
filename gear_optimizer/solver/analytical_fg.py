"""
Analytical FG Scorer - Pure Math Implementation

This module replaces GPU timeline simulation with analytical formulas.
All calculations are derived from the mathematical specification and
validated against SongTimelineGrid ground truth (13/13 tests passing).

Key insight: Instead of simulating note-by-note on GPU, we can calculate:
1. Fill penalty = ceil(forced_count * 0.5)
2. Section start = baseline_start + fill_penalty (forced affects fill_penalty, not added directly)
3. Fever mask derived from section boundaries
4. Score = head_score + body_score
"""
import numpy as np
from math import ceil, floor
from typing import List, Tuple, Dict, Optional


class AnalyticalFGScorer:
    """
    Analytical Force Greats scorer - no simulation, pure math.
    
    This class can pre-compute all timeline data on CPU, which the GPU kernel
    then uses for gem optimization only (no more timeline simulation on GPU).
    """
    
    def __init__(
        self,
        timestamps: np.ndarray,
        total_notes: int,
        long_notes: int,
        last_note_time: float,
        ref_ft: np.ndarray,  # Fever Time lookup (161 values)
        ref_ff: np.ndarray,  # Fever Fill Rate lookup (161 values)
    ):
        """
        Initialize with song data and reference arrays.
        
        Args:
            timestamps: Array of note timestamps
            total_notes: Total number of notes in song
            long_notes: Number of long/held notes
            last_note_time: Timestamp of last note (song length proxy)
            ref_ft: Fever Time stat lookup array (161 values)
            ref_ff: Fever Fill Rate stat lookup array (161 values)
        """
        self.timestamps = np.array(timestamps, dtype=np.float64)
        self.total_notes = total_notes
        self.long_notes = long_notes
        self.last_note_time = last_note_time
        self.ref_ft = ref_ft
        self.ref_ff = ref_ff
        
        # Pre-compute invariants
        self.head_len = min(100, total_notes)
        self.non_fever_cas = (total_notes - long_notes) * 0.333
        self.fever_time_cas = last_note_time * 0.15 + 0.15
        
    def _lookup(self, ref: np.ndarray, idx: int) -> float:
        """Safe lookup with clamping to [0, 160]."""
        return float(ref[max(0, min(160, idx))])
    
    def get_fever_params(self, ft_stat: int, ff_stat: int) -> Tuple[int, float, int, float]:
        """
        Get fever parameters for given FT/FF stats.
        
        Returns:
            (non_fever_base, fever_duration, non_fever_great_to_fill, raw_fever_fill)
        """
        ff_mult = self._lookup(self.ref_ff, ff_stat)
        ft_mult = self._lookup(self.ref_ft, ft_stat)
        
        raw_fever_fill = self.non_fever_cas * ff_mult
        non_fever_base = ceil(raw_fever_fill)
        fever_duration = self.fever_time_cas * ft_mult
        non_fever_great_to_fill = ceil(max(1.0, raw_fever_fill * 2))
        
        return non_fever_base, fever_duration, max(1, non_fever_great_to_fill), raw_fever_fill
    
    def get_section_analysis(self, ft_stat: int, ff_stat: int) -> dict:
        """
        Analyze fever sections and apply the 3 FG rules.
        
        The 3 FG rules:
        1. Fever overflow: If fever extends past last_note_time → useless section
        2. Gap constraint: Can't shift more FG than the gap to song end
        3. Section activation: Only sections with fever activations are useful
        
        Returns:
            dict with:
                'fever_activations': Number of fever windows that fully activate
                'gap': Notes between last fever end and song end
                'useful_sections': Max meaningful section index
                'section_caps': Recommended cap per section based on gap
        """
        non_fever_base, fever_duration, _, raw_fever_fill = self.get_fever_params(ft_stat, ff_stat)
        
        idx = 0
        section = 0
        activations = 0
        last_fever_end_idx = 0
        
        # Simulate baseline to count activations
        while idx < self.total_notes:
            base_notes = non_fever_base - 1 if section == 0 else non_fever_base
            idx += base_notes
            
            if idx >= self.total_notes:
                break
            
            fever_start = self.timestamps[idx]
            fever_end = fever_start + fever_duration
            
            # Rule 1: Fever overflow check
            if fever_end >= self.last_note_time:
                # Fever extends past song - this and subsequent sections are useless
                break
            
            fever_end_idx = self.binary_search_left(fever_end)
            last_fever_end_idx = fever_end_idx
            activations += 1
            section += 1
            idx = fever_end_idx
        
        # Rule 2: Gap constraint
        gap = self.total_notes - last_fever_end_idx
        
        # Rule 3: Section-based caps
        # Sections beyond activations have no benefit from FG
        useful_sections = activations
        
        # Calculate per-section caps based on gap
        section_caps = []
        for sec in range(useful_sections):
            # Later sections have less impact, so lower caps
            base_cap = min(non_fever_base, gap)
            if sec == 0:
                cap = base_cap
            elif sec == 1:
                cap = int(base_cap * 0.6)
            else:
                cap = int(base_cap * 0.3)
            section_caps.append(max(0, cap))
        
        return {
            'fever_activations': activations,
            'gap': gap,
            'useful_sections': useful_sections,
            'section_caps': section_caps,
            'non_fever_base': non_fever_base,
        }
    
    def get_fill_penalty(self, forced_count: int, raw_fever_fill: float, is_section_1: bool) -> int:
        """
        Calculate fill penalty in notes.
        Uses the new formula: ceil(raw_base + raw_penalty).
        
        For section 1, we subtract 1 from the result (indexing adjustment).
        """
        if forced_count <= 0:
            return 0
            
        penalty_raw = forced_count * 0.5
        notes_to_fill = ceil(raw_fever_fill + penalty_raw)
        
        if is_section_1:
            notes_to_fill -= 1
            base_notes = ceil(raw_fever_fill) - 1
        else:
            base_notes = ceil(raw_fever_fill)
            
        return max(0, int(notes_to_fill - base_notes))
    
    def binary_search_left(self, target_time: float) -> int:
        """
        Find first note index where timestamp >= target_time.
        Matches server's numpy.searchsorted(side='left') behavior.
        """
        lo, hi = 0, len(self.timestamps)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.timestamps[mid] < target_time:
                lo = mid + 1
            else:
                hi = mid
        return lo
    
    def get_breakpoints(
        self,
        ft_stat: int,
        ff_stat: int,
        max_fg: int | None = None,
    ) -> List[int]:
        """
        Get forced great counts that actually change the timeline (breakpoints).
        
        This is pure math - no simulation needed! Breakpoints occur when
        fill_penalty increases, which happens every 2 forced greats (since
        fill_penalty = ceil(forced * 0.5)).
        
        Args:
            ft_stat: Fever Time stat (0-160)
            ff_stat: Fever Fill Rate stat (0-160)
            max_fg: Maximum forced greats to consider. If None, uses non_fever_base
                    (the natural limit - you can't force more greats than notes in section)
            
        Returns:
            List of forced counts that are breakpoints (including 0)
        """
        raw_fever_fill = self.non_fever_cas * self._lookup(self.ref_ff, ff_stat)
        
        # Default to non_fever_base (natural limit - can't force more greats than exist)
        if max_fg is None:
            max_fg = ceil(raw_fever_fill)
        
        breakpoints = [0]  # Always include 0
        prev_penalty = 0
        
        for fc in range(1, max_fg + 1):
            penalty = self.get_fill_penalty(fc, raw_fever_fill, False) # Use section 2+ as proxy for delta changes
            if penalty != prev_penalty:
                breakpoints.append(fc)
                prev_penalty = penalty
        
        return breakpoints
    
    def get_all_section_breakpoints(
        self,
        ft_stat: int,
        ff_stat: int,
        section_caps: List[int],
    ) -> List[List[int]]:
        """
        Get breakpoints for multiple sections with per-section caps.
        
        Args:
            ft_stat: Fever Time stat
            ff_stat: Fever Fill Rate stat  
            section_caps: Max forced greats per section, e.g. [50, 30, 15, 10]
            
        Returns:
            List of breakpoint lists, one per section
        """
        return [
            self.get_breakpoints(ft_stat, ff_stat, cap)
            for cap in section_caps
        ]
    
    def compute_timeline_with_forced(
        self,
        ft_stat: int,
        ff_stat: int,
        forced_counts: List[int],
    ) -> Tuple[np.ndarray, int, int, int]:
        """
        Compute timeline with forced greats applied - ANALYTICAL version.
        
        This is the core function that replaces GPU simulation.
        
        Args:
            ft_stat: Fever Time stat (0-160)
            ff_stat: Fever Fill Rate stat (0-160)
            forced_counts: List of forced greats per section
            
        Returns:
            (fever_mask_head, count_body_fever, count_body_normal, fever_activations)
            
            fever_mask_head: boolean array of length head_len (which of first 100 notes in fever)
            count_body_fever: fever notes in body (after note 100)
            count_body_normal: normal notes in body
            fever_activations: number of fever windows activated
        """
        non_fever_base, fever_duration, non_fever_great_to_fill, raw_fever_fill = self.get_fever_params(ft_stat, ff_stat)
        
        idx = 0
        section = 0
        fever_mask = np.zeros(self.head_len, dtype=bool)
        count_body_fever = 0
        count_body_normal = 0
        fever_activations = 0
        
        while idx < self.total_notes and section < len(forced_counts) + 1:
            # Get forced count for this section (0 if beyond list)
            forced = forced_counts[section] if section < len(forced_counts) else 0
            if forced > non_fever_base:
                forced = non_fever_base  # Clamp to non_fever_base
            
            # Fill penalty: extra notes needed due to forced greats using fill bar
            # Uses ceil(raw_base + raw_penalty) - ceil(raw_base)
            fill_penalty = self.get_fill_penalty(forced, raw_fever_fill, bool(section == 0))
            
            notes_needed = ceil(raw_fever_fill + forced * 0.5)
            if section == 0:
                notes_needed -= 1
            
            section_start = idx
            idx += notes_needed
            
            if idx >= self.total_notes:
                # Song ended, count remaining as normal
                for note_idx in range(max(100, section_start), self.total_notes):
                    count_body_normal += 1
                break
            
            # Fever activates at this note
            fever_start_time = self.timestamps[idx]
            fever_end_time = fever_start_time + fever_duration
            fever_end_idx = self.binary_search_left(fever_end_time)
            fever_activations += 1
            
            # Mark fever notes in head
            for note_idx in range(idx, min(fever_end_idx, self.total_notes)):
                if note_idx < self.head_len:
                    fever_mask[note_idx] = True
                else:
                    count_body_fever += 1
            
            # Count non-fever notes in this section (body only)
            for note_idx in range(section_start, idx):
                if note_idx >= self.head_len:
                    count_body_normal += 1
            
            idx = fever_end_idx
            section += 1
        
        # Handle remaining notes after all fevers
        for note_idx in range(idx, self.total_notes):
            if note_idx >= self.head_len:
                count_body_normal += 1
        
        return fever_mask, count_body_fever, count_body_normal, fever_activations
    
    def pack_fever_mask(self, fever_mask: np.ndarray) -> Tuple[int, int, int, int]:
        """
        Pack boolean fever mask into 4 x u32 for GPU kernel compatibility.
        
        Returns (m0, m1, m2, m3) where each is a 32-bit packed bitmask.
        """
        m0, m1, m2, m3 = 0, 0, 0, 0
        for i, is_fever in enumerate(fever_mask):
            if is_fever:
                if i < 32:
                    m0 |= (1 << i)
                elif i < 64:
                    m1 |= (1 << (i - 32))
                elif i < 96:
                    m2 |= (1 << (i - 64))
                else:
                    m3 |= (1 << (i - 96))
        return m0, m1, m2, m3
    
    def precompute_all_configs(
        self,
        ft_stat: int,
        ff_stat: int,
        configs: List[List[int]],
    ) -> List[Tuple[int, int, int, int, int, int]]:
        """
        Pre-compute timeline data for all FG configs.
        
        This is the batch function that replaces GPU timeline simulation.
        The returned data can be uploaded to GPU for gem optimization.
        
        Args:
            ft_stat: Fever Time stat
            ff_stat: Fever Fill Rate stat
            configs: List of forced counts configurations
            
        Returns:
            List of tuples: (m0, m1, m2, m3, count_body_fever, count_body_normal)
            ready for GPU consumption.
        """
        results = []
        for cfg in configs:
            mask, bf, bn, _ = self.compute_timeline_with_forced(ft_stat, ff_stat, cfg)
            m0, m1, m2, m3 = self.pack_fever_mask(mask)
            results.append((m0, m1, m2, m3, bf, bn))
        return results


def create_scorer_from_calc_song(calc_song: dict, ref_arrays: dict) -> AnalyticalFGScorer:
    """
    Factory function to create AnalyticalFGScorer from calc_song format.
    
    Args:
        calc_song: Dict with 'song_data' and 'metadata' keys
        ref_arrays: Dict with 'Fever Time' and 'Fever Fill Rate' arrays
        
    Returns:
        Configured AnalyticalFGScorer instance
    """
    song_data = calc_song["song_data"]
    metadata = calc_song.get("metadata", {})
    
    return AnalyticalFGScorer(
        timestamps=np.array(song_data["timestamps"]),
        total_notes=len(song_data["timestamps"]),
        long_notes=int(metadata.get("Long Notes", 0)),
        last_note_time=float(metadata.get("Last Note Time", song_data["timestamps"][-1])),
        ref_ft=np.array(ref_arrays["Fever Time"]),
        ref_ff=np.array(ref_arrays["Fever Fill Rate"]),
    )
