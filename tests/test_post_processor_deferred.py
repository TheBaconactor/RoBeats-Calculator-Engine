from gear_optimizer.pipeline.post_processor_deferred import (
    build_deferred_post_context,
    build_deferred_post_db_payload,
    build_deferred_post_persist_entries,
    build_deferred_post_print_payload,
    build_deferred_post_result_payload,
)
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact


def test_deferred_post_finalizer_builds_replay_authoritative_entries():
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0]},
    }
    ref_arrays = {
        "Perfect Points": [1.0] * 1001,
        "Combo Multiplier": [1.0] * 1001,
        "Fever Multiplier": [1.0] * 1001,
        "Fever Fill Rate": [1.0] * 1001,
        "Fever Time": [1.0] * 1001,
    }
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 5,
    }
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
        "best_gear": ["G1"],
        "best_minis": ["M1"],
        "ga_candidates": [],
        "loadout_entries": None,
        "fg_variants": [],
        "prev_record": None,
        "attempt_lifetime": 0,
        "prev_attempts_first": 0,
        "db_best_fg_score": 0,
        "meta_primary_color": "Rush",
        "meta_secondary_color": "Flow",
    }

    context = build_deferred_post_context(item)
    db_payload = build_deferred_post_db_payload(context)
    persist_entries = build_deferred_post_persist_entries(item, db_payload=db_payload, context=context)
    result_payload = build_deferred_post_result_payload(item, db_payload=db_payload, persist_entries=persist_entries)

    assert context.attempt_lifetime == 1
    assert context.attempts_first == 1
    assert len(persist_entries) == 1
    persisted = persist_entries[0]
    persisted_stats = dict((persisted.get("details") or {}).get("Stats") or {})

    assert persisted["gear"] == ["G1"]
    assert persisted["minis"] == ["M1"]
    assert persisted["score"] != inflated_score
    assert persisted["score"] == int(score_stats_exact(persisted_stats, calc_song, ref_arrays))
    assert result_payload == {
        "song": "pytest_deferred_post_finalizer",
        "db_key": "pytest_deferred_post_finalizer",
        "db_payload": db_payload,
        "persist_entries": persist_entries,
        "log": "",
    }


def test_deferred_post_print_payload_preserves_pending_final_shape():
    def emit(_msg):
        return None

    calc_song = {"metadata": {}, "song_data": {}}
    ref_arrays = {"Perfect Points": [1.0]}
    item = {
        "song": "pytest_deferred_post_print",
        "cfg_dict": {"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
        "best_data": {"Score": 100, "BaseScore": 100},
        "best_gear": ["G1"],
        "best_minis": ["M1"],
        "prev_record": {"score": 99},
        "current_gear": ["G0"],
        "current_minis": ["M0"],
        "enable_gear": 1,
        "enable_mini": "",
        "fg_debug": True,
        "ref_arrays": ref_arrays,
        "calc_song": calc_song,
        "db_best_fg_score": "123",
    }

    context = build_deferred_post_context(item)
    payload = build_deferred_post_print_payload(item, context=context, emit=emit)

    assert payload == {
        "song": "pytest_deferred_post_print",
        "best_data": {"Score": 100, "BaseScore": 100},
        "best_gear": ["G1"],
        "best_minis": ["M1"],
        "prev_record": {"score": 99},
        "current_gear": ["G0"],
        "current_minis": ["M0"],
        "enable_gear": True,
        "enable_mini": False,
        "fg_debug": True,
        "ref_arrays": ref_arrays,
        "calc_song": calc_song,
        "cfg": context.cfg,
        "db_best_fg_score": 123,
        "_emit": emit,
    }
