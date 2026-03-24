def test_tui_progress_does_not_render_in_compute(monkeypatch):
    import gear_optimizer.app as app_mod

    called = False

    def _boom(*_args, **_kwargs):
        nonlocal called
        called = True
        raise RuntimeError("should not be called from compute process")

    # Patch only the app module's view of `shutil` so pytest's own terminal reporter
    # (which calls `shutil.get_terminal_size`) is unaffected.
    class _FakeShutil:
        @staticmethod
        def get_terminal_size(*args, **kwargs):
            return _boom(*args, **kwargs)

    monkeypatch.setattr(app_mod, "shutil", _FakeShutil)

    app = app_mod.GearOptimizerApp()
    # Force-enable progress + TUI for this unit test without needing a real TTY.
    app._output_enabled = False
    app._progress_enabled = True
    app._tui_enabled = True
    app._progress_interval = 0.05
    app._progress_bar_width = 16

    app._start_progress(10, completed=0)
    try:
        app._progress_event(completed_delta=0, record_info={"song": "TestSong", "status": "RUNNING"})
        app._progress_event(completed_delta=1, record_info={"song": "TestSong", "status": "DONE"})
    finally:
        app._stop_progress()

    assert not called
