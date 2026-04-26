import inspect
import os
import sys

import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def test_vulkan_stage1_keeps_post_config_timeline_surface() -> None:
    """
    Regression: the Vulkan Stage-1 ranking kernel must score each FG config over
    the same full timeline that Stage 2 recomputes. If Stage 1 stops after the
    configured forced-Great sections, it can select a config that loses once the
    remaining normal fever windows are included.
    """
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    body = inspect.getsource(fg_kernels.fg_stage1_waves_kernel)

    assert "if sec >= n_sections" not in body


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_stage1_packed_and_metadata_stay_consistent_on_cfg_tie():
    """
    Regression: In FG Stage 1, the packed (score,cfg_idx) winner must always match the metadata
    fields, even when the best score ties and cfg_idx tie-breaking applies across cfg chunks.

    We construct a deterministic tie across two sequential kernel calls:
      - Call A uses cfg_offset=1 (global cfg idx 1)
      - Call B uses cfg_offset=0 (global cfg idx 0, should win ties)

    Both calls evaluate an identical single config (n_cfg=1), so the final score is guaranteed
    to tie; the lower global cfg idx must be selected and metadata must update accordingly.
    """
    import taichi as ti

    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.taichi_gem import api as gem_api
    from gear_optimizer.solver.taichi_gem import fields as gem_fields
    from gear_optimizer.solver.taichi_gem.force_greats import api as fg_api
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

    gem_api.ensure_ready(ref_arrays)
    fg_fields.ensure_fields_allocated()

    # Song timestamps (small deterministic song).
    timestamps = np.linspace(0.0, 10.0, 40, dtype=np.float32)
    total_notes = fg_api._fg_upload_song_timestamps(timestamps)
    fg_api._fg_use_great_candidate_alias()
    fg_api._ensure_pair_caps_uploaded(None)

    # Upload a single genome's base stats.
    stats = np.zeros((gem_fields.MAX_GENOMES, 7), dtype=np.int16)
    stats[0, :] = [100, 100, 100, 200, 120, 80, 80]
    gem_fields.genome_base_stats.from_numpy(stats)

    # Upload a single FT/FF pair (0,0).
    ft_buf = np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32)
    ff_buf = np.zeros((fg_fields.FG_MAX_FTFF,), dtype=np.int32)
    ft_buf[0] = 0
    ff_buf[0] = 0
    fg_fields.fg_ft_list.from_numpy(ft_buf)
    fg_fields.fg_ff_list.from_numpy(ff_buf)

    n_genomes = 1
    n_ftff = 1
    n_work_items = 1
    n_cfg = 1
    n_sections = 2

    # Single config: all zeros (no forced fill penalties).
    forced = np.zeros((n_cfg, fg_fields.FG_MAX_SECTIONS), dtype=np.int32)
    forced_staging_rows = 4096
    forced_staging_np = np.zeros((forced_staging_rows, fg_fields.FG_MAX_SECTIONS), dtype=np.int32)
    forced_staging_np[:n_cfg, :] = forced
    forced_staging = ti.ndarray(dtype=ti.i32, shape=(forced_staging_rows, fg_fields.FG_MAX_SECTIONS))
    forced_staging.from_numpy(forced_staging_np)
    # Kernel signature includes an explicit destination offset (cfg_dst_offset).
    fg_kernels.fg_upload_forced_counts_kernel(int(n_cfg), 0, forced_staging)

    fg_kernels.fg_build_flat_work_kernel(int(n_genomes), int(n_ftff))
    fg_kernels.fg_stage1_init_kernel(int(n_genomes), int(n_ftff))

    long_notes = 0
    last_note_time = float(timestamps[total_notes - 1])
    total_budget = 90
    gem_scale_fever = 3

    flags = dict(
        is_p_ft=0,
        is_s_ft=0,
        is_p_ff=0,
        is_s_ff=0,
        is_p_pp=0,
        is_s_pp=0,
        is_p_cm=0,
        is_s_cm=0,
        is_p_fm=0,
        is_s_fm=0,
        is_p_ov=1,
        is_s_ov=0,
        song_slot=0,
        pair_caps_from_timeline=0,
    )

    # Process higher global cfg idx first, then lower one (tie-break winner).
    fg_kernels.fg_stage1_kernel(
        int(n_genomes),
        int(total_notes),
        int(long_notes),
        float(last_note_time),
        int(total_budget),
        int(gem_scale_fever),
        int(n_cfg),
        int(n_sections),
        int(n_ftff),
        1,  # cfg_offset
        0,  # cfg_read_offset
        **flags,
        is_first_chunk=1,
    )
    fg_kernels.fg_stage1_kernel(
        int(n_genomes),
        int(total_notes),
        int(long_notes),
        float(last_note_time),
        int(total_budget),
        int(gem_scale_fever),
        int(n_cfg),
        int(n_sections),
        int(n_ftff),
        0,  # cfg_offset (lower should win ties)
        0,  # cfg_read_offset
        **flags,
        is_first_chunk=0,
    )
    ti.sync()

    packed_out = np.zeros((1,), dtype=np.int64)
    cfg_out = np.zeros((1,), dtype=np.int32)

    @ti.kernel
    def _read_slot(packed: ti.types.ndarray(dtype=ti.i64, ndim=1), cfg_idx: ti.types.ndarray(dtype=ti.i32, ndim=1)):
        packed[0] = fg_kernels.fg_stage1_packed[0, 0]
        cfg_idx[0] = fg_kernels.fg_stage1_cfg_idx[0, 0]

    _read_slot(packed_out, cfg_out)
    ti.sync()

    packed = int(packed_out[0])
    cfg_meta = int(cfg_out[0])
    inverted = packed & 0x7FFFFFFF
    cfg_from_packed = 0x7FFFFFFF - int(inverted)

    assert cfg_from_packed == 0
    assert cfg_meta == cfg_from_packed
