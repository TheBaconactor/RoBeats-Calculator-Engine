-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.EventString)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.NoteHitMode)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = {
    ["Event"] = {}
}
v_u_8.Event.new = function(_, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_5, (copy 5): v_u_1 ]]
    local v18 = {}
    v_u_6:is_int(p_u_9)
    v_u_6:is_int(p_u_10)
    v_u_6:is_enum_member(p_u_11, v_u_2)
    v_u_6:is_number(p_u_12)
    v_u_6:is_bool(p_u_13)
    v_u_6:is_int_greater_than(p_u_14, 1, 4)
    v_u_6:is_enum_member(p_u_15, v_u_7)
    v_u_6:is_number(p_u_16)
    v_u_6:is_number(p_u_17)
    v18.get_time = function(_) --[[ Name: get_time ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): p_u_9 ]]
        return p_u_9;
    end;
    v18.get_note_index = function(_) --[[ Name: get_note_index ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): p_u_10 ]]
        return p_u_10;
    end;
    v18.get_note_result = function(_) --[[ Name: get_note_result ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): p_u_11 ]]
        return p_u_11;
    end;
    v18.get_hit_time_offset = function(_) --[[ Name: get_hit_time_offset ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): p_u_12 ]]
        return p_u_12;
    end;
    v18.get_is_fever = function(_) --[[ Name: get_is_fever ]] --[[ Line: 32 ]]
        --[[ Upvalues: (ref 1): p_u_13 ]]
        return p_u_13;
    end;
    v18.get_track_index = function(_) --[[ Name: get_track_index ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): p_u_14 ]]
        return p_u_14;
    end;
    v18.get_note_hit_mode = function(_) --[[ Name: get_note_hit_mode ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): p_u_15 ]]
        return p_u_15;
    end;
    v18.get_fever_pct = function(_) --[[ Name: get_fever_pct ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): p_u_16 ]]
        return p_u_16;
    end;
    v18.get_accuracy = function(_) --[[ Name: get_accuracy ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): p_u_17 ]]
        return p_u_17;
    end;
    v18.set_is_fever = function(_, p19) --[[ Name: set_is_fever ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): p_u_13 ]]
        p_u_13 = p19
    end;
    v18.set_fever_pct = function(_, p20) --[[ Name: set_fever_pct ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): p_u_16 ]]
        p_u_16 = p20
    end;
    v18.set_time = function(_, p21) --[[ Name: set_time ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_9 ]]
        v_u_6:is_int(p21)
        p_u_9 = p21
    end;
    v18.set_note_hit_mode = function(_, p22) --[[ Name: set_note_hit_mode ]] --[[ Line: 45 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): p_u_15 ]]
        v_u_6:is_enum_member(p22, v_u_7)
        p_u_15 = p22
    end;
    v18.serialize_to_table = function(_, p23) --[[ Name: serialize_to_table ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_9, (copy 3): p_u_10, (copy 4): p_u_11, (copy 5): p_u_12, (ref 6): p_u_13, (copy 7): p_u_14, (ref 8): p_u_15, (ref 9): p_u_16, (copy 10): p_u_17 ]]
        local v24 = {
            [v_u_5.ES_NOTESEQ_TIME] = p_u_9,
            [v_u_5.ES_NOTESEQ_NOTEINDEX] = p_u_10,
            [v_u_5.ES_NOTESEQ_NOTERESULT] = p_u_11,
            [v_u_5.ES_NOTESEQ_HITTIMEOFFSET] = p_u_12,
            [v_u_5.ES_NOTESEQ_ISFEVER] = p_u_13,
            [v_u_5.ES_NOTESEQ_TRACKINDEX] = p_u_14,
            [v_u_5.ES_NOTESEQ_NOTE_HIT_MODE] = p_u_15,
            [v_u_5.ES_NOTESEQ_FEVER_PCT] = p_u_16,
            [v_u_5.ES_NOTESEQ_ACCURACY] = p_u_17
        }
        if p23 then
            return v_u_5:es_table_convert(v24, false);
        else
            return v24;
        end;
    end;
    v18.debug_str = function(_) --[[ Name: debug_str ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): p_u_9, (copy 2): p_u_10, (ref 3): v_u_1, (copy 4): p_u_11, (ref 5): v_u_2, (copy 6): p_u_12, (ref 7): p_u_13, (copy 8): p_u_14, (ref 9): p_u_15, (ref 10): v_u_7 ]]
        return string.format("Event Time(%d) NoteIndex(%d) NoteResult(%s)(%s) HitTimeOffset(%.2f) Fever(%s) TrackIndex(%d) NoteHitMode(%s)", p_u_9, p_u_10, v_u_1:enum_val_to_name(p_u_11, v_u_2), tostring(p_u_11), p_u_12, tostring(p_u_13), p_u_14, v_u_1:enum_val_to_name(p_u_15, v_u_7));
    end;
    return v18;
end;
v_u_8.Event.deserialize_from_table = function(_, p25, p26) --[[ Name: deserialize_from_table ]] --[[ Line: 85 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_8 ]]
    if p26 == true then
        p25 = v_u_5:es_table_deconvert(p25)
    end;
    return v_u_8.Event:new(p25[v_u_5.ES_NOTESEQ_TIME], p25[v_u_5.ES_NOTESEQ_NOTEINDEX], p25[v_u_5.ES_NOTESEQ_NOTERESULT], p25[v_u_5.ES_NOTESEQ_HITTIMEOFFSET], p25[v_u_5.ES_NOTESEQ_ISFEVER], p25[v_u_5.ES_NOTESEQ_TRACKINDEX], p25[v_u_5.ES_NOTESEQ_NOTE_HIT_MODE], p25[v_u_5.ES_NOTESEQ_FEVER_PCT], p25[v_u_5.ES_NOTESEQ_ACCURACY]);
end;
v_u_8.new = function(_) --[[ Name: new ]] --[[ Line: 100 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6, (copy 3): v_u_8, (copy 4): v_u_4, (copy 5): v_u_5 ]]
    local v27 = {}
    local v_u_28 = v_u_3:new()
    local v_u_29 = 0
    local v_u_30 = 0
    local v_u_31 = 0
    local v_u_32 = 0
    local v_u_33 = 0
    local v_u_34 = 0
    v27.get_events = function(_) --[[ Name: get_events ]] --[[ Line: 111 ]]
        --[[ Upvalues: (copy 1): v_u_28 ]]
        return v_u_28;
    end;
    v27.get_time_start = function(_) --[[ Name: get_time_start ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v27.set_time_start = function(_, p35) --[[ Name: set_time_start ]] --[[ Line: 113 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_29 ]]
        v_u_6:is_int(p35)
        v_u_29 = p35
    end;
    v27.get_time_end = function(_) --[[ Name: get_time_end ]] --[[ Line: 114 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    v27.set_time_end = function(_, p36) --[[ Name: set_time_end ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_30 ]]
        v_u_6:is_int(p36)
        v_u_30 = p36
    end;
    v27.get_score_start = function(_) --[[ Name: get_score_start ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v27.set_score_start = function(_, p37) --[[ Name: set_score_start ]] --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_31 ]]
        v_u_6:is_int_greater_than(p37, -1)
        v_u_31 = p37
    end;
    v27.get_score_end = function(_) --[[ Name: get_score_end ]] --[[ Line: 118 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32;
    end;
    v27.set_score_end = function(_, p38) --[[ Name: set_score_end ]] --[[ Line: 119 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_32 ]]
        v_u_6:is_int_greater_than(p38, -1)
        v_u_32 = p38
    end;
    v27.get_combo_start = function(_) --[[ Name: get_combo_start ]] --[[ Line: 120 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end;
    v27.set_combo_start = function(_, p39) --[[ Name: set_combo_start ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_33 ]]
        v_u_6:is_int_greater_than(p39, -1)
        v_u_33 = p39
    end;
    v27.get_combo_end = function(_) --[[ Name: get_combo_end ]] --[[ Line: 122 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34;
    end;
    v27.set_combo_end = function(_, p40) --[[ Name: set_combo_end ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_34 ]]
        v_u_6:is_int_greater_than(p40, -1)
        v_u_34 = p40
    end;
    v27.add_note_event = function(_, p41, p42, p43, p44, p45, p46, p47, p48, p49) --[[ Name: add_note_event ]] --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_28 ]]
        local v50 = v_u_8.Event:new(p41, p42, p43, p44, p45, p46, p47, p48, p49)
        v_u_28:push_back(v50)
        return v50;
    end;
    local v_u_51 = v_u_4:new()
    v27.clear_events = function(_) --[[ Name: clear_events ]] --[[ Line: 132 ]]
        --[[ Upvalues: (copy 1): v_u_28, (copy 2): v_u_51 ]]
        v_u_28:clear()
        v_u_51:clear()
    end;
    v27.serialize_to_table = function(_, p52) --[[ Name: serialize_to_table ]] --[[ Line: 137 ]]
        --[[ Upvalues: (copy 1): v_u_28, (ref 2): v_u_5, (ref 3): v_u_29, (ref 4): v_u_30, (ref 5): v_u_31, (ref 6): v_u_32, (ref 7): v_u_33, (ref 8): v_u_34 ]]
        if p52 ~= true then
            p52 = false
        end;
        local v53 = {}
        for v54 = 1, v_u_28:count() do
            v53[#v53 + 1] = v_u_28:get(v54):serialize_to_table(p52)
        end;
        local v55 = {
            [v_u_5.ES_NOTESEQ_EVENTS] = v53,
            [v_u_5.ES_NOTESEQ_TIMESTART] = v_u_29,
            [v_u_5.ES_NOTESEQ_TIMEEND] = v_u_30,
            [v_u_5.ES_NOTESEQ_SCORESTART] = v_u_31,
            [v_u_5.ES_NOTESEQ_SCOREEND] = v_u_32,
            [v_u_5.ES_NOTESEQ_COMBOSTART] = v_u_33,
            [v_u_5.ES_NOTESEQ_COMBOEND] = v_u_34
        }
        if p52 then
            return v_u_5:es_table_convert(v55, false);
        else
            return v55;
        end;
    end;
    v27.load_events_from_table = function(_, p56, p57) --[[ Name: load_events_from_table ]] --[[ Line: 159 ]]
        --[[ Upvalues: (copy 1): v_u_28, (ref 2): v_u_8 ]]
        for v58 = 1, #p56 do
            v_u_28:push_back(v_u_8.Event:deserialize_from_table(p56[v58], p57))
        end;
    end;
    v27.debug_str = function(_, p59) --[[ Name: debug_str ]] --[[ Line: 165 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_33, (ref 6): v_u_34, (copy 7): v_u_28 ]]
        local v60 = string.format("NotePlaybackSequence(Time(%d,%d) Score(%d,%d) Combo(%d,%d)) Notes(%d)", v_u_29, v_u_30, v_u_31, v_u_32, v_u_33, v_u_34, v_u_28:count())
        if p59 ~= true then
            for v61 = 1, v_u_28:count() do
                v60 = v60 .. "\n\t" .. v_u_28:get(v61):debug_str()
            end;
        end;
        return v60;
    end;
    v27.append_notesequence = function(p62, p63) --[[ Name: append_notesequence ]] --[[ Line: 184 ]]
        --[[ Upvalues: (copy 1): v_u_51, (copy 2): v_u_28 ]]
        local v64 = p63:get_events()
        for v65 = 1, v64:count() do
            local v66 = v64:get(v65)
            local v67 = v66:debug_str()
            if v_u_51:contains(v67) ~= true then
                v_u_28:push_back(v66)
                v_u_51:add(v67, true)
            end;
        end;
        p62:set_time_end(p63:get_time_end())
        p62:set_score_end(p63:get_score_end())
        p62:set_combo_end(p63:get_combo_end())
    end;
    return v27;
end;
v_u_8.deserialize_from_table = function(_, p68, p69) --[[ Name: deserialize_from_table ]] --[[ Line: 206 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_8 ]]
    if p69 == true then
        p68 = v_u_5:es_table_deconvert(p68)
    end;
    local v70 = v_u_8:new()
    v70:set_time_start(p68[v_u_5.ES_NOTESEQ_TIMESTART])
    v70:set_time_end(p68[v_u_5.ES_NOTESEQ_TIMEEND])
    v70:set_score_start(p68[v_u_5.ES_NOTESEQ_SCORESTART])
    v70:set_score_end(p68[v_u_5.ES_NOTESEQ_SCOREEND])
    v70:set_combo_start(p68[v_u_5.ES_NOTESEQ_COMBOSTART])
    v70:set_combo_end(p68[v_u_5.ES_NOTESEQ_COMBOEND])
    v70:load_events_from_table(p68[v_u_5.ES_NOTESEQ_EVENTS], p69)
    return v70;
end;
return v_u_8;
