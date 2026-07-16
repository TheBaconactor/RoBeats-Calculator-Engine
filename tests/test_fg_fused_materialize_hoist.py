"""Song-invariant hoist for the fused per-candidate FG materialization loop.

The fused GA->FG handoff materializes one solve result per candidate, but the FG
song fingerprint (``extract_fg_song_inputs`` + the frontier geometry it keys) is
invariant across every candidate in a batch -- only the ``(ft_stat, ff_stat)``
suffix varies. These tests lock that:

* the fused builder threads a shared ``song_inputs`` and a per-``(ft_stat, ff_stat)``
  frontier memo instead of rebuilding both per candidate, deduping the frontier
  resolution exactly like the batch materialize sibling, while staying byte-identical
  to the standalone per-call path when the hoists are omitted;
* ``FgResponseScoringService.materialize_from_owner_score_map`` shares one
  ``song_inputs`` + one frontier memo per prepared batch (fresh per batch);
* the reducer payload builder accepts the hoisted ``song_inputs`` and produces a
  byte-identical payload to the self-extracting path.
"""

from types import SimpleNamespace

import numpy as np
import pytest

import gear_optimizer.solver.taichi_gem.force_greats.response_frontier as rf


_SONG_INPUTS = object()


def _score_row(ft_stat: int, ff_stat: int) -> rf.FgFusedOwnerScoreRow:
    return rf.FgFusedOwnerScoreRow(
        ft=1,
        ff=2,
        ft_stat=int(ft_stat),
        ff_stat=int(ff_stat),
        inner_row=tuple(0 for _ in range(11)),
        surface=(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    )


def _patch_builder_primitives(monkeypatch):
    """Replace the builder's three song-level primitives with recording stubs."""
    calls = {"resolver": 0, "extract": 0}
    frontier_by_key: dict[tuple[int, int], object] = {}
    captured: list[dict[str, object]] = []

    def _fake_resolver(calc_song, ref_arrays, scoring_bundle, *, ft_stat, ff_stat):
        calls["resolver"] += 1
        # One distinct frontier object per stat key: the resolver is a pure function of
        # the (normalized) stat key over a fixed song, so identity proves the memo returns
        # the object the resolver would have recomputed.
        return frontier_by_key.setdefault((int(ft_stat), int(ff_stat)), object())

    def _fake_extract(calc_song):
        calls["extract"] += 1
        return _SONG_INPUTS

    def _fake_solve_row(*, started, base_stats, selected_color, song_inputs, pair, row, surface, include_forced_counts):
        captured.append({"song_inputs": song_inputs, "frontier": pair[2], "surface": surface})
        return ("solve", id(song_inputs), id(pair[2]))

    monkeypatch.setattr(rf, "frontier_result_from_scoring_bundle_for_stats", _fake_resolver)
    monkeypatch.setattr(rf, "extract_fg_song_inputs", _fake_extract)
    monkeypatch.setattr(rf, "_solve_result_from_row", _fake_solve_row)
    return calls, captured


def _scoring_bundle():
    return SimpleNamespace(
        raw_fill_by_ff=[0.0] * 64,
        real_time_by_ft=[0.0] * 64,
    )


def test_fused_builder_hoists_song_inputs_and_dedups_frontier(monkeypatch):
    calls, captured = _patch_builder_primitives(monkeypatch)
    bundle = _scoring_bundle()

    memo: dict[tuple[int, int], object] = {}
    # Two candidates share stat key (3, 4); one candidate uses a different key (5, 6).
    for row in (_score_row(3, 4), _score_row(3, 4), _score_row(5, 6)):
        rf.build_fused_owner_solve_result_from_score_row(
            score_row=row,
            base_stats={"Perfect Points": 1},
            selected_color="Rush",
            calc_song={"song_data": {}, "metadata": {}},
            ref_arrays={},
            scoring_bundle=bundle,
            started=0.0,
            include_forced_counts=False,
            song_inputs=_SONG_INPUTS,
            frontier_by_stat_key=memo,
        )

    # song_inputs supplied -> never re-extracted; frontier resolved once per UNIQUE stat key.
    assert calls["extract"] == 0
    assert calls["resolver"] == 2
    assert set(memo) == {(3, 4), (5, 6)}
    # Both (3, 4) candidates received the very same frontier object (deduped via the memo).
    assert captured[0]["frontier"] is captured[1]["frontier"]
    assert captured[2]["frontier"] is not captured[0]["frontier"]
    # The shared song_inputs object is threaded verbatim into every solve.
    assert all(entry["song_inputs"] is _SONG_INPUTS for entry in captured)


def test_fused_builder_default_path_is_byte_identical(monkeypatch):
    calls, captured = _patch_builder_primitives(monkeypatch)
    bundle = _scoring_bundle()

    rows = (_score_row(3, 4), _score_row(3, 4), _score_row(5, 6))

    # Standalone (default) path: no shared song_inputs, no memo.
    for row in rows:
        rf.build_fused_owner_solve_result_from_score_row(
            score_row=row,
            base_stats={"Perfect Points": 1},
            selected_color="Rush",
            calc_song={"song_data": {}, "metadata": {}},
            ref_arrays={},
            scoring_bundle=bundle,
            started=0.0,
            include_forced_counts=False,
        )

    # Standalone path re-extracts and re-resolves per candidate...
    assert calls["extract"] == 3
    assert calls["resolver"] == 3
    default_frontiers = [entry["frontier"] for entry in captured]
    default_song_inputs = [entry["song_inputs"] for entry in captured]

    # ...yet the frontier VALUE resolved for a given stat key is identical to the hoisted
    # path (the resolver is pure in the stat key), and song_inputs is the same pure object.
    assert default_frontiers[0] is default_frontiers[1]  # same (3, 4) frontier
    assert default_frontiers[2] is not default_frontiers[0]
    assert all(si is _SONG_INPUTS for si in default_song_inputs)


def test_materialize_from_owner_score_map_shares_hoists_per_batch(monkeypatch):
    from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod
    import gear_optimizer.solver.scoring.fg_policy as fg_policy

    extract_calls = {"n": 0}

    def _fake_extract(calc_song):
        extract_calls["n"] += 1
        # Fresh object per batch so per-batch scoping is observable by identity.
        return SimpleNamespace(tag=f"song-{extract_calls['n']}")

    monkeypatch.setattr(fg_policy, "extract_fg_song_inputs", _fake_extract)

    seen: list[dict[str, object]] = []

    def _fake_build(*, score_row, base_stats, selected_color, calc_song, ref_arrays, scoring_bundle, started, include_forced_counts, song_inputs, frontier_by_stat_key):
        seen.append(
            {
                "score_row": score_row,
                "song_inputs": song_inputs,
                "memo": frontier_by_stat_key,
            }
        )
        return ("solve", score_row.ft_stat, score_row.ff_stat)

    monkeypatch.setattr(rf, "build_fused_owner_solve_result_from_score_row", _fake_build)

    captured_reducer: dict[str, object] = {}

    def _fake_materialize(plan, prepared_results, *, skyline=False):
        captured_reducer["prepared_results"] = prepared_results
        return prepared_results

    monkeypatch.setattr(reducer_mod.FgResultReducer, "materialize", staticmethod(_fake_materialize))

    def _batch(base_components):
        return SimpleNamespace(
            base_components=np.asarray(base_components, dtype=np.int32),
            selected_color="Rush",
            calc_song={"song_data": {}, "metadata": {}},
            ref_arrays={},
            scoring_bundle=_scoring_bundle(),
            started=0.0,
        )

    # Batch A: two candidates (distinct base_components 7-tuples). Batch B: one candidate.
    bc_a0 = [1, 0, 0, 0, 0, 0, 0]
    bc_a1 = [2, 0, 0, 0, 0, 0, 0]
    bc_b0 = [3, 0, 0, 0, 0, 0, 0]
    prepared_a = SimpleNamespace(
        batch=_batch([bc_a0, bc_a1]),
        rows=[("ck-a0", {"Perfect Points": 1}), ("ck-a1", {"Perfect Points": 2})],
    )
    prepared_b = SimpleNamespace(
        batch=_batch([bc_b0]),
        rows=[("ck-b0", {"Perfect Points": 3})],
    )
    plan = SimpleNamespace(prepared_batches=[prepared_a, prepared_b])

    owner_score_map = {
        (1, 0, 0, 0, 0, 0, 0): _score_row(3, 4),
        (2, 0, 0, 0, 0, 0, 0): _score_row(3, 4),
        (3, 0, 0, 0, 0, 0, 0): _score_row(5, 6),
    }

    out = FgResponseScoringService.materialize_from_owner_score_map(plan, owner_score_map)

    # One extract per batch (not per candidate).
    assert extract_calls["n"] == 2
    assert len(seen) == 3

    # Batch A's two candidates share one song_inputs object and one frontier memo dict.
    assert seen[0]["song_inputs"] is seen[1]["song_inputs"]
    assert seen[0]["memo"] is seen[1]["memo"]

    # Batch B is scoped independently: fresh song_inputs and a fresh memo.
    assert seen[2]["song_inputs"] is not seen[0]["song_inputs"]
    assert seen[2]["memo"] is not seen[0]["memo"]

    # The fused builder outputs are handed to the reducer grouped per prepared batch.
    assert out == [[("solve", 3, 4), ("solve", 3, 4)], [("solve", 5, 6)]]


def _reducer_payload_fixtures(monkeypatch, reducer_mod):
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseFrontierSolveResult,
        FgResponseInnerResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    frontier = FgResponseFrontierResult((surface,), {0: (surface,)}, 9, 3, 17, 5, 8, 4, 11, 0.0)
    result = FgResponseFrontierSolveResult(
        best_score=1234,
        ft=1,
        ff=2,
        gem_counts={"Perfect Points": 0},
        stats={"Fever Time": 12, "Fever Fill Rate": 34},
        surface=surface,
        frontier=frontier,
        inner=FgResponseInnerResult(1234, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        seconds=0.0,
        forced_counts=(),
        raw_fever_fill=1.0,
        real_fever_time=2.0,
    )

    monkeypatch.setattr(
        reducer_mod,
        "reconstruct_force_greats_response_trace",
        lambda **_kwargs: ({"forced_count": 1}, {"forced_count": 0}, {"forced_count": 1}),
    )
    monkeypatch.setattr(reducer_mod, "_assert_trace_hit_time_reachable", lambda *_a, **_k: None)
    monkeypatch.setattr(reducer_mod, "validate_force_greats_physical_replay", lambda **_k: None)
    monkeypatch.setattr(reducer_mod, "score_force_greats_response_surface_exact", lambda *_a, **_k: 1230)
    return result


def test_reducer_payload_accepts_hoisted_song_inputs_byte_identical(monkeypatch):
    from gear_optimizer.solver.fg_response_scoring.reducer import (
        FgTraceMaterializationCache,
        materialize_force_payload_from_response_frontier,
    )
    import gear_optimizer.solver.fg_response_scoring.reducer as reducer_mod

    result = _reducer_payload_fixtures(monkeypatch, reducer_mod)

    song_inputs = SimpleNamespace(
        timestamps=[0.0],
        perfect_candidates=[0.0],
        great_candidates=[0.0],
        perfect_floor=[0.0],
        great_floor=[0.0],
        lanes=[0],
        use_forced_great_timing=True,
    )
    extract_calls = {"n": 0}

    def _fake_extract(calc_song):
        extract_calls["n"] += 1
        return song_inputs

    monkeypatch.setattr(reducer_mod, "extract_fg_song_inputs", _fake_extract)

    calc_song = {"metadata": {}, "song_data": {"timestamps": [1.0], "lanes": [0], "note_types": [1]}}
    common = dict(
        eval_data={"Selected Element": "Rush"},
        base_stats={"Perfect Points": 1},
        paired_base_score=1000,
        selected_element="Rush",
        result=result,
        calc_song=calc_song,
        ref_arrays={},
    )

    payload_default = materialize_force_payload_from_response_frontier(
        **common, trace_cache=FgTraceMaterializationCache()
    )
    assert extract_calls["n"] == 1  # self-extracted once

    payload_hoisted = materialize_force_payload_from_response_frontier(
        **common, trace_cache=FgTraceMaterializationCache(), song_inputs=song_inputs
    )
    assert extract_calls["n"] == 1  # supplied song_inputs -> no re-extraction

    assert payload_hoisted == payload_default


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
