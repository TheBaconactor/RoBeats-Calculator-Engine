-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.GearSlotIncreaseUtil)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
v14:require_shared(function() --[[ Line: 17 ]]
    --[[ Upvalues: (ref 1): v_u_15 ]]
    v_u_15 = require(game.ReplicatedStorage.Pets.PetUtils)
end)
local v_u_16 = nil
v14:require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_16 ]]
    v_u_16 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
local v_u_50 = {
    ["get_override_appearance_default_id"] = function(_) --[[ Name: get_override_appearance_default_id ]] --[[ Line: 63 ]]
        return 0;
    end,
    ["ownedobj_get_override_appearance_id"] = function(_, p17) --[[ Name: ownedobj_get_override_appearance_id ]] --[[ Line: 65 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        local l_OAID_0 = p17.OAID
        if l_OAID_0 == nil then
            return 0;
        elseif l_OAID_0 == 0 then
            return l_OAID_0;
        else
            return v_u_2:singleton():get_equipment_for_id(l_OAID_0) == nil and 0 or l_OAID_0;
        end;
    end,
    ["playerblob_ownedid_to_equipmentid"] = function(_, p18, p19) --[[ Name: playerblob_ownedid_to_equipmentid ]] --[[ Line: 107 ]]
        for v20 = 1, #p18.OwnedEquipment do
            local l_OwnedEquipment_0 = p18.OwnedEquipment[v20]
            if l_OwnedEquipment_0.OwnedID == p19 then
                return l_OwnedEquipment_0.EquipmentID, l_OwnedEquipment_0;
            end;
        end;
        return nil, nil;
    end,
    ["playerblob_ownedid_to_ownedobj_dict"] = function(_, p21) --[[ Name: playerblob_ownedid_to_ownedobj_dict ]] --[[ Line: 117 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v22 = v_u_4:new()
        for v23 = 1, #p21.OwnedEquipment do
            local l_OwnedEquipment_1 = p21.OwnedEquipment[v23]
            if typeof(l_OwnedEquipment_1.OwnedID) == "number" then
                v22:add(l_OwnedEquipment_1.OwnedID, l_OwnedEquipment_1)
            end;
        end;
        return v22;
    end,
    ["playerblob_get_first_ownedid_of_equipmentid"] = function(_, p24, p25) --[[ Name: playerblob_get_first_ownedid_of_equipmentid ]] --[[ Line: 138 ]]
        for v26 = 1, #p24.OwnedEquipment do
            local l_OwnedEquipment_2 = p24.OwnedEquipment[v26]
            if l_OwnedEquipment_2.EquipmentID == p25 then
                return l_OwnedEquipment_2.OwnedID;
            end;
        end;
        return nil;
    end,
    ["playerblob_get_owned_count_of_equipmentid"] = function(_, p27, p28) --[[ Name: playerblob_get_owned_count_of_equipmentid ]] --[[ Line: 148 ]]
        local v29 = 0
        for v30 = 1, #p27.OwnedEquipment do
            if p27.OwnedEquipment[v30].EquipmentID == p28 then
                v29 = v29 + 1
            end;
        end;
        return v29;
    end,
    ["get_playerblob_day_week_modifier_statsdict"] = function(_, p31, _, p32) --[[ Name: get_playerblob_day_week_modifier_statsdict ]] --[[ Line: 211 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        local v33 = v_u_5:statsdict_base()
        if p32 ~= nil and p32 <= p31.TeamBuffWeekID then
            v_u_5:statsdict_apply_statmodifierobj(v33, (v_u_5:playerblob_get_team_buff_statmodifierobj(p31)))
        end;
        return v33;
    end,
    ["get_owned_equipment_list"] = function(_, p34) --[[ Name: get_owned_equipment_list ]] --[[ Line: 286 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        local v35 = v_u_3:new()
        for v36 = 1, #p34.OwnedEquipment do
            v35:push_back(p34.OwnedEquipment[v36])
        end;
        return v35;
    end,
    ["ownedid_is_equipped"] = function(_, p37, p38) --[[ Name: ownedid_is_equipped ]] --[[ Line: 294 ]]
        for v39 = 1, #p37.Equipped do
            if p37.Equipped[v39].OwnedID == p38 then
                return true;
            end;
        end;
        return false;
    end,
    ["set_equippedlist"] = function(_, p40, p41) --[[ Name: set_equippedlist ]] --[[ Line: 305 ]]
        p40.Equipped = p41
    end,
    ["cmp_equipdicts"] = function(_, p42, p43) --[[ Name: cmp_equipdicts ]] --[[ Line: 590 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        for _, v44 in v_u_1:slot_itr() do
            local v45 = p42[v44]
            local v46 = p43[v44]
            if v45.OwnedID ~= v46.OwnedID or (v45.EquipmentName ~= v46.EquipmentName or v45.Visible ~= v46.Visible) then
                return false;
            end;
        end;
        return true;
    end,
    ["get_equipped_ownedid_set"] = function(_, p47) --[[ Name: get_equipped_ownedid_set ]] --[[ Line: 668 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v48 = v_u_4:new()
        for v49 = 1, #p47.Equipped do
            v48:add(p47.Equipped[v49].OwnedID, true)
        end;
        return v48;
    end
}
v_u_50.playerblob_slot_to_equippedobj_dict = function(_, p51) --[[ Name: playerblob_slot_to_equippedobj_dict ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_50, (copy 3): v_u_2 ]]
    local v52 = v_u_4:new()
    for v53 = 1, #p51.Equipped do
        local l_Equipped_0 = p51.Equipped[v53]
        local v54 = v_u_50:playerblob_ownedid_to_equipmentid(p51, l_Equipped_0.OwnedID)
        if v54 ~= nil then
            local v55 = v_u_2:singleton():get_equipment_for_id(v54)
            if v55 then
                v52:add(v55:get_avatar_slot(), l_Equipped_0)
            end;
        end;
    end;
    return v52;
end;
v_u_50.playerblob_get_equipped_info = function(_, p56) --[[ Name: playerblob_get_equipped_info ]] --[[ Line: 45 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local v57 = {}
    for v58 = 1, #p56.Equipped do
        local l_Equipped_1 = p56.Equipped[v58]
        local v59, v60 = v_u_50:playerblob_ownedid_to_equipmentid(p56, l_Equipped_1.OwnedID)
        if v59 ~= nil then
            v57[#v57 + 1] = {
                ["EquipmentID"] = v59,
                ["Visible"] = l_Equipped_1.Visible,
                ["OAID"] = v_u_50:ownedobj_get_override_appearance_id(v60)
            }
        end;
    end;
    return v57;
end;
v_u_50.playerblob_equip_ownedid = function(_, p61, p62) --[[ Name: playerblob_equip_ownedid ]] --[[ Line: 76 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_6, (copy 3): v_u_2, (copy 4): v_u_1 ]]
    local v63 = v_u_50:playerblob_slot_to_equippedobj_dict(p61)
    local v64 = v_u_50:playerblob_ownedid_to_equipmentid(p61, p62)
    if v64 == nil then
        v_u_6:errf("PlayerBlobAvatar:playerblob_equip_ownedid does not own(%d)", p62)
    end;
    local v65 = v_u_2:singleton():get_equipment_for_id(v64)
    if v65 then
        v63:add(v65:get_avatar_slot(), {
            ["OwnedID"] = p62,
            ["Visible"] = true
        })
    end;
    p61.Equipped = {}
    for _, v66 in v_u_1:slot_itr() do
        if v63:contains(v66) then
            p61.Equipped[#p61.Equipped + 1] = v63:get(v66)
        end;
    end;
end;
v_u_50.playerblob_unequip_slot = function(_, p67, p68) --[[ Name: playerblob_unequip_slot ]] --[[ Line: 100 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local v69, v70 = v_u_50:get_equippedobj_for_slot(p67, p68)
    if v69 ~= nil then
        table.remove(p67.Equipped, v70)
    end;
end;
v_u_50.playerblob_ownedid_to_equipmentid_dict = function(_, p71) --[[ Name: playerblob_ownedid_to_equipmentid_dict ]] --[[ Line: 128 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_4 ]]
    local v72 = v_u_50:playerblob_ownedid_to_ownedobj_dict(p71)
    local v73 = v_u_4:new()
    for v74, v75 in v72:key_itr() do
        v73:add(v74, v75.EquipmentID)
    end;
    return v73;
end;
v_u_50.playerblob_alloc_ownedid = function(_, p76) --[[ Name: playerblob_alloc_ownedid ]] --[[ Line: 159 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local v77 = 1
    while v_u_50:playerblob_ownedid_to_equipmentid(p76, v77) ~= nil do
        v77 = v77 + 1
    end;
    return v77;
end;
v_u_50.playerblob_grant_equipmentid = function(_, p78, p79) --[[ Name: playerblob_grant_equipmentid ]] --[[ Line: 170 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_6 ]]
    if v_u_50:playerblob_can_add_more_gear(p78) ~= true then
        v_u_6:warnf("PlayerBlobAvatar:playerblob_grant_equipmentid playerblob_can_add_more_gear false")
        return -1;
    end;
    local v80 = v_u_50:playerblob_alloc_ownedid(p78)
    p78.OwnedEquipment[#p78.OwnedEquipment + 1] = {
        ["EquipmentID"] = p79,
        ["OwnedID"] = v80,
        ["OAID"] = v_u_50:get_override_appearance_default_id(),
        ["BoostUsedID"] = 0,
        ["BoostUsedCount"] = 0,
        ["Upgrades"] = {}
    }
    return v80;
end;
v_u_50.playerblob_apply_ownedid_statsdict = function(_, p81, p82, p83) --[[ Name: playerblob_apply_ownedid_statsdict ]] --[[ Line: 188 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_8 ]]
    local v84 = v_u_50:playerblob_ownedid_to_equipmentid(p81, p82)
    local v85 = v84 ~= nil and v_u_2:singleton():get_equipment_for_id(v84)
    if v85 then
        v_u_5:statsdict_apply_statmodifierobj(p83, v85:get_gear_statmodifierobj())
    end;
    local _, v86 = v_u_50:playerblob_ownedid_to_equipmentid(p81, p82)
    if v86 ~= nil then
        local l_Upgrades_0 = v86.Upgrades
        for v87 = 1, #l_Upgrades_0 do
            local v88 = v_u_8:singleton():get_equipment_upgrade_for_id(l_Upgrades_0[v87].UpgradeID)
            if v88 ~= nil then
                v_u_5:statsdict_apply_statmodifierobj(p83, v88:get_gear_statmodifierobj())
            end;
        end;
    end;
end;
v_u_50.get_playerblob_statsdict = function(_, p89, p90, p91) --[[ Name: get_playerblob_statsdict ]] --[[ Line: 220 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_50, (copy 3): v_u_9, (ref 4): v_u_15, (copy 5): v_u_6 ]]
    local v92 = v_u_5:statsdict_base()
    for v93 = 1, #p89.Equipped do
        v_u_50:playerblob_apply_ownedid_statsdict(p89, p89.Equipped[v93].OwnedID, v92)
    end;
    v_u_5:statsdict_apply_statmodifierobj(v92, v_u_50:get_playerblob_day_week_modifier_statsdict(p89, p90, p91))
    if v_u_9.DebugMinisActive == true then
        if v_u_15 then
            for _, v94 in v_u_15:playerblob_get_slot_to_owned_pet_dict(p89):key_itr() do
                v_u_15:playerblob_apply_pet_ownedid_statsdict(p89, v_u_15:ownedpet_get_ownedid(v94), v92)
            end;
            return v92;
        end;
        v_u_6:warnf("PlayerBlobAvatar:get_playerblob_statsdict PetUtils nil")
    end;
    return v92;
end;
v_u_50.get_equippedobj_for_slot = function(_, p95, p96) --[[ Name: get_equippedobj_for_slot ]] --[[ Line: 241 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_2 ]]
    for v97 = 1, #p95.Equipped do
        local l_Equipped_2 = p95.Equipped[v97]
        local l_OwnedID_0 = l_Equipped_2.OwnedID
        local v98, _ = v_u_50:playerblob_ownedid_to_equipmentid(p95, l_OwnedID_0)
        if v98 ~= nil then
            local v99 = v_u_2:singleton():get_equipment_for_id(v98)
            if v99 and p96 == v99:get_avatar_slot() then
                return l_Equipped_2, v97, l_OwnedID_0;
            end;
        end;
    end;
    return nil;
end;
v_u_50.get_equipmentdata_for_slot = function(_, p100, p101) --[[ Name: get_equipmentdata_for_slot ]] --[[ Line: 256 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_2, (copy 3): v_u_6 ]]
    local v102 = v_u_50:get_equippedobj_for_slot(p100, p101)
    if v102 == nil then
        return nil, nil;
    end;
    local v103, v104 = v_u_50:playerblob_ownedid_to_equipmentid(p100, v102.OwnedID)
    if v103 == nil then
        return nil, nil;
    end;
    local v105 = v_u_2:singleton():get_equipment_for_id(v103)
    if v105 == nil then
        return nil, nil;
    end;
    if p101 ~= v105:get_avatar_slot() then
        v_u_6:errf("PlayerBlobAvatar:get_equipmentdata_for_slot() slot_key does not match itr_equipmentdata:get_avatar_slot()")
    end;
    return v105, v104;
end;
v_u_50.get_visible_for_slot = function(_, p106, p107) --[[ Name: get_visible_for_slot ]] --[[ Line: 274 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local v108 = v_u_50:get_equippedobj_for_slot(p106, p107)
    if v108 == nil then
        return nil;
    else
        return v108.Visible;
    end;
end;
v_u_50.set_visible_for_slot = function(_, p109, p110, p111) --[[ Name: set_visible_for_slot ]] --[[ Line: 280 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local v112 = v_u_50:get_equippedobj_for_slot(p109, p110)
    if v112 ~= nil then
        v112.Visible = p111
    end;
end;
v_u_50.equip_debug_to_playerblob = function(_, p_u_113) --[[ Name: equip_debug_to_playerblob ]] --[[ Line: 309 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local function _(p114) --[[ Name: playerblob_grant_if_owned_count_is_zero ]] --[[ Line: 310 ]]
        --[[ Upvalues: (ref 1): v_u_50, (copy 2): p_u_113 ]]
        if v_u_50:playerblob_get_owned_count_of_equipmentid(p_u_113, p114) == 0 then
            v_u_50:playerblob_grant_equipmentid(p_u_113, p114)
        end;
    end;
    for v115 = 30, 67 do
        if v_u_50:playerblob_get_owned_count_of_equipmentid(p_u_113, v115) == 0 then
            v_u_50:playerblob_grant_equipmentid(p_u_113, v115)
        end;
    end;
    local function _(p116) --[[ Name: playerblob_equip_first_of_equipmentid ]] --[[ Line: 320 ]]
        --[[ Upvalues: (ref 1): v_u_50, (copy 2): p_u_113 ]]
        v_u_50:playerblob_equip_ownedid(p_u_113, (v_u_50:playerblob_get_first_ownedid_of_equipmentid(p_u_113, p116)))
    end;
    v_u_50:playerblob_validate_equippedlist(p_u_113, p_u_113.Equipped)
end;
v_u_50.playerblob_validate_equippedlist = function(_, p117, p118) --[[ Name: playerblob_validate_equippedlist ]] --[[ Line: 335 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    if typeof(p118) ~= "table" then
        return false;
    end;
    for v119 = 1, #p118 do
        local v120 = p118[v119]
        if v120.OwnedID == nil or v120.Visible == nil then
            return false;
        end;
        local v121, v122 = v_u_50:playerblob_ownedid_to_equipmentid(p117, v120.OwnedID)
        if v121 == nil or v122 == nil then
            return false;
        end;
        if v122.EquipmentID == nil or (v122.OwnedID == nil or v122.Upgrades == nil) then
            return false;
        end;
    end;
    return true;
end;
v_u_50.add_debug_gear_upgrades_to_playerblob = function(_, p123) --[[ Name: add_debug_gear_upgrades_to_playerblob ]] --[[ Line: 347 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_6, (copy 3): v_u_50, (copy 4): v_u_7 ]]
    if v_u_9.DebugGearSetUpgrades ~= true then
        v_u_6:errf("add_debug_gear_upgrades_to_playerblob invalid")
    end;
    local v124 = v_u_50:get_owned_equipment_list(p123)
    for v125 = 1, v124:count() do
        local v126 = v124:get(v125)
        local l_OwnedID_1 = v126.OwnedID
        v126.Upgrades = {}
        for _ = 1, v_u_7:rand_rangei(0, 6) do
            v_u_50:add_upgrade_to_ownedid(p123, 1, l_OwnedID_1)
        end;
    end;
end;
v_u_50.get_ownedid_upgrade_count = function(_, p127, p128) --[[ Name: get_ownedid_upgrade_count ]] --[[ Line: 364 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local _, v129 = v_u_50:playerblob_ownedid_to_equipmentid(p127, p128)
    return v129.Upgrades == nil and 0 or #v129.Upgrades;
end;
local function f_ownedobj_sort_revalidate_indexes(p130) --[[ Name: ownedobj_sort_revalidate_indexes ]] --[[ Line: 372 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v131 = v_u_3:new()
    for v132 = 1, #p130.Upgrades do
        v131:push_back(p130.Upgrades[v132])
    end;
    v131:sort(function(p133, p134) --[[ Line: 378 ]]
        return p134.Index - p133.Index;
    end)
    for v135 = 1, v131:count() do
        v131:get(v135).Index = v135 - 1
    end;
    p130.Upgrades = v131._table
end;
local function f_ownedobj_get_max_index(p136) --[[ Name: ownedobj_get_max_index ]] --[[ Line: 387 ]]
    if #p136.Upgrades <= 0 then
        return -1;
    end;
    local l_Index_0 = p136.Upgrades[1].Index
    for v137 = 1, #p136.Upgrades do
        l_Index_0 = math.max(l_Index_0, p136.Upgrades[v137].Index)
    end;
    return l_Index_0;
end;
v_u_50.add_upgrade_to_ownedid = function(_, p138, p139, p140) --[[ Name: add_upgrade_to_ownedid ]] --[[ Line: 400 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_8, (copy 3): f_ownedobj_sort_revalidate_indexes, (copy 4): f_ownedobj_get_max_index ]]
    local _, v141 = v_u_50:playerblob_ownedid_to_equipmentid(p138, p140)
    if v141.Upgrades ~= nil then
        if v_u_8:singleton():get_equipment_upgrade_for_id(p139) ~= nil then
            f_ownedobj_sort_revalidate_indexes(v141)
            local v142 = f_ownedobj_get_max_index(v141) + 1
            v141.Upgrades[#v141.Upgrades + 1] = {
                ["UpgradeID"] = p139,
                ["Index"] = v142
            }
            return true;
        end;
    end;
end;
v_u_50.remove_last_upgrade_on_ownedid = function(_, p143, p144) --[[ Name: remove_last_upgrade_on_ownedid ]] --[[ Line: 415 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): f_ownedobj_get_max_index, (copy 3): v_u_3, (copy 4): f_ownedobj_sort_revalidate_indexes ]]
    local _, v145 = v_u_50:playerblob_ownedid_to_equipmentid(p143, p144)
    if v145.Upgrades ~= nil then
        if #v145.Upgrades > 0 then
            local v146 = f_ownedobj_get_max_index(v145)
            local v147 = v_u_3:new()
            for v148 = 1, #v145.Upgrades do
                local l_Upgrades_1 = v145.Upgrades[v148]
                if l_Upgrades_1.Index ~= v146 then
                    v147:push_back(l_Upgrades_1)
                end;
            end;
            v145.Upgrades = v147._table
            f_ownedobj_sort_revalidate_indexes(v145)
        end;
    end;
end;
v_u_50.get_upgrade_on_ownedid_for_index = function(_, p149, p150, p151) --[[ Name: get_upgrade_on_ownedid_for_index ]] --[[ Line: 432 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local _, v152 = v_u_50:playerblob_ownedid_to_equipmentid(p149, p150)
    if v152 == nil then
        return nil;
    end;
    local v153 = nil
    local v154 = nil
    for v155 = 1, #v152.Upgrades do
        local l_Upgrades_2 = v152.Upgrades[v155]
        if l_Upgrades_2.Index == p151 then
            v154 = v155
            v153 = l_Upgrades_2
            break;
        end;
    end;
    return v153, v154, v152;
end;
v_u_50.remove_upgrade_on_ownedid_for_index = function(_, p156, p157, p158) --[[ Name: remove_upgrade_on_ownedid_for_index ]] --[[ Line: 447 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): f_ownedobj_sort_revalidate_indexes ]]
    local v159, v160, v161 = v_u_50:get_upgrade_on_ownedid_for_index(p156, p157, p158)
    if v159 ~= nil then
        table.remove(v161.Upgrades, v160)
        f_ownedobj_sort_revalidate_indexes(v161)
    end;
end;
v_u_50.get_pity_count_for_ownedid_upgradeid = function(_, p162, p163, p164) --[[ Name: get_pity_count_for_ownedid_upgradeid ]] --[[ Line: 454 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local _, v165 = v_u_50:playerblob_ownedid_to_equipmentid(p162, p163)
    if v165 == nil then
        return 0, 0, 0;
    elseif v165.BoostUsedID == p164 then
        return v165.BoostUsedCount, v165.BoostUsedID, v165.BoostUsedCount;
    else
        return 0, v165.BoostUsedID, v165.BoostUsedCount;
    end;
end;
v_u_50.update_pity_count_for_failed_boost_count_ownedid_upgradeid = function(_, p166, p167, p168, p169) --[[ Name: update_pity_count_for_failed_boost_count_ownedid_upgradeid ]] --[[ Line: 461 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local _, v170 = v_u_50:playerblob_ownedid_to_equipmentid(p166, p168)
    if v170 == nil then
        return;
    elseif v170.BoostUsedID == p169 then
        v170.BoostUsedCount = v170.BoostUsedCount + p167
    else
        v170.BoostUsedID = p169
        v170.BoostUsedCount = p167
    end;
end;
v_u_50.update_pity_count_for_success_ownedid = function(_, p171, p172) --[[ Name: update_pity_count_for_success_ownedid ]] --[[ Line: 472 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    local _, v173 = v_u_50:playerblob_ownedid_to_equipmentid(p171, p172)
    if v173 ~= nil then
        v173.BoostUsedID = 0
        v173.BoostUsedCount = 0
    end;
end;
v_u_50.playerblob_delete_ownedid = function(_, p174, p175) --[[ Name: playerblob_delete_ownedid ]] --[[ Line: 479 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_6 ]]
    local v176 = false
    for v177 = #p174.OwnedEquipment, 1, -1 do
        if p174.OwnedEquipment[v177].OwnedID == p175 then
            table.remove(p174.OwnedEquipment, v177)
            v176 = true
        end;
    end;
    if v_u_50:playerblob_validate_equippedlist(p174, p174.Equipped) == false then
        v_u_6:errf("PlayerBlobAvatar:playerblob_delete_ownedid post validate failed")
    end;
    return v176;
end;
v_u_50.playerblob_can_add_more_gear = function(_, p178) --[[ Name: playerblob_can_add_more_gear ]] --[[ Line: 494 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_13 ]]
    return v_u_50:get_owned_equipment_list(p178):count() < v_u_13:playerblob_get_max_gear_slot_count(p178);
end;
local v_u_179 = v_u_4:new():add_set_from_table_list({
    v_u_5.Type.PerfectPoints,
    v_u_5.Type.ComboMultiplier,
    v_u_5.Type.FeverFillRate,
    v_u_5.Type.FeverMultiplier,
    v_u_5.Type.FeverTime
})
v_u_50.get_base_gearpower_counted_stat_types = function(_) --[[ Name: get_base_gearpower_counted_stat_types ]] --[[ Line: 506 ]]
    --[[ Upvalues: (copy 1): v_u_179 ]]
    return v_u_179;
end;
v_u_50.statsdict_get_gear_power = function(_, p180, p181, p182) --[[ Name: statsdict_get_gear_power ]] --[[ Line: 508 ]]
    --[[ Upvalues: (copy 1): v_u_179, (copy 2): v_u_5 ]]
    local v183 = 0
    if p181 then
        for v184, _ in v_u_179:key_itr() do
            v183 = v183 + p180[v184] * 5
        end;
    end;
    if p182 then
        if p182:count() == 1 then
            return v183 + p180[v_u_5:elemental_color_to_gearstats_type(p182:get(1))] * 6;
        end;
        v183 = v183 + p180[v_u_5:elemental_color_to_gearstats_type(p182:get(1))] * 4 + p180[v_u_5:elemental_color_to_gearstats_type(p182:get(2))] * 2
    end;
    return v183;
end;
v_u_50.get_playerblob_base_gearpower_v2 = function(_, p185, p186, p187) --[[ Name: get_playerblob_base_gearpower_v2 ]] --[[ Line: 534 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    return v_u_50:statsdict_get_gear_power(v_u_50:get_playerblob_statsdict(p185, p186, p187), true, nil);
end;
v_u_50.get_playerblob_songkey_color_gearpower_v2 = function(_, p188, p189, p190, p191) --[[ Name: get_playerblob_songkey_color_gearpower_v2 ]] --[[ Line: 538 ]]
    --[[ Upvalues: (copy 1): v_u_50, (copy 2): v_u_10 ]]
    return v_u_50:get_playerblob_color_list_gearpower(p188, v_u_10:songkey_get_color_list(p189), p190, p191);
end;
v_u_50.get_playerblob_color_list_gearpower = function(_, p192, p193, p194, p195) --[[ Name: get_playerblob_color_list_gearpower ]] --[[ Line: 542 ]]
    --[[ Upvalues: (copy 1): v_u_50 ]]
    return v_u_50:statsdict_get_gear_power(v_u_50:get_playerblob_statsdict(p192, p194, p195), false, p193);
end;
v_u_50.playerblob_get_ownedid_base_gearpower = function(_, p196, p197) --[[ Name: playerblob_get_ownedid_base_gearpower ]] --[[ Line: 546 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_50 ]]
    local v198 = v_u_5:statsdict_base()
    v_u_50:playerblob_apply_ownedid_statsdict(p196, p197, v198)
    return v_u_50:statsdict_get_gear_power(v198, true, nil);
end;
v_u_50.playerblob_get_ownedid_gearpower = function(_, p199, p200) --[[ Name: playerblob_get_ownedid_gearpower ]] --[[ Line: 552 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_50 ]]
    local v201 = v_u_5:statsdict_base()
    v_u_50:playerblob_apply_ownedid_statsdict(p199, p200, v201)
    return v_u_50:playerblob_get_ownedid_gearpower_for_ranked_stats_list(p199, p200, (v_u_5:statsdict_get_ranked_colors(v201)));
end;
v_u_50.playerblob_get_ownedid_gearpower_for_ranked_stats_list = function(_, p202, p203, p204) --[[ Name: playerblob_get_ownedid_gearpower_for_ranked_stats_list ]] --[[ Line: 561 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_50 ]]
    local v205 = v_u_5:statsdict_base()
    v_u_50:playerblob_apply_ownedid_statsdict(p202, p203, v205)
    return v_u_50:statsdict_get_gear_power(v205, true, p204);
end;
v_u_50.playerblob_get_equipdict = function(_, p206) --[[ Name: playerblob_get_equipdict ]] --[[ Line: 567 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_50 ]]
    local v207 = {}
    for _, v208 in v_u_1:slot_itr() do
        local v209 = 0
        local v210 = v_u_50:get_equippedobj_for_slot(p206, v208)
        local v211, v212
        if v210 == nil then
            v211 = -1
            v212 = ""
        else
            v211 = v210.OwnedID
            v212 = v_u_50:get_equipmentdata_for_slot(p206, v208):get_name()
            if v_u_50:get_visible_for_slot(p206, v208) == true then
                v209 = true
            end;
        end;
        v207[v208] = {
            ["OwnedID"] = v211,
            ["EquipmentName"] = v212,
            ["Visible"] = v209
        }
    end;
    return v207;
end;
v_u_50.playerblob_autoequip_for_colors = function(_, p213, p214) --[[ Name: playerblob_autoequip_for_colors ]] --[[ Line: 601 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_50, (copy 5): v_u_12, (copy 6): v_u_2, (ref 7): v_u_15, (copy 8): v_u_3 ]]
    local v215 = v_u_11:new()
    local v_u_216 = v_u_4:new()
    local v217 = v_u_4:new()
    for _, v218 in v_u_1:slot_itr() do
        v215:list_of(v218)
        local v219 = v_u_50:get_visible_for_slot(p213, v218)
        if v219 ~= nil then
            v_u_12:is_bool(v219)
            v217:add(v218, v219)
        end;
    end;
    for v220 = 1, #p213.OwnedEquipment do
        local l_OwnedEquipment_3 = p213.OwnedEquipment[v220]
        local l_OwnedID_2 = l_OwnedEquipment_3.OwnedID
        local v221 = v_u_2:singleton():get_equipment_for_id(l_OwnedEquipment_3.EquipmentID)
        if v221 then
            v215:push_back_to(v221:get_avatar_slot(), l_OwnedID_2)
            v_u_216:add(l_OwnedID_2, v_u_50:playerblob_get_ownedid_gearpower_for_ranked_stats_list(p213, l_OwnedID_2, p214))
        end;
    end;
    for v222, v223 in v215:key_itr() do
        v223:sort(function(p224, p225) --[[ Line: 628 ]]
            --[[ Upvalues: (copy 1): v_u_216 ]]
            return v_u_216:get(p224) > v_u_216:get(p225);
        end)
        if v223:count() > 0 then
            v_u_50:playerblob_equip_ownedid(p213, (v223:get(1)))
            if v217:contains(v222) then
                v_u_50:set_visible_for_slot(p213, v222, v217:get(v222))
            end;
        end;
    end;
    local v_u_226 = v_u_4:new()
    local v227 = v_u_15:playerblob_get_ownedid_to_ownedpet_dict(p213)
    local v228 = v_u_3:new()
    for v229, _ in v227:key_itr() do
        v228:push_back(v229)
        v_u_226:add(v229, v_u_15:playerblob_get_pet_ownedid_gearpower_for_ranked_stats_list(p213, v229, p214))
    end;
    v228:sort(function(p230, p231) --[[ Line: 651 ]]
        --[[ Upvalues: (copy 1): v_u_226 ]]
        return v_u_226:get(p230) > v_u_226:get(p231);
    end)
    for v232, _ in v_u_15:get_pet_slot_set():key_itr() do
        v_u_15:playerblob_remove_pet_slotid(p213, v232)
    end;
    for _, _ in v_u_15:get_pet_slot_set():key_itr() do
        if v228:count() > 0 then
            v_u_15:playerblob_equip_pet_ownedid(p213, (v228:pop_front()))
        end;
    end;
end;
v_u_50.confirm_if_playerblob_cannot_add_any_more_gear = function(_, p233, p234, p_u_235) --[[ Name: confirm_if_playerblob_cannot_add_any_more_gear ]] --[[ Line: 676 ]]
    --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_6, (copy 3): v_u_50 ]]
    if v_u_16 == nil then
        return v_u_6:warnf("PlayerBlobAvatar:confirm_if_playerblob_cannot_add_any_more_gear PopupMessageUI is nil");
    end;
    if not v_u_50:playerblob_can_add_more_gear(p234) then
        return p233._menus:push_menu(v_u_16:new(p233, p233._spui, p233._menus):set_text("Max Gear Owned", "You have the max number of gear owned, and will not be able to receive this gear item. Are you sure you want to continue?"):set_okay_button_fn(function() --[[ Line: 686 ]]
            --[[ Upvalues: (copy 1): p_u_235 ]]
            p_u_235()
        end));
    end;
    p_u_235()
end;
return v_u_50;
