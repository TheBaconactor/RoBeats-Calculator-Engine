# Ceiling HitSim vs Monte Carlo (Real Songs) — 2026-04-04

Goal: validate the claim that the shipped **Analytical HitSim “ceiling”** GPU timeline
(`GPU_TIMELINE_CEILING_HITSIM=1`) is **never worse** than the **best** Monte Carlo HitSim sample
(`SongRepeats`-style max-over-seeds) for the same `(FT, FF)` cell, using real `Data/` charts.

This uses the repo’s comparison harness:

- Script: `tools/bench/bench_ceiling_vs_mc25.py`
- MC path: `simulate_perfect_hit_timestamps_with_great_candidates()` (Perfect-only offsets + monotone carry) +
  `calculate_fever_timeline_indices()`
- Ceiling path: `compute_timeline_grid_ceiling_hitsim_kernel` (GPU) + CPU reimplementation

Important detail: the ceiling kernel evaluates **two fully-feasible variants**:

- **normal-hi**: choose the latest nominal carry (`group_high`) during non-fever (“fill”) segments
- **normal-lo**: choose the earliest nominal carry (`group_low`) during non-fever segments

It then selects the better one via a deterministic score proxy (`_ceiling_compare_score()` with the same
`base=10000, combo=2.6, fever=5.25` used by this bench) plus tie-breakers.

## Experiment A (no counterexample)

Command:

```powershell
python tools/bench/bench_ceiling_vs_mc25.py --seeds 1000 --strict
```

Result (song defaults to “Everything Will Freeze …”):

- `ceiling_score == mc_best_score`
- MC `min == p50 == max` (this cell appears insensitive to sampled Perfect-window jitter)

## Experiment B (Bopeebo, the historical “counterexample”)

Command:

```powershell
python tools/bench/bench_ceiling_vs_mc25.py `
  --song "Data/Hard/Bopeebo (Hard) by Kawai Sprite.txt" `
  --ft 0 --ff 160 --seeds 2000 --strict
```

Observed (strict mode passes):

- `mc_best_score` **47904375**
- `ceiling_score` **47904375**
- `ceiling_score - mc_best_score = 0`
- CPU ceiling signature == GPU ceiling signature == MC-best signature

### Why this case mattered (what goes wrong if you *only* run normal-hi)

If you force *only* the **normal-hi** carry choice for Bopeebo at `(FT=0, FF=160)`, you can get a strictly worse
timeline than MC best-of-N, even when the *total* fever-note count is unchanged.

What happens is a **boundary flip trade**:

- One fever note shifts from **body → head**.
- Total fever notes stay the same, but score drops because head notes are always ≤ body notes in
  `gear_optimizer/solver/scoring_core.py::fast_calculate_score`:
  - body notes (≥100) have constant normal value `int(base*combo)`
  - head notes (first 100) ramp from ~`base` up to `base*combo`

For Bopeebo (bench’s fixed `base=10000, combo=2.6, fever=5.25`):

- losing 1 body fever note costs `136500 - 26000 = 110500`
- gaining fever on head note `i=88` yields `103020`
- net delta `= -7480`

This is exactly why the ceiling implementation compares **normal-hi vs normal-lo** and emits the better
score-signature: the “maximize fever length” intuition is not aligned with “maximize score” when you can trade
body vs head fever at cascade boundaries.

## Takeaway

- A one-shot ceiling timeline can be **dramatically faster** than Monte Carlo best-of-N while still matching MC-best on
  real charts, *if* it is **score-aware** in its deterministic choices.
- The minimal, fast improvement that fixed the Bopeebo case was: evaluate both **normal-hi** and **normal-lo** and
  select by a deterministic score proxy + tie-breakers (no per-seed sampling).

This is still not a formal proof that the ceiling kernel is a global optimum for all charts/cells, but it is strong
evidence that the dual-variant selection removes a real failure mode (score-worse-than-MC) without reintroducing any
Monte Carlo cost.

## Experiment C (new counterexample; fixed by adding a third dimension)

After dual-selection (`normal-hi` vs `normal-lo`) was in place, we found a real-song cell where the ceiling was still
strictly under MC best-of-N.

Command:

```powershell
python tools/bench/bench_ceiling_vs_mc25.py `
  --song "Data/Hard/Baby I Don't Care (Hard) by Johnny  Michiko Hamada [Nash Music Library].txt" `
  --ft 0 --ff 160 --seeds 500 --strict
```

Observed (pre-fix):

- `ceiling_score < mc_best_score` by **5440**
- Mechanism: greedy **fever-max** includes a head-only swing note (`i=91`) in an early window, which cascades into a
  later window shift and trades `1` body-fever note for `1` head-fever note.

Fix applied in this branch:

- Add a second fever-end policy:
  - `fever-max`: keep swing groups in-fever whenever feasible (existing)
  - `fever-min`: end fever at the earliest reachable out-group in the swing band
- Evaluate `(normal-hi/normal-lo) × (fever-max/fever-min)` (4 variants total) and select the best signature by the same
  deterministic score proxy + tie-breaks.

Observed (post-fix): the same command passes strict mode, and `ceiling_score == mc_best_score`.
