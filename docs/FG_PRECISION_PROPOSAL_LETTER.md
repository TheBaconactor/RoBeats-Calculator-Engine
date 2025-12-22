Proposal: Precision Improvements For ForceGreats + Scoring Parity

To: RoBeats-Calculator-Engine developer(s)
From: (proposal draft)
Subject: Precision upgrades for ForceGreats and in-game parity

Background
- Several songs show small score mismatches vs in-game (often +/-1), and some reports claim ForceGreats (FG) peaks that the optimizer does not reproduce (e.g., "bird feeder").
- We already removed FT/FF windowing in the finder, but remaining parity gaps likely come from timeline indexing and numeric rounding.

What Was Implemented (Now)
- Full FT/FF enumeration in ForceGreatsFinder (no +/-radius window): evaluates every valid FT/FF gem split for budget=90 (4,186 pairs).
- Removed the previous 1,024 FT/FF truncation and replaced it with GPU-safe chunking via `FG_MAX_FTFF`.

Key Observation From Investigation
- After full FT/FF enumeration, "bird feeder" still shows no FG improvement for the DB-best loadout under the current model.
- A brute evaluation of forced-great configs over the full FT/FF space confirms this is not a missed FT/FF pair; it is either (a) a mismatched report/config or (b) a remaining model-vs-in-game discrepancy.

Proposed Next Improvements (High Value)
1) Resolve fever/FG timeline parity (likely cause of "force shifting" reports)
   - Server processing order (see `<redacted-place-path>`) implies:
     - the activation hit is scored as Fever, and
     - there is a "transition note" after each fever window that is scored non-fever but does not contribute fill.
   - This explains the section-aware rule from `docs/Implementation Records/FEVER_FIX_PLAN.md`:
     - section 1 uses `non_fever_base - 1`
     - sections 2+ use `non_fever_base`
   - The fix is to ensure every FG path (CPU, analytical helpers, GPU kernels) is consistent with that rule; do NOT change to "-1 for all sections".
   - Implementation plan: `docs/Implementation Records/FG_FEVER_SHIFT_PARITY_PLAN.md`

2) Add a "Game-Parity Rescore" pass (precision verifier)
   - Keep GPU search in float32 for speed, but rescore the top candidates on CPU in float64 with Roblox/Luau-style floor/trunc order.
   - Use this rescore to decide "improvement over DB record" for tight cases and to report/store final scores.

3) Validate fill math against runtime ordering (only if needed)
   - The closed-form fill model `notes_to_fill = ceil(raw_fill + 0.5*k)` is correct if Great fill is exactly half Perfect and activation is immediate.
   - If any remaining mismatches are confirmed in-game, implement an "exact gauge sim" verifier that mirrors the game's fill/update order and use it only for top candidates.

4) Improve debuggability for reports
   - Keep a small probe workflow to evaluate a specific FG config against full FT/FF space for a given loadout (useful for answering "search vs model" quickly).

Suggested Rollout
- Phase 1: Fix fever activation indexing parity (CPU + GPU).
- Phase 2: Add float64 parity rescore for top candidates.
- Phase 3: Only if needed, add exact gauge sim verifier.

Notes
- Avoids song-specific regression fixtures; focus is on general parity and math correctness.
