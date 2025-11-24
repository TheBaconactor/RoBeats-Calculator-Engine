-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:25 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Local.NoteBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_5 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Effects.TriggerNoteEffect)
require(game.ReplicatedStorage.Effects.HoldingNoteEffect)
local v_u_6 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_7 = require(game.ReplicatedStorage.Shared.NoteHitMode)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_9 = require(game.ReplicatedStorage.Local.Adorn.HeldNoteAdornRender)
local v_u_10 = require(game.ReplicatedStorage.Local.NoteDecal.HeldNoteDecalRender)
local v11 = require(game.ReplicatedStorage.Local.HeldNoteState)
local v_u_12 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_13 = {
    ["State"] = v11
}
v_u_13.new = function(_, p14, p15, p16, p17, p18, p19, p20, p21) --[[ Name: new ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    local v22 = p14._lua_pool:depool("HeldNote")
    if v22 == nil then
        local v23 = v_u_13:_new(p14, p15, p16, p17, p18, p19, p20, p21)
        v23:cons()
        return v23;
    else
        v22:rebind(p14, p15, p16, p17, p18, p19, p20, p21)
        v22:cons()
        return v22;
    end;
end;
v_u_13.prepool = function(_, p24) --[[ Name: prepool ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_9, (copy 3): v_u_10 ]]
    p24._lua_pool:repool("HeldNote", v_u_13:_new())
    v_u_9:prepool(p24)
    v_u_10:prepool(p24)
end;
v_u_13._new = function(_, p_u_25, p_u_26, p_u_27, p_u_28, p_u_29, p_u_30, p_u_31, p_u_32) --[[ Name: _new ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_13, (copy 3): v_u_8, (copy 4): v_u_4, (copy 5): v_u_6, (copy 6): v_u_7, (copy 7): v_u_9, (copy 8): v_u_12, (copy 9): v_u_10, (copy 10): v_u_1, (copy 11): v_u_5, (copy 12): v_u_3 ]]
    local v33 = v_u_2:NoteBase(p_u_32)
    v33.rebind = function(p34, p35, p36, p37, p38, p39, p40, p41, p42) --[[ Name: rebind ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): p_u_25, (ref 2): p_u_26, (ref 3): p_u_27, (ref 4): p_u_28, (ref 5): p_u_29, (ref 6): p_u_30, (ref 7): p_u_31, (ref 8): p_u_32 ]]
        p_u_25 = p35
        p_u_26 = p36
        p_u_27 = p37
        p_u_28 = p38
        p_u_29 = p39
        p_u_30 = p40
        p_u_31 = p41
        p_u_32 = p42
        p34:set_note_index(p_u_32)
    end;
    local v_u_43 = 0
    local v_u_44 = nil
    local v_u_45 = nil
    local l_Pre_0 = v_u_13.State.Pre
    v33.get_state = function(_) --[[ Name: get_state ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): l_Pre_0 ]]
        return l_Pre_0;
    end;
    local v_u_46 = false
    v33.did_trigger_head = function(_) --[[ Name: did_trigger_head ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_46 ]]
        return v_u_46;
    end;
    local v_u_47 = false
    v33.did_trigger_tail = function(_) --[[ Name: did_trigger_tail ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        return v_u_47;
    end;
    local v_u_48 = 0
    local v_u_49 = false
    local v_u_50 = nil
    local v_u_51 = nil
    local v_u_52 = nil
    local v_u_53 = false
    v33.cons = function(p54) --[[ Name: cons ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): l_Pre_0, (ref 3): v_u_13, (ref 4): v_u_46, (ref 5): v_u_47, (ref 6): v_u_48, (ref 7): v_u_49, (ref 8): v_u_53, (ref 9): p_u_25, (ref 10): v_u_8, (ref 11): p_u_27, (ref 12): v_u_4, (ref 13): v_u_6, (ref 14): v_u_44, (ref 15): v_u_45, (ref 16): v_u_7, (ref 17): v_u_50, (ref 18): v_u_9, (ref 19): p_u_26, (ref 20): p_u_28, (ref 21): p_u_29, (ref 22): p_u_30, (ref 23): p_u_31, (ref 24): p_u_32 ]]
        p54:reset_note_colors()
        v_u_43 = 0
        l_Pre_0 = v_u_13.State.Pre
        v_u_46 = false
        v_u_47 = false
        v_u_48 = 0
        v_u_49 = false
        v_u_53 = p_u_25._player_settings_manager:get_key(v_u_8.Key.ShowHeldNoteTail) == true
        local v55 = p_u_25:es_gamelocal_get_tracksystems():get(p_u_27)
        local v56
        if v55 then
            v56 = v55:get_statsdict()
        else
            v_u_4:warnf("Creating note for unknown slot(%d)", p_u_27)
            v56 = v_u_6:get_imm_statsdict_base()
        end;
        v_u_44 = v_u_6:get_note_time_obj(v56)
        v_u_45 = v_u_6:get_note_time_obj(v56, v_u_6:note_hit_mode_get_time_multiplier(v_u_7.HeldHitTail))
        v_u_43 = p_u_25:es_gamelocal_get_audiomanager():get_current_time_ms()
        l_Pre_0 = v_u_13.State.Pre
        v_u_50 = v_u_9:new(p_u_25, p_u_26, p_u_27, p_u_28, p_u_29, p_u_30, p_u_31, p_u_32, p54)
        p54:update_note_display_mode()
        p54:update_visual(1)
    end;
    v33.update_note_display_mode = function(p57) --[[ Name: update_note_display_mode ]] --[[ Line: 111 ]]
        --[[ Upvalues: (ref 1): p_u_25, (ref 2): p_u_27, (ref 3): v_u_52, (ref 4): v_u_12, (ref 5): v_u_51, (ref 6): v_u_10, (ref 7): p_u_26, (ref 8): p_u_28, (ref 9): p_u_29, (ref 10): p_u_32, (ref 11): v_u_50 ]]
        local v58 = p_u_25:es_gamelocal_get_tracksystems():get(p_u_27)
        if v58 then
            v_u_52 = v58:get_active_note_display_mode()
            if v_u_52 == v_u_12.DecalUp or v_u_52 == v_u_12.DecalDown then
                if v_u_51 == nil then
                    v_u_51 = v_u_10:new(p_u_25, p_u_26, p_u_27, p_u_28, p_u_29, p_u_32, p57)
                end;
                v_u_50:set_visible(false)
                v_u_51:set_visible(true)
                return;
            end;
            v_u_50:set_visible(true)
            if v_u_51 then
                v_u_51:set_visible(false)
            end;
        end;
    end;
    v33.update_visual = function(_, p59) --[[ Name: update_visual ]] --[[ Line: 130 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_51 ]]
        v_u_50:update_visual(p59)
        if v_u_51 then
            v_u_51:update_visual(p59)
        end;
    end;
    v33.get_tail_hit_time = function(_) --[[ Name: get_tail_hit_time ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): p_u_29, (ref 2): p_u_30 ]]
        return p_u_29 + p_u_30;
    end;
    v33.is_tail_active = function(p60) --[[ Name: is_tail_active ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): p_u_31 ]]
        return p60:get_tail_hit_time() <= v_u_43 + p_u_31;
    end;
    v33.tail_visible = function(p61) --[[ Name: tail_visible ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_53, (ref 2): l_Pre_0, (ref 3): v_u_13 ]]
        local v62 = p61:is_tail_active()
        if v_u_53 then
            return v62;
        end;
        if v62 then
            v62 = l_Pre_0 == v_u_13.State.HoldMissedActive
        end;
        return v62;
    end;
    v33.get_head_t = function(_) --[[ Name: get_head_t ]] --[[ Line: 152 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): p_u_28, (ref 3): p_u_29 ]]
        return (v_u_43 - p_u_28) / (p_u_29 - p_u_28);
    end;
    v33.get_tail_t = function(p63) --[[ Name: get_tail_t ]] --[[ Line: 156 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): p_u_31 ]]
        return (v_u_43 - p63:get_tail_hit_time() + p_u_31) / p_u_31;
    end;
    v33.update = function(p64, p65, _) --[[ Name: update ]] --[[ Line: 161 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_43, (ref 3): p_u_25, (ref 4): p_u_27, (ref 5): v_u_48, (ref 6): v_u_49, (ref 7): p_u_29, (ref 8): l_Pre_0, (ref 9): v_u_13, (ref 10): v_u_5, (ref 11): v_u_3, (ref 12): p_u_26, (ref 13): v_u_7, (ref 14): p_u_32, (ref 15): v_u_50, (ref 16): v_u_51 ]]
        v_u_1:profilebegin("HeldNote:update")
        v_u_43 = p_u_25:es_gamelocal_get_audiomanager():get_current_time_ms()
        v_u_1:profilebegin("HeldNote:visual_update")
        if p_u_27 == p_u_25:get_local_game_slot() then
            p64:update_visual(p65)
        else
            v_u_48 = v_u_48 + p65
            if p_u_25:get_frame_count() % 4 == (p_u_27 - 1) % 4 then
                p64:update_visual(v_u_48)
                v_u_48 = 0
            end;
        end;
        v_u_1:profileend()
        if v_u_49 == false and p_u_29 < v_u_43 then
            p_u_25:es_gamelocal_get_audiomanager():notify_held_note_begin(p_u_29)
            v_u_49 = true
        end;
        if l_Pre_0 == v_u_13.State.Pre then
            if v_u_43 > p_u_29 - v_u_5.NOTE_REMOVE_TIME then
                p_u_25:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_25, v_u_3.NoteResult_Miss, p_u_27, p_u_26, {
                    ["PlaySFX"] = false,
                    ["PlayHoldEffect"] = false,
                    ["TimeMiss"] = true,
                    ["HitTime"] = p_u_29,
                    ["Type"] = 21,
                    [v_u_7.ParamNoteHitMode] = v_u_7.HeldTimeMissHead,
                    [v_u_7.ParamNoteIndex] = p_u_32
                })
                l_Pre_0 = v_u_13.State.HoldMissedActive
            end;
        elseif (l_Pre_0 == v_u_13.State.Holding or (l_Pre_0 == v_u_13.State.HoldMissedActive or l_Pre_0 == v_u_13.State.Passed)) and v_u_43 > p64:get_tail_hit_time() - v_u_5.NOTE_REMOVE_TIME then
            if l_Pre_0 == v_u_13.State.Holding or l_Pre_0 == v_u_13.State.HoldMissedActive then
                p_u_25:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_25, v_u_3.NoteResult_Miss, p_u_27, p_u_26, {
                    ["PlaySFX"] = false,
                    ["PlayHoldEffect"] = false,
                    ["TimeMiss"] = true,
                    ["HitTime"] = p64:get_tail_hit_time(),
                    ["Type"] = 22,
                    [v_u_7.ParamNoteHitMode] = v_u_7.HeldTimeMissTail,
                    [v_u_7.ParamNoteIndex] = p_u_32
                })
            end;
            l_Pre_0 = v_u_13.State.DoRemove
        end;
        v_u_50:update(p65)
        if v_u_51 then
            v_u_51:update(p65)
        end;
        v_u_1:profileend()
    end;
    v33.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 239 ]]
        --[[ Upvalues: (ref 1): l_Pre_0, (ref 2): v_u_13 ]]
        return l_Pre_0 == v_u_13.State.DoRemove;
    end;
    v33.do_remove = function(p66, _) --[[ Name: do_remove ]] --[[ Line: 243 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_51, (ref 3): p_u_25 ]]
        v_u_50:cleanup()
        v_u_50 = nil
        if v_u_51 then
            v_u_51:cleanup()
            v_u_51 = nil
        end;
        p_u_25._lua_pool:repool("HeldNote", p66)
    end;
    v33.get_delta_time_from_hit_time = function(p67) --[[ Name: get_delta_time_from_hit_time ]] --[[ Line: 253 ]]
        --[[ Upvalues: (ref 1): l_Pre_0, (ref 2): v_u_13, (ref 3): v_u_43, (ref 4): p_u_29 ]]
        if l_Pre_0 == v_u_13.State.Pre then
            return v_u_43 - p_u_29;
        else
            return l_Pre_0 ~= v_u_13.State.HoldMissedActive and 0 or v_u_43 - p67:get_tail_hit_time();
        end;
    end;
    v33.es_note_test_hit = function(p68, _, p69) --[[ Name: es_note_test_hit ]] --[[ Line: 262 ]]
        --[[ Upvalues: (ref 1): l_Pre_0, (ref 2): v_u_13, (ref 3): v_u_1, (ref 4): v_u_44, (ref 5): v_u_3 ]]
        local v70 = p69 == nil and 0 or p69
        if l_Pre_0 == v_u_13.State.Pre then
            local v71 = p68:get_delta_time_from_hit_time() + v70
            local v72 = v_u_1:timedelta_to_result_obj(v71, v_u_44)
            if v72 == v_u_3.NoteResult_Miss then
                return false, v72, v71;
            else
                return true, v72, v71;
            end;
        elseif l_Pre_0 == v_u_13.State.HoldMissedActive then
            local v73 = p68:get_delta_time_from_hit_time() + v70
            local v74 = v_u_1:timedelta_to_result_obj(v73, v_u_44)
            if v74 == v_u_3.NoteResult_Miss then
                return false, v74, v73;
            else
                return true, v74, v73;
            end;
        else
            return false, v_u_3.NoteResult_Miss, 0;
        end;
    end;
    v33.es_note_on_hit = function(p75, _, p76, _, p77) --[[ Name: es_note_on_hit ]] --[[ Line: 289 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_51, (ref 3): l_Pre_0, (ref 4): v_u_13, (ref 5): p_u_25, (ref 6): p_u_27, (ref 7): p_u_26, (ref 8): p_u_29, (ref 9): v_u_7, (ref 10): p_u_32, (ref 11): v_u_46, (ref 12): v_u_47 ]]
        v_u_50:note_on_hit(p76)
        if v_u_51 then
            v_u_51:note_on_hit(p76)
        end;
        if l_Pre_0 == v_u_13.State.Pre then
            p_u_25:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_25, p76, p_u_27, p_u_26, {
                ["PlaySFX"] = true,
                ["PlayHoldEffect"] = false,
                ["IsHeldNoteBegin"] = true,
                ["HitTime"] = p_u_29,
                ["Delta"] = p77,
                ["Type"] = 23,
                [v_u_7.ParamNoteHitMode] = v_u_7.HeldHitHead,
                [v_u_7.ParamNoteIndex] = p_u_32
            })
            v_u_46 = true
            l_Pre_0 = v_u_13.State.Holding
        elseif l_Pre_0 == v_u_13.State.HoldMissedActive then
            p_u_25:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_25, p76, p_u_27, p_u_26, {
                ["PlaySFX"] = true,
                ["PlayHoldEffect"] = false,
                ["HitTime"] = p75:get_tail_hit_time(),
                ["Delta"] = p77,
                ["Type"] = 24,
                [v_u_7.ParamNoteHitMode] = v_u_7.HeldMissHeadHitTail,
                [v_u_7.ParamNoteIndex] = p_u_32
            })
            v_u_47 = true
            l_Pre_0 = v_u_13.State.Passed
        end;
    end;
    v33.get_delta_time_from_release_time = function(p78) --[[ Name: get_delta_time_from_release_time ]] --[[ Line: 337 ]]
        --[[ Upvalues: (ref 1): l_Pre_0, (ref 2): v_u_13, (ref 3): v_u_43 ]]
        return l_Pre_0 ~= v_u_13.State.Holding and l_Pre_0 ~= v_u_13.State.HoldMissedActive and 0 or v_u_43 - p78:get_tail_hit_time();
    end;
    v33.es_note_test_release = function(p79, _, p80) --[[ Name: es_note_test_release ]] --[[ Line: 344 ]]
        --[[ Upvalues: (ref 1): l_Pre_0, (ref 2): v_u_13, (ref 3): v_u_1, (ref 4): v_u_45, (ref 5): v_u_3 ]]
        local v81 = p80 == nil and 0 or p80
        if l_Pre_0 == v_u_13.State.Holding or l_Pre_0 == v_u_13.State.HoldMissedActive then
            local v82 = p79:get_delta_time_from_release_time() + v81
            local v83 = v_u_1:timedelta_to_result_obj(v82, v_u_45)
            if v83 == v_u_3.NoteResult_Miss then
                if l_Pre_0 == v_u_13.State.HoldMissedActive then
                    return false, v_u_3.NoteResult_Miss, v82;
                else
                    return true, v_u_3.NoteResult_Miss, v82;
                end;
            else
                return true, v83, v82;
            end;
        else
            return false, v_u_3.NoteResult_Miss, 0;
        end;
    end;
    v33.es_note_on_release = function(p84, _, p85, _, p86) --[[ Name: es_note_on_release ]] --[[ Line: 364 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_51, (ref 3): l_Pre_0, (ref 4): v_u_13, (ref 5): v_u_3, (ref 6): p_u_25, (ref 7): p_u_27, (ref 8): p_u_26, (ref 9): v_u_7, (ref 10): p_u_32, (ref 11): v_u_47 ]]
        v_u_50:note_on_release(p85)
        if v_u_51 then
            v_u_51:note_on_release(p85)
        end;
        if l_Pre_0 == v_u_13.State.Holding or l_Pre_0 == v_u_13.State.HoldMissedActive then
            if p85 == v_u_3.NoteResult_Miss then
                p_u_25:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_25, v_u_3.NoteResult_Miss, p_u_27, p_u_26, {
                    ["PlaySFX"] = true,
                    ["PlayHoldEffect"] = false,
                    ["HitTime"] = p_u_25:es_gamelocal_get_audiomanager():get_current_time_ms(),
                    ["Type"] = 25,
                    [v_u_7.ParamNoteHitMode] = v_u_7.HeldReleaseEarly,
                    [v_u_7.ParamNoteIndex] = p_u_32
                })
                l_Pre_0 = v_u_13.State.HoldMissedActive
                return;
            end;
            p_u_25:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_25, p85, p_u_27, p_u_26, {
                ["PlaySFX"] = true,
                ["PlayHoldEffect"] = false,
                ["HitTime"] = p84:get_tail_hit_time(),
                ["Delta"] = p86,
                ["Type"] = 26,
                [v_u_7.ParamNoteHitMode] = v_u_7.HeldHitTail,
                [v_u_7.ParamNoteIndex] = p_u_32
            })
            v_u_47 = true
            l_Pre_0 = v_u_13.State.Passed
        end;
    end;
    v33.get_track_index = function(_) --[[ Name: get_track_index ]] --[[ Line: 407 ]]
        --[[ Upvalues: (ref 1): p_u_26 ]]
        return p_u_26;
    end;
    return v33;
end;
return v_u_13;
