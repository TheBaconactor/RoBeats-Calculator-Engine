-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v2 = {}
local function _(p3, p4) --[[ Name: weld_attachments ]] --[[ Line: 7 ]]
    local v5 = ("AttachmentWeld_" .. p3.Parent.Name .. "_") .. p4.Parent.Name
    local l_Weld_0 = Instance.new("Weld")
    l_Weld_0.Part0 = p3.Parent
    l_Weld_0.Part1 = p4.Parent
    l_Weld_0.C0 = p3.CFrame
    l_Weld_0.C1 = p4.CFrame
    l_Weld_0.Parent = p4.Parent
    l_Weld_0.Name = v5
    return l_Weld_0;
end;
local function f_findFirstMatchingAttachment(p6, p7) --[[ Name: findFirstMatchingAttachment ]] --[[ Line: 22 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v8 = v_u_1:new()
    for _, v9 in pairs(p6:GetChildren()) do
        if v9:IsA("BasePart") then
            v8:push_back(v9)
        end;
    end;
    v8:sort(function(p10, p11) --[[ Line: 30 ]]
        local l_Name_0 = p10.Name
        local l_Name_1 = p11.Name
        if l_Name_0 == "Head" then
            return true;
        elseif l_Name_1 == "Head" then
            return false;
        else
            local v12 = string.find(l_Name_0, "Left") or string.find(l_Name_0, "Right")
            local v13 = string.find(l_Name_1, "Left") or string.find(l_Name_1, "Right")
            if v12 and v13 then
                return l_Name_0 < l_Name_1;
            elseif v12 then
                return true;
            elseif v13 then
                return false;
            else
                return l_Name_0 < l_Name_1;
            end;
        end;
    end)
    for _, v14 in v8:key_itr() do
        for _, v15 in pairs(v14:GetChildren()) do
            if v15:IsA("Attachment") and v15.Name == p7 then
                return v15;
            end;
        end;
    end;
end;
local v_u_16 = nil
local v_u_17 = nil
v2.set_start_end_fns = function(_, p18, p19) --[[ Name: set_start_end_fns ]] --[[ Line: 59 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17 ]]
    v_u_16 = p18
    v_u_17 = p19
end;
v2.get_start_fn = function(_) --[[ Name: get_start_fn ]] --[[ Line: 64 ]]
    --[[ Upvalues: (ref 1): v_u_16 ]]
    return v_u_16;
end;
v2.get_end_fn = function(_) --[[ Name: get_end_fn ]] --[[ Line: 65 ]]
    --[[ Upvalues: (ref 1): v_u_17 ]]
    return v_u_17;
end;
v2.apply = function(_, p_u_20, p21, p_u_22) --[[ Name: apply ]] --[[ Line: 67 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (copy 3): f_findFirstMatchingAttachment ]]
    if v_u_16 then
        v_u_16()
    end;
    local v_u_23 = v_u_17
    local function v_u_24() --[[ Line: 73 ]]
        --[[ Upvalues: (copy 1): v_u_23, (copy 2): p_u_22 ]]
        if v_u_23 then
            v_u_23()
        end;
        if p_u_22 then
            p_u_22()
        end;
    end;
    p21.Parent = p_u_20
    local v_u_25 = p21:FindFirstChild("Handle")
    if v_u_25 then
        for _, v26 in pairs(v_u_25:GetChildren()) do
            if v26:IsA("Weld") then
                v26:Destroy()
            end;
        end;
        local v_u_27 = v_u_25:FindFirstChildOfClass("Attachment")
        if v_u_27 then
            local l_Name_2 = v_u_27.Name
            local v_u_28 = f_findFirstMatchingAttachment(p_u_20, l_Name_2)
            v_u_25.Anchored = true
            spawn(function() --[[ Line: 98 ]]
                --[[ Upvalues: (copy 1): v_u_25, (copy 2): p_u_20, (copy 3): v_u_27, (copy 4): v_u_24, (copy 5): v_u_23, (copy 6): p_u_22, (ref 7): v_u_28, (ref 8): f_findFirstMatchingAttachment, (copy 9): l_Name_2 ]]
                wait()
                v_u_25.Anchored = false
                local v29 = 0
                while v29 < 10 and p_u_20 do
                    if v_u_27 == nil or v_u_27.Parent == nil then
                        if v_u_24 then
                            if v_u_23 then
                                v_u_23()
                            end;
                            if p_u_22 then
                                p_u_22()
                            end;
                        end;
                        return;
                    end;
                    v_u_28 = f_findFirstMatchingAttachment(p_u_20, l_Name_2)
                    if v_u_28 and v_u_27 then
                        local v30 = v_u_28
                        local v31 = v_u_27
                        local v32 = ("AttachmentWeld_" .. v30.Parent.Name .. "_") .. v31.Parent.Name
                        local l_Weld_1 = Instance.new("Weld")
                        l_Weld_1.Part0 = v30.Parent
                        l_Weld_1.Part1 = v31.Parent
                        l_Weld_1.C0 = v30.CFrame
                        l_Weld_1.C1 = v31.CFrame
                        l_Weld_1.Parent = v31.Parent
                        l_Weld_1.Name = v32
                        if v_u_24 then
                            if v_u_23 then
                                v_u_23()
                            end;
                            if p_u_22 then
                                p_u_22()
                            end;
                        end;
                        return;
                    end;
                    v29 = v29 + 1
                    wait()
                end;
                warn("LocalWeldAccessories:findFirstMatchingAttachment", l_Name_2, "failed timeout, giving up")
                if v_u_24 then
                    if v_u_23 then
                        v_u_23()
                    end;
                    if p_u_22 then
                        p_u_22()
                    end;
                end;
            end)
            return;
        end;
        warn("LocalWeldAccessories:FindFirstChildOfClass(Attachment) failed")
        if v_u_24 then
            if v_u_23 then
                v_u_23()
            end;
            if p_u_22 then
                p_u_22()
                return;
            end;
        end;
    else
        warn("LocalWeldAccessories:accoutrement:FindFirstChild(Handle) failed")
        if v_u_24 then
            if v_u_23 then
                v_u_23()
            end;
            if p_u_22 then
                p_u_22()
            end;
        end;
    end;
end;
return v2;
