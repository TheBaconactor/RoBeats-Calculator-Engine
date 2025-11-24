-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_5 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
require(game.ReplicatedStorage.Avatar.ElementalColor)
require(game.ReplicatedStorage.Crafting.ColorTierMaterial)
require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_10 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v15 = {
    ["get_challengepassv2_square_icon_assetid"] = function(_) --[[ Name: get_challengepassv2_square_icon_assetid ]] --[[ Line: 30 ]]
        return "rbxassetid://16250890526";
    end,
    ["entry_list_to_table"] = function(_, p12) --[[ Name: entry_list_to_table ]] --[[ Line: 92 ]]
        local v13 = {}
        for v14 = 1, p12:count() do
            v13[v14] = p12:get(v14):to_table()
        end;
        return v13;
    end
}
local v_u_23 = {
    ["new"] = function(_, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6, (copy 3): v_u_1 ]]
        v_u_3:is_int_greater_than(p_u_16, 0)
        v_u_3:is_true(p_u_17:get_table() ~= nil)
        v_u_3:is_true(p_u_18:get_table() ~= nil)
        local v19 = {}
        v19.get_points = function(_) --[[ Name: get_points ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): p_u_16 ]]
            return p_u_16;
        end;
        v19.get_reward_list_standard = function(_) --[[ Name: get_reward_list_standard ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            return p_u_17;
        end;
        v19.get_reward_list_vip = function(_) --[[ Name: get_reward_list_vip ]] --[[ Line: 42 ]]
            --[[ Upvalues: (copy 1): p_u_18 ]]
            return p_u_18;
        end;
        v19.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_6, (copy 3): p_u_17, (copy 4): p_u_18 ]]
            return {
                ["Points"] = p_u_16,
                ["RewardListStandard"] = v_u_6.RewardInfo:list_to_table(p_u_17),
                ["RewardListVIP"] = v_u_6.RewardInfo:list_to_table(p_u_18)
            };
        end;
        v19.get_icon = function(_, p20) --[[ Name: get_icon ]] --[[ Line: 52 ]]
            --[[ Upvalues: (copy 1): p_u_18, (copy 2): p_u_17, (ref 3): v_u_1 ]]
            if p20 and p_u_18:count() > 0 then
                return p_u_18:get(1):get_image();
            elseif p_u_17:count() > 0 then
                return p_u_17:get(1):get_image();
            else
                return v_u_1:important_assetid();
            end;
        end;
        v19.get_amount = function(_, p21) --[[ Name: get_amount ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): p_u_18, (copy 2): p_u_17 ]]
            if p21 and p_u_18:count() > 0 then
                return p_u_18:get(1):get_amount();
            else
                return p_u_17:count() <= 0 and 0 or p_u_17:get(1):get_amount();
            end;
        end;
        v19.get_name = function(_, p22) --[[ Name: get_name ]] --[[ Line: 72 ]]
            --[[ Upvalues: (copy 1): p_u_18, (copy 2): p_u_17 ]]
            if p22 and p_u_18:count() > 0 then
                return p_u_18:get(1):get_name();
            else
                return p_u_17:count() <= 0 and "???" or p_u_17:get(1):get_name();
            end;
        end;
        return v19;
    end
}
v_u_23.from_table = function(_, p24) --[[ Name: from_table ]] --[[ Line: 84 ]]
    --[[ Upvalues: (copy 1): v_u_23, (copy 2): v_u_6 ]]
    return v_u_23:new(p24.Points, v_u_6.RewardInfo:table_to_list(p24.RewardListStandard), v_u_6.RewardInfo:table_to_list(p24.RewardListVIP));
end;
v15.entry_list_from_table = function(_, p25) --[[ Name: entry_list_from_table ]] --[[ Line: 100 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_23 ]]
    local v26 = v_u_2:new()
    for v27 = 1, #p25 do
        v26:push_back(v_u_23:from_table(p25[v27]))
    end;
    return v26;
end;
v15.entry_list_from_legacy_challengepass_mission_json_tab = function(_, p28) --[[ Name: entry_list_from_legacy_challengepass_mission_json_tab ]] --[[ Line: 110 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_11, (copy 3): v_u_9, (copy 4): v_u_6, (copy 5): v_u_4, (copy 6): v_u_5, (copy 7): v_u_23, (copy 8): v_u_8, (copy 9): v_u_10, (copy 10): v_u_7, (copy 11): v_u_3 ]]
    local v_u_29 = v_u_2:new()
    local v_u_30 = v_u_2:new()
    for v31 = 1, #p28 do
        local v32 = p28[v31]
        if v32.RewardType == v_u_11.RewardType.Dances then
            if v_u_9:singleton():contains_dance_for_id(v32.RewardID) then
                v_u_29:push_back(v_u_6.RewardInfo:new(v_u_6.RewardType.Dance, 1, v32.RewardID))
            end;
        elseif v32.RewardType == v_u_11.RewardType.Material and v_u_4:singleton():get_material_type(v32.RewardID) == v_u_5.Type.FeverIcon then
            v_u_30:push_back(v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, v32.RewardID))
        end;
    end;
    local v_u_33 = v_u_2:new()
    local function f_add_coin_entry(p34, p35, p36) --[[ Name: add_coin_entry ]] --[[ Line: 134 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6 ]]
        v_u_33:push_back(v_u_23:new(p34, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Coins, p35, -1) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Coins, p36, -1) })))
    end;
    local function f_add_star_entry(p37, p38, p39) --[[ Name: add_star_entry ]] --[[ Line: 142 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6 ]]
        v_u_33:push_back(v_u_23:new(p37, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Stars, p38, -1) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Stars, p39, -1) })))
    end;
    local function f_add_small_note_box_entry(p40, p41, p42) --[[ Name: add_small_note_box_entry ]] --[[ Line: 150 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        if p42 == nil then
            p42 = p41
        end;
        v_u_33:push_back(v_u_23:new(p40, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p41, v_u_8:get_small_note_box_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p42, v_u_8:get_small_note_box_id()) })))
    end;
    local function f_add_medium_note_box_entry(p43, p44, p45) --[[ Name: add_medium_note_box_entry ]] --[[ Line: 159 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        if p45 == nil then
            p45 = p44
        end;
        v_u_33:push_back(v_u_23:new(p43, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p44, v_u_8:get_medium_note_box_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p45, v_u_8:get_medium_note_box_id()) })))
    end;
    local function f_add_large_note_box_entry(p46, p47, p48) --[[ Name: add_large_note_box_entry ]] --[[ Line: 168 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        if p48 == nil then
            p48 = p47
        end;
        v_u_33:push_back(v_u_23:new(p46, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p47, v_u_8:get_large_note_box_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p48, v_u_8:get_large_note_box_id()) })))
    end;
    local function f_add_gem_box_entry(p49, p50, p51) --[[ Name: add_gem_box_entry ]] --[[ Line: 177 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        if p51 == nil then
            p51 = p50
        end;
        v_u_33:push_back(v_u_23:new(p49, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p50, v_u_8:get_gem_box_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p51, v_u_8:get_gem_box_id()) })))
    end;
    local function f_add_upgrade_boost_entry(p52, p53, p54) --[[ Name: add_upgrade_boost_entry ]] --[[ Line: 186 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_10 ]]
        if p54 == nil then
            p54 = p53
        end;
        v_u_33:push_back(v_u_23:new(p52, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p53, v_u_10:singleton():get_upgrade_boost_untradeable_material_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p54, v_u_10:singleton():get_upgrade_boost_material_id()) })))
    end;
    local function f_add_upgrade_protect_entry(p55, p56, p57) --[[ Name: add_upgrade_protect_entry ]] --[[ Line: 195 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_10 ]]
        if p57 == nil then
            p57 = p56
        end;
        v_u_33:push_back(v_u_23:new(p55, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p56, v_u_10:singleton():get_upgrade_protect_untradeable_material_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p57, v_u_10:singleton():get_upgrade_protect_material_id()) })))
    end;
    local function f_add_mini_box_1star_entry(p58, p59, p60) --[[ Name: add_mini_box_1star_entry ]] --[[ Line: 204 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        if p60 == nil then
            p60 = p59
        end;
        v_u_33:push_back(v_u_23:new(p58, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p59, v_u_8:get_mini_1star_box_not_tradeable_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p60, v_u_8:get_mini_1star_box_id()) })))
    end;
    local function f_add_mini_box_2star_entry(p61, p62, p63) --[[ Name: add_mini_box_2star_entry ]] --[[ Line: 213 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        if p63 == nil then
            p63 = p62
        end;
        v_u_33:push_back(v_u_23:new(p61, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p62, v_u_8:get_mini_2star_box_not_tradeable_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p63, v_u_8:get_mini_2star_box_id()) })))
    end;
    local function f_add_leaderboard_ticket_entry(p64, p65, p66) --[[ Name: add_leaderboard_ticket_entry ]] --[[ Line: 222 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_7 ]]
        if p66 == nil then
            p66 = p65
        end;
        v_u_33:push_back(v_u_23:new(p64, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p65, v_u_7:get_leaderboard_ticket_material_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, p66, v_u_7:get_leaderboard_ticket_material_id()) })))
    end;
    local function f_add_dance_entry(p67) --[[ Name: add_dance_entry ]] --[[ Line: 231 ]]
        --[[ Upvalues: (copy 1): v_u_29, (copy 2): v_u_33, (ref 3): v_u_23, (ref 4): v_u_2, (ref 5): v_u_6, (ref 6): v_u_8 ]]
        if v_u_29:count() > 0 then
            v_u_33:push_back(v_u_23:new(p67, v_u_29, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, v_u_8:get_dance_box_id()) })))
        else
            v_u_33:push_back(v_u_23:new(p67, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, v_u_8:get_dance_box_not_tradeable_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Stars, 5, -1) })))
        end;
    end;
    local function f_add_icon_entry(p68) --[[ Name: add_icon_entry ]] --[[ Line: 248 ]]
        --[[ Upvalues: (copy 1): v_u_30, (copy 2): v_u_33, (ref 3): v_u_23, (ref 4): v_u_2, (ref 5): v_u_6 ]]
        if v_u_30:count() > 0 then
            v_u_33:push_back(v_u_23:new(p68, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Stars, 1, -1) }), v_u_30))
        else
            v_u_33:push_back(v_u_23:new(p68, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Stars, 1, -1) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.Stars, 5, -1) })))
        end;
    end;
    local function f_add_extended_cut_song_box_normal_entry(p69) --[[ Name: add_extended_cut_song_box_normal_entry ]] --[[ Line: 264 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        v_u_33:push_back(v_u_23:new(p69, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, v_u_8:get_vip_song_normal_box_not_tradeable_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, v_u_8:get_vip_song_normal_box_id()) })))
    end;
    local function f_add_extended_cut_song_box_hard_entry(p70) --[[ Name: add_extended_cut_song_box_hard_entry ]] --[[ Line: 272 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8 ]]
        v_u_33:push_back(v_u_23:new(p70, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, v_u_8:get_vip_song_hard_box_not_tradeable_id()) }), v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, v_u_8:get_vip_song_hard_box_id()) })))
    end;
    local function f_add_challenge_pass_master_entry(p71) --[[ Name: add_challenge_pass_master_entry ]] --[[ Line: 280 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_23, (ref 3): v_u_2, (ref 4): v_u_6 ]]
        v_u_33:push_back(v_u_23:new(p71, v_u_2:new({ v_u_6.RewardInfo:new(v_u_6.RewardType.CraftingMaterials, 1, 366), v_u_6.RewardInfo:new(v_u_6.RewardType.Titles, 1, 121) }), v_u_2:new({})))
    end;
    f_add_coin_entry(100, 50, 100)
    f_add_small_note_box_entry(200, 1, 2)
    f_add_medium_note_box_entry(300, 1, 2)
    f_add_large_note_box_entry(400, 1, 2)
    f_add_star_entry(500, 1, 2)
    f_add_upgrade_protect_entry(600, 1, 2)
    f_add_upgrade_boost_entry(700, 1, 2)
    f_add_gem_box_entry(800, 1, 2)
    f_add_coin_entry(900, 100, 200)
    f_add_small_note_box_entry(1000, 1, 2)
    f_add_medium_note_box_entry(1100, 1, 2)
    f_add_large_note_box_entry(1200, 1, 2)
    f_add_gem_box_entry(1300, 1, 2)
    f_add_upgrade_protect_entry(1400, 1, 2)
    f_add_dance_entry(1500)
    f_add_upgrade_boost_entry(1600, 1, 2)
    f_add_mini_box_1star_entry(1700, 1, 1)
    f_add_coin_entry(1800, 150, 300)
    f_add_star_entry(1900, 1, 2)
    f_add_extended_cut_song_box_normal_entry(2000)
    f_add_small_note_box_entry(2100, 1, 2)
    f_add_medium_note_box_entry(2200, 1, 2)
    f_add_large_note_box_entry(2300, 1, 2)
    f_add_gem_box_entry(2400, 1, 2)
    f_add_upgrade_boost_entry(2500, 1, 2)
    f_add_upgrade_protect_entry(2600, 1, 2)
    f_add_small_note_box_entry(2700, 1, 2)
    f_add_medium_note_box_entry(2800, 1, 2)
    f_add_large_note_box_entry(2900, 1, 2)
    f_add_mini_box_2star_entry(3000, 1, 1)
    f_add_gem_box_entry(3100, 1, 2)
    f_add_upgrade_boost_entry(3200, 1, 2)
    f_add_mini_box_1star_entry(3300, 1, 1)
    f_add_leaderboard_ticket_entry(3400, 1, 2)
    f_add_icon_entry(3500)
    f_add_coin_entry(3600, 150, 300)
    f_add_small_note_box_entry(3700, 1, 2)
    f_add_medium_note_box_entry(3800, 1, 2)
    f_add_large_note_box_entry(3900, 1, 2)
    f_add_extended_cut_song_box_hard_entry(4000)
    f_add_star_entry(4100, 2, 4)
    f_add_small_note_box_entry(4200, 1, 2)
    f_add_medium_note_box_entry(4300, 1, 2)
    f_add_large_note_box_entry(4400, 1, 2)
    f_add_leaderboard_ticket_entry(4500, 1, 2)
    f_add_upgrade_boost_entry(4600, 1, 2)
    f_add_small_note_box_entry(4700, 1, 2)
    f_add_medium_note_box_entry(4800, 1, 2)
    f_add_large_note_box_entry(4900, 1, 2)
    f_add_leaderboard_ticket_entry(5000, 1, 2)
    f_add_leaderboard_ticket_entry(6000, 1, 0)
    f_add_leaderboard_ticket_entry(7000, 1, 0)
    f_add_challenge_pass_master_entry(7250)
    f_add_leaderboard_ticket_entry(8000, 1, 0)
    f_add_leaderboard_ticket_entry(9000, 1, 0)
    f_add_leaderboard_ticket_entry(10000, 1, 0)
    local v72 = 0
    for v73 = 1, v_u_33:count() do
        local v74 = v_u_33:get(v73)
        v_u_3:is_true(v72 < v74:get_points())
        v72 = v74:get_points()
        v74:get_reward_list_standard():remove_if(function(p75) --[[ Line: 366 ]]
            return p75:get_amount() == 0;
        end)
        v74:get_reward_list_vip():remove_if(function(p76) --[[ Line: 369 ]]
            return p76:get_amount() == 0;
        end)
    end;
    return v_u_33;
end;
return v15;
