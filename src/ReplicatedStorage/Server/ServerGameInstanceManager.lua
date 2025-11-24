-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Server.ServerGameInstance)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_11 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_12 = require(game.ReplicatedStorage.Server.ServerQueuedPlayer)
local v_u_13 = require(game.ReplicatedStorage.Shared.MatchMakingSettings)
local v_u_14 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_16 = require(game.ReplicatedStorage.Shared.EventString)
local v_u_17 = require(game.ReplicatedStorage.Server.Spectate.ServerNotePlaybackSequenceManager)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_19 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_20 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_21 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_22 = require(game.ReplicatedStorage.Avatar.PlayerBlobLoadout)
require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_23 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_24 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_25 = require(game.ReplicatedStorage.Server.Spectate.ServerSpectateManager)
local v_u_26 = require(game.ReplicatedStorage.Server.ServerRewardCooldownManager)
return {
    ["new"] = function(_, p_u_27) --[[ Name: new ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_17, (copy 3): v_u_25, (copy 4): v_u_26, (copy 5): v_u_24, (copy 6): v_u_23, (copy 7): v_u_14, (copy 8): v_u_22, (copy 9): v_u_13, (copy 10): v_u_8, (copy 11): v_u_4, (copy 12): v_u_7, (copy 13): v_u_3, (copy 14): v_u_1, (copy 15): v_u_5, (copy 16): v_u_10, (copy 17): v_u_6, (copy 18): v_u_11, (copy 19): v_u_19, (copy 20): v_u_20, (copy 21): v_u_9, (copy 22): v_u_21, (copy 23): v_u_15, (copy 24): v_u_18, (copy 25): v_u_12, (copy 26): v_u_16 ]]
        local v_u_28 = {}
        local v_u_29 = v_u_2:new()
        v_u_28.get_server_queued_player_for_id = function(_, p30) --[[ Name: get_server_queued_player_for_id ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): v_u_29 ]]
            return v_u_29:get(p30);
        end;
        v_u_28.get_server_queued_players_count = function(_) --[[ Name: get_server_queued_players_count ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): v_u_29 ]]
            return v_u_29:count();
        end;
        local v_u_31 = v_u_17:new(p_u_27)
        v_u_28.get_note_playback_sequence_manager = function(_) --[[ Name: get_note_playback_sequence_manager ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): v_u_31 ]]
            return v_u_31;
        end;
        local v_u_32 = v_u_25:new(p_u_27)
        local v_u_33 = v_u_26:new(p_u_27)
        v_u_28.get_reward_cooldown_manager = function(_) --[[ Name: get_reward_cooldown_manager ]] --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): v_u_33 ]]
            return v_u_33;
        end;
        local v_u_34 = v_u_24:new()
        local function _(p35) --[[ Name: is_player_in_match ]] --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): p_u_27 ]]
            return p_u_27._player_manager:get_player_gameinstance(p35) ~= nil;
        end;
        local function _(p36) --[[ Name: is_player_in_solo_match ]] --[[ Line: 56 ]]
            --[[ Upvalues: (copy 1): p_u_27 ]]
            local v37 = p_u_27._player_manager:get_player_gameinstance(p36)
            return v37 == nil and true or v37._slots:count() == 1;
        end;
        local function f_update_matchmaking_queue_info(p38) --[[ Name: update_matchmaking_queue_info ]] --[[ Line: 62 ]]
            --[[ Upvalues: (copy 1): v_u_29, (copy 2): p_u_27, (ref 3): v_u_23, (ref 4): v_u_14, (ref 5): v_u_22, (ref 6): v_u_13, (ref 7): v_u_8 ]]
            local v39 = 0
            for v40, _ in v_u_29:key_itr() do
                local v41 = p_u_27._player_manager:get_player_gameinstance(v40)
                if v41 == nil and true or v41._slots:count() == 1 then
                    v39 = v39 + 1
                end;
            end;
            local function f_get_playerblob_songkey_gearpower(p42, p43, p44) --[[ Name: get_playerblob_songkey_gearpower ]] --[[ Line: 70 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_23, (ref 3): v_u_14, (ref 4): v_u_22 ]]
                local v45 = p_u_27._api:get_day_id()
                local v46 = p_u_27._api:get_week_id()
                local v47 = v_u_23:songkey_get_color_list(p43)
                if p44 ~= true then
                    return v_u_14:statsdict_get_gear_power(v_u_14:get_playerblob_statsdict(p42, v45, v46), true, v47);
                end;
                local _, v48 = v_u_22:loadoutid_to_statsdict_get_top_loadoutid(v_u_22:playerblob_loadoutid_to_statsdict(p42, v45, v46), v47)
                return v48;
            end;
            for v49, _ in v_u_29:key_itr() do
                local v50 = p_u_27._player_manager:get_player_gameinstance(v49)
                local v51
                if v50 then
                    v51 = not p38 and true or v50 == p38
                else
                    v51 = false
                end;
                if v51 then
                    local v_u_52 = {}
                    v50._util:slots_foreach(function(p53, p54) --[[ Line: 105 ]]
                        --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_29, (copy 3): f_get_playerblob_songkey_gearpower, (ref 4): v_u_13, (copy 5): v_u_52 ]]
                        local v55 = p_u_27._player_blob_manager:get_cached_blob(p53._id)
                        local v56 = v_u_29:get(p53._id)
                        if v55 ~= nil and v56 ~= nil then
                            v_u_52[p54] = {
                                ["WaitTime"] = v56:get_wait_time(),
                                ["GearPower"] = f_get_playerblob_songkey_gearpower(v55, v56:get_requested_song_key(), v_u_13:get_auto_equip_best_loadout(v56:get_matchmaking_settings())),
                                ["MatchMode"] = v56:get_match_mode()
                            }
                        end;
                    end)
                    p_u_27._evt:fire_event_to_client(v_u_8.EVT_GameLoad_MatchmakingV3_ServerPushMatchmakingQueueInfo, p_u_27._player_manager:id_to_player(v49), {
                        ["EnqueuedPlayerCount"] = v_u_29:count(),
                        ["PlayerCount"] = v39,
                        ["GameId"] = v50._game_id
                    }, v_u_52)
                end;
            end;
        end;
        local function _(p57) --[[ Name: player_force_leave_current_match ]] --[[ Line: 135 ]]
            --[[ Upvalues: (copy 1): p_u_27, (copy 2): v_u_28, (copy 3): f_update_matchmaking_queue_info ]]
            local v58 = p_u_27._player_manager:get_player_gameinstance(p57)
            if v58 == nil then
                return false;
            end;
            v58._util:mark_player_as_left(p57)
            v_u_28:remove_enqueued_player(p57)
            f_update_matchmaking_queue_info()
            return true;
        end;
        v_u_28.make_new_gameinstance = function(_) --[[ Name: make_new_gameinstance ]] --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_27 ]]
            local v59 = v_u_4:new(p_u_27._game_instance_allocid, p_u_27)
            p_u_27._game_instances:push_back(v59)
            p_u_27._game_instance_allocid = p_u_27._game_instance_allocid + 1
            return v59;
        end;
        v_u_28.remove_enqueued_player = function(_, p60) --[[ Name: remove_enqueued_player ]] --[[ Line: 153 ]]
            --[[ Upvalues: (copy 1): v_u_29 ]]
            if v_u_29:contains(p60) then
                v_u_29:remove(p60)
            end;
        end;
        v_u_28.remove_gameinstance_from_queue = function(p_u_61, p62) --[[ Name: remove_gameinstance_from_queue ]] --[[ Line: 159 ]]
            --[[ Upvalues: (copy 1): f_update_matchmaking_queue_info ]]
            p62._util:slots_foreach(function(p63, _) --[[ Line: 160 ]]
                --[[ Upvalues: (copy 1): p_u_61 ]]
                p_u_61:remove_enqueued_player(p63._id)
            end)
            f_update_matchmaking_queue_info()
        end;
        local function _(p64) --[[ Name: gameinstance_all_players_should_start_matching ]] --[[ Line: 166 ]]
            --[[ Upvalues: (copy 1): v_u_29 ]]
            local v_u_65 = true
            p64._util:slots_foreach(function(p66, _) --[[ Line: 168 ]]
                --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_65 ]]
                local v67 = v_u_29:get(p66._id)
                if v67 ~= nil and v67:should_start_matching() == false then
                    v_u_65 = false
                    return false;
                end;
            end)
            return v_u_65;
        end;
        local function _(p68) --[[ Name: gameinstance_has_any_queued_players ]] --[[ Line: 178 ]]
            --[[ Upvalues: (copy 1): v_u_29 ]]
            local v_u_69 = false
            p68._util:slots_foreach(function(p70, _) --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_69 ]]
                if v_u_29:get(p70._id) ~= nil then
                    v_u_69 = true
                    return false;
                end;
            end)
            return v_u_69;
        end;
        local function _(p71, p_u_72) --[[ Name: gameinstance_contains_player_of_songkey ]] --[[ Line: 190 ]]
            local v_u_73 = false
            p71._util:slots_foreach(function(p74, _) --[[ Line: 192 ]]
                --[[ Upvalues: (copy 1): p_u_72, (ref 2): v_u_73 ]]
                if p74._requested_song_key == p_u_72 then
                    v_u_73 = true
                    return false;
                end;
            end)
            return v_u_73;
        end;
        local function _(p75) --[[ Name: gameinstance_song_difficulty_average ]] --[[ Line: 201 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_3 ]]
            local v_u_76 = 0
            local v_u_77 = 0
            p75._util:slots_foreach(function(p78, _) --[[ Line: 204 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_77, (ref 3): v_u_76, (ref 4): v_u_3 ]]
                local v79 = v_u_7:singleton():get_difficulty_for_key(p78._requested_song_key)
                v_u_77 = v_u_77 + 1
                v_u_76 = v_u_3:running_avg(v_u_76, v79, v_u_77)
            end)
            return v_u_76;
        end;
        local function _(p80, p_u_81) --[[ Name: gameinstance_all_players_matchmaking_time_greater_than ]] --[[ Line: 212 ]]
            --[[ Upvalues: (copy 1): v_u_29 ]]
            local v_u_82 = true
            p80._util:slots_foreach(function(p83, _) --[[ Line: 214 ]]
                --[[ Upvalues: (ref 1): v_u_29, (copy 2): p_u_81, (ref 3): v_u_82 ]]
                local v84 = v_u_29:get(p83._id)
                if v84 ~= nil and v84:get_matchmaking_time() < p_u_81 then
                    v_u_82 = false
                    return false;
                end;
            end)
            return v_u_82;
        end;
        local v_u_85 = v_u_1:new()
        local function f_attempt_matchmake_enqueued_player_gameinstance(p86, p87) --[[ Name: attempt_matchmake_enqueued_player_gameinstance ]] --[[ Line: 225 ]]
            --[[ Upvalues: (copy 1): v_u_85, (copy 2): p_u_27, (copy 3): v_u_29, (ref 4): v_u_7, (ref 5): v_u_3, (ref 6): v_u_5 ]]
            v_u_85:clear()
            for v88 = 1, p_u_27._game_instances:count() do
                local v89 = p_u_27._game_instances:get(v88)
                if v89._match_making:is_joinable() == true and v89._util:get_player(p86) == nil then
                    local v_u_90 = true
                    v89._util:slots_foreach(function(p91, _) --[[ Line: 168 ]]
                        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_90 ]]
                        local v92 = v_u_29:get(p91._id)
                        if v92 ~= nil and v92:should_start_matching() == false then
                            v_u_90 = false
                            return false;
                        end;
                    end)
                    if v_u_90 == true then
                        local v_u_93 = false
                        v89._util:slots_foreach(function(p94, _) --[[ Line: 180 ]]
                            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_93 ]]
                            if v_u_29:get(p94._id) ~= nil then
                                v_u_93 = true
                                return false;
                            end;
                        end)
                        if v_u_93 then
                            v_u_85:push_back(v89)
                        end;
                    end;
                end;
            end;
            local v95 = nil
            for v96 = 1, v_u_85:count() do
                local v97 = v_u_85:get(v96)
                local v_u_98 = p87:get_requested_song_key()
                local v_u_99 = false
                v97._util:slots_foreach(function(p100, _) --[[ Line: 192 ]]
                    --[[ Upvalues: (copy 1): v_u_98, (ref 2): v_u_99 ]]
                    if p100._requested_song_key == v_u_98 then
                        v_u_99 = true
                        return false;
                    end;
                end)
                local v_u_101
                if v_u_99 then
                    v_u_101 = 0
                else
                    local v_u_102 = 0
                    local v_u_103 = 0
                    v97._util:slots_foreach(function(p104, _) --[[ Line: 204 ]]
                        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_103, (ref 3): v_u_102, (ref 4): v_u_3 ]]
                        local v105 = v_u_7:singleton():get_difficulty_for_key(p104._requested_song_key)
                        v_u_103 = v_u_103 + 1
                        v_u_102 = v_u_3:running_avg(v_u_102, v105, v_u_103)
                    end)
                    v_u_101 = v_u_3:clamp(v_u_5:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(30, 30000), (math.abs(v_u_102 - p87:get_song_difficulty()))), 0, 100000)
                end;
                if v_u_101 <= p87:get_matchmaking_time() then
                    local v_u_106 = true
                    v97._util:slots_foreach(function(p107, _) --[[ Line: 214 ]]
                        --[[ Upvalues: (ref 1): v_u_29, (copy 2): v_u_101, (ref 3): v_u_106 ]]
                        local v108 = v_u_29:get(p107._id)
                        if v108 ~= nil and v108:get_matchmaking_time() < v_u_101 then
                            v_u_106 = false
                            return false;
                        end;
                    end)
                    if v_u_106 then
                        v95 = v97
                        break;
                    end;
                end;
            end;
            v_u_85:clear()
            return v95;
        end;
        local v_u_109 = v_u_2:new()
        v_u_28.get_cheer_cooldown_ms_for_player_id = function(_, p110) --[[ Name: get_cheer_cooldown_ms_for_player_id ]] --[[ Line: 277 ]]
            --[[ Upvalues: (copy 1): v_u_109 ]]
            if v_u_109:contains(p110) ~= true then
                v_u_109:add(p110, 0)
            end;
            return v_u_109:get(p110);
        end;
        v_u_28.set_cheer_cooldown_ms_for_player_id = function(_, p111, p112) --[[ Name: set_cheer_cooldown_ms_for_player_id ]] --[[ Line: 283 ]]
            --[[ Upvalues: (copy 1): v_u_109 ]]
            v_u_109:add(p111, p112)
        end;
        v_u_28.get_player_id_spectate_gameinstance = function(_, p113) --[[ Name: get_player_id_spectate_gameinstance ]] --[[ Line: 287 ]]
            --[[ Upvalues: (copy 1): v_u_32 ]]
            return v_u_32:get_player_id_spectate_gameinstance(p113);
        end;
        v_u_28.remove_spectating_player = function(p114, p115) --[[ Name: remove_spectating_player ]] --[[ Line: 292 ]]
            --[[ Upvalues: (copy 1): v_u_109 ]]
            local v116, _, _ = p114:get_player_id_spectate_gameinstance(p115)
            if v116 ~= nil then
                v116:spectator_leave(p115)
            end;
            v_u_109:remove(p115)
        end;
        v_u_28.player_disconnecting = function(_, p117) --[[ Name: player_disconnecting ]] --[[ Line: 300 ]]
            --[[ Upvalues: (copy 1): v_u_33 ]]
            v_u_33:player_disconnecting(p117)
        end;
        local v_u_118 = v_u_2:new()
        v_u_28.update = function(_, p119) --[[ Name: update ]] --[[ Line: 305 ]]
            --[[ Upvalues: (copy 1): v_u_109, (ref 2): v_u_5, (ref 3): v_u_10, (copy 4): v_u_29, (copy 5): p_u_27, (copy 6): f_attempt_matchmake_enqueued_player_gameinstance, (ref 7): v_u_6, (ref 8): v_u_11, (ref 9): v_u_19, (ref 10): v_u_20, (copy 11): f_update_matchmaking_queue_info, (copy 12): v_u_118, (ref 13): v_u_9, (ref 14): v_u_3, (copy 15): v_u_32, (copy 16): v_u_33, (copy 17): v_u_34 ]]
            for v120, v121 in v_u_109:key_itr() do
                if typeof(v121) == "number" then
                    v_u_109:add(v120, (v_u_5:IncrementClamp(v121, -v_u_5:TimescaleToDeltaTime(p119) * 1000, 0, v_u_10.SPECTATE_CHEER_COOLDOWN_MS)))
                end;
            end;
            for v122, v123 in v_u_29:key_itr() do
                v123:update(p119)
                local v124 = p_u_27._player_manager:get_player_gameinstance(v122)
                if v124 ~= nil and (v124._match_making:is_joinable() and v123:should_start_matching()) then
                    local v125 = p_u_27._player_manager:get_player_gameinstance(v122)
                    if v125 == nil and true or v125._slots:count() == 1 then
                        local v126 = v124._util:get_player(v122)
                        local v127 = v126 == nil and -1 or v126._event_info
                        local v128 = f_attempt_matchmake_enqueued_player_gameinstance(v122, v123)
                        if v128 ~= nil then
                            v124:remove_player_from_slot(v124._util:get_player_slot(v122))
                            if v128._match_making:request_slot_for_id(v122, v123:get_requested_song_key()) == -1 then
                                v_u_6:warnf("EVT_GameLoad_ClientRequestGameSlot request_slot_for_id fail")
                                p_u_27._api:api_report_evt(v_u_11.ReportEvt_ClientRequestGameSlot_RequestSlotForIdFail)
                                v124._match_making:request_slot_for_id(v122, v123:get_requested_song_key())
                            else
                                if v_u_19:test_enum_member(v127, v_u_20.EventMission) == true then
                                    v128._match_making:set_player_event_info(v122, v127)
                                end;
                                v128._match_making:push_update_matchmaking_info()
                                f_update_matchmaking_queue_info()
                            end;
                        end;
                    end;
                end;
            end;
            v_u_118:clear()
            for v129 = p_u_27._game_instances:count(), 1, -1 do
                local v_u_130 = p_u_27._game_instances:get(v129)
                v_u_130._util:slots_foreach(function(p131, _) --[[ Line: 364 ]]
                    --[[ Upvalues: (ref 1): v_u_118, (copy 2): v_u_130 ]]
                    if p131 ~= nil and p131._did_leave ~= true then
                        v_u_118:add(p131._id, v_u_130)
                    end;
                end)
                if v_u_130._current_mode == v_u_9.DoRemove then
                    v_u_130:on_remove()
                    p_u_27._game_instances:remove_at(v129)
                    if v_u_3:is_dev_build() then
                        v_u_6:puts("---\tRemoving ServerGameInstance[%d] _game_instances(%d)", v_u_130._game_id, p_u_27._game_instances:count())
                    end;
                end;
            end;
            for _, v132 in p_u_27._game_instances:key_itr() do
                v132:flag_removed_players_and_spectators_as_did_leave(v_u_118)
            end;
            v_u_32:update(p119)
            v_u_33:update(p119)
            v_u_34:update(p119)
        end;
        v_u_28.start = function(p_u_133) --[[ Name: start ]] --[[ Line: 387 ]]
            --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_21, (ref 3): v_u_15, (ref 4): v_u_18, (copy 5): v_u_28, (copy 6): f_update_matchmaking_queue_info, (ref 7): v_u_3, (ref 8): v_u_9, (ref 9): v_u_8, (ref 10): v_u_7, (ref 11): v_u_6, (copy 12): v_u_29, (ref 13): v_u_12, (ref 14): v_u_19, (ref 15): v_u_20, (copy 16): v_u_34, (ref 17): v_u_10, (ref 18): v_u_13, (copy 19): v_u_31, (ref 20): v_u_16, (copy 21): v_u_32 ]]
            local function f_check_if_playerid_can_start_song(p134, p135, p136) --[[ Name: check_if_playerid_can_start_song ]] --[[ Line: 389 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_21, (ref 3): v_u_15, (ref 4): v_u_18 ]]
                if p_u_27._game_instance_manager:get_reward_cooldown_manager():get_userid_last_played_song(p134) == p135 then
                    return true;
                end;
                if p_u_27._special_event_manager:test_event_if_playerid_can_start_songkey(p134, p135, p136) then
                    return true;
                end;
                local v137, v138 = v_u_21:is_event_active(p_u_27._api:get_day_event_list())
                if v137 and v_u_21:get_playable_song_set(v138):contains(p135) then
                    return true;
                end;
                local v139 = p_u_27._player_blob_manager:get_cached_blob(p134)
                return v_u_15:is_tester_status(v139) == true and true or (p_u_27._danceclub_manager:is_songkey_danceclub_active_song(p135) == true and true or (v_u_18:playerblob_has_access_to_song(v139, p135, p_u_27._api:get_day_id(), p_u_27._collection_manager:get_collection_info_for_player_id_playerblob(p134, v139)) and true or false));
            end;
            local function f_sanity_check_still_in_match(p_u_140) --[[ Name: sanity_check_still_in_match ]] --[[ Line: 430 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_28, (ref 3): f_update_matchmaking_queue_info, (ref 4): v_u_3, (ref 5): v_u_9 ]]
                if p_u_27._player_manager:get_player_gameinstance(p_u_140) ~= nil == true then
                    local v141 = p_u_27._player_manager:get_player_gameinstance(p_u_140)
                    if v141 ~= nil then
                        v141._util:mark_player_as_left(p_u_140)
                        v_u_28:remove_enqueued_player(p_u_140)
                        f_update_matchmaking_queue_info()
                    end;
                    if p_u_27._player_manager:get_player_gameinstance(p_u_140) ~= nil == true then
                        local v_u_142 = ""
                        pcall(function() --[[ Line: 435 ]]
                            --[[ Upvalues: (ref 1): p_u_27, (copy 2): p_u_140, (ref 3): v_u_142, (ref 4): v_u_3, (ref 5): v_u_9 ]]
                            local v143 = p_u_27._player_manager:get_player_gameinstance(p_u_140)
                            v_u_142 = string.format("ID(%d) CurrentMode(%s) Players(%d) AllPlayersFinished(%s) PlaybackMS(%.2f) LengthMS(%.2f) LoadTimeout(%d) GameEndingTimeout(%d)", v143._game_id, v_u_3:enum_val_to_name(v143._current_mode, v_u_9), v143._util:players_count(), tostring(v143._game_ending:all_players_finished()), v143._playback_time_ms, v143._sound_length_ms, v143._sound_load:get_server_load_timeout(), v143._game_ending:get_server_gameending_timeout())
                        end)
                        return true, string.format("ERROR: Already in match(%s)", v_u_142);
                    end;
                end;
                return false, "";
            end;
            p_u_27._evt:wait_on_event(v_u_8.EVT_GameLoad_MatchmakingV3_ClientEnqueue, function(p_u_144, p145, p146, p147) --[[ Line: 454 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_6, (ref 3): p_u_27, (ref 4): v_u_8, (ref 5): v_u_15, (copy 6): f_check_if_playerid_can_start_song, (copy 7): f_sanity_check_still_in_match, (ref 8): v_u_29, (copy 9): p_u_133, (ref 10): v_u_12, (ref 11): v_u_19, (ref 12): v_u_20, (ref 13): f_update_matchmaking_queue_info ]]
                if v_u_7:singleton():contains_key(p145) then
                    if p146 == nil then
                        v_u_6:warnf("EVT_GameLoad_MatchmakingV3_ClientEnqueue initial_matchmaking_settings nil")
                    else
                        local function f_error_response(p148) --[[ Name: error_response ]] --[[ Line: 458 ]]
                            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (copy 3): p_u_144 ]]
                            p_u_27._evt:fire_event_to_client(v_u_8.EVT_GameLoad_MatchmakingV3_ClientEnqueueErrorFromServer, p_u_144, p148)
                        end;
                        local v149 = p_u_27._player_blob_manager:get_cached_blob(p_u_144.UserId)
                        if v149 == nil then
                            return f_error_response("PlayerBlob not found");
                        end;
                        v_u_15:err_if_banned(v149)
                        if f_check_if_playerid_can_start_song(p_u_144.UserId, p145, p147) ~= true then
                            return f_error_response("Player cannot start song");
                        end;
                        p_u_27._player_model_cache:add_player_to_cache(p_u_144)
                        local l_UserId_0 = p_u_144.UserId
                        local v150, v151 = f_sanity_check_still_in_match(l_UserId_0)
                        if v150 == true then
                            return f_error_response(v151);
                        end;
                        if v_u_29:contains(l_UserId_0) then
                            p_u_133:remove_enqueued_player(l_UserId_0)
                        end;
                        v_u_29:add(l_UserId_0, v_u_12:new(l_UserId_0, p145, p146))
                        local v152 = p_u_133:make_new_gameinstance()
                        if v152._match_making:request_slot_for_id(l_UserId_0, p145) == -1 then
                            return f_error_response("ERROR: Cannot find slot.");
                        end;
                        if v_u_19:test_enum_member(p147, v_u_20.EventMission) == true then
                            v152._match_making:set_player_event_info(l_UserId_0, p147)
                        end;
                        p_u_27._player_status_manager:send_player_join_matchmaking_event(l_UserId_0, p145)
                        v152._match_making:push_update_matchmaking_info()
                        f_update_matchmaking_queue_info()
                    end;
                else
                    v_u_6:warnf("EVT_GameLoad_MatchmakingV3_ClientEnqueue key not found(%s)", p145)
                    return;
                end;
            end)
            p_u_27._evt:wait_on_event(v_u_8.EVT_GameLoad_MatchmakingV3_ClientJoinTargetPlayer, function(p_u_153, p154, p155, p156) --[[ Line: 494 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (ref 3): v_u_15, (ref 4): v_u_34, (copy 5): f_sanity_check_still_in_match, (ref 6): v_u_19, (ref 7): v_u_20, (ref 8): v_u_29, (ref 9): v_u_12, (ref 10): f_update_matchmaking_queue_info, (ref 11): v_u_10 ]]
                local l_UserId_1 = p_u_153.UserId
                local v157 = p_u_27._player_blob_manager:get_cached_blob(p_u_153.UserId)
                local function f_error_response(p158) --[[ Name: error_response ]] --[[ Line: 498 ]]
                    --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (copy 3): p_u_153 ]]
                    p_u_27._evt:fire_event_to_client(v_u_8.EVT_GameLoad_MatchmakingV3_ServerJoinTargetPlayerError, p_u_153, p158)
                end;
                if v157 == nil then
                    return f_error_response("PlayerBlob not found");
                end;
                v_u_15:err_if_banned(v157)
                local v159 = p_u_27._player_manager:get_player_gameinstance(p154)
                if v159 == nil then
                    return f_error_response("Match not found.");
                end;
                if v159._match_making:is_joinable() == false then
                    return f_error_response("Match is not joinable.");
                end;
                local v160 = v159._util:get_player(p154)
                if v160 == nil then
                    return f_error_response("Player not in match anymore.");
                end;
                local v161 = string.format("%d_join_%d", p_u_153.UserId, p154)
                if v_u_34:is_on_cooldown(v161) then
                    return f_error_response(string.format("Cannot join this player\'s match for another %.2f seconds.", (v_u_34:get_cooldown_time(v161))));
                end;
                local v162, v163 = f_sanity_check_still_in_match(l_UserId_1)
                if v162 == true then
                    return f_error_response(v163);
                end;
                local l__requested_song_key_0 = v160._requested_song_key
                if v159._match_making:request_slot_for_id(p_u_153.UserId, l__requested_song_key_0) == -1 then
                    return f_error_response("Failed to join match.");
                end;
                if v_u_19:test_enum_member(p156, v_u_20.EventMission) == true then
                    v159._match_making:set_player_event_info(l_UserId_1, p156)
                end;
                v_u_29:add(p_u_153.UserId, v_u_12:new(p_u_153.UserId, l__requested_song_key_0, p155))
                p_u_27._player_status_manager:send_player_join_matchmaking_event(p_u_153.UserId, l__requested_song_key_0)
                v159._match_making:push_update_matchmaking_info()
                f_update_matchmaking_queue_info()
                v_u_34:add_cooldown_to_id(v161, v_u_10.MATCHMAKING_JOIN_TARGET_COOLDOWN_TIME_SEC)
            end)
            local function _(p_u_164, p_u_165) --[[ Name: update_player_id_matchmaking_settings ]] --[[ Line: 546 ]]
                --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_13, (ref 3): v_u_29, (ref 4): f_update_matchmaking_queue_info, (ref 5): p_u_27, (ref 6): v_u_6 ]]
                local v166, v167 = pcall(function() --[[ Line: 547 ]]
                    --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_165, (ref 3): v_u_13, (ref 4): v_u_29, (copy 5): p_u_164, (ref 6): f_update_matchmaking_queue_info, (ref 7): p_u_27 ]]
                    v_u_19:is_table_same_format(p_u_165, v_u_13:new())
                    if v_u_29:contains(p_u_164) then
                        v_u_29:get(p_u_164):update_matchmaking_settings(p_u_165)
                        f_update_matchmaking_queue_info(p_u_27._player_manager:get_player_gameinstance(p_u_164))
                    end;
                end)
                if v166 ~= true then
                    v_u_6:warnf("update_player_id_matchmaking_settings failed(%s)", v167)
                end;
            end;
            p_u_27._evt:wait_on_event(v_u_8.EVT_GameLoad_MatchmakingV3_ClientUpdateSettings, function(p168, p_u_169) --[[ Line: 559 ]]
                --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_13, (ref 3): v_u_29, (ref 4): f_update_matchmaking_queue_info, (ref 5): p_u_27, (ref 6): v_u_6 ]]
                local l_UserId_2 = p168.UserId
                local v170, v171 = pcall(function() --[[ Line: 547 ]]
                    --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_169, (ref 3): v_u_13, (ref 4): v_u_29, (copy 5): l_UserId_2, (ref 6): f_update_matchmaking_queue_info, (ref 7): p_u_27 ]]
                    v_u_19:is_table_same_format(p_u_169, v_u_13:new())
                    if v_u_29:contains(l_UserId_2) then
                        v_u_29:get(l_UserId_2):update_matchmaking_settings(p_u_169)
                        f_update_matchmaking_queue_info(p_u_27._player_manager:get_player_gameinstance(l_UserId_2))
                    end;
                end)
                if v170 ~= true then
                    v_u_6:warnf("update_player_id_matchmaking_settings failed(%s)", v171)
                end;
            end)
            p_u_27._evt:wait_on_event(v_u_8.EVT_GameLoad_MatchmakingV3_ClientReady, function(p172, p_u_173) --[[ Line: 563 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_6, (ref 3): v_u_19, (ref 4): v_u_13, (ref 5): v_u_29, (ref 6): f_update_matchmaking_queue_info ]]
                local v174 = p_u_27._player_manager:get_player_gameinstance(p172.UserId)
                if v174 == nil then
                    v_u_6:warnf("[[ERROR]] ClientReadyToStart no containing game instance for player(%d)", p172.UserId)
                else
                    local l_UserId_3 = p172.UserId
                    local v175, v176 = pcall(function() --[[ Line: 547 ]]
                        --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_173, (ref 3): v_u_13, (ref 4): v_u_29, (copy 5): l_UserId_3, (ref 6): f_update_matchmaking_queue_info, (ref 7): p_u_27 ]]
                        v_u_19:is_table_same_format(p_u_173, v_u_13:new())
                        if v_u_29:contains(l_UserId_3) then
                            v_u_29:get(l_UserId_3):update_matchmaking_settings(p_u_173)
                            f_update_matchmaking_queue_info(p_u_27._player_manager:get_player_gameinstance(l_UserId_3))
                        end;
                    end)
                    if v175 ~= true then
                        v_u_6:warnf("update_player_id_matchmaking_settings failed(%s)", v176)
                    end;
                    v174._match_making:player_notify_ready_state(p172.UserId, true)
                end;
            end)
            p_u_27._evt:wait_on_event(v_u_8.EVT_GameLoad_MatchmakingV3_ClientLeaveMatch, function(p177) --[[ Line: 577 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_28, (ref 3): f_update_matchmaking_queue_info, (ref 4): v_u_8 ]]
                local l_UserId_4 = p177.UserId
                local v178 = p_u_27._player_manager:get_player_gameinstance(l_UserId_4)
                local v179
                if v178 == nil then
                    v179 = false
                else
                    v178._util:mark_player_as_left(l_UserId_4)
                    v_u_28:remove_enqueued_player(l_UserId_4)
                    f_update_matchmaking_queue_info()
                    v179 = true
                end;
                if v179 then
                    p_u_27._player_status_manager:send_player_lobby_load_event(p177.UserId)
                    p_u_27._evt:fire_event_to_client(v_u_8.EVT_GameLoad_MatchmakingV3_ServerAcknowledgeClientLeaveMatch, p177)
                end;
            end)
            p_u_27._evt:wait_on_event(v_u_8.EVT_GameLoad_ClientNotifyVotePickSelect, function(p180, p181) --[[ Line: 586 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_6 ]]
                local v182 = p_u_27._player_manager:get_player_gameinstance(p180.UserId)
                if v182 == nil then
                    v_u_6:warnf("[[ERROR]] ClientNotifyVotePickSelect no containing game instance for player(%d)", p180.UserId)
                else
                    v182._votepick:player_notify_votepick_select(p180.UserId, p181)
                end;
            end)
            p_u_27._evt:wait_on_event(v_u_8.EVT_GameLoad_ClientNotifyPreloadFinished, function(p183) --[[ Line: 607 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_6 ]]
                local v184 = p_u_27._player_manager:get_player_gameinstance(p183.UserId)
                if v184 == nil then
                    v_u_6:warnf("[[ERROR]] ClientNotifyPreloadFinished no containing game instance for player(%d)", p183.UserId)
                else
                    v184._sound_load:player_notify_loaded_state(p183.UserId, true)
                end;
            end)
            v_u_31:start()
            p_u_27._evt:wait_on_event(v_u_8.EVT_Game_ClientNotifyLocalFinished, function(p185, p186, p187, p188) --[[ Line: 630 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_6, (ref 3): v_u_16, (ref 4): v_u_31 ]]
                local function f_handle_local_finished(p189, p190, p191) --[[ Name: handle_local_finished ]] --[[ Line: 631 ]]
                    --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_6, (ref 3): v_u_16 ]]
                    local v192 = p_u_27._player_manager:get_player_gameinstance(p189.UserId)
                    if v192 == nil then
                        v_u_6:warnf("EVT_Game_ClientNotifyLocalFinished no containing game instance for player (%d)", p189.UserId)
                    else
                        local v193 = v_u_16:es_table_deconvert(p191)
                        v192._game_ending:notify_local_finished(p189.UserId, p190, {
                            ["Score"] = v193[v_u_16.ES_END_SCORE],
                            ["NakedScore"] = v193[v_u_16.ES_END_NAKEDSCORE],
                            ["Chain"] = v193[v_u_16.ES_END_CHAIN],
                            ["Accuracy"] = v193[v_u_16.ES_END_ACCURACY],
                            ["PerfectCount"] = v193[v_u_16.ES_END_PERFECTCOUNT],
                            ["GreatCount"] = v193[v_u_16.ES_END_GREATCOUNT],
                            ["OkayCount"] = v193[v_u_16.ES_END_OKAYCOUNT],
                            ["MissCount"] = v193[v_u_16.ES_END_MISSCOUNT],
                            ["MaxChain"] = v193[v_u_16.ES_END_MAXCHAIN],
                            ["FeverPercentage"] = v193[v_u_16.ES_END_FEVERPERCENTAGE],
                            ["AutoPlay"] = v193[v_u_16.ES_END_AUTOPLAY],
                            ["ComboMax"] = v193[v_u_16.ES_END_COMBOMAX]
                        })
                    end;
                end;
                v_u_31:client_deserialize_and_send_notesequence_update_for_playerid(p185.UserId, p188)
                f_handle_local_finished(p185, p186, p187)
            end)
            p_u_27._evt:wait_on_event(v_u_8.EVT_Game_ClientNotifyLeaveEndedGame, function(p194, _) --[[ Line: 662 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_6 ]]
                local v195 = p_u_27._player_manager:get_player_gameinstance(p194.UserId)
                if v195 == nil then
                    v_u_6:warnf("EVT_Game_ClientNotifyLeaveEndedGame no containing game instance for player (%d)", p194.UserId)
                else
                    v195._game_ended:notify_leave_ended_game(p194.UserId)
                end;
            end)
            v_u_32:start()
        end;
        return v_u_28;
    end
};
