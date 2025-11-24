-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_4 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_5 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v7 = {
    ["get_crafting_token_material_ids"] = function(_) --[[ Name: get_crafting_token_material_ids ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4 ]]
        return v_u_1:new():push_back_table_list({ v_u_4:brass_token_id(), v_u_4:silver_token_id(), v_u_4:gold_token_id() });
    end
}
local function f_get_tier_materials_list(p8) --[[ Name: get_tier_materials_list ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_2 ]]
    local v9 = v_u_1:new()
    for _, v10 in v_u_5:colors_list():key_itr() do
        local v11 = v_u_4:color_and_tier_to_material_id(v10, p8)
        v_u_6:is_true(v_u_2:singleton():contains_material(v11))
        v9:push_back(v11)
    end;
    return v9;
end;
v7.get_gem_material_ids = function(_) --[[ Name: get_gem_material_ids ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): f_get_tier_materials_list, (copy 2): v_u_3 ]]
    return f_get_tier_materials_list(v_u_3.Tier.T4);
end;
v7.get_large_note_material_ids = function(_) --[[ Name: get_large_note_material_ids ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): f_get_tier_materials_list, (copy 2): v_u_3 ]]
    return f_get_tier_materials_list(v_u_3.Tier.T3);
end;
v7.get_medium_note_material_ids = function(_) --[[ Name: get_medium_note_material_ids ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): f_get_tier_materials_list, (copy 2): v_u_3 ]]
    return f_get_tier_materials_list(v_u_3.Tier.T2);
end;
v7.get_small_note_material_ids = function(_) --[[ Name: get_small_note_material_ids ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): f_get_tier_materials_list, (copy 2): v_u_3 ]]
    return f_get_tier_materials_list(v_u_3.Tier.T1);
end;
local v_u_12 = v_u_1:new()
local v_u_13 = v_u_1:new()
for v14, v15 in v_u_2:singleton():material_key_itr() do
    if v15:is_blueprint() then
        if v15:get_tier() == v_u_3.Tier.T4 then
            v_u_12:push_back(v14)
        elseif v15:get_tier() == v_u_3.Tier.T3 then
            v_u_13:push_back(v14)
        end;
    end;
end;
v7.get_legendary_blueprint_material_ids = function(_) --[[ Name: get_legendary_blueprint_material_ids ]] --[[ Line: 55 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return v_u_12;
end;
v7.get_rare_blueprint_material_ids = function(_) --[[ Name: get_rare_blueprint_material_ids ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13;
end;
return v7;
