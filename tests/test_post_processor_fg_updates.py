import numpy as np
import pytest

from gear_optimizer.pipeline.post_processor_fg_updates import build_fg_update_state, canonicalize_fg_update_entries


_FG_SURFACE = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def _mock_base_song(*, primary_color: str = "Rush", n_notes: int = 96) -> dict:
    timestamps = np.linspace(0.0, 30.0, int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Primary Color": primary_color,
            "Secondary Color": "Flow",
            "Song Name": "Test Song",
            "Difficulty": "Hard",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {
            "timestamps": timestamps,
            "note_types": np.ones(int(n_notes), dtype=np.int16),
            "lanes": np.arange(int(n_notes), dtype=np.int16) % 4,
        },
    }


def test_canonicalize_fg_update_entries_uses_calc_song_and_ref_arrays(monkeypatch):
    entries = [{"score": 123, "gear": ["G1"], "minis": ["M1"]}]
    base_calc_song = _mock_base_song()
    curves = {"Perfect Points": [1.0]}
    calls = {}
    canonical_row = {
        "score": 456,
        "fg_base_score": 400,
        "fg_score": 500,
        "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
    }

    def fake_get_base_calc_song(file_path):
        calls["song_io"] = file_path
        return base_calc_song

    def fake_canonicalize(entries_arg, *, calc_song, curves):
        calls["canonicalize"] = {
            "entries": entries_arg,
            "calc_song": calc_song,
            "curves": curves,
        }
        return [canonical_row]

    # FG persistence prepares the scoring-ready song through the canonical helper, which
    # resolves the base song via song_preparation's binding and applies the timing envelope.
    monkeypatch.setattr("gear_optimizer.solver.song_preparation.get_base_calc_song", fake_get_base_calc_song)
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
    assert calls["song_io"] == "Data/Hard/Test Song.txt"
    passed = calls["canonicalize"]
    assert passed["entries"] == entries
    assert passed["curves"] is curves
    assert passed["calc_song"]["metadata"].get("Primary Color") == "Rush"
    # The timeline/FG frontier cache key includes the timing-envelope context, so FG
    # persistence must apply the envelope or the cache-keyed replay looks up an artifact
    # the startup prebuild never wrote (-> "Timeline frontier payload is missing").
    assert passed["calc_song"]["metadata"].get("TimingEnvelopeApplied") is True


def test_canonicalize_fg_update_entries_loads_the_curves_when_none_are_given(monkeypatch):
    entries = [{"score": 123}]
    base_calc_song = _mock_base_song()
    loaded_curves = object()
    calls = {}

    monkeypatch.setattr(
        "gear_optimizer.solver.song_preparation.get_base_calc_song",
        lambda _fp, _cfg=None: base_calc_song,
    )
    monkeypatch.setattr("gear_optimizer.pipeline.post_processor_fg_updates.load_stat_curves", lambda _path: loaded_curves)

    canonical_row = {
        "score": 123,
        "fg_base_score": 100,
        "fg_score": 125,
        "force": {"ForceGreats": {"config": {"NonFever1": 1}}},
    }

    def fake_canonicalize(entries_arg, *, calc_song, curves):
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

    base_calc_song = _mock_base_song()
    monkeypatch.setattr(
        "gear_optimizer.solver.song_preparation.get_base_calc_song",
        lambda _fp, _cfg=None: base_calc_song,
    )

    def fake_canonicalize(entries_arg, *, calc_song, curves):
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


def test_fg_canonicalization_prep_matches_prebuild_timeline_cache_key(monkeypatch):
    """The deferred FG canonicalization must derive the SAME timeline frontier cache key
    as the startup prebuild, so the cache-keyed base replay hits the prebuilt artifact
    instead of raising "Timeline frontier payload is missing" and dropping the FG score."""
    from gear_optimizer.data.song_io import clone_calc_song
    from gear_optimizer.solver.song_preparation import build_prepared_calc_song
    from gear_optimizer.solver.taichi_gem.api.timeline import _song_timing_cache_key
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    base = _mock_base_song()

    # Startup prebuild prep: base song + timing envelope (timeline_frontier_cache_prebuild).
    prebuild_song = clone_calc_song(base)
    apply_timing_envelope(prebuild_song)
    prebuild_key = _song_timing_cache_key(prebuild_song)

    # Deferred FG canonicalization prep (post-fix): the same canonical helper.
    monkeypatch.setattr("gear_optimizer.solver.song_preparation.get_base_calc_song", lambda _fp, _cfg=None: base)
    canon_song = build_prepared_calc_song(fp="Data/Hard/Test Song.txt").calc_song
    canon_key = _song_timing_cache_key(canon_song)

    assert canon_key == prebuild_key


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
