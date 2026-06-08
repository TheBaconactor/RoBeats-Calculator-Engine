from __future__ import annotations

from collections.abc import Callable
import logging

from ...core.utils import get_selected_element, safe_int
from .fg_config import has_valid_fg_config
from .force_greats.result_application import materialize_stats_from_payload
from .item_utils import names_list
from .persistence_records import evaluate_record_update



logger = logging.getLogger(__name__)
def normalize_force_payload(force_obj: object) -> dict:
    """
    Normalize persisted FG payload shape.

    Ensures selected element aliases are present and reconstructs `Stats` from
    `BaseStats` + gem counts when needed.
    """
    if not isinstance(force_obj, dict) or not force_obj:
        return {}

    out = dict(force_obj)

    selected_element = get_selected_element(out, "")
    if selected_element:
        out["SelectedElement"] = selected_element
        out["Selected Element"] = selected_element

    stats_obj = out.get("Stats")
    if isinstance(stats_obj, dict) and stats_obj:
        return out

    base_stats = out.get("BaseStats")
    if not isinstance(base_stats, dict) or not base_stats:
        return out

    computed_stats = materialize_stats_from_payload(out, selected_element=selected_element, mutate_payload=False)
    if isinstance(computed_stats, dict) and computed_stats:
        out["Stats"] = computed_stats
        return out

    out["Stats"] = dict(base_stats)
    return out


def make_build_details_fn(
    primary_color: str, secondary_color: str, effective_difficulty: str
) -> Callable[[dict], dict]:
    """
    Build a `build_details(data_dict) -> dict` function for persistence/loadout helpers.

    This is duplicated across multiple pipeline/orchestrator entrypoints; centralizing it
    keeps the persisted schema consistent.
    """

    def build_details(data_dict: dict) -> dict:
        if not isinstance(data_dict, dict) or not data_dict:
            return {}
        selected_element = get_selected_element(data_dict, "")
        stats_obj = data_dict.get("Stats")
        if not (isinstance(stats_obj, dict) and stats_obj):
            stats_obj = materialize_stats_from_payload(
                data_dict,
                selected_element=selected_element,
                mutate_payload=False,
            )
        if not isinstance(stats_obj, dict):
            stats_obj = {}
        return {
            "FT": data_dict.get("FT", 0),
            "FF": data_dict.get("FF", 0),
            "GemCounts": data_dict.get("GemCounts", {}),
            "Stats": stats_obj,
            "SelectedElement": selected_element,
            "PrimaryColor": primary_color,
            "SecondaryColor": secondary_color,
            "Difficulty": effective_difficulty,
            "TimelineFrontier": data_dict.get("TimelineFrontier", {}),
            "ForceGreats": data_dict.get("ForceGreats", {}),
        }

    return build_details


def build_db_payload(
    best_data,
    best_gear,
    best_minis,
    prev_record,
    attempt_lifetime,
    attempts_first,
    fg_variants,
    build_details_fn,
    db_best_fg_score=None,
):
    """
    Build database persistence payload.

    Args:
        best_data: Best optimization data
        best_gear: Best gear loadout
        best_minis: Best mini loadout
        prev_record: Previous database record
        attempt_lifetime: Lifetime attempt counter
        attempts_first: Current attempts_first counter (already computed per-song)
        fg_variants: Force greats variants
        build_details_fn: Function to build details dict from data dict
        db_best_fg_score: Best FG score from DB (across all loadouts)

    Returns:
        dict: Database payload
    """
    # Prefer BaseScore when present; otherwise fall back to Score.
    score = best_data.get("BaseScore") or best_data.get("Score", 0)

    def extract_names(record):
        """Extract names from record, handling both dict and string formats."""

        gear_items = record.get("gear") if record else []
        minis_items = record.get("minis") if record else []
        loadout = record.get("loadout") if record else None
        if (not gear_items and not minis_items) and loadout:
            gear_items = loadout[:6]
            minis_items = loadout[6:9]

        return names_list(gear_items), names_list(minis_items)

    best_gear_names = names_list(best_gear)
    best_mini_names = names_list(best_minis)
    best_details = build_details_fn(best_data)

    def attach_attempt_meta(details):
        """Copy details dict and tag attempt counters for DB persistence."""
        merged = dict(details or {})
        merged["attempt_lifetime"] = attempt_lifetime
        merged["attempts_first"] = attempts_first
        return merged

    # Build FG candidates from current run.
    # Always track best FG from this run independently.
    current_run_fg_candidates = []

    for fg_entry in fg_variants:
        if not has_valid_fg_config(fg_entry):
            continue

        fg_gear = fg_entry.get("gear", [])
        fg_minis = fg_entry.get("minis", [])
        fg_data = fg_entry.get("data", {})
        fg_gear_names = names_list(fg_gear)
        fg_mini_names = names_list(fg_minis)
        # Preserve the *base* score context for this FG entry so we can persist
        # the loadout with correct base+fg pairing (score != fg_score).
        base_score = fg_entry.get("base_score")
        if base_score is None:
            base_score = fg_entry.get("score", 0)
        try:
            base_score_i = int(base_score or 0)
        except Exception as e:
            logger.warning(f"persistence_payload:attach_attempt_meta: {e}")
            base_score_i = 0
        try:
            fg_score_i = int(fg_entry.get("fg_score", 0) or 0)
        except Exception as e:
            logger.warning(f"persistence_payload:attach_attempt_meta: {e}")
            fg_score_i = 0

        # ForceGreats is only a "useful" variant when it actually improves the score
        # for the same loadout. Persisting worse-than-base configs is confusing to users
        # (it looks like FG "regressed" compared to Base) and creates noisy FG records.
        if fg_score_i <= base_score_i:
            continue
        force_payload = normalize_force_payload(fg_data)
        if not isinstance(force_payload, dict) or not force_payload or not has_valid_fg_config(force_payload):
            continue
        current_run_fg_candidates.append(
            {
                # "score" is intentionally the FG score in this list (historical naming).
                "score": fg_score_i,
                "base_score": base_score_i,
                "fg_base_score": base_score_i,
                "gear": fg_gear_names,
                "minis": fg_mini_names,
                "details": build_details_fn(force_payload),
                # Flat raw payload to persist in `force_details_json`.
                "force": force_payload,
            }
        )

    # Centralized record comparison to keep all callers aligned.
    record_info = evaluate_record_update(best_data, prev_record, fg_variants, db_best_fg_score=db_best_fg_score)
    score = safe_int(record_info.get("score", score), 0)
    prev_score = record_info.get("prev_score")
    is_first = bool(record_info.get("is_first"))
    is_better = bool(record_info.get("is_better"))
    is_fg_better = bool(record_info.get("is_fg_better"))
    best_fg_score_run = safe_int(record_info.get("best_fg_score_run", 0), 0)
    prev_fg_score = safe_int(record_info.get("prev_fg_score", 0), 0)
    is_overall_better = bool(record_info.get("is_overall_better"))
    best_overall_score_run = safe_int(record_info.get("best_overall_score_run", 0), 0)
    prev_overall_score = safe_int(record_info.get("prev_overall_score", 0), 0)

    if is_first and is_overall_better:
        print(" >> NEW RECORD! (First entry for this song/context). Saving to Evolution Database...")
    elif is_overall_better and is_better:
        msg = f" >> NEW RECORD! Previous: {prev_score} | New: {score}"
        if is_fg_better and best_fg_score_run > 0:
            msg += f" (FG: {prev_fg_score} -> {best_fg_score_run})"
        msg += " - Updating Evolution Database..."
        print(msg)
    elif is_overall_better and is_fg_better and best_fg_score_run > 0:
        msg = (
            " >> NEW RECORD (ForceGreats)! "
            f"Previous Overall: {prev_overall_score} | New Overall: {best_overall_score_run} "
            f"(FG: {prev_fg_score} -> {best_fg_score_run}) - Updating Evolution Database..."
        )
        print(msg)
    else:
        msg = f" >> No overall improvement over DB Record (Overall: {prev_overall_score}, Base: {prev_score}, FG: {prev_fg_score})"
        if is_first:  # Edge case coverage
            msg = " >> Record exists but no improvement found."
        print(msg)

    # Aggregate candidates (best + second from previous DB and current run) and pick top two.
    candidates = []

    if prev_record and prev_score is not None:
        prev_gear_names, prev_mini_names = extract_names(prev_record)
        candidates.append(
            {
                "score": prev_score,
                "gear": prev_gear_names,
                "minis": prev_mini_names,
                "details": attach_attempt_meta(prev_record.get("details", {})),
            }
        )

    candidates.append(
        {
            "score": score,
            "gear": best_gear_names,
            "minis": best_mini_names,
            "details": attach_attempt_meta(best_details),
        }
    )

    candidates = sorted(candidates, key=lambda c: c.get("score", -1), reverse=True)

    top1 = candidates[0] if candidates else None

    updated_payload = {}
    updated_payload["attempt_lifetime"] = attempt_lifetime
    updated_payload["attempts_first"] = attempts_first
    # Expose the current run's metrics for downstream per-song counter updates.
    updated_payload["run_score"] = score or 0
    updated_payload["_record"] = record_info
    if top1:
        updated_payload.update(
            {
                "score": top1["score"],
                "gear": top1.get("gear", []),
                "minis": top1.get("minis", []),
                "details": attach_attempt_meta(top1.get("details", {})),
            }
        )

    updated_payload["fg_entries"] = list(current_run_fg_candidates)
    updated_payload.pop("second", None)

    # Find FG result for TOP1's specific loadout (not global best)
    # This ensures force_details_json matches the loadout's gear/minis
    fg_score_val = 0
    top1_gear = tuple(top1.get("gear", [])) if top1 else ()
    top1_minis = tuple(top1.get("minis", [])) if top1 else ()

    matching_fg = None
    for fg_cand in current_run_fg_candidates:
        fg_gear = tuple(fg_cand.get("gear", []))
        fg_minis = tuple(fg_cand.get("minis", []))
        if fg_gear == top1_gear and fg_minis == top1_minis:
            matching_fg = fg_cand
            break

    if matching_fg:
        fg_score_val = matching_fg.get("score", 0) or 0
        updated_payload["force"] = matching_fg.get("force") or {}
    # If no matching FG from current run, keep the old one from prev_record (if gear matches)
    elif prev_record and prev_record.get("force"):
        prev_force = prev_record.get("force")
        # Validate propagated force data

        if not has_valid_fg_config(prev_force):
            prev_force = None

        if prev_force:
            # `force` payload is flat and doesn't include gear/minis; match on the loadout itself.
            if top1_gear == tuple(names_list(prev_record.get("gear") or [])) and top1_minis == tuple(
                names_list(prev_record.get("minis") or [])
            ):
                updated_payload["force"] = prev_force
                fg_score_val = prev_record.get("fg_score", 0) or 0
            else:
                updated_payload.pop("force", None)
        else:
            updated_payload.pop("force", None)
    else:
        updated_payload.pop("force", None)

    updated_payload["fg_score"] = fg_score_val

    # Track BEST FG entry separately (may be a different loadout than best base)
    # This ensures we always persist the highest-scoring FG loadout
    best_fg_entry = None
    if current_run_fg_candidates:
        best_fg_entry = max(current_run_fg_candidates, key=lambda x: x.get("score", 0))
        best_fg_score = best_fg_entry.get("score", 0)
        updated_payload["run_best_fg_score"] = best_fg_score or 0
        # Only include if it's actually better than top1's FG score
        if best_fg_score > fg_score_val:
            updated_payload["best_fg"] = {
                "score": best_fg_score,
                "base_score": best_fg_entry.get("base_score", 0) or 0,
                "fg_base_score": best_fg_entry.get("fg_base_score", best_fg_entry.get("base_score", 0)) or 0,
                "gear": best_fg_entry.get("gear", []),
                "minis": best_fg_entry.get("minis", []),
                "details": best_fg_entry.get("details", {}),
                "force": best_fg_entry.get("force") or {},
            }
    else:
        updated_payload["run_best_fg_score"] = 0

    return updated_payload
