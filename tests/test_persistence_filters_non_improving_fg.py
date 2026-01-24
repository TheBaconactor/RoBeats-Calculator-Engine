from __future__ import annotations

import configparser


def test_build_db_payload_drops_fg_variants_worse_than_base():
    from gear_optimizer.helpers.song_helpers.persistence import build_db_payload, make_build_details_fn

    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")

    build_details = make_build_details_fn("Chill", "Flow", "Hard")

    best_data = {"BaseScore": 100, "Score": 100, "FT": 0, "FF": 0, "GemCounts": {}, "Stats": {}, "Selected Element": "Chill"}
    best_gear = [{"Name": "A"}] * 6
    best_minis = [{"Name": "M"}] * 3

    # FG variant has a valid config but is worse than base => should be ignored for persistence.
    fg_variants = [
        {
            "gear": best_gear,
            "minis": best_minis,
            "score": 100,
            "base_score": 100,
            "fg_score": 90,
            "data": {"Score": 90, "ForceGreats": {"config": {"NonFever1": 2}}},
        }
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

    # No persisted FG since it didn't improve the loadout's score.
    assert payload.get("fg_score", 0) == 0
    assert payload.get("force") is None

