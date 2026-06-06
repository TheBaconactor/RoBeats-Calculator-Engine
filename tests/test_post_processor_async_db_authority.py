import json
import queue
import threading

from gear_optimizer.solver.native_inflight_config import make_native_song


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


def test_post_processor_deferred_native_save_persists_exact_replay_authority(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.pipeline import post_processor
    from gear_optimizer.solver import native_inflight_fg_payload as result_events
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    db_path = tmp_path / "post_processor_exact_authority.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

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
    monkeypatch.setattr(post_processor, "print_results", lambda *_args, **_kwargs: None)

    song = make_native_song(
        song_name="pytest_post_processor_exact_authority",
        task_key="pytest_post_processor_exact_authority",
        ga_seed=789,
        db_key="pytest_post_processor_exact_authority",
        fp="Data/Hard/pytest_post_processor_exact_authority.txt",
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

    payload = result_events.build_deferred_post_payload(song, persist_pending_fg_job=False)
    result_queue: queue.Queue = queue.Queue()
    worker = threading.Thread(
        target=post_processor.run_post_processor,
        args=(result_queue, 1),
        daemon=True,
    )

    worker.start()
    result_queue.put(payload)
    result_queue.put(None)
    worker.join(timeout=15.0)

    assert not worker.is_alive()

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, details_json "
            "FROM team_buff_loadouts "
            "WHERE song_name = ? AND team_buff = 'T5'",
            ("pytest_post_processor_exact_authority",),
        ).fetchone()

    assert row is not None
    stored_details = _unpack_stats_after_load(json.loads(str(row["details_json"] or "{}"))) or {}
    stored_stats = dict(stored_details.get("Stats") or {})

    assert stored_stats
    assert stored_stats != stats
    assert int(row["score"]) != inflated_score
    assert int(row["score"]) == int(score_stats_exact(stored_stats, calc_song, ref_arrays))


def test_post_processor_fg_update_path_canonicalizes_before_save(tmp_path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db
    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.pipeline import post_processor

    db_path = tmp_path / "post_processor_fg_update_authority.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    ref_arrays = _get_team_buff_ref_arrays_cached()
    assert ref_arrays

    force_payload = {
        "Score": 32521173,
        "FT": 1,
        "FF": 15,
        "GemCounts": {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 13,
            "Element": 61,
        },
        "Selected Element": "Rush",
        "BaseScore": 32518595,
        "BaseStats": {
            "Perfect Points": 40,
            "Combo Multiplier": 50,
            "Fever Multiplier": 37,
            "Fever Time": 28,
            "Fever Fill Rate": 19,
            "Beat": 0,
            "Vibe": 44,
            "Rush": 321,
            "Flow": 29,
            "Chill": 33,
        },
        "ForceGreats": {"config": {"NonFever1": 5, "NonFever2": 0}, "final_score": 32521173},
        "forced_counts": [5, 0],
    }

    monkeypatch.setattr(post_processor, "print_results", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached",
        lambda: ref_arrays,
    )

    result_queue: queue.Queue = queue.Queue()
    worker = threading.Thread(
        target=post_processor.run_post_processor,
        args=(result_queue, 1),
        daemon=True,
    )
    worker.start()
    result_queue.put(
        {
            "_fg_update": True,
            "song": "pytest_post_processor_fg_update_authority",
            "db_key": "pytest_post_processor_fg_update_authority",
            "file_path": r"Data\Hard\00 (Hard) by garlagan.txt",
            "cfg_dict": {"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
            "ref_arrays": ref_arrays,
            "persist_entries": [
                {
                    "score": 32518595,
                    "fg_score": 32521173,
                    "fg_base_score": 32518595,
                    "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                    "minis": ["M1", "M2", "M3"],
                    "details": {
                        "Stats": {
                            "Perfect Points": 40,
                            "Combo Multiplier": 50,
                            "Fever Multiplier": 76,
                            "Fever Time": 31,
                            "Fever Fill Rate": 64,
                            "Beat": 3,
                            "Vibe": 89,
                            "Rush": 726,
                            "Flow": 29,
                            "Chill": 33,
                        },
                        "SelectedElement": "Rush",
                        "PrimaryColor": "Rush",
                        "SecondaryColor": "Rush",
                    },
                    "force": force_payload,
                    "_deferred_fg_update": True,
                }
            ],
        }
    )
    result_queue.put(None)
    worker.join(timeout=15.0)

    assert not worker.is_alive()

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json "
            "FROM team_buff_fg_loadouts "
            "WHERE song_name = ? AND team_buff = 'T5'",
            ("pytest_post_processor_fg_update_authority",),
        ).fetchone()

    assert row is not None
    stored_details = json.loads(str(row["details_json"] or "{}"))
    stored_force = json.loads(str(row["force_details_json"] or "{}"))
    assert int(row["score"]) == 32518595
    assert int(row["fg_score"]) == 32521173
    assert int(stored_details["BaseScore"]) == 32518595
    assert int(stored_force["BaseScore"]) == 32518595
    assert int(stored_force["Score"]) == 32521173
