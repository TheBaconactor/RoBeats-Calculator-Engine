from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from gear_optimizer.data.database import init_db, save_loadouts_batch


def _write_cfg(path: Path) -> None:
    # Keep it explicit: fixed TeamBuff mode with no TeamColor override (falls back to song primary).
    path.write_text(
        "\n".join(
            [
                "[IterationEngine]",
                "",
                "[TeamContributionBuffConstant]",
                "TeamColor=",
                "TeamBuff=T10",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_backfill_stats_script_uses_row_team_buff(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "evolution.db"
    cfg_path = tmp_path / "config.ini"
    _write_cfg(cfg_path)

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("METAFINDER_CONFIG_PATH", str(cfg_path))

    init_db()
    save_loadouts_batch(
        "Song T10",
        [
            {
                "score": 1,
                "fg_score": 0,
                "gear": ["Hat X", "Neck X", "Face X", "Shirt X", "Back X", "Pants X"],
                "minis": ["Mini X", "Mini Y", "Mini Z"],
                "details": {
                    "Stats": {
                        "Perfect Points": 0,
                        "Combo Multiplier": 0,
                        "Fever Multiplier": 0,
                        "Fever Fill Rate": 0,
                        "Fever Time": 0,
                        "Chill": 0,
                        "Flow": 0,
                        "Rush": 0,
                        "Beat": 0,
                        "Vibe": 0,
                    },
                    "GemCounts": {},
                    "FT": 0,
                    "FF": 0,
                    "PrimaryColor": "Rush",
                    "SecondaryColor": "Flow",
                    "SelectedElement": "Rush",
                },
            }
        ],
        team_buff="T10",
    )

    env = os.environ.copy()
    env["EVOLUTION_DB_PATH"] = str(db_path)
    env["METAFINDER_CONFIG_PATH"] = str(cfg_path)
    subprocess.run(
        [sys.executable, str(repo_root / "tools" / "db" / "backfill_stats.py")],
        cwd=str(repo_root),
        env=env,
        check=True,
    )

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff=?",
            ("Song T10", "T10"),
        ).fetchone()
        assert row is not None and row[0]
        details = json.loads(row[0])
        st = details.get("st")
        assert isinstance(st, list) and len(st) >= 10

        # `st` packs keys in order:
        # ('Perfect Points','Combo Multiplier','Fever Multiplier','Fever Fill Rate','Fever Time','Chill','Flow','Rush','Beat','Vibe')
        assert int(st[0] or 0) == 20
        assert int(st[7] or 0) == 25
    finally:
        conn.close()
