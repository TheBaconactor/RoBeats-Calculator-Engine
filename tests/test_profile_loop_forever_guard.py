import configparser

from gear_optimizer.app import GearOptimizerApp


def _mk_app() -> GearOptimizerApp:
    return GearOptimizerApp.__new__(GearOptimizerApp)


def test_profiling_mode_enabled_by_env(monkeypatch):
    app = _mk_app()
    monkeypatch.setenv("DEBUG_PROFILE", "1")
    cfg = configparser.ConfigParser()
    cfg.read_dict({"CalculateSong": {"LoopForever": "true"}})
    assert app._profiling_mode_enabled(cfg) is True


def test_profiling_mode_enabled_by_config():
    app = _mk_app()
    cfg = configparser.ConfigParser()
    cfg.read_dict(
        {
            "Debug": {"DebugProfile": "true"},
            "CalculateSong": {"LoopForever": "true"},
        }
    )
    assert app._profiling_mode_enabled(cfg) is True


def test_profiling_mode_disabled_without_flags(monkeypatch):
    app = _mk_app()
    monkeypatch.delenv("DEBUG_PROFILE", raising=False)
    monkeypatch.delenv("METAFINDER_DEBUG_PROFILE", raising=False)
    monkeypatch.delenv("PERF_TIMING", raising=False)
    cfg = configparser.ConfigParser()
    cfg.read_dict({"CalculateSong": {"LoopForever": "true"}})
    assert app._profiling_mode_enabled(cfg) is False


def test_loop_restart_wait_seconds_defaults_to_zero(monkeypatch):
    app = _mk_app()
    monkeypatch.delenv("METAFINDER_LOOP_RESTART_WAIT_SEC", raising=False)
    monkeypatch.delenv("LOOP_RESTART_WAIT_SEC", raising=False)
    cfg = configparser.ConfigParser()
    cfg.read_dict({"CalculateSong": {"LoopForever": "true"}})
    assert app._loop_restart_wait_seconds(cfg, default_seconds=0.0) == 0.0


def test_loop_restart_wait_seconds_env_overrides_config(monkeypatch):
    app = _mk_app()
    cfg = configparser.ConfigParser()
    cfg.read_dict({"IterationEngine": {"LoopRestartWaitSec": "2.5"}})
    monkeypatch.setenv("METAFINDER_LOOP_RESTART_WAIT_SEC", "0.25")
    assert app._loop_restart_wait_seconds(cfg, default_seconds=0.0) == 0.25


def test_handle_loop_restart_skips_sleep_when_wait_zero(monkeypatch):
    import gear_optimizer.app as app_mod

    app = _mk_app()
    sleep_calls: list[float] = []

    monkeypatch.setattr(app_mod.os.path, "exists", lambda _p: False)
    monkeypatch.setattr(app_mod.time, "sleep", lambda seconds: sleep_calls.append(float(seconds)))

    app._handle_loop_restart(wait_time=0)
    assert sleep_calls == []
