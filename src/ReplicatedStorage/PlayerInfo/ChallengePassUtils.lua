-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_13 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_14 = require(game.ReplicatedStorage.Crafting.CraftingRewardCategories)
local v_u_15 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_16 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_17 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v18 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_19 = nil
v18:require_shared(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_19 ]]
    v_u_19 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
end)
local v_u_27 = {
    ["RewardType"] = {
        ["Coins"] = 0,
        ["Stars"] = 1,
        ["SmallNotes"] = 2,
        ["MediumNotes"] = 3,
        ["LargeNotes"] = 4,
        ["Gems"] = 5,
        ["Tokens"] = 6,
        ["UpgradeProtects"] = 7,
        ["UpgradeBoosts"] = 8,
        ["Songs"] = 9,
        ["Dances"] = 10,
        ["Titles"] = 11,
        ["Gears"] = 12,
        ["Material"] = 13
    },
    ["ActionType"] = {
        ["PlaySong1P"] = 0,
        ["PlaySong2P"] = 1,
        ["PlaySong3P"] = 2,
        ["PlaySong4P"] = 3,
        ["Cheer"] = 4,
        ["CompleteDailyMission"] = 6,
        ["CompleteWeeklyMission"] = 7
    },
    ["ChallengePassMissionState"] = {
        ["Completed"] = 0,
        ["Current"] = 1,
        ["CurrentClaimable"] = 2,
        ["LockedVIP"] = 3,
        ["Locked"] = 4
    },
    ["playerblob_get_challengepass_active_mission"] = function(_, p20, p21) --[[ Name: playerblob_get_challengepass_active_mission ]] --[[ Line: 288 ]]
        local l_ChallengePassActiveTier_0 = p20.ChallengePassActiveTier
        local v22 = -1
        for v23 = 1, p21:count() do
            if l_ChallengePassActiveTier_0 == p21:get(v23):get_index() then
                v22 = v23
                break;
            end;
        end;
        if v22 == -1 then
            return nil, -1;
        else
            return p21:get(v22), v22;
        end;
    end,
    ["validate_playerblob_to_current_month_id"] = function(_, p24, p25) --[[ Name: validate_playerblob_to_current_month_id ]] --[[ Line: 420 ]]
        local v26
        if p24.ChallengePassMonth == p25 then
            v26 = false
        else
            p24.ChallengePassPoints = 0
            p24.ChallengePassMonth = p25
            p24.ChallengePassMonthActivated = false
            p24.ChallengePassActiveTier = 0
            v26 = true
        end;
        return v26;
    end
}
local v_u_28 = {
    [v_u_27.RewardType.Coins] = "Coins",
    [v_u_27.RewardType.Stars] = "Stars",
    [v_u_27.RewardType.SmallNotes] = "Small Notes",
    [v_u_27.RewardType.MediumNotes] = "Medium Notes",
    [v_u_27.RewardType.LargeNotes] = "Large Notes",
    [v_u_27.RewardType.Gems] = "Gems",
    [v_u_27.RewardType.Tokens] = "Tokens",
    [v_u_27.RewardType.UpgradeProtects] = "Upgrade Protects",
    [v_u_27.RewardType.UpgradeBoosts] = "Upgrade Boosts",
    [v_u_27.RewardType.Songs] = "Songs",
    [v_u_27.RewardType.Dances] = "Dances",
    [v_u_27.RewardType.Titles] = "Titles",
    [v_u_27.RewardType.Gears] = "Gears",
    [v_u_27.RewardType.Material] = "Material"
}
v_u_27.reward_type_to_name = function(_, p29) --[[ Name: reward_type_to_name ]] --[[ Line: 62 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_27, (copy 3): v_u_28 ]]
    v_u_3:is_enum_member(p29, v_u_27.RewardType)
    return v_u_28[p29];
end;
local v_u_30 = v1:new():add_table({
    [v_u_27.ActionType.PlaySong1P] = (function() --[[ Line: 80 ]]
        return {
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 82 ]]
                return "Finish match with 1 player";
            end,
            ["get_point_reward"] = function(_) --[[ Name: get_point_reward ]] --[[ Line: 83 ]]
                return 2;
            end
        };
    end)(),
    [v_u_27.ActionType.PlaySong2P] = (function() --[[ Line: 87 ]]
        return {
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 89 ]]
                return "Finish match with 2 players";
            end,
            ["get_point_reward"] = function(_) --[[ Name: get_point_reward ]] --[[ Line: 90 ]]
                return 3;
            end
        };
    end)(),
    [v_u_27.ActionType.PlaySong3P] = (function() --[[ Line: 94 ]]
        return {
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 96 ]]
                return "Finish match with 3 players";
            end,
            ["get_point_reward"] = function(_) --[[ Name: get_point_reward ]] --[[ Line: 97 ]]
                return 4;
            end
        };
    end)(),
    [v_u_27.ActionType.PlaySong4P] = (function() --[[ Line: 101 ]]
        return {
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 103 ]]
                return "Finish match with 4 players";
            end,
            ["get_point_reward"] = function(_) --[[ Name: get_point_reward ]] --[[ Line: 104 ]]
                return 5;
            end
        };
    end)(),
    [v_u_27.ActionType.Cheer] = (function() --[[ Line: 108 ]]
        return {
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 110 ]]
                return "Cheer a player";
            end,
            ["get_point_reward"] = function(_) --[[ Name: get_point_reward ]] --[[ Line: 111 ]]
                return 1;
            end
        };
    end)(),
    [v_u_27.ActionType.CompleteDailyMission] = (function() --[[ Line: 122 ]]
        return {
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 124 ]]
                return "Complete Daily Mission";
            end,
            ["get_point_reward"] = function(_) --[[ Name: get_point_reward ]] --[[ Line: 125 ]]
                return 5;
            end
        };
    end)(),
    [v_u_27.ActionType.CompleteWeeklyMission] = (function() --[[ Line: 129 ]]
        return {
            ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 131 ]]
                return "Complete Weekly Mission";
            end,
            ["get_point_reward"] = function(_) --[[ Name: get_point_reward ]] --[[ Line: 132 ]]
                return 25;
            end
        };
    end)()
})
v_u_27.get_challenge_pass_action_info = function(_) --[[ Name: get_challenge_pass_action_info ]] --[[ Line: 137 ]]
    --[[ Upvalues: (copy 1): v_u_30 ]]
    return v_u_30;
end;
v_u_27.playerblob_apply_action = function(_, p31, p32) --[[ Name: playerblob_apply_action ]] --[[ Line: 141 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_3, (copy 3): v_u_30 ]]
    if v_u_11.UseChallengePassV2 ~= true then
        v_u_3:is_true(v_u_30:contains(p32))
        local v33 = p31.ChallengePassPoints + v_u_30:get(p32):get_point_reward()
        v_u_3:is_int(v33)
        p31.ChallengePassPoints = v33
    end;
end;
local v_u_34 = v1:new():add_set_from_table_list({ v_u_27.RewardType.Coins, v_u_27.RewardType.Stars })
v_u_27.RewardTypesInt = v_u_34
local v_u_35 = v1:new():add_set_from_table_list({
    v_u_27.RewardType.SmallNotes,
    v_u_27.RewardType.MediumNotes,
    v_u_27.RewardType.LargeNotes,
    v_u_27.RewardType.Gems,
    v_u_27.RewardType.Tokens,
    v_u_27.RewardType.UpgradeProtects,
    v_u_27.RewardType.UpgradeBoosts,
    v_u_27.RewardType.Material
})
v_u_27.RewardTypesMaterial = v_u_35
local v_u_36 = v1:new():add_set_from_table_list({ v_u_27.RewardType.Songs })
v_u_27.RewardTypesSong = v_u_36
local v_u_37 = v1:new():add_set_from_table_list({ v_u_27.RewardType.Dances })
v_u_27.RewardTypesDance = v_u_37
local v_u_38 = v1:new():add_set_from_table_list({ v_u_27.RewardType.Titles })
v_u_27.RewardTypesTitle = v_u_38
local v_u_39 = v1:new():add_set_from_table_list({ v_u_27.RewardType.Gears })
v_u_27.RewardTypesGear = v_u_39
local v_u_47 = {
    ["new"] = function(_, p_u_40, p_u_41, p_u_42, p_u_43, p_u_44, p_u_45) --[[ Name: new ]] --[[ Line: 190 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_27, (copy 3): v_u_34, (copy 4): v_u_35, (copy 5): v_u_36, (copy 6): v_u_6, (copy 7): v_u_37, (copy 8): v_u_8, (copy 9): v_u_38, (copy 10): v_u_9, (copy 11): v_u_39, (copy 12): v_u_7, (copy 13): v_u_4 ]]
        local v46 = {}
        v46.get_index = function(_) --[[ Name: get_index ]] --[[ Line: 193 ]]
            --[[ Upvalues: (copy 1): p_u_40 ]]
            return p_u_40;
        end;
        v46.get_point_count = function(_) --[[ Name: get_point_count ]] --[[ Line: 194 ]]
            --[[ Upvalues: (copy 1): p_u_41 ]]
            return p_u_41;
        end;
        v46.get_reward_type = function(_) --[[ Name: get_reward_type ]] --[[ Line: 195 ]]
            --[[ Upvalues: (copy 1): p_u_42 ]]
            return p_u_42;
        end;
        v46.get_reward_count = function(_) --[[ Name: get_reward_count ]] --[[ Line: 196 ]]
            --[[ Upvalues: (copy 1): p_u_43 ]]
            return p_u_43;
        end;
        v46.get_reward_id = function(_) --[[ Name: get_reward_id ]] --[[ Line: 197 ]]
            --[[ Upvalues: (copy 1): p_u_44 ]]
            return p_u_44;
        end;
        v46.get_vip_required = function(_) --[[ Name: get_vip_required ]] --[[ Line: 198 ]]
            --[[ Upvalues: (copy 1): p_u_45 ]]
            return p_u_45;
        end;
        v46.validate = function(_) --[[ Name: validate ]] --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_40, (copy 3): p_u_41, (copy 4): p_u_42, (ref 5): v_u_27, (ref 6): v_u_34, (copy 7): p_u_43, (ref 8): v_u_35, (ref 9): v_u_36, (ref 10): v_u_6, (copy 11): p_u_44, (ref 12): v_u_37, (ref 13): v_u_8, (ref 14): v_u_38, (ref 15): v_u_9, (ref 16): v_u_39, (ref 17): v_u_7, (ref 18): v_u_4, (copy 19): p_u_45 ]]
            v_u_3:is_int(p_u_40)
            v_u_3:is_int(p_u_41)
            v_u_3:is_enum_member(p_u_42, v_u_27.RewardType)
            if v_u_34:contains(p_u_42) then
                v_u_3:is_int(p_u_43)
            elseif not v_u_35:contains(p_u_42) then
                if v_u_36:contains(p_u_42) then
                    v_u_3:is_true(v_u_6:singleton():contains_key(p_u_44))
                elseif v_u_37:contains(p_u_42) then
                    v_u_3:is_true(v_u_8:singleton():contains_dance_for_id(p_u_44))
                elseif v_u_38:contains(p_u_42) then
                    v_u_3:is_true(v_u_9:singleton():contains_title_for_id(p_u_44))
                elseif v_u_39:contains(p_u_42) then
                    v_u_3:is_non_nil(v_u_7:singleton():get_equipment_for_id(p_u_44))
                else
                    v_u_4:errf("unknown reward type")
                end;
            end;
            v_u_3:is_int(p_u_43)
            v_u_3:is_bool(p_u_45)
        end;
        v46:validate()
        return v46;
    end
}
v_u_27.json_to_challengepass_mission_list = function(_, p48) --[[ Name: json_to_challengepass_mission_list ]] --[[ Line: 226 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_47 ]]
    local v49 = v_u_2:new()
    if p48 then
        for v50 = 1, #p48 do
            local v51 = p48[v50]
            v49:push_back(v_u_47:new(v51.Index, v51.PointCount, v51.RewardType, v51.RewardCount, v51.RewardID, v51.VIPRequired))
        end;
    end;
    return v49;
end;
v_u_27.playerblob_get_challengepass_mission_state = function(_, p52, p53, p54) --[[ Name: playerblob_get_challengepass_mission_state ]] --[[ Line: 252 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_27 ]]
    if p53:get_vip_required() and (v_u_10:playerblob_has_vip_for_current_day(p52, p54) ~= true and p52.ChallengePassMonthActivated ~= true) then
        return v_u_27.ChallengePassMissionState.LockedVIP;
    else
        local l_ChallengePassActiveTier_1 = p52.ChallengePassActiveTier
        if p53:get_index() < l_ChallengePassActiveTier_1 then
            return v_u_27.ChallengePassMissionState.Completed;
        elseif l_ChallengePassActiveTier_1 < p53:get_index() then
            return v_u_27.ChallengePassMissionState.Locked;
        elseif p52.ChallengePassPoints < p53:get_point_count() then
            return v_u_27.ChallengePassMissionState.Current;
        else
            return v_u_27.ChallengePassMissionState.CurrentClaimable;
        end;
    end;
end;
v_u_27.playerblob_get_active_mission_point_totals = function(_, p55, p56) --[[ Name: playerblob_get_active_mission_point_totals ]] --[[ Line: 277 ]]
    --[[ Upvalues: (copy 1): v_u_27 ]]
    if p56:count() == 0 then
        return 0, 1;
    end;
    local v57, _ = v_u_27:playerblob_get_challengepass_active_mission(p55, p56)
    if v57 == nil then
        v57 = p56:get(p56:count())
    end;
    return p55.ChallengePassPoints, v57:get_point_count();
end;
v_u_27.get_owned_dance_challengepass_reward = function(_) --[[ Name: get_owned_dance_challengepass_reward ]] --[[ Line: 304 ]]
    --[[ Upvalues: (copy 1): v_u_27 ]]
    return v_u_27.RewardType.Stars, 15, 0;
end;
v_u_27.playerblob_claim_challengepass_mission = function(_, p58, p59, p60) --[[ Name: playerblob_claim_challengepass_mission ]] --[[ Line: 308 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_27, (copy 3): v_u_12, (copy 4): v_u_14, (copy 5): v_u_13, (copy 6): v_u_5, (copy 7): v_u_15, (copy 8): v_u_6, (copy 9): v_u_16, (copy 10): v_u_8, (copy 11): v_u_9, (copy 12): v_u_17, (copy 13): v_u_7, (ref 14): v_u_19, (copy 15): v_u_4 ]]
    local v61 = v_u_10:playerblob_has_vip_for_current_day(p58, p60)
    p58.ChallengePassActiveTier = p59:get_index() + 1
    local v62 = "Got: "
    if p59:get_reward_type() == v_u_27.RewardType.Coins then
        v_u_12:set_coin_currency(p58, v_u_12:get_coin_currency(p58) + p59:get_reward_count())
        return v62 .. string.format("%d Coins", p59:get_reward_count());
    end;
    if p59:get_reward_type() == v_u_27.RewardType.Stars then
        v_u_12:set_star_currency(p58, v_u_12:get_star_currency(p58) + p59:get_reward_count())
        return v62 .. string.format("%d Stars", p59:get_reward_count());
    end;
    if p59:get_reward_type() == v_u_27.RewardType.SmallNotes then
        for v63 = 1, p59:get_reward_count() do
            local v64 = v_u_14:get_small_note_material_ids():random()
            v_u_13:add_crafting_materials_of_id(p58, v64, 1)
            if v63 ~= 1 then
                v62 = v62 .. ", "
            end;
            v62 = v62 .. string.format("%s", v_u_5:singleton():get_material_name(v64))
        end;
        return v62;
    end;
    if p59:get_reward_type() == v_u_27.RewardType.MediumNotes then
        for v65 = 1, p59:get_reward_count() do
            local v66 = v_u_14:get_medium_note_material_ids():random()
            v_u_13:add_crafting_materials_of_id(p58, v66, 1)
            if v65 ~= 1 then
                v62 = v62 .. ", "
            end;
            v62 = v62 .. string.format("%s", v_u_5:singleton():get_material_name(v66))
        end;
        return v62;
    end;
    if p59:get_reward_type() == v_u_27.RewardType.LargeNotes then
        for v67 = 1, p59:get_reward_count() do
            local v68 = v_u_14:get_large_note_material_ids():random()
            v_u_13:add_crafting_materials_of_id(p58, v68, 1)
            if v67 ~= 1 then
                v62 = v62 .. ", "
            end;
            v62 = v62 .. string.format("%s", v_u_5:singleton():get_material_name(v68))
        end;
        return v62;
    end;
    if p59:get_reward_type() == v_u_27.RewardType.Gems then
        for v69 = 1, p59:get_reward_count() do
            local v70 = v_u_14:get_gem_material_ids():random()
            v_u_13:add_crafting_materials_of_id(p58, v70, 1)
            if v69 ~= 1 then
                v62 = v62 .. ", "
            end;
            v62 = v62 .. string.format("%s", v_u_5:singleton():get_material_name(v70))
        end;
        return v62;
    end;
    if p59:get_reward_type() == v_u_27.RewardType.Tokens then
        for v71 = 1, p59:get_reward_count() do
            local v72 = v_u_14:get_crafting_token_material_ids():random()
            v_u_13:add_crafting_materials_of_id(p58, v72, 1)
            if v71 ~= 1 then
                v62 = v62 .. ", "
            end;
            v62 = v62 .. string.format("%s", v_u_5:singleton():get_material_name(v72))
        end;
        return v62;
    end;
    if p59:get_reward_type() == v_u_27.RewardType.UpgradeProtects then
        local v73 = v_u_15:singleton():get_upgrade_protect_material_id()
        v_u_13:add_crafting_materials_of_id(p58, v73, p59:get_reward_count())
        return v62 .. string.format("%s x%d", v_u_5:singleton():get_material_name(v73), p59:get_reward_count());
    end;
    if p59:get_reward_type() == v_u_27.RewardType.UpgradeBoosts then
        local v74 = v_u_15:singleton():get_upgrade_boost_material_id()
        v_u_13:add_crafting_materials_of_id(p58, v74, p59:get_reward_count())
        return v62 .. string.format("%s x%d", v_u_5:singleton():get_material_name(v74), p59:get_reward_count());
    end;
    if p59:get_reward_type() == v_u_27.RewardType.Songs then
        for _ = 1, p59:get_reward_count() do
            v_u_12:add_song(p58, p59:get_reward_id())
        end;
        return v62 .. string.format("%s x%d", v_u_6:singleton():get_title_for_key(p59:get_reward_id()), p59:get_reward_count());
    end;
    if p59:get_reward_type() == v_u_27.RewardType.Dances then
        if v_u_16:get_owned_danceid_to_equipped_dict(p58):contains(p59:get_reward_id()) then
            local _, v75, _ = v_u_27:get_owned_dance_challengepass_reward()
            v_u_12:set_star_currency(p58, v_u_12:get_star_currency(p58) + v75)
            return v62 .. string.format("%d Stars (Owned Dance)", v75);
        end;
        v_u_16:add_owned_danceid(p58, p59:get_reward_id())
        v_u_16:set_danceid_equipped(p58, p59:get_reward_id(), true)
        v_u_16:validate_playerblob(p58)
        return v62 .. string.format("%s (Dance)", v_u_8:singleton():get_dance_name_for_id(p59:get_reward_id()));
    end;
    if p59:get_reward_type() == v_u_27.RewardType.Titles then
        v_u_12:add_title(p58, p59:get_reward_id())
        return v62 .. string.format("%s (Title)", v_u_9:singleton():get_title_name_for_id(p59:get_reward_id()));
    end;
    if p59:get_reward_type() == v_u_27.RewardType.Gears then
        v_u_17:playerblob_grant_equipmentid(p58, p59:get_reward_id())
        return v62 .. v_u_7:singleton():get_equipment_for_id(p59:get_reward_id());
    end;
    if p59:get_reward_type() ~= v_u_27.RewardType.Material then
        v_u_4:errf("ChallengePassUtils:playerblob_claim_challengepass_mission unknown reward_type(%s)", (tostring(p59:get_reward_type())))
        return v62;
    end;
    local v76 = p59:get_reward_id()
    if v61 then
        if v76 == v_u_19:get_vip_song_normal_box_not_tradeable_id() then
            v76 = v_u_19:get_vip_song_normal_box_id()
        end;
        if v76 == v_u_19:get_vip_song_hard_box_not_tradeable_id() then
            v76 = v_u_19:get_vip_song_hard_box_id()
        end;
    end;
    v_u_13:add_crafting_materials_of_id(p58, v76, p59:get_reward_count())
    return v62 .. string.format("%s x%d", v_u_5:singleton():get_material_name(v76), p59:get_reward_count());
end;
return v_u_27;
