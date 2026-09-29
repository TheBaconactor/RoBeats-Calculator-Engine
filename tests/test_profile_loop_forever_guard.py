import configparser

from gear_optimizer.app import GearOptimizerApp


def _mk_app() -> GearOptimizerApp:
    return GearOptimizerApp.__new__(GearOptimizerApp)


def test_loop_restart_wait_seconds_defaults_to_zero():
    app = _mk_app()
    cfg = configparser.ConfigParser()
    cfg.read_dict({"CalculateSong": {"LoopForever": "true"}})
    assert app._loop_restart_wait_seconds(cfg, default_seconds=0.0) == 0.0


def test_handle_loop_restart_skips_sleep_when_wait_zero(monkeypatch):
    import gear_optimizer.app as app_mod

    app = _mk_app()
    sleep_calls: list[float] = []

    monkeypatch.setattr(app_mod.os.path, "exists", lambda _p: False)
    monkeypatch.setattr(app_mod.time, "sleep", lambda seconds: sleep_calls.append(float(seconds)))

    app._handle_loop_restart(wait_time=0)
    assert sleep_calls == []


def test_memory_guard_restart_depends_on_pending_resume_work(monkeypatch):
    import gear_optimizer.app as app_mod

    app = _mk_app()

    class _Tracker:
        def __init__(self, pending: int) -> None:
            self._pending = pending

        def pending_count(self) -> int:
            return self._pending

    monkeypatch.setattr(app_mod, "memory_release_requested", lambda: False)
    assert app._memory_guard_restart_needed(_Tracker(10)) is False

    monkeypatch.setattr(app_mod, "memory_release_requested", lambda: True)
    assert app._memory_guard_restart_needed(_Tracker(0)) is False
    assert app._memory_guard_restart_needed(_Tracker(10)) is True
