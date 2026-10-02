"""FG planning: the GA surface's loadouts as FG jobs, deduplicated into one GPU scoring batch per element."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_candidate_names
from gear_optimizer.pipeline.results import SolvedLoadout
from gear_optimizer.solver.force_greats_common import FG_BASE_STATS7_KEY, extract_base_stats
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
    FgResponseFrontierPackedScoringBatch,
    prepare_force_greats_response_frontier_scoring_batch,
)


@dataclass(frozen=True, slots=True)
class FgJob:
    """One loadout's FG solve: the surface loadout, the element it is scored for, the gem-free stats the gem
    search starts from and the GA base score its result is paired with. Jobs with equal keys share one result."""

    loadout: SolvedLoadout
    selected: str
    base_stats: dict[str, Any]
    paired: int
    key: tuple[Any, ...]  # (selected, sorted base stats)


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedBatch:
    rows: tuple[tuple[tuple[Any, ...], dict[str, Any]], ...]
    batch: FgResponseFrontierPackedScoringBatch


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedPlan:
    song: TimedSong
    curves: StatCurves
    jobs: tuple[FgJob, ...]  # GA surface order
    prepared_batches: tuple[FgResponseFrontierPreparedBatch, ...]


def _device_base_stats7(eval_data: dict[str, Any]) -> tuple[int, ...] | None:
    """The GA's on-device base_stats7 (decode attaches it to the candidate's Data): the scored 7-vector of the
    fused handoff. Absent, the batch derives the vector from BaseStats (bit-identical,
    tests/test_gpu_base_stats7_equivalence.py)."""
    raw = eval_data.get(FG_BASE_STATS7_KEY)
    if raw is None:
        return None
    seq = tuple(int(v) for v in raw)
    if len(seq) != 7:
        raise ValueError(f"FG candidate device base_stats7 must have 7 components, got {len(seq)}")
    return seq


class FgPlanner:
    @staticmethod
    def base_stats_for_response_frontier(eval_data: dict[str, Any], *, selected: str) -> dict[str, Any]:
        base_stats = eval_data.get("BaseStats")
        if isinstance(base_stats, dict) and base_stats:
            return dict(base_stats)

        stats = eval_data.get("Stats")
        if not isinstance(stats, dict) or not stats:
            from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats

            stats = read_visible_stats(eval_data, mutate_payload=True)
        if not isinstance(stats, dict) or not stats:
            raise ValueError("ForceGreats response frontier requires Stats or BaseStats")

        base_stats = extract_base_stats(
            stats,
            eval_data.get("GemCounts") if isinstance(eval_data.get("GemCounts"), dict) else {},
            str(selected or eval_data.get("Selected Element", "") or ""),
            safe_int(eval_data.get("FT", 0), 0),
            safe_int(eval_data.get("FF", 0), 0),
        )
        if not isinstance(base_stats, dict) or not base_stats:
            raise ValueError("ForceGreats response frontier BaseStats extraction failed")
        eval_data["BaseStats"] = dict(base_stats)
        return dict(base_stats)

    @staticmethod
    def plan_many(
        ga_candidates,
        timed_song,
        curves,
        meta_primary_color,
        *,
        ga_registry=None,
        scoring_bundle=None,
    ) -> FgResponseFrontierPreparedPlan:
        if int(timed_song.fg_inputs.total_notes) <= 0:
            raise ValueError("ForceGreats response frontier requires a song with at least one note")
        jobs: list[FgJob] = []
        rows_by_selected: dict[str, list[tuple[tuple[Any, ...], dict[str, Any]]]] = {}
        base_stats7_by_selected: dict[str, list[tuple[int, ...] | None]] = {}
        planned: set[tuple[Any, ...]] = set()
        for idx, candidate in enumerate(ga_candidates):
            eval_data = candidate.get("Data") if isinstance(candidate, dict) else None
            if not isinstance(eval_data, dict) or not (eval_data.get("Stats") or eval_data.get("BaseStats")):
                raise ValueError(f"ForceGreats GA candidate {idx} is missing Data stats.")
            paired = int(candidate.get("BaseScore") or candidate.get("Score", 0) or 0)
            if paired <= 0:
                raise ValueError(f"ForceGreats GA candidate {idx} is missing a positive BaseScore.")
            gear, minis = materialize_candidate_names(candidate, registry=ga_registry)
            selected = str(eval_data.get("Selected Element") or meta_primary_color or "")
            base_stats = FgPlanner.base_stats_for_response_frontier(eval_data, selected=selected)
            key = (selected, tuple(sorted((str(k), safe_int(v, 0)) for k, v in base_stats.items())))
            jobs.append(FgJob(SolvedLoadout(tuple(gear), tuple(minis)), selected, base_stats, paired, key))
            if key not in planned:
                planned.add(key)
                rows_by_selected.setdefault(selected, []).append((key, base_stats))
                base_stats7_by_selected.setdefault(selected, []).append(_device_base_stats7(eval_data))

        prepared_batches = tuple(
            FgResponseFrontierPreparedBatch(
                rows=tuple(rows),
                batch=prepare_force_greats_response_frontier_scoring_batch(
                    base_stats_list=[base_stats for _key, base_stats in rows],
                    base_stats7_list=base_stats7_by_selected[selected],
                    song=timed_song,
                    curves=curves,
                    selected_color=selected,
                    scoring_bundle=scoring_bundle,
                ),
            )
            for selected, rows in rows_by_selected.items()
        )
        return FgResponseFrontierPreparedPlan(
            song=timed_song, curves=curves, jobs=tuple(jobs), prepared_batches=prepared_batches
        )

    @staticmethod
    def plan_prepared_ga_candidates(song, ga_candidates) -> FgResponseFrontierPreparedPlan:
        timed_song = song.gpu_inputs.timed_song
        if timed_song is None:
            raise RuntimeError("FG dynamic prep requires the song's timing")
        curves = getattr(getattr(song, "gpu_inputs", None), "curves", None)
        if curves is None:
            raise RuntimeError("FG dynamic prep requires stat curves")
        return FgPlanner.plan_many(
            ga_candidates,
            timed_song,
            curves,
            song.gpu_inputs.meta_primary_color,
            ga_registry=song.gpu_inputs.registry,
            scoring_bundle=song.runtime.fg.fg_response_scoring_bundle,
        )
