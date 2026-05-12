from gear_optimizer.pipeline.post_processor_fg_updates import build_fg_update_state, canonicalize_fg_update_entries


def test_canonicalize_fg_update_entries_uses_calc_song_ref_arrays_and_cfg(monkeypatch):
    entries = [{"score": 123, "gear": ["G1"], "minis": ["M1"]}]
    calc_song = {"metadata": {"Primary Color": "Rush"}}
    ref_arrays = {"Perfect Points": [1.0]}
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5"}}
    calls = {}

    def fake_get_base_calc_song(file_path, cfg):
        calls["song_io"] = (file_path, cfg)
        return calc_song

    def fake_canonicalize(entries_arg, *, calc_song, ref_arrays, cfg_dict):
        calls["canonicalize"] = {
            "entries": entries_arg,
            "calc_song": calc_song,
            "ref_arrays": ref_arrays,
            "cfg_dict": cfg_dict,
        }
        return [{"score": 456}]

    monkeypatch.setattr("gear_optimizer.data.song_io.get_base_calc_song", fake_get_base_calc_song)
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.baseline_replay.canonicalize_baseline_persist_entries",
        fake_canonicalize,
    )

    result = canonicalize_fg_update_entries(
        entries,
        file_path="Data/Hard/Test Song.txt",
        cfg_dict=cfg_dict,
        ref_arrays=ref_arrays,
        song_name="Test Song",
    )

    assert result == [{"score": 456}]
    assert calls["song_io"] == ("Data/Hard/Test Song.txt", cfg_dict)
    assert calls["canonicalize"] == {
        "entries": entries,
        "calc_song": calc_song,
        "ref_arrays": ref_arrays,
        "cfg_dict": cfg_dict,
    }


def test_canonicalize_fg_update_entries_uses_cached_ref_arrays(monkeypatch):
    entries = [{"score": 123}]
    calc_song = {"metadata": {"Primary Color": "Rush"}}
    cached_ref_arrays = {"Perfect Points": [1.0]}
    calls = {}

    monkeypatch.setattr("gear_optimizer.data.song_io.get_base_calc_song", lambda _fp, _cfg: calc_song)
    monkeypatch.setattr("gear_optimizer.app_async_db._get_team_buff_ref_arrays_cached", lambda: cached_ref_arrays)

    def fake_canonicalize(entries_arg, *, calc_song, ref_arrays, cfg_dict):
        calls["ref_arrays"] = ref_arrays
        return list(entries_arg)

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.baseline_replay.canonicalize_baseline_persist_entries",
        fake_canonicalize,
    )

    result = canonicalize_fg_update_entries(
        entries,
        file_path="Data/Hard/Test Song.txt",
        cfg_dict={},
        ref_arrays=None,
        song_name="Test Song",
    )

    assert result == entries
    assert calls["ref_arrays"] is cached_ref_arrays


def test_canonicalize_fg_update_entries_rejects_missing_file_path():
    assert (
        canonicalize_fg_update_entries(
            [{"score": 123}],
            file_path="",
            cfg_dict={},
            ref_arrays={"Perfect Points": [1.0]},
            song_name="Test Song",
        )
        == []
    )


def test_build_fg_update_state_preserves_existing_state_and_reports_improving_fg():
    state = build_fg_update_state(
        {"queued_at": 123},
        [
            {"score": 100, "fg_score": 99, "force": {"ForceGreats": {"config": [1, 0]}}},
            {
                "score": 100,
                "fg_score": 125,
                "force": {"ForceGreats": {"config": [1, 0]}},
                "details": {"ForceGreats": {"config": [1, 0]}},
            },
            {"score": 100, "fg_score": 140},
        ],
    )

    assert state["queued_at"] == 123
    assert state["saw_fg_update"] is True
    assert state["saved_count"] == 3
    assert state["best_fg"] == 125
    assert len(state["fg_variants"]) == 3
    assert state["fg_variants"][1] == {
        "data": {"ForceGreats": {"config": [1, 0]}, "Score": 125},
        "gear": [],
        "minis": [],
        "score": 100,
        "fg_score": 125,
        "_is_ga": False,
    }
