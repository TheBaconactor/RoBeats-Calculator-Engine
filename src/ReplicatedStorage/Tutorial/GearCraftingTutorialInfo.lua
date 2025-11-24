-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_4 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_5 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_11 = {
    ["get_craft_gear_icon"] = function(_) --[[ Name: get_craft_gear_icon ]] --[[ Line: 10 ]]
        return "http://www.roblox.com/asset/?id=6276642298";
    end,
    ["has_any_equipped_gear"] = function(_, p6) --[[ Name: has_any_equipped_gear ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v7
        if v_u_4:get_owned_equipment_list(p6):count() > 0 then
            v7 = v_u_4:playerblob_slot_to_equippedobj_dict(p6):count() > 0
        else
            v7 = false
        end;
        return v7;
    end,
    ["has_any_gear_upgrades"] = function(_, p8) --[[ Name: has_any_gear_upgrades ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v9 = v_u_4:get_owned_equipment_list(p8)
        for v10 = 1, v9:count() do
            if v_u_4:get_ownedid_upgrade_count(p8, v9:get(v10).OwnedID) > 0 then
                return true;
            end;
        end;
        return false;
    end
}
local v_u_12 = v1:new():add_table({
    [v_u_2.Blue] = 131,
    [v_u_2.Green] = 132,
    [v_u_2.Orange] = 133,
    [v_u_2.Purple] = 134,
    [v_u_2.Red] = 135
})
v_u_11.get_equipment_id_for_color = function(_, p13) --[[ Name: get_equipment_id_for_color ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_12 ]]
    v_u_3:is_enum_member(p13, v_u_2)
    return v_u_12:get(p13);
end;
v_u_11.playerblob_owns_any_tutorial_gear = function(_, p14) --[[ Name: playerblob_owns_any_tutorial_gear ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_4 ]]
    for _, v15 in v_u_12:key_itr() do
        if v_u_4:playerblob_get_owned_count_of_equipmentid(p14, v15) > 0 then
            return true;
        end;
    end;
    return false;
end;
v_u_11.playerblob_is_gear_tutorial_active = function(_, p16) --[[ Name: playerblob_is_gear_tutorial_active ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_11 ]]
    local v17
    if p16.MissionRank >= v_u_5.Novice then
        v17 = v_u_11:playerblob_owns_any_tutorial_gear(p16) == false
    else
        v17 = false
    end;
    return v17;
end;
return v_u_11;
