from pathlib import Path


def test_config_missing_option_emits_fallback_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("METAFINDER_FALLBACK_WARN", "1")

    cfg_path = Path(tmp_path) / "config.ini"
    cfg_path.write_text("[IterationEngine]\nMetaFinder=true\n", encoding="utf-8")

    from gear_optimizer.core.config import load_config

    cfg = load_config(str(cfg_path))
    capsys.readouterr()

    value = cfg.get("IterationEngine", "SongQueueLimit", fallback="0")
    captured = capsys.readouterr().err

    assert value == "0"
    assert "[FALLBACK][config.get.missing]" in captured
    assert "SongQueueLimit" in captured


def test_config_invalid_boolean_emits_fallback_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("METAFINDER_FALLBACK_WARN", "1")

    cfg_path = Path(tmp_path) / "config.ini"
    cfg_path.write_text("[IterationEngine]\nMetaFinder=not_a_bool\n", encoding="utf-8")

    from gear_optimizer.core.config import load_config

    cfg = load_config(str(cfg_path))
    capsys.readouterr()

    value = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
    captured = capsys.readouterr().err

    assert value is False
    assert "[FALLBACK][config.getboolean.invalid]" in captured
    assert "MetaFinder" in captured


def test_env_invalid_int_emits_fallback_warning(monkeypatch, capsys):
    monkeypatch.setenv("METAFINDER_FALLBACK_WARN", "1")
    monkeypatch.setenv("METAFINDER_TEST_BAD_INT", "abc")

    from gear_optimizer.core.env_config import _env_int

    capsys.readouterr()
    value = _env_int("METAFINDER_TEST_BAD_INT", 7)
    captured = capsys.readouterr().err

    assert value == 7
    assert "[FALLBACK][env.int.invalid]" in captured
    assert "METAFINDER_TEST_BAD_INT" in captured
