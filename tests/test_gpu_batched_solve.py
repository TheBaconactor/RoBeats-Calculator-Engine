import pytest


pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi  # noqa: F401
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_solve_genomes_parallel_merged_parity_small():
    """
    Parity check: merged multi-request solve matches running each request individually.

    This intentionally uses small genome counts and constrained FT/FF ranges to keep runtime low.
    """
    import numpy as np

    from gear_optimizer.solver.taichi_gem.api import solve_genomes_parallel, solve_genomes_parallel_merged

    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }

    def make_song(name: str):
        ts = np.linspace(0, 30, 120).astype(np.float64)
        return {
            "song_data": {"timestamps": ts},
            "metadata": {
                "Song Name": name,
                "Long Notes": 2,
                "Last Note Time": float(ts[-1]),
                "Primary Color": "Chill",
                "Secondary Color": "Flow",
            },
        }

    # Constrain max FT/FF: base stats near the cap.
    genomes = [
        {
            "base_pp": 60,
            "base_cm": 60,
            "base_fm": 60,
            "base_p_val": 200,
            "base_s_val": 100,
            "base_ft_stat": 150,
            "base_ff_stat": 150,
        }
        for _ in range(16)
    ]

    # Two requests with different OV flag behavior.
    payload_a = {
        "genome_stats_list": genomes,
        "timeline_grid": make_song("MERGE_A"),
        "is_p_ft": 0, "is_s_ft": 0,
        "is_p_ff": 0, "is_s_ff": 0,
        "is_p_pp": 1, "is_s_pp": 0,
        "is_p_cm": 0, "is_s_cm": 1,
        "is_p_fm": 0, "is_s_fm": 0,
        "is_p_ov": 1, "is_s_ov": 0,
        "ref_arrays": ref_arrays,
    }
    payload_b = {
        "genome_stats_list": genomes,
        "timeline_grid": make_song("MERGE_B"),
        "is_p_ft": 0, "is_s_ft": 0,
        "is_p_ff": 0, "is_s_ff": 0,
        "is_p_pp": 1, "is_s_pp": 0,
        "is_p_cm": 0, "is_s_cm": 1,
        "is_p_fm": 0, "is_s_fm": 0,
        "is_p_ov": 0, "is_s_ov": 1,
        "ref_arrays": ref_arrays,
    }

    total_budget = 20
    gem_scale_fever = 3

    # Individual
    res_a = solve_genomes_parallel(
        payload_a["genome_stats_list"],
        payload_a["timeline_grid"],
        payload_a["is_p_ft"], payload_a["is_s_ft"], payload_a["is_p_ff"], payload_a["is_s_ff"],
        payload_a["is_p_pp"], payload_a["is_s_pp"], payload_a["is_p_cm"], payload_a["is_s_cm"],
        payload_a["is_p_fm"], payload_a["is_s_fm"], payload_a["is_p_ov"], payload_a["is_s_ov"],
        payload_a["ref_arrays"],
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=0,
    )
    res_b = solve_genomes_parallel(
        payload_b["genome_stats_list"],
        payload_b["timeline_grid"],
        payload_b["is_p_ft"], payload_b["is_s_ft"], payload_b["is_p_ff"], payload_b["is_s_ff"],
        payload_b["is_p_pp"], payload_b["is_s_pp"], payload_b["is_p_cm"], payload_b["is_s_cm"],
        payload_b["is_p_fm"], payload_b["is_s_fm"], payload_b["is_p_ov"], payload_b["is_s_ov"],
        payload_b["ref_arrays"],
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=0,
    )

    # Merged
    merged = solve_genomes_parallel_merged(
        [payload_a, payload_b],
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
    )

    assert merged[0] == res_a
    assert merged[1] == res_b

