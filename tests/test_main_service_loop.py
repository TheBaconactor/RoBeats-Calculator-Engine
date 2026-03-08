import sys
import types

import main as optimizer_main


def test_main_runs_app_once_and_ignores_run_return_value(monkeypatch):
    calls: list[str] = []

    class FakeApp:
        def __init__(self):
            calls.append("init")

        def run(self):
            calls.append("run")
            return True

    monkeypatch.setattr(optimizer_main.multiprocessing, "freeze_support", lambda: None)
    monkeypatch.setattr(optimizer_main, "_read_config_path", lambda: "config.ini")
    monkeypatch.setattr(optimizer_main, "_apply_taichi_shell_env", lambda: None)
    monkeypatch.setattr(optimizer_main, "_apply_debug_profile_env", lambda _cfg: None)
    monkeypatch.setattr(optimizer_main, "_apply_gpu_song_slots_default", lambda: None)
    monkeypatch.setattr(optimizer_main, "_apply_throughput_mode_env", lambda: None)
    monkeypatch.setitem(sys.modules, "gear_optimizer.app", types.SimpleNamespace(GearOptimizerApp=FakeApp))

    assert optimizer_main.main() == 0
    assert calls == ["init", "run"]
