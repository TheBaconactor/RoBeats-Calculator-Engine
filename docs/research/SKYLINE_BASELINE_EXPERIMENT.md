# Skyline Baseline Experiment — do not drift

Date: 2026-05-08
Branch: research-3 (based on main @ 16fdafc3)
Song: Data/Hard/00 (Hard) by garlagan.txt
Hardware: Ryzen 8840HS, Radeon RX 7900 XTX, Taichi ti.vulkan

## Results (full gear + mini search, no fixes)
  GA (depth 75, seed 42):   33,061,828  (  4.00s)
  Skyline (exact DP+Pareto):33,061,828  (113.47s)
  Delta: 0  (skyline IS authoritative)

## Stage breakdown
  gear DP:                   ~0.1s
  gear global skyline:       ~0.7s
  gear local envelope prune: ~0.0s (1,443/1,556 kept)
  theorem5 response prune:   skipped (gear_cap, 1,443 > 768)
  combined skyline pairs:    ~111s  ← DOMINANT BOTTLENECK (CPU)
  combined envelope prune:   ~0.06s (65,073/66,095 kept)
  final pair eval (GPU):     ~0.8s  (65,073 pairs)

## GPU migration target
  Combined skyline pairs stage: outer-sum + grid scatter + 4D suffix-max
  Est. speedup from Taichi migration: 10-50x
  Projected skyline total after GPU migration: ~2-12s (vs GA's 4s)

## Gear/Mini pools
  Gear items: 267, Mini items: 88
  Gear skyline points: 1,443, Mini skyline points: 57
  DP 4D states: 3,819 frontier pairs

## Key files
  gear_optimizer/solver/exact_skyline.py (1574 lines)
  gear_optimizer/solver/mini_skyline.py (184 lines)
  gear_optimizer/solver/marginal_pruning.py (265 lines)
  tools/experiments/skyline_single_song.py (harness)
