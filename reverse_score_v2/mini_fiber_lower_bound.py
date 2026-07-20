"""Fiber-multiplicity lower-bound probe for the reverse score engine v2.

Handoff §16.1 requires a static probe that computes a guaranteed lower
bound on K (the answer-class size) from mini identity multiplicity,
WITHOUT solving the whole inversion. For each known synthetic or
own-account truth loadout, hold every non-mini decision fixed (the
truth's gear, upgrades, gems, buff) and count:

- For the truth's mini contribution vector per slot, how many DISTINCT
  (pet, level, rank, asc) tuples produce that exact vector?
- Across 3 mini slots, the joint identity multiplicity = product of
  per-slot counts (if independent) OR the C(n, 3) unordered count (if
  the game's ≤3 equipped distinct-pet law applies).

This is a LOWER BOUND on K for that row: any loadout class member that
shares the truth's non-mini decisions and uses contribution-equivalent
mini identities is a distinct class member (the mini-identity fiber,
handoff §12, is DISTINCT -- NOT collapsed).

The probe reports:
- per-sample fiber multiplicity lower bound on K,
- the worst case across 16 samples,
- whether this lower bound exceeds the 20s materialization budget
  (roughly: K > 10**6 is concerning; K > 10**7 is a likely no-go for
  explicit materialization),
- the histogram of fiber sizes (how many distinct (pet, level, rank,
  asc) tuples share each contribution vector).

Truth sampler: no ``reverse_score_v2.synth`` module exists yet. The
probe builds 16 truth loadouts via a DomainIR-based sampler: pick 3
distinct pets (the cross-slot distinct-pet law), pick a random
(level, rank, asc) state per pet, and use the resulting tuple's
contribution vector as the truth's per-slot mini contribution. Non-
mini decisions are held at the all-zero baseline (no gear, no upgrades,
no gems, no team buff) -- the probe isolates mini identity multiplicity
and does NOT depend on the non-mini baseline; any other fixed non-mini
baseline would give the same lower bound because the mini contribution
vector is what the fiber is counted over.

Usage:
    python -m reverse_score_v2.mini_fiber_lower_bound
"""
from __future__ import annotations

import math
import os
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from reverse_score_v2.mini_factored import (
    MiniTuple,
    build_mini_relation,
    flat_enumerate_mini_tuples,
)

# Number of truth samples the probe generates. The handoff names "16
# samples" (mirroring v1's LOVERS' OASIS Easy multi-seed); we use 16.
N_SAMPLES: int = 16

# Materialization-budget thresholds. K > 10**6 is concerning; K > 10**7
# is a likely no-go for explicit materialization within 20s.
K_CONCERNING: int = 10**6
K_LIKELY_NOGO: int = 10**7

# Fixed seed for the truth sampler; the probe is deterministic.
TRUTH_SEED: int = 20250719

# Number of mini slots in a loadout (handoff §3: ≤3 minis).
N_MINI_SLOTS: int = 3


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FiberProbeSample:
    """One truth sample's fiber probe result."""

    sample_id: int
    # The truth's per-slot mini tuples (the picked identities).
    truth_tuples: tuple[MiniTuple, ...]
    # Per-slot fiber sizes: for each slot's truth vec, how many
    # distinct (pet, level, rank, asc) tuples produce that exact vec.
    per_slot_fiber_sizes: tuple[int, ...]
    # Per-slot distinct pet counts: how many distinct pets appear in
    # each slot's fiber.
    per_slot_distinct_pets: tuple[int, ...]
    # Joint multiplicity if slots are independent and same-pet across
    # slots is allowed: product of per-slot fiber sizes.
    joint_ordered_with_repetition: int
    # Exact ordered count under the game's ≤3 distinct-pet law:
    # |{(t1,t2,t3) in F1×F2×F3 : pets pairwise distinct}|.
    # This is the defensible fiber-only lower bound on K when non-mini
    # decisions are held fixed (and also the exact mini-fiber class
    # size for that fixed non-mini baseline).
    joint_ordered_distinct_pets: int
    # Unordered C(n, 3) over the union of the three slot fibers
    # (handoff's illustrative figure when all three slots land in one
    # large fiber). Reported for comparison; not used as the K lower
    # bound when the three truth vectors differ.
    joint_unordered_comb: int
    # The defensible lower bound on K for this row.
    k_lower_bound: int


@dataclass(frozen=True, slots=True)
class FiberProbeReport:
    """Full report across all 16 samples."""

    samples: tuple[FiberProbeSample, ...]
    # Histogram of all fiber sizes seen across the 16 samples' slot
    # fibers (3 fibers per sample -> 48 fiber sizes).
    fiber_size_histogram: tuple[tuple[int, int], ...]
    # Histogram of all fiber sizes across the ENTIRE mini relation.
    global_fiber_size_histogram: tuple[tuple[int, int], ...]
    # Worst-case K lower bound across the 16 samples.
    worst_case_k_lower_bound: int
    # Best-case K lower bound across the 16 samples.
    best_case_k_lower_bound: int
    # Geometric mean K lower bound across the 16 samples.
    geometric_mean_k_lower_bound: float
    # Verdict: does the worst-case K lower bound exceed the 20s
    # materialization budget?
    worst_case_exceeds_concerning: bool
    worst_case_exceeds_likely_nogo: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_webport_root() -> Path:
    """Resolve the decompiled ReplicatedStorage root (SarHort V5 default)."""
    env_root = os.environ.get("ROBEATS_DECOMPILED_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(
        r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/SavedGame_706824758/ReplicatedStorage"
    )


def _build_vec_index(
    tuples: list[MiniTuple],
) -> tuple[dict[bytes, list[MiniTuple]], dict[bytes, set[str]]]:
    """Build the vec -> tuples index and vec -> pets index.

    The vec key is ``vec.tobytes()`` (the 7-dim int32 contribution
    vector's byte encoding). The tuples index lists every legal
    (pet, level, rank, asc) tuple sharing that vec; the pets index is
    the set of distinct pet names in that fiber (used for cross-slot
    uniqueness analysis).
    """
    vec_to_tuples: dict[bytes, list[MiniTuple]] = {}
    vec_to_pets: dict[bytes, set[str]] = {}
    for t in tuples:
        key = t.vec.tobytes()
        vec_to_tuples.setdefault(key, []).append(t)
        if t.pet_name is not None:
            vec_to_pets.setdefault(key, set()).add(t.pet_name)
    return vec_to_tuples, vec_to_pets


def _build_pet_to_tuples(tuples: list[MiniTuple]) -> dict[str, list[MiniTuple]]:
    """Build pet -> list of tuples index (for the truth sampler)."""
    pet_to_tuples: dict[str, list[MiniTuple]] = {}
    for t in tuples:
        if t.pet_name is None:
            continue
        pet_to_tuples.setdefault(t.pet_name, []).append(t)
    return pet_to_tuples


def _sample_truth_loadouts(
    pet_to_tuples: dict[str, list[MiniTuple]],
    rng: random.Random,
    n_samples: int,
    n_slots: int,
) -> list[tuple[MiniTuple, ...]]:
    """Sample 16 truth loadouts: 3 distinct pets, random state per pet.

    Each truth loadout is a tuple of n_slots MiniTuples, one per mini
    slot. The pets are sampled WITHOUT replacement (the game's ≤3
    distinct-pet law), and the (level, rank, asc) state per pet is
    sampled uniformly from that pet's legal states. Non-mini decisions
    are held at the all-zero baseline; the probe isolates mini identity
    multiplicity.
    """
    all_pet_names = sorted(pet_to_tuples.keys())
    if len(all_pet_names) < n_slots:
        raise ValueError(
            f"need >= {n_slots} distinct pets to fill the slots, "
            f"got {len(all_pet_names)}"
        )
    truths: list[tuple[MiniTuple, ...]] = []
    for _ in range(n_samples):
        chosen = rng.sample(all_pet_names, n_slots)
        slot_picks: list[MiniTuple] = []
        for pet_name in chosen:
            slot_picks.append(rng.choice(pet_to_tuples[pet_name]))
        truths.append(tuple(slot_picks))
    return truths


def _count_fiber_for_slot(
    truth_tuple: MiniTuple,
    vec_to_tuples: dict[bytes, list[MiniTuple]],
    vec_to_pets: dict[bytes, set[str]],
) -> tuple[int, int, list[MiniTuple]]:
    """Count the fiber size for one slot's truth vec.

    Returns (fiber_size, distinct_pet_count, fiber_tuples).
    """
    if truth_tuple.pet_name is None:
        # Empty slot: only the empty option produces the zero vec.
        return 1, 0, [truth_tuple]
    key = truth_tuple.vec.tobytes()
    fiber = vec_to_tuples.get(key, [truth_tuple])
    pets = vec_to_pets.get(key, set())
    return len(fiber), len(pets), fiber


def _count_joint_unordered_comb(
    slot_fibers: tuple[list[MiniTuple], ...],
) -> int:
    """C(n_total, 3) over the union of (pet, level, rank, asc) across fibers.

    Illustrative figure from the handoff when three slots land in one
    large fiber. Not the K lower bound when the three truth vectors
    differ.
    """
    seen: set[tuple] = set()
    for fiber in slot_fibers:
        for t in fiber:
            if t.pet_name is None:
                continue
            seen.add((t.pet_name, t.level, t.rank, t.asc))
    n_total = len(seen)
    if n_total < 3:
        return 0
    return math.comb(n_total, 3)


def _count_joint_ordered_with_repetition(
    per_slot_fiber_sizes: tuple[int, ...],
) -> int:
    """Product of per-slot fiber sizes (ordered, repetition allowed)."""
    product = 1
    for size in per_slot_fiber_sizes:
        product *= size
    return product


def _count_joint_ordered_distinct_pets(
    slot_fibers: tuple[list[MiniTuple], ...],
) -> int:
    """Exact |F1×F2×F3| under pairwise-distinct pet names.

    Groups each fiber by pet name, then enumerates pet triples. With
    ≤90 pets this is O(P^3) ≤ ~729k iterations -- fast enough for 16
    samples. This is the defensible fiber-only lower bound on K when
    non-mini decisions are held fixed.
    """
    if len(slot_fibers) != 3:
        raise ValueError(
            f"joint distinct-pet count requires exactly 3 slot fibers, "
            f"got {len(slot_fibers)}"
        )
    groups: list[Counter] = []
    for fiber in slot_fibers:
        by_pet: Counter = Counter()
        for t in fiber:
            if t.pet_name is not None:
                by_pet[t.pet_name] += 1
        groups.append(by_pet)
    pets0 = list(groups[0].keys())
    pets1 = list(groups[1].keys())
    pets2 = list(groups[2].keys())
    total = 0
    for p0 in pets0:
        c0 = groups[0][p0]
        for p1 in pets1:
            if p1 == p0:
                continue
            c1 = groups[1][p1]
            for p2 in pets2:
                if p2 == p0 or p2 == p1:
                    continue
                total += c0 * c1 * groups[2][p2]
    return total


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


def run_probe(
    relation,
    *,
    n_samples: int = N_SAMPLES,
    seed: int = TRUTH_SEED,
) -> FiberProbeReport:
    """Run the fiber-multiplicity lower-bound probe on the relation.

    Returns a ``FiberProbeReport`` with 16 samples and the global fiber
    size histogram.
    """
    tuples = flat_enumerate_mini_tuples(relation)
    vec_to_tuples, vec_to_pets = _build_vec_index(tuples)
    pet_to_tuples = _build_pet_to_tuples(tuples)
    rng = random.Random(seed)
    truths = _sample_truth_loadouts(pet_to_tuples, rng, n_samples, N_MINI_SLOTS)

    samples: list[FiberProbeSample] = []
    sample_fiber_sizes: list[int] = []
    k_lower_bounds: list[int] = []

    for sample_id, truth in enumerate(truths):
        per_slot_sizes: list[int] = []
        per_slot_pets: list[int] = []
        slot_fibers: list[list[MiniTuple]] = []
        for slot_idx in range(N_MINI_SLOTS):
            truth_tuple = truth[slot_idx]
            size, pet_count, fiber = _count_fiber_for_slot(
                truth_tuple, vec_to_tuples, vec_to_pets
            )
            per_slot_sizes.append(size)
            per_slot_pets.append(pet_count)
            slot_fibers.append(fiber)
            sample_fiber_sizes.append(size)
        joint_ordered = _count_joint_ordered_with_repetition(tuple(per_slot_sizes))
        joint_distinct = _count_joint_ordered_distinct_pets(tuple(slot_fibers))
        joint_comb = _count_joint_unordered_comb(tuple(slot_fibers))
        # Defensible lower bound: exact ordered count under the distinct-
        # pet law. The with-repetition product is an upper envelope; the
        # C(n,3) figure is the handoff's same-fiber illustration.
        k_lower = joint_distinct
        samples.append(
            FiberProbeSample(
                sample_id=sample_id,
                truth_tuples=truth,
                per_slot_fiber_sizes=tuple(per_slot_sizes),
                per_slot_distinct_pets=tuple(per_slot_pets),
                joint_ordered_with_repetition=joint_ordered,
                joint_ordered_distinct_pets=joint_distinct,
                joint_unordered_comb=joint_comb,
                k_lower_bound=k_lower,
            )
        )
        k_lower_bounds.append(k_lower)

    # Global fiber size histogram.
    global_sizes: list[int] = []
    for fiber in vec_to_tuples.values():
        global_sizes.append(len(fiber))
    global_hist = sorted(Counter(global_sizes).items())

    sample_hist = sorted(Counter(sample_fiber_sizes).items())

    worst = max(k_lower_bounds)
    best = min(k_lower_bounds)
    log_sum = sum(np.log(max(k, 1)) for k in k_lower_bounds)
    geo_mean = float(np.exp(log_sum / len(k_lower_bounds)))

    return FiberProbeReport(
        samples=tuple(samples),
        fiber_size_histogram=tuple(sample_hist),
        global_fiber_size_histogram=tuple(global_hist),
        worst_case_k_lower_bound=worst,
        best_case_k_lower_bound=best,
        geometric_mean_k_lower_bound=geo_mean,
        worst_case_exceeds_concerning=worst > K_CONCERNING,
        worst_case_exceeds_likely_nogo=worst > K_LIKELY_NOGO,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _print_sample_table(report: FiberProbeReport) -> None:
    print()
    print("  Per-sample fiber multiplicity lower bound on K:")
    print(
        f"  {'#':>3}  {'slot1 fiber':>14}  {'slot2 fiber':>14}  "
        f"{'slot3 fiber':>14}  {'pets1':>6}  {'pets2':>6}  {'pets3':>6}  "
        f"{'ordered*':>16}  {'distinct':>16}  {'K_lower':>16}"
    )
    print("  " + "-" * 130)
    for s in report.samples:
        print(
            f"  {s.sample_id:>3}  "
            f"{_fmt_int(s.per_slot_fiber_sizes[0]):>14}  "
            f"{_fmt_int(s.per_slot_fiber_sizes[1]):>14}  "
            f"{_fmt_int(s.per_slot_fiber_sizes[2]):>14}  "
            f"{s.per_slot_distinct_pets[0]:>6}  "
            f"{s.per_slot_distinct_pets[1]:>6}  "
            f"{s.per_slot_distinct_pets[2]:>6}  "
            f"{_fmt_int(s.joint_ordered_with_repetition):>16}  "
            f"{_fmt_int(s.joint_ordered_distinct_pets):>16}  "
            f"{_fmt_int(s.k_lower_bound):>16}"
        )
    print("  " + "-" * 130)
    print("  ordered* = product of per-slot fiber sizes (repetition allowed)")
    print("  distinct = exact |F1×F2×F3| under pairwise-distinct pets (K_lower)")


def _print_histogram(title: str, hist: tuple[tuple[int, int], ...]) -> None:
    print()
    print(f"  {title}")
    print(f"  {'fiber_size':>12}  {'count':>8}")
    print("  " + "-" * 30)
    for size, count in hist:
        print(f"  {size:>12,}  {count:>8,}")
    print("  " + "-" * 30)


def _print_verdict(report: FiberProbeReport) -> None:
    print()
    print("=" * 98)
    print("  VERDICT -- fiber-multiplicity lower bound on K")
    print("=" * 98)
    print(
        f"  worst-case K lower bound across 16 samples:  "
        f"{_fmt_int(report.worst_case_k_lower_bound)}"
    )
    print(
        f"  best-case K lower bound across 16 samples:   "
        f"{_fmt_int(report.best_case_k_lower_bound)}"
    )
    print(
        f"  geometric-mean K lower bound:                "
        f"{report.geometric_mean_k_lower_bound:.2f}"
    )
    print()
    print(
        f"  exceeds 10**6 (concerning):   "
        f"{report.worst_case_exceeds_concerning}"
    )
    print(
        f"  exceeds 10**7 (likely no-go): {report.worst_case_exceeds_likely_nogo}"
    )
    print()
    if report.worst_case_k_lower_bound > K_LIKELY_NOGO:
        print(
            "  -> The fiber-multiplicity lower bound EXCEEDS the 10**7 "
            "likely no-go threshold. The 138,601 -> 4,798 mini "
            "reformulation makes the SEARCH compact but leaves the "
            "OUTPUT K too large for explicit materialization within "
            "20s. The 20s gate cannot be claimed for these rows."
        )
    elif report.worst_case_k_lower_bound > K_CONCERNING:
        print(
            "  -> The fiber-multiplicity lower bound EXCEEDS the 10**6 "
            "concerning threshold but stays below 10**7. K1.a-with-S "
            "must measure whether the S constraint prunes the fiber-"
            "equivalent identities enough to fit the 20s budget."
        )
    else:
        print(
            "  -> The fiber-multiplicity lower bound stays under 10**6. "
            "Explicit materialization within 20s is credible; K1.a-"
            "with-S must confirm the exact K."
        )


def main() -> int:
    webport_root = _resolve_webport_root()
    if not webport_root.is_dir():
        print(f"ERROR: webport_root not found: {webport_root}", file=sys.stderr)
        return 2

    print(f"python: {sys.version.split()[0]}")
    print(f"numpy:  {np.__version__}")
    print(f"webport_root: {webport_root}")
    print()
    print("  Building factored mini relation (single-color Chill, seed song) ...")
    relation = build_mini_relation(webport_root, song_colors=("Chill",))
    print(f"  archetypes: {len(relation.archetypes)}")
    print(f"  legal_tuple_count: {_fmt_int(relation.legal_tuple_count)}")
    print(f"  total options (incl. empty): {_fmt_int(relation.legal_tuple_count + 1)}")
    print(
        f"  matches flat 138,601: "
        f"{relation.legal_tuple_count + 1 == 138_601}"
    )
    print(f"  N_SAMPLES: {N_SAMPLES}")
    print(f"  N_MINI_SLOTS: {N_MINI_SLOTS}")
    print(f"  K_CONCERNING: {K_CONCERNING:,}")
    print(f"  K_LIKELY_NOGO: {K_LIKELY_NOGO:,}")

    report = run_probe(relation)

    _print_sample_table(report)
    _print_histogram(
        "Fiber size histogram -- 16 samples' slot fibers (48 fibers total)",
        report.fiber_size_histogram,
    )
    _print_histogram(
        "Global fiber size histogram -- all fibers in the relation",
        report.global_fiber_size_histogram,
    )
    _print_verdict(report)

    print()
    print("=" * 98)
    print("  probe complete")
    print("=" * 98)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
