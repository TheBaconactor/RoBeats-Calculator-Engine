-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_4 = require(game.ReplicatedStorage.Effects.HoldingNoteEffect)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_7 = require(game.ReplicatedStorage.Effects.TriggerNoteEffect)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_9 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_10 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_11 = require(game.ReplicatedStorage.Local.HeldNoteState)
local v_u_12 = require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_96 = {
    ["_new"] = function(_, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17, p_u_18, p_u_19, p_u_20, p_u_21) --[[ Name: _new ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_12, (copy 3): v_u_8, (copy 4): v_u_6, (copy 5): v_u_1, (copy 6): v_u_10, (copy 7): v_u_11, (copy 8): v_u_2, (copy 9): v_u_4, (copy 10): v_u_3, (copy 11): v_u_9, (copy 12): v_u_7 ]]
        local v22 = {}
        v22.rebind = function(_, p23, p24, p25, p26, p27, p28, p29, p30, p31) --[[ Name: rebind ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): p_u_14, (ref 3): p_u_15, (ref 4): p_u_16, (ref 5): p_u_17, (ref 6): p_u_18, (ref 7): p_u_19, (ref 8): p_u_20, (ref 9): p_u_21 ]]
            p_u_13 = p23
            p_u_14 = p24
            p_u_15 = p25
            p_u_16 = p26
            p_u_17 = p27
            p_u_18 = p28
            p_u_19 = p29
            p_u_20 = p30
            p_u_21 = p31
        end;
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = true
        local v_u_40 = Vector2.new(0, 0.25)
        local v_u_41 = Vector2.new(1, 0.65)
        local v_u_42 = Vector2.new(0, 0.3833333333333333)
        local v_u_43 = Vector2.new(1, 0.85)
        local v_u_44 = false
        local v_u_45 = nil
        local v_u_46 = nil
        local v_u_47 = 1
        local v_u_48 = v_u_5:new()
        local v_u_49 = v_u_12:new(0.15)
        local v_u_50 = 0
        v22.cons = function(_) --[[ Name: cons ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_47, (copy 3): v_u_48, (ref 4): v_u_50, (ref 5): p_u_13, (ref 6): v_u_44, (ref 7): v_u_8, (ref 8): v_u_40, (ref 9): v_u_41, (ref 10): v_u_42, (ref 11): v_u_43, (ref 12): v_u_35, (ref 13): v_u_6, (ref 14): v_u_36, (ref 15): v_u_37, (ref 16): v_u_38, (ref 17): v_u_32, (ref 18): v_u_33, (ref 19): v_u_34, (ref 20): p_u_15, (ref 21): p_u_14, (ref 22): v_u_45, (ref 23): v_u_46, (ref 24): p_u_18, (ref 25): p_u_17 ]]
            v_u_39 = true
            v_u_47 = 1
            v_u_48:clear()
            v_u_50 = p_u_13:es_gamelocal_get_audiomanager():get_current_time_ms()
            v_u_44 = p_u_13._player_settings_manager:get_key(v_u_8.Key.HeldNoteTransparent) == true
            if p_u_13:show_fullscreen_mobile_ui() then
                v_u_40 = Vector2.new(0, 0.9)
                v_u_41 = Vector2.new(1, 1.05)
                v_u_42 = Vector2.new(0, 1.1)
                v_u_43 = Vector2.new(1, 1.25)
            else
                v_u_40 = Vector2.new(0, 0.25)
                v_u_41 = Vector2.new(1, 0.65)
                v_u_42 = Vector2.new(0, 0.3833333333333333)
                v_u_43 = Vector2.new(1, 0.85)
            end;
            local l_HeldNoteAdornProto_0 = game.ReplicatedStorage.ElementProtos.HeldNoteAdornProto
            local l_Body_0 = l_HeldNoteAdornProto_0.Body.Body
            local l_Head_0 = l_HeldNoteAdornProto_0.Head.Head
            local l_Tail_0 = l_HeldNoteAdornProto_0.Tail.Tail
            local l_HeadOutline_0 = l_HeldNoteAdornProto_0.Head.HeadOutline
            local l_TailOutline_0 = l_HeldNoteAdornProto_0.Tail.TailOutline
            local l_BodyOutlineLeft_0 = l_HeldNoteAdornProto_0.Body.BodyOutlineLeft
            local l_BodyOutlineRight_0 = l_HeldNoteAdornProto_0.Body.BodyOutlineRight
            v_u_35 = p_u_13._adorn_pool:depool(v_u_6.Type.Cylinder)
            v_u_6:cylinder_adorn_copy_properties(l_HeadOutline_0.Adorn, v_u_35)
            v_u_36 = p_u_13._adorn_pool:depool(v_u_6.Type.Cylinder)
            v_u_6:cylinder_adorn_copy_properties(l_TailOutline_0.Adorn, v_u_36)
            v_u_37 = p_u_13._adorn_pool:depool(v_u_6.Type.Cylinder)
            v_u_6:cylinder_adorn_copy_properties(l_BodyOutlineLeft_0.Adorn, v_u_37)
            v_u_38 = p_u_13._adorn_pool:depool(v_u_6.Type.Cylinder)
            v_u_6:cylinder_adorn_copy_properties(l_BodyOutlineRight_0.Adorn, v_u_38)
            v_u_32 = p_u_13._adorn_pool:depool(v_u_6.Type.Cylinder)
            v_u_6:cylinder_adorn_copy_properties(l_Body_0.Adorn, v_u_32)
            v_u_33 = p_u_13._adorn_pool:depool(v_u_6.Type.Sphere)
            v_u_6:sphere_adorn_copy_properties(l_Head_0.Adorn, v_u_33)
            v_u_34 = p_u_13._adorn_pool:depool(v_u_6.Type.Sphere)
            v_u_6:sphere_adorn_copy_properties(l_Tail_0.Adorn, v_u_34)
            local v51 = p_u_13:es_gamelocal_tracksystem_of_index(p_u_15):es_get_track(p_u_14)
            v_u_45 = v51:get_start_position()
            v_u_46 = v51:get_end_position()
            v_u_47 = 1
            v_u_48:clear()
            local v52 = p_u_13:es_gamelocal_get_audiomanager():get_beat_duration() * 0.5
            for v53 = v52, p_u_18, v52 do
                if v53 + v52 <= p_u_18 then
                    v_u_48:push_back(p_u_17 + v53)
                end;
            end;
        end;
        local function _() --[[ Name: is_local_slot ]] --[[ Line: 132 ]]
            --[[ Upvalues: (ref 1): p_u_15, (ref 2): p_u_13 ]]
            return p_u_15 == p_u_13:get_local_game_slot();
        end;
        local function f_get_head_t() --[[ Name: get_head_t ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): p_u_21 ]]
            return p_u_21:get_head_t();
        end;
        local function _() --[[ Name: get_head_position ]] --[[ Line: 140 ]]
            --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_46, (copy 3): f_get_head_t ]]
            return v_u_45:Lerp(v_u_46, f_get_head_t());
        end;
        local function _() --[[ Name: get_tail_hit_time ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): p_u_21 ]]
            return p_u_21:get_tail_hit_time();
        end;
        local function _() --[[ Name: get_tail_t ]] --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): p_u_21 ]]
            return p_u_21:get_tail_t();
        end;
        local function _() --[[ Name: get_tail_position ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_45, (ref 3): v_u_46 ]]
            if p_u_21:is_tail_active() then
                return v_u_45:Lerp(v_u_46, (p_u_21:get_tail_t()));
            else
                return v_u_45;
            end;
        end;
        v22.update_visual = function(_, p54) --[[ Name: update_visual ]] --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (ref 3): p_u_13, (ref 4): p_u_15, (ref 5): p_u_21, (ref 6): v_u_32, (ref 7): v_u_33, (ref 8): v_u_34, (ref 9): v_u_45, (ref 10): v_u_46, (copy 11): f_get_head_t, (ref 12): v_u_6, (ref 13): v_u_35, (ref 14): v_u_36, (ref 15): v_u_50, (ref 16): p_u_17, (ref 17): v_u_44, (ref 18): v_u_11, (ref 19): v_u_2, (ref 20): v_u_40, (ref 21): v_u_41, (ref 22): v_u_37, (ref 23): v_u_38, (ref 24): v_u_42, (ref 25): v_u_43 ]]
            v_u_1:profilebegin("HeldNote:update_visual(CFrame)")
            local v55 = p_u_21:color3_for_slot(p_u_15, (v_u_10:get_server_game_instance_player_powerbar_active(p_u_13._players._slots:get(p_u_15))))
            v_u_32.Color3 = v55
            v_u_33.Color3 = v55
            v_u_34.Color3 = v55
            local v56 = v_u_45:Lerp(v_u_46, f_get_head_t())
            local v57
            if p_u_21:is_tail_active() then
                v57 = v_u_45:Lerp(v_u_46, (p_u_21:get_tail_t()))
            else
                v57 = v_u_45
            end;
            v_u_33.CFrame = CFrame.new(v56 + Vector3.new(0, -0.35, 0)) * v_u_6:cylinder_up_cframe()
            v_u_34.CFrame = CFrame.new(v57 + Vector3.new(0, -0.35, 0)) * v_u_6:cylinder_up_cframe()
            v_u_35.CFrame = CFrame.new(v56 + Vector3.new(0, -0.65, 0)) * v_u_6:cylinder_up_cframe()
            v_u_36.CFrame = CFrame.new(v57 + Vector3.new(0, -0.65, 0)) * v_u_6:cylinder_up_cframe()
            if p_u_21:did_trigger_head() and p_u_17 < v_u_50 then
                v56 = v_u_46
            end;
            local v58 = v56 - v57
            local v59, v60, v61, v62, v63, v64
            if v_u_44 then
                v59 = 0
                v60 = 0.9
                v61 = 1
                v62 = 0.25
                v63 = 1
                v64 = 0.5
            else
                v59 = 0
                v60 = 0
                v61 = 1
                v62 = 0
                v63 = 0
                v64 = 0
            end;
            local v65 = p_u_21:get_state()
            if v65 == v_u_11.Pre then
                v_u_33.Transparency = v59
                v_u_35.Transparency = v59
            else
                v_u_33.Transparency = v61
                v_u_35.Transparency = v61
            end;
            if v65 == v_u_11.Passed and p_u_21:did_trigger_tail() then
                v_u_34.Transparency = v61
                v_u_36.Transparency = v61
            elseif p_u_21:tail_visible() then
                v_u_34.Transparency = v62
                v_u_36.Transparency = v63
            else
                v_u_34.Transparency = v61
                v_u_36.Transparency = v61
            end;
            local v66 = p_u_21:get_head_t()
            local v67 = CFrame.Angles(0, v_u_1:deg_to_rad(v_u_1:dir_ang_deg(v58.x, -v58.z) + 90), 0)
            local v68 = v58 * 0.5 + v57
            v_u_32.CFrame = CFrame.new(v68 + Vector3.new(0, -0.35, 0)) * v67
            local v69 = v_u_2:YForPointOf2PtLine(v_u_40, v_u_41, v_u_1:clamp(v66, 0, 1))
            local v70 = v69 * 0.75
            v_u_32.Height = v58.magnitude
            v_u_32.Radius = v70
            v_u_37.CFrame = CFrame.new(v68 + Vector3.new(-v70 * 1.15 - 0.15, -0.5, 0)) * v67
            v_u_38.CFrame = CFrame.new(v68 + Vector3.new(v70 * 1.15 + 0.15, -0.5, 0)) * v67
            v_u_37.Height = v_u_32.Height
            v_u_38.Height = v_u_32.Height
            v_u_37.Radius = v69 * 0.1
            v_u_38.Radius = v69 * 0.1
            local v71 = v_u_2:YForPointOf2PtLine(v_u_42, v_u_43, v_u_1:clamp(v66, 0, 1))
            local v72 = v_u_2:YForPointOf2PtLine(v_u_42, v_u_43, v_u_1:clamp(p_u_21:get_tail_t(), 0, 1))
            v_u_33.Radius = 1.45 * v71
            v_u_34.Radius = 1.45 * v72
            v_u_35.Radius = 1.65 * v71
            v_u_36.Radius = 1.65 * v72
            local v73 = false
            if v65 == v_u_11.HoldMissedActive then
                v_u_37.Transparency = v61
                v_u_38.Transparency = v61
                v64 = 0.9
            elseif v65 == v_u_11.Passed and p_u_21:did_trigger_tail() then
                v_u_37.Transparency = v61
                v_u_38.Transparency = v61
                v73 = true
                v64 = 1
            else
                v_u_37.Transparency = v60
                v_u_38.Transparency = v60
            end;
            if v73 then
                v_u_32.Transparency = v64
            else
                v_u_32.Transparency = v_u_2:Expt(v_u_32.Transparency, v64, v_u_2:NormalizedDefaultExptValueInSeconds(0.15), p54)
            end;
            v_u_1:profileend()
        end;
        local function f_update_beat() --[[ Name: update_beat ]] --[[ Line: 308 ]]
            --[[ Upvalues: (ref 1): p_u_15, (ref 2): p_u_13, (ref 3): v_u_50, (ref 4): v_u_47, (copy 5): v_u_48, (ref 6): p_u_21, (ref 7): v_u_11, (ref 8): p_u_14 ]]
            if p_u_15 == p_u_13:get_local_game_slot() == false then
                return;
            end;
            local v74 = v_u_50
            for v75 = v_u_47, v_u_48:count() do
                if v_u_48:get(v75) > v74 + 5 then
                    break;
                end;
                if p_u_21:get_state() == v_u_11.Holding then
                    p_u_13._world_effect_manager:notify_hold_tick(p_u_13, p_u_15, p_u_14)
                end;
                v_u_47 = v_u_47 + 1
            end;
        end;
        local function f_update_holding_flash(p76) --[[ Name: update_holding_flash ]] --[[ Line: 328 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_11, (copy 3): v_u_49, (ref 4): p_u_15, (ref 5): p_u_13, (ref 6): v_u_4, (ref 7): p_u_14, (ref 8): v_u_3 ]]
            if p_u_21:get_state() == v_u_11.Holding then
                v_u_49:update(p76)
                if v_u_49:do_flash() and p_u_15 == p_u_13:get_local_game_slot() then
                    p_u_13._effects:add_effect(v_u_4:new(p_u_13, p_u_13:es_gamelocal_tracksystem_of_index(p_u_15):es_get_track(p_u_14):get_end_position(), v_u_3.NoteResult_Perfect))
                end;
            end;
        end;
        v22.update = function(_, p77) --[[ Name: update ]] --[[ Line: 343 ]]
            --[[ Upvalues: (ref 1): v_u_50, (ref 2): p_u_13, (ref 3): v_u_39, (copy 4): f_update_beat, (copy 5): f_update_holding_flash ]]
            v_u_50 = p_u_13:es_gamelocal_get_audiomanager():get_current_time_ms()
            if v_u_39 == true then
                f_update_beat()
                f_update_holding_flash(p77)
            end;
        end;
        v22.cleanup = function(p78) --[[ Name: cleanup ]] --[[ Line: 350 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_34, (ref 5): v_u_35, (ref 6): v_u_36, (ref 7): v_u_37, (ref 8): v_u_38 ]]
            p_u_13._adorn_pool:repool(v_u_32)
            p_u_13._adorn_pool:repool(v_u_33)
            p_u_13._adorn_pool:repool(v_u_34)
            p_u_13._adorn_pool:repool(v_u_35)
            p_u_13._adorn_pool:repool(v_u_36)
            p_u_13._adorn_pool:repool(v_u_37)
            p_u_13._adorn_pool:repool(v_u_38)
            v_u_32 = nil
            v_u_33 = nil
            v_u_34 = nil
            v_u_35 = nil
            v_u_36 = nil
            v_u_37 = nil
            v_u_38 = nil
            p_u_13._lua_pool:repool("HeldNoteAdornRender", p78)
        end;
        v22.note_on_hit = function(_, p79) --[[ Name: note_on_hit ]] --[[ Line: 369 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): p_u_21, (ref 3): v_u_11, (ref 4): p_u_13, (ref 5): v_u_8, (ref 6): v_u_9, (ref 7): v_u_7, (ref 8): v_u_45, (ref 9): v_u_46, (copy 10): f_get_head_t, (ref 11): p_u_15, (ref 12): v_u_4 ]]
            if v_u_39 == true then
                local v80 = p_u_21:get_state()
                if v80 == v_u_11.Pre then
                    if p_u_13._player_settings_manager:get_key(v_u_8.Key.BrightnessSettings) == v_u_9.Normal then
                        p_u_13._effects:add_effect(v_u_7:new(p_u_13, v_u_45:Lerp(v_u_46, f_get_head_t()), p79, p_u_15 == p_u_13:get_local_game_slot()))
                        return;
                    end;
                elseif v80 == v_u_11.HoldMissedActive then
                    if p_u_13._player_settings_manager:get_key(v_u_8.Key.BrightnessSettings) == v_u_9.Normal then
                        local l__effects_0 = p_u_13._effects
                        local v81 = v_u_7
                        local v82 = p_u_13
                        local v83
                        if p_u_21:is_tail_active() then
                            v83 = v_u_45:Lerp(v_u_46, (p_u_21:get_tail_t()))
                        else
                            v83 = v_u_45
                        end;
                        l__effects_0:add_effect(v81:new(v82, v83, p79))
                    end;
                    local l__effects_1 = p_u_13._effects
                    local v84 = v_u_4
                    local v85 = p_u_13
                    local v86
                    if p_u_21:is_tail_active() then
                        v86 = v_u_45:Lerp(v_u_46, (p_u_21:get_tail_t()))
                    else
                        v86 = v_u_45
                    end;
                    l__effects_1:add_effect(v84:new(v85, v86, p79))
                end;
            end;
        end;
        v22.note_on_release = function(_, p87) --[[ Name: note_on_release ]] --[[ Line: 398 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): p_u_21, (ref 3): v_u_11, (ref 4): v_u_3, (ref 5): p_u_13, (ref 6): v_u_8, (ref 7): v_u_9, (ref 8): v_u_7, (ref 9): v_u_45, (ref 10): v_u_46, (ref 11): p_u_15, (ref 12): v_u_4 ]]
            if v_u_39 == true then
                local v88 = p_u_21:get_state()
                if v88 == v_u_11.Holding or v88 == v_u_11.HoldMissedActive then
                    if p87 == v_u_3.NoteResult_Miss then
                        return;
                    end;
                    if p_u_13._player_settings_manager:get_key(v_u_8.Key.BrightnessSettings) == v_u_9.Normal then
                        local l__effects_2 = p_u_13._effects
                        local v89 = v_u_7
                        local v90 = p_u_13
                        local v91
                        if p_u_21:is_tail_active() then
                            v91 = v_u_45:Lerp(v_u_46, (p_u_21:get_tail_t()))
                        else
                            v91 = v_u_45
                        end;
                        l__effects_2:add_effect(v89:new(v90, v91, p87, p_u_15 == p_u_13:get_local_game_slot()))
                    end;
                    local l__effects_3 = p_u_13._effects
                    local v92 = v_u_4
                    local v93 = p_u_13
                    local v94
                    if p_u_21:is_tail_active() then
                        v94 = v_u_45:Lerp(v_u_46, (p_u_21:get_tail_t()))
                    else
                        v94 = v_u_45
                    end;
                    l__effects_3:add_effect(v92:new(v93, v94, p87))
                end;
            end;
        end;
        v22.set_visible = function(_, p95) --[[ Name: set_visible ]] --[[ Line: 421 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_34, (ref 5): v_u_35, (ref 6): v_u_36, (ref 7): v_u_37, (ref 8): v_u_38 ]]
            v_u_39 = p95
            v_u_32.Visible = p95
            v_u_33.Visible = p95
            v_u_34.Visible = p95
            v_u_35.Visible = p95
            v_u_36.Visible = p95
            v_u_37.Visible = p95
            v_u_38.Visible = p95
        end;
        return v22;
    end
}
v_u_96.new = function(_, p97, p98, p99, p100, p101, p102, p103, p104, p105) --[[ Name: new ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_96 ]]
    local v106 = p97._lua_pool:depool("HeldNoteAdornRender")
    if v106 == nil then
        local v107 = v_u_96:_new(p97, p98, p99, p100, p101, p102, p103, p104, p105)
        v107:cons()
        return v107;
    else
        v106:rebind(p97, p98, p99, p100, p101, p102, p103, p104, p105)
        v106:cons()
        return v106;
    end;
end;
v_u_96.prepool = function(_, p108) --[[ Name: prepool ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_96 ]]
    p108._lua_pool:repool("HeldNoteAdornRender", v_u_96:_new())
end;
return v_u_96;
