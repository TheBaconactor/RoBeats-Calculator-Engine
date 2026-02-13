import importlib.util
from pathlib import Path
import sys


def _load_decider_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "tools" / "bench" / "declare_fg_quality_drop.py"
    spec = importlib.util.spec_from_file_location("declare_fg_quality_drop", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {script_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_decider_declares_real_drop():
    mod = _load_decider_module()
    thresholds = mod.DecisionThresholds(
        alpha=0.05,
        min_pairs=12,
        bootstrap_iters=2000,
        min_song_support_frac=0.10,
        min_song_support_count=3,
    )
    # Strong positive pair deltas => A consistently better than B.
    pair_deltas = [1200.0] * 13 + [900.0] * 2
    # 8 songs clearly positive, 42 ties.
    song_medians = [100.0] * 8 + [0.0] * 42
    d = mod.decide_quality_drop(pair_deltas=pair_deltas, song_median_deltas=song_medians, thresholds=thresholds)
    assert d["declaration"] == "REAL_QUALITY_DROP_FOR_B"
    assert d["gates"]["drop_pair_gate"] is True
    assert d["gates"]["drop_song_gate"] is True


def test_decider_declares_no_drop():
    mod = _load_decider_module()
    thresholds = mod.DecisionThresholds(
        alpha=0.05,
        min_pairs=12,
        bootstrap_iters=2000,
        min_song_support_frac=0.10,
        min_song_support_count=3,
    )
    # Strong negative pair deltas => B consistently better or equal.
    pair_deltas = [-1200.0] * 13 + [-900.0] * 2
    # Song medians can be ties in practice; pair-level evidence should still declare no-drop.
    song_medians = [0.0] * 50
    d = mod.decide_quality_drop(pair_deltas=pair_deltas, song_median_deltas=song_medians, thresholds=thresholds)
    assert d["declaration"] == "NO_REAL_QUALITY_DROP_FOR_B"
    assert d["gates"]["no_drop_pair_gate"] is True


def test_decider_declares_inconclusive_when_mixed():
    mod = _load_decider_module()
    thresholds = mod.DecisionThresholds(
        alpha=0.05,
        min_pairs=12,
        bootstrap_iters=2000,
        min_song_support_frac=0.10,
        min_song_support_count=3,
    )
    pair_deltas = [1000.0, -1000.0] * 8
    song_medians = [0.0] * 50
    d = mod.decide_quality_drop(pair_deltas=pair_deltas, song_median_deltas=song_medians, thresholds=thresholds)
    assert d["declaration"] == "INCONCLUSIVE"
