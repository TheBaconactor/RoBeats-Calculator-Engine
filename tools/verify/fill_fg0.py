"""Fill FG only for TRUE crash artifacts: songs that had best_fg_score>0 in the pre-wipe
backup but are now fg=0 (FG lost to the crash). Songs that were fg=0 in the backup too are
consistent and left alone. Scores ONE song at a time (the multi-song in-flight pipeline drops
FG for these; 1-song runs persist it). Matcher = chart-header title (substring) + difficulty,
the form the queue filter actually matches (app.py:612-623). Verifies + logs any miss."""
import os, re, sys, sqlite3, subprocess

DB = "evolution.db"
BAK = "evolution.db.backup-prewipe-20260615"


def artifacts():
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    c.execute("ATTACH '%s' AS bak" % BAK)
    rows = [r[0] for r in c.execute(
        "SELECT n.name FROM songs n JOIN bak.songs b ON n.name=b.name "
        "WHERE n.best_score>0 AND n.best_fg_score=0 AND b.best_fg_score>0 "
        "ORDER BY b.best_fg_score DESC").fetchall()]
    c.close()
    return rows


def fg(name):
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    r = c.execute("SELECT best_fg_score FROM songs WHERE name=?", (name,)).fetchone()
    c.close()
    return int(r[0]) if r and r[0] else 0


def parse(dbn):
    diff = "Easy" if "(Easy)" in dbn else "Hard" if "(Hard)" in dbn else "Normal"
    title = re.sub(r"\s*\((?:Easy|Normal|Hard)\)\s*$", "", dbn.split(" by ")[0])
    return title, diff


arts = artifacts()
print("TRUE artifacts to fill: %d" % len(arts), flush=True)
filled, failed = 0, []
for i, name in enumerate(arts, 1):
    if fg(name) > 0:
        filled += 1
        print("[%d/%d] already filled: %s" % (i, len(arts), name[:42]), flush=True)
        continue
    title, diff = parse(name)
    open("config.fill_one.ini", "w", encoding="utf-8").write(
        "[CalculateSong]\nSong_Name = %s\nDifficulty = %s\nTargetPrimary = All\n"
        "TargetSecondary = All\nLoopForever = false\n\n[IterationEngine]\nSongRepeats = 1\n"
        "SongQueueLimit = 1\n" % (title, diff))
    env = dict(os.environ)
    env["METAFINDER_CONFIG_PATH"] = "config.fill_one.ini"
    env.pop("EVOLUTION_DB_PATH", None)
    try:
        subprocess.run([sys.executable, "main.py"], env=env,
                       stdout=open("bin/fill_one_last.log", "w"), stderr=subprocess.STDOUT, timeout=300)
    except subprocess.TimeoutExpired:
        failed.append((name, "timeout"))
        print("[%d/%d] TIMEOUT %s" % (i, len(arts), name[:42]), flush=True)
        continue
    v = fg(name)
    if v > 0:
        filled += 1
        print("[%d/%d] OK fg=%d  %s" % (i, len(arts), v, name[:40]), flush=True)
    else:
        failed.append((name, "still0 title=%r diff=%s" % (title, diff)))
        print("[%d/%d] STILL 0 (title=%r diff=%s)  %s" % (i, len(arts), title, diff, name[:36]), flush=True)
print("=== ARTIFACT FILL DONE: filled=%d failed=%d ===" % (filled, len(failed)), flush=True)
for n, r in failed:
    print("  FAILED: %s  [%s]" % (n, r), flush=True)
