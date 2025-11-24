-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:04 PM
-- Cached decompilation

return {
    ["get_chain_target_scale"] = function(_, p1, p2, p3) --[[ Name: get_chain_target_scale ]] --[[ Line: 3 ]]
        local v4 = p2:es_gamelocal_get_tracksystems():get(p3)
        return v4 == nil and 0.85 or (v4:get_tier3_combo_count() < p1 and 1.35 or (v4:get_tier2_combo_count() < p1 and 1.19 or (v4:get_tier1_combo_count() < p1 and 1.02 or 0.85)));
    end,
    ["notif_index"] = function(_, p5, p6, p7) --[[ Name: notif_index ]] --[[ Line: 20 ]]
        local v8 = p6:es_gamelocal_get_tracksystems():get(p7)
        return v8 == nil and 1 or (v8:get_tier3_combo_count() < p5 and 4 or (v8:get_tier2_combo_count() < p5 and 3 or (v8:get_tier1_combo_count() < p5 and 2 or 1)));
    end
};
