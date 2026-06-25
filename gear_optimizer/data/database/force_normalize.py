"""
Force-Greats payload normalization, base-score derivation, and pairing asserts,
plus stats-reconstruction helpers used when persisting details.
"""
import logging
from typing import Any, Optional
from ...core.fallback_monitor import warn_fallback
from ...core.gem_defs import element_gem_count
from ...core.utils import safe_int as _safe_int_for_db
from ...core.team_buff import team_buff_effect

logger = logging.getLogger(__name__)


def _get_overflow_from_details(details):
    """
    Extract overflow value from details dict.
    Args:
        details: Details dictionary containing GemCounts
    Returns:
        int: Overflow value (Element), or 0 if not found
    """
    if not details:
        return 0
    gem_counts = details.get("GemCounts", {})
    if not gem_counts:
        return 0
    return element_gem_count(gem_counts)


def _ensure_stats_in_details(
    details: dict,
    gear: list,
    minis: list,
    minis_by_name: dict,
    *,
    team_buff: "Optional[str]" = None,
    team_color: "Optional[str]" = None,
) -> dict:
    """
    Ensure Stats are populated in details dict.
    Defers to the unified stats gateway first; falls back to heavy reconstruction
    from gear/mini names only when the gateway returns without Stats.
    """
    if not isinstance(details, dict):
        details = {}
    stats_obj = details.get("Stats")
    if isinstance(stats_obj, dict) and stats_obj:
        return details
    warn_fallback(
        "db.ensure_stats",
        "details missing Stats, reconstructing stats for persistence",
        context={"team_buff": team_buff or "", "team_color": team_color or ""},
        fatal=False,
    )
    try:
        from gear_optimizer.core.stats_calculator import compute_full_stats
        from gear_optimizer.data import database as _db
        gear_names = []
        for g in gear or []:
            if isinstance(g, dict):
                gear_names.append(g.get("Name", ""))
            elif isinstance(g, str):
                gear_names.append(g)
        mini_names = []
        for m in minis or []:
            if isinstance(m, dict):
                mini_names.append(m.get("Name", ""))
            elif isinstance(m, str):
                mini_names.append(m)
            elif isinstance(m, list) and m:
                first = m[0]
                if isinstance(first, dict):
                    mini_names.append(first.get("Name", ""))
                elif isinstance(first, str):
                    mini_names.append(first)
        gears_by_name = _db.get_gears_by_name_cached()
        base_stats = {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 0,
        }
        buff_tier = str(team_buff or "").strip().upper()
        buff_color = str(team_color or "").strip()
        if not buff_color:
            buff_color = str(
                details.get("PrimaryColor")
                or details.get("Primary Color")
                or details.get("SelectedElement")
                or details.get("Selected Element")
                or ""
            ).strip()
        for stat_name, delta in team_buff_effect(buff_tier, buff_color).items():
            base_stats[stat_name] = int(base_stats.get(stat_name, 0) or 0) + int(delta)
        gem_counts = dict(details.get("GemCounts", {}) or {})
        gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
        gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
        selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""
        computed = compute_full_stats(
            gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
        )
        details["Stats"] = computed
    except Exception as e:
        logger.warning(f"database:_ensure_stats_in_details: {e}")
    return details


def _force_payload_base_score(force_data: Any) -> int:
    if not isinstance(force_data, dict):
        return 0
    for key in ("BaseScore", "base_score"):
        score = _safe_int_for_db(force_data.get(key), 0)
        if score > 0:
            return score
    nested = force_data.get("details")
    if isinstance(nested, dict):
        for key in ("BaseScore", "base_score"):
            score = _safe_int_for_db(nested.get(key), 0)
            if score > 0:
                return score
    return 0


def _base_details_from_force_payload(base_details: Any, force_data: Any) -> dict:
    """
    Build the FG table details payload that explains the FG row's paired `score`.
    `force_details_json` owns the FG replay surface (`fg_score` plus ForceGreats config).
    The FG row's `details_json` owns the paired base replay surface for the same FG
    allocation, so it must be derived from the force payload's BaseStats+gems instead
    of from the loadout's separate best-base winner.
    """
    if not isinstance(force_data, dict):
        return {}
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload
    payload = force_data.get("details") if isinstance(force_data.get("details"), dict) else force_data
    if not isinstance(payload, dict):
        return {}
    selected = (
        payload.get("SelectedElement")
        or payload.get("Selected Element")
        or (base_details.get("SelectedElement") if isinstance(base_details, dict) else None)
        or (base_details.get("Selected Element") if isinstance(base_details, dict) else None)
        or ""
    )
    stats = materialize_stats_from_payload(payload, selected_element=selected)
    if not isinstance(stats, dict) or not stats:
        return {}
    out: dict[str, Any] = {}
    if isinstance(base_details, dict):
        for key in ("PrimaryColor", "Primary Color", "SecondaryColor", "Secondary Color"):
            if base_details.get(key) not in (None, ""):
                out[key] = base_details.get(key)
    out["Stats"] = dict(stats)
    out["FT"] = _safe_int_for_db(payload.get("FT", (payload.get("GemCounts") or {}).get("Fever Time", 0)), 0)
    out["FF"] = _safe_int_for_db(
        payload.get("FF", (payload.get("GemCounts") or {}).get("Fever Fill Rate", 0)),
        0,
    )
    gem_counts = payload.get("GemCounts")
    if isinstance(gem_counts, dict):
        out["GemCounts"] = dict(gem_counts)
    if selected:
        out["SelectedElement"] = str(selected)
    base_score = _force_payload_base_score(force_data)
    if base_score > 0:
        out["BaseScore"] = int(base_score)
    return out


def _compact_force_details_for_storage(force_data: Any) -> Any:
    """
    Return the raw FG payload without fields already persisted in FG details.
    `force_details_json` must keep the replay surface: BaseStats, GemCounts,
    FT/FF, selected element, ForceGreats config, and score. A materialized final
    `Stats` copy is redundant when BaseStats + gems are present, because FG
    replay reconstructs it from `force_details_json`. The FG table `details_json`
    remains the paired base-score detail surface.
    """
    if not isinstance(force_data, dict) or not force_data:
        return force_data
    out = dict(force_data)
    if (
        isinstance(out.get("Stats"), dict)
        and isinstance(out.get("BaseStats"), dict)
        and isinstance(out.get("GemCounts"), dict)
    ):
        out.pop("Stats", None)
    if "Score" in out and "score" in out:
        try:
            if int(out.get("Score") or 0) == int(out.get("score") or 0):
                out.pop("score", None)
        except Exception as e:
            logger.warning(f"database:_compact_force_details_for_storage: {e}")
    return out


def _coerce_db_int(v: Any) -> int:
    try:
        return int(v or 0)
    except Exception as e:
        logger.warning(f"database:_coerce_db_int: {e}")
        return 0


def _normalize_force_for_persistence(force_data: Any, *, fg_score: int) -> Any:
    if not isinstance(force_data, dict):
        return force_data
    out = dict(force_data)
    score_v = _coerce_db_int(fg_score)
    if score_v <= 0:
        score_v = _coerce_db_int(out.get("Score", 0))
    if score_v <= 0:
        score_v = _coerce_db_int(out.get("score", 0))
    if score_v > 0:
        out["score"] = int(score_v)
        out["Score"] = int(score_v)
    det = out.get("details")
    if isinstance(det, dict):
        fg = det.get("ForceGreats")
        if isinstance(fg, dict) and int(fg_score or 0) > 0:
            fg_out = dict(fg)
            fg_out["final_score"] = int(fg_score)
            det_out = dict(det)
            det_out["ForceGreats"] = fg_out
            out["details"] = det_out
    fg = out.get("ForceGreats")
    if isinstance(fg, dict) and int(score_v or 0) > 0:
        fg_out = dict(fg)
        fg_out["final_score"] = int(score_v)
        out["ForceGreats"] = fg_out
    return out


def _normalize_force_base_score_for_persistence(force_data: Any, *, fg_base_score: int) -> Any:
    if not isinstance(force_data, dict):
        return force_data
    base_i = _coerce_db_int(fg_base_score)
    if base_i <= 0:
        return force_data
    out = dict(force_data)
    out["BaseScore"] = int(base_i)
    det = out.get("details")
    if isinstance(det, dict):
        det_out = dict(det)
        det_out["BaseScore"] = int(base_i)
        out["details"] = det_out
    return out


def _assert_force_score_pairing(force_data: Any, *, fg_base_score: int, fg_score: int) -> None:
    if not isinstance(force_data, dict) or int(fg_score or 0) <= 0:
        return
    force_base = _force_payload_base_score(force_data)
    if int(force_base or 0) != int(fg_base_score or 0):
        raise AssertionError(
            "FG persistence payload BaseScore must match the paired FG base score "
            f"(force={force_base}, row={fg_base_score})."
        )
    force_score = _coerce_db_int(force_data.get("Score", force_data.get("score", 0)))
    if int(force_score or 0) != int(fg_score or 0):
        raise AssertionError(
            "FG persistence payload Score must match the row FG score "
            f"(force={force_score}, row={fg_score})."
        )
    fg_meta = force_data.get("ForceGreats")
    if isinstance(fg_meta, dict) and "final_score" in fg_meta:
        meta_score = _coerce_db_int(fg_meta.get("final_score"))
        if int(meta_score or 0) != int(fg_score or 0):
            raise AssertionError(
                "FG persistence ForceGreats.final_score must match the row FG score "
                f"(force={meta_score}, row={fg_score})."
            )
