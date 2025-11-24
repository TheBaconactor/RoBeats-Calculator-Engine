-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local _ = game:GetService("RunService")
local _ = game:GetService("UserInputService")
local s_Players_0 = game:GetService("Players")
local _ = game:GetService("StarterPlayer")
local _ = game:GetService("GamepadService")
local v_u_1 = require(script:WaitForChild("RootCamera"):WaitForChild("ClassicCamera"))()
local v_u_2 = require(script:WaitForChild("PopperCam"))
local v_u_3 = require(script:WaitForChild("TransparencyController"))()
local v_u_4 = {
    ["_enabled"] = true,
    ["destroy"] = function(_) --[[ Name: destroy ]] --[[ Line: 340 ]]
        script:Destroy()
    end
}
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local function _() --[[ Name: getCurrentCameraMode ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): s_Players_0 ]]
    local l_LocalPlayer_0 = s_Players_0.LocalPlayer
    if l_LocalPlayer_0 then
        return l_LocalPlayer_0.DevTouchCameraMode.Name;
    else
        return Enum.DevTouchCameraMovementMode.Classic.Name;
    end;
end;
local function _() --[[ Name: getCameraOcclusionMode ]] --[[ Line: 130 ]]
    --[[ Upvalues: (copy 1): s_Players_0 ]]
    local l_LocalPlayer_1 = s_Players_0.LocalPlayer
    if l_LocalPlayer_1 then
        return l_LocalPlayer_1.DevCameraOcclusionMode;
    end;
end;
local v_u_8 = CFrame.new()
local v_u_9 = CFrame.new()
local v_u_10 = -1
local v_u_11 = nil
local function f_Update(_, p12) --[[ Name: Update ]] --[[ Line: 141 ]]
    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_11, (copy 6): v_u_4, (ref 7): v_u_6, (copy 8): v_u_3 ]]
    local l_SPUtil_0 = p12.SPUtil
    if v_u_5 then
        local l_CurrentCamera_0 = workspace.CurrentCamera
        local v13 = nil
        local v14
        if l_CurrentCamera_0 then
            v14 = l_CurrentCamera_0.CFrame
            local l_CameraSubject_0 = l_CurrentCamera_0.CameraSubject
            if l_CameraSubject_0 and l_CameraSubject_0:IsA("Humanoid") then
                local l_RootPart_0 = l_CameraSubject_0.RootPart
                if l_RootPart_0 ~= nil then
                    v13 = l_RootPart_0.CFrame
                end;
            end;
        else
            v14 = nil
        end;
        local v15 = v_u_5.RotateInput.Magnitude > 0
        local v16 = l_SPUtil_0:cframe_delta(v13, v_u_8) > 0.01
        local v17 = l_SPUtil_0:cframe_delta(v14, v_u_9) > 0.01
        local v18 = v_u_10 ~= v_u_5:GetCameraZoom()
        local v19 = v_u_11 ~= v_u_4._enabled
        local v20 = v_u_5.TurningLeft or (v_u_5.TurningRight or v_u_5.GamepadPanningCamera.Magnitude > 0)
        v_u_8 = v13
        v_u_9 = v14
        v_u_10 = v_u_5:GetCameraZoom()
        v_u_11 = v_u_4._enabled
        if v15 or (v17 or (v16 or (v18 or (v19 or v20)))) then
            v_u_5:Update()
            if v_u_6 then
                v_u_6:Update(p12)
            end;
            if v_u_3 then
                v_u_3:Update()
            end;
        end;
    end;
end;
local function _(p21) --[[ Name: SetEnabledCamera ]] --[[ Line: 188 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    if v_u_5 ~= p21 then
        if v_u_5 then
            v_u_5:SetEnabled(false)
        end;
        v_u_5 = p21
        if v_u_5 then
            v_u_5:SetEnabled(true)
        end;
    end;
end;
local function _(_) --[[ Name: OnCameraMovementModeChange ]] --[[ Line: 200 ]]
    --[[ Upvalues: (copy 1): v_u_1, (ref 2): v_u_5, (copy 3): v_u_3, (ref 4): v_u_6, (copy 5): v_u_2 ]]
    local v22 = v_u_1
    if v_u_5 ~= v22 then
        if v_u_5 then
            v_u_5:SetEnabled(false)
        end;
        v_u_5 = v22
        if v_u_5 then
            v_u_5:SetEnabled(true)
        end;
    end;
    v_u_3:SetEnabled(true)
    v_u_6 = v_u_2
end;
local function _(_) end;
local function _(p23) --[[ Name: OnCameraSubjectChanged ]] --[[ Line: 253 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    v_u_3:SetSubject(p23)
end;
local function f_OnNewCamera() --[[ Name: OnNewCamera ]] --[[ Line: 257 ]]
    --[[ Upvalues: (copy 1): s_Players_0, (copy 2): v_u_1, (ref 3): v_u_5, (copy 4): v_u_3, (ref 5): v_u_6, (copy 6): v_u_2, (ref 7): v_u_7 ]]
    local v24 = v_u_1
    if v_u_5 ~= v24 then
        if v_u_5 then
            v_u_5:SetEnabled(false)
        end;
        v_u_5 = v24
        if v_u_5 then
            v_u_5:SetEnabled(true)
        end;
    end;
    v_u_3:SetEnabled(true)
    v_u_6 = v_u_2
    local l_CurrentCamera_1 = workspace.CurrentCamera
    if l_CurrentCamera_1 then
        if v_u_7 then
            v_u_7:disconnect()
        end;
        v_u_7 = l_CurrentCamera_1.Changed:connect(function(p25) --[[ Line: 265 ]]
            --[[ Upvalues: (ref 1): s_Players_0, (ref 2): v_u_1, (ref 3): v_u_5, (ref 4): v_u_3, (ref 5): v_u_6, (ref 6): v_u_2, (copy 7): l_CurrentCamera_1 ]]
            if p25 == "CameraType" then
                local v26 = v_u_1
                if v_u_5 ~= v26 then
                    if v_u_5 then
                        v_u_5:SetEnabled(false)
                    end;
                    v_u_5 = v26
                    if v_u_5 then
                        v_u_5:SetEnabled(true)
                    end;
                end;
                v_u_3:SetEnabled(true)
                v_u_6 = v_u_2
            elseif p25 == "CameraSubject" then
                v_u_3:SetSubject(l_CurrentCamera_1.CameraSubject)
            end;
        end)
        v_u_3:SetSubject(l_CurrentCamera_1.CameraSubject)
    end;
end;
local function _(_) --[[ Name: OnPlayerAdded ]] --[[ Line: 280 ]]
    --[[ Upvalues: (copy 1): f_OnNewCamera, (copy 2): s_Players_0, (copy 3): v_u_1, (ref 4): v_u_5, (copy 5): v_u_3, (ref 6): v_u_6, (copy 7): v_u_2 ]]
    f_OnNewCamera()
    local v27 = v_u_1
    if v_u_5 ~= v27 then
        if v_u_5 then
            v_u_5:SetEnabled(false)
        end;
        v_u_5 = v27
        if v_u_5 then
            v_u_5:SetEnabled(true)
        end;
    end;
    v_u_3:SetEnabled(true)
    v_u_6 = v_u_2
end;
v_u_4.connect_to_localplayer = function(_) --[[ Name: connect_to_localplayer ]] --[[ Line: 304 ]]
    --[[ Upvalues: (copy 1): s_Players_0, (copy 2): f_OnNewCamera, (copy 3): v_u_1, (ref 4): v_u_5, (copy 5): v_u_3, (ref 6): v_u_6, (copy 7): v_u_2 ]]
    f_OnNewCamera()
    local v28 = v_u_1
    if v_u_5 ~= v28 then
        if v_u_5 then
            v_u_5:SetEnabled(false)
        end;
        v_u_5 = v28
        if v_u_5 then
            v_u_5:SetEnabled(true)
        end;
    end;
    v_u_3:SetEnabled(true)
    v_u_6 = v_u_2
end;
v_u_4.set_look_behind_character = function(_, p29) --[[ Name: set_look_behind_character ]] --[[ Line: 314 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    if v_u_5 then
        v_u_5:set_look_behind_character(p29)
        v_u_5:Update()
    else
        warn("DefaultCameraScript:set_look_behind_character - EnabledCamera is nil")
    end;
end;
v_u_4.update = function(p30, p31, p32) --[[ Name: update ]] --[[ Line: 323 ]]
    --[[ Upvalues: (copy 1): f_Update ]]
    if p30._enabled ~= false then
        f_Update(p31, p32)
    end;
end;
v_u_4.set_enabled = function(p33, p34) --[[ Name: set_enabled ]] --[[ Line: 331 ]]
    --[[ Upvalues: (copy 1): f_OnNewCamera, (ref 2): v_u_5 ]]
    p33._enabled = p34
    if p33._enabled then
        f_OnNewCamera()
    elseif v_u_5 ~= nil then
        if v_u_5 then
            v_u_5:SetEnabled(false)
        end;
        v_u_5 = nil
        if v_u_5 then
            v_u_5:SetEnabled(true)
        end;
    end;
end;
script:WaitForChild("Self").OnInvoke = function() --[[ Name: OnInvoke ]] --[[ Line: 345 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    return v_u_4;
end
