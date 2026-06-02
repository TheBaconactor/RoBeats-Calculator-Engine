from __future__ import annotations

from ...core.utils import safe_int
from .fg_config import has_valid_fg_config


RECORD_UPDATE_SCORE_EPSILON = 2


def entry_base_score(entry: dict) -> int:
    if not isinstance(entry, dict):
        return 0
    return safe_int(entry.get("base_score") or entry.get("score", 0), 0)


def evaluate_record_update(best_data, prev_record, fg_variants, db_best_fg_score=None) -> dict:
    """
    Evaluate whether the current run beats the prior overall song record.

    Base and FG leaderboards remain separate persistence surfaces, but user-facing
    NEW/win counters should only advance when the run beats the best set overall
    for the song: max(base score, FG score).
    """
    score = 0
    if isinstance(best_data, dict):
        score = safe_int(best_data.get("BaseScore") or best_data.get("Score", 0), 0)

    prev_score = None
    if isinstance(prev_record, dict):
        prev_score_raw = prev_record.get("score")
        if prev_score_raw is not None:
            prev_score = safe_int(prev_score_raw, 0)

    is_first = prev_record is None
    score_improvement = int(score) - int(prev_score or 0)
    is_better = (prev_score is None) or (score_improvement > RECORD_UPDATE_SCORE_EPSILON)

    best_fg_score_run = 0
    for fg_entry in fg_variants or []:
        if not isinstance(fg_entry, dict):
            continue
        if not has_valid_fg_config(fg_entry):
            continue
        base_score_i = entry_base_score(fg_entry)
        fg_score_i = safe_int(fg_entry.get("fg_score", 0), 0)
        if fg_score_i <= base_score_i:
            continue
        if fg_score_i > best_fg_score_run:
            best_fg_score_run = fg_score_i

    prev_fg_score = (
        db_best_fg_score if db_best_fg_score is not None else (prev_record.get("fg_score") if prev_record else 0)
    )
    prev_fg_score = safe_int(prev_fg_score, 0)
    fg_improvement = int(best_fg_score_run) - int(prev_fg_score or 0)
    is_fg_better = fg_improvement > RECORD_UPDATE_SCORE_EPSILON
    prev_overall_score = max(int(prev_score or 0), int(prev_fg_score or 0))
    best_overall_score_run = max(int(score or 0), int(best_fg_score_run or 0))
    overall_improvement = int(best_overall_score_run) - int(prev_overall_score or 0)
    is_overall_better = is_first or (overall_improvement > RECORD_UPDATE_SCORE_EPSILON)

    return {
        "record_update": bool(is_overall_better),
        "is_first": bool(is_first),
        "is_better": bool(is_better),
        "is_fg_better": bool(is_fg_better),
        "is_overall_better": bool(is_overall_better),
        "score": int(score),
        "prev_score": prev_score,
        "best_fg_score_run": int(best_fg_score_run),
        "prev_fg_score": int(prev_fg_score),
        "best_overall_score_run": int(best_overall_score_run),
        "prev_overall_score": int(prev_overall_score),
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
            score = safe_int(best_data.get("BaseScore") or best_data.get("Score", 0), 0)
        best_fg_score_run = 0
        if fg_only:
            for fg_entry in fg_variants or []:
                if not isinstance(fg_entry, dict):
                    continue
                if not has_valid_fg_config(fg_entry):
                    continue
                base_score_i = entry_base_score(fg_entry)
                fg_score_i = safe_int(fg_entry.get("fg_score", 0), 0)
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
            "is_overall_better": False,
            "score": int(score),
            "prev_score": None,
            "best_fg_score_run": int(best_fg_score_run),
            "prev_fg_score": int(safe_int(prev_fg_score, 0)),
            "best_overall_score_run": int(max(int(score or 0), int(best_fg_score_run or 0))),
            "prev_overall_score": int(safe_int(prev_fg_score, 0)),
        }

    record_info = evaluate_record_update(best_data, prev_record, fg_variants, db_best_fg_score=db_best_fg_score)
    if not isinstance(record_info, dict):
        return None
    if fg_only:
        record_info = dict(record_info)
        record_info["record_update"] = bool(record_info.get("is_overall_better"))
    return record_info
