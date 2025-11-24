-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:22 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
local v_u_25 = {
    ["new"] = function(_, p_u_5, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4 ]]
        v_u_1:is_true(v_u_2:singleton():contains_key(p_u_5))
        v_u_1:is_int(p_u_6)
        v_u_1:is_int(p_u_7)
        local v8 = {}
        local v_u_9 = v_u_4.Score:new()
        local v_u_10 = false
        local v_u_11 = 0
        v8.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): p_u_5 ]]
            return p_u_5;
        end;
        v8.get_song_index = function(_) --[[ Name: get_song_index ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_6 ]]
            return p_u_6;
        end;
        v8.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            return p_u_7;
        end;
        v8.get_leaderboard_song_info_score = function(_) --[[ Name: get_leaderboard_song_info_score ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v8.get_reward_claimed = function(_) --[[ Name: get_reward_claimed ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end;
        v8.get_score_set_time = function(_) --[[ Name: get_score_set_time ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        v8.set_leaderboard_song_info_score = function(_, p12) --[[ Name: set_leaderboard_song_info_score ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_9 ]]
            v_u_1:is_table(p12)
            v_u_1:is_int(p12.Score)
            v_u_9 = p12
        end;
        v8.set_reward_claimed = function(_, p13) --[[ Name: set_reward_claimed ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10 ]]
            v_u_1:is_bool(p13)
            v_u_10 = p13
        end;
        v8.set_score_set_time = function(_, p14) --[[ Name: set_score_set_time ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_11 ]]
            v_u_1:is_number(p14)
            v_u_11 = p14
        end;
        v8.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 46 ]]
            --[[ Upvalues: (copy 1): p_u_5, (copy 2): p_u_6, (copy 3): p_u_7, (ref 4): v_u_4, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_11 ]]
            return {
                ["SongKey"] = p_u_5,
                ["SongIndex"] = p_u_6,
                ["WeekId"] = p_u_7,
                ["LeaderboardSongInfoScore"] = v_u_4.Score:to_table(v_u_9),
                ["RewardClaimed"] = v_u_10,
                ["ScoreSetTime"] = v_u_11
            };
        end;
        return v8;
    end,
    ["list_to_table"] = function(_, p15) --[[ Name: list_to_table ]] --[[ Line: 76 ]]
        local v16 = {}
        for v17 = 1, p15:count() do
            v16[v17] = p15:get(v17):to_table()
        end;
        return v16;
    end,
    ["try_player_week_participation_list_append"] = function(_, p18, p19) --[[ Name: try_player_week_participation_list_append ]] --[[ Line: 84 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        if p18:count() >= v_u_4:get_max_weekly_entries() then
            return false;
        end;
        for _, v20 in p18:key_itr() do
            if v20:get_song_index() == p19:get_song_index() then
                return false;
            end;
        end;
        p18:push_back(p19)
        return true;
    end,
    ["get_participation_from_list_of_song_index"] = function(_, p21, p22) --[[ Name: get_participation_from_list_of_song_index ]] --[[ Line: 97 ]]
        local v23 = nil
        for _, v24 in p21:key_itr() do
            if v24:get_song_index() == p22 then
                return v24;
            end;
        end;
        return v23;
    end
}
v_u_4.LeaderboardDSParticipation = v_u_25
v_u_25.from_table = function(_, p26) --[[ Name: from_table ]] --[[ Line: 60 ]]
    --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_4 ]]
    local v27 = v_u_25:new(p26.SongKey, p26.SongIndex, p26.WeekId)
    v27:set_leaderboard_song_info_score(v_u_4.Score:from_table(p26.LeaderboardSongInfoScore))
    v27:set_reward_claimed(p26.RewardClaimed)
    v27:set_score_set_time(p26.ScoreSetTime)
    return v27;
end;
v_u_25.table_to_list = function(_, p28) --[[ Name: table_to_list ]] --[[ Line: 68 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_25 ]]
    local v29 = v_u_3:new()
    for v30 = 1, #p28 do
        v29:push_back(v_u_25:from_table(p28[v30]))
    end;
    return v29;
end;
v_u_25.try_player_week_participation_update_neu_score = function(_, p31, p32, p33, p34) --[[ Name: try_player_week_participation_update_neu_score ]] --[[ Line: 108 ]]
    --[[ Upvalues: (copy 1): v_u_25 ]]
    local v35 = v_u_25:get_participation_from_list_of_song_index(p31, p33)
    if v35 == nil then
        return false;
    end;
    local v36 = v35:get_leaderboard_song_info_score()
    v36.Valid = true
    v36.Attempts = v36.Attempts + 1
    if p32.Score > v36.Score then
        v36.Score = p32.Score
        v36.GearMult = p32.GearMult
        v35:set_score_set_time(p34)
    else
        v35 = nil
    end;
    return true, v35;
end;
local function f_leaderboard_ds_participation_list_sort_by_score(p37) --[[ Name: leaderboard_ds_participation_list_sort_by_score ]] --[[ Line: 127 ]]
    p37:sort(function(p38, p39) --[[ Line: 128 ]]
        if p38:get_leaderboard_song_info_score().Score == p39:get_leaderboard_song_info_score().Score then
            return p38:get_score_set_time() < p39:get_score_set_time();
        else
            return p38:get_leaderboard_song_info_score().Score > p39:get_leaderboard_song_info_score().Score;
        end;
    end)
    for v40 = 1, p37:count() do
        p37:get(v40):get_leaderboard_song_info_score().Place = v40
    end;
end;
v_u_25.try_leaderboard_week_participation_list_sorted_insert = function(_, p41, p_u_42) --[[ Name: try_leaderboard_week_participation_list_sorted_insert ]] --[[ Line: 143 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): f_leaderboard_ds_participation_list_sort_by_score ]]
    v_u_3:remove_if(p41, function(p43) --[[ Line: 144 ]]
        --[[ Upvalues: (copy 1): p_u_42 ]]
        return p43:get_leaderboard_song_info_score().RbxID == p_u_42:get_leaderboard_song_info_score().RbxID;
    end)
    p41:push_back(p_u_42)
    f_leaderboard_ds_participation_list_sort_by_score(p41)
end;
v_u_25.list_to_leaderboard_song_info_score_list = function(_, p44) --[[ Name: list_to_leaderboard_song_info_score_list ]] --[[ Line: 151 ]]
    --[[ Upvalues: (copy 1): f_leaderboard_ds_participation_list_sort_by_score, (copy 2): v_u_3, (copy 3): v_u_4 ]]
    f_leaderboard_ds_participation_list_sort_by_score(p44)
    local v45 = v_u_3:new()
    for v46 = 1, p44:count() do
        local v47 = v_u_4.Score:copy(p44:get(v46):get_leaderboard_song_info_score())
        v47.Valid = true
        v45:push_back(v47)
    end;
    return v45;
end;
return v_u_25;
