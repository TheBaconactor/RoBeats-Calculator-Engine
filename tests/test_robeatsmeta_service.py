from __future__ import annotations

import subprocess
import threading
import time
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
    with service._INFLIGHT_SOLVES_LOCK:
        service._INFLIGHT_SOLVES.clear()
    yield tmp_path
    with service._INFLIGHT_SOLVES_LOCK:
        service._INFLIGHT_SOLVES.clear()


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


def test_chart_text_and_result_song_name_preserves_official_identity(data_root):
    _write_chart(data_root, "Hard", "Feeding [Hard]")

    chart_text, result_song_name = service.chart_text_and_result_song_name_for_request(
        {"jobId": "job_abc", "targetSongId": "Feeding [Hard]"},
        fallback_name="job_abc",
    )

    assert "Song Name\tFeeding [Hard]" in chart_text
    assert result_song_name == "Feeding [Hard]"


def test_chart_text_and_result_song_name_custom_uses_job_key(data_root):
    chart_text, result_song_name = service.chart_text_and_result_song_name_for_request(
        {"jobId": "job_abc", "chartText": "Song Name\tCustom\nSong Data\n500\t0\t0\t1"},
        fallback_name="job_abc",
    )

    assert chart_text.startswith("Song Name\tCustom")
    assert result_song_name == "job_abc"


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

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            env = kwargs["env"]
            captured["env"] = env
            # The chart file is keyed by the job slug, but its Song Name remains the official
            # song identity. Mini Ascension song targets match against this header.
            chart = (Path(env["ROBEATSMETA_OPTIMIZER_DATA_DIR"]) / "Hard" / "job_abc.txt").read_text("utf-8")
            assert "Song Name\tFeeding [Hard]" in chart
            self.returncode = 0

        def communicate(self, timeout=None):
            return ("", "")

    def fake_loadouts(song_name, **kwargs):
        assert song_name == "Feeding [Hard]"
        assert kwargs["team_buff"] == "T5"
        assert kwargs["limit"] == 51  # full leaderboard, not a single rank #1
        return [entry]

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service, "get_best_loadouts", fake_loadouts)

    result = service.solve({"jobId": "job_abc", "targetSongId": "Feeding [Hard]"})

    assert result == [entry]  # full T5 leaderboard returned verbatim (website persists + replays it)
    env = captured["env"]
    assert env["EVOLUTION_DB_PATH"].endswith("result.db")  # output DB redirected off evolution.db
    assert env["ROBEATSMETA_OPTIMIZER_DATA_DIR"].endswith("job_abc/Data")  # isolated song source
    assert env["ROBEATSMETA_OPTIMIZER_BIN_DIR"].endswith("job_abc/bin")  # isolated run state


def test_solve_joins_duplicate_live_job_instead_of_spawning_again(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))

    started = threading.Event()
    release = threading.Event()
    popen_count = 0
    popen_lock = threading.Lock()
    entry = {"loadout_hash": "h", "score": 999, "gear": ["A"], "minis": ["B"], "details": {}}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            nonlocal popen_count
            with popen_lock:
                popen_count += 1
            self.returncode = 0
            started.set()

        def communicate(self, timeout=None):
            assert release.wait(timeout=2.0)
            return ("", "")

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service, "get_best_loadouts", lambda *args, **kwargs: [entry])

    results: list[list[dict[str, object]]] = []
    errors: list[BaseException] = []

    def call_solve() -> None:
        try:
            results.append(service.solve({"jobId": "job_abc", "targetSongId": "Feeding [Hard]"}))
        except BaseException as exc:  # pragma: no cover - makes thread failures visible in assertion
            errors.append(exc)

    first = threading.Thread(target=call_solve)
    second = threading.Thread(target=call_solve)
    first.start()
    assert started.wait(timeout=2.0)
    second.start()
    time.sleep(0.05)
    release.set()
    first.join(timeout=2.0)
    second.join(timeout=2.0)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert results == [[entry], [entry]]
    assert popen_count == 1


def test_solve_propagates_optimizer_failure(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            self.returncode = 1

        def communicate(self, timeout=None):
            return ("", "boom")

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    with pytest.raises(RuntimeError):
        service.solve({"jobId": "job_x", "targetSongId": "Feeding [Hard]"})


def test_solve_times_out_and_kills_process_group(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))

    killed: dict[str, int] = {}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            self.pid = 4321
            self.returncode = None
            self._calls = 0

        def communicate(self, timeout=None):
            self._calls += 1
            if timeout is not None:  # the guarded solve call -> simulate a hang
                raise subprocess.TimeoutExpired(cmd="main.py", timeout=timeout)
            return ("", "")  # the post-kill drain

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service, "_kill_process_group", lambda proc: killed.setdefault("pid", proc.pid))

    with pytest.raises(RuntimeError, match="timed out"):
        service.solve({"jobId": "job_t", "targetSongId": "Feeding [Hard]"})
    assert killed["pid"] == 4321  # the whole process group was reaped, not orphaned


def test_read_json_rejects_oversize_body():
    handler = service.RoBeatsMetaServiceHandler.__new__(service.RoBeatsMetaServiceHandler)
    handler.headers = {"Content-Length": str(service._MAX_BODY_BYTES + 1)}
    with pytest.raises(service.RequestTooLarge):
        handler._read_json()


def _peak_concurrent_slots(workers: int, available: int, min_free: int, monkeypatch) -> int:
    """Drive N threads through the memory-admission gate and return the peak simultaneous slots."""
    monkeypatch.setattr(service, "_MIN_FREE_BYTES", min_free)
    monkeypatch.setattr(service, "_available_bytes", lambda: available)
    monkeypatch.setattr(service, "_active_solves", 0)
    peak = {"n": 0}
    peak_lock = threading.Lock()
    start = threading.Barrier(workers)

    def worker() -> None:
        start.wait()  # release together to maximize contention
        service._acquire_solve_slot()
        try:
            with peak_lock:
                peak["n"] = max(peak["n"], service._active_solves)
            time.sleep(0.05)  # hold the slot so overlap is observable
        finally:
            service._release_solve_slot()

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return peak["n"]


def test_memory_guard_serializes_solves_when_memory_low(monkeypatch):
    # Available memory always below the floor -> only the first (progress-guaranteed) solve runs;
    # additional solves wait for it to finish, so at most one runs at a time.
    peak = _peak_concurrent_slots(workers=4, available=0, min_free=8 * 1024 * 1024 * 1024, monkeypatch=monkeypatch)
    assert peak == 1


def test_memory_guard_allows_concurrency_when_memory_ample(monkeypatch):
    # Plenty of memory -> the gate admits everyone; concurrency is bounded only by the pool.
    peak = _peak_concurrent_slots(workers=4, available=64 * 1024 * 1024 * 1024, min_free=1, monkeypatch=monkeypatch)
    assert peak == 4
