-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Local.Note)
local v_u_5 = require(game.ReplicatedStorage.Local.HeldNote)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.Shared.NoteHitMode)
local v_u_11 = require(game.ReplicatedStorage.Shared.PowerBarState)
require(game.ReplicatedStorage.Shared.EventString)
local v12 = {}
local v_u_13 = v_u_2:new():add_set_from_table_list({ v_u_10.NoteHit, v_u_10.HeldHitHead })
local v_u_14 = v_u_2:new():add_set_from_table_list({ v_u_10.HeldHitTail, v_u_10.HeldMissHeadHitTail })
local v_u_15 = v_u_2:new():add_set_from_table_list({
    v_u_10.WhiffMiss,
    v_u_10.NoteTimeMiss,
    v_u_10.HeldTimeMissHead,
    v_u_10.HeldTimeMissTail,
    v_u_10.HeldReleaseEarly
})
local v_u_16 = v_u_2:new():add_set_from_table_list({ v_u_10.WhiffMiss, v_u_10.HeldReleaseEarly })
local v_u_17 = v_u_2:new():add_set_from_table_list({ v_u_10.HeldTimeMissTail })
local v_u_18 = {
    ["TimeTrigger"] = 0,
    ["LookAheadTrigger"] = 1,
    ["MissTimeTrigger"] = 2,
    ["Autoplay"] = 3,
    ["ComboPlayback"] = 4
}
local v_u_19 = {
    ["PressHit"] = 0,
    ["PressNoHit"] = 1,
    ["ReleaseHit"] = 2,
    ["ReleaseNoHit"] = 3,
    ["HandledMiss"] = 4
}
v12.new = function(_, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (copy 3): v_u_7, (copy 4): v_u_2, (copy 5): v_u_3, (copy 6): v_u_18, (copy 7): v_u_19, (copy 8): v_u_4, (copy 9): v_u_14, (copy 10): v_u_13, (copy 11): v_u_15, (copy 12): v_u_16, (copy 13): v_u_17, (copy 14): v_u_10, (copy 15): v_u_6, (copy 16): v_u_1, (copy 17): v_u_5, (copy 18): v_u_11 ]]
    local v23 = {
        ["notify_time_miss"] = function(p22) --[[ Name: notify_time_miss ]] --[[ Line: 534 ]]
            p22:combo_based_tar_noteresult_next()
        end
    }
    local v_u_24 = nil
    v23.cons = function(_) --[[ Name: cons ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_20, (ref 3): v_u_24 ]]
        v_u_9:singleton():get_data_for_key(p_u_20:es_gamelocal_get_audiomanager():get_song_key(), function(p25) --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            v_u_24 = p25.HitObjects
        end)
    end;
    local function f_get_slot() --[[ Name: get_slot ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): p_u_21 ]]
        return p_u_21:get_game_slot();
    end;
    local function _(p26) --[[ Name: get_note_type ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        if v_u_24 == nil then
            return false, false;
        end;
        local v27 = v_u_24[p26:get_note_index()]
        return v27.Type == 1, v27.Type == 2;
    end;
    local function _() --[[ Name: is_local_slot ]] --[[ Line: 80 ]]
        --[[ Upvalues: (copy 1): p_u_21, (copy 2): p_u_20 ]]
        return p_u_21:get_game_slot() == p_u_20:get_local_game_slot();
    end;
    local v_u_28 = 0
    v23.update = function(p29, p30) --[[ Name: update ]] --[[ Line: 85 ]]
        --[[ Upvalues: (copy 1): p_u_20, (copy 2): p_u_21, (ref 3): v_u_24, (ref 4): v_u_28, (ref 5): v_u_8, (ref 6): v_u_7 ]]
        if p_u_20 == nil or (p_u_21 == nil or v_u_24 == nil) then
            return;
        else
            v_u_28 = v_u_8:TimescaleToDeltaTime(p30) * 1000
            if p_u_21:get_game_slot() == p_u_20:get_local_game_slot() == true then
                if p_u_21:get_game_slot() == p_u_20:get_local_game_slot() and p_u_20:is_spectate() then
                    p29:test_active_notes(false, true, false)
                    return;
                elseif p_u_21:get_game_slot() == p_u_20:get_local_game_slot() and v_u_7.LocalAutoPlay == true then
                    p29:test_active_notes(true, false, false)
                elseif p_u_21:get_game_slot() == p_u_20:get_local_game_slot() and p_u_21:get_force_update_auto_player() == true then
                    p29:test_active_notes(true, false, false)
                end;
            else
                p29:test_active_notes(false, false, true)
                return;
            end;
        end;
    end;
    local function f_note_can_hit_noteresult(p31, p32) --[[ Name: note_can_hit_noteresult ]] --[[ Line: 100 ]]
        --[[ Upvalues: (copy 1): p_u_20 ]]
        local _, v33 = p31:es_note_test_hit(p_u_20)
        return v33 == p32, v33;
    end;
    local function f_note_can_release_noteresult(p34, p35) --[[ Name: note_can_release_noteresult ]] --[[ Line: 105 ]]
        --[[ Upvalues: (copy 1): p_u_20 ]]
        local _, v36 = p34:es_note_test_release(p_u_20)
        return v36 == p35, v36;
    end;
    local function f_empty_notesequence_playback_buffer() --[[ Name: empty_notesequence_playback_buffer ]] --[[ Line: 110 ]]
        --[[ Upvalues: (copy 1): p_u_20 ]]
        local v37 = p_u_20:get_spectate_manager()
        if v37 ~= nil then
            local v38 = v37:get_active_note_sequence()
            return v38:get_time_start() > p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms() or v38:get_time_end() < p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms();
        end;
    end;
    local v_u_39 = v_u_2:new()
    local v_u_40 = v_u_3:new()
    local v_u_41 = -1
    local v_u_42 = nil
    local v_u_43 = 0
    local l_TimeTrigger_0 = v_u_18.TimeTrigger
    local l_PressHit_0 = v_u_19.PressHit
    local v_u_44 = 0
    local v_u_45 = 0
    local function _() --[[ Name: get_audio_manager_time ]] --[[ Line: 135 ]]
        --[[ Upvalues: (copy 1): p_u_20 ]]
        return p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms();
    end;
    v23.test_active_notes = function(p46, p47, p48, p49) --[[ Name: test_active_notes ]] --[[ Line: 139 ]]
        --[[ Upvalues: (copy 1): v_u_40, (ref 2): v_u_4, (copy 3): p_u_20, (ref 4): v_u_42, (ref 5): v_u_43, (ref 6): l_TimeTrigger_0, (ref 7): v_u_18, (ref 8): v_u_14, (ref 9): v_u_41, (ref 10): v_u_44, (copy 11): f_empty_notesequence_playback_buffer, (ref 12): v_u_45, (copy 13): p_u_21, (copy 14): v_u_39, (ref 15): l_PressHit_0, (ref 16): v_u_19, (ref 17): v_u_24, (ref 18): v_u_13 ]]
        p46:update_spectate_note_sequence_events_start_index()
        p46:handle_misses()
        for v50 = v_u_40:count(), 1, -1 do
            local v51 = false
            local v52 = v_u_40:get(v50)
            local v53 = v52:get_track_index()
            local v54 = false
            local v55 = false
            local v56 = nil
            local v57 = nil
            if p47 == true then
                local l_NoteResult_Perfect_0 = v_u_4.NoteResult_Perfect
                local _, v58 = v52:es_note_test_release(p_u_20)
                if v58 == l_NoteResult_Perfect_0 then
                    v51 = true
                    v_u_42 = nil
                    v_u_43 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
                    l_TimeTrigger_0 = v_u_18.Autoplay
                end;
            elseif p48 == true then
                local v59, v60 = p46:note_contained_in_spectate_replication(v52, v_u_14)
                if v59 == nil or not p46:note_can_release_notesequence_event(v52, v59) then
                    v60 = v57
                else
                    v51 = true
                    v55 = true
                    p46:add_spectate_replication_event_handled_index(v60)
                    v_u_41 = v60
                    v_u_42 = v59
                    v_u_43 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
                    v_u_44 = v_u_44 + 1
                    v56 = v59
                end;
                if v59 == nil and f_empty_notesequence_playback_buffer() then
                    v57 = v60
                    v54 = true
                else
                    v57 = v60
                end;
            elseif p49 == true then
                v54 = true
            end;
            if v54 == true and p46:should_release_note_combo_based_play(v52) then
                v51 = true
                p46:combo_based_tar_noteresult_next()
                v_u_42 = nil
                v_u_43 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
                l_TimeTrigger_0 = v_u_18.ComboPlayback
                v_u_45 = v_u_45 + 1
            end;
            if v51 == true then
                if p_u_21:get_game_slot() == p_u_20:get_local_game_slot() then
                    p_u_20:debug_any_press()
                end;
                if v_u_39:contains(v53) ~= true then
                    p_u_21:es_tracksystem_press_index(p_u_20, v53)
                end;
                v_u_39:remove(v53)
                v_u_40:remove_at(v50)
                if p_u_21:es_tracksystem_release_index(p_u_20, v53) then
                    l_PressHit_0 = v_u_19.ReleaseHit
                else
                    l_PressHit_0 = v_u_19.ReleaseNoHit
                end;
            end;
            if v55 == true then
                p46:update_scoremanager_to_note_sequence_event(v56, v57)
            end;
        end;
        local v61 = p_u_21:es_tracksystem_get_notes()
        for v62 = 1, v61:count() do
            local v63 = v61:get(v62)
            local v64 = v63:get_track_index()
            local v65, v66
            if v_u_24 == nil then
                v65 = false
                v66 = false
            else
                local v67 = v_u_24[v63:get_note_index()]
                v66 = v67.Type == 1
                v65 = v67.Type == 2
            end;
            local v68 = false
            local v69 = false
            local v70 = false
            local v71 = nil
            local v72 = nil
            if not v65 or v_u_40:contains(v63) ~= true then
                if p47 == true then
                    local l_NoteResult_Perfect_1 = v_u_4.NoteResult_Perfect
                    local _, v73 = v63:es_note_test_hit(p_u_20)
                    if v73 == l_NoteResult_Perfect_1 then
                        v69 = true
                        v_u_42 = nil
                        v_u_43 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
                        l_TimeTrigger_0 = v_u_18.Autoplay
                    end;
                elseif p48 == true then
                    local v74, v75 = p46:note_contained_in_spectate_replication(v63, v_u_13)
                    if v74 == nil or not p46:note_can_hit_notesequence_event(v63, v74) then
                        v75 = v72
                    else
                        v69 = true
                        v70 = true
                        if v66 then
                            p46:add_spectate_replication_event_handled_index(v75)
                        end;
                        v_u_41 = v75
                        v_u_42 = v74
                        v_u_43 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
                        v_u_44 = v_u_44 + 1
                        v71 = v74
                    end;
                    if v74 == nil and f_empty_notesequence_playback_buffer() then
                        v72 = v75
                        v68 = true
                    else
                        v72 = v75
                    end;
                elseif p49 == true then
                    v68 = true
                end;
            end;
            if v68 == true and p46:should_hit_note_combo_based_play(v63) then
                v69 = true
                p46:combo_based_tar_noteresult_next()
                v_u_42 = nil
                v_u_43 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
                l_TimeTrigger_0 = v_u_18.ComboPlayback
                v_u_45 = v_u_45 + 1
            end;
            if v69 == true then
                if p_u_20:get_local_game_slot() == p_u_21:get_game_slot() then
                    p_u_20:debug_any_press()
                end;
                local v76 = false
                if v66 == true then
                    v76 = p_u_21:es_tracksystem_press_index(p_u_20, v64)
                    p_u_21:es_tracksystem_release_index(p_u_20, v64)
                elseif v65 == true and v_u_40:contains(v63) ~= true then
                    v_u_39:add(v64, true)
                    v_u_40:push_back(v63)
                    v76 = p_u_21:es_tracksystem_press_index(p_u_20, v64)
                end;
                if v76 then
                    l_PressHit_0 = v_u_19.PressHit
                else
                    l_PressHit_0 = v_u_19.PressNoHit
                end;
            end;
            if v70 == true then
                p46:update_scoremanager_to_note_sequence_event(v71, v72)
            end;
        end;
        if p_u_21:get_game_slot() == p_u_20:get_local_game_slot() then
            p46:update_status_text()
        end;
    end;
    local v_u_77 = v_u_2:new()
    v23.add_spectate_replication_event_handled_index = function(_, p78) --[[ Name: add_spectate_replication_event_handled_index ]] --[[ Line: 333 ]]
        --[[ Upvalues: (copy 1): v_u_77 ]]
        v_u_77:add(p78, true)
    end;
    v23.handle_misses = function(p79) --[[ Name: handle_misses ]] --[[ Line: 338 ]]
        --[[ Upvalues: (copy 1): p_u_20, (copy 2): v_u_77, (ref 3): v_u_15, (ref 4): v_u_16, (copy 5): p_u_21, (copy 6): v_u_39, (ref 7): v_u_17, (copy 8): v_u_40, (ref 9): v_u_41, (ref 10): v_u_42, (ref 11): v_u_43, (ref 12): l_TimeTrigger_0, (ref 13): v_u_18, (ref 14): l_PressHit_0, (ref 15): v_u_19, (ref 16): v_u_44 ]]
        local v80 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
        local v81 = p_u_20:get_spectate_manager()
        if v81 ~= nil then
            local v82 = v81:get_active_note_sequence():get_events()
            for v83 = p79:get_spectate_note_sequence_events_start_index(), v82:count() do
                if v_u_77:contains(v83) ~= true then
                    local v84 = v82:get(v83)
                    if v84:get_time() < v80 and v_u_15:contains(v84:get_note_hit_mode()) then
                        p79:add_spectate_replication_event_handled_index(v83)
                        local v85 = v84:get_track_index()
                        if v_u_16:contains(v84:get_note_hit_mode()) then
                            p_u_21:es_tracksystem_press_index(p_u_20, v85)
                            p_u_21:es_tracksystem_release_index(p_u_20, v85)
                            v_u_39:remove(v85)
                        end;
                        if v_u_17:contains(v84:get_note_hit_mode()) then
                            for v86 = v_u_40:count(), 1, -1 do
                                if v_u_40:get(v86):get_track_index() == v85 then
                                    v_u_40:remove_at(v86)
                                end;
                            end;
                        end;
                        p79:update_scoremanager_to_note_sequence_event(v84, v83)
                        v_u_41 = v83
                        v_u_42 = v84
                        v_u_43 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms()
                        l_TimeTrigger_0 = v_u_18.MissTimeTrigger
                        l_PressHit_0 = v_u_19.HandledMiss
                        v_u_44 = v_u_44 + 1
                    end;
                end;
            end;
        end;
    end;
    v23.note_contained_in_spectate_replication = function(p87, p88, p89) --[[ Name: note_contained_in_spectate_replication ]] --[[ Line: 382 ]]
        --[[ Upvalues: (copy 1): p_u_20, (copy 2): v_u_77 ]]
        local v90 = p_u_20:get_spectate_manager()
        if v90 ~= nil then
            local v91 = v90:get_active_note_sequence():get_events()
            for v92 = p87:get_spectate_note_sequence_events_start_index(), v91:count() do
                if v_u_77:contains(v92) ~= true then
                    local v93 = v91:get(v92)
                    if v93:get_note_index() == p88:get_note_index() and p89:contains(v93:get_note_hit_mode()) then
                        return v93, v92;
                    end;
                end;
            end;
        end;
    end;
    local function f_test_hit_timeoffset_greater_or_match_noteresult(p94, p95, p96) --[[ Name: test_hit_timeoffset_greater_or_match_noteresult ]] --[[ Line: 400 ]]
        --[[ Upvalues: (ref 1): l_TimeTrigger_0, (ref 2): v_u_18, (ref 3): v_u_28, (copy 4): p_u_20 ]]
        if p95:get_hit_time_offset() < p94 then
            l_TimeTrigger_0 = v_u_18.TimeTrigger
            return true;
        end;
        local v97 = v_u_28 * 2
        local _, v98 = p96:es_note_test_hit(p_u_20, 0)
        local _, v99 = p96:es_note_test_hit(p_u_20, v97)
        if p94 + v97 <= p95:get_hit_time_offset() or (v98 ~= p95:get_note_result() or v99 == p95:get_note_result()) then
            return false;
        end;
        l_TimeTrigger_0 = v_u_18.LookAheadTrigger
        return true;
    end;
    v23.note_can_hit_notesequence_event = function(_, p100, p101) --[[ Name: note_can_hit_notesequence_event ]] --[[ Line: 419 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_10, (copy 3): f_test_hit_timeoffset_greater_or_match_noteresult, (ref 4): v_u_6, (ref 5): v_u_1, (ref 6): v_u_5 ]]
        local v102, v103
        if v_u_24 == nil then
            v102 = false
            v103 = false
        else
            local v104 = v_u_24[p100:get_note_index()]
            v102 = v104.Type == 1
            v103 = v104.Type == 2
        end;
        local v105 = p101:get_note_hit_mode()
        if v102 then
            if v105 == v_u_10.NoteHit then
                if f_test_hit_timeoffset_greater_or_match_noteresult(p100:get_delta_time_from_hit_time(), p101, p100) then
                    return true;
                end;
            else
                v_u_6:warnf("NoteSequencePlayer:note_can_hit_notesequence_event is_note unexpected note_hit_mode(%s) note_index(%d) event(%s)", v_u_1:enum_val_to_name(v105, v_u_10), p100:get_note_index(), p101:debug_str())
            end;
        elseif v103 and (p100:get_state() == v_u_5.State.Pre or p100:get_state() == v_u_5.State.HoldMissedActive) then
            if v105 == v_u_10.HeldHitHead or v105 == v_u_10.HeldMissHeadHitTail then
                if f_test_hit_timeoffset_greater_or_match_noteresult(p100:get_delta_time_from_hit_time(), p101, p100) then
                    return true;
                end;
            else
                v_u_6:warnf("NoteSequencePlayer:note_can_hit_notesequence_event is_heldnote unexpected note_hit_mode(%s)", v_u_1:enum_val_to_name(v105, v_u_10))
            end;
        end;
        return false;
    end;
    local function f_test_release_timeoffset_greater_or_match_noteresult(p106, p107, p108) --[[ Name: test_release_timeoffset_greater_or_match_noteresult ]] --[[ Line: 453 ]]
        --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_28 ]]
        if p107:get_hit_time_offset() < p106 then
            return true;
        end;
        local _, v109 = p108:es_note_test_release(p_u_20, 0)
        local _, v110 = p108:es_note_test_release(p_u_20, v_u_28)
        return p106 + v_u_28 * 1.75 > p107:get_hit_time_offset() and (v109 == p107:get_note_result() and v110 ~= p107:get_note_result());
    end;
    v23.note_can_release_notesequence_event = function(_, p111, p112) --[[ Name: note_can_release_notesequence_event ]] --[[ Line: 469 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_6, (ref 3): v_u_10, (copy 4): f_test_release_timeoffset_greater_or_match_noteresult ]]
        local v113
        if v_u_24 == nil then
            v113 = false
        else
            v113 = v_u_24[p111:get_note_index()].Type == 2
        end;
        if v113 == true then
            local v114 = p112:get_note_hit_mode()
            return (v114 == v_u_10.HeldHitTail or v114 == v_u_10.HeldMissHeadHitTail) and f_test_release_timeoffset_greater_or_match_noteresult(p111:get_delta_time_from_release_time(), p112, p111) and true or false;
        else
            v_u_6:warnf("NoteSequencePlayer:note_can_release_notesequence_event is_heldnote(false)")
            return false;
        end;
    end;
    local v_u_115 = 0
    v23.combo_based_tar_noteresult_next = function(_) --[[ Name: combo_based_tar_noteresult_next ]] --[[ Line: 486 ]]
        --[[ Upvalues: (ref 1): v_u_115, (ref 2): v_u_1 ]]
        v_u_115 = v_u_1:rand_rangei(0, 10)
    end;
    v23:combo_based_tar_noteresult_next()
    local function f_get_combo_based_tar_noteresult() --[[ Name: get_combo_based_tar_noteresult ]] --[[ Line: 491 ]]
        --[[ Upvalues: (copy 1): p_u_20, (copy 2): f_get_slot, (ref 3): v_u_4, (ref 4): v_u_115 ]]
        local v116 = p_u_20._players._slots:get(f_get_slot())
        local v117, v118
        if v116 == nil then
            v117 = 1
            v118 = 0
        else
            v117 = v116._update_from_player_info_count
            v118 = v116._chain
        end;
        if v117 == 0 then
            return v_u_4.NoteResult_Perfect;
        elseif v118 <= 1 then
            return v_u_4.NoteResult_Miss;
        elseif v118 < 10 then
            if v_u_115 < 2 then
                return v_u_4.NoteResult_Okay;
            elseif v_u_115 < 6 then
                return v_u_4.NoteResult_Great;
            else
                return v_u_4.NoteResult_Perfect;
            end;
        elseif v_u_115 < 3 then
            return v_u_4.NoteResult_Great;
        else
            return v_u_4.NoteResult_Perfect;
        end;
    end;
    v23.should_hit_note_combo_based_play = function(_, p119) --[[ Name: should_hit_note_combo_based_play ]] --[[ Line: 522 ]]
        --[[ Upvalues: (copy 1): f_get_combo_based_tar_noteresult, (ref 2): v_u_4, (copy 3): f_note_can_hit_noteresult ]]
        local v120 = f_get_combo_based_tar_noteresult()
        if v120 == v_u_4.NoteResult_Miss then
            return false;
        else
            return f_note_can_hit_noteresult(p119, v120);
        end;
    end;
    v23.should_release_note_combo_based_play = function(_, p121) --[[ Name: should_release_note_combo_based_play ]] --[[ Line: 528 ]]
        --[[ Upvalues: (copy 1): f_get_combo_based_tar_noteresult, (ref 2): v_u_4, (copy 3): f_note_can_release_noteresult ]]
        local v122 = f_get_combo_based_tar_noteresult()
        if v122 == v_u_4.NoteResult_Miss then
            return false;
        else
            return f_note_can_release_noteresult(p121, v122);
        end;
    end;
    local v_u_123 = 1
    v23.get_spectate_note_sequence_events_start_index = function(_) --[[ Name: get_spectate_note_sequence_events_start_index ]] --[[ Line: 539 ]]
        --[[ Upvalues: (ref 1): v_u_123 ]]
        return v_u_123;
    end;
    v23.update_spectate_note_sequence_events_start_index = function(_) --[[ Name: update_spectate_note_sequence_events_start_index ]] --[[ Line: 544 ]]
        --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_123, (copy 3): v_u_77 ]]
        local v124 = p_u_20:get_spectate_manager()
        if v124 == nil then
            return;
        end;
        local v125 = v124:get_active_note_sequence():get_events()
        if v125:count() == 0 then
            return;
        end;
        local v126 = p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms() - 5000
        for v127 = v_u_123, v125:count() do
            if v125:get(v127):get_time() >= v126 and not v_u_77:contains(v127) then
                break;
            end;
            v_u_123 = v127
        end;
    end;
    v23.on_switch_focus_slot = function(_) --[[ Name: on_switch_focus_slot ]] --[[ Line: 562 ]]
        --[[ Upvalues: (ref 1): v_u_123, (copy 2): v_u_77 ]]
        v_u_123 = 1
        v_u_77:clear()
    end;
    v23.update_scoremanager_to_note_sequence_event = function(_, p128, p129) --[[ Name: update_scoremanager_to_note_sequence_event ]] --[[ Line: 567 ]]
        --[[ Upvalues: (copy 1): p_u_21, (copy 2): p_u_20, (ref 3): v_u_11 ]]
        if p_u_21:get_game_slot() == p_u_20:get_local_game_slot() then
            local v130, _ = p_u_20:es_gamelocal_get_scoremanager():get_score_objs()
            v130:es_playerscore_set_powerbar_state(v_u_11:active_bool_to_state(p128:get_is_fever()), p128:get_fever_pct())
            p_u_20:es_gamelocal_get_scoremanager():set_spectate_replicate_accuracy(p128:get_accuracy())
            if p_u_20:get_spectate_manager() then
                local v131 = p_u_20:get_spectate_manager():get_score_index_checkpoints()
                if v131:contains(p129) then
                    local v132 = v131:get(p129)
                    v130:es_playerscore_set_score(v132:get_score())
                    v130:set_chain(v132:get_combo())
                end;
            end;
        end;
    end;
    v23.update_status_text = function(p133) --[[ Name: update_status_text ]] --[[ Line: 591 ]]
        --[[ Upvalues: (copy 1): p_u_20, (copy 2): p_u_21, (ref 3): v_u_43, (ref 4): v_u_44, (ref 5): v_u_45, (ref 6): v_u_1, (ref 7): l_TimeTrigger_0, (ref 8): v_u_18, (ref 9): l_PressHit_0, (ref 10): v_u_19, (ref 11): v_u_42 ]]
        local v134 = p_u_20:get_spectate_manager()
        if v134 ~= nil then
            local v135 = v134:get_active_note_sequence()
            p_u_20:get_spectate_manager():set_ui_status_text(string.format("Slot(%d) Time(%.2f) SeqTime(%.2f,%.2f) SeqCount(%d) StartIndex(%d)", p_u_21:get_game_slot(), p_u_20:es_gamelocal_get_audiomanager():get_song_time_position_ms(), v135:get_time_start(), v135:get_time_end(), v135:get_events():count(), (p133:get_spectate_note_sequence_events_start_index())) .. "\n" .. string.format("Event: Time(%.2f) EventCount(%d) ComboPlaybackCount(%d) Trigger(%s) Result(%s)", v_u_43, v_u_44, v_u_45, v_u_1:enum_val_to_name(l_TimeTrigger_0, v_u_18), v_u_1:enum_val_to_name(l_PressHit_0, v_u_19)) .. "\n" .. (v_u_42 == nil and "nil" or v_u_42:debug_str()) .. "\n")
        end;
    end;
    v23:cons()
    return v23;
end;
return v12;
