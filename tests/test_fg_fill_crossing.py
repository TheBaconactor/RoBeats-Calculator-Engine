"""Canonical FG fill-crossing oracle + late-Great legality gate.

These pin the SOURCE OF TRUTH for fever activation (``server_fill_crossing``): a placement-aware
walk that reproduces the WebPort ScoreEngine crossing, replacing ``_action_table``'s compressed
``ceil(raw_fever_fill + 0.5*k)`` estimate (which lands one note too far right once Greats are placed
non-uniformly -- the FG late-Great over-report). The gate (``late_great_activation_is_legal``) keeps
a late-Great activation only when the Great is genuinely the fill-completion note.

Synthetic, deterministic, CPU-only. The denominators are chosen off the float knife-edge so the
crossing is unambiguous. The two real anchors this models (validated separately against the live
ScoreEngine, diff < 1e-6 on the denominator):

  * AmongUs (Hard) FG sec-1 -> the fill completes ON a Great -> late-Great LEGAL (delta=0 today).
  * Get Hyped (Hard) FG sec-2 -> 7 body-Greats early shift the fill so a PERFECT completes the bar
    at note 1371; the frontier's late-Great sits at 1372 (post-crossing) -> ILLEGAL (over-report).
"""

import random

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
    canonical_fever_sections,
    fg_canonical_fever_sections,
    fill_prefix_perfect_units,
    late_great_activation_is_legal,
    late_great_activation_prefix,
    late_great_prefix_is_legal,
    perfect_fill_crossing_offset,
    server_fever_end,
    server_fill_crossing,
    server_fill_crossing_fast,
    server_fill_crossing_run,
)

P = False  # Perfect (full fill)
G = True   # Great (half fill)


def test_perfect_only_crossing_matches_the_count():
    # All Perfects, denom 2.9 -> bar 0.345, 0.690, 1.035 -> crosses on the 3rd note (index 2).
    idx, is_great = server_fill_crossing([P, P, P, P], fever_fill_denom=2.9, start=0)
    assert (idx, is_great) == (2, False)


def test_great_is_the_completion_note_is_legal():
    # denom 2.4 -> P=0.4167, G=0.2083.  bar: 0.417, 0.833, +0.208 = 1.042 -> crosses ON the Great
    # at index 2.  A late-Great activation there is genuine: keep it.
    idx, is_great = server_fill_crossing([P, P, G], fever_fill_denom=2.4, start=0)
    assert (idx, is_great) == (2, True)
    assert late_great_activation_is_legal([P, P, G], 2.4, start=0, activation_index=2) is True


def test_perfect_crosses_before_the_late_great_is_illegal():
    # THE BUG SHAPE.  denom 1.9 -> bar 0.526, 1.053 -> a PERFECT completes the bar at index 1.
    # The frontier claims a late-Great activation at index 2 (post-crossing).  Reject it.
    idx, is_great = server_fill_crossing([P, P, G], fever_fill_denom=1.9, start=0)
    assert (idx, is_great) == (1, False)
    assert late_great_activation_is_legal([P, P, G], 1.9, start=0, activation_index=2) is False


def test_get_hyped_shape_early_greats_shift_completion_onto_a_perfect():
    # Scaled Get Hyped sec-2: a fill-start Perfect, then 7 Greats (body-Greats placed early),
    # then Perfects, with a Great planted one note PAST the true crossing (the frontier's 1372).
    # notes[0]=P, notes[1..7]=G (7), notes[8..]=P, and notes[9]=G (the illegal late-Great claim).
    notes = [P] + [G] * 7 + [P, G, P, P]
    # perfect-units: idx0=1.0, 1..7 add 0.5 -> 4.5 at idx7, idx8(P)->5.5, idx9(G)->6.0, idx10->7.0
    # denom 5.5 -> crosses when the running bar reaches full: at idx8 (a PERFECT), NOT idx9.
    idx, is_great = server_fill_crossing(notes, fever_fill_denom=5.5, start=0)
    assert (idx, is_great) == (8, False)
    # frontier's late-Great claim at idx9 is one past the real crossing -> illegal.
    assert late_great_activation_is_legal(notes, 5.5, start=0, activation_index=9) is False
    # ... and the reachable Perfect activation at the true crossing (idx8) is what must be served.


def test_fever_runs_to_end_returns_none():
    # Bar never fills before the chart ends (fever section runs to the last note): no crossing.
    idx, is_great = server_fill_crossing([P, P], fever_fill_denom=100.0, start=0)
    assert idx is None and is_great is False


def test_start_offset_excludes_the_wasted_note():
    # ``start`` is the first accumulating note; a wasted note before it must not be counted.
    # Walking from start=1 ignores notes[0] entirely.
    idx, _ = server_fill_crossing([P, P, P, P], fever_fill_denom=1.9, start=1)
    assert idx == 2  # bar from idx1: 0.526, 1.053 -> crosses at idx2, not idx1


def test_zero_denominator_fails_loud():
    with pytest.raises(ValueError):
        server_fill_crossing([P, P], fever_fill_denom=0.0, start=0)


def test_fast_path_is_oracle_approved_against_the_walk():
    # ORACLE APPROVAL: the O(log n) prefix-sum + searchsorted form must return the IDENTICAL index
    # to the reference walk for every placement/denominator/section-start. Randomized, deterministic
    # (seeded). Real denominators avoid the measure-zero exact-integer float knife-edge, so random
    # non-round denoms exercise the real regime.
    rng = random.Random(20260703)
    for _ in range(4000):
        length = rng.randint(1, 60)
        is_great = [rng.random() < 0.35 for _ in range(length)]
        denom = rng.uniform(0.3, length + 5.0)  # sometimes never crosses (fever to the end)
        start = rng.randint(0, length - 1)
        walk_idx, _ = server_fill_crossing(is_great, denom, start)
        prefix = fill_prefix_perfect_units(is_great)
        fast_idx = server_fill_crossing_fast(prefix, denom, start)
        assert fast_idx == walk_idx, (
            f"fast != walk: len={length} start={start} denom={denom!r} "
            f"walk={walk_idx} fast={fast_idx} greats={is_great}"
        )


def test_fast_path_matches_walk_on_the_gate_shapes():
    # The four gate-defining shapes must agree fast-vs-walk too (they are the ones the gate reads).
    for is_great, denom, start in [
        ([P, P, P, P], 2.9, 0),
        ([P, P, G], 2.4, 0),
        ([P, P, G], 1.9, 0),
        ([P] + [G] * 7 + [P, G, P, P], 5.5, 0),
        ([P, P, P, P], 1.9, 1),
    ]:
        walk_idx, _ = server_fill_crossing(is_great, denom, start)
        fast_idx = server_fill_crossing_fast(fill_prefix_perfect_units(is_great), denom, start)
        assert fast_idx == walk_idx


def test_fast_path_zero_denominator_fails_loud():
    with pytest.raises(ValueError):
        server_fill_crossing_fast(fill_prefix_perfect_units([P, P]), fever_fill_denom=0.0, start=0)


def test_canonical_stepping_multi_section():
    # 20 Perfects, denom 3 -> each section fills in 3 notes. Mock drain: fever lasts 3 notes from
    # activation. Stepping: crossing 2 -> end 5 -> next start 6 -> crossing 8 -> end 11 -> start 12 ->
    # crossing 14 -> end 17 -> start 18 -> from 18 the bar can't reach 3 before note 20 -> stop.
    prefix = fill_prefix_perfect_units([P] * 20)
    secs = fg_canonical_fever_sections(prefix, 3.0, drain_end=lambda a: min(a + 3, 20))
    assert secs == [(2, 5), (8, 11), (14, 17)]


def test_canonical_stepping_reproduces_scoreengine_sections():
    # The two real anchors (fever windows captured from the live WebPort ScoreEngine): the canonical
    # stepping, fed the ScoreEngine's own per-section drain ends, reproduces its activation crossings
    # and section boundaries EXACTLY -- 239/1127 then 1371/2422 (Get Hyped, sec-2 a Perfect crossing,
    # NOT the frontier's 1372), and 95/471 then 565/955 (AmongUs, sec-1 a Great crossing). The
    # placements are the minimal Great sets that produce those crossings (validated against the live
    # denominators, diff < 1e-6). This pins that the stepping's activation == the true crossing.
    def run(n, denom, great_idxs, ends):
        is_great = [i in set(great_idxs) for i in range(n)]
        prefix = fill_prefix_perfect_units(is_great)
        return fg_canonical_fever_sections(prefix, denom, drain_end=lambda a: ends[a], n=n)

    # Get Hyped: 7 body-Greats at 1129..1135 (they shift sec-2's crossing onto the Perfect at 1371).
    gh = run(2429, 239.96320551245213, range(1129, 1136), {239: 1127, 1371: 2422})
    assert gh == [(239, 1127), (1371, 2422)]

    # AmongUs: Greats placed so sec-1 completes ON a Great at 95 (the legal late-Great) and sec-2 on a
    # Perfect at 565. 4 Greats total: three early + the activation Great at 95.
    au = run(955, 93.7960430731101, [1, 2, 3, 95], {95: 471, 565: 955})
    assert au == [(95, 471), (565, 955)]


# --------------------------------------------------------------------------------------------------
# BASE + FG share ONE model. The drain half of the canonical formula (``server_fever_end``) and the
# base (all-Perfect) special case of the stepping. The base historical path searched the NOMINAL
# timestamps for the drain end and so under-counted boundary notes the player can hit EARLY into the
# window (the base under-report, e.g. Bopeebo at extreme FeverFill); the canonical drain searches the
# floor envelope (as FG already does), recovering exactly those reachable fever notes.
# --------------------------------------------------------------------------------------------------


def test_server_fever_end_floor_envelope_counts_early_hittable_boundary():
    # Fever activates at note 1 (hit late at 1.05); window is [1.05, 1.05 + 2.90) = [1.05, 3.95).
    # Note 4's NOMINAL time is 4.00 (>= 3.95 -> excluded) but its earliest legal hit (floor) is 3.90
    # (< 3.95 -> reachable INTO the window). The floor search counts it; the nominal search drops it.
    nominal = np.array([0.00, 1.00, 2.00, 3.00, 4.00, 5.00], dtype=np.float32)
    floor = np.array([0.00, 1.00, 2.00, 3.00, 3.90, 5.00], dtype=np.float32)
    end_floor = server_fever_end(floor, activation_hit_time=1.05, fever_time_sec=2.90, activation=1)
    end_nominal = server_fever_end(nominal, activation_hit_time=1.05, fever_time_sec=2.90, activation=1)
    assert end_floor == 5  # note 4 (index 4) is fevered -> first non-fever note is index 5
    assert end_nominal == 4  # nominal drops note 4 -> the base under-report, one note per section
    assert end_floor - end_nominal == 1


def test_server_fever_end_covers_activation_and_clamps_to_n():
    ts = np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float32)
    # Window shorter than the gap to the next note: fever still covers at least its own activation.
    assert server_fever_end(ts, activation_hit_time=1.0, fever_time_sec=0.1, activation=1) == 2
    # Window past the last note: end clamps to n (never runs off the array).
    assert server_fever_end(ts, activation_hit_time=1.0, fever_time_sec=100.0, activation=1) == 4


def test_base_all_perfect_stepping_matches_the_count():
    # BASE is the Perfect-only special case of the same stepping. 20 Perfects, denom 3.0: first
    # section fills in ceil(3)-1 = 2 notes (no wasted note) -> crossing at index 2; later sections
    # reset after the wasted note. Mock drain: fever lasts 3 notes.
    prefix = fill_prefix_perfect_units([P] * 20)
    secs = canonical_fever_sections(prefix, 3.0, drain_end=lambda a: min(a + 3, 20))
    assert secs == [(2, 5), (8, 11), (14, 17)]
    assert secs[0][0] == 2  # first activation == ceil(denom) - 1 (first section has no wasted note)


def test_canonical_fever_sections_is_the_unified_alias():
    # The FG call sites + the older tests use ``fg_canonical_fever_sections``; base and FG now share
    # this ONE stepping. The names must be the same object (no divergent second implementation).
    assert fg_canonical_fever_sections is canonical_fever_sections


# --------------------------------------------------------------------------------------------------
# O(1) production crossing. The production placement is always Perfects + one CONTIGUOUS forced-Great
# run, so ``server_fill_crossing_run`` computes the crossing in O(1) (no per-candidate O(n) prefix, no
# O(log n) search) — the cost of the old buggy ``state_i + ceil(...)``, but correct. These pin it
# bit-exact to the walk (ground truth) and the searchsorted form.
# --------------------------------------------------------------------------------------------------


def test_run_form_three_regions_and_base():
    # region 1 (Perfect before the run): denom 2.9, run at 5.. -> crosses at index 2, a Perfect.
    assert server_fill_crossing_run(0, 5, 3, 2.9, 20) == (2, False)
    # region 2 (Great inside the run): denom 2.4, run [2,3) -> P,P then the Great tips it at index 2.
    assert server_fill_crossing_run(0, 2, 1, 2.4, 20) == (2, True)
    # region 3 (Perfect after the run): denom 1.9, run [2,3) -> a Perfect crosses at index 1 first.
    assert server_fill_crossing_run(0, 2, 1, 1.9, 20) == (1, False)
    # base (k == 0): pure-Perfect crossing at start + ceil(denom) - 1.
    assert server_fill_crossing_run(0, 99, 0, 2.9, 20) == (2, False)
    # never fills before n -> None.
    assert server_fill_crossing_run(0, 99, 0, 100.0, 5) == (None, False)


def test_run_form_get_hyped_rejects_the_phantom_in_O1():
    # Get Hyped sec-2: start 1128, forced-Great run [1129, 1136) (k=7), denom 239.9632. The O(1) form
    # lands region 3 -> (1135) + ceil(235.4632) = 1371, a PERFECT. So the late-Great @1372 the frontier
    # claimed is one past the crossing -> phantom, rejected without any search.
    idx, is_great = server_fill_crossing_run(1128, 1129, 7, 239.96320560711627, 2430)
    assert (idx, is_great) == (1371, False)


def test_run_form_is_oracle_approved_against_walk_and_fast():
    # ORACLE APPROVAL of the O(1) form: for every contiguous-run placement it must return the IDENTICAL
    # (index, is_great) as the reference walk AND the searchsorted form. Randomized, seeded, incl. the
    # clip edges (run starting before ``start`` / extending past ``n``).
    rng = random.Random(7030706)
    for _ in range(6000):
        n = rng.randint(4, 400)
        s = rng.randint(0, n - 2)
        roll = rng.random()
        if roll < 0.15:
            g0, k = n, 0
        elif roll < 0.30:
            g0 = rng.randint(0, s)
            k = rng.randint(0, n - g0 + 8)
        else:
            g0 = rng.randint(s, n - 1)
            k = rng.randint(0, n - g0 + 8)
        denom = rng.uniform(0.3, (n - s) * 0.97) + rng.uniform(0.11, 0.39)

        is_great = [g0 <= i < g0 + k for i in range(n)]
        walk = server_fill_crossing(is_great, denom, s, n=n)
        run = server_fill_crossing_run(s, g0, k, denom, n)
        fast = server_fill_crossing_fast(fill_prefix_perfect_units(is_great), denom, s, n=n)
        assert run == walk, f"run != walk: n={n} s={s} g0={g0} k={k} denom={denom!r} {run} {walk}"
        assert (run[0] if run[0] is not None else -1) == (fast if fast is not None else -1)


def test_run_form_zero_denominator_fails_loud():
    with pytest.raises(ValueError):
        server_fill_crossing_run(0, 2, 1, 0.0, 20)


def test_late_great_prefix_gate_pins_the_real_anchors():
    # Get Hyped sec-2, live raw 239.9632; later section (one wasted note), activation offset fill=245.
    raw = 239.96320551245213
    # 7-Great prefix (doc-era served / phantom placement): a Perfect crosses first -> ILLEGAL.
    assert late_great_prefix_is_legal(245, 7, raw, first=False) is False
    # 9-Great prefix: the crossing IS the activation Great -> LEGAL (no regression on real late-Greats).
    assert late_great_prefix_is_legal(245, 9, raw, first=False) is True


def test_late_great_prefix_gate_matches_the_walk_oracle():
    # The O(1) search gate must equal the placement walk (late_great_activation_is_legal) for every
    # production placement (Perfects + a prefix-Great run + the activation Great), base and later
    # sections. Randomized, deterministic; skip the measure-zero integer knife-edge both forms warn on.
    rng = random.Random(101)
    for _ in range(5000):
        first = rng.random() < 0.5
        prefix = rng.randint(0, 12)
        pb = rng.randint(0, 40)  # Perfects between the run and the activation Great
        fill = prefix + pb + (0 if first else 1)
        raw = rng.uniform(0.3, prefix * 0.5 + pb + 3.0)
        if raw == round(raw):
            continue
        start = 0 if first else rng.randint(1, 20)
        a = start + fill - (0 if first else 1)  # activation Great position
        n = a + 3
        ig = [P] * n
        for i in range(start, start + prefix):
            ig[i] = G
        ig[a] = G
        assert late_great_prefix_is_legal(fill, prefix, raw, first) == late_great_activation_is_legal(
            ig, raw, start=start, activation_index=a, n=n
        ), (fill, prefix, raw, first, start, a)


def test_consolidated_owners_match_the_legacy_inline_formulas():
    # The DRY consolidation routed _action_table's fill and both the search compaction + reconstruct
    # mirror's late-Great math through perfect_fill_crossing_offset / late_great_activation_prefix.
    # Pin those single owners to the EXACT legacy inline formulas they replaced, so a future edit to a
    # helper that diverges from the shipped (bit-exact-verified) behavior is caught here. The
    # first-section `prefix == fill` placement is deliberately IN scope: the P/G brute-force oracle
    # realizes it (pure run, activation Great crossing on the run's end), so a cap to `fill - 1`
    # under-reports (record 16.28's cap direction was refuted; the fixture phantoms were the
    # region-2 normal edges, gated by perfect_crossing_is_region3 instead).
    from math import ceil

    for raw_i in range(20, 6000, 11):
        raw = raw_i / 20.0  # 1.0 .. 300.0 with fractional denominators
        for k in range(0, min(60, int(ceil(raw)) + 2)):
            legacy_fill = int(ceil(raw + 0.5 * k))
            assert perfect_fill_crossing_offset(raw, k, first=False) == legacy_fill
            assert perfect_fill_crossing_offset(raw, k, first=True) == max(0, legacy_fill - 1)
            for first in (False, True):
                fill = perfect_fill_crossing_offset(raw, k, first=first)
                wasted = 0 if first else 1
                legacy_prefix = min(max(0, k - 1), max(0, fill - wasted))
                legacy = (
                    legacy_prefix
                    if (k > 0 and late_great_prefix_is_legal(fill, legacy_prefix, raw, first=first))
                    else None
                )
                assert late_great_activation_prefix(fill, k, first=first, fever_fill_denom=raw) == legacy, (
                    raw, k, first, fill,
                )
