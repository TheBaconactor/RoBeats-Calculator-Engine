-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:22 PM
-- Time elapsed: 15 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.NotePlaybackSequence)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerScore)
require(game.ReplicatedStorage.Shared.PowerBarState)
local v_u_9 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_10 = require(game.ReplicatedStorage.Shared.StreamingVarianceCollector)
local v_u_11 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_12 = require(game.ReplicatedStorage.Shared.NoteHitMode)
local v13 = {
    ["ResyncErrorMode"] = {
        ["None"] = 0,
        ["Fever"] = 1,
        ["NoteIndex"] = 2,
        ["Combo"] = 3,
        ["ScoreEnd"] = 4,
        ["NoteResultMismatch"] = 5
    }
}
local v_u_14 = {
    ["None"] = 0,
    ["Fever"] = 1,
    ["NoteIndex"] = 2,
    ["Combo"] = 3,
    ["ScoreEnd"] = 4,
    ["NoteResultMismatch"] = 5
}
v13.new = function(_, _, p15, p16, p17) --[[ Name: new ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_8, (copy 4): v_u_11, (copy 5): v_u_10, (copy 6): v_u_2, (copy 7): v_u_9, (copy 8): v_u_12, (copy 9): v_u_3, (copy 10): v_u_5, (copy 11): v_u_14, (copy 12): v_u_4, (copy 13): v_u_7 ]]
    local v18 = {}
    local v_u_19 = nil
    v_u_6:singleton():get_data_for_key(p17, function(p20) --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        v_u_19 = p20.HitObjects
    end)
    local v_u_21 = v_u_1:new()
    local v_u_22 = v_u_8:new(p15._selected_song_key, p16._gear_stats)
    v_u_22:set_apply_hit_to_powerbar(false)
    local v_u_23 = v_u_8:new(p15._selected_song_key, v_u_11:statsdict_base())
    v_u_23:set_apply_hit_to_powerbar(false)
    local v_u_24 = 0
    local v_u_25 = v_u_10:new()
    local v_u_26 = v_u_2:new()
    v18.test_event_note_index = function(_, p27) --[[ Name: test_event_note_index ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_9, (copy 3): v_u_26 ]]
        if v_u_19 == nil then
            return false;
        end;
        if p27:get_note_result() == v_u_9.NoteResult_Miss then
            return true;
        end;
        local v28 = p27:get_note_index()
        if v28 <= 0 or #v_u_19 < v28 then
            return false;
        end;
        local v29 = v_u_19[v28].Type == 2 and 2 or 1
        if v_u_26:contains(v28) then
            if v_u_26:get(v28) > v29 - 1 then
                return false;
            end;
        else
            v_u_26:add(v28, 0)
        end;
        v_u_26:add(v28, v_u_26:get(v28) + 1)
        return true;
    end;
    v18.get_verified_event_time = function(_, p30) --[[ Name: get_verified_event_time ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_9, (copy 3): v_u_22, (ref 4): v_u_12, (ref 5): v_u_3, (ref 6): v_u_5 ]]
        if v_u_19 == nil then
            return -1;
        end;
        local v31 = p30:get_time()
        if p30:get_note_result() == v_u_9.NoteResult_Miss then
            return v31;
        end;
        local v32 = p30:get_note_index()
        local l_Type_0 = v_u_19[v32].Type
        local l_Time_0 = v_u_19[v32].Time
        local v33, v34 = v_u_22:get_okay_upper_lower_time()
        local v35 = v33 - v34
        local v36 = p30:get_note_hit_mode()
        if l_Type_0 == 2 and (v36 == v_u_12.HeldHitTail or v36 == v_u_12.HeldMissHeadHitTail) then
            local v37 = l_Time_0 + (v_u_19[v32].Duration == nil and 0 or v_u_19[v32].Duration)
            if v31 < v37 - v35 then
                if v_u_3:is_dev_build() then
                    v_u_5:warnf("ServerPlayerNoteSequenceInfo:get_verified_event_time() hitobject_type == 2 bound lower")
                end;
                v31 = v37 - v35
            end;
            if v37 + v35 < v31 then
                if v_u_3:is_dev_build() then
                    v_u_5:warnf("ServerPlayerNoteSequenceInfo:get_verified_event_time() hitobject_type == 2 bound upper")
                end;
                return v37 + v35;
            end;
        else
            if v31 < l_Time_0 - v35 then
                if v_u_3:is_dev_build() then
                    v_u_5:warnf("ServerPlayerNoteSequenceInfo:get_verified_event_time() bound lower")
                end;
                v31 = l_Time_0 - v35
            end;
            if l_Time_0 + v35 < v31 then
                if v_u_3:is_dev_build() then
                    v_u_5:warnf("ServerPlayerNoteSequenceInfo:get_verified_event_time() bound upper")
                end;
                v31 = l_Time_0 + v35
            end;
        end;
        return v31;
    end;
    v18.push_note_sequence = function(p38, p39) --[[ Name: push_note_sequence ]] --[[ Line: 129 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_9, (ref 3): v_u_19, (ref 4): v_u_12, (ref 5): v_u_3, (ref 6): v_u_5, (ref 7): v_u_11, (copy 8): v_u_22, (copy 9): v_u_23, (ref 10): v_u_24, (ref 11): v_u_4, (copy 12): v_u_25, (copy 13): v_u_26, (copy 14): v_u_21, (ref 15): v_u_7 ]]
        local l_None_0 = v_u_14.None
        local v40 = p39:get_events()
        local v41 = false
        local v42 = ""
        for v43 = 1, v40:count() do
            local v44 = v40:get(v43)
            if p38:test_event_note_index(v44) then
                local v45 = v44:get_note_result()
                local v46
                if v45 == v_u_9.NoteResult_Miss then
                    v46 = v45
                else
                    local v47 = v44:get_note_index()
                    local v48 = v_u_19 ~= nil and (v_u_19[v47] ~= nil and (v_u_19[v47].Type == 2 and v_u_19[v47].Duration ~= nil))
                    local v49 = v44:get_note_hit_mode()
                    if v48 == true then
                        if v49 ~= v_u_12.HeldHitHead and (v49 ~= v_u_12.HeldHitTail and v49 ~= v_u_12.HeldMissHeadHitTail) then
                            v44:set_note_hit_mode(v_u_12.HeldHitHead)
                            if v_u_3:is_dev_build() then
                                v_u_5:warnf("ServerPlayerNoteSequenceInfo:push_note_sequence() validate-fail note_hit_mode(%s) is_held_note(%s) note_index(%d)", v_u_3:enum_val_to_name(v49, v_u_12), tostring(v48), v47)
                            end;
                        end;
                    elseif v49 ~= v_u_12.NoteHit then
                        v44:set_note_hit_mode(v_u_12.NoteHit)
                        if v_u_3:is_dev_build() then
                            v_u_5:warnf("ServerPlayerNoteSequenceInfo:push_note_sequence() validate-fail note_hit_mode(%s) is_held_note(%s) note_index(%d)", v_u_3:enum_val_to_name(v49, v_u_12), tostring(v48), v47)
                        end;
                    end;
                    local v50, v51, v52, v53, v54, v55 = v_u_11:get_note_times(v_u_22:get_statsdict(), v_u_11:note_hit_mode_get_time_multiplier(v44:get_note_hit_mode()))
                    v46 = v_u_3:timedelta_to_result(v44:get_hit_time_offset(), v50, v51, v52, v53, v54, v55)
                    if v46 == v45 then
                        v46 = v45
                    else
                        v42 = string.format("NoteResult mismatch event(%s) calculated(%s) hit_time_offset(%s)", tostring(v44:get_note_result()), tostring(v46), (tostring(v44:get_hit_time_offset())))
                        l_None_0 = v_u_14.NoteResultMismatch
                        v41 = true
                    end;
                    if v46 ~= v_u_9.NoteResult_Miss then
                        local v56 = v44:get_note_hit_mode()
                        if v_u_19 ~= nil and v_u_19[v47] ~= nil then
                            local l_Time_1 = v_u_19[v47].Time
                            if v56 == v_u_12.HeldHitTail or v56 == v_u_12.HeldMissHeadHitTail then
                                l_Time_1 = l_Time_1 + (v_u_19[v47].Duration == nil and 0 or v_u_19[v47].Duration)
                            end;
                            local v57 = math.floor((v44:get_hit_time_offset()))
                            local v58 = math.floor(v44:get_time() - l_Time_1)
                            if math.abs(v57 - v58) > 1 then
                                v44:set_time(l_Time_1 + v57)
                                if v_u_3:is_dev_build() then
                                    v_u_5:warnf("delta(%.2f) itr_event:get_hit_time_offset(%.2f) hitobject_time-event_time(%.2f)", math.abs(v57 - v58), v57, v58)
                                end;
                            end;
                        end;
                    end;
                end;
                v_u_22:es_playerscore_apply_hit_to_powerbar(v46)
                v_u_23:es_playerscore_apply_hit_to_powerbar(v46)
                local v59 = p38:get_verified_event_time(v44)
                local v60 = math.max(0, v59 - v_u_24)
                v_u_24 = v59
                local v61 = v_u_4:DeltaTimeToTimescale(v60 / 1000)
                v_u_22:update(v61, false, false)
                v_u_23:update(v61, false, false)
                if v44:get_fever_pct() ~= v_u_22:get_power_bar_pct() then
                    v44:set_fever_pct(v_u_22:get_power_bar_pct())
                end;
                if v44:get_is_fever() ~= v_u_22:is_powerbar_active() then
                    if v41 ~= true then
                        l_None_0 = v_u_14.Fever
                        v42 = string.format("fever event[%s](%.2f) _player_score[%s](%.2f) time(%d) note_index(%d)", tostring(v44:get_is_fever()), v44:get_fever_pct(), tostring(v_u_22:is_powerbar_active()), v_u_22:get_power_bar_pct(), v44:get_time(), v44:get_note_index())
                        v41 = true
                    end;
                    v44:set_is_fever(v_u_22:is_powerbar_active())
                end;
                v_u_22:register_hit_noteresult_hitmode(v44:get_note_result(), v44:get_note_hit_mode())
                v_u_23:register_hit_noteresult_hitmode(v44:get_note_result(), v44:get_note_hit_mode())
                if v44:get_note_result() ~= v_u_9.NoteResult_Miss then
                    v_u_25:push_val(v44:get_hit_time_offset())
                end;
            else
                l_None_0 = v_u_14.NoteIndex
                v42 = string.format("note_index index(%d) count(%d)", v44:get_note_index(), not v_u_26:contains(v44:get_note_index()) and -1 or v_u_26:get(v44:get_note_index()))
                v41 = true
            end;
        end;
        if v41 ~= true and p39:get_combo_end() ~= v_u_22:get_chain() then
            l_None_0 = v_u_14.Combo
            v42 = string.format("combo seq:combo_end(%d) player_score:get_chain(%d)", p39:get_combo_end(), v_u_22:get_chain())
            v41 = true
        end;
        if v41 ~= true and p39:get_score_end() ~= v_u_22:get_score() then
            l_None_0 = v_u_14.ScoreEnd
            v42 = string.format("score seq:get_score_end(%d) player_score:get_score(%d)", p39:get_score_end(), v_u_22:get_score())
            v41 = true
        end;
        if v41 then
            p39:set_combo_end(v_u_22:get_chain())
            p39:set_score_end(v_u_22:get_score())
        end;
        v_u_21:push_back(p39)
        if v_u_21:count() > v_u_7.SERVER_PLAYER_NOTE_SEQUENCE_QUEUE_SIZE then
            v_u_21:pop_front()
        end;
        return v41, l_None_0, v42;
    end;
    v18.get_serialized_note_sequence_table_list_starting_at = function(_, p62) --[[ Name: get_serialized_note_sequence_table_list_starting_at ]] --[[ Line: 301 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        local v63 = p62
        local v64 = {}
        for v65 = 1, v_u_21:count() do
            local v66 = v_u_21:get(v65)
            if p62 <= v66:get_time_start() then
                v64[#v64 + 1] = v66:serialize_to_table(true)
                v63 = math.max(v63, v66:get_time_end())
            end;
        end;
        return v64, v63;
    end;
    v18.get_hit_time_avg_ct = function(_) --[[ Name: get_hit_time_avg_ct ]] --[[ Line: 314 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        return v_u_25:get_stdev(), v_u_25:get_ct();
    end;
    v18.get_player_score = function(_) --[[ Name: get_player_score ]] --[[ Line: 318 ]]
        --[[ Upvalues: (copy 1): v_u_22 ]]
        return v_u_22;
    end;
    v18.get_player_naked_score = function(_) --[[ Name: get_player_naked_score ]] --[[ Line: 322 ]]
        --[[ Upvalues: (copy 1): v_u_23 ]]
        return v_u_23;
    end;
    local v_u_67 = false
    v18.get_raise_resync_error = function(_) --[[ Name: get_raise_resync_error ]] --[[ Line: 327 ]]
        --[[ Upvalues: (ref 1): v_u_67 ]]
        return v_u_67;
    end;
    v18.set_raise_resync_error = function(_, p68) --[[ Name: set_raise_resync_error ]] --[[ Line: 328 ]]
        --[[ Upvalues: (ref 1): v_u_67 ]]
        v_u_67 = p68
    end;
    return v18;
end;
return v13;
