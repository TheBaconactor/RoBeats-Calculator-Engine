"""CLI probe for the reverse score engine v2 DomainIR.

Usage:
    python -m reverse_score_v2.domain_probe

Reports per-decision-layer option counts, total raw cross product, identity
fiber counts, suffix min/max P-contribution per layer, the contribution
matrix shape, and the gear-power weight vector. Reports for both the
single-color (``("Chill",)``) and two-color (``("Chill", "Flow")``) cases
to show how the elemental gem axis changes.

This probe does NOT require a song context -- the DomainIR is
song-independent except for the elemental gem color projection, which the
probe reports per color arity. The seed song name for the build is the
dummy ``__domain_ir_seed__``; the mini stat vectors are materialized
against that seed so the IR is concrete, but the mini-identity fiber
carries the full (name, level, rank, ascension) key and witness
materialization re-derives per-query ascension bonuses.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

from reverse_score_v2.domain_ir import DomainIR, build_domain_ir


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


def _print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(f"  {title}")
    print("=" * 78)


def _print_axis_table(ir: DomainIR) -> None:
    print()
    print(
        f"{'#':>3}  {'layer':<32} {'options':>9} {'fibers':>7} "
        f"{'suffix_min':>11} {'suffix_max':>11}"
    )
    print("-" * 78)
    total_cross = 1
    for i, axis in enumerate(ir.axes):
        n_opts = len(axis.options)
        n_fibers = len(axis.identity_fibers)
        total_cross *= n_opts
        print(
            f"{i:>3}  {axis.name:<32} {n_opts:>9,} {n_fibers:>7,} "
            f"{axis.suffix_min:>11,} {axis.suffix_max:>11,}"
        )
    print("-" * 78)
    print(f"  total raw cross product: {total_cross:,e}")
    print(f"  axes: {len(ir.axes)}")
    print(f"  upgrade_total_max: {ir.upgrade_total_max}")
    print(f"  gem_max_per_type: {ir.gem_max_per_type}")
    print(f"  upgrade_max_per_type: {ir.upgrade_max_per_type}")


def _print_contribution_matrix(ir: DomainIR) -> None:
    print()
    print("  Contribution matrix shape per axis (options x 7):")
    for i, (axis, mat) in enumerate(zip(ir.axes, ir.option_mats)):
        print(f"    {i:>3}  {axis.name:<32} {mat.shape}")
    print()
    print("  Stacked contribution matrix (all options x 7):")
    stacked = np.concatenate(ir.option_mats, axis=0)
    print(f"    shape: {stacked.shape}")
    print(f"    dtype: {stacked.dtype}")
    print(f"    min:   {int(stacked.min())}")
    print(f"    max:   {int(stacked.max())}")


def _print_pw(ir: DomainIR) -> None:
    print()
    print("  Gear-power weight vector pw (int32, 7-dim):")
    print(f"    {ir.pw.tolist()}")
    print(f"    song_colors: {ir.song_colors}")
    print("    P = vec @ pw")
    n_colors = len(ir.song_colors)
    if n_colors == 1:
        print("    one-color: P = 6*c1 + 5*(PP+CM+FM+FT+FF)")
    else:
        print("    two-color: P = 4*c1 + 2*c2 + 5*(PP+CM+FM+FT+FF)")


def _print_domain_findings(ir: DomainIR) -> None:
    """Surface any domain-shape finding that affects the reverse search."""
    print()
    print("  Domain-shape findings:")
    findings: list[str] = []

    # Largest axis by option count.
    largest = max(ir.axes, key=lambda a: len(a.options))
    findings.append(
        f"largest axis: {largest.name} with {len(largest.options):,} options"
    )

    # Axes where identity fibers collapse many options.
    for axis in ir.axes:
        n_opts = len(axis.options)
        n_fibers = len(axis.identity_fibers)
        if n_fibers < n_opts and n_fibers > 0:
            ratio = n_opts / max(1, n_fibers)
            findings.append(
                f"{axis.name}: {n_opts:,} options -> {n_fibers:,} fibers "
                f"(collapse ratio {ratio:.2f}x)"
            )

    # Suffix range width at the root (layer 0).
    root_span = ir.axes[0].suffix_max - ir.axes[0].suffix_min
    findings.append(
        f"root suffix P-span: [{ir.axes[0].suffix_min:,}, {ir.axes[0].suffix_max:,}] "
        f"(width {root_span:,})"
    )

    # Zero-projection upgrade axes (count-unrecoverable from observables).
    for axis in ir.axes:
        if not axis.name.startswith("upgrade:"):
            continue
        unit = axis.options[1].vec if len(axis.options) > 1 else None
        if unit is not None and not bool(np.any(unit)):
            findings.append(
                f"{axis.name}: per-unit projection all-zero -- count is "
                "observable-unrecoverable, bounded only by the joint budget"
            )

    # Gear axes with stat-equivalent pieces (identity fiber collapse).
    for axis in ir.axes:
        if not axis.name.startswith("gear:"):
            continue
        n_opts = len(axis.options)
        n_fibers = len(axis.identity_fibers)
        if n_fibers < n_opts:
            findings.append(
                f"{axis.name}: {n_opts - n_fibers} gear pieces share a stat "
                "projection with at least one other piece"
            )

    for f in findings:
        print(f"    - {f}")

    # Per-axis option count summary by category.
    print()
    print("  Option counts by category:")
    by_cat: dict[str, int] = {}
    for axis in ir.axes:
        cat = axis.name.split(":", 1)[0]
        by_cat[cat] = by_cat.get(cat, 0) + len(axis.options)
    for cat, count in sorted(by_cat.items()):
        print(f"    {cat:<12} {count:>9,}")


def main() -> int:
    webport_root = _resolve_webport_root()
    if not webport_root.is_dir():
        print(f"ERROR: webport_root not found: {webport_root}", file=sys.stderr)
        return 2

    print(f"webport_root: {webport_root}")
    print(f"python: {sys.version.split()[0]}")
    print(f"numpy: {np.__version__}")

    for song_colors in (("Chill",), ("Chill", "Flow")):
        _print_header(f"DomainIR build: song_colors={song_colors}")
        try:
            ir = build_domain_ir(webport_root, song_colors=song_colors)
        except Exception as exc:
            print(f"BUILD FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        _print_axis_table(ir)
        _print_pw(ir)
        _print_contribution_matrix(ir)
        _print_domain_findings(ir)

    print()
    print("=" * 78)
    print("  probe complete")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
