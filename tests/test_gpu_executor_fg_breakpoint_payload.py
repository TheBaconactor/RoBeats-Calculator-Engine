import numpy as np
import pytest

from gear_optimizer.solver.gpu_executor_fg import (
    maybe_precompute_fg_breakpoint_timeline,
    prepare_fg_breakpoint_payload_inputs,
    prepare_fg_breakpoint_solve_submission,
)


def _payload(**overrides):
    payload = {
        "n_sections": 2,
        "ftff_pairs": [[1, 2]],
        "base_stats_pairs": [[10, 20], [30, 40]],
        "non_fever_base_by_ff": np.zeros((161,), dtype=np.int16),
        "fp_cap_table": np.zeros((161, 51), dtype=np.int16),
        "song_slot": 3,
        "gem_scale_fever": 5,
        "solve_kwargs": {"total_budget": 90},
    }
    payload.update(overrides)
    return payload


def test_prepare_fg_breakpoint_payload_inputs_returns_none_for_no_sections():
    assert prepare_fg_breakpoint_payload_inputs({"n_sections": 0}) is None


def test_prepare_fg_breakpoint_payload_inputs_returns_none_for_empty_pairs():
    prepared = prepare_fg_breakpoint_payload_inputs(_payload(ftff_pairs=np.zeros((0, 2), dtype=np.int32)))

    assert prepared is None


def test_prepare_fg_breakpoint_payload_inputs_requires_breakpoint_inputs():
    with pytest.raises(ValueError, match="missing required breakpoint inputs"):
        prepare_fg_breakpoint_payload_inputs({"n_sections": 1})


def test_prepare_fg_breakpoint_payload_inputs_validates_pair_shape():
    with pytest.raises(ValueError, match="ftff_pairs must be shape"):
        prepare_fg_breakpoint_payload_inputs(_payload(ftff_pairs=[1, 2, 3]))


def test_prepare_fg_breakpoint_payload_inputs_normalizes_arrays_and_config():
    prepared = prepare_fg_breakpoint_payload_inputs(
        _payload(
            ftff_pairs=np.asarray([[1, 2, 9]], dtype=np.int64),
            base_stats_pairs=np.asarray([[10, 20, 99], [30, 40, 88]], dtype=np.int64),
        ),
        env_get=lambda _key, _default: "1",
    )

    assert prepared is not None
    assert prepared.n_sections == 2
    assert prepared.song_slot == 3
    assert prepared.gem_scale_fever == 5
    assert prepared.implicit_cfgs is True
    assert prepared.solve_kwargs_payload == {"total_budget": 90}
    assert prepared.pairs_arr.dtype == np.int32
    assert prepared.base_arr.dtype == np.int32
    assert prepared.pairs_arr.flags.c_contiguous
    assert prepared.base_arr.flags.c_contiguous
    np.testing.assert_array_equal(prepared.base_ft, np.asarray([10, 30], dtype=np.int32))
    np.testing.assert_array_equal(prepared.base_ff, np.asarray([20, 40], dtype=np.int32))


def test_prepare_fg_breakpoint_payload_inputs_reads_implicit_cfg_env():
    prepared = prepare_fg_breakpoint_payload_inputs(_payload(), env_get=lambda _key, _default: "0")

    assert prepared is not None
    assert prepared.implicit_cfgs is False


def test_maybe_precompute_fg_breakpoint_timeline_ignores_disabled_payload():
    calls = []

    maybe_precompute_fg_breakpoint_timeline(
        {"ensure_timeline_precompute": False},
        precompute_timeline_fn=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert calls == []


def test_maybe_precompute_fg_breakpoint_timeline_requires_dict_inputs():
    calls = []

    maybe_precompute_fg_breakpoint_timeline(
        {"ensure_timeline_precompute": True, "calc_song": {}, "solve_kwargs": {"ref_arrays": object()}},
        precompute_timeline_fn=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert calls == []


def test_maybe_precompute_fg_breakpoint_timeline_forwards_song_slot():
    calls = []
    calc_song = {"song_data": {}}
    ref_arrays = {"refs": True}

    maybe_precompute_fg_breakpoint_timeline(
        {
            "ensure_timeline_precompute": True,
            "calc_song": calc_song,
            "song_slot": 6,
            "solve_kwargs": {"ref_arrays": ref_arrays},
        },
        precompute_timeline_fn=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert calls == [((calc_song, ref_arrays), {"song_slot": 6})]


def test_maybe_precompute_fg_breakpoint_timeline_swallows_precompute_error():
    maybe_precompute_fg_breakpoint_timeline(
        {
            "ensure_timeline_precompute": True,
            "calc_song": {},
            "solve_kwargs": {"ref_arrays": {}},
        },
        precompute_timeline_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )


def test_prepare_fg_breakpoint_solve_submission_uses_genome_stats_length():
    genome_stats = [object(), object()]

    submission = prepare_fg_breakpoint_solve_submission(
        {
            "genome_stats_list": genome_stats,
            "timestamps_np": "timestamps",
            "great_candidate_timestamps_np": "greats",
            "long_notes": 1,
            "last_note_time": 9.5,
        },
        {"n_genomes_override": 99, "song_slot": 4},
    )

    assert submission.n_genomes == 2
    assert submission.genome_stats_list is genome_stats
    assert submission.timestamps_np == "timestamps"
    assert submission.great_candidate_timestamps_np == "greats"
    assert submission.long_notes == 1
    assert submission.last_note_time == 9.5
    assert submission.kwargs_local["accumulate_global"] is True
    assert submission.kwargs_local["return_raw"] is True
    assert "n_genomes_override" not in submission.kwargs_local
    assert submission.kwargs_local["song_slot"] == 4


def test_prepare_fg_breakpoint_solve_submission_uses_override_when_stats_absent():
    submission = prepare_fg_breakpoint_solve_submission({}, {"n_genomes_override": 3})

    assert submission.n_genomes == 3


def test_prepare_fg_breakpoint_solve_submission_rejects_empty_genome_count():
    with pytest.raises(ValueError, match="n_genomes <= 0"):
        prepare_fg_breakpoint_solve_submission({}, {})


def test_prepare_fg_breakpoint_solve_submission_rejects_removed_preupload_paths():
    with pytest.raises(ValueError, match="removed"):
        prepare_fg_breakpoint_solve_submission(
            {"ga_stage_coords": np.asarray([[0, 1]], dtype=np.int32)},
            {"n_genomes_override": 1},
        )

    with pytest.raises(ValueError, match="removed"):
        prepare_fg_breakpoint_solve_submission(
            {},
            {"n_genomes_override": 1, "genome_stats_preuploaded": True},
        )
