# zero_ms Re-solve — Provably-Safe Skip (Bit-Exact)

Date: 2026-06-21
Task: 4b of the zero_ms Lossless-Exact Replay (stacked on PR #59 / branch `zero-ms-lossless-exact`).

## Context

The zero_ms ("Non-Precise") Lossless-Exact Replay re-solves the gem allocation per
`(loadout, tier, color)` on the CPU-exact paths (base/meta via
`build_candidate_payload_exact_cpu`, FG via `fg_exact_resolve.resolve_fg_force_for_loadouts`), so the
served gems/stats/score equal a native zero_ms optimization of the exact config rather than the
inherited Perfect-window gems. Both re-solves run inside
`compute_team_buff_tier_leaderboards` (`gear_optimizer/helpers/song_helpers/team_buff_tiers.py`),
looping over every replay tier.

The owner asked for a **provably-safe skip**: skip re-solving a component when it is *provably
impossible* for the active config to change its bit-exact result; full re-solve otherwise. This is
MONEY-CRITICAL — players craft gem sets in-game from the served numbers, and a wrong served score is
compensated out of the owner's pocket. So the skip must be **sound (conservative — never a false
skip)** and **bit-exact-equal to the always-re-solve path** over a sweep.

## Soundness analysis (what is and isn't provably skippable)

The per-`(loadout, tier)` zero_ms re-solve — for BOTH the base/meta and FG branches — is a
**deterministic pure function**. Its inputs are:

- `target_fixed = apply_stat_delta(zero_ms_fixed_stats, zero_ms_tier_delta_map[tier])`
- the loadout `genome` (6 gear + 3 mini stat-dicts)
- the chart-fixed `calc_song` (`apply_timing_envelope(mode="zero_ms")`)
- `ref_arrays`, the per-loadout `selected_color`/`cfg`/`override_cfg`

Of these, **only `target_fixed` varies with `(tier, color)`**. The genome is loadout identity
(tier/color-invariant); `calc_song`/`ref_arrays` are per song; `selected_color`/`cfg`/`override_cfg`
are derived from `primary_color`/`secondary_color`/the loadout's `selected_element` and the
rehydrated baseline cfg — none of which depend on the tier or the target color. The exact CPU search
engines (`base_inner_cpu_search.py`, `response_inner_cpu_search.py`, `fixed_timing.py`) contain **no
RNG** (verified). The gem solver itself is exhaustive/deterministic, not a stochastic GA.

And `target_fixed` depends on `(tier, color)` **only through the frozen `tier_delta_map`** (the
baseline→tier stat delta). `apply_stat_delta` ignores zero-valued delta entries, so two delta maps
that differ only in zero entries produce a byte-identical `target_fixed`.

**Therefore: two configs whose `tier_delta_map` is byte-equal (after dropping zero entries) feed a
byte-identical re-solve input and produce a BYTE-IDENTICAL result** — score, gems, stats, and the
materialized witness (base details / FG force). This is the only skip that is *provable*, and it
subsumes the cases the spec called out:

- **Identity / zero-effect config.** When the delta is all-zero — the baseline tier at the baseline
  color (`team_buff_effect(tier,color) − team_buff_effect(base,base) == {}`), or any other
  zero-effect `(tier, color)` — `target_fixed` is `zero_ms_fixed_stats` verbatim (the stored
  baseline gem-less stats, shifted by nothing). All such configs collapse to ONE re-solve. This is
  the formalized identity short-circuit for zero_ms. (The owner's perfect_window identity — default
  tier + no color + perfect_window — is already not re-solved at all: perfect_window has no re-solve
  branch; it inherits the persisted gems by design.)
- **Distinct tiers/colors that share a delta map.** Solve once, reuse.

### What is NOT provably skippable (analyzed, deliberately omitted)

- **A non-zero-delta tier as "close enough" to the baseline.** The delta shifts Perfect Points and a
  color stat into the scorer's lookup tables, which have sharp breakpoints; the exhaustive gem search
  can re-optimize to a different allocation. Even if the *score* often barely moves, the *gems* can
  change, and "approximately equal" is not "bit-equal." Not skippable.
- **Component-level skips (e.g. "the FG surface doesn't depend on the delta").** The delta enters the
  gem-less base stats that the FG gem search re-allocates from; PP/color shifts can move the optimal
  allocation and therefore the FG score and gems. The FG note-graph *trace* is tier-invariant (and
  is already reused), but the FG *gem re-solve* is not delta-independent. Not skippable.
- **Reusing one component's re-solve as a proxy for another (base↔FG).** Different objectives. Not
  skippable.

The implemented skip makes cost proportional to the number of *distinct* configs, with the identity
case free — exactly the spec's intent — without ever skipping a config whose result could differ.

## Implementation

One canonical impl, no toggles (CLAUDE.md). New helper
`team_buff_tiers._tier_delta_signature(delta_map)` returns the canonical equivalence key: the sorted
tuple of **non-zero** `(stat, delta)` items (zero entries dropped because `apply_stat_delta` ignores
them, so they cannot change `target_fixed`). All-zero / identity ⇒ `()`.

Both zero_ms branches in `compute_team_buff_tier_leaderboards` now dedup by this signature:

- **base/meta:** a `resolved_by_sig` map caches, per distinct signature, the per-loadout scores AND
  the per-loadout re-solved witness payloads. A later tier with the same signature reuses them
  bit-for-bit, re-keying the witnesses under that tier's `(tier, loadout_hash)` so the DB-batch graft
  finds them. The empty-`loadout_hash` fail-loud guard is preserved on the reuse path.
- **FG:** an `fg_forces_by_sig` map caches the re-solved `force` list per signature; reused for every
  tier sharing it.

Witness objects are aliased across same-signature tiers; the DB-batch builder only *reads* from
them (never mutates), and their contents are provably identical, so aliasing is correct (and the
sweep test confirms byte-identical output end-to-end). perfect_window is structurally untouched (all
changes live inside `if timing_mode == "zero_ms":` blocks; no added line references the
perfect_window scoring path).

## Bit-exact proof (release oracle)

`tests/test_zero_ms_resolve_skip_bit_exact.py` (real-DB + song-file gated, CPU-only):

- **Sweep:** over `(tier ∈ {NONE,T1,T5,T10,T20,T50,T51}) × (color ∈ {default, Beat}) × sampled
  loadouts`, for sampled songs, it runs the FULL production path
  (`build_team_buff_tier_db_batches`, timing_mode=zero_ms) **with all tiers in one call** (so the
  per-call dedup actually fires across tiers) — once with the skip ENABLED (canonical) and once with
  `_tier_delta_signature` monkeypatched to a unique-per-call sentinel (the dedup cache can never hit
  ⇒ every `(loadout, tier)` is freshly re-solved = the always-re-solve reference). It asserts the
  per-`(color, tier)` DB batches are **byte-identical** (score + gems + stats + witness + force +
  details, via canonical JSON).
- **Anti-vacuity:** `test_skip_actually_fires_and_identity_signature_present` proves the empty
  (identity) signature appears in the sweep AND that ≥2 tiers share a signature (so the skip really
  fires; a green sweep is not vacuous).
- **Negative control (manual, during development):** forcing an UNSOUND collapse-all signature
  (`return ()`) makes the sweep FAIL (T1 wrongly reuses another tier's re-solve) — confirming the
  oracle has teeth.

## Verification

- New sweep + anti-vacuity tests: **3 passed** (`api/venv`, this Mac, CPU).
- Existing gate `tools/db/measure_lossless_exact_replay_gap.py --solver cpu --timing-mode zero_ms`:
  **delta=0 on every row** — meta+fg at T10 (8/8) and T5 (8/8), and meta+fg at T10 color=Beat (6/6).
  (`gems_changed=yes` rows are score-TIES: delta=0, exact score identical — benign, the served score
  is exact.)
- Related CPU suite green (21 passed): `test_lossless_exact_replay_gap_script`,
  `test_timing_envelope_zero_ms_mode`, `test_team_buff_tier_base_trace_failsafe`,
  `test_fg_cpu_search_parity`, `test_base_cpu_search_parity`, `test_team_buff_core`, and the new
  sweep test.
- perfect_window path unchanged (changes confined to zero_ms blocks; no perfect_window scoring line
  touched).

## Files

- `gear_optimizer/helpers/song_helpers/team_buff_tiers.py` — `_tier_delta_signature` + the two
  zero_ms dedup branches.
- `tests/test_zero_ms_resolve_skip_bit_exact.py` — the bit-exact sweep release oracle.
