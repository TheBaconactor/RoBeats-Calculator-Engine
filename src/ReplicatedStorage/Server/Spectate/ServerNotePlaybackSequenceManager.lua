-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Server.ServerGameInstance)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.Shared.EventString)
local v_u_6 = require(game.ReplicatedStorage.Shared.NotePlaybackSequence)
local v7 = {}
local v_u_8 = false
v7.new = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_1, (ref 6): v_u_8, (copy 7): v_u_5 ]]
    local v10 = {}
    v10.start = function(p_u_11) --[[ Name: start ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_3 ]]
        p_u_9._evt:wait_on_event(v_u_3.EVT_Spectate_ClientSendNoteSequenceUpdate, function(p12, p13) --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            p_u_11:client_deserialize_and_send_notesequence_update_for_playerid(p12.UserId, p13)
        end)
    end;
    v10.client_deserialize_and_send_notesequence_update_for_playerid = function(p14, p15, p16) --[[ Name: client_deserialize_and_send_notesequence_update_for_playerid ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        p14:client_send_notesequence_update_for_playerid(p15, v_u_6:deserialize_from_table(p16, true))
    end;
    v10.client_send_notesequence_update_for_playerid = function(_, p17, p18) --[[ Name: client_send_notesequence_update_for_playerid ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2, (ref 3): v_u_4, (ref 4): v_u_1, (ref 5): v_u_8, (ref 6): v_u_3, (ref 7): v_u_5 ]]
        local v19 = p18:get_events()
        if v19:count() > 0 then
            local v20 = p_u_9._player_manager:get_player_gameinstance(p17)
            if v20 == nil then
                v_u_2:warnf("client_send_notesequence_update_for_playerid no game_instance")
                return;
            end;
            local v21 = v20._player_note_sequence_info:get((v20._util:get_player_slot(p17)))
            if v21 == nil then
                v_u_2:warnf("client_send_notesequence_update_for_playerid no player_note_sequence_info")
                return;
            end;
            local v22, _, v23 = v21:push_note_sequence(p18)
            if v_u_4.DebugRandomResync == true and v_u_1:rand_rangei(1, 100) == 5 then
                v_u_8 = true
                v22 = true
            end;
            local v24 = v20._util:get_player(p17)
            if v24 == nil then
                v_u_2:warnf("client_send_notesequence_update_for_playerid tar_player is nil")
                return;
            end;
            if v24._did_leave == true then
                v_u_2:warnf("client_send_notesequence_update_for_playerid for _did_leave player")
                return;
            end;
            if v22 and v_u_8 then
                v_u_2:warnf("NoteSequence Resync(%s)", (string.format("Player(%s) SongKey(%s) %s", tostring(v24._name), tostring(v20._selected_song_key), v23)))
                if v21:get_raise_resync_error() ~= true then
                    v21:set_raise_resync_error(true)
                end;
            end;
            v24._score = v21:get_player_score():get_score()
            v24._chain = v21:get_player_score():get_chain()
            v24._fever_percentage = v21:get_player_score():get_power_bar_pct()
            v24._power_bar_active = v21:get_player_score():is_powerbar_active()
            v24._naked_score = v21:get_player_naked_score():get_score()
            v24._naked_chain = v21:get_player_naked_score():get_chain()
            v24._naked_fever_percentage = v21:get_player_naked_score():get_power_bar_pct()
            v24._naked_power_bar_active = v21:get_player_naked_score():is_powerbar_active()
            local v25 = v19:get(v19:count())
            v24._power_bar_active = v25:get_is_fever()
            v24._fever_percentage = v25:get_fever_pct()
            if v22 then
                p_u_9._evt:fire_event_to_client(v_u_3.EVT_Spectate_ServerResyncNoteSequence, p_u_9._player_manager:id_to_player(p17), v20._game_id, v_u_5:es_table_convert({
                    [v_u_5.ES_NOTESEQ_TIME] = v25:get_time(),
                    [v_u_5.ES_NOTESEQ_NOTEINDEX] = v25:get_note_index(),
                    [v_u_5.ES_NOTESEQ_ISFEVER] = v25:get_is_fever(),
                    [v_u_5.ES_NOTESEQ_FEVER_PCT] = v25:get_fever_pct(),
                    [v_u_5.ES_NOTESEQ_SCOREEND] = p18:get_score_end(),
                    [v_u_5.ES_NOTESEQ_COMBOEND] = p18:get_combo_end(),
                    [v_u_5.ES_NOTESEQ_NAKED_SCORE] = v24._naked_score,
                    [v_u_5.ES_NOTESEQ_NAKED_COMBO] = v24._naked_chain,
                    [v_u_5.ES_NOTESEQ_NAKED_ISFEVER] = v24._naked_power_bar_active,
                    [v_u_5.ES_NOTESEQ_NAKED_FEVER_PCT] = v24._naked_fever_percentage
                }))
            end;
        end;
    end;
    return v10;
end;
return v7;
