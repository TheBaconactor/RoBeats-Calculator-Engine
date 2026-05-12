# Native Deferred Post GA Candidate Compaction

Date: 2026-05-12

## Context

`native_inflight_result_events.py` built deferred-post payloads and also owned the GA-candidate row compaction/materialization loop.

## Broken invariant

Deferred-post payload assembly and GA candidate compaction are separate result-finalization responsibilities. Candidate row compaction should be independently testable and reusable.

## First violation point

`build_deferred_post_payload()` selected effective GA candidates, materialized gear/mini names, and shaped compact rows inline.

## Fix

Added `gear_optimizer.solver.native_inflight_post_candidates.build_ga_candidates_for_post()`.

`build_deferred_post_payload()` now delegates GA candidate row compaction to that helper while preserving the existing selector/materializer monkeypatch seam used by regression tests.

## Tests

Added `tests/test_native_inflight_post_candidates.py` for compact row shape, selector/materializer forwarding, non-dict candidate filtering, and default `BaseScore` behavior.

Verification:

```powershell
python -m ruff check gear_optimizer/solver/native_inflight_result_events.py gear_optimizer/solver/native_inflight_post_candidates.py tests/test_native_inflight_post_candidates.py tests/test_native_inflight_deferred_post_payload.py
python -m pytest tests/test_native_inflight_post_candidates.py tests/test_native_inflight_deferred_post_payload.py tests/test_post_processor_async_db_authority.py -q
```

## Complexity impact

This removes GA candidate compaction logic from the deferred-post payload assembler and adds a focused helper with direct tests. The deferred-post payload contract and native FG-inside-GA behavior are unchanged.
