"""RoBeats game rules that scores and the cached timing/FG frontiers depend on.

This module is part of the frontier cache fingerprint (response_cache_types / taichi_gem.api.timeline):
changing anything here rotates every cache version. Keep it to game rules.
"""

# The game's stat curves (gamedata.StatCurves) are indexed by stat value 0..MAX_STAT; higher values read the last one.
MAX_STAT = 160
GEM_BUDGET = 90
# A stat gem raises its stat by this much: Perfect Points and Combo Multiplier gain the normal amount,
# Fever Multiplier, Fever Time and Fever Fill Rate the fever amount.
STAT_GEM_GAIN_NORMAL = 2
STAT_GEM_GAIN_FEVER = 3
# ...and its element (PP: Chill, CM: Flow, FM: Rush, FT: Beat, FF: Vibe) by this much.
STAT_GEM_ELEMENT_GAIN = 3
# An element gem raises the selected element.
ELEMENT_GEM_GAIN = 6
