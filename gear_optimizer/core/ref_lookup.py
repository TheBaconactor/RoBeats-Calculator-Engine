from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .constants import TOTAL_ROWS
from .utils import safe_int
from ..solver.score_math import lookup_reference_py


@dataclass(frozen=True, slots=True)
class StatFactors:
    pp_factor: float
    combo_mul: float
    fever_mul: float
    fever_fill_rate: float
    fever_time_stat: float


def resolve_stat_factors(stats: Mapping[str, Any], ref_arrays: Mapping[str, Any]) -> StatFactors:
    pp_factor = lookup_reference_py(safe_int(stats.get("Perfect Points", 0), 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(
        safe_int(stats.get("Combo Multiplier", 0), 0),
        ref_arrays["Combo Multiplier"],
        TOTAL_ROWS,
    )
    fever_mul = lookup_reference_py(
        safe_int(stats.get("Fever Multiplier", 0), 0),
        ref_arrays["Fever Multiplier"],
        TOTAL_ROWS,
    )
    fever_fill_rate = lookup_reference_py(
        safe_int(stats.get("Fever Fill Rate", 0), 0),
        ref_arrays["Fever Fill Rate"],
        TOTAL_ROWS,
    )
    fever_time_stat = lookup_reference_py(
        safe_int(stats.get("Fever Time", 0), 0),
        ref_arrays["Fever Time"],
        TOTAL_ROWS,
    )
    return StatFactors(
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        fever_fill_rate=float(fever_fill_rate),
        fever_time_stat=float(fever_time_stat),
    )
