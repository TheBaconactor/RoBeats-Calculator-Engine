-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local v1 = {}
local v_u_2 = require(script.Parent)
local s_Players_0 = game:GetService("Players")
local _ = game:GetService("RunService")
local s_UserInputService_0 = game:GetService("UserInputService")
local s_ContextActionService_0 = game:GetService("ContextActionService")
local _ = game:GetService("StarterPlayer")
local s_GamepadService_0 = game:GetService("GamepadService")
local v_u_3 = Vector3.new(0, 0, 0)
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = 0
v1.get_allocid = function(_) --[[ Name: get_allocid ]] --[[ Line: 38 ]]
    --[[ Upvalues: (ref 1): v_u_8 ]]
    return v_u_8;
end;
while not s_Players_0.LocalPlayer do
    wait()
end;
local l_LocalPlayer_0 = s_Players_0.LocalPlayer
local function _() --[[ Name: stop_all_movement ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_3 ]]
    if v_u_2 then
        v_u_2:AddToPlayerMovement(-v_u_3)
    end;
    v_u_3 = Vector3.new(0, 0, 0)
    v_u_2:SetIsJumping(false)
end;
local function f_assignActivateGamepad() --[[ Name: assignActivateGamepad ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): s_UserInputService_0, (ref 2): v_u_4 ]]
    local v9 = s_UserInputService_0:GetConnectedGamepads()
    if #v9 > 0 then
        for v10 = 1, #v9 do
            if v_u_4 == nil then
                v_u_4 = v9[v10]
            elseif v9[v10].Value < v_u_4.Value then
                v_u_4 = v9[v10]
            end;
        end;
    end;
    if v_u_4 == nil then
        v_u_4 = Enum.UserInputType.Gamepad1
    end;
end;
v1.Enable = function(_) --[[ Name: Enable ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): l_LocalPlayer_0, (copy 2): s_UserInputService_0, (copy 3): v_u_2, (ref 4): v_u_3, (ref 5): v_u_4, (copy 6): s_ContextActionService_0, (copy 7): f_assignActivateGamepad, (ref 8): v_u_5, (ref 9): v_u_6, (ref 10): v_u_7, (copy 11): s_GamepadService_0 ]]
    local v_u_11 = 0
    local v_u_12 = 0
    local v_u_13 = 0
    local v_u_14 = 0
    local function _(p15, p16) --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): s_UserInputService_0 ]]
        return s_UserInputService_0:GamepadSupports(p15, p16);
    end;
    local function v19(_, p17, p18) --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3 ]]
        if p17 == Enum.UserInputState.Cancel then
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(0, 0, 0)
            return;
        elseif p18.Position.magnitude > 0.22 then
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(p18.Position.X, 0, -p18.Position.Y)
            v_u_2:AddToPlayerMovement(v_u_3)
        else
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(0, 0, 0)
        end;
    end;
    local function _(p20) --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): s_UserInputService_0, (ref 2): l_LocalPlayer_0, (ref 3): v_u_2, (ref 4): v_u_3, (ref 5): v_u_13, (ref 6): v_u_14, (ref 7): v_u_11, (ref 8): v_u_12 ]]
        if not s_UserInputService_0:GamepadSupports(p20, Enum.KeyCode.Thumbstick1) and (l_LocalPlayer_0 and l_LocalPlayer_0.Character) then
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(v_u_13 + v_u_14, 0, v_u_11 + v_u_12)
            v_u_2:AddToPlayerMovement(v_u_3)
        end;
    end;
    local function v23(_, p21, p22) --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): s_UserInputService_0, (ref 3): l_LocalPlayer_0, (ref 4): v_u_2, (ref 5): v_u_3, (ref 6): v_u_13, (ref 7): v_u_14, (ref 8): v_u_12 ]]
        if p21 == Enum.UserInputState.End then
            v_u_11 = -1
        elseif p21 == Enum.UserInputState.Begin or p21 == Enum.UserInputState.Cancel then
            v_u_11 = 0
        end;
        if not s_UserInputService_0:GamepadSupports(p22.UserInputType, Enum.KeyCode.Thumbstick1) and (l_LocalPlayer_0 and l_LocalPlayer_0.Character) then
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(v_u_13 + v_u_14, 0, v_u_11 + v_u_12)
            v_u_2:AddToPlayerMovement(v_u_3)
        end;
    end;
    local function v26(_, p24, p25) --[[ Line: 154 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): s_UserInputService_0, (ref 3): l_LocalPlayer_0, (ref 4): v_u_2, (ref 5): v_u_3, (ref 6): v_u_13, (ref 7): v_u_14, (ref 8): v_u_11 ]]
        if p24 == Enum.UserInputState.End then
            v_u_12 = 1
        elseif p24 == Enum.UserInputState.Begin or p24 == Enum.UserInputState.Cancel then
            v_u_12 = 0
        end;
        if not s_UserInputService_0:GamepadSupports(p25.UserInputType, Enum.KeyCode.Thumbstick1) and (l_LocalPlayer_0 and l_LocalPlayer_0.Character) then
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(v_u_13 + v_u_14, 0, v_u_11 + v_u_12)
            v_u_2:AddToPlayerMovement(v_u_3)
        end;
    end;
    local function v29(_, p27, p28) --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): v_u_13, (ref 2): s_UserInputService_0, (ref 3): l_LocalPlayer_0, (ref 4): v_u_2, (ref 5): v_u_3, (ref 6): v_u_14, (ref 7): v_u_11, (ref 8): v_u_12 ]]
        if p27 == Enum.UserInputState.End then
            v_u_13 = -1
        elseif p27 == Enum.UserInputState.Begin or p27 == Enum.UserInputState.Cancel then
            v_u_13 = 0
        end;
        if not s_UserInputService_0:GamepadSupports(p28.UserInputType, Enum.KeyCode.Thumbstick1) and (l_LocalPlayer_0 and l_LocalPlayer_0.Character) then
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(v_u_13 + v_u_14, 0, v_u_11 + v_u_12)
            v_u_2:AddToPlayerMovement(v_u_3)
        end;
    end;
    local function v32(_, p30, p31) --[[ Line: 174 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): s_UserInputService_0, (ref 3): l_LocalPlayer_0, (ref 4): v_u_2, (ref 5): v_u_3, (ref 6): v_u_13, (ref 7): v_u_11, (ref 8): v_u_12 ]]
        if p30 == Enum.UserInputState.End then
            v_u_14 = 1
        elseif p30 == Enum.UserInputState.Begin or p30 == Enum.UserInputState.Cancel then
            v_u_14 = 0
        end;
        if not s_UserInputService_0:GamepadSupports(p31.UserInputType, Enum.KeyCode.Thumbstick1) and (l_LocalPlayer_0 and l_LocalPlayer_0.Character) then
            v_u_2:AddToPlayerMovement(-v_u_3)
            v_u_3 = Vector3.new(v_u_13 + v_u_14, 0, v_u_11 + v_u_12)
            v_u_2:AddToPlayerMovement(v_u_3)
        end;
    end;
    local function _() --[[ Name: setActivateGamepad ]] --[[ Line: 184 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): s_ContextActionService_0, (ref 3): f_assignActivateGamepad ]]
        if v_u_4 then
            s_ContextActionService_0:UnbindActivate(v_u_4, Enum.KeyCode.ButtonR2)
        end;
        f_assignActivateGamepad()
        if v_u_4 then
            s_ContextActionService_0:BindActivate(v_u_4, Enum.KeyCode.ButtonR2)
        end;
    end;
    s_ContextActionService_0:BindAction("JumpButton", function(_, p33, p34) --[[ Line: 122 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        if p33 == Enum.UserInputState.Cancel then
            v_u_2:SetIsJumping(false)
        else
            v_u_2:SetIsJumping(p34.UserInputState == Enum.UserInputState.Begin)
        end;
    end, false, Enum.KeyCode.ButtonY)
    s_ContextActionService_0:BindAction("MoveThumbstick", v19, false, Enum.KeyCode.Thumbstick1)
    s_ContextActionService_0:BindAction("forwardDpad", v23, false, Enum.KeyCode.DPadUp)
    s_ContextActionService_0:BindAction("backwardDpad", v26, false, Enum.KeyCode.DPadDown)
    s_ContextActionService_0:BindAction("leftDpad", v29, false, Enum.KeyCode.DPadLeft)
    s_ContextActionService_0:BindAction("rightDpad", v32, false, Enum.KeyCode.DPadRight)
    if v_u_4 then
        s_ContextActionService_0:UnbindActivate(v_u_4, Enum.KeyCode.ButtonR2)
    end;
    f_assignActivateGamepad()
    if v_u_4 then
        s_ContextActionService_0:BindActivate(v_u_4, Enum.KeyCode.ButtonR2)
    end;
    v_u_5 = s_UserInputService_0.GamepadDisconnected:connect(function(p35) --[[ Line: 208 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2, (ref 3): v_u_3, (ref 4): s_ContextActionService_0, (ref 5): f_assignActivateGamepad ]]
        if v_u_4 == p35 then
            if v_u_2 then
                v_u_2:AddToPlayerMovement(-v_u_3)
            end;
            v_u_3 = Vector3.new(0, 0, 0)
            v_u_2:SetIsJumping(false)
            v_u_4 = nil
            if v_u_4 then
                s_ContextActionService_0:UnbindActivate(v_u_4, Enum.KeyCode.ButtonR2)
            end;
            f_assignActivateGamepad()
            if v_u_4 then
                s_ContextActionService_0:BindActivate(v_u_4, Enum.KeyCode.ButtonR2)
            end;
        end;
    end)
    v_u_6 = s_UserInputService_0.GamepadConnected:connect(function(_) --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): s_ContextActionService_0, (ref 3): f_assignActivateGamepad ]]
        if v_u_4 == nil then
            if v_u_4 then
                s_ContextActionService_0:UnbindActivate(v_u_4, Enum.KeyCode.ButtonR2)
            end;
            f_assignActivateGamepad()
            if v_u_4 then
                s_ContextActionService_0:BindActivate(v_u_4, Enum.KeyCode.ButtonR2)
            end;
        end;
    end)
    v_u_7 = s_GamepadService_0:GetPropertyChangedSignal("GamepadCursorEnabled"):Connect(function() --[[ Line: 223 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3 ]]
        if v_u_2 then
            v_u_2:AddToPlayerMovement(-v_u_3)
        end;
        v_u_3 = Vector3.new(0, 0, 0)
        v_u_2:SetIsJumping(false)
    end)
    s_GamepadService_0:DisableGamepadCursor()
end;
v1.Disable = function(_) --[[ Name: Disable ]] --[[ Line: 230 ]]
    --[[ Upvalues: (copy 1): s_ContextActionService_0, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_6, (ref 5): v_u_7, (copy 6): v_u_2, (ref 7): v_u_3, (copy 8): s_GamepadService_0 ]]
    s_ContextActionService_0:UnbindAction("forwardDpad")
    s_ContextActionService_0:UnbindAction("backwardDpad")
    s_ContextActionService_0:UnbindAction("leftDpad")
    s_ContextActionService_0:UnbindAction("rightDpad")
    s_ContextActionService_0:UnbindAction("MoveThumbstick")
    s_ContextActionService_0:UnbindAction("JumpButton")
    s_ContextActionService_0:UnbindActivate(v_u_4, Enum.KeyCode.ButtonR2)
    if v_u_5 then
        v_u_5:disconnect()
    end;
    if v_u_6 then
        v_u_6:disconnect()
    end;
    if v_u_7 then
        v_u_7:disconnect()
    end;
    v_u_4 = nil
    if v_u_2 then
        v_u_2:AddToPlayerMovement(-v_u_3)
    end;
    v_u_3 = Vector3.new(0, 0, 0)
    v_u_2:SetIsJumping(false)
    v_u_2:SetIsJumping(false)
    s_GamepadService_0:DisableGamepadCursor()
end;
s_GamepadService_0:DisableGamepadCursor()
return v1;
