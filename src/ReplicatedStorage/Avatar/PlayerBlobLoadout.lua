-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_2 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_9 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_10 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_11 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_13 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_35 = {
    ["invalid_loadout_index"] = function(_) --[[ Name: invalid_loadout_index ]] --[[ Line: 20 ]]
        return -1;
    end,
    ["invalid_owned_id"] = function(_) --[[ Name: invalid_owned_id ]] --[[ Line: 21 ]]
        return -1;
    end,
    ["loadout_slot_level_max"] = function(_) --[[ Name: loadout_slot_level_max ]] --[[ Line: 23 ]]
        return 10;
    end,
    ["playerblob_get_loadout_slot_level"] = function(_, p14) --[[ Name: playerblob_get_loadout_slot_level ]] --[[ Line: 24 ]]
        return p14.LSLvl;
    end,
    ["get_default_loadout_index_max"] = function(_) --[[ Name: get_default_loadout_index_max ]] --[[ Line: 49 ]]
        return 5;
    end,
    ["get_loadout_index_range"] = function(_, p15) --[[ Name: get_loadout_index_range ]] --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1 ]]
        if p15 == nil then
            return v_u_3:errf("PlayerBlobLoadout:get_loadout_index_range playerblob nil");
        end;
        local v16 = v_u_1:new(1, 5)
        if typeof(p15.LSLvl) == "number" then
            v16:set_max(5 + p15.LSLvl)
        end;
        return v16;
    end,
    ["player_settings_get_loadout_name"] = function(_, p17, p18) --[[ Name: player_settings_get_loadout_name ]] --[[ Line: 61 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_13 ]]
        v_u_7:is_int(p18)
        local v19 = string.format("Loadout %d", p18)
        local v20 = p17:get_key(v_u_13.Key.LoadoutNames)
        if typeof(v20) == "table" and (typeof(v20[p18]) == "string" and #v20[p18] > 0) then
            v19 = v20[p18]
        end;
        return v19;
    end,
    ["max_loadout_name_length"] = function(_) --[[ Name: max_loadout_name_length ]] --[[ Line: 73 ]]
        return 16;
    end,
    ["get_index_to_loadouts_multidict"] = function(_, p21) --[[ Name: get_index_to_loadouts_multidict ]] --[[ Line: 91 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        local v22 = v_u_6:new()
        for v23 = 1, #p21.Loadouts do
            local l_Loadouts_0 = p21.Loadouts[v23]
            v22:push_back_to(l_Loadouts_0.LoadoutIndex, l_Loadouts_0)
        end;
        return v22;
    end,
    ["get_id_to_loadout_dict"] = function(_, p24) --[[ Name: get_id_to_loadout_dict ]] --[[ Line: 120 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        local v25 = v_u_5:new()
        for v26 = 1, #p24.Loadouts do
            local l_Loadouts_1 = p24.Loadouts[v26]
            v25:add(l_Loadouts_1.ID, l_Loadouts_1)
        end;
        return v25;
    end,
    ["id_to_loadout_dict_get_next_available_id"] = function(_, p27) --[[ Name: id_to_loadout_dict_get_next_available_id ]] --[[ Line: 129 ]]
        local v28 = 0
        while p27:contains(v28) == true do
            v28 = v28 + 1
        end;
        return v28;
    end,
    ["playerblob_write_id_to_loadout_dict"] = function(_, p29, p30) --[[ Name: playerblob_write_id_to_loadout_dict ]] --[[ Line: 140 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v31 = v_u_4:new()
        for _, v32 in p30:key_itr() do
            v31:push_back(v32)
        end;
        v31:sort(function(p33, p34) --[[ Line: 145 ]]
            return p34.ID - p33.ID;
        end)
        p29.Loadouts = v31:get_table()
    end
}
v_u_35.can_playerblob_upgrade_loadout_slot_level = function(_, p36) --[[ Name: can_playerblob_upgrade_loadout_slot_level ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_35 ]]
    return p36.LSLvl < v_u_35:loadout_slot_level_max();
end;
v_u_35.loadout_slot_level_to_price = function(_, p37) --[[ Name: loadout_slot_level_to_price ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_35, (copy 3): v_u_12 ]]
    v_u_7:is_int(p37)
    v_u_7:is_true(p37 >= 0)
    v_u_7:is_true(p37 <= v_u_35:loadout_slot_level_max())
    return p37 * 50, v_u_12.CurrencyType.Stars;
end;
v_u_35.playerblob_get_next_loadout_slot_level_price = function(_, p38) --[[ Name: playerblob_get_next_loadout_slot_level_price ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_35 ]]
    return v_u_35:loadout_slot_level_to_price(p38.LSLvl + 1);
end;
v_u_35.playerblob_do_increment_loadout_slot_level = function(_, p39) --[[ Name: playerblob_do_increment_loadout_slot_level ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_35 ]]
    local v40
    if v_u_35:can_playerblob_upgrade_loadout_slot_level(p39) then
        p39.LSLvl = p39.LSLvl + 1
        v40 = true
    else
        v40 = false
    end;
    return v40;
end;
v_u_35.write_playerblob_loadout_index_name_to_settings = function(_, p41, p42, p43, p44) --[[ Name: write_playerblob_loadout_index_name_to_settings ]] --[[ Line: 75 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_3, (copy 3): v_u_13 ]]
    if v_u_35:get_loadout_index_range(p41):contains_eq(p42) ~= true then
        return v_u_3:warnf("PlayerBlobLoadout:write_playerblob_loadout_index_name_to_settings loadout_index(%d) out of range", p42);
    end;
    if typeof(p43) ~= "string" then
        return v_u_3:warnf("PlayerBlobLoadout:write_playerblob_loadout_index_name_to_settings loadout_name(%s) not string", (tostring(p43)));
    end;
    if #p43 > v_u_35:max_loadout_name_length() then
        return v_u_3:warnf("PlayerBlobLoadout:write_playerblob_loadout_index_name_to_settings loadout_name(%s) too long", p43);
    end;
    local v45 = p44:get_key(v_u_13.Key.LoadoutNames)
    for v46 = 1, p42 do
        if v45[v46] == nil then
            v45[v46] = ""
        end;
    end;
    v45[p42] = p43
end;
v_u_35.get_index_ownedid_set = function(_, p47, p48) --[[ Name: get_index_ownedid_set ]] --[[ Line: 100 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_35 ]]
    local v49 = v_u_5:new()
    for _, v50 in v_u_35:get_index_to_loadouts_multidict(p47):list_of(p48):key_itr() do
        if v50.OwnedID ~= v_u_35:invalid_owned_id() then
            v49:add_set(v50.OwnedID)
        end;
    end;
    return v49;
end;
v_u_35.get_index_pet_slot_to_ownedpet_dict = function(_, p51, p52) --[[ Name: get_index_pet_slot_to_ownedpet_dict ]] --[[ Line: 110 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_35, (copy 3): v_u_10 ]]
    local v53 = v_u_5:new()
    for _, v54 in v_u_35:get_index_to_loadouts_multidict(p51):list_of(p52):key_itr() do
        if v54.PetOwnedID ~= v_u_35:invalid_owned_id() then
            v53:add(v54.PetSlot, v_u_10:playerblob_get_pet_ownedid_ownedpet(p51, v54.PetOwnedID))
        end;
    end;
    return v53;
end;
v_u_35.playerblob_validate_loadouts_table_and_convert_to_id_to_loadout_dict = function(_, p55, p56) --[[ Name: playerblob_validate_loadouts_table_and_convert_to_id_to_loadout_dict ]] --[[ Line: 151 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_35 ]]
    local v57 = v_u_5:new()
    for v58 = 1, #p56 do
        v57:add(p56[v58].ID, p56[v58])
    end;
    v_u_35:playerblob_validate_id_to_loadout_dict(p55, v57)
    return v57;
end;
v_u_35.playerblob_validate_id_to_loadout_dict = function(_, p59, p60) --[[ Name: playerblob_validate_id_to_loadout_dict ]] --[[ Line: 160 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_35, (copy 4): v_u_3, (copy 5): v_u_2, (copy 6): v_u_8, (copy 7): v_u_10 ]]
    local v61 = v_u_5:new()
    local v62 = v_u_5:new()
    local v63 = v_u_5:new()
    for _, v64 in p60:key_itr() do
        v_u_7:is_int(v64.ID)
        v_u_7:is_true(v63:contains(v64.ID) == false)
        v63:add_set(v64.ID)
        v_u_7:is_int(v64.OwnedID)
        v_u_7:is_int(v64.PetOwnedID)
        v_u_7:is_true(v64.OwnedID ~= v_u_35:invalid_owned_id() and true or v64.PetOwnedID ~= v_u_35:invalid_owned_id())
        v_u_7:is_int(v64.LoadoutIndex)
        local l_LoadoutIndex_0 = v64.LoadoutIndex
        if v_u_35:get_loadout_index_range(p59):contains_eq(l_LoadoutIndex_0) == true then
            if v61:contains(l_LoadoutIndex_0) ~= true then
                v61:add(l_LoadoutIndex_0, v_u_5:new())
                v62:add(l_LoadoutIndex_0, v_u_5:new())
            end;
            if v64.OwnedID == v_u_35:invalid_owned_id() then
                if v64.PetOwnedID ~= v_u_35:invalid_owned_id() then
                    v_u_7:is_true(v_u_10:playerblob_get_pet_ownedid_ownedpet(p59, v64.PetOwnedID) ~= nil)
                    local v65 = v62:get(l_LoadoutIndex_0)
                    local l_PetSlot_0 = v64.PetSlot
                    v_u_7:is_true(v_u_10:get_pet_slot_set():contains(l_PetSlot_0))
                    v_u_7:is_false(v65:contains(l_PetSlot_0))
                    v65:add_set(l_PetSlot_0)
                end;
            else
                local v66 = v61:get(l_LoadoutIndex_0)
                local v67 = v_u_2:playerblob_ownedid_to_equipmentid(p59, v64.OwnedID)
                v_u_7:is_true(v67 ~= nil)
                local v68 = v_u_8:singleton():get_equipment_for_id(v67)
                v_u_7:is_true(v68 ~= nil)
                local v69 = v68:get_avatar_slot()
                v_u_7:is_false(v66:contains(v69))
                v66:add_set(v69)
            end;
        else
            v_u_3:warnf("PlayerBlobLoadout:playerblob_validate_id_to_loadout_dict itr_loadout_index(%d) out of range", l_LoadoutIndex_0)
        end;
    end;
end;
v_u_35.equip_loadout_index = function(_, p70, p71) --[[ Name: equip_loadout_index ]] --[[ Line: 206 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_2, (copy 3): v_u_10, (copy 4): v_u_35, (copy 5): v_u_8 ]]
    for _, v72 in v_u_9:slot_itr() do
        v_u_2:playerblob_unequip_slot(p70, v72)
    end;
    for v73, _ in v_u_10:get_pet_slot_set():key_itr() do
        v_u_10:playerblob_remove_pet_slotid(p70, v73)
    end;
    for _, v74 in v_u_35:get_index_to_loadouts_multidict(p70):list_of(p71):key_itr() do
        if v74.OwnedID == v_u_35:invalid_owned_id() then
            if v74.PetOwnedID ~= v_u_35:invalid_owned_id() then
                v_u_10:playerblob_equip_pet_ownedid(p70, v74.PetOwnedID, v74.PetSlot)
            end;
        else
            local l_OwnedID_0 = v74.OwnedID
            local v75 = v_u_2:playerblob_ownedid_to_equipmentid(p70, l_OwnedID_0)
            if v75 ~= nil then
                v_u_2:playerblob_equip_ownedid(p70, l_OwnedID_0)
                v_u_2:set_visible_for_slot(p70, v_u_8:singleton():get_equipment_for_id(v75):get_avatar_slot(), v74.Visible)
            end;
        end;
    end;
end;
v_u_35.update_loadout_index_to_equipped = function(_, p76, p_u_77) --[[ Name: update_loadout_index_to_equipped ]] --[[ Line: 232 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_5, (copy 3): v_u_2, (copy 4): v_u_10 ]]
    local v78 = v_u_35:get_id_to_loadout_dict(p76)
    v_u_5:remove_if(v78, function(p79) --[[ Line: 235 ]]
        --[[ Upvalues: (copy 1): p_u_77 ]]
        return p79.LoadoutIndex == p_u_77;
    end)
    for v80 = 1, #p76.Equipped do
        local v81 = v_u_35:id_to_loadout_dict_get_next_available_id(v78)
        local l_OwnedID_1 = p76.Equipped[v80].OwnedID
        local l_Visible_0 = p76.Equipped[v80].Visible
        if v_u_2:playerblob_ownedid_to_equipmentid(p76, l_OwnedID_1) ~= nil then
            v78:add(v81, {
                ["ID"] = v81,
                ["OwnedID"] = l_OwnedID_1,
                ["LoadoutIndex"] = p_u_77,
                ["Visible"] = l_Visible_0,
                ["PetOwnedID"] = v_u_35:invalid_owned_id(),
                ["PetSlot"] = v_u_10:get_invalid_pet_slot()
            })
        end;
    end;
    for v82 = 1, #p76.EquippedPets do
        local v83 = v_u_35:id_to_loadout_dict_get_next_available_id(v78)
        v78:add(v83, {
            ["ID"] = v83,
            ["OwnedID"] = v_u_35:invalid_owned_id(),
            ["LoadoutIndex"] = p_u_77,
            ["Visible"] = true,
            ["PetOwnedID"] = p76.EquippedPets[v82].OwnedID,
            ["PetSlot"] = p76.EquippedPets[v82].Slot
        })
    end;
    v_u_35:playerblob_validate_id_to_loadout_dict(p76, v78)
    v_u_35:playerblob_write_id_to_loadout_dict(p76, v78)
end;
v_u_35.remove_ownedid_from_loadouts = function(_, p84, p_u_85) --[[ Name: remove_ownedid_from_loadouts ]] --[[ Line: 274 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_5 ]]
    local v86 = v_u_35:get_id_to_loadout_dict(p84)
    v_u_5:remove_if(v86, function(p87) --[[ Line: 276 ]]
        --[[ Upvalues: (ref 1): v_u_35, (copy 2): p_u_85 ]]
        local v88
        if p87.OwnedID == v_u_35:invalid_owned_id() then
            v88 = false
        else
            v88 = p87.OwnedID == p_u_85
        end;
        return v88;
    end)
    v_u_35:playerblob_write_id_to_loadout_dict(p84, v86)
end;
v_u_35.remove_pet_ownedid_from_loadouts = function(_, p89, p_u_90) --[[ Name: remove_pet_ownedid_from_loadouts ]] --[[ Line: 282 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_5 ]]
    local v91 = v_u_35:get_id_to_loadout_dict(p89)
    v_u_5:remove_if(v91, function(p92) --[[ Line: 284 ]]
        --[[ Upvalues: (ref 1): v_u_35, (copy 2): p_u_90 ]]
        local v93
        if p92.PetOwnedID == v_u_35:invalid_owned_id() then
            v93 = false
        else
            v93 = p92.PetOwnedID == p_u_90
        end;
        return v93;
    end)
    v_u_35:playerblob_write_id_to_loadout_dict(p89, v91)
end;
v_u_35.playerblob_validate_with_dayid_weekid = function(_, p_u_94, _, _, _) --[[ Name: playerblob_validate_with_dayid_weekid ]] --[[ Line: 290 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_35, (copy 3): v_u_10, (copy 4): v_u_2 ]]
    local v95 = v_u_4:new(p_u_94.Loadouts)
    v_u_4:for_each(v95, function(p96) --[[ Line: 292 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_10 ]]
        if p96.PetOwnedID == nil then
            p96.PetOwnedID = v_u_35:invalid_owned_id()
        end;
        if p96.PetSlot == nil then
            p96.PetSlot = v_u_10:get_invalid_pet_slot()
        end;
    end)
    v_u_4:remove_if(v95, function(p97) --[[ Line: 300 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_2, (copy 3): p_u_94, (ref 4): v_u_10 ]]
        if p97.OwnedID == v_u_35:invalid_owned_id() then
            if p97.PetOwnedID == v_u_35:invalid_owned_id() then
                return false;
            else
                return v_u_10:playerblob_get_pet_ownedid_ownedpet(p_u_94, p97.PetOwnedID) == nil;
            end;
        else
            return v_u_2:playerblob_ownedid_to_equipmentid(p_u_94, p97.OwnedID) == nil;
        end;
    end)
end;
v_u_35.loadout_get_statsdict = function(_, p98, p99, p100, p101) --[[ Name: loadout_get_statsdict ]] --[[ Line: 311 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_11, (copy 3): v_u_2, (copy 4): v_u_10 ]]
    local v102 = v_u_35:get_index_to_loadouts_multidict(p98):list_of(p99)
    local v103 = v_u_11:statsdict_base()
    for _, v104 in v102:key_itr() do
        if v104.OwnedID == v_u_35:invalid_owned_id() then
            if v104.PetOwnedID ~= v_u_35:invalid_owned_id() then
                v_u_10:playerblob_apply_pet_ownedid_statsdict(p98, v104.PetOwnedID, v103)
            end;
        else
            v_u_2:playerblob_apply_ownedid_statsdict(p98, v104.OwnedID, v103)
        end;
    end;
    v_u_11:statsdict_apply_statmodifierobj(v103, v_u_2:get_playerblob_day_week_modifier_statsdict(p98, p100, p101))
    return v103, v_u_11:statsdict_get_ranked_colors(v103);
end;
v_u_35.loadout_get_gear_power = function(_, p105, p106, p107, p108, p109) --[[ Name: loadout_get_gear_power ]] --[[ Line: 330 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_11, (copy 3): v_u_2, (copy 4): v_u_10 ]]
    local v110 = v_u_35:get_index_to_loadouts_multidict(p105):list_of(p106)
    v_u_11:statsdict_base()
    local v111, v112 = v_u_35:loadout_get_statsdict(p105, p106, p107, p108)
    if p109 == nil then
        p109 = v112
    end;
    local v113 = 0
    for _, v114 in v110:key_itr() do
        if v114.OwnedID == v_u_35:invalid_owned_id() then
            if v114.PetOwnedID ~= v_u_35:invalid_owned_id() then
                v113 = v113 + v_u_10:playerblob_get_pet_ownedid_gearpower_for_ranked_stats_list(p105, v114.PetOwnedID, p109)
            end;
        else
            v113 = v113 + v_u_2:playerblob_get_ownedid_gearpower_for_ranked_stats_list(p105, v114.OwnedID, p109)
        end;
    end;
    return v113, p109, v111;
end;
v_u_35.playerblob_loadoutid_to_statsdict = function(_, p115, p116, p117) --[[ Name: playerblob_loadoutid_to_statsdict ]] --[[ Line: 355 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_35, (copy 3): v_u_2 ]]
    local v118 = v_u_5:new()
    v118:add(v_u_35:invalid_loadout_index(), v_u_2:get_playerblob_statsdict(p115, p116, p117))
    for v119, v120 in v_u_35:get_index_to_loadouts_multidict(p115):key_itr() do
        if v120:count() > 0 then
            v118:add(v119, v_u_35:loadout_get_statsdict(p115, v119, p116, p117))
        end;
    end;
    return v118;
end;
v_u_35.loadoutid_to_statsdict_get_top_loadoutid = function(_, p121, p122) --[[ Name: loadoutid_to_statsdict_get_top_loadoutid ]] --[[ Line: 373 ]]
    --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_2 ]]
    local v123 = v_u_35:invalid_loadout_index()
    local v124 = v_u_2:statsdict_get_gear_power(p121:get(v_u_35:invalid_loadout_index()), true, p122)
    for v125, v126 in p121:key_itr() do
        local v127 = v_u_2:statsdict_get_gear_power(v126, true, p122)
        if v124 < v127 then
            v123 = v125
            v124 = v127
        end;
    end;
    return v123, v124;
end;
return v_u_35;
