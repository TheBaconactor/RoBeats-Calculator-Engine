# ECLIPSE GA→FG Submission — Second-pass Re-evaluation (Net-new vs baseline engineering)

- Date: 2026-04-03
- Purpose: capture a stricter re-read of the ECLIPSE submission in a way that’s useful even if the baseline already has competent GPU plumbing.

## What was reviewed (bundle)

From `Research/eclipse_submission_bundle/`:

- `eclipse_report.pdf`
- `implementation_plan.md`
- `ga_fg_reduction_prototype.py`
- `prototype_results.json`

## Executive summary (opinion)

Re-reading the submission under a stricter “assume the baseline already has ordinary systems engineering” lens changes the story:

- The **FG exact-work reduction** is the clearest net-new piece: it’s a mathematical change to the exact solver, not just scheduling/caching/plumbing.
- The **GA signature reuse** story is interesting but more assumption- and workload-sensitive. The large headline GA cuts in the prototype are strongly driven by the *search schedule + cache lifetime*, not just the key.
- Once you remove baseline-adjacent wins (GPU-resident staging/handoff, generic dedup plumbing, frontier-style FG candidate management), the submission reads less like a broad “2× systems breakthrough” and more like “one strong FG reduction + one conditional GA idea”.

## What is *not* net-new if the baseline already has it

Treat as baseline-adjacent implementation details rather than the scientific headline (still valuable in production, just not the breakthrough):

- GPU-resident candidate staging / GA→FG handoff
- slot/epoch safety plumbing around slot-owned buffers
- generic on-device grouping / bucketing mechanics
- generic FG top-K/frontier management
- cache tables keyed by already-canonical identities

## What remains net-new

### 1) FG interval-DP / exact recurrence (strongest contribution)

The genuinely new part is not “manage FG candidates better”; it’s an exact reduction in the solver:

- reduce “choose which notes to force Great before an activation” to an activation-rank recurrence where the direct-cost term depends only on the **k cheapest prefix penalties**, and
- solve the induced **interval-path DP over fever activations**.

That changes the *cost per exact FG solve*, not just orchestration around FG.

### 2) FG monotone upper bound (net-new but secondary)

The monotone stopping rule is also net-new, but in the provided prototype it appears to be a smaller contributor than the recurrence/incremental-prefix maintenance itself.

### 3) GA semantic canonicalization (only if proved)

The GA-side idea is only “mathematically net-new” if you can state (and validate) a coarser-than-current **sufficient statistic** for the exact scorer:

> There exists a computable key κ(genome) such that exact base score and exact FG score are functions only of κ.

Without that sufficiency story, the GA side is a plausible caching tactic rather than a proved reduction.

## Prototype decomposition: separating “key strength” vs “schedule + cache lifetime”

The bundled prototype combines two effects:

1) changing the cache key (raw genome → coarser signature), and
2) changing the search schedule (multi-start restarts → steady-state).

To separate them, I re-ran the GA portion holding the *multi-start schedule fixed*, and computed the unique-eval cut under:

- raw-key cache under the same multi-start schedule, and
- signature-key cache under the same multi-start schedule,

then compared those to the prototype’s reported **steady-state + signature-cache** mode.

### GA exact-eval reductions (synthetic prototype)

Per song (mean across the same seeds/song-count regime as the bundle uses):

- Baseline proposals (children): **9216**
- Multi-start + raw-key cache: **~0.78%** exact-eval cut
- Multi-start + signature-key cache (same schedule): **~12.23%** exact-eval cut
- Steady-state + signature-key cache: **~59.76%** exact-eval cut

Interpretation (opinion):

- The “key strength” effect (raw → signature) under the same multi-start schedule is real but modest (~12%).
- The jump from ~12% → ~60% is dominated by **long-lived schedule + cache lifetime interacting with caching**, not by the key alone.

### FG kernel reductions (synthetic prototype)

From `prototype_results.json`:

- Naive vs reduced exact DP: **~2.46×** mean kernel speedup
- Extra activation-check reduction attributable to the monotone bound: **~9.7%** mean cut

Interpretation (opinion):

- Most of the FG win comes from the exact recurrence + incremental cheapest-prefix maintenance.
- The monotone bound is useful but looks like a secondary gain in this prototype.

## Revised end-to-end view if baseline systems wins are “already present”

Using the homework’s published baseline stage shares (`ga_gpu≈47.8%`, `fg_run≈22.3%`) and ignoring host-side decode/fg_prep savings as baseline-adjacent:

- FG reduction alone at ~2.46× implies only about **~1.15×** end-to-end.
- FG reduction + a schedule-held-fixed GA cut of ~12% implies about **~1.24×** end-to-end.
- Getting to **~1.7×** requires something like the much stronger ~60% GA reduction, which (in the prototype) comes from a favorable *combination* of aliasing structure + steady-state schedule + cache lifetime.

So under the stricter lens:

- FG reduction reads as **real and likely deployable** as a net-new exact-work reduction.
- GA reduction reads as **plausible but still assumption-sensitive** until key sufficiency + real alias rates are demonstrated on the real baseline candidate stream.

## Opinion on a “math-first” rewrite direction

The framing “what is the smallest exact state space the scorer really lives on?” is the right lens for multiplicative wins.

That said, a lot of the *obvious* timing-regime quotient work (FT/FF timeline precompute, explicit FT/FF combo enumeration under a gem budget) already exists in the real repo’s GPU gem solver architecture, so it would not be net-new here. The value in this direction is in finding a *strictly smaller* exact state space (or an exact reduction inside FG) than what’s already been exploited.

The most compelling “math-first” additions in the proposed rewrite are:

- **FG bounds:** strengthening pruning with a proof-backed bound (e.g., a dual-form upper bound for the “sum of k smallest prefix penalties” term) while remaining exact-safe.
- **Sufficient-statistic theorem framing:** writing the GA reuse story as a theorem with explicit proof obligations (what exact outputs are determined by what key, and how to falsify it).

### Captured “math-first rewrite” sketch (for record)

This is the specific math-first direction that seems most “breakthrough-shaped” (in the sense of shrinking exact state space / exact-work cost rather than adding more plumbing):

1) **Gem allocation timing-regime quotient (GA-side)**
   Fever walk structure depends combinatorially on only the fill and duration terms:

   - `q = ceil((N-L) * 0.333 * FF)`
   - `D = (t_{N-1} * 0.15 + 0.15) * FT`

   That suggests quotienting the gem-allocation state space by a smaller timing regime (e.g., reachable `(FF, FT)` pairs, or more tightly `(q, π_D)` where `π_D` is the implied fever-end pattern at duration `D`).

   Under a budget of `B` gems across 10 stats, raw allocations scale like `C(B+9,9)`, while `(g_FF, g_FT)` pairs scale like `C(B+2,2)`. For `B = 20`, that’s `10,015,005` vs `231`. Even if within-regime scoring still needs work, this is the kind of reduction that helps even when *every genome is unique* and cache hits are zero.

2) **FG interval-DP + a dual safe bound (FG-side)**
   Keep the exact interval-DP framing, but strengthen pruning using the dual identity for “sum of k smallest”:

   ```
   S_k(p_1,...,p_r) = max_tau [ k*tau - sum_j (tau - p_j)_+ ]
   ```

   For any chosen `tau`, this yields an exact-safe upper bound that can be used to prune DP transitions more aggressively than a raw suffix-bonus cap, while remaining proof-backed.

3) **GA semantic keys as a sufficient-statistic theorem**
   The GA reuse story becomes “mathematical” only if phrased as:

   > there exists a computable κ(genome) such that exact base score (and exact FG score, if applicable) are functions only of κ.

   Without proving what κ must include (song fingerprint, scoring/version knobs, any hit-sim/randomness context, etc.), it remains a workload-sensitive caching idea rather than a theorem.

## Message draft to the researcher (opinion-only tone)

Subject: Second-pass take (net-new vs baseline engineering)

I re-read the submission with a stricter lens: assume the baseline already has the “ordinary systems” pieces (exact reuse plumbing, GPU-resident staging/handoff, frontier-style FG candidate management), and focus only on what’s net-new because it changes the amount or cost of exact work.

Under that lens, the FG interval-DP / cheapest-prefix-penalty reduction reads as the clearest net-new contribution (it changes cost per exact FG solve). The GA signature reuse still feels promising, but it comes across as more assumption-sensitive: it depends on whether there is a provably sufficient score-semantic key that’s coarser than the identity already used for exact reuse, and the prototype’s largest GA cut appears to rely heavily on the steady-state schedule + cache lifetime rather than the key alone.

If you’re up for a second pass, I’d be most interested in reductions/bounds/identities that would remain net-new and multiplicative even if the baseline already has solid GPU dataflow + reuse + frontier plumbing.
