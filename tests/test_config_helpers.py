import configparser

from gear_optimizer.core.config import (
    AppRuntimeSettings,
    CalculateSongSettings,
    GASettings,
    GPUExecutionSettings,
    InflightSettings,
    load_config,
    read_fg_candidate_limit,
    read_fg_search_radius,
    read_fg_solver_mode,
    read_outer_search_engine,
    read_iteration_engine_settings,
)


def _build_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read_dict(
        {
            "IterationEngine": {
                "MetaFinder": "true",
                "AutoSelectBuffAndColor": "false",
                "ForceGreatsMode": "true",
                "ForceGreatsFinder": "true",
                "ForceGreatsDebug": "false",
                "GPU_Mode": "true",
                "GPU_Native_GA": "true",
                "GPU_SongSlots": "4",
                "InFlight_GA_QueueMult": "7",
                "GPU_GA_TournamentK": "9",
                "GPU_GA_MutationRate": "1.5",
                "GPU_GA_ImmigrantRate": "-1",
                "GPU_GA_EliteCount": "-2",
                "GPU_GA_NoveltyRepairAttempts": "9",
                "GAConvergenceTrace": "true",
                "GAConvergenceTraceEvery": "0",
                "GAConvergenceTraceOutDir": "",
                "GAConvergenceTraceSongFilter": "pytest",
                "GA_Depth": "0",
                "GA_MultiStart": "0",
                "InFlightSongs": "-3",
                "InFlightInstances": "0",
                "InFlight_RamMode": "true",
                "InFlight_SongFileCacheMax": "-1",
                "TeamBuff_BaseCalcSongCacheMax": "5",
                "UseEvolutionDB": "false",
                "LoopForever": "true",
                "EvalCPUCores": "-1",
                "SongQueueLimit": "5",
                "IgnoreResumeQueue": "true",
                "SongRepeats": "0",
                "BundleSongRepeats": "false",
                "LoopRestartWaitSec": "99.5",
                "FG_CandidateLimit": "9999",
                "FG_SearchRadius": "",
                "OuterSearchEngine": "unsupported",
                "FG_SolverMode": "exact_dp",
            },
            "CalculateSong": {
                "Difficulty": "",
                "Song_Name": "pytest song",
                "TargetPrimary": "",
                "TargetSecondary": "Rush",
            },
            "ForceGreats": {
                "NonFever1": "0",
                "NonFever2": "3",
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

    assert gpu.gpu_mode is True
    assert gpu.gpu_native_ga is True
    assert gpu.gpu_song_slots == 4
    assert gpu.ga_queue_mult == 7

    assert ga.tournament_k == 8
    assert ga.mutation_rate == 1.0
    assert ga.immigrant_rate == 0.0
    assert ga.elite_count == 0
    assert ga.novelty_repair_attempts == 4
    assert ga.convergence_trace is True
    assert ga.convergence_trace_every == 1
    assert ga.convergence_trace_out_dir == "artifacts/ga_trace"
    assert ga.convergence_trace_song_filter == "pytest"
    assert ga.search_depth == 1
    assert ga.multi_start == 1

    assert inflight.songs == 0
    assert inflight.instances == 1
    assert inflight.ram_mode is True
    assert inflight.song_file_cache_max == 0
    assert inflight.team_buff_calc_cache_max == 5
    assert inflight.ga_queue_mult == 7

    assert calc.difficulty == "Hard"
    assert calc.song_name == "pytest song"
    assert calc.target_primary == ""
    assert calc.target_secondary == "Rush"

    assert runtime.use_evolution_db is False
    assert runtime.loop_forever is True
    assert runtime.eval_cpu_cores == 0
    assert runtime.song_queue_limit == 5
    assert runtime.ignore_resume_queue is True
    assert runtime.song_repeats == 1
    assert runtime.bundle_song_repeats is False
    assert runtime.loop_restart_wait_sec == 60.0

    assert ie.meta_finder is True
    assert ie.enable_fever is True
    assert ie.enable_mini is True
    assert ie.enable_gear is True
    assert ie.auto_select_buff_and_color is False
    assert ie.force_greats_mode is True
    assert ie.force_greats_finder is False
    assert ie.force_greats_debug is False
    assert ie.force_greats_config == [0, 3]
    assert ie.manual_force_greats is True

    assert read_fg_candidate_limit(cfg, default=51, min_limit=1) == 5000
    assert read_fg_search_radius(cfg) is None
    assert read_outer_search_engine(cfg, default="ga") == "ga"
    assert read_fg_solver_mode(cfg, default="finder") == "finder"


def test_read_iteration_engine_settings_warns_on_invalid_boolean(monkeypatch, capsys):
    monkeypatch.setenv("METAFINDER_FALLBACK_WARN", "1")

    cfg = configparser.ConfigParser()
    cfg.read_dict({"IterationEngine": {"MetaFinder": "not-a-bool"}})

    capsys.readouterr()
    settings = read_iteration_engine_settings(cfg)
    captured = capsys.readouterr().err

    assert settings.meta_finder is False
    assert "[FALLBACK][config.getboolean.invalid]" in captured


class TestExtendsChain:
    def test_extends_layering_child_overrides_parent(self, tmp_path):
        parent = tmp_path / "base.ini"
        parent.write_text(
            "[IterationEngine]\n"
            "MetaFinder = true\n"
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
        assert cfg.getboolean("IterationEngine", "MetaFinder") is True
        assert cfg.getint("IterationEngine", "SongQueueLimit") == 3
        assert cfg.getint("IterationEngine", "GA_SearchDepth") == 500

    def test_extends_grandparent_layered(self, tmp_path):
        grandparent = tmp_path / "root.ini"
        grandparent.write_text(
            "[IterationEngine]\n"
            "MetaFinder = true\n"
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
        assert cfg.getboolean("IterationEngine", "MetaFinder") is True

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
        parent.write_text("[IterationEngine]\nMetaFinder=true\n", encoding="utf-8")
        child = tmp_path / "child.ini"
        child.write_text("[IterationEngine]\n_extends = base.ini\nSongQueueLimit=3\n", encoding="utf-8")
        cfg = load_config(str(child))
        assert not cfg.has_option("IterationEngine", "_extends")

    def test_extends_sections_merged_across_files(self, tmp_path):
        parent = tmp_path / "base.ini"
        parent.write_text(
            "[IterationEngine]\n"
            "MetaFinder = true\n"
            "SongQueueLimit = 10\n\n"
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
            "[IterationEngine]\nMetaFinder = true\n",
            encoding="utf-8",
        )
        cfg = load_config(str(single))
        assert cfg.getboolean("IterationEngine", "MetaFinder") is True
