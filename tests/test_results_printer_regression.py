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

