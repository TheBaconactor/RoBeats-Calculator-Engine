-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Time elapsed: 13 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.PlayerSongStatCollection)
local v_u_5 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_6 = require(game.ReplicatedStorage.Server.ServerDatastoreImpl.ServerPlayerSongStatsDatastoreManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerSongPlay)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.Shared.MatchMode)
local s_HttpService_0 = game:GetService("HttpService")
local v42 = {
    ["BatchWritePlayElement"] = {},
    ["new"] = function(_, p_u_11) --[[ Name: new ]] --[[ Line: 79 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_3, (copy 5): v_u_1, (copy 6): v_u_4, (copy 7): v_u_8, (copy 8): v_u_7, (copy 9): v_u_9 ]]
        local v12 = {}
        local v_u_13 = v_u_2:new()
        local v_u_14 = v_u_6:new(p_u_11)
        v12.get_song_stats_datastore_manager = function(_) --[[ Name: get_song_stats_datastore_manager ]] --[[ Line: 85 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            return v_u_14;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_11, (ref 3): v_u_3, (copy 4): v_u_14, (ref 5): v_u_1, (copy 6): v_u_13, (ref 7): v_u_4, (ref 8): v_u_8, (ref 9): v_u_7, (ref 10): v_u_9 ]]
            local v_u_15 = v_u_5:new():set_cooldown(2)
            p_u_11._evt:wait_on_event(v_u_3.EVT_PlayerSongStats_ClientRequestStats, function(p_u_16) --[[ Line: 92 ]]
                --[[ Upvalues: (copy 1): v_u_15, (ref 2): v_u_14, (ref 3): v_u_1, (ref 4): v_u_13, (ref 5): v_u_4, (ref 6): p_u_11, (ref 7): v_u_3 ]]
                local l_UserId_0 = p_u_16.UserId
                v_u_15:queue_key_request(l_UserId_0, function() --[[ Line: 94 ]]
                    --[[ Upvalues: (ref 1): v_u_14, (copy 2): l_UserId_0, (ref 3): v_u_1, (ref 4): v_u_13, (ref 5): v_u_4, (ref 6): p_u_11, (ref 7): v_u_3, (copy 8): p_u_16 ]]
                    v_u_14:dsapi_player_song_stats_get(l_UserId_0, function(p17, p18) --[[ Line: 95 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_13, (ref 3): l_UserId_0, (ref 4): v_u_4, (ref 5): p_u_11, (ref 6): v_u_3, (ref 7): p_u_16 ]]
                        if p18 == nil then
                            v_u_1:errf("SPRemoteEvent.EVT_PlayerSongStats_ClientRequestStats response ERR(%s)", p17)
                        end;
                        if v_u_13:contains(l_UserId_0) == false then
                            v_u_13:add(l_UserId_0, v_u_4:new())
                        end;
                        v_u_13:get(l_UserId_0):load_from_json_obj(p18)
                        p_u_11._evt:fire_event_to_client(v_u_3.EVT_PlayerSongStats_ServerRequestStatsResponse, p_u_16, p18)
                    end)
                end)
            end)
            local v_u_19 = v_u_5:new():set_cooldown(2)
            p_u_11._evt:wait_on_event(v_u_3.EVT_PlayerSongStats_ClientRequestRank, function(p_u_20, p_u_21) --[[ Line: 113 ]]
                --[[ Upvalues: (copy 1): v_u_19, (ref 2): v_u_14, (ref 3): v_u_1, (ref 4): v_u_13, (ref 5): v_u_4, (ref 6): p_u_11, (ref 7): v_u_3 ]]
                local l_UserId_1 = p_u_20.UserId
                v_u_19:queue_key_request(l_UserId_1, function() --[[ Line: 115 ]]
                    --[[ Upvalues: (ref 1): v_u_14, (copy 2): l_UserId_1, (copy 3): p_u_21, (ref 4): v_u_1, (ref 5): v_u_13, (ref 6): v_u_4, (ref 7): p_u_11, (ref 8): v_u_3, (copy 9): p_u_20 ]]
                    v_u_14:dsapi_player_song_stats_get_rank(l_UserId_1, p_u_21, function(p22, p23) --[[ Line: 116 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_13, (ref 3): l_UserId_1, (ref 4): v_u_4, (ref 5): p_u_11, (ref 6): v_u_3, (ref 7): p_u_20 ]]
                        if p23 == nil then
                            v_u_1:errf("SPRemoteEvent.EVT_PlayerSongStats_ClientRequestRank response ERR(%s)", p22)
                        end;
                        if v_u_13:contains(l_UserId_1) == false then
                            v_u_13:add(l_UserId_1, v_u_4:new())
                        end;
                        v_u_13:get(l_UserId_1):load_from_rank_request_json_obj(p23)
                        p_u_11._evt:fire_event_to_client(v_u_3.EVT_PlayerSongStats_ServerRequestRankResponse, p_u_20, p23)
                    end)
                end)
            end)
            local v_u_24 = v_u_5:new():set_cooldown(1.5)
            p_u_11._evt:wait_on_event(v_u_3.EVT_PlayerSongStats_ClientRequestPlayerSongPlayList, function(p_u_25, p_u_26, p_u_27) --[[ Line: 134 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_7, (copy 3): v_u_24, (ref 4): p_u_11, (ref 5): v_u_3, (ref 6): v_u_9, (ref 7): v_u_14 ]]
                v_u_8:is_enum_member(p_u_26, v_u_7.Category)
                v_u_24:queue_key_request(p_u_25.UserId, function() --[[ Line: 138 ]]
                    --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_3, (copy 3): p_u_25, (ref 4): v_u_7, (copy 5): p_u_26, (ref 6): v_u_8, (ref 7): v_u_9, (copy 8): p_u_27, (ref 9): v_u_14 ]]
                    local function _(p28) --[[ Name: response_callback ]] --[[ Line: 139 ]]
                        --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_3, (ref 3): p_u_25, (ref 4): v_u_7 ]]
                        p_u_11._evt:fire_event_to_client(v_u_3.EVT_PlayerSongStats_ServerRequestPlayerSongPlayListResponse, p_u_25, v_u_7:list_to_tab(p28))
                    end;
                    if p_u_26 == v_u_7.Category.TopScores then
                        v_u_8:is_true(v_u_9:singleton():contains_key(p_u_27))
                        v_u_14:datastore_get_songkey_top_scores_play_list_no_cooldown(p_u_27, function(p29) --[[ Line: 146 ]]
                            --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_3, (ref 3): p_u_25, (ref 4): v_u_7 ]]
                            p_u_11._evt:fire_event_to_client(v_u_3.EVT_PlayerSongStats_ServerRequestPlayerSongPlayListResponse, p_u_25, v_u_7:list_to_tab(p29))
                        end)
                        return;
                    elseif p_u_26 == v_u_7.Category.RecentScores then
                        v_u_8:is_true(v_u_9:singleton():contains_key(p_u_27))
                        v_u_14:datastore_get_songkey_recent_plays_play_list_no_cooldown(p_u_27, function(p30) --[[ Line: 153 ]]
                            --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_3, (ref 3): p_u_25, (ref 4): v_u_7 ]]
                            p_u_11._evt:fire_event_to_client(v_u_3.EVT_PlayerSongStats_ServerRequestPlayerSongPlayListResponse, p_u_25, v_u_7:list_to_tab(p30))
                        end)
                    elseif p_u_26 == v_u_7.Category.PlayerRecentScores then
                        v_u_14:datastore_get_player_recent_plays_play_list_no_cooldown(p_u_25.UserId, function(p31) --[[ Line: 158 ]]
                            --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_3, (ref 3): p_u_25, (ref 4): v_u_7 ]]
                            p_u_11._evt:fire_event_to_client(v_u_3.EVT_PlayerSongStats_ServerRequestPlayerSongPlayListResponse, p_u_25, v_u_7:list_to_tab(p31))
                        end)
                    end;
                end)
            end)
        end;
        v12.batch_write_play = function(_, p32, p33, p_u_34) --[[ Name: batch_write_play ]] --[[ Line: 169 ]]
            --[[ Upvalues: (copy 1): v_u_14, (ref 2): v_u_1, (copy 3): p_u_11, (copy 4): v_u_13 ]]
            if p_u_34:count() ~= 0 then
                v_u_14:dsapi_player_song_stats_batch_write_play(p32, p33, p_u_34, function(p35, p36) --[[ Line: 172 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_34, (ref 3): p_u_11, (ref 4): v_u_13 ]]
                    if p36 == nil then
                        v_u_1:errf("batch_write_play err(%s)", p35)
                    end;
                    for v37 = 1, #p36 do
                        local v38 = p36[v37]
                        for v39 = 1, p_u_34:count() do
                            local v40 = p_u_34:get(v39)
                            if v40:matches_json_element(v38) then
                                v40:callback(p_u_11, v_u_13, v38)
                            end;
                        end;
                    end;
                end)
            end;
        end;
        v12.player_disconnecting = function(_, p41) --[[ Name: player_disconnecting ]] --[[ Line: 188 ]]
            --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_14 ]]
            v_u_13:remove(p41)
            v_u_14:player_disconnecting(p41)
        end;
        f_cons()
        return v12;
    end
}
v42.BatchWritePlayElement.new = function(_, p_u_43, p_u_44, p_u_45, p_u_46, p_u_47, p_u_48, p_u_49, p_u_50, p_u_51, p_u_52) --[[ Name: new ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): s_HttpService_0, (copy 3): v_u_3, (copy 4): v_u_8, (copy 5): v_u_7 ]]
    local v53 = {}
    local l_UserId_2 = p_u_43.UserId
    local l_Casual_0 = v_u_10.Casual
    v53.get_api_data = function(_) --[[ Name: get_api_data ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): l_UserId_2, (copy 2): p_u_44, (copy 3): p_u_45, (copy 4): p_u_46, (copy 5): p_u_47, (copy 6): p_u_48, (copy 7): p_u_49, (ref 8): s_HttpService_0, (copy 9): p_u_50, (copy 10): p_u_51 ]]
        return {
            ["rbxid"] = l_UserId_2,
            ["songid"] = p_u_44,
            ["score"] = p_u_45,
            ["grade"] = p_u_46,
            ["accuracy"] = p_u_47,
            ["naked_score"] = p_u_48,
            ["gear_power"] = p_u_49,
            ["play_json"] = s_HttpService_0:JSONEncode(p_u_50),
            ["gear_json"] = s_HttpService_0:JSONEncode(p_u_51)
        };
    end;
    v53.matches_json_element = function(_, p54) --[[ Name: matches_json_element ]] --[[ Line: 48 ]]
        --[[ Upvalues: (copy 1): l_UserId_2 ]]
        return p54.PlayerId == l_UserId_2;
    end;
    v53.callback = function(_, p55, p56, p57) --[[ Name: callback ]] --[[ Line: 52 ]]
        --[[ Upvalues: (copy 1): l_UserId_2, (ref 2): v_u_3, (copy 3): p_u_43, (copy 4): p_u_52 ]]
        if p56:contains(l_UserId_2) == true then
            p56:get(l_UserId_2):write_play_result_from_json_obj(p57)
        end;
        p55._evt:fire_event_to_client(v_u_3.EVT_PlayerSongStats_ServerWritePlayResponse, p_u_43, p57)
        p_u_52(p57)
    end;
    v53.set_match_mode = function(_, p58) --[[ Name: set_match_mode ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_10, (ref 3): l_Casual_0 ]]
        v_u_8:is_enum_member(p58, v_u_10)
        l_Casual_0 = p58
    end;
    v53.get_as_player_song_play = function(_) --[[ Name: get_as_player_song_play ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): l_UserId_2, (copy 3): p_u_44, (copy 4): p_u_43, (copy 5): p_u_45, (copy 6): p_u_48, (copy 7): p_u_47, (copy 8): p_u_49, (ref 9): l_Casual_0 ]]
        local v59 = v_u_7:new(l_UserId_2, p_u_44)
        v59:set_rbxname(p_u_43.Name)
        v59:set_score(p_u_45)
        v59:set_naked_score(p_u_48)
        v59:set_accuracy(p_u_47)
        v59:set_gear_power(p_u_49)
        v59:set_match_mode(l_Casual_0)
        return v59;
    end;
    return v53;
end;
return v42;
