from __future__ import annotations


def test_gear_cpu_reference_keeps_identical_stats_in_different_ff_cells() -> None:
    from tests.parity.exact_skyline import _global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference

    states = {
        (0, 0, 0, 0): [
            (0, 100, 101),
            (1, 100, 102),
        ],
    }

    _stats, points, codes = _global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference(states)

    assert {tuple(int(x) for x in row.tolist()) for row in points} == {
        (0, 0, 0, 0, 0, 100),
        (0, 0, 0, 0, 1, 100),
    }
    assert {int(x) for x in codes.tolist()} == {101, 102}


def test_gear_cpu_reference_prunes_only_inside_fixed_timing_cell() -> None:
    from tests.parity.exact_skyline import _global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference

    states = {
        (0, 0, 0, 0): [
            (0, 100, 101),
            (1, 100, 102),
        ],
        (0, 1, 0, 0): [
            (0, 100, 103),
        ],
    }

    _stats, points, codes = _global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference(states)

    assert {tuple(int(x) for x in row.tolist()) for row in points} == {
        (0, 0, 0, 0, 1, 100),
        (0, 1, 0, 0, 0, 100),
    }
    assert {int(x) for x in codes.tolist()} == {102, 103}
