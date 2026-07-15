from gear_optimizer.pipeline.post_processor_persist import (
    build_post_persist_context,
    build_post_persist_db_payload,
    build_post_persist_entries,
    build_post_persist_result_payload,
)
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact


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


def test_deferred_post_finalizer_builds_replay_authoritative_entries():
    gear_names = [f"G{index}" for index in range(1, 7)]
    mini_names = [f"M{index}" for index in range(1, 4)]
    calc_song = {
        "metadata": {
            "Song Name": "pytest_deferred_post_finalizer",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
            "Total Notes": 1,
        },
        "song_data": {"timestamps": [0.0], "note_types": [1], "lanes": [0]},
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
    inflated_score = int(score_stats_exact(stats, calc_song, ref_arrays)) + 12345
    item = {
        "_deferred_post": True,
        "song": "pytest_deferred_post_finalizer",
        "db_key": "pytest_deferred_post_finalizer",
        "difficulty": "Hard",
        "cfg_dict": {"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        "calc_song": calc_song,
        "ref_arrays": ref_arrays,
        "best_data": {
            "Score": inflated_score,
            "BaseScore": inflated_score,
            "Stats": dict(stats),
            "Selected Element": "Rush",
        },
        "best_gear": gear_names,
        "best_minis": mini_names,
        "gears_by_name": {name: {"Name": name, "Perfect Points": 0} for name in gear_names},
        "minis_by_name": {name: {"Name": name, "Perfect Points": 0} for name in mini_names},
        "base_candidates": [],
        "loadout_entries": None,
        "fg_variants": [],
        "prev_record": None,
        "attempt_lifetime": 0,
        "prev_attempts_first": 0,
        "db_best_fg_score": 0,
        "meta_primary_color": "Rush",
        "meta_secondary_color": "Flow",
    }

    context = build_post_persist_context(item)
    db_payload = build_post_persist_db_payload(context)
    persist_entries = build_post_persist_entries(item, db_payload=db_payload, context=context)
    result_payload = build_post_persist_result_payload(item, db_payload=db_payload, persist_entries=persist_entries)

    assert context.attempt_lifetime == 1
    assert context.attempts_first == 1
    assert len(persist_entries) == 1
    persisted = persist_entries[0]
    persisted_stats = dict((persisted.get("details") or {}).get("Stats") or {})

    assert persisted["gear"] == gear_names
    assert persisted["minis"] == mini_names
    assert persisted["score"] != inflated_score
    assert persisted["score"] == int(score_stats_exact(persisted_stats, calc_song, ref_arrays))
    assert result_payload == {
        "song": "pytest_deferred_post_finalizer",
        "db_key": "pytest_deferred_post_finalizer",
        "db_payload": db_payload,
        "persist_entries": persist_entries,
        "log": "",
    }
