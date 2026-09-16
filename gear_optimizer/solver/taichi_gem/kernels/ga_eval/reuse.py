"""Exact GA reuse on the device; collisions evict entries, never alias results."""

import taichi as ti

from .. import kernels_helpers as fields


@ti.func
def _cache_slot(g: ti.i32) -> ti.i32:
    h = ti.u32(2166136261)
    for i in ti.static(range(7)):
        value = ti.cast(fields.genome_base_stats[g][i], ti.i32)
        h = (h ^ ti.cast(value + 32769, ti.u32)) * ti.u32(16777619)
    return ti.cast(h % ti.u32(fields.ga_eval_cache_key.shape[0]), ti.i32)


@ti.kernel
def ga_compute_exact_eval_rep_kernel(n_genomes: ti.i32):
    # Separate top-level loops provide a device barrier before owner selection.
    for slot in range(fields.ga_eval_cache_owner.shape[0]):
        fields.ga_eval_cache_owner[slot] = n_genomes
    for g in range(n_genomes):
        fields.ga_eval_incumbent_score[g] = 0
        stats = fields.genome_base_stats[g]
        slot = _cache_slot(g)
        hit = fields.ga_eval_cache_key[slot] != ti.u64(0)
        for i in ti.static(range(7)):
            if stats[i] != fields.ga_eval_cache_stats[slot][i]:
                hit = False
        rep = g
        if hit:
            fields.chunk_best_key[g] = fields.ga_eval_cache_key[slot]
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = fields.ga_eval_cache_results[slot][i]
        else:
            fields.chunk_best_key[g] = ti.u64(0)
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = 0
            # Deduplicate misses within this generation, preserving the earliest row.
            for j in range(g):
                same = True
                for i in ti.static(range(7)):
                    if stats[i] != fields.genome_base_stats[j][i]:
                        same = False
                if same:
                    rep = j
                    break
            if rep == g:
                ti.atomic_min(fields.ga_eval_cache_owner[slot], g)
        fields.ga_exact_eval_rep_idx[g] = rep


@ti.kernel
def ga_build_unique_slot_table_kernel(n_genomes: ti.i32):
    # Only uncached representatives need exact search. Zero pending rows is valid.
    ti.loop_config(serialize=True)
    count = 0
    for g in range(n_genomes):
        if fields.ga_exact_eval_rep_idx[g] == g and fields.chunk_best_key[g] == ti.u64(0):
            fields.ga_unique_slot_to_genome[count] = g
            count += 1
    fields.ga_exact_eval_unique_count[0] = count


@ti.kernel
def ga_scatter_dup_results_kernel(n_genomes: ti.i32):
    for g in range(n_genomes):
        rep = fields.ga_exact_eval_rep_idx[g]
        if rep != g:
            fields.chunk_best_key[g] = fields.chunk_best_key[rep]
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = fields.chunk_best_results[rep, i]
    # One deterministic writer per slot; lookup completed before this dispatch.
    for slot in range(fields.ga_eval_cache_owner.shape[0]):
        g = fields.ga_eval_cache_owner[slot]
        if g < n_genomes:
            for i in ti.static(range(7)):
                fields.ga_eval_cache_stats[slot][i] = ti.cast(fields.genome_base_stats[g][i], ti.i32)
            fields.ga_eval_cache_key[slot] = fields.chunk_best_key[g]
            for i in ti.static(range(4)):
                fields.ga_eval_cache_results[slot][i] = fields.chunk_best_results[g, i]
