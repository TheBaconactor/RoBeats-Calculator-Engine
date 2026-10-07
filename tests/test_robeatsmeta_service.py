from __future__ import annotations

import concurrent.futures
import io
import json
import os
import queue
import socket
import sqlite3
import shutil
import subprocess
import sys
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
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_PERSISTENT_SOLVER", "0")
    monkeypatch.setattr(service, "_PERSISTENT_SOLVE_WORKER", None)
    monkeypatch.setattr(service.db, "promote", lambda *_args, **_kwargs: None)
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


def test_completed_publication_becomes_the_service_data_source(data_root):
    published = data_root / "published" / "Data"
    (published / "Gear").mkdir(parents=True)

    service._activate_published_data(published)

    assert service._AUTHORITATIVE_PUBLICATION_READY.is_set()
    assert service.DATA_ROOT == published.resolve()
    assert service.GEAR_DIR == (published / "Gear").resolve()


def test_last_complete_publication_is_active_during_restart(data_root):
    code_revision = "a" * 40
    published = data_root / "snapshots" / code_revision / "Data"
    (published / "Gear").mkdir(parents=True)

    class _Distribution:
        @staticmethod
        def manifest_bytes():
            return f'{{"code_revision":"{code_revision}"}}'.encode()

    restored = service._activate_last_complete_publication(
        _Distribution(),  # type: ignore[arg-type]
        snapshots_root=data_root / "snapshots",
    )

    assert restored is True
    assert service._AUTHORITATIVE_PUBLICATION_READY.is_set()
    assert service.DATA_ROOT == published.resolve()


def test_api_catalog_uses_configured_external_song_library(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Private Calculator Chart")
    reference_data = data_root / "ReferenceClient" / "Data"
    for difficulty in ("Easy", "Normal", "Hard"):
        (reference_data / f"{difficulty} Songs").mkdir(parents=True)
    external_chart = reference_data / "Hard Songs" / "canonical.txt"
    external_chart.write_text(
        "Song Name\tCanonical Replay Chart\n"
        "Difficulty\t24\n"
        "Primary Color\tBeat\n"
        "Secondary Color\tVibe\n"
        "Song Data\n"
        "1000\t0\t0\t1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", str(reference_data))

    songs = service.list_official_songs()

    assert [song["songId"] for song in songs] == ["Canonical Replay Chart"]
    assert service.find_official_chart("Canonical Replay Chart") == external_chart
    with pytest.raises(service.RequestError):
        service.find_official_chart("Private Calculator Chart")


def test_external_catalog_cache_invalidates_when_a_chart_is_added(data_root, monkeypatch):
    reference_data = data_root / "ReferenceClient" / "Data"
    for difficulty in ("Easy", "Normal", "Hard"):
        (reference_data / f"{difficulty} Songs").mkdir(parents=True)
    normal_dir = reference_data / "Normal Songs"
    (normal_dir / "first.txt").write_text(
        "Song Name\tFirst Imported Chart\nSong Data\n1000\t0\t0\t1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", str(reference_data))

    assert [song["songId"] for song in service.list_official_songs()] == ["First Imported Chart"]

    (normal_dir / "second.txt").write_text(
        "Song Name\tSecond Imported Chart\nSong Data\n1000\t0\t0\t1\n",
        encoding="utf-8",
    )

    assert [song["songId"] for song in service.list_official_songs()] == [
        "First Imported Chart",
        "Second Imported Chart",
    ]


def test_the_next_image_serves_on_the_handed_over_listening_socket(monkeypatch):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    monkeypatch.setenv(service._LISTENER_FD_ENV, str(listener.fileno()))
    server = service._http_server("127.0.0.1", listener.getsockname()[1])
    try:
        assert server.socket.fileno() == listener.fileno()
        assert server.server_address == listener.getsockname()
        assert service._LISTENER_FD_ENV not in os.environ
    finally:
        server.socket.detach()
        listener.close()


def test_a_self_update_hands_the_listening_socket_to_the_next_image(monkeypatch):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    calls: list[str] = []
    maintainer_kwargs: dict[str, object] = {}
    executed: dict[str, object] = {}

    class _Server:
        daemon_threads = False

        def __init__(self, *_args, **_kwargs):
            self.socket = listener

        def serve_forever(self):
            maintainer_kwargs["restart_requested"]("abc123def4567890")

        def shutdown(self):
            calls.append("shutdown")

        def server_close(self):
            calls.append("close")

    class _Thread:
        def __init__(self, *, target, **_kwargs):
            self._target = target

        def start(self):
            self._target()

    class _Maintainer:
        def __init__(self, **kwargs):
            maintainer_kwargs.update(kwargs)

        def serve_forever(self):
            pass

        def stop(self):
            calls.append("stop")

    monkeypatch.delenv(service._LISTENER_FD_ENV, raising=False)
    monkeypatch.setattr(service, "ThreadingHTTPServer", _Server)
    monkeypatch.setattr(service.threading, "Thread", _Thread)
    monkeypatch.setattr(service, "_activate_last_complete_publication", lambda _state: True)
    monkeypatch.setattr(service, "FrontierServerMaintainer", _Maintainer)
    monkeypatch.setattr(service, "_reap_idle_persistent_worker_forever", lambda: None)
    monkeypatch.setattr(service, "_finish_server_code_update", lambda **_kwargs: None)
    monkeypatch.setattr(
        service.os, "execv", lambda _exe, args: executed.update(args=args, fd=os.environ[service._LISTENER_FD_ENV])
    )
    try:
        service.main(["--host", "127.0.0.1", "--port", "0"])
        assert calls == ["shutdown", "stop"]  # the listening socket stays open across the exec
        assert executed["fd"] == str(listener.fileno()) and listener.get_inheritable()
        assert executed["args"][1:3] == ["-m", "gear_optimizer.robeatsmeta_service"]
    finally:
        os.environ.pop(service._LISTENER_FD_ENV, None)
        listener.close()


def test_configured_external_library_requires_all_difficulty_directories(data_root, monkeypatch):
    reference_data = data_root / "ReferenceClient" / "Data"
    (reference_data / "Hard Songs").mkdir(parents=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", str(reference_data))

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
    monkeypatch.setattr(
        service,
        "_activate_last_complete_publication",
        lambda _state: calls.append("restore") or True,
    )

    maintainer_kwargs: dict[str, object] = {}

    class _Maintainer:
        def __init__(self, **kwargs):
            maintainer_kwargs.update(kwargs)
            calls.append("init")

        def serve_forever(self):
            calls.append("maintain")

        def stop(self):
            calls.append("stop")

    class _CatalogBuilder:
        def request(self):
            calls.append("catalog build")

    monkeypatch.setattr(service, "FrontierServerMaintainer", _Maintainer)
    monkeypatch.setattr(service, "_CatalogBuilder", _CatalogBuilder)
    monkeypatch.setattr(service, "_activate_published_data", lambda root: calls.append(f"activate {root}"))
    monkeypatch.setattr(service, "_reap_idle_persistent_worker_forever", lambda: calls.append("idle reaper"))

    assert service.main(["--host", "127.0.0.1", "--port", "0"]) == 0

    assert calls == ["restore", "init", "maintain", "idle reaper", "serve", "stop", "close"]
    # Publication prebuilds run in a child process, never on the service's maintenance thread.
    assert maintainer_kwargs["prebuild"] is service._prebuild_frontier_caches_isolated

    # Every publication the maintainer activates builds the charts it made newly solvable.
    maintainer_kwargs["publication_ready"](Path("published"))
    assert calls[-2:] == ["activate published", "catalog build"]


def test_frontier_refresh_endpoint_only_wakes_maintainer(data_root, monkeypatch):
    calls: list[tuple[object, object]] = []

    class _Maintainer:
        def request_refresh(self):
            calls.append(("wake", None))

    handler = service.RoBeatsMetaServiceHandler.__new__(service.RoBeatsMetaServiceHandler)
    handler.path = "/frontiers/refresh"
    handler.headers = {"Authorization": "Bearer secret"}
    handler.server = type("Server", (), {"frontier_maintainer": _Maintainer()})()
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_API_TOKEN", "secret")
    monkeypatch.setattr(handler, "_send", lambda status, payload: calls.append((status, payload)))

    handler.do_POST()

    assert calls == [("wake", None), (service.HTTPStatus.ACCEPTED, {"queued": True})]


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
        service.chart_text_and_result_song_name_for_request({"jobId": "x"}, fallback_name="x")


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
            captured["cmd"] = cmd
            # The chart file is keyed by the job slug, but its Song Name remains the official
            # song identity. Mini Ascension song targets match against this header.
            chart = (Path(env["ROBEATSMETA_OPTIMIZER_DATA_DIR"]) / "Hard" / "job_abc.txt").read_text("utf-8")
            assert "Song Name\tFeeding [Hard]" in chart
            self.returncode = 0

        def communicate(self, timeout=None):
            return ("", "")

    def fake_loadouts(path, song_name, tier, *, limit):
        assert song_name == "Feeding [Hard]"
        assert tier == "T5"
        assert limit == 51  # full leaderboard, not a single rank #1
        return [entry]

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service.legacy, "read_best_loadouts", fake_loadouts)

    result = service.solve(
        {"jobId": "job_abc", "targetSongId": "Feeding [Hard]", "timingMode": "non-precise"}
    )

    assert result == [entry]  # full T5 leaderboard returned verbatim for host persistence/replay
    assert captured["cmd"] == [sys.executable, str(service.REPO_ROOT / "main.py"), "run"]  # the standalone app
    env = captured["env"]
    assert env["EVOLUTION_DB_PATH"].endswith("result.db")  # output DB redirected off evolution.db
    run_root = Path(env["EVOLUTION_DB_PATH"]).parent
    assert run_root.parent == data_root / "runs"
    assert run_root.name.startswith("job_abc-")
    assert not run_root.exists()
    assert Path(env["ROBEATSMETA_OPTIMIZER_DATA_DIR"]) == run_root / "Data"  # isolated song source
    assert Path(env["ROBEATSMETA_OPTIMIZER_BIN_DIR"]) == run_root / "bin"  # isolated run state
    assert Path(env["TIMELINE_FRONTIER_CACHE_DIR"]) == data_root / "bin" / "timeline_frontier_cache"
    assert Path(env["FG_RESPONSE_FRONTIER_CACHE_DIR"]) == data_root / "bin" / "fg_response_frontier_cache"


def test_official_solve_uses_persistent_worker_for_mode_switches(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    worker_calls: list[dict[str, object]] = []
    entry = {"loadout_hash": "persistent", "score": 999}

    class FakeWorker:
        def request(self, payload):
            worker_calls.append(payload)
            return [entry]

    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_PERSISTENT_SOLVER", "1")
    monkeypatch.setattr(service, "_get_persistent_solve_worker", lambda: FakeWorker())

    result = service.solve(
        {
            "jobId": "persistent_mode_switch",
            "targetSongId": "Feeding [Hard]",
            "reasoning": "strong",
            "timingMode": "non-precise",
        }
    )

    assert result == [entry]
    assert len(worker_calls) == 1
    assert worker_calls[0]["reasoning"] == "strong"
    assert "Timing Mode\tnon-precise" in str(worker_calls[0]["chartText"])


def test_clean_official_solve_promotes_its_result(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True, exist_ok=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    entry = {"loadout_hash": "h", "score": 999, "gear": ["A"], "minis": ["B"], "details": {}}
    promoted: list[tuple[str, str, str, str]] = []

    class FakePopen:
        returncode = 0

        def __init__(self, *_args, **_kwargs):
            pass

        def communicate(self, timeout=None):
            return "", ""

    monkeypatch.setattr(service.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(service.legacy, "read_best_loadouts", lambda *args, **kwargs: [entry])
    monkeypatch.setattr(
        service.db,
        "promote",
        lambda source, target, song, tier: promoted.append((Path(source).name, target, song, tier)),
    )

    result = service.solve({"jobId": "job_promote", "targetSongId": "Feeding [Hard]"})

    assert result == [entry]
    # Merged from the solve's own result database while the isolated workspace still exists.
    assert promoted == [("result.db", str(service.paths().database), "Feeding [Hard]", "T5")]


def test_a_persistent_solve_asks_the_worker_to_promote(monkeypatch):
    payloads = []

    class FakeWorker:
        def request(self, payload):
            payloads.append(payload)
            return [{"score": 1}]

    monkeypatch.setattr(service, "_get_persistent_solve_worker", lambda: FakeWorker())
    monkeypatch.setattr(service, "_acquire_solve_slot", lambda: None)
    monkeypatch.setattr(service, "_release_solve_slot", lambda: None)
    for promote_to in ("/catalog/evolution.db", None):
        service._solve_persistent("job", "chart", "Song", 1, "default", promote_to=promote_to)
    assert payloads[0]["promoteTo"] == "/catalog/evolution.db"
    assert "promoteTo" not in payloads[1]


def test_only_clean_non_precise_official_solves_are_promoted(tmp_path, monkeypatch):
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "evolution.db"))
    clean = {"gear": [], "minis": [], "excludeGear": [], "excludeMinis": []}
    custom = {**clean, "gear": [{"name": "Custom"}]}

    def target(request, timing_mode="non-precise", pool=clean):
        return service._promotion_target(request, timing_mode=timing_mode, custom_pool=pool)

    assert target({"targetSongId": "Official"}) == str(tmp_path / "evolution.db")
    assert target({"targetSongId": "Official"}, timing_mode="precise") is None
    assert target({"targetSongId": "Official"}, pool=custom) is None
    assert target({"chartText": "Song Data\n"}) is None
    assert target({"targetSongId": "Official", "chartText": "Song Data\n"}) is None


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
    monkeypatch.setattr(service.legacy, "read_best_loadouts", lambda *args, **kwargs: [{"loadout_hash": "h"}])

    service.solve(
        {
            "jobId": "job_custom",
            "chartText": "Song Name\tCustom\nSong Data\n0.500\t1\t1\t1\n",
        }
    )

    workspace = Path(captured["EVOLUTION_DB_PATH"]).parent
    run_bin = workspace / "bin"
    assert Path(captured["TIMELINE_FRONTIER_CACHE_DIR"]) == run_bin / "timeline_frontier_cache"
    assert Path(captured["FG_RESPONSE_FRONTIER_CACHE_DIR"]) == run_bin / "fg_response_frontier_cache"
    assert not workspace.exists()


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
    monkeypatch.setattr(service.legacy, "read_best_loadouts", lambda *args, **kwargs: [{"loadout_hash": "h"}])

    service.solve({"jobId": "job_timing", "targetSongId": "Feeding [Hard]", "timingMode": "non-precise"})

    assert "Timing Mode\tnon-precise" in captured["chart"]


def test_solve_rejects_unknown_timing_mode(data_root):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    with pytest.raises(service.RequestError, match="unknown timingMode"):
        service.solve({"jobId": "job_timing", "targetSongId": "Feeding [Hard]", "timingMode": "approximate"})


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
    monkeypatch.setattr(service.legacy, "read_best_loadouts", lambda *a, **k: [entry])
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
    monkeypatch.setattr(service.legacy, "read_best_loadouts", lambda *args, **kwargs: [entry])

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


def test_available_bytes_darwin_excludes_compressible_and_speculative(monkeypatch):
    counters = {
        "vm.page_free_count": 100,
        "vm.page_pageable_external_count": 1000,
        "vm.page_purgeable_count": 10,
        "vm.page_speculative_count": 50,  # already inside pageable_external; must not be added
        "hw.pagesize": 16384,
    }
    monkeypatch.setattr(service.sys, "platform", "darwin")
    monkeypatch.setattr(service, "_sysctl_uint", counters.__getitem__)

    assert service._available_bytes() == (100 + 1000 + 10) * 16384


def test_available_bytes_darwin_sysctl_failure_raises(monkeypatch):
    def fail(name: str) -> int:
        raise OSError(2, name)

    monkeypatch.setattr(service.sys, "platform", "darwin")
    monkeypatch.setattr(service, "_sysctl_uint", fail)

    with pytest.raises(OSError):
        service._available_bytes()


@pytest.mark.skipif(sys.platform != "darwin", reason="reads macOS VM counters")
def test_sysctl_uint_reads_real_counters():
    assert service._sysctl_uint("vm.page_free_count") > 0  # a 4-byte counter
    assert service._sysctl_uint("hw.pagesize") > 0  # an 8-byte value
    with pytest.raises(OSError):
        service._sysctl_uint("vm.no_such_counter")


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

    from gear_optimizer.gamedata import read_gears, read_minis

    # The strict typed readers accept the service's rows (custom minis leave the level-1 block blank).
    gear = read_gears(work / "Gears.csv")["Test Hat"]
    mini = read_minis(work / "Minis.csv")["Test Mini"]
    assert (gear.slot, gear.stats["Chill"], gear.stats["Perfect Points"]) == ("Hat", 30, 20)
    assert (mini.element, mini.stats["Chill"], mini.stats["Combo Multiplier"]) == ("Chill", 90, 30)
    # The repeated L1 ascension columns in Minis.csv must stay empty for a custom mini.
    assert mini.level1_elements == {} and mini.song_targets == frozenset()
    assert ((catalog / "Gears.csv").read_bytes(), (catalog / "Minis.csv").read_bytes()) == before


def test_a_custom_pool_on_an_official_chart_is_solved_warm_with_its_own_catalog_copy(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    shutil.copytree(Path(service.__file__).resolve().parents[1] / "Data" / "Gear", data_root / "Data" / "Gear")
    seen: dict[str, object] = {}

    class FakeWorker:
        def request(self, payload):
            from gear_optimizer.gamedata import read_gears, read_minis

            gear_dir = Path(payload["gearDir"])
            seen.update(dir=gear_dir, gear=read_gears(gear_dir / "Gears.csv"), minis=read_minis(gear_dir / "Minis.csv"))
            return [{"loadout_hash": "custom", "score": 1}]

    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_PERSISTENT_SOLVER", "1")
    monkeypatch.setattr(service, "_get_persistent_solve_worker", lambda: FakeWorker())
    from gear_optimizer.gamedata import read_gears

    excluded = next(iter(read_gears(data_root / "Data" / "Gear" / "Gears.csv")))
    result = service.solve(
        {
            "jobId": "custom_pool_warm",
            "targetSongId": "Feeding [Hard]",
            "customGear": [_CUSTOM_GEAR],
            "customMinis": [_CUSTOM_MINI],
            "excludeGear": [excluded],
        }
    )

    assert result == [{"loadout_hash": "custom", "score": 1}]
    assert "Test Hat" in seen["gear"] and "Test Mini" in seen["minis"] and excluded not in seen["gear"]
    assert not Path(seen["dir"]).exists()  # the request's catalog copy goes with the request


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
    from gear_optimizer.gamedata import read_gears, read_minis

    catalog = Path(service.__file__).resolve().parents[1] / "Data" / "Gear"
    before = (catalog / "Gears.csv").read_bytes(), (catalog / "Minis.csv").read_bytes()
    gears_before = read_gears(catalog / "Gears.csv")
    minis_before = read_minis(catalog / "Minis.csv")
    drop_gear = list(gears_before)[:3]
    drop_mini = list(minis_before)[:2]

    work = tmp_path / "Gear"
    shutil.copytree(catalog, work)
    pool = service._custom_pool_for_request(
        {"customGear": [_CUSTOM_GEAR], "excludeGear": drop_gear, "excludeMinis": drop_mini}
    )
    service._remove_excluded_rows(work, pool)
    service._append_custom_pool_rows(work, pool)

    gears_after = read_gears(work / "Gears.csv")
    minis_after = read_minis(work / "Minis.csv")
    assert set(gears_after).isdisjoint(drop_gear)
    assert set(minis_after).isdisjoint(drop_mini)
    # exactly the excluded rows left, and the custom one arrived
    assert len(gears_after) == len(gears_before) - len(drop_gear) + 1
    assert len(minis_after) == len(minis_before) - len(drop_mini)
    assert _CUSTOM_GEAR["name"] in gears_after
    assert ((catalog / "Gears.csv").read_bytes(), (catalog / "Minis.csv").read_bytes()) == before


def test_excluding_an_unknown_name_is_a_no_op(tmp_path):
    from gear_optimizer.gamedata import read_gears

    catalog = Path(service.__file__).resolve().parents[1] / "Data" / "Gear"
    work = tmp_path / "Gear"
    shutil.copytree(catalog, work)
    pool = service._custom_pool_for_request({"excludeGear": ["No Such Gear At All"]})
    service._remove_excluded_rows(work, pool)
    # A stale exclusion (catalog moved on) must not fail the solve or drop anything.
    assert len(read_gears(work / "Gears.csv")) == len(read_gears(catalog / "Gears.csv"))


def test_same_job_different_inputs_own_separate_workspaces(data_root, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    runs = data_root / "runs"
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(runs))
    monkeypatch.setattr(service, "_SOLVE_SEMAPHORE", threading.Semaphore(2))
    monkeypatch.setattr(service, "_acquire_solve_slot", lambda: None)
    monkeypatch.setattr(service, "_release_solve_slot", lambda: None)
    first_started = threading.Event()
    both_started = threading.Barrier(2, timeout=5)
    paths = []

    class Process:
        returncode = 0

        def __init__(self, _cmd, **kwargs):
            self.work = Path(kwargs["env"]["EVOLUTION_DB_PATH"]).parent
            self.chart = self.work / "Data" / "Hard" / "same.txt"
            self.original = self.chart.read_text()
            paths.append(self.work)
            first_started.set()

        def communicate(self, timeout=None):
            both_started.wait()
            assert self.chart.read_text() == self.original
            return "", ""

    monkeypatch.setattr(service.subprocess, "Popen", Process)
    monkeypatch.setattr(service.legacy, "read_best_loadouts", lambda *a, **kw: [{"score": 1}])
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service.solve, {"jobId": "same", "chartText": "Song Data\n500\t0\t0\t1\n"})
        assert first_started.wait(5)
        second = pool.submit(service.solve, {"jobId": "same", "chartText": "Song Data\n750\t0\t0\t1\n"})
        assert first.result(timeout=10) == [{"score": 1}]
        assert second.result(timeout=10) == [{"score": 1}]
    assert len(set(paths)) == 2
    assert all(path.parent == runs and not path.exists() for path in paths)


def test_isolated_workspace_cleanup_includes_preparation_failure(data_root, monkeypatch):
    runs = data_root / "runs"
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(runs))

    def fail_copy(*args, **kwargs):
        raise OSError("catalog unavailable")

    monkeypatch.setattr(service.shutil, "copytree", fail_copy)
    with pytest.raises(OSError, match="catalog unavailable"):
        service._solve_isolated("job", "Song Data\n500\t0\t0\t1\n", "song", 1)
    assert not list(runs.iterdir())


@pytest.mark.parametrize(
    "exit_code, entries, message",
    [
        (1, [{"score": 1}], "optimizer exited 1"),
        (0, [], "optimizer produced no T5 loadout"),
    ],
)
def test_failed_solve_never_publishes_plausible_results(data_root, monkeypatch, exit_code, entries, message):
    from unittest.mock import Mock

    _write_chart(data_root, "Hard", "Official")
    gear = data_root / "Data" / "Gear"
    gear.mkdir(parents=True)
    (gear / "Gears.csv").write_text("name\n", encoding="utf-8")
    runs = data_root / "runs"
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(runs))
    publish = Mock()
    monkeypatch.setattr(service.db, "promote", publish)
    monkeypatch.setattr(service.legacy, "read_best_loadouts", lambda *a, **kw: entries)

    class Process:
        returncode = exit_code

        def __init__(self, *args, **kwargs):
            pass

        def communicate(self, timeout=None):
            return "", "GPU execution failed"

    monkeypatch.setattr(service.subprocess, "Popen", Process)
    with pytest.raises(RuntimeError, match=message):
        service.solve({"jobId": "failure", "targetSongId": "Official"})
    publish.assert_not_called()
    assert not list(runs.iterdir())


def _write_export(data_root: Path, *songs: tuple[int, str, str]) -> None:
    payload = {
        "songs": {
            "1": {
                "songs": [
                    {"songid": song_id, "displayname": displayname, "artist": artist}
                    for song_id, displayname, artist in songs
                ]
            }
        }
    }
    (data_root / "Data" / "exported_game_data.json").write_text(json.dumps(payload), encoding="utf-8")


def test_catalog_build_solves_described_official_charts_missing_from_the_catalog(data_root, monkeypatch):
    from gear_optimizer.store import db, schema

    _write_chart(data_root, "Normal", "Built by Artist", "built.txt")
    _write_chart(data_root, "Hard", "New (Hard) by Artist", "new.txt")
    _write_chart(data_root, "Normal", "Unreleased by Artist", "unreleased.txt")
    _write_export(data_root, (1, "Built", "Artist"), (2, "New (Hard)", "Artist"))
    db_path = data_root / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    conn = schema.connect(db_path, write=True)
    db.store_results(conn, "Built by Artist", "T5", [])  # a processed song
    conn.close()
    solved: list[dict[str, object]] = []
    monkeypatch.setattr(service, "solve", lambda request: solved.append(request) or [])
    service._AUTHORITATIVE_PUBLICATION_READY.set()

    service.build_missing_catalog_songs()

    # Only the chart the game data describes and the catalog lacks, as a clean official request
    # (default non-precise timing, no custom pool) so its result is promoted into the catalog.
    assert solved == [{"jobId": solved[0]["jobId"], "targetSongId": "New (Hard) by Artist"}]


def test_catalog_build_continues_past_a_failed_chart_and_yields_to_a_code_update(data_root, monkeypatch):
    for name in ("A by Artist", "B by Artist", "C by Artist"):
        _write_chart(data_root, "Normal", name, f"{name}.txt")
    _write_export(data_root, (1, "A", "Artist"), (2, "B", "Artist"), (3, "C", "Artist"))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(data_root / "missing.db"))
    attempted: list[str] = []

    def solve(request):
        attempted.append(request["targetSongId"])
        if request["targetSongId"] == "A by Artist":
            raise RuntimeError("optimizer exited 1")
        service._AUTHORITATIVE_PUBLICATION_READY.clear()  # a code update starts draining
        return []

    monkeypatch.setattr(service, "solve", solve)
    service._AUTHORITATIVE_PUBLICATION_READY.set()

    service.build_missing_catalog_songs()

    assert attempted == ["A by Artist", "B by Artist"]


def test_persistent_worker_restarts_when_a_new_catalog_activates(data_root, monkeypatch):
    first = data_root / "first" / "Gear"
    second = data_root / "second" / "Gear"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    spawned: list[Path] = []

    class _SolverProcess:
        def __init__(self, *_args, **_kwargs):
            spawned.append(service.GEAR_DIR)
            self._lines: queue.Queue[str | None] = queue.Queue()
            self.stdin = self
            self.stdout = self
            self.stderr = io.StringIO()

        def __iter__(self):
            return iter(self._lines.get, None)

        def write(self, _payload):
            self._lines.put('{"ok": true, "loadouts": []}\n')

        def flush(self):
            pass

        def poll(self):
            return None

        def wait(self, timeout=None):
            return 0

        def close(self):
            self._lines.put(None)

    monkeypatch.setattr(service.subprocess, "Popen", _SolverProcess)
    monkeypatch.setattr(service, "_kill_process_group", lambda _proc: None)
    worker = service._PersistentSolveWorker()
    try:
        for gear_dir in (first, first, second):
            monkeypatch.setattr(service, "GEAR_DIR", gear_dir)
            assert worker.request({"jobId": "job"}) == []
    finally:
        worker.stop()

    assert spawned == [first, second]


def test_incremental_frontier_prebuild_queues_only_the_changed_charts(data_root, monkeypatch):
    from gear_optimizer import gamedata
    from gear_optimizer.solver import cpu_work_manager
    from gear_optimizer.solver.frontier_cache import ordered_frontier_cache_song_paths

    _write_chart(data_root, "Normal", "Old by Artist", "old.txt")
    _write_chart(data_root, "Normal", "New by Artist", "new.txt")
    changed = data_root / "Data" / "Normal" / "new.txt"
    monkeypatch.setattr(gamedata, "load_stat_curves", lambda _path: object())
    queued: list[object] = []

    class _Stop(Exception):
        pass

    def capture(**kwargs):
        queued.append(kwargs["song_queue"])
        raise _Stop

    monkeypatch.setattr(cpu_work_manager, "run_startup_cpu_work", capture)

    with pytest.raises(_Stop):
        service._prebuild_frontier_caches(data_root / "Data", (changed,))

    # The prebuild reads the chart path from each queue tuple; anything else falls back to
    # every chart under Data/.
    queue_paths = [str(item[0]) for item in queued[0] if isinstance(item, tuple) and item]
    assert ordered_frontier_cache_song_paths(queue_paths=queue_paths, data_root=data_root / "Data") == [str(changed)]


class _InlineExecutor:
    """ProcessPoolExecutor stand-in that runs the child body synchronously."""

    created: list[dict[str, object]] = []

    def __init__(self, **kwargs):
        _InlineExecutor.created.append(kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def submit(self, fn, *args):
        future: concurrent.futures.Future = concurrent.futures.Future()
        try:
            future.set_result(fn(*args))
        except BaseException as exc:  # noqa: BLE001 - mirror a child failure into the future
            future.set_exception(exc)
        return future


class _ActivePublication:
    def __init__(self, body: bytes | None):
        self._body = body

    def manifest_bytes(self) -> bytes | None:
        return self._body


_ACTIVE_MANIFEST = json.dumps(
    {"bundles": [{"files": [{"scope": "timeline", "path": "c.npz"}, {"scope": "fg", "path": "d.npz"}]}]}
).encode("utf-8")


def test_isolated_prebuild_merges_active_publication_in_parent(tmp_path, monkeypatch):
    child_calls: list[tuple[object, ...]] = []

    def child_body(data_root, changed_charts):
        child_calls.append((data_root, changed_charts))
        return {"timeline": {"a.npz"}, "fg": {"b.npz"}}

    _InlineExecutor.created.clear()
    monkeypatch.setattr(service.concurrent.futures, "ProcessPoolExecutor", _InlineExecutor)
    monkeypatch.setattr(service, "_prebuild_frontier_caches", child_body)
    monkeypatch.setattr(service, "_FRONTIER_DISTRIBUTION", _ActivePublication(_ACTIVE_MANIFEST))
    changed = tmp_path / "Data" / "Normal" / "new.txt"

    incremental = service._prebuild_frontier_caches_isolated(tmp_path / "Data", [changed])
    full = service._prebuild_frontier_caches_isolated(tmp_path / "Data", None)

    assert incremental == {"timeline": {"a.npz", "c.npz"}, "fg": {"b.npz", "d.npz"}}
    assert full == {"timeline": {"a.npz"}, "fg": {"b.npz"}}
    assert child_calls == [(tmp_path / "Data", (changed,)), (tmp_path / "Data", None)]
    assert [(kw["max_workers"], kw["mp_context"].get_start_method()) for kw in _InlineExecutor.created] == [
        (1, "spawn"),
        (1, "spawn"),
    ]


def test_isolated_prebuild_propagates_child_failure(tmp_path, monkeypatch):
    def child_body(_data_root, _changed_charts):
        raise RuntimeError("frontier prebuild failed in the child")

    monkeypatch.setattr(service.concurrent.futures, "ProcessPoolExecutor", _InlineExecutor)
    monkeypatch.setattr(service, "_prebuild_frontier_caches", child_body)
    monkeypatch.setattr(service, "_FRONTIER_DISTRIBUTION", _ActivePublication(_ACTIVE_MANIFEST))

    with pytest.raises(RuntimeError, match="failed in the child"):
        service._prebuild_frontier_caches_isolated(tmp_path / "Data", None)


def test_isolated_prebuild_requires_active_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(service.concurrent.futures, "ProcessPoolExecutor", _InlineExecutor)
    monkeypatch.setattr(
        service,
        "_prebuild_frontier_caches",
        lambda *_args: {"timeline": {"a.npz"}, "fg": {"b.npz"}},
    )
    monkeypatch.setattr(service, "_FRONTIER_DISTRIBUTION", _ActivePublication(None))

    with pytest.raises(RuntimeError, match="requires the active complete publication"):
        service._prebuild_frontier_caches_isolated(tmp_path / "Data", (tmp_path / "Data" / "Normal" / "new.txt",))
