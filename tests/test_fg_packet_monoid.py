from __future__ import annotations

import numpy as np
import pytest

from tests.parity.force_greats.fg_frontier_kernel_parity import build_kernel_args
from tests.parity.force_greats.fg_packet_monoid import packet_body_dp, reference_body_dp


@pytest.mark.parametrize(
    ("raw_fever_fill", "non_fever_base", "real_fever_time", "use_forced_great_timing"),
    [
        (4.25, 12, 0.45, False),
        (7.50, 20, 0.72, True),
        (21.25, 44, 1.35, True),
    ],
)
def test_packet_monoid_body_dp_matches_direct_reference(
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    use_forced_great_timing: bool,
) -> None:
    timestamps = np.asarray([idx * 0.095 for idx in range(180)], dtype=np.float32)
    great_offsets = np.asarray([0.035 if idx % 11 == 0 else 0.0 for idx in range(180)], dtype=np.float32)
    args = build_kernel_args(
        timestamps=timestamps,
        great_candidate_timestamps=timestamps + great_offsets,
        raw_fever_fill=raw_fever_fill,
        non_fever_base=non_fever_base,
        real_fever_time=real_fever_time,
        use_forced_great_timing=use_forced_great_timing,
    )

    direct = reference_body_dp(args)
    packet, stats = packet_body_dp(args)

    assert packet == direct
    assert stats.max_interval_width >= stats.max_body_width


def test_packet_monoid_keeps_activation_late_great_witness_exact() -> None:
    timestamps = np.asarray([idx * 0.10 for idx in range(120)], dtype=np.float32)
    great_candidates = timestamps.copy()
    great_candidates[102] = np.float32(float(timestamps[102]) + 0.095)
    args = build_kernel_args(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        raw_fever_fill=1.25,
        non_fever_base=60,
        real_fever_time=0.32,
        use_forced_great_timing=True,
    )

    direct = reference_body_dp(args)
    packet, _stats = packet_body_dp(args)

    assert packet == direct
    assert any(point[2] > 0 for frontier in packet.values() for point in frontier)
