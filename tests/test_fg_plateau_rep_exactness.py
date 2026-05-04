from fractions import Fraction

from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch
from gear_optimizer.helpers.song_helpers.force_greats import result_application


def _ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def _fp_target(raw_fill: Fraction, forced_count: int) -> int:
    return _ceil_fraction(raw_fill + Fraction(forced_count, 2)) - _ceil_fraction(raw_fill)


def test_current_formula_has_at_most_two_forced_count_representatives_per_fp_target():
    for whole in range(0, 20):
        for frac_num in range(0, 20):
            raw_fill = Fraction((whole * 20) + frac_num, 20)
            buckets: dict[int, list[int]] = {}
            for forced_count in range(0, 80):
                buckets.setdefault(_fp_target(raw_fill, forced_count), []).append(forced_count)

            assert all(len(reps) <= 2 for reps in buckets.values())


def test_plateau_rep_expansion_emits_every_rep_mask_for_bounded_sections():
    stride = int(gpu_dispatch.FG_PLATEAU_REP_STRIDE)
    expected = {
        (1 + (stride if a else 0), 2 + (stride if b else 0), 3 + (stride if c else 0))
        for a in (0, 1)
        for b in (0, 1)
        for c in (0, 1)
    }

    rows = gpu_dispatch._expand_plateau_rep_counts_list([(1, 2, 3)], n_sections=3)
    assert set(rows) == expected


def test_plateau_rep_expansion_filters_invalid_k1_fp_targets():
    stride = int(gpu_dispatch.FG_PLATEAU_REP_STRIDE)
    valid_fps = [{1}, {2}, {3}]

    rows = gpu_dispatch._expand_plateau_rep_counts_list(
        [(1, 2, 3)],
        n_sections=3,
        section_k1_valid_fps=valid_fps,
    )

    expected = {
        (1, 2, 3),  # rep=0,0,0
        (1 + stride, 2, 3),  # rep=1,0,0
        (1, 2 + stride, 3),  # rep=0,1,0
        (1, 2, 3 + stride),  # rep=0,0,1
        (1 + stride, 2 + stride, 3),  # rep=1,1,0
        (1 + stride, 2, 3 + stride),  # rep=1,0,1
        (1, 2 + stride, 3 + stride),  # rep=0,1,1
        (1 + stride, 2 + stride, 3 + stride),  # rep=1,1,1
    }

    assert set(rows) == expected


def test_plateau_rep_expansion_drops_rows_with_invalid_reps():
    stride = int(gpu_dispatch.FG_PLATEAU_REP_STRIDE)
    # Section 0: fp=5 has valid k1; section 1: fp=2 does NOT have valid k1.
    valid_fps = [{5}, set()]

    rows = gpu_dispatch._expand_plateau_rep_counts_list(
        [(5, 2)],
        n_sections=2,
        section_k1_valid_fps=valid_fps,
    )

    expected = {
        (5, 2),  # rep=0,0
        (5 + stride, 2),  # rep=1,0  (section 1 rep skipped because invalid)
    }

    assert set(rows) == expected


def test_plateau_rep_expansion_empty_valid_fps_keeps_base_only():
    stride = int(gpu_dispatch.FG_PLATEAU_REP_STRIDE)
    valid_fps = [set(), set()]

    rows = gpu_dispatch._expand_plateau_rep_counts_list(
        [(1, 2)],
        n_sections=2,
        section_k1_valid_fps=valid_fps,
    )

    assert set(rows) == {(1, 2)}


def test_has_valid_k1_rep_detects_two_representatives():
    assert gpu_dispatch._has_valid_k1_rep(33.3, 34, 2, 34)
    # p=0, raw_fill=33.3: k=0 and k=1 both map to p=0 (same plateau)
    assert gpu_dispatch._has_valid_k1_rep(33.3, 34, 0, 34)
    # p=0, raw_fill=33.6: k=1 maps to p=1 (different plateau)
    assert not gpu_dispatch._has_valid_k1_rep(33.6, 34, 0, 34)


def test_has_valid_k1_rep_rejects_at_cap():
    assert not gpu_dispatch._has_valid_k1_rep(10.0, 10, 9, 10)


def test_fp_target_materialization_selects_same_plateau_representative_only_when_valid():
    class _TwoRepScorer:
        @staticmethod
        def get_fever_params(_ft_stat, _ff_stat):
            return (34, 0.0, 0, 33.3)

    class _OneRepScorer:
        @staticmethod
        def get_fever_params(_ft_stat, _ff_stat):
            return (34, 0.0, 0, 33.6)

    base_stats = {"Fever Time": 0, "Fever Fill Rate": 0}

    assert result_application.fp_targets_to_forced_counts([2], [0], base_stats, 0, 0, _TwoRepScorer()) == [4]
    assert result_application.fp_targets_to_forced_counts([2], [1], base_stats, 0, 0, _TwoRepScorer()) == [5]

    # raw_fill=33.6 has no k=1 representative for fp=0, so the rep flag must collapse to k=0.
    assert result_application.fp_targets_to_forced_counts([0], [1], base_stats, 0, 0, _OneRepScorer()) == [0]


def _ref_sig_is_dominated(sig_a, sig_b):
    """CPU reference for the GPU _fg_sig_is_dominated check."""
    # fever head mask superset: (ma & mb) == mb
    fever_dominates = True
    for w in range(4):
        ma = sig_a[w] & 0xFFFFFFFF
        mb = sig_b[w] & 0xFFFFFFFF
        if (ma & mb) != mb:
            fever_dominates = False

    # forced head mask subset: (ma & ~mb) == 0
    forced_dominates = True
    for w in range(4):
        ma = sig_a[6 + w] & 0xFFFFFFFF
        mb = sig_b[6 + w] & 0xFFFFFFFF
        if (ma & ~mb) != 0:
            forced_dominates = False

    body_fever_ok = sig_a[4] >= sig_b[4]
    body_normal_ok = sig_a[5] <= sig_b[5]
    forced_body_ok = sig_a[10] <= sig_b[10]

    # Require strict improvement on at least one dimension
    all_equal = True
    for w in range(4):
        if sig_a[w] != sig_b[w]:
            all_equal = False
        if sig_a[6 + w] != sig_b[6 + w]:
            all_equal = False
    if sig_a[4] != sig_b[4]:
        all_equal = False
    if sig_a[5] != sig_b[5]:
        all_equal = False
    if sig_a[10] != sig_b[10]:
        all_equal = False

    return fever_dominates and forced_dominates and body_fever_ok and body_normal_ok and forced_body_ok and not all_equal


def test_sig_dominance_superset_mask_and_subset_forced():
    sig_a = [0] * 11
    sig_b = [0] * 11
    # A: fever bits 0 and 5 set, 1 body fever, 1 body normal, 0 forced
    sig_a[0] = (1 << 0) | (1 << 5)
    sig_a[4] = 1
    sig_a[5] = 1

    # B: fever bit 0 only, 0 body fever, 1 body normal, 1 forced head
    sig_b[0] = 1 << 0
    sig_b[4] = 0
    sig_b[5] = 1
    sig_b[6] = 1 << 3
    sig_b[10] = 1

    assert _ref_sig_is_dominated(sig_a, sig_b)
    assert not _ref_sig_is_dominated(sig_b, sig_a)


def test_sig_dominance_equal_signatures_not_dominated():
    sig_a = [0] * 11
    sig_a[0] = 0xFF
    sig_a[4] = 5
    sig_a[5] = 3
    sig_a[6] = 0x0F

    sig_b = list(sig_a)
    assert not _ref_sig_is_dominated(sig_a, sig_b)
    assert not _ref_sig_is_dominated(sig_b, sig_a)


def test_sig_dominance_more_fever_but_more_forced():
    sig_a = [0] * 11
    sig_b = [0] * 11
    # A: more fever but also more forced → partial dominance fails
    sig_a[0] = 0xFF
    sig_a[4] = 10
    sig_a[5] = 2
    sig_a[6] = 0x0F
    sig_a[10] = 5

    # B: less fever but less forced
    sig_b[0] = 0x0F
    sig_b[4] = 5
    sig_b[5] = 5
    sig_b[6] = 0x03
    sig_b[10] = 2

    assert not _ref_sig_is_dominated(sig_a, sig_b)
    assert not _ref_sig_is_dominated(sig_b, sig_a)


def test_sig_dominance_body_count_comparison():
    sig_a = [0] * 11
    sig_b = [0] * 11
    # Same masks, but A has more body fever and fewer forced body
    sig_a[4] = 10  # more body fever
    sig_a[5] = 2   # fewer body normal
    sig_a[10] = 3  # fewer forced body

    sig_b[4] = 5
    sig_b[5] = 7
    sig_b[10] = 8

    assert _ref_sig_is_dominated(sig_a, sig_b)
    assert not _ref_sig_is_dominated(sig_b, sig_a)
