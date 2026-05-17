import queue

from gear_optimizer.solver.native_inflight_lifecycle import PostSender


def test_post_sender_forwards_items_to_post_queue():
    post_queue: queue.Queue[dict] = queue.Queue()
    sender = PostSender(post_queue)
    item = {"song": "Song A"}
    try:
        sender.send(item)
        assert post_queue.get(timeout=2.0) is item
    finally:
        sender.close(timeout=2.0)
