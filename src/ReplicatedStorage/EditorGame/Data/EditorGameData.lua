-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_13 = {
    ["NoteType"] = {
        ["Single"] = 1,
        ["Hold"] = 2
    },
    ["Track"] = {
        ["Track1"] = 1,
        ["Track2"] = 2,
        ["Track3"] = 3,
        ["Track4"] = 4
    },
    ["Note"] = {},
    ["get_earliest_allowed_note_time_ms"] = function(_) --[[ Name: get_earliest_allowed_note_time_ms ]] --[[ Line: 126 ]]
        return -1500;
    end,
    ["validate_note_data_list_paste"] = function(p6, p7, p8, p9) --[[ Name: validate_note_data_list_paste ]] --[[ Line: 175 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        local v10 = v_u_3:new()
        v10:push_back_from_list(p7)
        v10:push_back_from_list(p8)
        v_u_3:sort_fast(v10, function(p11, p12) --[[ Line: 179 ]]
            return p11:get_time_ms() < p12:get_time_ms();
        end)
        return p6:validate_note_data_list(v10, p9);
    end,
    ["TimingPoint"] = {},
    ["UndoState"] = {}
}
local v_u_14 = {
    ["Track1"] = 1,
    ["Track2"] = 2,
    ["Track3"] = 3,
    ["Track4"] = 4
}
v_u_13.Track.get_track_begin = function(p15) --[[ Name: get_track_begin ]] --[[ Line: 22 ]]
    return p15.Track1;
end;
v_u_13.Track.get_track_end = function(p16) --[[ Name: get_track_end ]] --[[ Line: 23 ]]
    return p16.Track4;
end;
v_u_13.Note.new = function(_) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_1 ]]
    local v17 = {}
    local v_u_18 = 0
    local l_Single_0 = v_u_13.NoteType.Single
    local l_Track1_0 = v_u_13.Track.Track1
    local v_u_19 = 0
    v17.get_time_ms = function(_) --[[ Name: get_time_ms ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    v17.set_time_ms = function(_, p20) --[[ Name: set_time_ms ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_18 ]]
        v_u_1:is_int(v_u_18)
        v_u_18 = p20
    end;
    v17.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): l_Single_0 ]]
        return l_Single_0;
    end;
    v17.set_type = function(_, p21) --[[ Name: set_type ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_13, (ref 3): l_Single_0 ]]
        v_u_1:is_enum_member(p21, v_u_13.NoteType)
        l_Single_0 = p21
    end;
    v17.get_track = function(_) --[[ Name: get_track ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): l_Track1_0 ]]
        return l_Track1_0;
    end;
    v17.set_track = function(_, p22) --[[ Name: set_track ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_13, (ref 3): l_Track1_0 ]]
        v_u_1:is_enum_member(p22, v_u_13.Track)
        l_Track1_0 = p22
    end;
    v17.get_duration = function(_) --[[ Name: get_duration ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        return v_u_19;
    end;
    v17.set_duration = function(_, p23) --[[ Name: set_duration ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_19 ]]
        v_u_1:is_number(p23)
        v_u_1:is_true(p23 > 0)
        v_u_19 = p23
    end;
    v17.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): l_Single_0, (ref 3): l_Track1_0, (ref 4): v_u_13, (ref 5): v_u_19 ]]
        local v24 = {
            ["Time"] = v_u_18,
            ["Type"] = l_Single_0,
            ["Track"] = l_Track1_0
        }
        if l_Single_0 == v_u_13.NoteType.Hold then
            v24.Duration = v_u_19
        end;
        return v24;
    end;
    v17.to_compressed_list = function(p25) --[[ Name: to_compressed_list ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_13, (ref 2): l_Track1_0, (ref 3): v_u_18, (ref 4): v_u_19 ]]
        return p25:get_type() == v_u_13.NoteType.Hold and { l_Track1_0, v_u_18, v_u_19 } or { l_Track1_0, v_u_18 };
    end;
    local v_u_26 = 0
    v17.local_get_selection_start_time_ms = function(_) --[[ Name: local_get_selection_start_time_ms ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v17.local_set_selection_start_time_ms = function(_, p27) --[[ Name: local_set_selection_start_time_ms ]] --[[ Line: 82 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = p27
    end;
    local l_Track1_1 = v_u_13.Track.Track1
    v17.local_get_selection_start_track = function(_) --[[ Name: local_get_selection_start_track ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): l_Track1_1 ]]
        return l_Track1_1;
    end;
    v17.local_set_selection_start_track = function(_, p28) --[[ Name: local_set_selection_start_track ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): l_Track1_1 ]]
        l_Track1_1 = p28
    end;
    local v_u_29 = 0
    v17.local_get_selection_start_duration = function(_) --[[ Name: local_get_selection_start_duration ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v17.local_set_selection_start_duration = function(_, p30) --[[ Name: local_set_selection_start_duration ]] --[[ Line: 90 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        v_u_29 = p30
    end;
    return v17;
end;
v_u_13.Note.invalid_local_selection_start_index = function(_) --[[ Name: invalid_local_selection_start_index ]] --[[ Line: 95 ]]
    return -1;
end;
v_u_13.Note.from_table = function(_, p31) --[[ Name: from_table ]] --[[ Line: 97 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_2 ]]
    local v32 = v_u_13.Note:new()
    v32:set_time_ms(p31.Time)
    v32:set_type(p31.Type)
    v32:set_track(p31.Track)
    if p31.Type == v_u_13.NoteType.Hold then
        if typeof(p31.Duration) == "number" and p31.Duration > 0 then
            v32:set_duration(p31.Duration)
            return v32;
        end;
        v_u_2:puts("Warning: Note from table has invalid duration, falling back to Single type.")
        v32:set_type(v_u_13.NoteType.Single)
    end;
    return v32;
end;
v_u_13.Note.from_compressed_list = function(_, p33) --[[ Name: from_compressed_list ]] --[[ Line: 113 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    local v34 = v_u_13.Note:new()
    v34:set_track(p33[1])
    v34:set_time_ms(p33[2])
    if #p33 ~= 3 then
        v34:set_type(v_u_13.NoteType.Single)
        return v34;
    end;
    v34:set_duration(p33[3])
    v34:set_type(v_u_13.NoteType.Hold)
    return v34;
end;
v_u_13.validate_note_data_list = function(_, p35, p36) --[[ Name: validate_note_data_list ]] --[[ Line: 130 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4, (copy 3): v_u_14, (copy 4): v_u_13 ]]
    if v_u_5:singleton():contains_key(p36) ~= true then
        return false, string.format("Invalid songkey(%s)", (tostring(p36)));
    end;
    local v37 = v_u_4:new()
    v37:add(v_u_14.Track1, v_u_13:get_earliest_allowed_note_time_ms())
    v37:add(v_u_14.Track2, v_u_13:get_earliest_allowed_note_time_ms())
    v37:add(v_u_14.Track3, v_u_13:get_earliest_allowed_note_time_ms())
    v37:add(v_u_14.Track4, v_u_13:get_earliest_allowed_note_time_ms())
    local v38 = v_u_13:get_earliest_allowed_note_time_ms()
    for v39 = 1, p35:count() do
        local v40 = p35:get(v39)
        local v41 = v40:get_time_ms()
        if v41 < v38 then
            return false, string.format("Note[%d] time(%d) is before last_time(%d)", v39, v41, v38);
        end;
        local v42 = v40:get_track()
        if v41 <= v37:get(v42) + 25 then
            return false, string.format("Note[%d] likely duplicate time/track note at time(%d) track(%d) last_time(%d)", v39, v41, v42, v37:get(v42));
        end;
        if v40:get_type() == v_u_13.NoteType.Hold then
            v37:add(v42, v41 + v40:get_duration())
            v38 = v41
        else
            v37:add(v42, v41)
            v38 = v41
        end;
    end;
    local v43 = v_u_5:singleton():songkey_get_approx_length_sec(p36) * 1000
    for v44, v45 in v37:key_itr() do
        if v43 + 2500 < v45 then
            return false, string.format("Track(%d) has note time(%d) that extends past song length(%d) ", v44, v45, v43 + 2500);
        end;
    end;
    return true, "";
end;
v_u_13.TimingPoint.new = function(_) --[[ Name: new ]] --[[ Line: 186 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v46 = {}
    local v_u_47 = 0
    local v_u_48 = 500
    v46.get_time_ms = function(_) --[[ Name: get_time_ms ]] --[[ Line: 192 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        return v_u_47;
    end;
    v46.set_time_ms = function(_, p49) --[[ Name: set_time_ms ]] --[[ Line: 193 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_47 ]]
        v_u_1:is_number(p49)
        v_u_47 = p49
    end;
    v46.get_beat_length_ms = function(_) --[[ Name: get_beat_length_ms ]] --[[ Line: 198 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        return v_u_48;
    end;
    v46.set_beat_length_ms = function(_, p50) --[[ Name: set_beat_length_ms ]] --[[ Line: 199 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_48 ]]
        v_u_1:is_number(p50)
        v_u_1:is_true(p50 > 0)
        v_u_48 = p50
    end;
    v46.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 205 ]]
        --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_48 ]]
        return {
            ["Time"] = v_u_47,
            ["BeatLength"] = v_u_48
        };
    end;
    return v46;
end;
v_u_13.TimingPoint.from_table = function(_, p51) --[[ Name: from_table ]] --[[ Line: 215 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    local v52 = v_u_13.TimingPoint:new()
    if typeof(p51.Time) == "number" then
        v52:set_time_ms(p51.Time)
    end;
    if typeof(p51.BeatLength) == "number" then
        v52:set_beat_length_ms(p51.BeatLength)
    end;
    return v52;
end;
v_u_13.TimingPoint.beat_length_ms_get_bpm = function(_, p53) --[[ Name: beat_length_ms_get_bpm ]] --[[ Line: 227 ]]
    return 60000 / p53;
end;
v_u_13.TimingPoint.bpm_get_beat_length_ms = function(_, p54) --[[ Name: bpm_get_beat_length_ms ]] --[[ Line: 232 ]]
    return 60000 / p54;
end;
v_u_13.TimingPoint.beat_length_ms_get_display_bgm = function(_, p55) --[[ Name: beat_length_ms_get_display_bgm ]] --[[ Line: 237 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    local v56 = v_u_13.TimingPoint:beat_length_ms_get_bpm(p55)
    if math.abs(math.floor(v56) - v56) < 0.01 then
        return string.format("%d", v56);
    else
        return string.format("%.2f", v56);
    end;
end;
v_u_13.TimingPoint.timing_point_get_display_bpm = function(_, p57) --[[ Name: timing_point_get_display_bpm ]] --[[ Line: 248 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13.TimingPoint:beat_length_ms_get_display_bgm((p57:get_beat_length_ms()));
end;
v_u_13.UndoState.new = function(_) --[[ Name: new ]] --[[ Line: 254 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_13 ]]
    local v58 = {}
    local v_u_59 = v_u_3:new()
    local v_u_60 = v_u_4:new()
    local v_u_61 = 0
    v58.get_loaded_note_data = function(_) --[[ Name: get_loaded_note_data ]] --[[ Line: 261 ]]
        --[[ Upvalues: (copy 1): v_u_59 ]]
        return v_u_59;
    end;
    v58.get_selected_note_index_set = function(_) --[[ Name: get_selected_note_index_set ]] --[[ Line: 262 ]]
        --[[ Upvalues: (copy 1): v_u_60 ]]
        return v_u_60;
    end;
    v58.get_display_time_ms = function(_) --[[ Name: get_display_time_ms ]] --[[ Line: 263 ]]
        --[[ Upvalues: (ref 1): v_u_61 ]]
        return v_u_61;
    end;
    v58.set_display_time_ms = function(_, p62) --[[ Name: set_display_time_ms ]] --[[ Line: 264 ]]
        --[[ Upvalues: (ref 1): v_u_61 ]]
        v_u_61 = p62
    end;
    v58.copy_current_editor_note_track_display_state = function(_, p63) --[[ Name: copy_current_editor_note_track_display_state ]] --[[ Line: 266 ]]
        --[[ Upvalues: (copy 1): v_u_59, (ref 2): v_u_13, (copy 3): v_u_60, (ref 4): v_u_61 ]]
        local v64 = p63:get_loaded_note_data()
        v_u_59:clear()
        for v65 = 1, v64:count() do
            v_u_59:push_back((v_u_13.Note:from_table(v64:get(v65):to_table())))
        end;
        v_u_60:clear()
        for v66, v67 in p63:get_selected_note_index_set():key_itr() do
            v_u_60:add(v66, v67)
        end;
        v_u_61 = p63:get_display_time_ms()
    end;
    v58.undo_state_has_any_changes_from_note_track_display_state = function(_, p68) --[[ Name: undo_state_has_any_changes_from_note_track_display_state ]] --[[ Line: 283 ]]
        --[[ Upvalues: (copy 1): v_u_59, (copy 2): v_u_60, (ref 3): v_u_4 ]]
        if v_u_59:count() ~= p68:get_loaded_note_data():count() then
            return true;
        end;
        if v_u_60:count() ~= p68:get_selected_note_index_set():count() then
            return true;
        end;
        if v_u_4:set_intersection(v_u_60, p68:get_selected_note_index_set()):count() ~= v_u_60:count() then
            return true;
        end;
        for v69 = 1, v_u_59:count() do
            local v70 = v_u_59:get(v69)
            local v71 = p68:get_loaded_note_data():get(v69)
            if v70:get_time_ms() ~= v71:get_time_ms() then
                return true;
            end;
            if v70:get_type() ~= v71:get_type() then
                return true;
            end;
            if v70:get_track() ~= v71:get_track() then
                return true;
            end;
            if v70:get_duration() ~= v71:get_duration() then
                return true;
            end;
        end;
        return false;
    end;
    v58.apply_undo_state_to_note_track_display = function(_, p72) --[[ Name: apply_undo_state_to_note_track_display ]] --[[ Line: 300 ]]
        --[[ Upvalues: (copy 1): v_u_59, (copy 2): v_u_60, (ref 3): v_u_61 ]]
        p72:get_loaded_note_data():clear()
        p72:get_selected_note_index_set():clear()
        for v73 = 1, v_u_59:count() do
            p72:get_loaded_note_data():push_back(v_u_59:get(v73))
        end;
        for v74, v75 in v_u_60:key_itr() do
            p72:get_selected_note_index_set():add(v74, v75)
        end;
        p72:set_display_time_ms(v_u_61)
    end;
    return v58;
end;
return v_u_13;
