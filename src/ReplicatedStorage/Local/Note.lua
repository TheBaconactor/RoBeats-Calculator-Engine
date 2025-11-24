-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Local.NoteBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Effects.HoldingNoteEffect)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_7 = require(game.ReplicatedStorage.Shared.NoteHitMode)
require(game.ReplicatedStorage.Effects.TriggerNoteEffect)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.LVector3)
require(game.ReplicatedStorage.Shared.LCFrame)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_8 = require(game.ReplicatedStorage.Local.Adorn.NoteAdornRender)
local v_u_9 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_10 = require(game.ReplicatedStorage.Local.NoteDecal.NoteDecalRender)
local v_u_11 = {
    ["State"] = {
        ["Pre"] = 0,
        ["DoRemove"] = 1
    }
}
v_u_11.new = function(_, p12, p13, p14, p15, p16, p17) --[[ Name: new ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    local v18 = p12._lua_pool:depool("Note")
    if v18 == nil then
        local v19 = v_u_11:_new(p12, p13, p14, p15, p16, p17)
        v19:cons()
        return v19;
    else
        v18:rebind(p12, p13, p14, p15, p16, p17)
        v18:cons()
        return v18;
    end;
end;
v_u_11.prepool = function(_, p20) --[[ Name: prepool ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_8, (copy 3): v_u_10 ]]
    p20._lua_pool:repool("Note", v_u_11:_new())
    v_u_8:prepool(p20)
    v_u_10:prepool(p20)
end;
v_u_11._new = function(_, p_u_21, p_u_22, p_u_23, p_u_24, p_u_25, p_u_26) --[[ Name: _new ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_11, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_8, (copy 6): v_u_9, (copy 7): v_u_10, (copy 8): v_u_1, (copy 9): v_u_3, (copy 10): v_u_7, (copy 11): v_u_4 ]]
    local v27 = v_u_2:NoteBase(p_u_26)
    v27.rebind = function(p28, p29, p30, p31, p32, p33, p34) --[[ Name: rebind ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_22, (ref 3): p_u_23, (ref 4): p_u_24, (ref 5): p_u_25, (ref 6): p_u_26 ]]
        p_u_21 = p29
        p_u_22 = p30
        p_u_23 = p31
        p_u_24 = p32
        p_u_25 = p33
        p_u_26 = p34
        p28:set_note_index(p_u_26)
    end;
    local l_Pre_0 = v_u_11.State.Pre
    local v_u_35 = 0
    local v_u_36 = nil
    v27.get_track = function(_) --[[ Name: get_track ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36;
    end;
    local v_u_37 = nil
    v27.get_slot_player = function(_) --[[ Name: get_slot_player ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37;
    end;
    local v_u_38 = 0
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = nil
    v27.cons = function(p43) --[[ Name: cons ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): l_Pre_0, (ref 2): v_u_11, (ref 3): v_u_35, (ref 4): v_u_36, (ref 5): v_u_37, (ref 6): v_u_38, (ref 7): p_u_21, (ref 8): p_u_23, (ref 9): v_u_5, (ref 10): v_u_6, (ref 11): v_u_39, (ref 12): p_u_22, (ref 13): v_u_40, (ref 14): v_u_8, (ref 15): p_u_24, (ref 16): p_u_25, (ref 17): p_u_26 ]]
        p43:reset_note_colors()
        l_Pre_0 = v_u_11.State.Pre
        v_u_35 = 0
        v_u_36 = nil
        v_u_37 = nil
        v_u_38 = 0
        local v44 = p_u_21:es_gamelocal_get_tracksystems():get(p_u_23)
        local v45
        if v44 then
            v45 = v44:get_statsdict()
        else
            v_u_5:warnf("Creating note for unknown slot(%d)", p_u_23)
            v45 = v_u_6:get_imm_statsdict_base()
        end;
        v_u_39 = v_u_6:get_note_time_obj(v45)
        v_u_36 = p_u_21:es_gamelocal_tracksystem_of_index(p_u_23):es_get_track(p_u_22)
        v_u_37 = p_u_21._players._slots:get(p_u_23)
        v_u_35 = 0
        v_u_40 = v_u_8:new(p_u_21, p_u_22, p_u_23, p_u_24, p_u_25, p_u_26, p43)
        p43:update_note_display_mode()
        p43:update_visual(0)
    end;
    v27.update_note_display_mode = function(p46) --[[ Name: update_note_display_mode ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_23, (ref 3): v_u_42, (ref 4): v_u_9, (ref 5): v_u_41, (ref 6): v_u_10, (ref 7): p_u_22, (ref 8): p_u_24, (ref 9): p_u_25, (ref 10): p_u_26, (ref 11): v_u_40 ]]
        local v47 = p_u_21:es_gamelocal_get_tracksystems():get(p_u_23)
        if v47 then
            v_u_42 = v47:get_active_note_display_mode()
            if v_u_42 == v_u_9.DecalUp or v_u_42 == v_u_9.DecalDown then
                if v_u_41 == nil then
                    v_u_41 = v_u_10:new(p_u_21, p_u_22, p_u_23, p_u_24, p_u_25, p_u_26, p46)
                end;
                v_u_40:set_visible(false)
                v_u_41:set_visible(true)
                return;
            end;
            v_u_40:set_visible(true)
            if v_u_41 then
                v_u_41:set_visible(false)
            end;
        end;
    end;
    v27.get_head_t = function(_) --[[ Name: get_head_t ]] --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v27.update_visual = function(_, p48) --[[ Name: update_visual ]] --[[ Line: 129 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_41 ]]
        v_u_40:update_visual(p48)
        if v_u_41 then
            v_u_41:update_visual(p48)
        end;
    end;
    v27.update = function(p49, p50, _) --[[ Name: update ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): l_Pre_0, (ref 3): v_u_11, (ref 4): p_u_21, (ref 5): v_u_35, (ref 6): p_u_24, (ref 7): p_u_25, (ref 8): p_u_23, (ref 9): v_u_38, (ref 10): v_u_3, (ref 11): p_u_22, (ref 12): v_u_7, (ref 13): p_u_26 ]]
        v_u_1:profilebegin("Note:update")
        if l_Pre_0 == v_u_11.State.Pre then
            v_u_35 = (p_u_21:es_gamelocal_get_audiomanager():get_current_time_ms() - p_u_24) / (p_u_25 - p_u_24)
            if p_u_23 == p_u_21:get_local_game_slot() then
                p49:update_visual(p50)
            else
                v_u_38 = v_u_38 + p50
                if p_u_21:get_frame_count() % 4 == (p_u_23 - 1) % 4 then
                    p49:update_visual(p50)
                    v_u_38 = 0
                end;
            end;
            if p49:should_remove(p_u_21) then
                p_u_21:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_21, v_u_3.NoteResult_Miss, p_u_23, p_u_22, {
                    ["PlaySFX"] = false,
                    ["PlayHoldEffect"] = false,
                    ["TimeMiss"] = true,
                    ["HitTime"] = p_u_25,
                    ["Type"] = 1,
                    [v_u_7.ParamNoteHitMode] = v_u_7.NoteTimeMiss,
                    [v_u_7.ParamNoteIndex] = p_u_26
                })
            end;
        end;
        v_u_1:profileend()
    end;
    v27.should_remove = function(p51, _) --[[ Name: should_remove ]] --[[ Line: 173 ]]
        --[[ Upvalues: (ref 1): l_Pre_0, (ref 2): v_u_11, (ref 3): v_u_4 ]]
        return l_Pre_0 == v_u_11.State.DoRemove and true or p51:get_time_to_end() < v_u_4.NOTE_REMOVE_TIME;
    end;
    v27.do_remove = function(p52, _) --[[ Name: do_remove ]] --[[ Line: 177 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_41, (ref 3): p_u_21 ]]
        v_u_40:cleanup()
        v_u_40 = nil
        if v_u_41 then
            v_u_41:cleanup()
            v_u_41 = nil
        end;
        p_u_21._lua_pool:repool("Note", p52)
    end;
    v27.get_delta_time_from_hit_time = function(_) --[[ Name: get_delta_time_from_hit_time ]] --[[ Line: 187 ]]
        --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_25 ]]
        return p_u_21:es_gamelocal_get_audiomanager():get_current_time_ms() - p_u_25;
    end;
    v27.es_note_test_hit = function(p53, _, p54) --[[ Name: es_note_test_hit ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_39, (ref 3): v_u_3 ]]
        local v55 = p53:get_delta_time_from_hit_time() + (p54 == nil and 0 or p54)
        local v56 = v_u_1:timedelta_to_result_obj(v55, v_u_39)
        if v56 == v_u_3.NoteResult_Miss then
            return false, v56, v55;
        else
            return true, v56, v55;
        end;
    end;
    v27.es_note_on_hit = function(_, _, p57, _, p58) --[[ Name: es_note_on_hit ]] --[[ Line: 203 ]]
        --[[ Upvalues: (ref 1): v_u_40, (ref 2): v_u_41, (ref 3): p_u_21, (ref 4): p_u_23, (ref 5): p_u_22, (ref 6): p_u_25, (ref 7): v_u_7, (ref 8): p_u_26, (ref 9): l_Pre_0, (ref 10): v_u_11 ]]
        v_u_40:note_on_hit(p57)
        if v_u_41 then
            v_u_41:note_on_hit(p57)
        end;
        p_u_21:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_21, p57, p_u_23, p_u_22, {
            ["PlaySFX"] = true,
            ["PlayHoldEffect"] = false,
            ["HitTime"] = p_u_25,
            ["Delta"] = p58,
            ["Type"] = 1,
            [v_u_7.ParamNoteHitMode] = v_u_7.NoteHit,
            [v_u_7.ParamNoteIndex] = p_u_26
        })
        l_Pre_0 = v_u_11.State.DoRemove
    end;
    v27.get_state = function(_) --[[ Name: get_state ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): l_Pre_0 ]]
        return l_Pre_0;
    end;
    v27.es_note_test_release = function(_, _, _) --[[ Name: es_note_test_release ]] --[[ Line: 228 ]]
        --[[ Upvalues: (ref 1): v_u_3 ]]
        return false, v_u_3.NoteResult_Miss;
    end;
    v27.es_note_on_release = function(_, _, _, _, _) end;
    v27.get_track_index = function(_) --[[ Name: get_track_index ]] --[[ Line: 233 ]]
        --[[ Upvalues: (ref 1): p_u_22 ]]
        return p_u_22;
    end;
    v27.get_time_to_end = function(_) --[[ Name: get_time_to_end ]] --[[ Line: 237 ]]
        --[[ Upvalues: (ref 1): p_u_25, (ref 2): p_u_24, (ref 3): v_u_35 ]]
        return (p_u_25 - p_u_24) * (1 - v_u_35);
    end;
    return v27;
end;
return v_u_11;
