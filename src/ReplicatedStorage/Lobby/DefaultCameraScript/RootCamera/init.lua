-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local s_Players_0 = game:GetService("Players")
local s_UserInputService_0 = game:GetService("UserInputService")
local s_StarterGui_0 = game:GetService("StarterGui")
local s_GuiService_0 = game:GetService("GuiService")
local v1, v2 = pcall(function() --[[ Line: 6 ]]
    return game:GetService("VRService");
end)
local v_u_3 = v1 and v2 and v2 or s_UserInputService_0
local v_u_4 = require(script.Parent:WaitForChild("ShiftLockController"))
local l_GameSettings_0 = UserSettings().GameSettings
local function _(p5, p6, p7) --[[ Name: clamp ]] --[[ Line: 20 ]]
    if p5 <= p6 then
        return math.min(p6, (math.max(p5, p7)));
    else
        return p7;
    end;
end;
local function _(p8, p9) --[[ Name: findAngleBetweenXZVectors ]] --[[ Line: 27 ]]
    return math.atan2(p9.X * p8.Z - p9.Z * p8.X, p9.X * p8.X + p9.Z * p8.Z);
end;
local function _(p10) --[[ Name: IsFinite ]] --[[ Line: 31 ]]
    local v11
    if p10 == p10 and p10 ~= (1 / 0) then
        v11 = p10 ~= (-1 / 0)
    else
        v11 = false
    end;
    return v11;
end;
local v_u_12 = {}
local function f_findPlayerHumanoid(p13) --[[ Name: findPlayerHumanoid ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    local v14
    if p13 then
        v14 = p13.Character
    else
        v14 = p13
    end;
    if v14 then
        local v15 = v_u_12[p13]
        if v15 and v15.Parent == v14 then
            return v15;
        end;
        v_u_12[p13] = nil
        for _, v16 in pairs(v14:GetChildren()) do
            if v16:IsA("Humanoid") then
                v_u_12[p13] = v16
                return v16;
            end;
        end;
    end;
end;
local v_u_17 = Vector2.new(0.2617993877991494, 0)
local v_u_18 = Vector2.new(0.7853981633974483, 0)
local v_u_19 = Vector2.new(0, 0)
local v_u_20 = Vector2.new(7.0685834705770345, 6.283185307179586)
local v_u_21 = Vector2.new(12.566370614359172, 5.969026041820607)
local v_u_22 = true
local v_u_23 = false
local function _(p24) --[[ Name: GetRenderCFrame ]] --[[ Line: 87 ]]
    return p24:GetRenderCFrame();
end;
return function() --[[ Name: CreateCamera ]] --[[ Line: 91 ]]
    --[[ Upvalues: (copy 1): s_StarterGui_0, (copy 2): v_u_17, (copy 3): v_u_18, (copy 4): v_u_19, (copy 5): v_u_4, (copy 6): s_Players_0, (copy 7): f_findPlayerHumanoid, (ref 8): v_u_3, (copy 9): l_GameSettings_0, (copy 10): s_UserInputService_0, (copy 11): v_u_20, (ref 12): v_u_23, (copy 13): v_u_21, (copy 14): s_GuiService_0, (ref 15): v_u_22 ]]
    local v_u_39 = {
        ["GetActivateValue"] = function(_) --[[ Name: GetActivateValue ]] --[[ Line: 95 ]]
            return 0.7;
        end,
        ["ShiftLock"] = false,
        ["Enabled"] = false,
        ["RotateInput"] = Vector2.new(),
        ["lastSubject"] = nil,
        ["lastSubjectPosition"] = Vector3.new(0, 5, 0),
        ["GetRenderCFrame"] = function(_, p25) --[[ Name: GetRenderCFrame ]] --[[ Line: 150 ]]
            p25:GetRenderCFrame()
        end,
        ["ResetCameraLook"] = function(_) end,
        ["GetCameraLook"] = function(_) --[[ Name: GetCameraLook ]] --[[ Line: 200 ]]
            return workspace.CurrentCamera and workspace.CurrentCamera.CoordinateFrame.lookVector or Vector3.new(0, 0, 1);
        end,
        ["GetCameraActualZoom"] = function(_) --[[ Name: GetCameraActualZoom ]] --[[ Line: 212 ]]
            local l_CurrentCamera_0 = workspace.CurrentCamera
            return not l_CurrentCamera_0 and 0 or (l_CurrentCamera_0.CoordinateFrame.p - l_CurrentCamera_0.Focus.p).magnitude;
        end,
        ["GetCameraHeight"] = function(_) --[[ Name: GetCameraHeight ]] --[[ Line: 220 ]]
            return 0;
        end,
        ["ViewSizeX"] = function(_) --[[ Name: ViewSizeX ]] --[[ Line: 228 ]]
            local l_CurrentCamera_1 = workspace.CurrentCamera
            return not l_CurrentCamera_1 and 1024 or l_CurrentCamera_1.ViewportSize.X;
        end,
        ["ViewSizeY"] = function(_) --[[ Name: ViewSizeY ]] --[[ Line: 237 ]]
            local l_CurrentCamera_2 = workspace.CurrentCamera
            return not l_CurrentCamera_2 and 768 or l_CurrentCamera_2.ViewportSize.Y;
        end,
        ["MouseTranslationToAngle"] = function(_, p26) --[[ Name: MouseTranslationToAngle ]] --[[ Line: 254 ]]
            return Vector2.new(p26.x / 1920, p26.y / 1200);
        end,
        ["RotateVector"] = function(_, p27, p28) --[[ Name: RotateVector ]] --[[ Line: 260 ]]
            return (CFrame.Angles(0, -p28.x, 0) * CFrame.new(Vector3.new(), p27) * CFrame.Angles(-p28.y, 0, 0)).lookVector, Vector2.new(p28.x, p28.y);
        end,
        ["RotateCamera"] = function(p29, p30, p31) --[[ Name: RotateCamera ]] --[[ Line: 266 ]]
            local v32 = math.asin(p30.y)
            local v33 = v32 + -1.0471975511965976
            local v34 = v32 + 1.3962634015954636
            local l_y_0 = p31.y
            if v33 <= v34 then
                l_y_0 = math.min(v34, (math.max(v33, l_y_0)))
            end;
            return p29:RotateVector(p30, Vector2.new(p31.x, l_y_0));
        end,
        ["ZoomCameraFixedBy"] = function(p35, p36) --[[ Name: ZoomCameraFixedBy ]] --[[ Line: 365 ]]
            return p35:ZoomCamera(p35:GetCameraZoom() + p36);
        end,
        ["Update"] = function(_) end,
        ["ZoomEnabled"] = true,
        ["PanEnabled"] = true,
        ["KeyPanEnabled"] = true,
        ["SetEnabled"] = function(p37, p38) --[[ Name: SetEnabled ]] --[[ Line: 1161 ]]
            if p38 ~= p37.Enabled then
                p37.Enabled = p38
                if p37.Enabled then
                    p37:ConnectInputEvents()
                    p37.cframe = workspace.CurrentCamera.CoordinateFrame
                    return;
                end;
                p37:DisconnectInputEvents()
            end;
        end
    }
    local v_u_40 = Vector3.new(0, 2, 0)
    v_u_39.GetRotateAmountValue = function(_, p41) --[[ Name: GetRotateAmountValue ]] --[[ Line: 99 ]]
        --[[ Upvalues: (ref 1): s_StarterGui_0, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_19 ]]
        local v42 = p41 or s_StarterGui_0:GetCore("VRRotationIntensity")
        if v42 then
            if v42 == "Low" then
                return v_u_17;
            end;
            if v42 == "High" then
                return v_u_18;
            end;
        end;
        return v_u_19;
    end;
    v_u_39.GetRepeatDelayValue = function(_, p43) --[[ Name: GetRepeatDelayValue ]] --[[ Line: 111 ]]
        --[[ Upvalues: (ref 1): s_StarterGui_0 ]]
        local v44 = p43 or s_StarterGui_0:GetCore("VRRotationIntensity")
        if v44 then
            if v44 == "Low" then
                return 0.1;
            end;
            if v44 == "High" then
                return 0.4;
            end;
        end;
        return 0;
    end;
    local v_u_45 = false
    local v_u_46 = false
    local v_u_47 = false
    local v_u_48 = 0
    local v_u_49 = {}
    v_u_39.GetShiftLock = function(_) --[[ Name: GetShiftLock ]] --[[ Line: 136 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        return v_u_4:IsShiftLocked();
    end;
    v_u_39.GetHumanoid = function(_) --[[ Name: GetHumanoid ]] --[[ Line: 140 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (ref 2): f_findPlayerHumanoid ]]
        return f_findPlayerHumanoid(s_Players_0.LocalPlayer);
    end;
    v_u_39.GetHumanoidRootPart = function(_) --[[ Name: GetHumanoidRootPart ]] --[[ Line: 145 ]]
        --[[ Upvalues: (copy 1): v_u_39 ]]
        local v50 = v_u_39:GetHumanoid()
        if v50 then
            v50 = v50.Torso
        end;
        return v50;
    end;
    v_u_39.GetSubjectPosition = function(_) --[[ Name: GetSubjectPosition ]] --[[ Line: 154 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_39, (ref 3): v_u_40 ]]
        local v51 = nil
        local l_CurrentCamera_3 = workspace.CurrentCamera
        if l_CurrentCamera_3 then
            l_CurrentCamera_3 = l_CurrentCamera_3.CameraSubject
        end;
        if l_CurrentCamera_3 then
            if l_CurrentCamera_3:IsA("VehicleSeat") then
                local v52 = l_CurrentCamera_3:GetRenderCFrame()
                v51 = v52.p + v52:vectorToWorldSpace(v_u_3.VREnabled and Vector3.new(0, 4, 0) or Vector3.new(0, 5, 0))
            elseif l_CurrentCamera_3:IsA("SkateboardPlatform") then
                v51 = l_CurrentCamera_3:GetRenderCFrame().p + Vector3.new(0, 5, 0)
            elseif l_CurrentCamera_3:IsA("BasePart") then
                v51 = l_CurrentCamera_3:GetRenderCFrame().p
            elseif l_CurrentCamera_3:IsA("Model") then
                v51 = l_CurrentCamera_3:GetModelCFrame().p
            elseif l_CurrentCamera_3:IsA("Humanoid") then
                if l_CurrentCamera_3:GetState() == Enum.HumanoidStateType.Dead and (l_CurrentCamera_3 == v_u_39.lastSubject and v_u_3.VREnabled) then
                    v51 = v_u_39.lastSubjectPosition
                else
                    local l_Torso_0 = l_CurrentCamera_3.Torso
                    if l_Torso_0 and l_Torso_0:IsA("BasePart") then
                        local v53 = l_Torso_0:GetRenderCFrame()
                        if l_CurrentCamera_3.RigType == Enum.HumanoidRigType.R15 then
                            v51 = v53.p + v53:vectorToWorldSpace(v_u_40 + l_CurrentCamera_3.CameraOffset)
                        else
                            v51 = v53.p + v53:vectorToWorldSpace(Vector3.new(0, 1.5, 0) + l_CurrentCamera_3.CameraOffset)
                        end;
                    end;
                end;
            end;
        end;
        v_u_39.lastSubject = l_CurrentCamera_3
        v_u_39.lastSubjectPosition = v51
        return v51;
    end;
    v_u_39.GetCameraZoom = function(_) --[[ Name: GetCameraZoom ]] --[[ Line: 204 ]]
        --[[ Upvalues: (copy 1): v_u_39, (ref 2): s_Players_0 ]]
        if v_u_39.currentZoom == nil then
            local l_LocalPlayer_0 = s_Players_0.LocalPlayer
            local v54 = v_u_39
            local v55
            if l_LocalPlayer_0 then
                local l_CameraMinZoomDistance_0 = l_LocalPlayer_0.CameraMinZoomDistance
                local l_CameraMaxZoomDistance_0 = l_LocalPlayer_0.CameraMaxZoomDistance
                v55 = l_CameraMinZoomDistance_0 > l_CameraMaxZoomDistance_0 and 10 or math.min(l_CameraMaxZoomDistance_0, (math.max(l_CameraMinZoomDistance_0, 10))) or 10
            else
                v55 = 10
            end;
            v54.currentZoom = v55
        end;
        return v_u_39.currentZoom;
    end;
    v_u_39.ScreenTranslationToAngle = function(_, p56) --[[ Name: ScreenTranslationToAngle ]] --[[ Line: 246 ]]
        --[[ Upvalues: (copy 1): v_u_39 ]]
        return Vector2.new(p56.x / v_u_39:ViewSizeX(), p56.y / v_u_39:ViewSizeY());
    end;
    v_u_39.IsInFirstPerson = function(_) --[[ Name: IsInFirstPerson ]] --[[ Line: 278 ]]
        --[[ Upvalues: (ref 1): v_u_45 ]]
        return v_u_45;
    end;
    v_u_39.UpdateMouseBehavior = function(p57) --[[ Name: UpdateMouseBehavior ]] --[[ Line: 283 ]]
        --[[ Upvalues: (ref 1): v_u_45, (ref 2): l_GameSettings_0, (ref 3): s_UserInputService_0, (ref 4): v_u_46, (ref 5): v_u_47 ]]
        if v_u_45 or p57:GetShiftLock() then
            pcall(function() --[[ Line: 286 ]]
                --[[ Upvalues: (ref 1): l_GameSettings_0 ]]
                l_GameSettings_0.RotationType = Enum.RotationType.CameraRelative
            end)
            if s_UserInputService_0.MouseBehavior ~= Enum.MouseBehavior.LockCenter then
                s_UserInputService_0.MouseBehavior = Enum.MouseBehavior.LockCenter
                return;
            end;
        else
            pcall(function() --[[ Line: 291 ]]
                --[[ Upvalues: (ref 1): l_GameSettings_0 ]]
                l_GameSettings_0.RotationType = Enum.RotationType.MovementRelative
            end)
            if v_u_46 or v_u_47 then
                s_UserInputService_0.MouseBehavior = Enum.MouseBehavior.LockCurrentPosition
                return;
            end;
            s_UserInputService_0.MouseBehavior = Enum.MouseBehavior.Default
        end;
    end;
    v_u_39.ZoomCamera = function(p58, p59) --[[ Name: ZoomCamera ]] --[[ Line: 300 ]]
        --[[ Upvalues: (ref 1): v_u_45, (copy 2): v_u_39, (ref 3): v_u_4 ]]
        v_u_45 = false
        v_u_39.currentZoom = math.min(20, (math.max(1, p59)))
        v_u_4:SetIsInFirstPerson(v_u_45)
        p58:UpdateMouseBehavior()
        return p58:GetCameraZoom();
    end;
    local function f_rk4Integrator(p60, p61, p62) --[[ Name: rk4Integrator ]] --[[ Line: 326 ]]
        local v_u_63 = p61 < 0 and -1 or 1
        local function _(p64, _) --[[ Name: acceleration ]] --[[ Line: 328 ]]
            --[[ Upvalues: (copy 1): v_u_63 ]]
            return v_u_63 * math.max(1, p64 / 3.3 + 0.5);
        end;
        local v65 = v_u_63 * math.max(1, p60 / 3.3 + 0.5)
        local v66 = p60 + p61 * (p62 / 2)
        local v67 = p61 + v65 * (p62 / 2)
        local v68 = v_u_63 * math.max(1, v66 / 3.3 + 0.5)
        local v69 = p60 + v67 * (p62 / 2)
        local v70 = p61 + v68 * (p62 / 2)
        local v71 = v_u_63 * math.max(1, v69 / 3.3 + 0.5)
        return p60 + (p61 + 2 * v67 + 2 * v70 + (p61 + v71 * p62)) * (p62 / 6), p61 + (v65 + 2 * v68 + 2 * v71 + v_u_63 * math.max(1, (p60 + v70 * p62) / 3.3 + 0.5)) * (p62 / 6);
    end;
    v_u_39.ZoomCameraBy = function(p72, p73) --[[ Name: ZoomCameraBy ]] --[[ Line: 351 ]]
        --[[ Upvalues: (copy 1): v_u_39, (copy 2): f_rk4Integrator ]]
        local v74 = v_u_39:GetCameraActualZoom()
        if v74 then
            local v75
            if UserSettings():IsUserFeatureEnabled("UserBetterInertialScrolling") then
                v75 = f_rk4Integrator(v74, p73, 0.1)
            else
                v75 = f_rk4Integrator(v74, p73, 1)
            end;
            p72:ZoomCamera(v75)
        end;
        return p72:GetCameraZoom();
    end;
    v_u_39.ApplyVRTransform = function(_) --[[ Name: ApplyVRTransform ]] --[[ Line: 374 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_39 ]]
        if v_u_3.VREnabled then
            local l_LocalPlayer_1 = game.Players.LocalPlayer
            if l_LocalPlayer_1 and (l_LocalPlayer_1.Character and (l_LocalPlayer_1.Character:FindFirstChild("HumanoidRootPart") and l_LocalPlayer_1.Character.HumanoidRootPart:FindFirstChild("RootJoint"))) then
                local l_CameraSubject_0 = workspace.CurrentCamera.CameraSubject
                if l_CameraSubject_0 then
                    l_CameraSubject_0 = l_CameraSubject_0:IsA("VehicleSeat")
                end;
                if v_u_39:IsInFirstPerson() and not l_CameraSubject_0 then
                    local v76 = v_u_3:GetUserCFrame(Enum.UserCFrame.Head)
                    l_LocalPlayer_1.Character.HumanoidRootPart.RootJoint.C0 = CFrame.new((v76 - v76.p):vectorToObjectSpace(v76.p)) * CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0)
                else
                    l_LocalPlayer_1.Character.HumanoidRootPart.RootJoint.C0 = CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0)
                end;
            else
                return;
            end;
        else
            return;
        end;
    end;
    local v_u_77 = true
    local v_u_78 = 0
    v_u_39.ShouldUseVRRotation = function(_) --[[ Name: ShouldUseVRRotation ]] --[[ Line: 403 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_77, (ref 3): v_u_78, (ref 4): s_StarterGui_0 ]]
        if not v_u_3.VREnabled then
            return false;
        end;
        if not v_u_77 and tick() - v_u_78 < 1 then
            return false;
        end;
        local v79, v80 = pcall(function() --[[ Line: 409 ]]
            --[[ Upvalues: (ref 1): s_StarterGui_0 ]]
            return s_StarterGui_0:GetCore("VRRotationIntensity");
        end)
        local v81
        if v79 then
            v81 = v80 ~= nil
        else
            v81 = v79
        end;
        v_u_77 = v81
        v_u_78 = tick()
        if v79 then
            if v80 == nil then
                v79 = false
            else
                v79 = v80 ~= "Smooth"
            end;
        end;
        return v79;
    end;
    v_u_39.GetVRRotationInput = function(p82) --[[ Name: GetVRRotationInput ]] --[[ Line: 416 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): s_StarterGui_0, (ref 3): v_u_48, (copy 4): v_u_49 ]]
        local v83 = v_u_19
        local v84 = s_StarterGui_0:GetCore("VRRotationIntensity")
        local v85 = p82.GamepadPanningCamera or v_u_19
        local v86 = tick() - v_u_48 >= p82:GetRepeatDelayValue(v84)
        if math.abs(v85.x) >= p82:GetActivateValue() then
            if v86 or not v_u_49[Enum.KeyCode.Thumbstick2] then
                v83 = v83 + p82:GetRotateAmountValue(v84) * (v85.x < 0 and -1 or 1)
                v_u_49[Enum.KeyCode.Thumbstick2] = true
            end;
        elseif math.abs(v85.x) < p82:GetActivateValue() - 0.1 then
            v_u_49[Enum.KeyCode.Thumbstick2] = nil
        end;
        if p82.TurningLeft then
            if v86 or not v_u_49[Enum.KeyCode.Left] then
                v83 = v83 - p82:GetRotateAmountValue(v84)
                v_u_49[Enum.KeyCode.Left] = true
            end;
        else
            v_u_49[Enum.KeyCode.Left] = nil
        end;
        if p82.TurningRight then
            if v86 or not v_u_49[Enum.KeyCode.Right] then
                v83 = v83 + p82:GetRotateAmountValue(v84)
                v_u_49[Enum.KeyCode.Right] = true
            end;
        else
            v_u_49[Enum.KeyCode.Right] = nil
        end;
        if v83 ~= v_u_19 then
            v_u_48 = tick()
        end;
        return v83;
    end;
    local v_u_87 = Vector3.new(1, 1, 1)
    local v_u_88 = nil
    local v_u_89 = nil
    local v_u_90 = false
    local v_u_91 = nil
    local v_u_92 = nil
    local v_u_93 = nil
    local v_u_94 = nil
    local v_u_95 = nil
    local function _(p96) --[[ Name: cancelCameraFreeze ]] --[[ Line: 470 ]]
        --[[ Upvalues: (ref 1): v_u_87, (ref 2): v_u_90, (ref 3): v_u_89 ]]
        if not p96 then
            v_u_87 = Vector3.new(v_u_87.x, 1, v_u_87.z)
        end;
        if v_u_90 then
            v_u_89 = nil
            v_u_90 = false
        end;
    end;
    local function _(p97, p98) --[[ Name: startCameraFreeze ]] --[[ Line: 480 ]]
        --[[ Upvalues: (ref 1): v_u_90, (ref 2): v_u_88, (ref 3): v_u_89, (ref 4): v_u_87 ]]
        if not v_u_90 then
            v_u_88 = p97
            v_u_89 = p98
            v_u_87 = Vector3.new(v_u_87.x, 0, v_u_87.z)
            v_u_90 = true
        end;
    end;
    local function f_rescaleCameraOffset(p99) --[[ Name: rescaleCameraOffset ]] --[[ Line: 489 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        v_u_40 = Vector3.new(0, 2, 0) * p99
    end;
    local function f_onHumanoidSubjectChildAdded(p100) --[[ Name: onHumanoidSubjectChildAdded ]] --[[ Line: 493 ]]
        --[[ Upvalues: (copy 1): f_rescaleCameraOffset, (ref 2): v_u_40 ]]
        if p100.Name == "BodyHeightScale" and p100:IsA("NumberValue") then
            if heightScaleChangedConn then
                heightScaleChangedConn:disconnect()
            end;
            heightScaleChangedConn = p100.Changed:connect(f_rescaleCameraOffset)
            v_u_40 = Vector3.new(0, 2, 0) * p100.Value
        end;
    end;
    local function f_onHumanoidSubjectChildRemoved(p101) --[[ Name: onHumanoidSubjectChildRemoved ]] --[[ Line: 503 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        if p101.Name == "BodyHeightScale" then
            v_u_40 = Vector3.new(0, 2, 0)
            if heightScaleChangedConn then
                heightScaleChangedConn:disconnect()
                heightScaleChangedConn = nil
            end;
        end;
    end;
    local function f_onNewCameraSubject() --[[ Name: onNewCameraSubject ]] --[[ Line: 513 ]]
        --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_94, (ref 3): v_u_95, (ref 4): v_u_89, (ref 5): v_u_87, (ref 6): v_u_90, (copy 7): f_onHumanoidSubjectChildAdded, (copy 8): f_onHumanoidSubjectChildRemoved, (copy 9): f_rescaleCameraOffset, (ref 10): v_u_40, (copy 11): v_u_39, (ref 12): v_u_3, (ref 13): v_u_88 ]]
        if v_u_91 then
            v_u_91:disconnect()
            v_u_91 = nil
        end;
        if v_u_94 then
            v_u_94:disconnect()
            v_u_94 = nil
        end;
        if v_u_95 then
            v_u_95:disconnect()
            v_u_95 = nil
        end;
        if heightScaleChangedConn then
            heightScaleChangedConn:disconnect()
            heightScaleChangedConn = nil
        end;
        local l_CurrentCamera_4 = workspace.CurrentCamera
        if l_CurrentCamera_4 then
            l_CurrentCamera_4 = workspace.CurrentCamera.CameraSubject
        end;
        if v_u_89 ~= l_CurrentCamera_4 then
            v_u_87 = Vector3.new(v_u_87.x, 1, v_u_87.z)
            if v_u_90 then
                v_u_89 = nil
                v_u_90 = false
            end;
        end;
        if l_CurrentCamera_4 and l_CurrentCamera_4:IsA("Humanoid") then
            v_u_94 = l_CurrentCamera_4.ChildAdded:connect(f_onHumanoidSubjectChildAdded)
            v_u_95 = l_CurrentCamera_4.ChildRemoved:connect(f_onHumanoidSubjectChildRemoved)
            for _, v102 in pairs(l_CurrentCamera_4:GetChildren()) do
                if v102.Name == "BodyHeightScale" and v102:IsA("NumberValue") then
                    if heightScaleChangedConn then
                        heightScaleChangedConn:disconnect()
                    end;
                    heightScaleChangedConn = v102.Changed:connect(f_rescaleCameraOffset)
                    v_u_40 = Vector3.new(0, 2, 0) * v102.Value
                end;
            end;
            v_u_91 = l_CurrentCamera_4.StateChanged:connect(function(_, p103) --[[ Line: 542 ]]
                --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_3, (copy 3): l_CurrentCamera_4, (ref 4): v_u_90, (ref 5): v_u_88, (ref 6): v_u_89, (ref 7): v_u_87 ]]
                if p103 == Enum.HumanoidStateType.Jumping and (not v_u_39:IsInFirstPerson() and v_u_3.VREnabled) then
                    local v104 = v_u_39:GetSubjectPosition()
                    local v105 = l_CurrentCamera_4
                    if not v_u_90 then
                        v_u_88 = v104
                        v_u_89 = v105
                        v_u_87 = Vector3.new(v_u_87.x, 0, v_u_87.z)
                        v_u_90 = true
                        return;
                    end;
                elseif p103 ~= Enum.HumanoidStateType.Jumping and (p103 ~= Enum.HumanoidStateType.Freefall and v_u_90) then
                    v_u_89 = nil
                    v_u_90 = false
                end;
            end)
        end;
    end;
    local function f_onCameraChanged(p106) --[[ Name: onCameraChanged ]] --[[ Line: 552 ]]
        --[[ Upvalues: (copy 1): f_onNewCameraSubject ]]
        if p106 == "CameraSubject" then
            f_onNewCameraSubject()
        end;
    end;
    local function _() --[[ Name: onCurrentCameraChanged ]] --[[ Line: 558 ]]
        --[[ Upvalues: (ref 1): v_u_92, (copy 2): f_onCameraChanged, (copy 3): f_onNewCameraSubject ]]
        if v_u_92 then
            v_u_92:disconnect()
            v_u_92 = nil
        end;
        local l_CurrentCamera_5 = workspace.CurrentCamera
        if l_CurrentCamera_5 then
            l_CurrentCamera_5.Changed:connect(f_onCameraChanged)
            f_onNewCameraSubject()
        end;
    end;
    v_u_39.GetVRFocus = function(p107, p108, p109) --[[ Name: GetVRFocus ]] --[[ Line: 570 ]]
        --[[ Upvalues: (ref 1): v_u_90, (ref 2): v_u_87, (ref 3): v_u_88, (ref 4): v_u_89 ]]
        local v110 = p107.LastCameraFocus or p108
        if not v_u_90 then
            v_u_87 = Vector3.new(v_u_87.x, math.min(1, v_u_87.y + 0.42 * p109), v_u_87.z)
        end;
        local v111
        if v_u_90 and (v_u_88 and v_u_88.y > v110.y) then
            v111 = CFrame.new((Vector3.new(p108.x, math.min(v_u_88.y, v110.y + 5 * p109), p108.z)))
        else
            v111 = CFrame.new(Vector3.new(p108.x, v110.y, p108.z):lerp(p108, v_u_87.y))
        end;
        if v_u_90 then
            if p107:IsInFirstPerson() then
                v_u_87 = Vector3.new(v_u_87.x, 1, v_u_87.z)
                if v_u_90 then
                    v_u_89 = nil
                    v_u_90 = false
                end;
            end;
            if v_u_88 and p108.y < v_u_88.y - 0.5 then
                v_u_87 = Vector3.new(v_u_87.x, 1, v_u_87.z)
                if v_u_90 then
                    v_u_89 = nil
                    v_u_90 = false
                end;
            end;
        end;
        return v111;
    end;
    local v_u_112 = nil
    local v_u_113 = nil
    local v_u_114 = nil
    local v_u_115 = {}
    local v_u_116 = 0
    local v_u_117 = nil
    local v_u_118 = nil
    local function _(p119, p120) --[[ Name: OnTouchBegan ]] --[[ Line: 616 ]]
        --[[ Upvalues: (ref 1): v_u_115, (ref 2): v_u_116 ]]
        v_u_115[p119] = p120
        if not p120 then
            v_u_116 = v_u_116 + 1
        end;
    end;
    local function f_OnTouchChanged(p121, p122) --[[ Name: OnTouchChanged ]] --[[ Line: 623 ]]
        --[[ Upvalues: (ref 1): v_u_115, (ref 2): v_u_116, (ref 3): v_u_114, (copy 4): v_u_39, (ref 5): v_u_112, (ref 6): v_u_113, (ref 7): v_u_20, (ref 8): v_u_117, (ref 9): v_u_118 ]]
        if v_u_115[p121] == nil then
            v_u_115[p121] = p122
            if not p122 then
                v_u_116 = v_u_116 + 1
            end;
        end;
        if v_u_116 == 1 then
            if v_u_115[p121] == false then
                v_u_114 = v_u_114 or v_u_39:GetCameraLook()
                v_u_112 = v_u_112 or p121.Position
                v_u_113 = v_u_113 or v_u_112
                v_u_39.UserPanningTheCamera = true
                local v123 = p121.Position - v_u_113
                if v_u_39.PanEnabled then
                    v_u_39.RotateInput = v_u_39.RotateInput + v_u_39:ScreenTranslationToAngle(v123) * v_u_20
                end;
                v_u_113 = p121.Position
            end;
        else
            v_u_114 = nil
            v_u_112 = nil
            v_u_113 = nil
            v_u_39.UserPanningTheCamera = false
        end;
        if v_u_116 == 2 then
            local v124 = {}
            for v125, v126 in pairs(v_u_115) do
                if not v126 then
                    table.insert(v124, v125)
                end;
            end;
            if #v124 == 2 then
                local l_magnitude_0 = (v124[1].Position - v124[2].Position).magnitude
                if not (v_u_117 and v_u_118) then
                    v_u_117 = l_magnitude_0
                    v_u_118 = v_u_39:GetCameraActualZoom()
                    return;
                end;
                local v127 = math.min(10, (math.max(0.1, l_magnitude_0 / math.max(0.01, v_u_117))))
                if v_u_39.ZoomEnabled then
                    v_u_39:ZoomCamera(v_u_118 / v127)
                    return;
                end;
            end;
        else
            v_u_117 = nil
            v_u_118 = nil
        end;
    end;
    local function _(p128, _) --[[ Name: OnTouchEnded ]] --[[ Line: 678 ]]
        --[[ Upvalues: (ref 1): v_u_115, (ref 2): v_u_116, (ref 3): v_u_114, (ref 4): v_u_112, (ref 5): v_u_113, (copy 6): v_u_39, (ref 7): v_u_117, (ref 8): v_u_118 ]]
        if v_u_115[p128] == false then
            if v_u_116 == 1 then
                v_u_114 = nil
                v_u_112 = nil
                v_u_113 = nil
                v_u_39.UserPanningTheCamera = false
            elseif v_u_116 == 2 then
                v_u_117 = nil
                v_u_118 = nil
            end;
        end;
        if v_u_115[p128] ~= nil and v_u_115[p128] == false then
            v_u_116 = v_u_116 - 1
        end;
        v_u_115[p128] = nil
    end;
    local function _(p129, p130) --[[ Name: OnMousePanButtonPressed ]] --[[ Line: 697 ]]
        --[[ Upvalues: (copy 1): v_u_39, (ref 2): v_u_114, (ref 3): v_u_112, (ref 4): v_u_113 ]]
        if not p130 then
            v_u_39:UpdateMouseBehavior()
            v_u_114 = v_u_114 or v_u_39:GetCameraLook()
            v_u_112 = v_u_112 or p129.Position
            v_u_113 = v_u_113 or v_u_112
            v_u_39.UserPanningTheCamera = true
        end;
    end;
    local function _(_, _) --[[ Name: OnMousePanButtonReleased ]] --[[ Line: 706 ]]
        --[[ Upvalues: (copy 1): v_u_39, (ref 2): v_u_46, (ref 3): v_u_47, (ref 4): v_u_114, (ref 5): v_u_112, (ref 6): v_u_113 ]]
        v_u_39:UpdateMouseBehavior()
        if not (v_u_46 or v_u_47) then
            v_u_114 = nil
            v_u_112 = nil
            v_u_113 = nil
            v_u_39.UserPanningTheCamera = false
        end;
    end;
    local function _(p131, p132) --[[ Name: OnMouse2Down ]] --[[ Line: 716 ]]
        --[[ Upvalues: (ref 1): v_u_46, (copy 2): v_u_39, (ref 3): v_u_114, (ref 4): v_u_112, (ref 5): v_u_113 ]]
        if p132 then
            return;
        else
            v_u_46 = true
            if not p132 then
                v_u_39:UpdateMouseBehavior()
                v_u_114 = v_u_114 or v_u_39:GetCameraLook()
                v_u_112 = v_u_112 or p131.Position
                v_u_113 = v_u_113 or v_u_112
                v_u_39.UserPanningTheCamera = true
            end;
        end;
    end;
    local function _(_, _) --[[ Name: OnMouse2Up ]] --[[ Line: 723 ]]
        --[[ Upvalues: (ref 1): v_u_46, (copy 2): v_u_39, (ref 3): v_u_47, (ref 4): v_u_114, (ref 5): v_u_112, (ref 6): v_u_113 ]]
        v_u_46 = false
        v_u_39:UpdateMouseBehavior()
        if not (v_u_46 or v_u_47) then
            v_u_114 = nil
            v_u_112 = nil
            v_u_113 = nil
            v_u_39.UserPanningTheCamera = false
        end;
    end;
    local function _(p133, p134) --[[ Name: OnMouse3Down ]] --[[ Line: 728 ]]
        --[[ Upvalues: (ref 1): v_u_47, (copy 2): v_u_39, (ref 3): v_u_114, (ref 4): v_u_112, (ref 5): v_u_113 ]]
        if p134 then
            return;
        else
            v_u_47 = true
            if not p134 then
                v_u_39:UpdateMouseBehavior()
                v_u_114 = v_u_114 or v_u_39:GetCameraLook()
                v_u_112 = v_u_112 or p133.Position
                v_u_113 = v_u_113 or v_u_112
                v_u_39.UserPanningTheCamera = true
            end;
        end;
    end;
    local function _(_, _) --[[ Name: OnMouse3Up ]] --[[ Line: 735 ]]
        --[[ Upvalues: (ref 1): v_u_47, (copy 2): v_u_39, (ref 3): v_u_46, (ref 4): v_u_114, (ref 5): v_u_112, (ref 6): v_u_113 ]]
        v_u_47 = false
        v_u_39:UpdateMouseBehavior()
        if not (v_u_46 or v_u_47) then
            v_u_114 = nil
            v_u_112 = nil
            v_u_113 = nil
            v_u_39.UserPanningTheCamera = false
        end;
    end;
    local function f_OnMouseMoved(p135, _) --[[ Name: OnMouseMoved ]] --[[ Line: 740 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_3, (ref 3): v_u_112, (ref 4): v_u_113, (ref 5): v_u_114, (copy 6): v_u_39, (ref 7): v_u_21 ]]
        if v_u_23 or not v_u_3.VREnabled then
            if v_u_112 and (v_u_113 and v_u_114) then
                local v136 = v_u_113 + p135.Delta
                if v_u_39.PanEnabled then
                    v_u_39.RotateInput = v_u_39.RotateInput + v_u_39:MouseTranslationToAngle(p135.Delta) * v_u_21
                end;
                v_u_113 = v136
            elseif (v_u_39:IsInFirstPerson() or v_u_39:GetShiftLock()) and v_u_39.PanEnabled then
                v_u_39.RotateInput = v_u_39.RotateInput + v_u_39:MouseTranslationToAngle(p135.Delta) * v_u_21
            end;
        else
            return;
        end;
    end;
    local function f_OnMouseWheel(p137, p138) --[[ Name: OnMouseWheel ]] --[[ Line: 760 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_3, (copy 3): v_u_39 ]]
        if v_u_23 or not v_u_3.VREnabled then
            if not p138 and v_u_39.ZoomEnabled then
                if UserSettings():IsUserFeatureEnabled("UserBetterInertialScrolling") then
                    v_u_39:ZoomCameraBy(-p137.Position.Z / 15)
                    return;
                end;
                v_u_39:ZoomCameraBy(math.min(1, (math.max(-1, -p137.Position.Z))) * 1.4)
            end;
        end;
    end;
    local function _(p139) --[[ Name: round ]] --[[ Line: 775 ]]
        return math.floor(p139 + 0.5);
    end;
    local function _(p140, p141, p142) --[[ Name: rotateVectorByAngleAndRound ]] --[[ Line: 781 ]]
        if p140 == Vector3.new(0, 0, 0) then
            return 0;
        end;
        local l_unit_0 = p140.unit
        return math.floor((math.atan2(l_unit_0.z, l_unit_0.x) + p141) / p142 + 0.5) * p142 - math.atan2(l_unit_0.z, l_unit_0.x);
    end;
    local function _(p143, p144) --[[ Name: OnKeyDown ]] --[[ Line: 791 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_3, (ref 3): v_u_114, (copy 4): v_u_39 ]]
        if v_u_23 or not v_u_3.VREnabled then
            if not p144 then
                if v_u_114 == nil and v_u_39.KeyPanEnabled then
                    if p143.KeyCode == Enum.KeyCode.Left then
                        v_u_39.TurningLeft = true
                        return;
                    end;
                    if p143.KeyCode == Enum.KeyCode.Right then
                        v_u_39.TurningRight = true
                    end;
                end;
            end;
        else
            return;
        end;
    end;
    local function _(p145, _) --[[ Name: OnKeyUp ]] --[[ Line: 834 ]]
        --[[ Upvalues: (copy 1): v_u_39 ]]
        if p145.KeyCode == Enum.KeyCode.Left then
            v_u_39.TurningLeft = false
        elseif p145.KeyCode == Enum.KeyCode.Right then
            v_u_39.TurningRight = false
        end;
    end;
    local v_u_146 = nil
    local v_u_147 = 0
    local v_u_148 = Vector2.new(0, 0)
    local v_u_149 = nil
    local function _(p150) --[[ Name: SCurveTranform ]] --[[ Line: 856 ]]
        local v151 = math.min(1, (math.max(-1, p150)))
        if v151 >= 0 then
            return 0.35 * v151 / (0.35 - v151 + 1);
        else
            return -(0.8 * -v151 / (0.8 + v151 + 1));
        end;
    end;
    local function _(p152) --[[ Name: toSCurveSpace ]] --[[ Line: 866 ]]
        return (math.abs(p152) * 2 - 1) * 1.1 - 0.1;
    end;
    local function _(p153) --[[ Name: fromSCurveSpace ]] --[[ Line: 870 ]]
        return p153 / 2 + 0.5;
    end;
    local function _(p154) --[[ Name: gamepadLinearToCurve ]] --[[ Line: 874 ]]
        local function _(p155) --[[ Name: onAxis ]] --[[ Line: 875 ]]
            local v156 = p155 < 0 and -1 or 1
            local v157 = math.min(1, (math.max(-1, (math.abs((math.abs(p155))) * 2 - 1) * 1.1 - 0.1)))
            local v158
            if v157 >= 0 then
                v158 = 0.35 * v157 / (0.35 - v157 + 1)
            else
                v158 = -(0.8 * -v157 / (0.8 + v157 + 1))
            end;
            return math.min(1, (math.max(-1, (v158 / 2 + 0.5) * v156)));
        end;
        local l_new_0 = Vector2.new
        local l_x_0 = p154.x
        local v159 = l_x_0 < 0 and -1 or 1
        local v160 = math.min(1, (math.max(-1, (math.abs((math.abs(l_x_0))) * 2 - 1) * 1.1 - 0.1)))
        local v161
        if v160 >= 0 then
            v161 = 0.35 * v160 / (0.35 - v160 + 1)
        else
            v161 = -(0.8 * -v160 / (0.8 + v160 + 1))
        end;
        local v162 = math.min(1, (math.max(-1, (v161 / 2 + 0.5) * v159)))
        local l_y_1 = p154.y
        local v163 = l_y_1 < 0 and -1 or 1
        local v164 = math.min(1, (math.max(-1, (math.abs((math.abs(l_y_1))) * 2 - 1) * 1.1 - 0.1)))
        local v165
        if v164 >= 0 then
            v165 = 0.35 * v164 / (0.35 - v164 + 1)
        else
            v165 = -(0.8 * -v164 / (0.8 + v164 + 1))
        end;
        return l_new_0(v162, (math.min(1, (math.max(-1, (v165 / 2 + 0.5) * v163)))));
    end;
    v_u_39.UpdateGamepad = function(_) --[[ Name: UpdateGamepad ]] --[[ Line: 887 ]]
        --[[ Upvalues: (copy 1): v_u_39, (ref 2): v_u_23, (ref 3): v_u_3, (ref 4): v_u_146, (ref 5): v_u_148, (ref 6): v_u_147, (ref 7): v_u_149 ]]
        local l_GamepadPanningCamera_0 = v_u_39.GamepadPanningCamera
        if not l_GamepadPanningCamera_0 or not v_u_23 and v_u_3.VREnabled then
            return Vector2.new(0, 0);
        end;
        local function _(p166) --[[ Name: onAxis ]] --[[ Line: 875 ]]
            local v167 = p166 < 0 and -1 or 1
            local v168 = math.min(1, (math.max(-1, (math.abs((math.abs(p166))) * 2 - 1) * 1.1 - 0.1)))
            local v169
            if v168 >= 0 then
                v169 = 0.35 * v168 / (0.35 - v168 + 1)
            else
                v169 = -(0.8 * -v168 / (0.8 + v168 + 1))
            end;
            return math.min(1, (math.max(-1, (v169 / 2 + 0.5) * v167)));
        end;
        local l_new_1 = Vector2.new
        local l_x_1 = l_GamepadPanningCamera_0.x
        local v170 = l_x_1 < 0 and -1 or 1
        local v171 = math.min(1, (math.max(-1, (math.abs((math.abs(l_x_1))) * 2 - 1) * 1.1 - 0.1)))
        local v172
        if v171 >= 0 then
            v172 = 0.35 * v171 / (0.35 - v171 + 1)
        else
            v172 = -(0.8 * -v171 / (0.8 + v171 + 1))
        end;
        local v173 = math.min(1, (math.max(-1, (v172 / 2 + 0.5) * v170)))
        local l_y_2 = l_GamepadPanningCamera_0.y
        local v174 = l_y_2 < 0 and -1 or 1
        local v175 = math.min(1, (math.max(-1, (math.abs((math.abs(l_y_2))) * 2 - 1) * 1.1 - 0.1)))
        local v176
        if v175 >= 0 then
            v176 = 0.35 * v175 / (0.35 - v175 + 1)
        else
            v176 = -(0.8 * -v175 / (0.8 + v175 + 1))
        end;
        local v177 = l_new_1(v173, (math.min(1, (math.max(-1, (v176 / 2 + 0.5) * v174)))))
        local v178 = tick()
        if v177.X == 0 and v177.Y == 0 then
            if v177 == Vector2.new(0, 0) then
                v_u_146 = nil
                if v_u_148 == Vector2.new(0, 0) then
                    v_u_147 = 0
                end;
            end;
        else
            v_u_39.userPanningTheCamera = true
        end;
        local v179
        if v_u_146 then
            if v_u_3.VREnabled then
                v_u_147 = 4
            else
                local v180 = (v178 - v_u_146) * 10
                v_u_147 = v_u_147 + 6 * (v180 * v180 / 0.7)
                if v_u_147 > 6 then
                    v_u_147 = 6
                end;
                if v_u_149 then
                    local l_magnitude_1 = ((v177 - v_u_148) / (v178 - v_u_146) - v_u_149).magnitude
                    if l_magnitude_1 > 12 then
                        v_u_147 = v_u_147 * (20 / l_magnitude_1)
                        if v_u_147 > 6 then
                            v_u_147 = 6
                        end;
                    end;
                end;
            end;
            v179 = v_u_147 * 1
            v_u_149 = (v177 - v_u_148) / (v178 - v_u_146)
        else
            v179 = 0
        end;
        v_u_148 = v177
        v_u_146 = v178
        return Vector2.new(v177.X * v179, v177.Y * v179 * 0.65);
    end;
    local v_u_181 = nil
    local v_u_182 = nil
    local v_u_183 = nil
    local v_u_184 = nil
    local v_u_185 = nil
    local v_u_186 = nil
    local v_u_187 = nil
    v_u_39.DisconnectInputEvents = function(p188) --[[ Name: DisconnectInputEvents ]] --[[ Line: 938 ]]
        --[[ Upvalues: (ref 1): v_u_181, (ref 2): v_u_182, (ref 3): v_u_183, (ref 4): v_u_184, (ref 5): v_u_185, (ref 6): v_u_186, (ref 7): v_u_187, (ref 8): v_u_91, (ref 9): v_u_92, (ref 10): v_u_93, (copy 11): v_u_39, (ref 12): v_u_112, (ref 13): v_u_113, (ref 14): v_u_114, (ref 15): v_u_46, (ref 16): v_u_47, (ref 17): v_u_115, (ref 18): v_u_116, (ref 19): v_u_117, (ref 20): v_u_118, (ref 21): s_UserInputService_0 ]]
        if v_u_181 then
            v_u_181:disconnect()
            v_u_181 = nil
        end;
        if v_u_182 then
            v_u_182:disconnect()
            v_u_182 = nil
        end;
        if v_u_183 then
            v_u_183:disconnect()
            v_u_183 = nil
        end;
        if v_u_184 then
            v_u_184:disconnect()
            v_u_184 = nil
        end;
        if v_u_185 then
            v_u_185:disconnect()
            v_u_185 = nil
        end;
        if v_u_186 then
            v_u_186:disconnect()
            v_u_186 = nil
        end;
        if v_u_187 then
            v_u_187:disconnect()
            v_u_187 = nil
        end;
        if v_u_91 then
            v_u_91:disconnect()
            v_u_91 = nil
        end;
        if v_u_92 then
            v_u_92:disconnect()
            v_u_92 = nil
        end;
        if v_u_93 then
            v_u_93:disconnect()
            v_u_93 = nil
        end;
        v_u_39.TurningLeft = false
        v_u_39.TurningRight = false
        v_u_39.LastCameraTransform = nil
        p188.LastSubjectCFrame = nil
        v_u_39.UserPanningTheCamera = false
        v_u_39.RotateInput = Vector2.new()
        v_u_39.GamepadPanningCamera = Vector2.new(0, 0)
        v_u_112 = nil
        v_u_113 = nil
        v_u_114 = nil
        v_u_46 = false
        v_u_47 = false
        v_u_115 = {}
        v_u_116 = 0
        v_u_117 = nil
        v_u_118 = nil
        if s_UserInputService_0.MouseBehavior ~= Enum.MouseBehavior.LockCenter then
            s_UserInputService_0.MouseBehavior = Enum.MouseBehavior.Default
        end;
    end;
    v_u_39.ResetInputStates = function(_) --[[ Name: ResetInputStates ]] --[[ Line: 1007 ]]
        --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_47, (copy 3): v_u_39, (ref 4): v_u_114, (ref 5): v_u_112, (ref 6): v_u_113, (ref 7): s_UserInputService_0, (ref 8): v_u_115, (ref 9): v_u_117, (ref 10): v_u_118, (ref 11): v_u_116 ]]
        v_u_46 = false
        v_u_47 = false
        v_u_39:UpdateMouseBehavior()
        if not (v_u_46 or v_u_47) then
            v_u_114 = nil
            v_u_112 = nil
            v_u_113 = nil
            v_u_39.UserPanningTheCamera = false
        end;
        if s_UserInputService_0.TouchEnabled then
            for v189, _ in pairs(v_u_115) do
                v_u_115[v189] = nil
            end;
            v_u_114 = nil
            v_u_112 = nil
            v_u_113 = nil
            v_u_39.UserPanningTheCamera = false
            v_u_117 = nil
            v_u_118 = nil
            v_u_116 = 0
        end;
    end;
    v_u_39.ConnectInputEvents = function(p190) --[[ Name: ConnectInputEvents ]] --[[ Line: 1029 ]]
        --[[ Upvalues: (ref 1): v_u_181, (ref 2): s_UserInputService_0, (ref 3): v_u_115, (ref 4): v_u_116, (ref 5): v_u_46, (copy 6): v_u_39, (ref 7): v_u_114, (ref 8): v_u_112, (ref 9): v_u_113, (ref 10): v_u_47, (ref 11): v_u_23, (ref 12): v_u_3, (ref 13): v_u_182, (copy 14): f_OnTouchChanged, (copy 15): f_OnMouseMoved, (copy 16): f_OnMouseWheel, (ref 17): v_u_183, (ref 18): v_u_117, (ref 19): v_u_118, (ref 20): v_u_184, (ref 21): s_GuiService_0, (ref 22): v_u_93, (ref 23): v_u_92, (copy 24): f_onCameraChanged, (copy 25): f_onNewCameraSubject, (ref 26): v_u_185, (ref 27): v_u_4, (ref 28): v_u_186, (ref 29): v_u_187 ]]
        v_u_181 = s_UserInputService_0.InputBegan:connect(function(p191, p192) --[[ Line: 1033 ]]
            --[[ Upvalues: (ref 1): v_u_115, (ref 2): v_u_116, (ref 3): v_u_46, (ref 4): v_u_39, (ref 5): v_u_114, (ref 6): v_u_112, (ref 7): v_u_113, (ref 8): v_u_47, (ref 9): v_u_23, (ref 10): v_u_3 ]]
            if p191.UserInputType == Enum.UserInputType.Touch then
                v_u_115[p191] = p192
                if not p192 then
                    v_u_116 = v_u_116 + 1
                end;
            elseif p191.UserInputType == Enum.UserInputType.MouseButton2 then
                if not p192 then
                    v_u_46 = true
                    if not p192 then
                        v_u_39:UpdateMouseBehavior()
                        v_u_114 = v_u_114 or v_u_39:GetCameraLook()
                        v_u_112 = v_u_112 or p191.Position
                        v_u_113 = v_u_113 or v_u_112
                        v_u_39.UserPanningTheCamera = true
                    end;
                end;
            elseif p191.UserInputType == Enum.UserInputType.MouseButton3 and not p192 then
                v_u_47 = true
                if not p192 then
                    v_u_39:UpdateMouseBehavior()
                    v_u_114 = v_u_114 or v_u_39:GetCameraLook()
                    v_u_112 = v_u_112 or p191.Position
                    v_u_113 = v_u_113 or v_u_112
                    v_u_39.UserPanningTheCamera = true
                end;
            end;
            if p191.UserInputType == Enum.UserInputType.Keyboard then
                if not v_u_23 and v_u_3.VREnabled then
                    return;
                end;
                if p192 then
                    return;
                end;
                if v_u_114 == nil and v_u_39.KeyPanEnabled then
                    if p191.KeyCode == Enum.KeyCode.Left then
                        v_u_39.TurningLeft = true
                        return;
                    end;
                    if p191.KeyCode == Enum.KeyCode.Right then
                        v_u_39.TurningRight = true
                    end;
                end;
            end;
        end)
        v_u_182 = s_UserInputService_0.InputChanged:connect(function(p193, p194) --[[ Line: 1047 ]]
            --[[ Upvalues: (ref 1): f_OnTouchChanged, (ref 2): f_OnMouseMoved, (ref 3): f_OnMouseWheel ]]
            if p193.UserInputType == Enum.UserInputType.Touch then
                f_OnTouchChanged(p193, p194)
                return;
            elseif p193.UserInputType == Enum.UserInputType.MouseMovement then
                f_OnMouseMoved(p193, p194)
            elseif p193.UserInputType == Enum.UserInputType.MouseWheel then
                f_OnMouseWheel(p193, p194)
            end;
        end)
        v_u_183 = s_UserInputService_0.InputEnded:connect(function(p195, _) --[[ Line: 1057 ]]
            --[[ Upvalues: (ref 1): v_u_115, (ref 2): v_u_116, (ref 3): v_u_114, (ref 4): v_u_112, (ref 5): v_u_113, (ref 6): v_u_39, (ref 7): v_u_117, (ref 8): v_u_118, (ref 9): v_u_46, (ref 10): v_u_47 ]]
            if p195.UserInputType == Enum.UserInputType.Touch then
                if v_u_115[p195] == false then
                    if v_u_116 == 1 then
                        v_u_114 = nil
                        v_u_112 = nil
                        v_u_113 = nil
                        v_u_39.UserPanningTheCamera = false
                    elseif v_u_116 == 2 then
                        v_u_117 = nil
                        v_u_118 = nil
                    end;
                end;
                if v_u_115[p195] ~= nil and v_u_115[p195] == false then
                    v_u_116 = v_u_116 - 1
                end;
                v_u_115[p195] = nil
            elseif p195.UserInputType == Enum.UserInputType.MouseButton2 then
                v_u_46 = false
                v_u_39:UpdateMouseBehavior()
                if not (v_u_46 or v_u_47) then
                    v_u_114 = nil
                    v_u_112 = nil
                    v_u_113 = nil
                    v_u_39.UserPanningTheCamera = false
                end;
            elseif p195.UserInputType == Enum.UserInputType.MouseButton3 then
                v_u_47 = false
                v_u_39:UpdateMouseBehavior()
                if not (v_u_46 or v_u_47) then
                    v_u_114 = nil
                    v_u_112 = nil
                    v_u_113 = nil
                    v_u_39.UserPanningTheCamera = false
                end;
            end;
            if p195.UserInputType == Enum.UserInputType.Keyboard then
                if p195.KeyCode == Enum.KeyCode.Left then
                    v_u_39.TurningLeft = false
                    return;
                end;
                if p195.KeyCode == Enum.KeyCode.Right then
                    v_u_39.TurningRight = false
                end;
            end;
        end)
        v_u_184 = s_GuiService_0.MenuOpened:connect(function() --[[ Line: 1071 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            v_u_39:ResetInputStates()
        end)
        v_u_93 = workspace.Changed:connect(function(p196) --[[ Line: 1075 ]]
            --[[ Upvalues: (ref 1): v_u_92, (ref 2): f_onCameraChanged, (ref 3): f_onNewCameraSubject ]]
            if p196 == "CurrentCamera" then
                if v_u_92 then
                    v_u_92:disconnect()
                    v_u_92 = nil
                end;
                local l_CurrentCamera_6 = workspace.CurrentCamera
                if l_CurrentCamera_6 then
                    l_CurrentCamera_6.Changed:connect(f_onCameraChanged)
                    f_onNewCameraSubject()
                end;
            end;
        end)
        if v_u_92 then
            v_u_92:disconnect()
            v_u_92 = nil
        end;
        local l_CurrentCamera_7 = workspace.CurrentCamera
        if l_CurrentCamera_7 then
            l_CurrentCamera_7.Changed:connect(f_onCameraChanged)
            f_onNewCameraSubject()
        end;
        v_u_185 = v_u_4.OnShiftLockToggled.Event:connect(function() --[[ Line: 1082 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            v_u_39:UpdateMouseBehavior()
        end)
        v_u_39.RotateInput = Vector2.new()
        local v_u_197 = nil
        local function f_assignActivateGamepad() --[[ Name: assignActivateGamepad ]] --[[ Line: 1089 ]]
            --[[ Upvalues: (ref 1): s_UserInputService_0, (ref 2): v_u_197 ]]
            local v198 = s_UserInputService_0:GetConnectedGamepads()
            if #v198 > 0 then
                for v199 = 1, #v198 do
                    if v_u_197 == nil then
                        v_u_197 = v198[v199]
                    elseif v198[v199].Value < v_u_197.Value then
                        v_u_197 = v198[v199]
                    end;
                end;
            end;
            if v_u_197 == nil then
                v_u_197 = Enum.UserInputType.Gamepad1
            end;
        end;
        v_u_186 = s_UserInputService_0.GamepadDisconnected:connect(function(p200) --[[ Line: 1106 ]]
            --[[ Upvalues: (ref 1): v_u_197, (copy 2): f_assignActivateGamepad ]]
            if v_u_197 == p200 then
                v_u_197 = nil
                f_assignActivateGamepad()
            end;
        end)
        v_u_187 = s_UserInputService_0.GamepadConnected:connect(function(_) --[[ Line: 1112 ]]
            --[[ Upvalues: (ref 1): v_u_197, (copy 2): f_assignActivateGamepad ]]
            if v_u_197 == nil then
                f_assignActivateGamepad()
            end;
        end)
        local function v203(_, p201, p202) --[[ Line: 1135 ]]
            --[[ Upvalues: (ref 1): v_u_197, (ref 2): v_u_39 ]]
            if p202.UserInputType == v_u_197 and (p202.KeyCode == Enum.KeyCode.ButtonR3 and (p201 == Enum.UserInputState.Begin and v_u_39.ZoomEnabled)) then
                if v_u_39.currentZoom > 1.5 then
                    v_u_39:ZoomCamera(0)
                    return;
                end;
                v_u_39:ZoomCamera(10)
            end;
        end;
        game.ContextActionService:BindAction("RootCamGamepadPan", function(_, p204, p205) --[[ Line: 1118 ]]
            --[[ Upvalues: (ref 1): v_u_197, (ref 2): v_u_39 ]]
            if p205.UserInputType == v_u_197 and p205.KeyCode == Enum.KeyCode.Thumbstick2 then
                if p204 == Enum.UserInputState.Cancel then
                    v_u_39.GamepadPanningCamera = Vector2.new(0, 0)
                    return;
                end;
                if Vector2.new(p205.Position.X, -p205.Position.Y).magnitude > 0.2 then
                    v_u_39.GamepadPanningCamera = Vector2.new(p205.Position.X, -p205.Position.Y)
                    return;
                end;
                v_u_39.GamepadPanningCamera = Vector2.new(0, 0)
            end;
        end, false, Enum.KeyCode.Thumbstick2)
        game.ContextActionService:BindAction("RootCamGamepadZoom", v203, false, Enum.KeyCode.ButtonR3)
        f_assignActivateGamepad()
        p190:UpdateMouseBehavior()
    end;
    local v_u_206 = nil
    v_u_39.set_look_behind_character = function(_) --[[ Name: set_look_behind_character ]] --[[ Line: 1175 ]]
        --[[ Upvalues: (ref 1): v_u_206 ]]
        if v_u_206 then
            v_u_206()
        else
            spawn(function() --[[ Line: 1179 ]]
                --[[ Upvalues: (ref 1): v_u_206 ]]
                while not v_u_206 do
                    wait()
                end;
                v_u_206()
            end)
        end;
    end;
    local function f_OnPlayerAdded(p_u_207) --[[ Name: OnPlayerAdded ]] --[[ Line: 1188 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): v_u_206, (copy 3): v_u_39, (ref 4): v_u_22 ]]
        local function f_OnCharacterAdded(p_u_208) --[[ Name: OnCharacterAdded ]] --[[ Line: 1197 ]]
            --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (copy 2): p_u_207, (ref 3): v_u_206, (ref 4): v_u_39 ]]
            local v_u_209 = f_findPlayerHumanoid(p_u_207)
            local v210 = tick()
            while tick() - v210 < 0.3 and (v_u_209 == nil or v_u_209.Torso == nil) do
                wait()
                v_u_209 = f_findPlayerHumanoid(p_u_207)
            end;
            v_u_206 = function() --[[ Line: 1204 ]]
                --[[ Upvalues: (ref 1): v_u_209, (ref 2): p_u_207, (copy 3): p_u_208, (ref 4): v_u_39 ]]
                if v_u_209 and (v_u_209.Torso and p_u_207.Character == p_u_208) then
                    v_u_39:ZoomCamera(12.5)
                    local l_unit_1 = (v_u_209.Torso.CFrame.lookVector - Vector3.new(0, 0.23, 0)).unit
                    local v211 = v_u_39:GetCameraLook()
                    local v212 = math.atan2(v211.X * l_unit_1.Z - v211.Z * l_unit_1.X, v211.X * l_unit_1.X + v211.Z * l_unit_1.Z)
                    local v213 = math.asin(v_u_39:GetCameraLook().y) - math.asin(l_unit_1.y)
                    local v214
                    if v212 == v212 and v212 ~= (1 / 0) then
                        v214 = v212 ~= (-1 / 0)
                    else
                        v214 = false
                    end;
                    local v215 = not v214 and 0 or v212
                    local v216
                    if v213 == v213 and v213 ~= (1 / 0) then
                        v216 = v213 ~= (-1 / 0)
                    else
                        v216 = false
                    end;
                    v_u_39.RotateInput = Vector2.new(v215, not v216 and 0 or v213)
                    v_u_39.LastCameraTransform = nil
                else
                    warn("_fn_set_look_behind_character fail")
                end;
            end
        end;
        p_u_207.CharacterAdded:connect(function(p217) --[[ Line: 1229 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_22, (copy 3): f_OnCharacterAdded ]]
            if v_u_39.Enabled or v_u_22 then
                f_OnCharacterAdded(p217)
                v_u_22 = false
            end;
        end)
        f_OnCharacterAdded(p_u_207.Character)
    end;
    if s_Players_0.LocalPlayer then
        f_OnPlayerAdded(s_Players_0.LocalPlayer)
    end;
    s_Players_0.ChildAdded:connect(function(p218) --[[ Line: 1243 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (copy 2): f_OnPlayerAdded ]]
        if p218 and s_Players_0.LocalPlayer == p218 then
            f_OnPlayerAdded(s_Players_0.LocalPlayer)
        end;
    end)
    local function _() --[[ Name: OnGameLoaded ]] --[[ Line: 1249 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        v_u_23 = true
    end;
    spawn(function() --[[ Line: 1253 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        if game:IsLoaded() then
            v_u_23 = true
        else
            game.Loaded:wait()
            v_u_23 = true
        end;
    end)
    return v_u_39;
end;
