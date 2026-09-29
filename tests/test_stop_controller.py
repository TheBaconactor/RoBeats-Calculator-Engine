from gear_optimizer.app_stop_control import STOP_FILE_POLL_SEC, StopController


def test_stop_controller_throttles_stop_file_checks(monkeypatch, tmp_path):
    now_box = {"now": 100.0}
    calls = {"exists": 0}
    monkeypatch.setattr("gear_optimizer.app_stop_control.time.monotonic", lambda: float(now_box["now"]))

    def _fake_exists(path):
        calls["exists"] += 1
        return False

    monkeypatch.setattr("gear_optimizer.app_stop_control.os.path.exists", _fake_exists)

    ctrl = StopController(bin_dir=str(tmp_path))

    assert ctrl.stop_requested_now() is False
    assert ctrl.stop_requested_now() is False
    assert calls["exists"] == 1

    now_box["now"] += STOP_FILE_POLL_SEC / 2
    assert ctrl.stop_requested_now() is False
    assert calls["exists"] == 1

    now_box["now"] += STOP_FILE_POLL_SEC
    assert ctrl.stop_requested_now() is False
    assert calls["exists"] == 2


def test_stop_controller_honors_stop_file_after_poll_interval(monkeypatch, tmp_path):
    now_box = {"now": 5.0}
    monkeypatch.setattr("gear_optimizer.app_stop_control.time.monotonic", lambda: float(now_box["now"]))

    ctrl = StopController(bin_dir=str(tmp_path))
    assert ctrl.stop_requested_now() is False

    (tmp_path / "STOP").write_text("", encoding="utf-8")
    now_box["now"] += STOP_FILE_POLL_SEC + 0.05

    assert ctrl.stop_requested_now() is True
    assert ctrl.stop_requested_event.is_set()
