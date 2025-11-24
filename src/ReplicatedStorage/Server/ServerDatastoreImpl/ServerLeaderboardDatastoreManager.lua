-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:22 PM
-- Time elapsed: 23 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
local v_u_8 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_9 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_10 = require(game.ReplicatedStorage.Server.ServerDatastoreImpl.LeaderboardDSParticipation)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local s_DataStoreService_0 = game:GetService("DataStoreService")
return {
    ["new"] = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_4, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_7, (copy 6): v_u_3, (copy 7): v_u_5, (copy 8): v_u_10, (copy 9): s_DataStoreService_0, (copy 10): v_u_9, (copy 11): v_u_11, (copy 12): v_u_6 ]]
        local v_u_13 = {}
        v_u_13.dsapi_leaderboards_get_info = function(p14, p_u_15, p16, p_u_17, p18) --[[ Name: dsapi_leaderboards_get_info ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_8, (ref 3): v_u_4 ]]
            if p_u_17 == nil then
                p_u_17 = p_u_12._api:get_week_id()
            end;
            local v_u_19 = v_u_8.Builder:new()
            local v_u_20 = {}
            if v_u_4.WeeklyLeaderboardDoWebAPIRead == true then
                v_u_19:begin()
                p_u_12._api:api_leaderboards_get_info(function(p21) --[[ Line: 37 ]]
                    --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_19 ]]
                    v_u_20 = p21
                    v_u_19:finish()
                end, p16, p18)
            end;
            if v_u_4.WeeklyLeaderboardDoDatastoreAPIWrite == true then
                v_u_19:begin()
                p14:datastore_get_cached_leaderboard_song_info_list(p_u_17, function(p22) --[[ Line: 49 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_20, (ref 3): p_u_17, (ref 4): p_u_12, (copy 5): v_u_19 ]]
                    if v_u_4.WeeklyLeaderboardDoDatastoreAPIRead == true then
                        v_u_20 = p22:get_table()
                        for v23 = 1, #v_u_20 do
                            local v24 = v_u_20[v23]
                            if p_u_17 == p_u_12._api:get_week_id() then
                                v24.TimeRemaining = p_u_12._api:get_time_to_next_week_sec()
                            else
                                v24.TimeRemaining = 0
                            end;
                        end;
                    end;
                    v_u_19:finish()
                end)
            end;
            v_u_19:wait_for_finish(function() --[[ Line: 65 ]]
                --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_20 ]]
                p_u_15(v_u_20)
            end)
        end;
        v_u_13.dsapi_leaderboards_player_enter_leaderboard = function(p25, p26, p27, p_u_28) --[[ Name: dsapi_leaderboards_player_enter_leaderboard ]] --[[ Line: 71 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_4 ]]
            local v29 = p_u_12._player_manager:id_to_player(p26)
            if v29 == nil then
                v_u_1:warnf("ServerLeaderboardDatastoreManager:dsapi_leaderboards_player_enter_leaderboard playerid=%s not found", (tostring(p26)))
                return p_u_28(false);
            end;
            local v30 = p_u_12._api:get_week_id()
            local l_SongKey_0 = p27.SongKey
            local l_SongIndex_0 = p27.SongIndex
            local v_u_31 = v_u_8.Builder:new()
            local v_u_32 = true
            if v_u_4.WeeklyLeaderboardDoWebAPIWrite == true then
                v_u_31:begin()
                p_u_12._api:api_leaderboards_player_enter_leaderboard(p26, l_SongIndex_0, function(p33) --[[ Line: 87 ]]
                    --[[ Upvalues: (ref 1): v_u_32, (copy 2): v_u_31 ]]
                    local v34 = v_u_32
                    if v34 then
                        v34 = p33 ~= nil
                    end;
                    v_u_32 = v34
                    v_u_31:finish()
                end)
            end;
            if v_u_4.WeeklyLeaderboardDoDatastoreAPIWrite == true then
                v_u_31:begin()
                p25:datastore_create_player_week_id_song_index_participation(v29, v30, l_SongKey_0, l_SongIndex_0, function(p35) --[[ Line: 95 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_32, (copy 3): v_u_31 ]]
                    if v_u_4.WeeklyLeaderboardDoDatastoreAPIRead == true then
                        v_u_32 = v_u_32 and p35
                    end;
                    v_u_31:finish()
                end)
            end;
            v_u_31:wait_for_finish(function() --[[ Line: 103 ]]
                --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_32 ]]
                p_u_28(v_u_32)
            end)
        end;
        v_u_13.dsapi_leaderboards_player_check_week_participation_count = function(p36, p37, p_u_38) --[[ Name: dsapi_leaderboards_player_check_week_participation_count ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_4, (copy 3): p_u_12 ]]
            local v_u_39 = v_u_8.Builder:new()
            local v_u_40 = 0
            if v_u_4.WeeklyLeaderboardDoWebAPIRead == true then
                v_u_39:begin()
                p_u_12._api:api_leaderboards_player_check_week_participation_count(p37, function(p41) --[[ Line: 116 ]]
                    --[[ Upvalues: (ref 1): v_u_40, (copy 2): v_u_39 ]]
                    v_u_40 = p41
                    v_u_39:finish()
                end)
            end;
            if v_u_4.WeeklyLeaderboardDoDatastoreAPIRead == true then
                v_u_39:begin()
                p36:datastore_get_player_week_id_leaderboard_participations(p37, p_u_12._api:get_week_id(), function(p42) --[[ Line: 124 ]]
                    --[[ Upvalues: (ref 1): v_u_40, (copy 2): v_u_39 ]]
                    v_u_40 = p42:count()
                    v_u_39:finish()
                end)
            end;
            v_u_39:wait_for_finish(function() --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): p_u_38, (ref 2): v_u_40 ]]
                p_u_38(v_u_40)
            end)
        end;
        v_u_13.dsapi_leaderboards_player_get_week_entered_leaderboards = function(p43, p44, p45, _, p_u_46) --[[ Name: dsapi_leaderboards_player_get_week_entered_leaderboards ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_4, (copy 3): p_u_12, (ref 4): v_u_2, (ref 5): v_u_7 ]]
            local v_u_47 = v_u_8.Builder:new()
            local v_u_48 = {}
            if v_u_4.WeeklyLeaderboardDoWebAPIRead == true then
                v_u_47:begin()
                p_u_12._api:api_leaderboards_player_get_week_entered_leaderboards(p44, p45, function(p49) --[[ Line: 143 ]]
                    --[[ Upvalues: (ref 1): v_u_48, (copy 2): v_u_47 ]]
                    v_u_48 = p49
                    v_u_47:finish()
                end)
            end;
            if v_u_4.WeeklyLeaderboardDoDatastoreAPIRead == true then
                v_u_47:begin()
                p43:datastore_get_player_week_id_leaderboard_participations(p44, p_u_12._api:get_week_id(), function(p50) --[[ Line: 156 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_48, (copy 4): v_u_47 ]]
                    local v51 = v_u_2:new()
                    for _, v52 in p50:key_itr() do
                        local v53 = v_u_7:new()
                        v53.SongKey = v52:get_song_key()
                        v53.SongIndex = v52:get_song_index()
                        v51:push_back(v53)
                    end;
                    v_u_48 = v51:get_table()
                    v_u_47:finish()
                end)
            end;
            v_u_47:wait_for_finish(function() --[[ Line: 170 ]]
                --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_48 ]]
                p_u_46(v_u_48)
            end)
        end;
        v_u_13.dsapi_leaderboards_player_get_pending_rewards_count = function(p54, p55, p_u_56) --[[ Name: dsapi_leaderboards_player_get_pending_rewards_count ]] --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_4, (copy 3): p_u_12 ]]
            local v_u_57 = v_u_8.Builder:new()
            local v_u_58 = 0
            if v_u_4.WeeklyLeaderboardDoWebAPIRead == true then
                v_u_57:begin()
                p_u_12._api:api_leaderboards_player_get_pending_rewards(p55, function(p59) --[[ Line: 182 ]]
                    --[[ Upvalues: (ref 1): v_u_58, (copy 2): v_u_57 ]]
                    v_u_58 = typeof(p59) == "table" and (p59.Count or 0) or 0
                    v_u_57:finish()
                end)
            end;
            if v_u_4.WeeklyLeaderboardDoDatastoreAPIRead == true then
                local v60 = p_u_12._api:get_week_id() - 1
                v_u_57:begin()
                p54:datastore_get_player_week_id_leaderboard_participations(p55, v60, function(p61) --[[ Line: 197 ]]
                    --[[ Upvalues: (ref 1): v_u_58, (copy 2): v_u_57 ]]
                    local v62 = 0
                    for _, v63 in p61:key_itr() do
                        if v63:get_reward_claimed() == false and v63:get_leaderboard_song_info_score().Attempts > 0 then
                            v62 = v62 + 1
                        end;
                    end;
                    v_u_58 = v62
                    v_u_57:finish()
                end)
            end;
            v_u_57:wait_for_finish(function() --[[ Line: 209 ]]
                --[[ Upvalues: (copy 1): p_u_56, (ref 2): v_u_58 ]]
                p_u_56(v_u_58)
            end)
        end;
        v_u_13.dsapi_leaderboards_player_claim_rewards = function(p_u_64, p_u_65, p_u_66) --[[ Name: dsapi_leaderboards_player_claim_rewards ]] --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_4, (copy 3): p_u_12, (ref 4): v_u_3, (ref 5): v_u_2, (ref 6): v_u_5, (ref 7): v_u_1 ]]
            local v_u_67 = v_u_8.Builder:new()
            local v_u_68 = {}
            if v_u_4.WeeklyLeaderboardDoWebAPIWrite == true then
                v_u_67:begin()
                p_u_12._api:api_leaderboards_player_claim_rewards(p_u_65, function(p69) --[[ Line: 221 ]]
                    --[[ Upvalues: (ref 1): v_u_68, (copy 2): v_u_67 ]]
                    v_u_68 = p69
                    v_u_67:finish()
                end)
            end;
            if v_u_4.WeeklyLeaderboardDoDatastoreAPIWrite == true then
                local v_u_70 = p_u_12._api:get_week_id() - 1
                v_u_67:begin()
                p_u_64:datastore_get_player_week_id_leaderboard_participations(p_u_65, v_u_70, function(p71) --[[ Line: 248 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_67, (ref 3): v_u_8, (copy 4): p_u_64, (copy 5): p_u_65, (copy 6): v_u_70, (ref 7): v_u_2, (ref 8): v_u_5, (ref 9): v_u_1, (ref 10): v_u_4, (ref 11): v_u_68 ]]
                    local v_u_72 = v_u_3:new()
                    local v_u_73 = v_u_3:new()
                    for _, v74 in p71:key_itr() do
                        v_u_73:add(v74:get_song_index(), v74:get_song_key())
                        local v75 = v74:get_leaderboard_song_info_score()
                        if v74:get_reward_claimed() == false and (v75.Valid == true and v75.Attempts > 0) then
                            v_u_72:add(v74:get_song_index(), 500)
                        end;
                    end;
                    if v_u_72:count() == 0 then
                        return v_u_67:finish();
                    end;
                    local v_u_76 = v_u_8.Builder:new()
                    v_u_3:for_each_key_value_sorted(v_u_72, function(p_u_77) --[[ Line: 264 ]]
                        --[[ Upvalues: (copy 1): v_u_76, (ref 2): p_u_64, (ref 3): p_u_65, (ref 4): v_u_70, (copy 5): v_u_72 ]]
                        v_u_76:begin()
                        p_u_64:datastore_get_participation_leaderboard_for_week_and_song_index_no_cooldown(p_u_65, v_u_70, p_u_77, function(p78) --[[ Line: 266 ]]
                            --[[ Upvalues: (ref 1): p_u_65, (ref 2): v_u_72, (copy 3): p_u_77, (ref 4): v_u_76 ]]
                            local v79 = 500
                            for v80 = 1, p78:count() do
                                if p78:get(v80):get_leaderboard_song_info_score().RbxID == p_u_65 then
                                    v79 = v80
                                    break;
                                end;
                            end;
                            v_u_72:add(p_u_77, v79)
                            v_u_76:finish()
                        end)
                    end)
                    v_u_76:wait_for_finish(function() --[[ Line: 281 ]]
                        --[[ Upvalues: (ref 1): p_u_64, (ref 2): p_u_65, (ref 3): v_u_70, (copy 4): v_u_72, (ref 5): v_u_2, (copy 6): v_u_73, (ref 7): v_u_5, (ref 8): v_u_1, (ref 9): v_u_4, (ref 10): v_u_68, (ref 11): v_u_67 ]]
                        p_u_64:datastore_update_week_claim_song_index_to_rank(p_u_65, v_u_70, v_u_72, function() --[[ Line: 287 ]]
                            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_72, (ref 3): v_u_73, (ref 4): v_u_70, (ref 5): v_u_5, (ref 6): v_u_1, (ref 7): v_u_4, (ref 8): v_u_68, (ref 9): v_u_67 ]]
                            local v81 = v_u_2:new()
                            for v82, v83 in v_u_72:key_itr() do
                                v81:push_back({
                                    ["Rank"] = v83,
                                    ["Week"] = v_u_70,
                                    ["SongKey"] = v_u_73:get(v82)
                                })
                            end;
                            if v_u_5:is_dev_build() then
                                v_u_1:puts("dsapi_leaderboards_player_claim_rewards (%s)", v_u_5:table_to_string(v81:get_table()))
                            end;
                            if v_u_4.WeeklyLeaderboardDoDatastoreAPIRead == true then
                                v_u_68 = v81:get_table()
                            end;
                            v_u_67:finish()
                        end)
                    end)
                end)
            end;
            v_u_67:wait_for_finish(function() --[[ Line: 311 ]]
                --[[ Upvalues: (copy 1): p_u_66, (ref 2): v_u_68 ]]
                p_u_66(v_u_68)
            end)
        end;
        v_u_13.dsapi_leaderboards_get_player_info = function(p_u_84, p_u_85, p_u_86, p_u_87, p88) --[[ Name: dsapi_leaderboards_get_player_info ]] --[[ Line: 317 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_7, (ref 3): v_u_4, (copy 4): p_u_12, (ref 5): v_u_10 ]]
            local v_u_89 = v_u_8.Builder:new()
            local v_u_90 = v_u_7:new()
            if v_u_4.WeeklyLeaderboardDoWebAPIRead == true then
                v_u_89:begin()
                p_u_12._api:api_leaderboards_get_player_info(p_u_85, p_u_86, function(p91) --[[ Line: 325 ]]
                    --[[ Upvalues: (ref 1): v_u_90, (copy 2): v_u_89 ]]
                    v_u_90 = p91
                    v_u_89:finish()
                end, p88)
            end;
            if v_u_4.WeeklyLeaderboardDoDatastoreAPIRead == true then
                local v_u_92 = p88
                if v_u_92 == nil then
                    v_u_92 = p_u_12._api:get_week_id()
                end;
                v_u_89:begin()
                p_u_84:datastore_get_player_week_id_leaderboard_participations(p_u_85, v_u_92, function(p93) --[[ Line: 345 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_86, (ref 3): v_u_90, (copy 4): v_u_89, (copy 5): p_u_84, (copy 6): p_u_85, (ref 7): v_u_92, (ref 8): v_u_10 ]]
                    local v_u_94 = v_u_7:new()
                    local v95 = false
                    local v_u_96 = 0
                    for _, v97 in p93:key_itr() do
                        if v97:get_song_index() == p_u_86 then
                            v_u_96 = v97:get_leaderboard_song_info_score().Attempts
                            v95 = true
                            break;
                        end;
                    end;
                    if v95 == true then
                        v_u_94.IsEntered = true
                        p_u_84:datastore_get_participation_leaderboard_for_week_and_song_index(p_u_85, v_u_92, p_u_86, function(p98) --[[ Line: 367 ]]
                            --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_85, (copy 3): v_u_94, (ref 4): v_u_7, (ref 5): v_u_96, (ref 6): v_u_90, (ref 7): v_u_89 ]]
                            local v99 = v_u_10:list_to_leaderboard_song_info_score_list(p98)
                            for v100 = 1, v99:count() do
                                local v101 = v99:get(v100)
                                if v101.RbxID == p_u_85 then
                                    v_u_94.YouDisplay = v_u_7.Score:copy(v101)
                                    v_u_94.YouDisplay.Attempts = v_u_96
                                    v_u_94.YouDisplay.Valid = true
                                    local v102 = v99:get(v100 - 1)
                                    if v102 ~= nil then
                                        v_u_94.YouDisplayAbove = v_u_7.Score:copy(v102)
                                        v_u_94.YouDisplayAbove.Valid = true
                                    end;
                                    local v103 = v99:get(v100 + 1)
                                    if v103 ~= nil then
                                        v_u_94.YouDisplayBelow = v_u_7.Score:copy(v103)
                                        v_u_94.YouDisplayBelow.Valid = true
                                    end;
                                    break;
                                end;
                            end;
                            v_u_90 = v_u_94
                            v_u_89:finish()
                        end)
                    else
                        v_u_94.IsEntered = false
                        v_u_90 = v_u_94
                        v_u_89:finish()
                    end;
                end)
            end;
            v_u_89:wait_for_finish(function() --[[ Line: 410 ]]
                --[[ Upvalues: (copy 1): p_u_87, (ref 2): v_u_90 ]]
                p_u_87(v_u_90)
            end)
        end;
        v_u_13.dsapi_write_play = function(p_u_104, p_u_105, p_u_106, p_u_107, p_u_108, _) --[[ Name: dsapi_write_play ]] --[[ Line: 417 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_1, (ref 3): v_u_4, (ref 4): v_u_10, (ref 5): v_u_7, (ref 6): v_u_5 ]]
            local v_u_109 = p_u_12._player_manager:id_to_player(p_u_105)
            if v_u_109 == nil then
                v_u_1:warnf("ServerLeaderboardDatastoreManager:dsapi_write_play playerid=%s not found", (tostring(p_u_105)))
            else
                local v_u_110 = p_u_12._api:get_week_id()
                if v_u_4.WeeklyLeaderboardDoDatastoreAPIWrite == true then
                    p_u_104:datastore_get_player_week_id_leaderboard_participations(p_u_105, v_u_110, function(p111) --[[ Line: 427 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_107, (ref 3): v_u_7, (copy 4): p_u_108, (ref 5): v_u_5, (ref 6): v_u_1, (copy 7): p_u_105, (copy 8): p_u_106, (copy 9): v_u_109, (copy 10): p_u_104, (copy 11): v_u_110 ]]
                        if v_u_10:get_participation_from_list_of_song_index(p111, p_u_107) ~= nil then
                            local v112 = v_u_7.Score:new()
                            local v113 = p_u_108._score or 0
                            local v114 = p_u_108._naked_score or 0
                            local v115 = v114 == 0 and 1 or v113 / v114
                            if v_u_5:is_dev_build() then
                                v_u_1:puts("ServerLeaderboardDatastoreManager:dsapi_write_play playerid=%s, songkey=%s, tar_song_index=%s, score=%s gear_mult=%s", tostring(p_u_105), tostring(p_u_106), tostring(p_u_107), tostring(v113), (tostring(v115)))
                            end;
                            v112.PlayerName = v_u_109.Name
                            v112.RbxID = p_u_105
                            v112.Score = v113
                            v112.GearMult = v115
                            p_u_104:datastore_update_score_to_player_participation(p_u_105, v_u_110, v112, p_u_107, function(p116) --[[ Line: 467 ]]
                                --[[ Upvalues: (ref 1): p_u_104, (ref 2): p_u_105, (ref 3): v_u_110 ]]
                                p_u_104:datastore_update_participation_to_leaderboard(p_u_105, v_u_110, p116)
                            end)
                        end;
                    end)
                end;
            end;
        end;
        local v_u_117 = s_DataStoreService_0:GetDataStore("WLBWeekSongIndex")
        local function _(p118, p119) --[[ Name: week_id_and_song_index_to_key ]] --[[ Line: 481 ]]
            return string.format("widsi_%d_%d", p118, p119);
        end;
        local v_u_120 = v_u_9:new():set_cooldown(0.5)
        local v_u_121 = v_u_9:new():set_cooldown(2.5)
        local function _(p122, p123, p_u_124) --[[ Name: leaderboard_ds_participation_list_update_cached_leaderboard_song_info_list ]] --[[ Line: 486 ]]
            --[[ Upvalues: (copy 1): v_u_13, (ref 2): v_u_10 ]]
            v_u_13:datastore_update_cached_leaderboard_song_info_list(p122, p123, function(p125) --[[ Line: 491 ]]
                --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_124 ]]
                local v126 = v_u_10:list_to_leaderboard_song_info_score_list(p_u_124)
                p125.TotalParticipants = v126:count()
                p125.LeaderboardPlaces = v126:get_table()
            end)
        end;
        v_u_13.datastore_update_participation_to_leaderboard = function(_, p_u_127, p_u_128, p_u_129) --[[ Name: datastore_update_participation_to_leaderboard ]] --[[ Line: 503 ]]
            --[[ Upvalues: (copy 1): v_u_121, (ref 2): v_u_2, (copy 3): p_u_12, (copy 4): v_u_117, (ref 5): v_u_10, (ref 6): v_u_5, (copy 7): v_u_13, (ref 8): v_u_11 ]]
            local v_u_130 = string.format("widsi_%d_%d", p_u_128, (p_u_129:get_song_index()))
            v_u_121:queue_key_request(p_u_127, function() --[[ Line: 506 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_12, (ref 3): v_u_117, (copy 4): v_u_130, (ref 5): v_u_10, (copy 6): p_u_129, (ref 7): v_u_5, (copy 8): p_u_128, (ref 9): v_u_13, (copy 10): p_u_127, (ref 11): v_u_11 ]]
                local v_u_131 = v_u_2:new()
                p_u_12._datastore_api:do_datastore_update(v_u_117, v_u_130, function(p132) --[[ Line: 511 ]]
                    --[[ Upvalues: (ref 1): v_u_131, (ref 2): v_u_10, (ref 3): p_u_129 ]]
                    if typeof(p132) == "table" then
                        v_u_131 = v_u_10:table_to_list(p132)
                    end;
                    v_u_10:try_leaderboard_week_participation_list_sorted_insert(v_u_131, p_u_129)
                    return v_u_10:list_to_table(v_u_131);
                end, function() --[[ Line: 521 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_128, (ref 3): p_u_129, (ref 4): v_u_131, (ref 5): v_u_13, (ref 6): v_u_10, (ref 7): p_u_12, (ref 8): p_u_127, (ref 9): v_u_11 ]]
                    v_u_5:spawn(function() --[[ Line: 522 ]]
                        --[[ Upvalues: (ref 1): p_u_128, (ref 2): p_u_129, (ref 3): v_u_131, (ref 4): v_u_13, (ref 5): v_u_10 ]]
                        local v_u_133 = v_u_131
                        v_u_13:datastore_update_cached_leaderboard_song_info_list(p_u_128, p_u_129:get_song_index(), function(p134) --[[ Line: 491 ]]
                            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_133 ]]
                            local v135 = v_u_10:list_to_leaderboard_song_info_score_list(v_u_133)
                            p134.TotalParticipants = v135:count()
                            p134.LeaderboardPlaces = v135:get_table()
                        end)
                    end)
                    v_u_5:spawn(function() --[[ Line: 525 ]]
                        --[[ Upvalues: (ref 1): p_u_12, (ref 2): p_u_127, (ref 3): v_u_5, (ref 4): p_u_129, (ref 5): v_u_11 ]]
                        local v136 = p_u_12._player_manager:id_to_player(p_u_127)
                        if v136 == nil then
                            return;
                        else
                            local v137 = p_u_12._player_manager:get_player_gameinstance(p_u_127)
                            if v137 == nil then
                                return;
                            else
                                local v138 = p_u_12._chat:gameid_get_channel(v137._game_id)
                                if v138 ~= nil then
                                    p_u_12._chat:get_chat_service():send_system_message_to_player_for_channel(v136, v138, string.format("New high score: %s! You are now %s on the weekly leaderboard for song \"%s\".", v_u_5:comma_value(p_u_129:get_leaderboard_song_info_score().Score), v_u_5:num_placify(p_u_129:get_leaderboard_song_info_score().Place), v_u_11:singleton():get_title_for_key(p_u_129:get_song_key())), function(p139) --[[ Line: 545 ]]
                                        --[[ Upvalues: (ref 1): v_u_5 ]]
                                        p139:set_channel_name("")
                                        p139:set_icon(v_u_5:get_leaderboard_icon())
                                    end)
                                end;
                            end;
                        end;
                    end)
                end)
            end)
        end;
        v_u_13.datastore_get_participation_leaderboard_for_week_and_song_index_no_cooldown = function(_, _, p140, p141, p_u_142) --[[ Name: datastore_get_participation_leaderboard_for_week_and_song_index_no_cooldown ]] --[[ Line: 556 ]]
            --[[ Upvalues: (copy 1): p_u_12, (copy 2): v_u_117, (ref 3): v_u_2, (ref 4): v_u_10 ]]
            p_u_12._datastore_api:do_datastore_get(v_u_117, string.format("widsi_%d_%d", p140, p141), function(_, p143) --[[ Line: 561 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_10, (copy 3): p_u_142 ]]
                local v144 = v_u_2:new()
                if typeof(p143) == "table" then
                    v144 = v_u_10:table_to_list(p143)
                end;
                p_u_142(v144)
            end)
        end;
        v_u_13.datastore_get_participation_leaderboard_for_week_and_song_index = function(p_u_145, p_u_146, p_u_147, p_u_148, p_u_149) --[[ Name: datastore_get_participation_leaderboard_for_week_and_song_index ]] --[[ Line: 571 ]]
            --[[ Upvalues: (copy 1): v_u_120 ]]
            v_u_120:queue_key_request(p_u_146, function() --[[ Line: 572 ]]
                --[[ Upvalues: (copy 1): p_u_145, (copy 2): p_u_146, (copy 3): p_u_147, (copy 4): p_u_148, (copy 5): p_u_149 ]]
                p_u_145:datastore_get_participation_leaderboard_for_week_and_song_index_no_cooldown(p_u_146, p_u_147, p_u_148, p_u_149)
            end)
        end;
        local function _(p150, p151) --[[ Name: player_id_week_id_to_key ]] --[[ Line: 583 ]]
            return string.format("piwi_%d_%d", p150, p151);
        end;
        local v_u_152 = v_u_9:new():set_cooldown(0.5)
        local v_u_153 = v_u_9:new():set_cooldown(2.5)
        v_u_13.datastore_create_player_week_id_song_index_participation = function(_, p154, p155, p156, p157, p_u_158) --[[ Name: datastore_create_player_week_id_song_index_participation ]] --[[ Line: 588 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_153, (copy 3): p_u_12, (copy 4): v_u_117, (ref 5): v_u_2, (ref 6): v_u_5 ]]
            local l_UserId_0 = p154.UserId
            local v_u_159 = string.format("piwi_%d_%d", l_UserId_0, p155)
            local v_u_160 = v_u_10:new(p156, p157, p155)
            local v161 = v_u_160:get_leaderboard_song_info_score()
            v161.RbxID = l_UserId_0
            v161.PlayerName = p154.Name
            local v_u_162 = false
            v_u_153:queue_key_request(l_UserId_0, function() --[[ Line: 598 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_117, (copy 3): v_u_159, (ref 4): v_u_2, (ref 5): v_u_10, (ref 6): v_u_162, (copy 7): v_u_160, (ref 8): v_u_5, (copy 9): p_u_158 ]]
                p_u_12._datastore_api:do_datastore_update(v_u_117, v_u_159, function(p163) --[[ Line: 602 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_10, (ref 3): v_u_162, (ref 4): v_u_160 ]]
                    local v164 = v_u_2:new()
                    if typeof(p163) == "table" then
                        v164 = v_u_10:table_to_list(p163)
                    end;
                    v_u_162 = v_u_10:try_player_week_participation_list_append(v164, v_u_160)
                    if v_u_162 == true then
                        return v_u_10:list_to_table(v164);
                    else
                        return nil;
                    end;
                end, function() --[[ Line: 619 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_158, (ref 3): v_u_162 ]]
                    v_u_5:spawn(function() --[[ Line: 620 ]]
                        --[[ Upvalues: (ref 1): p_u_158, (ref 2): v_u_162 ]]
                        p_u_158(v_u_162)
                    end)
                end)
            end)
        end;
        v_u_13.datastore_get_player_week_id_leaderboard_participations = function(_, p165, p166, p_u_167) --[[ Name: datastore_get_player_week_id_leaderboard_participations ]] --[[ Line: 628 ]]
            --[[ Upvalues: (copy 1): v_u_152, (copy 2): p_u_12, (copy 3): v_u_117, (ref 4): v_u_2, (ref 5): v_u_10 ]]
            local v_u_168 = string.format("piwi_%d_%d", p165, p166)
            v_u_152:queue_key_request(p165, function() --[[ Line: 630 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_117, (copy 3): v_u_168, (ref 4): v_u_2, (ref 5): v_u_10, (copy 6): p_u_167 ]]
                p_u_12._datastore_api:do_datastore_get(v_u_117, v_u_168, function(_, p169) --[[ Line: 634 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_10, (ref 3): p_u_167 ]]
                    local v170 = v_u_2:new()
                    if typeof(p169) == "table" then
                        v170 = v_u_10:table_to_list(p169)
                    end;
                    if p_u_167 ~= nil then
                        p_u_167(v170)
                    end;
                end)
            end)
        end;
        v_u_13.datastore_update_score_to_player_participation = function(_, p171, p172, p_u_173, p_u_174, p_u_175) --[[ Name: datastore_update_score_to_player_participation ]] --[[ Line: 647 ]]
            --[[ Upvalues: (copy 1): v_u_153, (copy 2): p_u_12, (copy 3): v_u_117, (ref 4): v_u_2, (ref 5): v_u_10, (ref 6): v_u_5, (ref 7): v_u_1 ]]
            local v_u_176 = string.format("piwi_%d_%d", p171, p172)
            v_u_153:queue_key_request(p171, function() --[[ Line: 649 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_117, (copy 3): v_u_176, (ref 4): v_u_2, (ref 5): v_u_10, (copy 6): p_u_174, (copy 7): p_u_173, (ref 8): v_u_5, (ref 9): v_u_1, (copy 10): p_u_175 ]]
                local v_u_177 = false
                local v_u_178 = nil
                p_u_12._datastore_api:do_datastore_update(v_u_117, v_u_176, function(p179) --[[ Line: 657 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_10, (ref 3): p_u_174, (ref 4): v_u_177, (ref 5): v_u_178, (ref 6): p_u_173, (ref 7): p_u_12, (ref 8): v_u_5, (ref 9): v_u_1 ]]
                    local v180 = v_u_2:new()
                    if typeof(p179) == "table" then
                        v180 = v_u_10:table_to_list(p179)
                    end;
                    local v181 = v_u_10:get_participation_from_list_of_song_index(v180, p_u_174)
                    local v182 = v181 == nil and 0 or v181:get_leaderboard_song_info_score().Score
                    local v183, v184 = v_u_10:try_player_week_participation_update_neu_score(v180, p_u_173, p_u_174, p_u_12._api:get_global_time())
                    v_u_177 = v183
                    v_u_178 = v184
                    if v_u_5:is_dev_build() then
                        v_u_1:puts("ServerLeaderboardDatastoreManager:datastore_update_score_to_player_participation update_success=%s, neu_high_score_participation=%s neu_score=%d pre_score=%d", tostring(v_u_177), v_u_5:table_to_string(v_u_178 and v_u_178:to_table() or {}), p_u_173.Score, v182)
                    end;
                    if v_u_177 == true then
                        return v_u_10:list_to_table(v180);
                    else
                        return nil;
                    end;
                end, function() --[[ Line: 693 ]]
                    --[[ Upvalues: (ref 1): v_u_177, (ref 2): v_u_178, (ref 3): p_u_175, (ref 4): v_u_5 ]]
                    if v_u_177 == true and (v_u_178 ~= nil and p_u_175 ~= nil) then
                        v_u_5:spawn(function() --[[ Line: 695 ]]
                            --[[ Upvalues: (ref 1): p_u_175, (ref 2): v_u_178 ]]
                            p_u_175(v_u_178)
                        end)
                    end;
                end)
            end)
        end;
        v_u_13.datastore_update_week_claim_song_index_to_rank = function(_, p185, p186, p_u_187, p_u_188) --[[ Name: datastore_update_week_claim_song_index_to_rank ]] --[[ Line: 704 ]]
            --[[ Upvalues: (copy 1): v_u_153, (copy 2): p_u_12, (copy 3): v_u_117, (ref 4): v_u_2, (ref 5): v_u_10 ]]
            local v_u_189 = string.format("piwi_%d_%d", p185, p186)
            v_u_153:queue_key_request(p185, function() --[[ Line: 706 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_117, (copy 3): v_u_189, (ref 4): v_u_2, (ref 5): v_u_10, (copy 6): p_u_187, (copy 7): p_u_188 ]]
                p_u_12._datastore_api:do_datastore_update(v_u_117, v_u_189, function(p190) --[[ Line: 710 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_10, (ref 3): p_u_187 ]]
                    local v191 = v_u_2:new()
                    if typeof(p190) == "table" then
                        v191 = v_u_10:table_to_list(p190)
                    end;
                    for _, v192 in v191:key_itr() do
                        local v193 = v192:get_song_index()
                        if p_u_187:contains(v193) then
                            v192:get_leaderboard_song_info_score().Place = p_u_187:get(v193)
                        end;
                        v192:set_reward_claimed(true)
                    end;
                    return v_u_10:list_to_table(v191);
                end, function() --[[ Line: 728 ]]
                    --[[ Upvalues: (ref 1): p_u_188 ]]
                    p_u_188()
                end)
            end)
        end;
        local v_u_194 = s_DataStoreService_0:GetDataStore("WLBInfoCache")
        local function _(p195) --[[ Name: key_cached_info_for_week_id ]] --[[ Line: 739 ]]
            return string.format("wlicache_%d", p195);
        end;
        local function _(p196, p_u_197) --[[ Name: webapi_get_liveops_info_only_leaderboard_song_info_list ]] --[[ Line: 742 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_2, (ref 3): v_u_7, (ref 4): v_u_6 ]]
            p_u_12._api:api_liveops_get_leaderboards_for_weekid(p196, function(p198) --[[ Line: 743 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): p_u_197 ]]
                table.sort(p198, function(p199, p200) --[[ Line: 746 ]]
                    return p199.LeaderboardID < p200.LeaderboardID;
                end)
                local v201 = v_u_2:new()
                local v202 = 0
                for v203 = 1, #p198 do
                    v202 = math.max(v202, p198[v203].LeaderboardID)
                end;
                for v204 = 1, #p198 do
                    local v205 = p198[v204]
                    local v206 = v_u_7:new()
                    v206.SongKey = v205.SongKey
                    v206.SongIndex = v205.LeaderboardID
                    v206.MaxSongIndex = v202
                    v206.EntryPrice = 500
                    v206.EntryPriceType = v_u_6.CurrencyType.Coins
                    v201:push_back(v206)
                end;
                p_u_197(v201)
            end)
        end;
        local v_u_207 = v_u_3:new()
        local function f_cached_list_copy(p208) --[[ Name: cached_list_copy ]] --[[ Line: 781 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_207, (ref 3): v_u_7 ]]
            local v209 = v_u_2:new()
            local v210 = v_u_2:new()
            if v_u_207:contains(p208) then
                v210 = v_u_207:get(p208)
            end;
            for _, v211 in v210:key_itr() do
                v209:push_back(v_u_7:from_leaderboard_info_table(v211))
            end;
            return v209;
        end;
        local v_u_212 = v_u_3:new()
        local v_u_213 = v_u_3:new()
        local v_u_214 = v_u_2:new()
        v_u_13.get_validated_liveops_info_only_leaderboard_song_info_list = function(_, p_u_215, p216) --[[ Name: get_validated_liveops_info_only_leaderboard_song_info_list ]] --[[ Line: 796 ]]
            --[[ Upvalues: (copy 1): v_u_212, (copy 2): v_u_214, (copy 3): v_u_213, (copy 4): v_u_207, (copy 5): f_cached_list_copy, (copy 6): p_u_12, (ref 7): v_u_2, (ref 8): v_u_7, (ref 9): v_u_6 ]]
            local v217 = tick()
            if v_u_212:contains(p_u_215) ~= true then
                v_u_212:add(p_u_215, 0)
            end;
            if v217 - v_u_212:get(p_u_215) > 120 then
                v_u_214:push_back(p216)
                if v_u_213:contains(p_u_215) ~= true then
                    v_u_213:add(p_u_215, true)
                    local function v_u_220(p218) --[[ Line: 807 ]]
                        --[[ Upvalues: (ref 1): v_u_207, (copy 2): p_u_215, (ref 3): v_u_212, (ref 4): v_u_214, (ref 5): f_cached_list_copy, (ref 6): v_u_213 ]]
                        v_u_207:add(p_u_215, p218)
                        v_u_212:add(p_u_215, tick())
                        for _, v219 in v_u_214:key_itr() do
                            v219((f_cached_list_copy(p_u_215)))
                        end;
                        v_u_214:clear()
                        v_u_213:remove(p_u_215)
                    end;
                    p_u_12._api:api_liveops_get_leaderboards_for_weekid(p_u_215, function(p221) --[[ Line: 743 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): v_u_220 ]]
                        table.sort(p221, function(p222, p223) --[[ Line: 746 ]]
                            return p222.LeaderboardID < p223.LeaderboardID;
                        end)
                        local v224 = v_u_2:new()
                        local v225 = 0
                        for v226 = 1, #p221 do
                            v225 = math.max(v225, p221[v226].LeaderboardID)
                        end;
                        for v227 = 1, #p221 do
                            local v228 = p221[v227]
                            local v229 = v_u_7:new()
                            v229.SongKey = v228.SongKey
                            v229.SongIndex = v228.LeaderboardID
                            v229.MaxSongIndex = v225
                            v229.EntryPrice = 500
                            v229.EntryPriceType = v_u_6.CurrencyType.Coins
                            v224:push_back(v229)
                        end;
                        v_u_220(v224)
                    end)
                    return;
                end;
            else
                p216((f_cached_list_copy(p_u_215)))
            end;
        end;
        local v_u_230 = v_u_9:new():set_cooldown(0.25)
        local function _(p_u_231) --[[ Name: limit_length_to_max_leaderboard_place_entries ]] --[[ Line: 827 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_2 ]]
            v_u_5:ptry(function() --[[ Line: 828 ]]
                --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_231 ]]
                local v232 = v_u_2:new(p_u_231.LeaderboardPlaces)
                while v232:count() > 50 do
                    v232:pop_back()
                end;
            end)
        end;
        v_u_13.datastore_get_cached_leaderboard_song_info_list = function(p_u_233, p_u_234, p_u_235) --[[ Name: datastore_get_cached_leaderboard_song_info_list ]] --[[ Line: 836 ]]
            --[[ Upvalues: (copy 1): v_u_230, (ref 2): v_u_8, (ref 3): v_u_2, (copy 4): p_u_12, (copy 5): v_u_194, (ref 6): v_u_3, (ref 7): v_u_5 ]]
            local v_u_236 = string.format("wlicache_%d", p_u_234)
            v_u_230:queue_key_request(0, function() --[[ Line: 839 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2, (copy 3): p_u_233, (copy 4): p_u_234, (ref 5): p_u_12, (ref 6): v_u_194, (copy 7): v_u_236, (copy 8): p_u_235, (ref 9): v_u_3, (ref 10): v_u_5 ]]
                local v_u_237 = v_u_8.Builder:new()
                local v_u_238 = v_u_2:new()
                local v_u_239 = nil
                v_u_237:begin()
                p_u_233:get_validated_liveops_info_only_leaderboard_song_info_list(p_u_234, function(p240) --[[ Line: 845 ]]
                    --[[ Upvalues: (ref 1): v_u_238, (copy 2): v_u_237 ]]
                    v_u_238 = p240
                    v_u_237:finish()
                end)
                v_u_237:begin()
                p_u_12._datastore_api:do_datastore_get(v_u_194, v_u_236, function(_, p241) --[[ Line: 854 ]]
                    --[[ Upvalues: (ref 1): v_u_239, (copy 2): v_u_237 ]]
                    v_u_239 = p241
                    v_u_237:finish()
                end)
                v_u_237:wait_for_finish(function() --[[ Line: 860 ]]
                    --[[ Upvalues: (ref 1): v_u_239, (ref 2): p_u_12, (ref 3): v_u_194, (ref 4): v_u_236, (ref 5): v_u_238, (ref 6): p_u_235, (ref 7): v_u_3, (ref 8): v_u_2, (ref 9): p_u_234, (ref 10): v_u_5 ]]
                    if v_u_239 == nil then
                        p_u_12._datastore_api:do_datastore_set(v_u_194, v_u_236, v_u_238:get_table(), function() --[[ Line: 867 ]]
                            --[[ Upvalues: (ref 1): p_u_235, (ref 2): v_u_238 ]]
                            p_u_235(v_u_238)
                        end)
                    else
                        local v242 = v_u_3:new()
                        for _, v243 in v_u_2:new(v_u_239):key_itr() do
                            v242:add(v243.SongIndex, v243)
                        end;
                        for _, v_u_244 in v_u_238:key_itr() do
                            if p_u_234 == p_u_12._api:get_week_id() then
                                v_u_244.TimeRemaining = p_u_12._api:get_time_to_next_week_sec()
                            else
                                v_u_244.TimeRemaining = 0
                            end;
                            if v242:contains(v_u_244.SongIndex) then
                                local v245 = v242:get(v_u_244.SongIndex)
                                v_u_244.TotalParticipants = v245.TotalParticipants
                                v_u_244.LeaderboardPlaces = v245.LeaderboardPlaces
                                v_u_5:ptry(function() --[[ Line: 828 ]]
                                    --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_244 ]]
                                    local v246 = v_u_2:new(v_u_244.LeaderboardPlaces)
                                    while v246:count() > 50 do
                                        v246:pop_back()
                                    end;
                                end)
                            end;
                        end;
                        p_u_235(v_u_238)
                    end;
                end)
            end)
        end;
        v_u_13.datastore_update_cached_leaderboard_song_info_list = function(p_u_247, p_u_248, p_u_249, p_u_250) --[[ Name: datastore_update_cached_leaderboard_song_info_list ]] --[[ Line: 897 ]]
            --[[ Upvalues: (copy 1): v_u_230, (copy 2): p_u_12, (copy 3): v_u_194, (ref 4): v_u_2, (ref 5): v_u_5, (ref 6): v_u_1 ]]
            local v_u_251 = string.format("wlicache_%d", p_u_248)
            v_u_230:queue_key_request(0, function() --[[ Line: 899 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_194, (copy 3): v_u_251, (ref 4): v_u_2, (copy 5): p_u_249, (copy 6): p_u_250, (ref 7): v_u_5, (ref 8): v_u_1, (copy 9): p_u_247, (copy 10): p_u_248 ]]
                local v_u_252 = false
                p_u_12._datastore_api:do_datastore_update(v_u_194, v_u_251, function(p253) --[[ Line: 904 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_249, (ref 3): p_u_250, (ref 4): v_u_5, (ref 5): v_u_252, (ref 6): v_u_1 ]]
                    if typeof(p253) ~= "table" then
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("ServerLeaderboardDatastoreManager:datastore_update_cached_leaderboard_song_info_list - no cached data found")
                        end;
                        return nil;
                    end;
                    local v254 = v_u_2:new(p253)
                    for v255 = 1, v254:count() do
                        local v_u_256 = v254:get(v255)
                        if v_u_256.SongIndex == p_u_249 then
                            p_u_250(v_u_256)
                            v_u_5:ptry(function() --[[ Line: 828 ]]
                                --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_256 ]]
                                local v257 = v_u_2:new(v_u_256.LeaderboardPlaces)
                                while v257:count() > 50 do
                                    v257:pop_back()
                                end;
                            end)
                            break;
                        end;
                    end;
                    v_u_252 = true
                    return v254:get_table();
                end, function() --[[ Line: 928 ]]
                    --[[ Upvalues: (ref 1): v_u_252, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): p_u_247, (ref 5): p_u_248, (ref 6): p_u_249, (ref 7): p_u_250 ]]
                    if v_u_252 == false then
                        v_u_5:spawn(function() --[[ Line: 930 ]]
                            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_5, (ref 3): p_u_247, (ref 4): p_u_248, (ref 5): p_u_249, (ref 6): p_u_250 ]]
                            v_u_1:warnf("datastore_update_cached_leaderboard_song_info_list not found, getting cached and retrying...")
                            v_u_5:wait(0.1)
                            p_u_247:datastore_get_cached_leaderboard_song_info_list(p_u_248, function() --[[ Line: 933 ]]
                                --[[ Upvalues: (ref 1): p_u_247, (ref 2): p_u_248, (ref 3): p_u_249, (ref 4): p_u_250 ]]
                                p_u_247:datastore_update_cached_leaderboard_song_info_list(p_u_248, p_u_249, p_u_250)
                            end)
                        end)
                    end;
                end)
            end)
        end;
        return v_u_13;
    end
};
