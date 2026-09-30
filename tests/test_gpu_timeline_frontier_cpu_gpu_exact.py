from tests.curves_support import synthetic_curves
import numpy as np
import pytest
from tests.songs_support import make_song


pytestmark = pytest.mark.gpu


def _cpu_frontier_payload(song, curves):
    from gear_optimizer.solver.timeline_exact_frontier import build_timeline_frontier_grid_payload

    return build_timeline_frontier_grid_payload(
        song_slot=0,
        total_notes=song.chart.total_notes,
        long_notes=song.chart.long_notes,
        last_note_time=song.chart.last_note_time,
        timestamps=song.chart.timestamps,
        perfect_candidate_timestamps=song.perfect_candidates,
        perfect_floor_timestamps=song.perfect_floor,
        lanes=song.chart.lanes,
        ref_ft=curves.f32["Fever Time"],
        ref_ff=curves.f32["Fever Fill Rate"],
    )


def test_gpu_timeline_frontier_upload_matches_cpu_payload() -> None:
    """
    Ensure the uploaded GPU fields match the exact CPU frontier payload on a synthetic chart.
    """
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    init_taichi()

    # Integer-ms chart to avoid float boundary issues.
    n_notes = 420
    gap_ms = 27
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::13] = np.int16(3)  # held tails widen carry window

    song = make_song(timestamps, name="TimelineFrontier CPU/GPU Exact", primary="Beat", note_types=note_types)

    rows = int(MAX_STAT) + 1
    curves = synthetic_curves({
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.2, 2.2, rows, dtype=np.float32),
        "Fever Time": np.linspace(0.8, 2.6, rows, dtype=np.float32),
    })

    cells = [(10, 10), (80, 80), (160, 40), (120, 30)]

    _prebuilt = build_or_load_timeline_frontier_payload(song, curves)
    precompute_timeline_gpu(song, curves, song_slot=0, prebuilt_frontier=_prebuilt)
    cpu_payload = _cpu_frontier_payload(song, curves)

    head_len_grid = np.asarray(gpu_fields.grid_head_len.to_numpy()[0], dtype=np.int32)
    bits_grid = np.asarray(gpu_fields.grid_fever_masks_bits.to_numpy()[0], dtype=np.uint32)
    body_fever_grid = np.asarray(gpu_fields.grid_count_body_fever.to_numpy()[0], dtype=np.int32)
    body_normal_grid = np.asarray(gpu_fields.grid_count_body_normal.to_numpy()[0], dtype=np.int32)
    gap_grid = np.asarray(gpu_fields.grid_gap.to_numpy()[0], dtype=np.int32)
    act_grid = np.asarray(gpu_fields.grid_fever_activations.to_numpy()[0], dtype=np.int32)
    frontier_count_grid = np.asarray(gpu_fields.grid_frontier_count.to_numpy()[0], dtype=np.int32)
    frontier_offset_grid = np.asarray(gpu_fields.grid_frontier_offset.to_numpy()[0], dtype=np.int32)

    for ft_idx, ff_idx in cells:
        head_len = int(head_len_grid[ft_idx, ff_idx])
        bits = tuple(int(x) for x in bits_grid[ft_idx, ff_idx, :].tolist())
        body_fever = int(body_fever_grid[ft_idx, ff_idx])
        body_normal = int(body_normal_grid[ft_idx, ff_idx])
        gap = int(gap_grid[ft_idx, ff_idx])
        acts = int(act_grid[ft_idx, ff_idx])
        frontier_count = int(frontier_count_grid[ft_idx, ff_idx])
        frontier_offset = int(frontier_offset_grid[ft_idx, ff_idx])
        gpu_sig = (head_len, bits, body_fever, body_normal, acts, gap, frontier_count, frontier_offset)

        cpu_count = int(cpu_payload.grid_frontier_count[0, ft_idx, ff_idx])
        cpu_offset = int(cpu_payload.grid_frontier_offset[0, ft_idx, ff_idx])
        cpu_head = int(cpu_payload.grid_head_len[0, ft_idx, ff_idx])
        cpu_bits = tuple(int(x) for x in cpu_payload.grid_fever_masks_bits[0, ft_idx, ff_idx, :].tolist())
        cpu_body_fever = int(cpu_payload.grid_count_body_fever[0, ft_idx, ff_idx])
        cpu_body_normal = int(cpu_payload.grid_count_body_normal[0, ft_idx, ff_idx])
        cpu_gap = int(cpu_payload.grid_gap[0, ft_idx, ff_idx])
        cpu_acts = int(cpu_payload.grid_fever_activations[0, ft_idx, ff_idx])
        cpu_sig = (cpu_head, cpu_bits, cpu_body_fever, cpu_body_normal, cpu_acts, cpu_gap, cpu_count, cpu_offset)

        assert gpu_sig == cpu_sig, (
            f"CPU/GPU frontier mismatch for cell (ft={ft_idx},ff={ff_idx}): cpu={cpu_sig} gpu={gpu_sig}"
        )


def test_gpu_timeline_frontier_repeated_upload_matches_baseline() -> None:
    """
    Ensure repeated exact frontier uploads produce identical grid outputs.

    This guards the cache/upload path that reuses the exact symbolic frontier for
    repeated requests of the same song and reference arrays.
    """
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    init_taichi()

    n_notes = 420
    gap_ms = 27
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::13] = np.int16(3)

    song = make_song(timestamps, name="TimelineFrontier Dedup Parity", primary="Beat", note_types=note_types)

    rows = int(MAX_STAT) + 1
    curves = synthetic_curves({
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        # Force a degenerate FT/FF surface so repeated precompute hits the same frontier shape.
        "Fever Fill Rate": np.full((rows,), 1.0, dtype=np.float32),
        "Fever Time": np.full((rows,), 1.0, dtype=np.float32),
    })

    _prebuilt = build_or_load_timeline_frontier_payload(song, curves)
    precompute_timeline_gpu(song, curves, song_slot=0, prebuilt_frontier=_prebuilt)
    precompute_timeline_gpu(song, curves, song_slot=1, prebuilt_frontier=_prebuilt)

    def _eq(field) -> bool:
        arr = field.to_numpy()
        return bool(np.array_equal(arr[0], arr[1]))

    assert _eq(gpu_fields.grid_head_len)
    assert _eq(gpu_fields.grid_fever_masks_bits)
    assert _eq(gpu_fields.grid_count_body_fever)
    assert _eq(gpu_fields.grid_count_body_normal)
    assert _eq(gpu_fields.grid_gap)
    assert _eq(gpu_fields.grid_fever_activations)
    assert _eq(gpu_fields.grid_frontier_count)
    assert _eq(gpu_fields.grid_frontier_offset)
