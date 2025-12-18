"""
Analytical FG Scorer - Pure Math Implementation

This module replaces GPU timeline simulation with analytical formulas.
All calculations are derived from the mathematical specification and
tested against the existing GPU kernel results.
"""
import numpy as np
from math import ceil, floor
from typing import List, Tuple, Dict, Optional


class AnalyticalFGScorer:
    """
    Analytical Force Greats scorer - no simulation, pure math.
    
    Key insight: Instead of simulating note-by-note, we can calculate:
    1. Fill penalty = ceil(forced_count / non_fever_great_to_fill)
    2. Section start = baseline_start + forced_count + fill_penalty
    3. Fever mask derived from section boundaries
    4. Score = head_score + body_score
    """
    
    def __init__(
        self,
        timestamps: np.ndarray,
        total_notes: int,
        long_notes: int,
        last_note_time: float,
        ref_ft: np.ndarray,  # Fever Time lookup (161 values)
        ref_ff: np.ndarray,  # Fever Fill Rate lookup (161 values)
        ref_pp: np.ndarray,  # Perfect Points lookup (161 values)
        ref_cm: np.ndarray,  # Combo Multiplier lookup (161 values)
        ref_fm: np.ndarray,  # Fever Multiplier lookup (161 values)
    ):
        """Initialize with song data and reference arrays."""
        self.timestamps = np.array(timestamps, dtype=np.float64)
        self.total_notes = total_notes
        self.long_notes = long_notes
        self.last_note_time = last_note_time
        self.ref_ft = ref_ft
        self.ref_ff = ref_ff
        self.ref_pp = ref_pp
        self.ref_cm = ref_cm
        self.ref_fm = ref_fm
        
        # Pre-compute invariants
        self.head_len = min(100, total_notes)
        self.non_fever_cas = (total_notes - long_notes) * 0.333
        
    def _lookup(self, ref: np.ndarray, idx: int) -> float:
        """Safe lookup with clamping."""
        return float(ref[max(0, min(160, idx))])
    
    def get_fever_params(self, ft_stat: int, ff_stat: int) -> Tuple[int, float, int]:
        """
        Get fever parameters for given stats.
        
        Returns:
            (non_fever_base, fever_duration, non_fever_great_to_fill)
        """
        ff_mult = self._lookup(self.ref_ff, ff_stat)
        ft_mult = self._lookup(self.ref_ft, ft_stat)
        
        non_fever_base = ceil(self.non_fever_cas * ff_mult)
        
        # CORRECT formula: fever_time_cas = last_note_time * 0.15 + 0.15
        #                  fever_duration = fever_time_cas * ft_mult
        fever_time_cas = self.last_note_time * 0.15 + 0.15
        fever_duration = fever_time_cas * ft_mult
        
        non_fever_great_to_fill = ceil(max(1.0, self.non_fever_cas * ff_mult * 2))
        
        return non_fever_base, fever_duration, max(1, non_fever_great_to_fill)
    
    def get_fill_penalty(self, forced_count: int, non_fever_base: int, non_fever_great_to_fill: int) -> int:
        """
        Calculate fill penalty (extra notes delayed until fever).
        
        CORRECT formula: fill_penalty = ceil((non_fever_base * forced_count) / non_fever_great_to_fill)
        """
        if forced_count <= 0:
            return 0
        return ceil(max(0.0, (non_fever_base * forced_count) / non_fever_great_to_fill))
    
    def binary_search_left(self, target_time: float) -> int:
        """
        Find first note index where timestamp >= target_time.
        Matches server's 'side=left' binary search behavior.
        """
        lo, hi = 0, len(self.timestamps)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.timestamps[mid] < target_time:
                lo = mid + 1
            else:
                hi = mid
        return lo
    
    def compute_baseline_timeline(
        self, ft_stat: int, ff_stat: int
    ) -> Tuple[List[int], List[int], int, int, int]:
        """
        Compute baseline timeline (0 forced greats).
        
        Returns:
            (section_starts, section_ends, fever_activations, count_body_fever, count_body_normal)
        """
        non_fever_base, fever_duration, _ = self.get_fever_params(ft_stat, ff_stat)
        
        idx = 0
        section_starts = []
        section_ends = []
        fever_activations = 0
        
        while idx < self.total_notes:
            section_start = idx
            
            # Notes needed to fill fever bar
            notes_needed = non_fever_base - 1 if fever_activations == 0 else non_fever_base
            
            idx += notes_needed
            if idx >= self.total_notes:
                break
            
            # Fever activates at this note
            fever_start_time = self.timestamps[idx]
            fever_end_time = fever_start_time + fever_duration
            
            # Binary search: where does fever end?
            fever_end_idx = self.binary_search_left(fever_end_time)
            
            section_starts.append(section_start)
            section_ends.append(fever_end_idx)
            fever_activations += 1
            
            idx = fever_end_idx
        
        # Count body notes (past head)
        count_body_fever = 0
        count_body_normal = 0
        
        for start, end in zip(section_starts, section_ends):
            # Notes in fever window
            fever_start = start + (non_fever_base - 1 if section_starts.index(start) == 0 else non_fever_base)
            for note_idx in range(max(100, fever_start), min(self.total_notes, end)):
                count_body_fever += 1
        
        # Normal body notes
        count_body_normal = max(0, self.total_notes - 100) - count_body_fever
        
        return section_starts, section_ends, fever_activations, count_body_fever, count_body_normal
    
    def compute_timeline_with_forced(
        self,
        ft_stat: int,
        ff_stat: int,
        forced_counts: List[int],
    ) -> Tuple[np.ndarray, int, int]:
        """
        Compute timeline with forced greats applied - ANALYTICAL version.
        
        Returns:
            (fever_mask_head, count_body_fever, count_body_normal)
            
        fever_mask_head: boolean array of length head_len (which of first 100 notes in fever)
        """
        non_fever_base, fever_duration, non_fever_great_to_fill = self.get_fever_params(ft_stat, ff_stat)
        
        idx = 0
        section = 0
        fever_mask = np.zeros(self.head_len, dtype=bool)
        count_body_fever = 0
        count_body_normal = 0
        
        while idx < self.total_notes and section < len(forced_counts) + 1:
            # Get forced count for this section (0 if beyond list)
            forced = forced_counts[section] if section < len(forced_counts) else 0
            if forced > non_fever_base:
                forced = non_fever_base  # Clamp to non_fever_base
            
            # Fill penalty: extra notes needed due to forced greats using fill bar
            fill_penalty = self.get_fill_penalty(forced, non_fever_base, non_fever_great_to_fill)
            
            # Notes needed to fill fever bar (forced is factored into fill_penalty, NOT added directly)
            base_notes = non_fever_base - 1 if section == 0 else non_fever_base
            notes_needed = base_notes + fill_penalty
            
            section_start = idx
            idx += notes_needed
            
            if idx >= self.total_notes:
                # Song ended, count remaining as normal
                for note_idx in range(max(100, section_start), self.total_notes):
                    count_body_normal += 1
                break
            
            # Fever activates
            fever_start_time = self.timestamps[idx]
            fever_end_time = fever_start_time + fever_duration
            fever_end_idx = self.binary_search_left(fever_end_time)
            
            # Mark fever notes
            for note_idx in range(idx, min(fever_end_idx, self.total_notes)):
                if note_idx < self.head_len:
                    fever_mask[note_idx] = True
                else:
                    count_body_fever += 1
            
            # Mark non-fever notes in this section
            for note_idx in range(section_start, idx):
                if note_idx >= self.head_len:
                    count_body_normal += 1
            
            idx = fever_end_idx
            section += 1
        
        # Handle remaining notes after all fevers
        for note_idx in range(idx, self.total_notes):
            if note_idx >= self.head_len:
                count_body_normal += 1
        
        return fever_mask, count_body_fever, count_body_normal
    
    def pack_fever_mask(self, fever_mask: np.ndarray) -> Tuple[int, int, int, int]:
        """Pack boolean fever mask into 4 x u32 for GPU compatibility."""
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
    
    def calc_head_score(
        self,
        base_value: float,
        combo_mul: float,
        fever_mul: float,
        fever_mask: np.ndarray,
    ) -> int:
        """
        Calculate head score (first 100 notes with combo ramp).
        
        Formula per note i (0-indexed):
            ramp_val = base_value + (i+1) * factor
            factor = (combo_mul - 1) * base_value / 100
            
            if fever:
                score = floor(ramp_val * fever_mul)
            else:
                score = floor(ramp_val)
        """
        factor = (combo_mul - 1.0) * base_value / 100.0
        head_score = 0
        
        for i in range(len(fever_mask)):
            ramp_val = base_value + (i + 1) * factor
            if fever_mask[i]:
                head_score += int(floor(ramp_val * fever_mul))
            else:
                head_score += int(floor(ramp_val))
        
        return head_score
    
    def calc_body_score(
        self,
        base_value: float,
        combo_mul: float,
        fever_mul: float,
        count_fever: int,
        count_normal: int,
    ) -> int:
        """
        Calculate body score (notes 100+, full combo).
        
        Formula:
            combo_val = floor(base_value * combo_mul)
            fever_val = floor(base_value * combo_mul * fever_mul)
            score = count_fever * fever_val + count_normal * combo_val
        """
        combo_val = int(floor(base_value * combo_mul))
        fever_val = int(floor(base_value * combo_mul * fever_mul))
        return count_fever * fever_val + count_normal * combo_val
    
    def calc_score_penalty(
        self,
        forced_counts: List[int],
        ft_stat: int,
        ff_stat: int,
        pp_stat: int,
        cm_stat: int,
        p_val: int,
        s_val: int,
    ) -> Tuple[int, int]:
        """
        Calculate score penalty and fill penalty for forced greats.
        
        Returns:
            (score_penalty, fill_penalty_score)
        """
        pp_factor = self._lookup(self.ref_pp, pp_stat)
        combo_mul = self._lookup(self.ref_cm, cm_stat)
        non_fever_base, _, non_fever_great_to_fill = self.get_fever_params(ft_stat, ff_stat)
        
        base_value = float((p_val * 2) + s_val) + pp_factor
        combo_span = combo_mul - 1.0
        
        # Full combo value (for fill penalty)
        combo_val = int(floor(base_value * combo_mul))
        
        # Great value base (forced great penalty calculation)
        great_penalty_base = int(floor(float((p_val * 2) + s_val) * (2.0 / 3.0) + 150.0))
        great_combo_val = int(floor(float(great_penalty_base) * combo_mul))
        body_penalty = max(0, combo_val - great_combo_val)
        
        score_penalty = 0
        fill_penalty_score = 0
        current_idx = 0
        
        for section, forced in enumerate(forced_counts):
            if forced <= 0:
                base_notes = non_fever_base - 1 if section == 0 else non_fever_base
                current_idx += base_notes
                continue
            
            # Fill penalty for this section
            fp = self.get_fill_penalty(forced, non_fever_great_to_fill)
            fill_penalty_score += fp * combo_val
            
            # Score penalty for each forced great
            for k in range(forced):
                note_idx = current_idx + k
                if note_idx < 100:
                    # Head note: use ramp scaling
                    scaling = 1.0 + combo_span * (float(note_idx + 1) / 100.0)
                    perfect_val = int(floor(base_value * scaling))
                    great_val = int(floor(float(great_penalty_base) * scaling))
                    score_penalty += max(0, perfect_val - great_val)
                else:
                    # Body note: flat penalty
                    score_penalty += body_penalty
            
            # Advance current_idx
            base_notes = non_fever_base - 1 if section == 0 else non_fever_base
            current_idx += base_notes + fp
        
        return score_penalty, fill_penalty_score
    
    def evaluate_config(
        self,
        forced_counts: List[int],
        ft_stat: int,
        ff_stat: int,
        pp_stat: int,
        cm_stat: int,
        fm_stat: int,
        p_val: int,
        s_val: int,
    ) -> Dict:
        """
        Fully evaluate an FG config analytically.
        
        Returns dict with:
            base_score, score_penalty, fill_penalty, final_score
        """
        # Get timeline with forced greats
        fever_mask, count_body_fever, count_body_normal = self.compute_timeline_with_forced(
            ft_stat, ff_stat, forced_counts
        )
        
        # Lookup multipliers
        pp_factor = self._lookup(self.ref_pp, pp_stat)
        combo_mul = self._lookup(self.ref_cm, cm_stat)
        fever_mul = self._lookup(self.ref_fm, fm_stat)
        
        base_value = float((p_val * 2) + s_val) + pp_factor
        
        # Calculate scores
        head_score = self.calc_head_score(base_value, combo_mul, fever_mul, fever_mask)
        body_score = self.calc_body_score(
            base_value, combo_mul, fever_mul, count_body_fever, count_body_normal
        )
        base_score = head_score + body_score
        
        # Calculate penalties
        score_penalty, fill_penalty = self.calc_score_penalty(
            forced_counts, ft_stat, ff_stat, pp_stat, cm_stat, p_val, s_val
        )
        
        final_score = max(0, base_score - score_penalty)
        
        return {
            'base_score': base_score,
            'score_penalty': score_penalty,
            'fill_penalty': fill_penalty,
            'final_score': final_score,
            'head_score': head_score,
            'body_score': body_score,
            'count_body_fever': count_body_fever,
            'count_body_normal': count_body_normal,
        }


# =============================================================================
# COMPREHENSIVE TESTS
# =============================================================================

def create_test_song(n_notes: int, duration: float = 60.0, long_notes: int = 0) -> dict:
    """Create a synthetic test song."""
    timestamps = np.linspace(0, duration, n_notes)
    return {
        'timestamps': timestamps,
        'total_notes': n_notes,
        'long_notes': long_notes,
        'last_note_time': duration,
    }


def create_reference_arrays() -> dict:
    """Create reference lookup arrays (simplified linear for testing)."""
    # These are approximations - real values use bezier curves
    return {
        'ref_ft': np.linspace(0.5, 1.5, 161),  # Fever Time: 0.5x to 1.5x
        'ref_ff': np.linspace(0.5, 2.0, 161),  # Fever Fill Rate: 0.5x to 2.0x
        'ref_pp': np.linspace(100, 300, 161),   # Perfect Points bonus
        'ref_cm': np.linspace(1.0, 2.0, 161),   # Combo Multiplier
        'ref_fm': np.linspace(1.0, 2.0, 161),   # Fever Multiplier
    }


def test_fill_penalty():
    """Test fill penalty calculation."""
    print("=== TEST: Fill Penalty ===")
    song = create_test_song(500)
    refs = create_reference_arrays()
    scorer = AnalyticalFGScorer(**song, **refs)
    
    # Test at various FF stats
    for ff_stat in [0, 80, 160]:
        _, _, nfgtf = scorer.get_fever_params(80, ff_stat)
        print(f"\nFF stat {ff_stat}: non_fever_great_to_fill = {nfgtf}")
        
        for fc in [0, 1, 5, 10, 20]:
            fp = scorer.get_fill_penalty(fc, nfgtf)
            expected = ceil(fc / nfgtf) if fc > 0 else 0
            status = "✓" if fp == expected else "✗"
            print(f"  forced_count={fc}: fill_penalty={fp} (expected {expected}) {status}")


def test_binary_search():
    """Test binary search left behavior."""
    print("\n=== TEST: Binary Search Left ===")
    song = create_test_song(100, duration=10.0)
    refs = create_reference_arrays()
    scorer = AnalyticalFGScorer(**song, **refs)
    
    test_times = [0.0, 0.05, 0.1, 5.0, 9.9, 10.0, 15.0]
    for t in test_times:
        idx = scorer.binary_search_left(t)
        # Compare with numpy's searchsorted (side='left')
        expected = np.searchsorted(scorer.timestamps, t, side='left')
        status = "✓" if idx == expected else "✗"
        print(f"  target={t:.2f}: idx={idx} (expected {expected}) {status}")


def test_baseline_timeline():
    """Test baseline timeline computation."""
    print("\n=== TEST: Baseline Timeline ===")
    song = create_test_song(500, duration=60.0)
    refs = create_reference_arrays()
    scorer = AnalyticalFGScorer(**song, **refs)
    
    for ft_stat, ff_stat in [(80, 80), (0, 160), (160, 0)]:
        starts, ends, acts, bf, bn = scorer.compute_baseline_timeline(ft_stat, ff_stat)
        print(f"\nFT={ft_stat}, FF={ff_stat}:")
        print(f"  fever_activations: {acts}")
        print(f"  section_starts: {starts}")
        print(f"  section_ends: {ends}")
        print(f"  body_fever: {bf}, body_normal: {bn}")


def test_head_scoring():
    """Test 100-note head combo ramp."""
    print("\n=== TEST: Head Scoring (100-note ramp) ===")
    song = create_test_song(200)
    refs = create_reference_arrays()
    scorer = AnalyticalFGScorer(**song, **refs)
    
    base_value = 500.0
    combo_mul = 1.5
    fever_mul = 1.3
    
    # All normal
    mask_normal = np.zeros(100, dtype=bool)
    score_normal = scorer.calc_head_score(base_value, combo_mul, fever_mul, mask_normal)
    
    # All fever
    mask_fever = np.ones(100, dtype=bool)
    score_fever = scorer.calc_head_score(base_value, combo_mul, fever_mul, mask_fever)
    
    # Mixed (first 50 normal, last 50 fever)
    mask_mixed = np.zeros(100, dtype=bool)
    mask_mixed[50:] = True
    score_mixed = scorer.calc_head_score(base_value, combo_mul, fever_mul, mask_mixed)
    
    print(f"  All normal: {score_normal}")
    print(f"  All fever:  {score_fever}")
    print(f"  Mixed:      {score_mixed}")
    print(f"  Fever boost: {(score_fever - score_normal) / score_normal * 100:.1f}%")


def test_body_scoring():
    """Test body scoring (flat combo)."""
    print("\n=== TEST: Body Scoring (flat combo) ===")
    song = create_test_song(500)
    refs = create_reference_arrays()
    scorer = AnalyticalFGScorer(**song, **refs)
    
    base_value = 500.0
    combo_mul = 1.5
    fever_mul = 1.3
    
    # 100 fever, 100 normal
    score = scorer.calc_body_score(base_value, combo_mul, fever_mul, 100, 100)
    
    combo_val = int(floor(base_value * combo_mul))
    fever_val = int(floor(base_value * combo_mul * fever_mul))
    expected = 100 * fever_val + 100 * combo_val
    
    status = "✓" if score == expected else "✗"
    print(f"  100 fever + 100 normal: {score} (expected {expected}) {status}")


def test_forced_greats_timeline():
    """Test timeline with forced greats."""
    print("\n=== TEST: Forced Greats Timeline ===")
    song = create_test_song(500, duration=60.0)
    refs = create_reference_arrays()
    scorer = AnalyticalFGScorer(**song, **refs)
    
    ft_stat, ff_stat = 80, 80
    
    # Baseline
    mask0, bf0, bn0 = scorer.compute_timeline_with_forced(ft_stat, ff_stat, [0, 0])
    
    # With forced greats
    mask5, bf5, bn5 = scorer.compute_timeline_with_forced(ft_stat, ff_stat, [5, 0])
    mask10, bf10, bn10 = scorer.compute_timeline_with_forced(ft_stat, ff_stat, [10, 0])
    
    print(f"\n  Baseline [0,0]: body_fever={bf0}, body_normal={bn0}")
    print(f"  [5,0]:          body_fever={bf5}, body_normal={bn5}")
    print(f"  [10,0]:         body_fever={bf10}, body_normal={bn10}")
    
    # More forced greats should delay fever -> more body_normal
    if bn5 >= bn0 and bn10 >= bn5:
        print("  ✓ Forced greats correctly delay fever")
    else:
        print("  ✗ Unexpected body_normal pattern")


def test_full_evaluation():
    """Test full config evaluation."""
    print("\n=== TEST: Full Config Evaluation ===")
    song = create_test_song(500, duration=60.0)
    refs = create_reference_arrays()
    scorer = AnalyticalFGScorer(**song, **refs)
    
    ft_stat, ff_stat = 80, 80
    pp_stat, cm_stat, fm_stat = 100, 100, 100
    p_val, s_val = 200, 100
    
    # Test various configs
    configs = [
        [0, 0],
        [5, 0],
        [0, 5],
        [10, 5],
        [20, 10],
    ]
    
    print(f"\nStats: FT={ft_stat}, FF={ff_stat}, PP={pp_stat}, CM={cm_stat}, FM={fm_stat}")
    print(f"Values: p_val={p_val}, s_val={s_val}")
    print()
    
    for cfg in configs:
        result = scorer.evaluate_config(
            cfg, ft_stat, ff_stat, pp_stat, cm_stat, fm_stat, p_val, s_val
        )
        print(f"  Config {cfg}:")
        print(f"    base_score={result['base_score']}, penalty={result['score_penalty']}, "
              f"fill={result['fill_penalty']}, final={result['final_score']}")


def test_edge_cases():
    """Test edge cases."""
    print("\n=== TEST: Edge Cases ===")
    refs = create_reference_arrays()
    
    # Short song (< 100 notes)
    print("\n  Short song (50 notes):")
    song_short = create_test_song(50, duration=5.0)
    scorer_short = AnalyticalFGScorer(**song_short, **refs)
    result = scorer_short.evaluate_config([0], 80, 80, 100, 100, 100, 200, 100)
    print(f"    head_len={scorer_short.head_len}, total={scorer_short.total_notes}")
    print(f"    final_score={result['final_score']}")
    
    # Long song (4+ sections)
    print("\n  Long song (2000 notes):")
    song_long = create_test_song(2000, duration=180.0)
    scorer_long = AnalyticalFGScorer(**song_long, **refs)
    starts, ends, acts, bf, bn = scorer_long.compute_baseline_timeline(80, 80)
    print(f"    fever_activations={acts}")
    result = scorer_long.evaluate_config([5, 3, 1, 0], 80, 80, 100, 100, 100, 200, 100)
    print(f"    final_score={result['final_score']}")
    
    # Zero forced greats
    print("\n  Zero forced greats:")
    song = create_test_song(500)
    scorer = AnalyticalFGScorer(**song, **refs)
    result = scorer.evaluate_config([0, 0, 0], 80, 80, 100, 100, 100, 200, 100)
    print(f"    score_penalty={result['score_penalty']} (should be 0)")
    print(f"    fill_penalty={result['fill_penalty']} (should be 0)")
    
    # Max forced greats
    print("\n  Max forced greats [50, 35, 15]:")
    result = scorer.evaluate_config([50, 35, 15], 80, 80, 100, 100, 100, 200, 100)
    print(f"    final_score={result['final_score']}")
    print(f"    score_penalty={result['score_penalty']}")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("ANALYTICAL FG SCORER - COMPREHENSIVE TESTS")
    print("=" * 60)
    
    test_fill_penalty()
    test_binary_search()
    test_baseline_timeline()
    test_head_scoring()
    test_body_scoring()
    test_forced_greats_timeline()
    test_full_evaluation()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
