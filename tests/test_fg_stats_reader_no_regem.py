"""Anti-regression guard for the FG visible-stats reader.

The reader must NEVER re-apply gems: in FG result/persist/serve payloads the stat row
is already post-gem. Re-applying gems double-counts (2026-07-11 Canon-in-D regression:
Vibe 1018 -> 1432); returning a pre-gem row verbatim would halve it. These tests pin the
reader directly (it previously had no direct unit test) and pin the storage boundary that
guarantees the reader's "BaseStats is post-gem" contract holds on disk.
"""

from __future__ import annotations

from gear_optimizer.data.database.force_normalize import _compact_force_details_for_storage
from gear_optimizer.helpers.song_helpers.force_greats.result_application import (
    read_visible_stats,
)
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

# A realistic post-gem visible row + its solved allocation (Canon In D T5 Vibe shape).
_POST_GEM = {
    "Perfect Points": 85,
    "Combo Multiplier": 81,
    "Fever Multiplier": 72,
    "Fever Fill Rate": 96,
    "Fever Time": 13,
    "Chill": 65,
    "Flow": 0,
    "Rush": 94,
    "Beat": 49,
    "Vibe": 1018,
}
_SEL = "Vibe"
_FT, _FF, _G_PP, _G_CM, _G_FM, _G_OV = 2, 32, 0, 0, 3, 53


def _doubled(row: dict) -> dict:
    """What a wrongful re-application of the gems on top of `row` would produce."""
    return apply_gems_to_base_stats(row, _SEL, _FT, _FF, _G_PP, _G_CM, _G_FM, _G_OV)


def test_reader_returns_base_stats_verbatim_and_never_re_gems():
    # BaseStats-only, nonzero gems: the reader must return BaseStats verbatim and must
    # NOT equal the re-gemmed row (that would be the double-count).
    payload = {
        "BaseStats": dict(_POST_GEM),
        "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": _G_FM, "Element": _G_OV},
        "FT": _FT,
        "FF": _FF,
        "Selected Element": _SEL,
    }
    out = read_visible_stats(payload)
    assert out == _POST_GEM
    doubled = _doubled(_POST_GEM)
    assert doubled != _POST_GEM  # sanity: the gems would change the row if re-applied
    assert out != doubled


def test_reader_prefers_explicit_post_gem_stats_over_divergent_base_stats():
    # Stale-schema shape: pre-gem BaseStats + explicit post-gem Stats. The reader must
    # return the post-gem Stats (not the pre-gem BaseStats, not a re-gem of either).
    pre_gem = {k: (v // 2 if v else v) for k, v in _POST_GEM.items()}
    payload = {
        "BaseStats": dict(pre_gem),
        "Stats": dict(_POST_GEM),
        "GemCounts": {"Fever Multiplier": _G_FM, "Element": _G_OV},
        "FT": _FT,
        "FF": _FF,
        "Selected Element": _SEL,
    }
    out = read_visible_stats(payload)
    assert out == _POST_GEM
    assert out != pre_gem


def test_reader_mutate_payload_writes_post_gem_row_not_doubled():
    payload = {
        "BaseStats": dict(_POST_GEM),
        "GemCounts": {"Fever Multiplier": _G_FM, "Element": _G_OV},
        "FT": _FT,
        "FF": _FF,
        "Selected Element": _SEL,
    }
    out = read_visible_stats(payload, mutate_payload=True)
    assert out == _POST_GEM
    assert payload["Stats"] == _POST_GEM
    assert payload["Stats"] != _doubled(_POST_GEM)


def test_storage_promotes_post_gem_stats_to_base_stats_then_reader_is_correct():
    # The GA/reducer producer emits a PRE-gem BaseStats + post-gem Stats. Compaction
    # must promote the post-gem row to BaseStats before dropping Stats, so the stored,
    # Stats-less block reads back to the post-gem row (not the halved pre-gem one).
    pre_gem = {k: (v // 2 if v else v) for k, v in _POST_GEM.items()}
    producer_payload = {
        "BaseStats": dict(pre_gem),   # pre-gem base (reducer)
        "Stats": dict(_POST_GEM),     # authoritative post-gem visible row
        "GemCounts": {"Fever Multiplier": _G_FM, "Element": _G_OV},
        "FT": _FT,
        "FF": _FF,
        "Selected Element": _SEL,
    }
    stored = _compact_force_details_for_storage(producer_payload)
    assert "Stats" not in stored                 # Stats dropped (compacted)
    assert stored["BaseStats"] == _POST_GEM       # but BaseStats promoted to post-gem row
    assert stored["BaseStats"] != pre_gem
    # Read-back through the canonical reader yields the post-gem row, never the pre-gem
    # (undercount) nor a re-gem (double-count).
    read_back = read_visible_stats(stored)
    assert read_back == _POST_GEM
    assert read_back != pre_gem
    assert read_back != _doubled(_POST_GEM)
