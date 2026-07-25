# Reference ScoreEngine Replay Oracle

Trouble-checking oracle that scores a reconstructed per-note trace through the **actual
reference `ScoreEngine`**, so the optimizer can be checked against the independent
scoring/combo/fever model — including which fever windows actually
activate and how many notes each captures.

## Why this is faithful (and its scope)
- `web/src/score/scoreEngine.ts` is Babylon-free (imports only `constants.ts`, `types.ts`,
  `gearStats.ts`, `judge.ts`) → Node-runnable after esbuild bundling.
- The replay loop here mirrors `game.ts:1064-1103` exactly (the `f94e933` physical-hit-time-order
  fix): events run in ascending `eventMs`, `advanceFeverTo(eventMs)` drains + runs the AUTO
  activation gate before each `registerHit`. `manualFever=false` (AUTO), matching replays and the
  meta sim (`replayDriver.ts:7-9`).
- **Scope caveat:** this is the reference *replay* order (decay → hit). The independently verified *live/server*
  path applies the hit to the power bar first, then advances per-frame decay — a different
  intra-event order. For the optimizer's surfaces the two are equivalent and authoritative:
  Perfect/Great-only, full combo, and a Perfect/Great while fever is active adds no fill/drain, so
  "was fever active at the hit" is decided by the decay-up-to-the-hit either way. The order WOULD
  matter for miss/whiff/early-release drain + wasted-fill; do not treat this as a general live/server
  scorer for such streams without reconciling the order.

## Build the bundle (once, or when origin/main changes)
Source origin/main WITHOUT touching the user's working tree:
```bash
git -C <local-reference-client> worktree add --detach <scratch> origin/main
node build_bundle.mjs \
  --src <scratch>/web/src \
  --esbuild <local-reference-client>
```
(`tsx` is NOT installed; `esbuild`/`tsc`/`vite` are. On Windows pass the native
`@esbuild/win32-x64/esbuild.exe`, not the `node_modules/esbuild/bin` shim.)

## Run
```bash
node oracle.mjs input.json   # or: cat input.json | node oracle.mjs -
```

### Input schema
```json
{
  "config":  { "hitCount": <int>, "hitObjectsCount": <int>, "lastNoteTimeSec": <float> },
  "statsdict": { "<GearStatType>": <rawStatPoints>, ... },
  "colors":  ["ColorBlue", ...],
  "events":  [ { "eventMs": <ms>, "result": "perfect|great|okay|miss",
                 "kind": "note|whiff|earlyRelease" }, ... ]
}
```
- `config.hitCount` = weighted rank-accuracy denominator; `hitObjectsCount` = fever-fill
  normaliser (taps + holds); `lastNoteTimeSec` = `(LastNoteTime_ms+1000)/1000` for the fever
  drain clock. Match `ScoreConfig` in `scoreEngine.ts`.
- `statsdict` keys are reference-engine `GEAR_STAT_TYPES` (`PerfectPoints`, `ComboMultiplier`,
  `FeverMultiplier`, `FeverTime`, `FeverFillRate`, `ColorBlue`, ...) carrying RAW stat point
  counts; the engine runs them through its own `fN` curves. Unknown keys throw (fail loud).
- `colors` = 0..2 color-stat keys (`colorStatForName("Chill")` → `"ColorBlue"`).
- `events` need NOT be pre-sorted — the oracle sorts by `(eventMs, input order)` like the plan
  builder. One entry per judged event (a tap once; a hold head AND tail). `j:"miss"` with
  `kind:"note"` = a real note timeout; `"whiff"/"earlyRelease"` ride the idle-no-op gate.

### Output
`{ score, chain, maxChain, tally, feverHits, localNoteCount, feverPercentage, feverMult,
   feverTimeSec, feverFillDenom, perEvent[], feverSections[] }` where each `feverSections`
entry is `{ activationEventIndex, activationMs, endMs, noteCount, stillActiveAtSongEnd? }` —
`noteCount` is the count of non-miss counted notes scored while that fever was active.

## Validation (hand-checked)
- 4× perfect @ base stats, `hitObjectsCount=4` → score **2056** (202 + 612 + 618 + 624); fever
  activates on event #1, `feverPercentage` 0.75.
- Fever drain: a >`feverTimeSec` gap deactivates fever before the next hit (that hit scores ×1).
