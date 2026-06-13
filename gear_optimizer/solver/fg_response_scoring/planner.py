from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.ga_entry_utils import (
    candidate_genome_ids,
    entry_loadout_hash,
    ga_candidate_key,
)
from gear_optimizer.helpers.song_helpers.force_greats.entry_utils import eval_data_from_entry, expected_selected_element
from gear_optimizer.solver.force_greats_common import FG_BASE_STATS7_KEY, extract_base_stats
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
    FgResponseFrontierPackedScoringBatch,
    prepare_force_greats_response_frontier_scoring_batch,
)

@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedBatch:
    rows: tuple[tuple[tuple[Any, ...], dict[str, Any]], ...]
    batch: FgResponseFrontierPackedScoringBatch


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPreparedPlan:
    calc_song: dict[str, Any]
    ref_arrays: dict[str, Any]
    pending_jobs: tuple[tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], int, tuple[Any, ...]], ...]
    prepared_batches: tuple[FgResponseFrontierPreparedBatch, ...]


class FgPlanner:
    @staticmethod
    def _entry_items_from_ga_candidates(ga_candidates, *, ga_registry=None) -> list[tuple[str, dict[str, Any]]]:
        items: list[tuple[str, dict[str, Any]]] = []
        for idx, candidate in enumerate(ga_candidates or []):
            if not isinstance(candidate, dict):
                raise ValueError(f"ForceGreats GA candidate {idx} is not a dict.")
            eval_data = candidate.get("Data")
            if not isinstance(eval_data, dict) or not eval_data:
                raise ValueError(f"ForceGreats GA candidate {idx} is missing Data.")
            genome_ids = candidate_genome_ids(candidate)
            registry_obj = ga_registry if ga_registry is not None else candidate.get("_ga_registry")
            score = int(candidate.get("BaseScore") or candidate.get("Score", 0) or 0)
            if score <= 0:
                raise ValueError(f"ForceGreats GA candidate {idx} is missing a positive BaseScore.")
            entry = {
                "gear": list(candidate.get("Gear") or []),
                "minis": list(candidate.get("Minis") or []),
                "score": int(score),
                "base_score": int(score),
                "details": {},
                "fg_score": int(candidate.get("fg_score", 0) or 0),
                "force": candidate.get("force"),
                "eval_data": eval_data,
                "_source": "ga",
                "_candidate_ref": candidate,
            }
            selected = str(eval_data.get("Selected Element", "") or "")
            if selected:
                entry["selected_element"] = selected
            if genome_ids is not None:
                entry["ga_genome_ids"] = list(genome_ids)
            if registry_obj is not None:
                entry["_ga_registry"] = registry_obj

            key = str(candidate.get("loadout_hash") or "").strip()
            if not key and (entry.get("gear") or entry.get("minis")):
                key = str(entry_loadout_hash(entry) or "")
            if not key and genome_ids is not None:
                key = ga_candidate_key(genome_ids)
            if not key:
                key = f"ga-candidate:{int(idx)}"
            entry["loadout_hash"] = str(key)
            items.append((str(key), entry))
        return items

    @staticmethod
    def _entry_items_from_skyline_candidate_records(
        candidate_records,
        *,
        default_selected_color: str,
    ) -> list[tuple[str, dict[str, Any]]]:
        items: list[tuple[str, dict[str, Any]]] = []
        for idx, record in enumerate(candidate_records or []):
            if not isinstance(record, dict):
                raise ValueError(f"Skyline ForceGreats candidate {idx} is not a dict.")
            eval_data = record.get("data")
            if not isinstance(eval_data, dict) or not eval_data:
                raise ValueError(f"Skyline ForceGreats candidate {idx} is missing data.")
            score = safe_int(record.get("base_score", eval_data.get("BaseScore", eval_data.get("Score", 0))), 0)
            if score <= 0:
                raise ValueError(f"Skyline ForceGreats candidate {idx} is missing a positive base_score.")
            selected = str(eval_data.get("Selected Element", "") or default_selected_color or "")
            entry = {
                "gear": list(record.get("gear") or []),
                "minis": list(record.get("minis") or []),
                "score": int(score),
                "base_score": int(score),
                "details": {},
                "fg_score": safe_int(record.get("fg_score", 0), 0),
                "force": record.get("force"),
                "eval_data": eval_data,
                "selected_element": selected,
                "_source": "skyline",
                "_candidate_ref": record,
                "_skyline_index": int(idx),
            }
            key = str(record.get("loadout_hash") or "").strip() or f"skyline-candidate:{int(idx)}"
            entry["loadout_hash"] = str(key)
            items.append((str(key), entry))
        return items

    @staticmethod
    def base_stats_for_response_frontier(eval_data: dict[str, Any], *, selected: str) -> dict[str, Any]:
        base_stats = eval_data.get("BaseStats")
        if isinstance(base_stats, dict) and base_stats:
            return dict(base_stats)

        stats = eval_data.get("Stats")
        if not isinstance(stats, dict) or not stats:
            from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload

            stats = materialize_stats_from_payload(eval_data, selected_element=selected, mutate_payload=True)
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
    def _device_base_stats7_for_entry(entry: dict[str, Any], eval_data: dict[str, Any]) -> Any:
        """Device base_stats7 for the FG scoring input when the candidate carries one.

        GPU-native GA candidates carry the on-device base_stats7 (decode attaches it to
        ``eval_data``); that vector is the authoritative scoring input for the fused
        handoff. DB-best / skyline / previous-record candidates have no payload row, so
        this returns ``None`` and the canonical constructor derives the 7-vector from
        their ``BaseStats`` dict (see response_frontier_base_components_row). Both are
        canonical sources, distinguished by candidate origin, not a fallback. The
        production GA path additionally asserts presence in
        ``plan_prepared_ga_candidates`` (the only payload-sourced caller)."""
        del entry  # origin is enforced by the production caller, not inferred here
        raw = eval_data.get(FG_BASE_STATS7_KEY)
        if raw is None:
            return None
        seq = tuple(int(v) for v in raw)
        if len(seq) != 7:
            raise ValueError(
                f"FG candidate device base_stats7 must have 7 components, got {len(seq)}"
            )
        return seq

    @staticmethod
    def _paired_base_score_from_entry(entry: dict[str, Any], eval_data: dict[str, Any]) -> int:
        for value in (
            entry.get("fg_base_score"),
            entry.get("base_score"),
            entry.get("score"),
            eval_data.get("fg_base_score"),
            eval_data.get("BaseScore"),
            eval_data.get("base_score"),
            eval_data.get("score"),
        ):
            score = safe_int(value, 0)
            if score > 0:
                return int(score)
        raise ValueError("ForceGreats response frontier candidate is missing paired source base score.")

    @staticmethod
    def _plan_from_items(
        entry_items,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        scoring_bundle=None,
    ) -> FgResponseFrontierPreparedPlan:
        song_inputs = extract_fg_song_inputs(calc_song)
        if int(song_inputs.total_notes) <= 0:
            raise ValueError("ForceGreats response frontier requires a song with at least one note")

        pending_jobs: list[tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], int, tuple[Any, ...]]] = []
        pending_by_selected: dict[str, list[tuple[tuple[Any, ...], dict[str, Any]]]] = {}
        # Per-representative device base_stats7 (or None for dict-sourced candidates),
        # aligned 1:1 with each pending_by_selected[selected] list. This is the Slice 2
        # FG scoring input source: the GPU-native pack kernel's on-device base_stats7,
        # carried through decode on each candidate's eval_data. The full BaseStats dict
        # still drives cache_key dedup + persistence; only the scored 7-vector switches
        # source. base_stats7 is bit-exact equal to the dict-derived 7-vector
        # (tests/test_gpu_base_stats7_equivalence.py).
        base_stats7_by_selected: dict[str, list[Any]] = {}
        pending_keys: set[tuple[Any, ...]] = set()
        for _key, entry in entry_items:
            if not isinstance(entry, dict):
                raise ValueError("ForceGreats response frontier received a non-dict entry.")
            eval_data = eval_data_from_entry(entry, str(meta_primary_color or ""))
            if not isinstance(eval_data, dict) or not eval_data:
                raise ValueError("ForceGreats response frontier entry is missing eval data.")
            selected = expected_selected_element(entry, str(meta_primary_color or ""))
            base_stats = FgPlanner.base_stats_for_response_frontier(eval_data, selected=selected)
            base_stats7 = FgPlanner._device_base_stats7_for_entry(entry, eval_data)
            paired_base_score = FgPlanner._paired_base_score_from_entry(entry, eval_data)
            cache_key = (
                str(selected or ""),
                tuple(sorted((str(key), safe_int(value, 0)) for key, value in base_stats.items())),
            )
            pending_jobs.append((entry, eval_data, selected, base_stats, int(paired_base_score), cache_key))
            if cache_key not in pending_keys:
                pending_keys.add(cache_key)
                pending_by_selected.setdefault(str(selected or ""), []).append((cache_key, base_stats))
                base_stats7_by_selected.setdefault(str(selected or ""), []).append(base_stats7)

        prepared_batches: list[FgResponseFrontierPreparedBatch] = []
        for selected, rows in pending_by_selected.items():
            batch = prepare_force_greats_response_frontier_scoring_batch(
                base_stats_list=[base_stats for _cache_key, base_stats in rows],
                base_stats7_list=list(base_stats7_by_selected.get(selected, [])),
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                selected_color=selected,
                scoring_bundle=scoring_bundle,
            )
            prepared_batches.append(
                FgResponseFrontierPreparedBatch(
                    rows=tuple(rows),
                    batch=batch,
                )
            )

        return FgResponseFrontierPreparedPlan(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            pending_jobs=tuple(pending_jobs),
            prepared_batches=tuple(prepared_batches),
        )

    @staticmethod
    def plan_many(
        ga_candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        ga_registry=None,
        scoring_bundle=None,
    ) -> FgResponseFrontierPreparedPlan:
        return FgPlanner._plan_from_items(
            FgPlanner._entry_items_from_ga_candidates(ga_candidates, ga_registry=ga_registry),
            calc_song,
            ref_arrays,
            meta_primary_color,
            scoring_bundle=scoring_bundle,
        )

    @staticmethod
    def plan_skyline_candidate_records(
        candidate_records,
        calc_song,
        ref_arrays,
        default_selected_color,
        *,
        scoring_bundle=None,
    ) -> FgResponseFrontierPreparedPlan:
        return FgPlanner._plan_from_items(
            FgPlanner._entry_items_from_skyline_candidate_records(
                candidate_records,
                default_selected_color=str(default_selected_color or ""),
            ),
            calc_song,
            ref_arrays,
            default_selected_color,
            scoring_bundle=scoring_bundle,
        )

    @staticmethod
    def plan_prepared_ga_candidates(song, ga_candidates) -> FgResponseFrontierPreparedPlan:
        from gear_optimizer.solver.native_inflight_pipeline import resolve_active_fg_calc_song

        calc_song = resolve_active_fg_calc_song(song)
        if not isinstance(calc_song, dict):
            raise RuntimeError("FG dynamic prep requires a resolved calc song")
        ref_arrays = getattr(getattr(song, "gpu_inputs", None), "ref_arrays", None)
        if not isinstance(ref_arrays, dict):
            raise RuntimeError("FG dynamic prep requires reference arrays")
        return FgPlanner.plan_many(
            ga_candidates,
            calc_song,
            ref_arrays,
            getattr(song.gpu_inputs, "meta_primary_color", ""),
            ga_registry=getattr(song.gpu_inputs, "registry", None),
            scoring_bundle=getattr(song.runtime.fg, "fg_response_scoring_bundle", None),
        )
