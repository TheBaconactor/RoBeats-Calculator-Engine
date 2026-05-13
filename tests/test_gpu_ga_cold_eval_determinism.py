from __future__ import annotations

from pathlib import Path
import configparser

import numpy as np
import pytest

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.core.config import load_paths_cache, read_iteration_engine_settings
from gear_optimizer.core.constants import GEM_SCALE_FEVER, PATHS
from gear_optimizer.core.utils import safe_int
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.data.song_io import scan_song_header
from gear_optimizer.solver.native_inflight_prepare import prepare_native_song
from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
from gear_optimizer.solver.taichi_gem.api import hard_reset_taichi
from gear_optimizer.solver.taichi_gem.api.ga_operations import (
    ga_download_global_best,
    ga_evaluate_population,
    ga_init_global_best,
    ga_upload_base_fixed_stats,
    ga_upload_item_stats,
    ga_upload_population_indices,
)
from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.slow]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _prepare_light_speed_song():
    repo_root = _repo_root()
    song_path = (
        repo_root
        / "Data"
        / "Hard"
        / "RoBeats The Light Speed Mashup [EXTENDED CUT] (Hard) by Various Artists (Arranged by ZirconEscalus and Got1Butter).txt"
    )
    meta = scan_song_header(str(song_path))
    if not meta or not str(meta.get("Song Name", "")).strip():
        raise RuntimeError(f"Failed to scan song metadata: {song_path}")

    cfg = configparser.ConfigParser()
    cfg.read(repo_root / "config.ini", encoding="utf-8")
    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "UseEvolutionDB", "false")
    cfg.set("IterationEngine", "GPU_Mode", "true")

    app = GearOptimizerApp()
    paths = load_paths_cache()
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    ref_arrays = app._preload_ref_arrays(stats_table)
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}
    ie = read_iteration_engine_settings(cfg)
    auto_buff = bool(ie.auto_select_buff_and_color)
    fg_debug = bool(ie.force_greats_debug)
    ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
    task = app._prepare_tasks(
        [(str(song_path), meta["Song Name"], "Hard")],
        cfg,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        False,
        auto_buff,
        ga_depth,
        None,
        fg_debug,
    )[0]
    return prepare_native_song(task)


def _load_fixed_population_ids() -> np.ndarray:
    fixture_path = _repo_root() / "tests" / "fixtures" / "lightspeed_run0_population_ids.txt"
    population_ids = np.loadtxt(fixture_path, delimiter=",", dtype=np.int32)
    if population_ids.ndim != 2 or population_ids.shape[1] != 9:
        raise RuntimeError(f"Unexpected Light Speed fixture shape: {population_ids.shape}")
    return np.ascontiguousarray(population_ids, dtype=np.int32)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_cold_eval_is_stable_across_hard_resets(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Regression: the exact same cold-evaluation population for Light Speed used to
    drift across Taichi/Vulkan hard resets because the Vulkan warmstart kernel's
    subgroup/shared-memory best-key reduction was not deterministic.

    This test freezes the population IDs and asserts the full winner payload stays
    identical across repeated hard resets.
    """
    monkeypatch.setenv("GPU_NATIVE_GA_PLATEAU_PRUNE", "0")
    monkeypatch.setenv("GPU_NATIVE_GA_BASE_STATS_REUSE", "0")
    monkeypatch.setenv("GPU_NATIVE_GA_EXACT_EVAL_REUSE", "0")

    song = _prepare_light_speed_song()
    population_ids = _load_fixed_population_ids()
    n_genomes = int(population_ids.shape[0])

    winners: list[tuple[int, tuple[int, ...], tuple[int, ...]]] = []

    with _GPU_LOCK:
        for rep in range(4):
            hard_reset_taichi(reason=f"pytest Light Speed cold-eval determinism {rep}")
            ga_upload_item_stats(song.gpu_inputs.item_stats, song.gpu_inputs.slot_start, song.gpu_inputs.slot_count)
            ga_upload_base_fixed_stats(song.gpu_inputs.base_fixed_stats_arr)
            precompute_timeline_gpu(song.gpu_inputs.calc_song, song.gpu_inputs.ref_arrays, song_slot=0)
            ga_upload_population_indices(population_ids, n_slots=9)
            ga_init_global_best()
            ga_evaluate_population(
                n_genomes=n_genomes,
                n_slots=9,
                total_budget=int(song.gpu_inputs.cfg_data.get("TotalBudget", 90)),
                gem_scale_fever=int(song.gpu_inputs.cfg_data.get("GemScaleFever", GEM_SCALE_FEVER)),
                song_slot=0,
                materialize_mode="update_global",
                **song.gpu_inputs.color_flags,
            )
            score, best_ids, best_results = ga_download_global_best()
            winners.append(
                (
                    int(score),
                    tuple(int(x) for x in best_ids[:9]),
                    tuple(int(x) for x in best_results[:7]),
                )
            )

    assert winners
    assert len(set(winners)) == 1, f"Cold-eval winner drifted across hard resets: {winners}"
    assert winners[0][0] > 0
    assert winners[0][2][0] == winners[0][0]
