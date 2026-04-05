#!/usr/bin/env python3
"""Self-contained prototype harness for the ECLIPSE GA->FG reduction.

This is a faithful mock-up, not a repo-integrated implementation.
It demonstrates:
1) exact FG reduction: interval-DP + monotone safe upper bound
2) GA exact-work reduction: steady-state GA + exact signature cache

Outputs JSON metrics and can optionally print human-readable tables.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np


# -----------------------------
# Synthetic song / FG prototype
# -----------------------------

@dataclass(frozen=True)
class FGSong:
    timestamps: Tuple[float, ...]
    fill_ok: Tuple[bool, ...]
    weights: Tuple[float, ...]

    @property
    def n_notes(self) -> int:
        return len(self.timestamps)


@dataclass(frozen=True)
class FGSignature:
    raw_fill: float
    duration: float
    fever_mul: float
    great_ratio: float


@dataclass
class FGResult:
    delta: float
    states_visited: int
    activation_checks: int
    elapsed_ms: float


def generate_song(seed: int, n_notes: int) -> FGSong:
    rng = random.Random(seed)
    # generate increasing timestamps with clustered rhythms
    t = []
    cur = 0.0
    for i in range(n_notes):
        cur += rng.uniform(0.18, 0.42) * (0.85 + 0.35 * math.sin(i / 23.0))
        t.append(cur)
    # long-note / fill-ineligible mask, around 10-14%
    fill_ok = [rng.random() > 0.12 for _ in range(n_notes)]
    # note weights increase with combo but with local oscillation
    weights = [
        (1.0 + 0.0035 * i)
        * (0.9 + 0.35 * rng.random())
        * (1.0 + 0.05 * math.sin(i / 11.0))
        for i in range(n_notes)
    ]
    return FGSong(tuple(t), tuple(fill_ok), tuple(weights))


def generate_fg_signature(seed: int, song: FGSong) -> FGSignature:
    rng = random.Random(seed)
    n_fill = sum(song.fill_ok)
    # reasonable range: fill count around 18-42 eligible notes
    target_fill_count = rng.randint(18, min(42, max(18, n_fill // 3)))
    frac = rng.uniform(0.05, 0.95)
    raw_fill = max(8.0, target_fill_count - frac)
    duration = rng.uniform(2.5, 5.8)
    fever_mul = rng.uniform(1.6, 2.2)
    great_ratio = rng.uniform(0.72, 0.9)
    return FGSignature(raw_fill=raw_fill, duration=duration, fever_mul=fever_mul, great_ratio=great_ratio)


class FGPrepared:
    def __init__(self, song: FGSong, sig: FGSignature):
        self.song = song
        self.sig = sig
        self.n = song.n_notes
        self.weights = np.array(song.weights, dtype=np.float64)
        self.fill_ok = np.array(song.fill_ok, dtype=np.bool_)
        self.timestamps = np.array(song.timestamps, dtype=np.float64)
        self.penalty = (1.0 - sig.great_ratio) * self.weights
        self.bonus = (sig.fever_mul - 1.0) * self.weights
        self.prefix_bonus = np.concatenate([[0.0], np.cumsum(self.bonus)])
        self.suffix_bonus = np.cumsum(self.bonus[::-1])[::-1]
        self.fever_end = self._precompute_fever_end()
        self.window_bonus = self._precompute_window_bonus()

    def _precompute_fever_end(self) -> np.ndarray:
        end = np.empty(self.n, dtype=np.int32)
        j = 0
        eps = 1e-12
        for i in range(self.n):
            if j < i:
                j = i
            limit = self.timestamps[i] + self.sig.duration + eps
            while j < self.n and self.timestamps[j] < limit:
                j += 1
            end[i] = j - 1
        return end

    def _precompute_window_bonus(self) -> np.ndarray:
        out = np.empty(self.n, dtype=np.float64)
        for i in range(self.n):
            e = int(self.fever_end[i])
            out[i] = float(self.prefix_bonus[e + 1] - self.prefix_bonus[i])
        return out

    def fill_sequence(self, start_idx: int, first_fever: bool) -> List[int]:
        elig = [i for i in range(start_idx, self.n) if self.fill_ok[i]]
        if not first_fever and elig:
            # transition note after fever ends does not contribute fill
            elig = elig[1:]
        return elig


# Minimal number of Greats required so the m-th fill-eligible note is the fever activation note.
def k_min_for_activation_rank(m: int, raw_fill: float) -> int:
    # From: (m - 1) - 0.5k < raw_fill <= m - 0.5k
    return max(0, math.floor(2.0 * (m - 1 - raw_fill) + 1e-12) + 1)


def fg_exact_naive(song: FGSong, sig: FGSignature) -> FGResult:
    prep = FGPrepared(song, sig)
    fill_floor = math.ceil(sig.raw_fill - 1e-12)
    states_counter = 0
    activation_checks = 0
    t0 = time.perf_counter()

    @lru_cache(maxsize=None)
    def solve(start_idx: int, first_fever: bool) -> float:
        nonlocal states_counter, activation_checks
        states_counter += 1
        elig = prep.fill_sequence(start_idx, first_fever)
        if len(elig) < fill_floor:
            return 0.0
        best = 0.0
        for m in range(fill_floor, len(elig) + 1):
            activation_checks += 1
            a = elig[m - 1]
            k = k_min_for_activation_rank(m, sig.raw_fill)
            if k > m - 1:
                continue
            prefix_penalties = sorted(float(prep.penalty[idx]) for idx in elig[: m - 1])
            cost = float(sum(prefix_penalties[:k]))
            next_start = int(prep.fever_end[a]) + 1
            reward = float(prep.window_bonus[a]) - cost + solve(next_start, False)
            if reward > best:
                best = reward
        return best

    delta = solve(0, True)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return FGResult(delta=float(delta), states_visited=states_counter, activation_checks=activation_checks, elapsed_ms=elapsed_ms)


def fg_exact_reduced(song: FGSong, sig: FGSignature) -> FGResult:
    import heapq

    prep = FGPrepared(song, sig)
    fill_floor = math.ceil(sig.raw_fill - 1e-12)
    states_counter = 0
    activation_checks = 0
    t0 = time.perf_counter()

    @lru_cache(maxsize=None)
    def solve(start_idx: int, first_fever: bool) -> float:
        nonlocal states_counter, activation_checks
        states_counter += 1
        elig = prep.fill_sequence(start_idx, first_fever)
        if len(elig) < fill_floor:
            return 0.0
        best = 0.0
        selected_max_heap: List[float] = []  # store negatives; selected set is current k smallest
        rest_min_heap: List[float] = []
        selected_sum = 0.0
        current_k = 0

        def grow_to(target_k: int) -> tuple[int, float]:
            nonlocal current_k, selected_sum
            while current_k < target_k and rest_min_heap:
                x = heapq.heappop(rest_min_heap)
                heapq.heappush(selected_max_heap, -x)
                selected_sum += x
                current_k += 1
            return current_k, selected_sum

        def add_prefix_value(x: float) -> None:
            nonlocal selected_sum
            if current_k == 0:
                heapq.heappush(rest_min_heap, x)
                return
            if len(selected_max_heap) < current_k:
                heapq.heappush(selected_max_heap, -x)
                selected_sum += x
                return
            largest_small = -selected_max_heap[0] if selected_max_heap else float('inf')
            if x < largest_small:
                removed = -heapq.heapreplace(selected_max_heap, -x)
                selected_sum += x - removed
                heapq.heappush(rest_min_heap, removed)
            else:
                heapq.heappush(rest_min_heap, x)

        for m in range(1, len(elig) + 1):
            a = elig[m - 1]
            if m >= fill_floor:
                activation_checks += 1
                k = k_min_for_activation_rank(m, sig.raw_fill)
                if k <= m - 1:
                    have_k, cost = grow_to(k)
                    if have_k == k:
                        ub = float(prep.suffix_bonus[a]) - cost
                        if ub <= best + 1e-12:
                            break
                        next_start = int(prep.fever_end[a]) + 1
                        reward = float(prep.window_bonus[a]) - cost + solve(next_start, False)
                        if reward > best:
                            best = reward
            add_prefix_value(float(prep.penalty[a]))
        return best

    delta = solve(0, True)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return FGResult(delta=float(delta), states_visited=states_counter, activation_checks=activation_checks, elapsed_ms=elapsed_ms)


def fg_exact_exhaustive_small(song: FGSong, sig: FGSignature) -> FGResult:
    prep = FGPrepared(song, sig)
    fill_floor = math.ceil(sig.raw_fill - 1e-12)
    states_counter = 0
    activation_checks = 0
    t0 = time.perf_counter()

    @lru_cache(maxsize=None)
    def solve(start_idx: int, first_fever: bool) -> float:
        nonlocal states_counter, activation_checks
        states_counter += 1
        elig = prep.fill_sequence(start_idx, first_fever)
        if len(elig) < fill_floor:
            return 0.0
        best = 0.0
        for m in range(fill_floor, len(elig) + 1):
            activation_checks += 1
            a = elig[m - 1]
            k = k_min_for_activation_rank(m, sig.raw_fill)
            if k > m - 1:
                continue
            prefix = elig[: m - 1]
            for subset in itertools.combinations(prefix, k):
                cost = float(sum(prep.penalty[idx] for idx in subset))
                next_start = int(prep.fever_end[a]) + 1
                reward = float(prep.window_bonus[a]) - cost + solve(next_start, False)
                if reward > best:
                    best = reward
        return best

    delta = solve(0, True)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return FGResult(delta=float(delta), states_visited=states_counter, activation_checks=activation_checks, elapsed_ms=elapsed_ms)


# ----------------------------------------
# Synthetic GA prototype for exact-work cut
# ----------------------------------------

NUM_SLOTS = 9
NUM_STATS = 10


@dataclass(frozen=True)
class Genome:
    genes: Tuple[int, ...]


@dataclass
class GAMetrics:
    baseline_exact_evals: int
    raw_cache_exact_evals: int
    signature_cache_exact_evals: int
    baseline_best: float
    raw_cache_best: float
    signature_cache_best: float
    unique_genomes: int
    unique_signatures: int


class GASimulator:
    def __init__(self, seed: int, n_items_per_slot: int = 28, n_classes_per_slot: int = 9):
        self.rng = random.Random(seed)
        self.n_items_per_slot = n_items_per_slot
        self.n_classes_per_slot = n_classes_per_slot
        # Several item ids share the same exact score-relevant stat bundle.
        self.slot_item_to_class: List[List[int]] = []
        self.slot_class_stats: List[List[Tuple[int, ...]]] = []
        for slot in range(NUM_SLOTS):
            cls_for_item = [self.rng.randrange(n_classes_per_slot) for _ in range(n_items_per_slot)]
            # bias toward collisions: re-map some ids to neighboring classes
            for i in range(0, n_items_per_slot, 5):
                cls_for_item[i] = cls_for_item[max(0, i - 1)]
            self.slot_item_to_class.append(cls_for_item)
            slot_stats: List[Tuple[int, ...]] = []
            for cls in range(n_classes_per_slot):
                vals = []
                local_rng = random.Random(seed * 1000 + slot * 97 + cls * 31)
                for s in range(NUM_STATS):
                    vals.append(local_rng.randint(-2, 5))
                slot_stats.append(tuple(vals))
            self.slot_class_stats.append(slot_stats)

    def random_genome(self) -> Genome:
        return Genome(tuple(self.rng.randrange(self.n_items_per_slot) for _ in range(NUM_SLOTS)))

    def signature(self, genome: Genome) -> Tuple[int, ...]:
        out = [0] * NUM_STATS
        for slot, item_id in enumerate(genome.genes):
            cls = self.slot_item_to_class[slot][item_id]
            vals = self.slot_class_stats[slot][cls]
            for i in range(NUM_STATS):
                out[i] += vals[i]
        return tuple(out)

    def fitness(self, signature: Tuple[int, ...], song_vec: Tuple[float, ...]) -> float:
        # Deterministic black-box stand-in for exact base scoring.
        total = 0.0
        for i, x in enumerate(signature):
            total += song_vec[i] * x
        # Mild nonlinearity to avoid trivial dominance.
        total += 0.05 * signature[0] * signature[4]
        total += 0.03 * signature[1] * signature[2]
        total -= 0.02 * max(0, -signature[7]) ** 2
        return total

    def crossover(self, a: Genome, b: Genome) -> Genome:
        return Genome(tuple(a.genes[i] if self.rng.random() < 0.5 else b.genes[i] for i in range(NUM_SLOTS)))

    def mutate(self, g: Genome, rate: float = 0.16) -> Genome:
        genes = list(g.genes)
        changed = False
        for i in range(NUM_SLOTS):
            if self.rng.random() < rate:
                genes[i] = self.rng.randrange(self.n_items_per_slot)
                changed = True
        if not changed and self.rng.random() < 0.25:
            j = self.rng.randrange(NUM_SLOTS)
            genes[j] = self.rng.randrange(self.n_items_per_slot)
        return Genome(tuple(genes))

    def tournament_select(self, scored_pop: Sequence[Tuple[Genome, float]], k: int = 3) -> Genome:
        sample = [scored_pop[self.rng.randrange(len(scored_pop))] for _ in range(k)]
        sample.sort(key=lambda x: x[1], reverse=True)
        return sample[0][0]

    def run_song(
        self,
        song_seed: int,
        pop_size: int = 160,
        restarts: int = 6,
        generations: int = 16,
        batch_size: int = 96,
    ) -> GAMetrics:
        song_rng = random.Random(song_seed)
        song_vec = tuple(song_rng.uniform(-1.3, 2.0) for _ in range(NUM_STATS))

        # Baseline: independent restarts, no cache.
        baseline_exact_evals = 0
        baseline_best = -1e18
        global_seen_raw: Dict[Tuple[int, ...], float] = {}
        global_seen_sig: Dict[Tuple[int, ...], float] = {}
        all_genomes = set()
        all_sigs = set()
        raw_cache_exact_evals = 0
        signature_cache_exact_evals = 0
        raw_cache_best = -1e18
        signature_cache_best = -1e18

        for _ in range(restarts):
            pop = [self.random_genome() for _ in range(pop_size)]
            scored_pop = []
            for g in pop:
                sig = self.signature(g)
                score = self.fitness(sig, song_vec)
                scored_pop.append((g, score))
                all_genomes.add(g.genes)
                all_sigs.add(sig)
            for _ in range(generations):
                children = []
                for _ in range(batch_size):
                    p1 = self.tournament_select(scored_pop)
                    p2 = self.tournament_select(scored_pop)
                    child = self.mutate(self.crossover(p1, p2))
                    children.append(child)

                baseline_exact_evals += len(children)
                child_scored_baseline = []
                child_scored_raw = []
                child_scored_sig = []
                for child in children:
                    sig = self.signature(child)
                    score = self.fitness(sig, song_vec)
                    child_scored_baseline.append((child, score))
                    # raw-key cache
                    if child.genes not in global_seen_raw:
                        global_seen_raw[child.genes] = score
                        raw_cache_exact_evals += 1
                    score_raw = global_seen_raw[child.genes]
                    child_scored_raw.append((child, score_raw))
                    # signature-key cache
                    if sig not in global_seen_sig:
                        global_seen_sig[sig] = score
                        signature_cache_exact_evals += 1
                    score_sig = global_seen_sig[sig]
                    child_scored_sig.append((child, score_sig))
                    all_genomes.add(child.genes)
                    all_sigs.add(sig)

                scored_pop = sorted(scored_pop + child_scored_baseline, key=lambda x: x[1], reverse=True)[:pop_size]
                baseline_best = max(baseline_best, scored_pop[0][1])
                raw_cache_best = max(raw_cache_best, max(score for _, score in child_scored_raw))
                signature_cache_best = max(signature_cache_best, max(score for _, score in child_scored_sig))

        # Proposed search: one long-lived population with signature cache.
        # Same number of child proposals as baseline.
        pop = [self.random_genome() for _ in range(pop_size)]
        proposal_steps = restarts * generations
        scored_pop = []
        sig_cache_steady: Dict[Tuple[int, ...], float] = {}
        steady_exact_evals = 0
        steady_best = -1e18
        for g in pop:
            sig = self.signature(g)
            score = self.fitness(sig, song_vec)
            scored_pop.append((g, score))
            sig_cache_steady.setdefault(sig, score)
        for _ in range(proposal_steps):
            children = []
            for _ in range(batch_size):
                p1 = self.tournament_select(scored_pop)
                p2 = self.tournament_select(scored_pop)
                children.append(self.mutate(self.crossover(p1, p2)))
            child_scored = []
            for child in children:
                sig = self.signature(child)
                if sig not in sig_cache_steady:
                    sig_cache_steady[sig] = self.fitness(sig, song_vec)
                    steady_exact_evals += 1
                score = sig_cache_steady[sig]
                child_scored.append((child, score))
            scored_pop = sorted(scored_pop + child_scored, key=lambda x: x[1], reverse=True)[:pop_size]
            steady_best = max(steady_best, scored_pop[0][1])

        return GAMetrics(
            baseline_exact_evals=baseline_exact_evals,
            raw_cache_exact_evals=raw_cache_exact_evals,
            signature_cache_exact_evals=steady_exact_evals,
            baseline_best=baseline_best,
            raw_cache_best=raw_cache_best,
            signature_cache_best=steady_best,
            unique_genomes=len(all_genomes),
            unique_signatures=len(all_sigs),
        )


# -----------------------------
# Benchmark orchestration
# -----------------------------


def ci95(samples: Sequence[float]) -> Tuple[float, float]:
    if not samples:
        return (0.0, 0.0)
    mean = statistics.mean(samples)
    if len(samples) == 1:
        return mean, 0.0
    stdev = statistics.stdev(samples)
    half = 1.96 * stdev / math.sqrt(len(samples))
    return mean, half


def run_fg_correctness(seed0: int = 9000, n_cases: int = 12) -> Dict[str, float]:
    mismatches = 0
    max_abs_err = 0.0
    exhaustive_ms = []
    naive_ms = []
    reduced_ms = []
    for j in range(n_cases):
        song = generate_song(seed0 + j, 18 + (j % 4))
        sig = generate_fg_signature(seed0 + 1000 + j, song)
        ex = fg_exact_exhaustive_small(song, sig)
        nv = fg_exact_naive(song, sig)
        rd = fg_exact_reduced(song, sig)
        exhaustive_ms.append(ex.elapsed_ms)
        naive_ms.append(nv.elapsed_ms)
        reduced_ms.append(rd.elapsed_ms)
        abs_err = max(abs(ex.delta - rd.delta), abs(ex.delta - nv.delta), abs(nv.delta - rd.delta))
        max_abs_err = max(max_abs_err, abs_err)
        if abs_err > 1e-8:
            mismatches += 1
    return {
        "n_cases": n_cases,
        "mismatches": mismatches,
        "max_abs_err": max_abs_err,
        "exhaustive_ms_mean": statistics.mean(exhaustive_ms),
        "naive_ms_mean": statistics.mean(naive_ms),
        "reduced_ms_mean": statistics.mean(reduced_ms),
    }


def run_fg_benchmark(seeds: Sequence[int], n_songs_per_seed: int = 14, n_notes: int = 260) -> Dict[str, object]:
    naive_times = []
    reduced_times = []
    states_naive = []
    states_reduced = []
    checks_naive = []
    checks_reduced = []
    per_seed = {}
    deltas_match = True
    for seed in seeds:
        seed_naive = []
        seed_reduced = []
        seed_states_naive = []
        seed_states_reduced = []
        seed_checks_naive = []
        seed_checks_reduced = []
        for j in range(n_songs_per_seed):
            song = generate_song(seed * 100 + j, n_notes + (j % 5) * 20)
            sig = generate_fg_signature(seed * 1000 + j, song)
            nv = fg_exact_naive(song, sig)
            rd = fg_exact_reduced(song, sig)
            naive_times.append(nv.elapsed_ms)
            reduced_times.append(rd.elapsed_ms)
            states_naive.append(nv.states_visited)
            states_reduced.append(rd.states_visited)
            checks_naive.append(nv.activation_checks)
            checks_reduced.append(rd.activation_checks)
            seed_naive.append(nv.elapsed_ms)
            seed_reduced.append(rd.elapsed_ms)
            seed_states_naive.append(nv.states_visited)
            seed_states_reduced.append(rd.states_visited)
            seed_checks_naive.append(nv.activation_checks)
            seed_checks_reduced.append(rd.activation_checks)
            if abs(nv.delta - rd.delta) > 1e-8:
                deltas_match = False
        per_seed[str(seed)] = {
            "naive_ms_mean": statistics.mean(seed_naive),
            "reduced_ms_mean": statistics.mean(seed_reduced),
            "speedup_mean": statistics.mean([n / r for n, r in zip(seed_naive, seed_reduced)]),
            "activation_check_cut_mean": statistics.mean([1.0 - (r / n) for n, r in zip(seed_checks_naive, seed_checks_reduced)]),
        }
    speedups = [n / r for n, r in zip(naive_times, reduced_times)]
    check_cuts = [1.0 - (r / n) for n, r in zip(checks_naive, checks_reduced)]
    out = {
        "n_total": len(naive_times),
        "deltas_match": deltas_match,
        "naive_ms": {"mean": statistics.mean(naive_times), "median": statistics.median(naive_times)},
        "reduced_ms": {"mean": statistics.mean(reduced_times), "median": statistics.median(reduced_times)},
        "speedup": {"mean": statistics.mean(speedups), "median": statistics.median(speedups)},
        "states_naive_mean": statistics.mean(states_naive),
        "states_reduced_mean": statistics.mean(states_reduced),
        "activation_checks_naive_mean": statistics.mean(checks_naive),
        "activation_checks_reduced_mean": statistics.mean(checks_reduced),
        "activation_check_cut_mean": statistics.mean(check_cuts),
        "per_seed": per_seed,
    }
    return out


def run_ga_benchmark(seeds: Sequence[int], n_songs_per_seed: int = 30) -> Dict[str, object]:
    baseline_evals = []
    raw_evals = []
    sig_evals = []
    baseline_best = []
    sig_best = []
    unique_genomes = []
    unique_sigs = []
    per_seed = {}
    for seed in seeds:
        sim = GASimulator(seed)
        seed_baseline_evals = []
        seed_raw_evals = []
        seed_sig_evals = []
        seed_baseline_best = []
        seed_sig_best = []
        for j in range(n_songs_per_seed):
            m = sim.run_song(song_seed=seed * 100 + j)
            baseline_evals.append(m.baseline_exact_evals)
            raw_evals.append(m.raw_cache_exact_evals)
            sig_evals.append(m.signature_cache_exact_evals)
            baseline_best.append(m.baseline_best)
            sig_best.append(m.signature_cache_best)
            unique_genomes.append(m.unique_genomes)
            unique_sigs.append(m.unique_signatures)
            seed_baseline_evals.append(m.baseline_exact_evals)
            seed_raw_evals.append(m.raw_cache_exact_evals)
            seed_sig_evals.append(m.signature_cache_exact_evals)
            seed_baseline_best.append(m.baseline_best)
            seed_sig_best.append(m.signature_cache_best)
        per_seed[str(seed)] = {
            "baseline_exact_evals_mean": statistics.mean(seed_baseline_evals),
            "raw_cache_exact_evals_mean": statistics.mean(seed_raw_evals),
            "signature_cache_exact_evals_mean": statistics.mean(seed_sig_evals),
            "raw_eval_cut_mean": statistics.mean([1.0 - r / b for b, r in zip(seed_baseline_evals, seed_raw_evals)]),
            "signature_eval_cut_mean": statistics.mean([1.0 - s / b for b, s in zip(seed_baseline_evals, seed_sig_evals)]),
            "best_score_delta_mean": statistics.mean([s - b for s, b in zip(seed_sig_best, seed_baseline_best)]),
        }
    raw_cut = [1.0 - r / b for b, r in zip(baseline_evals, raw_evals)]
    sig_cut = [1.0 - s / b for b, s in zip(baseline_evals, sig_evals)]
    best_delta = [s - b for s, b in zip(sig_best, baseline_best)]
    return {
        "n_total": len(baseline_evals),
        "baseline_exact_evals_mean": statistics.mean(baseline_evals),
        "raw_cache_exact_evals_mean": statistics.mean(raw_evals),
        "signature_cache_exact_evals_mean": statistics.mean(sig_evals),
        "raw_eval_cut_mean": statistics.mean(raw_cut),
        "signature_eval_cut_mean": statistics.mean(sig_cut),
        "best_score_delta_mean": statistics.mean(best_delta),
        "best_score_delta_median": statistics.median(best_delta),
        "unique_genomes_mean": statistics.mean(unique_genomes),
        "unique_signatures_mean": statistics.mean(unique_sigs),
        "per_seed": per_seed,
    }


def projected_throughput(ga_cut: float, fg_solve_cut: float, host_cut: float) -> Dict[str, float]:
    # Prompt baseline shares, normalized to sum to 1 because the published percentages are rounded.
    raw_shares = {
        "prep": 0.087,
        "ga_gpu": 0.478,
        "decode": 0.113,
        "fg_prep": 0.100,
        "fg_run": 0.223,
    }
    total = sum(raw_shares.values())
    shares = {k: v / total for k, v in raw_shares.items()}
    new_time = (
        shares["prep"]
        + shares["ga_gpu"] * (1.0 - ga_cut)
        + shares["decode"] * (1.0 - host_cut)
        + shares["fg_prep"] * (1.0 - host_cut)
        + shares["fg_run"] * (1.0 - fg_solve_cut)
    )
    speedup = 1.0 / new_time
    baseline_sph = 5669.5
    return {
        "normalized_time": new_time,
        "speedup": speedup,
        "songs_per_hour": baseline_sph * speedup,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_json", type=Path, default=Path("/mnt/data/eclipse_assignment/prototype_results.json"))
    parser.add_argument("--fg_notes", type=int, default=260)
    parser.add_argument("--fg_songs_per_seed", type=int, default=14)
    parser.add_argument("--ga_songs_per_seed", type=int, default=30)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 17, 23])
    args = parser.parse_args()

    correctness = run_fg_correctness()
    fg = run_fg_benchmark(args.seeds, n_songs_per_seed=args.fg_songs_per_seed, n_notes=args.fg_notes)
    ga = run_ga_benchmark(args.seeds, n_songs_per_seed=args.ga_songs_per_seed)

    per_seed_projection = {}
    seed_speedups = []
    seed_sph = []
    for seed in args.seeds:
        seed_key = str(seed)
        ga_cut = float(ga["per_seed"][seed_key]["signature_eval_cut_mean"])
        fg_check_cut = float(fg["per_seed"][seed_key]["activation_check_cut_mean"])
        fg_kernel_speedup = float(fg["per_seed"][seed_key]["speedup_mean"])
        fg_solve_cut = 1.0 - (1.0 - fg_check_cut) / fg_kernel_speedup
        host_cut = 0.45
        proj = projected_throughput(ga_cut=ga_cut, fg_solve_cut=fg_solve_cut, host_cut=host_cut)
        per_seed_projection[seed_key] = {
            "ga_cut": ga_cut,
            "fg_solve_cut": fg_solve_cut,
            "host_cut": host_cut,
            **proj,
        }
        seed_speedups.append(proj["speedup"])
        seed_sph.append(proj["songs_per_hour"])

    speedup_mean, speedup_ci = ci95(seed_speedups)
    sph_mean, sph_ci = ci95(seed_sph)
    out = {
        "correctness": correctness,
        "fg": fg,
        "ga": ga,
        "projection": {
            "per_seed": per_seed_projection,
            "speedup_mean": speedup_mean,
            "speedup_ci95": speedup_ci,
            "songs_per_hour_mean": sph_mean,
            "songs_per_hour_ci95": sph_ci,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
