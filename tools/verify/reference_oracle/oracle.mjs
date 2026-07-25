/**
 * oracle.mjs — headless reference ScoreEngine replay oracle.
 *
 * WHAT: replays a fully-resolved input stream (one entry per judged event: its physical hit
 * time in ms and its judgement) through the reference ScoreEngine exactly as the replay loop does,
 * and returns
 * the score + per-event fever membership + fever-section spans. This is the trouble-checking
 * oracle for the optimizer: give it the loadout's effective stats and the reconstructed per-note
 * (hit-time, judgement) trace, and it tells you what the reference engine scores — and which fever
 * windows really activate and how many notes each captures.
 *
 * SCORING-ORDER SCOPE (not "game-faithful" for arbitrary streams — read before extending):
 *   This mirrors the reference replay order: advanceFeverTo(eventMs) [decay + AUTO gate] THEN
 *   registerHit [fill/score]. The independently verified live/server path applies the hit result to the power
 *   bar FIRST, then advances the per-frame power-bar decay (GameLocal update -> ScoreManager:update),
 *   i.e. a different intra-event order. For the OPTIMIZER's surfaces this is exactly equivalent and
 *   authoritative: the optimizer only ever emits Perfect/Great with FULL COMBO (no Okay/Miss/whiff/
 *   early-release), and a Perfect/Great while fever is active adds NO fill and NO drain, so the only
 *   order-sensitive quantity (was fever active at the hit) is decided by the decay up to the hit
 *   either way. The order WOULD matter for miss/whiff/early-release drain and wasted-fill; this
 *   oracle is NOT a general live/server scorer for such streams -- reconcile the order first if you
 *   add them.
 *
 * WHY a stream and not the chart+consumption engine: the optimizer already knows each note's
 * judgement and hit offset for a specific decoded loadout. Resolving input→note consumption is
 * the NoteSystem's job in the live client, but for a fixed decoded loadout the mapping is 1:1
 * (each judged event has a known result at a known hit-ms). Feeding the resolved stream through
 * the SAME registerHit/feverTick path the replay uses reproduces the engine's score bit-for-bit
 * without pulling in Babylon/NoteSystem. j:"miss" events with kind:"note" are real note timeouts;
 * "whiff"/"earlyRelease" ride the idle-no-op gate.
 *
 * REPLAY FIDELITY (game.ts):
 *   - events are processed in ascending eventMs (physical act time), i tiebreak — the plan sort
 *     from replayDriver.ts:143 (the causality fix). Callers pass events already carrying eventMs.
 *   - before each event: advanceFeverTo(eventMs)  -> feverTick(dt) drains the active bar and runs
 *     the AUTO activation gate at input granularity (game.ts:1066, advanceFeverTo:1254).
 *   - registerHit(result, kind) applies bar fill / drain, chain, points (game.ts:1067 applyPress).
 *   - AFTER all events at/through a frame boundary, advanceFeverTo(frameMs) once more (game.ts:1070).
 *     We advance to the last event's eventMs at the end (there are no further inputs). Fever that
 *     would deactivate strictly AFTER the last input cannot change any score, so a final tick to
 *     lastNoteTimeSec is score-neutral; we still expose the fever-deactivation clock for spans.
 *   - manualFever=false (AUTO) — replays score with the engine's own gate (replayDriver.ts:7-9).
 *
 * INPUT (JSON on argv[2] path, or stdin):
 *   {
 *     "config":  { "hitCount": N, "hitObjectsCount": M, "lastNoteTimeSec": S },
 *     "statsdict": { "<GearStatType>": <rawStatPoints>, ... },   // WebPort stat keys, RAW points
 *     "colors":  ["ColorBlue", ...],                              // 0..2 color stat keys
 *     "events":  [ { "eventMs": <ms>, "result": "perfect|great|okay|miss", "kind": "note|whiff|earlyRelease" }, ... ]
 *   }
 *   Events need NOT be pre-sorted; the oracle sorts by (eventMs, input order) like the plan builder.
 *
 * OUTPUT (JSON on stdout):
 *   { "score", "chain", "maxChain", "tally", "feverHits", "localNoteCount", "feverPercentage",
 *     "feverMult", "feverTimeSec", "feverFillDenom",
 *     "perEvent": [ { "i","eventMs","result","kind","counted","points","feverActive","feverBar" } ],
 *     "feverSections": [ { "activationEventIndex","activationMs","endMs","noteCount" } ] }
 */
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
// Windows: dynamic import of an absolute path needs a file:// URL.
const { ScoreEngine, statsdictFrom } = await import(pathToFileURL(join(HERE, "score_bundle.mjs")).href);

function readInput() {
  const p = process.argv[2];
  const raw = p && p !== "-" ? readFileSync(p, "utf-8") : readFileSync(0, "utf-8");
  return JSON.parse(raw);
}

function run(input) {
  const { config, statsdict, colors = [], events } = input;
  if (!config || !Array.isArray(events)) throw new Error("oracle: input needs {config, events}");
  const stats = statsdictFrom(statsdict ?? {});
  const engine = new ScoreEngine(config, stats, colors);
  engine.manualFever = false; // AUTO, matching replay/meta-sim (replayDriver.ts:7-9)

  // Plan-builder sort: ascending physical act time, stable input-order tiebreak (replayDriver.ts:143).
  const plan = events.map((e, idx) => ({ ...e, __idx: idx }));
  plan.sort((a, b) => a.eventMs - b.eventMs || a.__idx - b.__idx);

  // feverClockMs starts at the first event's time — matches game.ts:424 (replay fever integration
  // starts at the first chart time; nothing drains before the first input).
  let feverClockMs = plan.length ? plan[0].eventMs : 0;
  // True fever-close clock when the bar drains to 0 strictly INSIDE the interval just advanced.
  // `feverTick` clamps the bar to 0 and flips `feverActive` but does NOT report WHEN it crossed, so
  // a section closed at `feverClockMs` (the jump target = next event / song end) reads too late. The
  // bar drains linearly at 1/feverTimeSec per second, so the real crossing is
  // `feverClockMs + feverBar*feverTimeSec*1000` (<= target). `null` when no mid-interval close.
  let lastDeactivateMs = null;
  const advanceFeverTo = (ms) => {
    lastDeactivateMs = null;
    const dtSec = (ms - feverClockMs) / 1000;
    if (dtSec > 0) {
      if (engine.feverActive) {
        const deactivateMs = feverClockMs + engine.feverBar * engine.feverTimeSec * 1000;
        if (deactivateMs <= ms) lastDeactivateMs = deactivateMs; // bar hits 0 before the target
      }
      engine.feverTick(dtSec, false); // AUTO gate; no manual trigger in replays
      feverClockMs = ms;
    }
  };

  const perEvent = [];
  const feverSections = [];
  let curSection = null;
  let wasFever = false;

  for (const ev of plan) {
    advanceFeverTo(ev.eventMs); // drain + AUTO activation gate at input granularity (game.ts:1066)
    // A fever section that just activated on the tick BEFORE this hit opens a span here; a hit whose
    // own fill completes the bar (AUTO in registerHit, scoreEngine.ts:182) opens it at the hit.
    if (engine.feverActive && !wasFever) {
      curSection = { activationEventIndex: ev.__idx, activationMs: ev.eventMs, endMs: null, noteCount: 0 };
    }
    const kind = ev.kind ?? "note";
    const { points, counted } = engine.registerHit(ev.result, kind);
    // Re-check activation: the hit itself may have flipped fever (AUTO fill-completes-bar case).
    if (engine.feverActive && !wasFever && !curSection) {
      curSection = { activationEventIndex: ev.__idx, activationMs: ev.eventMs, endMs: null, noteCount: 0 };
    }
    if (engine.feverActive && curSection) {
      if (ev.result !== "miss" && counted) curSection.noteCount += 1;
    }
    if (!engine.feverActive && wasFever && curSection) {
      // The drain that closed this section happened in the advanceFeverTo(ev.eventMs) above; use its
      // true crossing clock, not feverClockMs (== ev.eventMs, too late).
      curSection.endMs = lastDeactivateMs ?? feverClockMs;
      feverSections.push(curSection);
      curSection = null;
    }
    wasFever = engine.feverActive;
    perEvent.push({
      i: ev.__idx,
      eventMs: ev.eventMs,
      result: ev.result,
      kind,
      counted,
      points,
      feverActive: engine.feverActive,
      feverBar: engine.feverBar,
    });
  }
  // Drain to song end so a fever still active at the last input gets its true deactivation clock.
  const endMs = (config.lastNoteTimeSec ?? 0) * 1000;
  if (curSection) {
    const before = engine.feverActive;
    advanceFeverTo(Math.max(endMs, feverClockMs));
    // Fever still active at song end -> it closes at song end (feverClockMs); otherwise use the true
    // mid-interval crossing captured by advanceFeverTo, not feverClockMs (== song end, too late).
    curSection.endMs = engine.feverActive ? feverClockMs : (lastDeactivateMs ?? feverClockMs);
    curSection.stillActiveAtSongEnd = before && engine.feverActive;
    feverSections.push(curSection);
  }

  return {
    score: engine.score,
    chain: engine.chain,
    maxChain: engine.maxCombo(),
    tally: engine.tally,
    feverHits: engine.feverHits,
    localNoteCount: engine.localNoteCount,
    feverPercentage: engine.feverPercentage(),
    feverMult: engine.feverMult,
    feverTimeSec: engine.feverTimeSec,
    feverFillDenom: engine.feverFillDenom,
    perEvent,
    feverSections,
  };
}

const out = run(readInput());
process.stdout.write(JSON.stringify(out) + "\n");
