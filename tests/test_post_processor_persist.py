from tests.curves_support import synthetic_curves
from gear_optimizer.pipeline.post_processor_persist import (
    build_post_persist_context,
    build_post_persist_db_payload,
    build_post_persist_entries,
    build_post_persist_print_payload,
    build_post_persist_result_payload,
)
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact
from tests.songs_support import make_song


def _curves() -> dict:
    from gear_optimizer.rules import MAX_STAT

    rows = int(MAX_STAT) + 1
    return synthetic_curves({
        "Perfect Points": [1.0] * rows,
        "Combo Multiplier": [1.0] * rows,
        "Fever Multiplier": [1.0] * rows,
        "Fever Fill Rate": [1.0] * rows,
        "Fever Time": [1.0] * rows,
    })


def _prebuild_timeline_frontier(song, curves) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    build_or_load_timeline_frontier_payload(song, curves)


def test_deferred_post_finalizer_builds_replay_authoritative_entries():
    song = make_song([0.0])
    curves = _curves()
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 5,
    }
    _prebuild_timeline_frontier(song, curves)
    inflated_score = int(score_stats_exact(stats, song, curves)) + 12345
    item = {
        "_deferred_post": True,
        "song": "pytest_deferred_post_finalizer",
        "db_key": "pytest_deferred_post_finalizer",
        "difficulty": "Hard",
        "timed_song": song,
        "curves": curves,
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
        "db_best_fg_score": 0,
        "meta_primary_color": "Rush",
        "meta_secondary_color": "Flow",
    }

    context = build_post_persist_context(item)
    db_payload = build_post_persist_db_payload(context)
    persist_entries = build_post_persist_entries(item, db_payload=db_payload, context=context)
    result_payload = build_post_persist_result_payload(item, db_payload=db_payload, persist_entries=persist_entries)

    assert len(persist_entries) == 1
    persisted = persist_entries[0]
    persisted_stats = dict((persisted.get("details") or {}).get("Stats") or {})

    assert persisted["gear"] == ["G1"]
    assert persisted["minis"] == ["M1"]
    assert persisted["score"] != inflated_score
    assert persisted["score"] == int(score_stats_exact(persisted_stats, song, curves))
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

    item = {
        "song": "pytest_deferred_post_print",
        "best_data": {"Score": 100, "BaseScore": 100},
        "best_gear": ["G1"],
        "best_minis": ["M1"],
        "prev_record": {"score": 99},
        "curves": {"Perfect Points": [1.0]},
        "timed_song": make_song([0.0]),
        "db_best_fg_score": "123",
    }

    context = build_post_persist_context(item)
    payload = build_post_persist_print_payload(item, context=context, emit=emit)

    assert payload == {
        "song": "pytest_deferred_post_print",
        "best_data": {"Score": 100, "BaseScore": 100},
        "best_gear": ["G1"],
        "best_minis": ["M1"],
        "prev_record": {"score": 99},
        "db_best_fg_score": 123,
        "_emit": emit,
    }
