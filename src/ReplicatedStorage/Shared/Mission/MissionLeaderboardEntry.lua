-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
local v_u_6 = {
    ["INVALID_PLAYER_ID"] = 0,
    ["LeaderboardType"] = {
        ["TotalScore"] = 1,
        ["GearPower"] = 2
    }
}
local v_u_7 = v_u_2:new()
for _, v8 in pairs(v_u_6.LeaderboardType) do
    v_u_7:push_back(v8)
end;
v_u_6.LeaderboardType.all_types_list = function(_) --[[ Name: all_types_list ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    return v_u_7;
end;
v_u_6.LeaderboardType.type_to_name = function(_, p9) --[[ Name: type_to_name ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return p9 == v_u_6.LeaderboardType.TotalScore and "Total Score" or (p9 == v_u_6.LeaderboardType.GearPower and "Lowest Gear Power" or "");
end;
local v_u_10 = {}
v_u_6.MissionLeaderboardEntryPlayer = v_u_10
v_u_10.new = function(_) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1 ]]
    local v13 = {
        ["from_table"] = function(p11, p12) --[[ Name: from_table ]] --[[ Line: 84 ]]
            p11:set_name(p12.Name)
            p11:set_id(p12.ID)
            p11:set_score(p12.Score)
            p11:set_naked_score(p12.NakedScore)
            p11:set_gear_power(p12.GearPower)
            return p11;
        end
    }
    local v_u_14 = ""
    local l_INVALID_PLAYER_ID_0 = v_u_6.INVALID_PLAYER_ID
    local v_u_15 = 0
    local v_u_16 = 0
    local v_u_17 = 0
    v13.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        return v_u_14;
    end;
    v13.set_name = function(_, p18) --[[ Name: set_name ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_14 ]]
        v_u_1:is_string(p18)
        v_u_14 = p18
    end;
    v13.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): l_INVALID_PLAYER_ID_0 ]]
        return l_INVALID_PLAYER_ID_0;
    end;
    v13.set_id = function(_, p19) --[[ Name: set_id ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): l_INVALID_PLAYER_ID_0 ]]
        v_u_1:is_int(p19)
        l_INVALID_PLAYER_ID_0 = p19
    end;
    v13.get_score = function(_) --[[ Name: get_score ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        return v_u_15;
    end;
    v13.set_score = function(_, p20) --[[ Name: set_score ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_15 ]]
        v_u_1:is_int(p20)
        v_u_15 = p20
    end;
    v13.get_naked_score = function(_) --[[ Name: get_naked_score ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16;
    end;
    v13.set_naked_score = function(_, p21) --[[ Name: set_naked_score ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_16 ]]
        v_u_1:is_int(p21)
        v_u_16 = p21
    end;
    v13.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        return v_u_17;
    end;
    v13.set_gear_power = function(_, p22) --[[ Name: set_gear_power ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_17 ]]
        v_u_1:is_int(p22)
        v_u_17 = p22 < 0 and 0 or p22
    end;
    v13.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): l_INVALID_PLAYER_ID_0, (ref 3): v_u_15, (ref 4): v_u_16, (ref 5): v_u_17 ]]
        return {
            ["Name"] = v_u_14,
            ["ID"] = l_INVALID_PLAYER_ID_0,
            ["Score"] = v_u_15,
            ["NakedScore"] = v_u_16,
            ["GearPower"] = v_u_17
        };
    end;
    return v13;
end;
v_u_10.from_table = function(_, p23) --[[ Name: from_table ]] --[[ Line: 96 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    return v_u_10:new():from_table(p23);
end;
v_u_6.new = function(_) --[[ Name: new ]] --[[ Line: 100 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_2 ]]
    local v24 = {}
    local v_u_25 = v_u_10:new()
    local v_u_26 = false
    local v_u_27 = v_u_10:new()
    local v_u_28 = false
    local v_u_29 = v_u_10:new()
    local v_u_30 = false
    local v_u_31 = v_u_10:new()
    local v_u_32 = false
    v24.get_players_list = function(_) --[[ Name: get_players_list ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_26, (copy 3): v_u_25, (ref 4): v_u_28, (copy 5): v_u_27, (ref 6): v_u_30, (copy 7): v_u_29, (ref 8): v_u_32, (copy 9): v_u_31 ]]
        local v33 = v_u_2:new()
        if v_u_26 then
            v33:push_back(v_u_25)
        end;
        if v_u_28 then
            v33:push_back(v_u_27)
        end;
        if v_u_30 then
            v33:push_back(v_u_29)
        end;
        if v_u_32 then
            v33:push_back(v_u_31)
        end;
        return v33;
    end;
    v24.get_top_player_by_leaderboard_type = function(p34, _) --[[ Name: get_top_player_by_leaderboard_type ]] --[[ Line: 121 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        local v35 = v_u_25
        for _, v36 in p34:get_players_list():key_itr() do
            if v36:get_score() > v35:get_score() then
                v35 = v36
            end;
        end;
        return v35;
    end;
    v24.get_player_by_slot = function(_, p37) --[[ Name: get_player_by_slot ]] --[[ Line: 131 ]]
        --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_27, (copy 3): v_u_29, (copy 4): v_u_31 ]]
        if p37 == 1 then
            return v_u_25;
        elseif p37 == 2 then
            return v_u_27;
        elseif p37 == 3 then
            return v_u_29;
        elseif p37 == 4 then
            return v_u_31;
        else
            return nil;
        end;
    end;
    v24.set_has_player_in_slot = function(_, p38) --[[ Name: set_has_player_in_slot ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_28, (ref 3): v_u_30, (ref 4): v_u_32 ]]
        if p38 == 1 then
            v_u_26 = true
        end;
        if p38 == 2 then
            v_u_28 = true
        end;
        if p38 == 3 then
            v_u_30 = true
        end;
        if p38 == 4 then
            v_u_32 = true
        end;
    end;
    v24.contains_playerid = function(_, p39) --[[ Name: contains_playerid ]] --[[ Line: 146 ]]
        --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_27, (copy 3): v_u_29, (copy 4): v_u_31 ]]
        return v_u_25:get_id() == p39 and true or (v_u_27:get_id() == p39 and true or (v_u_29:get_id() == p39 and true or v_u_31:get_id() == p39));
    end;
    local v_u_40 = false
    local v_u_41 = ""
    v24.get_playerid_hash = function(p42) --[[ Name: get_playerid_hash ]] --[[ Line: 156 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_2, (ref 3): v_u_41 ]]
        if v_u_40 ~= true then
            local v43 = v_u_2:new()
            for _, v44 in p42:get_players_list():key_itr() do
                v43:push_back(v44:get_id())
            end;
            v43:sort(function(p45, p46) --[[ Line: 162 ]]
                return p45 < p46;
            end)
            local v47 = ""
            for _, v48 in v43:key_itr() do
                v47 = v47 .. tostring(v48) .. "_"
            end;
            v_u_41 = v47
            v_u_40 = true
        end;
        return v_u_41;
    end;
    local v_u_49 = false
    local v_u_50 = 0
    v24.get_calculated_total_score = function(p51) --[[ Name: get_calculated_total_score ]] --[[ Line: 175 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_50 ]]
        if v_u_49 ~= true then
            v_u_50 = 0
            for _, v52 in p51:get_players_list():key_itr() do
                v_u_50 = v_u_50 + v52:get_score()
            end;
            v_u_49 = true
        end;
        return v_u_50;
    end;
    local v_u_53 = false
    local v_u_54 = 0
    v24.get_calculated_total_gear_power = function(p55) --[[ Name: get_calculated_total_gear_power ]] --[[ Line: 188 ]]
        --[[ Upvalues: (ref 1): v_u_53, (ref 2): v_u_54 ]]
        if v_u_53 ~= true then
            v_u_54 = 0
            for _, v56 in p55:get_players_list():key_itr() do
                v_u_54 = v_u_54 + v56:get_gear_power()
            end;
            v_u_53 = true
        end;
        return v_u_54;
    end;
    v24.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 199 ]]
        --[[ Upvalues: (copy 1): v_u_25, (ref 2): v_u_26, (copy 3): v_u_27, (ref 4): v_u_28, (copy 5): v_u_29, (ref 6): v_u_30, (copy 7): v_u_31, (ref 8): v_u_32 ]]
        return {
            ["Player1"] = v_u_25:to_table(),
            ["HasPlayer1"] = v_u_26,
            ["Player2"] = v_u_27:to_table(),
            ["HasPlayer2"] = v_u_28,
            ["Player3"] = v_u_29:to_table(),
            ["HasPlayer3"] = v_u_30,
            ["Player4"] = v_u_31:to_table(),
            ["HasPlayer4"] = v_u_32
        };
    end;
    v24.from_table = function(p57, p58) --[[ Name: from_table ]] --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): v_u_25, (ref 2): v_u_26, (copy 3): v_u_27, (ref 4): v_u_28, (copy 5): v_u_29, (ref 6): v_u_30, (copy 7): v_u_31, (ref 8): v_u_32, (ref 9): v_u_49, (ref 10): v_u_53 ]]
        v_u_25:from_table(p58.Player1)
        v_u_26 = p58.HasPlayer1
        v_u_27:from_table(p58.Player2)
        v_u_28 = p58.HasPlayer2
        v_u_29:from_table(p58.Player3)
        v_u_30 = p58.HasPlayer3
        v_u_31:from_table(p58.Player4)
        v_u_32 = p58.HasPlayer4
        v_u_49 = false
        v_u_53 = false
        return p57;
    end;
    return v24;
end;
v_u_6.from_table = function(_, p59) --[[ Name: from_table ]] --[[ Line: 229 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6:new():from_table(p59);
end;
v_u_6.table_to_list = function(_, p60) --[[ Name: table_to_list ]] --[[ Line: 233 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6 ]]
    local v61 = v_u_2:new()
    for _, v62 in pairs(p60) do
        v61:push_back(v_u_6:from_table(v62))
    end;
    return v61;
end;
v_u_6.list_to_table = function(_, p63) --[[ Name: list_to_table ]] --[[ Line: 241 ]]
    local v64 = {}
    for _, v65 in p63:key_itr() do
        v64[#v64 + 1] = v65:to_table()
    end;
    return v64;
end;
v_u_6.LeaderboardInfo = {}
v_u_6.LeaderboardInfo.PLACE_NOT_FOUND = 99999
v_u_6.LeaderboardInfo.new = function(_, p_u_66, p_u_67, p_u_68, p_u_69) --[[ Name: new ]] --[[ Line: 251 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_3 ]]
    v_u_1:is_enum_member(p_u_66, v_u_6.LeaderboardType)
    v_u_1:is_true(v_u_3:singleton():contains_key(p_u_67))
    v_u_1:is_int(p_u_68)
    v_u_1:is_table(p_u_69)
    local v70 = {}
    v70.get_leaderboard_type = function(_) --[[ Name: get_leaderboard_type ]] --[[ Line: 259 ]]
        --[[ Upvalues: (copy 1): p_u_66 ]]
        return p_u_66;
    end;
    v70.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 260 ]]
        --[[ Upvalues: (copy 1): p_u_67 ]]
        return p_u_67;
    end;
    v70.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 261 ]]
        --[[ Upvalues: (copy 1): p_u_68 ]]
        return p_u_68;
    end;
    v70.get_entry_list = function(_) --[[ Name: get_entry_list ]] --[[ Line: 262 ]]
        --[[ Upvalues: (copy 1): p_u_69 ]]
        return p_u_69;
    end;
    v70.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 264 ]]
        --[[ Upvalues: (copy 1): p_u_66, (copy 2): p_u_67, (copy 3): p_u_68, (ref 4): v_u_6, (copy 5): p_u_69 ]]
        return {
            ["LeaderboardType"] = p_u_66,
            ["SongKey"] = p_u_67,
            ["WeekID"] = p_u_68,
            ["EntryList"] = v_u_6:list_to_table(p_u_69)
        };
    end;
    v70.get_playerid_place = function(_, p71) --[[ Name: get_playerid_place ]] --[[ Line: 273 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_69 ]]
        local l_PLACE_NOT_FOUND_0 = v_u_6.LeaderboardInfo.PLACE_NOT_FOUND
        for v72 = 1, p_u_69:count() do
            if p_u_69:get(v72):contains_playerid(p71) then
                return v72;
            end;
        end;
        return l_PLACE_NOT_FOUND_0;
    end;
    return v70;
end;
v_u_6.LeaderboardInfo.from_table = function(_, p73) --[[ Name: from_table ]] --[[ Line: 288 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6.LeaderboardInfo:new(p73.LeaderboardType, p73.SongKey, p73.WeekID, v_u_6:table_to_list(p73.EntryList));
end;
v_u_6.LeaderboardInfo.list_to_table = function(_, p74) --[[ Name: list_to_table ]] --[[ Line: 297 ]]
    local v75 = {}
    for _, v76 in p74:key_itr() do
        v75[#v75 + 1] = v76:to_table()
    end;
    return v75;
end;
v_u_6.LeaderboardInfo.table_to_list = function(_, p77) --[[ Name: table_to_list ]] --[[ Line: 305 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6 ]]
    local v78 = v_u_2:new()
    for _, v79 in pairs(p77) do
        v78:push_back(v_u_6.LeaderboardInfo:from_table(v79))
    end;
    return v78;
end;
v_u_6.leaderboard_place_to_reward_desc_info_list = function(_, p80, p81) --[[ Name: leaderboard_place_to_reward_desc_info_list ]] --[[ Line: 313 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (copy 3): v_u_4, (copy 4): v_u_5 ]]
    local v82 = v_u_2:new()
    if p80 <= 0 then
        return v82;
    else
        if p81:contains(v_u_6.LeaderboardType.TotalScore) then
            local v83 = p81:get(v_u_6.LeaderboardType.TotalScore)
            if v83 <= 200 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 94))
            end;
            if v83 <= 100 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 95))
            end;
            if v83 <= 25 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 96))
            end;
            if v83 <= 5 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 97))
            end;
            if v83 == 1 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 98))
            end;
        end;
        if p81:contains(v_u_6.LeaderboardType.GearPower) then
            local v84 = p81:get(v_u_6.LeaderboardType.GearPower)
            if v84 <= 200 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 101))
            end;
            if v84 <= 100 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 102))
            end;
            if v84 <= 25 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 103))
            end;
            if v84 <= 5 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 104))
            end;
            if v84 == 1 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 105))
            end;
        end;
        if p80 <= 10 then
            v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.CraftingMaterials, 4, v_u_5:get_leaderboard_ticket_material_id()))
            return v82;
        elseif p80 <= 50 then
            v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.CraftingMaterials, 3, v_u_5:get_leaderboard_ticket_material_id()))
            return v82;
        elseif p80 <= 100 then
            v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.CraftingMaterials, 2, v_u_5:get_leaderboard_ticket_material_id()))
            return v82;
        else
            if p80 <= 200 then
                v82:push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.CraftingMaterials, 1, v_u_5:get_leaderboard_ticket_material_id()))
            end;
            return v82;
        end;
    end;
end;
return v_u_6;
