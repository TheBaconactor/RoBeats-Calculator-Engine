-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_5 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_6 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_9 = require(game.ReplicatedStorage.Menu.SPUIDisplay)
local v_u_10 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.EventString)
return {
    ["new"] = function(_, p_u_11) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_9, (copy 4): v_u_1, (copy 5): v_u_7, (copy 6): v_u_8, (copy 7): v_u_10, (copy 8): v_u_6, (copy 9): v_u_2, (copy 10): v_u_5 ]]
        local v12 = {}
        local v_u_13 = false
        local v_u_14 = nil
        local v_u_15 = v_u_3:new()
        local v_u_16 = 1
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = 0
        local v_u_26 = 0
        v12.cons = function(p27) --[[ Name: cons ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_19, (ref 6): v_u_23, (ref 7): v_u_21, (ref 8): v_u_9, (ref 9): v_u_22, (ref 10): v_u_20, (ref 11): v_u_17, (ref 12): v_u_1, (ref 13): v_u_18, (ref 14): v_u_7, (copy 15): v_u_15 ]]
            if p_u_11:is_tutorial() then
                v_u_14 = game.ReplicatedStorage.WorldUIProto.TutorialOverlay:Clone()
                v_u_14.Parent = v_u_4:get_world_ui_folder()
                v_u_19 = game.ReplicatedStorage.WorldUIProto.WorldUINormalPlane:Clone()
                v_u_19.Parent = v_u_4:get_world_ui_folder()
                v_u_23 = v_u_19.PrimaryPart.SurfaceGui.Frame
                v_u_21 = v_u_9:new(v_u_14.Character, p_u_11._spui):set_position_nxy(0.05, 1):set_anchor_rnxy(0, 1)
                local l_Dialogue_0 = v_u_14.Dialogue
                local l_Frame_0 = l_Dialogue_0.PrimaryPart.SurfaceGui.Frame
                v_u_22 = l_Frame_0.TimeRemaining
                v_u_20 = v_u_9:new(l_Dialogue_0, p_u_11._spui, true):set_position_nxy(0.05, 0.5):set_anchor_rnxy(0, 1)
                v_u_17 = v_u_1:get_list_of_children_of_classname(l_Dialogue_0, "ImageLabel")
                v_u_17:push_back_from_list(v_u_1:get_list_of_children_of_classname(v_u_21:get_part(), "ImageLabel"))
                v_u_18 = v_u_1:get_list_of_children_of_classname(l_Dialogue_0, "TextLabel")
                v_u_7:singleton():get_data_for_key(p_u_11:es_gamelocal_get_audiomanager():get_song_key(), function(p28) --[[ Line: 73 ]]
                    --[[ Upvalues: (ref 1): v_u_15, (copy 2): l_Frame_0, (ref 3): v_u_13 ]]
                    local l_HitObjects_0 = p28.HitObjects[1]
                    local l_HitObjects_1 = p28.HitObjects[2]
                    local l_HitObjects_2 = p28.HitObjects[6]
                    local l_HitObjects_3 = p28.HitObjects[7]
                    v_u_15:push_back({
                        ["TimeMS"] = l_HitObjects_0.Time - 750,
                        ["VisibleFrame"] = l_Frame_0.Message1
                    })
                    v_u_15:push_back({
                        ["TimeMS"] = l_HitObjects_1.Time - 750,
                        ["VisibleFrame"] = l_Frame_0.Message2
                    })
                    v_u_15:push_back({
                        ["TimeMS"] = l_HitObjects_2.Time - 750,
                        ["VisibleFrame"] = l_Frame_0.Message3
                    })
                    v_u_15:push_back({
                        ["TimeMS"] = l_HitObjects_3.Time - 750,
                        ["VisibleFrame"] = l_Frame_0.Message4
                    })
                    v_u_15:push_back({
                        ["TimeMS"] = p28.HitObjects[12].Time - 750,
                        ["VisibleFrame"] = l_Frame_0.Message5
                    })
                    v_u_13 = true
                end)
                if p_u_11._input:is_controller_active() then
                    l_Frame_0.Message1.TextDisplay.Text = string.format("Press \'%s\' as the note hits the button.", p_u_11._input:button_keycode_to_name(p_u_11._input:track_index_to_default_controller_button(1)))
                    l_Frame_0.Message2.TextDisplay.Text = string.format("The default controls are\n\'%s\', \'%s\', \'%s\' and \'%s\'.", p_u_11._input:button_keycode_to_name(p_u_11._input:track_index_to_default_controller_button(1)), p_u_11._input:button_keycode_to_name(p_u_11._input:track_index_to_default_controller_button(2)), p_u_11._input:button_keycode_to_name(p_u_11._input:track_index_to_default_controller_button(3)), p_u_11._input:button_keycode_to_name(p_u_11._input:track_index_to_default_controller_button(4)))
                elseif v_u_1:is_mobile() then
                    l_Frame_0.Message1.TextDisplay.Text = "Tap as the note hits the button."
                    l_Frame_0.Message2.TextDisplay.Text = "There are 4 lanes, one for every button."
                    l_Frame_0.Message3.TextDisplay.Text = "For long notes, tap and hold as the note arrives."
                end;
                p27:set_anim_t(0)
            else
                v_u_13 = false
            end;
        end;
        v12.update = function(p29, p30, _) --[[ Name: update ]] --[[ Line: 121 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_16, (copy 3): v_u_15, (copy 4): p_u_11, (ref 5): v_u_8, (ref 6): v_u_25, (ref 7): v_u_10, (ref 8): v_u_26, (ref 9): v_u_24, (ref 10): v_u_1, (ref 11): v_u_22, (ref 12): v_u_6, (ref 13): v_u_2, (ref 14): v_u_5 ]]
            if v_u_13 == true then
                if v_u_16 <= v_u_15:count() then
                    local v31 = p_u_11:es_gamelocal_get_audiomanager():get_current_time_ms() - v_u_8.PRE_START_TIME_MS_MAX
                    local v32 = v_u_15:get(v_u_16)
                    if v32.TimeMS <= v31 then
                        p_u_11:set_paused(true)
                        v_u_16 = v_u_16 + 1
                        v_u_25 = 1
                        for v33 = 1, v_u_15:count() do
                            v_u_15:get(v33).VisibleFrame.Visible = false
                        end;
                        v32.VisibleFrame.Visible = true
                        p_u_11._sfx_manager:play_sfx(v_u_10.SFX_ACQUIRE)
                        v_u_26 = 0
                    end;
                end;
                if v_u_24 > 0 then
                    v_u_22.Text = tostring((v_u_1:clamp(math.ceil(9 - v_u_26), 1, 9)))
                end;
                if p_u_11:get_current_mode() == v_u_6.Paused then
                    v_u_26 = v_u_26 + v_u_2:TimescaleToDeltaTime(p30)
                    if v_u_24 == 1 and (v_u_26 > 9 or (p_u_11._input:control_just_pressed(v_u_5.KEY_CLICK) or (p_u_11._input:control_just_pressed(v_u_5.KEY_TRACK1) or (p_u_11._input:control_just_pressed(v_u_5.KEY_TRACK2) or (p_u_11._input:control_just_pressed(v_u_5.KEY_TRACK3) or (p_u_11._input:control_just_pressed(v_u_5.KEY_TRACK4) or p_u_11._input:control_just_pressed(v_u_5.KEY_POWERBAR_TRIGGER))))))) then
                        p_u_11:set_paused(false)
                        v_u_25 = 0
                    end;
                end;
                p29:set_anim_t(v_u_2:move_to(v_u_24, v_u_25, 0.25, p30))
                if v_u_24 > 0 then
                    p29:layout()
                end;
            end;
        end;
        local v_u_34 = 1
        v12.set_anim_t = function(_, p35) --[[ Name: set_anim_t ]] --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_1, (ref 3): v_u_17, (ref 4): v_u_18, (ref 5): v_u_14, (ref 6): v_u_34, (ref 7): v_u_2, (ref 8): v_u_23 ]]
            if v_u_24 ~= p35 then
                v_u_24 = p35
                v_u_1:list_set_alpha_name(v_u_17, {
                    ["ImageAlpha"] = v_u_24
                })
                v_u_1:list_set_alpha_name(v_u_18, {
                    ["TextAlpha"] = v_u_24
                })
                v_u_1:r_set_alpha(v_u_14, 1)
                v_u_34 = v_u_2:YForPointOf2PtLineP1P2X(0, 1.25, 1, 1, v_u_24)
                v_u_23.BackgroundTransparency = v_u_1:tra(v_u_2:YForPointOf2PtLineP1P2X(0, 0, 1, 0.25, v_u_24))
            end;
        end;
        v12.layout = function(_) --[[ Name: layout ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_11, (ref 3): v_u_20, (ref 4): v_u_34, (ref 5): v_u_21 ]]
            v_u_19.PrimaryPart.CFrame = p_u_11._spui:get_cframe()
            local v36 = p_u_11._spui:get_size_from_nxy(1, 1)
            v_u_19.PrimaryPart.Size = Vector3.new(v36.X, v36.Y, 0)
            p_u_11._spui:uiobj_rescale_to_max_nxy(v_u_20, 0.35, 0.25, v_u_34)
            p_u_11._spui:uiobj_rescale_to_max_nxy(v_u_21, 0.25, 0.5, v_u_34)
            v_u_20:layout()
            v_u_21:layout()
        end;
        v12.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 193 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_14, (ref 3): v_u_19 ]]
            if v_u_13 == true then
                v_u_14.Parent = nil
                v_u_19.Parent = nil
            end;
        end;
        v12:cons()
        return v12;
    end
};
