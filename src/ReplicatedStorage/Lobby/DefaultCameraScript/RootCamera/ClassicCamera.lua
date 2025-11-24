-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local _ = game:GetService("UserInputService")
local _, _ = pcall(function() --[[ Line: 3 ]]
    return game:GetService("VRService");
end)
local v_u_1 = require(script.Parent)
local v_u_2 = Vector2.new(0, 0)
local function _(p3, p4, p5) --[[ Name: clamp ]] --[[ Line: 17 ]]
    if p3 <= p4 then
        return math.min(p4, (math.max(p3, p5)));
    end;
    print("Trying to clamp when low:", p3, "is larger than high:", p4, "returning input value.")
    return p5;
end;
local function _(p6) --[[ Name: IsFinite ]] --[[ Line: 25 ]]
    local v7
    if p6 == p6 and p6 ~= (1 / 0) then
        v7 = p6 ~= (-1 / 0)
    else
        v7 = false
    end;
    return v7;
end;
local function _(p8) --[[ Name: IsFiniteVector3 ]] --[[ Line: 29 ]]
    local l_x_0 = p8.x
    local v9
    if l_x_0 == l_x_0 and l_x_0 ~= (1 / 0) then
        v9 = l_x_0 ~= (-1 / 0)
    else
        v9 = false
    end;
    if v9 then
        local l_y_0 = p8.y
        if l_y_0 == l_y_0 and l_y_0 ~= (1 / 0) then
            v9 = l_y_0 ~= (-1 / 0)
        else
            v9 = false
        end;
        if v9 then
            local l_z_0 = p8.z
            if l_z_0 == l_z_0 and l_z_0 ~= (1 / 0) then
                v9 = l_z_0 ~= (-1 / 0)
            else
                v9 = false
            end;
        end;
    end;
    return v9;
end;
local function _(p10, p11) --[[ Name: findAngleBetweenXZVectors ]] --[[ Line: 35 ]]
    return math.atan2(p11.X * p10.Z - p11.Z * p10.X, p11.X * p10.X + p11.Z * p10.Z);
end;
return function() --[[ Name: CreateClassicCamera ]] --[[ Line: 39 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): s_Players_0 ]]
    local v_u_12 = v_u_1()
    local v_u_13 = 0
    local v_u_14 = tick()
    v_u_12.LastUserPanCamera = tick()
    v_u_12.Update = function(p15) --[[ Name: Update ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): s_Players_0, (copy 3): v_u_12, (ref 4): v_u_2, (ref 5): v_u_13 ]]
        local v16 = tick()
        local v17 = p15.UserPanningTheCamera == true
        local l_CurrentCamera_0 = workspace.CurrentCamera
        local l_LocalPlayer_0 = s_Players_0.LocalPlayer
        p15:GetHumanoid()
        local v18
        if l_CurrentCamera_0 then
            v18 = l_CurrentCamera_0.CameraSubject
        else
            v18 = l_CurrentCamera_0
        end;
        local v19
        if v18 then
            v19 = v18:IsA("VehicleSeat")
        else
            v19 = v18
        end;
        if v18 then
            v18 = v18:IsA("SkateboardPlatform")
        end;
        if v_u_14 == nil or v16 - v_u_14 > 1 then
            v_u_12:ResetCameraLook()
            p15.LastCameraTransform = nil
        end;
        if v_u_14 then
            local v20 = p15:UpdateGamepad()
            local v21 = math.min(0.1, v16 - v_u_14)
            if v20 ~= v_u_2 then
                p15.RotateInput = p15.RotateInput + v20 * v21
                v17 = true
            end;
            local v22 = 0
            if not (v19 or v18) then
                v22 = v22 + (p15.TurningLeft and -120 or 0) + (p15.TurningRight and 120 or 0)
            end;
            if v22 ~= 0 then
                p15.RotateInput = p15.RotateInput + Vector2.new(math.rad(v22 * v21), 0)
                v17 = true
            end;
        end;
        if v17 then
            v_u_13 = 0
            v_u_12.LastUserPanCamera = tick()
        end;
        local v23 = p15:GetSubjectPosition()
        if v23 and (l_LocalPlayer_0 and l_CurrentCamera_0) then
            local v24 = p15:GetCameraZoom()
            local v25 = v24 < 0.5 and 0.5 or v24
            l_CurrentCamera_0.Focus = CFrame.new(v23)
            local v26 = p15:GetCameraHeight()
            local l_p_0 = l_CurrentCamera_0.Focus.p
            local v27 = p15:RotateCamera(p15:GetCameraLook(), p15.RotateInput)
            p15.RotateInput = v_u_2
            l_CurrentCamera_0.CFrame = CFrame.new(l_p_0 - v25 * v27, l_p_0) + Vector3.new(0, v26, 0)
            p15.LastCameraTransform = l_CurrentCamera_0.CFrame
            p15.LastCameraFocus = l_CurrentCamera_0.Focus
            p15.LastSubjectCFrame = nil
        end;
        v_u_14 = v16
    end;
    return v_u_12;
end;
