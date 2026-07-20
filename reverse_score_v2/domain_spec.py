"""Enumerable domain caps for synthetic sampling and reduced-domain tests.

Ported from v1 ``reverse_score.engine.DomainSpec`` without the inversion
engine. The synth generator samples strictly inside the same caps the
search enumerates, so round-trips stay closed by construction.
"""
from __future__ import annotations

from dataclasses import dataclass

from reverse_score_v2.domain import (
    COLOR_KEYS,
    DomainError,
    MINI_SLOTS,
    MiniState,
    TEAM_BUFF_TIERS,
)


@dataclass(frozen=True)
class DomainSpec:
    """Enumerable domain caps. Synth samples strictly inside this spec."""

    mini_options: tuple[MiniState, ...] = ()
    mini_max_equipped: int = MINI_SLOTS
    upgrade_type_ids: tuple[int, ...] = ()
    upgrade_max_per_type: int = 3
    upgrade_total_max: int = 6
    gem_max_per_type: int = 6
    gem_min_per_type: int = 0
    elemental_gem_max: int = 3
    team_buff_options: tuple[tuple[str, str] | None, ...] = (None,)
    allow_empty_gear_slots: bool = True
    gear_pool: dict[str, tuple[str, ...]] | None = None
    force_archetype: str | None = None

    def __post_init__(self) -> None:
        if not (0 <= self.gem_min_per_type <= self.gem_max_per_type):
            raise DomainError(
                f"gem_min_per_type={self.gem_min_per_type} outside "
                f"[0, gem_max_per_type={self.gem_max_per_type}]"
            )

    @staticmethod
    def default_team_buffs() -> tuple[tuple[str, str] | None, ...]:
        opts: list[tuple[str, str] | None] = [None]
        opts.extend(
            (tier, color)
            for tier in TEAM_BUFF_TIERS
            for color in COLOR_KEYS
        )
        return tuple(opts)
