-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:00 PM
-- Time elapsed: 12 milliseconds

require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.PlayerSongStatCollection)
local v_u_5 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = {
    ["Mode"] = {
        ["Initial"] = 0,
        ["Loading"] = 1,
        ["Loaded"] = 2
    }
}
v_u_7.new = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_7, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_6, (copy 6): v_u_2, (copy 7): v_u_5 ]]
    local v9 = {}
    local v_u_10 = v_u_4:new()
    local l_Initial_0 = v_u_7.Mode.Initial
    local v_u_11 = v_u_1:new()
    v9.cons = function(_) --[[ Name: cons ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_3, (copy 3): v_u_10, (copy 4): v_u_11 ]]
        p_u_8._evt:wait_on_event(v_u_3.EVT_PlayerSongStats_ServerWritePlayResponse, function(p_u_12) --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11 ]]
            if v_u_10:write_play_result_from_json_obj(p_u_12).IsNewBestScore == true then
                pcall(function() --[[ Line: 29 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_12, (ref 3): v_u_11 ]]
                    v_u_11:remove((v_u_10:load_from_rank_request_json_obj(p_u_12)))
                end)
            end;
        end)
        p_u_8._evt:wait_on_event(v_u_3.EVT_PlayerSongStats_ServerRequestRankResponse, function(p_u_13) --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11 ]]
            pcall(function() --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_13, (ref 3): v_u_11 ]]
                v_u_11:remove((v_u_10:load_from_rank_request_json_obj(p_u_13)))
            end)
        end)
    end;
    v9.load_stats = function(_) --[[ Name: load_stats ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): l_Initial_0, (ref 2): v_u_7, (copy 3): p_u_8, (ref 4): v_u_3, (copy 5): v_u_10 ]]
        if l_Initial_0 == v_u_7.Mode.Initial then
            l_Initial_0 = v_u_7.Mode.Loading
            p_u_8._evt:wait_on_event_once(v_u_3.EVT_PlayerSongStats_ServerRequestStatsResponse, function(p_u_14) --[[ Line: 47 ]]
                --[[ Upvalues: (ref 1): l_Initial_0, (ref 2): v_u_7, (ref 3): v_u_10 ]]
                l_Initial_0 = v_u_7.Mode.Loaded
                pcall(function() --[[ Line: 49 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_14 ]]
                    v_u_10:load_from_json_obj(p_u_14)
                end)
            end)
            p_u_8._evt:fire_event_to_server(v_u_3.EVT_PlayerSongStats_ClientRequestStats)
        end;
    end;
    v9.get_time_last_update = function(_) --[[ Name: get_time_last_update ]] --[[ Line: 56 ]]
        --[[ Upvalues: (copy 1): v_u_10 ]]
        return v_u_10:get_time_last_update();
    end;
    local function _(p15) --[[ Name: songkey_has_playcount_above_zero ]] --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): v_u_10 ]]
        local v16 = v_u_10:get_stat_for_songkey(p15)
        if v16 == nil then
            return false;
        else
            return v16.PlayCount > 0;
        end;
    end;
    local v_u_17 = false
    local v_u_18 = 0
    local v_u_19 = 0
    v9.request_ranks_for_songkey = function(_, p20) --[[ Name: request_ranks_for_songkey ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_10, (ref 3): v_u_17, (ref 4): v_u_19 ]]
        if p20 == v_u_18 then
            return;
        else
            local v21 = v_u_10:get_stat_for_songkey(p20)
            local v22
            if v21 == nil then
                v22 = false
            else
                v22 = v21.PlayCount > 0
            end;
            if v22 and v_u_10:get_rank_for_songkey(p20) == nil then
                v_u_17 = true
                v_u_18 = p20
                v_u_19 = 0
            else
                v_u_17 = false
                v_u_18 = 0
                v_u_19 = 0
            end;
        end;
    end;
    v9.update = function(_, p23) --[[ Name: update ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_19, (ref 3): v_u_6, (copy 4): p_u_8, (ref 5): v_u_3, (ref 6): v_u_18 ]]
        if v_u_17 == true then
            v_u_19 = v_u_19 + v_u_6:TimescaleToDeltaTime(p23)
            if v_u_19 > 1.5 then
                v_u_17 = false
                p_u_8._evt:fire_event_to_server(v_u_3.EVT_PlayerSongStats_ClientRequestRank, v_u_18)
            end;
        end;
    end;
    v9.get_playcount_display_str = function(_, p24) --[[ Name: get_playcount_display_str ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): l_Initial_0, (ref 2): v_u_7, (copy 3): v_u_10, (ref 4): v_u_2 ]]
        if l_Initial_0 == v_u_7.Mode.Initial or l_Initial_0 == v_u_7.Mode.Loading then
            return "Loading...";
        end;
        local v25 = v_u_10:get_stat_for_songkey(p24)
        return v25 == nil and "0" or string.format("%s", v_u_2:comma_value(v25.PlayCount));
    end;
    v9.get_best_grade_rank_value = function(_, p26) --[[ Name: get_best_grade_rank_value ]] --[[ Line: 107 ]]
        --[[ Upvalues: (ref 1): l_Initial_0, (ref 2): v_u_7, (ref 3): v_u_5, (copy 4): v_u_10 ]]
        if l_Initial_0 == v_u_7.Mode.Initial or l_Initial_0 == v_u_7.Mode.Loading then
            return v_u_5.Value.RankF, 0;
        else
            local v27 = v_u_10:get_stat_for_songkey(p26)
            if v27 == nil then
                return v_u_5.Value.RankF, 0;
            else
                return v27.BestGrade, v27.PlayCount;
            end;
        end;
    end;
    v9.get_best_grade_display_str = function(_, p28) --[[ Name: get_best_grade_display_str ]] --[[ Line: 119 ]]
        --[[ Upvalues: (ref 1): l_Initial_0, (ref 2): v_u_7, (copy 3): v_u_10, (ref 4): v_u_5 ]]
        if l_Initial_0 == v_u_7.Mode.Initial or l_Initial_0 == v_u_7.Mode.Loading then
            return "Loading Stats...", 0;
        else
            local v29 = v_u_10:get_stat_for_songkey(p28)
            if v29 == nil then
                return v_u_5:get_rank_value_name(v_u_5.Value.RankF), 0;
            else
                return v_u_5:get_rank_value_name(v29.BestGrade), v29.PlayCount;
            end;
        end;
    end;
    v9.get_best_score_display_str = function(_, p30) --[[ Name: get_best_score_display_str ]] --[[ Line: 131 ]]
        --[[ Upvalues: (ref 1): l_Initial_0, (ref 2): v_u_7, (copy 3): v_u_10, (ref 4): v_u_2 ]]
        if l_Initial_0 == v_u_7.Mode.Initial or l_Initial_0 == v_u_7.Mode.Loading then
            return "Loading Stats...";
        end;
        local v31 = v_u_10:get_stat_for_songkey(p30)
        return v31 == nil and "0" or string.format("%s", v_u_2:comma_value(v31.BestScore));
    end;
    v9.get_rank_display_str = function(_, p32) --[[ Name: get_rank_display_str ]] --[[ Line: 144 ]]
        --[[ Upvalues: (copy 1): v_u_10, (ref 2): l_Initial_0, (ref 3): v_u_7, (ref 4): v_u_2 ]]
        local v33 = v_u_10:get_stat_for_songkey(p32)
        local v34
        if v33 == nil then
            v34 = false
        else
            v34 = v33.PlayCount > 0
        end;
        if v34 ~= true then
            return "Not Ranked";
        end;
        if l_Initial_0 == v_u_7.Mode.Initial or l_Initial_0 == v_u_7.Mode.Loading then
            return "Loading Stats...";
        end;
        local v35, v36 = v_u_10:get_rank_for_songkey(p32)
        return v35 == nil and "Loading..." or ((v35 <= 0 or v36 <= 0) and "Not Ranked" or string.format("%s", v_u_2:num_placify(v35)));
    end;
    v9:cons()
    return v9;
end;
return v_u_7;
