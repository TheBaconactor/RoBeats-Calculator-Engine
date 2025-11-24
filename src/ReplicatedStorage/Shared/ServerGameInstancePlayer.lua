-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:03 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_2 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v8 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
v8:require_shared(function() --[[ Line: 14 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11 ]]
    v_u_9 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
    v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
    v_u_11 = require(game.ReplicatedStorage.Pets.PetUtils)
end)
local v_u_28 = {
    ["slot_from_player_info_table_for_id"] = function(_, p12, p13) --[[ Name: slot_from_player_info_table_for_id ]] --[[ Line: 296 ]]
        for v14 = 1, 4 do
            if p12[v14] ~= nil and p12[v14].UserId == p13 then
                return p12[v14].Slot;
            end;
        end;
        return -1;
    end,
    ["playerinfo_to_str"] = function(_, p15) --[[ Name: playerinfo_to_str ]] --[[ Line: 313 ]]
        local v16 = "["
        for v17 = 1, 4 do
            if p15[v17] ~= nil then
                v16 = v16 .. string.format("[%d] = {%s (%d) ready(%s)};", v17, p15[v17].Name, p15[v17].UserId, (tostring(p15[v17].Ready)))
            end;
        end;
        return v16;
    end,
    ["get_gear_info_data_for_playerblob"] = function(_, p18, p19, p20) --[[ Name: get_gear_info_data_for_playerblob ]] --[[ Line: 329 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11 ]]
        return {
            ["GearStats"] = v_u_10:get_playerblob_statsdict(p18, p19, p20),
            ["Equipped"] = v_u_10:playerblob_get_equipped_info(p18),
            ["DisplayPets"] = v_u_11:get_playerblob_displaypet_table(p18)
        };
    end,
    ["copy_icon_and_title_from_playerblob"] = function(_, p21, p22, p23, p24) --[[ Name: copy_icon_and_title_from_playerblob ]] --[[ Line: 341 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_7 ]]
        local v25, _ = v_u_6:playerblob_get_chat_icon(p22)
        p21._icon = v25
        local v26 = v_u_7:singleton():get_title_for_id(p22.CurrentTitleID)
        local v27
        if v26 and v26:is_visible() then
            if p22.CurrentTitleID == v_u_7:singleton():get_guild_title_id() then
                v27 = not (p23 and p24) and "Team" or string.format("Team \'%s\'", p24:get_name())
            else
                v27 = v26:get_name()
            end;
        else
            v27 = ""
        end;
        p21._title = v27
        p21._title_id = p22.CurrentTitleID
    end
}
v_u_28.new = function(_, p29, p30) --[[ Name: new ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (ref 3): v_u_9, (copy 4): v_u_1, (copy 5): v_u_28, (copy 6): v_u_5 ]]
    local v40 = {
        ["_id"] = p29,
        ["_name"] = p30,
        ["_requested_song_key"] = nil,
        ["_icon"] = v_u_3:transparent_assetid(),
        ["_title"] = "",
        ["_title_id"] = 0,
        ["_score"] = 0,
        ["_chain"] = 0,
        ["_power_bar_active"] = false,
        ["_fever_percentage"] = 0,
        ["_naked_score"] = 0,
        ["_naked_chain"] = 0,
        ["_naked_power_bar_active"] = false,
        ["_naked_fever_percentage"] = 0,
        ["_finished"] = false,
        ["_accuracy"] = 0,
        ["_perfect_count"] = 0,
        ["_great_count"] = 0,
        ["_okay_count"] = 0,
        ["_miss_count"] = 0,
        ["_combo_max"] = 0,
        ["_has_game_end_info"] = false,
        ["_like_count"] = 0,
        ["_did_leave"] = false,
        ["_match_mode"] = v_u_2.Compete,
        ["_stage_id"] = v_u_9:singleton():get_default_stage_id(),
        ["_gear_stats"] = v_u_1:statsdict_base(),
        ["_gear_info"] = v_u_28:get_default_gear_info(),
        ["_equipped"] = {},
        ["_display_pet_tab"] = {},
        ["_event_info"] = -1,
        ["_should_auto_equip_best_loadout"] = false,
        ["_update_from_player_info_count"] = 0,
        ["_early_quit"] = false,
        ["_ready"] = false,
        ["_matchmaking_time"] = 0,
        ["_votepick_song_key"] = nil,
        ["_timeout"] = 0,
        ["_loaded"] = false,
        ["set_requested_song_key"] = function(p31, p32) --[[ Name: set_requested_song_key ]] --[[ Line: 93 ]]
            p31._requested_song_key = p32
        end,
        ["get_player_info"] = function(p33, p34) --[[ Name: get_player_info ]] --[[ Line: 98 ]]
            return {
                ["Name"] = p33._name,
                ["UserId"] = p33._id,
                ["Slot"] = p34,
                ["RequestedSongKey"] = p33._requested_song_key,
                ["Score"] = p33._score,
                ["Chain"] = p33._chain,
                ["PowerBarActive"] = p33._power_bar_active,
                ["FeverPercentage"] = p33._fever_percentage,
                ["NakedScore"] = p33._naked_score,
                ["NakedChain"] = p33._naked_chain,
                ["NakedPowerBarActive"] = p33._naked_power_bar_active,
                ["NakedFeverPercentage"] = p33._naked_fever_percentage,
                ["Accuracy"] = p33._accuracy,
                ["Finished"] = p33._finished,
                ["PerfectCount"] = p33._perfect_count,
                ["GreatCount"] = p33._great_count,
                ["OkayCount"] = p33._okay_count,
                ["MissCount"] = p33._miss_count,
                ["ComboMax"] = p33._combo_max,
                ["HasGameEndInfo"] = p33._has_game_end_info,
                ["LikeCount"] = p33._like_count,
                ["DidLeave"] = p33._did_leave,
                ["MatchMode"] = p33._match_mode,
                ["Icon"] = p33._icon,
                ["Title"] = p33._title,
                ["TitleID"] = p33._title_id,
                ["StageID"] = p33._stage_id
            };
        end,
        ["get_player_matchmaking_info"] = function(p35, p36) --[[ Name: get_player_matchmaking_info ]] --[[ Line: 190 ]]
            return {
                ["Name"] = p35._name,
                ["UserId"] = p35._id,
                ["Slot"] = p36,
                ["RequestedSongKey"] = p35._requested_song_key,
                ["Ready"] = p35._ready,
                ["Timeout"] = p35._timeout,
                ["Loaded"] = p35._loaded,
                ["VotePickSongKey"] = p35._votepick_song_key,
                ["MatchMode"] = p35._match_mode,
                ["Icon"] = p35._icon,
                ["Title"] = p35._title,
                ["TitleID"] = p35._title_id,
                ["StageID"] = p35._stage_id
            };
        end,
        ["to_string"] = function(p37) --[[ Name: to_string ]] --[[ Line: 232 ]]
            return string.format("ServerGameInstancePlayer_Gear[Score(%d) Fever[%s](%.2f)] Naked[Score(%d) Fever[%s](%.2f)]", p37._score, tostring(p37._power_bar_active), p37._fever_percentage, p37._naked_score, tostring(p37._naked_power_bar_active), p37._naked_fever_percentage);
        end,
        ["get_gear_multiplier"] = function(p38) --[[ Name: get_gear_multiplier ]] --[[ Line: 243 ]]
            return p38._naked_score == 0 and 1 or p38._score / p38._naked_score;
        end,
        ["did_early_quit_or_leave"] = function(p39) --[[ Name: did_early_quit_or_leave ]] --[[ Line: 248 ]]
            return p39._early_quit == true and true or p39._did_leave == true;
        end
    }
    v40.update_from_player_info = function(p41, p42) --[[ Name: update_from_player_info ]] --[[ Line: 136 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        p41._id = p42.UserId
        p41._name = p42.Name
        if v_u_5:singleton():contains_key(p42.RequestedSongKey) then
            p41._requested_song_key = p42.RequestedSongKey
        end;
        if p42.Score ~= nil then
            p41._score = p42.Score
        end;
        if p42.Chain ~= nil then
            p41._chain = math.max(p41._chain, p42.Chain)
        end;
        if p42.PowerBarActive ~= nil then
            p41._power_bar_active = p42.PowerBarActive
        end;
        if p42.FeverPercentage ~= nil then
            p41._fever_percentage = math.max(p41._fever_percentage, p42.FeverPercentage)
        end;
        if p42.NakedScore ~= nil then
            p41._naked_score = p42.NakedScore
        end;
        if p42.NakedChain ~= nil then
            p41._naked_chain = p42.NakedChain
        end;
        if p42.NakedPowerBarActive ~= nil then
            p41._naked_power_bar_active = p42.NakedPowerBarActive
        end;
        if p42.NakedFeverPercentage ~= nil then
            p41._naked_fever_percentage = p42.NakedFeverPercentage
        end;
        if p42.Accuracy ~= nil then
            p41._accuracy = p42.Accuracy
        end;
        if p42.Finished ~= nil then
            p41._finished = p42.Finished
        end;
        if p42.PerfectCount ~= nil then
            p41._perfect_count = p42.PerfectCount
        end;
        if p42.GreatCount ~= nil then
            p41._great_count = p42.GreatCount
        end;
        if p42.OkayCount ~= nil then
            p41._okay_count = p42.OkayCount
        end;
        if p42.MissCount ~= nil then
            p41._miss_count = p42.MissCount
        end;
        if p42.ComboMax ~= nil then
            p41._combo_max = math.max(p41._combo_max, p42.ComboMax)
        end;
        if p42.HasGameEndInfo ~= nil then
            if p42.HasGameEndInfo == true then
                p41._has_game_end_info = true
            elseif p41._has_game_end_info == true then
                warn("ServerGameInstancePlayer:update_from_player_info HasGameEndInfo false when previously true")
            end;
        end;
        if p42.LikeCount ~= nil then
            p41._like_count = p42.LikeCount
        end;
        if p42.DidLeave ~= nil then
            p41._did_leave = p42.DidLeave
        end;
        if p42.MatchMode ~= nil then
            p41._match_mode = p42.MatchMode
        end;
        if p42.Icon ~= nil then
            p41._icon = p42.Icon
        end;
        if p42.Title ~= nil then
            p41._title = p42.Title
        end;
        if p42.TitleID ~= nil then
            p41._title_id = p42.TitleID
        end;
        if p42.StageID ~= nil then
            p41._stage_id = p42.StageID
        end;
        p41._update_from_player_info_count = p41._update_from_player_info_count + 1
    end;
    v40.update_from_matchmaking_info = function(p43, p44) --[[ Name: update_from_matchmaking_info ]] --[[ Line: 210 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        p43._id = p44.UserId
        p43._name = p44.Name
        if v_u_5:singleton():contains_key(p44.RequestedSongKey) then
            p43._requested_song_key = p44.RequestedSongKey
        end;
        if p44.Ready == nil then
            error("ServerGameInstancePlayer:update_from_matchmaking_info missing[Ready]")
        end;
        p43._ready = p44.Ready
        p43._timeout = p44.Timeout
        p43._loaded = p44.Loaded
        p43._votepick_song_key = p44.VotePickSongKey
        if p44.MatchMode ~= nil then
            p43._match_mode = p44.MatchMode
        end;
        if p44.Icon ~= nil then
            p43._icon = p44.Icon
        end;
        if p44.Title ~= nil then
            p43._title = p44.Title
        end;
        if p44.TitleID ~= nil then
            p43._title_id = p44.TitleID
        end;
        if p44.StageID ~= nil then
            p43._stage_id = p44.StageID
        end;
    end;
    return v40;
end;
local function f_update_dict_shared(p45, p46, p47) --[[ Name: update_dict_shared ]] --[[ Line: 255 ]]
    --[[ Upvalues: (copy 1): v_u_28 ]]
    local v48 = false
    for v49, _ in p45:key_itr() do
        local v50 = false
        for v51 = 1, 4 do
            if p46[v51] ~= nil and p46[v51].Slot == v49 then
                v50 = true
            end;
        end;
        if v50 == false then
            p45:remove(v49)
            v48 = true
        end;
    end;
    for v52 = 1, 4 do
        if p46[v52] ~= nil then
            local v53 = p46[v52]
            if p45:contains(v53.Slot) == false then
                p45:add(v53.Slot, v_u_28:new(v53.UserId, v53.Name))
                v48 = true
            end;
            p47(p45:get(v53.Slot), v53)
        end;
    end;
    return v48;
end;
local function f_update_from_player_info_updatefn(p54, p55) --[[ Name: update_from_player_info_updatefn ]] --[[ Line: 288 ]]
    p54:update_from_player_info(p55)
end;
local function f_update_from_matchmaking_info(p56, p57) --[[ Name: update_from_matchmaking_info ]] --[[ Line: 292 ]]
    p56:update_from_matchmaking_info(p57)
end;
v_u_28.update_dict_from_player_info_table = function(_, p58, p59) --[[ Name: update_dict_from_player_info_table ]] --[[ Line: 305 ]]
    --[[ Upvalues: (copy 1): f_update_dict_shared, (copy 2): f_update_from_player_info_updatefn ]]
    return f_update_dict_shared(p58, p59, f_update_from_player_info_updatefn);
end;
v_u_28.update_dict_from_matchmaking_info_table = function(_, p60, p61) --[[ Name: update_dict_from_matchmaking_info_table ]] --[[ Line: 309 ]]
    --[[ Upvalues: (copy 1): f_update_dict_shared, (copy 2): f_update_from_matchmaking_info ]]
    return f_update_dict_shared(p60, p61, f_update_from_matchmaking_info);
end;
v_u_28.get_default_gear_info = function(_) --[[ Name: get_default_gear_info ]] --[[ Line: 337 ]]
    --[[ Upvalues: (copy 1): v_u_28, (copy 2): v_u_4 ]]
    return v_u_28:get_gear_info_data_for_playerblob(v_u_4:get_default_playerblob(), 0, 0);
end;
return v_u_28;
