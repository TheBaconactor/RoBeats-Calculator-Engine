from __future__ import annotations

import copy
import json
import os
import threading
import time
import zlib
from collections import OrderedDict
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit, read_fg_search_radius
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT, TOTAL_ROWS
from gear_optimizer.core.fallback_monitor import warn_fallback
from gear_optimizer.core.utils import safe_int
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from gear_optimizer.helpers.song_helpers.fg_combo_booster import prepare_fg_combo_booster_candidates_job
from gear_optimizer.helpers.song_helpers.force_greats.entry_utils import build_fg_group_meta
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn

from gear_optimizer.solver.fever_timeline import get_song_timeline_grid
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.scoring.stats_scoring import fg_baseline_params
from gear_optimizer.solver.genetic import decode_gpu_native_ga_runs_payload

_FG_JIT_WARMED = False
_FG_DB_LOADOUTS_CACHE: "OrderedDict[str, tuple[int, list[dict]]]" = OrderedDict()
_FG_DB_LOADOUTS_CACHE_LOCK = threading.Lock()


def _fg_db_cache_max() -> int:
    try:
        raw = os.environ.get("INFLIGHT_FG_DB_CACHE_MAX")
        if raw is not None and str(raw).strip() != "":
            return max(0, int(raw))
    except Exception:
        pass
    return 256


def _fg_db_cache_get(song_name: str, *, limit: int) -> list[dict] | None:
    key = str(song_name or "").strip()
    if not key:
        return None
    try:
        with _FG_DB_LOADOUTS_CACHE_LOCK:
            entry = _FG_DB_LOADOUTS_CACHE.get(key)
            if entry is None:
                return None
            cached_limit, rows = entry
            if int(cached_limit) < int(limit):
                return None
            _FG_DB_LOADOUTS_CACHE.move_to_end(key)
            return list(rows[: int(limit)])
    except Exception:
        return None


def _fg_db_cache_put(song_name: str, *, limit: int, rows: list[dict]) -> None:
    key = str(song_name or "").strip()
    if not key:
        return
    if not isinstance(rows, list):
        return
    try:
        limit_i = max(0, int(limit))
    except Exception:
        limit_i = 0
    try:
        with _FG_DB_LOADOUTS_CACHE_LOCK:
            prev = _FG_DB_LOADOUTS_CACHE.get(key)
            if prev is not None:
                prev_limit, _prev_rows = prev
                # Keep the wider payload for this song key when possible.
                if int(prev_limit) > int(limit_i):
                    return
            _FG_DB_LOADOUTS_CACHE[key] = (int(limit_i), list(rows))
            _FG_DB_LOADOUTS_CACHE.move_to_end(key)
            max_n = int(_fg_db_cache_max())
            if max_n <= 0:
                _FG_DB_LOADOUTS_CACHE.clear()
                return
            while len(_FG_DB_LOADOUTS_CACHE) > max_n:
                _FG_DB_LOADOUTS_CACHE.popitem(last=False)
    except Exception:
        return


def _truthy(raw: Any) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _cfg_section_ci(cfg_dict: dict, name: str) -> dict:
    if not isinstance(cfg_dict, dict):
        return {}
    if name in cfg_dict and isinstance(cfg_dict.get(name), dict):
        return cfg_dict.get(name) or {}
    target = str(name).lower()
    for key, value in cfg_dict.items():
        if str(key).lower() == target and isinstance(value, dict):
            return value
    return {}


def _cfg_value_ci(section: dict, key: str, default: object = None) -> object:
    if not isinstance(section, dict):
        return default
    if key in section:
        return section.get(key, default)
    target = str(key).lower()
    for cur_key, cur_value in section.items():
        if str(cur_key).lower() == target:
            return cur_value
    return default


def _clone_calc_song_for_hitsim(calc_song: object) -> dict:
    """
    Fast, shallow clone of a calc_song payload for HitSim regime materialization.

    We only need to isolate top-level dicts that HitSim mutates (`metadata`, `song_data`).
    Numpy arrays inside `song_data` are treated as immutable inputs and are replaced (not mutated in-place)
    by the HitSim materializers.

    This avoids `copy.deepcopy(calc_song)` which is expensive for large song payloads.
    """
    if not isinstance(calc_song, dict):
        return {}
    out = dict(calc_song)
    meta0 = calc_song.get("metadata")
    out["metadata"] = dict(meta0) if isinstance(meta0, dict) else {}
    song_data0 = calc_song.get("song_data")
    out["song_data"] = dict(song_data0) if isinstance(song_data0, dict) else {}
    return out


def _candidate_item_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("Name", "") or "")
    return str(item or "")


def _candidate_name_key(candidate: dict) -> tuple[str, ...]:
    if not isinstance(candidate, dict):
        return ()
    gear = list(candidate.get("Gear") or candidate.get("gear") or [])[:6]
    minis = list(candidate.get("Minis") or candidate.get("minis") or [])[:3]
    return tuple([_candidate_item_name(item) for item in gear] + [_candidate_item_name(item) for item in minis])


def _candidate_to_genome_ids(candidate: dict, registry: Any) -> np.ndarray | None:
    if not isinstance(candidate, dict):
        return None
    raw_ids = candidate.get("GenomeIDs")
    if raw_ids is None:
        data = candidate.get("Data") if isinstance(candidate.get("Data"), dict) else candidate.get("data")
        if isinstance(data, dict):
            raw_ids = data.get("GenomeIDs")
    if raw_ids is not None:
        try:
            out = np.asarray(list(raw_ids)[:9], dtype=np.int32)
            if int(out.shape[0]) >= 9 and bool(np.any(out != 0)):
                return out[:9].copy()
        except Exception:
            pass
    if registry is None:
        return None
    item_to_id = getattr(registry, "item_to_id", None)
    if not isinstance(item_to_id, dict):
        return None
    gear = list(candidate.get("Gear") or candidate.get("gear") or [])[:6]
    minis = list(candidate.get("Minis") or candidate.get("minis") or [])[:3]
    out = np.zeros((9,), dtype=np.int32)
    for slot_idx in range(6):
        if slot_idx >= len(gear):
            continue
        name = _candidate_item_name(gear[slot_idx])
        if not name:
            continue
        out[slot_idx] = int(item_to_id.get((slot_idx, name), 0) or 0)
    for mini_idx in range(3):
        if mini_idx >= len(minis):
            continue
        name = _candidate_item_name(minis[mini_idx])
        if not name:
            continue
        out[6 + mini_idx] = int(item_to_id.get((6 + mini_idx, name), 0) or 0)
    if not bool(np.any(out != 0)):
        return None
    return out


def _hitsim_matrix_enabled(song: Any) -> bool:
    cfg_dict = getattr(song, "cfg_dict", {}) or {}
    human_cfg = _cfg_section_ci(cfg_dict, "HumanHitSim")
    return _truthy(_cfg_value_ci(human_cfg, "MatrixAfterRefine", "1"))


def _set_hitsim_matrix_status(song: Any, status: str, reason: str = "", *, context: dict[str, Any] | None = None) -> None:
    try:
        calc_song = getattr(song, "calc_song", None)
        meta = calc_song.get("metadata") if isinstance(calc_song, dict) else None
        if not isinstance(meta, dict):
            return
        meta = dict(meta)
        meta["HumanHitSimRegimeMatrixStatus"] = str(status or "")
        if reason:
            meta["HumanHitSimRegimeMatrixReason"] = str(reason)
        if isinstance(context, dict):
            for key, value in context.items():
                meta[f"HumanHitSimRegimeMatrix{key}"] = value
        calc_song["metadata"] = meta
    except Exception:
        return


def _set_hitsim_continuation_status(song: Any, status: str, reason: str = "", *, context: dict[str, Any] | None = None) -> None:
    try:
        calc_song = getattr(song, "calc_song", None)
        meta = calc_song.get("metadata") if isinstance(calc_song, dict) else None
        if not isinstance(meta, dict):
            return
        meta = dict(meta)
        meta["HumanHitSimContinuationStatus"] = str(status or "")
        if reason:
            meta["HumanHitSimContinuationReason"] = str(reason)
        if isinstance(context, dict):
            for key, value in context.items():
                meta[f"HumanHitSimContinuation{key}"] = value
        calc_song["metadata"] = meta
    except Exception:
        return


def _hitsim_matrix_candidate_limit(song: Any) -> int:
    cfg_dict = getattr(song, "cfg_dict", {}) or {}
    human_cfg = _cfg_section_ci(cfg_dict, "HumanHitSim")
    fallback = safe_int(getattr(song, "cfg_data", {}).get("fg_candidate_limit", FG_CANDIDATE_LIMIT), FG_CANDIDATE_LIMIT)
    limit = safe_int(_cfg_value_ci(human_cfg, "MatrixCandidateLimit", str(int(fallback))), int(fallback))
    if limit <= 0:
        limit = int(fallback)
    return max(1, int(limit))


def _hitsim_matrix_gem_counts(g_pp: int, g_cm: int, g_fm: int, g_ov: int) -> dict[str, int]:
    return {
        "Perfect Points": int(g_pp),
        "Combo Multiplier": int(g_cm),
        "Fever Multiplier": int(g_fm),
        "Element": int(g_ov),
    }


def _hitsim_matrix_gem_details(g_ft: int, g_ff: int, g_pp: int, g_cm: int, g_fm: int, g_ov: int) -> dict[str, int]:
    return {
        "FeverGems": int(g_ft),
        "FeverFillGems": int(g_ff),
        "PP": int(g_pp),
        "CM": int(g_cm),
        "FM": int(g_fm),
        "OV": int(g_ov),
    }


def _hitsim_matrix_identity_key(genome_ids: Any) -> tuple[int, ...] | None:
    try:
        ids = [int(x) for x in list(genome_ids)[:9]]
    except Exception:
        return None
    if len(ids) < 9:
        return None
    return tuple(ids[:6] + sorted(ids[6:9]))


def _hitsim_matrix_base_score(candidate: dict) -> int:
    if not isinstance(candidate, dict):
        return 0
    return safe_int(candidate.get("BaseScore", candidate.get("Score", 0)), 0)


def _hitsim_matrix_merge_base_stats(base_fixed: dict, genome: list[dict]) -> dict:
    merged = dict(base_fixed or {})
    for item in list(genome or [])[:9]:
        if not isinstance(item, dict) or not item:
            continue
        for key, val in item.items():
            if key in {"Name", "ID", "Rarity", "Color", "Team", "Source"}:
                continue
            try:
                if val:
                    merged[key] = merged.get(key, 0) + val
            except Exception:
                continue
    return merged


def _hitsim_matrix_decode_genome(registry: Any, genome_ids: np.ndarray, candidate: dict) -> list:
    genome = list(candidate.get("Genome") or [])
    if len(genome) >= 9:
        return list(genome[:9])
    decode_genome = getattr(registry, "decode_genome", None)
    if callable(decode_genome):
        try:
            decoded = list(decode_genome(np.asarray(genome_ids, dtype=np.int32)))
            if len(decoded) >= 9:
                return list(decoded[:9])
        except Exception:
            pass
    gear = list(candidate.get("Gear") or [])[:6]
    minis = list(candidate.get("Minis") or [])[:3]
    out = gear + minis
    while len(out) < 9:
        out.append({})
    return out[:9]


def _normalize_hitsim_matrix_candidate(candidate: dict, *, song: Any) -> dict | None:
    if not isinstance(candidate, dict):
        return None
    genome_ids = _candidate_to_genome_ids(candidate, getattr(song, "registry", None))
    if genome_ids is None:
        return None
    identity = _hitsim_matrix_identity_key(genome_ids.tolist())
    if identity is None:
        return None
    genome = _hitsim_matrix_decode_genome(getattr(song, "registry", None), genome_ids, candidate)
    data = candidate.get("Data") if isinstance(candidate.get("Data"), dict) else candidate.get("data")
    if not isinstance(data, dict):
        data = {}
    base_stats = data.get("BaseStats") if isinstance(data.get("BaseStats"), dict) else None
    if not isinstance(base_stats, dict) or not base_stats:
        base_stats = _hitsim_matrix_merge_base_stats(getattr(song, "fixed_stats", {}) or {}, genome)
    if not isinstance(base_stats, dict) or not base_stats:
        return None
    base_score = safe_int(candidate.get("BaseScore", candidate.get("Score", data.get("BaseScore", data.get("Score", 0)))), 0)
    return {
        "Score": int(base_score),
        "BaseScore": int(base_score),
        "GenomeIDs": [int(x) for x in genome_ids.tolist()],
        "Genome": copy.deepcopy(list(genome[:9])),
        "Gear": copy.deepcopy(list(genome[:6])),
        "Minis": copy.deepcopy(list(genome[6:9])),
        "Data": copy.deepcopy(data),
        "_ga_registry": getattr(song, "registry", None),
        "_hitsim_matrix_identity": tuple(identity),
        "_hitsim_matrix_base_stats": dict(base_stats),
    }


def _hitsim_matrix_regime_candidates(refine_info: dict) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    def _append(candidate: Any) -> None:
        if not isinstance(candidate, dict):
            return
        data = candidate.get("Data") if isinstance(candidate.get("Data"), dict) else candidate.get("data")
        if not isinstance(data, dict):
            return
        regime_id = str(candidate.get("HumanHitSimRegimeId", data.get("HumanHitSimRegimeId", "")) or "")
        alpha_num = data.get("HumanHitSimRegimeAlphaNumerator")
        alpha_den = data.get("HumanHitSimRegimeAlphaDenominator")
        if not regime_id:
            try:
                has_alpha = alpha_num is not None and alpha_den is not None and int(alpha_den) != 0
            except Exception:
                has_alpha = False
            if not has_alpha:
                return
            regime_id = f"{int(alpha_num)}/{int(alpha_den)}"
        if not regime_id or regime_id in seen:
            return
        seen.add(regime_id)
        out.append(
            {
                "regime_id": str(regime_id),
                "regime_data": copy.deepcopy(data),
            }
        )

    for winner in list(refine_info.get("regime_winners") or []):
        _append(winner)
    _append(refine_info.get("selected_candidate"))
    return out


def _prepare_hitsim_matrix_plan(song: Any, *, refine_info: dict, ga_candidates: list[dict]) -> dict | None:
    if bool(getattr(song, "_hitsim_in_continuation", False)):
        _set_hitsim_matrix_status(song, "skipped", "continuation_active")
        return None
    if not _hitsim_matrix_enabled(song):
        _set_hitsim_matrix_status(song, "disabled", "config_disabled")
        return None
    registry = getattr(song, "registry", None)
    if registry is None:
        warn_fallback("hitsim.matrix.registry", "matrix planning skipped because registry is unavailable")
        _set_hitsim_matrix_status(song, "failed", "missing_registry")
        return None

    regimes = _hitsim_matrix_regime_candidates(refine_info if isinstance(refine_info, dict) else {})
    if not regimes:
        _set_hitsim_matrix_status(song, "skipped", "no_regimes")
        return None

    candidate_limit = int(_hitsim_matrix_candidate_limit(song))
    primary_color = str(getattr(song, "meta_primary_color", "") or "")
    secondary_color = str(getattr(song, "meta_secondary_color", "") or "")
    selected_candidate = refine_info.get("selected_candidate") if isinstance(refine_info, dict) else None
    source_candidates = []
    if isinstance(selected_candidate, dict):
        source_candidates.append(selected_candidate)
    source_candidates.extend(list(refine_info.get("merged_candidates") or []))
    source_candidates.extend(list(ga_candidates or []))

    normalized_by_identity: dict[tuple[int, ...], dict] = {}
    for raw_candidate in source_candidates:
        normalized = _normalize_hitsim_matrix_candidate(raw_candidate, song=song)
        if not isinstance(normalized, dict):
            continue
        identity = tuple(normalized.get("_hitsim_matrix_identity") or ())
        if not identity:
            continue
        existing = normalized_by_identity.get(identity)
        if existing is None or _hitsim_matrix_base_score(normalized) > _hitsim_matrix_base_score(existing):
            normalized_by_identity[identity] = normalized

    if not normalized_by_identity:
        _set_hitsim_matrix_status(song, "skipped", "no_candidates")
        return None

    candidate_entries = select_fg_candidates(
        list(normalized_by_identity.values()),
        limit=int(candidate_limit),
        primary_color=primary_color,
        secondary_color=secondary_color,
    )
    if not candidate_entries:
        _set_hitsim_matrix_status(song, "skipped", "candidate_selector_empty")
        return None

    try:
        from gear_optimizer.solver.hit_simulation import materialize_human_hit_sim_regime
    except Exception as exc:
        warn_fallback("hitsim.matrix.import", "failed importing regime materializer", exc=exc)
        _set_hitsim_matrix_status(song, "failed", "materializer_import")
        return None

    population_indices = np.asarray([entry.get("GenomeIDs") or [] for entry in candidate_entries], dtype=np.int32)
    if int(population_indices.shape[0]) <= 0 or int(population_indices.shape[1]) != 9:
        _set_hitsim_matrix_status(song, "failed", "invalid_population_shape")
        return None

    shared_request_payload = {
        "population_indices": np.asarray(population_indices, dtype=np.int32),
        "item_stats": np.asarray(getattr(song, "item_stats", np.zeros((0, 10), dtype=np.int32)), dtype=np.int32),
        "slot_start": np.asarray(getattr(song, "slot_start", np.zeros((9,), dtype=np.int32)), dtype=np.int32),
        "slot_count": np.asarray(getattr(song, "slot_count", np.zeros((9,), dtype=np.int32)), dtype=np.int32),
        "base_fixed_stats": np.asarray(getattr(song, "base_fixed_stats_arr", np.zeros((10,), dtype=np.int32)), dtype=np.int32),
        "ref_arrays": getattr(song, "ref_arrays", {}) or {},
        "song_slot": 0,
    }
    for flag_name, flag_value in dict(getattr(song, "color_flags", {}) or {}).items():
        shared_request_payload[str(flag_name)] = int(flag_value or 0)

    jobs: list[dict] = []
    for regime in regimes:
        regime_data = regime.get("regime_data")
        if not isinstance(regime_data, dict):
            continue
        calc_song_variant = _clone_calc_song_for_hitsim(getattr(song, "calc_song", {}) or {})
        applied = materialize_human_hit_sim_regime(calc_song_variant, regime_data=regime_data)
        if not isinstance(applied, dict):
            warn_fallback(
                "hitsim.matrix.materialize",
                "regime materialization returned no output",
                context={"regime_id": str(regime.get("regime_id", "") or "")},
            )
            continue
        jobs.append(
            {
                "regime_id": str(regime.get("regime_id", "") or ""),
                "regime_data": copy.deepcopy(regime_data),
                "calc_song": calc_song_variant,
            }
        )

    if not jobs:
        _set_hitsim_matrix_status(song, "skipped", "no_jobs")
        return None
    _set_hitsim_matrix_status(
        song,
        "planned",
        "ok",
        context={"CandidateCount": int(len(candidate_entries)), "RegimeCount": int(len(jobs))},
    )
    return {
        "candidate_entries": list(candidate_entries),
        "jobs": jobs,
        "shared_request_payload": shared_request_payload,
        "candidate_limit": int(candidate_limit),
    }


def _build_hitsim_matrix_candidate_payload(
    *,
    candidate_entry: dict,
    score: int,
    g_ft: int,
    g_ff: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
    regime_data: dict,
    selected_color: str,
    registry: Any,
) -> dict:
    genome = copy.deepcopy(list(candidate_entry.get("Genome") or []))[:9]
    gear = copy.deepcopy(list(candidate_entry.get("Gear") or []))[:6]
    minis = copy.deepcopy(list(candidate_entry.get("Minis") or []))[:3]
    gear_names = [_candidate_item_name(item) for item in gear]
    mini_names = [_candidate_item_name(item) for item in minis]
    base_stats = dict(candidate_entry.get("_hitsim_matrix_base_stats") or {})
    final_stats = apply_gems_to_base_stats(
        base_stats,
        str(selected_color or ""),
        int(g_ft),
        int(g_ff),
        int(g_pp),
        int(g_cm),
        int(g_fm),
        int(g_ov),
    )
    data = {
        "Score": int(score),
        "BaseScore": int(score),
        "Genome": copy.deepcopy(genome),
        "Gear": copy.deepcopy(gear),
        "Minis": copy.deepcopy(minis),
        "GearNames": list(gear_names),
        "MiniNames": list(mini_names),
        "FT": int(g_ft),
        "FF": int(g_ff),
        "GemCounts": _hitsim_matrix_gem_counts(int(g_pp), int(g_cm), int(g_fm), int(g_ov)),
        "Stats": final_stats,
        "BaseStats": dict(base_stats),
        "Selected Element": str(selected_color or ""),
        "Details": _hitsim_matrix_gem_details(int(g_ft), int(g_ff), int(g_pp), int(g_cm), int(g_fm), int(g_ov)),
    }
    for key in (
        "HumanHitSimRefineMode",
        "HumanHitSimDistribution",
        "HumanHitSimGreatMode",
        "HumanHitSimSeed",
        "HumanHitSimRegimeId",
        "HumanHitSimRegimeFamily",
        "HumanHitSimRegimeScope",
        "HumanHitSimRegimeAlphaNumerator",
        "HumanHitSimRegimeAlphaDenominator",
        "HumanHitSimRegimeLeftNumerator",
        "HumanHitSimRegimeLeftDenominator",
        "HumanHitSimRegimeRightNumerator",
        "HumanHitSimRegimeRightDenominator",
    ):
        if key in regime_data:
            data[key] = copy.deepcopy(regime_data.get(key))
    payload = {
        "Score": int(score),
        "BaseScore": int(score),
        "Genome": copy.deepcopy(genome),
        "GenomeIDs": [int(x) for x in list(candidate_entry.get("GenomeIDs") or [])[:9]],
        "_ga_registry": registry,
        "Gear": copy.deepcopy(gear),
        "Minis": copy.deepcopy(minis),
        "MiniNames": list(mini_names),
        "Data": data,
        "HumanHitSimRegimeId": str(data.get("HumanHitSimRegimeId", "") or ""),
        "HumanHitSimRegimeFamily": str(data.get("HumanHitSimRegimeFamily", "") or ""),
        "HumanHitSimRegimeScope": str(data.get("HumanHitSimRegimeScope", "") or ""),
    }
    return payload


def _finalize_hitsim_matrix_merged_candidates(merged_by_identity: dict[tuple[int, ...], dict]) -> list[dict]:
    out: list[dict] = []
    for entry in list(merged_by_identity.values()):
        if not isinstance(entry, dict):
            continue
        payload = copy.deepcopy(entry.get("payload")) if isinstance(entry.get("payload"), dict) else None
        if not isinstance(payload, dict):
            continue
        regime_ids = [str(x) for x in list(entry.get("regime_ids") or []) if str(x or "").strip()]
        payload["HumanHitSimMergedRegimeIds"] = list(regime_ids)
        payload["HumanHitSimMergedRegimeCount"] = int(len(regime_ids))
        data = payload.get("Data")
        if isinstance(data, dict):
            data["HumanHitSimMergedRegimeIds"] = list(regime_ids)
            data["HumanHitSimMergedRegimeCount"] = int(len(regime_ids))
            payload["Data"] = data
        out.append(payload)
    return out


def _hitsim_matrix_job_request_payload(shared_request_payload: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    payload = dict(shared_request_payload or {})
    payload["timeline_grid"] = copy.deepcopy(job.get("calc_song") or {})
    payload["song_slot"] = 0
    return payload


def _run_hitsim_matrix_gpu_batch(
    *,
    gpu_client: GpuServiceClient,
    jobs: list[dict],
    shared_request_payload: dict[str, Any],
) -> list[list[tuple[int, int, int, int, int, int, int]]] | None:
    submit = getattr(gpu_client, "submit_solve_genomes_from_registry_matrix", None)
    if not callable(submit):
        warn_fallback("hitsim.matrix.batch", "gpu matrix batch unavailable; falling back to per-regime solves")
        return None
    payload = {
        "shared_request_payload": dict(shared_request_payload or {}),
        "regimes": [{"timeline_grid": copy.deepcopy(job.get("calc_song") or {})} for job in list(jobs or [])],
    }
    try:
        handle = submit(payload)
        results = handle.future.result()
    except Exception as exc:
        warn_fallback("hitsim.matrix.batch", "gpu matrix batch failed; falling back to per-regime solves", exc=exc)
        return None
    if not isinstance(results, list) or len(results) != int(len(jobs)):
        warn_fallback(
            "hitsim.matrix.batch",
            "gpu matrix batch returned an unexpected result shape; falling back to per-regime solves",
            context={"expected_regimes": int(len(jobs)), "actual_regimes": int(len(results)) if isinstance(results, list) else -1},
        )
        return None
    return results


def _run_hitsim_matrix_jobs_sync(song: Any, gpu_client: Optional[GpuServiceClient] = None) -> tuple[dict, list, list, list[dict]]:
    plan = getattr(song, "_hitsim_matrix_plan", None)
    baseline_best = copy.deepcopy(getattr(song, "best_data", {}) or {})
    baseline_gear = copy.deepcopy(list(getattr(song, "best_gear", []) or []))
    baseline_minis = copy.deepcopy(list(getattr(song, "best_minis", []) or []))
    baseline_candidates = copy.deepcopy(list(getattr(song, "ga_candidates", []) or []))
    baseline_calc_song = copy.deepcopy(getattr(song, "calc_song", {}) or {})

    def _cleanup() -> None:
        for attr in ("_hitsim_matrix_plan", "_hitsim_matrix_submit_t0"):
            try:
                delattr(song, attr)
            except Exception:
                pass

    if not isinstance(plan, dict) or gpu_client is None:
        if gpu_client is None:
            warn_fallback("hitsim.matrix.gpu_client", "matrix execution skipped because gpu_client is unavailable")
            _set_hitsim_matrix_status(song, "failed", "missing_gpu_client")
        _cleanup()
        return baseline_best, baseline_gear, baseline_minis, baseline_candidates

    jobs = list(plan.get("jobs") or [])
    candidate_entries = list(plan.get("candidate_entries") or [])
    shared_request_payload = dict(plan.get("shared_request_payload") or {})
    if not jobs or not candidate_entries or not shared_request_payload:
        _set_hitsim_matrix_status(song, "skipped", "empty_plan")
        _cleanup()
        return baseline_best, baseline_gear, baseline_minis, baseline_candidates

    current_score = safe_int(baseline_best.get("Score", baseline_best.get("BaseScore", 0)), 0)
    selected_color = str(getattr(song, "cfg_data", {}).get("selected_color", "") or "")
    primary_color = str(getattr(song, "meta_primary_color", "") or "")
    secondary_color = str(getattr(song, "meta_secondary_color", "") or "")

    merged_by_identity: dict[tuple[int, ...], dict] = {}
    fg_regime_groups_by_id: dict[str, dict[str, Any]] = {}
    regime_winners: list[dict] = []
    completed_jobs = 0
    evaluated_pairs = 0
    best_candidate_payload: dict | None = None
    best_candidate_score = int(current_score)
    best_calc_song = copy.deepcopy(baseline_calc_song)
    execution_mode = "per_regime"

    try:
        batch_results = _run_hitsim_matrix_gpu_batch(
            gpu_client=gpu_client,
            jobs=jobs,
            shared_request_payload=shared_request_payload,
        )
        if isinstance(batch_results, list):
            execution_mode = "gpu_batch"

        for job_idx, job in enumerate(jobs):
            gpu_results = None
            job_regime_id = str(job.get("regime_id", "") or "")
            if job_regime_id:
                fg_regime_groups_by_id.setdefault(
                    str(job_regime_id),
                    {
                        "regime_id": str(job_regime_id),
                        "calc_song": copy.deepcopy(job.get("calc_song") or baseline_calc_song),
                        "ga_candidates": [],
                    },
                )
            if isinstance(batch_results, list) and job_idx < len(batch_results):
                gpu_results = batch_results[job_idx]
            if gpu_results is None:
                try:
                    handle = gpu_client.submit_solve_genomes_from_registry(
                        _hitsim_matrix_job_request_payload(shared_request_payload, job)
                    )
                    gpu_results = handle.future.result()
                except Exception as exc:
                    warn_fallback(
                        "hitsim.matrix.job",
                        "matrix regime solve failed",
                        context={"regime_id": str(job.get("regime_id", "") or "")},
                        exc=exc,
                    )
                    continue
            if not isinstance(gpu_results, list) or not gpu_results:
                warn_fallback(
                    "hitsim.matrix.job",
                    "matrix regime solve returned no result rows",
                    context={"regime_id": str(job.get("regime_id", "") or "")},
                )
                continue
            completed_jobs += 1
            local_best_payload: dict | None = None
            local_best_score = -1
            for idx, result_row in enumerate(list(gpu_results)[: len(candidate_entries)]):
                try:
                    score, g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = [int(x) for x in list(result_row)[:7]]
                except Exception as exc:
                    warn_fallback(
                        "hitsim.matrix.result_row",
                        "matrix regime solve returned a malformed result row",
                        context={
                            "regime_id": str(job.get("regime_id", "") or ""),
                            "candidate_index": int(idx),
                        },
                        exc=exc,
                    )
                    continue
                candidate_entry = candidate_entries[idx]
                identity = tuple(candidate_entry.get("_hitsim_matrix_identity") or ())
                if not identity:
                    warn_fallback(
                        "hitsim.matrix.identity",
                        "matrix candidate was missing its identity key",
                        context={
                            "regime_id": str(job.get("regime_id", "") or ""),
                            "candidate_index": int(idx),
                        },
                    )
                    continue
                payload = _build_hitsim_matrix_candidate_payload(
                    candidate_entry=candidate_entry,
                    score=int(score),
                    g_ft=int(g_ft),
                    g_ff=int(g_ff),
                    g_pp=int(g_pp),
                    g_cm=int(g_cm),
                    g_fm=int(g_fm),
                    g_ov=int(g_ov),
                    regime_data=dict(job.get("regime_data") or {}),
                    selected_color=selected_color,
                    registry=getattr(song, "registry", None),
                )
                if job_regime_id:
                    regime_group = fg_regime_groups_by_id.get(str(job_regime_id))
                    if isinstance(regime_group, dict):
                        regime_group.setdefault("ga_candidates", []).append(copy.deepcopy(payload))
                evaluated_pairs += 1
                entry = merged_by_identity.get(identity)
                regime_id = str(payload.get("HumanHitSimRegimeId", "") or "")
                if entry is None:
                    merged_by_identity[identity] = {
                        "payload": copy.deepcopy(payload),
                        "regime_ids": [regime_id] if regime_id else [],
                    }
                else:
                    regime_ids = [str(x) for x in list(entry.get("regime_ids") or []) if str(x or "").strip()]
                    if regime_id and regime_id not in regime_ids:
                        regime_ids.append(regime_id)
                    entry["regime_ids"] = regime_ids
                    existing_payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
                    existing_score = safe_int(existing_payload.get("Score", existing_payload.get("BaseScore", 0)), 0)
                    if int(score) > int(existing_score):
                        entry["payload"] = copy.deepcopy(payload)

                if int(score) > int(local_best_score):
                    local_best_score = int(score)
                    local_best_payload = payload
                if int(score) > int(best_candidate_score):
                    best_candidate_score = int(score)
                    best_candidate_payload = payload
                    best_calc_song = copy.deepcopy(job.get("calc_song") or {})

            if isinstance(local_best_payload, dict):
                regime_winners.append(local_best_payload)
    except Exception as exc:
        warn_fallback("hitsim.matrix.run", "matrix execution failed", exc=exc)
        _set_hitsim_matrix_status(song, "failed", "matrix_exception")
        _cleanup()
        return baseline_best, baseline_gear, baseline_minis, baseline_candidates

    merged_candidates = _finalize_hitsim_matrix_merged_candidates(merged_by_identity)
    if completed_jobs <= 0:
        warn_fallback("hitsim.matrix.jobs", "matrix completed with zero successful regimes")
        _set_hitsim_matrix_status(song, "failed", "no_completed_jobs")
        _cleanup()
        return baseline_best, baseline_gear, baseline_minis, baseline_candidates
    if merged_candidates:
        merged_candidates = select_fg_candidates(
            merged_candidates,
            limit=int(safe_int(getattr(song, "cfg_data", {}).get("fg_candidate_limit", FG_CANDIDATE_LIMIT), FG_CANDIDATE_LIMIT)),
            primary_color=primary_color,
            secondary_color=secondary_color,
        )
    fg_regime_groups: list[dict[str, Any]] = []
    fg_candidate_limit = int(
        safe_int(
            getattr(song, "cfg_data", {}).get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        )
    )
    for group in list(fg_regime_groups_by_id.values()):
        if not isinstance(group, dict):
            continue
        group_candidates = list(group.get("ga_candidates") or [])
        if not group_candidates:
            continue
        selected_group_candidates = select_fg_candidates(
            group_candidates,
            limit=int(fg_candidate_limit),
            primary_color=primary_color,
            secondary_color=secondary_color,
        )
        if not selected_group_candidates:
            continue
        fg_regime_groups.append(
            {
                "regime_id": str(group.get("regime_id", "") or ""),
                "calc_song": copy.deepcopy(group.get("calc_song") or baseline_calc_song),
                "ga_candidates": list(selected_group_candidates),
            }
        )

    selected_candidate = max(
        merged_candidates,
        key=lambda cand: safe_int(cand.get("Score", cand.get("BaseScore", 0)), 0),
        default=best_candidate_payload,
    )
    if not isinstance(selected_candidate, dict):
        selected_candidate = best_candidate_payload if isinstance(best_candidate_payload, dict) else None

    final_best = copy.deepcopy(baseline_best)
    final_gear = copy.deepcopy(baseline_gear)
    final_minis = copy.deepcopy(baseline_minis)
    final_calc_song = copy.deepcopy(baseline_calc_song)
    candidate_changed = False
    regime_changed = False

    if isinstance(selected_candidate, dict):
        selected_data = copy.deepcopy(selected_candidate.get("Data") or {})
        selected_score = safe_int(selected_candidate.get("Score", selected_candidate.get("BaseScore", 0)), 0)
        selected_regime_id = str(selected_candidate.get("HumanHitSimRegimeId", selected_data.get("HumanHitSimRegimeId", "")) or "")
        baseline_regime_id = str((baseline_best or {}).get("HumanHitSimRegimeId", "") or "")
        if int(selected_score) > int(current_score):
            final_best = selected_data if isinstance(selected_data, dict) else {}
            final_gear = copy.deepcopy(list(selected_candidate.get("Gear") or []))
            final_minis = copy.deepcopy(list(selected_candidate.get("Minis") or []))
            final_calc_song = copy.deepcopy(best_calc_song if isinstance(best_calc_song, dict) else baseline_calc_song)
        candidate_changed = bool(int(selected_score) > int(current_score))
        regime_changed = bool(candidate_changed and selected_regime_id and selected_regime_id != baseline_regime_id)

    matrix_meta = (
        final_calc_song.get("metadata")
        if isinstance(final_calc_song, dict) and isinstance(final_calc_song.get("metadata"), dict)
        else {}
    )
    matrix_meta = dict(matrix_meta or {})
    matrix_meta["HumanHitSimRegimeMatrixApplied"] = True
    matrix_meta["HumanHitSimRegimeMatrixCandidateCount"] = int(len(candidate_entries))
    matrix_meta["HumanHitSimRegimeMatrixRegimeCount"] = int(len(jobs))
    matrix_meta["HumanHitSimRegimeMatrixCompletedRegimeCount"] = int(completed_jobs)
    matrix_meta["HumanHitSimRegimeMatrixEvaluatedPairs"] = int(evaluated_pairs)
    matrix_meta["HumanHitSimRegimeMatrixRegimeWinnerCount"] = int(len(regime_winners))
    matrix_meta["HumanHitSimRegimeMatrixMergedCandidateCount"] = int(len(merged_candidates))
    matrix_meta["HumanHitSimRegimeMatrixBestScore"] = int(best_candidate_score)
    matrix_meta["HumanHitSimRegimeMatrixCandidateChanged"] = bool(candidate_changed)
    matrix_meta["HumanHitSimRegimeMatrixRegimeChanged"] = bool(regime_changed)
    matrix_meta["HumanHitSimRegimeMatrixExecutionMode"] = str(execution_mode)
    if isinstance(final_calc_song, dict):
        final_calc_song["metadata"] = matrix_meta
    _set_hitsim_matrix_status(
        song,
        "applied",
        "ok",
        context={
            "CandidateCount": int(len(candidate_entries)),
            "RegimeCount": int(len(jobs)),
            "CompletedRegimeCount": int(completed_jobs),
        },
    )

    refine_info = copy.deepcopy(getattr(song, "_hitsim_last_refine_info", {}) or {})
    if isinstance(refine_info, dict):
        refine_info["matrix_applied"] = True
        refine_info["matrix_candidate_count"] = int(len(candidate_entries))
        refine_info["matrix_regime_count"] = int(len(jobs))
        refine_info["matrix_completed_regime_count"] = int(completed_jobs)
        refine_info["matrix_evaluated_pairs"] = int(evaluated_pairs)
        refine_info["matrix_regime_winner_count"] = int(len(regime_winners))
        refine_info["matrix_merged_candidate_count"] = int(len(merged_candidates))
        refine_info["matrix_best_score"] = int(best_candidate_score)
        refine_info["matrix_candidate_changed"] = bool(candidate_changed)
        refine_info["matrix_regime_changed"] = bool(regime_changed)
        refine_info["matrix_fg_regime_group_count"] = int(len(fg_regime_groups))
        refine_info["regime_winners"] = list(regime_winners)
        refine_info["merged_candidates"] = list(merged_candidates)
        if isinstance(selected_candidate, dict):
            refine_info["selected_candidate"] = copy.deepcopy(selected_candidate)
        setattr(song, "_hitsim_last_refine_info", refine_info)

    if fg_regime_groups:
        setattr(song, "_hitsim_fg_regime_groups", list(fg_regime_groups))
    else:
        try:
            delattr(song, "_hitsim_fg_regime_groups")
        except Exception:
            pass
    song.calc_song = copy.deepcopy(final_calc_song)
    _cleanup()
    return final_best, final_gear, final_minis, list(merged_candidates or baseline_candidates)


def _mutate_seed_genome(
    genome: np.ndarray,
    *,
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    rng: np.random.Generator,
    mutations: int,
) -> np.ndarray:
    out = np.asarray(genome, dtype=np.int32).copy()
    n_mut = max(0, int(mutations))
    if n_mut <= 0:
        return out
    for _ in range(n_mut):
        slot_idx = int(rng.integers(0, 9))
        count = int(slot_count[slot_idx]) if slot_idx < int(slot_count.shape[0]) else 0
        if count <= 0:
            continue
        start = int(slot_start[slot_idx])
        out[slot_idx] = int(start + int(rng.integers(0, count)))
    return out


def _build_hitsim_initial_populations(
    *,
    seed_candidates: list[dict],
    registry: Any,
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    num_runs: int,
    n_genomes: int,
    seed: int,
    mutations_per_copy: int,
) -> np.ndarray | None:
    genomes: list[np.ndarray] = []
    seen: set[tuple[int, ...]] = set()
    for candidate in list(seed_candidates or []):
        genome_ids = _candidate_to_genome_ids(candidate, registry)
        if genome_ids is None:
            continue
        key = tuple(int(x) for x in genome_ids.tolist())
        if key in seen:
            continue
        seen.add(key)
        genomes.append(genome_ids)
    if not genomes:
        return None

    runs = max(1, int(num_runs))
    pop = max(1, int(n_genomes))
    out = np.zeros((runs, pop, 9), dtype=np.int32)
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    base_count = int(len(genomes))
    for run_idx in range(runs):
        for genome_idx in range(pop):
            base = np.asarray(genomes[(genome_idx + run_idx) % base_count], dtype=np.int32)
            if genome_idx < base_count:
                out[run_idx, genome_idx, :] = base
            else:
                out[run_idx, genome_idx, :] = _mutate_seed_genome(
                    base,
                    slot_start=np.asarray(slot_start, dtype=np.int32),
                    slot_count=np.asarray(slot_count, dtype=np.int32),
                    rng=rng,
                    mutations=int(mutations_per_copy),
                )
    return out


def _prepare_hitsim_continuation_jobs(song: Any, *, refine_info: dict, ga_candidates: list[dict]) -> list[dict]:
    if bool(getattr(song, "_hitsim_in_continuation", False)):
        _set_hitsim_continuation_status(song, "skipped", "continuation_active")
        return []
    cfg_dict = getattr(song, "cfg_dict", {}) or {}
    human_cfg = _cfg_section_ci(cfg_dict, "HumanHitSim")
    max_regimes = safe_int(_cfg_value_ci(human_cfg, "ContinueMaxRegimes", "0"), 0)
    if max_regimes <= 0:
        _set_hitsim_continuation_status(song, "disabled", "config_disabled")
        return []

    regime_winners = list(refine_info.get("regime_winners") or [])
    if not regime_winners:
        _set_hitsim_continuation_status(song, "skipped", "no_regime_winners")
        return []

    selected_candidate = refine_info.get("selected_candidate") or {}
    selected_key = _candidate_name_key(selected_candidate if isinstance(selected_candidate, dict) else {})
    merged_candidates = list(refine_info.get("merged_candidates") or [])

    continue_runs = safe_int(_cfg_value_ci(human_cfg, "ContinueRuns", "1"), 1)
    if continue_runs <= 0:
        continue_runs = 1
    continue_generations = safe_int(
        _cfg_value_ci(human_cfg, "ContinueGenerations", str(max(1, int(getattr(song, "gens_per_run", 1) or 1) // 2))),
        max(1, int(getattr(song, "gens_per_run", 1) or 1) // 2),
    )
    if continue_generations <= 0:
        continue_generations = 1
    continue_population = safe_int(
        _cfg_value_ci(human_cfg, "ContinuePopulation", str(min(256, int(getattr(song, "n_genomes", 256) or 256)))),
        min(256, int(getattr(song, "n_genomes", 256) or 256)),
    )
    if continue_population <= 0:
        continue_population = min(256, int(getattr(song, "n_genomes", 256) or 256))
    continue_seed_limit = safe_int(_cfg_value_ci(human_cfg, "ContinueSeedCandidateLimit", "24"), 24)
    if continue_seed_limit <= 0:
        continue_seed_limit = 24
    continue_mutations = safe_int(_cfg_value_ci(human_cfg, "ContinueMutationsPerCopy", "1"), 1)
    if continue_mutations < 0:
        continue_mutations = 0

    candidate_limit = safe_int(getattr(song, "cfg_data", {}).get("fg_candidate_limit", FG_CANDIDATE_LIMIT), FG_CANDIDATE_LIMIT)
    all_seed_candidates = list(merged_candidates or []) + list(ga_candidates or [])
    all_seed_candidates = select_fg_candidates(
        all_seed_candidates,
        limit=max(int(candidate_limit), int(continue_seed_limit)),
        primary_color=str(getattr(song, "meta_primary_color", "") or ""),
        secondary_color=str(getattr(song, "meta_secondary_color", "") or ""),
    )

    planned: list[dict] = []
    seen_regime_ids: set[str] = set()
    for winner in list(regime_winners):
        if not isinstance(winner, dict):
            continue
        regime_data = winner.get("Data")
        if not isinstance(regime_data, dict):
            continue
        regime_id = str(winner.get("HumanHitSimRegimeId", regime_data.get("HumanHitSimRegimeId", "")) or "")
        if not regime_id or regime_id in seen_regime_ids:
            continue
        if _candidate_name_key(winner) == selected_key:
            continue
        seen_regime_ids.add(regime_id)
        planned.append(winner)

    planned.sort(key=lambda row: -safe_int(row.get("Score", row.get("BaseScore", 0)), 0))
    planned = planned[: int(max_regimes)]
    if not planned:
        _set_hitsim_continuation_status(song, "skipped", "no_divergent_regimes")
        return []

    try:
        from gear_optimizer.solver.hit_simulation import materialize_human_hit_sim_regime
    except Exception as exc:
        warn_fallback("hitsim.continuation.import", "failed importing regime materializer", exc=exc)
        _set_hitsim_continuation_status(song, "failed", "materializer_import")
        return []

    jobs: list[dict] = []
    for idx, winner in enumerate(planned):
        regime_data = winner.get("Data")
        if not isinstance(regime_data, dict):
            continue

        calc_song_variant = _clone_calc_song_for_hitsim(getattr(song, "calc_song", {}) or {})
        applied = materialize_human_hit_sim_regime(calc_song_variant, regime_data=regime_data)
        if not isinstance(applied, dict):
            warn_fallback(
                "hitsim.continuation.materialize",
                "regime materialization returned no output",
                context={"regime_id": str(winner.get("HumanHitSimRegimeId", regime_data.get("HumanHitSimRegimeId", "")) or "")},
            )
            continue

        seed_candidates = [winner] + list(all_seed_candidates or [])
        seed_candidates = select_fg_candidates(
            seed_candidates,
            limit=int(continue_seed_limit),
            primary_color=str(getattr(song, "meta_primary_color", "") or ""),
            secondary_color=str(getattr(song, "meta_secondary_color", "") or ""),
        )
        seed_token = f"{getattr(song, 'ga_seed', 0)}|{regime_id}|{idx}"
        seed_base = int(zlib.crc32(seed_token.encode("utf-8", errors="replace")) & 0xFFFFFFFF) or 1
        initial_populations = _build_hitsim_initial_populations(
            seed_candidates=seed_candidates,
            registry=getattr(song, "registry", None),
            slot_start=np.asarray(getattr(song, "slot_start", np.zeros((9,), dtype=np.int32)), dtype=np.int32),
            slot_count=np.asarray(getattr(song, "slot_count", np.zeros((9,), dtype=np.int32)), dtype=np.int32),
            num_runs=int(continue_runs),
            n_genomes=int(continue_population),
            seed=int(seed_base),
            mutations_per_copy=int(continue_mutations),
        )
        if initial_populations is None:
            warn_fallback(
                "hitsim.continuation.population",
                "failed building seeded continuation population",
                context={"regime_id": str(regime_id)},
            )
            continue

        jobs.append(
            {
                "regime_id": regime_id,
                "calc_song": calc_song_variant,
                "initial_populations": initial_populations,
                "num_runs": int(continue_runs),
                "n_genomes": int(continue_population),
                "n_generations": int(continue_generations),
                "ga_seed": int(seed_base),
                "winner_score": safe_int(winner.get("Score", winner.get("BaseScore", 0)), 0),
            }
        )

    if jobs:
        setattr(
            song,
            "_hitsim_continuation_base_state",
            {
                "job_count": int(len(jobs)),
                "ga_seed": getattr(song, "ga_seed", None),
                "num_runs": int(getattr(song, "num_runs", 1) or 1),
                "n_genomes": int(getattr(song, "n_genomes", 1) or 1),
                "gens_per_run": int(getattr(song, "gens_per_run", 1) or 1),
                "db_seed_ids": getattr(song, "db_seed_ids", None),
                "db_seed_prob": float(getattr(song, "db_seed_prob", 0.0) or 0.0),
                "db_seed_copies": int(getattr(song, "db_seed_copies", 0) or 0),
                "db_seed_mutations": int(getattr(song, "db_seed_mutations", 0) or 0),
                "calc_song": copy.deepcopy(getattr(song, "calc_song", {}) or {}),
            },
        )
        _set_hitsim_continuation_status(
            song,
            "planned",
            "ok",
            context={
                "RegimeCount": int(len(jobs)),
                "RequestedRegimeCount": int(len(planned)),
                "Population": int(continue_population),
                "Runs": int(continue_runs),
                "Generations": int(continue_generations),
            },
        )
    else:
        _set_hitsim_continuation_status(
            song,
            "failed",
            "no_jobs",
            context={"RequestedRegimeCount": int(len(planned))},
        )
    return jobs


def _advance_hitsim_continuation(
    song: Any,
    *,
    best_data: dict,
    best_gear: list,
    best_minis: list,
    ga_candidates: list[dict],
) -> dict:
    jobs = list(getattr(song, "_hitsim_continuation_jobs", []) or [])
    active = bool(getattr(song, "_hitsim_continuation_active", False))
    if not jobs and not active:
        return {
            "resubmit": False,
            "best_data": best_data,
            "best_gear": best_gear,
            "best_minis": best_minis,
            "ga_candidates": ga_candidates,
        }

    current_score = safe_int((best_data or {}).get("Score", (best_data or {}).get("BaseScore", 0)), 0)
    best_acc = getattr(song, "_hitsim_continuation_best_data", None)
    best_acc_score = safe_int((best_acc or {}).get("Score", (best_acc or {}).get("BaseScore", 0)), 0)
    if best_acc is None or int(current_score) >= int(best_acc_score):
        setattr(song, "_hitsim_continuation_best_data", copy.deepcopy(best_data or {}))
        setattr(song, "_hitsim_continuation_best_gear", list(best_gear or []))
        setattr(song, "_hitsim_continuation_best_minis", list(best_minis or []))
        setattr(song, "_hitsim_continuation_best_calc_song", copy.deepcopy(getattr(song, "calc_song", {}) or {}))

    merged_candidates = list(getattr(song, "_hitsim_continuation_ga_candidates", []) or [])
    merged_candidates.extend(list(ga_candidates or []))
    merged_candidates = select_fg_candidates(
        merged_candidates,
        limit=int(safe_int(getattr(song, "cfg_data", {}).get("fg_candidate_limit", FG_CANDIDATE_LIMIT), FG_CANDIDATE_LIMIT)),
        primary_color=str(getattr(song, "meta_primary_color", "") or ""),
        secondary_color=str(getattr(song, "meta_secondary_color", "") or ""),
    )
    setattr(song, "_hitsim_continuation_ga_candidates", merged_candidates)

    if jobs:
        next_job = dict(jobs.pop(0))
        setattr(song, "_hitsim_continuation_jobs", jobs)
        setattr(song, "_hitsim_continuation_active", True)
        setattr(song, "_hitsim_in_continuation", True)
        song.calc_song = copy.deepcopy(next_job["calc_song"])
        _set_hitsim_continuation_status(
            song,
            "active",
            "ok",
            context={
                "ActiveRegimeId": str(next_job.get("regime_id", "") or ""),
                "RemainingRegimeCount": int(len(jobs)),
            },
        )
        song.ga_initial_populations = np.asarray(next_job["initial_populations"], dtype=np.int32)
        song.num_runs = int(next_job["num_runs"])
        song.n_genomes = int(next_job["n_genomes"])
        song.gens_per_run = int(next_job["n_generations"])
        song.ga_seed = int(next_job["ga_seed"])
        song.db_seed_ids = None
        song.db_seed_prob = 0.0
        song.db_seed_copies = 0
        song.db_seed_mutations = 0
        return {"resubmit": True}

    base_state = getattr(song, "_hitsim_continuation_base_state", {}) or {}
    if isinstance(base_state, dict):
        song.ga_seed = base_state.get("ga_seed")
        song.num_runs = int(base_state.get("num_runs", getattr(song, "num_runs", 1)) or 1)
        song.n_genomes = int(base_state.get("n_genomes", getattr(song, "n_genomes", 1)) or 1)
        song.gens_per_run = int(base_state.get("gens_per_run", getattr(song, "gens_per_run", 1)) or 1)
        song.db_seed_ids = base_state.get("db_seed_ids")
        song.db_seed_prob = float(base_state.get("db_seed_prob", 0.0) or 0.0)
        song.db_seed_copies = int(base_state.get("db_seed_copies", 0) or 0)
        song.db_seed_mutations = int(base_state.get("db_seed_mutations", 0) or 0)

    best_out = copy.deepcopy(getattr(song, "_hitsim_continuation_best_data", best_data) or {})
    best_gear_out = list(getattr(song, "_hitsim_continuation_best_gear", best_gear) or [])
    best_minis_out = list(getattr(song, "_hitsim_continuation_best_minis", best_minis) or [])
    best_calc_song = copy.deepcopy(getattr(song, "_hitsim_continuation_best_calc_song", getattr(song, "calc_song", {}) or {}))
    if isinstance(best_calc_song, dict) and best_calc_song:
        song.calc_song = best_calc_song
    _set_hitsim_continuation_status(
        song,
        "completed",
        "ok",
        context={
            "JobCount": int((base_state or {}).get("job_count", 0) or 0),
            "BestScore": int(safe_int(best_out.get("Score", best_out.get("BaseScore", 0)), 0)),
        },
    )
    song.ga_initial_populations = None
    setattr(song, "_hitsim_continuation_active", False)
    setattr(song, "_hitsim_in_continuation", False)
    for attr in (
        "_hitsim_continuation_jobs",
        "_hitsim_continuation_base_state",
        "_hitsim_continuation_best_data",
        "_hitsim_continuation_best_gear",
        "_hitsim_continuation_best_minis",
        "_hitsim_continuation_best_calc_song",
        "_hitsim_last_refine_info",
    ):
        try:
            delattr(song, attr)
        except Exception:
            pass
    ga_candidates_out = list(getattr(song, "_hitsim_continuation_ga_candidates", merged_candidates) or [])
    try:
        delattr(song, "_hitsim_continuation_ga_candidates")
    except Exception:
        pass
    return {
        "resubmit": False,
        "best_data": best_out,
        "best_gear": best_gear_out,
        "best_minis": best_minis_out,
        "ga_candidates": ga_candidates_out,
    }


def _thread_cpu_time_s() -> float:
    """Best-effort per-thread CPU timer for CPU-only profiling."""
    try:
        return float(time.thread_time())
    except Exception:
        return 0.0


class _InFlightStageProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None = None) -> None:
        self.enabled = bool(enabled)
        self.out_path = out_path
        self._t0 = time.perf_counter()
        self._stage: dict[str, dict[str, Any]] = {}
        self._song: dict[str, dict[str, float]] = {}
        self._allow_prefixes = self._parse_prefixes(os.environ.get("INFLIGHT_STAGE_PROFILE_PREFIX", ""))
        if _truthy(os.environ.get("INFLIGHT_STAGE_PROFILE_FG_ONLY", "0")) and not self._allow_prefixes:
            # Convenience mode: only record FG-related stages (and the "underfed" wait marker that indicates
            # CPU-side bubbles while no GPU work is in flight).
            self._allow_prefixes = ("fg_", "underfed_wait")

    @staticmethod
    def _parse_prefixes(raw: Any) -> tuple[str, ...]:
        prefixes: list[str] = []
        for part in str(raw or "").split(","):
            part = str(part).strip()
            if part:
                prefixes.append(part)
        return tuple(prefixes)

    def record(self, stage: str, seconds: float, *, cpu_seconds: float | None = None, song: str | None = None) -> None:
        if not self.enabled:
            return
        allow = self._allow_prefixes
        if allow and not any(str(stage).startswith(p) for p in allow):
            return
        try:
            seconds = float(seconds)
        except Exception:
            return
        if seconds < 0:
            return

        if cpu_seconds is not None:
            try:
                cpu_seconds = float(cpu_seconds)
            except Exception:
                cpu_seconds = None
            if cpu_seconds is not None and cpu_seconds < 0:
                cpu_seconds = None

        entry = self._stage.get(stage)
        if entry is None:
            entry = {
                "count": 0,
                "total_s": 0.0,
                "max_s": 0.0,
                "samples_s": [],
                "cpu_total_s": 0.0,
                "cpu_max_s": 0.0,
                "cpu_samples_s": [],
            }
            self._stage[stage] = entry
        entry["count"] = int(entry["count"]) + 1
        entry["total_s"] = float(entry["total_s"]) + seconds
        entry["max_s"] = max(float(entry["max_s"]), seconds)
        try:
            entry["samples_s"].append(seconds)
        except Exception:
            pass

        if cpu_seconds is not None:
            entry["cpu_total_s"] = float(entry.get("cpu_total_s", 0.0) or 0.0) + float(cpu_seconds)
            entry["cpu_max_s"] = max(float(entry.get("cpu_max_s", 0.0) or 0.0), float(cpu_seconds))
            try:
                entry["cpu_samples_s"].append(float(cpu_seconds))
            except Exception:
                pass

        if song:
            per_song = self._song.get(song)
            if per_song is None:
                per_song = {}
                self._song[song] = per_song
            per_song[stage] = float(per_song.get(stage, 0.0)) + seconds
            if cpu_seconds is not None:
                per_song[f"{stage}_cpu"] = float(per_song.get(f"{stage}_cpu", 0.0)) + float(cpu_seconds)

    @staticmethod
    def _quantile(samples: list[float], p: float) -> float:
        if not samples:
            return 0.0
        xs = sorted(float(x) for x in samples)
        n = len(xs)
        if n == 1:
            return xs[0]
        idx = int(round(float(p) * (n - 1)))
        idx = max(0, min(n - 1, idx))
        return xs[idx]

    def summary(self) -> dict[str, Any]:
        if not self.enabled:
            return {}
        total_wall = time.perf_counter() - self._t0
        stages: dict[str, Any] = {}
        for name, entry in self._stage.items():
            samples = entry.get("samples_s") or []
            cpu_samples = entry.get("cpu_samples_s") or []
            stages[name] = {
                "count": int(entry.get("count", 0) or 0),
                "total_s": float(entry.get("total_s", 0.0) or 0.0),
                "max_s": float(entry.get("max_s", 0.0) or 0.0),
                "p50_s": self._quantile(samples, 0.50),
                "p95_s": self._quantile(samples, 0.95),
                "cpu_total_s": float(entry.get("cpu_total_s", 0.0) or 0.0),
                "cpu_max_s": float(entry.get("cpu_max_s", 0.0) or 0.0),
                "cpu_p50_s": self._quantile(cpu_samples, 0.50),
                "cpu_p95_s": self._quantile(cpu_samples, 0.95),
            }
        return {"total_wall_s": float(total_wall), "stages": stages, "songs": self._song}

    def emit(self) -> None:
        if not self.enabled:
            return
        summary = self.summary()
        stages = summary.get("stages") or {}
        ranked = sorted(stages.items(), key=lambda kv: float(kv[1].get("total_s", 0.0) or 0.0), reverse=True)
        print(f"[InFlight][StageProfile] total_wall_s={float(summary.get('total_wall_s', 0.0) or 0.0):.3f}")
        for name, info in ranked[:10]:
            print(
                "[InFlight][StageProfile] {:<12} total={:>8.3f}s cpu={:>8.3f}s p50={:>6.3f}s p95={:>6.3f}s max={:>6.3f}s n={}".format(
                    name,
                    float(info.get("total_s", 0.0) or 0.0),
                    float(info.get("cpu_total_s", 0.0) or 0.0),
                    float(info.get("p50_s", 0.0) or 0.0),
                    float(info.get("p95_s", 0.0) or 0.0),
                    float(info.get("max_s", 0.0) or 0.0),
                    int(info.get("count", 0) or 0),
                )
            )

        ranked_cpu = sorted(stages.items(), key=lambda kv: float(kv[1].get("cpu_total_s", 0.0) or 0.0), reverse=True)
        if ranked_cpu:
            print("[InFlight][CpuProfile] top_cpu_s")
            for name, info in ranked_cpu[:10]:
                cpu_total = float(info.get("cpu_total_s", 0.0) or 0.0)
                if cpu_total <= 0.0:
                    continue
                print(
                    "[InFlight][CpuProfile] {:<12} cpu_total={:>8.3f}s p50={:>6.3f}s p95={:>6.3f}s max={:>6.3f}s n={}".format(
                        name,
                        cpu_total,
                        float(info.get("cpu_p50_s", 0.0) or 0.0),
                        float(info.get("cpu_p95_s", 0.0) or 0.0),
                        float(info.get("cpu_max_s", 0.0) or 0.0),
                        int(info.get("count", 0) or 0),
                    )
                )

        out_path = str(self.out_path or "").strip()
        if not out_path:
            return
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, sort_keys=True)
        except Exception:
            pass


def _warmup_fg_jit(calc_song: dict, ref_arrays: dict) -> None:
    global _FG_JIT_WARMED
    if _FG_JIT_WARMED:
        return
    if not calc_song or not ref_arrays:
        return
    try:
        fg_baseline_params({"Fever Time": 0, "Fever Fill Rate": 0}, calc_song, ref_arrays)
    except Exception:
        pass
    try:
        grid = get_song_timeline_grid(calc_song, ref_arrays)
        grid.get_timeline(0, int(TOTAL_ROWS))
        grid.to_gpu_arrays_minimal()
    except Exception:
        pass
    _FG_JIT_WARMED = True


def _decode_ga_payload_sync(song: Any, runs_payload: np.ndarray) -> tuple[dict, list, list, list[dict]]:
    cpu_t0 = _thread_cpu_time_s()
    best_data, best_gear, best_minis, ga_candidates = decode_gpu_native_ga_runs_payload(
        runs_payload=runs_payload,
        registry=song.registry,
        cfg_data=song.cfg_data,
        base_stats_fixed=song.fixed_stats,
        fg_candidate_limit=safe_int(
            song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        ),
    )

    # Optional post-GA HumanHitSim refinement for ApplyTo=ALL.
    # Runs on the decoded GA winner only and updates the in-flight song context in-place.
    try:
        from gear_optimizer.solver.hit_simulation import refine_human_hit_sim_after_ga

        refine_info = refine_human_hit_sim_after_ga(
            song.calc_song,
            cfg_dict=song.cfg_dict or {},
            best_data=best_data if isinstance(best_data, dict) else {},
            ref_arrays=song.ref_arrays if isinstance(song.ref_arrays, dict) else {},
            ga_seed=getattr(song, "ga_seed", None),
            candidate_pool=ga_candidates if isinstance(ga_candidates, list) else None,
        )
        if isinstance(refine_info, dict) and isinstance(best_data, dict):
            setattr(song, "_hitsim_last_refine_info", refine_info)
            refined_score = safe_int(refine_info.get("best_score", 0), 0)
            best_data["Score"] = int(refined_score)
            best_data["BaseScore"] = int(refined_score)
            selected_candidate = refine_info.get("selected_candidate")
            if isinstance(selected_candidate, dict):
                selected_gear = selected_candidate.get("Gear")
                selected_minis = selected_candidate.get("Minis")
                if selected_gear is not None:
                    best_gear = list(selected_gear or [])
                if selected_minis is not None:
                    best_minis = list(selected_minis or [])
            merged_candidates = refine_info.get("merged_candidates")
            if not isinstance(merged_candidates, list) or not merged_candidates:
                merged_candidates = [
                    {
                        "Score": int(refined_score),
                        "BaseScore": int(refined_score),
                        "Gear": list(best_gear or []),
                        "Minis": list(best_minis or []),
                        "Data": best_data,
                    }
                ]
            if isinstance(ga_candidates, list):
                ga_candidates = list(ga_candidates) + list(merged_candidates)
                fg_candidate_limit = safe_int(
                    song.cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT),
                    FG_CANDIDATE_LIMIT,
                )
                meta = song.calc_song.get("metadata") if isinstance(song.calc_song, dict) else {}
                primary_color = str((meta or {}).get("Primary Color", "") or "")
                secondary_color = str((meta or {}).get("Secondary Color", "") or "")
                ga_candidates = select_fg_candidates(
                    ga_candidates,
                    limit=int(fg_candidate_limit),
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                )
            else:
                ga_candidates = list(merged_candidates)
            matrix_plan = _prepare_hitsim_matrix_plan(
                song,
                refine_info=refine_info,
                ga_candidates=list(ga_candidates or []),
            )
            if isinstance(matrix_plan, dict) and matrix_plan:
                setattr(song, "_hitsim_matrix_plan", matrix_plan)
            else:
                try:
                    delattr(song, "_hitsim_matrix_plan")
                except Exception:
                    pass
    except Exception as exc:
        warn_fallback("hitsim.refine_after_ga", "post-GA HumanHitSim refine failed; keeping decoded GA winner", exc=exc)
        try:
            calc_song = getattr(song, "calc_song", None)
            meta = calc_song.get("metadata") if isinstance(calc_song, dict) else None
            if isinstance(meta, dict):
                meta = dict(meta)
                meta["HumanHitSimRefineAfterGAStatus"] = "failed"
                meta["HumanHitSimRefineAfterGAReason"] = str(type(exc).__name__)
                calc_song["metadata"] = meta
        except Exception:
            pass

    out = (best_data, best_gear, best_minis, ga_candidates)
    try:
        setattr(song, "_cpu_decode_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
    return out


def _prefetch_db_loadouts_sync(
    song_name: str,
    *,
    limit: int,
    gears_by_name: dict,
    minis_by_name: dict,
) -> list[dict]:
    try:
        limit_i = max(0, int(limit))
    except Exception:
        limit_i = 0
    cached = _fg_db_cache_get(song_name, limit=limit_i)
    if cached is not None:
        return cached

    try:
        from gear_optimizer.data.database import get_best_loadouts

        rows = get_best_loadouts(song_name, limit=limit_i, gears_by_name=gears_by_name, minis_by_name=minis_by_name)
        if isinstance(rows, list):
            _fg_db_cache_put(song_name, limit=limit_i, rows=rows)
            return rows
        return []
    except Exception:
        return []


def _prepare_fg_job_sync(song: Any, gpu_client: Optional[GpuServiceClient] = None) -> None:
    cpu_t0 = _thread_cpu_time_s()
    cfg = song.cfg

    perf = _truthy(os.environ.get("PERF_TIMING", "0"))
    t0 = time.perf_counter() if perf else 0.0

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    song.fg_candidate_limit = int(fg_candidate_limit)
    song.fg_search_radius = read_fg_search_radius(cfg)

    # If HumanHitSim is configured for FG-only, we defer the expensive simulation until
    # we actually enter the FG prep stage (keeps CPU prep lighter on low-end machines).
    try:
        meta = song.calc_song.get("metadata") if isinstance(song.calc_song, dict) else None
        if isinstance(meta, dict) and str(meta.get("HumanHitSimApplyTo", "") or "").strip().upper() == "FG":
            from gear_optimizer.solver.hit_simulation import apply_human_hit_sim

            apply_human_hit_sim(song.calc_song, cfg_dict=song.cfg_dict or {})
    except Exception:
        pass

    ga_candidates = list(song.ga_candidates or [])
    # If GA came from the GPU-native "selected payload" path, candidates are already GPU-selected
    # (bounded + deduped) and re-running the CPU selector is pure overhead on slower machines.
    is_gpu_selected_payload = False
    try:
        if ga_candidates:
            d0 = ga_candidates[0].get("Data") if isinstance(ga_candidates[0], dict) else None
            if isinstance(d0, dict) and ("_ga_gpu_run_idx" in d0 or "_ga_gpu_row_idx" in d0):
                is_gpu_selected_payload = True
    except Exception:
        is_gpu_selected_payload = False

    if is_gpu_selected_payload:
        ga_candidates = ga_candidates[: int(fg_candidate_limit)]
    else:
        ga_candidates = select_fg_candidates(
            ga_candidates,
            limit=fg_candidate_limit,
            primary_color=str(song.meta_primary_color or ""),
            secondary_color=str(song.meta_secondary_color or ""),
        )
    song.ga_candidates = ga_candidates
    t_select = time.perf_counter() if perf else 0.0

    def _prime_fg_group_meta_for_candidates(candidates: list[dict] | None, *, calc_song: dict | None) -> None:
        if not isinstance(candidates, list) or not candidates:
            return
        if not isinstance(calc_song, dict) or not calc_song:
            return
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            data = candidate.get("Data")
            if not isinstance(data, dict):
                continue
            if isinstance(data.get("_fg_group_meta"), dict):
                continue
            base_stats = data.get("BaseStats")
            if not isinstance(base_stats, dict) or not base_stats:
                continue
            try:
                fg_group_meta = build_fg_group_meta(
                    base_stats=base_stats,
                    calc_song=calc_song,
                    ref_arrays=song.ref_arrays if isinstance(song.ref_arrays, dict) else {},
                    selected_element=str(data.get("Selected Element", "") or ""),
                    center_ft=int(data.get("FT", 0) or 0),
                    center_ff=int(data.get("FF", 0) or 0),
                    primary_color=str(song.meta_primary_color or ""),
                    secondary_color=str(song.meta_secondary_color or ""),
                    run_idx=data.get("_ga_gpu_run_idx"),
                    row_idx=data.get("_ga_gpu_row_idx"),
                )
                if isinstance(fg_group_meta, dict):
                    data["_fg_group_meta"] = fg_group_meta
            except Exception:
                continue

    _prime_fg_group_meta_for_candidates(ga_candidates, calc_song=song.calc_song)
    for group in list(getattr(song, "_hitsim_fg_regime_groups", []) or []):
        if not isinstance(group, dict):
            continue
        _prime_fg_group_meta_for_candidates(
            group.get("ga_candidates"),
            calc_song=group.get("calc_song") if isinstance(group.get("calc_song"), dict) else song.calc_song,
        )

    # Non-blocking DB prefetch: check if future is ready without blocking.
    # If the DB read is still in progress, proceed with GA candidates only.
    # This prevents FG worker threads from stalling on DB I/O and starving the GPU.
    db_loadouts_full = song.db_loadouts_full
    prefetch_pending = False
    if db_loadouts_full is None and song.db_loadouts_future is not None:
        try:
            fut = song.db_loadouts_future
            # Use done() check to avoid blocking - if DB read isn't ready, skip it
            if fut.done():
                try:
                    db_loadouts_full = fut.result(timeout=0)
                    song.db_loadouts_full = db_loadouts_full
                    if isinstance(db_loadouts_full, list):
                        _fg_db_cache_put(song.db_key, limit=int(fg_candidate_limit), rows=db_loadouts_full)
                except Exception:
                    db_loadouts_full = None
                finally:
                    song.db_loadouts_future = None
            else:
                # DB prefetch still running - proceed without it to keep GPU fed
                if perf:
                    print("[PERF][FGPrep] db_prefetch not ready, proceeding without DB loadouts")
                prefetch_pending = True
                db_loadouts_full = None
        except Exception:
            db_loadouts_full = None
    t_db = time.perf_counter() if perf else 0.0

    build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, song.effective_difficulty)
    song.fg_direct_ga_candidates = bool(song.force_greats_finder)
    # Keep FG prep focused on DB rows; GPU finder consumes GA candidates directly and
    # only the retained GA subset is merged back into `song.loadout_entries` after FG.
    loadout_ga_candidates = [] if bool(song.fg_direct_ga_candidates) else list(ga_candidates or [])
    song.loadout_entries = build_loadout_entries(
        song.db_key,
        bool(song.use_evo_db),
        loadout_ga_candidates,
        fg_candidate_limit,
        song.gears_by_name,
        song.minis_by_name,
        build_details,
        db_loadouts_full=db_loadouts_full,
        # If prefetch is still in-flight, avoid a duplicate synchronous DB read.
        allow_db_query=not bool(prefetch_pending),
        # FG grouping reads eval_data/BaseStats directly; defer details materialization
        # until persistence/retained-output paths so CPU prep does not stall the GPU.
        materialize_ga_details=False,
        ga_registry=song.registry,
    )
    t_build = time.perf_counter() if perf else 0.0

    # Native in-flight optimization: submit the combo-booster GPU eval early (during FG prep)
    try:
        combo_enabled = _truthy(os.environ.get("FG_COMBO_BOOSTER_ENABLED", "1"))
        existing_job = getattr(song, "fg_combo_job", None)
        if (
            combo_enabled
            and gpu_client is not None
            and song.force_greats_finder
            and song.ga_candidates
            and not existing_job
        ):
            job = prepare_fg_combo_booster_candidates_job(
                existing_candidates=list(song.ga_candidates or []),
                registry=song.registry,
                base_stats_fixed=song.fixed_stats,
                cfg_data=song.cfg_data,
                calc_song=song.calc_song,
                ref_arrays=song.ref_arrays,
                primary_color=str(song.meta_primary_color or ""),
                secondary_color=str(song.meta_secondary_color or ""),
                song_slot=int(song.song_slot or 0),
                gpu_client=gpu_client,
            )
            if job:
                song.fg_combo_job = job
    except Exception:
        pass

    if perf:
        select_ms = (t_select - t0) * 1000.0
        db_wait_ms = (t_db - t_select) * 1000.0
        build_ms = (t_build - t_db) * 1000.0
        total_ms = (t_build - t0) * 1000.0
        try:
            loadouts_n = len(song.loadout_entries or {})
        except Exception:
            loadouts_n = 0
        db_n = -1
        try:
            if isinstance(db_loadouts_full, list):
                db_n = len(db_loadouts_full)
        except Exception:
            db_n = -1
        print(
            "[PERF][FGPrep] "
            f"limit={fg_candidate_limit} ga={len(ga_candidates)} loadouts={loadouts_n} "
            f"select={select_ms:.1f}ms db_wait={db_wait_ms:.1f}ms build={build_ms:.1f}ms total={total_ms:.1f}ms "
            f"db_prefetch={int(db_n >= 0)} db_n={db_n}"
        )

    try:
        setattr(song, "_cpu_fg_prep_s", max(0.0, _thread_cpu_time_s() - float(cpu_t0)))
    except Exception:
        pass
