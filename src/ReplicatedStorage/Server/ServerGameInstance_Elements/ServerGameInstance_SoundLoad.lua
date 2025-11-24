-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_5 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
local v_u_6 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_8 = require(game.ReplicatedStorage.Avatar.PlayerBlobLoadout)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_10 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_11 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["new"] = function(_, p_u_13, p_u_14) --[[ Name: new ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_11, (copy 3): v_u_12, (copy 4): v_u_8, (copy 5): v_u_9, (copy 6): v_u_3, (copy 7): v_u_2, (copy 8): v_u_10, (copy 9): v_u_1, (copy 10): v_u_4, (copy 11): v_u_5, (copy 12): v_u_7 ]]
        local v15 = {}
        local v_u_16 = {}
        local v_u_17 = v_u_6.PRELOAD_TIMEOUT_MS + 5000
        v15.start_load = function(_, p_u_18) --[[ Name: start_load ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): p_u_14, (copy 2): p_u_13, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_8, (ref 6): v_u_9, (ref 7): v_u_3, (ref 8): v_u_6, (ref 9): v_u_2, (copy 10): v_u_16 ]]
            p_u_14._util:slots_foreach(function(p_u_19, _) --[[ Line: 32 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_11, (ref 3): v_u_12, (ref 4): v_u_8, (ref 5): v_u_9, (copy 6): p_u_18, (ref 7): v_u_3, (ref 8): p_u_14 ]]
                local v20 = p_u_13._player_blob_manager:get_cached_blob(p_u_19._id)
                if v20 then
                    local v_u_21 = false
                    local v_u_22 = v_u_11:new()
                    v_u_22:load_from_json_str(v_u_12:get_player_settings_str(v20))
                    if p_u_19._should_auto_equip_best_loadout == true then
                        local v_u_23, v24 = v_u_8:loadoutid_to_statsdict_get_top_loadoutid(v_u_8:playerblob_loadoutid_to_statsdict(v20, p_u_13._api:get_day_id(), (p_u_13._api:get_week_id())), v_u_9:songkey_get_color_list(p_u_18))
                        if v24 > 0 and v_u_8:get_loadout_index_range(v20):contains(v_u_23) then
                            v_u_8:equip_loadout_index(v20, v_u_23)
                            v_u_3:ptry(function() --[[ Line: 46 ]]
                                --[[ Upvalues: (ref 1): p_u_13, (ref 2): p_u_14, (copy 3): p_u_19, (ref 4): v_u_8, (copy 5): v_u_22, (copy 6): v_u_23, (ref 7): v_u_3 ]]
                                local v25 = p_u_13._chat:get_chat_service()
                                local v26 = p_u_13._chat:gameid_get_channel(p_u_14._game_id)
                                local v27 = p_u_13._player_manager:id_to_player(p_u_19._id)
                                if v27 and (v25 and v26) then
                                    v25:send_system_message_to_player_for_channel(v27, v26, string.format("You switched to loadout \'%s\'!", v_u_8:player_settings_get_loadout_name(v_u_22, v_u_23)), function(p28) --[[ Line: 57 ]]
                                        --[[ Upvalues: (ref 1): v_u_3 ]]
                                        p28:set_icon(v_u_3:important_assetid())
                                    end)
                                end;
                            end)
                        end;
                    end;
                    local function _(p29, p30) --[[ Name: check_updated_setting ]] --[[ Line: 66 ]]
                        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_21 ]]
                        if v_u_22:get_key(p29) ~= p30 then
                            v_u_22:set_key(p29, p30)
                            v_u_21 = true
                        end;
                    end;
                    local l_AutoEquipBestLoadout_0 = v_u_11.Key.AutoEquipBestLoadout
                    local l__should_auto_equip_best_loadout_0 = p_u_19._should_auto_equip_best_loadout
                    if v_u_22:get_key(l_AutoEquipBestLoadout_0) ~= l__should_auto_equip_best_loadout_0 then
                        v_u_22:set_key(l_AutoEquipBestLoadout_0, l__should_auto_equip_best_loadout_0)
                        v_u_21 = true
                    end;
                    local l_MatchMode_0 = v_u_11.Key.MatchMode
                    local l__match_mode_0 = p_u_19._match_mode
                    if v_u_22:get_key(l_MatchMode_0) ~= l__match_mode_0 then
                        v_u_22:set_key(l_MatchMode_0, l__match_mode_0)
                        v_u_21 = true
                    end;
                    local l_SelectedGameStage_0 = v_u_11.Key.SelectedGameStage
                    local l__stage_id_0 = p_u_19._stage_id
                    if v_u_22:get_key(l_SelectedGameStage_0) ~= l__stage_id_0 then
                        v_u_22:set_key(l_SelectedGameStage_0, l__stage_id_0)
                        v_u_21 = true
                    end;
                    if v_u_21 then
                        v_u_12:set_player_settings_str(v20, v_u_22:to_json())
                    end;
                end;
            end)
            p_u_14:select_song(p_u_18)
            p_u_14._util:slots_foreach(function(p31, p32) --[[ Line: 86 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_13, (ref 3): v_u_2, (ref 4): p_u_14, (ref 5): v_u_16 ]]
                p31._timeout = v_u_6.PRELOAD_TIMEOUT_MS
                local v33 = p_u_13._player_manager:id_to_player(p31._id)
                if v33 ~= nil then
                    p_u_13._evt:fire_event_to_client(v_u_2.EVT_GameLoad_ServerNotifyClientDoPreload, v33, p_u_14._util:get_player_info_data(), p32, p_u_14._match_making:get_player_matchmaking_info(), p_u_14._util:get_player_gear_info(), p_u_14._selected_song_key, p_u_14._util:get_player_note_skin_info():to_table(), p_u_14._util:get_player_dance_info():to_table())
                    table.insert(v_u_16, #v_u_16 + 1, {
                        ["rbxid"] = v33.UserId,
                        ["connection_success"] = true
                    })
                end;
            end)
            p_u_14._match_making:push_update_matchmaking_info()
            p_u_13._player_status_manager:send_soundload_start_event(p_u_14)
        end;
        v15.player_notify_loaded_state = function(p34, p35, p36) --[[ Name: player_notify_loaded_state ]] --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_14, (ref 3): v_u_1 ]]
            v_u_10:is_bool(p36)
            if p_u_14._util:player_in_game(p35) == false then
                v_u_1:errf("ServerGameInstance player_notify_loaded_state gameid(%d) does not contain userid(%d)", p34._game_id, p35)
            else
                p_u_14._util:get_player(p35)._loaded = p36
                p_u_14._match_making:push_update_matchmaking_info()
            end;
        end;
        v15.all_players_loaded = function(_) --[[ Name: all_players_loaded ]] --[[ Line: 125 ]]
            --[[ Upvalues: (copy 1): p_u_14 ]]
            local v_u_37 = true
            p_u_14._util:slots_foreach(function(p38, _) --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): v_u_37 ]]
                if p38._loaded == false then
                    v_u_37 = false
                end;
            end)
            return v_u_37;
        end;
        v15.players_loaded_count = function(_) --[[ Name: players_loaded_count ]] --[[ Line: 135 ]]
            --[[ Upvalues: (copy 1): p_u_14 ]]
            local v_u_39 = 0
            p_u_14._util:slots_foreach(function(p40, _) --[[ Line: 137 ]]
                --[[ Upvalues: (ref 1): v_u_39 ]]
                if p40._loaded == true then
                    v_u_39 = v_u_39 + 1
                end;
            end)
            return v_u_39;
        end;
        v15.start_game = function(_) --[[ Name: start_game ]] --[[ Line: 145 ]]
            --[[ Upvalues: (copy 1): p_u_14, (copy 2): p_u_13, (ref 3): v_u_4, (ref 4): v_u_1, (ref 5): v_u_6, (ref 6): v_u_5, (ref 7): v_u_2 ]]
            local l__selected_song_key_0 = p_u_14._selected_song_key
            local _, v41 = p_u_13._audio_cache:get_audio_length(v_u_4:singleton():get_audio_assetid_for_key(l__selected_song_key_0))
            local v42 = v_u_4:singleton():songkey_get_approx_length_sec(l__selected_song_key_0)
            local v43 = v42 + 5
            v_u_1:puts("ServerGameInstance_SoundLoad:start_game() songkey(%d) AssetId_AudioLength(%.2f) approx_song_length(%.2f)", l__selected_song_key_0, v41, v42)
            p_u_14._sound_length_ms = v43 * 1000 + v_u_6.PRE_START_TIME_MS_MAX + v_u_6.POST_TIME_PLAYING_MS_MAX
            p_u_14._current_mode = v_u_5.Game
            p_u_14._util:slots_foreach(function(p44, _) --[[ Line: 162 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (ref 3): p_u_14, (copy 4): l__selected_song_key_0 ]]
                local v45 = p_u_13._player_manager:id_to_player(p44._id)
                if v45 ~= nil then
                    p_u_13._evt:fire_event_to_client(v_u_2.EVT_GameLoad_ServerNotifyClientDoStart, v45, p_u_14._game_id)
                    if p_u_13._danceclub_manager:is_songkey_danceclub_active_song(l__selected_song_key_0) == true then
                        p_u_13._danceclub_manager:player_started_danceclub_active_song(v45, l__selected_song_key_0)
                    end;
                end;
            end)
            p_u_13._player_status_manager:send_match_start_event(p_u_14)
        end;
        v15.get_server_load_timeout = function(_) --[[ Name: get_server_load_timeout ]] --[[ Line: 180 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        v15.update = function(p46, p_u_47) --[[ Name: update ]] --[[ Line: 182 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_7, (ref 3): v_u_17, (copy 4): p_u_13, (ref 5): v_u_4 ]]
            p_u_14._util:slots_foreach(function(p48, _) --[[ Line: 183 ]]
                --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_47 ]]
                if p48._loaded == false then
                    p48._timeout = p48._timeout - v_u_7:TimescaleToDeltaTime(p_u_47) * 1000
                    if p48._timeout <= 0 then
                        p48._loaded = true
                    end;
                end;
            end)
            local v49 = v_u_17
            v_u_17 = v_u_17 - v_u_7:TimescaleToDeltaTime(p_u_47) * 1000
            if v49 > 0 and v_u_17 <= 0 then
                p_u_14._util:slots_foreach(function(p50, _) --[[ Line: 195 ]]
                    p50._loaded = true
                end)
            end;
            p_u_13._audio_cache:get_audio_length(v_u_4:singleton():get_audio_assetid_for_key(p_u_14._selected_song_key))
            if p46:all_players_loaded() then
                p46:start_game()
            end;
        end;
        return v15;
    end
};
