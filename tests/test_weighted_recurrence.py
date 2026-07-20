"""Test suite for the reverse score engine v2 weighted recurrence.

Verifies the §16.5 weighted recurrence `C(s) = Σ w(e)·C(s')` on the
synthetic CPU domain in `reverse_score_v2.weighted_recurrence`:

1. `test_weighted_recurrence_root_K_equals_flat_enumeration_count`
   - The weighted root K equals the flat (option-product) count.
2. `test_weighted_rank_unrank_covers_all_identities`
   - `weighted_unrank(ir, r)` for `r in range(K)` enumerates every
     flat identity exactly once, in deterministic order.
   - `weighted_rank` is the inverse: `weighted_rank(ir, unrank(r)) == r`.
3. `test_weighted_recurrence_saturates_at_MAX_K`
   - With `max_k = MAX_K // 2`, the recurrence caps at `MAX_K + 1`
     (saturation detection).
4. `test_canonical_scorer_gate_passes_on_all_witnesses`
   - For every materialized witness, two choice tuples with the same
     canonical key produce the same synthetic score.

See `reverse_score_v2/CLASS_EQUIVALENCE_RESOLUTION.md` for the
class-identity resolution that governs this test.
"""
from __future__ import annotations

import numpy as np

from reverse_score_v2.weighted_recurrence import (
    SYNTH_MAX_K,
    SYNTH_PW,
    build_synth_ir,
    canonical_key,
    canonical_scorer_gate,
    flat_count,
    flat_enumerate,
    root_k,
    synth_score,
    weighted_count,
    weighted_rank,
    weighted_unrank,
)


def test_weighted_recurrence_root_K_equals_flat_enumeration_count():
    """K from the weighted recurrence equals the brute-force flat count.

    Under persistent identities (CLASS_EQUIVALENCE_RESOLUTION.md §2.4),
    K is the exact number of physical loadouts in the supported domain.
    The weighted recurrence's K must equal the option-product count,
    because every option is a distinct class member and the fiber
    weights sum to the option count per axis.
    """
    ir = build_synth_ir()
    k_weighted = root_k(ir)
    k_flat = flat_count(ir)
    assert k_weighted == k_flat, f"weighted K={k_weighted} != flat K={k_flat}"
    # Sanity: K is the option product (1 * 7 * 7 * 4 * 3 * 4 = 2352).
    expected_k = 1
    for axis in ir.axes:
        expected_k *= len(axis.options)
    assert k_weighted == expected_k, f"K={k_weighted}, expected option product {expected_k}"


def test_weighted_rank_unrank_covers_all_identities():
    """`weighted_unrank` enumerates every identity exactly once, in the
    same order as the flat enumeration. `weighted_rank` is the inverse.
    """
    ir = build_synth_ir()
    k = root_k(ir)
    assert k > 0, "synthetic domain must be non-empty"

    # The flat enumeration yields every option tuple in canonical axis order.
    flat_list = list(flat_enumerate(ir))
    assert len(flat_list) == k

    # The weighted unrank yields the r-th tuple for r in [0, K).
    unranked = [weighted_unrank(ir, r) for r in range(k)]
    assert len(unranked) == k

    # Every unranked tuple must equal the corresponding flat tuple.
    # The canonical order is: axes in order, within an axis the options
    # in the order they were defined (which matches both flat_enumerate
    # and the fiber-member lexicographic sort when fibers are singletons;
    # for multi-member fibers, the fiber order is first-appearance order
    # and within-fiber members are lexicographically sorted by label).
    # To compare: project both to the canonical key. Use a stringified
    # key for set comparison because option labels mix str and None
    # (the empty mini/gear options carry None), which cannot be sorted
    # directly across mixed types.
    flat_keys = [str(canonical_key(c)) for c in flat_list]
    unranked_keys = [str(canonical_key(c)) for c in unranked]

    # Every identity appears exactly once in each enumeration.
    assert sorted(flat_keys) == sorted(unranked_keys), "identity sets differ"

    # The weighted unrank order is deterministic and matches the flat
    # order (both use the same axis order and within-axis option order).
    # Verify by index: for every r, unranked[r] == flat[r].
    mismatches = [(r, flat_keys[r], unranked_keys[r]) for r in range(k) if flat_keys[r] != unranked_keys[r]]
    assert not mismatches, f"order mismatch at {mismatches[:3]}"

    # weighted_rank is the inverse of weighted_unrank.
    for r in range(k):
        choice = weighted_unrank(ir, r)
        r_back = weighted_rank(ir, choice)
        assert r_back == r, f"rank/unrank roundtrip failed: r={r}, back={r_back}"


def test_weighted_recurrence_saturates_at_MAX_K():
    """With `max_k = MAX_K // 2`, the recurrence caps at `max_k + 1`.

    The synthetic domain's true K is small (2352 < MAX_K); saturation
    is verified by setting `max_k` BELOW the true K. The recurrence
    must return `max_k + 1` (the canonical saturation sentinel).
    """
    ir = build_synth_ir()
    true_k = root_k(ir)
    assert true_k < SYNTH_MAX_K, "synthetic domain K must be below MAX_K"

    # Set max_k below the true K; the recurrence must saturate.
    max_k = true_k // 2
    assert max_k >= 1, "true K must be >= 2 to test saturation"
    saturated_k = root_k(ir, max_k=max_k)
    assert saturated_k == max_k + 1, f"saturated K={saturated_k}, expected {max_k + 1}"

    # With max_k above the true K, the recurrence returns the exact K.
    exact_k = root_k(ir, max_k=true_k * 2)
    assert exact_k == true_k, f"exact K={exact_k}, expected {true_k}"


def test_canonical_scorer_gate_passes_on_all_witnesses():
    """For every materialized witness, two choice tuples with the same
    canonical key produce the same synthetic score (the soundness gate).

    Under persistent identities, the canonical key is the full label
    tuple, so two tuples with the same key are the same tuple. The gate
    is asserted on every materialized witness as a defensive check
    against any future collapse that breaks the invariant.

    Also verifies the deeper property the production gate enforces:
    two witnesses with the same CONTRIBUTION VECTOR (i.e. in the same
    identity fiber) produce the same score, because the scorer reads
    only the 7-dim projection.
    """
    ir = build_synth_ir()
    k = root_k(ir)
    assert k > 0

    # Materialize every witness and assert the gate passes.
    for r in range(k):
        choice = weighted_unrank(ir, r)
        # The gate: same key -> same score (trivially true under
        # persistent identities; asserted defensively).
        assert canonical_scorer_gate(choice, choice), f"self-gate failed at r={r}"

    # The deeper property: any two witnesses in the same identity fiber
    # (same contribution vector across all axes) produce the same score.
    # Build the set of all witnesses grouped by their full accumulated
    # contribution vector.
    vec_to_score: dict[bytes, int] = {}
    vec_to_keys: dict[bytes, list[tuple]] = {}
    for r in range(k):
        choice = weighted_unrank(ir, r)
        vec = np.zeros(7, dtype=np.int32)
        for opt in choice:
            vec = vec + opt.vec
        key = vec.tobytes()
        score = synth_score(choice)
        if key in vec_to_score:
            assert vec_to_score[key] == score, (
                f"two witnesses with the same contribution vector produce different scores "
                f"at r={r}: keys={vec_to_keys[key]} vs {canonical_key(choice)}"
            )
        else:
            vec_to_score[key] = score
            vec_to_keys[key] = []
        vec_to_keys[key].append(canonical_key(choice))

    # Sanity: at least one contribution vector is shared by multiple
    # distinct identities (the synthetic domain is designed for this).
    shared = [k for k, v in vec_to_keys.items() if len(v) > 1]
    assert shared, "no shared contribution vector — fiber weight never exceeds 1"


# ---------------------------------------------------------------------------
# Additional invariants (not required by the task but document the
# contract for future agents).
# ---------------------------------------------------------------------------


def test_fiber_weights_match_option_counts():
    """The sum of fiber weights on each axis equals the option count.

    This is the structural invariant that makes the weighted K equal
    the flat K: every option is in exactly one fiber, and the fiber
    weight is the option count in that fiber.
    """
    ir = build_synth_ir()
    for axis in ir.axes:
        total_weight = sum(len(fiber) for fiber in axis.identity_fibers)
        assert total_weight == len(axis.options), (
            f"axis {axis.name}: weight sum {total_weight} != options {len(axis.options)}"
        )


def test_distinct_fibers_have_distinct_contribution_vectors():
    """Two fibers on the same axis have distinct contribution vectors.

    This is the structural invariant that makes the fiber grouping
    well-defined: each fiber is the set of options sharing one
    contribution vector.
    """
    ir = build_synth_ir()
    for axis in ir.axes:
        vecs = [fiber[0].vec.tobytes() for fiber in axis.identity_fibers]
        assert len(vecs) == len(set(vecs)), f"axis {axis.name} has duplicate fiber vectors"


def test_unrank_out_of_range_raises():
    """`weighted_unrank(ir, r)` for `r >= K` raises IndexError."""
    ir = build_synth_ir()
    k = root_k(ir)
    try:
        weighted_unrank(ir, k)
    except IndexError:
        return
    raise AssertionError(f"unrank(K={k}) did not raise IndexError")
