-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Time elapsed: 12 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_7 = require(game.ReplicatedStorage.Shared.MatchMode)
local v8 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_9 = nil
v8:require_shared(function() --[[ Line: 11 ]]
    --[[ Upvalues: (ref 1): v_u_9 ]]
    v_u_9 = require(game.ReplicatedStorage.Shared.PlayerSongStatCollection)
end)
local v_u_53 = {
    ["Category"] = {
        ["TopScores"] = 1,
        ["RecentScores"] = 2,
        ["PlayerRecentScores"] = 3
    },
    ["new"] = function(_, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_7, (copy 5): v_u_4, (copy 6): v_u_6 ]]
        v_u_1:is_int(p_u_10)
        v_u_1:is_int(p_u_11)
        if v_u_2:singleton():contains_key(p_u_11) ~= true then
            v_u_3:warnf("PlayerSongPlay:new invalid song_key(%d) for rbxid(%d)", p_u_11, p_u_10)
        end;
        local v12 = {}
        local v_u_13 = math.floor((tick()))
        local v_u_14 = ""
        local v_u_15 = 0
        local v_u_16 = 0
        local v_u_17 = 0
        local v_u_18 = 0
        local l_Casual_0 = v_u_7.Casual
        v12.get_rbxid = function(_) --[[ Name: get_rbxid ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): p_u_10 ]]
            return p_u_10;
        end;
        v12.get_songkey = function(_) --[[ Name: get_songkey ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            return p_u_11;
        end;
        v12.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 42 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            return p_u_11;
        end;
        v12.get_time = function(_) --[[ Name: get_time ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13;
        end;
        v12.set_time = function(_, p19) --[[ Name: set_time ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_13 ]]
            v_u_1:is_number(p19)
            v_u_13 = math.floor(p19)
        end;
        v12.get_rbxname = function(_) --[[ Name: get_rbxname ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        v12.set_rbxname = function(_, p20) --[[ Name: set_rbxname ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_14 ]]
            v_u_1:is_string(p20)
            v_u_14 = p20
        end;
        v12.get_score = function(_) --[[ Name: get_score ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        v12.set_score = function(_, p21) --[[ Name: set_score ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_15 ]]
            v_u_1:is_int(p21)
            v_u_15 = p21
        end;
        v12.get_naked_score = function(_) --[[ Name: get_naked_score ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        v12.set_naked_score = function(_, p22) --[[ Name: set_naked_score ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_16 ]]
            v_u_1:is_int(p22)
            v_u_16 = p22
        end;
        v12.get_accuracy = function(_) --[[ Name: get_accuracy ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        v12.set_accuracy = function(_, p23) --[[ Name: set_accuracy ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_17, (ref 3): v_u_4 ]]
            v_u_1:is_number(p23)
            v_u_17 = v_u_4:clamp(p23, 0, 1)
        end;
        v12.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        v12.set_gear_power = function(_, p24) --[[ Name: set_gear_power ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_18 ]]
            v_u_1:is_int(p24)
            v_u_18 = p24
        end;
        v12.get_match_mode = function(_) --[[ Name: get_match_mode ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): l_Casual_0 ]]
            return l_Casual_0;
        end;
        v12.set_match_mode = function(_, p25) --[[ Name: set_match_mode ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_7, (ref 3): l_Casual_0 ]]
            v_u_1:is_enum_member(p25, v_u_7)
            l_Casual_0 = p25
        end;
        v12.get_time_string = function(_) --[[ Name: get_time_string ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return os.date("%Y-%m-%d %H:%M:%S", v_u_13);
        end;
        v12.get_gear_multiplier = function(_) --[[ Name: get_gear_multiplier ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_15 ]]
            return v_u_16 <= 0 and 1 or v_u_15 / v_u_16;
        end;
        v12.get_display_accuracy_string = function(_) --[[ Name: get_display_accuracy_string ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return string.format("%.2f", v_u_17 * 100);
        end;
        v12.get_grade = function(_) --[[ Name: get_grade ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_17 ]]
            return v_u_6:accuracy_to_rank_value(v_u_17);
        end;
        v12.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 76 ]]
            --[[ Upvalues: (copy 1): p_u_10, (copy 2): p_u_11, (ref 3): v_u_13, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_16, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): l_Casual_0 ]]
            return {
                ["R"] = p_u_10,
                ["S"] = p_u_11,
                ["T"] = v_u_13,
                ["N"] = v_u_14,
                ["GS"] = v_u_15,
                ["NS"] = v_u_16,
                ["A"] = v_u_17,
                ["GP"] = v_u_18,
                ["MM"] = l_Casual_0
            };
        end;
        return v12;
    end,
    ["keep_datastore_list_count"] = function(_) --[[ Name: keep_datastore_list_count ]] --[[ Line: 116 ]]
        return 1000;
    end,
    ["list_to_tab"] = function(_, p26) --[[ Name: list_to_tab ]] --[[ Line: 135 ]]
        local v27 = {}
        for v28 = 1, p26:count() do
            table.insert(v27, p26:get(v28):to_table())
        end;
        return v27;
    end,
    ["play_update_player_song_stat_collection"] = function(_, p29, p30, p31) --[[ Name: play_update_player_song_stat_collection ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_9 ]]
        local v32 = p30:add_songkey(p29:get_songkey())
        p31:set_old_score(v_u_9.Stat:get_best_score(v32))
        if p29:get_score() > v_u_9.Stat:get_best_score(v32) then
            v_u_9.Stat:set_best_score(v32, p29:get_score())
            p31:set_is_new_best_score(true)
        end;
        p31:set_best_score(v_u_9.Stat:get_best_score(v32))
        p31:set_old_grade(v_u_9.Stat:get_best_grade(v32))
        if p29:get_grade() > v_u_9.Stat:get_best_grade(v32) then
            v_u_9.Stat:set_best_grade(v32, p29:get_grade())
            p31:set_is_new_best_grade(true)
        end;
        p31:set_best_grade(v_u_9.Stat:get_best_grade(v32))
        v_u_9.Stat:set_play_count(v32, v_u_9.Stat:get_play_count(v32) + 1)
        p31:set_play_count(v_u_9.Stat:get_play_count(v32))
    end,
    ["WritePlayResult"] = {
        ["new"] = function(_, p33) --[[ Name: new ]] --[[ Line: 184 ]]
            --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1 ]]
            local v34 = {}
            local v_u_35 = p33:get_rbxid()
            local v_u_36 = p33:get_songkey()
            local v_u_37 = false
            local v_u_38 = false
            local v_u_39 = 0
            local l_RankF_0 = v_u_6.Value.RankF
            local v_u_40 = 0
            local l_RankF_1 = v_u_6.Value.RankF
            local v_u_41 = 0
            local v_u_42 = 0
            local v_u_43 = 0
            v34.set_is_new_best_score = function(_, p44) --[[ Name: set_is_new_best_score ]] --[[ Line: 199 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_37 ]]
                v_u_1:is_bool(p44)
                v_u_37 = p44
            end;
            v34.set_is_new_best_grade = function(_, p45) --[[ Name: set_is_new_best_grade ]] --[[ Line: 204 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_38 ]]
                v_u_1:is_bool(p45)
                v_u_38 = p45
            end;
            v34.set_best_score = function(_, p46) --[[ Name: set_best_score ]] --[[ Line: 209 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_39 ]]
                v_u_1:is_int(p46)
                v_u_39 = p46
            end;
            v34.set_best_grade = function(_, p47) --[[ Name: set_best_grade ]] --[[ Line: 214 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6, (ref 3): l_RankF_0 ]]
                v_u_1:is_enum_member(p47, v_u_6.Value)
                l_RankF_0 = p47
            end;
            v34.set_old_score = function(_, p48) --[[ Name: set_old_score ]] --[[ Line: 219 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_40 ]]
                v_u_1:is_int(p48)
                v_u_40 = p48
            end;
            v34.set_old_grade = function(_, p49) --[[ Name: set_old_grade ]] --[[ Line: 224 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6, (ref 3): l_RankF_1 ]]
                v_u_1:is_enum_member(p49, v_u_6.Value)
                l_RankF_1 = p49
            end;
            v34.set_play_count = function(_, p50) --[[ Name: set_play_count ]] --[[ Line: 229 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_41 ]]
                v_u_1:is_int(p50)
                v_u_41 = p50
            end;
            v34.set_rank = function(_, p51) --[[ Name: set_rank ]] --[[ Line: 234 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_43 ]]
                v_u_1:is_int(p51)
                v_u_43 = p51
            end;
            v34.set_total_count = function(_, p52) --[[ Name: set_total_count ]] --[[ Line: 239 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_42 ]]
                v_u_1:is_int(p52)
                v_u_42 = p52
            end;
            v34.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 244 ]]
                --[[ Upvalues: (copy 1): v_u_35, (copy 2): v_u_36, (ref 3): v_u_37, (ref 4): v_u_38, (ref 5): v_u_39, (ref 6): l_RankF_0, (ref 7): v_u_40, (ref 8): l_RankF_1, (ref 9): v_u_41, (ref 10): v_u_42, (ref 11): v_u_43 ]]
                return {
                    ["PlayerId"] = v_u_35,
                    ["SongKey"] = v_u_36,
                    ["IsNewBestScore"] = v_u_37,
                    ["IsNewBestGrade"] = v_u_38,
                    ["BestScore"] = v_u_39,
                    ["BestGrade"] = l_RankF_0,
                    ["OldScore"] = v_u_40,
                    ["OldGrade"] = l_RankF_1,
                    ["PlayCount"] = v_u_41,
                    ["TotalCount"] = v_u_42,
                    ["Rank"] = v_u_43
                };
            end;
            return v34;
        end
    }
}
v_u_53.from_table = function(_, p54) --[[ Name: from_table ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_53 ]]
    local l_R_0 = p54.R
    local l_S_0 = p54.S
    local l_T_0 = p54.T
    local l_N_0 = p54.N
    local l_GS_0 = p54.GS
    local l_NS_0 = p54.NS
    local l_A_0 = p54.A
    local l_GP_0 = p54.GP
    local v55 = v_u_53:new(l_R_0, l_S_0)
    v55:set_time(l_T_0)
    v55:set_rbxname(l_N_0)
    v55:set_score(l_GS_0)
    v55:set_naked_score(l_NS_0)
    v55:set_accuracy(l_A_0)
    v55:set_gear_power(l_GP_0)
    if p54.MM then
        v55:set_match_mode(p54.MM)
    end;
    return v55;
end;
v_u_53.keep_list_within_datastore_list_count = function(_, p56) --[[ Name: keep_list_within_datastore_list_count ]] --[[ Line: 118 ]]
    --[[ Upvalues: (copy 1): v_u_53 ]]
    while p56:count() > v_u_53:keep_datastore_list_count() do
        p56:pop_back()
    end;
end;
v_u_53.tab_to_list = function(_, p57) --[[ Name: tab_to_list ]] --[[ Line: 124 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_53 ]]
    local v58 = v_u_5:new()
    if type(p57) == "table" then
        for _, v59 in ipairs(p57) do
            v58:push_back((v_u_53:from_table(v59)))
        end;
    end;
    return v58;
end;
return v_u_53;
