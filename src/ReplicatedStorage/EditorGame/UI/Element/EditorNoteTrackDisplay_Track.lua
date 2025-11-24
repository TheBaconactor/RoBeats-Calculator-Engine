-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_3 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.Note2DSettings)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPRange)
require(game.ReplicatedStorage.Local.HeldNoteState)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
v5:require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_6 ]]
    v_u_6 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorGameDisplayUtil)
end)
return {
    ["new"] = function(_, p_u_7, p_u_8, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_2 ]]
        local v_u_11 = {}
        local v_u_12 = 0
        local v_u_13 = 0
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local function f_create_ui_elements() --[[ Name: create_ui_elements ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_14, (ref 3): v_u_1, (ref 4): v_u_12, (copy 5): p_u_9, (ref 6): v_u_15, (ref 7): v_u_16, (ref 8): v_u_17, (ref 9): v_u_18, (ref 10): v_u_4, (copy 11): p_u_7, (ref 12): v_u_3 ]]
            local v19 = v_u_6:get_base_zindex()
            v_u_14 = Instance.new("ImageLabel")
            v_u_14.Image = ""
            v_u_14.BackgroundColor3 = v_u_1:color3(0, 0, 0)
            v_u_14.BackgroundTransparency = v_u_1:tra(v_u_12)
            v_u_14.Name = v_u_1:gen_name(string.format("EditorNoteTrackDisplay.Track[%d]", p_u_9))
            v_u_14.ZIndex = v19
            local l_ImageLabel_0 = Instance.new("ImageLabel", v_u_14)
            l_ImageLabel_0.Image = ""
            l_ImageLabel_0.BackgroundColor3 = v_u_1:color3(255, 255, 255)
            l_ImageLabel_0.BackgroundTransparency = v_u_1:tra(0.1)
            l_ImageLabel_0.Size = UDim2.new(0, 4, 1, 0)
            l_ImageLabel_0.Position = UDim2.new(0, -2, 0, 0)
            l_ImageLabel_0.ZIndex = v19 + 1
            local l_ImageLabel_1 = Instance.new("ImageLabel", v_u_14)
            l_ImageLabel_1.Image = ""
            l_ImageLabel_1.BackgroundColor3 = v_u_1:color3(255, 255, 255)
            l_ImageLabel_1.BackgroundTransparency = v_u_1:tra(0.1)
            l_ImageLabel_1.Size = UDim2.new(0, 4, 1, 0)
            l_ImageLabel_1.Position = UDim2.new(1, -2, 0, 0)
            l_ImageLabel_1.ZIndex = v19 + 1
            v_u_15 = Instance.new("ImageLabel", v_u_14)
            v_u_15.ZIndex = v19 + 2
            v_u_15.Name = v_u_1:gen_name(string.format("EditorNoteTrackDisplay.TriggerButton[%d]", p_u_9))
            v_u_15.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_15.BackgroundTransparency = 1
            v_u_15.ImageTransparency = v_u_1:tra(1)
            v_u_16 = Instance.new("ImageLabel", v_u_15)
            v_u_16.ZIndex = v19 + 3
            v_u_16.Size = UDim2.new(1, 0, 1, 0)
            v_u_16.BackgroundTransparency = 1
            v_u_17 = Instance.new("ImageLabel", v_u_16)
            v_u_17.ZIndex = v19 + 4
            v_u_17.Size = UDim2.new(1, 0, 1, 0)
            v_u_17.BackgroundTransparency = 1
            v_u_17.ImageTransparency = v_u_1:tra(0.75)
            v_u_18 = Instance.new("TextLabel")
            v_u_18.ZIndex = v19 + 1
            v_u_18.AnchorPoint = Vector2.new(0.5, 1)
            v_u_18.BackgroundTransparency = 1
            v_u_18.Font = Enum.Font.SourceSansBold
            v_u_18.TextScaled = true
            v_u_18.TextColor3 = v_u_1:color3(100, 100, 100)
            v_u_18.Visible = false
            v_u_18.Parent = v_u_15
            v_u_18.Position = UDim2.new(0.5, 0, 0, 0)
            v_u_18.Size = UDim2.new(0.8, 0, 0.8, 0)
            v_u_18.TextColor3 = v_u_1:color3(100, 100, 100)
            v_u_18.AnchorPoint = Vector2.new(0.5, 1)
            local v20
            if v_u_1:is_mobile() then
                v20 = "Tap!"
            elseif v_u_4.ControllerInputEnabled and p_u_7._input:is_controller_active() then
                v20 = string.format("%s\n%s", p_u_7._input:button_keycode_to_name(p_u_7._input:track_index_to_default_controller_button(p_u_9)), p_u_7._input:button_keycode_to_name(p_u_7._input:track_index_to_default_controller_dpad(p_u_9)))
            else
                local function _() --[[ Name: get_track_key ]] --[[ Line: 119 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_3 ]]
                    if p_u_9 == 1 then
                        return v_u_3.KEY_TRACK1;
                    elseif p_u_9 == 2 then
                        return v_u_3.KEY_TRACK2;
                    elseif p_u_9 == 3 then
                        return v_u_3.KEY_TRACK3;
                    else
                        return v_u_3.KEY_TRACK4;
                    end;
                end;
                local v21
                if p_u_9 == 1 then
                    v21 = v_u_3.KEY_TRACK1
                elseif p_u_9 == 2 then
                    v21 = v_u_3.KEY_TRACK2
                elseif p_u_9 == 3 then
                    v21 = v_u_3.KEY_TRACK3
                else
                    v21 = v_u_3.KEY_TRACK4
                end;
                if p_u_7._input:get_custom_key_keycode(v21) == nil then
                    v20 = p_u_9 == 1 and "A" or (p_u_9 == 2 and "S" or (p_u_9 == 3 and "D" or "F"))
                else
                    v20 = p_u_7._input:get_key_display_str(v21)
                end;
            end;
            v_u_18.Text = v20
        end;
        local v_u_22 = Vector2.new(p_u_10.Size.X.Offset, p_u_10.Size.Y.Offset)
        local function _() --[[ Name: get_parent_frame_size ]] --[[ Line: 150 ]]
            --[[ Upvalues: (copy 1): v_u_22 ]]
            return v_u_22;
        end;
        local l_X_0 = v_u_22.X
        local l_Y_0 = v_u_22.Y
        local function f_cons() --[[ Name: cons ]] --[[ Line: 155 ]]
            --[[ Upvalues: (copy 1): f_create_ui_elements, (copy 2): v_u_11, (ref 3): v_u_14, (copy 4): p_u_10, (ref 5): v_u_6, (copy 6): p_u_7, (ref 7): v_u_15, (copy 8): p_u_9, (ref 9): v_u_16, (ref 10): v_u_1, (ref 11): v_u_17 ]]
            f_create_ui_elements()
            local v23, v24 = v_u_11:get_track_size_and_position()
            v_u_14.Parent = p_u_10
            v_u_14.Position = UDim2.new(0, v24, 0, 0)
            v_u_14.Size = UDim2.new(0, v23.X, 0, v23.Y)
            local v25 = v_u_6:get_note_decal_info(p_u_7)
            v_u_15.Parent = p_u_10
            v_u_15.Image = v25:get_trigger_back_assetid(p_u_9)
            v_u_16.Image = v25:get_trigger_mid_assetid(p_u_9)
            if v25:apply_color_to_trigger_mid() then
                v_u_16.ImageColor3 = v_u_1:color3(52, 41, 23)
            end;
            v_u_17.Image = v25:get_trigger_over_assetid(p_u_9)
            local _, v26 = v_u_11:get_start_end_point_for_track_system_index()
            v_u_15.Position = UDim2.new(0, v26.X, 0, v26.Y)
            local v27 = v23.X * v25:get_note_size_scale()
            v_u_15.Size = UDim2.new(0, v27, 0, v27)
            if v25:apply_color_to_trigger_mid() then
                v_u_16.ImageColor3 = v_u_1:color3(52, 41, 23)
            end;
            local v28 = v_u_6:get_color3_for_track(p_u_7, p_u_9, false)
            v_u_15.ImageColor3 = v28
            v_u_17.ImageColor3 = v28
            v_u_15.Visible = false
        end;
        v_u_11.get_track_size_and_position = function(_) --[[ Name: get_track_size_and_position ]] --[[ Line: 190 ]]
            --[[ Upvalues: (copy 1): l_X_0, (copy 2): l_Y_0, (copy 3): p_u_9 ]]
            local v29 = Vector2.new(l_X_0 / 4, l_Y_0)
            return v29, v29.X * (p_u_9 - 1);
        end;
        v_u_11.get_start_end_point_for_track_system_index = function(p30) --[[ Name: get_start_end_point_for_track_system_index ]] --[[ Line: 196 ]]
            --[[ Upvalues: (copy 1): l_Y_0 ]]
            local v31, v32 = p30:get_track_size_and_position()
            local v33 = v32 + v31.X * 0.5
            local l_X_1 = v31.X
            return Vector2.new(v33, -l_X_1), Vector2.new(v33, l_Y_0 - l_X_1);
        end;
        local v_u_34 = false
        v_u_11.is_track_pressed = function(_) --[[ Name: is_track_pressed ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            return v_u_34;
        end;
        v_u_11.track_press = function(_) --[[ Name: track_press ]] --[[ Line: 213 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_12, (ref 3): v_u_14, (ref 4): v_u_1, (ref 5): v_u_34 ]]
            v_u_13 = 0.5
            v_u_12 = v_u_13
            v_u_14.BackgroundTransparency = v_u_1:tra(v_u_12)
            v_u_34 = true
        end;
        v_u_11.track_release = function(_) --[[ Name: track_release ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_34 ]]
            v_u_13 = 0.25
            v_u_34 = false
        end;
        local function _(p35, p36, p37) --[[ Name: next ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            return v_u_2:Expt(p35, p36, v_u_2:NormalizedDefaultExptValueInSeconds(0.25), p37);
        end;
        v_u_11.update = function(_, p38) --[[ Name: update ]] --[[ Line: 233 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_2, (ref 4): v_u_14, (ref 5): v_u_1, (copy 6): p_u_8, (ref 7): v_u_18, (ref 8): v_u_15 ]]
            local v39 = v_u_2:Expt(v_u_12, v_u_13, v_u_2:NormalizedDefaultExptValueInSeconds(0.25), p38)
            if v39 ~= v_u_12 then
                v_u_12 = v39
                v_u_14.BackgroundTransparency = v_u_1:tra(v_u_12)
            end;
            if p_u_8:is_playing() then
                if p_u_8:get_time_since_any_pressed() > 2.5 then
                    v_u_18.Visible = true
                else
                    v_u_18.Visible = false
                end;
                v_u_15.Visible = true
                v_u_15.ImageTransparency = v_u_1:tra(1)
            else
                v_u_18.Visible = false
                v_u_15.Visible = true
                v_u_15.ImageTransparency = v_u_1:tra(0.25)
            end;
        end;
        f_cons()
        return v_u_11;
    end
};
