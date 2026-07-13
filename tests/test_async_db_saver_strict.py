import time

import pytest

from gear_optimizer.app_async_db import AsyncDbSaver


def test_async_db_saver_strict_latches_errors_and_surfaces_them(tmp_path, monkeypatch):
    # Async DB persistence is strict when GPU_STRICT is on (default); pin it so the
    # test stays hermetic under a GPU_STRICT=0 dev/CI env. A save failure must latch
    # and surface rather than continue "successfully".
    monkeypatch.setenv("GPU_STRICT", "1")
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "strict.db"))

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("gear_optimizer.app_async_db.save_optimizer_song_result", _boom)

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


def test_async_db_saver_strict_rejects_blank_song_key(tmp_path, monkeypatch):
    monkeypatch.setenv("GPU_STRICT", "1")
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "blank.db"))
    saver = AsyncDbSaver()
    saver.submit(
        "   ",
        [{"score": 1, "fg_score": 0, "gear": ["G1"], "minis": ["M1"], "details": {}, "force": None}],
        meta={"_processed_run": True},
    )

    deadline = time.monotonic() + 5.0
    while saver.last_error() is None and time.monotonic() < deadline:
        time.sleep(0.05)

    err = saver.last_error()
    assert err is not None
    assert "non-empty song key" in err["message"]
    with pytest.raises(RuntimeError, match="non-empty song key"):
        saver.shutdown(timeout=0.5)


def test_async_db_saver_strict_latches_malformed_score(tmp_path, monkeypatch):
    monkeypatch.setenv("GPU_STRICT", "1")
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "malformed.db"))
    saver = AsyncDbSaver()
    saver.submit(
        "Malformed Song",
        [
            {
                "score": "not-an-integer",
                "fg_score": 0,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {},
                "force": None,
            }
        ],
        meta={"_processed_run": True},
    )

    deadline = time.monotonic() + 5.0
    while saver.last_error() is None and time.monotonic() < deadline:
        time.sleep(0.05)

    err = saver.last_error()
    assert err is not None
    assert "invalid score" in err["message"]
    with pytest.raises(RuntimeError, match="invalid score"):
        saver.shutdown(timeout=0.5)
