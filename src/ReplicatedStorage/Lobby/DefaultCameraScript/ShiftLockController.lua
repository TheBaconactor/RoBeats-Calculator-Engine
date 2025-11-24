-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_UserInputService_0 = game:GetService("UserInputService")
local l_GameSettings_0 = UserSettings().GameSettings
local v_u_1 = {}
while not s_Players_0.LocalPlayer do
    wait()
end;
local l_LocalPlayer_0 = s_Players_0.LocalPlayer
local v_u_2 = l_LocalPlayer_0:GetMouse()
local v_u_3 = l_LocalPlayer_0:WaitForChild("PlayerGui")
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = false
local v_u_8 = false
local v_u_9 = false
v_u_1.OnShiftLockToggled = Instance.new("BindableEvent")
local function _() --[[ Name: isShiftLockMode ]] --[[ Line: 41 ]]
    --[[ Upvalues: (copy 1): l_LocalPlayer_0, (copy 2): l_GameSettings_0 ]]
    local l_DevEnableMouseLock_0 = l_LocalPlayer_0.DevEnableMouseLock
    if l_DevEnableMouseLock_0 then
        if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
            l_DevEnableMouseLock_0 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
        else
            l_DevEnableMouseLock_0 = false
        end;
    end;
    return l_DevEnableMouseLock_0;
end;
local v_u_10 = not s_UserInputService_0.TouchEnabled and l_LocalPlayer_0.DevEnableMouseLock
if v_u_10 then
    if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
        v_u_10 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
    else
        v_u_10 = false
    end;
end;
local function f_onShiftLockToggled() --[[ Name: onShiftLockToggled ]] --[[ Line: 58 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_5, (copy 3): v_u_2, (copy 4): v_u_1 ]]
    v_u_7 = not v_u_7
    if v_u_7 then
        v_u_5.Image = "rbxasset://textures/ui/mouseLock_on.png"
        v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
    else
        v_u_5.Image = "rbxasset://textures/ui/mouseLock_off.png"
        v_u_2.Icon = ""
    end;
    v_u_1.OnShiftLockToggled:Fire()
end;
local function f_initialize() --[[ Name: initialize ]] --[[ Line: 70 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5, (ref 3): v_u_7, (copy 4): f_onShiftLockToggled, (ref 5): v_u_10, (copy 6): v_u_3 ]]
    if v_u_4 then
        v_u_4:Destroy()
        v_u_4 = nil
    end;
    v_u_4 = Instance.new("ScreenGui")
    v_u_4.Name = "ControlGui"
    local l_Frame_0 = Instance.new("Frame")
    l_Frame_0.Name = "BottomLeftControl"
    l_Frame_0.Size = UDim2.new(0, 130, 0, 46)
    l_Frame_0.Position = UDim2.new(0, 0, 1, -46)
    l_Frame_0.BackgroundTransparency = 1
    l_Frame_0.Parent = v_u_4
    v_u_5 = Instance.new("ImageButton")
    v_u_5.Name = "MouseLockLabel"
    v_u_5.Size = UDim2.new(0, 31, 0, 31)
    v_u_5.Position = UDim2.new(0, 12, 0, 2)
    v_u_5.BackgroundTransparency = 1
    v_u_5.Image = v_u_7 and "rbxasset://textures/ui/mouseLock_on.png" or "rbxasset://textures/ui/mouseLock_off.png"
    v_u_5.Visible = true
    v_u_5.Parent = l_Frame_0
    v_u_5.MouseButton1Click:connect(f_onShiftLockToggled)
    v_u_4.Parent = v_u_10 and v_u_3 or nil
end;
v_u_1.IsShiftLocked = function(_) --[[ Name: IsShiftLocked ]] --[[ Line: 100 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_7 ]]
    local v11 = v_u_10
    if v11 then
        v11 = v_u_7
    end;
    return v11;
end;
v_u_1.SetIsInFirstPerson = function(_, p12) --[[ Name: SetIsInFirstPerson ]] --[[ Line: 104 ]]
    --[[ Upvalues: (ref 1): v_u_9 ]]
    v_u_9 = p12
end;
local function _(_, _, _) --[[ Line: 109 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_7, (ref 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_1 ]]
    if v_u_10 then
        v_u_7 = not v_u_7
        if v_u_7 then
            v_u_5.Image = "rbxasset://textures/ui/mouseLock_on.png"
            v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
        else
            v_u_5.Image = "rbxasset://textures/ui/mouseLock_off.png"
            v_u_2.Icon = ""
        end;
        v_u_1.OnShiftLockToggled:Fire()
    end;
end;
local function _() --[[ Name: disableShiftLock ]] --[[ Line: 115 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_10, (copy 3): v_u_2, (ref 4): v_u_6, (ref 5): v_u_8, (copy 6): v_u_1 ]]
    if v_u_4 then
        v_u_4.Parent = nil
    end;
    v_u_10 = false
    v_u_2.Icon = ""
    if v_u_6 then
        v_u_6:disconnect()
        v_u_6 = nil
    end;
    v_u_8 = false
    v_u_1.OnShiftLockToggled:Fire()
end;
local function f_onShiftInputBegan(p13, p14) --[[ Name: onShiftInputBegan ]] --[[ Line: 128 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_7, (ref 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_1 ]]
    if not p14 then
        if p13.UserInputType == Enum.UserInputType.Keyboard and (p13.KeyCode == Enum.KeyCode.LeftShift or p13.KeyCode == Enum.KeyCode.RightShift) and v_u_10 then
            v_u_7 = not v_u_7
            if v_u_7 then
                v_u_5.Image = "rbxasset://textures/ui/mouseLock_on.png"
                v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
            else
                v_u_5.Image = "rbxasset://textures/ui/mouseLock_off.png"
                v_u_2.Icon = ""
            end;
            v_u_1.OnShiftLockToggled:Fire()
        end;
    end;
end;
local function _() --[[ Name: enableShiftLock ]] --[[ Line: 137 ]]
    --[[ Upvalues: (ref 1): v_u_10, (copy 2): l_LocalPlayer_0, (copy 3): l_GameSettings_0, (ref 4): v_u_4, (copy 5): v_u_3, (ref 6): v_u_7, (copy 7): v_u_2, (copy 8): v_u_1, (ref 9): v_u_8, (ref 10): v_u_6, (copy 11): s_UserInputService_0, (copy 12): f_onShiftInputBegan ]]
    local l_DevEnableMouseLock_1 = l_LocalPlayer_0.DevEnableMouseLock
    if l_DevEnableMouseLock_1 then
        if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
            l_DevEnableMouseLock_1 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
        else
            l_DevEnableMouseLock_1 = false
        end;
    end;
    v_u_10 = l_DevEnableMouseLock_1
    if v_u_10 then
        if v_u_4 then
            v_u_4.Parent = v_u_3
        end;
        if v_u_7 then
            v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
            v_u_1.OnShiftLockToggled:Fire()
        end;
        if not v_u_8 then
            v_u_6 = s_UserInputService_0.InputBegan:connect(f_onShiftInputBegan)
            v_u_8 = true
        end;
    end;
end;
l_GameSettings_0.Changed:connect(function(p15) --[[ Line: 154 ]]
    --[[ Upvalues: (copy 1): l_GameSettings_0, (ref 2): v_u_10, (copy 3): l_LocalPlayer_0, (ref 4): v_u_4, (copy 5): v_u_3, (ref 6): v_u_7, (copy 7): v_u_2, (copy 8): v_u_1, (ref 9): v_u_8, (ref 10): v_u_6, (copy 11): s_UserInputService_0, (copy 12): f_onShiftInputBegan ]]
    if p15 == "ControlMode" then
        if l_GameSettings_0.ControlMode ~= Enum.ControlMode.MouseLockSwitch then
            if v_u_4 then
                v_u_4.Parent = nil
            end;
            v_u_10 = false
            v_u_2.Icon = ""
            if v_u_6 then
                v_u_6:disconnect()
                v_u_6 = nil
            end;
            v_u_8 = false
            v_u_1.OnShiftLockToggled:Fire()
            return;
        end;
        local l_DevEnableMouseLock_2 = l_LocalPlayer_0.DevEnableMouseLock
        if l_DevEnableMouseLock_2 then
            if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
                l_DevEnableMouseLock_2 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
            else
                l_DevEnableMouseLock_2 = false
            end;
        end;
        v_u_10 = l_DevEnableMouseLock_2
        if v_u_10 then
            if v_u_4 then
                v_u_4.Parent = v_u_3
            end;
            if v_u_7 then
                v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
                v_u_1.OnShiftLockToggled:Fire()
            end;
            if not v_u_8 then
                v_u_6 = s_UserInputService_0.InputBegan:connect(f_onShiftInputBegan)
                v_u_8 = true
                return;
            end;
        end;
    elseif p15 == "ComputerMovementMode" then
        if l_GameSettings_0.ComputerMovementMode == Enum.ComputerMovementMode.ClickToMove then
            if v_u_4 then
                v_u_4.Parent = nil
            end;
            v_u_10 = false
            v_u_2.Icon = ""
            if v_u_6 then
                v_u_6:disconnect()
                v_u_6 = nil
            end;
            v_u_8 = false
            v_u_1.OnShiftLockToggled:Fire()
            return;
        end;
        local l_DevEnableMouseLock_3 = l_LocalPlayer_0.DevEnableMouseLock
        if l_DevEnableMouseLock_3 then
            if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
                l_DevEnableMouseLock_3 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
            else
                l_DevEnableMouseLock_3 = false
            end;
        end;
        v_u_10 = l_DevEnableMouseLock_3
        if v_u_10 then
            if v_u_4 then
                v_u_4.Parent = v_u_3
            end;
            if v_u_7 then
                v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
                v_u_1.OnShiftLockToggled:Fire()
            end;
            if not v_u_8 then
                v_u_6 = s_UserInputService_0.InputBegan:connect(f_onShiftInputBegan)
                v_u_8 = true
            end;
        end;
    end;
end)
l_LocalPlayer_0.Changed:connect(function(p16) --[[ Line: 170 ]]
    --[[ Upvalues: (copy 1): l_LocalPlayer_0, (ref 2): v_u_10, (copy 3): l_GameSettings_0, (ref 4): v_u_4, (copy 5): v_u_3, (ref 6): v_u_7, (copy 7): v_u_2, (copy 8): v_u_1, (ref 9): v_u_8, (ref 10): v_u_6, (copy 11): s_UserInputService_0, (copy 12): f_onShiftInputBegan ]]
    if p16 == "DevEnableMouseLock" then
        if not l_LocalPlayer_0.DevEnableMouseLock then
            if v_u_4 then
                v_u_4.Parent = nil
            end;
            v_u_10 = false
            v_u_2.Icon = ""
            if v_u_6 then
                v_u_6:disconnect()
                v_u_6 = nil
            end;
            v_u_8 = false
            v_u_1.OnShiftLockToggled:Fire()
            return;
        end;
        local l_DevEnableMouseLock_4 = l_LocalPlayer_0.DevEnableMouseLock
        if l_DevEnableMouseLock_4 then
            if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
                l_DevEnableMouseLock_4 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
            else
                l_DevEnableMouseLock_4 = false
            end;
        end;
        v_u_10 = l_DevEnableMouseLock_4
        if v_u_10 then
            if v_u_4 then
                v_u_4.Parent = v_u_3
            end;
            if v_u_7 then
                v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
                v_u_1.OnShiftLockToggled:Fire()
            end;
            if not v_u_8 then
                v_u_6 = s_UserInputService_0.InputBegan:connect(f_onShiftInputBegan)
                v_u_8 = true
                return;
            end;
        end;
    elseif p16 == "DevComputerMovementMode" then
        if l_LocalPlayer_0.DevComputerMovementMode == Enum.DevComputerMovementMode.ClickToMove or l_LocalPlayer_0.DevComputerMovementMode == Enum.DevComputerMovementMode.Scriptable then
            if v_u_4 then
                v_u_4.Parent = nil
            end;
            v_u_10 = false
            v_u_2.Icon = ""
            if v_u_6 then
                v_u_6:disconnect()
                v_u_6 = nil
            end;
            v_u_8 = false
            v_u_1.OnShiftLockToggled:Fire()
            return;
        end;
        local l_DevEnableMouseLock_5 = l_LocalPlayer_0.DevEnableMouseLock
        if l_DevEnableMouseLock_5 then
            if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
                l_DevEnableMouseLock_5 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
            else
                l_DevEnableMouseLock_5 = false
            end;
        end;
        v_u_10 = l_DevEnableMouseLock_5
        if v_u_10 then
            if v_u_4 then
                v_u_4.Parent = v_u_3
            end;
            if v_u_7 then
                v_u_2.Icon = "rbxasset://textures/MouseLockedCursor.png"
                v_u_1.OnShiftLockToggled:Fire()
            end;
            if not v_u_8 then
                v_u_6 = s_UserInputService_0.InputBegan:connect(f_onShiftInputBegan)
                v_u_8 = true
            end;
        end;
    end;
end)
l_LocalPlayer_0.CharacterAdded:connect(function(_) --[[ Line: 188 ]]
    --[[ Upvalues: (copy 1): s_UserInputService_0, (copy 2): f_initialize ]]
    if not s_UserInputService_0.TouchEnabled then
        f_initialize()
    end;
end)
if not s_UserInputService_0.TouchEnabled then
    f_initialize()
    local l_DevEnableMouseLock_6 = l_LocalPlayer_0.DevEnableMouseLock
    if l_DevEnableMouseLock_6 then
        if l_GameSettings_0.ControlMode == Enum.ControlMode.MouseLockSwitch and (l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.ClickToMove and l_GameSettings_0.ComputerMovementMode ~= Enum.ComputerMovementMode.ClickToMove) then
            l_DevEnableMouseLock_6 = l_LocalPlayer_0.DevComputerMovementMode ~= Enum.DevComputerMovementMode.Scriptable
        else
            l_DevEnableMouseLock_6 = false
        end;
    end;
    if l_DevEnableMouseLock_6 then
        local _ = s_UserInputService_0.InputBegan:connect(f_onShiftInputBegan)
        local _ = true
    end;
end;
return v_u_1;
