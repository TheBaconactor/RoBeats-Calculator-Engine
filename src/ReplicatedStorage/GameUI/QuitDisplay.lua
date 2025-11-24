-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_5 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_6 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_7 = require(game.ReplicatedStorage.Local.AudioManager)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v9 = {}
local v_u_10 = {
    ["Keyboard"] = 1,
    ["Mobile"] = 2,
    ["Tutorial"] = 3
}
v9.new = function(_, p_u_11) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_10, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_6, (copy 6): v_u_7, (copy 7): v_u_5, (copy 8): v_u_2, (copy 9): v_u_8 ]]
    local v12 = v_u_3:SPUIObjectBase()
    local l_Keyboard_0 = v_u_10.Keyboard
    local l__spui_0 = p_u_11._spui
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = nil
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local function _(p21) --[[ Name: set_visible ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_18, (ref 3): v_u_19 ]]
        if v_u_20 ~= p21 then
            v_u_20 = p21
            for _, v22 in v_u_18:key_itr() do
                v22.Visible = p21
            end;
            for _, v23 in v_u_19:key_itr() do
                v23.Visible = p21
            end;
        end;
    end;
    local v_u_24 = ""
    local v_u_25 = ""
    local function _(p26) --[[ Name: set_text ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): l_Keyboard_0, (ref 2): v_u_10, (ref 3): v_u_25, (ref 4): v_u_15 ]]
        if l_Keyboard_0 ~= v_u_10.Tutorial then
            if v_u_25 ~= p26 then
                v_u_25 = p26
                v_u_15.Text = v_u_25
            end;
        end;
    end;
    local v_u_27 = {
        ["TextColor3"] = v_u_1:color3(229, 255, 254),
        ["TextStrokeColor3"] = v_u_1:color3(0, 33, 255)
    }
    local v_u_28 = {
        ["TextColor3"] = v_u_1:color3(253, 255, 105),
        ["TextStrokeColor3"] = v_u_1:color3(160, 65, 6)
    }
    local function _(p29) --[[ Name: set_colors ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): l_Keyboard_0, (ref 2): v_u_10, (ref 3): v_u_15 ]]
        if l_Keyboard_0 ~= v_u_10.Tutorial then
            if p29 ~= nil then
                v_u_15.TextColor3 = p29.TextColor3
                v_u_15.TextStrokeColor3 = p29.TextStrokeColor3
            end;
        end;
    end;
    local function _() --[[ Name: get_chatbar_size_nxy ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        return 105 / v_u_1:screen_size().X, 37 / v_u_1:screen_size().Y;
    end;
    v12.cons = function(p30) --[[ Name: cons ]] --[[ Line: 85 ]]
        --[[ Upvalues: (copy 1): p_u_11, (ref 2): l_Keyboard_0, (ref 3): v_u_10, (ref 4): v_u_1, (ref 5): v_u_24, (ref 6): v_u_13, (ref 7): v_u_18, (ref 8): v_u_19, (ref 9): v_u_17, (ref 10): v_u_16, (ref 11): v_u_4, (ref 12): v_u_14, (ref 13): v_u_15, (ref 14): v_u_20, (ref 15): v_u_25, (copy 16): v_u_27 ]]
        if p_u_11:is_tutorial() then
            l_Keyboard_0 = v_u_10.Tutorial
        elseif v_u_1:is_mobile() then
            l_Keyboard_0 = v_u_10.Mobile
            v_u_24 = "Hold here to quit."
        else
            l_Keyboard_0 = v_u_10.Keyboard
            v_u_24 = "Hold \"Backspace\" to quit."
        end;
        if l_Keyboard_0 == v_u_10.Tutorial then
            v_u_13 = game.ReplicatedStorage.WorldUIProto.TutorialQuitDisplay:Clone()
        elseif l_Keyboard_0 == v_u_10.Mobile then
            v_u_13 = game.ReplicatedStorage.WorldUIProto.QuitDisplayMobile:Clone()
        else
            v_u_13 = game.ReplicatedStorage.WorldUIProto.QuitDisplay:Clone()
        end;
        v_u_18 = v_u_1:get_list_of_children_of_classname(v_u_13, "ImageLabel")
        v_u_19 = v_u_1:get_list_of_children_of_classname(v_u_13, "TextLabel")
        v_u_17 = v_u_13.PrimaryPart.Size
        v_u_16 = v_u_17
        v_u_13.Parent = v_u_4:get_world_ui_folder()
        v_u_14 = v_u_13.PrimaryPart
        v_u_15 = v_u_14.SurfaceGui.Frame.TextLabel
        if v_u_20 ~= false then
            v_u_20 = false
            for _, v31 in v_u_18:key_itr() do
                v31.Visible = false
            end;
            for _, v32 in v_u_19:key_itr() do
                v32.Visible = false
            end;
        end;
        if l_Keyboard_0 ~= v_u_10.Tutorial and v_u_25 ~= "" then
            v_u_25 = ""
            v_u_15.Text = v_u_25
        end;
        local v33 = v_u_27
        if l_Keyboard_0 ~= v_u_10.Tutorial and v33 ~= nil then
            v_u_15.TextColor3 = v33.TextColor3
            v_u_15.TextStrokeColor3 = v33.TextStrokeColor3
        end;
        p30:layout()
    end;
    local v_u_34 = false
    local v_u_35 = 1
    local v_u_36 = v_u_3:cframe_params_default()
    v12.layout = function(p37) --[[ Name: layout ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): l_Keyboard_0, (ref 2): v_u_10, (ref 3): v_u_1, (copy 4): l__spui_0, (ref 5): v_u_35, (copy 6): v_u_36, (ref 7): v_u_13 ]]
        if l_Keyboard_0 == v_u_10.Tutorial then
            local v38 = 105 / v_u_1:screen_size().X
            p37:opt_rescale_to_max_nxy(l__spui_0, v38 * 3, 37 / v_u_1:screen_size().Y * 1.5, v_u_35)
            v_u_36.PositionNXY:set(v38, 0)
            v_u_36.OffsetXYZ:from_vector3(p37:anchored_offset(0, 0))
        else
            local v39 = 105 / v_u_1:screen_size().X
            local v40 = 37 / v_u_1:screen_size().Y
            p37:opt_rescale_to_max_nxy(l__spui_0, 0.3, 0.3)
            v_u_36.PositionNXY:set(v39, v40 / 2)
            v_u_36.OffsetXYZ:from_vector3(p37:anchored_offset(0, 0.5))
        end;
        local v41, v42 = p37:opt_update_cframe_params(l__spui_0, v_u_36)
        if v41 == true then
            v_u_13:SetPrimaryPartCFrame(v42)
        end;
    end;
    v12.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 148 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        v_u_13.Parent = nil
    end;
    local v_u_43 = 0
    v12.update = function(p44, p45, p46) --[[ Name: update ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_20, (ref 5): v_u_18, (ref 6): v_u_19, (ref 7): v_u_43, (copy 8): l__spui_0, (ref 9): v_u_34, (ref 10): v_u_5, (ref 11): v_u_2, (ref 12): l_Keyboard_0, (ref 13): v_u_10, (ref 14): v_u_35, (ref 15): v_u_8, (ref 16): v_u_25, (ref 17): v_u_15, (copy 18): v_u_28, (ref 19): v_u_24, (copy 20): v_u_27 ]]
        if p_u_11:is_spectate() then
            return;
        elseif p46._players._slots:count() > 1 or (p_u_11:get_current_mode() ~= v_u_6.Game or p_u_11:es_gamelocal_get_audiomanager():get_current_mode() ~= v_u_7.Mode.Playing) then
            if v_u_20 ~= false then
                v_u_20 = false
                for _, v47 in v_u_18:key_itr() do
                    v47.Visible = false
                end;
                for _, v48 in v_u_19:key_itr() do
                    v48.Visible = false
                end;
            end;
            v_u_43 = 0
        else
            if v_u_20 ~= true then
                v_u_20 = true
                for _, v49 in v_u_18:key_itr() do
                    v49.Visible = true
                end;
                for _, v50 in v_u_19:key_itr() do
                    v50.Visible = true
                end;
            end;
            if p_u_11._input:get_has_frame_focused_element() == false and p44:get_nrect(l__spui_0):contains_vec2((l__spui_0:get_cursor_nxy())) then
                v_u_34 = true
            else
                v_u_34 = false
            end;
            local v51 = v_u_43 > 0 and v_u_34
            if v51 then
                v51 = p_u_11._input:control_just_released(v_u_5.KEY_CLICK)
            end;
            if v_u_43 <= 0 then
                if p_u_11._input:control_just_pressed(v_u_5.KEY_GAME_QUIT) or v_u_34 and p_u_11._input:control_just_pressed(v_u_5.KEY_CLICK) then
                    v_u_43 = v_u_43 + v_u_2:TimescaleToDeltaTime(p45)
                else
                    v_u_43 = 0
                end;
            elseif p_u_11._input:control_pressed(v_u_5.KEY_GAME_QUIT) or v_u_34 and p_u_11._input:control_pressed(v_u_5.KEY_CLICK) then
                v_u_43 = v_u_43 + v_u_2:TimescaleToDeltaTime(p45)
            else
                v_u_43 = 0
            end;
            if l_Keyboard_0 == v_u_10.Tutorial then
                v_u_35 = v_u_2:expt_sec(v_u_35, v_u_43 > 0 and 1.15 or (v_u_34 and 1.1 or 1), 0.25, p45)
                if v_u_43 > 2 or v51 then
                    p_u_11:early_quit()
                    p_u_11._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                end;
            elseif v_u_43 > 0 then
                if l_Keyboard_0 == v_u_10.Mobile then
                    local v52 = string.format("Hold here for %d more seconds to quit.", (math.ceil((math.max(0, 2 - v_u_43)))))
                    if l_Keyboard_0 ~= v_u_10.Tutorial and v_u_25 ~= v52 then
                        v_u_25 = v52
                        v_u_15.Text = v_u_25
                    end;
                else
                    local v53 = string.format("Hold \"%s\" for %d more seconds to quit.", "Backspace", (math.ceil((math.max(0, 2 - v_u_43)))))
                    if l_Keyboard_0 ~= v_u_10.Tutorial and v_u_25 ~= v53 then
                        v_u_25 = v53
                        v_u_15.Text = v_u_25
                    end;
                end;
                local v54 = v_u_28
                if l_Keyboard_0 ~= v_u_10.Tutorial and v54 ~= nil then
                    v_u_15.TextColor3 = v54.TextColor3
                    v_u_15.TextStrokeColor3 = v54.TextStrokeColor3
                end;
                if v_u_43 >= 2 then
                    p_u_11:early_quit()
                end;
            else
                v_u_43 = 0
                local v55 = v_u_24
                if l_Keyboard_0 ~= v_u_10.Tutorial and v_u_25 ~= v55 then
                    v_u_25 = v55
                    v_u_15.Text = v_u_25
                end;
                local v56 = v_u_27
                if l_Keyboard_0 ~= v_u_10.Tutorial and v56 ~= nil then
                    v_u_15.TextColor3 = v56.TextColor3
                    v_u_15.TextStrokeColor3 = v56.TextStrokeColor3
                end;
            end;
            p44:layout()
        end;
    end;
    v12.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 229 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        return v_u_13.PrimaryPart.Position;
    end;
    v12.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 232 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        return v_u_17;
    end;
    v12.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 235 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16;
    end;
    v12.set_size = function(_, p57) --[[ Name: set_size ]] --[[ Line: 238 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_14 ]]
        v_u_16 = p57
        v_u_14.Size = Vector3.new(p57.X, p57.Y, 0)
    end;
    v12:cons()
    return v12;
end;
return v9;
