/**
 * build_bundle.mjs — bundle the reference ScoreEngine into a single Node-runnable ESM file.
 *
 * The reference ScoreEngine is the game-faithful scoring/combo/fever model. scoreEngine.ts imports
 * only ../constants.ts + ../types.ts +
 * ./gearStats.ts + ../judge/judge.ts — all Babylon-free — so esbuild can bundle it with no
 * browser deps. We do NOT use the user's working tree: the caller points --src at a scratch
 * worktree/archive of origin/main.
 *
 * Usage:
 *   node build_bundle.mjs --src <path-to-reference-client/src> --esbuild <path-to-esbuild-bin>
 *                         [--out <bundle.mjs>]
 *
 * esbuild binary is taken from the user's installed web/node_modules (tsx is NOT installed;
 * esbuild + tsc + vite are). On Windows pass the NATIVE binary, not the .bin shim:
 *   web/node_modules/@esbuild/win32-x64/esbuild.exe
 * (the node_modules/esbuild/bin/esbuild shim is a JS launcher Windows can't spawnSync directly).
 * Default --out is ./score_bundle.mjs next to this file.
 */
import { execFileSync } from "node:child_process";
import { writeFileSync, mkdtempSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  if (i >= 0 && i + 1 < process.argv.length) return process.argv[i + 1];
  return def;
}

const src = arg("src");
const esbuild = arg("esbuild");
const out = resolve(arg("out", join(import.meta.dirname ?? ".", "score_bundle.mjs")));
if (!src || !esbuild) {
  console.error("usage: node build_bundle.mjs --src <reference-client/src> --esbuild <esbuild-bin> [--out <file>]");
  process.exit(2);
}
const scorePath = join(src, "score", "scoreEngine.ts");
if (!existsSync(scorePath)) {
  console.error(`ERROR: scoreEngine.ts not found under ${src} (expected ${scorePath}) — wrong --src?`);
  process.exit(2);
}

// A tiny entry re-exporting exactly the public surface the oracle needs.
const entryDir = mkdtempSync(join(tmpdir(), "score-oracle-"));
const entry = join(entryDir, "_oracle_entry.ts");
writeFileSync(
  entry,
  [
    `export { ScoreEngine } from ${JSON.stringify(join(src, "score", "scoreEngine.ts"))};`,
    `export { statsdictFrom, statsdictBase, colorStatForName, GEAR_STAT_TYPES,`,
    `  perfectPoints, greatPoints, okayPoints, feverMultiplier, feverFillScales,`,
    `  feverDecayRate, feverMissDrainPct, continuousComboMultiplier } from ${JSON.stringify(join(src, "score", "gearStats.ts"))};`,
    `export { judgeTap, judgeTail, judgeWithEdges } from ${JSON.stringify(join(src, "judge", "judge.ts"))};`,
  ].join("\n"),
  "utf-8",
);

execFileSync(esbuild, [entry, "--bundle", "--format=esm", "--platform=node", `--outfile=${out}`], {
  stdio: "inherit",
});
console.error(`[build_bundle] wrote ${out}`);
