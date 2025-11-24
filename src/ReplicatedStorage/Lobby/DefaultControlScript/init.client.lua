-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local _ = game:GetService("ContextActionService")
local s_Players_0 = game:GetService("Players")
local s_UserInputService_0 = game:GetService("UserInputService")
local l_GameSettings_0 = UserSettings().GameSettings
if s_Players_0.LocalPlayer == nil then
    error("DefaultControlScript Player is nil")
else
    local l_LocalPlayer_0 = s_Players_0.LocalPlayer
    local v_u_1 = nil
    local v_u_2 = l_LocalPlayer_0:WaitForChild("PlayerGui")
    local l_TouchEnabled_0 = s_UserInputService_0.TouchEnabled
    local v_u_3 = l_TouchEnabled_0 and l_GameSettings_0.TouchMovementMode or l_GameSettings_0.ComputerMovementMode
    local v_u_4 = l_TouchEnabled_0 and l_LocalPlayer_0.DevTouchMovementMode or l_LocalPlayer_0.DevComputerMovementMode
    if l_TouchEnabled_0 then
        v_u_4 = Enum.DevTouchMovementMode.Thumbstick
    end;
    local v_u_5 = nil
    local v_u_6 = nil
    local l_ModalEnabled_0 = s_UserInputService_0.ModalEnabled
    local v_u_7 = true
    local v_u_8 = {
        ["Current"] = nil
    }
    v_u_8.SwitchTo = function(_, p9) --[[ Name: SwitchTo ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): v_u_8 ]]
        if v_u_8.Current ~= p9 then
            if v_u_8.Current then
                v_u_8.Current:Disable()
            end;
            v_u_8.Current = p9
            if v_u_8.Current then
                v_u_8.Current:Enable()
            end;
        end;
    end;
    local v_u_10 = nil
    local v_u_11 = {
        ["Gamepad"] = require(script.MasterControl:WaitForChild("Gamepad")),
        ["Touch"] = {},
        ["Keyboard"] = {}
    }
    local v_u_12 = require(script:WaitForChild("MasterControl"))
    local v_u_13 = require(script.MasterControl:WaitForChild("Thumbstick"))
    local v_u_14 = require(script.MasterControl:WaitForChild("Thumbpad"))
    local v_u_15 = require(script.MasterControl:WaitForChild("DPad"))
    local v_u_16 = require(script.MasterControl:WaitForChild("TouchJump"))
    local v_u_17 = require(script.MasterControl:WaitForChild("KeyboardMovement"))
    getTouchModule = function() --[[ Name: getTouchModule ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_13, (copy 3): v_u_14, (copy 4): v_u_15 ]]
        local v18 = nil
        if v_u_4 == Enum.DevTouchMovementMode.Thumbstick then
            return v_u_13;
        end;
        if v_u_4 == Enum.DevTouchMovementMode.Thumbpad then
            return v_u_14;
        end;
        if v_u_4 == Enum.DevTouchMovementMode.DPad then
            return v_u_15;
        end;
        if v_u_4 == Enum.DevTouchMovementMode.ClickToMove then
            return nil;
        end;
        if v_u_4 == Enum.DevTouchMovementMode.Scriptable then
            v18 = nil
        end;
        return v18;
    end;
    local function _(p19) --[[ Name: setJumpModule ]] --[[ Line: 120 ]]
        --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_8, (copy 3): v_u_11 ]]
        if p19 then
            if v_u_8.Current == v_u_11.Touch then
                v_u_16:Enable()
            end;
        else
            v_u_16:Disable()
        end;
    end;
    setClickToMove = function() --[[ Name: setClickToMove ]] --[[ Line: 128 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_3, (ref 3): v_u_1, (ref 4): v_u_10, (copy 5): v_u_8 ]]
        if v_u_4 == Enum.DevTouchMovementMode.ClickToMove or (v_u_4 == Enum.DevComputerMovementMode.ClickToMove or (v_u_3 == Enum.ComputerMovementMode.ClickToMove or v_u_3 == Enum.TouchMovementMode.ClickToMove)) then
            if v_u_1 == Enum.UserInputType.Touch then
                v_u_10 = v_u_8.Current
                return;
            end;
        elseif v_u_10 then
            v_u_10:Disable()
            v_u_10 = nil
        end;
    end;
    v_u_11.Touch.Current = nil
    v_u_11.Touch.LocalPlayerChangedCon = nil
    v_u_11.Touch.GameSettingsChangedCon = nil
    v_u_11.Touch.RefreshControlStyle = function(_) --[[ Name: RefreshControlStyle ]] --[[ Line: 146 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_16 ]]
        if v_u_11.Touch.Current then
            v_u_11.Touch.Current:Disable()
        end;
        v_u_16:Disable()
        v_u_16:Disable()
        v_u_11.Touch:Enable()
    end;
    v_u_11.Touch.DisconnectEvents = function(_) --[[ Name: DisconnectEvents ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        if v_u_11.Touch.LocalPlayerChangedCon then
            v_u_11.Touch.LocalPlayerChangedCon:disconnect()
            v_u_11.Touch.LocalPlayerChangedCon = nil
        end;
        if v_u_11.Touch.GameSettingsChangedCon then
            v_u_11.Touch.GameSettingsChangedCon:disconnect()
            v_u_11.Touch.GameSettingsChangedCon = nil
        end;
    end;
    v_u_11.Touch.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_16, (copy 3): v_u_8, (copy 4): v_u_11, (copy 5): l_LocalPlayer_0, (copy 6): l_GameSettings_0, (ref 7): v_u_5 ]]
        local v20 = getTouchModule()
        if v20 then
            setClickToMove()
            if v_u_7 then
                if v_u_8.Current == v_u_11.Touch then
                    v_u_16:Enable()
                end;
            else
                v_u_16:Disable()
            end;
            v20:Enable()
            v_u_11.Touch.Current = v20
            if v_u_7 then
                v_u_16:Enable()
            end;
        end;
        v_u_11.Touch:DisconnectEvents()
        v_u_11.Touch.LocalPlayerChangedCon = l_LocalPlayer_0.Changed:connect(function(p21) --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            if p21 == "DevTouchMovementMode" then
                v_u_11.Touch:RefreshControlStyle()
            end;
        end)
        v_u_11.Touch.GameSettingsChangedCon = l_GameSettings_0.Changed:connect(function(p22) --[[ Line: 184 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            if p22 == "TouchMovementMode" then
                v_u_11.Touch:RefreshControlStyle()
            end;
        end)
        if v_u_5 then
            v_u_5.Enabled = true
        end;
    end;
    v_u_11.Touch.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 194 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_13, (copy 3): v_u_15, (copy 4): v_u_14, (copy 5): v_u_16, (ref 6): v_u_5 ]]
        v_u_11.Touch:DisconnectEvents()
        local v23 = getTouchModule()
        if v23 == v_u_13 or (v23 == v_u_15 or v23 == v_u_14) then
            v23:Disable()
            v_u_16:Disable()
            v_u_16:Disable()
        end;
        if v_u_5 then
            v_u_5.Enabled = false
        end;
    end;
    local function f_getKeyboardModule() --[[ Name: getKeyboardModule ]] --[[ Line: 212 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_17 ]]
        local v24 = nil
        if v_u_4 == Enum.DevComputerMovementMode.KeyboardMouse then
            return v_u_17;
        end;
        if v_u_4 == Enum.DevComputerMovementMode.ClickToMove then
            v24 = v_u_17
        end;
        return v24;
    end;
    v_u_11.Keyboard.RefreshControlStyle = function(_) --[[ Name: RefreshControlStyle ]] --[[ Line: 234 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        v_u_11.Keyboard:Disable()
        v_u_11.Keyboard:Enable()
    end;
    v_u_11.Keyboard.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 238 ]]
        --[[ Upvalues: (copy 1): f_getKeyboardModule, (copy 2): v_u_11, (copy 3): l_LocalPlayer_0, (copy 4): l_GameSettings_0 ]]
        local v25 = f_getKeyboardModule()
        if v25 then
            v25:Enable()
        end;
        v_u_11.Keyboard:DisconnectEvents()
        v_u_11.Keyboard.LocalPlayerChangedCon = l_LocalPlayer_0.Changed:connect(function(p26) --[[ Line: 245 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            if p26 == "DevComputerMovementMode" then
                v_u_11.Keyboard:RefreshControlStyle()
            end;
        end)
        v_u_11.Keyboard.GameSettingsChangedCon = l_GameSettings_0.Changed:connect(function(p27) --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            if p27 == "ComputerMovementMode" then
                v_u_11.Keyboard:RefreshControlStyle()
            end;
        end)
    end;
    v_u_11.Keyboard.DisconnectEvents = function(_) --[[ Name: DisconnectEvents ]] --[[ Line: 257 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        if v_u_11.Keyboard.LocalPlayerChangedCon then
            v_u_11.Keyboard.LocalPlayerChangedCon:disconnect()
            v_u_11.Keyboard.LocalPlayerChangedCon = nil
        end;
        if v_u_11.Keyboard.GameSettingsChangedCon then
            v_u_11.Keyboard.GameSettingsChangedCon:disconnect()
            v_u_11.Keyboard.GameSettingsChangedCon = nil
        end;
    end;
    v_u_11.Keyboard.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 267 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): f_getKeyboardModule ]]
        v_u_11.Keyboard:DisconnectEvents()
        local v28 = f_getKeyboardModule()
        if v28 then
            v28:Disable()
        end;
    end;
    local function f_createTouchGuiContainer() --[[ Name: createTouchGuiContainer ]] --[[ Line: 284 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_2, (ref 3): v_u_6, (copy 4): v_u_13, (copy 5): v_u_15, (copy 6): v_u_14, (copy 7): v_u_16 ]]
        if v_u_5 then
            v_u_5:Destroy()
        end;
        v_u_5 = Instance.new("ScreenGui")
        v_u_5.Name = "TouchGui"
        v_u_5.Parent = v_u_2
        v_u_6 = Instance.new("Frame")
        v_u_6.Name = "TouchControlFrame"
        v_u_6.Size = UDim2.new(1, 0, 1, 0)
        v_u_6.BackgroundTransparency = 1
        v_u_6.Parent = v_u_5
        v_u_13:Create(v_u_6)
        v_u_15:Create(v_u_6)
        v_u_14:Create(v_u_6)
        v_u_16:Create(v_u_6)
    end;
    local v_u_29 = nil
    l_LocalPlayer_0.CharacterAdded:connect(function(_) --[[ Line: 329 ]]
        --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_29, (copy 3): s_UserInputService_0, (copy 4): f_createTouchGuiContainer ]]
        if v_u_8.Current then
            v_u_29 = v_u_8.Current
            v_u_8:SwitchTo(nil)
        end;
        if s_UserInputService_0.TouchEnabled then
            f_createTouchGuiContainer()
        end;
        if v_u_8.Current == nil then
            v_u_8:SwitchTo(v_u_29)
        end;
    end)
    l_LocalPlayer_0.CharacterRemoving:connect(function() --[[ Line: 344 ]]
        --[[ Upvalues: (ref 1): v_u_29, (copy 2): v_u_8 ]]
        v_u_29 = v_u_8.Current
        v_u_8:SwitchTo(nil)
    end)
    s_UserInputService_0.Changed:connect(function(p30) --[[ Line: 349 ]]
        --[[ Upvalues: (ref 1): l_ModalEnabled_0, (copy 2): s_UserInputService_0, (ref 3): v_u_1, (copy 4): v_u_8, (copy 5): v_u_11 ]]
        if p30 == "ModalEnabled" then
            l_ModalEnabled_0 = s_UserInputService_0.ModalEnabled
            if v_u_1 == Enum.UserInputType.Touch then
                if v_u_8.Current == v_u_11.Touch and l_ModalEnabled_0 then
                    v_u_8:SwitchTo(nil)
                    return;
                end;
                if v_u_8.Current == nil and not l_ModalEnabled_0 then
                    v_u_8:SwitchTo(v_u_11.Touch)
                end;
            end;
        end;
    end)
    local function v_u_32(p31) --[[ Line: 375 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_4, (copy 3): v_u_8, (copy 4): v_u_11 ]]
        if v_u_1 ~= p31 then
            v_u_1 = p31
            if v_u_1 == Enum.UserInputType.Touch then
                v_u_4 = Enum.DevTouchMovementMode.Thumbstick
                v_u_8:SwitchTo(v_u_11.Touch)
                return;
            end;
            if v_u_1 == Enum.UserInputType.Keyboard or (v_u_1 == Enum.UserInputType.MouseButton1 or (v_u_1 == Enum.UserInputType.MouseButton2 or (v_u_1 == Enum.UserInputType.MouseButton3 or (v_u_1 == Enum.UserInputType.MouseWheel or v_u_1 == Enum.UserInputType.MouseMovement)))) then
                v_u_4 = Enum.DevComputerMovementMode.KeyboardMouse
                v_u_8:SwitchTo(v_u_11.Keyboard)
                return;
            end;
            if v_u_1 == Enum.UserInputType.Gamepad1 or (v_u_1 == Enum.UserInputType.Gamepad2 or (v_u_1 == Enum.UserInputType.Gamepad3 or v_u_1 == Enum.UserInputType.Gamepad4)) then
                v_u_8:SwitchTo(v_u_11.Gamepad)
            end;
        end;
    end;
    if l_TouchEnabled_0 then
        f_createTouchGuiContainer()
    end;
    s_UserInputService_0.GamepadDisconnected:connect(function(_) --[[ Line: 422 ]]
        --[[ Upvalues: (copy 1): s_UserInputService_0, (copy 2): v_u_8, (copy 3): v_u_11, (copy 4): l_TouchEnabled_0 ]]
        if #s_UserInputService_0:GetConnectedGamepads() > 0 then
            return;
        elseif s_UserInputService_0.KeyboardEnabled then
            v_u_8:SwitchTo(v_u_11.Keyboard)
        elseif l_TouchEnabled_0 then
            v_u_8:SwitchTo(v_u_11.Touch)
        end;
    end)
    s_UserInputService_0.GamepadConnected:connect(function(_) --[[ Line: 433 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_11 ]]
        v_u_8:SwitchTo(v_u_11.Gamepad)
    end)
    s_UserInputService_0.InputBegan:connect(function(p33, _) --[[ Line: 437 ]]
        --[[ Upvalues: (copy 1): v_u_32 ]]
        v_u_32(p33.UserInputType)
    end)
    v_u_32(s_UserInputService_0:GetLastInputType())
    local v_u_34 = {
        ["_enabled"] = true
    }
    v_u_34.update = function(p35, p36, p37) --[[ Name: update ]] --[[ Line: 448 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        if p35._enabled == false then
            if v_u_12:is_force_jump() then
                v_u_12:Update(p36, p37)
            end;
        else
            v_u_12:Update(p36, p37)
        end;
    end;
    v_u_34.get_move_vector = function(_) --[[ Name: get_move_vector ]] --[[ Line: 459 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:get_move_vector();
    end;
    v_u_34.is_jumping = function(_) --[[ Name: is_jumping ]] --[[ Line: 460 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:is_jumping();
    end;
    v_u_34.set_enabled = function(p38, p39) --[[ Name: set_enabled ]] --[[ Line: 462 ]]
        --[[ Upvalues: (copy 1): l_TouchEnabled_0, (copy 2): v_u_13, (copy 3): v_u_12 ]]
        if l_TouchEnabled_0 then
            v_u_13:set_functionality_enabled(p39)
        end;
        if p39 == true then
            v_u_12:Enable()
        elseif p39 == false then
            v_u_12:Disable()
        end;
        p38._enabled = p39
    end;
    v_u_34.set_touch_jump_enabled = function(_, p40) --[[ Name: set_touch_jump_enabled ]] --[[ Line: 474 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_16, (copy 3): v_u_8, (copy 4): v_u_11 ]]
        v_u_7 = p40
        if p40 then
            if v_u_8.Current == v_u_11.Touch then
                v_u_16:Enable()
            end;
        else
            v_u_16:Disable()
        end;
    end;
    v_u_34.set_next_jump_as_boosted = function(_, p41, p42) --[[ Name: set_next_jump_as_boosted ]] --[[ Line: 479 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        v_u_12:set_next_jump_as_boosted(p41, p42)
    end;
    v_u_34.force_jump = function(_) --[[ Name: force_jump ]] --[[ Line: 483 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        v_u_12:force_jump()
    end;
    v_u_34.destroy = function(_, _) --[[ Name: destroy ]] --[[ Line: 487 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_8, (copy 3): v_u_11 ]]
        if v_u_5 ~= nil then
            v_u_5:Destroy()
        end;
        v_u_8:SwitchTo(nil)
        for _, v43 in pairs(v_u_11) do
            if v43.DisconnectEvents then
                v43:DisconnectEvents()
            end;
        end;
        script:Destroy()
    end;
    script:WaitForChild("Self").OnInvoke = function() --[[ Name: OnInvoke ]] --[[ Line: 507 ]]
        --[[ Upvalues: (copy 1): v_u_34 ]]
        return v_u_34;
    end
end;
