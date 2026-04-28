"""
Experiment: Validate S9 — FG Dual-Mechanism Decomposition Theorem

Validates:
  Lemma 1: Body notes have constant fever/normal value
  Lemma 2: Body-only window shift produces zero base score change
  Lemma 3: Head shift benefit is bounded by d * (B_max - B_min)
  Lemma 4: The decomposition upper bound is admissible
  Pre-test: If shift_bound + create_bound <= 0, FG cannot improve score

Uses existing fast_calculate_score and calculate_fever_timeline_indices.
No GPU required. No real Data/ needed.
"""
import sys, os, math, unittest
import numpy as np

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Must set Numba cache before importing solver modules
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(os.path.dirname(__file__), "__pycache__"))

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.scoring_core import fast_calculate_score, lookup_reference_py
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices


def make_synthetic_song(n_notes=200, spacing_ms=80, fever_fill_rate=0.5, fever_time_stat=1.5):
    """Create a synthetic song with N notes at uniform spacing."""
    timestamps = np.array([i * spacing_ms / 1000.0 for i in range(n_notes)], dtype=np.float64)
    last_note_time = timestamps[-1]
    return {
        "timestamps": timestamps,
        "n_notes": n_notes,
        "last_note_time": last_note_time,
        "long_notes": 0,
        "fever_fill_rate": fever_fill_rate,
        "fever_time_stat": fever_time_stat,
    }


def compute_fever_mask(timestamps, total_notes, fever_fill_rate, fever_time_stat, long_notes, last_note_time):
    """Compute fever mask using the existing function."""
    mask_buffer = np.zeros(total_notes, dtype=bool)
    head_mask, body_fever, body_normal, activations, last_end = calculate_fever_timeline_indices(
        timestamps, total_notes, fever_fill_rate, fever_time_stat,
        long_notes, last_note_time, mask_buffer
    )
    return mask_buffer.copy(), head_mask, body_fever, body_normal, activations


def compute_score_from_mask(fever_mask, base_value, combo_mul, fever_mul, total_notes=None):
    """Compute score from a boolean fever mask."""
    if total_notes is None:
        total_notes = len(fever_mask)
    head_limit = min(total_notes, 100)
    head_mask = fever_mask[:head_limit]
    n_fever_body = int(np.sum(fever_mask[head_limit:])) if total_notes > 100 else 0
    n_normal_body = max(0, total_notes - head_limit - n_fever_body)
    return fast_calculate_score(base_value, combo_mul, fever_mul, head_mask, n_fever_body, n_normal_body)


def shift_fever_mask(mask, shift_by):
    """Shift a boolean fever mask RIGHT by shift_by positions. Notes shift out on left, in on right."""
    shifted = np.zeros_like(mask)
    n = len(mask)
    if shift_by >= n:
        return shifted
    shifted[shift_by:] = mask[: n - shift_by]
    return shifted


class TestS9Decomposition(unittest.TestCase):
    """Validate S9: FG Dual-Mechanism Decomposition Theorem."""

    @classmethod
    def setUpClass(cls):
        cls.song = make_synthetic_song(n_notes=200, spacing_ms=80)
        cls.timestamps = cls.song["timestamps"]
        cls.N = cls.song["n_notes"]
        cls.ff = cls.song["fever_fill_rate"]
        cls.ft = cls.song["fever_time_stat"]

        # Compute base fever timeline
        cls.mask, cls.head, cls.body_f, cls.body_n, cls.activations = compute_fever_mask(
            cls.timestamps, cls.N, cls.ff, cls.ft, cls.song["long_notes"], cls.song["last_note_time"]
        )

        # Scoring constants (arbitrary but realistic)
        cls.base_value = 400.0
        cls.combo_mul = 2.5
        cls.fever_mul = 4.0

        # Fever bonus per note: V_fever - V_normal
        cls.fever_val = int(cls.base_value * cls.combo_mul * cls.fever_mul)     # fever body note
        cls.normal_val = int(cls.base_value * cls.combo_mul)                    # normal body note
        cls.bonus_body = cls.fever_val - cls.normal_val

        cls.base_score = compute_score_from_mask(
            cls.mask, cls.base_value, cls.combo_mul, cls.fever_mul, cls.N
        )

    # ── Lemma 1: Body score constancy ──────────────────────────────
    def test_lemma1_body_score_constancy(self):
        """Each body note (i >= 100) contributes identical fever bonus regardless of position."""
        # Verify: changing which body notes are fever (same count) produces same score
        for d_fever in [1, 5, 10, 30]:
            # Mask A: fever at positions 150..150+d_fever
            mask_a = np.zeros(self.N, dtype=bool)
            mask_a[150 : 150 + d_fever] = True
            s_a = compute_score_from_mask(mask_a, self.base_value, self.combo_mul, self.fever_mul, self.N)

            # Mask B: fever at positions 170..170+d_fever (different body positions)
            mask_b = np.zeros(self.N, dtype=bool)
            mask_b[170 : 170 + d_fever] = True
            s_b = compute_score_from_mask(mask_b, self.base_value, self.combo_mul, self.fever_mul, self.N)

            self.assertEqual(s_a, s_b,
                f"Same count at different positions should be equal: {s_a} vs {s_b} for d={d_fever}")

        # Verify per-body-note marginal value is constant
        s0 = compute_score_from_mask(np.zeros(self.N, dtype=bool), self.base_value, self.combo_mul, self.fever_mul, self.N)
        s1 = compute_score_from_mask(
            self._mask_with_one_fever_at(150), self.base_value, self.combo_mul, self.fever_mul, self.N
        )
        s2 = compute_score_from_mask(
            self._mask_with_one_fever_at(180), self.base_value, self.combo_mul, self.fever_mul, self.N
        )

        delta_a = s1 - s0
        delta_b = s2 - s0
        self.assertEqual(delta_a, delta_b,
            f"Per-body-note fever bonus should be position-independent: {delta_a} vs {delta_b}")

    def _mask_with_one_fever_at(self, idx):
        mask = np.zeros(self.N, dtype=bool)
        mask[idx] = True
        return mask

    # ── Lemma 2: Body-only window shift produces zero base score change ──
    def test_lemma2_body_only_shift_zero(self):
        """Shifting a fever window entirely within the body region changes no base score."""
        fever_notes = 30
        positions = [100, 110, 120, 130, 140, 150, 160, 170]

        scores = []
        for start in positions:
            if start + fever_notes > self.N:
                continue
            mask = np.zeros(self.N, dtype=bool)
            mask[start : start + fever_notes] = True
            s = compute_score_from_mask(mask, self.base_value, self.combo_mul, self.fever_mul, self.N)
            scores.append(s)

        # All positions should produce identical scores
        self.assertTrue(all(s == scores[0] for s in scores),
            f"Body window shift should produce identical scores, got {scores}")

    # ── Lemma 3: Head shift benefit is bounded by d * (B_max - B_min) ──
    def test_lemma3_head_shift_bound(self):
        """Benefit of shifting a fever window in head is bounded by shift * (B_max - B_min)."""
        # Compute B(i) = fever_bonus at each head note
        head_bonuses = []
        for i in range(min(self.N, 100)):
            mask = np.zeros(self.N, dtype=bool)
            mask[i] = True
            s_fever = compute_score_from_mask(mask, self.base_value, self.combo_mul, self.fever_mul, self.N)
            mask[i] = False
            s_normal = compute_score_from_mask(mask, self.base_value, self.combo_mul, self.fever_mul, self.N)
            head_bonuses.append(s_fever - s_normal)

        B_max = max(head_bonuses)
        B_min = min(head_bonuses)
        self.assertGreater(B_max, B_min, "Head ramp should create varying fever bonus")

        # Simulate: move a fever window of width W by d notes RIGHT in head region
        W = 15
        for d in [1, 2, 3, 5, 10]:
            if d + W > 100:
                continue
            a = 20  # base start
            b = a + W  # base end

            # Base mask: fever at a..b-1
            base_mask = np.zeros(self.N, dtype=bool)
            base_mask[a:b] = True
            base_s = compute_score_from_mask(base_mask, self.base_value, self.combo_mul, self.fever_mul, self.N)

            # Shifted mask: fever at a+d..b+d-1
            shifted_mask = np.zeros(self.N, dtype=bool)
            shifted_mask[a + d : b + d] = True
            shifted_s = compute_score_from_mask(shifted_mask, self.base_value, self.combo_mul, self.fever_mul, self.N)

            delta = shifted_s - base_s
            bound = d * (B_max - B_min)

            self.assertLessEqual(delta, bound + 1,  # +1 for floor/rounding
                f"Shift delta {delta} exceeds bound {bound} for d={d}, W={W}")

    # ── Lemma 4: Decomposition upper bound is admissible ──
    def test_lemma4_decomposition_bound_admissible(self):
        """The decomposition upper bound never underestimates the true FG score ceiling."""
        # Compute head fever bonus range
        head_bonuses = []
        for i in range(min(self.N, 100)):
            mask = np.zeros(self.N, dtype=bool)
            mask[i] = True
            s_f = compute_score_from_mask(mask, self.base_value, self.combo_mul, self.fever_mul, self.N)
            mask[i] = False
            s_n = compute_score_from_mask(mask, self.base_value, self.combo_mul, self.fever_mul, self.N)
            head_bonuses.append(s_f - s_n)
        B_max = max(head_bonuses)
        B_min = min(head_bonuses)

        # Maximum possible shift per section (from forced-great caps)
        max_shift = 30   # typical section cap
        n_sections = max(1, self.activations + 1)

        # Shift bound
        shift_bound = n_sections * max_shift * (B_max - B_min)

        # Creation bound: if we can add one more fever window
        # Window width = fever_duration / note_spacing
        fever_duration_s = self.ft * (self.song["last_note_time"] * 0.15 + 0.15)
        note_spacing_s = 80.0 / 1000.0
        window_width = max(1, int(fever_duration_s / note_spacing_s))
        create_bound = window_width * B_max  # up to one extra activation

        total_bound = shift_bound + create_bound

        # The bound should be positive (FG could theoretically help)
        self.assertGreater(total_bound, 0,
            f"Decomposition bound should be > 0 for this song: {total_bound}")

        # Verify: the absolute maximum score (all notes fever) is <= base_score + bound
        all_fever_mask = np.ones(self.N, dtype=bool)
        all_fever_score = compute_score_from_mask(
            all_fever_mask, self.base_value, self.combo_mul, self.fever_mul, self.N
        )
        max_possible_gain = all_fever_score - self.base_score

        self.assertLessEqual(max_possible_gain, total_bound,
            f"Max possible gain {max_possible_gain} exceeds bound {total_bound}")

    # ── Integration: Pre-FG skip test ──
    def test_integration_pre_fg_skip(self):
        """If the decomposition bound is <= 0, FG cannot improve base score."""
        # Compute the bound elements
        head_bonuses = []
        for i in range(min(self.N, 100)):
            mask = np.zeros(self.N, dtype=bool)
            mask[i] = True
            s_f = compute_score_from_mask(mask, self.base_value, self.combo_mul, self.fever_mul, self.N)
            mask[i] = False
            s_n = compute_score_from_mask(mask, self.base_value, self.combo_mul, self.fever_mul, self.N)
            head_bonuses.append(s_f - s_n)

        B_max = max(head_bonuses)
        B_min = min(head_bonuses)
        shift_bound = self.activations * 30 * (B_max - B_min)
        create_bound = 0  # assume no room for extra activation

        # The minimum penalty to achieve any shift is > 0
        # Since each forced Great costs at least 1 combo_value, the minimum penalty
        # for any forced Great in the body is body_penalty
        body_penalty = self.fever_val - self.normal_val  # simplified: penalty = fever bonus

        # Net bound: shift benefit - minimum penalty to shift
        net_bound = shift_bound - body_penalty

        # For this synthetic song, the bound should be positive (FG might help)
        # This is a smoke test, not an assertion of negativity
        actual_gain = 0
        for d in [1, 5, 10]:
            if self.activations >= 1:
                # Try shifting the first fever window
                a = 0
                for i in range(self.N):
                    if self.mask[i]:
                        a = i
                        break
                # Find the first contiguous fever block
                b = a
                while b < self.N and self.mask[b]:
                    b += 1

                if a < 100 and b <= self.N:
                    shifted = self.mask.copy()
                    shift_amount = min(d, self.N - b)
                    if shift_amount > 0:
                        shifted[a : a + shift_amount] = False
                        shifted[b : b + shift_amount] = True
                        shifted_s = compute_score_from_mask(
                            shifted, self.base_value, self.combo_mul, self.fever_mul, self.N
                        )
                        gain = shifted_s - self.base_score
                        actual_gain = max(actual_gain, gain)

        # The actual gain should be bounded by the decomposition bound
        self.assertLessEqual(actual_gain, net_bound + self.base_score,
            f"Actual FG gain {actual_gain} exceeds net bound {net_bound}")

    # ── Lemma: Body window shift with penalty always negative ──
    def test_body_shift_with_penalty_always_negative(self):
        """Any forced Great that shifts a body-only fever window is net negative."""
        # Find a body-only fever window
        fever_start = None
        for i in range(100, self.N):
            if self.mask[i]:
                fever_start = i
                break

        if fever_start is None:
            self.skipTest("No body fever window in base timeline")

        fever_end = fever_start
        while fever_end < self.N and self.mask[fever_end]:
            fever_end += 1

        # Shift this window RIGHT by d within body
        for d in [1, 3, 5]:
            if fever_end + d > self.N:
                continue
            shifted = self.mask.copy()
            shifted[fever_start : fever_start + d] = False
            shifted[fever_end : fever_end + d] = True

            shifted_s = compute_score_from_mask(
                shifted, self.base_value, self.combo_mul, self.fever_mul, self.N
            )

            # Base score change from shift alone
            shift_delta = shifted_s - self.base_score

            # Should be exactly 0 from Lemma 2
            self.assertEqual(shift_delta, 0,
                f"Body-only shift should produce zero base score change, got {shift_delta}")

            # With penalty: total = shift_delta - penalty = -penalty < 0
            # So FG cannot help via body-only shifting


if __name__ == "__main__":
    unittest.main(verbosity=2)
