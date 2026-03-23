import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = pytest.mark.gpu


def _unpack_head_bits(bits_u32: np.ndarray, head_len: int) -> np.ndarray:
    bits = np.asarray(bits_u32, dtype=np.uint32).reshape(-1)
    n = int(max(0, head_len))
    out = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        w = i >> 5
        b = i & 31
        if (int(bits[w]) >> b) & 1:
            out[i] = True
    return out


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ceiling_timeline_is_upper_bound_over_mc_samples(monkeypatch) -> None:
    """
    Ceiling mode should be a deterministic upper envelope over feasible Perfect-window hit timings.

    This test compares GPU ceiling output to a Monte Carlo best-of-N over Perfect hit timestamps
    (same chord grouping + monotone event-time rule) on a small synthetic chart.

    If ceiling ever scores lower than the best MC sample, we are under-approximating the ceiling.
    """
    from math import ceil

    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.hit_simulation import (
        compute_fever_timeline_signature,
        generate_perfect_hit_times_ms,
        prepare_perfect_hit_simulation,
    )
    from gear_optimizer.solver.scoring_core import fast_calculate_score
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    init_taichi()

    # Build a chart directly in integer ms space (robust to float32 boundary issues).
    n_notes = 360
    gap_ms = 27
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    # Include held-tail notes so the carry window includes (+80) values.
    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::13] = np.int16(3)

    calc_song = {
        "metadata": {
            "Song Name": "CeilingHitSim MC Upper Bound",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(n_notes),
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": note_types,
        },
    }

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        # Taichi runtime expects these core lookup tables to be present.
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

    # Pick a cell that tends to have multiple fever activations on this synthetic chart.
    ft_idx = 120
    ff_idx = 30

    # GPU ceiling result (one-shot).
    monkeypatch.setenv("GPU_TIMELINE_CEILING_HITSIM", "1")
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

    head_len_grid = np.asarray(gpu_fields.grid_head_len.to_numpy()[0], dtype=np.int32)
    bits_grid = np.asarray(gpu_fields.grid_fever_masks_bits.to_numpy()[0], dtype=np.uint32)
    body_fever_grid = np.asarray(gpu_fields.grid_count_body_fever.to_numpy()[0], dtype=np.int32)
    body_normal_grid = np.asarray(gpu_fields.grid_count_body_normal.to_numpy()[0], dtype=np.int32)

    head_len = int(head_len_grid[ft_idx, ff_idx])
    head_mask = _unpack_head_bits(bits_grid[ft_idx, ff_idx, :], head_len)
    body_fever = int(body_fever_grid[ft_idx, ff_idx])
    body_normal = int(body_normal_grid[ft_idx, ff_idx])

    base = 10000.0
    combo = 2.6
    fever = 5.25
    ceiling_score = int(fast_calculate_score(base, combo, fever, head_mask, body_fever, body_normal))

    # Monte Carlo: best-of-N Perfect event time samples (same monotone carry model).
    prepared = prepare_perfect_hit_simulation(
        timestamps,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )

    non_fever_cas = float(n_notes) * 0.333
    non_fever_base = int(ceil(non_fever_cas * float(ref_arrays["Fever Fill Rate"][ff_idx])))
    non_fever_base = max(1, non_fever_base)

    fever_time_cas = float(calc_song["metadata"]["Last Note Time"]) * 0.15 + 0.15
    real_fever_time_ms = int(ceil(fever_time_cas * float(ref_arrays["Fever Time"][ft_idx]) * 1000.0))
    real_fever_time_ms = max(0, real_fever_time_ms)

    best_mc_score = None
    seeds = 200
    for s in range(1, int(seeds) + 1):
        event_ms = generate_perfect_hit_times_ms(prepared, seed=int(s))
        _, fever_mask_head, count_body_fever, count_body_normal = compute_fever_timeline_signature(
            event_ms,
            non_fever_base=non_fever_base,
            real_fever_time_ms=real_fever_time_ms,
        )
        score = int(
            fast_calculate_score(
                base,
                combo,
                fever,
                np.asarray(fever_mask_head, dtype=np.bool_),
                int(count_body_fever),
                int(count_body_normal),
            )
        )
        if best_mc_score is None or score > int(best_mc_score):
            best_mc_score = int(score)

    assert best_mc_score is not None
    assert ceiling_score >= int(best_mc_score), (
        f"ceiling<{seeds}-sample MC best: ceiling={ceiling_score} mc={best_mc_score}"
    )
