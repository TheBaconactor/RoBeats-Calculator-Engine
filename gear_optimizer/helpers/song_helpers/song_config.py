"""
Song Helpers - Song Config - Song configuration setup.

This module provides configuration operations:
- setup_song_config: Setup configuration, load current stats
"""

from ...data.csv_parser import get_fixed_stats, get_config_gear_stats, get_config_mini_stats
from ...core.config import read_iteration_engine_settings
from ...core.team_buff import resolve_baseline_team_buff_from_cfg, team_buff_effect


def apply_baseline_team_buff_config(cfg, calc_song) -> tuple[str, str]:
    """Apply the canonical optimizer baseline TeamBuff to the live per-song config."""
    p_col = calc_song["metadata"].get("Primary Color", "Rush")
    if not cfg.has_section("TeamContributionBuffConstant"):
        cfg.add_section("TeamContributionBuffConstant")
    team_buff = resolve_baseline_team_buff_from_cfg(cfg, default="T5")
    cfg.set("TeamContributionBuffConstant", "TeamColor", p_col)
    cfg.set("TeamContributionBuffConstant", "TeamBuff", team_buff)
    return team_buff, p_col


def assert_fixed_stats_include_baseline_team_buff(
    fixed_stats: dict,
    *,
    team_buff: str,
    team_color: str,
) -> None:
    """Fail loudly if the starting stat surface lost the canonical TeamBuff."""
    expected = team_buff_effect(team_buff, team_color)
    for stat_name, delta in expected.items():
        actual = fixed_stats.get(stat_name, 0) if isinstance(fixed_stats, dict) else 0
        try:
            actual_i = int(actual or 0)
        except (TypeError, ValueError) as exc:
            raise AssertionError(f"Baseline TeamBuff stat {stat_name!r} is not an integer: {actual!r}") from exc
        if actual_i < int(delta):
            raise AssertionError(
                "Optimizer starting stats are missing the canonical TeamBuff "
                f"({team_buff}/{team_color}: {stat_name} expected at least {delta}, got {actual_i})."
            )


def setup_song_config(cfg, calc_song, paths, gears_by_name, minis_by_name):
    """
    Setup configuration, auto-buff, load current stats.

    Args:
        cfg: Configuration object
        calc_song: Song calculation data
        paths: Path configuration
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name

    Returns:
        tuple: (fixed_stats, current_gear_stats, current_gear_list,
                current_mini_stats, current_mini_list)
    """
    read_iteration_engine_settings(cfg)
    team_buff, team_color = apply_baseline_team_buff_config(cfg, calc_song)
    # Keep auto-buff selection silent so the UI stays clean.

    fixed_stats = get_fixed_stats(cfg)
    assert_fixed_stats_include_baseline_team_buff(
        fixed_stats,
        team_buff=team_buff,
        team_color=team_color,
    )

    # Load Current Config for Seeding / Fallback
    current_gear_stats, current_gear_list = get_config_gear_stats(cfg, paths, gears_by_name)
    current_mini_stats, current_mini_list = get_config_mini_stats(cfg, paths, minis_by_name)

    return (
        fixed_stats,
        current_gear_stats,
        current_gear_list,
        current_mini_stats,
        current_mini_list,
    )
