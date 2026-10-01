from __future__ import annotations

import os
import pickle
import threading
import time
from concurrent.futures import Future
from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver.fg_materialization_worker import (
    build_fg_materialization_request,
)
from gear_optimizer.solver.fg_response_scoring.planner import (
    FgResponseFrontierPreparedBatch,
    FgResponseFrontierPreparedPlan,
)
from tests.native_song_factory import make_native_song
from tests.songs_support import make_song


def _echo_process_value(song_key: str, value: int) -> tuple[str, int]:
    return song_key, value


def test_fg_materialization_request_compacts_the_batches_and_pickles():
    from gear_optimizer.pipeline.results import SolvedLoadout
    from gear_optimizer.solver.fg_materialization_worker import FgMaterializationBatch
    from gear_optimizer.solver.fg_response_scoring.planner import FgJob

    base_stats = {"Vibe": 10}
    cache_key = ("Vibe", (("Vibe", 10),))
    job = FgJob(
        SolvedLoadout(tuple(f"gear-{idx}" for idx in range(6)), tuple(f"mini-{idx}" for idx in range(3))),
        "Vibe",
        base_stats,
        123,
        cache_key,
    )
    batch = SimpleNamespace(
        started=1.0,
        base_components=np.zeros((1, 7), dtype=np.int32),
        selected_color="Vibe",
        song=make_song([0.0, 0.5]),
        curves={"Perfect Points": np.zeros((1,), dtype=np.float32)},
        scoring_bundle=SimpleNamespace(cache_key=("bundle",)),
        driver_only=lambda: None,  # the owner's batch holds driver-side state the worker never reads
    )
    plan = FgResponseFrontierPreparedPlan(
        song=batch.song,
        curves=batch.curves,
        jobs=(job,),
        prepared_batches=(FgResponseFrontierPreparedBatch(rows=((cache_key, base_stats),), batch=batch),),
    )
    song = make_native_song(task_key="pickle-plan", song_name="Pickle Plan")
    song.runtime.fg.fg_response_frontier_plan = plan
    song.runtime.fg.fg_owner_score_map = {}

    request = build_fg_materialization_request(song)

    assert isinstance(request.plan.prepared_batches[0].batch, FgMaterializationBatch)
    copy = pickle.loads(pickle.dumps(request))
    assert (copy.song_key, copy.plan.jobs) == ("pickle-plan", (job,))


