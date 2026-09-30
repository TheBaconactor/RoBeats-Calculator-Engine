from dataclasses import replace

from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.store import boards as store_boards
from gear_optimizer.store.boards import boards
from tests.store_support import candidate, fg_row, meta_row

NOW = 500


def merge(rows, candidates, *, now):
    """The merge with entry numbers continuing after the given rows' (as one song's database would)."""
    next_meta = 1 + max((r.loadout.meta.seq for r in rows if r.loadout.meta), default=0)
    next_fg = 1 + max((r.loadout.fg.seq for r in rows if r.loadout.fg), default=0)
    return store_boards.merge(rows, candidates, now=now, next_seq=(next_meta, next_fg))


def _by_hash(rows):
    return {r.loadout.loadout_hash: r.loadout for r in rows}


def test_new_loadouts_enter_the_boards_in_candidate_order():
    rows = merge([meta_row("old", 100, seq=7)], [candidate("a", 90), candidate("b", 95, 99)], now=NOW)
    got = _by_hash(rows)
    assert (got["a"].meta.seq, got["b"].meta.seq, got["b"].fg.seq) == (8, 9, 1)
    assert got["a"].meta.updated == got["b"].meta.updated == got["b"].fg.updated == NOW
    assert got["old"].meta.updated == 100  # untouched


def test_a_higher_score_replaces_the_meta_result_and_keeps_its_entry():
    rows = merge([meta_row("a", 100, seq=3)], [candidate("a", 120)], now=NOW)
    (got,) = rows
    assert (got.loadout.score, got.loadout.meta.seq, got.loadout.meta.updated) == (120, 3, NOW)
    assert got.meta_trace == candidate("a", 120).row.meta_trace


def test_a_lower_score_only_refreshes_the_meta_result():
    stored = meta_row("a", 100, seq=3)
    (got,) = merge([stored], [candidate("a", 90)], now=NOW)
    assert got.loadout.score == 100
    assert got.loadout.meta == replace(stored.loadout.meta, updated=NOW)


def test_an_equal_or_higher_fg_score_replaces_the_fg_result():
    (got,) = merge([fg_row("a", 100, 150, seq=4)], [candidate("a", 100, 150)], now=NOW)
    assert (got.loadout.fg_score, got.loadout.fg.seq, got.loadout.fg.updated) == (150, 4, NOW)
    (got,) = merge([fg_row("a", 100, 150, seq=4)], [candidate("a", 100, 140)], now=NOW)
    assert (got.loadout.fg_score, got.loadout.fg.updated) == (150, NOW)


def test_a_deferred_fg_update_refreshes_a_stored_meta_result():
    (got,) = merge([meta_row("a", 100, seq=2)], [candidate("a", 100, 130, deferred=True)], now=NOW)
    assert (got.loadout.score, got.loadout.meta.seq, got.loadout.meta.updated) == (100, 2, NOW)
    assert (got.loadout.fg_score, got.loadout.fg.seq) == (130, 1)


def test_a_deferred_fg_update_never_adds_a_meta_result():
    # Version 18 stored the update's FG allocation as a meta row here (the Diva/GHOUL base rows).
    (got,) = merge([], [candidate("a", 100, 130, deferred=True)], now=NOW)
    assert got.loadout.meta is None and got.meta_trace is None
    assert (got.loadout.score, got.loadout.fg_score) == (100, 130)


def test_fg_results_compare_with_the_loadouts_single_base_score():
    # The FG result beats the base score it was paired with (95) but not the loadout's best base score (120).
    (got,) = merge([meta_row("a", 120)], [candidate("a", 95, 110)], now=NOW)
    assert got.loadout.fg is None and got.loadout.score == 120
    # An FG board entry shows the loadout's base score, not its paired one.
    (got,) = merge([fg_row("a", 100, 150, meta=False)], [candidate("a", 90)], now=NOW)
    assert (got.loadout.score, got.loadout.fg_score, got.loadout.meta.seq) == (90, 150, 1)


def test_boards_keep_the_best_scores_and_the_earliest_entries_among_equal_scores():
    stored = [meta_row(f"m{i:02}", 1000 - i, seq=i + 1) for i in range(LOADOUTS_PER_SONG_LIMIT - 1)]
    stored.append(meta_row("tie-early", 500, seq=100))
    rows = merge(stored, [candidate("tie-late", 500), candidate("low", 400)], now=NOW)
    meta, _ = boards(rows)
    assert len(meta) == LOADOUTS_PER_SONG_LIMIT
    names = {x.loadout_hash for x in meta}
    assert "tie-early" in names and "tie-late" not in names and "low" not in names


def test_a_loadout_leaving_the_fg_board_keeps_an_fg_score_no_higher_than_its_score():
    stored = [fg_row(f"f{i:02}", 100, 200 + i, seq=i + 1) for i in range(LOADOUTS_PER_SONG_LIMIT)]
    rows = merge(stored, [candidate("new", 100, 1000)], now=NOW)
    got = _by_hash(rows)
    assert got["f00"].fg is None and got["f00"].fg_score == 100 and got["f00"].meta is not None
    assert got["new"].fg.seq == LOADOUTS_PER_SONG_LIMIT + 1


def test_a_loadout_on_neither_board_is_dropped():
    stored = [fg_row(f"f{i:02}", 100, 200 + i, meta=False, seq=i + 1) for i in range(LOADOUTS_PER_SONG_LIMIT)]
    rows = merge(stored, [candidate("new", 100, 1000, deferred=True)], now=NOW)
    assert "f00" not in _by_hash(rows) and len(rows) == LOADOUTS_PER_SONG_LIMIT


def test_stale_fg_scores_settle_on_the_next_write_and_missing_ones_stay_missing():
    rows = merge([meta_row("stale", 100, fg_score=150), meta_row("none", 90)], [candidate("x", 50)], now=NOW)
    got = _by_hash(rows)
    assert (got["stale"].fg_score, got["none"].fg_score, got["x"].fg_score) == (100, None, None)


def test_meta_board_order_breaks_ties_by_fg_score_then_newest_then_earliest():
    rows = [
        meta_row("no-fg", 100, updated=9, seq=1),
        meta_row("fg", 100, fg_score=100, updated=1, seq=2),
        meta_row("newer", 100, updated=10, seq=3),
        meta_row("later-entry", 100, updated=10, seq=4),
    ]
    meta, _ = boards(rows)
    assert [x.loadout_hash for x in meta] == ["fg", "newer", "later-entry", "no-fg"]
