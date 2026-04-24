"""
Song Helpers - Persistence - Database payload and persistence entry building.

This module provides persistence operations:
- build_db_payload: Build database persistence payload
- build_persistence_entries: Build all persistence entries

Extension rule:
- If persistence shape or record-improvement logic changes, update this module first
  and reuse these helpers from orchestrators to avoid duplicated save semantics.
"""

from collections.abc import Callable
from typing import Any

from ...core.utils import get_selected_element
from .ga_entry_utils import entry_loadout_hash, materialize_candidate_names, materialize_entry_names
from .item_utils import names_list
from .retention import select_retained_hashes


def _safe_int_force(value: Any, default: int = 0) -> int:
    """Best-effort integer coercion used for DB payload normalization."""
    try:
        return int(str(value)) if value is not None else int(default)
    except Exception:
        try:
            return int(float(str(value)))
        except Exception:
            return int(default)


def _normalize_force_payload(force_obj: object) -> dict:
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

    try:
        from .force_greats.result_application import materialize_stats_from_payload

        computed_stats = materialize_stats_from_payload(out, selected_element=selected_element, mutate_payload=False)
        if isinstance(computed_stats, dict) and computed_stats:
            out["Stats"] = computed_stats
            return out
    except Exception:
        pass

    out["Stats"] = dict(base_stats)
    return out


def _has_valid_fg_config(fg_container):
    """
    Check if FG container (entry or force obj) has a non-empty/non-zero configuration.
    Handles both 'fg_entry' result format and flat `force` payload format.
    """
    try:
        # Path 1: Result dict (has "data")
        data = fg_container.get("data", {})
        if data:
            fg_meta = data.get("ForceGreats", {})
            config = fg_meta.get("config", {})
            return bool(config and sum(config.values()) > 0)

        # Path 2: Flat force payload (persisted in force_details_json)
        fg_meta = fg_container.get("ForceGreats", {})
        if fg_meta:
            config = fg_meta.get("config", {})
            return bool(config and sum(config.values()) > 0)

        return False
    except Exception:
        return False


def evaluate_record_update(best_data, prev_record, fg_variants, db_best_fg_score=None) -> dict:
    """
    Evaluate whether the current run beats prior base/FG records.

    Returns a dict with:
        - record_update (bool)
        - is_first (bool)
        - is_better (bool)
        - is_fg_better (bool)
        - score (int)
        - prev_score (int|None)
        - best_fg_score_run (int)
        - prev_fg_score (int)
    """
    score = 0
    if isinstance(best_data, dict):
        score = _safe_int_force(best_data.get("BaseScore") or best_data.get("Score", 0), 0)

    prev_score = None
    if isinstance(prev_record, dict):
        prev_score_raw = prev_record.get("score")
        if prev_score_raw is not None:
            prev_score = _safe_int_force(prev_score_raw, 0)

    is_first = prev_record is None
    is_better = (prev_score is None) or (score > prev_score)

    best_fg_score_run = 0
    for fg_entry in fg_variants or []:
        if not isinstance(fg_entry, dict):
            continue
        if not _has_valid_fg_config(fg_entry):
            continue
        base_score = fg_entry.get("base_score")
        if base_score is None:
            base_score = fg_entry.get("score", 0)
        base_score_i = _safe_int_force(base_score, 0)
        fg_score_i = _safe_int_force(fg_entry.get("fg_score", 0), 0)
        if fg_score_i <= base_score_i:
            continue
        if fg_score_i > best_fg_score_run:
            best_fg_score_run = fg_score_i

    prev_fg_score = (
        db_best_fg_score if db_best_fg_score is not None else (prev_record.get("fg_score") if prev_record else 0)
    )
    prev_fg_score = _safe_int_force(prev_fg_score, 0)
    is_fg_better = best_fg_score_run > prev_fg_score

    return {
        "record_update": bool(is_better or is_fg_better),
        "is_first": bool(is_first),
        "is_better": bool(is_better),
        "is_fg_better": bool(is_fg_better),
        "score": int(score),
        "prev_score": prev_score,
        "best_fg_score_run": int(best_fg_score_run),
        "prev_fg_score": int(prev_fg_score),
    }


def evaluate_progress_record_update(
    best_data,
    prev_record,
    fg_variants,
    *,
    db_best_fg_score=None,
    baseline_valid: bool = True,
    fg_only: bool = False,
) -> dict | None:
    """
    Progress/UI-safe record evaluation.

    `baseline_valid=False` means the DB baseline could not be read reliably
    (for example, a strict read hit a temporary lock). In that case we fail
    closed and suppress `record_update` so the NEW counter cannot over-report.
    """
    if not baseline_valid:
        score = 0
        if isinstance(best_data, dict):
            score = _safe_int_force(best_data.get("BaseScore") or best_data.get("Score", 0), 0)
        best_fg_score_run = 0
        if fg_only:
            for fg_entry in fg_variants or []:
                if not isinstance(fg_entry, dict):
                    continue
                if not _has_valid_fg_config(fg_entry):
                    continue
                base_score = fg_entry.get("base_score")
                if base_score is None:
                    base_score = fg_entry.get("score", 0)
                base_score_i = _safe_int_force(base_score, 0)
                fg_score_i = _safe_int_force(fg_entry.get("fg_score", 0), 0)
                if fg_score_i > base_score_i and fg_score_i > best_fg_score_run:
                    best_fg_score_run = fg_score_i
        prev_fg_score = (
            db_best_fg_score if db_best_fg_score is not None else (prev_record.get("fg_score") if prev_record else 0)
        )
        return {
            "record_update": False,
            "baseline_unavailable": True,
            "is_first": False,
            "is_better": False,
            "is_fg_better": False,
            "score": int(score),
            "prev_score": None,
            "best_fg_score_run": int(best_fg_score_run),
            "prev_fg_score": int(_safe_int_force(prev_fg_score, 0)),
        }

    record_info = evaluate_record_update(best_data, prev_record, fg_variants, db_best_fg_score=db_best_fg_score)
    if not isinstance(record_info, dict):
        return None
    if fg_only:
        record_info = dict(record_info)
        record_info["record_update"] = bool(record_info.get("is_fg_better"))
    return record_info


def make_build_details_fn(
    primary_color: str, secondary_color: str, effective_difficulty: str
) -> Callable[[dict], dict]:
    """
    Build a `build_details(data_dict) -> dict` function for persistence/loadout helpers.

    This is duplicated across multiple pipeline/orchestrator entrypoints; centralizing it
    keeps the persisted schema consistent.
    """

    try:
        from .force_greats.result_application import materialize_stats_from_payload
    except Exception:
        materialize_stats_from_payload = None

    def build_details(data_dict: dict) -> dict:
        if not isinstance(data_dict, dict) or not data_dict:
            return {}
        selected_element = get_selected_element(data_dict, "")
        stats_obj = data_dict.get("Stats")
        if not (isinstance(stats_obj, dict) and stats_obj) and callable(materialize_stats_from_payload):
            try:
                stats_obj = materialize_stats_from_payload(
                    data_dict,
                    selected_element=selected_element,
                    mutate_payload=False,
                )
            except Exception:
                stats_obj = stats_obj if isinstance(stats_obj, dict) else {}
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
        if not _has_valid_fg_config(fg_entry):
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
        except Exception:
            base_score_i = 0
        try:
            fg_score_i = int(fg_entry.get("fg_score", 0) or 0)
        except Exception:
            fg_score_i = 0

        # ForceGreats is only a "useful" variant when it actually improves the score
        # for the same loadout. Persisting worse-than-base configs is confusing to users
        # (it looks like FG "regressed" compared to Base) and creates noisy FG records.
        if fg_score_i <= base_score_i:
            continue
        current_run_fg_candidates.append(
            {
                # "score" is intentionally the FG score in this list (historical naming).
                "score": fg_score_i,
                "base_score": base_score_i,
                "gear": fg_gear_names,
                "minis": fg_mini_names,
                "details": build_details_fn(_normalize_force_payload(fg_data)),
                # Flat raw payload to persist in `force_details_json`.
                "force": _normalize_force_payload(fg_data),
            }
        )

    # Centralized record comparison to keep all callers aligned.
    record_info = evaluate_record_update(best_data, prev_record, fg_variants, db_best_fg_score=db_best_fg_score)
    score = _safe_int_force(record_info.get("score", score), 0)
    prev_score = record_info.get("prev_score")
    is_first = bool(record_info.get("is_first"))
    is_better = bool(record_info.get("is_better"))
    is_fg_better = bool(record_info.get("is_fg_better"))
    best_fg_score_run = _safe_int_force(record_info.get("best_fg_score_run", 0), 0)
    prev_fg_score = _safe_int_force(record_info.get("prev_fg_score", 0), 0)

    if is_first:
        print(" >> NEW RECORD! (First entry for this song/context). Saving to Evolution Database...")
    elif is_better:
        msg = f" >> NEW RECORD! Previous: {prev_score} | New: {score}"
        if is_fg_better and best_fg_score_run > 0:
            msg += f" (FG: {prev_fg_score} -> {best_fg_score_run})"
        msg += " - Updating Evolution Database..."
        print(msg)
    elif is_fg_better and best_fg_score_run > 0:
        # FG-only improvement
        msg = f" >> NEW RECORD (ForceGreats)! Previous FG: {prev_fg_score} | New FG: {best_fg_score_run} - Updating Evolution Database..."
        print(msg)
    else:
        msg = f" >> No improvement over DB Record (Base: {prev_score}, FG: {prev_fg_score})"
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

        if not _has_valid_fg_config(prev_force):
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
                "gear": best_fg_entry.get("gear", []),
                "minis": best_fg_entry.get("minis", []),
                "details": best_fg_entry.get("details", {}),
                "force": best_fg_entry.get("force") or {},
            }
    else:
        updated_payload["run_best_fg_score"] = 0

    return updated_payload


def _canonicalize_retained_baseline_persist_entries(
    persist_entries: list[dict],
    *,
    calc_song: dict | None,
    ref_arrays: dict | None,
    cfg_dict: dict | None,
) -> list[dict]:
    """Route retained baseline rows through the shared replay canonicalizer."""
    from .baseline_replay import canonicalize_baseline_persist_entries

    return canonicalize_baseline_persist_entries(
        persist_entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
    )


def build_persistence_entries(
    db_payload,
    ga_candidates,
    loadout_entries,
    build_details_fn,
    *,
    calc_song: dict | None = None,
    ref_arrays: dict | None = None,
    cfg_dict: dict | None = None,
):
    """
    Build all persistence entries.

    Args:
        db_payload: Database payload
        ga_candidates: List of GA candidate loadouts
        loadout_entries: Dictionary of loadout entries (or None)
        build_details_fn: Function to build details dict from data dict
        calc_song: Optional calc-song payload used to canonicalize replayable persisted scores
        ref_arrays: Optional stats lookup arrays used for canonical replay scoring
        cfg_dict: Optional runtime config dict used to resolve the baseline TeamBuff tier

    Returns:
        list: List of persistence entries
    """
    from ...core.constants import LOADOUTS_PER_SONG_LIMIT

    persist_entries = []
    # Deduplicate by loadout hash but prefer the best base score and best FG payload when
    # duplicates occur (e.g., top1 + union entries, best_fg fallback + union entries).
    entry_index_by_hash: dict[str, int] = {}
    def _loadout_hash(gear_items, mini_items) -> str:
        try:
            from ...data.database import get_loadout_hash

            return str(get_loadout_hash(gear_items, mini_items))
        except Exception:
            # Fallback: best-effort stable-ish signature
            return str((tuple(gear_items or []), tuple(mini_items or [])))

    def _append_entry(
        score_val,
        gear_items,
        mini_items,
        details_obj,
        fg_score_val=0,
        force_obj=None,
        *,
        fg_base_score_val=None,
        loadout_hash_val=None,
    ):
        h = str(loadout_hash_val or "").strip() or _loadout_hash(gear_items, mini_items)

        # Extract attempt metadata from details for tagging
        attempt_lifetime = details_obj.get("attempt_lifetime", 0) if details_obj else 0
        attempts_first = details_obj.get("attempts_first", 0) if details_obj else 0

        # Tag attempts metadata so downstream displays (Best/Lifetime) can advance.
        details_with_meta = dict(details_obj or {})
        details_with_meta["attempt_lifetime"] = attempt_lifetime
        details_with_meta["attempts_first"] = attempts_first

        force_out = _normalize_force_payload(force_obj) if isinstance(force_obj, dict) else force_obj

        new_entry = {
            "loadout_hash": h,
            "score": score_val or 0,
            "fg_score": fg_score_val or 0,
            "gear": names_list(gear_items),
            "minis": names_list(mini_items),
            "details": details_with_meta,
            "force": force_out,
        }
        # Preserve the base-score context for the best-FG payload when available.
        # This enables FG leaderboard semantics (`fg_score > fg_base_score`) even when
        # the best base score for the same hash is higher than the FG base context.
        if fg_base_score_val is not None:
            try:
                new_entry["fg_base_score"] = int(fg_base_score_val or 0)
            except Exception:
                new_entry["fg_base_score"] = 0
        elif force_out is not None and int(fg_score_val or 0) > 0:
            try:
                new_entry["fg_base_score"] = int(score_val or 0)
            except Exception:
                new_entry["fg_base_score"] = 0

        # Merge duplicates by hash to preserve BOTH:
        # - best base score + its details payload, AND
        # - best FG score + its force payload.
        #
        # This prevents FG-allocation details from accidentally replacing base-optimal
        # details when the same hash is emitted multiple times in different roles.
        idx = entry_index_by_hash.get(h)
        if idx is None:
            persist_entries.append(new_entry)
            entry_index_by_hash[h] = len(persist_entries) - 1
            return

        existing = persist_entries[idx]
        if not isinstance(existing, dict):
            persist_entries[idx] = new_entry
            return

        try:
            existing_score = int(existing.get("score", 0) or 0)
        except Exception:
            existing_score = 0
        try:
            new_score_i = int(new_entry.get("score", 0) or 0)
        except Exception:
            new_score_i = 0

        if new_score_i > existing_score:
            existing["score"] = new_score_i
            existing["gear"] = new_entry.get("gear", existing.get("gear"))
            existing["minis"] = new_entry.get("minis", existing.get("minis"))
            existing["details"] = new_entry.get("details", existing.get("details"))
        elif new_score_i == existing_score:
            # Fill missing details payload on ties (common when GA details are materialized lazily).
            if not existing.get("details") and new_entry.get("details"):
                existing["details"] = new_entry["details"]

        try:
            existing_fg = int(existing.get("fg_score", 0) or 0)
        except Exception:
            existing_fg = 0
        try:
            new_fg_i = int(new_entry.get("fg_score", 0) or 0)
        except Exception:
            new_fg_i = 0

        if new_fg_i > existing_fg:
            existing["fg_score"] = new_fg_i
            existing["force"] = new_entry.get("force")
            if "fg_base_score" in new_entry:
                existing["fg_base_score"] = new_entry.get("fg_base_score")
        elif new_fg_i == existing_fg:
            # Fill missing force payload on ties.
            if existing.get("force") is None and new_entry.get("force") is not None:
                existing["force"] = new_entry.get("force")
                if "fg_base_score" in new_entry and "fg_base_score" not in existing:
                    existing["fg_base_score"] = new_entry.get("fg_base_score")
            elif "fg_base_score" in new_entry and "fg_base_score" not in existing:
                existing["fg_base_score"] = new_entry.get("fg_base_score")

    def _canonicalize_retained_entries(entries_to_normalize: list[dict]) -> list[dict]:
        """
        Normalize retained rows before we merge them into the persistence payload.

        Why this exists:
        - seeded `loadout_entries` can inherit stale base scores from DB/FG staging
        - the final baseline canonicalizer repairs the persisted output, but the deferred
          pre-persistence surface would still expose the stale rows

        Running the same replay canonicalization here keeps the retained frontier aligned with
        the write-path contract and makes deferred/pre-persist inspection reflect the rows we
        actually mean to expose.
        """
        if not entries_to_normalize:
            return entries_to_normalize
        if not (isinstance(calc_song, dict) and calc_song and isinstance(ref_arrays, dict) and ref_arrays):
            return entries_to_normalize

        try:
            from .baseline_replay import canonicalize_baseline_persist_entries

            return canonicalize_baseline_persist_entries(
                entries_to_normalize,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                cfg_dict=cfg_dict,
            )
        except Exception:
            return entries_to_normalize

    # Top 1 (base) - store with its OWN fg_score and force data (if available)
    # This ensures the force_details_json matches the loadout gear
    top1_details = db_payload.get("details", {})
    _append_entry(
        db_payload.get("score", 0),
        db_payload.get("gear", []),
        db_payload.get("minis", []),
        top1_details,
        db_payload.get("fg_score", 0),
        db_payload.get("force"),  # This comes from top1's own FG, not global best
    )

    # BEST FG ENTRY: If a different loadout has the best FG score, include it as a priority entry
    # This ensures we always persist the highest-scoring FG loadout
    best_fg = db_payload.get("best_fg")
    if best_fg:
        # If we already have `loadout_entries` (DB+GA union), the best FG loadout
        # will be included in that loop with correct base_score+fg_score. Only
        # emit a separate entry when it is missing (fallback path).
        best_fg_hash = None
        try:
            from ...data.database import get_loadout_hash

            best_fg_hash = get_loadout_hash(best_fg.get("gear", []), best_fg.get("minis", []))
        except Exception:
            best_fg_hash = None

        if isinstance(loadout_entries, dict) and best_fg_hash:
            for entry in loadout_entries.values():
                try:
                    if str(entry_loadout_hash(entry) or "") == str(best_fg_hash):
                        best_fg = None
                        break
                except Exception:
                    continue

    if best_fg:
        best_fg_gear = best_fg.get("gear", [])
        best_fg_minis = best_fg.get("minis", [])
        best_fg_details = best_fg.get("details", {})
        best_fg_score = best_fg.get("score", 0)

        # Flat force payload (persisted in `force_details_json`).
        best_fg_force = best_fg.get("force") if isinstance(best_fg.get("force"), dict) else None

        # Base score context for the best-FG loadout (never equals FG score).
        base_score = best_fg.get("base_score")
        if base_score is None:
            base_score = best_fg_details.get("BaseScore") or best_fg_details.get("Score", 0)

        # Fallback: recover from `loadout_entries` if present.
        if (not base_score) and isinstance(loadout_entries, dict):
            try:
                from ...data.database import get_loadout_hash

                h = get_loadout_hash(best_fg_gear, best_fg_minis)
                entry = loadout_entries.get(h) or {}
                base_score = entry.get("base_score") or entry.get("score", 0) or 0
            except Exception:
                base_score = base_score or 0

        _append_entry(
            base_score,  # Base score context (unpenalized)
            best_fg_gear,
            best_fg_minis,
            best_fg_details,
            best_fg_score,  # fg_score
            best_fg_force,  # force object
        )

    # GA candidates (capped to DB limit)
    # NOTE: GA candidates are normally handled in the loadout_entries loop below,
    # which includes their FG scores. This section only covers callers that do not
    # provide loadout_entries.
    if ga_candidates and loadout_entries is None:
        for eval_result in ga_candidates:
            eval_data = eval_result.get("Data") or {}
            # Use BaseScore (true score) for DB storage; fall back for older payloads.
            eval_score = eval_result.get("BaseScore") or eval_result.get("Score", 0)
            eval_gear, eval_minis = materialize_candidate_names(eval_result, mutate=True)
            eval_details = build_details_fn(eval_data)

            _append_entry(
                eval_score,
                eval_gear,
                eval_minis,
                eval_details,
                0,  # No FG score available in this fallback path
                None,
                loadout_hash_val=eval_result.get("loadout_hash"),
            )

    # Include DB+GA union entries (with updated FG) if available
    if loadout_entries is not None:
        # PERF: The DB enforces `LOADOUTS_PER_SONG_LIMIT` by pruning, but building thousands of
        # Python dicts + JSON payloads just to throw most away is expensive (and blocks GPU).
        # Pre-prune here to the exact retention intent:
        # - top-N by base score, plus
        # - top-N by FG score (only when FG strictly beats base AND force config is valid).
        try:
            items = list(loadout_entries.items()) if isinstance(loadout_entries, dict) else []
        except Exception:
            items = []

        def _base_score(entry: dict) -> int:
            try:
                return int(entry.get("base_score") or entry.get("score", 0) or 0)
            except Exception:
                return 0

        def _fg_score(entry: dict) -> int:
            try:
                return int(entry.get("fg_score", 0) or 0)
            except Exception:
                return 0

        def _fg_valid(entry: dict) -> bool:
            force_obj = entry.get("force")
            return force_obj is not None and _has_valid_fg_config(force_obj)

        selected_hashes = select_retained_hashes(
            items,
            limit=int(LOADOUTS_PER_SONG_LIMIT),
            base_score_fn=_base_score,
            fg_score_fn=_fg_score,
            fg_valid_fn=_fg_valid,
        )

        retained_entries: list[dict[str, Any]] = []

        for h, entry in items:
            if str(h) not in selected_hashes:
                continue
            # Ensure FG score is zeroed if configuration is invalid

            fg_score_to_save = entry.get("fg_score", 0)
            force_obj = entry.get("force")

            if force_obj and not _has_valid_fg_config(force_obj):
                fg_score_to_save = 0
                force_obj = None  # Explicitly clear valid force object if invalid (prevent empty JSON)

            # PERF: In some fast paths we avoid constructing `details` for GA candidates
            # during FG prep to reduce Python overhead. For DB persistence we still want
            # the full details payload, so build it lazily from `eval_data` here.
            details_obj = entry.get("details", {}) or {}
            if (not details_obj) and entry.get("eval_data") and build_details_fn is not None:
                try:
                    details_obj = build_details_fn(entry.get("eval_data") or {})
                except Exception:
                    details_obj = details_obj or {}

            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            retained_entry = {
                "loadout_hash": str(h),
                "score": entry.get("base_score") or entry.get("score", 0),
                "fg_score": fg_score_to_save,
                "gear": gear_names,
                "minis": mini_names,
                "details": details_obj,
                "force": force_obj,
            }
            if isinstance(entry, dict) and entry.get("fg_base_score") is not None:
                retained_entry["fg_base_score"] = entry.get("fg_base_score")
            retained_entries.append(retained_entry)

        for entry in _canonicalize_retained_entries(retained_entries):
            if not isinstance(entry, dict):
                continue
            _append_entry(
                entry.get("score", 0),
                entry.get("gear", []),
                entry.get("minis", []),
                entry.get("details", {}),
                entry.get("fg_score", 0),
                entry.get("force"),
                fg_base_score_val=entry.get("fg_base_score"),
                loadout_hash_val=entry.get("loadout_hash"),
            )

    return _canonicalize_retained_baseline_persist_entries(
        persist_entries,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=cfg_dict,
    )
