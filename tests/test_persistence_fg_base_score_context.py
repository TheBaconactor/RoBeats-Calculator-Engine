from tests.songs_support import make_song


def test_authoritative_fg_preserves_source_paired_base_score(monkeypatch):
    from gear_optimizer.helpers.song_helpers import persistence_authority as authority

    monkeypatch.setattr(
        authority,
        "score_stats_exact_with_timeline_trace",
        lambda *_args, **_kwargs: {"score": 160, "TimelineFrontier": {}},
    )
    monkeypatch.setattr(
        authority,
        "score_stats_fixed_timing_exact",
        lambda *_args, **_kwargs: 160,
    )
    monkeypatch.setattr(
        authority,
        "score_force_greats_response_surface_exact",
        lambda *_args, **_kwargs: 150,
    )

    entry = {
        "score": 160,
        "fg_score": 1,
        "fg_base_score": 100,
        "details": {"Stats": {"Perfect Points": 0}},
        "force": {
            "BaseScore": 100,
            "Score": 1,
            "Stats": {"Perfect Points": 0},
            "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 1},
            "response_surface": [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        },
    }

    out = authority.canonicalize_authoritative_fg_entry(
        entry,
        song=make_song([0.0, 0.5], mode="zero_ms"),
        curves={},
    )

    assert out["score"] == 160
    assert out["fg_base_score"] == 100
    assert out["fg_score"] == 150
    assert out["force"]["BaseScore"] == 100
    assert out["force"]["Score"] == 150
