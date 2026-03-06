import configparser

from gear_optimizer.app import GearOptimizerApp


def _build_cfg(song_repeats: int) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "SongRepeats", str(int(song_repeats)))
    return cfg


def test_prepare_tasks_song_repeats_expands_queue():
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(3)

    song_queue = [("dummy.txt", "Dummy Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        use_evo_db=False,
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 3
    assert all(len(t) == 17 for t in tasks)
    assert [app._task_queue_label(t) for t in tasks] == [
        "Dummy Song (Run 1/3)",
        "Dummy Song (Run 2/3)",
        "Dummy Song (Run 3/3)",
    ]

    seeds = [t[16]["ga_seed"] for t in tasks]
    assert len(seeds) == 3
    assert len(set(seeds)) == 3


def test_prepare_tasks_song_repeats_one_keeps_single_shape():
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    cfg = _build_cfg(1)

    song_queue = [("dummy.txt", "Dummy Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        use_evo_db=False,
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 1
    assert len(tasks[0]) == 16
    assert app._extract_repeat_ctx(tasks[0]) is None
    assert app._task_queue_label(tasks[0]) == "Dummy Song"


def test_prepare_tasks_backend_priority_new_songs_use_fixed_50_repeats(monkeypatch, tmp_path):
    song_meta_path = tmp_path / "song_meta_index.json"
    canonical_db = tmp_path / "canonical.db"
    song_meta_path.write_text("[]", encoding="utf-8")
    canonical_db.write_text("", encoding="utf-8")
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    app = GearOptimizerApp.__new__(GearOptimizerApp)
    app._robeatsmeta_api = type("DummyApi", (), {"backend_mode_enabled": staticmethod(lambda: True)})()
    app._backend_priority_song_names = {"New Song"}
    app._backend_priority_song_repeat_count = 50
    cfg = _build_cfg(25)

    song_queue = [("dummy.txt", "New Song", "Hard")]
    tasks = app._prepare_tasks(
        song_queue=song_queue,
        cfg=cfg,
        paths={},
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        use_evo_db=False,
        auto_buff="",
        ga_depth=1,
        status_queue=None,
        fg_debug=False,
    )

    assert len(tasks) == 50
    assert app._task_queue_label(tasks[-1]) == "New Song (Run 50/50)"
