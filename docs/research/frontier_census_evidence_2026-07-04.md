# Frontier Census Evidence — Exactness + GA-Speed, Loadout Search Space

Generated: 2026-07-04
Status: first measured evidence pass for
`docs/research/single_song_cell_conditioned_exact_frontier_proposal.md` (Gate A).
Harness: `tools/research/frontier_census.py` (CPU-only; runnable on any machine).
Raw results: `docs/research/frontier_census_results_2026-07-04/*.json`.

Scope: the **loadout search space only** (6 gear slots x distinct-3 minis), per the
project owner's framing that this is the GA's weak point while the timeline and FG
layers are trusted. The oracle for every exactness claim is the repo's own f64
fixed-timing exact scorer (`score_stats_fixed_timing_exact_batch` — chart-time
deterministic fever timeline). Environment: Linux sandbox, single CPU core,
~2.5 GB usable RAM (this bounded the largest completed pool sizes; see Limits).

## 1. Verdict summary

- **Exactness: PASS, unanimously, on every completed run.** The cell-conditioned
  DP (per-cell dominance only, cells enumerated) is measurably lossless over the
  production loadout space at every tested scale, on 6 distinct charts across
  Easy/Normal/Hard and 4 color pairs including the `Flow/Flow` (primary ==
  secondary) edge case.
- **GA-speed: supported, with a structure that is better than the proposal hoped
  for.** The DP frontier is larger than the proposal's a-priori estimate
  (10^6–10^7 states, not 10^5–10^6), but two measured facts compensate:
  (a) the score-relevant `(b, c, f)`-collapse shrinks the set to evaluate by
  3.3–4.3x, and (b) **the frontier is timeline-independent — it depends on the
  song only through `(primary_color, secondary_color)`** — so at most ~25
  frontiers cover the entire catalog (5 colors x 5). Exactness then costs one
  frontier build per color pair (amortized over ~2,237 charts ≈ 90x reuse) plus a
  per-song batched evaluation of the same shape of work a GA run already does.

## 2. Evidence checks (all green)

| Check | What it proves | Result |
|---|---|---|
| V1 | Dominance axes `ref_pp/ref_cm/ref_fm` nondecreasing (L3 precondition) | PASS. `Fever Fill Rate` is **non-monotone** in real data — and FF is a conditioned axis, never a dominance axis. The design choice is validated by the data. |
| E1 | Dominance completeness: sampled legal loadouts covered by a same-cell frontier state with `(PP, CM, FM, V)` all >= | **0 misses / 240,000 samples** (30k x 8 runs) |
| E2 | Scorer monotonicity at fixed cell (L3/O3), against the repo oracle | **0 violations / 1,900 ordered pairs** |
| E3 | Brute-force argmax equality (O5): exhaustive enumeration of random sub-pools (~14,580 loadouts each) vs DP frontier, both scored by the repo oracle | **bit-exact equality on all 16 trials** |
| P | Harness's vectorized census scorer vs oracle | bit-identical on 300-row subsamples per song |
| (dev) | Exhaustive coverage on synthetic pools during hardening | 3 x 14,580 loadouts, 0 misses |

## 3. Census results

All rows completed end-to-end (DP + collapse + eval + E1/E2/E3). `F_dp` = final
per-cell Pareto frontier (states carried by the DP). `F_eval` = after per-cell
`(b, CM, FM)` staircase collapse — the set a GPU would actually score.
GA budget reference: `705 x 125 x 3 = 264,375` evaluations/song.

| Song (chart) | Colors | Pools (gear/slot, minis) | Raw space | F_dp | F_eval | F_eval / GA | Cells | DP s (1 core) | Eval s |
|---|---|---|---|---|---|---|---|---|---|
| Red Room (Easy) | Rush/Flow | 8, 12 | 5.8e7 | 1,288,400 | 388,408 | 1.5x | 10,173 | 1.6 | 0.6 |
| Red Room (Easy) | Rush/Flow | 10, 16 | 5.6e8 | 2,945,185 | 725,349 | 2.7x | 11,051 | 4.6 | 1.2 |
| Red Room (Easy) | Rush/Flow | 12, 20 | 3.4e9 | 5,651,123 | 1,306,540 | 4.9x | 11,868 | 16.9 | 2.4 |
| Starry Night (Easy) | Flow/Flow | 10, 16 | 5.6e8 | 5,576,659 | 1,059,758 | 4.0x | 11,017 | 6.1 | 2.3 |
| #include signal.h (Normal) | Vibe/Flow | 10, 16 | 5.6e8 | 3,985,473 | 812,314 | 3.1x | 9,987 | 5.1 | 1.6 |
| Red Room (Normal) | Rush/Flow | 8, 14 | 9.5e7 | 1,381,378 | 405,563 | 1.5x | 10,175 | 1.7 | 0.6 |
| #include signal.h (Hard) | Vibe/Flow | 8, 14 | 9.5e7 | 1,985,513 | 522,266 | 2.0x | 7,776 | 1.9 | 0.8 |
| Red Room (Hard) | Rush/Flow | 8, 14 | 9.5e7 | 1,381,378 | 405,563 | 1.5x | 10,175 | 1.7 | 0.6 |

Full-pool partial (Red Room Easy, gear capped 16/slot, minis 28; level-6 reduce
exceeded sandbox RAM): mini-triple frontier 281 -> gear level widths
3,550 / 38,894 / 266,835 / 1,312,185 / 3,983,120 (L1–L5), recorded in
`frontier_census_results_2026-07-04/redroom_easy_g16_m28_partial_widths.txt`.
Uncapped Red Room pools are ~24–25 gear/slot and 39 minis.

Scaling fit (Red Room Easy, 3 completed sizes): `F_dp ~ raw_space^0.36`,
extrapolating to uncapped pools (raw ~2.2e12): **F_dp ≈ 2–6 x 10^7 states,
F_eval ≈ 0.5–1.5 x 10^7** (19–57x one GA song budget). To be replaced by a
measured number on a >= 8 GB machine (the harness runs as-is; see §6).

## 4. The timeline-independence finding (biggest practical consequence)

Red Room **Normal** and Red Room **Hard** produced *identical* frontiers
(F_dp 1,381,378; F_eval 405,563; 10,175 cells) with different best scores —
because the DP consumes the song only through `(primary_color, secondary_color)`
(pool filtering + the `v = 2*primary + secondary` projection). The timeline enters
only at evaluation.

Consequences, in production terms:

- There are at most **25 distinct frontiers** (ordered color pairs) for the whole
  catalog under a fixed item DB and team-buff context — ~90x amortization over
  2,237 charts.
- The expensive object (the frontier build) is **cacheable and content-addressed**
  exactly like the timeline frontier cache: key = (item-pool content hash,
  color pair, team-buff context, clamp constants).
- Per-song exact base optimization reduces to: load cached color-pair frontier ->
  score `F_eval` states against the song's cell grid (existing fixed-scoring GPU
  kernel shape) -> argmax. That is a *single embarrassingly-parallel batch* — no
  125-generation sequential dependency like the GA loop.

## 5. GA-speed assessment (honest version)

- Evaluation counts: F_eval at full pools ≈ 19–57x one GA song budget, but GA
  spends its budget across 375 sequentially dependent kernel waves
  (125 gens x 3 starts); the exact evaluation is one independent batch. On the
  7900 XTX the eval kernel throughput, not wave count, is the binding constraint,
  and the CPU harness already sustains ~5.5e5 exact f64 evals/s on one core.
- DP transit: sort/scan/segment ops over 10^7–10^8 keys; on-GPU radix throughput
  puts a full-pool frontier build in the seconds range — and it runs **once per
  color pair**, not per song.
- Net: amortized per-song exact cost ≈ one batched evaluation pass comparable to
  (or below) a 3-start GA run's kernel work; the 66 s / 511 s costs of the
  research-4 exact path are not intrinsic to exactness.

## 6. Limits and what still needs measuring

- Sandbox RAM (~2.5 GB) blocked uncapped-pool completion (OOM at gear level 6 of
  Red Room Easy). The harness completes it on any >= 8 GB machine:
  `python tools/research/frontier_census.py --song "Data/Easy/(The) Red  Room (Easy) by Camellia.txt" --verbose`
  (raise `STATE_HARD_CAP` accordingly). That yields the exact full-pool F_dp /
  F_eval this document extrapolates.
- Oracle scope is the fixed-timing (chart-time) scorer by design — the timing
  envelope and FG layers are trusted per the owner's scoping. The DP claims are
  scorer-agnostic given per-cell monotonicity (E2), so swapping in the envelope
  payload scorer changes evaluation, not the frontier.
- Team-buff stat seed not applied (constant additive offset; changes PP lookup
  start, not the structure). Rerun with the T5 seed before production claims.
- The base leaderboard top-1 is what E3 certifies; top-K and FG-side certification
  follow the proposal's Sections 9 and 7 (unchanged by these measurements).

## 7. Defects found and fixed during hardening (recorded for reuse)

1. **Fenwick stamp reuse (harness kernel):** the per-cell Fenwick used a stamp
   array persisting across calls with a counter restarting at 0 — stale entries
   from earlier calls acted as phantom dominators and silently over-pruned
   (E1 caught it: 9,776/30,000 misses). Fix: monotone stamp counter threaded
   across calls. Lesson worth keeping: **E1-style dominance-completeness sampling
   is the cheapest tripwire for any future skyline/frontier kernel** — parity
   tests on curated inputs did not catch this; random coverage did, immediately.
2. **Primary == secondary color aggregation (harness E3 reference):** real charts
   exist with `Primary Color == Secondary Color` (e.g. Starry Night, Flow/Flow).
   Accumulating the color key twice doubles `b` (6F instead of the
   production-correct 3F). The DP and projection were correct; the brute-force
   *reference* was wrong and E3 caught the 42% discrepancy. Any future exact
   tooling must treat the color pair as a set-with-multiplicity, not two keys.
3. **Working-tree corruption (repo, pre-existing):**
   `gear_optimizer/solver/score_math.py` (+7,496 NUL bytes appended) and
   `gear_optimizer/domain/jobs.py` (+65 NUL bytes) are corrupted on disk —
   Python cannot import files containing NUL bytes. `git show HEAD:<file>` is
   clean for both; the corruption is a pure null-tail append (interrupted write).
   **Restore with:** `git checkout -- gear_optimizer/solver/score_math.py gear_optimizer/domain/jobs.py`.
   The harness now preflights for this and fails with the same guidance.

## 8. Relation to the proposal's gates

- Gate A (frontier census): **passed with revision** — frontiers are 10x larger
  than hoped in raw-lattice form, but `(b,c,f)`-collapse plus color-pair caching
  land the amortized per-song cost at GA order. The proposal's Section 10 cost
  model should be updated to the measured widths and the color-pair cache.
- Gate B (FG shape) and Gate C (adoption policy): untouched by this pass;
  the FG certificate design is unaffected because the frontier it ranges over is
  now known to be cacheable per color pair.
