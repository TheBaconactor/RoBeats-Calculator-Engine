from __future__ import annotations

from gear_optimizer.helpers.song_helpers.persistence_payload import build_db_payload
from gear_optimizer.helpers.song_helpers.results_printer import print_results
from gear_optimizer.pipeline.song_processor import _native_fg_variant_from_record


def _native_fg_record() -> dict:
    return {
        "base_score": 34253930,
        "fg_score": 34259925,
        "fg_base_score": 34253930,
        "genome": [
            {"Name": "FG Hat"},
            {"Name": "FG Neck"},
            {"Name": "FG Face"},
            {"Name": "FG Shirt"},
            {"Name": "FG Back"},
            {"Name": "FG Pants"},
            {"Name": "FG Mini 1"},
            {"Name": "FG Mini 2"},
            {"Name": "FG Mini 3"},
        ],
        "data": {
            "BaseScore": 34253930,
            "Score": 34259925,
            "FGScore": 34259925,
            "FT": 0,
            "FF": 0,
            "GemCounts": {},
            "Stats": {},
            "BaseStats": {},
            "ForceGreats": {"config": {"FT": 1}},
            "force": {
                "ForceGreats": {"config": {"FT": 1}},
                "Stats": {},
                "BaseStats": {},
            },
        },
    }


def test_native_fg_variant_preserves_reportable_fg_score() -> None:
    variant = _native_fg_variant_from_record(_native_fg_record())
    assert variant is not None
    assert int(variant["score"]) == 34253930
    assert int(variant["fg_score"]) == 34259925
    assert int(variant["data"]["FGScore"]) == 34259925


def test_native_fg_variant_reaches_report_and_db_payload(capsys) -> None:
    variant = _native_fg_variant_from_record(_native_fg_record())
    assert variant is not None

    best_data = {
        "BaseScore": 34253930,
        "Score": 34253930,
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "Stats": {},
        "BaseStats": {},
        "ForceGreats": {"config": {"FT": 1}},
    }
    best_gear = [{"Name": "Base Hat"}]
    best_minis = [{"Name": "Base Mini"}]

    payload = build_db_payload(
        best_data,
        best_gear,
        best_minis,
        prev_record=None,
        attempt_lifetime=1,
        attempts_first=1,
        fg_variants=[variant],
        build_details_fn=lambda data: {
            "FT": data.get("FT", 0),
            "FF": data.get("FF", 0),
            "GemCounts": data.get("GemCounts", {}),
            "Stats": data.get("Stats", {}),
            "ForceGreats": data.get("ForceGreats", {}),
        },
        db_best_fg_score=0,
    )
    assert int(payload["run_best_fg_score"]) == 34259925
    assert int(payload["best_fg"]["score"]) == 34259925

    print_results(
        "00 (Hard) by garlagan",
        best_data,
        best_gear,
        best_minis,
        best_gear,
        best_minis,
        True,
        True,
        [variant],
        lambda _msg: None,
        fg_debug=False,
        ref_arrays=None,
        calc_song=None,
        cfg=None,
        db_best_fg_score=0,
        prev_record=None,
    )
    out = capsys.readouterr().out
    assert "Best FG Score Found: 34259925" in out
