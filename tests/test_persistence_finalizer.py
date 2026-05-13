from gear_optimizer.persistence.finalizer import build_persistence_batch, build_persistence_result_payload


def test_build_persistence_batch_preserves_payload_shape():
    db_payload = {"score": 123}
    persist_entries = [{"score": 123, "gear": ["G"], "minis": []}]

    batch = build_persistence_batch(
        song="Song",
        db_key="Song::T5",
        db_payload=db_payload,
        persist_entries=persist_entries,
        log="done",
    )

    assert batch.as_result_payload() == {
        "song": "Song",
        "db_key": "Song::T5",
        "db_payload": db_payload,
        "persist_entries": persist_entries,
        "log": "done",
    }


def test_build_persistence_result_payload_returns_post_processor_shape():
    assert build_persistence_result_payload(
        song="Song",
        db_key="Song::T5",
        db_payload={"score": 1},
        persist_entries=[],
    ) == {
        "song": "Song",
        "db_key": "Song::T5",
        "db_payload": {"score": 1},
        "persist_entries": [],
        "log": "",
    }
