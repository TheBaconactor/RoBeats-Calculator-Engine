-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:33 PM
-- Cached decompilation

local v1 = {}
local v_u_2 = {
    Vector2.new(1, 1) / 2,
    Vector2.new(0, 0),
    Vector2.new(1, 0),
    Vector2.new(1, 1),
    Vector2.new(0, 1)
}
local v_u_3 = { "Humanoid", "VehicleSeat", "SkateboardPlatform" }
local s_Players_0 = game:GetService("Players")
local v_u_4 = nil
local v_u_5 = nil
local v_u_6 = {}
local v_u_7 = {}
local v_u_8 = 0
local v_u_9 = 0
local v_u_10 = false
local function f_OptCastRayWhitelist(p11, p12, p13) --[[ Name: OptCastRayWhitelist ]] --[[ Line: 48 ]]
    local v14 = RaycastParams.new()
    v14.FilterType = Enum.RaycastFilterType.Whitelist
    v14.FilterDescendantsInstances = p13
    v14.IgnoreWater = true
    local v15 = p12 - p11
    local v16 = Ray.new(p11, v15.Unit * math.min(v15.Magnitude, 999))
    local v17 = workspace:Raycast(v16.Origin, v16.Direction, v14)
    if v17 then
        return v17.Instance, v17.Position;
    else
        return nil, p12;
    end;
end;
local function f_ScreenToWorld(p18, p19, p20) --[[ Name: ScreenToWorld ]] --[[ Line: 64 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    local l_FieldOfView_0 = v_u_4.FieldOfView
    local l_CoordinateFrame_0 = v_u_4.CoordinateFrame
    local l_Unit_0 = l_CoordinateFrame_0:vectorToWorldSpace((Vector3.new(p18.x - p19.x / 2, p19.y / 2 - p18.y, -(p19.y / (math.tan(math.rad(l_FieldOfView_0) / 2) * 2))))).Unit
    return l_CoordinateFrame_0.p + l_Unit_0 * (p20 / math.sin(1.5707963267948966 - math.acos((math.min(1, l_Unit_0:Dot(l_CoordinateFrame_0.lookVector))))));
end;
local function f_OnCameraChanged(p21) --[[ Name: OnCameraChanged ]] --[[ Line: 74 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (ref 3): v_u_10, (copy 4): v_u_3 ]]
    if p21 == "CameraSubject" then
        v_u_7 = {}
        local l_CameraSubject_0 = v_u_4.CameraSubject
        if l_CameraSubject_0 then
            v_u_10 = false
            for _, v22 in pairs(v_u_3) do
                if l_CameraSubject_0:IsA(v22) then
                    v_u_10 = true
                    break;
                end;
            end;
            if l_CameraSubject_0:IsA("VehicleSeat") then
                v_u_7 = l_CameraSubject_0:GetConnectedParts(true)
            end;
        end;
    end;
end;
local function _(p23, p24) --[[ Name: OnCharacterAdded ]] --[[ Line: 97 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    v_u_6[p23] = p24
end;
local function f_OnPlayersChildAdded(p_u_25) --[[ Name: OnPlayersChildAdded ]] --[[ Line: 101 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    if p_u_25:IsA("Player") then
        p_u_25.CharacterAdded:connect(function(p26) --[[ Line: 103 ]]
            --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_6 ]]
            v_u_6[p_u_25] = p26
        end)
        if p_u_25.Character then
            v_u_6[p_u_25] = p_u_25.Character
        end;
    end;
end;
local function f_OnPlayersChildRemoved(p27) --[[ Name: OnPlayersChildRemoved ]] --[[ Line: 112 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    if p27:IsA("Player") then
        v_u_6[p27] = nil
    end;
end;
local function f_OnWorkspaceChanged(p28) --[[ Name: OnWorkspaceChanged ]] --[[ Line: 118 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5, (copy 3): f_OnCameraChanged ]]
    local v29 = p28 == "CurrentCamera" and workspace.CurrentCamera
    if v29 then
        v_u_4 = v29
        if v_u_5 then
            v_u_5:disconnect()
        end;
        v_u_5 = v_u_4.Changed:connect(f_OnCameraChanged)
        f_OnCameraChanged("CameraSubject")
    end;
end;
v1.Update = function(_, p_u_30) --[[ Name: Update ]] --[[ Line: 137 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_4, (copy 3): v_u_2, (copy 4): f_ScreenToWorld, (copy 5): f_OptCastRayWhitelist, (ref 6): v_u_9, (ref 7): v_u_8 ]]
    if v_u_10 then
        local l_p_0 = v_u_4.Focus.p
        local l_CoordinateFrame_1 = v_u_4.CoordinateFrame
        local v31 = l_CoordinateFrame_1.p + l_CoordinateFrame_1.lookVector * 0.5
        local l_ViewportSize_0 = v_u_4.ViewportSize
        local v_u_32 = {}
        pcall(function() --[[ Line: 146 ]]
            --[[ Upvalues: (copy 1): p_u_30, (copy 2): v_u_32 ]]
            table.insert(v_u_32, p_u_30.EnvironmentSetup:get_lobby_environment())
        end)
        local v33 = 0
        for _, v34 in pairs(v_u_2) do
            local v35 = f_ScreenToWorld(l_ViewportSize_0 * v34, l_ViewportSize_0, 0.5)
            local _, v36 = f_OptCastRayWhitelist(l_p_0 + (v35 - v31), v35, v_u_32)
            local l_Magnitude_0 = (v36 - v35).Magnitude
            if v33 < l_Magnitude_0 then
                v33 = l_Magnitude_0
            end;
        end;
        local l_Magnitude_1 = (l_CoordinateFrame_1.p - l_p_0).Magnitude
        if math.abs(l_Magnitude_1 - v_u_9) > 0.001 then
            v_u_8 = 0
        end;
        local v37 = math.max(v33, v_u_8)
        if v37 > 0 then
            v_u_4.CoordinateFrame = l_CoordinateFrame_1 + l_CoordinateFrame_1.lookVector * v37
            v_u_8 = math.max(0, v37 - 0.3)
        end;
        v_u_9 = l_Magnitude_1
    end;
end;
workspace.Changed:connect(f_OnWorkspaceChanged)
local l_CurrentCamera_0 = workspace.CurrentCamera
if l_CurrentCamera_0 then
    local v38 = l_CurrentCamera_0
    if v_u_5 then
        v_u_5:disconnect()
    end;
    v_u_5 = v38.Changed:connect(f_OnCameraChanged)
    f_OnCameraChanged("CameraSubject")
end;
s_Players_0.ChildRemoved:connect(f_OnPlayersChildRemoved)
s_Players_0.ChildAdded:connect(f_OnPlayersChildAdded)
for _, v39 in pairs(s_Players_0:GetPlayers()) do
    f_OnPlayersChildAdded(v39)
end;
return v1;
