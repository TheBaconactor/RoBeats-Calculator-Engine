-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local s_InsertService_0 = game:GetService("InsertService")
local s_Players_0 = game:GetService("Players")
local v_u_1 = require(game.ReplicatedStorage.Avatar.CreateCharacterUtilities)
local v_u_2 = require(game.ReplicatedStorage.Avatar.CreateCharacterEnum)
local l_Default_0 = game.ReplicatedStorage.CharacterProtos.Default
local function f_setupHumanoid(p3, p4) --[[ Name: setupHumanoid ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    local v_u_5 = p3:FindFirstChild("Humanoid")
    if v_u_5 then
        v_u_5.Parent = nil
        v_u_5.Parent = p3
    else
        v_u_5 = Instance.new("Humanoid", p3)
        if p4 == v_u_2.AvatarTypes.R15 then
            v_u_5.RigType = v_u_2.HumanoidRigType.R15
            v_u_5.HipHeight = 1.35
        else
            v_u_5.RigType = v_u_2.HumanoidRigType.R6
        end;
    end;
    v_u_5.DisplayDistanceType = v_u_2.HumanoidDisplayDistanceType.None
    for _, v_u_6 in pairs(v_u_2.HumanoidRigType:GetEnumItems()) do
        if v_u_6 ~= v_u_2.HumanoidStateType.None and v_u_6 ~= v_u_2.HumanoidStateType.RunningNoPhysics then
            pcall(function() --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_6 ]]
                v_u_5:SetStateEnabled(v_u_6, false)
            end)
        end;
    end;
end;
local function _(p_u_7, p8) --[[ Name: getInsertServiceDummy ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): s_InsertService_0 ]]
    local v_u_9 = nil
    local v10, v11 = pcall(function() --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): s_InsertService_0, (copy 3): p_u_7 ]]
        v_u_9 = s_InsertService_0:LoadAsset(p_u_7):GetChildren()[1]
    end)
    if v10 then
        return v_u_9;
    end;
    warn("Error loading InsertService dummy: \n" .. v11)
    return p8:Clone();
end;
local function f_getDummy() --[[ Name: getDummy ]] --[[ Line: 60 ]]
    --[[ Upvalues: (copy 1): l_Default_0 ]]
    return l_Default_0:Clone();
end;
local function _(_) --[[ Name: getResolvedAvatarType ]] --[[ Line: 64 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.AvatarTypes.R15;
end;
return function(p_u_12) --[[ Name: createCharacter ]] --[[ Line: 68 ]]
    --[[ Upvalues: (copy 1): f_getDummy, (copy 2): s_Players_0, (copy 3): v_u_2, (copy 4): l_Default_0, (copy 5): v_u_1, (copy 6): f_setupHumanoid ]]
    if not (p_u_12 and tonumber(p_u_12)) then
        warn("createCharacter failed: not a valid userId")
        return f_getDummy();
    end;
    local v13, v14 = pcall(function() --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (copy 2): p_u_12 ]]
        return s_Players_0:GetCharacterAppearanceAsync(p_u_12);
    end)
    if not v13 then
        warn("createCharacter: Failed to load characterAppearance for userId " .. tostring(p_u_12))
        return f_getDummy();
    end;
    local l_R15_0 = v_u_2.AvatarTypes.R15
    local v15 = l_Default_0:Clone()
    v15.Name = tostring(p_u_12)
    for _, v16 in pairs(v14:GetChildren()) do
        if v16:IsA("Folder") then
            v_u_1.AddItemToCharacter(v15, v16, l_R15_0)
        end;
    end;
    if l_R15_0 == v_u_2.AvatarTypes.R15 then
        v_u_1.BuildRigFromAttachments(v15.HumanoidRootPart)
    end;
    f_setupHumanoid(v15, l_R15_0)
    for _, v17 in pairs(v14:GetChildren()) do
        if not v17:IsA("Folder") then
            v_u_1.AddItemToCharacter(v15, v17, l_R15_0)
        end;
    end;
    v14:Destroy()
    return v15;
end;
