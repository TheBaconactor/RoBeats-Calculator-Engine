-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.NotePlaybackSequence)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_2 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.EventString)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.PowerBarState)
return {
    ["new"] = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_6, (copy 6): v_u_5, (copy 7): v_u_7 ]]
        local v9 = {}
        local v_u_10 = v_u_1:new()
        local v_u_11 = v_u_1:new()
        v9.add_note_event = function(_, p12, p13, p14, p15, p16, p17, p18, p19, p20) --[[ Name: add_note_event ]] --[[ Line: 22 ]]
            --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_10 ]]
            v_u_10:get_events():push_back((v_u_11:add_note_event(p12, p13, p14, p15, p16, p17, p18, p19, p20)))
        end;
        local v_u_21 = 0
        v9.update = function(p22, p23) --[[ Name: update ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_3, (ref 3): v_u_2, (copy 4): p_u_8, (ref 5): v_u_4 ]]
            v_u_21 = v_u_21 + v_u_3:TimescaleToDeltaTime(p23)
            if v_u_21 > v_u_2.SPECTATE_REPLICATION_EVERY_SEC then
                v_u_21 = 0
                local v24 = p22:process_pending_playback_sequence_and_serialize_to_table()
                if p_u_8:is_networked() then
                    p_u_8._evt:fire_event_to_server(v_u_4.EVT_Spectate_ClientSendNoteSequenceUpdate, v24)
                end;
            end;
        end;
        v9.process_pending_playback_sequence_and_serialize_to_table = function(_) --[[ Name: process_pending_playback_sequence_and_serialize_to_table ]] --[[ Line: 50 ]]
            --[[ Upvalues: (copy 1): p_u_8, (copy 2): v_u_11 ]]
            v_u_11:set_time_end((math.floor((p_u_8:es_gamelocal_get_audiomanager():get_song_time_position_ms()))))
            v_u_11:set_score_end(p_u_8:es_gamelocal_get_scoremanager():get_score())
            v_u_11:set_combo_end(p_u_8:es_gamelocal_get_scoremanager():get_chain())
            local v25 = v_u_11:serialize_to_table(true)
            v_u_11:clear_events()
            v_u_11:set_time_start(v_u_11:get_time_end())
            v_u_11:set_score_start(v_u_11:get_score_end())
            v_u_11:set_combo_start(v_u_11:get_combo_end())
            return v25;
        end;
        v9.resync_note_sequence = function(_, p26) --[[ Name: resync_note_sequence ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (copy 3): p_u_8, (ref 4): v_u_7, (copy 5): v_u_10, (ref 6): v_u_3 ]]
            v_u_6:is_int(p26[v_u_5.ES_NOTESEQ_TIME])
            v_u_6:is_int(p26[v_u_5.ES_NOTESEQ_NOTEINDEX])
            v_u_6:is_bool(p26[v_u_5.ES_NOTESEQ_ISFEVER])
            v_u_6:is_number(p26[v_u_5.ES_NOTESEQ_FEVER_PCT])
            v_u_6:is_int(p26[v_u_5.ES_NOTESEQ_SCOREEND])
            v_u_6:is_int(p26[v_u_5.ES_NOTESEQ_COMBOEND])
            local v27, v28 = p_u_8:es_gamelocal_get_scoremanager():get_score_objs()
            v27:get_score()
            v27:get_power_bar_pct()
            v27:es_playerscore_set_score(p26[v_u_5.ES_NOTESEQ_SCOREEND])
            v27:set_chain(p26[v_u_5.ES_NOTESEQ_COMBOEND])
            v27:es_playerscore_set_powerbar_state(v_u_7:active_bool_to_state(p26[v_u_5.ES_NOTESEQ_ISFEVER]), p26[v_u_5.ES_NOTESEQ_FEVER_PCT])
            v28:es_playerscore_set_score(p26[v_u_5.ES_NOTESEQ_NAKED_SCORE])
            v28:set_chain(p26[v_u_5.ES_NOTESEQ_NAKED_COMBO])
            v28:es_playerscore_set_powerbar_state(v_u_7:active_bool_to_state(p26[v_u_5.ES_NOTESEQ_NAKED_ISFEVER]), p26[v_u_5.ES_NOTESEQ_NAKED_FEVER_PCT])
            local v29 = v_u_10:get_events()
            local v30 = p26[v_u_5.ES_NOTESEQ_TIME]
            local v31 = p26[v_u_5.ES_NOTESEQ_NOTEINDEX]
            local v32 = false
            local v33 = 0
            for v34 = 1, v29:count() do
                local v35 = v29:get(v34)
                if v32 == true then
                    local v36 = v35:get_time() - v33
                    if v36 > 0 then
                        v27:update(v_u_3:DeltaTimeToTimescale(v36 / 1000), false, false)
                    end;
                    v27:set_track_hit_counts(false)
                    v27:register_hit_noteresult_hitmode(v35:get_note_result(), v35:get_note_hit_mode())
                    v27:set_track_hit_counts(true)
                    v35:set_is_fever(v27:is_powerbar_active())
                    v35:set_fever_pct(v27:get_power_bar_pct())
                elseif v35:get_time() == v30 and v31 == v35:get_note_index() then
                    v35:set_is_fever(p26[v_u_5.ES_NOTESEQ_ISFEVER])
                    v35:set_fever_pct(p26[v_u_5.ES_NOTESEQ_FEVER_PCT])
                    v32 = true
                end;
                v33 = v35:get_time()
            end;
        end;
        v9.reset = function(_) --[[ Name: reset ]] --[[ Line: 135 ]]
            --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_11 ]]
            v_u_10:clear_events()
            v_u_11:clear_events()
        end;
        return v9;
    end
};
