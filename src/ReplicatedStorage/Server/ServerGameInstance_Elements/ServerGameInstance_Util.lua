-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["new"] = function(_, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_5 ]]
        local v27 = {
            ["SLOTS_MAX"] = 4,
            ["get_player_info_data"] = function(p8) --[[ Name: get_player_info_data ]] --[[ Line: 88 ]]
                local v_u_9 = {}
                p8:slots_foreach(function(p10, p11) --[[ Line: 90 ]]
                    --[[ Upvalues: (copy 1): v_u_9 ]]
                    v_u_9[p11] = p10:get_player_info(p11)
                end)
                return v_u_9;
            end,
            ["get_player"] = function(p12, p_u_13) --[[ Name: get_player ]] --[[ Line: 96 ]]
                local v_u_14 = nil
                local v_u_15 = -1
                p12:slots_foreach(function(p16, p17) --[[ Line: 99 ]]
                    --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_14, (ref 3): v_u_15 ]]
                    if p16._id == p_u_13 then
                        v_u_14 = p16
                        v_u_15 = p17
                    end;
                end)
                return v_u_14, v_u_15;
            end,
            ["get_player_slot"] = function(p18, p_u_19) --[[ Name: get_player_slot ]] --[[ Line: 108 ]]
                local v_u_20 = -1
                p18:slots_foreach(function(p21, p22) --[[ Line: 110 ]]
                    --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_20 ]]
                    if p21._id == p_u_19 then
                        v_u_20 = p22
                    end;
                end)
                return v_u_20;
            end,
            ["player_in_game"] = function(p23, p24) --[[ Name: player_in_game ]] --[[ Line: 118 ]]
                local v25 = p23:get_player(p24)
                local v26
                if v25 == nil then
                    v26 = false
                else
                    v26 = v25._did_leave ~= true
                end;
                return v26;
            end
        }
        v27.slots_foreach = function(p28, p29) --[[ Name: slots_foreach ]] --[[ Line: 29 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            for v30 = 1, p28.SLOTS_MAX do
                if p_u_7._slots:contains(v30) and p29(p_u_7._slots:get(v30), v30) == false then
                    return;
                end;
            end;
        end;
        v27.players_count = function(_) --[[ Name: players_count ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            local v_u_31 = 0
            p_u_7._util:slots_foreach(function(_, _) --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): v_u_31 ]]
                v_u_31 = v_u_31 + 1
            end)
            return v_u_31;
        end;
        v27.mark_player_as_left = function(p32, p_u_33) --[[ Name: mark_player_as_left ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_3, (copy 3): p_u_6 ]]
            if p_u_7._current_mode == v_u_3.Game or (p_u_7._current_mode == v_u_3.GameEnding or p_u_7._current_mode == v_u_3.GameEnded) then
                p32:slots_foreach(function(p34, _) --[[ Line: 53 ]]
                    --[[ Upvalues: (copy 1): p_u_33 ]]
                    if p34._id == p_u_33 then
                        p34._did_leave = true
                        p34._finished = true
                        return false;
                    end;
                end)
                p_u_7:remove_playerid_from_game_chat_channel(p_u_33)
                p32:push_update_player_info()
                p_u_6._player_status_manager:send_player_left_match_event(p_u_33, p_u_7)
                return;
            elseif p_u_7._current_mode == v_u_3.MatchMaking or (p_u_7._current_mode == v_u_3.VotePick or p_u_7._current_mode == v_u_3.SoundLoad) then
                p32:slots_foreach(function(p35, p36) --[[ Line: 69 ]]
                    --[[ Upvalues: (copy 1): p_u_33, (ref 2): p_u_7 ]]
                    if p35._id == p_u_33 then
                        p_u_7:remove_player_from_slot(p36)
                        return false;
                    end;
                end)
                p_u_7._match_making:push_update_matchmaking_info()
            else
                p32:slots_foreach(function(p37, p38) --[[ Line: 78 ]]
                    --[[ Upvalues: (copy 1): p_u_33, (ref 2): p_u_7 ]]
                    if p37._id == p_u_33 then
                        p_u_7:remove_player_from_slot(p38)
                        return false;
                    end;
                end)
            end;
        end;
        v27.push_update_player_info = function(_) --[[ Name: push_update_player_info ]] --[[ Line: 125 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            p_u_7:set_frame_push_update_game_info()
        end;
        local function _(p39, p40) --[[ Name: send_player_info_data_to_id ]] --[[ Line: 129 ]]
            --[[ Upvalues: (copy 1): p_u_6, (ref 2): v_u_2, (copy 3): p_u_7 ]]
            local v41 = p_u_6._player_manager:id_to_player(p39)
            if v41 ~= nil then
                p_u_6._evt:fire_event_to_client(v_u_2.EVT_Game_ServerUpdatePlayerInfo, v41, p_u_7._game_id, p40, p_u_7._playback_time_ms)
            end;
        end;
        v27.send_update_player_info = function(p42) --[[ Name: send_update_player_info ]] --[[ Line: 142 ]]
            --[[ Upvalues: (copy 1): p_u_6, (ref 2): v_u_2, (copy 3): p_u_7 ]]
            local v_u_43 = p42:get_player_info_data()
            p42:slots_foreach(function(p44, _) --[[ Line: 144 ]]
                --[[ Upvalues: (copy 1): v_u_43, (ref 2): p_u_6, (ref 3): v_u_2, (ref 4): p_u_7 ]]
                if p44:did_early_quit_or_leave() then
                    return;
                else
                    local v45 = v_u_43
                    local v46 = p_u_6._player_manager:id_to_player(p44._id)
                    if v46 ~= nil then
                        p_u_6._evt:fire_event_to_client(v_u_2.EVT_Game_ServerUpdatePlayerInfo, v46, p_u_7._game_id, v45, p_u_7._playback_time_ms)
                    end;
                end;
            end)
            for v47 = 1, p_u_7._spectators:count() do
                local v48 = p_u_6._player_manager:id_to_player((p_u_7._spectators:get(v47):get_player_id()))
                if v48 ~= nil then
                    p_u_6._evt:fire_event_to_client(v_u_2.EVT_Game_ServerUpdatePlayerInfo, v48, p_u_7._game_id, v_u_43, p_u_7._playback_time_ms)
                end;
            end;
        end;
        v27.update_player_gear_info = function(_) --[[ Name: update_player_gear_info ]] --[[ Line: 156 ]]
            --[[ Upvalues: (copy 1): p_u_7, (copy 2): p_u_6, (ref 3): v_u_1 ]]
            p_u_7._util:slots_foreach(function(p49, _) --[[ Line: 157 ]]
                --[[ Upvalues: (ref 1): p_u_6, (ref 2): v_u_1 ]]
                local v50 = p_u_6._player_blob_manager:get_cached_blob(p49._id)
                if v50 ~= nil then
                    local v51 = v_u_1:get_gear_info_data_for_playerblob(v50, p_u_6._api:get_day_id(), p_u_6._api:get_week_id())
                    p49._gear_info_data = v51
                    p49._gear_stats = v51.GearStats
                    p49._display_pet_tab = v51.DisplayPets
                end;
            end)
        end;
        v27.get_player_gear_info = function(_) --[[ Name: get_player_gear_info ]] --[[ Line: 168 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            local v_u_52 = {}
            p_u_7._util:slots_foreach(function(p53, p54) --[[ Line: 170 ]]
                --[[ Upvalues: (copy 1): v_u_52 ]]
                v_u_52[p54] = p53._gear_info_data
            end)
            return v_u_52;
        end;
        v27.is_player_spectating_gameinstance = function(_, p55) --[[ Name: is_player_spectating_gameinstance ]] --[[ Line: 176 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            for v56 = 1, p_u_7._spectators:count() do
                local v57 = p_u_7._spectators:get(v56)
                if v57:get_player_id() == p55 then
                    return v57, v56;
                end;
            end;
            return nil, -1;
        end;
        v27.get_player_note_skin_info = function(_) --[[ Name: get_player_note_skin_info ]] --[[ Line: 186 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_7, (copy 3): p_u_6 ]]
            local v_u_58 = v_u_4:new()
            p_u_7._util:slots_foreach(function(p59, p60) --[[ Line: 188 ]]
                --[[ Upvalues: (ref 1): p_u_6, (copy 2): v_u_58 ]]
                local v61 = p_u_6._player_blob_manager:get_cached_blob(p59._id)
                if v61 == nil then
                    v_u_58:add_default_to_slot(p60)
                else
                    v_u_58:add_playerblob_to_slot(v61, p60)
                end;
            end)
            return v_u_58;
        end;
        v27.get_player_dance_info = function(_) --[[ Name: get_player_dance_info ]] --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_7, (copy 3): p_u_6 ]]
            local v_u_62 = v_u_5:new()
            p_u_7._util:slots_foreach(function(p63, p64) --[[ Line: 201 ]]
                --[[ Upvalues: (ref 1): p_u_6, (copy 2): v_u_62 ]]
                local v65 = p_u_6._player_blob_manager:get_cached_blob(p63._id)
                if v65 then
                    v_u_62:add_playerblob_to_slot(v65, p64)
                end;
            end)
            return v_u_62;
        end;
        return v27;
    end
};
