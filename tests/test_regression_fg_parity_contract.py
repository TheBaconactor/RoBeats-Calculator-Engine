"""
Regression tests that lock the three FG/base parity contract invariants that broke during refactoring.

Pre-refactor working lineage: 9e194e58 -> 0ad22fd3
Refactor boundary that made this fragile: 4602c29f -> bb80284d -> bc381434

These tests enforce that the pipeline cannot silently regress again.
"""

import pytest


def _base_stats(pp: int = 100) -> dict:
    return {
        "Perfect Points": int(pp),
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 100,
        "Vibe": 100,
        "Chill": 100,
    }


# ── R1: BaseScore preservation ────────────────────────────────────────────────
# The GPU solver produces a paired-base BaseScore for the specific FT/FF/gem
# allocation. The variant builder must not silently overwrite it with the entry's
# best base score when the force payload already carries a valid paired-base value.


def test_r1_retained_fg_preserves_force_base_when_valid_and_lte_entry_base():
    """BaseScore=800 (valid paired) and entry_base=1000 -> must preserve 800."""
    from gear_optimizer.helpers.song_helpers.force_greats.retained_variants import (
        retain_and_build_fg_variants,
    )

    entry = {
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "score": 1000,
        "base_score": 1000,
        "fg_score": 1200,
        "force": {
            "BaseScore": 800,
            "Score": 1200,
            "BaseStats": _base_stats(100),
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }

    variants = retain_and_build_fg_variants(
        entry_items=[("h1", entry)],
        sig_results={},
        entry_sig={},
        loadout_entries={},
        direct_ga_items=[],
        loadouts_per_song_limit=1,
        entry_base_score_fn=lambda _entry: 1000,
    )

    assert variants
    assert variants[0]["base_score"] == 800
    assert variants[0]["data"]["BaseScore"] == 800
    assert variants[0]["data"]["Score"] == 1200


def test_r1b_retained_fg_uses_entry_base_when_force_base_is_zero():
    """Force BaseScore=0 means no paired-base; should use entry's best base."""
    from gear_optimizer.helpers.song_helpers.force_greats.retained_variants import (
        retain_and_build_fg_variants,
    )

    entry = {
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "score": 1000,
        "base_score": 1000,
        "fg_score": 1200,
        "force": {
            "BaseScore": 0,
            "Score": 1200,
            "BaseStats": _base_stats(100),
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }

    variants = retain_and_build_fg_variants(
        entry_items=[("h1", entry)],
        sig_results={},
        entry_sig={},
        loadout_entries={},
        direct_ga_items=[],
        loadouts_per_song_limit=1,
        entry_base_score_fn=lambda _entry: 1000,
    )

    assert variants
    assert variants[0]["base_score"] == 1000
    assert variants[0]["data"]["BaseScore"] == 1000


def test_r1c_retained_fg_rejects_force_base_when_gt_entry_base():
    """Inflated BaseScore (e.g., stale cached value > entry base) must be replaced."""
    from gear_optimizer.helpers.song_helpers.force_greats.retained_variants import (
        retain_and_build_fg_variants,
    )

    entry = {
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "score": 1000,
        "base_score": 1000,
        "fg_score": 1200,
        "force": {
            "BaseScore": 9999,
            "Score": 1200,
            "BaseStats": _base_stats(100),
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }

    variants = retain_and_build_fg_variants(
        entry_items=[("h1", entry)],
        sig_results={},
        entry_sig={},
        loadout_entries={},
        direct_ga_items=[],
        loadouts_per_song_limit=1,
        entry_base_score_fn=lambda _entry: 1000,
    )

    assert variants
    assert variants[0]["base_score"] == 1000
    assert variants[0]["data"]["BaseScore"] == 1000


# ── R2: Top-K keep-mask width ────────────────────────────────────────────────
# The keep-mask must cover at least max(LOADOUTS_PER_SONG_LIMIT, len(entry_items))
# so entries beyond the top-K window still get their FG force payload downloaded.


def test_r2_topk_keep_mask_covers_full_entry_set():
    """200 entries -> keep-mask must include at least 200 signatures."""
    from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_batching import (
        _build_topk_keep_signature_set,
    )

    N = 200
    items = []
    entry_sig: dict[int, str] = {}
    for i in range(N):
        entry = {
            "score": N - i,
            "base_score": N - i,
            "fg_score": 0,
        }
        entry_sig[id(entry)] = f"sig_{i}"
        items.append((f"h{i}", entry))

    result = _build_topk_keep_signature_set(
        items=items,
        entry_sig=entry_sig,
        group_signature_rows={},
        base_keep_n=len(items),
        fg_proxy_keep_n=len(items),
        max_keep_total=len(items),
    )
    assert len(result) == N, f"keep-mask covers {len(result)} sigs, expected {N}"


def test_r2b_topk_keep_mask_at_least_entry_count_guard():
    """max(LOADOUTS_PER_SONG_LIMIT, len(items)) must be the effective minimum."""
    from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_batching import (
        _build_topk_keep_signature_set,
    )

    N = 150
    items = []
    entry_sig: dict[int, str] = {}
    for i in range(N):
        entry = {"score": N - i, "base_score": N - i, "fg_score": 0}
        entry_sig[id(entry)] = f"sig_{i}"
        items.append((f"h{i}", entry))

    result = _build_topk_keep_signature_set(
        items=items,
        entry_sig=entry_sig,
        group_signature_rows={},
        base_keep_n=N,
        fg_proxy_keep_n=N,
        max_keep_total=N,
    )
    assert len(result) >= N


# ── R3: FG score presence after retention ────────────────────────────────────
# When sig_results contain FG improvements for some entries, the retention flow
# must surface those fg_scores so fg_candidates are correctly selected.


def test_r3_retained_fg_selections_include_fg_candidates_when_sig_results_present():
    """Entry without direct fg_score but with matching sig_result gets fg candidate treatment."""
    from gear_optimizer.helpers.song_helpers.force_greats.retained_variants import (
        retain_and_build_fg_variants,
    )

    entry = {
        "score": 1000,
        "base_score": 1000,
        "fg_score": 0,
        "force": {
            "BaseScore": 800,
            "Score": 1200,
            "BaseStats": _base_stats(100),
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
    }
    entry_sig = {id(entry): "sig_a"}
    sig_results = {
        "sig_a": {
            "fg_score": 1200,
            "base_score": 800,
            "force": {
                "BaseScore": 800,
                "Score": 1200,
                "FT": 9,
                "FF": 18,
                "GemCounts": {"Perfect Points": 1},
                "BaseStats": _base_stats(100),
                "ForceGreats": {"config": {"NonFever1": 1}},
            },
        }
    }

    variants = retain_and_build_fg_variants(
        entry_items=[("h1", entry)],
        sig_results=sig_results,
        entry_sig=entry_sig,
        loadout_entries={},
        direct_ga_items=[],
        loadouts_per_song_limit=10,
        entry_base_score_fn=lambda _entry: 1000,
    )

    assert variants
    assert variants[0]["fg_score"] == 1200
    assert variants[0]["base_score"] == 800


# ── R4: Database persistence contract ─────────────────────────────────────────
# Even when entry best base (1000) > force paired base (800), the database must
# persist the FG row when fg_score > paired base, not reject it.


def test_r4_db_persists_fg_when_fg_score_beats_paired_base(tmp_path, monkeypatch):
    """Entry base=1000, force base=800, fg=1200, force has valid config -> FG row must exist."""
    from gear_optimizer.data.database import (
        _base_details_from_force_payload,
        _unpack_stats_after_load,
        get_db_connection,
        get_loadout_hash,
        init_db,
        save_loadouts_batch,
    )

    db_path = tmp_path / "r4_fg_contract.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "pytest_r4_fg_persist_contract"
    gear = ["G1", "G2", "G3", "G4", "G5", "G6"]
    minis = ["M1", "M2", "M3"]
    h = get_loadout_hash(gear, minis)

    base_details = {
        "FT": 0,
        "FF": 0,
        "GemCounts": {},
        "Stats": _base_stats(100),
        "SelectedElement": "Rush",
        "PrimaryColor": "Rush",
        "SecondaryColor": "Flow",
        "Difficulty": "Hard",
    }
    force_payload = {
        "BaseScore": 800,
        "Score": 1200,
        "FT": 9,
        "FF": 18,
        "GemCounts": {"Perfect Points": 1},
        "BaseStats": _base_stats(100),
        "Selected Element": "Rush",
        "ForceGreats": {"config": {"NonFever1": 1}},
    }

    save_loadouts_batch(
        song_name,
        [
            {
                "score": 1000,
                "fg_score": 0,
                "gear": gear,
                "minis": minis,
                "details": base_details,
                "force": None,
            },
            {
                "score": 800,
                "fg_score": 1200,
                "gear": gear,
                "minis": minis,
                "details": {},
                "force": force_payload,
                "_deferred_fg_update": True,
            },
        ],
    )

    with get_db_connection(str(db_path)) as conn:
        base_row = conn.execute(
            "SELECT score, fg_score FROM team_buff_loadouts "
            "WHERE song_name=? AND team_buff='T5'",
            (song_name,),
        ).fetchone()
        fg_row = conn.execute(
            "SELECT score, fg_score FROM team_buff_fg_loadouts "
            "WHERE song_name=? AND team_buff='T5'",
            (song_name,),
        ).fetchone()

    assert base_row is not None
    assert int(base_row["score"]) == 1000
    assert int(base_row["fg_score"]) == 1200

    assert fg_row is not None, "FG row must exist when fg_score (1200) > paired base (800)"
    assert int(fg_row["score"]) == 800
    assert int(fg_row["fg_score"]) == 1200


# ── R5: sig_results_has_fg_improvement correctness ────────────────────────────


def test_r5_sig_results_has_fg_improvement_true_when_fg_beats_base():
    from gear_optimizer.helpers.song_helpers.force_greats.entry_resolution import (
        sig_results_has_fg_improvement,
    )

    sig_results = {
        "sig_a": {
            "fg_score": 1200,
            "base_score": 800,
            "force": {
                "BaseScore": 800,
                "Score": 1200,
                "ForceGreats": {"config": {"NonFever1": 1}},
            },
        }
    }
    assert sig_results_has_fg_improvement(sig_results=sig_results, sigs=["sig_a"])


def test_r5b_sig_results_has_fg_improvement_false_when_fg_lte_base():
    from gear_optimizer.helpers.song_helpers.force_greats.entry_resolution import (
        sig_results_has_fg_improvement,
    )

    sig_results = {
        "sig_b": {
            "fg_score": 800,
            "base_score": 1000,
            "force": {
                "BaseScore": 1000,
                "Score": 800,
                "ForceGreats": {"config": {"NonFever1": 1}},
            },
        }
    }
    assert not sig_results_has_fg_improvement(sig_results=sig_results, sigs=["sig_b"])


def test_r5c_sig_results_has_fg_improvement_false_when_no_force():
    from gear_optimizer.helpers.song_helpers.force_greats.entry_resolution import (
        sig_results_has_fg_improvement,
    )

    sig_results = {
        "sig_c": {"fg_score": 1200, "base_score": 800, "force": None},
    }
    assert not sig_results_has_fg_improvement(sig_results=sig_results, sigs=["sig_c"])
