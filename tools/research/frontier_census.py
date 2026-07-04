"""Frontier census + exactness evidence harness (research tooling, CPU-only).

Evidence for docs/research/single_song_cell_conditioned_exact_frontier_proposal.md,
scoped to the *loadout search space* (6 gear slots x distinct-3 minis). The timeline
and FG layers are out of scope (treated as trusted, proposal A5). The oracle is the
repo's own f64 fixed-timing exact scorer (``score_stats_fixed_timing_exact_batch``,
chart-time deterministic fever timeline).

Checks per song:
  V1  Dominance-axis ref tables (PP/CM/FM) nondecreasing (hard assert; FT/FF are
      conditioned axes and may be non-monotone -- FF is, in real data).
  E1  Dominance completeness: every sampled legal loadout is covered by a same-cell
      frontier state with (PP, CM, FM, V) all >= (V = 2*val_primary + val_secondary).
  E2  Scorer monotonicity (proposal L3/O3): random same-cell ordered stat pairs
      never score lower on the higher point.
  E3  Brute-force argmax equality (proposal O5): on enumerable random sub-pools,
      DP frontier best == exhaustive best, bit-exact via the repo oracle.
  P   The harness's vectorized census scorer is bit-identical to the oracle on a
      random subsample (guards E4's wall-time numbers).
  E4  Census: level widths, distinct (FT, FF) cells, per-cell widths, final DP
      frontier, the (b, c, f)-collapsed evaluation frontier, and wall times,
      against the GA evaluation budget 705*125*3 = 264,375.

Usage (from repo root, CPU only, no GPU/DB/cache writes):
  python tools/research/frontier_census.py --easy 3 --normal 3 --hard 3 --out out.json
  python tools/research/frontier_census.py --song "Data/Easy/<chart>.txt" --verbose
  # pool caps for scaling studies / RAM-bounded machines:
  python tools/research/frontier_census.py --max-gear-per-slot 12 --max-minis 20

Memory: the exact DP frontier on full pools reaches 10^6-10^7 states (measured);
STATE_HARD_CAP fails loudly if a level exceeds the configured bound. Sandbox
findings 2026-07-04: full-pool Red Room (Easy) exceeds a ~2.5 GB RAM budget; use a
machine with >= 8 GB free or pool caps.

Findings log (2026-07-04, first evidence pass): see
docs/research/frontier_census_evidence_2026-07-04.md
"""

from __future__ import annotations

import argparse
import gc
import itertools
import json
import os
import random
import sys
import time
from dataclasses import dataclass

import numpy as np
from numba import njit

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _preflight_null_bytes() -> None:
    """Fail with actionable guidance if working-tree sources contain NUL bytes.

    2026-07-04: gear_optimizer/solver/score_math.py and gear_optimizer/domain/jobs.py
    were found with null-byte tails appended (interrupted write); Python cannot
    import such files. `git diff` shows them modified while `git show HEAD:<file>`
    is clean -- restore with `git checkout -- <file>`.
    """
    suspects = (
        "gear_optimizer/solver/score_math.py",
        "gear_optimizer/domain/jobs.py",
    )
    bad = []
    for rel in suspects:
        p = os.path.join(REPO_ROOT, rel)
        try:
            with open(p, "rb") as fh:
                if b"\x00" in fh.read():
                    bad.append(rel)
        except OSError:
            continue
    if bad:
        raise SystemExit(
            "corrupted source files (null bytes) block imports: "
            + ", ".join(bad)
            + "\nrestore with: git checkout -- " + " ".join(f'"{b}"' for b in bad)
        )


_preflight_null_bytes()

from gear_optimizer.core.constants import MAX_STAT_INDEX, TOTAL_ROWS  # noqa: E402
from gear_optimizer.core.utils import _relevant_row_projection, safe_float, safe_int  # noqa: E402
from gear_optimizer.data.csv_parser import (  # noqa: E402
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.data.song_io import get_base_calc_song  # noqa: E402
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools  # noqa: E402
from gear_optimizer.helpers.song_helpers.ref_array_builder import (  # noqa: E402
    build_ref_arrays_from_stats,
)
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_indices  # noqa: E402
from gear_optimizer.solver.score_math import lookup_reference_py  # noqa: E402
from gear_optimizer.solver.scoring.exact_rescore import (  # noqa: E402
    score_stats_fixed_timing_exact_batch,
)

GA_EVAL_BUDGET = 705 * 125 * 3  # population x generations x multi-start (constants.py)
CAP = int(MAX_STAT_INDEX)  # 160
STATE_HARD_CAP = 12_000_000  # fail-loud level-width guard; raise on big-RAM machines
FT, FF, PP, CM, FM = range(5)  # state column layout


# --------------------------------------------------------------------------- data


def project_rows(rows, p_color, s_color):
    """Rows -> (deltas [N,5]=[FT,FF,PP,CM,FM] int16, V [N] int64 = 2*vp+vs,
    aux [N,2]=(vp,vs) int32), via the repo's own score-relevant projection."""
    n = len(rows)
    deltas = np.zeros((n, 5), dtype=np.int16)
    vp_vs = np.zeros((n, 2), dtype=np.int32)
    for i, row in enumerate(rows):
        pp, cm, fm, ft, ff, vp, vs = _relevant_row_projection(row, p_color, s_color)
        deltas[i] = (ft, ff, pp, cm, fm)
        vp_vs[i] = (vp, vs)
    v = (2 * vp_vs[:, 0].astype(np.int64) + vp_vs[:, 1]).astype(np.int64)
    return deltas, v, vp_vs


@dataclass
class SongContext:
    name: str
    path: str
    calc_song: dict
    ref_arrays: dict
    p_color: str
    s_color: str
    slots: list
    gear_pool: dict
    mini_pool: list


def build_context(song_path, all_gears, all_minis, ref_arrays):
    calc_song = get_base_calc_song(song_path)
    md = calc_song.get("metadata", {}) or {}
    p_color = str(md.get("Primary Color", "")).strip()
    s_color = str(md.get("Secondary Color", "")).strip()
    if not p_color:
        raise ValueError(f"song has no primary color: {song_path}")
    slots = sorted({str(g.get("type")) for g in all_gears})
    if len(slots) != 6:
        raise ValueError(f"expected 6 gear slot types, got {slots}")
    gear_pool, mini_pool, _b, _a, _ = initialize_pools(all_gears, all_minis, p_color, slots, s_color)
    if gear_pool is None or len(mini_pool) < 3:
        raise ValueError(f"pool init failed for {song_path}")
    return SongContext(
        str(md.get("Song Name", os.path.basename(song_path))), song_path, calc_song,
        ref_arrays, p_color, s_color, slots, gear_pool, mini_pool,
    )


# ----------------------------------------------------------------------- DP core


class StateSet:
    """keys5 [N,5] int16 (coords <= CAP), V [N] int64 (=2vp+vs), aux [N,2] int32."""

    __slots__ = ("keys5", "V", "aux")

    def __init__(self, keys5, V, aux):
        self.keys5, self.V, self.aux = keys5, V, aux

    @staticmethod
    def seed():
        return StateSet(np.zeros((1, 5), np.int16), np.zeros(1, np.int64), np.zeros((1, 2), np.int32))

    @staticmethod
    def empty():
        return StateSet(np.zeros((0, 5), np.int16), np.zeros(0, np.int64), np.zeros((0, 2), np.int32))

    def __len__(self):
        return len(self.V)

    def concat(self, other):
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self
        return StateSet(
            np.concatenate([self.keys5, other.keys5]),
            np.concatenate([self.V, other.V]),
            np.concatenate([self.aux, other.aux]),
        )

    def take(self, idx):
        return StateSet(self.keys5[idx], self.V[idx], self.aux[idx])

    def add_item(self, delta5, v, vp_vs):
        return StateSet(
            np.minimum(self.keys5 + delta5[None, :], np.int16(CAP)),
            self.V + int(v),
            self.aux + vp_vs[None, :],
        )

    def expand(self, deltas, v, vp_vs):
        n, m = len(self), len(v)
        if n * m > STATE_HARD_CAP:
            raise MemoryError(f"expansion {n}x{m} exceeds STATE_HARD_CAP")
        si = np.repeat(np.arange(n, dtype=np.int64), m)
        ii = np.tile(np.arange(m, dtype=np.int64), n)
        return StateSet(
            np.minimum(self.keys5[si] + deltas[ii], np.int16(CAP)),
            self.V[si] + v[ii],
            self.aux[si] + vp_vs[ii],
        )


def _pack(keys5):
    k = keys5.astype(np.int64)
    return (((((k[:, 0] << 8) | k[:, 1]) << 8 | k[:, 2]) << 8 | k[:, 3]) << 8) | k[:, 4]


# cache=False deliberately: numba's on-disk cache keys by defining-module name and
# broke when this file was loaded under a different module name (evidence pass).
@njit(cache=False)
def _pareto_keep_kernel(cell, cflip, fflip, V, keep, tree, stamp, stamp_base):
    """Per-cell Pareto ((PP handled by sort order), CM, FM, V) via a 2D Fenwick
    prefix-max over flipped (CM, FM). Input sorted by (cell asc, PP desc, CM desc,
    FM desc, V desc); only earlier rows can dominate. `stamp_base` must strictly
    increase across calls (returned value feeds the next call) -- reusing stamps
    resurrects stale tree entries and silently over-prunes."""
    cur = stamp_base
    n = cell.shape[0]
    size = tree.shape[0]
    i = 0
    while i < n:
        cur += 1
        c0 = cell[i]
        j = i
        while j < n and cell[j] == c0:
            c = cflip[j] + 1
            f = fflip[j] + 1
            best = np.int64(-1)
            a = c
            while a > 0:
                b = f
                while b > 0:
                    if stamp[a, b] == cur and tree[a, b] > best:
                        best = tree[a, b]
                    b -= b & (-b)
                a -= a & (-a)
            if best >= V[j]:
                keep[j] = False
            else:
                a = c
                while a < size:
                    b = f
                    while b < size:
                        if stamp[a, b] != cur or tree[a, b] < V[j]:
                            stamp[a, b] = cur
                            tree[a, b] = V[j]
                        b += b & (-b)
                    a += a & (-a)
            j += 1
        i = j
    return cur


_FEN_TREE = np.full((CAP + 2, CAP + 2), -1, dtype=np.int64)
_FEN_STAMP = np.zeros((CAP + 2, CAP + 2), dtype=np.int64)
_STAMP_COUNTER = [0]

V_BITS = 13
V_MAX = (1 << V_BITS) - 1


def reduce_states(s, pareto):
    """Exact-key dedupe (max-V witness) + per-cell Pareto. Single composite-key
    argsorts keep transient memory ~1/4 of a 5-key lexsort."""
    if len(s) <= 1:
        return s
    if int(s.V.max(initial=0)) > V_MAX:
        raise AssertionError(f"V exceeds composite-key budget ({int(s.V.max())} > {V_MAX})")
    packed = _pack(s.keys5)  # 40 bits
    key1 = (packed << V_BITS) | (V_MAX - s.V)
    order = np.argsort(key1, kind="stable")
    packed = packed[order]
    first = np.ones(len(packed), dtype=bool)
    first[1:] = packed[1:] != packed[:-1]
    sel = order[first]
    del key1, packed, order, first
    s = s.take(sel)
    if not pareto or len(s) <= 1:
        return s
    k5 = s.keys5.astype(np.int64)
    cell = k5[:, FT] * 256 + k5[:, FF]
    key2 = (
        (cell << 37)
        | ((CAP - k5[:, PP]) << 29)
        | ((CAP - k5[:, CM]) << 21)
        | ((CAP - k5[:, FM]) << V_BITS)
        | (V_MAX - s.V)
    )
    order = np.argsort(key2, kind="stable")
    del key2
    s = s.take(order)
    cell = cell[order]
    del order
    keep = np.ones(len(s), dtype=bool)
    _STAMP_COUNTER[0] = _pareto_keep_kernel(
        cell,
        (np.int64(CAP) - s.keys5[:, CM]).astype(np.int64),
        (np.int64(CAP) - s.keys5[:, FM]).astype(np.int64),
        s.V,
        keep, _FEN_TREE, _FEN_STAMP, _STAMP_COUNTER[0],
    )
    return s.take(np.flatnonzero(keep))


@dataclass
class DPResult:
    frontier: object
    gear_widths: list
    gear_raw: list
    wall_s: float
    peak: int = 0


def _mini_subset_dp(start, mini_proj, pareto, hard_cap):
    """Distinct-3 mini subset DP: 0/1 transitions item-by-item, socket layers 0..3
    processed high->low so no item is reused within its own pass."""
    m_deltas, m_v, m_aux = mini_proj
    layers = [start, StateSet.empty(), StateSet.empty(), StateSet.empty()]
    peak = 0
    for i in range(len(m_v)):
        for k in (2, 1, 0):
            if len(layers[k]) == 0:
                continue
            grown = layers[k + 1].concat(layers[k].add_item(m_deltas[i], m_v[i], m_aux[i]))
            peak = max(peak, len(grown))
            if len(grown) > hard_cap:
                raise MemoryError(f"mini layer {k + 1} exceeded STATE_HARD_CAP")
            layers[k + 1] = reduce_states(grown, pareto)
    return layers[3], peak


def run_dp(gear_projs, mini_proj, pareto=True, verbose=False, minis_first=True):
    """Exact DP over the production loadout space. minis_first keeps peaks lower:
    the distinct-3 mini frontier is tiny (hundreds), gear stages then grow toward
    the final width. Ordering does not affect the final frontier (T1)."""
    t0 = time.perf_counter()
    gear_widths, gear_raw = [], []
    peak = 0
    if minis_first:
        cur, peak = _mini_subset_dp(StateSet.seed(), mini_proj, pareto, STATE_HARD_CAP)
        if verbose:
            print(f"    [dp] mini-triple frontier: width={len(cur)}", flush=True)
    else:
        cur = StateSet.seed()
    for deltas, v, vp_vs in gear_projs:
        m = len(v)
        raw_total = len(cur) * m
        gear_raw.append(raw_total)
        chunk_items = max(1, min(m, STATE_HARD_CAP // max(1, len(cur))))
        if len(cur) > 2_000_000:
            chunk_items = 1
        acc = StateSet.empty()
        for a in range(0, m, chunk_items):
            e = min(a + chunk_items, m)
            part = cur.expand(deltas[a:e], v[a:e], vp_vs[a:e])
            peak = max(peak, len(acc) + len(part))
            acc = reduce_states(acc.concat(part), pareto)
            del part
            gc.collect()
        cur = acc
        gear_widths.append(len(cur))
        if verbose:
            print(f"    [dp] gear level {len(gear_widths)}: raw={raw_total} -> width={len(cur)}", flush=True)

    if not minis_first:
        cur, mpeak = _mini_subset_dp(cur, mini_proj, pareto, STATE_HARD_CAP)
        peak = max(peak, mpeak)
    if len(cur) == 0:
        raise ValueError("empty final frontier")
    res = DPResult(cur, gear_widths, gear_raw, time.perf_counter() - t0)
    res.peak = peak
    return res


# ----------------------------------------------------- vectorized census scorer


class CellScorer:
    """Vectorized f64 replica of calculate_score_exact over the chart-time fever
    timeline, identical op order per lane. Bit-parity asserted vs the oracle."""

    def __init__(self, ctx):
        song_data = ctx.calc_song.get("song_data", {}) or {}
        hits = song_data.get("fg_timestamps")
        if hits is None:
            hits = song_data.get("chart_timestamps", song_data.get("timestamps", ()))
        self.hits = np.asarray(hits, dtype=np.float32)
        self.total_notes = int(len(self.hits))
        md = ctx.calc_song.get("metadata", {}) or {}
        self.long_notes = safe_int(md.get("Long Notes"), 0)
        default_last = float(self.hits[-1]) if self.total_notes else 0.0
        self.last_note_time = safe_float(md.get("Last Note Time"), default_last)
        self.ft_axis = ctx.ref_arrays["Fever Time"]
        self.ff_axis = ctx.ref_arrays["Fever Fill Rate"]
        self.pp_axis = np.asarray(ctx.ref_arrays["Perfect Points"], dtype=np.float64)
        self.cm_axis = np.asarray(ctx.ref_arrays["Combo Multiplier"], dtype=np.float64)
        self.fm_axis = np.asarray(ctx.ref_arrays["Fever Multiplier"], dtype=np.float64)
        self.mask_buffer = np.zeros(self.total_notes, dtype=np.bool_)
        self._cache = {}

    def timeline(self, ft, ff):
        key = (int(ft), int(ff))
        got = self._cache.get(key)
        if got is None:
            ft_factor = lookup_reference_py(int(ft), self.ft_axis, TOTAL_ROWS)
            ff_factor = lookup_reference_py(int(ff), self.ff_axis, TOTAL_ROWS)
            mask, nf, nn, _act, _last = calculate_fever_timeline_indices(
                self.hits, self.total_notes, ff_factor, ft_factor,
                self.long_notes, self.last_note_time, self.mask_buffer,
            )
            got = (np.asarray(mask, dtype=np.bool_).copy(), int(nf), int(nn))
            self._cache[key] = got
        return got

    def score_frontier(self, f, chunk=20_000):
        b = f.V.astype(np.float64) + self.pp_axis[np.minimum(f.keys5[:, PP], TOTAL_ROWS)]
        c = self.cm_axis[np.minimum(f.keys5[:, CM], TOTAL_ROWS)]
        fv = self.fm_axis[np.minimum(f.keys5[:, FM], TOTAL_ROWS)]
        out = np.zeros(len(f), dtype=np.int64)
        cells = f.keys5[:, FT] * 256 + f.keys5[:, FF]
        order = np.argsort(cells, kind="stable")
        cs = cells[order]
        starts = np.flatnonzero(np.r_[True, cs[1:] != cs[:-1]])
        ends = np.r_[starts[1:], len(order)]
        for a, e in zip(starts, ends):
            idx = order[a:e]
            ft = int(f.keys5[idx[0], FT]); ff = int(f.keys5[idx[0], FF])
            mask, nf, nn = self.timeline(ft, ff)
            H = int(len(mask))
            pos = np.arange(1, H + 1, dtype=np.float64)
            mrow = mask[None, :]
            for c0 in range(0, len(idx), chunk):
                sel = idx[c0:c0 + chunk]
                bb = b[sel][:, None]; cc = c[sel][:, None]; ffm = fv[sel][:, None]
                combo_val = np.floor(b[sel] * c[sel]).astype(np.int64)
                fever_val = np.floor(b[sel] * c[sel] * fv[sel]).astype(np.int64)
                body = nf * fever_val + nn * combo_val
                scaling = ((cc - 1.0) / 100.0) * pos[None, :] + 1.0
                pv = bb * scaling
                head = np.where(mrow, np.floor(pv * ffm), np.floor(pv)).astype(np.int64).sum(axis=1)
                out[sel] = body + head
        return out


def frontier_stats_rows(f, ctx, idx=None):
    rows = []
    rng_idx = range(len(f)) if idx is None else idx
    for i in rng_idx:
        row = {
            "Fever Time": int(f.keys5[i, FT]), "Fever Fill Rate": int(f.keys5[i, FF]),
            "Perfect Points": int(f.keys5[i, PP]), "Combo Multiplier": int(f.keys5[i, CM]),
            "Fever Multiplier": int(f.keys5[i, FM]), ctx.p_color: int(f.aux[i, 0]),
        }
        if ctx.s_color:
            row[ctx.s_color] = int(f.aux[i, 1])
        rows.append(row)
    return rows


# ------------------------------------------------------------------- evidence


def e1_dominance_completeness(dp, gear_projs, mini_proj, samples, seed):
    rng = random.Random(seed)
    f = dp.frontier
    cell_index = {}
    cells = f.keys5[:, FT] * 256 + f.keys5[:, FF]
    for idx, c in enumerate(cells):
        cell_index.setdefault(int(c), []).append(idx)
    m_deltas, m_v, _ = mini_proj
    n_minis = len(m_v)
    misses = 0
    k5, V = f.keys5, f.V
    for _ in range(samples):
        tot = np.zeros(5, dtype=np.int64)
        v = 0
        for deltas, iv, _aux in gear_projs:
            i = rng.randrange(len(iv))
            tot = np.minimum(tot + deltas[i], CAP)
            v += int(iv[i])
        for i in rng.sample(range(n_minis), 3):
            tot = np.minimum(tot + m_deltas[i], CAP)
            v += int(m_v[i])
        covered = False
        for idx in cell_index.get(int(tot[FT]) * 256 + int(tot[FF]), ()):
            if k5[idx, PP] >= tot[PP] and k5[idx, CM] >= tot[CM] and k5[idx, FM] >= tot[FM] and V[idx] >= v:
                covered = True
                break
        misses += 0 if covered else 1
    return {"samples": samples, "misses": misses}


def e2_scorer_monotonicity(ctx, pairs, seed):
    rng = random.Random(seed)
    rows_lo, rows_hi = [], []
    for _ in range(pairs):
        lo = {
            "Fever Time": rng.randrange(0, CAP + 1), "Fever Fill Rate": rng.randrange(0, CAP + 1),
            "Perfect Points": rng.randrange(0, CAP + 1), "Combo Multiplier": rng.randrange(0, CAP + 1),
            "Fever Multiplier": rng.randrange(0, CAP + 1), ctx.p_color: rng.randrange(0, 400),
        }
        hi = dict(lo)
        hi["Perfect Points"] = min(CAP, lo["Perfect Points"] + rng.randrange(0, 40))
        hi["Combo Multiplier"] = min(CAP, lo["Combo Multiplier"] + rng.randrange(0, 40))
        hi["Fever Multiplier"] = min(CAP, lo["Fever Multiplier"] + rng.randrange(0, 40))
        hi[ctx.p_color] = lo[ctx.p_color] + rng.randrange(0, 80)
        if ctx.s_color:
            lo[ctx.s_color] = rng.randrange(0, 300)
            hi[ctx.s_color] = lo[ctx.s_color] + rng.randrange(0, 80)
        rows_lo.append(lo); rows_hi.append(hi)
    s_lo = score_stats_fixed_timing_exact_batch(rows_lo, ctx.calc_song, ctx.ref_arrays)
    s_hi = score_stats_fixed_timing_exact_batch(rows_hi, ctx.calc_song, ctx.ref_arrays)
    return {"pairs": pairs, "violations": int(sum(1 for a, b in zip(s_lo, s_hi) if b < a))}


def _accumulate(row, item, ctx):
    pp, cm, fm, ft, ff, vp, vs = _relevant_row_projection(item, ctx.p_color, ctx.s_color)
    row["Perfect Points"] = min(CAP, row["Perfect Points"] + pp)
    row["Combo Multiplier"] = min(CAP, row["Combo Multiplier"] + cm)
    row["Fever Multiplier"] = min(CAP, row["Fever Multiplier"] + fm)
    row["Fever Time"] = min(CAP, row["Fever Time"] + ft)
    row["Fever Fill Rate"] = min(CAP, row["Fever Fill Rate"] + ff)
    row[ctx.p_color] = row.get(ctx.p_color, 0) + vp
    # primary == secondary happens on real charts (e.g. Flow/Flow): the color key
    # must be accumulated once, or b doubles to 2*(vp+vs) + (vp+vs) = 6F != 3F.
    if ctx.s_color and ctx.s_color != ctx.p_color:
        row[ctx.s_color] = row.get(ctx.s_color, 0) + vs


def e3_bruteforce_equality(ctx, trials, per_slot, mini_sub, seed):
    rng = random.Random(seed)
    out = []
    for t in range(trials):
        sub_gear = {s: rng.sample(ctx.gear_pool[s], min(per_slot, len(ctx.gear_pool[s]))) for s in ctx.slots}
        sub_minis = rng.sample(ctx.mini_pool, min(mini_sub, len(ctx.mini_pool)))
        zero = {"Fever Time": 0, "Fever Fill Rate": 0, "Perfect Points": 0,
                "Combo Multiplier": 0, "Fever Multiplier": 0, ctx.p_color: 0}
        if ctx.s_color:
            zero[ctx.s_color] = 0
        stats_rows = []
        for gear_combo in itertools.product(*[sub_gear[s] for s in ctx.slots]):
            base = dict(zero)
            for g in gear_combo:
                _accumulate(base, g, ctx)
            for tri in itertools.combinations(sub_minis, 3):
                row = dict(base)
                for mrow in tri:
                    _accumulate(row, mrow, ctx)
                stats_rows.append(row)
        brute_max = max(score_stats_fixed_timing_exact_batch(stats_rows, ctx.calc_song, ctx.ref_arrays))
        gear_projs = [project_rows(sub_gear[s], ctx.p_color, ctx.s_color) for s in ctx.slots]
        mini_proj = project_rows(sub_minis, ctx.p_color, ctx.s_color)
        dp = run_dp(gear_projs, mini_proj)
        dp_max = max(score_stats_fixed_timing_exact_batch(
            frontier_stats_rows(dp.frontier, ctx), ctx.calc_song, ctx.ref_arrays))
        rec = {"trial": t, "enumerated": len(stats_rows), "frontier": len(dp.frontier),
               "brute_max": int(brute_max), "dp_max": int(dp_max),
               "equal": bool(int(brute_max) == int(dp_max))}
        out.append(rec)
        if not rec["equal"]:
            raise AssertionError(f"E3 FAILURE song={ctx.name} trial={t}: {rec}")
    return out


# ------------------------------------------------------------------------- main


def census(ctx, args):
    gear_projs = [project_rows(ctx.gear_pool[s], ctx.p_color, ctx.s_color) for s in ctx.slots]
    mini_proj = project_rows(ctx.mini_pool, ctx.p_color, ctx.s_color)
    dp = run_dp(gear_projs, mini_proj, verbose=args.verbose)
    f = dp.frontier
    cells = f.keys5[:, FT] * 256 + f.keys5[:, FF]
    uniq, counts = np.unique(cells, return_counts=True)

    # score-space collapse: per cell, staircase on (b, CM, FM). This is the set the
    # GPU would actually need to score; PP and V matter only through b at this point.
    ppax = np.asarray(ctx.ref_arrays["Perfect Points"], dtype=np.float64)
    b_val = f.V.astype(np.float64) + ppax[np.minimum(f.keys5[:, PP], TOTAL_ROWS)]
    b_key = np.round(b_val * 4096.0).astype(np.int64)
    cellv = (f.keys5[:, FT].astype(np.int64) * 256 + f.keys5[:, FF]).astype(np.int64)
    order2 = np.lexsort((-b_key, -f.keys5[:, FM], -f.keys5[:, CM], cellv))
    keep2 = np.ones(len(f), dtype=bool)
    _STAMP_COUNTER[0] = _pareto_keep_kernel(
        cellv[order2],
        (np.int64(CAP) - f.keys5[order2, CM]).astype(np.int64),
        (np.int64(CAP) - f.keys5[order2, FM]).astype(np.int64),
        b_key[order2],
        keep2, _FEN_TREE, _FEN_STAMP, _STAMP_COUNTER[0],
    )
    eval_frontier = int(keep2.sum())

    scorer = CellScorer(ctx)
    t0 = time.perf_counter()
    fr_scores = scorer.score_frontier(f)
    eval_wall = time.perf_counter() - t0

    rng = random.Random(args.seed + 7)
    sub = sorted(rng.sample(range(len(f)), min(args.parity_sample, len(f))))
    oracle = score_stats_fixed_timing_exact_batch(frontier_stats_rows(f, ctx, sub), ctx.calc_song, ctx.ref_arrays)
    mismatch = [int(i) for i, o in zip(sub, oracle) if int(fr_scores[i]) != int(o)]
    if mismatch:
        raise AssertionError(f"P FAILURE song={ctx.name}: vectorized scorer mismatch at {mismatch[:5]}")

    e1 = e1_dominance_completeness(dp, gear_projs, mini_proj, args.e1_samples, args.seed)
    e2 = e2_scorer_monotonicity(ctx, args.e2_pairs, args.seed + 1)
    e3 = e3_bruteforce_equality(ctx, args.e3_trials, args.e3_per_slot, args.e3_minis, args.seed + 2)

    res = {
        "song": ctx.name,
        "difficulty_dir": os.path.basename(os.path.dirname(ctx.path)),
        "colors": [ctx.p_color, ctx.s_color],
        "pools": {"gear_per_slot": {s: len(ctx.gear_pool[s]) for s in ctx.slots}, "minis": len(ctx.mini_pool)},
        "raw_space": {
            "gear_product": float(np.prod([float(len(ctx.gear_pool[s])) for s in ctx.slots])),
            "mini_triples": int(len(ctx.mini_pool) * (len(ctx.mini_pool) - 1) * (len(ctx.mini_pool) - 2) // 6),
        },
        "dp": {
            "gear_level_widths": dp.gear_widths,
            "gear_level_raw_expansion": dp.gear_raw,
            "final_frontier": len(f),
            "eval_frontier_bcf_collapse": eval_frontier,
            "distinct_cells": int(len(uniq)),
            "per_cell_width": {"mean": round(float(np.mean(counts)), 2),
                               "p95": round(float(np.percentile(counts, 95)), 2),
                               "max": int(np.max(counts))},
            "peak_states": int(getattr(dp, "peak", 0)),
            "dp_wall_s": round(dp.wall_s, 3),
            "frontier_eval_wall_s": round(eval_wall, 3),
        },
        "vs_ga": {"ga_eval_budget": GA_EVAL_BUDGET,
                  "dp_frontier_over_ga": round(len(f) / GA_EVAL_BUDGET, 4),
                  "eval_frontier_over_ga": round(eval_frontier / GA_EVAL_BUDGET, 4)},
        "best_base_score_fixed_timing": int(np.max(fr_scores)),
        "parity_subsample": len(sub),
        "E1": e1, "E2": e2, "E3": e3,
    }
    if e1["misses"]:
        raise AssertionError(f"E1 FAILURE song={ctx.name}: {e1}")
    if e2["violations"]:
        raise AssertionError(f"E2 FAILURE song={ctx.name}: {e2}")
    return res


def pick_songs(args):
    songs = []
    for dirname, n in (("Easy", args.easy), ("Normal", args.normal), ("Hard", args.hard)):
        d = os.path.join(REPO_ROOT, "Data", dirname)
        if not os.path.isdir(d) or n <= 0:
            continue
        files = sorted(x for x in os.listdir(d) if x.endswith(".txt"))
        songs.extend(os.path.join(d, x) for x in files[:n])
    return songs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--easy", type=int, default=3)
    ap.add_argument("--normal", type=int, default=3)
    ap.add_argument("--hard", type=int, default=3)
    ap.add_argument("--e1-samples", type=int, default=50_000)
    ap.add_argument("--e2-pairs", type=int, default=1_000)
    ap.add_argument("--e3-trials", type=int, default=2)
    ap.add_argument("--e3-per-slot", type=int, default=3)
    ap.add_argument("--e3-minis", type=int, default=6)
    ap.add_argument("--parity-sample", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260704)
    ap.add_argument("--song", action="append", default=[],
                    help="explicit chart path(s); overrides --easy/--normal/--hard")
    ap.add_argument("--max-gear-per-slot", type=int, default=0)
    ap.add_argument("--max-minis", type=int, default=0)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    paths = {"Stats": os.path.join(REPO_ROOT, "Data", "Gear", "Stats.txt")}
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    refs = build_ref_arrays_from_stats(read_table(paths["Stats"]))

    mono = {k: bool(np.all(np.diff(np.asarray(v)) >= 0)) for k, v in refs.items()}
    print("[V1] ref-table nondecreasing:", mono, flush=True)
    for axis in ("Perfect Points", "Combo Multiplier", "Fever Multiplier"):
        if not mono[axis]:
            raise AssertionError(f"V1 FAILURE: dominance axis {axis} is not monotone")

    results = {"V1_ref_monotone": mono, "ga_eval_budget": GA_EVAL_BUDGET, "songs": [], "failures": []}
    song_list = args.song if args.song else pick_songs(args)
    for sp in song_list:
        t0 = time.perf_counter()
        print(f"[song] {os.path.basename(sp)}", flush=True)
        try:
            ctx = build_context(sp, all_gears, all_minis, refs)
            if args.max_gear_per_slot > 0:
                for s in ctx.slots:
                    ctx.gear_pool[s] = ctx.gear_pool[s][: args.max_gear_per_slot]
            if args.max_minis > 0:
                ctx.mini_pool = ctx.mini_pool[: args.max_minis]
            res = census(ctx, args)
            res["total_wall_s"] = round(time.perf_counter() - t0, 3)
            results["songs"].append(res)
            print(json.dumps(res), flush=True)
        except Exception as exc:  # census tooling: record loudly, keep measuring
            results["failures"].append({"song": os.path.basename(sp), "error": repr(exc)})
            print(f"[FAILURE] {os.path.basename(sp)}: {exc!r}", flush=True)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        print(f"wrote {args.out}")
    print(f"\n{len(results['songs'])} songs passed, {len(results['failures'])} failed")
    if results["failures"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
