from gear_optimizer.app import _progress_ui_enabled_default


def test_progress_ui_defaults_off_when_stream_is_not_tty():
    assert (
        _progress_ui_enabled_default(
            configured_enabled=True,
            output_enabled=False,
            progress_env_present=False,
            stream_is_tty=False,
        )
        is False
    )


def test_progress_ui_can_be_forced_on_headless_stream():
    assert (
        _progress_ui_enabled_default(
            configured_enabled=True,
            output_enabled=False,
            progress_env_present=True,
            stream_is_tty=False,
        )
        is True
    )


def test_progress_ui_respects_output_mode_suppression_without_override():
    assert (
        _progress_ui_enabled_default(
            configured_enabled=True,
            output_enabled=True,
            progress_env_present=False,
            stream_is_tty=True,
        )
        is False
    )
