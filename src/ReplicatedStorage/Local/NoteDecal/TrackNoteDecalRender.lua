-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_3 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_5 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_7 = require(game.ReplicatedStorage.Shared.Note2DSettings)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["new"] = function(_, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_8, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_4, (copy 7): v_u_5, (copy 8): v_u_2 ]]
        local v12 = {}
        local v_u_13 = p_u_9._ui_manager:get_decal_ui_manager()
        local v_u_14 = 0.25
        local v_u_15 = 0.15
        local v_u_16 = 0
        local v_u_17 = 0
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        v12.cons = function(_) --[[ Name: cons ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_14, (ref 3): v_u_17, (ref 4): v_u_18, (ref 5): v_u_1, (copy 6): p_u_10, (copy 7): p_u_11, (ref 8): v_u_19, (ref 9): v_u_20, (ref 10): v_u_21, (ref 11): v_u_22, (ref 12): v_u_8, (copy 13): p_u_9, (ref 14): v_u_6 ]]
            v_u_16 = v_u_14
            v_u_17 = v_u_16
            v_u_18 = Instance.new("ImageLabel")
            v_u_18.Image = ""
            v_u_18.BackgroundColor3 = v_u_1:color3(0, 0, 0)
            v_u_18.BackgroundTransparency = v_u_1:tra(v_u_16)
            v_u_18.Name = v_u_1:gen_name(string.format("_ui_track_background slot(%d) _track_index(%d)", p_u_10:get_game_slot(), p_u_11))
            v_u_18.ZIndex = 0
            local l_ImageLabel_0 = Instance.new("ImageLabel", v_u_18)
            l_ImageLabel_0.Image = ""
            l_ImageLabel_0.BackgroundColor3 = v_u_1:color3(255, 255, 255)
            l_ImageLabel_0.BackgroundTransparency = v_u_1:tra(0.1)
            l_ImageLabel_0.Size = UDim2.new(0, 4, 1, 0)
            l_ImageLabel_0.Position = UDim2.new(0, -2, 0, 0)
            l_ImageLabel_0.ZIndex = 1
            local l_ImageLabel_1 = Instance.new("ImageLabel", v_u_18)
            l_ImageLabel_1.Image = ""
            l_ImageLabel_1.BackgroundColor3 = v_u_1:color3(255, 255, 255)
            l_ImageLabel_1.BackgroundTransparency = v_u_1:tra(0.1)
            l_ImageLabel_1.Size = UDim2.new(0, 4, 1, 0)
            l_ImageLabel_1.Position = UDim2.new(1, -2, 0, 0)
            l_ImageLabel_1.ZIndex = 1
            v_u_19 = Instance.new("ImageLabel", v_u_18)
            v_u_19.ZIndex = 2
            v_u_19.Name = v_u_1:gen_name(string.format("_ui_trigger_button_back slot(%d) _track_index(%d)", p_u_10:get_game_slot(), p_u_11))
            v_u_19.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_19.BackgroundTransparency = 1
            v_u_20 = Instance.new("ImageLabel", v_u_19)
            v_u_20.ZIndex = 3
            v_u_20.Size = UDim2.new(1, 0, 1, 0)
            v_u_20.BackgroundTransparency = 1
            v_u_21 = Instance.new("ImageLabel", v_u_20)
            v_u_21.ZIndex = 4
            v_u_21.Size = UDim2.new(1, 0, 1, 0)
            v_u_21.BackgroundTransparency = 1
            v_u_21.ImageTransparency = v_u_1:tra(0.75)
            v_u_22 = Instance.new("TextLabel")
            v_u_22.ZIndex = 1
            v_u_22.AnchorPoint = Vector2.new(0.5, 1)
            v_u_22.BackgroundTransparency = 1
            v_u_22.Font = Enum.Font.SourceSansBold
            v_u_22.TextScaled = true
            v_u_22.TextColor3 = v_u_1:color3(100, 100, 100)
            v_u_22.Visible = false
            local v23
            if v_u_1:is_mobile() then
                v23 = "Tap!"
            elseif v_u_8.ControllerInputEnabled and p_u_9._input:is_controller_active() then
                v23 = string.format("%s\n%s", p_u_9._input:button_keycode_to_name(p_u_9._input:track_index_to_default_controller_button(p_u_11)), p_u_9._input:button_keycode_to_name(p_u_9._input:track_index_to_default_controller_dpad(p_u_11)))
            else
                local function _() --[[ Name: get_track_key ]] --[[ Line: 100 ]]
                    --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_6 ]]
                    if p_u_11 == 1 then
                        return v_u_6.KEY_TRACK1;
                    elseif p_u_11 == 2 then
                        return v_u_6.KEY_TRACK2;
                    elseif p_u_11 == 3 then
                        return v_u_6.KEY_TRACK3;
                    else
                        return v_u_6.KEY_TRACK4;
                    end;
                end;
                local v24
                if p_u_11 == 1 then
                    v24 = v_u_6.KEY_TRACK1
                elseif p_u_11 == 2 then
                    v24 = v_u_6.KEY_TRACK2
                elseif p_u_11 == 3 then
                    v24 = v_u_6.KEY_TRACK3
                else
                    v24 = v_u_6.KEY_TRACK4
                end;
                if p_u_9._input:get_custom_key_keycode(v24) == nil then
                    v23 = p_u_11 == 1 and "A" or (p_u_11 == 2 and "S" or (p_u_11 == 3 and "D" or "F"))
                else
                    v23 = p_u_9._input:get_key_display_str(v24)
                end;
            end;
            v_u_22.Text = v23
        end;
        v12.set_note_display_mode = function(_, p25) --[[ Name: set_note_display_mode ]] --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_18, (ref 3): v_u_19, (ref 4): v_u_22, (copy 5): v_u_13, (copy 6): p_u_11, (copy 7): p_u_10, (ref 8): v_u_7, (ref 9): v_u_14, (ref 10): v_u_15, (ref 11): v_u_1, (ref 12): v_u_4, (ref 13): v_u_20, (ref 14): v_u_21 ]]
            if p25 == v_u_3.Default then
                v_u_18.Parent = nil
                v_u_19.Parent = nil
                v_u_22.Parent = nil
                return;
            else
                local v26, v27 = v_u_13:get_track_size_and_position()
                local v28 = v_u_13:get_screengui()
                v_u_18.Parent = v28
                v_u_18.Position = UDim2.new(0, v27:get(p_u_11), 0, 0)
                v_u_18.Size = UDim2.new(0, v26._x, 0, v26._y)
                local _, _, v29 = p_u_10:get_player_note2d_settings()
                if v29 == v_u_7.Background.Dark then
                    v_u_14 = 0.95
                    v_u_15 = 0.9
                elseif v29 == v_u_7.Background.Transparent then
                    v_u_14 = 0.15
                    v_u_15 = 0.1
                else
                    v_u_14 = 0.5
                    v_u_15 = 0.4
                end;
                v_u_18.BackgroundTransparency = v_u_1:tra(v_u_14)
                local _, v30 = p_u_10:get_player_note_display_mode_and_decal_id()
                local v31 = v_u_4:singleton():get_info_for_id(v30)
                v_u_19.Parent = v28
                v_u_19.Image = v31:get_trigger_back_assetid(p_u_11)
                v_u_20.Image = v31:get_trigger_mid_assetid(p_u_11)
                if v31:apply_color_to_trigger_mid() then
                    v_u_20.ImageColor3 = v_u_1:color3(52, 41, 23)
                end;
                v_u_21.Image = v31:get_trigger_over_assetid(p_u_11)
                local _, v32 = v_u_13:get_start_end_point_for_track_system_index(p_u_10, p_u_11)
                v_u_19.Position = UDim2.new(0, v32.X, 0, v32.Y)
                local v33 = v26._x * v31:get_note_size_scale()
                v_u_19.Size = UDim2.new(0, v33, 0, v33)
                if v_u_1:is_mobile() then
                    v_u_22.Parent = v28
                    v_u_22.Position = UDim2.new(p_u_11 * 0.25 - 0.125, 0, 1, 0)
                    v_u_22.Size = UDim2.new(0, v33 * 0.8, 0, v33 * 0.8)
                    v_u_22.TextColor3 = v_u_1:color3(175, 175, 175)
                    v_u_22.AnchorPoint = Vector2.new(0.5, 1)
                    return;
                else
                    local v34 = p_u_10:get_active_note_display_mode()
                    if v34 == v_u_3.DecalDown then
                        v_u_22.Parent = v_u_19
                        v_u_22.Position = UDim2.new(0.5, 0, 0, 0)
                        v_u_22.Size = UDim2.new(0.8, 0, 0.8, 0)
                        v_u_22.TextColor3 = v_u_1:color3(100, 100, 100)
                        v_u_22.AnchorPoint = Vector2.new(0.5, 1)
                    elseif v34 == v_u_3.DecalUp then
                        v_u_22.Parent = v_u_19
                        v_u_22.Position = UDim2.new(0.5, 0, 1, 0)
                        v_u_22.Size = UDim2.new(0.8, 0, 0.8, 0)
                        v_u_22.TextColor3 = v_u_1:color3(100, 100, 100)
                        v_u_22.AnchorPoint = Vector2.new(0.5, 0)
                    end;
                end;
            end;
        end;
        v12.update_color = function(_) --[[ Name: update_color ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_9, (copy 3): p_u_10, (copy 4): p_u_11, (ref 5): v_u_19, (ref 6): v_u_21 ]]
            local v35
            if v_u_5:get_server_game_instance_player_powerbar_active(p_u_9._players._slots:get(p_u_10:get_game_slot())) then
                v35 = p_u_10:get_fevercolor_list():get(p_u_11):to_color3()
            else
                v35 = p_u_10:get_basecolor_list():get(p_u_11):to_color3()
            end;
            v_u_19.ImageColor3 = v35
            v_u_21.ImageColor3 = v35
        end;
        local function _(p36, p37, p38) --[[ Name: next ]] --[[ Line: 209 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            return v_u_2:Expt(p36, p37, v_u_2:NormalizedDefaultExptValueInSeconds(0.25), p38);
        end;
        v12.update = function(p39, p40) --[[ Name: update ]] --[[ Line: 217 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_3, (copy 3): v_u_13, (ref 4): v_u_16, (ref 5): v_u_17, (ref 6): v_u_2, (ref 7): v_u_18, (ref 8): v_u_1, (copy 9): p_u_9, (ref 10): v_u_22 ]]
            local v41 = p_u_10:get_active_note_display_mode()
            if v41 ~= v_u_3.Default and v_u_13:raise_ui_recalculate() then
                p39:set_note_display_mode(v41)
            end;
            p39:update_color()
            local v42 = v_u_2:Expt(v_u_16, v_u_17, v_u_2:NormalizedDefaultExptValueInSeconds(0.25), p40)
            if v42 ~= v_u_16 then
                v_u_16 = v42
                v_u_18.BackgroundTransparency = v_u_1:tra(v_u_16)
            end;
            if p_u_9:is_spectate() == true or (p_u_9:is_preview_game() == true or (not p_u_9._camera_manager or p_u_9._camera_manager:camera_transitioning() == true)) then
                v_u_22.Visible = false
                return;
            else
                local v43 = p_u_9:es_gamelocal_get_audiomanager()
                local v44 = v43:get_current_mode()
                local v45 = v43:Mode()
                v43:is_beat()
                local v46
                if v44 == v45.PostPlaying then
                    v46 = false
                else
                    v46 = v44 ~= v45.Finished
                end;
                if v46 and (v43:get_song_length_ms() - v43:get_current_time_ms() > 5000 and p_u_9:get_time_since_any_pressed() > 2.5) then
                    v_u_22.Visible = true
                else
                    v_u_22.Visible = false
                end;
            end;
        end;
        v12.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 252 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:Destroy()
            v_u_18 = nil
        end;
        v12.press = function(_) --[[ Name: press ]] --[[ Line: 257 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_18, (ref 5): v_u_1 ]]
            v_u_17 = v_u_15
            v_u_16 = v_u_17
            v_u_18.BackgroundTransparency = v_u_1:tra(v_u_16)
        end;
        v12.release = function(_) --[[ Name: release ]] --[[ Line: 263 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_14 ]]
            v_u_17 = v_u_14
        end;
        v12:cons()
        return v12;
    end
};
