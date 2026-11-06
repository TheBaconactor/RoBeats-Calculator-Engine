"""The GA's Taichi kernels. A batch's runs lie contiguously in the population: genome g of run r at r * n_genomes + g."""

from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_NORMAL
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
from .scoring import (
    GpuColorFlags,
    exact_gem_search,
    gem_weights,
    gem_reference,
    gems_to_cap,
    lookup_ref_cm,
    lookup_ref_fm,
    lookup_ref_pp,
    pair_score,
    reference_bound,
    search_context,
    shape_value,
    surface_search,
)

_I32_ARRAY = ti.types.ndarray(dtype=ti.i32, ndim=1)
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
        sigma_hn: ti.f32 = ti.cast(head_coeffs[i, 2], ti.f32) / 100.0
        sigma_hf: ti.f32 = ti.cast(head_coeffs[i, 3], ti.f32) / 100.0
        fields.grid_frontier_shape_pool[i] = ti.Vector([
            ti.cast(body_fever[i], ti.f32) + sigma_hf, ti.cast(body_normal[i], ti.f32) + sigma_hn,
            ti.cast(head_coeffs[i, 1], ti.f32) - sigma_hf, ti.cast(head_coeffs[i, 0], ti.f32) - sigma_hn,
        ])


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


@ti.func
def _aggregate_stats(n_genomes: ti.i32, flags: GpuColorFlags):
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


@ti.func
def _find_representatives(n_genomes: ti.i32):
    """Each genome's row to evaluate: a memo hit restores its result, a miss takes the first miss of its memo slot when
    their stats are equal (O(n); misses of other stats sharing a slot are simply evaluated). Collisions evict memo
    entries, never alias results."""
    fields.ga_search_count[0] = 0
    # Separate top-level loops provide a device barrier before owner selection and before the owners are read.
    for slot in range(fields.GA_EVAL_CACHE_SIZE):
        fields.ga_eval_cache_owner[slot] = n_genomes
    for g in range(n_genomes):
        fields.ga_eval_incumbent_score[g] = 0
        fields.ga_survivor_count[g] = 0
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


@ti.func
def _scatter_results(n_genomes: ti.i32):
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
def _combo_option(combo_idx: ti.i32, stats: ti.types.vector(7, ti.i32), flags: GpuColorFlags) -> ti.types.vector(4, ti.i32):
    """[first surface, surfaces, residual budget, 2 x primary + secondary] after a combo's FT/FF gems (a combo of the
    genome's key shortlist, none past MAX_STAT)."""
    ft: ti.i32 = fields.ftff_combo_ft[combo_idx]
    ff: ti.i32 = fields.ftff_combo_ff[combo_idx]
    ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, stats[5] + (ft * STAT_GEM_GAIN_FEVER)))
    ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, stats[6] + (ff * STAT_GEM_GAIN_FEVER)))
    p_val: ti.i32 = stats[3] + (ft * STAT_GEM_ELEMENT_GAIN * flags.is_p_ft) + (ff * STAT_GEM_ELEMENT_GAIN * flags.is_p_ff)
    s_val: ti.i32 = stats[4] + (ft * STAT_GEM_ELEMENT_GAIN * flags.is_s_ft) + (ff * STAT_GEM_ELEMENT_GAIN * flags.is_s_ff)
    return ti.Vector([
        fields.grid_frontier_offset[ft_idx, ff_idx], fields.grid_frontier_count[ft_idx, ff_idx], GEM_BUDGET - ft - ff,
        (p_val << 1) + s_val,
    ])


@ti.func
def _most_valuable_surface(combos: _I32_ARRAY, span, stats, flags: GpuColorFlags, pair, least_budget: ti.i32):
    """[surface, its residual budget, its 2 x primary + secondary, the largest budget] over the combos of a shortlist
    `span` (first, count): the surface of the highest value at the (CM, FM) gems `pair`, of a combo with least_budget."""
    weights = gem_weights(flags)
    w_ov: ti.i32 = weights[3]
    pair_cost: ti.i32 = (pair[0] * (w_ov - weights[1])) + (pair[1] * (w_ov - weights[2]))
    combo_mul: ti.f32 = lookup_ref_cm(stats[1] + (pair[0] * STAT_GEM_GAIN_NORMAL))
    fever_mul: ti.f32 = lookup_ref_fm(stats[2] + (pair[1] * STAT_GEM_GAIN_FEVER))
    pp_base: ti.f32 = lookup_ref_pp(stats[0])
    top_value: ti.f32 = -1.0e30
    top = ti.Vector([0, 0, 0], dt=ti.i32)
    largest_budget: ti.i32 = 0
    for k in range(span[1]):
        option = _combo_option(combos[span[0] + k], stats, flags)
        largest_budget = ti.max(largest_budget, option[2])
        if option[2] >= least_budget:
            base: ti.f32 = ti.cast(option[3] + (option[2] * w_ov) - pair_cost, ti.f32) + pp_base
            for pool_idx in range(option[0], option[0] + option[1]):
                value = base * shape_value(fields.grid_frontier_shape_pool[pool_idx], combo_mul, fever_mul)
                if value > top_value:
                    top_value = value
                    top = ti.Vector([pool_idx, option[2], option[3]])
    return ti.Vector([top[0], top[1], top[2], largest_budget])


@ti.func
def _reference_search(n_genomes: ti.i32, flags: GpuColorFlags, starts: _I32_ARRAY, counts: _I32_ARRAY, combos: _I32_ARRAY):
    """What each unique uncached row needs before its combos are searched: an incumbent, its reference and the combos
    that can reach the incumbent.

    The surface most valuable at capped multipliers is searched exactly over the largest residual budget of the row's
    combos, at the base value of its own budget: so its best score caps its value at every (CM, FM) pair any combo can
    spend, up to the notes' floors (scoring.gem_reference), and each other surface's follows through their ratios
    (scoring.reference_bound). A combo of that budget can spend the best pair, and the surface most valuable there,
    nearly always the row's winner, scored there is the incumbent."""
    w_ov: ti.i32 = gem_weights(flags)[3]
    for genome in range(n_genomes):
        if fields.ga_exact_eval_rep_idx[genome] == genome and fields.chunk_best_key[genome] == ti.u64(0):
            stats = ti.cast(fields.genome_base_stats[genome], ti.i32)
            stat_key: ti.i32 = ti.min(stats[5], MAX_STAT) * (MAX_STAT + 1) + ti.min(stats[6], MAX_STAT)
            span = ti.Vector([starts[stat_key], counts[stat_key]])
            if span[1] > 0:
                caps = ti.Vector([gems_to_cap(stats[1], STAT_GEM_GAIN_NORMAL), gems_to_cap(stats[2], STAT_GEM_GAIN_FEVER)])
                top = _most_valuable_surface(combos, span, stats, flags, caps, 0)
                base: ti.i32 = top[2] + (top[1] * w_ov)
                wide = search_context(top[3], stats, base - (top[3] * w_ov), flags, top[0])
                best = surface_search(wide, 0)
                pair = ti.Vector([best[2], best[3]])
                top = _most_valuable_surface(combos, span, stats, flags, pair, pair[0] + pair[1])
                incumbent = pair_score(search_context(top[1], stats, top[2], flags, top[0]), pair[0], pair[1])
                reference = gem_reference(wide, base, best[0])
                fields.ga_eval_incumbent_score[genome] = incumbent
                fields.ga_gem_reference[genome] = reference
                survivors = ti.i32(0)
                for k in range(span[1]):
                    combo_idx: ti.i32 = combos[span[0] + k]
                    option = _combo_option(combo_idx, stats, flags)
                    option_base: ti.f32 = ti.cast(option[3] + (option[2] * w_ov), ti.f32)
                    reaches = ti.i32(0)
                    for pool_idx in range(option[0], option[0] + option[1]):
                        bound = reference_bound(reference, option_base, fields.grid_frontier_shape_pool[pool_idx])
                        if bound >= ti.cast(incumbent, ti.f32):
                            reaches = 1
                    if reaches != 0:
                        if survivors < GA_FTFF_LANES:
                            fields.ga_survivors[genome, survivors] = combo_idx
                            slot = ti.atomic_add(fields.ga_search_count[0], 1)
                            fields.ga_search_list[slot] = (genome * GA_FTFF_LANES) + survivors
                        survivors += 1
                fields.ga_survivor_count[genome] = survivors


@ti.func
def _search_combos(n_genomes: ti.i32, flags: GpuColorFlags, starts: _I32_ARRAY, counts: _I32_ARRAY, combos: _I32_ARRAY):
    """The exact search of the listed combos, each thread its genome's lane, which keeps its lane's winner; finish_lanes
    reduces the lanes (no u64 atomics: MoltenVK rejects atomic_fetch_max on ulong). A row with too many combos to list
    has every lane stride its shortlist.

    The launch is sized by the host-known population; the live threads are read on the device, so a generation needs no
    host readback (a full pipeline drain). A SIMD group runs as long as its slowest thread, so they are packed."""
    lanes = ti.static(GA_FTFF_LANES)
    for slot in range(n_genomes * lanes):
        if slot >= fields.ga_search_count[0]:
            continue
        entry = fields.ga_search_list[slot]
        genome = entry // lanes
        lane = entry - genome * lanes
        survivors = fields.ga_survivor_count[genome]
        fields.ga_lane_best_key[genome, lane] = ti.u64(0)
        for i in ti.static(range(4)):
            fields.ga_lane_best_results[genome, lane, i] = 0
        stats = ti.cast(fields.genome_base_stats[genome], ti.i32)
        reference = fields.ga_gem_reference[genome]
        best_key = ti.u64(0)
        best = ti.Vector([0, 0, 0, 0, 0], dt=ti.i32)
        stat_key: ti.i32 = ti.min(stats[5], MAX_STAT) * (MAX_STAT + 1) + ti.min(stats[6], MAX_STAT)
        listed = survivors <= lanes
        n_combos: ti.i32 = survivors if listed else counts[stat_key]
        local_c: ti.i32 = lane
        while local_c < n_combos:
            combo_idx: ti.i32 = combos[starts[stat_key] + local_c]
            if listed:
                combo_idx = fields.ga_survivors[genome, local_c]
            # The threshold is the best exact score found for this genome (here or in another lane), not score + 1:
            # culling only bound < score keeps every tie, so the winning combo is unchanged. Stale reads of the shared
            # incumbent only cull less.
            cull_threshold: ti.i32 = ti.max(best[0], fields.ga_eval_incumbent_score[genome])
            result = exact_gem_search(_combo_option(combo_idx, stats, flags), stats, flags, cull_threshold, reference)
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


@ti.func
def _finish_lanes(n_genomes: ti.i32):
    for g in range(n_genomes):
        best_key = fields.chunk_best_key[g]
        best_lane = ti.i32(-1)
        for lane in range(ti.min(fields.ga_survivor_count[g], GA_FTFF_LANES)):
            key = fields.ga_lane_best_key[g, lane]
            if key > best_key:
                best_key = key
                best_lane = lane
        if best_lane >= 0:
            fields.chunk_best_key[g] = best_key
            for i in ti.static(range(4)):
                fields.chunk_best_results[g, i] = fields.ga_lane_best_results[g, best_lane, i]


@ti.kernel
def evaluate_kernel(n_genomes: ti.i32, flags: GpuColorFlags, starts: _I32_ARRAY, counts: _I32_ARRAY, combos: _I32_ARRAY):
    """The exact evaluation of the population in one launch: memo hits restored, each unique uncached row searched,
    duplicates scattered. Each step's top-level loop is a dispatch of its own, with a barrier before the next."""
    _aggregate_stats(n_genomes, flags)
    _find_representatives(n_genomes)
    _reference_search(n_genomes, flags, starts, counts, combos)
    _search_combos(n_genomes, flags, starts, counts, combos)
    _finish_lanes(n_genomes)
    _scatter_results(n_genomes)


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
    """Genome g into a run's top rows, score order, unless a row holds its loadout; the dedup comes before the cut, or
    copies of a converged genome would crowd out lower unique ones. Equal loadouts have equal scores: only rows of g's
    score can be copies."""
    K = ti.static(GA_FG_CANDIDATES_PER_RUN)
    gears = ti.Vector([fields.population_indices[g, s] for s in ti.static(range(6))])
    minis = _sorted_minis(g)
    position = ti.i32(0)
    while position < K and top_scores[position] > score:
        position += 1
    copy = ti.i32(0)
    while position < K and top_scores[position] == score and copy == 0:
        copy = _same_loadout(top_idx[position], gears, minis)
        position += 1
    if copy == 0 and position < K:
        tt = K - 1
        while tt > position:
            top_scores[tt] = top_scores[tt - 1]
            top_idx[tt] = top_idx[tt - 1]
            tt -= 1
        top_scores[position] = score
        top_idx[position] = g


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
