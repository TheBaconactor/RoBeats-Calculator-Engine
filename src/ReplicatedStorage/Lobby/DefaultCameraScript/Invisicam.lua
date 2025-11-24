-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:32 PM
-- Cached decompilation

local v1 = {
    ["MODE"] = {
        ["CUSTOM"] = 1,
        ["LIMBS"] = 2,
        ["MOVEMENT"] = 3,
        ["CORNERS"] = 4,
        ["CIRCLE1"] = 5,
        ["CIRCLE2"] = 6,
        ["LIMBMOVE"] = 7
    }
}
local v_u_2 = {
    ["CUSTOM"] = 1,
    ["LIMBS"] = 2,
    ["MOVEMENT"] = 3,
    ["CORNERS"] = 4,
    ["CIRCLE1"] = 5,
    ["CIRCLE2"] = 6,
    ["LIMBMOVE"] = 7
}
local l_LIMBS_0 = v_u_2.LIMBS
local v_u_3 = {
    ["Head"] = true,
    ["Left Arm"] = true,
    ["Right Arm"] = true,
    ["Left Leg"] = true,
    ["Right Leg"] = true
}
local v_u_4 = {
    Vector3.new(1, 1, -1),
    Vector3.new(1, -1, -1),
    Vector3.new(-1, -1, -1),
    Vector3.new(-1, 1, -1)
}
local _ = game:GetService("RunService")
local l_LocalPlayer_0 = game:GetService("Players").LocalPlayer
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = {}
local v_u_10 = {}
local v_u_11 = {}
local function f_AssertTypes(p12, ...) --[[ Name: AssertTypes ]] --[[ Line: 64 ]]
    local v13 = {}
    local v14 = ""
    for _, v15 in pairs({ ... }) do
        v13[v15] = true
        v14 = v14 .. (v14 == "" and "" or " or ") .. v15
    end;
    local v16 = type(p12)
    assert(v13[v16], v14 .. " type expected, got: " .. v16)
end;
local function _(p17, p18) --[[ Name: CameraCast ]] --[[ Line: 75 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    local l_p_0 = v_u_5.CoordinateFrame.p
    local v19 = p17 - l_p_0
    return workspace:FindPartOnRayWithIgnoreList(Ray.new(l_p_0, v19.Unit * math.min(v19.Magnitude, 999)), p18);
end;
local function f_LimbBehavior(p20) --[[ Name: LimbBehavior ]] --[[ Line: 86 ]]
    --[[ Upvalues: (ref 1): v_u_11 ]]
    for _, v21 in pairs(v_u_11) do
        if v21.Parent then
            table.insert(p20, v21.Position)
        end;
    end;
end;
local function f_MoveBehavior(p22) --[[ Name: MoveBehavior ]] --[[ Line: 94 ]]
    --[[ Upvalues: (ref 1): v_u_7 ]]
    for v23 = 1, 3 do
        local l_Position_0 = v_u_7.Position
        local l_Velocity_0 = v_u_7.Velocity
        table.insert(p22, l_Position_0 + (v23 - 1) * v_u_7.CFrame.lookVector * (Vector3.new(l_Velocity_0.X, 0, l_Velocity_0.Z).Magnitude / 2))
    end;
end;
local function f_CornerBehavior(p24) --[[ Name: CornerBehavior ]] --[[ Line: 103 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_6, (copy 3): v_u_4 ]]
    local l_CFrame_0 = v_u_7.CFrame
    local l_p_1 = l_CFrame_0.p
    local v25 = l_CFrame_0 - l_p_1
    local v26 = v_u_6:GetExtentsSize() / 2
    table.insert(p24, l_p_1)
    for _, v27 in pairs(v_u_4) do
        table.insert(p24, l_p_1 + v25 * (v26 * v27))
    end;
end;
local function f_CircleBehavior(p28) --[[ Name: CircleBehavior ]] --[[ Line: 114 ]]
    --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_2, (ref 3): v_u_7, (ref 4): v_u_5 ]]
    local v29
    if v_u_8 == v_u_2.CIRCLE1 then
        v29 = v_u_7.CFrame
    else
        local l_CoordinateFrame_0 = v_u_5.CoordinateFrame
        v29 = l_CoordinateFrame_0 - l_CoordinateFrame_0.p + v_u_7.Position
    end;
    table.insert(p28, v29.p)
    for v30 = 0, 9 do
        local v31 = 0.6283185307179586 * v30
        table.insert(p28, v29 * (3 * Vector3.new(math.cos(v31), math.sin(v31), 0)))
    end;
end;
local function f_LimbMoveBehavior(p32) --[[ Name: LimbMoveBehavior ]] --[[ Line: 130 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): f_MoveBehavior ]]
    for _, v33 in pairs(v_u_11) do
        if v33.Parent then
            table.insert(p32, v33.Position)
        end;
    end;
    f_MoveBehavior(p32)
end;
local function f_OnCharacterAdded(p34) --[[ Name: OnCharacterAdded ]] --[[ Line: 135 ]]
    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_11, (copy 3): v_u_3 ]]
    v_u_6 = p34
    v_u_11 = {}
    for _, v35 in pairs(v_u_6:GetChildren()) do
        if v35:IsA("BasePart") and v_u_3[v35.Name] then
            table.insert(v_u_11, v35)
        end;
    end;
end;
local function f_OnWorkspaceChanged(p36) --[[ Name: OnWorkspaceChanged ]] --[[ Line: 146 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    local v37 = p36 == "CurrentCamera" and workspace.CurrentCamera
    if v37 then
        v_u_5 = v37
    end;
end;
v1.Update = function(_) --[[ Name: Update ]] --[[ Line: 160 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_6, (copy 3): v_u_9, (ref 4): v_u_8, (copy 5): v_u_10, (ref 6): v_u_5 ]]
    -- block 30
    if not (v_u_7 and v_u_7.Parent) then
        local v38 = v_u_6:FindFirstChild("Humanoid")
        if v38 and v38.Torso then
            v_u_7 = v38.Torso
        else
            v_u_7 = v_u_6:FindFirstChild("Torso")
            if not v_u_7 then
                return;
            end;
        end;
    end;
    local v39 = {}
    v_u_9[v_u_8](v39)
    local v_u_40 = {}
    local v41 = { v_u_6 }
    local function _(p42) --[[ Name: add ]] --[[ Line: 183 ]]
        --[[ Upvalues: (copy 1): v_u_40, (ref 2): v_u_10 ]]
        v_u_40[p42] = true
        if not v_u_10[p42] then
            v_u_10[p42] = p42.LocalTransparencyModifier
        end;
    end;
    local v43, v44, v45
    -- GenericForInit
v43, v44, v45 = pairs(v39)
[internal control] = v45
-- end GenericForInit
    -- ::l9:: (Possible bug with goto)
    local v46, v47
    -- GenericForNext
v46, v47 = v43(v44, [internal control])
if v46 ~= nil
[internal control] = v46
-- end GenericForNext
    -- ::l3:: (Possible bug with goto)
    break;
    -- ::l8:: (Possible bug with goto)
    while true do
        local l_p_2 = v_u_5.CoordinateFrame.p
        local v48 = v47 - l_p_2
        local v49 = workspace:FindPartOnRayWithIgnoreList(Ray.new(l_p_2, v48.Unit * math.min(v48.Magnitude, 999)), v41)
        if v49 then
            v_u_40[v49] = true
            if not v_u_10[v49] then
                v_u_10[v49] = v49.LocalTransparencyModifier
            end;
            for _, v50 in pairs(v49:GetChildren()) do
                if v50:IsA("Decal") or v50:IsA("Texture") then
                    v_u_40[v50] = true
                    if not v_u_10[v50] then
                        v_u_10[v50] = v50.LocalTransparencyModifier
                    end;
                end;
            end;
            table.insert(v41, v49)
        end;
        if not v49 then
            continue;
        end;
    end;
    -- block 9
    break;
    -- block 11
    break;
    -- ::l21:: (Possible bug with goto)
    for v51, v52 in pairs(v_u_10) do
        local l_LocalTransparencyModifier_0 = v51.LocalTransparencyModifier
        if v_u_40[v51] then
            if l_LocalTransparencyModifier_0 < 0.75 then
                v51.LocalTransparencyModifier = math.min(l_LocalTransparencyModifier_0 + 0.1, 0.75)
            end;
        elseif v52 < l_LocalTransparencyModifier_0 then
            v51.LocalTransparencyModifier = math.max(v52, l_LocalTransparencyModifier_0 - 0.1)
        else
            v_u_10[v51] = nil
        end;
    end;
    return;
end;
v1.SetMode = function(_, p53) --[[ Name: SetMode ]] --[[ Line: 221 ]]
    --[[ Upvalues: (copy 1): f_AssertTypes, (copy 2): v_u_2, (ref 3): v_u_8 ]]
    f_AssertTypes(p53, "number")
    for _, v54 in pairs(v_u_2) do
        if v54 == p53 then
            v_u_8 = p53
            return;
        end;
    end;
    error("Invalid mode number")
end;
v1.SetCustomBehavior = function(_, p55) --[[ Name: SetCustomBehavior ]] --[[ Line: 232 ]]
    --[[ Upvalues: (copy 1): f_AssertTypes, (copy 2): v_u_9, (copy 3): v_u_2 ]]
    f_AssertTypes(p55, "function")
    v_u_9[v_u_2.CUSTOM] = p55
end;
v1.Cleanup = function(_) --[[ Name: Cleanup ]] --[[ Line: 238 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    for v56, v57 in pairs(v_u_10) do
        v56.LocalTransparencyModifier = v57
    end;
end;
workspace.Changed:connect(f_OnWorkspaceChanged)
local l_CurrentCamera_0 = workspace.CurrentCamera
if l_CurrentCamera_0 then
    local _ = l_CurrentCamera_0
end;
l_LocalPlayer_0.CharacterAdded:connect(f_OnCharacterAdded)
if l_LocalPlayer_0.Character then
    f_OnCharacterAdded(l_LocalPlayer_0.Character)
end;
v1:SetMode(l_LIMBS_0)
v_u_9[v_u_2.CUSTOM] = function() end
v_u_9[v_u_2.LIMBS] = f_LimbBehavior
v_u_9[v_u_2.MOVEMENT] = f_MoveBehavior
v_u_9[v_u_2.CORNERS] = f_CornerBehavior
v_u_9[v_u_2.CIRCLE1] = f_CircleBehavior
v_u_9[v_u_2.CIRCLE2] = f_CircleBehavior
v_u_9[v_u_2.LIMBMOVE] = f_LimbMoveBehavior
return v1;
