from __future__ import annotations

import numpy as np

from tests.parity.timing_response_antichain import timing_response_antichain_keep_mask


def test_timing_response_antichain_drops_only_same_pack_covered_spends() -> None:
    packs = np.array([1, 1, 1, 2, 2, 2], dtype=np.int32)
    remaining = np.array([8, 7, 6, 4, 4, 3], dtype=np.int32)
    lane_value = np.array([10, 9, 11, 4, 5, 4], dtype=np.int32)

    keep = timing_response_antichain_keep_mask(
        packs=packs,
        remaining=remaining,
        lane_value=lane_value,
    )

    assert keep.tolist() == [True, False, True, False, True, False]
    for idx, kept in enumerate(keep.tolist()):
        if kept:
            continue
        covering = np.flatnonzero(
            keep
            & (packs == packs[idx])
            & (remaining >= remaining[idx])
            & (lane_value >= lane_value[idx])
        )
        assert covering.size > 0


def test_timing_response_antichain_keeps_cross_pack_points() -> None:
    packs = np.array([1, 2], dtype=np.int32)
    remaining = np.array([8, 7], dtype=np.int32)
    lane_value = np.array([10, 9], dtype=np.int32)

    keep = timing_response_antichain_keep_mask(
        packs=packs,
        remaining=remaining,
        lane_value=lane_value,
    )

    assert keep.tolist() == [True, True]


def test_timing_response_antichain_rejects_mismatched_vectors() -> None:
    try:
        timing_response_antichain_keep_mask(
            packs=np.array([1, 1], dtype=np.int32),
            remaining=np.array([8], dtype=np.int32),
            lane_value=np.array([10, 9], dtype=np.int32),
        )
    except ValueError as exc:
        assert "same shape" in str(exc)
    else:
        raise AssertionError("expected shape mismatch to fail clearly")
