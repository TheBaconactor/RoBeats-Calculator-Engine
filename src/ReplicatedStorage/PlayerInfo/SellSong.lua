-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_5 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
require(game.ReplicatedStorage.Avatar.ElementalColor)
require(game.ReplicatedStorage.PlayerInfo.MatchEndRouletteReward)
local v_u_7 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_21 = {
    ["get_sell_rewards_dict"] = function(_, p8) --[[ Name: get_sell_rewards_dict ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_5 ]]
        local v9 = v_u_3:new()
        local v10 = v_u_2:singleton():key_get_audiomod(p8)
        local v11 = v_u_2:singleton():get_audiomod_to_modes_of_songkey(p8):get(v_u_2.MOD_NORMAL)
        local v12
        if v11 == nil then
            v12 = nil
        else
            v12 = v_u_4:singleton():get_songkey_recipe_id(v11)
        end;
        if v10 == v_u_2.MOD_HARDMODE and v12 ~= nil then
            for v13, v14 in v_u_4:singleton():get_song_recipe_requirements_dict(v12):key_itr() do
                v9:add(v13, (math.max(1, v14 * (v_u_2.NORMAL_COMBINE_COUNT - 1))))
            end;
            return v9;
        end;
        if v12 ~= nil then
            for v15, _ in v_u_4:singleton():get_song_recipe_requirements_dict(v12):key_itr() do
                v9:add(v15, 1)
            end;
            return v9;
        end;
        if not v_u_6:songkey_has_secondary_color(p8) then
            v9:add(v_u_7:color_and_tier_to_material_id(v_u_6:songkey_primary_color(p8), v_u_5.Tier.T1), 2)
            return v9;
        end;
        v9:add(v_u_7:color_and_tier_to_material_id(v_u_6:songkey_primary_color(p8), v_u_5.Tier.T1), 1)
        v9:add(v_u_7:color_and_tier_to_material_id(v_u_6:songkey_secondary_color(p8), v_u_5.Tier.T1), 1)
        return v9;
    end,
    ["rewards_dict_to_string"] = function(_, p16) --[[ Name: rewards_dict_to_string ]] --[[ Line: 57 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v17 = ""
        for v18, v19 in p16:key_itr() do
            local v20 = string.format("%s x%d", v_u_4:singleton():get_material_name(v18), v19)
            if #v17 == 0 then
                v17 = v20
            else
                v17 = v17 .. ", " .. v20
            end;
        end;
        return v17;
    end,
    ["can_sell_key"] = function(_, _) --[[ Name: can_sell_key ]] --[[ Line: 76 ]]
        return true;
    end
}
v_u_21.playerblob_can_sell_key = function(_, p22, p23) --[[ Name: playerblob_can_sell_key ]] --[[ Line: 70 ]]
    --[[ Upvalues: (copy 1): v_u_21, (copy 2): v_u_1 ]]
    if v_u_21:can_sell_key(p23) == false then
        return false;
    end;
    local v24 = v_u_1:get_song_key_owned_count(p22, p23)
    return v24 > 0, v24;
end;
return v_u_21;
