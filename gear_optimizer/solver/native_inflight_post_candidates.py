from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.fg_candidate_selector import select_effective_unique_ga_candidates
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_candidate_names


def build_ga_candidates_for_post(
    candidates: list[dict] | None,
    *,
    registry: Any,
    minis_by_name: dict | None,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    limit: int = LOADOUTS_PER_SONG_LIMIT,
    selector: Callable[..., list[dict]] = select_effective_unique_ga_candidates,
    materializer: Callable[..., tuple[list[str], list[str]]] = materialize_candidate_names,
) -> list[dict[str, Any]]:
    selected = selector(
        list(candidates or []),
        limit=int(limit),
        registry=registry,
        minis_by_name=minis_by_name,
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
    )
    out: list[dict[str, Any]] = []
    for cand in selected or []:
        if not isinstance(cand, dict):
            continue
        data0 = cand.get("Data") or {}
        candidate_for_post = dict(cand)
        candidate_for_post["Data"] = dict(data0) if isinstance(data0, dict) else {}
        gear_names, mini_names = materializer(
            candidate_for_post,
            registry=registry,
            mutate=False,
        )
        out.append(
            {
                "Score": candidate_for_post.get("Score", 0),
                "BaseScore": candidate_for_post.get("BaseScore", candidate_for_post.get("Score", 0)),
                "Gear": list(gear_names),
                "Minis": list(mini_names),
                "Data": candidate_for_post.get("Data") or {},
                "_fg_priority": candidate_for_post.get("_fg_priority", 0),
                "loadout_hash": candidate_for_post.get("loadout_hash"),
            }
        )
    return out
