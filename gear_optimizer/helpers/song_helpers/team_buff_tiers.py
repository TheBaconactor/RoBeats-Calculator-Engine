from __future__ import annotations

from heapq import nsmallest
import re
import logging

from ...core.team_buff import (
    DEFAULT_TEAM_BUFF_REPLAY_TIERS,
    normalize_team_buff_sequence,
    resolve_baseline_team_buff_from_cfg_dict,
    resolve_team_color_from_cfg_dict,
    team_buff_effect,
)
from ...core.utils import get_selected_element, safe_int as _safe_int
from ...data.loadout_equivalence import representative_mini_names
from .fg_config import has_valid_fg_config, require_response_surface
from .force_greats.result_application import materialize_stats_from_payload
from .ref_array_builder import resolve_exact_replay_ref_arrays


logger = logging.getLogger(__name__)


def _norm_text(v: object) -> str:
    return str(v or "").strip()


def _loadout_hash(entry: dict) -> str:
    return _norm_text(entry.get("loadout_hash", ""))


_MINI_LITERAL_RE = re.compile(r"""['"]([^'"]+)['"]""")


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






def _resolve_team_color(cfg_dict: dict, calc_song: dict) -> str:
    primary_color = _norm_text((calc_song.get("metadata", {}) or {}).get("Primary Color", ""))
    return resolve_team_color_from_cfg_dict(cfg_dict, primary_color=primary_color)


def _resolve_base_team_buff(cfg_dict: dict) -> str:
    if isinstance(cfg_dict, dict):
        if isinstance(cfg_dict.get("IterationEngine"), dict):
            return resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
        sec = cfg_dict.get("TeamContributionBuffConstant")
        if isinstance(sec, dict):
            raw = _norm_text(sec.get("TeamBuff", sec.get("teambuff", "")))
            if raw:
                normalized = normalize_team_buff_sequence((raw,), default=("T5",))
                if normalized:
                    return str(normalized[0])
        raw = _norm_text(cfg_dict.get("TeamBuff", cfg_dict.get("teambuff", "")))
        if raw:
            normalized = normalize_team_buff_sequence((raw,), default=("T5",))
            if normalized:
                return str(normalized[0])
    return resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")


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


def _entry_origin_priority(entry: dict) -> tuple[int, int, int]:
    force_obj = entry.get("force")
    has_force = 1 if isinstance(force_obj, dict) and has_valid_fg_config(force_obj) else 0
    return (
        has_force,
        _safe_int(entry.get("fg_score"), 0),
        _safe_int(entry.get("score"), 0),
    )


def _force_payload_stats(force_obj: dict, fallback_stats: dict) -> dict:
    if not isinstance(force_obj, dict) or not force_obj:
        return fallback_stats if isinstance(fallback_stats, dict) else {}
    stats = materialize_stats_from_payload(force_obj, mutate_payload=False)
    return stats if isinstance(stats, dict) and stats else (fallback_stats if isinstance(fallback_stats, dict) else {})


def _team_buff_delta_map(
    *,
    base_team_buff: str,
    target_team_buff: str,
    base_team_color: str,
    target_team_color: str,
) -> dict[str, int]:
    base = team_buff_effect(base_team_buff, base_team_color)
    target = team_buff_effect(target_team_buff, target_team_color)
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


def _replay_stat_slice(
    stats: dict,
    *,
    primary_color: str,
    secondary_color: str,
) -> dict[str, int]:
    return {
        "pp": _safe_int(stats.get("Perfect Points", 0), 0),
        "p_val": _safe_int(stats.get(primary_color, 0), 0) if primary_color else 0,
        "s_val": _safe_int(stats.get(secondary_color, 0), 0) if secondary_color else 0,
        "ft_stat": _safe_int(stats.get("Fever Time", 0), 0),
        "ff_stat": _safe_int(stats.get("Fever Fill Rate", 0), 0),
        "cm_stat": _safe_int(stats.get("Combo Multiplier", 0), 0),
        "fm_stat": _safe_int(stats.get("Fever Multiplier", 0), 0),
    }


def _fg_replay_snapshot(
    *,
    fg_stats: dict,
    paired_base_stats: dict,
    primary_color: str,
    secondary_color: str,
    surface: object,
    config: object,
) -> dict:
    fg = _replay_stat_slice(fg_stats, primary_color=primary_color, secondary_color=secondary_color)
    base = _replay_stat_slice(paired_base_stats, primary_color=primary_color, secondary_color=secondary_color)
    return {
        "pp": int(fg["pp"]),
        "p_val": int(fg["p_val"]),
        "s_val": int(fg["s_val"]),
        "ft_stat": int(fg["ft_stat"]),
        "ff_stat": int(fg["ff_stat"]),
        "cm_stat": int(fg["cm_stat"]),
        "fm_stat": int(fg["fm_stat"]),
        "base_pp": int(base["pp"]),
        "base_p_val": int(base["p_val"]),
        "base_s_val": int(base["s_val"]),
        "base_ft_stat": int(base["ft_stat"]),
        "base_ff_stat": int(base["ff_stat"]),
        "base_cm_stat": int(base["cm_stat"]),
        "base_fm_stat": int(base["fm_stat"]),
        "surface": surface,
        "config": config,
    }


def _fg_stats_at_tier(
    fg: dict,
    *,
    delta_pp: int,
    delta_primary: int,
    delta_secondary: int,
    primary_color: str,
    secondary_color: str,
    paired_base: bool = False,
) -> dict[str, int]:
    if paired_base:
        pp = int(fg.get("base_pp", fg.get("pp", 0)) or 0)
        p_val = int(fg.get("base_p_val", fg.get("p_val", 0)) or 0)
        s_val = int(fg.get("base_s_val", fg.get("s_val", 0)) or 0)
        ft_stat = int(fg.get("base_ft_stat", fg.get("ft_stat", 0)) or 0)
        ff_stat = int(fg.get("base_ff_stat", fg.get("ff_stat", 0)) or 0)
        cm_stat = int(fg.get("base_cm_stat", fg.get("cm_stat", 0)) or 0)
        fm_stat = int(fg.get("base_fm_stat", fg.get("fm_stat", 0)) or 0)
    else:
        pp = int(fg.get("pp", 0) or 0)
        p_val = int(fg.get("p_val", 0) or 0)
        s_val = int(fg.get("s_val", 0) or 0)
        ft_stat = int(fg.get("ft_stat", 0) or 0)
        ff_stat = int(fg.get("ff_stat", 0) or 0)
        cm_stat = int(fg.get("cm_stat", 0) or 0)
        fm_stat = int(fg.get("fm_stat", 0) or 0)
    stats = {
        "Perfect Points": pp + int(delta_pp),
        "Combo Multiplier": cm_stat,
        "Fever Multiplier": fm_stat,
        "Fever Time": ft_stat,
        "Fever Fill Rate": ff_stat,
    }
    if primary_color:
        stats[primary_color] = p_val + int(delta_primary)
    if secondary_color:
        stats[secondary_color] = s_val + int(delta_secondary)
    return stats


def _fg_identity_details(force_out: object, calc_song: dict) -> dict[str, str]:
    """Chart/loadout identity fields required by FG serialization (not meta scoring)."""
    meta0 = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}
    chart_primary = _norm_text(meta0.get("Primary Color", ""))
    chart_secondary = _norm_text(meta0.get("Secondary Color", ""))
    selected = _norm_text(get_selected_element(force_out, "") if isinstance(force_out, dict) else "")
    primary = chart_primary or selected
    secondary = chart_secondary or primary or "General"
    return {
        "SelectedElement": selected or primary,
        "PrimaryColor": primary,
        "SecondaryColor": secondary,
    }


def _apply_force_delta(force_obj: object, *, delta: dict[str, int], fg_score: int) -> object:
    """Update a flat persisted FG payload (force_details_json) with the replayed score/tier delta."""
    if not isinstance(force_obj, dict) or not force_obj:
        return force_obj

    out = dict(force_obj)
    out["Score"] = int(fg_score)
    base_stats = out.get("BaseStats")
    if delta and isinstance(base_stats, dict) and base_stats:
        out["BaseStats"] = _apply_stat_delta(base_stats, delta)
    fg = out.get("ForceGreats")
    if isinstance(fg, dict):
        fg_out = dict(fg)
        fg_out["final_score"] = int(fg_score)
        out["ForceGreats"] = fg_out
    return out



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
    replay_surfaces: tuple[str, ...] = ("meta", "fg"),
) -> dict:
    """
    Re-score persisted entries under TeamBuff tiers and return per-tier leaderboards.

    Base and FG scoring use CPU exact replay for retained rows. GPU scoring remains
    the search path; replay/canonicalization is the final user-visible score authority.

    This is designed for post-processing:
    - Uses the existing gem allocations (Stats in details) as-is.
    - Scores the persisted FG response surface exactly (the canonical FG
      representation; tier deltas never shift FT/FF, so the fever timeline is
      tier-invariant and only stat values re-derive).
    - Produces top-N lists by base score and FG score per tier.
    """
    n = max(0, int(limit))
    if not entries or n <= 0:
        return {"tiers": {}, "meta": {"candidate_count": 0}}
    replay_meta = "meta" in {str(s).strip().lower() for s in (replay_surfaces or ("meta", "fg"))}
    replay_fg = "fg" in {str(s).strip().lower() for s in (replay_surfaces or ("meta", "fg"))}
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)

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

    base_effect = team_buff_effect(base_team_buff, base_team_color)
    tier_list = normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS)

    try:
        from ...solver.timing_envelope import apply_timing_envelope

        apply_timing_envelope(calc_song)
    except Exception as e:
        logger.debug(f"team_buff_tiers:compute_team_buff_tier_leaderboards: {e}")

    per_entry: list[dict] = []

    for entry in entries:
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

        base_slice = _replay_stat_slice(
            stats_base,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )

        force_obj = entry.get("force")
        fg_snapshot = None
        if isinstance(force_obj, dict) and has_valid_fg_config(force_obj):
            fg_stats0 = _force_payload_stats(force_obj, stats_base)
            fg_stats = (
                _ensure_stats_include_base_effect(fg_stats0, base_effect) if isinstance(fg_stats0, dict) else {}
            )
            if not isinstance(fg_stats, dict) or not fg_stats:
                fg_stats = stats_base

            force_base_raw = force_obj.get("BaseStats")
            if isinstance(force_base_raw, dict) and force_base_raw:
                force_base_stats = _ensure_stats_include_base_effect(force_base_raw, base_effect)
            else:
                force_base_stats = fg_stats

            fg_snapshot = _fg_replay_snapshot(
                fg_stats=fg_stats,
                paired_base_stats=force_base_stats,
                primary_color=primary_color,
                secondary_color=secondary_color,
                surface=require_response_surface(force_obj),
                config=(force_obj.get("ForceGreats", {}) or {}).get("config"),
            )

        per_entry.append(
            {
                "loadout_hash": _norm_text(entry.get("loadout_hash", "")),
                "gear": gear,
                "minis": minis,
                "source_score": _safe_int(entry.get("score"), 0),
                "source_fg_base_score": _safe_int(entry.get("fg_base_score"), _safe_int(entry.get("score"), 0)),
                "source_fg_score": _safe_int(entry.get("fg_score"), 0),
                "base": base_slice,
                "fg": fg_snapshot,
            }
        )

    from ...solver.scoring.exact_rescore import (
        score_force_greats_response_surface_exact,
        score_stats_exact_batch,
    )

    tier_deltas: dict[str, tuple[int, int, int]] = {}
    for tier in tier_list:
        delta_map = _team_buff_delta_map(
            base_team_buff=base_team_buff,
            target_team_buff=str(tier),
            base_team_color=base_team_color,
            target_team_color=target_team_color,
        )
        tier_deltas[str(tier)] = (
            int(delta_map.get("Perfect Points", 0)),
            int(delta_map.get(primary_color, 0)) if primary_color else 0,
            int(delta_map.get(secondary_color, 0)) if secondary_color else 0,
        )

    meta_scores_by_tier: dict[str, list[int]] = {}
    if replay_meta and per_entry:
        for tier in tier_list:
            dpp, dp, ds = tier_deltas[str(tier)]
            tier_stats = [
                _fg_stats_at_tier(
                    e.get("base") or {},
                    delta_pp=int(dpp),
                    delta_primary=int(dp),
                    delta_secondary=int(ds),
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                )
                for e in per_entry
            ]
            meta_scores_by_tier[str(tier)] = [
                int(s) for s in score_stats_exact_batch(tier_stats, calc_song, ref_arrays)
            ]
    else:
        meta_scores_by_tier = {str(t): [0] * len(per_entry) for t in tier_list}

    fg_scores_by_tier: dict[str, list[int]] = {str(t): [0] * len(per_entry) for t in tier_list}
    have_fg = replay_fg and any(isinstance(e.get("fg"), dict) for e in per_entry)
    if have_fg:
        for tier in tier_list:
            dpp, dp, ds = tier_deltas[str(tier)]
            out_list = fg_scores_by_tier[str(tier)]
            for idx, e in enumerate(per_entry):
                fg = e.get("fg")
                if not isinstance(fg, dict):
                    continue
                stats = _fg_stats_at_tier(
                    fg,
                    delta_pp=int(dpp),
                    delta_primary=int(dp),
                    delta_secondary=int(ds),
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                )
                replay_score = score_force_greats_response_surface_exact(
                    stats, calc_song, ref_arrays, fg["surface"]
                )
                if replay_score is None:
                    raise ValueError(
                        "FG response surface tier replay failed for loadout "
                        f"{e.get('loadout_hash')!r} at tier {tier!r}."
                    )
                out_list[idx] = int(replay_score)

    tiers_out: dict[str, dict] = {}
    for tier in tier_list:
        delta_pp, delta_primary, delta_secondary = tier_deltas[str(tier)]
        base_scores = meta_scores_by_tier.get(str(tier), [])
        fg_scores_for_tier = fg_scores_by_tier.get(str(tier)) if have_fg else None

        base_ranked: list[dict] = []
        fg_ranked: list[dict] = []

        for i, e in enumerate(per_entry):
            base_score = int(base_scores[i]) if replay_meta and i < len(base_scores) else 0
            fg_score = 0
            if fg_scores_for_tier is not None and i < len(fg_scores_for_tier):
                fg_score = int(fg_scores_for_tier[i] or 0)
            fg = e.get("fg")

            if replay_meta:
                base_ranked.append(
                    {
                        "loadout_hash": e.get("loadout_hash") or "",
                        "gear": e.get("gear") or [],
                        "minis": e.get("minis") or [],
                        "score": int(base_score),
                        "source_score": int(e.get("source_score") or 0),
                    }
                )

            if replay_fg and isinstance(fg, dict) and int(fg_score) > 0:
                fg_ranked.append(
                    {
                        "loadout_hash": e.get("loadout_hash") or "",
                        "gear": e.get("gear") or [],
                        "minis": e.get("minis") or [],
                        "fg_score": int(fg_score),
                        "source_score": int(e.get("source_score") or 0),
                        "source_fg_base_score": int(e.get("source_fg_base_score") or 0),
                        "source_fg_score": int(e.get("source_fg_score") or 0),
                        "force_config": fg.get("config"),
                        "_replay_fg": fg,
                    }
                )

        base_top = nsmallest(
            int(n),
            base_ranked,
            key=lambda r: (-int(r.get("score", 0) or 0), str(r.get("loadout_hash") or "")),
        )
        fg_top_raw = nsmallest(
            int(n),
            fg_ranked,
            key=lambda r: (-int(r.get("fg_score", 0) or 0), str(r.get("loadout_hash") or "")),
        )
        paired_stats: list[dict[str, int]] = []
        paired_rows: list[dict] = []
        fg_top: list[dict] = []
        for row in fg_top_raw:
            fg_snap = row.pop("_replay_fg", None)
            if isinstance(fg_snap, dict):
                paired_rows.append(row)
                paired_stats.append(
                    _fg_stats_at_tier(
                        fg_snap,
                        delta_pp=int(delta_pp),
                        delta_primary=int(delta_primary),
                        delta_secondary=int(delta_secondary),
                        primary_color=primary_color,
                        secondary_color=secondary_color,
                        paired_base=True,
                    )
                )
            else:
                row["fg_base_score"] = 0
            fg_top.append(row)
        if paired_stats:
            fg_base_scores = score_stats_exact_batch(paired_stats, calc_song, ref_arrays)
            for row, score in zip(paired_rows, fg_base_scores):
                row["fg_base_score"] = int(score)
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
    replay_surface: str = "both",
) -> dict[str, list[dict]]:
    """
    Return DB-ready entry batches per tier.

    Output format:
        { "T5": [ {score, fg_score, gear, minis, details, force}, ... ], ... }

    Selection:
    - meta: top-N by replayed base score only
    - fg: top-N by replayed FG score only
    - both: union(top-N base, top-N FG) for persistence canonicalization
    """
    tier_list = normalize_team_buff_sequence(tiers, default=DEFAULT_TEAM_BUFF_REPLAY_TIERS)
    surface = str(replay_surface or "both").strip().lower()
    if surface not in {"meta", "fg", "both"}:
        surface = "both"
    replay_surfaces = ("meta", "fg") if surface == "both" else (surface,)

    from ...solver.scoring.exact_rescore import score_stats_exact_with_timeline_trace

    payload = compute_team_buff_tier_leaderboards(
        entries=entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
        limit=limit,
        tiers=tier_list,
        base_team_color_override=base_team_color_override,
        target_team_color_override=target_team_color_override,
        replay_surfaces=replay_surfaces,
    )

    payload_meta = payload.get("meta") or {}
    base_team_buff = _norm_text(payload_meta.get("base_team_buff")) or _resolve_base_team_buff(cfg_dict)
    base_team_color = _norm_text(payload_meta.get("base_team_color"))
    target_team_color = _norm_text(payload_meta.get("target_team_color"))
    if not base_team_color or not target_team_color:
        base_team_color, target_team_color = _resolve_team_colors_for_tiering(
            cfg_dict,
            calc_song,
            base_team_color_override=base_team_color_override,
            target_team_color_override=target_team_color_override,
        )
    base_effect = team_buff_effect(base_team_buff, base_team_color)

    orig_by_hash: dict[str, dict] = {}
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        h = _loadout_hash(e)
        if not h:
            continue
        current = orig_by_hash.get(h)
        if not isinstance(current, dict) or _entry_origin_priority(e) > _entry_origin_priority(current):
            orig_by_hash[h] = e

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

        if surface == "meta":
            selected_rows = [r for r in base_top if isinstance(r, dict)]
        elif surface == "fg":
            selected_rows = [r for r in fg_top if isinstance(r, dict)]
        else:
            base_score_by_hash: dict[str, int] = {}
            fg_score_by_hash: dict[str, int] = {}
            fg_base_score_by_hash: dict[str, int] = {}
            source_score_by_hash: dict[str, int] = {}
            source_fg_base_score_by_hash: dict[str, int] = {}
            source_fg_score_by_hash: dict[str, int] = {}
            ordered_hashes: list[str] = []
            ordered_hash_set: set[str] = set()

            for r in base_top:
                if not isinstance(r, dict):
                    continue
                h = _loadout_hash(r)
                if not h:
                    continue
                base_score_by_hash[h] = _safe_int(r.get("score"), 0)
                fg_score_by_hash[h] = _safe_int(r.get("fg_score"), 0)
                if "source_score" in r:
                    source_score_by_hash[h] = _safe_int(r.get("source_score"), 0)
                if "source_fg_base_score" in r:
                    source_fg_base_score_by_hash[h] = _safe_int(r.get("source_fg_base_score"), 0)
                if "source_fg_score" in r:
                    source_fg_score_by_hash[h] = _safe_int(r.get("source_fg_score"), 0)
                if h not in ordered_hash_set:
                    ordered_hashes.append(h)
                    ordered_hash_set.add(h)

            for r in fg_top:
                if not isinstance(r, dict):
                    continue
                h = _loadout_hash(r)
                if not h:
                    continue
                fg_score_by_hash[h] = _safe_int(r.get("fg_score"), 0)
                fg_base_score_by_hash[h] = _safe_int(r.get("fg_base_score"), 0)
                if h not in base_score_by_hash:
                    base_score_by_hash[h] = _safe_int(r.get("score"), 0)
                if "source_score" in r:
                    source_score_by_hash[h] = _safe_int(r.get("source_score"), 0)
                if "source_fg_base_score" in r:
                    source_fg_base_score_by_hash[h] = _safe_int(r.get("source_fg_base_score"), 0)
                if "source_fg_score" in r:
                    source_fg_score_by_hash[h] = _safe_int(r.get("source_fg_score"), 0)
                if h not in ordered_hash_set:
                    ordered_hashes.append(h)
                    ordered_hash_set.add(h)

            selected_hashes = set(base_score_by_hash.keys()) | set(fg_score_by_hash.keys())
            if len(ordered_hash_set) < len(selected_hashes):
                ordered_hashes.extend(sorted(selected_hashes - ordered_hash_set))
            selected_rows = []
            for h in ordered_hashes:
                orig = orig_by_hash.get(h)
                if not isinstance(orig, dict):
                    continue
                selected_rows.append(
                    {
                        "_hash": h,
                        "_orig": orig,
                        "score": int(base_score_by_hash.get(h, 0) or 0),
                        "fg_score": int(fg_score_by_hash.get(h, 0) or 0),
                        "fg_base_score": int(fg_base_score_by_hash.get(h, 0) or 0),
                        "source_score": int(source_score_by_hash.get(h, orig.get("source_score", 0)) or 0),
                        "source_fg_base_score": int(
                            source_fg_base_score_by_hash.get(h, orig.get("source_fg_base_score", 0)) or 0
                        ),
                        "source_fg_score": int(source_fg_score_by_hash.get(h, orig.get("source_fg_score", 0)) or 0),
                    }
                )

        out_entries: list[dict] = []
        for r in selected_rows:
            if surface == "both":
                orig = r.get("_orig")
                if not isinstance(orig, dict):
                    continue
                score_out = int(r.get("score") or 0)
                fg_score_out = int(r.get("fg_score") or 0)
                fg_base_score_out = int(r.get("fg_base_score") or 0)
            else:
                h = _loadout_hash(r)
                orig = orig_by_hash.get(h)
                if not isinstance(orig, dict):
                    continue
                score_out = _safe_int(r.get("score"), 0)
                fg_score_out = _safe_int(r.get("fg_score"), 0)
                fg_base_score_out = _safe_int(r.get("fg_base_score"), 0)

            details_out: dict = {}
            force_out: object = None
            if surface in {"meta", "both"}:
                details_base = orig.get("details") or {}
                if not isinstance(details_base, dict):
                    details_base = {}
                if isinstance(details_base, dict):
                    stats0 = details_base.get("Stats")
                    if isinstance(stats0, dict) and stats0:
                        details_base = dict(details_base)
                        details_base["Stats"] = _ensure_stats_include_base_effect(stats0, base_effect)
                details_out = _apply_details_delta(details_base, delta_map)
                # `_apply_details_delta` copies the baseline (T5) details verbatim except for
                # Stats, so `details_out` inherits the baseline TimelineFrontier — a per-note
                # trace that is WRONG for this (shifted) tier. Drop it unconditionally: the
                # per-tier graph must come from the fresh exact recompute below, never from the
                # stale baseline witness. Fail safe — any TimelineFrontier a consumer sees is
                # guaranteed to be for THIS tier; if the recompute cannot produce one, the row
                # carries none and the consumer omits the graph rather than drawing another
                # tier's timing (issue #38, base surface).
                if isinstance(details_out, dict):
                    details_out.pop("TimelineFrontier", None)
                # Recompute the per-note timeline trace for the tier-shifted stats so the
                # base note graph reflects this tier rather than the frozen baseline
                # witnesses (issue #38, point 4 — base surface). Additive only: the row's
                # `score` already comes from the leaderboard; this attaches a TimelineFrontier
                # whose frontier_trace the consumer uses to draw an exact per-tier graph.
                trace_stats = details_out.get("Stats") if isinstance(details_out, dict) else None
                if isinstance(trace_stats, dict) and trace_stats:
                    timeline_frontier = score_stats_exact_with_timeline_trace(
                        trace_stats, calc_song, ref_arrays
                    ).get("TimelineFrontier")
                    if isinstance(timeline_frontier, dict) and timeline_frontier.get("frontier_trace"):
                        details_out["TimelineFrontier"] = timeline_frontier

            if surface in {"fg", "both"}:
                force_base = orig.get("force")
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
                # NB: unlike the base TimelineFrontier above, the FG note-graph trace
                # (ForceGreats.frontier_trace) is NOT recomputed per tier — it is tier-invariant.
                # The base witness is the argmax surface in the (FT,FF) cell, which CAN change per
                # tier as base_value shifts; the FG witness is reconstructed from the FROZEN
                # response_surface plus song timing and FT/FF fever geometry, none of which a tier
                # delta touches (it shifts only Perfect Points + element colors, never FT/FF). The
                # trace is also purely structural (activation indices / judgments / timing offsets,
                # no score values — the renderer applies per-tier stats), so the persisted baseline
                # trace is already the exact per-tier witness. See test_fg_note_graph_trace_is_tier_invariant
                # and docs TIER_REPLAY_BASE_FRONTIER_TRACE.md (FG section).

            out_row: dict = {
                "loadout_hash": str(orig.get("loadout_hash") or ""),
                "gear": _flat_item_names(orig.get("gear")),
                "minis": _representative_mini_names_from_any(orig.get("minis")),
            }
            if surface in {"meta", "both"}:
                out_row["score"] = score_out
                out_row["details"] = details_out
            if surface in {"fg", "both"}:
                out_row["fg_score"] = fg_score_out
                out_row["fg_base_score"] = fg_base_score_out
                out_row["force"] = force_out
                if surface == "fg":
                    out_row["details"] = _fg_identity_details(force_out, calc_song)
            if surface == "both":
                for src_key in ("source_score", "source_fg_base_score", "source_fg_score"):
                    out_row[src_key] = int(r.get(src_key, 0) or 0)
            else:
                for src_key in ("source_score", "source_fg_base_score", "source_fg_score"):
                    if src_key in r:
                        out_row[src_key] = _safe_int(r.get(src_key), 0)

            out_entries.append(out_row)
        batches[str(tier)] = out_entries

    return batches
