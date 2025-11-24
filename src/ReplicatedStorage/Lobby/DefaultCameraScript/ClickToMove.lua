-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local s_UserInputService_0 = game:GetService("UserInputService")
local s_PathfindingService_0 = game:GetService("PathfindingService")
local s_Players_0 = game:GetService("Players")
local s_RunService_0 = game:GetService("RunService")
local s_Debris_0 = game:GetService("Debris")
local _ = game:GetService("ReplicatedStorage")
local v_u_1 = require(script.Parent:WaitForChild("RootCamera"):WaitForChild("ClassicCamera"))
local l_localPlayer_0 = s_Players_0.localPlayer
local v_u_2 = l_localPlayer_0:GetMouse()
local l_FindPartOnRayWithIgnoreList_0 = workspace.FindPartOnRayWithIgnoreList
local v_u_3 = nil
local v_u_4 = nil
local v_u_5, v_u_6
if s_UserInputService_0.TouchEnabled then
    v_u_5 = Instance.new("BindableEvent")
    v_u_5.Name = "OnClickToMoveFailStateChange"
    v_u_6 = Instance.new("BindableEvent")
    v_u_6.Name = "EnableTouchJump"
    local l_Parent_0 = script.Parent.Parent
    v_u_5.Parent = l_Parent_0
    v_u_6.Parent = l_Parent_0
else
    v_u_5 = nil
    v_u_6 = nil
end;
local v_u_39 = {
    ["Signal"] = {
        ["Create"] = function() --[[ Name: Create ]] --[[ Line: 48 ]]
            local v7 = {}
            local l_BindableEvent_0 = Instance.new("BindableEvent")
            local v_u_8 = nil
            local v_u_9 = nil
            v7.fire = function(_, ...) --[[ Name: fire ]] --[[ Line: 56 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (copy 3): l_BindableEvent_0 ]]
                v_u_8 = { ... }
                v_u_9 = select("#", ...)
                l_BindableEvent_0:Fire()
            end;
            v7.connect = function(_, p_u_10) --[[ Name: connect ]] --[[ Line: 62 ]]
                --[[ Upvalues: (copy 1): l_BindableEvent_0, (ref 2): v_u_8, (ref 3): v_u_9 ]]
                if not p_u_10 then
                    error("connect(nil)", 2)
                end;
                return l_BindableEvent_0.Event:connect(function() --[[ Line: 64 ]]
                    --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_8, (ref 3): v_u_9 ]]
                    p_u_10(unpack(v_u_8, 1, v_u_9))
                end);
            end;
            v7.wait = function(_) --[[ Name: wait ]] --[[ Line: 69 ]]
                --[[ Upvalues: (copy 1): l_BindableEvent_0, (ref 2): v_u_8, (ref 3): v_u_9 ]]
                l_BindableEvent_0.Event:wait()
                assert(v_u_8, "Missing arg data, likely due to :TweenSize/Position corrupting threadrefs.")
                return unpack(v_u_8, 1, v_u_9);
            end;
            return v7;
        end
    },
    ["Create"] = function(p_u_11) --[[ Name: Create ]] --[[ Line: 79 ]]
        return function(p12) --[[ Line: 80 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            local v13 = Instance.new(p_u_11)
            for v14, v15 in pairs(p12) do
                if type(v14) == "number" then
                    v15.Parent = v13
                else
                    v13[v14] = v15
                end;
            end;
            return v13;
        end;
    end,
    ["Clamp"] = function(p16, p17, p18) --[[ Name: clamp ]] --[[ Line: 93 ]]
        return math.max(math.min(p17, p18), p16);
    end,
    ["ViewSizeX"] = function() --[[ Name: ViewSizeX ]] --[[ Line: 98 ]]
        local l_CurrentCamera_0 = workspace.CurrentCamera
        local v19 = l_CurrentCamera_0 and (l_CurrentCamera_0.ViewportSize.X or 0) or 0
        local v20 = l_CurrentCamera_0 and l_CurrentCamera_0.ViewportSize.Y or 0
        if v19 == 0 then
            return 1024;
        elseif v20 < v19 then
            return v19;
        else
            return v20;
        end;
    end,
    ["ViewSizeY"] = function() --[[ Name: ViewSizeY ]] --[[ Line: 114 ]]
        local l_CurrentCamera_1 = workspace.CurrentCamera
        local v21 = l_CurrentCamera_1 and (l_CurrentCamera_1.ViewportSize.X or 0) or 0
        local v22 = l_CurrentCamera_1 and l_CurrentCamera_1.ViewportSize.Y or 0
        if v22 == 0 then
            return 768;
        elseif v22 < v21 then
            return v22;
        else
            return v21;
        end;
    end,
    ["AspectRatio"] = function() --[[ Name: AspectRatio ]] --[[ Line: 130 ]]
        local l_CurrentCamera_2 = workspace.CurrentCamera
        local v23 = l_CurrentCamera_2 and (l_CurrentCamera_2.ViewportSize.X or 0) or 0
        local v24 = l_CurrentCamera_2 and l_CurrentCamera_2.ViewportSize.Y or 0
        if v23 == 0 then
            v24 = 1024
        elseif v24 < v23 then
            v24 = v23
        end;
        local l_CurrentCamera_3 = workspace.CurrentCamera
        local v25 = l_CurrentCamera_3 and (l_CurrentCamera_3.ViewportSize.X or 0) or 0
        local v26 = l_CurrentCamera_3 and l_CurrentCamera_3.ViewportSize.Y or 0
        if v26 == 0 then
            v25 = 768
        elseif v26 < v25 then
            v25 = v26
        end;
        return v24 / v25;
    end,
    ["GetUnitRay"] = function(p27, p28, _, _, p29) --[[ Name: GetUnitRay ]] --[[ Line: 148 ]]
        return p29:ScreenPointToRay(p27, p28);
    end,
    ["Round"] = function(p30, p31) --[[ Line: 169 ]]
        local v32 = p31 or 1
        return math.floor((p30 + v32 / 2) / v32) * v32;
    end,
    ["AveragePoints"] = function(p33) --[[ Name: AveragePoints ]] --[[ Line: 174 ]]
        local v34 = Vector2.new(0, 0)
        if #p33 > 0 then
            for v35 = 1, #p33 do
                v34 = v34 + p33[v35]
            end;
            v34 = v34 / #p33
        end;
        return v34;
    end,
    ["FuzzyEquals"] = function(p36, p37) --[[ Name: FuzzyEquals ]] --[[ Line: 186 ]]
        local v38
        if p37 < p36 + 0.1 then
            v38 = p36 - 0.1 < p37
        else
            v38 = false
        end;
        return v38;
    end
}
local function f_FindChacterAncestor(p40) --[[ Name: FindChacterAncestor ]] --[[ Line: 135 ]]
    --[[ Upvalues: (copy 1): f_FindChacterAncestor ]]
    if p40 then
        local v41 = p40:FindFirstChild("Humanoid")
        if v41 then
            return p40, v41;
        else
            return f_FindChacterAncestor(p40.Parent);
        end;
    else
        return;
    end;
end;
v_u_39.FindChacterAncestor = f_FindChacterAncestor
local l_FindPartOnRayWithIgnoreList_1 = workspace.FindPartOnRayWithIgnoreList
local function f_Raycast(p42, p43, p44) --[[ Name: Raycast ]] --[[ Line: 154 ]]
    --[[ Upvalues: (copy 1): l_FindPartOnRayWithIgnoreList_1, (copy 2): f_Raycast ]]
    local v45 = p44 or {}
    local v46, v47 = l_FindPartOnRayWithIgnoreList_1(workspace, p42, v45)
    if not v46 then
        return nil, nil;
    end;
    if not p43 or v46.CanCollide ~= false then
        return v46, v47;
    end;
    table.insert(v45, v46)
    return f_Raycast(p42, p43, v45);
end;
v_u_39.Raycast = f_Raycast
local v_u_48 = 0
s_UserInputService_0.InputBegan:connect(function(p49, p50) --[[ Line: 192 ]]
    --[[ Upvalues: (ref 1): v_u_48 ]]
    if not p50 and (p49.UserInputType == Enum.UserInputType.Touch or (p49.UserInputType == Enum.UserInputType.MouseButton1 or p49.UserInputType == Enum.UserInputType.MouseButton2)) then
        v_u_48 = tick()
    end;
end)
v_u_39.GetLastInput = function() --[[ Line: 201 ]]
    --[[ Upvalues: (ref 1): v_u_48 ]]
    return v_u_48;
end;
local v_u_51 = {}
local function f_findPlayerHumanoid(p52) --[[ Name: findPlayerHumanoid ]] --[[ Line: 207 ]]
    --[[ Upvalues: (copy 1): v_u_51 ]]
    local v53
    if p52 then
        v53 = p52.Character
    else
        v53 = p52
    end;
    if v53 then
        local v54 = v_u_51[p52]
        if v54 and v54.Parent == v53 then
            return v54;
        end;
        v_u_51[p52] = nil
        for _, v55 in pairs(v53:GetChildren()) do
            if v55:IsA("Humanoid") then
                v_u_51[p52] = v55
                return v55;
            end;
        end;
    end;
end;
local function f_CFrameInterpolator(p_u_56, p57) --[[ Name: CFrameInterpolator ]] --[[ Line: 225 ]]
    local l_fromAxisAngle_0 = CFrame.fromAxisAngle
    local l_components_0 = CFrame.new().components
    local l_inverse_0 = CFrame.new().inverse
    local l_new_0 = Vector3.new
    local l_acos_0 = math.acos
    local l_sqrt_0 = math.sqrt
    local _, _, _, v58, v59, v60, v61, v62, v63, v64, v65, v66 = l_components_0(l_inverse_0(p_u_56) * p57)
    local v67 = (v58 + v62 + v66 - 1) / 2
    local v_u_68 = l_new_0(v65 - v63, v60 - v64, v61 - v59)
    local v_u_69 = p57.p - p_u_56.p
    if v67 >= 0.999 then
        return 0, function(p70) --[[ Line: 248 ]]
            --[[ Upvalues: (copy 1): p_u_56, (copy 2): v_u_69 ]]
            return p_u_56 + v_u_69 * p70;
        end;
    end;
    local v_u_71
    if v67 <= -0.999 then
        v_u_71 = 3.141592653589793
        local v72 = (v58 + 1) / 2
        local v73 = (v62 + 1) / 2
        local v74 = (v66 + 1) / 2
        if v73 < v72 and v74 < v72 then
            if v72 < 0.001 then
                v_u_68 = Vector3.new(0, 0.70710677, 0.70710677)
            else
                local v75 = l_sqrt_0(v72)
                v_u_68 = l_new_0(v75, (v61 + v59) / 4 / v75, (v64 + v60) / 4 / v75)
            end;
        elseif v74 < v73 then
            if v73 < 0.001 then
                v_u_68 = Vector3.new(0.70710677, 0, 0.70710677)
            else
                local v76 = l_sqrt_0(v73)
                v_u_68 = l_new_0((v61 + v59) / 4 / v76, v76, (v65 + v63) / 4 / v76)
            end;
        elseif v74 < 0.001 then
            v_u_68 = Vector3.new(0.70710677, 0.70710677, 0)
        else
            local v77 = l_sqrt_0(v74)
            v_u_68 = l_new_0((v64 + v60) / 4 / v77, (v65 + v63) / 4 / v77, v77)
        end;
    else
        v_u_71 = l_acos_0(v67)
    end;
    return v_u_71, function(p78) --[[ Line: 290 ]]
        --[[ Upvalues: (copy 1): p_u_56, (copy 2): l_fromAxisAngle_0, (ref 3): v_u_68, (ref 4): v_u_71, (copy 5): v_u_69 ]]
        return p_u_56 * l_fromAxisAngle_0(v_u_68, v_u_71 * p78) + v_u_69 * p78;
    end;
end;
local l_Signal_0 = v_u_39.Signal
local l_Create_0 = v_u_39.Create
local v_u_84 = (function() --[[ Name: CreateController ]] --[[ Line: 300 ]]
    --[[ Upvalues: (copy 1): f_findPlayerHumanoid, (copy 2): l_localPlayer_0 ]]
    local v_u_79 = {
        ["TorsoLookPoint"] = nil
    }
    v_u_79.SetTorsoLookPoint = function(p80, p_u_81) --[[ Name: SetTorsoLookPoint ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (copy 3): v_u_79 ]]
        local v_u_82 = f_findPlayerHumanoid(l_localPlayer_0)
        if v_u_82 then
            v_u_82.AutoRotate = false
        end;
        v_u_79.TorsoLookPoint = p_u_81
        p80:UpdateTorso()
        delay(2, function() --[[ Line: 313 ]]
            --[[ Upvalues: (ref 1): v_u_79, (copy 2): p_u_81, (copy 3): v_u_82 ]]
            if v_u_79.TorsoLookPoint == p_u_81 then
                v_u_79.TorsoLookPoint = nil
                if v_u_82 then
                    v_u_82.AutoRotate = true
                end;
            end;
        end)
    end;
    v_u_79.UpdateTorso = function(_, _) --[[ Name: UpdateTorso ]] --[[ Line: 324 ]]
        --[[ Upvalues: (copy 1): v_u_79, (ref 2): f_findPlayerHumanoid, (ref 3): l_localPlayer_0 ]]
        if v_u_79.TorsoLookPoint then
            local l_TorsoLookPoint_0 = v_u_79.TorsoLookPoint
            local v83 = f_findPlayerHumanoid(l_localPlayer_0)
            if v83 then
                v83 = v83.Torso
            end;
            if v83 then
                local l_unit_0 = (l_TorsoLookPoint_0 - v83.CFrame.p).unit
                v83.CFrame = CFrame.new(v83.CFrame.p, v83.CFrame.p + Vector3.new(l_unit_0.X, 0, l_unit_0.Z).unit)
            end;
        end;
    end;
    return v_u_79;
end)()
local function _() --[[ Name: GetCharacter ]] --[[ Line: 348 ]]
    --[[ Upvalues: (copy 1): l_localPlayer_0 ]]
    local v85 = l_localPlayer_0
    if v85 then
        v85 = l_localPlayer_0.Character
    end;
    return v85;
end;
local function _() --[[ Name: GetTorso ]] --[[ Line: 352 ]]
    --[[ Upvalues: (copy 1): f_findPlayerHumanoid, (copy 2): l_localPlayer_0 ]]
    local v86 = f_findPlayerHumanoid(l_localPlayer_0)
    if v86 then
        v86 = v86.Torso
    end;
    return v86;
end;
local function _(p87) --[[ Name: IsPartAHumanoid ]] --[[ Line: 357 ]]
    local v88 = p87 and p87.Parent
    if v88 then
        v88 = p87.Parent:FindFirstChild("Humanoid") ~= nil
    end;
    return v88;
end;
local function f_doAutoJump() --[[ Name: doAutoJump ]] --[[ Line: 361 ]]
    --[[ Upvalues: (copy 1): l_localPlayer_0, (copy 2): f_findPlayerHumanoid, (copy 3): l_FindPartOnRayWithIgnoreList_0 ]]
    local v89 = l_localPlayer_0
    if v89 then
        v89 = l_localPlayer_0.Character
    end;
    if v89 == nil then
        return;
    else
        local v90 = f_findPlayerHumanoid(l_localPlayer_0)
        if v90 == nil then
            return;
        else
            local v91 = f_findPlayerHumanoid(l_localPlayer_0)
            if v91 then
                v91 = v91.Torso
            end;
            if v91 ~= nil then
                local l_CFrame_0 = v91.CFrame
                local l_lookVector_0 = l_CFrame_0.lookVector
                local l_p_0 = l_CFrame_0.p
                local v92 = Ray.new(l_p_0 + Vector3.new(0, -v91.Size.Y / 2, 0), l_lookVector_0 * 1.5)
                local v93 = Ray.new(l_p_0 + Vector3.new(0, 7 - v91.Size.Y, 0), l_lookVector_0 * 1.5)
                local v94, _ = l_FindPartOnRayWithIgnoreList_0(workspace, v92, { v89 }, false)
                local v95, _ = l_FindPartOnRayWithIgnoreList_0(workspace, v93, { v89 }, false)
                if v94 and (v95 == nil and v94.CanCollide == true) then
                    local v96 = v94 and v94.Parent
                    if v96 then
                        v96 = v94.Parent:FindFirstChild("Humanoid") ~= nil
                    end;
                    if not v96 then
                        v90.Jump = true
                    end;
                end;
            end;
        end;
    end;
end;
local v_u_97 = {
    [Enum.HumanoidStateType.FallingDown] = false,
    [Enum.HumanoidStateType.Flying] = false,
    [Enum.HumanoidStateType.Freefall] = false,
    [Enum.HumanoidStateType.GettingUp] = false,
    [Enum.HumanoidStateType.Ragdoll] = false,
    [Enum.HumanoidStateType.Running] = false,
    [Enum.HumanoidStateType.Seated] = false,
    [Enum.HumanoidStateType.Swimming] = false,
    [Enum.HumanoidStateType.Climbing] = false
}
local function _() --[[ Name: enableAutoJump ]] --[[ Line: 414 ]]
    --[[ Upvalues: (copy 1): f_findPlayerHumanoid, (copy 2): l_localPlayer_0, (copy 3): v_u_97 ]]
    local v98 = f_findPlayerHumanoid(l_localPlayer_0)
    if v98 then
        v98 = v98:GetState()
    end;
    if v98 then
        return v_u_97[v98] == nil;
    else
        return false;
    end;
end;
local function _() --[[ Name: getAutoJump ]] --[[ Line: 423 ]]
    return true;
end;
local function _(p99) --[[ Name: vec3IsZero ]] --[[ Line: 427 ]]
    return p99.magnitude < 0.05;
end;
local function _() --[[ Name: calcDesiredWalkVelocity ]] --[[ Line: 432 ]]
    return Vector3.new(1, 1, 1);
end;
local function _(_) --[[ Name: preStepSimulatorSide ]] --[[ Line: 437 ]]
    --[[ Upvalues: (copy 1): f_findPlayerHumanoid, (copy 2): l_localPlayer_0, (copy 3): v_u_97, (copy 4): f_doAutoJump ]]
    if true then
        local v100 = f_findPlayerHumanoid(l_localPlayer_0)
        if v100 then
            v100 = v100:GetState()
        end;
        local v101
        if v100 then
            v101 = v_u_97[v100] == nil
        else
            v101 = false
        end;
        if v101 and (Vector3.new(1, 1, 1)).magnitude >= 0.05 then
            f_doAutoJump()
        end;
    end;
end;
local function f_AutoJumper() --[[ Name: AutoJumper ]] --[[ Line: 446 ]]
    --[[ Upvalues: (copy 1): f_findPlayerHumanoid, (copy 2): l_localPlayer_0, (copy 3): v_u_97, (copy 4): f_doAutoJump ]]
    local v_u_102 = {}
    local v_u_103 = false
    local v_u_104 = nil
    v_u_102.Run = function(_) --[[ Name: Run ]] --[[ Line: 451 ]]
        --[[ Upvalues: (ref 1): v_u_103, (ref 2): v_u_104, (copy 3): v_u_102 ]]
        v_u_103 = true
        local v_u_105 = nil
        v_u_105 = coroutine.create(function() --[[ Line: 454 ]]
            --[[ Upvalues: (ref 1): v_u_103, (ref 2): v_u_105, (ref 3): v_u_104, (ref 4): v_u_102 ]]
            while v_u_103 and v_u_105 == v_u_104 do
                v_u_102:Step()
                wait()
            end;
        end)
        v_u_104 = v_u_105
        coroutine.resume(v_u_105)
    end;
    v_u_102.Stop = function(_) --[[ Name: Stop ]] --[[ Line: 464 ]]
        --[[ Upvalues: (ref 1): v_u_103 ]]
        v_u_103 = false
    end;
    v_u_102.Step = function(_) --[[ Name: Step ]] --[[ Line: 468 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (ref 3): v_u_97, (ref 4): f_doAutoJump ]]
        if true then
            local v106 = f_findPlayerHumanoid(l_localPlayer_0)
            if v106 then
                v106 = v106:GetState()
            end;
            local v107
            if v106 then
                v107 = v_u_97[v106] == nil
            else
                v107 = false
            end;
            if v107 and (Vector3.new(1, 1, 1)).magnitude >= 0.05 then
                f_doAutoJump()
            end;
        end;
    end;
    return v_u_102;
end;
local function f_CreateDestinationIndicator(p108) --[[ Name: CreateDestinationIndicator ]] --[[ Line: 479 ]]
    --[[ Upvalues: (copy 1): l_Create_0 ]]
    return l_Create_0("Part")({
        ["Name"] = "PathGlobe",
        ["TopSurface"] = "Smooth",
        ["BottomSurface"] = "Smooth",
        ["Shape"] = "Ball",
        ["CanCollide"] = false,
        ["Size"] = Vector3.new(2, 2, 2),
        ["BrickColor"] = BrickColor.new("Institutional white"),
        ["Transparency"] = 0,
        ["Anchored"] = true,
        ["CFrame"] = CFrame.new(p108)
    });
end;
local function f_Pather(p_u_109, p_u_110) --[[ Name: Pather ]] --[[ Line: 496 ]]
    --[[ Upvalues: (copy 1): l_Signal_0, (copy 2): f_findPlayerHumanoid, (copy 3): l_localPlayer_0, (copy 4): v_u_84, (copy 5): v_u_39, (copy 6): s_PathfindingService_0, (ref 7): v_u_3 ]]
    local v_u_111 = {
        ["Cancelled"] = false,
        ["Started"] = false,
        ["Finished"] = l_Signal_0.Create(),
        ["PathFailed"] = l_Signal_0.Create(),
        ["PathStarted"] = l_Signal_0.Create(),
        ["PathComputed"] = false
    }
    v_u_111.YieldUntilPointReached = function(_, _, p112, p113) --[[ Name: YieldUntilPointReached ]] --[[ Line: 508 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (copy 3): v_u_111, (ref 4): v_u_84 ]]
        local v114 = p113 or 10000000
        local v115 = f_findPlayerHumanoid(l_localPlayer_0)
        local v116
        if v115 then
            v116 = v115.Torso
        else
            v116 = v115
        end;
        local v117 = tick()
        local v118 = v117
        while v116 and (tick() - v117 < v114 and v_u_111.Cancelled == false) do
            local v119 = p112 - v116.CFrame.p
            local l_magnitude_0 = (v119 * Vector3.new(1, 0, 1)).magnitude
            if l_magnitude_0 < 6 and v119.Y >= 2.2 then
                v115.Jump = true
            end;
            if l_magnitude_0 < 2 then
                return true;
            end;
            if tick() - v118 > 1.5 then
                v115:MoveTo(p112)
                v118 = tick()
            end;
            v_u_84:UpdateTorso(p112)
            wait()
        end;
        return false;
    end;
    v_u_111.Cancel = function(_) --[[ Name: Cancel ]] --[[ Line: 539 ]]
        --[[ Upvalues: (copy 1): v_u_111, (ref 2): f_findPlayerHumanoid, (ref 3): l_localPlayer_0 ]]
        v_u_111.Cancelled = true
        local v120 = f_findPlayerHumanoid(l_localPlayer_0)
        local v121
        if v120 then
            v121 = v120.Torso
        else
            v121 = v120
        end;
        if v120 and v121 then
            v120:MoveTo(v121.CFrame.p)
        end;
    end;
    v_u_111.CheckOcclusion = function(_, p122, p123, p124, p125) --[[ Name: CheckOcclusion ]] --[[ Line: 548 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (ref 3): v_u_39 ]]
        local v126 = f_findPlayerHumanoid(l_localPlayer_0)
        if v126 then
            v126 = v126.Torso
        end;
        local v127 = p125 == nil and (v126 and Vector3.new(v126.Size.X / 2, 0, v126.Size.Z / 2) or Vector3.new(1, 0, 1)) or p125
        local v128 = p123 - p122
        local l_unit_1 = v128.unit
        local v129 = (Vector3.new(0, 1, 0)):Cross(l_unit_1) * v127
        local v130, _ = v_u_39.Raycast(Ray.new(p122 + v129, v128 + v129), true, { p124 })
        local v131, _ = v_u_39.Raycast(Ray.new(p122, v128), true, { p124 })
        local v132, _ = v_u_39.Raycast(Ray.new(p122 - v129, v128 - v129), true, { p124 })
        if v130 or (v131 or v132) then
            return false;
        end;
        for v133 = 1, math.floor(v128.magnitude / 2) do
            local v134, _ = v_u_39.Raycast(Ray.new(p122 + l_unit_1 * v133 * 2, Vector3.new(0, -7, 0)), true, { p124 })
            if not v134 then
                return false;
            end;
        end;
        return true;
    end;
    v_u_111.SmoothPoints = function(_, p135) --[[ Name: SmoothPoints ]] --[[ Line: 581 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (ref 3): v_u_39, (copy 4): v_u_111, (copy 5): p_u_109 ]]
        local v136 = {}
        local v137 = f_findPlayerHumanoid(l_localPlayer_0)
        if v137 then
            v137 = v137.Torso
        end;
        for v138 = 1, #p135 do
            table.insert(v136, p135[v138])
        end;
        for v139 = #v136 - 1, 1, -1 do
            if v139 + 1 <= #v136 then
                local v140 = v136[v139 + 1]
                local v141 = v136[v139]
                local v142 = v136[v139 - 1]
                if v142 == nil then
                    if v137 then
                        v142 = Vector3.new(v137.CFrame.p.X, v141.Y, v137.CFrame.p.Z)
                    else
                        v142 = v137
                    end;
                end;
                if v142 and (v_u_39.FuzzyEquals(v141.Y, v142.Y) and (v_u_39.FuzzyEquals(v141.Y, v140.Y) and v_u_111:CheckOcclusion(v142, v140, p_u_109))) then
                    table.remove(v136, v139)
                end;
            end;
        end;
        return v136;
    end;
    v_u_111.CheckNeighboringCells = function(_, p143) --[[ Name: CheckNeighboringCells ]] --[[ Line: 615 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (ref 3): v_u_39, (copy 4): v_u_111 ]]
        local v144 = {}
        local v145 = f_findPlayerHumanoid(l_localPlayer_0)
        if p143 then
            if v145 then
                v145 = v145.Torso
            end;
        else
            v145 = p143
        end;
        if v145 then
            local l_p_1 = v145.CFrame.p
            local v146 = Vector3.new(v_u_39.Round(l_p_1.X - 2, 4) + 2, v_u_39.Round(l_p_1.Y - 2, 4) + 2, v_u_39.Round(l_p_1.Z - 2, 4) + 2)
            local v147 = {}
            for v148 = -4, 4, 8 do
                table.insert(v147, v146 + Vector3.new(v148, 0, -4))
                table.insert(v147, v146 + Vector3.new(v148, 0, 4))
            end;
            for _, v149 in pairs(v147) do
                if v_u_111:CheckOcclusion(v146, v149, p143, Vector3.new(0, 0, 0)) then
                    table.insert(v144, v149)
                end;
            end;
        end;
        return v144;
    end;
    v_u_111.ComputeDirectPath = function(_) --[[ Name: ComputeDirectPath ]] --[[ Line: 640 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (copy 3): p_u_110, (copy 4): v_u_111, (copy 5): p_u_109 ]]
        local v150 = f_findPlayerHumanoid(l_localPlayer_0)
        if v150 then
            v150 = v150.Torso
        end;
        if v150 then
            local l_p_2 = v150.CFrame.p
            local v151 = p_u_110
            if (v151 - l_p_2).magnitude < 150 then
                local v_u_152 = v151 - (v151 - l_p_2).unit * 2
                if v_u_111:CheckOcclusion(l_p_2, v_u_152, p_u_109, Vector3.new(0, 0, 0)) then
                    local v153 = {
                        ["Status"] = Enum.PathStatus.Success
                    }
                    v153.GetPointCoordinates = function(_) --[[ Name: GetPointCoordinates ]] --[[ Line: 652 ]]
                        --[[ Upvalues: (ref 1): v_u_152 ]]
                        return { v_u_152 };
                    end;
                    return v153;
                end;
            end;
        end;
    end;
    local function _(p154, p155, p156) --[[ Name: AllAxisInThreshhold ]] --[[ Line: 661 ]]
        local v157
        if math.abs(p154.X - p155.X) <= p156 and math.abs(p154.Y - p155.Y) <= p156 then
            v157 = math.abs(p154.Z - p155.Z) <= p156
        else
            v157 = false
        end;
        return v157;
    end;
    v_u_111.ComputePath = function(_) --[[ Name: ComputePath ]] --[[ Line: 667 ]]
        --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (copy 3): v_u_111, (ref 4): s_PathfindingService_0, (copy 5): p_u_110, (copy 6): p_u_109 ]]
        local v_u_158 = false
        local v_u_159 = f_findPlayerHumanoid(l_localPlayer_0)
        if v_u_159 then
            v_u_159 = v_u_159.Torso
        end;
        if v_u_159 then
            if v_u_111.PathComputed then
                return;
            end;
            v_u_111.PathComputed = true
            local v160
            if not pcall(function() --[[ Line: 676 ]]
                --[[ Upvalues: (ref 1): v_u_111, (ref 2): s_PathfindingService_0, (copy 3): v_u_159, (ref 4): p_u_110, (ref 5): v_u_158 ]]
                v_u_111.pathResult = s_PathfindingService_0:ComputeSmoothPathAsync(v_u_159.CFrame.p - Vector3.new(0, 3, 0), p_u_110, 400)
                v_u_158 = true
            end) then
                v_u_111.pathResult = s_PathfindingService_0:ComputeRawPathAsync(v_u_159.CFrame.p - Vector3.new(0, 3, 0), p_u_110, 400)
                v160 = false
                v_u_158 = v160
            end;
            local v161 = v_u_111
            local l_pathResult_0 = v_u_111.pathResult
            if l_pathResult_0 then
                l_pathResult_0 = v_u_111.pathResult:GetPointCoordinates()
            end;
            v161.pointList = l_pathResult_0
            local v162 = false
            if v_u_111.pathResult.Status == Enum.PathStatus.FailFinishNotEmpty then
                local v163 = p_u_110 - workspace.CurrentCamera.CoordinateFrame.p
                if v163.magnitude > 2 then
                    local v_u_164 = p_u_110 - v163.unit * 2.1
                    if not pcall(function() --[[ Line: 693 ]]
                        --[[ Upvalues: (ref 1): v_u_111, (ref 2): s_PathfindingService_0, (copy 3): v_u_159, (copy 4): v_u_164, (ref 5): v_u_158 ]]
                        v_u_111.pathResult = s_PathfindingService_0:ComputeSmoothPathAsync(v_u_159.CFrame.p, v_u_164, 400)
                        v_u_158 = true
                    end) then
                        v_u_111.pathResult = s_PathfindingService_0:ComputeRawPathAsync(v_u_159.CFrame.p, v_u_164, 400)
                        v160 = false
                        v_u_158 = v160
                    end;
                    local v165 = v_u_111
                    local l_pathResult_1 = v_u_111.pathResult
                    if l_pathResult_1 then
                        l_pathResult_1 = v_u_111.pathResult:GetPointCoordinates()
                    end;
                    v165.pointList = l_pathResult_1
                    v162 = true
                end;
            end;
            if v_u_111.pathResult.Status == Enum.PathStatus.ClosestNoPath and (#v_u_111.pointList >= 1 and v162 == false) then
                local l_pointList_0 = v_u_111.pointList[#v_u_111.pointList]
                local v166 = p_u_110
                local v167
                if math.abs(v166.X - l_pointList_0.X) <= 4 and math.abs(v166.Y - l_pointList_0.Y) <= 4 then
                    v167 = math.abs(v166.Z - l_pointList_0.Z) <= 4
                else
                    v167 = false
                end;
                if v167 and (v_u_159.CFrame.p - p_u_110).magnitude > (l_pointList_0 - p_u_110).magnitude then
                    local v168 = {
                        ["Status"] = Enum.PathStatus.Success
                    }
                    v168.GetPointCoordinates = function(_) --[[ Name: GetPointCoordinates ]] --[[ Line: 710 ]]
                        --[[ Upvalues: (ref 1): v_u_111 ]]
                        return { v_u_111.pointList };
                    end;
                    v_u_111.pathResult = v168
                    v162 = true
                end;
            end;
            if (v_u_111.pathResult.Status == Enum.PathStatus.FailStartNotEmpty or v_u_111.pathResult.Status == Enum.PathStatus.ClosestNoPath) and v162 == false then
                for _, v_u_169 in pairs((v_u_111:CheckNeighboringCells(p_u_109))) do
                    local v_u_170 = nil
                    if not pcall(function() --[[ Line: 721 ]]
                        --[[ Upvalues: (ref 1): v_u_170, (ref 2): s_PathfindingService_0, (copy 3): v_u_169, (ref 4): p_u_110, (ref 5): v_u_158 ]]
                        v_u_170 = s_PathfindingService_0:ComputeSmoothPathAsync(v_u_169, p_u_110, 400)
                        v_u_158 = true
                    end) then
                        v_u_170 = s_PathfindingService_0:ComputeRawPathAsync(v_u_169, p_u_110, 400)
                        local v171 = false
                        v_u_158 = v171
                    end;
                    if v_u_170 and v_u_170.Status == Enum.PathStatus.Success then
                        v_u_111.pathResult = v_u_170
                        if v_u_111.pathResult then
                            v_u_111.pointList = v_u_111.pathResult:GetPointCoordinates()
                            table.insert(v_u_111.pointList, 1, v_u_169)
                        end;
                        break;
                    end;
                end;
            end;
        end;
        return v_u_158;
    end;
    v_u_111.IsValidPath = function(_) --[[ Name: IsValidPath ]] --[[ Line: 752 ]]
        --[[ Upvalues: (copy 1): v_u_111 ]]
        v_u_111:ComputePath()
        return v_u_111.pathResult.Status == Enum.PathStatus.Success;
    end;
    v_u_111.GetPathStatus = function(_) --[[ Name: GetPathStatus ]] --[[ Line: 758 ]]
        --[[ Upvalues: (copy 1): v_u_111 ]]
        v_u_111:ComputePath()
        return v_u_111.pathResult.Status;
    end;
    v_u_111.Start = function(_) --[[ Name: Start ]] --[[ Line: 763 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): f_findPlayerHumanoid, (ref 3): l_localPlayer_0, (copy 4): v_u_111, (ref 5): v_u_39, (copy 6): p_u_109 ]]
        if not v_u_3 then
            spawn(function() --[[ Line: 767 ]]
                --[[ Upvalues: (ref 1): f_findPlayerHumanoid, (ref 2): l_localPlayer_0, (ref 3): v_u_111, (ref 4): v_u_39, (ref 5): p_u_109 ]]
                local v172 = f_findPlayerHumanoid(l_localPlayer_0)
                local v173
                if v172 then
                    v173 = v172.Torso
                else
                    v173 = v172
                end;
                if v173 then
                    if v_u_111.Started then
                        return;
                    end;
                    v_u_111.Started = true
                    local v174 = v_u_111:ComputePath()
                    if v_u_111:IsValidPath() then
                        v_u_111.PathStarted:fire()
                        local v175 = v174 and v_u_111.pointList or v_u_111:SmoothPoints(v_u_111.pointList)
                        for v176, v_u_177 in pairs(v175) do
                            if v172 then
                                if v_u_111.Cancelled then
                                    return;
                                end;
                                v172:MoveTo(v_u_177)
                                local v178 = math.abs(v172.WalkSpeed) <= 0 and 10 or ((v173.CFrame.p - v_u_177) * Vector3.new(1, 0, 1)).magnitude / math.abs(v172.WalkSpeed)
                                local v_u_179 = true
                                if v176 == 1 and CameraModule then
                                    local _, _ = CameraModule:TweenCameraLook((CameraModule:LookAtPreserveHeight(v175[#v175])))
                                end;
                                if (v172.Torso.CFrame.p - v_u_177).magnitude > 9 then
                                    spawn(function() --[[ Line: 814 ]]
                                        --[[ Upvalues: (ref 1): v_u_179, (ref 2): v_u_111, (copy 3): v_u_177, (ref 4): v_u_39 ]]
                                        while v_u_179 and v_u_111.Cancelled == false do
                                            if CameraModule and (tick() - v_u_39.GetLastInput() > 2 and math.deg((math.acos(((CameraModule:GetCameraLook() * Vector3.new(1, 0, 1)).unit:Dot(((v_u_177 - CameraModule.cframe.p) * Vector3.new(1, 0, 1)).unit))))) > workspace.CurrentCamera.FieldOfView / 2) then
                                                local _, _ = CameraModule:TweenCameraLook((CameraModule:LookAtPreserveHeight(v_u_177)))
                                            end;
                                            wait(0.1)
                                        end;
                                    end)
                                end;
                                local v180 = v_u_111:YieldUntilPointReached(p_u_109, v_u_177, v178 * 3 + 1)
                                local _ = false
                                if not v180 then
                                    v_u_111.PathFailed:fire()
                                    return;
                                end;
                            end;
                        end;
                        v_u_111.Finished:fire()
                        return;
                    end;
                end;
                v_u_111.PathFailed:fire()
            end)
        end;
    end;
    return v_u_111;
end;
local function _(p_u_181) --[[ Name: FlashRed ]] --[[ Line: 862 ]]
    local l_BrickColor_0 = p_u_181.BrickColor
    local v_u_182 = BrickColor.new("Really red")
    local v_u_183 = tick()
    spawn(function() --[[ Line: 867 ]]
        --[[ Upvalues: (copy 1): p_u_181, (copy 2): v_u_183, (copy 3): l_BrickColor_0, (copy 4): v_u_182 ]]
        while p_u_181 and tick() - v_u_183 < 4 do
            p_u_181.BrickColor = l_BrickColor_0
            wait(0.13)
            if p_u_181 then
                p_u_181.BrickColor = v_u_182
            end;
            wait(0.13)
        end;
    end)
end;
local function _(p184) --[[ Name: IsInBottomLeft ]] --[[ Line: 881 ]]
    --[[ Upvalues: (copy 1): v_u_39 ]]
    local v185 = math.min(v_u_39.ViewSizeY() * 0.33, 250)
    local v186
    if p184.X <= v185 then
        v186 = p184.Y > v_u_39.ViewSizeY() - v185
    else
        v186 = false
    end;
    return v186;
end;
local function _(p187) --[[ Name: IsInBottomRight ]] --[[ Line: 887 ]]
    --[[ Upvalues: (copy 1): v_u_39 ]]
    local v188 = math.min(v_u_39.ViewSizeY() * 0.33, 250)
    local v189
    if p187.X >= v_u_39.ViewSizeX() - v188 then
        v189 = p187.Y > v_u_39.ViewSizeY() - v188
    else
        v189 = false
    end;
    return v189;
end;
local function _(_) --[[ Name: CheckAlive ]] --[[ Line: 893 ]]
    --[[ Upvalues: (copy 1): f_findPlayerHumanoid, (copy 2): l_localPlayer_0 ]]
    local v190 = f_findPlayerHumanoid(l_localPlayer_0)
    local v191
    if v190 == nil then
        v191 = false
    else
        v191 = v190.Health > 0
    end;
    return v191;
end;
local function f_GetEquippedTool(p192) --[[ Name: GetEquippedTool ]] --[[ Line: 898 ]]
    if p192 ~= nil then
        for _, v193 in pairs(p192:GetChildren()) do
            if v193:IsA("Tool") then
                return v193;
            end;
        end;
    end;
end;
local function f_ExploreWithRayCast(p194, p_u_195) --[[ Name: ExploreWithRayCast ]] --[[ Line: 908 ]]
    --[[ Upvalues: (copy 1): v_u_39, (copy 2): l_localPlayer_0 ]]
    local v196 = {}
    for v197 = 0, 15 do
        table.insert(v196, CFrame.Angles(0, 0.39269908169872414 * v197, 0) * p_u_195)
    end;
    local v_u_198 = {}
    local function f_ExploreHeuristic() --[[ Name: ExploreHeuristic ]] --[[ Line: 920 ]]
        --[[ Upvalues: (copy 1): v_u_198, (copy 2): p_u_195 ]]
        for _, v199 in pairs(v_u_198) do
            v199.Value = ((-1 * p_u_195):Dot(v199.Vector) + 1) / 2 * (v199.Distance / 40)
        end;
    end;
    for _, v200 in pairs(v196) do
        local _, v201 = v_u_39.Raycast(Ray.new(p194, v200 * 40), true, { l_localPlayer_0.Character })
        if v201 then
            table.insert(v_u_198, {
                ["Vector"] = v200,
                ["Distance"] = (v201 - p194).magnitude
            })
        else
            table.insert(v_u_198, {
                ["Vector"] = v200,
                ["Distance"] = 40
            })
        end;
    end;
    f_ExploreHeuristic()
    table.sort(v_u_198, function(p202, p203) --[[ Line: 940 ]]
        return p202.Value > p203.Value;
    end)
    return v_u_198;
end;
local v_u_204 = 1
local v_u_205 = nil
local v_u_206 = nil
local v_u_207 = nil
local v_u_208 = nil
local function _() --[[ Name: CleanupPath ]] --[[ Line: 951 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_205, (ref 3): v_u_207, (ref 4): v_u_208, (ref 5): v_u_206, (copy 6): s_Debris_0 ]]
    v_u_4 = nil
    if v_u_205 then
        v_u_205:Cancel()
    end;
    if v_u_207 then
        v_u_207:disconnect()
        v_u_207 = nil
    end;
    if v_u_208 then
        v_u_208:disconnect()
        v_u_208 = nil
    end;
    if v_u_206 then
        s_Debris_0:AddItem(v_u_206, 0)
        v_u_206 = nil
    end;
end;
local function f_getExtentsSize(p209) --[[ Name: getExtentsSize ]] --[[ Line: 970 ]]
    local l_X_0 = p209[1].Position.X
    local l_Y_0 = p209[1].Position.Y
    local l_Z_0 = p209[1].Position.Z
    local l_X_1 = p209[1].Position.X
    local l_Y_1 = p209[1].Position.Y
    local l_Z_1 = p209[1].Position.Z
    for v210 = 2, #p209 do
        l_X_0 = math.max(l_X_0, p209[v210].Position.X)
        l_Y_0 = math.max(l_Y_0, p209[v210].Position.Y)
        l_Z_0 = math.max(l_Z_0, p209[v210].Position.Z)
        l_X_1 = math.min(l_X_1, p209[v210].Position.X)
        l_Y_1 = math.min(l_Y_1, p209[v210].Position.Y)
        l_Z_1 = math.min(l_Z_1, p209[v210].Position.Z)
    end;
    return Region3.new(Vector3.new(l_X_1, l_Y_1, l_Z_1), (Vector3.new(l_X_0, l_Y_0, l_Z_0)));
end;
local function f_inExtents(p211, p212) --[[ Name: inExtents ]] --[[ Line: 988 ]]
    if p212.X < p211.CFrame.p.X - p211.Size.X / 2 or p212.X > p211.CFrame.p.X + p211.Size.X / 2 then
        return false;
    else
        return p212.Z >= p211.CFrame.p.Z - p211.Size.Z / 2 and p212.Z <= p211.CFrame.p.Z + p211.Size.Z / 2;
    end;
end;
local v_u_213 = nil
local v_u_214 = 0
local v_u_215 = 0
local function f_OnTap(p216, p_u_217) --[[ Name: OnTap ]] --[[ Line: 1002 ]]
    --[[ Upvalues: (ref 1): v_u_204, (copy 2): l_localPlayer_0, (copy 3): f_findPlayerHumanoid, (copy 4): v_u_39, (copy 5): v_u_2, (ref 6): v_u_4, (ref 7): v_u_205, (ref 8): v_u_207, (ref 9): v_u_208, (ref 10): v_u_206, (copy 11): s_Debris_0, (ref 12): v_u_214, (copy 13): f_GetEquippedTool, (ref 14): v_u_3, (copy 15): f_Pather, (ref 16): v_u_215, (ref 17): v_u_5, (copy 18): f_CreateDestinationIndicator, (ref 19): v_u_213, (copy 20): f_ExploreWithRayCast, (copy 21): f_getExtentsSize, (copy 22): f_inExtents, (copy 23): f_OnTap ]]
    v_u_204 = v_u_204 + 1
    local l_CurrentCamera_4 = workspace.CurrentCamera
    local l_Character_0 = l_localPlayer_0.Character
    local v218 = f_findPlayerHumanoid(l_localPlayer_0)
    local v219
    if v218 == nil then
        v219 = false
    else
        v219 = v218.Health > 0
    end;
    if not v219 then
        return;
    end;
    if #p216 == 1 or p_u_217 then
        if l_CurrentCamera_4 then
            local v220 = v_u_39.GetUnitRay(p216[1].x, p216[1].y, v_u_2.ViewSizeX, v_u_2.ViewSizeY, l_CurrentCamera_4)
            local v221, v222 = v_u_39.Raycast(Ray.new(v220.Origin, v220.Direction * 400), true, { l_Character_0 })
            local v_u_223, v224 = v_u_39.FindChacterAncestor(v221)
            local v_u_225 = l_Character_0 and l_Character_0:FindFirstChild("Humanoid")
            if v_u_225 then
                v_u_225 = l_Character_0:FindFirstChild("Humanoid").Torso
            end;
            local l_p_3 = v_u_225.CFrame.p
            if p_u_217 then
                v_u_223 = nil
            else
                p_u_217 = v222
            end;
            if v_u_223 and (v224 and (v224.Torso and (v224.Torso.CFrame.p - v_u_225.CFrame.p).magnitude < 7)) then
                v_u_4 = nil
                if v_u_205 then
                    v_u_205:Cancel()
                end;
                if v_u_207 then
                    v_u_207:disconnect()
                    v_u_207 = nil
                end;
                if v_u_208 then
                    v_u_208:disconnect()
                    v_u_208 = nil
                end;
                if v_u_206 then
                    s_Debris_0:AddItem(v_u_206, 0)
                    v_u_206 = nil
                end;
                local v226 = f_findPlayerHumanoid(l_localPlayer_0)
                if v226 then
                    v226:MoveTo(p_u_217)
                end;
                v_u_214 = v_u_214 + 1
                local v227 = f_GetEquippedTool(l_Character_0)
                if v227 then
                    v227:Activate()
                    LastFired = tick()
                end;
            elseif p_u_217 and (l_Character_0 and not v_u_3) then
                local v228 = f_Pather(l_Character_0, p_u_217)
                if v228:IsValidPath() then
                    v_u_215 = 0
                    l_localPlayer_0:Move(Vector3.new(1, 0, 0))
                    l_localPlayer_0:Move(Vector3.new(0, 0, 0))
                    v228:Start()
                    if v_u_5 then
                        v_u_5:Fire(false)
                    end;
                    v_u_4 = nil
                    if v_u_205 then
                        v_u_205:Cancel()
                    end;
                    if v_u_207 then
                        v_u_207:disconnect()
                        v_u_207 = nil
                    end;
                    if v_u_208 then
                        v_u_208:disconnect()
                        v_u_208 = nil
                    end;
                    if v_u_206 then
                        s_Debris_0:AddItem(v_u_206, 0)
                        v_u_206 = nil
                    end;
                    local v_u_229 = f_CreateDestinationIndicator(p_u_217)
                    v_u_229.Parent = l_CurrentCamera_4
                    v_u_205 = v228
                    v_u_206 = v_u_229
                    if v_u_213 then
                        v_u_213:Run()
                    end;
                    v_u_207 = v228.Finished:connect(function() --[[ Line: 1067 ]]
                        --[[ Upvalues: (ref 1): v_u_213, (ref 2): v_u_229, (ref 3): v_u_206, (ref 4): s_Debris_0, (ref 5): v_u_223, (ref 6): f_findPlayerHumanoid, (ref 7): l_localPlayer_0, (ref 8): v_u_214, (ref 9): f_GetEquippedTool, (copy 10): l_Character_0, (ref 11): p_u_217, (copy 12): v_u_225, (copy 13): l_p_3, (ref 14): v_u_39, (ref 15): f_ExploreWithRayCast ]]
                        if v_u_213 then
                            v_u_213:Stop()
                        end;
                        if v_u_229 then
                            if v_u_206 == v_u_229 then
                                v_u_206 = nil
                            end;
                            s_Debris_0:AddItem(v_u_229, 0)
                            v_u_229 = nil
                        end;
                        if v_u_223 then
                            local v230 = f_findPlayerHumanoid(l_localPlayer_0)
                            v_u_214 = v_u_214 + 1
                            local v231 = f_GetEquippedTool(l_Character_0)
                            if v231 then
                                v231:Activate()
                                LastFired = tick()
                            end;
                            if v230 then
                                v230:MoveTo(p_u_217)
                            end;
                        end;
                        local v232 = v_u_225
                        if v232 then
                            v232 = v_u_225.CFrame.p
                        end;
                        if v232 and (l_p_3 and tick() - v_u_39.GetLastInput() > 2) then
                            local v233 = f_ExploreWithRayCast(v232, ((l_p_3 - v232) * Vector3.new(1, 0, 1)).unit)
                            if v233[1] and (v233[1].Vector and (v233[1].Vector.magnitude >= 0.5 and (v233[1].Distance > 3 and CameraModule))) then
                                local _, _ = CameraModule:TweenCameraLook((CameraModule:LookAtPreserveHeight(v232 + v233[1].Vector * v233[1].Distance)))
                            end;
                        end;
                    end)
                    v_u_208 = v228.PathFailed:connect(function() --[[ Line: 1104 ]]
                        --[[ Upvalues: (ref 1): v_u_213, (ref 2): v_u_229, (ref 3): s_Debris_0 ]]
                        if v_u_213 then
                            v_u_213:Stop()
                        end;
                        if v_u_229 then
                            local v_u_234 = v_u_229
                            local l_BrickColor_1 = v_u_234.BrickColor
                            local v_u_235 = BrickColor.new("Really red")
                            local v_u_236 = tick()
                            spawn(function() --[[ Line: 867 ]]
                                --[[ Upvalues: (copy 1): v_u_234, (copy 2): v_u_236, (copy 3): l_BrickColor_1, (copy 4): v_u_235 ]]
                                while v_u_234 and tick() - v_u_236 < 4 do
                                    v_u_234.BrickColor = l_BrickColor_1
                                    wait(0.13)
                                    if v_u_234 then
                                        v_u_234.BrickColor = v_u_235
                                    end;
                                    wait(0.13)
                                end;
                            end)
                            s_Debris_0:AddItem(v_u_229, 3)
                        end;
                    end)
                elseif p_u_217 then
                    local v_u_237 = f_CreateDestinationIndicator(p_u_217)
                    local l_BrickColor_2 = v_u_237.BrickColor
                    local v_u_238 = BrickColor.new("Really red")
                    local v_u_239 = tick()
                    spawn(function() --[[ Line: 867 ]]
                        --[[ Upvalues: (copy 1): v_u_237, (copy 2): v_u_239, (copy 3): l_BrickColor_2, (copy 4): v_u_238 ]]
                        while v_u_237 and tick() - v_u_239 < 4 do
                            v_u_237.BrickColor = l_BrickColor_2
                            wait(0.13)
                            if v_u_237 then
                                v_u_237.BrickColor = v_u_238
                            end;
                            wait(0.13)
                        end;
                    end)
                    s_Debris_0:AddItem(v_u_237, 1)
                    v_u_237.Parent = l_CurrentCamera_4
                    if v_u_206 == nil then
                        v_u_215 = v_u_215 + 1
                        if v_u_215 >= 3 then
                            if v_u_5 then
                                v_u_5:Fire(true)
                            end;
                            v_u_4 = nil
                            if v_u_205 then
                                v_u_205:Cancel()
                            end;
                            if v_u_207 then
                                v_u_207:disconnect()
                                v_u_207 = nil
                            end;
                            if v_u_208 then
                                v_u_208:disconnect()
                                v_u_208 = nil
                            end;
                            if v_u_206 then
                                s_Debris_0:AddItem(v_u_206, 0)
                                v_u_206 = nil
                            end;
                        end;
                    end;
                end;
            elseif p_u_217 and (l_Character_0 and v_u_3) then
                local v240 = f_CreateDestinationIndicator(p_u_217)
                v240.Parent = l_CurrentCamera_4
                v_u_206 = v240
                v_u_4 = p_u_217
                local v241 = v_u_3:GetConnectedParts(true)
                while wait() do
                    if not v_u_3 or v_u_206 ~= v240 then
                        s_Debris_0:AddItem(v240, 0)
                        if v_u_3 == nil and v240 == v_u_206 then
                            v_u_4 = nil
                            f_OnTap(p216, p_u_217)
                        end;
                        break;
                    end;
                    if f_inExtents(f_getExtentsSize(v241), v240.Position) then
                        s_Debris_0:AddItem(v240, 0)
                        v_u_4 = nil
                        break;
                    end;
                end;
            end;
            return;
        end;
    elseif #p216 >= 2 and l_CurrentCamera_4 then
        v_u_214 = v_u_214 + 1
        local v242 = v_u_39.AveragePoints(p216)
        v_u_39.GetUnitRay(v242.x, v242.y, v_u_2.ViewSizeX, v_u_2.ViewSizeY, l_CurrentCamera_4)
        local v243 = f_GetEquippedTool(l_Character_0)
        if v243 then
            v243:Activate()
            LastFired = tick()
        end;
    end;
end;
return function() --[[ Name: CreateClickToMoveModule ]] --[[ Line: 1179 ]]
    --[[ Upvalues: (copy 1): s_RunService_0, (copy 2): v_u_1, (copy 3): f_CFrameInterpolator, (copy 4): v_u_39, (copy 5): s_UserInputService_0, (ref 6): v_u_5, (ref 7): v_u_4, (ref 8): v_u_205, (ref 9): v_u_207, (ref 10): v_u_208, (ref 11): v_u_206, (copy 12): s_Debris_0, (copy 13): f_OnTap, (ref 14): v_u_213, (copy 15): f_AutoJumper, (ref 16): v_u_3, (ref 17): v_u_6, (copy 18): l_localPlayer_0 ]]
    local v244 = {}
    local v_u_245 = {}
    local v_u_246 = 0
    local v_u_247 = tick()
    local v_u_248 = Vector2.new()
    local v_u_249 = tick()
    local v_u_250 = Vector2.new()
    local v_u_251 = tick()
    local v_u_252 = {
        [Enum.KeyCode.W] = true,
        [Enum.KeyCode.A] = true,
        [Enum.KeyCode.S] = true,
        [Enum.KeyCode.D] = true,
        [Enum.KeyCode.Up] = true,
        [Enum.KeyCode.Down] = true
    }
    local v_u_253 = nil
    local v_u_254 = nil
    local v_u_255 = nil
    local v_u_256 = nil
    local v_u_257 = nil
    local v_u_258 = nil
    local v_u_259 = nil
    local v_u_260 = nil
    local v_u_261 = nil
    local v_u_262 = nil
    local function _(p263) --[[ Name: disconnectEvent ]] --[[ Line: 1213 ]]
        if p263 then
            p263:disconnect()
        end;
    end;
    local function f_DisconnectEvents() --[[ Name: DisconnectEvents ]] --[[ Line: 1219 ]]
        --[[ Upvalues: (ref 1): v_u_253, (ref 2): v_u_254, (ref 3): v_u_255, (ref 4): v_u_256, (ref 5): v_u_257, (ref 6): v_u_258, (ref 7): v_u_259, (ref 8): v_u_261, (ref 9): v_u_260, (ref 10): s_RunService_0, (ref 11): v_u_262 ]]
        local v264 = v_u_253
        if v264 then
            v264:disconnect()
        end;
        local v265 = v_u_254
        if v265 then
            v265:disconnect()
        end;
        local v266 = v_u_255
        if v266 then
            v266:disconnect()
        end;
        local v267 = v_u_256
        if v267 then
            v267:disconnect()
        end;
        local v268 = v_u_257
        if v268 then
            v268:disconnect()
        end;
        local v269 = v_u_258
        if v269 then
            v269:disconnect()
        end;
        local v270 = v_u_259
        if v270 then
            v270:disconnect()
        end;
        local v271 = v_u_261
        if v271 then
            v271:disconnect()
        end;
        local v272 = v_u_260
        if v272 then
            v272:disconnect()
        end;
        pcall(function() --[[ Line: 1229 ]]
            --[[ Upvalues: (ref 1): s_RunService_0 ]]
            s_RunService_0:UnbindFromRenderStep("ClickToMoveRenderUpdate")
        end)
        local v273 = v_u_262
        if v273 then
            v273:disconnect()
        end;
    end;
    local function _(p274) --[[ Name: IsFinite ]] --[[ Line: 1235 ]]
        local v275
        if p274 == p274 and p274 ~= (1 / 0) then
            v275 = p274 ~= (-1 / 0)
        else
            v275 = false
        end;
        return v275;
    end;
    local function _(p276, p277) --[[ Name: findAngleBetweenXZVectors ]] --[[ Line: 1239 ]]
        return math.atan2(p277.X * p276.Z - p277.Z * p276.X, p277.X * p276.X + p277.Z * p276.Z);
    end;
    CameraModule = v_u_1()
    CameraModule.LookAtPreserveHeight = function(_, p278) --[[ Name: LookAtPreserveHeight ]] --[[ Line: 1248 ]]
        local l_p_4 = workspace.CurrentCamera.Focus.p
        local l_cframe_0 = CameraModule.cframe
        local v279 = (Vector3.new(p278.x, l_p_4.y, p278.z) - l_p_4).unit * Vector3.new(l_cframe_0.lookVector.x, 0, l_cframe_0.lookVector.z).magnitude + Vector3.new(0, l_cframe_0.lookVector.y, 0)
        local v280 = l_p_4 - v279.unit * (l_p_4 - l_cframe_0.p).magnitude
        return CFrame.new(v280, v280 + v279);
    end;
    CameraModule.TweenCameraLook = function(p_u_281, p282, p283) --[[ Name: TweenCameraLook ]] --[[ Line: 1264 ]]
        --[[ Upvalues: (ref 1): f_CFrameInterpolator, (ref 2): v_u_39 ]]
        local function _(p284) --[[ Name: SCurve ]] --[[ Line: 1266 ]]
            return 1 / (1 + 2.718281828459 ^ (-p284 * 1.5));
        end;
        local function _(p285, p286, p287, p288) --[[ Name: easeOutSine ]] --[[ Line: 1269 ]]
            if p288 <= p285 then
                return p286 + p287;
            else
                return p287 * math.sin(p285 / p288 * 1.5707963267948966) + p286;
            end;
        end;
        local v289, v_u_290 = f_CFrameInterpolator(CFrame.new(Vector3.new(), p_u_281:GetCameraLook()), p282 - p282.p)
        local v291 = v_u_39.Clamp(0, 3.141592653589793, v289)
        local v_u_292 = 0.65 * (1 / (1 + 2.718281828459 ^ (-(v291 - 0.7853981633974483) * 1.5))) + 0.15
        if p283 then
            v_u_292 = v291 / p283
        end;
        local v_u_293 = tick()
        local v_u_294 = v_u_293 + v_u_292
        p_u_281.UpdateTweenFunction = function() --[[ Line: 1283 ]]
            --[[ Upvalues: (copy 1): v_u_293, (ref 2): v_u_39, (ref 3): v_u_292, (copy 4): v_u_290, (copy 5): p_u_281, (copy 6): v_u_294 ]]
            local v295 = tick() - v_u_293
            local v296 = v_u_292
            local v297 = v_u_39.Clamp(0, 1, v296 <= v295 and 1 or 1 * math.sin(v295 / v296 * 1.5707963267948966) + 0)
            local l_lookVector_1 = v_u_290(v297).lookVector
            local v298 = p_u_281:GetCameraLook()
            local v299 = math.atan2(v298.X * l_lookVector_1.Z - v298.Z * l_lookVector_1.X, v298.X * l_lookVector_1.X + v298.Z * l_lookVector_1.Z)
            local v300
            if v299 == v299 and v299 ~= (1 / 0) then
                v300 = v299 ~= (-1 / 0)
            else
                v300 = false
            end;
            if v300 and math.abs(v299) > 0.0001 then
                p_u_281.RotateInput = p_u_281.RotateInput + Vector2.new(v299, 0)
            end;
            return v_u_294 <= v295 and true or v297 >= 1;
        end;
    end;
    local function _(p301, p302) --[[ Name: OnTouchBegan ]] --[[ Line: 1298 ]]
        --[[ Upvalues: (copy 1): v_u_245, (ref 2): v_u_246 ]]
        if v_u_245[p301] == nil and not p302 then
            v_u_246 = v_u_246 + 1
        end;
        v_u_245[p301] = p302
    end;
    local function _(p303, p304) --[[ Name: OnTouchChanged ]] --[[ Line: 1305 ]]
        --[[ Upvalues: (copy 1): v_u_245, (ref 2): v_u_246 ]]
        if v_u_245[p303] == nil then
            v_u_245[p303] = p304
            if not p304 then
                v_u_246 = v_u_246 + 1
            end;
        end;
    end;
    local function _(p305, _) --[[ Name: OnTouchEnded ]] --[[ Line: 1314 ]]
        --[[ Upvalues: (copy 1): v_u_245, (ref 2): v_u_246 ]]
        if v_u_245[p305] ~= nil and v_u_245[p305] == false then
            v_u_246 = v_u_246 - 1
        end;
        v_u_245[p305] = nil
    end;
    local function f_OnCharacterAdded(p306) --[[ Name: OnCharacterAdded ]] --[[ Line: 1326 ]]
        --[[ Upvalues: (copy 1): f_DisconnectEvents, (ref 2): v_u_254, (ref 3): s_UserInputService_0, (copy 4): v_u_245, (ref 5): v_u_246, (ref 6): v_u_39, (ref 7): v_u_5, (copy 8): v_u_252, (ref 9): v_u_4, (ref 10): v_u_205, (ref 11): v_u_207, (ref 12): v_u_208, (ref 13): v_u_206, (ref 14): s_Debris_0, (ref 15): v_u_247, (ref 16): v_u_248, (ref 17): v_u_249, (ref 18): v_u_250, (ref 19): v_u_255, (ref 20): v_u_256, (ref 21): v_u_251, (ref 22): f_OnTap, (ref 23): v_u_253, (ref 24): v_u_213, (ref 25): f_AutoJumper, (ref 26): v_u_3, (ref 27): s_RunService_0, (ref 28): v_u_261, (ref 29): v_u_6, (ref 30): v_u_257, (ref 31): v_u_262, (ref 32): v_u_258, (ref 33): v_u_260 ]]
        f_DisconnectEvents()
        v_u_254 = s_UserInputService_0.InputBegan:connect(function(p307, p308) --[[ Line: 1329 ]]
            --[[ Upvalues: (ref 1): v_u_245, (ref 2): v_u_246, (ref 3): v_u_39, (ref 4): v_u_5, (ref 5): v_u_252, (ref 6): v_u_4, (ref 7): v_u_205, (ref 8): v_u_207, (ref 9): v_u_208, (ref 10): v_u_206, (ref 11): s_Debris_0, (ref 12): v_u_247, (ref 13): v_u_248, (ref 14): v_u_249, (ref 15): v_u_250 ]]
            if p307.UserInputType == Enum.UserInputType.Touch then
                if v_u_245[p307] == nil and not p308 then
                    v_u_246 = v_u_246 + 1
                end;
                v_u_245[p307] = p308
                local l_Position_0 = p307.Position
                local v309 = math.min(v_u_39.ViewSizeY() * 0.33, 250)
                local v310
                if l_Position_0.X <= v309 then
                    v310 = l_Position_0.Y > v_u_39.ViewSizeY() - v309
                else
                    v310 = false
                end;
                local l_Position_1 = p307.Position
                local v311 = math.min(v_u_39.ViewSizeY() * 0.33, 250)
                local v312
                if l_Position_1.X >= v_u_39.ViewSizeX() - v311 then
                    v312 = l_Position_1.Y > v_u_39.ViewSizeY() - v311
                else
                    v312 = false
                end;
                if v312 or v310 then
                    for v313, _ in pairs(v_u_245) do
                        if v313 ~= p307 then
                            local l_Position_2 = v313.Position
                            local v314 = math.min(v_u_39.ViewSizeY() * 0.33, 250)
                            local v315
                            if l_Position_2.X <= v314 then
                                v315 = l_Position_2.Y > v_u_39.ViewSizeY() - v314
                            else
                                v315 = false
                            end;
                            local l_Position_3 = v313.Position
                            local v316 = math.min(v_u_39.ViewSizeY() * 0.33, 250)
                            local v317
                            if l_Position_3.X >= v_u_39.ViewSizeX() - v316 then
                                v317 = l_Position_3.Y > v_u_39.ViewSizeY() - v316
                            else
                                v317 = false
                            end;
                            if v313.UserInputState ~= Enum.UserInputState.End and (v310 and v317 or v312 and v315) then
                                if v_u_5 then
                                    v_u_5:Fire(true)
                                end;
                                return;
                            end;
                        end;
                    end;
                end;
            end;
            if p308 == false and (p307.UserInputType == Enum.UserInputType.Keyboard and v_u_252[p307.KeyCode]) then
                v_u_4 = nil
                if v_u_205 then
                    v_u_205:Cancel()
                end;
                if v_u_207 then
                    v_u_207:disconnect()
                    v_u_207 = nil
                end;
                if v_u_208 then
                    v_u_208:disconnect()
                    v_u_208 = nil
                end;
                if v_u_206 then
                    s_Debris_0:AddItem(v_u_206, 0)
                    v_u_206 = nil
                end;
            end;
            if p307.UserInputType == Enum.UserInputType.MouseButton1 then
                v_u_247 = tick()
                v_u_248 = p307.Position
            end;
            if p307.UserInputType == Enum.UserInputType.MouseButton2 then
                v_u_249 = tick()
                v_u_250 = p307.Position
            end;
        end)
        v_u_255 = s_UserInputService_0.InputChanged:connect(function(p318, p319) --[[ Line: 1367 ]]
            --[[ Upvalues: (ref 1): v_u_245, (ref 2): v_u_246 ]]
            if p318.UserInputType == Enum.UserInputType.Touch and v_u_245[p318] == nil then
                v_u_245[p318] = p319
                if not p319 then
                    v_u_246 = v_u_246 + 1
                end;
            end;
        end)
        v_u_256 = s_UserInputService_0.InputEnded:connect(function(p320, _) --[[ Line: 1373 ]]
            --[[ Upvalues: (ref 1): v_u_245, (ref 2): v_u_246, (ref 3): v_u_251, (ref 4): v_u_249, (ref 5): v_u_250, (ref 6): f_OnTap ]]
            if p320.UserInputType == Enum.UserInputType.Touch then
                if v_u_245[p320] ~= nil and v_u_245[p320] == false then
                    v_u_246 = v_u_246 - 1
                end;
                v_u_245[p320] = nil
            end;
            if p320.UserInputType == Enum.UserInputType.MouseButton2 then
                v_u_251 = tick()
                local l_Position_4 = p320.Position
                if v_u_251 - v_u_249 < 0.25 and (l_Position_4 - v_u_250).magnitude < 5 then
                    f_OnTap({ l_Position_4 })
                end;
            end;
        end)
        v_u_253 = s_UserInputService_0.TouchTap:connect(function(p321, p322) --[[ Line: 1388 ]]
            --[[ Upvalues: (ref 1): f_OnTap ]]
            if not p322 then
                f_OnTap(p321)
            end;
        end)
        if not s_UserInputService_0.TouchEnabled then
            if v_u_213 then
                v_u_213:Stop()
                v_u_213 = nil
            end;
            v_u_213 = f_AutoJumper()
        end;
        local function f_getThrottleAndSteer(p323, p324) --[[ Name: getThrottleAndSteer ]] --[[ Line: 1402 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4 ]]
            local v325 = p324 - p323.Position
            local l_unit_2 = Vector3.new(v325.X, 0, v325.Z).unit
            local l_unit_3 = Vector3.new(p323.CFrame.lookVector.X, 0, p323.CFrame.lookVector.Z).unit
            local l_magnitude_1 = (l_unit_2 - l_unit_3).magnitude
            local v326 = math.deg((math.acos((l_unit_2:Dot(l_unit_3)))))
            local v327 = p323.CFrame:pointToObjectSpace(p324).X > 0
            local v328 = l_magnitude_1 > 1.8 and -1 or (l_magnitude_1 < 0.25 and 1 or 0)
            local v329 = v_u_3.Position - v_u_4
            local l_Velocity_0 = v_u_3.Velocity
            if l_Velocity_0.magnitude * 1.5 > v329.magnitude then
                v328 = l_Velocity_0.magnitude * 0.5 <= v329.magnitude and 0 or -v328
            end;
            local v330 = v326 > 5 and v326 < 175 and (v327 and 1 or -1) or 0
            local v331 = math.deg(v_u_3.RotVelocity.magnitude)
            local v332 = math.max(math.min(v326, 180 - v326), 10)
            if v_u_3.RotVelocity.X < 0 == (v330 < 0) and v332 < v331 * 1.5 then
                v330 = v332 >= v331 * 0.5 and 0 or -v330
            end;
            return v328, v330;
        end;
        local function f_Update() --[[ Name: Update ]] --[[ Line: 1448 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (copy 3): f_getThrottleAndSteer ]]
            if CameraModule then
                if CameraModule.UserPanningTheCamera then
                    CameraModule.UpdateTweenFunction = nil
                elseif CameraModule.UpdateTweenFunction and CameraModule.UpdateTweenFunction() then
                    CameraModule.UpdateTweenFunction = nil
                end;
                CameraModule:Update()
            end;
            if v_u_3 and v_u_4 then
                local v333, v334 = f_getThrottleAndSteer(v_u_3, v_u_4)
                v_u_3.Throttle = v333
                v_u_3.Steer = v334
            end;
        end;
        if not pcall(function() --[[ Line: 1471 ]]
            --[[ Upvalues: (ref 1): s_RunService_0, (copy 2): f_Update ]]
            s_RunService_0:BindToRenderStep("ClickToMoveRenderUpdate", Enum.RenderPriority.Camera.Value - 1, f_Update)
        end) then
            if v_u_261 then
                v_u_261:disconnect()
            end;
            v_u_261 = s_RunService_0.RenderStepped:connect(f_Update)
        end;
        local v_u_335 = false
        local v_u_336 = false
        local function f_onSeated(p337, p338, p339) --[[ Name: onSeated ]] --[[ Line: 1481 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_3, (ref 3): v_u_213, (ref 4): v_u_335, (ref 5): v_u_336, (ref 6): f_AutoJumper ]]
            if p338 then
                if v_u_6 then
                    v_u_6:Fire(true)
                end;
                if p339.ClassName == "VehicleSeat" then
                    v_u_3 = p339
                    if v_u_213 then
                        v_u_213:Stop()
                        v_u_213 = nil
                        v_u_335 = true
                    else
                        v_u_335 = false
                    end;
                    if p337.AutoJumpEnabled then
                        v_u_336 = true
                        p337.AutoJumpEnabled = false
                        return;
                    end;
                end;
            else
                v_u_3 = nil
                if v_u_6 then
                    v_u_6:Fire(false)
                end;
                if v_u_335 then
                    v_u_213 = f_AutoJumper()
                    v_u_335 = false
                end;
                if v_u_336 then
                    p337.AutoJumpEnabled = true
                    v_u_336 = false
                end;
            end;
        end;
        local function f_OnCharacterChildAdded(p_u_340) --[[ Name: OnCharacterChildAdded ]] --[[ Line: 1516 ]]
            --[[ Upvalues: (ref 1): s_UserInputService_0, (ref 2): v_u_257, (ref 3): s_Debris_0, (ref 4): v_u_206, (ref 5): v_u_213, (ref 6): v_u_262, (copy 7): f_onSeated ]]
            if s_UserInputService_0.TouchEnabled and p_u_340:IsA("Tool") then
                p_u_340.ManualActivationOnly = true
            end;
            if p_u_340:IsA("Humanoid") then
                local v341 = v_u_257
                if v341 then
                    v341:disconnect()
                end;
                v_u_257 = p_u_340.Died:connect(function() --[[ Line: 1524 ]]
                    --[[ Upvalues: (ref 1): s_Debris_0, (ref 2): v_u_206, (ref 3): v_u_213 ]]
                    s_Debris_0:AddItem(v_u_206, 1)
                    if v_u_213 then
                        v_u_213:Stop()
                        v_u_213 = nil
                    end;
                end)
                v_u_262 = p_u_340.Seated:connect(function(p342, p343) --[[ Line: 1533 ]]
                    --[[ Upvalues: (ref 1): f_onSeated, (copy 2): p_u_340 ]]
                    f_onSeated(p_u_340, p342, p343)
                end)
                if p_u_340.SeatPart then
                    f_onSeated(p_u_340, true, p_u_340.SeatPart)
                end;
            end;
        end;
        v_u_258 = p306.ChildAdded:connect(function(p344) --[[ Line: 1540 ]]
            --[[ Upvalues: (copy 1): f_OnCharacterChildAdded ]]
            f_OnCharacterChildAdded(p344)
        end)
        v_u_260 = p306.ChildRemoved:connect(function(p345) --[[ Line: 1543 ]]
            --[[ Upvalues: (ref 1): s_UserInputService_0 ]]
            if s_UserInputService_0.TouchEnabled and p345:IsA("Tool") then
                p345.ManualActivationOnly = false
            end;
        end)
        for _, v346 in pairs(p306:GetChildren()) do
            f_OnCharacterChildAdded(v346)
        end;
    end;
    local v_u_347 = false
    v244.Stop = function(_) --[[ Name: Stop ]] --[[ Line: 1557 ]]
        --[[ Upvalues: (ref 1): v_u_347, (copy 2): f_DisconnectEvents, (ref 3): v_u_4, (ref 4): v_u_205, (ref 5): v_u_207, (ref 6): v_u_208, (ref 7): v_u_206, (ref 8): s_Debris_0, (ref 9): v_u_213, (ref 10): s_UserInputService_0, (ref 11): l_localPlayer_0 ]]
        if v_u_347 then
            f_DisconnectEvents()
            v_u_4 = nil
            if v_u_205 then
                v_u_205:Cancel()
            end;
            if v_u_207 then
                v_u_207:disconnect()
                v_u_207 = nil
            end;
            if v_u_208 then
                v_u_208:disconnect()
                v_u_208 = nil
            end;
            if v_u_206 then
                s_Debris_0:AddItem(v_u_206, 0)
                v_u_206 = nil
            end;
            if v_u_213 then
                v_u_213:Stop()
                v_u_213 = nil
            end;
            if CameraModule then
                CameraModule.UpdateTweenFunction = nil
                CameraModule:SetEnabled(false)
            end;
            local v348 = s_UserInputService_0.TouchEnabled and l_localPlayer_0.Character
            if v348 then
                for _, v349 in pairs(v348:GetChildren()) do
                    if v349:IsA("Tool") then
                        v349.ManualActivationOnly = false
                    end;
                end;
            end;
            v_u_4 = nil
            v_u_347 = false
        end;
    end;
    v244.Start = function(_) --[[ Name: Start ]] --[[ Line: 1585 ]]
        --[[ Upvalues: (ref 1): v_u_347, (ref 2): l_localPlayer_0, (copy 3): f_OnCharacterAdded, (ref 4): v_u_259 ]]
        if not v_u_347 then
            if l_localPlayer_0.Character then
                f_OnCharacterAdded(l_localPlayer_0.Character)
            end;
            v_u_259 = l_localPlayer_0.CharacterAdded:connect(f_OnCharacterAdded)
            if CameraModule then
                CameraModule:SetEnabled(true)
            end;
            v_u_347 = true
        end;
    end;
    return v244;
end;
