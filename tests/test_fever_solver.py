from pathlib import Path

from gear_optimizer.gamedata import load_gears, load_minis, stat_curves, song_minis
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.settings import paths
from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination_batch
from gear_optimizer.stats import GEM_KINDS, apply_gems, gems, total


def _gems(allocation) -> tuple[int, ...]:
    return tuple(allocation[k] for k in GEM_KINDS)


def test_real_song_gem_search_finds_the_exact_optimum_past_a_float32_near_tie():
    """Kanpai (Hard), baseline T5: a float32 ranking prefers 7 FM / 19 FF / 64 element (float32 66,025,156, exact
    66,023,473); the exact optimum moves one element gem to Fever Fill Rate (66,024,847)."""
    from gear_optimizer.chart import load_chart
    from gear_optimizer.solver.timing_envelope import time_song
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    song = time_song(load_chart(Path(__file__).resolve().parents[1] / "Data" / "Hard" / "Kanpai (Hard) by Kagi.txt"), "precise")
    curves = stat_curves()
    build_or_load_timeline_frontier_payload(song, curves)
    gears = load_gears(paths().gears_csv)
    view = {m.name: m for m in song_minis(load_minis(paths().minis_csv).values(), song.chart.name, "Vibe", "Vibe")}
    gear = (
        "The Games: Hidden Shine",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Vibe Ringleader's Harmonica",
        "Legendary Marshall's Coat",
        "The Games: Cape",
        "Legendary Musketeer's Trousers",
    )
    minis = ("Electroman", "Ringmaster Roxie", "Kagi")
    pre_gem = total(baseline_fixed_stats(song.chart), *(gears[n].stats for n in gear), *(view[n].stats for n in minis))
    (result,) = solve_best_fever_combination_batch([pre_gem], song, curves, selected_color="Vibe")
    best = gems(fm=7, ff=20, element=63)
    assert (result.gems, result.score, result.stats) == (_gems(best), 66024847, apply_gems(pre_gem, best, "Vibe"))
