-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v4 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_5 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_6 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
local v_u_12 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_13 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_14 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_15 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_16 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_18 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v19 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_20 = nil
v19:require_shared(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_20 ]]
    v_u_20 = require(game.ReplicatedStorage.Avatar.PlayerBlobLoadout)
end)
local v_u_33 = {
    ["add_debug_pets_to_playerblob"] = function(_, p21) --[[ Name: add_debug_pets_to_playerblob ]] --[[ Line: 28 ]]
        p21.OwnedPets = {
            {
                ["OwnedID"] = 0,
                ["PetID"] = 1,
                ["Exp"] = 0,
                ["Rank"] = 1
            },
            {
                ["OwnedID"] = 1,
                ["PetID"] = 1,
                ["Exp"] = 500,
                ["Rank"] = 1
            },
            {
                ["OwnedID"] = 2,
                ["PetID"] = 1,
                ["Exp"] = 4000,
                ["Rank"] = 1
            }
        }
        p21.EquippedPets = {
            {
                ["OwnedID"] = 0,
                ["Slot"] = 1
            },
            {
                ["OwnedID"] = 1,
                ["Slot"] = 2
            },
            {
                ["OwnedID"] = 2,
                ["Slot"] = 3
            }
        }
    end,
    ["get_pet_icon"] = function(_) --[[ Name: get_pet_icon ]] --[[ Line: 37 ]]
        return "rbxassetid://8636395534";
    end,
    ["get_invalid_pet_slot"] = function(_) --[[ Name: get_invalid_pet_slot ]] --[[ Line: 50 ]]
        return -1;
    end,
    ["get_pet_slot_1_id"] = function(_) --[[ Name: get_pet_slot_1_id ]] --[[ Line: 51 ]]
        return 1;
    end,
    ["get_pet_slot_2_id"] = function(_) --[[ Name: get_pet_slot_2_id ]] --[[ Line: 52 ]]
        return 2;
    end,
    ["get_pet_slot_3_id"] = function(_) --[[ Name: get_pet_slot_3_id ]] --[[ Line: 53 ]]
        return 3;
    end,
    ["is_ownedpet"] = function(_, p22) --[[ Name: is_ownedpet ]] --[[ Line: 63 ]]
        return p22.PetID ~= nil;
    end,
    ["ownedpet_get_ownedid"] = function(_, p23) --[[ Name: ownedpet_get_ownedid ]] --[[ Line: 64 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8 ]]
        if p23.OwnedID == nil then
            v_u_2:warnf("PetUtils:ownedpet_get_ownedid(%s) no OwnedID", v_u_8:table_to_string(p23))
        end;
        return p23.OwnedID;
    end,
    ["ownedpet_get_petid"] = function(_, p24) --[[ Name: ownedpet_get_petid ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8 ]]
        if p24.PetID == nil then
            v_u_2:warnf("PetUtils:ownedpet_get_petid(%s) no PetID", v_u_8:table_to_string(p24))
        end;
        return p24.PetID;
    end,
    ["ownedpet_get_exp"] = function(_, p25) --[[ Name: ownedpet_get_exp ]] --[[ Line: 76 ]]
        return p25.Exp;
    end,
    ["ownedpet_get_rank"] = function(_, p26) --[[ Name: ownedpet_get_rank ]] --[[ Line: 77 ]]
        return p26.Rank;
    end,
    ["equippedpet_get_slot"] = function(_, p27) --[[ Name: equippedpet_get_slot ]] --[[ Line: 87 ]]
        return p27.Slot;
    end,
    ["equippedpet_get_ownedid"] = function(_, p28) --[[ Name: equippedpet_get_ownedid ]] --[[ Line: 88 ]]
        return p28.OwnedID;
    end,
    ["get_max_rank"] = function(_) --[[ Name: get_max_rank ]] --[[ Line: 199 ]]
        return 4;
    end,
    ["get_min_rank"] = function(_) --[[ Name: get_min_rank ]] --[[ Line: 200 ]]
        return 1;
    end,
    ["get_max_level"] = function(_) --[[ Name: get_max_level ]] --[[ Line: 201 ]]
        return 50;
    end,
    ["get_min_level"] = function(_) --[[ Name: get_min_level ]] --[[ Line: 202 ]]
        return 1;
    end,
    ["get_exp_for_next_level"] = function(_, p29, p30) --[[ Name: get_exp_for_next_level ]] --[[ Line: 204 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_9, (copy 3): v_u_13 ]]
        local v31 = v_u_8:clamp(p29, 0, 50)
        local v32 = math.ceil((p30 == v_u_13.Rarity.Tier1 and 150 or (p30 == v_u_13.Rarity.Tier2 and 200 or (p30 == v_u_13.Rarity.Tier3 and 250 or (p30 == v_u_13.Rarity.Tier4 and 425 or 500)))) * v31 * v_u_9:YForPointOf2PtLineP1P2X(1, 1, 50, 5, v31))
        return v32 - v32 % 50;
    end
}
local v_u_34 = v_u_3:new():add_table({
    [v_u_13.Rarity.Tier1] = "http://www.roblox.com/asset/?id=6423425381",
    [v_u_13.Rarity.Tier2] = "http://www.roblox.com/asset/?id=6423426034",
    [v_u_13.Rarity.Tier3] = "http://www.roblox.com/asset/?id=6423426306",
    [v_u_13.Rarity.Tier4] = "http://www.roblox.com/asset/?id=6423426592",
    [v_u_13.Rarity.Tier5] = "http://www.roblox.com/asset/?id=6423426871"
})
v_u_33.pet_rarity_to_icon = function(_, p35) --[[ Name: pet_rarity_to_icon ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_34 ]]
    return v_u_34:get(p35);
end;
local v_u_36 = { v_u_33:get_pet_slot_1_id(), v_u_33:get_pet_slot_2_id(), v_u_33:get_pet_slot_3_id() }
v_u_33.get_pet_slot_list = function(_) --[[ Name: get_pet_slot_list ]] --[[ Line: 60 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_36 ]]
    return v_u_1:new():push_back_table_list(v_u_36);
end;
v_u_33.get_pet_slot_set = function(_) --[[ Name: get_pet_slot_set ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_36 ]]
    return v_u_3:new():add_set_from_table_list(v_u_36);
end;
v_u_33.ownedpet_get_rarity = function(_, p37) --[[ Name: ownedpet_get_rarity ]] --[[ Line: 78 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_33, (copy 3): v_u_2, (copy 4): v_u_8, (copy 5): v_u_13 ]]
    local v38 = v_u_5:singleton():get_data_for_petid(v_u_33:ownedpet_get_petid(p37))
    if v38 ~= nil then
        return v38:get_rarity();
    end;
    v_u_2:warnf("PetUtils:ownedpet_get_rarity(%s) pet_info is nil", v_u_8:table_to_string(p37))
    return v_u_13.Rarity.Tier1;
end;
v_u_33.playerblob_get_ownedid_to_ownedpet_dict = function(_, p39) --[[ Name: playerblob_get_ownedid_to_ownedpet_dict ]] --[[ Line: 90 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_33 ]]
    local v40 = v_u_3:new()
    for v41 = 1, #p39.OwnedPets do
        local l_OwnedPets_0 = p39.OwnedPets[v41]
        v40:add(v_u_33:ownedpet_get_ownedid(l_OwnedPets_0), l_OwnedPets_0)
    end;
    return v40;
end;
v_u_33.playerblob_get_pet_ownedid_ownedpet = function(_, p42, p43) --[[ Name: playerblob_get_pet_ownedid_ownedpet ]] --[[ Line: 99 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p42):get(p43);
end;
local function f_playerblob_equippedpet_tab_get_slot_to_owned_pet_dict(p44, p45) --[[ Name: playerblob_equippedpet_tab_get_slot_to_owned_pet_dict ]] --[[ Line: 104 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_3 ]]
    local v46 = v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p44)
    local v47 = v_u_3:new()
    local v48 = false
    for v49 = 1, #p45 do
        local v50 = p45[v49]
        if v46:contains(v_u_33:equippedpet_get_ownedid(v50)) then
            v47:add(v_u_33:equippedpet_get_slot(v50), v46:get(v_u_33:equippedpet_get_ownedid(v50)))
        else
            v48 = true
        end;
    end;
    return v47, v48;
end;
v_u_33.playerblob_get_slot_to_owned_pet_dict = function(_, p51) --[[ Name: playerblob_get_slot_to_owned_pet_dict ]] --[[ Line: 122 ]]
    --[[ Upvalues: (copy 1): f_playerblob_equippedpet_tab_get_slot_to_owned_pet_dict ]]
    return f_playerblob_equippedpet_tab_get_slot_to_owned_pet_dict(p51, p51.EquippedPets);
end;
v_u_33.cmp_slot_to_ownedpet_dict = function(_, p52, p53) --[[ Name: cmp_slot_to_ownedpet_dict ]] --[[ Line: 126 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    for v54, _ in v_u_33:get_pet_slot_set():key_itr() do
        local v55 = p52:contains(v54)
        local v56 = p53:contains(v54)
        if v55 ~= v56 then
            return false;
        end;
        if v55 and (v56 and v_u_33:ownedpet_get_ownedid(p52:get(v54)) ~= v_u_33:ownedpet_get_ownedid(p53:get(v54))) then
            return false;
        end;
    end;
    return true;
end;
v_u_33.playerblob_validate_equipped_pet_table = function(_, p57, p58) --[[ Name: playerblob_validate_equipped_pet_table ]] --[[ Line: 140 ]]
    --[[ Upvalues: (copy 1): f_playerblob_equippedpet_tab_get_slot_to_owned_pet_dict ]]
    local _, v59 = f_playerblob_equippedpet_tab_get_slot_to_owned_pet_dict(p57, p58)
    return v59 == false;
end;
v_u_33.playerblob_write_equipped_pet_table = function(_, p60, p61) --[[ Name: playerblob_write_equipped_pet_table ]] --[[ Line: 148 ]]
    --[[ Upvalues: (copy 1): f_playerblob_equippedpet_tab_get_slot_to_owned_pet_dict, (copy 2): v_u_33 ]]
    local v62 = f_playerblob_equippedpet_tab_get_slot_to_owned_pet_dict(p60, p61)
    local v63 = {}
    for _, v64 in v_u_33:get_pet_slot_list():key_itr() do
        if v62:contains(v64) then
            local v65 = v62:get(v64)
            v63[#v63 + 1] = {
                ["OwnedID"] = v_u_33:ownedpet_get_ownedid(v65),
                ["Slot"] = v64
            }
        end;
    end;
    p60.EquippedPets = v63
end;
v_u_33.playerblob_pet_ownedid_is_equipped = function(_, p66, p67) --[[ Name: playerblob_pet_ownedid_is_equipped ]] --[[ Line: 163 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v68 = v_u_33:playerblob_get_slot_to_owned_pet_dict(p66)
    for v69, _ in v_u_33:get_pet_slot_set():key_itr() do
        if v68:contains(v69) and p67 == v_u_33:ownedpet_get_ownedid(v68:get(v69)) then
            return true, v69;
        end;
    end;
    return false, nil;
end;
local v_u_70 = v4:new()
local v_u_71 = v_u_20
for v72, _ in v_u_3:new():add_set_from_table_list({
    v_u_13.Rarity.Tier1,
    v_u_13.Rarity.Tier2,
    v_u_13.Rarity.Tier3,
    v_u_13.Rarity.Tier4,
    v_u_13.Rarity.Tier5
}):key_itr() do
    local v73 = 0
    for v74 = 1, 50 do
        local v75 = v_u_70:list_of(v72)
        v73 = v73 + v_u_33:get_exp_for_next_level(v74 - 1, v72)
        v75:push_back(v73)
    end;
end;
v_u_33.debug_log_rarity_to_exp = function(_) --[[ Name: debug_log_rarity_to_exp ]] --[[ Line: 245 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): v_u_33, (copy 5): v_u_70, (copy 6): v_u_6, (copy 7): v_u_8, (copy 8): v_u_2 ]]
    local v76 = "\n"
    for _, v77 in v_u_1:new():push_back_table_list({ 1, 2 }):key_itr() do
        local v78 = v_u_5:singleton():get_data_for_petid(v77)
        local v79 = v78:get_rarity()
        local v80 = v_u_3:new()
        for v81 = 1, 50 do
            for v82 = 1, 4 do
                if v81 <= v_u_33:rank_to_max_level(v82) then
                    v80:add(v81, v82)
                    break;
                end;
            end;
        end;
        v76 = v76 .. string.format("-----Pet[%s] Rarity(%d)\n", v78:get_name(), v79)
        local v83 = v_u_70:list_of(v79)
        for v84 = 1, 50 do
            local v85 = v80:get(v84)
            local v86 = v_u_6:statsdict_base()
            v_u_33:petid_level_rank_apply_statsdict(v77, v84, v85, v86)
            local v87 = v83:get(v84)
            local v88
            if v84 < 50 then
                v88 = v83:get(v84 + 1)
            else
                v88 = v87
            end;
            v76 = v76 .. string.format("\tLevel[%d] Rank(%d) Exp(%s) Next(%s) Stats(%s)\n", v84, v85, v_u_8:comma_value(v87), v_u_8:comma_value(v88 - v87), v_u_6:statsdict_to_str(v86))
        end;
    end;
    v_u_2:warnf(v76)
end;
v_u_33.get_exp_to_level = function(_, p89, p90) --[[ Name: get_exp_to_level ]] --[[ Line: 290 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_70 ]]
    return v_u_70:list_of(p90):get((v_u_8:clamp(p89, 1, 50)));
end;
local v_u_91 = v_u_3:new()
v_u_33.pet_exp_get_level = function(_, p92, p93) --[[ Name: pet_exp_get_level ]] --[[ Line: 297 ]]
    --[[ Upvalues: (copy 1): v_u_91, (copy 2): v_u_70 ]]
    local v94 = string.format("rarity(%d)_exp(%d)", p93, p92)
    if v_u_91:contains(v94) then
        return v_u_91:get(v94);
    end;
    local v95 = v_u_70:list_of(p93)
    local v96 = 1
    for v97 = 2, v95:count() do
        if v95:get(v97) > p92 then
            break;
        end;
        v96 = v97
    end;
    v_u_91:add(v94, v96)
    return v96;
end;
v_u_33.ownedpet_get_level = function(_, p98) --[[ Name: ownedpet_get_level ]] --[[ Line: 315 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return v_u_33:pet_exp_get_level(v_u_33:ownedpet_get_exp(p98), v_u_33:ownedpet_get_rarity(p98));
end;
v_u_33.rank_to_max_level = function(_, p99) --[[ Name: rank_to_max_level ]] --[[ Line: 319 ]]
    return p99 >= 4 and 50 or (p99 >= 3 and 40 or (p99 >= 2 and 30 or 20));
end;
v_u_33.ownedpet_get_max_level = function(_, p100) --[[ Name: ownedpet_get_max_level ]] --[[ Line: 331 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return v_u_33:rank_to_max_level(v_u_33:ownedpet_get_rank(p100));
end;
v_u_33.petid_level_rank_apply_statsdict = function(_, p101, p102, p103, p104) --[[ Name: petid_level_rank_apply_statsdict ]] --[[ Line: 335 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_8, (copy 3): v_u_6, (copy 4): v_u_9, (copy 5): v_u_18 ]]
    local v105 = v_u_5:singleton():get_data_for_petid(p101)
    if v105 ~= nil then
        local v106 = v_u_8:clamp(p102, 1, 50)
        local v107 = v_u_8:clamp(p103, 1, 4)
        local v108 = v105:get_base_statmodifierobj()
        for v109, v110 in pairs(v108) do
            v108[v109] = v110 * v107
        end;
        v_u_6:statsdict_apply_statmodifierobj(p104, v108)
        local v111 = v105:get_color_statmodifierobj()
        local v112 = v_u_9:YForPointOf2PtLineP1P2X(1, 1, 50, 5, v106)
        for v113, v114 in pairs(v111) do
            if v_u_18.PetRankUpEnabled == true then
                v111[v113] = math.floor(v114 * v112)
            else
                v111[v113] = math.ceil(v114 * v112)
            end;
        end;
        v_u_6:statsdict_apply_statmodifierobj(p104, v111)
    end;
end;
v_u_33.playerblob_apply_pet_ownedid_statsdict = function(_, p115, p116, p117) --[[ Name: playerblob_apply_pet_ownedid_statsdict ]] --[[ Line: 364 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v118 = v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p115)
    if v118:contains(p116) == true then
        local v119 = v118:get(p116)
        v_u_33:petid_level_rank_apply_statsdict(v_u_33:ownedpet_get_petid(v119), v_u_33:ownedpet_get_level(v119), v_u_33:ownedpet_get_rank(v119), p117)
    end;
end;
v_u_33.playerblob_get_pet_ownedid_gearpower_for_ranked_stats_list = function(_, p120, p121, p122) --[[ Name: playerblob_get_pet_ownedid_gearpower_for_ranked_stats_list ]] --[[ Line: 375 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_33, (copy 3): v_u_10 ]]
    local v123 = v_u_6:statsdict_base()
    v_u_33:playerblob_apply_pet_ownedid_statsdict(p120, p121, v123)
    return v_u_10:statsdict_get_gear_power(v123, true, p122);
end;
v_u_33.playerblob_get_pet_ownedid_gearpower = function(_, p124, p125) --[[ Name: playerblob_get_pet_ownedid_gearpower ]] --[[ Line: 382 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_33 ]]
    local v126 = v_u_6:statsdict_base()
    v_u_33:playerblob_apply_pet_ownedid_statsdict(p124, p125, v126)
    return v_u_33:playerblob_get_pet_ownedid_gearpower_for_ranked_stats_list(p124, p125, (v_u_6:statsdict_get_ranked_colors(v126)));
end;
v_u_33.playerblob_remove_pet_slotid = function(_, p127, p_u_128) --[[ Name: playerblob_remove_pet_slotid ]] --[[ Line: 391 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_33, (copy 3): v_u_1 ]]
    v_u_7:is_true(v_u_33:get_pet_slot_set():contains(p_u_128))
    if v_u_33:playerblob_get_slot_to_owned_pet_dict(p127):contains(p_u_128) ~= true then
        return false;
    end;
    v_u_1:remove_if(v_u_1:new(p127.EquippedPets), function(p129) --[[ Line: 396 ]]
        --[[ Upvalues: (ref 1): v_u_33, (copy 2): p_u_128 ]]
        return v_u_33:equippedpet_get_slot(p129) == p_u_128;
    end)
    return true;
end;
v_u_33.playerblob_equip_pet_ownedid = function(_, p130, p131, p132) --[[ Name: playerblob_equip_pet_ownedid ]] --[[ Line: 402 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_7 ]]
    if v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p130):contains(p131) == true then
        local v133, v134 = v_u_33:playerblob_pet_ownedid_is_equipped(p130, p131)
        if v133 then
            return true, v134;
        elseif p132 == nil then
            local v135 = v_u_33:playerblob_get_slot_to_owned_pet_dict(p130)
            if v135:count() == v_u_33:get_pet_slot_set():count() and v135:contains(v_u_33:get_pet_slot_3_id()) then
                v_u_33:playerblob_remove_pet_slotid(p130, v_u_33:get_pet_slot_3_id())
                v135 = v_u_33:playerblob_get_slot_to_owned_pet_dict(p130)
            end;
            for _, v136 in v_u_33:get_pet_slot_list():key_itr() do
                if v135:contains(v136) ~= true then
                    p130.EquippedPets[#p130.EquippedPets + 1] = {
                        ["OwnedID"] = p131,
                        ["Slot"] = v136
                    }
                    return true, v136;
                end;
            end;
            return false;
        else
            v_u_7:is_true(v_u_33:get_pet_slot_set():contains(p132))
            if v_u_33:playerblob_get_slot_to_owned_pet_dict(p130):contains(p132) then
                v_u_33:playerblob_remove_pet_slotid(p130, p132)
            end;
            p130.EquippedPets[#p130.EquippedPets + 1] = {
                ["OwnedID"] = p131,
                ["Slot"] = p132
            }
            return true, p132;
        end;
    else
        return false;
    end;
end;
v_u_33.get_gem_train_amount = function(_) --[[ Name: get_gem_train_amount ]] --[[ Line: 444 ]]
    return 2000;
end;
v_u_33.get_large_note_train_amount = function(_) --[[ Name: get_large_note_train_amount ]] --[[ Line: 445 ]]
    return 200;
end;
v_u_33.get_medium_note_train_amount = function(_) --[[ Name: get_medium_note_train_amount ]] --[[ Line: 446 ]]
    return 20;
end;
v_u_33.get_small_note_train_amount = function(_) --[[ Name: get_small_note_train_amount ]] --[[ Line: 447 ]]
    return 2;
end;
v_u_33.sealed_mini_train_amount = function(_, p137, p138) --[[ Name: sealed_mini_train_amount ]] --[[ Line: 449 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return (p137 == v_u_13.Rarity.Tier1 and 1 or (p137 == v_u_13.Rarity.Tier2 and 2 or (p137 == v_u_13.Rarity.Tier3 and 3 or (p137 == v_u_13.Rarity.Tier4 and 4 or (p137 == v_u_13.Rarity.Tier5 and 5 or 1))))) * 2000 * (p138 and 2 or 1);
end;
v_u_33.get_materialid_to_value_dict_of_train_consumable_materials_for_pet_id = function(_, p139, p140) --[[ Name: get_materialid_to_value_dict_of_train_consumable_materials_for_pet_id ]] --[[ Line: 470 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_7, (copy 4): v_u_15, (copy 5): v_u_5, (copy 6): v_u_6, (copy 7): v_u_11, (copy 8): v_u_12, (copy 9): v_u_33, (copy 10): v_u_18 ]]
    if p140 == nil then
        v_u_2:warnf("PetUtils:get_materialid_to_value_dict_of_train_consumable_materials_for_pet_id did not include has_vip, defaulting to false")
        p140 = false
    end;
    local v_u_141 = v_u_3:new()
    local v_u_142 = 1
    if p140 == true then
        v_u_142 = v_u_142 + 0.1
    end;
    local function f_add_material_id_train_amount_with_multiplier(p143, p144) --[[ Name: add_material_id_train_amount_with_multiplier ]] --[[ Line: 482 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_15, (ref 3): v_u_142, (copy 4): v_u_141 ]]
        v_u_7:is_true(v_u_15:singleton():contains_material(p143))
        local v145 = math.floor(p144 * v_u_142)
        v_u_7:is_int(v145)
        v_u_7:is_true(v145 > 0)
        v_u_141:add(p143, v145)
    end;
    local v146 = v_u_5:singleton():get_data_for_petid(p139)
    local v147 = v_u_6:statsdict_base()
    v_u_6:statsdict_apply_statmodifierobj(v147, v146:get_color_statmodifierobj())
    for _, v148 in v_u_6:statsdict_get_ranked_colors(v147):key_itr() do
        if v147[v_u_6:elemental_color_to_gearstats_type(v148)] > 0 then
            f_add_material_id_train_amount_with_multiplier(v_u_11:color_and_tier_to_material_id(v148, v_u_12.Tier.T1), v_u_33:get_small_note_train_amount())
            f_add_material_id_train_amount_with_multiplier(v_u_11:color_and_tier_to_material_id(v148, v_u_12.Tier.T2), v_u_33:get_medium_note_train_amount())
            f_add_material_id_train_amount_with_multiplier(v_u_11:color_and_tier_to_material_id(v148, v_u_12.Tier.T3), v_u_33:get_large_note_train_amount())
            if v_u_18.PetRankUpEnabled == true then
                f_add_material_id_train_amount_with_multiplier(v_u_11:color_and_tier_to_material_id(v148, v_u_12.Tier.T4), v_u_33:get_gem_train_amount())
            end;
        end;
    end;
    for v149, v150 in v_u_15:singleton():material_key_itr() do
        if v150:is_pet() then
            local v151 = v150:get_pet_id()
            f_add_material_id_train_amount_with_multiplier(v149, v_u_33:sealed_mini_train_amount(v_u_5:singleton():get_data_for_petid(v151):get_rarity(), p139 == v151))
        elseif v150:is_blueprint() then
            if v_u_18.PetRankUpEnabled == true then
                if v150:get_tier() <= v_u_12.Tier.T3 then
                    f_add_material_id_train_amount_with_multiplier(v149, 1000)
                else
                    f_add_material_id_train_amount_with_multiplier(v149, 2000)
                end;
            elseif v150:get_tier() <= v_u_12.Tier.T3 then
                f_add_material_id_train_amount_with_multiplier(v149, 500)
            else
                f_add_material_id_train_amount_with_multiplier(v149, 1000)
            end;
        end;
    end;
    return v_u_141;
end;
v_u_33.ownedpet_get_info_for_apply_exp_gain = function(_, p152, p153) --[[ Name: ownedpet_get_info_for_apply_exp_gain ]] --[[ Line: 550 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_8, (copy 3): v_u_33 ]]
    v_u_7:is_true(p153 >= 0)
    v_u_7:is_true(p153 < v_u_8:input_max_number())
    local v154 = v_u_33:ownedpet_get_exp(p152)
    local v155 = v154 + p153
    local v156 = v_u_33:pet_exp_get_level(v155, v_u_33:ownedpet_get_rarity(p152))
    local v157 = v_u_33:ownedpet_get_max_level(p152)
    local v158, v159
    if v157 <= v156 then
        v158 = v_u_33:get_exp_to_level(v157, v_u_33:ownedpet_get_rarity(p152))
        v159 = v155 - v158
    else
        v158 = v155
        v159 = 0
    end;
    return {
        ["FinalEXP"] = v158,
        ["WastedEXP"] = v159,
        ["GainedEXP"] = v158 - v154
    };
end;
v_u_33.ownedpet_apply_exp_gain = function(_, p160, p161) --[[ Name: ownedpet_apply_exp_gain ]] --[[ Line: 574 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_8, (copy 3): v_u_33 ]]
    v_u_7:is_true(p161 >= 0)
    v_u_7:is_true(p161 < v_u_8:input_max_number())
    local v162 = v_u_33:ownedpet_get_info_for_apply_exp_gain(p160, p161)
    p160.Exp = v162.FinalEXP
    if p160.Exp < 0 then
        p160.Exp = 0
    end;
    return v162;
end;
v_u_33.playerblob_validate_with_dayid_weekid = function(_, p163, _, _, p164) --[[ Name: playerblob_validate_with_dayid_weekid ]] --[[ Line: 587 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_3 ]]
    local v165 = false
    for _, v166 in v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p163):key_itr() do
        local v167 = v_u_33:ownedpet_get_max_level(v166)
        local v168 = v_u_33:ownedpet_get_level(v166)
        local v169 = v_u_33:ownedpet_get_exp(v166)
        if v167 < v168 then
            v166.Exp = v_u_33:get_exp_to_level(v167, v_u_33:ownedpet_get_rarity(v166))
            v_u_3:counter_increment(p164, "Ct_OwnedPet_OverMaxLevel", 1)
            p164:add("OwnedPet_OverMaxLevel", {
                ["CurEXP"] = v169,
                ["CurLevel"] = v168,
                ["PostEXP"] = v_u_33:ownedpet_get_exp(v166),
                ["PostLevel"] = v_u_33:ownedpet_get_level(v166)
            })
            v165 = true
        end;
    end;
    return v165;
end;
v_u_33.get_playerblob_displaypet_table = function(_, p170) --[[ Name: get_playerblob_displaypet_table ]] --[[ Line: 610 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v171 = {}
    for v172, v173 in v_u_33:playerblob_get_slot_to_owned_pet_dict(p170):key_itr() do
        v171[#v171 + 1] = {
            ["PetID"] = v_u_33:ownedpet_get_petid(v173),
            ["Slot"] = v172
        }
    end;
    return v171;
end;
v_u_33.displaypet_table_get_slot_to_petid_dict = function(_, p174) --[[ Name: displaypet_table_get_slot_to_petid_dict ]] --[[ Line: 622 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v175 = v_u_3:new()
    for v176 = 1, #p174 do
        local v177 = p174[v176]
        v175:add(v177.Slot, v177.PetID)
    end;
    return v175;
end;
v_u_33.get_play_exp_per_minute = function(_) --[[ Name: get_play_exp_per_minute ]] --[[ Line: 631 ]]
    --[[ Upvalues: (copy 1): v_u_18 ]]
    return v_u_18.PetRankUpEnabled == true and 30 or 5;
end;
v_u_33.get_play_exp_amount = function(_, p178, p179, p180) --[[ Name: get_play_exp_amount ]] --[[ Line: 639 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_9, (copy 3): v_u_14, (copy 4): v_u_8 ]]
    local v181 = v_u_33:get_play_exp_per_minute()
    return v_u_8:clamp(math.ceil(v_u_9:YForPointOf2PtLineP1P2X(60, v181, 360, v181 * 6, v_u_14:singleton():songkey_get_approx_length_sec(p178)) * v_u_9:YForPointOf2PtLineP1P2X(0.35, 0.25, 0.85, 1, p180) * v_u_9:YForPointOf2PtLineP1P2X(1, 1, 4, 4, p179)), v181, v181 * 6 * 4);
end;
v_u_33.get_max_number_of_owned_pets = function(_) --[[ Name: get_max_number_of_owned_pets ]] --[[ Line: 676 ]]
    return 100;
end;
v_u_33.playerblob_get_owned_petid_set = function(_, p182) --[[ Name: playerblob_get_owned_petid_set ]] --[[ Line: 678 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_3 ]]
    local v183 = v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p182)
    local v184 = v_u_3:new()
    for _, v185 in v183:key_itr() do
        v184:add_set(v_u_33:ownedpet_get_petid(v185))
    end;
    return v184;
end;
v_u_33.playerblob_can_add_pet_of_petid = function(_, p186, p187) --[[ Name: playerblob_can_add_pet_of_petid ]] --[[ Line: 687 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v188 = v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p186)
    local v189 = v_u_33:playerblob_get_owned_petid_set(p186)
    if v188:count() >= v_u_33:get_max_number_of_owned_pets() then
        return false, "You own the max number of Minis.";
    elseif v189:contains(p187) == true then
        return false, "You already own this Mini.";
    else
        return true, "";
    end;
end;
v_u_33.playerblob_add_pet_of_petid = function(_, p_u_190, p191) --[[ Name: playerblob_add_pet_of_petid ]] --[[ Line: 702 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    if v_u_33:playerblob_can_add_pet_of_petid(p_u_190, p191) ~= true then
        return false, nil;
    end;
    local v194 = (function() --[[ Name: playerblob_alloc_pet_ownedid ]] --[[ Line: 705 ]]
        --[[ Upvalues: (ref 1): v_u_33, (copy 2): p_u_190 ]]
        local v192 = v_u_33:playerblob_get_ownedid_to_ownedpet_dict(p_u_190)
        local v193 = 1
        while v192:contains(v193) == true do
            v193 = v193 + 1
        end;
        return v193;
    end)()
    p_u_190.OwnedPets[#p_u_190.OwnedPets + 1] = {
        ["OwnedID"] = v194,
        ["PetID"] = p191,
        ["Exp"] = 0,
        ["Rank"] = 1
    }
    return true, v194;
end;
v_u_33.playerblob_any_slot_free = function(_, p195) --[[ Name: playerblob_any_slot_free ]] --[[ Line: 728 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return v_u_33:playerblob_get_slot_to_owned_pet_dict(p195):count() < v_u_33:get_pet_slot_list():count();
end;
v_u_33.playerblob_add_pet_or_material_of_petid = function(_, p196, p197) --[[ Name: playerblob_add_pet_or_material_of_petid ]] --[[ Line: 732 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_5, (copy 3): v_u_33, (copy 4): v_u_16 ]]
    v_u_7:is_true(v_u_5:singleton():contains_petid(p197))
    local v198 = nil
    local v199 = nil
    local v200 = nil
    if v_u_33:playerblob_can_add_pet_of_petid(p196, p197) then
        local v201, v202 = v_u_33:playerblob_add_pet_of_petid(p196, p197)
        return string.format("\"%s\" Mini added to your collection.", v_u_5:singleton():get_name_for_petid(p197)), v201, v202, v200;
    end;
    local v203 = v_u_5:singleton():get_data_for_petid(p197):get_material_id()
    v_u_16:add_crafting_materials_of_id(p196, v203, 1)
    return string.format("\"%s\" Mini added to your inventory.", v_u_5:singleton():get_name_for_petid(p197)), v198, v199, v203;
end;
v_u_33.playerblob_get_display_ownedid_petid = function(_, p204) --[[ Name: playerblob_get_display_ownedid_petid ]] --[[ Line: 747 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v205 = v_u_33:get_pet_slot_list()
    local v206 = v_u_33:playerblob_get_slot_to_owned_pet_dict(p204)
    for v207 = v205:count(), 1, -1 do
        local v208 = v205:get(v207)
        if v206:contains(v208) then
            local v209 = v206:get(v208)
            return true, v_u_33:ownedpet_get_ownedid(v209), v_u_33:ownedpet_get_petid(v209);
        end;
    end;
    return false, nil, nil;
end;
v_u_33.server_grant_and_opt_equip_petid = function(_, p_u_210, p_u_211, p212, p_u_213) --[[ Name: server_grant_and_opt_equip_petid ]] --[[ Line: 760 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_17 ]]
    local v_u_214, v_u_215, v_u_216, v_u_217 = v_u_33:playerblob_add_pet_or_material_of_petid(p_u_210._player_blob_manager:get_cached_blob(p_u_211.UserId), p212, false)
    p_u_210._player_blob_manager:enqueue_blob_sync_request(p_u_211.UserId, v_u_17.PlayerBlobRequestType.Write, function(p218) --[[ Line: 766 ]]
        --[[ Upvalues: (copy 1): v_u_215, (ref 2): v_u_33, (copy 3): v_u_216, (copy 4): p_u_210, (copy 5): p_u_211, (ref 6): v_u_17, (copy 7): p_u_213, (copy 8): v_u_214, (copy 9): v_u_217 ]]
        if v_u_215 and v_u_33:playerblob_any_slot_free(p218) then
            v_u_33:playerblob_equip_pet_ownedid(p218, v_u_216)
            p_u_210._player_blob_manager:enqueue_blob_sync_request(p_u_211.UserId, v_u_17.PlayerBlobRequestType.Write, function(p219) --[[ Line: 772 ]]
                --[[ Upvalues: (ref 1): p_u_210, (ref 2): p_u_211, (ref 3): p_u_213, (ref 4): v_u_216, (ref 5): v_u_214 ]]
                p_u_210._lobby_manager:update_player_character_to_equipped_data(p_u_211, p219)
                p_u_213({
                    ["PetOwnedID"] = v_u_216,
                    ["Message"] = v_u_214
                })
            end)
        else
            p_u_213({
                ["MaterialID"] = v_u_217,
                ["Message"] = v_u_214
            })
        end;
    end)
end;
v_u_33.ownedpet_can_rank_up = function(_, p220) --[[ Name: ownedpet_can_rank_up ]] --[[ Line: 788 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v221
    if v_u_33:ownedpet_get_level(p220) == v_u_33:ownedpet_get_max_level(p220) then
        v221 = v_u_33:ownedpet_get_rank(p220) < 4
    else
        v221 = false
    end;
    return v221;
end;
v_u_33.ownedpet_get_rank_up_point_total_requirement = function(_, p222) --[[ Name: ownedpet_get_rank_up_point_total_requirement ]] --[[ Line: 805 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_13 ]]
    local v223 = v_u_33:ownedpet_get_rarity(p222)
    local v224 = v_u_33:ownedpet_get_rank(p222)
    return v223 == v_u_13.Rarity.Tier2 and (v224 == 1 and 20 or (v224 == 2 and 60 or 120)) or (v224 == 1 and 10 or (v224 == 2 and 30 or 90));
end;
v_u_33.ownedpet_get_material_id_rank_up_point_amount = function(_, p225, p226) --[[ Name: ownedpet_get_material_id_rank_up_point_amount ]] --[[ Line: 840 ]]
    --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_15, (copy 3): v_u_5, (copy 4): v_u_3, (copy 5): v_u_13 ]]
    local v227 = v_u_33:ownedpet_get_petid(p225)
    local v228 = v_u_15:singleton():get_material(p226)
    if v228 == nil then
        return 0;
    end;
    if v228:is_pet() ~= true then
        return 0;
    end;
    local v229 = v228:get_pet_id()
    local v230 = v_u_5:singleton():get_data_for_petid(v229):get_rarity()
    return v_u_3:set_intersection(v_u_5:singleton():get_data_for_petid(v227):get_colors_set(), (v_u_5:singleton():get_data_for_petid(v229):get_colors_set())):count() == 0 and 0 or (v229 == v227 and (v230 == v_u_13.Rarity.Tier2 and 20 or 10) or (v230 == v_u_13.Rarity.Tier2 and 4 or 2));
end;
v_u_33.ownedpet_get_materialid_to_count_dict_rank_up_point_total = function(_, p231, p232) --[[ Name: ownedpet_get_materialid_to_count_dict_rank_up_point_total ]] --[[ Line: 871 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    local v233 = 0
    for v234, v235 in p232:key_itr() do
        v233 = v233 + v_u_33:ownedpet_get_material_id_rank_up_point_amount(p231, v234) * v235
    end;
    return v233;
end;
v_u_33.ownedpet_increment_rank = function(_, p236) --[[ Name: ownedpet_increment_rank ]] --[[ Line: 879 ]]
    local v237 = p236.Rank + 1
    p236.Rank = v237 > 4 and 4 or v237
end;
v_u_33.playerblob_unequip_pet_and_remove_from_loadouts = function(_, p238, p239) --[[ Name: playerblob_unequip_pet_and_remove_from_loadouts ]] --[[ Line: 888 ]]
    --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_71 ]]
    if v_u_33:playerblob_pet_ownedid_is_equipped(p238, p239) then
        for v240, v241 in v_u_33:playerblob_get_slot_to_owned_pet_dict(p238):key_itr() do
            if v_u_33:ownedpet_get_ownedid(v241) == p239 then
                v_u_33:playerblob_remove_pet_slotid(p238, v240)
                break;
            end;
        end;
    end;
    v_u_71:remove_pet_ownedid_from_loadouts(p238, p239)
end;
v_u_33.playerblob_delete_pet_ownedid = function(_, p242, p_u_243) --[[ Name: playerblob_delete_pet_ownedid ]] --[[ Line: 904 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_33 ]]
    v_u_1:remove_if(v_u_1:new(p242.OwnedPets), function(p244) --[[ Line: 908 ]]
        --[[ Upvalues: (ref 1): v_u_33, (copy 2): p_u_243 ]]
        return v_u_33:ownedpet_get_ownedid(p244) == p_u_243;
    end)
end;
return v_u_33;
