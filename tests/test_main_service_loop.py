import sys
import threading
import types

import pytest

import gear_optimizer.app as app_module
import gear_optimizer.cli as optimizer_cli
from gear_optimizer.app import GearOptimizerApp


def test_cli_run_inits_app_once_and_ignores_run_return_value(monkeypatch):
    calls: list[str] = []

    class FakeApp:
        def __init__(self):
            calls.append("init")

        def run(self):
            calls.append("run")
            return True

    monkeypatch.setattr(optimizer_cli, "common_init", lambda: None)
    monkeypatch.setattr(optimizer_cli, "_read_config_path", lambda: "config.ini")
    monkeypatch.setattr(optimizer_cli, "_apply_taichi_shell_env", lambda: None)
    monkeypatch.setattr(optimizer_cli, "_apply_debug_profile_env", lambda _cfg: None)
    monkeypatch.setattr(optimizer_cli, "_apply_gpu_song_slots_default", lambda: None)
    monkeypatch.setattr(optimizer_cli, "_apply_throughput_mode_env", lambda: None)
    monkeypatch.setitem(sys.modules, "gear_optimizer.app", types.SimpleNamespace(GearOptimizerApp=FakeApp))

    assert optimizer_cli.run() == 0
    assert calls == ["init", "run"]


def test_iteration_failure_propagates_after_cleanup(monkeypatch):
    app = object.__new__(GearOptimizerApp)
    cleanup_calls: list[str] = []
    app._stop_requested_now = lambda: False
    app._stop_progress = lambda: cleanup_calls.append("progress")
    app._cleanup_resources = lambda: cleanup_calls.append("resources")
    app._stop_requested = threading.Event()

    def _fail_config_load():
        raise RuntimeError("startup exploded")

    monkeypatch.setattr(app_module, "load_config", _fail_config_load)

    with pytest.raises(RuntimeError, match="startup exploded"):
        app._run_single_iteration()

    assert cleanup_calls == ["progress", "resources"]


def test_cli_run_returns_failure_when_app_raises(monkeypatch, capsys):
    class FailingApp:
        def run(self):
            raise RuntimeError("iteration failed")

    monkeypatch.setattr(optimizer_cli, "common_init", lambda: None)
    monkeypatch.setattr(optimizer_cli, "_read_config_path", lambda: "config.ini")
    monkeypatch.setattr(optimizer_cli, "_apply_taichi_shell_env", lambda: None)
    monkeypatch.setattr(optimizer_cli, "_apply_debug_profile_env", lambda _cfg: None)
    monkeypatch.setattr(optimizer_cli, "_apply_gpu_song_slots_default", lambda: None)
    monkeypatch.setattr(optimizer_cli, "_apply_throughput_mode_env", lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.app",
        types.SimpleNamespace(GearOptimizerApp=FailingApp),
    )

    assert optimizer_cli.run() == 1
    assert "Fatal Error: iteration failed" in capsys.readouterr().out
