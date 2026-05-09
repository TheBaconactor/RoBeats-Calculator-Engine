import os
import sys
from pathlib import Path

import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.slow]


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_exact_skyline_beats_or_matches_ga_real_song():
    """Real-data parity gate: exact skyline must be >= GA on the same chart."""

    from gear_optimizer.core.config import load_config, load_paths_cache
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.helpers.song_helpers import setup_song_config
    from gear_optimizer.helpers.ga_helpers import initialize_pools
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.exact_skyline import solve_exact_skyline
    from gear_optimizer.solver.genetic import solve_coevolution_genetic

    song_path = Path("Data/Hard/00 (Hard) by garlagan.txt")
    if not song_path.exists():
        pytest.skip("Real song file not present in workspace")

    cfg = load_config("config.ini")

    # Force GPU usage (GPU-only policy) and deterministic timeline.
    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", "true")

    if not cfg.has_section("HumanHitSim"):
        cfg.add_section("HumanHitSim")
    cfg.set("HumanHitSim", "Enabled", "false")
    cfg.set("HumanHitSim", "Seed", "1")

    # Ensure manual gems/overflow are off for stable comparisons.
    if not cfg.has_section("UserInputStatsGems"):
        cfg.add_section("UserInputStatsGems")
    for key in ["perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"]:
        cfg.set("UserInputStatsGems", key, "0")

    if not cfg.has_section("ElementalGems"):
        cfg.add_section("ElementalGems")
    for key in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
        cfg.set("ElementalGems", key, "0")

    # Keep GA small-ish; exact solver ignores ga_depth.
    ga_depth = 15
    ga_seed = 123

    paths = load_paths_cache() or {}

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g.get("Name", ""): g for g in all_gears if g.get("Name")}
    minis_by_name = {m.get("Name", ""): m for m in all_minis if m.get("Name")}

    stats_table = read_table(str(paths.get("Stats", "") or ""))
    if not stats_table:
        pytest.skip("Stats table missing; cannot build ref_arrays")

    from gear_optimizer.core.constants import TOTAL_ROWS
    import numpy as np

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        tmp = []
        for v in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(v)
            try:
                val = float(stats_table[lookup_index][i])
            except Exception:
                val = 0.0
            tmp.append(val)
        ref_arrays[name] = np.asarray(tmp, dtype=np.float32)

    cfg_dict = cfg_to_dict(cfg)
    base_calc_song = get_base_calc_song(str(song_path), cfg_dict)
    calc_song = clone_calc_song(base_calc_song)

    # Ensure chart_timestamps exists (matches process_song_task behavior).
    song_data = calc_song.get("song_data", {}) or {}
    if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
        song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float32)

    auto_buff = cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False)
    (
        ga_settings,
        fixed_stats,
        _current_gear_stats,
        _current_gear_list,
        _current_mini_stats,
        _current_mini_list,
        *_rest,
    ) = setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)

    # Fix minis to a deterministic, valid triple so the exact solver finishes quickly.
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    p_color = str((calc_song or {}).get("metadata", {}).get("Primary Color", "Rush") or "Rush")
    s_color = str((calc_song or {}).get("metadata", {}).get("Secondary Color", "") or "")
    _gear_pool, mini_pool, *_ = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
    assert mini_pool and len(mini_pool) >= 3
    fixed_minis = sorted(list(mini_pool), key=lambda m: str(m.get("Name", "") or ""))[:3]

    ga_best_data, *_ = solve_coevolution_genetic(
        cfg,
        fixed_stats,
        paths,
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        optimize_gear=True,
        optimize_minis=False,
        fixed_gear=None,
        fixed_minis=fixed_minis,
        ga_depth=int(ga_depth),
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=lambda _m: None,
        executor=None,
        known_loadouts=None,
        song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
        ga_seed=int(ga_seed),
    )
    ga_score = int((ga_best_data or {}).get("BaseScore") or (ga_best_data or {}).get("Score") or 0)

    exact_best_data, *_ = solve_exact_skyline(
        cfg,
        fixed_stats,
        paths,
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        optimize_gear=True,
        optimize_minis=False,
        fixed_gear=None,
        fixed_minis=fixed_minis,
        ga_depth=int(ga_depth),
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=lambda _m: None,
        executor=None,
        known_loadouts=None,
        song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
        ga_seed=int(ga_seed),
    )
    exact_score = int((exact_best_data or {}).get("BaseScore") or (exact_best_data or {}).get("Score") or 0)

    assert exact_score >= ga_score
