from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch


def test_should_use_fused_breakpoints_solve_defaults_on_for_inprocess(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FORCE_FUSED_FG", raising=False)
    monkeypatch.delenv("FG_FUSE_BREAKPOINTS_SOLVE", raising=False)

    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=True, has_gpu_client=True) is True
    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=False, has_gpu_client=True) is False
    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=True, has_gpu_client=False) is False


def test_should_use_fused_breakpoints_solve_allows_legacy_optout(monkeypatch):
    monkeypatch.setenv("INFLIGHT_FORCE_FUSED_FG", "0")
    monkeypatch.setenv("FG_FUSE_BREAKPOINTS_SOLVE", "0")
    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=True, has_gpu_client=True) is False

    monkeypatch.setenv("FG_FUSE_BREAKPOINTS_SOLVE", "1")
    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=True, has_gpu_client=True) is True


def test_default_fused_payloads_per_request_scales_with_fg_workers(monkeypatch):
    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "1")
    assert gpu_dispatch._default_fused_payloads_per_request() == 64

    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "2")
    assert gpu_dispatch._default_fused_payloads_per_request() == 96

    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "4")
    assert gpu_dispatch._default_fused_payloads_per_request() == 128
