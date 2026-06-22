"""Release oracle for the Task 4b provably-safe zero_ms re-solve skip (bit-exact).

The zero_ms Lossless-Exact Replay re-solves the gem allocation per (loadout, tier, color) on the
CPU-exact paths. Task 4b adds a PROVABLY-SOUND skip: the re-solve depends on the active config ONLY
through the frozen baseline->tier stat ``delta`` (``_tier_delta_signature``), so two configs whose
delta is byte-equal feed a byte-identical re-solve input and therefore produce a byte-identical
result -- the skip re-solves ONCE per distinct delta signature and reuses it. The identity / any
zero-effect (tier, color) collapses to the empty signature.

MONEY-CRITICAL: a false skip = a wrong served score = real money lost. This module is the bit-exact
release gate proving the skip-enabled production path is byte-identical to a forced ALWAYS-re-solve
path over a sweep of (tier x color x sampled loadouts). It also proves the skip actually FIRES (so a
green run is not vacuous) and that the empty/identity signature is exercised.

Real-DB + song-file gated (skips cleanly when the evolution DB or the song .txt files are absent, as
on a bare CI checkout); CPU-only (no GPU/frontier-cache dependency on the zero_ms path).
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load the measure-tool module by path (it lives under tools/, not an importable package) so the
# test reuses its validated real-data loaders rather than re-deriving them.
_GAP_SCRIPT = REPO_ROOT / "tools" / "db" / "measure_lossless_exact_replay_gap.py"
_SPEC = importlib.util.spec_from_file_location("measure_lossless_exact_replay_gap_for_skip_test", _GAP_SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
GAP = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = GAP
_SPEC.loader.exec_module(GAP)

from gear_optimizer.core.config import load_config
from gear_optimizer.core.team_buff import normalize_team_buff
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.database import get_best_loadouts, get_evolution_db_path
from gear_optimizer.data.loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
from gear_optimizer.helpers.song_helpers import team_buff_tiers
from gear_optimizer.helpers.song_helpers.team_buff_tiers import build_team_buff_tier_db_batches


# Sweep axes. Tiers span the full TeamBuff order (incl. the baseline T5 -> empty signature and NONE
# -> zero-effect) so the dedup collapses several cells; colors include the song default plus an
# explicit non-default element so the color axis is exercised too.
_SWEEP_TIERS = ("NONE", "T1", "T5", "T10", "T20", "T50", "T51")
_SWEEP_COLORS = ("", "Beat")  # "" = song-default team color (no override); "Beat" = non-default
_TIMING_MODE = "zero_ms"
_PER_SONG_LIMIT = 2
_MAX_SONGS = 2


def _canonical(obj):
    """Stable JSON for byte-exact dict comparison (numpy/tuples -> lists/strings)."""
    return json.dumps(obj, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def _resolve_real_db_path() -> Path | None:
    """Resolve a POPULATED team_buff_loadouts DB for the sweep.

    NOTE: tests/conftest.py mutates ``EVOLUTION_DB_PATH`` to a temp COPY of ``<repo>/evolution.db``
    (empty on a bare worktree), so we cannot rely on it here. Probe, in order: an explicit
    ``ROBEATS_SWEEP_DB`` env, the conftest-set ``EVOLUTION_DB_PATH`` IF it actually has loadouts, and
    the standard serving-host layout ``<repo>/../ExternalDatabases/evolution.db``. Return the first
    that exists AND contains rows; else None (-> the suite skips).
    """
    import os
    import sqlite3

    candidates: list[Path] = []
    env_sweep = str(os.environ.get("ROBEATS_SWEEP_DB") or "").strip()
    if env_sweep:
        candidates.append(Path(env_sweep))
    try:
        cur = get_evolution_db_path()
        if cur:
            candidates.append(Path(str(cur)))
    except Exception:
        pass
    candidates.append(REPO_ROOT.parent / "ExternalDatabases" / "evolution.db")

    seen: set[str] = set()
    for cand in candidates:
        key = str(cand)
        if key in seen:
            continue
        seen.add(key)
        if not cand.exists():
            continue
        try:
            conn = sqlite3.connect(str(cand))
            try:
                row = conn.execute("SELECT COUNT(*) FROM team_buff_loadouts").fetchone()
            finally:
                conn.close()
        except Exception:
            continue
        if row and int(row[0] or 0) > 0:
            return cand
    return None


def _load_sweep_cases():
    """Return [(song_name, base_calc_song, cfg, cfg_dict, ref_arrays, entries)]; [] if no data."""
    db_path = _resolve_real_db_path()
    if db_path is None:
        return []

    cfg = load_config(str(REPO_ROOT / "config.ini"))
    cfg_dict = cfg_to_dict(cfg)
    ref_arrays = GAP._get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        return []

    from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg_dict

    baseline_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
    gears_by_name = get_gears_by_name_cached()
    minis_by_name = get_minis_by_name_cached()

    song_names = GAP._distinct_song_names(db_path=str(db_path), team_buff=str(baseline_team_buff))
    cases = []
    for song_name in song_names:
        if len(cases) >= _MAX_SONGS:
            break
        entries = get_best_loadouts(
            song_name,
            limit=_PER_SONG_LIMIT,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            team_buff=str(baseline_team_buff),
            db_path=str(db_path),
        )
        if not entries:
            continue
        song_file = GAP._song_file_from_name(song_name, details=entries[0].get("details"))
        if song_file is None or not song_file.exists():
            continue
        base_calc_song = get_base_calc_song(str(song_file), cfg_dict)
        cases.append((song_name, base_calc_song, cfg, cfg_dict, ref_arrays, entries[:_PER_SONG_LIMIT]))
    return cases


_CASES = _load_sweep_cases()
pytestmark = pytest.mark.skipif(
    not _CASES,
    reason="zero_ms skip bit-exact sweep needs the evolution DB + song .txt files (absent here)",
)


def _batches_for_color(*, base_calc_song, cfg_dict, ref_arrays, color):
    """Run the FULL production zero_ms path for ALL sweep tiers in ONE call at the given color.

    Passing every tier in a single ``build_team_buff_tier_db_batches`` call is what exercises the
    per-call signature dedup ACROSS tiers (the skip only fires within one call) -- so this is what
    makes the bit-exact comparison meaningful. Returns ``{tier: [rows]}``.
    """
    active_calc_song, base_color_override, target_color_override = GAP._prepare_active_calc_song(
        base_calc_song,
        timing_mode=_TIMING_MODE,
        team_buff_color_override=str(color),
        primary_element_override="",
        secondary_element_override="",
    )
    tiers = tuple(normalize_team_buff(t, default="T5") for t in _SWEEP_TIERS)
    batches = build_team_buff_tier_db_batches(
        entries=_CASES_ENTRIES_BY_SONG[base_calc_song["metadata"]["Song Name"]],
        calc_song=clone_calc_song(active_calc_song),
        ref_arrays=dict(ref_arrays),
        cfg_dict=dict(cfg_dict),
        limit=_PER_SONG_LIMIT,
        tiers=tiers,
        base_team_color_override=base_color_override,
        target_team_color_override=target_color_override,
        replay_surface="both",
        timing_mode=_TIMING_MODE,
    )
    return {t: batches.get(t, []) for t in tiers}


# Song-name -> entries (the production path keys re-solve witnesses by loadout_hash; entries must be
# the SAME objects across the skip / no-skip runs so only the skip differs).
_CASES_ENTRIES_BY_SONG = {c[0]: c[5] for c in _CASES}


@pytest.mark.parametrize("song_name,base_calc_song,cfg,cfg_dict,ref_arrays,entries", _CASES)
def test_skip_path_is_byte_identical_to_always_resolve(
    song_name, base_calc_song, cfg, cfg_dict, ref_arrays, entries, monkeypatch
):
    """For every (tier, color) in the sweep, the skip-enabled production batch must be byte-identical
    to a forced ALWAYS-re-solve batch. The forced path is produced by monkeypatching the dedup key to
    be unique per call, so the signature cache NEVER hits and each (loadout, tier) is freshly
    re-solved -- the strongest possible reference. All tiers run in ONE call per color so the dedup
    actually fires across tiers."""
    # 1) Skip ENABLED: the canonical production path (dedup by _tier_delta_signature). All tiers in
    #    one call per color -> the signature dedup collapses the tiers that share a delta.
    skip_batches = {
        color: _batches_for_color(
            base_calc_song=base_calc_song, cfg_dict=cfg_dict, ref_arrays=ref_arrays, color=color
        )
        for color in _SWEEP_COLORS
    }

    # 2) Skip DISABLED (reference): force a unique signature per call so the dedup cache can never hit
    #    -> every (loadout, tier) is re-solved from scratch (the "always re-solve" path). Same single
    #    call shape, so the ONLY difference between the two runs is whether the skip fires.
    _counter = itertools.count()
    monkeypatch.setattr(team_buff_tiers, "_tier_delta_signature", lambda _dm: ("__forced_unique__", next(_counter)))
    forced_batches = {
        color: _batches_for_color(
            base_calc_song=base_calc_song, cfg_dict=cfg_dict, ref_arrays=ref_arrays, color=color
        )
        for color in _SWEEP_COLORS
    }

    # 3) Byte-exact equality across the whole sweep (score + gems + witness + force + details), per
    #    (color, tier).
    for color in _SWEEP_COLORS:
        for tier in (normalize_team_buff(t, default="T5") for t in _SWEEP_TIERS):
            assert _canonical(skip_batches[color][tier]) == _canonical(forced_batches[color][tier]), (
                f"zero_ms skip diverged from always-re-solve for {song_name!r} at "
                f"(color={color!r}, tier={tier!r}) -- the provably-safe skip is NOT bit-exact "
                "(release blocker)."
            )


def test_skip_actually_fires_and_identity_signature_present():
    """Guard against a vacuous green: prove the dedup actually collapses cells in the sweep (>=2
    tiers share a signature) AND that the empty/identity signature appears (default tier, no color
    override). Uses the real config's baseline so the signatures match production."""
    song_name, base_calc_song, cfg, cfg_dict, ref_arrays, _entries = _CASES[0]
    from gear_optimizer.core.team_buff import (
        resolve_baseline_team_buff_from_cfg_dict,
        resolve_team_color_from_cfg_dict,
    )

    metadata = base_calc_song.get("metadata", {}) or {}
    primary_color = str(metadata.get("Primary Color") or "").strip()
    secondary_color = str(metadata.get("Secondary Color") or "").strip()
    base_team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
    base_team_color = resolve_team_color_from_cfg_dict(cfg_dict, primary_color=primary_color)

    sig_counts: dict[tuple, int] = {}
    for color in _SWEEP_COLORS:
        target_color = color or base_team_color
        for tier in _SWEEP_TIERS:
            delta = team_buff_tiers._team_buff_delta_map(
                base_team_buff=str(base_team_buff),
                target_team_buff=normalize_team_buff(tier, default="T5"),
                base_team_color=str(base_team_color),
                target_team_color=str(target_color),
            )
            delta_map = {"Perfect Points": int(delta.get("Perfect Points", 0))}
            if primary_color:
                delta_map[primary_color] = int(delta.get(primary_color, 0))
            if secondary_color:
                delta_map[secondary_color] = int(delta.get(secondary_color, 0))
            sig = team_buff_tiers._tier_delta_signature(delta_map)
            sig_counts[sig] = sig_counts.get(sig, 0) + 1

    # The empty (identity / zero-effect) signature must appear -- it is at least the baseline tier at
    # the baseline color, which the sweep includes.
    assert () in sig_counts, f"identity/empty signature never produced (got {sorted(sig_counts)})"
    # And the dedup must collapse SOMETHING (otherwise the skip never fires and the bit-exact test
    # above would be vacuous).
    assert any(count >= 2 for count in sig_counts.values()), (
        f"no signature repeated across the sweep -> the skip never fires; sig_counts={sig_counts}"
    )
