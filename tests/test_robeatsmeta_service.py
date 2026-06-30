from __future__ import annotations

from pathlib import Path

import pytest

from gear_optimizer import robeatsmeta_service as service


def _write_chart(root: Path, difficulty: str, song_name: str, filename: str = "song.txt") -> None:
    folder = root / "Data" / difficulty
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_text(
        f"Song Name\t{song_name}\n"
        f"Difficulty\t{difficulty}\n"
        "Primary Color\tBeat\n"
        "Secondary Color\tVibe\n"
        "Song Data\n"
        "1000\t0\t0\t1\n",
        encoding="utf-8",
    )


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(service, "DATA_ROOT", tmp_path / "Data")
    monkeypatch.setattr(service, "GEAR_DIR", tmp_path / "Data" / "Gear")
    return tmp_path


def test_list_official_songs_reads_headers(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    songs = {s["songId"]: s for s in service.list_official_songs()}
    assert songs["Canon in D [Normal]"]["difficulty"] == "Normal"
    assert songs["Canon in D [Normal]"]["primaryElement"] == "Beat"
    assert songs["Feeding [Hard]"]["difficulty"] == "Hard"


def test_find_official_chart_exact_match(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    chart = service.find_official_chart("Canon in D [Normal]")
    assert chart.read_text(encoding="utf-8").startswith("Song Name\tCanon in D [Normal]")


def test_find_official_chart_unknown_raises(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    with pytest.raises(service.RequestError):
        service.find_official_chart("Not A Real Song")  # no fuzzy/substring fallback


def test_chart_text_custom_takes_precedence(data_root):
    request = {"chartText": "Song Name\tCustom\nSong Data\n500\t0\t0\t1"}
    assert service.chart_text_for_request(request).startswith("Song Name\tCustom")


def test_chart_text_official_reads_file(data_root):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    assert "Song Name\tFeeding [Hard]" in service.chart_text_for_request({"targetSongId": "Feeding [Hard]"})


def test_chart_text_requires_a_source(data_root):
    with pytest.raises(service.RequestError):
        service.chart_text_for_request({"jobId": "x"})


def test_solve_runs_isolated_and_returns_loadout_entry(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))

    captured: dict[str, dict[str, str]] = {}
    entry = {"loadout_hash": "h", "score": 999, "gear": ["A"], "minis": ["B"], "details": {}}

    def fake_run(cmd, **kwargs):
        env = kwargs["env"]
        captured["env"] = env
        # the chart was written into the isolated Data dir, keyed by the job slug
        chart = (Path(env["ROBEATSMETA_OPTIMIZER_DATA_DIR"]) / "Hard" / "job_abc.txt").read_text("utf-8")
        assert "Song Name\tjob_abc" in chart

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    def fake_loadouts(song_name, **kwargs):
        assert song_name == "job_abc"
        assert kwargs["team_buff"] == "T5"
        return [entry]

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    monkeypatch.setattr(service, "get_best_loadouts", fake_loadouts)

    result = service.solve({"jobId": "job_abc", "targetSongId": "Feeding [Hard]"})

    assert result == entry  # raw loadout entry returned verbatim (website serializes it)
    env = captured["env"]
    assert env["EVOLUTION_DB_PATH"].endswith("result.db")  # output DB redirected off evolution.db
    assert env["ROBEATSMETA_OPTIMIZER_DATA_DIR"].endswith("job_abc/Data")  # isolated song source
    assert env["ROBEATSMETA_OPTIMIZER_BIN_DIR"].endswith("job_abc/bin")  # isolated run state


def test_solve_propagates_optimizer_failure(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "boom"

        return Result()

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        service.solve({"jobId": "job_x", "targetSongId": "Feeding [Hard]"})
