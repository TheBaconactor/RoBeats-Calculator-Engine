import sys
import types

import gear_optimizer.cli as optimizer_cli


def test_cli_run_inits_app_once_and_returns_its_exit_status(monkeypatch):
    calls: list[str] = []
    status = []

    class FakeApp:
        def __init__(self):
            calls.append("init")

        def run(self):
            calls.append("run")
            return status[0]

    monkeypatch.setattr(optimizer_cli, "common_init", lambda: None)
    monkeypatch.setitem(sys.modules, "gear_optimizer.app", types.SimpleNamespace(GearOptimizerApp=FakeApp))

    status.append(0)
    assert optimizer_cli.run() == 0
    status[0] = 1
    assert optimizer_cli.run() == 1
    assert calls == ["init", "run", "init", "run"]
