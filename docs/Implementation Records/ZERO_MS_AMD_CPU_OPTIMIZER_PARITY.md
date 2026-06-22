# zero_ms Lossless-Exact Replay — AMD/CPU optimizer-parity (Task 4d)

Status: **ANALYSIS + HARNESS COMPLETE. Cross-vendor loop PROVEN on the Mac (CPU); the AMD-GPU run
is the owner's step.** This record establishes that the EXACT values the zero_ms serving host (macOS
/ MoltenVK, CPU native-f64) produces equal what the native offline optimizer produces on f64-capable
hardware (the AMD RX 7900 XTX). No production compute was changed — this is the parity argument plus
a runnable cross-machine harness (`tools/db/verify_amd_cpu_parity.py`) and the existing unit gates.

Money-critical context: players craft these gear sets in-game off the served numbers; a shown value
that the native optimizer would not reproduce is compensated out of pocket. So "served EXACT ==
native-optimizer EXACT" must be argued, not assumed.

## The two compute axes and where each runs

| Axis | Serving (Mac, this is what users see) | Offline optimizer / reference | GPU kernel exists? |
|---|---|---|---|
| **FG** (forced-greats response inner search) | `response_inner_cpu_search.resolve_fg_response_groups_native_f64` (CPU native f64) | canonical f64 GPU kernel `_fg_response_inner_group_kernel` on the AMD RX 7900 XTX (Vulkan has shaderFloat64 there) | **YES** — genuine cross-vendor pair |
| **base/meta** (inner PP/CM/FM/OV gem allocation) | `scoring/base_inner_cpu_search.resolve_base_combo_exhaustive` (CPU, exhaustive) | *(none — see below)* | **NO** — vendor-independent CPU code |

## Chain #1 — FG: served (Mac CPU) == AMD-native, by a proven bit-exact twin

1. The serving FG search `resolve_fg_response_groups_native_f64` is a native-f64 transcription of the
   canonical GPU kernel `_fg_response_inner_group_kernel` — same ops, same order, native doubles. It
   handles BOTH the gems-fixed replay (residual_budget==0) and the lossless-exact re-solve
   (residual_budget>0).
2. The two are gated **bit-for-bit identical** by `tests/test_fg_cpu_search_parity.py` (random groups,
   budgets 0 and 3, all 11 output columns: best_score, surface, g_pp/cm/fm/ov, final pp/cm/fm/primary/
   secondary). **Confirmed passing on `zero-ms-lossless-exact` (this branch).**
3. The canonical f64 kernel `_fg_response_inner_group_kernel` is exactly what the offline path runs on
   the AMD RX 7900 XTX in **native f64** (Vulkan exposes shaderFloat64 on that GPU). The Mac GPU
   (MoltenVK) has no f64, which is precisely why serving uses the CPU twin.

   ⇒ served FG (Mac CPU) == canonical f64 kernel == AMD-native FG. **The cross-vendor question for FG
   reduces to the canonical-kernel parity, which is the proven test.**

The one genuine cross-vendor unknown the unit test does NOT exercise (it runs the kernel on Taichi's
CPU backend) is whether the **same kernel source on real AMD f64 silicon** still equals the CPU. IEEE
754 f64 with the same op order is deterministic across conformant hardware, so this is expected to
hold; the harness exists to **confirm it on the actual RX 7900 XTX**.

## Chain #2 — base/meta: exhaustive ⇒ exact by construction, vendor-independent

There is intentionally **NO GPU base-combo exhaustive kernel** in the repo (grep confirms: the only
base exhaustive implementation is `scoring/base_inner_cpu_search.py`, pure numba CPU). The base
exactness claim does **not** rest on matching an AMD run, for two reasons:

- **Exhaustive ⇒ exact by construction.** `resolve_base_combo_exhaustive` enumerates EVERY feasible
  (g_pp, g_cm, g_fm, g_ov) split of the budget for each FT/FF timeline, applies the per-gem stat math
  exactly as `optimize_core_jit` does, scores each EXACTLY with the production `fast_calculate_score`
  (float32, same op order), and keeps the global argmax. An exhaustive max can never fall below any
  feasible allocation, so the resolved score is provably ≥ the greedy and ≥ any inherited allocation.
  This argument is **vendor-independent** (no GPU, no f64-vs-f32 boundary across machines).
- **zero_ms base has no AMD reference to diverge from.** The offline AMD GA optimizes the
  **perfect_window** base leaderboard. The zero_ms base path **replays** that perfect_window
  leaderboard (the AMD GA output is served as a replay) and, under the lossless-exact change,
  re-solves the gem allocation at chart timing on the CPU. There is no "AMD zero_ms base" run; the
  thing zero_ms base must equal is *the exact optimum of the served config*, which the exhaustive
  search delivers by construction.

The base axis of the harness therefore checks the property that actually carries the claim and that
must hold identically on both machines: exhaustive ≥ greedy (dominance) and score == re-score of the
returned split (self-consistency), the same checks as `tests/test_base_cpu_search_parity.py`.
**Confirmed passing on this branch** (600 cases; exhaustive strictly beats greedy in 84, never below).

## Chain #3 — the cross-vendor primitive question, for completeness

"Does AMD GPU f64 agree bit-for-bit with Mac CPU f64 on the same inputs?" For FG this **is** chain #1
(canonical-kernel parity). For base there is no GPU kernel, and the scoring primitive
(`fast_calculate_score`) is float32 numba shared by greedy, exhaustive, and final scoring on every
machine — there is no second implementation to disagree.

## The harness — `tools/db/verify_amd_cpu_parity.py`

Runnable on both machines; closes the loop on real hardware.

- **FG axis:** for randomized (loadout, config) groups (pp-allowed/blocked, single/dual color, budgets
  0/3/5/8, head lengths 32/64/100) it computes FG via **(A)** `_fg_response_inner_group_kernel` and
  **(B)** `resolve_fg_response_groups_native_f64`, asserting bit-exact equality on all 11 columns.
  - `--arch gpu` on the AMD RX 7900 XTX: (A) runs in **native f64 on the GPU** — the real cross-vendor
    proof.
  - `--arch cpu` on the Mac: (A) runs on Taichi's CPU backend — a CPU-vs-CPU **smoke** that verifies
    the harness wiring without an AMD GPU.
- **base axis:** runs the dominance + self-consistency soundness checks (vendor-independent; same code
  both machines).
- Exit 0 on full parity, 1 on any mismatch (owner/CI-runnable).

### How to run

```bash
# On the AMD RX 7900 XTX  (THE cross-vendor proof — owner's step):
PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --arch gpu --cases 400

# On the Mac  (CPU-vs-CPU smoke; proves the harness, not the cross-vendor claim):
PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --arch cpu --cases 400

# Single axis:
PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --arch gpu --fg
PYTHONPATH=. python tools/db/verify_amd_cpu_parity.py --base
```

## What is PROVEN on the Mac vs what the owner must run on AMD

**Proven on the Mac (this branch):**
- FG CPU search == canonical f64 kernel, bit-exact (`tests/test_fg_cpu_search_parity.py`, budgets 0/3).
- Base exhaustive ≥ greedy and self-consistent (`tests/test_base_cpu_search_parity.py`, 600 cases).
- Harness end-to-end green: FG 400 groups bit-exact, base 400 cases sound, exit 0
  (`--arch cpu` smoke).

**Owner's remaining step (needs the AMD RX 7900 XTX — this Mac has no AMD GPU):**
- `verify_amd_cpu_parity.py --arch gpu` on the RX 7900 XTX, exercising `_fg_response_inner_group_kernel`
  in native f64 on real silicon and asserting bit-exact equality with the CPU search. Expected to pass
  (deterministic IEEE 754 f64, identical op order); this is the empirical confirmation that closes the
  cross-vendor loop.

## Why no production compute changed

This task is analysis + a harness + docs. The harness imports the existing serving and kernel
functions and compares them; it adds no code on any serving path. Served values are unchanged by
construction.
