-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.Override)
local v2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_4 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_5 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugOut)
local v10 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_11 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 14 ]]
    --[[ Upvalues: (ref 1): v_u_11 ]]
    v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
end)
local v_u_12 = v10.DoTriggerButtonAssetFix == true and 0.99 or 1
local v_u_13 = {
    ["TriggerButtonAsset"] = {}
}
v_u_13.TriggerButtonAsset.new = function(_, p_u_14, p_u_15, _, p_u_16) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (copy 1): v_u_3, (ref 2): v_u_11 ]]
    local v17 = {
        ["update"] = function(_, _) end,
        ["on_press"] = function(_) end,
        ["on_release"] = function(_) end,
        ["set_game_noteskin_colors"] = function(_, _, _) end
    }
    v17.get_obj = function(_) --[[ Name: get_obj ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): p_u_16 ]]
        return p_u_16;
    end;
    v17.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): p_u_16 ]]
        p_u_16:Destroy()
    end;
    local v_u_18 = CFrame.new()
    v17.get_initial_cframe = function(_) --[[ Name: get_initial_cframe ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    v17.set_cframe = function(_, p19) --[[ Name: set_cframe ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_16 ]]
        v_u_18 = p19
        p_u_16:SetPrimaryPartCFrame(p19)
    end;
    v17.set_note_display_mode = function(_, p20, _) --[[ Name: set_note_display_mode ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_14, (copy 3): p_u_15, (copy 4): p_u_16, (ref 5): v_u_11 ]]
        if p20 == v_u_3.Default then
            if p_u_14:show_fullscreen_mobile_ui() then
                if p_u_15 == p_u_14:get_local_game_slot() then
                    p_u_16.Parent = v_u_11:get_local_elements_folder()
                else
                    p_u_16.Parent = nil
                end;
            else
                p_u_16.Parent = v_u_11:get_local_elements_folder()
                return;
            end;
        else
            p_u_16.Parent = nil
            return;
        end;
    end;
    return v17;
end;
local function f_create_default_trigger_button_asset(p_u_21, p_u_22, p23) --[[ Name: create_default_trigger_button_asset ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_13, (ref 2): v_u_12, (copy 3): v_u_6, (copy 4): v_u_1, (copy 5): v_u_4, (copy 6): v_u_5, (copy 7): v_u_7, (copy 8): v_u_8 ]]
    local v_u_24
    if p_u_21:show_fullscreen_mobile_ui() then
        v_u_24 = game.ReplicatedStorage.ElementProtos.TriggerButtonProtoMobile:Clone()
    else
        v_u_24 = game.ReplicatedStorage.ElementProtos.TriggerButtonProto:Clone()
    end;
    local v25 = v_u_13.TriggerButtonAsset:new(p_u_21, p_u_22, p23, v_u_24)
    local v_u_26 = 1
    local v_u_27 = nil
    local v_u_28 = nil
    local function _() --[[ Name: cons ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_24, (ref 3): v_u_28, (ref 4): v_u_12 ]]
        v_u_27 = v_u_24.Outer
        v_u_27.Transparency = 0.65
        v_u_28 = v_u_27.InteriorGlow
        v_u_28.Transparency = v_u_12
    end;
    local v_u_29 = v_u_6:get_default_base_color():to_color3()
    local v_u_30 = v_u_6:get_default_fever_color():to_color3()
    v_u_1:get_base_fn(v25, "set_game_noteskin_colors")
    v25.set_game_noteskin_colors = function(_, p31, p32) --[[ Name: set_game_noteskin_colors ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30, (ref 3): v_u_27 ]]
        v_u_29 = p31
        v_u_30 = p32
        v_u_27.Color = v_u_29
    end;
    v_u_1:get_base_fn(v25, "on_press")
    v25.on_press = function(_) --[[ Name: on_press ]] --[[ Line: 94 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_26 ]]
        if p_u_21._player_settings_manager:get_key(v_u_4.Key.BrightnessSettings) == v_u_5.Dark then
            v_u_26 = 0.35
        else
            v_u_26 = 0
        end;
    end;
    v_u_1:get_base_fn(v25, "on_release")
    v25.on_release = function(_) --[[ Name: on_release ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_12 ]]
        v_u_26 = v_u_12
    end;
    v_u_1:get_base_fn(v25, "update")
    v25.update = function(_, p33) --[[ Name: update ]] --[[ Line: 109 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_28, (ref 3): v_u_26, (ref 4): v_u_8, (copy 5): p_u_21, (copy 6): p_u_22, (ref 7): v_u_27, (ref 8): v_u_30, (ref 9): v_u_29 ]]
        local v34 = v_u_7:Expt(v_u_28.Transparency, v_u_26, v_u_7:NormalizedDefaultExptValueInSeconds(0.45), p33)
        if v34 ~= v_u_28.Transparency then
            v_u_28.Transparency = v34
        end;
        if v_u_8:get_server_game_instance_player_powerbar_active(p_u_21._players._slots:get(p_u_22)) then
            v_u_27.Color = v_u_30
        else
            v_u_27.Color = v_u_29
        end;
    end;
    v_u_27 = v_u_24.Outer
    v_u_27.Transparency = 0.65
    v_u_28 = v_u_27.InteriorGlow
    v_u_28.Transparency = v_u_12
    return v25;
end;
local v_u_35 = v2:invalid_material_id()
v_u_13.new = function(_) --[[ Name: new ]] --[[ Line: 132 ]]
    --[[ Upvalues: (copy 1): f_create_default_trigger_button_asset, (copy 2): v_u_35, (copy 3): v_u_9 ]]
    local v40 = {
        ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 135 ]]
            return "";
        end,
        ["get_icon"] = function(_) --[[ Name: get_icon ]] --[[ Line: 136 ]]
            return "";
        end,
        ["load_stage"] = function(_, _) end,
        ["setup_stage"] = function(_, _) end,
        ["teardown_stage"] = function(_, _) end,
        ["game_update"] = function(_, _, _) end,
        ["create_shine_for_slot_at_cframe"] = function(_, _, _, _) end,
        ["on_switch_focus_slot"] = function(_, _) end,
        ["should_do_game_start_zoom_in_effect"] = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 145 ]]
            return true, 75, 85, 1.25;
        end,
        ["game_camera_transition"] = function(_, _) end,
        ["process_character_location_for_slot"] = function(_, p36, p37, p38, p39) --[[ Name: process_character_location_for_slot ]] --[[ Line: 158 ]]
            return p36, p37, p38, p39;
        end
    }
    v40.create_trigger_button_asset = function(_, p41, p42, p43) --[[ Name: create_trigger_button_asset ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): f_create_default_trigger_button_asset ]]
        return f_create_default_trigger_button_asset(p41, p42, p43);
    end;
    local v_u_44 = v_u_35
    v40.get_material_id = function(_) --[[ Name: get_material_id ]] --[[ Line: 149 ]]
        --[[ Upvalues: (ref 1): v_u_44 ]]
        return v_u_44;
    end;
    v40.set_material_id = function(_, p45) --[[ Name: set_material_id ]] --[[ Line: 150 ]]
        --[[ Upvalues: (ref 1): v_u_44, (ref 2): v_u_35, (ref 3): v_u_9 ]]
        if v_u_44 == v_u_35 then
            v_u_44 = p45
        else
            v_u_9:errf("set_material_id already set")
        end;
    end;
    return v40;
end;
return v_u_13;
