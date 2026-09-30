"""
Force-Greats payload normalization, base-score derivation, and pairing asserts,
plus stats-reconstruction helpers used when persisting details.
"""
from collections.abc import Mapping
from typing import Any, Optional
from ...core.gem_defs import element_gem_count
from ...core.utils import safe_int as _safe_int_for_db
from ...core.team_buff import team_buff_effect
from ...gamedata import ELEMENTS, Gear, Mini, SongMini, load_gears
from ...helpers.song_helpers.item_utils import item_name
from ...settings import paths
from ...stats import gems, named_loadout_stats


_CORE_SCORE_STAT_KEYS = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
)


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


def _details_gem_allocation(details: dict, selected_element: str) -> dict[str, int]:
    """The gem allocation stored in row details (GemCounts plus FT/FF).

    Element gems need a selected element; a legacy row without a valid one keeps them unapplied, as
    the old stats rebuild did.
    """
    gem_counts = details.get("GemCounts")
    if not isinstance(gem_counts, dict):
        gem_counts = {}
    return gems(
        pp=gem_counts.get("Perfect Points", 0) or 0,
        cm=gem_counts.get("Combo Multiplier", 0) or 0,
        fm=gem_counts.get("Fever Multiplier", 0) or 0,
        ft=int(details.get("FT", 0) or 0),
        ff=int(details.get("FF", 0) or 0),
        element=element_gem_count(gem_counts) if selected_element in ELEMENTS else 0,
    )


def _ensure_stats_in_details(
    details: dict,
    gear: list,
    minis: list,
    minis_by_name: Mapping[str, Mini | SongMini],
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
    gear_names = [item_name(g) for g in gear or [] if isinstance(g, (Gear, str))]
    mini_names = []
    for m in minis or []:
        first = m[0] if isinstance(m, list) and m else m
        if isinstance(first, (Mini, SongMini, str)):
            mini_names.append(item_name(first))
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
    selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""
    details["Stats"] = named_loadout_stats(
        team_buff_effect(buff_tier, buff_color),
        gear_names,
        mini_names,
        load_gears(paths().gears_csv),
        minis_by_name,
        _details_gem_allocation(details, selected_element),
        selected_element,
    )
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
    `force_details_json` owns the FG replay surface (`fg_score` plus response surface).
    The FG row's `details_json` owns the paired base replay surface for the same FG
    allocation, so it must be derived from the force payload's BaseStats+gems instead
    of from the loadout's separate best-base winner.
    """
    if not isinstance(force_data, dict):
        return {}
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats
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
    stats = read_visible_stats(payload)
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
    FT/FF, selected element, response surface, and score.

    Storage contract: on disk, `BaseStats` IS the post-gem visible stats row — the
    solved gem allocation is already baked into it. The reader
    (`read_visible_stats`) returns it verbatim and NEVER re-applies gems.
    Some producers (the GA/response-frontier reducer) emit a PRE-gem `BaseStats`
    alongside the authoritative post-gem `Stats`; before dropping the redundant
    `Stats`, we PROMOTE it to `BaseStats` so the stored `BaseStats` is unambiguously
    the post-gem row. Re-applying gems on read would double-count (the 2026-07-11
    Canon-in-D regression); returning a pre-gem `BaseStats` verbatim would halve it —
    promotion removes the ambiguity at the write boundary. The FG table `details_json`
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
        # Promote the authoritative post-gem visible row to BaseStats, then drop the
        # now-redundant Stats copy. Guarantees stored BaseStats == the post-gem row.
        out["BaseStats"] = dict(out["Stats"])
        out.pop("Stats", None)
    if "Score" in out and "score" in out:
        if int(out.get("Score") or 0) == int(out.get("score") or 0):
            out.pop("score", None)
    return out


def _align_force_stats_with_persisted_loadout(force_data: Any, details: Any) -> Any:
    """Make the FG replay payload describe the same canonical mini representatives as the row.

    Mini equivalence may replace a solved mini with a deterministic display representative.
    Equivalent variants can differ only in off-song elemental stats, so the score remains exact,
    but persisting the solved variant's full stat row beside the representative names makes the
    displayed loadout internally inconsistent.  Relevant score dimensions must remain identical;
    only then may the canonical representative's complete stat row replace the FG payload row.
    """
    if not isinstance(force_data, dict):
        return force_data
    if not isinstance(details, dict):
        raise ValueError("FG persistence requires canonical loadout details")

    canonical = details.get("Stats")
    if not isinstance(canonical, dict) or not canonical:
        raise ValueError("FG persistence requires canonical loadout Stats")

    from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats

    solved = read_visible_stats(force_data)
    if not solved:
        raise ValueError("FG persistence requires replayable force Stats")

    relevant = list(_CORE_SCORE_STAT_KEYS)
    for key in (
        details.get("PrimaryColor") or details.get("Primary Color"),
        details.get("SecondaryColor") or details.get("Secondary Color"),
        details.get("SelectedElement") or details.get("Selected Element"),
    ):
        name = str(key or "").strip()
        if name and name not in relevant:
            relevant.append(name)

    changed_relevant = [
        key
        for key in relevant
        if int(solved.get(key, 0) or 0) != int(canonical.get(key, 0) or 0)
    ]
    if changed_relevant:
        changes = ", ".join(
            f"{key}={int(solved.get(key, 0) or 0)}->{int(canonical.get(key, 0) or 0)}"
            for key in changed_relevant
        )
        raise ValueError(
            "Canonical mini representatives changed FG scoring Stats: " + changes
        )

    out = dict(force_data)
    out["Stats"] = {str(key): int(value or 0) for key, value in canonical.items()}
    if isinstance(out.get("BaseStats"), dict):
        out["BaseStats"] = dict(out["Stats"])
    return out


def _coerce_db_int(v: Any) -> int:
    return int(v or 0)


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
