from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, FG_SEARCH_RADIUS, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.profile_events import emit_profile_event
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
from gear_optimizer.solver.scoring.runtime_state import FORCE_GREATS_ALGO_VERSION


@dataclass(slots=True)
class NativeFgCandidateSurface:
    loadout_hashes: list[str] = field(default_factory=list)
    entries: list[dict[str, Any] | None] = field(default_factory=list)
    candidates: list[dict[str, Any] | None] = field(default_factory=list)
    base_data: list[dict[str, Any]] = field(default_factory=list)
    base_stats: list[dict[str, Any]] = field(default_factory=list)
    base_scores: list[int] = field(default_factory=list)
    selected_colors: list[str] = field(default_factory=list)
    center_fts: list[int] = field(default_factory=list)
    center_ffs: list[int] = field(default_factory=list)
    gear: list[list[str]] = field(default_factory=list)
    minis: list[list[str]] = field(default_factory=list)
    is_ga: list[bool] = field(default_factory=list)
    fg_scores: list[int] = field(default_factory=list)
    force_payloads: list[dict[str, Any] | None] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.loadout_hashes)

    def append(
        self,
        *,
        loadout_hash: str,
        entry: dict[str, Any] | None,
        candidate: dict[str, Any] | None,
        base_data: dict[str, Any],
        base_stats: dict[str, Any],
        base_score: int,
        selected_color: str,
        center_ft: int,
        center_ff: int,
        gear: list[str],
        minis: list[str],
        is_ga: bool,
    ) -> None:
        self.loadout_hashes.append(str(loadout_hash))
        self.entries.append(entry)
        self.candidates.append(candidate)
        self.base_data.append(base_data)
        self.base_stats.append(base_stats)
        self.base_scores.append(int(base_score))
        self.selected_colors.append(str(selected_color or ""))
        self.center_fts.append(int(center_ft))
        self.center_ffs.append(int(center_ff))
        self.gear.append(list(gear or []))
        self.minis.append(list(minis or []))
        self.is_ga.append(bool(is_ga))
        self.fg_scores.append(int(base_score))
        self.force_payloads.append(None)


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


def _append_ga_candidate(
    surface: NativeFgCandidateSurface,
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
        return

    selected_color = get_selected_element(data, default_selected_color)
    base_stats = _candidate_base_stats(data, selected_color=selected_color)
    if not base_stats:
        return

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
        return

    base_score = safe_int(candidate.get("BaseScore", candidate.get("Score", 0)), 0)
    surface.append(
        loadout_hash=str(loadout_hash),
        entry=None,
        candidate=candidate,
        base_data=data,
        base_stats=base_stats,
        base_score=int(base_score),
        selected_color=str(selected_color or ""),
        center_ft=safe_int(data.get("FT", 0), 0),
        center_ff=safe_int(data.get("FF", 0), 0),
        gear=list(gear_names),
        minis=list(mini_names),
        is_ga=True,
    )


def _append_loadout_entry(
    surface: NativeFgCandidateSurface,
    key: str,
    entry: dict[str, Any],
    *,
    default_selected_color: str,
) -> dict[str, Any] | None:
    data = eval_data_from_entry(entry, default_selected_color)
    if not isinstance(data, dict) or not data:
        return

    selected_color = get_selected_element(data, default_selected_color)
    base_stats = _candidate_base_stats(data, selected_color=selected_color)
    if not base_stats:
        return

    gear_names, mini_names = materialize_entry_names(entry, mutate=True)
    loadout_hash = str(entry.get("loadout_hash") or entry.get("_resolved_loadout_hash") or key or "")
    if not loadout_hash:
        return

    surface.append(
        loadout_hash=str(loadout_hash),
        entry=entry,
        candidate=None,
        base_data=data,
        base_stats=base_stats,
        base_score=int(entry_base_score(entry)),
        selected_color=str(selected_color or ""),
        center_ft=safe_int(data.get("FT", 0), 0),
        center_ff=safe_int(data.get("FF", 0), 0),
        gear=list(gear_names),
        minis=list(mini_names),
        is_ga=str(entry.get("_source") or "") == "ga",
    )


def build_native_fg_candidate_surface(
    *,
    loadout_entries: dict[str, dict] | None,
    ga_candidates: list[dict] | None,
    default_selected_color: str,
    primary_color: str,
    secondary_color: str,
    minis_by_name: dict[str, dict] | None = None,
    registry: Any = None,
) -> NativeFgCandidateSurface:
    surface = NativeFgCandidateSurface()

    for key, entry in list((loadout_entries or {}).items()):
        if not isinstance(entry, dict):
            continue
        _append_loadout_entry(surface, str(key), entry, default_selected_color=default_selected_color)

    for candidate in ga_candidates or []:
        if not isinstance(candidate, dict):
            continue
        _append_ga_candidate(
            surface,
            candidate,
            default_selected_color=default_selected_color,
            primary_color=primary_color,
            secondary_color=secondary_color,
            minis_by_name=minis_by_name,
            registry=registry,
        )

    return surface


def score_native_fg_candidate_surface(
    *,
    surface: NativeFgCandidateSurface | None,
    loadout_entries: dict[str, dict] | None,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    search_radius: int | None = None,
    retained_limit: int = LOADOUTS_PER_SONG_LIMIT,
    gpu_client: Any | None = None,
) -> list[dict[str, Any]]:
    if surface is None or len(surface) <= 0:
        return []

    _ = search_radius
    center_fts: list[int | None] = [None for _ in range(len(surface))]
    center_ffs: list[int | None] = [None for _ in range(len(surface))]
    radius_arg = None

    fg_results, batch_stats = solve_native_force_greats_gpu_batch(
        base_stats_list=[dict(stats) for stats in surface.base_stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_colors=[str(color) for color in surface.selected_colors],
        center_fts=center_fts,
        center_ffs=center_ffs,
        search_radius=radius_arg,
        gpu_client=gpu_client,
    )
    meta = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}
    song_name = str(meta.get("Song Name") or meta.get("Song") or "").strip()
    song_diff = str(meta.get("Difficulty") or "").strip()
    emit_profile_event(
        component="native_fg",
        event="candidate_cache_stats",
        song_key=f"{song_name} ({song_diff})" if song_name and song_diff else song_name or None,
        metrics=dict(batch_stats or {}),
    )

    items: list[tuple[str, dict]] = []
    for idx in range(len(surface)):
        fg_result = fg_results[idx] if idx < len(fg_results) else None
        force_payload = None
        base_score = int(surface.base_scores[idx])
        fg_score = int(base_score)
        if isinstance(fg_result, dict) and fg_result:
            fg_score = safe_int(fg_result.get("final_score", base_score), base_score)
            force_payload = _materialize_force_payload(
                base_data=_safe_dict(surface.base_data[idx]),
                base_score=int(base_score),
                base_stats=dict(surface.base_stats[idx]),
                fg_result=fg_result,
                selected_color=str(surface.selected_colors[idx]),
                search_radius=FG_SEARCH_RADIUS,
                center_ft=int(surface.center_fts[idx]),
                center_ff=int(surface.center_ffs[idx]),
            )

        surface.fg_scores[idx] = int(fg_score)
        surface.force_payloads[idx] = force_payload
        entry = surface.entries[idx]
        if isinstance(entry, dict):
            entry["fg_score"] = int(fg_score)
            if isinstance(force_payload, dict):
                entry["force"] = force_payload
        candidate = surface.candidates[idx]
        if isinstance(candidate, dict):
            candidate["fg_score"] = int(fg_score)
            if isinstance(force_payload, dict):
                candidate["force"] = force_payload
        items.append(
            (
                str(surface.loadout_hashes[idx]),
                {
                    "base_score": int(base_score),
                    "fg_score": int(fg_score),
                    "force": force_payload,
                },
            )
        )

    retained_hashes = select_retained_hashes(
        items,
        limit=max(int(FG_CANDIDATE_LIMIT), int(retained_limit)),
        base_score_fn=lambda rec: safe_int(rec.get("base_score", 0), 0),
        fg_score_fn=lambda rec: safe_int(rec.get("fg_score", 0), 0),
        fg_valid_fn=lambda rec: has_valid_fg_config(rec.get("force")),
    )

    fg_variants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx in range(len(surface)):
        loadout_hash = str(surface.loadout_hashes[idx])
        if loadout_hash not in retained_hashes or loadout_hash in seen:
            continue
        seen.add(loadout_hash)
        force_payload = surface.force_payloads[idx]
        if not isinstance(force_payload, dict) or not has_valid_fg_config(force_payload):
            continue
        fg_variants.append(
            {
                "data": force_payload,
                "force": force_payload,
                "gear": list(surface.gear[idx] or []),
                "minis": list(surface.minis[idx] or []),
                "score": int(surface.base_scores[idx] or 0),
                "base_score": int(surface.base_scores[idx] or 0),
                "fg_score": int(surface.fg_scores[idx] or 0),
                "_entry_ref": surface.entries[idx],
                "_is_ga": bool(surface.is_ga[idx]),
            }
        )

        entry = surface.entries[idx]
        if entry is None and isinstance(loadout_entries, dict):
            loadout_entries[loadout_hash] = {
                "gear": list(surface.gear[idx] or []),
                "minis": list(surface.minis[idx] or []),
                "score": int(surface.base_scores[idx] or 0),
                "base_score": int(surface.base_scores[idx] or 0),
                "details": {},
                "fg_score": int(surface.fg_scores[idx] or 0),
                "force": force_payload,
                "eval_data": surface.base_data[idx],
                "_source": "ga" if bool(surface.is_ga[idx]) else "db",
            }

    fg_variants.sort(key=lambda row: safe_int(row.get("fg_score", 0), 0), reverse=True)
    return fg_variants
