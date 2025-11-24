-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_UserInputService_0 = game:GetService("UserInputService")
local v1, v2 = pcall(function() --[[ Line: 3 ]]
    return game:GetService("VRService");
end)
local v_u_3 = v1 and v2 and v2 or s_UserInputService_0
local v_u_4 = require(script.Parent)
local function _(p5, p6, p7) --[[ Name: clamp ]] --[[ Line: 14 ]]
    if p5 <= p6 then
        return math.min(p6, (math.max(p5, p7)));
    end;
    print("Trying to clamp when low:", p5, "is larger than high:", p6, "returning input value.")
    return p7;
end;
local function _(p8) --[[ Name: IsFinite ]] --[[ Line: 22 ]]
    local v9
    if p8 == p8 and p8 ~= (1 / 0) then
        v9 = p8 ~= (-1 / 0)
    else
        v9 = false
    end;
    return v9;
end;
local function _(p10) --[[ Name: IsFiniteVector3 ]] --[[ Line: 26 ]]
    local l_x_0 = p10.x
    local v11
    if l_x_0 == l_x_0 and l_x_0 ~= (1 / 0) then
        v11 = l_x_0 ~= (-1 / 0)
    else
        v11 = false
    end;
    if v11 then
        local l_y_0 = p10.y
        if l_y_0 == l_y_0 and l_y_0 ~= (1 / 0) then
            v11 = l_y_0 ~= (-1 / 0)
        else
            v11 = false
        end;
        if v11 then
            local l_z_0 = p10.z
            if l_z_0 == l_z_0 and l_z_0 ~= (1 / 0) then
                v11 = l_z_0 ~= (-1 / 0)
            else
                v11 = false
            end;
        end;
    end;
    return v11;
end;
local function _(p12, p13) --[[ Name: findAngleBetweenXZVectors ]] --[[ Line: 31 ]]
    return math.atan2(p13.X * p12.Z - p13.Z * p12.X, p13.X * p12.X + p13.Z * p12.Z);
end;
return function() --[[ Name: CreateFollowCamera ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): s_Players_0, (ref 3): v_u_3 ]]
    local v_u_14 = v_u_4()
    local v_u_15 = 0
    local v_u_16 = tick()
    v_u_14.LastUserPanCamera = tick()
    v_u_14.Update = function(p17) --[[ Name: Update ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): s_Players_0, (copy 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_3 ]]
        local v18 = tick()
        local v19 = v18 - v_u_16
        local v20 = p17.UserPanningTheCamera == true
        local l_CurrentCamera_0 = workspace.CurrentCamera
        local l_LocalPlayer_0 = s_Players_0.LocalPlayer
        local v21 = p17:GetHumanoid()
        local v22
        if l_CurrentCamera_0 then
            v22 = l_CurrentCamera_0.CameraSubject
        else
            v22 = l_CurrentCamera_0
        end;
        local v23
        if v21 then
            v23 = v21:GetState() == Enum.HumanoidStateType.Climbing
        else
            v23 = v21
        end;
        local v24
        if v22 then
            v24 = v22:IsA("VehicleSeat")
        else
            v24 = v22
        end;
        local v25
        if v22 then
            v25 = v22:IsA("SkateboardPlatform")
        else
            v25 = v22
        end;
        if v_u_16 == nil or v18 - v_u_16 > 1 then
            v_u_14:ResetCameraLook()
            p17.LastCameraTransform = nil
        end;
        if v_u_16 then
            if p17:ShouldUseVRRotation() then
                p17.RotateInput = p17.RotateInput + p17:GetVRRotationInput()
            else
                local v26 = math.min(0.1, v18 - v_u_16)
                local v27 = 0
                if not (v24 or v25) then
                    v27 = v27 + (p17.TurningLeft and -120 or 0) + (p17.TurningRight and 120 or 0)
                end;
                local v28 = p17:UpdateGamepad()
                if v28 ~= Vector2.new(0, 0) then
                    p17.RotateInput = p17.RotateInput + v28 * v26
                    v20 = true
                end;
                if v27 ~= 0 then
                    p17.RotateInput = p17.RotateInput + Vector2.new(math.rad(v27 * v26), 0)
                    v20 = true
                end;
            end;
        end;
        if v20 then
            v_u_15 = 0
            v_u_14.LastUserPanCamera = tick()
        end;
        local v29 = v18 - v_u_14.LastUserPanCamera < 2
        local v30 = p17:GetSubjectPosition()
        if v30 and (l_LocalPlayer_0 and l_CurrentCamera_0) then
            local v31 = p17:GetCameraZoom()
            local v32 = v31 < 0.5 and 0.5 or v31
            if p17:GetShiftLock() and not p17:IsInFirstPerson() then
                local v33 = (p17:RotateCamera(p17:GetCameraLook(), p17.RotateInput) * Vector3.new(1, 0, 1)):Cross(Vector3.new(0, 1, 0)).unit * 1.75
                local l_x_1 = v33.x
                local v34
                if l_x_1 == l_x_1 and l_x_1 ~= (1 / 0) then
                    v34 = l_x_1 ~= (-1 / 0)
                else
                    v34 = false
                end;
                if v34 then
                    local l_y_1 = v33.y
                    if l_y_1 == l_y_1 and l_y_1 ~= (1 / 0) then
                        v34 = l_y_1 ~= (-1 / 0)
                    else
                        v34 = false
                    end;
                    if v34 then
                        local l_z_1 = v33.z
                        if l_z_1 == l_z_1 and l_z_1 ~= (1 / 0) then
                            v34 = l_z_1 ~= (-1 / 0)
                        else
                            v34 = false
                        end;
                    end;
                end;
                if v34 then
                    v30 = v30 + v33
                end;
            elseif p17.LastCameraTransform and not v20 then
                local v35 = p17:IsInFirstPerson()
                if (v23 or (v24 or v25)) and (v_u_16 and (v21 and v21.Torso)) then
                    if v35 then
                        if p17.LastSubjectCFrame and (v24 or v25) and v22:IsA("BasePart") then
                            local l_lookVector_0 = p17.LastSubjectCFrame.lookVector
                            local l_lookVector_1 = v22.CFrame.lookVector
                            local v36 = -math.atan2(l_lookVector_1.X * l_lookVector_0.Z - l_lookVector_1.Z * l_lookVector_0.X, l_lookVector_1.X * l_lookVector_0.X + l_lookVector_1.Z * l_lookVector_0.Z)
                            local v37
                            if v36 == v36 and v36 ~= (1 / 0) then
                                v37 = v36 ~= (-1 / 0)
                            else
                                v37 = false
                            end;
                            if v37 then
                                p17.RotateInput = p17.RotateInput + Vector2.new(v36, 0)
                            end;
                            v_u_15 = 0
                        end;
                    elseif not v29 then
                        local l_lookVector_2 = v21.Torso.CFrame.lookVector
                        if v25 then
                            l_lookVector_2 = v22.CFrame.lookVector
                        end;
                        v_u_15 = math.min(4.363323129985824, (math.max(0, v_u_15 + 3.839724354387525 * v19)))
                        local v38 = not v23 and p17:IsInFirstPerson() and 1 or math.min(1, (math.max(0, v_u_15 * v19)))
                        local v39 = p17:GetCameraLook()
                        local v40 = math.atan2(v39.X * l_lookVector_2.Z - v39.Z * l_lookVector_2.X, v39.X * l_lookVector_2.X + v39.Z * l_lookVector_2.Z)
                        local v41
                        if v40 == v40 and v40 ~= (1 / 0) then
                            v41 = v40 ~= (-1 / 0)
                        else
                            v41 = false
                        end;
                        if v41 and math.abs(v40) > 0.0001 then
                            p17.RotateInput = p17.RotateInput + Vector2.new(v40 * v38, 0)
                        end;
                    end;
                elseif not (v35 or (v29 or v_u_3.VREnabled)) then
                    local v42 = -(p17.LastCameraTransform.p - v30)
                    local v43 = p17:GetCameraLook()
                    local v44 = math.atan2(v43.X * v42.Z - v43.Z * v42.X, v43.X * v42.X + v43.Z * v42.Z)
                    local v45
                    if v44 == v44 and v44 ~= (1 / 0) then
                        v45 = v44 ~= (-1 / 0)
                    else
                        v45 = false
                    end;
                    if v45 and math.abs(v44) > 0.0001 then
                        p17.RotateInput = p17.RotateInput + Vector2.new(v44, 0)
                    end;
                end;
            end;
            local v46 = p17:RotateCamera(p17:GetCameraLook(), p17.RotateInput)
            p17.RotateInput = Vector2.new()
            l_CurrentCamera_0.Focus = v_u_3.VREnabled and p17:GetVRFocus(v30, v19) or CFrame.new(v30)
            l_CurrentCamera_0.CFrame = CFrame.new(l_CurrentCamera_0.Focus.p - v32 * v46, l_CurrentCamera_0.Focus.p) + Vector3.new(0, p17:GetCameraHeight(), 0)
            p17.LastCameraTransform = l_CurrentCamera_0.CFrame
            p17.LastCameraFocus = l_CurrentCamera_0.Focus
            if v24 or v25 and v22:IsA("BasePart") then
                p17.LastSubjectCFrame = v22.CFrame
            else
                p17.LastSubjectCFrame = nil
            end;
        end;
        v_u_16 = v18
    end;
    return v_u_14;
end;
