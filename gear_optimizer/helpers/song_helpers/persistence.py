"""
Song Helpers - Persistence API.

Centralized persistence canonicalization lives in `persistence_canon.py`.
This module stays as the stable import surface for pipeline and tests.
"""

from __future__ import annotations

from .persistence_canon import ReplayContext, assemble_without_replay, canonicalize_and_assemble
from .persistence_payload import (
    build_db_payload as build_db_payload,
    make_build_details_fn as make_build_details_fn,
    normalize_force_payload,
)
from .persistence_records import (
    RECORD_UPDATE_SCORE_EPSILON as RECORD_UPDATE_SCORE_EPSILON,
    evaluate_progress_record_update as evaluate_progress_record_update,
)

_normalize_force_payload = normalize_force_payload


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
    Compatibility wrapper around the centralized canonicalization gateway.

    Production callers should pass replay context (`calc_song`, `ref_arrays`, `cfg_dict`)
    so persisted rows are authoritative and replayable.
    """
    if not (isinstance(calc_song, dict) and calc_song and isinstance(ref_arrays, dict) and ref_arrays):
        return assemble_without_replay(
            db_payload=db_payload if isinstance(db_payload, dict) else {},
            ga_candidates=ga_candidates,
            loadout_entries=loadout_entries,
            build_details_fn=build_details_fn,
        )

    replay_ctx = ReplayContext(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict=dict(cfg_dict) if isinstance(cfg_dict, dict) else {},
    )
    return canonicalize_and_assemble(
        db_payload=db_payload if isinstance(db_payload, dict) else {},
        ga_candidates=ga_candidates,
        loadout_entries=loadout_entries,
        build_details_fn=build_details_fn,
        replay_ctx=replay_ctx,
    )
