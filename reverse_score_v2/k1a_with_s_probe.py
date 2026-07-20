"""K1.a-with-S probe on a real leaderboard row (Gateway top-1).

Handoff §16.10 gate: invert a real (S, N, P, A) row under the IFF
row predicate with S+P (not P-only), and emit the required telemetry
including the fiber-only lower bound on K.

Real row (dump corpus, worklog-validated naked fingerprint):
  Gateway Normal -- Temmie013_TH
  S=19,879,361  N=486,097  P=5834  A=1.0

This probe:
1. Loads the chart, verifies naked bit-exact match.
2. Confirms a feasible 7-dim residual witness for (S, P) under the
   corrected same-primary/secondary color projection.
3. Compiles witness-local predicate-branch telemetry (full hi=104
   plateau^3 compile is research-cap territory; see report).
4. Runs the fiber-multiplicity lower-bound probe on this chart's mini
   relation (16 samples) and records worst/geo-mean K_lower.
5. Runs full-DomainIR P-only backward recurrence until the honest 1M
   cap (expected wall at a mini layer).
6. Runs a reduced-domain completing S+P weighted count on a labeled
   synth sample (machinery proof + exact K on a closed domain).
7. Projects search work against K1.b rho_transition / rho_sort.
8. Writes ``artifacts/k1a_with_s_probe.json`` and prints a verdict.

Usage:
    python -m reverse_score_v2.k1a_with_s_probe
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.data.mini_scaling import extract_pet_info
from gear_optimizer.data.upgrades import extract_upgrade_defs
from gear_optimizer.solver.scoring.exact_rescore import (
    ExactScoreIR,
    _replay_cell,
    build_exact_score_ir,
    score_stats_exact,
)
from reverse_score_v2.domain import MiniState, build_tables
from reverse_score_v2.domain_ir import (
    Axis,
    AxisOption,
    DomainIR,
    _compute_suffix_bounds,
    _finalize_axis,
    build_domain_ir,
)
from reverse_score_v2.domain_spec import DomainSpec
from reverse_score_v2.mini_factored import build_mini_relation
from reverse_score_v2.mini_fiber_lower_bound import (
    K_CONCERNING,
    run_probe as run_fiber_probe,
)
from reverse_score_v2.oracle import SongOracle, resolve_chart
from reverse_score_v2.row_predicate import (
    observables_from_stats7,
)
from reverse_score_v2.state_volume_probe import (
    BYTES_PER_STATE,
    CAP,
    _backward_recurrence,
)
from reverse_score_v2.synth import generate
from reverse_score_v2.weighted_recurrence import root_k

# Gateway top-1 dump row (Temmie013_TH). Naked fingerprint validated
# bit-exact against the chart in the v2 worklog.
GATEWAY_S: int = 19_879_361
GATEWAY_N: int = 486_097
GATEWAY_P: int = 5834
GATEWAY_A: float = 1.0

# Feasible residual witness found by P-conserving search (Chill mass in
# both primary and secondary slots -- ExactScoreIR base_int = 3*c).
GATEWAY_WITNESS: np.ndarray = np.array(
    [624, 624, 104, 96, 68, 68, 82], dtype=np.int32
)

# K1.b measured rates (artifacts/k1b_gpu_primitive_probe.json).
K1B_RHO_TRANSITION: float = 7.42e9
K1B_RHO_SORT: float = 1.61e8
K1B_T_DISPATCH_S: float = 181e-6

# Explicit-output contract ceiling and preferred GA-like budget.
BUDGET_CEILING_S: float = 20.0
BUDGET_PREFERRED_S: float = 5.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _webport_root() -> Path:
    env_root = os.environ.get("ROBEATS_DECOMPILED_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(
        r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/"
        r"SavedGame_706824758/ReplicatedStorage"
    )


def _load_k1b_rates(repo: Path) -> dict[str, float]:
    path = repo / "artifacts" / "k1b_gpu_primitive_probe.json"
    if not path.is_file():
        return {
            "rho_transition": K1B_RHO_TRANSITION,
            "rho_sort": K1B_RHO_SORT,
            "t_dispatch_s": K1B_T_DISPATCH_S,
            "source": "hardwired_defaults",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "rho_transition": float(data["rho_transition"]),
        "rho_sort": float(data["rho_sort"]),
        "t_dispatch_s": float(data["t_dispatch_us"]) * 1e-6,
        "source": str(path),
    }


@dataclass(frozen=True, slots=True)
class WitnessBranchTelemetry:
    """Branches that cover the Gateway witness under a stated residual box."""

    residual_box_hi: int
    covering_branch_count: int
    residual_basis: tuple[str, ...]
    exact_pins: tuple[tuple[str, int], ...]
    base_int_values_count: int
    compile_seconds: float
    note: str


def _witness_branch_telemetry(
    ir: ExactScoreIR,
    witness: np.ndarray,
    *,
    target_s: int,
    song_colors: tuple[str, ...],
) -> WitnessBranchTelemetry:
    """Exact branch covering the witness (FT/FF + plateaus pinned).

    Full §16.3 plateau^3 x FT/FF enumeration at hi≈104 is research-cap
    territory on this row; the gate still requires branch telemetry, so
    we report the exact covering branch for the known feasible witness
    and state the compile limitation loudly.
    """
    t0 = time.perf_counter()
    v = np.asarray(witness, dtype=np.int64).reshape(-1)
    primary, secondary = int(v[0]), int(v[1])
    pp, cm, fm, ft, ff = (int(v[2]), int(v[3]), int(v[4]), int(v[5]), int(v[6]))
    hi = max(pp, cm, fm, ft, ff)
    if hi > TOTAL_ROWS:
        raise ValueError(f"witness mains exceed TOTAL_ROWS={TOTAL_ROWS}: {hi}")

    base = 2 * primary + secondary
    base_grid = np.arange(0, base + 1, dtype=np.int64)
    pp_f = np.full(base_grid.shape, float(ir.pp_table[pp]))
    cm_f = np.full(base_grid.shape, float(ir.cm_table[cm]))
    fm_f = np.full(base_grid.shape, float(ir.fm_table[fm]))
    scores = _replay_cell(
        ir,
        ft_i=ft,
        ff_i=ff,
        base_int=base_grid,
        pp_factor=pp_f,
        combo_mul=cm_f,
        fever_mul=fm_f,
    )
    hit = base_grid[scores == int(target_s)]
    elapsed = time.perf_counter() - t0
    covering = 1 if base in set(int(x) for x in hit.tolist()) else 0
    basis = (
        ("primary", "secondary", "pp", "cm", "fm")
        if len(song_colors) == 2
        else ("primary", "pp", "cm", "fm")
    )
    return WitnessBranchTelemetry(
        residual_box_hi=hi,
        covering_branch_count=covering,
        residual_basis=basis,
        exact_pins=(("ft", ft), ("ff", ff)),
        base_int_values_count=int(hit.size),
        compile_seconds=elapsed,
        note=(
            "witness-local branch only; full plateau^3 x FT/FF compile at "
            f"hi={hi} exceeds research-cap for this probe and is not claimed "
            "as the exact global branch count"
        ),
    )


def _filter_domain_ir_for_synth(
    ir: DomainIR,
    *,
    keep_mini_labels: set[tuple],
    keep_upgrade_uids: set[int],
    upgrade_max: int,
    gem_max: int,
    gear_by_slot: dict[str, str | None],
    gear_named_cap: int = 2,
) -> DomainIR:
    """Tight reduced DomainIR for a labeled synth completing track."""
    new_axes: list[Axis] = []
    for axis in ir.axes:
        kept: list[AxisOption] = []
        if axis.name.startswith("mini:"):
            for opt in axis.options:
                if opt.label[1] is None or opt.label in keep_mini_labels:
                    kept.append(opt)
        elif axis.name.startswith("upgrade:"):
            uid = int(axis.options[0].label[1])
            for opt in axis.options:
                count = int(opt.label[3])
                if uid in keep_upgrade_uids:
                    if count <= upgrade_max:
                        kept.append(opt)
                elif count == 0:
                    kept.append(opt)
        elif axis.name.startswith("gem:"):
            for opt in axis.options:
                if axis.name == "gem:elemental":
                    count = int(opt.label[3])
                else:
                    count = int(opt.label[2])
                if count <= gem_max:
                    kept.append(opt)
        elif axis.name.startswith("gear:"):
            slot = axis.name.split(":", 1)[1]
            truth_name = gear_by_slot.get(slot)
            kept = [axis.options[0]]
            named = list(axis.options[1:])
            if truth_name is not None:
                for opt in named:
                    if opt.label[2] == truth_name:
                        kept.append(opt)
                        break
            for opt in named:
                if len(kept) >= 1 + gear_named_cap:
                    break
                if opt not in kept:
                    kept.append(opt)
        elif axis.name == "team_buff":
            # Keep only the zero / NONE option for the light completing track.
            kept = [axis.options[0]]
        else:
            kept = list(axis.options)
        if not kept:
            raise RuntimeError(f"filtered axis {axis.name} has zero options")
        new_axes.append(_finalize_axis(axis.name, tuple(kept)))

    axes_list = list(new_axes)
    _compute_suffix_bounds(axes_list, ir.pw)
    option_mats = tuple(
        np.stack([opt.vec for opt in axis.options], axis=0).astype(np.int32)
        for axis in axes_list
    )
    return DomainIR(
        axes=tuple(axes_list),
        pw=ir.pw.copy(),
        p_target_axis=-1,
        song_colors=ir.song_colors,
        option_mats=option_mats,
        layer_names=tuple(a.name for a in axes_list),
        upgrade_total_max=min(ir.upgrade_total_max, upgrade_max * max(1, len(keep_upgrade_uids))),
        gem_max_per_type=gem_max,
        upgrade_max_per_type=upgrade_max,
        pet_defs=ir.pet_defs,
        upgrade_defs=ir.upgrade_defs,
        mini_rows=ir.mini_rows,
        gear_rows=ir.gear_rows,
        gem_elemental_colors=ir.gem_elemental_colors,
    )


def main() -> int:
    repo = _repo_root()
    webport = _webport_root()
    if not webport.is_dir():
        print(f"ERROR: webport_root not found: {webport}", file=sys.stderr)
        return 2

    print("=" * 72)
    print("K1.a-with-S — Gateway top-1 real row")
    print("=" * 72)

    chart = resolve_chart(repo / "Data", "Gateway", "Normal")
    oracle = SongOracle(chart)
    print(f"chart: {chart.name}")
    print(f"song_display: {oracle.song_display}")
    print(f"song_colors: {oracle.song_colors}")
    naked = oracle.naked_score()
    print(f"naked: {naked:,}  (dump N={GATEWAY_N:,})")
    if naked != GATEWAY_N:
        print("ERROR: naked fingerprint mismatch — refusing to continue", file=sys.stderr)
        return 2

    refs = _get_team_buff_ref_arrays_cached()
    exact_ir = build_exact_score_ir(oracle.calc_song, refs)

    # --- Witness feasibility ------------------------------------------------
    s_w, n_w, p_w, a_w = observables_from_stats7(
        exact_ir,
        GATEWAY_WITNESS,
        song_colors=oracle.song_colors,
        naked_score=naked,
    )
    print()
    print(f"witness vec: {GATEWAY_WITNESS.tolist()}")
    print(f"witness (S,N,P,A): ({s_w:,}, {n_w:,}, {p_w}, {a_w})")
    witness_ok = (
        s_w == GATEWAY_S and n_w == GATEWAY_N and p_w == GATEWAY_P and a_w == GATEWAY_A
    )
    print(f"witness matches dump row: {witness_ok}")
    if not witness_ok:
        print("ERROR: witness does not reproduce dump observables", file=sys.stderr)
        return 2
    # Cross-check dict path
    stats_dict = {
        "Chill": int(GATEWAY_WITNESS[0]),
        "Perfect Points": int(GATEWAY_WITNESS[2]),
        "Combo Multiplier": int(GATEWAY_WITNESS[3]),
        "Fever Multiplier": int(GATEWAY_WITNESS[4]),
        "Fever Time": int(GATEWAY_WITNESS[5]),
        "Fever Fill Rate": int(GATEWAY_WITNESS[6]),
    }
    s_exact = int(score_stats_exact(stats_dict, oracle.calc_song, refs))
    print(f"score_stats_exact cross-check: {s_exact:,}  match={s_exact == GATEWAY_S}")

    branch_tel = _witness_branch_telemetry(
        exact_ir,
        GATEWAY_WITNESS,
        target_s=GATEWAY_S,
        song_colors=oracle.song_colors,
    )
    print()
    print("predicate-branch telemetry (witness-local):")
    print(f"  covering_branch_count: {branch_tel.covering_branch_count}")
    print(f"  residual_basis: {branch_tel.residual_basis}")
    print(f"  exact_pins: {branch_tel.exact_pins}")
    print(f"  base_int hits in cell: {branch_tel.base_int_values_count}")
    print(f"  compile_s: {branch_tel.compile_seconds:.4f}")
    print(f"  note: {branch_tel.note}")

    # --- Fiber lower bound --------------------------------------------------
    print()
    print("fiber-only lower bound on K (16 mini-truth samples, Gateway song):")
    t0 = time.perf_counter()
    relation = build_mini_relation(
        webport,
        song_name=oracle.song_display,
        song_colors=oracle.song_colors,
    )
    fiber_report = run_fiber_probe(relation)
    fiber_s = time.perf_counter() - t0
    print(f"  worst K_lower: {fiber_report.worst_case_k_lower_bound:,}")
    print(f"  best  K_lower: {fiber_report.best_case_k_lower_bound:,}")
    print(f"  geo   K_lower: {fiber_report.geometric_mean_k_lower_bound:,.1f}")
    print(
        f"  exceeds 1e6 concerning: {fiber_report.worst_case_exceeds_concerning}  "
        f"exceeds 1e7 no-go: {fiber_report.worst_case_exceeds_likely_nogo}"
    )
    print(f"  fiber_probe_s: {fiber_s:.2f}")

    # --- Full DomainIR P-only wall ------------------------------------------
    print()
    print("full DomainIR P-only backward recurrence (honest CAP=1M):")
    t0 = time.perf_counter()
    full_ir = build_domain_ir(
        webport,
        song_colors=oracle.song_colors,
        song_name=oracle.song_display,
    )
    build_s = time.perf_counter() - t0
    print(f"  axes: {len(full_ir.axes)}  build_s: {build_s:.2f}")
    mini_opts = [len(a.options) for a in full_ir.axes if a.name.startswith("mini:")]
    print(f"  mini options/slot: {mini_opts}")

    t0 = time.perf_counter()
    bw_reports, root_k_p, wall_idx, mem_idx = _backward_recurrence(full_ir, GATEWAY_P)
    bw_s = time.perf_counter() - t0
    full_walled = wall_idx is not None or mem_idx is not None
    # Honest discipline: never report K=0 on a capacity wall (§16.8).
    root_k_reported: int | None = None if full_walled else root_k_p
    peak_live = max((r.live_states for r in bw_reports), default=0)
    peak_bytes = peak_live * BYTES_PER_STATE
    print(f"  layers reported: {len(bw_reports)} / {len(full_ir.axes)}")
    print(
        f"  wall_idx: {wall_idx}  mem_idx: {mem_idx}  "
        f"root_k_P: {'UNKNOWN (walled)' if full_walled else root_k_p}"
    )
    print(f"  backward_s: {bw_s:.2f}")
    for r in bw_reports[-5:]:
        live = f"capped@{CAP:,}" if r.capped else f"{r.live_states:,}"
        print(
            f"    [{r.idx}] {r.name:<28} opts={r.n_options:>8,}  "
            f"trans={r.transitions:>12,}  live={live}"
        )

    # --- Reduced-domain completing S+P track --------------------------------
    print()
    print("reduced-domain completing S+P track (labeled synth on Gateway):")
    pets = extract_pet_info(webport)
    upgrades = extract_upgrade_defs(webport)
    tables = build_tables(
        gears_csv=repo / "Data" / "Gear" / "Gears.csv",
        minis_csv=repo / "Data" / "Gear" / "Minis.csv",
        pets=pets,
        upgrades=upgrades,
    )
    pet_names = sorted(tables.pets.keys())[:6]
    mini_opts_spec = tuple(
        MiniState(name=n, level=50, rank=4, ascension=10) for n in pet_names[:4]
    )
    uids = tuple(sorted(tables.upgrades_by_id.keys())[:4])
    spec = DomainSpec(
        mini_options=mini_opts_spec,
        upgrade_type_ids=uids,
        upgrade_max_per_type=2,
        upgrade_total_max=6,
        gem_max_per_type=2,
        elemental_gem_max=2,
        team_buff_options=(None,),
        force_archetype="light",
    )
    samples = generate(oracle, tables, spec, n=1, seed=20250719)
    sample = samples[0]
    print(
        f"  synth sample (S,N,P)=({sample.observables.score:,}, "
        f"{sample.observables.naked_score:,}, {sample.observables.gear_power})"
    )
    keep_mini_labels: set[tuple] = set()
    for m in mini_opts_spec:
        keep_mini_labels.add(("mini", m.name, m.level, m.rank, m.ascension))
    for m in sample.loadout.minis:
        keep_mini_labels.add(("mini", m.name, m.level, m.rank, m.ascension))
    reduced = _filter_domain_ir_for_synth(
        full_ir,
        keep_mini_labels=keep_mini_labels,
        keep_upgrade_uids=set(uids),
        upgrade_max=2,
        gem_max=0,  # gems pinned to zero for a fast completing track
        gear_by_slot=dict(sample.loadout.gear),
        gear_named_cap=1,
    )
    n_opts_total = 1
    for axis in reduced.axes:
        n_opts_total *= len(axis.options)
    print(f"  reduced option-product (unweighted upper): {n_opts_total:,}")
    if n_opts_total > 5_000_000:
        print("  SKIP weighted S+P: reduced product still too large")
        k_sp = k_p = k_s = -1
        saturated_sp = False
        reduced_s = 0.0
        target_s = sample.observables.score
        target_p = sample.observables.gear_power
        target_n = sample.observables.naked_score
    else:
        target_s = sample.observables.score
        target_p = sample.observables.gear_power
        target_n = sample.observables.naked_score

        def feasible_sp(state: np.ndarray, axis_idx: int) -> bool:
            if axis_idx != len(reduced.axes):
                return True
            s, _n, p, _a = observables_from_stats7(
                exact_ir,
                state,
                song_colors=oracle.song_colors,
                naked_score=target_n,
            )
            return s == target_s and p == target_p

        def feasible_p(state: np.ndarray, axis_idx: int) -> bool:
            if axis_idx != len(reduced.axes):
                return True
            _s, _n, p, _a = observables_from_stats7(
                exact_ir,
                state,
                song_colors=oracle.song_colors,
                naked_score=target_n,
            )
            return p == target_p

        def feasible_s(state: np.ndarray, axis_idx: int) -> bool:
            if axis_idx != len(reduced.axes):
                return True
            s, _n, _p, _a = observables_from_stats7(
                exact_ir,
                state,
                song_colors=oracle.song_colors,
                naked_score=target_n,
            )
            return s == target_s

        t0 = time.perf_counter()
        k_sp = root_k(reduced, feasible=feasible_sp, max_k=K_CONCERNING)
        k_p = root_k(reduced, feasible=feasible_p, max_k=K_CONCERNING)
        k_s = root_k(reduced, feasible=feasible_s, max_k=K_CONCERNING)
        reduced_s = time.perf_counter() - t0
        saturated_sp = k_sp > K_CONCERNING
        print(
            f"  ablation root K: P={k_p:,}  S={k_s:,}  S+P={k_sp:,}  "
            f"sat_sp={saturated_sp}"
        )
        print(f"  reduced_weighted_s: {reduced_s:.2f}")
    print(
        f"  synth observables closed under oracle: "
        f"S={sample.observables.score:,} P={sample.observables.gear_power}"
    )

    # --- Budget projection --------------------------------------------------
    rates = _load_k1b_rates(repo)
    # Sum transitions reported before wall (lower bound on work).
    trans_before_wall = int(sum(r.transitions for r in bw_reports))
    t_search_lb = trans_before_wall / rates["rho_transition"]
    # Sort cost if we sorted every live state at each reported layer once.
    sort_keys = int(sum(min(r.live_states, CAP) for r in bw_reports))
    t_sort_lb = sort_keys / rates["rho_sort"]
    print()
    print("budget vs K1.b (lower bound from P-only layers before wall):")
    print(f"  transitions_before_wall: {trans_before_wall:,}")
    print(f"  T_search_lb: {t_search_lb*1e3:.3f} ms")
    print(f"  sort_keys_lb: {sort_keys:,}  T_sort_lb: {t_sort_lb:.3f} s")
    print(
        f"  preferred budget {BUDGET_PREFERRED_S:.0f}s / ceiling {BUDGET_CEILING_S:.0f}s — "
        "full root NOT reached; wall prevents a complete budget claim"
    )

    # --- Verdict ------------------------------------------------------------
    print()
    if full_walled and fiber_report.worst_case_exceeds_concerning:
        verdict = "FAIL"
        reason = (
            "Gateway full-DomainIR P-only walls before root; fiber-only K_lower "
            f"worst={fiber_report.worst_case_k_lower_bound:,} exceeds 1e6 concerning; "
            "exact root K and full branch count not obtained without research truncation"
        )
    elif full_walled:
        verdict = "FAIL"
        reason = (
            "Gateway full-DomainIR walls before root under P; S+P cannot be "
            "claimed on the production domain from this probe"
        )
    else:
        verdict = "PASS_CANDIDATE"
        reason = "root reached — inspect telemetry before promoting"
    print(f"VERDICT: {verdict}")
    print(f"  {reason}")

    artifact = {
        "row": {
            "song": "Gateway",
            "difficulty": "Normal",
            "player": "Temmie013_TH",
            "S": GATEWAY_S,
            "N": GATEWAY_N,
            "P": GATEWAY_P,
            "A": GATEWAY_A,
            "naked_match": True,
            "song_colors": list(oracle.song_colors),
        },
        "witness": {
            "vec": GATEWAY_WITNESS.tolist(),
            "matches_row": witness_ok,
            "score_stats_exact": s_exact,
        },
        "predicate_branch_telemetry": asdict(branch_tel),
        "fiber_lower_bound": {
            "worst": fiber_report.worst_case_k_lower_bound,
            "best": fiber_report.best_case_k_lower_bound,
            "geometric_mean": fiber_report.geometric_mean_k_lower_bound,
            "exceeds_concerning_1e6": fiber_report.worst_case_exceeds_concerning,
            "exceeds_likely_nogo_1e7": fiber_report.worst_case_exceeds_likely_nogo,
            "probe_seconds": fiber_s,
            "n_samples": len(fiber_report.samples),
        },
        "full_domain_p_only": {
            "walled": full_walled,
            "wall_idx": wall_idx,
            "mem_idx": mem_idx,
            "root_k": root_k_reported,
            "layers_reported": len(bw_reports),
            "layers_total": len(full_ir.axes),
            "peak_live_states": peak_live,
            "peak_live_bytes": peak_bytes,
            "transitions_before_wall": trans_before_wall,
            "backward_seconds": bw_s,
            "layer_tail": [
                {
                    "idx": r.idx,
                    "name": r.name,
                    "n_options": r.n_options,
                    "transitions": r.transitions,
                    "live_states": r.live_states,
                    "capped": r.capped,
                }
                for r in bw_reports[-8:]
            ],
        },
        "reduced_domain_sp": {
            "synth_S": target_s,
            "synth_P": target_p,
            "K_P": k_p,
            "K_S": k_s,
            "K_SP": k_sp,
            "saturated_sp": saturated_sp,
            "seconds": reduced_s,
            "option_product_unweighted": n_opts_total,
        },
        "budget_k1b": {
            **rates,
            "T_search_lb_s": t_search_lb,
            "T_sort_lb_s": t_sort_lb,
            "budget_ceiling_s": BUDGET_CEILING_S,
            "budget_preferred_s": BUDGET_PREFERRED_S,
            "complete_budget_claimable": False,
        },
        "verdict": verdict,
        "reason": reason,
        "color_arity_fix": (
            "SongOracle.song_colors now retains Secondary even when equal to "
            "Primary so DomainIR projects both color slots; observables_from_stats7 "
            "computes P as vec@pw (alias-safe)."
        ),
    }
    out = repo / "artifacts" / "k1a_with_s_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print()
    print(f"artifact: {out}")
    return 0 if verdict.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
