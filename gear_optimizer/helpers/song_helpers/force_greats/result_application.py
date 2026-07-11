from __future__ import annotations

from typing import Any


def read_visible_stats(
    payload: Any,
    *,
    mutate_payload: bool = False,
) -> dict[str, Any]:
    """Return the post-gem *visible* stats for an FG result / persist / serve payload.

    CONTRACT — read before touching gem math here:
      This reader receives FG *result / persist / serve* payloads, in which the visible
      stat row is already post-gem. Two shapes occur:

        * ``Stats`` present  -> it IS the authoritative post-gem visible row; return it.
        * only ``BaseStats`` -> in these payloads ``BaseStats`` is itself the post-gem
          visible row (the search bakes the GemCounts / FT / FF allocation in exactly
          once via ``apply_gems_to_base_stats`` — see ``response_frontier.py``:
          "post-gem stats span all 10 keys"). Return it verbatim.

      Gems must NOT be re-applied here. Re-applying them counts every gem twice — the
      2026-07-11 Canon-in-D FG regression (Vibe 1018 -> 1432, FF 96 -> 192, ...) where
      the score stayed correct but the persisted stat row was doubled. Genuine gem
      *application* (a pre-gem base -> post-gem stats) is the separate
      ``apply_gems_to_base_stats`` helper, used only inside the search — where, unlike
      here, ``BaseStats`` in the candidate ``eval_data`` really is the pre-gem base.

    This is the single canonical reader for pipeline, inflight orchestration, and DB
    persistence. The selected element is intentionally not a parameter — the allocation
    is already baked into the stat row, so it is never needed here.
    """
    if not isinstance(payload, dict):
        return {}

    # An explicit Stats row is the authoritative post-gem visible stats.
    existing = payload.get("Stats")
    if isinstance(existing, dict) and existing:
        return existing if mutate_payload else dict(existing)

    # Otherwise BaseStats is itself the post-gem visible row — surfaced verbatim, never
    # re-gemmed.
    base_stats = payload.get("BaseStats")
    if isinstance(base_stats, dict) and base_stats:
        if mutate_payload:
            payload["Stats"] = dict(base_stats)
            return payload["Stats"]
        return dict(base_stats)

    return {}
