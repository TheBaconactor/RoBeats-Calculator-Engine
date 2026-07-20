"""Weighted recurrence for the reverse score engine v2.

Reference CPU implementation of the §16.5 weighted recurrence
`C(s) = Σ w(e)·C(s')`, where the edge weight `w(e)` is the fiber weight
(the number of canonical identities the edge represents).

This module specifies and implements:

1. The recurrence over `DomainIR.identity_fibers`.
2. Saturating counts (research: cap at `MAX_K + 1`; production: exact).
3. Rank/unrank through weighted child intervals.
4. A CPU reference on a tiny synthetic domain (2 mini slots, 3 gear
   slots, no upgrades, no gems, no team buff) that verifies:
   - root K equals the flat enumeration count,
   - rank/unrank covers all identities in deterministic order,
   - the canonical scorer gate passes on every witness,
   - saturation at `MAX_K`.

The synthetic domain bypasses `build_domain_ir` (which requires the
decompiled webport root) and constructs a `DomainIR` directly from the
`Axis`/`AxisOption`/`DomainIR` dataclasses. The synthetic scorer
follows the same stat-input contract as
`gear_optimizer.solver.scoring.exact_rescore._score_stat_inputs`:
it reads the 7-dim observable projection and returns `gear_power = vec
@ pw` as the score. The canonical scorer gate test asserts two
loadouts with the same canonical key produce the same score — that is
the soundness property the production gate enforces via
`score_stat_arrays_exact_batch`.

See `CLASS_EQUIVALENCE_RESOLUTION.md` for the class-identity resolution
that governs this module.
"""
from __future__ import annotations

from typing import Callable, Iterator, Mapping

import numpy as np

from reverse_score_v2.domain_ir import (
    PROJECTION_DIM,
    Axis,
    AxisOption,
    DomainIR,
    GEAR_SLOTS,
    PROJECTION_KEYS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The synthetic domain: 2 mini slots + 3 gear slots + the team-buff
# zero option. No upgrades, no gems, no elemental axis. Single-color
# (Chill). Designed so K is small enough to enumerate exactly in a test
# but large enough to exercise multiple fibers with weight > 1.
SYNTH_SONG_COLORS: tuple[str, ...] = ("Chill",)
SYNTH_MINI_SLOTS: int = 2
SYNTH_GEAR_SLOTS: tuple[str, ...] = ("Hat", "Neck", "Face")
SYNTH_MAX_K: int = 1_000_000

# The gear-power weight vector for a single-color Chill chart, matching
# `domain_ir._gear_power_weights` exactly: P = 6*c1 + 5*sum(main).
SYNTH_PW: np.ndarray = np.array([6, 0, 5, 5, 5, 5, 5], dtype=np.int32)


# ---------------------------------------------------------------------------
# The weighted recurrence
# ---------------------------------------------------------------------------


def weighted_count(
    ir: DomainIR,
    state: np.ndarray,
    axis_idx: int,
    *,
    feasible: Callable[[np.ndarray, int], bool] | None = None,
    max_k: int | None = None,
    memo: dict[tuple[bytes, int], int] | None = None,
) -> int:
    """C(s, i) = Σ over fibers f of axis i: |f| * C(s + vec(f), i+1).

    Terminal states (i == len(axes)) return 1 if feasible, 0 otherwise.

    `feasible(state, axis_idx)` is the pruning predicate. If None,
    every terminal state is feasible (K = the full option product
    weighted by fiber sizes).

    `max_k` caps the count at `max_k + 1` (saturation detection). If
    None, the count is exact.

    `memo` is an optional memoization table keyed by (state.tobytes(),
    axis_idx). The CPU reference passes a dict for repeated queries;
    one-shot root-K computation omits it.
    """
    n = len(ir.axes)
    if axis_idx == n:
        if feasible is None or feasible(state, axis_idx):
            return 1
        return 0

    if memo is not None:
        key = (state.tobytes(), axis_idx)
        cached = memo.get(key)
        if cached is not None:
            return cached

    total = 0
    axis = ir.axes[axis_idx]
    for fiber in axis.identity_fibers:
        weight = len(fiber)
        vec = fiber[0].vec
        child_state = state + vec
        if feasible is not None and not _prefix_feasible(ir, child_state, axis_idx + 1, feasible):
            continue
        sub = weighted_count(ir, child_state, axis_idx + 1, feasible=feasible, max_k=max_k, memo=memo)
        total += weight * sub
        if max_k is not None and total > max_k:
            total = max_k + 1
            break

    if max_k is not None and total > max_k:
        total = max_k + 1

    if memo is not None:
        memo[key] = total
    return total


def _prefix_feasible(
    ir: DomainIR,
    state: np.ndarray,
    axis_idx: int,
    feasible: Callable[[np.ndarray, int], bool],
) -> bool:
    """Cheap pre-check: if the caller's feasibility predicate rejects a
    state at axis_idx, no descendant can be feasible either (the
    predicate is monotone in the suffix bounds by construction). The
    backward recurrence's pruning uses this to skip infeasible subtrees
    before recursing.
    """
    return feasible(state, axis_idx)


# ---------------------------------------------------------------------------
# Rank / unrank through weighted intervals
# ---------------------------------------------------------------------------


def weighted_unrank(
    ir: DomainIR,
    r: int,
    *,
    feasible: Callable[[np.ndarray, int], bool] | None = None,
    memo: dict[tuple[bytes, int], int] | None = None,
) -> tuple[AxisOption, ...]:
    """Materialize the r-th class member (0-indexed).

    Descends through the weighted child intervals. At each axis, picks
    the fiber containing index `r`, then the member option within the
    fiber (by lexicographic label order), then the subtree position.

    Returns the tuple of `AxisOption` choices (one per axis) that
    identifies the r-th physical loadout in the canonical order.
    """
    state = np.zeros(PROJECTION_DIM, dtype=np.int32)
    choices: list[AxisOption] = []
    for axis_idx in range(len(ir.axes)):
        axis = ir.axes[axis_idx]
        span_total = 0
        chosen_fiber: tuple[AxisOption, ...] | None = None
        chosen_vec: np.ndarray | None = None
        chosen_sub_count: int = 0
        for fiber in axis.identity_fibers:
            weight = len(fiber)
            vec = fiber[0].vec
            child_state = state + vec
            if feasible is not None and not _prefix_feasible(ir, child_state, axis_idx + 1, feasible):
                continue
            sub = weighted_count(ir, child_state, axis_idx + 1, feasible=feasible, memo=memo)
            span = weight * sub
            if r < span_total + span:
                chosen_fiber = fiber
                chosen_vec = vec
                chosen_sub_count = sub
                r = r - span_total
                break
            span_total += span
        if chosen_fiber is None:
            raise IndexError(f"r={r} out of range at axis {axis_idx} (state={state.tolist()})")
        # within the fiber: pick member index, then subtree position
        if chosen_sub_count <= 0:
            raise IndexError(f"empty subtree at axis {axis_idx}")
        fiber_index = r // chosen_sub_count
        sub_index = r % chosen_sub_count
        # fiber members are sorted lexicographically by label (domain_ir._finalize_axis)
        option = chosen_fiber[fiber_index]
        choices.append(option)
        state = state + chosen_vec
        r = sub_index
    # at the terminal axis, r must be 0
    if r != 0:
        raise IndexError(f"residual r={r} at terminal")
    return tuple(choices)


def weighted_rank(
    ir: DomainIR,
    choices: tuple[AxisOption, ...],
    *,
    feasible: Callable[[np.ndarray, int], bool] | None = None,
    memo: dict[tuple[bytes, int], int] | None = None,
) -> int:
    """Inverse of `weighted_unrank`: given a choice per axis, return its
    index in the canonical order.

    For each axis, project the chosen option to its fiber and member
    index, and accumulate the weighted offsets of preceding fibers and
    preceding member options within the chosen fiber.
    """
    state = np.zeros(PROJECTION_DIM, dtype=np.int32)
    r = 0
    for axis_idx, option in enumerate(choices):
        axis = ir.axes[axis_idx]
        for fiber in axis.identity_fibers:
            if option not in fiber:
                vec = fiber[0].vec
                child_state = state + vec
                if feasible is not None and not _prefix_feasible(ir, child_state, axis_idx + 1, feasible):
                    continue
                sub = weighted_count(ir, child_state, axis_idx + 1, feasible=feasible, memo=memo)
                r += len(fiber) * sub
                continue
            # found the fiber: add offsets for preceding members within the fiber
            vec = fiber[0].vec
            child_state = state + vec
            sub = weighted_count(ir, child_state, axis_idx + 1, feasible=feasible, memo=memo)
            member_index = fiber.index(option)
            r += member_index * sub
            state = state + vec
            break
        else:
            raise ValueError(f"option {option!r} not in axis {axis_idx} fibers")
    return r


# ---------------------------------------------------------------------------
# Flat enumeration (the K-ground-truth)
# ---------------------------------------------------------------------------


def flat_enumerate(ir: DomainIR) -> Iterator[tuple[AxisOption, ...]]:
    """Brute-force enumeration of every option tuple, in canonical axis
    order. Used as the ground truth for the weighted recurrence's
    rank/unrank order.

    The per-axis iteration order matches the weighted recurrence's
    canonical order: fibers in first-appearance order, within-fiber
    members lexicographically sorted by label. This is the same order
    `weighted_unrank` produces, so the two enumerations agree index by
    index.

    This is the FLAT enumeration (every option, not every fiber). The
    weighted recurrence's K must equal the count of flat tuples, and
    `weighted_unrank(ir, r)` for `r in range(K)` must equal the r-th
    flat tuple.
    """
    n = len(ir.axes)
    if n == 0:
        yield ()
        return
    head = ir.axes[0]
    # Walk fibers in first-appearance order, within-fiber members
    # lexicographically sorted by label. This matches the order
    # `weighted_unrank` produces, so the two enumerations agree index
    # by index.
    for fiber in head.identity_fibers:
        for opt in fiber:
            for tail in flat_enumerate(_drop_axis(ir, 0)):
                yield (opt,) + tail


def _drop_axis(ir: DomainIR, axis_idx: int) -> DomainIR:
    """Return a copy of `ir` with axis `axis_idx` removed. The flat
    enumeration helper uses this to recurse.
    """
    import dataclasses

    axes = ir.axes[:axis_idx] + ir.axes[axis_idx + 1 :]
    option_mats = ir.option_mats[:axis_idx] + ir.option_mats[axis_idx + 1 :]
    layer_names = ir.layer_names[:axis_idx] + ir.layer_names[axis_idx + 1 :]
    return dataclasses.replace(
        ir,
        axes=axes,
        option_mats=option_mats,
        layer_names=layer_names,
    )


def flat_count(ir: DomainIR) -> int:
    """Brute-force count: product of `len(axis.options)` over all axes.

    For the unconstrained domain (no feasibility predicate), this
    equals `weighted_count(ir, 0, 0)` with `feasible=None`. The test
    asserts equality.
    """
    n = 1
    for axis in ir.axes:
        n *= len(axis.options)
    return n


# ---------------------------------------------------------------------------
# Canonical key for the synthetic domain
# ---------------------------------------------------------------------------


def canonical_key(choices: tuple[AxisOption, ...]) -> tuple:
    """The class-identity key for the synthetic domain.

    Under persistent identities (see CLASS_EQUIVALENCE_RESOLUTION.md
    §3), the canonical key carries the FULL option label per axis — no
    collapse by contribution vector. Two choice tuples are the same
    class member iff their canonical keys are equal as Python tuples.
    """
    return tuple(option.label for option in choices)


# ---------------------------------------------------------------------------
# Synthetic scorer (mirrors the production stat-input contract)
# ---------------------------------------------------------------------------


def synth_score(choices: tuple[AxisOption, ...], pw: np.ndarray = SYNTH_PW) -> int:
    """The synthetic observable for a choice tuple.

    Mirrors the production contract: the scorer reads the 7-dim
    observable projection and returns `gear_power = vec @ pw`. The
    production scorer (`score_stat_arrays_exact_batch`) reads the same
    7 stat keys and applies the same gear-power weighting; the
    synthetic scorer is a minimal CPU reference that exercises the
    contract without the GPU frontier payload.
    """
    vec = np.zeros(PROJECTION_DIM, dtype=np.int32)
    for option in choices:
        vec = vec + option.vec
    return int(vec @ pw.astype(np.int64))


def canonical_scorer_gate(
    choices_a: tuple[AxisOption, ...],
    choices_b: tuple[AxisOption, ...],
    pw: np.ndarray = SYNTH_PW,
) -> bool:
    """The soundness gate: two choice tuples with the same canonical
    key must produce the same score.

    Under persistent identities the canonical key is the full label
    tuple, so two tuples with the same key are the same tuple and
    trivially produce the same score. The gate is asserted on every
    materialized witness as a defensive check against any future
    collapse that breaks the invariant.
    """
    if canonical_key(choices_a) != canonical_key(choices_b):
        return True
    return synth_score(choices_a, pw) == synth_score(choices_b, pw)


# ---------------------------------------------------------------------------
# Synthetic DomainIR builder
# ---------------------------------------------------------------------------


def _make_option(label: tuple, vec_values: tuple[int, ...]) -> AxisOption:
    """Helper: build an AxisOption with the given label and 7-dim vec."""
    assert len(vec_values) == PROJECTION_DIM, f"vec must be {PROJECTION_DIM}-dim, got {len(vec_values)}"
    return AxisOption(label=label, vec=np.array(vec_values, dtype=np.int32))


def _finalize_axis(name: str, options: tuple[AxisOption, ...]) -> Axis:
    """Group options into identity fibers (identical 7-dim vec).

    Mirrors `domain_ir._finalize_axis` but is independent of it so the
    synthetic test does not depend on the production builder's
    internals.
    """
    fibers: dict[bytes, list[AxisOption]] = {}
    order: list[bytes] = []
    for opt in options:
        key = opt.vec.tobytes()
        if key not in fibers:
            fibers[key] = []
            order.append(key)
        fibers[key].append(opt)
    grouped = tuple(
        tuple(sorted(fibers[key], key=lambda o: tuple(str(x) for x in o.label)))
        for key in order
    )
    return Axis(
        name=name,
        options=options,
        identity_fibers=grouped,
        suffix_min=0,
        suffix_max=0,
    )


def build_synth_ir() -> DomainIR:
    """Build a tiny synthetic DomainIR for the weighted-recurrence test.

    Domain: 2 mini slots + 3 gear slots + the team-buff zero option, on
    a single-color (Chill) chart. No upgrades, no gems, no elemental
    axis. The mini slots have a small state space (3 named minis × 2
    levels) so the total K is small. The gear slots have a few options
    each, some with identical contribution vectors (to exercise fibers
    with weight > 1).
    """
    axes: list[Axis] = []

    # Axis 0: team_buff (zero only — no team buff in the synthetic domain)
    tb_options = (
        _make_option(("team_buff", "NONE", ""), (0, 0, 0, 0, 0, 0, 0)),
    )
    axes.append(_finalize_axis("team_buff", tb_options))

    # Axis 1, 2: mini slots (3 names x 2 levels = 6 states + empty).
    # Color stat (Chill) and Perfect Points depend on (name, level).
    # Two distinct (name, level) states can share a contribution vector
    # (e.g. (alpha, 1) and (beta, 2) both contributing (2, 0, 1, 0, 0, 0, 0)).
    # This exercises the fiber weight > 1 case for the mini-identity
    # fiber's CONTRIBUTION vector (the identity stays distinct; the
    # fiber weight multiplies the subtree count).
    mini_states = (
        ("alpha", 1, 1, 0),  # name, level, rank, ascension
        ("alpha", 2, 1, 0),
        ("beta",  1, 1, 0),
        ("beta",  2, 1, 0),
        ("gamma", 1, 1, 0),
        ("gamma", 2, 1, 0),
    )
    # Chill contribution and Perfect Points contribution per state.
    # Two states share a vector by design:
    #   (alpha, 1) -> chill=1, pp=1  (vec: (1, 0, 1, 0, 0, 0, 0))
    #   (beta, 2)  -> chill=1, pp=1  (vec: (1, 0, 1, 0, 0, 0, 0))  -- SAME vec
    # This makes a fiber of size 2 for the mini-identity fiber's
    # contribution vector (identity distinct, weight 2).
    mini_vecs = {
        ("alpha", 1, 1, 0): (1, 0, 1, 0, 0, 0, 0),
        ("alpha", 2, 1, 0): (2, 0, 2, 0, 0, 0, 0),
        ("beta",  1, 1, 0): (1, 0, 0, 0, 0, 0, 0),
        ("beta",  2, 1, 0): (1, 0, 1, 0, 0, 0, 0),  # shares with (alpha, 1)
        ("gamma", 1, 1, 0): (0, 0, 1, 0, 0, 0, 0),
        ("gamma", 2, 1, 0): (3, 0, 1, 0, 0, 0, 0),
    }
    mini_options = [_make_option(("mini", None, None, None, None), (0, 0, 0, 0, 0, 0, 0))]
    for state in mini_states:
        mini_options.append(_make_option(("mini", *state), mini_vecs[state]))
    mini_axis_options = tuple(mini_options)
    # Both mini slots share the same option set.
    axes.append(_finalize_axis("mini:0", mini_axis_options))
    axes.append(_finalize_axis("mini:1", mini_axis_options))

    # Axes 3, 4, 5: gear slots (Hat, Neck, Face). Each slot has an empty
    # option plus a few gear pieces. Some gear pieces share a
    # contribution vector across slots (exercises the upgrade-count-like
    # fiber weight for gear identity, which under persistent identities
    # has weight 1 per identity but a contribution-vector fiber weight
    # > 1).
    gear_options = {
        "Hat": (
            ("gear", "Hat", None),    (0, 0, 0, 0, 0, 0, 0),
            ("gear", "Hat", "H1"),     (1, 0, 0, 0, 0, 0, 0),
            ("gear", "Hat", "H2"),     (0, 0, 1, 0, 0, 0, 0),
            ("gear", "Hat", "H3"),     (1, 0, 0, 0, 0, 0, 0),  # shares vec with H1
        ),
        "Neck": (
            ("gear", "Neck", None),    (0, 0, 0, 0, 0, 0, 0),
            ("gear", "Neck", "N1"),    (0, 0, 1, 0, 0, 0, 0),
            ("gear", "Neck", "N2"),    (2, 0, 0, 0, 0, 0, 0),
        ),
        "Face": (
            ("gear", "Face", None),    (0, 0, 0, 0, 0, 0, 0),
            ("gear", "Face", "F1"),    (1, 0, 1, 0, 0, 0, 0),
            ("gear", "Face", "F2"),    (1, 0, 1, 0, 0, 0, 0),  # shares vec with F1
            ("gear", "Face", "F3"),    (0, 0, 2, 0, 0, 0, 0),
        ),
    }
    for slot in SYNTH_GEAR_SLOTS:
        opts = []
        for i in range(0, len(gear_options[slot]), 2):
            label = gear_options[slot][i]
            vec = gear_options[slot][i + 1]
            opts.append(_make_option(label, vec))
        axes.append(_finalize_axis(f"gear:{slot}", tuple(opts)))

    option_mats = tuple(
        np.stack([opt.vec for opt in axis.options], axis=0).astype(np.int32)
        for axis in axes
    )
    layer_names = tuple(axis.name for axis in axes)
    pw = SYNTH_PW
    return DomainIR(
        axes=tuple(axes),
        pw=pw,
        p_target_axis=-1,
        song_colors=SYNTH_SONG_COLORS,
        option_mats=option_mats,
        layer_names=layer_names,
        upgrade_total_max=0,
        gem_max_per_type=0,
        upgrade_max_per_type=0,
        pet_defs=(),
        upgrade_defs=(),
        mini_rows=(),
        gear_rows=(),
        gem_elemental_colors=(),
    )


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def root_k(
    ir: DomainIR,
    *,
    feasible: Callable[[np.ndarray, int], bool] | None = None,
    max_k: int | None = None,
) -> int:
    """K = C(0, 0): the weighted root count."""
    state = np.zeros(PROJECTION_DIM, dtype=np.int32)
    return weighted_count(ir, state, 0, feasible=feasible, max_k=max_k)


__all__ = [
    "SYNTH_SONG_COLORS",
    "SYNTH_MINI_SLOTS",
    "SYNTH_GEAR_SLOTS",
    "SYNTH_MAX_K",
    "SYNTH_PW",
    "Axis",
    "AxisOption",
    "DomainIR",
    "GEAR_SLOTS",
    "PROJECTION_KEYS",
    "weighted_count",
    "weighted_unrank",
    "weighted_rank",
    "flat_enumerate",
    "flat_count",
    "canonical_key",
    "synth_score",
    "canonical_scorer_gate",
    "build_synth_ir",
    "root_k",
]


# Silence the unused-import linter for re-exports that are part of the
# public API surface.
_ = (Axis, AxisOption, DomainIR, GEAR_SLOTS, PROJECTION_KEYS, Mapping)
