# Custom frontier cache isolation and workspace admission

## Invariants

Official charts use the canonical persistent Base and Force-Greats frontier caches. Uploaded
custom charts must not publish into those caches or survive in process-global memory after their
request ends. Exact first-frontier reduction must also reject an impossible scratch allocation
before worker threads begin allocating it.

## Implementation

Custom service solves receive per-job Base and FG cache directories inside the disposable solve
workspace. In-process custom operations use a context-local temporary cache scope and bypass the
process-global frontier, payload, scoring, and bundle-array caches. Official solves retain the
existing persistent paths and memory caches.

Uploaded charts are limited to 4,000 replay events at the request boundary. First-frontier
admission computes the exact scratch bytes per worker from the workspace plan, multiplies by the
scheduler's maximum active reduction width, reserves up to 2 GiB (or 25% of currently available
memory), and raises `MemoryError` before allocation when the exact workspace cannot fit. Failure to
query optional host memory telemetry leaves the exact allocation path unchanged.

## Cache compatibility

The operational routing and admission checks do not change any admitted frontier or persisted
payload member. Fingerprints rotate to Base `41d3117fada0` and FG `9a025b3ab4a1`. The mappings
retain the immediate byte-proven `73245c017cbd` and `31fb6828e146` lineages respectively. The three
Issue #161 Base predecessors remain rejected everywhere.

## Complexity

The chart limit is O(lines) at the external request boundary. Admission is O(1); it replaces the
risk of partial multi-worker allocation with one exact preflight calculation. Cache scoping adds
constant-time context lookups and removes global-memory retention for custom requests.
