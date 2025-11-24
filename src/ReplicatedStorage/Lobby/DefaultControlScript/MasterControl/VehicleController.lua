-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local s_ContextActionService_0 = game:GetService("ContextActionService")
local s_Players_0 = game:GetService("Players")
local s_RunService_0 = game:GetService("RunService")
local v_u_1 = require(script.Parent)
local v2 = {}
while not s_Players_0.LocalPlayer do
    wait()
end;
local l_LocalPlayer_0 = s_Players_0.LocalPlayer
local v_u_3 = nil
local v_u_4 = 0
local v_u_5 = 0
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = false
local v_u_9 = false
local v_u_10 = false
local v_u_11 = false
local function f_onThrottleAccel(_, p12, _) --[[ Name: onThrottleAccel ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_4, (ref 3): v_u_9, (ref 4): v_u_8 ]]
    v_u_1:AddToPlayerMovement((Vector3.new(0, 0, -v_u_4)))
    v_u_4 = (p12 == Enum.UserInputState.End or v_u_9) and 0 or -1
    v_u_1:AddToPlayerMovement((Vector3.new(0, 0, v_u_4)))
    v_u_8 = p12 ~= Enum.UserInputState.End
    if p12 == Enum.UserInputState.End and v_u_9 then
        v_u_4 = 1
        v_u_1:AddToPlayerMovement((Vector3.new(0, 0, v_u_4)))
    end;
end;
local function f_onThrottleDeccel(_, p13, _) --[[ Name: onThrottleDeccel ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_4, (ref 3): v_u_8, (ref 4): v_u_9 ]]
    v_u_1:AddToPlayerMovement((Vector3.new(0, 0, -v_u_4)))
    v_u_4 = (p13 == Enum.UserInputState.End or v_u_8) and 0 or 1
    v_u_1:AddToPlayerMovement((Vector3.new(0, 0, v_u_4)))
    v_u_9 = p13 ~= Enum.UserInputState.End
    if p13 == Enum.UserInputState.End and v_u_8 then
        v_u_4 = -1
        v_u_1:AddToPlayerMovement((Vector3.new(0, 0, v_u_4)))
    end;
end;
local function f_onSteerRight(_, p14, _) --[[ Name: onSteerRight ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_5, (ref 3): v_u_11, (ref 4): v_u_10 ]]
    v_u_1:AddToPlayerMovement((Vector3.new(-v_u_5, 0, 0)))
    v_u_5 = (p14 == Enum.UserInputState.End or v_u_11) and 0 or 1
    v_u_1:AddToPlayerMovement((Vector3.new(v_u_5, 0, 0)))
    v_u_10 = p14 ~= Enum.UserInputState.End
    if p14 == Enum.UserInputState.End and v_u_11 then
        v_u_5 = -1
        v_u_1:AddToPlayerMovement((Vector3.new(v_u_5, 0, 0)))
    end;
end;
local function f_onSteerLeft(_, p15, _) --[[ Name: onSteerLeft ]] --[[ Line: 70 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_5, (ref 3): v_u_10, (ref 4): v_u_11 ]]
    v_u_1:AddToPlayerMovement((Vector3.new(-v_u_5, 0, 0)))
    v_u_5 = (p15 == Enum.UserInputState.End or v_u_10) and 0 or -1
    v_u_1:AddToPlayerMovement((Vector3.new(v_u_5, 0, 0)))
    v_u_11 = p15 ~= Enum.UserInputState.End
    if p15 == Enum.UserInputState.End and v_u_10 then
        v_u_5 = 1
        v_u_1:AddToPlayerMovement((Vector3.new(v_u_5, 0, 0)))
    end;
end;
local function f_getHumanoid() --[[ Name: getHumanoid ]] --[[ Line: 81 ]]
    --[[ Upvalues: (copy 1): l_LocalPlayer_0 ]]
    local v16 = l_LocalPlayer_0
    if v16 then
        v16 = l_LocalPlayer_0.Character
    end;
    if v16 then
        for _, v17 in pairs(v16:GetChildren()) do
            if v17:IsA("Humanoid") then
                return v17;
            end;
        end;
    end;
end;
local function _(p18) --[[ Name: getClosestFittingValue ]] --[[ Line: 92 ]]
    return p18 > 0.5 and 1 or (p18 < -0.5 and -1 or 0);
end;
local function f_onRenderStepped() --[[ Name: onRenderStepped ]] --[[ Line: 101 ]]
    --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_1, (ref 3): v_u_4 ]]
    if v_u_3 then
        local v19 = v_u_1:GetMoveVector()
        game:GetService("UserInputService"):GetGamepadConnected(Enum.UserInputType.Gamepad1)
        local v20 = v_u_3
        local v21 = -v19.z
        v20.Throttle = v21 > 0.5 and 1 or (v21 < -0.5 and -1 or 0)
        local v22 = v_u_3
        local l_x_0 = v19.x
        v22.Steer = l_x_0 > 0.5 and 1 or (l_x_0 < -0.5 and -1 or 0)
    end;
end;
local function f_onSeated(p23, p24) --[[ Name: onSeated ]] --[[ Line: 113 ]]
    --[[ Upvalues: (ref 1): v_u_3, (copy 2): s_ContextActionService_0, (copy 3): f_onThrottleAccel, (copy 4): f_onThrottleDeccel, (copy 5): f_onSteerRight, (copy 6): f_onSteerLeft, (copy 7): s_RunService_0, (copy 8): f_onRenderStepped, (ref 9): v_u_7, (copy 10): v_u_1, (ref 11): v_u_5, (ref 12): v_u_4 ]]
    if p23 then
        if p24 and p24:IsA("VehicleSeat") then
            v_u_3 = p24
            s_ContextActionService_0:BindAction("throttleAccel", f_onThrottleAccel, false, Enum.KeyCode.ButtonR2)
            s_ContextActionService_0:BindAction("throttleDeccel", f_onThrottleDeccel, false, Enum.KeyCode.ButtonL2)
            s_ContextActionService_0:BindAction("arrowSteerRight", f_onSteerRight, false, Enum.KeyCode.Right)
            s_ContextActionService_0:BindAction("arrowSteerLeft", f_onSteerLeft, false, Enum.KeyCode.Left)
            if not pcall(function() --[[ Line: 123 ]]
                --[[ Upvalues: (ref 1): s_RunService_0, (ref 2): f_onRenderStepped ]]
                s_RunService_0:BindToRenderStep("VehicleControlStep", Enum.RenderPriority.Input.Value, f_onRenderStepped)
            end) then
                if not v_u_7 then
                    v_u_7 = s_RunService_0.RenderStepped:connect(f_onRenderStepped)
                end;
            end;
        end;
    else
        v_u_3 = nil
        s_ContextActionService_0:UnbindAction("throttleAccel")
        s_ContextActionService_0:UnbindAction("throttleDeccel")
        s_ContextActionService_0:UnbindAction("arrowSteerRight")
        s_ContextActionService_0:UnbindAction("arrowSteerLeft")
        v_u_1:AddToPlayerMovement((Vector3.new(-v_u_5, 0, -v_u_4)))
        v_u_4 = 0
        v_u_5 = 0
        if not pcall(function() --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): s_RunService_0 ]]
            s_RunService_0:UnbindFromRenderStep("VehicleControlStep")
        end) and v_u_7 then
            v_u_7:disconnect()
            v_u_7 = nil
        end;
    end;
end;
local function f_CharacterAdded(_) --[[ Name: CharacterAdded ]] --[[ Line: 149 ]]
    --[[ Upvalues: (copy 1): f_getHumanoid, (ref 2): v_u_6, (copy 3): f_onSeated ]]
    local v25 = f_getHumanoid()
    while not v25 do
        wait()
        v25 = f_getHumanoid()
    end;
    if v_u_6 then
        v_u_6:disconnect()
        v_u_6 = nil
    end;
    v_u_6 = v25.Seated:connect(f_onSeated)
end;
if l_LocalPlayer_0.Character then
    f_CharacterAdded(l_LocalPlayer_0.Character)
end;
l_LocalPlayer_0.CharacterAdded:connect(f_CharacterAdded)
return v2;
