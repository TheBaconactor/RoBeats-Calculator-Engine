import configparser

from gear_optimizer.app import GearOptimizerApp


def _mk_app() -> GearOptimizerApp:
    return GearOptimizerApp.__new__(GearOptimizerApp)


def test_profiling_mode_enabled_by_env(monkeypatch):
    app = _mk_app()
    monkeypatch.setenv("DEBUG_PROFILE", "1")
    cfg = configparser.ConfigParser()
    cfg.read_dict({"IterationEngine": {"LoopForever": "true"}})
    assert app._profiling_mode_enabled(cfg) is True


def test_profiling_mode_enabled_by_config():
    app = _mk_app()
    cfg = configparser.ConfigParser()
    cfg.read_dict(
        {
            "Debug": {"DebugProfile": "true"},
            "IterationEngine": {"LoopForever": "true"},
        }
    )
    assert app._profiling_mode_enabled(cfg) is True


def test_profiling_mode_disabled_without_flags(monkeypatch):
    app = _mk_app()
    monkeypatch.delenv("DEBUG_PROFILE", raising=False)
    monkeypatch.delenv("METAFINDER_DEBUG_PROFILE", raising=False)
    monkeypatch.delenv("PERF_TIMING", raising=False)
    monkeypatch.delenv("GPU_EXECUTOR_TRACE_PATH", raising=False)
    cfg = configparser.ConfigParser()
    cfg.read_dict({"IterationEngine": {"LoopForever": "true"}})
    assert app._profiling_mode_enabled(cfg) is False
