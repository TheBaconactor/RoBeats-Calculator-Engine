import numpy as np

from gear_optimizer.solver.hit_simulation import simulate_perfect_hit_timestamps


def test_simulate_perfect_hit_timestamps_is_deterministic_and_monotonic():
    # Includes a chord (duplicate timestamp) and a held-tail note (type=3).
    timestamps = np.array([0.000, 0.050, 0.100, 0.100, 0.120], dtype=np.float64)
    note_types = np.array([1, 1, 1, 1, 3], dtype=np.int16)

    out1, dbg1 = simulate_perfect_hit_timestamps(timestamps, note_types, seed=123)
    out2, dbg2 = simulate_perfect_hit_timestamps(timestamps, note_types, seed=123)

    assert np.array_equal(out1, out2)
    assert dbg1 == dbg2

    # Monotonic non-decreasing in integer ms (server-aligned).
    out_ms = np.floor(out1 * 1000.0 + 1e-6).astype(np.int64)
    assert np.all(np.diff(out_ms) >= 0)

    # Chord notes share the same sampled hit-time.
    assert out_ms[2] == out_ms[3]


def test_simulate_perfect_hit_timestamps_respects_head_and_tail_windows():
    timestamps = np.array([1.000, 1.050, 1.100], dtype=np.float64)
    note_types = np.array([1, 3, 1], dtype=np.int16)  # middle note is held tail

    out, dbg = simulate_perfect_hit_timestamps(timestamps, note_types, seed=999)
    assert dbg["forced_monotonic"] == 0

    base_ms = np.floor(timestamps * 1000.0 + 1e-6).astype(np.int64)
    out_ms = np.floor(out * 1000.0 + 1e-6).astype(np.int64)
    delta = out_ms - base_ms

    # Head perfect window at stat=0: [-20, +40]ms
    assert -20 <= int(delta[0]) <= 40
    assert -20 <= int(delta[2]) <= 40

    # Tail window is wider by x2: [-40, +80]ms
    assert -40 <= int(delta[1]) <= 80
