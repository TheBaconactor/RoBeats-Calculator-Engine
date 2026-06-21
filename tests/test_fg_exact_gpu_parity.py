"""GPU parity gate for the macOS-exact FG scorer (Task A.2, Approach A).

Runs the integer soft-float FG scorer on ti.vulkan (MoltenVK) and asserts it is
bit-for-bit identical to the CPU f64 reference (tools/fg_gpu_port/fg_exact_ref.py).
Marked `gpu` (only runs under `-m gpu`). Validated to 200,000 samples by hand;
trimmed here for suite speed.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "fg_gpu_port"))


@pytest.mark.gpu
def test_fg_softfloat_gpu_parity_vulkan():
    import softfloat_taichi as sft
    bad = sft._run("vulkan", 3000)
    assert bad == 0, f"{bad} GPU/CPU score mismatches"
