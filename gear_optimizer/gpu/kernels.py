"""The GA's Taichi kernels. A batch's runs lie contiguously in the population: genome g of run r at r * n_genomes + g."""

from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER
from gear_optimizer.solver.genetic_pipeline import (
    GA_DIVERSE_PARENT_B_RATE,
    GA_INIT_HEURISTIC_K,
    GA_MUTATION_RATE,
    GA_NOVELTY_REPAIR_ATTEMPTS,
    GA_TOURNAMENT_K,
)

from . import fields
from .fields import GA_FG_CANDIDATES_PER_RUN, GA_FTFF_LANES, GA_RESULT_COLS, ITEM_STAT_DIM, MAX_SLOTS
from .runtime import ti
from .scoring import GpuColorFlags, combo_upper_bound, exact_gem_search

_RATE_ONE = 4294967295.0
_MUTATION_RATE_FP = int(GA_MUTATION_RATE * _RATE_ONE)
_DIVERSE_PARENT_B_RATE_FP = int(GA_DIVERSE_PARENT_B_RATE * _RATE_ONE)


@ti.func
def _xorshift32(x: ti.u32) -> ti.u32:
    """Deterministic per-thread RNG: fast, and good enough for the GA's operators."""
    x ^= x << ti.u32(13)
    x ^= x >> ti.u32(17)
    x ^= x << ti.u32(5)
    return x


@ti.func
def _seeded_state(state: ti.u32) -> ti.u32:
    if state == ti.u32(0):
        state = ti.u32(1)
    return state


@ti.func
def _repair_mini_uniqueness(m0: ti.i32, m1: ti.i32, m2: ti.i32, state: ti.u32):
    """Three minis re-drawn apart (a pool of one is left alone), sorted."""
    pool_start = fields.slot_start[6]
    pool_count = fields.slot_count[6]
    if pool_count > 1:
        for _ in range(10):
            if m1 == m0:
                state = _xorshift32(state)
                m1 = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
        for _ in range(10):
            if m2 == m0 or m2 == m1:
                state = _xorshift32(state)
                m2 = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
    if m0 > m1:
        m0, m1 = m1, m0
    if m1 > m2:
        m1, m2 = m2, m1
    if m0 > m1:
        m0, m1 = m1, m0
    return m0, m1, m2, state


@ti.kernel
def upload_items_kernel(
    items: ti.types.ndarray(dtype=ti.i32, ndim=2),
    n_items: ti.i32,
    starts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """The first n_items rows of the item table and the slot pools, without a padded MAX_ITEMS transfer."""
    for i, j in ti.ndrange(n_items, ti.static(ITEM_STAT_DIM)):
        fields.item_stats[i, j] = items[i, j]
    for s in ti.static(range(MAX_SLOTS)):
        fields.slot_start[s] = starts[s]
        fields.slot_count[s] = counts[s]


@ti.kernel
def upload_surfaces_kernel(
    n: ti.i32,
    body_fever: ti.types.ndarray(dtype=ti.i32, ndim=1),
    body_normal: ti.types.ndarray(dtype=ti.i32, ndim=1),
    masks: ti.types.ndarray(dtype=ti.u32, ndim=2),
    head_coeffs: ti.types.ndarray(dtype=ti.i16, ndim=2),
):
    """The song's first n frontier surfaces, without a padded transfer of the pool."""
    for i in range(n):
        fields.grid_frontier_body_fever_pool[i] = body_fever[i]
        fields.grid_frontier_body_normal_pool[i] = body_normal[i]
        for word in ti.static(range(4)):
            fields.grid_frontier_masks_bits_pool[i, word] = masks[i, word]
            fields.grid_frontier_head_coeffs_pool[i, word] = head_coeffs[i, word]


@ti.kernel
def start_batch_kernel(run_start: ti.i32, n_runs: ti.i32, n_genomes: ti.i32, seed: ti.u32, heuristic_copies: ti.i32):
    """A batch's initial populations and RNG states, by run id and genome: the same for any batch width. A run's first
    heuristic_copies genomes draw from the top items of each slot."""
    for r, g in ti.ndrange(n_runs, n_genomes):
        run_id = run_start + r
        genome = r * n_genomes + g
        fields.ga_rng_state[genome] = _seeded_state(
            (seed + ti.cast(run_id, ti.u32)) ^ (ti.cast(g, ti.u32) * ti.u32(747796405)) ^ ti.u32(2891336453)
        )
        state = _seeded_state(seed ^ (ti.cast(run_id, ti.u32) * ti.u32(747796405)) ^ (ti.cast(g, ti.u32) * ti.u32(2891336453)))
        state = _xorshift32(state)
        for s in range(MAX_SLOTS):
            pool_start = fields.slot_start[s]
            pool_count = fields.slot_count[s]
            if pool_count <= 0:
                fields.population_indices[genome, s] = 0
                continue
            state = _xorshift32(state)
            state = _xorshift32(state)
            if g < heuristic_copies:
                fields.population_indices[genome, s] = fields.ga_init_heuristic_topk[
                    s, ti.cast(state % ti.u32(GA_INIT_HEURISTIC_K), ti.i32)
                ]
            else:
                fields.population_indices[genome, s] = pool_start + ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
        if fields.slot_count[6] > 1:
            m0, m1, m2, state = _repair_mini_uniqueness(
                fields.population_indices[genome, 6],
                fields.population_indices[genome, 7],
                fields.population_indices[genome, 8],
                state,
            )
            fields.population_indices[genome, 6] = m0
            fields.population_indices[genome, 7] = m1
            fields.population_indices[genome, 8] = m2


@ti.kernel
def load_population_kernel(population: ti.types.ndarray(dtype=ti.i32, ndim=2), n_genomes: ti.i32):
    for g, s in ti.ndrange(n_genomes, ti.static(MAX_SLOTS)):
        fields.population_indices[g, s] = population[g, s]


@ti.func
def _base_stats7(ids: ti.types.vector(MAX_SLOTS, ti.i32), flags: GpuColorFlags) -> ti.types.vector(7, ti.i32):
    """[PP, CM, FM, primary, secondary, FT, FF] of the fixed stats plus the items `ids` (id 0 = empty slot).

    item_stats layout: [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]; the primary / secondary value sums the
    element stats its color flags select (Beat<-FT, Vibe<-FF, Rush<-FM, Flow<-CM, Chill<-PP).
    """
    st = ti.Vector([fields.base_fixed_stats[c] for c in ti.static(range(ITEM_STAT_DIM))])
    for s in ti.static(range(MAX_SLOTS)):
        if ids[s] > 0:
            for c in ti.static(range(ITEM_STAT_DIM)):
                st[c] += fields.item_stats[ids[s], c]
    p_val = (st[5] * flags.is_p_ft) + (st[6] * flags.is_p_ff) + (st[7] * flags.is_p_fm) + (st[8] * flags.is_p_cm) + (st[9] * flags.is_p_pp)
    s_val = (st[5] * flags.is_s_ft) + (st[6] * flags.is_s_ff) + (st[7] * flags.is_s_fm) + (st[8] * flags.is_s_cm) + (st[9] * flags.is_s_pp)
    return ti.Vector([st[0], st[1], st[2], p_val, s_val, st[3], st[4]])


@ti.kernel
def aggregate_stats_kernel(n_genomes: ti.i32, flags: GpuColorFlags):
    for g in range(n_genomes):
        b = _base_stats7(ti.Vector([fields.population_indices[g, s] for s in ti.static(range(MAX_SLOTS))]), flags)
        for i in ti.static(range(7)):
            fields.genome_base_stats[g][i] = ti.cast(b[i], ti.i16)


@ti.func
def _memo_slot(g: ti.i32) -> ti.i32:
    h = ti.u32(2166136261)
    for i in ti.static(range(7)):
        value = ti.cast(fields.genome_base_stats[g][i], ti.i32)
        h = (h ^ ti.cast(value + 32769, ti.u32)) * ti.u32(16777619)
    return ti.cast(h % ti.u32(fields.GA_EVAL_CACHE_SIZE), ti.i32)


@ti.kernel
def find_representatives_kernel(n_genomes: ti.i32):
    """Each genome's row to evaluate: a memo hit restores its result, a miss takes the first miss of its memo slot when
    their stats are equal (O(n); misses of other stats sharing a slot are simply evaluated). Collisions evict memo
    entries, never alias results."""
    # Separate top-level loops provide a device barrier before owner selection and before the owners are read.
    for slot in range(fields.GA_EVAL_CACHE_SIZE):
        fields.ga_eval_cache_owner[slot] = n_genomes
    for g in range(n_genomes):
        fields.ga_eval_incumbent_score[g] = 0
        stats = fields.genome_base_stats[g]
        slot = _memo_slot(g)
        hit = fields.ga_eval_cache_key[slot] != ti.u64(0)
        for i in ti.static(range(7)):
            if stats[i] != fields.ga_eval_cache_stats[slot][i]:
                hit = False
        if hit:
            fields.chunk_best_key[g] = fields.ga_eval_cache_key[slot]
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = fields.ga_eval_cache_results[slot][i]
        else:
            fields.chunk_best_key[g] = ti.u64(0)
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = 0
            ti.atomic_min(fields.ga_eval_cache_owner[slot], g)
    for g in range(n_genomes):
        rep = g
        if fields.chunk_best_key[g] == ti.u64(0):
            owner = fields.ga_eval_cache_owner[_memo_slot(g)]
            same = True
            for i in ti.static(range(7)):
                if fields.genome_base_stats[g][i] != fields.genome_base_stats[owner][i]:
                    same = False
            if same:
                rep = owner
        fields.ga_exact_eval_rep_idx[g] = rep


@ti.kernel
def list_unique_rows_kernel(n_genomes: ti.i32):
    """The uncached representatives, which need the exact search; zero pending rows is valid."""
    ti.loop_config(serialize=True)
    count = 0
    for g in range(n_genomes):
        if fields.ga_exact_eval_rep_idx[g] == g and fields.chunk_best_key[g] == ti.u64(0):
            fields.ga_unique_slot_to_genome[count] = g
            count += 1
    fields.ga_exact_eval_unique_count[0] = count


@ti.kernel
def scatter_results_kernel(n_genomes: ti.i32):
    """Each duplicate's winner from its representative, then the new results into the memo."""
    for g in range(n_genomes):
        rep = fields.ga_exact_eval_rep_idx[g]
        if rep != g:
            fields.chunk_best_key[g] = fields.chunk_best_key[rep]
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = fields.chunk_best_results[rep, i]
    # One deterministic writer per slot; lookup completed before this dispatch.
    for slot in range(fields.GA_EVAL_CACHE_SIZE):
        g = fields.ga_eval_cache_owner[slot]
        if g < n_genomes:
            for i in ti.static(range(7)):
                fields.ga_eval_cache_stats[slot][i] = ti.cast(fields.genome_base_stats[g][i], ti.i32)
            fields.ga_eval_cache_key[slot] = fields.chunk_best_key[g]
            for i in ti.static(range(4)):
                fields.ga_eval_cache_results[slot][i] = fields.chunk_best_results[g, i]


@ti.func
def _solve_combo(
    combo_idx: ti.i32, flags: GpuColorFlags, stats: ti.types.vector(7, ti.i32), cull_threshold: ti.i32
) -> ti.types.vector(5, ti.i32):
    """[score, PP, CM, FM, element gems] of the best gem allocation spending combo combo_idx's FT/FF gems (a combo of the
    genome's key shortlist, none past MAX_STAT); score -1 when the combo's relaxed bound is below cull_threshold."""
    result = ti.Vector([-1, 0, 0, 0, 0], dt=ti.i32)
    ft: ti.i32 = fields.ftff_combo_ft[combo_idx]
    ff: ti.i32 = fields.ftff_combo_ff[combo_idx]
    ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, stats[5] + (ft * STAT_GEM_GAIN_FEVER)))
    ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, stats[6] + (ff * STAT_GEM_GAIN_FEVER)))
    head_len: ti.i32 = fields.grid_head_len[ft_idx, ff_idx]
    budget: ti.i32 = GEM_BUDGET - ft - ff
    p_val: ti.i32 = stats[3] + (ft * STAT_GEM_ELEMENT_GAIN * flags.is_p_ft) + (ff * STAT_GEM_ELEMENT_GAIN * flags.is_p_ff)
    s_val: ti.i32 = stats[4] + (ft * STAT_GEM_ELEMENT_GAIN * flags.is_s_ft) + (ff * STAT_GEM_ELEMENT_GAIN * flags.is_s_ff)
    pruned: ti.i32 = 0
    if cull_threshold > 0:
        bound = combo_upper_bound(budget, stats[0], stats[1], stats[2], p_val, s_val, flags, head_len,
                                  fields.grid_body_total[ft_idx, ff_idx])
        if bound < ti.cast(cull_threshold, ti.f32):
            pruned = 1
    if pruned == 0:
        result = exact_gem_search(budget, stats[0], stats[1], stats[2], p_val, s_val, flags, head_len, ft_idx, ff_idx,
                                  cull_threshold)
    return result


@ti.kernel
def search_combos_kernel(
    n_genomes: ti.i32,
    flags: GpuColorFlags,
    shortlist_start: ti.types.ndarray(dtype=ti.i32, ndim=1),
    shortlist_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    shortlist_combos: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """The exact search of every unique uncached row.

    The launch is sized by the host-known population; the live rows are read on the device, so a generation needs no
    host readback (a full pipeline drain). Each (row, lane) strides the combos of the genome's pre-gem (FT, FF) key in
    the song's shortlist (key ft * (MAX_STAT + 1) + ff owns shortlist_combos[start[key] : start[key] + count[key]]) and
    keeps its lane's winner; finish_lanes_kernel reduces the lanes (no u64 atomics: MoltenVK rejects atomic_fetch_max on
    ulong).
    """
    lanes = ti.static(GA_FTFF_LANES)
    for tid in range(n_genomes * lanes):
        slot_idx = tid // lanes
        if slot_idx >= fields.ga_exact_eval_unique_count[0]:
            continue
        lane = tid - slot_idx * lanes
        genome = fields.ga_unique_slot_to_genome[slot_idx]
        fields.ga_lane_best_key[genome, lane] = ti.u64(0)
        for i in ti.static(range(4)):
            fields.ga_lane_best_results[genome, lane, i] = 0
        stats = ti.cast(fields.genome_base_stats[genome], ti.i32)
        best_key = ti.u64(0)
        best = ti.Vector([0, 0, 0, 0, 0], dt=ti.i32)
        stat_key: ti.i32 = ti.min(stats[5], MAX_STAT) * (MAX_STAT + 1) + ti.min(stats[6], MAX_STAT)
        first: ti.i32 = shortlist_start[stat_key]
        n_key_combos: ti.i32 = shortlist_count[stat_key]
        local_c: ti.i32 = lane
        while local_c < n_key_combos:
            combo_idx: ti.i32 = shortlist_combos[first + local_c]
            # Skip the inner solve when even the relaxed bound cannot reach the best exact score already found for this
            # genome (here or in another lane). The threshold is that score, not score + 1: culling only bound < score
            # keeps every tie, so the winning combo is unchanged. Stale reads of the shared incumbent only cull less.
            cull_threshold: ti.i32 = ti.max(best[0], fields.ga_eval_incumbent_score[genome])
            result = _solve_combo(combo_idx, flags, stats, cull_threshold)
            if result[0] >= 0:
                key = (ti.cast(result[0] + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                if key > best_key:
                    best_key = key
                    best = result
                    ti.atomic_max(fields.ga_eval_incumbent_score[genome], result[0])
            local_c += lanes
        if best_key != ti.u64(0):
            fields.ga_lane_best_key[genome, lane] = best_key
            for i in ti.static(range(4)):
                fields.ga_lane_best_results[genome, lane, i] = best[1 + i]


@ti.kernel
def finish_lanes_kernel(n_genomes: ti.i32):
    # Only the unique uncached rows have fresh lanes: reducing every row would read stale lanes of duplicates.
    for s in range(n_genomes):
        if s >= fields.ga_exact_eval_unique_count[0]:
            continue
        g = fields.ga_unique_slot_to_genome[s]
        best_key = fields.chunk_best_key[g]
        best_lane = ti.i32(-1)
        for lane in range(GA_FTFF_LANES):
            key = fields.ga_lane_best_key[g, lane]
            if key > best_key:
                best_key = key
                best_lane = lane
        if best_lane >= 0:
            fields.chunk_best_key[g] = best_key
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = fields.ga_lane_best_results[g, best_lane, i]


@ti.func
def _result_row(genome: ti.i32) -> ti.types.vector(GA_RESULT_COLS, ti.i32):
    """[score, FT, FF, PP, CM, FM, element gems] of a genome's winner."""
    key = fields.chunk_best_key[genome]
    combo_idx = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
    result = ti.Vector.zero(ti.i32, GA_RESULT_COLS)
    result[0] = ti.cast(key >> ti.u64(32), ti.i32) - 1
    result[1] = fields.ftff_combo_ft[combo_idx]
    result[2] = fields.ftff_combo_ff[combo_idx]
    for i in ti.static(range(4)):
        result[3 + i] = fields.chunk_best_results[genome, i]
    return result


@ti.func
def _refresh_scores_and_runs_best(run_start: ti.i32, n_runs: ti.i32, n_genomes: ti.i32):
    """Every genome's score from its winner (-1 without one), and each run's best row where the run improved."""
    for g in range(n_runs * n_genomes):
        fields.ga_scores[g] = ti.cast(fields.chunk_best_key[g] >> ti.u64(32), ti.i32) - 1
    for r in range(n_runs):
        start: ti.i32 = r * n_genomes
        best_score: ti.i32 = -1
        best_g: ti.i32 = start
        for local_g in range(n_genomes):
            score = fields.ga_scores[start + local_g]
            if score > best_score:
                best_score = score
                best_g = start + local_g
        run_id = run_start + r
        if best_score > fields.ga_run_best[run_id, 0]:
            result = _result_row(best_g)
            fields.ga_run_best[run_id, 0] = result[0]
            for s in ti.static(range(MAX_SLOTS)):
                fields.ga_run_best[run_id, 1 + s] = fields.population_indices[best_g, s]
            for j in ti.static(range(GA_RESULT_COLS)):
                fields.ga_run_best[run_id, 1 + MAX_SLOTS + j] = result[j]


@ti.kernel
def update_runs_best_kernel(run_start: ti.i32, n_runs: ti.i32, n_genomes: ti.i32):
    _refresh_scores_and_runs_best(run_start, n_runs, n_genomes)


@ti.func
def _matches_parent(g: ti.i32, parent: ti.i32) -> ti.i32:
    match = ti.i32(1)
    for s in ti.static(range(MAX_SLOTS)):
        if fields.population_next_indices[g, s] != fields.population_indices[parent, s]:
            match = ti.i32(0)
    return match


@ti.func
def _repair_next_minis(g: ti.i32, state: ti.u32) -> ti.u32:
    """Next-generation genome g with its minis apart and sorted."""
    if fields.slot_count[6] > 1:
        m0, m1, m2, state = _repair_mini_uniqueness(
            fields.population_next_indices[g, 6],
            fields.population_next_indices[g, 7],
            fields.population_next_indices[g, 8],
            state,
        )
        fields.population_next_indices[g, 6] = m0
        fields.population_next_indices[g, 7] = m1
        fields.population_next_indices[g, 8] = m2
    return state


@ti.func
def _mutate_to_other_item(g: ti.i32, state: ti.u32) -> ti.u32:
    state = _xorshift32(state)
    mut_slot = ti.cast(state % ti.u32(MAX_SLOTS), ti.i32)
    pool_start = fields.slot_start[mut_slot]
    pool_count = fields.slot_count[mut_slot]
    if pool_count > 0:
        old_item = fields.population_next_indices[g, mut_slot]
        state = _xorshift32(state)
        offset = ti.cast(state % ti.cast(pool_count, ti.u32), ti.i32)
        if pool_count > 1:
            current_offset = old_item - pool_start
            if current_offset >= 0 and current_offset < pool_count and offset >= current_offset:
                offset = (offset + 1) % pool_count
        fields.population_next_indices[g, mut_slot] = pool_start + offset
        state = _repair_next_minis(g, state)
    return state


@ti.func
def _repair_parent_clone(g: ti.i32, pa: ti.i32, pb: ti.i32, state: ti.u32) -> ti.u32:
    """A child that came out as a copy of a parent is mutated, a bounded number of times."""
    clone = _matches_parent(g, pa)
    if clone == 0:
        clone = _matches_parent(g, pb)
    for _ in ti.static(range(GA_NOVELTY_REPAIR_ATTEMPTS)):
        if clone != 0:
            state = _mutate_to_other_item(g, state)
            clone = _matches_parent(g, pa)
            if clone == 0:
                clone = _matches_parent(g, pb)
    return state


@ti.func
def _fg_proxy(genome: ti.i32) -> ti.i64:
    stats7 = fields.genome_base_stats[genome]
    return (
        ti.cast(stats7[2], ti.i64) * 4
        + ti.cast(stats7[6], ti.i64) * 4
        + ti.cast(stats7[5], ti.i64) * 3
        + ti.cast(stats7[1], ti.i64) * 2
        + ti.cast(stats7[0], ti.i64)
        + ti.cast(stats7[3], ti.i64) * 2
        + ti.cast(stats7[4], ti.i64)
    )


@ti.func
def _base_stats_dominate(a: ti.i32, b: ti.i32) -> ti.i32:
    """Pointwise pre-gem dominance, for exact score ties."""
    dominates = ti.i32(1)
    strictly_better = ti.i32(0)
    for i in ti.static(range(7)):
        av = ti.cast(fields.genome_base_stats[a][i], ti.i32)
        bv = ti.cast(fields.genome_base_stats[b][i], ti.i32)
        if av < bv:
            dominates = ti.i32(0)
        if av > bv:
            strictly_better = ti.i32(1)
    return dominates & strictly_better


@ti.func
def _breed_next_generation(n_runs: ti.i32, n_genomes: ti.i32):
    """Each run's first genome is its best (the first of the best scores); every other comes from a tournament of each
    parent, a uniform crossover, a mutation at _MUTATION_RATE_FP and the repairs."""
    for g in range(n_runs * n_genomes):
        run: ti.i32 = g // n_genomes
        local_g: ti.i32 = g - run * n_genomes
        run_start: ti.i32 = run * n_genomes
        if local_g == 0:
            elite: ti.i32 = run_start
            elite_score: ti.i32 = -1
            for local_idx in range(n_genomes):
                score: ti.i32 = fields.ga_scores[run_start + local_idx]
                if score > elite_score:
                    elite_score = score
                    elite = run_start + local_idx
            for s in ti.static(range(MAX_SLOTS)):
                fields.population_next_indices[g, s] = fields.population_indices[elite, s]
            continue
        state = fields.ga_rng_state[g]
        pa = run_start
        pa_score = ti.cast(-2147483648, ti.i32)
        for _ in range(GA_TOURNAMENT_K):
            state = _xorshift32(state)
            idx = run_start + ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = fields.ga_scores[idx]
            if sc > pa_score or (sc == pa_score and _base_stats_dominate(idx, pa) != 0):
                pa_score = sc
                pa = idx
        pb = run_start
        pb_score = ti.cast(-2147483648, ti.i32)
        pb_proxy = ti.i64(-1)
        state = _xorshift32(state)
        diverse_b = state < ti.u32(_DIVERSE_PARENT_B_RATE_FP)
        for _ in range(GA_TOURNAMENT_K):
            state = _xorshift32(state)
            idx = run_start + ti.cast(state % ti.cast(n_genomes, ti.u32), ti.i32)
            sc = fields.ga_scores[idx]
            if diverse_b:
                proxy = _fg_proxy(idx)
                if (
                    proxy > pb_proxy
                    or (proxy == pb_proxy and sc > pb_score)
                    or (proxy == pb_proxy and sc == pb_score and _base_stats_dominate(idx, pb) != 0)
                ):
                    pb_proxy = proxy
                    pb_score = sc
                    pb = idx
            elif sc > pb_score or (sc == pb_score and _base_stats_dominate(idx, pb) != 0):
                pb_score = sc
                pb = idx
        for s in range(MAX_SLOTS):
            state = _xorshift32(state)
            parent = pa if (state & ti.u32(1)) != 0 else pb
            fields.population_next_indices[g, s] = fields.population_indices[parent, s]
        state = _xorshift32(state)
        if state < ti.u32(_MUTATION_RATE_FP):
            state = _xorshift32(state)
            mut_slot = ti.cast(state % ti.u32(MAX_SLOTS), ti.i32)
            pool_count = fields.slot_count[mut_slot]
            if pool_count > 0:
                state = _xorshift32(state)
                fields.population_next_indices[g, mut_slot] = fields.slot_start[mut_slot] + ti.cast(
                    state % ti.cast(pool_count, ti.u32), ti.i32
                )
        state = _repair_next_minis(g, state)
        state = _repair_parent_clone(g, pa, pb, state)
        fields.ga_rng_state[g] = state


@ti.kernel
def next_generation_kernel(run_start: ti.i32, n_runs: ti.i32, n_genomes: ti.i32):
    """One transition in one dispatch: the scores and run bests of the evaluated population (before it changes), the next
    generation, and the swap."""
    _refresh_scores_and_runs_best(run_start, n_runs, n_genomes)
    _breed_next_generation(n_runs, n_genomes)
    for g, s in ti.ndrange(n_runs * n_genomes, ti.static(MAX_SLOTS)):
        fields.population_indices[g, s] = fields.population_next_indices[g, s]


@ti.func
def _sort3_i32(a: ti.i32, b: ti.i32, c: ti.i32) -> ti.types.vector(3, ti.i32):
    if b < a:
        a, b = b, a
    if c < b:
        b, c = c, b
    if b < a:
        a, b = b, a
    return ti.Vector([a, b, c])


@ti.func
def _sorted_minis(genome: ti.i32) -> ti.types.vector(3, ti.i32):
    return _sort3_i32(
        fields.population_indices[genome, 6], fields.population_indices[genome, 7], fields.population_indices[genome, 8]
    )


@ti.func
def _same_loadout(genome: ti.i32, gears: ti.types.vector(6, ti.i32), minis: ti.types.vector(3, ti.i32)) -> ti.i32:
    same = ti.i32(1)
    for s in ti.static(range(6)):
        if fields.population_indices[genome, s] != gears[s]:
            same = ti.i32(0)
    if (_sorted_minis(genome) != minis).any():
        same = ti.i32(0)
    return same


@ti.func
def _write_candidate(run_id: ti.i32, row: ti.i32, genome: ti.i32, result: ti.types.vector(GA_RESULT_COLS, ti.i32)):
    fields.ga_fg_candidates[run_id, row, 0] = result[0]
    for s in ti.static(range(6)):
        fields.ga_fg_candidates[run_id, row, 1 + s] = fields.population_indices[genome, s]
    minis = _sorted_minis(genome)
    for s in ti.static(range(3)):
        fields.ga_fg_candidates[run_id, row, 7 + s] = minis[s]
    for j in ti.static(range(GA_RESULT_COLS)):
        fields.ga_fg_candidates[run_id, row, 1 + MAX_SLOTS + j] = result[j]
    stats = fields.genome_base_stats[genome]
    for j in ti.static(range(7)):
        fields.ga_fg_candidates[run_id, row, 1 + MAX_SLOTS + GA_RESULT_COLS + j] = ti.cast(stats[j], ti.i32)


@ti.func
def _keep_top_candidate(top_scores: ti.template(), top_idx: ti.template(), score: ti.i32, g: ti.i32):
    """Genome g into a run's top rows, score order: a loadout already there keeps its better score; the dedup comes
    before the cut, or copies of a converged genome would crowd out lower unique ones."""
    K = ti.static(GA_FG_CANDIDATES_PER_RUN)
    gears = ti.Vector([fields.population_indices[g, s] for s in ti.static(range(6))])
    minis = _sorted_minis(g)
    duplicate = ti.i32(-1)
    for j in range(K):
        if duplicate < 0 and top_idx[j] >= 0 and _same_loadout(top_idx[j], gears, minis) != 0:
            duplicate = j
    if duplicate >= 0:
        if score > top_scores[duplicate]:
            top_scores[duplicate] = score
            top_idx[duplicate] = g
            cur = duplicate
            while cur > 0 and top_scores[cur] > top_scores[cur - 1]:
                top_scores[cur - 1], top_scores[cur] = top_scores[cur], top_scores[cur - 1]
                top_idx[cur - 1], top_idx[cur] = top_idx[cur], top_idx[cur - 1]
                cur -= 1
    else:
        inserted = ti.i32(0)
        for j in range(K):
            if inserted == 0 and score > top_scores[j]:
                tt = K - 1
                while tt > j:
                    top_scores[tt] = top_scores[tt - 1]
                    top_idx[tt] = top_idx[tt - 1]
                    tt -= 1
                top_scores[j] = score
                top_idx[j] = g
                inserted = 1


@ti.kernel
def pack_candidates_kernel(run_start: ti.i32, n_runs: ti.i32, n_genomes: ti.i32):
    """Rows 1..GA_FG_CANDIDATES_PER_RUN of each run's candidate table: the top unique genomes of its final population."""
    K = ti.static(GA_FG_CANDIDATES_PER_RUN)
    for r in range(n_runs):
        run_id = run_start + r
        top_scores = ti.Vector([-2147483648] * K, dt=ti.i32)
        top_idx = ti.Vector([-1] * K, dt=ti.i32)
        start = r * n_genomes
        for local_g in range(n_genomes):
            score = fields.ga_scores[start + local_g]
            if score > 0:
                _keep_top_candidate(top_scores, top_idx, score, start + local_g)
        for j in range(K):
            for c in ti.static(range(fields.GA_FG_CANDIDATE_COLS)):
                fields.ga_fg_candidates[run_id, 1 + j, c] = 0
            if top_idx[j] >= 0:
                _write_candidate(run_id, 1 + j, top_idx[j], _result_row(top_idx[j]))


@ti.kernel
def pack_run_bests_kernel(n_runs: ti.i32, flags: GpuColorFlags):
    """Row 0 of each run's candidate table: its best across generations (after the polish, which consumes the population),
    minis sorted, pre-gem stats recomputed from the item ids."""
    for r in range(n_runs):
        for c in ti.static(range(fields.GA_RUN_BEST_COLS)):
            fields.ga_fg_candidates[r, 0, c] = fields.ga_run_best[r, c]
        minis = _sort3_i32(fields.ga_run_best[r, 7], fields.ga_run_best[r, 8], fields.ga_run_best[r, 9])
        for s in ti.static(range(3)):
            fields.ga_fg_candidates[r, 0, 7 + s] = minis[s]
        ids = ti.Vector([fields.ga_run_best[r, 1 + s] for s in ti.static(range(MAX_SLOTS))])
        stats = _base_stats7(ids, flags)
        for i in ti.static(range(7)):
            fields.ga_fg_candidates[r, 0, 1 + MAX_SLOTS + GA_RESULT_COLS + i] = stats[i]
