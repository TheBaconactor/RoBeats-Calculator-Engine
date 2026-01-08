import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_breakpoints_max_fp_kernel_parity_small():
    """
    Parity test for the new FG breakpoint-range kernel used by ForceGreatsFinder batching.

    We compare GPU-computed per-(pair, section) max FP caps against a direct CPU reference
    implementing the same logic as `helpers.fg_utils.iter_analytical_breakpoint_groups`.
    """
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem.kernels import kernels_breakpoints
    from gear_optimizer.helpers.fg_utils import _fp_cap_from_forced, MAX_SECTION_CAPS
    from gear_optimizer.solver.analytical_fg import create_scorer_from_calc_song
    from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE

    # Use exactly representable timestamps (step=0.125) to avoid f32 boundary drift.
    n_notes = 512
    dt = np.float32(0.125)
    timestamps = (np.arange(n_notes, dtype=np.float32) * dt).astype(np.float32)
    last_note_time = float(timestamps[-1])

    calc_song = {
        "metadata": {
            "Song Name": "FG Breakpoints MaxFP Parity",
            "Difficulty": "Test",
            "Primary Color": "Rush",
            "Secondary Color": "Beat",
            "Long Notes": 0,
            "Last Note Time": last_note_time,
            "Total Notes": n_notes,
        },
        "song_data": {"timestamps": timestamps},
    }

    # Simple monotone ref arrays with length 161 (index 0..160).
    ref_arrays = {
        "Fever Time": np.linspace(0.8, 1.2, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.8, 1.8, 161, dtype=np.float32),
        "Perfect Points": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }

    # Precompute baseline timeline grid on GPU (fills grid_gap/grid_fever_activations).
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

    scorer = create_scorer_from_calc_song(calc_song, ref_arrays)

    # Inputs (small but non-trivial).
    ftff_pairs = [(0, 0), (5, 0), (0, 5), (10, 10)]
    base_stats_pairs = {(80, 80), (60, 110), (100, 40)}
    n_sections = 4
    gem_scale_fever = 3

    # CPU reference: compute max_fp_by_sec for each pair.
    cpu_max_fp = np.zeros((len(ftff_pairs), n_sections), dtype=np.int16)
    for i_pair, (ft_g, ff_g) in enumerate(ftff_pairs):
        max_fp_by_sec = [0 for _ in range(n_sections)]
        for base_ft, base_ff in base_stats_pairs:
            ft_stat = int(base_ft) + int(ft_g) * int(gem_scale_fever)
            ff_stat = int(base_ff) + int(ff_g) * int(gem_scale_fever)
            analysis = scorer.get_section_analysis(ft_stat, ff_stat)
            useful = min(n_sections, int(analysis.get("useful_sections", 0) or 0))
            if useful <= 0:
                continue

            analyzed_caps = analysis.get("section_caps") or []
            for sec in range(useful):
                if sec < len(analyzed_caps) and analyzed_caps[sec] > 0:
                    cap = min(int(analyzed_caps[sec]), int(MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4))
                else:
                    cap = int(MAX_SECTION_CAPS[sec] if sec < len(MAX_SECTION_CAPS) else 4)
                if cap <= 0:
                    continue
                fp_cap = _fp_cap_from_forced(scorer, ft_stat, ff_stat, int(cap))
                if fp_cap > max_fp_by_sec[sec]:
                    max_fp_by_sec[sec] = int(fp_cap)

        cpu_max_fp[i_pair, :] = np.asarray(max_fp_by_sec, dtype=np.int16)

    # Build the exact FP cap lookup tables (same approach as gpu_dispatch).
    non_fever_cas = max(0.0, float((n_notes - 0)) * float(FEVER_FILL_BASE_RATE))
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float64)[:161]
    raw_fill = non_fever_cas * ref_ff
    ceil_raw = np.ceil(raw_fill)
    non_fever_base_by_ff = np.clip(ceil_raw, 0, 32767).astype(np.int16)
    fp_cap_table = np.zeros((161, 51), dtype=np.int16)
    for forced_cap in range(0, 51):
        fp = np.ceil(raw_fill + (forced_cap * 0.5)) - ceil_raw
        fp_cap_table[:, forced_cap] = np.maximum(0, fp).astype(np.int16)

    # GPU kernel evaluation.
    pair_ft = np.asarray([p[0] for p in ftff_pairs], dtype=np.int32)
    pair_ff = np.asarray([p[1] for p in ftff_pairs], dtype=np.int32)
    base_list = sorted({(int(a), int(b)) for (a, b) in base_stats_pairs})
    base_ft = np.asarray([p[0] for p in base_list], dtype=np.int32)
    base_ff = np.asarray([p[1] for p in base_list], dtype=np.int32)

    gpu_max_fp = np.zeros((len(ftff_pairs), n_sections), dtype=np.int16)
    kernels_breakpoints.fg_compute_max_fp_by_pair_kernel(
        int(len(ftff_pairs)),
        int(len(base_list)),
        int(n_sections),
        int(0),  # song_slot
        int(gem_scale_fever),
        pair_ft,
        pair_ff,
        base_ft,
        base_ff,
        non_fever_base_by_ff,
        fp_cap_table,
        gpu_max_fp,
    )

    # Strict equality expected for this synthetic exact-timestamp setup.
    assert np.array_equal(cpu_max_fp, gpu_max_fp), f"cpu_max_fp={cpu_max_fp} gpu_max_fp={gpu_max_fp}"
