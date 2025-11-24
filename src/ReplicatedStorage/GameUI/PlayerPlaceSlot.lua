-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:29 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Shared.ChainCombo)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.GameUI.ComboNotifDisplay)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_10 = require(game.ReplicatedStorage.Local.GameLocalMode)
require(game.ReplicatedStorage.Shared.LVector3)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_12 = require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_13 = v3:new():push_back_table_list({ "ComboSurface" })
return {
    ["new"] = function(_, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_11, (copy 3): v_u_6, (copy 4): v_u_5, (copy 5): v_u_2, (copy 6): v_u_12, (copy 7): v_u_10, (copy 8): v_u_1, (copy 9): v_u_8, (copy 10): v_u_9, (copy 11): v_u_7, (copy 12): v_u_13 ]]
        local v_u_16 = v_u_4:SPUIObjectBase()
        local v_u_17 = nil
        v_u_16._rotation = {
            ["X"] = 0,
            ["Y"] = 0,
            ["Z"] = 0
        }
        v_u_16._position_nxy = {
            ["X"] = 0,
            ["Y"] = 0
        }
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = nil
        local v_u_30 = false
        local v_u_31 = nil
        local v_u_32 = -1
        local v_u_33 = 0
        local v_u_34 = nil
        local v_u_35 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_34, (copy 3): v_u_16, (ref 4): v_u_19, (ref 5): v_u_25, (ref 6): v_u_24, (ref 7): v_u_27, (ref 8): v_u_28, (ref 9): v_u_20, (ref 10): v_u_21, (ref 11): v_u_22, (ref 12): v_u_23, (ref 13): v_u_26, (ref 14): v_u_29, (copy 15): p_u_14, (copy 16): p_u_15, (ref 17): v_u_11, (ref 18): v_u_31, (ref 19): v_u_6, (ref 20): v_u_5, (ref 21): v_u_18 ]]
            v_u_35 = game.ReplicatedStorage.WorldUIProto.PlayerPlaceSlot:Clone()
            v_u_34 = v_u_35.PrimaryPart
            v_u_16:set_enabled(false)
            local l_Frame_0 = v_u_35.MainSurface.SurfaceGui.Frame
            v_u_19 = l_Frame_0.ScoreDisplay
            v_u_25 = l_Frame_0.ModeDisplay
            v_u_24 = l_Frame_0.Back
            v_u_27 = l_Frame_0.GearMultiplierText
            v_u_28 = l_Frame_0.GearMultiplierDisplay
            local l_Frame_1 = v_u_35.PortraitSurface.SurfaceGui.Frame
            v_u_20 = l_Frame_1.ProfileIcon
            v_u_21 = l_Frame_1.NameDisplay
            v_u_22 = l_Frame_1.PlaceDisplay
            v_u_23 = l_Frame_1.ProfileIconBack
            v_u_26 = l_Frame_1.PlayerFeverIconDisplay
            v_u_29 = v_u_35.EmitterSurface.ParticleEmitter
            local v36 = p_u_14:get_game_note_skin_info():get_slot_fevericon_effect_from_setting(p_u_15)
            if v36 == v_u_11:singleton():get_disabled_icon_id() then
                v36 = v_u_11:singleton():get_stars_icon_id()
            end;
            v_u_11:singleton():get_fevericon_for_id(v36):apply_to_emitter(v_u_29)
            v_u_29.Rate = 35
            v_u_29.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.35), NumberSequenceKeypoint.new(1, 1) })
            v_u_16._native_size = v_u_35.PrimaryPart.Size
            v_u_16._size = v_u_16._native_size
            v_u_31 = v_u_6:new(v_u_35.ComboSurface.SurfaceGui.Frame.ComboNotif1, v_u_35.ComboSurface.SurfaceGui.Frame.ComboNotif2, v_u_35.ComboSurface.SurfaceGui.Frame.ComboNotif3, v_u_35.ComboSurface.SurfaceGui.Frame.ComboNotif4, v_u_35.ComboSurface.SurfaceGui.Frame.ChainDisplay, v_u_35.ComboSurface.SurfaceGui.Frame.MultiplierDisplay, v_u_5:new(v_u_16, v_u_35.PrimaryPart, v_u_35.ComboSurface), p_u_14, p_u_15)
            v_u_18 = v_u_5:new(v_u_16, v_u_35.PrimaryPart, v_u_35.PortraitSurface)
            v_u_16._rotation.Y = 15
            v_u_16:layout()
            v_u_16:set_alpha(0)
        end;
        v_u_16.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_35 ]]
            v_u_31:teardown()
            v_u_35:Destroy()
            v_u_35 = nil
        end;
        local v_u_37 = 1
        local v_u_38 = 1
        local l__spui_0 = p_u_14._spui
        local function f_set_size(p39) --[[ Name: set_size ]] --[[ Line: 135 ]]
            --[[ Upvalues: (copy 1): p_u_14, (copy 2): v_u_16, (copy 3): l__spui_0 ]]
            local v40 = p_u_14:show_fullscreen_mobile_ui() and 0.75 or 1
            if v_u_16:is_focused_slot() then
                v_u_16:opt_rescale_to_max_nxy(l__spui_0, v40 * 0.215, v40 * 0.165, p39)
            else
                v_u_16:opt_rescale_to_max_nxy(l__spui_0, v40 * 0.2, v40 * 0.15, p39)
            end;
        end;
        local v_u_41 = v_u_4:cframe_params_default()
        local v_u_42 = false
        local v_u_43 = Vector2.new()
        local v_u_44 = nil
        v_u_16.layout = function(p45) --[[ Name: layout ]] --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_44, (copy 3): f_set_size, (ref 4): v_u_43, (ref 5): v_u_37, (copy 6): v_u_41, (copy 7): l__spui_0, (ref 8): v_u_35, (ref 9): v_u_18 ]]
            if v_u_42 ~= true or v_u_44 ~= p45:is_focused_slot() then
                v_u_44 = p45:is_focused_slot()
                f_set_size(1)
                v_u_43 = p45:anchored_offset(0, 0)
                v_u_42 = true
            end;
            f_set_size(v_u_37)
            v_u_41.PositionNXY:set(p45._position_nxy.X, p45._position_nxy.Y)
            v_u_41.OffsetXYZ:set(v_u_43.X, v_u_43.Y)
            v_u_41.LocalRotationOffset:set(p45._rotation.X, p45._rotation.Y, p45._rotation.Z)
            local v46, v47 = p45:opt_update_cframe_params(l__spui_0, v_u_41)
            if v46 == true then
                v_u_35:SetPrimaryPartCFrame(v47)
            end;
            v_u_18:layout()
        end;
        local l__slots_0 = p_u_14._players._slots
        v_u_16.update = function(p48, p49, p50) --[[ Name: update ]] --[[ Line: 172 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_2, (ref 3): v_u_32, (ref 4): v_u_33, (copy 5): l__slots_0, (copy 6): p_u_15, (ref 7): v_u_12, (ref 8): v_u_31, (ref 9): v_u_38, (ref 10): v_u_10, (copy 11): l__spui_0, (ref 12): v_u_1, (copy 13): p_u_14, (ref 14): v_u_8, (ref 15): v_u_9, (ref 16): v_u_37 ]]
            if v_u_17 ~= false then
                p48:set_alpha(v_u_2:Expt(v_u_32, v_u_33, v_u_2:exptvsec(0.5), p49))
                local v51
                if l__slots_0:contains(p_u_15) then
                    if v_u_12:get_selected_mode() == v_u_12.Compete then
                        v51 = l__slots_0:get(p_u_15)._chain
                    else
                        v51 = l__slots_0:get(p_u_15)._naked_chain
                    end;
                else
                    v51 = 0
                end;
                v_u_31:update_with_chain_value(p49, v51, -1, v_u_32)
                v_u_38 = 1
                if p50:is_spectate() and (p50:get_current_mode() == v_u_10.Spectate and (p48:get_nrect(l__spui_0):contains_vec2((l__spui_0:get_cursor_nxy())) and p50._input:get_has_frame_focused_element() ~= true)) then
                    p50._input:set_has_frame_focused_element(true)
                    v_u_38 = 1.15
                    local v52
                    if v_u_1:is_mobile() then
                        v52 = p_u_14._input:control_just_released(v_u_8.KEY_CLICK)
                    else
                        v52 = p_u_14._input:control_just_pressed(v_u_8.KEY_CLICK)
                    end;
                    if v52 then
                        v_u_38 = 1.75
                        if p48:is_focused_slot() ~= true then
                            p50._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                            p50:get_spectate_manager():switch_to_focus_slot(p_u_15)
                        end;
                    end;
                end;
                v_u_37 = v_u_2:Expt(v_u_37, v_u_38, v_u_2:exptvsec(0.5), p49)
            end;
        end;
        v_u_16.set_enabled = function(_, p53) --[[ Name: set_enabled ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_35, (ref 3): v_u_7, (ref 4): v_u_33 ]]
            if v_u_17 ~= p53 then
                v_u_17 = p53
                if v_u_17 then
                    v_u_35.Parent = v_u_7:get_world_ui_folder()
                    v_u_33 = 1
                    return;
                end;
                v_u_35.Parent = nil
                v_u_33 = 0
            end;
        end;
        v_u_16.get_enabled = function(_) --[[ Name: get_enabled ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        local v_u_54 = ""
        local v_u_55 = -1
        local v_u_56 = -1
        local v_u_57 = nil
        local v_u_58 = nil
        v_u_16.is_focused_slot = function(_) --[[ Name: is_focused_slot ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_56, (copy 2): p_u_14 ]]
            return v_u_56 == p_u_14:get_local_game_slot();
        end;
        v_u_16.update_player_info = function(p59, p60, p61, p62) --[[ Name: update_player_info ]] --[[ Line: 248 ]]
            --[[ Upvalues: (ref 1): v_u_56, (ref 2): v_u_19, (ref 3): v_u_1, (ref 4): v_u_12, (ref 5): v_u_30, (ref 6): v_u_29, (ref 7): v_u_27, (ref 8): v_u_28, (ref 9): v_u_54, (ref 10): v_u_55, (ref 11): v_u_57, (ref 12): v_u_58, (ref 13): v_u_20, (ref 14): v_u_21, (ref 15): v_u_25, (ref 16): v_u_26, (ref 17): v_u_22, (copy 18): p_u_14, (ref 19): v_u_23, (ref 20): v_u_24 ]]
            v_u_56 = p61
            v_u_19.Text = v_u_1:comma_value(v_u_12:get_server_game_instance_player_score(p60))
            v_u_30 = true
            v_u_29.Enabled = v_u_12:get_server_game_instance_player_powerbar_active(p60)
            if v_u_12:get_selected_mode() == v_u_12.Casual then
                v_u_27.Visible = false
                v_u_28.Visible = false
            else
                v_u_27.Visible = true
                v_u_28.Visible = true
                v_u_28.Text = string.format("x%.2f", p60:get_gear_multiplier())
            end;
            if p60._name == v_u_54 and (p62 == v_u_55 and (v_u_57 == p59:is_focused_slot() and v_u_58 == v_u_12:get_selected_mode())) then
                return;
            else
                v_u_54 = p60._name
                v_u_55 = p62
                v_u_57 = p59:is_focused_slot()
                v_u_20.Image = string.format("https://www.roblox.com/headshot-thumbnail/image?userId=%d&width=150&height=150&format=png", p60._id)
                v_u_21.Text = p60._name
                v_u_58 = v_u_12:get_selected_mode()
                v_u_25.Image = v_u_12:get_icon_for_mode(v_u_12:get_selected_mode())
                v_u_26.Image = p60._icon
                if p62 == 1 then
                    v_u_22.Text = "1st"
                elseif p62 == 2 then
                    v_u_22.Text = "2nd"
                elseif p62 == 3 then
                    v_u_22.Text = "3rd"
                else
                    v_u_22.Text = "4th"
                end;
                if p_u_14:get_local_game_slot() == p61 then
                    v_u_23.Image = "rbxassetid://698517128"
                    v_u_24.Image = "rbxassetid://698517145"
                else
                    v_u_24.Image = "rbxassetid://698517123"
                    v_u_23.Image = "rbxassetid://698517131"
                end;
            end;
        end;
        v_u_16.get_place = function(_) --[[ Name: get_place ]] --[[ Line: 301 ]]
            --[[ Upvalues: (ref 1): v_u_55 ]]
            return v_u_55;
        end;
        v_u_16.set_tar_alpha = function(_, p63) --[[ Name: set_tar_alpha ]] --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            v_u_33 = p63
        end;
        v_u_16.set_alpha = function(_, p64) --[[ Name: set_alpha ]] --[[ Line: 309 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_1, (ref 3): v_u_35, (ref 4): v_u_13, (ref 5): v_u_22, (ref 6): v_u_30, (ref 7): v_u_29 ]]
            if v_u_32 ~= p64 then
                v_u_32 = p64
                v_u_1:r_set_alpha(v_u_35, v_u_32, v_u_13)
                v_u_22.TextStrokeTransparency = v_u_1:tra(p64 * 0.75)
            end;
            if v_u_32 < 0.05 and v_u_30 == true then
                v_u_29.Enabled = false
                v_u_30 = false
            end;
        end;
        v_u_16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 323 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            return v_u_34.Position;
        end;
        v_u_16.get_native_size = function(p65) --[[ Name: get_native_size ]] --[[ Line: 326 ]]
            return p65._native_size;
        end;
        v_u_16.get_size = function(p66) --[[ Name: get_size ]] --[[ Line: 329 ]]
            return p66._size;
        end;
        v_u_16.set_size = function(p67, p68) --[[ Name: set_size ]] --[[ Line: 332 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_34 ]]
            p67._size = p68
            v_u_1:set_size(v_u_34, p68.X, p68.Y, 0)
        end;
        f_cons()
        return v_u_16;
    end
};
