import random


def test_extract_base_stats_roundtrip_fuzz():
    """
    Invariant/property test:
    - Start with base stats
    - Apply gem contributions (PP/CM/FM/FT/FF/Overflow)
    - _extract_base_stats() must recover the original base stats

    This protects downstream FG logic and DB persistence from "double-counting"
    or stale/mis-applied gem contributions.
    """
    from gear_optimizer.core.constants import (
        ELEMENTAL_GEM_SCALE,
        GEM_SCALE_FEVER,
        GEM_SCALE_NORMAL,
        GEM_STAT_TO_ELEMENT_SCALE,
    )
    from gear_optimizer.solver.scoring.force_greats import _extract_base_stats

    rng = random.Random(0)
    selected_color = "Rush"

    for _ in range(100):
        base_stats = {
            "Perfect Points": rng.randint(0, 160),
            "Combo Multiplier": rng.randint(0, 160),
            "Fever Multiplier": rng.randint(0, 160),
            "Fever Fill Rate": rng.randint(0, 160),
            "Fever Time": rng.randint(0, 160),
            "Rush": rng.randint(0, 900),
            "Flow": rng.randint(0, 900),
            "Beat": rng.randint(0, 900),
            "Vibe": rng.randint(0, 900),
            "Chill": rng.randint(0, 900),
        }

        gem_counts = {
            "Perfect Points": rng.randint(0, 25),
            "Combo Multiplier": rng.randint(0, 25),
            "Fever Multiplier": rng.randint(0, 25),
            "Element": rng.randint(0, 80),
        }
        ft_gems = rng.randint(0, 25)
        ff_gems = rng.randint(0, 25)

        stats_with_gems = dict(base_stats)
        stats_with_gems["Perfect Points"] += gem_counts["Perfect Points"] * GEM_SCALE_NORMAL
        stats_with_gems["Combo Multiplier"] += gem_counts["Combo Multiplier"] * GEM_SCALE_NORMAL
        stats_with_gems["Fever Multiplier"] += gem_counts["Fever Multiplier"] * GEM_SCALE_FEVER
        stats_with_gems["Fever Time"] += ft_gems * GEM_SCALE_FEVER
        stats_with_gems["Fever Fill Rate"] += ff_gems * GEM_SCALE_FEVER

        stats_with_gems["Chill"] += gem_counts["Perfect Points"] * GEM_STAT_TO_ELEMENT_SCALE
        stats_with_gems["Flow"] += gem_counts["Combo Multiplier"] * GEM_STAT_TO_ELEMENT_SCALE
        stats_with_gems["Rush"] += gem_counts["Fever Multiplier"] * GEM_STAT_TO_ELEMENT_SCALE
        stats_with_gems["Beat"] += ft_gems * GEM_STAT_TO_ELEMENT_SCALE
        stats_with_gems["Vibe"] += ff_gems * GEM_STAT_TO_ELEMENT_SCALE
        stats_with_gems[selected_color] += gem_counts["Element"] * ELEMENTAL_GEM_SCALE

        recovered = _extract_base_stats(
            stats_with_gems,
            gem_counts,
            selected_color,
            ft_gems,
            ff_gems,
        )
        assert recovered == base_stats

