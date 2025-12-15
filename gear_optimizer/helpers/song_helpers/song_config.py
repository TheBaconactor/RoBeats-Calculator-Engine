"""
Song Helpers - Song Config - Song configuration setup.

This module provides configuration operations:
- setup_song_config: Setup configuration, auto-buff, load current stats
"""
from ...data.models import GASettings
from ...data.csv_parser import get_fixed_stats, get_config_gear_stats, get_config_mini_stats


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
    ga_settings = GASettings.from_cfg(cfg)

    # MetaFinder controls all optimizers collectively.
    meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
    enable_fever = enable_mini = enable_gear = bool(meta_finder)

    force_greats_mode = cfg.getboolean("IterationEngine", "ForceGreatsMode", fallback=False)
    force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
    # ForceGreatsMode must be enabled for ForceGreatsFinder to work
    if not force_greats_mode:
        force_greats_finder = False

    # Import here to avoid circular dependency
    from ...core.config import load_force_greats_config
    force_greats_config = load_force_greats_config(cfg)
    manual_force_greats = force_greats_mode and any(force_greats_config)

    # --- Auto Select Buff & Color Logic ---
    if auto_buff:
        p_col = calc_song["metadata"].get("Primary Color", "Rush")
        if not cfg.has_section("TeamContributionBuffConstant"):
            cfg.add_section("TeamContributionBuffConstant")
        cfg.set("TeamContributionBuffConstant", "TeamColor", p_col)
        cfg.set("TeamContributionBuffConstant", "TeamBuff", "T5")
        print(f"[Auto-Config] Set Team Buff: T5 | Team Color: {p_col}")

    fixed_stats = get_fixed_stats(cfg)

    # Load Current Config for Seeding / Fallback
    current_gear_stats, current_gear_list = get_config_gear_stats(
        cfg, paths, gears_by_name
    )
    current_mini_stats, current_mini_list = get_config_mini_stats(
        cfg, paths, minis_by_name
    )

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
