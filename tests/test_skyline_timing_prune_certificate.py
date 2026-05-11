def _certificate_holds(
    *,
    same_signature: bool,
    cur_ft: int,
    cur_ff: int,
    witness_ft: int,
    witness_ff: int,
    w_ft: int,
    w_ff: int,
    w_ov: int,
) -> bool:
    if not same_signature:
        return False
    saved = (cur_ft + cur_ff) - (witness_ft + witness_ff)
    if saved < 0:
        return False
    cur_value = (cur_ft * w_ft) + (cur_ff * w_ff)
    witness_value = (witness_ft * w_ft) + (witness_ff * w_ff)
    compensated_value = witness_value + (saved * w_ov)
    if compensated_value > cur_value:
        return True
    if compensated_value == cur_value:
        if saved > 0:
            return True
        return witness_ft < cur_ft or (witness_ft == cur_ft and witness_ff < cur_ff)
    return False


def test_same_signature_saved_overflow_compensates_timing_element_value():
    assert _certificate_holds(
        same_signature=True,
        cur_ft=5,
        cur_ff=0,
        witness_ft=0,
        witness_ff=0,
        w_ft=6,
        w_ff=0,
        w_ov=12,
    )


def test_different_timing_signature_never_certifies_even_with_better_stats():
    assert not _certificate_holds(
        same_signature=False,
        cur_ft=5,
        cur_ff=0,
        witness_ft=0,
        witness_ff=0,
        w_ft=6,
        w_ff=0,
        w_ov=12,
    )


def test_lost_timing_element_value_must_be_compensated():
    assert not _certificate_holds(
        same_signature=True,
        cur_ft=1,
        cur_ff=0,
        witness_ft=0,
        witness_ff=0,
        w_ft=6,
        w_ff=0,
        w_ov=0,
    )


def test_more_expensive_alias_is_not_a_skip_witness():
    assert not _certificate_holds(
        same_signature=True,
        cur_ft=0,
        cur_ff=0,
        witness_ft=1,
        witness_ff=0,
        w_ft=6,
        w_ff=0,
        w_ov=12,
    )


def test_equal_value_same_cost_uses_canonical_witness_direction():
    assert _certificate_holds(
        same_signature=True,
        cur_ft=1,
        cur_ff=0,
        witness_ft=0,
        witness_ff=1,
        w_ft=3,
        w_ff=3,
        w_ov=0,
    )
    assert not _certificate_holds(
        same_signature=True,
        cur_ft=0,
        cur_ff=1,
        witness_ft=1,
        witness_ff=0,
        w_ft=3,
        w_ff=3,
        w_ov=0,
    )


def test_timing_alias_index_uses_only_single_frontier_signature_cells():
    from gear_optimizer.solver.taichi_gem.api.timeline import _build_timing_alias_witness_index

    sig0 = [[1, 1], [1, 2]]
    sig1 = [[7, 7], [7, 9]]
    frontier_count = [[1, 2], [1, 1]]

    witness_ft, witness_ff = _build_timing_alias_witness_index(sig0, sig1, frontier_count, witness_k=2)

    assert (int(witness_ft[1, 0, 0]), int(witness_ff[1, 0, 0])) == (0, 0)
    assert int(witness_ft[0, 1, 0]) == -1


def _quotient_bit_is_set(bits, base_ft: int, base_ff: int, combo_idx: int) -> bool:
    word = int(bits[base_ft, base_ff, combo_idx >> 5])
    return ((word >> (combo_idx & 31)) & 1) != 0


def test_timing_quotient_combo_order_matches_gpu_table_order():
    from gear_optimizer.solver.taichi_gem.ftff_combos import ftff_combo_arrays as shared_ftff_combo_arrays
    from gear_optimizer.solver.timing_quotient import ftff_combo_arrays

    q_ft, q_ff = ftff_combo_arrays()
    gpu_ft, gpu_ff, _budget_left = shared_ftff_combo_arrays(90)

    assert q_ft.astype(int).tolist() == gpu_ft.astype(int).tolist()
    assert q_ff.astype(int).tolist() == gpu_ff.astype(int).tolist()


def test_timing_quotient_prunes_same_signature_overflow_compensated_combo():
    import numpy as np

    from gear_optimizer.solver.timing_quotient import (
        build_timing_quotient_keep_bits,
        ftff_combo_arrays,
    )

    combo_ft, combo_ff = ftff_combo_arrays()
    combo_00 = int(np.flatnonzero((combo_ft == 0) & (combo_ff == 0))[0])
    combo_10 = int(np.flatnonzero((combo_ft == 1) & (combo_ff == 0))[0])
    sig0 = np.zeros((161, 161), dtype=np.uint64)
    sig1 = np.zeros((161, 161), dtype=np.uint64)
    frontier_count = np.ones((161, 161), dtype=np.int16)

    bits, stats = build_timing_quotient_keep_bits(
        sig0,
        sig1,
        frontier_count,
        np.asarray([[0, 0]], dtype=np.int16),
        w_ft=0,
        w_ff=0,
        w_overflow=12,
    )

    assert _quotient_bit_is_set(bits, 0, 0, combo_00)
    assert not _quotient_bit_is_set(bits, 0, 0, combo_10)
    assert stats["timing_quotient_pruned_records"] > 0


def test_timing_quotient_keeps_combo_when_selected_value_is_not_compensated():
    import numpy as np

    from gear_optimizer.solver.timing_quotient import (
        build_timing_quotient_keep_bits,
        ftff_combo_arrays,
    )

    combo_ft, combo_ff = ftff_combo_arrays()
    combo_10 = int(np.flatnonzero((combo_ft == 1) & (combo_ff == 0))[0])
    sig0 = np.zeros((161, 161), dtype=np.uint64)
    sig1 = np.zeros((161, 161), dtype=np.uint64)
    frontier_count = np.ones((161, 161), dtype=np.int16)

    bits, _stats = build_timing_quotient_keep_bits(
        sig0,
        sig1,
        frontier_count,
        np.asarray([[0, 0]], dtype=np.int16),
        w_ft=6,
        w_ff=0,
        w_overflow=0,
    )

    assert _quotient_bit_is_set(bits, 0, 0, combo_10)


def test_timing_quotient_keeps_multi_frontier_cells():
    import numpy as np

    from gear_optimizer.solver.timing_quotient import (
        build_timing_quotient_keep_bits,
        ftff_combo_arrays,
    )

    combo_ft, combo_ff = ftff_combo_arrays()
    combo_10 = int(np.flatnonzero((combo_ft == 1) & (combo_ff == 0))[0])
    sig0 = np.zeros((161, 161), dtype=np.uint64)
    sig1 = np.zeros((161, 161), dtype=np.uint64)
    frontier_count = np.ones((161, 161), dtype=np.int16)
    frontier_count[3, 0] = 2

    bits, _stats = build_timing_quotient_keep_bits(
        sig0,
        sig1,
        frontier_count,
        np.asarray([[0, 0]], dtype=np.int16),
        w_ft=0,
        w_ff=0,
        w_overflow=12,
    )

    assert _quotient_bit_is_set(bits, 0, 0, combo_10)


