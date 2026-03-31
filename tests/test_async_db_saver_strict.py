import time

import pytest

from gear_optimizer.app_async_db import AsyncDbSaver


def test_async_db_saver_strict_latches_errors_and_surfaces_them(monkeypatch):
    monkeypatch.setenv("METAFINDER_ASYNC_DB_STRICT", "1")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    # AsyncDbSaver imports these symbols into its module namespace.
    monkeypatch.setattr("gear_optimizer.app_async_db.save_loadouts_batch", _boom)
    monkeypatch.setattr("gear_optimizer.app_async_db.get_song_counters", lambda *_a, **_k: (0, 0, 0, 0))
    monkeypatch.setattr("gear_optimizer.app_async_db.update_song_counters", lambda *_a, **_k: None)

    saver = AsyncDbSaver()
    saver.submit(
        "Song",
        [{"score": 1, "fg_score": 0, "gear": ["G1"], "minis": ["M1"], "details": {}, "force": None}],
        meta={"db_key": "Song", "_processed_run": True},
    )

    deadline = time.monotonic() + 5.0
    while saver.last_error() is None and time.monotonic() < deadline:
        time.sleep(0.05)

    assert saver.last_error() is not None

    with pytest.raises(RuntimeError):
        saver.submit("Song2", [], meta={"db_key": "Song2", "_processed_run": True})

    with pytest.raises(RuntimeError):
        saver.flush(timeout=0.5)

    with pytest.raises(RuntimeError):
        saver.shutdown(timeout=0.5)
