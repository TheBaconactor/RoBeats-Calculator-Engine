"""
Compatibility surface for the genetic solver entry points.

Large implementation details live in `genetic_pipeline.py`; this module keeps
the public import path stable and forwards runtime monkeypatch overrides used
by tests and local profiling hooks.
"""

from __future__ import annotations

from . import genetic_pipeline as _pipeline

# Runtime-overridable hooks/settings used by tests and profiling.
_GPU_NATIVE_AVAILABLE = _pipeline._GPU_NATIVE_AVAILABLE
_GPU_NATIVE_GA_VULKAN_RETRIES = getattr(_pipeline, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0)
_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS = getattr(_pipeline, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0)
GPU_GA_GENS_PER_MIGRATION = _pipeline.GPU_GA_GENS_PER_MIGRATION
_require_gpu_api = _pipeline._require_gpu_api
emit_profile_event = _pipeline.emit_profile_event
build_fg_group_meta = _pipeline.build_fg_group_meta
analyze_ga_redundancy_from_runs_payload = _pipeline.analyze_ga_redundancy_from_runs_payload
summarize_ga_redundancy_record = _pipeline.summarize_ga_redundancy_record
write_ga_redundancy_audit_record = _pipeline.write_ga_redundancy_audit_record


def _sync_runtime_overrides() -> None:
    _pipeline._GPU_NATIVE_AVAILABLE = _GPU_NATIVE_AVAILABLE
    _pipeline._GPU_NATIVE_GA_VULKAN_RETRIES = _GPU_NATIVE_GA_VULKAN_RETRIES
    _pipeline._GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS = _GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS
    _pipeline.GPU_GA_GENS_PER_MIGRATION = GPU_GA_GENS_PER_MIGRATION
    _pipeline._require_gpu_api = _require_gpu_api
    _pipeline.emit_profile_event = emit_profile_event
    _pipeline.build_fg_group_meta = build_fg_group_meta
    _pipeline.analyze_ga_redundancy_from_runs_payload = analyze_ga_redundancy_from_runs_payload
    _pipeline.summarize_ga_redundancy_record = summarize_ga_redundancy_record
    _pipeline.write_ga_redundancy_audit_record = write_ga_redundancy_audit_record


def decode_gpu_native_ga_runs_payload(*args, **kwargs):
    _sync_runtime_overrides()
    return _pipeline.decode_gpu_native_ga_runs_payload(*args, **kwargs)


def run_gpu_native_ga_runs_payload_prebuilt(*args, **kwargs):
    _sync_runtime_overrides()
    return _pipeline.run_gpu_native_ga_runs_payload_prebuilt(*args, **kwargs)


def solve_coevolution_genetic(*args, **kwargs):
    _sync_runtime_overrides()
    return _pipeline.solve_coevolution_genetic(*args, **kwargs)


def __getattr__(name: str):
    return getattr(_pipeline, name)


__all__ = [
    "decode_gpu_native_ga_runs_payload",
    "run_gpu_native_ga_runs_payload_prebuilt",
    "solve_coevolution_genetic",
]
