import configparser

from gear_optimizer.core.config import (
    AppRuntimeSettings,
    CalculateSongSettings,
    GASettings,
    GPUExecutionSettings,
    InflightSettings,
    read_fg_candidate_limit,
    read_fg_search_radius,
    read_fg_solver_mode,
    read_iteration_engine_settings,
    read_outer_search_engine,
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
