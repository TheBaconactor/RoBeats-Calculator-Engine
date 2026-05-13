"""
Song Helpers - Song Config - Song configuration setup.

This module provides configuration operations:
- setup_song_config: Setup configuration, auto-buff, load current stats
"""

from ...data.models import GAEvolutionSettings
from ...data.csv_parser import get_fixed_stats, get_config_gear_stats, get_config_mini_stats
from ...core.config import read_iteration_engine_settings


def setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name):
    """
    Setup configuration, auto-buff, load current stats.

    Args:
        cfg: Configuration object
        calc_song: Song calculation data
        auto_buff: Whether to enable auto buff
        paths: Path configuration
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name

    Returns:
        tuple: (ga_settings, fixed_stats, current_gear_stats, current_gear_list,
                current_mini_stats, current_mini_list, meta_finder, enable_fever,
                enable_mini, enable_gear, force_greats_mode, force_greats_finder,
                force_greats_config, manual_force_greats)
    """
    ga_settings = GAEvolutionSettings.from_cfg(cfg)

    ie = read_iteration_engine_settings(cfg)
    meta_finder = bool(ie.meta_finder)
    enable_fever = bool(ie.enable_fever)
    enable_mini = bool(ie.enable_mini)
    enable_gear = bool(ie.enable_gear)

    force_greats_mode = bool(ie.force_greats_mode)
    force_greats_finder = bool(ie.force_greats_finder)
    force_greats_config = list(ie.force_greats_config or [])
    manual_force_greats = bool(ie.manual_force_greats)

    # --- Auto Select Buff & Color Logic ---
    if auto_buff:
        p_col = calc_song["metadata"].get("Primary Color", "Rush")
        if not cfg.has_section("TeamContributionBuffConstant"):
            cfg.add_section("TeamContributionBuffConstant")
        cfg.set("TeamContributionBuffConstant", "TeamColor", p_col)
        cfg.set("TeamContributionBuffConstant", "TeamBuff", "T5")
        # Keep auto-buff selection silent so the UI stays clean.

    fixed_stats = get_fixed_stats(cfg)

    # Load Current Config for Seeding / Fallback
    current_gear_stats, current_gear_list = get_config_gear_stats(cfg, paths, gears_by_name)
    current_mini_stats, current_mini_list = get_config_mini_stats(cfg, paths, minis_by_name)

    return (
        ga_settings,
        fixed_stats,
        current_gear_stats,
        current_gear_list,
        current_mini_stats,
        current_mini_list,
        meta_finder,
        enable_fever,
        enable_mini,
        enable_gear,
        force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    )
