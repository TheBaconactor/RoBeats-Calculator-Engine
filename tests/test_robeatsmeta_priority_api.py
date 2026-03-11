import configparser
import json
import sqlite3
import threading
import time

from gear_optimizer.robeatsmeta_api import RoBeatsMetaOptimizerApi, _file_lock


def _write_song_meta_index(path):
    payload = [
        {"id": "Alpha (Hard) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Hard"},
        {"id": "Alpha (Normal) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Normal"},
        {"id": "Alpha (Easy) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Easy"},
        {"id": "Beta (Hard) by Artist", "title": "Beta", "artist": "Artist", "difficulty": "Hard"},
        {"id": "Gamma (Hard) by Artist", "title": "Gamma", "artist": "Artist", "difficulty": "Hard"},
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_prioritize_song_queue_promotes_requested_song_id(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    now = 1_700_000_000
    result = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now,
    )

    assert result["queued"] is True

    song_queue = [
        ("beta.txt", "Beta (Hard) by Artist", "Hard"),
        ("alpha_h.txt", "Alpha (Hard) by Artist", "Hard"),
        ("gamma.txt", "Gamma (Hard) by Artist", "Hard"),
        ("alpha_n.txt", "Alpha (Normal) by Artist", "Normal"),
        ("alpha_e.txt", "Alpha (Easy) by Artist", "Easy"),
    ]

    prioritized = api.prioritize_song_queue(song_queue, now=now + 5)
    assert [item[1] for item in prioritized] == [
        "Alpha (Hard) by Artist",
        "Beta (Hard) by Artist",
        "Gamma (Hard) by Artist",
        "Alpha (Normal) by Artist",
        "Alpha (Easy) by Artist",
    ]


def test_reprioritize_pending_tasks_moves_requested_song_id_to_front(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    now = 1_700_000_100
    api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now,
    )

    tasks = [
        ("beta.txt", "Beta (Hard) by Artist", "Hard"),
        ("gamma.txt", "Gamma (Hard) by Artist", "Hard"),
        ("alpha_h.txt", "Alpha (Hard) by Artist", "Hard"),
        ("alpha_n.txt", "Alpha (Normal) by Artist", "Normal"),
        ("alpha_e.txt", "Alpha (Easy) by Artist", "Easy"),
    ]

    changed = api.reprioritize_pending_tasks(tasks, start_index=1, now=now + 1)

    assert changed is True
    assert [task[1] for task in tasks] == [
        "Beta (Hard) by Artist",
        "Alpha (Hard) by Artist",
        "Gamma (Hard) by Artist",
        "Alpha (Normal) by Artist",
        "Alpha (Easy) by Artist",
    ]

    api.mark_song_computed(song_id="Alpha (Hard) by Artist", now=now + 2)
    second_visit = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now + 3,
    )

    assert second_visit["queued"] is False
    assert second_visit["reason"] == "fresh_compute"


def test_record_song_visit_skips_when_same_song_id_is_already_processing(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    api.mark_song_started(song_id="Alpha (Hard) by Artist (Run 3/25)")

    result = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=1_700_000_500,
    )

    assert result["queued"] is False
    assert result["reason"] == "already_processing"


def test_record_song_visit_skips_when_same_song_id_is_already_queued(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    now = 1_700_000_600
    first = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now,
    )
    second = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now + 1,
    )

    assert first["queued"] is True
    assert second["queued"] is False
    assert second["reason"] == "already_queued"


def test_record_song_visit_song_mode_ignores_family_level_db_presence(monkeypatch, tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"

    _write_song_meta_index(song_meta_path)
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))

    conn = sqlite3.connect(str(canonical_db))
    try:
        conn.execute("CREATE TABLE songs (name TEXT)")
        conn.execute("INSERT INTO songs (name) VALUES (?)", ("Alpha (Hard) by Artist",))
        conn.commit()
    finally:
        conn.close()

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    now = 1_700_000_900

    first = api.record_song_visit(
        song_id="Alpha (Easy) by Artist",
        title="Alpha",
        artist="Artist",
        now=now,
    )
    assert first["queued"] is True

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    entries = raw.get("entries") or {}
    assert isinstance(entries, dict)
    assert len(entries) == 1
    entry = next(iter(entries.values()))
    assert int(entry.get("last_computed_at", 0) or 0) == 0
    assert int(entry.get("last_requested_at", 0) or 0) == int(now)

    second = api.record_song_visit(
        song_id="Alpha (Normal) by Artist",
        title="Alpha",
        artist="Artist",
        now=now + 10,
    )
    assert second["queued"] is True


def test_record_song_visit_honors_recent_family_blacklist_in_song_mode(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    now = 1_700_001_000
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "active_bundle_key": "",
                "entries": {
                    "alpha|artist": {
                        "bundle_key": "alpha|artist",
                        "song_id": "Alpha (Hard) by Artist",
                        "title": "Alpha",
                        "artist": "Artist",
                        "last_computed_at": now,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    result = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now + 60,
    )

    assert result["queued"] is False
    assert result["reason"] == "fresh_compute"

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    entries = raw.get("entries") or {}
    assert list(entries.keys()) == ["song:alpha (hard) by artist"]
    entry = entries["song:alpha (hard) by artist"]
    assert int(entry.get("last_computed_at", 0)) == int(now)


def test_record_song_visit_honors_pending_family_entry_in_song_mode(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    now = 1_700_001_100
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "active_bundle_key": "",
                "entries": {
                    "alpha|artist": {
                        "bundle_key": "alpha|artist",
                        "song_id": "Alpha (Hard) by Artist",
                        "title": "Alpha",
                        "artist": "Artist",
                        "last_requested_at": now,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    result = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now + 1,
    )

    assert result["queued"] is False
    assert result["reason"] == "already_queued"

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    entries = raw.get("entries") or {}
    assert list(entries.keys()) == ["song:alpha (hard) by artist"]
    entry = entries["song:alpha (hard) by artist"]
    assert int(entry.get("last_requested_at", 0)) == int(now)


def test_mark_song_computed_creates_recent_blacklist_without_prior_visit(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    now = 1_700_001_150

    api.mark_song_started(song_id="Alpha (Hard) by Artist")
    marked = api.mark_song_computed(song_id="Alpha (Hard) by Artist", now=now)

    assert marked is True

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    assert raw.get("active_bundle_key") == ""
    entries = raw.get("entries") or {}
    entry = entries.get("song:alpha (hard) by artist") or {}
    assert int(entry.get("last_computed_at", 0) or 0) == int(now)

    revisit = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now + 60,
    )
    assert revisit["queued"] is False
    assert revisit["reason"] == "fresh_compute"


def test_record_song_visit_respects_pending_queue_cap_without_eviction(tmp_path, monkeypatch):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    payload = [
        {"id": f"Song {i} (Hard) by Artist", "title": f"Song {i}", "artist": "Artist", "difficulty": "Hard"}
        for i in range(12)
    ]
    song_meta_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_MAX_PENDING_VISITS", "10")

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    now = 1_700_000_700
    for i in range(10):
        result = api.record_song_visit(
            song_id=f"Song {i} (Hard) by Artist",
            title=f"Song {i}",
            artist="Artist",
            now=now + i,
        )
        assert result["queued"] is True

    blocked = api.record_song_visit(
        song_id="Song 10 (Hard) by Artist",
        title="Song 10",
        artist="Artist",
        now=now + 20,
    )
    assert blocked["queued"] is False
    assert blocked["reason"] == "queue_full"

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    entries = raw.get("entries") or {}
    assert len(entries) == 10


def test_record_song_visit_fails_fast_when_priority_state_lock_is_busy(tmp_path, monkeypatch):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_VISIT_LOCK_TIMEOUT_SEC", "0.05")

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)

    lock_ready = threading.Event()
    release_lock = threading.Event()

    def _hold_lock() -> None:
        with _file_lock(api._lock_path):
            lock_ready.set()
            release_lock.wait(timeout=5.0)

    holder = threading.Thread(target=_hold_lock)
    holder.start()
    assert lock_ready.wait(timeout=1.0) is True

    started = time.perf_counter()
    result = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=1_700_000_800,
    )
    elapsed = time.perf_counter() - started

    release_lock.set()
    holder.join(timeout=1.0)

    assert result["queued"] is False
    assert result["reason"] == "busy"
    assert elapsed < 0.5


def test_service_defaults_force_continuous_all_difficulty_mode(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")

    api = RoBeatsMetaOptimizerApi(
        state_path=tmp_path / "priority_state.json",
        song_meta_index_path=song_meta_path,
    )
    cfg = configparser.ConfigParser()

    changed = api.apply_service_defaults(cfg)

    assert changed is True
    assert cfg.get("IterationEngine", "LoopForever") == "true"
    assert cfg.get("IterationEngine", "SongRepeats") == "25"
    assert cfg.get("IterationEngine", "UseEvolutionDB") == "true"
    assert cfg.get("IterationEngine", "InFlightSongs") == "12"
    assert cfg.get("CalculateSong", "Difficulty") == "All"
    assert cfg.get("CalculateSong", "Song_Name") == ""
    assert cfg.get("CalculateSong", "TargetPrimary") == "all"
    assert cfg.get("CalculateSong", "TargetSecondary") == "all"


def test_service_mode_defaults_to_disabled_without_explicit_env(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))

    assert RoBeatsMetaOptimizerApi.service_mode_enabled(song_meta_index_path=song_meta_path) is False

    api = RoBeatsMetaOptimizerApi(
        state_path=tmp_path / "priority_state.json",
        song_meta_index_path=song_meta_path,
    )
    assert api.backend_mode_enabled() is False
    assert api.apply_service_defaults(configparser.ConfigParser()) is False


def test_service_mode_env_zero_disables_backend_override(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "0")

    assert RoBeatsMetaOptimizerApi.service_mode_enabled(song_meta_index_path=song_meta_path) is False

    api = RoBeatsMetaOptimizerApi(
        state_path=tmp_path / "priority_state.json",
        song_meta_index_path=song_meta_path,
    )
    cfg = configparser.ConfigParser()

    changed = api.apply_service_defaults(cfg)

    assert changed is False
    assert api.backend_mode_enabled() is False


def test_service_defaults_env_zero_keeps_service_mode_without_overrides(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_DEFAULTS", "0")

    api = RoBeatsMetaOptimizerApi(
        state_path=tmp_path / "priority_state.json",
        song_meta_index_path=song_meta_path,
    )
    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "LoopForever", "false")
    cfg.set("IterationEngine", "SongRepeats", "2")

    changed = api.apply_service_defaults(cfg)

    assert api.backend_mode_enabled() is True
    assert api.service_defaults_enabled() is False
    assert changed is False
    assert cfg.get("IterationEngine", "LoopForever") == "false"
    assert cfg.get("IterationEngine", "SongRepeats") == "2"


def test_service_benchmark_mode_keeps_defaults_but_forces_bounded_loop(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_DEFAULTS", "1")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_BENCHMARK_MODE", "1")

    api = RoBeatsMetaOptimizerApi(
        state_path=tmp_path / "priority_state.json",
        song_meta_index_path=song_meta_path,
    )
    cfg = configparser.ConfigParser()

    changed = api.apply_service_defaults(cfg)

    assert api.backend_mode_enabled() is True
    assert api.service_defaults_enabled() is True
    assert api.benchmark_mode_enabled() is True
    assert changed is True
    assert cfg.get("IterationEngine", "LoopForever") == "false"
    assert cfg.get("IterationEngine", "SongRepeats") == "25"
    assert cfg.get("IterationEngine", "InFlightSongs") == "12"
    assert cfg.get("CalculateSong", "Difficulty") == "All"


def test_priority_queue_env_zero_keeps_service_mode_but_disables_queue_shaping(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_PRIORITY_QUEUE", "0")

    assert RoBeatsMetaOptimizerApi.service_mode_enabled(song_meta_index_path=song_meta_path) is True
    assert RoBeatsMetaOptimizerApi.priority_queue_enabled() is False


def test_app_priority_keeps_backend_new_songs_ahead_of_visit_reprioritization():
    from gear_optimizer.app import GearOptimizerApp

    class DummyApi:
        @staticmethod
        def backend_mode_enabled():
            return True

        @staticmethod
        def prioritize_song_queue(song_queue):
            return list(reversed(song_queue))

    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._robeatsmeta_api = DummyApi()
    app._backend_priority_song_names = {"New Song (Hard) by Artist"}

    queue = [
        ("new.txt", "New Song (Hard) by Artist", "Hard"),
        ("old1.txt", "Old Song 1", "Hard"),
        ("old2.txt", "Old Song 2", "Hard"),
    ]

    prioritized = app._prioritize_robeatsmeta_song_queue(queue)
    assert [item[1] for item in prioritized] == [
        "New Song (Hard) by Artist",
        "Old Song 2",
        "Old Song 1",
    ]


def test_app_marks_song_batch_computed_only_after_final_task(tmp_path, monkeypatch):
    from gear_optimizer.app import GearOptimizerApp
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_PRIORITY_QUEUE", "1")

    state_path = tmp_path / "priority_state.json"
    status_path = tmp_path / "status.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    payload = [
        {"id": "Alpha (Easy) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Easy"},
    ]
    song_meta_path.write_text(json.dumps(payload), encoding="utf-8")

    api = RoBeatsMetaOptimizerApi(
        state_path=state_path,
        status_path=status_path,
        song_meta_index_path=song_meta_path,
    )
    now = int(time.time())
    api.record_song_visit(song_id="Alpha (Easy) by Artist", title="Alpha", artist="Artist", now=now)

    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._robeatsmeta_api = api
    app._run_tasks_ref = [
        ("alpha_easy.txt", "Alpha (Easy) by Artist", "Easy", {}, None, None, None, None, None, None, None, None, None, None, None, None, {"repeat_index": 1, "repeat_total": 2, "ga_seed": 1}),
        ("alpha_easy_again.txt", "Alpha (Easy) by Artist", "Easy", {}, None, None, None, None, None, None, None, None, None, None, None, None, {"repeat_index": 2, "repeat_total": 2, "ga_seed": 2}),
    ]
    completed = {"Alpha (Easy) by Artist (Run 1/2)"}
    app._run_completed_ref = completed

    marked_mid = app._maybe_mark_robeatsmeta_song_batch_computed("Alpha (Easy) by Artist (Run 1/2)", completed)
    state_mid = json.loads(state_path.read_text(encoding="utf-8"))
    entry_mid = next(iter((state_mid.get("entries") or {}).values()))
    assert marked_mid is False
    assert entry_mid.get("last_computed_at", 0) == 0

    completed.add("Alpha (Easy) by Artist (Run 2/2)")
    marked_final = app._maybe_mark_robeatsmeta_song_batch_computed("Alpha (Easy) by Artist (Run 2/2)", completed)
    state_final = json.loads(state_path.read_text(encoding="utf-8"))
    entry_final = next(iter((state_final.get("entries") or {}).values()))
    assert marked_final is True
    assert int(entry_final.get("last_computed_at", 0)) > 0


def test_filter_recently_computed_song_queue_skips_completed_bundles_but_keeps_pending(tmp_path, monkeypatch):
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_PRIORITY_QUEUE", "1")
    state_path = tmp_path / "priority_state.json"
    status_path = tmp_path / "status.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    payload = [
        {"id": "Alpha (Hard) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Hard"},
        {"id": "Beta (Hard) by Artist", "title": "Beta", "artist": "Artist", "difficulty": "Hard"},
    ]
    song_meta_path.write_text(json.dumps(payload), encoding="utf-8")

    api = RoBeatsMetaOptimizerApi(
        state_path=state_path,
        status_path=status_path,
        song_meta_index_path=song_meta_path,
    )
    now = int(time.time())
    api.record_song_visit(song_id="Alpha (Hard) by Artist", title="Alpha", artist="Artist", now=now)
    api.mark_song_computed(song_id="Alpha (Hard) by Artist", now=now + 1)
    api.record_song_visit(song_id="Beta (Hard) by Artist", title="Beta", artist="Artist", now=now + 2)

    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._robeatsmeta_api = api

    queue = [
        ("alpha.txt", "Alpha (Hard) by Artist", "Hard"),
        ("beta.txt", "Beta (Hard) by Artist", "Hard"),
    ]

    filtered = app._filter_robeatsmeta_recently_computed_song_queue(queue)
    assert [item[1] for item in filtered] == ["Beta (Hard) by Artist"]


def test_filter_recently_computed_song_queue_honors_family_blacklist_in_song_mode(tmp_path, monkeypatch):
    from gear_optimizer.app import GearOptimizerApp

    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_PRIORITY_QUEUE", "1")
    state_path = tmp_path / "priority_state.json"
    status_path = tmp_path / "status.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)
    now = int(time.time())
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "active_bundle_key": "",
                "entries": {
                    "alpha|artist": {
                        "bundle_key": "alpha|artist",
                        "song_id": "Alpha (Hard) by Artist",
                        "title": "Alpha",
                        "artist": "Artist",
                        "last_computed_at": now,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    api = RoBeatsMetaOptimizerApi(
        state_path=state_path,
        status_path=status_path,
        song_meta_index_path=song_meta_path,
    )

    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._robeatsmeta_api = api

    queue = [("alpha.txt", "Alpha (Hard) by Artist", "Hard")]

    filtered = app._filter_robeatsmeta_recently_computed_song_queue(queue)
    assert filtered == []


def test_prioritize_song_queue_honors_pending_family_key_in_song_mode(tmp_path):
    state_path = tmp_path / "priority_state.json"
    song_meta_path = tmp_path / "song_meta_index.json"
    _write_song_meta_index(song_meta_path)

    now = 1_700_001_200
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "active_bundle_key": "",
                "entries": {
                    "alpha|artist": {
                        "bundle_key": "alpha|artist",
                        "song_id": "Alpha (Hard) by Artist",
                        "title": "Alpha",
                        "artist": "Artist",
                        "last_requested_at": now,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    api = RoBeatsMetaOptimizerApi(state_path=state_path, song_meta_index_path=song_meta_path)
    song_queue = [
        ("beta.txt", "Beta (Hard) by Artist", "Hard"),
        ("alpha_h.txt", "Alpha (Hard) by Artist", "Hard"),
    ]

    prioritized = api.prioritize_song_queue(song_queue, now=now + 5)
    assert [item[1] for item in prioritized] == [
        "Alpha (Hard) by Artist",
        "Beta (Hard) by Artist",
    ]


def test_app_pending_song_queue_uses_cached_song_path_index_without_rescan():
    from gear_optimizer.app import GearOptimizerApp

    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._song_path_index_lock = threading.Lock()
    app._song_path_index = {
        "Alpha (Hard) by Artist": [
            {
                "fp": "/tmp/Hard/alpha.txt",
                "abs_fp": "/tmp/Hard/alpha.txt",
                "song_name": "Alpha (Hard) by Artist",
                "song_name_lower": "alpha (hard) by artist",
                "detected_diff": "Hard",
                "primary_color": "chill",
                "secondary_color": "flow",
            }
        ]
    }
    app._song_path_index_ready = True
    app._song_path_index_roots = ("/tmp",)
    app._stop_requested_now = lambda: False
    app._song_index_roots = lambda: ["/tmp"]

    scans = {"count": 0}

    def _never_scan(_roots):
        scans["count"] += 1
        return {}

    app._scan_song_paths_for_index = _never_scan

    first_queue, first_unresolved = app._build_song_queue_from_pending_ids(
        ["Alpha (Hard) by Artist"],
        diff_lower="hard",
        filter_search="",
        target_primary_all=True,
        target_primary_colors=set(),
        target_secondary_all=True,
        target_secondary_colors=set(),
    )
    second_queue, second_unresolved = app._build_song_queue_from_pending_ids(
        ["Alpha (Hard) by Artist"],
        diff_lower="hard",
        filter_search="",
        target_primary_all=True,
        target_primary_colors=set(),
        target_secondary_all=True,
        target_secondary_colors=set(),
    )

    assert scans["count"] == 0
    assert first_unresolved == []
    assert second_unresolved == []
    assert [item[1] for item in first_queue] == ["Alpha (Hard) by Artist"]
    assert [item[1] for item in second_queue] == ["Alpha (Hard) by Artist"]
