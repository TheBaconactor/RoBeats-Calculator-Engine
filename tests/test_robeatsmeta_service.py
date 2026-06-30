from __future__ import annotations

from pathlib import Path

from gear_optimizer import robeatsmeta_service as service


def _write_chart(root: Path, difficulty: str, song_name: str) -> None:
    folder = root / "Data" / difficulty
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "song.txt").write_text(
        f"Song Name\t{song_name}\n"
        f"Difficulty\t{difficulty}\n"
        "Primary Color\tBeat\n"
        "Secondary Color\tVibe\n"
        "Song Data\n"
        "1000\t0\t0\t1\n",
        encoding="utf-8",
    )


def test_resolve_official_song_uses_chart_header(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "REPO_ROOT", tmp_path)
    _write_chart(tmp_path, "Normal", "Canon in D by Johann Pachelbel [Normal]")

    assert service.resolve_official_song("Canon in D by Johann Pachelbel [Normal]") == (
        "Canon in D by Johann Pachelbel [Normal]",
        "Normal",
    )


def test_solve_official_request_returns_build_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "REPO_ROOT", tmp_path)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(tmp_path / "runs"))
    _write_chart(tmp_path, "Normal", "Canon in D by Johann Pachelbel [Normal]")
    solved: list[tuple[str, str, Path, int]] = []

    def fake_run(song_name: str, difficulty: str, db_path: Path, repeats: int) -> None:
        solved.append((song_name, difficulty, db_path, repeats))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text("placeholder", encoding="utf-8")

    def fake_best_loadouts(song_name: str, **kwargs):
        assert song_name == "Canon in D by Johann Pachelbel [Normal]"
        assert kwargs["team_buff"] == "T5"
        return [
            {
                "loadout_hash": "hash-1",
                "score": 123456,
                "gear": ["Ruby Guitar", "Bass Cannon"],
                "minis": ["Mini A", "Mini B", "Mini C"],
                "details": {
                    "Selected Element": "Beat",
                    "Primary Color": "Beat",
                    "Secondary Color": "Vibe",
                    "Stats": {
                        "Perfect Points": 1,
                        "Combo Multiplier": 2,
                        "Fever Multiplier": 3,
                        "Fever Fill Rate": 4,
                        "Fever Time": 5,
                        "Beat": 6,
                        "Vibe": 7,
                    },
                    "GemCounts": [1, 2, 3, 4, 5, 6],
                },
            }
        ]

    monkeypatch.setattr(service, "run_official_solve", fake_run)
    monkeypatch.setattr(service, "get_best_loadouts", fake_best_loadouts)

    build = service.solve_official_request(
        {
            "jobId": "job_abc",
            "targetSongId": "Canon in D by Johann Pachelbel [Normal]",
        }
    )

    assert solved[0][0] == "Canon in D by Johann Pachelbel [Normal]"
    assert solved[0][1] == "Normal"
    assert build["score"] == 123456
    assert build["gear"] == ["Ruby Guitar", "Bass Cannon"]
    assert build["minis"] == ["Mini A", "Mini B", "Mini C"]
    assert build["teamBuffTier"] == "T5"
    assert build["stats"]["perfectPoints"] == 1
