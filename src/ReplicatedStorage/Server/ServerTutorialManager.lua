-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.TutorialInfo)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.MatchLeavePenalty)
local v_u_10 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_11 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_13 = require(game.ReplicatedStorage.Tutorial.TutorialData)
local v_u_14 = require(game.ServerScriptService.SPDiveAPI)
local v_u_15 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
return {
    ["new"] = function(_, p_u_17) --[[ Name: new ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_3, (copy 3): v_u_7, (copy 4): v_u_4, (copy 5): v_u_1, (copy 6): v_u_2, (copy 7): v_u_5, (copy 8): v_u_10, (copy 9): v_u_13, (copy 10): v_u_9, (copy 11): v_u_12, (copy 12): v_u_11, (copy 13): v_u_16, (copy 14): v_u_6, (copy 15): v_u_15, (copy 16): v_u_14 ]]
        local v18 = {}
        local v_u_19 = v_u_8:get_song_select_key_set()
        local v_u_20 = v_u_8:get_song_select_table()
        local v_u_21 = v_u_3:new()
        v18.start = function(_) --[[ Name: start ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_17, (ref 3): v_u_4, (copy 4): v_u_20, (ref 5): v_u_1, (copy 6): v_u_19, (ref 7): v_u_2, (ref 8): v_u_5, (ref 9): v_u_10, (ref 10): v_u_13, (ref 11): v_u_9, (ref 12): v_u_12, (ref 13): v_u_11, (ref 14): v_u_16, (ref 15): v_u_6, (ref 16): v_u_15, (copy 17): v_u_21, (ref 18): v_u_3, (ref 19): v_u_14 ]]
            local function _(p22, p23) --[[ Name: playerblob_add_song_if_count_zero ]] --[[ Line: 32 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                if v_u_7:get_song_key_owned_count(p22, p23) <= 0 then
                    v_u_7:add_song(p22, p23)
                end;
            end;
            p_u_17._evt:wait_on_event(v_u_4.EVT_Tutorial_ClientRequestSongSelectInfo, function(p24) --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_4, (ref 3): v_u_20 ]]
                p_u_17._evt:fire_event_to_client(v_u_4.EVT_Tutorial_ServerSongSelectInfoResponse, p24, v_u_20)
            end)
            p_u_17._evt:wait_on_event(v_u_4.EVT_Tutorial_ClientSongSelectSubmitChoices, function(p_u_25, p_u_26) --[[ Line: 43 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_7, (ref 3): v_u_1, (ref 4): v_u_19, (ref 5): v_u_2, (ref 6): v_u_20, (ref 7): v_u_4 ]]
                p_u_17._player_blob_manager:enqueue_blob_sync_request(p_u_25.UserId, v_u_7.PlayerBlobRequestType.Get, function(p_u_27) --[[ Line: 47 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_1, (copy 3): p_u_26, (ref 4): v_u_19, (ref 5): v_u_2, (ref 6): v_u_20, (ref 7): p_u_17, (copy 8): p_u_25, (ref 9): v_u_4 ]]
                    if p_u_27.TutorialStage == v_u_7.TutorialStage.LegacyTutorialComplete or p_u_27.TutorialStage == v_u_7.TutorialStage.TutorialSongAcquired then
                        if #p_u_26 == 3 then
                            for v28 = 1, #p_u_26 do
                                if v_u_19:contains(p_u_26[v28]) == false then
                                    v_u_1:errf("SPRemoteEvent.EVT_Tutorial_ServerSongSelectSubmitChoicesResponse error validating to __song_select_key_set")
                                    return;
                                end;
                            end;
                            v_u_2:new():push_back_table_list(v_u_20)
                            for v29 = 1, #p_u_26 do
                                v_u_7:add_song(p_u_27, p_u_26[v29])
                            end;
                            p_u_27.TutorialStage = v_u_7.TutorialStage.TutorialComplete
                            p_u_17._player_blob_manager:enqueue_blob_sync_request(p_u_25.UserId, v_u_7.PlayerBlobRequestType.Write, function() --[[ Line: 80 ]]
                                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_27, (ref 3): p_u_17, (ref 4): v_u_4, (ref 5): p_u_25 ]]
                                v_u_1:puts("SPRemoteEvent.EVT_Tutorial_ServerSongSelectSubmitChoicesResponse on PlayerBlob tutorial_stage(%d)", p_u_27.TutorialStage)
                                p_u_17._evt:fire_event_to_client(v_u_4.EVT_Tutorial_ServerSongSelectSubmitChoicesResponse, p_u_25)
                            end)
                        else
                            v_u_1:errf("SPRemoteEvent.EVT_Tutorial_ServerSongSelectSubmitChoicesResponse song_request_list len(%d)", #p_u_26)
                        end;
                    else
                        v_u_1:errf("SPRemoteEvent.EVT_Tutorial_ServerSongSelectSubmitChoicesResponse on PlayerBlob tutorial_stage(%d)", p_u_27.TutorialStage)
                        return;
                    end;
                end)
            end)
            p_u_17._evt:wait_on_event(v_u_4.EVT_Warning_ClientMarkAsRead, function(p_u_30) --[[ Line: 89 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_4 ]]
                local v31 = p_u_17._player_blob_manager:get_cached_blob(p_u_30.UserId)
                if v31 == nil then
                    v_u_1:errf("EVT_Warning_ClientMarkAsRead cannot find blob")
                end;
                v_u_7:set_warning(v31, false, "")
                p_u_17._player_blob_manager:enqueue_blob_sync_request(p_u_30.UserId, v_u_7.PlayerBlobRequestType.Write, function() --[[ Line: 98 ]]
                    --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_4, (copy 3): p_u_30 ]]
                    p_u_17._evt:fire_event_to_client(v_u_4.EVT_Warning_ServerAcknowledgeClientMarkAsRead, p_u_30)
                end)
            end)
            p_u_17._evt:wait_on_event(v_u_4.EVT_Tutorial_ClientRequestTutorialSongGive, function(p_u_32) --[[ Line: 104 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_5, (ref 5): v_u_10, (ref 6): v_u_13, (ref 7): v_u_4 ]]
                local v33 = p_u_17._player_blob_manager:get_cached_blob(p_u_32.UserId)
                if v33 == nil then
                    v_u_1:errf("EVT_Tutorial_ClientRequestTutorialSongGive cannot find blob")
                end;
                if v33.TutorialStage == v_u_7.TutorialStage.LegacyTutorialComplete then
                    v33.TutorialStage = v_u_7.TutorialStage.TutorialComplete
                elseif v33.TutorialStage == v_u_7.TutorialStage.NewPlayer then
                    if v_u_5.TutorialSkipSongSelect == true then
                        v33.TutorialStage = v_u_7.TutorialStage.TutorialComplete
                        v_u_7:set_coin_currency(v33, (math.max(v_u_10.PLAYER_STARTING_COINS, v_u_7:get_coin_currency(v33))))
                    else
                        v33.TutorialStage = v_u_7.TutorialStage.TutorialSongAcquired
                    end;
                else
                    v_u_1:errf("EVT_Tutorial_ClientRequestTutorialSongGive incorrect tutorial stage")
                end;
                local v_u_34 = v_u_13:get_tutorial_grant_songkey()
                if v_u_7:get_song_key_owned_count(v33, v_u_34) <= 0 then
                    v_u_7:add_song(v33, v_u_34)
                end;
                p_u_17._player_blob_manager:enqueue_blob_sync_request(p_u_32.UserId, v_u_7.PlayerBlobRequestType.Write, function() --[[ Line: 130 ]]
                    --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_4, (copy 3): p_u_32, (copy 4): v_u_34 ]]
                    p_u_17._evt:fire_event_to_client(v_u_4.EVT_Tutorial_ServerResponseTutorialSongGive, p_u_32, v_u_34)
                end)
            end)
            p_u_17._evt:wait_on_event(v_u_4.EVT_Startup_ClientRequestApplyJustLeftMatch, function(p_u_35) --[[ Line: 136 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_9, (ref 5): v_u_4 ]]
                local v36 = p_u_17._player_blob_manager:get_cached_blob(p_u_35.UserId)
                if v36 == nil then
                    v_u_1:errf("EVT_Startup_ClientRequestApplyJustLeftMatch cannot find blob")
                end;
                if v_u_7:get_just_left_match(v36) ~= true then
                    v_u_1:errf("EVT_Startup_ClientRequestApplyJustLeftMatch just_left_match_false")
                end;
                local v_u_37 = v_u_9:on_startup_apply_just_left_match_penalty_for_playerblob(v36, p_u_17._api:get_global_time())
                p_u_17._player_blob_manager:enqueue_blob_sync_request(p_u_35.UserId, v_u_7.PlayerBlobRequestType.Write, function() --[[ Line: 146 ]]
                    --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_4, (copy 3): p_u_35, (copy 4): v_u_37 ]]
                    p_u_17._evt:fire_event_to_client(v_u_4.EVT_Startup_ServerAcknowledgeApplyJustLeftMatch, p_u_35, v_u_37)
                end)
            end)
            p_u_17._evt:wait_on_event(v_u_4.EVT_MatchLeavePenalty_ClientRequestRequiredProductID, function(p38) --[[ Line: 152 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_1, (ref 3): v_u_9, (ref 4): v_u_4 ]]
                local v39 = p_u_17._player_blob_manager:get_cached_blob(p38.UserId)
                if v39 == nil then
                    v_u_1:errf("EVT_Startup_ClientRequestApplyJustLeftMatch cannot find blob")
                end;
                p_u_17._evt:fire_event_to_client(v_u_4.EVT_MatchLeavePenalty_ServerRespondRequiredProductID, p38, (v_u_9:get_required_productid_to_clear_penalty(v39, p_u_17._api:get_global_time())))
            end)
            p_u_17._evt:wait_on_event(v_u_4.EVT_Holiday_Xmas_ClientRequest, function(p_u_40) --[[ Line: 159 ]]
                --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_4, (ref 3): v_u_12, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_7, (ref 7): v_u_16, (ref 8): v_u_6 ]]
                local function f_response(p41, p42) --[[ Name: response ]] --[[ Line: 163 ]]
                    --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_4, (copy 3): p_u_40 ]]
                    p_u_17._evt:fire_event_to_client(v_u_4.EVT_Holiday_Xmas_ServerResponse, p_u_40, p_u_17._api:get_day_id(), p41, p42)
                end;
                p_u_17._player_blob_manager:get_verified_cached_blob(p_u_40.UserId, function(p43) --[[ Line: 166 ]]
                    --[[ Upvalues: (ref 1): p_u_17, (ref 2): v_u_12, (ref 3): v_u_10, (copy 4): f_response, (ref 5): v_u_11, (ref 6): v_u_7, (copy 7): p_u_40, (ref 8): v_u_16, (ref 9): v_u_6, (ref 10): v_u_4 ]]
                    if p_u_17._api:get_day_event_list():is_event_type_active(v_u_12.EventType.HolidayEvent) == true and p_u_17._api:get_day_id() >= v_u_10.NEWYEARS_2021_DAY then
                        if v_u_11:get_owned_danceid_to_equipped_dict(p43):contains(v_u_10.NEWYEARS_2021_DANCEID) == true then
                            p_u_17._evt:fire_event_to_client(v_u_4.EVT_Holiday_Xmas_ServerResponse, p_u_40, p_u_17._api:get_day_id(), false, "")
                        else
                            v_u_11:add_owned_danceid(p43, v_u_10.NEWYEARS_2021_DANCEID)
                            v_u_11:set_danceid_equipped(p43, v_u_10.NEWYEARS_2021_DANCEID, true)
                            v_u_7:set_star_currency(p43, v_u_7:get_star_currency(p43) + v_u_10.NEWYEARS_2021_STARREWARD)
                            for v44 = 1, #v_u_10.NEWYEARS_2021_SONGREWARDS do
                                v_u_7:add_song(p43, v_u_10.NEWYEARS_2021_SONGREWARDS[v44])
                            end;
                            p_u_17._player_blob_manager:enqueue_blob_sync_request(p_u_40.UserId, v_u_7.PlayerBlobRequestType.Write, function(_) --[[ Line: 184 ]]
                                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_10, (ref 3): v_u_6, (ref 4): p_u_17, (ref 5): v_u_4, (ref 6): p_u_40 ]]
                                local v45 = string.format("Happy New Years from RoBeats!\nYou got:\nDance: %s\n%d Stars", v_u_16:singleton():get_dance_name_for_id(v_u_10.NEWYEARS_2021_DANCEID), v_u_10.NEWYEARS_2021_STARREWARD)
                                for v46 = 1, #v_u_10.NEWYEARS_2021_SONGREWARDS do
                                    v45 = v45 .. string.format("\nSong: %s", v_u_6:singleton():get_title_for_key(v_u_10.NEWYEARS_2021_SONGREWARDS[v46]))
                                end;
                                p_u_17._evt:fire_event_to_client(v_u_4.EVT_Holiday_Xmas_ServerResponse, p_u_40, p_u_17._api:get_day_id(), true, v45)
                            end)
                        end;
                    else
                        return f_response(false, "");
                    end;
                end)
            end)
            p_u_17._evt:wait_on_event(v_u_4.EVT_Tutorial_ClientReportTutorialStep, function(p47, p48) --[[ Line: 201 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_13, (ref 3): v_u_21, (ref 4): v_u_3, (ref 5): v_u_1, (ref 6): v_u_14 ]]
                v_u_15:is_enum_member(p48, v_u_13.Step)
                if v_u_21:contains(p47.UserId) ~= true then
                    v_u_21:add(p47.UserId, v_u_3:new())
                end;
                local v49 = v_u_21:get(p47.UserId)
                if v49:contains(p48) then
                    return v_u_1:warnf("_player_id_to_reported_tutorial_step_set(%d) contains(%d)", p47.UserId, p48);
                end;
                v49:add_set(p48)
                if p48 == v_u_13.Step.TutorialBegin then
                    v_u_14:event_tutorial_started(p47)
                end;
                v_u_14:event_tutorial_step_completed(p47, p48)
                if p48 == v_u_13.Step.TutorialLoadedIntoLobby then
                    v_u_14:event_tutorial_completed(p47, p48, false)
                end;
            end)
        end;
        v18.get_starter_song_key_set = function(_) --[[ Name: get_starter_song_key_set ]] --[[ Line: 222 ]]
            --[[ Upvalues: (copy 1): v_u_19 ]]
            return v_u_19;
        end;
        v18.player_disconnecting = function(_, p50) --[[ Name: player_disconnecting ]] --[[ Line: 226 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            v_u_21:remove(p50)
        end;
        return v18;
    end
};
