import configparser

from gear_optimizer.solver.native_inflight_orchestrator import _read_fg_backlog_threshold


def _cfg_with_iteration_engine(**pairs: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {k: str(v) for k, v in pairs.items()}
    return cfg


def test_backlog_threshold_uses_legacy_fg_interleave_every_when_new_key_missing(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_BACKLOG_THRESHOLD", raising=False)
    monkeypatch.delenv("FG_BACKLOG_THRESHOLD", raising=False)

    cfg = _cfg_with_iteration_engine(FG_InterleaveEvery="24")
    assert _read_fg_backlog_threshold(cfg) == 24


def test_backlog_threshold_prefers_new_key_over_legacy(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_BACKLOG_THRESHOLD", raising=False)
    monkeypatch.delenv("FG_BACKLOG_THRESHOLD", raising=False)

    cfg = _cfg_with_iteration_engine(FG_BacklogThreshold="13", FG_InterleaveEvery="24")
    assert _read_fg_backlog_threshold(cfg) == 13


def test_backlog_threshold_env_override_wins(monkeypatch):
    monkeypatch.setenv("INFLIGHT_FG_BACKLOG_THRESHOLD", "9")

    cfg = _cfg_with_iteration_engine(FG_BacklogThreshold="13", FG_InterleaveEvery="24")
    assert _read_fg_backlog_threshold(cfg) == 9
