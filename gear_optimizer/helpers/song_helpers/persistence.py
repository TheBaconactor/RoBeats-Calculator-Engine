"""
Song Helpers - Persistence - Database payload and persistence entry building.

This module provides persistence operations:
- build_db_payload: Build database persistence payload
- build_persistence_entries: Build all persistence entries
"""

import json


def _has_valid_fg_config(fg_container):
    """
    Check if FG container (entry or force obj) has a non-empty/non-zero configuration.
    Handles both 'fg_entry' result format and 'force_obj' DB format.
    """
    try:
        # Path 1: Result dict (has "data")
        data = fg_container.get("data", {})
        if data:
            fg_meta = data.get("ForceGreats", {})
            config = fg_meta.get("config", {})
            return bool(config and sum(config.values()) > 0)

        # Path 2: Force object (direct details)
        details = fg_container.get("details", {})
        if details:
            fg_meta = details.get("ForceGreats", {})
            config = fg_meta.get("config", {})
            return bool(config and sum(config.values()) > 0)

        return False
    except Exception:
        return False


def build_db_payload(
    best_data,
    best_gear,
    best_minis,
    prev_record,
    attempt_lifetime,
    prev_attempts_first,
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
        prev_attempts_first: Previous attempts_first counter
        fg_variants: Force greats variants
        build_details_fn: Function to build details dict from data dict
        db_best_fg_score: Best FG score from DB (across all loadouts)

    Returns:
        dict: Database payload
    """
    # Use BaseScore if available (true base score).
    # Fall back to Score if BaseScore not present (backwards compatibility).
    score = best_data.get("BaseScore") or best_data.get("Score", 0)

    prev_score = prev_record.get("score") if prev_record else None
    is_first = prev_record is None
    is_better = (prev_score is None) or (score > prev_score)

    def extract_names(record):
        """Extract names from record, handling both dict and string formats."""

        def get_name(item):
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""

        gear_items = record.get("gear") if record else []
        minis_items = record.get("minis") if record else []
        loadout = record.get("loadout") if record else None
        if (not gear_items and not minis_items) and loadout:
            gear_items = loadout[:6]
            minis_items = loadout[6:9]

        gear_names = [get_name(g) for g in (gear_items or [])]
        minis_names = [get_name(m) for m in (minis_items or [])]
        return gear_names, minis_names

    def _names(items):
        out = []
        for it in items or []:
            if isinstance(it, dict):
                name = it.get("Name", "")
            else:
                name = str(it) if it else ""
            out.append(name)
        return out

    best_gear_names = _names(best_gear)
    best_mini_names = _names(best_minis)
    best_details = build_details_fn(best_data)

    attempts_first = 1 if is_first or is_better else (prev_attempts_first + 1 if prev_attempts_first else 1)

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
        fg_gear_names = _names(fg_gear)
        fg_mini_names = _names(fg_minis)
        # Preserve the *base* score context for this FG entry so we can persist
        # the loadout with correct base+fg pairing (score != fg_score).
        base_score = fg_entry.get("base_score")
        if base_score is None:
            base_score = fg_entry.get("score", 0)
        current_run_fg_candidates.append(
            {
                # "score" is intentionally the FG score in this list (historical naming).
                "score": fg_entry.get("fg_score", 0),
                "base_score": base_score or 0,
                "gear": fg_gear_names,
                "minis": fg_mini_names,
                "details": build_details_fn(fg_data),
            }
        )

    # Determine if FG improved
    best_fg_score_run = 0
    if current_run_fg_candidates:
        best_cand = max(current_run_fg_candidates, key=lambda x: x.get("score", 0))
        best_fg_score_run = best_cand.get("score", 0)

    # Use the max FG score from DB (any loadout) if provided, else fallback to prev_record
    prev_fg_score = (
        db_best_fg_score if db_best_fg_score is not None else (prev_record.get("fg_score") if prev_record else 0)
    )
    prev_fg_score = prev_fg_score or 0  # Ensure it's not None
    is_fg_better = best_fg_score_run > prev_fg_score

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
        updated_payload["force"] = {
            "score": matching_fg.get("score"),
            "gear": matching_fg.get("gear", []),
            "minis": matching_fg.get("minis", []),
            "details": matching_fg.get("details", {}),
        }
    # If no matching FG from current run, keep the old one from prev_record (if gear matches)
    elif prev_record and prev_record.get("force"):
        prev_force = prev_record.get("force")
        # Validate propagated force data

        if not _has_valid_fg_config(prev_force):
            prev_force = None

        if prev_force:
            prev_force_gear = tuple(prev_force.get("gear", []))
            prev_force_minis = tuple(prev_force.get("minis", []))
            if prev_force_gear == top1_gear and prev_force_minis == top1_minis:
                updated_payload["force"] = prev_force
                fg_score_val = prev_force.get("score", 0) or 0
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
        # Only include if it's actually better than top1's FG score
        if best_fg_score > fg_score_val:
            updated_payload["best_fg"] = {
                "score": best_fg_score,
                "base_score": best_fg_entry.get("base_score", 0) or 0,
                "gear": best_fg_entry.get("gear", []),
                "minis": best_fg_entry.get("minis", []),
                "details": best_fg_entry.get("details", {}),
            }

    return updated_payload


def build_persistence_entries(
    db_payload,
    ga_candidates,
    loadout_entries,
    build_details_fn,
):
    """
    Build all persistence entries.

    Args:
        db_payload: Database payload
        ga_candidates: List of GA candidate loadouts
        loadout_entries: Dictionary of loadout entries (or None)
        build_details_fn: Function to build details dict from data dict

    Returns:
        list: List of persistence entries
    """
    from ...core.constants import LOADOUTS_PER_SONG_LIMIT

    persist_entries = []
    seen_hashes: set[str] = set()

    def _loadout_hash(gear_items, mini_items) -> str:
        try:
            from ...data.database import get_loadout_hash

            return str(get_loadout_hash(gear_items, mini_items))
        except Exception:
            # Fallback: best-effort stable-ish signature
            return str((tuple(gear_items or []), tuple(mini_items or [])))

    def _names_list(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(it.get("Name", ""))
            else:
                names.append(str(it) if it else "")
        return names

    def _append_entry(score_val, gear_items, mini_items, details_obj, fg_score_val=0, force_obj=None):
        # Avoid emitting duplicates (we may include top1/best_fg + retained union entries).
        h = _loadout_hash(gear_items, mini_items)
        if h in seen_hashes:
            return
        seen_hashes.add(h)

        # Extract attempt metadata from details for tagging
        attempt_lifetime = details_obj.get("attempt_lifetime", 0) if details_obj else 0
        attempts_first = details_obj.get("attempts_first", 0) if details_obj else 0

        # Tag attempts metadata so downstream displays (Best/Lifetime) can advance.
        details_with_meta = dict(details_obj or {})
        details_with_meta["attempt_lifetime"] = attempt_lifetime
        details_with_meta["attempts_first"] = attempts_first

        persist_entries.append(
            {
                "score": score_val or 0,
                "fg_score": fg_score_val or 0,
                "gear": _names_list(gear_items),
                "minis": _names_list(mini_items),
                "details": details_with_meta,
                "force": force_obj,
            }
        )

    # Top 1 (base) - store with its OWN fg_score and force data (if available)
    # This ensures the force_details_json matches the loadout gear
    _append_entry(
        db_payload.get("score", 0),
        db_payload.get("gear", []),
        db_payload.get("minis", []),
        db_payload.get("details", {}),
        db_payload.get("fg_score", 0),
        db_payload.get("force"),  # This comes from top1's own FG, not global best
    )

    # BEST FG ENTRY: If a different loadout has the best FG score, include it as a priority entry
    # This ensures we always persist the highest-scoring FG loadout
    best_fg = db_payload.get("best_fg")
    if best_fg:
        # If we already have `loadout_entries` (DB+GA union), the best FG loadout
        # will be included in that loop with correct base_score+fg_score. Only
        # emit a separate entry when it is missing (legacy path).
        best_fg_hash = None
        try:
            from ...data.database import get_loadout_hash

            best_fg_hash = get_loadout_hash(best_fg.get("gear", []), best_fg.get("minis", []))
        except Exception:
            best_fg_hash = None

        if isinstance(loadout_entries, dict) and best_fg_hash and best_fg_hash in loadout_entries:
            best_fg = None

    if best_fg:
        best_fg_gear = best_fg.get("gear", [])
        best_fg_minis = best_fg.get("minis", [])
        best_fg_details = best_fg.get("details", {})
        best_fg_score = best_fg.get("score", 0)

        # Build force object for the best FG entry
        best_fg_force = {
            "score": best_fg_score,
            "gear": best_fg_gear,
            "minis": best_fg_minis,
            "details": best_fg_details,
        }

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
    # NOTE: GA candidates are now handled in the loadout_entries loop below,
    # which includes their FG scores. This section is kept for backwards compatibility
    # with older code that may not populate loadout_entries.
    if ga_candidates and loadout_entries is None:
        for eval_result in ga_candidates:
            eval_data = eval_result.get("Data") or {}
            # Use BaseScore (true score) for DB storage; fall back for older payloads.
            eval_score = eval_result.get("BaseScore") or eval_result.get("Score", 0)
            eval_gear = eval_result.get("Gear", [])
            eval_minis = eval_result.get("Minis", [])
            eval_details = build_details_fn(eval_data)
            _append_entry(
                eval_score,
                eval_gear,
                eval_minis,
                eval_details,
                0,  # No FG score available in this legacy path
                None,
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

        # Top base (retain by base score only).
        top_base = sorted(items, key=lambda kv: _base_score(kv[1]), reverse=True)[: int(LOADOUTS_PER_SONG_LIMIT)]

        # Top FG (retain by fg_score, but only when valid FG details exist and FG beats base).
        fg_candidates = []
        for h, e in items:
            try:
                base_s = _base_score(e)
                fg_s = _fg_score(e)
                force_obj = e.get("force")
                if fg_s > base_s and force_obj is not None and _has_valid_fg_config(force_obj):
                    fg_candidates.append((h, e))
            except Exception:
                continue
        top_fg = sorted(fg_candidates, key=lambda kv: _fg_score(kv[1]), reverse=True)[: int(LOADOUTS_PER_SONG_LIMIT)]

        selected_hashes = set()
        for h, _e in list(top_base) + list(top_fg):
            selected_hashes.add(str(h))

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

            _append_entry(
                entry.get("base_score") or entry.get("score", 0),
                entry.get("gear", []),
                entry.get("minis", []),
                details_obj,
                fg_score_to_save,
                force_obj,
            )

    return persist_entries
