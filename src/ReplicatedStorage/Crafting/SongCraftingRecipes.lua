-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Crafting.SongRecipeBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_8 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
return {
    ["add_to_craftdatabase"] = function(_, p9) --[[ Name: add_to_craftdatabase ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_7, (copy 3): v_u_2, (copy 4): v_u_3, (copy 5): v_u_6, (copy 6): v_u_8, (copy 7): v_u_5, (copy 8): v_u_1 ]]
        for v10, v_u_11 in v_u_4:singleton():all_keys():key_itr() do
            if v_u_4:singleton():key_get_audiomod(v_u_11) == v_u_4.MOD_NORMAL and v_u_4:singleton():get_songkey_should_grant(v_u_11) then
                local v12 = v_u_4:singleton():get_difficulty_for_key(v_u_11)
                local v13 = v_u_7:songkey_get_color_list(v_u_11)
                local v14 = v_u_7:songkey_primary_color(v_u_11)
                local v15 = v_u_7:songkey_has_secondary_color(v_u_11)
                local v16
                if v15 then
                    v16 = v_u_7:songkey_secondary_color(v_u_11)
                else
                    v16 = v14
                end;
                local v17 = 0
                local v18
                if v13:count() >= 2 then
                    v18 = math.ceil(v_u_2:clamp(v12, 5, 30) * 0.5)
                    v17 = math.ceil(v_u_2:clamp(v12, 5, 30) * 0.25)
                else
                    v18 = math.ceil(v_u_2:clamp(v12, 5, 30) * 0.75)
                end;
                local v_u_19 = v_u_3:new()
                local function f_add_to_materials_table(p20, p21) --[[ Name: add_to_materials_table ]] --[[ Line: 37 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_19 ]]
                    local v22 = v_u_6:color_and_tier_to_material_id(p20, p21)
                    local v23 = v_u_19:get(v22)
                    if v23 == nil then
                        if v_u_19:count() >= 4 then
                            return false;
                        end;
                        v_u_19:add(v22, 1)
                    else
                        v_u_19:add(v22, v23 + 1)
                    end;
                    return true;
                end;
                while v18 >= 10 do
                    f_add_to_materials_table(v14, v_u_8.Tier.T2)
                    v18 = v18 - 10
                end;
                while v18 >= 1 do
                    f_add_to_materials_table(v14, v_u_8.Tier.T1)
                    v18 = v18 - 1
                end;
                if v15 then
                    while v17 >= 10 do
                        f_add_to_materials_table(v16, v_u_8.Tier.T2)
                        v17 = v17 - 10
                    end;
                    while v17 >= 1 do
                        f_add_to_materials_table(v16, v_u_8.Tier.T1)
                        v17 = v17 - 1
                    end;
                end;
                if v_u_19:count() == 0 or v_u_19:count() > 4 then
                    v_u_5:errf("ERROR IN SongCraftingRecipes gen(%d,%s)", v_u_11, v_u_2:table_to_string(v_u_19._table))
                end;
                local v24 = v_u_1:new()
                v24.get_song = function(_) --[[ Name: get_song ]] --[[ Line: 74 ]]
                    --[[ Upvalues: (copy 1): v_u_11 ]]
                    return v_u_11;
                end;
                v24.get_requirements = function(_, p25) --[[ Name: get_requirements ]] --[[ Line: 75 ]]
                    --[[ Upvalues: (copy 1): v_u_19 ]]
                    p25:clear()
                    for v26, v27 in v_u_19:key_itr() do
                        p25:add(v26, v27)
                    end;
                end;
                p9:add_to_song_recipe_dict(v10, v24)
            end;
        end;
    end
};
