-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Cached decompilation

local function _(p1, p2, p3) --[[ Name: clamp ]] --[[ Line: 5 ]]
    if p1 <= p2 then
        return math.min(p2, (math.max(p1, p3)));
    else
        return p3;
    end;
end;
local function _(p4, p5) --[[ Name: Round ]] --[[ Line: 12 ]]
    local v6 = 10 ^ (p5 or 0)
    return math.floor(p4 * v6 + 0.5) / v6;
end;
return function() --[[ Name: CreateTransparencyController ]] --[[ Line: 18 ]]
    local v7 = {}
    local v_u_8 = tick()
    local v_u_9 = false
    local v_u_10 = false
    local v_u_11 = nil
    local v_u_12 = nil
    local v_u_13 = nil
    local v_u_14 = {}
    local v_u_15 = {}
    local v_u_16 = {}
    local function f_HasToolAncestor(p17) --[[ Name: HasToolAncestor ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): f_HasToolAncestor ]]
        if p17.Parent == nil then
            return false;
        else
            return p17.Parent:IsA("Tool") or f_HasToolAncestor(p17.Parent);
        end;
    end;
    local function _(p18) --[[ Name: IsValidPartToModify ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): f_HasToolAncestor ]]
        if not (p18:IsA("BasePart") or p18:IsA("Decal")) then
            return false;
        end;
        local v19
        if p18.Parent == nil then
            v19 = false
        else
            v19 = p18.Parent:IsA("Tool") or f_HasToolAncestor(p18.Parent)
        end;
        return not v19;
    end;
    local function f_CachePartsRecursive(p20) --[[ Name: CachePartsRecursive ]] --[[ Line: 44 ]]
        --[[ Upvalues: (copy 1): f_HasToolAncestor, (ref 2): v_u_16, (ref 3): v_u_9, (copy 4): f_CachePartsRecursive ]]
        if p20 then
            local v21
            if p20:IsA("BasePart") or p20:IsA("Decal") then
                local v22
                if p20.Parent == nil then
                    v22 = false
                else
                    v22 = p20.Parent:IsA("Tool") or f_HasToolAncestor(p20.Parent)
                end;
                v21 = not v22
            else
                v21 = false
            end;
            if v21 then
                v_u_16[p20] = true
                v_u_9 = true
            end;
            for _, v23 in pairs(p20:GetChildren()) do
                f_CachePartsRecursive(v23)
            end;
        end;
    end;
    local function f_TeardownTransparency() --[[ Name: TeardownTransparency ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_9, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_13, (copy 6): v_u_14, (copy 7): v_u_15 ]]
        for v24, _ in pairs(v_u_16) do
            v24.LocalTransparencyModifier = 0
        end;
        v_u_16 = {}
        v_u_9 = true
        v_u_11 = nil
        if v_u_12 then
            v_u_12:disconnect()
            v_u_12 = nil
        end;
        if v_u_13 then
            v_u_13:disconnect()
            v_u_13 = nil
        end;
        for v25, v26 in pairs(v_u_14) do
            v26:disconnect()
            v_u_14[v25] = nil
        end;
        for v27, v28 in pairs(v_u_15) do
            v28:disconnect()
            v_u_15[v27] = nil
        end;
    end;
    local function f_SetupTransparency(p_u_29) --[[ Name: SetupTransparency ]] --[[ Line: 82 ]]
        --[[ Upvalues: (copy 1): f_TeardownTransparency, (ref 2): v_u_12, (copy 3): f_HasToolAncestor, (ref 4): v_u_16, (ref 5): v_u_9, (copy 6): v_u_14, (copy 7): v_u_15, (ref 8): v_u_13, (copy 9): f_CachePartsRecursive ]]
        f_TeardownTransparency()
        if v_u_12 then
            v_u_12:disconnect()
        end;
        v_u_12 = p_u_29.DescendantAdded:connect(function(p30) --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): f_HasToolAncestor, (ref 2): v_u_16, (ref 3): v_u_9, (ref 4): v_u_14, (ref 5): v_u_15, (copy 6): p_u_29 ]]
            local v31
            if p30:IsA("BasePart") or p30:IsA("Decal") then
                local v32
                if p30.Parent == nil then
                    v32 = false
                else
                    v32 = p30.Parent:IsA("Tool") or f_HasToolAncestor(p30.Parent)
                end;
                v31 = not v32
            else
                v31 = false
            end;
            if v31 then
                v_u_16[p30] = true
                v_u_9 = true
            elseif p30:IsA("Tool") then
                if v_u_14[p30] then
                    v_u_14[p30]:disconnect()
                end;
                v_u_14[p30] = p30.DescendantAdded:connect(function(p33) --[[ Line: 94 ]]
                    --[[ Upvalues: (ref 1): v_u_16 ]]
                    v_u_16[p33] = nil
                    if p33:IsA("BasePart") or p33:IsA("Decal") then
                        p33.LocalTransparencyModifier = 0
                    end;
                end)
                if v_u_15[p30] then
                    v_u_15[p30]:disconnect()
                end;
                v_u_15[p30] = p30.DescendantRemoving:connect(function(p34) --[[ Line: 102 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): f_HasToolAncestor, (ref 3): v_u_16, (ref 4): v_u_9 ]]
                    wait()
                    if p_u_29 and (p34 and p34:IsDescendantOf(p_u_29)) then
                        local v35
                        if p34:IsA("BasePart") or p34:IsA("Decal") then
                            local v36
                            if p34.Parent == nil then
                                v36 = false
                            else
                                v36 = p34.Parent:IsA("Tool") or f_HasToolAncestor(p34.Parent)
                            end;
                            v35 = not v36
                        else
                            v35 = false
                        end;
                        if v35 then
                            v_u_16[p34] = true
                            v_u_9 = true
                        end;
                    end;
                end)
            end;
        end)
        if v_u_13 then
            v_u_13:disconnect()
        end;
        v_u_13 = p_u_29.DescendantRemoving:connect(function(p37) --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            if v_u_16[p37] then
                v_u_16[p37] = nil
                p37.LocalTransparencyModifier = 0
            end;
        end)
        f_CachePartsRecursive(p_u_29)
    end;
    v7.SetEnabled = function(p38, p39) --[[ Name: SetEnabled ]] --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        if v_u_10 ~= p39 then
            v_u_10 = p39
            p38:Update()
        end;
    end;
    v7.SetSubject = function(_, p40) --[[ Name: SetSubject ]] --[[ Line: 132 ]]
        --[[ Upvalues: (copy 1): f_SetupTransparency, (copy 2): f_TeardownTransparency ]]
        local v41
        if p40 and p40:IsA("Humanoid") then
            v41 = p40.Parent
        else
            v41 = nil
        end;
        if p40 and (p40:IsA("VehicleSeat") and p40.Occupant) then
            v41 = p40.Occupant.Parent
        end;
        if v41 then
            f_SetupTransparency(v41)
        else
            f_TeardownTransparency()
        end;
    end;
    v7.Update = function(_) --[[ Name: Update ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_8, (ref 4): v_u_9, (ref 5): v_u_16 ]]
        local v42 = false
        local v43 = tick()
        local l_CurrentCamera_0 = workspace.CurrentCamera
        if l_CurrentCamera_0 then
            local v44
            if v_u_10 then
                local v45 = (7 - (l_CurrentCamera_0.Focus.p - l_CurrentCamera_0.CoordinateFrame.p).magnitude) / 5
                local v46 = v45 < 0.5 and 0 or v45
                if v_u_11 then
                    local v47 = v46 - v_u_11
                    if not v42 and (v46 < 1 and v_u_11 < 0.95) then
                        local v48 = 2.8 * (v43 - v_u_8)
                        local v49 = -v48
                        if v49 <= v48 then
                            v47 = math.min(v48, (math.max(v49, v47)))
                        end;
                    end;
                    v46 = v_u_11 + v47
                else
                    v_u_9 = true
                end;
                local v50 = 10 ^ (2 or 0)
                v44 = math.min(1, (math.max(0, math.floor(v46 * v50 + 0.5) / v50)))
            else
                v44 = 0
            end;
            if v_u_9 or v_u_11 ~= v44 then
                for v51, _ in pairs(v_u_16) do
                    v51.LocalTransparencyModifier = v44
                end;
                v_u_9 = false
                v_u_11 = v44
            end;
        end;
        v_u_8 = v43
    end;
    return v7;
end;
