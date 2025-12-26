import pytest


def _noop_status_emit(_msg: str) -> None:
    return


def test_results_printer_fg_debug_uses_wrapper_fg_score_for_cached_entries(capsys):
    """
    Regression test:
    Cached FG reuse entries store the score at wrapper-level `fg_score`, while
    `data` is a persisted details dict that may not include `Score`.
    The debug printer must display the real score (not 0).
    """
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    found_song_name = "Test Song"
    best_data = {"Score": 123, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"}

    # Cached FG reuse shape: `data` is details-only (no Score),
    # wrapper carries `fg_score` and `score`.
    cached_fg_variant = {
        "data": {
            "FT": 1,
            "FF": 2,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Stats": {},
            "SelectedElement": "Rush",
            "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 999},
        },
        "gear": [{"Name": "G1", "type": "Hat"}],
        "minis": [{"Name": "M1"}],
        "score": 123,
        "fg_score": 999,
    }

    print_results(
        found_song_name,
        best_data=best_data,
        best_gear=[],
        best_minis=[],
        current_gear_list=[],
        current_mini_list=[],
        enable_gear=True,
        enable_mini=True,
        fg_variants=[cached_fg_variant],
        status_emit_fn=_noop_status_emit,
        fg_debug=True,
        ref_arrays={"dummy": 1},
        calc_song={"dummy": 1},
        cfg=None,
    )

    out = capsys.readouterr().out
    assert "=== FORCE GREATS OPTIMIZATION DEBUG ===" in out
    assert "\nTotal Score: 999\n" in out


def test_results_printer_fg_debug_uses_data_score_when_present(capsys):
    """
    Non-cached FG variants carry Score on the inner data dict; printer should
    still display it correctly.
    """
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    found_song_name = "Test Song"
    best_data = {"Score": 123, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"}

    fg_variant = {
        "data": {
            "Score": 777,
            "FT": 1,
            "FF": 2,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Selected Element": "Rush",
            "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 777},
        },
        "gear": [{"Name": "G1", "type": "Hat"}],
        "minis": [{"Name": "M1"}],
        "score": 123,
        "fg_score": 777,
    }

    print_results(
        found_song_name,
        best_data=best_data,
        best_gear=[],
        best_minis=[],
        current_gear_list=[],
        current_mini_list=[],
        enable_gear=True,
        enable_mini=True,
        fg_variants=[fg_variant],
        status_emit_fn=_noop_status_emit,
        fg_debug=True,
        ref_arrays={"dummy": 1},
        calc_song={"dummy": 1},
        cfg=None,
    )

    out = capsys.readouterr().out
    assert "=== FORCE GREATS OPTIMIZATION DEBUG ===" in out
    assert "\nTotal Score: 777\n" in out


def test_results_printer_fg_debug_falls_back_to_force_greats_final_score(capsys):
    """
    Regression test:
    Some callers may pass a wrapper-level `fg_score` of 0 while the persisted
    details dict contains the real FG score under ForceGreats.final_score.
    The debug printer should still display the real score (not 0).
    """
    from gear_optimizer.helpers.song_helpers.results_printer import print_results

    found_song_name = "Test Song"
    best_data = {"Score": 123, "FT": 0, "FF": 0, "GemCounts": {}, "Selected Element": "Rush"}

    fg_variant = {
        "data": {
            "FT": 1,
            "FF": 2,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Stats": {},
            "SelectedElement": "Rush",
            "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 999},
        },
        "gear": [{"Name": "G1", "type": "Hat"}],
        "minis": [{"Name": "M1"}],
        "score": 123,
        "fg_score": 0,
    }

    print_results(
        found_song_name,
        best_data=best_data,
        best_gear=[],
        best_minis=[],
        current_gear_list=[],
        current_mini_list=[],
        enable_gear=True,
        enable_mini=True,
        fg_variants=[fg_variant],
        status_emit_fn=_noop_status_emit,
        fg_debug=True,
        ref_arrays={"dummy": 1},
        calc_song={"dummy": 1},
        cfg=None,
    )

    out = capsys.readouterr().out
    assert "=== FORCE GREATS OPTIMIZATION DEBUG ===" in out
    assert "\nTotal Score: 999\n" in out


def test_results_printer_prefers_nonzero_fg_config_over_zero_config(capsys):
    """
    Regression test:
    When FG variants include a "no-op" config (all zeros), prefer showing the
    best variant with a non-zero FG config to match DB/persistence behavior.
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

    nonzero_cfg_variant = {
        "data": {
            "Score": 90,
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Fever Multiplier": 0, "Combo Multiplier": 0, "Perfect Points": 0, "Element": 0},
            "Selected Element": "Rush",
            "ForceGreats": {"config": {"NonFever1": 3, "NonFever2": 0}, "final_score": 90},
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
        current_gear_list=[],
        current_mini_list=[],
        enable_gear=True,
        enable_mini=True,
        fg_variants=[zero_cfg_variant, nonzero_cfg_variant],
        status_emit_fn=_noop_status_emit,
        fg_debug=True,
        ref_arrays={"dummy": 1},
        calc_song={"dummy": 1},
        cfg=None,
    )

    out = capsys.readouterr().out
    assert "\nTotal Score: 90\n" in out
    assert "FG Config: {'NonFever1': 3, 'NonFever2': 0}" in out
    assert "FG Config: {'NonFever1': 0, 'NonFever2': 0}" not in out
