from __future__ import annotations

from typing import Any

from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.utils import get_selected_element, safe_int
from gear_optimizer.helpers.song_helpers.fg_config import has_valid_fg_config
from gear_optimizer.helpers.song_helpers.force_greats.entry_resolution import entry_base_score
from gear_optimizer.helpers.song_helpers.force_greats.entry_utils import eval_data_from_entry
from gear_optimizer.helpers.song_helpers.force_greats.result_application import apply_gems_to_base_fast
from gear_optimizer.helpers.song_helpers.ga_entry_utils import (
    candidate_loadout_hash,
    materialize_candidate_names,
    materialize_entry_names,
)
from gear_optimizer.helpers.song_helpers.retention import select_retained_hashes
from gear_optimizer.solver.native_force_greats import solve_native_force_greats_gpu_batch
from gear_optimizer.solver.scoring import _extract_base_stats
from gear_optimizer.solver.scoring.gpu_solver import FORCE_GREATS_ALGO_VERSION


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _candidate_base_stats(data: dict[str, Any], *, selected_color: str) -> dict[str, Any]:
    base_stats = data.get("BaseStats")
    if isinstance(base_stats, dict) and base_stats:
        return dict(base_stats)

    stats = data.get("Stats")
    if not isinstance(stats, dict) or not stats:
        return {}

    base_stats = _extract_base_stats(
        stats,
        data.get("GemCounts") if isinstance(data.get("GemCounts"), dict) else {},
        str(selected_color or data.get("Selected Element", "") or ""),
        safe_int(data.get("FT", 0), 0),
        safe_int(data.get("FF", 0), 0),
    )
    if isinstance(base_stats, dict) and base_stats:
        data["BaseStats"] = dict(base_stats)
        return dict(base_stats)
    return {}


def _gem_count(gem_counts: Any, key: str) -> int:
    if not isinstance(gem_counts, dict):
        return 0
    return safe_int(gem_counts.get(key, 0), 0)


def _materialize_force_payload(
    *,
    base_data: dict[str, Any],
    base_score: int,
    base_stats: dict[str, Any],
    fg_result: dict[str, Any],
    selected_color: str,
    search_radius: int | None,
    center_ft: int,
    center_ff: int,
) -> dict[str, Any]:
    final_score = safe_int(fg_result.get("final_score", 0), 0)
    fg_ft = safe_int(fg_result.get("FT", center_ft), center_ft)
    fg_ff = safe_int(fg_result.get("FF", center_ff), center_ff)
    gem_counts = fg_result.get("gem_counts") if isinstance(fg_result.get("gem_counts"), dict) else {}

    g_pp = _gem_count(gem_counts, "Perfect Points")
    g_cm = _gem_count(gem_counts, "Combo Multiplier")
    g_fm = _gem_count(gem_counts, "Fever Multiplier")
    g_ov = _gem_count(gem_counts, "Element")

    force_payload = dict(base_data)
    force_payload["BaseScore"] = int(base_score)
    force_payload["Score"] = int(final_score)
    force_payload["FT"] = int(fg_ft)
    force_payload["FF"] = int(fg_ff)
    force_payload["GemCounts"] = dict(gem_counts)
    force_payload["BaseStats"] = dict(base_stats)
    force_payload["Stats"] = apply_gems_to_base_fast(
        base_stats,
        str(selected_color or ""),
        int(fg_ft),
        int(fg_ff),
        int(g_pp),
        int(g_cm),
        int(g_fm),
        int(g_ov),
    )
    force_payload["ForceGreats"] = {
        "enabled": True,
        "mode": "finder",
        "algo_version": int(FORCE_GREATS_ALGO_VERSION),
        "search_radius": None if search_radius is None else int(search_radius),
        "center_ft": int(center_ft),
        "center_ff": int(center_ff),
        "config": fg_result.get("config_dict", {}) or {},
        "fp_targets": list(fg_result.get("fp_targets") or []),
        "final_score": int(final_score),
    }
    force_payload["forced_counts"] = list(fg_result.get("config_counts") or [])
    return force_payload


def _record_from_ga_candidate(
    candidate: dict[str, Any],
    *,
    default_selected_color: str,
    primary_color: str,
    secondary_color: str,
    minis_by_name: dict[str, dict] | None,
    registry: Any,
) -> dict[str, Any] | None:
    data = candidate.get("Data")
    if not isinstance(data, dict) or not data:
        return None

    selected_color = get_selected_element(data, default_selected_color)
    base_stats = _candidate_base_stats(data, selected_color=selected_color)
    if not base_stats:
        return None

    gear_names, mini_names = materialize_candidate_names(candidate, registry=registry, mutate=True)
    loadout_hash = candidate_loadout_hash(
        candidate,
        registry=registry,
        minis_by_name=minis_by_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        selected_color=str(selected_color or ""),
        mutate=True,
    )
    if not loadout_hash:
        return None

    base_score = safe_int(candidate.get("BaseScore", candidate.get("Score", 0)), 0)
    return {
        "hash": str(loadout_hash),
        "entry": None,
        "candidate": candidate,
        "data": data,
        "base_stats": base_stats,
        "base_score": int(base_score),
        "selected_color": str(selected_color or ""),
        "center_ft": safe_int(data.get("FT", 0), 0),
        "center_ff": safe_int(data.get("FF", 0), 0),
        "gear": list(gear_names),
        "minis": list(mini_names),
        "_is_ga": True,
    }


def _record_from_loadout_entry(
    key: str,
    entry: dict[str, Any],
    *,
    default_selected_color: str,
) -> dict[str, Any] | None:
    data = eval_data_from_entry(entry, default_selected_color)
    if not isinstance(data, dict) or not data:
        return None

    selected_color = get_selected_element(data, default_selected_color)
    base_stats = _candidate_base_stats(data, selected_color=selected_color)
    if not base_stats:
        return None

    gear_names, mini_names = materialize_entry_names(entry, mutate=True)
    loadout_hash = str(entry.get("loadout_hash") or entry.get("_resolved_loadout_hash") or key or "")
    if not loadout_hash:
        return None

    return {
        "hash": str(loadout_hash),
        "entry": entry,
        "candidate": None,
        "data": data,
        "base_stats": base_stats,
        "base_score": int(entry_base_score(entry)),
        "selected_color": str(selected_color or ""),
        "center_ft": safe_int(data.get("FT", 0), 0),
        "center_ff": safe_int(data.get("FF", 0), 0),
        "gear": list(gear_names),
        "minis": list(mini_names),
        "_is_ga": str(entry.get("_source") or "") == "ga",
    }


def score_native_ga_force_greats(
    *,
    loadout_entries: dict[str, dict] | None,
    ga_candidates: list[dict] | None,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    default_selected_color: str,
    primary_color: str,
    secondary_color: str,
    minis_by_name: dict[str, dict] | None = None,
    registry: Any = None,
    search_radius: int | None = None,
    retained_limit: int = LOADOUTS_PER_SONG_LIMIT,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for key, entry in list((loadout_entries or {}).items()):
        if not isinstance(entry, dict):
            continue
        rec = _record_from_loadout_entry(str(key), entry, default_selected_color=default_selected_color)
        if rec is not None:
            records.append(rec)

    for candidate in ga_candidates or []:
        if not isinstance(candidate, dict):
            continue
        rec = _record_from_ga_candidate(
            candidate,
            default_selected_color=default_selected_color,
            primary_color=primary_color,
            secondary_color=secondary_color,
            minis_by_name=minis_by_name,
            registry=registry,
        )
        if rec is not None:
            records.append(rec)

    if not records:
        return []

    if search_radius is not None and int(search_radius) < 0:
        center_fts: list[int | None] = [None for _ in records]
        center_ffs: list[int | None] = [None for _ in records]
        radius_arg = None
    else:
        center_fts = [int(rec["center_ft"]) for rec in records]
        center_ffs = [int(rec["center_ff"]) for rec in records]
        radius_arg = search_radius

    fg_results, _batch_stats = solve_native_force_greats_gpu_batch(
        base_stats_list=[dict(rec["base_stats"]) for rec in records],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_colors=[str(rec["selected_color"]) for rec in records],
        center_fts=center_fts,
        center_ffs=center_ffs,
        search_radius=radius_arg,
    )

    items: list[tuple[str, dict]] = []
    for idx, rec in enumerate(records):
        fg_result = fg_results[idx] if idx < len(fg_results) else None
        force_payload = None
        fg_score = int(rec["base_score"])
        if isinstance(fg_result, dict) and fg_result:
            fg_score = safe_int(fg_result.get("final_score", rec["base_score"]), int(rec["base_score"]))
            force_payload = _materialize_force_payload(
                base_data=_safe_dict(rec["data"]),
                base_score=int(rec["base_score"]),
                base_stats=dict(rec["base_stats"]),
                fg_result=fg_result,
                selected_color=str(rec["selected_color"]),
                search_radius=search_radius,
                center_ft=int(rec["center_ft"]),
                center_ff=int(rec["center_ff"]),
            )

        rec["fg_score"] = int(fg_score)
        rec["force"] = force_payload
        entry = rec.get("entry")
        if isinstance(entry, dict):
            entry["fg_score"] = int(fg_score)
            if isinstance(force_payload, dict):
                entry["force"] = force_payload
        candidate = rec.get("candidate")
        if isinstance(candidate, dict):
            candidate["fg_score"] = int(fg_score)
            if isinstance(force_payload, dict):
                candidate["force"] = force_payload
        items.append((str(rec["hash"]), rec))

    retained_hashes = select_retained_hashes(
        items,
        limit=max(int(FG_CANDIDATE_LIMIT), int(retained_limit)),
        base_score_fn=lambda rec: safe_int(rec.get("base_score", 0), 0),
        fg_score_fn=lambda rec: safe_int(rec.get("fg_score", 0), 0),
        fg_valid_fn=lambda rec: has_valid_fg_config(rec.get("force")),
    )

    fg_variants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in records:
        loadout_hash = str(rec["hash"])
        if loadout_hash not in retained_hashes or loadout_hash in seen:
            continue
        seen.add(loadout_hash)
        force_payload = rec.get("force")
        if not isinstance(force_payload, dict) or not has_valid_fg_config(force_payload):
            continue
        fg_variants.append(
            {
                "data": force_payload,
                "force": force_payload,
                "gear": list(rec.get("gear") or []),
                "minis": list(rec.get("minis") or []),
                "score": int(rec.get("base_score", 0) or 0),
                "base_score": int(rec.get("base_score", 0) or 0),
                "fg_score": int(rec.get("fg_score", 0) or 0),
                "_entry_ref": rec.get("entry"),
                "_is_ga": bool(rec.get("_is_ga")),
            }
        )

        entry = rec.get("entry")
        if entry is None and isinstance(loadout_entries, dict):
            loadout_entries[loadout_hash] = {
                "gear": list(rec.get("gear") or []),
                "minis": list(rec.get("minis") or []),
                "score": int(rec.get("base_score", 0) or 0),
                "base_score": int(rec.get("base_score", 0) or 0),
                "details": {},
                "fg_score": int(rec.get("fg_score", 0) or 0),
                "force": force_payload,
                "eval_data": rec.get("data"),
                "_source": "ga" if bool(rec.get("_is_ga")) else "db",
            }

    fg_variants.sort(key=lambda row: safe_int(row.get("fg_score", 0), 0), reverse=True)
    return fg_variants
