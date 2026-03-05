from gear_optimizer.app import _banner_enabled_default, _progress_ui_enabled_default


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


def test_banner_defaults_off_when_stream_is_not_tty():
    assert _banner_enabled_default(stream_is_tty=False, banner_env=None) is False


def test_banner_can_be_explicitly_forced_or_disabled():
    assert _banner_enabled_default(stream_is_tty=False, banner_env="1") is True
    assert _banner_enabled_default(stream_is_tty=True, banner_env="0") is False
