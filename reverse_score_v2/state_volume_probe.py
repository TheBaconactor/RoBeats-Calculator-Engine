"""CPU state-volume probe for the reverse score engine v2 (P-constraint only).

Implements the backward, target-sliced recurrence from handoff §5.A.3.d on
the DomainIR with a P (gear-power) row predicate only. The full S (score)
constraint needs the ExactScoreIR row-predicate compiler, which is not yet
built; this probe is an upper bound on per-layer live state volumes.

Usage:
    python -m reverse_score_v2.state_volume_probe

State representation
--------------------
Each partial state is the 7-dim int32 accumulated contribution vector from
the layers already consumed. Two states with the same vector are the same
suffix state (handoff §5.A.3.d identity-fiber collapse) and merge. The
residual P-budget is derived as ``R = P_target - vec @ pw``; we never store
it separately because the 7-dim vec is the merge key.

Backward recurrence
-------------------
Process layers from LAST to FIRST. After processing layers ``i+1..end`` we
hold the set of accumulated vectors ``V`` over those layers. At layer ``i``
we form predecessors ``V' = V + opt_i.vec`` for each ``opt_i`` in
``axis[i].options``. A predecessor is kept iff the residual
``P_target - V' @ pw`` is achievable by the remaining suffix
``0..i-1`` -- i.e.

    axis[i-1].suffix_min <= P_target - V' @ pw <= axis[i-1].suffix_max

When ``i == 0`` the residual must be exactly zero (``V' @ pw == P_target``);
those are the root completions, and K is the number of distinct full states
that hit the target.

The per-layer state count is capped at ``CAP = 1_000_000``. If a layer
exceeds the cap, the probe reports "capped at 1M" and stops expanding that
layer (the wall). This matches v1's honest-cap discipline.

Bytes per state: 7-dim int32 vec = 28 bytes (we do not store the residual
separately; it is derived). Reported as 28 bytes per live state.

Read-only on production: imports ``DomainIR`` / ``build_domain_ir`` from
``reverse_score_v2.domain_ir``; does not modify any file under
``gear_optimizer/`` or ``reverse_score_v2/domain_ir.py``.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from reverse_score_v2.domain_ir import DomainIR, build_domain_ir

# Per-layer honest cap (matches v1's discipline).
CAP: int = 1_000_000

# Bytes per live state: 7-dim int32 vec (the residual is derived, not stored).
BYTES_PER_STATE: int = 7 * 4

# Probe memory ceiling. If a single layer's bytes would exceed this, stop.
MEM_BUDGET_BYTES: int = 2 * 1024 * 1024 * 1024  # 2 GB


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


@dataclass(frozen=True, slots=True)
class LayerReport:
    """One row of the per-layer report table."""

    idx: int
    name: str
    n_options: int
    transitions: int
    live_states: int
    capped: bool
    bytes_live: int


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Full result of one (P_target, song_colors) probe run."""

    p_target: int
    song_colors: tuple[str, ...]
    backward: list[LayerReport]
    forward: list[LayerReport]
    root_completions_k: int
    max_live_bytes: int
    hit_wall_at: int | None  # idx of the layer that capped (backward order)
    hit_mem_at: int | None


def _compute_prefix_bounds(ir: DomainIR) -> tuple[list[int], list[int]]:
    """Compute per-layer ``prefix_min`` / ``prefix_max`` P-contribution.

    For axis ``i``, ``prefix_min[i]`` is the sum of min P-contribution over
    axes ``0..i-1`` (the prefix before this layer); ``prefix_max[i]`` is
    the sum of max P-contribution over the same range. Used by the
    backward recurrence: when processing layer ``i`` (going backward),
    ``state_P`` is the accumulated P from layers ``i+1..end`` (already
    decided), and the residual ``P_target - state_P`` must be achievable
    by the not-yet-decided prefix ``0..i-1`` -- i.e.

        prefix_min[i] <= P_target - state_P <= prefix_max[i]

    For ``i == 0`` the prefix is empty, so the residual must be exactly
    zero (``state_P == P_target``).
    """
    pw = ir.pw.astype(np.int64)
    n = len(ir.axes)
    prefix_min = [0] * n
    prefix_max = [0] * n
    acc_min = 0
    acc_max = 0
    for i in range(n):
        prefix_min[i] = acc_min
        prefix_max[i] = acc_max
        opt_p = ir.option_mats[i].astype(np.int64) @ pw
        acc_min += int(opt_p.min())
        acc_max += int(opt_p.max())
    return prefix_min, prefix_max


def _expand_and_filter(
    cur: np.ndarray,
    opt_mat: np.ndarray,
    pw: np.int64,
    p_target: int,
    smin: int | None,
    smax: int | None,
    is_root: bool,
) -> tuple[np.ndarray, int, bool]:
    """Expand ``cur`` (M, 7) by ``opt_mat`` (K, 7), filter by residual
    feasibility, and return (unique kept int32 (L, 7), transitions, capped).

    Streams in option-chunks to avoid materializing the full (M, K, 7)
    tensor. Declares ``capped=True`` if the pre-merge survivor count
    exceeds ``CAP`` -- in that case the caller should treat the layer as
    hitting the wall and the returned array is empty (no point continuing
    the merge).

    When ``is_root`` is True (i == 0 / i == n-1 for backward / forward),
    ``smin`` / ``smax`` are ignored and the kept set is exactly
    ``V' @ pw == p_target``.
    """
    M = cur.shape[0]
    K = opt_mat.shape[0]
    transitions = M * K

    cur64 = cur.astype(np.int64)
    opt64 = opt_mat.astype(np.int64)

    # Chunk over options to bound peak memory. Each chunk produces a
    # (M, K_chunk, 7) int64 tensor; pick K_chunk so that tensor is <= ~256 MB.
    # 256 MB / (M * 7 * 8 bytes) = chunk size.
    bytes_per_opt_row = M * 7 * 8  # int64
    if bytes_per_opt_row == 0:
        k_chunk = K
    else:
        k_chunk = max(1, (256 * 1024 * 1024) // bytes_per_opt_row)
    k_chunk = min(k_chunk, K)

    survivor_chunks: list[np.ndarray] = []
    pre_merge_count = 0
    cap_pre_merge = 4 * CAP  # generous: allow 4M pre-merge rows before declaring cap

    for lo in range(0, K, k_chunk):
        hi = min(lo + k_chunk, K)
        opt_chunk = opt64[lo:hi]  # (kc, 7)
        # (M, kc, 7) = cur64[:, None, :] + opt_chunk[None, :, :]
        block = cur64[:, None, :] + opt_chunk[None, :, :]
        flat = block.reshape(-1, 7)
        p_contrib = flat @ pw
        if is_root:
            mask = p_contrib == p_target
        else:
            assert smin is not None and smax is not None
            mask = (p_contrib >= p_target - smax) & (p_contrib <= p_target - smin)
        if not mask.any():
            continue
        kept = flat[mask]
        survivor_chunks.append(kept)
        pre_merge_count += kept.shape[0]
        if pre_merge_count > cap_pre_merge:
            # Pre-merge survivor count is already huge; final unique will
            # almost certainly exceed CAP. Declared capped.
            return np.zeros((0, 7), dtype=np.int32), transitions, True

    if not survivor_chunks:
        return np.zeros((0, 7), dtype=np.int32), transitions, False

    cat = np.concatenate(survivor_chunks, axis=0)
    # Free the chunk list early.
    del survivor_chunks
    # Pre-merge count is the raw survivor count; the post-merge count is
    # what we actually care about. If cat itself already exceeds a
    # generous multiple of CAP, the unique will too (unique can only
    # shrink). We still run unique because the shrink can be dramatic
    # (that's the sharing signal we want to measure).
    if cat.shape[0] > 8 * CAP:
        # Even with an extreme merge ratio (8:1), this would still cap.
        return np.zeros((0, 7), dtype=np.int32), transitions, True

    kept_unique = np.unique(cat, axis=0).astype(np.int32, copy=False)
    return kept_unique, transitions, kept_unique.shape[0] > CAP


def _backward_recurrence(ir: DomainIR, p_target: int) -> tuple[list[LayerReport], int, int | None, int | None]:
    """Run the backward recurrence.

    Returns (per-layer reports in BACKWARD processing order, root
    completions K, wall layer idx or None, mem-cap layer idx or None).
    """
    pw = ir.pw.astype(np.int64)
    axes = ir.axes
    n = len(axes)
    prefix_min, prefix_max = _compute_prefix_bounds(ir)
    reports: list[LayerReport] = []
    wall_idx: int | None = None
    mem_idx: int | None = None

    # Initial state set: the empty accumulated vector (nothing consumed yet).
    # We process from layer n-1 down to layer 0.
    cur = np.zeros((1, 7), dtype=np.int32)
    root_k = 0

    for i in range(n - 1, -1, -1):
        axis = axes[i]
        opt_mat = ir.option_mats[i]  # (n_opts, 7) int32
        n_opts = opt_mat.shape[0]

        if i == 0:
            # Prefix is empty -> residual must be exactly zero.
            smin = smax = None
            is_root = True
        else:
            # Residual P_target - V'@pw must be achievable by the prefix
            # 0..i-1.
            smin = prefix_min[i]
            smax = prefix_max[i]
            is_root = False

        kept_unique, transitions, capped = _expand_and_filter(
            cur, opt_mat, pw, p_target, smin, smax, is_root
        )

        if capped:
            # Wall: report and stop. The true live count is > CAP.
            reports.append(
                LayerReport(
                    idx=i,
                    name=axis.name,
                    n_options=n_opts,
                    transitions=transitions,
                    live_states=CAP,
                    capped=True,
                    bytes_live=CAP * BYTES_PER_STATE,
                )
            )
            wall_idx = i
            break

        live = kept_unique.shape[0]
        bytes_live = live * BYTES_PER_STATE

        if bytes_live > MEM_BUDGET_BYTES:
            reports.append(
                LayerReport(
                    idx=i,
                    name=axis.name,
                    n_options=n_opts,
                    transitions=transitions,
                    live_states=live,
                    capped=False,
                    bytes_live=bytes_live,
                )
            )
            mem_idx = i
            break

        reports.append(
            LayerReport(
                idx=i,
                name=axis.name,
                n_options=n_opts,
                transitions=transitions,
                live_states=live,
                capped=False,
                bytes_live=bytes_live,
            )
        )

        if i == 0:
            # The kept set at i == 0 ARE the root completions (V' @ pw ==
            # p_target). K = live.
            root_k = live

        cur = kept_unique

    return reports, root_k, wall_idx, mem_idx


def _forward_recurrence(ir: DomainIR, p_target: int) -> tuple[list[LayerReport], int | None, int | None]:
    """Run the forward recurrence for comparison.

    Forward: process layers 0..n-1. After layer i we hold accumulated
    vectors over layers 0..i. At layer i+1 we form successors V' = V +
    opt_{i+1}.vec and keep iff residual is feasible against suffix i+2..end.
    """
    pw = ir.pw.astype(np.int64)
    axes = ir.axes
    n = len(axes)
    reports: list[LayerReport] = []
    wall_idx: int | None = None
    mem_idx: int | None = None

    cur = np.zeros((1, 7), dtype=np.int32)

    for i in range(n):
        axis = axes[i]
        opt_mat = ir.option_mats[i]
        n_opts = opt_mat.shape[0]

        if i == n - 1:
            smin = smax = None
            is_root = True
        else:
            smin = axes[i].suffix_min  # suffix from i+1
            smax = axes[i].suffix_max
            is_root = False

        kept_unique, transitions, capped = _expand_and_filter(
            cur, opt_mat, pw, p_target, smin, smax, is_root
        )

        if capped:
            reports.append(
                LayerReport(
                    idx=i,
                    name=axis.name,
                    n_options=n_opts,
                    transitions=transitions,
                    live_states=CAP,
                    capped=True,
                    bytes_live=CAP * BYTES_PER_STATE,
                )
            )
            wall_idx = i
            break

        live = kept_unique.shape[0]
        bytes_live = live * BYTES_PER_STATE

        if bytes_live > MEM_BUDGET_BYTES:
            reports.append(
                LayerReport(
                    idx=i,
                    name=axis.name,
                    n_options=n_opts,
                    transitions=transitions,
                    live_states=live,
                    capped=False,
                    bytes_live=bytes_live,
                )
            )
            mem_idx = i
            break

        reports.append(
            LayerReport(
                idx=i,
                name=axis.name,
                n_options=n_opts,
                transitions=transitions,
                live_states=live,
                capped=False,
                bytes_live=bytes_live,
            )
        )
        cur = kept_unique

    return reports, wall_idx, mem_idx


def _print_layer_table(title: str, reports: list[LayerReport], total_axes: int) -> None:
    print()
    print(f"  {title}")
    print(
        f"  {'idx':>3}  {'layer':<34} {'options':>9} {'transitions':>14} "
        f"{'live_states':>14} {'bytes':>14}"
    )
    print("  " + "-" * 96)
    for r in reports:
        live_str = "capped at 1M" if r.capped else f"{r.live_states:,}"
        if r.bytes_live > MEM_BUDGET_BYTES and not r.capped:
            live_str = f"{r.live_states:,} (mem-cap)"
        print(
            f"  {r.idx:>3}  {r.name:<34} {r.n_options:>9,} {r.transitions:>14,} "
            f"{live_str:>14} {r.bytes_live:>14,}"
        )
    print("  " + "-" * 96)
    print(f"  axes reported: {len(reports)} / {total_axes}")


def run_probe(ir: DomainIR, p_target: int) -> ProbeResult:
    """Run backward + forward recurrence for one P target."""
    bw_reports, root_k, bw_wall, bw_mem = _backward_recurrence(ir, p_target)
    fw_reports, fw_wall, fw_mem = _forward_recurrence(ir, p_target)
    max_live_bytes = max((r.bytes_live for r in bw_reports), default=0)
    return ProbeResult(
        p_target=p_target,
        song_colors=ir.song_colors,
        backward=bw_reports,
        forward=fw_reports,
        root_completions_k=root_k,
        max_live_bytes=max_live_bytes,
        hit_wall_at=bw_wall if bw_wall is not None else bw_mem,
        hit_mem_at=bw_mem,
    )


def _print_sharing_findings(direction: str, reports: list[LayerReport]) -> None:
    """Surface axes where merge collapsed dramatically (sharing wins) and
    axes where every option survived as a distinct state (wall candidates).
    """
    print()
    print(f"  Merge findings ({direction}):")
    print(
        f"  {'idx':>3}  {'layer':<34} {'options':>9} {'live_states':>14} "
        f"{'ratio':>10}"
    )
    print("  " + "-" * 80)
    sharing_wins: list[tuple[int, str, int, int, float]] = []
    wall_candidates: list[tuple[int, str, int, int, float]] = []
    for r in reports:
        if r.n_options <= 1:
            continue
        if r.live_states >= CAP:
            continue  # capped, no clean ratio
        ratio = r.live_states / r.n_options
        if r.live_states < 100 and r.n_options > 1000:
            sharing_wins.append((r.idx, r.name, r.n_options, r.live_states, ratio))
        elif r.live_states >= r.n_options:
            wall_candidates.append((r.idx, r.name, r.n_options, r.live_states, ratio))
        print(
            f"  {r.idx:>3}  {r.name:<34} {r.n_options:>9,} {r.live_states:>14,} "
            f"{ratio:>10.4f}"
        )
    print()
    if sharing_wins:
        print("  Sharing wins (n_options -> <100 live):")
        for idx, name, nopts, live, ratio in sharing_wins:
            print(f"    - idx={idx} {name}: {nopts:,} -> {live:,} (ratio {ratio:.6f})")
    else:
        print("  No dramatic sharing wins (no axis with >1000 options -> <100 live).")
    if wall_candidates:
        print("  Wall candidates (merge did NOT collapse, live >= options):")
        for idx, name, nopts, live, ratio in wall_candidates:
            print(f"    - idx={idx} {name}: {nopts:,} -> {live:,} (ratio {ratio:.4f})")
    else:
        print("  No clean wall candidates from merge ratio alone.")


def main() -> int:
    webport_root = _resolve_webport_root()
    if not webport_root.is_dir():
        print(f"ERROR: webport_root not found: {webport_root}", file=sys.stderr)
        return 2

    print(f"webport_root: {webport_root}")
    print(f"python: {sys.version.split()[0]}")
    print(f"numpy: {np.__version__}")
    print(f"CAP (per-layer state cap): {CAP:,}")
    print(f"BYTES_PER_STATE: {BYTES_PER_STATE} (7-dim int32 vec; residual derived)")
    print(f"MEM_BUDGET_BYTES: {MEM_BUDGET_BYTES:,} ({MEM_BUDGET_BYTES // (1024**3)} GB)")

    # v1 yardstick row: "Report 4: New World (Hard)" -- single-color Chill,
    # gearPower 5834. The chart file lists Primary=Chill, Secondary=Chill;
    # the DomainIR treats (Chill, Chill) as the single-color case
    # (song_colors=("Chill",)) because the two-color fiber requires two
    # DISTINCT colors for the c1/c2 split to be meaningful.
    song_colors: tuple[str, ...] = ("Chill",)
    song_name = "Report 4 New World (Hard)"

    print()
    print("=" * 98)
    print(f"  Building DomainIR: song_colors={song_colors}, song_name={song_name!r}")
    print("=" * 98)
    try:
        ir = build_domain_ir(webport_root, song_colors=song_colors, song_name=song_name)
    except Exception as exc:
        print(f"BUILD FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"  axes: {len(ir.axes)}")
    print(f"  pw: {ir.pw.tolist()}")
    print(f"  upgrade_total_max: {ir.upgrade_total_max}")
    print(f"  gem_max_per_type: {ir.gem_max_per_type}")
    print(f"  upgrade_max_per_type: {ir.upgrade_max_per_type}")

    targets = (5834, 500)
    results: list[ProbeResult] = []
    for p_target in targets:
        print()
        print("#" * 98)
        print(f"  PROBE: P_target = {p_target}, song_colors = {song_colors}")
        print("#" * 98)
        try:
            res = run_probe(ir, p_target)
        except Exception as exc:
            print(f"PROBE FAILED at P={p_target}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        results.append(res)

        _print_layer_table("Backward pass (last -> first):", res.backward, len(ir.axes))
        _print_layer_table("Forward pass (first -> last):", res.forward, len(ir.axes))
        _print_sharing_findings("backward pass", res.backward)
        _print_sharing_findings("forward pass", res.forward)

        print()
        print(f"  Root completion count K = {res.root_completions_k:,}")
        print(f"  Max live bytes (backward) = {res.max_live_bytes:,} ({res.max_live_bytes / (1024**2):.1f} MB)")
        if res.hit_wall_at is not None:
            wall_layer = ir.axes[res.hit_wall_at]
            print(
                f"  WALL: backward pass capped at layer idx={res.hit_wall_at} "
                f"({wall_layer.name}, {len(wall_layer.options):,} options)"
            )
        else:
            print("  WALL: none -- backward pass stayed under the 1M cap at every reported layer.")
        if res.hit_mem_at is not None:
            print(f"  MEM-CAP: backward pass hit the 2GB budget at layer idx={res.hit_mem_at}.")

    # Final verdict.
    print()
    print("=" * 98)
    print("  VERDICT")
    print("=" * 98)
    gateway = results[0]
    if gateway.hit_wall_at is None and gateway.max_live_bytes < MEM_BUDGET_BYTES:
        max_live = max((r.live_states for r in gateway.backward), default=0)
        print(
            f"  Gateway top-1 (P=5834): no layer capped at 1M. Max live states "
            f"(backward) = {max_live:,}. Max live bytes = {gateway.max_live_bytes:,}."
        )
        if max_live < 100_000:
            print("  -> Backward recurrence + P predicate ALONE breaks the wall.")
            print("     20s target is credible; K1.a (with S) will be tighter still.")
        else:
            print("  -> Live states exceed the 10^5 credibility threshold but stay under 1M.")
            print("     P-only predicate is not enough to break the wall cleanly; K1.a needed.")
    else:
        wl = gateway.hit_wall_at
        wl_name = ir.axes[wl].name if wl is not None else "?"
        print(f"  Gateway top-1 (P=5834): WALL at backward layer idx={wl} ({wl_name}).")
        print("  -> Backward recurrence + P predicate does NOT break the wall.")
        print("     K1.a (with S) is required to bring live state volume down.")

    print()
    print("  Per-target summary:")
    for r in results:
        max_bw = max((rr.live_states for rr in r.backward), default=0)
        max_fw = max((rr.live_states for rr in r.forward), default=0)
        print(
            f"    P={r.p_target:>5}: K={r.root_completions_k:>10,}  "
            f"max_bw_live={max_bw:>10,}  max_fw_live={max_fw:>10,}  "
            f"max_bw_bytes={r.max_live_bytes:>14,}  "
            f"wall={'yes@'+str(r.hit_wall_at) if r.hit_wall_at is not None else 'no'}"
        )

    print()
    print("=" * 98)
    print("  probe complete")
    print("=" * 98)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
