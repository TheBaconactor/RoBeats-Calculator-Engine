# ECLIPSE Implementation Plan

> Archived research snapshot. This proposal is not the current production
> architecture or an active implementation plan.

## Goal
Implement an exact, GPU-first throughput optimization for the GA -> FG pipeline by combining:
1. exact score-signature deduplication for GA evaluation, and
2. an exact interval-DP for FG with proof-backed upper-bound pruning.

## Scope boundary
This plan changes representation and orchestration, not score semantics.
- No approximate score is persisted.
- No FG work is deferred.
- Any candidate dropped before exact FG must be eliminated by a safe upper bound.

## Exact identity
For each staged GA candidate row, pack an exact score signature:

`ExactScoreKey = (song_fingerprint, base_stat_q[10], aux_mask)`

Where:
- `song_fingerprint` is the exact chart identity used by the scorer.
- `base_stat_q[10]` is the fixed-point encoding already used by the production scorer.
- `aux_mask` contains any discrete score-relevant flags not already implied by the 10 stats.

Two candidates with the same `ExactScoreKey` must receive identical exact base score and identical exact FG result.

## Data structures

### 1) DeviceSignatureBuffer
GPU array parallel to the staged candidate rows.

Fields:
- `key_hi`, `key_lo` or equivalent packed exact key bytes
- `run_idx`
- `row_idx`
- `song_slot`
- `slot_ticket`

Invariant:
- key bytes are bit-exact with the production scorer representation.

### 2) UniqueSpanTable
Generated after radix sorting the signature buffer on-device.

Fields per span:
- `span_begin`
- `span_end`
- packed exact key
- one representative `(run_idx, row_idx)`

Invariant:
- all rows in one span have the same exact key.

### 3) ExactEvalTable
Persistent exact-only cache keyed by `(song_fingerprint, exact_key)`.

Payload:
- exact base score
- exact FG score if already solved
- optional exact intermediate payloads needed for winner persistence

Invariant:
- no approximate result may ever be inserted.

### 4) FGFrontierBuffer
Device buffer containing only unique candidates that survive the safe FG upper bound.

Fields:
- exact key
- representative row handle
- exact base score
- precomputed FG scalars / pointers

Invariant:
- every dropped candidate failed a proof-backed upper bound.

### 5) SongSlotTicket
Per-slot ownership generation counter.

Invariant:
- any slot-local fast path is valid only when the ticket matches.
- if the ticket mismatches, fall back to canonical exact cache lookup.

## GPU pipeline steps

### Step A: exact signature packing
For each staged candidate row:
1. read `genome_base_stats`
2. quantize to exact fixed-point form
3. build `ExactScoreKey`
4. append `(key, run_idx, row_idx, song_slot, slot_ticket)` to `DeviceSignatureBuffer`

### Step B: on-device unique grouping
1. radix sort by packed key
2. run-length encode to produce unique spans
3. query `ExactEvalTable`
4. compact cache misses into a dense miss buffer

### Step C: exact base evaluation on misses only
1. run the existing exact GPU evaluator only on miss representatives
2. write exact results back to `ExactEvalTable`
3. scatter exact scores to every row in each span

### Step D: exact FG upper bound on-device
For each unique candidate:
1. load exact base score
2. compute safe FG upper bound
3. compare with current song best final score
4. emit only survivors to `FGFrontierBuffer`

### Step E: exact FG interval-DP on-device
For each FG frontier candidate:
1. precompute fever window endpoints `fever_end[a]`
2. precompute `window_bonus[a]`
3. precompute `suffix_bonus[a]`
4. run the exact interval-DP with monotone stopping
5. write exact final score back to `ExactEvalTable`

### Step F: persistence
Only winners cross the host boundary.

## Exact FG math needed by the kernel
For a state `s` with fill-counting eligible notes `u_1, u_2, ...`:
- activation at rank `m` requires
  `k_min(m) = min{k >= 0 : ceil(raw_fill + 0.5*k) = m}`
- direct penalty for that activation is
  `C_s(m) = sum of the k_min(m) cheapest penalties among {c_{u_1}, ..., c_{u_{m-1}}}`
- fever reward is
  `B(a) = sum_{i=a}^{e(a)} b_i`
- exact recurrence is
  `DP(s) = max_m [ B(a(m)) - C_s(m) + DP(next(e(a(m)))) ]`

Safe stopping rule:
- `U_s(a) = suffix_bonus[a] - C_s(a)` upper-bounds any transition that starts at `a` or later
- because `suffix_bonus[a]` decreases and `C_s(a)` increases with later activations, once `U_s(a) <= current_best`, scanning can stop exactly

## Pseudocode

```text
initialize population P
initialize ExactEvalTable U
initialize current_best_final = -inf

while budget_remaining:
    children = propose_children(P)

    rows = gpu_pack_exact_signatures(children)
    groups = gpu_sort_and_group(rows)

    misses = []
    for g in groups:
        if not U.contains_exact(song_id, g.key):
            misses.append(g)

    exact_scores = gpu_exact_base_eval(misses)
    U.insert_exact_batch(song_id, misses, exact_scores)
    gpu_scatter_exact_scores(groups, U)

    fg_frontier = gpu_filter_by_safe_fg_ub(groups, current_best_final)
    fg_exact = gpu_exact_fg_interval_dp(fg_frontier)
    U.insert_exact_fg_batch(song_id, fg_frontier, fg_exact)

    current_best_final = max(current_best_final, max(fg_exact))
    P = select_next_population(P, children)
```

FG kernel:

```text
solve(state s):
    eligible = fill_counting_notes_after(s)
    best = 0
    prefix_min_cost = empty incremental structure

    for activation rank m from first feasible to end:
        k = k_min(m)
        cost = cheapest_prefix_cost(prefix_min_cost, k)
        a = eligible[m]

        if suffix_bonus[a] - cost <= best:
            break

        e = fever_end[a]
        value = window_bonus[a] - cost + solve(next_state(e))
        best = max(best, value)
        prefix_min_cost.insert(penalty[a])

    return best
```

## Correctness invariants
1. Only exact results go into `ExactEvalTable`.
2. Key packing is exact fixed-point, never lossy float hashing.
3. Candidate rejection before exact FG uses only a safe upper bound.
4. Slot-local pointers are used only if `slot_ticket` still matches.
5. Any fallback path must still hit the exact canonical table, not recompute approximately.

## Instrumentation to add
- total proposed children
- raw duplicate rate
- exact-key collision rate
- exact eval count before/after grouping
- cache hit/miss counts
- FG frontier size before/after upper-bound pruning
- FG solve count
- mean / p90 activation checks per FG solve
- host<->device bytes transferred
- slot-ticket invalidation count
- integrated songs/hour with FG fully completed

## Deployment validation checklist
1. Measure actual genome -> exact-key collision rate on real songs.
2. Verify exact key equality implies bit-identical exact score on a golden corpus.
3. Compare interval-DP FG output against the current exact FG solver on the same candidates.
4. Re-run the 200-song benchmark with fixed seeds and confirm zero FG backlog.
5. Profile end-to-end utilization and host<->device bytes before and after.
