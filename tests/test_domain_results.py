from gear_optimizer.domain.results import PersistenceBatch


def test_persistence_batch_preserves_post_processor_result_payload_shape():
    db_payload = {"score": 123}
    persist_entries = [{"score": 123, "gear": ["G"], "minis": []}]

    batch = PersistenceBatch(
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
