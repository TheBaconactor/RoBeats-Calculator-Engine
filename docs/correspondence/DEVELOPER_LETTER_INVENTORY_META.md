Subject: Help Needed: RoBeats Inventory Meta Coverage (<=100 Gear-Variant Cap)

Hi [Name],

I'm reaching out for your help on an optimization problem in my RoBeats MetaFinder project. Since you have never seen this codebase, I can share a self-contained report (plain-language explanation + real data) on request.

I'm currently stuck because the search space is extremely large and my current approach is not making meaningful progress. I'd like your best assessment of what is going wrong (modeling or algorithmically) and what the most promising path forward is.

At a glance (problem spec)
- Inputs: per-song peak candidates from SQLite (`team_buff_loadouts` and `team_buff_fg_loadouts`). Each candidate includes:
  - 6 gear items (Hat/Neck/Face/Shirt/Back/Pant),
  - selected element (Chill/Flow/Rush/Beat/Vibe),
  - gem totals across 6 stats (PP, CM, FM, FT, FF, OV) that sum to 90 (6 slots x 15),
  - minis (3 equipped minis, stored as 3 groups).
- Decision: pick an inventory I of <= 100 gear variants.
- Feasibility / coverage: a song is covered if (for at least one of its peak candidates) we can assign 6 variants (one per slot) from I such that the 6 per-slot gem vectors sum exactly to the candidate totals and the OV color-lock rules match the song's selected element.
- Objective: maximize the number of covered songs in the target set.
  - Important: I do NOT assume the instance is fully coverable under the 100-variant cap (in fact, I believe full coverage across all elements/songs is impossible). I'm looking for the best achievable coverage and, ideally, a way to reason about feasibility / upper bounds.
- Output: inventory list + per-song assignment (which DB row/candidate + which 6 inventory variants were used).

Hard constraints (please do not relax unless I explicitly say so)
- Inventory cap: <= 100 gear variants total (not "100 gear names").
- Exact-peak only: a covered song must match the DB peak candidate exactly (no near-peak scoring).
- Production solver loop must remain GPU-first (Taichi on Vulkan). CPU is fine for analysis and preprocessing, but not as a production fallback solver.

Target songs ("higher songs")
- When I say "higher songs" I mean: [PLEASE CONFIRM: e.g. all Hard songs / a specific curated list].
  If you need a precise list/definition, tell me and I'll provide it. If unclear, assume the full song set.

What I need from you
1) A clean formalization of this problem class (even if you choose an approximate modeling).
2) Where the combinatorics are coming from and why the current method is stalling.
3) A recommendation: keep iterating on the current heuristic vs restart, and what the restart should be (e.g., maximum-coverage / set-cover style methods with implicit columns, relaxations, bounding ideas, etc.).
4) Practical diagnostics: metrics/plots that would quickly reveal whether we are improving or just random-walking.

Glossary (terms used in the report)
- Gear item: one of the six equipped slots (Hat, Neck, Face, Shirt, Back, Pant).
- Gem stats: PP (Perfect Points), CM (Combo Multiplier), FM (Fever Multiplier), FT (Fever Time), FF (Fever Fill Rate), OV (Element/Overflow).
- Element: Chill/Flow/Rush/Beat/Vibe. Each song has a selected element.
- Gear variant: a specific per-slot 15-gem allocation for a gear item plus an OV color lock (wildcard if OV==0; element-locked if OV>0).
- Peak candidate: a DB row tied for that song's best score (from `team_buff_loadouts` or `team_buff_fg_loadouts`).
- Covered song: there exists at least one peak candidate for which all 6 required slot variants can be drawn from the shared inventory and sum exactly to the candidate totals.

Game mechanics (as modeled by the engine)
- Scoring uses 6 upgrade dimensions: PP, CM, FM, FT, FF, and OV. The data table `Data/Gear/Stats.txt` provides the underlying numeric curves used by the scoring model.
- Each equipped gear item has exactly 15 upgrade "gems" distributed across the 6 stats (per-slot budget = 15).
- Across six gear slots, totals sum to 90 and those totals are stored in the DB for each peak candidate (in the candidate's details JSON).
- OV is special in our model:
  - OV==0 yields a colorless ("wildcard") variant reusable across elements.
  - OV>0 yields an element-colored variant that must match the song's selected element.
- Force Greats (FG): the DB has a separate FG leaderboard (`team_buff_fg_loadouts`) with `fg_score` and an optional force payload. Inventory-meta coverage treats per-song peak as max(base score, FG score) and targets reproducing the peak candidate; it does not re-simulate hit timing during coverage solving.
- Minis: minis contribute to scoring in the original run and are part of the DB candidate, but the inventory-meta coverage problem does not constrain minis under the 100-variant cap (they are reported, not budgeted).

Thanks,
Emily Montes
