# Human HitSim FG Default Alignment

- Date: 2026-03-23
- Status: Implemented (config default)

## Context

`docs/HUMAN_HIT_SIM.md` documents the intended production default as `ApplyTo = FG`, so the analytical FG path gets
simulated timestamps and great-candidate carry data while the rest of the optimizer stays on chart timestamps.

The root production configs (`config.ini` and `config.profile.ini`) were still defaulting `HumanHitSim.ApplyTo = All`.
That widened the default to every scoring path and made the production baseline depend on simulated timestamps even when
the intent was FG-only analytical timing.

## Decision

Change the root production default to `HumanHitSim.ApplyTo = FG`.

Leave the benchmark/profile presets under `configs/` alone unless a specific run explicitly wants the global `All`
behavior.

## Implementation

- Updated `config.ini` to set `ApplyTo = FG`.
- Updated `config.profile.ini` to set `ApplyTo = FG` so the checked-in profiling profile matches the documented default.
- Reverted the unrelated `GPU_TIMELINE_CEILING_HITSIM` test-default tweak; `tests/conftest.py` continues to force the
  deterministic GPU timeline for parity tests.

## Consequences

- Base scoring and non-FG runtime paths remain on chart timestamps by default.
- FG evaluations still receive the analytical hit-sim payload (`fg_timestamps` and `fg_great_candidate_timestamps`),
  which is the path described in `docs/HUMAN_HIT_SIM.md`.
- The repo’s default production config now matches the documented FG-only behavior.

## Verification

- Confirmed the default mismatch against `gear_optimizer/solver/hit_simulation.py` and
  `gear_optimizer/solver/taichi_gem/api/timeline.py`.
- No runtime benchmark was needed because this was a configuration-default alignment, not a scoring-math change.
