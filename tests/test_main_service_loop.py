import sys
import types

import gear_optimizer.cli as optimizer_cli


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
