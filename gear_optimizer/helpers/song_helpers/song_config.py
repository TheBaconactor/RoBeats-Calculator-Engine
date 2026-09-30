"""The optimizer's starting stats for a song: the baseline TeamBuff on the song's primary color."""

from ...chart import Chart
from ...core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF, team_buff_effect

_FIXED_STAT_KEYS = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
)


def baseline_fixed_stats(chart: Chart) -> dict[str, int]:
    """Stats every loadout starts from: zero, plus the baseline TeamBuff on the song's primary color."""
    primary_color = chart.primary
    fixed_stats = dict.fromkeys(_FIXED_STAT_KEYS, 0)
    for stat_name, delta in team_buff_effect(OPTIMIZER_BASELINE_TEAM_BUFF, primary_color).items():
        fixed_stats[stat_name] += int(delta)
    return fixed_stats
