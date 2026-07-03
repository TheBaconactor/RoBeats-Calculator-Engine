"""
Regression: the spawned post-processor child must durably log failure payloads.

The post-processor runs in a `multiprocessing` child whose root logger has no
handlers, and (in quiet mode) stderr is suppressed process-wide when Taichi is
imported. Before the fix, per-song `[POST] FAILED: ...` payloads reached neither
the console nor `bin/error.log`, concealing fail-loud errors (the 2026-07-02
"stuck at 33/2237" incident). `run_post_processor` now calls
`configure_default_logging()` at its entry point so error payloads are durably
recorded to `bin/error.log`.
"""

from __future__ import annotations

import multiprocessing

import pytest


def test_post_processor_child_logs_failure_payload_to_file(tmp_path, monkeypatch):
    # Redirect the durable log target into the test's tmp dir. The spawned child
    # re-reads this env var when it imports `constants` and resolves BIN_DIR, so the
    # child writes `bin/error.log` under `tmp_path` instead of the repo tree.
    bin_dir = tmp_path / "bin"
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_BIN_DIR", str(bin_dir))
    # Quiet mode is the production default and the case that concealed the incident
    # (stderr suppressed); keep output disabled so we exercise the file handler only.
    monkeypatch.delenv("METAFINDER_OUTPUT", raising=False)
    monkeypatch.delenv("METAFINDER_VERBOSE", raising=False)

    # A spawn context matches the Windows production path (fresh child, unconfigured
    # root logger) rather than inheriting the parent's handlers via fork.
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()
    result_queue.put(
        {
            "_error": "boom-sentinel-8f3a2c",
            "_error_type": "ValueError",
            "_song_name": "UnitTestSong",
        }
    )
    result_queue.put(None)  # shutdown sentinel

    from gear_optimizer.pipeline.post_processor import run_post_processor

    proc = ctx.Process(target=run_post_processor, args=(result_queue, 1), name="TestPostProc")
    proc.start()
    proc.join(timeout=90)

    if proc.is_alive():  # pragma: no cover - only on a hang
        proc.terminate()
        proc.join(timeout=5)
        pytest.fail("post-processor child did not exit after processing the shutdown sentinel")

    assert proc.exitcode == 0, f"post-processor child exited with {proc.exitcode}"

    log_file = bin_dir / "error.log"
    assert log_file.exists(), "post-processor child did not create bin/error.log"

    text = log_file.read_text(encoding="utf-8")
    assert "[POST] FAILED" in text
    assert "UnitTestSong" in text
    assert "boom-sentinel-8f3a2c" in text
