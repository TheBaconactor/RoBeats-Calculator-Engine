import taichi as ti

from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers

_xorshift32 = kernels_helpers._xorshift32


@ti.func
def _stripe_idx(counts: ti.template(), s_idx: ti.i32, slot: ti.i32) -> ti.i32:
    stripe_count = ti.static(counts.shape[1])
    # Hash by song+slot so add/remove are consistent and updates spread across stripes.
    h = ti.u32(s_idx) * ti.u32(0x7F4A7C15) + ti.u32(slot) * ti.u32(0x9E3779B9)
    return ti.i32(h % ti.u32(stripe_count))


__all__ = ["_stripe_idx", "_xorshift32"]
