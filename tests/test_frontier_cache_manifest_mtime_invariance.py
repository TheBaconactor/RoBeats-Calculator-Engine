"""Regression guard for the frontier-cache manifest fast-path identity check.

Both the timeline and FG response-frontier caches mark recently-used bundles by bumping their
mtime via ``os.utime`` (idle-TTL retention/purge). The manifest fast-path must therefore key on
cache-file *size*, not *mtime* -- otherwise a retention touch invalidates the recorded identity and
the expensive per-file validator re-runs for every song on every startup (the measured FG defect:
fast-path hit 0/6704 -> ~100s warm verify vs timeline's ~9s).

CPU-only: exercises the shared ``build_manifest_plan`` directly (where the invariant lives), so it
covers both caches without GPU/Taichi or real bundle files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from gear_optimizer.solver.frontier_cache_manifest import build_manifest_plan

_VERSION_FIELD = "frontier_version"
_CACHE_VERSION = "v1"


def _plan(song_path: Path, manifest_path: Path, *, validator=None):
    return build_manifest_plan(
        [str(song_path)],
        manifest_path=manifest_path,
        cache_version=_CACHE_VERSION,
        version_field=_VERSION_FIELD,
        ref_sig_hex="ref",
        stat_sig_hex="stat",
        cache_file_validator=validator,
    )


def _seed_manifest_entry(song_path: Path, cache_path: Path, manifest_path: Path) -> None:
    """Record the song -> cache_file association the way ``apply_manifest_results`` would, so the
    next ``build_manifest_plan`` exercises the identity fast-path (not the cold no-entry miss)."""
    key = _plan(song_path, manifest_path).key_by_norm_path[os.path.abspath(song_path).casefold()]
    st = os.stat(cache_path)
    manifest_path.write_text(
        json.dumps(
            {
                "schema": 1,
                _VERSION_FIELD: _CACHE_VERSION,
                "entries": {
                    key: {
                        "cache_file": str(cache_path),
                        "cache_mtime_ns": int(st.st_mtime_ns),
                        "cache_size": int(st.st_size),
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_manifest_fast_path_survives_mtime_touch(tmp_path: Path) -> None:
    song_path = tmp_path / "Song.txt"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_path = cache_dir / "deadbeef.npz"
    manifest_path = cache_dir / "manifest_v1.json"
    song_path.write_bytes(b"chart-bytes")
    cache_path.write_bytes(b"x" * 4096)

    _seed_manifest_entry(song_path, cache_path, manifest_path)

    # Simulate the retention touch: identical bytes, a clearly different mtime (os.utime is exactly
    # what _touch_*_bundle_files does for idle-TTL bookkeeping).
    before_ns = cache_path.stat().st_mtime_ns
    future = cache_path.stat().st_mtime + 10_000.0
    os.utime(cache_path, (future, future))
    assert cache_path.stat().st_mtime_ns != before_ns, "precondition: the touch must move mtime"
    assert cache_path.stat().st_size == 4096

    calls = {"n": 0}

    def validator(_cache_file: str) -> bool:
        calls["n"] += 1
        return True

    plan = _plan(song_path, manifest_path, validator=validator)

    assert plan.hit_paths == (str(song_path),)
    assert plan.missing_paths == ()
    assert calls["n"] == 0, "mtime-only touch must hit the fast-path without re-validation"


def test_manifest_fast_path_still_detects_size_change(tmp_path: Path) -> None:
    # Negative control: size is the change-detector, so a real content change (different size) must
    # drop out of the fast-path and force re-validation.
    song_path = tmp_path / "Song.txt"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_path = cache_dir / "deadbeef.npz"
    manifest_path = cache_dir / "manifest_v1.json"
    song_path.write_bytes(b"chart-bytes")
    cache_path.write_bytes(b"x" * 4096)

    _seed_manifest_entry(song_path, cache_path, manifest_path)

    # Content actually changed (different size).
    cache_path.write_bytes(b"y" * 8192)

    calls = {"n": 0}

    def validator(_cache_file: str) -> bool:
        calls["n"] += 1
        return True

    plan = _plan(song_path, manifest_path, validator=validator)

    assert plan.hit_paths == (str(song_path),)  # re-validated complete -> still a hit
    assert calls["n"] == 1, "a real size change must drop to the validator, not silently fast-hit"
