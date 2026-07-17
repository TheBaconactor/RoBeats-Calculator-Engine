"""1:1 ports of RoBeats game mechanics needed by the reverse engine.

Sources (decompiled, [REDACTED PRIVATE REPOSITORY] repo):
- ``ReplicatedStorage/Shared/BezierDist.lua``   -- arc-length bezier curves
- ``ReplicatedStorage/Avatar/GearStats.lua``    -- f_N stat curves, gear power,
  color point bonus
- ``ReplicatedStorage/Avatar/PlayerBlobAvatar.lua`` -- statsdict gear power
- ``ReplicatedStorage/Pets/PetUtils.lua``       -- mini level/rank scaling law

Live-game constants are hardwired (no flags, per repo policy):
- ``ExtendedGearStatCap160 = true``  -> effective stat clamp is [-80, 160]
- ``PetRankUpEnabled = true``        -> pet color scaling uses floor()
- ``ColorGearStatsEnabled = true``   -> upgrade definitions use color branch

Stat keys use the optimizer's canonical display names so composed dicts feed
``score_stats_exact`` directly.
"""
from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

# Optimizer canonical stat-key names (== GearStats type_to_name, minus " Points"
# suffix on colors, matching gear_optimizer conventions).
COLOR_KEYS: tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")
GEARPOWER_MAIN_KEYS: tuple[str, ...] = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Fill Rate",
    "Fever Multiplier",
    "Fever Time",
)

# Decompiled GearStats type name -> optimizer stat key.
GAME_TYPE_TO_KEY: dict[str, str] = {
    "ColorBlue": "Chill",
    "ColorGreen": "Vibe",
    "ColorPurple": "Flow",
    "ColorRed": "Rush",
    "ColorOrange": "Beat",
    "NoteSpeed": "Note Speed",
    "PerfectTime": "Perfect Time",
    "PerfectPoints": "Perfect Points",
    "GreatTime": "Great Time",
    "GreatPoints": "Great Points",
    "OkayTime": "Okay Time",
    "OkayPoints": "Okay Points",
    "ComboThreshold": "Combo Threshold",
    "ComboMultiplier": "Combo Multiplier",
    "ComboBreakMultiplier": "Combo Break Multiplier",
    "FeverFillRate": "Fever Fill Rate",
    "FeverMultiplier": "Fever Multiplier",
    "FeverTime": "Fever Time",
    "FeverDrainRate": "Fever Drain Rate",
}

STAT_CLAMP_LO = -80
STAT_CLAMP_HI = 160  # ExtendedGearStatCap160 == true (live)

PET_MIN_LEVEL = 1
PET_MAX_LEVEL = 50
PET_MIN_RANK = 1
PET_MAX_RANK = 4


def _lerp(a: float, b: float, t: float) -> float:
    return (b - a) * t + a


def _line_y(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    """CurveUtil.YForPointOf2PtLineP1P2X -- exact argument order preserved."""
    slope = (y1 - y2) / (x1 - x2)
    return slope * x + (y1 - slope * x1)


class BezierDist:
    """Arc-length-parameterized cubic bezier, sampled at 10 segments.

    Port of ``BezierDist.lua`` (default segment count 10). ``get_y_for_
    distance_pct`` walks the sampled polyline by arc length and evaluates the
    bezier Y at the recovered parameter t.
    """

    __slots__ = ("_pts", "_samples", "_total")

    def __init__(self, x1, y1, x2, y2, x3, y3, x4, y4, segments: int = 10):
        self._pts = (x1, y1, x2, y2, x3, y3, x4, y4)
        samples: list[tuple[float, float]] = [(0.0, 0.0)]  # (t, cum distance)
        t = 0.0
        dist = 0.0
        prev = (x1, y1)
        for _ in range(segments):
            t += 1.0 / segments
            px = self._bezier_val(x1, x2, x3, x4, t)
            py = self._bezier_val(y1, y2, y3, y4, t)
            dist += math.hypot(px - prev[0], py - prev[1])
            samples.append((t, dist))
            prev = (px, py)
        self._samples = samples
        self._total = dist

    @staticmethod
    def _bezier_val(a: float, b: float, c: float, d: float, t: float) -> float:
        u = 1.0 - t
        return u * u * u * a + 3.0 * t * u * u * b + 3.0 * t * t * u * c + t * t * t * d

    def _seg_for_distance(self, target: float) -> int:
        """Port of the Lua bisection (f_T); returns 0-based lower index."""
        lo = 1
        hi = len(self._samples)
        while hi - lo > 1:
            mid = math.floor(_lerp(lo, hi, 0.5))
            if self._samples[mid - 1][1] < target:
                lo = mid
            else:
                hi = mid
        return lo - 1

    def get_t_for_distance(self, distance: float) -> float:
        d = min(max(distance, 0.0), self._total)
        if d == self._total:
            return 1.0
        i = self._seg_for_distance(d)
        t0, d0 = self._samples[i]
        t1, d1 = self._samples[i + 1]
        return _lerp(t0, t1, (d - d0) / (d1 - d0))

    def get_y_for_distance_pct(self, pct: float) -> float:
        x1, y1, _x2, y2, _x3, y3, _x4, y4 = self._pts
        t = self.get_t_for_distance(self._total * pct)
        return self._bezier_val(y1, y2, y3, y4, t)


# The five shaping curves from GearStats.lua (upval12..upval16).
_CURVE_NEG_INNER = BezierDist(0, 0, 0.4, 0.1, 1, 0.8, 1, 1)   # (-40, 0)
_CURVE_NEG_OUTER = BezierDist(0, 0, 0.8, 0, 0.9, 0.8, 1, 1)   # (-80, -40)
_CURVE_POS_INNER = BezierDist(0, 0, 0, 0.4, 0.7, 0.9, 1, 1)   # (0, 40)
_CURVE_POS_OUTER = BezierDist(0, 0, 0.2, 0.1, 0.4, 1, 1, 1)   # (40, 80)
_CURVE_EXTENDED = BezierDist(0, 0, 0, 0.5, 0.6, 1, 1, 1)      # (80, 160)


def f_n(a: float, b: float, c: float, d: float, e: float, stat: float) -> float:
    """GearStats f_N: the 5-anchor stat interpolation curve.

    Anchors correspond to effective stat values -80, -40, 0, +80, and the
    positive-side interpolation targets; ``c`` is the stat-0 base value.
    """
    v3 = min(max(stat, STAT_CLAMP_LO), STAT_CLAMP_HI)
    if v3 > 0:
        if v3 < 40:
            pct = _CURVE_POS_INNER.get_y_for_distance_pct(_line_y(0, 0, 40, 1, v3))
            v4 = _lerp(c, d, pct)
        elif v3 > 80:
            pct = _CURVE_EXTENDED.get_y_for_distance_pct(_line_y(80, 0, 160, 1, v3))
            v4 = _lerp(e, e + (e - d) * 0.35, pct)
        else:
            pct = _CURVE_POS_OUTER.get_y_for_distance_pct(_line_y(40, 0, 80, 1, v3))
            v4 = _lerp(d, e, pct)
    elif v3 < 0:
        if v3 > -40:
            pct = _CURVE_NEG_INNER.get_y_for_distance_pct(_line_y(-40, 0, 0, 1, v3))
            v4 = _lerp(b, c, pct)
        else:
            pct = _CURVE_NEG_OUTER.get_y_for_distance_pct(_line_y(-80, 0, -40, 1, v3))
            v4 = _lerp(a, b, pct)
    else:
        return c
    if not math.isfinite(v4):
        return c
    return v4


# --- Stat value curves (GearStats.lua, base value == 3rd argument) ---------

def perfect_points(stat: float) -> int:
    return math.floor(f_n(50, 100, 200, 350, 450, stat))


def great_points(stat: float) -> int:
    return math.floor(f_n(35, 75, 150, 225, 300, stat))


def okay_points(stat: float) -> int:
    return math.floor(f_n(25, 50, 100, 150, 200, stat))


def combo_thresholds(stat: float) -> tuple[int, int, float]:
    v = f_n(600, 450, 100, 20, 10, stat)
    return math.floor(v * 0.25), math.floor(v * 0.5), v


def combo_multiplier(stat: float) -> tuple[float, float, float]:
    v = f_n(0, 0.25, 1, 1.4, 1.6, stat)
    return 1 + v * 0.25, 1 + v * 0.5, 1 + v


def fever_multiplier(stat: float) -> float:
    return f_n(1, 1.25, 3, 4.75, 5.25, stat)


def fever_fill(stat: float) -> tuple[float, float]:
    v = f_n(0.6, 0.5, 0.333, 0.166, 0.1, stat)
    return v, v * 2


def fever_drain(stat: float) -> float:
    return f_n(0.5, 0.25, 0.1, 0.01, 0, stat)


def base_decay_rate(stat: float) -> float:
    """Fever Time stat curve (GearStats.get_base_decay_rate)."""
    return f_n(0, 0.05, 0.15, 0.35, 0.4, stat)


def combo_break_multiplier(stat: float) -> float:
    return f_n(0, 0.1, 0.5, 0.9, 1, stat)


def note_speed_multiplier(stat: float) -> float:
    return f_n(1.8, 1.55, 1, 0.5, 0.35, stat)


# --- Gear power (PlayerBlobAvatar.statsdict_get_gear_power) ----------------

def gear_power(
    stats: Mapping[str, int],
    *,
    include_base: bool = True,
    song_colors: Sequence[str] | None = None,
) -> int:
    """Exact port. Leaderboard gearPower == base part + song-color part.

    Base part: 5 x each of the five main stats (raw, unclamped).
    Color part: 6 x c1 for single-color songs, else 4 x c1 + 2 x c2 in
    (primary, secondary) order.
    """
    p = 0
    if include_base:
        for key in GEARPOWER_MAIN_KEYS:
            p += 5 * int(stats.get(key, 0))
    if song_colors:
        colors = [c for c in song_colors if c]
        for c in colors:
            if c not in COLOR_KEYS:
                raise ValueError(f"unknown song color {c!r}")
        if len(colors) == 1:
            p += 6 * int(stats.get(colors[0], 0))
        elif len(colors) == 2:
            p += 4 * int(stats.get(colors[0], 0)) + 2 * int(stats.get(colors[1], 0))
        else:
            raise ValueError(f"songs carry 1 or 2 colors, got {colors!r}")
    return p


def color_point_bonus_perfect(
    stats: Mapping[str, int], song_colors: Sequence[str]
) -> int:
    """Per-Perfect color bonus (GearStats color bonus, Perfect weights).

    Single color: floor(3 * c1). Two colors: floor(2 * c1) + floor(1 * c2).
    Documented here for reference/tests; production scoring flows through the
    optimizer's exact scorer which already implements the full table.
    """
    colors = [c for c in song_colors if c]
    if len(colors) == 1:
        return math.floor(3 * int(stats.get(colors[0], 0)))
    if len(colors) == 2:
        return math.floor(2 * int(stats.get(colors[0], 0))) + math.floor(
            1 * int(stats.get(colors[1], 0))
        )
    raise ValueError(f"songs carry 1 or 2 colors, got {colors!r}")


# --- Mini (pet) scaling law (PetUtils) --------------------------------------

def pet_rank_to_max_level(rank: int) -> int:
    if rank >= 4:
        return 50
    if rank >= 3:
        return 40
    if rank >= 2:
        return 30
    return 20


def pet_color_level_scale(level: int) -> float:
    """Linear 1x at level 1 -> 5x at level 50 (YForPointOf2PtLineP1P2X)."""
    return _line_y(1, 1, 50, 5, level)


def pet_stats_delta(
    base_mods: Mapping[str, int],
    color_mods: Mapping[str, int],
    level: int,
    rank: int,
) -> dict[str, int]:
    """petid_level_rank_apply_statsdict: rank multiplies base mods; level
    scales color mods by lerp(1..5 over level 1..50), floored
    (PetRankUpEnabled == true)."""
    lv = min(max(int(level), PET_MIN_LEVEL), PET_MAX_LEVEL)
    rk = min(max(int(rank), PET_MIN_RANK), PET_MAX_RANK)
    out: dict[str, int] = {}
    for key, val in base_mods.items():
        out[key] = out.get(key, 0) + int(val) * rk
    scale = pet_color_level_scale(lv)
    for key, val in color_mods.items():
        out[key] = out.get(key, 0) + math.floor(int(val) * scale)
    return out


def merge_stats(target: dict[str, int], delta: Mapping[str, int]) -> dict[str, int]:
    for key, val in delta.items():
        if not isinstance(val, (int, float)):
            raise TypeError(f"non-numeric stat delta {key!r}={val!r}")
        target[key] = int(target.get(key, 0)) + int(val)
    return target


def observable_projection(
    stats: Mapping[str, int], song_colors: Sequence[str]
) -> tuple[int, ...]:
    """The stat dims that (score, gear power) can see for one song:
    (c1[, c2], PP, CM, FM, FT, FF). Everything else is invisible."""
    dims: list[int] = [int(stats.get(c, 0)) for c in song_colors if c]
    dims.extend(int(stats.get(k, 0)) for k in GEARPOWER_MAIN_KEYS)
    return tuple(dims)


def iter_all_stat_keys() -> Iterable[str]:
    return GAME_TYPE_TO_KEY.values()
