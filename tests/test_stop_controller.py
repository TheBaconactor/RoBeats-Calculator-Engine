from gear_optimizer.app_stop_control import StopController


def test_stop_controller_throttles_stop_file_checks(monkeypatch, tmp_path):
    now_box = {"now": 100.0}
    calls = {"exists": 0}
    stop_file = tmp_path / "STOP"

    monkeypatch.setenv("METAFINDER_STOP_FILE", str(stop_file))
    monkeypatch.setenv("METAFINDER_STOP_FILE_POLL_SEC", "0.5")
    monkeypatch.setattr("gear_optimizer.app_stop_control.time.monotonic", lambda: float(now_box["now"]))

    def _fake_exists(path):
        calls["exists"] += 1
        return False

    monkeypatch.setattr("gear_optimizer.app_stop_control.os.path.exists", _fake_exists)

    ctrl = StopController(bin_dir=str(tmp_path))

    assert ctrl.stop_requested_now() is False
    assert ctrl.stop_requested_now() is False
    assert calls["exists"] == 1

    now_box["now"] += 0.25
    assert ctrl.stop_requested_now() is False
    assert calls["exists"] == 1

    now_box["now"] += 0.50
    assert ctrl.stop_requested_now() is False
    assert calls["exists"] == 2


def test_stop_controller_honors_stop_file_after_poll_interval(monkeypatch, tmp_path):
    now_box = {"now": 5.0}
    stop_file = tmp_path / "STOP"

    monkeypatch.setenv("METAFINDER_STOP_FILE", str(stop_file))
    monkeypatch.setenv("METAFINDER_STOP_FILE_POLL_SEC", "0.2")
    monkeypatch.setattr("gear_optimizer.app_stop_control.time.monotonic", lambda: float(now_box["now"]))

    ctrl = StopController(bin_dir=str(tmp_path))
    assert ctrl.stop_requested_now() is False

    stop_file.write_text("", encoding="utf-8")
    now_box["now"] += 0.25

    assert ctrl.stop_requested_now() is True
    assert ctrl.stop_requested_event.is_set()
