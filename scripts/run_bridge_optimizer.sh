#!/usr/bin/env bash
#
# Dedicated optimizer instance for the RoBeatsMeta custom-chart bridge.
#
# It runs the SAME canonical default pipeline as the catalog optimizer, but against an ISOLATED
# state dir + song source + output DB so user uploads never touch the official bin/ caches, the
# Data/ catalog, or evolution.db. Charts the website drops in <bridge data>/Hard/ are processed
# normally (multi-song queue) and loadouts land in the separate results DB the website reads.
#
# Required env (point these at the site optimizer bridge settings):
#   ROBEATSMETA_OPTIMIZER_DATA_DIR   bridge song dir (must contain Hard/ where charts are written)
#   EVOLUTION_DB_PATH                separate results DB (NEVER the catalog evolution.db)
# Optional:
#   ROBEATSMETA_OPTIMIZER_BIN_DIR    isolated state dir (default: <data dir>/.optimizer_bin)
#   METAFINDER_CONFIG_PATH           config override (default: repo config.ini)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

: "${ROBEATSMETA_OPTIMIZER_DATA_DIR:?set ROBEATSMETA_OPTIMIZER_DATA_DIR to the bridge song dir (contains Hard/)}"
: "${EVOLUTION_DB_PATH:?set EVOLUTION_DB_PATH to the separate custom results DB (never evolution.db)}"

export ROBEATSMETA_OPTIMIZER_BIN_DIR="${ROBEATSMETA_OPTIMIZER_BIN_DIR:-$ROBEATSMETA_OPTIMIZER_DATA_DIR/.optimizer_bin}"

# Isolated state + the difficulty buckets the discovery walks.
mkdir -p "$ROBEATSMETA_OPTIMIZER_BIN_DIR" \
         "$ROBEATSMETA_OPTIMIZER_DATA_DIR/Easy" \
         "$ROBEATSMETA_OPTIMIZER_DATA_DIR/Normal" \
         "$ROBEATSMETA_OPTIMIZER_DATA_DIR/Hard"

# Gear data must be real files in the bridge dir (discovery does not follow symlinks). Refresh
# from the catalog on start so the bridge optimizes against current gear/minis/stats.
if [ -d "$REPO_ROOT/Data/Gear" ]; then
  rm -rf "$ROBEATSMETA_OPTIMIZER_DATA_DIR/Gear"
  cp -R "$REPO_ROOT/Data/Gear" "$ROBEATSMETA_OPTIMIZER_DATA_DIR/Gear"
fi

echo "[bridge-optimizer] data=$ROBEATSMETA_OPTIMIZER_DATA_DIR bin=$ROBEATSMETA_OPTIMIZER_BIN_DIR db=$EVOLUTION_DB_PATH"
exec python3 "$REPO_ROOT/main.py" run
