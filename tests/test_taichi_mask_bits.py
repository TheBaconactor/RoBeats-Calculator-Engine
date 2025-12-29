"""
Regression test: Verify bitpacked head-fever masks are bit-identical to the legacy i8 mask.

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
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi_vulkan
    from gear_optimizer.solver.taichi_gem.api import ensure_ready
    from gear_optimizer.solver.taichi_gem import fields as gf
    from gear_optimizer.solver.taichi_gem import kernels as gk
    from gear_optimizer.core.constants import TOTAL_ROWS

    # Init Taichi + allocate grid fields
    try:
        init_taichi_vulkan()
    except Exception as exc:
        pytest.skip(f"Taichi Vulkan init failed: {exc}")
    ensure_ready()

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
    n_cases = ft_samples.shape[0]

    # Use fixed scoring params; we only want mask representation parity.
    base_value = np.float32(1234.5)
    combo_mul = np.float32(1.75)
    fever_mul = np.float32(2.6)

    out_old = ti.field(dtype=ti.i32, shape=n_cases)
    out_new = ti.field(dtype=ti.i32, shape=n_cases)
    ft_f = ti.field(dtype=ti.i32, shape=n_cases)
    ff_f = ti.field(dtype=ti.i32, shape=n_cases)
    ft_f.from_numpy(ft_samples)
    ff_f.from_numpy(ff_samples)

    @ti.kernel
    def _compare(n: ti.i32):
        for i in range(n):
            ft = ft_f[i]
            ff = ff_f[i]
            song_slot = ti.i32(0)
            head_len = gf.grid_head_len[song_slot, ft, ff]
            cnt_fever = gf.grid_count_body_fever[song_slot, ft, ff]
            cnt_normal = gf.grid_count_body_normal[song_slot, ft, ff]

            # Legacy: per-note i8 lookup in head loop
            s_old = gk.calc_score_with_grid(
                ti.cast(base_value, ti.f32),
                ti.cast(combo_mul, ti.f32),
                ti.cast(fever_mul, ti.f32),
                song_slot,
                ft,
                ff,
                head_len,
                cnt_fever,
                cnt_normal,
            )

            # New: cached bitset words
            m0 = gf.grid_fever_masks_bits[song_slot, ft, ff, 0]
            m1 = gf.grid_fever_masks_bits[song_slot, ft, ff, 1]
            m2 = gf.grid_fever_masks_bits[song_slot, ft, ff, 2]
            m3 = gf.grid_fever_masks_bits[song_slot, ft, ff, 3]
            s_new = gk.calc_score_with_grid_bits(
                ti.cast(base_value, ti.f32),
                ti.cast(combo_mul, ti.f32),
                ti.cast(fever_mul, ti.f32),
                m0,
                m1,
                m2,
                m3,
                head_len,
                cnt_fever,
                cnt_normal,
            )

            out_old[i] = s_old
            out_new[i] = s_new

    _compare(n_cases)
    ti.sync()

    old_np = out_old.to_numpy()
    new_np = out_new.to_numpy()

    # Exact equality required
    assert np.array_equal(old_np, new_np), f"Mask-bit parity mismatch: old={old_np}, new={new_np}"
