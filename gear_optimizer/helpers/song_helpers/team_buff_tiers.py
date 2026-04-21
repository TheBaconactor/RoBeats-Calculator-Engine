from __future__ import annotations

import os
import re
from math import ceil
from typing import Any

import numpy as np

from ...core.constants import FEVER_FILL_BASE_RATE, TOTAL_ROWS
from ...core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    TEAM_BUFF_ELEMENTS,
    canonicalize_team_buff,
    normalize_team_buff_sequence,
    team_buff_effect,
)
from ...core.time_quantize import quantize_to_int_ms
from ...data.loadout_equivalence import representative_mini_names
from ...solver.scoring_core import lookup_reference_py

_ELEMENTS = TEAM_BUFF_ELEMENTS


def _norm_text(v: object) -> str:
    return str(v or "").strip()


def _truthy_cfg(v: object) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


_MINI_LITERAL_RE = re.compile(r"""['"]([^'"]+)['"]""")

_HITSIM_APPLY_CODE_TO_STR: dict[int, str] = {0: "FG", 1: "ALL"}
_HITSIM_DIST_CODE_TO_STR: dict[int, str] = {0: "uniform"}
_HITSIM_GREAT_MODE_CODE_TO_STR: dict[int, str] = {0: "late", 1: "early", 2: "full"}


def _hitsim_params_from_details(details: object) -> tuple[int, str, str, str] | None:
    """
    Extract persisted HumanHitSim context for deterministic recompute.

    Preferred compact format:
        details["hs"] = [seed, apply_to_code, dist_code, great_mode_code]
    """
    if not isinstance(details, dict):
        return None

    hs = details.get("hs")
    if isinstance(hs, (list, tuple)) and len(hs) >= 4:
        try:
            seed = int(hs[0] or 0)
        except Exception:
            seed = 0
        if seed <= 0:
            return None
        try:
            apply_code = int(hs[1] or 0)
        except Exception:
            apply_code = 0
        try:
            dist_code = int(hs[2] or 0)
        except Exception:
            dist_code = 0
        try:
            mode_code = int(hs[3] or 0)
        except Exception:
            mode_code = 0
        apply_to = _HITSIM_APPLY_CODE_TO_STR.get(int(apply_code), "FG")
        dist = _HITSIM_DIST_CODE_TO_STR.get(int(dist_code), "uniform")
        mode = _HITSIM_GREAT_MODE_CODE_TO_STR.get(int(mode_code), "late")
        return (int(seed), str(apply_to), str(dist), str(mode))

    # Back-compat: verbose key style.
    if details.get("HumanHitSimSeed") is not None:
        try:
            seed = int(details.get("HumanHitSimSeed") or 0)
        except Exception:
            seed = 0
        if seed <= 0:
            return None
        apply_to = str(details.get("HumanHitSimApplyTo", "FG") or "FG").strip().upper()
        if apply_to not in {"FG", "ALL"}:
            apply_to = "FG"
        dist = str(details.get("HumanHitSimDistribution", "uniform") or "uniform").strip().lower() or "uniform"
        mode = str(details.get("HumanHitSimGreatMode", "late") or "late").strip().lower() or "late"
        return (int(seed), apply_to, dist, mode)

    return None


def _shallow_clone_calc_song(calc_song: dict) -> dict:
    meta0 = calc_song.get("metadata", {}) or {}
    song_data0 = calc_song.get("song_data", {}) or {}
    out = dict(calc_song)
    out["metadata"] = dict(meta0) if isinstance(meta0, dict) else {}
    out["song_data"] = dict(song_data0) if isinstance(song_data0, dict) else {}
    return out


def _mini_names_from_text(text: str) -> list[str]:
    s = text.strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        matches = [m.group(1).strip() for m in _MINI_LITERAL_RE.finditer(s)]
        matches = [m for m in matches if m]
        if matches:
            return matches
        inner = s[1:-1].strip()
        if inner:
            parts = [p.strip().strip("'\"") for p in inner.split(",")]
            cleaned = [p for p in parts if p]
            if cleaned:
                return cleaned
    return [s]


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
        if isinstance(slot, (list, tuple)):
            names: list[str] = []
            for raw in slot:
                if isinstance(raw, dict):
                    s = _norm_text(raw.get("Name", raw.get("name", "")))
                    if s:
                        names.append(s)
                    continue
                if isinstance(raw, str):
                    for name in _mini_names_from_text(raw):
                        if name:
                            names.append(name)
                    continue
                s = _norm_text(raw)
                for name in _mini_names_from_text(s):
                    if name:
                        names.append(name)
            names = sorted(set(n for n in names if n))
            if names:
                groups.append(names)
            continue

        if isinstance(slot, dict):
            s = _norm_text(slot.get("Name", slot.get("name", "")))
            names = _mini_names_from_text(s)
            if names:
                groups.append(sorted(set(n for n in names if n)))
            continue

        if isinstance(slot, str):
            names = _mini_names_from_text(slot)
            if names:
                groups.append(sorted(set(n for n in names if n)))
            continue

        s = _norm_text(slot)
        names = _mini_names_from_text(s)
        if names:
            groups.append(sorted(set(n for n in names if n)))
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
    return canonicalize_team_buff(v)


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


def _resolve_team_colors_for_tiering(
    cfg_dict: dict,
    calc_song: dict,
    *,
    base_team_color_override: object = None,
    target_team_color_override: object = None,
) -> tuple[str, str]:
    """
    Resolve source/target TeamColor for tier delta computation.

    - source/base color: color used by persisted baseline rows.
    - target color: color to evaluate output tiers against.
    """
    resolved = _resolve_team_color(cfg_dict, calc_song)
    if base_team_color_override is None:
        base_team_color = resolved
    else:
        base_team_color = _norm_text(base_team_color_override)

    if target_team_color_override is None:
        target_team_color = base_team_color
    else:
        target_team_color = _norm_text(target_team_color_override)

    return str(base_team_color), str(target_team_color)


def _team_buff_effect(team_buff: str, team_color: str) -> dict[str, int]:
    return team_buff_effect(team_buff, team_color)


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


def _force_counts_to_fp_targets(
    forced_counts: list[int],
    *,
    calc_song: dict,
    ff_stat: int,
    ref_arrays: dict,
) -> list[int]:
    """
    Convert persisted forced-count configs back into the GPU finder's FP-target form.

    Compact DB payloads persist `ForceGreats.config` as actual forced Great counts per
    section, but the low-level GPU finder consumes fill-penalty targets (FP targets).
    Replaying persisted counts directly into the GPU solver underestimates FG scores.
    """
    counts = [max(0, int(x)) for x in list(forced_counts or [])]
    if not counts:
        return []

    try:
        song_data = calc_song.get("song_data", {}) or {}
        timestamps = song_data.get("timestamps")
        total_notes = int(len(timestamps)) if timestamps is not None else 0
    except Exception:
        total_notes = 0

    if total_notes <= 0:
        try:
            total_notes = _safe_int((calc_song.get("metadata", {}) or {}).get("Total Notes"), 0)
        except Exception:
            total_notes = 0

    try:
        long_notes = _safe_int((calc_song.get("metadata", {}) or {}).get("Long Notes"), 0)
    except Exception:
        long_notes = 0

    try:
        ff_factor = float(lookup_reference_py(int(ff_stat), ref_arrays["Fever Fill Rate"], TOTAL_ROWS))
        raw_fill = max(0.0, float(total_notes - long_notes) * float(FEVER_FILL_BASE_RATE)) * float(ff_factor)
        base_notes = int(ceil(raw_fill))
    except Exception:
        return counts

    fp_targets: list[int] = []
    for forced in counts:
        if forced <= 0:
            fp_targets.append(0)
            continue
        fp_targets.append(max(0, int(ceil(raw_fill + (float(forced) * 0.5)) - base_notes)))
    return fp_targets


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(str(v)) if v is not None else int(default)
    except Exception:
        try:
            return int(float(str(v)))
        except Exception:
            return int(default)


def _floor_to_int_ms(timestamps_sec: np.ndarray) -> np.ndarray:
    return quantize_to_int_ms(timestamps_sec)


def _build_base_hitsim_ctx(calc_song: dict) -> dict | None:
    if not isinstance(calc_song, dict):
        return None
    meta = calc_song.get("metadata", {}) or {}
    if not meta.get("HumanHitSimApplied"):
        return None
    apply_to = str(meta.get("HumanHitSimApplyTo", "") or "").strip().upper()
    if apply_to != "ALL":
        return None
    song_data = calc_song.get("song_data", {}) or {}
    chart_ts = song_data.get("chart_timestamps")
    timestamps = song_data.get("timestamps")
    if chart_ts is None or timestamps is None:
        return None
    chart_ms = _floor_to_int_ms(np.asarray(chart_ts, dtype=np.float32))
    sim_ms = _floor_to_int_ms(np.asarray(timestamps, dtype=np.float32))
    total_notes = int(np.asarray(timestamps).shape[0])
    if total_notes <= 0:
        return None
    n = min(int(chart_ms.shape[0]), int(sim_ms.shape[0]), int(total_notes))
    if n <= 0:
        return None
    long_notes = _safe_int(meta.get("Long Notes"), 0)
    return {
        "chart_ms": chart_ms,
        "sim_ms": sim_ms,
        "n": int(n),
        "total_notes": int(total_notes),
        "long_notes": int(long_notes),
    }


def _base_hitsim_delta_for_stats(*, stats: dict, ref_arrays: dict, ctx: dict, ff_cache: dict[int, float]) -> int | None:
    if not isinstance(stats, dict) or not stats:
        return None
    try:
        ff_stat = _stats_get_int(stats, "Fever Fill Rate", 0)
    except Exception:
        ff_stat = 0
    try:
        ff_factor = ff_cache.get(int(ff_stat))
    except Exception:
        ff_factor = None
    if ff_factor is None:
        try:
            ff_factor = lookup_reference_py(ff_stat, ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
        except Exception:
            return None
        try:
            ff_cache[int(ff_stat)] = float(ff_factor)
        except Exception:
            pass

    total_notes = int(ctx.get("total_notes", 0) or 0)
    long_notes = int(ctx.get("long_notes", 0) or 0)
    non_fever_cas = (total_notes - long_notes) * FEVER_FILL_BASE_RATE
    non_fever_base = ceil(non_fever_cas * float(ff_factor))
    notes_to_fill = int(non_fever_base) - 1
    end_normal_idx = min(int(notes_to_fill), int(total_notes))
    if end_normal_idx <= 0:
        return None
    n = int(ctx.get("n", 0) or 0)
    if end_normal_idx >= n:
        return None
    chart_ms = ctx.get("chart_ms")
    sim_ms = ctx.get("sim_ms")
    if chart_ms is None or sim_ms is None:
        return None
    return int(sim_ms[end_normal_idx]) - int(chart_ms[end_normal_idx])


def _team_buff_delta_map(
    *,
    base_team_buff: str,
    target_team_buff: str,
    base_team_color: str,
    target_team_color: str,
) -> dict[str, int]:
    base = _team_buff_effect(base_team_buff, base_team_color)
    target = _team_buff_effect(target_team_buff, target_team_color)
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


def _ensure_stats_include_base_effect(stats: dict, base_effect: dict[str, int]) -> dict:
    """
    Ensure `stats` includes the base TeamBuff effect when tiering is expressed as deltas vs base.

    Some historical DB repairs/backfills computed `details["Stats"]` as loadout-only (no TeamBuff),
    while tier recomputation assumes the saved stats represent the runtime base (auto mode => T5).

    Heuristic: if Perfect Points is less than the base PP add, treat the stats as missing TeamBuff
    and add the base effect.
    """
    if not isinstance(stats, dict) or not stats or not isinstance(base_effect, dict) or not base_effect:
        return stats if isinstance(stats, dict) else {}
    base_pp = _safe_int(base_effect.get("Perfect Points", 0), 0)
    if base_pp <= 0:
        return dict(stats)
    pp0 = _safe_int(stats.get("Perfect Points", 0), 0)
    if pp0 < base_pp:
        return _apply_stat_delta(stats, base_effect)
    return dict(stats)


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

    # Nested force payload format: `{score, gear, minis, details: {...}}`
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


def compute_team_buff_tier_leaderboards(
    *,
    entries: list[dict],
    calc_song: dict,
    ref_arrays: dict,
    cfg_dict: dict,
    limit: int = 51,
    tiers: tuple[str, ...] = DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    base_team_color_override: object = None,
    target_team_color_override: object = None,
) -> dict:
    """
    Re-score persisted entries under TeamBuff tiers and return per-tier leaderboards.

    Base scoring uses the GPU fixed-scoring path and FG scoring uses the GPU ForceGreats
    kernel (fixed-stats mode) so on-demand tier computation matches production scoring
    semantics (including GPU timeline behavior).

    This is designed for post-processing:
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

    base_team_color, target_team_color = _resolve_team_colors_for_tiering(
        cfg_dict,
        calc_song,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
    )
    base_team_buff = _resolve_base_team_buff(cfg_dict)

    base_effect = _team_buff_effect(base_team_buff, base_team_color)
    tier_list = normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS)

    # Group entries by persisted HumanHitSim context (if any). This matters when
    # HumanHitSim.Seed=0 chooses a different random seed per run; persisted rows
    # can come from multiple seeds and must be rescored against their own timing.
    meta_calc = calc_song.get("metadata", {}) or {}
    calc_song_already_hitsim = bool(meta_calc.get("HumanHitSimApplied"))
    entry_groups: dict[tuple[int, str, str, str] | None, list[dict]] = {}
    if calc_song_already_hitsim:
        entry_groups[None] = list(entries)
    else:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            details0 = entry.get("details")
            hs_params = _hitsim_params_from_details(details0)
            entry_groups.setdefault(hs_params, []).append(entry)

    calc_song_by_hitsim: dict[tuple[int, str, str, str], dict] = {}
    per_entry: list[dict] = []

    for hs_key, group_entries in entry_groups.items():
        group_song = calc_song
        if hs_key is not None:
            cached = calc_song_by_hitsim.get(hs_key)
            if cached is None:
                seed, apply_to, dist, mode = hs_key
                song1 = _shallow_clone_calc_song(calc_song)
                # Defensive: ensure we can re-apply even if callers accidentally pass a dirty meta.
                try:
                    meta1 = song1.get("metadata", {}) or {}
                    if isinstance(meta1, dict):
                        for k in (
                            "HumanHitSimApplied",
                            "HumanHitSimSeed",
                            "HumanHitSimApplyTo",
                            "HumanHitSimDistribution",
                            "HumanHitSimGreatMode",
                            "HumanHitSimSeedIsRandom",
                            "HumanHitSimDebug",
                            "HumanHitSimPlanned",
                        ):
                            meta1.pop(k, None)
                        song1["metadata"] = meta1
                except Exception:
                    pass

                try:
                    from ...solver.hit_simulation import apply_human_hit_sim

                    apply_human_hit_sim(
                        song1,
                        cfg_dict={
                            "HumanHitSim": {
                                "Enabled": "1",
                                "ApplyTo": str(apply_to),
                                "Seed": int(seed),
                                "Distribution": str(dist),
                                "GreatMode": str(mode),
                            }
                        },
                    )
                except Exception:
                    # Fallback: score using chart timestamps (better than crashing).
                    pass

                cached = song1
                calc_song_by_hitsim[hs_key] = cached
            group_song = cached

        for entry in group_entries:
            if not isinstance(entry, dict):
                continue
            details = entry.get("details") or {}
            if not isinstance(details, dict):
                details = {}
            stats_base_raw = details.get("Stats") or {}
            stats_base = (
                _ensure_stats_include_base_effect(stats_base_raw, base_effect)
                if isinstance(stats_base_raw, dict)
                else {}
            )
            if not isinstance(stats_base, dict) or not stats_base:
                continue

            gear = _flat_item_names(entry.get("gear") or [])
            minis = _representative_mini_names_from_any(entry.get("minis") or [])

            # Base multipliers/indices for GPU fixed scoring (tier changes do not affect CM/FM/FT/FF).
            ft_idx = _stats_get_int(stats_base, "Fever Time", 0)
            ff_idx = _stats_get_int(stats_base, "Fever Fill Rate", 0)
            cm_factor = lookup_reference_py(
                _stats_get_int(stats_base, "Combo Multiplier", 0), ref_arrays["Combo Multiplier"], TOTAL_ROWS
            )
            fm_factor = lookup_reference_py(
                _stats_get_int(stats_base, "Fever Multiplier", 0), ref_arrays["Fever Multiplier"], TOTAL_ROWS
            )

            base_pp_stat = _stats_get_int(stats_base, "Perfect Points", 0)
            base_primary_val = _stats_get_int(stats_base, primary_color, 0) if primary_color else 0
            base_secondary_val = _stats_get_int(stats_base, secondary_color, 0) if secondary_color else 0

            # Optional FG stats snapshot (may have a different gem allocation than base).
            force_obj = entry.get("force")
            fg_counts = _extract_force_config_counts(force_obj) if isinstance(force_obj, dict) else []
            fg_pp_stat = int(base_pp_stat)
            fg_primary_val = int(base_primary_val)
            fg_secondary_val = int(base_secondary_val)
            fg_ft_stat = int(ft_idx)
            fg_ff_stat = int(ff_idx)
            fg_cm_stat = _stats_get_int(stats_base, "Combo Multiplier", 0)
            fg_fm_stat = _stats_get_int(stats_base, "Fever Multiplier", 0)
            fg_fp_targets = []
            if fg_counts:
                fg_stats0 = _force_payload_stats(force_obj, stats_base) if isinstance(force_obj, dict) else stats_base
                fg_stats = (
                    _ensure_stats_include_base_effect(fg_stats0, base_effect) if isinstance(fg_stats0, dict) else {}
                )
                if not isinstance(fg_stats, dict) or not fg_stats:
                    fg_stats = stats_base

                fg_pp_stat = _stats_get_int(fg_stats, "Perfect Points", 0)
                fg_primary_val = _stats_get_int(fg_stats, primary_color, 0) if primary_color else 0
                fg_secondary_val = _stats_get_int(fg_stats, secondary_color, 0) if secondary_color else 0
                fg_ft_stat = _stats_get_int(fg_stats, "Fever Time", 0)
                fg_ff_stat = _stats_get_int(fg_stats, "Fever Fill Rate", 0)
                fg_cm_stat = _stats_get_int(fg_stats, "Combo Multiplier", 0)
                fg_fm_stat = _stats_get_int(fg_stats, "Fever Multiplier", 0)
                fg_fp_targets = _force_counts_to_fp_targets(
                    fg_counts,
                    calc_song=group_song,
                    ff_stat=int(fg_ff_stat),
                    ref_arrays=ref_arrays,
                )

            per_entry.append(
                {
                    "loadout_hash": _norm_text(entry.get("loadout_hash", "")),
                    "song": group_song,
                    "gear": gear,
                    "minis": minis,
                    "source_score": _safe_int(entry.get("score"), 0),
                    "source_fg_base_score": _safe_int(entry.get("fg_base_score"), _safe_int(entry.get("score"), 0)),
                    "source_fg_score": _safe_int(entry.get("fg_score"), 0),
                    "base": {
                        "cm": float(cm_factor),
                        "fm": float(fm_factor),
                        "ft_idx": int(ft_idx),
                        "ff_idx": int(ff_idx),
                        "pp": int(base_pp_stat),
                        "p_val": int(base_primary_val),
                        "s_val": int(base_secondary_val),
                    },
                    "fg": None
                    if not fg_counts
                    else {
                        "pp": int(fg_pp_stat),
                        "p_val": int(fg_primary_val),
                        "s_val": int(fg_secondary_val),
                        "ft_stat": int(fg_ft_stat),
                        "ff_stat": int(fg_ff_stat),
                        "cm_stat": int(fg_cm_stat),
                        "fm_stat": int(fg_fm_stat),
                        "counts": fg_counts,
                        "fp_targets": fg_fp_targets,
                        "config": (
                            (force_obj.get("ForceGreats", {}) or {}).get("config")
                            if isinstance(force_obj, dict)
                            else None
                        ),
                    },
                }
            )

    # Compute tiered scores for all retained entries.
    from ...solver.scoring.gpu_solver import _GPU_LOCK
    from ...solver.taichi_gem.api.fixed_scoring import score_fixed_stats_gpu

    # Group by (possibly HitSim-mutated) calc_song object so we can batch GPU fixed scoring per song context.
    per_entry_by_song_id: dict[int, list[dict]] = {}
    song_by_id: dict[int, dict] = {}
    for e in per_entry:
        song0 = e.get("song")
        if not isinstance(song0, dict):
            continue
        sid = int(id(song0))
        song_by_id.setdefault(sid, song0)
        per_entry_by_song_id.setdefault(sid, []).append(e)

    tier_deltas: dict[str, tuple[int, int, int]] = {}
    for tier in tier_list:
        target_effect = _team_buff_effect(tier, target_team_color)
        tier_deltas[str(tier)] = (
            int(target_effect.get("Perfect Points", 0) - base_effect.get("Perfect Points", 0)),
            int(target_effect.get(primary_color, 0) - base_effect.get(primary_color, 0)) if primary_color else 0,
            int(target_effect.get(secondary_color, 0) - base_effect.get(secondary_color, 0)) if secondary_color else 0,
        )

    # Precompute all FG scores for all tiers in the fewest possible GPU calls.
    fg_scores_by_sid: dict[int, dict[str, list[int]]] = {}
    have_fg = any(isinstance(e.get("fg"), dict) for e in per_entry)
    if have_fg:
        from ...solver.taichi_gem.force_greats.api import solve_force_greats_finder_gpu
        from ...solver.taichi_gem.force_greats.fields import FG_MAX_SECTIONS

        for sid, group_entries in per_entry_by_song_id.items():
            tier_to_scores: dict[str, list[int]] = {str(t): [0] * len(group_entries) for t in tier_list}

            group_song = song_by_id.get(sid)
            if not isinstance(group_song, dict):
                fg_scores_by_sid[sid] = tier_to_scores
                continue

            song_data = group_song.get("song_data", {}) or {}
            ts_raw = song_data.get("fg_timestamps", song_data.get("timestamps"))
            if ts_raw is None:
                fg_scores_by_sid[sid] = tier_to_scores
                continue
            timestamps_np = np.asarray(ts_raw, dtype=np.float32)
            great_raw = song_data.get("fg_great_candidate_timestamps")
            great_np = np.asarray(great_raw, dtype=np.float32) if great_raw is not None else None

            meta = group_song.get("metadata", {}) or {}
            long_notes = _safe_int(meta.get("Long Notes"), 0)
            base_ts_raw = song_data.get("timestamps", ts_raw)
            base_ts = np.asarray(base_ts_raw, dtype=np.float32)
            default_last_note = float(base_ts[-1]) if int(base_ts.shape[0]) > 0 else 0.0
            last_note_time = float(meta.get("Last Note Time", default_last_note))

            # Group by forced-count config; each config requires one FG GPU call.
            counts_to_indices: dict[tuple[int, ...], list[int]] = {}
            for idx, e in enumerate(group_entries):
                fg = e.get("fg")
                if not isinstance(fg, dict):
                    continue
                counts0 = fg.get("fp_targets")
                if not isinstance(counts0, (list, tuple)) or not counts0:
                    continue
                counts_t = tuple(int(x) for x in counts0)
                if not counts_t:
                    continue
                if int(len(counts_t)) > int(FG_MAX_SECTIONS):
                    # Production FG solver is limited to FG_MAX_SECTIONS; skip rather than crashing.
                    continue
                counts_to_indices.setdefault(counts_t, []).append(int(idx))

            for counts_t, idxs in counts_to_indices.items():
                n_sections = int(len(counts_t))
                if n_sections <= 0:
                    continue

                genomes: list[dict[str, Any]] = []
                for t in tier_list:
                    dpp, dp, ds = tier_deltas[str(t)]
                    for idx in idxs:
                        fg = group_entries[idx].get("fg") or {}
                        genomes.append(
                            {
                                "base_pp": int(fg.get("pp", 0) or 0) + int(dpp),
                                "base_cm": int(fg.get("cm_stat", 0) or 0),
                                "base_fm": int(fg.get("fm_stat", 0) or 0),
                                "base_ft_stat": int(fg.get("ft_stat", 0) or 0),
                                "base_ff_stat": int(fg.get("ff_stat", 0) or 0),
                                "base_p_val": int(fg.get("p_val", 0) or 0) + int(dp),
                                "base_s_val": int(fg.get("s_val", 0) or 0) + int(ds),
                            }
                        )
                if not genomes:
                    continue

                with _GPU_LOCK:
                    out_raw = solve_force_greats_finder_gpu(
                        genomes,
                        timestamps_np,
                        great_np,
                        int(long_notes),
                        float(last_note_time),
                        [counts_t],
                        [(0, 0)],
                        n_sections=n_sections,
                        is_p_ft=0,
                        is_s_ft=0,
                        is_p_ff=0,
                        is_s_ff=0,
                        is_p_pp=0,
                        is_s_pp=0,
                        is_p_cm=0,
                        is_s_cm=0,
                        is_p_fm=0,
                        is_s_fm=0,
                        is_p_ov=0,
                        is_s_ov=0,
                        ref_arrays=ref_arrays,
                        total_budget=0,
                        return_raw=True,
                    )

                if not isinstance(out_raw, dict):
                    continue
                final_scores = out_raw.get("final_score")
                if final_scores is None:
                    continue
                final_np = np.asarray(final_scores, dtype=np.int32)
                if int(final_np.shape[0]) != len(genomes):
                    continue

                k = 0
                for t in tier_list:
                    tier_key = str(t)
                    out_list = tier_to_scores.get(tier_key)
                    if out_list is None:
                        k += len(idxs)
                        continue
                    for idx in idxs:
                        out_list[idx] = int(final_np[k])
                        k += 1

            fg_scores_by_sid[sid] = tier_to_scores
    else:
        for sid, group_entries in per_entry_by_song_id.items():
            fg_scores_by_sid[sid] = {str(t): [0] * len(group_entries) for t in tier_list}

    tiers_out: dict[str, dict] = {}
    for tier in tier_list:
        delta_pp, delta_primary, delta_secondary = tier_deltas[str(tier)]

        base_ranked: list[dict] = []
        fg_ranked: list[dict] = []

        for sid, group_entries in per_entry_by_song_id.items():
            group_song = song_by_id.get(sid)
            if not isinstance(group_song, dict) or not group_entries:
                continue

            base_inputs: list[dict[str, Any]] = []
            for e in group_entries:
                b = e.get("base") or {}
                pp_stat = int(b.get("pp", 0) or 0) + int(delta_pp)
                p_val = int(b.get("p_val", 0) or 0) + int(delta_primary)
                s_val = int(b.get("s_val", 0) or 0) + int(delta_secondary)
                pp_factor = lookup_reference_py(pp_stat, ref_arrays["Perfect Points"], TOTAL_ROWS)
                base_value = (p_val * 2) + s_val + float(pp_factor)
                base_inputs.append(
                    {
                        "base_value": float(base_value),
                        "combo_mul": float(b.get("cm", 1.0) or 1.0),
                        "fever_mul": float(b.get("fm", 1.0) or 1.0),
                        "ft_idx": int(b.get("ft_idx", 0) or 0),
                        "ff_idx": int(b.get("ff_idx", 0) or 0),
                    }
                )

            with _GPU_LOCK:
                base_scores = score_fixed_stats_gpu(base_inputs, group_song, ref_arrays=ref_arrays)

            fg_scores_for_tier = (fg_scores_by_sid.get(sid) or {}).get(str(tier)) if have_fg else None

            for i, (e, base_score) in enumerate(zip(group_entries, base_scores)):
                fg_score = 0
                if fg_scores_for_tier is not None and i < int(len(fg_scores_for_tier)):
                    fg_score = int(fg_scores_for_tier[i] or 0)
                fg = e.get("fg")
                source_fg_base_compare_score = int(e.get("source_fg_base_score") or 0)
                if source_fg_base_compare_score <= 0:
                    source_fg_base_compare_score = int(base_score)
                # Public derived-tier views should surface FG rows when the replayed
                # target-tier FG score beats the replayed target-tier base score.
                # Preserve the source compact DB pairing separately for debugging and
                # baseline-tier canonical semantics.
                fg_visibility_compare_score = int(base_score)
                if str(tier).strip().upper() == str(base_team_buff).strip().upper():
                    fg_visibility_compare_score = int(source_fg_base_compare_score)

                out_row = {
                    "loadout_hash": e.get("loadout_hash") or "",
                    "gear": e.get("gear") or [],
                    "minis": e.get("minis") or [],
                    "score": int(base_score),
                    "fg_score": int(fg_score) if int(fg_score) > 0 else 0,
                    "source_score": int(e.get("source_score") or 0),
                    "source_fg_score": int(e.get("source_fg_score") or 0),
                }
                base_ranked.append(out_row)

                if isinstance(fg, dict) and int(fg_score) > int(fg_visibility_compare_score):
                    fg_ranked.append(
                        {
                            "loadout_hash": e.get("loadout_hash") or "",
                            "gear": e.get("gear") or [],
                            "minis": e.get("minis") or [],
                            "score": int(base_score),
                            "fg_base_score": int(fg_visibility_compare_score),
                            "fg_score": int(fg_score),
                            "source_score": int(e.get("source_score") or 0),
                            "source_fg_base_score": int(e.get("source_fg_base_score") or 0),
                            "source_fg_score": int(e.get("source_fg_score") or 0),
                            "force_config": fg.get("config"),
                        }
                    )

        base_ranked.sort(
            key=lambda r: (
                -int(r.get("score", 0) or 0),
                str(r.get("loadout_hash") or ""),
            )
        )
        fg_ranked.sort(
            key=lambda r: (
                -int(r.get("fg_score", 0) or 0),
                str(r.get("loadout_hash") or ""),
            )
        )

        base_top = base_ranked[:n]
        fg_top = fg_ranked[:n]
        tiers_out[str(tier)] = {"base_top51": base_top, "fg_top51": fg_top}

    return {
        "meta": {
            "candidate_count": int(len(per_entry)),
            "team_color": target_team_color,
            "base_team_color": base_team_color,
            "target_team_color": target_team_color,
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
    tiers: tuple[str, ...] = DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    base_team_color_override: object = None,
    target_team_color_override: object = None,
) -> dict[str, list[dict]]:
    """
    Return DB-ready entry batches per tier.

    Output format:
        { "T5": [ {score, fg_score, gear, minis, details, force}, ... ], ... }

    Selection:
    - union(top-N by base score, top-N by FG score) per tier
    """
    tier_list = normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS)

    payload = compute_team_buff_tier_leaderboards(
        entries=entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        limit=limit,
        tiers=tier_list,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
    )

    base_team_color, target_team_color = _resolve_team_colors_for_tiering(
        cfg_dict,
        calc_song,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
    )
    base_team_buff = _resolve_base_team_buff(cfg_dict)
    base_effect = _team_buff_effect(base_team_buff, base_team_color)
    try:
        meta0 = calc_song.get("metadata", {}) or {}
        base_hitsim_enabled = (
            bool(meta0.get("HumanHitSimApplied"))
            and str(meta0.get("HumanHitSimApplyTo", "") or "").strip().upper() == "ALL"
        )
    except Exception:
        base_hitsim_enabled = False
    # Default: do not compute/persist derived per-window HitSim deltas here; they are large.
    persist_hitsim_deltas = str(os.environ.get("DB_PERSIST_HITSIM_DELTAS", "0") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    base_hitsim_enabled = bool(base_hitsim_enabled and persist_hitsim_deltas)
    base_deltas_cache: dict[tuple[int, int], tuple[int, ...]] = {}
    fg_deltas_cache: dict[tuple[int, int, tuple[int, ...]], tuple[int, ...]] = {}

    # Match replay rows back to persisted entries using order-invariant gear/mini names.
    def _stable_key_from_payload(e: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return (
            tuple(sorted(_flat_item_names(e.get("gear")))),
            tuple(sorted(_representative_mini_names_from_any(e.get("minis")))),
        )

    orig_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], dict] = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        orig_by_key[_stable_key_from_payload(e)] = e

    batches: dict[str, list[dict]] = {}
    for tier, tier_payload in (payload.get("tiers") or {}).items():
        delta_map = _team_buff_delta_map(
            base_team_buff=base_team_buff,
            target_team_buff=str(tier),
            base_team_color=base_team_color,
            target_team_color=target_team_color,
        )
        base_top = tier_payload.get("base_top51") or []
        fg_top = tier_payload.get("fg_top51") or []

        base_score_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}
        fg_score_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}
        fg_base_score_by_key: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}

        ordered_keys: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        ordered_key_set: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()

        for r in base_top:
            if not isinstance(r, dict):
                continue
            k = _stable_key_from_payload(r)
            base_score_by_key[k] = _safe_int(r.get("score"), 0)
            fg_score_by_key[k] = _safe_int(r.get("fg_score"), 0)
            if k not in ordered_key_set:
                ordered_keys.append(k)
                ordered_key_set.add(k)

        for r in fg_top:
            if not isinstance(r, dict):
                continue
            k = _stable_key_from_payload(r)
            fg_score_by_key[k] = _safe_int(r.get("fg_score"), 0)
            fg_base_score_by_key[k] = _safe_int(r.get("fg_base_score"), 0)
            if k not in base_score_by_key:
                base_score_by_key[k] = _safe_int(r.get("score"), 0)
            if k not in ordered_key_set:
                ordered_keys.append(k)
                ordered_key_set.add(k)

        selected_keys = set(base_score_by_key.keys()) | set(fg_score_by_key.keys())
        if len(ordered_key_set) < len(selected_keys):
            ordered_keys.extend(sorted(selected_keys - ordered_key_set))
        out_entries: list[dict] = []
        for k in ordered_keys:
            orig = orig_by_key.get(k)
            if not isinstance(orig, dict):
                continue

            score_out = int(base_score_by_key.get(k, 0) or 0)
            fg_score_out = int(fg_score_by_key.get(k, 0) or 0)
            fg_base_score_out = int(fg_base_score_by_key.get(k, 0) or 0)

            # Keep payloads internally consistent: adjust Stats + FG score fields for this tier.
            details_base = orig.get("details") or {}
            if not isinstance(details_base, dict):
                details_base = {}
            if isinstance(details_base, dict):
                stats0 = details_base.get("Stats")
                if isinstance(stats0, dict) and stats0:
                    details_base = dict(details_base)
                    details_base["Stats"] = _ensure_stats_include_base_effect(stats0, base_effect)
            details_out = _apply_details_delta(details_base, delta_map)
            if isinstance(details_out, dict) and base_hitsim_enabled:
                existing_deltas = details_out.get("hitsim_offset_deltas_ms")
                if isinstance(existing_deltas, (list, tuple)) and existing_deltas:
                    details_out.pop("hitsim_offset_delta_ms", None)
                elif details_out.get("hitsim_offset_deltas_ms") is None:
                    stats0 = details_out.get("Stats")
                    if isinstance(stats0, dict):
                        try:
                            ff0 = _stats_get_int(stats0, "Fever Fill Rate", 0)
                            ft0 = _stats_get_int(stats0, "Fever Time", 0)
                        except Exception:
                            ff0 = 0
                            ft0 = 0

                        cache_key = (int(ff0), int(ft0))
                        deltas_t = base_deltas_cache.get(cache_key)
                        if deltas_t is None:
                            try:
                                from ...solver.scoring.force_greats import summarize_hitsim_offset_deltas_ms_for_base

                                computed = summarize_hitsim_offset_deltas_ms_for_base(
                                    calc_song, {"Stats": stats0}, ref_arrays
                                )
                            except Exception:
                                computed = None
                            if computed:
                                try:
                                    deltas_t = tuple(int(x) for x in computed)
                                except Exception:
                                    deltas_t = None
                                if deltas_t:
                                    base_deltas_cache[cache_key] = deltas_t

                        if deltas_t:
                            if details_out.get("hitsim_offset_deltas_ms") is None:
                                details_out["hitsim_offset_deltas_ms"] = list(deltas_t)
                            details_out.pop("hitsim_offset_delta_ms", None)

            force_base = orig.get("force")
            # If the persisted BaseStats payload is missing the base TeamBuff effect, add it first so
            # the tier delta map can't create negative stats.
            if isinstance(force_base, dict) and base_effect:
                force_base_obj = force_base
                force_base = dict(force_base_obj)
                bs = force_base.get("BaseStats")
                if isinstance(bs, dict) and bs:
                    force_base["BaseStats"] = _ensure_stats_include_base_effect(bs, base_effect)
                det = force_base.get("details")
                if isinstance(det, dict):
                    st = det.get("Stats")
                    if isinstance(st, dict) and st:
                        det_out = dict(det)
                        det_out["Stats"] = _ensure_stats_include_base_effect(st, base_effect)
                        force_base["details"] = det_out
            force_out = _apply_force_delta(
                force_base,
                delta=delta_map,
                fg_score=fg_score_out,
            )
            if isinstance(force_out, dict) and base_hitsim_enabled and fg_score_out > score_out:
                fg_meta = force_out.get("ForceGreats")
                if isinstance(fg_meta, dict):
                    existing_deltas = fg_meta.get("hitsim_offset_deltas_ms")
                    if isinstance(existing_deltas, (list, tuple)) and existing_deltas:
                        if "hitsim_offset_delta_ms" in fg_meta:
                            fg_meta_out = dict(fg_meta)
                            fg_meta_out.pop("hitsim_offset_delta_ms", None)
                            force_out["ForceGreats"] = fg_meta_out
                    else:
                        forced_counts = _extract_force_config_counts(force_out)
                        if forced_counts:
                            fg_stats = force_out.get("Stats")
                            if not isinstance(fg_stats, dict) or not fg_stats:
                                fg_stats = _force_payload_stats(force_out, details_out.get("Stats", {}))
                            if isinstance(fg_stats, dict) and fg_stats:
                                try:
                                    ff_stat = _stats_get_int(fg_stats, "Fever Fill Rate", 0)
                                    ft_stat = _stats_get_int(fg_stats, "Fever Time", 0)
                                except Exception:
                                    ff_stat = 0
                                    ft_stat = 0
                                cfg_key = (int(ff_stat), int(ft_stat), tuple(int(x) for x in forced_counts))
                                deltas_t = fg_deltas_cache.get(cfg_key)
                                if deltas_t is None:
                                    try:
                                        from ...solver.scoring.force_greats import (
                                            summarize_hitsim_offset_deltas_ms_for_fg_variant,
                                        )

                                        fg_data = {"ForceGreats": fg_meta, "Stats": fg_stats}
                                        computed = summarize_hitsim_offset_deltas_ms_for_fg_variant(
                                            calc_song, fg_data, ref_arrays
                                        )
                                    except Exception:
                                        computed = None
                                    if computed:
                                        try:
                                            deltas_t = tuple(int(x) for x in computed)
                                        except Exception:
                                            deltas_t = None
                                        if deltas_t:
                                            fg_deltas_cache[cfg_key] = deltas_t
                                if deltas_t:
                                    fg_meta_out = dict(fg_meta)
                                    if fg_meta_out.get("hitsim_offset_deltas_ms") is None:
                                        fg_meta_out["hitsim_offset_deltas_ms"] = list(deltas_t)
                                    fg_meta_out.pop("hitsim_offset_delta_ms", None)
                                    force_out["ForceGreats"] = fg_meta_out
                                    if isinstance(details_out, dict):
                                        fg_det = details_out.get("ForceGreats")
                                        if isinstance(fg_det, dict) and fg_det.get("hitsim_offset_deltas_ms") is None:
                                            fg_det_out = dict(fg_det)
                                            if fg_det_out.get("hitsim_offset_deltas_ms") is None:
                                                fg_det_out["hitsim_offset_deltas_ms"] = list(deltas_t)
                                            fg_det_out.pop("hitsim_offset_delta_ms", None)
                                            details_out["ForceGreats"] = fg_det_out

            if isinstance(details_out, dict):
                details_out = dict(details_out)
                details_out.pop("hitsim_offset_delta_ms", None)
                fg0 = details_out.get("ForceGreats")
                if isinstance(fg0, dict) and "hitsim_offset_delta_ms" in fg0:
                    fg1 = dict(fg0)
                    fg1.pop("hitsim_offset_delta_ms", None)
                    details_out["ForceGreats"] = fg1

            if isinstance(force_out, dict):
                fg0 = force_out.get("ForceGreats")
                if isinstance(fg0, dict) and "hitsim_offset_delta_ms" in fg0:
                    fg1 = dict(fg0)
                    fg1.pop("hitsim_offset_delta_ms", None)
                    force_out = dict(force_out)
                    force_out["ForceGreats"] = fg1

            out_entries.append(
                {
                    "loadout_hash": str(orig.get("loadout_hash") or ""),
                    "score": score_out,
                    "fg_score": fg_score_out,
                    "fg_base_score": fg_base_score_out,
                    "gear": _flat_item_names(orig.get("gear")),
                    "minis": _representative_mini_names_from_any(orig.get("minis")),
                    "details": details_out,
                    "force": force_out,
                }
            )
        batches[str(tier)] = out_entries

    return batches
