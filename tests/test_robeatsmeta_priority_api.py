import configparser
import json

from gear_optimizer.robeatsmeta_api import RoBeatsMetaOptimizerApi


def _write_song_meta_index(path):
    payload = [
        {"id": "Alpha (Hard) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Hard"},
        {"id": "Alpha (Normal) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Normal"},
        {"id": "Alpha (Easy) by Artist", "title": "Alpha", "artist": "Artist", "difficulty": "Easy"},
        {"id": "Beta (Hard) by Artist", "title": "Beta", "artist": "Artist", "difficulty": "Hard"},
        {"id": "Gamma (Hard) by Artist", "title": "Gamma", "artist": "Artist", "difficulty": "Hard"},
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_prioritize_song_queue_promotes_all_difficulties_for_requested_song(tmp_path):
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
    assert [item[1] for item in prioritized[:3]] == [
        "Alpha (Hard) by Artist",
        "Alpha (Normal) by Artist",
        "Alpha (Easy) by Artist",
    ]


def test_reprioritize_pending_tasks_moves_requested_song_family_to_front(tmp_path):
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
        "Alpha (Normal) by Artist",
        "Alpha (Easy) by Artist",
        "Gamma (Hard) by Artist",
    ]

    api.mark_song_computed(song_id="Alpha (Normal) by Artist", now=now + 2)
    second_visit = api.record_song_visit(
        song_id="Alpha (Hard) by Artist",
        title="Alpha",
        artist="Artist",
        now=now + 3,
    )

    assert second_visit["queued"] is False
    assert second_visit["reason"] == "fresh_compute"


def test_service_defaults_force_continuous_all_difficulty_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")

    api = RoBeatsMetaOptimizerApi(
        state_path=tmp_path / "priority_state.json",
        song_meta_index_path=tmp_path / "song_meta_index.json",
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


def test_app_priority_keeps_backend_new_songs_ahead_of_visit_reprioritization():
    from gear_optimizer.app import GearOptimizerApp

    class DummyApi:
        @staticmethod
        def priority_queue_enabled():
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
