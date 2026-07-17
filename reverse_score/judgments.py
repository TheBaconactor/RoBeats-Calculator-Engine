"""Judgment-count recovery for non-FC plays (accuracy < 1).

Game accuracy (PlayerScore.get_accuracy):
    accuracy = (perfect + 0.75*great + 0.25*okay) / hit_count
with hit_count the song's judgeable-event count (holds judge twice) plus
early-release extras, and perfect+great+okay+miss == hit_count.

Substituting perfect = H - g - o - m gives the deficit identity
    H - weighted = 0.25*g + 0.75*o + 1.0*m  ==  (g + 3*o + 4*m) / 4
so the integer k = g + 3o + 4m must land in the narrow band the rounded
accuracy admits. Enumerating k then all non-negative (g, o, m) solving
g + 3o + 4m = k yields every judgment multiset consistent with the display.

This is layer 1 of non-FC inversion: it recovers WHAT was hit, exactly and
completely. Layer 2 (which notes -- the sequence DP against the exact naked
score) is a separate work item; ``invert`` fails loudly for accuracy < 1 and
points here so no caller can mistake counts for a full inversion.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JudgmentCounts:
    perfect: int
    great: int
    okay: int
    miss: int

    @property
    def total(self) -> int:
        return self.perfect + self.great + self.okay + self.miss

    def accuracy(self) -> float:
        return (self.perfect + 0.75 * self.great + 0.25 * self.okay) / self.total


def feasible_judgment_counts(
    accuracy: float,
    hit_count: int,
    *,
    decimals: int = 5,
    max_k: int | None = None,
) -> list[JudgmentCounts]:
    """All (perfect, great, okay, miss) multisets whose exact accuracy rounds
    to ``accuracy`` at ``decimals`` places for a song with ``hit_count``
    judgeable events.

    The leaderboard payload carries 5-decimal accuracy; the in-game display
    rounds harder (pass decimals=2 for screenshots). ``max_k`` caps the
    enumerated deficit (defaults to the theoretical maximum 4*hit_count).
    """
    if hit_count <= 0:
        raise ValueError(f"hit_count must be positive, got {hit_count}")
    if not (0.0 <= accuracy <= 1.0):
        raise ValueError(f"accuracy must be in [0, 1], got {accuracy}")
    half_ulp = 0.5 * 10.0 ** (-decimals)
    # weighted = H - k/4 must satisfy round(weighted/H) == accuracy:
    #   (accuracy - half_ulp) * H <= H - k/4 <= (accuracy + half_ulp) * H
    k_lo_f = 4.0 * hit_count * (1.0 - accuracy - half_ulp)
    k_hi_f = 4.0 * hit_count * (1.0 - accuracy + half_ulp)
    k_lo = max(0, int(-(-k_lo_f // 1)))  # ceil
    k_hi = int(k_hi_f // 1)  # floor
    ceiling = 4 * hit_count if max_k is None else min(max_k, 4 * hit_count)
    k_hi = min(k_hi, ceiling)

    out: list[JudgmentCounts] = []
    for k in range(k_lo, k_hi + 1):
        for okay in range(k // 3 + 1):
            rem = k - 3 * okay
            for miss in range(rem // 4 + 1):
                great = rem - 4 * miss
                perfect = hit_count - great - okay - miss
                if perfect < 0:
                    continue
                counts = JudgmentCounts(perfect, great, okay, miss)
                # Guard the closed form against rounding-edge drift.
                if round(counts.accuracy(), decimals) == round(accuracy, decimals):
                    out.append(counts)
    return out


def is_true_full_combo(counts: list[JudgmentCounts]) -> bool:
    """True iff the only feasible multiset is all-Perfect."""
    return len(counts) == 1 and counts[0].great == 0 and counts[0].okay == 0 and counts[0].miss == 0
