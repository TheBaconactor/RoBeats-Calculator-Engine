from __future__ import annotations

import json
import sqlite3
from configparser import ConfigParser
from pathlib import Path

from tools.db.recover_song_base_deficit import RecoverySettings, _resolve_song_target, _write_recovery_config


def test_write_recovery_config_overrides_expected_knobs(tmp_path: Path) -> None:
    base_cfg = tmp_path / "base.ini"
    base_cfg.write_text(
        """
[CalculateSong]
Song_Name = old song
Difficulty = Hard

[IterationEngine]
SongRepeats = 1
GA_SearchDepth = 50
GA_MultiStart = 1
GA_DBSeedProbability = 0.1
InFlightSongs = 16
FG_CandidateLimit = 51
FG_SearchRadius = 5
""".strip(),
        encoding="utf-8",
    )
    out_cfg = tmp_path / "recovery.ini"

    _write_recovery_config(
        out_path=out_cfg,
        base_config_path=base_cfg,
        target_song_name="Target Song",
        difficulty="Normal",
        settings=RecoverySettings(
            song_repeats=5,
            ga_search_depth=125,
            ga_multistart=5,
            ga_db_seed_probability=1.0,
            in_flight_songs=1,
        ),
    )

    cfg = ConfigParser()
    cfg.read(out_cfg, encoding="utf-8")

    assert cfg.get("CalculateSong", "Song_Name") == "Target Song"
    assert cfg.get("CalculateSong", "Difficulty") == "Normal"
    assert cfg.get("IterationEngine", "SongRepeats") == "5"
    assert cfg.get("IterationEngine", "SongQueueLimit") == "1"
    assert cfg.get("IterationEngine", "InFlightSongs") == "1"
    assert cfg.get("IterationEngine", "GA_SearchDepth") == "125"
    assert cfg.get("IterationEngine", "GA_MultiStart") == "5"
    assert cfg.get("IterationEngine", "GA_DBSeedProbability") == "1.0"
    assert cfg.get("IterationEngine", "IgnoreResumeQueue") == "true"


def test_resolve_song_target_prefers_exact_match_and_requested_difficulty(tmp_path: Path) -> None:
    db_path = tmp_path / "evolution.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE team_buff_loadouts (
                song_name TEXT,
                team_buff TEXT,
                score INTEGER,
                details_json TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO team_buff_loadouts(song_name, team_buff, score, details_json) VALUES (?, ?, ?, ?)",
            [
                (
                    "Target Song",
                    "T5",
                    100,
                    json.dumps({"Difficulty": "Normal"}),
                ),
                (
                    "Target Song (Hard) by Someone",
                    "T5",
                    999,
                    json.dumps({"Difficulty": "Hard"}),
                ),
                (
                    "Another Target Song",
                    "T5",
                    500,
                    json.dumps({"Difficulty": "Normal"}),
                ),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    target = _resolve_song_target(db_path=db_path, song_search="Target Song", difficulty="Normal")

    assert target["song_name"] == "Target Song"
    assert target["difficulty"] == "Normal"
