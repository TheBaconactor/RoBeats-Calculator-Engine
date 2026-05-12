from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadRefsOutcome:
    response: GpuResponse
    last_ref_arrays_sig: bytes | None


def execute_load_refs(
    request: GpuRequest,
    *,
    last_ref_arrays_sig: bytes | None,
    load_ref_arrays_fn,
    ref_arrays_sig_fn,
) -> LoadRefsOutcome:
    """Load reference arrays, skipping redundant uploads when the content signature matches."""
    ref_arrays = request.payload["ref_arrays"]
    sig = ref_arrays_sig_fn(ref_arrays)
    if sig is None or sig != last_ref_arrays_sig:
        load_ref_arrays_fn(ref_arrays)
        last_ref_arrays_sig = sig

    return LoadRefsOutcome(
        response=GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        ),
        last_ref_arrays_sig=last_ref_arrays_sig,
    )


def ref_arrays_sig(ref_arrays: Any) -> bytes | None:
    """
    Stable content signature for `ref_arrays` dict to avoid redundant uploads.
    """
    try:
        from .taichi_gem.api.initialization import _ref_arrays_sig as _taichi_ref_arrays_sig
    except Exception as e:
        logger.debug(f"gpu_executor:ref_arrays_sig: {e}")
        return None
    try:
        return _taichi_ref_arrays_sig(ref_arrays)
    except Exception as e:
        logger.debug(f"gpu_executor:ref_arrays_sig: {e}")
        return None
