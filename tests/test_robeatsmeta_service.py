from __future__ import annotations

import shutil
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
    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", raising=False)
    monkeypatch.setattr(service, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(service, "DATA_ROOT", tmp_path / "Data")
    monkeypatch.setattr(service, "GEAR_DIR", tmp_path / "Data" / "Gear")
    monkeypatch.setattr(service, "_TIMELINE_FRONTIER_CACHE_DIR", tmp_path / "bin" / "timeline_frontier_cache")
    monkeypatch.setattr(service, "_FG_RESPONSE_FRONTIER_CACHE_DIR", tmp_path / "bin" / "fg_response_frontier_cache")
    monkeypatch.setattr(service, "_SERVICE_DRAINING_FOR_UPDATE", False)
    service._AUTHORITATIVE_PUBLICATION_READY.clear()
    service.clear_official_song_catalog_cache()
    with service._INFLIGHT_SOLVES_LOCK:
        service._INFLIGHT_SOLVES.clear()
    yield tmp_path
    service._AUTHORITATIVE_PUBLICATION_READY.clear()
    service.clear_official_song_catalog_cache()
    with service._INFLIGHT_SOLVES_LOCK:
        service._INFLIGHT_SOLVES.clear()


def test_list_official_songs_reads_headers(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    songs = {s["songId"]: s for s in service.list_official_songs()}
    assert songs["Canon in D [Normal]"]["difficulty"] == "Normal"
    assert songs["Canon in D [Normal]"]["primaryElement"] == "Beat"
    assert songs["Feeding [Hard]"]["difficulty"] == "Hard"


def test_completed_publication_becomes_the_website_optimizer_data_source(data_root):
    published = data_root / "published" / "Data"
    (published / "Gear").mkdir(parents=True)

    service._activate_published_data(published)

    assert service._AUTHORITATIVE_PUBLICATION_READY.is_set()
    assert service.DATA_ROOT == published.resolve()
    assert service.GEAR_DIR == (published / "Gear").resolve()


def test_api_catalog_uses_configured_webport_song_library(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Private MetaFinder Chart")
    webport_data = data_root / "[REDACTED PRIVATE REPOSITORY]" / "Data"
    for difficulty in ("Easy", "Normal", "Hard"):
        (webport_data / f"{difficulty} Songs").mkdir(parents=True)
    external_chart = webport_data / "Hard Songs" / "canonical.txt"
    external_chart.write_text(
        "Song Name\tCanonical Replay Chart\n"
        "Difficulty\t24\n"
        "Primary Color\tBeat\n"
        "Secondary Color\tVibe\n"
        "Song Data\n"
        "1000\t0\t0\t1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", str(webport_data))

    songs = service.list_official_songs()

    assert [song["songId"] for song in songs] == ["Canonical Replay Chart"]
    assert service.find_official_chart("Canonical Replay Chart") == external_chart
    with pytest.raises(service.RequestError):
        service.find_official_chart("Private MetaFinder Chart")


def test_configured_webport_library_requires_all_difficulty_directories(data_root, monkeypatch):
    webport_data = data_root / "[REDACTED PRIVATE REPOSITORY]" / "Data"
    (webport_data / "Hard Songs").mkdir(parents=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", str(webport_data))

    with pytest.raises(RuntimeError, match="Easy Songs.*Normal Songs"):
        service.list_official_songs()


def test_service_starts_frontier_server_maintenance(monkeypatch):
    calls: list[str] = []

    class _Server:
        daemon_threads = False

        def __init__(self, *_args, **_kwargs):
            pass

        def serve_forever(self):
            calls.append("serve")

        def server_close(self):
            calls.append("close")

    class _Thread:
        def __init__(self, *, target, **_kwargs):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(service, "ThreadingHTTPServer", _Server)
    monkeypatch.setattr(service.threading, "Thread", _Thread)

    class _Maintainer:
        def __init__(self, **_kwargs):
            calls.append("init")

        def serve_forever(self):
            calls.append("maintain")

        def stop(self):
            calls.append("stop")

    monkeypatch.setattr(service, "FrontierServerMaintainer", _Maintainer)

    assert service.main(["--host", "127.0.0.1", "--port", "0"]) == 0

    assert calls == ["init", "maintain", "serve", "stop", "close"]


def test_find_official_chart_exact_match(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    chart = service.find_official_chart("Canon in D [Normal]")
    assert chart.read_text(encoding="utf-8").startswith("Song Name\tCanon in D [Normal]")


def test_official_song_catalog_reuses_header_scan_for_lookup(data_root, monkeypatch):
    _write_chart(data_root, "Normal", "Canon in D [Normal]", filename="canon.txt")
    _write_chart(data_root, "Hard", "Feeding [Hard]", filename="feeding.txt")

    real_read_full_header = service._read_full_header
    scanned: list[Path] = []

    def counted_read_full_header(path: Path) -> dict[str, str]:
        scanned.append(path)
        return real_read_full_header(path)

    monkeypatch.setattr(service, "_read_full_header", counted_read_full_header)

    songs = service.list_official_songs()
    chart = service.find_official_chart("Feeding [Hard]")

    assert [song["songId"] for song in songs] == ["Canon in D [Normal]", "Feeding [Hard]"]
    assert chart.name == "feeding.txt"
    assert len(scanned) == 2


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


def test_custom_chart_event_limit_rejects_before_solve(data_root, monkeypatch):
    monkeypatch.setattr(service, "_MAX_CUSTOM_CHART_EVENTS", 2)
    chart = "Song Name\tCustom\nSong Data\n0.1\t1\t1\t1\n0.2\t2\t2\t1\n0.3\t3\t3\t1\n"

    with pytest.raises(service.RequestError, match="exceeds 2 replay events"):
        service.solve({"jobId": "too_large", "chartText": chart})


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

    result = service.solve(
        {"jobId": "job_abc", "targetSongId": "Feeding [Hard]", "timingMode": "zero_ms"}
    )

    assert result == [entry]  # full T5 leaderboard returned verbatim (website persists + replays it)
    env = captured["env"]
    assert env["EVOLUTION_DB_PATH"].endswith("result.db")  # output DB redirected off evolution.db
    run_root = data_root / "runs" / "job_abc"
    assert Path(env["ROBEATSMETA_OPTIMIZER_DATA_DIR"]) == run_root / "Data"  # isolated song source
    assert Path(env["ROBEATSMETA_OPTIMIZER_BIN_DIR"]) == run_root / "bin"  # isolated run state
    assert Path(env["TIMELINE_FRONTIER_CACHE_DIR"]) == data_root / "bin" / "timeline_frontier_cache"
    assert Path(env["FG_RESPONSE_FRONTIER_CACHE_DIR"]) == data_root / "bin" / "fg_response_frontier_cache"


def test_custom_solve_frontier_caches_are_inside_throwaway_workspace(data_root, monkeypatch):
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))
    captured: dict[str, str] = {}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            captured.update(kwargs["env"])
            self.returncode = 0

        def communicate(self, timeout=None):
            return "", ""

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service, "get_best_loadouts", lambda *args, **kwargs: [{"loadout_hash": "h"}])

    service.solve({
        "jobId": "job_custom",
        "chartText": "Song Name\tCustom\nSong Data\n0.500\t1\t1\t1\n",
    })

    run_bin = data_root / "runs" / "job_custom" / "bin"
    assert Path(captured["TIMELINE_FRONTIER_CACHE_DIR"]) == run_bin / "timeline_frontier_cache"
    assert Path(captured["FG_RESPONSE_FRONTIER_CACHE_DIR"]) == run_bin / "fg_response_frontier_cache"
    assert not (data_root / "runs" / "job_custom").exists()


def test_solve_stamps_requested_timing_mode_into_isolated_chart(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))

    captured: dict[str, str] = {}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            chart_path = Path(kwargs["env"]["ROBEATSMETA_OPTIMIZER_DATA_DIR"]) / "Hard" / "job_timing.txt"
            captured["chart"] = chart_path.read_text("utf-8")
            self.returncode = 0

        def communicate(self, timeout=None):
            return ("", "")

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service, "get_best_loadouts", lambda *args, **kwargs: [{"loadout_hash": "h"}])

    service.solve(
        {"jobId": "job_timing", "targetSongId": "Feeding [Hard]", "timingMode": "zero_ms"}
    )

    assert "Timing Mode\tzero_ms" in captured["chart"]


def test_solve_rejects_unknown_timing_mode(data_root):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    with pytest.raises(service.RequestError, match="unknown timingMode"):
        service.solve(
            {"jobId": "job_timing", "targetSongId": "Feeding [Hard]", "timingMode": "approximate"}
        )


def _capture_solve_config(data_root, monkeypatch, request: dict) -> str:
    """Run one mocked solve and return the config.ini text the service generated for it."""
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(data_root / "runs"))

    captured: dict[str, str] = {}
    entry = {"loadout_hash": "h", "score": 999, "gear": ["A"], "minis": ["B"], "details": {}}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            env = kwargs["env"]
            captured["config"] = Path(env["METAFINDER_CONFIG_PATH"]).read_text("utf-8")
            self.returncode = 0

        def communicate(self, timeout=None):
            return ("", "")

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service, "get_best_loadouts", lambda *a, **k: [entry])
    service.solve(request)
    return captured["config"]


def test_solve_default_reasoning_omits_search_knobs(data_root, monkeypatch):
    # "default" (and absent) must reproduce stock behavior: no GA search knobs are written, so
    # config.py's own fallbacks apply exactly as before this feature existed.
    config = _capture_solve_config(data_root, monkeypatch, {"jobId": "job_def", "targetSongId": "Feeding [Hard]"})
    assert "GA_SearchDepth" not in config
    assert "GA_MultiStart" not in config


def test_solve_strong_reasoning_scales_search_knobs(data_root, monkeypatch):
    config = _capture_solve_config(
        data_root, monkeypatch, {"jobId": "job_str", "targetSongId": "Feeding [Hard]", "reasoning": "strong"}
    )
    # 2x of the stock bases (125, 3).
    assert "GA_SearchDepth = 250" in config
    assert "GA_MultiStart = 6" in config


def test_solve_max_reasoning_scales_search_knobs(data_root, monkeypatch):
    config = _capture_solve_config(
        data_root, monkeypatch, {"jobId": "job_max", "targetSongId": "Feeding [Hard]", "reasoning": "MAX"}
    )
    # 4x of the stock bases (125, 3). Case-insensitive; unknown values fall back to default.
    assert "GA_SearchDepth = 500" in config
    assert "GA_MultiStart = 12" in config


def test_solve_unknown_reasoning_falls_back_to_default(data_root, monkeypatch):
    config = _capture_solve_config(
        data_root, monkeypatch, {"jobId": "job_unk", "targetSongId": "Feeding [Hard]", "reasoning": "ultra"}
    )
    assert "GA_SearchDepth" not in config


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
    monkeypatch.setattr(service, "_SERVICE_DRAINING_FOR_UPDATE", False)
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


# --- custom gear / mini pool -------------------------------------------------

_CUSTOM_GEAR = {"name": "Test Hat", "type": "Hat", "chill": 30, "ppoint": 20}
_CUSTOM_MINI = {"name": "Test Mini", "type": "Chill", "chill": 90, "cbmlt": 30}


@pytest.mark.parametrize(
    "request_payload",
    [
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, name=f"Hat {i}") for i in range(6)]}, id="over-item-cap"),
        pytest.param({"customGear": {"name": "Hat"}}, id="not-a-list"),
        pytest.param({"customGear": ["Hat"]}, id="item-not-an-object"),
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, name='a,b"\nHat')]}, id="csv-hostile-name"),
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, name="=1+1")]}, id="formula-injection-name"),
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, name="x" * 33)]}, id="name-too-long"),
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, type="Wings")]}, id="unknown-slot"),
        pytest.param({"customMinis": [dict(_CUSTOM_MINI, type="Sparkle")]}, id="unknown-mini-type"),
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, chill=-1)]}, id="negative-stat"),
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, chill=10**9)]}, id="stat-out-of-range"),
        pytest.param({"customGear": [dict(_CUSTOM_GEAR, chill="30")]}, id="stat-not-an-int"),
        pytest.param({"customGear": [_CUSTOM_GEAR, dict(_CUSTOM_GEAR, type="Face")]}, id="duplicate-name"),
    ],
)
def test_custom_pool_rejects_invalid_requests(request_payload):
    with pytest.raises(service.RequestError):
        service._custom_pool_for_request(request_payload)


def test_custom_pool_rows_land_in_the_request_copy_and_never_the_catalog(tmp_path):
    catalog = Path(service.__file__).resolve().parents[1] / "Data" / "Gear"
    before = (catalog / "Gears.csv").read_bytes(), (catalog / "Minis.csv").read_bytes()

    work = tmp_path / "Gear"
    shutil.copytree(catalog, work)
    pool = service._custom_pool_for_request({"customGear": [_CUSTOM_GEAR], "customMinis": [_CUSTOM_MINI]})
    service._append_custom_pool_rows(work, pool)

    from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows

    gear = next(g for g in parse_gear_rows(str(work / "Gears.csv")) if g["Name"] == "Test Hat")
    mini = next(m for m in parse_mini_rows(str(work / "Minis.csv")) if m["Name"] == "Test Mini")
    assert (gear["type"], gear["Chill"], gear["Perfect Points"]) == ("Hat", 30, 20)
    assert (mini["type"], mini["Chill"], mini["Combo Multiplier"]) == ("Chill", 90, 30)
    # The repeated L1 ascension columns in Minis.csv must stay empty for a custom mini.
    assert "Mini Ascension Base Chill" not in mini
    assert ((catalog / "Gears.csv").read_bytes(), (catalog / "Minis.csv").read_bytes()) == before


def test_custom_pool_refuses_to_redefine_a_catalog_item(tmp_path):
    catalog = Path(service.__file__).resolve().parents[1] / "Data" / "Gear"
    work = tmp_path / "Gear"
    shutil.copytree(catalog, work)
    import csv

    with (catalog / "Gears.csv").open(encoding="utf-8-sig", newline="") as handle:
        # A catalog name the validator itself accepts, so the collision check is what rejects it.
        taken = next(
            row["Gear Name"]
            for row in csv.DictReader(handle)
            if service._CUSTOM_ITEM_NAME_RE.match(str(row["Gear Name"]).strip())
        )
    pool = service._custom_pool_for_request({"customGear": [dict(_CUSTOM_GEAR, name=taken)]})
    with pytest.raises(service.RequestError):
        service._append_custom_pool_rows(work, pool)


@pytest.mark.parametrize(
    "request_payload",
    [
        pytest.param({"excludeGear": "Hat"}, id="not-a-list"),
        pytest.param({"excludeGear": [123]}, id="not-a-string"),
        pytest.param({"excludeGear": ["a\nb"]}, id="newline-in-name"),
        pytest.param({"excludeGear": ['a"b']}, id="quote-in-name"),
        pytest.param({"excludeGear": ["x" * 65]}, id="name-too-long"),
        pytest.param({"excludeGear": [f"Hat {i}" for i in range(401)]}, id="over-gear-cap"),
        pytest.param({"excludeMinis": [f"Mini {i}" for i in range(201)]}, id="over-mini-cap"),
    ],
)
def test_excluded_names_reject_invalid_requests(request_payload):
    with pytest.raises(service.RequestError):
        service._custom_pool_for_request(request_payload)


def test_excluded_names_accept_real_catalog_names_with_punctuation():
    # Real names carry characters a USER may not invent ("(The) Red * Room", commas, unicode).
    pool = service._custom_pool_for_request(
        {"excludeGear": ["Juggernaut's Goggles"], "excludeMinis": ["(The) Red * Room", "t+pazolite"]}
    )
    assert pool["excludeGear"] == ["Juggernaut's Goggles"]
    assert pool["excludeMinis"] == ["(The) Red * Room", "t+pazolite"]


def test_excluded_rows_leave_the_request_copy_without_them_and_never_the_catalog(tmp_path):
    from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows

    catalog = Path(service.__file__).resolve().parents[1] / "Data" / "Gear"
    before = (catalog / "Gears.csv").read_bytes(), (catalog / "Minis.csv").read_bytes()
    gears_before = parse_gear_rows(str(catalog / "Gears.csv"))
    minis_before = parse_mini_rows(str(catalog / "Minis.csv"))
    drop_gear = [g["Name"] for g in gears_before[:3]]
    drop_mini = [m["Name"] for m in minis_before[:2]]

    work = tmp_path / "Gear"
    shutil.copytree(catalog, work)
    pool = service._custom_pool_for_request(
        {"customGear": [_CUSTOM_GEAR], "excludeGear": drop_gear, "excludeMinis": drop_mini}
    )
    service._remove_excluded_rows(work, pool)
    service._append_custom_pool_rows(work, pool)

    gears_after = parse_gear_rows(str(work / "Gears.csv"))
    minis_after = parse_mini_rows(str(work / "Minis.csv"))
    assert {g["Name"] for g in gears_after}.isdisjoint(drop_gear)
    assert {m["Name"] for m in minis_after}.isdisjoint(drop_mini)
    # exactly the excluded rows left, and the custom one arrived
    assert len(gears_after) == len(gears_before) - len(drop_gear) + 1
    assert len(minis_after) == len(minis_before) - len(drop_mini)
    assert _CUSTOM_GEAR["name"] in {g["Name"] for g in gears_after}
    assert ((catalog / "Gears.csv").read_bytes(), (catalog / "Minis.csv").read_bytes()) == before


def test_excluding_an_unknown_name_is_a_no_op(tmp_path):
    from gear_optimizer.data.csv_parser import parse_gear_rows

    catalog = Path(service.__file__).resolve().parents[1] / "Data" / "Gear"
    work = tmp_path / "Gear"
    shutil.copytree(catalog, work)
    pool = service._custom_pool_for_request({"excludeGear": ["No Such Gear At All"]})
    service._remove_excluded_rows(work, pool)
    # A stale exclusion (catalog moved on) must not fail the solve or drop anything.
    assert len(parse_gear_rows(str(work / "Gears.csv"))) == len(parse_gear_rows(str(catalog / "Gears.csv")))
