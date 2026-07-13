from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_entry_names
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
from gear_optimizer.solver.scoring.stats_scoring import _force_greats_counts_to_dict
from gear_optimizer.solver.taichi_gem.force_greats import (
    FgResponseFrontierSolveResult,
    reconstruct_force_greats_response_trace,
)
from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
    activation_hit_is_reachable_weighted_lane_aware,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import FgTraceEdgeOptionsCache

from .planner import FgResponseFrontierPreparedPlan
from .physical_replay import validate_force_greats_physical_replay


@dataclass(slots=True)
class FgTraceMaterializationCache:
    """Validated trace/edge cache bound to one exact calc-song owner."""

    traces: dict[Any, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    edge_options: FgTraceEdgeOptionsCache = field(default_factory=FgTraceEdgeOptionsCache)
    _calc_song_owner: dict[str, Any] | None = None

    def bind(self, calc_song: dict[str, Any]) -> None:
        if self._calc_song_owner is None:
            self._calc_song_owner = calc_song
        elif self._calc_song_owner is not calc_song:
            raise ValueError("FG trace materialization cache cannot be reused across calc-song owners")


def _assert_trace_hit_time_reachable(frontier_trace, song_inputs, *, raw_fever_fill: float) -> None:
    """FAIL LOUD if a persisted activation is not input-engine reachable.

    This is the persistence-side invariant for the canonical owner: the activation clock and drain
    window must be produced by the same weighted, lane-aware hit-time walk the surface prices. It never
    mutates the surface; a rejection here means the producer emitted a phantom surface and must be fixed.
    """
    ts = np.asarray(song_inputs.timestamps, dtype=np.float32).reshape(-1)
    pc = np.asarray(song_inputs.perfect_candidates, dtype=np.float32).reshape(-1)
    gc = np.asarray(song_inputs.great_candidates, dtype=np.float32).reshape(-1)
    pf = np.asarray(song_inputs.perfect_floor, dtype=np.float32).reshape(-1)
    gf = np.asarray(song_inputs.great_floor, dtype=np.float32).reshape(-1)
    lanes = np.asarray(song_inputs.lanes, dtype=np.int32).reshape(-1)
    n = int(ts.shape[0])
    if any(int(arr.shape[0]) != n for arr in (pc, gc, pf, gf, lanes)):
        raise ValueError("FG persist guard: timing arrays and lanes must match timestamps")

    for row in frontier_trace:
        a = int(row["activation_index"])
        if not (0 <= a < n):
            continue
        section_start = max(0, int(row.get("forced_start_index", 0)))
        forced_start = max(0, int(row.get("forced_run_start_index", section_start)))
        forced_count = max(0, int(row.get("forced_run_count", row.get("forced_prefix_count", 0))))
        forced_end = min(n, forced_start + forced_count)
        lo = pf.copy()
        hi = pc.copy()
        units = np.ones((n,), dtype=np.float32)
        if forced_end > forced_start:
            lo[forced_start:forced_end] = gf[forced_start:forced_end]
            hi[forced_start:forced_end] = gc[forced_start:forced_end]
            units[forced_start:forced_end] = np.float32(0.5)
        if str(row.get("activation_judgment")) == "late_great":
            lo[a] = gf[a]
            hi[a] = gc[a]
            units[a] = np.float32(0.5)
        h_a = float(row.get("activation_hit_window_upper_ms", float(hi[a]) * 1000.0)) / 1000.0
        if not activation_hit_is_reachable_weighted_lane_aware(
            activation_index=a,
            activation_hit_timestamp=h_a,
            low_hit_timestamps=lo,
            high_hit_timestamps=hi,
            lanes=lanes,
            fill_units=units,
            fever_fill_denom=float(raw_fever_fill),
            section_start=section_start,
            section_end=n,
        ):
            raise ValueError(
                f"FG persist guard: activation @{a} (section {row.get('section')}, "
                f"judgment={row.get('activation_judgment')}) is not reachable under the weighted, "
                f"lane-aware input-engine owner. The frontier build must foreclose this; a trace "
                f"reaching persistence with it is a producer regression, not a persist fixup."
            )


def materialize_force_payload_from_response_frontier(
    *,
    eval_data: dict[str, Any],
    base_stats: dict[str, Any],
    paired_base_score: int,
    selected_element: str,
    result: FgResponseFrontierSolveResult,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    reconstruction_frontier=None,
    trace_cache: FgTraceMaterializationCache | None = None,
) -> dict[str, Any]:
    if trace_cache is not None:
        trace_cache.bind(calc_song)
    frontier = reconstruction_frontier or result.frontier
    song_inputs = extract_fg_song_inputs(calc_song)
    if trace_cache is not None:
        trace_cache.edge_options.bind_owner(calc_song, note_count=len(song_inputs.timestamps))
    song_lanes = getattr(song_inputs, "lanes", None)
    if song_lanes is None:
        raise ValueError("FG response materialization requires song input lanes")
    non_fever_base = int(frontier.non_fever_base)
    surface = result.surface
    # Memoize the trace DFS across the loadouts materialized for one song: the trace is a pure
    # function of its inputs but is recomputed once per kept loadout today, and that DFS (with
    # its per-section centered-witness) is the dominant post-score host cost. The key MUST
    # include raw_fever_fill / non_fever_base -- they build the action table and vary per
    # candidate via the Fever Fill stat, so a surface-only key would be wrong -- while the
    # song-level timestamp/floor inputs are constant across the calls sharing one trace_cache
    # and are excluded. With no cache supplied this is the original single-shot behavior with
    # zero added work: no key, no lookup, no copy.
    base_trace = None
    trace_key = None
    trace_is_validated = False
    if trace_cache is not None:
        trace_key = (
            non_fever_base,
            (
                int(surface.fever0), int(surface.fever1), int(surface.fever2), int(surface.fever3),
                int(surface.great0), int(surface.great1), int(surface.great2), int(surface.great3),
                int(surface.body_fever), int(surface.body_great), int(surface.body_fever_great),
            ),
            float(result.raw_fever_fill),
            float(result.real_fever_time),
            bool(song_inputs.use_forced_great_timing),
        )
        base_trace = trace_cache.traces.get(trace_key)
        trace_is_validated = base_trace is not None
    if base_trace is None:
        base_trace = reconstruct_force_greats_response_trace(
            non_fever_base=non_fever_base,
            target_surface=surface,
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.perfect_floor,
            great_floor_timestamps=song_inputs.great_floor,
            lanes=song_lanes,
            raw_fever_fill=float(result.raw_fever_fill),
            real_fever_time=float(result.real_fever_time),
            use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
            edge_options_cache=None if trace_cache is None else trace_cache.edge_options,
        )
    # Validate before publishing into the song-local cache. A cache hit therefore proves this
    # exact immutable trace already crossed the persist-time reachability barrier; repeating the
    # chart-wide guard for every loadout with the same semantic trace adds no independent check.
    if not trace_is_validated:
        _assert_trace_hit_time_reachable(base_trace, song_inputs, raw_fever_fill=float(result.raw_fever_fill))
        song_data = calc_song.get("song_data")
        if not isinstance(song_data, dict):
            raise ValueError("FG response materialization requires canonical song_data")
        note_types = song_data.get("note_types")
        if note_types is None:
            raise ValueError("FG response materialization requires chart note_types")
        validate_force_greats_physical_replay(
            frontier_trace=base_trace,
            surface=surface,
            timestamps=song_inputs.timestamps,
            note_types=note_types,
            lanes=song_lanes,
            raw_fever_fill=float(result.raw_fever_fill),
            real_fever_time=float(result.real_fever_time),
        )
        if trace_cache is not None:
            trace_cache.traces[trace_key] = base_trace
    # On the cache path, hand each payload fresh per-row dicts (the cached base_trace is never
    # handed out directly, so it can't be mutated downstream); with no cache, return as-is,
    # exactly like before.
    frontier_trace = base_trace if trace_cache is None else tuple(dict(row) for row in base_trace)
    trace_counts = tuple(int(row["forced_count"]) for row in frontier_trace)
    if result.forced_counts:
        forced_counts = tuple(int(v) for v in result.forced_counts)
        if forced_counts != trace_counts:
            raise ValueError("ForceGreats response frontier forced_counts do not match the reconstructed trace")
    else:
        forced_counts = trace_counts
    config = _force_greats_counts_to_dict(list(forced_counts), max(2, len(forced_counts)))
    paired_base = safe_int(paired_base_score, 0)
    if paired_base <= 0:
        raise ValueError("ForceGreats response frontier is missing paired source base score.")
    final_score_obj = score_force_greats_response_surface_exact(result.stats, calc_song, ref_arrays, result.surface)
    if final_score_obj is None:
        raise ValueError("ForceGreats response frontier exact surface replay failed")
    final_score = int(final_score_obj)

    payload = dict(eval_data)
    payload["BaseStats"] = dict(base_stats)
    payload["Stats"] = dict(result.stats)
    payload["BaseScore"] = int(paired_base)
    payload["Score"] = int(final_score)
    payload["Selected Element"] = str(selected_element or payload.get("Selected Element", "") or "")
    payload["GemCounts"] = dict(result.gem_counts)
    payload["FT"] = int(result.ft)
    payload["FF"] = int(result.ff)
    payload["forced_counts"] = list(forced_counts)
    payload["response_surface"] = [
        int(result.surface.fever0),
        int(result.surface.fever1),
        int(result.surface.fever2),
        int(result.surface.fever3),
        int(result.surface.great0),
        int(result.surface.great1),
        int(result.surface.great2),
        int(result.surface.great3),
        int(result.surface.body_fever),
        int(result.surface.body_great),
        int(result.surface.body_fever_great),
    ]
    payload["ForceGreats"] = {
        "config": config,
        "final_score": int(final_score),
        # Fever-window parameters of this surface (the server's feverFillDenom and the fever
        # duration in seconds). Persisted so the legality audit (tools/dev/audit_loadout_legality.py)
        # can re-derive the canonical fill-crossing / drain for every loadout without re-solving,
        # and so the frontend timing graph can place the fever window. Cheap (two floats), exact.
        "raw_fever_fill": float(result.raw_fever_fill),
        "real_fever_time": float(result.real_fever_time),
        "frontier_trace": list(frontier_trace),
        "frontier_first_surfaces": int(len(frontier.first_frontier)),
        "frontier_states": int(frontier.states_evaluated),
        "frontier_max_state": int(frontier.max_state_frontier),
        "frontier_transitions": int(frontier.transitions_evaluated),
        "non_fever_base": int(frontier.non_fever_base),
    }
    return payload


class FgResultReducer:
    @staticmethod
    def _result_cache(
        plan: FgResponseFrontierPreparedPlan,
        prepared_results: list[list[FgResponseFrontierSolveResult]],
    ) -> dict[tuple[Any, ...], FgResponseFrontierSolveResult]:
        result_cache: dict[tuple[Any, ...], FgResponseFrontierSolveResult] = {}
        if len(prepared_results) != len(plan.prepared_batches):
            raise ValueError("ForceGreats response frontier plan received the wrong number of prepared result batches")
        for prepared, results in zip(plan.prepared_batches, prepared_results, strict=True):
            rows = list(prepared.rows)
            if len(results) != len(rows):
                raise ValueError("ForceGreats response frontier batch returned the wrong number of results")
            for (cache_key, _base_stats), result in zip(rows, results, strict=True):
                result_cache[cache_key] = result
        return result_cache

    @staticmethod
    def materialize(
        plan: FgResponseFrontierPreparedPlan,
        prepared_results: list[list[FgResponseFrontierSolveResult]],
        *,
        skyline: bool = False,
    ) -> list[dict[str, Any]]:
        calc_song = plan.calc_song
        ref_arrays = plan.ref_arrays
        variants: list[dict[str, Any]] = []
        result_cache = FgResultReducer._result_cache(plan, prepared_results)

        pending_variants: list[dict[str, Any]] = []
        for entry, eval_data, selected, base_stats, paired_base_score, cache_key in plan.pending_jobs:
            result = result_cache.get(cache_key)
            if result is None:
                raise ValueError("ForceGreats response frontier batch missed a candidate result")
            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            pending_variants.append(
                {
                    "entry": entry,
                    "eval_data": eval_data,
                    "selected": selected,
                    "base_stats": base_stats,
                    "paired_base_score": int(paired_base_score),
                    "result": result,
                    "gear": gear_names,
                    "minis": mini_names,
                    "fg_score": int(result.best_score),
                    "_is_ga": str(entry.get("_source") or "") == "ga",
                }
            )

        pending_jobs = (
            pending_variants
            if skyline
            else sorted(
                pending_variants,
                key=lambda variant: int(variant["fg_score"]),
                reverse=True,
            )[: int(LOADOUTS_PER_SONG_LIMIT)]
        )

        trace_cache = FgTraceMaterializationCache()
        for item in pending_jobs:
            result = item["result"]
            payload = materialize_force_payload_from_response_frontier(
                eval_data=item["eval_data"],
                base_stats=item["base_stats"],
                paired_base_score=int(item["paired_base_score"]),
                selected_element=item["selected"],
                result=result,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                trace_cache=trace_cache,
            )

            entry = item["entry"]
            exact_fg_score = safe_int(payload.get("Score", 0), 0)
            exact_base_score = safe_int(payload.get("BaseScore", 0), 0)
            if skyline:
                variants.append(
                    {
                        "record": entry.get("_candidate_ref"),
                        "data": payload,
                        "force": payload,
                        "base_stats": dict(item["base_stats"]),
                        "selected": item["selected"],
                        "base_score": int(exact_base_score),
                        "fg_score": int(exact_fg_score),
                        "fg_delta": int(exact_fg_score) - int(exact_base_score),
                        "_entry_ref": entry,
                        "_is_skyline": True,
                    }
                )
                continue
            if exact_fg_score <= exact_base_score:
                continue
            if exact_fg_score > safe_int(entry.get("fg_score", 0), 0):
                entry["force"] = payload
                entry["fg_score"] = exact_fg_score
                entry["fg_base_score"] = exact_base_score
            variants.append(
                {
                    "data": payload,
                    "gear": item["gear"],
                    "minis": item["minis"],
                    "score": exact_base_score,
                    "base_score": exact_base_score,
                    "fg_score": exact_fg_score,
                    "_entry_ref": entry,
                    "_is_ga": bool(item["_is_ga"]),
                }
            )

        if skyline:
            return variants
        variants.sort(key=lambda v: int(v.get("fg_score", 0) or 0), reverse=True)
        return variants[: int(LOADOUTS_PER_SONG_LIMIT)]
