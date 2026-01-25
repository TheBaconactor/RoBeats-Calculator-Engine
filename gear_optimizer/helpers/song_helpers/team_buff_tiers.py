from __future__ import annotations

import ast
import copy
from dataclasses import dataclass

import numpy as np

from ...core.constants import TOTAL_ROWS
from ...data.loadout_equivalence import representative_mini_names
from ...solver.fever_timeline import calculate_fever_timeline_indices
from ...solver.scoring_core import fast_calculate_score, lookup_reference_py
from ...solver.scoring.force_greats import _compute_force_greats_timeline
from ...solver.scoring.stats_scoring import build_great_penalty_table

_TEAM_BUFF_TIERS: dict[str, dict[str, int]] = {
    "NONE": {"PP": 0, "Elem": 0},
    "T1": {"PP": 25, "Elem": 35},
    "T5": {"PP": 25, "Elem": 30},
    "T10": {"PP": 20, "Elem": 25},
    "T15": {"PP": 15, "Elem": 20},
}

_ELEMENTS = ("Chill", "Flow", "Rush", "Beat", "Vibe")


def _norm_text(v: object) -> str:
    return str(v or "").strip()


def _truthy_cfg(v: object) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _unwrap_list_literal(s: str) -> list[str] | None:
    """
    Best-effort recovery for legacy minis corruption where names were persisted as strings like:
      "['Electroman']"  (Python repr) or '["Electroman"]' (JSON-ish)
    """
    s = str(s or "").strip()
    if len(s) < 2:
        return None
    if (s[0] not in "[(") or (s[-1] not in "])"):
        return None
    try:
        parsed = ast.literal_eval(s)
    except Exception:
        return None
    if not isinstance(parsed, (list, tuple)):
        return None
    out: list[str] = []
    for item in parsed:
        if isinstance(item, (list, tuple)):
            for sub in item:
                sub_s = str(sub or "").strip()
                if sub_s:
                    out.append(sub_s)
        else:
            item_s = str(item or "").strip()
            if item_s:
                out.append(item_s)
    return out or None


def _flat_item_names(items: object) -> list[str]:
    out: list[str] = []
    if not items:
        return out
    for it in items if isinstance(items, (list, tuple)) else [items]:
        if isinstance(it, (list, tuple)):
            out.extend(_flat_item_names(it))
        elif isinstance(it, dict):
            name = _norm_text(it.get("Name", it.get("name", "")))
            if name:
                out.append(name)
        else:
            name = _norm_text(it)
            if name:
                out.append(name)
    return out


def _mini_groups_from_any(minis: object) -> list[list[str]]:
    groups: list[list[str]] = []
    if not minis:
        return groups
    for slot in minis if isinstance(minis, (list, tuple)) else [minis]:
        # Slot can be:
        # - "Name" (str)
        # - {"Name": "..."} (dict)
        # - ["A", "B"] (variant group)
        # - ["['A']"] (corrupted repr)
        if isinstance(slot, (list, tuple)):
            names: list[str] = []
            for raw in slot:
                if isinstance(raw, dict):
                    s = _norm_text(raw.get("Name", raw.get("name", "")))
                    if s:
                        names.append(s)
                    continue
                if isinstance(raw, str):
                    repaired = _unwrap_list_literal(raw)
                    if repaired:
                        names.extend(repaired)
                    else:
                        s = raw.strip()
                        if s:
                            names.append(s)
                    continue
                s = _norm_text(raw)
                if s:
                    names.append(s)
            names = sorted(set(n for n in names if n))
            if names:
                groups.append(names)
            continue

        if isinstance(slot, dict):
            s = _norm_text(slot.get("Name", slot.get("name", "")))
            if s:
                groups.append([s])
            continue

        if isinstance(slot, str):
            repaired = _unwrap_list_literal(slot)
            if repaired:
                names = sorted(set(n for n in repaired if n))
                if names:
                    groups.append(names)
            else:
                s = slot.strip()
                if s:
                    groups.append([s])
            continue

        s = _norm_text(slot)
        if s:
            groups.append([s])
    return groups


def _representative_mini_names_from_any(minis: object) -> list[str]:
    groups = _mini_groups_from_any(minis)
    return representative_mini_names(groups) if groups else []


def _auto_select_team_buff_and_color(cfg_dict: dict) -> bool:
    if not isinstance(cfg_dict, dict):
        return False
    ie = cfg_dict.get("IterationEngine") or {}
    if not isinstance(ie, dict):
        return False
    raw = ie.get("AutoSelectBuffAndColor", ie.get("autoselectbuffandcolor", ""))
    return _truthy_cfg(raw)


def _norm_team_buff(v: object) -> str:
    s = _norm_text(v).upper()
    return s if s in _TEAM_BUFF_TIERS else ""


def _resolve_team_section(cfg_dict: dict) -> dict:
    if not isinstance(cfg_dict, dict):
        return {}
    sec = cfg_dict.get("TeamContributionBuffConstant") or {}
    return sec if isinstance(sec, dict) else {}


def _resolve_team_color(cfg_dict: dict, calc_song: dict) -> str:
    # Match runtime: when auto mode is enabled, we always set TeamColor to the song's primary color.
    if _auto_select_team_buff_and_color(cfg_dict):
        try:
            return _norm_text((calc_song.get("metadata", {}) or {}).get("Primary Color", ""))
        except Exception:
            return ""
    team_section = _resolve_team_section(cfg_dict)
    team_color = _norm_text(team_section.get("TeamColor", team_section.get("teamcolor", "")))
    if not team_color:
        try:
            team_color = _norm_text((calc_song.get("metadata", {}) or {}).get("Primary Color", ""))
        except Exception:
            team_color = ""
    return team_color


def _resolve_base_team_buff(cfg_dict: dict) -> str:
    # Match runtime: when auto mode is enabled, we always set TeamBuff to T5.
    if _auto_select_team_buff_and_color(cfg_dict):
        return "T5"
    team_section = _resolve_team_section(cfg_dict)
    base = _norm_team_buff(team_section.get("TeamBuff", team_section.get("teambuff", "T5")))
    return base or "T5"


def _team_buff_effect(team_buff: str, team_color: str) -> dict[str, int]:
    """
    Return the raw stat deltas applied by TeamBuff for the given color.

    Matches `gear_optimizer/core/stats_calculator.py::build_base_stats_from_config`.
    """
    tier = _TEAM_BUFF_TIERS.get(_norm_team_buff(team_buff))
    if not tier:
        return {}

    pp_add = int(tier["PP"])
    elem_add = int(tier["Elem"])
    out: dict[str, int] = {"Perfect Points": pp_add}

    team_color = _norm_text(team_color)
    valid_color_key = next((k for k in _ELEMENTS if k.lower() == team_color.lower()), None)
    if valid_color_key:
        out[valid_color_key] = elem_add
    elif team_color:
        out["Perfect Points"] += pp_add
    return out


def _dict_cfg_to_counts(cfg: dict) -> list[int]:
    if not isinstance(cfg, dict) or not cfg:
        return []
    pairs: list[tuple[int, int]] = []
    for k, v in cfg.items():
        if not isinstance(k, str) or not k.startswith("NonFever"):
            continue
        try:
            idx = int(k.replace("NonFever", "")) - 1
        except Exception:
            continue
        try:
            val = int(v)
        except Exception:
            val = 0
        pairs.append((idx, val))
    if not pairs:
        return []
    pairs.sort(key=lambda x: x[0])
    max_idx = pairs[-1][0]
    out = [0] * (max_idx + 1)
    for idx, v in pairs:
        if 0 <= idx < len(out):
            out[idx] = max(0, int(v))
    return out


def _extract_force_config_counts(force_obj: dict) -> list[int]:
    if not isinstance(force_obj, dict) or not force_obj:
        return []

    fg_meta = force_obj.get("ForceGreats")
    if not isinstance(fg_meta, dict):
        details = force_obj.get("details") or {}
        fg_meta = details.get("ForceGreats") if isinstance(details, dict) else None
    if not isinstance(fg_meta, dict):
        return []

    cfg = fg_meta.get("config") or {}
    counts = _dict_cfg_to_counts(cfg if isinstance(cfg, dict) else {})
    if not counts:
        return []
    if sum(int(x) for x in counts) <= 0:
        return []
    return counts


def _force_payload_stats(force_obj: dict, fallback_stats: dict) -> dict:
    """Compute FG Stats from a flat force payload when possible."""
    if not isinstance(force_obj, dict) or not force_obj:
        return fallback_stats if isinstance(fallback_stats, dict) else {}
    base_stats = force_obj.get("BaseStats")
    if not isinstance(base_stats, dict) or not base_stats:
        return fallback_stats if isinstance(fallback_stats, dict) else {}
    gem_counts = force_obj.get("GemCounts") or {}
    if not isinstance(gem_counts, dict):
        gem_counts = {}
    try:
        from .force_greats.result_application import apply_gems_to_base_fast

        sel = force_obj.get("Selected Element") or force_obj.get("SelectedElement") or ""
        ft_val = int(force_obj.get("FT", 0) or 0)
        ff_val = int(force_obj.get("FF", 0) or 0)
        g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
        g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
        g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
        g_ov = int(gem_counts.get("Element", 0) or 0)
        return apply_gems_to_base_fast(base_stats, str(sel), ft_val, ff_val, g_pp, g_cm, g_fm, g_ov)
    except Exception:
        return fallback_stats if isinstance(fallback_stats, dict) else {}


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v) if v is not None else int(default)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return int(default)


def _team_buff_delta_map(*, base_team_buff: str, target_team_buff: str, team_color: str) -> dict[str, int]:
    base = _team_buff_effect(base_team_buff, team_color)
    target = _team_buff_effect(target_team_buff, team_color)
    keys = set(base.keys()) | set(target.keys())
    out: dict[str, int] = {}
    for k in keys:
        delta = int(target.get(k, 0) or 0) - int(base.get(k, 0) or 0)
        if delta:
            out[str(k)] = int(delta)
    return out


def _apply_stat_delta(stats: dict, delta: dict[str, int]) -> dict:
    if not isinstance(stats, dict) or not stats:
        return {}
    if not delta:
        return dict(stats)
    out = dict(stats)
    for k, d in delta.items():
        if not d:
            continue
        out[str(k)] = _safe_int(out.get(k, 0), 0) + int(d)
    return out


def _apply_details_delta(details: object, delta: dict[str, int]) -> dict:
    if not isinstance(details, dict) or not details:
        return {}
    if not delta:
        return dict(details)
    out = dict(details)
    stats = out.get("Stats")
    if isinstance(stats, dict) and stats:
        out["Stats"] = _apply_stat_delta(stats, delta)
    return out


def _apply_force_delta(force_obj: object, *, delta: dict[str, int], fg_score: int) -> object:
    if not isinstance(force_obj, dict) or not force_obj:
        return force_obj

    # Legacy format: `{score, gear, minis, details: {...}}`
    if isinstance(force_obj.get("details"), dict):
        if not delta:
            # Still update the score if present to prevent stale payloads.
            out0 = dict(force_obj)
            if "score" in out0:
                out0["score"] = int(fg_score)
            details0 = out0.get("details")
            if isinstance(details0, dict):
                fg0 = details0.get("ForceGreats")
                if isinstance(fg0, dict):
                    fg0_out = dict(fg0)
                    fg0_out["final_score"] = int(fg_score)
                    details0_out = dict(details0)
                    details0_out["ForceGreats"] = fg0_out
                    out0["details"] = details0_out
            return out0

        out = dict(force_obj)
        if "score" in out:
            out["score"] = int(fg_score)
        details = out.get("details")
        if isinstance(details, dict) and details:
            details_out = dict(details)
            stats = details_out.get("Stats")
            if isinstance(stats, dict) and stats:
                details_out["Stats"] = _apply_stat_delta(stats, delta)
            fg = details_out.get("ForceGreats")
            if isinstance(fg, dict):
                fg_out = dict(fg)
                fg_out["final_score"] = int(fg_score)
                details_out["ForceGreats"] = fg_out
            out["details"] = details_out
        return out

    # New format: flat raw FG payload (persisted in force_details_json)
    if not delta:
        out0 = dict(force_obj)
        out0["Score"] = int(fg_score)
        fg0 = out0.get("ForceGreats")
        if isinstance(fg0, dict):
            fg0_out = dict(fg0)
            fg0_out["final_score"] = int(fg_score)
            out0["ForceGreats"] = fg0_out
        return out0

    out = dict(force_obj)
    out["Score"] = int(fg_score)
    base_stats = out.get("BaseStats")
    if isinstance(base_stats, dict) and base_stats:
        out["BaseStats"] = _apply_stat_delta(base_stats, delta)
    fg = out.get("ForceGreats")
    if isinstance(fg, dict):
        fg_out = dict(fg)
        fg_out["final_score"] = int(fg_score)
        out["ForceGreats"] = fg_out
    return out


def _stats_get_int(stats: dict, key: str, default: int = 0) -> int:
    if not isinstance(stats, dict):
        return default
    return _safe_int(stats.get(key, default), default)


@dataclass(frozen=True)
class _TimelineCtx:
    fever_mask_head: np.ndarray
    count_body_fever: int
    count_body_normal: int


@dataclass(frozen=True)
class _FgTimelineCtx:
    fever_mask_head: np.ndarray
    count_body_fever: int
    count_body_normal: int
    section_details: list[dict]


def _build_base_timeline_ctx(
    *, stats: dict, calc_song: dict, ref_arrays: dict, fever_mask_buffer: np.ndarray
) -> _TimelineCtx:
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("timestamps")
    if timestamps is None:
        raise ValueError("calc_song.song_data.timestamps missing")
    timestamps = np.asarray(timestamps)
    total_notes = int(timestamps.shape[0])
    if total_notes <= 0:
        return _TimelineCtx(np.zeros(0, dtype=np.bool_), 0, 0)

    meta = calc_song.get("metadata", {}) or {}
    long_notes = _safe_int(meta.get("Long Notes"), 0)
    last_note_time = float(meta.get("Last Note Time", float(timestamps[-1]) if total_notes else 0.0))

    ff_factor = lookup_reference_py(
        _stats_get_int(stats, "Fever Fill Rate", 0), ref_arrays["Fever Fill Rate"], TOTAL_ROWS
    )
    ft_factor = lookup_reference_py(_stats_get_int(stats, "Fever Time", 0), ref_arrays["Fever Time"], TOTAL_ROWS)

    if fever_mask_buffer.shape[0] != total_notes:
        raise ValueError("fever_mask_buffer wrong length")

    fever_mask_head, count_fever, count_normal, _acts, _last_end = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        float(ff_factor),
        float(ft_factor),
        int(long_notes),
        float(last_note_time),
        fever_mask_buffer,
    )
    return _TimelineCtx(fever_mask_head.copy(), int(count_fever), int(count_normal))


def _build_fg_timeline_ctx(
    *,
    stats: dict,
    calc_song: dict,
    ref_arrays: dict,
    forced_counts: list[int],
) -> _FgTimelineCtx | None:
    if not forced_counts:
        return None

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    if timestamps is None:
        return None
    great_candidates = song_data.get("fg_great_candidate_timestamps", timestamps)
    use_forced_great_timing = bool(song_data.get("fg_great_candidate_timestamps") is not None)

    timestamps = np.asarray(timestamps)
    total_notes = int(timestamps.shape[0])
    if total_notes <= 0:
        return None

    meta = calc_song.get("metadata", {}) or {}
    long_notes = _safe_int(meta.get("Long Notes"), 0)
    base_ts = np.asarray(song_data.get("timestamps", timestamps))
    default_last_note = float(base_ts[-1]) if int(base_ts.shape[0]) > 0 else 0.0
    last_note_time = float(meta.get("Last Note Time", default_last_note))

    ff_factor = lookup_reference_py(
        _stats_get_int(stats, "Fever Fill Rate", 0), ref_arrays["Fever Fill Rate"], TOTAL_ROWS
    )
    ft_factor = lookup_reference_py(_stats_get_int(stats, "Fever Time", 0), ref_arrays["Fever Time"], TOTAL_ROWS)

    fever_mask_head, count_fever, count_normal, _non_fever_base, section_details = _compute_force_greats_timeline(
        timestamps,
        great_candidates,
        total_notes,
        float(ff_factor),
        float(ft_factor),
        int(long_notes),
        float(last_note_time),
        list(forced_counts),
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
        use_forced_great_timing=use_forced_great_timing,
    )
    return _FgTimelineCtx(fever_mask_head, int(count_fever), int(count_normal), section_details)


def _score_from_ctx(
    *,
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    ctx: _TimelineCtx,
) -> int:
    return int(
        fast_calculate_score(
            float(base_value),
            float(combo_mul),
            float(fever_mul),
            ctx.fever_mask_head,
            int(ctx.count_body_fever),
            int(ctx.count_body_normal),
        )
    )


def _score_fg_from_ctx(
    *,
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    primary_val: int,
    secondary_val: int,
    ctx: _FgTimelineCtx,
) -> int:
    from math import floor

    base_score = int(
        fast_calculate_score(
            float(base_value),
            float(combo_mul),
            float(fever_mul),
            ctx.fever_mask_head,
            int(ctx.count_body_fever),
            int(ctx.count_body_normal),
        )
    )

    combo_value = floor(float(base_value) * float(combo_mul))

    great_penalty_base_head = (
        floor((float(primary_val) * 2.0) * (2.0 / 3.0)) + floor(float(secondary_val) * (2.0 / 3.0)) + 150
    )
    great_penalty_base_raw = ((float(primary_val) * 2.0) * (2.0 / 3.0)) + (float(secondary_val) * (2.0 / 3.0)) + 150.0

    great_combo_value = floor(float(great_penalty_base_raw) * float(combo_mul))
    body_penalty = max(0, int(combo_value) - int(great_combo_value))

    penalty_table = build_great_penalty_table(float(base_value), float(combo_mul), float(great_penalty_base_head))
    if penalty_table:
        penalty_table[-1] = int(body_penalty)

    total_score_penalty = 0
    for detail in ctx.section_details:
        forced = _safe_int(detail.get("forced"), 0)
        if forced <= 0:
            continue
        skip_wasted = bool(detail.get("skip_wasted"))
        start_idx = _safe_int(detail.get("start_idx"), 0) + (0 if skip_wasted else 1)
        note_idx = int(start_idx)
        remaining = int(forced)
        score_penalty = 0
        while remaining > 0:
            if 0 <= note_idx < len(penalty_table):
                score_penalty += int(penalty_table[note_idx])
            else:
                score_penalty += int(body_penalty)
            note_idx += 1
            remaining -= 1
        total_score_penalty += score_penalty

    return max(0, int(base_score) - int(total_score_penalty))


def compute_team_buff_tier_leaderboards(
    *,
    entries: list[dict],
    calc_song: dict,
    ref_arrays: dict,
    cfg_dict: dict,
    limit: int = 51,
    tiers: tuple[str, ...] = ("NONE", "T1", "T5", "T10", "T15"),
) -> dict:
    """
    Re-score persisted entries under TeamBuff tiers and return per-tier leaderboards.

    This is intentionally CPU-only and designed for post-processing:
    - Uses the existing gem allocations (Stats in details) as-is.
    - Uses the existing ForceGreats config (force_details_json) as-is.
    - Produces top-N lists by base score and FG score per tier.
    """
    n = max(0, int(limit))
    if not entries or n <= 0:
        return {"tiers": {}, "meta": {"candidate_count": 0}}

    meta0 = calc_song.get("metadata", {}) or {}
    primary_color = _norm_text(meta0.get("Primary Color", ""))
    secondary_color = _norm_text(meta0.get("Secondary Color", ""))

    team_color = _resolve_team_color(cfg_dict, calc_song)
    base_team_buff = _resolve_base_team_buff(cfg_dict)

    base_effect = _team_buff_effect(base_team_buff, team_color)
    tier_list = tuple(t for t in tiers if _norm_team_buff(t))

    # Per-entry timeline cache (tier changes do not affect FT/FF, so timeline is stable per entry).
    song_data = calc_song.get("song_data", {}) or {}
    base_timestamps = song_data.get("timestamps")
    base_timestamps = np.asarray(base_timestamps) if base_timestamps is not None else np.zeros(0, dtype=np.float32)
    total_notes = int(base_timestamps.shape[0])
    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_) if total_notes > 0 else np.zeros(0, dtype=np.bool_)

    per_entry: list[dict] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        details = entry.get("details") or {}
        if not isinstance(details, dict):
            details = {}
        stats_base = details.get("Stats") or {}
        if not isinstance(stats_base, dict) or not stats_base:
            continue

        gear = _flat_item_names(entry.get("gear") or [])
        minis = _representative_mini_names_from_any(entry.get("minis") or [])

        # Base timeline + multipliers for base scoring.
        base_ctx = _build_base_timeline_ctx(
            stats=stats_base, calc_song=calc_song, ref_arrays=ref_arrays, fever_mask_buffer=fever_mask_buffer
        )
        cm_factor = lookup_reference_py(
            _stats_get_int(stats_base, "Combo Multiplier", 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS
        )
        fm_factor = lookup_reference_py(
            _stats_get_int(stats_base, "Fever Multiplier", 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS
        )

        base_pp_stat = _stats_get_int(stats_base, "Perfect Points", 0)
        base_primary_val = _stats_get_int(stats_base, primary_color, 0) if primary_color else 0
        base_secondary_val = _stats_get_int(stats_base, secondary_color, 0) if secondary_color else 0

        # Optional FG context (may have a different gem allocation than base).
        force_obj = entry.get("force")
        fg_counts = _extract_force_config_counts(force_obj) if isinstance(force_obj, dict) else []
        fg_ctx = None
        fg_cm_factor = float(cm_factor)
        fg_fm_factor = float(fm_factor)
        fg_pp_stat = int(base_pp_stat)
        fg_primary_val = int(base_primary_val)
        fg_secondary_val = int(base_secondary_val)
        if fg_counts:
            fg_stats = _force_payload_stats(force_obj, stats_base) if isinstance(force_obj, dict) else stats_base
            if not isinstance(fg_stats, dict) or not fg_stats:
                fg_stats = stats_base

            fg_ctx = _build_fg_timeline_ctx(
                stats=fg_stats, calc_song=calc_song, ref_arrays=ref_arrays, forced_counts=fg_counts
            )
            fg_cm_factor = lookup_reference_py(
                _stats_get_int(fg_stats, "Combo Multiplier", 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS
            )
            fg_fm_factor = lookup_reference_py(
                _stats_get_int(fg_stats, "Fever Multiplier", 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS
            )
            fg_pp_stat = _stats_get_int(fg_stats, "Perfect Points", 0)
            fg_primary_val = _stats_get_int(fg_stats, primary_color, 0) if primary_color else 0
            fg_secondary_val = _stats_get_int(fg_stats, secondary_color, 0) if secondary_color else 0

        per_entry.append(
            {
                "gear": gear,
                "minis": minis,
                "source_score": _safe_int(entry.get("score"), 0),
                "source_fg_score": _safe_int(entry.get("fg_score"), 0),
                "base": {
                    "ctx": base_ctx,
                    "cm": float(cm_factor),
                    "fm": float(fm_factor),
                    "pp": int(base_pp_stat),
                    "p_val": int(base_primary_val),
                    "s_val": int(base_secondary_val),
                },
                "fg": None
                if fg_ctx is None
                else {
                    "ctx": fg_ctx,
                    "cm": float(fg_cm_factor),
                    "fm": float(fg_fm_factor),
                    "pp": int(fg_pp_stat),
                    "p_val": int(fg_primary_val),
                    "s_val": int(fg_secondary_val),
                    "counts": fg_counts,
                    "config": (
                        (force_obj.get("ForceGreats", {}) or {}).get("config")
                        if isinstance(force_obj, dict)
                        else None
                    ),
                },
            }
        )

    # Compute tiered scores for all retained entries.
    tiers_out: dict[str, dict] = {}
    for tier in tier_list:
        target_effect = _team_buff_effect(tier, team_color)

        delta_pp = int(target_effect.get("Perfect Points", 0) - base_effect.get("Perfect Points", 0))
        delta_primary = (
            int(target_effect.get(primary_color, 0) - base_effect.get(primary_color, 0)) if primary_color else 0
        )
        delta_secondary = (
            int(target_effect.get(secondary_color, 0) - base_effect.get(secondary_color, 0)) if secondary_color else 0
        )

        base_ranked: list[dict] = []
        fg_ranked: list[dict] = []

        for e in per_entry:
            b = e["base"]
            pp_stat = int(b["pp"]) + delta_pp
            p_val = int(b["p_val"]) + delta_primary
            s_val = int(b["s_val"]) + delta_secondary
            pp_factor = lookup_reference_py(pp_stat, ref_arrays["Perfect Points"], TOTAL_ROWS)
            base_value = (p_val * 2) + s_val + float(pp_factor)
            base_score = _score_from_ctx(base_value=base_value, combo_mul=b["cm"], fever_mul=b["fm"], ctx=b["ctx"])

            fg_score = 0
            fg = e.get("fg")
            if fg and fg.get("ctx") is not None:
                pp_stat_fg = int(fg["pp"]) + delta_pp
                p_val_fg = int(fg["p_val"]) + delta_primary
                s_val_fg = int(fg["s_val"]) + delta_secondary
                pp_factor_fg = lookup_reference_py(pp_stat_fg, ref_arrays["Perfect Points"], TOTAL_ROWS)
                base_value_fg = (p_val_fg * 2) + s_val_fg + float(pp_factor_fg)
                fg_score = _score_fg_from_ctx(
                    base_value=base_value_fg,
                    combo_mul=float(fg["cm"]),
                    fever_mul=float(fg["fm"]),
                    primary_val=int(p_val_fg),
                    secondary_val=int(s_val_fg),
                    ctx=fg["ctx"],
                )

            out_row = {
                "gear": e["gear"],
                "minis": e["minis"],
                "score": int(base_score),
                "fg_score": int(fg_score) if int(fg_score) > 0 else 0,
                "source_score": int(e["source_score"]),
                "source_fg_score": int(e["source_fg_score"]),
            }
            base_ranked.append(out_row)

            if fg and fg.get("ctx") is not None and int(fg_score) > int(base_score):
                fg_ranked.append(
                    {
                        "gear": e["gear"],
                        "minis": e["minis"],
                        "score": int(base_score),
                        "fg_score": int(fg_score),
                        "source_score": int(e["source_score"]),
                        "source_fg_score": int(e["source_fg_score"]),
                        "force_config": fg.get("config"),
                    }
                )

        base_ranked.sort(key=lambda r: int(r.get("score", 0) or 0), reverse=True)
        fg_ranked.sort(key=lambda r: int(r.get("fg_score", 0) or 0), reverse=True)

        base_top = base_ranked[:n]
        fg_top = fg_ranked[:n]
        tiers_out[str(tier)] = {"base_top51": base_top, "fg_top51": fg_top}

    return {
        "meta": {
            "candidate_count": int(len(per_entry)),
            "team_color": team_color,
            "base_team_buff": base_team_buff,
            "primary_color": primary_color,
            "secondary_color": secondary_color,
        },
        "tiers": tiers_out,
    }


def build_team_buff_tier_db_batches(
    *,
    entries: list[dict],
    calc_song: dict,
    ref_arrays: dict,
    cfg_dict: dict,
    limit: int = 51,
    tiers: tuple[str, ...] = ("NONE", "T1", "T5", "T10", "T15"),
) -> dict[str, list[dict]]:
    """
    Return DB-ready entry batches per tier.

    Output format:
        { "T5": [ {score, fg_score, gear, minis, details, force}, ... ], ... }

    Selection:
    - union(top-N by base score, top-N by FG score) per tier
    """
    payload = compute_team_buff_tier_leaderboards(
        entries=entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        limit=limit,
        tiers=tiers,
    )

    team_color = _resolve_team_color(cfg_dict, calc_song)
    base_team_buff = _resolve_base_team_buff(cfg_dict)

    # Map original entries by a stable key (order-invariant names).
    def _stable_key_from_entry(e: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return (
            tuple(sorted(_flat_item_names(e.get("gear")))),
            tuple(sorted(_representative_mini_names_from_any(e.get("minis")))),
        )

    orig_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], dict] = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        orig_by_key[_stable_key_from_entry(e)] = e

    batches: dict[str, list[dict]] = {}
    for tier, tier_payload in (payload.get("tiers") or {}).items():
        delta_map = _team_buff_delta_map(
            base_team_buff=base_team_buff, target_team_buff=str(tier), team_color=team_color
        )
        base_top = tier_payload.get("base_top51") or []
        fg_top = tier_payload.get("fg_top51") or []

        base_score_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}
        fg_score_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}

        for r in base_top:
            if not isinstance(r, dict):
                continue
            k = (
                tuple(sorted(_flat_item_names(r.get("gear")))),
                tuple(sorted(_representative_mini_names_from_any(r.get("minis")))),
            )
            base_score_by_key[k] = _safe_int(r.get("score"), 0)
            fg_score_by_key[k] = _safe_int(r.get("fg_score"), 0)

        for r in fg_top:
            if not isinstance(r, dict):
                continue
            k = (
                tuple(sorted(_flat_item_names(r.get("gear")))),
                tuple(sorted(_representative_mini_names_from_any(r.get("minis")))),
            )
            fg_score_by_key[k] = _safe_int(r.get("fg_score"), 0)
            if k not in base_score_by_key:
                base_score_by_key[k] = _safe_int(r.get("score"), 0)

        selected_keys = set(base_score_by_key.keys()) | set(fg_score_by_key.keys())
        out_entries: list[dict] = []
        for k in selected_keys:
            orig = orig_by_key.get(k)
            if not isinstance(orig, dict):
                continue

            score_out = int(base_score_by_key.get(k, 0) or 0)
            fg_score_out = int(fg_score_by_key.get(k, 0) or 0)

            # Keep payloads internally consistent: adjust Stats + FG score fields for this tier.
            details_out = _apply_details_delta(copy.deepcopy(orig.get("details") or {}), delta_map)
            force_out = _apply_force_delta(
                copy.deepcopy(orig.get("force")),
                delta=delta_map,
                fg_score=fg_score_out,
            )

            out_entries.append(
                {
                    "score": score_out,
                    "fg_score": fg_score_out,
                    "gear": _flat_item_names(orig.get("gear")),
                    "minis": _representative_mini_names_from_any(orig.get("minis")),
                    "details": details_out,
                    "force": force_out,
                }
            )
        batches[str(tier)] = out_entries

    return batches
