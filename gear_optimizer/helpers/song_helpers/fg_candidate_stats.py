"""The GA candidates selected for FG, given their gem-applied stats and canonical base scores."""

from __future__ import annotations

from gear_optimizer.gamedata import StatCurves
from ...core.gem_defs import element_gem_count
from ...core.utils import get_selected_element
from ...solver.scoring.exact_rescore import score_stats_exact_batch
from ...solver.timing_envelope import TimedSong
from ...stats import apply_gems, gems


def hydrate_fg_candidate_stats(
    candidates: list[dict],
    *,
    selected_color: str,
    song: TimedSong | None = None,
    curves: StatCurves | None = None,
) -> None:
    """Give the GA candidates selected for FG (decode_gpu_native_ga_runs_payload's: the best with its Data["Stats"],
    the GPU rows with their pre-gem Data["BaseStats"]) their gem-applied Data["Stats"] and selected element. The
    GA's own score is kept as RawGASearchScore; with `song` and `curves` the base score becomes the exact replay of
    the Stats."""
    if not candidates:
        return
    if (song is None) != (curves is None):
        raise ValueError("song and curves must be provided together for canonical FG candidate scores")
    for cand in candidates:
        data = cand["Data"]
        sel = get_selected_element(data) or selected_color
        if data.get("Stats"):
            stats = dict(data["Stats"])
        else:
            data["BaseStats"] = dict(data["BaseStats"])
            counts = data["GemCounts"]
            allocation = gems(
                pp=counts["Perfect Points"],
                cm=counts["Combo Multiplier"],
                fm=counts["Fever Multiplier"],
                ft=data["FT"],
                ff=data["FF"],
                element=element_gem_count(counts),
            )
            stats = apply_gems(data["BaseStats"], allocation, sel)
        score = cand["BaseScore"]
        cand["RawGASearchScore"] = score
        data["RawGASearchScore"] = score
        data["Selected Element"] = sel
        data["Stats"] = stats
    if song is None:
        return
    exact_scores = score_stats_exact_batch([cand["Data"]["Stats"] for cand in candidates], song, curves)
    for cand, score in zip(candidates, exact_scores, strict=True):
        cand["Score"] = cand["BaseScore"] = cand["Data"]["Score"] = cand["Data"]["BaseScore"] = int(score)
