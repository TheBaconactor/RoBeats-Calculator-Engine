from pathlib import Path

from gear_optimizer.gamedata import load_gears, load_minis, load_stat_curves, song_minis
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.pipeline.results import gem_allocation
from gear_optimizer.settings import paths
from gear_optimizer.solver.scoring.fever_solver import exact_climb, solve_best_fever_combination_batch
from gear_optimizer.stats import GEM_KINDS, apply_gems, gems, total


def _gems(allocation) -> tuple[int, ...]:
    return tuple(allocation[k] for k in GEM_KINDS)


def test_exact_climb_moves_one_gem_at_a_time_scoring_every_row_still_improving_in_one_batch():
    calls = []

    def fever_fill_only(rows):  # an exact scorer that rewards Fever Fill Rate only (3 per gem)
        calls.append(len(rows))
        return [row["Fever Fill Rate"] for row in rows]

    pre = [total({"Fever Fill Rate": 10}), total({"Rush": 5})]
    starts = [_gems(gems(fm=2, ff=87, element=1)), _gems(gems(ff=90))]
    got = exact_climb(pre, starts, "Rush", fever_fill_only)
    assert got == ([_gems(gems(ff=90))] * 2, [10 + 270, 270])
    # The start scores, then one batch per step: 3 improving steps for the first row (the second stops after its
    # first step's moves) and the step where no move improves.
    assert len(calls) == 5 and calls[0] == 2


def test_exact_climb_keeps_the_search_allocation_when_no_move_strictly_improves():
    start = _gems(gems(fm=20, ff=6, element=64))
    assert exact_climb([total({"Rush": 100})], [start], "Rush", lambda rows: [7] * len(rows)) == ([start], [7])


def test_real_song_gem_search_climbs_past_a_float32_near_tie():
    """Kanpai (Hard), baseline T5: the GPU search, ranking in float32, picks 7 FM / 19 FF / 64 element (float32
    66,025,156, exact 66,023,473); moving one element gem to Fever Fill Rate scores 66,024,847."""
    from gear_optimizer.solver.song_preparation import prepare_song
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    song = prepare_song(str(Path(__file__).resolve().parents[1] / "Data" / "Hard" / "Kanpai (Hard) by Kagi.txt"))
    curves = load_stat_curves(paths().stats_txt)
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
    assert (gem_allocation(result, "Vibe"), result["Score"]) == (_gems(best), 66024847)
    assert result["Stats"] == apply_gems(pre_gem, best, "Vibe")
