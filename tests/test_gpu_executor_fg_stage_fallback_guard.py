import sys
import types

import numpy as np


def test_gpu_executor_fg_stage_uses_keyword_args(monkeypatch):
    """
    Regression test:
    The GA->FG staging API is keyword-only. If the executor accidentally calls it
    with positional args, staging raises `TypeError` and silently degrades FG.

    Ensure the executor calls staging with keyword arguments.
    """
    from gear_optimizer.solver.gpu_executor import GpuExecutor

    # Stub Taichi/GPU modules so this test is CPU-only and deterministic.
    taichi_gem_pkg = types.ModuleType("gear_optimizer.solver.taichi_gem")
    taichi_gem_pkg.__path__ = []  # mark as package
    force_greats_pkg = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats")
    force_greats_pkg.__path__ = []  # mark as package

    taichi_api_mod = types.ModuleType("gear_optimizer.solver.taichi_gem.api")

    calls: list[tuple[int, tuple[int, ...] | None, int]] = []

    def _stage_ok(*, table_slot: int, coords: np.ndarray, n_slots: int = 9):
        calls.append((int(table_slot), getattr(coords, "shape", None), int(n_slots)))
        return 1

    taichi_api_mod.ga_stage_genome_base_stats_from_fg_candidates_table = _stage_ok

    fg_api_mod = types.ModuleType("gear_optimizer.solver.taichi_gem.force_greats.api")

    def _noop(*_args, **_kwargs):
        return None

    fg_api_mod.fg_reset_global_best = _noop
    fg_api_mod.solve_force_greats_finder_gpu_tasks = _noop
    fg_api_mod.fg_download_global_best = lambda *_a, **_k: {"cfg_counts": np.zeros((1, 1), dtype=np.int32)}

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem", taichi_gem_pkg)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", taichi_api_mod)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats", force_greats_pkg)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.force_greats.api", fg_api_mod)

    ex = GpuExecutor()
    ex._in_process_queues = True

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
        "ga_stage_coords": np.asarray([[0, 0]], dtype=np.int32),
        "ga_stage_table_slot": 1,
    }

    ex._run_fg_solve_with_breakpoints_payload(payload)
    assert calls == [(1, (1, 2), 9)]
