from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.lib import format as np_format

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.profile_events import emit_profile_event

from .response_cache_keys import (
    _fg_response_disk_cache_dir,
    _fg_response_disk_cache_path,
    _fg_response_cache_version,
)
from .response_cache_patterns import (
    SURFACE_PATTERN_COLUMNS,
    SURFACE_ROW_COLUMNS,
    expand_surface_rows,
    intern_surface_row_words,
    pack_surface_patterns,
    unpack_surface_patterns,
)
from .response_cache_types import (
    _BUNDLE_ARRAY_CACHE_MAX,
    _MEMORY_CACHE_MAX,
    _PAYLOAD_CACHE_MAX,
    _SCORING_BUNDLE_ARRAY_NAMES,
    _SURFACE_BUNDLE_PATH_ARRAY_NAME,
    _SURFACE_GENERATION_ARRAY_NAME,
    FgResponseFrontierCachePayload,
    FgResponseFrontierScoringBundle,
    _normalize_stat_key,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseFrontierResult

logger = logging.getLogger(__name__)

_frontier_cache: OrderedDict[tuple, FgResponseFrontierResult] = OrderedDict()
_payload_cache: OrderedDict[tuple, FgResponseFrontierCachePayload] = OrderedDict()
_bundle_array_cache: OrderedDict[tuple, dict[str, np.ndarray]] = OrderedDict()
_scoring_bundle_cache: OrderedDict[tuple, FgResponseFrontierScoringBundle] = OrderedDict()
_frontier_cache_last_access: dict[tuple, float] = {}
_payload_cache_last_access: dict[tuple, float] = {}
_bundle_array_cache_last_access: dict[tuple, float] = {}
_scoring_bundle_cache_last_access: dict[tuple, float] = {}
_frontier_cache_lock = threading.RLock()
_RESPONSE_BUNDLE_BUILD_PARALLELISM = 1
_response_bundle_build_slots = threading.BoundedSemaphore(int(_RESPONSE_BUNDLE_BUILD_PARALLELISM))
_NPZ_FAST_COMPRESS_LEVEL = 1
# Scoring surfaces live in two uncompressed, C-order, memmap-able sidecars next to the bundle
# .npz. Every logical surface row stores one exact head-pattern ID plus its three body counts;
# every distinct head pattern stores the eight fever/Great mask words plus four uint16 head
# coefficients packed into two uint32 words. The reader expands only requested row ranges, so the
# scorer still sees the canonical 11-word rows and four coefficients while disk traffic scales
# with the interned representation. IDs are uint32 for every chart -- no size-dependent format.
_SURFACE_ROW_SIDECAR_SUFFIX = ".surf_rows.npy"
_SURFACE_PATTERN_SIDECAR_SUFFIX = ".surf_patterns.npy"
_FILESYSTEM_COMPRESSION_MIN_BYTES = 4096
_MACOS_COMPRESSION_BATCH_FILES = 32
_MACOS_COMPRESSION_STAGING_DIR = ".macos_hfs_compression_staging"
# Cleanup-only names from V29. They are never read: the V30 version gate requires the compact
# row/pattern format. The stale-version sweeper must still remove them when it deletes a V29 bundle,
# otherwise every deliberate rotation strands the largest files from the old full pool.
_OBSOLETE_SURFACE_SIDECAR_SUFFIXES = (".surf_pool.npy", ".surf_coeffs.npy")

# Exact cache-output compatibility is narrower than the conservative DP source fingerprint. PR
# #141 changed the region physicality representation and cache staging ownership, but independent
# M1LLI0N/Calamity logical oracles matched every ordered surface at all 25,921 stat keys and both
# persisted V30 sidecars were byte-identical. Keep this ratified pair explicit: a future DP change
# receives a different current fingerprint and therefore inherits no compatibility automatically.
_EXACT_COMPATIBLE_PREDECESSOR_VERSIONS: dict[str, tuple[str, ...]] = {
    # Transactional publication adds an immutable sidecar generation to the metadata and carries
    # that storage snapshot through lazy readers. The producer, stat-key mapping, ordered logical
    # surfaces, and scores are unchanged, and legacy fixed-sidecar bundles remain directly readable.
    "fg-response-frontier-visible-first-v31+logic-04e3683c0789": (
        "fg-response-frontier-visible-first-v31+logic-52861c6156f1",
        "fg-response-frontier-visible-first-v31+logic-8953b1ce23bf",
        "fg-response-frontier-visible-first-v31+logic-f6b8a98a3729",
        "fg-response-frontier-visible-first-v31+logic-76140458b749",
        "fg-response-frontier-visible-first-v31+logic-822b279e81da",
        "fg-response-frontier-visible-first-v31+logic-eed4d4700100",
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Same-color Great scoring now preserves the production chart's two color slots and their
    # separate floor operations. This changes only surface scoring: the V31 producer, ordered
    # surfaces, stat-key mapping, and compact sidecars are unchanged. Preserve the complete
    # already-ratified lineage explicitly so the corrected scorer reuses the finished pool.
    "fg-response-frontier-visible-first-v31+logic-52861c6156f1": (
        "fg-response-frontier-visible-first-v31+logic-8953b1ce23bf",
        "fg-response-frontier-visible-first-v31+logic-f6b8a98a3729",
        "fg-response-frontier-visible-first-v31+logic-76140458b749",
        "fg-response-frontier-visible-first-v31+logic-822b279e81da",
        "fg-response-frontier-visible-first-v31+logic-eed4d4700100",
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Production behavior is unchanged: unreachable/test-only helpers moved out of fingerprinted
    # modules, and two zero-reference Numba helpers were deleted. The optimized producer, ordered
    # surfaces, stat-key mapping, and compact sidecars are identical, so preserve the complete
    # already-ratified V31 lineage explicitly.
    "fg-response-frontier-visible-first-v31+logic-8953b1ce23bf": (
        "fg-response-frontier-visible-first-v31+logic-f6b8a98a3729",
        "fg-response-frontier-visible-first-v31+logic-76140458b749",
        "fg-response-frontier-visible-first-v31+logic-822b279e81da",
        "fg-response-frontier-visible-first-v31+logic-eed4d4700100",
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Base now reaches the shared producer exclusively through Perfect-only actions. The deleted
    # body-only shortcut was guarded by use_forced_great_timing == 0, so the V31 forced-Great
    # producer cannot execute any removed statement. Its ordered surfaces and compact sidecars are
    # unchanged; keep the complete ratified lineage explicit and non-transitive.
    "fg-response-frontier-visible-first-v31+logic-f6b8a98a3729": (
        "fg-response-frontier-visible-first-v31+logic-76140458b749",
        "fg-response-frontier-visible-first-v31+logic-822b279e81da",
        "fg-response-frontier-visible-first-v31+logic-eed4d4700100",
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Trace reconstruction now derives fever_window_end_ms from the same centered activation hit
    # it serializes. The previous trace mixed that hit with the later legal interval edge. A complete
    # 25,921-key V31 bundle comparison matched every non-version NPZ member and both compact
    # sidecars byte-for-byte, so the correction changes only the reconstructed physical witness.
    "fg-response-frontier-visible-first-v31+logic-76140458b749": (
        "fg-response-frontier-visible-first-v31+logic-822b279e81da",
        "fg-response-frontier-visible-first-v31+logic-eed4d4700100",
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Issue #154 replaces Base timeline production and tightens Base/FG note-graph reconstruction.
    # The only conservative FG fingerprint input changed here is note_graph.py, which is not
    # imported by the cached V31 producer. The persisted response surfaces, stat-key mapping, and
    # compact sidecars are therefore unchanged. Keep every ratified V31 lineage explicit because
    # compatibility resolution is deliberately non-transitive.
    "fg-response-frontier-visible-first-v31+logic-822b279e81da": (
        "fg-response-frontier-visible-first-v31+logic-eed4d4700100",
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Reconstruction now centers the final score-parity activation interval instead of replacing
    # the producer's centered witness with its latest edge. Early-Great endpoint constraints are
    # intersected before centering. This changes note-graph timing guidance only; V31 producer
    # surfaces and cache bytes remain identical.
    "fg-response-frontier-visible-first-v31+logic-eed4d4700100": (
        "fg-response-frontier-visible-first-v31+logic-f67224918652",
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Witness decoding now preserves genuine fractional schedule windows and applies near-integer
    # repair only when float encoding would otherwise cross a canonical judgment edge. This is a
    # reconstruction correction; V31 producer surfaces and cache bytes remain identical.
    "fg-response-frontier-visible-first-v31+logic-f67224918652": (
        "fg-response-frontier-visible-first-v31+logic-11055cda9f1e",
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Exact schedule input_order makes an activation and its postactivation follower legal at the
    # same inclusive judgment edge. Removing the obsolete 0.001ms reconstruction-only gap changes
    # no V31 response surface or cache byte.
    "fg-response-frontier-visible-first-v31+logic-11055cda9f1e": (
        "fg-response-frontier-visible-first-v31+logic-60b24504b797",
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Reconstruction now materializes the complete cross-section Perfect/Great label map before
    # selecting any activation timing. This removes trace-order dependence from witness decoding;
    # the already-built V31 response surfaces and cache bytes are unchanged.
    "fg-response-frontier-visible-first-v31+logic-60b24504b797": (
        "fg-response-frontier-visible-first-v31+logic-9e160ae9539c",
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Exact schedule reconstruction now honors every producer-owned preactivation note while
    # choosing the activation witness. Those rows were already present in V31 bundles and already
    # validated by the weighted lane-aware producer; this only prevents reconstruction from also
    # treating them as postactivation label caps. No cache bytes change.
    "fg-response-frontier-visible-first-v31+logic-9e160ae9539c": (
        "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29",
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Note-graph replay now snaps only near-integer witness deltas on the same 0.1ms parity rule
    # used by the V31 timing envelope. Raw chart and genuinely fractional event times stay exact;
    # float32 representation drift no longer crosses a judgment edge. No cache bytes change.
    "fg-response-frontier-visible-first-v31+logic-d1bb9475bd29": (
        "fg-response-frontier-visible-first-v31+logic-cbd1843e029f",
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Same-time head-ramp reconstruction now projects the entire chart-order cluster through its
    # exact judgment intervals. Equal event timestamps remain ordered by canonical input_order;
    # no artificial 1ms separation is introduced at the inclusive late-Great edge. This changes
    # only the physical witness selected for an existing surface, not the V31 producer or bytes.
    "fg-response-frontier-visible-first-v31+logic-cbd1843e029f": (
        "fg-response-frontier-visible-first-v31+logic-da4da67d45fd",
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Exact schedule reconstruction projects preferred note timings into the persisted order's
    # judgment intervals, bounded by the preceding note and activation. This only corrects the
    # physical witness chosen for an already-selected surface; the V31 producer, bundle metadata,
    # and compact sidecars are unchanged. List the complete ratified lineage directly because
    # compatibility is deliberately non-transitive.
    "fg-response-frontier-visible-first-v31+logic-da4da67d45fd": (
        "fg-response-frontier-visible-first-v31+logic-76d9f97718b6",
        "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf",
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Raw per-note judgment intervals are now reconstructed separately from the monotone prefix-max
    # fever-end envelopes. This corrects witness validation only; the frontier producer and V31 bytes
    # are unchanged. Compatibility remains explicit and deliberately non-transitive.
    "fg-response-frontier-visible-first-v31+logic-b4ffccc942cf": (
        "fg-response-frontier-visible-first-v31+logic-0d29b422376d",
        "fg-response-frontier-visible-first-v31+logic-cb063da1d695",
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Canonical replay now schedules score-neutral body events by exact physical cross-lane order,
    # keeps score-bearing head rows in chart order, models Great's disjoint early/late bands, and
    # chains later sections after the prior wasted note. These modules reconstruct and validate an
    # already-selected surface; the Numba frontier producer and persisted V31 bytes are unchanged.
    # List both ratified V31 predecessors directly because compatibility is deliberately non-transitive.
    "fg-response-frontier-visible-first-v31+logic-cb063da1d695": (
        "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3",
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # Exact-schedule note-graph reconstruction now chains postactivation presses per lane instead
    # of imposing a foreign global chart-order chain across independent lanes, and a hold-head
    # activation may use the trace's legal upper edge when an endpoint requires it. Endpoint timing
    # also uses the exact strict cutoff rather than inventing a full 1ms gap. The cached V31 producer,
    # bundle metadata, and both compact sidecars are untouched; the conservative game-engine
    # fingerprint still moves because note_graph.py changed. Ratify only the exact production V31
    # pool built immediately before these reconstruction fixes.
    "fg-response-frontier-visible-first-v31+logic-e6d65b65c8f3": (
        "fg-response-frontier-visible-first-v31+logic-6c5b5bf6e4de",
    ),
    # The exact FG scorer again reads the immutable PP/CM/FM tables directly instead of
    # materializing three per-lane copies. Cached frontier production and ordered V30 bytes are
    # untouched. List every ratified predecessor directly: resolution is deliberately
    # non-transitive, so a future fingerprint cannot inherit compatibility by accident.
    "fg-response-frontier-visible-first-v30+logic-6126c01d035d": (
        "fg-response-frontier-visible-first-v30+logic-87b79fd8a257",
        "fg-response-frontier-visible-first-v30+logic-584d8e8c6077",
        "fg-response-frontier-visible-first-v30+logic-a6d09c0280bd",
    ),
    # Trace reconstruction now consumes the existing packed Numba reachability owner and the
    # breakpoint reader preserves caller dtypes instead of copying them to float64. Neither module
    # is called by the production cache producer; the changed response-builder CPU oracle remains
    # surface-identical to the Numba producer under the exact differential suite. The conservative
    # source fingerprint still rotates, so ratify both non-transitive predecessors explicitly.
    "fg-response-frontier-visible-first-v30+logic-87b79fd8a257": (
        "fg-response-frontier-visible-first-v30+logic-584d8e8c6077",
        "fg-response-frontier-visible-first-v30+logic-a6d09c0280bd",
    ),
    "fg-response-frontier-visible-first-v30+logic-584d8e8c6077": (
        "fg-response-frontier-visible-first-v30+logic-a6d09c0280bd",
    ),
}


def fg_response_compatible_cache_versions() -> tuple[str, ...]:
    """Current version followed by explicitly ratified, byte-compatible predecessors."""
    current = _fg_response_cache_version()
    predecessors = _EXACT_COMPATIBLE_PREDECESSOR_VERSIONS.get(current, ())
    return (current, *predecessors)


def _cache_key_with_version(cache_key: tuple, version: str) -> tuple:
    key = tuple(cache_key)
    if not key:
        raise ValueError("FG response cache key must contain a version")
    return (str(version), *key[1:])


def resolve_fg_response_bundle_path(cache_key: tuple) -> Path:
    """Resolve the canonical current path or an exact compatible predecessor path.

    Writes always target ``_fg_response_disk_cache_path(cache_key)``. This resolver is read-only and
    only considers a predecessor when the caller owns the current full cache key and the current
    content-addressed file is absent. Full NPZ/sidecar validation still gates every cache hit.
    """
    current_path = _fg_response_disk_cache_path(cache_key)
    if current_path.exists():
        return current_path
    key = tuple(cache_key)
    current = _fg_response_cache_version()
    if not key or str(key[0]) != current:
        return current_path
    for predecessor in fg_response_compatible_cache_versions()[1:]:
        predecessor_path = _fg_response_disk_cache_path(_cache_key_with_version(key, predecessor))
        if predecessor_path.exists():
            return predecessor_path
    return current_path


def _fg_response_cache_version_is_compatible(version: str) -> bool:
    return str(version) in fg_response_compatible_cache_versions()


def _purged_version_marker_value() -> str:
    return "\n".join(fg_response_compatible_cache_versions())


def _memory_cache_get_locked(
    cache: OrderedDict,
    last_access: dict[tuple, float],
    cache_key: tuple,
):
    cached = cache.get(cache_key)
    if cached is None:
        return None
    moment = time.monotonic()
    cache.move_to_end(cache_key)
    last_access[cache_key] = moment
    return cached


def _memory_cache_put_locked(
    cache: OrderedDict,
    last_access: dict[tuple, float],
    cache_key: tuple,
    value,
    *,
    max_entries: int,
) -> None:
    moment = time.monotonic()
    cache[cache_key] = value
    cache.move_to_end(cache_key)
    last_access[cache_key] = moment
    while len(cache) > int(max_entries):
        stale_key, _stale_value = cache.popitem(last=False)
        last_access.pop(stale_key, None)


class FgResponseSurfaceSidecarError(RuntimeError):
    """A current-version bundle .npz exists but its uncompressed surface sidecar is missing or
    disagrees in shape/dtype/row-count. This is a desync (e.g. interrupted migration), not a cache
    miss -- it must surface loudly so the human re-runs the re-pack, never silently rebuild."""


_UNSPECIFIED_SURFACE_GENERATION = object()


def _normalize_surface_generation(value: object) -> str | None:
    if value is None:
        return None
    array = np.asarray(value)
    if int(array.size) != 1:
        raise FgResponseSurfaceSidecarError("FG response frontier surface generation metadata is invalid")
    generation = str(array.item())
    if not generation:
        return None
    try:
        normalized = uuid.UUID(hex=generation).hex
    except (AttributeError, ValueError) as exc:
        raise FgResponseSurfaceSidecarError(
            "FG response frontier surface generation metadata is invalid"
        ) from exc
    if normalized != generation:
        raise FgResponseSurfaceSidecarError("FG response frontier surface generation metadata is invalid")
    return generation


def _surface_generation_from_bundle_data(data) -> str | None:
    if _SURFACE_GENERATION_ARRAY_NAME not in data.files:
        return None
    return _normalize_surface_generation(data[_SURFACE_GENERATION_ARRAY_NAME])


def _surface_generation_from_bundle_path(bundle_path: Path) -> str | None:
    path = Path(bundle_path)
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as data:
        return _surface_generation_from_bundle_data(data)


def _surface_sidecar_paths(
    bundle_path: Path,
    *,
    generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
) -> tuple[Path, Path]:
    """Return the immutable sidecars referenced by one bundle metadata generation.

    Existing V30/V31 bundles have no generation member and retain their fixed legacy sidecars.
    """
    base = Path(bundle_path)
    if base.suffix != ".npz":
        raise ValueError(f"FG response frontier bundle path must be a .npz: {base}")
    stem = base.name[: -len(".npz")]
    if generation is _UNSPECIFIED_SURFACE_GENERATION:
        normalized_generation = _surface_generation_from_bundle_path(base)
    else:
        normalized_generation = _normalize_surface_generation(generation)
    sidecar_stem = stem if normalized_generation is None else f"{stem}.{normalized_generation}"
    return (
        base.with_name(f"{sidecar_stem}{_SURFACE_ROW_SIDECAR_SUFFIX}"),
        base.with_name(f"{sidecar_stem}{_SURFACE_PATTERN_SIDECAR_SUFFIX}"),
    )


def _stale_surface_sidecar_paths(bundle_path: Path) -> tuple[Path, ...]:
    """All known sidecars to delete with a stale bundle; no obsolete format is readable."""
    base = Path(bundle_path)
    stem = base.name[: -len(".npz")]
    current = (
        base.with_name(f"{stem}{_SURFACE_ROW_SIDECAR_SUFFIX}"),
        base.with_name(f"{stem}{_SURFACE_PATTERN_SIDECAR_SUFFIX}"),
        *base.parent.glob(f"{stem}.*{_SURFACE_ROW_SIDECAR_SUFFIX}"),
        *base.parent.glob(f"{stem}.*{_SURFACE_PATTERN_SIDECAR_SUFFIX}"),
    )
    obsolete = tuple(base.with_name(f"{stem}{suffix}") for suffix in _OBSOLETE_SURFACE_SIDECAR_SUFFIXES)
    return tuple(dict.fromkeys((*current, *obsolete)))


def _surface_sidecar_paths_for_key(
    cache_key: tuple,
    *,
    generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
    bundle_path: str | Path | None = None,
) -> tuple[Path, Path]:
    resolved_path = resolve_fg_response_bundle_path(cache_key) if bundle_path is None else Path(bundle_path)
    return _surface_sidecar_paths(resolved_path, generation=generation)


def _remove_fg_response_bundle_files(bundle_path: Path) -> int:
    removed = 0
    for path in (bundle_path, *_stale_surface_sidecar_paths(bundle_path)):
        if not path.exists():
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue
        removed += 1
    return removed


def _live_fg_response_bundle_path(
    bundle_path: Path,
) -> Path | None:
    return bundle_path if bundle_path.exists() else None


def _surface_sidecar_files(directory: Path) -> tuple[Path, ...]:
    rows = directory.glob(f"*{_SURFACE_ROW_SIDECAR_SUFFIX}")
    patterns = directory.glob(f"*{_SURFACE_PATTERN_SIDECAR_SUFFIX}")
    return tuple(sorted((*rows, *patterns), key=lambda path: path.name))


def _file_allocated_bytes(path: Path) -> int:
    stat = path.stat()
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        get_compressed_size = ctypes.windll.kernel32.GetCompressedFileSizeW
        get_compressed_size.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        get_compressed_size.restype = wintypes.DWORD
        high = wintypes.DWORD(0)
        low = int(get_compressed_size(str(path), ctypes.byref(high)))
        return (int(high.value) << 32) | low
    blocks = getattr(stat, "st_blocks", None)
    if blocks is not None:
        return int(blocks) * 512
    return int(stat.st_size)


def _sidecar_needs_filesystem_compression(path: Path) -> bool:
    try:
        logical = int(path.stat().st_size)
        if logical < _FILESYSTEM_COMPRESSION_MIN_BYTES:
            return False
        return _file_allocated_bytes(path) >= logical
    except OSError:
        return False


def cache_dir_sidecars_need_compression() -> bool:
    """Whether startup should enter locked filesystem maintenance for exact sidecars."""
    if sys.platform not in {"darwin", "win32"}:
        return False
    directory = _fg_response_disk_cache_dir()
    if not directory.exists():
        return False
    return any(_sidecar_needs_filesystem_compression(path) for path in _surface_sidecar_files(directory))


def _compress_cache_dir_sidecars_windows(directory: Path) -> None:
    try:
        result = subprocess.run(
            ["compact", "/c", "/exe:XPRESS16K", "/s:" + str(directory)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3600,
            check=False,
        )
        if int(result.returncode) != 0:
            logger.warning("FG cache XPRESS16K compression exited %s", int(result.returncode))
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("FG cache XPRESS16K compression failed: %s", exc)


def _compress_cache_dir_sidecars_macos(directory: Path) -> None:
    candidates = tuple(
        path for path in _surface_sidecar_files(directory) if _sidecar_needs_filesystem_compression(path)
    )
    if not candidates:
        return
    staging = directory / _MACOS_COMPRESSION_STAGING_DIR
    try:
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir()
        for start in range(0, len(candidates), _MACOS_COMPRESSION_BATCH_FILES):
            batch = candidates[start : start + _MACOS_COMPRESSION_BATCH_FILES]
            result = subprocess.run(
                [
                    "/usr/bin/ditto",
                    "--hfsCompression",
                    "--nocache",
                    *(str(path) for path in batch),
                    str(staging),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3600,
                check=False,
            )
            if int(result.returncode) != 0:
                logger.warning("FG cache APFS/HFS+ compression exited %s", int(result.returncode))
                return
            staged_batch = tuple(staging / path.name for path in batch)
            for source, staged in zip(batch, staged_batch, strict=True):
                if not staged.is_file() or int(staged.stat().st_size) != int(source.stat().st_size):
                    logger.warning("FG cache APFS/HFS+ copy validation failed: %s", source)
                    return
            for source, staged in zip(batch, staged_batch, strict=True):
                os.replace(staged, source)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("FG cache APFS/HFS+ compression failed: %s", exc)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def compress_cache_dir_sidecars() -> None:
    """Losslessly compress exact sidecars while preserving the mmap-visible file bytes.

    Windows uses one NTFS WOF XPRESS16K pass. macOS copies uncompressed sidecars in bounded batches
    through ``ditto --hfsCompression`` and atomically replaces each original; APFS/HFS+ then
    decompresses pages transparently for ``np.load(mmap_mode="r")``. Unsupported platforms are a
    no-op because no general filesystem-transparent compressor exists there. This is an external
    filesystem boundary and never changes cache semantics or the logic fingerprint.
    """
    directory = _fg_response_disk_cache_dir()
    if not directory.exists():
        return
    if sys.platform == "win32":
        _compress_cache_dir_sidecars_windows(directory)
    elif sys.platform == "darwin":
        _compress_cache_dir_sidecars_macos(directory)


_PURGED_VERSION_MARKER = ".purged_version"


def purge_stale_version_cache_files(*, authorize_rotation: bool = False) -> int:
    """Delete bundles outside the current exact compatibility lineage.

    Versions outside the explicit compatible set are dead weight because every reader rejects them,
    but deleting a provisioned full pool is an explicit production rotation, never routine startup
    maintenance. Without ``authorize_rotation`` this function detects any incompatible bundle and
    fails loudly before unlinking a byte. An authorized prebuild sweeps once per compatibility-lineage
    change, guarded by a `.purged_version` marker so later startup stays O(1). Returns the number of
    files removed. External filesystem boundary: unreadable/corrupt bundles are left in place rather
    than guessed at, and if any unlink fails (e.g. a locked file) the marker remains unwritten so the
    next authorized prebuild retries instead of stranding the file.
    """
    directory = _fg_response_disk_cache_dir()
    if not directory.exists():
        return 0
    compatible = frozenset(fg_response_compatible_cache_versions())
    marker_value = _purged_version_marker_value()
    marker = directory / _PURGED_VERSION_MARKER
    try:
        if marker.read_text(encoding="utf-8").strip() == marker_value:
            return 0
    except OSError:
        pass
    stale_bundles: list[Path] = []
    for npz in directory.glob("*.npz"):
        try:
            with np.load(npz, allow_pickle=False) as bundle:
                version = str(bundle["version"].item()) if "version" in bundle.files else None
        except Exception:
            # Any unreadable/corrupt bundle (bad zip, corrupt member, IO error): keep it rather than
            # crash the whole sweep. This is the documented FS boundary, matching the bundle readers.
            version = None
        if version is None or version in compatible:
            continue
        stale_bundles.append(npz)
    if stale_bundles and not bool(authorize_rotation):
        raise RuntimeError(
            "FG response frontier cache contains "
            f"{len(stale_bundles)} incompatible bundle(s); preserved them because destructive "
            "cache rotation was not explicitly authorized"
        )

    removed = 0
    purge_complete = True
    for npz in stale_bundles:
        for stale in (npz, *_stale_surface_sidecar_paths(npz)):
            try:
                stale.unlink()
                removed += 1
            except FileNotFoundError:
                pass  # already absent: nothing to remove, not a retry-worthy failure
            except OSError:
                purge_complete = False  # locked/in-use: leave marker unwritten, retry next prebuild
    if purge_complete:
        try:
            marker.write_text(marker_value, encoding="utf-8")
        except OSError:
            pass
    return removed


def _save_surface_sidecar_atomic(path: Path, array: np.ndarray) -> None:
    """Write `array` as an uncompressed C-order .npy via tmp + os.replace.

    Uncompressed at the numpy layer so the reader can `np.load(..., mmap_mode="r")` and page rows
    lazily; on-disk size is reclaimed by the bulk NTFS pass at prebuild-end (see
    `compress_cache_dir_sidecars`), which keeps the bytes small while preserving the memmap path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp")
    try:
        with open(tmp, "wb") as handle:
            np_format.write_array(handle, np.ascontiguousarray(array), allow_pickle=False)
        os.replace(tmp, path)
    except Exception:
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _surface_sidecar_header(path: Path) -> tuple[tuple[int, ...], np.dtype] | None:
    try:
        with open(path, "rb") as handle:
            version = np_format.read_magic(handle)
            if version == (1, 0):
                shape, _fortran_order, dtype = np_format.read_array_header_1_0(handle)
            elif version == (2, 0):
                shape, _fortran_order, dtype = np_format.read_array_header_2_0(handle)
            else:
                return None
    except Exception:
        return None
    return tuple(int(dim) for dim in shape), np.dtype(dtype)


def _open_surface_sidecar_memmap(path: Path, *, columns: int, dtype: np.dtype, row_count: int) -> np.ndarray:
    """Open a surface sidecar read-only memmap and fail loud on any shape/dtype/row-count drift."""
    if not path.exists():
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar is missing: {path}")
    memmap = np.load(path, mmap_mode="r", allow_pickle=False)
    if int(memmap.ndim) != 2 or int(memmap.shape[1]) != int(columns):
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar has invalid shape: {path}")
    if memmap.dtype != np.dtype(dtype):
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar has invalid dtype: {path}")
    if int(memmap.shape[0]) != int(row_count):
        raise FgResponseSurfaceSidecarError(
            "FG response frontier surface sidecar row count disagrees with bundle metadata: "
            f"{int(memmap.shape[0])} != {int(row_count)} ({path})"
        )
    return memmap


def _gather_surface_ranges(
    memmap: np.ndarray,
    *,
    ranges: tuple[tuple[int, int], ...],
    out: np.ndarray,
) -> None:
    """Slice-copy each [start, start+count) row block out of the memmap into `out`, range order preserved."""
    row_count = int(memmap.shape[0])
    out_cursor = 0
    for start, count in ranges:
        end = int(start) + int(count)
        if end > row_count:
            raise ValueError("FG response surface range exceeds cached rows")
        out[out_cursor : out_cursor + int(count)] = memmap[int(start) : end]
        out_cursor += int(count)
    if out_cursor != int(out.shape[0]):
        raise ValueError("FG response surface gather produced the wrong row count")


def _as_uint8_exact(name: str, values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if array.size:
        min_value = int(np.min(array))
        max_value = int(np.max(array))
        info = np.iinfo(np.uint8)
        if min_value < int(info.min) or max_value > int(info.max):
            raise ValueError(f"{name} exceeds persisted uint8 bounds: {min_value}..{max_value}")
    return np.asarray(array, dtype=np.uint8)


def _persisted_packed_frontier_metadata(
    packed_frontiers: dict[str, np.ndarray],
    *,
    surface_row_count: int,
    surface_pattern_count: int,
) -> dict[str, np.ndarray]:
    """Slim-.npz metadata for a packed bundle. Surfaces live in the sidecars, not here.

    The explicit row/pattern counts pin both sidecar shapes so the reader can fail loud on any
    sidecar/npz desync without guessing from IDs or per-frontier offsets.
    """
    return {
        "frontier_meta": np.asfortranarray(np.asarray(packed_frontiers["frontier_meta"], dtype=np.int32)),
        "first_offsets": np.asarray(packed_frontiers["first_offsets"], dtype=np.int32),
        "first_counts": np.asarray(packed_frontiers["first_counts"], dtype=np.int32),
        "first_surface_row_count": np.asarray(int(surface_row_count), dtype=np.int64),
        "first_surface_pattern_count": np.asarray(int(surface_pattern_count), dtype=np.int64),
    }


def _memory_get(cache_key: tuple) -> FgResponseFrontierResult | None:
    with _frontier_cache_lock:
        frontier = _memory_cache_get_locked(_frontier_cache, _frontier_cache_last_access, cache_key)
        return frontier if isinstance(frontier, FgResponseFrontierResult) else None


def _frontier_is_complete(frontier: FgResponseFrontierResult | None) -> bool:
    return frontier is not None and bool(frontier.first_frontier)


def _memory_put(cache_key: tuple, frontier: FgResponseFrontierResult) -> None:
    if not frontier.first_frontier:
        raise ValueError("FG response frontier cache requires first-frontier surfaces")
    with _frontier_cache_lock:
        _memory_cache_put_locked(
            _frontier_cache,
            _frontier_cache_last_access,
            cache_key,
            frontier,
            max_entries=_MEMORY_CACHE_MAX,
        )


def _payload_memory_get(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    with _frontier_cache_lock:
        payload = _memory_cache_get_locked(_payload_cache, _payload_cache_last_access, cache_key)
        return payload if isinstance(payload, FgResponseFrontierCachePayload) else None


def _payload_memory_put(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    with _frontier_cache_lock:
        _memory_cache_put_locked(
            _payload_cache,
            _payload_cache_last_access,
            cache_key,
            payload,
            max_entries=_PAYLOAD_CACHE_MAX,
        )


def reset_fg_response_frontier_payload_cache() -> None:
    with _frontier_cache_lock:
        _frontier_cache.clear()
        _frontier_cache_last_access.clear()
        _payload_cache.clear()
        _payload_cache_last_access.clear()
        _bundle_array_cache.clear()
        _bundle_array_cache_last_access.clear()
        _scoring_bundle_cache.clear()
        _scoring_bundle_cache_last_access.clear()


def release_fg_response_song_memory(bundle_key: tuple) -> int:
    """Evict every in-memory cache entry for one song's response-frontier surfaces.

    Called once a song's FG scoring is complete: the ~0.5-1.5 GB surface pool it loaded is no
    longer needed for the rest of this run, so drop it from every memory tier instead of letting
    it sit until the entry-count LRU (`_MEMORY_CACHE_MAX`/`_BUNDLE_ARRAY_CACHE_MAX`) evicts it.
    Without this the surfaces accumulate one-per-scored-song and
    trip the memory guard after only a few dozen songs. Lossless: any later access rebuilds from
    the on-disk bundle.

    Every cache keys its entries as ``(version, song_key, *ref_axes, <suffix>)`` (bundle marker,
    stat key, or stat-key tuple); the shared per-song prefix is the bundle key without its
    trailing marker, so match on that to sweep the scoring bundle, slim metadata, frontier and
    payload tiers together. Returns the number of entries removed.
    """
    if not bundle_key:
        return 0
    prefix = tuple(bundle_key[:-1])
    if not prefix:
        return 0
    n = len(prefix)
    removed = 0
    with _frontier_cache_lock:
        for cache, last_access in (
            (_scoring_bundle_cache, _scoring_bundle_cache_last_access),
            (_bundle_array_cache, _bundle_array_cache_last_access),
            (_frontier_cache, _frontier_cache_last_access),
            (_payload_cache, _payload_cache_last_access),
        ):
            stale = [key for key in cache if key[:n] == prefix]
            for key in stale:
                cache.pop(key, None)
                last_access.pop(key, None)
                removed += 1
    return removed


def _save_payload(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    from .response_cache_serde import _pack_frontiers
    from .response_inner_host import _precompute_surface_head_coeffs

    path = _fg_response_disk_cache_path(cache_key)
    surface_generation = uuid.uuid4().hex
    row_sidecar, pattern_sidecar = _surface_sidecar_paths(path, generation=surface_generation)
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
        frontiers = payload.frontiers
        frontier_id_by_object = {id(frontier): idx for idx, frontier in enumerate(frontiers)}
        sorted_items = sorted(payload.frontier_by_key.items())
        packed_frontiers = _pack_frontiers(frontiers)
        first_surface_pool = np.ascontiguousarray(
            np.asarray(packed_frontiers["first_surface_pool"], dtype=np.uint32)
        )
        surface_row_count = int(first_surface_pool.shape[0])
        stat_keys = np.asarray([key for key, _frontier in sorted_items], dtype=np.int32)
        first_surface_head_len = min(int(payload.total_notes), 100)
        # Pattern identity is established from every exact mask word before coefficient work.
        # Head coefficients depend only on those words plus head_len, so computing them for the
        # unique table is identical to computing N logical rows and selecting each pattern's first
        # row, while deleting the N x 4 int32 + uint16 coefficient staging arrays.
        first_surface_rows, first_surface_pattern_words = intern_surface_row_words(first_surface_pool)
        first_surface_pattern_coeffs = _precompute_surface_head_coeffs(
            first_surface_pattern_words,
            head_len=int(first_surface_head_len),
        )
        first_surface_patterns = pack_surface_patterns(
            first_surface_pattern_words,
            first_surface_pattern_coeffs,
        )
        surface_pattern_count = int(first_surface_patterns.shape[0])
        # Publish immutable generation sidecars first, then atomically replace the sole metadata
        # pointer. Readers that already opened the old metadata keep resolving the old immutable
        # files; an interruption before the final replace leaves that generation fully readable.
        _save_surface_sidecar_atomic(row_sidecar, first_surface_rows)
        _save_surface_sidecar_atomic(pattern_sidecar, first_surface_patterns)
        _save_npz_fast_compressed(
            tmp,
            {
                "version": np.asarray(_fg_response_cache_version()),
                _SURFACE_GENERATION_ARRAY_NAME: np.asarray(surface_generation),
                "stat_keys": np.asfortranarray(_as_uint8_exact("FG response stat keys", stat_keys)),
                "frontier_ids": np.asarray(
                    [frontier_id_by_object[id(frontier)] for _key, frontier in sorted_items],
                    dtype=np.int32,
                ),
                "raw_fill_by_ff": np.asarray(payload.raw_fill_by_ff, dtype=np.float64),
                "non_fever_base_by_ff": np.asarray(payload.non_fever_base_by_ff, dtype=np.int32),
                "real_time_by_ft": np.asarray(payload.real_time_by_ft, dtype=np.float64),
                "total_notes": np.asarray(int(payload.total_notes), dtype=np.int32),
                "long_notes": np.asarray(int(payload.long_notes), dtype=np.int32),
                "use_forced_great_timing": np.asarray(int(payload.use_forced_great_timing), dtype=np.int8),
                "first_surface_head_len": _as_uint8_exact(
                    "FG response first surface head length",
                    np.asarray(int(first_surface_head_len), dtype=np.int32),
                ),
                **_persisted_packed_frontier_metadata(
                    packed_frontiers,
                    surface_row_count=surface_row_count,
                    surface_pattern_count=surface_pattern_count,
                ),
            },
        )
        tmp.replace(path)
    except Exception:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def _save_npz_fast_compressed(path: Path, arrays: dict[str, np.ndarray]) -> None:
    with zipfile.ZipFile(
        path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=int(_NPZ_FAST_COMPRESS_LEVEL),
        allowZip64=True,
    ) as archive:
        for name, array in arrays.items():
            with archive.open(f"{name}.npy", mode="w", force_zip64=True) as handle:
                np_format.write_array(handle, np.asanyarray(array), allow_pickle=False)


def _load_payload(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    from .response_cache_serde import _unpack_frontiers

    path = _live_fg_response_bundle_path(resolve_fg_response_bundle_path(cache_key))
    if path is None:
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if not _fg_response_cache_version_is_compatible(version):
                return None
            surface_generation = _surface_generation_from_bundle_data(data)
            row_sidecar, pattern_sidecar = _surface_sidecar_paths(path, generation=surface_generation)
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            frontiers = _unpack_frontiers(
                data,
                row_sidecar=row_sidecar,
                pattern_sidecar=pattern_sidecar,
            )
            frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult] = {}
            for idx, key_row in enumerate(stat_keys):
                frontier_idx = int(frontier_ids[idx])
                if frontier_idx < 0 or frontier_idx >= len(frontiers):
                    return None
                key = _normalize_stat_key((int(key_row[0]), int(key_row[1])))
                frontier_by_key[key] = frontiers[frontier_idx]
            payload = FgResponseFrontierCachePayload(
                frontier_by_key=frontier_by_key,
                raw_fill_by_ff=np.asarray(data["raw_fill_by_ff"], dtype=np.float64),
                non_fever_base_by_ff=np.asarray(data["non_fever_base_by_ff"], dtype=np.int32),
                real_time_by_ft=np.asarray(data["real_time_by_ft"], dtype=np.float64),
                total_notes=int(np.asarray(data["total_notes"]).item()),
                long_notes=int(np.asarray(data["long_notes"]).item()),
                use_forced_great_timing=bool(int(np.asarray(data["use_forced_great_timing"]).item())),
            )
            if payload.raw_fill_by_ff.shape[0] != TOTAL_ROWS + 1 or payload.real_time_by_ft.shape[0] != TOTAL_ROWS + 1:
                return None
            return payload
    except FgResponseSurfaceSidecarError:
        # A current-version .npz whose surface sidecar is gone/mismatched is a desync, not a cache
        # miss. Surface it loudly (forces a re-pack) instead of deleting the .npz and silently
        # rebuilding from scratch.
        raise
    except Exception:
        _remove_fg_response_bundle_files(path)
        return None


def _payload_file_info_if_complete(path: Path, keys: Iterable[tuple[int, int]]) -> tuple[int, int, int] | None:
    requested = set(normalize_fg_response_stat_keys(keys))
    path = _live_fg_response_bundle_path(path)
    if path is None:
        return None
    required = {"version", *_SCORING_BUNDLE_ARRAY_NAMES}
    legacy_required = required - {_SURFACE_GENERATION_ARRAY_NAME}
    try:
        with np.load(path, allow_pickle=False) as data:
            files = set(data.files)
            # Slim .npz: exactly the metadata set, no surface chunk members. The surfaces are the two
            # uncompressed sidecars validated below. Legacy fixed-sidecar bundles remain readable;
            # every new write includes one immutable sidecar generation.
            if files not in (required, legacy_required):
                return None
            version = str(data["version"].item())
            if not _fg_response_cache_version_is_compatible(version):
                return None
            surface_generation = _surface_generation_from_bundle_data(data)
            row_sidecar, pattern_sidecar = _surface_sidecar_paths(path, generation=surface_generation)
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            meta = np.asarray(data["frontier_meta"], dtype=np.int32)
            surface_row_count = int(np.asarray(data["first_surface_row_count"]).item())
            surface_pattern_count = int(np.asarray(data["first_surface_pattern_count"]).item())
            first_offsets = np.asarray(data["first_offsets"], dtype=np.int64).reshape(-1)
            first_counts = np.asarray(data["first_counts"], dtype=np.int64).reshape(-1)
            raw_fill_by_ff = np.asarray(data["raw_fill_by_ff"])
            non_fever_base_by_ff = np.asarray(data["non_fever_base_by_ff"])
            real_time_by_ft = np.asarray(data["real_time_by_ft"])
            total_notes = int(np.asarray(data["total_notes"]).item())
            long_notes = int(np.asarray(data["long_notes"]).item())
            if int(stat_keys.ndim) != 2 or int(stat_keys.shape[1]) != 2:
                return None
            if int(frontier_ids.ndim) != 1 or int(stat_keys.shape[0]) != int(frontier_ids.shape[0]):
                return None
            if int(meta.ndim) != 2 or int(meta.shape[0]) <= 0:
                return None
            if int(first_offsets.shape[0]) != int(meta.shape[0]) or int(first_counts.shape[0]) != int(meta.shape[0]):
                return None
            if int(raw_fill_by_ff.shape[0]) != TOTAL_ROWS + 1:
                return None
            if int(non_fever_base_by_ff.shape[0]) != TOTAL_ROWS + 1 or int(real_time_by_ft.shape[0]) != TOTAL_ROWS + 1:
                return None
            if total_notes < 0 or long_notes < 0 or long_notes > total_notes:
                return None
            if int(np.asarray(data["first_surface_head_len"]).item()) != min(total_notes, 100):
                return None
            if surface_row_count < 0 or surface_pattern_count <= 0:
                return None
            if bool(np.any(first_offsets < 0)) or bool(np.any(first_counts <= 0)):
                return None
            max_surface_end = int(np.max(first_offsets + first_counts))
            if surface_row_count < max_surface_end:
                return None
            row_header = _surface_sidecar_header(row_sidecar)
            pattern_header = _surface_sidecar_header(pattern_sidecar)
            if row_header != ((surface_row_count, SURFACE_ROW_COLUMNS), np.dtype(np.uint32)):
                return None
            if pattern_header != ((surface_pattern_count, SURFACE_PATTERN_COLUMNS), np.dtype(np.uint32)):
                return None
            present: set[tuple[int, int]] = set()
            for idx, key_row in enumerate(stat_keys):
                frontier_idx = int(frontier_ids[int(idx)])
                if frontier_idx < 0 or frontier_idx >= int(meta.shape[0]):
                    return None
                present.add(_normalize_stat_key((int(key_row[0]), int(key_row[1]))))
            if not requested.issubset(present):
                return None
            return (
                int(total_notes),
                int(long_notes),
                int(len(requested)),
            )
    except Exception:
        _remove_fg_response_bundle_files(path)
        return None


def fg_response_cache_file_is_complete(cache_file: str | Path, *, stat_keys: Iterable[tuple[int, int]]) -> bool:
    try:
        path = Path(cache_file)
    except TypeError:
        return False
    return _payload_file_info_if_complete(path, stat_keys) is not None


def _payload_disk_info_if_complete(
    cache_key: tuple,
    keys: Iterable[tuple[int, int]],
) -> tuple[int, int, int] | None:
    return _payload_file_info_if_complete(resolve_fg_response_bundle_path(cache_key), keys)


def _load_bundle_array_members(cache_key: tuple, *, names: Iterable[str]) -> dict[str, np.ndarray]:
    requested = tuple(dict.fromkeys(str(name) for name in names))
    if not requested:
        raise ValueError("FG response frontier bundle array request was empty")
    snapshot_names = tuple(
        dict.fromkeys((*requested, _SURFACE_GENERATION_ARRAY_NAME, _SURFACE_BUNDLE_PATH_ARRAY_NAME))
    )
    with _frontier_cache_lock:
        cached = _memory_cache_get_locked(_bundle_array_cache, _bundle_array_cache_last_access, cache_key)
        if cached is not None and all(name in cached for name in snapshot_names):
            return {name: cached[name] for name in requested}
    bundle_path = resolve_fg_response_bundle_path(cache_key)
    path = _live_fg_response_bundle_path(bundle_path)
    if path is None:
        raise ValueError(f"FG response frontier bundle cache is missing: {bundle_path}")
    with np.load(path, allow_pickle=False) as data:
        version = str(data["version"].item())
        if not _fg_response_cache_version_is_compatible(version):
            raise ValueError("FG response frontier bundle cache version is invalid")
        missing = [
            name
            for name in snapshot_names
            if name not in (_SURFACE_GENERATION_ARRAY_NAME, _SURFACE_BUNDLE_PATH_ARRAY_NAME)
            and name not in data.files
        ]
        if missing:
            raise ValueError(f"FG response frontier bundle cache is missing arrays: {missing[:5]!r}")
        surface_generation = _surface_generation_from_bundle_data(data)
        loaded = {
            name: np.asarray(data[name])
            for name in snapshot_names
            if name not in (_SURFACE_GENERATION_ARRAY_NAME, _SURFACE_BUNDLE_PATH_ARRAY_NAME)
        }
        loaded[_SURFACE_GENERATION_ARRAY_NAME] = np.asarray(surface_generation or "")
        loaded[_SURFACE_BUNDLE_PATH_ARRAY_NAME] = np.asarray(str(path))
    with _frontier_cache_lock:
        cached = _bundle_array_cache.get(cache_key)
        cached_generation = None
        if cached is not None and _SURFACE_GENERATION_ARRAY_NAME in cached:
            cached_generation = _normalize_surface_generation(cached[_SURFACE_GENERATION_ARRAY_NAME])
        cached_path = None
        if cached is not None and _SURFACE_BUNDLE_PATH_ARRAY_NAME in cached:
            cached_path = str(np.asarray(cached[_SURFACE_BUNDLE_PATH_ARRAY_NAME]).item())
        if cached is None or cached_generation != surface_generation or cached_path != str(path):
            cached = {}
            _bundle_array_cache[cache_key] = cached
        cached.update(loaded)
        _bundle_array_cache_last_access[cache_key] = time.monotonic()
        while len(_bundle_array_cache) > int(_BUNDLE_ARRAY_CACHE_MAX):
            stale_key, _stale_value = _bundle_array_cache.popitem(last=False)
            _bundle_array_cache_last_access.pop(stale_key, None)
        _bundle_array_cache.move_to_end(cache_key)
        return {name: cached[name] for name in requested}


def _normalize_surface_ranges(ranges: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    normalized: list[tuple[int, int]] = []
    for start, count in ranges:
        start_i = int(start)
        count_i = int(count)
        if start_i < 0 or count_i <= 0:
            raise ValueError("FG response surface range is invalid")
        normalized.append((start_i, count_i))
    if not normalized:
        raise ValueError("FG response surface rows require at least one range")
    return tuple(normalized)


def _surface_counts_for_key(cache_key: tuple) -> tuple[int, int, str | None, Path]:
    arrays = _load_bundle_array_members(
        cache_key,
        names=(
            "first_surface_row_count",
            "first_surface_pattern_count",
            _SURFACE_GENERATION_ARRAY_NAME,
            _SURFACE_BUNDLE_PATH_ARRAY_NAME,
        ),
    )
    row_count = int(np.asarray(arrays["first_surface_row_count"]).item())
    pattern_count = int(np.asarray(arrays["first_surface_pattern_count"]).item())
    surface_generation = _normalize_surface_generation(arrays[_SURFACE_GENERATION_ARRAY_NAME])
    bundle_path = Path(str(np.asarray(arrays[_SURFACE_BUNDLE_PATH_ARRAY_NAME]).item()))
    if row_count < 0:
        raise ValueError("FG response frontier bundle has a negative surface row count")
    if pattern_count <= 0:
        raise ValueError("FG response frontier bundle has no surface head patterns")
    return int(row_count), int(pattern_count), surface_generation, bundle_path


def _surface_counts_from_sidecars(row_sidecar: Path, pattern_sidecar: Path) -> tuple[int, int]:
    row_header = _surface_sidecar_header(row_sidecar)
    pattern_header = _surface_sidecar_header(pattern_sidecar)
    if (
        row_header is None
        or len(row_header[0]) != 2
        or int(row_header[0][1]) != SURFACE_ROW_COLUMNS
        or row_header[1] != np.dtype(np.uint32)
    ):
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar has invalid shape: {row_sidecar}")
    if (
        pattern_header is None
        or len(pattern_header[0]) != 2
        or int(pattern_header[0][1]) != SURFACE_PATTERN_COLUMNS
        or pattern_header[1] != np.dtype(np.uint32)
    ):
        raise FgResponseSurfaceSidecarError(
            f"FG response frontier surface sidecar has invalid shape: {pattern_sidecar}"
        )
    row_count = int(row_header[0][0])
    pattern_count = int(pattern_header[0][0])
    if row_count < 0 or pattern_count <= 0:
        raise FgResponseSurfaceSidecarError("FG response frontier surface sidecar has invalid row counts")
    return row_count, pattern_count


def load_first_surface_scoring_rows(
    cache_key: tuple,
    ranges: Iterable[tuple[int, int]],
    *,
    surface_generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
    bundle_path: str | Path | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    started = time.perf_counter()
    normalized = _normalize_surface_ranges(ranges)
    if surface_generation is _UNSPECIFIED_SURFACE_GENERATION:
        surface_row_count, surface_pattern_count, resolved_generation, resolved_bundle_path = (
            _surface_counts_for_key(cache_key)
        )
        row_sidecar, pattern_sidecar = _surface_sidecar_paths_for_key(
            cache_key,
            generation=resolved_generation,
            bundle_path=resolved_bundle_path,
        )
    else:
        row_sidecar, pattern_sidecar = _surface_sidecar_paths_for_key(
            cache_key,
            generation=surface_generation,
            bundle_path=bundle_path,
        )
        surface_row_count, surface_pattern_count = _surface_counts_from_sidecars(row_sidecar, pattern_sidecar)
    row_count = sum(int(count) for _start, count in normalized)
    row_refs = np.empty((int(row_count), SURFACE_ROW_COLUMNS), dtype=np.uint32)
    load_t0 = time.perf_counter()
    row_memmap = _open_surface_sidecar_memmap(
        row_sidecar, columns=SURFACE_ROW_COLUMNS, dtype=np.dtype(np.uint32), row_count=surface_row_count
    )
    pattern_memmap = _open_surface_sidecar_memmap(
        pattern_sidecar,
        columns=SURFACE_PATTERN_COLUMNS,
        dtype=np.dtype(np.uint32),
        row_count=surface_pattern_count,
    )
    load_ms = float((time.perf_counter() - load_t0) * 1000.0)
    copy_t0 = time.perf_counter()
    # Slice-copy out of the read-only memmaps into freshly-owned contiguous arrays so the returned
    # arrays never alias a memmap (which could be evicted/closed across songs).
    _gather_surface_ranges(row_memmap, ranges=normalized, out=row_refs)
    rows, coeffs = expand_surface_rows(row_refs, pattern_memmap)
    copy_ms = float((time.perf_counter() - copy_t0) * 1000.0)
    emit_profile_event(
        component="fg_response_cache",
        event="surface_chunk_load",
        metrics={
            "ranges": int(len(normalized)),
            "chunks": 0,
            "rows": int(row_count),
            "load_ms": float(load_ms),
            "copy_ms": float(copy_ms),
            "elapsed_ms": float((time.perf_counter() - started) * 1000.0),
        },
    )
    return rows, coeffs


def load_first_surface_scoring_patterns(
    cache_key: tuple,
    ranges: Iterable[tuple[int, int]],
    *,
    surface_generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
    bundle_path: str | Path | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load the canonical compact scoring representation for requested frontier ranges.

    Returns ``(surface_pattern_ids, surface_counts, pattern_words, pattern_coeffs)``. Pattern IDs
    are remapped densely for this gather, but surface-row order is untouched; therefore exact-score
    ties retain the producer's original first-row priority.
    """
    started = time.perf_counter()
    normalized = _normalize_surface_ranges(ranges)
    if surface_generation is _UNSPECIFIED_SURFACE_GENERATION:
        surface_row_count, surface_pattern_count, resolved_generation, resolved_bundle_path = (
            _surface_counts_for_key(cache_key)
        )
        row_sidecar, pattern_sidecar = _surface_sidecar_paths_for_key(
            cache_key,
            generation=resolved_generation,
            bundle_path=resolved_bundle_path,
        )
    else:
        row_sidecar, pattern_sidecar = _surface_sidecar_paths_for_key(
            cache_key,
            generation=surface_generation,
            bundle_path=bundle_path,
        )
        surface_row_count, surface_pattern_count = _surface_counts_from_sidecars(row_sidecar, pattern_sidecar)
    row_count = sum(int(count) for _start, count in normalized)
    row_refs = np.empty((int(row_count), SURFACE_ROW_COLUMNS), dtype=np.uint32)
    load_t0 = time.perf_counter()
    row_memmap = _open_surface_sidecar_memmap(
        row_sidecar,
        columns=SURFACE_ROW_COLUMNS,
        dtype=np.dtype(np.uint32),
        row_count=surface_row_count,
    )
    pattern_memmap = _open_surface_sidecar_memmap(
        pattern_sidecar,
        columns=SURFACE_PATTERN_COLUMNS,
        dtype=np.dtype(np.uint32),
        row_count=surface_pattern_count,
    )
    load_ms = float((time.perf_counter() - load_t0) * 1000.0)
    copy_t0 = time.perf_counter()
    _gather_surface_ranges(row_memmap, ranges=normalized, out=row_refs)
    global_pattern_ids = np.asarray(row_refs[:, 0], dtype=np.uint64)
    if bool(np.any(global_pattern_ids >= int(surface_pattern_count))):
        raise ValueError("FG response surface row references an invalid head-pattern ID")
    unique_ids, local_ids = np.unique(global_pattern_ids, return_inverse=True)
    selected_patterns = np.ascontiguousarray(
        pattern_memmap[np.asarray(unique_ids, dtype=np.intp)],
        dtype=np.uint32,
    )
    pattern_words, pattern_coeffs = unpack_surface_patterns(selected_patterns)
    surface_counts = np.ascontiguousarray(row_refs[:, 1:4], dtype=np.int32)
    surface_pattern_ids = np.ascontiguousarray(local_ids, dtype=np.int32)
    copy_ms = float((time.perf_counter() - copy_t0) * 1000.0)
    emit_profile_event(
        component="fg_response_cache",
        event="surface_pattern_load",
        metrics={
            "ranges": int(len(normalized)),
            "rows": int(row_count),
            "patterns": int(pattern_words.shape[0]),
            "load_ms": float(load_ms),
            "copy_ms": float(copy_ms),
            "elapsed_ms": float((time.perf_counter() - started) * 1000.0),
        },
    )
    return surface_pattern_ids, surface_counts, pattern_words, pattern_coeffs


def _invalidate_bundle_array_views(bundle_key: tuple) -> None:
    with _frontier_cache_lock:
        _bundle_array_cache.pop(bundle_key, None)
        _bundle_array_cache_last_access.pop(bundle_key, None)
        _scoring_bundle_cache.pop(bundle_key, None)
        _scoring_bundle_cache_last_access.pop(bundle_key, None)


def _scoring_bundle_memory_get(bundle_key: tuple) -> FgResponseFrontierScoringBundle | None:
    with _frontier_cache_lock:
        cached = _memory_cache_get_locked(_scoring_bundle_cache, _scoring_bundle_cache_last_access, bundle_key)
        return cached if isinstance(cached, FgResponseFrontierScoringBundle) else None


def _scoring_bundle_memory_put(bundle_key: tuple, scoring_bundle: FgResponseFrontierScoringBundle) -> None:
    with _frontier_cache_lock:
        _memory_cache_put_locked(
            _scoring_bundle_cache,
            _scoring_bundle_cache_last_access,
            bundle_key,
            scoring_bundle,
            max_entries=_BUNDLE_ARRAY_CACHE_MAX,
        )
