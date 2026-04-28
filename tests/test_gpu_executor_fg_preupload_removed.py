import numpy as np
import pytest


def test_gpu_executor_rejects_fg_preuploaded_genome_stats():
    from gear_optimizer.solver.gpu_executor import GpuExecutor

    ex = GpuExecutor()
    payload = {
        "n_sections": 1,
        "ftff_pairs": np.asarray([[0, 0]], dtype=np.int32),
        "base_stats_pairs": np.asarray([[0, 0]], dtype=np.int32),
        "non_fever_base_by_ff": np.asarray([0], dtype=np.int16),
        "fp_cap_table": np.asarray([[0]], dtype=np.int16),
        "song_slot": 1,
        "gem_scale_fever": 3,
        "genome_stats_list": None,
        "timestamps_np": np.asarray([0.0, 1.0], dtype=np.float32),
        "great_candidate_timestamps_np": None,
        "long_notes": 0,
        "last_note_time": 1.0,
        "solve_kwargs": {
            "genome_stats_preuploaded": True,
            "upload_genome_stats": False,
            "n_genomes_override": 1,
        },
    }

    with pytest.raises(ValueError, match="removed"):
        ex._run_fg_solve_with_breakpoints_payload(payload)
