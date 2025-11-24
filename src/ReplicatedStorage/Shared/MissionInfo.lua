-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_2 = require(game.ReplicatedStorage.Shared.MissionType)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
local v8 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.EditorGame.Data.EditorGamePlayInfo)
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
v11:require_shared(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14 ]]
    v_u_12 = require(game.ReplicatedStorage.Shared.GuildUtil)
    v_u_13 = require(game.ReplicatedStorage.Shared.Mission.ScaledScoreMissionUtil)
    v_u_14 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
end)
local v_u_40 = {
    ["RewardType"] = {
        ["Coins"] = 0,
        ["Stars"] = 1,
        ["Gems"] = 2,
        ["Tokens"] = 3,
        ["Special"] = 4,
        ["UseRewardDescriptionInfo"] = 5
    },
    ["MissionWriteInfo"] = {},
    ["missiondata_empty"] = function(_) --[[ Name: missiondata_empty ]] --[[ Line: 45 ]]
        return {
            ["Day"] = 0,
            ["Week"] = 0,
            ["Daily"] = {},
            ["Weekly"] = {}
        };
    end,
    ["get_mission_hint_text"] = function(_, p15) --[[ Name: get_mission_hint_text ]] --[[ Line: 171 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_10 ]]
        local l_Type_0 = p15.Type
        if l_Type_0 == v_u_2.Cheer then
            return string.format("To cheer, spectate a player from the player list in the social menu.");
        elseif l_Type_0 == v_u_2.NoteMachine then
            return string.format("Get crafting materials to make songs and gear upgrades from the Note Machine.");
        elseif l_Type_0 == v_u_2.StarMachine then
            return string.format("Acquire new songs and additional copies from the Song Machine.");
        elseif l_Type_0 == v_u_2.UpgradeGear then
            return string.format("Get crafting materials from trading and the Note Machine.");
        elseif l_Type_0 == v_u_2.CombineSong then
            return string.format("Combine songs in the songs menu.");
        else
            return l_Type_0 ~= v_u_2.LikeCustomMap and "" or string.format("Must play for %d seconds or longer, and cannot like your own map.", v_u_10:get_minimum_reward_time_play_sec());
        end;
    end,
    ["render_difficulty_image"] = function(_, p16, p17) --[[ Name: render_difficulty_image ]] --[[ Line: 196 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if p17 == v_u_1.Star then
            p16.Image = "rbxassetid://1138402008"
            return;
        elseif p17 == v_u_1.Pro then
            p16.Image = "rbxassetid://1138402010"
            return;
        elseif p17 == v_u_1.Amateur then
            p16.Image = "rbxassetid://1138400518"
            return;
        elseif p17 == v_u_1.Novice then
            p16.Image = "rbxassetid://1138402011"
        else
            p16.Image = "rbxassetid://1138400519"
        end;
    end,
    ["playerblob_missionid_get_count"] = function(_, p18, p19, p20) --[[ Name: playerblob_missionid_get_count ]] --[[ Line: 273 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        local v21 = 0
        local v22 = nil
        if p19 == v_u_7.Daily then
            v22 = p18.DayMissionProgress
        elseif p19 == v_u_7.Weekly then
            v22 = p18.WeekMissionProgress
        end;
        if v22 then
            for v23 = 1, #v22 do
                local v24 = v22[v23]
                if v24.MissionID == p20 then
                    v21 = v24.Count
                end;
            end;
        end;
        return v21;
    end,
    ["playerblob_get_missionid_completed"] = function(_, p25, p26, p27) --[[ Name: playerblob_get_missionid_completed ]] --[[ Line: 364 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_5 ]]
        local v28
        if p26 == v_u_7.Daily then
            v28 = p25.DayMissionProgress
        elseif p26 == v_u_7.Weekly then
            v28 = p25.WeekMissionProgress
        else
            v_u_5:warnf("MissionInfo:playerblob_get_missionid_completed invalid timeframe(%s)", (tostring(p26)))
            v28 = {}
        end;
        for v29 = 1, #v28 do
            local v30 = v28[v29]
            if v30.MissionID == p27 and v30.Completed == true then
                return true;
            end;
        end;
        return false;
    end,
    ["mission_get_id"] = function(_, p31) --[[ Name: mission_get_id ]] --[[ Line: 387 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        if p31.ID == nil then
            v_u_5:errf("mission no ID")
        end;
        return p31.ID;
    end,
    ["mission_get_type"] = function(_, p32) --[[ Name: mission_get_type ]] --[[ Line: 391 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        if p32.Type == nil then
            v_u_5:errf("mission no type")
        end;
        return p32.Type;
    end,
    ["mission_get_difficulty"] = function(_, p33) --[[ Name: mission_get_difficulty ]] --[[ Line: 395 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        if p33.Difficulty == nil then
            v_u_5:errf("mission no difficulty")
        end;
        return p33.Difficulty;
    end,
    ["invalid_mission_id"] = function(_) --[[ Name: invalid_mission_id ]] --[[ Line: 399 ]]
        return -1;
    end,
    ["mission_get_targetsong"] = function(_, p34) --[[ Name: mission_get_targetsong ]] --[[ Line: 400 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        if p34.TargetSong == nil then
            return v_u_3:invalid_songkey();
        else
            return p34.TargetSong;
        end;
    end,
    ["mission_get_count"] = function(_, p35) --[[ Name: mission_get_count ]] --[[ Line: 404 ]]
        return p35.Count == nil and 1 or p35.Count;
    end,
    ["mission_get_playersrequired"] = function(_, p36) --[[ Name: mission_get_playersrequired ]] --[[ Line: 408 ]]
        return p36.PlayersRequired == nil and 1 or p36.PlayersRequired;
    end,
    ["playerblob_get_mission_difficulty"] = function(_, p37) --[[ Name: playerblob_get_mission_difficulty ]] --[[ Line: 412 ]]
        return p37.MissionRank;
    end,
    ["playerblob_upgrade_mission_difficulty"] = function(_, p38) --[[ Name: playerblob_upgrade_mission_difficulty ]] --[[ Line: 426 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        p38.MissionRank = v_u_1:difficulty_upgrade(p38.MissionRank)
    end,
    ["mission_difficulty_to_recommended_gearpower"] = function(_, p39) --[[ Name: mission_difficulty_to_recommended_gearpower ]] --[[ Line: 430 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return p39 == v_u_1.Star and 500 or (p39 == v_u_1.Pro and 250 or (p39 == v_u_1.Amateur and 75 or (p39 == v_u_1.Novice and 25 or 0)));
    end
}
v_u_40.MissionWriteInfo.new = function(_, p_u_41, p_u_42, p_u_43, p_u_44) --[[ Name: new ]] --[[ Line: 36 ]]
    local v45 = {}
    v45.get_timeframe = function(_) --[[ Name: get_timeframe ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): p_u_41 ]]
        return p_u_41;
    end;
    v45.get_mission_id = function(_) --[[ Name: get_mission_id ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): p_u_42 ]]
        return p_u_42;
    end;
    v45.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): p_u_43 ]]
        return p_u_43;
    end;
    v45.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): p_u_44 ]]
        return p_u_44;
    end;
    return v45;
end;
v_u_40.mission_is_any_song = function(_, p46) --[[ Name: mission_is_any_song ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_40 ]]
    return v_u_40:mission_get_targetsong(p46) <= 0;
end;
v_u_40.render_placeholder_cover_art = function(_, p47, p48, p49) --[[ Name: render_placeholder_cover_art ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_40, (copy 2): v_u_2 ]]
    if v_u_40:mission_get_type(p47) == v_u_2.Cheer then
        p48.Image = "rbxassetid://791944285"
    elseif v_u_40:mission_get_type(p47) == v_u_2.NoteMachine then
        p48.Image = "rbxassetid://1530931968"
    elseif v_u_40:mission_get_type(p47) == v_u_2.StarMachine then
        p48.Image = "rbxassetid://7123568029"
    elseif v_u_40:mission_get_type(p47) == v_u_2.UpgradeGear then
        p48.Image = "rbxassetid://1520323733"
    elseif v_u_40:mission_get_type(p47) == v_u_2.CombineSong then
        p48.Image = "rbxassetid://792162284"
    else
        p48.Image = "rbxassetid://1138398505"
    end;
    p49.Visible = false
end;
v_u_40.get_mission_description_text = function(_, p50) --[[ Name: get_mission_description_text ]] --[[ Line: 82 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): v_u_40, (copy 5): v_u_4, (ref 6): v_u_13 ]]
    local l_Count_0 = p50.Count
    local v51 = l_Count_0 == nil and 1 or l_Count_0
    local l_PlayersRequired_0 = p50.PlayersRequired
    local v52 = l_PlayersRequired_0 == nil and 1 or l_PlayersRequired_0
    local v53 = not v_u_3:singleton():contains_key(p50.TargetSong) and "any song" or string.format("\"%s\"", v_u_3:singleton():get_title_for_key(p50.TargetSong))
    local l_Type_1 = p50.Type
    if l_Type_1 == v_u_2.CompleteMatch then
        if v51 == 1 then
            if v52 == 1 then
                return string.format("Play %s once.", v53);
            else
                return string.format("Play %s in a match with %d or more players.", v53, v52);
            end;
        elseif v52 == 1 then
            return string.format("Play %s %d times.", v53, v51);
        else
            return string.format("Play %s %d times in a match with %d or more players.", v53, v51, v52);
        end;
    elseif l_Type_1 == v_u_2.WinMatch then
        if v51 == 1 then
            return string.format("Win playing %s in a match with %d or more players.", v53, v52);
        else
            return string.format("Win %d times playing %s in a match with %d or more players.", v51, v53, v52);
        end;
    elseif l_Type_1 == v_u_2.Score then
        if v52 == 1 then
            return string.format("Score %s or more playing %s.%s", v_u_6:comma_value(v51), v53, v_u_40:mission_get_required_gearpower_str(p50));
        else
            return string.format("Score %s or more playing %s in a match with %d or more players.%s", v_u_6:comma_value(v51), v53, v52, v_u_40:mission_get_required_gearpower_str(p50));
        end;
    elseif l_Type_1 == v_u_2.Rank then
        local v54 = v_u_4:get_rank_value_name((v_u_4:index_to_rank_value(v51)))
        if v52 == 1 then
            return string.format("Get a rank of %s or better playing %s.", v54, v53);
        else
            return string.format("Get a rank of %s or better playing %s in a match with %d or more players.", v54, v53, v52);
        end;
    elseif l_Type_1 == v_u_2.Cheer then
        return string.format("Cheer any other %d times.", v51);
    elseif l_Type_1 == v_u_2.NoteMachine then
        return string.format("Spin the Note Machine %d times.", v51);
    elseif l_Type_1 == v_u_2.StarMachine then
        return string.format("Spin the Song Machine %d times.", v51);
    elseif l_Type_1 == v_u_2.UpgradeGear then
        return string.format("Upgrade your gear from the crafting menu %d time(s).", v51);
    elseif l_Type_1 == v_u_2.CombineSong then
        return string.format("Combine 5 copies of any song to get its hard mode %d time(s).", v51);
    elseif l_Type_1 == v_u_2.PointTotal then
        return string.format("Score %s or more combined among all players in a match playing %s.%s", v_u_6:comma_value(v51), v53, v_u_40:mission_get_required_gearpower_str(p50));
    elseif l_Type_1 == v_u_2.ScaledScore then
        return string.format("Play %s. (Required accuracy: %.2f%% or higher)", v53, v_u_13:mission_difficulty_to_required_accuracy(v_u_40:mission_get_difficulty(p50)) * 100);
    elseif l_Type_1 == v_u_2.NoMiss then
        return string.format("CHALLENGE: Complete %s with no misses.", v53);
    else
        return l_Type_1 ~= v_u_2.LikeCustomMap and "???" or string.format("Play and like %d custom map(s).", v51);
    end;
end;
local v_u_55 = v8:new({
    [v_u_1.Beginner] = "http://www.roblox.com/asset/?id=6423425381",
    [v_u_1.Novice] = "http://www.roblox.com/asset/?id=6423426034",
    [v_u_1.Amateur] = "http://www.roblox.com/asset/?id=6423426306",
    [v_u_1.Pro] = "http://www.roblox.com/asset/?id=6423426592",
    [v_u_1.Star] = "http://www.roblox.com/asset/?id=6423426871"
})
v_u_40.difficulty_to_icon = function(_, p56) --[[ Name: difficulty_to_icon ]] --[[ Line: 218 ]]
    --[[ Upvalues: (copy 1): v_u_55 ]]
    return v_u_55:get(p56);
end;
v_u_40.missiondata_foreach = function(_, p57, p58, p59, p60) --[[ Name: missiondata_foreach ]] --[[ Line: 220 ]]
    --[[ Upvalues: (copy 1): v_u_40, (copy 2): v_u_7, (copy 3): v_u_9 ]]
    local v63 = p60 == nil and function(p61, p62) --[[ Line: 222 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40:mission_get_id(p62) - v_u_40:mission_get_id(p61);
    end or p60
    local v64
    if p58 == v_u_7.Weekly then
        v64 = p57.Weekly
    else
        v64 = p57.Daily
    end;
    local v65 = v_u_9:new()
    v65:push_back_table_list(v64)
    v65:sort(v63)
    for _, v66 in v65:key_itr() do
        if p59(v66) == true then
            break;
        end;
    end;
end;
v_u_40.playerblob_missiondata_available_foreach = function(_, p_u_67, p68, p_u_69, p_u_70, p71) --[[ Name: playerblob_missiondata_available_foreach ]] --[[ Line: 246 ]]
    --[[ Upvalues: (copy 1): v_u_40 ]]
    v_u_40:missiondata_foreach(p68, p_u_69, function(p72) --[[ Line: 247 ]]
        --[[ Upvalues: (ref 1): v_u_40, (copy 2): p_u_67, (copy 3): p_u_69, (copy 4): p_u_70 ]]
        local v73
        if v_u_40:playerblob_get_missionid_completed(p_u_67, p_u_69, v_u_40:mission_get_id(p72)) == false and v_u_40:playerblob_get_mission_difficulty(p_u_67) >= v_u_40:mission_get_difficulty(p72) then
            v73 = p_u_70(p72)
        else
            v73 = false
        end;
        return v73;
    end, p71)
end;
v_u_40.missiondata_get_mission_of_id_and_timeframe = function(_, p74, p75, p76) --[[ Name: missiondata_get_mission_of_id_and_timeframe ]] --[[ Line: 257 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_40 ]]
    local v77
    if p75 == v_u_7.Weekly then
        v77 = p74.Weekly
    else
        v77 = p74.Daily
    end;
    for v78 = 1, #v77 do
        local v79 = v77[v78]
        if v_u_40:mission_get_id(v79) == p76 then
            return v79;
        end;
    end;
    return nil;
end;
local function f_playerblob_get_create_missionprogress_of_id(p80, p81) --[[ Name: playerblob_get_create_missionprogress_of_id ]] --[[ Line: 293 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_5, (copy 3): v_u_9 ]]
    local v82 = p81:get_timeframe()
    local v83 = p81:get_mission_id()
    local v84 = p81:get_day_id()
    local v85 = p81:get_week_id()
    local v86
    if v82 == v_u_7.Daily then
        v86 = p80.DayMissionProgress
    else
        v86 = v82 ~= v_u_7.Weekly and {} or p80.WeekMissionProgress
    end;
    for v87 = 1, #v86 do
        local v88 = v86[v87]
        if v88.MissionID == v83 then
            local v89 = true
            if v82 == v_u_7.Daily then
                v89 = v88.DayID == v84
            elseif v82 == v_u_7.Weekly then
                v89 = v88.WeekID == v85
            end;
            if v89 then
                return v88, v86;
            end;
            v_u_5:warnf("playerblob_get_create_missionprogress_of_id day_ok false")
            v_u_9:new(v86):remove_at(v87)
            break;
        end;
    end;
    local v90 = {
        ["MissionID"] = v83,
        ["Count"] = 0,
        ["Completed"] = false
    }
    if v82 == v_u_7.Daily then
        v90.DayID = v84
    elseif v82 == v_u_7.Weekly then
        v90.WeekID = v85
    end;
    v86[#v86 + 1] = v90
    return v90, v86;
end;
v_u_40.playerblob_missionid_set_count = function(_, p91, p92, p93) --[[ Name: playerblob_missionid_set_count ]] --[[ Line: 342 ]]
    --[[ Upvalues: (copy 1): f_playerblob_get_create_missionprogress_of_id ]]
    f_playerblob_get_create_missionprogress_of_id(p91, p92).Count = p93
end;
v_u_40.playerblob_missiondata_missionid_is_completeable = function(_, p94, p95, p96, p_u_97) --[[ Name: playerblob_missiondata_missionid_is_completeable ]] --[[ Line: 346 ]]
    --[[ Upvalues: (copy 1): v_u_40 ]]
    local v_u_98 = nil
    v_u_40:playerblob_missiondata_available_foreach(p94, p95, p96, function(p99) --[[ Line: 348 ]]
        --[[ Upvalues: (ref 1): v_u_40, (copy 2): p_u_97, (ref 3): v_u_98 ]]
        if v_u_40:mission_get_id(p99) == p_u_97 then
            v_u_98 = p99
        end;
    end)
    if v_u_98 == nil then
        return false;
    else
        return v_u_40:mission_get_count(v_u_98) <= v_u_40:playerblob_missionid_get_count(p94, p96, p_u_97);
    end;
end;
v_u_40.playerblob_missionid_set_completed = function(_, p100, p101, p102) --[[ Name: playerblob_missionid_set_completed ]] --[[ Line: 383 ]]
    --[[ Upvalues: (copy 1): f_playerblob_get_create_missionprogress_of_id ]]
    f_playerblob_get_create_missionprogress_of_id(p100, p101).Completed = p102
end;
v_u_40.mission_get_required_gearpower_str = function(_, p103) --[[ Name: mission_get_required_gearpower_str ]] --[[ Line: 444 ]]
    --[[ Upvalues: (copy 1): v_u_40, (copy 2): v_u_2 ]]
    local v104 = v_u_40:mission_get_type(p103)
    if v104 ~= v_u_2.Score and v104 ~= v_u_2.PointTotal then
        return "";
    end;
    local v105 = v_u_40:mission_difficulty_to_recommended_gearpower(v_u_40:mission_get_difficulty(p103))
    return v105 == 0 and "" or string.format(" Recommended gear power: %d or above.", v105);
end;
v_u_40.get_playerblob_mission_progress_text = function(_, p106, p107, p108) --[[ Name: get_playerblob_mission_progress_text ]] --[[ Line: 455 ]]
    --[[ Upvalues: (copy 1): v_u_40, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): v_u_4 ]]
    local v109 = v_u_40:mission_get_count(p107)
    local v110 = v_u_40:playerblob_missionid_get_count(p106, p108, (v_u_40:mission_get_id(p107)))
    local v111 = v_u_40:mission_get_type(p107)
    if v111 == v_u_2.CompleteMatch then
        return string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    elseif v111 == v_u_2.WinMatch then
        return string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    elseif v111 == v_u_2.Score then
        return string.format("%s", v_u_6:comma_value((math.floor(v110))));
    elseif v111 == v_u_2.Rank then
        return string.format("%s", (v_u_4:get_rank_value_name((v_u_4:index_to_rank_value(v110)))));
    elseif v111 == v_u_2.Cheer then
        return string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    elseif v111 == v_u_2.NoteMachine then
        return string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    elseif v111 == v_u_2.StarMachine then
        return string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    elseif v111 == v_u_2.UpgradeGear then
        return string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    elseif v111 == v_u_2.CombineSong then
        return string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    elseif v111 == v_u_2.PointTotal then
        return string.format("%s", v_u_6:comma_value((math.floor(v110))));
    else
        return (v111 == v_u_2.ScaledScore or v111 == v_u_2.NoMiss) and (v110 <= 0 and "Incomplete" or "Complete") or string.format("%d/%d", math.floor(v110), (math.floor(v109)));
    end;
end;
return v_u_40;
