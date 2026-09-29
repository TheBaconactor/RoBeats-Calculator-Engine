from pathlib import Path

import pytest

from gear_optimizer import settings
from gear_optimizer.settings import RunSettings, read_run_settings, reasoning_search

REPO_ROOT = Path(__file__).resolve().parents[1]


def _config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.ini"
    path.write_text(text, encoding="utf-8")
    return path


def test_repo_config_is_all_defaults():
    assert read_run_settings(REPO_ROOT / "config.ini") == RunSettings()


def test_missing_config_file_is_all_defaults(tmp_path):
    assert read_run_settings(tmp_path / "absent.ini") == RunSettings()


def test_every_key_parses(tmp_path):
    path = _config(
        tmp_path,
        "[CalculateSong]\n"
        "Song_Name = pytest song\n"
        "Difficulty = Hard\n"
        "TargetPrimary = Rush\n"
        "TargetSecondary = Flow|Beat\n"
        "LoopForever = true\n"
        "[IterationEngine]\n"
        "SongRepeats = 4\n"
        "SongQueueLimit = 2\n"
        "IgnoreResumeQueue = yes\n"
        "GA_SearchDepth = 250\n"
        "GA_MultiStart = 6\n"
        "MemorySoftLimitGB = 7.5\n"
        "MemorySoftLimitPercent = 0\n",
    )
    assert read_run_settings(path) == RunSettings(
        song_name="pytest song",
        difficulty="Hard",
        target_primary="Rush",
        target_secondary="Flow|Beat",
        loop_forever=True,
        song_repeats=4,
        song_queue_limit=2,
        ignore_resume_queue=True,
        search_depth=250,
        multi_start=6,
        memory_soft_limit_gb=7.5,
        memory_soft_limit_percent=0.0,
    )


def test_empty_text_value_means_the_default(tmp_path):
    path = _config(tmp_path, "[CalculateSong]\nSong_Name =\nDifficulty =\nTargetPrimary =\n")
    assert read_run_settings(path) == RunSettings()


@pytest.mark.parametrize(
    "text",
    [
        "[IterationEngine]\nInFlightSongs = 4\n",
        "[IterationEngine]\nForceGreatsDebug = true\n",
        "[IterationEngine]\nLoopForever = true\n",
        "[UserInputStatsGems]\nperfect_points = 3\n",
        "[TeamContributionBuffConstant]\nTeamBuff = T5\n",
        "[Gear]\nHat = Crown\n",
        "[ForceGreats]\nNonFever1 = 1\n",
    ],
)
def test_removed_or_unknown_keys_are_errors(tmp_path, text):
    with pytest.raises(ValueError, match="is not a config.ini setting"):
        read_run_settings(_config(tmp_path, text))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[IterationEngine]\nSongRepeats = many\n", "must be an integer"),
        ("[IterationEngine]\nMemorySoftLimitGB = lots\n", "must be a number"),
        ("[CalculateSong]\nLoopForever = maybe\n", "must be true/false"),
        ("[IterationEngine]\nSongRepeats = 0\n", ">= 1"),
        ("[IterationEngine]\nGA_MultiStart = 0\n", ">= 1"),
        ("[IterationEngine]\nSongQueueLimit = -1\n", ">= 0"),
    ],
)
def test_malformed_values_are_errors(tmp_path, text, message):
    with pytest.raises(ValueError, match=message):
        read_run_settings(_config(tmp_path, text))


def test_reasoning_levels_scale_the_default_search():
    assert reasoning_search("default") == (125, 3)
    assert reasoning_search("strong") == (250, 6)
    assert reasoning_search("max") == (500, 12)
    with pytest.raises(KeyError):
        reasoning_search("ultra")


def test_env_switches_parse_strictly(monkeypatch):
    monkeypatch.delenv("GA_SEED", raising=False)
    assert settings.ga_seed() is None
    monkeypatch.setenv("GA_SEED", "1234")
    assert settings.ga_seed() == 1234
    monkeypatch.setenv("GA_SEED", "abc")
    with pytest.raises(ValueError, match="GA_SEED"):
        settings.ga_seed()

    monkeypatch.delenv("METAFINDER_PROGRESS", raising=False)
    assert settings.progress() is None
    monkeypatch.setenv("METAFINDER_PROGRESS", "0")
    assert settings.progress() is False
    monkeypatch.setenv("METAFINDER_PROGRESS", "on")
    assert settings.progress() is True

    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "sometimes")
    with pytest.raises(ValueError, match="ROBEATSMETA_OPTIMIZER_SERVICE_MODE"):
        settings.service_mode()
