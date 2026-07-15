import json
import queue
import threading

from tests.native_song_factory import make_native_song


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
    from gear_optimizer.data.loadout_equivalence import (
        get_gears_by_name_cached,
        get_minis_by_name_cached,
    )
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
        _representative_mini_names_from_any,
    )
    from gear_optimizer.pipeline import post_processor
    from gear_optimizer.solver import native_inflight_fg_payload as result_events
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    db_path = tmp_path / "post_processor_exact_authority.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    calc_song = {
        "metadata": {
            "Song Name": "pytest_post_processor_exact_authority",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0], "lanes": [0], "note_types": [1]},
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
    gear_names = list(get_gears_by_name_cached())[:6]
    mini_names = []
    minis_by_name = get_minis_by_name_cached()
    for name in minis_by_name:
        representative = _representative_mini_names_from_any([name])
        if len(representative) == 1 and representative[0] in minis_by_name:
            mini_names.append(name)
        if len(mini_names) == 3:
            break
    assert len(gear_names) == 6 and len(mini_names) == 3

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
        db_key="pytest_post_processor_exact_authority",
        fp="Data/Hard/pytest_post_processor_exact_authority.txt",
        effective_difficulty="Hard",
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        fg_debug=False,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        base_candidates=[
            {
                "Score": inflated_score,
                "BaseScore": inflated_score,
                "Gear": list(gear_names),
                "Minis": list(mini_names),
                "Data": {
                    "Stats": dict(stats),
                    "Selected Element": "Rush",
                },
            }
        ],
        best_data={
            "Score": inflated_score,
            "BaseScore": inflated_score,
            "Stats": dict(stats),
            "Selected Element": "Rush",
        },
        best_gear=list(gear_names),
        best_minis=list(mini_names),
        current_gear_list=[],
        current_mini_list=[],
        meta_primary_color="Rush",
        meta_secondary_color="Flow",
        prev_record=None,
        attempt_lifetime=0,
        prev_attempts_first=0,
        db_best_fg_score=0,
        fg_variants=[],
    )

    payload = result_events.build_deferred_post_payload(song)
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
