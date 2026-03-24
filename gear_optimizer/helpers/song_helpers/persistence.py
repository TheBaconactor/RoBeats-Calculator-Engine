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

    # Persist only the per-window HitSim deltas; strip the legacy scalar if present.
    fg0 = out.get("ForceGreats")
    if isinstance(fg0, dict) and "hitsim_offset_delta_ms" in fg0:
        fg1 = dict(fg0)
        fg1.pop("hitsim_offset_delta_ms", None)
        out["ForceGreats"] = fg1

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
        hitsim_deltas_ms_raw = data_dict.get("hitsim_offset_deltas_ms")
        hitsim_deltas_ms: list[int] | None = None
        if isinstance(hitsim_deltas_ms_raw, (list, tuple)):
            tmp: list[int] = []
            for v in hitsim_deltas_ms_raw:
                try:
                    tmp.append(int(v))
                except Exception:
                    continue
            if tmp:
                hitsim_deltas_ms = tmp
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
            "hitsim_offset_deltas_ms": hitsim_deltas_ms,
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


def build_persistence_entries(
    db_payload,
    ga_candidates,
    loadout_entries,
    build_details_fn,
    *,
    calc_song: dict | None = None,
    ref_arrays: dict | None = None,
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
    # PERF: Base HitSim per-window deltas depend only on (FFR, FT) + the song's simulated timing
    # (HumanHitSim.ApplyTo=ALL). Cache per (FFR, FT) stat pair.
    _hitsim_base_deltas_cache: dict[tuple[int, int], tuple[int, ...]] = {}
    # PERF: FG HitSim per-window deltas depend on (FFR, FT, NonFever counts) + the song's simulated timing.
    _hitsim_fg_deltas_cache: dict[tuple[int, int, tuple[int, ...]], tuple[int, ...]] = {}

    def _maybe_backfill_base_hitsim_deltas(details_obj: dict) -> dict:
        if not (calc_song is not None and ref_arrays is not None and isinstance(details_obj, dict)):
            return details_obj

        existing_deltas = details_obj.get("hitsim_offset_deltas_ms")
        if isinstance(existing_deltas, (list, tuple)) and existing_deltas:
            # Strip legacy scalar if present on old rows.
            if "hitsim_offset_delta_ms" in details_obj:
                out0 = dict(details_obj)
                out0.pop("hitsim_offset_delta_ms", None)
                return out0
            return details_obj

        meta0 = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
        apply_to = str(meta0.get("HumanHitSimApplyTo", "") or "").strip().upper()
        if not (meta0.get("HumanHitSimApplied") and apply_to == "ALL"):
            return details_obj

        stats_obj = details_obj.get("Stats")
        if not isinstance(stats_obj, dict) or not stats_obj:
            return details_obj

        try:
            ff_stat = int(stats_obj.get("Fever Fill Rate", 0) or 0)
        except Exception:
            ff_stat = 0
        try:
            ft_stat = int(stats_obj.get("Fever Time", 0) or 0)
        except Exception:
            ft_stat = 0

        cache_key = (int(ff_stat), int(ft_stat))
        deltas_t = _hitsim_base_deltas_cache.get(cache_key)
        if deltas_t is None:
            try:
                from ...solver.scoring.force_greats import summarize_hitsim_offset_deltas_ms_for_base

                computed = summarize_hitsim_offset_deltas_ms_for_base(calc_song, {"Stats": stats_obj}, ref_arrays)
            except Exception:
                computed = None
            if computed:
                try:
                    deltas_t = tuple(int(x) for x in computed)
                except Exception:
                    deltas_t = None
                if deltas_t:
                    _hitsim_base_deltas_cache[cache_key] = deltas_t

        if not deltas_t:
            return details_obj

        out = dict(details_obj)
        out.pop("hitsim_offset_delta_ms", None)
        out["hitsim_offset_deltas_ms"] = list(deltas_t)
        return out

    def _nonfever_counts_from_config_for_hitsim(config: object) -> tuple[int, ...]:
        if not isinstance(config, dict) or not config:
            return ()
        pairs: list[tuple[int, int]] = []
        for key, val in config.items():
            if not isinstance(key, str) or not key.startswith("NonFever"):
                continue
            try:
                idx = int(key.replace("NonFever", "").strip()) - 1
            except Exception:
                continue
            try:
                cnt = int(val or 0)
            except Exception:
                cnt = 0
            pairs.append((idx, max(0, cnt)))
        if not pairs:
            return ()
        pairs.sort(key=lambda x: x[0])
        max_idx = pairs[-1][0]
        if max_idx < 0:
            return ()
        out = [0] * (max_idx + 1)
        for idx, cnt in pairs:
            if 0 <= idx < len(out):
                out[idx] = int(cnt)
        if sum(out) <= 0:
            return ()
        return tuple(int(v) for v in out)

    def _maybe_backfill_fg_hitsim_deltas(force_obj: dict, *, stats_obj: dict) -> dict:
        if not (calc_song is not None and ref_arrays is not None and isinstance(force_obj, dict) and isinstance(stats_obj, dict)):
            return force_obj

        meta0 = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
        apply_to = str(meta0.get("HumanHitSimApplyTo", "") or "").strip().upper()
        if not (meta0.get("HumanHitSimApplied") and apply_to == "ALL"):
            return force_obj

        fg_meta = force_obj.get("ForceGreats") or {}
        if not isinstance(fg_meta, dict):
            return force_obj

        existing_deltas = fg_meta.get("hitsim_offset_deltas_ms")
        if isinstance(existing_deltas, (list, tuple)) and existing_deltas:
            if "hitsim_offset_delta_ms" in fg_meta:
                fg_meta_out = dict(fg_meta)
                fg_meta_out.pop("hitsim_offset_delta_ms", None)
                out0 = dict(force_obj)
                out0["ForceGreats"] = fg_meta_out
                return out0
            return force_obj
        if fg_meta.get("hitsim_offset_deltas_ms") is not None:
            return force_obj

        forced_counts = _nonfever_counts_from_config_for_hitsim(fg_meta.get("config") or {})
        if not forced_counts:
            return force_obj

        try:
            ff_stat = int(stats_obj.get("Fever Fill Rate", 0) or 0)
        except Exception:
            ff_stat = 0
        try:
            ft_stat = int(stats_obj.get("Fever Time", 0) or 0)
        except Exception:
            ft_stat = 0

        cache_key = (int(ff_stat), int(ft_stat), tuple(int(x) for x in forced_counts))
        deltas_t = _hitsim_fg_deltas_cache.get(cache_key)
        if deltas_t is None:
            try:
                from ...solver.scoring.force_greats import summarize_hitsim_offset_deltas_ms_for_fg_variant

                computed = summarize_hitsim_offset_deltas_ms_for_fg_variant(
                    calc_song,
                    {"ForceGreats": fg_meta, "Stats": stats_obj},
                    ref_arrays,
                )
            except Exception:
                computed = None
            if computed:
                try:
                    deltas_t = tuple(int(x) for x in computed)
                except Exception:
                    deltas_t = None
                if deltas_t:
                    _hitsim_fg_deltas_cache[cache_key] = deltas_t

        if not deltas_t:
            return force_obj

        fg_meta_out = dict(fg_meta)
        if fg_meta_out.get("hitsim_offset_deltas_ms") is None:
            fg_meta_out["hitsim_offset_deltas_ms"] = list(deltas_t)
        fg_meta_out.pop("hitsim_offset_delta_ms", None)

        out = dict(force_obj)
        out["ForceGreats"] = fg_meta_out

        # Keep the nested details shape consistent when present (some consumers inspect it).
        nested0 = out.get("details")
        if isinstance(nested0, dict):
            nested_out = dict(nested0)
            nested_out.pop("hitsim_offset_delta_ms", None)
            nested_fg0 = nested_out.get("ForceGreats")
            if isinstance(nested_fg0, dict):
                nested_fg_out = dict(nested_fg0)
                if nested_fg_out.get("hitsim_offset_deltas_ms") is None:
                    nested_fg_out["hitsim_offset_deltas_ms"] = list(deltas_t)
                nested_fg_out.pop("hitsim_offset_delta_ms", None)
                nested_out["ForceGreats"] = nested_fg_out
            out["details"] = nested_out

        return out

    def _loadout_hash(gear_items, mini_items) -> str:
        try:
            from ...data.database import get_loadout_hash

            return str(get_loadout_hash(gear_items, mini_items))
        except Exception:
            # Fallback: best-effort stable-ish signature
            return str((tuple(gear_items or []), tuple(mini_items or [])))

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
        # Strip legacy HitSim scalar fields (we persist the per-window list only).
        details_with_meta.pop("hitsim_offset_delta_ms", None)
        fg_meta0 = details_with_meta.get("ForceGreats")
        if isinstance(fg_meta0, dict) and "hitsim_offset_delta_ms" in fg_meta0:
            fg_meta1 = dict(fg_meta0)
            fg_meta1.pop("hitsim_offset_delta_ms", None)
            details_with_meta["ForceGreats"] = fg_meta1

        force_out = _normalize_force_payload(force_obj) if isinstance(force_obj, dict) else force_obj

        persist_entries.append(
            {
                "score": score_val or 0,
                "fg_score": fg_score_val or 0,
                "gear": names_list(gear_items),
                "minis": names_list(mini_items),
                "details": details_with_meta,
                "force": force_out,
            }
        )

    # Top 1 (base) - store with its OWN fg_score and force data (if available)
    # This ensures the force_details_json matches the loadout gear
    top1_details = db_payload.get("details", {})
    if isinstance(top1_details, dict):
        top1_details = _maybe_backfill_base_hitsim_deltas(top1_details)
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
        if isinstance(best_fg_details, dict):
            best_fg_details = _maybe_backfill_base_hitsim_deltas(best_fg_details)

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

            # If we're in a context that has the full HitSim inputs, ensure the base delta is present
            # even on this GA-candidates fallback path (used by native in-flight deferred posts).
            if (
                calc_song is not None
                and ref_arrays is not None
                and isinstance(eval_details, dict)
                and eval_details.get("hitsim_offset_deltas_ms") is None
            ):
                meta0 = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
                apply_to = str(meta0.get("HumanHitSimApplyTo", "") or "").strip().upper()
                if not (meta0.get("HumanHitSimApplied") and apply_to == "ALL"):
                    stats_obj = None
                else:
                    stats_obj = eval_details.get("Stats")
                if isinstance(stats_obj, dict) and stats_obj:
                    try:
                        ff_stat = int(stats_obj.get("Fever Fill Rate", 0) or 0)
                    except Exception:
                        ff_stat = 0
                    try:
                        ft_stat = int(stats_obj.get("Fever Time", 0) or 0)
                    except Exception:
                        ft_stat = 0

                    cache_key = (int(ff_stat), int(ft_stat))
                    deltas_t = _hitsim_base_deltas_cache.get(cache_key)
                    if deltas_t is None:
                        try:
                            from ...solver.scoring.force_greats import summarize_hitsim_offset_deltas_ms_for_base

                            computed = summarize_hitsim_offset_deltas_ms_for_base(
                                calc_song, {"Stats": stats_obj}, ref_arrays
                            )
                        except Exception:
                            computed = None
                        if computed:
                            try:
                                deltas_t = tuple(int(x) for x in computed)
                            except Exception:
                                deltas_t = None
                            if deltas_t:
                                _hitsim_base_deltas_cache[cache_key] = deltas_t

                    if deltas_t:
                        eval_details = dict(eval_details)
                        eval_details.pop("hitsim_offset_delta_ms", None)
                        eval_details["hitsim_offset_deltas_ms"] = list(deltas_t)

            _append_entry(
                eval_score,
                eval_gear,
                eval_minis,
                eval_details,
                0,  # No FG score available in this fallback path
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

            # Frontend expects this present for *all* retained base rows (top51), not just top1.
            # Compute lazily for the final retained set so we don't do extra work for pruned rows.
            if (
                calc_song is not None
                and ref_arrays is not None
                and isinstance(details_obj, dict)
                and details_obj.get("hitsim_offset_deltas_ms") is None
            ):
                meta0 = (calc_song.get("metadata") or {}) if isinstance(calc_song, dict) else {}
                apply_to = str(meta0.get("HumanHitSimApplyTo", "") or "").strip().upper()
                if not (meta0.get("HumanHitSimApplied") and apply_to == "ALL"):
                    stats_obj = None
                else:
                    stats_obj = details_obj.get("Stats")
                if isinstance(stats_obj, dict) and stats_obj:
                    try:
                        ff_stat = int(stats_obj.get("Fever Fill Rate", 0) or 0)
                    except Exception:
                        ff_stat = 0
                    try:
                        ft_stat = int(stats_obj.get("Fever Time", 0) or 0)
                    except Exception:
                        ft_stat = 0

                    cache_key = (int(ff_stat), int(ft_stat))
                    deltas_t = _hitsim_base_deltas_cache.get(cache_key)
                    if deltas_t is None:
                        try:
                            from ...solver.scoring.force_greats import summarize_hitsim_offset_deltas_ms_for_base

                            computed = summarize_hitsim_offset_deltas_ms_for_base(
                                calc_song, {"Stats": stats_obj}, ref_arrays
                            )
                        except Exception:
                            computed = None
                        if computed:
                            try:
                                deltas_t = tuple(int(x) for x in computed)
                            except Exception:
                                deltas_t = None
                            if deltas_t:
                                _hitsim_base_deltas_cache[cache_key] = deltas_t

                    if deltas_t:
                        details_obj = dict(details_obj)
                        details_obj.pop("hitsim_offset_delta_ms", None)
                        details_obj["hitsim_offset_deltas_ms"] = list(deltas_t)

            # Ensure FG per-window deltas are present for all retained rows that have a valid FG payload.
            # Store them on the persisted `force` payload (used by FG leaderboard rows + frontend).
            if (
                calc_song is not None
                and ref_arrays is not None
                and isinstance(details_obj, dict)
                and isinstance(force_obj, dict)
                and fg_score_to_save
                and int(fg_score_to_save or 0) > int(_base_score(entry) or 0)
            ):
                stats_obj = details_obj.get("Stats")
                if isinstance(stats_obj, dict) and stats_obj:
                    force_obj = _maybe_backfill_fg_hitsim_deltas(force_obj, stats_obj=stats_obj)

            gear_names, mini_names = materialize_entry_names(entry, mutate=True)
            _append_entry(
                entry.get("base_score") or entry.get("score", 0),
                gear_names,
                mini_names,
                details_obj,
                fg_score_to_save,
                force_obj,
            )

    return persist_entries
