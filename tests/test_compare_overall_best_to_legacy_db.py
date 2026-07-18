import json
import sqlite3

from tools.db.compare_overall_best_to_legacy_db import (
    _best_fg_rescored_legacy,
    _song_file_from_name,
    _song_path_index,
)


def test_song_file_fallback_indexes_chart_headers(tmp_path):
    chart = tmp_path / "Data" / "Normal" / "filename-does-not-match.txt"
    chart.parent.mkdir(parents=True)
    chart.write_text(
        "Song Name\tCanonical Song by Artist\n"
        "Primary Color\tRush\n"
        "Secondary Color\tFlow\n"
        "Difficulty\tNormal\n"
        "Song Data\n",
        encoding="utf-8",
    )

    _song_path_index.cache_clear()
    assert _song_file_from_name(tmp_path, "Canonical Song by Artist") == chart


def test_fg_replay_uses_response_surface_not_legacy_config(tmp_path, monkeypatch):
    chart = tmp_path / "Data" / "Normal" / "Song by Artist.txt"
    chart.parent.mkdir(parents=True)
    chart.write_text("Song Name\tSong by Artist\nSong Data\n", encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE team_buff_fg_loadouts "
        "(song_name TEXT, team_buff TEXT, loadout_hash TEXT, force_details_json TEXT, details_json TEXT)"
    )
    conn.execute(
        "INSERT INTO team_buff_fg_loadouts VALUES (?, ?, ?, ?, ?)",
        (
            "Song by Artist",
            "T5",
            "surface-winner",
            json.dumps(
                {
                    "Stats": {"Rush": 1},
                    "response_surface": [0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0],
                    "ForceGreats": {"config": {"NonFever1": 1}},
                }
            ),
            "{}",
        ),
    )

    from gear_optimizer.data import database, song_io
    from gear_optimizer.solver.scoring import exact_rescore

    monkeypatch.setattr(database, "_base_details_from_force_payload", lambda _details, force: force)
    monkeypatch.setattr(database, "_unpack_stats_after_load", lambda details: details)
    monkeypatch.setattr(song_io, "get_base_calc_song", lambda _path, _cfg: {"song": True})
    monkeypatch.setattr(
        exact_rescore,
        "score_force_greats_response_surface_exact",
        lambda _stats, _song, _refs, surface: int(surface.great0),
    )

    best = _best_fg_rescored_legacy(
        conn,
        song="Song by Artist",
        team_buff="T5",
        project_root=tmp_path,
        cfg_dict={},
        ref_arrays={"ok": True},
        calc_song_cache={},
    )
    assert best == {"best": 7, "hash": "surface-winner"}


def test_fg_replay_legality_gate_rejects_unreachable_surface(tmp_path, monkeypatch):
    chart = tmp_path / "Data" / "Normal" / "Song by Artist.txt"
    chart.parent.mkdir(parents=True)
    chart.write_text("Song Name\tSong by Artist\nSong Data\n", encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE team_buff_fg_loadouts "
        "(song_name TEXT, team_buff TEXT, loadout_hash TEXT, force_details_json TEXT, details_json TEXT)"
    )
    conn.execute(
        "INSERT INTO team_buff_fg_loadouts VALUES (?, ?, ?, ?, ?)",
        (
            "Song by Artist",
            "T5",
            "phantom",
            json.dumps({"Stats": {"Rush": 1}, "response_surface": [0] * 11, "ForceGreats": {"frontier_trace": [{}]}}),
            "{}",
        ),
    )

    from gear_optimizer.data import database, song_io
    from gear_optimizer.solver import timing_envelope
    from tools.dev import audit_loadout_legality

    monkeypatch.setattr(database, "_base_details_from_force_payload", lambda _details, force: force)
    monkeypatch.setattr(database, "_unpack_stats_after_load", lambda details: details)
    monkeypatch.setattr(song_io, "get_base_calc_song", lambda _path, _cfg: {"song": True})
    monkeypatch.setattr(song_io, "clone_calc_song", lambda song: dict(song))
    monkeypatch.setattr(timing_envelope, "apply_timing_envelope", lambda _song, mode: None)
    monkeypatch.setattr(audit_loadout_legality, "audit_fg_loadout", lambda *_args, **_kwargs: ["phantom"])

    best = _best_fg_rescored_legacy(
        conn,
        song="Song by Artist",
        team_buff="T5",
        project_root=tmp_path,
        cfg_dict={},
        ref_arrays={"ok": True},
        calc_song_cache={},
        validate_legality=True,
    )
    assert best == {"best": 0, "hash": ""}
