"""Reverse score lookup engine (separate product surface from the optimizer).

Given the observables a RoBeats leaderboard row exposes for a play --
score, naked (casual) score, accuracy, and gear power -- this package
recovers the equivalence class of loadouts consistent with them.

Components:
- ``game_model``: 1:1 ports of the decompiled game's stat curves, gear power
  formula, and mini (pet) level/rank scaling law ([REDACTED PRIVATE REPOSITORY] sources).
- ``webport_extract``: parsers that lift pet stat tables and gear-upgrade
  definitions out of the decompiled Lua sources.
- ``domain``: the loadout domain (gear, per-piece upgrades, minis with
  level/rank/ascension, gems, team buff) and statsdict composition.
- ``oracle``: forward map loadout -> observables, scoring through the
  optimizer's canonical exact scorer (one scoring implementation, reused).
- ``synthetic``: seeded synthetic labeled-data generator over the domain.
- ``engine``: the reverse sieve (lattice fold + exact gear-power join +
  exact-score filter + witness expansion + soundness gate).

Scoring semantics are never duplicated here: the geared/naked scores come
from ``gear_optimizer.solver.scoring.exact_rescore`` (the canonical exact
implementation). This package only adds the domain model around it and the
inversion machinery.
"""

__all__ = [
    "game_model",
    "webport_extract",
    "domain",
    "oracle",
    "synthetic",
    "engine",
]
