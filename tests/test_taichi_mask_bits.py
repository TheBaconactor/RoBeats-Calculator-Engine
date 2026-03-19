"""
Regression test: Verify bitpacked head-fever masks are bit-identical to the i8 mask.

This specifically guards the optimization where we:
- pack grid_fever_masks[ft,ff,:] into 4x u32 words (grid_fever_masks_bits)
- score head notes via bit-tests instead of per-note global mask reads

Requirement: GPU path must remain EXACT (bit-identical scores and allocations).
"""

import os
import sys
import numpy as np
import pytest

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


pytestmark = pytest.mark.gpu


def test_mask_bits_parity():
    pytest.importorskip("taichi")
    import taichi as ti

    from gear_optimizer.solver.fever_timeline import SongTimelineGrid
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    from gear_optimizer.solver.taichi_gem.api import ensure_ready
    from gear_optimizer.solver.taichi_gem import fields as gf
    from gear_optimizer.core.constants import TOTAL_ROWS

    # Init Taichi + allocate grid fields
    try:
        init_taichi()
    except Exception as exc:
        pytest.skip(f"Taichi init failed: {exc}")
    ensure_ready()
    # Allocate legacy i8 masks for this parity test; production uses bitpacked masks.
    gf.ensure_grid_unpacked_masks_allocated()

    # Build a deterministic mock song and reference arrays so the timeline grid is stable
    # (We only care about the fever masks being consistent between representations.)
    n_notes = 250
    timestamps = np.linspace(0, 120, n_notes).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "Mask Bits Parity Test Song",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": n_notes,
        },
        "song_data": {"timestamps": timestamps},
    }

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }

    grid = SongTimelineGrid(calc_song, ref_arrays)
    # Ensure grid is computed and uploaded (populates both i8 masks and bitset masks)
    ensure_ready(timeline_grid=grid)

    # Sample a handful of (ft,ff) cells including boundaries
    ft_samples = np.array([0, 1, 10, 50, 100, 159, 160], dtype=np.int32)
    ff_samples = np.array([0, 2, 11, 60, 120, 158, 160], dtype=np.int32)
    ti.sync()

    # Download full grids (small enough for a regression test) and validate
    # representation parity on CPU to avoid backend-specific kernel flakiness.
    song_slot = 0
    head_len_np = gf.grid_head_len.to_numpy()[song_slot]
    masks_bits_np = gf.grid_fever_masks_bits.to_numpy()[song_slot]  # (161,161,4) u32
    masks_np = gf.grid_fever_masks.to_numpy()[0]  # (161,161,100) i8, stored only for slot 0

    for ft, ff in zip(ft_samples.tolist(), ff_samples.tolist(), strict=True):
        hl = int(head_len_np[ft, ff])
        words = masks_bits_np[ft, ff]
        mask_row = masks_np[ft, ff]
        for i in range(hl):
            word = int(words[i >> 5])
            bit = (word >> (i & 31)) & 1
            m = int(mask_row[i])
            assert (m != 0) == (bit != 0), f"Mask mismatch at ft={ft}, ff={ff}, i={i}: i8={m}, bit={bit}"

    # If representation matches, score parity follows (score kernels are deterministic functions of the mask).
