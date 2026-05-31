import configparser
from pathlib import Path

import pytest

from gear_optimizer.core.config import (
    AppRuntimeSettings,
    CalculateSongSettings,
    GASettings,
    GPUExecutionSettings,
    InflightSettings,
    load_config,
    read_fg_candidate_limit,
    read_iteration_engine_settings,
)


def _build_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read_dict(
        {
            "IterationEngine": {
                "ForceGreatsDebug": "false",
                "GPU_SongSlots": "4",
                "InFlight_GA_QueueMult": "7",
                "GPU_GA_TournamentK": "9",
                "GPU_GA_MutationRate": "1.5",
                "GPU_GA_ImmigrantRate": "-1",
                "GPU_GA_EliteCount": "-2",
                "GPU_GA_NoveltyRepairAttempts": "9",
                "GA_SearchDepth": "0",
                "GA_MultiStart": "0",
                "InFlightSongs": "-3",
                "InFlight_SongFileCacheMax": "-1",
                "TeamBuff_BaseCalcSongCacheMax": "5",
                "EvalCPUCores": "-1",
                "SongQueueLimit": "5",
                "IgnoreResumeQueue": "true",
                "SongRepeats": "0",
                "LoopRestartWaitSec": "99.5",
                "FG_CandidateLimit": "9999",
            },
            "CalculateSong": {
                "Difficulty": "",
                "Song_Name": "pytest song",
                "TargetPrimary": "",
                "TargetSecondary": "Rush",
                "LoopForever": "true",
            },
        }
    )
    return cfg


def test_config_parsing_helpers_preserve_clamps_and_defaults():
    cfg = _build_config()

    gpu = GPUExecutionSettings.from_config(cfg)
    ga = GASettings.from_config(cfg)
    inflight = InflightSettings.from_config(cfg)
    calc = CalculateSongSettings.from_config(cfg)
    runtime = AppRuntimeSettings.from_config(cfg)
    ie = read_iteration_engine_settings(cfg)

    assert gpu.gpu_song_slots == 4
    assert gpu.ga_queue_mult == 7

    assert ga.tournament_k == 8
    assert ga.mutation_rate == 1.0
    assert ga.immigrant_rate == 0.0
    assert ga.elite_count == 0
    assert ga.novelty_repair_attempts == 4
    assert ga.search_depth == 1
    assert ga.multi_start == 1

    assert inflight.songs == 0
    assert inflight.song_file_cache_max == 0
    assert inflight.team_buff_calc_cache_max == 5
    assert inflight.ga_queue_mult == 7

    assert calc.difficulty == "All"
    assert calc.song_name == "pytest song"
    assert calc.target_primary == ""
    assert calc.target_secondary == "Rush"

    assert runtime.loop_forever is True
    assert runtime.eval_cpu_cores == 0
    assert runtime.song_queue_limit == 5
    assert runtime.ignore_resume_queue is True
    assert runtime.song_repeats == 1
    assert runtime.loop_restart_wait_sec == 60.0

    assert ie.force_greats_debug is False

    assert read_fg_candidate_limit(cfg, default=51, min_limit=1) == 5000


@pytest.mark.parametrize(
    "cfg_dict",
    [
        {"ForceGreats": {"NonFever1": "1"}},
        {"IterationEngine": {"ForceGreatsManual": "1"}},
        {"IterationEngine": {"FG_SolverMode": "exact_dp"}},
        {"IterationEngine": {"FG_SearchRadius": "-1"}},
    ],
)
def test_non_response_frontier_force_greats_config_is_rejected(cfg_dict):
    cfg = configparser.ConfigParser()
    cfg.read_dict(cfg_dict)

    with pytest.raises(ValueError, match="response-frontier is the only supported ForceGreats scorer"):
        read_iteration_engine_settings(cfg)


def test_repo_config_keeps_song_selection_loop_flag_only():
    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_config(str(repo_root / "config.ini"))

    assert set(cfg.sections()) == {"CalculateSong"}
    assert set(cfg.options("CalculateSong")) == {
        "song_name",
        "difficulty",
        "targetprimary",
        "targetsecondary",
        "loopforever",
    }


def test_loop_forever_is_owned_by_calculate_song_only():
    cfg = configparser.ConfigParser()
    cfg.read_dict({"IterationEngine": {"LoopForever": "true"}})

    assert AppRuntimeSettings.from_config(cfg).loop_forever is False

    cfg.read_dict({"CalculateSong": {"LoopForever": "true"}})
    assert AppRuntimeSettings.from_config(cfg).loop_forever is True


class TestExtendsChain:
    def test_extends_layering_child_overrides_parent(self, tmp_path):
        parent = tmp_path / "base.ini"
        parent.write_text(
            "[CalculateSong]\n"
            "LoopForever = true\n"
            "[IterationEngine]\n"
            "SongQueueLimit = 10\n"
            "GA_SearchDepth = 500\n",
            encoding="utf-8",
        )
        child = tmp_path / "child.ini"
        child.write_text(
            "[IterationEngine]\n"
            "_extends = base.ini\n"
            "SongQueueLimit = 3\n",
            encoding="utf-8",
        )
        cfg = load_config(str(child))
        assert cfg.getboolean("CalculateSong", "LoopForever") is True
        assert cfg.getint("IterationEngine", "SongQueueLimit") == 3
        assert cfg.getint("IterationEngine", "GA_SearchDepth") == 500

    def test_extends_grandparent_layered(self, tmp_path):
        grandparent = tmp_path / "root.ini"
        grandparent.write_text(
            "[CalculateSong]\n"
            "LoopForever = true\n"
            "[IterationEngine]\n"
            "GA_SearchDepth = 100\n"
            "SongQueueLimit = 50\n",
            encoding="utf-8",
        )
        parent = tmp_path / "mid.ini"
        parent.write_text(
            "[IterationEngine]\n"
            "_extends = root.ini\n"
            "GA_SearchDepth = 200\n",
            encoding="utf-8",
        )
        child = tmp_path / "leaf.ini"
        child.write_text(
            "[IterationEngine]\n"
            "_extends = mid.ini\n"
            "SongQueueLimit = 5\n",
            encoding="utf-8",
        )
        cfg = load_config(str(child))
        assert cfg.getint("IterationEngine", "GA_SearchDepth") == 200
        assert cfg.getint("IterationEngine", "SongQueueLimit") == 5
        assert cfg.getboolean("CalculateSong", "LoopForever") is True

    def test_extends_cycle_stops(self, tmp_path):
        a = tmp_path / "a.ini"
        b = tmp_path / "b.ini"
        a.write_text("[IterationEngine]\n_extends = b.ini\nX=1\n", encoding="utf-8")
        b.write_text("[IterationEngine]\n_extends = a.ini\nY=2\n", encoding="utf-8")
        cfg = load_config(str(a))
        assert cfg.getint("IterationEngine", "X") == 1
        assert cfg.getint("IterationEngine", "Y") == 2

    def test_extends_key_removed_from_result(self, tmp_path):
        parent = tmp_path / "base.ini"
        parent.write_text("[CalculateSong]\nLoopForever=true\n", encoding="utf-8")
        child = tmp_path / "child.ini"
        child.write_text("[IterationEngine]\n_extends = base.ini\nSongQueueLimit=3\n", encoding="utf-8")
        cfg = load_config(str(child))
        assert not cfg.has_option("IterationEngine", "_extends")

    def test_extends_sections_merged_across_files(self, tmp_path):
        parent = tmp_path / "base.ini"
        parent.write_text(
            "[IterationEngine]\n"
            "SongQueueLimit = 10\n\n"
            "[CalculateSong]\n"
            "LoopForever = true\n\n"
            "[TeamContributionBuffConstant]\n"
            "TeamBuff = T5\n"
            "TeamColor = Rush\n",
            encoding="utf-8",
        )
        child = tmp_path / "child.ini"
        child.write_text(
            "[IterationEngine]\n"
            "_extends = base.ini\n"
            "SongQueueLimit = 3\n\n"
            "[UserInputStatsGems]\n"
            "perfect_points = 0\n",
            encoding="utf-8",
        )
        cfg = load_config(str(child))
        assert cfg.get("TeamContributionBuffConstant", "TeamBuff") == "T5"
        assert cfg.getint("IterationEngine", "SongQueueLimit") == 3
        assert cfg.getint("UserInputStatsGems", "perfect_points") == 0

    def test_no_extends_loads_normally(self, tmp_path):
        single = tmp_path / "standalone.ini"
        single.write_text(
            "[CalculateSong]\nLoopForever = true\n",
            encoding="utf-8",
        )
        cfg = load_config(str(single))
        assert cfg.getboolean("CalculateSong", "LoopForever") is True

    def test_extends_missing_parent_raises(self, tmp_path):
        child = tmp_path / "child.ini"
        child.write_text(
            "[IterationEngine]\n"
            "_extends = missing_base.ini\n"
            "SongQueueLimit = 3\n",
            encoding="utf-8",
        )
        with pytest.raises(FileNotFoundError, match=r"Config _extends chain broken"):
            load_config(str(child))

    def test_extends_chain_missing_mid_parent_raises(self, tmp_path):
        parent = tmp_path / "base.ini"
        parent.write_text(
            "[CalculateSong]\n"
            "LoopForever = true\n",
            encoding="utf-8",
        )
        mid = tmp_path / "mid.ini"
        mid.write_text(
            "[IterationEngine]\n"
            "_extends = missing.ini\n"
            "SongQueueLimit = 5\n",
            encoding="utf-8",
        )
        child = tmp_path / "child.ini"
        child.write_text(
            "[IterationEngine]\n"
            "_extends = mid.ini\n"
            "SongQueueLimit = 3\n",
            encoding="utf-8",
        )
        with pytest.raises(FileNotFoundError, match=r"Config _extends chain broken"):
            load_config(str(child))
