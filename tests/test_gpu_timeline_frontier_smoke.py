import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = pytest.mark.gpu


def _count_head_fever(bits_u32: np.ndarray, head_len: int) -> int:
    bits = np.asarray(bits_u32, dtype=np.uint32).reshape(-1)
    n = int(max(0, head_len))
    total = 0
    for i in range(n):
        w = i >> 5
        b = i & 31
        if (int(bits[w]) >> b) & 1:
            total += 1
    return int(total)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_timeline_frontier_upload_populates_retained_surfaces() -> None:
    """
    Exact frontier smoke: build the candidate-independent payload, upload it, and
    verify representative cells expose retained fever surfaces.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    init_taichi()

    # Build a chart directly in integer ms space (robust to float32 boundary issues).
    n_notes = 320
    gap_ms = 30
    ts_ms = (np.arange(n_notes, dtype=np.int32) * np.int32(gap_ms)).astype(np.int32)
    timestamps = (ts_ms.astype(np.float32) * np.float32(0.001)).astype(np.float32)

    # Include some held-tail notes so the carry window includes (+80) values.
    note_types = np.ones(n_notes, dtype=np.int16)
    note_types[::11] = np.int16(3)

    calc_song = {
        "metadata": {
            "Song Name": "TimelineFrontier Timeline Smoke",
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
            "lanes": np.arange(n_notes, dtype=np.int32) % np.int32(4),
        },
    }
    apply_timing_envelope(calc_song, mode="perfect_window")

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        # Taichi runtime expects these core lookup tables to be present.
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }

    ftff_samples = [(10, 10), (80, 80), (160, 40)]

    def _read_total_fever() -> dict[tuple[int, int], int]:
        head_len_grid = np.asarray(gpu_fields.grid_head_len.to_numpy()[0], dtype=np.int32)
        bits_grid = np.asarray(gpu_fields.grid_fever_masks_bits.to_numpy()[0], dtype=np.uint32)
        body_fever_grid = np.asarray(gpu_fields.grid_count_body_fever.to_numpy()[0], dtype=np.int32)

        out: dict[tuple[int, int], int] = {}
        for ft_idx, ff_idx in ftff_samples:
            head_len = int(head_len_grid[ft_idx, ff_idx])
            bits = bits_grid[ft_idx, ff_idx, :]
            head_fever = _count_head_fever(bits, head_len)
            body_fever = int(body_fever_grid[ft_idx, ff_idx])
            out[(ft_idx, ff_idx)] = int(head_fever + body_fever)
        return out

    prebuilt = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    assert int(prebuilt.payload.frontier_pool_used) > 0

    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt)
    total_fever = _read_total_fever()
    frontier_count_grid = np.asarray(gpu_fields.grid_frontier_count.to_numpy()[0], dtype=np.int32)

    for cell in ftff_samples:
        assert int(frontier_count_grid[cell[0], cell[1]]) > 0, f"missing retained frontier for cell {cell}"
    assert any(v > 0 for v in total_fever.values()), f"expected at least one fever note; got {total_fever}"
