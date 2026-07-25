// reference constants
var JUDGE_EDGES_TAP = [430, 190, 40, -20, -95, -235];
var HELD_TAIL_WINDOW_MULT = 2;
var JUDGE_EDGES_TAIL = JUDGE_EDGES_TAP.map((e) => e * HELD_TAIL_WINDOW_MULT);
var SCORING = {
  /** the power-bar activation threshold (PlayerScore.lua:267 `bar < 1` gate) */
  FEVER_ACTIVATE_AT: 1,
  /** drain weights on a hit during fever: −drainPct × these (GearStats.lua:346) */
  FEVER_DRAIN_WEIGHT: { perfect: 0, great: 0, okay: 0.25, miss: 1 },
  /** accuracy weights (PlayerScore.lua:265,311) */
  ACCURACY_WEIGHT: { perfect: 1, great: 0.75, okay: 0.25, miss: 0 }
};

// reference curve helpers
function yFor2PtLine(x1, y1, x2, y2, x) {
  const slope = (y1 - y2) / (x1 - x2);
  return slope * x + (y1 - slope * x1);
}
function bezier1D(a, b, c, d, t) {
  const u = 1 - t;
  return u * u * u * a + 3 * t * u * u * b + 3 * t * t * u * c + t * t * t * d;
}
var BezierDist = class {
  constructor(x1, y1, x2, y2, x3, y3, x4, y4, segments = 10) {
    this.y1 = y1;
    this.y2 = y2;
    this.y3 = y3;
    this.y4 = y4;
    let t = 0;
    let dist = 0;
    let px = x1;
    let py = y1;
    for (let i = 1; i <= segments; i++) {
      t += 1 / segments;
      const cx = bezier1D(x1, x2, x3, x4, t);
      const cy = bezier1D(y1, y2, y3, y4, t);
      dist += Math.hypot(cx - px, cy - py);
      this.ts.push(t);
      this.dists.push(dist);
      px = cx;
      py = cy;
    }
    this.total = dist;
  }
  ts = [0];
  dists = [0];
  total;
  /** BezierDist.lua:43-58 f_T — bisect for the last entry with distance < target (1-based lua → 0-based here). */
  bracket(target) {
    let lo = 0;
    let hi = this.dists.length - 1;
    while (hi - lo > 1) {
      const mid = Math.floor(lo + (hi - lo) * 0.5);
      if (this.dists[mid] < target) lo = mid;
      else hi = mid;
    }
    return lo;
  }
  /** BezierDist.lua:60-75 get_t_for_distance. */
  tForDistance(d) {
    const v = clamp(d, 0, this.total);
    if (v === this.total) return 1;
    const i = this.bracket(v);
    const d0 = this.dists[i];
    return this.ts[i] + (this.ts[i + 1] - this.ts[i]) * ((v - d0) / (this.dists[i + 1] - d0));
  }
  /** BezierDist.lua:82 get_y_for_distance_pct — Bézier Y at the t for pct of total arc length. */
  yForDistancePct(pct) {
    return bezier1D(this.y1, this.y2, this.y3, this.y4, this.tForDistance(this.total * pct));
  }
};
function clamp(v, lo = 0, hi = 1) {
  return v < lo ? lo : v > hi ? hi : v;
}

// reference gear-stat model
var GEAR_STAT_TYPES = [
  "ColorBlue",
  "ColorGreen",
  "ColorPurple",
  "ColorRed",
  "ColorOrange",
  "NoteSpeed",
  "PerfectTime",
  "PerfectPoints",
  "GreatTime",
  "GreatPoints",
  "OkayTime",
  "OkayPoints",
  "ComboThreshold",
  "ComboMultiplier",
  "ComboBreakMultiplier",
  "FeverFillRate",
  "FeverMultiplier",
  "FeverTime",
  "FeverDrainRate"
];
function statsdictBase() {
  return Object.fromEntries(GEAR_STAT_TYPES.map((k) => [k, 0]));
}
function statsdictFrom(partial) {
  const out = statsdictBase();
  for (const [k, v] of Object.entries(partial ?? {})) {
    if (!(k in out)) throw new Error(`gearStats: unknown stat "${k}" (valid: ${GEAR_STAT_TYPES.join(", ")})`);
    if (!Number.isFinite(v)) throw new Error(`gearStats: stat "${k}" is not a finite number (${v})`);
    out[k] = v;
  }
  return out;
}
var COLOR_NAME_TO_STAT = {
  Chill: "ColorBlue",
  Blue: "ColorBlue",
  Vibe: "ColorGreen",
  Green: "ColorGreen",
  Flow: "ColorPurple",
  Purple: "ColorPurple",
  Rush: "ColorRed",
  Red: "ColorRed",
  Beat: "ColorOrange",
  Orange: "ColorOrange"
};
function colorStatForName(name) {
  return COLOR_NAME_TO_STAT[name] ?? null;
}
var EASE_NEG_40_0 = new BezierDist(0, 0, 0.4, 0.1, 1, 0.8, 1, 1);
var EASE_NEG_80_40 = new BezierDist(0, 0, 0.8, 0, 0.9, 0.8, 1, 1);
var EASE_0_40 = new BezierDist(0, 0, 0, 0.4, 0.7, 0.9, 1, 1);
var EASE_40_80 = new BezierDist(0, 0, 0.2, 0.1, 0.4, 1, 1, 1);
var EASE_80_160 = new BezierDist(0, 0, 0, 0.5, 0.6, 1, 1, 1);
function fN(aN80, aN40, a0, a40, a80, stat) {
  const s = clamp(stat, -80, 160);
  let v;
  if (s > 0) {
    if (s < 40) {
      v = lerp(a0, a40, EASE_0_40.yForDistancePct(yFor2PtLine(0, 0, 40, 1, s)));
    } else if (s > 80) {
      v = lerp(a80, a80 + (a80 - a40) * 0.35, EASE_80_160.yForDistancePct(yFor2PtLine(80, 0, 160, 1, s)));
    } else {
      v = lerp(a40, a80, EASE_40_80.yForDistancePct(yFor2PtLine(40, 0, 80, 1, s)));
    }
  } else if (s < 0) {
    if (s > -40) {
      v = lerp(aN40, a0, EASE_NEG_40_0.yForDistancePct(yFor2PtLine(-40, 0, 0, 1, s)));
    } else {
      v = lerp(aN80, aN40, EASE_NEG_80_40.yForDistancePct(yFor2PtLine(-80, 0, -40, 1, s)));
    }
  } else {
    v = a0;
  }
  return Number.isFinite(v) ? v : a0;
}
var lerp = (a, b, t) => (b - a) * t + a;
var perfectPoints = (s) => Math.floor(fN(50, 100, 200, 350, 450, s.PerfectPoints));
var greatPoints = (s) => Math.floor(fN(35, 75, 150, 225, 300, s.GreatPoints));
var okayPoints = (s) => Math.floor(fN(25, 50, 100, 150, 200, s.OkayPoints));
function comboThresholds(s) {
  const v = fN(600, 450, 100, 20, 10, s.ComboThreshold);
  return [Math.floor(v * 0.25), Math.floor(v * 0.5), v];
}
function comboMultipliers(s) {
  const v = fN(0, 0.25, 1, 1.4, 1.6, s.ComboMultiplier);
  return [1 + v * 0.25, 1 + v * 0.5, 1 + v];
}
function continuousComboMultiplier(s, combo) {
  const [t1, t2, t3] = comboThresholds(s);
  const [m1, m2, m3] = comboMultipliers(s);
  if (combo <= t1) return yFor2PtLine(0, 1, t1, m1, combo);
  if (combo <= t2) return yFor2PtLine(t1, m1, t2, m2, combo);
  if (combo <= t3) return yFor2PtLine(t2, m2, t3, m3, combo);
  return m3;
}
var feverDecayRate = (s) => fN(0, 0.05, 0.15, 0.35, 0.4, s.FeverTime);
var feverMissDrainPct = (s) => fN(0.5, 0.25, 0.1, 0.01, 0, s.FeverDrainRate);
function feverFillScales(s) {
  const v = fN(0.6, 0.5, 0.333, 0.166, 0.1, s.FeverFillRate);
  return { perfect: v, great: v * 2 };
}
var feverMultiplier = (s) => fN(1, 1.25, 3, 4.75, 5.25, s.FeverMultiplier);
var comboBreakMultiplier = (s) => fN(0, 0.1, 0.5, 0.9, 1, s.ComboBreakMultiplier);
var chainAfterBreak = (s, chain) => Math.floor(comboBreakMultiplier(s) * chain);
function colorPointBonus(s, result, colors) {
  if (colors.length === 0) return [0, 0];
  if (colors.length === 1) {
    const f = result === "perfect" ? 3 : result === "great" ? 2 : result === "okay" ? 1 : 0;
    return [Math.floor(f * s[colors[0]]), 0];
  }
  let f1 = 0;
  let f2 = 0;
  if (result === "perfect") {
    f1 = 2;
    f2 = 1;
  } else if (result === "great") {
    f1 = 1.3333333333333333;
    f2 = 0.6666666666666666;
  } else if (result === "okay") {
    f1 = 0.6666666666666666;
    f2 = 0.3333333333333333;
  }
  return [Math.floor(f1 * s[colors[0]]), Math.floor(f2 * s[colors[1]])];
}

// reference score engine
function clamp01(x) {
  return x < 0 ? 0 : x > 1 ? 1 : x;
}
var ScoreEngine = class {
  score = 0;
  /** current combo chain */
  chain = 0;
  maxChain = 0;
  /** fever meter 0..1 */
  feverBar = 0;
  feverActive = false;
  /** MANUAL power-bar mode (the LIVE game's behaviour): the bar holds at full and only ×N-activates on a
   *  KEY_POWERBAR_TRIGGER (Space) tap, vs AUTO which fires the instant it fills (the dev build:
   *  DebugConfig.PowerBarManualEnabled=false — and the meta sim's model, so replays run AUTO). */
  manualFever = true;
  tally = { perfect: 0, great: 0, okay: 0, miss: 0 };
  /** combo-breaking whiffs + early releases (n_v_0_9) — the extra rank-accuracy denominator term. */
  whiffPenalties = 0;
  /** counted REAL note events (taps/heads/tails incl. time-misses; excludes whiffs) — n_v_0_12,
   *  the Fever % denominator. */
  localNoteCount = 0;
  /** per-note records for the end-screen accuracy graph (NoteTimeGraph) */
  graphHits = [];
  /** non-miss hits landed while fever was active (n_v_0_4) — numerator of the note-based Fever %. */
  feverHits = 0;
  /** non-miss hits within the CURRENT fever (n_v_0_3): reset while inactive, 1 at activation. */
  powerbarNotes = 0;
  /** SERVER-calibrated "wasted note": the first hit after a fever window ends contributes NO
   *  fill (the meta sim's server-matching timeline — fever_timeline.py:86 "later sections:
   *  non_fever_base notes (1 'wasted' note where fever ends)"). Armed on deactivation. */
  wastedFillPending = false;
  /** Perfect-fill denominator = HitObjectsCount × fillScale (GearStats.lua:237) — a Great fills
   *  half (its scale is ×2). Cross-checked against the chart's "Fever Fill" header at base stats. */
  feverFillDenom;
  greatFillDenom;
  /** seconds for the active bar to drain 1→0 = approxLengthSec × decayRate (GearStats.lua:225,328). */
  feverTimeSec;
  /** the ×N score multiplier while fever is active (GearStats.lua:243). */
  feverMult;
  missDrainPct;
  basePoints;
  stats;
  /** song elemental colors as color-stat keys (primary[, secondary]) — chart header driven. */
  colors;
  cfg;
  constructor(cfg, stats = statsdictBase(), colors = []) {
    this.cfg = cfg;
    this.stats = stats;
    this.colors = colors;
    const fill = feverFillScales(stats);
    this.feverFillDenom = cfg.hitObjectsCount * fill.perfect;
    this.greatFillDenom = cfg.hitObjectsCount * fill.great;
    this.feverTimeSec = cfg.lastNoteTimeSec * 0.15 * (feverDecayRate(stats) / 0.15);
    this.feverMult = feverMultiplier(stats);
    this.missDrainPct = feverMissDrainPct(stats);
    this.basePoints = {
      perfect: perfectPoints(stats),
      great: greatPoints(stats),
      okay: okayPoints(stats),
      miss: 0
    };
  }
  /**
   * Register one judged input. Returns the awarded points and whether the event COUNTED
   * (an idle whiff/early-release is a complete no-op — callers gate feedback on `counted`).
   */
  registerHit(result, kind = "note") {
    if (this.feverActive) {
      this.feverBar = clamp01(this.feverBar - this.missDrainPct * SCORING.FEVER_DRAIN_WEIGHT[result]);
    } else if (this.wastedFillPending) {
      this.wastedFillPending = false;
    } else {
      this.feverBar = clamp01(this.feverBar + this.feverFill(result));
      if (!this.manualFever && this.feverBar >= SCORING.FEVER_ACTIVATE_AT) {
        this.feverActive = true;
        this.powerbarNotes = 0;
      }
    }
    this.maxChain = Math.max(this.chain, this.maxChain);
    let counted = true;
    if (result === "perfect" || result === "great") {
      this.chain += 1;
      this.tally[result] += 1;
      this.localNoteCount += 1;
    } else if (result === "okay") {
      this.tally.okay += 1;
      this.localNoteCount += 1;
    } else {
      if (this.chain > 0) {
        this.chain = chainAfterBreak(this.stats, this.chain);
      } else if (kind !== "note") {
        counted = false;
      }
      if (counted) {
        this.tally.miss += 1;
        if (kind !== "note") this.whiffPenalties += 1;
        else this.localNoteCount += 1;
      }
    }
    const [c1, c2] = colorPointBonus(this.stats, result, this.colors);
    const base = this.basePoints[result] + c1 + c2;
    const chainMult = this.comboMultiplier();
    const feverMult = this.feverActive ? this.feverMult : 1;
    const points = Math.floor(base * chainMult * feverMult);
    if (!counted) return { points, counted };
    this.score += points;
    if (result !== "miss") {
      this.powerbarNotes += 1;
      if (this.feverActive) this.feverHits += 1;
    }
    return { points, counted };
  }
  /** Fever-bar fill for one hit while charging (GearStats.lua:237 scales): a Perfect adds
   *  1/(N × scale), a Great half that, Okay/Miss nothing. No tail weighting. */
  feverFill(result) {
    if (this.feverFillDenom <= 0) return 0;
    if (result === "perfect") return 1 / this.feverFillDenom;
    if (result === "great") return 1 / this.greatFillDenom;
    return 0;
  }
  /** Per-frame (or, in replays, per-event) power-bar integration + activation gate
   *  (PlayerScore.lua:210-276 `t.update`, gate at :267):
   *  when inactive, activate iff bar≥1 AND (auto OR triggerPressed); while active the bar drains
   *  1→0 over feverTimeSec of chart time, deactivating at 0. `powerbarNotes` resets while
   *  inactive and seeds to 1 at activation (lua:266,272). */
  feverTick(dtSeconds, triggerPressed = false) {
    if (this.feverActive) {
      this.feverBar -= dtSeconds / this.feverTimeSec;
      if (this.feverBar <= 0) {
        this.feverBar = 0;
        this.feverActive = false;
        this.wastedFillPending = true;
      }
      return;
    }
    this.powerbarNotes = 0;
    if (this.feverBar >= SCORING.FEVER_ACTIVATE_AT && (!this.manualFever || triggerPressed)) {
      this.feverActive = true;
      this.powerbarNotes = 1;
    }
  }
  /** Record one judged note for the end-screen graph (NoteTimeGraph get_registered_hits). */
  recordGraphHit(result, timeMs, delta, fever) {
    this.graphHits.push({ result, timeMs, delta, fever });
  }
  /** Results "Fever %" stat — PlayerScore.lua:120-123 get_fever_percentage: non-miss hits landed
   *  while fever was active over the counted REAL note events (n_v_0_4 / n_v_0_12). */
  feverPercentage() {
    return this.localNoteCount > 0 ? this.feverHits / this.localNoteCount : 0;
  }
  /** Highest combo reached (maxChain captures BEFORE each increment, so fold in the live chain). */
  maxCombo() {
    return Math.max(this.maxChain, this.chain);
  }
  /** The CURRENT chain's score multiplier — GearStats.get_continuous_combo_multiplier_for_combo
   *  (piecewise-linear over the stats-derived thresholds, flat at the top). */
  comboMultiplier() {
    return continuousComboMultiplier(this.stats, this.chain);
  }
  /** Weighted hit sum (perfect×1 + great×0.75 + okay×0.25; miss×0). Numerator for both accuracies. */
  weightedHits() {
    const w = SCORING.ACCURACY_WEIGHT;
    return this.tally.perfect * w.perfect + this.tally.great * w.great + this.tally.okay * w.okay;
  }
  /** RUNNING average accuracy (PlayerScore.lua:318-324 get_average_accuracy): weighted hits over the
   *  notes judged SO FAR. This is the value shown in the "Avg %" text panel — NOT what drives the rank. */
  accuracy() {
    const judged = this.tally.perfect + this.tally.great + this.tally.okay + this.tally.miss;
    return judged > 0 ? this.weightedHits() / judged : 0;
  }
  /** RANK-driving accuracy (PlayerScore.lua:311-316 get_accuracy): weighted hits over the FIXED
   *  full-song note count (HitCount) + combo-breaking whiffs/early releases (n_v_0_9). The
   *  denominator is the whole chart's weighted note total, set once — so this starts near 0 and
   *  climbs toward its final value as you hit notes. RankBar.lua:103-120 feeds THIS into
   *  accuracy_to_rank_value (the rank icon + bar fill), while accuracy() feeds the % text. */
  rankAccuracy() {
    const denom = this.cfg.hitCount + this.whiffPenalties;
    return denom > 0 ? this.weightedHits() / denom : 0;
  }
  /** Freeze the mutable scoring state (for a replay seek checkpoint). Pairs with `restore`. */
  snapshot() {
    return {
      score: this.score,
      chain: this.chain,
      maxChain: this.maxChain,
      feverBar: this.feverBar,
      feverActive: this.feverActive,
      whiffPenalties: this.whiffPenalties,
      localNoteCount: this.localNoteCount,
      feverHits: this.feverHits,
      powerbarNotes: this.powerbarNotes,
      wastedFillPending: this.wastedFillPending,
      tally: { ...this.tally },
      graphLen: this.graphHits.length
    };
  }
  /** Restore a `snapshot` taken earlier in the SAME run (same config/stats). `graph` is the authoritative
   *  graph sliced to `snap.graphLen` — assigned wholesale so the engine's graphHits exactly matches the
   *  snapshot point; subsequent registerHit/recordGraphHit append from there, reproducing the run. Config
   *  and `manualFever` are untouched (immutable within a run). */
  restore(snap, graph) {
    this.score = snap.score;
    this.chain = snap.chain;
    this.maxChain = snap.maxChain;
    this.feverBar = snap.feverBar;
    this.feverActive = snap.feverActive;
    this.whiffPenalties = snap.whiffPenalties;
    this.localNoteCount = snap.localNoteCount;
    this.feverHits = snap.feverHits;
    this.powerbarNotes = snap.powerbarNotes;
    this.wastedFillPending = snap.wastedFillPending;
    this.tally = { ...snap.tally };
    this.graphHits = graph;
  }
};

// reference judgement model
function judgeWithEdges(delta, edges) {
  const okayLate = edges[0];
  const greatLate = edges[1];
  const perfectLate = edges[2];
  const perfectEarly = edges[3];
  const greatEarly = edges[4];
  const okayEarly = edges[5];
  if (delta > okayLate) return "miss";
  if (delta > greatLate) return "okay";
  if (delta > perfectLate) return "great";
  if (delta > perfectEarly) return "perfect";
  if (delta > greatEarly) return "great";
  if (delta > okayEarly) return "okay";
  return "miss";
}
function judgeTap(delta) {
  return judgeWithEdges(delta, JUDGE_EDGES_TAP);
}
function judgeTail(delta) {
  return judgeWithEdges(delta, JUDGE_EDGES_TAIL);
}
export {
  GEAR_STAT_TYPES,
  ScoreEngine,
  colorStatForName,
  continuousComboMultiplier,
  feverDecayRate,
  feverFillScales,
  feverMissDrainPct,
  feverMultiplier,
  greatPoints,
  judgeTail,
  judgeTap,
  judgeWithEdges,
  okayPoints,
  perfectPoints,
  statsdictBase,
  statsdictFrom
};
