from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch


def test_gpu_dispatch_timing_envelope_telemetry_is_present():
    import inspect

    source = inspect.getsource(gpu_dispatch.process_force_greats_gpu_finder)

    assert "timing_envelope_fg" in source


def test_uses_timing_envelope_fg_detects_fg_timing_stream():
    calc_song = {
        "metadata": {"TimingEnvelopeApplied": True},
        "song_data": {
            "fg_timestamps": [0.0, 1.0],
            "fg_great_candidate_timestamps": [0.05, 1.05],
        },
    }

    assert gpu_dispatch._uses_timing_envelope_fg(calc_song) is True
    assert gpu_dispatch._uses_timing_envelope_fg({"metadata": {}, "song_data": {}}) is False


def test_should_use_fused_breakpoints_solve_defaults_on_for_inprocess(monkeypatch):
    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=True, has_gpu_client=True) is True
    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=False, has_gpu_client=True) is False
    assert gpu_dispatch._should_use_fused_breakpoints_solve(in_process=True, has_gpu_client=False) is False


def test_default_fused_payloads_per_request_scales_with_fg_workers(monkeypatch):
    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "1")
    assert gpu_dispatch._default_fused_payloads_per_request() == 4

    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "2")
    assert gpu_dispatch._default_fused_payloads_per_request() == 8

    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "4")
    assert gpu_dispatch._default_fused_payloads_per_request() == 8
