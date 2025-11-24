-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v4 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_5 = {
    ["get_invalid_material_id"] = function(_) --[[ Name: get_invalid_material_id ]] --[[ Line: 25 ]]
        return -1;
    end,
    ["brass_token_id"] = function(_) --[[ Name: brass_token_id ]] --[[ Line: 33 ]]
        return 21;
    end,
    ["silver_token_id"] = function(_) --[[ Name: silver_token_id ]] --[[ Line: 34 ]]
        return 22;
    end,
    ["gold_token_id"] = function(_) --[[ Name: gold_token_id ]] --[[ Line: 35 ]]
        return 23;
    end
}
local function f_dict_tier_to_material(p6, p7, p8, p9) --[[ Name: dict_tier_to_material ]] --[[ Line: 8 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1 ]]
    return v_u_3:new():add_table({
        [v_u_1.Tier.T1] = p6,
        [v_u_1.Tier.T2] = p7,
        [v_u_1.Tier.T3] = p8,
        [v_u_1.Tier.T4] = p9
    });
end;
local v_u_10 = v_u_3:new():add_table({
    [v4.Blue] = f_dict_tier_to_material(1, 2, 3, 4),
    [v4.Green] = f_dict_tier_to_material(5, 6, 7, 8),
    [v4.Orange] = f_dict_tier_to_material(9, 10, 11, 12),
    [v4.Purple] = f_dict_tier_to_material(13, 14, 15, 16),
    [v4.Red] = f_dict_tier_to_material(17, 18, 19, 20)
})
v_u_5.get_dict = function(_) --[[ Name: get_dict ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    return v_u_10;
end;
v_u_5.color_and_tier_to_material_id = function(_, p11, p12) --[[ Name: color_and_tier_to_material_id ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_5 ]]
    if v_u_10:contains(p11) == true then
        local v13 = v_u_10:get(p11)
        if v13:contains(p12) == true then
            return v13:get(p12);
        else
            return v_u_5:get_invalid_material_id();
        end;
    else
        return v_u_5:get_invalid_material_id();
    end;
end;
v_u_5.get_token_id_set = function(_) --[[ Name: get_token_id_set ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_5 ]]
    return v_u_3:new():add_set_from_table_list({ v_u_5:brass_token_id(), v_u_5:silver_token_id(), v_u_5:gold_token_id() });
end;
local v_u_14 = v_u_3:new()
for v15, v16 in v_u_10:key_itr() do
    for v17, v18 in v16:key_itr() do
        v_u_14:add(v18, v2:new():push_back_table_list({ v15, v17 }))
    end;
end;
v_u_5.get_color_and_tier_for_material_id = function(_, p19) --[[ Name: get_color_and_tier_for_material_id ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14:get(p19);
end;
return v_u_5;
