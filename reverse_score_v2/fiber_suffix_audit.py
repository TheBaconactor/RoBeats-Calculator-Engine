"""Fiber collapse + suffix band audit for the reverse score engine v2 DomainIR.

Read-only analysis script. Builds the DomainIR for single-color (``Chill``)
and two-color (``Chill``, ``Flow``) and reports:

1. Per-axis fiber collapse efficiency (options, fibers, ratio, top-5 fiber
   sizes, perfect vs lossy).
2. Per-layer suffix band width + cumulative narrowing.
3. ``P=5834`` (Gateway top-1, single-color) per-layer pruning factor: the
   fraction of options whose P-contribution is within the feasible band
   ``[target - suffix_max_other_layers, target - suffix_min_other_layers]``.
   This is the predicate filter the backward recurrence applies BEFORE the
   merge step; the merge collapses further.
4. The 8 off-color upgrade types (all-zero on single-color Chill, plus
   two-color behavior).
5. Negative ``suffix_min`` layers on two-color (Chill, Flow) and the
   implication for the backward recurrence (negative residuals must be
   permitted, not clamped at 0).
6. Gear axis deep check (per-slot option/fiber counts, collapse ratio,
   P-contribution range, negative-contribution flag).

Does NOT modify the DomainIR. Does NOT commit. Leaves the audit script in
the working tree.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

from reverse_score_v2.domain_ir import PROJECTION_KEYS, DomainIR, build_domain_ir

# Gateway top-1 single-color target. Used for the predicate filter in
# Section 3. Hardwired -- the audit is a one-shot probe of the DomainIR
# against a known target, not a per-song query.
P_TARGET_SINGLE: int = 5834


def _resolve_webport_root() -> Path:
    """Resolve the decompiled ReplicatedStorage root.

    Honors ``ROBEATS_DECOMPILED_ROOT`` if set; else falls back to the
    canonical SarHort V5 path the handoff names.
    """
    env_root = os.environ.get("ROBEATS_DECOMPILED_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    return Path(
        r"<redacted-user-home>/Desktop/Exceptions/SarHort V5/workspace/SavedGame_706824758/ReplicatedStorage"
    )


def _build_both() -> tuple[DomainIR, DomainIR]:
    webport_root = _resolve_webport_root()
    if not webport_root.is_dir():
        raise SystemExit(f"ERROR: webport_root not found: {webport_root}")
    ir1 = build_domain_ir(webport_root, song_colors=("Chill",))
    ir2 = build_domain_ir(webport_root, song_colors=("Chill", "Flow"))
    return ir1, ir2


def _axis_option_p(axis, pw: np.ndarray) -> np.ndarray:
    """Return per-option P-contribution for one axis as int64."""
    mat = np.stack([opt.vec for opt in axis.options], axis=0).astype(np.int64)
    return mat @ pw.astype(np.int64)


def _top5_fiber_sizes(axis) -> list[int]:
    return sorted((len(f) for f in axis.identity_fibers), reverse=True)[:5]


def _verify_perfect_collapse(axis) -> bool:
    """Return True iff every option in each fiber has an identical vec.

    ``_finalize_axis`` groups by ``vec.tobytes()`` so this is guaranteed by
    construction; the check exists to fail loudly if a future change
    introduces lossy fibers.
    """
    for fiber in axis.identity_fibers:
        ref = fiber[0].vec
        for opt in fiber[1:]:
            if not np.array_equal(opt.vec, ref):
                return False
    return True


# ---------------------------------------------------------------------------
# Section 1: per-axis fiber collapse efficiency
# ---------------------------------------------------------------------------


def section1_fiber_collapse(ir: DomainIR, label: str) -> None:
    print(f"\n{'=' * 78}")
    print(f"  Section 1: per-axis fiber collapse ({label})")
    print(f"{'=' * 78}")
    print(
        f"{'#':>3}  {'layer':<32} {'opts':>9} {'fibers':>7} {'ratio':>6}  "
        f"{'top-5 fiber sizes':<24}  {'quality':<8}"
    )
    print("-" * 100)
    lossy = 0
    for i, axis in enumerate(ir.axes):
        n_opts = len(axis.options)
        n_fibers = len(axis.identity_fibers)
        ratio = n_opts / n_fibers if n_fibers else 0.0
        top5 = _top5_fiber_sizes(axis)
        top5_str = ",".join(str(s) for s in top5)
        perfect = _verify_perfect_collapse(axis)
        quality = "perfect" if perfect else "LOSSY"
        if not perfect:
            lossy += 1
        print(
            f"{i:>3}  {axis.name:<32} {n_opts:>9,} {n_fibers:>7,} {ratio:>6.2f}  "
            f"{top5_str:<24}  {quality:<8}"
        )
    print("-" * 100)
    print(f"  lossy axes: {lossy} (expected 0; fibers group by vec.tobytes())")


# ---------------------------------------------------------------------------
# Section 2: suffix band width per layer
# ---------------------------------------------------------------------------


def section2_suffix_band(ir: DomainIR, label: str) -> None:
    print(f"\n{'=' * 78}")
    print(f"  Section 2: per-layer suffix band width ({label})")
    print(f"{'=' * 78}")
    print(
        f"{'#':>3}  {'layer':<32} {'smin':>9} {'smax':>9} {'band':>9}  "
        f"{'band/total':>10}  {'cumul_narrow':>12}"
    )
    print("-" * 100)
    # Root suffix span = the band at layer 0. Used as the total P range
    # denominator: a tight band means strong pruning.
    root_band = ir.axes[0].suffix_max - ir.axes[0].suffix_min
    total_p_range = root_band if root_band > 0 else 1
    initial = root_band if root_band > 0 else 1
    for i, axis in enumerate(ir.axes):
        band = axis.suffix_max - axis.suffix_min
        ratio = band / total_p_range
        cumul_narrow = (initial - band) / initial if initial > 0 else 0.0
        print(
            f"{i:>3}  {axis.name:<32} {axis.suffix_min:>9,} {axis.suffix_max:>9,} "
            f"{band:>9,}  {ratio:>10.4f}  {cumul_narrow:>12.4f}"
        )
    print("-" * 100)
    print(f"  total P range (root suffix band): {total_p_range:,}")


# ---------------------------------------------------------------------------
# Section 3: P=5834 per-layer pruning factor
# ---------------------------------------------------------------------------


def section3_pruning_factor(
    ir: DomainIR, label: str, target: int = P_TARGET_SINGLE
) -> None:
    print(f"\n{'=' * 78}")
    print(f"  Section 3: P={target} per-layer pruning factor ({label})")
    print(f"{'=' * 78}")
    pw = ir.pw.astype(np.int64)
    opt_p_per_axis: list[np.ndarray] = []
    axis_min: list[int] = []
    axis_max: list[int] = []
    for axis in ir.axes:
        p = _axis_option_p(axis, pw)
        opt_p_per_axis.append(p)
        axis_min.append(int(p.min()))
        axis_max.append(int(p.max()))
    total_min = sum(axis_min)
    total_max = sum(axis_max)
    print(f"  target P: {target:,}")
    print(f"  total min P (sum of per-axis mins): {total_min:,}")
    print(f"  total max P (sum of per-axis maxs): {total_max:,}")
    print(f"  predicate band (any layer): [{target - total_max:,}, {target - total_min:,}]")
    print()
    print(
        f"{'#':>3}  {'layer':<32} {'opts':>9} {'feasible':>9} {'factor':>8}  "
        f"{'band_low':>9}  {'band_high':>9}"
    )
    print("-" * 100)
    for i, axis in enumerate(ir.axes):
        # Other layers' min/max P sums (all layers except i).
        suffix_min_other = total_min - axis_min[i]
        suffix_max_other = total_max - axis_max[i]
        band_low = target - suffix_max_other
        band_high = target - suffix_min_other
        p = opt_p_per_axis[i]
        feasible = int(np.count_nonzero((p >= band_low) & (p <= band_high)))
        factor = feasible / len(axis.options) if len(axis.options) else 0.0
        print(
            f"{i:>3}  {axis.name:<32} {len(axis.options):>9,} {feasible:>9,} "
            f"{factor:>8.4f}  {band_low:>9,}  {band_high:>9,}"
        )
    print("-" * 100)
    # Interpretation: report whether the predicate is binding at all.
    # On single-color Chill at P=5834, total_max (7,944) exceeds the target
    # and every per-axis max is far below target - suffix_min_other, so
    # band_high is above every option's P and band_low is below every
    # option's P. The suffix-band predicate is non-binding here; pruning
    # happens at the merge step (cross-layer sum constraint), not at the
    # per-layer predicate filter.
    nontrivial = []
    for i, axis in enumerate(ir.axes):
        p = opt_p_per_axis[i]
        suffix_min_other = total_min - axis_min[i]
        suffix_max_other = total_max - axis_max[i]
        band_low = target - suffix_max_other
        band_high = target - suffix_min_other
        feasible = int(np.count_nonzero((p >= band_low) & (p <= band_high)))
        if feasible < len(axis.options):
            nontrivial.append((i, axis.name, feasible, len(axis.options)))
    if not nontrivial:
        print(
            f"  NOTE: predicate filter is non-binding at P={target:,} -- every "
            f"option passes at every layer. The total max P ({total_max:,}) "
            f"exceeds the target and no per-axis max exceeds the high band. "
            f"Pruning happens at the merge step (cross-layer sum constraint), "
            f"not the per-layer predicate filter."
        )
    else:
        print(f"  layers where the predicate prunes (factor < 1.0): {len(nontrivial)}")
        for i, name, f, n in nontrivial:
            print(f"    layer {i:>3}  {name:<32}  {f}/{n}")


# ---------------------------------------------------------------------------
# Section 4: the 8 off-color upgrade types
# ---------------------------------------------------------------------------


def section4_offcolor_upgrades(ir1: DomainIR, ir2: DomainIR) -> None:
    print(f"\n{'=' * 78}")
    print("  Section 4: 8 off-color upgrade types (single vs two-color)")
    print(f"{'=' * 78}")
    off_color_axes = []
    for axis in ir1.axes:
        if not axis.name.startswith("upgrade:"):
            continue
        if len(axis.options) <= 1:
            continue
        # options[1] is count=1 -> unit_vec.
        unit_vec = axis.options[1].vec
        if not np.any(unit_vec):
            off_color_axes.append(axis)
    print(f"  off-color (all-zero on single-color Chill) upgrade axes: {len(off_color_axes)}")
    print()
    print(
        f"  {'axis':<32}  {'1-color unit vec':<28}  {'2-color unit vec':<28}  "
        f"{'1c P':>5}  {'2c P':>5}  {'status':<16}"
    )
    print("-" * 130)
    ir2_by_name = {a.name: a for a in ir2.axes}
    pw1 = ir1.pw.astype(np.int64)
    pw2 = ir2.pw.astype(np.int64)
    becomes_nonzero = []
    for axis in off_color_axes:
        a2 = ir2_by_name.get(axis.name)
        uv1 = axis.options[1].vec
        uv2 = a2.options[1].vec if a2 is not None else None
        p1 = int(uv1 @ pw1)
        p2 = int(uv2 @ pw2) if uv2 is not None else None
        uv1_str = str(uv1.tolist())
        uv2_str = str(uv2.tolist()) if uv2 is not None else "?"
        if p2 is not None and p2 != 0:
            status = "becomes nonzero"
            becomes_nonzero.append(axis.name)
        else:
            status = "remains zero"
        p2_str = str(p2) if p2 is not None else "?"
        print(
            f"  {axis.name:<32}  {uv1_str:<28}  {uv2_str:<28}  {p1:>5}  {p2_str:>5}  {status:<16}"
        )
    print("-" * 130)
    print(f"  becomes non-zero on two-color (Chill, Flow): {becomes_nonzero}")
    print()
    print("  implication: the 8 off-color types are observable-unrecoverable")
    print("  on single-color charts; the reverse search must bound them only")
    print("  by the joint budget (90) and materialize their counts via the")
    print("  upgrade-count fiber at witness time.")


# ---------------------------------------------------------------------------
# Section 5: negative suffix_min layers on two-color
# ---------------------------------------------------------------------------


def section5_negative_suffix_min(ir2: DomainIR) -> None:
    print(f"\n{'=' * 78}")
    print("  Section 5: negative suffix_min on two-color (Chill, Flow)")
    print(f"{'=' * 78}")
    neg_layers = [(i, a) for i, a in enumerate(ir2.axes) if a.suffix_min < 0]
    print(f"  layers with negative suffix_min: {len(neg_layers)}")
    for i, a in neg_layers:
        print(
            f"    layer {i:>3}  {a.name:<32}  "
            f"suffix_min={a.suffix_min:,}  suffix_max={a.suffix_max:,}"
        )
    if neg_layers:
        most_neg = min(neg_layers, key=lambda x: x[1].suffix_min)
        print(
            f"  most negative suffix_min: {most_neg[1].suffix_min:,} "
            f"at layer {most_neg[0]} ({most_neg[1].name})"
        )
    print()
    print("  implication: the residual P-budget can go negative mid-recurrence")
    print("  and recover; the backward recurrence must allow negative")
    print("  residuals, not clamp at 0.")


# ---------------------------------------------------------------------------
# Section 6: gear axis deep check
# ---------------------------------------------------------------------------


def section6_gear_deep_check(ir: DomainIR, label: str) -> None:
    print(f"\n{'=' * 78}")
    print(f"  Section 6: gear axis deep check ({label})")
    print(f"{'=' * 78}")
    print(
        f"  {'slot':<32}  {'opts':>6}  {'fibers':>7}  {'ratio':>6}  "
        f"{'P min':>7}  {'P max':>7}  {'neg P?':>7}"
    )
    print("-" * 100)
    pw = ir.pw.astype(np.int64)
    any_neg = False
    for axis in ir.axes:
        if not axis.name.startswith("gear:"):
            continue
        p = _axis_option_p(axis, pw)
        n_opts = len(axis.options)
        n_fibers = len(axis.identity_fibers)
        ratio = n_opts / n_fibers if n_fibers else 0.0
        p_min = int(p.min())
        p_max = int(p.max())
        has_neg = bool((p < 0).any())
        if has_neg:
            any_neg = True
        print(
            f"  {axis.name:<32}  {n_opts:>6,}  {n_fibers:>7,}  {ratio:>6.2f}  "
            f"{p_min:>7,}  {p_max:>7,}  {str(has_neg):>7}"
        )
    print("-" * 100)
    print(f"  any gear piece has negative P contribution: {any_neg}")


# ---------------------------------------------------------------------------
# Section 7: one-paragraph summary
# ---------------------------------------------------------------------------


def section7_summary(ir1: DomainIR, ir2: DomainIR) -> None:
    """One-paragraph summary of hard-prune vs wall axes + gear neg implication."""
    print(f"\n{'=' * 78}")
    print("  Section 7: one-paragraph summary")
    print(f"{'=' * 78}")
    # Identify prune-hard vs wall axes from fiber collapse on single-color.
    prune_hard: list[str] = []
    walls: list[str] = []
    for axis in ir1.axes:
        n_opts = len(axis.options)
        n_fibers = len(axis.identity_fibers)
        if n_fibers == 1 and n_opts > 1:
            prune_hard.append(f"{axis.name} ({n_opts}->1)")
        elif n_opts == n_fibers:
            walls.append(f"{axis.name} ({n_opts})")
        else:
            ratio = n_opts / n_fibers if n_fibers else 0.0
            prune_hard.append(f"{axis.name} ({n_opts}->{n_fibers}, {ratio:.2f}x)")
    neg_gear = False
    pw = ir1.pw.astype(np.int64)
    for axis in ir1.axes:
        if axis.name.startswith("gear:"):
            if int(_axis_option_p(axis, pw).min()) < 0:
                neg_gear = True
    # Negative suffix_min count on two-color.
    neg_count = sum(1 for a in ir2.axes if a.suffix_min < 0)
    print(
        "Axes that prune hard (backward recurrence shrinks them dramatically): "
        + "; ".join(prune_hard)
        + "."
    )
    print()
    print(
        "Wall candidates (no fiber collapse -- every option is its own fiber): "
        + "; ".join(walls)
        + "."
    )
    print()
    print(
        f"Two-color (Chill, Flow): {neg_count} layers have negative suffix_min "
        f"(most negative = {min(a.suffix_min for a in ir2.axes)}); the recurrence "
        f"must allow negative residuals."
    )
    print()
    print(
        f"Gear negative contribution: any single-color gear piece with negative "
        f"P-contribution = {neg_gear}. "
        + (
            "The gear suffix bounds CAN go negative on signed-stat patterns."
            if neg_gear
            else "All gear pieces have non-negative P contribution; the gear suffix "
            "bounds stay non-negative on single-color."
        )
    )


def main() -> int:
    print(f"python: {sys.version.split()[0]}")
    print(f"numpy: {np.__version__}")
    ir1, ir2 = _build_both()
    print(f"single-color axes: {len(ir1.axes)}; two-color axes: {len(ir2.axes)}")
    print(f"single-color pw: {ir1.pw.tolist()}")
    print(f"two-color pw: {ir2.pw.tolist()}")
    print(f"projection keys: {PROJECTION_KEYS}")

    section1_fiber_collapse(ir1, "single-color Chill")
    section2_suffix_band(ir1, "single-color Chill")
    section3_pruning_factor(ir1, "single-color Chill", target=P_TARGET_SINGLE)
    section4_offcolor_upgrades(ir1, ir2)
    section5_negative_suffix_min(ir2)
    section6_gear_deep_check(ir1, "single-color Chill")
    section6_gear_deep_check(ir2, "two-color (Chill, Flow)")
    section7_summary(ir1, ir2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
