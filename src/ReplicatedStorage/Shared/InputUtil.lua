-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local s_GamepadService_0 = game:GetService("GamepadService")
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
v9:require_client(function() --[[ Line: 13 ]]
    --[[ Upvalues: (ref 1): v_u_10 ]]
    v_u_10 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
end)
local v_u_11 = {
    ["KEY_TRACK1"] = 0,
    ["KEY_TRACK2"] = 1,
    ["KEY_TRACK3"] = 2,
    ["KEY_TRACK4"] = 3,
    ["KEY_POWERBAR_TRIGGER"] = 4,
    ["KEY_GAME_QUIT"] = 5,
    ["KEY_UP"] = 10,
    ["KEY_DOWN"] = 11,
    ["KEY_LEFT"] = 12,
    ["KEY_RIGHT"] = 13,
    ["KEY_A"] = 14,
    ["KEY_B"] = 15,
    ["KEY_MOD1"] = 21,
    ["KEY_MENU_OPEN"] = 31,
    ["KEY_MENU_ENTER"] = 32,
    ["KEY_MENU_BACK"] = 33,
    ["KEY_MENU_MATCHMAKING_CHAT_FOCUS"] = 34,
    ["KEY_CHAT_WINDOW_FOCUS"] = 35,
    ["KEY_MENU_SPUITEXTINPUT_ESC"] = 36,
    ["KEY_CLICK"] = 41,
    ["KEY_SCROLL_UP"] = 51,
    ["KEY_SCROLL_DOWN"] = 52,
    ["KEY_DEBUG_1"] = 100,
    ["KEY_DEBUG_2"] = 101,
    ["KEY_DEBUG_3"] = 102,
    ["KEY_DEBUG_4"] = 103,
    ["KEY_EDITOR_PLAY_PAUSE"] = 500,
    ["KEY_EDITOR_TIME_FORWARD"] = 501,
    ["KEY_EDITOR_TIME_BACK"] = 502,
    ["KEY_EDITOR_MODIFIER_SHIFT"] = 503,
    ["KEY_EDITOR_SELECT_MODE"] = 504,
    ["KEY_EDITOR_ADD_MODE"] = 505,
    ["KEY_EDITOR_DELETE_MODE"] = 506,
    ["KEY_EDITOR_UNDO"] = 507,
    ["KEY_EDITOR_REDO"] = 508,
    ["KEY_EDITOR_MODIFIER_CTRL"] = 509,
    ["KEY_EDITOR_MODIFIER_ALT"] = 510,
    ["KEY_EDITOR_TOGGLE_HOLD_BEAT_LENGTH"] = 511,
    ["KEY_EDITOR_COPY"] = 512,
    ["KEY_EDITOR_PASTE_MODE"] = 513,
    ["KEYCODE_TOUCH_TRACK1"] = 10001,
    ["KEYCODE_TOUCH_TRACK2"] = 10002,
    ["KEYCODE_TOUCH_TRACK3"] = 10003,
    ["KEYCODE_TOUCH_TRACK4"] = 10004
}
local v_u_12 = v_u_3:new({
    v_u_11.KEY_TRACK1,
    v_u_11.KEY_TRACK2,
    v_u_11.KEY_TRACK3,
    v_u_11.KEY_TRACK4
})
local v_u_13 = v_u_2:new():add_set_from_table_list(v_u_12:get_table())
v_u_11.get_track_index_list = function(_) --[[ Name: get_track_index_list ]] --[[ Line: 82 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return v_u_12;
end;
v_u_11.get_track_index_set = function(_) --[[ Name: get_track_index_set ]] --[[ Line: 83 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    return v_u_13;
end;
local v_u_14 = v_u_2:new()
local v_u_15 = v_u_2:new()
local v_u_16 = v_u_10
for v17 = 1, v_u_12:count() do
    v_u_14:add(v_u_12:get(v17), v17)
    v_u_15:add(v17, v_u_12:get(v17))
end;
v_u_11.get_key_to_track_index = function(_) --[[ Name: get_key_to_track_index ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14;
end;
v_u_11.get_track_index_to_key = function(_) --[[ Name: get_track_index_to_key ]] --[[ Line: 94 ]]
    --[[ Upvalues: (copy 1): v_u_15 ]]
    return v_u_15;
end;
local v_u_18 = v_u_2:new():add_set_from_table_list({
    Enum.UserInputType.Gamepad1,
    Enum.UserInputType.Gamepad2,
    Enum.UserInputType.Gamepad3,
    Enum.UserInputType.Gamepad4,
    Enum.UserInputType.Gamepad5,
    Enum.UserInputType.Gamepad6,
    Enum.UserInputType.Gamepad7,
    Enum.UserInputType.Gamepad8
})
local v_u_19 = v_u_2:new():add_set_from_table_list({ Enum.KeyCode.ButtonA })
v_u_11.new = function(_) --[[ Name: new ]] --[[ Line: 104 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_8, (copy 5): v_u_3, (copy 6): v_u_7, (copy 7): v_u_18, (copy 8): v_u_19, (copy 9): s_GamepadService_0, (copy 10): v_u_4, (ref 11): v_u_16, (copy 12): v_u_6, (copy 13): v_u_5, (copy 14): v_u_15, (copy 15): v_u_12 ]]
    local v_u_20 = {
        ["update"] = function(_, _) end
    }
    v_u_20.get_track_index_list = function(_) --[[ Name: get_track_index_list ]] --[[ Line: 107 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        return v_u_11:get_track_index_list();
    end;
    v_u_20.get_track_index_set = function(_) --[[ Name: get_track_index_set ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        return v_u_11:get_track_index_set();
    end;
    v_u_20.get_key_to_track_index = function(_) --[[ Name: get_key_to_track_index ]] --[[ Line: 109 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        return v_u_11:get_key_to_track_index();
    end;
    v_u_20.get_track_index_to_key = function(_) --[[ Name: get_track_index_to_key ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        return v_u_11:get_track_index_to_key();
    end;
    local s_UserInputService_0 = game:GetService("UserInputService")
    local v_u_21 = v_u_2:new()
    local v_u_22 = v_u_2:new()
    local v_u_23 = v_u_2:new()
    local v_u_24 = false
    local v_u_25 = false
    local v_u_26 = false
    local v_u_27 = false
    local v_u_28 = 0
    local v_u_29 = v_u_2:new()
    local v_u_30 = v_u_1:is_console_ui() == true
    local v_u_31 = v_u_8:new()
    local v_u_32 = v_u_3:new()
    local v_u_33 = false
    local v_u_34 = false
    local v_u_35 = 0
    v_u_20.is_controller_active = function(_) --[[ Name: is_controller_active ]] --[[ Line: 138 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    v_u_20.get_controller_track_enum_to_keycodes = function(_) --[[ Name: get_controller_track_enum_to_keycodes ]] --[[ Line: 139 ]]
        --[[ Upvalues: (copy 1): v_u_31 ]]
        return v_u_31;
    end;
    v_u_20.get_controller_enable_virtual_cursor_keycode_list = function(_) --[[ Name: get_controller_enable_virtual_cursor_keycode_list ]] --[[ Line: 140 ]]
        --[[ Upvalues: (copy 1): v_u_32 ]]
        return v_u_32;
    end;
    local l_ScreenGui_0 = Instance.new("ScreenGui")
    l_ScreenGui_0.Name = "InputUtil"
    l_ScreenGui_0.ResetOnSpawn = false
    l_ScreenGui_0.DisplayOrder = 0
    spawn(function() --[[ Line: 148 ]]
        --[[ Upvalues: (copy 1): l_ScreenGui_0 ]]
        l_ScreenGui_0.Parent = game.Players.LocalPlayer.PlayerGui
    end)
    local l_TextLabel_0 = Instance.new("TextLabel", l_ScreenGui_0)
    l_TextLabel_0.AnchorPoint = Vector2.new(0, 1)
    l_TextLabel_0.BackgroundTransparency = 1
    l_TextLabel_0.Position = UDim2.new(0, 0, 1, 0)
    l_TextLabel_0.Size = UDim2.new(1, 0, 0, 45)
    l_TextLabel_0.Font = Enum.Font.SourceSansBold
    l_TextLabel_0.Text = ""
    l_TextLabel_0.TextSize = 42
    l_TextLabel_0.TextColor3 = Color3.new(1, 1, 1)
    l_TextLabel_0.TextStrokeColor3 = Color3.new(0.2, 0.2, 0.2)
    l_TextLabel_0.TextStrokeTransparency = 0
    l_TextLabel_0.TextTransparency = 0
    l_TextLabel_0.TextXAlignment = Enum.TextXAlignment.Center
    l_TextLabel_0.TextYAlignment = Enum.TextYAlignment.Center
    l_TextLabel_0.AutoLocalize = false
    l_TextLabel_0.Text = ""
    local function f_update_controller_cursor_hint_display() --[[ Name: update_controller_cursor_hint_display ]] --[[ Line: 170 ]]
        --[[ Upvalues: (copy 1): v_u_32, (ref 2): l_TextLabel_0, (copy 3): v_u_20 ]]
        if v_u_32:count() == 0 then
            l_TextLabel_0.Text = "Use the Virtual Cursor to interact with the menu."
        else
            local v36 = ""
            for v37, v38 in v_u_32:key_itr() do
                if v37 > 1 and v37 < v_u_32:count() then
                    v36 = v36 .. ", "
                elseif v37 > 1 and v37 == v_u_32:count() then
                    v36 = v36 .. " or "
                end;
                v36 = v36 .. v_u_20:button_keycode_to_name(v38)
            end;
            l_TextLabel_0.Text = string.format("Press %s to show the cursor.", v36)
        end;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 189 ]]
        --[[ Upvalues: (ref 1): l_TextLabel_0, (copy 2): s_UserInputService_0, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_26, (copy 6): v_u_20, (ref 7): v_u_11, (ref 8): v_u_7, (ref 9): v_u_18, (ref 10): v_u_33, (ref 11): v_u_34, (ref 12): v_u_35, (ref 13): v_u_19, (copy 14): v_u_32, (ref 15): s_GamepadService_0, (ref 16): v_u_27, (ref 17): v_u_28, (ref 18): v_u_30 ]]
        l_TextLabel_0.Text = ""
        l_TextLabel_0.Visible = false
        s_UserInputService_0.TextBoxFocused:connect(function(_) --[[ Line: 195 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            v_u_24 = true
        end)
        s_UserInputService_0.TextBoxFocusReleased:connect(function(_) --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            v_u_25 = true
        end)
        s_UserInputService_0.InputBegan:connect(function(p39, _) --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_20, (ref 3): v_u_11, (ref 4): v_u_7, (ref 5): v_u_18, (ref 6): v_u_33, (ref 7): v_u_34, (ref 8): v_u_35, (ref 9): v_u_19, (ref 10): v_u_32, (ref 11): s_GamepadService_0 ]]
            if p39.UserInputType == Enum.UserInputType.Keyboard then
                if v_u_26 ~= true then
                    v_u_20:input_began(p39.KeyCode)
                end;
            elseif p39.UserInputType == Enum.UserInputType.MouseButton1 then
                v_u_20:input_began(v_u_11.KEY_CLICK)
                return;
            elseif p39.UserInputType == Enum.UserInputType.Touch then
                v_u_20:input_began(v_u_11.KEY_CLICK)
                v_u_20:touch_began(p39.Position.X, p39.Position.Y)
            elseif v_u_7.ControllerInputEnabled == true and v_u_18:contains(p39.UserInputType) then
                if v_u_33 == true and v_u_20:get_available_controller_keys():contains(p39.KeyCode) then
                    v_u_34 = true
                    v_u_35 = p39.KeyCode
                    return;
                end;
                if v_u_19:contains(p39.KeyCode) then
                    v_u_20:input_began(v_u_11.KEY_CLICK)
                elseif v_u_32:contains(p39.KeyCode) then
                    if s_GamepadService_0.GamepadCursorEnabled == false then
                        s_GamepadService_0:EnableGamepadCursor(nil)
                    else
                        s_GamepadService_0:DisableGamepadCursor()
                    end;
                end;
                v_u_20:input_began(p39.KeyCode)
            end;
        end)
        s_UserInputService_0.InputChanged:connect(function(p40, _) --[[ Line: 239 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            if p40.UserInputType == Enum.UserInputType.Touch then
                v_u_20:touch_changed(p40.Position.X, p40.Position.Y)
            end;
        end)
        s_UserInputService_0.InputEnded:connect(function(p41, _) --[[ Line: 245 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_20, (ref 5): v_u_11, (ref 6): v_u_7, (ref 7): v_u_18, (ref 8): v_u_33 ]]
            if p41.UserInputType == Enum.UserInputType.Keyboard then
                if v_u_26 == true then
                    v_u_27 = true
                    v_u_28 = p41.KeyCode
                else
                    v_u_20:input_ended(p41.KeyCode)
                end;
            elseif p41.UserInputType == Enum.UserInputType.MouseButton1 then
                v_u_20:input_ended(v_u_11.KEY_CLICK)
                return;
            elseif p41.UserInputType == Enum.UserInputType.Touch then
                v_u_20:input_ended(v_u_11.KEY_CLICK)
                v_u_20:touch_ended(p41.Position.X, p41.Position.Y)
            elseif v_u_7.ControllerInputEnabled == true and v_u_18:contains(p41.UserInputType) then
                if v_u_33 == true and v_u_20:get_available_controller_keys():contains(p41.KeyCode) then
                    return;
                end;
                if p41.KeyCode == Enum.KeyCode.ButtonA then
                    v_u_20:input_ended(v_u_11.KEY_CLICK)
                end;
                v_u_20:input_ended(p41.KeyCode)
            end;
        end)
        game.Players.LocalPlayer:GetMouse().WheelForward:connect(function() --[[ Line: 272 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_11 ]]
            v_u_20:input_began(v_u_11.KEY_SCROLL_UP)
        end)
        game.Players.LocalPlayer:GetMouse().WheelBackward:connect(function() --[[ Line: 275 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_11 ]]
            v_u_20:input_began(v_u_11.KEY_SCROLL_DOWN)
        end)
        s_UserInputService_0.LastInputTypeChanged:connect(function(p42) --[[ Line: 279 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_18, (ref 3): v_u_30 ]]
            if v_u_7.ControllerInputEnabled == true then
                v_u_30 = v_u_18:contains(p42)
            end;
        end)
    end;
    local v_u_43 = 0.25
    local v_u_44 = 0.5
    local v_u_45 = 0.75
    v_u_20.set_touch_track_ends = function(_, p46, p47, p48) --[[ Name: set_touch_track_ends ]] --[[ Line: 290 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_44, (ref 3): v_u_45 ]]
        v_u_43 = p46
        v_u_44 = p47
        v_u_45 = p48
    end;
    v_u_20.get_touch_track_ends = function(_) --[[ Name: get_touch_track_ends ]] --[[ Line: 296 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_44, (ref 3): v_u_45 ]]
        return v_u_43, v_u_44, v_u_45;
    end;
    local function _(p49, _) --[[ Name: get_touch_keycode ]] --[[ Line: 298 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_43, (ref 3): v_u_11, (ref 4): v_u_44, (ref 5): v_u_45 ]]
        local v50 = p49 / v_u_1:screen_size().X
        if v50 <= v_u_43 then
            return v_u_11.KEYCODE_TOUCH_TRACK1;
        elseif v50 <= v_u_44 then
            return v_u_11.KEYCODE_TOUCH_TRACK2;
        elseif v50 <= v_u_45 then
            return v_u_11.KEYCODE_TOUCH_TRACK3;
        else
            return v_u_11.KEYCODE_TOUCH_TRACK4;
        end;
    end;
    local v_u_51 = 0
    local v_u_52 = v_u_3:new()
    local function f_get_nearest_touch(p53) --[[ Name: get_nearest_touch ]] --[[ Line: 313 ]]
        --[[ Upvalues: (copy 1): v_u_52 ]]
        if v_u_52:count() == 0 then
            return nil;
        end;
        local v54 = v_u_52:get(1)
        local v55 = p53:distance_to(v54)
        local v56 = 1
        for v57 = 2, v_u_52:count() do
            local v58 = v_u_52:get(v57)
            local v59 = p53:distance_to(v58)
            if v59 < v55 then
                v56 = v57
                v54 = v58
                v55 = v59
            end;
        end;
        return v54, v56;
    end;
    v_u_20.get_touch_move_count = function(_) --[[ Name: get_touch_move_count ]] --[[ Line: 330 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51;
    end;
    v_u_20.touch_began = function(p60, p61, p62) --[[ Name: touch_began ]] --[[ Line: 332 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_43, (ref 3): v_u_11, (ref 4): v_u_44, (ref 5): v_u_45, (copy 6): v_u_52, (ref 7): v_u_4, (ref 8): v_u_51 ]]
        local v63 = p61 / v_u_1:screen_size().X
        local v64
        if v63 <= v_u_43 then
            v64 = v_u_11.KEYCODE_TOUCH_TRACK1
        elseif v63 <= v_u_44 then
            v64 = v_u_11.KEYCODE_TOUCH_TRACK2
        elseif v63 <= v_u_45 then
            v64 = v_u_11.KEYCODE_TOUCH_TRACK3
        else
            v64 = v_u_11.KEYCODE_TOUCH_TRACK4
        end;
        v_u_52:push_back(v_u_4:new(p61, p62, 0))
        v_u_51 = 0
        p60:input_began(v64)
    end;
    v_u_20.touch_changed = function(p65, p66, p67) --[[ Name: touch_changed ]] --[[ Line: 339 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): f_get_nearest_touch, (ref 3): v_u_1, (ref 4): v_u_43, (ref 5): v_u_11, (ref 6): v_u_44, (ref 7): v_u_45, (ref 8): v_u_51 ]]
        local v68 = v_u_4:new(p66, p67)
        local v69 = f_get_nearest_touch(v68)
        if v69 ~= nil then
            local v70 = v69._x / v_u_1:screen_size().X
            local v71
            if v70 <= v_u_43 then
                v71 = v_u_11.KEYCODE_TOUCH_TRACK1
            elseif v70 <= v_u_44 then
                v71 = v_u_11.KEYCODE_TOUCH_TRACK2
            elseif v70 <= v_u_45 then
                v71 = v_u_11.KEYCODE_TOUCH_TRACK3
            else
                v71 = v_u_11.KEYCODE_TOUCH_TRACK4
            end;
            local v72 = v68._x / v_u_1:screen_size().X
            local v73
            if v72 <= v_u_43 then
                v73 = v_u_11.KEYCODE_TOUCH_TRACK1
            elseif v72 <= v_u_44 then
                v73 = v_u_11.KEYCODE_TOUCH_TRACK2
            elseif v72 <= v_u_45 then
                v73 = v_u_11.KEYCODE_TOUCH_TRACK3
            else
                v73 = v_u_11.KEYCODE_TOUCH_TRACK4
            end;
            if v71 ~= v73 then
                p65:input_ended(v71)
                p65:input_began(v73)
            end;
            v_u_51 = v69._z
            v69:set(p66, p67, v69._z + 1)
        end;
    end;
    v_u_20.touch_ended = function(p74, p75, p76) --[[ Name: touch_ended ]] --[[ Line: 354 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): f_get_nearest_touch, (copy 3): v_u_52, (ref 4): v_u_51, (ref 5): v_u_1, (ref 6): v_u_43, (ref 7): v_u_11, (ref 8): v_u_44, (ref 9): v_u_45 ]]
        local v77, v78 = f_get_nearest_touch((v_u_4:new(p75, p76)))
        if v77 ~= nil then
            v_u_52:remove_at(v78)
            v_u_51 = v77._z
            local v79 = v77._x / v_u_1:screen_size().X
            local v80
            if v79 <= v_u_43 then
                v80 = v_u_11.KEYCODE_TOUCH_TRACK1
            elseif v79 <= v_u_44 then
                v80 = v_u_11.KEYCODE_TOUCH_TRACK2
            elseif v79 <= v_u_45 then
                v80 = v_u_11.KEYCODE_TOUCH_TRACK3
            else
                v80 = v_u_11.KEYCODE_TOUCH_TRACK4
            end;
            p74:input_ended(v80)
        end;
    end;
    v_u_20.input_began = function(_, p81) --[[ Name: input_began ]] --[[ Line: 366 ]]
        --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_21 ]]
        v_u_22:add(p81, true)
        v_u_21:add(p81, true)
    end;
    v_u_20.input_ended = function(_, p82) --[[ Name: input_ended ]] --[[ Line: 371 ]]
        --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_23 ]]
        v_u_22:remove(p82)
        v_u_23:add(p82, true)
    end;
    local v_u_83 = v_u_4:new(0, 0)
    local v_u_84 = v_u_4:new()
    v_u_20.get_cursor_delta = function(_) --[[ Name: get_cursor_delta ]] --[[ Line: 379 ]]
        --[[ Upvalues: (copy 1): v_u_84, (copy 2): v_u_83 ]]
        local v85 = game.Players.LocalPlayer:GetMouse()
        v_u_84:set(v85.X - v_u_83._x, v85.Y - v_u_83._y)
        return v_u_84:to_vector3();
    end;
    local v_u_86 = false
    local v_u_87 = -1
    v_u_20.set_has_frame_focused_element = function(p88, p89) --[[ Name: set_has_frame_focused_element ]] --[[ Line: 391 ]]
        --[[ Upvalues: (ref 1): v_u_86, (ref 2): v_u_87 ]]
        v_u_86 = p89
        if p89 == true then
            local v90 = p88:get_frame_index_state()
            if v90 then
                v_u_87 = v90:get_test_val()
            else
                v_u_87 = -1
            end;
        else
            v_u_87 = -1
            return;
        end;
    end;
    v_u_20.get_has_frame_focused_element = function(_) --[[ Name: get_has_frame_focused_element ]] --[[ Line: 404 ]]
        --[[ Upvalues: (ref 1): v_u_86 ]]
        return v_u_86;
    end;
    local v_u_91 = true
    v_u_20.is_mouse_visible = function(_) --[[ Name: is_mouse_visible ]] --[[ Line: 409 ]]
        --[[ Upvalues: (ref 1): v_u_91 ]]
        return v_u_91;
    end;
    v_u_20.set_mouse_visible = function(p92, p93) --[[ Name: set_mouse_visible ]] --[[ Line: 410 ]]
        --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_7, (ref 3): s_GamepadService_0, (copy 4): s_UserInputService_0 ]]
        v_u_91 = p93
        if v_u_7.ControllerInputEnabled == true and p92:is_controller_active() then
            if s_GamepadService_0.GamepadCursorEnabled == true then
                s_UserInputService_0.MouseIconEnabled = true
            else
                s_UserInputService_0.MouseIconEnabled = false
            end;
        else
            s_UserInputService_0.MouseIconEnabled = p93
            return;
        end;
    end;
    local v_u_94 = false
    v_u_20.set_keyboard_focused_mode = function(_, p95) --[[ Name: set_keyboard_focused_mode ]] --[[ Line: 424 ]]
        --[[ Upvalues: (ref 1): v_u_94, (ref 2): v_u_7, (ref 3): s_GamepadService_0 ]]
        v_u_94 = p95
        if v_u_94 == true and (v_u_7.ControllerInputEnabled == true and s_GamepadService_0.GamepadCursorEnabled) then
            s_GamepadService_0:DisableGamepadCursor()
        end;
    end;
    v_u_20.post_update = function(p96) --[[ Name: post_update ]] --[[ Line: 442 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_94, (ref 3): v_u_11, (copy 4): v_u_83, (ref 5): v_u_7, (ref 6): v_u_30, (ref 7): v_u_91, (copy 8): s_UserInputService_0, (ref 9): s_GamepadService_0, (ref 10): l_TextLabel_0, (copy 11): v_u_21, (copy 12): v_u_23, (copy 13): v_u_22, (ref 14): v_u_25, (ref 15): v_u_24, (ref 16): v_u_16, (ref 17): v_u_86, (ref 18): v_u_6, (ref 19): v_u_87 ]]
        local v97 = game.Players.LocalPlayer:GetMouse()
        if v_u_1:is_mobile() == false then
            if v_u_94 == true and (p96:control_pressed(v_u_11.KEY_TRACK1) or (p96:control_pressed(v_u_11.KEY_TRACK2) or (p96:control_pressed(v_u_11.KEY_TRACK3) or p96:control_pressed(v_u_11.KEY_TRACK4)))) then
                p96:set_mouse_visible(false)
            elseif v97.X ~= v_u_83._x or v97.Y ~= v_u_83._y then
                p96:set_mouse_visible(true)
            end;
        end;
        v_u_83:set(v97.X, v97.Y)
        if v_u_7.ControllerInputEnabled and v_u_30 then
            if v_u_91 == true and (v_u_94 == false and (s_UserInputService_0.GamepadEnabled == true and s_GamepadService_0.GamepadCursorEnabled == false)) then
                l_TextLabel_0.Visible = true
            else
                l_TextLabel_0.Visible = false
            end;
        else
            l_TextLabel_0.Visible = false
        end;
        v_u_21:clear()
        v_u_23:clear()
        if v_u_22:contains(v_u_11.KEY_SCROLL_UP) then
            p96:input_ended(v_u_11.KEY_SCROLL_UP)
        end;
        if v_u_22:contains(v_u_11.KEY_SCROLL_DOWN) then
            p96:input_ended(v_u_11.KEY_SCROLL_DOWN)
        end;
        if v_u_25 == true then
            v_u_25 = false
            v_u_24 = false
        end;
        local v98 = v_u_16:singleton()
        if v_u_86 == true then
            if v98:ui_needs_refresh() then
                p96:set_has_frame_focused_element(false)
                return;
            end;
            if v_u_6:test_enum_member(v_u_87, v_u_16.Test) then
                if v_u_16:test_frame_index_should_run(v_u_87, v98:get_next_index()) then
                    p96:set_has_frame_focused_element(false)
                    return;
                end;
            else
                p96:set_has_frame_focused_element(false)
            end;
        end;
    end;
    local v_u_99 = v_u_2:new()
    v_u_20.button_keycode_to_name = function(_, p_u_100) --[[ Name: button_keycode_to_name ]] --[[ Line: 495 ]]
        --[[ Upvalues: (copy 1): v_u_99, (copy 2): s_UserInputService_0, (ref 3): v_u_1 ]]
        if v_u_99:contains(p_u_100) ~= true then
            local v_u_101 = "None"
            pcall(function() --[[ Line: 498 ]]
                --[[ Upvalues: (ref 1): v_u_101, (ref 2): s_UserInputService_0, (copy 3): p_u_100 ]]
                v_u_101 = s_UserInputService_0:GetStringForKeyCode(p_u_100)
            end)
            v_u_101 = v_u_1:string_replace(v_u_101, "Button", "")
            v_u_101 = v_u_1:string_replace(v_u_101, "DPad", "")
            v_u_99:add(p_u_100, v_u_101)
        end;
        return v_u_99:get(p_u_100);
    end;
    local function f_active_dict_contains_controller_keycode(p102, p103) --[[ Name: active_dict_contains_controller_keycode ]] --[[ Line: 508 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_31 ]]
        for _, v104 in v_u_31:list_of((v_u_11:get_track_index_to_key():get(p103))):key_itr() do
            if p102:contains(v104) then
                return true;
            end;
        end;
        return false;
    end;
    local v105 = v_u_2
    local v135 = {
        [v_u_11.KEY_POWERBAR_TRIGGER] = function(_, p106) --[[ Line: 567 ]]
            return p106:contains(Enum.KeyCode.Space);
        end,
        [v_u_11.KEY_DOWN] = function(_, p107) --[[ Line: 579 ]]
            return p107:contains(Enum.KeyCode.Down);
        end,
        [v_u_11.KEY_UP] = function(_, p108) --[[ Line: 582 ]]
            return p108:contains(Enum.KeyCode.Up);
        end,
        [v_u_11.KEY_LEFT] = function(_, p109) --[[ Line: 585 ]]
            return p109:contains(Enum.KeyCode.Left);
        end,
        [v_u_11.KEY_RIGHT] = function(_, p110) --[[ Line: 588 ]]
            return p110:contains(Enum.KeyCode.Right);
        end,
        [v_u_11.KEY_A] = function(_, p111) --[[ Line: 591 ]]
            return p111:contains(Enum.KeyCode.A);
        end,
        [v_u_11.KEY_B] = function(_, p112) --[[ Line: 594 ]]
            return p112:contains(Enum.KeyCode.B);
        end,
        [v_u_11.KEY_MOD1] = function(_, p113) --[[ Line: 597 ]]
            return p113:contains(Enum.KeyCode.LeftShift) or p113:contains(Enum.KeyCode.RightShift);
        end,
        [v_u_11.KEY_MENU_OPEN] = function(_, p114) --[[ Line: 600 ]]
            return p114:contains(Enum.KeyCode.Return);
        end,
        [v_u_11.KEY_MENU_ENTER] = function(_, _) --[[ Line: 603 ]]
            return false;
        end,
        [v_u_11.KEY_MENU_BACK] = function(_, p115) --[[ Line: 606 ]]
            return p115:contains(Enum.KeyCode.Backspace);
        end,
        [v_u_11.KEY_MENU_SPUITEXTINPUT_ESC] = function(_, p116) --[[ Line: 621 ]]
            return p116:contains(Enum.KeyCode.Escape);
        end,
        [v_u_11.KEY_DEBUG_1] = function(_, p117) --[[ Line: 630 ]]
            return p117:contains(Enum.KeyCode.PageUp) or p117:contains(Enum.KeyCode.Insert);
        end,
        [v_u_11.KEY_DEBUG_2] = function(_, p118) --[[ Line: 633 ]]
            return p118:contains(Enum.KeyCode.PageDown) or p118:contains(Enum.KeyCode.Delete);
        end,
        [v_u_11.KEY_DEBUG_3] = function(_, p119) --[[ Line: 636 ]]
            return p119:contains(Enum.KeyCode.Home);
        end,
        [v_u_11.KEY_DEBUG_4] = function(_, p120) --[[ Line: 639 ]]
            return p120:contains(Enum.KeyCode.End);
        end,
        [v_u_11.KEY_EDITOR_PLAY_PAUSE] = function(_, p121) --[[ Line: 655 ]]
            return p121:contains(Enum.KeyCode.Space);
        end,
        [v_u_11.KEY_EDITOR_TIME_FORWARD] = function(_, p122) --[[ Line: 658 ]]
            return p122:contains(Enum.KeyCode.Up) or p122:contains(Enum.KeyCode.W);
        end,
        [v_u_11.KEY_EDITOR_TIME_BACK] = function(_, p123) --[[ Line: 661 ]]
            return p123:contains(Enum.KeyCode.Down) or p123:contains(Enum.KeyCode.S);
        end,
        [v_u_11.KEY_EDITOR_MODIFIER_SHIFT] = function(_, p124) --[[ Line: 664 ]]
            return p124:contains(Enum.KeyCode.LeftShift) or p124:contains(Enum.KeyCode.RightShift);
        end,
        [v_u_11.KEY_EDITOR_SELECT_MODE] = function(_, p125) --[[ Line: 667 ]]
            return p125:contains(Enum.KeyCode.Q) or p125:contains(Enum.KeyCode.One);
        end,
        [v_u_11.KEY_EDITOR_ADD_MODE] = function(_, p126) --[[ Line: 670 ]]
            return p126:contains(Enum.KeyCode.A) or p126:contains(Enum.KeyCode.Two);
        end,
        [v_u_11.KEY_EDITOR_DELETE_MODE] = function(_, p127) --[[ Line: 673 ]]
            return p127:contains(Enum.KeyCode.D) or p127:contains(Enum.KeyCode.Three);
        end,
        [v_u_11.KEY_EDITOR_UNDO] = function(_, p128) --[[ Line: 676 ]]
            return p128:contains(Enum.KeyCode.Z);
        end,
        [v_u_11.KEY_EDITOR_REDO] = function(_, p129) --[[ Line: 679 ]]
            return p129:contains(Enum.KeyCode.X);
        end,
        [v_u_11.KEY_EDITOR_MODIFIER_CTRL] = function(_, p130) --[[ Line: 682 ]]
            return p130:contains(Enum.KeyCode.LeftControl) or p130:contains(Enum.KeyCode.RightControl);
        end,
        [v_u_11.KEY_EDITOR_MODIFIER_ALT] = function(_, p131) --[[ Line: 685 ]]
            return p131:contains(Enum.KeyCode.LeftAlt) or p131:contains(Enum.KeyCode.RightAlt);
        end,
        [v_u_11.KEY_EDITOR_TOGGLE_HOLD_BEAT_LENGTH] = function(_, p132) --[[ Line: 688 ]]
            return p132:contains(Enum.KeyCode.E) or p132:contains(Enum.KeyCode.Four);
        end,
        [v_u_11.KEY_EDITOR_COPY] = function(_, p133) --[[ Line: 691 ]]
            return p133:contains(Enum.KeyCode.C);
        end,
        [v_u_11.KEY_EDITOR_PASTE_MODE] = function(_, p134) --[[ Line: 694 ]]
            return p134:contains(Enum.KeyCode.Five) or p134:contains(Enum.KeyCode.V);
        end
    }
    v135[v_u_11.KEY_TRACK1] = function(_, p136) --[[ Line: 519 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_30, (copy 3): v_u_29, (ref 4): v_u_11, (ref 5): v_u_7, (copy 6): f_active_dict_contains_controller_keycode ]]
        if v_u_1:is_mobile() == false and (v_u_30 == false and v_u_29:contains(v_u_11.KEY_TRACK1)) then
            return p136:contains(v_u_29:get(v_u_11.KEY_TRACK1));
        end;
        local v137 = not (p136:contains(Enum.KeyCode.A) or (p136:contains(Enum.KeyCode.J) or p136:contains(Enum.KeyCode.One))) and (not (p136:contains(Enum.KeyCode.Q) or p136:contains(Enum.KeyCode.U)) and (not p136:contains(v_u_11.KEYCODE_TOUCH_TRACK1) and v_u_7.ControllerInputEnabled))
        if v137 then
            v137 = f_active_dict_contains_controller_keycode(p136, 1)
        end;
        return v137;
    end
    v135[v_u_11.KEY_TRACK2] = function(_, p138) --[[ Line: 531 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_30, (copy 3): v_u_29, (ref 4): v_u_11, (ref 5): v_u_7, (copy 6): f_active_dict_contains_controller_keycode ]]
        if v_u_1:is_mobile() == false and (v_u_30 == false and v_u_29:contains(v_u_11.KEY_TRACK2)) then
            return p138:contains(v_u_29:get(v_u_11.KEY_TRACK2));
        end;
        local v139 = not (p138:contains(Enum.KeyCode.S) or (p138:contains(Enum.KeyCode.K) or p138:contains(Enum.KeyCode.Two))) and (not (p138:contains(Enum.KeyCode.W) or p138:contains(Enum.KeyCode.I)) and (not p138:contains(v_u_11.KEYCODE_TOUCH_TRACK2) and v_u_7.ControllerInputEnabled))
        if v139 then
            v139 = f_active_dict_contains_controller_keycode(p138, 2)
        end;
        return v139;
    end
    v135[v_u_11.KEY_TRACK3] = function(_, p140) --[[ Line: 543 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_30, (copy 3): v_u_29, (ref 4): v_u_11, (ref 5): v_u_7, (copy 6): f_active_dict_contains_controller_keycode ]]
        if v_u_1:is_mobile() == false and (v_u_30 == false and v_u_29:contains(v_u_11.KEY_TRACK3)) then
            return p140:contains(v_u_29:get(v_u_11.KEY_TRACK3));
        end;
        local v141 = not (p140:contains(Enum.KeyCode.D) or (p140:contains(Enum.KeyCode.L) or p140:contains(Enum.KeyCode.Three))) and (not (p140:contains(Enum.KeyCode.E) or p140:contains(Enum.KeyCode.O)) and (not p140:contains(v_u_11.KEYCODE_TOUCH_TRACK3) and v_u_7.ControllerInputEnabled))
        if v141 then
            v141 = f_active_dict_contains_controller_keycode(p140, 3)
        end;
        return v141;
    end
    v135[v_u_11.KEY_TRACK4] = function(_, p142) --[[ Line: 555 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_30, (copy 3): v_u_29, (ref 4): v_u_11, (ref 5): v_u_7, (copy 6): f_active_dict_contains_controller_keycode ]]
        if v_u_1:is_mobile() == false and (v_u_30 == false and v_u_29:contains(v_u_11.KEY_TRACK4)) then
            return p142:contains(v_u_29:get(v_u_11.KEY_TRACK4));
        end;
        local v143 = not (p142:contains(Enum.KeyCode.F) or (p142:contains(Enum.KeyCode.Semicolon) or p142:contains(Enum.KeyCode.Four))) and (not (p142:contains(Enum.KeyCode.R) or p142:contains(Enum.KeyCode.P)) and (not p142:contains(v_u_11.KEYCODE_TOUCH_TRACK4) and v_u_7.ControllerInputEnabled))
        if v143 then
            v143 = f_active_dict_contains_controller_keycode(p142, 4)
        end;
        return v143;
    end
    v135[v_u_11.KEY_GAME_QUIT] = function(_, p144) --[[ Line: 573 ]]
        --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_11 ]]
        if v_u_29:contains(v_u_11.KEY_GAME_QUIT) then
            return p144:contains(v_u_29:get(v_u_11.KEY_GAME_QUIT));
        else
            return p144:contains(Enum.KeyCode.Backspace);
        end;
    end
    v135[v_u_11.KEY_MENU_MATCHMAKING_CHAT_FOCUS] = function(_, p145) --[[ Line: 609 ]]
        --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_11, (ref 3): v_u_24 ]]
        if v_u_29:contains(v_u_11.KEY_MENU_MATCHMAKING_CHAT_FOCUS) then
            local v146 = p145:contains(v_u_29:get(v_u_11.KEY_MENU_MATCHMAKING_CHAT_FOCUS))
            if v146 then
                v146 = v_u_24 == false
            end;
            return v146;
        else
            local v147 = p145:contains(Enum.KeyCode.Period)
            if v147 then
                v147 = v_u_24 == false
            end;
            return v147;
        end;
    end
    v135[v_u_11.KEY_CHAT_WINDOW_FOCUS] = function(_, p148) --[[ Line: 615 ]]
        --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_11, (ref 3): v_u_24 ]]
        if v_u_29:contains(v_u_11.KEY_CHAT_WINDOW_FOCUS) then
            local v149 = p148:contains(v_u_29:get(v_u_11.KEY_CHAT_WINDOW_FOCUS))
            if v149 then
                v149 = v_u_24 == false
            end;
            return v149;
        else
            local v150 = p148:contains(Enum.KeyCode.Slash)
            if v150 then
                v150 = v_u_24 == false
            end;
            return v150;
        end;
    end
    v135[v_u_11.KEY_SCROLL_UP] = function(_, p151) --[[ Line: 624 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        return p151:contains(v_u_11.KEY_SCROLL_UP);
    end
    v135[v_u_11.KEY_SCROLL_DOWN] = function(_, p152) --[[ Line: 627 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        return p152:contains(v_u_11.KEY_SCROLL_DOWN);
    end
    v135[v_u_11.KEYCODE_TOUCH_TRACK1] = function(_, _) --[[ Line: 642 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_11 ]]
        return v_u_22:contains(v_u_11.KEYCODE_TOUCH_TRACK1);
    end
    v135[v_u_11.KEYCODE_TOUCH_TRACK2] = function(_, _) --[[ Line: 645 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_11 ]]
        return v_u_22:contains(v_u_11.KEYCODE_TOUCH_TRACK2);
    end
    v135[v_u_11.KEYCODE_TOUCH_TRACK3] = function(_, _) --[[ Line: 648 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_11 ]]
        return v_u_22:contains(v_u_11.KEYCODE_TOUCH_TRACK3);
    end
    v135[v_u_11.KEYCODE_TOUCH_TRACK4] = function(_, _) --[[ Line: 651 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_11 ]]
        return v_u_22:contains(v_u_11.KEYCODE_TOUCH_TRACK4);
    end
    local v_u_153 = v105:new(v135)
    local function f_is_control_active(p154, p155) --[[ Name: is_control_active ]] --[[ Line: 699 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_24, (copy 3): v_u_153 ]]
        if p154 == v_u_11.KEY_CLICK then
            return p155:contains(v_u_11.KEY_CLICK);
        end;
        if v_u_24 == true then
            return false;
        end;
        if v_u_153:contains(p154) then
            return v_u_153:get(p154)(p154, p155);
        end;
        warn("INPUTKEY NOT FOUND ", p154)
        return false;
    end;
    local v_u_156 = nil
    v_u_20.get_frame_index_state = function(_) --[[ Name: get_frame_index_state ]] --[[ Line: 718 ]]
        --[[ Upvalues: (ref 1): v_u_156 ]]
        return v_u_156;
    end;
    v_u_20.set_frame_index_state = function(_, p157) --[[ Name: set_frame_index_state ]] --[[ Line: 719 ]]
        --[[ Upvalues: (ref 1): v_u_156, (ref 2): v_u_5 ]]
        if p157 ~= nil and v_u_156 ~= nil then
            v_u_5:warnf("InputUtil:set_frame_index_state(%s) when not nil(%s)", p157:get_name(), v_u_156:get_name())
        end;
        v_u_156 = p157
    end;
    v_u_20.control_just_pressed = function(_, p158) --[[ Name: control_just_pressed ]] --[[ Line: 730 ]]
        --[[ Upvalues: (ref 1): v_u_156, (copy 2): f_is_control_active, (copy 3): v_u_21 ]]
        if v_u_156 then
            return f_is_control_active(p158, v_u_156:get_just_pressed_keys());
        else
            return f_is_control_active(p158, v_u_21);
        end;
    end;
    v_u_20.control_pressed = function(_, p159) --[[ Name: control_pressed ]] --[[ Line: 734 ]]
        --[[ Upvalues: (copy 1): f_is_control_active, (copy 2): v_u_22 ]]
        return f_is_control_active(p159, v_u_22);
    end;
    v_u_20.control_just_released = function(_, p160) --[[ Name: control_just_released ]] --[[ Line: 737 ]]
        --[[ Upvalues: (ref 1): v_u_156, (copy 2): f_is_control_active, (copy 3): v_u_23 ]]
        if v_u_156 then
            return f_is_control_active(p160, v_u_156:get_just_released_keys());
        else
            return f_is_control_active(p160, v_u_23);
        end;
    end;
    v_u_20.clear_just_pressed_keys = function(_) --[[ Name: clear_just_pressed_keys ]] --[[ Line: 742 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        v_u_21:clear()
    end;
    v_u_20.clear_just_released_keys = function(_) --[[ Name: clear_just_released_keys ]] --[[ Line: 745 ]]
        --[[ Upvalues: (copy 1): v_u_23 ]]
        v_u_23:clear()
    end;
    v_u_20.get_just_pressed_keys = function(_) --[[ Name: get_just_pressed_keys ]] --[[ Line: 748 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        return v_u_21;
    end;
    v_u_20.get_just_released_keys = function(_) --[[ Name: get_just_released_keys ]] --[[ Line: 749 ]]
        --[[ Upvalues: (copy 1): v_u_23 ]]
        return v_u_23;
    end;
    v_u_20.record_next_keycode_input = function(_) --[[ Name: record_next_keycode_input ]] --[[ Line: 753 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27 ]]
        v_u_26 = true
        v_u_27 = false
    end;
    v_u_20.has_recorded_keycode_input = function(_) --[[ Name: has_recorded_keycode_input ]] --[[ Line: 758 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v_u_20.cancel_record_next_keycode_input = function(_) --[[ Name: cancel_record_next_keycode_input ]] --[[ Line: 762 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = false
    end;
    v_u_20.get_recorded_keycode = function(_) --[[ Name: get_recorded_keycode ]] --[[ Line: 766 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v_u_20.reset_to_default_controls = function(_) --[[ Name: reset_to_default_controls ]] --[[ Line: 772 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        v_u_29:clear()
    end;
    v_u_20.set_custom_key_keycode = function(_, p161, p162) --[[ Name: set_custom_key_keycode ]] --[[ Line: 776 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        v_u_29:add(p161, p162)
    end;
    v_u_20.remove_custom_key = function(_, p163) --[[ Name: remove_custom_key ]] --[[ Line: 780 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        v_u_29:remove(p163)
    end;
    v_u_20.get_custom_key_keycode = function(_, p164) --[[ Name: get_custom_key_keycode ]] --[[ Line: 784 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        return v_u_29:get(p164);
    end;
    v_u_20.get_key_display_str = function(_, p165) --[[ Name: get_key_display_str ]] --[[ Line: 788 ]]
        --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_11 ]]
        if v_u_29:contains(p165) then
            return v_u_29:get(p165).Name;
        else
            return p165 == v_u_11.KEY_MENU_MATCHMAKING_CHAT_FOCUS and "." or (p165 == v_u_11.KEY_CHAT_WINDOW_FOCUS and "/" or (p165 == v_u_11.KEY_TRACK1 and "A/J/Q/U/1" or (p165 == v_u_11.KEY_TRACK2 and "S/K/W/I/2" or (p165 == v_u_11.KEY_TRACK3 and "D/L/E/O/3" or (p165 == v_u_11.KEY_TRACK4 and "F/;/R/P/4" or (p165 == v_u_11.KEY_POWERBAR_TRIGGER and "Space" or string.format("??? (%d)", (tostring(p165)))))))));
        end;
    end;
    local v166 = v_u_3:new({
        Enum.KeyCode.ButtonX,
        Enum.KeyCode.ButtonA,
        Enum.KeyCode.ButtonY,
        Enum.KeyCode.ButtonB,
        Enum.KeyCode.DPadLeft,
        Enum.KeyCode.DPadDown,
        Enum.KeyCode.DPadRight,
        Enum.KeyCode.DPadUp,
        Enum.KeyCode.ButtonL1,
        Enum.KeyCode.ButtonR1,
        Enum.KeyCode.ButtonL2,
        Enum.KeyCode.ButtonR2
    })
    local v_u_167 = v_u_2:new():add_set_from_table_list(v166:get_table())
    v_u_20.get_available_controller_keys = function(_) --[[ Name: get_available_controller_keys ]] --[[ Line: 828 ]]
        --[[ Upvalues: (copy 1): v_u_167 ]]
        return v_u_167;
    end;
    local v_u_168 = v_u_2:new()
    local v_u_169 = v_u_33
    local v_u_170 = v_u_35
    local v_u_171 = v_u_34
    for v172, _ in v_u_167:key_itr() do
        v_u_168:add(v172.Value, v172)
    end;
    v_u_20.value_to_controller_keycode = function(_) --[[ Name: value_to_controller_keycode ]] --[[ Line: 834 ]]
        --[[ Upvalues: (copy 1): v_u_168 ]]
        return v_u_168;
    end;
    local v_u_173 = v_u_2:new()
    for v174, v175 in v166:key_itr() do
        v_u_173:add(v175, v174)
    end;
    local function f_sort_controller_track_enum_to_keycodes() --[[ Name: sort_controller_track_enum_to_keycodes ]] --[[ Line: 840 ]]
        --[[ Upvalues: (copy 1): v_u_31, (ref 2): v_u_3, (copy 3): v_u_173, (copy 4): v_u_32 ]]
        for _, v176 in v_u_31:key_itr() do
            v_u_3:make_unique(v176)
            v176:sort(function(p177, p178) --[[ Line: 843 ]]
                --[[ Upvalues: (ref 1): v_u_173 ]]
                return v_u_173:get(p177) < v_u_173:get(p178);
            end)
        end;
        v_u_3:make_unique(v_u_32)
        v_u_32:sort(function(p179, p180) --[[ Line: 848 ]]
            --[[ Upvalues: (ref 1): v_u_173 ]]
            return v_u_173:get(p179) < v_u_173:get(p180);
        end)
    end;
    local v_u_181 = v_u_2:new({
        Enum.KeyCode.ButtonX,
        Enum.KeyCode.ButtonA,
        Enum.KeyCode.ButtonY,
        Enum.KeyCode.ButtonB
    })
    local v_u_182 = v_u_2:new():add_set_from_table_list(v_u_181:get_table())
    local v_u_183 = v_u_2:new({
        Enum.KeyCode.DPadLeft,
        Enum.KeyCode.DPadDown,
        Enum.KeyCode.DPadUp,
        Enum.KeyCode.DPadRight
    })
    local v_u_184 = v_u_2:new():add_set_from_table_list(v_u_183:get_table())
    local v_u_185 = v_u_2:new({
        [1] = Enum.KeyCode.ButtonL1,
        [4] = Enum.KeyCode.ButtonR1
    })
    v_u_20.track_index_to_default_controller_button = function(_, p186) --[[ Name: track_index_to_default_controller_button ]] --[[ Line: 871 ]]
        --[[ Upvalues: (copy 1): v_u_31, (ref 2): v_u_15, (copy 3): v_u_182 ]]
        for _, v187 in v_u_31:list_of(v_u_15:get(p186)):key_itr() do
            if v_u_182:contains(v187) then
                return v187;
            end;
        end;
        return "None";
    end;
    v_u_20.track_index_to_default_controller_dpad = function(_, p188) --[[ Name: track_index_to_default_controller_dpad ]] --[[ Line: 881 ]]
        --[[ Upvalues: (copy 1): v_u_31, (ref 2): v_u_15, (copy 3): v_u_184 ]]
        for _, v189 in v_u_31:list_of(v_u_15:get(p188)):key_itr() do
            if v_u_184:contains(v189) then
                return v189;
            end;
        end;
        return "None";
    end;
    local v_u_190 = v_u_2:new():add_set_from_table_list({ Enum.KeyCode.ButtonL2, Enum.KeyCode.ButtonR2 })
    local function f_set_default_controller_keybinds() --[[ Name: set_default_controller_keybinds ]] --[[ Line: 894 ]]
        --[[ Upvalues: (copy 1): v_u_31, (ref 2): v_u_12, (copy 3): v_u_181, (copy 4): v_u_183, (copy 5): v_u_185, (copy 6): v_u_32, (copy 7): v_u_190, (copy 8): f_sort_controller_track_enum_to_keycodes, (copy 9): f_update_controller_cursor_hint_display ]]
        v_u_31:clear()
        for v191, v192 in v_u_12:key_itr() do
            local v193 = v_u_181:get(v191)
            if v193 ~= nil and v_u_31:list_of(v192):contains(v193) ~= true then
                v_u_31:push_back_to(v192, v193)
            end;
            local v194 = v_u_183:get(v191)
            if v194 ~= nil and v_u_31:list_of(v192):contains(v194) ~= true then
                v_u_31:push_back_to(v192, v194)
            end;
            local v195 = v_u_185:get(v191)
            if v195 ~= nil and v_u_31:list_of(v192):contains(v195) ~= true then
                v_u_31:push_back_to(v192, v195)
            end;
        end;
        v_u_32:clear()
        for v196, _ in v_u_190:key_itr() do
            v_u_32:push_back(v196)
        end;
        f_sort_controller_track_enum_to_keycodes()
        f_update_controller_cursor_hint_display()
    end;
    f_set_default_controller_keybinds()
    v_u_20.reset_to_default_controller_keybinds = function(_) --[[ Name: reset_to_default_controller_keybinds ]] --[[ Line: 921 ]]
        --[[ Upvalues: (copy 1): f_set_default_controller_keybinds ]]
        f_set_default_controller_keybinds()
    end;
    v_u_20.update_controller_keybinds = function(_, p197, p198) --[[ Name: update_controller_keybinds ]] --[[ Line: 922 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_31, (copy 3): v_u_32, (copy 4): f_set_default_controller_keybinds, (ref 5): v_u_6, (ref 6): v_u_12, (copy 7): v_u_167, (copy 8): f_sort_controller_track_enum_to_keycodes, (copy 9): f_update_controller_cursor_hint_display, (ref 10): v_u_2, (ref 11): v_u_5 ]]
        local function f_remove_keycode_from_all_other_lists(p199) --[[ Name: remove_keycode_from_all_other_lists ]] --[[ Line: 923 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_31, (ref 3): v_u_32 ]]
            for _, v200 in v_u_11:get_track_index_list():key_itr() do
                v_u_31:list_of(v200):remove(p199)
            end;
            v_u_32:remove(p199)
        end;
        f_set_default_controller_keybinds()
        for v201, v202 in p197:key_itr() do
            v_u_6:is_true(v_u_12:contains(v201))
            for _, v203 in v202:key_itr() do
                v_u_6:is_true(v_u_167:contains(v203))
                f_remove_keycode_from_all_other_lists(v203)
                v_u_31:push_back_to(v201, v203)
            end;
        end;
        if p198 then
            for _, v204 in p198:key_itr() do
                v_u_6:is_true(v_u_167:contains(v204))
                f_remove_keycode_from_all_other_lists(v204)
                v_u_32:push_back(v204)
            end;
        end;
        f_sort_controller_track_enum_to_keycodes()
        f_update_controller_cursor_hint_display()
        local v205 = v_u_2:new()
        for _, v206 in v_u_31:key_itr() do
            for _, v207 in v206:key_itr() do
                v_u_2:counter_increment(v205, v207)
            end;
        end;
        for _, v208 in v_u_32:key_itr() do
            v_u_2:counter_increment(v205, v208)
        end;
        for v209, v210 in v205:key_itr() do
            if v210 > 1 then
                v_u_5:warnf("InputUtil:set_controller_keybinds key(%s) count(%d)", tostring(v209), v210)
            end;
        end;
    end;
    v_u_20.record_next_controller_keycode_input = function(_) --[[ Name: record_next_controller_keycode_input ]] --[[ Line: 971 ]]
        --[[ Upvalues: (ref 1): v_u_169, (ref 2): v_u_171 ]]
        v_u_169 = true
        v_u_171 = false
    end;
    v_u_20.has_recorded_controller_keycode_input = function(_) --[[ Name: has_recorded_controller_keycode_input ]] --[[ Line: 975 ]]
        --[[ Upvalues: (ref 1): v_u_171 ]]
        return v_u_171;
    end;
    v_u_20.cancel_record_next_controller_keycode_input = function(_) --[[ Name: cancel_record_next_controller_keycode_input ]] --[[ Line: 976 ]]
        --[[ Upvalues: (ref 1): v_u_169 ]]
        v_u_169 = false
    end;
    v_u_20.get_recorded_controller_keycode = function(_) --[[ Name: get_recorded_controller_keycode ]] --[[ Line: 977 ]]
        --[[ Upvalues: (ref 1): v_u_170 ]]
        return v_u_170;
    end;
    f_cons()
    return v_u_20;
end;
local v_u_211 = v_u_2:new()
local v_u_212 = v_u_2:new()
for _, v213 in pairs(Enum.KeyCode:GetEnumItems()) do
    local l_Value_0 = v213.Value
    v_u_211:add(v213, l_Value_0)
    v_u_212:add(l_Value_0, v213)
end;
v_u_11.keycode_enum_to_value = function(_, p214) --[[ Name: keycode_enum_to_value ]] --[[ Line: 990 ]]
    --[[ Upvalues: (copy 1): v_u_211 ]]
    return v_u_211:get(p214);
end;
v_u_11.value_to_keycode_enum = function(_, p215) --[[ Name: value_to_keycode_enum ]] --[[ Line: 991 ]]
    --[[ Upvalues: (copy 1): v_u_212 ]]
    return v_u_212:get(p215);
end;
return v_u_11;
