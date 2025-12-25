"""
Test CPU vs GPU Breakpoint Collection Parity.

This test validates that the GPU breakpoint kernel produces identical
breakpoint sets to the CPU analytical method.
"""
import os
import sys
import numpy as np
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.analytical_fg import create_scorer_from_calc_song
from gear_optimizer.helpers.fg_utils import collect_analytical_breakpoints


def create_test_song_data(n_notes: int = 500, duration: float = 60.0, long_notes: int = 0):
    """Create synthetic test song in calc_song format."""
    timestamps = np.linspace(0, duration, n_notes).tolist()
    return {
        "song_data": {"timestamps": np.array(timestamps)},
        "metadata": {
            "Song Name": "Test Song",
            "Difficulty": "Test",
            "Last Note Time": str(duration),
            "Total Notes": str(n_notes),
            "Long Notes": str(long_notes),
            "Primary Color": "Rush",
            "Secondary Color": "Beat",
        }
    }


def create_reference_arrays():
    """Create reference lookup arrays (simplified for testing)."""
    return {
        "Fever Time": np.linspace(0.5, 1.5, 161),
        "Fever Fill Rate": np.linspace(0.5, 2.0, 161),
        "Perfect Points": np.linspace(100, 300, 161),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161),
    }


def collect_breakpoints_gpu(scorer, num_sections, section_caps=None):
    """
    GPU-accelerated breakpoint collection using existing kernels.
    
    This is the proposed replacement for collect_analytical_breakpoints.
    """
    try:
        from gear_optimizer.solver.taichi_gem.kernels import kernels_breakpoints
        from gear_optimizer.solver.taichi_gem import runtime, fields
        import taichi as ti
        import itertools
        
        # Ensure Taichi is initialized
        if not runtime.is_initialized():
            runtime.init_taichi()
        fields.ensure_fields_allocated()
        
        # Get section analysis (same as CPU version)
        analysis = scorer.get_section_analysis(80, 80)
        useful_sections = analysis['useful_sections']
        analyzed_caps = analysis['section_caps']
        
        actual_sections = min(num_sections, useful_sections)
        if actual_sections <= 0:
            return [()]
        
        # Get section caps (same logic as CPU version)
        if section_caps is None:
            from gear_optimizer.helpers.fg_utils import MAX_SECTION_CAPS
            section_caps = []
            for i in range(actual_sections):
                if i < len(analyzed_caps) and analyzed_caps[i] > 0:
                    cap = min(analyzed_caps[i], MAX_SECTION_CAPS[i] if i < len(MAX_SECTION_CAPS) else 4)
                else:
                    cap = MAX_SECTION_CAPS[i] if i < len(MAX_SECTION_CAPS) else 4
                section_caps.append(cap)
        else:
            section_caps = section_caps[:actual_sections]
        
        # Upload song timestamps to GPU (if not already uploaded)
        timestamps_np = np.asarray(scorer.timestamps, dtype=np.float32)
        fields.song_timestamps.from_numpy(np.pad(timestamps_np, (0, fields.MAX_SONG_NOTES - len(timestamps_np))))

        # Upload reference lookup tables required by kernels_breakpoints.
        # The CPU scorer carries ref_ft/ref_ff; the GPU kernels read from
        # kernels_helpers.ref_ft_field/ref_ff_field (bound via fields.bind_fields).
        fields.ref_ft_field.from_numpy(np.asarray(scorer.ref_ft, dtype=np.float32))
        fields.ref_ff_field.from_numpy(np.asarray(scorer.ref_ff, dtype=np.float32))
        
        # Prepare FT/FF pairs for GPU kernel
        # Use representative FT=80 and sample FF values (same as CPU version)
        ft_pairs_list = [80]
        ff_pairs_list = list(range(0, 161, 10))  # 17 samples

        # CPU code enumerates breakpoints in *fill-penalty (FP)* units, where
        # FP = ceil(raw_fill + forced*0.5) - ceil(raw_fill). Compute the max FP
        # per section across the same FF sample set so the GPU kernel scans the
        # same [0..max_fp] range.
        from gear_optimizer.helpers.fg_utils import _fp_cap_from_forced
        max_fp_per_section = []
        for sec in range(actual_sections):
            if section_caps[sec] <= 0:
                max_fp_per_section.append(0)
                continue
            max_fp = 0
            for ff_stat in ff_pairs_list:
                fp_cap = _fp_cap_from_forced(scorer, 80, ff_stat, int(section_caps[sec]))
                if fp_cap > max_fp:
                    max_fp = fp_cap
            max_fp_per_section.append(int(max_fp))
         
        n_pairs = len(ft_pairs_list) * len(ff_pairs_list)
        ft_array = np.zeros(256, dtype=np.int32)
        ff_array = np.zeros(256, dtype=np.int32)
        
        idx = 0
        for ft in ft_pairs_list:
            for ff in ff_pairs_list:
                ft_array[idx] = ft
                ff_array[idx] = ff
                idx += 1
        
        # Upload pairs to GPU
        kernels_breakpoints.bp_pair_ft.from_numpy(ft_array)
        kernels_breakpoints.bp_pair_ff.from_numpy(ff_array)
        
        # Reset mask
        kernels_breakpoints.reset_breakpoint_mask_kernel()
        
        # Collect breakpoints on GPU
        max_count = max(max_fp_per_section) if max_fp_per_section else 0
        kernels_breakpoints.collect_breakpoints_kernel(
            n_pairs=idx,
            total_notes=scorer.total_notes,
            long_notes=scorer.long_notes,
            last_note_time=scorer.last_note_time,
            max_sections=actual_sections,
            max_count=max_count,
        )
        
        # Sync and download mask
        ti.sync()
        mask = kernels_breakpoints.bp_result_mask.to_numpy()
        
        # Extract breakpoints from mask (same as proposed in optimization doc)
        section_breakpoints = []
        for sec in range(actual_sections):
            sec_cap = max_fp_per_section[sec]
            if sec_cap <= 0:
                section_breakpoints.append([0])
            else:
                breakpoints = [0]  # Always include 0
                for count in range(1, sec_cap + 1):
                    if mask[sec, count] > 0:
                        breakpoints.append(count)
                section_breakpoints.append(breakpoints)
        
        # Generate all combinations (same as CPU version)
        return list(itertools.product(*section_breakpoints))
        
    except ImportError as e:
        pytest.skip(f"GPU not available: {e}")


@pytest.mark.parametrize("song_notes,duration", [
    (200, 30.0),   # Short song
    (500, 60.0),   # Medium song
    (1000, 120.0), # Long song
])
@pytest.mark.parametrize("num_sections", [2, 3, 4])
def test_cpu_vs_gpu_breakpoints(song_notes, duration, num_sections):
    """Test that GPU breakpoint kernel produces identical results to CPU."""
    calc_song = create_test_song_data(song_notes, duration=duration)
    ref_arrays = create_reference_arrays()
    scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
    
    # CPU breakpoints (current production code)
    cpu_breakpoints = collect_analytical_breakpoints(scorer, num_sections)
    
    # GPU breakpoints (proposed replacement)
    gpu_breakpoints = collect_breakpoints_gpu(scorer, num_sections)
    
    # Should produce identical breakpoint sets
    cpu_set = set(cpu_breakpoints)
    gpu_set = set(gpu_breakpoints)
    
    # Check for exact match
    assert cpu_set == gpu_set, (
        f"CPU/GPU breakpoint mismatch (song={song_notes}, sections={num_sections}):\n"
        f"  CPU count: {len(cpu_breakpoints)}\n"
        f"  GPU count: {len(gpu_breakpoints)}\n"
        f"  CPU only: {cpu_set - gpu_set}\n"
        f"  GPU only: {gpu_set - cpu_set}"
    )
    
    # Also verify they're in same order (for determinism)
    assert cpu_breakpoints == gpu_breakpoints


@pytest.mark.parametrize("song_notes", [200, 500, 1000])
def test_breakpoint_coverage(song_notes):
    """Verify breakpoints cover all critical FG counts."""
    calc_song = create_test_song_data(song_notes, duration=song_notes / 10.0)
    ref_arrays = create_reference_arrays()
    scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
    
    # Get CPU breakpoints
    breakpoints = collect_analytical_breakpoints(scorer, num_sections=4)
    
    # Verify we have reasonable coverage
    assert len(breakpoints) > 0, "Should have at least one config"
    
    # Zero config should be included (might be (0,), (0,0), etc depending on sections)
    has_zero = any(all(x == 0 for x in bp) if isinstance(bp, tuple) else bp == 0 for bp in breakpoints)
    assert has_zero, "Should include zero FG config"
    
    # Verify no duplicate configs
    assert len(breakpoints) == len(set(breakpoints)), "Should have no duplicates"


def test_breakpoint_count_matches_expectations():
    """Verify breakpoint count is reasonable (not too many, not too few)."""
    calc_song = create_test_song_data(500, duration=60.0)
    ref_arrays = create_reference_arrays()
    scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
    
    breakpoints = collect_analytical_breakpoints(scorer, num_sections=4)
    
    # Should be much smaller than full grid (50^4 = 6.25M)
    # Typical: ~100-500 configs instead of millions
    assert len(breakpoints) < 10000, f"Too many breakpoints: {len(breakpoints)}"
    assert len(breakpoints) > 1, "Should have more than just zero config"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
