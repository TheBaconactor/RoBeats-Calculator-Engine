from __future__ import annotations

import os

import numpy as np
import pytest

from gear_optimizer.core.constants import GEM_SCALE_FEVER
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
from gear_optimizer.solver.taichi_gem import fields as gpu_fields
from gear_optimizer.solver.taichi_gem.api.ga_operations import (
    ga_download_results,
    ga_download_scores,
    ga_evaluate_population,
    ga_init_runs_best,
    ga_pack_fg_candidates_table_segmented,
    ga_refresh_scores_and_update_runs_best,
    ga_upload_base_fixed_stats,
    ga_upload_item_stats,
    ga_upload_population_indices,
    ga_write_best_and_update_global,
    ga_write_best_results_and_update_runs_best,
)
from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu

pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def _make_calc_song(*, name: str, p_color: str, s_color: str, n: int = 1200) -> dict:
    ts = np.linspace(0.0, 160.0, n, dtype=np.float32)
    return {
        "metadata": {
            "Song Name": name,
            "Primary Color": p_color,
            "Secondary Color": s_color,
            "Long Notes": 25,
            "Last Note Time": float(ts[-1]),
        },
        "song_data": {"timestamps": ts},
    }


def _color_flags(*, p_color: str, s_color: str, selected_color: str) -> dict[str, int]:
    return {
        "is_p_pp": 1 if p_color == "Chill" else 0,
        "is_s_pp": 1 if s_color == "Chill" else 0,
        "is_p_cm": 1 if p_color == "Flow" else 0,
        "is_s_cm": 1 if s_color == "Flow" else 0,
        "is_p_fm": 1 if p_color == "Rush" else 0,
        "is_s_fm": 1 if s_color == "Rush" else 0,
        "is_p_ov": 1 if selected_color == p_color else 0,
        "is_s_ov": 1 if selected_color == s_color else 0,
        "is_p_ft": 1 if p_color == "Beat" else 0,
        "is_s_ft": 1 if s_color == "Beat" else 0,
        "is_p_ff": 1 if p_color == "Vibe" else 0,
        "is_s_ff": 1 if s_color == "Vibe" else 0,
    }


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_eval_key_consistency_and_determinism() -> None:
    """
    Race/consistency check for GPU-native GA evaluation:
    - `chunk_best_key` encodes the same score/ft/ff that we materialize in `genome_result_stats`.

    Vulkan subgroup scheduling can change winner tie paths between dispatches, so this
    test enforces per-run key/result consistency rather than byte-identical repeats.
    """
    n_genomes = 128
    total_budget = 90

    rng = np.random.default_rng(1337)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    def make_item_pool(prefix: str, n: int) -> list[dict]:
        items: list[dict] = []
        for i in range(n):
            items.append(
                _mk_item(
                    f"{prefix}{i}",
                    **{
                        "Perfect Points": int(rng.integers(0, 120)),
                        "Combo Multiplier": int(rng.integers(0, 120)),
                        "Fever Multiplier": int(rng.integers(0, 120)),
                        "Fever Time": int(rng.integers(0, 40)),
                        "Fever Fill Rate": int(rng.integers(0, 40)),
                        "Beat": int(rng.integers(0, 200)),
                        "Vibe": int(rng.integers(0, 200)),
                        "Rush": int(rng.integers(0, 200)),
                        "Flow": int(rng.integers(0, 200)),
                        "Chill": int(rng.integers(0, 200)),
                    },
                )
            )
        return items

    gear_pool = {slot: make_item_pool(f"{slot}_", 14) for slot in slots}
    mini_pool = make_item_pool("Mini_", 24)
    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_arrays = registry.to_gpu_arrays()

    base_fixed_stats_arr = np.array(
        [
            int(rng.integers(100, 300)),  # PP
            int(rng.integers(100, 300)),  # CM
            int(rng.integers(100, 300)),  # FM
            int(rng.integers(0, 40)),  # FT
            int(rng.integers(0, 40)),  # FF
            int(rng.integers(200, 400)),  # Beat
            int(rng.integers(200, 400)),  # Vibe
            int(rng.integers(200, 400)),  # Rush
            int(rng.integers(200, 400)),  # Flow
            int(rng.integers(200, 400)),  # Chill
        ],
        dtype=np.int32,
    )

    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 1.0, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float64),
    }

    calc_song = _make_calc_song(name="RaceFreeEval_BeatVibe", p_color="Beat", s_color="Vibe")
    flags = _color_flags(p_color="Beat", s_color="Vibe", selected_color="Beat")

    old_prune = os.environ.get("GPU_NATIVE_GA_PLATEAU_PRUNE")
    os.environ["GPU_NATIVE_GA_PLATEAU_PRUNE"] = "0"
    try:
        with _GPU_LOCK:
            ga_upload_item_stats(gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"])
            ga_upload_base_fixed_stats(base_fixed_stats_arr)
            precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

            genomes: list[list[dict]] = []
            for _g in range(n_genomes):
                gear = [gear_pool[slot][int(rng.integers(0, len(gear_pool[slot])))] for slot in slots]
                minis = [mini_pool[int(i)] for i in rng.choice(len(mini_pool), size=3, replace=False)]
                genomes.append(gear + minis)
            pop_indices = registry.encode_population(genomes)
            ga_upload_population_indices(pop_indices, n_slots=9)

            # Repeat the exact no-hints evaluation several times to stress the
            # reduction/materialization path where hidden misses previously appeared.
            for _rep in range(4):
                ga_evaluate_population(
                    n_genomes=n_genomes,
                    n_slots=9,
                    total_budget=total_budget,
                    gem_scale_fever=GEM_SCALE_FEVER,
                    song_slot=0,
                    is_p_ft=flags["is_p_ft"],
                    is_s_ft=flags["is_s_ft"],
                    is_p_ff=flags["is_p_ff"],
                    is_s_ff=flags["is_s_ff"],
                    is_p_pp=flags["is_p_pp"],
                    is_s_pp=flags["is_s_pp"],
                    is_p_cm=flags["is_p_cm"],
                    is_s_cm=flags["is_s_cm"],
                    is_p_fm=flags["is_p_fm"],
                    is_s_fm=flags["is_s_fm"],
                    is_p_ov=flags["is_p_ov"],
                    is_s_ov=flags["is_s_ov"],
                )
                ga_write_best_and_update_global(
                    n_genomes=n_genomes,
                    n_slots=9,
                    total_budget=total_budget,
                    gem_scale_fever=GEM_SCALE_FEVER,
                    song_slot=0,
                    is_p_ft=flags["is_p_ft"],
                    is_s_ft=flags["is_s_ft"],
                    is_p_ff=flags["is_p_ff"],
                    is_s_ff=flags["is_s_ff"],
                    is_p_pp=flags["is_p_pp"],
                    is_s_pp=flags["is_s_pp"],
                    is_p_cm=flags["is_p_cm"],
                    is_s_cm=flags["is_s_cm"],
                    is_p_fm=flags["is_p_fm"],
                    is_s_fm=flags["is_s_fm"],
                    is_p_ov=flags["is_p_ov"],
                    is_s_ov=flags["is_s_ov"],
                )

                results = ga_download_results(n_genomes)
                scores = ga_download_scores(n_genomes)
                assert np.array_equal(results[:, 0], scores)

                if gpu_fields.chunk_best_key is not None:
                    best_keys = np.asarray(gpu_fields.chunk_best_key.to_numpy()[:n_genomes], dtype=np.uint64)
                    best_scores = (best_keys >> np.uint64(32)).astype(np.int64) - 1
                    best_combo = (best_keys & np.uint64(0xFFFFFFFF)).astype(np.int64)
                    # When no valid combo exists, key is 0 and score is -1.
                    assert np.array_equal(best_scores.astype(np.int32), results[:, 0])
                else:
                    best_combo = np.asarray(gpu_fields.chunk_best_idx.to_numpy()[:n_genomes], dtype=np.int32)
                    # Metal uses split score/index reduction buffers; final score is
                    # re-materialized into ga_scores/genome_result_stats after the
                    # winning combo index is finalized.
                    assert np.array_equal(scores, results[:, 0])

                combo_ft = np.asarray(gpu_fields.ftff_combo_ft.to_numpy(), dtype=np.int32)
                combo_ff = np.asarray(gpu_fields.ftff_combo_ff.to_numpy(), dtype=np.int32)

                valid = best_combo >= 0
                valid &= best_combo < combo_ft.shape[0]
                valid &= results[:, 0] >= 0

                if np.any(valid):
                    ft = combo_ft[best_combo[valid]]
                    ff = combo_ff[best_combo[valid]]
                    assert np.array_equal(ft, results[valid, 1])
                    assert np.array_equal(ff, results[valid, 2])
    finally:
        if old_prune is None:
            os.environ.pop("GPU_NATIVE_GA_PLATEAU_PRUNE", None)
        else:
            os.environ["GPU_NATIVE_GA_PLATEAU_PRUNE"] = old_prune


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_eval_raw_key_scores_match_materialized_scores() -> None:
    """
    The Vulkan warmstart key must carry the same exact score that materialization finalizes.

    This guards the corrected optimization boundary uncovered during occupancy work:
    once the warmstart reduction is race-free, the packed `chunk_best_key` score becomes
    selection-safe and can be trusted to match the later materialized GA score.
    """
    n_genomes = 96
    total_budget = 90

    rng = np.random.default_rng(20260423)
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    def make_item_pool(prefix: str, n: int) -> list[dict]:
        items: list[dict] = []
        for i in range(n):
            items.append(
                _mk_item(
                    f"{prefix}{i}",
                    **{
                        "Perfect Points": int(rng.integers(0, 120)),
                        "Combo Multiplier": int(rng.integers(0, 120)),
                        "Fever Multiplier": int(rng.integers(0, 120)),
                        "Fever Time": int(rng.integers(0, 40)),
                        "Fever Fill Rate": int(rng.integers(0, 40)),
                        "Beat": int(rng.integers(0, 200)),
                        "Vibe": int(rng.integers(0, 200)),
                        "Rush": int(rng.integers(0, 200)),
                        "Flow": int(rng.integers(0, 200)),
                        "Chill": int(rng.integers(0, 200)),
                    },
                )
            )
        return items

    gear_pool = {slot: make_item_pool(f"{slot}_", 14) for slot in slots}
    mini_pool = make_item_pool("Mini_", 24)
    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_arrays = registry.to_gpu_arrays()

    base_fixed_stats_arr = np.array(
        [
            int(rng.integers(100, 300)),
            int(rng.integers(100, 300)),
            int(rng.integers(100, 300)),
            int(rng.integers(0, 40)),
            int(rng.integers(0, 40)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
        ],
        dtype=np.int32,
    )

    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 1.0, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float64),
    }

    calc_song = _make_calc_song(name="SteadyStateScoreRefresh_BeatVibe", p_color="Beat", s_color="Vibe")
    flags = _color_flags(p_color="Beat", s_color="Vibe", selected_color="Beat")

    genomes: list[list[dict]] = []
    for _g in range(n_genomes):
        gear = [gear_pool[slot][int(rng.integers(0, len(gear_pool[slot])))] for slot in slots]
        minis = [mini_pool[int(i)] for i in rng.choice(len(mini_pool), size=3, replace=False)]
        genomes.append(gear + minis)
    pop_indices = registry.encode_population(genomes)

    with _GPU_LOCK:
        ga_upload_item_stats(gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"])
        ga_upload_base_fixed_stats(base_fixed_stats_arr)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)
        ga_upload_population_indices(pop_indices, n_slots=9)

        ga_evaluate_population(
            n_genomes=n_genomes,
            n_slots=9,
            total_budget=total_budget,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=0,
            is_p_ft=flags["is_p_ft"],
            is_s_ft=flags["is_s_ft"],
            is_p_ff=flags["is_p_ff"],
            is_s_ff=flags["is_s_ff"],
            is_p_pp=flags["is_p_pp"],
            is_s_pp=flags["is_s_pp"],
            is_p_cm=flags["is_p_cm"],
            is_s_cm=flags["is_s_cm"],
            is_p_fm=flags["is_p_fm"],
            is_s_fm=flags["is_s_fm"],
            is_p_ov=flags["is_p_ov"],
            is_s_ov=flags["is_s_ov"],
            materialize_mode="none",
        )
        best_keys = np.asarray(gpu_fields.chunk_best_key.to_numpy()[:n_genomes], dtype=np.uint64)
        raw_key_scores = (best_keys >> np.uint64(32)).astype(np.int64) - 1

        ga_write_best_and_update_global(
            n_genomes=n_genomes,
            n_slots=9,
            total_budget=total_budget,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=0,
            is_p_ft=flags["is_p_ft"],
            is_s_ft=flags["is_s_ft"],
            is_p_ff=flags["is_p_ff"],
            is_s_ff=flags["is_s_ff"],
            is_p_pp=flags["is_p_pp"],
            is_s_pp=flags["is_s_pp"],
            is_p_cm=flags["is_p_cm"],
            is_s_cm=flags["is_s_cm"],
            is_p_fm=flags["is_p_fm"],
            is_s_fm=flags["is_s_fm"],
            is_p_ov=flags["is_p_ov"],
            is_s_ov=flags["is_s_ov"],
        )
        results = ga_download_results(n_genomes)
        scores = ga_download_scores(n_genomes)

    assert np.array_equal(scores, results[:, 0])
    mismatch = np.count_nonzero(raw_key_scores.astype(np.int32) != results[:, 0])
    assert mismatch == 0


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_light_refresh_and_fg_pack_match_full_materialization() -> None:
    n_runs = 3
    n_genomes_per_run = 32
    n_genomes = n_runs * n_genomes_per_run
    total_budget = 90
    song_slot = 0

    rng = np.random.default_rng(20260424)
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    def make_item_pool(prefix: str, n: int) -> list[dict]:
        items: list[dict] = []
        for i in range(n):
            items.append(
                _mk_item(
                    f"{prefix}{i}",
                    **{
                        "Perfect Points": int(rng.integers(0, 120)),
                        "Combo Multiplier": int(rng.integers(0, 120)),
                        "Fever Multiplier": int(rng.integers(0, 120)),
                        "Fever Time": int(rng.integers(0, 40)),
                        "Fever Fill Rate": int(rng.integers(0, 40)),
                        "Beat": int(rng.integers(0, 200)),
                        "Vibe": int(rng.integers(0, 200)),
                        "Rush": int(rng.integers(0, 200)),
                        "Flow": int(rng.integers(0, 200)),
                        "Chill": int(rng.integers(0, 200)),
                    },
                )
            )
        return items

    def build_expected_top_rows(
        *,
        scores: np.ndarray,
        results: np.ndarray,
        base_stats: np.ndarray,
        population: np.ndarray,
        k: int,
    ) -> np.ndarray:
        expected = np.zeros((n_runs, k, 24), dtype=np.int32)
        for run_idx in range(n_runs):
            start = run_idx * n_genomes_per_run
            top_scores = np.full((k,), np.iinfo(np.int32).min, dtype=np.int32)
            top_idx = np.full((k,), -1, dtype=np.int32)
            for local_g in range(n_genomes_per_run):
                g = start + local_g
                score = int(scores[g])
                if score <= 0:
                    continue
                for j in range(k):
                    if score > int(top_scores[j]):
                        if j + 1 < k:
                            top_scores[j + 1 :] = top_scores[j:-1]
                            top_idx[j + 1 :] = top_idx[j:-1]
                        top_scores[j] = score
                        top_idx[j] = g
                        break

            for j in range(k):
                g = int(top_idx[j])
                if g < 0 or int(top_scores[j]) <= 0:
                    continue
                ids = np.asarray(population[g], dtype=np.int32).copy()
                ids[6:9] = np.sort(ids[6:9])
                expected[run_idx, j, 0] = int(scores[g])
                expected[run_idx, j, 1:10] = ids
                expected[run_idx, j, 10:17] = np.asarray(results[g], dtype=np.int32)
                expected[run_idx, j, 17:24] = np.asarray(base_stats[g], dtype=np.int32)
        return expected

    gear_pool = {slot: make_item_pool(f"{slot}_", 14) for slot in slots}
    mini_pool = make_item_pool("Mini_", 24)
    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_arrays = registry.to_gpu_arrays()

    base_fixed_stats_arr = np.array(
        [
            int(rng.integers(100, 300)),
            int(rng.integers(100, 300)),
            int(rng.integers(100, 300)),
            int(rng.integers(0, 40)),
            int(rng.integers(0, 40)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
            int(rng.integers(200, 400)),
        ],
        dtype=np.int32,
    )

    ref_arrays = {
        "Perfect Points": np.linspace(0.0, 1.0, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 3.0, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float64),
    }

    calc_song = _make_calc_song(name="LightRefreshFGPack_BeatVibe", p_color="Beat", s_color="Vibe")
    flags = _color_flags(p_color="Beat", s_color="Vibe", selected_color="Beat")

    genomes: list[list[dict]] = []
    for _g in range(n_genomes):
        gear = [gear_pool[slot][int(rng.integers(0, len(gear_pool[slot])))] for slot in slots]
        minis = [mini_pool[int(i)] for i in rng.choice(len(mini_pool), size=3, replace=False)]
        genomes.append(gear + minis)
    pop_indices = registry.encode_population(genomes)

    with _GPU_LOCK:
        ga_upload_item_stats(gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"])
        ga_upload_base_fixed_stats(base_fixed_stats_arr)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
        ga_upload_population_indices(pop_indices, n_slots=9)
        ga_init_runs_best(run_idx_start=0, n_runs=n_runs, n_slots=9)

        ga_evaluate_population(
            n_genomes=n_genomes,
            n_slots=9,
            total_budget=total_budget,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=song_slot,
            is_p_ft=flags["is_p_ft"],
            is_s_ft=flags["is_s_ft"],
            is_p_ff=flags["is_p_ff"],
            is_s_ff=flags["is_s_ff"],
            is_p_pp=flags["is_p_pp"],
            is_s_pp=flags["is_s_pp"],
            is_p_cm=flags["is_p_cm"],
            is_s_cm=flags["is_s_cm"],
            is_p_fm=flags["is_p_fm"],
            is_s_fm=flags["is_s_fm"],
            is_p_ov=flags["is_p_ov"],
            is_s_ov=flags["is_s_ov"],
            materialize_mode="none",
        )

        ga_refresh_scores_and_update_runs_best(
            run_idx_start=0,
            n_runs=n_runs,
            n_genomes_per_run=n_genomes_per_run,
            n_slots=9,
            total_budget=total_budget,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=song_slot,
            is_p_ft=flags["is_p_ft"],
            is_s_ft=flags["is_s_ft"],
            is_p_ff=flags["is_p_ff"],
            is_s_ff=flags["is_s_ff"],
            is_p_pp=flags["is_p_pp"],
            is_s_pp=flags["is_s_pp"],
            is_p_cm=flags["is_p_cm"],
            is_s_cm=flags["is_s_cm"],
            is_p_fm=flags["is_p_fm"],
            is_s_fm=flags["is_s_fm"],
            is_p_ov=flags["is_p_ov"],
            is_s_ov=flags["is_s_ov"],
        )
        light_scores = ga_download_scores(n_genomes).copy()
        light_row0 = np.asarray(gpu_fields.ga_runs_payload_packed.to_numpy()[:n_runs, 0, :], dtype=np.int32)

        ga_pack_fg_candidates_table_segmented(
            table_slot=song_slot,
            run_idx_start=0,
            n_runs=n_runs,
            n_genomes_per_run=n_genomes_per_run,
            n_slots=9,
            total_budget=total_budget,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=song_slot,
            is_p_ft=flags["is_p_ft"],
            is_s_ft=flags["is_s_ft"],
            is_p_ff=flags["is_p_ff"],
            is_s_ff=flags["is_s_ff"],
            is_p_pp=flags["is_p_pp"],
            is_s_pp=flags["is_s_pp"],
            is_p_cm=flags["is_p_cm"],
            is_s_cm=flags["is_s_cm"],
            is_p_fm=flags["is_p_fm"],
            is_s_fm=flags["is_s_fm"],
            is_p_ov=flags["is_p_ov"],
            is_s_ov=flags["is_s_ov"],
        )
        k = int(gpu_fields.GA_FG_CANDIDATES_PER_RUN)
        light_fg_rows = np.asarray(
            gpu_fields.ga_fg_candidates_packed.to_numpy()[song_slot, :n_runs, 1 : (k + 1), :],
            dtype=np.int32,
        )

        ga_init_runs_best(run_idx_start=0, n_runs=n_runs, n_slots=9)
        ga_write_best_results_and_update_runs_best(
            run_idx_start=0,
            n_runs=n_runs,
            n_genomes_per_run=n_genomes_per_run,
            n_slots=9,
            total_budget=total_budget,
            gem_scale_fever=GEM_SCALE_FEVER,
            song_slot=song_slot,
            is_p_ft=flags["is_p_ft"],
            is_s_ft=flags["is_s_ft"],
            is_p_ff=flags["is_p_ff"],
            is_s_ff=flags["is_s_ff"],
            is_p_pp=flags["is_p_pp"],
            is_s_pp=flags["is_s_pp"],
            is_p_cm=flags["is_p_cm"],
            is_s_cm=flags["is_s_cm"],
            is_p_fm=flags["is_p_fm"],
            is_s_fm=flags["is_s_fm"],
            is_p_ov=flags["is_p_ov"],
            is_s_ov=flags["is_s_ov"],
        )
        full_scores = ga_download_scores(n_genomes)
        full_results = ga_download_results(n_genomes)
        full_row0 = np.asarray(gpu_fields.ga_runs_payload_packed.to_numpy()[:n_runs, 0, :], dtype=np.int32)
        base_stats = np.asarray(gpu_fields.genome_base_stats.to_numpy()[:n_genomes], dtype=np.int32)

    assert np.array_equal(light_scores, full_scores)
    assert np.array_equal(light_row0, full_row0)

    expected_fg_rows = build_expected_top_rows(
        scores=full_scores,
        results=full_results,
        base_stats=base_stats,
        population=pop_indices,
        k=k,
    )
    assert np.array_equal(light_fg_rows, expected_fg_rows)
