from concurrent.futures import Future
from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_config import make_native_song
from gear_optimizer.solver.native_inflight_fg_payload import build_fg_update_payload
from gear_optimizer.solver.native_inflight_orchestrator import (
    build_native_song_error_payload,
    build_native_task_error_payload,
)


def _ref_arrays() -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS

    rows = int(TOTAL_ROWS) + 1
    return {
        "Perfect Points": [1.0] * rows,
        "Combo Multiplier": [1.0] * rows,
        "Fever Multiplier": [1.0] * rows,
        "Fever Fill Rate": [1.0] * rows,
        "Fever Time": [1.0] * rows,
    }


def _prebuild_timeline_frontier(calc_song: dict, ref_arrays: dict) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    apply_timing_envelope(calc_song)
    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)


def test_native_song_error_payload_suppresses_bundle_progress():
    song = make_native_song(song_name="Bundle Song", task_key="bundle-key")
    song.runtime.bundle.bundle_parent_task = ("parent",)

    payload = build_native_song_error_payload(
        song,
        exc=RuntimeError("boom"),
        trace="TRACE",
    )

    assert payload["_error"] == "boom"
    assert payload["_error_type"] == "RuntimeError"
    assert payload["song"] == "Bundle Song"
    assert payload["_queue_key"] == "bundle-key"
    assert payload["_queue_label"] == "bundle-key"
    assert payload["_suppress_progress"] is True


def test_native_song_error_payload_can_leave_bundle_progress_unsuppressed():
    song = make_native_song(song_name="Bundle Song", task_key="bundle-key")
    song.runtime.bundle.bundle_parent_task = ("parent",)

    payload = build_native_song_error_payload(
        song,
        exc=RuntimeError("boom"),
        trace="TRACE",
        suppress_for_bundle=False,
    )

    assert "_suppress_progress" not in payload


def test_native_task_error_payload_defaults_queue_label_and_can_suppress_progress():
    payload = build_native_task_error_payload(
        song_name="Task Song",
        queue_key="task-key",
        exc=ValueError("bad task"),
        trace="TRACE",
        suppress_progress=True,
    )

    assert payload["song"] == "Task Song"
    assert payload["_queue_key"] == "task-key"
    assert payload["_queue_label"] == "task-key"
    assert payload["_error"] == "bad task"
    assert payload["_error_type"] == "ValueError"
    assert payload["_suppress_progress"] is True


def test_fg_update_payload_uses_shared_result_event_shape():
    cfg_dict = {"IterationEngine": {}}
    entries = [{"score": 101, "fg_score": 111}]
    song = make_native_song(
        song_name="FG Song",
        task_key="fg-song",
        db_key="fg-db",
        fp="Data/Hard/fg_song.txt",
        cfg_dict=cfg_dict,
    )

    payload = build_fg_update_payload(song, persist_entries=entries)

    assert payload == {
        "_fg_update": True,
        "song": "FG Song",
        "db_key": "fg-db",
        "persist_entries": entries,
        "file_path": "Data/Hard/fg_song.txt",
        "cfg_dict": cfg_dict,
    }
    assert payload["persist_entries"] is not entries


def test_native_inflight_deferred_post_payload_keeps_replay_context_when_fg_debug_disabled(monkeypatch):
    from gear_optimizer.solver import native_inflight_fg_payload as result_events

    calc_song = {
        "metadata": {"Primary Color": "Rush", "Secondary Color": "Flow", "Long Notes": 0, "Last Note Time": 0.0},
        "song_data": {"timestamps": [0.0], "note_types": [1]},
    }
    ref_arrays = _ref_arrays()
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    ga_candidates = [
        {
            "Score": 111,
            "BaseScore": 111,
            "Gear": ["G1"],
            "Minis": ["M1"],
            "Data": {"Stats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            "_fg_priority": 7,
            "loadout_hash": "hash-1",
        }
    ]

    monkeypatch.setattr(
        result_events,
        "materialize_candidate_names",
        lambda candidate, *, registry=None, mutate=False: (
            list(candidate.get("Gear") or []),
            list(candidate.get("Minis") or []),
        ),
    )

    song = make_native_song(
        song_name="pytest_native_deferred_post",
        task_key="pytest_native_deferred_post",
        ga_seed=123,
        db_key="pytest_native_deferred_post",
        fp="Data/Hard/pytest_native_deferred_post.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        fg_debug=False,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        ga_candidates=ga_candidates,
        best_data={"Score": 111, "BaseScore": 111, "Stats": {"Perfect Points": 1}},
        best_gear=["G1"],
        best_minis=["M1"],
        current_gear_list=["CurrentGear"],
        current_mini_list=["CurrentMini"],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record={"score": 100},
        attempt_lifetime=9,
        prev_attempts_first=2,
        db_best_fg_score=105,
    )

    payload = result_events.build_deferred_post_payload(song)

    assert payload["_deferred_post"] is True
    assert payload["_pending_fg_job"] is True
    assert payload["fg_debug"] is False
    assert payload["calc_song"] is calc_song
    assert payload["ref_arrays"] is ref_arrays
    assert payload["best_data"]["BaseScore"] == 111
    assert len(payload["ga_candidates"]) == 1
    candidate = payload["ga_candidates"][0]
    assert candidate["Gear"] == ["G1"]
    assert candidate["Minis"] == ["M1"]
    assert candidate["_fg_priority"] == 7
    assert candidate["loadout_hash"] == "hash-1"
    assert candidate["Data"]["Stats"] == {"Perfect Points": 1}
    assert candidate["Data"]["Selected Element"] == "Rush"
    assert candidate["Data"]["RawGASearchScore"] == 111
    assert candidate["Score"] == candidate["BaseScore"] == candidate["Data"]["BaseScore"]
    assert candidate["Data"]["Score"] == candidate["Data"]["BaseScore"]


def test_deferred_post_reuses_prepared_ga_candidate_surface(monkeypatch):
    from gear_optimizer.solver import native_inflight_fg_payload as result_events
    from gear_optimizer.solver import native_inflight_pipeline as stages

    calc_song = {
        "metadata": {"Primary Color": "Rush", "Secondary Color": "Flow", "Long Notes": 0, "Last Note Time": 0.0},
        "song_data": {"timestamps": [0.0]},
    }
    ref_arrays = _ref_arrays()
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    song = make_native_song(
        song_name="pytest_native_deferred_post_reuse",
        task_key="pytest_native_deferred_post_reuse",
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        ga_candidates=[
            {
                "Score": 200,
                "BaseScore": 200,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"Stats": {"Perfect Points": 2}, "Selected Element": "Rush"},
                "loadout_hash": "hash-1",
            }
        ],
        best_data={"Score": 200, "BaseScore": 200},
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        cfg_data={"selected_color": "Rush"},
        fixed_stats={},
    )

    stages.prepare_ga_candidate_surface_for_fg(song, fg_candidate_limit=51)
    monkeypatch.setattr(
        stages,
        "select_top_base_ga_candidates",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("selected twice")),
    )

    payload = result_events.build_deferred_post_payload(song)

    candidate = payload["ga_candidates"][0]
    assert candidate["Data"]["RawGASearchScore"] == 200
    assert candidate["Score"] == candidate["BaseScore"] == candidate["Data"]["BaseScore"]
    assert candidate["Data"]["Stats"]["Perfect Points"] == 2


def test_native_inflight_deferred_post_payload_uses_inline_fg_as_authority(monkeypatch):
    from gear_optimizer.solver import native_inflight_fg_payload as result_events

    monkeypatch.setattr(
        result_events,
        "materialize_candidate_names",
        lambda candidate, *, registry=None, mutate=False: (
            list(candidate.get("Gear") or []),
            list(candidate.get("Minis") or []),
        ),
    )

    inline_calc_song = {
        "metadata": {"Primary Color": "Rush", "Secondary Color": "Flow", "Long Notes": 0, "Last Note Time": 0.0},
        "song_data": {"timestamps": [0.0]},
    }
    inline_ref_arrays = _ref_arrays()
    _prebuild_timeline_frontier(inline_calc_song, inline_ref_arrays)
    song = make_native_song(
        song_name="pytest_native_deferred_post_inline_fg",
        task_key="pytest_native_deferred_post_inline_fg",
        ga_seed=321,
        db_key="pytest_native_deferred_post_inline_fg",
        fp="Data/Hard/pytest_native_deferred_post_inline_fg.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        fg_debug=False,
        calc_song=inline_calc_song,
        ref_arrays=inline_ref_arrays,
        ga_candidates=[
            {
                "Score": 111,
                "BaseScore": 111,
                "Gear": ["G1"],
                "Minis": ["M1"],
                "Data": {"BaseStats": {"Perfect Points": 1}, "Selected Element": "Rush"},
            }
        ],
        best_data={"Score": 111, "BaseScore": 111, "Stats": {"Perfect Points": 1}},
        best_gear=["G1"],
        best_minis=["M1"],
        fg_variants=[
            {
                "score": 111,
                "base_score": 111,
                "fg_score": 130,
                "gear": ["G1"],
                "minis": ["M1"],
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record={"score": 100},
        attempt_lifetime=3,
        prev_attempts_first=2,
        db_best_fg_score=105,
    )

    payload = result_events.build_deferred_post_payload(song)

    assert payload["_pending_fg_job"] is False
    assert int(payload["fg_variants"][0]["fg_score"]) == 130


def test_native_inflight_fg_worker_records_progress_info(tmp_path, monkeypatch):
    # Fused GA->FG handoff (Slice 3): run_fg_job_sync materializes from the owner FG
    # score map (no client SCORE submission). Records the FG progress info as before.
    import numpy as np

    from gear_optimizer.solver import native_inflight_pipeline as fg_pipeline
    from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgFusedOwnerScoreRow

    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0], "fg_timestamps": [0.0]},
    }
    ref_arrays = _ref_arrays()
    base_components = (5, 6, 7, 8, 9, 10, 11)
    planner_key = ("ck0",)
    base_stats = {"Perfect Points": 1}
    owner_map = {
        base_components: FgFusedOwnerScoreRow(
            ft=1,
            ff=2,
            ft_stat=3,
            ff_stat=6,
            inner_row=(130, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            surface=(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )
    }
    song = make_native_song(
        song_name="pytest_native_inline_fg_runner",
        task_key="pytest_native_inline_fg_runner",
        db_key="pytest_native_inline_fg_runner",
        best_data={"BaseScore": 111},
        fg_variants=None,
        db_best_score=100,
        db_best_fg_score=100,
        db_baseline_valid=True,
        fg_response_frontier_plan=SimpleNamespace(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            pending_jobs=(({"loadout_hash": "ck0"}, {}, "Rush", base_stats, 111, planner_key),),
            prepared_batches=[
                SimpleNamespace(
                    batch=SimpleNamespace(
                        base_components=np.asarray([base_components], dtype=np.int32),
                        selected_color="Rush",
                        calc_song=calc_song,
                        ref_arrays=ref_arrays,
                        scoring_bundle=object(),
                        started=0.0,
                    ),
                    rows=((planner_key, base_stats),),
                )
            ],
        ),
    )
    song.runtime.fg.fg_owner_score_map = owner_map

    monkeypatch.setattr(
        FgResultReducer,
        "materialize",
        staticmethod(
            lambda _plan, prepared_results, **kwargs: [
                {
                    "score": 111,
                    "base_score": 111,
                    "fg_score": int(
                        (
                            prepared_results[0][0]
                            if prepared_results
                            else next(iter(kwargs["result_cache_override"].values()))
                        ).best_score
                    ),
                    "gear": ["G1"],
                    "minis": ["M1"],
                    "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
                }
            ]
        ),
    )
    monkeypatch.setattr(
        response_frontier,
        "build_fused_owner_solve_result_from_score_row",
        lambda *, score_row, **_kwargs: SimpleNamespace(best_score=int(score_row.inner_row[0])),
    )

    fg_pipeline.run_fg_job_sync(song, gpu_client=None)

    assert int(song.runtime.fg.fg_variants[0]["fg_score"]) == 130
    assert song.runtime.db.record_info["song"] == "pytest_native_inline_fg_runner"
    assert song.runtime.db.record_info["record_update"] is True


def test_native_inflight_deferred_post_payload_keeps_persistence_on_exact_replay_authority(monkeypatch):
    from gear_optimizer.helpers.song_helpers.persistence_canon import build_persistence_entries
    from gear_optimizer.solver import native_inflight_fg_payload as result_events
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0]},
    }
    ref_arrays = _ref_arrays()
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 5,
    }
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    raw_exact_score = int(score_stats_exact(stats, calc_song, ref_arrays))
    inflated_score = raw_exact_score + 12345

    monkeypatch.setattr(
        result_events,
        "materialize_candidate_names",
        lambda candidate, *, registry=None, mutate=False: (
            list(candidate.get("Gear") or []),
            list(candidate.get("Minis") or []),
        ),
    )

    song = make_native_song(
        song_name="pytest_native_deferred_post_exact_authority",
        task_key="pytest_native_deferred_post_exact_authority",
        ga_seed=456,
        db_key="pytest_native_deferred_post_exact_authority",
        fp="Data/Hard/pytest_native_deferred_post_exact_authority.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        fg_debug=False,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        ga_candidates=[],
        best_data={
            "Score": inflated_score,
            "BaseScore": inflated_score,
            "Stats": dict(stats),
            "Selected Element": "Rush",
        },
        best_gear=["G1"],
        best_minis=["M1"],
        current_gear_list=[],
        current_mini_list=[],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record=None,
        attempt_lifetime=0,
        prev_attempts_first=0,
        db_best_fg_score=0,
    )

    payload = result_events.build_deferred_post_payload(song)
    persist_entries = build_persistence_entries(
        {
            "score": int(payload["best_data"]["Score"]),
            "fg_score": 0,
            "gear": list(payload["best_gear"]),
            "minis": list(payload["best_minis"]),
            "details": {"Stats": dict(stats), "Selected Element": "Rush"},
            "force": None,
        },
        payload["ga_candidates"],
        None,
        lambda data: dict(data),
        calc_song=payload["calc_song"],
        ref_arrays=payload["ref_arrays"],
        cfg_dict=payload["cfg_dict"],
    )

    assert len(persist_entries) == 1
    persisted = persist_entries[0]
    persisted_stats = dict((persisted.get("details") or {}).get("Stats") or {})

    assert persisted["gear"] == ["G1"]
    assert persisted["minis"] == ["M1"]
    assert persisted["fg_score"] == 0
    assert persisted["force"] is None
    assert persisted["score"] != inflated_score
    assert persisted["score"] == int(score_stats_exact(persisted_stats, payload["calc_song"], payload["ref_arrays"]))
