import pytest


_FG_SURFACE = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def _noop_status_emit(_msg: str) -> None:
    return


def test_results_printer_prints_db_best_fg_score_when_no_variants(capsys):
    """Regression test: deferred FG jobs can leave fg_variants empty; output should not show FG=0 if DB best is known."""
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    print_results(
        "Test Song",
        best_data={"Score": 123, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"},
        best_gear=[],
        best_minis=[],
        fg_variants=[],
        status_emit_fn=_noop_status_emit,
        db_best_fg_score=456,
    )

    out = capsys.readouterr().out
    assert "Best FG Score Found: 456" in out


def test_results_printer_includes_db_cached_fg_variants_for_loadout_printing(capsys):
    """
    Regression test:
    When the best FG variant comes from a DB-cached entry (i.e. `_is_ga` is False),
    the console output should still print the ForceGreats loadout.
    """
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    best_data = {"Score": 44590483, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"}

    db_cached_fg_variant = {
        "data": {
            "Score": 44612857,
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Selected Element": "Rush",
            "response_surface": _FG_SURFACE,
            "ForceGreats": {"final_score": 44612857},
        },
        "gear": ["G1"],
        "minis": ["M1"],
        "score": 44590483,
        "fg_score": 44612857,
        "_is_ga": False,
    }

    print_results(
        "Test Song",
        best_data=best_data,
        best_gear=["G1"],
        best_minis=["M1"],
        fg_variants=[db_cached_fg_variant],
        status_emit_fn=_noop_status_emit,
        db_best_fg_score=44612857,
        prev_record={"score": 44590483, "gear": ["G1"], "minis": ["M1"], "details": {"Score": 44590483}},
    )

    out = capsys.readouterr().out
    assert "Best FG Score Found: 44612857" in out
    assert "[Best Gear Loadout (ForceGreats)]" in out
    assert "FG Config:" not in out


def test_results_printer_best_base_score_floors_to_db_record_when_higher(capsys):
    """
    Regression test:
    Console output should reflect the persisted winner. When a higher DB base record
    is provided, the printer must show the DB score/loadout (not the current-run one).
    """
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    found_song_name = "Test Song"
    best_data = {"Score": 100, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"}
    prev_record = {
        "score": 200,
        "fg_score": 0,
        "gear": [{"Name": "DB Gear", "type": "Hat"}],
        "minis": [{"Name": "DB Mini"}],
        "details": {"Score": 200, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"},
    }

    print_results(
        found_song_name,
        best_data=best_data,
        best_gear=[{"Name": "G1", "type": "Hat"}],
        best_minis=[{"Name": "M1"}],
        fg_variants=[],
        status_emit_fn=_noop_status_emit,
        prev_record=prev_record,
    )

    out = capsys.readouterr().out
    assert "Best Base Score Found: 200" in out
    assert "Hat: DB Gear" in out
    assert "Hat: G1" not in out


def test_results_printer_best_fg_score_uses_variants_only(capsys):
    """
    Regression test:
    Console output must reflect the FG variants passed for this run.
    """
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    found_song_name = "Test Song"
    best_data = {"Score": 100, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"}

    fg_variant = {
        "data": {
            "Score": 90,
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Selected Element": "Rush",
            "response_surface": _FG_SURFACE,
            "ForceGreats": {"final_score": 90},
        },
        "gear": [{"Name": "G2", "type": "Hat"}],
        "minis": [{"Name": "M2"}],
        "_is_ga": True,
        "score": 100,
        "fg_score": 90,
    }

    print_results(
        found_song_name,
        best_data=best_data,
        best_gear=[{"Name": "G1", "type": "Hat"}],
        best_minis=[{"Name": "M1"}],
        fg_variants=[fg_variant],
        status_emit_fn=_noop_status_emit,
    )

    out = capsys.readouterr().out
    assert "Best Base Score Found: 100" in out
    assert "Best FG Score Found: 90" in out


def test_results_printer_ignores_legacy_config_only_variant(capsys):
    """
    Regression test:
    A retired config-only payload is not FG authority. Prefer the variant carrying
    the exact response surface even when the legacy payload has a higher score.
    """
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    found_song_name = "Test Song"
    best_data = {"Score": 100, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"}

    zero_cfg_variant = {
        "data": {
            "Score": 100,
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Selected Element": "Rush",
            "ForceGreats": {"config": {"NonFever1": 0, "NonFever2": 0}, "final_score": 100},
        },
        "gear": [{"Name": "G1", "type": "Hat"}],
        "minis": [{"Name": "M1"}],
        "score": 100,
        "fg_score": 100,
    }

    response_surface_variant = {
        "data": {
            "Score": 90,
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Selected Element": "Rush",
            "response_surface": _FG_SURFACE,
            "ForceGreats": {"final_score": 90},
        },
        "gear": [{"Name": "G2", "type": "Hat"}],
        "minis": [{"Name": "M2"}],
        "score": 100,
        "fg_score": 90,
    }

    print_results(
        found_song_name,
        best_data=best_data,
        best_gear=[],
        best_minis=[],
        fg_variants=[zero_cfg_variant, response_surface_variant],
        status_emit_fn=_noop_status_emit,
    )

    out = capsys.readouterr().out
    assert "Best FG Score Found: 90\n" in out
    assert "Hat: G2\n" in out
    assert "G1" not in out
