from gear_optimizer.solver.native_inflight_config import make_native_song

import pytest
import numpy as np


def test_ftff_response_position_prune_matches_pair_prune_with_canonical_frontier_keys():
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import (
        prune_dominated_ftff_response_pairs,
        prune_dominated_ftff_response_positions,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult

    frontiers = tuple(FgResponseFrontierResult((), {}, 0, 0, 0, 0, 0, 0, 0, 0.0) for _ in range(4))
    frontier_classes = (0, 0, 1, 2)
    class_by_frontier_id = {id(frontier): int(frontier_classes[idx]) for idx, frontier in enumerate(frontiers)}
    rows = [
        (0, 5, 10, 10),
        (1, 6, 9, 10),
        (1, 6, 11, 10),
        (2, 2, 5, 5),
        (2, 4, 5, 5),
        (3, 7, 12, 8),
        (3, 6, 8, 12),
        (3, 5, 7, 7),
    ]
    pairs = [
        (
            int(idx),
            0,
            int(residual),
            (0, 0, 0, int(primary), int(secondary), 0, 0),
            frontiers[int(frontier_idx)],
            0.0,
            0.0,
        )
        for idx, (frontier_idx, residual, primary, secondary) in enumerate(rows)
    ]

    expected = prune_dominated_ftff_response_pairs(
        pairs,
        primary_color="Beat",
        secondary_color="Vibe",
        frontier_key_of=lambda pair: class_by_frontier_id[id(pair[4])],
    )
    positions = np.arange(len(rows), dtype=np.int32)
    got = prune_dominated_ftff_response_positions(
        positions=positions,
        frontier_ids=np.asarray([frontier_classes[frontier_idx] for frontier_idx, *_rest in rows], dtype=np.int32),
        residuals=np.asarray([residual for _frontier_idx, residual, _primary, _secondary in rows], dtype=np.int32),
        primary_values=np.asarray([primary for _frontier_idx, _residual, primary, _secondary in rows], dtype=np.int32),
        secondary_values=np.asarray([secondary for _frontier_idx, _residual, _primary, secondary in rows], dtype=np.int32),
    )

    assert got.tolist() == [int(pair[0]) for pair in expected]


def test_nojit_fixed_stats_score_matches_jit_score():
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score, evaluate_stats_score_nojit

    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 1,
            "Last Note Time": 1.5,
        },
        "song_data": {"timestamps": np.asarray([0.0, 0.25, 0.5, 1.0, 1.5], dtype=np.float32)},
    }
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }
    stats = {
        "Perfect Points": 37,
        "Combo Multiplier": 41,
        "Fever Multiplier": 59,
        "Fever Time": 23,
        "Fever Fill Rate": 29,
        "Rush": 101,
        "Flow": 83,
    }

    assert evaluate_stats_score_nojit(stats, calc_song, ref_arrays) == evaluate_stats_score(stats, calc_song, ref_arrays)


def test_process_force_greats_response_frontier_failure_raises_directly(monkeypatch):
    from gear_optimizer.helpers.song_helpers import force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter

    def _boom(*_args, **_kwargs):
        raise RuntimeError("response frontier path failed")

    monkeypatch.setattr(adapter, "process_force_greats_response_frontier_gpu", _boom)

    class _Registry:
        @staticmethod
        def decode_names(ids):
            return [f"I{int(x)}" for x in ids[:9]]

    ga_candidates = [
        {
            "BaseScore": 321,
            "GenomeIDs": [1, 2, 3, 4, 5, 6, 9, 8, 7],
            "Data": {
                "BaseStats": {"Perfect Points": 5, "Rush": 7},
                "GemCounts": {"Perfect Points": 1},
                "FT": 1,
                "FF": 2,
                "Selected Element": "Rush",
            },
        }
    ]

    with pytest.raises(RuntimeError, match="response frontier path failed"):
        force_greats.process_force_greats(
            loadout_entries={},
            calc_song={"metadata": {}, "song_data": {}},
            ref_arrays={},
            meta_primary_color="Rush",
            ga_candidates=ga_candidates,
            ga_registry=_Registry(),
        )


def test_prepare_fg_job_sync_uses_db_only_entries_for_response_frontier_route(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter

    seen = {"ga_n": None}

    def _fake_build_loadout_entries(
        found_song_name,
        ga_candidates,
        gears_by_name,
        minis_by_name,
        build_details_fn,
        team_buff="T5",
        materialize_ga_details=True,
        ga_registry=None,
    ):
        seen["ga_n"] = len(ga_candidates or [])
        return {}

    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)
    monkeypatch.setattr(
        response_frontier_adapter,
        "prepare_force_greats_response_frontier_plan",
        lambda *_args, **_kwargs: "prepared-plan",
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[
            {
                "Score": 100,
                "BaseScore": 100,
                "GenomeIDs": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert seen["ga_n"] == 0
    assert song.runtime.fg.fg_direct_ga_candidates is True
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"
    assert len(song.runtime.decode.ga_candidates or []) == 1


def test_prepare_fg_job_sync_canonicalizes_gpu_payload_before_response_frontier(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter

    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        response_frontier_adapter,
        "prepare_force_greats_response_frontier_plan",
        lambda *_args, **_kwargs: "prepared-plan",
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    duplicate_prefix = [
        {
            "Score": 1000 - i,
            "BaseScore": 1000 - i,
            "Gear": ["DupG1", "DupG2", "DupG3", "DupG4", "DupG5", "DupG6"],
            "Minis": ["DupM1", "DupM2", "DupM3"],
            "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": i, "Selected Element": "Rush"},
        }
        for i in range(60)
    ]
    keeper = {
        "Score": 100,
        "BaseScore": 100,
        "Gear": ["KeepG1", "KeepG2", "KeepG3", "KeepG4", "KeepG5", "KeepG6"],
        "Minis": ["KeepM1", "KeepM2", "KeepM3"],
        "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": 60, "Selected Element": "Rush"},
    }

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=duplicate_prefix + [keeper],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    selected = song.runtime.decode.ga_candidates or []
    assert len(selected) == 2
    assert any((cand.get("Gear") or [None])[0] == "KeepG1" for cand in selected)
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"


def test_prepare_fg_job_sync_does_not_prune_exact_fg_prep_by_fg_candidate_limit(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter

    seen: dict[str, int] = {}

    def _assert_lossless_selector(candidates, *, limit, **_kwargs):
        seen["candidate_count"] = len(candidates or [])
        seen["limit"] = int(limit)
        if int(limit) < len(candidates or []):
            raise AssertionError("exact FG prep may not use FG_CandidateLimit as a pruning cap")
        return list(candidates or [])

    monkeypatch.setattr(stages, "select_effective_unique_ga_candidates", _assert_lossless_selector)
    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        response_frontier_adapter,
        "prepare_force_greats_response_frontier_plan",
        lambda *_args, **_kwargs: "prepared-plan",
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}
    ga_candidates = [
        {
            "Score": 1000 - i,
            "BaseScore": 1000 - i,
            "Gear": [f"G{i}_{slot}" for slot in range(6)],
            "Minis": [f"M{i}_{slot}" for slot in range(3)],
            "Data": {"_ga_gpu_run_idx": 0, "_ga_gpu_row_idx": i, "Selected Element": "Rush"},
        }
        for i in range(77)
    ]

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=ga_candidates,
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={"selected_color": "Rush"},
        ref_arrays={},
        song_slot=1,
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert seen == {"candidate_count": 77, "limit": 77}
    assert len(song.runtime.decode.ga_candidates or []) == 77
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"


def test_prepare_fg_job_sync_does_not_wait_for_cpu_prewarm_before_dynamic_prep(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter

    seen: dict[str, bool] = {"waited": False, "built": False}

    class _PrewarmFuture:
        def result(self):
            seen["waited"] = True
            raise AssertionError("FG dynamic prep must not block on broad CPU prewarm")

    def _fake_build_loadout_entries(*_args, **_kwargs):
        seen["built"] = True
        return {}

    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(stages, "build_loadout_entries", _fake_build_loadout_entries)
    monkeypatch.setattr(
        response_frontier_adapter,
        "prepare_force_greats_response_frontier_plan",
        lambda *_args, **_kwargs: "prepared-plan",
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}

    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {}},
        cfg_dict={},
        ga_candidates=[{"BaseScore": 100, "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
        cpu_prewarm_future=_PrewarmFuture(),
    )

    stages.prepare_fg_job_sync(song, gpu_client=None)

    assert seen == {"waited": False, "built": True}
    assert song.runtime.fg.fg_response_frontier_plan == "prepared-plan"


def test_prepare_fg_job_sync_requires_materialized_response_frontier_plan(monkeypatch):
    import configparser

    import gear_optimizer.solver.native_inflight_pipeline as stages
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter

    monkeypatch.setattr(stages, "hydrate_fg_candidate_stats", lambda *args, **kwargs: None)
    monkeypatch.setattr(stages, "build_loadout_entries", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        response_frontier_adapter,
        "prepare_force_greats_response_frontier_plan",
        lambda *_args, **_kwargs: None,
    )

    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"FG_CandidateLimit": "51"}
    song = make_native_song(
        cfg=cfg,
        calc_song={"metadata": {}, "song_data": {"notes": [{"time": 1.0}]}},
        cfg_dict={},
        ga_candidates=[{"BaseScore": 100, "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"}}],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        db_key="song-db-key",
        gears_by_name={},
        minis_by_name={},
        effective_difficulty="Hard",
        registry=None,
        fixed_stats={},
        cfg_data={},
        ref_arrays={},
    )

    with pytest.raises(RuntimeError, match="did not materialize the exact response frontier plan"):
        stages.prepare_fg_job_sync(song, gpu_client=None)


def test_process_force_greats_forwards_direct_ga_candidates_to_response_frontier(monkeypatch):
    from gear_optimizer.helpers.song_helpers import force_greats
    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter

    seen: list[tuple[int, object]] = []
    registry = object()

    def _fake_response_frontier(
        loadout_entries,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        ga_candidates=None,
        ga_registry=None,
        score_prepared_batch=None,
    ):
        _ = (
            loadout_entries,
            calc_song,
            ref_arrays,
            meta_primary_color,
            ga_registry,
            score_prepared_batch,
        )
        seen.append((len(list(ga_candidates or [])), ga_registry))
        return [
            {
                "data": {
                    "Score": 100 + len(seen),
                    "BaseScore": 90,
                    "ForceGreats": {"config": {"NonFever1": 1}},
                },
                "gear": [f"G{len(seen)}"],
                "minis": [f"M{len(seen)}"],
                "score": 90,
                "fg_score": 100 + len(seen),
            }
        ]

    monkeypatch.setattr(adapter, "process_force_greats_response_frontier_gpu", _fake_response_frontier)

    ga_candidates = [
        {
            "Gear": ["A"],
            "Minis": ["B"],
            "BaseScore": 90,
            "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
        }
    ]

    out = force_greats.process_force_greats(
        loadout_entries={},
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        meta_primary_color="Rush",
        ga_candidates=ga_candidates,
        ga_registry=registry,
    )

    assert seen == [(1, registry)]
    assert len(out) == 1
    assert int(out[0]["fg_score"]) == 101


def test_force_payload_uses_supplied_reconstruction_frontier(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    scoring_frontier = FgResponseFrontierResult((surface,), {}, 1, 1, 1, 1, 1, 1, 7, 0.0)
    full_frontier = FgResponseFrontierResult((surface,), {0: (surface,)}, 9, 3, 17, 5, 8, 4, 11, 0.0)
    result = FgResponseFrontierSolveResult(
        best_score=1234,
        ft=1,
        ff=2,
        gem_counts={"Perfect Points": 0},
        stats={"Fever Time": 12, "Fever Fill Rate": 34},
        surface=surface,
        frontier=scoring_frontier,
        inner=FgResponseInnerResult(1234, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        seconds=0.0,
        forced_counts=(),
        raw_fever_fill=1.0,
        real_fever_time=2.0,
    )
    seen = {}

    monkeypatch.setattr(
        adapter,
        "extract_fg_song_inputs",
        lambda calc_song: SimpleNamespace(timestamps=[0.0], great_candidates=[0.0], use_forced_great_timing=True),
    )

    def _fake_reconstruct(**kwargs):
        seen["frontier"] = kwargs["frontier"]
        return (1, 0, 1)

    monkeypatch.setattr(adapter, "reconstruct_force_greats_response_counts", _fake_reconstruct)
    monkeypatch.setattr(adapter, "score_stats_exact", lambda *_args, **_kwargs: 1000)
    monkeypatch.setattr(adapter, "evaluate_force_greats_exact", lambda *_args, **_kwargs: {"final_score": 1230})

    payload = adapter._force_payload_from_response_frontier(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        selected_element="Rush",
        result=result,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        reconstruction_frontier=full_frontier,
    )

    assert seen["frontier"] is full_frontier
    assert payload["forced_counts"] == [1, 0, 1]
    assert payload["Score"] == 1230
    assert payload["ForceGreats"]["final_score"] == 1230
    assert payload["ForceGreats"]["frontier_states"] == 9
    assert payload["ForceGreats"]["non_fever_base"] == 11


def test_force_payload_reconstructs_counts_without_state_frontiers(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    result = FgResponseFrontierSolveResult(
        best_score=1234,
        ft=1,
        ff=2,
        gem_counts={"Perfect Points": 0},
        stats={"Fever Time": 12, "Fever Fill Rate": 34},
        surface=surface,
        frontier=FgResponseFrontierResult((surface,), {}, 1, 1, 1, 1, 1, 1, 7, 0.0),
        inner=FgResponseInnerResult(1234, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        seconds=0.0,
        forced_counts=(),
        raw_fever_fill=1.0,
        real_fever_time=2.0,
    )

    monkeypatch.setattr(
        adapter,
        "extract_fg_song_inputs",
        lambda calc_song: SimpleNamespace(
            total_notes=1,
            timestamps=[0.0],
            great_candidates=[0.0],
            use_forced_great_timing=True,
        ),
    )
    monkeypatch.setattr(adapter, "reconstruct_force_greats_response_counts", lambda **_kwargs: (1, 0, 1))
    monkeypatch.setattr(adapter, "score_stats_exact", lambda *_args, **_kwargs: 1000)
    monkeypatch.setattr(adapter, "evaluate_force_greats_exact", lambda *_args, **_kwargs: {"final_score": 1230})

    payload = adapter._force_payload_from_response_frontier(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        selected_element="Rush",
        result=result,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
    )

    assert payload["forced_counts"] == [1, 0, 1]
    assert payload["Score"] == 1230


def test_response_frontier_route_reconstructs_only_top_limit_candidates(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    scoring_frontier = FgResponseFrontierResult((surface,), {}, 1, 1, 1, 1, 1, 1, 3, 0.0)

    def _result(best_score: int, ft_stat: int, ff_stat: int):
        return FgResponseFrontierSolveResult(
            best_score=best_score,
            ft=1,
            ff=2,
            gem_counts={"Perfect Points": 0},
            stats={"Fever Time": ft_stat, "Fever Fill Rate": ff_stat},
            surface=surface,
            frontier=scoring_frontier,
            inner=FgResponseInnerResult(best_score, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            seconds=0.0,
            forced_counts=(),
            raw_fever_fill=1.0,
            real_fever_time=2.0,
        )

    monkeypatch.setattr(adapter, "LOADOUTS_PER_SONG_LIMIT", 1)
    monkeypatch.setattr(adapter, "eval_data_from_entry", lambda entry, primary: dict(entry["Data"]))
    monkeypatch.setattr(adapter, "expected_selected_element", lambda entry, primary: str(entry["Data"]["Selected Element"]))
    monkeypatch.setattr(adapter, "score_stats_exact", lambda stats, calc_song, ref_arrays: 60)
    monkeypatch.setattr(
        adapter,
        "_base_stats_for_response_frontier",
        lambda eval_data, selected: {"Perfect Points": int(eval_data["pp"])},
    )
    monkeypatch.setattr(adapter, "entry_base_score", lambda entry: int(entry["BaseScore"]))
    monkeypatch.setattr(adapter, "materialize_entry_names", lambda entry, mutate=True: (list(entry["Gear"]), list(entry["Minis"])))
    monkeypatch.setattr(adapter, "extract_fg_song_inputs", lambda calc_song: SimpleNamespace(total_notes=1))
    monkeypatch.setattr(
        adapter,
        "prepare_force_greats_response_frontier_scoring_batch",
        lambda **kwargs: {"base_stats_list": list(kwargs["base_stats_list"])},
    )

    seen_payloads = []

    def _fake_force_payload(*, result, reconstruction_frontier=None, **kwargs):
        seen_payloads.append((int(result.best_score), reconstruction_frontier))
        return {
            "BaseScore": 60,
            "Score": int(result.best_score),
            "ForceGreats": {"config": {"NonFever1": 1}},
            "forced_counts": [1],
        }

    monkeypatch.setattr(adapter, "_force_payload_from_response_frontier", _fake_force_payload)

    entries = {
        "top": {
            "Gear": ["G1"],
            "Minis": ["M1"],
            "BaseScore": 50,
            "Data": {"Selected Element": "Rush", "pp": 1},
        },
        "low": {
            "Gear": ["G2"],
            "Minis": ["M2"],
            "BaseScore": 40,
            "Data": {"Selected Element": "Rush", "pp": 2},
        },
    }

    out = adapter.process_force_greats_response_frontier_gpu(
        entries,
        calc_song={"metadata": {}, "song_data": {}},
        ref_arrays={},
        meta_primary_color="Rush",
        score_prepared_batch=lambda _batch, **_kwargs: [_result(100, 10, 20), _result(90, 30, 40)],
    )

    assert seen_payloads == [(100, None)]
    assert len(out) == 1
    assert int(out[0]["fg_score"]) == 100


def test_response_frontier_cache_validation_rejects_legacy_modes():
    from gear_optimizer.helpers.song_helpers.force_greats.cache_validation import (
        is_cached_force_valid_for_response_frontier,
    )

    payload = {
        "Selected Element": "Rush",
        "ForceGreats": {
            "mode": "finder",
            "config": {"NonFever1": 1},
        },
    }

    assert is_cached_force_valid_for_response_frontier(payload, "Rush") is False

    payload["ForceGreats"]["mode"] = "bellman"
    assert is_cached_force_valid_for_response_frontier(payload, "Rush") is False

    payload["ForceGreats"]["mode"] = "response_frontier"
    assert is_cached_force_valid_for_response_frontier(payload, "Rush") is True


def test_response_frontier_prunes_duplicate_constant_ftff_frontiers_by_best_residual():
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import prune_best_positions_by_frontier

    positions = np.asarray([0, 1, 2, 3], dtype=np.int32)
    frontier_ids = np.asarray([5, 5, 7, 5], dtype=np.int32)
    residuals = np.asarray([1, 3, 2, 2], dtype=np.int32)

    kept_positions = prune_best_positions_by_frontier(
        positions=positions,
        frontier_ids=frontier_ids,
        residuals=residuals,
    )

    np.testing.assert_array_equal(kept_positions, np.asarray([1, 2], dtype=np.int32))


def test_response_frontier_ftff_antichain_prunes_only_same_pack_dominance():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import (
        prune_dominated_ftff_response_pairs,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def frontier():
        return FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )

    pack_a = frontier()
    pack_b = frontier()
    dominated_same_pack = (1, 2, 10, {"Rush": 50, "Flow": 20}, pack_a, 0.0, 0.0)
    dominator_same_pack = (0, 2, 11, {"Rush": 50, "Flow": 21}, pack_a, 0.0, 0.0)
    same_stats_other_pack = (1, 2, 10, {"Rush": 50, "Flow": 20}, pack_b, 0.0, 0.0)

    kept = prune_dominated_ftff_response_pairs(
        [dominated_same_pack, dominator_same_pack, same_stats_other_pack],
        primary_color="Rush",
        secondary_color="Flow",
    )

    assert any(pair is dominator_same_pack for pair in kept)
    assert any(pair is same_stats_other_pack for pair in kept)
    assert not any(pair is dominated_same_pack for pair in kept)


def test_response_frontier_ftff_antichain_matches_naive_dominance():
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_ftff_prune import (
        prune_dominated_ftff_response_pairs,
        response_pair_dominates,
    )

    surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def frontier():
        return FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )

    pack_a = frontier()
    pack_b = frontier()
    pairs = []
    for frontier_obj in (pack_a, pack_b):
        for residual in (7, 8, 9):
            for rush in (10, 12, 12):
                for flow in (4, 5, 7):
                    pairs.append((0, 0, residual, {"Rush": rush, "Flow": flow}, frontier_obj, 0.0, 0.0))

    naive = []
    for pair in pairs:
        if any(
            response_pair_dominates(other, pair, primary_color="Rush", secondary_color="Flow")
            for other in naive
        ):
            continue
        naive = [
            other
            for other in naive
            if not response_pair_dominates(pair, other, primary_color="Rush", secondary_color="Flow")
        ]
        naive.append(pair)

    kept = prune_dominated_ftff_response_pairs(pairs, primary_color="Rush", secondary_color="Flow")

    assert kept == naive


def test_process_force_greats_uses_shared_response_frontier_solver(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    calls = []

    def _result(base_stats, selected_color):
        surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        frontier = FgResponseFrontierResult(
            first_frontier=(surface,),
            state_frontiers={},
            states_evaluated=1,
            actions=1,
            transitions_evaluated=1,
            generated_surfaces=1,
            retained_surfaces_total=1,
            max_state_frontier=1,
            non_fever_base=5,
            seconds=0.0,
        )
        inner = FgResponseInnerResult(
            best_score=150,
            surface_index=0,
            g_pp=1,
            g_cm=2,
            g_fm=3,
            g_ov=4,
            final_pp=11,
            final_cm=12,
            final_fm=13,
            final_primary=14,
            final_secondary=15,
        )
        return FgResponseFrontierSolveResult(
            best_score=150,
            ft=6,
            ff=7,
            gem_counts={"Perfect Points": 1, "Combo Multiplier": 2, "Fever Multiplier": 3, "Element": 4},
            stats={**base_stats, "Fever Time": 6, "Fever Fill Rate": 7},
            surface=surface,
            frontier=frontier,
            inner=inner,
            seconds=0.0,
            forced_counts=(5, 0),
        )

    def _fake_prepare_batch(*, base_stats_list, calc_song, ref_arrays, selected_color, **_kwargs):
        calls.append((list(base_stats_list), selected_color, calc_song, ref_arrays))
        return {"base_stats_list": list(base_stats_list), "selected_color": selected_color}

    def _fake_score_batch(batch, **_kwargs):
        return [_result(base_stats, str(batch["selected_color"])) for base_stats in batch["base_stats_list"]]

    monkeypatch.setattr(adapter, "extract_fg_song_inputs", lambda _song: SimpleNamespace(total_notes=2))
    monkeypatch.setattr(adapter, "prepare_force_greats_response_frontier_scoring_batch", _fake_prepare_batch)
    monkeypatch.setattr(adapter, "score_stats_exact", lambda *_args, **_kwargs: 100)
    monkeypatch.setattr(adapter, "score_stats_exact", lambda *_args, **_kwargs: 100)
    monkeypatch.setattr(adapter, "evaluate_force_greats_exact", lambda *_args, **_kwargs: {"final_score": 150})

    out = adapter.process_force_greats_response_frontier_gpu(
        {},
        {"metadata": {}, "song_data": {}},
        {},
        "Rush",
        ga_candidates=[
            {
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {
                    "BaseStats": {
                        "Perfect Points": 0,
                        "Combo Multiplier": 0,
                        "Fever Multiplier": 0,
                        "Fever Time": 0,
                        "Fever Fill Rate": 0,
                        "Rush": 10,
                    },
                    "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
                    "FT": 0,
                    "FF": 0,
                    "Selected Element": "Rush",
                },
            }
        ],
        score_prepared_batch=_fake_score_batch,
    )

    assert len(calls) == 1
    assert len(calls[0][0]) == 1
    assert calls[0][1] == "Rush"
    assert len(out) == 1
    assert out[0]["fg_score"] == 150
    assert out[0]["base_score"] == 100
    assert out[0]["data"]["FT"] == 6
    assert out[0]["data"]["FF"] == 7
    assert out[0]["data"]["GemCounts"]["Element"] == 4
    assert out[0]["data"]["ForceGreats"]["mode"] == "response_frontier"
    assert out[0]["data"]["ForceGreats"]["config"] == {"NonFever1": 5, "NonFever2": 0}
    assert out[0]["gear"] == ["G1"]
    assert out[0]["minis"] == ["M1"]


def test_process_force_greats_batches_response_frontier_candidates(monkeypatch):
    from types import SimpleNamespace

    from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter as adapter
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    calls: list[int] = []

    def _fake_prepare_batch(*, base_stats_list, calc_song, ref_arrays, selected_color, **_kwargs):
        _ = (calc_song, ref_arrays, selected_color)
        calls.append(len(base_stats_list))
        return {"base_stats_list": list(base_stats_list)}

    def _fake_score_batch(batch, **_kwargs):
        out = []
        for idx, base_stats in enumerate(batch["base_stats_list"]):
            surface = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, idx, 0)
            frontier = FgResponseFrontierResult(
                first_frontier=(surface,),
                state_frontiers={},
                states_evaluated=1,
                actions=1,
                transitions_evaluated=1,
                generated_surfaces=1,
                retained_surfaces_total=1,
                max_state_frontier=1,
                non_fever_base=5,
                seconds=0.0,
            )
            inner = FgResponseInnerResult(
                best_score=200 + idx,
                surface_index=0,
                g_pp=0,
                g_cm=0,
                g_fm=0,
                g_ov=1,
                final_pp=0,
                final_cm=0,
                final_fm=0,
                final_primary=0,
                final_secondary=0,
            )
            out.append(
                FgResponseFrontierSolveResult(
                    best_score=200 + idx,
                    ft=0,
                    ff=0,
                    gem_counts={"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 1},
                    stats={**base_stats, "Rush": int(base_stats.get("Rush", 0) or 0) + 1},
                    surface=surface,
                    frontier=frontier,
                    inner=inner,
                    seconds=0.0,
                    forced_counts=(5, 0),
                )
            )
        return out

    monkeypatch.setattr(adapter, "extract_fg_song_inputs", lambda _song: SimpleNamespace(total_notes=2))
    monkeypatch.setattr(adapter, "prepare_force_greats_response_frontier_scoring_batch", _fake_prepare_batch)
    monkeypatch.setattr(adapter, "score_stats_exact", lambda *_args, **_kwargs: 100)
    monkeypatch.setattr(adapter, "score_stats_exact", lambda *_args, **_kwargs: 100)
    monkeypatch.setattr(
        adapter,
        "evaluate_force_greats_exact",
        lambda stats, *_args, **_kwargs: {"final_score": int(stats["Rush"]) + 189},
    )

    out = adapter.process_force_greats_response_frontier_gpu(
        {},
        {"metadata": {}, "song_data": {}},
        {},
        "Rush",
        ga_candidates=[
            {
                "BaseScore": 100,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"BaseStats": {"Perfect Points": 0, "Rush": 10}, "Selected Element": "Rush"},
            },
            {
                "BaseScore": 101,
                "Gear": ["G2"],
                "Minis": ["M2"],
                "Data": {"BaseStats": {"Perfect Points": 0, "Rush": 11}, "Selected Element": "Rush"},
            },
        ],
        score_prepared_batch=_fake_score_batch,
    )

    assert calls == [2]
    assert [row["fg_score"] for row in out] == [201, 200]
