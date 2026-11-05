"""Exact cross-generation reuse against fresh GPU evaluation."""

import numpy as np
import pytest

from tests.curves_support import synthetic_curves
from tests.test_gpu_ga_eval_incumbent_cull import (
    _GPU_LOCK,
    _N_GENOMES,
    _PRIMARY_COLOR,
    _SECONDARY_COLOR,
    _SELECTED_COLOR,
    _TOTAL_BUDGET,
    _song,
    _curves,
    _run_production_eval,
    eval_device_state as eval_device_state,
)

pytestmark = pytest.mark.gpu


def test_repeated_generation_reuses_complete_winners(eval_device_state):
    from gear_optimizer.gpu import fields

    with _GPU_LOCK:
        first = _run_production_eval(eval_device_state)
        second = _run_production_eval(eval_device_state)
        for expected, actual in zip(first, second, strict=True):
            np.testing.assert_array_equal(actual, expected)
        assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 0


def test_reference_reload_cannot_reuse_old_scores(eval_device_state):
    from gear_optimizer.gpu.api.ga_operations import reset_ga_evaluation_cache
    from gear_optimizer.gpu.api.initialization import load_curves

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
    from gear_optimizer.gpu import fields
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.pipeline.prepare import ga_ftff_shortlist
    from gear_optimizer.gpu.api.ga_operations import ga_upload_ftff_shortlist, reset_ga_evaluation_cache
    from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload
    from gear_optimizer.gpu.api.timeline import precompute_timeline_gpu

    def upload(mode, notes):
        # As the GA's state restore: the song's timeline with its shortlist (every key).
        song = _song(n_notes=notes, mode=mode)
        refs = _curves()
        payload = build_or_load_timeline_frontier_payload(song, refs)
        precompute_timeline_gpu(song, refs, song_slot=0, prebuilt_payload=payload.payload)
        shortlist = ga_ftff_shortlist(payload.payload, reach=np.ones((161, 161), dtype=bool),
                                      color_flags=build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR))
        ga_upload_ftff_shortlist(shortlist, song_key=song.timeline_key)

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
    from gear_optimizer.gpu import fields
    from gear_optimizer.gpu.api.ga_operations import ga_load_initial_populations_batch

    with _GPU_LOCK:
        _run_production_eval(eval_device_state)
        assert np.any(fields.ga_eval_cache_key.to_numpy())
        ga_load_initial_populations_batch(run_idx_start=0, n_runs=1, n_genomes_per_run=_N_GENOMES)
        assert not np.any(fields.ga_eval_cache_key.to_numpy())


def test_changed_budget_clears_live_winners_without_reaggregation(eval_device_state):
    from gear_optimizer.gpu import fields
    from gear_optimizer.solver.ftff_combos import FtffShortlist
    from gear_optimizer.gpu.api.ga_operations import (
        ga_evaluate_prepared_population, ga_upload_ftff_shortlist, reset_ga_evaluation_cache,
    )

    keys = 161 * 161
    song = _song()
    # With no gems the only combo is (0, 0), index 0: every key's shortlist.
    no_gems = FtffShortlist(np.arange(keys, dtype=np.int32), np.ones(keys, dtype=np.int32),
                            np.zeros(keys, dtype=np.int32), 0)
    with _GPU_LOCK:
        old = _run_production_eval(eval_device_state)
        try:
            ga_upload_ftff_shortlist(no_gems, song_key=song.timeline_key)
            kwargs = dict(flags=eval_device_state, total_budget=0)
            ga_evaluate_prepared_population(_N_GENOMES, **kwargs)
            assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) > 0
            actual = fields.chunk_best_key.to_numpy()[:_N_GENOMES]
            assert not np.array_equal(actual, old[0])
            reset_ga_evaluation_cache()
            fields.chunk_best_key.fill(0)
            ga_evaluate_prepared_population(_N_GENOMES, **kwargs)
            np.testing.assert_array_equal(fields.chunk_best_key.to_numpy()[:_N_GENOMES], actual)
        finally:
            _upload_fixture_shortlist()


def _upload_fixture_shortlist():
    """The fixture song's shortlist (every key)."""
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.pipeline.prepare import ga_ftff_shortlist
    from gear_optimizer.gpu.api.ga_operations import ga_upload_ftff_shortlist
    from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload

    song = _song()
    payload = build_or_load_timeline_frontier_payload(song, _curves()).payload
    shortlist = ga_ftff_shortlist(payload, reach=np.ones((161, 161), dtype=bool),
                                  color_flags=build_color_flags(_PRIMARY_COLOR, _SECONDARY_COLOR, _SELECTED_COLOR))
    ga_upload_ftff_shortlist(shortlist, song_key=song.timeline_key)


def test_evaluation_refuses_a_shortlist_of_another_song_or_combo_table(eval_device_state):
    from gear_optimizer.solver.ftff_combos import FtffShortlist
    from gear_optimizer.gpu.api.ga_operations import (
        ga_evaluate_prepared_population, ga_upload_ftff_shortlist,
    )

    keys = 161 * 161
    with _GPU_LOCK:
        with pytest.raises(RuntimeError, match="indexes the combo table"):
            ga_evaluate_prepared_population(_N_GENOMES, flags=eval_device_state, total_budget=_TOTAL_BUDGET - 1)
        try:
            ga_upload_ftff_shortlist(
                FtffShortlist(np.zeros(keys, dtype=np.int32), np.zeros(keys, dtype=np.int32),
                              np.zeros(0, dtype=np.int32), _TOTAL_BUDGET),
                song_key=("another song",),
            )
            with pytest.raises(RuntimeError, match="not the evaluated song's"):
                ga_evaluate_prepared_population(_N_GENOMES, flags=eval_device_state, total_budget=_TOTAL_BUDGET)
        finally:
            _upload_fixture_shortlist()
