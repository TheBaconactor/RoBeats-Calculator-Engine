"""Exact cross-generation reuse against fresh GPU evaluation."""

import numpy as np
import pytest

from tests.curves_support import synthetic_curves
from tests.test_gpu_ga_eval_incumbent_cull import (
    _GPU_LOCK,
    _N_GENOMES,
    _song,
    _curves,
    _run_production_eval,
    eval_device_state as eval_device_state,
)

pytestmark = pytest.mark.gpu


def test_repeated_generation_reuses_complete_winners(eval_device_state):
    from gear_optimizer.solver.taichi_gem import fields

    with _GPU_LOCK:
        first = _run_production_eval(eval_device_state)
        second = _run_production_eval(eval_device_state)
        for expected, actual in zip(first, second, strict=True):
            np.testing.assert_array_equal(actual, expected)
        assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 0


def test_reference_reload_cannot_reuse_old_scores(eval_device_state):
    from gear_optimizer.solver.taichi_gem.api.ga_operations import reset_ga_evaluation_cache
    from gear_optimizer.solver.taichi_gem.api.initialization import load_curves

    with _GPU_LOCK:
        original = _run_production_eval(eval_device_state)
        changed = synthetic_curves({"Perfect Points": _curves().f64["Perfect Points"] * 1.5})
        try:
            load_curves(changed)
            actual = _run_production_eval(eval_device_state)
            reset_ga_evaluation_cache()
            fresh = _run_production_eval(eval_device_state)
            assert not np.array_equal(actual[0], original[0])
            for a, b in zip(actual, fresh, strict=True):
                np.testing.assert_array_equal(a, b)
        finally:
            load_curves(_curves())


@pytest.mark.parametrize("timing_mode,n_notes", [("precise", 80), ("non-precise", 400)])
def test_replacing_song_slot_or_timing_cannot_reuse_old_scores(eval_device_state, timing_mode, n_notes):
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api.ga_operations import reset_ga_evaluation_cache
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload, precompute_timeline_gpu,
    )

    def upload(mode, notes):
        song = _song(n_notes=notes, mode=mode)
        refs = _curves()
        payload = build_or_load_timeline_frontier_payload(song, refs)
        precompute_timeline_gpu(song, refs, song_slot=0, prebuilt_frontier=payload)

    with _GPU_LOCK:
        _run_production_eval(eval_device_state)
        try:
            upload(timing_mode, n_notes)
            assert not np.any(fields.ga_eval_cache_key.to_numpy())
            actual = _run_production_eval(eval_device_state)
            reset_ga_evaluation_cache()
            fresh = _run_production_eval(eval_device_state)
            for a, b in zip(actual, fresh, strict=True):
                np.testing.assert_array_equal(a, b)
        finally:
            upload("precise", 400)


def test_loading_another_run_batch_discards_cached_winners(eval_device_state):
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api.ga_operations import ga_load_initial_populations_batch

    with _GPU_LOCK:
        _run_production_eval(eval_device_state)
        assert np.any(fields.ga_eval_cache_key.to_numpy())
        ga_load_initial_populations_batch(run_idx_start=0, n_runs=1, n_genomes_per_run=_N_GENOMES)
        assert not np.any(fields.ga_eval_cache_key.to_numpy())


def test_changed_budget_clears_live_winners_without_reaggregation(eval_device_state):
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api.ga_operations import (
        ga_evaluate_prepared_population, reset_ga_evaluation_cache,
    )

    with _GPU_LOCK:
        old = _run_production_eval(eval_device_state)
        kwargs = dict(flags=eval_device_state, total_budget=0)
        ga_evaluate_prepared_population(_N_GENOMES, **kwargs)
        assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) > 0
        actual = fields.chunk_best_key.to_numpy()[:_N_GENOMES]
        assert not np.array_equal(actual, old[0])
        reset_ga_evaluation_cache()
        fields.chunk_best_key.fill(0)
        ga_evaluate_prepared_population(_N_GENOMES, **kwargs)
        np.testing.assert_array_equal(fields.chunk_best_key.to_numpy()[:_N_GENOMES], actual)
