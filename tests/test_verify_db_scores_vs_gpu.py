import json
import sqlite3


def test_fg_score_verifier_replays_force_surface_not_paired_base(monkeypatch):
    from tools.db.verify_db_scores_vs_gpu import _replay_fg_score

    force = {
        "BaseStats": {"Perfect Points": 40, "Fever Time": 10},
        "response_surface": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    }
    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.exact_rescore.score_force_greats_response_surface_exact",
        lambda stats, calc_song, ref_arrays, surface: 456,
    )

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT 100 AS score, 456 AS fg_score, ? AS force_details_json",
            (json.dumps(force),),
        ).fetchone()
        assert _replay_fg_score(row, calc_song={}, ref_arrays={}) == 456
        assert int(row["score"]) != 456
    finally:
        conn.close()


def test_tutorial_song_resolves_to_easy_chart():
    from tools.db.verify_db_scores_vs_gpu import _infer_difficulty_from_song_name

    assert _infer_difficulty_from_song_name("Monday Night Monsters (Tutorial) by FinnMK") == "Easy"
