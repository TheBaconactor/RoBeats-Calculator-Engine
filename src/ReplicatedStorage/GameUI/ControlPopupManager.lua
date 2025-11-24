-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_4 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_6 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local _ = game:GetService("UserInputService")
local v_u_8 = {
    ["Popup"] = {}
}
v_u_8.Popup.new = function(_, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_7, (copy 5): v_u_6 ]]
    local v12 = {}
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = 0
    local v_u_16 = 0
    local v_u_17 = nil
    local function _() --[[ Name: face_obj_to_camera ]] --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_2, (copy 3): p_u_9 ]]
        if p_u_10 ~= nil then
            p_u_10.CFrame = v_u_2:lookat_camera_cframe(p_u_10.CFrame.p, p_u_9._spui)
        end;
    end;
    v12.cons = function(p18) --[[ Name: cons ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_2, (copy 3): p_u_9, (ref 4): v_u_14, (ref 5): v_u_17, (ref 6): v_u_13, (ref 7): v_u_15 ]]
        if p_u_10 ~= nil then
            p_u_10.CFrame = v_u_2:lookat_camera_cframe(p_u_10.CFrame.p, p_u_9._spui)
        end;
        v_u_14 = p_u_10.SurfaceGui.Frame
        v_u_17 = p_u_10.SurfaceGui.Frame.Back
        v_u_13 = p_u_10.SurfaceGui.Frame.Letter
        p18:update_control_letter_key()
        p18:set_control_popup_alpha(v_u_15)
    end;
    v12.set_control_popup_alpha = function(_, p19) --[[ Name: set_control_popup_alpha ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_2, (ref 3): v_u_17, (ref 4): v_u_3, (ref 5): p_u_10 ]]
        v_u_13.TextTransparency = v_u_2:tra(p19)
        v_u_17.ImageTransparency = v_u_2:tra(v_u_3:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(1, 0.85), p19))
        local v20 = v_u_3:YForPointOf2PtLine(Vector2.new(0, 1.8), Vector2.new(1, 1.4), p19)
        if math.abs(p_u_10.Size.X - v20) > 0.1 then
            p_u_10.Size = Vector3.new(v20, v20, 0.2)
        end;
    end;
    v12.get_track_key = function(_) --[[ Name: get_track_key ]] --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_4 ]]
        if p_u_11 == 1 then
            return v_u_4.KEY_TRACK1;
        elseif p_u_11 == 2 then
            return v_u_4.KEY_TRACK2;
        elseif p_u_11 == 3 then
            return v_u_4.KEY_TRACK3;
        else
            return v_u_4.KEY_TRACK4;
        end;
    end;
    v12.update_control_letter_key = function(p21) --[[ Name: update_control_letter_key ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_13, (ref 3): v_u_7, (copy 4): p_u_9, (copy 5): p_u_11 ]]
        if v_u_2:is_mobile() then
            v_u_13.Text = "Tap!"
            return;
        elseif v_u_7.ControllerInputEnabled and p_u_9._input:is_controller_active() then
            v_u_13.Text = string.format("%s\n%s", p_u_9._input:button_keycode_to_name(p_u_9._input:track_index_to_default_controller_button(p_u_11)), p_u_9._input:button_keycode_to_name(p_u_9._input:track_index_to_default_controller_dpad(p_u_11)))
            return;
        else
            local v22 = p21:get_track_key()
            if p_u_9._input:get_custom_key_keycode(v22) == nil then
                if p_u_11 == 1 then
                    v_u_13.Text = "A"
                    return;
                elseif p_u_11 == 2 then
                    v_u_13.Text = "S"
                    return;
                elseif p_u_11 == 3 then
                    v_u_13.Text = "D"
                else
                    v_u_13.Text = "F"
                end;
            else
                v_u_13.Text = p_u_9._input:get_key_display_str(v22)
                return;
            end;
        end;
    end;
    v12.update = function(p23, p24, p25, p26, p27, p28) --[[ Name: update ]] --[[ Line: 93 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_6, (copy 3): p_u_11, (ref 4): v_u_15, (ref 5): v_u_3, (ref 6): v_u_16, (ref 7): v_u_14, (ref 8): p_u_10, (ref 9): v_u_2 ]]
        if p_u_9:is_spectate() then
            return;
        else
            local v29 = p_u_9:es_gamelocal_get_tracksystems():get(p_u_9:get_local_game_slot())
            local v30 = p25 and ((v29 and v29:get_active_note_display_mode() == v_u_6.Default and true or false) and (p26 and 1.5 + (p_u_11 - 1) * 0.05 < p28)) and 1 or 0
            if v_u_15 ~= v30 then
                v_u_15 = v_u_3:expt_sec(v_u_15, v30, 0.5, p24)
                p23:set_control_popup_alpha(v_u_15)
            end;
            if v_u_15 > 0.05 then
                if p27 then
                    v_u_16 = -10
                else
                    v_u_16 = v_u_3:expt_sec(v_u_16, 0, 0.5, p24)
                end;
                v_u_14.Position = UDim2.new(0, 0, 0, v_u_16)
            end;
            if p_u_10 ~= nil then
                p_u_10.CFrame = v_u_2:lookat_camera_cframe(p_u_10.CFrame.p, p_u_9._spui)
            end;
        end;
    end;
    v12.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): p_u_10 ]]
        p_u_10:Destroy()
        p_u_10 = nil
    end;
    v12:cons()
    return v12;
end;
v_u_8.new = function(_, p_u_31) --[[ Name: new ]] --[[ Line: 134 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_8 ]]
    local v32 = {
        ["cons"] = function(_) end
    }
    local v_u_33 = v_u_1:new()
    v32.update = function(_, p34) --[[ Name: update ]] --[[ Line: 142 ]]
        --[[ Upvalues: (copy 1): p_u_31, (copy 2): v_u_33 ]]
        local v35 = p_u_31:es_gamelocal_get_audiomanager()
        local v36 = v35:get_current_mode()
        local v37 = v35:Mode()
        local v38 = v35:is_beat()
        local v39
        if v36 == v37.PostPlaying then
            v39 = false
        else
            v39 = v36 ~= v37.Finished
        end;
        local v40 = v35:get_song_length_ms() - v35:get_current_time_ms() > 5000
        local v41 = p_u_31:get_time_since_any_pressed()
        for v42 = 1, v_u_33:count() do
            v_u_33:get(v42):update(p34, v39, v40, v38, v41)
        end;
    end;
    v32.add_control_popup = function(_, p43, p44) --[[ Name: add_control_popup ]] --[[ Line: 156 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_33, (ref 3): v_u_8, (copy 4): p_u_31 ]]
        p44.Parent = v_u_5:get_world_ui_folder()
        v_u_33:push_back(v_u_8.Popup:new(p_u_31, p44, p43))
    end;
    v32.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 161 ]]
        --[[ Upvalues: (copy 1): v_u_33 ]]
        for v45 = 1, v_u_33:count() do
            v_u_33:get(v45):teardown()
        end;
    end;
    v32:cons()
    return v32;
end;
return v_u_8;
