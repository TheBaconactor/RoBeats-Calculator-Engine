from gear_optimizer.data.database import get_loadout_hash
from gear_optimizer.helpers.song_helpers.persistence_canon import build_persistence_entries
from gear_optimizer.helpers.song_helpers.persistence_entry_selection import build_retained_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence_payload import make_build_details_fn
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


def _stats(pp: int) -> dict:
    return {
        "Perfect Points": int(pp),
        "Combo Multiplier": 1,
        "Fever Multiplier": 1,
        "Fever Fill Rate": 1,
        "Fever Time": 1,
        "Rush": 1,
        "Flow": 1,
    }


def test_retained_entries_rebuild_details_when_stats_missing_but_details_nonempty():
    loadout_entries = {
        "h1": {
            "score": 123,
            "details": {"FT": 2, "FF": 3, "GemCounts": {"Perfect Points": 1}},
            "eval_data": {
                "FT": 7,
                "FF": 8,
                "GemCounts": {"Perfect Points": 9},
                "Stats": _stats(99),
                "Selected Element": "Rush",
            },
            "gear": ["G1"],
            "minis": ["M1"],
        }
    }

    def _build_details(data: dict) -> dict:
        return {
            "FT": data.get("FT", 0),
            "FF": data.get("FF", 0),
            "GemCounts": data.get("GemCounts", {}),
            "Stats": dict(data.get("Stats") or {}),
            "SelectedElement": data.get("Selected Element", ""),
            "PrimaryColor": "Rush",
            "SecondaryColor": "Flow",
            "Difficulty": "Hard",
        }

    retained = build_retained_loadout_entries(loadout_entries, _build_details)
    assert len(retained) == 1
    details = retained[0]["details"]
    assert details.get("Stats") == _stats(99)
    assert int(details.get("FT", 0)) == 7
    assert int(details.get("FF", 0)) == 8


def test_retained_entries_keep_existing_details_when_stats_present():
    existing_details = {
        "FT": 2,
        "FF": 3,
        "GemCounts": {"Perfect Points": 1},
        "Stats": _stats(42),
    }
    loadout_entries = {
        "h1": {
            "score": 123,
            "details": dict(existing_details),
            "eval_data": {
                "FT": 7,
                "FF": 8,
                "GemCounts": {"Perfect Points": 9},
                "Stats": _stats(99),
                "Selected Element": "Rush",
            },
            "gear": ["G1"],
            "minis": ["M1"],
        }
    }

    def _build_details(_data: dict) -> dict:
        return {
            "FT": 999,
            "FF": 999,
            "GemCounts": {"Perfect Points": 999},
            "Stats": _stats(999),
        }

    retained = build_retained_loadout_entries(loadout_entries, _build_details)
    assert len(retained) == 1
    assert retained[0]["details"] == existing_details


def test_missing_stats_details_rebuild_before_canonical_replay_scoring():
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
    eval_stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 10,
        "Flow": 5,
    }
    _prebuild_timeline_frontier(calc_song, ref_arrays)
    exact_score = int(score_stats_exact(eval_stats, calc_song, ref_arrays))
    inflated_score = exact_score + 4321

    gear = ["G1"]
    minis = ["M1"]
    loadout_hash = get_loadout_hash(gear, minis)
    build_details = make_build_details_fn("Rush", "Flow", "Hard")

    loadout_entries = {
        loadout_hash: {
            "score": inflated_score,
            "fg_score": 0,
            "gear": list(gear),
            "minis": list(minis),
            # Non-empty details but missing Stats reproduces the retained-entry hole.
            "details": {
                "FT": 0,
                "FF": 0,
                "GemCounts": {},
                "SelectedElement": "Rush",
                "PrimaryColor": "Rush",
                "SecondaryColor": "Flow",
            },
            "eval_data": {
                "FT": 0,
                "FF": 0,
                "GemCounts": {},
                "Stats": dict(eval_stats),
                "Selected Element": "Rush",
            },
        }
    }

    persist_entries = build_persistence_entries(
        {
            "score": 1,
            "fg_score": 0,
            "gear": ["X"],
            "minis": ["Y"],
            "details": {"Stats": _stats(1), "SelectedElement": "Rush"},
            "force": None,
        },
        [],
        loadout_entries,
        build_details,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5"}},
    )

    retained = next(e for e in persist_entries if str(e.get("loadout_hash") or "") == str(loadout_hash))
    retained_stats = dict((retained.get("details") or {}).get("Stats") or {})
    assert retained_stats
    assert int(retained["score"]) == int(score_stats_exact(retained_stats, calc_song, ref_arrays))
    assert int(retained["score"]) != int(inflated_score)


def test_build_persistence_entries_keeps_all_improving_fg_variants_from_payload():
    from gear_optimizer.helpers.song_helpers.persistence_payload import build_db_payload

    build_details = make_build_details_fn("Rush", "Flow", "Hard")
    best_data = {
        "BaseScore": 1000,
        "Score": 1000,
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "Stats": _stats(10),
        "Selected Element": "Rush",
    }
    best_gear = ["G_top"]
    best_minis = ["M_top"]
    fg_variants = [
        {
            "gear": ["G_top"],
            "minis": ["M_top"],
            "base_score": 1000,
            "fg_score": 1100,
            "data": {
                "BaseScore": 1000,
                "Stats": _stats(10),
                "ForceGreats": {"config": {"NonFever1": 1}},
            },
        },
        {
            "gear": ["G_second"],
            "minis": ["M_second"],
            "base_score": 900,
            "fg_score": 1200,
            "data": {
                "BaseScore": 900,
                "Stats": _stats(9),
                "ForceGreats": {"config": {"NonFever1": 2}},
            },
        },
        {
            "gear": ["G_third"],
            "minis": ["M_third"],
            "base_score": 850,
            "fg_score": 950,
            "data": {
                "BaseScore": 850,
                "Stats": _stats(8),
                "ForceGreats": {"config": {"NonFever1": 3}},
            },
        },
    ]

    payload = build_db_payload(
        best_data,
        best_gear,
        best_minis,
        prev_record=None,
        attempt_lifetime=1,
        attempts_first=1,
        fg_variants=fg_variants,
        build_details_fn=build_details,
        db_best_fg_score=0,
    )

    from gear_optimizer.helpers.song_helpers.persistence_canon import assemble_without_replay

    persist_entries = assemble_without_replay(
        db_payload=payload,
        ga_candidates=[],
        loadout_entries=None,
        build_details_fn=build_details,
    )

    fg_rows = [entry for entry in persist_entries if int(entry.get("fg_score", 0) or 0) > int(entry.get("score", 0) or 0)]
    assert {tuple(row.get("gear") or []) for row in fg_rows} == {
        ("G_top",),
        ("G_second",),
        ("G_third",),
    }
