"""Timing service mode -- the single policy home for the ``strict_zero_ms`` deploy flag.

A deployment may need to serve ONLY the ``zero_ms`` (fixed chart-time) timing model while the
input-aware ``perfect_window`` timing model is under development. That is a deploy-time service
posture (an external boundary, like ``serving_api`` / ``GPU_STRICT``), NOT a per-request behavior
toggle: the whole optimizer is prepared and scored for one timing model for the life of the
process, and the expensive ``perfect_window`` timeline frontier is never prebuilt.

The flag itself lives in ``env_config.ENV.strict_zero_ms`` (``ROBEATSMETA_STRICT_ZERO_MS``); this
module exposes the thin policy helpers that the forcing sites call so the decision is expressed in
ONE place and every caller stays a one-liner:

- ``strict_zero_ms()``                -> is this deployment zero_ms-only?
- ``prepared_timing_mode_override()`` -> the ``mode=`` to pass ``apply_timing_envelope`` at prep
                                          sites: ``"zero_ms"`` when strict, else the caller's value
                                          (default ``None`` == let the chart metadata decide).
- ``enforce_service_timing_mode()``   -> coerce a requested/selected timing_mode to the serviceable
                                          one at the request gate and tier re-solve: ``"zero_ms"``
                                          when strict, else the requested mode unchanged.

Flag OFF (the default, and the only state the standalone optimizer ever runs in) makes every helper
a no-op: ``prepared_timing_mode_override()`` returns ``None`` and ``enforce_service_timing_mode(m)``
returns ``m``, so the perfect_window default path is byte-for-byte unchanged. This is the "thin
gate": strict mode only forces the *mode input*; all preparation/scoring/frontier machinery below is
the one canonical implementation, so precise-mode changes are inherited automatically.

See docs/Implementation Records/STRICT_ZERO_MS_SERVICE_MODE.md.
"""

from __future__ import annotations

import logging

from gear_optimizer.core.env_config import ENV as _ENV

logger = logging.getLogger(__name__)

# The only timing model a strict-zero_ms deployment can serve.
SERVICE_ONLY_TIMING_MODE = "zero_ms"

_coercion_warned: set[str] = set()


def strict_zero_ms() -> bool:
    """True when this deployment serves only the ``zero_ms`` timing model (service mode)."""
    return bool(_ENV.strict_zero_ms)


def prepared_timing_mode_override(requested: str | None = None) -> str | None:
    """Timing ``mode`` to prepare a calc_song for.

    Strict deployment -> ``"zero_ms"`` (force every preparation to fixed chart time). Otherwise the
    caller's ``requested`` value verbatim (``None`` lets ``apply_timing_envelope`` resolve the
    chart's ``Timing Mode`` metadata, defaulting to ``perfect_window`` -- main's existing behavior).
    """
    if strict_zero_ms():
        return SERVICE_ONLY_TIMING_MODE
    return requested


def enforce_service_timing_mode(mode: str) -> str:
    """Coerce an already-validated timing mode to the one this deployment can serve.

    Strict deployment -> always ``"zero_ms"`` (a ``perfect_window`` request is served as zero_ms,
    warned once so the coercion is visible -- the ``perfect_window`` frontier is not built here).
    Otherwise the requested ``mode`` is returned unchanged.
    """
    if not strict_zero_ms():
        return mode
    normalized = str(mode or "").strip().lower()
    if normalized and normalized != SERVICE_ONLY_TIMING_MODE and normalized not in _coercion_warned:
        _coercion_warned.add(normalized)
        logger.warning(
            "[strict_zero_ms] deployment serves only %r; request for %r is served as %r "
            "(the perfect_window timing frontier is not built in this service mode).",
            SERVICE_ONLY_TIMING_MODE,
            normalized,
            SERVICE_ONLY_TIMING_MODE,
        )
    return SERVICE_ONLY_TIMING_MODE
