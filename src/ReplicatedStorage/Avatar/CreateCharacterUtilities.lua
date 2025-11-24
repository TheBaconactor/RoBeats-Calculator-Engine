-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v3 = {
    ["FindFirstMatchingAttachment"] = findFirstMatchingAttachment,
    ["GetAvatarType"] = getAvatarType
}
local v_u_4 = require(game.ReplicatedStorage.Avatar.CreateCharacterEnum)
local function f_buildJoint(p5, p6) --[[ Name: buildJoint ]] --[[ Line: 13 ]]
    local v7 = p5.Name:gsub("RigAttachment", "")
    local v8 = p6.Parent:FindFirstChild(v7) or Instance.new("Motor6D")
    v8.Name = v7
    v8.Part0 = p5.Parent
    v8.Part1 = p6.Parent
    v8.C0 = p5.CFrame
    v8.C1 = p6.CFrame
    v8.Parent = p6.Parent
end;
local function v_u_17(p_u_9, p10) --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): f_buildJoint, (ref 2): v_u_17 ]]
    local v_u_11 = {}
    for _, v12 in pairs(p_u_9.Parent:GetChildren()) do
        if v12:IsA("BasePart") and (v12 ~= p_u_9 and v12 ~= p10) then
            table.insert(v_u_11, v12)
        end;
    end;
    local function f_processRigAttachment(p13) --[[ Name: processRigAttachment ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): v_u_11, (ref 2): f_buildJoint, (ref 3): v_u_17, (copy 4): p_u_9 ]]
        for _, v14 in pairs(v_u_11) do
            local v15 = v14:FindFirstChild(p13.Name)
            if v15 then
                f_buildJoint(p13, v15)
                v_u_17(v15.Parent, p_u_9)
            end;
        end;
    end;
    for _, v16 in pairs(p_u_9:GetChildren()) do
        if v16:IsA("Attachment") and string.find(v16.Name, "RigAttachment") then
            f_processRigAttachment(v16)
        end;
    end;
end;
findFirstMatchingAttachment = function(p18, p19) --[[ Name: findFirstMatchingAttachment ]] --[[ Line: 59 ]]
    for _, v20 in pairs(p18:GetChildren()) do
        if v20:IsA("Attachment") and v20.Name == p19 then
            return v20;
        end;
        if not (v20:IsA("Accoutrement") or v20:IsA("Tool")) then
            local v21 = findFirstMatchingAttachment(v20, p19)
            if v21 then
                return v21;
            end;
        end;
    end;
end;
getAvatarType = function(p22) --[[ Name: getAvatarType ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    local v23 = p22:FindFirstChildOfClass("Humanoid")
    if v23 then
        if v23.RigType == v_u_4.HumanoidRigType.R15 then
            return v_u_4.AvatarTypes.R15;
        else
            return v_u_4.AvatarTypes.R6;
        end;
    else
        return v_u_4.AvatarTypes.Unknown;
    end;
end;
local function f_getOldCharacterMesh(p24, p25) --[[ Name: getOldCharacterMesh ]] --[[ Line: 90 ]]
    for _, v26 in pairs(p24:GetChildren()) do
        if v26:IsA("CharacterMesh") and v26.BodyPart == p25.BodyPart then
            return v26;
        end;
    end;
end;
local function _(p27, p28) --[[ Name: weldAttachments ]] --[[ Line: 98 ]]
    local l_Weld_0 = Instance.new("Weld")
    l_Weld_0.Part0 = p27.Parent
    l_Weld_0.Part1 = p28.Parent
    l_Weld_0.C0 = p27.CFrame
    l_Weld_0.C1 = p28.CFrame
    l_Weld_0.Parent = p27.Parent
    return l_Weld_0;
end;
local function _(p29, p30, p31, p32, p33, p34) --[[ Name: buildWeld ]] --[[ Line: 108 ]]
    local l_Weld_1 = Instance.new("Weld")
    l_Weld_1.Name = p29
    l_Weld_1.Part0 = p31
    l_Weld_1.Part1 = p32
    l_Weld_1.C0 = p33
    l_Weld_1.C1 = p34
    l_Weld_1.Parent = p30
    return l_Weld_1;
end;
local v_u_35 = nil
v_u_35 = {
    ["CharacterMesh"] = function(p36, p37, _) --[[ Line: 125 ]]
        --[[ Upvalues: (copy 1): f_getOldCharacterMesh ]]
        local v38 = f_getOldCharacterMesh(p36, p37)
        if v38 then
            v38:Destroy()
        end;
        for _, v39 in pairs(p36:GetChildren()) do
            if p37.BodyPart.Name == v39.Name:gsub("%s+", "") then
                local l_SpecialMesh_0 = Instance.new("SpecialMesh")
                l_SpecialMesh_0.MeshId = "rbxassetid://" .. p37.MeshId
                l_SpecialMesh_0.Parent = v39
                break;
            end;
        end;
        p37.Parent = p36
    end,
    ["Decal"] = function(p40, p41, _) --[[ Line: 141 ]]
        local v42 = p41.Name == "face" and p40:FindFirstChild("Head")
        if v42 then
            local v43 = v42:FindFirstChild("face") or p41
            v43.Name = "face"
            v43.Texture = p41.Texture
            v43.Parent = v42
        end;
    end,
    ["SpecialMesh"] = function(p44, p45, _) --[[ Line: 153 ]]
        local v46 = p44:FindFirstChild("Head")
        if v46 then
            local v47 = v46:FindFirstChildOfClass("SpecialMesh")
            if v47 then
                v47:Destroy()
            end;
            p45.Parent = v46
        end;
    end,
    ["Folder"] = function(p48, p49, p50) --[[ Line: 164 ]]
        --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_35 ]]
        if p49.Name == "R6" and p50 == v_u_4.AvatarTypes.R6 then
            local v51 = p49:FindFirstChildOfClass("CharacterMesh")
            if v51 then
                v_u_35.CharacterMesh(p48, v51)
                return;
            end;
        else
            if p49.Name == "R15" and p50 == v_u_4.AvatarTypes.R15 then
                for _, v52 in pairs(p49:GetChildren()) do
                    if v52:IsA("BasePart") then
                        local v53 = p48:FindFirstChild(v52.Name)
                        v53.Name = ""
                        v53:Destroy()
                        v52.Parent = p48
                    end;
                end;
                return;
            end;
            local v54 = p49.Name == "R15Anim" and (p50 == v_u_4.AvatarTypes.R15 and p48:FindFirstChild("Animate"))
            if v54 then
                for _, v55 in pairs(p49:GetChildren()) do
                    v55.Parent = v54
                end;
            end;
        end;
    end,
    ["NumberValue"] = function(p56, p57, _) --[[ Line: 189 ]]
        p57.Parent = p56:FindFirstChildOfClass("Humanoid")
    end
}
local function f_addAccoutrement(p58, p59, _) --[[ Name: addAccoutrement ]] --[[ Line: 195 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    p59.Parent = p58
    local v60 = p59:FindFirstChild("Handle")
    if v60 then
        local v61 = v60:FindFirstChildOfClass("Attachment")
        if v61 then
            local v62 = findFirstMatchingAttachment(p58, v61.Name)
            if v62 then
                local v63 = v_u_1:get_list_of_children_of_classname(p59, "WrapLayer"):count() > 0
                if not v63 then
                    local l_Weld_2 = Instance.new("Weld")
                    l_Weld_2.Part0 = v62.Parent
                    l_Weld_2.Part1 = v61.Parent
                    l_Weld_2.C0 = v62.CFrame
                    l_Weld_2.C1 = v61.CFrame
                    l_Weld_2.Parent = v62.Parent
                    return;
                end;
                if v_u_2.AllowLayeredClothing ~= true then
                    p59:Destroy()
                    return;
                end;
                local l_Weld_3 = Instance.new("Weld")
                l_Weld_3.Part0 = v62.Parent
                l_Weld_3.Part1 = v61.Parent
                l_Weld_3.C0 = v62.CFrame
                l_Weld_3.C1 = v61.CFrame
                l_Weld_3.Parent = v62.Parent
                local v64 = v_u_1:get_character_humanoid(p58)
                if v64 and v63 then
                    p59.Parent = nil
                    v64:AddAccessory(p59)
                    return;
                end;
            end;
        else
            warn("CreateCharacterUtilities:addAccoutrement attachment not found, attaching to head")
            local v65 = p58:FindFirstChild("Head")
            if v65 then
                local v66 = CFrame.new(0, 0.5, 0)
                local l_AttachmentPoint_0 = p59.AttachmentPoint
                local l_Weld_4 = Instance.new("Weld")
                l_Weld_4.Name = "HeadWeld"
                l_Weld_4.Part0 = v65
                l_Weld_4.Part1 = v60
                l_Weld_4.C0 = v66
                l_Weld_4.C1 = l_AttachmentPoint_0
                l_Weld_4.Parent = v65
            end;
        end;
    end;
end;
local function v71(p67, p68, p69) --[[ Line: 235 ]]
    --[[ Upvalues: (ref 1): v_u_35, (copy 2): f_addAccoutrement ]]
    if p67 then
        if p68 then
            local v70 = p69 or getAvatarType(p67)
            if v_u_35[p68.ClassName] then
                v_u_35[p68.ClassName](p67, p68, v70)
                return;
            elseif p68:IsA("Accoutrement") then
                f_addAccoutrement(p67, p68, v70)
            else
                p68.Parent = p67
            end;
        else
            warn("AddItemToCharacter: Item is nil", "Stack Trace:" .. debug.traceback())
            return;
        end;
    else
        warn("AddItemToCharacter: Character is nil", "Stack Trace:" .. debug.traceback())
        return;
    end;
end;
v3.BuildRigFromAttachments = v_u_17
v3.AddItemToCharacter = v71
return v3;
