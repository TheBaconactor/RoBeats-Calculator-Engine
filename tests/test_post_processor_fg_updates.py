import numpy as np
import pytest

from gear_optimizer.pipeline.post_processor_fg_updates import build_fg_update_state, canonicalize_fg_update_entries
from tests.songs_support import make_song


_FG_SURFACE = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def _mock_song(*, primary_color: str = "Rush", n_notes: int = 96):
    return make_song(
        np.linspace(0.0, 30.0, int(n_notes)),
        name="Test Song",
        primary=primary_color,
        lanes=np.arange(int(n_notes), dtype=np.int32) % 4,
    )


def test_canonicalize_fg_update_entries_uses_the_prepared_song_and_curves(monkeypatch):
    entries = [{"score": 123, "gear": ["G1"], "minis": ["M1"]}]
    song = _mock_song()
    curves = {"Perfect Points": [1.0]}
    calls = {}
    canonical_row = {
        "score": 456,
        "fg_base_score": 400,
        "fg_score": 500,
        "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
    }

    def fake_prepare_song(file_path):
        calls["prepare"] = file_path
        return song

    def fake_canonicalize(entries_arg, *, song, curves):
        calls["canonicalize"] = {
            "entries": entries_arg,
            "song": song,
            "curves": curves,
        }
        return [canonical_row]

    # FG persistence prepares the scoring-ready song through the canonical helper.
    monkeypatch.setattr("gear_optimizer.solver.song_preparation.prepare_song", fake_prepare_song)
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.persistence_authority.canonicalize_authoritative_fg_entries",
        fake_canonicalize,
    )

    result = canonicalize_fg_update_entries(
        entries,
        file_path="Data/Hard/Test Song.txt",
        curves=curves,
        song_name="Test Song",
    )

    assert result == [canonical_row]
    assert calls["prepare"] == "Data/Hard/Test Song.txt"
    passed = calls["canonicalize"]
    assert passed["entries"] == entries
    assert passed["curves"] is curves
    assert passed["song"] is song


def test_canonicalize_fg_update_entries_loads_the_curves_when_none_are_given(monkeypatch):
    entries = [{"score": 123}]
    song = _mock_song()
    loaded_curves = object()
    calls = {}

    monkeypatch.setattr("gear_optimizer.solver.song_preparation.prepare_song", lambda _fp: song)
    monkeypatch.setattr("gear_optimizer.pipeline.post_processor_fg_updates.load_stat_curves", lambda _path: loaded_curves)

    canonical_row = {
        "score": 123,
        "fg_base_score": 100,
        "fg_score": 125,
        "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
    }

    def fake_canonicalize(entries_arg, *, song, curves):
        calls["curves"] = curves
        return [canonical_row]

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.persistence_authority.canonicalize_authoritative_fg_entries",
        fake_canonicalize,
    )

    result = canonicalize_fg_update_entries(
        entries,
        file_path="Data/Hard/Test Song.txt",
        curves=None,
        song_name="Test Song",
    )

    assert result == [canonical_row]
    assert calls["curves"] is loaded_curves


def test_canonicalize_fg_update_entries_reraises_missing_frontier_cache(monkeypatch):
    """A missing required frontier cache must fail loudly, not be swallowed into base-only."""
    from gear_optimizer.solver.frontier_cache_errors import MissingFrontierCacheError

    song = _mock_song()
    monkeypatch.setattr("gear_optimizer.solver.song_preparation.prepare_song", lambda _fp: song)

    def fake_canonicalize(entries_arg, *, song, curves):
        raise MissingFrontierCacheError(
            "Timeline frontier payload is missing. Startup cache prebuild must build the "
            "candidate-independent all-FT/FF timeline frontier before runtime scoring."
        )

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.persistence_authority.canonicalize_authoritative_fg_entries",
        fake_canonicalize,
    )

    with pytest.raises(MissingFrontierCacheError):
        canonicalize_fg_update_entries(
            [{"score": 123, "force": {"ForceGreats": {}}}],
            file_path="Data/Hard/Test Song.txt",
            curves={"Perfect Points": [1.0]},
            song_name="Test Song",
        )


def test_missing_frontier_cache_error_is_valueerror_subclass():
    """Backward-compatible: existing `except ValueError` callers still catch the loud error."""
    from gear_optimizer.solver.frontier_cache_errors import MissingFrontierCacheError

    assert issubclass(MissingFrontierCacheError, ValueError)


def test_fg_canonicalization_prep_matches_prebuild_timeline_cache_key(tmp_path):
    """The deferred FG canonicalization must derive the SAME timeline frontier cache key
    as the startup prebuild, so the cache-keyed base replay hits the prebuilt artifact
    instead of raising "Timeline frontier payload is missing" and dropping the FG score."""
    from gear_optimizer.chart import load_chart
    from gear_optimizer.solver.song_preparation import prepare_song
    from gear_optimizer.solver.timing_envelope import time_song

    chart_path = tmp_path / "Test Song.txt"
    chart_path.write_text(
        "Song Name\tTest Song\nDifficulty\tHard\nPrimary Color\tRush\nSecondary Color\tFlow\n"
        "Last Note Time\t0.4\nLong Notes\t0\nSong Data\n0.0 1 0 1\n0.2 2 1 1\n0.4 3 2 1\n",
        encoding="utf-8",
    )

    # Startup prebuild prep (timeline_frontier_cache_prebuild) for the default timing mode.
    prebuild_key = time_song(load_chart(chart_path), "perfect_window").timeline_key

    assert prepare_song(str(chart_path)).timeline_key == prebuild_key


def test_canonicalize_fg_update_entries_rejects_missing_file_path():
    assert (
        canonicalize_fg_update_entries(
            [{"score": 123}],
            file_path="",
            curves={"Perfect Points": [1.0]},
            song_name="Test Song",
        )
        == []
    )


def test_build_fg_update_state_preserves_existing_state_and_reports_improving_fg():
    state = build_fg_update_state(
        {"queued_at": 123},
        [
            {"score": 100, "fg_score": 99, "force": {"ForceGreats": {"config": [1, 0]}}},
            {
                "score": 100,
                "fg_score": 125,
                "force": {"response_surface": _FG_SURFACE, "ForceGreats": {}},
                "details": {"ForceGreats": {}},
            },
            {"score": 100, "fg_score": 140},
        ],
    )

    assert state["queued_at"] == 123
    assert state["saw_fg_update"] is True
    assert state["saved_count"] == 3
    assert state["best_fg"] == 125
    assert len(state["fg_variants"]) == 3
    assert state["fg_variants"][1] == {
        "data": {"response_surface": _FG_SURFACE, "ForceGreats": {}, "Score": 125},
        "gear": [],
        "minis": [],
        "score": 100,
        "fg_score": 125,
        "_is_ga": False,
    }
