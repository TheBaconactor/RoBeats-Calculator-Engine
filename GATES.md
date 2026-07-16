# GPU byte-gates pending for opt-2 (numba-fy `validate_force_greats_physical_replay`)

Worktree: `C:/wtopt2`  · branch: `perf/opt-2-physical-replay-numba` · base: `2b9616e8`
Fresh numba cache used for CPU verification: `C:/wtopt2/bin/numba_cache_wtopt2`

## What changed (scope)
- Only `gear_optimizer/solver/fg_response_scoring/physical_replay.py` — the FG wrapper
  `validate_force_greats_physical_replay` body loops (`:267-279` per-note judgment + event-time
  accumulation, `:281-298` input-order + lane-cursor scan, `:300` `_event_time_fever_mask`) were
  folded into one nogil numba pass `_force_greats_replay_kernel` (+ `_judgment_code` twin).
- The graph builder (`force_greats_note_graph` / `reconcile_force_greats_note_graph` in
  `note_graph.py`) is untouched — it stays the producer. No fingerprinted producer source was
  edited, so **no cache fingerprint rotates**.
- The function is a **read-only validation guard** on the persist path: it either returns the same
  `FgPhysicalReplay` (event_order / fever_mask / judgments) or raises the same `ValueError`. It does
  **not** change any persisted trace bytes or any score, so the persisted-loadout byte-oracle is
  expected trivially unchanged; the gate below confirms the guard's pass/raise decision and the
  score sums on the real production corpus.

## CPU gates already run (green — see report)
- `ruff check` on `physical_replay.py`, `tests/test_fg_physical_replay_numba.py`,
  `tools/dev/bench_fg_physical_replay.py` → clean.
- `NUMBA_CACHE_DIR=C:/wtopt2/bin/numba_cache_wtopt2 python -m pytest -m "not gpu" -p no:cacheprovider`
  `tests/test_fg_note_graph.py tests/test_loadout_oracle_replay.py tests/test_fg_physical_replay_numba.py`
  → 73 passed, 1 skipped.
- Kernel proven **bit-exact** vs a Python golden reference built from the still-present original
  helpers (`_judgment_at`, `_event_time_fever_mask`) over 900 randomized cases + all 8 error paths,
  plus 5 real-data traces (Mopemope/Alice/Light-it-up) asserting exact event_order/judgments/fever,
  plus 8 wrapper fail-loud message-parity tests.

## GPU / full-corpus gates STILL REQUIRED before ship (do NOT claim exactness until green)
Run on the RX 7900 XTX box when the GPU is free, on an **isolated cache root**, from `C:/wtopt2`
with `NUMBA_CACHE_DIR=C:/wtopt2/bin/numba_cache_wtopt2` exported (recompile dependent tool modules
first — numba `cache=True` does not invalidate cross-file callers).

1. **132-trace persisted-loadout byte-oracle** (the fg_mat_bench replay harness over the 23 real
   charts) — must be SHA256-equal at every step to the pinned baseline:
   `75bd33a3f1865736bd25d88606b3269675c598ee9488ade0533f2bf8c84b55d2`.
   Abort on any witness/score byte drift. (This exercises the guard's decision on the real corpus;
   because no persisted bytes change, expect step-for-step equality.)

2. **Seeded q24 A/B full GPU solve** — `main` @ `2b9616e8` vs this branch, `GA_SEED=42`, isolated
   cache roots, interleaved:
   - expected `sum(best_score)   = 1076272869`
   - expected `sum(best_fg_score) = 1023982456`
   Both leaderboards must be bit-identical (base and FG separate). Any digit drift = abort.

3. Optional: `pytest -m gpu` FG suites unchanged vs `main`'s known failure set (judge by
   failure-SET diff, not absolute count — CPU baseline has a known red set).

## Honest note on payoff (see report)
The named block is genuinely ~3x lighter on the GIL (Alice n=1989: body 2.39 ms → 0.81 ms/call, of
which only 0.014 ms is the nogil kernel), but the graph build inside the same function
(`note_graph.py`, correctly off-limits) is ~10.15 ms/call and dominates — so full-call GIL-held time
drops ~13% (12.54 → 10.95 ms), not 3x. The win is real and on-target for the FG-worker/post-processor
GIL, just bounded by the untouchable producer build.
