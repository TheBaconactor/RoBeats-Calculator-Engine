"""K0 Amdahl audit for the Issue #116 GPU kernel assignment.

Measures, on REAL charts and REAL production geometries, how one FG first-frontier
build call splits between:

  1. the reachability/radix PREPASS (states marked, pair_mod sized);
  2. the packet-monoid BODY-TAIL DP (states n-1 .. 100) -- the part a
     state-synchronous GPU wave could take over;
  3. everything after (the HEAD stage, states 99..0, cone filter, surface store).

This is measurement-only research tooling: it never opens a frontier cache, never
writes production state, and reuses the production prep functions so kernel inputs
are byte-identical to what the reducer feeds `_first_frontier_from_precomputed_
end_indices_numba`. The split kernel below copies ONLY the driver's fast-path +
prepass verbatim and then calls the production body-DP semantic owner directly,
so the body work measured IS the production implementation.

Usage:
    python tools/dev/issue116_amdahl_probe.py --song "M1LLI0N PP (Full Version)" --diff Hard
    python tools/dev/issue116_amdahl_probe.py --song "Stars by James" --diff Normal --fts 8 --ffs 8
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from numba import njit  # noqa: E402

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as _rb  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (  # noqa: E402
    _compact_first_frontier_action_arrays,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (  # noqa: E402
    _precompute_end_indices,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (  # noqa: E402
    _early_great_extension_gap_bound,
    _FirstFrontierStampWorkspace,
    _song_first_frontier_pair_mod_bound,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table  # noqa: E402
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes  # noqa: E402

_MODE_PREPASS = 0
_MODE_BODY = 1


@njit(cache=True, nogil=True)
def _probe_prepass_body(
    mode: int,
    n: int,
    action_count: int,
    region_action_count: int,
    raw_fever_fill: float,
    action_k,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    timestamps,
    candidate_high_delta_max,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    prefix_perfect_hit,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hits,
    region_perfect_hits,
    region_perfect_valids,
    ws_pair_values,
    ws_pair_stamps,
    ws_pair_touched,
    ws_bit_values,
    ws_bit_stamps,
    pair_epoch_in: int,
    bit_epoch_in: int,
):
    """Fast-path + reachability prepass copied verbatim from the production driver
    (`_first_frontier_from_precomputed_end_indices_numba`), then a direct call of the
    production `_numba_packet_body_tails_from_precomputed_end_indices` when mode==1.

    Returns (fast_path, states_evaluated, generated_surfaces, retained_total,
    max_state_frontier, reachable_count, pair_mod, pair_epoch, bit_epoch)."""
    # --- fast path (verbatim) ---
    if int(use_forced_great_timing_i) == 0 and int(action_count) > 0 and int(first_fill[0]) >= 100:
        zero_body_fever = _rb._numba_zero_forced_body_fever_precomputed(
            int(n),
            later_fill,
            later_forced,
            first_fill,
            first_forced,
            later_activation_forced,
            first_activation_forced,
            int(use_forced_great_timing_i),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(zero_body_fever) >= 0:
            if int(zero_body_fever) >= max(0, int(n) - 100):
                return (1, 0, 0, 0, 0, 0, 0, int(pair_epoch_in), int(bit_epoch_in))
            max_body_fever = _rb._numba_max_body_fever_precomputed(
                int(n),
                int(action_count),
                later_fill,
                first_fill,
                later_forced,
                first_forced,
                later_activation_forced,
                first_activation_forced,
                int(use_forced_great_timing_i),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                perfect_end_idx,
                great_end_idx,
                great_floor_end_idx,
                int(real_time_idx),
            )
            if int(zero_body_fever) == int(max_body_fever):
                return (1, 0, 0, 0, 0, 0, 0, int(pair_epoch_in), int(bit_epoch_in))

    # --- reachability prepass (verbatim) ---
    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    perfect_activation_processed = np.zeros(int(n), dtype=np.bool_)
    late_activation_processed = np.zeros(int(n), dtype=np.bool_)
    max_eg_width = 0
    for action_idx in range(int(action_count)):
        fill = int(first_fill[int(action_idx)])
        if int(fill) >= int(n):
            continue
        prefix_forced = int(first_activation_forced[int(action_idx)])
        needs_perfect = not perfect_activation_processed[int(fill)]
        needs_late = (
            int(use_forced_great_timing_i) != 0
            and int(prefix_forced) >= 0
            and not late_activation_processed[int(fill)]
        )
        if not needs_perfect and not needs_late:
            continue
        edge_hit = float(prefix_perfect_hit[int(fill)])
        edge_valid = int(prefix_perfect_valid[int(fill)])
        edge_e = -1
        edge_eg_e = 0
        if int(edge_valid) != 0:
            edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(fill)])
            edge_eg_e = int(capped_eg_perfect_e[int(real_time_idx), int(fill)])
        if needs_perfect:
            perfect_activation_processed[int(fill)] = True
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True
                max_eg_width = max(
                    max_eg_width,
                    _rb._numba_mark_early_great_reachable_from_hit(
                        reachable,
                        int(n),
                        int(fill),
                        int(edge_e),
                        float(edge_hit),
                        great_floor_timestamps,
                        float(real_fever_time),
                    ),
                )
        if needs_late:
            late_activation_processed[int(fill)] = True
            activation_hit = float(prefix_late_hit[int(fill)])
            activation_valid = int(prefix_late_valid[int(fill)])
            activation_e = -1
            activation_eg_e = 0
            if int(activation_valid) != 0:
                activation_e = int(capped_late_edge_e[int(real_time_idx), int(fill)])
                activation_eg_e = int(capped_eg_late_e[int(real_time_idx), int(fill)])
            if _rb._numba_late_edge_extends(
                int(edge_e), int(activation_e), int(activation_eg_e), int(edge_eg_e)
            ):
                reachable[int(activation_e)] = True
                max_eg_width = max(
                    max_eg_width,
                    _rb._numba_mark_early_great_reachable_from_hit(
                        reachable,
                        int(n),
                        int(fill),
                        int(activation_e),
                        float(activation_hit),
                        great_floor_timestamps,
                        float(real_fever_time),
                    ),
                )
    if int(use_forced_great_timing_i) != 0:
        max_eg_width = max(
            int(max_eg_width),
            _rb._numba_mark_region_entries_for_section(
                reachable,
                int(n),
                0,
                region_starts,
                region_offsets,
                region_activations,
                region_great_ends,
                region_is_greats,
                region_act_hits,
                region_perfect_hits,
                region_perfect_valids,
                float(real_fever_time),
                perfect_floor_timestamps,
                great_floor_timestamps,
            ),
        )
    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        section_start = int(state_i) + 1
        for action_idx in range(int(action_count)):
            activation = int(state_i) + int(later_fill[int(action_idx)])
            if int(activation) >= int(n):
                continue
            prefix_forced = int(later_activation_forced[int(action_idx)])
            needs_perfect = not perfect_activation_processed[int(activation)]
            needs_late = (
                int(use_forced_great_timing_i) != 0
                and int(prefix_forced) >= 0
                and not late_activation_processed[int(activation)]
            )
            if not needs_perfect and not needs_late:
                continue
            edge_hit = float(prefix_perfect_hit[int(activation)])
            edge_valid = int(prefix_perfect_valid[int(activation)])
            edge_e = -1
            edge_eg_e = 0
            if int(edge_valid) != 0:
                edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
                edge_eg_e = int(capped_eg_perfect_e[int(real_time_idx), int(activation)])
            if needs_perfect:
                perfect_activation_processed[int(activation)] = True
                if int(edge_e) >= 0:
                    reachable[int(edge_e)] = True
                    max_eg_width = max(
                        max_eg_width,
                        _rb._numba_mark_early_great_reachable_from_hit(
                            reachable,
                            int(n),
                            int(activation),
                            int(edge_e),
                            float(edge_hit),
                            great_floor_timestamps,
                            float(real_fever_time),
                        ),
                    )
            if needs_late:
                late_activation_processed[int(activation)] = True
                activation_hit = float(prefix_late_hit[int(activation)])
                activation_valid = int(prefix_late_valid[int(activation)])
                activation_e = -1
                activation_eg_e = 0
                if int(activation_valid) != 0:
                    activation_e = int(capped_late_edge_e[int(real_time_idx), int(activation)])
                    activation_eg_e = int(capped_eg_late_e[int(real_time_idx), int(activation)])
                if _rb._numba_late_edge_extends(
                    int(edge_e), int(activation_e), int(activation_eg_e), int(edge_eg_e)
                ):
                    reachable[int(activation_e)] = True
                    max_eg_width = max(
                        max_eg_width,
                        _rb._numba_mark_early_great_reachable_from_hit(
                            reachable,
                            int(n),
                            int(activation),
                            int(activation_e),
                            float(activation_hit),
                            great_floor_timestamps,
                            float(real_fever_time),
                        ),
                    )
        if int(use_forced_great_timing_i) != 0:
            max_eg_width = max(
                int(max_eg_width),
                _rb._numba_mark_region_entries_for_section(
                    reachable,
                    int(n),
                    int(section_start),
                    region_starts,
                    region_offsets,
                    region_activations,
                    region_great_ends,
                    region_is_greats,
                    region_act_hits,
                    region_perfect_hits,
                    region_perfect_valids,
                    float(real_fever_time),
                    perfect_floor_timestamps,
                    great_floor_timestamps,
                ),
            )

    # --- radix sizing (verbatim) ---
    min_later_fill = max(1, int(later_fill[0]) if int(action_count) > 0 else 1)
    section_bound = int(n) // int(min_later_fill) + 4
    pair_mod = min(int(n) + 1, int(section_bound) * (1 + int(max_eg_width)) + 1)
    pair_size = (int(n) + 1) * int(pair_mod)
    if (
        int(ws_pair_values.shape[0]) < int(pair_size)
        or int(ws_pair_stamps.shape[0]) < int(pair_size)
        or int(ws_pair_touched.shape[0]) < int(pair_size)
        or int(ws_bit_values.shape[0]) < int(pair_mod) + 1
        or int(ws_bit_stamps.shape[0]) < int(pair_mod) + 1
    ):
        raise ValueError("probe stamp workspace undersized for this geometry's pair radix")

    reachable_count = 0
    for state_i in range(int(n) + 1):
        if reachable[state_i]:
            reachable_count += 1

    if int(mode) == 0:
        return (0, 0, 0, 0, 0, int(reachable_count), int(pair_mod), int(pair_epoch_in), int(bit_epoch_in))

    best_fever_by_pair = ws_pair_values[: int(pair_size)]
    pair_stamp = ws_pair_stamps[: int(pair_size)]
    touched_pair = ws_pair_touched[: int(pair_size)]
    bit_values = ws_bit_values[: int(pair_mod) + 1]
    bit_stamps = ws_bit_stamps[: int(pair_mod) + 1]

    (
        _body_values,
        _body_starts,
        _body_counts,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        pair_stamp_value,
        bit_stamp_value,
    ) = _rb._numba_packet_body_tails_from_precomputed_end_indices(
        int(n),
        int(action_count),
        int(region_action_count),
        float(raw_fever_fill),
        action_k,
        later_fill,
        later_forced,
        later_activation_forced,
        reachable,
        int(use_forced_great_timing_i),
        timestamps,
        candidate_high_delta_max,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
        great_floor_timestamps,
        lanes,
        region_starts,
        region_offsets,
        region_activations,
        region_great_ends,
        region_is_greats,
        region_act_hits,
        region_perfect_hits,
        region_perfect_valids,
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
        float(real_fever_time),
        int(real_time_idx),
        int(pair_mod),
        best_fever_by_pair,
        pair_stamp,
        touched_pair,
        int(pair_epoch_in),
        bit_values,
        bit_stamps,
        int(bit_epoch_in),
    )
    return (
        0,
        int(states_evaluated),
        int(generated_surfaces),
        int(retained_total),
        int(max_state_frontier),
        int(reachable_count),
        int(pair_mod),
        int(pair_stamp_value),
        int(bit_stamp_value),
    )


def _load_ref_arrays():
    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.constants import PATHS
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats

    paths_cache = load_paths_cache() or {}
    stats_path = str((paths_cache.get("Stats") or PATHS.stats_csv) or "").strip()
    if not stats_path or not os.path.exists(stats_path):
        raise SystemExit(f"cannot find Stats table at {stats_path!r}")
    return build_ref_arrays_from_stats(read_table(stats_path), dtype=np.float32)


def _find_chart(song: str, diff: str) -> str:
    pattern = str(REPO / "Data" / diff / "*.txt")
    hits = [p for p in sorted(glob.glob(pattern)) if song.lower() in os.path.basename(p).lower()]
    if not hits:
        raise SystemExit(f"no chart matching {song!r} under Data/{diff}/")
    if len(hits) > 1:
        print(f"note: {len(hits)} matches, using first: {os.path.basename(hits[0])}")
    return hits[0]


class SongProbeInputs:
    """Byte-identical kernel inputs for a strided sample of one song's real geometries.

    Mirrors the reducer/scheduler prep exactly (same production prep functions in the
    same order); shared by the Amdahl probe and the post-body phase-split probe."""

    def __init__(self, *, chart: str, diff: str, fts: int, ffs: int) -> None:
        from gear_optimizer.data.song_io import get_base_calc_song
        from gear_optimizer.solver.timing_envelope import apply_timing_envelope

        ref_arrays = _load_ref_arrays()
        calc_song = get_base_calc_song(chart, {})
        if not calc_song:
            raise SystemExit(f"failed to load chart {chart!r}")
        apply_timing_envelope(calc_song)

        song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft = _response_axes(
            calc_song, ref_arrays
        )
        self.chart = chart
        self.ts = np.ascontiguousarray(np.asarray(song_inputs.timestamps, dtype=np.float32).reshape(-1))
        self.n = int(self.ts.shape[0])
        self.perfect_ts = np.ascontiguousarray(
            np.asarray(song_inputs.perfect_candidates, dtype=np.float32).reshape(-1)
        )
        self.great_ts = np.ascontiguousarray(
            np.asarray(song_inputs.great_candidates, dtype=np.float32).reshape(-1)
        )
        self.floor_ts = np.ascontiguousarray(
            np.asarray(song_inputs.perfect_floor, dtype=np.float32).reshape(-1)
        )
        self.great_floor_ts = np.ascontiguousarray(
            np.asarray(song_inputs.great_floor, dtype=np.float32).reshape(-1)
        )
        self.lane_arr = np.ascontiguousarray(np.asarray(song_inputs.lanes, dtype=np.int32).reshape(-1))
        self.uft = bool(song_inputs.use_forced_great_timing)
        total_rows = int(raw_fill_by_ff.shape[0]) - 1

        ft_idx = np.unique(np.linspace(0, total_rows, num=max(1, fts), dtype=np.int64))
        ff_idx = np.unique(np.linspace(0, total_rows, num=max(1, ffs), dtype=np.int64))
        geoms: dict[tuple, tuple] = {}
        for ft in ft_idx:
            for ff in ff_idx:
                key = (
                    float(raw_fill_by_ff[ff]),
                    int(non_fever_base_by_ff[ff]),
                    float(real_time_by_ft[ft]),
                )
                geoms.setdefault(key, key)
        self.geometry_rows = list(geoms.values())

        self.candidate_high_delta_max = float(
            np.float32(
                max(0.0, float(np.max(np.maximum(self.perfect_ts, self.great_ts) - self.ts))) + 1.0e-6
            )
        )
        (
            self.prefix_perfect_hit,
            self.prefix_perfect_valid,
            self.prefix_late_hit,
            self.prefix_late_valid,
        ) = _rb._numba_build_prefix_activation_hit_tables(self.n, self.ts, self.perfect_ts, self.great_ts)

        self.prepared = []
        action_cache: dict[tuple, tuple] = {}
        for raw_fill, nfb, rft in self.geometry_rows:
            akey = (float(raw_fill), int(nfb), self.uft)
            arrs = action_cache.get(akey)
            if arrs is None:
                actions, later_fill, first_fill, later_forced, first_forced = _action_table(
                    raw_fever_fill=float(raw_fill),
                    non_fever_base=int(nfb),
                    use_forced_great_timing=self.uft,
                )
                arrs = _compact_first_frontier_action_arrays(
                    actions, later_fill, first_fill, later_forced, first_forced, float(raw_fill)
                )
                action_cache[akey] = arrs
            self.prepared.append((0, int(nfb), float(raw_fill), float(rft), *arrs))

        real_times = np.asarray([float(g[3]) for g in self.prepared], dtype=np.float32)
        (
            self.real_time_index,
            self.timestamp_end_idx,
            self.perfect_end_idx,
            self.great_end_idx,
            self.great_floor_end_idx,
            self.capped_perfect_edge_e,
            self.capped_late_edge_e,
            self.capped_eg_perfect_e,
            self.capped_eg_late_e,
        ) = _precompute_end_indices(
            timestamps=self.ts,
            perfect_candidate_timestamps=self.perfect_ts,
            great_candidate_timestamps=self.great_ts,
            perfect_floor_timestamps=self.floor_ts,
            great_floor_timestamps=self.great_floor_ts,
            prefix_perfect_hit=self.prefix_perfect_hit,
            prefix_late_hit=self.prefix_late_hit,
            lanes=self.lane_arr,
            real_times=real_times,
        )

        self.pair_mod_bound = _song_first_frontier_pair_mod_bound(
            n=self.n,
            prepared=self.prepared,
            eg_gap_bound=_early_great_extension_gap_bound(self.floor_ts, self.great_floor_ts),
        )
        self.ws = _FirstFrontierStampWorkspace(
            (self.n + 1) * int(self.pair_mod_bound),
            int(self.pair_mod_bound) + 1,
            (int(self.pair_mod_bound) + 1) * (self.n + 2),
        )
        self._region_cache: dict[tuple, tuple] = {}
        self.region_build_s = 0.0

    def region_table_for(self, raw_fill: float, nfb: int, action_k) -> tuple:
        if not self.uft:
            return (
                np.zeros(self.n + 2, dtype=np.int64),
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.float64),
                np.empty(0, dtype=np.float64),
                np.empty(0, dtype=np.int32),
            )
        rkey = (float(raw_fill), int(nfb))
        table = self._region_cache.get(rkey)
        if table is None:
            t0 = time.perf_counter()
            table = _rb._numba_build_region_core_table(
                self.n,
                int(action_k.shape[0]),
                np.ascontiguousarray(action_k, dtype=np.int32),
                float(raw_fill),
                self.ts,
                self.candidate_high_delta_max,
                self.floor_ts,
                self.perfect_ts,
                self.great_floor_ts,
                self.great_ts,
                self.lane_arr,
            )
            self.region_build_s += time.perf_counter() - t0
            self._region_cache[rkey] = table
        return table


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True)
    ap.add_argument("--diff", default="Hard", choices=("Easy", "Normal", "Hard"))
    ap.add_argument("--fts", type=int, default=6, help="fever-time samples strided over the FT axis")
    ap.add_argument("--ffs", type=int, default=6, help="fever-fill samples strided over the FF axis")
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    chart = _find_chart(args.song, args.diff)
    sp = SongProbeInputs(chart=chart, diff=args.diff, fts=args.fts, ffs=args.ffs)
    n = sp.n
    uft = sp.uft
    ts = sp.ts
    perfect_ts = sp.perfect_ts
    great_ts = sp.great_ts
    floor_ts = sp.floor_ts
    great_floor_ts = sp.great_floor_ts
    lane_arr = sp.lane_arr
    candidate_high_delta_max = sp.candidate_high_delta_max
    prefix_perfect_hit = sp.prefix_perfect_hit
    prefix_perfect_valid = sp.prefix_perfect_valid
    prefix_late_hit = sp.prefix_late_hit
    prefix_late_valid = sp.prefix_late_valid
    prepared = sp.prepared
    real_time_index = sp.real_time_index
    timestamp_end_idx = sp.timestamp_end_idx
    perfect_end_idx = sp.perfect_end_idx
    great_end_idx = sp.great_end_idx
    great_floor_end_idx = sp.great_floor_end_idx
    capped_perfect_edge_e = sp.capped_perfect_edge_e
    capped_late_edge_e = sp.capped_late_edge_e
    capped_eg_perfect_e = sp.capped_eg_perfect_e
    capped_eg_late_e = sp.capped_eg_late_e
    ws = sp.ws
    region_table_for = sp.region_table_for
    print(
        f"chart={os.path.basename(chart)} n={n} uft={uft} -> {len(prepared)} unique geometries"
    )
    print(f"pair_mod_bound={sp.pair_mod_bound} workspace={ws.total_bytes / 2**20:.1f} MiB")

    def run_full(item, rt_idx: int, region_table) -> tuple[float, tuple]:
        t0 = time.perf_counter()
        (
            rows,
            se,
            gs,
            rt_ct,
            msf,
            pair_epoch,
            bit_epoch,
            branch_a_epoch,
        ) = _rb._first_frontier_from_precomputed_end_indices_numba(
            n,
            int(item[5].shape[0]),
            int(item[4].shape[0]),
            float(item[2]),
            item[4],
            item[5],
            item[6],
            item[7],
            item[8],
            item[9],
            item[10],
            ts,
            candidate_high_delta_max,
            perfect_ts,
            great_ts,
            floor_ts,
            great_floor_ts,
            lane_arr,
            prefix_perfect_hit,
            prefix_perfect_valid,
            prefix_late_hit,
            prefix_late_valid,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            capped_perfect_edge_e,
            capped_late_edge_e,
            capped_eg_perfect_e,
            capped_eg_late_e,
            float(item[3]),
            int(rt_idx),
            1 if uft else 0,
            int(_rb._HEAD_FILTER_MIN_SURFACES),
            region_table[0],
            region_table[1],
            region_table[2],
            region_table[3],
            region_table[4],
            region_table[5],
            region_table[6],
            region_table[7],
            ws.pair_values,
            ws.pair_stamps,
            ws.pair_touched,
            ws.bit_values,
            ws.bit_stamps,
            ws.branch_a_values,
            ws.branch_a_stamps,
            int(ws.pair_epoch),
            int(ws.bit_epoch),
            int(ws.branch_a_epoch),
        )
        elapsed = time.perf_counter() - t0
        ws.store_epochs(int(pair_epoch), int(bit_epoch), int(branch_a_epoch))
        return elapsed, (int(rows.shape[0]), int(se), int(gs), int(rt_ct), int(msf))

    def run_probe(mode: int, item, rt_idx: int, region_table) -> tuple[float, tuple]:
        t0 = time.perf_counter()
        out = _probe_prepass_body(
            int(mode),
            n,
            int(item[5].shape[0]),
            int(item[4].shape[0]),
            float(item[2]),
            item[4],
            item[5],
            item[6],
            item[7],
            item[8],
            item[9],
            item[10],
            ts,
            candidate_high_delta_max,
            perfect_ts,
            great_ts,
            floor_ts,
            great_floor_ts,
            lane_arr,
            prefix_perfect_hit,
            prefix_perfect_valid,
            prefix_late_hit,
            prefix_late_valid,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            capped_perfect_edge_e,
            capped_late_edge_e,
            capped_eg_perfect_e,
            capped_eg_late_e,
            float(item[3]),
            int(rt_idx),
            1 if uft else 0,
            region_table[0],
            region_table[1],
            region_table[2],
            region_table[3],
            region_table[4],
            region_table[5],
            region_table[6],
            region_table[7],
            ws.pair_values,
            ws.pair_stamps,
            ws.pair_touched,
            ws.bit_values,
            ws.bit_stamps,
            int(ws.pair_epoch),
            int(ws.bit_epoch),
        )
        elapsed = time.perf_counter() - t0
        ws.pair_epoch = int(out[7])
        ws.bit_epoch = int(out[8])
        return elapsed, out

    # JIT warmup on the first geometry (uncounted).
    warm_item = prepared[0]
    warm_table = region_table_for(float(warm_item[2]), int(warm_item[1]), warm_item[4])
    run_full(warm_item, int(real_time_index[0]), warm_table)[0]
    run_probe(_MODE_PREPASS, warm_item, int(real_time_index[0]), warm_table)
    run_probe(_MODE_BODY, warm_item, int(real_time_index[0]), warm_table)

    total_full = total_body = total_prepass = 0.0
    region_build_s = 0.0
    sum_states = sum_generated = sum_retained = 0
    sum_head_generated = sum_head_retained = sum_first_rows = 0
    max_frontier = 0
    fast_paths = 0
    per_geom = []
    for gi, item in enumerate(prepared):
        rt_idx = int(real_time_index[gi])
        rt0 = time.perf_counter()
        region_table = region_table_for(float(item[2]), int(item[1]), item[4])
        region_build_s += time.perf_counter() - rt0

        t_full, prod_counters = min(
            (run_full(item, rt_idx, region_table) for _ in range(args.reps)), key=lambda x: x[0]
        )
        t_pre, _ = min(
            (run_probe(_MODE_PREPASS, item, rt_idx, region_table) for _ in range(args.reps)),
            key=lambda x: x[0],
        )
        t_body, out = min(
            (run_probe(_MODE_BODY, item, rt_idx, region_table) for _ in range(args.reps)),
            key=lambda x: x[0],
        )
        fast, se, gs, rt_count, msf, reach, pair_mod, _pe, _be = out
        fast_paths += int(fast)
        total_full += t_full
        total_body += t_body
        total_prepass += t_pre
        sum_states += int(se)
        sum_generated += int(gs)
        sum_retained += int(rt_count)
        max_frontier = max(max_frontier, int(msf))
        head_generated = int(prod_counters[2]) - int(gs)
        head_retained = int(prod_counters[3]) - int(rt_count)
        sum_head_generated += head_generated
        sum_head_retained += head_retained
        sum_first_rows += int(prod_counters[0])
        per_geom.append(
            (
                t_full,
                t_body,
                t_pre,
                int(se),
                int(gs),
                int(rt_count),
                int(reach),
                int(pair_mod),
                head_generated,
                head_retained,
                int(prod_counters[0]),
            )
        )

    head_s = total_full - total_body
    body_only_s = total_body - total_prepass
    print(f"\n=== Amdahl split over {len(prepared)} geometries (min of {args.reps} reps each) ===")
    print(f"  full kernel     : {total_full:8.3f} s")
    print(
        f"  prepass         : {total_prepass:8.3f} s  ({100.0 * total_prepass / max(total_full, 1e-12):5.1f}%)"
    )
    print(
        f"  body-tail DP    : {body_only_s:8.3f} s  ({100.0 * body_only_s / max(total_full, 1e-12):5.1f}%)"
    )
    print(
        f"  head stage+rest : {head_s:8.3f} s  ({100.0 * head_s / max(total_full, 1e-12):5.1f}%)"
    )
    print(f"  region tables   : {region_build_s:8.3f} s (build, cached per key; NOT in full-kernel time)")
    print(f"  fast-path geoms : {fast_paths}")
    if sum_states:
        print("\n=== body-DP shape (wave-design inputs) ===")
        print(f"  states evaluated (sum)      : {sum_states:,}")
        print(f"  candidate touches (sum)     : {sum_generated:,}")
        print(f"  retained rows (sum)         : {sum_retained:,}")
        print(f"  candidates/state (avg)      : {sum_generated / sum_states:8.2f}")
        print(f"  retained/state (avg)        : {sum_retained / sum_states:8.2f}")
        print(f"  max state frontier          : {max_frontier}")
    print("\n=== head-stage shape ===")
    print(f"  head generated surfaces (sum): {sum_head_generated:,}")
    print(f"  head retained surfaces (sum) : {sum_head_retained:,}")
    print(f"  first-frontier rows (sum)    : {sum_first_rows:,}")
    slowest = sorted(per_geom, key=lambda r: -r[0])[:5]
    print(
        "\n  slowest geometries (t_full, t_body, t_pre, states, body_touch, body_ret, reach, pmod, head_gen, head_ret, first_rows):"
    )
    for row in slowest:
        print(
            f"    {row[0]:7.3f} {row[1]:7.3f} {row[2]:7.3f} {row[3]:8,} {row[4]:11,} {row[5]:9,} "
            f"{row[6]:6,} {row[7]:5} {row[8]:11,} {row[9]:9,} {row[10]:7,}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
