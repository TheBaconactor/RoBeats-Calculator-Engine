"""The service through its request entry points. `worker` fakes the solve process; test_service_worker_protocol runs a
real one."""

from __future__ import annotations

import io
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

from gear_optimizer import robeatsmeta_service as service
from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.settings import paths


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


def _write_export(root: Path, *songs: tuple[int, str, str]) -> None:
    gear = {"name": "Catalog Hat", "slot": 3, "stats": {
        "ColorBlue": 1, "ColorPurple": 0, "ColorRed": 0, "ColorOrange": 0, "ColorGreen": 0, "PerfectPoints": 0,
        "ComboMultiplier": 0, "FeverMultiplier": 0, "FeverTime": 0, "FeverFillRate": 0, "PerfectTime": 0,
    }}
    mini = {"name": "Catalog Mini", "stats": {
        "ColorBlue": 1, "ColorPurple": 0, "ColorRed": 0, "ColorOrange": 0, "ColorGreen": 0, "ComboMultiplier": 0,
        "FeverMultiplier": 0, "FeverTime": 0, "FeverFillRate": 0,
    }}
    (root / "Data").mkdir(exist_ok=True)
    (root / "Data" / "exported_game_data.json").write_text(json.dumps({
        "gears": {"1": {"gears": [gear]}},
        "minis": {"1": {"minis": [mini]}},
        "songs": {"1": {"songs": [{"songid": i, "displayname": title, "artist": artist} for i, title, artist in songs]}},
    }), encoding="utf-8")


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", raising=False)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path / "Data"))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "evolution.db"))
    service.clear_official_charts()
    yield tmp_path
    service.clear_official_charts()


@pytest.fixture
def worker(monkeypatch):
    """Every solve-process request, with the worker that took it; each answers one loadout."""
    requests: list[dict] = []

    def request(self, payload):
        requests.append({**payload, "worker": self})
        return [{"loadout_hash": "h"}]

    monkeypatch.setattr(service._SolveWorker, "request", request)
    monkeypatch.setattr(service._SolveWorker, "stop", lambda self: None)
    return requests


def test_list_official_songs_reads_headers(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    songs = {s["songId"]: s for s in service.list_official_songs()}
    assert songs["Canon in D [Normal]"]["difficulty"] == "Normal"
    assert songs["Canon in D [Normal]"]["primaryElement"] == "Beat"
    assert songs["Feeding [Hard]"]["difficulty"] == "Hard"


def test_a_title_loses_its_difficulty_suffix(data_root):
    folder = data_root / "Data" / "Hard"
    folder.mkdir(parents=True)
    (folder / "song.txt").write_text("Song Name\tSong\nTitle\tSong (Hard)\nSong Data\n", encoding="utf-8")
    assert service.list_official_songs()[0]["title"] == "Song"


def test_an_unreadable_chart_stays_out_of_the_list(data_root):
    _write_chart(data_root, "Normal", "Good")
    (data_root / "Data" / "Normal" / "bad.txt").write_text("no tab\n", encoding="utf-8")
    assert [song["songId"] for song in service.list_official_songs()] == ["Good"]


def test_the_list_comes_from_a_configured_library(data_root, monkeypatch):
    library = data_root / "Library"
    for difficulty in ("Easy", "Normal", "Hard"):
        (library / f"{difficulty} Songs").mkdir(parents=True)
    (library / "Normal Songs" / "chart.txt").write_text("Song Name\tLibrary Chart\nSong Data\n", encoding="utf-8")
    _write_chart(data_root, "Normal", "Private Calculator Chart")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", str(library))

    assert [song["songId"] for song in service.list_official_songs()] == ["Library Chart"]
    assert service.find_official_chart("Library Chart").parent == library / "Normal Songs"
    with pytest.raises(service.RequestError):
        service.find_official_chart("Private Calculator Chart")


def test_a_configured_library_needs_every_difficulty(data_root, monkeypatch):
    library = data_root / "Library"
    (library / "Hard Songs").mkdir(parents=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR", str(library))
    with pytest.raises(RuntimeError, match="Easy Songs.*Normal Songs"):
        service.list_official_songs()


def test_find_official_chart_is_an_exact_match(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    assert service.find_official_chart("Canon in D [Normal]").name == "song.txt"
    with pytest.raises(service.RequestError):
        service.find_official_chart("Canon in D")


def test_a_refresh_rereads_the_charts_and_wakes_the_updater(data_root, monkeypatch):
    _write_chart(data_root, "Normal", "First")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_API_TOKEN", "secret")
    calls: list[object] = []
    handler = service.RoBeatsMetaServiceHandler.__new__(service.RoBeatsMetaServiceHandler)
    handler.path = "/frontiers/refresh"
    handler.headers = {"Authorization": "Bearer secret"}
    handler.server = type("Server", (), {"updater": type("U", (), {"request_check": lambda _: calls.append("wake")})()})()
    monkeypatch.setattr(handler, "_send", lambda status, payload: calls.append((status, payload)))

    assert len(service.list_official_songs()) == 1
    _write_chart(data_root, "Normal", "Second", "second.txt")
    # Requests never stat the library: the chart appears once the publisher's refresh arrives.
    assert len(service.list_official_songs()) == 1

    handler.do_POST()

    assert calls == ["wake", (service.HTTPStatus.ACCEPTED, {"queued": True})]
    assert len(service.list_official_songs()) == 2


def test_requests_need_the_token(data_root, monkeypatch):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_API_TOKEN", "secret")
    statuses: list[object] = []
    handler = service.RoBeatsMetaServiceHandler.__new__(service.RoBeatsMetaServiceHandler)
    handler.headers = {"Authorization": "Bearer wrong"}
    monkeypatch.setattr(handler, "_send", lambda status, _payload: statuses.append(status))
    for handle, path in ((handler.do_GET, "/songs"), (handler.do_POST, "/optimize"), (handler.do_POST, "/frontiers/refresh")):
        handler.path = path
        handle()
    assert statuses == [service.HTTPStatus.UNAUTHORIZED] * 3


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
    updater_callbacks: dict[str, object] = {}
    executed: dict[str, object] = {}

    class _Server:
        daemon_threads = False

        def __init__(self, *_args, **_kwargs):
            self.socket = listener

        def serve_forever(self):
            updater_callbacks["restart"]("abc123def4567890")

        def shutdown(self):
            calls.append("shutdown")

        def server_close(self):
            calls.append("close")

    class _Thread:
        def __init__(self, *, target, **_kwargs):
            self._target = target

        def start(self):
            self._target()

    class _Updater:
        def __init__(self, _repo_root, **kwargs):
            updater_callbacks.update(kwargs)

        def serve_forever(self):
            pass

        def stop(self):
            calls.append("stop")

    monkeypatch.delenv(service._LISTENER_FD_ENV, raising=False)
    monkeypatch.setattr(service, "ThreadingHTTPServer", _Server)
    monkeypatch.setattr(service.threading, "Thread", _Thread)
    monkeypatch.setattr(service, "ServiceUpdater", _Updater)
    monkeypatch.setattr(service._warm_worker, "stop", lambda: calls.append("worker"))
    monkeypatch.setattr(
        service.os, "execv", lambda _exe, args: executed.update(args=args, fd=os.environ[service._LISTENER_FD_ENV])
    )
    try:
        service.main(["--host", "127.0.0.1", "--port", "0"])
        assert calls == ["shutdown", "worker", "stop"]  # the listening socket stays open across the exec
        assert executed["fd"] == str(listener.fileno()) and listener.get_inheritable()
        assert executed["args"][1:3] == ["-m", "gear_optimizer.robeatsmeta_service"]
    finally:
        os.environ.pop(service._LISTENER_FD_ENV, None)
        listener.close()


def test_an_official_request_keeps_its_song_identity(data_root):
    _write_chart(data_root, "Normal", "Canon in D [Normal]")
    request = service.parse_request({"jobId": "job/1", "targetSongId": "Canon in D [Normal]", "timingMode": PRECISE})
    assert (request.job, request.song_name, request.uploaded, request.promotes) == ("job_1", "Canon in D [Normal]", False, True)
    assert "Song Name\tCanon in D [Normal]\n" in request.chart_text
    assert "Timing Mode\tprecise\n" in request.chart_text
    assert "Difficulty\tNormal\n" in request.chart_text  # the timeline cache key reads it


def test_an_uploaded_chart_takes_the_job_as_its_name_and_never_promotes():
    request = service.parse_request({"jobId": "job", "chartText": "Song Name\tMine\nSong Data\n1000\t0\t0\t1\n"})
    assert (request.song_name, request.uploaded, request.promotes) == ("job", True, False)
    assert request.chart_text.splitlines()[:2] == ["Timing Mode\tnon-precise", "Song Name\tjob"]


def test_the_solve_headers_come_first_when_a_chart_lacks_them():
    request = service.parse_request({"jobId": "job", "chartText": "Title\tMine\nSong Data\n1000\t0\t0\t1\n"})
    assert request.chart_text.splitlines()[:3] == ["Song Name\tjob", "Timing Mode\tnon-precise", "Title\tMine"]


@pytest.mark.parametrize("request_payload", [
    pytest.param({}, id="no-chart"),
    pytest.param({"targetSongId": "Not A Real Song"}, id="unknown-song"),
    pytest.param({"chartText": "Song Name\tMine\n"}, id="no-song-data"),
    pytest.param({"chartText": "Song Data\n" + "1000\t0\t0\t1\n" * 4001}, id="too-many-events"),
    pytest.param({"chartText": "Song Data\n", "timingMode": "zero_ms"}, id="unknown-timing-mode"),
    pytest.param({"chartText": "Song Data\n", "reasoning": "extreme"}, id="unknown-reasoning"),
])
def test_a_bad_request_is_refused(data_root, request_payload):
    with pytest.raises(service.RequestError):
        service.parse_request(request_payload)


@pytest.mark.parametrize("value", ["..", "...", "", None])
def test_a_job_id_cannot_climb_out_of_the_run_root(value):
    assert service._job_slug(value) == "job"


def test_a_clean_official_solve_runs_warm_and_promotes(data_root, worker):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    assert service.solve({"jobId": "job", "targetSongId": "Feeding [Hard]", "reasoning": "strong"}) == [{"loadout_hash": "h"}]
    (request,) = worker
    assert request["worker"] is service._warm_worker
    assert request["promoteTo"] == str(paths().database)
    assert (request["songName"], request["reasoning"], request["uploaded"]) == ("Feeding [Hard]", "strong", False)


def test_a_custom_pool_runs_warm_and_never_promotes(data_root, worker):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    service.solve({"jobId": "job", "targetSongId": "Feeding [Hard]", "excludeGear": ["Some Hat"]})
    (request,) = worker
    assert request["worker"] is service._warm_worker
    assert request["promoteTo"] is None
    assert request["customPool"]["excludeGear"] == ["Some Hat"]


def test_an_uploaded_chart_gets_its_own_worker_and_throwaway_frontiers(data_root, worker):
    service.solve({"jobId": "job", "chartText": "Song Data\n1000\t0\t0\t1\n"})
    (request,) = worker
    own = request["worker"]
    assert own is not service._warm_worker
    assert own._frontier_root == own._root and own._root.parent == data_root / "runs"
    assert request["promoteTo"] is None and request["uploaded"] is True
    assert not own._root.exists()


def test_a_failed_upload_leaves_no_workspace(data_root, monkeypatch):
    def fail(_self, _payload):
        raise RuntimeError("no T5")

    monkeypatch.setattr(service._SolveWorker, "request", fail)
    with pytest.raises(RuntimeError, match="no T5"):
        service.solve({"jobId": "job", "chartText": "Song Data\n1000\t0\t0\t1\n"})
    assert list((data_root / "runs").iterdir()) == []


def _hold_solves(monkeypatch) -> tuple[threading.Event, threading.Event, list[dict]]:
    started, release = threading.Event(), threading.Event()
    requests: list[dict] = []

    def request(_self, payload):
        requests.append(payload)
        started.set()
        assert release.wait(timeout=5.0)
        if payload["reasoning"] == "max":
            raise RuntimeError("solve failed")
        return [{"reasoning": payload["reasoning"]}]

    monkeypatch.setattr(service._SolveWorker, "request", request)
    return started, release, requests


def test_a_retry_joins_the_running_job(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    started, release, requests = _hold_solves(monkeypatch)
    results: list[object] = []

    def call() -> None:
        results.append(service.solve({"jobId": "job", "targetSongId": "Feeding [Hard]"}))

    threads = [threading.Thread(target=call) for _ in range(2)]
    threads[0].start()
    assert started.wait(timeout=5.0)
    threads[1].start()
    while len(service._in_flight) != 1:  # pragma: no cover - the owner registered before it started
        time.sleep(0.01)
    time.sleep(0.05)
    release.set()
    for thread in threads:
        thread.join(timeout=5.0)
    assert results == [[{"reasoning": "default"}]] * 2
    assert len(requests) == 1 and service._in_flight == {}


def test_a_joined_failure_reaches_both_callers(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    started, release, _requests = _hold_solves(monkeypatch)
    errors: list[str] = []

    def call() -> None:
        try:
            service.solve({"jobId": "job", "targetSongId": "Feeding [Hard]", "reasoning": "max"})
        except RuntimeError as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=call) for _ in range(2)]
    threads[0].start()
    assert started.wait(timeout=5.0)
    threads[1].start()
    time.sleep(0.05)
    release.set()
    for thread in threads:
        thread.join(timeout=5.0)
    assert errors == ["solve failed", "solve failed"]


def test_the_same_job_with_other_inputs_solves_apart(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    _started, release, requests = _hold_solves(monkeypatch)
    release.set()
    for reasoning in ("default", "strong"):
        service.solve({"jobId": "job", "targetSongId": "Feeding [Hard]", "reasoning": reasoning})
    assert [request["reasoning"] for request in requests] == ["default", "strong"]


def test_a_draining_service_refuses_new_solves(data_root, worker):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    service._drain_solves()
    try:
        with pytest.raises(service.ServiceNotReady):
            service.solve({"jobId": "job", "targetSongId": "Feeding [Hard]"})
    finally:
        service._resume_solves()
    assert service.solve({"jobId": "job", "targetSongId": "Feeding [Hard]"}) == [{"loadout_hash": "h"}]


def test_a_drain_waits_for_running_solves(monkeypatch):
    finished: list[str] = []
    entered, release = threading.Event(), threading.Event()

    def solve() -> None:
        with service._solve_slot():
            entered.set()
            assert release.wait(timeout=5.0)
            finished.append("solve")

    thread = threading.Thread(target=solve)
    thread.start()
    assert entered.wait(timeout=5.0)
    threading.Timer(0.05, release.set).start()
    service._drain_solves()
    finished.append("drained")
    service._resume_solves()
    thread.join(timeout=5.0)
    assert finished == ["solve", "drained"]


def test_read_json_rejects_an_oversize_body():
    handler = service.RoBeatsMetaServiceHandler.__new__(service.RoBeatsMetaServiceHandler)
    handler.headers = {"Content-Length": str(service.service_settings().max_body_bytes + 1)}
    handler.rfile = io.BytesIO()
    with pytest.raises(service.RequestTooLarge):
        handler._read_json()


def _peak_concurrent_slots(workers: int, available: int, min_free: int, monkeypatch) -> int:
    """Drive N threads through the memory gate and return the peak simultaneous slots."""
    monkeypatch.setattr(service, "_MIN_FREE_BYTES", min_free)
    monkeypatch.setattr(service, "_available_bytes", lambda: available)
    peak = {"n": 0}
    peak_lock = threading.Lock()
    start = threading.Barrier(workers)

    def worker() -> None:
        start.wait()  # release together to maximize contention
        with service._solve_slot():
            with peak_lock:
                peak["n"] = max(peak["n"], service._active_solves)
            time.sleep(0.05)  # hold the slot so overlap is observable

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return peak["n"]


def test_low_memory_runs_one_solve_at_a_time(monkeypatch):
    assert _peak_concurrent_slots(workers=4, available=0, min_free=8 << 30, monkeypatch=monkeypatch) == 1


def test_ample_memory_lets_solves_overlap(monkeypatch):
    assert _peak_concurrent_slots(workers=4, available=64 << 30, min_free=1, monkeypatch=monkeypatch) == 4


def test_available_bytes_on_macos_counts_only_what_frees_without_compressing(monkeypatch):
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


@pytest.mark.skipif(sys.platform != "darwin", reason="reads macOS VM counters")
def test_sysctl_uint_reads_real_counters():
    assert service._sysctl_uint("vm.page_free_count") > 0  # a 4-byte counter
    assert service._sysctl_uint("hw.pagesize") > 0  # an 8-byte value
    with pytest.raises(OSError):
        service._sysctl_uint("vm.no_such_counter")


_CUSTOM_GEAR = {"name": "Test Hat", "type": "Hat", "chill": 30, "ppoint": 20}
_CUSTOM_MINI = {"name": "Test Mini", "type": "Chill", "chill": 90, "cbmlt": 30}
_SONG = {"chartText": "Song Data\n"}


@pytest.mark.parametrize("request_payload", [
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, name=f"Hat {i}") for i in range(16)]}, id="over-item-cap"),
    pytest.param({"customMinis": [dict(_CUSTOM_MINI, name=f"Mini {i}") for i in range(16)]}, id="over-mini-cap"),
    pytest.param({"customGear": {"name": "Hat"}}, id="not-a-list"),
    pytest.param({"customGear": ["Hat"]}, id="item-not-an-object"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, name='a,b"\nHat')]}, id="hostile-name"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, name="=1+1")]}, id="formula-injection-name"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, name="x" * 33)]}, id="name-too-long"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, type="Wings")]}, id="unknown-slot"),
    pytest.param({"customMinis": [dict(_CUSTOM_MINI, type="Sparkle")]}, id="unknown-mini-type"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, chill=-1)]}, id="negative-stat"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, chill=10**9)]}, id="stat-out-of-range"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, chill="30")]}, id="stat-not-an-int"),
    pytest.param({"customGear": [dict(_CUSTOM_GEAR, chill=True)]}, id="stat-a-bool"),
    pytest.param({"customGear": [_CUSTOM_GEAR, dict(_CUSTOM_GEAR, type="Face")]}, id="duplicate-name"),
    pytest.param({"excludeGear": "Hat"}, id="exclude-not-a-list"),
    pytest.param({"excludeGear": [123]}, id="exclude-not-a-string"),
    pytest.param({"excludeGear": ["a\nb"]}, id="exclude-newline-in-name"),
    pytest.param({"excludeGear": ['a"b']}, id="exclude-quote-in-name"),
    pytest.param({"excludeGear": ["x" * 65]}, id="exclude-name-too-long"),
    pytest.param({"excludeGear": [f"Hat {i}" for i in range(401)]}, id="exclude-over-gear-cap"),
    pytest.param({"excludeMinis": [f"Mini {i}" for i in range(201)]}, id="exclude-over-mini-cap"),
])
def test_an_invalid_custom_pool_is_refused(request_payload):
    with pytest.raises(service.RequestError):
        service.parse_request(_SONG | request_payload)


def test_custom_pool_accepts_fifteen_items_of_each_kind():
    request = service.parse_request(_SONG | {
        "customGear": [dict(_CUSTOM_GEAR, name=f"Hat {i}") for i in range(15)],
        "customMinis": [dict(_CUSTOM_MINI, name=f"Mini {i}") for i in range(15)],
    })
    assert len(request.custom_pool["customGear"]) == 15
    assert len(request.custom_pool["customMinis"]) == 15


def test_excluded_names_accept_real_catalog_names_with_punctuation():
    # Real names carry characters a user may not invent ("(The) Red * Room", commas, unicode).
    pool = service.parse_request(_SONG | {
        "excludeGear": ["Juggernaut's Goggles", "  "], "excludeMinis": ["(The) Red * Room", "t+pazolite"],
    }).custom_pool
    assert pool["excludeGear"] == ["Juggernaut's Goggles"]
    assert pool["excludeMinis"] == ["(The) Red * Room", "t+pazolite"]


def test_a_custom_item_cannot_redefine_a_catalog_item_that_stays(data_root):
    _write_export(data_root)
    for field, item in (("customGear", _CUSTOM_GEAR | {"name": "CATALOG hat"}), ("customMinis", _CUSTOM_MINI | {"name": "catalog mini"})):
        with pytest.raises(service.RequestError, match="taken"):
            service.parse_request(_SONG | {field: [item]})
    pool = service.parse_request(_SONG | {
        "customGear": [_CUSTOM_GEAR | {"name": "Catalog Hat"}], "excludeGear": ["catalog hat"],
    }).custom_pool
    assert [item["name"] for item in pool["customGear"]] == ["Catalog Hat"]
    assert list(load_catalog(paths().game_export).gears) == ["Catalog Hat"]


def _store_catalog(data_root: Path, *songs: str) -> None:
    from gear_optimizer.store import db, schema

    schema.ensure(data_root / "evolution.db")
    conn = schema.connect(data_root / "evolution.db", write=True)
    for song in songs:
        for mode in ("non-precise", "precise"):
            db.store_results(conn, mode, song, "T5", [])
    conn.close()


def test_a_catalog_pass_solves_the_described_charts_the_catalog_lacks(data_root, monkeypatch):
    _write_chart(data_root, "Normal", "Built by Artist", "built.txt")
    _write_chart(data_root, "Hard", "New (Hard) by Artist", "new.txt")
    _write_chart(data_root, "Normal", "Unreleased by Artist", "unreleased.txt")
    _write_export(data_root, (1, "Built", "Artist"), (2, "New (Hard)", "Artist"))
    _store_catalog(data_root, "Built by Artist")
    solved: list[dict] = []
    monkeypatch.setattr(service, "solve", lambda request: solved.append(request) or [])

    service.build_missing_catalog_songs()

    # As clean official requests (no custom pool), so their results are promoted into the catalog.
    assert [(r["targetSongId"], r["timingMode"]) for r in solved] == [
        ("New (Hard) by Artist", "non-precise"),
        ("New (Hard) by Artist", "precise"),
    ]
    assert all(set(r) == {"jobId", "targetSongId", "timingMode"} for r in solved)
    assert len({r["jobId"] for r in solved}) == 2


def test_a_catalog_pass_with_nothing_to_build_warms_the_solver_without_promoting(data_root, worker):
    _write_chart(data_root, "Normal", "B by Artist", "b.txt")
    _write_chart(data_root, "Hard", "A (Hard) by Artist", "a.txt")
    _write_export(data_root, (1, "B", "Artist"), (2, "A (Hard)", "Artist"))
    _store_catalog(data_root, "B by Artist", "A (Hard) by Artist")

    service.build_missing_catalog_songs()

    (request,) = worker
    assert request["worker"] is service._warm_worker
    assert request["songName"] == "A (Hard) by Artist"
    assert "Timing Mode\tprecise\n" in request["chartText"]
    assert request["promoteTo"] is None


def test_a_catalog_pass_goes_past_a_failed_chart_and_yields_to_a_drain(data_root, monkeypatch):
    for name in ("A by Artist", "B by Artist", "C by Artist"):
        _write_chart(data_root, "Normal", name, f"{name}.txt")
    _write_export(data_root, (1, "A", "Artist"), (2, "B", "Artist"), (3, "C", "Artist"))
    attempted: list[tuple[str, str]] = []

    def solve(request):
        attempted.append((request["targetSongId"], request["timingMode"]))
        if request["targetSongId"] == "A by Artist":
            raise RuntimeError("no T5")
        raise service.ServiceNotReady("a code update is draining")

    monkeypatch.setattr(service, "solve", solve)

    service.build_missing_catalog_songs()

    assert attempted == [("A by Artist", "non-precise"), ("A by Artist", "precise"), ("B by Artist", "non-precise")]


def test_a_data_refresh_builds_every_chart_in_both_modes_and_rereads_the_list(data_root, monkeypatch):
    from gear_optimizer.frontier import startup_prebuild

    _write_chart(data_root, "Hard", "A")
    _write_chart(data_root, "Easy", "B")
    seen: list[dict] = []

    class _Executor:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def submit(self, task):
            task()
            return type("Done", (), {"result": lambda _: None})()

    monkeypatch.setattr(service, "ProcessPoolExecutor", _Executor)
    monkeypatch.setattr(startup_prebuild, "run_startup_cpu_work", lambda **kwargs: seen.append(kwargs))
    built: list[str] = []
    monkeypatch.setattr(service, "build_missing_catalog_songs", lambda: built.append("pass"))
    assert len(service.list_official_songs()) == 2
    _write_chart(data_root, "Normal", "C")

    service.refresh_data()

    (call,) = seen
    assert call["authorize_destructive_rotation"] is True
    assert {mode: len(charts) for mode, charts in call["charts_by_mode"].items()} == {"precise": 3, "non-precise": 3}
    assert built == ["pass"] and len(service.list_official_songs()) == 3


def _lookup_handler(monkeypatch, body: dict, path: str = "/reverse") -> tuple[service.RoBeatsMetaServiceHandler, list]:
    answers: list = []
    handler = service.RoBeatsMetaServiceHandler.__new__(service.RoBeatsMetaServiceHandler)
    handler.headers = {}
    handler.path = path
    monkeypatch.setattr(handler, "_read_json", lambda: body)
    monkeypatch.setattr(handler, "_send", lambda status, payload: answers.append((status, payload)))
    return handler, answers


def test_a_lookup_takes_its_own_queue_and_no_solve_slot(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    taken: list[dict] = []

    def request(_self, payload):
        taken.append(payload)
        return {"verdict": "sets"}

    monkeypatch.setattr(service._LookupWorker, "request", request)
    monkeypatch.setattr(service, "_solve_slot", lambda: pytest.fail("a lookup waited for a solve slot"))
    handler, answers = _lookup_handler(monkeypatch, {"targetSongId": "Feeding [Hard]", "score": 5, "accuracy": 99.91, "gearPower": 40})
    handler.do_POST()
    assert answers == [(service.HTTPStatus.OK, {"verdict": "sets"})]
    assert taken[0]["score"] == 5
    assert taken[0]["accuracy"] == 99.91
    assert taken[0]["gearPower"] == 40
    assert taken[0]["chartPath"].endswith("song.txt")


def test_a_prepare_readies_the_song_in_the_lookup_queue(data_root, monkeypatch):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    taken: list[dict] = []
    monkeypatch.setattr(service._LookupWorker, "request", lambda _self, payload: taken.append(payload) or {"prepared": True})
    monkeypatch.setattr(service, "_solve_slot", lambda: pytest.fail("a prepare waited for a solve slot"))
    handler, answers = _lookup_handler(monkeypatch, {"targetSongId": "Feeding [Hard]", "accuracy": 99.5}, "/reverse/prepare")
    handler.do_POST()
    assert answers == [(service.HTTPStatus.OK, {"prepared": True})]
    assert taken[0]["prepare"] is True
    assert taken[0]["accuracy"] == 99.5
    assert taken[0]["chartPath"].endswith("song.txt")
    for body in ({"accuracy": 99.5}, {"targetSongId": "Feeding [Hard]", "accuracy": -1}, {"targetSongId": "Unknown [Hard]"}):
        handler, answers = _lookup_handler(monkeypatch, body, "/reverse/prepare")
        handler.do_POST()
        assert answers[0][0] == service.HTTPStatus.BAD_REQUEST


@pytest.mark.parametrize("body", ({"score": 5}, {"targetSongId": "Feeding [Hard]"}, {"targetSongId": "Feeding [Hard]", "score": True}, {"targetSongId": "Feeding [Hard]", "score": 5, "matchMode": "Solo"}, {"targetSongId": "Feeding [Hard]", "score": 5, "accuracy": "all"}, {"targetSongId": "Feeding [Hard]", "score": 5, "teamBuff": "T99"}, {"targetSongId": "Feeding [Hard]", "score": 5, "teamColor": "Pink"}))
def test_a_lookup_with_a_row_no_menu_shows_is_refused(data_root, monkeypatch, body):
    _write_chart(data_root, "Hard", "Feeding [Hard]")
    handler, answers = _lookup_handler(monkeypatch, body)
    handler.do_POST()
    assert answers[0][0] == service.HTTPStatus.BAD_REQUEST


def test_lookups_run_in_arrival_order_and_refuse_past_the_queue(monkeypatch):
    release = threading.Event()
    order: list[int] = []

    class Held:
        def request(self, payload):
            assert release.wait(timeout=5.0)
            order.append(payload["n"])
            return {"n": payload["n"]}

    monkeypatch.setattr(service, "_LOOKUPS_QUEUED", 3)
    lookups = service._LookupQueue(Held())
    threads = []
    for n in range(3):
        threads.append(threading.Thread(target=lookups.lookup, args=({"n": n},)))
        threads[-1].start()
        while lookups._places._value > 2 - n:
            pass
    with pytest.raises(service.ServiceNotReady):
        lookups.lookup({"n": 3})
    release.set()
    for thread in threads:
        thread.join(timeout=5.0)
    assert order == [0, 1, 2]
