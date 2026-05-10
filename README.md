# RoBeats MetaFinder

Exact skyline is the production optimizer.

## Production config

```ini
[CalculateSong]
; PRODUCTION: song target selection inputs (Song_Name, Difficulty, TargetPrimary, TargetSecondary).
Song_Name =
Difficulty =
TargetPrimary = All
TargetSecondary = All

LoopForever = true
```

## Run

```powershell
python main.py
```

The historical GA, queued GPU, configurable rank sizing, manual gear/mini/gem input, and external ForceGreats pipeline surfaces have been removed from this branch.
