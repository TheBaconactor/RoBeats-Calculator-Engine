# Research Index

This folder stores standalone research artifacts that are not required for day-to-day runtime docs.

## Files

- `inventory_coverage_complexity.md` — NP-completeness proof, reduction analysis, structural theorems for the inventory coverage problem
- `math_first_rewrite_proposal.md`
- `FG_SCORE_LOOP_GPU_GAP_MEASURED_20260621.md` — measured FG score-loop GPU gap on heavy songs (37-57M rows, 15-37 s/song); supersedes the 2026-06-13 review
- `FG_SCORE_LOOP_OPTIMIZATION_BRAINSTORM_20260621.md` — exact, lossless, no-regression optimization levers for the FG score loop (O1-O14; brainstorm only, no impl)
- `FG_SCORE_LOOP_EXECUTION_PLAN_20260621.md` — census-gated, bit-exact execution plan for the safe subset (O10, O4-constant, O1+O14) for a blind executor; O12 and the O4 subtract-penalty form are out of scope
- `FG_SCORE_LOOP_RESULTS_20260621.md` — executed outcome: O10 merged to main, O4 shelved (both bit-exact, timing-neutral), O1+O14 skipped (C3 realistic 0.25-0.57%); net ~zero speedup
- `FG_GROUP_INCUMBENT_MEASUREMENT_20260621.md` — next-step spec: cheap best-case measurement of whether a group-kernel (per-owner) cross-surface incumbent would skip enough surfaces to be worth a heavy-song dispatch rewrite
- `FG_GROUP_INCUMBENT_HANDOFF_20260621.md` — turnkey blind-executor handoff for the above measurement (dump-hook patch, run commands, analyzer `artifacts/profile/c4b_best_case_incumbent.py`, decision thresholds, report format). RESULT: skip ceilings 0.29-0.87 real, but forced group kernel 5.1× slower → per-owner dispatch dead
- `FG_TWOPASS_SEED_QUALITY_HANDOFF_20260621.md` — handoff (M-A) to settle the last live variant (two-pass seed): per-surface-exact dump + analyzer `artifacts/profile/ma_seed_quality.py` measuring whether the top-UB seed reaches the skip ceiling
- `FG_GPU_IDLE_CORRECTED_DIAGNOSIS_20260621.md` — sub-second per-chunk measurement (RGP installed) correcting the score-loop-only framing: chunk dispatch idle is 0.9%, the real GPU idle is the ~20 s post-score host work + 2.3 s GA warmup gap + 67 s cold-JIT (one-time)
- `FG_POSTSCORE_HOTSPOT_20260621.md` — pinpointed the ~12 s post-score GPU-idle to `reconstruct_force_greats_response_trace` (51× in the reducer, no cross-call cache, 235 ms/call); lever = per-surface trace cache if unique-surface count ≪ 51
- `GPU_FUSED_FG_OWNER_GAP_REVIEW_REQUEST_20260613.md` — earlier FG owner-gap review (superseded by the 2026-06-21 docs above; numbers under-sampled the heavy tail)

## Bundles

- `eclipse_submission_bundle/README.md`
- `eclipse_submission_bundle/implementation_plan.md`
- `eclipse_submission_bundle/ga_fg_reduction_prototype.py`
- `eclipse_submission_bundle/prototype_results.json`
- `eclipse_submission_bundle/eclipse_report.tex`
- `eclipse_submission_bundle/eclipse_report.pdf`

## Branch Archives

- `branch-archives/README.md` - branch-separated research document archive imported from incompatible research/architecture branches; preserved for comparison only.
