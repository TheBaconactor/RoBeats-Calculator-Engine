"""
Song Helpers - Persistence API.

Centralized persistence canonicalization lives in `persistence_canon.py`.
This module stays as the stable import surface for pipeline and tests.
"""

from __future__ import annotations

from .persistence_canon import ReplayContext, canonicalize_and_assemble
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

    Replay context is required so persisted rows are authoritative and replayable.
    Tests/tooling that intentionally need shape-only assembly should call
    `persistence_canon.assemble_without_replay` explicitly.
    """
    if not (isinstance(calc_song, dict) and calc_song and isinstance(ref_arrays, dict) and ref_arrays):
        raise ValueError("build_persistence_entries requires calc_song and ref_arrays for authoritative replay.")

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
